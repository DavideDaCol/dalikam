import os
from functools import partial
from pathlib import Path

import nibabel as nib
from PyQt6.QtCore import QObject, QThread, pyqtSignal

from dalikam.backend.segmentation import build_hash
from dalikam.router.router import Router
from dalikam.ui.filePage.fileModel import FileInfo, FileSelectionModel


class FileHashWorker(QObject):
    """
    Computes content hashes for scans that were never hashed before.

    Hashing reads the entire volume so it runs off the UI thread. 
    Each completed hash is emitted so the view can refresh the
    segmentation indicator without re-reading the file.
    """

    file_hashed: pyqtSignal = pyqtSignal(str, str)
    finished: pyqtSignal = pyqtSignal()

    def __init__(self, paths: list[str]) -> None:
        super().__init__()
        self._paths = paths

    def run(self) -> None:
        for path in self._paths:
            try:
                digest = build_hash(Path(path))
            except OSError:
                # skip the file
                continue
            self.file_hashed.emit(path, digest)
        self.finished.emit()


class FileViewModel(QObject):
    folders_updated: pyqtSignal = pyqtSignal(list)
    file_hash_updated: pyqtSignal = pyqtSignal(str, str)

    def __init__(self, model: FileSelectionModel, router: Router) -> None:
        super().__init__()
        self._model: FileSelectionModel = model
        self._router: Router = router 
        self._hash_thread: QThread | None = None
        self._hash_worker: FileHashWorker | None = None

    # ---- PATH VALIDATION ----

    def path_validity_check(self, path: str) -> bool:
        return os.path.exists(path)

    # ---- ROUTING ----

    def file_chosen(self, context: FileInfo | None = None) -> None:
        print("file has been chosen, starting viewer...")
        self._router.navigate("viewer", context)

    def go_back(self) -> None:
        self._router.navigate("landing")

    # ---- FOLDER OPERATIONS ----

    def add_folder(self, name: str) -> None:
        name = name.strip()
        if not name:
            return
        self._model.add_folder(name)
        self.page_refresh()

    def rename_folder(self, old_name: str, new_name: str) -> None:
        new_name = new_name.strip()
        if not new_name or new_name == old_name:
            return
        self._model.rename_folder(old_name, new_name)
        self.page_refresh()

    def delete_folder(self, name: str) -> None:
        self._model.delete_folder(name)
        self.page_refresh()

    def add_file_to_folder(self, folder_name: str, path: str) -> None:
        self._model.add_file_to_folder(folder_name, path)
        self.page_refresh()

    def move_file(self, path: str, from_folder: str, to_folder: str) -> None:
        self._model.move_file(path, from_folder, to_folder)
        self.page_refresh()

    # ---- FILE OPERATIONS ----

    def set_file_hash(self, path: str, file_hash: str) -> None:
        self._model.set_file_hash(path, file_hash)

    def segmentation_present(self, file: FileInfo) -> bool:
        """Check whether a segmentation already exists for a file.

        Relies on the cached content hash; if the hash was never computed the
        indicator reports "not segmented" until the background worker fills it
        in and emits `file_hash_updated`.
        """
        if file.file_hash is None:
            return False
        return self._model.settings.get_sm_files().get(file.file_hash) is not None

    def ensure_hashes(self) -> None:
        """Launch background hashing for scans that still miss a content hash."""
        if self._hash_thread is not None and self._hash_thread.isRunning():
            return
        pending = [f.path for f in self._model.get_all_files() if f.file_hash is None]
        if not pending:
            return

        self._hash_thread = QThread(self)
        worker = FileHashWorker(pending)
        # Keep a class reference to avoid garbage collection
        self._hash_worker = worker
        worker.moveToThread(self._hash_thread)
        self._hash_thread.started.connect(worker.run)
        worker.file_hashed.connect(self._on_file_hashed)
        worker.finished.connect(self._hash_thread.quit)
        worker.finished.connect(worker.deleteLater)
        # Bind the specific thread object so a stale finished signal can never
        # tear down a thread that replaced it in the meantime
        self._hash_thread.finished.connect(partial(self._on_hash_thread_finished, self._hash_thread))
        self._hash_thread.start()

    def _on_file_hashed(self, path: str, digest: str) -> None:
        self.set_file_hash(path, digest)
        self.file_hash_updated.emit(path, digest)

    def _on_hash_thread_finished(self, thread: QThread) -> None:
        if self._hash_thread is thread:
            self._hash_thread = None
        self._hash_worker = None
        thread.deleteLater()

    def get_file_metadata(self, file: FileInfo) -> dict:
        """Collect display metadata for the info panel.

        NIfTI dimensions and voxel spacing come from the header only
        (nibabel loads it lazily), so this stays cheap even for large scans.
        """
        try:
            image = nib.load(file.path)
            dimensions = tuple(image.shape)
            voxel_size = tuple(image.header.get_zooms())
        except Exception:
            dimensions, voxel_size = None, None

        return {
            "name": file.name,
            "path": file.path,
            "size": file.size,
            "created": file.creation_date,
            "modified": file.last_mod_date,
            "dimensions": dimensions,
            "voxel_size": voxel_size,
            "segmented": self.segmentation_present(file),
        }

    # ---- VIEW REFRESH ----

    def page_refresh(self) -> None:
        self.folders_updated.emit(self._model.get_folders())
