"""Tests for JMD CLI commands: stats, batch, diff with body text."""

import json
import os
from pathlib import Path

import pytest

from jmd.parser import parse, strip_annotations
from jmd.cli import _doc_to_dict, cmd_stats, cmd_batch, cmd_diff


SAMPLE = """@meta
title: "Test Story"
author: "Josii"

@characters
Odin: {archetype: "seeker", voice: "bitter", tags: [norse]}

@body
# Chapter 1

The ash pierced the worlds. [?q1:question:Josii:unresolved]Check this lore.[?]

@annotations
q1:
  type: question
  author: Josii
  status: unresolved
  text: "Verify which realm."

q2:
  type: praise
  author: Josii
  status: resolved
  text: "Good opening."
"""


def _make_args(**kwargs):
    """Build a simple argparse-like namespace."""
    class NS:
        def __init__(self, **kw):
            for k, v in kw.items():
                setattr(self, k, v)
    return NS(**kwargs)


def test_doc_to_dict_roundtrip():
    doc = parse(SAMPLE)
    d = _doc_to_dict(doc)
    assert d["meta"]["title"] == "Test Story"
    assert d["meta"]["author"] == "Josii"
    assert len(d["characters"]) == 1
    assert d["characters"][0]["name"] == "Odin"
    assert len(d["inline_annotations"]) == 1
    assert len(d["standalone_annotations"]) == 2


def test_stats_counts(capsys, tmp_path):
    p = tmp_path / "test.jmd"
    p.write_text(SAMPLE)
    args = _make_args(file=str(p))
    cmd_stats(args)
    out = capsys.readouterr().out
    assert "Words:" in out
    assert "Annotations:  2 total" in out
    assert "question" in out
    assert "praise" in out
    assert "Health score:" in out


def test_batch_render_html(tmp_path):
    # Create two .jmd files
    (tmp_path / "a.jmd").write_text(SAMPLE)
    (tmp_path / "b.jmd").write_text(SAMPLE.replace("Test Story", "Other Story"))

    out_dir = tmp_path / "out"
    args = _make_args(directory=str(tmp_path), format="html", output=str(out_dir))
    cmd_batch(args)

    assert (out_dir / "a.html").exists()
    assert (out_dir / "b.html").exists()
    html = (out_dir / "a.html").read_text()
    assert "Test Story" in html


def test_batch_render_json(tmp_path):
    (tmp_path / "single.jmd").write_text(SAMPLE)
    out_dir = tmp_path / "json_out"
    args = _make_args(directory=str(tmp_path), format="json", output=str(out_dir))
    cmd_batch(args)

    assert (out_dir / "single.json").exists()
    data = json.loads((out_dir / "single.json").read_text())
    assert data["meta"]["title"] == "Test Story"


def test_batch_empty_dir(tmp_path, capsys):
    args = _make_args(directory=str(tmp_path), format="html", output=None)
    cmd_batch(args)
    out = capsys.readouterr().out
    assert "No .jmd files" in out


def test_diff_no_differences(capsys, tmp_path):
    p = tmp_path / "same.jmd"
    p.write_text(SAMPLE)
    args = _make_args(file_a=str(p), file_b=str(p))
    cmd_diff(args)
    out = capsys.readouterr().out
    assert "No differences found" in out


def test_diff_body_text_changed(capsys, tmp_path):
    a = tmp_path / "a.jmd"
    b = tmp_path / "b.jmd"
    a.write_text(SAMPLE)
    b.write_text(SAMPLE.replace("The ash pierced the worlds", "The oak pierced the worlds"))

    args = _make_args(file_a=str(a), file_b=str(b))
    cmd_diff(args)
    out = capsys.readouterr().out
    assert "Body text changed" in out
    assert "oak" in out or "ash" in out


def test_diff_annotation_status_changed(capsys, tmp_path):
    a = tmp_path / "a.jmd"
    b = tmp_path / "b.jmd"
    a.write_text(SAMPLE)
    b.write_text(SAMPLE.replace("status: unresolved", "status: resolved", 1))

    args = _make_args(file_a=str(a), file_b=str(b))
    cmd_diff(args)
    out = capsys.readouterr().out
    assert "status: unresolved → resolved" in out


def test_diff_annotation_added(capsys, tmp_path):
    a = tmp_path / "a.jmd"
    b = tmp_path / "b.jmd"
    base = """@meta
title: "X"

@body
Hello.

@annotations
q1:
  type: note
  author: Josii
  status: unresolved
  text: "Old"
"""
    a.write_text(base)
    b.write_text(base + "\nq2:\n  type: question\n  author: Josii\n  status: unresolved\n  text: \"New\"\n")

    args = _make_args(file_a=str(a), file_b=str(b))
    cmd_diff(args)
    out = capsys.readouterr().out
    assert "Added annotations" in out
    assert "q2" in out
