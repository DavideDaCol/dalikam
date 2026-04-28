from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from nibabel.filebasedimages import FileBasedImage

from dalikam.ui.viewerPage.viewerVM import ViewerVM

from pyvistaqt import QtInteractor
from  pyvista import BaseReader, DICOMReader

class viewerView(QWidget):

    def __init__(self, vm: ViewerVM) -> None:
        super().__init__()
        self._viewmodel: ViewerVM = vm
        self.viewlayout: QVBoxLayout = QVBoxLayout()
        self.draw_loader()
        _ = self._viewmodel.draw_file.connect(self.plot_file)

    def draw_loader(self):
        title = QLabel("Loading in progress...")
        title.setStyleSheet("color: #000000;")
        self.viewlayout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.viewlayout.addWidget(title)
        self.setLayout(self.viewlayout)

    def plot_file(self, data: BaseReader | DICOMReader):
        print(f"drawing {data.path}")

        for i in reversed(range(self.viewlayout.count())):
            item = self.viewlayout.takeAt(i)
            if item is not None:
                inner_widget = item.widget()
                if inner_widget is not None:
                    inner_widget.deleteLater()

        title = QLabel("this is what you get if the thing loads")
        plotter = QtInteractor()
        _ = plotter.add_volume(data.read(), opacity="linear")
        self.viewlayout.addWidget(title)
        self.viewlayout.addWidget(plotter)
