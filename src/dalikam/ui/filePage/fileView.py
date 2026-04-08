import typing
from typing import override
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QWidget, QVBoxLayout
from PyQt6.QtGui import QShowEvent
from dalikam.ui.filePage.fileVM import FileViewModel

class FileSelectionView(QWidget):
    def __init__(self, vm: FileViewModel):
        super().__init__()
        self._viewmodel: FileViewModel = vm

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(QLabel("file selection page"))

        self.setLayout(layout)

    @override
    def showEvent(self, a0: QShowEvent | None) -> None:
        self._viewmodel.page_loaded()
