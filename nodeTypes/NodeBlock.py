from qtpy.QtGui import QPainterPath, QTransform
from qtpy.QtCore import Qt, QRectF
from qtpy.QtWidgets import QFileDialog, QMenu, QWidget

from .Node import Node
from nodeParts.Parts import NodeResize, NodeInput
from htmlEditor import HtmlEditor
import nodeUtils


class NodeBlock(Node):
    def __init__(self, d, dialog=None):
        super().__init__(d, dialog)
        self.path = QPainterPath()
        self.path.addRect(0, 0, 1, 1)

    def addExtraControls(self):
        self.resizeItem = NodeResize(self, rect=QRectF(-12, -12, 12, 12))
        self.connector = NodeInput(self)
        self.connector.setRect(QRectF(-5, -5, 10, 10))

    def shape(self):
        t = QTransform()
        t.scale(self._rect.width(), self._rect.height())
        return t.map(self.path)

    def setRect(self, rect):

        super().setRect(rect)
        if self.connector is not None:
            self.connector.setPos(self._rect.center().x(), self._rect.bottom())
        name_item = self.nameItem
        if name_item is not None:
            name_item.setPos(
                rect.center().x() - name_item.boundingRect().width() * 0.5,
                rect.center().y() - name_item.boundingRect().height() * 0.5,
            )
        icon_item = self.iconItem
        if icon_item is not None and name_item is not None:
            icon_item.prepareGeometryChange()
            icon_item.setPos(
                name_item.pos().x() - name_item.boundingRect().width() * 0.5,
                name_item.pos().y(),
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

        setRectAction = menu.addAction("Shape Rectangle")
        setCircleAction = menu.addAction("Shape Circle")
        setDiamondAction = menu.addAction("Shape Diamond")

        action = menu.exec(event.screenPos())
        if action == setIconAction:
            from nodeCommand import CommandSetNodeAttribute

            filename, _ = QFileDialog.getOpenFileName(
                self.dialog, "Open File", "", "Icon Files (*.jpg *.png *.ico)"
            )
            if filename:
                nodeUtils.options.undoStack.push(
                    CommandSetNodeAttribute([self], {"icon": filename})
                )
        elif action == clearIconAction and self.icon is not None:
            from nodeCommand import CommandSetNodeAttribute

            nodeUtils.options.undoStack.push(
                CommandSetNodeAttribute([self], {"icon": None})
            )
        elif action == editNameAction and self.nameItem is not None:
            self.nameItem.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextEditorInteraction
            )
            self.nameItem.setFocus(Qt.FocusReason.MouseFocusReason)

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

            def on_keywords_edit(text):
                from nodeCommand import CommandSetNodeAttribute

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
                    "func": on_keywords_edit,
                    "type": "text",
                },
            )
            editor.show()

    def paint(self, painter, option, widget=None):
        painter.setBrush(self.brush)
        painter.setPen(self.pen)
        t = QTransform()
        t.scale(self._rect.width(), self._rect.height())

        painter.drawPath(t.map(self.path))
