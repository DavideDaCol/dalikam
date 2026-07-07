from PyQt6.QtWidgets import QMainWindow, QStackedWidget

from dalikam.backend.segmentation import SegmentationManager
from dalikam.router.router import Router
from dalikam.ui.filePage.fileModel import FileInfo, FileSelectionModel
from dalikam.ui.filePage.fileVM import FileViewModel
from dalikam.ui.filePage.fileView import FileSelectionView
from dalikam.ui.landingPage.landingModel import LandingModel
from dalikam.ui.landingPage.landingVM import landingVM
from dalikam.ui.landingPage.landingView import LandingPage
from dalikam.ui.viewerPage.viewerModel import viewerModel
from dalikam.ui.viewerPage.viewerVM import ViewerVM
from dalikam.ui.viewerPage.viewerView import viewerView


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dalikam")
        self.setGeometry(700, 300, 800, 600)

        # Initialize all models
        self._landingModel: LandingModel = LandingModel()
        self._fileModel: FileSelectionModel = FileSelectionModel()
        self._viewerModel: viewerModel = viewerModel()

        # Initialize app page router
        self._router: Router = Router()

        # Initialize backend segmentation coordinator
        self._seg_manager: SegmentationManager = SegmentationManager()

        # Initialize all view models
        self.landingViewModel: landingVM = landingVM(self._landingModel, self._router)
        self.fileViewModel: FileViewModel = FileViewModel(self._fileModel, self._router)
        self.viewerViewModel: ViewerVM = ViewerVM(self._viewerModel, self._seg_manager, self._router)

        _ = self._router.routeChange.connect(self.change_page)

        # Initialize all views
        hero_section = LandingPage(self.landingViewModel)
        file_selection = FileSelectionView(self.fileViewModel)
        viewer_section = viewerView(self.viewerViewModel)

        # Create the main container of the app
        self.main_container: QStackedWidget = QStackedWidget()
        _ = self.main_container.addWidget(hero_section)
        _ = self.main_container.addWidget(file_selection)
        _ = self.main_container.addWidget(viewer_section)
        self.setCentralWidget(self.main_container)

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

        # CASE: passing data from the file model to the viewer model
        if index == self._router.page_names["viewer"] and context:
            self.viewerViewModel.set_file(context)
