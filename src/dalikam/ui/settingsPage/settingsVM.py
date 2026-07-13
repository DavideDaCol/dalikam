from PyQt6.QtCore import QObject, QProcess, pyqtSignal
from pathlib import Path

from dalikam.tools.utils import get_micromamba_dir, get_env_name
from dalikam.ui.settingsPage.settingsModel import SettingsModel, VerificationResult

MODEL_TYPE_KEYS = {
    "nnUNet (3D Low-Res)": "3d_lowres",
    "nnUNet (3D Full-Res)": "3d_fullres",
    "nnUNet (2D)": "2d",
}


class HardwareWorker(QObject):
    """
        Spawns a QProcess to enter the inference environment and control hardware availability.
        Returns the information using signals and informs the user with a QDialog window.

        Attributes:
            process: the QProcess instance that enters the inference environment.
    """
    hardware_controlled = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self.process: QProcess | None = None

    def run(self):
        self.process = QProcess(self)
        self.process.readyReadStandardOutput.connect(self.push_result)
        self.process.finished.connect(self.process.deleteLater)

        print("created worker thread")

        conda = get_micromamba_dir()
        env_name = get_env_name()
        script_path = Path(__file__).parent / "check_devices.py"

        arguments = [
            "run", "-n", env_name,
            "python", str(script_path)
        ]

        print("starting device check")

        self.process.start(str(conda), arguments)

        print("finished device check")

    def push_result(self):
        if self.process is not None:
            data = self.process.readAllStandardOutput()
            text = data.data().decode("utf-8", errors="replace")
            print(f"torch test result: {text}")
            self.hardware_controlled.emit(text)

class SettingsVM(QObject):
    results_ready = pyqtSignal(str)
    model_loaded = pyqtSignal(str)

    def __init__(self, model: SettingsModel):
        super().__init__()
        self._model: SettingsModel = model
        self.worker: HardwareWorker | None = None

    def check_inference_device(self):
        self.worker = HardwareWorker()
        self.worker.hardware_controlled.connect(self.create_window)
        self.worker.run()

    def create_window(self, contents: str):
        self.results_ready.emit(contents)

    def get_device_index(self) -> int:
        return self._model.get_device_index()

    def set_device(self, index):
        print(f"received index {index}")
        self._model.set_device(index)

    def load_model(self, zip_path: Path, model_type_key: str):
        try:
            result = self._model.load_model(zip_path, model_type_key)
            self.model_loaded.emit(result)
        except ValueError as e:
            self.model_loaded.emit(str(e))

    def get_model_path(self, model_type_key: str) -> str:
        return self._model.get_model_path(model_type_key)

    def get_preferred_model_type(self) -> str:
        return self._model.get_preferred_model_type()

    def set_preferred_model_type(self, model_type: str) -> None:
        self._model.set_preferred_model_type(model_type)

    def verify_model(self, model_type_key: str):
        try:
            result: VerificationResult = self._model.verify_model(model_type_key)
            self.results_ready.emit(self._format_verification(result))
        except ValueError as e:
            self.results_ready.emit(str(e))

    def delete_weight_paths(self) -> None:
        for key in MODEL_TYPE_KEYS.values():
            self._model.delete_model_path(key)
        self.model_loaded.emit("All weight paths have been deleted")

    def delete_saved_segmentations(self) -> None:
        self._model.delete_saved_segmentations()
        self.results_ready.emit("Saved segmentations have been deleted")

    def delete_scan_paths(self) -> None:
        self._model.delete_scan_paths()
        self.results_ready.emit("Scan paths have been deleted")

    def _format_verification(self, result: VerificationResult) -> str:
        if result.errors:
            lines = ["Verification FAILED:"]
            lines.extend(f"  - {e}" for e in result.errors)
            return "\n".join(lines)

        lines = ["Verification OK"]
        if result.warnings:
            lines.append("Warnings:")
            lines.extend(f"  - {w}" for w in result.warnings)
        lines.append(f"Found {result.fold_count} fold checkpoint(s)")
        return "\n".join(lines)
