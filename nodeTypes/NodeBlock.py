from qtpy.QtGui import *
from qtpy.QtCore import *
from qtpy import QtWidgets

from .Node import Node
from nodeParts.Parts import NodeResize, NodeInput
from nodeCommand import CommandSetNodeAttribute
from htmlEditor import HtmlEditor
import nodeUtils


class NodeBlock(Node):
    def __init__(self, d, dialog=None):
        Node.__init__(self, d, dialog)
        self.path = QPainterPath()
        self.path.addRect(0, 0, 1, 1)

    def addExtraControls(self):
        self.resizeItem = NodeResize(self, rect=QRectF(-12, -12, 12, 12))
        self.connector = NodeInput(self)
        self.connector.setRect(QRectF(-5, -5, 10, 10))

    def shape(self):
        t = QTransform()
        t.scale(self.rect.width(), self.rect.height())
        return self.path * t

    def setRect(self, rect):

        Node.setRect(self, rect)
        # self.nameItem.prepareGeometryChange()
        if self.connector:
            self.connector.setPos(self.rect.center().x(), self.rect.bottom())
        if self.nameItem:
            self.nameItem.setPos(
                rect.center().x() - self.nameItem.boundingRect().width() * 0.5,
                rect.center().y() - self.nameItem.boundingRect().height() * 0.5,
            )
        if self.iconItem:
            self.iconItem.prepareGeometryChange()
            self.iconItem.setPos(
                self.nameItem.pos().x()
                - self.nameItem.boundingRect().width() * 0.5,
                self.nameItem.pos().y(),
            )

    def contextMenuEvent(self, event):
        menu = QtWidgets.QMenu(self.scene().parent())
        setIconAction = menu.addAction("Set icon")
        clearIconAction = menu.addAction("Clear icon")
        editNameAction = menu.addAction("Edit title")
        editKeywordsAction = menu.addAction("Edit keywords")

        setRectAction = menu.addAction("Shape Rectangle")
        setCircleAction = menu.addAction("Shape Circle")
        setDiamondAction = menu.addAction("Shape Diamond")

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

        elif action == setRectAction:
            self.path = QPainterPath()
            self.path.addRect(0, 0, 1, 1)
            self.update()
        elif action == setCircleAction:
            self.path = QPainterPath()
            self.path.addEllipse(0, 0, 1, 1)
            self.update()
        elif action == setDiamondAction:
            self.path = QPainterPath()
            self.path.moveTo(0, 0.5)
            self.path.lineTo(0.5, 1)
            self.path.lineTo(1, 0.5)
            self.path.lineTo(0.5, 0)
            self.path.lineTo(0, 0.5)
            self.update()

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

    def paint(self, painter, option, widget=None):
        painter.setBrush(self.brush)
        painter.setPen(self.pen)
        # painter.drawRoundedRect(self.rect, nodeUtils.options.nodeRadius, nodeUtils.options.nodeRadius)

        # c = QColor(self.color)
        # c.setRgb(min(255, c.red() * 0.8), min(255, c.green() * 0.8), min(255, c.blue() * 0.8))
        # painter.setPen(QPen(c, 1))
        t = QTransform()
        t.scale(self.rect.width(), self.rect.height())

        painter.drawPath(self.path * t)
        # painter.drawRoundedRect(r, nodeUtils.options.nodeRadius - 1, nodeUtils.options.nodeRadius - 1)
