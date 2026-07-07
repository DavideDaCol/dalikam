import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication
from dalikam.ui.landingPage.main_window import MainWindow

def main():
    style_path = Path(__file__).parent / "style.qss"
    app = QApplication(sys.argv)
    with open(style_path, "r") as f:
        _style = f.read()
        app.setStyleSheet(_style)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
