import vtkmodules.all as vtk


class viewerModel:
    def __init__(self) -> None:
        self.raw_data: vtk.vtkNIFTIImageReader = vtk.vtkNIFTIImageReader()
        self.path_data: str = ""
        self.labels: list[str] | None = None

    def set_raw_data(self, path: str) -> vtk.vtkNIFTIImageReader:
        # TODO move this function to an async thread
        print(f"starting load of file at path {path}")
        self.path_data = path
        self.raw_data.SetFileName(path)
        self.raw_data.Update()
        print("file is done loading")
        return self.raw_data

    # REVIEW potentially unneeded
    def get_raw_data(self) -> vtk.vtkNIFTIImageReader:
        if self.raw_data.GetNIFTIHeader() != "":
            return self.raw_data
        else:
            print("CRITICAL: trying to access a file that was not loaded.")
            raise FileNotFoundError

    def get_path(self):
        return self.path_data

    def get_labels(self) -> list[str] | None:
        return self.labels
