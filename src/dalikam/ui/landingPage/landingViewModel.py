from dalikam.ui.landingPage.landingModel import landingModel
from PyQt6.QtCore import QObject, pyqtSignal

class landingVM(QObject):
    settingsAvailable = pyqtSignal(dict)

    def __init__(self, model):
        super().__init__()
        self._model = model
        print("landing page view model was initalized")

    def debugBtnPress(self, name: str):
        settings: dict = self._model.get_settings()
        print(f"settings: {settings}")
        self.settingsAvailable.emit(settings)