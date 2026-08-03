import os
from typing import Protocol

import nibabel as nib
from PyQt6.QtWidgets import QMessageBox, QWidget


def verify_segmentation_extents(
    volume_extents: tuple[tuple[int, int], tuple[int, int], tuple[int, int]],
    seg_extents: tuple[tuple[int, int], tuple[int, int], tuple[int, int]],
) -> bool:
    """Check that a segmentation map spans the same volume as the scan on every axis.

    Compares the (min, max) pairs of the X, Y and Z axes of the original scan
    against the segmentation map, so mismatches are caught before rendering.

    Args:
        `volume_extents (tuple)`: three (min, max) pairs for the X, Y and Z axes
            of the original scan.
        `seg_extents (tuple)`: three (min, max) pairs for the X, Y and Z axes
            of the segmentation map.

    Returns:
        `bool`: True when the segmentation matches the scan on every axis.
    """
    return all(v == s for v, s in zip(volume_extents, seg_extents))


def is_valid_segmentation(path: str) -> bool:
    """Return True when `path` is a NIfTI file containing scalar 3D label data.

    Runs the pre-load controls on the segmentation file alone: the path must
    exist on the file system, the extension must be NIfTI (and the file must
    actually load as one), and the contents must be a scalar 3D volume.
    """
    if not os.path.isfile(path):
        return False
    if not (path.endswith(".nii") or path.endswith(".nii.gz")):
        return False
    try:
        img = nib.load(path)
    except Exception:
        return False
    return len(img.shape) == 3


def segmentation_matches_scan(scan_path: str, seg_path: str) -> bool:
    """Return True when the segmentation spans the same volume as the scan.

    Compares the (X, Y, Z) dimensions of both NIfTI files via nibabel, so it
    agrees with the per-renderer extent checks regardless of any downsampling.
    """
    try:
        scan_shape = nib.load(scan_path).shape
        seg_shape = nib.load(seg_path).shape
    except Exception:
        return False
    if len(scan_shape) != 3 or len(seg_shape) != 3:
        return False
    return verify_segmentation_extents(
        ((0, scan_shape[0] - 1), (0, scan_shape[1] - 1), (0, scan_shape[2] - 1)),
        ((0, seg_shape[0] - 1), (0, seg_shape[1] - 1), (0, seg_shape[2] - 1)),
    )


def show_invalid_segmentation(parent: QWidget | None) -> None:
    """Display an error box for a file that is not a valid segmentation map."""
    QMessageBox.critical(
        parent,
        "Invalid segmentation map",
        "The file you tried to load is either not a segmentation map "
        "or does not match the dimensions of the OCT scan.",
    )


class Visualizer(Protocol):
    def load_model(self, data: str): ...

    def add_segmentation(self, seg_path: str): ...

    def remove_segmentation(self): ...

    def call_render(self): ...

    def cleanup(self): ...

    def toggle_label_visibility(self, label_val: int, visible: bool): ...

    def update_label_color(self, label_val: int, color: tuple[float, float, float]) -> None: ...
