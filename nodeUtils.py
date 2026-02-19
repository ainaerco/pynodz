import re
import os
import json
from random import randint
from qtpy.QtGui import QFont, QColor, QPixmap, QUndoStack
from qtpy.QtCore import QObject, QMimeData


def getNodeClass(x):
    from nodeTypes import (
        Node,  # noqa: F401
        NodeGroup,  # noqa: F401
        NodeShader,  # noqa: F401
        NodeControl,  # noqa: F401
        NodeNote,  # noqa: F401
        NodeGraph,  # noqa: F401
        NodeBlock,  # noqa: F401
        NodeBookmark,  # noqa: F401
    )

    return locals()[x]


def normalizeName(name):
    we = re.sub(r"(\s{1,}|\-{1,}|\_{1,})+", "_", name)
    lowers = "abcdefghijklmnopqrstuvwxyz"
    skips = "_"
    we = we.rstrip(skips)
    result = ""
    i = 1
    while i <= len(we):
        if we[i - 1] == skips:
            if we[i] in lowers:
                result += we[i].upper()
            else:
                result += we[i]
            i += 1
        else:
            result += we[i - 1]
        i += 1
    return result


def incrementName(name, dic):
    """
    Increments name index by given dictinary
    Dictinary keys are names, values are number of instances
    Values of dict are updated
    """
    res = re.sub(r"\d+$", "", name)
    if res in dic.keys():
        d = dic[res] + 1
        dic[res] = d
        res += "%d" % d
    else:
        dic[res] = 0
        res += "0"
    return res


def listRemove(lst, item):
    """
    Removes item or items from list if it's exists
    List is referenced
    """
    try:
        idx = lst.index(item)
        del lst[idx]
    except Exception:
        pass


def mergeDicts(dict1, dict2):
    """
    Result should be converted to dict()
    """
    for k in set(dict1.keys()).union(dict2.keys()):
        if k in dict1 and k in dict2:
            if isinstance(dict1[k], dict) and isinstance(dict2[k], dict):
                yield (k, dict(mergeDicts(dict1[k], dict2[k])))
            else:
                # If one of the values is not a dict, you can't continue merging it.
                # Value from second dict overrides one in first and we move on.
                yield (k, dict2[k])
                # Alternatively, replace this with exception raiser to alert you of value conflicts
        elif k in dict1:
            yield (k, dict1[k])
        else:
            yield (k, dict2[k])


def sample(iterator, k):
    """
    Samples k elements from an iterable object.

    :param iterator: an object that is iterable
    :param k: the number of items to sample
    keys = self.shaders.keys()
    for key in sample(iter(keys), 10):
    """
    # fill the reservoir to start
    result = [next(iterator) for _ in range(k)]

    n = k
    for item in iterator:
        n += 1
        s = randint(0, n)
        if s < k:
            result[s] = item

    return result


class NodeMimeData(QMimeData):
    def __init__(self, *args):
        QMimeData.__init__(self, *args)
        self.object = None
        self.origin = None

    def setOrigin(self, point):
        self.origin = point

    def setObject(self, obj):
        self.object = obj

    def getObject(self):
        return self.object


class NodesOptions(QObject):
    def __init__(self):
        QObject.__init__(self)
        self.undoStack = QUndoStack(self)
        self.arnold = self.loadArnoldSettings()
        self.splineStep = 20
        self.ids = -1
        self.iconSize = 18
        self.nodeRadius = 5
        self.colorSelector = "triangle"
        self.icons = {}
        self.nodes = {}
        self.names = {}
        self.connections = {}
        self.selected = []
        self.dialog = None
        self.colorPicker = None
        self.viewport = None
        self.scene = None
        self.attributeFont = QFont("Courier New")
        self.attributeFont.setPixelSize(14)
        self.titleFont = QFont("Courier New")
        self.titleFont.setPixelSize(14)
        self.titleFont.setBold(True)
        self.typeColors = {
            "ENUM": QColor(100, 10, 10),
            "FLOAT": QColor(10, 100, 10),
            "RGB": QColor(200, 10, 10),
            "RGBA": QColor(200, 10, 10),
            "MATRIX": QColor(10, 10, 100),
            "STRING": QColor(50, 50, 50),
            "VECTOR": QColor(100, 100, 100),
            "BOOL": QColor(10, 100, 100),
            "POINT": QColor(100, 100, 10),
            "POINT2": QColor(100, 100, 10),
        }

    def addId(self):
        self.ids += 1

    def setIds(self, value):
        self.ids = value

    def addNode(self, name, val):
        self.nodes[name] = val

    def deleteNode(self, name):
        del self.nodes[name]

    def clearNodes(self):
        self.nodes.clear()

    def addConnection(self, name, val):
        self.connections[name] = val

    def deleteConnection(self, name):
        del self.connections[name]

    def clearConnections(self):
        self.connections.clear()

    def saveArnoldSettings(self):
        path = "arnold_settings.json"
        js = json.dumps(
            self.arnold, sort_keys=False, indent=4
        )  # .decode('unicode-escape').encode('utf-8')
        f = open(path, "w")
        f.write(js)
        f.close()

    def loadArnoldSettings(self):
        path = "arnold_settings.json"
        result = {}
        if not os.path.isfile(path):
            return result
        with open(path, "r") as f:
            r = f.read()
            result = json.loads(r)
        return result

    def getIcon(self, icon, resize=True):
        if icon not in self.icons.keys():
            # ico = QIcon(icon)
            pix = QPixmap(icon)
            # pix = ico.pixmap(32,32)
            if pix.isNull():
                # print "Null pixmap",icon,os.path.abspath(icon)
                return None
            if resize:
                pix = pix.scaled(self.iconSize, self.iconSize)
            self.icons[icon] = pix
        return self.icons[icon]

    def saveTempImage(self, pixmap, name):
        pixmap.save()

    def addSelection(self, nodes):
        if not isinstance(nodes, list):
            nodes = [nodes]
        self.selected += nodes
        for n in nodes:
            n.setSelected(True)

    def setSelection(self, nodes):
        if not isinstance(nodes, list):
            nodes = [nodes]
        for n in self.selected:
            n.setSelected(False)
        self.selected = nodes
        for n in nodes:
            n.setSelected(True)

    def removeSelection(self, nodes):
        if not isinstance(nodes, list):
            nodes = [nodes]
        for n in nodes:
            n.setSelected(False)
            listRemove(self.selected, n)

    def clearSelection(self):
        for sel in self.selected:
            sel.setSelected(False)
        self.selected = []

    def getSelectedClass(self, c):
        return [x for x in self.selected if issubclass(x.__class__, c)]


options = NodesOptions()
