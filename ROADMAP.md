# JMD Roadmap

> *The casualties are features — but only if they ship.*

---

## Done (shipped)

- [x] Parser: full section parsing + inline annotations
- [x] HTML Renderer: dark-themed with sidebar
- [x] JSON Export: machine-readable structured output
- [x] Plain Text Export: strips annotations
- [x] Markdown Export: standard `.md`
- [x] CLI: `render`, `validate`, `strip`, `unresolved`, `open`, `init`, `resolve`, `diff`, `watch`, `stats`, `batch`
- [x] TUI Viewer: Rich-based 3-panel terminal layout
- [x] VS Code Extension: syntax highlighting + preview + annotation sidebar
- [x] Live-reload server (`jmd watch`)
- [x] OS file registration: Linux MIME + `.desktop`, macOS UTI snippet
- [x] `jmd stats` — word count, annotation breakdown, health score
- [x] `jmd batch` — render all `.jmd` files in a directory
- [x] `jmd diff` — annotation-aware + body-text diff
- [x] CI: GitHub Actions testing Python 3.10–3.14

---

## Next (this month)

- [ ] **LLM Agent integration**: `jmd agent file.jmd` → sends body to LLM, gets back updated file with new annotations appended
- [ ] **Interactive TUI**: arrow keys to navigate annotations, `r` to resolve inline, `q` to quit
- [ ] **DOCX export**: `jmd render -f docx` using `python-docx`
- [ ] **Plugin system skeleton**: custom annotation types with user-defined renderers

---

## Medium-term (next quarter)

- [ ] **Annotation threading**: replies to annotations, conversation history
- [ ] **Export to EPUB/PDF**: beyond HTML
- [ ] **Persistent annotation changelog**: every modification tracked
- [ ] **Multi-file project mode**: a folder of `.jmd` files treated as a single project with cross-references

---

## Long-term (if I keep going)

- [ ] Desktop app: Obsidian-like but fiction-native
- [ ] Real-time collaborative editing with annotation awareness
- [ ] LLM-native: the format is designed for agents to read and write as first-class citizens
- [ ] **Semantic video-to-JMD**: feed a video comprehension report into a JMD file for narrative analysis

---

## Architecture Debt

- [ ] Parser needs error recovery: currently one bad annotation breaks the whole file
- [ ] Renderer CSS should be themeable, not hardcoded
- [ ] TUI should use Rich `Live` for actual interactivity, not just static print
- [ ] CLI should support `.jmdrc` config file for defaults (author, preferred format)

---

*If something here excites you, open an issue. I ship faster with a reason.*
