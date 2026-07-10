import numpy as np
import vtkmodules.all as vtk
from vtkmodules.util.numpy_support import vtk_to_numpy


class viewerModel:
    def __init__(self) -> None:
        self.raw_data: vtk.vtkNIFTIImageReader = vtk.vtkNIFTIImageReader()
        self.path_data: str = ""
        self.labels: list[str] | None = None

    def set_raw_data(self, path: str) -> vtk.vtkNIFTIImageReader:
        # TODO move the raw_data update call to the viewmodel (and also a thread)
        print(f"starting load of file at path {path}")
        self.path_data = path
        self.raw_data.SetFileName(path)
        self.raw_data.Update()
        print("file is done loading")
        return self.raw_data

    # REVIEW potentially unneeded
    def get_raw_data(self) -> vtk.vtkNIFTIImageReader:
        header = self.raw_data.GetNIFTIHeader()
        if header != "" and header is not None:
            return self.raw_data
        else:
            print("CRITICAL: trying to access a file that was not loaded.")
            raise FileNotFoundError

    def get_path(self):
        return self.path_data

    def get_labels(self) -> list[str] | None:
        return self.labels

    @staticmethod
    def extract_labels_from_nifti(path: str) -> list[int]:
        """Read a NIfTI segmentation file and return the unique label values found."""
        reader = vtk.vtkNIFTIImageReader()
        reader.SetFileName(path)
        reader.Update()
        scalars = reader.GetOutput().GetPointData().GetScalars()
        unique_vals = np.unique(vtk_to_numpy(scalars))
        return sorted(int(v) for v in unique_vals if v != 0)
