from qtpy.QtCore import Qt, QRectF
from qtpy.QtWidgets import QInputDialog
from qtpy import QtWidgets
from .Node import Node
from nodeParts.Parts import NodeInput
from nodeAttrs import (
    NodeAttrString,
    NodeAttrImage,
    NodeAttr,
    getAttrByType,
    NodePanel,
)
from copy import deepcopy

import nodeUtils
from htmlEditor import HtmlEditor
from nodeUtils import mergeDicts
from nodeCommand import CommandSetNodeAttribute, CommandCreateConnection


class NodeShader(Node):
    def __init__(self, d, dialog=None):
        Node.__init__(self, d, dialog)
        layout = QtWidgets.QGraphicsLinearLayout(Qt.Orientation.Vertical)
        layout.setSpacing(7)
        layout.setContentsMargins(23, 20, 7, 7)
        self.setLayout(layout)
        if (
            self.shader
            and self.shader in self.dialog.shaders.keys()
            and self.shader in nodeUtils.options.arnold.keys()
        ):
            if "_output" in nodeUtils.options.arnold[self.shader].keys():
                self.connector.setType(
                    nodeUtils.options.arnold[self.shader]["_output"]
                )
            shader = self.dialog.shaders[self.shader]
            for a in shader["attributes_order"]:
                attr = shader["attributes"][a]
                if (
                    attr["name"] in nodeUtils.options.arnold[self.shader].keys()
                    and "_pin"
                    in nodeUtils.options.arnold[self.shader][
                        attr["name"]
                    ].keys()
                ):
                    self.pinUnpin(
                        attr,
                        nodeUtils.options.arnold[self.shader][attr["name"]][
                            "_pin"
                        ],
                    )

    def addExtraControls(self):
        self.connector = NodeInput(self)
        self.connector.setRect(QRectF(-5, -5, 10, 10))

    def resize(self, width, height):
        rect = QRectF(0, 0, width, height)
        Node.setRect(self, rect)
        QtWidgets.QGraphicsWidget.resize(self, width, height)

    def updateGeometry(self):
        # self.prepareGeometryChange()
        layout = self.layout()
        margin = layout.spacing()
        (left, t, r, b) = layout.getContentsMargins()
        height = t
        width = self._rect.width()
        for i in range(layout.count()):
            item = layout.itemAt(i)
            height += item.rect.height() + margin
            width = item.rect.width() + left + r

        height += b
        self.resize(width, height)
        QtWidgets.QGraphicsWidget.updateGeometry(self)

    def init(self, d):
        Node.init(self, d)
        self.shader = d.get("shader", None)
        self.attributes = {}
        self.pinnedAttributes = {}
        # self.values = d.get('values', {})

    def fromDict(self, d):
        self.values = {}
        if "shader" in d.keys():
            self.shader = d["shader"]
        if "values" in d.keys():
            vs = d["values"]
            # print "fromDict",vs
            for key in vs.keys():
                self.values[key] = deepcopy(vs[key])
                if key not in self.attributes.keys():
                    continue
                self.attributes[key].value = vs[key]
                self.attributes[key].update()
                if key in self.pinnedAttributes.keys():
                    self.pinnedAttributes[key].value = vs[key]
                    self.pinnedAttributes[key].update()
        Node.fromDict(self, d)

    def toDict(self):
        res = Node.toDict(self)
        res["shader"] = self.shader
        res["values"] = dict(self.values)
        # print "toDict",res['values']
        return res

    def pinUnpin(self, attr, pinned):
        # print self.name,'pinUnpin'
        nodeUtils.options.arnold = dict(
            mergeDicts(
                nodeUtils.options.arnold,
                {self.shader: {attr["name"]: {"_pin": pinned}}},
            )
        )
        # nodeUtils.options.arnold.update({self.shader:{attr['name']:{'_pin':pinned}}})
        if attr["name"] in self.pinnedAttributes.keys():
            if not pinned:
                self.prepareGeometryChange()
                self.layout().removeItem(self.pinnedAttributes[attr["name"]])
                self.scene().removeItem(self.pinnedAttributes[attr["name"]])

                del self.pinnedAttributes[attr["name"]]
                # self.setRect(self.form.boundingRect())
                self.updateGeometry()
                return
            else:
                return
        elif not pinned:
            return

        item = self.addAttr(attr)
        self.pinnedAttributes[attr["name"]] = item
        item.prepareGeometryChange()
        item.resize(200, nodeUtils.options.attributeFont.pixelSize() + 4)
        self.layout().addItem(item)

        # self.setRect(self.form.boundingRect())
        self.updateGeometry()

    def updateAttribute(self, name, value):
        # if attr.value.__class__==list:
        v = {name: deepcopy(value)}
        # else:
        #    v = {attr.attr['name']: attr.value}
        print(v, "updateAttribute", name)
        nodeUtils.options.undoStack.push(
            CommandSetNodeAttribute([self], {"values": v})
        )

    def addAttr(self, attr):
        connectedAttrs = [
            x.attr for x in self.connections if x.child == self and x.attr
        ]
        clas = getAttrByType(attr["type"])
        if clas is None:
            clas = NodeAttr
        if self.shader == "image" and attr["name"] == "filename":
            clas = NodeAttrImage
        item = clas(self, nodeUtils.options, attr)

        if attr["name"] in self.values.keys():
            item.value = deepcopy(self.values[attr["name"]])
        else:
            self.values[attr["name"]] = deepcopy(item.value)
        self.attributes[attr["name"]] = item

        if connectedAttrs is not None and attr["name"] in connectedAttrs:
            item.setConnected(True)
        if (
            self.shader in nodeUtils.options.arnold.keys()
            and attr["name"] in nodeUtils.options.arnold[self.shader].keys()
            and "_pin"
            in nodeUtils.options.arnold[self.shader][attr["name"]].keys()
        ):
            item.pin.setState(
                nodeUtils.options.arnold[self.shader][attr["name"]]["_pin"]
            )
        if "help" in attr.keys():
            item.setToolTip(attr["help"])
        return item

    def setSelected(self, state):
        Node.setSelected(self, state)
        if not state:
            self.attributes = {}
            self.dialog.attrView.setSceneRect(QRectF())
            self.dialog.attrScene.clear()
            return
        if not (self.shader and self.shader in self.dialog.shaders.keys()):
            return

        shader = self.dialog.shaders[self.shader]
        self.dialog.attrView.setSceneRect(QRectF())
        self.dialog.attrScene.clear()
        self.dialog.attrView.setAlignment(Qt.AlignTop)
        layout = QtWidgets.QGraphicsLinearLayout(Qt.Vertical)
        layout.setSpacing(7)
        attr = {"name": self.name, "type": "STRING", "default": ""}
        nameItem = NodeAttrString(self, nodeUtils.options, attr)
        nameItem.resize(self.dialog.attrView.width() - 32, 16)
        layout.addItem(nameItem)

        if "help" in shader.keys() and shader["help"]:
            nameItem.setToolTip(shader["help"])
        height = nameItem.rect.height()

        if "pages" in shader.keys() and len(shader["pages"]) > 0:
            for pageName in shader["pages"].keys():
                pageItem = NodePanel(
                    self,
                    nodeUtils.options,
                    {
                        "name": "",
                        "label": pageName[len("page00__:") :],
                        "default": "",
                        "type": "",
                    },
                )

                pageLayout = QtWidgets.QGraphicsLinearLayout(
                    Qt.Orientation.Vertical
                )
                pageLayout.setSpacing(7)
                pageLayout.setContentsMargins(23, 20, 7, 7)

                for attrName in shader["pages"][pageName]:
                    attr = shader["attributes"][attrName]

                    item = self.addAttr(attr)
                    item.setVisible(False)
                    item.prepareGeometryChange()
                    item.resize(
                        100, nodeUtils.options.attributeFont.pixelSize() + 4
                    )
                    height += item.rect.height() + 7
                    pageLayout.addItem(item)

                pageItem.resize(
                    self.dialog.attrView.width() - 32,
                    nodeUtils.options.attributeFont.pixelSize() + 4,
                )
                pageItem.setLayout(pageLayout)
                # pageItem.setCollapsed(True)
                layout.addItem(pageItem)
        else:
            for a in shader["attributes_order"]:
                attr = shader["attributes"][a]
                item = self.addAttr(attr)
                item.prepareGeometryChange()
                item.resize(
                    self.dialog.attrView.width() - 32,
                    nodeUtils.options.attributeFont.pixelSize() + 4,
                )
                height += item.rect.height() + 7
                layout.addItem(item)

        form = QtWidgets.QGraphicsWidget()
        form.setLayout(layout)
        form.setPos(0, 0)
        self.dialog.attrScene.addItem(form)
        self.dialog.attrView.setSceneRect(
            0, 0, self.dialog.attrView.width(), height
        )

    def dropEvent(self, event):
        mime = event.mimeData()
        if mime.hasFormat("node/connect") and mime.getObject() != self:
            # self.dialog.ids+=1

            if mime.getObject().__class__ == Node:
                d = {
                    "name": "Connection",
                    "parent": mime.getObject().id,
                    "child": self.id,
                }
                nodeUtils.options.undoStack.push(
                    CommandCreateConnection(self.scene(), d)
                )
                return
            menu = QtWidgets.QMenu(self.scene().parent())
            shader = self.dialog.shaders[self.shader]
            types = ["RGB", "RGBA", "VECTOR", "POINT"]
            conns = [
                x["name"]
                for x in shader["attributes"].values()
                if x["type"] in types
            ]
            if len(conns) == 0:
                return
            for c in conns:
                menu.addAction(c)
            action = menu.exec(event.screenPos())
            if action is None:
                return
            # print action.text()
            d = {
                "name": "Connection",
                "parent": mime.getObject().id,
                "child": self.id,
                "attr": str(action.text()),
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
        setOutputAction = menu.addAction("Set output type")
        action = menu.exec(event.screenPos())
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
            self.nameItem.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextEditorInteraction
            )
            self.nameItem.setFocus(Qt.FocusReason.MouseFocusReason)
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
        elif action == setOutputAction:
            text = QInputDialog.getItem(
                self.dialog,
                "QInputDialog::getText()",
                "Set shader output type:",
                nodeUtils.options.typeColors.keys(),
            )
            if text[1]:
                nodeUtils.options.arnold = dict(
                    mergeDicts(
                        nodeUtils.options.arnold,
                        {self.shader: {"_output": str(text[0])}},
                    )
                )
                self.connector.setType(str(text[0]))
