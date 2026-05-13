"""Mermaid 图表创建对话框。"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QTextEdit, QPushButton, QGroupBox,
)

from core.markdown_utils import MERMAID_TEMPLATES, mermaid_snippet


class MermaidDialog(QDialog):
    """Mermaid 图表创建对话框。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("插入 Mermaid 图表")
        self.setMinimumSize(560, 420)
        self.setModal(True)
        self._snippet: str = ""
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        type_group = QGroupBox("图表类型")
        type_layout = QVBoxLayout(type_group)
        self._type_combo = QComboBox()
        self._type_combo.addItems(list(MERMAID_TEMPLATES.keys()))
        self._type_combo.currentTextChanged.connect(self._on_type_changed)
        type_layout.addWidget(self._type_combo)
        layout.addWidget(type_group)

        code_group = QGroupBox("Mermaid 代码")
        code_layout = QVBoxLayout(code_group)
        self._code_edit = QTextEdit()
        self._code_edit.setMinimumHeight(200)
        code_layout.addWidget(self._code_edit)
        layout.addWidget(code_group)

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

        self._on_type_changed(self._type_combo.currentText())

    def _on_type_changed(self, diagram_type: str) -> None:
        if diagram_type in MERMAID_TEMPLATES:
            self._code_edit.setPlainText(MERMAID_TEMPLATES[diagram_type])

    def _on_insert(self) -> None:
        dtype = self._type_combo.currentText()
        code = self._code_edit.toPlainText().strip()
        self._snippet = mermaid_snippet(dtype, code)
        self.accept()

    def snippet(self) -> str:
        return self._snippet
