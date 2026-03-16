from PyQt6.QtWidgets import QMainWindow, QLabel, QVBoxLayout
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtCore import Qt

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dalikam")
        self.setGeometry(700,300,800,600)
        self.loadLabel()

    def loadLabel(self):
        label = QLabel(self)
        font = label.font()
        font.setPointSize(40)
        label.setFont(font)
        label.setText("<font color=blue>Dalikam</font>")
        label.setAutoFillBackground(True)
        palette = QPalette()
        palette.setColor(QPalette.ColorGroup.Active,QPalette.ColorRole.Window,QColor(18,19,20,255))
        label.setPalette(palette)
        label.setAlignment(
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter
        )
        self.setCentralWidget(label)