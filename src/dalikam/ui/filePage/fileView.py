from typing import override
from functools import partial
from PyQt6.QtWidgets import QFileDialog, QHBoxLayout, QLabel, QMessageBox, QPushButton, QWidget, QVBoxLayout
from PyQt6.QtGui import QMouseEvent, QShowEvent
from PyQt6.QtCore import Qt, pyqtSignal
from dalikam.ui.filePage.fileModel import FileInfo
from dalikam.ui.filePage.fileVM import FileViewModel

class FileEntryWidget(QWidget):
    clicked: pyqtSignal = pyqtSignal()

    def __init__(self, file: FileInfo):
        super().__init__()
        self.file: FileInfo = file

        layout = QHBoxLayout(self)

        icon_placeholder = QLabel("icon")
        file_name = QLabel(file.name)
        file_path = QLabel(file.path)
        file_mod_date = QLabel(f"{file.last_mod_date}")
        file_creat_date = QLabel(f"{file.creation_date}")

        layout.addWidget(icon_placeholder)
        layout.addWidget(file_name)
        layout.addStretch()
        layout.addWidget(file_path)
        layout.addStretch()
        layout.addWidget(file_mod_date)
        layout.addWidget(file_creat_date)

    @override
    def mousePressEvent(self, a0: QMouseEvent | None):
        self.clicked.emit()
        super().mousePressEvent(a0)

class FileSelectionView(QWidget):
    def __init__(self, vm: FileViewModel):
        super().__init__()
        self._viewmodel: FileViewModel = vm
        self.setObjectName("filePage")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._viewmodel.no_saved_paths.connect(self.empty_path_list)
        self._viewmodel.paths_available.connect(self.fill_paths)

        layout = QVBoxLayout()

        title = QLabel("Select file")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.path_layout: QVBoxLayout = QVBoxLayout()

        btn_row = QHBoxLayout()
        back_btn = QPushButton("Back")
        open_btn = QPushButton("New File")
        open_btn.clicked.connect(self.path_navigation_request)
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

    def path_navigation_request(self) -> None:
        selection_result = QFileDialog.getOpenFileName(self, "Choose a file", "/home", "Imaging Files (*.nii *.nii.gz)")
        new_file = selection_result[0]
        print(f"selected file: {new_file}")
        if new_file:
            if self._viewmodel.path_validity_check(new_file):
                self._viewmodel.path_list_update(new_file)
            else:
                error_box = QMessageBox(self)
                error_box.setIcon(QMessageBox.Icon.Warning)
                error_box.setText("Path is not valid")
                error_box.setInformativeText(f"the selected path '{new_file}' does not seem to exist.")
                res = error_box.exec()
                print(f"exit status {res}")

    def empty_path_list(self) -> None:
        self.path_layout.addWidget(QLabel("no files saved"))

    def file_factory(self, file: FileInfo) -> QHBoxLayout:
        file_entry = QHBoxLayout()
        icon_placeholder = QLabel("icon")
        file_name = QLabel(file.name)
        file_path = QLabel(file.path)
        file_mod_date = QLabel(f"{file.last_mod_date}")
        file_creat_date = QLabel(f"{file.creation_date}")

        file_entry.addWidget(icon_placeholder)
        file_entry.addWidget(file_name)
        file_entry.addStretch()
        file_entry.addWidget(file_path)
        file_entry.addStretch()
        file_entry.addWidget(file_mod_date)
        file_entry.addWidget(file_creat_date)

        return file_entry

    def fill_paths(self, file_info: list[FileInfo]) -> None:
        for i in reversed(range(self.path_layout.count())):
            item = self.path_layout.takeAt(i)
            if item is not None:
                inner_widget = item.widget()
                if inner_widget is not None:
                    inner_widget.deleteLater()
                    
        for file in file_info:
            entry_widget = FileEntryWidget(file)

            print(f"making entry widget with path {file.path}")

            entry_widget.clicked.connect(partial(self._viewmodel.file_chosen, file))

            self.path_layout.addWidget(entry_widget)
