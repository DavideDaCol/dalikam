from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QLayout, QPushButton, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider

from dalikam.ui.viewerPage.viewerVM import ViewerVM
from dalikam.rendering.visualizer import SliceView, SlicerType

import vtk

class SideMenu(QWidget):
    """Side panel widget containing the view mode buttons and the segmentation label selector.

    Arranges view control buttons (Axial, Coronal, Sagittal, Segmentation) vertically with a
    dynamic label display area above them. The label area is cleared and repopulated on
    each `draw_labels` call. Initial labels must be set via `draw_labels` after construction.

    TODO: view mode buttons are not connected to any slot; clicking them has no effect.
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

    def __init__(self) -> None:
        super().__init__()
        self.menulayout: QVBoxLayout = QVBoxLayout()
        self.setLayout(self.menulayout)
        self.menulayout.addWidget(QLabel("this is where the label selector will be"))

        self.label_layout: QVBoxLayout = QVBoxLayout()
        self.menulayout.addLayout(self.label_layout)

        self.menulayout.addStretch()
        self.menulayout.addWidget(QPushButton("Axial View"))
        self.menulayout.addWidget(QPushButton("Coronal View"))
        self.menulayout.addWidget(QPushButton("Sagittal View"))
        self.menulayout.addWidget(QPushButton("Run Segmentation"))

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

"""Slider widget containing the image slice slider and its min/max values. 

    Arranges the slider and its labels horizontally to let the user control the slice to view.
    Each view has its own slider instance to keep the indexes separated. The values are updated
    after every sliderMoved event (triggered by PyQt when the user moves the slider).

    Attributes:
        `slider_layout (QHBoxLayout)`: top-level layout holding the slider and labels
        `slider (QSlider)`: slider component to control which slide of the OCT to view
        `min_slice (QLabel)`: indicates the smallest possible slide index for the current
                OCT scan
        `max_slice (QLabel)`: indicates the biggest possible slide index for the current
                OCT scan

    Exported interface:
        `update_slice()`: emits a PyQt signal containing the current position of the slider
            such that the viewer can update its renderer.
        `update_extent(layout: QLayout)`: replaces the default extent values with the ones 
            exctracted from the NIfTI file

    """

class Slider(QWidget):
    slider_moved = pyqtSignal(int)
    def __init__(self) -> None:
        super().__init__()
        self.slider_layout = QHBoxLayout()
        self.setLayout(self.slider_layout)

        self.min_slice = QLabel("0")
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setSliderPosition(50)
        self.max_slice = QLabel("100")

        self.slider_layout.addWidget(self.min_slice)
        self.slider_layout.addWidget(self.slider)
        self.slider_layout.addWidget(self.max_slice)

        self.slider.sliderMoved.connect(self.update_slice)
        # TODO add the methods to update the labels and the slider

    def update_slice(self) -> None:
        self.slider_moved.emit(self.slider.sliderPosition())

    def update_extent(self, range_val: tuple[int, int]) -> None:
        min_ext, max_ext = range_val
        self.slider.setRange(min_ext, max_ext)
        self.slider.setSliderPosition((max_ext + min_ext) // 2)
        self.min_slice.setText(str(min_ext))
        self.max_slice.setText(str(max_ext))



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
        self.slices: SliceView = SliceView(SlicerType.axial)

        # control menu
        self.side_menu: SideMenu = SideMenu()

        self.slider = Slider()

        self.sliceLayout: QVBoxLayout = QVBoxLayout()
        self.sliceLayout.addWidget(self.slices)
        self.sliceLayout.addWidget(self.slider)

        self.viewlayout.addWidget(self.side_menu, 1)
        self.viewlayout.addLayout(self.sliceLayout, 3)

        # connect all the signals
        _ = self.slider.slider_moved.connect(self.update_slice_pos)
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
        self.slices.load_model(data)
        extent = self.slices.get_extent()
        self.slider.update_extent(extent)

    def update_slice_pos(self, pos: int) -> None:
        """Send the captured slider value and send it to the VTK widget.

        Args:
            `pos (int)`: the new position captured from the slider.
        """
        print(f"sending value {pos} to vtk widget")
        self.slices.change_slice(pos)