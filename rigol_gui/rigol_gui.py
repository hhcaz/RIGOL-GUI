import os
import pickle
import numpy as np
import webbrowser

from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

from . import utils
from . import line_plot
from . import commu_gui
from . import wave_gen_gui
from . import sharing_vars


class InfoButton(QPushButton):
    URL = "https://github.com/hhcaz/rigol-gui"

    def __init__(self):
        super().__init__(parent=None)
        self.setText("Launch Web Browser")
        self.clicked.connect(self.try_open_browser)
        self.clipboard = QApplication.clipboard()
    
    def try_open_browser(self):
        success = webbrowser.open(self.URL)
        if not success:
            self.clipboard.setText(self.URL)
            print("[INFO] Failed to open web browser, "
                  "copy link to clipboard instead")


class ControlPannel(QWidget):
    def __init__(self):
        super().__init__(parent=None)

        self.device_sel = commu_gui.DeviceSelect()
        self.down_ch1_btn = commu_gui.DownloadButton(1)
        self.down_ch2_btn = commu_gui.DownloadButton(2)
        self.apply_ch1_btn = commu_gui.ApplyButton(1)
        self.apply_ch2_btn = commu_gui.ApplyButton(2)
        self.info_btn = InfoButton()

        vl = QVBoxLayout(self)
        box = QGroupBox(title="Select Device"); box.setLayout(self.device_sel)
        vl.addWidget(box)

        hl = QHBoxLayout(); hl.addWidget(self.down_ch1_btn); hl.addWidget(self.down_ch2_btn)
        box = QGroupBox(title="Download Wave"); box.setLayout(hl)
        vl.addWidget(box)

        hl = QHBoxLayout(); hl.addWidget(self.apply_ch1_btn); hl.addWidget(self.apply_ch2_btn)
        box = QGroupBox(title="Play Wave"); box.setLayout(hl)
        vl.addWidget(box)

        hl = QHBoxLayout(); hl.addWidget(self.info_btn)
        box = QGroupBox(title="How to Use"); box.setLayout(hl)
        vl.addWidget(box)


class ConfigPanel(QTabWidget):
    def __init__(self):
        super().__init__(parent=None)

        self.squ = wave_gen_gui.SquareWaveWidget()
        self.tri = wave_gen_gui.TriangleWaveWidget()
        self.pulse = wave_gen_gui.PulseWaveWidget()
        self.script = wave_gen_gui.ScriptWaveWidget()

        self.addTab(self.squ, "Squ")
        self.addTab(self.tri, "Tri")
        self.addTab(self.pulse, "Pulse")
        self.addTab(self.script, "Script")
        self.setCurrentWidget(self.pulse)
    
    def sub_tab_widgets(self):
        return [self.squ, self.tri, self.pulse, self.script]


class WorkingFolderDock(QDockWidget):
    fileDoubleClicked = pyqtSignal(wave_gen_gui.WaveInfo)

    def __init__(self):
        super().__init__(parent=None)

        self.setToolTip("Double click *.pkl file to load previous saved wave.")
        self.setObjectName("Working Folder")
        features = QDockWidget.DockWidgetFeatures()
        self.setFeatures(features | QDockWidget.DockWidgetFloatable | QDockWidget.DockWidgetMovable)
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.setVisible(True)

        self.prev_dir = os.path.abspath("./")
        self.dir_model = QFileSystemModel()
        self.dir_model.setRootPath(self.prev_dir)
        self.dir_model.setFilter(QDir.NoDotAndDotDot | QDir.AllDirs | QDir.Files)

        self.tree_view = QTreeView()
        self.tree_view.setModel(self.dir_model)
        self.tree_view.setRootIndex(self.dir_model.index(self.prev_dir))
        self.tree_view.doubleClicked.connect(self._emit_saved_wave)
        self.tree_view.setSortingEnabled(True)
        self.tree_view.sortByColumn(0, Qt.AscendingOrder)

        self.select_btn = QPushButton(text="Change Folder")
        self.select_btn.clicked.connect(self._select_working_dir)

        w = QWidget()
        vl = QVBoxLayout(w)
        vl.addWidget(self.tree_view)
        vl.addWidget(self.select_btn)
        self.setWidget(w)
        self._update_title()
    
    def _update_title(self):
        may_be_drive, folder = os.path.split(self.prev_dir)
        if len(folder) == 0:
            folder = may_be_drive
        self.setWindowTitle(folder)
    
    def _select_working_dir(self):
        path = utils.openDirDialog(prefer_dir=self.prev_dir)
        if path is not None:
            self.dir_model.setRootPath(path)
            self.tree_view.setRootIndex(self.dir_model.index(path))
            self.prev_dir = path
            self._update_title()
    
    def _emit_saved_wave(self, index):
        path = self.dir_model.fileInfo(index).absoluteFilePath()
        if os.path.isfile(path):
            if not path.lower().endswith(".pkl"):
                msg = "Only recognize files ending with `.pkl`."
                utils.showErrMsg(msg)
            else:
                with open(path, "rb") as fp:
                    info = pickle.load(fp)
                    info = wave_gen_gui.WaveInfo(**info)
                    self.fileDoubleClicked.emit(info)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__(parent=None)
        x = np.linspace(0, 1, 1000)
        y = np.zeros_like(x)
        self.line_plot = line_plot.LinePlotWidget(
            line_plot.Data(x=x, y=y)
        )
        self.line_plot.refresh()

        self.control_panel = ControlPannel()
        self.config_panel = ConfigPanel()
        hl = QHBoxLayout()
        hl.addWidget(self.control_panel)
        hl.addWidget(self.config_panel)

        # self.config_panel.sizeHint = self.control_panel.sizeHint
        self.config_panel.sizeHint = lambda: QSize(
            int(self.control_panel.sizeHint().width() * 1.2),
            self.control_panel.sizeHint().height()
        )

        vl = QVBoxLayout()
        vl.addWidget(self.line_plot)
        vl.addLayout(hl)

        center_widget = QWidget()
        center_widget.setLayout(vl)
        self.setCentralWidget(center_widget)

        self.dock = WorkingFolderDock()
        self.dock.fileDoubleClicked.connect(self._load_saved_wave)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.dock)
        # self.resizeDocks([self.dock], [1000], Qt.Horizontal)

        for wave_config_widget in self.config_panel.sub_tab_widgets():
            wave_config_widget.previewClicked.connect(self._load_preview_wave)
    
    def _load_preview_wave(self, wave_info: wave_gen_gui.WaveInfo):
        sharing_vars.displayed_wave = wave_info
        x = wave_info.data["x"]
        y = wave_info.data["y"]
        self.line_plot.set_xy(x, y)
        self.line_plot.refresh()
    
    def _load_saved_wave(self, wave_info: wave_gen_gui.WaveInfo):
        self._load_preview_wave(wave_info)
        wave_type = wave_info.type
        if wave_type == "square":
            self.config_panel.setCurrentWidget(self.config_panel.squ)
            self.config_panel.squ.from_wave(wave_info)
        elif wave_type == "triangle":
            self.config_panel.setCurrentWidget(self.config_panel.tri)
            self.config_panel.tri.from_wave(wave_info)
        elif wave_type == "pulse":
            self.config_panel.setCurrentWidget(self.config_panel.pulse)
            self.config_panel.pulse.from_wave(wave_info)
        elif wave_type == "script":
            self.config_panel.setCurrentWidget(self.config_panel.script)
            self.config_panel.script.from_wave(wave_info)
        else:
            msg = "Unknown wave type: {}".format(wave_type)
            utils.showErrMsg(msg)


if __name__ == "__main__":

    import sys

    app = QApplication(sys.argv)

    main_win = MainWindow()
    main_win.show()

    app.exec()
