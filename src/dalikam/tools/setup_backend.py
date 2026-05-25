from pathlib import Path
import shutil
import subprocess

ENV_NAME = "dalikam_oct"
DEPTH = 3

def main():
    # get the path to the project root and to the segmentation backend
    ROOT = Path(__file__).resolve().parents[DEPTH]
    print(f"the project's root path is: {ROOT}")
    SEG_DIR = ROOT / "src" / "dalikam" / "backend" / "OCT_segmentation"
    print(f"the segmentation backend is: {SEG_DIR}")

    # check if micromamba is in the user's path
    requirements = shutil.which("micromamba")

    if not requirements:
        print("part of the requirements are not satisfied: missing micromamba.")
        exit(-1)
    else :
        print("environment requirements are satisfied")

    # list all currently present conda environments
    result = subprocess.run(
        ["micromamba", "env", "list"],
        check=True, 
        encoding="utf-8", 
        stdout=subprocess.PIPE
    )
    output = result.stdout
    print(f"list of current environments: {output}")

    # if the environment is already present, remove it
    if output.find(ENV_NAME) != -1:
        print(f"the micromamba environment '{ENV_NAME}' is already present, clearing...")
        _ = subprocess.run(["micromamba", "env", "remove", "-n", ENV_NAME, "-y"], check=True)

    # create the conda environment
    _ = subprocess.run(["micromamba", "env", "create", "-n", ENV_NAME, "python=3.10", "-y"], check=True)

    # download the requirements
    _ = subprocess.run([
        "micromamba", 
        "run", 
        "-n", 
        ENV_NAME,
        "pip",
        "install",
        "-r",
        str(SEG_DIR / "requirement.txt")
    ],check=True)

    _ = subprocess.run([
        "micromamba", 
        "run", 
        "-n", 
        ENV_NAME,
        "python",
        str(SEG_DIR / "setup.py"),
        "install",
    ],check=True)

if __name__ == "__main__":
    main()