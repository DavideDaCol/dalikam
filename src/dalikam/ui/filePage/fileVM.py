import os

from PyQt6.QtCore import QObject, pyqtSignal

from dalikam.router.router import Router
from dalikam.ui.filePage.fileModel import FileInfo, FileSelectionModel

class FileViewModel(QObject):
    no_saved_paths: pyqtSignal = pyqtSignal()
    paths_available: pyqtSignal = pyqtSignal(list)

    def __init__(self, model: FileSelectionModel, router: Router) -> None:
        super().__init__()
        self._model: FileSelectionModel = model
        self._router: Router = router 

    def path_validity_check(self,path: str) -> bool:
            return os.path.exists(path)
    
    def path_list_update(self, path: str) -> None:
        self._model.insert_path(path)
        self.page_loaded()

    def file_chosen(self, context: FileInfo | None = None) -> None:
        print("file has been chosen, starting viewer...")
        self._router.navigate("viewer", context)

    def page_loaded(self):
        paths = self._model.get_all_paths()
        if len(paths) == 0:
            self.no_saved_paths.emit()
        else:
            self.paths_available.emit(paths)