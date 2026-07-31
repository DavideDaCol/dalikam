import os

from PyQt6.QtCore import QObject, pyqtSignal

from dalikam.router.router import Router
from dalikam.ui.filePage.fileModel import FileInfo, FileSelectionModel


class FileViewModel(QObject):
    no_saved_paths: pyqtSignal = pyqtSignal()
    paths_available: pyqtSignal = pyqtSignal(list)
    folders_updated: pyqtSignal = pyqtSignal(list)

    def __init__(self, model: FileSelectionModel, router: Router) -> None:
        super().__init__()
        self._model: FileSelectionModel = model
        self._router: Router = router 

    # ---- PATH UPDATES ----

    def path_validity_check(self,path: str) -> bool:
            return os.path.exists(path)
    
    def path_list_update(self, path: str) -> None:
        self._model.insert_path(path)
        self.page_refresh()

    # --- FOLDER OPERATIONS ---

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

    # ---- FILE OPERATIONS

    def set_file_hash(self, path: str, file_hash: str) -> None:
        self._model.set_file_hash(path, file_hash)

    def segmentation_present(self, file: FileInfo) -> bool:
        """Check whether a segmentation already exists for a file.

        Relies on the cached content hash; if the hash was never computed the
        indicator simply reports "not segmented" until the worker fills it in.
        """
        if file.file_hash is None:
            return False
        return self._model.settings.get_sm_files().get(file.file_hash) is not None

    # ---- ROUTING OPERATIONS ----

    def file_chosen(self, context: FileInfo | None = None) -> None:
        print("file has been chosen, starting viewer...")
        self._router.navigate("viewer", context)

    def page_refresh(self):
        paths = self._model.get_all_paths()
        if len(paths) == 0:
            self.no_saved_paths.emit()
        else:
            self.paths_available.emit(paths)
        self.folders_updated.emit(self._model.get_folders())
