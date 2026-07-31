import logging
import os
from datetime import datetime

from dalikam.backend.state import StateManager

logger = logging.getLogger(__name__)

# Folder assigned to files that don't belong to any user-created folder
DEFAULT_FOLDER_NAME = "Unfiled"


class FileInfo:
    """
    File metadata helper class.

    Carries the OS-level metadata the file browser shows. It also caches the
    SHA256 hash used by the segmentation pipeline (see `segmentation.build_hash`):
    hashing requires reading the whole volume, which can be multiple GB, so we
    persist it alongside the path and only recompute it when the file changes.
    """

    path: str
    name: str
    creation_date: datetime
    last_mod_date: datetime
    size: int
    mtime_ns: int
    file_hash: str | None

    def __init__(self, path: str, file_hash: str | None = None):
        self.path = path
        self.name = os.path.basename(self.path)
        self.file_hash = file_hash

        stat = os.stat(self.path)
        self.creation_date = datetime.fromtimestamp(stat.st_birthtime)
        self.last_mod_date = datetime.fromtimestamp(stat.st_mtime)
        self.size = stat.st_size
        # Nanosecond mtime is stored verbatim to validate the cached hash on
        # reload: float mtimes lose precision through QSettings and would
        # invalidate the cache even when the file was never touched.
        self.mtime_ns = stat.st_mtime_ns


class Folder:
    """
    A non-nestable virtual folder used purely to organize scans.

    Folders only reference files by absolute path; the underlying files are
    never moved, copied or renamed on disk.
    """

    def __init__(self, name: str):
        self.name = name
        self.files: list[FileInfo] = []

    def add_file(self, file: FileInfo) -> None:
        self.files.append(file)

    def remove_file(self, path: str) -> None:
        # filters all saved files and keeps all paths that don't match the supplied one
        self.files = [f for f in self.files if f.path != path]

    def to_dict(self) -> dict:
        """Serialize the folder for persistent storage."""
        return {
            "name": self.name,
            "files": [self._file_to_dict(f) for f in self.files],
        }

    @staticmethod
    def _file_to_dict(file: FileInfo) -> dict:
        # The cached hash is only trustworthy while the file's mtime and size
        # are unchanged; storing both lets us validate it on reload for free.
        # mtime_ns is an integer, so it round-trips through QSettings exactly.
        return {
            "path": file.path,
            "file_hash": file.file_hash,
            "mtime_ns": file.mtime_ns,
            "size": file.size,
        }


class FolderManager:
    """
    Manages the list of virtual folders and their persistence.

    Acts as the single source of truth for which scans the user has added to the app;
    Structure is loaded from QSettings on construction and files whose path no longer 
    exists are pruned.
    """

    def __init__(self, settings: StateManager) -> None:
        self._settings: StateManager = settings
        self.folders: list[Folder] = []
        self.load_from_settings()

    def load_from_settings(self) -> None:
        """Rebuild the folder structure from persistent storage."""
        self.folders = []
        for folder_data in self._settings.get_folders():
            folder = Folder(folder_data["name"])
            for file_data in folder_data.get("files", []):
                file = self._restore_file(file_data)
                if file is not None:
                    folder.add_file(file)
            self.folders.append(folder)

        # CASE: recover paths that still use the old model with no folders
        if not self.folders and self._settings.get_raw_files():
            logger.info("migrating legacy raw paths into default folder")
            folder = Folder(DEFAULT_FOLDER_NAME)
            for path in self._settings.get_raw_files():
                if os.path.exists(path):
                    folder.add_file(FileInfo(path))
            self.folders.append(folder)
            self.save_to_settings()

    def save_to_settings(self) -> None:
        self._settings.set_folders([f.to_dict() for f in self.folders])

    def get_folder(self, name: str) -> Folder | None:
        return next((f for f in self.folders if f.name == name), None)

    def add_folder(self, name: str) -> Folder:
        folder = Folder(name)
        self.folders.append(folder)
        self.save_to_settings()
        return folder

    def rename_folder(self, old_name: str, new_name: str) -> None:
        folder = self.get_folder(old_name)
        if folder is None:
            raise ValueError(f"folder '{old_name}' does not exist")
        if self.get_folder(new_name) is not None:
            raise ValueError(f"folder '{new_name}' already exists")
        folder.name = new_name
        self.save_to_settings()

    def delete_folder(self, name: str) -> None:
        self.folders = [f for f in self.folders if f.name != name]
        self.save_to_settings()

    def add_file_to_folder(
        self, folder_name: str, path: str, file_hash: str | None = None
    ) -> None:
        """Register an existing file inside a folder, ignoring duplicates."""
        folder = self.get_folder(folder_name)
        if folder is None:
            raise ValueError(f"folder '{folder_name}' does not exist")
        if any(f.path == path for f in folder.files):
            return
        folder.add_file(FileInfo(path, file_hash=file_hash))
        self.save_to_settings()

    def move_file(self, path: str, from_folder: str, to_folder: str) -> None:
        """Move a file between virtual folders; never touches the file itself."""
        if from_folder == to_folder:
            return
        source = self.get_folder(from_folder)
        target = self.get_folder(to_folder)
        if source is None or target is None:
            raise ValueError("source or target folder does not exist")
        file = next((f for f in source.files if f.path == path), None)
        if file is None:
            raise ValueError(f"file '{path}' not found in folder '{from_folder}'")
        source.remove_file(path)
        target.add_file(file)
        self.save_to_settings()

    def set_file_hash(self, path: str, file_hash: str) -> None:
        """Attach a freshly computed hash to a file and persist it.

        Called by the background hash worker once it has read the volume, so the
        segmentation indicator can be evaluated without re-reading the file.
        """
        for folder in self.folders:
            for file in folder.files:
                if file.path == path:
                    file.file_hash = file_hash
                    self.save_to_settings()
                    return

    @staticmethod
    def _restore_file(file_data: dict) -> FileInfo | None:
        """Reconstruct a FileInfo from storage, reusing the cached hash if valid."""
        path = file_data["path"]
        try:
            stat = os.stat(path)
        except OSError:
            logger.info(f"pruning stale file {path}")
            return None
        cached_hash = file_data.get("file_hash")
        if (
            cached_hash
            and file_data.get("mtime_ns") == stat.st_mtime_ns
            and file_data.get("size") == stat.st_size
        ):
            return FileInfo(path, file_hash=cached_hash)
        return FileInfo(path)


class FileSelectionModel:
    """
    Wrapper over the folder-based storage used by the file page.

    Owns the StateManager and the FolderManager, which is now the single source of
    truth for stored scans.
    """

    def __init__(self, settings: StateManager | None = None) -> None:
        self.settings: StateManager = settings or StateManager()
        self._folders: FolderManager = FolderManager(self.settings)

    def get_folders(self) -> list[Folder]:
        return self._folders.folders

    def add_folder(self, name: str) -> None:
        self._folders.add_folder(name)

    def rename_folder(self, old_name: str, new_name: str) -> None:
        self._folders.rename_folder(old_name, new_name)

    def delete_folder(self, name: str) -> None:
        self._folders.delete_folder(name)

    def add_file_to_folder(self, folder_name: str, path: str) -> None:
        self._folders.add_file_to_folder(folder_name, path)

    def move_file(self, path: str, from_folder: str, to_folder: str) -> None:
        self._folders.move_file(path, from_folder, to_folder)

    def set_file_hash(self, path: str, file_hash: str) -> None:
        self._folders.set_file_hash(path, file_hash)

    # --- legacy flat-path API ---

    def get_all_paths(self) -> list[FileInfo]:
        """Flatten all files across folders, mirroring the old path list."""
        return [f for folder in self._folders.folders for f in folder.files]

    def insert_path(self, path: str) -> None:
        """Legacy entry point: add a file to the default folder."""
        if self._folders.get_folder(DEFAULT_FOLDER_NAME) is None:
            self._folders.add_folder(DEFAULT_FOLDER_NAME)
        self._folders.add_file_to_folder(DEFAULT_FOLDER_NAME, path)
