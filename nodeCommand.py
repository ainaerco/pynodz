from qtpy.QtCore import (
    QObject,
    QPointF,
    QPropertyAnimation,
    QParallelAnimationGroup,
)
from qtpy.QtCore import Property  # type: ignore[attr-defined]
from qtpy.QtGui import QUndoCommand

import nodeUtils
from nodeUtils import listRemove, incrementName
from nodeParts.Connection import Connection
from nodeUtils import getNodeClass
from nodeTypes import Node
import bezier


class NodeAnimationBridge(QObject):  # type: ignore[misc]
    """Bridge QObject so QPropertyAnimation can drive a QGraphicsItem (pos/opacity)."""

    def __init__(self, item, parent=None):
        super().__init__(parent)
        self._item = item
        self._pos = QPointF(item.pos())
        self._opacity = float(item.opacity())

    def get_pos(self):
        return self._pos

    def set_pos(self, value: QPointF):
        self._pos = value
        if self._item is not None:
            self._item.setPos(value.x(), value.y())
            for c in self._item.connections:
                c.prepareGeometryChange()
                c.updatePath()
                c.update()

    pos = Property(QPointF, get_pos, set_pos)

    def get_opacity(self):
        return self._opacity

    def set_opacity(self, value):
        self._opacity = value
        if self._item is not None:
            self._item.setOpacity(value)
            for c in self._item.connections:
                c.setOpacity(value)

    opacity = Property(float, get_opacity, set_opacity)


class OpacityBezierAnimation(QPropertyAnimation):  # type: ignore[misc]
    """QPropertyAnimation that interpolates opacity using a bezier curve."""

    def __init__(self, target, bezier_curve, parent=None):
        super().__init__(target, b"opacity", parent)
        self._bezier = bezier_curve

    def interpolated(self, from_, to, progress):
        if self._bezier is not None:
            return self._bezier(progress)[1]
        return super().interpolated(from_, to, progress)


def _create_node_animations(item, old_pos, new_pos, duration_ms, fade_out):
    """Create a QParallelAnimationGroup for one node: position + optional opacity."""
    bridge = NodeAnimationBridge(item)
    group = QParallelAnimationGroup()

    pos_anim = QPropertyAnimation(bridge, b"pos")
    pos_anim.setDuration(duration_ms)
    pos_anim.setStartValue(QPointF(old_pos))
    pos_anim.setEndValue(QPointF(new_pos))
    group.addAnimation(pos_anim)

    if fade_out:
        opacity_points = [(0.0, 0.0), (0.5, 0.3), (0.7, 0.5), (1.0, 1.0)]
        opacity_bezier = bezier.Bspline(opacity_points)
        opacity_anim = OpacityBezierAnimation(bridge, opacity_bezier)
        opacity_anim.setDuration(duration_ms)
        opacity_anim.setStartValue(0.0)
        opacity_anim.setEndValue(1.0)
        group.addAnimation(opacity_anim)

    return group, bridge


class CommandMoveNode(QUndoCommand):  # type: ignore[misc]
    def __init__(self, sel, pos):
        super().__init__()
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
        super().__init__()
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
        n = [nodeUtils.options.nodes[x] for x in self.node_ids]
        duration_ms = self.time
        self.animations = []
        self._bridges = []
        root_group = QParallelAnimationGroup()
        for i in range(len(n)):
            group, bridge = _create_node_animations(
                n[i],
                self.old_positions[i],
                self.positions[i],
                duration_ms,
                self.fadeOut,
            )
            root_group.addAnimation(group)
            self.animations.append(group)
            self._bridges.append(bridge)
        root_group.start()
        self._root_animation = root_group


class CommandSetNodeAttribute(QUndoCommand):  # type: ignore[misc]
    def __init__(self, sel, d):
        super().__init__()
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
        super().__init__()
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
        super().__init__()
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
        super().__init__()
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
        super().__init__()
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
            listRemove(c.parent_node.connections, c)
            listRemove(c.parent_node.childs, c.child)
            nodeUtils.options.deleteConnection(c.id)
            self.scene.removeItem(c)


class CommandDeleteNodes(QUndoCommand):  # type: ignore[misc]
    def __init__(self, dialog, nodes):
        super().__init__()
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
            if type(n) is Node and n.collapsed:
                n.setCollapsed(True)
            for c in n.connections:
                self.saved_conns += [c.toDict()]
                listRemove(c.child.connections, c)
                listRemove(c.parent_node.connections, c)
                listRemove(c.parent_node.childs, c.child)
                nodeUtils.options.deleteConnection(c.id)
                self.dialog.scene.removeItem(c)
            self.saved_nodes += [n.toDict()]
            nodeUtils.options.deleteNode(n.id)
            self.dialog.scene.removeItem(n)
