from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar


SPINNER_CHARS = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"


class LoadingOverlay(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("background-color: #1e1f22;")
        self.setVisible(False)

        layout = QVBoxLayout()
        self.setLayout(layout)

        self._spinner_index = 0
        self._spinner = QLabel(SPINNER_CHARS[0])
        self._spinner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._spinner.setStyleSheet("font-size: 48pt; color: #d5d5d5; background: transparent;")

        self._message = QLabel("Loading scan...")
        self._message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._message.setStyleSheet("font-size: 18pt; color: #d5d5d5; background: transparent;")

        self._progress = QProgressBar()
        self._progress.setRange(0, 0)
        self._progress.setFixedWidth(400)
        self._progress.setFixedHeight(6)
        self._progress.setTextVisible(False)
        self._progress.setStyleSheet("""
            QProgressBar { background-color: #0d0d0c; border-radius: 3px; border: none; }
            QProgressBar::chunk { background-color: #9ac3fe; border-radius: 3px; }
        """)

        layout.addStretch()
        layout.addWidget(self._spinner, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addSpacing(16)
        layout.addWidget(self._message, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addSpacing(24)
        layout.addWidget(self._progress, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.setInterval(80)

    def _tick(self):
        self._spinner_index = (self._spinner_index + 1) % len(SPINNER_CHARS)
        self._spinner.setText(SPINNER_CHARS[self._spinner_index])

    def set_message(self, msg: str):
        self._message.setText(msg)

    def set_progress(self, value: int, maximum: int = 100):
        self._progress.setRange(0, maximum)
        self._progress.setValue(value)

    def set_indeterminate(self, enabled: bool = True):
        self._progress.setRange(0, 0 if enabled else 100)

    def show(self):
        self._timer.start()
        if self.parent():
            self.resize(self.parent().size())
        self.setVisible(True)
        self.raise_()

    def hide(self):
        self._timer.stop()
        self.setVisible(False)

    def resizeEvent(self, event):
        if self.parent():
            self.resize(self.parent().size())
        super().resizeEvent(event)
