import webbrowser
from qtpy.QtGui import QFont, QColor, QBrush, QPen
from qtpy.QtCore import Qt, QRectF, QUrl, QFileInfo
from qtpy.QtWidgets import (
    QApplication,
    QFileDialog,
    QGraphicsItem,
    QGraphicsPixmapItem,
    QGraphicsRectItem,
    QMenu,
    QWidget,
)
import node_utils
from .node import Node
from node_parts.parts import TitleItem, NodeResize
from html_editor import HtmlEditor

icon_size = 24
ICONS = {}


class UrlTitleItem(TitleItem):
    """TitleItem that does not become editable on mouse clicks (URL is read-only)."""

    def __init__(self, text, parent, attr, title=False):
        super().__init__(text, parent, attr, title)
        # Prevent focus on single click so no edit boundary/cursor appears
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsFocusable, False)

    def mouseDoubleClickEvent(self, event):
        # Do not enable text editing; let event propagate to parent to open URL
        event.ignore()


class NodeBookmark(Node):
    def __init__(self, d, dialog=None):
        super().__init__(d, dialog)

        self.url = d.get("url")
        self.urlItem = UrlTitleItem(self.url or "", self, "url")
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
                self.iconItem = QGraphicsPixmapItem(pix, self)
                self.iconItem.setPos(5, 5)

        # Ensure height fits title row + small gap + URL row (avoid clipping)
        opts_icon_size = node_utils.options.iconSize
        min_height = opts_icon_size + 4 + 20  # title row + gap + url line
        if self._rect.height() < min_height:
            self._rect = QRectF(0, 0, self._rect.width(), min_height)
        self.setRect(self._rect)
        # Apply Options menu visibility for new bookmarks
        if self.dialog:
            if self.urlItem:
                self.urlItem.setVisible(self.dialog.showUrlsAction.isChecked())
            if self.iconItem is not None:
                self.iconItem.setVisible(
                    self.dialog.showIconsAction.isChecked()
                )
            if self.nameItem is not None:
                self.nameItem.setVisible(
                    self.dialog.showNamesAction.isChecked()
                )
        # Clip only name/URL (and icon) to node shape; resize icon stays unclipped
        self._clipContainer = QGraphicsRectItem(self)
        self._clipContainer.setRect(
            0, 0, self._rect.width(), self._rect.height()
        )
        self._clipContainer.setPen(QPen(Qt.PenStyle.NoPen))
        self._clipContainer.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        self._clipContainer.setFlag(
            QGraphicsItem.GraphicsItemFlag.ItemClipsChildrenToShape
        )
        self._clipContainer.setZValue(-1)
        self._clipContainer.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self.nameItem.setParentItem(self._clipContainer)
        self.urlItem.setParentItem(self._clipContainer)
        if getattr(self, "iconItem", None) is not None:
            self.iconItem.setParentItem(self._clipContainer)

    def addExtraControls(self):
        self.resizeItem = NodeResize(self, rect=QRectF(-12, -12, 12, 12))
        self.resizeItem.hide()

    def setRect(self, rect):
        super().setRect(rect)
        clipContainer = getattr(self, "_clipContainer", None)
        if clipContainer is not None:
            clipContainer.setRect(0, 0, self._rect.width(), self._rect.height())
        icon_size = node_utils.options.iconSize
        show_icons = (
            self.dialog.showIconsAction.isChecked() if self.dialog else True
        )
        has_icon = getattr(self, "iconItem", None) is not None and show_icons
        # Left-aligned: text to the right of the icon (or at left edge if no icon)
        text_left = 5 + icon_size + 4 if has_icon else 5
        if self.nameItem:
            self.nameItem.prepareGeometryChange()
            self.nameItem.setPos(text_left, 0)
        urlItem = getattr(self, "urlItem", None)
        if urlItem:
            url_gap = 4
            if self.dialog:
                show_names = self.dialog.showNamesAction.isChecked()
                first_row = icon_size if (show_icons or show_names) else 0
            else:
                first_row = icon_size
            y = first_row + url_gap
            urlItem.prepareGeometryChange()
            urlItem.setPos(text_left, y)

    def fromDict(self, d):
        Node.fromDict(self, d)
        if "url" in d.keys():
            self.url = d["url"]
            urlItem = getattr(self, "urlItem", None)
            if urlItem:
                urlItem.setPlainText(self.url)

    def toDict(self):
        res = Node.toDict(self)
        if self.url is not None:
            res["url"] = self.url
        return res

    def mouseDoubleClickEvent(self, event):
        if self.nameItem and self.nameItem.isUnderMouse():
            super().mouseDoubleClickEvent(event)
            return
        if self.url:
            webbrowser.open(self.url)
        else:
            self.alignChilds()

    def contextMenuEvent(self, event):
        if event is None:
            return
        scene = self.scene()
        parent = scene.parent() if scene is not None else None
        menu = QMenu(parent=parent if isinstance(parent, QWidget) else None)
        setIconAction = menu.addAction("Set icon")
        editNameAction = menu.addAction("Edit title")
        copyUrlAction = menu.addAction("Copy url")
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
        elif action == editNameAction and self.nameItem is not None:
            self.nameItem.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextEditorInteraction
            )
            self.nameItem.setFocus(Qt.FocusReason.MouseFocusReason)
        elif action == copyUrlAction and self.url is not None:
            clipboard = QApplication.clipboard()
            if clipboard is not None:
                clipboard.setText(self.url)
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
