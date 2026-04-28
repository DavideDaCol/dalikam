from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel

class viewerView(QWidget):

    def __init__(self) -> None:
        super().__init__()
        title = QLabel("viewer page")
        title.setStyleSheet("color: #000000;")
        layout = QVBoxLayout()
        layout.addWidget(title)
        self.setLayout(layout)
