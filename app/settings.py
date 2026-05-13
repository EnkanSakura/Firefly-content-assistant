"""Firefly Markdown Assistant — 应用配置（QSettings 持久化）"""

from __future__ import annotations

from pathlib import Path
from PySide6.QtCore import QSettings, QByteArray


class AppSettings:
    """封装 QSettings 的应用配置访问。

    存储位置：Windows 下写入注册表 HKCU\Software\Firefly MDA
    """

    _ORG = "FireflyMDA"
    _APP = "FireflyMarkdownAssistant"

    def __init__(self) -> None:
        self._s = QSettings(self._ORG, self._APP)

    # ── 工作目录 ────────────────────────────────────────────────

    @property
    def workspace_dir(self) -> str:
        return self._s.value("workspace_dir", "")

    @workspace_dir.setter
    def workspace_dir(self, value: str) -> None:
        self._s.setValue("workspace_dir", value)

    # ── 最近文件 ────────────────────────────────────────────────

    def recent_files(self) -> list[str]:
        val = self._s.value("recent_files", [])
        return val if isinstance(val, list) else []

    def add_recent_file(self, path: str) -> None:
        files = self.recent_files()
        if path in files:
            files.remove(path)
        files.insert(0, path)
        self._s.setValue("recent_files", files[:10])

    # ── 窗口几何 ────────────────────────────────────────────────

    @property
    def window_geometry(self) -> QByteArray | None:
        return self._s.value("window_geometry")

    @window_geometry.setter
    def window_geometry(self, value: QByteArray) -> None:
        self._s.setValue("window_geometry", value)

    @property
    def window_state(self) -> QByteArray | None:
        return self._s.value("window_state")

    @window_state.setter
    def window_state(self, value: QByteArray) -> None:
        self._s.setValue("window_state", value)

    @property
    def splitter_sizes(self) -> list[int]:
        val = self._s.value("splitter_sizes", [250, 500, 350])
        if isinstance(val, list):
            return [int(v) for v in val]
        return [250, 500, 350]

    @splitter_sizes.setter
    def splitter_sizes(self, value: list[int]) -> None:
        self._s.setValue("splitter_sizes", value)

    # ── 编辑器配置 ──────────────────────────────────────────────

    @property
    def editor_font_family(self) -> str:
        return self._s.value("editor_font_family", "Consolas")

    @editor_font_family.setter
    def editor_font_family(self, value: str) -> None:
        self._s.setValue("editor_font_family", value)

    @property
    def editor_font_size(self) -> int:
        val = self._s.value("editor_font_size", 14)
        return int(val)

    @editor_font_size.setter
    def editor_font_size(self, value: int) -> None:
        self._s.setValue("editor_font_size", value)

    @property
    def tab_width(self) -> int:
        val = self._s.value("tab_width", 4)
        return int(val)

    @tab_width.setter
    def tab_width(self, value: int) -> None:
        self._s.setValue("tab_width", value)

    @property
    def word_wrap(self) -> bool:
        val = self._s.value("word_wrap", True)
        return val if isinstance(val, bool) else True

    @word_wrap.setter
    def word_wrap(self, value: bool) -> None:
        self._s.setValue("word_wrap", value)

    # ── 预览配置 ────────────────────────────────────────────────

    @property
    def auto_preview(self) -> bool:
        val = self._s.value("auto_preview", True)
        return val if isinstance(val, bool) else True

    @auto_preview.setter
    def auto_preview(self, value: bool) -> None:
        self._s.setValue("auto_preview", value)

    @property
    def preview_delay_ms(self) -> int:
        val = self._s.value("preview_delay_ms", 300)
        return int(val)

    @preview_delay_ms.setter
    def preview_delay_ms(self, value: int) -> None:
        self._s.setValue("preview_delay_ms", value)

    # ── 标签/分类历史 ───────────────────────────────────────────

    @property
    def tag_history(self) -> list[str]:
        val = self._s.value("tag_history", [])
        return val if isinstance(val, list) else []

    def add_tag(self, tag: str) -> None:
        tags = self.tag_history
        if tag in tags:
            tags.remove(tag)
        tags.insert(0, tag)
        self._s.setValue("tag_history", tags[:50])

    @property
    def category_history(self) -> list[str]:
        val = self._s.value("category_history", ["文章示例"])
        return val if isinstance(val, list) else ["文章示例"]

    def add_category(self, cat: str) -> None:
        cats = self.category_history
        if cat in cats:
            cats.remove(cat)
        cats.insert(0, cat)
        self._s.setValue("category_history", cats[:30])
