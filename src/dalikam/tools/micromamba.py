import os
import platform
import tarfile
from pathlib import Path

import requests
import tqdm

LINUX_X86_URL = "https://micro.mamba.pm/api/micromamba/linux-64/latest"
LINUX_ARM_URL = "https://micro.mamba.pm/api/micromamba/linux-aarch64/latest"
MACOS_URL = "https://micro.mamba.pm/api/micromamba/osx-arm64/latest"  # Apple Silicon only
# TODO test Windows url, extraction might be different
WINDOWS_X86_URL = "https://micro.mamba.pm/api/micromamba/win-64/latest"


def download_micromamba(root: Path) -> None:
    bin_path = root.joinpath("bin")
    # if the bin folder exists already, delete it
    if os.path.exists(bin_path):
        for filename in os.listdir(bin_path):
            print(f"removing previous installation of micromamba")
            file_path = os.path.join(bin_path, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)

    selected_url = ""

    if platform.system() == "Windows":
        print("Current platform: Windows (x86-64)")
        selected_url = WINDOWS_X86_URL
    elif platform.system() == "Darwin":
        print("Current platform: MacOS (ARM64)")
        selected_url = MACOS_URL
    elif platform.system() == "Linux":
        if platform.architecture()[0] == "64bit":
            print("Current platform: Linux (x86-64)")
            selected_url = LINUX_X86_URL
        else:
            print("Current platform: Linux (ARM64)")
            selected_url = LINUX_ARM_URL
    else:
        print("Micromamba is not supported for your platform.")
        raise NotImplementedError

    # make web request to micromamba servers, download file as stream
    headers = {"User-Agent": "Mozilla/5.0"}
    with requests.get(selected_url, headers=headers, stream=True) as r:
        r.raise_for_status()
        r.raw.decode_content = True
        total_size = int(r.headers.get("Content-Length", 0))  # for the progress bar

        # progress bar over the download progress
        with tqdm.tqdm.wrapattr(
                r.raw, "read", total=total_size, desc="Downloading micromamba",
                unit="B", unit_scale=True, unit_divisor=1024,
        ) as wrapped_raw:
            with tarfile.open(fileobj=wrapped_raw, mode="r|bz2") as tar:
                # extract only the micromamba binary
                for member in tar:
                    if member.name == "bin/micromamba":
                        tar.extract(member, path=root)
                        break
    print("Successfully extracted micromamba")
