from qtpy.QtCore import Qt, QRectF
from qtpy import QtWidgets

from .Node import Node
from nodeParts.Parts import NodeInput
import nodeUtils
from copy import deepcopy
from nodeUtils import incrementName
from nodeCommand import CommandSetNodeAttribute
from nodeAttrs import getAttrByType, NodeAttr


class NodeControl(Node):
    def __init__(self, d, dialog=None):
        Node.__init__(self, d, dialog)
        self.setAcceptDrops(True)
        self.setZValue(0)
        self.graphicLayout = QtWidgets.QGraphicsLinearLayout(
            Qt.Orientation.Vertical
        )
        self.graphicLayout.setSpacing(7)
        self.graphicLayout.setContentsMargins(23, 20, 7, 7)
        self.setLayout(self.graphicLayout)
        self.attrNames = {}
        for key in self.values.keys():
            c = self.values[key].__class__
            if c == float:
                attr = {
                    "default": 0,
                    "type": "FLOAT",
                    "name": key,
                    "value": self.values[key],
                }
                self.pinUnpin(attr, True)
            elif c == list and len(self.values[key]) == 3:
                attr = {
                    "default": [0, 0, 0],
                    "type": "VECTOR",
                    "name": key,
                    "value": self.values[key],
                }
                self.pinUnpin(attr, True)
            elif c == str or c is unicode:
                attr = {
                    "default": "",
                    "type": "STRING",
                    "name": key,
                    "value": self.values[key],
                }
                self.pinUnpin(attr, True)
            else:
                print("unsupported attr class", c)

    def addExtraControls(self):
        pass

    def resize(self, width, height):
        rect = QRectF(0, 0, width, height)
        Node.setRect(self, rect)
        QtWidgets.QGraphicsWidget.resize(self, width, height)

    def updateGeometry(self):
        # self.prepareGeometryChange()
        margin = self.graphicLayout.spacing()
        (l, t, r, b) = self.graphicLayout.getContentsMargins()
        height = t
        width = self.rect.width()
        for i in range(self.graphicLayout.count()):
            item = self.graphicLayout.itemAt(i)
            height += item.rect.height() + margin
            width = item.rect.width() + l + r

        height += b
        self.resize(width, height)
        QtWidgets.QGraphicsWidget.updateGeometry(self)

    def init(self, d):
        Node.init(self, d)
        self.pinnedAttributes = {}
        self.values = d.get("values", {})

    def pinUnpin(self, attr, pinned):
        # print self.name,'pinUnpin'
        # nodeUtils.options.arnold = dict(mergeDicts(nodeUtils.options.arnold,{self.shader:{attr['name']:{'_pin':pinned}}}))
        # nodeUtils.options.arnold.update({self.shader:{attr['name']:{'_pin':pinned}}})
        if attr["name"] in self.pinnedAttributes.keys():
            if not pinned:
                self.prepareGeometryChange()
                self.graphicLayout.removeItem(
                    self.pinnedAttributes[attr["name"]]
                )
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
        self.graphicLayout.addItem(item)
        connector = NodeInput(self)
        connector.setRect(QRectF(-5, -5, 10, 10))

        # self.setRect(self.form.boundingRect())
        self.updateGeometry()
        p = item.pos() + self.rect.topRight() + item.rect.bottomLeft() * 0.5

        connector.setPos(p.x() - item.pos().x(), p.y())

    def contextMenuEvent(self, event):
        menu = QtWidgets.QMenu(self.scene().parent())
        addFloatControl = menu.addAction("Add Float Control")
        addVectorControl = menu.addAction("Add Vector Control")
        addStringControl = menu.addAction("Add String Control")
        action = menu.exec_(event.screenPos())
        if action == addFloatControl:
            name = "float_control"
            name = incrementName(name, self.attrNames)
            attr = {"default": 0, "type": "FLOAT", "name": name}
            self.pinUnpin(attr, True)
        elif action == addVectorControl:
            name = "vector_control"
            name = incrementName(name, self.attrNames)
            attr = {"default": [0, 0, 0], "type": "VECTOR", "name": name}
            self.pinUnpin(attr, True)
        elif action == addStringControl:
            name = "string_control"
            name = incrementName(name, self.attrNames)
            attr = {"default": "", "type": "STRING", "name": name}
            self.pinUnpin(attr, True)

    def fromDict(self, d):
        if "values" in d.keys():
            vs = d["values"]
            # print "fromDict",vs
            for key in vs.keys():
                self.values[key] = deepcopy(vs[key])
                if key in self.pinnedAttributes.keys():
                    self.pinnedAttributes[key].value = vs[key]
                    self.pinnedAttributes[key].update()
        Node.fromDict(self, d)

    def toDict(self):
        res = Node.toDict(self)
        res["values"] = dict(self.values)
        # print "toDict",res['values']
        return res

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
        if clas == None:
            clas = NodeAttr
        item = clas(self, nodeUtils.options, attr)
        if attr["name"] in self.values.keys():
            item.value = deepcopy(self.values[attr["name"]])
        else:
            self.values[attr["name"]] = deepcopy(item.value)
        if connectedAttrs is not None and attr["name"] in connectedAttrs:
            item.setConnected(True)

        return item
