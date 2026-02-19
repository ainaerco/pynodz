import webbrowser
from qtpy.QtGui import QFont, QColor
from qtpy.QtCore import Qt, QRectF, QUrl, QFileInfo
from qtpy import QtWidgets
import nodeUtils
from nodeCommand import CommandSetNodeAttribute
from .Node import Node
from nodeParts.Parts import TitleItem, NodeResize
from htmlEditor import HtmlEditor

icon_size = 24
ICONS = {}


class NodeBookmark(Node):
    def __init__(self, d, dialog=None):
        super().__init__(d, dialog)

        self.url = d.get("url")
        self.urlItem = TitleItem(self.url or "", self, "url")
        font = QFont()
        font.setUnderline(True)
        self.urlItem.setFont(font)
        self.urlItem.setDefaultTextColor(QColor(25, 25, 210))

        if self.icon is None and self.url and self.dialog is not None:
            url = QUrl(self.url)
            fi = QFileInfo(url.toLocalFile())
            typ = self.dialog.systemIcons().type(fi)
            if typ != "Unknown":
                if typ in ICONS:
                    pix = ICONS[typ]
                else:
                    pix = (
                        self.dialog.systemIcons()
                        .icon(fi)
                        .pixmap(icon_size, icon_size)
                    )
                    if pix.height() > 16:
                        pix = pix.scaled(16, 16)
                    ICONS[typ] = pix

                self.icon = pix
                self.iconItem = QtWidgets.QGraphicsPixmapItem(pix, self)
                self.iconItem.setPos(5, 5)

        # Ensure height fits title row + small gap + URL row (avoid clipping)
        opts_icon_size = nodeUtils.options.iconSize
        min_height = opts_icon_size + 4 + 20  # title row + gap + url line
        if self._rect.height() < min_height:
            self._rect = QRectF(0, 0, self._rect.width(), min_height)
        self.setRect(self._rect)
        self.setFlag(
            QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemClipsChildrenToShape
        )

    def addExtraControls(self):
        self.resizeItem = NodeResize(self, rect=QRectF(-12, -12, 12, 12))
        self.resizeItem.hide()

    def setRect(self, rect):
        super().setRect(rect)
        if self.urlItem:
            icon_size = nodeUtils.options.iconSize
            # One title row + small gap (base Node uses 2*icon_size; we use less)
            url_gap = 4
            if self.dialog:
                show_icons = self.dialog.showIconsAction.isChecked()
                show_names = self.dialog.showNamesAction.isChecked()
                first_row = icon_size if (show_icons or show_names) else 0
            else:
                first_row = icon_size
            y = first_row + url_gap
            self.urlItem.prepareGeometryChange()
            self.urlItem.setPos(0, y)

    def fromDict(self, d):
        Node.fromDict(self, d)
        if "url" in d.keys():
            self.url = d["url"]
            if self.urlItem:
                self.urlItem.setPlainText(self.url)

    def toDict(self):
        res = Node.toDict(self)
        if self.url is not None:
            res["url"] = self.url
        return res

    def mouseDoubleClickEvent(self, event):
        if self.url:
            webbrowser.open(self.url)
        else:
            self.alignChilds()

    def contextMenuEvent(self, event):
        if event is None:
            return
        scene = self.scene()
        parent = scene.parent() if scene is not None else None
        menu = QtWidgets.QMenu(
            parent=parent if isinstance(parent, QtWidgets.QWidget) else None
        )
        setIconAction = menu.addAction("Set icon")
        editNameAction = menu.addAction("Edit title")
        editUrlAction = menu.addAction("Edit url")
        copyUrlAction = menu.addAction("Copy url")
        editKeywordsAction = menu.addAction("Edit keywords")
        action = menu.exec(event.screenPos())
        if action == setIconAction:
            filename, _ = QtWidgets.QFileDialog.getOpenFileName(
                self.dialog, "Open File", "", "Icon Files (*.jpg *.png *.ico)"
            )
            if filename:
                nodeUtils.options.undoStack.push(
                    CommandSetNodeAttribute([self], {"icon": filename})
                )
        elif action == editNameAction and self.nameItem is not None:
            self.nameItem.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextEditorInteraction
            )
            self.nameItem.setFocus(Qt.FocusReason.MouseFocusReason)
        elif action == editUrlAction and self.urlItem is not None:
            self.urlItem.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextEditorInteraction
            )
            self.urlItem.setFocus(Qt.FocusReason.MouseFocusReason)
        elif action == copyUrlAction and self.url is not None:
            clipboard = QtWidgets.QApplication.clipboard()
            if clipboard is not None:
                clipboard.setText(self.url)
        elif action == editKeywordsAction:

            def on_keywords_edit(text):
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
