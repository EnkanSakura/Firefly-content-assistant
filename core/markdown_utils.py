"""Firefly Markdown 语法模板与生成工具。

为 Firefly Astro 博客主题提供所有扩展语法的模板定义、
代码片段生成与 Frontmatter 构建函数。
"""

from __future__ import annotations

import textwrap
from datetime import date, datetime
from typing import Any

# ---------------------------------------------------------------------------
# Frontmatter
# ---------------------------------------------------------------------------

FRONTMATTER_FIELDS: dict[str, dict[str, Any]] = {
    "title":        {"label": "标题",       "type": "text",     "required": True,  "default": ""},
    "published":    {"label": "发布日期",   "type": "date",     "required": False, "default": date.today().isoformat()},
    "updated":      {"label": "更新日期",   "type": "date",     "required": False, "default": ""},
    "pinned":       {"label": "置顶",       "type": "bool",     "required": False, "default": False},
    "description":  {"label": "描述",       "type": "text",     "required": False, "default": ""},
    "image":        {"label": "封面图",     "type": "text",     "required": False, "default": ""},
    "tags":         {"label": "标签",       "type": "tags",     "required": False, "default": []},
    "category":     {"label": "分类",       "type": "text",     "required": False, "default": ""},
    "draft":        {"label": "草稿",       "type": "bool",     "required": False, "default": False},
    "password":     {"label": "文章密码",   "type": "text",     "required": False, "default": ""},
    "passwordHint": {"label": "密码提示",   "type": "text",     "required": False, "default": ""},
    "licenseName":  {"label": "许可证",     "type": "text",     "required": False, "default": ""},
    "author":       {"label": "作者",       "type": "text",     "required": False, "default": ""},
    "sourceLink":   {"label": "源链接",     "type": "text",     "required": False, "default": ""},
}

FRONTMATTER_ORDER = list(FRONTMATTER_FIELDS.keys())


def build_frontmatter(values: dict[str, Any]) -> str:
    """根据字段值字典构建 YAML frontmatter 字符串。

    空值字段自动跳过；tags 以 YAML 流式数组输出。
    """
    lines: list[str] = ["---"]
    for key in FRONTMATTER_ORDER:
        if key not in values:
            continue
        val = values[key]
        # 跳过空值（bool 型 False 保留，列表空则跳过）
        if val is None or val == "":
            if key in ("draft", "pinned"):
                pass
            else:
                continue
        if isinstance(val, list) and len(val) == 0:
            continue

        if isinstance(val, bool):
            lines.append(f"{key}: {str(val).lower()}")
        elif isinstance(val, list):
            tags_str = ", ".join(repr(t) if " " in t else t for t in val)
            lines.append(f"{key}: [{tags_str}]")
        elif isinstance(val, (date, datetime)):
            lines.append(f"{key}: {val.isoformat()}")
        elif isinstance(val, str):
            if any(c in val for c in (":", "#", "{", "}", "[", "]", ",",
                                        "&", "*", "!", "|", ">", "<", "%", "@", "`")):
                lines.append(f'{key}: "{val}"')
            else:
                lines.append(f"{key}: {val}")
        else:
            lines.append(f"{key}: {val}")
    lines.append("---\n")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 提醒框 (Admonitions / Callouts)
# ---------------------------------------------------------------------------

GITHUB_CALLOUT_TYPES = ["NOTE", "TIP", "IMPORTANT", "WARNING", "CAUTION"]
OBSIDIAN_CALLOUT_TYPES = [
    "NOTE", "ABSTRACT", "SUMMARY", "TLDR", "INFO", "TODO",
    "TIP", "HINT", "IMPORTANT", "SUCCESS", "CHECK", "DONE",
    "QUESTION", "HELP", "FAQ", "WARNING", "CAUTION", "ATTENTION",
    "FAILURE", "FAIL", "MISSING", "DANGER", "ERROR", "BUG",
    "EXAMPLE", "QUOTE", "CITE",
]
VITEPRESS_CALLOUT_TYPES = ["NOTE", "TIP", "IMPORTANT", "WARNING", "CAUTION"]
DOCUSAURUS_CALLOUT_TYPES = ["note", "tip", "important", "warning", "caution"]

CALLOUT_STYLES = {
    "GitHub":     {"prefix": "> [!", "types": GITHUB_CALLOUT_TYPES,   "wrap_each_line": True},
    "Obsidian":   {"prefix": "> [!", "types": OBSIDIAN_CALLOUT_TYPES, "wrap_each_line": True},
    "VitePress":  {"prefix": "> [!", "types": VITEPRESS_CALLOUT_TYPES,"wrap_each_line": True},
    "Docusaurus": {"prefix": ":::",    "types": DOCUSAURUS_CALLOUT_TYPES,
                   "wrap_each_line": False, "suffix": ":::"},
}


def admonition_snippet(style: str, callout_type: str,
                       title: str = "", content: str = "") -> str:
    """生成提醒框 Markdown 片段。"""
    cfg = CALLOUT_STYLES[style]
    display_title = title.strip() if title.strip() else callout_type

    if style == "Docusaurus":
        if title.strip():
            return f":::{callout_type}[{display_title}]\n{content}\n:::"
        else:
            return f":::{callout_type}\n{content}\n:::"
    else:
        header = f"> [!{callout_type}] {display_title}"
        if not content.strip():
            return header
        content_lines = content.strip().split("\n")
        body = "\n".join(f"> {line}" for line in content_lines)
        return f"{header}\n{body}"


# ---------------------------------------------------------------------------
# 图片画廊网格
# ---------------------------------------------------------------------------

def image_grid_snippet(image_paths: list[str]) -> str:
    """生成 [grid] 图片画廊片段。"""
    lines = ["[grid]"]
    for p in image_paths:
        alt = p.rsplit("/", 1)[-1] if "/" in p else p
        lines.append(f"![{alt}]({p})")
    lines.append("[/grid]")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# GitHub 仓库卡片
# ---------------------------------------------------------------------------

def github_card_snippet(repo: str) -> str:
    """生成 GitHub 仓库卡片。"""
    return f"::github{{repo=\"{repo}\"}}"


# ---------------------------------------------------------------------------
# 剧透
# ---------------------------------------------------------------------------

def spoiler_snippet(text: str) -> str:
    """生成剧透文本。"""
    return f":spoiler[{text}]"


# ---------------------------------------------------------------------------
# 视频嵌入
# ---------------------------------------------------------------------------

def video_snippet(platform: str, video_id: str, width: str = "100%",
                  height: str = "468") -> str:
    """生成视频 iframe 嵌入代码。"""
    if platform == "youtube":
        src = f"https://www.youtube.com/embed/{video_id}"
        extra = ('allow="accelerometer; autoplay; clipboard-write; '
                 'encrypted-media; gyroscope; picture-in-picture; web-share" '
                 'allowfullscreen')
    elif platform == "bilibili":
        src = f"//player.bilibili.com/player.html?bvid={video_id}&p=1&autoplay=0"
        extra = ('scrolling="no" border="0" frameborder="no" '
                 'framespacing="0" allowfullscreen="true"')
    else:
        raise ValueError(f"不支持的平台: {platform}")

    return (
        f'<iframe width="{width}" height="{height}" '
        f'src="{src}" '
        f'title="{platform} video player" '
        f'frameborder="0" {extra}></iframe>'
    )


# ---------------------------------------------------------------------------
# 可折叠部分
# ---------------------------------------------------------------------------

def details_snippet(summary: str, content: str) -> str:
    """生成 <details> 可折叠块。"""
    return f"<details>\n<summary>{summary}</summary>\n\n{content}\n\n</details>"


# ---------------------------------------------------------------------------
# 代码块 (Expressive Code)
# ---------------------------------------------------------------------------

def code_block_snippet(
    code: str = "",
    language: str = "",
    title: str = "",
    frame: str = "",
    line_markers: str = "",
    del_lines: str = "",
    ins_lines: str = "",
    text_markers: list[str] | None = None,
    wrap_mode: str = "",
    collapse: str = "",
    show_line_numbers: str = "",
    start_line: int = 0,
    diff_lang: str = "",
) -> str:
    """生成带 Expressive Code 选项的代码块。"""
    meta_parts: list[str] = []

    if language:
        meta_parts.append(language)
    if title:
        meta_parts.append(f'title="{title}"')
    if frame:
        meta_parts.append(f'frame="{frame}"')
    if line_markers:
        meta_parts.append(line_markers)
    if del_lines:
        meta_parts.append(del_lines)
    if ins_lines:
        meta_parts.append(ins_lines)
    if text_markers:
        for tm in text_markers:
            meta_parts.append(tm)
    if wrap_mode:
        meta_parts.append(wrap_mode)
    if collapse:
        meta_parts.append(collapse)
    if show_line_numbers:
        meta_parts.append(show_line_numbers)
    if start_line > 0 and "showLineNumbers" in show_line_numbers:
        meta_parts.append(f"startLineNumber={start_line}")
    if diff_lang:
        meta_parts.append(f'lang="{diff_lang}"')

    header = " ".join(meta_parts)
    return f"```{header}\n{code}\n```"


# ---------------------------------------------------------------------------
# Mermaid 图表模板
# ---------------------------------------------------------------------------

MERMAID_TEMPLATES: dict[str, str] = {
    "流程图": textwrap.dedent("""\
    graph TD
        A[开始] --> B{条件检查}
        B -->|是| C[处理步骤 1]
        B -->|否| D[处理步骤 2]
        C --> E[结束]
        D --> E"""),
    "时序图": textwrap.dedent("""\
    sequenceDiagram
        participant A as 客户端
        participant B as 服务器
        A->>B: 发送请求
        B-->>A: 返回响应"""),
    "甘特图": textwrap.dedent("""\
    gantt
        title 项目计划
        dateFormat  YYYY-MM-DD
        section 阶段一
        任务A      :a1, 2024-01-01, 7d
        任务B      :a2, after a1, 5d"""),
    "类图": textwrap.dedent("""\
    classDiagram
        class Animal {
            +String name
            +int age
            +makeSound()
        }
        class Dog {
            +breed
            +bark()
        }
        Animal <|-- Dog"""),
    "状态图": textwrap.dedent("""\
    stateDiagram-v2
        [*] --> 待处理
        待处理 --> 处理中 : 开始
        处理中 --> 已完成 : 成功
        处理中 --> 失败 : 异常
        已完成 --> [*]
        失败 --> [*]"""),
    "饼图": textwrap.dedent("""\
    pie title 数据分布
        "类别A" : 40
        "类别B" : 30
        "类别C" : 20
        "类别D" : 10"""),
}


def mermaid_snippet(diagram_type: str, content: str = "") -> str:
    """生成 Mermaid 代码块。"""
    if not content.strip() and diagram_type in MERMAID_TEMPLATES:
        content = MERMAID_TEMPLATES[diagram_type]
    return f"```mermaid\n{content.strip()}\n```"


# ---------------------------------------------------------------------------
# PlantUML 图表模板
# ---------------------------------------------------------------------------

PLANTUML_TEMPLATES: dict[str, str] = {
    "活动图": textwrap.dedent("""\
    @startuml
    start
    :步骤 1;
    if (条件?) then (是)
        :步骤 2;
    else (否)
        :步骤 3;
    endif
    stop
    @enduml"""),
    "状态图": textwrap.dedent("""\
    @startuml
    [*] --> 状态1
    状态1 --> 状态2 : 事件
    状态2 --> [*]
    @enduml"""),
    "用例图": textwrap.dedent("""\
    @startuml
    left to right direction
    actor 用户
    rectangle 系统 {
        usecase "功能1" as UC1
        usecase "功能2" as UC2
    }
    用户 --> UC1
    用户 --> UC2
    @enduml"""),
    "组件图": textwrap.dedent("""\
    @startuml
    package "应用" {
        [前端] as Frontend
        [后端] as Backend
        database "数据库" as DB
    }
    Frontend --> Backend
    Backend --> DB
    @enduml"""),
    "部署图": textwrap.dedent("""\
    @startuml
    node "服务器" {
        artifact "应用"
    }
    node "客户端" {
        artifact "浏览器"
    }
    @enduml"""),
    "ER图": textwrap.dedent("""\
    @startuml
    entity User {
        *id : uuid <<PK>>
        --
        username : varchar
        email : varchar
    }
    @enduml"""),
    "时序图": textwrap.dedent("""\
    @startuml
    Alice -> Bob: Hello
    Bob --> Alice: Hi
    @enduml"""),
    "C4容器图": textwrap.dedent("""\
    @startuml
    !includeurl https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Container.puml

    Person(user, "用户", "描述")

    System_Boundary(system, "系统") {
        Container(app, "应用", "技术栈", "描述")
        ContainerDb(db, "数据库", "类型", "描述")
    }

    Rel(user, app, "使用")
    Rel(app, db, "读写")
    @enduml"""),
}


def plantuml_snippet(diagram_type: str, content: str = "") -> str:
    """生成 PlantUML 代码块。"""
    if not content.strip() and diagram_type in PLANTUML_TEMPLATES:
        content = PLANTUML_TEMPLATES[diagram_type]
    return f"```plantuml\n{content.strip()}\n```"


# ---------------------------------------------------------------------------
# KaTeX 数学公式模板
# ---------------------------------------------------------------------------

KATEX_EXAMPLES: dict[str, str] = {
    "行内公式": "$E = mc^2$",
    "块级公式": "$$\n\\int_{-\\infty}^{\\infty} e^{-x^2} dx = \\sqrt{\\pi}\n$$",
    "矩阵": (
        "$$\n"
        "\\begin{pmatrix}\n"
        "a & b \\\\\n"
        "c & d\n"
        "\\end{pmatrix}\n"
        "$$"
    ),
    "化学方程式": "$$\n\\ce{CH4 + 2O2 -> CO2 + 2H2O}\n$$",
}


def katex_snippet(formula_type: str = "块级公式", custom: str = "") -> str:
    """生成 KaTeX 公式片段。"""
    if custom.strip():
        return custom
    return KATEX_EXAMPLES.get(formula_type, "$$公式$$")


# ---------------------------------------------------------------------------
# 表格
# ---------------------------------------------------------------------------

def table_snippet(rows: int = 3, cols: int = 3) -> str:
    """生成空表格模板。"""
    header = "| " + " | ".join(f"列{i+1}" for i in range(cols)) + " |"
    sep    = "| " + " | ".join(":---" for _ in range(cols)) + " |"
    body_lines = [
        "| " + " | ".join("" for _ in range(cols)) + " |"
        for _ in range(rows)
    ]
    return "\n".join([header, sep] + body_lines)
