from qtpy.QtGui import QColor, QPen, QBrush, QLinearGradient, QDrag
from qtpy.QtCore import Qt, QRectF, QPointF, QTimer, QByteArray, QSizeF
from qtpy import QtWidgets

import nodeUtils
from nodeUtils import NodeMimeData
from nodeParts.Parts import TitleItem, NodeInput, NodeResize, DropDown
from htmlEditor import HtmlEditor
from nodeCommand import (
    CommandMoveAnimNode,
    CommandSetNodeAttribute,
    CommandCreateConnection,
)


class Node(QtWidgets.QGraphicsWidget):
    def __init__(self, d, dialog=None):
        QtWidgets.QGraphicsWidget.__init__(self)
        self.dialog = dialog

        self.init(d)
        self.nameItem = TitleItem(self.display_name, self, "display_name")

        self.pen = QPen(Qt.black, 1.5)
        self.addExtraControls()
        self.setRect(self.rect)
        self.timer = QTimer()
        self.timer.setInterval(QtWidgets.QApplication.startDragTime())
        self.timer.setSingleShot(True)
        self.mouseReleased = False
        self.timer.timeout.connect(self.onTimer)

    def addExtraControls(self):
        self.connector = NodeInput(self)
        self.connector.setRect(QRectF(-5, -5, 10, 10))
        self.resizeItem = NodeResize(self, rect=QRectF(-12, -12, 12, 12))
        self.resizeItem.hide()
        self.dropdown = DropDown(
            self, nodeUtils.options, "resources/icons/dropdown_arrows.png"
        )
        if self.collapsed is True:
            self.dropdown.setState(True)

    def init(self, d):

        self.resizeItem = None
        self.connector = None
        self.dropdown = None
        self.shadow = None
        self.urlItem = None
        self.htmlItem = None
        self.nameItem = None
        self.iconItem = None
        self.name = ""
        self.display_name = ""
        self.keywords = ""
        self.connections = []
        self.childs = []
        self.collapsed_childs = []
        self.collapsed = d.get("collapsed", False)
        self.setSelected(False)
        width = d.get("width", 90)
        height = d.get("height", 24)
        self.rect = d.get("rect", QRectF(0, 0, width, height))

        self.setTransformOriginPoint(self.rect.center())
        if "rot" in d.keys():
            self.setRotation(d["rot"])

        self.html = ""

        if self.dialog.showShadowsAction.isChecked():
            self.addShadow()

        self.setColor(QColor(d.get("rgb", "#fafafa")))

        self.selected = False
        self.setZValue(1)

        self.old_pos = QPointF()

        self.icon = d.get("icon", None)

        if self.icon:
            icon = nodeUtils.options.getIcon(self.icon)
            if icon:
                self.iconItem = QtWidgets.QGraphicsPixmapItem(icon, self)
                self.iconItem.setPos(5, 5)

        # for i in range(random.randint(0, 2)):
        # self.addInput("input %d" % i)

        self.fromDict(d)
        self.setAcceptDrops(True)
        self.setAcceptHoverEvents(True)

    def addShadow(self):
        self.shadow = QtWidgets.QGraphicsDropShadowEffect()
        self.shadow.setOffset(4, 4)
        self.shadow.setBlurRadius(8)
        self.setGraphicsEffect(self.shadow)

    def setCollapsed(self, state):
        for c in self.childs:
            if c.__class__ == Node or c.__class__ == Node:
                c.setCollapsed(False)
                # c.dropdown.setState(True)
                c.setVisible(state)
                for con in c.connections:
                    if con.parent != self:
                        con.setVisible(False)
                    else:
                        con.setVisible(state)
            else:  # c.__class__==BookmarkNode:
                c.setVisible(state)
                for con in c.connections:
                    con.setVisible(state)
        self.collapsed = not state
        if state is True:
            # self.alignChilds()
            nodeUtils.options.setSelection([self])

    def alignChilds(self):
        x = self.pos().x() + self.boundingRect().width() + 50
        y = 0

        def getKey(item):
            return item.pos().y()

        self.childs = sorted(self.childs, key=getKey)
        for child in self.childs:
            y += child.boundingRect().height() + 5
        y = self.pos().y() + self.boundingRect().center().y() - y * 0.5
        positions = []
        for child in self.childs:
            positions += [QPointF(x, y)]
            child.old_pos = child.pos()
            y += child.boundingRect().height() + 5
        nodeUtils.options.undoStack.push(
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
        # else:
        #     print 'WARNING: id is empty'
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
                icon = nodeUtils.options.getIcon(self.icon)
                if self.scene() and self.iconItem:
                    self.scene().removeItem(self.iconItem)
                if icon:
                    self.iconItem = QtWidgets.QGraphicsPixmapItem(icon, self)
                    self.iconItem.setPos(5, 5)
            else:
                z = self.iconItem
                self.iconItem = None
                z.scene().removeItem(z)

    def toDict(self):
        res = {"name": self.name}
        res["id"] = self.id
        res["display_name"] = self.display_name
        res["collapsed"] = self.collapsed
        res["keywords"] = self.keywords
        res["posx"] = round(self.pos().x(), 2)
        res["posy"] = round(self.pos().y(), 2)
        res["width"] = round(self.rect.width(), 2)
        res["height"] = round(self.rect.height(), 2)
        res["rgb"] = str(self.color.name())
        if self.rotation() != 0:
            res["rot"] = self.rotation()
        res["type"] = self.__class__.__name__
        if self.icon:
            res["icon"] = self.icon
        return res

    def setPos(self, *args):
        QtWidgets.QGraphicsWidget.setPos(self, *args)
        for c in self.connections:
            c.prepareGeometryChange()
            c.updatePath()
            c.update()
            # c.update()

    def setColor(self, c):
        self.color = QColor(c.red(), c.green(), c.blue(), 50)
        if self.shadow:
            c = c.darker(150)
            c.setAlpha(150)
            self.shadow.setColor(c)
        gradient = QLinearGradient(self.rect.topLeft(), self.rect.bottomRight())
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

    def sizeHint(self, which, constraint):
        if which == Qt.MinimumSize or which == Qt.PreferredSize:
            return QSizeF(self.rect.width(), self.rect.height())
        # elif which==Qt.MaximumSize:
        #     return QSizeF(1000,1000)
        return constraint

    def setRect(self, rect):

        for c in self.connections:
            c.prepareGeometryChange()
            c.updatePath()
            c.update()
        # self.minmaxRect = QRectF(nodeUtils.options.iconSize, nodeUtils.options.iconSize, 500, 1000)
        # rect.setWidth(rect.width())
        # rect.setHeight(rect.height())
        self.rect = rect
        # self.rect.setWidth(max(self.minmaxRect.left(), min(self.rect.width(), self.minmaxRect.width())))
        # self.rect.setHeight(max(self.minmaxRect.top(), min(self.rect.height(), self.minmaxRect.height())))

        if self.connector:
            self.connector.prepareGeometryChange()
            # self.connector.setPos(self.rect.center().x(),self.rect.bottom())
            self.connector.setPos(self.rect.right(), self.rect.center().y())
        if self.resizeItem:
            self.resizeItem.prepareGeometryChange()
            self.resizeItem.setPos(
                self.rect.right() - self.resizeItem.boundingRect().width() / 2,
                self.rect.bottom()
                - self.resizeItem.boundingRect().height() / 2,
            )
        if self.nameItem:
            self.nameItem.prepareGeometryChange()
            self.nameItem.setPos(
                self.rect.center().x()
                - self.nameItem.boundingRect().width() * 0.5,
                0,
            )
        if self.dropdown:
            self.dropdown.setPos(
                self.rect.right() - self.dropdown.boundingRect().width() - 8, 3
            )
        self.setColor(self.color)
        if self.urlItem:
            icon_size = nodeUtils.options.iconSize
            self.urlItem.prepareGeometryChange()
            if (
                self.dialog.showUrlsAction.isChecked()
                and not self.dialog.showNamesAction.isChecked()
                and self.dialog.showIconsAction.isChecked()
            ):
                self.urlItem.setPos(icon_size + 8, icon_size / 4)
            else:
                self.urlItem.setPos(
                    0,
                    self.dialog.showIconsAction.isChecked()
                    and icon_size
                    or 0 + self.dialog.showNamesAction.isChecked()
                    and icon_size
                    or 0,
                )

    def setSelected(self, state):
        if self.shadow:
            self.shadow.updateBoundingRect()
        self.selected = state
        if state:
            if self.resizeItem:
                self.resizeItem.show()
            self.setZValue(2)
            self.pen = QPen(QColor(250, 140, 10), 1.5)
        else:
            if self.resizeItem:
                self.resizeItem.hide()
            self.setZValue(1)
            if self.dialog.outline:
                self.pen = QPen(Qt.black, 1.5)
            else:
                self.pen = QPen(QColor(0, 0, 0, 0), 0)

    def mouseDoubleClickEvent(self, event):
        def get_childs(node):
            childs = node.childs
            for c in childs:
                childs += get_childs(c)
            return childs

        # sel = list(set([self] + get_childs(self)))

        # nodeUtils.options.setSelection(self.childs)
        self.alignChilds()
        QtWidgets.QGraphicsWidget.mouseDoubleClickEvent(self, event)

    def onTimer(self):
        if not self.mouseReleased:
            # print "skipTimer"
            return
        # print "onTimer"
        drag = QDrag(self.dialog)
        mime = NodeMimeData()
        mime.setObject(self)
        mime.setData("node/move", QByteArray())
        mime.setOrigin(self.mouseReleased)
        drag.setMimeData(mime)
        drag.exec_(Qt.MoveAction)

    def mouseReleaseEvent(self, event):
        self.mouseReleased = None

    def mousePressEvent(self, event):
        # print self.id,self.name
        # print self.color.name()

        if event.button() != Qt.LeftButton:
            event.ignore()
            return

        # Selection
        if QtWidgets.QApplication.keyboardModifiers() & Qt.ControlModifier:
            if self.selected:
                nodeUtils.options.removeSelection(self)
            else:
                nodeUtils.options.selected += [self]
                self.setSelected(True)
            return
        else:
            if not self.selected:
                nodeUtils.options.setSelection([self])

        if not self.timer.isActive():
            self.mouseReleased = self.mapToScene(
                event.pos().x(), event.pos().y()
            )
            self.timer.start()

    def hoverEnterEvent(self, event):
        self.setToolTip(self.name)

    def hoverLeaveEvent(self, event):
        self.setToolTip("")

    def dropEvent(self, event):
        mime = event.mimeData()
        if mime.hasFormat("node/connect") and mime.getObject() != self:
            # self.dialog.ids+=1
            d = {
                "name": "Connection",
                "parent": mime.getObject().id,
                "child": self.id,
            }
            nodeUtils.options.undoStack.push(
                CommandCreateConnection(self.scene(), d)
            )

    def contextMenuEvent(self, event):
        menu = QtWidgets.QMenu(self.scene().parent())
        setIconAction = menu.addAction("Set icon")
        clearIconAction = menu.addAction("Clear icon")
        editNameAction = menu.addAction("Edit title")
        editKeywordsAction = menu.addAction("Edit keywords")
        action = menu.exec_(event.screenPos())
        if action == setIconAction:
            f, mask = QtWidgets.QFileDialog.getOpenFileName(
                self.dialog, "Open File", "", "Icon Files (*.jpg *.png *.ico)"
            )
            if f:
                print(f)
                nodeUtils.options.undoStack.push(
                    CommandSetNodeAttribute([self], {"icon": f})
                )
        elif action == clearIconAction and self.icon is not None:
            nodeUtils.options.undoStack.push(
                CommandSetNodeAttribute([self], {"icon": None})
            )
        elif action == editNameAction:
            self.nameItem.setTextInteractionFlags(Qt.TextEditorInteraction)
            self.nameItem.setFocus(Qt.MouseFocusReason)
        elif action == editKeywordsAction:

            def f(text):
                nodeUtils.options.undoStack.push(
                    CommandSetNodeAttribute(
                        [self], {"keywords": "%s" % text.toPlainText()}
                    )
                )

            editor = HtmlEditor(
                self.dialog,
                {
                    "node": self,
                    "text": self.keywords,
                    "func": f,
                    "type": "text",
                },
            )
            editor.show()

    def boundingRect(self):
        return self.rect

    def resize(self, width, height):
        rect = QRectF(0, 0, width, height)
        self.setRect(rect)
        QtWidgets.QGraphicsWidget.resize(self, width, height)

    def paint(self, painter, option, widget=None):
        painter.setBrush(self.brush)
        painter.setPen(self.pen)
        painter.drawRoundedRect(
            self.rect,
            nodeUtils.options.nodeRadius,
            nodeUtils.options.nodeRadius,
        )
        r = QRectF(self.rect)
        r.adjust(1.5, 1.5, -1.5, -1.5)
        c = QColor(self.color)
        c.darker(80)
        painter.setPen(QPen(c, 1))
        painter.drawRoundedRect(
            r,
            nodeUtils.options.nodeRadius - 1,
            nodeUtils.options.nodeRadius - 1,
        )
