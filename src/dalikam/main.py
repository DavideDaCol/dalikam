import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from dalikam.tools.utils import get_root
from dalikam.ui.landingPage.main_window import MainWindow

def main():
    style_path = Path(__file__).parent / "style.qss"
    logo_path = get_root() / "assets" / "icon.png"
    app = QApplication(sys.argv)
    with open(style_path, "r") as f:
        _style = f.read()
        app.setStyleSheet(_style)
    window = MainWindow()
    window.setWindowIcon(QIcon(str(logo_path)))
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
