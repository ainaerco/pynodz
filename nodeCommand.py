from qtpy.QtCore import QTimeLine
from qtpy.QtGui import QUndoCommand
from qtpy import QtWidgets

import nodeUtils
from nodeUtils import listRemove, incrementName
from nodeParts.Connection import Connection
from nodeUtils import getNodeClass
import bezier


class NodeAnimation(QtWidgets.QGraphicsItemAnimation):  # type: ignore[misc]
    def __init__(self, *args):
        super().__init__(*args)
        self.opacity_points: list[tuple[float, float]] = []
        self.opacity_bezier = None

    def setOpacityAt(self, t: float, o: float) -> None:
        self.opacity_points += [(t, o)]
        if len(self.opacity_points) > 3:
            self.opacity_bezier = bezier.Bspline(self.opacity_points)

    def afterAnimationStep(self, step: float) -> None:
        item = self.item()
        if item is not None and self.opacity_bezier is not None:
            o = self.opacity_bezier(step)[1]
            item.setOpacity(o)
            for c in item.connections:
                c.setOpacity(o)
        if item is not None:
            for c in item.connections:
                c.prepareGeometryChange()
                c.updatePath()
                c.update()
        super().afterAnimationStep(step)


class CommandMoveNode(QUndoCommand):  # type: ignore[misc]
    def __init__(self, sel, pos):
        QUndoCommand.__init__(self)
        self.node_ids = [x.id for x in sel]
        self.positions = pos
        self.old_positions = [x.old_pos for x in sel]
        self.setText("move node")

    def undo(self):
        n = [nodeUtils.options.nodes[x] for x in self.node_ids]
        for i in range(len(n)):
            n[i].setPos(self.old_positions[i].x(), self.old_positions[i].y())
            n[i].update()

    def redo(self):
        n = [nodeUtils.options.nodes[x] for x in self.node_ids]
        for i in range(len(n)):
            n[i].setPos(self.positions[i].x(), self.positions[i].y())
            n[i].update()


class CommandMoveAnimNode(QUndoCommand):  # type: ignore[misc]
    def __init__(self, sel, pos, time, fadeOut=False):
        QUndoCommand.__init__(self)
        self.node_ids = [x.id for x in sel]
        self.positions = pos
        self.fadeOut = fadeOut
        self.time = time
        self.old_positions = [x.old_pos for x in sel]
        self.setText("node move")

    def undo(self):
        n = [nodeUtils.options.nodes[x] for x in self.node_ids]
        for i in range(len(n)):
            n[i].prepareGeometryChange()
            n[i].setPos(self.old_positions[i].x(), self.old_positions[i].y())

    def redo(self):
        timeline = QTimeLine()
        timeline.setUpdateInterval(int(1000 / 25))
        timeline.setDuration(self.time)
        n = [nodeUtils.options.nodes[x] for x in self.node_ids]
        self.animations = []
        for i in range(len(n)):
            animation = NodeAnimation()
            animation.setItem(n[i])
            animation.setTimeLine(timeline)
            animation.setPosAt(0, self.old_positions[i])
            animation.setPosAt(1, self.positions[i])
            if self.fadeOut:
                animation.setOpacityAt(0.0, 0.0)
                animation.setOpacityAt(0.5, 0.3)
                animation.setOpacityAt(0.7, 0.5)
                animation.setOpacityAt(1.0, 1.0)
            self.animations.append(animation)
        timeline.start()


class CommandSetNodeAttribute(QUndoCommand):  # type: ignore[misc]
    def __init__(self, sel, d):
        QUndoCommand.__init__(self)
        self.node_ids = [x.id for x in sel]
        self.old_names = []
        self.new_names = []
        if "name" in d.keys():
            for s in sel:
                self.old_names += [s.name]
                d["name"] = incrementName(d["name"], nodeUtils.options.names)
                self.new_names += [d["name"]]
        self.dict = d
        self.undo_dict = []
        self.setText("set node attribute")

    def undo(self):
        nodes = [nodeUtils.options.nodes[x] for x in self.node_ids]
        if "name" in self.dict.keys():
            for i in range(len(nodes)):
                node = nodes[i]
                node.fromDict(self.undo_dict[i])
                node.name = self.old_names[i]
        else:
            for i in range(len(nodes)):
                node = nodes[i]
                node.fromDict(self.undo_dict[i])

    def redo(self):
        nodes = [nodeUtils.options.nodes[x] for x in self.node_ids]
        if "name" in self.dict.keys():
            self.undo_dict = []
            for i, node in enumerate(nodes):
                self.undo_dict += [node.toDict()]
                node.fromDict(self.dict)
                node.name = self.new_names[i]
        else:
            self.undo_dict = []
            for node in nodes:
                self.undo_dict += [node.toDict()]
                node.fromDict(self.dict)


class CommandSetColor(QUndoCommand):  # type: ignore[misc]
    def __init__(self, sel, color):
        QUndoCommand.__init__(self)
        self.node_ids = [x.id for x in sel]

        self.color = color
        self.undo_colors = [x.color for x in sel]
        self.setText("set color")

    def undo(self):
        n = [nodeUtils.options.nodes[x] for x in self.node_ids]
        for i in range(len(n)):
            n[i].setColor(self.undo_colors[i])

    def redo(self):
        ns = [nodeUtils.options.nodes[x] for x in self.node_ids]
        for n in ns:
            n.setColor(self.color)


class CommandCreateNode(QUndoCommand):  # type: ignore[misc]
    def __init__(self, dialog, d):
        QUndoCommand.__init__(self)
        self.dialog = dialog
        self.dict = d
        if "name" not in self.dict.keys():
            raise ValueError("CommandCreateNode 'name' not specified")
        if "id" not in d.keys():
            nodeUtils.options.addId()
            self.dict["id"] = nodeUtils.options.ids
        self.dict["name"] = incrementName(
            self.dict["name"], nodeUtils.options.names
        )

        self.setText("create node")

    def getName(self):
        return self.dict["id"]

    def undo(self):
        n = nodeUtils.options.nodes[self.dict["id"]]
        nodeUtils.options.deleteNode(n.id)
        self.dialog.scene.removeItem(n)

    def redo(self):
        n = getNodeClass(self.dict.get("type", "Node"))(self.dict, self.dialog)
        n.setPos(self.dict.get("posx", 0), self.dict.get("posy", 0))
        nodeUtils.options.addNode(n.id, n)
        self.dialog.scene.addItem(n)


class CommandCreateConnection(QUndoCommand):  # type: ignore[misc]
    def __init__(self, scene, d):
        QUndoCommand.__init__(self)
        self.scene = scene
        self.dict = d
        if "name" not in self.dict.keys():
            raise ValueError("CommandCreateNode 'name' not specified")
        if "parent" not in self.dict.keys():
            raise ValueError("CommandCreateNode 'parent' not specified")
        if "child" not in self.dict.keys():
            raise ValueError("CommandCreateNode 'child' not specified")
        if "id" not in d.keys():
            nodeUtils.options.addId()
            self.dict["id"] = nodeUtils.options.ids
        self.dict["name"] = incrementName(
            self.dict["name"], nodeUtils.options.names
        )
        self.setText("create connection")

    def getName(self):
        return self.dict["id"]

    def undo(self):
        c = nodeUtils.options.connections[self.dict["id"]]
        parent = nodeUtils.options.nodes[self.dict["parent"]]
        child = nodeUtils.options.nodes[self.dict["child"]]
        listRemove(child.connections, c)
        listRemove(parent.connections, c)
        listRemove(parent.childs, child)
        nodeUtils.options.deleteConnection(c.id)
        self.scene.removeItem(c)

    def redo(self):
        d = {}
        d.update(self.dict)

        d["parent"] = nodeUtils.options.nodes[self.dict["parent"]]
        d["child"] = nodeUtils.options.nodes[self.dict["child"]]
        parent = d["parent"]
        child = d["child"]
        c = Connection(d)
        nodeUtils.options.addConnection(c.id, c)
        parent.childs += [child]
        parent.connections += [c]
        child.connections += [c]
        self.scene.addItem(c)


class CommandDeleteConnections(QUndoCommand):  # type: ignore[misc]
    def __init__(self, scene, conns):
        QUndoCommand.__init__(self)
        self.scene = scene
        self.conn_ids = [x.id for x in conns]
        self.saved_conns = []
        self.setText("delete connection")

    def undo(self):
        for i in range(len(self.conn_ids)):
            parent = nodeUtils.options.nodes[self.saved_conns[i]["parent"]]
            child = nodeUtils.options.nodes[self.saved_conns[i]["child"]]
            self.saved_conns[i]["child"] = child
            self.saved_conns[i]["parent"] = parent
            c = Connection(self.saved_conns[i])
            nodeUtils.options.addConnection(c.id, c)
            parent.connections += [c]
            parent.childs += [child]
            child.connections += [c]
            self.scene.addItem(c)

    def redo(self):
        self.saved_conns = []
        conns = [nodeUtils.options.connections[x] for x in self.conn_ids]
        for c in conns:
            self.saved_conns += [c.toDict()]
            listRemove(c.child.connections, c)
            listRemove(c.parent.connections, c)
            listRemove(c.parent.childs, c.child)
            nodeUtils.options.deleteConnection(c.id)
            self.scene.removeItem(c)


class CommandDeleteNodes(QUndoCommand):  # type: ignore[misc]
    def __init__(self, dialog, nodes):
        QUndoCommand.__init__(self)
        self.node_ids = [x.id for x in nodes]
        self.dialog = dialog
        self.saved_nodes = []
        self.saved_conns = []
        self.setText("delete node")

    def undo(self):
        for n in self.saved_nodes:
            node = getNodeClass(n["type"])(n, self.dialog)
            node.setPos(n["posx"], n["posy"])

            nodeUtils.options.addNode(node.id, node)
            self.dialog.scene.addItem(node)

        for i in range(len(self.saved_conns)):
            parent = nodeUtils.options.nodes[self.saved_conns[i]["parent"]]
            child = nodeUtils.options.nodes[self.saved_conns[i]["child"]]
            self.saved_conns[i]["child"] = child
            self.saved_conns[i]["parent"] = parent
            c = Connection(self.saved_conns[i])
            nodeUtils.options.addConnection(c.id, c)
            parent.connections += [c]
            parent.childs += [child]
            child.connections += [c]
            self.dialog.scene.addItem(c)

    def redo(self):
        self.saved_conns = []
        self.saved_nodes = []
        ns = [nodeUtils.options.nodes[x] for x in self.node_ids]
        for n in ns:
            if n.__class__.__name__ == "Node" and n.collapsed:
                n.setCollapsed(True)
            for c in n.connections:
                self.saved_conns += [c.toDict()]
                listRemove(c.child.connections, c)
                listRemove(c.parent.connections, c)
                listRemove(c.parent.childs, c.child)
                nodeUtils.options.deleteConnection(c.id)
                self.dialog.scene.removeItem(c)
            self.saved_nodes += [n.toDict()]
            nodeUtils.options.deleteNode(n.id)
            self.dialog.scene.removeItem(n)
