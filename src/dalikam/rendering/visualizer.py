from enum import Enum
from typing import override

import vtk
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QResizeEvent
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QSlider, QHBoxLayout, QLabel
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

from dalikam.backend.segmentation import SegmentationManager


class SlicerType(Enum):
    """ Enum to differentiate between the possible types of orientations"""
    axial = "axial"
    coronal = "coronal"
    sagittal = "sagittal"


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


class SliceView(QWidget):
    def __init__(self, orientation: SlicerType) -> None:
        super().__init__()
        self.setObjectName("sliceView")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self.orientation: SlicerType = orientation

        self.ext_x, self.ext_y, self.ext_z = (0, 0), (0, 0), (0, 0)

        layout = QVBoxLayout()
        self.setLayout(layout)

        # VTK QT widget to visualize the 3D model
        self.vtkwidget: QVTKRenderWindowInteractor = QVTKRenderWindowInteractor()

        # Backend middleman
        self.sm_manager: SegmentationManager = SegmentationManager()

        decorator = QWidget()
        decorator.setObjectName("viewerDecorator")
        decorator.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        frame_layout = QVBoxLayout()
        frame_layout.setContentsMargins(2, 2, 2, 2)

        decorator.setLayout(frame_layout)
        frame_layout.addWidget(self.vtkwidget)

        layout.addWidget(decorator)

        # Interactor component of the VTK QT widget (to drag and zoom)
        self.interactor: vtk.vtkRenderWindowInteractor = self.vtkwidget.GetRenderWindow().GetInteractor()
        style = SliceInteractor()
        self.interactor.SetInteractorStyle(style)

        self.slice_actor = vtk.vtkImageSlice()
        self.seg_slice_actor = vtk.vtkImageSlice()

        # TODO possibly move this to a dedicated rendering method

        # VTK renderer to compute the geometry of the model
        self.renderer: vtk.vtkRenderer = vtk.vtkRenderer()
        self.vtkwidget.GetRenderWindow().AddRenderer(self.renderer)

        self.slicer: vtk.vtkImageSliceMapper = vtk.vtkImageSliceMapper()
        self.seg_mapper: vtk.vtkImageSliceMapper = vtk.vtkImageSliceMapper()

        if orientation == SlicerType.axial:
            self.slicer.SetOrientationToZ()
            self.seg_mapper.SetOrientationToZ()
        elif orientation == SlicerType.coronal:
            self.slicer.SetOrientationToY()
            self.seg_mapper.SetOrientationToY()
        else:
            self.slicer.SetOrientationToX()
            self.seg_mapper.SetOrientationToX()

        self.renderer.ResetCamera()
        self.vtkwidget.Initialize()
        self.vtkwidget.Start()

        self.vtkwidget.GetRenderWindow().Render()

        self.slider = Slider()
        _ = self.slider.slider_moved.connect(self.change_slice)
        layout.addWidget(self.slider)

    # visual flaire: add rounded corners
    @override
    def resizeEvent(self, a0: QResizeEvent | None):
        # This creates a rounded rectangle mask for the widget
        from PyQt6.QtGui import QRegion, QPainterPath

        path = QPainterPath()
        # 15px matches your stylesheet's border-radius
        path.addRoundedRect(self.rect().toRectF(), 15, 15)
        self.setMask(QRegion(path.toFillPolygon().toPolygon()))

        super().resizeEvent(a0)

    '''
    # render the vtk window for the hidden views once they are shown
    @override
    def showEvent(self, a0: QShowEvent | None) -> None:
        self.vtkwidget.GetRenderWindow().Render()
        super().showEvent(a0)
    '''

    def load_model(self, data: vtk.vtkNIFTIImageReader):
        # map the data in the .nii file to a set of image slices
        self.renderer.RemoveAllViewProps()
        img_data = data.GetOutput()
        extents = img_data.GetExtent()
        self.ext_x = (extents[0], extents[1])
        self.ext_y = (extents[2], extents[3])
        self.ext_z = (extents[4], extents[5])

        selected_extent = (0, 0)
        # TODO review this
        if self.orientation == SlicerType.axial:
            selected_extent = self.ext_z
        elif self.orientation == SlicerType.coronal:
            selected_extent = self.ext_y
        else:
            selected_extent = self.ext_x

        self.slider.update_extent(selected_extent)
        self.slicer.SetInputConnection(data.GetOutputPort())

        mid_slice = selected_extent[0] + (selected_extent[1] - selected_extent[0]) // 2
        self.slicer.SetSliceNumber(mid_slice)

        self.slice_actor.SetMapper(self.slicer)

        r = img_data.GetScalarRange()
        prop = self.slice_actor.GetProperty()
        prop.SetColorWindow(r[1] - r[0])
        prop.SetColorLevel((r[0] + r[1]) / 2)

        self.renderer.AddViewProp(self.slice_actor)

        camera = self.renderer.GetActiveCamera()
        camera.ParallelProjectionOn()

        # find the center of the bounding box data
        bounds = img_data.GetBounds()
        center = [
            (bounds[0] + bounds[1]) / 2.0,
            (bounds[2] + bounds[3]) / 2.0,
            (bounds[4] + bounds[5]) / 2.0
        ]

        # position the camera far enough away along the viewing axis
        distance = 500.0

        if self.orientation == SlicerType.axial:
            # Looking down Z axis
            camera.SetPosition(center[0], center[1], center[2] + distance)
            camera.SetFocalPoint(center[0], center[1], center[2])
            camera.SetViewUp(0, 1, 0)

        elif self.orientation == SlicerType.coronal:
            # Looking down Y axis
            camera.SetPosition(center[0], center[1] - distance, center[2])
            camera.SetFocalPoint(center[0], center[1], center[2])
            camera.SetViewUp(0, 0, 1)

        else:
            # Looking down X axis
            camera.SetPosition(center[0] + distance, center[1], center[2])
            camera.SetFocalPoint(center[0], center[1], center[2])
            camera.SetViewUp(0, 0, 1)

        self.renderer.ResetCamera()
        self.vtkwidget.GetRenderWindow().Render()

    def add_segmentation(self, seg_path: str) -> None:
        """
            This function:
            1) asks the backend manager to compute the segmentation
            2) verifies that the results match the original scan
            3) creates a color table to differentiate all labels
            4) adds the segmentation map to the slicer
        """
        loader = vtk.vtkNIFTIImageReader()
        loader.SetFileName(seg_path)
        loader.Update()

        raw_data = loader.GetOutput()
        extents = raw_data.GetExtent()

        # check if extents match
        if (extents[0], extents[1]) != self.ext_x:
            print("extents on X axis do not match. terminating segmentation")
            return
        # TODO do this for all extents, maybe in separate function

        selected_extent = (0, 0)
        # TODO abstract this logic to a separate function
        if self.orientation == SlicerType.axial:
            selected_extent = self.ext_z
        elif self.orientation == SlicerType.coronal:
            selected_extent = self.ext_y
        else:
            selected_extent = self.ext_x

        lut = vtk.vtkLookupTable()
        lut.SetNumberOfTableValues(3)
        lut.SetRange(0, 2)
        lut.Build()

        lut.SetTableValue(0, 0.0, 0.0, 0.0, 0.0)  # transparent
        lut.SetTableValue(1, 1.0, 0.0, 0.0, 0.5)  # red
        lut.SetTableValue(2, 0.0, 1.0, 0.0, 0.5)  # green

        color_mapper = vtk.vtkImageMapToColors()
        color_mapper.SetLookupTable(lut)
        color_mapper.SetInputData(raw_data)
        color_mapper.Update()

        self.seg_mapper.SetInputConnection(color_mapper.GetOutputPort())
        mid_seg_slice = selected_extent[0] + (selected_extent[1] - selected_extent[0]) // 2
        self.seg_mapper.SetSliceNumber(mid_seg_slice)

        self.seg_slice_actor.SetMapper(self.seg_mapper)

        self.renderer.AddViewProp(self.seg_slice_actor)

    def get_extent(self) -> tuple[int, int]:
        """returns the minimum and maximum index for slices, according to the viewer's orientation"""
        if self.orientation == SlicerType.axial:
            return self.ext_z
        elif self.orientation == SlicerType.coronal:
            return self.ext_y
        else:
            return self.ext_x

    def change_slice(self, pos: int):
        """updates the slice that is currently being viewed.
        This event is sent from the slider in the viewerView"""
        self.slicer.SetSliceNumber(pos)
        self.seg_mapper.SetSliceNumber(pos)
        self.vtkwidget.GetRenderWindow().Render()


class SliceInteractor(vtk.vtkInteractorStyleImage):
    """
        Overrides the InteractorStyleImage class so that drag events do not change
        values like image exposure or brightness. The event is converted to panning
    """

    def __init__(self):
        super().__init__()
        self.AddObserver("LeftButtonPressEvent", self.left_btn_press)
        self.AddObserver("LeftButtonReleaseEvent", self.left_btn_release)

    def left_btn_press(self, obj, event):
        # Change state to Pan
        self.StartPan()

    def left_btn_release(self, obj, event):
        # End state
        self.EndPan()
