# Dalikam

Desktop application for segmentation, visualization and analysis of retinal OCT images.

---

## Overview

Dalikam's main function is to visualize and segment (thanks to Simone Roman's [OCT Segmentation project](https://github.com/Roman-Simone/OCT_segmentation)) retinal OCT images in two and three dimensions. It is aimed towards optometrist and other healthcare personnel.

Dalikam can visualize the NIfTI files in 4 modes: Axial cut, Coronal cut, Saggital view and 3D view.

The OCT images can be segmented with two different models:
- nnUNet 2, a segmentation model with automatic configuration
- SamED-OCT, a purpose built segmentatio model based on the Segment-Anything-Model

Dalikam is part of a thesis project regarding the development of desktop applications using the MVVM design pattern.

## Features

- Load NIfTI retinal OCT scans
- Visualize segmentation layers in 2D and/or 3D
- Run AI-based segmentation inference
- Export the processed results
- Customization: label colors, visualizer color scheme, model of choice

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

- A GPU with support for CUDA, RTX 3060 or newer is recommended.

### Software Requirements

- Python 3.14
- UV package manager
- (optional, for AI inference): CUDA 12 or newer. Pytorch should include its own CUDA runtime 

---

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/DavideDaCol/dalikam.git
cd dalikam
```

### 2. Install project dependencies
```bash
uv sync
```

### 3. Install AI inference dependencies
[TBD]


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

Both NIfTI 1 and NIfTI 2 files are supported

### Running Segmentation

- The app is distributed under a "Bring your own Weights" philosophy. Please look [here](https://example.com) for details
- Once you have obtained the model weights, open Dalikam and open the settings. Click on the "load weights" button to move the model weights in the application environment.
- Still in the settings menu, choose your preferred inference model using the appropriate dropdown
- Segmentation inference will then be available inside of the application after opening a file

### Exporting Results

The segmented images can be exported as a new NIfTI file. The user can also export singular slices or 3D views as png images.

## Project Structure

.
├── assets
└── src
    └── dalikam
        ├── ui
        │   ├── filePage
        │   ├── landingPage
        │   └── viewerPage
        ├── style.qss
        └── main.py

## Architecture Overview

- UI layer: MVVM (Model, view, view-model)
- Visualization pipeline: VTK (Visualization ToolKit)
- AI inference: python subprocess

[TBD architecture diagram image]

## Dataset and Model Information
### Dataset

The models were trained using the [RETOUCH Dataset](https://retouch.grand-challenge.org/).
The dataset is not publicly accessible, please refer to your academic institution to request access.

### Models

Details on the segmentation models used by Dalikam can be found [here](https://github.com/Roman-Simone/OCT_segmentation).

## Limitations
- The project is currently still being built, many features are missing and breaking changes are to be expected.
- Initial development has only taken place on Linux and no official testing pipeline has been set up yet.
- Currently, only the nnUNet inference engine is working and is yet to be integrated.
- Web-based inference is not supported for privacy concerns: a GPU is required for inference.

## Future Improvements / TODOs
- integrate the inference engine
- style the segmentation viewer
- add settings page
- add custom color palette

## References
[TBD]

## License

The project uses the MIT Software License.

## Author

Davide Da Col

Bachelor Thesis in Computer Science

Università degli Studi di Trento

2026