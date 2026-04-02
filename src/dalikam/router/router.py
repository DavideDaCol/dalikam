from PyQt6.QtCore import QObject, pyqtSignal

class Router(QObject):
    routeChange: pyqtSignal = pyqtSignal(int)

    def __init__(self) -> None:
        super().__init__()

        self.page_stack: list[int] = []
        self.page_names: dict[str,int] = {}
        self.register_routes()

    def register_routes(self):
        self.page_names.update({
            "landing": 0,
            "file": 1 
        })

    def register_route(self, name: str, index: int):
        self.page_names.update({name: index})

    def navigate(self, page: str):
        index = self.page_names[page]
        print(f"navigating to page {page} with index {index}")
        self.page_stack.append(index)
        self.routeChange.emit(index)
