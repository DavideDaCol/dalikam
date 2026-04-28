import pyvista as pv
from nibabel.filebasedimages import FileBasedImage

class viewerModel:
    def __init__(self) -> None:
        self.raw_data: pv.BaseReader | pv.DICOMReader | None = None

    def set_raw_data(self, path: str) -> pv.BaseReader | pv.DICOMReader:
        # TODO move this function to an async thread
        print(f"starting load of file at path {path}")
        self.raw_data = pv.get_reader(path)
        print("file is done loading")
        return self.raw_data
    
    # REVIEW potentially unneeded
    def get_raw_data(self) -> pv.BaseReader | pv.DICOMReader:
        if self.raw_data:
            return self.raw_data
        else:
            print("CRITICAL: trying to access a file that was not loaded.")
            raise FileNotFoundError 