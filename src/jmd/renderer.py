"""JMD Renderer — compiles .jmd to HTML, plain text, Markdown."""

import html as html_module
import re
from typing import Optional

from .parser import parse, JMDDocument, JMDInlineAnno, JMDStandaloneAnno, _ANNO_RE


def render_html(doc: JMDDocument, standalone: bool = True) -> str:
    body_parts = []
    body_parts.append(_render_meta_header(doc))
    if doc.characters:
        body_parts.append(_render_characters(doc))
    if doc.lore:
        body_parts.append(_render_lore(doc))
    body_parts.append(_render_body(doc))
    if doc.standalone_annos:
        body_parts.append(_render_standalone_annotations(doc))
    if doc.revision:
        body_parts.append(_render_revision(doc))
    inner = "\n".join(body_parts)
    if standalone:
        return _wrap_html(doc.meta.title or "Untitled", inner, doc)
    return inner


def _wrap_html(title: str, body_inner: str, doc=None) -> str:
    css = """
    body {
        font-family: "Georgia", "Times New Roman", serif;
        font-size: 18px;
        line-height: 1.7;
        max-width: 680px;
        margin: 40px auto;
        padding: 0 20px;
        color: #e0e0e0;
        background: #1a1a1a;
    }
    h1 { color: #c792ea; border-bottom: 2px solid #c792ea; padding-bottom: 10px; }
    h2 { color: #82aaff; margin-top: 36px; }
    h3 { color: #f78c6c; margin-top: 24px; }
    .meta-bar { background: #2d2d2d; border-radius: 6px; padding: 12px 18px; margin-bottom: 24px; font-size: 14px; color: #a0a0a0; }
    .meta-bar span { margin-right: 16px; }
    .anno { border-bottom: 3px solid; cursor: pointer; transition: background 0.15s; }
    .anno.question { border-color: #f78c6c; }
    .anno.praise { border-color: #c3e88d; }
    .anno.critique { border-color: #ffcb6b; }
    .anno.rewrite { border-color: #82aaff; }
    .anno.note { border-color: #a0a0a0; }
    .anno.lore-check { border-color: #bb80b3; }
    .anno:hover { background: rgba(255,255,255,0.08); }
    .dialogue { color: #c3e88d; font-style: italic; }
    .section { margin-bottom: 40px; }
    .char-card { display: inline-block; background: #2d2d2d; border-radius: 4px;
                 padding: 8px 12px; margin: 4px; font-size: 13px; }
    .char-name { font-weight: bold; color: #c792ea; }
    .status.unresolved { color: #f78c6c; }
    .status.resolved { color: #c3e88d; }
    #ann-sidebar { position: fixed; right: 20px; top: 40px; width: 260px;
                   background: #2d2d2d; border-radius: 6px; padding: 12px;
                   font-size: 13px; max-height: 80vh; overflow-y: auto;
                   border: 1px solid #3a3a3a; }
    #ann-sidebar h3 { margin-top: 0; font-size: 14px; color: #c792ea; }
    .ann-item { border-left: 2px solid #444; padding-left: 8px; margin: 8px 0; }
    .ann-item .type-tag { font-size: 10px; padding: 1px 6px; border-radius: 3px; display: inline-block; margin-right: 4px; }
    """
    js = """
    document.querySelectorAll('.anno').forEach(el => {
        el.addEventListener('click', () => {
            const text = el.getAttribute('data-ann-text');
            if (text) alert(text);
        });
    });
    """
    sidebar = _render_sidebar(doc) if doc else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html_module.escape(title)}</title>
<style>{css}</style>
</head>
<body>
{body_inner}
{sidebar}
<script>{js}</script>
</body>
</html>"""


def _render_meta_header(doc: JMDDocument) -> str:
    parts = []
    if doc.meta.title:
        parts.append(f'<h1>{html_module.escape(doc.meta.title)}</h1>')
    bar = []
    if doc.meta.author:
        bar.append(f'By {html_module.escape(doc.meta.author)}')
    if doc.meta.last_llm_pass:
        bar.append(f'Last pass: {doc.meta.last_llm_pass}')
    if bar:
        parts.append(f'<div class="meta-bar"><span>' + '</span> <span>'.join(bar) + '</span></div>')
    return "\n".join(parts)


def _render_characters(doc: JMDDocument) -> str:
    cards = []
    for c in doc.characters:
        archetype = f' · {html_module.escape(c.archetype)}' if c.archetype else ""
        cards.append(
            f'<div class="char-card"><span class="char-name">{html_module.escape(c.name)}</span>'
            f'{archetype}</div>'
        )
    return f'<div class="section"><h3>Characters</h3><p>' + " ".join(cards) + '</p></div>'


def _render_lore(doc: JMDDocument) -> str:
    items = []
    for l in doc.lore:
        ref = f'<a href="{html_module.escape(l.ref or "#")}" style="color:#82aaff;">{html_module.escape(l.ref or "No ref")}</a>'
        items.append(f'<li><strong>{html_module.escape(l.name)}</strong>: {html_module.escape(l.context or "")} ({ref})</li>')
    return f'<div class="section"><h3>Lore</h3><ul>' + "\n".join(items) + '</ul></div>'


def _render_body(doc: JMDDocument) -> str:
    raw = doc.body
    annotation_map = {sa.ann_id: sa for sa in doc.standalone_annos.values()}

    def _replace(m: re.Match) -> str:
        ann_id = m.group(1).strip()
        ann_type = m.group(2).strip()
        author = m.group(3).strip()
        status = m.group(4).strip()
        inner_text = m.group(5)
        sa = annotation_map.get(ann_id)
        tooltip = sa.text if sa else f"[{ann_type} by {author}: {status}]"
        tooltip = html_module.escape(tooltip).replace('"', '\u0026quot;')
        return (
            f'<span class="anno {ann_type} {status}" '
            f'data-ann-id="{html_module.escape(ann_id)}" '
            f'data-ann-text="{tooltip}"'
            f'>{html_module.escape(inner_text)}</span>'
        )

    rendered = _ANNO_RE.sub(_replace, raw)
    rendered = re.sub(r'^# (.+)$', r'<h2>\1</h2>', rendered, flags=re.MULTILINE)
    rendered = re.sub(r'^## (.+)$', r'<h3>\1</h3>', rendered, flags=re.MULTILINE)
    rendered = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', rendered)
    rendered = re.sub(r'\*(.+?)\*', r'<em>\1</em>', rendered)
    rendered = _markdown_to_paragraphs(rendered)
    return f'<div class="section">\n{rendered}\n</div>'


def _markdown_to_paragraphs(text: str) -> str:
    lines = text.split('\n')
    out, para = [], []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if para:
                out.append('<p>' + ' '.join(para) + '</p>')
                para = []
            continue
        if stripped.startswith('<'):
            if para:
                out.append('<p>' + ' '.join(para) + '</p>')
                para = []
            out.append(line)
            continue
        para.append(stripped)
    if para:
        out.append('<p>' + ' '.join(para) + '</p>')
    return '\n'.join(out)


def _render_standalone_annotations(doc: JMDDocument) -> str:
    items = []
    colors = {"question": "#f78c6c", "praise": "#c3e88d", "critique": "#ffcb6b",
              "rewrite": "#82aaff", "note": "#a0a0a0", "lore-check": "#bb80b3"}
    for ann_id, sa in doc.standalone_annos.items():
        col = colors.get(sa.ann_type, "#a0a0a0")
        status_class = "resolved" if sa.status == "resolved" else "unresolved"
        items.append(
            f'<div class="ann-item">'
            f'<span class="type-tag" style="background:{col};color:#1a1a1a;">{sa.ann_type}</span> '
            f'<span class="status {status_class}">{sa.status}</span> '
            f'<strong>{html_module.escape(sa.ann_id)}</strong> '
            f'by {html_module.escape(sa.author)}<br>'
            f'{html_module.escape(sa.text)}</div>'
        )
    return f'<div class="section"><h3>Annotations</h3>\n' + '\n'.join(items) + '\n</div>'


def _render_revision(doc: JMDDocument) -> str:
    raw = doc.revision.get("raw", "")
    if not raw:
        return ""
    return f'<div class="section"><h3>Revision Log</h3><pre style="background:#2d2d2d;padding:12px;border-radius:4px;font-size:12px;">{html_module.escape(raw)}</pre></div>'


def _render_sidebar(doc: JMDDocument) -> str:
    if not doc.standalone_annos:
        return ""
    unresolved = [a for a in doc.standalone_annos.values() if a.status != "resolved"]
    resolved = [a for a in doc.standalone_annos.values() if a.status == "resolved"]

    def _render_list(items):
        out = []
        for a in items:
            out.append(
                f'<div class="ann-item" style="margin-bottom:6px;">'
                f'<strong>{a.ann_id}</strong> ({a.ann_type})<br>'
                f'{html_module.escape(a.text[:60])}' + ('...' if len(a.text) > 60 else '') +
                f'</div>'
            )
        return '\n'.join(out)

    return (
        f'<div id="ann-sidebar">'
        f'<h3>Unresolved ({len(unresolved)})</h3>'
        + _render_list(unresolved)
        + f'<h3>Resolved ({len(resolved)})</h3>'
        + _render_list(resolved)
        + f'</div>'
    )


def render_plain(doc: JMDDocument) -> str:
    parts = []
    if doc.meta.title:
        parts.append("=" * 60)
        parts.append(doc.meta.title)
        parts.append("=" * 60)
    body = _strip_annotations(doc.body)
    parts.append(body)
    return "\n\n".join(parts)


def render_markdown(doc: JMDDocument) -> str:
    parts = []
    if doc.meta.title:
        parts.append(f"# {doc.meta.title}\n")
    parts.append(doc.body)
    if doc.standalone_annos:
        parts.append("\n\n---\n")
        for idx, (ann_id, sa) in enumerate(doc.standalone_annos.items(), 1):
            parts.append(f"[^{idx}]: **{sa.ann_type}** ({sa.status}) by {sa.author}: {sa.text}")
    return "\n".join(parts)


def _strip_annotations(raw: str) -> str:
    return _ANNO_RE.sub(r'\5', raw)
