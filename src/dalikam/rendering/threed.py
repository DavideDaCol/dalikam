from collections.abc import MutableSequence
from dataclasses import dataclass
from typing import override

import nibabel as nib
import numpy as np
import vtkmodules.all as vtk
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QResizeEvent
from PyQt6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)
from scipy.ndimage import zoom
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from vtkmodules.util import numpy_support
from vtkmodules.util.numpy_support import vtk_to_numpy
from vtkmodules.vtkCommonDataModel import vtkPiecewiseFunction
from vtkmodules.vtkRenderingCore import vtkActor

from dalikam.tools.utils import label_to_spread_color

MAX_VOXELS = 20_000_000


def downsample_volume(scan: np.ndarray, affine: np.ndarray, factor: float) -> tuple[np.ndarray, np.ndarray]:
    """Downsample volume and adjust the affine matrix accordingly."""
    scan = zoom(scan, factor, order=1)
    new_affine = affine.copy()
    new_affine[:3, :3] = affine[:3, :3] / factor
    return scan, new_affine


@dataclass
class VolumeData:
    """Contains information regarding volume data, extracted from the NIfTI file."""
    voxels: np.ndarray  # uint8, VTK axis order (Z, Y, X)
    seg_labels: np.ndarray | None  # int32, VTK axis order (Z, Y, X)
    dims: tuple  # (X, Y, Z) for vtkImageData.SetDimensions
    signal_onset: float  # noise floor threshold [0, 1]
    affine: np.ndarray  # 4x4 NIfTI affine

# ---- HELPER FUNCTIONS ----

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
    z_dim = vol.shape[0]
    slice_medians = []
    # compute gradients once every 5 slices to speed up computation
    for i in range(z_dim // 5):
        # extract the data over a two-dimensional slice
        s = vol[:, :, i * 5]
        # find the intensity gradients and normalize them
        gx, gy = np.gradient(s)
        gradients = np.hypot(gx, gy)
        # extract the median intensity over the top third quantile, weighted wrt the gradients
        slice_medians.append(weighted_quantile(s.ravel(), gradients.ravel(), 0.67))
    return float(np.median(slice_medians))


def affine_to_vtk_matrix(affine: np.ndarray) -> vtk.vtkMatrix4x4:
    """Convert a 4x4 NumPy affine to a vtkMatrix4x4. Used for 3D volume orientation."""
    mat = vtk.vtkMatrix4x4()
    for r in range(4):
        for c in range(4):
            mat.SetElement(r, c, affine[r, c])
    return mat

# ---- INITIALIZATION ----

class ThreeDSliceView(QWidget):
    def __init__(self):
        super().__init__()

        # Helper class used to organize raw and metadata
        self._data: VolumeData | None = None

        # Initialize VTK objects
        self._volume_actor = vtkActor()
        self._volume_mapper = vtk.vtkSmartVolumeMapper()

        self._segmentation_mesh = vtk.vtkSurfaceNets3D()
        self._segmentation_actor = vtk.vtkActor()

        self._opacity = vtkPiecewiseFunction()
        self._clip_fn = vtk.vtkPlanes()
        self._lut = vtk.vtkLookupTable()
        self._label_lut_lookup: dict[int, int] = {}
        self._cap_lut = vtk.vtkLookupTable()
        self._caps = {}

        #Initialize axis sliders
        self._x_min_sld = QSlider()
        self._x_max_sld = QSlider()
        self._y_min_sld = QSlider()
        self._y_max_sld = QSlider()
        self._z_min_sld = QSlider()
        self._z_max_sld = QSlider()

        # Set up the rendering pipeline
        self._init_renderer()

        # Build the opacity and slicing controls
        self._build_ui()

    # ---- VTK INITIALIZATION ----

    def _init_renderer(self):
        """Creates the VTK interactor and initializes the renderer and camera."""
        self._layout = QVBoxLayout()
        self.setLayout(self._layout)

        self._vtk_widget: QVTKRenderWindowInteractor = QVTKRenderWindowInteractor()
        self._decorator = QWidget()
        self._decorator.setObjectName("viewerDecorator")
        self._decorator.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        frame_layout = QVBoxLayout()
        frame_layout.setContentsMargins(2, 2, 2, 2)

        self._decorator.setLayout(frame_layout)
        frame_layout.addWidget(self._vtk_widget)

        # initialize volume rendering components
        self.renderer = vtk.vtkRenderer()
        self._vtk_widget.GetRenderWindow().AddRenderer(self.renderer)
        self._vtk_widget.Initialize()

        # create the interactor window to capture user input
        interactor = self._vtk_widget.GetRenderWindow().GetInteractor()
        interactor.SetDesiredUpdateRate(30.0)
        interactor.SetStillUpdateRate(0.0001)

        # add axes actor as a frame of reference in 3D space
        axes = vtk.vtkAxesActor()
        self._orientation = vtk.vtkOrientationMarkerWidget()
        self._orientation.SetOrientationMarker(axes)
        self._orientation.SetInteractor(interactor)
        self._orientation.EnabledOn()
        self._orientation.SetInteractive(0)
        self._orientation.SetViewport(0.0, 0.0, 0.15, 0.15)

    # ---- UI INITIALIZATION ----

    def _build_ui(self):
        self._layout.addWidget(self._decorator)
        self._layout.addLayout(self._build_opacity_row())
        for axis in ("x", "y", "z"):
            self._layout.addLayout(self._build_axis_row(axis))
        self._layout.addLayout(self._build_action_row())

    def _build_opacity_row(self):
        """Builds controls for the opacity onset (where the background stops) and the maximum opacity level."""
        row = QHBoxLayout()

        # Onset slider, sets at which intensity value the pipeline should start rendering the volume
        self._onset_lbl = QLabel(f"Opacity onset: 0")
        row.addWidget(self._onset_lbl)

        self._onset_sld = QSlider(Qt.Orientation.Horizontal)
        self._onset_sld.setRange(0, 1000)
        # initial value, this will then be modified after the volume is loaded
        self._onset_sld.setValue(0)
        self._onset_sld.valueChanged.connect(self._on_opacity_changed)
        row.addWidget(self._onset_sld)

        # Max opacity slider, sets the level of transparency of the volume
        self._max_op_lbl = QLabel("Max: 100%")
        row.addWidget(self._max_op_lbl)

        self._max_op_sld = QSlider(Qt.Orientation.Horizontal)
        self._max_op_sld.setRange(1, 100)
        # Initially view model at 100% opacity (reduced to 1% when segmentation loads)
        self._max_op_sld.setValue(100)
        self._max_op_sld.valueChanged.connect(self._on_opacity_changed)
        row.addWidget(self._max_op_sld)

        return row

    def _build_axis_row(self, axis):
        """Builds controls for the maximum and minimum visible slices at the specified axis."""
        default_max = 100

        row = QHBoxLayout()
        lbl = QLabel(axis.upper())
        lbl.setFixedWidth(16)
        row.addWidget(lbl)

        # minimum slice slider: sets the starting slice, all the previous slices are not rendered
        min_lbl = QLabel("0")
        min_lbl.setFixedWidth(36)
        min_sld = QSlider(Qt.Orientation.Horizontal)
        min_sld.setRange(0, default_max)
        min_sld.setValue(0)
        min_sld.valueChanged.connect(self._on_plane_changed)

        # maximum slice slider: sets the ending slice, all the following slices are not rendered
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

        # TODO is this really necessary?
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

    @override
    def resizeEvent(self, a0: QResizeEvent | None):
        """Adds rounded corners to the 3D viewer viewport using a rounded rectangle mask."""
        from PyQt6.QtGui import QRegion, QPainterPath

        path = QPainterPath()
        # 15px matches the stylesheet's border-radius
        path.addRoundedRect(self.rect().toRectF(), 15, 15)
        self.setMask(QRegion(path.toFillPolygon().toPolygon()))

        super().resizeEvent(a0)

    # ---- VOLUME LOADING ----

    def load_model(self, data: str):
        """Loads the raw data from the data path inside the VolumeData instance, then calls the volume renderer."""
        affine = nib.load(data).affine
        scan = nib.load(data).get_fdata(dtype=np.float32)
        
        # intensity normalization: clip the data at the lowest and highest 1%
        lo, hi = np.percentile(scan, 1), np.percentile(scan, 99)
        scan = np.clip(scan, lo, hi)
        scan = (scan - lo) / (hi - lo)
        if scan.size > MAX_VOXELS:
            factor = (MAX_VOXELS / scan.size) ** (1.0 / 3)
            scan, affine = downsample_volume(scan, affine, factor)
        
        # Rotate volume
        # Nibabel assumes (X,Y,Z) while VTK assumes (Z,Y,X)
        scan = np.ascontiguousarray(np.transpose(scan, (2, 1, 0)))
        dims = (scan.shape[2], scan.shape[1], scan.shape[0])
        onset = noise_floor_heuristic(scan)
        scan_u8 = np.ascontiguousarray((scan * 255).astype(np.uint8))
        self.load_model_data(VolumeData(scan_u8, None, dims, onset, affine))

    def load_model_data(self, data: VolumeData):
        """Sets preloaded VolumeData and builds the VTK rendering pipeline.

        Meant to be called on the main thread after VolumeData has been
        produced by a background worker.
        """
        self._data = data
        self._set_slider_values()
        self._render_model()


    def add_segmentation(self, seg_path: str) -> None:
        """Loads the raw data from seg_path, then calls the segmentation mesh renderer.

        The volume may have been downsampled during load_model (if it exceeded
        MAX_VOXELS), so the segmentation is downsampled to the same shape to
        keep VTK dimensions consistent.
        """

        # load and orient the raw voxel data
        raw_data = nib.load(seg_path).get_fdata(dtype=np.float32)
        raw_data = np.ascontiguousarray(np.transpose(raw_data, (2, 1, 0)).astype(np.int32))

        if self._data is not None:
            # downsample segmentation to match the (possibly downsampled) volume
            target_shape = self._data.voxels.shape
            if raw_data.shape != target_shape:
                factors = (target_shape[0] / raw_data.shape[0],
                           target_shape[1] / raw_data.shape[1],
                           target_shape[2] / raw_data.shape[2])
                raw_data = zoom(raw_data, factors, order=0).astype(np.int32)

            self._data.seg_labels = raw_data
            self._render_segmentation()
            self._max_op_sld.setValue(1)

    def remove_segmentation(self):
        self.renderer.RemoveViewProp(self._segmentation_actor)
        if self._data is not None:
            self._data.seg_labels = None
        self._caps = {}
        self._refresh_caps()
        self._max_op_sld.setValue(100)

    # ---- RENDERING ----

    def _render_model(self):
        """
        Multi-stage 3D rendering pipeline for the OCT scan. Uses vtkSmartVolumeMapper to convert the voxels into a
        3D volume, then applies the clipping planes to cut the resulting visualization according to the user's needs.
        Utilizes the opacity function as computed in `load_model` to set the overall transparency. Finally, calls
        `_init_caps` for future segmentation loading, in order to better highlight the segmentation's occupied volume.
        """

        # clean up the renderer in case this isn't the first volume being displayed
        self.renderer.RemoveAllViewProps()

        if self._data is not None:
            # Stage 1: load the voxel data into VTK
            vtk_arr = numpy_support.numpy_to_vtk(
                self._data.voxels.ravel(), deep=True, array_type=vtk.VTK_UNSIGNED_CHAR,
            )
            image = vtk.vtkImageData()
            image.GetPointData().SetScalars(vtk_arr)
            image.SetDimensions(self._data.dims)

            # Stage 2: map all voxels to a 3D volume
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

            # Stage 3: apply grayscale color scheme using the signal onset and the voxel intensity values
            onset = self._data.signal_onset
            color = vtk.vtkColorTransferFunction()
            color.AddRGBPoint(0.0, 0.0, 0.0, 0.0)
            color.AddRGBPoint(onset * 255, 0.0, 0.0, 0.0)
            color.AddRGBPoint(255.0, 1.0, 1.0, 1.0)

            # Stage 4: apply transparency level also using the signal onset, initially at 100%
            opacity = vtk.vtkPiecewiseFunction()
            opacity.AddPoint(0.0, 0.0)
            opacity.AddPoint(onset * 255, 0.0)
            opacity.AddPoint(255.0, 1.0)

            # Apply all the computed functions and set rendering parameters
            prop = vtk.vtkVolumeProperty()
            prop.SetScalarOpacity(opacity)
            prop.SetColor(color)
            prop.ShadeOff()
            prop.SetAmbient(0.25)
            prop.SetDiffuse(0.7)
            prop.SetSpecular(0.1)
            prop.SetInterpolationTypeToLinear()

            # Stage 5: create the final actor and add it to the renderer
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

            # For future segmentation: highlight the borders in the sliced volume
            self._init_caps()

    def _render_segmentation(self, ):
        """
        Multi-stage 3D rendering pipeline for the segmentation. Uses vtkSurfaceNets3D to convert the predicted labels
        into a 3D mesh, then creates a color lookup table for each label and applies the clipping planes to cut the
        resulting visualization according to the user's needs. Finally, converts the mesh into a polygon.
        """
        if self._data is not None and self._data.seg_labels is not None:

            # Stage 1: load the predicted labels into VTK
            seg_img = vtk.vtkImageData()
            seg_img.SetDimensions(self._data.dims)
            vtk_arr = numpy_support.numpy_to_vtk(
                self._data.seg_labels.ravel(), deep=True, array_type=vtk.VTK_INT,
            )
            seg_img.GetPointData().SetScalars(vtk_arr)

            # get the amount of labels in the segmentation map
            scalars = seg_img.GetPointData().GetScalars()
            label_values = sorted(int(v) for v in np.unique(vtk_to_numpy(scalars)))
            n_labels = len(label_values)

            # Stage 2: create a lookup table to assign a color to each label
            self._lut.SetNumberOfTableValues(n_labels)
            self._lut.SetRange(min(label_values), max(label_values))
            self._lut.Build()

            # assign colors dynamically and as spaced apart as possible
            for i, value in enumerate(label_values):
                if value == 0:
                    self._lut.SetTableValue(i, 0.0, 0.0, 0.0, 0.0)
                else:
                    r, g, b = label_to_spread_color(i, len(label_values))
                    self._lut.SetTableValue(i, r, g, b, 0.5)
                self._label_lut_lookup.update({value: i})

            # Stage 2b: duplicate the LUT for the caps with full opacity
            self._cap_lut.DeepCopy(self._lut)
            for i, value in enumerate(label_values):
                if value != 0:
                    colors: MutableSequence[float] = [0.0, 0.0, 0.0]
                    self._cap_lut.GetColor(i, colors)
                    self._cap_lut.SetTableValue(i, colors[0], colors[1], colors[2], 1.0)

            # Stage 3: use SurfaceNets3D to convert the label map into a 3D mesh
            self._segmentation_mesh.SetInputData(seg_img)
            for i, value in enumerate(label_values):
                self._segmentation_mesh.SetValue(i, value)
            self._segmentation_mesh.Update()

            # Stage 4: add the clipping planes to slice the segmentation
            dims = self._data.dims
            self._clip_fn.SetBounds(0, dims[0], 0, dims[1], 0, dims[2])

            clipper = vtk.vtkClipPolyData()
            clipper.SetInputConnection(self._segmentation_mesh.GetOutputPort())
            clipper.SetClipFunction(self._clip_fn)
            clipper.GenerateClippedOutputOff()
            clipper.InsideOutOn()

            # Stage 5: convert the mesh into a polygon that VTK can render
            mapper = vtk.vtkPolyDataMapper()
            mapper.SetInputConnection(clipper.GetOutputPort())
            mapper.ScalarVisibilityOn()
            mapper.SetScalarModeToUseCellData()
            mapper.SetArrayComponent(0)
            mapper.SetLookupTable(self._lut)
            mapper.SetScalarRange(0, n_labels)

            # tweak the actor parameters for improved visualization
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

            # add the result to the renderer
            self.renderer.AddViewProp(self._segmentation_actor)

    def call_render(self):
        """Simple callback function to refresh the renderer if the state has changed."""
        self._vtk_widget.GetRenderWindow().Render()

    def toggle_label_visibility(self, label_val: int, visible: bool) -> None:
        """Modifies the lookup table to show or hide the label with the given value."""

        colors: MutableSequence[float] = [0.0, 0.0, 0.0]

        lut_idx = self._label_lut_lookup.get(label_val)
        if lut_idx is not None:
            self._lut.GetColor(lut_idx, colors)
            if visible:
                self._lut.SetTableValue(lut_idx, colors[0], colors[1], colors[2], 0.5)
            else:
                self._lut.SetTableValue(lut_idx, colors[0], colors[1], colors[2], 0)

            # Tells VTK that the color lookup table got modified
            self._lut.Modified()
            self.call_render()

    def cleanup(self):
        """Cleanly closes all connections and rendering objects."""
        self.renderer.RemoveAllViewProps()
        rw = self._vtk_widget.GetRenderWindow()
        rw.RemoveRenderer(self.renderer)
        self._vtk_widget.Finalize()
        rw.Finalize()

    # ---- EVENTS ----

    def _set_slider_values(self):
        """Sets the correct slider steps and values once the model is loaded."""
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

    def _on_opacity_changed(self, _value):
        """Rebuilds the opacity function according to the new onset and maximum transparency values."""
        onset = self._onset_sld.value() / 1000.0
        max_op = self._max_op_sld.value() / 100.0

        self._onset_lbl.setText(f"Opacity onset: {onset:.3f}")
        self._max_op_lbl.setText(f"Max: {self._max_op_sld.value()}%")

        # Rebuild VTK opacity function
        self._opacity.RemoveAllPoints()
        self._opacity.AddPoint(0.0, 0.0)
        self._opacity.AddPoint(onset * 255, 0.0)
        self._opacity.AddPoint(255.0, max_op)

        # Tell VTK the opacity function changed and explicitly re-render the scene
        self._volume_mapper.Modified()
        self.call_render()

    def _on_plane_changed(self, _value):
        """Updates the clipping planes to slice the volume, ensuring that the bounds are set coherently."""
        axes = ("x", "y", "z")
        for a in axes:
            mn = getattr(self, f"_{a}_min_sld")
            mx = getattr(self, f"_{a}_max_sld")

            # safety check: only slice "forwards"
            if mn.value() > mx.value():
                mx.blockSignals(True)
                mx.setValue(mn.value())
                mx.blockSignals(False)

        # get all current slider values after the update
        x_min = self._x_min_sld.value()
        x_max = self._x_max_sld.value()
        y_min = self._y_min_sld.value()
        y_max = self._y_max_sld.value()
        z_min = self._z_min_sld.value()
        z_max = self._z_max_sld.value()

        # for each axis, modify the text labels
        for a in axes:
            mn, mx = getattr(self, f"_{a}_min_sld").value(), getattr(self, f"_{a}_max_sld").value()
            getattr(self, f"_{a}_min_lbl").setText(str(mn))
            getattr(self, f"_{a}_max_lbl").setText(str(mx))

        self._refresh_caps(full_range=False)

        # for each axis, move the clipping planes to the updated coordinates
        self._volume_mapper.SetCroppingRegionPlanes(
            float(x_min), float(x_max),
            float(y_min), float(y_max),
            float(z_min), float(z_max),
        )
        self._volume_mapper.Modified()

        # for each axis, update the clipping function
        self._clip_fn.SetBounds(
            float(x_min), float(x_max),
            float(y_min), float(y_max),
            float(z_min), float(z_max),
        )

        self.call_render()

    def _on_cluster_toggle(self, checked):
        self._volume_actor.SetVisibility(not checked)
        self._vtk_widget.GetRenderWindow().Render()

    def _on_reset(self):
        self._max_op_sld.setValue(100)
        if self._data is not None:
            self._onset_sld.setValue(int(self._data.signal_onset * 1000))
            self._x_min_sld.setValue(0)
            self._x_max_sld.setValue(self._data.dims[0])
            self._y_min_sld.setValue(0)
            self._y_max_sld.setValue(self._data.dims[1])
            self._z_min_sld.setValue(0)
            self._z_max_sld.setValue(self._data.dims[2])

    # ---- VISUALIZATION AIDS ----

    def _init_caps(self):
        for axis in ("x", "y", "z"):
            for side in ("min", "max"):
                self._caps[(axis, side)] = self._make_cap_actor()
        self._refresh_caps(full_range=True)

    def _make_cap_actor(self):
        """Add region bounds to the segmentation if the volume has been sliced."""
        img = vtk.vtkImageData()
        color_map = vtk.vtkImageMapToColors()
        color_map.SetLookupTable(self._cap_lut)
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
        """Update a single cap slice from the segmentation labels."""
        img, color_map, actor = cap
        x_min, x_max, y_min, y_max, z_min, z_max = bounds
        axis_idx = {"x": 0, "y": 1, "z": 2}[axis]
        if self._data is not None:
            # clamp index to valid range for this axis
            index = max(0, min(index, self._data.dims[axis_idx] - 1))

            sm = self._data.seg_labels
            if sm is not None:
                # extract a single face from the segmentation volume along the given axis
                # VTK order is (Z, Y, X), so the axis mapping differs from the spatial names
                if axis == "x":
                    face = sm[z_min:z_max, y_min:y_max, index:index + 1]
                    origin = (index, y_min, z_min)
                elif axis == "y":
                    face = sm[z_min:z_max, index:index + 1, x_min:x_max]
                    origin = (x_min, index, z_min)
                else:
                    face = sm[index:index + 1, y_min:y_max, x_min:x_max]
                    origin = (x_min, y_min, index)

                # push numpy data into VTK image and position it at the correct origin
                flat = np.ascontiguousarray(face.astype(np.int32))
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
        if self._data is not None:
            d = self._data.dims

            # either clamp the values or choose the current slider values as the coordinates
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