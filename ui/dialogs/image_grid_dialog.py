"""图片画廊网格创建对话框。"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QGroupBox,
)

from core.markdown_utils import image_grid_snippet


class ImageGridDialog(QDialog):
    """图片网格创建对话框 —— 最多 4 张图片。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("插入图片网格")
        self.setMinimumSize(480, 280)
        self.setModal(True)
        self._snippet: str = ""
        self._edits: list[QLineEdit] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        group = QGroupBox("图片路径 (最多 4 张)")
        gl = QVBoxLayout(group)

        for i in range(4):
            row = QHBoxLayout()
            row.addWidget(QLabel(f"图片 {i + 1}:"))
            edit = QLineEdit()
            edit.setPlaceholderText(f"./images/example{i+1}.avif")
            row.addWidget(edit)
            gl.addLayout(row)
            self._edits.append(edit)

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
        paths = [e.text().strip() for e in self._edits if e.text().strip()]
        if not paths:
            self.reject()
            return
        self._snippet = image_grid_snippet(paths)
        self.accept()

    def snippet(self) -> str:
        return self._snippet
