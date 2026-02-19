from __future__ import annotations

from typing import cast

from qtpy.QtCore import Qt, QRectF
from qtpy.QtWidgets import QInputDialog
from qtpy import QtWidgets
from .Node import Node
from nodeUtils import NodeMimeData
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
            self.dialog is not None
            and self.shader
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
        layout = self.layout()
        if layout is None:
            return
        margin = layout.spacing() if hasattr(layout, "spacing") else 0  # type: ignore[union-attr]
        (left, t, r, b) = layout.getContentsMargins()
        height = float(t) if t is not None else 0.0
        width = self._rect.width()
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item is None:
                continue
            geom = item.geometry()
            h = geom.height() if geom.height() is not None else 0.0
            w = geom.width() if geom.width() is not None else 0.0
            height += h + margin
            width = w + (left or 0) + (r or 0)

        height += b if b is not None else 0
        self.resize(width, height)
        QtWidgets.QGraphicsWidget.updateGeometry(self)

    def init(self, d):
        Node.init(self, d)
        self.shader = d.get("shader", None)
        self.attributes = {}
        self.pinnedAttributes = {}

    def fromDict(self, d):
        self.values = {}
        if "shader" in d.keys():
            self.shader = d["shader"]
        if "values" in d.keys():
            vs = d["values"]
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
        return res

    def pinUnpin(self, attr, pinned):
        nodeUtils.options.arnold = dict(
            mergeDicts(
                nodeUtils.options.arnold,
                {self.shader: {attr["name"]: {"_pin": pinned}}},
            )
        )
        if attr["name"] in self.pinnedAttributes.keys():
            if not pinned:
                self.prepareGeometryChange()
                ly = self.layout()
                if ly is not None:
                    ly.removeItem(self.pinnedAttributes[attr["name"]])  # type: ignore[union-attr]
                scene = self.scene()
                if scene is not None:
                    scene.removeItem(self.pinnedAttributes[attr["name"]])

                del self.pinnedAttributes[attr["name"]]
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
        ly = self.layout()
        if ly is not None:
            ly.addItem(item)  # type: ignore[union-attr]

        self.updateGeometry()

    def updateAttribute(self, name, value):
        v = {name: deepcopy(value)}
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

    def setSelected(self, selected: bool):
        Node.setSelected(self, selected)
        if self.dialog is None:
            return
        if not selected:
            self.attributes = {}
            self.dialog.attrView.setSceneRect(QRectF())
            self.dialog.attrScene.clear()
            return
        if not (self.shader and self.shader in self.dialog.shaders.keys()):
            return

        shader = self.dialog.shaders[self.shader]
        self.dialog.attrView.setSceneRect(QRectF())
        self.dialog.attrScene.clear()
        self.dialog.attrView.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout = QtWidgets.QGraphicsLinearLayout(Qt.Orientation.Vertical)
        layout.setSpacing(7)
        attr = {"name": self.name, "type": "STRING", "default": ""}
        nameItem = NodeAttrString(self, nodeUtils.options, attr)
        nameItem.resize(self.dialog.attrView.width() - 32, 16)
        layout.addItem(nameItem)

        if "help" in shader.keys() and shader["help"]:
            nameItem.setToolTip(shader["help"])
        height = nameItem.geometry().height()

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
                    height += item.geometry().height() + 7
                    pageLayout.addItem(item)

                pageItem.resize(
                    self.dialog.attrView.width() - 32,
                    nodeUtils.options.attributeFont.pixelSize() + 4,
                )
                pageItem.setLayout(pageLayout)
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
                height += item.geometry().height() + 7
                layout.addItem(item)

        form = QtWidgets.QGraphicsWidget()
        form.setLayout(layout)
        form.setPos(0, 0)
        self.dialog.attrScene.addItem(form)
        self.dialog.attrView.setSceneRect(
            0, 0, self.dialog.attrView.width(), height
        )

    def dropEvent(self, event):
        if event is None:
            return
        mime = cast(NodeMimeData, event.mimeData())
        obj = mime.getObject() if mime is not None else None
        if (
            mime is None
            or not mime.hasFormat("node/connect")
            or obj is None
            or obj == self
        ):
            return
        if obj.__class__ == Node:
            d = {
                "name": "Connection",
                "parent": obj.id,
                "child": self.id,
            }
            scene = self.scene()
            if scene is not None:
                nodeUtils.options.undoStack.push(
                    CommandCreateConnection(scene, d)
                )
            return
        if self.dialog is None:
            return
        scene = self.scene()
        parent = scene.parent() if scene is not None else None
        menu = QtWidgets.QMenu(
            parent=parent if isinstance(parent, QtWidgets.QWidget) else None
        )
        shader = self.dialog.shaders.get(self.shader)
        if shader is None:
            return
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
        d = {
            "name": "Connection",
            "parent": obj.id,
            "child": self.id,
            "attr": str(action.text()),
        }
        scene = self.scene()
        if scene is not None:
            nodeUtils.options.undoStack.push(CommandCreateConnection(scene, d))

    def contextMenuEvent(self, event):
        if event is None:
            return
        scene = self.scene()
        parent = scene.parent() if scene is not None else None
        menu = QtWidgets.QMenu(
            parent=parent if isinstance(parent, QtWidgets.QWidget) else None
        )
        setIconAction = menu.addAction("Set icon")
        clearIconAction = menu.addAction("Clear icon")
        editNameAction = menu.addAction("Edit title")
        editKeywordsAction = menu.addAction("Edit keywords")
        setOutputAction = menu.addAction("Set output type")
        action = menu.exec(event.screenPos())
        if action == setIconAction:
            filename, _ = QtWidgets.QFileDialog.getOpenFileName(
                self.dialog, "Open File", "", "Icon Files (*.jpg *.png *.ico)"
            )
            if filename:
                nodeUtils.options.undoStack.push(
                    CommandSetNodeAttribute([self], {"icon": filename})
                )
        elif action == clearIconAction and self.icon is not None:
            nodeUtils.options.undoStack.push(
                CommandSetNodeAttribute([self], {"icon": None})
            )
        elif action == editNameAction and self.nameItem is not None:
            self.nameItem.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextEditorInteraction
            )
            self.nameItem.setFocus(Qt.FocusReason.MouseFocusReason)
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
