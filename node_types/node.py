from __future__ import annotations

from typing import cast

from qtpy.QtGui import QColor, QPen, QBrush, QLinearGradient, QDrag
from qtpy.QtCore import Qt, QRectF, QPointF, QTimer, QByteArray, QSizeF
from qtpy.QtWidgets import (
    QApplication,
    QFileDialog,
    QGraphicsDropShadowEffect,
    QGraphicsPixmapItem,
    QGraphicsWidget,
    QMenu,
    QWidget,
)

import node_utils
from node_utils import NodeMimeData
from node_parts.parts import TitleItem, NodeInput, NodeResize, DropDown
from html_editor import HtmlEditor


class Node(QGraphicsWidget):
    def __init__(self, d, dialog=None):
        super().__init__()
        self.dialog = dialog

        self.init(d)
        self.nameItem = TitleItem(self.display_name, self, "display_name")

        self.pen = QPen(Qt.GlobalColor.black, 1.5)
        self.addExtraControls()
        self.setRect(self._rect)
        self.timer = QTimer()
        self.timer.setInterval(QApplication.startDragTime())
        self.timer.setSingleShot(True)
        self._mouseReleased = False
        self.timer.timeout.connect(self.onTimer)

    def addExtraControls(self):
        self.connector = NodeInput(self)
        self.connector.setRect(QRectF(-5, -5, 10, 10))
        self.resizeItem = NodeResize(self, rect=QRectF(-12, -12, 12, 12))
        self.resizeItem.hide()
        self.dropdown = DropDown(self, node_utils.options)
        if self.collapsed is True:
            self.dropdown.setState(True)

    def init(self, d):
        self.resizeItem = None
        self.connector = None
        self.dropdown = None
        self.shadow = None
        self.nameItem = None
        self.htmlItem = None
        self.iconItem = None
        self.name = ""
        self.id = d.get("id", "")
        self.display_name = ""
        self.keywords = ""
        self.connections = []
        self.childs = []
        self.collapsed_childs = []
        self.collapsed = d.get("collapsed", False)
        self.setSelected(False)
        width = d.get("width", 90)
        height = d.get("height", 24)
        self._rect = d.get("rect", QRectF(0, 0, width, height))

        self.setTransformOriginPoint(self._rect.center())
        if "rot" in d.keys():
            self.setRotation(d["rot"])

        self.html = ""

        if self.dialog and self.dialog.showShadowsAction.isChecked():
            self.addShadow()

        self.setColor(QColor(d.get("rgb", "#fafafa")))

        self._selected = False
        self.setZValue(1)

        self.old_pos = QPointF()

        self.icon = d.get("icon", None)

        if self.icon:
            icon = node_utils.options.get_icon(self.icon)
            if icon:
                self.iconItem = QGraphicsPixmapItem(icon, self)
                self.iconItem.setPos(5, 5)

        self.fromDict(d)
        self.setAcceptDrops(True)
        self.setAcceptHoverEvents(True)

    def addShadow(self):
        self.shadow = QGraphicsDropShadowEffect()
        self.shadow.setOffset(4, 4)
        self.shadow.setBlurRadius(8)
        self.setGraphicsEffect(self.shadow)

    def setCollapsed(self, collapsed: bool):
        for c in self.childs:
            if isinstance(c, Node):
                c.setCollapsed(False)
                c.setVisible(collapsed)
                for con in c.connections:
                    if con.parent_node != self:
                        con.setVisible(False)
                    else:
                        con.setVisible(collapsed)
            else:
                c.setVisible(collapsed)
                for con in c.connections:
                    con.setVisible(collapsed)
        self.collapsed = not collapsed
        if collapsed is True:
            node_utils.options.set_selection([self])

    def alignChilds(self):
        x = self.pos().x() + self._rect.width() + 50
        y = 0

        def getKey(item):
            return item.pos().y()

        self.childs = sorted(self.childs, key=getKey)
        for child in self.childs:
            y += child.boundingRect().height() + 5
        y = self.pos().y() + self._rect.center().y() - y * 0.5
        positions = []
        for child in self.childs:
            positions += [QPointF(x, y)]
            child.old_pos = child.pos()
            y += child.boundingRect().height() + 5
        from node_command import CommandMoveAnimNode

        node_utils.options.undoStack.push(
            CommandMoveAnimNode(self.childs, positions, 300, True)
        )

    def fromDict(self, d):
        if "width" in d.keys() and "height" in d.keys():
            width = d["width"]
            height = d["height"]
            rect = QRectF(0, 0, width, height)
            self.setRect(rect)
        elif "rect" in d.keys():
            rect = d["rect"]
            self.setRect(rect)
        if "keywords" in d.keys():
            self.keywords = d["keywords"]
        if "id" in d.keys():
            self.id = d["id"]
        if "rgb" in d.keys():
            self.setColor(QColor(d["rgb"]))
        if "name" in d.keys():
            self.name = d["name"]
        if "display_name" in d.keys():
            self.display_name = d["display_name"]
        elif not self.display_name:
            self.display_name = self.name.rstrip("0123456789")
        if self.nameItem:
            self.nameItem.setPlainText(self.display_name)
        if "rot" in d:
            self.prepareGeometryChange()
            self.setRotation(d["rot"])
        if "icon" in d.keys():
            self.icon = d["icon"]
            if self.icon is not None:
                icon = node_utils.options.get_icon(self.icon)
                scene = self.scene()
                if scene is not None and self.iconItem is not None:
                    scene.removeItem(self.iconItem)
                if icon:
                    self.iconItem = QGraphicsPixmapItem(icon, self)
                    self.iconItem.setPos(5, 5)
            else:
                z = self.iconItem
                self.iconItem = None
                scene = self.scene()
                if z is not None and scene is not None:
                    scene.removeItem(z)

    def toDict(self):
        res = {"name": self.name}
        res["id"] = self.id
        res["display_name"] = self.display_name
        res["collapsed"] = self.collapsed
        res["keywords"] = self.keywords
        res["posx"] = round(self.pos().x(), 2)
        res["posy"] = round(self.pos().y(), 2)
        res["width"] = round(self._rect.width(), 2)
        res["height"] = round(self._rect.height(), 2)
        res["rgb"] = str(self.color.name())
        if self.rotation() != 0:
            res["rot"] = self.rotation()
        res["type"] = type(self).__name__
        if self.icon:
            res["icon"] = self.icon
        return res

    def setPos(self, x: float, y: float) -> None:  # type: ignore[override]
        super().setPos(x, y)
        for c in self.connections:
            c.prepareGeometryChange()
            c.updatePath()
            c.update()

    def setColor(self, c):
        self.color = QColor(c.red(), c.green(), c.blue(), 50)
        if self.shadow:
            c = c.darker(150)
            c.setAlpha(150)
            self.shadow.setColor(c)
        gradient = QLinearGradient(
            self._rect.topLeft(), self._rect.bottomRight()
        )
        color = QColor()
        color.setHsv(
            self.color.hue(),
            max(0, self.color.saturation() - 60),
            self.color.value(),
            100,
        )
        gradient.setColorAt(0, self.color)
        gradient.setColorAt(1, color)
        self.brush = QBrush(gradient)
        self.update()

    def sizeHint(self, which, constraint=None):
        if (
            which == Qt.SizeHint.MinimumSize
            or which == Qt.SizeHint.PreferredSize
        ):
            return QSizeF(self._rect.width(), self._rect.height())
        return constraint

    def setRect(self, rect):
        w = max(rect.width(), node_utils.options.minNodeWidth)
        h = max(rect.height(), node_utils.options.minNodeHeight)
        if w != rect.width() or h != rect.height():
            rect = QRectF(rect.x(), rect.y(), w, h)
        rect_changed = rect != self._rect
        for c in self.connections:
            c.prepareGeometryChange()
            c.updatePath()
            c.update()
        self._rect = rect

        if self.connector:
            self.connector.prepareGeometryChange()
            self.connector.setPos(self._rect.right(), self._rect.center().y())
        if self.resizeItem:
            self.resizeItem.prepareGeometryChange()
            self.resizeItem.setPos(
                self._rect.right() - self.resizeItem.boundingRect().width() / 2,
                self._rect.bottom()
                - self.resizeItem.boundingRect().height() / 2,
            )
        if self.nameItem:
            self.nameItem.prepareGeometryChange()
            self.nameItem.setPos(
                self._rect.center().x()
                - self.nameItem.boundingRect().width() * 0.5,
                0,
            )
        if self.dropdown:
            self.dropdown.setPos(
                self._rect.right() - self.dropdown.boundingRect().width() - 8, 3
            )
        if rect_changed:
            self.setColor(self.color)

    def setSelected(self, selected: bool):
        if self.shadow:
            self.shadow.updateBoundingRect()
        self._selected = selected
        if selected:
            if self.resizeItem:
                self.resizeItem.show()
            self.setZValue(2)
            self.pen = QPen(QColor(250, 140, 10), 1.5)
        else:
            if self.resizeItem:
                self.resizeItem.hide()
            self.setZValue(1)
            if self.dialog and self.dialog.outline:
                self.pen = QPen(Qt.GlobalColor.black, 1.5)
            else:
                self.pen = QPen(QColor(0), 0)

    def mouseDoubleClickEvent(self, event):
        if event is None:
            return
        # Forward double-click to title so name can be edited when clicking on it
        if self.nameItem is not None and self.nameItem.isVisible():
            nameLocal = self.nameItem.mapFromParent(event.pos())
            if self.nameItem.boundingRect().contains(nameLocal):
                self.nameItem.mouseDoubleClickEvent(event)
                return

        def getChilds(node):
            childs = node.childs
            for c in childs:
                childs += getChilds(c)
            return childs

        self.alignChilds()
        super().mouseDoubleClickEvent(event)

    def onTimer(self):
        if self._mouseReleased is None:
            return
        drag = QDrag(self.dialog)
        mime = NodeMimeData()
        mime.setObject(self)
        mime.setData("node/move", QByteArray())
        mime.setOrigin(self._mouseReleased)
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.MoveAction)

    def mouseReleaseEvent(self, event):
        self._mouseReleased = None

    def mousePressEvent(self, event):
        if event is None:
            return
        if event.button() != Qt.MouseButton.LeftButton:
            event.ignore()
            return

        # Selection
        if (
            QApplication.keyboardModifiers()
            & Qt.KeyboardModifier.ControlModifier
        ):
            if self._selected:
                node_utils.options.remove_selection(self)
            else:
                node_utils.options.selected += [self]
                self.setSelected(True)
            return
        else:
            if not self._selected:
                node_utils.options.set_selection([self])

        if not self.timer.isActive() and event is not None:
            self._mouseReleased = self.mapToScene(
                event.pos().x(), event.pos().y()
            )
            self.timer.start()

    def hoverEnterEvent(self, event):
        self.setToolTip(self.name)

    def hoverLeaveEvent(self, event):
        self.setToolTip("")

    def dropEvent(self, event):
        if event is None:
            return
        mime = cast(NodeMimeData, event.mimeData())
        obj = mime.getObject() if mime is not None else None
        if (
            mime is not None
            and mime.hasFormat("node/connect")
            and obj is not None
            and obj != self
        ):
            d = {
                "name": "Connection",
                "parent": obj.id,
                "child": self.id,
            }
            scene = self.scene()
            if scene is not None:
                from node_command import CommandCreateConnection

                node_utils.options.undoStack.push(
                    CommandCreateConnection(scene, d)
                )

    def contextMenuEvent(self, event):
        if event is None:
            return
        scene = self.scene()
        parent = scene.parent() if scene is not None else None
        menu = QMenu(parent=parent if isinstance(parent, QWidget) else None)
        setIconAction = menu.addAction("Set icon")
        clearIconAction = menu.addAction("Clear icon")
        editNameAction = menu.addAction("Edit title")
        editKeywordsAction = menu.addAction("Edit keywords")
        action = menu.exec(event.screenPos())
        if action == setIconAction:
            from node_command import CommandSetNodeAttribute

            filename, _ = QFileDialog.getOpenFileName(
                self.dialog, "Open File", "", "Icon Files (*.jpg *.png *.ico)"
            )
            if filename:
                node_utils.options.undoStack.push(
                    CommandSetNodeAttribute([self], {"icon": filename})
                )
        elif action == clearIconAction and self.icon is not None:
            from node_command import CommandSetNodeAttribute

            node_utils.options.undoStack.push(
                CommandSetNodeAttribute([self], {"icon": None})
            )
        elif action == editNameAction and self.nameItem is not None:
            self.nameItem.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextEditorInteraction
            )
            self.nameItem.setFocus(Qt.FocusReason.MouseFocusReason)
        elif action == editKeywordsAction:

            def onKeywordsEdit(text):
                from node_command import CommandSetNodeAttribute

                node_utils.options.undoStack.push(
                    CommandSetNodeAttribute(
                        [self], {"keywords": "%s" % text.toPlainText()}
                    )
                )

            editor = HtmlEditor(
                self.dialog,
                {
                    "node": self,
                    "text": self.keywords,
                    "func": onKeywordsEdit,
                    "type": "text",
                },
            )
            editor.show()

    def resize(self, width: float, height: float) -> None:  # type: ignore[override]
        rect = QRectF(0, 0, width, height)
        self.setRect(rect)
        super().resize(width, height)

    def paint(self, painter, option, widget=None):
        if painter is None:
            return
        painter.setBrush(self.brush)
        painter.setPen(self.pen)
        painter.drawRoundedRect(
            self._rect,
            node_utils.options.nodeRadius,
            node_utils.options.nodeRadius,
        )
        r = QRectF(self._rect)
        r.adjust(1.5, 1.5, -1.5, -1.5)
        c = QColor(self.color)
        c.darker(80)
        painter.setPen(QPen(c, 1))
        painter.drawRoundedRect(
            r,
            node_utils.options.nodeRadius - 1,
            node_utils.options.nodeRadius - 1,
        )
