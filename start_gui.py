import sys
import pyvisa_py
from PyQt5.QtWidgets import QApplication
from rigol_gui.rigol_gui import MainWindow


app = QApplication(sys.argv)
main_win = MainWindow()
main_win.show()
app.exec()

