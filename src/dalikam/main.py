import sys
from PyQt6.QtWidgets import QApplication
from dalikam.ui.landingPage.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    with open("src/dalikam/style.qss", "r") as f:
        _style = f.read()
        app.setStyleSheet(_style)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
