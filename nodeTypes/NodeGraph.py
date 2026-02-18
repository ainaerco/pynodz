from qtpy.QtGui import *
from qtpy.QtCore import *
from .Node import Node
from nodeCommand import CommandMoveNode
import nodeUtils


class NodeGraph(Node):
    def __init__(self, d, dialog=None):
        Node.__init__(self, d, dialog)

    def addExtraControls(self):
        pass

    # def setSelected(self, state):
    #     Node.setSelected(self, state)
    #     print self.connections
    #     for c in self.connections:
    #         c.setSelected(state)

    def setRect(self, rect):
        fm = QFontMetrics(nodeUtils.options.titleFont)
        width = max(rect.width(), fm.width(self.name) + 20)
        rect.setWidth(width)
        Node.setRect(self, rect)

    def setColor(self, c):
        self.color = QColor(c.red(), c.green(), c.blue(), 255)
        if self.shadow:
            c = c.darker(150)
            c.setAlpha(255)
            self.shadow.setColor(c)
        gradient = QLinearGradient(self.rect.topLeft(), self.rect.bottomRight())
        color = QColor()
        color.setHsv(
            self.color.hue(),
            max(0, self.color.saturation() - 10),
            self.color.value(),
            255,
        )
        gradient.setColorAt(0, self.color)
        gradient.setColorAt(1, color)
        self.brush = QBrush(gradient)
        self.update()

    def alignChilds(self):
        x = self.pos().x() + self.boundingRect().width() + 50
        y = 0

        def getKey(item):
            return item.pos().y()

        self.childs = sorted(self.childs, key=getKey)
        for child in self.childs:
            y += child.boundingRect().height() + 5
        y = self.pos().y() + self.boundingRect().center().y() - y * 0.5
        positions = []
        for child in self.childs:
            positions += [QPointF(x, y)]
            child.old_pos = child.pos()
            y += child.boundingRect().height() + 5
        nodeUtils.options.undoStack.push(
            CommandMoveNode(self.childs, positions)
        )

    def mouseDoubleClickEvent(self, event):
        # print "mouseDoubleClickEvent"
        def get_childs(node):
            nodeList = [node]

            for n in nodeList:
                childs = n.childs
                for c in childs:
                    if c not in nodeList:
                        nodeList.append(c)

            return nodeList

        li = get_childs(self)
        for node in li:
            node.alignChilds()
