from typing import override

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QCloseEvent, QAction
from PyQt6.QtWidgets import QMainWindow, QStackedWidget, QToolBar

from dalikam.backend.segmentation import SegmentationManager
from dalikam.router.router import Router
from dalikam.ui.filePage.fileModel import FileInfo, FileSelectionModel
from dalikam.ui.filePage.fileVM import FileViewModel
from dalikam.ui.filePage.fileView import FileSelectionView
from dalikam.ui.landingPage.landingModel import LandingModel
from dalikam.ui.landingPage.landingVM import landingVM
from dalikam.ui.landingPage.landingView import LandingPage
from dalikam.ui.settingsPage.settingsModel import SettingsModel
from dalikam.ui.settingsPage.settingsVM import SettingsVM
from dalikam.ui.settingsPage.settingsView import SettingsView
from dalikam.ui.viewerPage.viewerModel import viewerModel
from dalikam.ui.viewerPage.viewerVM import ViewerVM
from dalikam.ui.viewerPage.viewerView import viewerView


class MenuBar(QToolBar):
    menu_route = pyqtSignal(int, object)

    def __init__(self, page_map: dict[str, int]):
        super().__init__()
        self.map = page_map
        self.setMovable(False)
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)

        for name, page in [("Start", "landing"),
                           ("File", "file"),
                           ("Settings", "settings")]:
            action = QAction(name, self)
            action.triggered.connect(lambda checked, p=page: self.change_page(self.map[p]))
            self.addAction(action)

    def change_page(self, incoming: int):
        print(f"got top bar navigation event, content: {incoming}")
        self.menu_route.emit(incoming, None)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dalikam")
        self.setGeometry(700, 300, 800, 600)

        # Initialize all models
        self._landingModel: LandingModel = LandingModel()
        self._fileModel: FileSelectionModel = FileSelectionModel()
        self._viewerModel: viewerModel = viewerModel()
        self._settingsModel: SettingsModel = SettingsModel()

        # Initialize app page router
        self._router: Router = Router()

        # Create the top level menu bar (hidden at startup)
        self._toolbar = MenuBar(self._router.get_registered_routes())
        self._toolbar.setVisible(False)

        # Initialize backend segmentation coordinator
        self._seg_manager: SegmentationManager = SegmentationManager()

        # Initialize all view models
        self.landingViewModel: landingVM = landingVM(self._landingModel, self._router)
        self.fileViewModel: FileViewModel = FileViewModel(self._fileModel, self._router)
        self.viewerViewModel: ViewerVM = ViewerVM(self._viewerModel, self._seg_manager, self._router)
        self.settingsViewModel: SettingsVM = SettingsVM(self._settingsModel)

        _ = self._router.routeChange.connect(self.change_page)
        _ = self._toolbar.menu_route.connect(self.change_page)

        # Initialize all views
        self.hero_section = LandingPage(self.landingViewModel)
        self.file_selection = FileSelectionView(self.fileViewModel)
        self.viewer_section = viewerView(self.viewerViewModel)
        self.settings_section = SettingsView(self.settingsViewModel)

        # Create the main container of the app
        self.main_container: QStackedWidget = QStackedWidget()
        _ = self.main_container.addWidget(self.hero_section)
        _ = self.main_container.addWidget(self.file_selection)
        _ = self.main_container.addWidget(self.viewer_section)
        _ = self.main_container.addWidget(self.settings_section)
        self.setCentralWidget(self.main_container)

        self.addToolBar(self._toolbar)

    @override
    def closeEvent(self, a0: QCloseEvent | None):
        if self.viewer_section is not None:
            self.viewer_section.cleanup_viewer()
        if a0 is not None:
            a0.accept()

    def change_page(self, index: int, context: FileInfo | None):
        """
        Connects the router component to the main page widget and changes the visualized
        widget whenever instructed. It relies on occasional context to send information
        to underlying widgets, such as paths or settings.

        Args
        ----------
        index: int
            the number corresponding to the order of the widget in the QStackWidget that acts as
            the main container
        context: FileInfo | None
            additional context used by the viewer section to determine which file was chosen
            in the file selection page
        """
        print(f"got page navigation event, switching to index {index}")
        self.main_container.setCurrentIndex(index)

        # Hide the toolbar if you're on the landing page
        self._toolbar.setVisible(index != self._router.page_names["landing"])

        # CASE: passing data from the file model to the viewer model
        if index == self._router.page_names["viewer"] and context:
            self.viewerViewModel.set_file(context)
