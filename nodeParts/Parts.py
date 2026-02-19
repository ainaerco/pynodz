from qtpy.QtGui import QColor, QTextCursor, QTextCharFormat, QDrag
from qtpy.QtCore import Qt, QByteArray
from qtpy import QtWidgets
from qtpy.QtGui import QBrush, QPen, QCursor
from qtpy.QtSvg import QSvgRenderer
from qtpy.QtSvgWidgets import QGraphicsSvgItem
import nodeUtils
from nodeUtils import NodeMimeData
from nodeCommand import CommandSetNodeAttribute


class TitleItem(QtWidgets.QGraphicsTextItem):
    def __init__(self, text, parent, attr, title=False):
        QtWidgets.QGraphicsTextItem.__init__(self, text, parent)
        self.setFocus(Qt.FocusReason.MouseFocusReason)
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
            cursor.select(QTextCursor.SelectionType.Document)
            cursor.mergeCharFormat(format)

    def keyPressEvent(self, event):
        if event is not None and event.key() != Qt.Key.Key_Return:
            QtWidgets.QGraphicsTextItem.keyPressEvent(self, event)
        else:
            nodeUtils.options.undoStack.push(
                CommandSetNodeAttribute(
                    [self.parent], {self.attr: self.toPlainText()}
                )
            )
            self.setTextInteractionFlags(
                Qt.TextInteractionFlag.NoTextInteraction
            )

    def focusOutEvent(self, event):
        if (
            Qt.TextInteractionFlag.TextEditorInteraction
            == self.textInteractionFlags()
        ):
            nodeUtils.options.undoStack.push(
                CommandSetNodeAttribute(
                    [self.parent], {self.attr: self.toPlainText()}
                )
            )
        self.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self.textCursor().clearSelection()
        QtWidgets.QGraphicsTextItem.focusOutEvent(self, event)


class NodeInput(QtWidgets.QGraphicsRectItem):
    def __init__(self, parent, type=None):
        QtWidgets.QGraphicsRectItem.__init__(self, parent)
        self.parent = parent
        self._type = None
        self.setType(type)
        self._brush = QBrush(1)
        self._pen = QPen(Qt.GlobalColor.black, 0.3)

    def setType(self, type):
        self._type = type
        if type and type in nodeUtils.options.typeColors.keys():
            self._brush.setColor(nodeUtils.options.typeColors[type])
        self.update()

    def mousePressEvent(self, event):
        if event is None:
            return
        if event.button() != Qt.MouseButton.LeftButton:
            event.ignore()
            return

        drag = QDrag(event.widget())
        mime = NodeMimeData()
        mime.setData("node/connect", QByteArray())
        mime.setObject(self.parentItem())
        drag.setMimeData(mime)
        cursor = QCursor(Qt.CursorShape.ArrowCursor)
        drag.setDragCursor(cursor.pixmap(), Qt.DropAction.CopyAction)
        drag.exec(Qt.DropAction.CopyAction)

    def paint(self, painter, option, widget=None):
        if painter is None:
            return
        painter.setBrush(self._brush)
        painter.setPen(self._pen)
        painter.drawEllipse(self.boundingRect())


class NodeResize(QtWidgets.QGraphicsPixmapItem):
    def __init__(self, node, **kwargs):
        QtWidgets.QGraphicsPixmapItem.__init__(
            self,
            nodeUtils.options.getAwesomePixmap("fa6s.maximize", 16),
            node,
        )
        self.node = node

    def mousePressEvent(self, event):
        if event is None:
            return
        if event.button() != Qt.MouseButton.LeftButton:
            event.ignore()
            return
        nodeUtils.options.setSelection([self.node])
        drag = QDrag(event.widget())
        mime = NodeMimeData()
        data = QByteArray()
        mime.setData("node/resize", data)
        mime.setObject(self.node)
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.MoveAction)


class DropDown(QtWidgets.QGraphicsPixmapItem):
    def __init__(self, parent, options):
        pixmap = options.getAwesomePixmap("fa6s.caret-down", options.iconSize)
        QtWidgets.QGraphicsPixmapItem.__init__(self, pixmap, parent)
        self.state = False
        self.parent = parent
        self.setShapeMode(
            QtWidgets.QGraphicsPixmapItem.ShapeMode.BoundingRectShape
        )

    def setState(self, state):
        self.state = state
        self.parent.setCollapsed(not state)

    def mousePressEvent(self, event):
        if event is None:
            return
        if event.buttons() & Qt.MouseButton.LeftButton:
            self.setState(not self.state)
