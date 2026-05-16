from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLayout, QPushButton, QWidget, QVBoxLayout, QHBoxLayout, QLabel

from dalikam.ui.viewerPage.viewerVM import ViewerVM
from dalikam.rendering.visualizer import ThreeDview

import vtk


class SideMenu(QWidget):
    def __init__(self, labels: list[str] | None) -> None:
        super().__init__()
        self.menulayout: QVBoxLayout = QVBoxLayout()
        self.setLayout(self.menulayout)
        self.menulayout.addWidget(QLabel("this is where the label selector will be"))
        
        self.label_layout: QVBoxLayout = QVBoxLayout()
        self.menulayout.addLayout(self.label_layout)

        self.menulayout.addStretch()
        self.menulayout.addWidget(QPushButton("Axial View"))
        self.menulayout.addWidget(QPushButton("Coronal View"))
        self.menulayout.addWidget(QPushButton("Saggital View"))
        self.menulayout.addWidget(QPushButton("3D View"))

    def clear_layout(self, layout: QLayout):
        while layout.count():
            item = layout.takeAt(0)
            if item is not None:
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()

    def draw_labels(self, labels: list[str]):
        self.clear_layout(self.label_layout)
        for label in labels:
            self.label_layout.addWidget(QLabel(label))


class viewerView(QWidget):

    def __init__(self, vm: ViewerVM) -> None:
        super().__init__()
        self._viewmodel: ViewerVM = vm

        self.setObjectName("viewerPage")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        # layout to hold everything in place
        self.viewlayout: QHBoxLayout = QHBoxLayout()
        self.setLayout(self.viewlayout)

        # custom 3D viewer
        self.threed: ThreeDview = ThreeDview()
        self.side_menu: SideMenu = SideMenu(None)

        self.viewlayout.addWidget(self.side_menu, 1)
        self.viewlayout.addWidget(self.threed, 3)
        _ = self._viewmodel.draw_file.connect(self.plot_file)
        _ = self._viewmodel.labels_changed.connect(self.side_menu.draw_labels)

        self._viewmodel.testlabels()

    # Starts from the (loaded) raw data and displays it as the 3D model
    def plot_file(self, data: vtk.vtkNIFTIImageReader):
        print(f"drawing {data.descriptive_name}")
        self.threed.load_model(data)