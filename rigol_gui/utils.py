import os
import sys
import errno
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from typing import Iterable, Union


def getIcon(
    name,
    target_wh: Union[Iterable, int, None]=None,
    mask_color: Union[str, None]=None,
    target_color: Union[str, None]=None
):
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, "icons", name)

    if target_wh is not None:
        if isinstance(target_wh, int):
            target_wh = [target_wh, target_wh]

    if path.endswith(("svg", "SVG")):
        pixmap = QIcon(path).pixmap(QSize(32, 32)) if target_wh is None \
            else QIcon(path).pixmap(QSize(target_wh[0], target_wh[1]))
        
    else:
        pixmap = QPixmap(path)
        if target_wh is not None:
            pixmap.scaled(target_wh[0], target_wh[1], Qt.KeepAspectRatio)

    if (mask_color is not None) and (target_color is not None):
        mask = pixmap.createMaskFromColor(QColor(mask_color), Qt.MaskOutColor)
        pixmap.fill(QColor(target_color))
        pixmap.setMask(mask)
    
    return QIcon(pixmap)


def openDirDialog(prefer_dir="./"):
    if not os.path.exists(prefer_dir):
        os.makedirs(prefer_dir)
    
    path = QFileDialog.getExistingDirectory(
        None,
        "Open Directory",
        prefer_dir,
        QFileDialog.ShowDirsOnly
    )
    if len(path) == 0:
        path = None
    print("[INFO] [from app] Choose dir = {}".format(path))
    return path


def openFileDialog(filter=None, prefer_dir="./"):
    if filter is None:
        filter = "Any File (*)"
    
    if not os.path.exists(prefer_dir):
        os.makedirs(prefer_dir)

    path = QFileDialog.getOpenFileName(
        None,
        "Open File",
        prefer_dir,
        filter=filter
    )[0]

    if path == "":
        path = None

    return path


def saveFileDialog(filter=None, prefer_dir="./"):
    if filter is None:
        filter = "Any File (*)"
    
    # if not os.path.exists(prefer_dir):
    #     os.makedirs(prefer_dir)
    
    path = QFileDialog.getSaveFileName(
        None,
        "Save File",
        prefer_dir,
        filter=filter
    )[0]

    if path == "":
        path = None
    
    return path


def showErrMsg(msg):
    err_msg = QMessageBox(None)
    err_msg.setIcon(QMessageBox.Critical)
    err_msg.setWindowTitle("Error")
    err_msg.setDetailedText("")
    err_msg.setText(msg)
    err_msg.exec()


def is_pathname_valid(pathname: str) -> bool:
    ERROR_INVALID_NAME = 123
    try:
        if not isinstance(pathname, str) or not pathname:
            return False
        _, pathname = os.path.splitdrive(pathname)
        root_dirname = os.environ.get('HOMEDRIVE', 'C:') \
            if sys.platform == 'win32' else os.path.sep
        assert os.path.isdir(root_dirname)

        root_dirname = root_dirname.rstrip(os.path.sep) + os.path.sep
        for pathname_part in pathname.split(os.path.sep):
            try:
                os.lstat(root_dirname + pathname_part)
            except OSError as exc:
                if hasattr(exc, 'winerror'):
                    if exc.winerror == ERROR_INVALID_NAME:
                        return False
                elif exc.errno in {errno.ENAMETOOLONG, errno.ERANGE}:
                    return False
    except TypeError as exc:
        return False
    else:
        return True

