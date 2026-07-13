from dataclasses import dataclass, field
from pathlib import Path
import json
import shutil
import tempfile
import zipfile

from dalikam.backend.state import StateManager
from dalikam.tools.utils import get_device_map

DATASET_REQUIRED_FIELDS = {"channel_names", "labels", "numTraining", "file_ending"}
PLANS_REQUIRED_FIELDS = {"configurations", "dataset_name"}


@dataclass
class VerificationResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    fold_count: int = 0


def _models_root() -> Path:
    return Path(__file__).resolve().parents[2] / "backend" / "models"


class SettingsModel:
    def __init__(self):
        self.settings = StateManager()

    def set_device(self, index: int):
        device = get_device_map().get(index)
        if device is not None:
            self.settings.set_preferred_device(device)

    def get_device_index(self) -> int:
        device = self.settings.get_preferred_device()
        device_map = get_device_map()
        reverse = {v: k for k, v in device_map.items()}
        return reverse.get(device, 0)

    def get_preferred_model_type(self) -> str:
        return self.settings.get_preferred_model_type()

    def set_preferred_model_type(self, model_type: str) -> None:
        self.settings.set_preferred_model_type(model_type)

    def get_model_path(self, model_type_key: str) -> str:
        return self.settings.get_model_path(model_type_key)

    def delete_model_path(self, model_type_key: str) -> None:
        path = self.settings.get_model_path(model_type_key)
        if path:
            model_dir = Path(path)
            if model_dir.is_dir():
                shutil.rmtree(model_dir)
        self.settings.delete_model_path(model_type_key)

    def delete_saved_segmentations(self) -> None:
        self.settings.delete_sm_files()
        predictions_dir = Path(__file__).resolve().parents[2] / "backend" / "predictions"
        if predictions_dir.is_dir():
            shutil.rmtree(predictions_dir)

    def delete_scan_paths(self) -> None:
        self.settings.delete_raw_files()

    def load_model(self, zip_path: Path, model_type_key: str) -> str:
        """Extract a model zip archive into backend/models/<name>/.

        The archive must contain dataset.json and plans.json at its top level
        (or inside a single subdirectory), plus fold_*/checkpoint_final.pth files.

        The model_type_key (e.g. "3d_lowres") is used to store the path under
        that specific model configuration.

        Returns a description string for display in the UI.
        Raises ValueError on invalid archives.
        """
        if not zip_path.is_file():
            raise ValueError(f"File not found: {zip_path}")

        model_name = zip_path.stem
        dest = _models_root() / model_name

        if dest.exists():
            shutil.rmtree(dest)

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(tmp_path)

            contents = list(tmp_path.iterdir())
            if (
                len(contents) == 1
                and contents[0].is_dir()
                and not (contents[0] / "dataset.json").exists()
            ):
                extract_root = contents[0]
            else:
                extract_root = tmp_path

            if not (extract_root / "dataset.json").exists():
                raise ValueError("Zip archive is missing dataset.json")
            if not (extract_root / "plans.json").exists():
                raise ValueError("Zip archive is missing plans.json")

            shutil.copytree(extract_root, dest)

        self.settings.set_model_path(model_type_key, str(dest))
        return f"Loaded model '{model_name}' from {zip_path.name}"

    def verify_model(self, model_type_key: str) -> VerificationResult:
        """Validate that the model directory for the given type contains valid
        nnUNet inference artifacts."""
        model_dir = Path(self.settings.get_model_path(model_type_key))
        if not model_dir.is_dir():
            raise ValueError("No model loaded for this configuration")

        result = VerificationResult()

        dataset_path = model_dir / "dataset.json"
        plans_path = model_dir / "plans.json"

        if not dataset_path.exists():
            result.errors.append("dataset.json is missing")
        else:
            try:
                with open(dataset_path) as f:
                    ds = json.load(f)
                missing = DATASET_REQUIRED_FIELDS - ds.keys()
                if missing:
                    result.errors.append(f"dataset.json is missing fields: {', '.join(sorted(missing))}")
            except json.JSONDecodeError as e:
                result.errors.append(f"dataset.json is not valid JSON: {e}")

        if not plans_path.exists():
            result.errors.append("plans.json is missing")
        else:
            try:
                with open(plans_path) as f:
                    plans = json.load(f)
                missing = PLANS_REQUIRED_FIELDS - plans.keys()
                if missing:
                    result.errors.append(f"plans.json is missing fields: {', '.join(sorted(missing))}")
                else:
                    configs = plans.get("configurations", {})
                    if model_type_key not in configs:
                        result.warnings.append(
                            f"Configuration '{model_type_key}' not found in plans.json "
                            f"(available: {', '.join(sorted(configs.keys()))})"
                        )
            except json.JSONDecodeError as e:
                result.errors.append(f"plans.json is not valid JSON: {e}")

        fold_dirs = list(model_dir.glob("fold_*/checkpoint_final.pth"))
        result.fold_count = len(fold_dirs)
        if not fold_dirs:
            result.errors.append("No fold_*/checkpoint_final.pth found")
        elif not any((model_dir / f"fold_{i}" / "checkpoint_final.pth").exists() for i in range(10)):
            result.warnings.append("No standard fold directory (fold_0..fold_9) found")

        return result
