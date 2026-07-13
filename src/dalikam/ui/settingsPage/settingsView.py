from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QWidget, QVBoxLayout, QLabel, QHBoxLayout, QComboBox, QPushButton, QFileDialog

from dalikam.ui.settingsPage.settingsVM import SettingsVM, MODEL_TYPE_KEYS


class SettingsView(QWidget):
    def __init__(self, vm: SettingsVM):
        super().__init__()
        self._viewmodel: SettingsVM = vm

        self._viewmodel.results_ready.connect(self.draw_results_popup)
        self._viewmodel.model_loaded.connect(self._on_model_loaded)

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

        # add all model descriptions to dropdown
        self._model_type_names = list(MODEL_TYPE_KEYS.keys())
        self.model_dropdown = QComboBox()
        self.model_dropdown.addItems(self._model_type_names)

        saved_type = self._viewmodel.get_preferred_model_type()
        model_type_values = list(MODEL_TYPE_KEYS.values())
        if saved_type in model_type_values:
            self.model_dropdown.setCurrentIndex(model_type_values.index(saved_type))

        load_model = QPushButton("Load Model Weights")
        load_model.clicked.connect(self._on_load_model)
        verify_model = QPushButton("Verify Weights")
        verify_model.clicked.connect(self._on_verify_model)

        model_row.addStretch()
        model_row.addWidget(model_text)
        model_row.addWidget(self.model_dropdown)
        model_row.addStretch()
        model_row.addWidget(load_model)
        model_row.addStretch()
        model_row.addWidget(verify_model)
        model_row.addStretch()

        path_row = QHBoxLayout()

        path_text = QLabel("Path to model weighs: ")
        self.weight_path = QLabel("Not set")

        path_row.addStretch()
        path_row.addWidget(path_text)
        path_row.addWidget(self.weight_path)
        path_row.addStretch()

        self._update_path_label()
        self.model_dropdown.currentIndexChanged.connect(self._on_model_type_changed)

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
        hardware_dropdown.blockSignals(True)
        hardware_dropdown.setCurrentIndex(self._viewmodel.get_device_index())
        hardware_dropdown.blockSignals(False)
        hardware_dropdown.currentIndexChanged.connect(self._viewmodel.set_device)

        test_hardware = QPushButton("Test Hardware Availability")
        test_hardware.clicked.connect(self._viewmodel.check_inference_device)

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

        weights_button.clicked.connect(self._viewmodel.delete_weight_paths)
        sm_button.clicked.connect(self._viewmodel.delete_saved_segmentations)
        scan_button.clicked.connect(self._viewmodel.delete_scan_paths)

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

    def draw_results_popup(self, content: str):
        popup = QDialog(self)
        layout = QHBoxLayout()
        layout.addWidget(QLabel(content))
        popup.setLayout(layout)
        popup.exec()

    def _on_load_model(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Model Archive", "", "Zip Archives (*.zip)"
        )
        if path:
            from pathlib import Path
            model_type_key = MODEL_TYPE_KEYS[self.model_dropdown.currentText()]
            self._viewmodel.load_model(Path(path), model_type_key)

    def _on_model_loaded(self, message: str):
        self._update_path_label()
        self.draw_results_popup(message)

    def _update_path_label(self):
        model_type_key = MODEL_TYPE_KEYS[self.model_dropdown.currentText()]
        path = self._viewmodel.get_model_path(model_type_key)
        self.weight_path.setText(path if path else "Not set")

    def _on_model_type_changed(self, index: int):
        model_type_key = MODEL_TYPE_KEYS[self._model_type_names[index]]
        self._viewmodel.set_preferred_model_type(model_type_key)
        self._update_path_label()

    def _on_verify_model(self):
        model_type_key = MODEL_TYPE_KEYS[self.model_dropdown.currentText()]
        self._viewmodel.verify_model(model_type_key)