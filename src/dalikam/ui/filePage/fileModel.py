from datetime import date, datetime
import os
from typing import cast
from PyQt6.QtCore import QSettings

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
        self.known_paths: QSettings = QSettings("DavideDaCol","Dalikam")

    """
    returns all currently stored paths. 
    Paths are persistent: they are remembered even if the user closes the app.
    """
    def get_all_paths(self) -> list[FileInfo]:
        # TODO anything cleaner than this cast? It shouldn't fail on its own but it's ugly
        return cast(list[FileInfo], self.known_paths.value("paths", [], list))

    """
    saves the given `path` in the `known_paths` data structure.
    Paths are assumed to be absolute with respect to the root file system.
    """
    def insert_path(self, path: str):
        
        current_paths: list[FileInfo] = self.get_all_paths()

        # Avoid duplicate paths
        for file in current_paths:
            if file.path == path:
                current_paths.remove(file)

        new_info = FileInfo(path)
        current_paths.insert(0, new_info)
        # Keeps only the 5 most recent file paths
        current_paths = current_paths[:5]

        self.known_paths.setValue("paths", current_paths)