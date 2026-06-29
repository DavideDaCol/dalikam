from typing import override
from enum import Enum
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QResizeEvent, QMouseEvent
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QSlider

from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
import vtk

# Enum to differentiate between the possible types of orientations
class SlicerType(Enum):
    axial = "axial"
    coronal = "coronal"
    sagittal = "sagittal"

class SliceView(QWidget):
    def __init__(self, orientation: SlicerType) -> None:
        super().__init__()
        self.setObjectName("sliceView")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self.orientation: SlicerType = orientation

        self.ext_x, self.ext_y, self.ext_z = (0,0), (0,0), (0,0)

        layout = QVBoxLayout()
        self.setLayout(layout)

        # VTK QT widget to visualize the 3D model
        self.vtkwidget: QVTKRenderWindowInteractor = QVTKRenderWindowInteractor()

        decorator = QWidget()
        decorator.setObjectName("viewerDecorator")
        decorator.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        frame_layout = QVBoxLayout()
        frame_layout.setContentsMargins(2,2,2,2)

        decorator.setLayout(frame_layout)
        frame_layout.addWidget(self.vtkwidget)

        layout.addWidget(decorator)

        # Interactor component of the VTK QT widget (to drag and zoom)
        self.interactor: vtk.vtkRenderWindowInteractor = self.vtkwidget.GetRenderWindow().GetInteractor()
        style = SliceInteractor()
        self.interactor.SetInteractorStyle(style)

        self.slice_actor = vtk.vtkImageSlice()

        # TODO possibly move this to a dedicated rendering method

        # VTK renderer to compute the geometry of the model
        self.renderer: vtk.vtkRenderer = vtk.vtkRenderer()
        self.vtkwidget.GetRenderWindow().AddRenderer(self.renderer)

        self.slicer: vtk.vtkImageSliceMapper = vtk.vtkImageSliceMapper()

        if orientation == SlicerType.axial:
            self.slicer.SetOrientationToZ()
        elif orientation == SlicerType.coronal:
            self.slicer.SetOrientationToY()
        else:
            self.slicer.SetOrientationToX()

        self.renderer.ResetCamera()
        self.vtkwidget.Initialize()
        self.vtkwidget.Start()

        self.vtkwidget.GetRenderWindow().Render()

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

    def load_model(self, data: vtk.vtkNIFTIImageReader):
        # map the data in the .nii file to a set of image slices
            self.renderer.RemoveAllViewProps()
            img_data = data.GetOutput()
            extents = img_data.GetExtent()
            self.ext_x = (extents[0], extents[1])
            self.ext_y = (extents[2], extents[3])
            self.ext_z = (extents[4], extents[5])

            self.slicer.SetInputConnection(data.GetOutputPort())

            mid_slice = self.ext_z[0] + (self.ext_z[1] - self.ext_z[0]) // 2
            self.slicer.SetSliceNumber(mid_slice)

            self.slice_actor.SetMapper(self.slicer)

            r = img_data.GetScalarRange()
            prop = self.slice_actor.GetProperty()
            prop.SetColorWindow(r[1] - r[0])
            prop.SetColorLevel((r[0] + r[1]) / 2)

            self.renderer.AddViewProp(self.slice_actor)

            self.renderer.ResetCamera()

            camera = self.renderer.GetActiveCamera()
            camera.ParallelProjectionOn()

            self.renderer.ResetCamera()
            self.vtkwidget.GetRenderWindow().Render()

    # returns the minimum and maximum index for slices, according to the viewer's orientation
    def get_extent(self) -> tuple[int,int]:
        if self.orientation == SlicerType.axial:
            return self.ext_z
        elif self.orientation == SlicerType.coronal:
            return self.ext_y
        else:
            return self.ext_x

    # updates the slice that is currently being viewed.
    # This event is sent from the slider in the viewerView
    def change_slice(self, pos: int):
        self.slicer.SetSliceNumber(pos)
        self.vtkwidget.GetRenderWindow().Render()

# Overrides the InteractorStyleImage class so that drag events do not change
# values like image exposure or brightness. The event is converted to panning
class SliceInteractor(vtk.vtkInteractorStyleImage):
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