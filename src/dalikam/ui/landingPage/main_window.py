from sqlite3 import Connection
from PyQt6.QtWidgets import QMainWindow, QStackedWidget
from dalikam.router.router import Router
from dalikam.ui.landingPage.landingView import LandingPage
from dalikam.ui.landingPage.landingVM import landingVM
from dalikam.ui.landingPage.landingModel import LandingModel
from dalikam.ui.filePage.fileView import FileSelectionView
from dalikam.ui.filePage.fileModel import FileSelectionModel
from dalikam.ui.filePage.fileVM import FileViewModel

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dalikam")
        self.setGeometry(700,300,800,600)

        # Initialize all models
        self._landingModel: LandingModel = LandingModel()
        self._fileModel: FileSelectionModel = FileSelectionModel()

        # Initialize app page router
        self._router: Router = Router()

        # Initialize all view models
        self.landingViewModel: landingVM = landingVM(self._landingModel, self._router) 
        self.fileViewModel: FileViewModel = FileViewModel(self._fileModel, self._router)

        _ = self._router.routeChange.connect(self.change_page)

        # Initialize all views
        hero_section = LandingPage(self.landingViewModel)
        file_selection = FileSelectionView(self.fileViewModel)

        # Create the main container of the app
        self.main_container: QStackedWidget = QStackedWidget()
        _ = self.main_container.addWidget(hero_section)
        _ = self.main_container.addWidget(file_selection)
        self.setCentralWidget(self.main_container)

    def change_page(self, index: int):
        print(f"got page navigation event, switching to index {index}")
        self.main_container.setCurrentIndex(index)