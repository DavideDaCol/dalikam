import logging
import os
from datetime import date, datetime

from dalikam.backend.state import StateManager

logger = logging.getLogger(__name__)


class FileInfo:
    path: str
    name: str
    creation_date: date
    last_mod_date: date

    def __init__(self, path: str):
        self.path = path
        self.name = os.path.basename(self.path)
        self.creation_date = datetime.fromtimestamp(os.stat(self.path).st_ctime)
        self.last_mod_date = datetime.fromtimestamp(os.stat(self.path).st_mtime)


class FileSelectionModel:
    """
    Model for the File Selection page.

    If a user decides to open a .nii.gz file from the OS's file explorer, the path
    to that file will be saved in a persistent data structure called `known_paths`.
    The user will be able to then retrieve the file if needed; paths are presumed to
    be absolute.
    """

    def __init__(self) -> None:
        # Initialize persistent storage of known .nii.gz file paths
        self.settings: StateManager = StateManager()

    """
    returns all currently stored paths. 
    Paths are persistent: they are remembered even if the user closes the app.
    """

    def get_all_paths(self) -> list[FileInfo]:

        old_paths: list[str] = self.settings.get_raw_files()
        valid_paths: list[FileInfo] = []
        new_paths: list[str] = []

        # Check if stored paths still exist
        for path in old_paths:
            if os.path.exists(path):
                valid_paths.append(FileInfo(path))
                new_paths.append(path)
            else:
                logger.info(f"deleting old path {path}")

        if len(old_paths) != len(new_paths):
            self.settings.set_raw_files(new_paths)

        return valid_paths

    """
    saves the given `path` in the `known_paths` data structure.
    Paths are assumed to be absolute with respect to the root file system.
    """

    def insert_path(self, path: str):

        current_paths: list[str] = self.settings.get_raw_files()

        # Avoid duplicate paths
        if path in current_paths:
            current_paths.remove(path)

        current_paths.insert(0, path)
        # Keeps only the 5 most recent file paths
        current_paths = current_paths[:5]

        self.settings.set_raw_files(current_paths)
