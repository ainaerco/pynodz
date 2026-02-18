from qtpy.QtCore import Qt, QRectF
from qtpy import QtWidgets

import nodeUtils
from htmlEditor import HtmlEditor
from .Node import Node
from nodeParts.Parts import TitleItem, NodeResize
from nodeCommand import CommandSetNodeAttribute


class NodeNote(Node):
    def __init__(self, d, dialog=None):
        Node.__init__(self, d, dialog)
        self.html = d.get("html", None)
        self.htmlItem = TitleItem("", self, "html")
        doc = self.htmlItem.document()
        if doc:
            doc.setIndentWidth(20)
        self.htmlItem.setPos(0, nodeUtils.options.iconSize)
        if self.html:
            self.htmlItem.setHtml(self.html)

        self.setRect(self._rect)
        # self.setFlag(QtWidgets.QGraphicsItem.ItemClipsChildrenToShape)

    def addExtraControls(self):
        self.resizeItem = NodeResize(self, rect=QRectF(-12, -12, 12, 12))
        self.resizeItem.hide()

    def setRect(self, rect):
        self._rect = rect
        self._rect.setWidth(max(nodeUtils.options.iconSize, self._rect.width()))
        self._rect.setHeight(
            max(nodeUtils.options.iconSize, self._rect.height())
        )
        # self.nameItem.prepareGeometryChange()
        # self.nameItem.setPos(self.icon and (Dialog.showIconsAction.isChecked() and nodeUtils.options.iconSize or -4)+8 or 2,nodeUtils.options.iconSize/4.0)
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
            nodeUtils.options.undoStack.push(
                CommandSetNodeAttribute([self], {"html": text.toHtml()})
            )

        editor = HtmlEditor(
            self.dialog,
            {"node": self, "text": self.html, "func": f, "type": "html"},
        )
        editor.show()

    def contextMenuEvent(self, event):
        menu = QtWidgets.QMenu(self.scene().parent())
        editNameAction = menu.addAction("Edit title")
        # editTextAction = menu.addAction("Edit url")
        # copyUrlAction = menu.addAction("Copy url")
        action = menu.exec(event.screenPos())
        if action == editNameAction:
            self.nameItem.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextEditorInteraction
            )
            self.nameItem.setFocus(Qt.FocusReason.MouseFocusReason)
