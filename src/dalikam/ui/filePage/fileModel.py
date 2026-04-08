from typing import cast
from PyQt6.QtCore import QSettings

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
    def get_all_paths(self) -> list[str]:
        # TODO anything cleaner than this cast? It shouldn't fail on its own but it's ugly
        return cast(list[str], self.known_paths.value("paths", [], list))

    """
    saves the given `path` in the `known_paths` data structure.
    Paths are assumed to be absolute with respect to the root file system.
    """
    def insert_path(self, path: str):
        
        current_paths: list[str] = self.get_all_paths()

        # Avoid duplicate paths
        if path in current_paths:
            current_paths.remove(path)

        current_paths.insert(0, path)
        # Keeps only the 5 most recent file paths
        current_paths = current_paths[:5]

        self.known_paths.setValue("paths", current_paths)