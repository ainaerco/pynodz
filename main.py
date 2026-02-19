from __future__ import annotations

import sys
import logging
import os
import yaml
import inspect
import subprocess
from copy import deepcopy
from functools import partial
from typing import Any, cast

from operator import methodcaller
from qtpy.QtGui import (
    QAction,
    QShortcut,
    QImage,
    QPainter,
    QBrush,
    QColor,
    QCursor,
    QKeySequence,
    qRed,
    qGreen,
    qBlue,
    qRgb,
    QPainterPath,
    QDrag,
)
from qtpy.QtCore import (
    Qt,
    QSettings,
    QSize,
    QPoint,
    QRectF,
    QPointF,
    QByteArray,
    QTimer,
    QRect,
    QMimeData,
)
from qtpy.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QDialog,
    QFileDialog,
    QFileIconProvider,
    QGraphicsItem,
    QGraphicsPixmapItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsView,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMenu,
    QMenuBar,
    QMessageBox,
    QPushButton,
    QRubberBand,
    QSlider,
    QSplitter,
    QSystemTrayIcon,
    QTableWidget,
    QVBoxLayout,
    QWidget,
    QTableWidgetItem,
    QTableWidget,
)

import nodeUtils
from nodeUtils import NodeMimeData, mergeDicts
from nodeAttrs import NodePanel, lerp_2d_list
from nodeCommand import (
    CommandSetNodeAttribute,
    CommandCreateNode,
    CommandMoveNode,
    CommandCreateConnection,
    CommandDeleteNodes,
    CommandDeleteConnections,
)
from nodeParts.Connection import Connection

from nodeTypes import Node, NodeGroup, NodeShader, NodeBookmark

import urllib.error
import urllib.parse
import urllib.request
from bs4 import BeautifulSoup

try:
    from parseArnold import getArnoldShaders  # type: ignore[import-untyped]
except ImportError:

    def getArnoldShaders():
        return {}


from demoShaders import getDemoShaders


try:
    from rezContext import loadContext  # type: ignore[import-untyped]
except ImportError:

    def loadContext(filename):
        return {}


logging.basicConfig(
    level=logging.DEBUG,
    format="%(relativeCreated)6d %(threadName)s %(message)s",
)
log = logging.getLogger("NodeEditor")
log.setLevel(logging.DEBUG)
RECENT_FILES_COUNT = 5


def _event_pos(event: Any) -> QPoint:
    """Get position from a QDrag* or QMouse* event as QPoint."""
    pos = getattr(event, "pos", None) or getattr(event, "position", None)
    if callable(pos):
        val = pos()
        to_pt = getattr(val, "toPoint", None)
        if callable(to_pt):
            return cast(QPoint, to_pt())
        if isinstance(val, (QPoint, QPointF)):
            return QPoint(int(val.x()), int(val.y()))
    return QPoint()


def sign(x):
    return (1, 0)[x < 0]


def set_proxy(name, port):
    """Configure HTTP/HTTPS proxy via environment for urllib and similar."""
    if name and str(port).strip():
        proxy = f"{name}:{port}"
        os.environ["http_proxy"] = proxy
        os.environ["https_proxy"] = proxy
    else:
        os.environ.pop("http_proxy", None)
        os.environ.pop("https_proxy", None)


user_agent = {
    "User-Agent": "Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.0.7) Gecko/2009021910 Firefox/3.0.7"
}


def download_icon(soup, url):
    icon_link = soup.find("link", rel="shortcut icon")
    if not icon_link:
        icon_link = soup.find("link", rel="icon")
    if not icon_link:
        icon_link = soup.find("link", rel="Shortcut Icon")
    if not icon_link:
        icon_link = soup.find("link", rel="SHORTCUT ICON")
    if icon_link:
        icon_abs_link = urllib.parse.urljoin(url, icon_link["href"])
        parsed = urllib.parse.urlparse(url)
        icon_path = (parsed.hostname or "").split("www.")[-1]
        icon_path = (
            "downloads/"
            + "_".join(icon_path.split(".")[:-1])
            + "_"
            + icon_abs_link.split("/")[-1].split("?")[0]
        )
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.0.7) Gecko/2009021910 Firefox/3.0.7"
        }
        if not os.path.isfile(icon_path):
            try:
                request = urllib.request.Request(icon_abs_link, None, headers)
                icon = urllib.request.urlopen(request, timeout=10)

            except urllib.error.HTTPError:
                icon_abs_link = urllib.parse.urljoin(
                    url, "/" + icon_link["href"]
                )
                request = urllib.request.Request(icon_abs_link, None, headers)
                icon = urllib.request.urlopen(request, timeout=10)
            icon_dir = os.path.dirname(icon_path)
            if icon_dir:
                os.makedirs(icon_dir, exist_ok=True)
            with open(icon_path, "wb") as f:
                f.write(icon.read())
        return icon_path
    return None


class FilteredMenu(QMenu):
    def __init__(self, parent):
        super().__init__(parent)
        self.filterString = ""

    def keyPressEvent(self, event):  # pyright: ignore[reportIncompatibleMethodOverride]
        if event is None:
            return
        if event.key() == Qt.Key.Key_Enter or event.key() == Qt.Key.Key_Return:
            event.accept()
            super().keyPressEvent(event)
            return
        self.filterString += event.text()
        actions_old = self.actions()
        actions = []
        for a in actions_old:
            if self.filterString in str(a.text()).lower():
                actions += [QAction(a.text(), self)]
        self.clear()
        self.addSeparator()
        self.addActions(actions)
        self.move(QCursor.pos())
        super().keyPressEvent(event)


class OptionsDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Options")
        layout = QVBoxLayout(self)
        self.useProxy = QCheckBox("Use proxy")
        self.useProxy.stateChanged.connect(self.useProxyCheck)
        self.proxyName = QLineEdit()
        self.proxyPort = QLineEdit()
        self.pnLabel = QLabel("HTTP Proxy:")
        self.ppLabel = QLabel("Port:")
        label1 = QLabel("Node radius:")
        self.nodeRadius = QSlider(Qt.Orientation.Horizontal)
        self.nodeRadius.setMaximum(20)
        label2 = QLabel("Background brightness:")
        self.backBrightness = QSlider(Qt.Orientation.Horizontal)
        self.backBrightness.setValue(50)
        self.outline = QCheckBox("Node outline")
        layout.addWidget(self.useProxy)
        layout.addWidget(self.pnLabel)
        layout.addWidget(self.proxyName)
        layout.addWidget(self.ppLabel)
        layout.addWidget(self.proxyPort)
        layout.addWidget(self.outline)
        layout.addWidget(label1)
        layout.addWidget(self.nodeRadius)
        layout.addWidget(label2)
        layout.addWidget(self.backBrightness)

        self.nodeRadius.sliderMoved.connect(self.nodeRadiusChanged)
        self.backBrightness.sliderMoved.connect(self.brightChanged)
        self.readSettings()

    def nodeRadiusChanged(self, z):
        nodeUtils.options.nodeRadius = z
        p = cast(Any, self.parent())
        if p is not None and getattr(p, "viewport", None) is not None:
            p.viewport.update()

    def brightChanged(self, z):
        p = cast(Any, self.parent())
        if p is None or getattr(p, "backImage", None) is None:
            return
        img = p.backImage
        fmt = cast(Any, getattr(QImage, "Format_Indexed8", 3))
        img = img.convertToFormat(fmt)
        for i in range(img.colorCount()):
            r = qRed(img.color(i)) * z * 0.02
            g = qGreen(img.color(i)) * z * 0.02
            b = qBlue(img.color(i)) * z * 0.02
            img.setColor(i, qRgb(int(r), int(g), int(b)))
        if getattr(p, "viewport", None) is not None:
            p.viewport.setBackgroundBrush(QBrush(img))

    def readSettings(self):
        p = cast(Any, self.parent())
        if p is None or getattr(p, "settings", None) is None:
            return
        p.settings.beginGroup("MainWindow")
        state = bool(p.settings.value("use_proxy", 0))
        self.useProxy.setChecked(state)
        self.useProxyCheck(state)
        self.proxyName.setText(p.settings.value("proxy_name", ""))
        self.proxyPort.setText(p.settings.value("proxy_port", ""))
        self.nodeRadius.setValue(p.settings.value("Options.nodeRadius", 5))
        self.backBrightness.setValue(p.settings.value("back_brightness", 50))
        state = bool(p.settings.value("outline", 0))
        self.outline.setChecked(state)
        p.settings.endGroup()

    def useProxyCheck(self, state: bool):
        self.proxyName.setEnabled(state)
        self.proxyPort.setEnabled(state)
        self.pnLabel.setEnabled(state)
        self.ppLabel.setEnabled(state)

    def closeEvent(self, event):  # pyright: ignore[reportIncompatibleMethodOverride]
        if event is None:
            return
        p = cast(Any, self.parent())
        if p is None or getattr(p, "settings", None) is None:
            return
        p.settings.beginGroup("MainWindow")
        p.settings.setValue("use_proxy", self.useProxy.isChecked())
        p.settings.setValue("proxy_name", self.proxyName.text())
        proxyPort = self.proxyPort.text()
        if proxyPort:
            p.settings.setValue("proxy_port", int(proxyPort))
        p.settings.setValue("Options.nodeRadius", self.nodeRadius.value())
        p.settings.setValue("back_brightness", self.backBrightness.value())
        p.settings.setValue("outline", self.outline.isChecked())
        p.settings.endGroup()


class NodeDialog(QWidget):
    def __init__(self):
        super().__init__()
        self.filename = None
        self.shaders = None
        self.outline = False
        self._main_layout = QVBoxLayout()
        toolBox = QGroupBox()
        self.toolLayout = QHBoxLayout(toolBox)
        toolSize = QSize(25, 25)
        newButton = QPushButton(
            nodeUtils.options.getAwesomeIcon("fa6s.file"), ""
        )
        newButton.setFlat(True)
        newButton.setFixedSize(toolSize)
        newButton.setToolTip("New scene")
        self.toolLayout.addWidget(newButton)
        openButton = QPushButton(
            nodeUtils.options.getAwesomeIcon("fa6s.folder-open"), ""
        )
        openButton.setFlat(True)
        openButton.setFixedSize(toolSize)
        openButton.setToolTip("Open scene")
        self.toolLayout.addWidget(openButton)
        saveButton = QPushButton(
            nodeUtils.options.getAwesomeIcon("fa6s.floppy-disk"), ""
        )
        saveButton.setFlat(True)
        saveButton.setFixedSize(toolSize)
        saveButton.setToolTip("Save scene")
        self.toolLayout.addWidget(saveButton)
        alignVButton = QPushButton(
            nodeUtils.options.getAwesomeIcon("fa6s.arrows-up-down"), ""
        )
        alignVButton.setFlat(True)
        alignVButton.setFixedSize(toolSize)
        alignVButton.setToolTip("Align vertical")
        self.toolLayout.addWidget(alignVButton)
        alignHButton = QPushButton(
            nodeUtils.options.getAwesomeIcon("fa6s.arrows-left-right"), ""
        )
        alignHButton.setFlat(True)
        alignHButton.setFixedSize(toolSize)
        alignHButton.setToolTip("Align horizontal")
        self.toolLayout.addWidget(alignHButton)
        undoButton = QPushButton(
            nodeUtils.options.getAwesomeIcon("fa6s.rotate-left"), ""
        )
        undoButton.setFlat(True)
        undoButton.setFixedSize(toolSize)
        undoButton.setToolTip("Undo (Ctrl+Z)")
        self.toolLayout.addWidget(undoButton)
        redoButton = QPushButton(
            nodeUtils.options.getAwesomeIcon("fa6s.rotate-right"), ""
        )
        redoButton.setFlat(True)
        redoButton.setFixedSize(toolSize)
        redoButton.setToolTip("Redo (Ctrl+Y)")
        self.toolLayout.addWidget(redoButton)
        colorButton = QPushButton(
            nodeUtils.options.getAwesomeIcon("fa6s.palette"), ""
        )
        colorButton.setFlat(True)
        colorButton.setFixedSize(toolSize)
        colorButton.setToolTip("Set Color (c)")
        self.toolLayout.addWidget(colorButton)
        self.toolLayout.addStretch()
        self.searchEdit = QLineEdit()
        self.searchEdit.setFixedSize(QSize(250, 25))
        self.toolLayout.addWidget(self.searchEdit)
        searchButton = QPushButton(
            nodeUtils.options.getAwesomeIcon("fa6s.magnifying-glass"), ""
        )
        searchButton.setFlat(True)
        searchButton.setFixedSize(toolSize)
        searchButton.setToolTip("Search")
        self.toolLayout.addWidget(searchButton)
        toolBox.setMaximumHeight(48)
        self._main_layout.addWidget(toolBox)

        menuBar = QMenuBar()
        newAction = QAction("&New", self)
        newAction.setShortcut("Ctrl+N")
        newAction.triggered.connect(self.clear)
        importAction = QAction("Import", self)

        exportAction = QAction("Export", self)

        openAction = QAction("&Open", self)
        openAction.setShortcut("Ctrl+O")
        openAction.triggered.connect(self.openFile)
        saveAction = QAction("&Save", self)
        saveAction.setShortcut("Ctrl+S")
        saveAction.triggered.connect(self.saveFile)
        saveAsAction = QAction("Save as", self)
        saveAsAction.triggered.connect(self.saveFileAs)
        exitAction = QAction("&Exit", self)
        exitAction.setShortcut("Ctrl+Q")
        exitAction.setStatusTip("Exit application")
        exitAction.triggered.connect(self.close)
        fileMenu = menuBar.addMenu("File")
        if fileMenu is not None:
            fileMenu.addAction(newAction)
            fileMenu.addSeparator()
            fileMenu.addAction(openAction)
            fileMenu.addAction(saveAction)
            fileMenu.addAction(saveAsAction)
            self.recentMenu = QMenu("Recent")
            fileMenu.addMenu(self.recentMenu)
            fileMenu.addSeparator()
            fileMenu.addAction(importAction)
            fileMenu.addAction(exportAction)
            fileMenu.addAction(exitAction)
        optionsMenu = menuBar.addMenu("Options")
        self.showIconsAction = QAction("Show icons", self)
        self.showIconsAction.setCheckable(True)
        self.showIconsAction.setChecked(True)
        self.showIconsAction.triggered.connect(self.showIcons)
        self.showNamesAction = QAction("Show names", self)
        self.showNamesAction.setCheckable(True)
        self.showNamesAction.setChecked(True)
        self.showNamesAction.triggered.connect(self.showNames)
        self.showUrlsAction = QAction("Show urls", self)
        self.showUrlsAction.setCheckable(True)
        self.showUrlsAction.setChecked(True)
        self.showUrlsAction.triggered.connect(self.showUrls)
        self.showShadowsAction = QAction("Show shadows", self)
        self.showShadowsAction.setCheckable(True)
        self.showShadowsAction.setChecked(True)
        self.showShadowsAction.triggered.connect(self.showShadows)

        editConnectionAction = QAction("Connection options...", self)
        editConnectionAction.triggered.connect(self.connectionOptions)
        if optionsMenu is not None:
            optionsMenu.addAction(self.showIconsAction)
            optionsMenu.addAction(self.showNamesAction)
            optionsMenu.addAction(self.showUrlsAction)
            optionsMenu.addAction(self.showShadowsAction)
            optionsMenu.addAction(editConnectionAction)

        if hasattr(self._main_layout, "setMenuBar"):
            self._main_layout.setMenuBar(menuBar)
        self.recentFiles = []
        self.settings = QSettings("NodeBookmark Editor", "Zhuk")

        shortcut = QShortcut(QKeySequence("Del"), self)
        shortcut.activated.connect(self.delete)
        shortcut = QShortcut(QKeySequence("C"), self)
        shortcut.activated.connect(self.switchColorPicker)
        shortcut = QShortcut(QKeySequence("Ctrl+V"), self)
        shortcut.activated.connect(self.paste)
        shortcut = QShortcut(QKeySequence("Ctrl+Z"), self)
        shortcut.activated.connect(self.undo)
        shortcut = QShortcut(QKeySequence("Ctrl+Y"), self)
        shortcut.activated.connect(self.redo)
        shortcut = QShortcut(QKeySequence("Up"), self)
        shortcut.activated.connect(self.up)
        shortcut = QShortcut(QKeySequence("Down"), self)
        shortcut.activated.connect(self.down)
        shortcut = QShortcut(QKeySequence("Left"), self)
        shortcut.activated.connect(self.left)
        shortcut = QShortcut(QKeySequence("Right"), self)
        shortcut.activated.connect(self.right)
        shortcut = QShortcut(QKeySequence("F"), self)
        shortcut.activated.connect(self.zoom)
        shortcut = QShortcut(QKeySequence("Tab"), self)
        shortcut.activated.connect(self.tabCreate)

        newButton.clicked.connect(self.clear)
        openButton.clicked.connect(self.openFile)
        saveButton.clicked.connect(self.saveFile)
        alignHButton.clicked.connect(self.alignH)
        alignVButton.clicked.connect(self.alignV)
        undoButton.clicked.connect(self.undo)
        redoButton.clicked.connect(self.redo)
        colorButton.clicked.connect(self.switchColorPicker)
        searchButton.clicked.connect(self.search)
        newButton.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        # global scene
        self.scene = QGraphicsScene(0, 0, 10, 10, self)
        self.viewport = View(self)
        self.viewport.setScene(self.scene)
        self.viewport.setViewportUpdateMode(
            QGraphicsView.ViewportUpdateMode.BoundingRectViewportUpdate
        )  # BoundingRectViewportUpdate#FullViewportUpdate
        self.backImage = QImage("resources/icons/grid.png")
        rh = getattr(QPainter, "RenderHint", type("_", (), {}))
        hints = (
            getattr(rh, "Antialiasing", 0x01)
            | getattr(rh, "TextAntialiasing", 0x40)
            | getattr(rh, "SmoothPixmapTransform", 0x04)
        )
        self.viewport.setRenderHints(cast(Any, hints))
        self.viewport.setBackgroundBrush(QBrush(self.backImage))

        self.attrView = QGraphicsView(self)
        self.attrView.setMinimumWidth(200)
        self.attrView.setViewportUpdateMode(
            QGraphicsView.ViewportUpdateMode.BoundingRectViewportUpdate
        )
        self.attrView.setRenderHints(
            cast(
                Any,
                getattr(
                    getattr(
                        QPainter,
                        "RenderHint",
                        type("_", (), {"Antialiasing": 1})(),
                    ),
                    "Antialiasing",
                    0x01,
                ),
            )
        )
        self.attrView.setBackgroundBrush(QBrush(QColor(100, 100, 100)))
        self.attrScene = Scene(0, 0, 180, 500, self)
        self.attrView.setScene(self.attrScene)
        self.attrView.setAcceptDrops(True)

        self.splitter = QSplitter(self)
        self.splitter.addWidget(self.viewport)
        self.splitter.addWidget(self.attrView)
        self._main_layout.addWidget(self.splitter)
        self.splitter.splitterMoved.connect(self.splitterMoved)
        icon = nodeUtils.options.getAwesomeIcon("fa6s.diagram-project")
        self._systemIcons = QFileIconProvider()
        self.setWindowIcon(icon)
        self.setLayout(self._main_layout)
        self.readSettings()
        arnold_path = (
            "arnold.yaml" if os.path.isfile("arnold.yaml") else "arnold.json"
        )
        if os.path.isfile(arnold_path):
            with open(arnold_path, "r", encoding="utf-8") as f:
                self.shaders = yaml.safe_load(f.read()) or {}
        else:
            arnold_shaders = getArnoldShaders()
            self.shaders = (
                arnold_shaders if arnold_shaders else getDemoShaders()
            )

        self.rebuildRecentFiles()
        if self.recentFiles:
            self.openFile(self.recentFiles[0])
        self.grabber = None

    def systemIcons(self):
        return self._systemIcons

    def rebuildRecentFiles(self):
        self.recentMenu.clear()
        for f in self.recentFiles:
            action = QAction(f, self)
            action.triggered.connect(partial(self.openFile, f))
            self.recentMenu.addAction(action)

    def splitterMoved(self, pos, index):
        self.viewport.updateGeometry()
        self.attrView.updateGeometry()
        height = 0
        for item in self.attrScene.items():
            if isinstance(item, NodePanel):
                item.prepareGeometryChange()
                geom = item.geometry() if hasattr(item, "geometry") else None
                h = geom.height() if geom is not None else 0
                item.resize(self.attrView.width() - 28, h)
                item.updateItems()
                item.updateGeometry()

        self.attrView.setSceneRect(0, 0, self.attrView.width(), height)

    def mousePressEvent(self, event):  # pyright: ignore[reportIncompatibleMethodOverride]
        if event is None:
            return
        if self.grabber is not None:
            self.grabber.ungrab()
            self.releaseMouse()

    def tabCreate(self):
        menu = FilteredMenu(self)
        actions = []
        shaders_list = list((self.shaders or {}).keys())
        shaders_list.sort()
        for shader in shaders_list:
            actions += [menu.addAction(shader)]
        p = QCursor.pos()
        menuAction = menu.exec(p)
        p = self.mapFromGlobal(p)
        p = self.viewport.mapToScene(p)
        text = menuAction.text() if menuAction else None
        if menuAction and text is not None:
            shaders = self.shaders or {}
            shader = shaders.get(str(text))
            d: dict[str, Any] = {"name": str(text)}

            d["type"] = "NodeShader"
            nodeUtils.options.clearSelection()
            d["posx"] = float(p.x())
            d["posy"] = float(p.y())
            d["shader"] = str(text)
            command = CommandCreateNode(self, d)
            nodeUtils.options.undoStack.push(command)
            nodeUtils.options.setSelection(
                nodeUtils.options.nodes[command.getName()]
            )
            # nodes[self.ids].setPos(p.x(), p.y())
            # nodes[self.ids].shader = str(menuAction.text())
            # self.scene.addItem(nodes[self.ids])

    def search(self):
        nodeUtils.options.clearSelection()
        nodeUtils.options.addSelection(
            [
                n
                for n in nodeUtils.options.nodes.values()
                if str(self.searchEdit.text()).lower() in n.keywords.lower()
            ]
        )

    def zoom(self):
        if len(nodeUtils.options.selected) == 0:
            return
        r = QRectF()
        selected = [
            x for x in nodeUtils.options.selected if isinstance(x, Node)
        ]
        for s in selected:
            r = r.united(s.boundingRect().translated(s.pos()))

        v = self.viewport.visibleRect()
        self.viewport.scaleFactor = max(
            r.width() / v.width(), r.height() / v.height()
        )
        self.viewport.setSceneRect(r)
        self.viewport.scale(
            1 / self.viewport.scaleFactor, 1 / self.viewport.scaleFactor
        )

    def keyMove(self, offset):
        sel = nodeUtils.options.getSelectedClass(Node)
        if len(sel) == 0:
            return
        positions = []
        for n in sel:
            positions += [n.pos() + offset]
        cmd = nodeUtils.options.undoStack.command(
            nodeUtils.options.undoStack.count() - 1
        )
        if (
            nodeUtils.options.undoStack.count() == 0
            or cmd is None
            or type(cmd) is not CommandMoveNode
        ):
            for n in sel:
                cast(Any, n).old_pos = n.pos()
            nodeUtils.options.undoStack.push(CommandMoveNode(sel, positions))
        elif getattr(cmd, "node_ids", None) == [
            getattr(x, "name", None) for x in sel
        ]:
            nodeUtils.options.undoStack.undo()
            nodeUtils.options.undoStack.push(CommandMoveNode(sel, positions))

    def up(self):
        self.keyMove(QPointF(0, -5))

    def down(self):
        self.keyMove(QPointF(0, 5))

    def left(self):
        self.keyMove(QPointF(-5, 0))

    def right(self):
        self.keyMove(QPointF(5, 0))

    def trayIconClick(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.isVisible():
                self.hide()
            else:
                self.show()
        elif reason == QSystemTrayIcon.ActivationReason.Context:
            menu = QMenu(self)
            exitAction = menu.addAction("Exit")
            action = menu.exec(QCursor.pos())
            if action == exitAction:
                self.close()

    def connectionOptions(self):
        self.options = OptionsDialog(self)
        self.options.show()

    def _refreshOptionsVisibility(self):
        """Apply Options menu state to all nodes and force a repaint."""
        self._applyOptionsVisibilityToScene()

    def _applyOptionsVisibilityToScene(
        self,
        show_icons=None,
        show_names=None,
        show_urls=None,
    ):
        """Apply Options menu visibility to all NodeBookmark nodes and force repaint."""
        if show_icons is None:
            show_icons = self.showIconsAction.isChecked()
        if show_names is None:
            show_names = self.showNamesAction.isChecked()
        if show_urls is None:
            show_urls = self.showUrlsAction.isChecked()
        # Use options.nodes (source of truth); nodes are the same objects as in the scene.
        # Do setRect first (layout), then set visibility so NodeBookmark.setRect doesn't overwrite us.
        for n in nodeUtils.options.nodes.values():
            if not isinstance(n, NodeBookmark):
                continue
            n.prepareGeometryChange()
            n.setRect(n._rect)
            # Apply visibility after setRect so it isn't overwritten by setRect reading action state.
            # Hide all pixmap children in the icon zone (top-left); catches iconItem and any duplicate.
            for child in n.childItems():
                if isinstance(child, QGraphicsPixmapItem):
                    try:
                        p = child.pos()
                        if p.x() < 40 and p.y() < 40:
                            child.setVisible(show_icons)
                            child.update()
                    except Exception:
                        pass
            name_item = getattr(n, "nameItem", None)
            if name_item is not None:
                name_item.setVisible(show_names)
                name_item.update()
            url_item = getattr(n, "urlItem", None)
            if url_item is not None:
                url_item.setVisible(show_urls)
                url_item.update()
            n.update()
        self.scene.update(self.scene.sceneRect())
        vp = self.viewport.viewport()
        if vp is not None:
            vp.update(0, 0, vp.width(), vp.height())
        # Force view to redraw
        old_mode = self.viewport.viewportUpdateMode()
        self.viewport.setViewportUpdateMode(
            QGraphicsView.ViewportUpdateMode.FullViewportUpdate
        )
        vp_widget = self.viewport.viewport()
        if vp_widget is not None:
            vp_widget.update()
        self.viewport.setViewportUpdateMode(old_mode)

    def showIcons(self, checked):
        self._applyOptionsVisibilityToScene(show_icons=checked)

    def showNames(self, checked):
        self._applyOptionsVisibilityToScene(show_names=checked)

    def showUrls(self, checked):
        self._applyOptionsVisibilityToScene(show_urls=checked)

    def showShadows(self, checked):
        if checked:
            for n in nodeUtils.options.nodes.values():
                n.addShadow()
        else:
            for n in nodeUtils.options.nodes.values():
                n.shadow.setColor(QColor(0, 0, 0, 0))

    def setStyleSheet(self, fname):  # pyright: ignore[reportIncompatibleMethodOverride]
        if not fname or not os.path.isfile(fname):
            return
        with open(fname, "r", encoding="utf-8") as f:
            super().setStyleSheet(f.read())

    def writeSettings(self):
        self.settings.beginGroup("MainWindow")
        self.settings.setValue("size", self.size())
        self.settings.setValue("pos", self.pos())
        self.settings.setValue("show_icons", self.showIconsAction.isChecked())
        self.settings.setValue("show_names", self.showNamesAction.isChecked())
        self.settings.setValue("show_urls", self.showUrlsAction.isChecked())
        self.settings.setValue(
            "show_shadows", self.showShadowsAction.isChecked()
        )
        self.settings.setValue("splitter", self.splitter.sizes())
        self.settings.endGroup()
        self.settings.setValue("recent", self.recentFiles)

    def readSettings(self):
        self.settings.beginGroup("MainWindow")
        self.resize(self.settings.value("size", QSize(400, 400)))
        self.move(self.settings.value("pos", QPoint(200, 200)))
        split = self.settings.value("splitter", [100, 300])
        split = [int(x) for x in split]
        self.splitter.setSizes(split)
        c = bool(self.settings.value("show_icons", True))
        self.showIcons(c)
        self.showIconsAction.setChecked(c)
        c = bool(self.settings.value("show_names", True))
        self.showNames(c)
        self.showNamesAction.setChecked(c)
        c = bool(self.settings.value("show_urls", True))
        self.showUrls(c)
        self.showUrlsAction.setChecked(c)
        c = bool(self.settings.value("show_shadows", True))
        self.showShadowsAction.setChecked(c)

        if self.settings.value("use_proxy", 0):
            proxy_name = self.settings.value("proxy_name", "")
            proxy_port = self.settings.value("proxy_port", "")
            set_proxy(proxy_name, proxy_port)
        nodeUtils.options.nodeRadius = int(
            self.settings.value("Options.nodeRadius", 5) or 5
        )
        z = int(self.settings.value("back_brightness", 50) or 50)
        if z != 50:
            img = self.backImage
            fmt = cast(Any, getattr(QImage, "Format_Indexed8", 3))
            img = img.convertToFormat(fmt)
            for i in range(img.colorCount()):
                r = qRed(img.color(i)) * z * 0.02
                g = qGreen(img.color(i)) * z * 0.02
                b = qBlue(img.color(i)) * z * 0.02
                img.setColor(i, qRgb(int(r), int(g), int(b)))
            self.viewport.setBackgroundBrush(QBrush(img))
        self.outline = bool(self.settings.value("outline", True))
        self.settings.endGroup()
        self.recentFiles = self.settings.value("recent", [])

    def undo(self):
        nodeUtils.options.undoStack.undo()

    def redo(self):
        nodeUtils.options.undoStack.redo()

    def alignH(self):
        sel = nodeUtils.options.getSelectedClass(Node)
        if len(sel) == 0:
            return
        y = sel[0].pos().y()
        for n in sel:
            y = (y + n.pos().y()) / 2.0
        positions = []
        for n in sel:
            n.old_pos = n.pos()
            positions += [QPointF(n.pos().x(), y)]
        nodeUtils.options.undoStack.push(CommandMoveNode(sel, positions))

    def alignV(self):
        sel = nodeUtils.options.getSelectedClass(Node)
        if len(sel) == 0:
            return
        x = sel[0].pos().x()
        for n in sel:
            x = (x + n.pos().x()) / 2.0
        positions = []
        for n in sel:
            n.old_pos = n.pos()
            positions += [QPointF(x, n.pos().y())]
        nodeUtils.options.undoStack.push(CommandMoveNode(sel, positions))

    def addBookmark(self, d):
        url = (d.get("url") or "").strip()
        if not url.lower().startswith(("http://", "https://")):
            log.warning(
                "addBookmark: invalid or non-HTTP(S) URL: %r", url or "(empty)"
            )
            return
        req = urllib.request.Request(url, headers=user_agent)
        response = urllib.request.urlopen(req, timeout=10)
        page = response.read()
        soup = BeautifulSoup(page, features="html.parser")
        page = page.lower()
        d["type"] = "NodeBookmark"
        if soup.title:
            d["name"] = soup.title.string
        else:
            d["name"] = "NodeBookmark"
        keywords = [
            x.get("content")
            for x in soup.find_all("meta", attrs={"name": "keywords"})
        ]
        if keywords:
            keywords = keywords[0]
            keywords = [
                x.strip()
                for x in (str(keywords).split(",") if keywords else [])
            ]
            d["keywords"] = "\n".join(keywords).lower()  # .encode("utf-8")
        icon = download_icon(soup, url)
        if icon:
            d["icon"] = icon
        nodeUtils.options.clearSelection()
        command = CommandCreateNode(self, d)
        nodeUtils.options.undoStack.push(command)
        nodeUtils.options.setSelection(
            nodeUtils.options.nodes[command.getName()]
        )

    def paste(self):
        p = QCursor.pos()
        p = self.mapFromGlobal(p)
        p = self.viewport.mapToScene(p)

        d = {
            "posx": p.x(),
            "posy": p.y(),
            "url": "%s"
            % (
                (lambda c: c.text() if c and hasattr(c, "text") else "")(
                    QApplication.clipboard()
                )
            ),
        }
        self.addBookmark(d)

    def switchColorPicker(self):
        if nodeUtils.options.colorPicker:
            self.scene.removeItem(nodeUtils.options.colorPicker)
            nodeUtils.options.colorPicker = None
        else:
            picker = ColorPicker()
            setattr(nodeUtils.options, "colorPicker", picker)
            self.viewport.updateColorPicker()
            self.scene.addItem(picker)

    def openFile(self, f=None):
        if not f:
            f, _mask = QFileDialog.getOpenFileName(
                self,
                "Open File",
                "",
                "Node Files (*.nod);;Context Files (*.rxt);;",
            )
        if f and os.path.isfile(f):
            if f not in self.recentFiles:
                if len(self.recentFiles) >= RECENT_FILES_COUNT:
                    self.recentFiles.pop()
                self.recentFiles.insert(0, f)
                self.rebuildRecentFiles()
            self.filename = str(f)
            # global nodes
            # global connections

            self.clear()
            op_file = None
            if os.path.splitext(self.filename)[-1] == ".rxt":
                dump = loadContext(self.filename)
            else:
                with open(self.filename, "r", encoding="utf-8") as op_file:
                    text = op_file.read()

                # Strip control chars that PyYAML rejects (e.g. 0x009b / ANSI remnants)
                def _yaml_safe(c):
                    o = ord(c)
                    if o in (9, 10, 13):
                        return True
                    if o < 32 or o == 0x7F:
                        return False
                    if 0x80 <= o <= 0x9F:
                        return False
                    if 0xD800 <= o <= 0xDFFF or o in (0xFFFE, 0xFFFF):
                        return False
                    return True

                text = "".join(c for c in text if _yaml_safe(c))
                dump = yaml.safe_load(text)
            ids = -1
            if isinstance(dump["nodes"], dict):
                for key in dump["nodes"].keys():
                    d = dump["nodes"][key]
                    ids = max(ids, d["id"])
                    # d['display_name'] = d['name'].rstrip("0123456789")
                    nodeUtils.options.undoStack.push(CommandCreateNode(self, d))
            elif isinstance(dump["nodes"], list):
                for d in dump["nodes"]:
                    ids = max(ids, d["id"])
                    # d['display_name'] = d['name'].rstrip("0123456789")
                    nodeUtils.options.undoStack.push(CommandCreateNode(self, d))
            if "connections" in dump.keys():
                for d in dump["connections"]:
                    ids = max(ids, d["id"])
                    nodeUtils.options.undoStack.push(
                        CommandCreateConnection(self.scene, d)
                    )
            for n in nodeUtils.options.nodes.values():
                if n.collapsed is True:
                    n.setCollapsed(False)
            self._refreshOptionsVisibility()
            nodeUtils.options.setIds(ids)
            # if 'ids' in dump.keys():
            #     self.ids = dump['ids']
            # else:
            #     self.ids = len(nodes)+len(connections)
            if "viewport" in dump.keys():
                self.viewport.setSceneRect(
                    dump["viewport"]["left"],
                    dump["viewport"]["top"],
                    dump["viewport"]["width"],
                    dump["viewport"]["height"],
                )
                self.viewport.scaleFactor = dump["viewport"]["scaleFactor"]
                self.viewport.scale(
                    1 / self.viewport.scaleFactor, 1 / self.viewport.scaleFactor
                )
            if op_file:
                op_file.close()
            self.setWindowTitle("Node Editor - %s" % self.filename)

    def saveFile(self):
        if not self.filename:
            return
        try:
            save_nodes = {}
            for nv in nodeUtils.options.nodes.values():
                d = nv.toDict()
                save_nodes[d["name"]] = d
            save_connections = []
            for nc in nodeUtils.options.connections.values():
                save_connections += [nc.toDict()]
            rect = self.viewport.sceneRect()
            r = {
                "left": rect.left(),
                "top": rect.top(),
                "width": rect.width(),
                "height": rect.height(),
                "scaleFactor": self.viewport.scaleFactor,
            }
            dump = {
                "nodes": save_nodes,
                "viewport": r,
                "connections": save_connections,
            }
            data = yaml.dump(
                dump,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
            )
            with open(self.filename, "w", encoding="utf-8") as f:
                f.write(data)

            nodeUtils.options.undoStack.clear()
        except Exception as e:
            messageBox = QMessageBox()
            messageBox.critical(self, "Error", "An error has occured !\n%s" % e)
            messageBox.setFixedSize(500, 200)

    def saveFileAs(self):
        self.filename, pattern = QFileDialog.getSaveFileName(
            self, "Save File", "", "NodeBookmark Files (*.nod)"
        )
        if self.filename:
            self.saveFile()
            self.setWindowTitle("NodeBookmark Editor - %s" % self.filename)
            nodeUtils.options.undoStack.clear()

    def clear(self):
        self.setWindowTitle("NodeBookmark Editor")
        # global connections

        nodeUtils.options.selected = []
        nodeUtils.options.clearNodes()
        # self.ids = -1
        nodeUtils.options.setIds(-1)
        nodeUtils.options.clearConnections()
        nodeUtils.options.undoStack.clear()
        self.scene.clear()

    def delete(self):
        del_nodes = nodeUtils.options.getSelectedClass(Node)
        if len(del_nodes) > 0:
            nodeUtils.options.clearSelection()
            nodeUtils.options.undoStack.push(
                CommandDeleteNodes(self, del_nodes)
            )
        del_conns = nodeUtils.options.getSelectedClass(Connection)
        if len(del_conns) > 0:
            nodeUtils.options.clearSelection()
            nodeUtils.options.undoStack.push(
                CommandDeleteConnections(self.scene, del_conns)
            )

    def closeEvent(self, event):  # pyright: ignore[reportIncompatibleMethodOverride]
        if event is None:
            return
        """
        if nodeUtils.options.undoStack.count() > 0:
            ret = QMessageBox(
                QMessageBox.Information,
                "Save Changes",
                "Save changes to\n%s" % self.filename,
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            ).exec()
            if QMessageBox.Yes == ret:
                self.saveFile()
            elif QMessageBox.Cancel == ret:
                event.ignore()
        """
        nodeUtils.options.saveArnoldSettings()
        nodeUtils.options.undoStack.clear()
        self.writeSettings()
        for d in self.findChildren(QDialog):
            # print d
            d.close()


class Scene(QGraphicsScene):
    def __init__(self, *args):
        super().__init__(*args)

    def dragEnterEvent(self, event):
        if event is None:
            return
        items = self.items(event.scenePos())
        if len(items) == 0:
            return
        items.sort(key=methodcaller("zValue"))
        maxZ = 0  # items[-1].zValue()
        for item in [
            x for x in items if x.acceptDrops() and x.zValue() >= maxZ
        ]:
            item.dragEnterEvent(event)
        event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event is None:
            return
        items = self.items(event.scenePos())
        if len(items) == 0:
            return
        items.sort(key=methodcaller("zValue"))
        maxZ = 0
        for item in [
            x for x in items if x.acceptDrops() and x.zValue() >= maxZ
        ]:
            item.dragMoveEvent(event)
        event.acceptProposedAction()

    def dropEvent(self, event):
        if event is None:
            return
        items = self.items(event.scenePos())
        if len(items) == 0:
            return
        items.sort(key=methodcaller("zValue"))
        maxZ = 0  # items[-1].zValue()
        for item in [
            x for x in items if x.acceptDrops() and x.zValue() >= maxZ
        ]:
            item.dropEvent(event)

    def contextMenuEvent(self, event):
        if len(nodeUtils.options.selected) == 0:
            return
        n = nodeUtils.options.selected[-1]
        if not isinstance(n, NodeShader):
            return

        super().contextMenuEvent(event)
        if event is not None and event.isAccepted():
            return
        parent = self.parent()
        menu = QMenu(cast(Any, parent))
        setdef = menu.addAction("Set as default")
        revert = menu.addAction("Revert to defaults")

        action = menu.exec(QCursor.pos())
        if action == setdef:
            attrs = [
                x
                for x in n.attributes.values()
                if x.attr["default"] != x._value
            ]
            for a in attrs:
                nodeUtils.options.arnold = dict(
                    mergeDicts(
                        nodeUtils.options.arnold,
                        {
                            n.shader: {
                                a.attr["name"]: {"_default": a.attr["default"]}
                            }
                        },
                    )
                )
        elif action == revert:
            attrs = [
                x
                for x in n.attributes.values()
                if x.attr["default"] != x._value
            ]
            if len(attrs) == 0:
                return
            v = {}
            for a in attrs:
                a.setDefault()
                if isinstance(a.value, list):
                    v[a.attr["name"]] = deepcopy(a.value)
                else:
                    v[a.attr["name"]] = a.value
            # print n.values
            # print v,"updateAttribute"
            nodeUtils.options.undoStack.push(
                CommandSetNodeAttribute([n], {"values": v})
            )


class View(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.dialog = parent
        self.old_pos = QPoint(0, 0)
        self.origin = QPoint(0, 0)
        self.scaleFactor = 1.0
        rb_shape = cast(
            Any,
            getattr(
                getattr(
                    QRubberBand,
                    "Shape",
                    type("_", (), {"Rectangle": 0})(),
                ),
                "Rectangle",
                0,
            ),
        )
        self.rubberband = QRubberBand(rb_shape, self)
        self.temp_connection = None
        self.setAcceptDrops(True)

    def visibleRect(self):
        vp = self.viewport()
        tl = QPoint()
        br = vp.rect().bottomRight() if vp else QPoint()
        return self.mapToScene(QRect(tl, br)).boundingRect()

    def updateColorPicker(self):
        if nodeUtils.options.colorPicker:
            z = self.mapToScene(QPoint(0, self.height()))
            nodeUtils.options.colorPicker.prepareGeometryChange()
            nodeUtils.options.colorPicker.setPos(
                z.x(),
                z.y() - nodeUtils.options.colorPicker.boundingRect().height(),
            )
            nodeUtils.options.colorPicker.setScale(self.scaleFactor)

    def resizeEvent(self, event):
        self.updateColorPicker()

    def wheelEvent(self, event):
        if len(nodeUtils.options.selected) == 1 and isinstance(
            nodeUtils.options.selected[0], Node
        ):
            n = nodeUtils.options.selected[0]
            n.prepareGeometryChange()

            if (
                QApplication.keyboardModifiers()
                & Qt.KeyboardModifier.ControlModifier
            ):
                angle_delta = getattr(event, "angleDelta", None)
                if callable(angle_delta):
                    angle_delta = angle_delta()
                d_y = (
                    cast(Any, angle_delta).y() if angle_delta is not None else 0
                )
                n.setScale((d_y > 0 and n.scale() * 1.1) or n.scale() * 0.9)
                return
            elif (
                QApplication.keyboardModifiers()
                & Qt.KeyboardModifier.ShiftModifier
            ):
                angle_delta = getattr(event, "angleDelta", None)
                if callable(angle_delta):
                    angle_delta = angle_delta()
                delta = angle_delta
                if delta is not None and cast(Any, delta).y() > 0:
                    n.setRotation(n.rotation() + 10)
                else:
                    n.setRotation(n.rotation() - 10)
                for c in n.connections:
                    c.prepareGeometryChange()
                    c.updatePath()
                    c.update()
                return

        scalingFactor = 1.15
        angle_delta = getattr(event, "angleDelta", None)
        if callable(angle_delta):
            angle_delta = angle_delta()
        delta = angle_delta
        if delta is not None and cast(Any, delta).y() > 0:
            self.scale(scalingFactor, scalingFactor)
            self.scaleFactor /= scalingFactor
        else:
            self.scaleFactor *= scalingFactor
            scalingFactor = 1.0 / scalingFactor
            self.scale(scalingFactor, scalingFactor)
        self.updateColorPicker()

    def mousePressEvent(self, event):
        if event is None:
            return
        if event.buttons() & Qt.MouseButton.MiddleButton:
            drag = QDrag(self.parent())
            mime = QMimeData()
            mime.setData("scene/move", QByteArray())
            drag.setMimeData(mime)
            drag.exec(Qt.DropAction.MoveAction)
        elif (
            event.buttons() & Qt.MouseButton.LeftButton
            and len(self.items(event.pos())) == 0
        ):
            drag = QDrag(self.parent())
            mime = QMimeData()
            mime.setData("scene/rubberband", QByteArray())
            drag.setMimeData(mime)
            drag.exec(Qt.DropAction.MoveAction)
        super().mousePressEvent(event)

    def dragEnterEvent(self, event):
        if event is None:
            return
        self.mouse_stack = [QPoint()] * 20
        p = _event_pos(event)
        self.old_pos = p
        self.origin = p
        mime = event.mimeData()
        if mime is None:
            return

        if mime.hasFormat("node/connect"):
            n = cast(NodeMimeData, mime).getObject()
            if n is None or not getattr(n, "connector", None):
                log.error("dragEnterEvent: node '%r' has no connector", n)
            else:
                ep = _event_pos(event)
                self.temp_connection = Connection(
                    {
                        "parent": n.pos() + n.connector.pos(),
                        "child": self.mapToScene(cast(Any, ep)),
                        "constrain": False,
                    }
                )
                scene = self.scene()
                if scene is not None:
                    scene.addItem(self.temp_connection)
        elif mime.hasFormat("node/move"):
            for sel in nodeUtils.options.selected:
                cast(Any, sel).old_pos = sel.pos()
            sel = cast(NodeMimeData, mime).getObject()
            if sel is not None and type(sel) is NodeGroup:
                sel_ = cast(Any, sel)
                rect = QRectF(
                    sel_.pos().x(),
                    sel_.pos().y(),
                    sel_._rect.width(),
                    sel_._rect.height(),
                )
                scene = self.scene()
                childs_list = (
                    scene.items(
                        rect,
                        Qt.ItemSelectionMode.IntersectsItemShape,
                        Qt.SortOrder.DescendingOrder,
                    )
                    if scene
                    else []
                )
                sel_.childs = [
                    x for x in childs_list if isinstance(x, Node) and x != sel
                ]
                for x in sel_.childs:
                    cast(Any, x).old_pos = x.pos()
            nmime = cast(NodeMimeData, mime)
            if getattr(nmime, "origin", None) is not None:
                self.origin = nmime.origin
            else:
                self.origin = self.mapToScene(self.old_pos)
        elif mime.hasUrls():
            nodeUtils.options.clearSelection()
        elif mime.hasFormat("scene/rubberband"):
            ep = _event_pos(event)
            self.rubberband.setGeometry(
                QRect(
                    cast(QPoint, self.old_pos),
                    cast(QPoint, ep),
                ).normalized()
            )
            self.rubberband.show()
        else:
            self.rubberband.hide()

        super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event is None:
            return
        mime = event.mimeData()
        if mime is None:
            return
        ep = _event_pos(event)
        if mime.hasFormat("scene/rubberband"):
            self.rubberband.setGeometry(QRect(self.old_pos, ep).normalized())
            return
        elif mime.hasFormat("scene/move"):
            p = QPointF(
                float(self.old_pos.x() - ep.x()),
                float(self.old_pos.y() - ep.y()),
            )
            r = self.sceneRect()
            r.translate(p * self.scaleFactor)
            self.setSceneRect(r)
            self.updateColorPicker()
            self.old_pos = ep
            return
        elif mime.hasFormat("node/connect"):
            if self.temp_connection:
                self.temp_connection.prepareGeometryChange()
                self.temp_connection.child = self.mapToScene(ep)
                self.temp_connection.prepareGeometryChange()
                self.temp_connection.updatePath()
                self.temp_connection.update()

            super().dragMoveEvent(event)
            event.acceptProposedAction()
            return
        elif mime.hasFormat("node/resize"):
            sel = cast(NodeMimeData, mime).getObject()
            if sel is not None:
                res = (ep - self.old_pos) * self.scaleFactor
                sany = cast(Any, sel)
                sany.prepareGeometryChange()
                sany.resize(
                    sany._rect.width() + res.x(),
                    sany._rect.height() + res.y(),
                )
                sany.updateGeometry()
            self.old_pos = ep
            return
        elif mime.hasFormat("node/move"):
            origin_pt = (
                self.origin
                if isinstance(self.origin, QPointF)
                else self.mapToScene(cast(Any, self.origin))
            )
            scene = self.scene()
            for sel in nodeUtils.options.selected:
                sel_any = cast(Any, sel)
                if type(sel) is NodeGroup:
                    for x in getattr(sel_any, "childs", []):
                        pos = self.mapToScene(cast(Any, ep))
                        pos = pos - origin_pt
                        pos = pos + cast(Any, x).old_pos
                        x.setPos(pos.x(), pos.y())
                if isinstance(sel, Node):
                    p_pt = (
                        self.mapToScene(cast(Any, ep))
                        - origin_pt
                        + sel_any.old_pos
                    )
                    sel.setPos(p_pt.x(), p_pt.y())
            return
        event.accept()
        super().dragMoveEvent(event)
        return

        # Disconnect node behavior
        if len(nodeUtils.options.selected) == 1 and isinstance(
            nodeUtils.options.selected[0], Node
        ):
            sel = nodeUtils.options.selected[0]
            self.mouse_stack.append((event.pos() - self.old_pos))
            del self.mouse_stack[0]
            state = 0
            state_value = 0
            # detect erratically movement
            for i in range(len(self.mouse_stack)):
                if state == 0 and abs(self.mouse_stack[i].x()) > 10:
                    state = i
                    state_value = sign(self.mouse_stack[i].x())
                if (
                    i - state < 7
                    and abs(self.mouse_stack[i].x()) > 10
                    and state_value != sign(self.mouse_stack[i].x())
                ):
                    state = -1
            if state == -1 and len(sel.connections) > 0:
                nodeUtils.options.undoStack.push(
                    CommandDeleteConnections(self.scene(), sel.connections)
                )
                self.mouse_stack = [QPoint()] * 20
            self.old_pos = event.pos()

    def dragLeaveEvent(self, event):
        self.rubberband.hide()
        if self.temp_connection:
            scene = self.scene()
            if scene is not None:
                scene.removeItem(self.temp_connection)
            self.temp_connection = None
        super().dragLeaveEvent(event)

    def dropEvent(self, event):
        if event is None:
            return
        mime = event.mimeData()
        if mime is None:
            return

        if self.temp_connection:
            scene = self.scene()
            if scene is not None:
                scene.removeItem(self.temp_connection)
            self.temp_connection = None

        elif mime.hasFormat("node/move"):
            positions = []
            sel_nodes = []
            for sel in nodeUtils.options.getSelectedClass(Node):
                sel_nodes += [sel]
                positions += [sel.pos()]
            if len(sel_nodes) > 0:
                nodeUtils.options.undoStack.push(
                    CommandMoveNode(sel_nodes, positions)
                )
            ep = _event_pos(event)
            for item in self.items(ep):
                if (
                    not isinstance(item, Node)
                    or (item in nodeUtils.options.selected)
                    or type(item) is NodeGroup
                ):
                    continue
                selected = nodeUtils.options.selected
                nodeUtils.options.clearSelection()
                nodeUtils.options.undoStack.undo()
                for s in selected:
                    if not isinstance(s, Node):
                        continue
                    d = {
                        "name": "Connection",
                        "parent": getattr(item, "id", None),
                        "child": getattr(s, "id", None),
                    }

                    nodeUtils.options.undoStack.push(
                        CommandCreateConnection(self.scene(), d)
                    )
        elif mime.hasFormat("scene/rubberband"):
            self.rubberband.hide()
            rect = self.rubberband.geometry()
            sel = [
                x
                for x in self.items(rect)
                if isinstance(x, Node) or type(x) is Connection
            ]
            nodeUtils.options.setSelection(sel)
            return
        elif mime.hasFormat("node/connect"):
            item = cast(NodeMimeData, mime).getObject()
            ep = _event_pos(event)
            s = self.items(ep)
            if s and len(s) > 0:
                first = s[0]
                d = {
                    "name": "Connection",
                    "parent": getattr(item, "id", None),
                    "child": getattr(first, "id", None),
                }
                scene = self.scene()
                if scene is not None:
                    nodeUtils.options.undoStack.push(
                        CommandCreateConnection(scene, d)
                    )

        super().dropEvent(event)

    def contextMenuEvent(self, event):
        if event is None:
            return
        ep = _event_pos(event)
        for item in self.items(ep):
            if isinstance(item, Node) or type(item) is Connection:
                super().contextMenuEvent(event)
                return
        menu = QMenu(self)
        newNodeAction = menu.addAction("New node")
        newBookmarkAction = menu.addAction("New bookmark")
        newNoteAction = menu.addAction("New note")
        newGroupAction = menu.addAction("New group")
        newControlAction = menu.addAction("New control")
        newBlockAction = menu.addAction("New block")
        menu.addSeparator()
        action = menu.exec(self.mapToGlobal(ep))
        p_pt = self.mapToScene(ep)
        d: dict[str, Any] = {"posx": p_pt.x(), "posy": p_pt.y()}
        command = None
        if action == newNodeAction:
            d["type"] = "Node"
            d["name"] = "Node"
        elif action == newBookmarkAction:
            d["type"] = "NodeBookmark"
            d["name"] = "Bookmark"
        elif action == newNoteAction:
            d["type"] = "NodeNote"
            d["name"] = "Note"
        elif action == newGroupAction:
            d["type"] = "NodeGroup"
            d["name"] = "Group"
        elif action == newControlAction:
            d["type"] = "NodeControl"
            d["name"] = "Control"
        elif action == newBlockAction:
            d["type"] = "NodeBlock"
            d["name"] = "Block"

        if "name" in d:
            nodeUtils.options.clearSelection()
            command = CommandCreateNode(self.dialog, d)
            nodeUtils.options.undoStack.push(command)
            nodeUtils.options.setSelection(
                nodeUtils.options.nodes[command.getName()]
            )


class ColorPicker(QGraphicsItem):
    def __init__(self):
        super().__init__()
        self.setZValue(2)

        ncolors = 30
        nrows = 1
        ncols = ncolors / nrows
        size = 16
        self.rect = QRectF(0, 0, size, ncols * (size + 2))
        self.colors = []
        self.setTransformOriginPoint(self.rect.bottomLeft())

        for i in range(ncolors):
            item = ColorPickerItem(0, 0, size, size, self)
            color = QColor()
            color.setHsv(int(i / float(ncolors) * 359), 150, 250)
            item.setBrush(QBrush(color))
            item.setPos(0, i / nrows * (size + 2))
            self.colors += [item]

    def boundingRect(self):
        return self.rect

    def paint(self, painter, option, widget=None):  # pyright: ignore[reportIncompatibleMethodOverride]
        if painter is None:
            return
        pass


class ColorPickerItem(QGraphicsRectItem):
    def __init__(self, *args):
        super().__init__(*args)

    def mousePressEvent(self, event):
        if event is None or event.button() != Qt.MouseButton.LeftButton:
            if event is not None:
                event.ignore()
            return

        nodeUtils.options.undoStack.push(
            CommandSetNodeAttribute(
                nodeUtils.options.getSelectedClass(Node),
                {"rgb": self.brush().color().name()},
            )
        )

        scene = self.scene()
        if scene is not None and nodeUtils.options.colorPicker is not None:
            scene.removeItem(nodeUtils.options.colorPicker)
        nodeUtils.options.colorPicker = None


callGraph = None


def str_to_obj(astr):
    try:
        return globals()[astr]
    except KeyError:
        try:
            __import__(astr)
            mod = sys.modules[astr]
            return mod
        except ImportError:
            module, _, basename = astr.rpartition(".")
            if module:
                mod = str_to_obj(module)
                return getattr(mod, basename)
            else:
                raise


class PerfomanceGraph(QGraphicsItem):
    def __init__(self, *args):
        super().__init__(*args)
        self.rect = QRectF()
        self.path = QPainterPath()

    def boundingRect(self):
        return self.rect

    def updatePath(self, li):
        self.prepareGeometryChange()
        self.path = QPainterPath()
        scene = self.scene()
        views = scene.views() if scene else []
        scene_height = float(views[0].height()) if views else 100.0
        max_li = 0.5
        v = lerp_2d_list((0, max_li), (scene_height, 100), li[0])
        self.path.moveTo(0, v)
        for i in range(1, len(li)):
            v = lerp_2d_list((0, max_li), (scene_height, 100), li[i])
            self.path.lineTo(i * 5, v)
        self.rect = self.path.boundingRect()
        self.update()

    def paint(self, painter, option, widget=None):  # pyright: ignore[reportIncompatibleMethodOverride]
        if painter is not None:
            painter.drawPath(self.path)


def _default_source_editor_template():
    """Cross-platform default: use EDITOR/VISUAL env if set, else empty (user sets via 'Set editor')."""
    editor = (
        os.environ.get("VISUAL") or os.environ.get("EDITOR") or ""
    ).strip()
    if editor:
        return editor + ' "%(source)s":%(line)d'
    return ""


class CallDialog(QDialog):
    def __init__(self, parent=None, callGraph=None):
        super().__init__(parent)
        self.callGraph = callGraph
        self.timer = QTimer()
        menuBar = QMenuBar()
        optionsMenu = menuBar.addMenu("nodeUtils.options")
        self.drawPerfomanceOption = QAction("View perfomance", self)
        self.drawPerfomanceOption.setCheckable(True)
        self.drawPerfomanceOption.triggered.connect(self.switchGraph)
        self.sourceEditorOption = QAction("Set editor", self)
        self.sourceEditorOption.triggered.connect(self.setSourceEditor)
        if optionsMenu is not None:
            optionsMenu.addAction(self.drawPerfomanceOption)
            optionsMenu.addAction(self.sourceEditorOption)

        self.sourceEditor = _default_source_editor_template()

        layout = QVBoxLayout()
        self.setLayout(layout)
        layout.setMenuBar(menuBar)
        self.table = QTableWidget(200, 4)
        self.table.setHorizontalHeaderLabels(
            ["Method", "Calls", "Time", "Time per call"]
        )
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)
        self.button = QPushButton("Start timer")

        self.view = QGraphicsView(self)
        self.view.setMinimumWidth(200)
        self.view.setViewportUpdateMode(
            QGraphicsView.ViewportUpdateMode.MinimalViewportUpdate
        )
        self.view.setRenderHints(
            QPainter.RenderHint.Antialiasing
            | QPainter.RenderHint.SmoothPixmapTransform
        )
        self.view.setBackgroundBrush(QBrush(QColor(100, 100, 100)))
        self.scene = QGraphicsScene(0, 0, 180, 500, self)
        self.view.setScene(self.scene)
        self.view.setAcceptDrops(True)

        self.perfList = []
        self.perfGraph = PerfomanceGraph()
        self.previousTime = 0
        self.scene.addItem(self.perfGraph)

        self.splitter = QSplitter(self)
        self.splitter.addWidget(self.table)
        self.splitter.addWidget(self.view)
        layout.addWidget(self.splitter)
        layout.addWidget(self.button)

        self.settings = QSettings("PiTools", "Vulturizer")
        self.splitter.splitterMoved.connect(self.splitterMoved)
        self.timer.timeout.connect(self.timerEvent)
        self.button.clicked.connect(self.switchTimer)
        self.table.cellDoubleClicked.connect(self.itemClick)
        self.setLayout(layout)

        self.loadSettings()
        self.timerEvent()

    def splitterMoved(self, pos, index):
        self.view.updateGeometry()
        self.view.setSceneRect(0, 0, self.view.width(), self.view.height())

    def switchGraph(self):
        self.view.setVisible(self.drawPerfomanceOption.isChecked())

    def switchTimer(self):
        if not self.timer.isActive():
            self.button.setText("Stop timer")
            self.timer.start(200)
        else:
            self.button.setText("Start timer")
            self.timer.stop()

    def closeEvent(self, event):  # pyright: ignore[reportIncompatibleMethodOverride]
        self.saveSettings()
        super().closeEvent(event)

    def setSourceEditor(self):
        text = QInputDialog.getText(
            self,
            "Set editor",
            "Command template (%(source)s = file, %(line)d = line):",
            QLineEdit.EchoMode.Normal,
            self.sourceEditor,
        )
        if text:
            self.sourceEditor = str(text[0])

    def saveSettings(self):
        self.settings.setValue("size", self.size())
        self.settings.setValue("pos", self.pos())
        self.settings.setValue("splitter", self.splitter.sizes())
        self.settings.setValue(
            "drawPerfomance", self.drawPerfomanceOption.isChecked()
        )
        self.settings.setValue("sourceEditor", self.sourceEditor)

    def loadSettings(self):
        self.resize(self.settings.value("size", QSize(400, 400)).toSize())
        self.move(self.settings.value("pos", QPoint(200, 200)).toPoint())
        split = self.settings.value("splitter", [100, 300]).toList()
        split = [x.toInt()[0] for x in split]

        self.splitter.setSizes(split)
        b = bool(self.settings.value("drawPerfomance", 0).toInt()[0])
        self.drawPerfomanceOption.setChecked(b)
        self.view.setVisible(b)
        s = self.settings.value(
            "sourceEditor", _default_source_editor_template()
        )
        self.sourceEditor = str(s) if s else _default_source_editor_template()

    def itemClick(self, row, column):
        if not self.sourceEditor or not self.sourceEditor.strip():
            QMessageBox.information(
                self,
                "Source editor",
                "Set your editor command in Options → Set editor.\n"
                "Use %(source)s for file path and %(line)d for line number.",
            )
            return
        command = ""
        try:
            item = self.table.item(row, 0)
            if item is None:
                return
            data_val = item.data(0)
            data_str = (
                data_val.toString()
                if hasattr(data_val, "toString")
                else str(data_val)
            )
            func = str_to_obj(str(data_str))
            filename = inspect.getsourcefile(func)
            line = inspect.getsourcelines(func)[-1]
            command = self.sourceEditor % {
                "source": filename,
                "line": int(line),
            }
            subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                shell=True,
            )
        except Exception:
            pass

    def timerEvent(self, event=None):  # pyright: ignore[reportIncompatibleMethodOverride]
        if not self.callGraph:
            return
        self.callGraph.done()
        self.table.clear()
        self.table.setSortingEnabled(False)
        total_time = 0
        for output in self.callGraph.output:
            i = 0
            generator = output.processor.nodes()
            j = sum(1 for x in generator)
            self.table.setRowCount(j)
            for node in output.processor.nodes():
                item = QTableWidgetItem(node.name)
                self.table.setItem(i, 0, item)
                item = QTableWidgetItem()
                item.setData(Qt.ItemDataRole.EditRole, node.calls.value)
                self.table.setItem(i, 1, item)
                item = QTableWidgetItem()
                item.setData(Qt.ItemDataRole.EditRole, node.time.value)
                total_time += node.time.value
                self.table.setItem(i, 2, item)
                item = QTableWidgetItem()
                item.setData(
                    Qt.ItemDataRole.EditRole,
                    node.time.value / float(node.calls.value),
                )
                self.table.setItem(i, 3, item)
                i += 1
            self.table.update()
        self.perfList += [total_time - self.previousTime]
        self.previousTime = total_time
        if len(self.perfList) > 40:
            self.perfList = self.perfList[1:]
        if self.drawPerfomanceOption.isChecked():
            self.perfGraph.updatePath(self.perfList)
        self.table.setSortingEnabled(True)
        self.callGraph.start(reset=False)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    QApplication.setDoubleClickInterval(400)
    QApplication.setStartDragTime(200)
    window = NodeDialog()
    window.show()
    sys.exit(app.exec())

    # from pycallgraph import PyCallGraph
    # from json_output import JsonOutput
    # jsonOut = JsonOutput()
    # jsonOut.output_file = "c:\\wewe.nod"
    # callGraph = PyCallGraph(output=jsonOut)

    # with callGraph:

    #     app = QApplication(sys.argv)

    #     window = NodeDialog()
    #     window.show()
    #     calls = CallDialog(None,callGraph=callGraph)
    #     calls.show()
    #     sys.exit(app.exec())
