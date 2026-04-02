from PyQt6.QtWidgets import QMainWindow, QStackedWidget
from dalikam.router.router import Router
from dalikam.ui.landingPage.landingView import LandingPage
from dalikam.ui.landingPage.landingViewModel import landingVM
from dalikam.ui.landingPage.landingModel import LandingModel
from dalikam.ui.filePage.fileView import FileSelectionView

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dalikam")
        self.setGeometry(700,300,800,600)
        self._landingModel: LandingModel = LandingModel()
        self._navigator: Router = Router()
        self.landingViewModel: landingVM = landingVM(self._landingModel, self._navigator) 

        self._navigator.routeChange.connect(self.change_page)

        hero_section = LandingPage(self.landingViewModel)
        file_selection = FileSelectionView()

        self.main_container: QStackedWidget = QStackedWidget()
        _ = self.main_container.addWidget(hero_section)
        _ = self.main_container.addWidget(file_selection)
        self.setCentralWidget(self.main_container)

    def change_page(self, index: int):
        print(f"got page navigation event, switching to index {index}")
        self.main_container.setCurrentIndex(index)