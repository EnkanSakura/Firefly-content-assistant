"""Firefly Markdown Assistant 主窗口。

提供完整的 Markdown 文章编辑环境：
- Frontmatter 表单面板（可折叠）
- 富工具栏（左侧）
- Markdown 文本编辑器（中央）
- 实时预览面板（右侧，可切换）
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QToolBar, QToolButton, QStatusBar,
    QPlainTextEdit, QTextEdit, QDockWidget,
    QMenu, QMenuBar, QFileDialog, QMessageBox,
    QApplication, QLabel, QFrame, QSizePolicy,
    QGroupBox, QFormLayout, QLineEdit, QCheckBox,
    QDateEdit, QPushButton, QScrollArea, QComboBox,
)
from PySide6.QtCore import Qt, QDate, QFileInfo, QTimer, QUrl
from PySide6.QtGui import QAction, QFont, QKeySequence, QShortcut

from app.constants import APP_STYLESHEET
from core.markdown_utils import (
    build_frontmatter,
    FRONTMATTER_FIELDS, FRONTMATTER_ORDER,
    github_card_snippet, spoiler_snippet, video_snippet,
    details_snippet, katex_snippet,
)
from ui.dialogs.admonition_dialog import AdmonitionDialog
from ui.dialogs.code_block_dialog import CodeBlockDialog
from ui.dialogs.mermaid_dialog import MermaidDialog
from ui.dialogs.plantuml_dialog import PlantUMLDialog
from ui.dialogs.image_grid_dialog import ImageGridDialog
from ui.dialogs.table_dialog import TableDialog


# ── 编辑器字体 ──────────────────────────────────────────
EDITOR_FONT = QFont("Consolas", 13)
EDITOR_FONT.setStyleHint(QFont.StyleHint.Monospace)


# ── 工具栏按钮工厂 ──────────────────────────────────────
def _make_btn(text: str, tooltip: str = "", icon: str = "") -> QPushButton:
    btn = QPushButton(text)
    btn.setToolTip(tooltip)
    btn.setFixedHeight(34)
    btn.setMinimumWidth(36)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    return btn


def _make_sep() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setFixedHeight(1)
    f.setStyleSheet("background-color: #313244;")
    return f


# ── Frontmatter 面板 ────────────────────────────────────
class FrontmatterPanel(QWidget):
    """可折叠的 Frontmatter 编辑面板。"""

    fm_ready = None  # signal placeholder (callable)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._widgets: dict[str, Any] = {}
        self._collapsed = False
        self._setup()

    def _setup(self) -> None:
        main = QVBoxLayout(self)
        main.setContentsMargins(0, 0, 0, 0)

        # 顶部折叠按钮
        header = QHBoxLayout()
        self._toggle_btn = QPushButton("▼ Frontmatter")
        self._toggle_btn.setObjectName("primary")
        self._toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toggle_btn.clicked.connect(self._toggle)
        header.addWidget(self._toggle_btn)
        header.addStretch()
        self._reset_btn = QPushButton("清空")
        self._reset_btn.clicked.connect(self._reset)
        header.addWidget(self._reset_btn)
        main.addLayout(header)

        # 滚动区域
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setMaximumHeight(300)

        form_widget = QWidget()
        form = QFormLayout(form_widget)
        form.setSpacing(6)
        form.setContentsMargins(8, 4, 8, 8)

        for key in FRONTMATTER_ORDER:
            info = FRONTMATTER_FIELDS[key]
            if info["type"] == "text":
                w = QLineEdit()
                w.setPlaceholderText(f"输入{info['label']}...")
            elif info["type"] == "date":
                w = QDateEdit()
                w.setCalendarPopup(True)
                w.setDisplayFormat("yyyy-MM-dd")
                w.setDate(QDate.currentDate())
            elif info["type"] == "bool":
                w = QCheckBox()
            elif info["type"] == "tags":
                w = QLineEdit()
                w.setPlaceholderText("标签, 用逗号分隔")
            else:
                w = QLineEdit()
            form.addRow(f"{info['label']}:", w)
            self._widgets[key] = w

        self._scroll.setWidget(form_widget)
        main.addWidget(self._scroll)

        self.setMaximumHeight(350)

    def _toggle(self) -> None:
        self._collapsed = not self._collapsed
        self._scroll.setVisible(not self._collapsed)
        self._toggle_btn.setText("▶ Frontmatter" if self._collapsed else "▼ Frontmatter")
        if self._collapsed:
            self.setMaximumHeight(50)
        else:
            self.setMaximumHeight(350)

    def _reset(self) -> None:
        for key, w in self._widgets.items():
            info = FRONTMATTER_FIELDS[key]
            if info["type"] == "text":
                w.clear()
            elif info["type"] == "date":
                w.setDate(QDate.currentDate())
            elif info["type"] == "bool":
                w.setChecked(False)
            elif info["type"] == "tags":
                w.clear()

    def collect_values(self) -> dict[str, Any]:
        values: dict[str, Any] = {}
        for key, w in self._widgets.items():
            info = FRONTMATTER_FIELDS[key]
            if info["type"] == "text":
                val = w.text().strip()
                values[key] = val if val else info["default"]
            elif info["type"] == "date":
                values[key] = w.date().toPython()
            elif info["type"] == "bool":
                values[key] = w.isChecked()
            elif info["type"] == "tags":
                raw = w.text().strip()
                values[key] = [t.strip() for t in raw.split(",") if t.strip()] if raw else []
        return values

    def set_values(self, values: dict[str, Any]) -> None:
        for key, w in self._widgets.items():
            if key not in values:
                continue
            val = values[key]
            info = FRONTMATTER_FIELDS[key]
            if info["type"] == "text":
                w.setText(str(val) if val else "")
            elif info["type"] == "date":
                if isinstance(val, date):
                    w.setDate(QDate(val.year, val.month, val.day))
                elif isinstance(val, str) and val:
                    try:
                        d = date.fromisoformat(val)
                        w.setDate(QDate(d.year, d.month, d.day))
                    except ValueError:
                        pass
            elif info["type"] == "bool":
                w.setChecked(bool(val))
            elif info["type"] == "tags":
                if isinstance(val, list):
                    w.setText(", ".join(val))


# ── 主窗口 ──────────────────────────────────────────────
class MainWindow(QMainWindow):
    """Firefly Markdown Assistant 主窗口。"""

    SETTINGS_FILE = Path.home() / ".firefly_md_assistant.json"

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Firefly Markdown Assistant")
        self.resize(1280, 800)
        self.setMinimumSize(900, 600)
        self._current_file: str = ""
        self._dirty = False
        self._auto_save_timer = QTimer(self)
        self._auto_save_timer.setInterval(30000)  # 30s
        self._auto_save_timer.timeout.connect(self._auto_save)
        self._auto_save_timer.start()

        # 预览图片缓存（远程图片 → base64 data URI）
        self._preview_img_cache: dict[str, str] = {}

        # 预览防抖定时器（500ms 延迟，避免频繁刷新）
        self._preview_timer = QTimer(self)
        self._preview_timer.setInterval(500)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.timeout.connect(self._update_preview)

        self._setup_menu()
        self._setup_central()
        self._setup_statusbar()
        self._load_settings()

        # 保存快捷键
        QShortcut(QKeySequence.StandardKey.Save, self, activated=self.save_file)

    # ── 菜单栏 ───────────────────────────────────────
    def _setup_menu(self) -> None:
        bar = self.menuBar()

        file_menu = bar.addMenu("文件(&F)")
        file_menu.addAction("新建(&N)", self.new_file, QKeySequence.StandardKey.New)
        file_menu.addAction("打开(&O)...", self.open_file, QKeySequence.StandardKey.Open)
        file_menu.addAction("保存(&S)", self.save_file, QKeySequence.StandardKey.Save)
        file_menu.addAction("另存为(&A)...", self.save_as)
        file_menu.addSeparator()
        file_menu.addAction("退出(&Q)", self.close, "Ctrl+Q")

        edit_menu = bar.addMenu("编辑(&E)")
        edit_menu.addAction("撤销(&U)", lambda: self._editor.undo(), "Ctrl+Z")
        edit_menu.addAction("重做(&R)", lambda: self._editor.redo(), "Ctrl+Y")
        edit_menu.addSeparator()
        edit_menu.addAction("生成 / 更新 Frontmatter", self._generate_frontmatter, "Ctrl+Shift+F")

        insert_menu = bar.addMenu("插入(&I)")
        insert_menu.addAction("代码块...", self._insert_code_block, "Ctrl+Shift+C")
        insert_menu.addAction("提醒框...", self._insert_admonition, "Ctrl+Shift+A")
        insert_menu.addAction("Mermaid 图表...", self._insert_mermaid, "Ctrl+Shift+M")
        insert_menu.addAction("PlantUML 图表...", self._insert_plantuml, "Ctrl+Shift+P")
        insert_menu.addAction("图片网格...", self._insert_image_grid)
        insert_menu.addAction("表格...", self._insert_table, "Ctrl+Shift+T")
        insert_menu.addSeparator()
        insert_menu.addAction("GitHub 仓库卡片", self._insert_github_card)
        insert_menu.addAction("剧透文本", self._insert_spoiler)
        insert_menu.addAction("视频嵌入", self._insert_video)
        insert_menu.addAction("可折叠详情", self._insert_details)
        insert_menu.addSeparator()
        katex_menu = insert_menu.addMenu("KaTeX 公式")
        katex_menu.addAction("行内公式", lambda: self._insert_katex("行内公式"))
        katex_menu.addAction("块级公式", lambda: self._insert_katex("块级公式"))
        katex_menu.addAction("矩阵", lambda: self._insert_katex("矩阵"))
        katex_menu.addAction("化学方程式", lambda: self._insert_katex("化学方程式"))

        view_menu = bar.addMenu("视图(&V)")
        view_menu.addAction("切换预览面板", self._toggle_preview, "Ctrl+P")

        help_menu = bar.addMenu("帮助(&H)")
        help_menu.addAction("关于", self._about)

    # ── 中央区域 ────────────────────────────────────
    def _setup_central(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Frontmatter 面板
        self._fm_panel = FrontmatterPanel()
        root.addWidget(self._fm_panel)

        # 水平分割：工具栏 + 编辑器 + 预览
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(2)

        # 左侧工具栏
        self._toolbar = self._create_toolbar()
        splitter.addWidget(self._toolbar)

        # 中央编辑器
        self._editor = QPlainTextEdit()
        self._editor.setFont(EDITOR_FONT)
        self._editor.setTabStopDistance(36)
        self._editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self._editor.textChanged.connect(self._on_editor_changed)
        splitter.addWidget(self._editor)

        # 右侧预览
        self._preview = QTextEdit()
        self._preview.setReadOnly(True)
        self._preview.setFont(QFont("Segoe UI", 12))
        self._preview.setVisible(False)
        splitter.addWidget(self._preview)

        splitter.setSizes([80, 800, 400])
        root.addWidget(splitter)

    # ── 工具栏 ──────────────────────────────────────
    def _create_toolbar(self) -> QWidget:
        container = QWidget()
        container.setFixedWidth(90)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 8, 4, 8)
        layout.setSpacing(4)

        # 基础 Markdown
        basic_btns = [
            ("H1", "# ", "标题 1"),
            ("H2", "## ", "标题 2"),
            ("H3", "### ", "标题 3"),
            ("**B**", "**", "粗体"),
            ("_I_", "_", "斜体"),
            ("~~S~~", "~~", "删除线"),
            ("`", "`", "行内代码"),
        ]
        for label, prefix, tip in basic_btns:
            btn = _make_btn(label, tip)
            btn.clicked.connect(lambda _, p=prefix: self._surround(p))
            layout.addWidget(btn)

        layout.addWidget(_make_sep())

        # 块元素
        block_btns = [
            ("链接", "[", "插入链接"),
            ("图片", "![", "插入图片"),
            ("引用", "> ", "引用块"),
            ("列表", "- ", "无序列表"),
            ("编号", "1. ", "有序列表"),
            ("分割", "---", "分割线"),
        ]
        for label, prefix, tip in block_btns:
            btn = _make_btn(label, tip)
            btn.clicked.connect(lambda _, p=prefix: self._insert_line_prefix(p))
            layout.addWidget(btn)

        layout.addWidget(_make_sep())

        # Firefly 扩展
        ext_btns = [
            ("代码块", self._insert_code_block, "插入 Expressive Code 代码块"),
            ("提醒框", self._insert_admonition, "插入提醒框"),
            ("表格", self._insert_table, "插入表格"),
            ("GitHub", self._insert_github_card, "GitHub 仓库卡片"),
            ("图片网格", self._insert_image_grid, "图片画廊网格"),
            ("Mermaid", self._insert_mermaid, "Mermaid 图表"),
            ("PlantUML", self._insert_plantuml, "PlantUML 图表"),
            ("公式", lambda: self._insert_katex("块级公式"), "KaTeX 公式"),
            ("视频", self._insert_video, "嵌入视频"),
            ("剧透", self._insert_spoiler, "剧透文本"),
            ("折叠", self._insert_details, "可折叠详情"),
        ]
        for label, callback, tip in ext_btns:
            btn = _make_btn(label, tip)
            btn.clicked.connect(callback)
            layout.addWidget(btn)

        layout.addStretch()

        # 底部操作
        ops_btns = [
            ("生成\nFrontmatter", self._generate_frontmatter, "生成/更新 Frontmatter"),
            ("预览", self._toggle_preview, "切换预览面板"),
        ]
        for label, callback, tip in ops_btns:
            btn = _make_btn(label, tip)
            btn.setFixedHeight(44)
            btn.clicked.connect(callback)
            layout.addWidget(btn)

        return container

    # ── 状态栏 ──────────────────────────────────────
    def _setup_statusbar(self) -> None:
        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._file_label = QLabel(" 新建文件")
        self._status.addWidget(self._file_label)
        self._status.addPermanentWidget(QLabel("Firefly Markdown Assistant v1.0"))

    # ── 编辑器辅助 ──────────────────────────────────
    def _insert_at_cursor(self, text: str) -> None:
        cursor = self._editor.textCursor()
        cursor.insertText(text)
        self._editor.setFocus()

    def _surround(self, marker: str) -> None:
        """用 marker 包裹选中文本（**粗体**、_斜体_ 等）；H 标签插入行首。"""
        cursor = self._editor.textCursor()

        # H 标签：始终在行首插入一次
        if marker.startswith("#"):
            start_line = cursor.selectionStart() if cursor.hasSelection() else cursor.position()
            cursor.setPosition(start_line)
            cursor.movePosition(cursor.MoveOperation.StartOfLine)
            cursor.insertText(marker)
            return

        # 包裹型标记：** _ ~~ `
        if cursor.hasSelection():
            sel = cursor.selectedText()
            cursor.insertText(f"{marker}{sel}{marker}")
        else:
            cursor.insertText(f"{marker}{marker}")
            cursor.movePosition(cursor.MoveOperation.Left, cursor.MoveMode.MoveAnchor, len(marker))

    def _insert_line_prefix(self, prefix: str) -> None:
        """在当前行首插入前缀。"""
        cursor = self._editor.textCursor()
        if prefix in ("[", "!["):
            if prefix == "[":
                self._insert_at_cursor("[链接文字](url)")
            else:
                self._insert_at_cursor("![替代文字](./images/example.avif)")
            return
        cursor.movePosition(cursor.MoveOperation.StartOfLine)
        cursor.insertText(prefix)

    def _on_editor_changed(self) -> None:
        self._dirty = True
        self._update_title()
        # 预览可见时，通过防抖定时器触发刷新
        if self._preview.isVisible():
            self._preview_timer.start()

    def _update_title(self) -> None:
        title = "Firefly Markdown Assistant"
        if self._current_file:
            title += f" - {Path(self._current_file).name}"
        if self._dirty:
            title += " *"
        self.setWindowTitle(title)

    # ── Frontmatter ────────────────────────────────
    def _generate_frontmatter(self) -> None:
        values = self._fm_panel.collect_values()
        fm_text = build_frontmatter(values)
        # 检查编辑器开头是否已有 frontmatter
        current = self._editor.toPlainText()
        if current.lstrip().startswith("---"):
            # 替换现有 frontmatter
            idx = current.find("---", 3)
            if idx != -1:
                new_text = fm_text + current[idx + 4:].lstrip("\n")
                self._editor.setPlainText(new_text)
                return
        # 在前面插入
        new_text = fm_text + ("\n" + current if current.strip() else "\n")
        self._editor.setPlainText(new_text)
        self._status.showMessage("Frontmatter 已生成", 3000)

    # ── 插入功能 ──────────────────────────────────
    def _insert_admonition(self) -> None:
        dlg = AdmonitionDialog(self)
        if dlg.exec() == AdmonitionDialog.DialogCode.Accepted:
            self._insert_at_cursor("\n" + dlg.snippet() + "\n")

    def _insert_code_block(self) -> None:
        dlg = CodeBlockDialog(self)
        if dlg.exec() == CodeBlockDialog.DialogCode.Accepted:
            self._insert_at_cursor("\n" + dlg.snippet() + "\n")

    def _insert_mermaid(self) -> None:
        dlg = MermaidDialog(self)
        if dlg.exec() == MermaidDialog.DialogCode.Accepted:
            self._insert_at_cursor("\n" + dlg.snippet() + "\n")

    def _insert_plantuml(self) -> None:
        dlg = PlantUMLDialog(self)
        if dlg.exec() == PlantUMLDialog.DialogCode.Accepted:
            self._insert_at_cursor("\n" + dlg.snippet() + "\n")

    def _insert_image_grid(self) -> None:
        dlg = ImageGridDialog(self)
        if dlg.exec() == ImageGridDialog.DialogCode.Accepted:
            self._insert_at_cursor("\n" + dlg.snippet() + "\n")

    def _insert_table(self) -> None:
        dlg = TableDialog(self)
        if dlg.exec() == TableDialog.DialogCode.Accepted:
            self._insert_at_cursor("\n" + dlg.snippet() + "\n")

    def _insert_github_card(self) -> None:
        cursor = self._editor.textCursor()
        if cursor.hasSelection():
            repo = cursor.selectedText().strip()
        else:
            repo = "Owner/Repo"
        self._insert_at_cursor("\n" + github_card_snippet(repo) + "\n")

    def _insert_spoiler(self) -> None:
        cursor = self._editor.textCursor()
        text = cursor.selectedText() if cursor.hasSelection() else "隐藏内容"
        self._insert_at_cursor(spoiler_snippet(text))

    def _insert_video(self) -> None:
        cursor = self._editor.textCursor()
        text = cursor.selectedText() if cursor.hasSelection() else "dQw4w9WgXcQ"
        self._insert_at_cursor("\n" + video_snippet("youtube", text) + "\n")

    def _insert_details(self) -> None:
        self._insert_at_cursor(
            "\n" + details_snippet("点击展开", "隐藏的内容") + "\n"
        )

    def _insert_katex(self, formula_type: str) -> None:
        snippet = katex_snippet(formula_type)
        self._insert_at_cursor("\n" + snippet + "\n")

    # ── 文件操作 ──────────────────────────────────
    def new_file(self) -> None:
        if self._dirty:
            r = QMessageBox.question(self, "未保存",
                                       "当前文件有未保存的更改，是否保存？",
                                       QMessageBox.StandardButton.Save |
                                       QMessageBox.StandardButton.Discard |
                                       QMessageBox.StandardButton.Cancel)
            if r == QMessageBox.StandardButton.Save:
                self.save_file()
            elif r == QMessageBox.StandardButton.Cancel:
                return
        self._editor.clear()
        self._current_file = ""
        self._dirty = False
        self._fm_panel._reset()
        self._update_title()
        self._status.showMessage("新建文件", 2000)

    def open_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "打开 Markdown 文件", "",
            "Markdown Files (*.md *.mdx);;All Files (*)"
        )
        if not path:
            return
        try:
            content = Path(path).read_text(encoding="utf-8")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法打开文件：{e}")
            return
        self._editor.setPlainText(content)
        self._current_file = path
        self._dirty = False
        self._update_title()
        self._parse_frontmatter(content)
        self._status.showMessage(f"已打开: {path}", 3000)

    def _parse_frontmatter(self, content: str) -> None:
        """尝试从已有内容解析 frontmatter 并填充面板。"""
        if not content.lstrip().startswith("---"):
            return
        lines = content.split("\n")
        if len(lines) < 2:
            return
        fm_lines: list[str] = []
        in_fm = False
        for line in lines[1:]:
            if line.strip() == "---":
                break
            fm_lines.append(line)
        values: dict[str, Any] = {}
        for line in fm_lines:
            if ":" not in line:
                continue
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key in FRONTMATTER_FIELDS:
                info = FRONTMATTER_FIELDS[key]
                if info["type"] == "bool":
                    values[key] = val.lower() == "true"
                elif info["type"] == "tags":
                    # 去掉方括号和引号
                    clean = val.strip("[]")
                    values[key] = [t.strip().strip('"').strip("'") for t in clean.split(",") if t.strip()]
                else:
                    values[key] = val
        if values:
            self._fm_panel.set_values(values)

    def save_file(self) -> None:
        if self._current_file:
            self._write_file(self._current_file)
        else:
            self.save_as()

    def save_as(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "保存 Markdown 文件", "",
            "Markdown Files (*.md);;All Files (*)"
        )
        if path:
            self._current_file = path
            self._write_file(path)

    def _write_file(self, path: str) -> None:
        try:
            Path(path).write_text(self._editor.toPlainText(), encoding="utf-8")
            self._dirty = False
            self._update_title()
            self._status.showMessage(f"已保存: {path}", 3000)
            self._save_settings()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存失败：{e}")

    def _auto_save(self) -> None:
        if self._dirty and self._current_file:
            self._write_file(self._current_file)

    # ── 预览切换 ──────────────────────────────────
    def _toggle_preview(self) -> None:
        visible = not self._preview.isVisible()
        self._preview.setVisible(visible)
        if visible:
            self._update_preview()

    def _update_preview(self) -> None:
        """简易预览：将 Markdown 转为 HTML 显示。"""
        import re
        text = self._editor.toPlainText()

        # 去掉 frontmatter
        if text.lstrip().startswith("---"):
            idx = text.find("---", 3)
            if idx != -1:
                text = text[idx + 3:].lstrip("\n")

        html = text

        # ── 第 1 遍：提取代码块，替换为占位符 ──
        code_blocks: list[str] = []

        def _save_code(m: re.Match) -> str:
            lang_meta = m.group(1).strip()
            raw = m.group(2)
            # HTML 转义代码内容
            safe = (
                raw.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
            )
            lang_tag = (
                f'<span style="color:#a6adc8;font-size:11px">{lang_meta}</span>\n'
                if lang_meta
                else ""
            )
            code_blocks.append(
                f'<pre style="background:#313244;color:#cdd6f4;'
                f'padding:12px;border-radius:6px;overflow-x:auto;'
                f'font-size:12px;white-space:pre;margin:12px 0">{lang_tag}{safe}</pre>'
            )
            return f"%%CB{len(code_blocks) - 1}%%"

        html = re.sub(r"```([^\n]*)\n([\s\S]*?)```", _save_code, html)

        # ── 第 2 遍：保护原始 HTML 标签（img / iframe / details / div 等）──
        raw_tags: list[str] = []

        def _protect_tag(m: re.Match) -> str:
            raw_tags.append(m.group(0))
            return f"%%HT{len(raw_tags) - 1}%%"

        # 自闭合标签 + 配对标签（简化匹配，覆盖 Firefly 常见用例）
        html = re.sub(
            r'<(img|iframe|details|summary|div|span|br|hr)\b[^>]*/?>|'
            r'</(iframe|details|summary|div|span)>',
            _protect_tag,
            html,
            flags=re.IGNORECASE,
        )

        # ── 第 3 遍：转义正文中的 HTML ──
        html = html.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        # 恢复原始 HTML 标签
        for i, tag in enumerate(raw_tags):
            html = html.replace(f"%%HT{i}%%", tag)

        # ── 第 3 遍：Markdown 格式转换 ──

        # 标题
        html = re.sub(r"^#### (.+)$", r"<h4>\1</h4>", html, flags=re.MULTILINE)
        html = re.sub(r"^### (.+)$", r"<h3>\1</h3>", html, flags=re.MULTILINE)
        html = re.sub(r"^## (.+)$", r"<h2>\1</h2>", html, flags=re.MULTILINE)
        html = re.sub(r"^# (.+)$", r"<h1>\1</h1>", html, flags=re.MULTILINE)

        # ── 图片解析（远程 base64 内联；本地 → file:/// 绝对路径）──
        cache = self._preview_img_cache
        base_dir = (
            Path(self._current_file).parent
            if self._current_file
            else Path.cwd()
        )

        def _resolve_img_src(src: str) -> str:
            """远程图片下载后转 base64 data URI；本地路径转为 file:/// URL。"""
            src = src.strip()
            if src.startswith(("http://", "https://")):
                if src in cache:
                    return cache[src]
                try:
                    import urllib.request
                    req = urllib.request.Request(src, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req, timeout=5) as resp:
                        data = resp.read()
                    ct = resp.headers.get("Content-Type", "image/png")
                    b64 = __import__("base64").b64encode(data).decode()
                    uri = f"data:{ct};base64,{b64}"
                    cache[src] = uri
                    return uri
                except Exception:
                    cache[src] = src
                    return src
            # 本地路径 → file:/// 绝对 URL
            try:
                resolved = (base_dir / src).resolve()
                return resolved.as_uri()
            except Exception:
                return src

        # 链接包裹图片: [![alt](img)](url)
        def _link_img_repl(m: re.Match) -> str:
            alt = m.group(1)
            src = _resolve_img_src(m.group(2))
            href = m.group(3)
            return f'<a href="{href}"><img src="{src}" alt="{alt}" style="max-width:100%"></a>'

        html = re.sub(
            r'\[!\[([^\]]*)\]\(([^)]+)\)\]\(([^)]+)\)',
            _link_img_repl,
            html,
        )

        # 独立图片
        def _img_repl(m: re.Match) -> str:
            alt = m.group(1)
            src = _resolve_img_src(m.group(2))
            return f'<img src="{src}" alt="{alt}" style="max-width:100%">'

        html = re.sub(
            r'!\[([^\]]*)\]\(([^)]+)\)',
            _img_repl,
            html,
        )
        # 普通链接
        html = re.sub(
            r"\[([^\]]+)\]\(([^)]+)\)",
            r'<a href="\2" style="color:#89b4fa">\1</a>',
            html,
        )

        # 粗体 / 斜体 / 删除线 / 行内代码
        html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)
        html = re.sub(r"\*(.+?)\*", r"<em>\1</em>", html)
        html = re.sub(r"~~(.+?)~~", r"<del>\1</del>", html)
        html = re.sub(
            r"`([^`]+)`",
            r'<code style="background:#313244;padding:2px 6px;border-radius:3px">\1</code>',
            html,
        )

        # ── 表格转换 ──
        def _convert_table(m: re.Match) -> str:
            """将 Markdown 表格块转为 HTML <table>。"""
            block = m.group(0)
            lines = block.strip().split("\n")
            rows_html: list[str] = []
            for i, line in enumerate(lines):
                cells = [c.strip() for c in line.strip("|").split("|")]
                if i == 1:
                    continue  # 跳过分隔行
                tag = "th" if i == 0 else "td"
                cells_html = "".join(
                    f'<{tag} style="padding:6px 12px;border:1px solid #45475a;'
                    f'text-align:left">{c}</{tag}>'
                    for c in cells
                )
                rows_html.append(f"<tr>{cells_html}</tr>")
            return (
                '<table style="border-collapse:collapse;margin:12px 0;width:100%">'
                + "".join(rows_html)
                + "</table>"
            )

        html = re.sub(
            r'(?:^\|.+\|\s*$\n?){2,}',
            _convert_table,
            html,
            flags=re.MULTILINE,
        )

        # ── 第 4 遍：段落处理（分割线 → <hr>；双换行 → 段落边界）──
        html = re.sub(r"^---$", r"<hr>", html, flags=re.MULTILINE)
        paragraphs = html.split("\n\n")
        wrapped: list[str] = []
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            # 代码块/HTML占位符或块级 HTML 元素不包裹 <p>
            if re.match(
                r"^(%%(CB|HT)\d+%%|<(h[1-6]|hr|table|ul|ol|blockquote|pre|div))",
                para,
            ):
                wrapped.append(para)
            else:
                wrapped.append(f"<p>{para.replace(chr(10), '<br>')}</p>")
        html = "\n".join(wrapped)

        # ── 第 5 遍：恢复代码块（在所有段落包裹之后） ──
        for i, cb in enumerate(code_blocks):
            html = html.replace(f"%%CB{i}%%", cb)

        # ── 最终样式 ──
        styled = (
            '<div style="color:#cdd6f4;font-family:\'Segoe UI\',sans-serif;'
            'font-size:14px;line-height:1.8;max-width:800px;padding:16px;'
            'word-wrap:break-word;overflow-wrap:break-word">'
            f"{html}"
            "</div>"
        )
        self._preview.setHtml(styled)

    # ── 设置持久化 ────────────────────────────────
    def _save_settings(self) -> None:
        try:
            data = {"last_file": self._current_file}
            self.SETTINGS_FILE.write_text(json.dumps(data))
        except Exception:
            pass

    def _load_settings(self) -> None:
        try:
            if self.SETTINGS_FILE.exists():
                data = json.loads(self.SETTINGS_FILE.read_text())
                last = data.get("last_file", "")
                if last and Path(last).exists():
                    self._current_file = last
                    self._editor.setPlainText(Path(last).read_text(encoding="utf-8"))
                    self._update_title()
        except Exception:
            pass

    # ── 关于 ──────────────────────────────────────
    def _about(self) -> None:
        QMessageBox.about(
            self, "关于 Firefly Markdown Assistant",
            "<h3>Firefly Markdown Assistant v1.0</h3>"
            "<p>专为 Firefly Astro 博客主题设计的 Markdown 文章辅助生成工具。</p>"
            "<p>支持所有 Firefly 扩展语法，包括：</p>"
            "<ul>"
            "<li>Frontmatter 可视化编辑</li>"
            "<li>提醒框 (GitHub / Obsidian / VitePress / Docusaurus)</li>"
            "<li>Expressive Code 代码块</li>"
            "<li>Mermaid / PlantUML 图表</li>"
            "<li>KaTeX 数学公式</li>"
            "<li>图片网格、视频嵌入、剧透等</li>"
            "</ul>"
        )

    def closeEvent(self, event) -> None:
        if self._dirty:
            r = QMessageBox.question(
                self, "未保存",
                "当前文件有未保存的更改，是否保存？",
                QMessageBox.StandardButton.Save |
                QMessageBox.StandardButton.Discard |
                QMessageBox.StandardButton.Cancel,
            )
            if r == QMessageBox.StandardButton.Save:
                self.save_file()
                event.accept()
            elif r == QMessageBox.StandardButton.Discard:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
