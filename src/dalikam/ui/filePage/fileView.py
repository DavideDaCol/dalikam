from functools import partial
from typing import override

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QFontMetrics, QIcon, QMouseEvent, QPixmap, QShowEvent
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from dalikam.tools.utils import get_root
from dalikam.ui.filePage.fileModel import DEFAULT_FOLDER_NAME, FileInfo, Folder
from dalikam.ui.filePage.fileVM import FileViewModel

DATE_FORMAT = "%d %b %Y %H:%M"

SEGMENTED_COLOR = "#4ade80"
UNSEGMENTED_COLOR = "#6b7280"

NAME_COLUMN_WIDTH = 180
SEGMENT_TEXT_WIDTH = 270


def format_size(num: int) -> str:
    """Human-readable byte count, e.g. 1536 -> '1.5 KB'."""
    value = float(num)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024:
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} PB"


def _asset_pixmap(name: str, size: int) -> QPixmap:
    """Load an asset icon from the assets folder, scaled to ``size`` px."""
    path = get_root() / "assets" / name
    if not path.exists():
        return QPixmap()
    return QPixmap(str(path)).scaled(
        size,
        size,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )


class FileRowWidget(QWidget):
    """
    Visual representation of an OCT file entry in the file explorer.
    Contains segmentation indicator, scan name and action buttons.

    Clicking the row (or the file name) opens the file in the viewer.
    """

    clicked: pyqtSignal = pyqtSignal()
    info_requested: pyqtSignal = pyqtSignal(object)
    move_requested: pyqtSignal = pyqtSignal(object)

    def __init__(self, file: FileInfo, segmented: bool) -> None:
        super().__init__()
        self.file: FileInfo = file
        self.setObjectName("fileRow")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self._seg_label = QLabel()
        self._seg_label.setObjectName("segIndicator")

        self._seg_text = QLabel()
        self._seg_text.setObjectName("segText")

        icon_label = QLabel()
        icon_label.setPixmap(_asset_pixmap("icon.png", 24))

        title = file.name
        while "." in title:
            title = title.rsplit(".", 1)[0]
        if len(title) > 25:
            title = title[:24] + "…"

        self._name = QLabel(title)
        self._name.setObjectName("fileName")
        self._name.setToolTip(file.path)

        # Both the name column and the status text use fixed widths, so the
        # three groups have identical extents on every row. The equal stretch
        # items then distribute the leftover space evenly.
        self._name.setFixedWidth(NAME_COLUMN_WIDTH)
        self._name.setText(
            QFontMetrics(self._name.font()).elidedText(
                title, Qt.TextElideMode.ElideRight, NAME_COLUMN_WIDTH
            )
        )
        self._seg_text.setFixedWidth(SEGMENT_TEXT_WIDTH)

        info_btn = QPushButton()
        info_btn.setObjectName("iconButton")
        info_btn.setIcon(QIcon(_asset_pixmap("info_icon.png", 24)))
        info_btn.setIconSize(QSize(24, 24))
        info_btn.setToolTip("Show detailed file information")
        move_btn = QPushButton("Change folder")
        move_btn.setObjectName("rowButton")
        move_btn.setToolTip("Move to another folder")

        info_btn.clicked.connect(lambda: self.info_requested.emit(self.file))
        move_btn.clicked.connect(lambda: self.move_requested.emit(self.file))

        move_btn.setFixedHeight(32)
        info_btn.setFixedHeight(32)

        layout.addWidget(icon_label)
        layout.addSpacing(8)
        layout.addWidget(self._name)

        layout.addStretch(1)
        layout.addWidget(self._seg_label)
        layout.addSpacing(6)
        layout.addWidget(self._seg_text)

        layout.addStretch(1)
        layout.addWidget(move_btn)
        layout.addSpacing(6)
        layout.addWidget(info_btn)

        self.set_segmented(segmented)

    def set_segmented(self, segmented: bool) -> None:
        """Update the indicator: green sphere + label if a segmentation exists."""
        self._seg_label.setFixedSize(24, 24)
        if segmented:
            self._seg_label.setStyleSheet(
                f"background-color: {SEGMENTED_COLOR}; border-radius: 12px;"
            )
        else:
            self._seg_label.setStyleSheet(
                f"background-color: transparent;"
                f"border: 2px solid {UNSEGMENTED_COLOR}; border-radius: 12px;"
            )
        self._seg_text.setText(
            "Segmentation present" if segmented else "Segmentation absent"
        )
        color = SEGMENTED_COLOR if segmented else UNSEGMENTED_COLOR
        self._seg_text.setStyleSheet(f"color: {color}; font-size: 10pt;")
        self._seg_label.setToolTip(
            "Segmentation available" if segmented else "No segmentation"
        )

    @override
    def mousePressEvent(self, a0: QMouseEvent | None) -> None:
        """Allows the whole header to be clickable, except for the action buttons."""

        self.clicked.emit()
        super().mousePressEvent(a0)


class ClickableHeader(QWidget):
    """Folder header; clicking it (outside the buttons) toggles the folder."""

    clicked: pyqtSignal = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("folderHeader")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

    @override
    def mousePressEvent(self, a0: QMouseEvent | None) -> None:
        self.clicked.emit()
        super().mousePressEvent(a0)


class FolderWidget(QWidget):
    """
    A collapsible, non-nestable folder rendered as a header over its rows.

    File-level actions are forwarded upward so the owning view can route them
    to the view model.
    """

    open_requested: pyqtSignal = pyqtSignal(object)
    info_requested: pyqtSignal = pyqtSignal(object)
    move_requested: pyqtSignal = pyqtSignal(object)
    rename_requested: pyqtSignal = pyqtSignal(object)
    delete_requested: pyqtSignal = pyqtSignal(object)
    toggled: pyqtSignal = pyqtSignal(str, bool)

    def __init__(self, folder: Folder, collapsed: bool) -> None:
        super().__init__()
        self.folder: Folder = folder
        self.setObjectName("folderWidget")

        outer = QVBoxLayout(self)
        outer.setSpacing(0)
        outer.setContentsMargins(0, 4, 0, 4)

        self._header = ClickableHeader()
        self._header.clicked.connect(self.toggle)

        header_layout = QHBoxLayout(self._header)
        header_layout.setContentsMargins(16, 10, 16, 10)
        header_layout.setSpacing(10)

        self._toggle_label = QLabel()
        self._toggle_label.setObjectName("folderToggle")

        folder_icon = QLabel()
        folder_icon.setPixmap(_asset_pixmap("folder_icon.png", 22))

        self._name_label = QLabel(folder.name)
        self._name_label.setObjectName("folderName")

        self._count_label = QLabel(f"({len(folder.files)})")
        self._count_label.setObjectName("folderCount")

        rename_btn = QPushButton()
        rename_btn.setObjectName("iconButton")
        rename_btn.setIcon(QIcon(_asset_pixmap("edit_icon.png", 22)))
        rename_btn.setIconSize(QSize(22, 22))
        rename_btn.setToolTip("Rename folder")
        rename_btn.clicked.connect(lambda: self.rename_requested.emit(self.folder))

        delete_btn = QPushButton()
        delete_btn.setObjectName("iconButton")
        delete_btn.setIcon(QIcon(_asset_pixmap("cancel_icon.png", 22)))
        delete_btn.setIconSize(QSize(22, 22))
        delete_btn.setToolTip("Delete folder")
        delete_btn.clicked.connect(lambda: self.delete_requested.emit(self.folder))

        header_layout.addWidget(folder_icon)
        header_layout.addWidget(self._name_label)
        header_layout.addWidget(self._count_label)
        header_layout.addStretch()
        header_layout.addWidget(rename_btn)
        header_layout.addWidget(delete_btn)
        header_layout.addWidget(self._toggle_label)

        self._files_container = QWidget()
        self.files_layout = QVBoxLayout(self._files_container)
        self.files_layout.setContentsMargins(28, 0, 0, 0)
        self.files_layout.setSpacing(2)

        outer.addWidget(self._header)
        outer.addWidget(self._files_container)

        self.set_collapsed(collapsed)

    def add_file(self, file: FileInfo, segmented: bool) -> FileRowWidget:
        """Append a file row to this folder and return it for later lookups."""
        row = FileRowWidget(file, segmented)
        row.clicked.connect(lambda: self.open_requested.emit(file))
        row.info_requested.connect(self.info_requested)
        row.move_requested.connect(self.move_requested)
        self.files_layout.addWidget(row)
        return row

    def toggle(self) -> None:
        self.set_collapsed(not self._collapsed)

    def set_collapsed(self, collapsed: bool) -> None:
        self._collapsed = collapsed
        self._files_container.setVisible(not collapsed)
        self._toggle_label.setPixmap(
            _asset_pixmap(
                "triangle_right_icon.png" if collapsed else "triangle_down_icon.png",
                22,
            )
        )
        self.toggled.emit(self.folder.name, collapsed)


class InfoPanel(QWidget):
    """Side panel rendering detailed metadata for the selected file."""

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("infoPanel")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("File Info")
        title.setObjectName("infoTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._header = QLabel("Select a file to view details")
        self._header.setObjectName("infoHeader")
        self._header.setWordWrap(True)
        self._header.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(title)
        layout.addWidget(self._header)
        layout.addSpacing(8)

        self._fields: dict[str, QLabel] = {}
        for field in (
            "Path",
            "Size",
            "Created",
            "Modified",
            "Dimensions",
            "Voxel size",
            "Segmented",
        ):
            name_label = QLabel(field)
            name_label.setObjectName("infoFieldName")
            value_label = QLabel("—")
            value_label.setObjectName("infoFieldValue")
            value_label.setWordWrap(True)
            value_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

            section = QVBoxLayout()
            section.setSpacing(2)
            section.addWidget(name_label)
            section.addWidget(value_label)
            layout.addLayout(section)
            self._fields[field] = value_label

        layout.addStretch()

    def populate(self, metadata: dict) -> None:
        self._header.setText(metadata["name"])
        self._fields["Path"].setText(metadata["path"])
        self._fields["Size"].setText(format_size(metadata["size"]))
        self._fields["Created"].setText(metadata["created"].strftime(DATE_FORMAT))
        self._fields["Modified"].setText(metadata["modified"].strftime(DATE_FORMAT))

        dimensions = metadata["dimensions"]
        self._fields["Dimensions"].setText(
            " × ".join(map(str, dimensions)) if dimensions else "unknown"
        )
        voxel_size = metadata["voxel_size"]
        self._fields["Voxel size"].setText(
            " x ".join(f"{z:g}" for z in voxel_size) if voxel_size else "unknown"
        )
        self._fields["Segmented"].setText("Yes" if metadata["segmented"] else "No")

    def clear(self) -> None:
        self._header.setText("Select a file to view details")
        for value_label in self._fields.values():
            value_label.setText("—")


class FileSelectionView(QWidget):
    def __init__(self, vm: FileViewModel):
        super().__init__()
        self._viewmodel: FileViewModel = vm
        self.setObjectName("filePage")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._folders: list[Folder] = []
        self._rows: dict[str, FileRowWidget] = {}
        self._collapsed_folders: set[str] = set()

        self._viewmodel.folders_updated.connect(self._render_folders)
        self._viewmodel.file_hash_updated.connect(self._on_file_hash_updated)

        title = QLabel("Select file")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        add_folder_btn = QPushButton("Add Folder")
        new_file_btn = QPushButton("New File")
        back_btn = QPushButton("Back")

        add_folder_btn.clicked.connect(self._add_folder_request)
        new_file_btn.clicked.connect(self._add_file_request)
        back_btn.clicked.connect(self._viewmodel.go_back)

        self._folders_scroll = QScrollArea()
        self._folders_scroll.setWidgetResizable(True)
        self._folders_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self._folders_container = QWidget()
        self._folders_container.setObjectName("foldersContainer")
        self._folders_layout = QVBoxLayout(self._folders_container)
        self._folders_layout.setContentsMargins(0, 0, 0, 0)
        self._folders_scroll.setWidget(self._folders_container)

        self._info_panel = InfoPanel()

        content = QHBoxLayout()
        content.setSpacing(16)

        left_column = QVBoxLayout()
        left_column.addWidget(title)
        left_column.addWidget(self._folders_scroll, 1)

        content.addLayout(left_column, 2)
        content.addWidget(self._info_panel, 1)

        bottom_bar = QHBoxLayout()
        bottom_bar.setSpacing(16)
        bottom_bar.addWidget(add_folder_btn, 1)
        bottom_bar.addWidget(new_file_btn, 1)
        bottom_bar.addWidget(back_btn, 1)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(24)
        root.addLayout(content, 1)
        root.addLayout(bottom_bar)

    @override
    def showEvent(self, a0: QShowEvent | None) -> None:
        self._viewmodel.page_refresh()

    # ---- RENDERING ----

    def _render_folders(self, folders: list[Folder]) -> None:
        self._folders = folders
        self._rows.clear()
        self._clear_layout(self._folders_layout)
        self._folders_layout.addStretch()

        if not folders:
            hint = QLabel("No folders yet. Use 'Add Folder' to organize your scans.")
            hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
            hint.setWordWrap(True)
            self._folders_layout.insertWidget(0, hint)
            self._info_panel.clear()
        else:
            for folder in folders:
                widget = FolderWidget(
                    folder, collapsed=folder.name in self._collapsed_folders
                )
                widget.open_requested.connect(self._viewmodel.file_chosen)
                widget.info_requested.connect(self._show_file_info)
                widget.move_requested.connect(partial(self._move_requested, folder.name))
                widget.rename_requested.connect(self._rename_requested)
                widget.delete_requested.connect(self._delete_requested)
                widget.toggled.connect(self._on_folder_toggled)
                self._folders_layout.insertWidget(self._folders_layout.count() - 1, widget)

                for file in folder.files:
                    row = widget.add_file(file, self._viewmodel.segmentation_present(file))
                    self._rows[file.path] = row

        self._viewmodel.ensure_hashes()

    def _on_file_hash_updated(self, path: str, digest: str) -> None:
        row = self._rows.get(path)
        if row is not None:
            row.set_segmented(self._viewmodel.segmentation_present(row.file))

    def _on_folder_toggled(self, name: str, collapsed: bool) -> None:
        if collapsed:
            self._collapsed_folders.add(name)
        else:
            self._collapsed_folders.discard(name)

    @staticmethod
    def _clear_layout(layout: QVBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    # ---- USER ACTIONS ----

    def _add_folder_request(self) -> None:
        name, ok = QInputDialog.getText(self, "Add Folder", "Folder name:")
        if ok and name.strip():
            self._viewmodel.add_folder(name)

    def _rename_requested(self, folder: Folder) -> None:
        name, ok = QInputDialog.getText(
            self, "Rename Folder", "New name:", text=folder.name
        )
        if ok and name.strip() and name.strip() != folder.name:
            self._viewmodel.rename_folder(folder.name, name)

    def _delete_requested(self, folder: Folder) -> None:
        result = QMessageBox.question(
            self,
            "Delete Folder",
            f"Remove folder '{folder.name}' and its entries from the list?\n"
            "The files on disk are not touched.",
        )
        if result == QMessageBox.StandardButton.Yes:
            self._viewmodel.delete_folder(folder.name)

    def _add_file_request(self) -> None:
        selection_result = QFileDialog.getOpenFileName(
            self, "Choose a file", "", "Imaging Files (*.nii *.nii.gz)"
        )
        new_file = selection_result[0]
        if not new_file:
            return
        if not self._viewmodel.path_validity_check(new_file):
            QMessageBox.warning(
                self,
                "Invalid path",
                f"the selected path '{new_file}' does not seem to exist.",
            )
            return
        target = self._select_destination_folder()
        if target is not None:
            self._viewmodel.add_file_to_folder(target, new_file)

    def _select_destination_folder(self) -> str | None:
        """Pick the folder that receives a new file, creating a default if needed."""
        names = [f.name for f in self._folders]
        if not names:
            self._viewmodel.add_folder(DEFAULT_FOLDER_NAME)
            return DEFAULT_FOLDER_NAME
        if len(names) == 1:
            return names[0]
        name, ok = QInputDialog.getItem(
            self, "Add file", "Destination folder:", names, 0, False
        )
        return name if ok else None

    def _move_requested(self, from_folder: str, file: FileInfo) -> None:
        candidates = [f.name for f in self._folders if f.name != from_folder]
        if not candidates:
            QMessageBox.information(self, "Move file", "No other folders available.")
            return
        name, ok = QInputDialog.getItem(
            self, "Move file", f"Move '{file.name}' to:", candidates, 0, False
        )
        if ok and name:
            self._viewmodel.move_file(file.path, from_folder, name)

    def _show_file_info(self, file: FileInfo) -> None:
        self._info_panel.populate(self._viewmodel.get_file_metadata(file))
