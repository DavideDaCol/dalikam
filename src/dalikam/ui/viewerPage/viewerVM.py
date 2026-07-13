from datetime import datetime
from pathlib import Path
import shutil

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
    segmentation_ended = pyqtSignal(Path)
    segmentation_loaded = pyqtSignal(Path)

    def __init__(self, model: viewerModel, manager: SegmentationManager, router: Router) -> None:
        super().__init__()
        self._model: viewerModel = model
        self._manager: SegmentationManager = manager
        self._router: Router = router
        self._result_path: Path | None = None
        self._manager.completed_segmentation.connect(self.end_segmentation)

    def set_file(self, file: FileInfo):
        raw_data = self._model.set_raw_data(file.path)
        self.draw_file.emit(raw_data)

    def init_labels(self):
        self.labels_changed.emit(["load or create a segmentation map to view its labels"], [-1], {})

    def start_segmentation(self):
        self._manager.run_segmentation(Path(self._model.get_path()))
    
    def end_segmentation(self, result: Path):
        self._result_path = result
        labels = viewerModel.extract_labels_from_nifti(str(result))
        colors = generate_label_colors(labels)
        named_labels = list(map(to_names,labels))
        self._model.labels = named_labels
        self.labels_changed.emit(self._model.labels, labels, colors)
        self.segmentation_ended.emit(result)

    def export_segmentation(self, save_dir: Path) -> Path:
        """Copy the segmentation result to save_dir with a clean timestamped name."""
        stem = Path(self._model.get_path()).with_suffix("").stem
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        dest = save_dir / f"{stem}_{timestamp}.nii.gz"
        shutil.copy2(str(self._result_path), dest)
        return dest

    def load_external_segmentation(self, path: Path):
        """Load an external segmentation file, reusing the existing pipeline."""
        self.end_segmentation(path)
        self.segmentation_loaded.emit(path)
