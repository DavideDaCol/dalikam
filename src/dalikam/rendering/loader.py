import nibabel as nib
import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal

from dalikam.rendering.threed import VolumeData, downsample_volume, noise_floor_heuristic, MAX_VOXELS
from dalikam.tools.load_timer import LoadTimer


class VolumeLoadWorker(QObject):
    progress = pyqtSignal(int)
    status_message = pyqtSignal(str)
    finished = pyqtSignal(object)

    def __init__(self, path: str, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._path = path

    def run(self):
        timer = LoadTimer("Volume load timing (loader.py)")
        try:
            with timer.measure("read_affine"):
                affine = nib.load(self._path).affine
            self.progress.emit(10)

            with timer.measure("read_voxels"):
                scan = nib.load(self._path).get_fdata(dtype=np.float32)
            self.progress.emit(40)

            source_dims = scan.shape

            with timer.measure("voxel_processing"):
                with timer.measure("normalize"):
                    lo, hi = np.percentile(scan, 1), np.percentile(scan, 99)
                    scan = np.clip(scan, lo, hi)
                    scan = (scan - lo) / (hi - lo)
                self.progress.emit(60)

                with timer.measure("downsample"):
                    if scan.size > MAX_VOXELS:
                        factor = (MAX_VOXELS / scan.size) ** (1.0 / 3)
                        shape_str = f"{scan.shape[0]}x{scan.shape[1]}x{scan.shape[2]}"
                        self.status_message.emit(f"Downsampling volume ({shape_str})...")
                        scan, affine = downsample_volume(scan, affine, factor)
                        self.status_message.emit("Downsampling complete")
            self.progress.emit(70)

            with timer.measure("transpose"):
                scan = np.ascontiguousarray(np.transpose(scan, (2, 1, 0)))
                dims = (scan.shape[2], scan.shape[1], scan.shape[0])
            self.progress.emit(75)

            with timer.measure("noise_floor"):
                onset = noise_floor_heuristic(scan)
            self.progress.emit(90)

            with timer.measure("uint8_convert"):
                scan_u8 = np.ascontiguousarray((scan * 255).astype(np.uint8))

            timer.report()

            data = VolumeData(scan_u8, None, dims, onset, affine, source_dims)
            self.finished.emit(data)
        except Exception as e:
            self.finished.emit(e)
