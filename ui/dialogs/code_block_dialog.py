"""代码块（Expressive Code）创建对话框。"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QLineEdit, QTextEdit, QPushButton, QCheckBox, QGroupBox,
    QSpinBox, QFormLayout,
)
from PySide6.QtCore import Qt

from core.markdown_utils import code_block_snippet


LANGUAGES = [
    "", "js", "ts", "jsx", "tsx", "py", "rs", "go", "java",
    "c", "cpp", "cs", "rb", "php", "swift", "kotlin", "scala",
    "html", "css", "scss", "json", "yaml", "toml", "xml",
    "sql", "graphql", "bash", "sh", "powershell", "ps", "zsh",
    "dockerfile", "nginx", "makefile", "cmake",
    "md", "markdown", "diff", "ansi",
]


class CodeBlockDialog(QDialog):
    """Expressive Code 代码块创建对话框。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("插入代码块")
        self.setMinimumSize(600, 550)
        self.setModal(True)
        self._snippet: str = ""
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # 基础选项
        basic = QGroupBox("基础选项")
        form = QFormLayout(basic)

        self._lang_combo = QComboBox()
        self._lang_combo.setEditable(True)
        self._lang_combo.addItems(LANGUAGES)
        form.addRow("语言:", self._lang_combo)

        self._title_edit = QLineEdit()
        self._title_edit.setPlaceholderText("例如: my-file.js")
        form.addRow("标题:", self._title_edit)

        self._frame_combo = QComboBox()
        self._frame_combo.addItems(["", "code", "terminal", "none"])
        form.addRow("框架类型:", self._frame_combo)

        layout.addWidget(basic)

        # 高级选项
        adv = QGroupBox("行标记与高亮")
        adv_form = QFormLayout(adv)

        self._line_markers = QLineEdit()
        self._line_markers.setPlaceholderText("例如: {1, 4, 7-8}")
        adv_form.addRow("行标记:", self._line_markers)

        self._del_lines = QLineEdit()
        self._del_lines.setPlaceholderText("例如: del={2}")
        adv_form.addRow("删除行:", self._del_lines)

        self._ins_lines = QLineEdit()
        self._ins_lines.setPlaceholderText("例如: ins={3-4}")
        adv_form.addRow("插入行:", self._ins_lines)

        self._text_markers = QLineEdit()
        self._text_markers.setPlaceholderText('例如: "text" 或 /regex/')
        adv_form.addRow("文本标记:", self._text_markers)

        layout.addWidget(adv)

        # 其他选项
        opts = QGroupBox("其他选项")
        opts_layout = QVBoxLayout(opts)
        opts_row = QHBoxLayout()
        self._show_lines = QCheckBox("显示行号")
        opts_row.addWidget(self._show_lines)

        self._start_line = QSpinBox()
        self._start_line.setRange(1, 9999)
        self._start_line.setValue(1)
        self._start_line.setEnabled(False)
        self._show_lines.toggled.connect(self._start_line.setEnabled)
        opts_row.addWidget(QLabel("起始行号:"))
        opts_row.addWidget(self._start_line)
        opts_row.addStretch()
        opts_layout.addLayout(opts_row)

        wrap_row = QHBoxLayout()
        self._wrap_combo = QComboBox()
        self._wrap_combo.addItems(["", "wrap", "wrap=false",
                                    "wrap preserveIndent",
                                    "wrap preserveIndent=false"])
        wrap_row.addWidget(QLabel("自动换行:"))
        wrap_row.addWidget(self._wrap_combo)
        wrap_row.addStretch()
        opts_layout.addLayout(wrap_row)

        self._diff_chk = QCheckBox("diff 语法 (行首 +/-)")
        opts_layout.addWidget(self._diff_chk)

        self._collapse_edit = QLineEdit()
        self._collapse_edit.setPlaceholderText("例如: collapse={1-5, 12-14}")
        opts_layout.addWidget(QLabel("可折叠行范围:"))
        opts_layout.addWidget(self._collapse_edit)

        layout.addWidget(opts)

        # 代码内容
        code_group = QGroupBox("代码内容")
        code_layout = QVBoxLayout(code_group)
        self._code_edit = QTextEdit()
        self._code_edit.setPlaceholderText("在此输入代码...")
        self._code_edit.setMinimumHeight(120)
        code_layout.addWidget(self._code_edit)
        layout.addWidget(code_group)

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

    def _on_insert(self) -> None:
        lang = self._lang_combo.currentText().strip()
        if self._diff_chk.isChecked() and not lang:
            lang = "diff"

        show_ln = ""
        if self._show_lines.isChecked():
            show_ln = "showLineNumbers"

        text_markers = []
        tm = self._text_markers.text().strip()
        if tm:
            text_markers = [p.strip() for p in tm.split(",")]

        self._snippet = code_block_snippet(
            code=self._code_edit.toPlainText(),
            language=lang,
            title=self._title_edit.text().strip(),
            frame=self._frame_combo.currentText(),
            line_markers=self._line_markers.text().strip(),
            del_lines=self._del_lines.text().strip(),
            ins_lines=self._ins_lines.text().strip(),
            text_markers=text_markers,
            wrap_mode=self._wrap_combo.currentText(),
            collapse=self._collapse_edit.text().strip(),
            show_line_numbers=show_ln,
            start_line=self._start_line.value(),
        )
        self.accept()

    def snippet(self) -> str:
        return self._snippet
