from dataclasses import dataclass
from typing import override, MutableSequence
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
        self._volume_actor = vtkActor()
        self._opacity = vtkPiecewiseFunction()
        self._x_min_sld = QSlider()
        self._x_max_sld = QSlider()
        self._y_min_sld = QSlider()
        self._y_max_sld = QSlider()
        self._z_min_sld = QSlider()
        self._z_max_sld = QSlider()
        self._data: VolumeData | None = None
        self._caps = {}
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
        self._segmentation_actor = vtk.vtkActor()
        self._clip_fn = vtk.vtkPlanes()
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

        self._set_slider_values()

        self.renderer.RemoveAllViewProps()

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

            self._volume_actor = actor
            self._volume_mapper = mapper
            self._opacity = opacity
            self.renderer.AddActor(actor)
            self.renderer.ResetCamera()
            self.call_render()

            self._init_caps()


    def add_segmentation(self, seg_path: str) -> None:

        raw_data = nib.load(seg_path).get_fdata(dtype=np.float32)
        raw_data = np.ascontiguousarray(np.transpose(raw_data, (2, 1, 0)).astype(np.int32))

        if self._data is not None:

            self._data.seg_labels = raw_data

            vtk_arr = numpy_support.numpy_to_vtk(
                self._data.seg_labels.ravel(), deep=True, array_type=vtk.VTK_INT,
            )
            seg_img = vtk.vtkImageData()
            seg_img.GetPointData().SetScalars(vtk_arr)
            seg_img.SetDimensions(self._data.dims)

            # get the amount of labels in the segmentation map
            scalars = seg_img.GetPointData().GetScalars()
            unique_vals = sorted(int(v) for v in np.unique(vtk_to_numpy(scalars)))
            n_labels = len(unique_vals)

            # create a lookup table to assign a color to each label
            self._lut.SetNumberOfTableValues(n_labels)
            self._lut.SetRange(min(unique_vals), max(unique_vals))
            self._lut.Build()

            # assign colors dynamically and as spaced apart as possible
            for i, val in enumerate(unique_vals):
                if val == 0:
                    self._lut.SetTableValue(i, 0.0, 0.0, 0.0, 0.0)
                else:
                    r, g, b = label_to_spread_color(val, len(unique_vals))
                    self._lut.SetTableValue(i, r, g, b, 0.5)

            self._segmentation_mesh.SetInputData(seg_img)
            self._segmentation_mesh.SetValue(0, 0)
            self._segmentation_mesh.SetValue(1, 1)
            self._segmentation_mesh.SetValue(2, 2)
            self._segmentation_mesh.Update()

            dims = self._data.dims
            self._clip_fn.SetBounds(0, dims[0], 0, dims[1], 0, dims[2])

            clipper = vtk.vtkClipPolyData()
            clipper.SetInputConnection(self._segmentation_mesh.GetOutputPort())
            clipper.SetClipFunction(self._clip_fn)
            clipper.GenerateClippedOutputOff()
            clipper.InsideOutOn()

            mapper = vtk.vtkPolyDataMapper()
            mapper.SetInputConnection(clipper.GetOutputPort())
            mapper.ScalarVisibilityOn()
            mapper.SetScalarModeToUseCellData()
            mapper.SetArrayComponent(0)
            mapper.SetLookupTable(self._lut)
            mapper.SetScalarRange(0, 3)

            self._segmentation_actor.SetMapper(mapper)
            self._segmentation_actor.SetUserMatrix(affine_to_vtk_matrix(self._data.affine))
            self._segmentation_actor.GetProperty().SetOpacity(1.0)
            self._segmentation_actor.GetProperty().SetInterpolationToGouraud()
            self._segmentation_actor.ForceOpaqueOn()

            back = vtk.vtkProperty()
            back.SetOpacity(1.0)
            back.SetDiffuseColor(0.8, 0.8, 0.8)
            self._segmentation_actor.SetBackfaceProperty(back)
            self._segmentation_actor.GetProperty().SetBackfaceCulling(0)

            self.renderer.AddViewProp(self._segmentation_actor)


    def _build_ui(self):
        self._layout.addWidget(self._decorator)
        self._layout.addLayout(self._build_opacity_row())
        for axis in ("x", "y", "z"):
            self._layout.addLayout(self._build_axis_row(axis))
        self._layout.addLayout(self._build_action_row())

    def _build_opacity_row(self):
        row = QHBoxLayout()

        self._onset_lbl = QLabel(f"Opacity onset: 0")
        row.addWidget(self._onset_lbl)

        self._onset_sld = QSlider(Qt.Orientation.Horizontal)
        self._onset_sld.setRange(0, 1000)
        # initial value, this will then be modified after the volume is loaded
        self._onset_sld.setValue(0)
        self._onset_sld.valueChanged.connect(self._on_opacity_changed)
        row.addWidget(self._onset_sld)

        self._max_op_lbl = QLabel("Max: 1%")
        row.addWidget(self._max_op_lbl)

        self._max_op_sld = QSlider(Qt.Orientation.Horizontal)
        self._max_op_sld.setRange(1, 100)
        # Initially view model at 1% opacity to show the segmentation underneath
        self._max_op_sld.setValue(1)
        self._max_op_sld.valueChanged.connect(self._on_opacity_changed)
        row.addWidget(self._max_op_sld)

        return row

    def _build_axis_row(self, axis):
        default_max = 100

        row = QHBoxLayout()
        lbl = QLabel(axis.upper())
        lbl.setFixedWidth(16)
        row.addWidget(lbl)

        min_lbl = QLabel("0")
        min_lbl.setFixedWidth(36)
        min_sld = QSlider(Qt.Orientation.Horizontal)
        min_sld.setRange(0, default_max)
        min_sld.setValue(0)
        min_sld.valueChanged.connect(self._on_plane_changed)

        max_lbl = QLabel(str(default_max))
        max_lbl.setFixedWidth(36)
        max_sld = QSlider(Qt.Orientation.Horizontal)
        max_sld.setRange(0, default_max)
        max_sld.setValue(default_max)
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

    def _set_slider_values(self):
        if self._data is not None:
            self._onset_sld.setValue(int(self._data.signal_onset * 1000))

            for axis in ("x", "y", "z"):
                idx = {"x": 0, "y": 1, "z": 2}[axis]
                d_max = self._data.dims[idx]

                min_sld = getattr(self, f"_{axis}_min_sld")
                max_sld = getattr(self, f"_{axis}_max_sld")
                min_lbl = getattr(self, f"_{axis}_min_lbl")
                max_lbl = getattr(self, f"_{axis}_max_lbl")

                min_sld.blockSignals(True)
                max_sld.blockSignals(True)

                min_sld.setRange(0, d_max)
                min_sld.setValue(0)
                min_lbl.setText("0")

                max_sld.setRange(0, d_max)
                max_sld.setValue(d_max)
                max_lbl.setText(str(d_max))

                min_sld.blockSignals(False)
                max_sld.blockSignals(False)

    def call_render(self):
        self._vtk_widget.GetRenderWindow().Render()

    def toggle_label_visibility(self, label_idx: int, visible: bool) -> None:
        colors: MutableSequence[float] = [0.0, 0.0, 0.0]
        self._lut.GetColor(label_idx, colors)
        if visible:
            self._lut.SetTableValue(label_idx, colors[0], colors[1], colors[2], 0.5)
        else:
            self._lut.SetTableValue(label_idx, colors[0], colors[1], colors[2], 0)

        # Tells VTK that the color lookup table got modified
        self._lut.Modified()
        self.call_render()

    def cleanup(self):
        self.renderer.RemoveAllViewProps()
        rw = self._vtk_widget.GetRenderWindow()
        rw.RemoveRenderer(self.renderer)
        self._vtk_widget.Finalize()
        rw.Finalize()

    def _init_caps(self):
        for axis in ("x", "y", "z"):
            for side in ("min", "max"):
                self._caps[(axis, side)] = self._make_cap_actor()
        self._refresh_caps(full_range=True)

    def _make_cap_actor(self):
        img = vtk.vtkImageData()
        color_map = vtk.vtkImageMapToColors()
        color_map.SetLookupTable(self._lut)
        color_map.SetInputData(img)
        color_map.SetOutputFormatToRGBA()

        actor = vtk.vtkImageActor()
        actor.GetMapper().SetInputConnection(color_map.GetOutputPort())
        actor.SetUserMatrix(affine_to_vtk_matrix(self._data.affine))
        actor.GetProperty().SetInterpolationTypeToNearest()
        actor.VisibilityOff()
        self.renderer.AddActor(actor)
        return img, color_map, actor

    def _update_cap(self, cap, axis, index, bounds, active):
        """Update a single cap image from the segmentation labels."""
        img, color_map, actor = cap
        x_min, x_max, y_min, y_max, z_min, z_max = bounds
        axis_idx = {"x": 0, "y": 1, "z": 2}[axis]
        if self._data is not None:
            index = max(0, min(index, self._data.dims[axis_idx] - 1))

            sm = self._data.seg_labels
            if sm is not None:
                if axis == "x":
                    slab = sm[z_min:z_max, y_min:y_max, index:index + 1]
                    origin = (index, y_min, z_min)
                elif axis == "y":
                    slab = sm[z_min:z_max, index:index + 1, x_min:x_max]
                    origin = (x_min, index, z_min)
                else:
                    slab = sm[index:index + 1, y_min:y_max, x_min:x_max]
                    origin = (x_min, y_min, index)

                flat = np.ascontiguousarray(slab.astype(np.int32))
                vtk_arr = numpy_support.numpy_to_vtk(
                    flat.ravel(), deep=True, array_type=vtk.VTK_INT,
                )
                img.SetDimensions(flat.shape[2], flat.shape[1], flat.shape[0])
                img.GetPointData().SetScalars(vtk_arr)
                img.SetOrigin(*origin)
                color_map.Update()
                actor.SetDisplayExtent(img.GetExtent())
                actor.SetVisibility(active)

    def _refresh_caps(self, full_range=False):
        """Refresh all 6 cap slices from current slider positions."""
        d = self._data.dims
        if full_range:
            x_min, x_max = 0, d[0]
            y_min, y_max = 0, d[1]
            z_min, z_max = 0, d[2]
        else:
            x_min = self._x_min_sld.value()
            x_max = self._x_max_sld.value()
            y_min = self._y_min_sld.value()
            y_max = self._y_max_sld.value()
            z_min = self._z_min_sld.value()
            z_max = self._z_max_sld.value()

        bounds = (x_min, x_max, y_min, y_max, z_min, z_max)
        self._update_cap(self._caps[("x", "min")], "x", x_min, bounds, active=(x_min > 0))
        self._update_cap(self._caps[("x", "max")], "x", x_max, bounds, active=(x_max < d[0]))
        self._update_cap(self._caps[("y", "min")], "y", y_min, bounds, active=(y_min > 0))
        self._update_cap(self._caps[("y", "max")], "y", y_max, bounds, active=(y_max < d[1]))
        self._update_cap(self._caps[("z", "min")], "z", z_min, bounds, active=(z_min > 0))
        self._update_cap(self._caps[("z", "max")], "z", z_max, bounds, active=(z_max < d[2]))

    def _on_opacity_changed(self, _value):
        onset = self._onset_sld.value() / 1000.0
        max_op = self._max_op_sld.value() / 100.0

        self._onset_lbl.setText(f"Opacity onset: {onset:.3f}")
        self._max_op_lbl.setText(f"Max: {self._max_op_sld.value()}%")

        self._opacity.RemoveAllPoints()
        self._opacity.AddPoint(0.0, 0.0)
        self._opacity.AddPoint(onset * 255, 0.0)
        self._opacity.AddPoint(255.0, max_op)

        self._volume_mapper.Modified()
        self.call_render()

    def _on_plane_changed(self, _value):
        axes = ("x", "y", "z")
        for a in axes:
            mn = getattr(self, f"_{a}_min_sld")
            mx = getattr(self, f"_{a}_max_sld")
            if mn.value() > mx.value():
                mx.blockSignals(True)
                mx.setValue(mn.value())
                mx.blockSignals(False)

        x_min = self._x_min_sld.value()
        x_max = self._x_max_sld.value()
        y_min = self._y_min_sld.value()
        y_max = self._y_max_sld.value()
        z_min = self._z_min_sld.value()
        z_max = self._z_max_sld.value()

        for a in axes:
            mn, mx = getattr(self, f"_{a}_min_sld").value(), getattr(self, f"_{a}_max_sld").value()
            getattr(self, f"_{a}_min_lbl").setText(str(mn))
            getattr(self, f"_{a}_max_lbl").setText(str(mx))

        self._refresh_caps(full_range=False)

        self._volume_mapper.SetCroppingRegionPlanes(
            float(x_min), float(x_max),
            float(y_min), float(y_max),
            float(z_min), float(z_max),
        )
        self._volume_mapper.Modified()

        self._clip_fn.SetBounds(
            float(x_min), float(x_max),
            float(y_min), float(y_max),
            float(z_min), float(z_max),
        )

        self._vtk_widget.GetRenderWindow().Render()

    def _on_cluster_toggle(self, checked):
        self._volume_actor.SetVisibility(not checked)
        self._vtk_widget.GetRenderWindow().Render()

    def _on_reset(self):
        self._max_op_sld.setValue(1)
        if self._data is not None:
            self._onset_sld.setValue(int(self._data.signal_onset * 1000))
            self._x_min_sld.setValue(0)
            self._x_max_sld.setValue(self._data.dims[0])
            self._y_min_sld.setValue(0)
            self._y_max_sld.setValue(self._data.dims[1])
            self._z_min_sld.setValue(0)
            self._z_max_sld.setValue(self._data.dims[2])
