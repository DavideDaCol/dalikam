from dataclasses import dataclass
from typing import override
import nibabel as nib
import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QResizeEvent
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QCheckBox, QPushButton
import vtkmodules.all as vtk
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from vtkmodules.util import numpy_support
from vtkmodules.util.numpy_support import vtk_to_numpy
from vtkmodules.vtkCommonDataModel import vtkPiecewiseFunction
from vtkmodules.vtkRenderingCore import vtkActor
from vtkmodules.vtkRenderingVolumeOpenGL2 import vtkSmartVolumeMapper

from dalikam.rendering.visualizer import Slider
from dalikam.tools.utils import label_to_spread_color

MAX_VOXELS=20_000_000

@dataclass
class VolumeData:
    """
    Contains information regarding volume data, extracted from the NIfTI file.
    """
    voxels: np.ndarray    # uint8, VTK axis order (Z, Y, X)
    seg_labels: np.ndarray | None  # int32, VTK axis order (Z, Y, X)
    dims: tuple            # (X, Y, Z) for vtkImageData.SetDimensions
    signal_onset: float    # noise floor threshold [0, 1]
    affine: np.ndarray     # 4x4 NIfTI affine

def weighted_quantile(values, weights, q):
    """Smallest value whose cumulative weight reaches q * total weight."""
    values = np.asarray(values)
    weights = np.asarray(weights)
    order = np.argsort(values)
    cumsum = weights[order].cumsum()
    cutoff = weights.sum() * q
    return values[order][cumsum >= cutoff][0]

def noise_floor_heuristic(vol) -> float:
    """Estimate background noise level from gradient-weighted slice medians."""
    # compute gradients over z dimension, since it's usually the most detailed
    z_dim = vol.shape[2]
    slice_medians = []
    # compute gradients once every 5 slices to speed up computation
    for i in range(z_dim // 5):
        # extract the data over a two-dimensional slice
        s = vol[:, :, i * 5]
        # find the intensity gradients and normalize them
        gx, gy = np.gradient(s)
        gradients = np.hypot(gx,gy)
        # extract the median intensity over the top third quantile, weighted wrt the gradients
        slice_medians.append(weighted_quantile(s.ravel(), gradients.ravel(), 0.67))
    return float(np.median(slice_medians))

def affine_to_vtk_matrix(affine: np.ndarray) -> vtk.vtkMatrix4x4:
    """Convert a 4x4 NumPy affine to a vtkMatrix4x4."""
    mat = vtk.vtkMatrix4x4()
    for r in range(4):
        for c in range(4):
            mat.SetElement(r, c, affine[r, c])
    return mat

class ThreeDSliceView(QWidget):
    def __init__(self):
        super().__init__()
        self.dims = (0, 0, 0)
        self.onset = 0.0
        self.scan_u8 = np.ascontiguousarray((0, 0, 0))
        self.vol_actor = vtkActor()
        self.vol_mapper = vtkSmartVolumeMapper()
        self.opacity = vtkPiecewiseFunction()
        self._data: VolumeData | None = None
        self._init_renderer()
        self._build_ui()

    def _init_renderer(self):

        self._layout = QVBoxLayout()
        self.setLayout(self._layout)

        self.ext_x, self.ext_y, self.ext_z = (0, 0), (0, 0), (0, 0)

        self._vtk_widget: QVTKRenderWindowInteractor = QVTKRenderWindowInteractor()
        self._decorator = QWidget()
        self._decorator.setObjectName("viewerDecorator")
        self._decorator.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        frame_layout = QVBoxLayout()
        frame_layout.setContentsMargins(2, 2, 2, 2)

        self._decorator.setLayout(frame_layout)
        frame_layout.addWidget(self._vtk_widget)

        # initialize volume rendering components
        self._volume_mapper = vtk.vtkSmartVolumeMapper()
        self._segmentation_mesh = vtk.vtkSurfaceNets3D()
        self._lut = vtk.vtkLookupTable()

        self.renderer = vtk.vtkRenderer()
        self._vtk_widget.GetRenderWindow().AddRenderer(self.renderer)
        self._vtk_widget.Initialize()

        interactor = self._vtk_widget.GetRenderWindow().GetInteractor()
        interactor.SetDesiredUpdateRate(30.0)
        interactor.SetStillUpdateRate(0.0001)

        axes = vtk.vtkAxesActor()
        self._orientation = vtk.vtkOrientationMarkerWidget()
        self._orientation.SetOrientationMarker(axes)
        self._orientation.SetInteractor(interactor)
        self._orientation.EnabledOn()
        self._orientation.SetInteractive(0)
        self._orientation.SetViewport(0.0, 0.0, 0.15, 0.15)

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

    def load_model(self, data: str):
        affine = nib.load(data).affine
        scan = nib.load(data).get_fdata(dtype=np.float32)

        lo, hi = np.percentile(scan, 1), np.percentile(scan, 99)
        scan = np.clip(scan, lo, hi)
        scan = (scan - lo) / (hi - lo)

        if scan.size > MAX_VOXELS:
            # TODO perform downsampling
            pass

        # Nibabel (X,Y,Z) -> VTK (Z,Y,X)
        scan = np.ascontiguousarray(np.transpose(scan, (2, 1, 0)))

        dims = (scan.shape[2], scan.shape[1], scan.shape[0])
        onset = noise_floor_heuristic(scan)
        scan_u8 = np.ascontiguousarray((scan * 255).astype(np.uint8))

        self._data = VolumeData(scan_u8, None, dims, onset, affine)

        if self._data is not None:

            vtk_arr = numpy_support.numpy_to_vtk(
                self._data.voxels.ravel(), deep=True, array_type=vtk.VTK_UNSIGNED_CHAR,
            )
            image = vtk.vtkImageData()
            image.GetPointData().SetScalars(vtk_arr)
            image.SetDimensions(self._data.dims)

            mapper = vtk.vtkSmartVolumeMapper()
            mapper.SetInputData(image)
            mapper.SetRequestedRenderModeToGPU()
            mapper.SetBlendModeToComposite()
            mapper.SetAutoAdjustSampleDistances(1)
            mapper.SetInteractiveAdjustSampleDistances(1)
            mapper.SetCropping(1)
            mapper.SetCroppingRegionPlanes(
                0, float(self._data.dims[0]),
                0, float(self._data.dims[1]),
                0, float(self._data.dims[2]),
            )
            mapper.Update()

            onset = self._data.signal_onset
            color = vtk.vtkColorTransferFunction()
            color.AddRGBPoint(0.0, 0.0, 0.0, 0.0)
            color.AddRGBPoint(onset * 255, 0.0, 0.0, 0.0)
            color.AddRGBPoint(255.0, 1.0, 1.0, 1.0)

            opacity = vtk.vtkPiecewiseFunction()
            opacity.AddPoint(0.0, 0.0)
            opacity.AddPoint(onset * 255, 0.0)
            opacity.AddPoint(255.0, 0.01)

            prop = vtk.vtkVolumeProperty()
            prop.SetScalarOpacity(opacity)
            prop.SetColor(color)
            prop.ShadeOff()
            prop.SetAmbient(0.25)
            prop.SetDiffuse(0.7)
            prop.SetSpecular(0.1)
            prop.SetInterpolationTypeToLinear()

            actor = vtk.vtkVolume()
            actor.SetMapper(mapper)
            actor.SetProperty(prop)
            actor.SetUserMatrix(affine_to_vtk_matrix(self._data.affine))

            self.vol_actor = actor
            self.vol_mapper = mapper
            self.opacity = opacity
            self.renderer.AddActor(actor)
            self.renderer.ResetCamera()
            self.call_render()


    def add_segmentation(self, seg_path: str) -> None:

        raw_data = nib.load(seg_path).get_fdata(dtype=np.float32)
        raw_data = np.ascontiguousarray(np.transpose(raw_data, (2, 1, 0)).astype(np.int32))
        extents = (raw_data.shape[2], raw_data.shape[1], raw_data.shape[0])

        # get the amount of labels in the segmentation map
        scalars = raw_data.GetPointData().GetScalars()
        unique_vals = sorted(int(v) for v in np.unique(vtk_to_numpy(scalars)))
        n_labels = len(unique_vals)

        # create a lookup table to assign a color to each label
        self.lut = vtk.vtkLookupTable()
        self.lut.SetNumberOfTableValues(n_labels)
        self.lut.SetRange(min(unique_vals), max(unique_vals))
        self.lut.Build()

        # assign colors dynamically and as spaced apart as possible
        for i, val in enumerate(unique_vals):
            if val == 0:
                self.lut.SetTableValue(i, 0.0, 0.0, 0.0, 0.0)
            else:
                r, g, b = label_to_spread_color(val, len(unique_vals))
                self.lut.SetTableValue(i, r, g, b, 0.5)

        color_mapper = vtk.vtkImageMapToColors()
        color_mapper.SetLookupTable(self.lut)
        color_mapper.SetInputData(raw_data)
        color_mapper.Update()

        self.seg_mapper.SetInputConnection(color_mapper.GetOutputPort())
        self.seg_mapper.SetSliceNumber(self.slicer.GetSliceNumber())

        self.seg_slice_actor.SetMapper(self.seg_mapper)

        self.renderer.AddViewProp(self.seg_slice_actor)

    def _build_ui(self):
        self._layout.addWidget(self._decorator)
        self._layout.addLayout(self._build_opacity_row())
        # TODO get back to this
        # for axis in ("x", "y", "z"):
            # self._layout.addLayout(self._build_axis_row(axis))
        # self._layout.addLayout(self._build_action_row())

    def _build_opacity_row(self):
        row = QHBoxLayout()

        self._onset_lbl = QLabel(f"Opacity onset: 0")
        row.addWidget(self._onset_lbl)

        self._onset_sld = Slider()
        row.addWidget(self._onset_sld)

        self._max_op_lbl = QLabel("Max: 1%")
        row.addWidget(self._max_op_lbl)

        self._max_op_sld = Slider()
        row.addWidget(self._max_op_sld)

        return row

    def _build_axis_row(self, axis):
        d = self._dims
        idx = {"x": 0, "y": 1, "z": 2}[axis]

        row = QHBoxLayout()
        lbl = QLabel(axis.upper())
        lbl.setFixedWidth(16)
        row.addWidget(lbl)

        min_lbl = QLabel("0")
        min_lbl.setFixedWidth(36)
        min_sld = QSlider(Qt.Orientation.Horizontal)
        min_sld.setRange(0, d[idx])
        min_sld.setValue(0)
        min_sld.valueChanged.connect(self._on_plane_changed)

        max_lbl = QLabel(str(d[idx]))
        max_lbl.setFixedWidth(36)
        max_sld = QSlider(Qt.Orientation.Horizontal)
        max_sld.setRange(0, d[idx])
        max_sld.setValue(d[idx])
        max_sld.valueChanged.connect(self._on_plane_changed)

        row.addWidget(min_lbl)
        row.addWidget(min_sld, 1)
        row.addWidget(max_lbl)
        row.addWidget(max_sld, 1)

        setattr(self, f"_{axis}_min_lbl", min_lbl)
        setattr(self, f"_{axis}_max_lbl", max_lbl)
        setattr(self, f"_{axis}_min_sld", min_sld)
        setattr(self, f"_{axis}_max_sld", max_sld)

        return row

    def _build_action_row(self):
        row = QHBoxLayout()

        cluster_cb = QCheckBox("Show clusters only")
        cluster_cb.toggled.connect(self._on_cluster_toggle)
        row.addWidget(cluster_cb)

        row.addStretch()

        reset_btn = QPushButton("Reset All")
        reset_btn.clicked.connect(self._on_reset)
        row.addWidget(reset_btn)

        return row

    def call_render(self):
        self._vtk_widget.GetRenderWindow().Render()

    def cleanup(self):
        self.renderer.RemoveAllViewProps()
        rw = self._vtk_widget.GetRenderWindow()
        rw.RemoveRenderer(self.renderer)
        self._vtk_widget.Finalize()
        rw.Finalize()