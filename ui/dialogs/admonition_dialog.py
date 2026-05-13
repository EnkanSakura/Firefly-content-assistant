"""提醒框（Callout / Admonition）创建对话框。"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QLineEdit, QTextEdit, QPushButton, QGroupBox,
)
from PySide6.QtCore import Qt

from core.markdown_utils import (
    CALLOUT_STYLES, admonition_snippet,
)


class AdmonitionDialog(QDialog):
    """提醒框创建对话框 —— 支持四种风格和多种类型。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("插入提醒框")
        self.setMinimumSize(520, 400)
        self.setModal(True)
        self._snippet: str = ""
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # 风格选择
        style_group = QGroupBox("提醒框风格")
        style_layout = QVBoxLayout(style_group)
        self._style_combo = QComboBox()
        self._style_combo.addItems(list(CALLOUT_STYLES.keys()))
        self._style_combo.currentTextChanged.connect(self._on_style_changed)
        style_layout.addWidget(self._style_combo)
        layout.addWidget(style_group)

        # 类型选择
        type_group = QGroupBox("类型")
        type_layout = QVBoxLayout(type_group)
        self._type_combo = QComboBox()
        self._type_combo.setEditable(True)
        type_layout.addWidget(self._type_combo)
        layout.addWidget(type_group)

        # 自定义标题
        title_layout = QHBoxLayout()
        title_layout.addWidget(QLabel("自定义标题:"))
        self._title_edit = QLineEdit()
        self._title_edit.setPlaceholderText("留空使用默认类型名")
        title_layout.addWidget(self._title_edit)
        layout.addLayout(title_layout)

        # 内容
        content_group = QGroupBox("提醒框内容")
        content_layout = QVBoxLayout(content_group)
        self._content_edit = QTextEdit()
        self._content_edit.setPlaceholderText("输入提醒框正文...")
        self._content_edit.setMinimumHeight(100)
        content_layout.addWidget(self._content_edit)
        layout.addWidget(content_group)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        insert_btn = QPushButton("插入")
        insert_btn.setObjectName("primary")
        insert_btn.clicked.connect(self._on_insert)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(insert_btn)
        layout.addLayout(btn_layout)

        self._on_style_changed("GitHub")

    def _on_style_changed(self, style: str) -> None:
        self._type_combo.clear()
        self._type_combo.addItems(CALLOUT_STYLES[style]["types"])

    def _on_insert(self) -> None:
        style = self._style_combo.currentText()
        ctype = self._type_combo.currentText()
        title = self._title_edit.text().strip()
        content = self._content_edit.toPlainText().strip()
        self._snippet = admonition_snippet(style, ctype, title, content)
        self.accept()

    def snippet(self) -> str:
        return self._snippet
