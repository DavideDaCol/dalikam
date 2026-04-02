from PyQt6.QtWidgets import QMainWindow
from dalikam.ui.landingPage.landingView import LandingPage
from dalikam.ui.landingPage.landingViewModel import landingVM
from dalikam.ui.landingPage.landingModel import landingModel

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dalikam")
        self.setGeometry(700,300,800,600)
        self._landingModel: landingModel = landingModel()
        self.landingViewModel: landingVM = landingVM(self._landingModel) 

        widget = LandingPage(self.landingViewModel)
        self.setCentralWidget(widget)