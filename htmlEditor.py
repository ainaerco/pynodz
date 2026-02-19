import sys
from qtpy.QtGui import (
    QColor,
    QTextCharFormat,
    QTextListFormat,
    QTextTableFormat,
    QTextLength,
    QTextCursor,
    QTextBlockFormat,
    QPalette,
    QFont,
    QUndoStack,
)
from qtpy import QtCore
from qtpy.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QFontComboBox,
    QGroupBox,
    QHBoxLayout,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

import nodeUtils


class HtmlEditor(QDialog):
    def __init__(self, parent=None, d={}):
        super().__init__(parent)
        self.node = d.get("node", None)
        if self.node:
            self.setWindowTitle("Editor - %s" % self.node.name)
        else:
            self.setWindowTitle("Editor")

        self.undoStack = QUndoStack(self)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setLayout(layout)

        toolBox = QGroupBox()
        self.toolLayout = QHBoxLayout(toolBox)
        self.toolLayout.setContentsMargins(0, 0, 0, 0)
        self.toolLayout.setSpacing(0)
        toolSize = QtCore.QSize(25, 25)

        newButton = QPushButton(
            nodeUtils.options.getAwesomeIcon("fa6s.folder-open"), ""
        )
        newButton.setFlat(True)
        newButton.setFixedSize(toolSize)
        newButton.setToolTip("New scene")

        saveButton = QPushButton(
            nodeUtils.options.getAwesomeIcon("fa6s.floppy-disk"), ""
        )
        saveButton.setFlat(True)
        saveButton.setFixedSize(toolSize)
        saveButton.setToolTip("Save scene")

        undoButton = QPushButton(
            nodeUtils.options.getAwesomeIcon("fa6s.rotate-left"), ""
        )
        undoButton.setFlat(True)
        undoButton.setFixedSize(toolSize)
        undoButton.setToolTip("Undo (Ctrl+Z)")

        redoButton = QPushButton(
            nodeUtils.options.getAwesomeIcon("fa6s.rotate-right"), ""
        )
        redoButton.setFlat(True)
        redoButton.setFixedSize(toolSize)
        redoButton.setToolTip("Redo (Ctrl+Y)")

        self.fonts = QFontComboBox()
        self.fonts.setFixedSize(QtCore.QSize(200, 25))
        self.fonts.setFontFilters(QFontComboBox.FontFilter.ScalableFonts)

        self.font_size = QComboBox()
        for i in range(8, 26, 2):
            self.font_size.addItem(str(i))
        self.font_size.setFixedSize(QtCore.QSize(40, 25))
        self.font_size = QComboBox()
        for i in range(4, 26, 2):
            self.font_size.addItem(str(i))
        self.font_size.setFixedSize(QtCore.QSize(40, 25))

        bold = QPushButton(nodeUtils.options.getAwesomeIcon("fa6s.bold"), "")
        bold.setFixedSize(toolSize)
        bold.setFlat(True)
        italic = QPushButton(
            nodeUtils.options.getAwesomeIcon("fa6s.italic"), ""
        )
        italic.setFixedSize(toolSize)
        italic.setFlat(True)
        underline = QPushButton(
            nodeUtils.options.getAwesomeIcon("fa6s.underline"), ""
        )
        underline.setFixedSize(toolSize)
        underline.setFlat(True)
        unindent = QPushButton(
            nodeUtils.options.getAwesomeIcon("fa6s.outdent"), ""
        )
        unindent.setFixedSize(toolSize)
        unindent.setFlat(True)
        indent = QPushButton(
            nodeUtils.options.getAwesomeIcon("fa6s.indent"), ""
        )
        indent.setFixedSize(toolSize)
        indent.setFlat(True)
        bullet = QPushButton(
            nodeUtils.options.getAwesomeIcon("fa6s.list-ul"), ""
        )
        bullet.setFixedSize(toolSize)
        bullet.setFlat(True)
        number = QPushButton(
            nodeUtils.options.getAwesomeIcon("fa6s.list-ol"), ""
        )
        number.setFixedSize(toolSize)
        number.setFlat(True)
        image = QPushButton(nodeUtils.options.getAwesomeIcon("fa6s.image"), "")
        image.setFixedSize(toolSize)
        image.setFlat(True)
        table = QPushButton(nodeUtils.options.getAwesomeIcon("fa6s.table"), "")
        table.setFixedSize(toolSize)
        table.setFlat(True)

        self.align = QComboBox()
        self.align.addItem("")
        self.align.setItemIcon(
            0, nodeUtils.options.getAwesomeIcon("fa6s.align-left")
        )
        self.align.addItem("")
        self.align.setItemIcon(
            1, nodeUtils.options.getAwesomeIcon("fa6s.align-center")
        )
        self.align.addItem("")
        self.align.setItemIcon(
            2, nodeUtils.options.getAwesomeIcon("fa6s.align-right")
        )
        self.align.addItem("")
        self.align.setItemIcon(
            3, nodeUtils.options.getAwesomeIcon("fa6s.align-justify")
        )
        self.align.setFixedSize(QtCore.QSize(30, 25))
        self.align.setStyleSheet(
            "::drop-down { width: 0px; border-style: none}"
        )

        self.colors = QComboBox()
        ncolors = 16
        ngrays = 6
        for i in range(ngrays):
            color = QColor(
                int(i * 255 / ngrays),
                int(i * 255 / ngrays),
                int(i * 255 / ngrays),
            )
            self.colors.addItem("")
            self.colors.setItemData(
                i, color, QtCore.Qt.ItemDataRole.DecorationRole
            )
        for i in range(ncolors):
            color = QColor()
            color.setHsv(int(i / float(ncolors) * 359), 150, 250)
            self.colors.addItem("")
            self.colors.setItemData(
                ngrays + i, color, QtCore.Qt.ItemDataRole.DecorationRole
            )
        self.colors.setFixedSize(QtCore.QSize(44, 25))
        self.colors.setStyleSheet("background:#000000")

        line1 = QFrame()
        line1.setFrameShape(QFrame.Shape.VLine)
        line1.setFrameShadow(QFrame.Shadow.Sunken)
        line2 = QFrame()
        line2.setFrameShape(QFrame.Shape.VLine)
        line2.setFrameShadow(QFrame.Shadow.Sunken)

        self.toolLayout.addWidget(newButton)
        self.toolLayout.addWidget(saveButton)
        self.toolLayout.addWidget(undoButton)
        self.toolLayout.addWidget(redoButton)
        self.toolLayout.addWidget(line1)
        self.toolLayout.addWidget(bold)
        self.toolLayout.addWidget(italic)
        self.toolLayout.addWidget(underline)
        self.toolLayout.addWidget(line2)
        self.toolLayout.addWidget(image)
        self.toolLayout.addWidget(table)
        self.toolLayout.addStretch()
        self.toolLayout.addWidget(self.fonts)
        self.toolLayout.addWidget(self.font_size)
        self.toolLayout.addWidget(unindent)
        self.toolLayout.addWidget(indent)
        self.toolLayout.addWidget(bullet)
        self.toolLayout.addWidget(number)
        self.toolLayout.addWidget(self.align)
        self.toolLayout.addWidget(self.colors)

        layout.addWidget(toolBox)

        self.html = QTextEdit()
        self.html.document().setIndentWidth(20)
        self.text = d.get("text", None)
        self.f = d.get("func", None)
        if self.node and self.text:
            t = d.get("type", "")
            if t == "text":
                self.html.setPlainText(self.text)
            elif t == "html":
                self.html.setHtml(self.text)

        layout.addWidget(self.html)

        undoButton.clicked.connect(self.html.undo)
        redoButton.clicked.connect(self.html.redo)
        bold.clicked.connect(self.boldPress)
        number.clicked.connect(self.ascendPress)
        bullet.clicked.connect(self.bulletPress)
        italic.clicked.connect(self.italicPress)
        underline.clicked.connect(self.underlinePress)
        image.clicked.connect(self.insertImage)
        table.clicked.connect(self.insertTable)
        self.fonts.currentIndexChanged.connect(self.fontChanged)
        self.font_size.currentIndexChanged.connect(self.fontSizeChanged)
        self.align.currentIndexChanged.connect(self.alignChanged)
        self.colors.currentIndexChanged.connect(self.colorChanged)

    def ascendPress(self):
        cursor = self.html.textCursor()
        list_format = QTextListFormat()
        if (
            cursor.currentList() is None
            or cursor.currentList().format().style()
            != QTextListFormat.Style.ListDecimal
        ):
            list_format.setIndent(1)
            list_format.setStyle(QTextListFormat.Style.ListDecimal)
        else:
            list_format.setIndent(0)
        cursor.createList(list_format)

    def bulletPress(self):
        cursor = self.html.textCursor()
        list_format = QTextListFormat()
        if (
            cursor.currentList() is None
            or cursor.currentList().format().style()
            != QTextListFormat.Style.ListDisc
        ):
            list_format.setIndent(1)
            list_format.setStyle(QTextListFormat.Style.ListDisc)
        else:
            list_format.setIndent(0)
        cursor.createList(list_format)

    def insertTable(self):
        cursor = self.html.textCursor()

        f = QTextTableFormat()
        f.setBorder(1)
        f.setCellSpacing(-1)
        f.setColumnWidthConstraints(
            [
                QTextLength(QTextLength.Type.FixedLength, 70),
                QTextLength(QTextLength.Type.FixedLength, 170),
            ]
        )
        cursor.insertTable(2, 2, f)

    def insertImage(self, f=None):
        f, mask = QFileDialog.getOpenFileName(
            self,
            "Open File",
            "",
            "Bitmap Files (*.bmp)\nJPEG (*.jpg *jpeg)\nGIF (*.gif)\nPNG (*.png)",
        )
        if f:
            cursor = self.html.textCursor()
            cursor.insertImage(f)

    def indentPress(self):
        cur = self.html.textCursor()
        pos = cur.position()  # Where a selection ends
        cur.setPosition(pos)
        # Move the position back one, selection the character prior to the original position
        cur.setPosition(pos - 1, QTextCursor.MoveMode.KeepAnchor)

        if cur.selectedText() == "\t":
            cur.removeSelectedText()

    def boldPress(self):
        cursor = self.html.textCursor()
        cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        format = QTextCharFormat()
        format.setFontWeight(
            QFont.Weight.Bold
            if format.fontWeight() == QFont.Weight.Bold
            else QFont.Weight.Normal
        )
        cursor.mergeCharFormat(format)

    def italicPress(self):
        cursor = self.html.textCursor()
        cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        format = QTextCharFormat()
        font = format.font()
        font.setItalic(not font.italic())
        format.setFont(font)
        cursor.mergeCharFormat(format)

    def underlinePress(self):
        cursor = self.html.textCursor()
        cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        format = QTextCharFormat()
        format.setFontUnderline(not format.fontUnderline())
        cursor.mergeCharFormat(format)

    def fontChanged(self, i):
        cursor = self.html.textCursor()
        format = QTextCharFormat()
        font = self.fonts.currentFont()
        font.setPointSize(int(self.font_size.currentText()))
        format.setFont(font)
        cursor.mergeCharFormat(format)

    def fontSizeChanged(self, i):
        cursor = self.html.textCursor()
        format = QTextCharFormat()
        format.setFontPointSize(int(self.font_size.currentText()))
        cursor.mergeCharFormat(format)

    def alignChanged(self, i):
        cursor = self.html.textCursor()
        format = QTextBlockFormat()
        if i == 0:
            format.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        elif i == 1:
            format.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)
        elif i == 2:
            format.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        elif i == 3:
            format.setAlignment(QtCore.Qt.AlignmentFlag.AlignJustify)
        cursor.mergeBlockFormat(format)

    def colorChanged(self, i):
        pal = self.colors.palette()
        color = QColor(
            self.colors.itemData(i, QtCore.Qt.ItemDataRole.DecorationRole)
        )
        pal.setColor(QPalette.ColorRole.ButtonText, color)
        self.colors.setStyleSheet("background:%s" % color.name())
        cursor = self.html.textCursor()
        format = QTextCharFormat()
        format.setForeground(color)
        cursor.mergeCharFormat(format)

    def closeEvent(self, a0):
        if self.node and self.f:
            self.f(self.html)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    QApplication.setDoubleClickInterval(4000)
    win = HtmlEditor()
    win.show()
    sys.exit(app.exec())
