import hashlib
import re
import subprocess
from pathlib import Path

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


class SegmentationManager:
    """ 
        Backend coordinator class; its purpose is to orchestrate the segmentation process by creating
        and renaming files, calling the nnUNet inference command and loading the resulting segmentation
        in the segmentation map.

        Attributes:
            settings:           Central state module to access persistent application data
            segmentation_map :  Hashmap that associates OCT scans to their segmentation map
            segmentation_load:  Notifies if inference is done
    """

    def __init__(self) -> None:
        self.settings: StateManager = StateManager()
        self.segmentation_map: dict[str, Path] = self.settings.get_sm_files()
        self.segmentation_loaded: bool = False

        # TODO add a "ML model loader" that creates the "fold" structure that nnUNet needs 

        self.settings.remove_segmentations()

    def segmentation_present(self, file_hash: str) -> bool:
        """Reads the sha256 hash of a file to check if it has already been segmented"""
        # Get old saved values from persistent data structure
        paths = self.settings.get_sm_files()

        if paths is not None:
            if paths.get(file_hash) is not None:
                return True

        return False

    # WARN this only runs nnUNet for now, since samED isn't working yet
    def run_segmentation(self, path: Path) -> Path | None:
        """Creates a segmentation map using the inference engine."""
        # Build hash for this file
        hashed_file = build_hash(path)

        # Has this file been segmented before? if it has, don't bother, otherwise...
        if not self.segmentation_present(hashed_file):

            CONDA = get_micromamba_dir()
            ENV = get_env_name()

            model_folder = Path(__file__).resolve().parents[0].joinpath("models")
            predictions_folder = Path(__file__).resolve().parents[0].joinpath("predictions")
            if not predictions_folder.exists():
                predictions_folder.mkdir()

            # create a symlink to the file with the nnUNet naming convention.
            # This doesn't move the original file and makes no copies.

            symlink_name = build_nnunet_name(path, hashed_file)
            tmp_dir = Path(".tmp").resolve()
            tmp_dir.mkdir(exist_ok=True)
            symlink_path = tmp_dir.joinpath(symlink_name)
            symlink_path.symlink_to(path.resolve())

            if path.name.endswith('.nii.gz'):
                base = path.name[:-7]
                final_file = predictions_folder / f"{base}_{hashed_file}.nii.gz"
            else:
                final_file = predictions_folder / f"{path.stem}_{hashed_file}{path.suffix}"

            # TODO this needs to be moved to an async thread, inference can freeze or kill the app

            status = subprocess.call([
                CONDA,
                "run",
                "-n",
                ENV,
                "nnUNetv2_predict_from_modelfolder",
                "-i",
                tmp_dir,
                "-o",
                predictions_folder,
                "-m",
                model_folder,
                "-f",
                "4",
                "-device",
                "cpu",  # TODO wire this to the settings
            ])

            print(f"inference finished with exit status {status}")

            if status == 0:
                self.settings.update_sm_files(hashed_file, final_file)
            else:
                # TODO let the user know that inference failed
                pass

            for file in tmp_dir.glob("*"):
                file.unlink()
            tmp_dir.rmdir()

        return self.settings.get_sm_files().get(hashed_file)
