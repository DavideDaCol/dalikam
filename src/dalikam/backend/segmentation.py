import hashlib
import re
from pathlib import Path

from PyQt6.QtCore import QObject, QThread, QProcess, pyqtSignal
from PyQt6.QtWidgets import QDialog

from dalikam.backend.state import StateManager
from dalikam.tools.utils import get_env_name, get_micromamba_dir

UniqueFile = tuple[Path, str]


def build_hash(path: Path) -> str:
    """Compute the hash of a file using the specified algorithm."""
    hash_fx = hashlib.new("sha256")

    with open(path, "rb") as file:
        while chunk := file.read(8192):
            hash_fx.update(chunk)

    return hash_fx.hexdigest()


def build_nnunet_name(path: Path, file_hash: str) -> str:
    """Rename the file to respect nnUNet's naming conventions"""
    file_name = path.name
    renamed = re.sub(".nii.gz", "_" + file_hash + "_0000.nii.gz", file_name)
    return renamed

class SegmentationWorker(QObject):
    finished = pyqtSignal()
    done_segmentation = pyqtSignal(int)
    progress_log = pyqtSignal(str)

    def __init__(self, conda_path, env_name, input_path: Path,  model_path: Path, prediction_path: Path, device: str):
        super().__init__()
        self.conda = str(conda_path)
        self.env_name = str(env_name)
        self.input_path = str(input_path)
        self.model_path = str(model_path)
        self.prediction_path = str(prediction_path)
        self.device = device
        self.process: QProcess | None = None

    def run(self):

        print("thread has started execution")

        self.process = QProcess(self)

        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.finished.connect(self.handle_end)

        inference_arguments = [
                "run",
                "-n", self.env_name,
                "nnUNetv2_predict_from_modelfolder",
                "-i", self.input_path,
                "-o", self.prediction_path,
                "-m", self.model_path,
                "-f", "4",
                "-device", self.device
            ]
        
        self.process.start(self.conda, inference_arguments)


    def handle_stdout(self):
        if self.process is not None:
            data = self.process.readAllStandardOutput()
            text = data.data().decode("utf-8", errors="replace")
            print(f"thread said:\n{text}")

    def handle_end(self, exit_code):
        print("thread has finished execution")

        # To notify the end of inference
        self.done_segmentation.emit(exit_code)

        # To tell the thread to close everything
        self.finished.emit()




class SegmentationManager(QObject):
    """ 
        Backend coordinator class; its purpose is to orchestrate the segmentation process by creating
        and renaming files, calling the nnUNet inference command and loading the resulting segmentation
        in the segmentation map.

        Attributes:
            settings:           Central state module to access persistent application data
            segmentation_map :  Hashmap that associates OCT scans to their segmentation map
            segmentation_load:  Notifies if inference is done
    """

    completed_segmentation = pyqtSignal(Path)

    def __init__(self) -> None:
        super().__init__()
        self.settings: StateManager = StateManager()
        self.segmentation_map: dict[str, Path] = self.settings.get_sm_files()
        self.progress_window: QDialog = QDialog()
        self.final_file: Path | None = None
        # TODO this .tmp folder is ridiculous, use the tempfile module instead 
        self.tmp_dir: Path = Path(".tmp").resolve()
        self.file_hash: str | None = None
        self.segmentation_thread: QThread | None = None
        self.worker: SegmentationWorker | None = None
        self.segmentation_loaded: bool = False

        

        # TODO add a "ML model loader" that creates the "fold" structure that nnUNet needs 

    def segmentation_present(self, file_hash: str) -> bool:
        """Reads the sha256 hash of a file to check if it has already been segmented"""
        # Get old saved values from persistent data structure
        paths = self.settings.get_sm_files()

        if paths.get(file_hash) is not None:
            return True

        return False

    # WARN this only runs nnUNet for now, since samED isn't working yet
    def run_segmentation(self, path: Path):
        """Creates a segmentation map using the inference engine."""

        print(f"start inference run for file {path}")

        # Build hash for this file
        hashed_file = build_hash(path)
        self.file_hash = hashed_file

        CONDA = get_micromamba_dir()
        ENV = get_env_name()

        model_folder = Path(__file__).resolve().parents[0].joinpath("models")
        predictions_folder = Path(__file__).resolve().parents[0].joinpath("predictions")

        if path.name.endswith('.nii.gz'):
            base = path.name[:-7]
            self.final_file = predictions_folder / f"{base}_{hashed_file}.nii.gz"
        else:
            self.final_file = predictions_folder / f"{path.stem}_{hashed_file}{path.suffix}"

        print(f"the hash for this file is {hashed_file}. is it saved? {self.segmentation_present(hashed_file)}")

        # Has this file been segmented before? if it has, don't bother, otherwise...
        if not self.segmentation_present(hashed_file):

            if not predictions_folder.exists():
                predictions_folder.mkdir()

            # create a symlink to the file with the nnUNet naming convention.
            # This doesn't move the original file and makes no copies.

            symlink_name = build_nnunet_name(path, hashed_file)
            self.tmp_dir.mkdir(exist_ok=True)
            symlink_path = self.tmp_dir.joinpath(symlink_name)
            symlink_path.symlink_to(path.resolve())

            # Instantiate a new thread
            self.segmentation_thread = QThread()

            # Instantiate a new worker
            self.worker = SegmentationWorker(CONDA, ENV, self.tmp_dir, model_folder, predictions_folder, "cuda")

            self.worker.moveToThread(self.segmentation_thread)

            self.segmentation_thread.started.connect(self.worker.run)
            self.worker.finished.connect(self.segmentation_thread.quit)

            self.worker.finished.connect(self.worker.deleteLater)
            self.segmentation_thread.finished.connect(self.segmentation_thread.deleteLater)

            self.worker.done_segmentation.connect(self.conclude_segmentation)

            self.segmentation_thread.start()

        else:
            self.conclude_segmentation()

    
    def conclude_segmentation(self):
        self.settings.update_sm_files(self.file_hash, self.final_file)
        if self.tmp_dir.exists():
            for file in self.tmp_dir.glob("*"):
                file.unlink()
            self.tmp_dir.rmdir()
        if self.final_file is not None:
            self.completed_segmentation.emit(self.final_file)
