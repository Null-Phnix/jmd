"""JMD Parser — reads .jmd files into structured data."""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class JMDMeta:
    title: Optional[str] = None
    author: Optional[str] = None
    last_llm_pass: Optional[str] = None
    extras: Dict[str, str] = field(default_factory=dict)


@dataclass
class JMDCharacter:
    name: str
    archetype: Optional[str] = None
    voice: Optional[str] = None
    tags: List[str] = field(default_factory=list)


@dataclass
class JMDLore:
    name: str
    ref: Optional[str] = None
    context: Optional[str] = None


@dataclass
class JMDInlineAnno:
    ann_id: str
    ann_type: str
    author: str
    status: str
    start_offset: int = 0
    end_offset: int = 0


@dataclass
class JMDStandaloneAnno:
    ann_id: str
    ann_type: str
    author: str
    status: str
    created: Optional[str] = None
    text: str = ""


@dataclass
class JMDDocument:
    body: str = ""
    meta: JMDMeta = field(default_factory=JMDMeta)
    characters: List[JMDCharacter] = field(default_factory=list)
    lore: List[JMDLore] = field(default_factory=list)
    inline_annos: List[JMDInlineAnno] = field(default_factory=list)
    standalone_annos: Dict[str, JMDStandaloneAnno] = field(default_factory=dict)
    revision: Dict = field(default_factory=dict)
    raw_sections: Dict[str, str] = field(default_factory=dict)


# Inline annotation regex: [?ID:TYPE:AUTHOR:STATUS]text[?]
_ANNO_RE = re.compile(
    r'\[\?\s*([^:]+):([^:]+):([^:]+):([^\]]+)\](.*?)\[\?\]',
    re.DOTALL
)


def parse(raw: str) -> JMDDocument:
    doc = JMDDocument()

    # Split on @section headers
    section_pattern = re.compile(r'\n?@(\w+)\s*\n')
    parts = section_pattern.split(raw)

    sections = {}
    current_name = "preamble"
    current_content = parts[0] if parts else ""

    for i in range(1, len(parts), 2):
        sections[current_name] = current_content.strip()
        current_name = parts[i]
        current_content = parts[i + 1] if i + 1 < len(parts) else ""

    sections[current_name] = current_content.strip()
    doc.raw_sections = sections

    if "meta" in sections:
        doc.meta = _parse_meta(sections["meta"])
    if "characters" in sections:
        doc.characters = _parse_characters(sections["characters"])
    if "lore" in sections:
        doc.lore = _parse_lore(sections["lore"])
    if "body" in sections:
        doc.body, doc.inline_annos = _parse_body(sections["body"])
    else:
        doc.body = raw
        doc.inline_annos = []
    if "annotations" in sections:
        doc.standalone_annos = _parse_standalones(sections["annotations"])
    if "revision" in sections:
        doc.revision = _parse_revision(sections["revision"])

    return doc


def _parse_meta(content: str) -> JMDMeta:
    meta = JMDMeta()
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, val = line.split(":", 1)
        key = key.strip().lower()
        val = val.strip().strip('"').strip("'")
        if key == "title":
            meta.title = val
        elif key == "author":
            meta.author = val
        elif key == "last_llm_pass":
            meta.last_llm_pass = val
        else:
            meta.extras[key] = val
    return meta


def _parse_characters(content: str) -> List[JMDCharacter]:
    chars = []
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = re.match(r'(\w+):\s*(.+)', line)
        if match:
            name = match.group(1)
            kv = _parse_braced(match.group(2))
            chars.append(JMDCharacter(
                name=name,
                archetype=kv.get("archetype"),
                voice=kv.get("voice"),
                tags=[t.strip() for t in kv.get("tags", "").strip("[]").split(",") if t.strip()]
            ))
    return chars


def _parse_lore(content: str) -> List[JMDLore]:
    entries = []
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = re.match(r'(\w+):\s*(.+)', line)
        if match:
            name = match.group(1)
            kv = _parse_braced(match.group(2))
            entries.append(JMDLore(name=name, ref=kv.get("ref"), context=kv.get("context")))
    return entries


def _parse_braced(text: str) -> Dict[str, str]:
    text = text.strip()
    if text.startswith("{") and text.endswith("}"):
        text = text[1:-1]
    result = {}
    key_pattern = re.compile(r'(\w+)\s*:\s*("[^"]*"|\[[^\]]*\]|[^,]+)')
    for m in key_pattern.finditer(text):
        k = m.group(1)
        v = m.group(2).strip().strip('"').strip("'")
        result[k] = v
    return result


def _parse_body(content: str) -> tuple:
    annos = []
    for m in _ANNO_RE.finditer(content):
        annos.append(JMDInlineAnno(
            ann_id=m.group(1).strip(),
            ann_type=m.group(2).strip(),
            author=m.group(3).strip(),
            status=m.group(4).strip(),
            start_offset=m.start(),
            end_offset=m.end()
        ))
    return content, annos


def _parse_standalones(content: str) -> Dict[str, JMDStandaloneAnno]:
    result = {}
    current_id = None
    current_lines = []
    current_meta = {}

    for line in content.splitlines():
        line_stripped = line.strip()
        if not line_stripped or line_stripped.startswith("#"):
            continue
        if re.match(r'^[a-zA-Z0-9_-]+:$', line_stripped):
            if current_id:
                result[current_id] = _build_standalone(current_id, current_lines, current_meta)
            current_id = line_stripped.rstrip(':')
            current_lines = []
            current_meta = {}
            continue
        meta_match = re.match(r'^(type|author|status|created|text):\s*(.*)', line_stripped)
        if meta_match:
            current_meta[meta_match.group(1)] = meta_match.group(2).strip().strip('"').strip("'")
            continue
        current_lines.append(line.rstrip())

    if current_id:
        result[current_id] = _build_standalone(current_id, current_lines, current_meta)
    return result


def _build_standalone(ann_id, lines, meta):
    text = "\n".join(lines).strip()
    real_text = meta.get("text", text)
    return JMDStandaloneAnno(
        ann_id=ann_id,
        ann_type=meta.get("type", "note"),
        author=meta.get("author", "unknown"),
        status=meta.get("status", "unresolved"),
        created=meta.get("created"),
        text=real_text
    )


def _parse_revision(content: str) -> Dict:
    return {"raw": content}


def strip_annotations(raw: str) -> str:
    return _ANNO_RE.sub(r'\5', raw)
