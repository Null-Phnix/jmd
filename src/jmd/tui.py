"""JMD TUI Viewer — rich terminal display for .jmd files."""

import re
import sys
from pathlib import Path

from rich.console import Console, Group
from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text
from rich import box

from .parser import parse, JMDDocument, _ANNO_RE


def open_file(path: str, console: Console = None):
    p = Path(path)
    if not p.exists():
        print(f"Error: File not found: {p}", file=sys.stderr)
        sys.exit(1)

    raw = p.read_text()
    doc = parse(raw)
    _render_tui(doc, raw, console)


def _render_tui(doc: JMDDocument, raw: str, console: Console = None):
    if console is None:
        console = Console()

    left = _build_left_panel(doc)
    center = _build_body_panel(doc)
    right = _build_right_panel(doc)

    layout = Layout()
    layout.split_row(
        Layout(left, name="left", size=30),
        Layout(center, name="center", ratio=2),
        Layout(right, name="right", size=34),
    )

    console.print(layout)
    console.print()
    console.print(
        "[dim]Keys: q=quit | a=toggle annotations | j/k=scroll | n/p=next/prev anno (not interactive yet)[/dim]"
    )


def _build_left_panel(doc: JMDDocument) -> Panel:
    meta_text = Text()
    if doc.meta.title:
        meta_text.append(doc.meta.title, style="bold magenta")
        meta_text.append("\n")
    if doc.meta.author:
        meta_text.append("By ", style="dim")
        meta_text.append(doc.meta.author, style="italic")
        meta_text.append("\n")
    if doc.meta.last_llm_pass:
        meta_text.append("Pass: ", style="dim")
        meta_text.append(doc.meta.last_llm_pass[:10], style="cyan")
        meta_text.append("\n")

    outline = Text()
    outline.append("\nOutline\n", style="bold bright_cyan underline")
    outline.append("  Meta\n", style="dim")
    if doc.characters:
        outline.append(f"  Characters ({len(doc.characters)})\n", style="dim")
    if doc.lore:
        outline.append(f"  Lore ({len(doc.lore)})\n", style="dim")
    outline.append("  Body\n", style="dim")
    if doc.standalone_annos:
        outline.append(f"  Annotations ({len(doc.standalone_annos)})\n", style="dim")

    annos = Text()
    annos.append("\nAnnotations\n", style="bold bright_cyan underline")
    unresolved = [a for a in doc.standalone_annos.values() if a.status != "resolved"]
    resolved = [a for a in doc.standalone_annos.values() if a.status == "resolved"]

    type_colors = {
        "question": "bright_red",
        "praise": "bright_green",
        "critique": "bright_yellow",
        "rewrite": "bright_blue",
        "note": "dim",
        "lore-check": "bright_magenta",
    }

    if unresolved:
        annos.append(f"\nUnresolved ({len(unresolved)})\n", style="bold red")
        for a in unresolved:
            col = type_colors.get(a.ann_type, "white")
            annos.append(f"  {a.ann_id} ", style="bold")
            annos.append(f"[{a.ann_type}]\n", style=col)

    if resolved:
        annos.append(f"\nResolved ({len(resolved)})\n", style="dim green")
        for a in resolved:
            col = type_colors.get(a.ann_type, "white")
            annos.append(f"  {a.ann_id} ", style="dim bold")
            annos.append(f"[{a.ann_type}]\n", style=f"dim {col}")

    content = Group(meta_text, outline, annos)
    return Panel(content, title="JMD", border_style="bright_cyan", box=box.ROUNDED)


def _build_body_panel(doc: JMDDocument) -> Panel:
    body_text = Text()
    body_raw = doc.body

    type_bg = {
        "question": "on bright_red",
        "praise": "on bright_green",
        "critique": "on bright_yellow",
        "rewrite": "on bright_blue",
        "note": "on grey37",
        "lore-check": "on bright_magenta",
    }

    pos = 0
    for m in _ANNO_RE.finditer(body_raw):
        before = body_raw[pos:m.start()]
        body_text = _append_markdown(body_text, before)

        ann_id = m.group(1).strip()
        ann_type = m.group(2).strip()
        status = m.group(4).strip()
        inner = m.group(5)

        style = type_bg.get(ann_type, "on white")
        if status == "resolved":
            style += " strike"

        body_text.append(inner, style=style)
        pos = m.end()

    if pos < len(body_raw):
        body_text = _append_markdown(body_text, body_raw[pos:])

    return Panel(body_text, title="Body", border_style="bright_blue", box=box.ROUNDED)


def _append_markdown(text_obj: Text, raw: str) -> Text:
    """Append markdown-formatted text to a Rich Text object."""
    lines = raw.split("\n")
    for i, line in enumerate(lines):
        if i > 0:
            text_obj.append("\n")

        stripped = line.strip()
        if stripped.startswith("# "):
            text_obj.append(stripped[2:], style="bold bright_cyan underline")
            continue
        if stripped.startswith("## "):
            text_obj.append(stripped[3:], style="bold cyan")
            continue
        if stripped.startswith("### "):
            text_obj.append(stripped[4:], style="bold bright_blue")
            continue

        remaining = line
        while remaining:
            bold_match = re.search(r'\*\*(.+?)\*\*', remaining)
            italic_match = re.search(r'\*(.+?)\*', remaining)
            code_match = re.search(r'`(.+?)`', remaining)

            matches = []
            if bold_match:
                matches.append((bold_match.start(), 'bold', bold_match))
            if italic_match:
                if not (bold_match and bold_match.start() <= italic_match.start() < bold_match.end()):
                    matches.append((italic_match.start(), 'italic', italic_match))
            if code_match:
                matches.append((code_match.start(), 'code', code_match))

            if not matches:
                text_obj.append(remaining)
                break

            matches.sort(key=lambda x: x[0])
            _, fmt, m = matches[0]

            if m.start() > 0:
                text_obj.append(remaining[:m.start()])

            inner = m.group(1)
            if fmt == 'bold':
                text_obj.append(inner, style="bold bright_white")
            elif fmt == 'italic':
                text_obj.append(inner, style="italic bright_yellow")
            elif fmt == 'code':
                text_obj.append(inner, style="on grey37 bright_white")

            remaining = remaining[m.end():]

    return text_obj


def _build_right_panel(doc: JMDDocument) -> Panel:
    if not doc.standalone_annos:
        return Panel(Text("No annotations."), title="Details", border_style="dim", box=box.ROUNDED)

    content = Text()
    type_colors = {
        "question": "bright_red",
        "praise": "bright_green",
        "critique": "bright_yellow",
        "rewrite": "bright_blue",
        "note": "dim",
        "lore-check": "bright_magenta",
    }

    for ann_id, a in doc.standalone_annos.items():
        col = type_colors.get(a.ann_type, "white")
        status_style = "green" if a.status == "resolved" else "red"
        content.append(f"\n{ann_id}\n", style="bold bright_white")
        content.append(f"  type: ", style="dim")
        content.append(f"[{a.ann_type}]\n", style=col)
        content.append(f"  author: ", style="dim")
        content.append(f"{a.author}\n", style="cyan")
        content.append(f"  status: ", style="dim")
        content.append(f"{a.status}\n", style=status_style)
        if a.created:
            content.append(f"  created: ", style="dim")
            content.append(f"{a.created}\n", style="dim")
        content.append(f"  {a.text}\n", style="bright_white")
        content.append("─" * 28 + "\n", style="dim")

    return Panel(content, title=f"Annotations ({len(doc.standalone_annos)})", border_style="bright_magenta", box=box.ROUNDED)
