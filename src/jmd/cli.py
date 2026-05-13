"""JMD CLI — command-line interface for the JMD format."""

import argparse
import sys
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
    else:
        err(f"Unknown format: {fmt}")
    output_path.write_text(output)
    print(f"Rendered to {output_path}")


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


def cmd_open(args):
    open_file(args.file)



def main():
    parser = argparse.ArgumentParser(prog="jmd", description="JMD — Josii's Markdown Extension")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("render", help="Render .jmd to HTML/text/Markdown")
    p.add_argument("file")
    p.add_argument("-o", "--output")
    p.add_argument("-f", "--format", choices=["html", "text", "markdown"])
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

    p = sub.add_parser("open", help="Open a .jmd file in the terminal TUI viewer")
    p.add_argument("file")
    p.set_defaults(func=cmd_open)

    if HAS_WATCHDOG:
        add_watch_subparser(sub)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
