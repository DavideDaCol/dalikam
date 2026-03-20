from PyQt6.QtWidgets import QMainWindow
from dalikam.presentation.view.landingView import LandingPage

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dalikam")
        self.setGeometry(700,300,800,600)

        widget = LandingPage()
        self.setCentralWidget(widget)