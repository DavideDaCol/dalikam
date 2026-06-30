import os
import subprocess
from pathlib import Path

from dalikam.tools.micromamba import download_micromamba

ENV_NAME = "dalikam_oct"
DEPTH = 3


def main():
    # get the path to the project root, the micromamba binary and the segmentation backend
    ROOT = Path(__file__).resolve().parents[DEPTH]
    MICROMAMBA_DIR = ROOT / "bin" / "micromamba"
    print(f"the project's root path is: {ROOT}")
    SEG_DIR = ROOT / "src" / "dalikam" / "backend" / "OCT_segmentation"
    print(f"the segmentation backend is: {SEG_DIR}")

    # check if micromamba has been downloaded
    if not os.path.exists(MICROMAMBA_DIR):
        download_micromamba(ROOT)

    # check if the download went well
    if os.path.exists(MICROMAMBA_DIR):

        # list all currently present conda environments
        result = subprocess.run(
            [MICROMAMBA_DIR, "env", "list"],
            check=True,
            encoding="utf-8",
            stdout=subprocess.PIPE
        )
        output = result.stdout
        print(f"list of current environments: {output}")

        # if the environment is already present, remove it
        if output.find(ENV_NAME) != -1:
            print(f"the micromamba environment '{ENV_NAME}' is already present, clearing...")
            _ = subprocess.run([MICROMAMBA_DIR, "env", "remove", "-n", ENV_NAME, "-y"], check=True)

        # create the conda environment
        _ = subprocess.run([MICROMAMBA_DIR, "env", "create", "-n", ENV_NAME, "python=3.10", "-y"], check=True)

        # download the requirements
        _ = subprocess.run([
            MICROMAMBA_DIR,
            "run",
            "-n",
            ENV_NAME,
            "pip",
            "install",
            "-r",
            str(SEG_DIR / "requirement.txt")
        ], check=True)

        _ = subprocess.run([
            MICROMAMBA_DIR,
            "run",
            "-n",
            ENV_NAME,
            "python",
            str(SEG_DIR / "setup.py"),
            "install",
        ], check=True)

    else:
        print("the download of micromamba has failed, exiting...")
        raise FileNotFoundError


if __name__ == "__main__":
    main()
