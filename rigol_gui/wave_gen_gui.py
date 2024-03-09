import os
import pickle
import traceback
from datetime import datetime

from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from collections import namedtuple
from typing import Union, Dict, List

from . import utils
from . import editor
from . import wave_gen


def wave_config_scroll_area():
    scroll_area = QScrollArea()
    scroll_area.horizontalScrollBar().hide()
    scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
    scroll_area.setWidgetResizable(True)
    return scroll_area


def setup_wave_config_layout(labels, widgets):
    lv0 = QVBoxLayout()
    for label in labels:
        label_widget = QLabel(label, None)
        label_widget.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lv0.addWidget(label_widget)
    
    lv1 = QVBoxLayout()
    for widget in widgets:
        lv1.addWidget(widget)
    
    lv1.sizeHint = lv0.sizeHint

    layout_params = QHBoxLayout()
    layout_params.addLayout(lv0)
    layout_params.addLayout(lv1)
    widget_params = QWidget()
    widget_params.setLayout(layout_params)
    scroll_area = wave_config_scroll_area()
    scroll_area.setWidget(widget_params)

    vl = QVBoxLayout()
    vl.addWidget(scroll_area)
    return vl


Param = namedtuple("Param", ["full_name", "short_name", "default_text", "convert_func"])
WaveInfo = namedtuple("WaveInfo", ["type", "params_val", "params_text", "data"])


class WaveWidgetBase(QWidget):
    previewClicked = pyqtSignal(WaveInfo)

    def __init__(self):
        super().__init__(parent=None)
        self.wave_info = None
        self.prev_save_dir = "./"
    
    def gen_wave(self) -> WaveInfo:
        raise NotImplementedError
    
    def from_wave(self, info: Union[WaveInfo, Dict]):
        raise NotImplementedError
    
    def _emit_wave(self):
        try:
            wave_info = self.gen_wave()
            self.previewClicked.emit(wave_info)
            self.wave_info = wave_info
        except Exception as e:
            self.wave_info = None
            print(traceback.format_exc())
            msg = repr(e) + "\n\n" + "See console for more detailed information."
            utils.showErrMsg(msg)
    
    def _save_wave(self):
        if self.wave_info is None:
            self._emit_wave()
        
        if self.wave_info is not None:
            timestamp = datetime.strftime(datetime.now(), "%Y.%m.%d-%H.%M.%S")
            wave_type = self.wave_info.type
            fname = timestamp + "-" + wave_type + ".pkl"
            prefer_path = os.path.join(self.prev_save_dir, fname)

            path = utils.saveFileDialog(prefer_dir=prefer_path)
            if path is not None:
                if not path.lower().endswith(".pkl"):
                    path += ".pkl"
                with open(path, "wb") as fp:
                    pickle.dump(self.wave_info._asdict(), fp)
                self.prev_save_dir = os.path.dirname(path)


class LineEditWaveWidgetBase(WaveWidgetBase):
    DEFAULT_PARAMS: List[Param] = []

    def __init__(self):
        super().__init__()

        labels = []
        widgets = []

        for param in self.DEFAULT_PARAMS:
            labels.append(param.short_name + ":")
            param_widget_name = param.full_name + "_edit"
            setattr(self, param_widget_name, QLineEdit(param.default_text))
            widgets.append(getattr(self, param_widget_name))

        self.preview_btn = QPushButton(text="Preview")
        self.save_btn = QPushButton(text="Save")

        self.preview_btn.clicked.connect(self._emit_wave)
        self.save_btn.clicked.connect(self._save_wave)

        hl = QHBoxLayout()
        hl.addWidget(self.preview_btn)
        hl.addWidget(self.save_btn)

        vl = setup_wave_config_layout(labels, widgets)
        vl.addLayout(hl)
        self.setLayout(vl)
    
    def get_params(self):
        params_val = {}
        params_text = {}
        for param in self.DEFAULT_PARAMS:
            param_widget_name = param.full_name + "_edit"
            text = getattr(self, param_widget_name).text()
            params_text[param.full_name] = text
            params_val[param.full_name] = param.convert_func(text)
        return params_val, params_text
    
    def from_wave(self, info: Union[WaveInfo, Dict]):
        if isinstance(info, dict):
            info = WaveInfo(**info)
        
        for param in self.DEFAULT_PARAMS:
            param_widget_name = param.full_name + "_edit"
            getattr(self, param_widget_name).setText(info.params_text[param.full_name])


class SquareWaveWidget(LineEditWaveWidgetBase):
    DEFAULT_PARAMS = [
        Param("total_time"  , "Tmax"    , "10"  , float),
        Param("upper"       , "upper"   , "1"   , float),
        Param("lower"       , "lower"   , "-1"  , float),
        Param("frequency"   , "freq"    , "1"   , float),
        Param("duty_cycle"  , "duty"    , "0.5" , float),
        Param("num_cycles"  , "cycle"   , "-1"  , int  ),
        Param("delay"       , "delay"   , "0"   , float),
        Param("rest_v"      , "rest"    , "0"   , float)
    ]

    def gen_wave(self):
        params_val, params_text = self.get_params()
        x, y = wave_gen.square(**params_val)

        return WaveInfo(
            type="square",
            params_val=params_val,
            params_text=params_text,
            data={"x": x, "y": y}
        )


class TriangleWaveWidget(LineEditWaveWidgetBase):
    DEFAULT_PARAMS = [
        Param("total_time"  , "Tmax"    , "10"  , float),
        Param("upper"       , "upper"   , "1"   , float),
        Param("lower"       , "lower"   , "-1"  , float),
        Param("frequency"   , "freq"    , "1"   , float),
        Param("phase"       , "phase"   , "0.25", float),
        Param("num_cycles"  , "cycle"   , "-1"  , int  ),
        Param("delay"       , "delay"   , "0"   , float),
        Param("rest_v"      , "rest"    , "0"   , float)
    ]

    def gen_wave(self):
        params_val, params_text = self.get_params()
        x, y = wave_gen.triangle(**params_val)

        return WaveInfo(
            type="triangle",
            params_val=params_val,
            params_text=params_text,
            data={"x": x, "y": y}
        )


class PulseWaveWidget(LineEditWaveWidgetBase):
    DEFAULT_PARAMS = [
        Param("total_time"  , "Tmax"    , "10" , float),
        Param("amps"        , "amps"    , "[1]*8 + [-0.5]*8", eval),
        Param("widths"      , "wids"    , "[0.1]*16", eval),
        Param("gaps"        , "gaps"    , "[0.4]*16", eval),
        Param("delay"       , "delay"   , "1" , float),
        Param("rest_v"      , "rest"    , "0" , float)
    ]

    def gen_wave(self):
        params_val, params_text = self.get_params()
        x, y = wave_gen.pulse(**params_val)

        return WaveInfo(
            type="pulse",
            params_val=params_val,
            params_text=params_text,
            data={"x": x, "y": y}
        )


script_wave_demo = (
"""# Example to generate custom wave:
# User need to define the value of `{0}`
# and implement function `{1}`.

import math

# {0} is total time, you can modify the value,
# but do not modify the variable name `{0}`
{0} = 10

# Function to calculate desired voltage at given
# timestep `t`, you can modify the implementation,
# but do not modify the function name `{1}`.
# Note: `t` varies from [0, {0})
def {1}(t):
    if t <= {0} * 0.1:
        y = 0.0
    elif t <= {0} * 0.9:
        y = math.sin(t)
    else:
        y = 1.0
    return y

""".format(
    wave_gen.User.TOTAL_TIME_NAME, 
    wave_gen.User.IMPL_FUNC_NAME
))


class ScriptWaveWidget(WaveWidgetBase):

    def __init__(self):
        super().__init__()

        self.user = wave_gen.User()
        self.editor = editor.PythonCodeEditor()
        self.editor.setPlainText(script_wave_demo)

        scroll_area = wave_config_scroll_area()
        scroll_area.setWidget(self.editor)

        self.preview_btn = QPushButton(text="Preview")
        self.save_btn = QPushButton(text="Save")
        self.load_btn = QPushButton(text="Load")

        self.preview_btn.clicked.connect(self._emit_wave)
        self.load_btn.clicked.connect(self._load_script)
        self.save_btn.clicked.connect(self._save_wave)

        hl = QHBoxLayout()
        hl.addWidget(self.preview_btn)
        hl.addWidget(self.save_btn)
        hl.addWidget(self.load_btn)
        vl = QVBoxLayout()
        vl.addWidget(scroll_area)
        vl.addLayout(hl)
        self.setLayout(vl)

        self.prev_script_dir = "./"
    
    def gen_wave(self):
        text = self.editor.toPlainText()
        self.user.update(text)
        x, y = self.user()

        return WaveInfo(
            type="script",
            params_val=None,
            params_text=text,
            data={"x": x, "y": y}
        )

    def from_wave(self, info: Union[WaveInfo, Dict]):
        if isinstance(info, dict):
            info = WaveInfo(**info)
        self.editor.setPlainText(info.params_text)
    
    def _load_script(self):
        path = utils.openFileDialog(prefer_dir=self.prev_script_dir)
        if path is not None:
            with open(path, "r") as fp:
                text = fp.read()
            self.editor.setPlainText(text)
            self.prev_script_dir = os.path.dirname(path)

