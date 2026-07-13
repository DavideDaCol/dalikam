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

    def delete_sm_files(self) -> None:
        """
            removes all saved segmentation paths. This does not remove the files themselves, just the path. File
            deletion is handled by the settings model.
        """
        self.settings.remove("SM_unique_files")

    def get_raw_files(self):
        """Returns all saved paths to raw OCT scans"""
        return self.settings.value("paths", [], list)

    def set_raw_files(self, paths: list[str]) -> None:
        """Sets list of paths as the list of saved OCT paths"""
        self.settings.setValue("paths", paths)

    def delete_raw_files(self) -> None:
        """removes all saved paths to OCR scans."""
        self.settings.remove("paths")

    def set_preferred_device(self, device):
        """"saves the preferred inference device (CPU, CUDA, MPS)."""
        self.settings.setValue("preferred_device", device)

    def get_preferred_device(self) -> str:
        """Returns the user's inference device. CPU by default"""
        return self.settings.value("preferred_device", "cpu", str)

    def set_model_path(self, model_type: str, path: str) -> None:
        """Saves the absolute path to a loaded model directory for a given model type"""
        self.settings.setValue(f"model_path_{model_type}", path)

    def get_model_path(self, model_type: str) -> str:
        """Returns the saved path for a model type, or empty string if none"""
        return self.settings.value(f"model_path_{model_type}", "", str)

    def delete_model_path(self, model_type: str) -> None:
        """
            removes all saved model weight paths. This does not remove the files themselves, just the path. File
            deletion is handled by the settings model.
        """
        self.settings.remove(f"model_path_{model_type}")

    def get_preferred_model_type(self) -> str:
        """Returns the saved preference for weights"""
        return self.settings.value("preferred_model_type", "", str)

    def set_preferred_model_type(self, model_type: str) -> None:
        """Saves the user's preference for inference model."""
        self.settings.setValue("preferred_model_type", model_type)
