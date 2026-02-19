"""Markdown editor dialog, API-compatible with html_editor.HtmlEditor.

Use the same pattern as HtmlEditor: pass a dict d with keys:
- node: optional node reference (for window title)
- text: initial markdown text
- func: callback when closing; receives the editor widget (call .toPlainText())
- type: "markdown" or "text" (both treated as plain markdown source)

Example from a node:
    def on_save(editor):
        node_utils.options.undoStack.push(
            CommandSetNodeAttribute([self], {"markdown": editor.toPlainText()})
        )
    editor = MarkdownEditor(
        self.dialog,
        {"node": self, "text": self.markdown, "func": on_save, "type": "markdown"},
    )
    editor.show()
"""

import sys
from qtpy import QtCore
from qtpy.QtGui import QTextCursor
from qtpy.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
)

import node_utils

try:
    import markdown as _markdown_lib

    def _markdownToHtml(text: str) -> str:
        return _markdown_lib.markdown(
            text,
            extensions=["extra", "nl2br", "sane_lists"],
            output_format="html",
        )
except ImportError:
    _markdown_lib = None

    def _markdownToHtml(text: str) -> str:
        return "<p>Install the <code>markdown</code> package for preview.</p>"


def _previewHtmlWrap(body: str) -> str:
    """Wrap rendered markdown in a minimal HTML document for preview."""
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        "<style>body{font-family:sans-serif;padding:8px;line-height:1.5;}"
        "code{background:#eee;padding:1px 4px;} pre{background:#eee;padding:8px;}"
        "img{max-width:100%;}"
        "ul{list-style-type:disc;padding-left:1.5em;} ol{list-style-type:decimal;padding-left:1.5em;} li{margin:0.25em 0;}"
        "</style></head><body>" + body + "</body></html>"
    )


def _wrap_or_insert(cursor, before, after, default_text=""):
    """Wrap selection with before/after, or insert default_text with before/after."""
    if cursor.hasSelection():
        text = cursor.selectedText()
        cursor.insertText("%s%s%s" % (before, text, after))
    else:
        cursor.insertText("%s%s%s" % (before, default_text, after))


class MarkdownEditor(QDialog):
    def __init__(self, parent=None, d=None):
        super().__init__(parent)
        d = d or {}
        self.node = d.get("node", None)
        if self.node:
            self.setWindowTitle("Markdown - %s" % self.node.name)
        else:
            self.setWindowTitle("Markdown Editor")

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setLayout(layout)

        toolBox = QGroupBox()
        self.toolLayout = QHBoxLayout(toolBox)
        self.toolLayout.setContentsMargins(0, 0, 0, 0)
        self.toolLayout.setSpacing(0)
        toolSize = QtCore.QSize(25, 25)

        undoBtn = QPushButton(
            node_utils.options.get_awesome_icon("fa6s.rotate-left"), ""
        )
        undoBtn.setFlat(True)
        undoBtn.setFixedSize(toolSize)
        undoBtn.setToolTip("Undo (Ctrl+Z)")

        redoBtn = QPushButton(
            node_utils.options.get_awesome_icon("fa6s.rotate-right"), ""
        )
        redoBtn.setFlat(True)
        redoBtn.setFixedSize(toolSize)
        redoBtn.setToolTip("Redo (Ctrl+Y)")

        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)

        boldBtn = QPushButton(
            node_utils.options.get_awesome_icon("fa6s.bold"), ""
        )
        boldBtn.setFixedSize(toolSize)
        boldBtn.setFlat(True)
        boldBtn.setToolTip("Bold (**text**)")

        italicBtn = QPushButton(
            node_utils.options.get_awesome_icon("fa6s.italic"), ""
        )
        italicBtn.setFixedSize(toolSize)
        italicBtn.setFlat(True)
        italicBtn.setToolTip("Italic (*text*)")

        codeBtn = QPushButton(
            node_utils.options.get_awesome_icon("fa6s.code"), ""
        )
        codeBtn.setFixedSize(toolSize)
        codeBtn.setFlat(True)
        codeBtn.setToolTip("Inline code (`code`)")

        h1Btn = QPushButton(
            node_utils.options.get_awesome_icon("fa6s.heading"), ""
        )
        h1Btn.setFixedSize(toolSize)
        h1Btn.setFlat(True)
        h1Btn.setToolTip("Heading (## )")

        bulletBtn = QPushButton(
            node_utils.options.get_awesome_icon("fa6s.list-ul"), ""
        )
        bulletBtn.setFixedSize(toolSize)
        bulletBtn.setFlat(True)
        bulletBtn.setToolTip("Bullet list (- )")

        numberBtn = QPushButton(
            node_utils.options.get_awesome_icon("fa6s.list-ol"), ""
        )
        numberBtn.setFixedSize(toolSize)
        numberBtn.setFlat(True)
        numberBtn.setToolTip("Numbered list (1. )")

        linkBtn = QPushButton(
            node_utils.options.get_awesome_icon("fa6s.link"), ""
        )
        linkBtn.setFixedSize(toolSize)
        linkBtn.setFlat(True)
        linkBtn.setToolTip("Link [text](url)")

        imageBtn = QPushButton(
            node_utils.options.get_awesome_icon("fa6s.image"), ""
        )
        imageBtn.setFixedSize(toolSize)
        imageBtn.setFlat(True)
        imageBtn.setToolTip("Image ![alt](url)")

        self.previewBtn = QPushButton(
            node_utils.options.get_awesome_icon("fa6s.eye"), ""
        )
        self.previewBtn.setFixedSize(toolSize)
        self.previewBtn.setFlat(True)
        self.previewBtn.setCheckable(True)
        self.previewBtn.setToolTip("Show formatted preview")
        self.previewBtn.setChecked(False)

        self.toolLayout.addWidget(undoBtn)
        self.toolLayout.addWidget(redoBtn)
        self.toolLayout.addWidget(line)
        self.toolLayout.addWidget(boldBtn)
        self.toolLayout.addWidget(italicBtn)
        self.toolLayout.addWidget(codeBtn)
        self.toolLayout.addWidget(h1Btn)
        self.toolLayout.addWidget(bulletBtn)
        self.toolLayout.addWidget(numberBtn)
        self.toolLayout.addWidget(linkBtn)
        self.toolLayout.addWidget(imageBtn)
        self.toolLayout.addWidget(line)
        self.toolLayout.addWidget(self.previewBtn)
        self.toolLayout.addStretch()

        layout.addWidget(toolBox)

        self.text_edit = QTextEdit()
        self.text_edit.setAcceptRichText(False)
        self.text = d.get("text", None)
        self.f = d.get("func", None)
        if self.node and self.text is not None:
            self.text_edit.setPlainText(self.text)

        self.preview_edit = QTextEdit()
        self.preview_edit.setReadOnly(True)
        self.preview_edit.setAcceptRichText(True)

        self.splitter = QSplitter(QtCore.Qt.Orientation.Horizontal)
        self.splitter.addWidget(self.text_edit)
        self.splitter.addWidget(self.preview_edit)
        self.splitter.setSizes([1, 0])
        self.preview_edit.hide()

        self._previewTimer = QtCore.QTimer(self)
        self._previewTimer.setSingleShot(True)
        self._previewTimer.timeout.connect(self._updatePreview)

        layout.addWidget(self.splitter)

        undoBtn.clicked.connect(self.text_edit.undo)
        redoBtn.clicked.connect(self.text_edit.redo)
        boldBtn.clicked.connect(self._bold)
        italicBtn.clicked.connect(self._italic)
        codeBtn.clicked.connect(self._code)
        h1Btn.clicked.connect(self._heading)
        bulletBtn.clicked.connect(self._bullet)
        numberBtn.clicked.connect(self._number)
        linkBtn.clicked.connect(self._link)
        imageBtn.clicked.connect(self._image)
        self.text_edit.textChanged.connect(self._schedulePreviewUpdate)
        self.previewBtn.toggled.connect(self._togglePreview)

    def _schedulePreviewUpdate(self):
        if self.previewBtn.isChecked():
            self._previewTimer.start(300)

    def _updatePreview(self):
        html = _markdownToHtml(self.text_edit.toPlainText())
        self.preview_edit.setHtml(_previewHtmlWrap(html))

    def _togglePreview(self, on):
        if on:
            self.preview_edit.show()
            self.splitter.setSizes([self.splitter.width() // 2] * 2)
            self._updatePreview()
        else:
            self.preview_edit.hide()
            self.splitter.setSizes([self.splitter.width(), 0])

    def _bold(self):
        cursor = self.text_edit.textCursor()
        _wrap_or_insert(cursor, "**", "**", "bold text")

    def _italic(self):
        cursor = self.text_edit.textCursor()
        _wrap_or_insert(cursor, "*", "*", "italic text")

    def _code(self):
        cursor = self.text_edit.textCursor()
        _wrap_or_insert(cursor, "`", "`", "code")

    def _heading(self):
        cursor = self.text_edit.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.StartOfLine)
        cursor.insertText("## ")

    def _bullet(self):
        cursor = self.text_edit.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.StartOfLine)
        cursor.insertText("- ")

    def _number(self):
        cursor = self.text_edit.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.StartOfLine)
        cursor.insertText("1. ")

    def _link(self):
        cursor = self.text_edit.textCursor()
        if cursor.hasSelection():
            text = cursor.selectedText()
            cursor.insertText("[%s](url)" % text)
        else:
            cursor.insertText("[link text](url)")

    def _image(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Insert image",
            "",
            "Images (*.png *.jpg *.jpeg *.gif *.bmp *.webp)",
        )
        if path:
            cursor = self.text_edit.textCursor()
            cursor.insertText("![image](%s)" % path)

    def toPlainText(self):
        """Return current markdown source (for compatibility with node callback)."""
        return self.text_edit.toPlainText()

    def toHtml(self):
        """Not used for markdown; provided so callers can use same pattern as HtmlEditor."""
        return self.text_edit.toPlainText()

    def closeEvent(self, event):
        if self.node and self.f:
            self.f(self)
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    QApplication.setDoubleClickInterval(4000)
    win = MarkdownEditor()
    win.show()
    sys.exit(app.exec())
