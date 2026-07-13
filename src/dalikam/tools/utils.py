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

def get_device_map() -> dict[int, str]:
    return {
        0: "cpu",
        1: "cuda",
        2: "mps"
    }

def hsv_to_rgb(h: float, s: float, v: float) -> tuple[float, float, float]:
    """Convert HSV to RGB. All values are in the range 0 - 1."""
    i = int(h * 6)
    f = h * 6 - i
    p = v * (1 - s)
    q = v * (1 - f * s)
    t = v * (1 - (1 - f) * s)
    i %= 6
    if i == 0:
        return v, t, p
    if i == 1:
        return q, v, p
    if i == 2:
        return p, v, t
    if i == 3:
        return p, q, v
    if i == 4:
        return t, p, v
    return v, p, q

def label_to_spread_color(label: int, label_n: int) -> tuple[float,float,float]:
        """
            Assign a color to a label, given the label index and how many labels there are.
            The colors are spread programmatically over the color wheel using hsv, which is
            then converted back to rgb for ease of use.
        """
        hue = (label - 1) / max(label_n - 1, 1)
        r, g, b = hsv_to_rgb(hue, 0.8, 0.9)

        return r,g,b

def generate_label_colors(labels_int: list[int]) -> dict[int, tuple[float, float, float]]:
    """
        Create a color map from the labels to the colors, to identify which label has which color.
    """
    result: dict[int, tuple[float, float, float]] = {}
    n_total = len(labels_int) + 1 # consider missing background label
    
    for num in labels_int:
        spread_color = label_to_spread_color(num, n_total)
        print(f"associating to label {num} color {spread_color}")
        result.update({num: spread_color})

    return result
