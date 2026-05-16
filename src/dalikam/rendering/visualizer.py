from typing import override
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QResizeEvent
from PyQt6.QtWidgets import QWidget, QVBoxLayout

from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
import vtk

class ThreeDview(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("threeD")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

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

        # Interactor component of the VTK QT widget (used to rotate and move the 3d volume)
        self.interactor: vtk.vtkRenderWindowInteractor = self.vtkwidget.GetRenderWindow().GetInteractor()

        # VTK renderer to compute the geometry of the model
        self.renderer: vtk.vtkRenderer = vtk.vtkRenderer()
        self.vtkwidget.GetRenderWindow().AddRenderer(self.renderer)

        # VTK map to go from data to model
        self.volume_map: vtk.vtkSmartVolumeMapper = vtk.vtkSmartVolumeMapper()

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
        # map the data in the .nii file to a volume that can be rendered
            self.renderer.RemoveAllViewProps()
            scaled_data = self.normalize_map(data)
            self.volume_map.SetInputConnection(scaled_data.GetOutputPort())
            self.set_render_appearance(scaled_data)
            self.renderer.ResetCamera()
            self.vtkwidget.GetRenderWindow().Render()

    # this function configures the aesthetic side of the renderer such as the 
    # opacity and the color function
    def set_render_appearance(self, data: vtk.vtkImageShiftScale):
        opacity = vtk.vtkPiecewiseFunction()

        min_val, max_val = data.GetOutput().GetScalarRange()
        mid = min_val + 0.3 * (max_val - min_val)

        threshold = min_val + 0.5 * (max_val - min_val)

        _ = opacity.AddPoint(min_val, 0.0)
        _ = opacity.AddPoint(threshold, 0.0)
        _ = opacity.AddPoint(threshold + 1, 0.6)
        _ = opacity.AddPoint(max_val, 1.0)

        color_func = vtk.vtkColorTransferFunction()
        low = min_val
        high = max_val
        mid1 = low + 0.4 * (high - low)
        mid2 = low + 0.7 * (high - low)

        _ = color_func.AddRGBPoint(low, 0.0, 0.0, 0.0)
        _ = color_func.AddRGBPoint(mid1, 0.3, 0.3, 0.3)
        _ = color_func.AddRGBPoint(mid2, 0.8, 0.8, 0.8)
        _ = color_func.AddRGBPoint(high, 1.0, 1.0, 1.0)

        volume_property = vtk.vtkVolumeProperty()
        volume_property.SetColor(color_func)  # pyright: ignore[reportUnknownMemberType]
        volume_property.SetScalarOpacity(opacity)  # pyright: ignore[reportUnknownMemberType]
        volume_property.ShadeOn()
        volume_property.SetInterpolationTypeToLinear()

        # 4. Volume actor
        volume = vtk.vtkVolume()
        volume.SetMapper(self.volume_map)
        volume.SetProperty(volume_property)

        # 5. Add to scene
        self.renderer.AddVolume(volume)
        self.renderer.SetBackground(0.0, 0.0, 0.0)

    # TODO: this preprocessing stage should live in the model, not the view.
    # functionality is fine, but archtecturally it's unstable
    def normalize_map(self, data: vtk.vtkNIFTIImageReader) -> vtk.vtkImageShiftScale:
        scaler = vtk.vtkImageShiftScale()
        scaler.SetInputConnection(data.GetOutputPort())

        # improve performance by going from 16 to 8 bit precision
        scaler.SetOutputScalarTypeToUnsignedChar()

        min_range, max_range = data.GetOutput().GetScalarRange()
        scale = 255.0 / (max_range - min_range)

        scaler.SetShift(-min_range)
        scaler.SetScale(scale)

        scaler.Update()

        return scaler
