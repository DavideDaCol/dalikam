from pathlib import Path

from PyQt6.QtCore import QSettings


class StateManager(object):
    """
        Persistent state manager module. Allows to store information on persistent storage to retrieve
        it after exiting the application. Supplies custom modules to manipulate the stored info in a
        programmatic way.

        Attributes:
            settings: a QSettings object, which creates or connects to a permanent storage file
    """

    def __init__(self):
        self.settings = QSettings("DavideDaCol", "dalikam")
        print("contents of SM_unique_files: ")
        for el in self.settings.value("SM_unique_files", []):
            print(el[0])

    def clear(self) -> None:
        """Completely clears all the saved objects"""
        self.settings.clear()

    def get_sm_files(self) -> dict[str, Path]:
        """Returns the map containing the files that have already been segmented by Dalikam"""
        return self.settings.value(
            "SM_unique_files", {}, dict
        )

    def update_sm_files(self, key, value) -> None:
        """Adds a new file to the segmentation map once inference is completed"""
        old_files = self.get_sm_files()
        old_files.update({key: value})
        self.settings.setValue("SM_unique_files", old_files)

    def get_raw_files(self):
        """Returns all saved paths to raw OCT scans"""
        return self.settings.value("paths", [], list)

    def set_raw_files(self, paths: list[str]) -> None:
        """Sets list of paths as the list of saved OCT paths"""
        self.settings.setValue("paths", paths)
