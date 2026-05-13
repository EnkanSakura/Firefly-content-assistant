"""Firefly Markdown Assistant — 启动入口。

一款专为 Firefly Astro 博客主题设计的 Markdown 文章辅助生成工具。
支持 Frontmatter 可视化编辑、提醒框、代码块、Mermaid/PlantUML 图表、
KaTeX 数学公式、图片网格等全部 Firefly 扩展语法。
"""

from __future__ import annotations

import sys
from pathlib import Path

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from app.constants import APP_STYLESHEET
from ui.main_window import MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Firefly Markdown Assistant")
    app.setStyleSheet(APP_STYLESHEET)

    # 高 DPI 支持
    if hasattr(Qt, "AA_EnableHighDpiScaling"):
        app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, "AA_UseHighDpiPixmaps"):
        app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
