"""JMD CLI — command-line interface for the JMD format."""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from .watch import add_watch_subparser, HAS_WATCHDOG
from .parser import parse, strip_annotations, _ANNO_RE
from .renderer import render_html, render_plain, render_markdown
from .tui import open_file


def err(msg: str):
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(1)


def cmd_render(args):
    path = Path(args.file)
    if not path.exists():
        err(f"File not found: {path}")
    raw = path.read_text()
    doc = parse(raw)
    output_path = Path(args.output) if args.output else path.with_suffix(".html")
    fmt = args.format or ("html" if output_path.suffix == ".html" else "text")
    if fmt == "html":
        output = render_html(doc)
    elif fmt == "text":
        output = render_plain(doc)
    elif fmt == "markdown":
        output = render_markdown(doc)
    elif fmt == "json":
        output = json.dumps(_doc_to_dict(doc), indent=2, default=str)
    else:
        err(f"Unknown format: {fmt}")
    output_path.write_text(output)
    print(f"Rendered to {output_path}")


def _doc_to_dict(doc):
    """Serialize a JMDDocument to a plain dict for JSON export."""
    return {
        "meta": {
            "title": doc.meta.title,
            "author": doc.meta.author,
            "last_llm_pass": doc.meta.last_llm_pass,
            "extras": doc.meta.extras,
        },
        "characters": [
            {"name": c.name, "archetype": c.archetype, "voice": c.voice, "tags": c.tags}
            for c in doc.characters
        ],
        "lore": [
            {"name": l.name, "ref": l.ref, "context": l.context}
            for l in doc.lore
        ],
        "body": doc.body,
        "inline_annotations": [
            {
                "id": a.ann_id,
                "type": a.ann_type,
                "author": a.author,
                "status": a.status,
                "start": a.start_offset,
                "end": a.end_offset,
            }
            for a in doc.inline_annos
        ],
        "standalone_annotations": {
            k: {
                "id": v.ann_id,
                "type": v.ann_type,
                "author": v.author,
                "status": v.status,
                "created": v.created,
                "text": v.text,
            }
            for k, v in doc.standalone_annos.items()
        },
        "revision": doc.revision,
    }


def cmd_validate(args):
    path = Path(args.file)
    if not path.exists():
        err(f"File not found: {path}")
    raw = path.read_text()
    issues = _validate(raw)
    if not issues:
        print("✓ No issues found.")
        return
    errors = [m for lvl, m in issues if lvl == "error"]
    warnings = [m for lvl, m in issues if lvl == "warning"]
    infos = [m for lvl, m in issues if lvl == "info"]
    if errors:
        print(f"❌ {len(errors)} error(s):")
        for m in errors:
            print(f"  - {m}")
    if warnings:
        print(f"⚠ {len(warnings)} warning(s):")
        for m in warnings:
            print(f"  - {m}")
    if infos:
        print(f"ℹ {len(infos)} note(s):")
        for m in infos:
            print(f"  - {m}")
    if errors:
        sys.exit(1)


def _validate(raw: str):
    issues = []
    has_body = "@body" in raw
    has_meta = "@meta" in raw
    if not has_body:
        issues.append(("error", "Missing @body section"))
    if not has_meta:
        issues.append(("warning", "Missing @meta section"))
    try:
        doc = parse(raw)
    except Exception as e:
        issues.append(("error", f"Parse error: {e}"))
        return issues
    inline_ids = {a.ann_id for a in doc.inline_annos}
    standalone_ids = set(doc.standalone_annos.keys())
    for oid in (inline_ids - standalone_ids):
        issues.append(("warning", f"Inline annotation '{oid}' has no @annotations entry"))
    for a in doc.standalone_annos.values():
        if a.status == "unresolved":
            issues.append(("info", f"Unresolved '{a.ann_id}': {a.text[:60]}"))
    return issues


def cmd_strip(args):
    path = Path(args.file)
    if not path.exists():
        err(f"File not found: {path}")
    raw = path.read_text()
    clean = strip_annotations(raw)
    if args.output:
        Path(args.output).write_text(clean)
        print(f"Clean text written to {args.output}")
    else:
        print(clean)


def cmd_unresolved(args):
    path = Path(args.file)
    if not path.exists():
        err(f"File not found: {path}")
    raw = path.read_text()
    doc = parse(raw)
    unresolved = [a for a in doc.standalone_annos.values() if a.status != "resolved"]
    if not unresolved:
        print("No unresolved annotations.")
        return
    print(f"Unresolved annotations ({len(unresolved)}):")
    for a in unresolved:
        print(f"  [{a.ann_type}] {a.ann_id} by {a.author}: {a.text[:80]}")


def cmd_stats(args):
    path = Path(args.file)
    if not path.exists():
        err(f"File not found: {path}")
    raw = path.read_text()
    doc = parse(raw)

    # Word / character counts (strip annotations for clean text)
    clean_body = strip_annotations(doc.body)
    words = len(clean_body.split())
    chars = len(clean_body)
    reading_time = max(1, round(words / 200))  # ~200 wpm

    # Annotation stats
    total = len(doc.standalone_annos)
    unresolved = [a for a in doc.standalone_annos.values() if a.status == "unresolved"]
    resolved = [a for a in doc.standalone_annos.values() if a.status == "resolved"]
    deferred = [a for a in doc.standalone_annos.values() if a.status == "deferred"]
    rejected = [a for a in doc.standalone_annos.values() if a.status == "rejected"]

    by_type = {}
    for a in doc.standalone_annos.values():
        by_type[a.ann_type] = by_type.get(a.ann_type, 0) + 1

    # Lore consistency: unresolved lore-checks
    lore_issues = [a for a in doc.standalone_annos.values() if a.ann_type == "lore-check" and a.status == "unresolved"]

    # Health score: resolved / total (0-100)
    health = 0
    if total > 0:
        health = round((len(resolved) / total) * 100)

    print(f"📊  Stats for {path.name}")
    print()
    print(f"  Words:        {words:,}")
    print(f"  Characters:   {chars:,}")
    print(f"  Reading time: ~{reading_time} min")
    print()
    print(f"  Annotations:  {total} total")
    print(f"    Unresolved: {len(unresolved)}")
    print(f"    Resolved:   {len(resolved)}")
    print(f"    Deferred:   {len(deferred)}")
    print(f"    Rejected:   {len(rejected)}")
    if by_type:
        print()
        print("  By type:")
        for t, count in sorted(by_type.items()):
            print(f"    {t:12s} {count}")
    if lore_issues:
        print()
        print(f"  ⚠ Lore checks unresolved: {len(lore_issues)}")
    print()
    health_color = "🟢" if health >= 75 else "🟡" if health >= 50 else "🔴"
    print(f"  Health score: {health_color} {health}% resolved")


def cmd_batch(args):
    import os
    dir_path = Path(args.directory)
    if not dir_path.exists() or not dir_path.is_dir():
        err(f"Not a directory: {dir_path}")

    fmt = args.format or "html"
    files = sorted(dir_path.glob("*.jmd"))
    if not files:
        print(f"No .jmd files in {dir_path}")
        return

    out_dir = Path(args.output) if args.output else dir_path / "_rendered"
    out_dir.mkdir(exist_ok=True)

    rendered = 0
    for path in files:
        try:
            raw = path.read_text()
            doc = parse(raw)
            if fmt == "html":
                output = render_html(doc)
                suffix = ".html"
            elif fmt == "text":
                output = render_plain(doc)
                suffix = ".txt"
            elif fmt == "markdown":
                output = render_markdown(doc)
                suffix = ".md"
            elif fmt == "json":
                output = json.dumps(_doc_to_dict(doc), indent=2, default=str)
                suffix = ".json"
            else:
                err(f"Unknown format: {fmt}")
            out_path = out_dir / (path.stem + suffix)
            out_path.write_text(output)
            rendered += 1
        except Exception as e:
            print(f"  ✗ {path.name}: {e}")

    print(f"Rendered {rendered}/{len(files)} .jmd files → {out_dir}")


def cmd_open(args):
    open_file(args.file)


def cmd_init(args):
    path = Path(args.output)
    if path.exists() and not args.force:
        err(f"File already exists: {path}. Use --force to overwrite.")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    template = f"""@meta
title: "{args.title}"
author: "{args.author}"
last_llm_pass: "{now}"

@characters
# character_name: {{archetype: "archetype", voice: "voice", tags: [tag1, tag2]}}

@lore
# lore_name: {{ref: "bifrost://lore/name", context: "Description"}}

@body
# Chapter 1

Your story begins here.

@annotations
# annotation_id:
#   type: question
#   author: {args.author}
#   status: unresolved
#   text: "Your annotation text here."

@revision
  pass: 1
  timestamp: "{now}"
  changes: []
"""
    path.write_text(template)
    print(f"Created {path}")


def cmd_resolve(args):
    path = Path(args.file)
    if not path.exists():
        err(f"File not found: {path}")
    raw = path.read_text()
    ann_id = args.ann_id
    new_status = args.status

    # Update in @annotations section
    section_re = re.compile(
        rf'({re.escape(ann_id)}:\s*\n(?:\s+\w+:.*\n)*)\s+status:\s*\w+',
        re.MULTILINE,
    )
    new_raw, n = section_re.subn(rf'\1  status: {new_status}', raw)
    if n == 0:
        err(f"Annotation '{ann_id}' not found in @annotations section.")

    # Update inline annotations too
    inline_re = re.compile(
        rf'(\[\?\s*{re.escape(ann_id)}:[^:]+:[^:]+):\w+(\])'
    )
    new_raw, n2 = inline_re.subn(rf'\1:{new_status}\2', new_raw)

    path.write_text(new_raw)
    print(f"Updated '{ann_id}' status → {new_status} ({n2} inline markers updated)")


def cmd_diff(args):
    path_a = Path(args.file_a)
    path_b = Path(args.file_b)
    for p, label in [(path_a, "A"), (path_b, "B")]:
        if not p.exists():
            err(f"File {label} not found: {p}")

    doc_a = parse(path_a.read_text())
    doc_b = parse(path_b.read_text())

    ids_a = set(doc_a.standalone_annos.keys())
    ids_b = set(doc_b.standalone_annos.keys())

    added = ids_b - ids_a
    removed = ids_a - ids_b
    common = ids_a & ids_b

    changed = []
    for ann_id in common:
        sa_a = doc_a.standalone_annos[ann_id]
        sa_b = doc_b.standalone_annos[ann_id]
        if sa_a.status != sa_b.status:
            changed.append((ann_id, f"status: {sa_a.status} → {sa_b.status}", None))
        if sa_a.text != sa_b.text:
            changed.append((ann_id, f"text changed ({len(sa_a.text)}→{len(sa_b.text)} chars)", None))

    # Body text diff (strip annotations for clean comparison)
    import difflib
    body_a = strip_annotations(doc_a.body)
    body_b = strip_annotations(doc_b.body)
    body_changed = body_a != body_b

    if not (added or removed or changed or body_changed):
        print("No differences found.")
        return

    if added:
        print(f"\n🟢 Added annotations in B ({len(added)}):")
        for aid in added:
            a = doc_b.standalone_annos[aid]
            print(f"  + [{a.ann_type}] {aid}: {a.text[:60]}")
    if removed:
        print(f"\n🔴 Removed annotations in B ({len(removed)}):")
        for aid in removed:
            a = doc_a.standalone_annos[aid]
            print(f"  - [{a.ann_type}] {aid}: {a.text[:60]}")
    if changed:
        print(f"\n🟡 Changed annotations ({len(changed)}):")
        for aid, desc, _ in changed:
            print(f"  ~ {aid}: {desc}")

    if body_changed:
        print(f"\n📝 Body text changed:")
        words_a = len(body_a.split())
        words_b = len(body_b.split())
        delta = words_b - words_a
        if delta != 0:
            sign = "+" if delta > 0 else ""
            print(f"  Word count: {words_a} → {words_b} ({sign}{delta})")
        # Show unified diff snippet
        diff = list(difflib.unified_diff(
            body_a.splitlines(),
            body_b.splitlines(),
            lineterm="",
            n=1,
        ))
        if diff:
            print(f"  Diff lines: {len(diff)}")
            for line in diff[:12]:
                prefix = " "
                if line.startswith("+"):
                    prefix = "+"
                elif line.startswith("-"):
                    prefix = "-"
                print(f"    {prefix} {line[:70]}")
            if len(diff) > 12:
                print(f"    ... ({len(diff) - 12} more lines)")
    print()


def main():
    parser = argparse.ArgumentParser(prog="jmd", description="JMD — Josii's Markdown Extension")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("render", help="Render .jmd to HTML/text/Markdown/JSON")
    p.add_argument("file")
    p.add_argument("-o", "--output")
    p.add_argument("-f", "--format", choices=["html", "text", "markdown", "json"])
    p.set_defaults(func=cmd_render)

    p = sub.add_parser("validate", help="Validate a .jmd file")
    p.add_argument("file")
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("strip", help="Remove annotations")
    p.add_argument("file")
    p.add_argument("-o", "--output")
    p.set_defaults(func=cmd_strip)

    p = sub.add_parser("unresolved", help="List unresolved annotations")
    p.add_argument("file")
    p.set_defaults(func=cmd_unresolved)

    p = sub.add_parser("stats", help="Show word count, annotation breakdown, and writing health")
    p.add_argument("file")
    p.set_defaults(func=cmd_stats)

    p = sub.add_parser("open", help="Open a .jmd file in the terminal TUI viewer")
    p.add_argument("file")
    p.set_defaults(func=cmd_open)

    p = sub.add_parser("init", help="Create a new .jmd file from template")
    p.add_argument("-o", "--output", required=True, help="Output file path")
    p.add_argument("-t", "--title", default="Untitled", help="Story title")
    p.add_argument("-a", "--author", default="Josii", help="Author name")
    p.add_argument("-f", "--force", action="store_true", help="Overwrite existing file")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("resolve", help="Change an annotation's status")
    p.add_argument("file")
    p.add_argument("ann_id", help="Annotation ID to update")
    p.add_argument("status", choices=["resolved", "unresolved", "deferred", "rejected"], help="New status")
    p.set_defaults(func=cmd_resolve)

    p = sub.add_parser("diff", help="Compare annotations between two .jmd files")
    p.add_argument("file_a", help="First .jmd file")
    p.add_argument("file_b", help="Second .jmd file")
    p.set_defaults(func=cmd_diff)

    p = sub.add_parser("batch", help="Render all .jmd files in a directory")
    p.add_argument("directory", help="Directory containing .jmd files")
    p.add_argument("-f", "--format", choices=["html", "text", "markdown", "json"], default="html")
    p.add_argument("-o", "--output", help="Output directory (default: _rendered/)")
    p.set_defaults(func=cmd_batch)

    if HAS_WATCHDOG:
        add_watch_subparser(sub)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
