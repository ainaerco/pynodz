from qtpy.QtCore import Qt, QRectF
from qtpy.QtWidgets import QGraphicsLinearLayout, QMenu, QWidget

from .node import Node
from node_parts.parts import NodeInput
import node_utils
from copy import deepcopy
from node_utils import increment_name
from node_attrs import get_attr_by_type, NodeAttr


class NodeControl(Node):
    def __init__(self, d, dialog=None):
        super().__init__(d, dialog)
        self.setAcceptDrops(True)
        self.setZValue(0)
        self.graphicLayout = QGraphicsLinearLayout(Qt.Orientation.Vertical)
        self.graphicLayout.setSpacing(7)
        self.graphicLayout.setContentsMargins(23, 20, 7, 7)
        self.setLayout(self.graphicLayout)
        self.attrNames = {}
        for key in self.values.keys():
            c = type(self.values[key])
            if c is float:
                attr = {
                    "default": 0,
                    "type": "FLOAT",
                    "name": key,
                    "value": self.values[key],
                }
                self.pinUnpin(attr, True)
            elif c is list and len(self.values[key]) == 3:
                attr = {
                    "default": [0, 0, 0],
                    "type": "VECTOR",
                    "name": key,
                    "value": self.values[key],
                }
                self.pinUnpin(attr, True)
            elif c is str:
                attr = {
                    "default": "",
                    "type": "STRING",
                    "name": key,
                    "value": self.values[key],
                }
                self.pinUnpin(attr, True)

    def addExtraControls(self):
        pass

    def resize(self, width, height):
        rect = QRectF(0, 0, width, height)
        super().setRect(rect)
        super().resize(width, height)

    def updateGeometry(self):
        # self.prepareGeometryChange()
        margin = self.graphicLayout.spacing()
        (left, t, r, b) = self.graphicLayout.getContentsMargins()
        height = float(t) if t is not None else 0.0
        width = self._rect.width()
        for i in range(self.graphicLayout.count()):
            item = self.graphicLayout.itemAt(i)
            if item is None:
                continue
            geom = item.geometry()
            h = geom.height() if geom.height() is not None else 0.0
            w = geom.width() if geom.width() is not None else 0.0
            height = height + h + margin
            width = w + (left or 0) + (r or 0)
        height += b if b is not None else 0
        self.resize(width, height)
        super().updateGeometry()

    def init(self, d):
        super().init(d)
        self.pinnedAttributes = {}
        self.values = d.get("values", {})

    def pinUnpin(self, attr, pinned):
        if attr["name"] in self.pinnedAttributes.keys():
            if not pinned:
                self.prepareGeometryChange()
                self.graphicLayout.removeItem(
                    self.pinnedAttributes[attr["name"]]
                )
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
        item.resize(200, node_utils.options.attributeFont.pixelSize() + 4)
        self.graphicLayout.addItem(item)
        connector = NodeInput(self)
        connector.setRect(QRectF(-5, -5, 10, 10))

        self.updateGeometry()
        geom = item.geometry()
        p = item.pos() + self._rect.topRight() + geom.bottomLeft() * 0.5

        connector.setPos(p.x() - item.pos().x(), p.y())

    def contextMenuEvent(self, event):
        if event is None:
            return
        scene = self.scene()
        parent = scene.parent() if scene is not None else None
        menu = QMenu(parent=parent if isinstance(parent, QWidget) else None)
        addFloatControl = menu.addAction("Add Float Control")
        addVectorControl = menu.addAction("Add Vector Control")
        addStringControl = menu.addAction("Add String Control")
        action = menu.exec(event.screenPos())
        if action == addFloatControl:
            name = "float_control"
            name = increment_name(name, self.attrNames)
            attr = {"default": 0, "type": "FLOAT", "name": name}
            self.pinUnpin(attr, True)
        elif action == addVectorControl:
            name = "vector_control"
            name = increment_name(name, self.attrNames)
            attr = {"default": [0, 0, 0], "type": "VECTOR", "name": name}
            self.pinUnpin(attr, True)
        elif action == addStringControl:
            name = "string_control"
            name = increment_name(name, self.attrNames)
            attr = {"default": "", "type": "STRING", "name": name}
            self.pinUnpin(attr, True)

    def fromDict(self, d):
        if "values" in d.keys():
            vs = d["values"]
            for key in vs.keys():
                self.values[key] = deepcopy(vs[key])
                if key in self.pinnedAttributes.keys():
                    self.pinnedAttributes[key].value = vs[key]
                    self.pinnedAttributes[key].update()
        Node.fromDict(self, d)

    def toDict(self):
        res = Node.toDict(self)
        res["values"] = dict(self.values)
        return res

    def updateAttribute(self, name, value):
        from node_command import CommandSetNodeAttribute

        v = {name: deepcopy(value)}
        node_utils.options.undoStack.push(
            CommandSetNodeAttribute([self], {"values": v})
        )

    def addAttr(self, attr):
        connectedAttrs = [
            x.attr for x in self.connections if x.child == self and x.attr
        ]
        clas = get_attr_by_type(attr["type"])
        if clas is None:
            clas = NodeAttr
        item = clas(self, node_utils.options, attr)
        if attr["name"] in self.values.keys():
            item.value = deepcopy(self.values[attr["name"]])
        else:
            self.values[attr["name"]] = deepcopy(item.value)
        if connectedAttrs is not None and attr["name"] in connectedAttrs:
            item.setConnected(True)

        return item
