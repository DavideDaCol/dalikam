from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal

from dalikam.backend.segmentation import SegmentationManager
from dalikam.router.router import Router
from dalikam.tools.utils import generate_label_colors
from dalikam.ui.filePage.fileModel import FileInfo
from dalikam.ui.viewerPage.viewerModel import viewerModel

def to_names(val: int) -> str:
    """Maps label indexes to the respective fluid name"""
    if val == 1:
        return "Intraretinal fluid (IRF)"
    elif val == 2:
        return "Subretinal fluid (SRF)"
    elif val == 3:
        return "Pigment Epithelial Detachment (PED)"
    else:
        return "Unknown Label"

class ViewerVM(QObject):
    draw_file: pyqtSignal = pyqtSignal(object)
    labels_changed: pyqtSignal = pyqtSignal(list,list,dict)

    def __init__(self, model: viewerModel, manager: SegmentationManager, router: Router) -> None:
        super().__init__()
        self._model: viewerModel = model
        self._manager: SegmentationManager = manager
        self._router: Router = router

    def set_file(self, file: FileInfo):
        raw_data = self._model.set_raw_data(file.path)
        self.draw_file.emit(raw_data)

    def init_labels(self):
        self.labels_changed.emit(["load or create a segmentation map to view its labels"], [-1], {})

    def start_segmentation(self) -> Path | None:
        result = self._manager.run_segmentation(Path(self._model.get_path()))
        if result is not None:
            labels = viewerModel.extract_labels_from_nifti(str(result))
            colors = generate_label_colors(labels)
            named_labels = list(map(to_names,labels))
            self._model.labels = named_labels
            self.labels_changed.emit(self._model.labels, labels, colors)
        return result
