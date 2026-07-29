import nibabel as nib
import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal

from dalikam.rendering.threed import VolumeData, downsample_volume, noise_floor_heuristic, MAX_VOXELS


class VolumeLoadWorker(QObject):
    progress = pyqtSignal(int)
    status_message = pyqtSignal(str)
    finished = pyqtSignal(object)

    def __init__(self, path: str, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._path = path

    def run(self):
        try:
            affine = nib.load(self._path).affine
            self.progress.emit(10)

            scan = nib.load(self._path).get_fdata(dtype=np.float32)
            self.progress.emit(40)

            lo, hi = np.percentile(scan, 1), np.percentile(scan, 99)
            scan = np.clip(scan, lo, hi)
            scan = (scan - lo) / (hi - lo)
            self.progress.emit(60)

            if scan.size > MAX_VOXELS:
                factor = (MAX_VOXELS / scan.size) ** (1.0 / 3)
                shape_str = f"{scan.shape[0]}x{scan.shape[1]}x{scan.shape[2]}"
                self.status_message.emit(f"Downsampling volume ({shape_str})...")
                scan, affine = downsample_volume(scan, affine, factor)
                self.status_message.emit("Downsampling complete")
            self.progress.emit(70)

            scan = np.ascontiguousarray(np.transpose(scan, (2, 1, 0)))
            dims = (scan.shape[2], scan.shape[1], scan.shape[0])
            self.progress.emit(75)

            onset = noise_floor_heuristic(scan)
            self.progress.emit(90)

            scan_u8 = np.ascontiguousarray((scan * 255).astype(np.uint8))

            data = VolumeData(scan_u8, None, dims, onset, affine)
            self.finished.emit(data)
        except Exception as e:
            self.finished.emit(e)
