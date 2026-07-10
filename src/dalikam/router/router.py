from PyQt6.QtCore import QObject, pyqtSignal

from dalikam.ui.filePage.fileModel import FileInfo

class Router(QObject):
    routeChange: pyqtSignal = pyqtSignal(int, object)

    def __init__(self) -> None:
        super().__init__()

        self.page_stack: list[int] = []
        self.page_names: dict[str,int] = {}
        self.register_routes()

    def register_routes(self):
        self.page_names.update({
            "landing": 0,
            "file": 1,
            "viewer": 2,
            "settings": 3
        })

    def get_registered_routes(self) -> dict[str,int]:
        return self.page_names

    def navigate(self, page: str, context: FileInfo | None = None):
        index = self.page_names[page]
        print(f"navigating to page {page} with index {index}")
        self.page_stack.append(index)
        self.routeChange.emit(index, context)
