# from qtpy.QtGui import *
from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast


# For parent/widget that pyright sees as QObject but is NodeAttr in practice
def _attr_parent(obj: Any) -> Any:
    return cast(Any, obj)


from qtpy.QtGui import (
    QTextBlockFormat,
    QTextCursor,
    QColor,
    QPen,
    QBrush,
    QLinearGradient,
    QRadialGradient,
    QConicalGradient,
    QPainterPath,
    QDrag,
    QCursor,
    QFontMetrics,
    QPixmap,
    QImage,
    QKeyEvent,
)
from qtpy.QtCore import (
    QPropertyAnimation,
    Qt,
    QPointF,
    QRectF,
    QSizeF,
    QByteArray,
    QTimer,
    QRect,
)
from qtpy import QtWidgets

import bezier

import math
import colorsys
from copy import deepcopy

try:
    from images.imageDialog import PreviewFileDialog  # type: ignore[import-untyped]
except ImportError:
    PreviewFileDialog = QtWidgets.QFileDialog  # fallback
try:
    from _geometry import getBarycentric, Vector, Ray  # type: ignore[import-untyped]
except ImportError:
    Vector = None
    Ray = None
    getBarycentric = None

if TYPE_CHECKING:
    from qtpy.QtWidgets import QWidget

from nodeUtils import NodeMimeData
from nodeParts.Parts import DropDown
from random import random


def _is_node_shader(obj):
    """Avoid circular import: nodeTypes.NodeShader imports nodeAttrs."""
    from nodeTypes.NodeShader import NodeShader

    return isinstance(obj, NodeShader)


def lerp_2d_list(a, b, s):
    """
    source,target,value
    """
    # print lerp_2d_list
    (a1, a2), (b1, b2) = a, b
    return b1 + ((s - a1) * (b2 - b1) / (a2 - a1))


def getAttrByType(typ):
    if typ == "BOOL":
        return NodeAttrBool
    elif typ == "FLOAT":
        return NodeAttrFloat
    elif typ == "ENUM":
        return NodeAttrEnum
    elif typ == "RGB":
        return NodeAttrRgb
    elif typ == "RGBA":
        return NodeAttrRgb
    elif typ == "INT":
        return NodeAttrInt
    elif typ == "BYTE":
        return NodeAttrInt
    elif typ == "UINT":
        return NodeAttrInt
    elif typ == "VECTOR":
        return NodeAttrVector
    elif typ == "POINT":
        return NodeAttrVector
    elif typ == "POINT2":
        return NodeAttrVector
    elif typ == "STRING":
        return NodeAttrString
    elif typ == "MATRIX":
        return NodeAttrMatrix
    elif typ == "FLOAT[]":
        return NodeAttrSpline
    elif typ == "POINT[]":
        return NodeAttrArray
    elif typ == "INT[]":
        return NodeAttrArray
    elif typ == "VECTOR[]":
        return NodeAttrArray
    elif typ == "MATRIX[]":
        return NodeAttrArray
    elif typ == "RGB[]" or typ == "RGBA[]":
        return NodeAttrRamp
    elif typ == "POINT2[]":  # POINT2
        return NodeAttrArray
    elif typ == "STRING[]":
        return NodeAttrArray
    else:
        return None


def getAttrDefault(typ):
    if typ == "BOOL":
        return True
    elif typ == "FLOAT":
        return 0.0
    elif typ == "ENUM":
        return ""
    elif typ == "RGB":
        return [0.0, 0.0, 0.0]
    elif typ == "RGBA":
        return [0.0, 0.0, 0.0, 1.0]
    elif typ == "INT":
        return 0
    elif typ == "BYTE":
        return 0
    elif typ == "UINT":
        return 0
    elif typ == "VECTOR":
        return [0.0, 0.0, 0.0]
    elif typ == "POINT":
        return [0.0, 0.0, 0.0]
    elif typ == "POINT2":
        return [0.0, 0.0]
    elif typ == "STRING":
        return ""
    elif typ == "MATRIX":
        return [
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ]
    else:
        return None


class ItemRgbAnimation(QPropertyAnimation):
    def __init__(self, *args):
        QPropertyAnimation.__init__(self, *args)
        self._item = None
        self.rgb_pointsR = []
        self.rgb_bezierR = None
        self.rgb_pointsG = []
        self.rgb_bezierG = None
        self.rgb_pointsB = []
        self.rgb_bezierB = None

    def setRgbAt(self, t, r, g, b):
        self.rgb_pointsR += [(t, r)]
        if len(self.rgb_pointsR) > 3:
            self.rgb_bezierR = bezier.Bspline(self.rgb_pointsR)
        self.rgb_pointsG += [(t, g)]
        if len(self.rgb_pointsG) > 3:
            self.rgb_bezierG = bezier.Bspline(self.rgb_pointsG)
        self.rgb_pointsB += [(t, b)]
        if len(self.rgb_pointsB) > 3:
            self.rgb_bezierB = bezier.Bspline(self.rgb_pointsB)

    def setItem(self, item):
        self._item = item

    def afterAnimationStep(self, step):
        """Custom step handler for RGB animation. Parent QPropertyAnimation has no afterAnimationStep."""
        item = self._item
        if (
            item is not None
            and self.rgb_bezierR is not None
            and self.rgb_bezierG is not None
            and self.rgb_bezierB is not None
        ):
            r = self.rgb_bezierR(step)[1]
            g = self.rgb_bezierG(step)[1]
            b = self.rgb_bezierB(step)[1]
            item.setRgb(r, g, b)


class StringTextItem(QtWidgets.QGraphicsTextItem):
    def __init__(self, parent, options, value, index=None):
        QtWidgets.QGraphicsTextItem.__init__(self, parent)
        self.setPlainText(value)
        self.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.setPos(0, -4)
        self.options = options
        self.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.index = index
        self.parent = parent
        self.setFont(self.options.attributeFont)

    def setAlignment(self, alignment):
        self.alignment = alignment
        format = QTextBlockFormat()
        format.setAlignment(alignment)
        cursor = self.textCursor()
        cursor.select(QTextCursor.SelectionType.Document)
        cursor.mergeBlockFormat(format)
        cursor.clearSelection()
        self.setTextCursor(cursor)

    def setValue(self, text):
        text = str(text)
        parent = self.parent()
        if parent is None:
            return
        p = _attr_parent(parent)
        if not self.index:
            if p._value != text:
                p._value = text
                self.setAlignment(Qt.AlignmentFlag.AlignRight)
                p.updateAttribute()
        elif isinstance(self.index, (list, tuple)) and len(self.index) == 2:
            if p._value[self.index[0]][self.index[1]] != text:
                p._value[self.index[0]][self.index[1]] = text
                self.setAlignment(Qt.AlignmentFlag.AlignRight)
                p.updateAttribute()
        else:
            if p._value[self.index] != text:
                p._value[self.index] = text
                self.setAlignment(Qt.AlignmentFlag.AlignRight)
                p.updateAttribute()

    def focusOutEvent(self, event):
        if (
            Qt.TextInteractionFlag.TextEditorInteraction
            == self.textInteractionFlags()
        ):
            self.setValue(self.toPlainText())
        self.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self.textCursor().clearSelection()
        QtWidgets.QGraphicsTextItem.focusOutEvent(self, event)

    def mouseDoubleClickEvent(
        self, event: QtWidgets.QGraphicsSceneMouseEvent | None
    ):
        if event is not None:
            event.accept()
        self.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextEditorInteraction
        )
        self.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.setFocus(Qt.FocusReason.MouseFocusReason)

    def keyPressEvent(self, event: QKeyEvent | None):
        if event is None:
            return
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            if (
                Qt.TextInteractionFlag.TextEditorInteraction
                == self.textInteractionFlags()
            ):
                self.setValue(self.toPlainText())
            self.setTextInteractionFlags(
                Qt.TextInteractionFlag.NoTextInteraction
            )
            self.textCursor().clearSelection()
        QtWidgets.QGraphicsTextItem.keyPressEvent(self, event)


class NumericTextItem(StringTextItem):
    def __init__(self, parent, options, value, mask, index=None):
        StringTextItem.__init__(self, parent, options, mask % value, index)

        self.mask = mask

    def setAlignment(self, alignment: Qt.AlignmentFlag):
        self.alignment = alignment
        format = QTextBlockFormat()
        format.setAlignment(alignment)
        cursor = self.textCursor()
        cursor.select(QTextCursor.SelectionType.Document)
        cursor.mergeBlockFormat(format)
        cursor.clearSelection()
        self.setTextCursor(cursor)

    def setValue(self, text: str):
        v = float(text)
        parent = self.parent()
        if parent is None:
            return
        p = _attr_parent(parent)
        if self.index is None:
            if p._value == v:
                return
            p._value = v
        elif isinstance(self.index, (list, tuple)) and len(self.index) == 2:
            if p._value[self.index[0]][self.index[1]] == v:
                return
            p._value[self.index[0]][self.index[1]] = v
        else:
            if p._value[self.index] == v:
                return
            p._value[self.index] = v
        self.setAlignment(Qt.AlignmentFlag.AlignRight)
        p.updateAttribute()

    def keyPressEvent(self, event: QKeyEvent | None):
        if event is None:
            return
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            # self.setValue(self.toPlainText())
            self.setTextInteractionFlags(
                Qt.TextInteractionFlag.NoTextInteraction
            )
            self.textCursor().clearSelection()
        if (
            (event.key() > Qt.Key.Key_0 and event.key() < Qt.Key.Key_9)
            or event.key() == Qt.Key.Key_Period
            or event.key() == Qt.Key.Key_Backspace
            or event.key() == Qt.Key.Key_Delete
            or event.key() == Qt.Key.Key_Left
            or event.key() == Qt.Key.Key_Right
            or event.key() == Qt.Key.Key_Escape
        ):
            QtWidgets.QGraphicsTextItem.keyPressEvent(self, event)


class NodeAttr(QtWidgets.QGraphicsWidget):
    def __init__(self, parent, options, attr):
        QtWidgets.QGraphicsWidget.__init__(self, parent)
        # DeviceCoordinateCache = 1 (Qt enum; stub may not define it)
        self.setCacheMode(cast(Any, 1))
        self.setZValue(1)
        self.attr = attr
        self.options = options
        self._type = attr["type"]
        if isinstance(attr["default"], list):
            self._value = deepcopy(attr["default"])
        else:
            self._value = attr["default"]
        self.pinIcon = None
        if _is_node_shader(parent) and not isinstance(self, NodePanel):
            self.pin = PinUnpin(self, options, False)
            # self.pinIcon = QtWidgets.QGraphicsPixmapItem(self.options.getIcon('resources/icons/unpin.png'), self)
            self.pin.setPos(-18, 0)

        self._rect = QRectF()
        self.pen = QPen()
        self.pen.setWidthF(0.5)
        self.connectedPen = QPen(2)
        self.connectedPen.setColor(QColor(20, 20, 150))
        self.connectedPen.setWidth(2)
        self.connected = False
        # self.brush = QBrush(QColor(150, 150, 150))
        gradient = QLinearGradient(
            self._rect.topLeft(), self._rect.bottomRight()
        )
        color = QColor(150, 150, 150)
        gradient.setColorAt(0, color)
        color.setHsv(
            color.hue(), max(0, color.saturation() - 60), color.value(), 100
        )
        gradient.setColorAt(1, color)
        self.brush = QBrush(gradient)

        self.darkBrush = QBrush(QColor(50, 50, 50, 150))
        self.selectedBrush = QBrush(QColor(255, 153, 62, 180))
        self.label = self.attr["name"] + self.attr["type"]
        if "label" in attr.keys():
            self.label = self.attr["label"]

        self.shadow = QtWidgets.QGraphicsDropShadowEffect()
        self.shadow.setOffset(4, 4)
        self.shadow.setBlurRadius(8)
        self.setGraphicsEffect(self.shadow)
        self.setGraphicsItem(self)
        if _is_node_shader(self.parent()):
            self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event is not None:
            event.accept()

    def dragMoveEvent(self, event):
        if event is not None:
            event.accept()

    def dropEvent(self, event):
        if event is None:
            return
        mime = event.mimeData()
        if mime is None or not mime.hasFormat("node/connect"):
            return
        self.setConnected(True)
        event.accept()
        self.update()

    def setConnected(self, state):
        if self.connected != state:
            self.pen, self.connectedPen = self.connectedPen, self.pen
        self.connected = state

    def updateAttribute(self, name=None, value=None):
        p = self.parent()
        if p is not None:
            _attr_parent(p).updateAttribute(self.attr["name"], self._value)

    def setDefault(self):
        self._value = self.attr["default"]

    def setGeometry(self, geom):  # pyright: ignore[reportIncompatibleMethodOverride]
        self.prepareGeometryChange()
        QtWidgets.QGraphicsWidget.setGeometry(self, geom)
        self.setPos(geom.topLeft())

    def resize(self, width, height):  # pyright: ignore[reportIncompatibleMethodOverride]
        self._rect = QRectF(0, 0, width, height)
        gradient = QLinearGradient(
            self._rect.topLeft(), self._rect.bottomLeft()
        )
        color = QColor(150, 150, 150)
        gradient.setColorAt(0, color)
        color.setHsv(
            color.hue(),
            max(0, color.saturation() - 60),
            int(color.value() * 0.4),
            100,
        )
        gradient.setColorAt(1, color)
        self.brush = QBrush(gradient)
        QtWidgets.QGraphicsWidget.resize(self, width, height)

    def sizeHint(self, which, constraint=None):
        sh = getattr(Qt, "SizeHintFlag", getattr(Qt, "SizeHint", None))
        if sh and (which == sh.MinimumSize or which == sh.PreferredSize):
            return QSizeF(self._rect.width(), self._rect.height())
        return constraint if constraint is not None else QSizeF()

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self._value = value

    def paint(self, painter, option, widget=None):
        if painter is None:
            return
        painter.setPen(self.pen)
        painter.setFont(self.options.attributeFont)
        painter.drawText(5, 10, self.attr["name"] + self.attr["type"])

    def contextMenuEvent(self, event):
        if event is None:
            return
        p = self.parent()
        if p is None or not _is_node_shader(p):
            return
        scene = self.scene()
        menu_parent = cast("QWidget | None", scene.parent() if scene else None)
        menu = QtWidgets.QMenu(menu_parent)
        defaultAction = menu.addAction("Revert to default")
        action = menu.exec(QCursor.pos())
        if action == defaultAction:
            self.setDefault()
            self.updateAttribute(self.attr["name"], self._value)
        event.accept()

    def updateGeometry(self):
        QtWidgets.QGraphicsWidget.updateGeometry(self)
        layout = self.parentLayoutItem()
        if not layout:
            return
        parent = layout.parentLayoutItem()
        if not isinstance(parent, NodePanel):
            return
        parent.prepareGeometryChange()
        parent.fitItems()
        QtWidgets.QGraphicsWidget.updateGeometry(parent)


class NodeAttrEnum(NodeAttr):
    def __init__(self, parent, options, attr):
        NodeAttr.__init__(self, parent, options, attr)
        self.buttonRect = QRectF()
        self.mousePosition = QPointF()

        self.label = self.attr["name"]

        self.expanded = False
        self.height = self._rect.height()

        self.items = self.attr["enum"]
        if isinstance(self.items, str):
            self.items = [self.attr["enum"]]
        self.path = QPainterPath()

    def resize(self, width, height):
        self._rect = QRectF(0, 0, width, height)
        self.buttonRect = QRectF(
            self._rect.width() - self._rect.height(),
            0,
            self._rect.height(),
            self._rect.height(),
        )
        self.path = QPainterPath()
        c = self.buttonRect.center()
        self.path.moveTo(c.x(), c.y() + self.buttonRect.height() / 2 * 0.6)
        self.path.lineTo(
            c.x() - self.buttonRect.width() / 2 * 0.6,
            c.y() - self.buttonRect.height() / 2 * 0.4,
        )
        self.path.lineTo(
            c.x() + self.buttonRect.width() / 2 * 0.6,
            c.y() - self.buttonRect.height() / 2 * 0.4,
        )
        self.path.lineTo(c.x(), c.y() + self.buttonRect.height() / 2 * 0.6)
        self.height = self._rect.height()
        QtWidgets.QGraphicsWidget.resize(self, width, height)

    def paint(self, painter, option, widget=None):
        painter.setBrush(self.brush)
        painter.setPen(self.pen)
        painter.setFont(self.options.attributeFont)
        rounded = QPainterPath()
        rounded.addRoundedRect(
            self._rect, self.options.nodeRadius, self.options.nodeRadius
        )
        painter.drawPath(rounded)
        w = self.options.attributeFont.pixelSize()
        if not self.expanded:
            painter.drawRoundedRect(
                self.buttonRect,
                self.options.nodeRadius,
                self.options.nodeRadius,
            )
            painter.setBrush(self.darkBrush)
            painter.drawPath(self.path)
            fm = QFontMetrics(self.options.attributeFont)
            painter.drawText(5, w, self.label)
            text_w = (
                fm.horizontalAdvance(self._value)
                if hasattr(fm, "horizontalAdvance")
                else getattr(fm, "width", lambda _: 0)(self._value)
            )
            painter.drawText(
                self._rect.width() - self.buttonRect.width() - text_w - 5,
                w,
                self._value,
            )
        else:
            painter.setPen(QPen(0))
            painter.setBrush(self.selectedBrush)
            selectPath = QPainterPath()
            selectPath.addRect(
                0, self.mousePosition.y() - w * 0.5, self._rect.width(), w
            )
            selectPath = selectPath.intersected(rounded)
            painter.drawPath(selectPath)
            painter.setPen(self.pen)
            for i in range(len(self.items)):
                painter.drawText(5, w + i * w, self.items[i])

    def mousePressEvent(self, event):
        if event is None or event.button() != Qt.MouseButton.LeftButton:
            if event is not None:
                event.ignore()
            return

        if self.expanded:
            pos = int(
                self.mousePosition.y() / self.options.attributeFont.pixelSize()
            )
            pos = min(max(pos, 0), len(self.items) - 1)
            self.value = self.items[pos]
            self.updateAttribute(self.attr["name"], self._value)
            self.hoverLeaveEvent(None)
        else:
            self.expanded = True
            self._rect.setHeight(
                len(self.items) * self.options.attributeFont.pixelSize()
                + self.options.attributeFont.pixelSize() / 2
            )
            self.prepareGeometryChange()
            self.setZValue(2)
            self.setAcceptHoverEvents(True)
            self.updateGeometry()

    def hoverLeaveEvent(self, event):
        self.expanded = False
        self.setAcceptHoverEvents(False)
        self.prepareGeometryChange()
        self._rect.setHeight(self.height)
        #
        self.setZValue(0)
        self.updateGeometry()

    def hoverMoveEvent(self, event):
        if event is not None:
            self.mousePosition = event.pos()
        self.update()


class NodeAttrFloat(NodeAttr):  # (QGraphicsObject, NodeAttr):
    def __init__(self, parent, options, attr):
        NodeAttr.__init__(self, parent, options, attr)
        self.margin = 7
        self.valueRect = QRectF()
        self.numericText = NumericTextItem(
            self, self.options, self._value, r"%.2f"
        )

        self.dragStart = None
        self.softmin = 0.0
        self.softmax = 1.0
        if "softmin" in self.attr.keys():
            self.softmin = self.attr["softmin"]
        if "softmax" in self.attr.keys():
            self.softmax = self.attr["softmax"]
        self.min = None
        if "min" in self.attr.keys():
            self.min = self.attr["min"]
        self.max = None
        if "max" in self.attr.keys():
            self.max = self.attr["max"]
        if "default" in self.attr.keys():
            if self.attr["default"] > self.softmax:
                self.softmax = self.attr["default"]
            elif self.attr["default"] < self.softmin:
                self.softmin = self.attr["default"]
        self.pen.setWidth(1)
        self.setAcceptDrops(True)

    def resize(self, width, height):
        self._rect = QRectF(0, 0, width, height)
        self.numericText.setTextWidth(self._rect.width())
        QtWidgets.QGraphicsWidget.resize(self, width, height)

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        value = float(value)
        if self.max:
            value = min(self.max, value)
        if self.min:
            value = max(self.min, value)
        self._value = value
        self.numericText.setPlainText("%.2f" % self._value)
        self.numericText.setAlignment(Qt.AlignmentFlag.AlignRight)

    def paint(self, painter, option, widget=None):
        painter.setBrush(self.darkBrush)
        painter.setPen(self.pen)
        painter.drawRoundedRect(
            self._rect, self.options.nodeRadius, self.options.nodeRadius
        )
        v = lerp_2d_list(
            (self.softmin, self.softmax),
            (0, self._rect.width() - 2 * self.margin),
            self._value,
        )
        v = min(v, self._rect.width() - 2 * self.margin)
        painter.setBrush(self.selectedBrush)
        painter.drawRect(self.margin, 0, v, self._rect.height())
        painter.setFont(self.options.attributeFont)
        painter.drawText(
            self.margin + 5, self.options.attributeFont.pixelSize(), self.label
        )

    def setRgb(self, r, g, b):
        self.selectedBrush.setColor(QColor(r, g, b, 150))
        self.update()

    def mousePressEvent(self, event):
        if event is None:
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragStart = event.pos().x()
            drag = QDrag(event.widget())
            mime = NodeMimeData()
            mime.setData("attr/float", QByteArray())
            mime.setObject(self)
            drag.setMimeData(mime)
            drag.exec(Qt.DropAction.MoveAction)

    def dragMoveEvent(self, event):
        mime = event.mimeData()
        if self.dragStart is not None:
            if (
                abs(self.mapFromScene(event.scenePos()).x() - self.dragStart)
                < 5
            ):
                event.accept()
                return
        if mime.hasFormat("attr/float") and mime.getObject() == self:
            self.drag(event)
            self.update()
            event.accept()

    def drag(self, event):
        if event is None:
            return
        p = self.mapFromScene(event.scenePos())
        v = max(
            0, min(p.x() - self.margin, self._rect.width() - 2 * self.margin)
        )
        v = lerp_2d_list(
            (0, self._rect.width() - 2 * self.margin),
            (self.softmin, self.softmax),
            v,
        )
        self.value = v
        self.dragStart = None

    def dropEvent(self, event):
        NodeAttr.dropEvent(self, event)
        self.updateAttribute(self.attr["name"], self._value)


class NodeAttrInt(NodeAttrFloat):
    def __init__(self, parent, options, attr):
        NodeAttrFloat.__init__(self, parent, options, attr)
        self.softmin = 0
        self.softmax = 1
        self.numericText.mask = r"%d"
        self.numericText.setPlainText(self.numericText.mask % self._value)
        self.numericText.setAlignment(Qt.AlignmentFlag.AlignRight)

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        value = round(value)
        if value == self.value:
            return
        if "max" in self.attr.keys():
            value = min(self.attr["max"], value)
        if "min" in self.attr.keys():
            value = max(self.attr["min"], value)
        self._value = int(value)
        self.numericText.setPlainText("%d" % self._value)
        self.numericText.setAlignment(Qt.AlignmentFlag.AlignRight)


class NodeAttrVector(NodeAttrFloat):
    def __init__(self, parent, options, attr):
        NodeAttr.__init__(self, parent, options, attr)
        self.margin = 7
        self.softmin = 0.0
        self.softmax = 1.0
        self.dimension = len(self._value)
        self.numericTexts = []
        for i in range(self.dimension):
            self.numericTexts += [
                NumericTextItem(self, self.options, self._value[i], r"%.2f", i)
            ]
        self.setAcceptDrops(True)
        self.dragStart = None

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self._value = value
        for i in range(self.dimension):
            self.numericTexts[i].setPlainText("%.2f" % self._value[i])
            self.numericTexts[i].setAlignment(Qt.AlignmentFlag.AlignRight)

    def paint(self, painter, option, widget=None):
        for i in range(self.dimension):
            painter.setBrush(self.darkBrush)
            painter.setPen(self.pen)
            r = QRectF(
                0, 0, self._rect.width() / self.dimension, self._rect.height()
            )
            r.moveLeft(i * self._rect.width() / self.dimension)
            painter.drawRoundedRect(
                r, self.options.nodeRadius, self.options.nodeRadius
            )
            painter.setBrush(self.selectedBrush)
            r.moveLeft(self.margin + i * self._rect.width() / self.dimension)
            v = max(self.softmin, min(self.softmax, self._value[i]))
            v = lerp_2d_list(
                (self.softmin, self.softmax),
                (0, self._rect.width() / self.dimension - 2 * self.margin),
                v,
            )
            r.setWidth(v)
            painter.drawRect(r)
        painter.setFont(self.options.attributeFont)
        painter.drawText(
            self.margin + 5, self.options.attributeFont.pixelSize(), self.label
        )

    def resize(self, width, height):
        self._rect = QRectF(0, 0, width, height)
        for i in range(self.dimension):
            self.numericTexts[i].setPos(
                i * self._rect.width() / self.dimension, -4
            )
            self.numericTexts[i].setTextWidth(
                self._rect.width() / self.dimension
            )
        QtWidgets.QGraphicsWidget.resize(self, width, height)

    def drag(self, event):
        x = self.mapFromScene(event.scenePos()).x()
        for i in range(self.dimension):
            if (
                x >= i * self._rect.width() / self.dimension + self.margin
                and x
                <= (i + 1) * self._rect.width() / self.dimension - self.margin
            ):
                self._value[i] = lerp_2d_list(
                    (
                        i * self._rect.width() / self.dimension + self.margin,
                        (i + 1) * self._rect.width() / self.dimension
                        - self.margin,
                    ),
                    (self.softmin, self.softmax),
                    x,
                )
                self.numericTexts[i].setPlainText("%.2f" % self._value[i])
                self.numericTexts[i].setAlignment(Qt.AlignmentFlag.AlignRight)
                self.update()


class NodeAttrMatrix(NodeAttrFloat):
    def __init__(self, parent, options, attr):
        NodeAttr.__init__(self, parent, options, attr)
        self.margin = 7
        self.softmin = 0.0
        self.softmax = 1.0

        self.setDefault()
        self.dimension = 4
        self.numericTexts = []
        for i in range(self.dimension):
            n = []
            for j in range(self.dimension):
                n += [
                    NumericTextItem(
                        self, self.options, self._value[i][j], r"%.2f", [i, j]
                    )
                ]
            self.numericTexts += [n]
        self.setAcceptDrops(True)

    def setDefault(self):
        if self.attr["default"] == "":
            self._value = [
                [1, 0, 0, 0],
                [0, 1, 0, 0],
                [0, 0, 1, 0],
                [0, 0, 0, 1],
            ]

    @property
    def value(self):  # pyright: ignore[reportIncompatibleMethodOverride]
        return self._value

    @value.setter
    def value(self, value):  # pyright: ignore[reportIncompatibleMethodOverride]
        self._value = value
        for i in range(self.dimension):
            for j in range(self.dimension):
                self.numericTexts[i][j].setPlainText("%.2f" % self._value[i][j])
                self.numericTexts[i][j].setAlignment(
                    Qt.AlignmentFlag.AlignRight
                )

    def paint(self, painter, option, widget=None):
        if painter is None:
            return
        painter.setPen(self.pen)
        painter.drawRoundedRect(
            self._rect, self.options.nodeRadius, self.options.nodeRadius
        )
        painter.setBrush(self.darkBrush)
        for i in range(self.dimension):
            for j in range(self.dimension):
                r = QRectF(
                    0,
                    0,
                    (self._rect.width() - self.margin * 2) / self.dimension,
                    self.options.attributeFont.pixelSize() + 2,
                )
                r.moveTo(
                    self.margin
                    + j
                    * (self._rect.width() - self.margin * 2)
                    / self.dimension,
                    (i + 1) * (self.options.attributeFont.pixelSize() + 5),
                )
                painter.drawRoundedRect(
                    r, self.options.nodeRadius, self.options.nodeRadius
                )
                r.moveTo(
                    self.margin
                    + self.margin
                    + j
                    * (self._rect.width() - self.margin * 2)
                    / self.dimension,
                    (i + 1) * (self.options.attributeFont.pixelSize() + 5),
                )
                v = max(self.softmin, min(self.softmax, self._value[i][j]))
                v = lerp_2d_list(
                    (self.softmin, self.softmax),
                    (
                        0,
                        (self._rect.width() - self.margin * 2) / self.dimension
                        - 2 * self.margin,
                    ),
                    v,
                )
                r.setWidth(v)
                painter.drawRect(r)
        painter.setFont(self.options.attributeFont)
        painter.drawText(
            2 * self.margin, self.options.attributeFont.pixelSize(), self.label
        )

    def resize(self, width, height):
        height = max(
            height,
            (self.options.attributeFont.pixelSize() + 5) * (self.dimension + 1)
            + self.margin,
        )
        self._rect = QRectF(0, 0, width, height)

        for i in range(self.dimension):
            for j in range(self.dimension):
                self.numericTexts[i][j].setPos(
                    self.margin
                    + j * (width - self.margin * 2) / self.dimension,
                    (i + 1) * (self.options.attributeFont.pixelSize() + 5) - 4,
                )
                self.numericTexts[i][j].setTextWidth(
                    (width - self.margin * 2) / self.dimension
                )
        QtWidgets.QGraphicsWidget.resize(self, width, height)

    def drag(self, event):
        pos = self.mapFromScene(event.scenePos())
        for i in range(self.dimension):
            for j in range(self.dimension):
                if not (
                    pos.x()
                    >= self.margin
                    + j
                    * (self._rect.width() - self.margin * 2)
                    / self.dimension
                    and pos.x()
                    <= (j + 1)
                    * (self._rect.width() - self.margin * 2)
                    / self.dimension
                    and pos.y()
                    > (i + 1) * (self.options.attributeFont.pixelSize() + 5)
                    and pos.y()
                    < (i + 1) * (self.options.attributeFont.pixelSize() + 5)
                    + self.options.attributeFont.pixelSize()
                    + 2
                ):
                    continue

                self._value[i][j] = lerp_2d_list(
                    (
                        j
                        * (self._rect.width() - self.margin * 2)
                        / self.dimension
                        + self.margin,
                        (j + 1)
                        * (self._rect.width() - 2 * self.margin)
                        / self.dimension,
                    ),
                    (self.softmin, self.softmax),
                    pos.x(),
                )
                self.numericTexts[i][j].setPlainText("%.2f" % self._value[i][j])
                self.numericTexts[i][j].setAlignment(
                    Qt.AlignmentFlag.AlignRight
                )

                self.update()
                return


class NodeAttrBool(NodeAttr):
    def __init__(self, parent, options, attr):
        NodeAttr.__init__(self, parent, options, attr)
        self.brush.setColor(QColor(70, 70, 70, 50))
        self.buttonRect = QRectF(0, 0, 14, 14)
        self.path = QPainterPath()
        self.path.moveTo(self.buttonRect.x(), self.buttonRect.height() / 2)
        self.path.lineTo(
            self.buttonRect.x() + self.buttonRect.width() / 2.0,
            self.buttonRect.height(),
        )
        self.path.lineTo(self.buttonRect.x() + self.buttonRect.width(), 0)
        self.path.lineTo(self.buttonRect.x() + self.buttonRect.width() - 1.2, 0)
        self.path.lineTo(
            self.buttonRect.x() + self.buttonRect.width() / 2.0 - 0.3,
            self.buttonRect.height() - 1.5,
        )
        self.path.lineTo(
            self.buttonRect.x(), self.buttonRect.height() / 2 - 1.5
        )
        # self.label = self.attr['name']

    def paint(self, painter, option, widget=None):
        painter.setPen(self.pen)
        painter.setBrush(self.brush)
        painter.drawRoundedRect(
            self.buttonRect,
            self.options.nodeRadius * 0.3,
            self.options.nodeRadius * 0.3,
        )
        if self._value:
            painter.setBrush(QBrush())
            painter.drawPath(self.path)
        painter.setFont(self.options.attributeFont)
        painter.drawText(
            self.buttonRect.right() + 5,
            self.options.attributeFont.pixelSize(),
            self.label,
        )

    def mousePressEvent(self, event):
        if event is None or not (event.buttons() & Qt.MouseButton.LeftButton):
            self._value = not self._value
            self.updateAttribute(self.attr["name"], self._value)
            # self.update()


class NodeAttrImage(NodeAttr):
    def __init__(self, parent, options, attr):
        NodeAttr.__init__(self, parent, options, attr)
        self.pixmap = QtWidgets.QGraphicsPixmapItem(
            options.getAwesomePixmap("fa6s.image", 64),
            self,
        )
        self.textItem = StringTextItem(self, self.options, attr["default"])
        self.textItem.setPlainText("")
        self._value = attr["default"]
        # ItemClipsChildrenToShape (stub may not define it)
        self.setFlag(cast(Any, 0x100), True)

    def setAlignment(self, alignment):
        self.alignment = alignment
        format = QTextBlockFormat()
        format.setAlignment(alignment)
        cursor = self.textItem.textCursor()
        cursor.select(QTextCursor.SelectionType.Document)
        cursor.mergeBlockFormat(format)
        cursor.clearSelection()
        self.textItem.setTextCursor(cursor)

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):  # pyright: ignore[reportIncompatibleMethodOverride]
        self._value = value
        self.textItem.setPlainText(str(value))
        self.textItem.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.update()

    def resize(self, width, height):
        width = self.pixmap.boundingRect().width()
        height = self.pixmap.boundingRect().height()
        self.pixmap.setPos(
            width / 2 - self.pixmap.boundingRect().width() / 2, 0
        )
        self._rect = QRectF(0, 0, width, height)
        self.textItem.setTextWidth(width)
        QtWidgets.QGraphicsWidget.resize(self, width, height)

    def contextMenuEvent(self, event):
        if event is None:
            return
        scene = self.scene()
        menu_parent = cast("QWidget | None", scene.parent() if scene else None)
        menu = QtWidgets.QMenu(menu_parent)
        defaultAction = menu.addAction("Revert to default")
        editNameAction = menu.addAction("Edit string")
        fileNameAction = menu.addAction("Open file")
        action = menu.exec(event.screenPos())
        if action == defaultAction:
            self.setDefault()
            self.textItem.setPlainText(self._value)
            self.textItem.setAlignment(Qt.AlignmentFlag.AlignRight)
            self.updateAttribute(self.attr["name"], self._value)
        if action == editNameAction and event is not None:
            self.textItem.mouseDoubleClickEvent(event)
        if action == fileNameAction:
            dialog = PreviewFileDialog(
                menu_parent,
                "Open artwork",
                "",
                r"Image Files (*.tx *.tif *.png *.jpg);;",
            )
            dialog.setAcceptMode(
                cast(Any, 0)
            )  # QFileDialog.AcceptMode.AcceptOpen
            ok = dialog.exec()
            f = [x for x in dialog.selectedFiles()]
            if not ok or not f:
                return
            preview_pixmap = getattr(dialog, "pixmap", None)
            if preview_pixmap is not None:
                w = int(self.pixmap.boundingRect().width())
                h = int(self.pixmap.boundingRect().height())
                tm = getattr(Qt, "TransformationMode", None)
                aspect = tm.KeepAspectRatio if tm else 1
                smooth = tm.SmoothTransformation if tm else 2
                self.pixmap.setPixmap(
                    preview_pixmap.scaled(w, h, aspect, smooth)
                )
            self.textItem.setValue(f[0])
            self.textItem.setPlainText(f[0])
            self.textItem.setAlignment(Qt.AlignmentFlag.AlignRight)
            self.prepareGeometryChange()
            self.resize(self.size().width(), self.size().height())
            self.update()

        event.accept()

    def paint(self, painter, option, widget=None):
        painter.setPen(self.pen)
        painter.setBrush(self.brush)
        painter.drawRoundedRect(
            self._rect, self.options.nodeRadius, self.options.nodeRadius
        )
        painter.setFont(self.options.attributeFont)
        painter.drawText(
            4, self.options.attributeFont.pixelSize(), self.attr["name"]
        )


class NodeAttrString(NodeAttr):
    def __init__(self, parent, options, attr):
        NodeAttr.__init__(self, parent, options, attr)
        self.textItem = StringTextItem(self, self.options, attr["default"])
        self.textItem.setPlainText("")
        self._value = attr["default"]

    def setAlignment(self, alignment):
        self.alignment = alignment
        format = QTextBlockFormat()
        format.setAlignment(alignment)
        cursor = self.textItem.textCursor()
        cursor.select(QTextCursor.SelectionType.Document)
        cursor.mergeBlockFormat(format)
        cursor.clearSelection()
        self.textItem.setTextCursor(cursor)

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):  # pyright: ignore[reportIncompatibleMethodOverride]
        self._value = value
        self.textItem.setPlainText(str(value))
        self.textItem.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.update()

    def resize(self, width, height):
        self._rect = QRectF(0, 0, width, height)
        self.textItem.setTextWidth(width)
        QtWidgets.QGraphicsWidget.resize(self, width, height)

    def contextMenuEvent(self, event):
        if event is None:
            return
        scene = self.scene()
        menu_parent = cast("QWidget | None", scene.parent() if scene else None)
        menu = QtWidgets.QMenu(menu_parent)
        defaultAction = menu.addAction("Revert to default")
        editNameAction = menu.addAction("Edit string")
        fileNameAction = menu.addAction("Open file")
        action = menu.exec(event.screenPos())
        if action == defaultAction:
            self.setDefault()
            self.textItem.setPlainText(self._value)
            self.textItem.setAlignment(Qt.AlignmentFlag.AlignRight)
            self.updateAttribute(self.attr["name"], self._value)
        if action == editNameAction:
            self.textItem.mouseDoubleClickEvent(event)
        if action == fileNameAction:
            f, mask = QtWidgets.QFileDialog.getOpenFileName(
                menu_parent, "Open File", "", "All Files (*.*)"
            )
            if f:
                self.textItem.setValue(f)
                self.textItem.setPlainText(f)
                self.textItem.setAlignment(Qt.AlignmentFlag.AlignRight)

        event.accept()

    def paint(self, painter, option, widget=None):
        painter.setPen(self.pen)
        painter.setBrush(self.brush)
        painter.drawRoundedRect(
            self._rect, self.options.nodeRadius, self.options.nodeRadius
        )
        painter.setFont(self.options.attributeFont)
        painter.drawText(
            4, self.options.attributeFont.pixelSize(), self.attr["name"]
        )


class NodeAttrArray(NodeAttr):
    def __init__(self, parent, options, attr):
        NodeAttr.__init__(self, parent, options, attr)
        self.addButton = QRectF(
            0,
            0,
            self.options.attributeFont.pixelSize(),
            self.options.attributeFont.pixelSize(),
        )
        self.removeButton = QRectF(
            0,
            0,
            self.options.attributeFont.pixelSize(),
            self.options.attributeFont.pixelSize(),
        )
        # self.label = self.attr['name']
        self._value = None
        self.items = []
        self.addPath = QPainterPath()
        self.removePath = QPainterPath()
        p = 1.7

        c = self.addButton.center()
        r = self.addButton.right()
        b = self.addButton.bottom()
        self.addPath.moveTo(c.x() - p, c.y() - p)
        self.addPath.lineTo(c.x() - p, 0)
        self.addPath.lineTo(c.x() + p, 0)
        self.addPath.lineTo(c.x() + p, c.y() - p)
        self.addPath.lineTo(r, c.y() - p)
        self.addPath.lineTo(r, c.y() + p)
        self.addPath.lineTo(c.x() + p, c.y() + p)
        self.addPath.lineTo(c.x() + p, b)
        self.addPath.lineTo(c.x() - p, b)
        self.addPath.lineTo(c.x() - p, c.y() + p)
        self.addPath.lineTo(0, c.y() + p)
        self.addPath.lineTo(0, c.y() - p)
        self.addPath.lineTo(c.x() - p, c.y() - p)

        c = self.removeButton.center()
        r = self.removeButton.right()
        b = self.removeButton.bottom()
        self.removePath.moveTo(0, c.y() - p)
        self.removePath.lineTo(r, c.y() - p)
        self.removePath.lineTo(r, c.y() + p)
        self.removePath.lineTo(0, c.y() + p)
        self.removePath.lineTo(0, c.y() - p)

    def setDefault(self):
        self.value = []

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self._value = value
        self.prepareGeometryChange()
        while len(self.items) > 0:
            self.removeItem()

        if not self._value:
            return
        if not isinstance(self._value, list) or len(self._value) == 0:
            return
        for d in self._value:
            self.addItem({"default": deepcopy(d)})

        self.resize(self._rect.width(), self._rect.height())
        self.updateGeometry()
        self.update()

    def addItem(self, d=None):
        if self.attr["type"].endswith("[]"):
            typ = self.attr["type"][:-2]
        else:
            return
        if d is None:
            d = {}
        d["name"] = self.attr["name"] + str(len(self.items))
        d["label"] = self.attr["name"] + str(len(self.items))
        d["type"] = typ
        clas = getAttrByType(typ)
        if clas is None:
            return
        if "default" not in d:
            default = getAttrDefault(typ)

            if default is None:
                return
            d["default"] = deepcopy(default)
        n = clas(self, self.options, d)

        self.items += [n]

    def removeItem(self):
        if len(self.items) == 0:
            return
        n = self.items[-1]
        scene = self.scene()
        if scene is not None:
            scene.removeItem(n)
        del self.items[-1]

    def updateAttribute(self, name=None, value=None):
        self._value = []
        for i in range(len(self.items)):
            self._value += [self.items[i].value]
        p = self.parent()
        if p is not None:
            _attr_parent(p).updateAttribute(self.attr["name"], self._value)

    def resize(self, width, height):
        self._rect = QRectF(0, 0, width, height)

        # self.itemHeight = rect.height()
        self.addPath.translate(-self.addButton.topLeft())
        self.removePath.translate(-self.removeButton.topLeft())
        h = self.options.attributeFont.pixelSize() + 5
        for i in range(len(self.items)):
            self.items[i].prepareGeometryChange()
            self.items[i].resize(
                width - 10, self.options.attributeFont.pixelSize()
            )
            self.items[i].setPos(5, h)
            self.items[i].updateGeometry()
            h += self.items[i].geometry().height() + 5
            # (self.options.attributeFont.pixelSize()+3)*(i+1)

        self._rect.setHeight(h)
        self.addButton = QRectF(
            width - self.options.attributeFont.pixelSize(),
            0,
            self.options.attributeFont.pixelSize(),
            self.options.attributeFont.pixelSize(),
        )

        self.removeButton = QRectF(
            width - 2 * self.options.attributeFont.pixelSize() - 3,
            0,
            self.options.attributeFont.pixelSize(),
            self.options.attributeFont.pixelSize(),
        )
        self.addPath.translate(self.addButton.topLeft())
        self.removePath.translate(self.removeButton.topLeft())

        QtWidgets.QGraphicsWidget.resize(self, width, h)
        # self.update()

    def paint(self, painter, option, widget=None):
        painter.setBrush(self.brush)
        painter.setPen(self.pen)
        painter.setFont(self.options.attributeFont)

        painter.drawRoundedRect(
            self._rect, self.options.nodeRadius, self.options.nodeRadius
        )

        painter.drawRoundedRect(
            self.addButton, self.options.nodeRadius, self.options.nodeRadius
        )
        painter.drawRoundedRect(
            self.removeButton, self.options.nodeRadius, self.options.nodeRadius
        )
        painter.drawPath(self.addPath)
        painter.drawPath(self.removePath)
        painter.drawText(5, self.options.attributeFont.pixelSize(), self.label)

    def mousePressEvent(self, event):
        if event is None or event.button() != Qt.MouseButton.LeftButton:
            if event is not None:
                event.ignore()
            return
        if self.addButton.contains(event.pos()):
            self.prepareGeometryChange()
            self.addItem()
            self.updateAttribute(self.attr["name"], self._value)
            self.resize(self._rect.width(), self._rect.height())
            self.updateGeometry()
            # self.update()
        if self.removeButton.contains(event.pos()):
            self.prepareGeometryChange()
            self.removeItem()
            self.updateAttribute(self.attr["name"], self._value)
            self.resize(self._rect.width(), self._rect.height())
            self.updateGeometry()
            # self.update()


class SplinePoint(QtWidgets.QGraphicsItem):
    def __init__(self, parent):
        QtWidgets.QGraphicsItem.__init__(self, parent)
        self._rect = QRectF(-7, -7, 14, 14)
        self.color = [0.0, 0.0, 0.0]
        self.path = QPainterPath()
        self.path.addEllipse(QPointF(), 4, 4)
        self.setAcceptDrops(True)
        self.selected = False

    def boundingRect(self):
        return self._rect

    def paint(self, painter, option, widget=None):
        if painter is None:
            return
        if self.selected:
            painter.setPen(QPen(QColor(200, 0, 50)))
        painter.drawPath(self.path)

    def shape(self):
        p = QPainterPath()
        p.addRect(self._rect)
        return p

    def mousePressEvent(self, event):
        if event is None or event.button() != Qt.MouseButton.LeftButton:
            if event is not None:
                event.ignore()
            return
        drag = QDrag(event.widget())
        mime = NodeMimeData()
        mime.setData("spline/move", QByteArray())
        mime.setObject(self)
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.MoveAction)
        event.accept()

    def contextMenuEvent(self, event):
        return
        if self.anchor:
            return
        menu = QtWidgets.QMenu(self.scene().parent())
        defaultAction = menu.addAction("Delete")
        action = menu.exec(QCursor.pos())
        if action == defaultAction:
            self.parent().removePoint(self)
            self.parent().updateSpline()
        event.accept()


class RampRect(NodeAttr):
    def __init__(self, parent, options, attr):
        NodeAttr.__init__(self, parent, options, attr)
        self.label = "Spline::" + self.attr["name"]

        self.points = []  # [SplinePoint(self),SplinePoint(self)]

        self.setAcceptDrops(True)
        self.setFlag(cast(Any, 0x1))  # ItemIsFocusable
        self.selectedId = 0
        self.gradient = QLinearGradient()
        self.gradient.setColorAt(0, QColor(0, 0, 0))
        self.gradient.setColorAt(1, QColor(0, 0, 0))

    def updateNumeric(self):
        p = self.parent()
        if p is not None:
            _attr_parent(p).updateNumeric(
                self.selectedId, self.points[self.selectedId].pos()
            )

    def updateColor(self):
        p = self.parent()
        if p is not None:
            _attr_parent(p).updateColor(self.points[self.selectedId].color)

    def updateRamp(self):
        self.gradient = QLinearGradient()
        for p in self.points:
            c = QColor()
            c.setRgbF(p.color[0], p.color[1], p.color[2])
            self.gradient.setColorAt(p.pos().x() / self._rect.width(), c)
        self.gradient.setStart(self._rect.topLeft())
        self.gradient.setFinalStop(self._rect.topRight())

    def updateValue(self):
        # self._value = [[self.start.pos().x(),self.start.pos().y()]]
        self._value = []
        for p in self.points:
            self._value += [[p.pos().x(), p.pos().y()]]
        # self._value += [[self.end.pos().x(),self.end.pos().y()]]

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self._value = value
        while len(self.points) != 0:
            self.removePoint(self.points[-1])
        # print self._value,not self._value
        if not self._value or not isinstance(self._value, list):
            self._value = []
            n = SplinePoint(self)
            n.setPos(self._rect.left(), self._rect.height() / 2)
            n.selected = True
            self.points = [n]
            self._value = [[n.pos().x(), n.pos().y()]]
            n = SplinePoint(self)
            n.setPos(self._rect.right(), self._rect.height() / 2)
            self.points += [n]
            self._value += [[n.pos().x(), n.pos().y()]]
            self.selectedId = 0
            self.updateNumeric()

            return
        for i in range(len(self._value)):
            n = SplinePoint(self)
            n.setPos(self._value[i][0], self._rect.height() / 2)
            if i == self.selectedId:
                n.selected = True
            self.points += [n]
        self.updateNumeric()
        # self.updateSpline()

    def resize(self, width, height):
        self._rect = QRectF(0, 0, width, height)
        if self.points:
            self.points[0].setPos(self._rect.left(), height / 2)
            self.points[-1].setPos(self._rect.right(), height / 2)
        QtWidgets.QGraphicsWidget.resize(self, width, height)

    def paint(self, painter, option, widget=None):
        painter.setBrush(QBrush(self.gradient))
        painter.setPen(self.pen)
        painter.drawRect(self._rect)

    def addPoint(self, pos):
        n = SplinePoint(self)
        n.setPos(pos.x(), self._rect.height() / 2)
        n.color = [random(), random(), random()]
        self.points += [n]
        return n

    def removePoint(self, point):
        n = None
        ni: int | None = None
        for i in range(len(self.points)):
            if self.points[i] == point:
                n = self.points[i]
                ni = i
                break
        if not n or ni is None:
            return
        scene = self.scene()
        if scene is not None:
            scene.removeItem(n)
        del self.points[ni]

    def focusOutEvent(self, event):
        QtWidgets.QGraphicsWidget.focusOutEvent(self, event)

    def mousePressEvent(self, event):
        self.setFocus(Qt.FocusReason.MouseFocusReason)
        if event is None or event.button() != Qt.MouseButton.LeftButton:
            # event.ignore()
            return
        event.ignore()

        n = self.addPoint(event.pos())
        scene = self.scene()
        drag = QDrag(scene.parent() if scene else None)
        mime = NodeMimeData()
        mime.setData("spline/move", QByteArray())
        mime.setObject(n)
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.MoveAction)

    def dragEnterEvent(self, event):
        self.setFocus(Qt.FocusReason.MouseFocusReason)
        if event is None:
            return
        mime = event.mimeData()
        # if not mime.hasFormat('spline/move') or mime.getObject().parent != self:
        #    return

        for i in range(len(self.points)):
            if self.points[i] == mime.getObject():
                mime.getObject().selected = True
            else:
                self.points[i].selected = False

    def dragMoveEvent(self, event):
        if event is None:
            return
        mime = event.mimeData()
        obj = mime.getObject() if mime else None
        if (
            mime
            and mime.hasFormat("spline/move")
            and obj is not None
            and getattr(obj, "parent", None) == self
        ):
            p = self.mapFromScene(event.scenePos())
            if obj == self.points[0] or obj == self.points[-1]:
                obj.setPos(obj.pos().x(), p.y())
            else:
                obj.setPos(p.x(), self._rect.height() / 2)

            self.points.sort(key=lambda x: x.pos().x())
            self.updateRamp()
            self.update()

    def dropEvent(self, event):
        for i in range(len(self.points)):
            if self.points[i].selected:
                self.selectedId = i
                break
        self.updateColor()
        self.updateValue()
        self.updateAttribute(self.attr["name"], self._value)

    def keyPressEvent(self, event):
        if len(self.points) < 3:
            return
        if event is None:
            return
        if event.key() == Qt.Key.Key_Backspace:
            self.removePoint(self.points[-2])
            self.selectedId = 0
            self.updateValue()
            self.updateRamp()
            self.update()
            return
        elif event.key() == Qt.Key.Key_Delete:
            if self.selectedId != 0 and self.selectedId != len(self.points) - 1:
                self.removePoint(self.points[self.selectedId])
                self.selectedId = 0
                # self.updateNumeric()
                self.updateValue()
                self.updateRamp()
                self.update()
                # self.parent().updateAttribute(self)
                return


class SplineRect(NodeAttr):
    def __init__(self, parent, options, attr):
        NodeAttr.__init__(self, parent, options, attr)
        self.label = "Spline::" + self.attr["name"]

        self.points = []  # [SplinePoint(self),SplinePoint(self)]

        self.path = QPainterPath()
        self.spline = QPainterPath()
        self.setAcceptDrops(True)
        self.setFlag(cast(Any, 0x1))  # ItemIsFocusable
        self.selectedId = 0

    def updateNumeric(self):
        p = self.parent()
        if p is not None:
            _attr_parent(p).updateNumeric(
                self.selectedId, self.points[self.selectedId].pos()
            )

    def updateValue(self):
        # self._value = [[self.start.pos().x(),self.start.pos().y()]]
        self._value = []
        for p in self.points:
            self._value += [[p.pos().x(), p.pos().y()]]
        # self._value += [[self.end.pos().x(),self.end.pos().y()]]

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self._value = value
        while len(self.points) != 0:
            self.removePoint(self.points[-1])
        # print self._value,not self._value
        if not self._value or not isinstance(self._value, list):
            self._value = []
            n = SplinePoint(self)
            n.setPos(self._rect.bottomLeft())
            n.selected = True
            self.points = [n]
            self._value = [[n.pos().x(), n.pos().y()]]
            n = SplinePoint(self)
            n.setPos(self._rect.topRight())
            self.points += [n]
            self._value += [[n.pos().x(), n.pos().y()]]
            self.updateSpline()
            self.selectedId = 0
            self.updateNumeric()

            return
        for i in range(len(self._value)):
            n = SplinePoint(self)
            n.setPos(self._value[i][0], self._value[i][1])
            if i == self.selectedId:
                n.selected = True
            self.points += [n]

        self.updateNumeric()
        self.updateSpline()
        self.update()

    def resize(self, width, height):
        self._rect = QRectF(0, 0, width, height)
        if self.points:
            self.points[0].setPos(self._rect.bottomLeft())
            self.points[-1].setPos(self._rect.topRight())
        QtWidgets.QGraphicsWidget.resize(self, width, height)

    def paint(self, painter, option, widget=None):
        painter.setBrush(self.darkBrush)
        painter.setPen(self.pen)
        painter.setFont(self.options.attributeFont)
        painter.drawRect(self._rect)
        painter.drawPath(self.spline)

    def addPoint(self, pos):
        n = SplinePoint(self)
        n.setPos(pos)
        self.points += [n]
        return n

    def removePoint(self, point):
        n = None
        ni: int | None = None
        for i in range(len(self.points)):
            if self.points[i] == point:
                n = self.points[i]
                ni = i
                break
        if not n or ni is None:
            return
        scene = self.scene()
        if scene is not None:
            scene.removeItem(n)
        del self.points[ni]

    def updateSpline(self):
        # http://stackoverflow.com/questions/14344099/smooth-spline-representation-of-an-arbitrary-contour-flength-x-y
        p_x = [-20]
        p_y = [self.points[0].pos().y()]
        for i in range(len(self.points)):
            p_x += [self.points[i].pos().x()]
            p_y += [self.points[i].pos().y()]
        p_x += [self._rect.width() + 20]
        p_y += [self.points[-1].pos().y()]
        x_intpol, y_intpol = bezier.CatmullRom(p_x, p_y, 20)

        # print len(x_intpol),self.options.splineStep,len(p_x)
        self.spline = QPainterPath()
        self.spline.moveTo(0, y_intpol[0])
        for i in range(len(x_intpol)):
            # print x_intpol[i], y_intpol[i]
            self.spline.lineTo(x_intpol[i], y_intpol[i])
        self.spline.lineTo(self._rect.bottomRight())
        self.spline.lineTo(self._rect.bottomLeft())
        rounded = QPainterPath()
        rounded.addRoundedRect(
            self._rect, self.options.nodeRadius, self.options.nodeRadius
        )
        self.spline = self.spline.intersected(rounded)

    def focusOutEvent(self, event):
        QtWidgets.QGraphicsWidget.focusOutEvent(self, event)

    def mousePressEvent(self, event):
        self.setFocus(Qt.FocusReason.MouseFocusReason)
        if event is None or event.button() != Qt.MouseButton.LeftButton:
            return
        event.ignore()

        n = self.addPoint(event.pos())
        scene = self.scene()
        drag_parent = scene.parent() if scene else None
        drag = QDrag(drag_parent)
        mime = NodeMimeData()
        mime.setData("spline/move", QByteArray())
        mime.setObject(n)
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.MoveAction)

    def keyPressEvent(self, event):
        if event is None or len(self.points) < 3:
            return
        if event.key() == Qt.Key.Key_Backspace:
            self.removePoint(self.points[-2])
            self.selectedId = 0
            # self.updateNumeric()
            self.updateValue()
            # self.updateSpline()
            self.updateAttribute(self.attr["name"], self._value)
            return
        elif event.key() == Qt.Key.Key_Delete:
            if self.selectedId != 0 and self.selectedId != len(self.points) - 1:
                self.removePoint(self.points[self.selectedId])
                self.selectedId = 0
                # self.updateNumeric()
                self.updateValue()
                # self.updateSpline()
                self.updateAttribute(self.attr["name"], self._value)
                return

    def dragEnterEvent(self, event):
        self.setFocus(Qt.FocusReason.MouseFocusReason)
        if event is None:
            return
        mime = event.mimeData()
        # if not mime.hasFormat('spline/move') or mime.getObject().parent != self:
        #    return
        for i in range(len(self.points)):
            if self.points[i] == mime.getObject():
                mime.getObject().selected = True
            else:
                self.points[i].selected = False

    def dragMoveEvent(self, event):
        if event is None:
            return
        mime = event.mimeData()
        obj = mime.getObject() if mime else None
        if (
            mime
            and mime.hasFormat("spline/move")
            and obj is not None
            and getattr(obj, "parent", None) == self
        ):
            p = self.mapFromScene(event.scenePos())
            if obj == self.points[0] or obj == self.points[-1]:
                obj.setPos(obj.pos().x(), p.y())
            else:
                obj.setPos(p)

            self.points.sort(key=lambda x: x.pos().x())
            self.updateSpline()
            self.update()

    def dropEvent(self, event):
        for i in range(len(self.points)):
            if self.points[i].selected:
                self.selectedId = i
                break
        self.updateValue()
        self.updateAttribute(self.attr["name"], self._value)


class NodeAttrSpline(NodeAttr):
    def __init__(self, parent, options, attr):
        NodeAttr.__init__(self, parent, options, attr)
        self.widget = SplineRect(self, options, attr)
        self.widget.setVisible(False)

        self.margin = 7
        self.numericText = NumericTextItem(
            self, self.options, 0, r"%.2f", [0, 1]
        )
        self.numericText.setVisible(False)
        self.dropdown = DropDown(self, options)
        self.dropdown.setState(True)
        self.collapsed = True

    def updateNumeric(self, id, pos):
        self.numericText.index = [id, 1]
        self.numericText.setPlainText("%.2f" % pos.y())
        self.numericText.setAlignment(Qt.AlignmentFlag.AlignRight)

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self._value = value
        self.widget.value = value

    def updateAttribute(self, name=None, value=None):
        if name is not None:
            self._value = value
        p = self.parent()
        if p is not None:
            _attr_parent(p).updateAttribute(self.attr["name"], self._value)

    def resize(self, width, height):
        self._rect.setWidth(width)
        self._rect.setHeight(height)
        self.dropdown.setPos(width - self.dropdown.boundingRect().width(), 0)
        self.numericText.setTextWidth(width)
        w = self.options.attributeFont.pixelSize()
        self.numericText.setPos(0, height - w - self.margin)

        self.height = w + self.margin

        self.widget.prepareGeometryChange()
        self.widget.setPos(self.margin, w + self.margin)
        self.widget.resize(
            width - self.margin * 2, height - w * 2 - self.margin * 2
        )
        if self.widget.points:
            self.widget.updateSpline()
            self.widget.updateGeometry()
        QtWidgets.QGraphicsWidget.resize(self, width, height)

    def paint(self, painter, option, widget=None):
        painter.setBrush(self.darkBrush)
        painter.setPen(self.pen)
        painter.drawRoundedRect(
            self._rect, self.options.nodeRadius, self.options.nodeRadius
        )
        painter.setFont(self.options.attributeFont)
        painter.drawText(5, self.options.attributeFont.pixelSize(), self.label)

    def setCollapsed(self, state):
        self.collapsed = state
        if self.collapsed:
            self.prepareGeometryChange()
            self.widget.setVisible(True)
            self.numericText.setVisible(True)
            self.resize(self._rect.width(), 130)
            self.updateGeometry()
            # self.setAcceptHoverEvents(True)
        else:
            self.widget.setVisible(False)
            self.numericText.setVisible(False)
            self.prepareGeometryChange()
            self.resize(
                self._rect.width(), self.options.attributeFont.pixelSize() + 6
            )
            self.updateGeometry()

    def hoverLeaveEvent(self, event):
        return
        self.expanded = False
        self.setAcceptHoverEvents(False)
        self.widget.setVisible(False)
        self.numericText.setVisible(False)
        self.prepareGeometryChange()
        self.resize(self._rect.width(), self.height)
        self.updateGeometry()


class NodeAttrRamp(NodeAttr):
    def __init__(self, parent, options, attr):  # , , attrPos, attrInterp):
        NodeAttr.__init__(self, parent, options, attr)
        self.widget = RampRect(self, options, attr)
        self.widget.setVisible(False)

        self.margin = 7
        self.numericText = NumericTextItem(
            self, self.options, 0, r"%.2f", [0, 0]
        )
        self.numericText.setVisible(False)
        self.colorItem = NodeAttrRgb(
            self,
            options,
            {"name": "color", "type": "RGB", "default": [0, 0, 0]},
        )
        self.colorItem.setVisible(False)
        self.colorItem.setZValue(3)
        self.label = "Ramp::" + self.attr["name"]
        self.dropdown = DropDown(self, options)
        self.dropdown.setState(True)
        self.collapsed = True

    def updateNumeric(self, id, pos):
        self.numericText.index = [id, 0]
        self.numericText.setPlainText("%.2f" % pos.x())
        self.numericText.setAlignment(Qt.AlignmentFlag.AlignRight)

    def updateColor(self, color):
        self.colorItem.value = color
        self.colorItem.update()

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self._value = value
        self.widget.value = value

    def updateAttribute(self, name=None, value=None):
        if name is not None:
            self._value = value
        p = self.parent()
        if p is not None:
            _attr_parent(p).updateAttribute(self.attr["name"], self._value)

    def resize(self, width, height):
        self._rect.setWidth(width)
        self._rect.setHeight(height)
        self.dropdown.setPos(width - self.dropdown.boundingRect().width(), 0)
        w = self.options.attributeFont.pixelSize()
        self.numericText.setTextWidth(width * 0.5 - 2 * self.margin)
        self.numericText.setPos(
            width * 0.5 + self.margin, height - w - 1.2 * self.margin
        )

        self.colorItem.prepareGeometryChange()
        self.colorItem.resize(width * 0.7, w)
        self.colorItem.setPos(self.margin, height - w - self.margin)
        self.colorItem.updateGeometry()

        self.height = w + self.margin
        self.widget.setPos(self.margin, w + self.margin)
        self.widget.resize(
            width - self.margin * 2, height - w * 2 - self.margin * 3
        )
        QtWidgets.QGraphicsWidget.resize(self, width, height)

    def paint(self, painter, option, widget=None):
        painter.setBrush(self.darkBrush)
        painter.setPen(self.pen)
        painter.drawRoundedRect(
            self._rect, self.options.nodeRadius, self.options.nodeRadius
        )
        painter.setFont(self.options.attributeFont)
        painter.drawText(5, self.options.attributeFont.pixelSize(), self.label)

    def setCollapsed(self, state):
        self.collapsed = state
        if self.collapsed:
            self.prepareGeometryChange()
            self.widget.setVisible(True)
            self.numericText.setVisible(True)
            self.colorItem.setVisible(True)
            self.resize(self._rect.width(), 130)
            self.updateGeometry()
            self.setZValue(2)
            # self.setAcceptHoverEvents(True)
        else:
            self.widget.setVisible(False)
            self.numericText.setVisible(False)
            self.colorItem.setVisible(False)
            self.prepareGeometryChange()
            self.resize(
                self._rect.width(), self.options.attributeFont.pixelSize() + 6
            )
            self.setZValue(1)
            self.updateGeometry()


def dot(a, b):
    return a.x() * b.x() + a.y() * b.y()


def cross(a, b):
    return a.x() * b.y() - a.y() * b.x()


def length(p):
    return (p.x() * p.x() + p.y() * p.y()) ** 0.5


def angle(a, b):
    la = length(a)
    lb = length(b)
    if la == 0.0 or lb == 0.0:
        return 0.0
    costheta = dot(a, b) / (la * lb)
    if costheta > 1.0:
        costheta = 1.0
    if costheta < -1.0:
        costheta = -1.0
    return math.acos(costheta)


def rotate(point, angle):
    c = math.cos(angle)
    s = math.sin(angle)
    px = point.x() * c - point.y() * s
    py = point.x() * s + point.y() * c
    a = QPointF(px, py)
    return a


class PinUnpin(QtWidgets.QGraphicsPixmapItem):
    def __init__(self, parent, options, pinned=False):
        QtWidgets.QGraphicsPixmapItem.__init__(self, parent)
        self.parent = parent
        self.options = options
        self.state = None
        self.setState(pinned)
        self.setShapeMode(cast(Any, 0))  # BoundingRectShape

    def setState(self, state):
        if self.state == state:
            return
        self.state = state
        if self.state:
            self.setPixmap(
                self.options.getAwesomePixmap(
                    "fa6s.thumbtack", self.options.iconSize
                )
            )
        else:
            self.setPixmap(
                self.options.getAwesomePixmap(
                    "fa6s.thumbtack-slash", self.options.iconSize
                )
            )

    def mousePressEvent(self, event):
        if event is not None and (event.buttons() & Qt.MouseButton.LeftButton):
            self.setState(not self.state)
            p = self.parent()
            if p is not None:
                pp = p.parent()
                if pp is not None:
                    _attr_parent(pp).pinUnpin(_attr_parent(p).attr, self.state)


class ColorPicker(QtWidgets.QGraphicsPixmapItem):
    def __init__(self, icon, parent):
        QtWidgets.QGraphicsPixmapItem.__init__(self, icon, parent)
        self.parent = parent
        # QDesktopWidget.screenCount()

        self.timer = QTimer()
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.onTimer)
        self.setShapeMode(cast(Any, 0))  # BoundingRectShape
        # self.setMouseTracking(True)

    def onTimer(self):
        b = self.img.pixel(QCursor.pos())
        c = QColor()
        c.setRgb(b)

        p = self.parent()
        if p is not None and hasattr(p, "value"):
            p.value = [c.redF(), c.greenF(), c.blueF()]
            p.update()

    def ungrab(self):
        self.timer.stop()
        p = self.parent()
        if p is not None:
            _attr_parent(p).updateAttribute()

    def mousePressEvent(self, event):
        if event is None or self.timer.isActive():
            return
        desktop = getattr(QtWidgets.QApplication, "desktop", None)
        if desktop is None:
            return
        app_desktop = desktop()
        self.screens = app_desktop.screenCount()
        wholeDisplayGeometry = QRect()
        for i in range(self.screens):
            screenRect = app_desktop.screenGeometry(i)
            wholeDisplayGeometry = wholeDisplayGeometry.united(screenRect)
        grab = getattr(QPixmap, "grabWindow", None)
        if grab is None:
            return
        grabbed = grab(
            app_desktop.winId(),
            wholeDisplayGeometry.x(),
            wholeDisplayGeometry.y(),
            wholeDisplayGeometry.width(),
            wholeDisplayGeometry.height(),
        )
        self.img = grabbed.toImage()
        scene = self.scene()
        if scene is not None:
            win = scene.parent()
            if win is not None:
                setattr(win, "grabber", self)
                grab_mouse = getattr(win, "grabMouse", None)
                if grab_mouse is not None:
                    grab_mouse()
        self.timer.start()


class NodePanel(NodeAttr):
    def __init__(self, parent, options, attr):
        NodeAttr.__init__(self, parent, options, attr)
        self.setZValue(0)
        self.label = attr["label"]
        self.dropdown = DropDown(self, options)
        self.collapsed = True
        self.dropdown.setState(False)

        # self.setCollapsed(True)
        self.setAcceptHoverEvents(True)
        # self.timer = QTimer()
        # self.timer.setInterval(1000)
        # self.timer.setSingleShot(True)
        # self.timer.timeout.connect(self.onTimer)

    def resize(self, width, height):
        self.dropdown.setPos(width - self.dropdown.boundingRect().width(), 0)
        NodeAttr.resize(self, width, height)

    def fitItems(self):
        if self.collapsed:
            height = self.options.attributeFont.pixelSize() + 4
            self.resize(self._rect.width(), height)
            return
        layout = self.layout()
        if layout is None:
            return
        margin = getattr(layout, "spacing", lambda: 0)() or 0
        (left, t, r, b) = layout.getContentsMargins()
        height = float(t) if t is not None else 0.0
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item is not None:
                geom = item.geometry() if hasattr(item, "geometry") else None
                h = geom.height() if geom is not None else 0
                height += (h if h is not None else 0) + margin

        height += b if b is not None else 0
        self.resize(self._rect.width(), height)

    def updateItems(self):
        if self.collapsed:
            return
        layout = self.layout()
        if not layout:
            return
        (left, t, r, b) = layout.getContentsMargins()
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item is not None:
                it = cast(Any, item)
                if hasattr(it, "prepareGeometryChange"):
                    it.prepareGeometryChange()
                if hasattr(it, "resize"):
                    geom = it.geometry() if hasattr(it, "geometry") else None
                    h = geom.height() if geom is not None else 0
                    left_f = left if left is not None else 0
                    r_f = r if r is not None else 0
                    it.resize(self._rect.width() - left_f - r_f, h)
                if hasattr(it, "updateGeometry"):
                    QtWidgets.QGraphicsWidget.updateGeometry(it)

    def updateGeometry(self):
        QtWidgets.QGraphicsWidget.updateGeometry(self)

    def paint(self, painter, option, widget=None):
        if painter is None:
            return
        painter.setPen(self.pen)
        painter.setBrush(self.brush)
        painter.setFont(self.options.attributeFont)
        painter.drawRoundedRect(
            self._rect, self.options.nodeRadius, self.options.nodeRadius
        )
        painter.drawText(7, self.options.attributeFont.pixelSize(), self.label)

    def setCollapsed(self, state):
        if self.collapsed == state:
            return
        layout = self.layout()
        if layout is None:
            return
        self.collapsed = state
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item is not None and hasattr(cast(Any, item), "setVisible"):
                cast(Any, item).setVisible(not state)

        self.prepareGeometryChange()
        self.fitItems()
        self.updateItems()
        QtWidgets.QGraphicsWidget.updateGeometry(self)
        self.update()

    def onTimer(self):
        self.setCollapsed(True)

    def hoverEnterEvent(self, event):
        # self.timer.stop()
        pass
        # self.setCollapsed(False)

    def hoverLeaveEvent(self, event):
        # self.timer.start()
        pass


class NodeAttrRgb(NodeAttr):
    def __init__(self, parent, options, attr):
        NodeAttr.__init__(self, parent, options, attr)
        self.expanded = False
        self.colorRect = QRectF()
        self.buttonRect = QRectF()
        self.path = QPainterPath()
        self.triangleImage = QImage()
        self.triangle = QPainterPath()
        self.point = QPointF()
        self.p1 = QPointF()
        self.p2 = QPointF()
        self.p3 = QPointF()
        self.p4 = QPointF()
        self.colorPicker = ColorPicker(
            self.options.getAwesomePixmap(
                "fa6s.eye-dropper", self.options.iconSize
            ),
            self,
        )
        self.colorPicker.setVisible(False)
        self.circle = QPainterPath()
        self.circleCenter = QPointF()
        self.circlePoint = QPointF()
        self.circleRadius = 0.0
        self.margin = 7

        self.label = self.attr["name"]
        if "label" in attr.keys():
            self.label = self.attr["label"]

        self.hue = 0.0
        self.sat = 1.0
        self.val = 1.0
        self.alpha = 1.0

        self.valueBrush = QBrush()
        self.valueRect = QRectF()
        self.valuePoint = QPointF()
        self.opacityBrush = QBrush()
        self.opacityRect = QRectF()
        self.opacityPoint = QPointF()
        self.opacityPixmap = QBrush(
            self.options.getIcon("resources/icons/transparent_small.png")
        )

        self.gradientP1 = QLinearGradient()
        self.gradientP1.setColorAt(0, QColor(255, 0, 0, 255))
        self.gradientP1.setColorAt(1, QColor(255, 255, 255))
        self.gradientP3 = QLinearGradient()
        self.gradientP3.setColorAt(0, QColor(0, 0, 0))
        self.gradientP3.setColorAt(1, QColor(0, 0, 0, 0))
        self.gradientC = QRadialGradient()

        self.gradientHSV = QConicalGradient()
        angle = 0.0
        c = QColor()
        while angle <= 360.0:
            c.setHsvF(angle / 360.0, 1.0, 1.0, 1.0)
            self.gradientHSV.setColorAt(angle / 360.0, c)
            angle += 30.0
        d = {}
        d["name"] = self.attr["name"]
        d["label"] = self.attr["type"]
        d["type"] = "VECTOR"
        d["default"] = self._value
        self.vectorItem = NodeAttrVector(self, options, d)
        self.vectorItem.setVisible(False)
        self.value = self._value
        self.setAcceptDrops(True)

    def updateAttribute(self, name=None, value=None):
        if name:
            self.value = value
        p = self.parent()
        if p is not None:
            _attr_parent(p).updateAttribute(self.attr["name"], self._value)

    def updateValue(self):
        c = list(colorsys.hsv_to_rgb(self.hue, self.sat, self.val))
        if self.attr["type"] == "RGBA":
            c += [self.alpha]
        self._value = c
        self.vectorItem.value = c

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        # print self,'value.setter'
        if self.attr["type"] == "RGBA":
            self.alpha = value[3]
        hsv = list(colorsys.rgb_to_hsv(value[0], value[1], value[2]))
        if hsv[1] != 0.0:
            self.hue = hsv[0]
        self.sat = hsv[1]
        self.val = hsv[2]
        self._value = value
        self.updateTriangle()
        self.updatePoint()
        # self.update()

    def setHue(self, v):
        self.hue = v
        if self.hue > 1:
            self.hue = self.hue - 1
        if self.hue < 0:
            self.hue = self.hue + 1

    def fromPoint(self):
        if self.options.colorSelector == "triangle":
            a = angle(self.p3 - self.p1, self.p3 - self.point)
            self.sat = lerp_2d_list((0.0, math.pi / 3.0), (1.0, 0.0), a)
            p3t = self.p3 - (self.p1 + self.p2) * 0.5
            p3p = self.p3 - self.point
            proj_len = math.cos(angle(p3t, p3p)) * length(p3p)
            self.val = lerp_2d_list((0.0, length(p3t)), (0.0, 1.0), proj_len)
        if self.options.colorSelector == "square":
            p1p = self.p1 - self.point
            proj_len = math.cos(angle(self.p1 - self.p2, p1p)) * length(p1p)
            self.sat = lerp_2d_list(
                (0.0, length(self.p2 - self.p1)), (1.0, 0.0), proj_len
            )
            p3p = self.p3 - self.point
            proj_len = math.cos(angle(self.p3 - self.p2, p3p)) * length(p3p)
            self.val = lerp_2d_list(
                (0.0, length(self.p3 - self.p2)), (0.0, 1.0), proj_len
            )
        # print self.sat,self.val

    def updatePoint(self):
        # print self,'updatePoint'
        self.circlePoint = QPointF(self.circleRadius * 0.85, 0.0)
        self.circlePoint = self.circleCenter + rotate(
            self.circlePoint, -self.hue * math.pi * 2
        )
        s = lerp_2d_list(
            (0.0, 1.0),
            (self.valueRect.bottom(), self.valueRect.top()),
            self.val,
        )
        cx = self.valueRect.center().x()
        self.valuePoint = QPointF(cx if cx is not None else 0.0, s)
        s = lerp_2d_list(
            (0.0, 1.0),
            (self.opacityRect.bottom(), self.opacityRect.top()),
            self.alpha,
        )
        ox = self.opacityRect.center().x()
        self.opacityPoint = QPointF(ox if ox is not None else 0.0, s)
        if self.val == 0.0:
            self.point = self.p3
            return
        if Ray is None or Vector is None:
            return
        s = lerp_2d_list((1.0, 0.0), (0.0, math.pi / 3.0), self.sat)
        a = self.p3 - self.p1
        a = rotate(a, s)

        ray = Ray(
            Vector(self.p3.x(), self.p3.y(), 0.0), Vector(-a.x(), -a.y(), 0.0)
        )
        a = ray.intersectRayLine(
            Vector(self.p1.x(), self.p1.y(), 0.0),
            Vector(self.p2.x(), self.p2.y(), 0.0),
        )

        # a = intersectRayLine(self.p3,-a,self.p1,self.p2)
        a = QPointF(a.x, a.y)

        # if a is None:
        #    a = QPointF(self.p2)
        a = self.p3 - a
        a = a * self.val
        self.point = self.p3 - a

    def updateTriangle(self):
        # print self,'updateTriangle'
        radius = self.circleRadius * 0.7
        self.triangle = QPainterPath()
        a = -self.hue * math.pi * 2
        c = QColor()
        c.setHsvF(self.hue, 1.0, 1.0, 1.0)
        if self.options.colorSelector == "triangle":
            self.p1.setX(math.cos(a) * radius + self.circleCenter.x())
            self.p1.setY(math.sin(a) * radius + self.circleCenter.y())
            self.p2.setX(
                math.cos(math.pi * 2.0 / 3.0 + a) * radius
                + self.circleCenter.x()
            )
            self.p2.setY(
                math.sin(math.pi * 2.0 / 3.0 + a) * radius
                + self.circleCenter.y()
            )
            self.p3.setX(
                math.cos(math.pi * 4.0 / 3.0 + a) * radius
                + self.circleCenter.x()
            )
            self.p3.setY(
                math.sin(math.pi * 4.0 / 3.0 + a) * radius
                + self.circleCenter.y()
            )
            self.triangle.moveTo(self.p1)
            self.triangle.lineTo(self.p2)
            self.triangle.lineTo(self.p3)
            self.triangle.lineTo(self.p1)
            self.gradientP1.setColorAt(0, c)
            self.gradientP1.setStart(self.p1)
            self.gradientP1.setFinalStop(self.p2)
            self.gradientP3.setStart(self.p3)
            self.gradientP3.setFinalStop((self.p1 + self.p2) * 0.5)
        elif self.options.colorSelector == "square":
            self.p1.setX(
                math.cos(math.pi * 1.0 / 4.0 + a) * radius
                + self.circleCenter.x()
            )
            self.p1.setY(
                math.sin(math.pi * 1.0 / 4.0 + a) * radius
                + self.circleCenter.y()
            )
            self.p2.setX(
                math.cos(math.pi * 3.0 / 4.0 + a) * radius
                + self.circleCenter.x()
            )
            self.p2.setY(
                math.sin(math.pi * 3.0 / 4.0 + a) * radius
                + self.circleCenter.y()
            )
            self.p3.setX(
                math.cos(math.pi * 5.0 / 4.0 + a) * radius
                + self.circleCenter.x()
            )
            self.p3.setY(
                math.sin(math.pi * 5.0 / 4.0 + a) * radius
                + self.circleCenter.y()
            )
            self.p4.setX(
                math.cos(math.pi * 7.0 / 4.0 + a) * radius
                + self.circleCenter.x()
            )
            self.p4.setY(
                math.sin(math.pi * 7.0 / 4.0 + a) * radius
                + self.circleCenter.y()
            )
            self.triangle.moveTo(self.p1)
            self.triangle.lineTo(self.p2)
            self.triangle.lineTo(self.p3)
            self.triangle.lineTo(self.p4)
            self.gradientP1.setColorAt(0, c)
            self.gradientP1.setStart(self.p1)
            self.gradientP1.setFinalStop(self.p2)
            self.gradientP3.setStart(self.p3)
            self.gradientP3.setFinalStop(self.p2)

    def resize(self, width, height):
        self._rect.setWidth(width)
        self._rect.setHeight(height)

        w = self.options.attributeFont.pixelSize()
        self.colorPicker.prepareGeometryChange()
        self.colorPicker.setPos(
            width - self.colorPicker.boundingRect().width(), 30
        )
        self.colorPicker.update()

        self.vectorItem.prepareGeometryChange()
        self.vectorItem.resize(width - 2 * self.margin, w + 4)
        self.vectorItem.setPos(self.margin, height - w - 4 - self.margin)
        self.vectorItem.updateGeometry()

        self.height = w + self.margin
        self.colorRect = QRectF(0, 0, w * 2, w + self.margin - 4)
        self.buttonRect = QRectF(width - w, 0, w, w)
        self.path = QPainterPath()
        c = self.buttonRect.center()
        self.path.moveTo(c.x(), c.y() + self.buttonRect.height() / 2 * 0.6)
        self.path.lineTo(
            c.x() - w / 2 * 0.6, c.y() - self.buttonRect.height() / 2 * 0.4
        )
        self.path.lineTo(
            c.x() + w / 2 * 0.6, c.y() - self.buttonRect.height() / 2 * 0.4
        )
        self.path.lineTo(c.x(), c.y() + self.buttonRect.height() / 2 * 0.6)

        h = height - w - 50
        r = QRectF(self.margin, w + self.margin, h, h)
        self.valueRect = QRectF(
            h + self.margin * 2, w + self.margin * 1.5, w, h
        )
        g = QLinearGradient()
        g.setColorAt(0, QColor(255, 255, 255))
        g.setColorAt(1, QColor(0, 0, 0))
        g.setStart(self.valueRect.topLeft())
        g.setFinalStop(self.valueRect.bottomLeft())
        self.valueBrush = QBrush(g)
        self.opacityRect = self.valueRect.translated(
            self.valueRect.width() + self.margin, 0
        )
        g.setColorAt(1, QColor(255, 255, 255, 0))
        g.setStart(self.opacityRect.topLeft())
        g.setFinalStop(self.opacityRect.bottomLeft())
        self.opacityBrush = QBrush(g)

        self.circleCenter = r.center()
        self.circleRadius = h / 2
        self.circle = QPainterPath()
        self.circle.addEllipse(r)
        self.updateTriangle()
        self.updatePoint()
        s = QPainterPath()
        p = 0.15
        r1 = QRectF(
            r.left() + r.width() * p,
            r.top() + r.height() * p,
            r.width() * (1 - 2 * p),
            h * (1 - 2 * p),
        )
        s.addEllipse(r1)
        self.circle = self.circle.subtracted(s)
        self.gradientHSV.setCenter(self.circleCenter)
        # self.gradientC = QRadialGradient(self.circleCenter,self.circleRadius)
        # self.gradientC.setColorAt(0,QColor(255,255,255,255))
        # self.gradientC.setColorAt(1,QColor(255,255,255,0))
        QtWidgets.QGraphicsWidget.resize(self, width, height)

    def paint(self, painter, option, widget=None):
        # print self,'paint'
        # global Z
        # Z+=1
        # if Z>1000:

        #    sys.settrace(traceit)
        painter.setBrush(self.darkBrush)
        painter.setPen(self.pen)
        painter.drawRoundedRect(
            self._rect, self.options.nodeRadius, self.options.nodeRadius
        )
        painter.drawRoundedRect(
            self.buttonRect, self.options.nodeRadius, self.options.nodeRadius
        )
        painter.drawPath(self.path)
        if self.attr["type"] == "RGBA":
            painter.setBrush(self.opacityPixmap)
            painter.drawRoundedRect(
                self.colorRect, self.options.nodeRadius, self.options.nodeRadius
            )
        c = QColor()
        c.setHsvF(self.hue, self.sat, self.val, self.alpha)
        painter.setBrush(QBrush(c))
        painter.drawRoundedRect(
            self.colorRect, self.options.nodeRadius, self.options.nodeRadius
        )

        if self.expanded:
            p = QPainterPath()
            p.addEllipse(-4, -4, 8, 8)
            if self.attr["type"] == "RGBA":
                painter.setPen(QPen(0))
                painter.setBrush(self.opacityPixmap)
                painter.drawRoundedRect(
                    self.opacityRect,
                    self.options.nodeRadius,
                    self.options.nodeRadius,
                )
                painter.setPen(self.pen)
                painter.setBrush(self.opacityBrush)
                painter.drawRoundedRect(
                    self.opacityRect,
                    self.options.nodeRadius,
                    self.options.nodeRadius,
                )
                painter.setBrush(self.darkBrush)
                painter.drawPath(p.translated(self.opacityPoint))

            painter.setBrush(self.valueBrush)
            painter.drawRoundedRect(
                self.valueRect, self.options.nodeRadius, self.options.nodeRadius
            )

            painter.setPen(QPen(0))
            painter.setBrush(QBrush(self.gradientHSV))
            painter.drawPath(self.circle)
            # painter.setBrush(QBrush(self.gradientC))
            # painter.drawPath(self.circle)

            # painter.drawImage(0,0, self.triangleImage)
            painter.setBrush(QBrush(self.gradientP1))
            painter.drawPath(self.triangle)
            painter.setBrush(QBrush(self.gradientP3))
            painter.drawPath(self.triangle)

            c = int(255 - 255 * self.val)
            painter.setPen(QPen(QColor(c, c, c)))
            painter.setBrush(self.darkBrush)
            painter.drawPath(p.translated(self.point))
            painter.drawPath(p.translated(self.valuePoint))
            painter.setPen(self.pen)
            painter.drawPath(p.translated(self.circlePoint))
        painter.setFont(self.options.attributeFont)
        painter.drawText(
            self.colorRect.right() + 5,
            self.options.attributeFont.pixelSize(),
            self.label,
        )

    def mousePressEvent(self, event):
        if event is None or event.button() != Qt.MouseButton.LeftButton:
            return
        event.ignore()
        if self.buttonRect.contains(event.pos()):
            if not self.expanded:
                self.expanded = True
                self.vectorItem.setVisible(True)
                self.colorPicker.setVisible(True)
                self.prepareGeometryChange()
                self.resize(self._rect.width(), 200)
                self.updateGeometry()
                self.update()
                # self.setAcceptHoverEvents(True)
            else:
                self.expanded = False
                self.vectorItem.setVisible(False)
                self.colorPicker.setVisible(False)
                self.prepareGeometryChange()
                self.resize(self._rect.width(), self.height)
                self.updateGeometry()
                self.update()
            return
        scene = self.scene()
        drag_parent = scene.parent() if scene else None
        if self.valueRect.contains(event.pos()):
            drag = QDrag(drag_parent)
            mime = NodeMimeData()
            mime.setData("rgb/value", QByteArray())
            mime.setObject(self)
            drag.setMimeData(mime)
            drag.exec(Qt.DropAction.MoveAction)
            return
        if self.attr["type"] == "RGBA" and self.opacityRect.contains(
            event.pos()
        ):
            drag = QDrag(drag_parent)
            mime = NodeMimeData()
            mime.setData("rgb/opacity", QByteArray())
            mime.setObject(self)
            drag.setMimeData(mime)
            drag.exec(Qt.DropAction.MoveAction)
            return
        p = event.pos() - self.circleCenter
        dist = length(p)
        if dist <= self.circleRadius and dist >= self.circleRadius * 0.7:
            drag = QDrag(drag_parent)
            mime = NodeMimeData()
            mime.setData("rgb/drag", QByteArray())
            mime.setObject(self)
            drag.setMimeData(mime)
            drag.exec(Qt.DropAction.MoveAction)
        elif dist < self.circleRadius * 0.7:
            drag = QDrag(drag_parent)
            mime = NodeMimeData()
            mime.setData("rgb/point", QByteArray())
            mime.setObject(self)
            drag.setMimeData(mime)
            drag.exec(Qt.DropAction.MoveAction)

    def wheelEvent(self, event):
        if event is None:
            return
        if self.expanded:
            p = event.pos() - self.circleCenter
            dist = length(p)
            if dist <= self.circleRadius * 1.2:
                delta = getattr(event, "angleDelta", None)
                y = delta.y() if delta is not None else 0
                self.setHue(self.hue + 0.0001 * y)
                self.updateValue()
                self.updateAttribute()
                return
        QtWidgets.QGraphicsWidget.wheelEvent(self, event)

    def dragMoveEvent(self, event):
        mime = event.mimeData()
        if mime.hasFormat("rgb/drag") and mime.getObject() == self:
            p = self.mapFromScene(event.scenePos()) - self.circleCenter
            angle = math.atan2(-p.y(), p.x())
            self.setHue(angle / math.pi * 0.5)
            self.updateTriangle()
            self.updatePoint()
            self.update()
        elif (
            mime.hasFormat("rgb/point")
            and getBarycentric is not None
            and Vector is not None
        ):
            p = self.mapFromScene(event.scenePos())
            a = Vector(self.p1.x(), self.p1.y(), 0.0)
            b = Vector(self.p2.x(), self.p2.y(), 0.0)
            c = Vector(self.p3.x(), self.p3.y(), 0.0)
            # (u,v,w) = getBarycentric(p,self.p1,self.p2,self.p3)
            vec = getBarycentric(Vector(p.x(), p.y(), 0.0), a, b, c)
            u = vec[0]
            v = vec[1]
            w = vec[2]
            if u > 0 and v > 0 and w > 0:
                self.point = p
                self.fromPoint()
                self.updatePoint()
                self.update()
        elif mime.hasFormat("rgb/value"):
            p = self.mapFromScene(event.scenePos())
            self.val = max(
                0.0,
                min(
                    1.0,
                    lerp_2d_list(
                        (self.valueRect.bottom(), self.valueRect.top()),
                        (0.0, 1.0),
                        p.y(),
                    ),
                ),
            )
            self.updatePoint()
            self.update()
        elif mime.hasFormat("rgb/opacity"):
            p = self.mapFromScene(event.scenePos())
            self.alpha = max(
                0.0,
                min(
                    1.0,
                    lerp_2d_list(
                        (self.opacityRect.bottom(), self.opacityRect.top()),
                        (0.0, 1.0),
                        p.y(),
                    ),
                ),
            )
            self.updatePoint()
            self.update()
        # NodeAttr.dragMoveEvent(self,event)

    def dropEvent(self, event):
        NodeAttr.dropEvent(self, event)
        # if event.isAccepted():
        #    return
        self.updateValue()
        self.updateAttribute()
