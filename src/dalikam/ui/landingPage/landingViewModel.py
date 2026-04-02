from dalikam.router.router import Router
from dalikam.ui.landingPage.landingModel import LandingModel
from PyQt6.QtCore import QObject, pyqtSignal

class landingVM(QObject):
    settingsAvailable:pyqtSignal = pyqtSignal(dict)

    def __init__(self, model: LandingModel, navigator: Router):
        super().__init__()
        self._model: LandingModel = model
        self._navigator: Router = navigator
        print("landing page view model was initalized")

    def debug_btn_press(self):
        settings: dict[str,str] = self._model.get_settings()
        print(f"settings: {settings}")
        self.settingsAvailable.emit(settings)

    def start_clicked(self):
        print("start button has been clicked")
        self._navigator.navigate("file")