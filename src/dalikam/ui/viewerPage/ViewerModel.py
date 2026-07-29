import numpy as np
import vtkmodules.all as vtk
from vtkmodules.util.numpy_support import vtk_to_numpy


class ViewerModel:
    def __init__(self) -> None:
        self.path_data: str = ""
        self.labels: list[str] | None = None

    def get_path(self):
        return self.path_data

    def get_labels(self) -> list[str] | None:
        return self.labels

    # TODO consider moving this to nibabel
    @staticmethod
    def extract_labels_from_nifti(path: str) -> list[int]:
        """Read a NIfTI segmentation file and return the unique label values found."""
        reader = vtk.vtkNIFTIImageReader()
        reader.SetFileName(path)
        reader.Update()
        scalars = reader.GetOutput().GetPointData().GetScalars()
        values = np.unique(vtk_to_numpy(scalars))
        return sorted(int(v) for v in values if v != 0)
