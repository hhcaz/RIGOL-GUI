
from PyQt5 import QtGui, QtWidgets


class WrapDelegate(QtWidgets.QStyledItemDelegate):

    referenceWidth = 0
    wrapMode = QtGui.QTextOption.WrapAtWordBoundaryOrAnywhere

    def sizeHint(self, opt, index):
        doc = QtGui.QTextDocument(index.data())
        textOption = QtGui.QTextOption()
        textOption.setWrapMode(self.wrapMode)
        doc.setDefaultTextOption(textOption)
        doc.setTextWidth(self.referenceWidth)
        return doc.size().toSize()

    def paint(self, qp, opt, index):
        self.initStyleOption(opt, index)
        style = opt.widget.style()
        opt.text = ''
        style.drawControl(style.CE_ItemViewItem, opt, qp, opt.widget)
        doc = QtGui.QTextDocument(index.data())
        textOption = QtGui.QTextOption()
        textOption.setWrapMode(textOption.WrapAtWordBoundaryOrAnywhere)
        doc.setDefaultTextOption(textOption)
        doc.setTextWidth(opt.rect.width())
        qp.save()
        qp.translate(opt.rect.topLeft())
        qp.setClipRect(0, 0, opt.rect.width(), opt.rect.height())
        doc.drawContents(qp)
        qp.restore()


class ComboWrap(QtWidgets.QComboBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.delegate = WrapDelegate(self.view())
        self.view().setItemDelegate(self.delegate)
        self.view().setResizeMode(QtWidgets.QListView.Adjust)

    def showPopup(self):
        container = self.view().parent()
        l, _, r, _ = container.layout().getContentsMargins()
        margin = l + r + container.frameWidth() * 2
        if self.model().rowCount() > self.maxVisibleItems():
            margin += self.view().verticalScrollBar().sizeHint().width()
        self.delegate.referenceWidth = self.width() - margin
        super().showPopup()


if __name__ == "__main__":
    from random import choice

    letters = 'abcdefhgijklmnopqrstuvwxyz0123456789' * 2 + ' '
    app = QtWidgets.QApplication([])
    combo = ComboWrap()
    combo.addItems([''.join(choice(letters) for i in range(100)) for i in range(20)])
    combo.show()
    app.exec()
