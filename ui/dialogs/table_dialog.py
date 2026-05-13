"""表格创建对话框。"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox,
    QPushButton, QGroupBox, QFormLayout,
)

from core.markdown_utils import table_snippet


class TableDialog(QDialog):
    """表格创建对话框。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("插入表格")
        self.setMinimumSize(320, 180)
        self.setModal(True)
        self._snippet: str = ""
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        group = QGroupBox("表格尺寸")
        form = QFormLayout(group)

        self._rows_spin = QSpinBox()
        self._rows_spin.setRange(2, 20)
        self._rows_spin.setValue(3)
        form.addRow("行数:", self._rows_spin)

        self._cols_spin = QSpinBox()
        self._cols_spin.setRange(2, 10)
        self._cols_spin.setValue(3)
        form.addRow("列数:", self._cols_spin)

        layout.addWidget(group)

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

    def _on_insert(self) -> None:
        self._snippet = table_snippet(
            self._rows_spin.value(),
            self._cols_spin.value(),
        )
        self.accept()

    def snippet(self) -> str:
        return self._snippet
