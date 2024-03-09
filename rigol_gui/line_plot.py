import numpy as np
import pyqtgraph as pg

from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *


class Data(object):
    def __init__(self, x, y):
        self.x = x
        self.y = y
    
    def num_curves(self):
        return 1
    
    def get_ith_curve(self, i):
        return self.x, self.y
    
    def get_y_at_x(self, x):
        return [self.y]



class LinePlot(pg.GraphicsLayout):
    mouseMoveTo = pyqtSignal(float)

    def __init__(self,
        data: Data,
    ):
        super().__init__(
            parent=None,
            border=None
        )

        self.curves = []
        self.colors = []

        self.vline = None
        self.plot = pg.PlotWidget()
        self.label = pg.LabelItem(justify="left")
        self.updating = False

        self.timer = QTimer(self)
        self.timer.setInterval(int(1. / 60. * 1000.))
        self.timer.timeout.connect(self.update)

        self.init(data)

        self.addItem(self.label, row=0, col=0)
        proxy = QGraphicsProxyWidget()
        proxy.setWidget(self.plot)
        self.addItem(proxy, row=1, col=0)

        self.plot.setMouseEnabled(x=True, y=False)
        self.plot.setDownsampling(mode="peak")
        self.plot.setClipToView(True)
        self.plot.scene().sigMouseMoved.connect(self.mouseMoveInSceneEvent)
        
        # self.destroyed.connect(lambda: print("LinePlot destroyed"))
    
    def init(self, data: Data):
        self.stopUpdating()

        self.num_curves = data.num_curves()
        self.data = data

        # remove previous content
        for curve in self.curves:
            self.plot.removeItem(curve)
        self.curves.clear()
        self.colors.clear()
        self.tryRemoveVLine()

        # add new content
        for i in range(self.num_curves):
            self.colors.append(pg.mkColor((i, self.num_curves)))
        for i, c in enumerate(self.colors):
            curve = pg.PlotDataItem(
                name="Curve/{:0>2d}".format(i),
                pen=pg.mkPen(c, width=1)
            )
            self.plot.addItem(curve)
            self.curves.append(curve)

        self.fmt_str = self.generateFormatString()
        self.init_str = self.fmt_str.replace("{:.4f}", "///////////")\
                                    .replace("{:+.4e}", "///////////")
        self.label.setText(self.init_str)
    
    def getInitParams(self):
        return self.data, self.num_curves

    def generateFormatString(self):
        string = "<span style='font-size: 8pt'><b>Time = {:.4f}</b><br>"
        i = 0
        for i, c in enumerate(self.colors):
            assert isinstance(c, QColor)
            sep = "&nbsp;" if ((i+1) % 4) or (i == self.num_curves - 1) else "<br>"
            string += "<span style='color: rgba({}, {}, {}, {})'>"\
                      .format(c.red(), c.green(), c.blue(), c.alpha()) + \
                      "<b>Curve/{:0>2d}".format(i) + \
                      " = {:+.4e}" + "{}</b></span>".format(sep)
        # ex_params = [""]
        ex_params = []
        for j, param in enumerate(ex_params):
            sep = "&nbsp;" if ((i+j+1) % 4) or (i+j == self.num_curves - 1) else "<br>"
            string += "<span style='color: white'> <b> {}".format(param) + \
                " = {:+.4e}" + "{} </b></span>".format(sep)
        string += "</span>"
        return string
    
    def tryAddVLine(self):
        if self.vline is None:
            self.vline = pg.InfiniteLine(
                angle=90,
                movable=False,
                pen=pg.mkPen(QColor(255, 255, 255), width=1)
            )
            self.plot.addItem(self.vline, ignoreBounds=True)
    
    def tryRemoveVLine(self):
        if self.vline is not None:
            self.plot.removeItem(self.vline)
            self.vline = None
    
    def getLineViewBox(self):
        return self.plot.getViewBox()
    
    def startUpdating(self):
        if self.updating:
            return
        self.updating = True
        self.tryRemoveVLine()
        self.label.setText(self.init_str)
        self.plot.getViewBox().enableAutoRange(axis="xy", enable=True)
        # self.timer.start()

    def stopUpdating(self):
        if not self.updating:
            return
        # self.timer.stop()
        self.update()
        self.tryAddVLine()
        self.updating = False
    
    def emptyCurves(self):
        if self.updating:
            print("[INFO] Try empty curves while updating, failed")
            return
        self.tryRemoveVLine()
        self.label.setText(self.init_str)
        for c in self.curves:
            c.setData(x=None, y=None)

    def update(self):
        if self.num_curves == 0:
            return
        if self.data is None:
            for i in range(self.num_curves):
                curve: pg.PlotDataItem = self.curves[i]
                curve.setData(x=None, y=None)
            return
        
        kwds = {'antialias': False, 'connect': 'all', 'skipFiniteCheck': False}
        for i in range(self.num_curves):
            x, y = self.data.get_ith_curve(i)
            curve: pg.PlotDataItem = self.curves[i]
            curve.setData(x=x, y=y, **kwds)

    def mouseMoveInSceneEvent(self, pos: QPointF):
        if not self.plot.sceneBoundingRect().contains(pos):
            return
        pts: QPointF = self.plot.getViewBox().mapSceneToView(pos)
        self.mouseMoveTo.emit(float(pts.x()))

    def moveVLineTo(self, pos_x):
        if self.num_curves == 0:
            return
        if self.updating:
            return
        
        ys = []
        for i in range(self.data.num_curves()):
            ci: pg.PlotDataItem = self.curves[i]
            xi = ci.getData()[0]

            if xi is None:
                continue
            num_pts = xi.shape[0]
            if num_pts == 0:
                continue

            index = np.argmin(np.abs(pos_x - xi))
            x_sel = xi[index]
            y_sel = ci.getData()[1][index]
            ys.append(y_sel)
        
        self.tryAddVLine()
        self.vline.setPos(pos_x)
        values = [pos_x] + ys + self.calExtParams()
        self.label.setText(self.fmt_str.format(*values))

    def calExtParams(self):
        return []


class LinePlotWidget(pg.GraphicsLayoutWidget):
    def __init__(self, data: Data):
        super().__init__(parent=None, show=False, size=None, title=None)

        self.line_plot = LinePlot(data)
        self.addItem(self.line_plot)
        self.setFixedHeight(400)
        self.line_plot.mouseMoveTo.connect(self.line_plot.moveVLineTo)
    
    def set_xy(self, x, y):
        self.line_plot.data.x = x
        self.line_plot.data.y = y
    
    def refresh(self):
        self.line_plot.startUpdating()
        self.line_plot.stopUpdating()

