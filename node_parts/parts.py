from qtpy.QtGui import QColor, QTextCursor, QTextCharFormat, QDrag
from qtpy.QtCore import Qt, QByteArray
from qtpy.QtWidgets import (
    QGraphicsDropShadowEffect,
    QGraphicsPixmapItem,
    QGraphicsRectItem,
    QGraphicsTextItem,
)
from qtpy.QtGui import QBrush, QPen, QCursor
import node_utils
from node_utils import NodeMimeData


class TitleItem(QGraphicsTextItem):
    def __init__(self, text, parent, attr, title=False):
        super().__init__(text, parent)
        self.setFocus(Qt.FocusReason.MouseFocusReason)
        self.parent_item = parent
        self.attr = attr
        self.setFont(node_utils.options.titleFont)
        if title:
            self.setDefaultTextColor(QColor(200, 200, 250))

            shadow = QGraphicsDropShadowEffect(self)
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
            super().keyPressEvent(event)
        else:
            from node_command import CommandSetNodeAttribute

            node_utils.options.undoStack.push(
                CommandSetNodeAttribute(
                    [self.parent_item], {self.attr: self.toPlainText()}
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
            from node_command import CommandSetNodeAttribute

            node_utils.options.undoStack.push(
                CommandSetNodeAttribute(
                    [self.parent_item], {self.attr: self.toPlainText()}
                )
            )
        self.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self.textCursor().clearSelection()
        super().focusOutEvent(event)


class NodeInput(QGraphicsRectItem):
    def __init__(self, parent, type=None):
        super().__init__(parent)
        self.parent_item = parent
        self._type = None
        self.setType(type)
        self._brush = QBrush(1)
        self._pen = QPen(Qt.GlobalColor.black, 0.3)

    def setType(self, type):
        self._type = type
        if type and type in node_utils.options.typeColors.keys():
            self._brush.setColor(node_utils.options.typeColors[type])
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


class NodeResize(QGraphicsPixmapItem):
    def __init__(self, node, **kwargs):
        super().__init__(
            node_utils.options.get_awesome_pixmap("fa6s.maximize", 16),
            node,
        )
        self.node = node

    def mousePressEvent(self, event):
        if event is None:
            return
        if event.button() != Qt.MouseButton.LeftButton:
            event.ignore()
            return
        node_utils.options.set_selection([self.node])
        drag = QDrag(event.widget())
        mime = NodeMimeData()
        data = QByteArray()
        mime.setData("node/resize", data)
        mime.setObject(self.node)
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.MoveAction)


class DropDown(QGraphicsPixmapItem):
    def __init__(self, parent, options):
        pixmap = options.get_awesome_pixmap("fa6s.caret-down", options.iconSize)
        super().__init__(pixmap, parent)
        self.state = False
        self.parent_item = parent
        self.setShapeMode(QGraphicsPixmapItem.ShapeMode.BoundingRectShape)

    def setState(self, state):
        self.state = state
        self.parent_item.setCollapsed(not state)

    def mousePressEvent(self, event):
        if event is None:
            return
        if event.buttons() & Qt.MouseButton.LeftButton:
            self.setState(not self.state)
