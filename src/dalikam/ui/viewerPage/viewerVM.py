from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal

from dalikam.backend.segmentation import SegmentationManager
from dalikam.router.router import Router
from dalikam.ui.filePage.fileModel import FileInfo
from dalikam.ui.viewerPage.viewerModel import viewerModel


class ViewerVM(QObject):
    draw_file: pyqtSignal = pyqtSignal(object)
    labels_changed: pyqtSignal = pyqtSignal(list)

    def __init__(self, model: viewerModel, manager: SegmentationManager, router: Router) -> None:
        super().__init__()
        self._model: viewerModel = model
        self._manager: SegmentationManager = manager
        self._router: Router = router

    def set_file(self, file: FileInfo):
        raw_data = self._model.set_raw_data(file.path)
        self.draw_file.emit(raw_data)

    def set_labels(self):
        labels = self._model.get_labels()
        if labels is not None:
            self.labels_changed.emit(labels)

    def testlabels(self):
        self.labels_changed.emit(["label one", "label two", "label three"])

    def start_segmentation(self) -> Path | None:
        result = self._manager.run_segmentation(Path(self._model.get_path()))
        if result is not None:
            labels = viewerModel.extract_labels_from_nifti(str(result))
            self._model.labels = [str(l) for l in labels]
            self.labels_changed.emit(self._model.labels)
        return result
