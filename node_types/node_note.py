from qtpy.QtCore import Qt, QRectF
from qtpy.QtWidgets import QMenu, QWidget

import node_utils
from html_editor import HtmlEditor
from .node import Node
from node_parts.parts import TitleItem, NodeResize


class NodeNote(Node):
    def __init__(self, d, dialog=None):
        super().__init__(d, dialog)
        self.html = d.get("html", None)
        self.htmlItem = TitleItem("", self, "html")
        doc = self.htmlItem.document()
        if doc:
            doc.setIndentWidth(20)
        self.htmlItem.setPos(0, node_utils.options.iconSize)
        if self.html:
            self.htmlItem.setHtml(self.html)

        self.setRect(self._rect)

    def addExtraControls(self):
        self.resizeItem = NodeResize(self, rect=QRectF(-12, -12, 12, 12))
        self.resizeItem.hide()

    def setRect(self, rect):
        self._rect = rect
        self._rect.setWidth(
            max(node_utils.options.iconSize, self._rect.width())
        )
        self._rect.setHeight(
            max(node_utils.options.iconSize, self._rect.height())
        )
        if self.htmlItem:
            self.htmlItem.setTextWidth(self._rect.width())
        if self.resizeItem:
            self.resizeItem.prepareGeometryChange()
            self.resizeItem.setPos(self._rect.right(), self._rect.bottom())
        self.setColor(self.color)

    def fromDict(self, d):
        Node.fromDict(self, d)
        if "html" in d.keys():
            self.html = d["html"]
            if self.htmlItem:
                self.htmlItem.setHtml(self.html)

    def toDict(self):
        res = Node.toDict(self)
        if self.html is not None:
            res["html"] = self.html
        return res

    def mouseDoubleClickEvent(self, event):
        def f(text):
            from node_command import CommandSetNodeAttribute

            node_utils.options.undoStack.push(
                CommandSetNodeAttribute([self], {"html": text.toHtml()})
            )

        editor = HtmlEditor(
            self.dialog,
            {"node": self, "text": self.html, "func": f, "type": "html"},
        )
        editor.show()

    def contextMenuEvent(self, event):
        if event is None:
            return
        scene = self.scene()
        parent = scene.parent() if scene is not None else None
        menu = QMenu(parent=parent if isinstance(parent, QWidget) else None)
        editNameAction = menu.addAction("Edit title")
        action = menu.exec(event.screenPos())
        if action == editNameAction and self.nameItem is not None:
            self.nameItem.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextEditorInteraction
            )
            self.nameItem.setFocus(Qt.FocusReason.MouseFocusReason)
