"""Tests for the JMD parser."""

import pytest
from jmd.parser import parse, strip_annotations, JMDDocument, JMDMeta, JMDCharacter, JMDLore


SIMPLE = """@meta
title: "Test"
author: "Josii"

@body
Hello world.

@annotations
a1:
  type: question
  author: Josii
  status: unresolved
  text: "Is this right?"
"""


def test_parse_meta():
    doc = parse(SIMPLE)
    assert doc.meta.title == "Test"
    assert doc.meta.author == "Josii"


def test_parse_body():
    doc = parse(SIMPLE)
    assert "Hello world." in doc.body


def test_parse_standalone_annotations():
    doc = parse(SIMPLE)
    assert "a1" in doc.standalone_annos
    assert doc.standalone_annos["a1"].ann_type == "question"
    assert doc.standalone_annos["a1"].status == "unresolved"
    assert doc.standalone_annos["a1"].text == "Is this right?"


def test_strip_annotations():
    raw = "Hello [?q1:question:Josii:unresolved]world[?]."
    stripped = strip_annotations(raw)
    assert stripped == "Hello world."
    assert "[?" not in stripped


def test_inline_annotations():
    raw = """@body
This is [?a1:question:Josii:unresolved]annotated text[?] here.
"""
    doc = parse(raw)
    assert len(doc.inline_annos) == 1
    assert doc.inline_annos[0].ann_id == "a1"
    assert doc.inline_annos[0].ann_type == "question"


def test_characters():
    raw = """@characters
Odin: {archetype: "seeker", voice: "bitter", tags: [norse, aesir]}
"""
    doc = parse(raw)
    assert len(doc.characters) == 1
    assert doc.characters[0].name == "Odin"
    assert doc.characters[0].archetype == "seeker"
    assert doc.characters[0].voice == "bitter"
    assert doc.characters[0].tags == ["norse", "aesir"]


def test_lore():
    raw = """@lore
Yggdrasil: {ref: "bifrost://yggdrasil", context: "World tree"}
"""
    doc = parse(raw)
    assert len(doc.lore) == 1
    assert doc.lore[0].name == "Yggdrasil"
    assert doc.lore[0].ref == "bifrost://yggdrasil"
    assert doc.lore[0].context == "World tree"


def test_roundtrip_body():
    """Body should not lose content."""
    raw = """@body
Line one.

Line two.
"""
    doc = parse(raw)
    assert "Line one." in doc.body
    assert "Line two." in doc.body


def test_empty_doc():
    doc = parse("")
    assert isinstance(doc, JMDDocument)
    assert doc.body == ""


def test_no_body_fallback():
    """If there's no @body, raw content becomes body."""
    raw = "Just some text without sections."
    doc = parse(raw)
    assert doc.body == raw
