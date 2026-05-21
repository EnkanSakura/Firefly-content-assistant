"""Firefly Markdown Assistant 主窗口。

提供完整的 Markdown 文章编辑环境：
- Frontmatter 表单面板（可折叠）
- 富工具栏（左侧）
- Markdown 文本编辑器（中央）
- 实时预览面板（右侧，可切换）
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from datetime import date
from pathlib import Path
from typing import Any

from PySide6.QtWidgets import (
    QStyle,
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter,
    QPlainTextEdit, QTextEdit,
    QMenu, QFileDialog, QMessageBox,
    QApplication, QLabel, QFrame, QSizePolicy,
    QGroupBox, QFormLayout, QLineEdit, QCheckBox,
    QDateEdit, QPushButton, QScrollArea, QComboBox,
)
from PySide6.QtCore import Qt, QDate, QEvent, QFileInfo, QPoint, QRect, QTimer, QUrl
from PySide6.QtGui import QFont, QKeySequence, QShortcut

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
    btn.setMinimumWidth(100)
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
        self.setFixedHeight(0)

    def _setup(self) -> None:
        # 弹出面板（浮动，不占布局空间）
        self._popup = QFrame()
        self._popup.setWindowFlags(
            Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint
        )
        self._popup.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._popup.setStyleSheet(
            "#fmPopup { background-color: #1e1e2e; border: 2px solid #89b4fa;"
            "border-radius: 8px; }"
        )
        self._popup.setObjectName("fmPopup")
        popup_layout = QVBoxLayout(self._popup)
        popup_layout.setContentsMargins(12, 8, 12, 12)

        form_widget = QWidget()
        form = QFormLayout(form_widget)
        form.setSpacing(6)
        form.setContentsMargins(0, 0, 0, 0)

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

        popup_layout.addWidget(form_widget)
        # 清空按钮
        reset_btn = QPushButton("清空")
        reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        reset_btn.clicked.connect(self._reset)
        popup_layout.addWidget(reset_btn)
        self._popup.setFixedWidth(420)
        self._popup.installEventFilter(self)

        # 背景遮罩（展开时覆盖整个窗口）
        self._overlay = QWidget()
        self._overlay.setStyleSheet("background-color: rgba(0, 0, 0, 120);")
        self._overlay.hide()
        self._overlay.installEventFilter(self)

        # 默认收起
        self._collapsed = True
    def toggle_from(self, anchor: QPushButton) -> None:
        """从标题栏按钮触发展开/收起。"""
        self._collapsed = not self._collapsed
        if self._collapsed:
            self._popup.hide()
            self._overlay.hide()
        else:
            # 遮罩覆盖父窗口
            win = self.window()
            if win and self._overlay:
                self._overlay.setParent(win)
                self._overlay.setGeometry(0, 0, win.width(), win.height())
                self._overlay.show()
                self._overlay.raise_()
            # 定位弹出面板
            pos = anchor.mapToGlobal(anchor.rect().bottomLeft())
            self._popup.move(pos)
            self._popup.show()
            self._popup.raise_()

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

    def eventFilter(self, obj, event) -> bool:
        if obj is self._popup and event.type() == QEvent.Type.Hide:
            self._collapsed = True
            self._overlay.hide()
        elif obj is self._overlay and event.type() == QEvent.Type.MouseButtonPress:
            self._popup.hide()
            self._overlay.hide()
            self._collapsed = True
        return super().eventFilter(obj, event)

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

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Firefly Markdown Assistant — 新建文件")
        self._current_file: str = ""
        self._dirty = False
        self.resize(1280, 800)
        self.setMinimumSize(900, 600)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._normal_geometry = None

        # 预览图片缓存（远程图片 → base64 data URI）
        self._preview_img_cache: dict[str, str] = {}

        # 预览防抖定时器
        self._preview_timer = QTimer(self)
        self._preview_timer.setInterval(300)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.timeout.connect(self._update_preview)

        self._setup_menu()
        self._setup_central()
        self._setup_statusbar()

        # 快捷键
        QShortcut(QKeySequence.StandardKey.Save, self, activated=self.save_file)
        QShortcut(QKeySequence.StandardKey.New, self, activated=self.new_file)
        QShortcut(QKeySequence.StandardKey.Open, self, activated=self.open_file)
        QShortcut(QKeySequence("Ctrl+Shift+F"), self, activated=self._generate_frontmatter)

    # ── 自定义标题栏（图标按钮）────────────────────────
    def _setup_menu(self) -> None:
        self._title_bar = QWidget()
        self._title_bar.setFixedHeight(40)
        self._title_bar.setObjectName("titleBar")
        self._title_bar.setStyleSheet(
            "#titleBar { background-color: #181825;"
            "border-top-left-radius: 8px; border-top-right-radius: 8px;"
            "border-bottom: 1px solid #313244; }"
        )
        self._title_bar.setCursor(Qt.CursorShape.ArrowCursor)
        tb_layout = QHBoxLayout(self._title_bar)
        tb_layout.setContentsMargins(8, 0, 4, 0)
        tb_layout.setSpacing(2)

        # 应用名称
        app_label = QLabel("Firefly MDA")
        app_label.setStyleSheet(
            "color: #89b4fa; font-size: 12px; font-weight: bold;"
            "background: transparent; border: none; padding: 0 8px;"
        )
        tb_layout.addWidget(app_label)

        # 分隔线
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("background-color: #313244;")
        sep.setFixedWidth(1)
        sep.setFixedHeight(20)
        tb_layout.addWidget(sep)

        # 功能按钮（文字标签）
        func_btns = [
            ("新建", "新建 (Ctrl+N)", self.new_file),
            ("打开", "打开 (Ctrl+O)", self.open_file),
            ("保存", "保存 (Ctrl+S)", self.save_file),
            ("另存", "另存为", self.save_as),
        ]
        for label, tip, cb in func_btns:
            btn = QPushButton(label)
            btn.setFixedHeight(26)
            btn.setToolTip(tip)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(
                "QPushButton { color: #cdd6f4; background: transparent; border: none;"
                "padding: 0 10px; font-size: 12px; border-radius: 4px; }"
                "QPushButton:hover { background: #313244; }"
                "QPushButton:pressed { background: #45475a; }"
            )
            btn.clicked.connect(cb)
            tb_layout.addWidget(btn)

        # 分隔符
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.VLine)
        sep2.setStyleSheet("background-color: #313244;")
        sep2.setFixedWidth(1)
        sep2.setFixedHeight(20)
        tb_layout.addWidget(sep2)

        # 编辑按钮
        edit_btns = [
            ("撤销", "撤销 (Ctrl+Z)", lambda: self._editor.undo()),
            ("重做", "重做 (Ctrl+Y)", lambda: self._editor.redo())
        ]
        for label, tip, cb in edit_btns:
            btn = QPushButton(label)
            btn.setFixedHeight(26)
            btn.setToolTip(tip)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(
                "QPushButton { color: #cdd6f4; background: transparent; border: none;"
                "padding: 0 10px; font-size: 12px; border-radius: 4px; }"
                "QPushButton:hover { background: #313244; }"
                "QPushButton:pressed { background: #45475a; }"
            )
            btn.clicked.connect(cb)
            tb_layout.addWidget(btn)

        # FM 分隔符
        sep3 = QFrame()
        sep3.setFrameShape(QFrame.Shape.VLine)
        sep3.setStyleSheet("background-color: #313244;")
        sep3.setFixedWidth(1)
        sep3.setFixedHeight(20)
        tb_layout.addWidget(sep3)

        # Frontmatter按钮
        fm_btns = [
            ("刷新", "刷新 Frontmatter (Ctrl+Shift+F)", self._generate_frontmatter)
        ]

        self._fm_toggle_btn = QPushButton("FM")
        self._fm_toggle_btn.setFixedHeight(26)
        self._fm_toggle_btn.setToolTip("Frontmatter 编辑面板")
        self._fm_toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._fm_toggle_btn.setStyleSheet(
            "QPushButton { color: #89b4fa; background: transparent; border: none;"
            "padding: 0 10px; font-size: 12px; font-weight: bold; border-radius: 4px; }"
            "QPushButton:hover { background: #313244; }"
            "QPushButton:pressed { background: #45475a; }"
        )
        self._fm_toggle_btn.clicked.connect(
            lambda: self._fm_panel.toggle_from(self._fm_toggle_btn)
        )
        tb_layout.addWidget(self._fm_toggle_btn)

        for label, tip, cb in fm_btns:
            btn = QPushButton(label)
            btn.setFixedHeight(26)
            btn.setToolTip(tip)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(
                "QPushButton { color: #cdd6f4; background: transparent; border: none;"
                "padding: 0 10px; font-size: 12px; border-radius: 4px; }"
                "QPushButton:hover { background: #313244; }"
                "QPushButton:pressed { background: #45475a; }"
            )
            btn.clicked.connect(cb)
            tb_layout.addWidget(btn)


        tb_layout.addStretch()

        # 窗口控制按钮（Windows 默认风格）
        style = self.style()
        win_ctrls = [
            (QStyle.StandardPixmap.SP_TitleBarMinButton, self.showMinimized, "最小化"),
            (QStyle.StandardPixmap.SP_TitleBarMaxButton, self._toggle_maximize, "最大化"),
            (QStyle.StandardPixmap.SP_TitleBarCloseButton, self.close, "关闭"),
        ]
        for sp_icon, slot, tip in win_ctrls:
            btn = QPushButton()
            btn.setIcon(style.standardIcon(sp_icon))
            btn.setFixedSize(36, 28)
            btn.setToolTip(tip)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(
                "QPushButton { background: transparent; border: none;"
                "border-radius: 4px; }"
                "QPushButton:hover { background: #313244; }"
            )
            if sp_icon == QStyle.StandardPixmap.SP_TitleBarCloseButton:
                btn.setStyleSheet(
                    "QPushButton { background: transparent; border: none;"
                    "border-radius: 4px; }"
                    "QPushButton:hover { background: #e06c75; }"
                )
            btn.clicked.connect(slot)
            tb_layout.addWidget(btn)

        # 拖拽支持
        self._title_bar.mousePressEvent = self._title_bar_press
        self._title_bar.mouseMoveEvent = self._title_bar_move
        self._title_bar.mouseReleaseEvent = self._title_bar_release
        self._title_bar.mouseDoubleClickEvent = self._title_bar_dblclick

    def _title_bar_press(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint()
    
    def _title_bar_move(self, event) -> None:
        if hasattr(self, '_drag_pos'):
            delta = event.globalPosition().toPoint() - self._drag_pos
            self.move(self.pos() + delta)
            self._drag_pos = event.globalPosition().toPoint()

    def _title_bar_release(self, event) -> None:
        if hasattr(self, '_drag_pos'):
            del self._drag_pos

    def _title_bar_dblclick(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._toggle_maximize()
            if hasattr(self, '_drag_pos'):
                del self._drag_pos

    def _toggle_maximize(self) -> None:
        if self.isMaximized():
            self.showNormal()
        else:
            self._normal_geometry = self.geometry()
            self.showMaximized()

    def _update_maximize_style(self) -> None:
        """最大化时移除圆角和边距，恢复时加回。"""
        maximized = self.isMaximized()
        # 更新中央布局边距
        cw = self.centralWidget()
        if cw and cw.layout():
            m = 0 if maximized else 8
            cw.layout().setContentsMargins(m, m, m, 0)
        # 更新标题栏圆角
        if maximized:
            self._title_bar.setStyleSheet(
                "#titleBar { background-color: #181825;"
                "border-bottom: 1px solid #313244; }"
            )
        else:
            self._title_bar.setStyleSheet(
                "#titleBar { background-color: #181825;"
                "border-top-left-radius: 8px; border-top-right-radius: 8px;"
                "border-bottom: 1px solid #313244; }"
            )
        # 更新内容容器圆角
        if maximized:
            self._content_frame.setStyleSheet(
                "#contentFrame { background-color: #1e1e2e; border: none; }"
            )
        else:
            self._content_frame.setStyleSheet(
                "#contentFrame { background-color: #1e1e2e; border: none;"
                "border-bottom-left-radius: 8px; border-bottom-right-radius: 8px; }"
            )
        # 更新状态栏圆角
        if maximized:
            self._status.setStyleSheet(
                "background-color: #181825; border-top: 1px solid #313244;"
            )
        else:
            self._status.setStyleSheet(
                "background-color: #181825; border-top: 1px solid #313244;"
                "border-bottom-left-radius: 8px; border-bottom-right-radius: 8px;"
            )

    def changeEvent(self, event) -> None:
        if event.type() == QEvent.Type.WindowStateChange:
            pass  # state handled by isMaximized() directly
            self._update_maximize_style()
        super().changeEvent(event)

    def moveEvent(self, event) -> None:
        if not self.isMaximized():
            self._normal_geometry = self.geometry()
        super().moveEvent(event)

    def resizeEvent(self, event) -> None:
        if not self.isMaximized():
            self._normal_geometry = self.geometry()
        super().resizeEvent(event)

    def nativeEvent(self, eventType, message) -> tuple[bool, int]:
        """处理 WM_NCCALCSIZE 和 WM_NCHITTEST。"""
        msg = ctypes.cast(int(message), ctypes.POINTER(wintypes.MSG)).contents
        if msg.message == 0x0083:  # WM_NCCALCSIZE — 消除非客户区边框
            return True, 0
        if msg.message == 0x0084:  # WM_NCHITTEST — 边框拖拽 / Aero Snap
            result = self._hit_test(msg)
            return True, result
        return False, 0

    def _hit_test(self, msg) -> int:
        """返回 WM_NCHITTEST 结果。

        使用 frameGeometry 获取窗口在屏幕上的实际区域，
        并通过 devicePixelRatioF 将物理像素坐标转换为逻辑坐标。
        """
        BORDER = 6
        dpr = self.devicePixelRatioF()
        # lParam 为物理像素坐标，除以 DPR 得到逻辑坐标
        px = (ctypes.c_int16)(msg.lParam & 0xFFFF).value / dpr
        py = (ctypes.c_int16)((msg.lParam >> 16) & 0xFFFF).value / dpr
        # frameGeometry：窗口在屏幕上的实际区域（逻辑坐标）
        fg = self.frameGeometry()
        rx, ry = px - fg.x(), py - fg.y()
        w, h = fg.width(), fg.height()

        maximized = self.isMaximized()

        # 标题栏（包括按钮区域）—— 始终可拖拽
        margin = 0 if maximized else 8
        tb_h = self._title_bar.height() + margin
        if margin <= rx < w - margin and margin <= ry < tb_h:
            # 检查鼠标下是否有子控件（按钮等），如有则不拦截点击
            child = self._title_bar.childAt(
                self._title_bar.mapFromGlobal(
                    QPoint(int(px), int(py))
                )
            )
            if child is not None and child is not self._title_bar:
                return 1  # HTCLIENT — 让子控件接收鼠标事件
            return 2  # HTCAPTION

        # 最大化时不允许拖拽边框调整大小
        if maximized:
            return 1  # HTCLIENT

        on_left = rx < BORDER and rx >= 0
        on_right = rx > w - BORDER and rx <= w
        on_top = ry < BORDER and ry >= 0
        on_bottom = ry > h - BORDER and ry <= h

        if on_left and on_top:
            return 13  # HTTOPLEFT
        if on_right and on_top:
            return 14  # HTTOPRIGHT
        if on_left and on_bottom:
            return 16  # HTBOTTOMLEFT
        if on_right and on_bottom:
            return 17  # HTBOTTOMRIGHT
        if on_left:
            return 10  # HTLEFT
        if on_right:
            return 11  # HTRIGHT
        if on_top:
            return 12  # HTTOP
        if on_bottom:
            return 15  # HTBOTTOM
        return 1  # HTCLIENT

    # ── 中央区域 ────────────────────────────────────
    def _setup_central(self) -> None:
        cw = QWidget()
        cw.setObjectName("centralWidget")
        cw.setStyleSheet("#centralWidget { background: transparent; }")
        self.setCentralWidget(cw)
        root = QVBoxLayout(cw)
        root.setContentsMargins(8, 8, 8, 0)
        root.setSpacing(0)

        # 自定义标题栏
        root.addWidget(self._title_bar)

        # 内容容器（圆角底部）
        content_frame = QFrame()
        content_frame.setObjectName("contentFrame")
        self._content_frame = content_frame
        content_frame.setStyleSheet(
            "#contentFrame { background-color: #1e1e2e; border: none;"
            "border-bottom-left-radius: 8px; border-bottom-right-radius: 8px; }"
        )
        self._frame_layout = frame_layout = QVBoxLayout(content_frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame_layout.setSpacing(0)

        # Frontmatter 面板
        self._fm_panel = FrontmatterPanel()
        frame_layout.addWidget(self._fm_panel)

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
        self._editor.cursorPositionChanged.connect(self._sync_preview_scroll)
        self._editor.verticalScrollBar().valueChanged.connect(self._sync_preview_scroll)
        splitter.addWidget(self._editor)

        # 右侧预览
        self._preview = QTextEdit()
        self._preview.setReadOnly(True)
        self._preview.setFont(QFont("Segoe UI", 12))
        self._preview.setVisible(True)
        splitter.addWidget(self._preview)

        splitter.setSizes([130, 640, 430])
        frame_layout.addWidget(splitter)

        root.addWidget(content_frame)

    # ── 工具栏 ──────────────────────────────────────
    def _create_toolbar(self) -> QWidget:
        container = QWidget()
        container.setFixedWidth(130)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 8, 4, 8)
        layout.setSpacing(4)

        # 基础 Markdown
        basic_btns = [
            ("H1", "# ", "一级标题 — 在行首插入 #"),
            ("H2", "## ", "二级标题 — 在行首插入 ##"),
            ("H3", "### ", "三级标题 — 在行首插入 ###"),
            ("**B**", "**", "粗体 — 用 ** 包裹选中文本"),
            ("_I_", "_", "斜体 — 用 _ 包裹选中文本"),
            ("~~S~~", "~~", "删除线 — 用 ~~ 包裹选中文本"),
            ("`", "`", "行内代码 — 用 ` 包裹选中文本"),
        ]
        for label, prefix, tip in basic_btns:
            btn = _make_btn(label, tip)
            btn.clicked.connect(lambda _, p=prefix: self._surround(p))
            layout.addWidget(btn)

        layout.addWidget(_make_sep())

        # 块元素
        block_btns = [
            ("链接", "[", "插入 Markdown 链接 — 格式：[文本](url)"),
            ("图片", "![", "插入图片 — 格式：![alt](url)"),
            ("引用", "> ", "引用块 — 在行首插入 >"),
            ("列表", "- ", "无序列表 — 在行首插入 -"),
            ("编号", "1. ", "有序列表 — 在行首插入 1."),
            ("分割", "---", "分割线 — 插入 ---"),
        ]
        for label, prefix, tip in block_btns:
            btn = _make_btn(label, tip)
            btn.clicked.connect(lambda _, p=prefix: self._insert_line_prefix(p))
            layout.addWidget(btn)

        layout.addWidget(_make_sep())

        # Firefly 扩展
        ext_btns = [
            ("代码块", self._insert_code_block, "插入 Expressive Code 代码块"),
            ("提醒框", self._insert_admonition, "插入提醒框 — GitHub/Obsidian/VitePress/Docusaurus 样式"),
            ("表格", self._insert_table, "插入表格 — 支持列宽、对齐方式"),
            ("GitHub", self._insert_github_card, "GitHub 仓库卡片"),
            ("图片网格", self._insert_image_grid, "插入图片网格 — Firefly 扩展语法"),
            ("Mermaid", self._insert_mermaid, "Mermaid 图表"),
            ("PlantUML", self._insert_plantuml, "PlantUML 图表"),
            ("公式", lambda: self._insert_katex("块级公式"), "KaTeX 公式"),
            ("视频", self._insert_video, "嵌入视频 — 支持 B站/YouTube"),
            ("剧透", self._insert_spoiler, "剧透/隐藏文本 — Firefly 扩展语法"),
            ("折叠", self._insert_details, "可折叠详情块 — Firefly 扩展语法"),
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
        self._status = QWidget()
        self._status.setFixedHeight(28)
        self._status.setStyleSheet(
            "background-color: #181825; border-top: 1px solid #313244;"
            "border-bottom-left-radius: 8px; border-bottom-right-radius: 8px;"
        )
        status_layout = QHBoxLayout(self._status)
        status_layout.setContentsMargins(12, 0, 12, 0)
        self._file_label = QLabel(" 新建文件")
        self._status_msg = QLabel("")
        self._status_msg.setStyleSheet("color: #a6adc8; font-size: 11px; border: none; background: transparent;")
        self._status_msg_timer = QTimer(self)
        self._status_msg_timer.setSingleShot(True)
        self._status_msg_timer.timeout.connect(lambda: self._status_msg.setText(""))
        status_layout.addWidget(self._file_label)
        status_layout.addWidget(self._status_msg)
        status_layout.addStretch()
        version_label = QLabel("Firefly Markdown Assistant v1.0")
        version_label.setStyleSheet("color: #585b70; font-size: 11px;")
        status_layout.addWidget(version_label)
        self._frame_layout.addWidget(self._status)

    def _show_status(self, msg: str, timeout_ms: int = 3000) -> None:
        self._status_msg.setText(msg)
        self._status_msg_timer.start(timeout_ms)

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
            self._editor.setTextCursor(cursor)
            self._editor.setFocus()
            return

        # 包裹型标记：** _ ~~ `
        if cursor.hasSelection():
            sel = cursor.selectedText()
            cursor.insertText(f"{marker}{sel}{marker}")
        else:
            cursor.insertText(f"{marker}{marker}")
            cursor.movePosition(cursor.MoveOperation.Left, cursor.MoveMode.MoveAnchor, len(marker))

        self._editor.setTextCursor(cursor)
        self._editor.setFocus()

    def _insert_line_prefix(self, prefix: str) -> None:
        """在当前行首插入前缀。"""
        cursor = self._editor.textCursor()
        if prefix in ("[", "!["):
            if prefix == "[":
                cursor.insertText("[链接文字](url)")
                # 选中填充文字方便直接替换
                cursor.movePosition(cursor.MoveOperation.Left, cursor.MoveMode.MoveAnchor, 6)  # )url]( 共6字符
                cursor.movePosition(cursor.MoveOperation.Left, cursor.MoveMode.KeepAnchor, 4)  # 选中「链接文字」
                self._editor.setTextCursor(cursor)
                self._editor.setFocus()
            else:
                cursor.insertText("![替代文字](./images/example.avif)")
                # 选中填充文字方便直接替换
                cursor.movePosition(cursor.MoveOperation.Left, cursor.MoveMode.MoveAnchor, 24)  # 移至「替代文字」右侧
                cursor.movePosition(cursor.MoveOperation.Left, cursor.MoveMode.KeepAnchor, 4)  # 选中「替代文字」
                self._editor.setTextCursor(cursor)
                self._editor.setFocus()
            return
        cursor.movePosition(cursor.MoveOperation.StartOfLine)
        cursor.insertText(prefix)
        self._editor.setTextCursor(cursor)
        self._editor.setFocus()

    def _on_editor_changed(self) -> None:
        self._dirty = True
        self._update_title()
        # 预览可见时，通过防抖定时器触发刷新
        if self._preview.isVisible():
            self._preview_timer.start()

    def _update_title(self) -> None:
        title = "Firefly Markdown Assistant — 新建文件"
        if self._current_file:
            fname = Path(self._current_file).name
            title = f"{fname} — Firefly Markdown Assistant"
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
        self._show_status("Frontmatter 已生成", 3000)

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
        self._show_status("新建文件", 2000)

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
        self._show_status(f"已打开: {path}", 3000)

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
            self._show_status(f"已保存: {path}", 3000)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存失败：{e}")

    # ── 预览同步 ──────────────────────────────────
    def _sync_preview_scroll(self) -> None:
        """根据编辑器当前可见行比例，同步预览滚动位置。"""
        if not self._preview.isVisible():
            return
        editor_sb = self._editor.verticalScrollBar()
        preview_sb = self._preview.verticalScrollBar()
        if not editor_sb or not preview_sb:
            return

        # 使用光标所在行 + 总行数估算位置比例（比 scrollbar 值更稳定）
        cursor = self._editor.textCursor()
        line_num = cursor.blockNumber()
        total_lines = max(self._editor.blockCount(), 1)
        ratio = line_num / total_lines

        pmax = preview_sb.maximum()
        if pmax > 0:
            preview_sb.setValue(int(ratio * pmax))

    # ── 预览切换 ──────────────────────────────────
    def _toggle_preview(self) -> None:
        visible = not self._preview.isVisible()
        self._preview.setVisible(visible)
        if visible:
            self._update_preview()

    # ── Firefly 扩展语法 → HTML ─────────────────────
    @staticmethod
    def _convert_firefly_extensions(html: str) -> str:
        """将 Firefly 特殊语法转为带样式的 HTML。"""
        import re

        # --- Docusaurus 风格提醒框 :::type[title]\ncontent\n::: ---
        _ADMON_COLORS = {
            "note":      ("#89b4fa", "#1e1e2e", "📝"),
            "tip":       ("#a6e3a1", "#1e1e2e", "💡"),
            "info":      ("#89b4fa", "#1e1e2e", "ℹ️"),
            "important": ("#cba6f7", "#1e1e2e", "❗"),
            "warning":   ("#fab387", "#1e1e2e", "⚠️"),
            "danger":    ("#f38ba8", "#1e1e2e", "🔥"),
            "caution":   ("#f38ba8", "#1e1e2e", "⚠️"),
            "success":   ("#a6e3a1", "#1e1e2e", "✅"),
        }

        def _admon_repl(m: re.Match) -> str:
            atype = m.group(1).lower()
            title = m.group(2) or ""
            content = m.group(3).strip()
            color, text_color, icon = _ADMON_COLORS.get(
                atype, ("#89b4fa", "#1e1e2e", "📄")
            )
            disp_title = title if title else atype.upper()
            content_html = content.replace("\n", "<br>")
            return (
                f'<div style="background:#1e1e2e;border-left:4px solid {color};'
                f'border-radius:6px;padding:12px 16px;margin:12px 0">'
                f'<div style="font-weight:bold;color:{color};margin-bottom:6px">'
                f'{icon} {disp_title}</div>'
                f'<div style="color:#cdd6f4">{content_html}</div>'
                f'</div>'
            )

        html = re.sub(
            r":::(note|tip|info|important|warning|danger|caution|success)"
            r"(?:\[([^\]]*)\])?\n([\s\S]*?):::",
            _admon_repl, html,
        )

        # --- GitHub 风格提醒框 > [!NOTE]\n> content ---
        def _gh_callout_repl(m: re.Match) -> str:
            atype = m.group(1).lower()
            lines = m.group(2).strip().split("\n")
            color, text_color, icon = _ADMON_COLORS.get(
                atype, ("#89b4fa", "#1e1e2e", "📄")
            )
            # 去掉每行的 > 前缀
            body_lines = []
            for line in lines:
                stripped = line.strip()
                if stripped.startswith(">"):
                    stripped = stripped[1:].strip()
                body_lines.append(stripped)
            content_html = "<br>".join(body_lines)
            return (
                f'<div style="background:#1e1e2e;border-left:4px solid {color};'
                f'border-radius:6px;padding:12px 16px;margin:12px 0">'
                f'<div style="font-weight:bold;color:{color};margin-bottom:6px">'
                f'{icon} {atype.upper()}</div>'
                f'<div style="color:#cdd6f4">{content_html}</div>'
                f'</div>'
            )

        html = re.sub(
            r">\s*\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]\s*\n"
            r"((?:>.*\n?)+)",
            _gh_callout_repl, html,
            flags=re.IGNORECASE,
        )

        # --- 剧透 :spoiler[text] ---
        html = re.sub(
            r":spoiler\[([^\]]+)\]",
            r'<span style="background:#45475a;color:#45475a;'
            r'border-radius:4px;padding:2px 8px;cursor:pointer" '
            r'onmouseover="this.style.color=\'#cdd6f4\'" '
            r'onmouseout="this.style.color=\'#45475a\'">\1</span>',
            html,
        )

        # --- GitHub 仓库卡片 ::github{repo="Owner/Repo"} ---
        def _github_card_repl(m: re.Match) -> str:
            repo = m.group(1)
            return (
                f'<div style="background:#181825;border:1px solid #313244;'
                f'border-radius:8px;padding:12px;margin:12px 0;display:flex;'
                f'align-items:center;gap:12px">'
                f'<span style="font-size:20px">📦</span>'
                f'<div>'
                f'<div style="font-weight:bold;color:#89b4fa">{repo}</div>'
                f'<div style="color:#a6adc8;font-size:12px">'
                f'<a href="https://github.com/{repo}" style="color:#89b4fa">'
                f'github.com/{repo}</a></div>'
                f'</div></div>'
            )
        html = re.sub(r"::github\{repo=\"([^\"]+)\"\}", _github_card_repl, html)

        # --- 图片网格 [grid]\n![alt](url)\n[/grid] ---
        def _grid_repl(m: re.Match) -> str:
            images = m.group(1).strip().split("\n")
            imgs_html = ""
            for img in images:
                img = img.strip()
                if img:
                    imgs_html += (
                        f'<div style="flex:1 1 200px;max-width:300px">'
                        f'{img}'
                        f'</div>'
                    )
            return (
                f'<div style="display:flex;flex-wrap:wrap;gap:8px;'
                f'margin:12px 0">{imgs_html}</div>'
            )
        html = re.sub(r"\[grid\]\n([\s\S]*?)\[/grid\]", _grid_repl, html)

        # --- KaTeX 块级公式 $$...$$ ---
        def _katex_block_repl(m: re.Match) -> str:
            formula = m.group(1).strip()
            return (
                f'<div style="background:#181825;border:1px solid #313244;'
                f'border-radius:6px;padding:16px;margin:12px 0;text-align:center;'
                f'overflow-x:auto">'
                f'<code style="color:#cba6f7;font-family:\'Consolas\',monospace;'
                f'font-size:14px;white-space:pre">{formula}</code>'
                f'</div>'
            )
        html = re.sub(r"\$\$([^$]+)\$\$", _katex_block_repl, html)

        # --- KaTeX 行内公式 $...$ ---
        html = re.sub(
            r"(?<!\$)\$(?!\$)([^$]+)(?<!\$)\$(?!\$)",
            r'<code style="color:#cba6f7;background:#313244;'
            r'padding:1px 6px;border-radius:4px;font-family:\'Consolas\',monospace;'
            r'font-size:13px">\1</code>',
            html,
        )

        return html

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
                f'<pre style="background:#11111b;color:#cdd6f4;'
                f'padding:12px;border-radius:6px;overflow-x:auto;'
                f'font-size:12px;white-space:pre;margin:12px 0">{lang_tag}{safe}</pre>'
            )
            return f"%%CB{len(code_blocks) - 1}%%"

        html = re.sub(r"```([^\n]*)\n([\s\S]*?)```", _save_code, html)

        # ── 第 1.5 遍：Firefly 扩展语法 → HTML ──
        html = self._convert_firefly_extensions(html)

        # ── 第 2 遍：保护原始 HTML 标签（img / iframe / details / div 等）──
        raw_tags: list[str] = []

        def _protect_tag(m: re.Match) -> str:
            raw_tags.append(m.group(0))
            return f"%%HT{len(raw_tags) - 1}%%"

        # 自闭合标签 + 配对标签（覆盖 code/pre 防止 KaTeX 等被转义）
        html = re.sub(
            r'<(img|iframe|details|summary|div|span|br|hr|code|pre)\b[^>]*/?>|'
            r'</(iframe|details|summary|div|span|code|pre)>',
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
        html = re.sub(r"\b_([^_]+)_\b", r"<em>\1</em>", html)  # _italic_ 下划线斜体
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

        # 恢复预览滚动位置，减少抖动
        if saved_scroll > 0 and preview_sb:
            preview_sb.setValue(min(saved_scroll, preview_sb.maximum()))

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