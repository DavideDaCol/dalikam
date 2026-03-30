from PyQt6.QtWidgets import QMainWindow
from dalikam.presentation.view.landingView import LandingPage
from dalikam.presentation.viewmodel.landingViewModel import landingVM

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dalikam")
        self.setGeometry(700,300,800,600)
        self.landingViewModel: landingVM = landingVM() 

        widget = LandingPage(self.landingViewModel)
        self.setCentralWidget(widget)