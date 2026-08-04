# Dalikam

Desktop application for the segmentation, visualization and analysis of retinal OCT images.

## Overview

Dalikam's main function is to visualize and segment (thanks to Simone Roman's [OCT Segmentation project](https://github.com/Roman-Simone/OCT_segmentation)) retinal OCT images in two and three dimensions. It is aimed towards optometrist and other healthcare personnel.

Dalikam can visualize the NIfTI files in 4 modes: Axial cut, Coronal cut, Saggital view and 3D view.

The OCT images can be segmented with two different models:
- nnUNet v2, a segmentation model with automatic configuration
- SamED-OCT, a purpose built segmentation model based on the [Segment-Anything-Model](https://github.com/facebookresearch/segment-anything)

Dalikam is part of a thesis project regarding the development of desktop applications using the MVVM architectural design pattern.

## Features

- Load NIfTI retinal OCT scans
- Run AI-based segmentation inference
- Visualize a scan and its segmentation in 2D and/or 3D
- Slice volumes to analyze the results
- Export the processed results
- Customization: label visualization, model type, transparency controls

## Screenshots

### Main Interface

[TBD]

### Visualization View

[TBD]

### Segmentation Output

[TBD]

---

## System Requirements

### Supported Operating Systems

- Windows 11
- Linux (Arch, Ubuntu, Debian, Fedora)
- MacOS 13+

### Hardware Requirements

- A GPU with support for CUDA (RTX 3060 or newer) or a CPU with MPS support (Apple Silicon) is recommended for inference. The application will fall back to CPU inference if needed but longer loading times are to be expected.

### Software Requirements

- Python 3.14
- UV package manager (install [here](https://docs.astral.sh/uv/getting-started/installation/))
- (optional, for AI inference): CUDA 12 or newer. Pytorch should include its own CUDA runtime.

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/DavideDaCol/dalikam.git
cd dalikam
```

### 2. Install project dependencies
```bash
git submodule update --init --recursive
uv sync
```

### 3. Install AI inference dependencies
```bash
uv run setup
```


### 4. Run the Application
```bash
uv run start-app
```

## Usage
### Typical Workflow
- Launch the application
- Load a NIfTI scan
- Visualize the scan in 2D
- Press 3D view to view the OCT in 3D
- Run segmentation inference
- Inspect results
- Export output

Both NIfTI 1 and NIfTI 2 files are supported.

### Running Segmentation

- The app is distributed under a "Bring your own Weights" philosophy. Please look [here](https://example.com) for details;
- Once you have obtained the model weights, which should be packaged as a .zip archive, open Dalikam and open the settings
- Still in the settings menu, choose your preferred inference model using the appropriate dropdown (3D low-res / 3d full-res / 2d) and press the load weights button;
- Segmentation inference will then be available inside of the application after opening a file.

### Exporting Results

The segmented images can be exported as a new NIfTI file. Simply create the segmentation map and press on the "Export Segmentation" button; a file dialog will ask where to save the NIfTI file containing the newly generated segmentation

## Project Structure

```bash
.
├── assets
└── src
    └── dalikam
        ├── backend
        ├── rendering
        ├── router
        ├── tools
        ├── ui
        │   ├── components
        │   ├── filePage
        │   ├── landingPage
        │   ├── settingsPage
        │   └── viewerPage
        ├── style.qss
        └── main.py
```

## Architecture Overview

- UI layer: MVVM (Model, view, view-model)
- Visualization pipeline: VTK (Visualization ToolKit)
- AI inference: Qt QProcess for asynchronous computation + separate conda environment

![Architecture diagram](https://i.ibb.co/PvHZhgBs/Screenshot-2026-07-26-180325.png)

## Dataset and Model Information
### Dataset

The models were trained using the [RETOUCH Dataset](https://retouch.grand-challenge.org/).
The dataset is not publicly accessible, please refer to your academic institution to request access.

### Models

Details on the segmentation models used by Dalikam can be found [here](https://github.com/Roman-Simone/OCT_segmentation).

The trained models will segment the image looking for the presence of some or all of the following fluids: Intra-Retinal Fluid (IRF), Sub-Retinal Fluid (SRF), Pigment Epithelial Detachment (PED). The specific labels that will be produced can be found in the `dataset.json` file bundled with the model weights.

## Limitations
- The project is currently still being built, many features are missing and breaking changes are to be expected.
- The application has not been validated for usage on MacOS and no official testing pipeline has been set up yet.
- Currently, only the nnUNet inference engine is correctly integrated, because SamED has had some platform-dependent issues.
- Cloud-based inference is not supported for privacy concerns: a GPU is required for inference.

## Future Improvements / TODOs
- style the file selector
- add custom color selection for the labels
- official testing pipeline
- full release pipeline

## References
[TBD]

## License

The project uses the MIT Software License.

## Author

Davide Da Col

Bachelor's Thesis in Computer Science

Università degli Studi di Trento

2026