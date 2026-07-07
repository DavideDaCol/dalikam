import os
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

    # TODO this function is at best unnecessary and at worst dangerous.
    # TODO it can remove a segmentation even if the file is only renamed or moved.
    # TODO does it matter if we keep an extra file?
    def remove_segmentations(self) -> None:
        """Scans the segmentation folder to check if the files still exist."""
        # Get old saved values from persistent data structure
        res = self.get_sm_files()
        if res is not None:
            old_paths: dict[str, Path] = res

            valid_paths: dict[str, Path] = {}

            # Check if stored paths still exist
            for sm_path in old_paths:
                key_val = old_paths.get(sm_path)
                if key_val is not None and os.path.exists(key_val):
                    valid_paths.update({sm_path: key_val})

            # Update map if paths have been removed
            if len(old_paths) != len(valid_paths):
                self.settings.setValue("SM_unique_files", valid_paths)
