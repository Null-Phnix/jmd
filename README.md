# JMD — Josii's Markdown Extension

> *I write fiction with LLMs. The problem isn't the writing — it's keeping track of what's real, what's a suggestion, and what I still need to verify.*

---

## Why I Built This

I've been writing [Bifrost](https://github.com/Null-Phnix/bifrost) — a Norse mythology project — for over a year. The workflow is simple in theory:

1. Write a scene
2. Send it to Claude / GPT / whatever
3. Get feedback: "Odin's voice is too soft here," "the Well of Mimir is in Jotunheim, not Niflheim," "this line is great but the next one falls flat"
4. Apply some changes, save the file
5. Repeat

The problem is step 3 → 4. The feedback lives in chat windows. The changes live in new chat sessions. The file on disk is a fork of a fork of a fork, and I have no idea which suggestions I've already applied, which ones I rejected, and which ones I'm still thinking about.

I tried:
- **Comments in the text** — clutter the narrative
- **Separate notes files** — get out of sync
- **Git history** — too coarse, hard to read
- **Markdown** — no built-in annotation system

None of them worked. So I made JMD.

---

## What JMD Is

**JMD** = Markdown + structured metadata + inline annotations + standalone annotations + revision tracking, all in one file.

It's a single file format where:
- Your **text** is just Markdown
- Your **annotations** are inline markers with IDs
- Your **annotation details** (the actual feedback) live in a separate section
- Your **characters** and **lore** are declared up front
- Your **revision history** is logged automatically

The file is human-readable without any tool. But with `jmd open`, you get a beautiful TUI. With the VS Code extension, you get a preview panel. With `jmd render`, you get dark-themed HTML.

---

## The Problem It Solves

### 1. The Annotation Drift Problem
When you're iterating with LLMs, you get feedback scattered across 50 chat sessions. JMD keeps every annotation in the file, linked to the text it refers to, with status tracking (unresolved / resolved).

### 2. The "What Did I Change And Why" Problem
`@revision` section logs every pass: what changed, what annotation triggered it, and why. No more guessing why a paragraph looks different.

### 3. The Lore Consistency Problem
`@characters` and `@lore` sections declare your world upfront. When an LLM suggests something that contradicts established lore, you mark it as a `lore-check` annotation.

### 4. The "LLM Feedback In One Ear, Out The Other" Problem
Inline annotations (`[?q1:question:Josii:unresolved]...text...[?]`) make it impossible to ignore feedback. The text literally has a colored underline.

---

## Current State

| Feature | Status |
|---|---|
| Parser (Python) | ✅ Reads `@meta`, `@characters`, `@lore`, `@body`, `@annotations`, `@revision` |
| HTML Renderer | ✅ Dark-themed HTML with sidebar, annotation cards |
| Plain Text Export | ✅ Strips annotations, outputs clean prose |
| Markdown Export | ✅ Converts to standard Markdown |
| CLI (`jmd`) | ✅ `render`, `validate`, `strip`, `unresolved`, `open`, `watch` |
| TUI Viewer (`jmd open`) | ✅ Rich-based terminal layout with 3 panels |
| VS Code Extension | 🔄 Syntax highlighting ✅, preview panel 🔄 |
| Live-reload server | ✅ `jmd watch file.jmd --port 8080` |
| OS file registration | 🚧 Linux MIME type + .desktop pending |

---

## What I Still Want

### Immediate (next few weeks)
- [ ] VS Code preview panel with live HTML rendering
- [ ] VS Code annotation sidebar (tree view of unresolved)
- [ ] Linux `.desktop` file + MIME type so double-clicking `.jmd` opens in browser
- [ ] macOS UTI registration
- [ ] Annotation status toggle from CLI (`jmd resolve q1 file.jmd`)

### Medium-term (next few months)
- [ ] **LLM Agent integration**: `jmd agent file.jmd` sends the file to an LLM (with annotations as context) and receives back the updated file with new annotations
- [ ] **Annotation threading**: replies to annotations, not just single comments
- [ ] **Diff mode**: `jmd diff v1.jmd v2.jmd` showing annotation-aware diffs
- [ ] **Export to DOCX/EPUB/PDF**: not just HTML
- [ ] **Plugin system**: custom annotation types with custom renderers

### Long-term (dreaming)
- [ ] A desktop app that feels like Obsidian but for fiction
- [ ] Real-time collaborative editing with annotation awareness
- [ ] LLM-native: the file format is designed for agents to read and write

---

## My End Goal

I want a world where:
1. I write a scene in any editor
2. I run `jmd agent file.jmd` and get back the file with 12 new annotations
3. I run `jmd open file.jmd` and see all 12 in a beautiful TUI
4. I resolve 8, rewrite 3, defer 1
5. I commit the `.jmd` file — it's the single source of truth

The file is the project. Not a folder of notes. Not a chat history. One file. All state.

---

## Quick Start

```bash
# Install
pip install jmd-format

# Open a file in the terminal TUI
jmd open my_story.jmd

# Render to HTML
jmd render my_story.jmd -o my_story.html

# Validate
jmd validate my_story.jmd

# Watch for changes and auto-render
jmd watch my_story.jmd --port 8080
```

## Example File

See [examples/odins_bargain.jmd](examples/odins_bargain.jmd) for a full example.

---

## The Format

```jmd
@meta
title: "My Story"
author: "Josii"
last_llm_pass: "2026-05-12"

@characters
Odin: {archetype: "seeker", voice: "bitter", tags: [norse]}

@lore
Yggdrasil: {ref: "bifrost://lore/yggdrasil", context: "World tree"}

@body
# Chapter 1

The tree stood silent. [?q1:question:Josii:unresolved]This opening is weak.[?]

@annotations
q1:
  type: question
  author: Josii
  status: unresolved
  text: "The opening is weak. Try something with more weight."

@revision
  pass: 1
  timestamp: "2026-05-12T10:00:00Z"
  changes: []
```

---

## License

MIT — do whatever you want. If you build something cool, tell me.

---

> *"The casualties are features."* — Josii, probably, about something
