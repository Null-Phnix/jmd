"""JMD Watch — live-reload server for .jmd files."""

import argparse
import time
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler

from .renderer import render_html
from .parser import parse

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    HAS_WATCHDOG = True
except ImportError:
    HAS_WATCHDOG = False
    Observer = None
    FileSystemEventHandler = None


def add_watch_subparser(sub):
    p = sub.add_parser("watch", help="Watch a .jmd file and serve live HTML")
    p.add_argument("file")
    p.add_argument("--port", type=int, default=8080)
    p.add_argument("-o", "--output")
    p.set_defaults(func=cmd_watch)


def cmd_watch(args):
    path = Path(args.file)
    if not path.exists():
        print(f"Error: File not found: {path}")
        return

    output_path = Path(args.output) if args.output else path.with_suffix(".html")
    _render(path, output_path)

    if not HAS_WATCHDOG:
        print("watchdog not installed. Install with: pip install jmd-format[watch]")
        return

    class Handler(FileSystemEventHandler):
        def on_modified(self, event):
            if event.src_path == str(path.resolve()):
                _render(path, output_path)
                print(f"  → Re-rendered {output_path}")

    observer = Observer()
    observer.schedule(Handler(), str(path.parent), recursive=False)
    observer.start()

    print(f"Watching {path} → {output_path}")
    print(f"Server running at http://localhost:{args.port}/")

    server = HTTPServer(("", args.port), SimpleHTTPRequestHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


def _render(path, output_path):
    raw = path.read_text()
    doc = parse(raw)
    html = render_html(doc)
    output_path.write_text(html)
