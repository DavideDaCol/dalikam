from typing import override
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget, QVBoxLayout
from PyQt6.QtGui import QShowEvent
from PyQt6.QtCore import Qt
from dalikam.ui.filePage.fileVM import FileViewModel

class FileSelectionView(QWidget):
    def __init__(self, vm: FileViewModel):
        super().__init__()
        self._viewmodel: FileViewModel = vm
        self.setObjectName("filePage")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._viewmodel.no_saved_paths.connect(self.empty_path_list)

        layout = QVBoxLayout()

        title = QLabel("Select file")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.path_layout: QVBoxLayout = QVBoxLayout()

        btn_row = QHBoxLayout()
        back_btn = QPushButton("Back")
        open_btn = QPushButton("Open")
        btn_row.addWidget(back_btn)
        btn_row.addWidget(open_btn)

        layout.addWidget(title)
        layout.addLayout(self.path_layout)
        layout.addStretch()
        layout.addLayout(btn_row)

        self.setLayout(layout)

    @override
    def showEvent(self, a0: QShowEvent | None) -> None:
        self._viewmodel.page_loaded()

    def empty_path_list(self) -> None:
        self.path_layout.addWidget(QLabel("no files saved"))
