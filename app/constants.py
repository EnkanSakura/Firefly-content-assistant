"""应用常量和配置。"""

# 窗口默认尺寸
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 800
WINDOW_MIN_WIDTH = 900
WINDOW_MIN_HEIGHT = 600

# 字体
EDITOR_FONT_FAMILY = "Consolas, 'Cascadia Code', 'JetBrains Mono', monospace"
EDITOR_FONT_SIZE = 13
UI_FONT_SIZE = 13

# 样式表（暗色主题）
APP_STYLESHEET = """
QMainWindow {
    background-color: transparent;
    color: #cdd6f4;
}
QMenuBar {
    background-color: #181825;
    color: #cdd6f4;
    border-bottom: 1px solid #313244;
    padding: 2px;
}
QMenuBar::item:selected {
    background-color: #45475a;
    border-radius: 4px;
}
QMenu {
    background-color: #1e1e2e;
    color: #cdd6f4;
    border: 1px solid #313244;
    padding: 4px;
}
QMenu::item:selected {
    background-color: #45475a;
    border-radius: 4px;
}
QToolBar {
    background-color: #181825;
    border-right: 1px solid #313244;
    spacing: 4px;
    padding: 4px;
}
QToolButton {
    background-color: transparent;
    color: #cdd6f4;
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}
QToolButton:hover {
    background-color: #313244;
    border-color: #45475a;
}
QToolButton:pressed {
    background-color: #45475a;
}
QToolButton:checked {
    background-color: #313244;
    border-color: #89b4fa;
}
QPlainTextEdit {
    background-color: #1e1e2e;
    color: #cdd6f4;
    border: 1px solid #313244;
    border-radius: 6px;
    padding: 8px;
    font-family: 'Consolas', 'Cascadia Code', monospace;
    font-size: 13px;
    selection-background-color: #45475a;
}
QTextEdit {
    background-color: #1e1e2e;
    color: #cdd6f4;
    border: 1px solid #313244;
    border-radius: 6px;
    padding: 8px;
    font-size: 13px;
}
QLineEdit, QTextEdit, QSpinBox, QDateEdit, QComboBox {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 12px;
}
QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QDateEdit:focus, QComboBox:focus {
    border-color: #89b4fa;
}
QComboBox::drop-down {
    border: none;
    padding-right: 6px;
}
QComboBox QAbstractItemView {
    background-color: #313244;
    color: #cdd6f4;
    selection-background-color: #45475a;
    border: 1px solid #45475a;
}
QCheckBox {
    color: #cdd6f4;
    spacing: 6px;
    font-size: 12px;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #45475a;
    border-radius: 3px;
    background-color: #313244;
}
QCheckBox::indicator:checked {
    background-color: #89b4fa;
    border-color: #89b4fa;
}
QLabel {
    color: #cdd6f4;
}
QGroupBox {
    color: #cdd6f4;
    border: 1px solid #313244;
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 16px;
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}
QPushButton {
    background-color: #45475a;
    color: #cdd6f4;
    border: 1px solid #585b70;
    border-radius: 6px;
    padding: 6px 16px;
    font-size: 12px;
}
QPushButton:hover {
    background-color: #585b70;
}
QPushButton:pressed {
    background-color: #313244;
}
QPushButton#primary {
    background-color: #89b4fa;
    color: #1e1e2e;
    border: none;
    font-weight: bold;
}
QPushButton#primary:hover {
    background-color: #b4d0fb;
}
QStatusBar {
    background-color: #181825;
    color: #a6adc8;
    border-top: 1px solid #313244;
    font-size: 11px;
}
QScrollBar:vertical {
    background-color: #1e1e2e;
    width: 10px;
    border-radius: 5px;
}
QScrollBar::handle:vertical {
    background-color: #45475a;
    border-radius: 5px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background-color: #585b70;
}
QScrollBar:horizontal {
    background-color: #1e1e2e;
    height: 10px;
    border-radius: 5px;
}
QScrollBar::handle:horizontal {
    background-color: #45475a;
    border-radius: 5px;
    min-width: 30px;
}
QTabWidget::pane {
    border: 1px solid #313244;
    border-radius: 6px;
    background-color: #1e1e2e;
}
QTabBar::tab {
    background-color: #181825;
    color: #a6adc8;
    padding: 6px 16px;
    border: 1px solid #313244;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background-color: #1e1e2e;
    color: #cdd6f4;
    border-bottom: 2px solid #89b4fa;
}
QTabBar::tab:hover {
    color: #cdd6f4;
}
QSplitter::handle {
    background-color: #313244;
    width: 2px;
    height: 2px;
}
QDialog {
    background-color: #1e1e2e;
    color: #cdd6f4;
}
QListWidget {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 4px;
}
QListWidget::item:selected {
    background-color: #45475a;
}
QListWidget::item:hover {
    background-color: #3a3b4e;
}
"""
