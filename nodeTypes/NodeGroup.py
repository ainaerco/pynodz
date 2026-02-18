from qtpy.QtGui import QPen, QColor, QLinearGradient, QBrush
from qtpy.QtCore import Qt, QPointF, QRectF
from .Node import Node
import nodeUtils


class NodeGroup(Node):
    def __init__(self, d, dialog=None):

        Node.__init__(self, d, dialog)

        self.setAcceptDrops(True)
        self.anchor = QPointF()
        self.setZValue(0)

    def addExtraControls(self):
        # self.resizeItem = NodeResize(self, rect=QRectF(-12, -12, 12, 12))
        # self.resizeItem.hide()
        # self.dropdown = DropDown(self,nodeUtils.options,'resources/icons/dropdown_arrows.png')
        # if self.collapsed == True: self.dropdown.setState(True)
        Node.addExtraControls(self)

    def init(self, d):
        self.collapsedRect = QRectF(0, 0, 100, 25)
        Node.init(self, d)

    def setRect(self, rect):
        self.collapsedRect.setWidth(rect.width())
        if self.scene():
            rect = QRectF(
                self.pos().x(),
                self.pos().y(),
                self._rect.width(),
                self._rect.height(),
            )
            self.childs = [
                x
                for x in self.scene().items(
                    rect,
                    Qt.ItemSelectionMode.IntersectsItemShape,
                    Qt.SortOrder.DescendingOrder,
                )
                if issubclass(x.__class__, Node) and x != self
            ]
        Node.setRect(self, rect)

    def setSelected(self, selected: bool):
        if self.shadow:
            self.shadow.updateBoundingRect()
        self._selected = selected
        if selected:
            self.pen = QPen(QColor(250, 140, 10), 3)
        else:
            if self.dialog and self.dialog.outline:
                self.pen = QPen(Qt.GlobalColor.black, 1.5)
            else:
                self.pen = QPen(QColor(0, 0, 0, 0), 0)

    def setCollapsed(self, collapsed: bool):
        # if not collapsed and self.scene():
        #     self.childs = [x for x in self.scene().items(self.pos().x(),self.pos().y(),
        #     self._rect.width(),self._rect.height(), Qt.IntersectsItemShape, Qt.DescendingOrder) if issubclass(x.__class__,Node) and x!=self]
        # if self.collapsed is collapsed:
        #     self.prepareGeometryChange()
        #     self.rect,self.collapsedRect = self.collapsedRect,self.rect
        #     self.resize(self._rect.width(), self._rect.height())
        #     self.update()
        Node.setCollapsed(self, collapsed)

    def setColor(self, c):
        self.color = QColor(c.red(), c.green(), c.blue(), 30)
        if self.shadow:
            c = c.darker(150)
            c.setAlpha(30)
            self.shadow.setColor(c)
        gradient = QLinearGradient(
            self._rect.topLeft(), self._rect.bottomRight()
        )
        color = QColor()
        color.setHsv(
            self.color.hue(),
            max(0, self.color.saturation() - 60),
            self.color.value(),
            30,
        )
        gradient.setColorAt(0, self.color)
        gradient.setColorAt(1, color)
        self.brush = QBrush(gradient)

    def paint(self, painter, option, widget=None):
        painter.setBrush(self.brush)
        painter.setPen(self.pen)
        painter.drawRoundedRect(
            self.rect,
            nodeUtils.options.nodeRadius,
            nodeUtils.options.nodeRadius,
        )
