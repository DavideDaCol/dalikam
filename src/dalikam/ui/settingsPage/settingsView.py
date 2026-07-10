from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QComboBox, QPushButton

from dalikam.ui.settingsPage.settingsVM import SettingsVM


class SettingsView(QWidget):
    def __init__(self, vm: SettingsVM):
        super().__init__()
        self._viewmodel: SettingsVM = vm

        self.setObjectName("settingsPage")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        settings_layout = QVBoxLayout()

        title = QLabel("Settings")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        inference_section = QVBoxLayout()
        inference_title = QLabel("AI Inference")
        inference_title.setObjectName("smallTitle")

        model_row = QHBoxLayout()
        model_text = QLabel("Chosen model: ")

        model_dropdown = QComboBox()
        model_dropdown.addItems(["nnUNet (3D Low-Res)", "nnUNet (3D Full-Res)", "nnUNet (2D)"])

        load_model = QPushButton("Load Model Weights")
        verify_model = QPushButton("Verify Weights")

        model_row.addStretch()
        model_row.addWidget(model_text)
        model_row.addWidget(model_dropdown)
        model_row.addStretch()
        model_row.addWidget(load_model)
        model_row.addStretch()
        model_row.addWidget(verify_model)
        model_row.addStretch()

        path_row = QHBoxLayout()

        path_text = QLabel("Path to model weighs: ")
        weight_path = QLabel("Not set")

        path_row.addStretch()
        path_row.addWidget(path_text)
        path_row.addWidget(weight_path)
        path_row.addStretch()

        inference_section.addWidget(inference_title)
        inference_section.addStretch()
        inference_section.addLayout(model_row)
        inference_section.addStretch()
        inference_section.addLayout(path_row)

        hardware_section = QVBoxLayout()
        hardware_title = QLabel("Hardware")
        hardware_title.setObjectName("smallTitle")

        hardware_row = QHBoxLayout()
        hardware_text = QLabel("Inference device: ")

        hardware_dropdown = QComboBox()
        hardware_dropdown.addItems(["CPU (Not recommended)", "CUDA (NVIDIA Cards)", "MPS (Apple Silicon)"])

        test_hardware = QPushButton("Test Hardware Availability")

        hardware_row.addStretch()
        hardware_row.addWidget(hardware_text)
        hardware_row.addWidget(hardware_dropdown)
        hardware_row.addStretch()
        hardware_row.addWidget(test_hardware)
        hardware_row.addStretch()

        hardware_section.addWidget(hardware_title)
        hardware_section.addLayout(hardware_row)

        privacy_section = QVBoxLayout()
        privacy_title = QLabel("Privacy")
        privacy_title.setObjectName("smallTitle")

        privacy_row = QHBoxLayout()
        weights_button = QPushButton("Delete Weight Paths")
        sm_button = QPushButton("Delete Saved Segmentations")
        scan_button = QPushButton("Delete Scan Paths")

        privacy_row.addStretch()
        privacy_row.addWidget(weights_button)
        privacy_row.addStretch()
        privacy_row.addWidget(sm_button)
        privacy_row.addStretch()
        privacy_row.addWidget(scan_button)
        privacy_row.addStretch()

        privacy_section.addWidget(privacy_title)
        privacy_section.addLayout(privacy_row)

        settings_layout.addWidget(title)
        settings_layout.addLayout(inference_section)
        settings_layout.addStretch()
        settings_layout.addLayout(hardware_section)
        settings_layout.addStretch()
        settings_layout.addLayout(privacy_section)
        settings_layout.addStretch()

        self.setLayout(settings_layout)