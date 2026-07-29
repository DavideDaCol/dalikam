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

def label_to_spread_color(label_idx: int, total_count: int) -> tuple[float,float,float]:
        """
            Assign a color to a label, given its position in the label list and how many
            labels there are. The colors are spread programmatically over the color wheel
            using hsv, which is then converted back to rgb for ease of use.
        """
        hue = (label_idx - 1) / max(total_count - 1, 1)
        r, g, b = hsv_to_rgb(hue, 0.8, 0.9)

        return r,g,b

def generate_label_colors(label_values: list[int]) -> dict[int, tuple[float, float, float]]:
    """
        Create a color map from the label values to the colors, to identify which label has which color.
    """
    result: dict[int, tuple[float, float, float]] = {}
    n_total = len(label_values) + 1 # consider missing background label
    
    for idx, value in enumerate(label_values):
        spread_color = label_to_spread_color(idx + 1, n_total)
        result.update({value: spread_color})

    return result
