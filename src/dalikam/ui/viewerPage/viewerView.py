from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QLayout, QPushButton, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QStackedWidget

from dalikam.ui.viewerPage.viewerVM import ViewerVM
from dalikam.rendering.visualizer import SliceView, SlicerType

import vtk


class SideMenu(QWidget):
    """Side panel widget containing the view mode buttons and the segmentation label selector.

    Arranges view control buttons (Axial, Coronal, Sagittal, Segmentation) vertically with a
    dynamic label display area above them. The label area is cleared and repopulated on
    each `draw_labels` call. Initial labels must be set via `draw_labels` after construction.

    TODO: the initial label display is a static placeholder, actual logic is yet to be implemented.

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

    def __init__(self) -> None:
        super().__init__()
        self.menulayout: QVBoxLayout = QVBoxLayout()
        self.setLayout(self.menulayout)
        self.menulayout.addWidget(QLabel("this is where the label selector will be"))

        self.label_layout: QVBoxLayout = QVBoxLayout()
        self.menulayout.addLayout(self.label_layout)

        self.menulayout.addStretch()

        self.axial_btn = QPushButton("Axial View")
        self.axial_btn.clicked.connect(self.axial_btn_clicked)

        self.coronal_btn = QPushButton("Coronal View")
        self.coronal_btn.clicked.connect(self.coronal_btn_clicked)

        self.sagittal_btn = QPushButton("Sagittal View")
        self.sagittal_btn.clicked.connect(self.sagittal_btn_clicked)

        self.segmentation_btn = QPushButton("TEST Segmentation")
        self.segmentation_btn.clicked.connect(self.segmentation_btn_clicked)

        self.menulayout.addWidget(self.axial_btn)
        self.menulayout.addWidget(self.coronal_btn)
        self.menulayout.addWidget(self.sagittal_btn)
        self.menulayout.addWidget(self.segmentation_btn)

    def axial_btn_clicked(self):
        self.orientation_changed.emit(0)

    def coronal_btn_clicked(self):
        self.orientation_changed.emit(1)

    def sagittal_btn_clicked(self):
        self.orientation_changed.emit(2)

    def segmentation_btn_clicked(self):
        self.segmentation_requested.emit()

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

    def draw_labels(self, labels: list[str]):
        """Replace the current label widgets with new ones from the provided list.

        Clears `label_layout` via `clear_layout`, then creates one `QLabel` per entry
        and appends it to the layout.

        Args:
            `labels (list[str])`: segmentation label names to display.
        """
        self.clear_layout(self.label_layout)
        for label in labels:
            self.label_layout.addWidget(QLabel(label))


class viewerView(QWidget):
    """Main viewer page that hosts the 3D rendering widget and the side menu.

    Composes the ThreeDview (3D volume renderer) and SideMenu into a horizontal
    layout. Connects ViewModel signals to update the rendered volume and label
    display.

    TODO: the testlabels() call on the ViewModel emits sample labels and should be
    replaced with actual data when the segmentation pipeline is integrated.
    TODO: view mode switching (axial/coronal/sagittal/3D) is not yet implemented.

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
        _ = self.side_menu.segmentation_requested.connect(self.load_slices)

        self.viewlayout.addWidget(self.side_menu, 1)
        self.viewlayout.addWidget(self.slices, 3)

        # connect all the signals
        _ = self._viewmodel.draw_file.connect(self.plot_file)
        _ = self._viewmodel.labels_changed.connect(self.side_menu.draw_labels)

        # TODO: remove when segmentation pipeline provides real labels
        self._viewmodel.testlabels()

    def plot_file(self, data: vtk.vtkNIFTIImageReader):
        """Dispatch raw NIfTI data to the 3D renderer for display.

        Args:
            `data (vtk.vtkNIFTIImageReader)`: The reader with loaded NIfTI data
                ready for rendering. Caller must ensure Update() has been called.
        """
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

    def load_slices(self):
        counter = 1
        for view in self.slice_views:
            view.add_segmentation()
            view.vtkwidget.GetRenderWindow().Render()
            print(f"done drawing labels for viewer {counter}")
            counter += 1
