from pathlib import Path
import platform

DEPTH = 3
ENV_NAME = "dalikam_oct"


def get_root() -> Path:
    return Path(__file__).resolve().parents[DEPTH]


def get_env_name() -> str:
    return ENV_NAME


def get_micromamba_dir() -> Path:
    root = get_root()
    if platform.system() == "Windows":
        return root / "Library" / "bin" / "micromamba"
    else:
        return root / "bin" / "micromamba"
