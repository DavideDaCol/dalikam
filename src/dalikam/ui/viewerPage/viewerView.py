import vtkmodules.all as vtk
from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtWidgets import QLayout, QPushButton, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QStackedWidget, QFileDialog, QDialog

from dalikam.rendering.visualizer import SliceView, SlicerType
from dalikam.ui.viewerPage.viewerVM import ViewerVM

def rgb_to_hex(rgb: tuple[float, float, float]) -> str:
    return "#{:02x}{:02x}{:02x}".format(int(rgb[0]*255),int(rgb[1]*255),int(rgb[2]*255))

class SegmentationLabel(QWidget):
    """
        QWidget used to identify which label is assigned to which color.

        Constructor attributes:
            label_name: the name of the label that is to be displayed
            color: the color of the label, given as an RGB tuple of values from 0 to 1
    """
    toggle: pyqtSignal = pyqtSignal(int,bool)

    def __init__(self, label_name: str, index: int, color: tuple[float, float, float]) -> None:
        super().__init__()
        layout = QHBoxLayout()
        self.clickable = QWidget()
        self.clickable.setFixedSize(QSize(30,30))
        self.clickable.setObjectName("labelColorSquare")

        self.visibility = True
        self.index = index

        self.hex_code = rgb_to_hex(color)
        self.clickable.setStyleSheet(f'background:{self.hex_code}')
        layout.addWidget(self.clickable)
        title =  QLabel(label_name)
        title.setObjectName("labelTitle")
        layout.addWidget(title)
        layout.addStretch()
        self.setLayout(layout)

    def mousePressEvent(self, a0):
        self.visibility = not self.visibility
        self.toggle.emit(self.index, self.visibility)
        if self.visibility:
            self.clickable.setStyleSheet(f'background:{self.hex_code}')
        else:
            self.clickable.setStyleSheet('background:#808080')


class SideMenu(QWidget):
    """Side panel widget containing the view mode buttons and the segmentation label selector.

    Arranges view control buttons (Axial, Coronal, Sagittal, Segmentation) vertically with a
    dynamic label display area above them. The label area is cleared and repopulated on
    each `draw_labels` call. Initial labels must be set via `draw_labels` after construction.

    Attributes:
        `menulayout (QVBoxLayout)`: top-level layout holding the label selector placeholder
            and view mode buttons.
        `label_layout (QVBoxLayout)`: sub-layout dynamically cleared and redrawn with
            segmentation label widgets.

    Constructor arguments:
        `labels (list[str] | None)`: reserved for initial labels; currently ignored.

    Exported interface:
        `draw_labels(labels: list[str])`: clears the current label widgets and repopulates
            them from the provided list.
        `clear_layout(layout: QLayout)`: removes and deletes all widgets from the given
            layout.

    """
    # TODO separate this routing logic in separate file
    orientation_changed = pyqtSignal(int)
    segmentation_requested = pyqtSignal()
    export_requested = pyqtSignal()
    load_segmentation_requested = pyqtSignal()
    remove_segmentation_requested = pyqtSignal()
    toggle_label_requested = pyqtSignal(int, bool)

    def __init__(self) -> None:
        super().__init__()
        self._export_mode = False
        self._segmentation_loaded = False
        self.menuLayout: QVBoxLayout = QVBoxLayout()
        self.setLayout(self.menuLayout)
        title_layout = QHBoxLayout()
        title_layout.addStretch()
        menu_title = QLabel("Segmentation labels:")
        menu_title.setObjectName("segmentationTitle")
        title_layout.addWidget(menu_title)
        title_layout.addStretch()
        self.menuLayout.addLayout(title_layout)

        self.label_layout: QVBoxLayout = QVBoxLayout()
        self.menuLayout.addLayout(self.label_layout)

        self.label_list: list[SegmentationLabel] = []

        self.menuLayout.addStretch()

        self.axial_btn = QPushButton("Axial View")
        self.axial_btn.clicked.connect(self.axial_btn_clicked)

        self.coronal_btn = QPushButton("Coronal View")
        self.coronal_btn.clicked.connect(self.coronal_btn_clicked)

        self.sagittal_btn = QPushButton("Sagittal View")
        self.sagittal_btn.clicked.connect(self.sagittal_btn_clicked)

        self.segmentation_btn = QPushButton("Create Segmentation")
        self.segmentation_btn.clicked.connect(self.sm_btn_clicked)

        self.load_segmentation_btn = QPushButton("Load Segmentation")
        self.load_segmentation_btn.clicked.connect(self.load_seg_btn_clicked)

        self.menuLayout.addWidget(self.axial_btn)
        self.menuLayout.addWidget(self.coronal_btn)
        self.menuLayout.addWidget(self.sagittal_btn)
        self.menuLayout.addWidget(self.segmentation_btn)
        self.menuLayout.addWidget(self.load_segmentation_btn)

    def axial_btn_clicked(self):
        self.orientation_changed.emit(0)

    def coronal_btn_clicked(self):
        self.orientation_changed.emit(1)

    def sagittal_btn_clicked(self):
        self.orientation_changed.emit(2)

    def sm_btn_clicked(self):
        if self._export_mode:
            self.export_requested.emit()
        else:
            self.segmentation_requested.emit()

    def set_export_mode(self):
        """Switch the segmentation button to export mode."""
        self._export_mode = True
        self.segmentation_btn.setText("Export Segmentation")

    def reset_create_mode(self):
        """Switch the segmentation button back to create mode."""
        self._export_mode = False
        self.segmentation_btn.setText("Create Segmentation")

    def load_seg_btn_clicked(self):
        if self._segmentation_loaded:
            self.remove_segmentation_requested.emit()
        else:
            self.load_segmentation_requested.emit()

    def set_segmentation_loaded(self):
        """Toggle the load/remove button to remove mode."""
        self._segmentation_loaded = True
        self.load_segmentation_btn.setText("Remove Segmentation")

    def set_segmentation_unloaded(self):
        """Toggle the load/remove button back to load mode."""
        self._segmentation_loaded = False
        self.load_segmentation_btn.setText("Load Segmentation")

    def clear_layout(self, layout: QLayout):
        """Remove all widgets from the given layout and schedule them for deletion.

        Iterates over the layout's children, extracts widget items, and calls
        `deleteLater` on each.

        Args:
            `layout (QLayout)`: the layout to clear.
        """
        while layout.count():
            item = layout.takeAt(0)
            if item is not None:
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()

    def draw_labels(self, label_names: list[str], labels_idx: list[int], color_map: dict[int, tuple[float, float, float]]):
        """Replace the current label widgets with new ones from the provided list.

        Clears `label_layout` via `clear_layout`, then creates one `QLabel` per entry
        and appends it to the layout.

        Args:
            `labels (list[str])`: segmentation label names to display.
        """
        self.clear_layout(self.label_layout)
        for i in range (0,len(label_names)):
            color = color_map.get(labels_idx[i])
            if color is not None:
                label = SegmentationLabel(label_names[i], labels_idx[i], color)
                label.toggle.connect(self.relay_toggle)
                self.label_layout.addWidget(label)
            else:
                self.label_layout.addWidget(QLabel(label_names[0]))

    def relay_toggle(self, index: int, visible: bool):
        self.toggle_label_requested.emit(index,visible)

class viewerView(QWidget):
    """Main viewer page that hosts the 3D rendering widget and the side menu.

    Composes the ThreeDview (3D volume renderer) and SideMenu into a horizontal
    layout. Connects ViewModel signals to update the rendered volume and label
    display.


    Attributes:
        _viewmodel (ViewerVM): ViewModel driving the viewer page.
        viewlayout (QHBoxLayout): root layout splitting side menu and 3D view.
        slices (SliceView): VTK-based 3D volumetric renderer widget.
        side_menu (SideMenu): side panel with view controls and label display.

    Constructor args:
        vm (ViewerVM): ViewModel that provides file data and label state.

    Exported interface:
        plot_file(data: vtk.vtkNIFTIImageReader): slot connected to
            ViewerVM.draw_file. Loads raw NIfTI data into the 3D renderer.

    Errors / edge cases:
        plot_file must only be called after the reader has completed loading
        (data.Update() has been called).
    """

    def __init__(self, vm: ViewerVM) -> None:
        super().__init__()
        self._viewmodel: ViewerVM = vm

        self.setObjectName("viewerPage")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        # layout to hold everything in place
        self.viewlayout: QHBoxLayout = QHBoxLayout()
        self.setLayout(self.viewlayout)

        # custom slice viewer
        self.slices = QStackedWidget()
        self.slice_views: list[SliceView] = []
        axial_slicer = SliceView(SlicerType.axial)
        self.slice_views.append(axial_slicer)
        coronal_slicer = SliceView(SlicerType.coronal)
        self.slice_views.append(coronal_slicer)
        sagittal_slicer = SliceView(SlicerType.sagittal)
        self.slice_views.append(sagittal_slicer)

        for view in self.slice_views:
            self.slices.addWidget(view)

        # control menu
        self.side_menu: SideMenu = SideMenu()
        _ = self.side_menu.orientation_changed.connect(self.change_view)
        _ = self.side_menu.segmentation_requested.connect(self.compute_slices)
        _ = self.side_menu.export_requested.connect(self._on_export_requested)
        _ = self.side_menu.load_segmentation_requested.connect(self._on_load_segmentation)
        _ = self.side_menu.remove_segmentation_requested.connect(self._on_remove_segmentation)
        _ = self.side_menu.toggle_label_requested.connect(self._on_toggle_visibility)

        self.viewlayout.addWidget(self.side_menu, 1)
        self.viewlayout.addWidget(self.slices, 3)

        # connect all the signals
        _ = self._viewmodel.draw_file.connect(self.plot_file)
        _ = self._viewmodel.labels_changed.connect(self.side_menu.draw_labels)
        _ = self._viewmodel.segmentation_ended.connect(self.load_slices)
        _ = self._viewmodel.segmentation_ended.connect(self.side_menu.set_export_mode)
        _ = self._viewmodel.segmentation_ended.connect(self.side_menu.set_segmentation_loaded)

        self._viewmodel.init_labels()

    def cleanup_viewer(self):
        for view in self.slice_views:
            view.cleanup()

    def plot_file(self, data: vtk.vtkNIFTIImageReader):
        """Dispatch raw NIfTI data to the 3D renderer for display."""
        self.side_menu.reset_create_mode()
        print(f"drawing {data.descriptive_name}")
        counter = 1
        for view in self.slice_views:
            view.load_model(data)
            print(f"done loading data for viewer {counter}")
            counter += 1

    def change_view(self, page: int):
        self.slices.setCurrentIndex(page)
        active_view = self.slice_views[page]
        active_view.vtkwidget.GetRenderWindow().Render()

    def compute_slices(self):
        self._viewmodel.start_segmentation()


    def load_slices(self, slices):
        counter = 1
        for view in self.slice_views:
            view.add_segmentation(str(slices))
            view.vtkwidget.GetRenderWindow().Render()
            print(f"done drawing labels for viewer {counter}")
            counter += 1

    def _on_export_requested(self):
        save_dir = QFileDialog.getExistingDirectory(self, "Select Export Location")
        if not save_dir:
            return
        from pathlib import Path
        dest = self._viewmodel.export_segmentation(Path(save_dir))
        popup = QDialog(self)
        layout = QHBoxLayout()
        layout.addWidget(QLabel(f"Exported to {dest}"))
        popup.setLayout(layout)
        popup.exec()

    def _on_load_segmentation(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Segmentation File", "", "NIfTI Files (*.nii.gz)"
        )
        if not path:
            return
        from pathlib import Path
        self._viewmodel.load_external_segmentation(Path(path))

    def _on_remove_segmentation(self):
        for view in self.slice_views:
            view.remove_segmentation()
            view.vtkwidget.GetRenderWindow().Render()
        self._viewmodel.init_labels()
        self.side_menu.set_segmentation_unloaded()
        self.side_menu.reset_create_mode()

    def _on_toggle_visibility(self, index: int, visible: bool):
        for view in self.slice_views:
            view.toggle_label_visibility(index, visible)
