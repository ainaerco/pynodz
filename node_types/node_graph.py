from qtpy.QtGui import QFontMetrics, QColor, QLinearGradient, QBrush
from qtpy.QtCore import QPointF
from .node import Node
import node_utils


class NodeGraph(Node):
    def __init__(self, d, dialog=None):
        super().__init__(d, dialog)

    def addExtraControls(self):
        pass

    def setRect(self, rect):
        fm = QFontMetrics(node_utils.options.titleFont)
        width = max(rect.width(), fm.horizontalAdvance(self.name) + 20)
        rect.setWidth(width)
        super().setRect(rect)

    def setColor(self, c):
        self.color = QColor(c.red(), c.green(), c.blue(), 255)
        if self.shadow:
            c = c.darker(150)
            c.setAlpha(255)
            self.shadow.setColor(c)
        gradient = QLinearGradient(
            self._rect.topLeft(), self._rect.bottomRight()
        )
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
        x = self.pos().x() + self._rect.width() + 50
        y = 0

        def getKey(item):
            return item.pos().y()

        self.childs = sorted(self.childs, key=getKey)
        for child in self.childs:
            y += child._rect.height() + 5
        y = self.pos().y() + self._rect.center().y() - y * 0.5
        positions = []
        for child in self.childs:
            positions += [QPointF(x, y)]
            child.old_pos = child.pos()
            y += child._rect.height() + 5
        from node_command import CommandMoveNode

        node_utils.options.undoStack.push(
            CommandMoveNode(self.childs, positions)
        )

    def mouseDoubleClickEvent(self, event):
        def getChilds(node):
            nodeList = [node]

            for n in nodeList:
                childs = n.childs
                for c in childs:
                    if c not in nodeList:
                        nodeList.append(c)

            return nodeList

        li = getChilds(self)
        for node in li:
            node.alignChilds()
