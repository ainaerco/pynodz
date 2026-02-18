import webbrowser
from qtpy.QtGui import *
from qtpy.QtCore import *
from qtpy import QtWidgets
import nodeUtils
from nodeCommand import CommandSetNodeAttribute
from .Node import Node
from nodeParts.Parts import TitleItem, NodeResize
from htmlEditor import HtmlEditor

icon_size = 24


class BookmarkNode(Node):
    def __init__(self, d, dialog=None):
        Node.__init__(self, d, dialog)

        # self.nameItem = QGraphicsTextEditItem(self.name, self, 'name')
        self.url = d.get("url")
        self.urlItem = TitleItem(self.url, self, "url")
        font = QFont()
        font.setUnderline(True)
        self.urlItem.setFont(font)
        self.urlItem.setDefaultTextColor(QColor(25, 25, 210))

        if self.icon is None and self.url:
            url = QUrl(self.url)
            fi = QFileInfo(url.toLocalFile())
            typ = self.dialog.systemIcons().type(fi)
            global icons
            if typ != "Unknown":
                if icons.keys(typ):
                    pix = icons[typ]
                else:
                    pix = (
                        self.dialog.systemIcons()
                        .icon(fi)
                        .pixmap(icon_size, icon_size)
                    )
                    if pix.height() > 16:
                        pix = pix.scaled(16, 16)
                    icons[typ] = pix

                self.icon = pix
                self.iconItem = QtWidgets.QGraphicsPixmapItem(pix, self)
                self.iconItem.setPos(5, 5)

        self.setRect(self.rect)
        self.setFlag(QtWidgets.QGraphicsItem.ItemClipsChildrenToShape)

    def addExtraControls(self):
        self.resizeItem = NodeResize(self, rect=QRectF(-12, -12, 12, 12))
        self.resizeItem.hide()

    # def setRect(self, rect):
    #     minx = icon_size + 10
    #     miny = minx + ((self.dialog.showUrlsAction.isChecked() and self.dialog.showNamesAction.isChecked()) and 10 or 0)
    #     maxy = -miny
    #     minmaxRect = QRectF(minx, miny, 256, maxy)
    #     self.rect = rect
    #     self.rect.setWidth(max(minmaxRect.left(), min(self.rect.width(), minmaxRect.right())))
    #     self.rect.setHeight(max(minmaxRect.top(), min(self.rect.height(), minmaxRect.bottom())))

    #     self.nameItem.prepareGeometryChange()
    #     self.nameItem.setPos(self.icon and (self.dialog.showIconsAction.isChecked() and icon_size or -4) + 8 or 2,
    #                          icon_size / 4.0)
    #     if self.url:
    #         self.urlItem.prepareGeometryChange()
    #         if self.dialog.showUrlsAction.isChecked() and not self.dialog.showNamesAction.isChecked() and self.dialog.showIconsAction.isChecked():
    #             self.urlItem.setPos(icon_size + 8, icon_size / 4)
    #         else:
    #             self.urlItem.setPos(0,
    #                                 self.dialog.showIconsAction.isChecked() and icon_size or 0 + self.dialog.showNamesAction.isChecked() and icon_size or 0)
    #     if self.resize:
    #         self.resize.prepareGeometryChange()
    #         self.resize.setPos(self.rect.right(), self.rect.bottom())
    #     self.setColor(self.color)

    def fromDict(self, d):
        print("fromDict", d)
        Node.fromDict(self, d)
        if "url" in d.keys():
            self.url = d["url"]
            if self.urlItem:
                self.urlItem.setPlainText(self.url)

    def toDict(self):
        res = Node.toDict(self)
        if self.url is not None:
            res["url"] = self.url
        print("toDict", res)
        return res

    def mouseDoubleClickEvent(self, event):
        if self.url:
            webbrowser.open(self.url)
        else:
            self.alignChilds()

    def contextMenuEvent(self, event):
        menu = QtWidgets.QMenu(self.scene().parent())
        setIconAction = menu.addAction("Set icon")
        editNameAction = menu.addAction("Edit title")
        editUrlAction = menu.addAction("Edit url")
        copyUrlAction = menu.addAction("Copy url")
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
        elif action == editNameAction:
            self.nameItem.setTextInteractionFlags(Qt.TextEditorInteraction)
            self.nameItem.setFocus(Qt.MouseFocusReason)
        elif action == editUrlAction:
            self.urlItem.setTextInteractionFlags(Qt.TextEditorInteraction)
            self.urlItem.setFocus(Qt.MouseFocusReason)
        elif action == copyUrlAction:
            QtWidgets.QApplication.clipboard().setText(self.url)
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
