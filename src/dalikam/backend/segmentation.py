import hashlib
import re
from pathlib import Path

from PyQt6.QtCore import QObject, QProcess, pyqtSignal
from PyQt6.QtWidgets import QPlainTextEdit, QDialog, QVBoxLayout, QLabel, QProgressBar, QPushButton

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

class InferenceProgressWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("inferenceProgressWindow")
        self.setWindowTitle("AI Inference")
        self.resize(550, 400)
        self.setModal(True)

        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        # Message Label
        self.label = QLabel("Creating segmentation map...", self)
        layout.addWidget(self.label)

        # Indefinite Progress Bar
        # TODO consider updating this progress bar to follow nnUNet's logs
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 0) # Smooth loading animation
        layout.addWidget(self.progress_bar)

        # Log Text Box
        self.log_text = QPlainTextEdit(self)
        self.log_text.setReadOnly(True)
        self.log_text.setObjectName("logBox")
        layout.addWidget(self.log_text)

        # Cancel Button
        self.cancel_button = QPushButton("Cancel", self)
        layout.addWidget(self.cancel_button)

class SegmentationWorker(QObject):
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
        self.dialog_window: InferenceProgressWindow | None = None

    def run(self):

        print("thread has started execution")

        self.process = QProcess(self)

        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.readyReadStandardError.connect(self.handle_stderr)
        self.process.finished.connect(self.handle_end)

        self.dialog_window = InferenceProgressWindow()
        if self.dialog_window:
            self.dialog_window.cancel_button.clicked.connect(self.process.kill)

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
        self.dialog_window.show()


    def handle_stdout(self):
        if self.process is not None:
            data = self.process.readAllStandardOutput()
            text = data.data().decode("utf-8", errors="replace")
            print(f"output pipe said:\n{text}")
            if self.dialog_window:
                self.dialog_window.log_text.appendPlainText(text)

    def handle_stderr(self):
        if self.process is not None:
            data = self.process.readAllStandardError()
            text = data.data().decode("utf-8", errors="replace")
            print(f"error pipe said:\n{text}")
            if self.dialog_window:
                self.dialog_window.log_text.appendPlainText(text)

    def handle_end(self, exit_code):
        print("thread has finished execution")

        if self.dialog_window is not None:
            self.dialog_window.close()

        # To notify the end of inference
        if exit_code == 0:
            self.done_segmentation.emit(exit_code)

        # To tell the thread to close everything
        self.deleteLater()




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
        self.final_file: Path | None = None
        # TODO this .tmp folder is ridiculous, use the tempfile module instead 
        self.tmp_dir: Path = Path(".tmp").resolve()
        self.file_hash: str | None = None
        self.worker: SegmentationWorker | None = None
        self.segmentation_loaded: bool = False

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

        # get the path to the model weights from the settings.
        # this changes depending on the chosen model type
        saved_model_type = self.settings.get_preferred_model_type()
        saved_model_path = self.settings.get_model_path(saved_model_type) if saved_model_type else ""
        if saved_model_path:
            model_folder = Path(saved_model_path)
        else:
            model_folder = Path(__file__).resolve().parents[0] / "models" / "default"

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
            if not symlink_path.exists():
                symlink_path.symlink_to(path.resolve())

            device = self.settings.get_preferred_device()

            # Instantiate a new worker
            self.worker = SegmentationWorker(CONDA, ENV, self.tmp_dir, model_folder, predictions_folder, device)
            if self.worker:
                self.worker.done_segmentation.connect(self.conclude_segmentation)
                self.worker.run()

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
