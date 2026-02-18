from qtpy.QtGui import QColor, QTextCursor, QTextCharFormat, QDrag
from qtpy.QtCore import Qt, QByteArray
from qtpy import QtWidgets
from qtpy.QtGui import QBrush, QPen, QCursor
from qtpy.QtSvg import QSvgRenderer
from qtpy.QtSvgWidgets import QGraphicsSvgItem
import nodeUtils
from nodeUtils import NodeMimeData
from nodeCommand import CommandSetNodeAttribute

RESIZE_SVG = QSvgRenderer("resources/resize.svg")


class TitleItem(QtWidgets.QGraphicsTextItem):
    def __init__(self, text, parent, attr, title=False):
        QtWidgets.QGraphicsTextItem.__init__(self, text, parent)
        self.setFocus(Qt.MouseFocusReason)
        self.parent = parent
        self.attr = attr
        self.setFont(nodeUtils.options.titleFont)
        if title:
            self.setDefaultTextColor(QColor(200, 200, 250))

            shadow = QtWidgets.QGraphicsDropShadowEffect(self)
            shadow.setOffset(2, 2)
            shadow.setBlurRadius(2)
            self.setGraphicsEffect(shadow)
            pen = QPen(QColor(10, 70, 120), 0.5)
            format = QTextCharFormat()
            format.setTextOutline(pen)
            cursor = QTextCursor(self.document())
            cursor.select(QTextCursor.Document)
            cursor.mergeCharFormat(format)
            # self.setFlags(QtWidgets.QGraphicsItem.ItemClipsToShape)

    def keyPressEvent(self, event):
        if event.key() != Qt.Key_Return:
            QtWidgets.QGraphicsTextItem.keyPressEvent(self, event)
        else:
            nodeUtils.options.undoStack.push(
                CommandSetNodeAttribute(
                    [self.parent], {self.attr: self.toPlainText()}
                )
            )
            self.setTextInteractionFlags(Qt.NoTextInteraction)

    def focusOutEvent(self, event):
        if Qt.TextEditorInteraction == self.textInteractionFlags():
            nodeUtils.options.undoStack.push(
                CommandSetNodeAttribute(
                    [self.parent], {self.attr: self.toPlainText()}
                )
            )
        self.setTextInteractionFlags(Qt.NoTextInteraction)
        self.textCursor().clearSelection()
        QtWidgets.QGraphicsTextItem.focusOutEvent(self, event)


class NodeInput(QtWidgets.QGraphicsRectItem):
    def __init__(self, parent, type=None):
        QtWidgets.QGraphicsRectItem.__init__(self, parent)
        self.parent = parent
        self.type = None
        self.setType(type)
        self.brush = QBrush(1)
        self.pen = QPen(Qt.black, 0.3)

    def setType(self, type):
        self.type = type
        if type and type in nodeUtils.options.typeColors.keys():
            self.brush.setColor(nodeUtils.options.typeColors[type])
        self.update()

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            event.ignore()
            return
        # nodeUtils.options.clearSelection()

        drag = QDrag(event.widget())
        mime = NodeMimeData()
        mime.setData("node/connect", QByteArray())
        mime.setObject(self.parentItem())
        drag.setMimeData(mime)
        # self.parent.connector = self
        cursor = QCursor(Qt.ArrowCursor)
        drag.setDragCursor(cursor.pixmap(), Qt.CopyAction)
        drag.exec(Qt.CopyAction)

    def paint(self, painter, option, widget=None):
        painter.setBrush(self.brush)
        painter.setPen(self.pen)
        painter.drawEllipse(self.boundingRect())


class NodeResize(QGraphicsSvgItem):
    def __init__(self, node, **kwargs):
        QGraphicsSvgItem.__init__(self, node)
        self.node = node
        self.setSharedRenderer(RESIZE_SVG)
        # self.setElementId("layer1")
        # self.rect = kwargs['rect']
        # self.pen = QPen(QColor(0, 0, 0), 2)

    # def boundingRect(self):
    #     return self.rect

    # def paint(self, painter, option, widget):
    #     path = QPainterPath()
    #     path.moveTo(self.rect.topRight())
    #     path.lineTo(self.rect.bottomLeft())
    #     painter.drawPath(path)
    #     path.moveTo(self.rect.left() + 4, self.rect.bottom())
    #     path.lineTo(self.rect.right(), self.rect.top() + 4)
    #     painter.setPen(self.pen)
    #     painter.drawPath(path)

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            event.ignore()
            return
        nodeUtils.options.setSelection([self.node])
        drag = QDrag(event.widget())
        mime = NodeMimeData()
        # data = QByteArray("%d" % id(self.node))
        data = QByteArray()
        mime.setData("node/resize", data)
        mime.setObject(self.node)
        drag.setMimeData(mime)
        drag.exec(Qt.MoveAction)


class DropDown(QtWidgets.QGraphicsPixmapItem):
    def __init__(self, parent, options, pixmap="resources/icons/dropdown.png"):
        QtWidgets.QGraphicsPixmapItem.__init__(
            self, options.getIcon(pixmap), parent
        )
        # self.rect = QRectF(0, 0, options.iconSize * 0.8, options.iconSize * 0.8)
        # self.pen = QPen(Qt.black, 1)
        # self.brush = QBrush(QColor(0, 0, 0, 120))
        self.state = False
        self.parent = parent
        self.setShapeMode(QtWidgets.QGraphicsPixmapItem.BoundingRectShape)

    def setState(self, state):
        self.state = state
        self.parent.setCollapsed(not state)

    def mousePressEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            self.setState(not self.state)
