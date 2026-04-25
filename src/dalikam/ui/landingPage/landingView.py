from typing import override
from dalikam.ui.landingPage.landingVM import landingVM
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QLabel, QPushButton, QStackedLayout, QVBoxLayout, QHBoxLayout, QWidget
from PyQt6.QtGui import QPaintEvent, QPainter, QPixmap


class BackgroundWidget(QWidget):
    """
    Used to implement more robust background manipulation features;
    practically a wrapper for QPixmap.

    Attributes
    ----------
    path: str
        path to the background image
    """

    def __init__(self, path: str):
        super().__init__()
        self.bg: QPixmap = QPixmap(path)

    @override
    # This method is used to scale the background in a sane way.
    # It replicates the behavior of CSS cover by running whenever the paintEvent is emitted,
    # the image is cropped if the window is too small in any dimension.
    def paintEvent(self, a0: QPaintEvent | None) -> None:
        painter = QPainter(self)

        # Get the aspect ratio of the background after the window resize
        bg_scaled = self.bg.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation
        )

        # Calculate where the center of the background is after the resize
        anchor_x = (bg_scaled.width() - self.width()) // 2
        anchor_y = (bg_scaled.height() - self.height()) // 2

        # Draw the new pixmap in the middle, clip the edges if the window is small
        painter.drawPixmap(0,0,bg_scaled,anchor_x,anchor_y, self.width(), self.height())

class LandingPage(QWidget):
    """
    The hero section of the application: serves as the first screen the user sees and
    allows to move to other pages. 
    """

    def __init__(self, vm: landingVM):
        super().__init__()
        self._viewmodel: landingVM = vm

        # connect the slots from the viewModel to the view
        self._viewmodel.settingsAvailable.connect(self.printSettings)

        background = BackgroundWidget(path="./assets/bg.png")

        menu_layer = QVBoxLayout()

        title = QLabel("Dalikam")
        title.setObjectName("mainTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        button_layer = QHBoxLayout()
        # TODO move these magic numbers to a const or similar solutions
        button_layer.setSpacing(20)

        file_btn = QPushButton("start")
        settings_btn = QPushButton("settings")
        exit_btn = QPushButton("exit")

        _ = settings_btn.clicked.connect(self._viewmodel.debug_btn_press)
        _ = file_btn.clicked.connect(self._viewmodel.start_clicked)
        exit_btn.clicked.connect(QApplication.quit)

        button_layer.addWidget(file_btn)
        button_layer.addWidget(settings_btn)
        button_layer.addWidget(exit_btn)

        menu_layer.addStretch()
        menu_layer.addWidget(title)
        menu_layer.addLayout(button_layer)
        menu_layer.addStretch()

        menu_layer.setSpacing(10)
        menu_layer.setContentsMargins(50, 50, 50, 50)

        menu_widget = QWidget()
        menu_widget.setLayout(menu_layer)

        top_layer = QStackedLayout()
        top_layer.setStackingMode(QStackedLayout.StackingMode.StackAll)

        # TODO figure out if the assignment is absolutely necessary
        _ = top_layer.addWidget(background)
        _ = top_layer.addWidget(menu_widget)

        self.setLayout(top_layer)

    def printSettings(self, settings: dict[str,str]):
        print(f"in the view settings were received as: {settings}")