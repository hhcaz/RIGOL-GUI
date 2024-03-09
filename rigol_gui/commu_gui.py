
import pyvisa as visa
from typing import Union

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

from . import utils
from . import commu
from . import wave_gen_gui
from . import sharing_vars
from .mline_cb import ComboWrap


class DeviceQComboBox(ComboWrap):
    def __init__(self):
        super().__init__(parent=None)
        
        self.rm = visa.ResourceManager()
        self.device: Union[commu.DeviceManager, None] = None
        self.activated[str].connect(self._try_open_device)

    def detectDevice(self):
        rc = self.rm.list_resources()
        rc = list(rc) + ["Dummy Rigol Device"]
        self.clear()
        self.addItems(rc)
        self.setCurrentIndex(-1)
        self.showPopup()
    
    def _check_is_rigol(self, name: str):
        candidates = ["::dg4", "::dg5", "rigol"]
        name = name.lower().strip()
        is_rigol = False

        for candi in candidates:
            if candi in name:
                is_rigol = True
                break
        return is_rigol

    def _try_open_device(self):
        if self.count() > 0:
            device_name = self.currentText()
            if not self._check_is_rigol(device_name):
                self.setCurrentIndex(-1)
                self.device = None
                msg = "`{}` seems not to be a rigol device".format(device_name)
                utils.showErrMsg(msg)
            else:
                if "dummy" in device_name.lower():
                    self.device = commu.DeviceManager.dummy()
                else:
                    if self.device is not None:
                        self.device.inst.close()
                    inst = self.rm.open_resource(device_name, timeout=1)
                    self.device = commu.DeviceManager(inst)
        else:
            self.device = None
        
        sharing_vars.opened_device = self.device


class DeviceSelect(QHBoxLayout):
    def __init__(self):
        super().__init__()
        self.device_cb = DeviceQComboBox()

        detect_action = QAction()
        detect_action.setIcon(
            utils.getIcon(
                name="search_black_24dp.svg",
                target_wh=self.device_cb.sizeHint().height(),
                mask_color="black",
                target_color="#252324"
            )
        )
        detect_action.triggered.connect(self.device_cb.detectDevice)
        detect_btn = QToolButton()
        detect_btn.setDefaultAction(detect_action)
        detect_btn.setToolButtonStyle(Qt.ToolButtonIconOnly)

        self.addWidget(self.device_cb)
        self.addWidget(detect_btn)


class DownloadButton(QPushButton):
    def __init__(self, ch=1):
        super().__init__(parent=None)

        self.ch = ch
        self.setIcon(
            utils.getIcon(
                name="file_download_black_24dp.svg",
                target_wh=(64, 64),
                mask_color="black",
                target_color="#42a5f5"
            )
        )
        self.setText("CH{}".format(ch))
        self.clicked.connect(self._download)
    
    def _download(self):
        device: commu.DeviceManager = sharing_vars.opened_device
        if device is None:
            msg = "No device open, select device first."
            utils.showErrMsg(msg)
            return
        
        wave: wave_gen_gui.WaveInfo = sharing_vars.displayed_wave
        if wave is None:
            msg = "No wave preview, generate wave first."
            utils.showErrMsg(msg)
            return

        x = wave.data["x"]
        y = wave.data["y"]
        device[self.ch].data = (x[-1], y)


class ApplyButton(QPushButton):

    ON = 1
    OFF = 0

    def __init__(self, ch=1):
        super().__init__(parent=None)

        self.ch = ch
        self.play_icon = utils.getIcon(
            name="play_arrow_black_24dp.svg",
            mask_color="black",
            target_color="#009688",
            target_wh=(64, 64)
        )

        self.stop_icon = utils.getIcon(
            name="stop_black_24dp.svg",
            mask_color="black",
            target_color="red",
            target_wh=(64, 64)
        )

        self.state = self.OFF
        self.setIcon(self.play_icon)
        self.setText("CH{}".format(ch))
        self.clicked.connect(self._switch_state)
    
    def minimumSizeHint(self):
        # return QSize(125, 125)
        return QSize(125, 75)
    
    def on(self):
        if self.state == self.OFF:
            self._switch_state()
    
    def off(self):
        if self.state == self.ON:
            self._switch_state()
    
    def _switch_state(self):
        target_state = 1 - self.state
        success, msg = self._apply_state(target_state)
        # confirm state
        if success:
            if target_state == self.OFF:
                self.setIcon(self.play_icon)
            else:
                self.setIcon(self.stop_icon)
            self.state = target_state
        else:
            msg = (msg + " " + "Apply state failed.").strip()
            utils.showErrMsg(msg)
    
    def _apply_state(self, target_state):
        device: commu.DeviceManager = sharing_vars.opened_device
        if device is None:
            msg = "No device open, select device first."
            success = False
        else:
            msg = ""
            # apply state change
            device[self.ch].state = target_state
            # confirm state change
            success = device[self.ch].state == target_state
        return success, msg

