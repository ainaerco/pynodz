from qtpy.QtGui import QPen, QColor, QPainterPath, QTransform
from qtpy.QtCore import Qt, QRectF, QPointF
from qtpy import QtWidgets

import bezier

try:
    import pybezier
except ImportError:
    pybezier = None  # optional dependency
from math import cos, sin, atan2
import nodeUtils


class Connection(QtWidgets.QGraphicsItem):
    def __init__(self, d):
        QtWidgets.QGraphicsItem.__init__(self)
        from nodeParts.Parts import TitleItem

        self.p_x = []
        self.p_y = []
        self.pen = QPen(Qt.GlobalColor.black, 1)

        self.arrow1 = QPainterPath()
        self.arrow2 = QPainterPath()
        self.constrain = d.get("constrain", True)
        self.nameItem = TitleItem("", self, "name")
        self.fromDict(d)
        self.updatePath()
        self.setAcceptDrops(True)
        self.setAcceptHoverEvents(True)

    def fromDict(self, d):
        self.parent = d["parent"]
        self.child = d["child"]
        if "id" in d.keys():
            self.id = d["id"]
        self.name = d.get("name", "")
        self.constrain = d.get("constrain", True)
        self.attr = d.get("attr", "")
        if self.attr:
            self.nameItem.setPlainText(d["attr"])

    def toDict(self):
        res = {"parent": self.parent.id, "child": self.child.id}
        res["type"] = "Connection"
        res["name"] = self.name
        res["attr"] = self.attr
        res["id"] = self.id
        return res

    def shape(self):
        p = QPainterPath()
        z = self.boundingRect()
        p.addRect(z)
        return self.path

    def updatePath(self):

        if self.constrain:
            t = QTransform()
            if hasattr(self.parent, "connector") and self.parent.connector:
                p1 = t.map(self.parent.pos() + self.parent.connector.pos())
            else:
                p = self.parent.pos() + self.parent._rect.center()
                t.translate(p.x(), p.y())
                t.rotate(self.parent.rotation())
                t.translate(-p.x(), -p.y())
                p1 = t.map(
                    self.parent.pos()
                    + self.parent._rect.center()
                    + self.parent._rect.topRight() * 0.5
                )

            t = QTransform()
            p = self.child.pos() + self.child._rect.center()
            t.translate(p.x(), p.y())
            t.rotate(self.child.rotation())
            t.translate(-p.x(), -p.y())
            p2 = t.map(self.child.pos() + self.child._rect.topRight() * 0.5)
            self._rect = QRectF(p1, p2)
        else:
            self._rect = QRectF(self.parent, self.child)
        a = self._rect.topLeft()
        b = self._rect.bottomRight()

        self.path = QPainterPath()

        self.p_x = [
            a.x(),
            a.x() + (b.x() - a.x()) * 0.1,
            (a.x() + b.x()) / 2.0,
            b.x() - (b.x() - a.x()) * 0.1,
            b.x(),
        ]
        self.p_y = [
            a.y(),
            a.y() + abs(b.y() - a.y()) * 0.2,
            (a.y() + b.y()) / 2.0,
            b.y() - abs(b.y() - a.y()) * 0.2,
            b.y(),
        ]
        P = list(zip(self.p_x, self.p_y))
        # P = [(a.x(),a.y()),(a.x(),a.y()+10),(a.x(),a.y()+20),((b.x()+a.x())*0.5,(b.y()+a.y())*0.5),(b.x(),b.y()-20),(b.x(),b.y()-10),(b.x(),b.y())]
        # P = [(a.x(), a.y()), (a.x() + 10, a.y()), (a.x() + 30, a.y()), (b.x() - 30, b.y()), (b.x() - 10, b.y()),(b.x(), b.y())]

        S = bezier.Bezier(P)
        self.path.moveTo(P[0][0], P[0][1])
        step_size = 1 / float(nodeUtils.options.splineStep)
        for i in range(1, nodeUtils.options.splineStep + 1):
            t_ = i * step_size
            # try:
            x, y = S(t_)
            # except AssertionError: continue
            self.path.lineTo(x, y)
        return
        # x, y = S(0.85)

        # Lagrange
        li = []
        for i in range(len(self.p_x)):
            li += [self.p_x[i]] + [self.p_y[i]]
        return
        w = pybezier.Spline(li)
        li = w.interpolate(4)
        x_intpol = []
        y_intpol = []
        for i in range(len(li) / 2):
            x_intpol += [li[i * 2]]
            y_intpol += [li[i * 2 + 1]]
        # x_intpol, y_intpol = bezier.CatmullRom(self.p_x, self.p_y, nodeUtils.options.splineStep/3)

        self.path.moveTo(x_intpol[0], y_intpol[0])
        for i in range(1, len(x_intpol)):
            self.path.lineTo(x_intpol[i], y_intpol[i])
        x = x_intpol[-2]
        y = y_intpol[-2]

        self.nameItem.setPos(self.boundingRect().center())
        self.nameItem.setRotation(-self.path.angleAtPercent(0.5))
        # x,y=S(0.5)
        # p0 = QPointF(x,y)
        # p0 = p0-b
        # a = degrees(atan2(p0.y(),p0.x()))
        # self.nameItem.setRotation(180+a)

        p0 = QPointF(x, y)
        p0 = p0 - b
        a = atan2(p0.y(), p0.x())
        self.arrow1 = QPainterPath()
        self.arrow1.moveTo(b)
        self.arrow1.lineTo(
            b.x() + cos(a - 0.15) * 15.0, b.y() + sin(a - 0.15) * 15.0
        )
        self.arrow2 = QPainterPath()
        self.arrow2.moveTo(b)
        self.arrow2.lineTo(
            b.x() + cos(a + 0.15) * 15.0, b.y() + sin(a + 0.15) * 15.0
        )

    def boundingRect(self):
        return self.path.controlPointRect()

    def setSelected(self, selected: bool):
        if selected:
            self.pen = QPen(QColor(250, 200, 70), 1.3)
        else:
            self.pen = QPen(Qt.GlobalColor.black, 1.3)
        self.update()

    def paint(self, painter, option, widget=None):
        if painter is None:
            return
        painter.setPen(self.pen)
        painter.drawPath(self.path)
        painter.drawPath(self.arrow1)
        painter.drawPath(self.arrow2)

    def contextMenuEvent(self, event):
        if event is None:
            return
        scene = self.scene()
        if scene is None:
            return
        parent = scene.parent() if scene is not None else None
        menu = QtWidgets.QMenu(
            parent=parent if isinstance(parent, QtWidgets.QWidget) else None
        )
        editNameAction = menu.addAction("Edit name")
        action = menu.exec(event.screenPos())
        if action == editNameAction:
            self.nameItem.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextEditorInteraction
            )
            self.nameItem.setFocus(Qt.FocusReason.MouseFocusReason)
