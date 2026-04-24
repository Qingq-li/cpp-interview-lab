from __future__ import annotations

import base64
import cgi
import argparse
import html
import json
import os
import mimetypes
import random
import re
import signal
import sys
import subprocess
import threading
import uuid
import webbrowser
from datetime import datetime
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple
import tempfile
from urllib.parse import parse_qs, urlparse


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class NotebookSpec:
    slug: str
    title: str
    source_path: Path
    description: str


@dataclass(frozen=True)
class Section:
    title: str
    raw: str
    html: str


@dataclass(frozen=True)
class Card:
    number: int
    title: str
    sections: Tuple[Section, ...]
    source_path: Path

    @property
    def preview(self) -> str:
        for section in self.sections:
            if section.title == "核心答案":
                snippet = first_paragraph(section.raw)
                if snippet:
                    return snippet
        if self.sections:
            snippet = first_paragraph(self.sections[0].raw)
            if snippet:
                return snippet
        return self.title

    @property
    def labels(self) -> Tuple[str, ...]:
        return tuple(section.title for section in self.sections[:5])


@dataclass(frozen=True)
class Notebook:
    spec: NotebookSpec
    cards: Tuple[Card, ...]

    @property
    def by_number(self) -> Dict[int, Card]:
        return {card.number: card for card in self.cards}


NOTEBOOKS: Tuple[NotebookSpec, ...] = (
    NotebookSpec(
        slug="beginner",
        title="C++ 面试笔记：初级篇",
        source_path=ROOT / "docs" / "zh" / "beginner.md",
        description="把 beginner.md 拆成逐题 flash card，默认先看问题，再点按钮展开答案。",
    ),
    NotebookSpec(
        slug="intermediate",
        title="C++ 面试笔记：中级篇",
        source_path=ROOT / "docs" / "zh" / "intermediate.md",
        description="覆盖拷贝控制、移动语义、模板、智能指针、并发基础等中级题目。",
    ),
    NotebookSpec(
        slug="advanced",
        title="C++ 面试笔记：高级篇",
        source_path=ROOT / "docs" / "zh" / "advanced.md",
        description="整理完美转发、内存模型、SFINAE、对象切片和现代 C++ 设计。",
    ),
    NotebookSpec(
        slug="coding-round",
        title="手写代码题",
        source_path=ROOT / "docs" / "zh" / "coding-round.md",
        description="把常见手写题拆成可快速复习的独立卡片。",
    ),
    NotebookSpec(
        slug="modern-cpp",
        title="C++17 / C++20 高频特性",
        source_path=ROOT / "docs" / "zh" / "modern-cpp.md",
        description="聚焦 optional、variant、string_view、span、concepts 等现代特性。",
    ),
    NotebookSpec(
        slug="stl-container-cheatsheet",
        title="STL 容器速查表",
        source_path=ROOT / "docs" / "zh" / "stl-container-cheatsheet.md",
        description="记录 STL 容器的复杂度、迭代器失效和容器选择原则。",
    ),
    NotebookSpec(
        slug="concurrency-deep-dive",
        title="并发专题",
        source_path=ROOT / "docs" / "zh" / "concurrency-deep-dive.md",
        description="覆盖线程、锁、条件变量、内存模型、线程池和 async/future。",
    ),
    NotebookSpec(
        slug="project-answer-templates",
        title="项目回答模板",
        source_path=ROOT / "docs" / "zh" / "project-answer-templates.md",
        description="把八股题连接到真实项目表达，适合面试回答训练。",
    ),
)

CARD_HEADING_RE = re.compile(r"^##\s+(\d+)\.\s+(.+?)\s*$", re.M)
SECTION_HEADING_RE = re.compile(r"^###\s+(.+?)\s*$")
NOTE_HEADING_RE = re.compile(r"^Note:?\s*$")
FENCE_RE = re.compile(r"^```([A-Za-z0-9_+-]*)\s*$")
LIST_ITEM_RE = re.compile(r"^\s*-\s+(.*)$")
CODE_FENCE_CAPTURE_RE = re.compile(
    r"```([A-Za-z0-9_+-]*)\s*\n(.*?)\n```", re.S)

STATE_PREFIX = "flashcards:v2"
CPP_LANGUAGE = "cpp17"
DEFAULT_CPP_TEMPLATE = """#include <iostream>

int main() {
    std::cout << "Hello, world!\\n";
    return 0;
}
"""
MAX_SOURCE_CHARS = 200_000
COMPILE_TIMEOUT_SECONDS = 10
RUN_TIMEOUT_SECONDS = 3
MAX_CAPTURED_OUTPUT_CHARS = 20_000
MAX_NOTE_TEXT_CHARS = 100_000
MAX_NOTE_ATTACHMENT_BYTES = 8 * 1024 * 1024
DEFAULT_STATE_DIR = Path(os.environ.get("FLASHCARDS_STATE_DIR", ROOT / "data"))
STATE_FILE_NAME = "flashcards-state.json"


class PersistentStateStore:
    def __init__(self, state_dir: Path) -> None:
        self.state_dir = state_dir
        self.state_path = state_dir / STATE_FILE_NAME
        self._lock = threading.Lock()
        self._state = self._load()

    def _default_state(self) -> Dict[str, object]:
        return {
            "saved_cards": [],
            "notebooks": {},
            "notes": {},
        }

    def _load(self) -> Dict[str, object]:
        try:
            raw = self.state_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return self._default_state()
        except OSError:
            return self._default_state()

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return self._default_state()

        if not isinstance(data, dict):
            return self._default_state()

        saved_cards = data.get("saved_cards", [])
        notebooks = data.get("notebooks", {})
        notes = data.get("notes", {})
        if not isinstance(saved_cards, list):
            saved_cards = []
        if not isinstance(notebooks, dict):
            notebooks = {}
        if not isinstance(notes, dict):
            notes = {}
        return {
            "saved_cards": [str(entry) for entry in saved_cards],
            "notebooks": {
                str(slug): self._normalize_notebook_state(state)
                for slug, state in notebooks.items()
                if isinstance(state, dict)
            },
            "notes": {
                str(slug): {
                    str(card_id): self._normalize_note_state(note_state)
                    for card_id, note_state in cards.items()
                    if isinstance(note_state, dict)
                }
                for slug, cards in notes.items()
                if isinstance(cards, dict)
            },
        }

    @staticmethod
    def _normalize_notebook_state(state: Dict[str, object]) -> Dict[str, object]:
        viewed = state.get("viewed", {})
        if isinstance(viewed, list):
            viewed = {str(card_id): "" for card_id in viewed}
        elif not isinstance(viewed, dict):
            viewed = {}
        revealed = state.get("revealed", [])
        if not isinstance(revealed, list):
            revealed = []
        last_card = state.get("lastCard", "")
        if not isinstance(last_card, str):
            last_card = ""
        return {
            "viewed": {str(card_id): str(value) for card_id, value in viewed.items()},
            "revealed": [str(entry) for entry in revealed],
            "lastCard": last_card,
        }

    @staticmethod
    def _normalize_note_state(state: Dict[str, object]) -> Dict[str, object]:
        text = state.get("text", "")
        if not isinstance(text, str):
            text = ""
        updated_at = state.get("updatedAt", "")
        if not isinstance(updated_at, str):
            updated_at = ""
        attachments = state.get("attachments", [])
        if not isinstance(attachments, list):
            attachments = []
        normalized_attachments = []
        for attachment in attachments:
            if not isinstance(attachment, dict):
                continue
            attachment_id = attachment.get("id", "")
            if not isinstance(attachment_id, str) or not attachment_id:
                continue
            normalized_attachments.append(
                {
                    "id": attachment_id,
                    "filename": attachment.get("filename", "") if isinstance(attachment.get("filename", ""), str) else "",
                    "url": attachment.get("url", "") if isinstance(attachment.get("url", ""), str) else "",
                    "mimeType": attachment.get("mimeType", "") if isinstance(attachment.get("mimeType", ""), str) else "",
                    "createdAt": attachment.get("createdAt", "") if isinstance(attachment.get("createdAt", ""), str) else "",
                    "size": int(attachment.get("size", 0)) if isinstance(attachment.get("size", 0), int) else 0,
                }
            )
        return {
            "text": text,
            "attachments": normalized_attachments,
            "updatedAt": updated_at,
        }

    def snapshot(self) -> Dict[str, object]:
        with self._lock:
            return json.loads(json.dumps(self._state))

    def save_saved_cards(self, saved_cards: Sequence[str]) -> None:
        with self._lock:
            self._state["saved_cards"] = [str(entry) for entry in saved_cards]
            self._persist()

    def save_notebook_state(self, notebook_slug: str, state: Dict[str, object]) -> None:
        with self._lock:
            notebooks = self._state.setdefault("notebooks", {})
            if not isinstance(notebooks, dict):
                notebooks = {}
                self._state["notebooks"] = notebooks
            notebooks[str(notebook_slug)
                      ] = self._normalize_notebook_state(state)
            self._persist()

    def save_note_state(self, notebook_slug: str, card_id: str, note_state: Dict[str, object]) -> None:
        with self._lock:
            notes = self._state.setdefault("notes", {})
            if not isinstance(notes, dict):
                notes = {}
                self._state["notes"] = notes
            notebook_notes = notes.setdefault(str(notebook_slug), {})
            if not isinstance(notebook_notes, dict):
                notebook_notes = {}
                notes[str(notebook_slug)] = notebook_notes
            notebook_notes[str(card_id)] = self._normalize_note_state(
                note_state)
            self._persist()

    def _persist(self) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(self._state, ensure_ascii=False,
                             indent=2, sort_keys=True)
        tmp_path = self.state_path.with_suffix(".tmp")
        tmp_path.write_text(payload, encoding="utf-8")
        tmp_path.replace(self.state_path)


APP_CSS = """
:root {
  --bg: #f4efe6;
  --bg-2: #ece2d2;
  --surface: rgba(255, 250, 243, 0.9);
  --surface-solid: #fffaf3;
  --surface-strong: #fff2df;
  --ink: #1f1a17;
  --muted: #65584d;
  --line: rgba(81, 67, 57, 0.16);
  --accent: #0f766e;
  --accent-2: #9a3412;
  --accent-3: #b45309;
  --shadow: 0 18px 45px rgba(73, 51, 30, 0.13);
  --radius: 22px;
  --radius-sm: 14px;
  --max: 1160px;
  --font-body: "Avenir Next", "Segoe UI", "Noto Sans SC", "PingFang SC", sans-serif;
  --font-display: "Iowan Old Style", "Palatino Linotype", "Georgia", serif;
  --font-mono: "SFMono-Regular", "Consolas", "Liberation Mono", monospace;
}

* {
  box-sizing: border-box;
}

html {
  color-scheme: light;
}

body {
  margin: 0;
  color: var(--ink);
  font-family: var(--font-body);
  line-height: 1.62;
  background:
    radial-gradient(circle at top left, rgba(15, 118, 110, 0.12), transparent 28%),
    radial-gradient(circle at 85% 10%, rgba(180, 83, 9, 0.12), transparent 22%),
    linear-gradient(180deg, var(--bg), var(--bg-2));
  min-height: 100vh;
}

a {
  color: inherit;
  text-decoration: none;
}

a:hover {
  color: var(--accent);
}

.app-shell {
  max-width: var(--max);
  margin: 0 auto;
  padding: 24px;
}

.hero {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 20px;
  align-items: end;
  margin: 18px 0 22px;
}

.eyebrow {
  margin: 0 0 10px;
  text-transform: uppercase;
  letter-spacing: 0.18em;
  font-size: 12px;
  color: var(--accent-2);
  font-weight: 700;
}

.hero h1,
.hero h2 {
  margin: 0;
  font-family: var(--font-display);
  line-height: 1.05;
  letter-spacing: -0.02em;
}

.hero h1 {
  font-size: clamp(2rem, 4vw, 3.8rem);
}

.hero h2 {
  font-size: clamp(1.7rem, 3vw, 2.8rem);
}

.lede {
  max-width: 66ch;
  margin: 14px 0 0;
  color: var(--muted);
  font-size: 1.02rem;
}

.hero-card {
  padding: 18px 20px;
  border: 1px solid var(--line);
  border-radius: 20px;
  background: rgba(255, 250, 243, 0.76);
  box-shadow: var(--shadow);
  min-width: 220px;
}

.hero-card .stat {
  font-size: 30px;
  font-weight: 800;
  letter-spacing: -0.03em;
}

.hero-card .stat-label {
  margin-top: 4px;
  color: var(--muted);
  font-size: 13px;
}

.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  margin: 18px 0 20px;
}

.search {
  flex: 1 1 300px;
  min-width: 240px;
  border: 1px solid var(--line);
  background: var(--surface);
  border-radius: 999px;
  padding: 14px 18px;
  font: inherit;
  box-shadow: var(--shadow);
}

.search:focus {
  outline: 2px solid rgba(15, 118, 110, 0.35);
  outline-offset: 2px;
}

.button,
.button-secondary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border-radius: 999px;
  border: 1px solid transparent;
  padding: 13px 18px;
  font-weight: 700;
  transition: transform 0.15s ease, box-shadow 0.15s ease, background 0.15s ease;
  box-shadow: var(--shadow);
}

.button {
  background: linear-gradient(135deg, var(--accent), #115e59);
  color: #fff;
}

.button-secondary {
  background: var(--surface);
  color: var(--ink);
  border-color: var(--line);
}

.button:hover,
.button-secondary:hover {
  transform: translateY(-1px);
}

.panel {
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: var(--surface);
  box-shadow: var(--shadow);
  overflow: hidden;
}

.overview-grid {
  display: grid;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  gap: 16px;
}

.card-tile {
  grid-column: span 6;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 20px;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: rgba(255, 250, 243, 0.82);
  box-shadow: var(--shadow);
  min-height: 180px;
  transition: transform 0.16s ease, border-color 0.16s ease;
}

.card-tile:hover {
  transform: translateY(-2px);
  border-color: rgba(15, 118, 110, 0.3);
}

.card-tile .card-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  color: var(--muted);
  font-size: 13px;
}

.card-tile .card-number {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 999px;
  background: rgba(15, 118, 110, 0.12);
  color: var(--accent);
  font-weight: 800;
}

.card-tile h3 {
  margin: 0;
  font-size: 1.15rem;
  line-height: 1.35;
}

.card-preview {
  color: var(--muted);
  margin: 0;
  flex: 1 1 auto;
}

.tag-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.question-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(44px, 1fr));
  gap: 10px;
}

.question-cell {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  aspect-ratio: 1 / 1;
  border-radius: 14px;
  border: 1px solid rgba(81, 67, 57, 0.14);
  background: #e7e8ec;
  color: #64748b;
  font-weight: 800;
  font-size: 14px;
  letter-spacing: -0.02em;
  transition: transform 0.15s ease, box-shadow 0.15s ease, background 0.15s ease, color 0.15s ease;
}

.question-cell:hover {
  transform: translateY(-1px);
  box-shadow: 0 8px 18px rgba(73, 51, 30, 0.12);
}

.question-cell.is-today {
  background: linear-gradient(135deg, #1d4ed8, #0ea5e9);
  color: #fff;
  border-color: rgba(30, 64, 175, 0.35);
  box-shadow: 0 10px 20px rgba(29, 78, 216, 0.22);
}

.question-cell.is-old {
  background: #dfe3ea;
  color: #3f4a5d;
}

.question-cell.is-saved {
  outline: 2px solid rgba(180, 83, 9, 0.3);
  outline-offset: 1px;
}

.question-cell.is-new {
  background: #e7e8ec;
}

.home-saved-shell {
  margin-top: 24px;
}

.home-collection-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.home-collection-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.home-collection-body {
  margin-top: 16px;
}

.saved-empty {
  margin: 12px 0 0;
  color: var(--muted);
}

.saved-grid {
  margin-top: 16px;
}

.saved-card .reveal-actions {
  margin-top: auto;
}

.button-secondary.is-saved {
  background: rgba(15, 118, 110, 0.12);
  border-color: rgba(15, 118, 110, 0.28);
  color: var(--accent);
}

.card-workspace {
  position: relative;
}

.playground-backdrop {
  position: fixed;
  inset: 0;
  z-index: 48;
  background: rgba(25, 20, 15, 0.34);
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.2s ease;
}

.playground-backdrop.is-open {
  opacity: 1;
  pointer-events: auto;
}

.playground-drawer {
  position: fixed;
  top: 16px;
  right: 16px;
  bottom: 16px;
  width: min(480px, calc(100vw - 32px));
  z-index: 49;
  transform: translateX(calc(100% + 24px));
  visibility: hidden;
  pointer-events: none;
  transition: transform 0.24s ease, visibility 0.24s ease;
}

.playground-drawer.is-open {
  transform: translateX(0);
  visibility: visible;
  pointer-events: auto;
}

.playground-shell {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 18px;
  border: 1px solid var(--line);
  border-radius: 24px;
  background: rgba(255, 250, 243, 0.95);
  box-shadow: var(--shadow);
  backdrop-filter: blur(12px);
}

.playground-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.playground-title {
  font-family: var(--font-display);
  font-size: 1.45rem;
  line-height: 1.1;
  font-weight: 700;
}

.playground-subtitle {
  margin-top: 6px;
  color: var(--muted);
  font-size: 13px;
}

.playground-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.playground-label {
  margin: 2px 0 0;
  font-size: 13px;
  font-weight: 700;
  color: var(--muted);
}

.playground-editor,
.playground-stdin {
  width: 100%;
  border: 1px solid rgba(81, 67, 57, 0.18);
  border-radius: 16px;
  background: #14110f;
  color: #f7f4ef;
  font-family: var(--font-mono);
  font-size: 13px;
  line-height: 1.55;
  padding: 14px;
  resize: vertical;
}

.playground-editor {
  min-height: 280px;
  flex: 1 1 auto;
}

.playground-stdin {
  min-height: 90px;
}

.playground-output-grid {
  display: grid;
  gap: 12px;
}

.playground-section {
  border: 1px solid var(--line);
  border-radius: 16px;
  overflow: hidden;
  background: rgba(255, 250, 243, 0.82);
}

.playground-section-head {
  padding: 12px 14px;
  font-size: 13px;
  font-weight: 700;
  color: var(--accent);
  background: rgba(15, 118, 110, 0.06);
  border-bottom: 1px solid rgba(15, 118, 110, 0.08);
}

.playground-output {
  margin: 0;
  min-height: 112px;
  padding: 14px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
  background: #101010;
  color: #f5f2ec;
  font-family: var(--font-mono);
  font-size: 13px;
  line-height: 1.55;
}

.playground-status {
  margin-top: auto;
  color: var(--muted);
  font-size: 13px;
}

.tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(180, 83, 9, 0.08);
  color: var(--accent-2);
  font-size: 12px;
  font-weight: 700;
}

.breadcrumb {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  color: var(--muted);
  font-size: 14px;
  margin-bottom: 14px;
}

.breadcrumb a {
  color: var(--accent);
  font-weight: 700;
}

.flashcard {
  padding: 26px;
}

.question-block {
  display: grid;
  grid-template-columns: 1fr;
  gap: 16px;
  padding: 24px;
  border: 1px solid rgba(15, 118, 110, 0.18);
  border-radius: 20px;
  background:
    linear-gradient(180deg, rgba(255, 250, 243, 0.96), rgba(255, 246, 232, 0.9)),
    var(--surface-solid);
}

.question-block h1 {
  margin: 0;
  font-family: var(--font-display);
  font-size: clamp(1.6rem, 3vw, 2.4rem);
  line-height: 1.18;
}

.question-block .question-number {
  color: var(--accent-2);
  font-weight: 800;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  font-size: 12px;
}

.question-note {
  color: var(--muted);
  margin: 0;
}

.reveal-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 18px;
}

.answer-wrap {
  margin-top: 18px;
  display: grid;
  gap: 14px;
}

.answer-wrap[hidden] {
  display: none;
}

.answer-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
}

.answer-section {
  border: 1px solid var(--line);
  border-radius: 18px;
  background: rgba(255, 250, 243, 0.86);
  overflow: hidden;
}

.answer-section .section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 18px;
  background: rgba(15, 118, 110, 0.06);
  border-bottom: 1px solid rgba(15, 118, 110, 0.08);
}

.answer-section .section-head h2 {
  margin: 0;
  font-size: 1rem;
  color: var(--accent);
}

.answer-section.is-english .section-head {
  background: rgba(29, 78, 216, 0.07);
}

.answer-section.is-english .section-head h2 {
  color: #1d4ed8;
}

.answer-section .section-body {
  padding: 18px;
}

.answer-section p {
  margin: 0 0 1em;
}

.answer-section p:last-child {
  margin-bottom: 0;
}

.answer-section ul {
  margin: 0.25rem 0 0.95rem;
  padding-left: 1.25rem;
}

.answer-section li + li {
  margin-top: 0.45rem;
}

.answer-section pre {
  overflow: auto;
  margin: 0.8rem 0 0;
  padding: 16px 18px;
  border-radius: 16px;
  background: #151311;
  color: #f6f3ef;
  font-family: var(--font-mono);
  font-size: 13px;
  line-height: 1.55;
}

.answer-section code {
  font-family: var(--font-mono);
  font-size: 0.95em;
}

.answer-section p code,
.answer-section li code {
  padding: 0.12rem 0.35rem;
  border-radius: 8px;
  background: rgba(180, 83, 9, 0.12);
  color: #6b2f00;
}

.note-callout {
  margin: 0.75rem 0 0;
  padding: 16px 18px;
  border-radius: 16px;
  border: 1px solid rgba(180, 83, 9, 0.16);
  background: rgba(255, 244, 225, 0.82);
}

.note-callout .note-label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  font-size: 12px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--accent-3);
  font-weight: 800;
}

.note-panel {
  margin-top: 18px;
  border: 1px solid rgba(15, 118, 110, 0.16);
  border-radius: 20px;
  background: rgba(255, 250, 243, 0.9);
  box-shadow: 0 12px 28px rgba(73, 51, 30, 0.08);
  overflow: hidden;
}

.note-panel-head {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 12px;
  padding: 16px 18px;
  background: rgba(15, 118, 110, 0.05);
  border-bottom: 1px solid rgba(15, 118, 110, 0.08);
}

.note-title {
  font-weight: 800;
  font-size: 1.02rem;
  color: var(--accent);
}

.note-subtitle {
  margin-top: 4px;
  color: var(--muted);
  font-size: 13px;
}

.note-head-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}

.note-status,
.note-count {
  font-size: 12px;
  color: var(--muted);
}

.note-body {
  padding: 16px 18px 18px;
  display: grid;
  gap: 14px;
}

.note-body[hidden] {
  display: none;
}

.note-editor {
  width: 100%;
  min-height: 180px;
  border: 1px solid rgba(81, 67, 57, 0.16);
  border-radius: 16px;
  padding: 14px;
  resize: vertical;
  background: #fffdf8;
  color: var(--ink);
  font-family: var(--font-mono);
  font-size: 13px;
  line-height: 1.6;
}

.note-actions {
  margin-top: 0;
}

.note-preview-shell,
.note-attachments-shell {
  border: 1px solid rgba(81, 67, 57, 0.12);
  border-radius: 16px;
  overflow: hidden;
  background: rgba(255, 250, 243, 0.88);
}

.note-section-head {
  padding: 12px 14px;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--accent-2);
  background: rgba(180, 83, 9, 0.06);
  border-bottom: 1px solid rgba(180, 83, 9, 0.08);
}

.note-preview {
  padding: 14px;
  color: var(--ink);
  font-size: 14px;
  line-height: 1.7;
}

.note-empty {
  color: var(--muted);
  font-size: 13px;
}

.note-image {
  margin: 0 0 14px;
}

.note-image img,
.note-attachment-preview {
  display: block;
  max-width: 100%;
  border-radius: 14px;
  border: 1px solid rgba(81, 67, 57, 0.14);
}

.note-image figcaption {
  margin-top: 6px;
  font-size: 12px;
  color: var(--muted);
}

.note-attachments {
  display: grid;
  gap: 12px;
  padding: 14px;
}

.note-attachment-card {
  border: 1px solid rgba(81, 67, 57, 0.12);
  border-radius: 16px;
  padding: 12px;
  background: #fffdf8;
  display: grid;
  gap: 10px;
}

.note-attachment-top {
  display: flex;
  gap: 12px;
  align-items: center;
}

.note-attachment-preview {
  width: 72px;
  height: 72px;
  object-fit: cover;
  background: #f5f0e5;
}

.note-file-icon {
  width: 72px;
  height: 72px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 14px;
  background: rgba(15, 118, 110, 0.1);
  color: var(--accent);
  font-size: 12px;
  font-weight: 800;
}

.note-attachment-meta {
  min-width: 0;
}

.note-attachment-name {
  font-weight: 700;
  word-break: break-word;
}

.note-attachment-sub {
  margin-top: 4px;
  font-size: 12px;
  color: var(--muted);
}

.note-attachment-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.muted {
  color: var(--muted);
}

.progress-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  margin: 16px 0 18px;
}

.progress-track {
  flex: 1 1 260px;
  height: 10px;
  border-radius: 999px;
  background: rgba(70, 55, 44, 0.09);
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  width: 0%;
  border-radius: inherit;
  background: linear-gradient(90deg, var(--accent), #1f8f83);
  transition: width 0.18s ease;
}

.progress-meta {
  min-width: 160px;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
  font-size: 14px;
  color: var(--muted);
}

.progress-meta .muted {
  font-size: 13px;
}

.page-footer {
  margin: 24px 0 6px;
  color: var(--muted);
  font-size: 14px;
}

@media (max-width: 900px) {
  .hero {
    grid-template-columns: 1fr;
  }

  .card-tile {
    grid-column: span 12;
  }

  .flashcard {
    padding: 18px;
  }

  .question-block,
  .answer-section .section-body {
    padding: 16px;
  }

  .progress-meta {
    align-items: flex-start;
  }

  .playground-drawer {
    left: 0;
    right: 0;
    top: auto;
    bottom: 0;
    width: 100vw;
    height: 72vh;
    transform: translateY(104%);
  }

  .playground-drawer.is-open {
    transform: translateY(0);
  }

  .playground-shell {
    border-radius: 24px 24px 0 0;
  }

  .note-panel-head,
  .note-attachment-top {
    align-items: flex-start;
  }

  .note-head-actions,
  .note-attachment-actions {
    width: 100%;
  }

  .note-editor {
    min-height: 160px;
  }
}

@media (max-width: 640px) {
  .app-shell {
    padding: 16px;
  }

  .button,
  .button-secondary,
  .search {
    width: 100%;
  }

  .reveal-actions {
    flex-direction: column;
  }

  .playground-drawer {
    height: 80vh;
  }
}
"""


APP_JS = """
function safeJsonParse(value, fallback) {
  try {
    return JSON.parse(value);
  } catch (error) {
    return fallback;
  }
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function todayStamp() {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function getBootData() {
  const node = document.getElementById('flashcards-data');
  if (!node) {
    return { notebooks: [], persistentState: { saved_cards: [], notebooks: {}, notes: {} } };
  }

  return safeJsonParse(node.textContent || node.innerText || '{}', {
    notebooks: [],
    persistentState: { saved_cards: [], notebooks: {}, notes: {} },
  }) || { notebooks: [], persistentState: { saved_cards: [], notebooks: {}, notes: {} } };
}

function getBootPersistentState() {
  const boot = getBootData();
  const persistentState = boot.persistentState || {};
  return {
    saved_cards: Array.isArray(persistentState.saved_cards) ? persistentState.saved_cards : [],
    notebooks: persistentState.notebooks && typeof persistentState.notebooks === 'object' ? persistentState.notebooks : {},
    notes: persistentState.notes && typeof persistentState.notes === 'object' ? persistentState.notes : {},
  };
}

function hydratePersistentStateFromBoot() {
  const persistentState = getBootPersistentState();
  localStorage.setItem(getStoreKey('saved'), JSON.stringify(persistentState.saved_cards || []));
  Object.entries(persistentState.notebooks || {}).forEach(([slug, state]) => {
    localStorage.setItem(getStoreKey(`notebook:${slug}`), JSON.stringify(state));
  });
  Object.entries(persistentState.notes || {}).forEach(([slug, cards]) => {
    Object.entries(cards || {}).forEach(([cardId, noteState]) => {
      localStorage.setItem(getStoreKey(`note:${slug}:${cardId}`), JSON.stringify(noteState));
    });
  });
}

async function refreshPersistentStateFromServer() {
  const response = await fetch('/_api/state', { cache: 'no-store' });
  if (!response.ok) {
    throw new Error(`Failed to load persistent state: ${response.status}`);
  }

  const snapshot = await response.json();
  const savedCards = Array.isArray(snapshot.saved_cards) ? snapshot.saved_cards : [];
  const notebooks = snapshot.notebooks && typeof snapshot.notebooks === 'object' ? snapshot.notebooks : {};
  const notes = snapshot.notes && typeof snapshot.notes === 'object' ? snapshot.notes : {};

  localStorage.setItem(getStoreKey('saved'), JSON.stringify(savedCards));

  Object.keys(localStorage).forEach((key) => {
    if (!key.startsWith(getStoreKey('notebook:')) && !key.startsWith(getStoreKey('note:'))) {
      return;
    }
    localStorage.removeItem(key);
  });

  Object.entries(notebooks).forEach(([slug, state]) => {
    localStorage.setItem(getStoreKey(`notebook:${slug}`), JSON.stringify(state));
  });

  Object.entries(notes).forEach(([slug, cards]) => {
    Object.entries(cards || {}).forEach(([cardId, noteState]) => {
      localStorage.setItem(getStoreKey(`note:${slug}:${cardId}`), JSON.stringify(noteState));
    });
  });
}

function getStoreKey(scope) {
  return `flashcards:v2:${scope}`;
}

function getNotebookState(notebookSlug) {
  const raw = localStorage.getItem(getStoreKey(`notebook:${notebookSlug}`));
  const state = safeJsonParse(raw, null) || {};

  if (Array.isArray(state.viewed)) {
    const viewed = {};
    state.viewed.forEach((cardId) => {
      viewed[String(cardId)] = '';
    });
    state.viewed = viewed;
  } else if (!state.viewed || typeof state.viewed !== 'object') {
    state.viewed = {};
  }

  state.revealed = Array.isArray(state.revealed) ? state.revealed : [];
  state.lastCard = typeof state.lastCard === 'string' ? state.lastCard : '';
  return state;
}

function saveNotebookState(notebookSlug, state) {
  localStorage.setItem(getStoreKey(`notebook:${notebookSlug}`), JSON.stringify(state));
  syncPersistentState('notebook', { notebookSlug, state });
}

function getSavedCards() {
  const raw = localStorage.getItem(getStoreKey('saved'));
  const saved = safeJsonParse(raw, []);
  return Array.isArray(saved) ? saved : [];
}

function saveSavedCards(savedCards) {
  localStorage.setItem(getStoreKey('saved'), JSON.stringify(savedCards));
  syncPersistentState('saved_cards', { savedCards });
}

function noteKey(notebookSlug, cardId) {
  return `note:${notebookSlug}:${cardId}`;
}

function getNoteState(notebookSlug, cardId) {
  const raw = localStorage.getItem(getStoreKey(noteKey(notebookSlug, cardId)));
  const state = safeJsonParse(raw, null) || {};
  state.text = typeof state.text === 'string' ? state.text : '';
  state.updatedAt = typeof state.updatedAt === 'string' ? state.updatedAt : '';
  state.open = Boolean(state.open);
  state.attachments = Array.isArray(state.attachments) ? state.attachments : [];
  state.attachments = state.attachments
    .filter((entry) => entry && typeof entry === 'object')
    .map((entry) => ({
      id: typeof entry.id === 'string' ? entry.id : '',
      filename: typeof entry.filename === 'string' ? entry.filename : '',
      url: typeof entry.url === 'string' ? entry.url : '',
      mimeType: typeof entry.mimeType === 'string' ? entry.mimeType : '',
      createdAt: typeof entry.createdAt === 'string' ? entry.createdAt : '',
      size: Number.isInteger(entry.size) ? entry.size : 0,
      storedName: typeof entry.storedName === 'string' ? entry.storedName : '',
    }))
    .filter((entry) => entry.id && entry.url);
  return state;
}

function saveNoteState(notebookSlug, cardId, state) {
  localStorage.setItem(getStoreKey(noteKey(notebookSlug, cardId)), JSON.stringify(state));
  syncPersistentState('note', { notebookSlug, cardId: String(cardId), noteState: state });
}

function syncPersistentState(kind, payload) {
  fetch('/_api/state', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ kind, ...payload }),
  }).catch(() => {});
}

function cardKey(notebookSlug, cardId) {
  return `${notebookSlug}:${cardId}`;
}

function isCardSaved(notebookSlug, cardId) {
  return getSavedCards().includes(cardKey(notebookSlug, cardId));
}

function toggleCardSaved(notebookSlug, cardId) {
  const key = cardKey(notebookSlug, cardId);
  const saved = getSavedCards();
  const index = saved.indexOf(key);

  if (index >= 0) {
    saved.splice(index, 1);
    saveSavedCards(saved);
    return false;
  }

  saved.unshift(key);
  saveSavedCards(saved);
  return true;
}

function markVisited(notebookSlug, cardId) {
  const state = getNotebookState(notebookSlug);
  const entry = String(cardId);
  state.viewed[entry] = todayStamp();
  state.lastCard = entry;
  saveNotebookState(notebookSlug, state);
}

function visitedToday(notebookSlug, cardId) {
  const state = getNotebookState(notebookSlug);
  return state.viewed[String(cardId)] === todayStamp();
}

function renderProgress(root, notebookSlug) {
  const state = getNotebookState(notebookSlug);
  const total = Number(root.dataset.totalCards || '0');
  const visitedEntries = Object.keys(state.viewed);
  const today = todayStamp();
  const todayCount = visitedEntries.filter((cardId) => state.viewed[cardId] === today).length;
  const progressFill = document.querySelector('[data-progress-fill]');
  const progressLabels = document.querySelectorAll('[data-progress-label]');
  const todayLabels = document.querySelectorAll('[data-today-label]');

  if (progressFill) {
    progressFill.style.width = total ? `${Math.min(100, (visitedEntries.length / total) * 100)}%` : '0%';
  }

  progressLabels.forEach((label) => {
    label.textContent = total
      ? `${visitedEntries.length}/${total} visited`
      : '0 visited';
  });

  todayLabels.forEach((label) => {
    label.textContent = `${todayCount} today`;
  });
}

function updateQuestionGrid(notebookSlug) {
  const state = getNotebookState(notebookSlug);
  const today = todayStamp();

  document.querySelectorAll('[data-question-cell]').forEach((cell) => {
    const cardId = cell.dataset.cardId;
    const visitedAt = state.viewed[cardId] || '';
    const saved = isCardSaved(notebookSlug, cardId);
    const todayFlag = visitedAt === today;
    cell.classList.toggle('is-today', todayFlag);
    cell.classList.toggle('is-old', Boolean(visitedAt) && !todayFlag);
    cell.classList.toggle('is-new', !visitedAt);
    cell.classList.toggle('is-saved', saved);
    cell.setAttribute('aria-pressed', saved ? 'true' : 'false');
  });
}

function bindSearch() {
  const searchInput = document.querySelector('[data-card-search]');
  const cards = Array.from(document.querySelectorAll('[data-card-tile]'));
  const visibleLabel = document.querySelector('[data-visible-count]');
  const clearButton = document.querySelector('[data-clear-button]');

  const refresh = () => {
    const query = (searchInput && searchInput.value || '').trim().toLowerCase();
    let visibleCount = 0;

    cards.forEach((tile) => {
      const haystack = (tile.dataset.searchText || '').toLowerCase();
      const visible = !query || haystack.includes(query);
      tile.hidden = !visible;
      if (visible) {
        visibleCount += 1;
      }
    });

    if (visibleLabel) {
      visibleLabel.textContent = String(visibleCount);
    }
  };

  if (searchInput) {
    searchInput.addEventListener('input', refresh);
  }

  if (clearButton) {
    clearButton.addEventListener('click', () => {
      if (searchInput) {
        searchInput.value = '';
        refresh();
        searchInput.focus();
      }
    });
  }

  refresh();
}

function bindOverviewPage() {
  const grid = document.querySelector('[data-overview-root]');
  const notebookRoot = document.querySelector('[data-notebook-root]');
  if (!grid || !notebookRoot) {
    return;
  }

  const notebookSlug = grid.dataset.notebookSlug;
  const resumeButton = document.querySelector('[data-resume-button]');

  if (resumeButton) {
    const state = getNotebookState(notebookSlug);
    if (state.lastCard) {
      resumeButton.href = `/${notebookSlug}/${state.lastCard}`;
      resumeButton.hidden = false;
    } else {
      resumeButton.hidden = true;
    }
  }

  updateQuestionGrid(notebookSlug);
  renderProgress(notebookRoot, notebookSlug);
  bindSearch();
}

function bindCardPage() {
  const root = document.querySelector('[data-card-root]');
  if (!root) {
    return;
  }

  const notebookSlug = root.dataset.notebookSlug;
  const cardId = root.dataset.cardId;
  const revealKey = root.dataset.revealKey;
  const answerWrap = document.querySelector('[data-answer-wrap]');
  const revealButton = document.querySelector('[data-reveal-button]');
  const saveButton = document.querySelector('[data-save-button]');
  const randomButton = document.querySelector('[data-random-button]');

  const syncSaveButton = () => {
    if (!saveButton) {
      return;
    }
    const saved = isCardSaved(notebookSlug, cardId);
    saveButton.textContent = saved ? 'SAVED' : 'SAVE';
    saveButton.classList.toggle('is-saved', saved);
    saveButton.setAttribute('aria-pressed', saved ? 'true' : 'false');
  };

  const openAnswer = () => {
    if (!answerWrap || !revealButton) {
      return;
    }

    answerWrap.hidden = false;
    revealButton.hidden = true;
    const state = getNotebookState(notebookSlug);
    const entry = String(cardId);
    if (!state.revealed.includes(entry)) {
      state.revealed.push(entry);
    }
    state.lastCard = entry;
    saveNotebookState(notebookSlug, state);
    markVisited(notebookSlug, cardId);
    updateQuestionGrid(notebookSlug);
    renderProgress(root, notebookSlug);
    answerWrap.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  const state = getNotebookState(notebookSlug);
  if (state.revealed.includes(String(cardId)) || localStorage.getItem(revealKey) === '1') {
    openAnswer();
  }

  if (revealButton) {
    revealButton.addEventListener('click', () => {
      localStorage.setItem(revealKey, '1');
      openAnswer();
    });
  }

  if (saveButton) {
    saveButton.addEventListener('click', () => {
      toggleCardSaved(notebookSlug, cardId);
      syncSaveButton();
      updateQuestionGrid(notebookSlug);
    });
  }

  if (randomButton) {
    randomButton.addEventListener('click', () => {
      window.location.href = randomButton.dataset.target || randomButton.href;
    });
  }

  syncSaveButton();
  markVisited(notebookSlug, cardId);
  updateQuestionGrid(notebookSlug);
  renderProgress(root, notebookSlug);
}

function bindPlaygroundPanel() {
  const root = document.querySelector('[data-playground-root]');
  if (!root) {
    return;
  }

  const notebookSlug = root.dataset.notebookSlug;
  const cardId = root.dataset.cardId;
  const storageKey = `playground:${notebookSlug}:${cardId}`;
  const data = safeJsonParse(root.dataset.playgroundData || '{}', { samples: [], defaultSource: '', defaultTemplate: '', language: 'cpp17' }) || {};
  const samples = Array.isArray(data.samples) ? data.samples : [];
  const defaultSource = typeof data.defaultSource === 'string' ? data.defaultSource : '';
  const defaultTemplate = typeof data.defaultTemplate === 'string' ? data.defaultTemplate : '';
  const language = typeof data.language === 'string' ? data.language : 'cpp17';

  const openButton = document.querySelector('[data-playground-open]');
  const closeButton = root.querySelector('[data-playground-close]');
  const loadButton = root.querySelector('[data-playground-load-example]');
  const clearButton = root.querySelector('[data-playground-clear]');
  const runButton = root.querySelector('[data-playground-run]');
  const sourceEditor = root.querySelector('[data-playground-source]');
  const stdinEditor = root.querySelector('[data-playground-stdin]');
  const compileOutput = root.querySelector('[data-playground-compile-output]');
  const runtimeOutput = root.querySelector('[data-playground-runtime-output]');
  const statusLabel = root.querySelector('[data-playground-status]');
  const backdrop = document.querySelector('[data-playground-backdrop]');

  const rawState = safeJsonParse(localStorage.getItem(getStoreKey(storageKey)), null) || {};
  const state = {
    open: Boolean(rawState.open),
    source: typeof rawState.source === 'string' ? rawState.source : undefined,
    stdin: typeof rawState.stdin === 'string' ? rawState.stdin : '',
    sampleIndex: Number.isInteger(rawState.sampleIndex) ? rawState.sampleIndex : 0,
    lastResult: rawState.lastResult && typeof rawState.lastResult === 'object' ? rawState.lastResult : null,
  };

  const saveState = () => {
    localStorage.setItem(getStoreKey(storageKey), JSON.stringify(state));
  };

  const setOutput = (result) => {
    if (!result) {
      return;
    }

    const compileParts = [];
    if (result.compile_stdout) {
      compileParts.push(result.compile_stdout);
    }
    if (result.compile_stderr) {
      compileParts.push(result.compile_stderr);
    }
    if (!compileParts.length && result.phase === 'validation' && result.error) {
      compileParts.push(result.error);
    }
    if (!compileParts.length && result.phase === 'compile') {
      compileParts.push('Compilation finished without diagnostics.');
    }
    if (compileOutput) {
      compileOutput.textContent = compileParts.join('\\n').trim() || 'Compilation succeeded.';
    }

    const runtimeParts = [];
    if (result.run_stdout) {
      runtimeParts.push(result.run_stdout);
    }
    if (result.run_stderr) {
      runtimeParts.push(result.run_stderr);
    }
    if (result.phase === 'compile') {
      runtimeParts.push('Program was not executed because compilation failed.');
    } else if (result.phase === 'validation' && result.error) {
      runtimeParts.push('Program was not executed.');
    } else if (!runtimeParts.length && result.ok) {
      runtimeParts.push('Program finished without output.');
    }
    if (runtimeOutput) {
      runtimeOutput.textContent = runtimeParts.join('\\n').trim() || 'No runtime output.';
    }

    if (statusLabel) {
      if (result.phase === 'validation' && result.error) {
        statusLabel.textContent = result.error;
      } else if (result.phase === 'compile') {
        statusLabel.textContent = 'Compilation failed.';
      } else if (result.run_timed_out) {
        statusLabel.textContent = 'Runtime timed out.';
      } else if (result.ok) {
        statusLabel.textContent = `Done. Exit code ${result.run_returncode}.`;
      } else {
        statusLabel.textContent = `Runtime finished with exit code ${result.run_returncode}.`;
      }
    }
  };

  const setOpen = (open) => {
    root.classList.toggle('is-open', open);
    root.setAttribute('aria-hidden', open ? 'false' : 'true');
    if (backdrop) {
      backdrop.hidden = !open;
      backdrop.classList.toggle('is-open', open);
    }
    document.body.classList.toggle('playground-open', open);
    state.open = open;
    saveState();
    if (open && sourceEditor) {
      sourceEditor.focus();
      sourceEditor.select();
    }
  };

  const syncEditors = () => {
    if (sourceEditor) {
      const initialSource = state.source === undefined ? defaultSource : state.source;
      sourceEditor.value = initialSource || defaultSource || defaultTemplate;
    }
    if (stdinEditor) {
      stdinEditor.value = state.stdin;
    }
    if (compileOutput && !state.lastResult) {
      compileOutput.textContent = 'Waiting for code...';
    }
    if (runtimeOutput && !state.lastResult) {
      runtimeOutput.textContent = 'RUN to see output.';
    }
    if (state.lastResult) {
      setOutput(state.lastResult);
    }
  };

  if (openButton) {
    openButton.addEventListener('click', () => {
      setOpen(true);
    });
  }

  if (closeButton) {
    closeButton.addEventListener('click', () => setOpen(false));
  }

  if (backdrop) {
    backdrop.addEventListener('click', () => setOpen(false));
  }

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && root.classList.contains('is-open')) {
      setOpen(false);
    }
  });

  if (sourceEditor) {
    sourceEditor.addEventListener('input', () => {
      state.source = sourceEditor.value;
      saveState();
    });
  }

  if (stdinEditor) {
    stdinEditor.addEventListener('input', () => {
      state.stdin = stdinEditor.value;
      saveState();
    });
  }

  if (loadButton) {
    loadButton.addEventListener('click', () => {
      if (samples.length) {
        const index = state.sampleIndex % samples.length;
        state.source = samples[index];
        state.sampleIndex = (index + 1) % samples.length;
      } else {
        state.source = defaultSource || defaultTemplate;
      }
      if (sourceEditor) {
        sourceEditor.value = state.source || defaultSource || defaultTemplate;
      }
      saveState();
    });
  }

  if (clearButton) {
    clearButton.addEventListener('click', () => {
      state.source = '';
      state.stdin = '';
      state.lastResult = null;
      state.sampleIndex = 0;
      if (sourceEditor) {
        sourceEditor.value = '';
      }
      if (stdinEditor) {
        stdinEditor.value = '';
      }
      if (compileOutput) {
        compileOutput.textContent = 'Waiting for code...';
      }
      if (runtimeOutput) {
        runtimeOutput.textContent = 'RUN to see output.';
      }
      if (statusLabel) {
        statusLabel.textContent = 'Cleared.';
      }
      saveState();
    });
  }

  if (runButton) {
    runButton.addEventListener('click', async () => {
      const payload = {
        source: sourceEditor ? sourceEditor.value : '',
        stdin: stdinEditor ? stdinEditor.value : '',
        language,
        notebook_slug: notebookSlug,
        card_id: cardId,
      };

      runButton.disabled = true;
      const previousLabel = runButton.textContent;
      runButton.textContent = 'RUNNING...';
      if (statusLabel) {
        statusLabel.textContent = 'Compiling...';
      }

      try {
        const response = await fetch('/_api/compile', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        const result = await response.json();
        state.lastResult = result;
        saveState();
        setOutput(result);
      } catch (error) {
        const result = {
          ok: false,
          phase: 'network',
          error: `Request failed: ${error && error.message ? error.message : error}`,
        };
        state.lastResult = result;
        saveState();
        if (compileOutput) {
          compileOutput.textContent = result.error;
        }
        if (runtimeOutput) {
          runtimeOutput.textContent = 'Program was not executed.';
        }
        if (statusLabel) {
          statusLabel.textContent = result.error;
        }
      } finally {
        runButton.disabled = false;
        runButton.textContent = previousLabel;
      }
    });
  }

  if (backdrop) {
    backdrop.hidden = !state.open;
  }
  setOpen(state.open);
  syncEditors();
  setOutput(state.lastResult);
}

function escapeRegExp(value) {
  const slash = String.fromCharCode(92);
  return String(value)
    .split(slash).join(slash + slash)
    .split('.').join(slash + '.')
    .split('*').join(slash + '*')
    .split('+').join(slash + '+')
    .split('?').join(slash + '?')
    .split('^').join(slash + '^')
    .split('$').join(slash + '$')
    .split('{').join(slash + '{')
    .split('}').join(slash + '}')
    .split('(').join(slash + '(')
    .split(')').join(slash + ')')
    .split('|').join(slash + '|')
    .split('[').join(slash + '[')
    .split(']').join(slash + ']');
}

function renderNotePreview(text) {
  const escaped = escapeHtml(text || '');
  if (!escaped.trim()) {
    return '<div class="note-empty">Paste text or screenshots here. `Ctrl+V` works when the note editor is focused.</div>';
  }

  let htmlText = escaped;
  htmlText = htmlText.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, (match, alt, url) => {
    const safeAlt = escapeHtml(alt || '');
    return `<figure class="note-image"><img src="${escapeHtml(url)}" alt="${safeAlt}"><figcaption>${safeAlt || 'image'}</figcaption></figure>`;
  });
  htmlText = htmlText.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (match, label, url) => `<a href="${escapeHtml(url)}" target="_blank" rel="noreferrer">${label}</a>`);
  return htmlText.split(String.fromCharCode(10)).join('<br>');
}

function insertTextAtCursor(textarea, text) {
  if (!textarea) {
    return;
  }

  const start = textarea.selectionStart ?? textarea.value.length;
  const end = textarea.selectionEnd ?? textarea.value.length;
  const before = textarea.value.slice(0, start);
  const after = textarea.value.slice(end);
  textarea.value = `${before}${text}${after}`;
  const cursor = start + text.length;
  textarea.selectionStart = cursor;
  textarea.selectionEnd = cursor;
}

function fileToDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ''));
    reader.onerror = () => reject(reader.error || new Error('Failed to read file.'));
    reader.readAsDataURL(file);
  });
}

async function uploadNoteAttachment(notebookSlug, cardId, file) {
  const dataUrl = await fileToDataUrl(file);
  const response = await fetch('/_api/note-attachment', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      notebookSlug,
      cardId: String(cardId),
      filename: file.name || 'paste.png',
      dataUrl,
    }),
  });
  const result = await response.json();
  if (!response.ok || !result.ok) {
    throw new Error(result && result.error ? result.error : 'Upload failed.');
  }
  return result.attachment;
}

async function deleteNoteAttachment(notebookSlug, cardId, attachmentUrl) {
  const response = await fetch('/_api/note-attachment-delete', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      notebookSlug,
      cardId: String(cardId),
      attachmentUrl,
    }),
  });
  const result = await response.json();
  if (!response.ok || !result.ok) {
    throw new Error(result && result.error ? result.error : 'Delete failed.');
  }
}

function bindNotePanel() {
  const root = document.querySelector('[data-note-root]');
  if (!root) {
    return;
  }

  const notebookSlug = root.dataset.notebookSlug;
  const cardId = root.dataset.cardId;
  const storageKey = getStoreKey(noteKey(notebookSlug, cardId));
  const state = getNoteState(notebookSlug, cardId);
  const noteBody = root.querySelector('[data-note-body]');
  const toggleButtons = Array.from(document.querySelectorAll('[data-note-toggle]'));
  const clearButton = root.querySelector('[data-note-clear]');
  const collapseButton = root.querySelector('[data-note-collapse]');
  const textarea = root.querySelector('[data-note-text]');
  const preview = root.querySelector('[data-note-preview]');
  const attachmentList = root.querySelector('[data-note-attachments]');
  const countLabel = root.querySelector('[data-note-count]');
  const statusLabel = root.querySelector('[data-note-status]');

  let syncTimer = null;
  state.open = Boolean(state.open || state.text.trim() || state.attachments.length);

  const persist = (immediate = false) => {
    localStorage.setItem(storageKey, JSON.stringify(state));
    if (syncTimer) {
      clearTimeout(syncTimer);
      syncTimer = null;
    }
    if (immediate) {
      syncPersistentState('note', { notebookSlug, cardId: String(cardId), noteState: state });
    } else {
      syncTimer = window.setTimeout(() => {
        syncPersistentState('note', { notebookSlug, cardId: String(cardId), noteState: state });
      }, 450);
    }
    if (statusLabel) {
      statusLabel.textContent = state.updatedAt ? `Saved ${state.updatedAt.replace('T', ' ').slice(0, 19)}` : 'Draft';
    }
  };

  const syncEditorValue = () => {
    if (textarea && textarea.value !== state.text) {
      textarea.value = state.text;
    }
  };

  const renderAttachments = () => {
    if (!attachmentList) {
      return;
    }

    if (!state.attachments.length) {
      attachmentList.innerHTML = '<div class="note-empty">No attachments yet.</div>';
      if (countLabel) {
        countLabel.textContent = '0';
      }
      return;
    }

    attachmentList.innerHTML = state.attachments
      .map((attachment) => {
        const isImage = (attachment.mimeType || '').startsWith('image/');
        const previewHtml = isImage
          ? `<img src="${escapeHtml(attachment.url)}" alt="${escapeHtml(attachment.filename || 'attachment')}" class="note-attachment-preview">`
          : `<span class="note-file-icon">FILE</span>`;
        return `
          <article class="note-attachment-card" data-attachment-id="${escapeHtml(attachment.id)}">
            <div class="note-attachment-top">
              ${previewHtml}
              <div class="note-attachment-meta">
                <div class="note-attachment-name">${escapeHtml(attachment.filename || 'attachment')}</div>
                <div class="note-attachment-sub">${escapeHtml(attachment.mimeType || '')}</div>
              </div>
            </div>
            <div class="note-attachment-actions">
              <a class="button-secondary" href="${escapeHtml(attachment.url)}" target="_blank" rel="noreferrer">Open</a>
              <button class="button-secondary" type="button" data-note-delete-attachment data-attachment-url="${escapeHtml(attachment.url)}">Delete</button>
            </div>
          </article>
        `;
      })
      .join('');

    attachmentList.querySelectorAll('[data-note-delete-attachment]').forEach((button) => {
      button.addEventListener('click', async () => {
        const attachmentUrl = button.dataset.attachmentUrl || '';
        if (!attachmentUrl) {
          return;
        }

        button.disabled = true;
        try {
          await deleteNoteAttachment(notebookSlug, cardId, attachmentUrl);
          state.attachments = state.attachments.filter((item) => item.url !== attachmentUrl);
          state.text = state.text
            .replace(new RegExp(`!\\[[^\\]]*\\]\\(${escapeRegExp(attachmentUrl)}\\)\\n?`, 'g'), '')
            .replace(new RegExp(`\\[[^\\]]*\\]\\(${escapeRegExp(attachmentUrl)}\\)`, 'g'), '')
            .trim();
          state.updatedAt = new Date().toISOString();
          syncEditorValue();
          renderPreview();
          renderAttachments();
          persist(true);
        } catch (error) {
          if (statusLabel) {
            statusLabel.textContent = error && error.message ? error.message : 'Failed to delete attachment.';
          }
        } finally {
          button.disabled = false;
        }
      });
    });

    if (countLabel) {
      countLabel.textContent = String(state.attachments.length);
    }
  };

  const renderPreview = () => {
    if (preview) {
      preview.innerHTML = renderNotePreview(state.text);
    }
  };

  const setOpen = (open, focusEditor = false) => {
    state.open = open;
    if (noteBody) {
      noteBody.hidden = !open;
    }
    toggleButtons.forEach((button) => {
      button.textContent = open ? 'Hide note' : 'Open note';
    });
    if (open && focusEditor && textarea) {
      textarea.focus();
    }
    persist(true);
  };

  const scheduleSave = () => {
    state.updatedAt = new Date().toISOString();
    persist(false);
    renderPreview();
    renderAttachments();
  };

  syncEditorValue();
  renderPreview();
  renderAttachments();
  setOpen(state.open, false);

  toggleButtons.forEach((button) => {
    button.addEventListener('click', () => setOpen(!state.open, !state.open));
  });

  if (collapseButton) {
    collapseButton.addEventListener('click', () => setOpen(false));
  }

  if (textarea) {
    textarea.addEventListener('input', () => {
      state.text = textarea.value;
      scheduleSave();
    });

    textarea.addEventListener('paste', async (event) => {
      const clipboardItems = Array.from((event.clipboardData && event.clipboardData.items) || []);
      const imageFiles = clipboardItems
        .map((item) => item.kind === 'file' ? item.getAsFile() : null)
        .filter((file) => file && file.type && file.type.startsWith('image/'));

      if (!imageFiles.length) {
        return;
      }

      event.preventDefault();
      const insertedSnippets = [];
      try {
        for (const file of imageFiles) {
          const attachment = await uploadNoteAttachment(notebookSlug, cardId, file);
          state.attachments.push(attachment);
          insertedSnippets.push(`![${attachment.filename}](${attachment.url})`);
        }
        const snippet = `${insertedSnippets.join(String.fromCharCode(10))}${String.fromCharCode(10)}`;
        insertTextAtCursor(textarea, snippet);
        state.text = textarea.value;
        scheduleSave();
        renderAttachments();
        setOpen(true, false);
      } catch (error) {
        if (statusLabel) {
          statusLabel.textContent = error && error.message ? error.message : 'Failed to upload clipboard image.';
        }
      }
    });
  }

  if (clearButton) {
    clearButton.addEventListener('click', async () => {
      if (!state.text && !state.attachments.length) {
        return;
      }

      clearButton.disabled = true;
      try {
        for (const attachment of [...state.attachments]) {
          await deleteNoteAttachment(notebookSlug, cardId, attachment.url);
        }
      } catch (error) {
        if (statusLabel) {
          statusLabel.textContent = error && error.message ? error.message : 'Failed to clear attachments.';
        }
      }
      state.text = '';
      state.attachments = [];
      state.updatedAt = new Date().toISOString();
      if (textarea) {
        textarea.value = '';
      }
      renderPreview();
      renderAttachments();
      persist(true);
      clearButton.disabled = false;
    });
  }

  window.addEventListener('beforeunload', () => {
    if (syncTimer) {
      clearTimeout(syncTimer);
      syncTimer = null;
      syncPersistentState('note', { notebookSlug, cardId: String(cardId), noteState: state });
    }
  });
}

function bindHomePage() {
  const root = document.querySelector('[data-home-root]');
  if (!root) {
    return;
  }

  const boot = getBootData();
  const savedRoot = document.querySelector('[data-saved-root]');
  const savedEmpty = document.querySelector('[data-saved-empty]');
  const savedCount = document.querySelector('[data-saved-count]');
  const collectionBodies = new Map(Array.from(document.querySelectorAll('[data-home-body]')).map((node) => [node.dataset.homeBody, node]));
  const collectionToggles = new Map();
  const cardMap = new Map();

  boot.notebooks.forEach((notebook) => {
    notebook.cards.forEach((card) => {
      cardMap.set(cardKey(notebook.slug, card.number), { notebook, card });
    });
  });

  document.querySelectorAll('[data-home-toggle]').forEach((button) => {
    const target = button.dataset.homeToggle;
    if (!target) {
      return;
    }
    const group = collectionToggles.get(target) || { button: null };
    group.button = button;
    collectionToggles.set(target, group);
  });

  const setCollectionOpen = (name, open) => {
    const body = collectionBodies.get(name);
    const toggles = collectionToggles.get(name) || {};
    if (body) {
      body.hidden = !open;
    }
    if (toggles.button) {
      toggles.button.textContent = open ? '折叠' : '展开';
      toggles.button.setAttribute('aria-expanded', open ? 'true' : 'false');
    }
  };

  collectionToggles.forEach((_, name) => setCollectionOpen(name, false));

  document.querySelectorAll('[data-home-toggle]').forEach((button) => {
    const target = button.dataset.homeToggle;
    if (!target) {
      return;
    }
    button.addEventListener('click', () => {
      const body = collectionBodies.get(target);
      setCollectionOpen(target, !(body && !body.hidden));
    });
  });

  const renderSaved = () => {
    if (!savedRoot) {
      return;
    }

    const entries = getSavedCards();
    if (savedCount) {
      savedCount.textContent = String(entries.length);
    }

    if (!entries.length) {
      if (savedRoot.querySelector('[data-saved-card]')) {
        if (savedEmpty) {
          savedEmpty.hidden = true;
        }
        if (savedCount) {
          savedCount.textContent = String(savedRoot.querySelectorAll('[data-saved-card]').length);
        }
        return;
      }
      savedRoot.innerHTML = '';
      if (savedEmpty) {
        savedEmpty.hidden = false;
      }
      return;
    }

    if (savedEmpty) {
      savedEmpty.hidden = true;
    }

    savedRoot.innerHTML = entries
      .map((key) => {
        const pair = cardMap.get(key);
        if (!pair) {
          return '';
        }

        const notebook = pair.notebook;
        const card = pair.card;
        return `
          <article class="card-tile saved-card" data-saved-card data-key="${escapeHtml(key)}">
            <div class="card-meta">
              <span class="card-number">${String(card.number).padStart(2, '0')}</span>
              <span>${escapeHtml(notebook.title)}</span>
            </div>
            <h3>${escapeHtml(card.title)}</h3>
            <p class="card-preview">${escapeHtml(card.preview)}</p>
            <div class="tag-row">
              ${card.labels.map((label) => `<span class="tag">${escapeHtml(label)}</span>`).join('')}
            </div>
            <div class="reveal-actions">
              <a class="button" href="${escapeHtml(card.url)}">Open</a>
              <button class="button-secondary" type="button" data-unsave-button data-key="${escapeHtml(key)}">Remove</button>
            </div>
          </article>
        `;
      })
      .join('');

    savedRoot.querySelectorAll('[data-unsave-button]').forEach((button) => {
      button.addEventListener('click', () => {
        const key = button.dataset.key;
        const current = getSavedCards().filter((entry) => entry !== key);
        saveSavedCards(current);
        renderSaved();
      });
    });
  };

  renderSaved();

  window.addEventListener('storage', (event) => {
    if (!event.key || event.key.startsWith(getStoreKey('saved')) || event.key.startsWith(getStoreKey('notebook:'))) {
      renderSaved();
      const activeNotebook = document.querySelector('[data-overview-root]');
      if (activeNotebook) {
        updateQuestionGrid(activeNotebook.dataset.notebookSlug);
        renderProgress(activeNotebook, activeNotebook.dataset.notebookSlug);
      }
    }
  });
}

document.addEventListener('DOMContentLoaded', () => {
  const init = async () => {
    hydratePersistentStateFromBoot();
    try {
      await refreshPersistentStateFromServer();
    } catch (error) {
      console.warn('Persistent state refresh failed:', error);
    }

    bindHomePage();
    bindOverviewPage();
    bindCardPage();
    bindPlaygroundPanel();
    bindNotePanel();
  };

  init();
});
"""


def notebook_index() -> Tuple[Notebook, ...]:
    notebooks: List[Notebook] = []
    for spec in NOTEBOOKS:
        notebooks.append(load_notebook(spec))
    return tuple(notebooks)


def load_notebook(spec: NotebookSpec) -> Notebook:
    if not spec.source_path.exists():
        raise FileNotFoundError(
            f"Notebook source not found: {spec.source_path}")

    text = spec.source_path.read_text(encoding="utf-8")
    cards: List[Card] = []
    matches = list(CARD_HEADING_RE.finditer(text))

    for index, match in enumerate(matches):
        number = int(match.group(1))
        title = match.group(2).strip()
        body_start = match.end()
        body_end = matches[index + 1].start() if index + \
            1 < len(matches) else len(text)
        body = text[body_start:body_end].strip("\n")
        if not body.strip():
            continue

        sections = parse_sections(body)
        cards.append(
            Card(
                number=number,
                title=title,
                sections=tuple(sections),
                source_path=spec.source_path,
            )
        )

    cards.sort(key=lambda card: card.number)
    return Notebook(spec=spec, cards=tuple(cards))


def parse_sections(body: str) -> List[Section]:
    sections: List[Section] = []
    current_title: Optional[str] = None
    buffer: List[str] = []
    in_code = False

    def flush() -> None:
        nonlocal current_title, buffer
        if current_title is None:
            buffer = []
            return
        raw = "\n".join(buffer).strip("\n")
        if raw.strip():
            sections.append(
                Section(
                    title=current_title,
                    raw=raw,
                    html=render_markdown(raw),
                )
            )
        current_title = None
        buffer = []

    for line in body.splitlines():
        fence = FENCE_RE.match(line.strip())
        if fence:
            in_code = not in_code
            buffer.append(line)
            continue

        if not in_code:
            section = SECTION_HEADING_RE.match(line)
            if section:
                flush()
                current_title = section.group(1).strip()
                buffer = []
                continue

            if NOTE_HEADING_RE.match(line.strip()):
                flush()
                current_title = "Note"
                buffer = []
                continue

        buffer.append(line)

    flush()
    return sections


def render_markdown(text: str) -> str:
    lines = text.splitlines()
    output: List[str] = []
    paragraph: List[str] = []
    list_items: List[str] = []
    in_code = False
    code_lang = ""
    code_lines: List[str] = []

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            joined = " ".join(part.strip()
                              for part in paragraph if part.strip())
            if joined:
                output.append(f"<p>{render_inline(joined)}</p>")
        paragraph = []

    def flush_list() -> None:
        nonlocal list_items
        if list_items:
            items = "".join(
                f"<li>{render_inline(item)}</li>" for item in list_items)
            output.append(f"<ul>{items}</ul>")
        list_items = []

    def flush_code() -> None:
        nonlocal code_lines, code_lang
        body = "\n".join(code_lines)
        if code_lang == "note":
            note_html = render_markdown(body)
            output.append(
                "<aside class=\"note-callout\">"
                "<div class=\"note-label\">Note</div>"
                f"{note_html}"
                "</aside>"
            )
        else:
            lang = f" language-{html.escape(code_lang, quote=True)}" if code_lang else ""
            output.append(
                f"<pre><code class=\"{lang.strip()}\">{html.escape(body)}</code></pre>")
        code_lines = []
        code_lang = ""

    for line in lines:
        fence = FENCE_RE.match(line.strip())
        if fence:
            if in_code:
                flush_code()
                in_code = False
            else:
                flush_paragraph()
                flush_list()
                in_code = True
                code_lang = fence.group(1).strip()
            continue

        if in_code:
            code_lines.append(line)
            continue

        stripped = line.strip()
        if not stripped:
            flush_paragraph()
            flush_list()
            continue

        bullet = LIST_ITEM_RE.match(line)
        if bullet:
            flush_paragraph()
            list_items.append(bullet.group(1).strip())
            continue

        if list_items and line.startswith("  "):
            list_items[-1] = f"{list_items[-1]} {stripped}"
            continue

        flush_list()
        paragraph.append(stripped)

    if in_code:
        flush_code()

    flush_paragraph()
    flush_list()
    return "".join(output)


def render_inline(text: str) -> str:
    escaped = html.escape(text)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        lambda match: (
            f'<a href="{html.escape(match.group(2), quote=True)}" '
            'rel="noreferrer noopener" target="_blank">'
            f"{match.group(1)}</a>"
        ),
        escaped,
    )
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", escaped)
    return escaped


def first_paragraph(text: str) -> str:
    for part in re.split(r"\n\s*\n", text.strip()):
        stripped = part.strip()
        if not stripped:
            continue
        stripped = re.sub(r"^-\s+", "", stripped, flags=re.M)
        stripped = re.sub(r"`([^`]+)`", r"\1", stripped)
        stripped = re.sub(r"\s+", " ", stripped)
        return stripped[:180] + ("..." if len(stripped) > 180 else "")
    return ""


def section_badges(labels: Sequence[str]) -> str:
    return "".join(f'<span class="tag">{html.escape(label)}</span>' for label in labels)


def extract_code_samples(card: Card) -> List[str]:
    samples: List[str] = []
    for section in card.sections:
        for match in CODE_FENCE_CAPTURE_RE.finditer(section.raw):
            language = match.group(1).strip().lower()
            if language == "note":
                continue
            if language not in {"", "cpp", "c++", "cc", "cxx", CPP_LANGUAGE, "cpp17", "cpp20"}:
                continue
            code = match.group(2).strip("\n")
            if code.strip():
                samples.append(code)
    return samples


def playground_payload(card: Card) -> Dict[str, object]:
    samples = extract_code_samples(card)
    return {
        "language": CPP_LANGUAGE,
        "defaultSource": samples[0] if samples else DEFAULT_CPP_TEMPLATE,
        "defaultTemplate": DEFAULT_CPP_TEMPLATE,
        "samples": samples,
    }


def notebook_payload(notebook: Notebook) -> Dict[str, object]:
    return {
        "slug": notebook.spec.slug,
        "title": notebook.spec.title,
        "description": notebook.spec.description,
        "totalCards": len(notebook.cards),
        "cards": [
            {
                "number": card.number,
                "title": card.title,
                "preview": card.preview,
                "labels": list(card.labels),
                "url": card_url(notebook, card),
            }
            for card in notebook.cards
        ],
    }


def boot_payload(notebooks: Sequence[Notebook], persistent_state: Optional[Dict[str, object]] = None) -> Dict[str, object]:
    return {
        "notebooks": [notebook_payload(notebook) for notebook in notebooks],
        "persistentState": persistent_state or {"saved_cards": [], "notebooks": {}, "notes": {}},
    }


def truncate_text(text: str, limit: int = MAX_CAPTURED_OUTPUT_CHARS) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "\n[output truncated]"


def compile_cpp_submission(source: str, stdin_data: str = "", language: str = CPP_LANGUAGE) -> Dict[str, object]:
    if language != CPP_LANGUAGE:
        return {
            "ok": False,
            "phase": "validation",
            "error": f"Unsupported language: {language}",
        }

    if len(source) > MAX_SOURCE_CHARS:
        return {
            "ok": False,
            "phase": "validation",
            "error": f"Source too large; limit is {MAX_SOURCE_CHARS} characters.",
        }

    with tempfile.TemporaryDirectory(prefix="flashcards_compile_") as tmpdir:
        tmp_path = Path(tmpdir)
        source_path = tmp_path / "main.cpp"
        executable_path = tmp_path / "main.out"
        source_path.write_text(source, encoding="utf-8")

        compile_cmd = [
            "g++",
            "-std=c++17",
            "-O0",
            "-pipe",
            "-Wall",
            "-Wextra",
            "-pedantic",
            str(source_path),
            "-o",
            str(executable_path),
        ]
        try:
            compile_proc = subprocess.run(
                compile_cmd,
                cwd=tmpdir,
                capture_output=True,
                text=True,
                timeout=COMPILE_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired as exc:
            return {
                "ok": False,
                "phase": "compile",
                "compiled": False,
                "compile_returncode": None,
                "compile_stdout": truncate_text(exc.stdout or ""),
                "compile_stderr": truncate_text((exc.stderr or "") + f"\nCompilation timed out after {COMPILE_TIMEOUT_SECONDS} seconds."),
                "run_returncode": None,
                "run_stdout": "",
                "run_stderr": "",
                "run_timed_out": False,
            }

        compile_stdout = truncate_text(compile_proc.stdout)
        compile_stderr = truncate_text(compile_proc.stderr)

        if compile_proc.returncode != 0:
            return {
                "ok": False,
                "phase": "compile",
                "compiled": False,
                "compile_returncode": compile_proc.returncode,
                "compile_stdout": compile_stdout,
                "compile_stderr": compile_stderr,
                "run_returncode": None,
                "run_stdout": "",
                "run_stderr": "",
                "run_timed_out": False,
            }

        run_proc = subprocess.Popen(
            [str(executable_path)],
            cwd=tmpdir,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
        try:
            run_stdout, run_stderr = run_proc.communicate(
                input=stdin_data, timeout=RUN_TIMEOUT_SECONDS)
            run_timed_out = False
        except subprocess.TimeoutExpired:
            run_timed_out = True
            try:
                os.killpg(run_proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            run_stdout, run_stderr = run_proc.communicate()

        run_stdout = truncate_text(run_stdout or "")
        run_stderr = truncate_text(run_stderr or "")
        run_returncode = run_proc.returncode
        if run_timed_out:
            run_stderr = (run_stderr + "\n" if run_stderr else "") + \
                f"Execution timed out after {RUN_TIMEOUT_SECONDS} seconds."

        return {
            "ok": (not run_timed_out) and run_returncode == 0,
            "phase": "run",
            "compiled": True,
            "compile_returncode": compile_proc.returncode,
            "compile_stdout": compile_stdout,
            "compile_stderr": compile_stderr,
            "run_returncode": run_returncode,
            "run_stdout": run_stdout,
            "run_stderr": run_stderr,
            "run_timed_out": run_timed_out,
        }


def safe_slug_path_component(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._") or "item"


def infer_attachment_extension(filename: str, mime_type: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg"}:
        return suffix
    guessed = mimetypes.guess_extension(mime_type or "")
    if guessed:
        return guessed
    return ".bin"


def decode_data_url(data_url: str) -> Tuple[bytes, str]:
    if not data_url.startswith("data:"):
        raise ValueError("Expected a data URL.")
    header, _, payload = data_url.partition(",")
    if ";base64" not in header:
        raise ValueError("Only base64 data URLs are supported.")
    mime_type = header[5:header.index(";base64")] or "application/octet-stream"
    return base64.b64decode(payload), mime_type


def note_attachment_dir(state_dir: Path, notebook_slug: str, card_id: str) -> Path:
    return state_dir / "note-attachments" / safe_slug_path_component(notebook_slug) / safe_slug_path_component(str(card_id))


def note_attachment_url(notebook_slug: str, card_id: str, filename: str) -> str:
    return f"/_attachments/{safe_slug_path_component(notebook_slug)}/{safe_slug_path_component(str(card_id))}/{filename}"


def save_note_attachment_file(state_dir: Path, notebook_slug: str, card_id: str, filename: str, data: bytes, mime_type: str) -> Dict[str, object]:
    if len(data) > MAX_NOTE_ATTACHMENT_BYTES:
        raise ValueError(
            f"Attachment too large; limit is {MAX_NOTE_ATTACHMENT_BYTES} bytes.")

    attachment_dir = note_attachment_dir(state_dir, notebook_slug, card_id)
    attachment_dir.mkdir(parents=True, exist_ok=True)
    attachment_id = uuid.uuid4().hex
    extension = infer_attachment_extension(filename, mime_type)
    stored_name = f"{attachment_id}{extension}"
    stored_path = attachment_dir / stored_name
    stored_path.write_bytes(data)
    return {
        "id": attachment_id,
        "filename": filename or stored_name,
        "url": note_attachment_url(notebook_slug, card_id, stored_name),
        "mimeType": mime_type or "application/octet-stream",
        "createdAt": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "size": len(data),
        "storedName": stored_name,
    }


def delete_note_attachment_file(state_dir: Path, notebook_slug: str, card_id: str, stored_name: str) -> None:
    attachment_path = note_attachment_dir(
        state_dir, notebook_slug, card_id) / stored_name
    try:
        attachment_path.unlink()
    except FileNotFoundError:
        pass


def attachment_url_to_stored_name(url: str) -> Optional[str]:
    parsed = urlparse(url)
    if not parsed.path.startswith("/_attachments/"):
        return None
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 4:
        return None
    return parts[-1]


def notebook_by_slug(notebooks: Sequence[Notebook], slug: str) -> Notebook:
    for notebook in notebooks:
        if notebook.spec.slug == slug:
            return notebook
    raise KeyError(slug)


def card_url(notebook: Notebook, card: Card) -> str:
    return f"/{notebook.spec.slug}/{card.number}"


def overview_url(notebook: Notebook) -> str:
    return f"/{notebook.spec.slug}"


def random_url(notebook: Notebook) -> str:
    return f"/{notebook.spec.slug}/random"


def render_page(title: str, body: str, extra_head: str = "", boot_data: Optional[Dict[str, object]] = None) -> str:
    boot_script = ""
    if boot_data is not None:
        boot_script = (
            '<script id="flashcards-data" type="application/json">'
            f"{html.escape(json.dumps(boot_data, ensure_ascii=False), quote=True)}"
            "</script>"
        )
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <link rel="stylesheet" href="/_static/app.css">
  {extra_head}
</head>
<body>
  {body}
  {boot_script}
  <script src="/_static/app.js" defer></script>
</body>
</html>"""


def render_home(notebooks: Sequence[Notebook], persistent_state: Optional[Dict[str, object]] = None) -> str:
    tiles = []
    card_lookup = {}
    for notebook in notebooks:
        card_count = len(notebook.cards)
        for card in notebook.cards:
            card_lookup[f"{notebook.spec.slug}:{card.number}"] = (notebook, card)
        tiles.append(
            f"""
            <a class="card-tile" href="{overview_url(notebook)}">
              <div class="card-meta">
                <span class="card-number">01</span>
                <span>{card_count} cards</span>
              </div>
              <h3>{html.escape(notebook.spec.title)}</h3>
              <p class="card-preview">{html.escape(notebook.spec.description)}</p>
              <div class="tag-row">
                <span class="tag">local notebook</span>
                <span class="tag">question first</span>
                <span class="tag">answer reveal</span>
              </div>
            </a>
            """
        )

    saved_entries = []
    saved_state_root = (persistent_state or {}).get("saved_cards", []) if persistent_state else []
    if isinstance(saved_state_root, list):
        for key in saved_state_root:
            pair = card_lookup.get(str(key))
            if pair is None:
                continue
            notebook, card = pair
            saved_entries.append(
                f"""
                <article class="card-tile saved-card" data-saved-card data-key="{html.escape(str(key), quote=True)}">
                  <div class="card-meta">
                    <span class="card-number">{card.number:02d}</span>
                    <span>{html.escape(notebook.spec.title)}</span>
                  </div>
                  <h3>{html.escape(card.title)}</h3>
                  <p class="card-preview">{html.escape(card.preview)}</p>
                  <div class="tag-row">
                    {section_badges(card.labels)}
                  </div>
                  <div class="reveal-actions">
                    <a class="button" href="{card_url(notebook, card)}">Open</a>
                    <button class="button-secondary" type="button" data-unsave-button data-key="{html.escape(str(key), quote=True)}">Remove</button>
                  </div>
                </article>
                """
            )

    note_entries = []
    note_state_root = (persistent_state or {}).get(
        "notes", {}) if persistent_state else {}
    if isinstance(note_state_root, dict):
        notebook_map = {notebook.spec.slug: notebook for notebook in notebooks}
        for notebook_slug, cards in note_state_root.items():
            notebook = notebook_map.get(notebook_slug)
            if notebook is None or not isinstance(cards, dict):
                continue
            for card_id, note_state in cards.items():
                if not isinstance(note_state, dict):
                    continue
                text = note_state.get("text", "")
                attachments = note_state.get("attachments", [])
                updated_at = note_state.get("updatedAt", "")
                if not isinstance(text, str):
                    text = ""
                if not isinstance(attachments, list):
                    attachments = []
                if not text.strip() and not attachments:
                    continue
                try:
                    card_number = int(card_id)
                except (TypeError, ValueError):
                    continue
                card = notebook.by_number.get(card_number)
                if card is None:
                    continue
                preview = first_paragraph(text) if text.strip(
                ) else f"{len(attachments)} attachment(s)"
                note_entries.append(
                    {
                        "updatedAt": updated_at if isinstance(updated_at, str) else "",
                        "html": f"""
                          <article class="card-tile note-card">
                            <div class="card-meta">
                              <span class="card-number">{card.number:02d}</span>
                              <span>{html.escape(notebook.spec.title)}</span>
                            </div>
                            <h3>{html.escape(card.title)}</h3>
                            <p class="card-preview">{html.escape(preview)}</p>
                            <div class="tag-row">
                              <span class="tag">note</span>
                              <span class="tag">{len(attachments)} attachments</span>
                            </div>
                            <div class="reveal-actions">
                              <a class="button" href="{card_url(notebook, card)}">Open note</a>
                            </div>
                          </article>
                        """,
                    }
                )

    note_entries.sort(key=lambda entry: entry.get(
        "updatedAt", ""), reverse=True)
    note_tiles = [entry["html"] for entry in note_entries[:12]]

    body = f"""
    <div class="app-shell" data-home-root data-notebook-root data-total-cards="{sum(len(n.cards) for n in notebooks)}">
      <section class="hero">
        <div>
          <p class="eyebrow">Flash card notebook</p>
          <h1>C++ 学习笔记卡片站</h1>
          <p class="lede">把原始 Markdown 按题拆开，先看问题，再按按钮展开答案。每个 notebook 都能快速跳题，首页还会集中展示你保存过的题目。</p>
        </div>
        <div class="hero-card">
          <div class="stat">{len(notebooks)}</div>
          <div class="stat-label">available notebooks</div>
        </div>
      </section>
      <div class="toolbar">
        <a class="button" href="{overview_url(notebooks[0])}">进入 beginner 卡片站</a>
        <span class="button-secondary">Markdown 是唯一内容源</span>
      </div>
      <section class="home-saved-shell">
        <div class="home-collection-head">
          <div class="card-meta">
            <span class="muted">Saved cards</span>
            <span class="muted"><strong data-saved-count>{len(saved_entries)}</strong> saved</span>
          </div>
          <div class="home-collection-actions">
            <button class="button-secondary" type="button" data-home-toggle="saved" data-home-collapsed>展开</button>
          </div>
        </div>
        <div class="home-collection-body" data-home-body="saved" hidden>
          <p class="saved-empty" data-saved-empty {'hidden' if saved_entries else ''}>你还没有保存任何题目。点开题目页里的 SAVE 就会出现在这里。</p>
          <div class="overview-grid saved-grid" data-saved-root>{''.join(saved_entries)}</div>
        </div>
      </section>
      <section class="home-saved-shell">
        <div class="home-collection-head">
          <div class="card-meta">
            <span class="muted">My Notes</span>
            <span class="muted">{len(note_tiles)} recent</span>
          </div>
          <div class="home-collection-actions">
            <button class="button-secondary" type="button" data-home-toggle="notes" data-home-collapsed>展开</button>
          </div>
        </div>
        <div class="home-collection-body" data-home-body="notes" hidden>
          <p class="saved-empty" {'hidden' if note_tiles else ''}>你的 note 还为空。打开题目页里的 note 区，输入文字或粘贴截图后会出现在这里。</p>
          <div class="overview-grid saved-grid">{''.join(note_tiles)}</div>
        </div>
      </section>
      <section class="overview-grid">
        {''.join(tiles)}
      </section>
      <p class="page-footer">本地启动后可以直接把这套页面当作练习工具使用，不需要数据库或登录。</p>
    </div>
    """
    return render_page("C++ 学习笔记卡片站", body, boot_data=boot_payload(notebooks, persistent_state))


def render_overview(notebook: Notebook, persistent_state: Optional[Dict[str, object]] = None) -> str:
    cards = []
    for card in notebook.cards:
        search_text = " ".join(
            [card.title, card.preview, " ".join(card.labels)])
        cards.append(
            f"""
            <a class="question-cell is-new" data-question-cell data-card-id="{card.number}" data-search-text="{html.escape(search_text, quote=True)}" href="{card_url(notebook, card)}" aria-label="{html.escape(card.title, quote=True)}" title="{html.escape(card.title, quote=True)}">
              {card.number:02d}
            </a>
            """
        )

    tiles = []
    for card in notebook.cards:
        search_text = " ".join(
            [card.title, card.preview, " ".join(card.labels)])
        tiles.append(
            f"""
            <a class="card-tile" data-card-tile data-search-text="{html.escape(search_text, quote=True)}" href="{card_url(notebook, card)}">
              <div class="card-meta">
                <span class="card-number">{card.number:02d}</span>
                <span>{len(card.sections)} sections</span>
              </div>
              <h3>{html.escape(card.title)}</h3>
              <p class="card-preview">{html.escape(card.preview)}</p>
              <div class="tag-row">{section_badges(card.labels)}</div>
            </a>
            """
        )

    body = f"""
    <div class="app-shell" data-notebook-root data-total-cards="{len(notebook.cards)}">
      <div class="breadcrumb">
        <a href="/">Home</a>
        <span> / </span>
        <span>{html.escape(notebook.spec.title)}</span>
      </div>
      <section class="hero">
        <div>
          <p class="eyebrow">Beginner notebook</p>
          <h1>{html.escape(notebook.spec.title)}</h1>
          <p class="lede">{html.escape(notebook.spec.description)}</p>
        </div>
        <div class="hero-card">
          <div class="stat">{len(notebook.cards)}</div>
          <div class="stat-label">cards in this notebook</div>
        </div>
      </section>

      <div class="progress-row">
        <div class="progress-track" aria-hidden="true">
          <div class="progress-fill" data-progress-fill></div>
        </div>
        <div class="progress-meta" data-progress-label>0 cards visited</div>
      </div>

      <div class="toolbar">
        <input class="search" data-card-search type="search" placeholder="搜索题目、关键词、section..." aria-label="Search cards">
        <a class="button" data-resume-button href="#" hidden>继续上次学习</a>
        <button class="button-secondary" data-clear-button type="button">清空搜索</button>
      </div>

      <div class="toolbar">
        <a class="button-secondary" href="{random_url(notebook)}">随机抽题</a>
        <span class="muted">当前显示 <strong data-visible-count>{len(notebook.cards)}</strong> 张卡片。</span>
      </div>

      <section class="panel flashcard" aria-label="Quick jump grid">
        <div class="card-meta">
          <span class="muted">Quick jump grid</span>
          <span class="muted"><span data-progress-label>0 visited</span> · <span data-today-label>0 today</span></span>
        </div>
        <div class="question-grid" data-overview-root data-notebook-slug="{html.escape(notebook.spec.slug, quote=True)}">
          {''.join(cards)}
        </div>
      </section>

      <section class="overview-grid" style="margin-top: 18px;">
        {''.join(tiles)}
      </section>

      <p class="page-footer">答案默认不在总览页展开，点进题目后再显示，减少“看答案”的摩擦。</p>
    </div>
    """
    return render_page(notebook.spec.title, body, boot_data=boot_payload([notebook], persistent_state))


def render_card_page(notebook: Notebook, card: Card, persistent_state: Optional[Dict[str, object]] = None) -> str:
    card_index = card.number - 1
    previous_card = notebook.cards[card_index - 1] if card_index > 0 else None
    next_card = notebook.cards[card_index +
                               1] if card_index + 1 < len(notebook.cards) else None
    playground_data = playground_payload(card)
    playground_data_json = html.escape(json.dumps(
        playground_data, ensure_ascii=False), quote=True)
    answer_sections = "".join(
        f"""
        <section class="answer-section{' is-english' if section.title.lower() == 'english explanation' else ''}">
          <div class="section-head">
            <h2>{html.escape(section.title)}</h2>
            {'<span class="tag">For English interviews</span>' if section.title.lower() == 'english explanation' else ''}
          </div>
          <div class="section-body">
            {section.html}
          </div>
        </section>
        """
        for section in card.sections
    )
    body = f"""
    <div class="app-shell" data-notebook-root data-total-cards="{len(notebook.cards)}">
      <div class="breadcrumb">
        <a href="/">Home</a>
        <span> / </span>
        <a href="{overview_url(notebook)}">{html.escape(notebook.spec.slug)}</a>
        <span> / </span>
        <span>#{card.number:02d}</span>
      </div>

      <section class="hero">
        <div>
          <p class="eyebrow">Flash card</p>
          <h2>{html.escape(notebook.spec.title)}</h2>
          <p class="lede">先看题目，再点“显示答案”。你也可以用上一题、下一题和随机题保持复习节奏。</p>
        </div>
        <div class="hero-card">
          <div class="stat">{card.number:02d}</div>
          <div class="stat-label">question {card.number} of {len(notebook.cards)}</div>
        </div>
      </section>

      <div class="card-workspace">
        <article class="panel flashcard card-main" data-card-root data-notebook-slug="{html.escape(notebook.spec.slug, quote=True)}" data-card-id="{card.number}" data-reveal-key="flashcards:{html.escape(notebook.spec.slug, quote=True)}:reveal:{card.number}">
          <div class="question-block">
            <div class="question-number">Question {card.number:02d}</div>
            <h1>{html.escape(card.title)}</h1>
            <p class="question-note">默认先隐藏答案，点按钮后展开。这个页面会记住你的学习进度。</p>
            <div class="answer-summary">{section_badges(card.labels)}</div>
            <div class="reveal-actions">
              <button class="button" type="button" data-reveal-button>显示答案</button>
              <button class="button-secondary" type="button" data-save-button>SAVE</button>
              <button class="button-secondary" type="button" data-playground-open>RUN C++</button>
              <button class="button-secondary" type="button" data-note-toggle>My Note</button>
              <a class="button-secondary" href="{overview_url(notebook)}">返回总览</a>
              <a class="button-secondary" href="{random_url(notebook)}" data-random-button data-target="{random_url(notebook)}">随机题</a>
            </div>
          </div>

          <div class="answer-wrap" data-answer-wrap hidden>
            {answer_sections}
          </div>

          <section class="note-panel" data-note-root data-notebook-slug="{html.escape(notebook.spec.slug, quote=True)}" data-card-id="{card.number}">
            <div class="note-panel-head">
              <div>
                <div class="note-title">My Note</div>
                <div class="note-subtitle">Paste text, screenshots, or images. `Ctrl+V` works when the editor is focused.</div>
              </div>
              <div class="note-head-actions">
                <span class="note-status" data-note-status>Draft</span>
                <span class="note-count"><strong data-note-count>0</strong> attachments</span>
                <button class="button-secondary" type="button" data-note-toggle>Open note</button>
              </div>
            </div>

            <div class="note-body" data-note-body hidden>
              <textarea class="note-editor" data-note-text spellcheck="false" placeholder="Write markdown notes here. Paste text or screenshots with Ctrl+V."></textarea>

              <div class="reveal-actions note-actions">
                <button class="button-secondary" type="button" data-note-clear>Clear note</button>
                <button class="button-secondary" type="button" data-note-collapse>Collapse</button>
              </div>

              <section class="note-preview-shell">
                <div class="note-section-head">Preview</div>
                <div class="note-preview" data-note-preview></div>
              </section>

              <section class="note-attachments-shell">
                <div class="note-section-head">Attachments</div>
                <div class="note-attachments" data-note-attachments></div>
              </section>
            </div>
          </section>

          <div class="reveal-actions">
            {'<a class="button-secondary" href="' + card_url(notebook, previous_card) + '">上一题</a>' if previous_card else '<span class="button-secondary" aria-disabled="true">上一题</span>'}
            {'<a class="button-secondary" href="' + card_url(notebook, next_card) + '">下一题</a>' if next_card else '<span class="button-secondary" aria-disabled="true">下一题</span>'}
            <a class="button-secondary" href="{random_url(notebook)}">换一题</a>
          </div>
        </article>

        <div class="playground-backdrop" data-playground-backdrop hidden></div>
        <aside
          class="playground-drawer"
          data-playground-root
          data-notebook-slug="{html.escape(notebook.spec.slug, quote=True)}"
          data-card-id="{card.number}"
          data-playground-key="flashcards:{html.escape(notebook.spec.slug, quote=True)}:{card.number}"
          data-playground-data="{playground_data_json}"
          aria-label="C++ playground"
          aria-hidden="true"
        >
          <div class="playground-shell">
            <div class="playground-head">
              <div>
                <div class="playground-title">Quick C++ Runner</div>
                <div class="playground-subtitle">Compiles locally with `g++ -std=c++17`.</div>
              </div>
              <button class="button-secondary" type="button" data-playground-close>Close</button>
            </div>

            <div class="playground-toolbar">
              <button class="button-secondary" type="button" data-playground-load-example>Load Example</button>
              <button class="button-secondary" type="button" data-playground-clear>Clear</button>
              <button class="button" type="button" data-playground-run>RUN</button>
            </div>

            <label class="playground-label" for="playground-source">Code</label>
            <textarea id="playground-source" class="playground-editor" data-playground-source spellcheck="false" autocomplete="off" autocapitalize="off" autocorrect="off"></textarea>

            <label class="playground-label" for="playground-stdin">stdin</label>
            <textarea id="playground-stdin" class="playground-stdin" data-playground-stdin spellcheck="false" autocomplete="off" autocapitalize="off" autocorrect="off" placeholder="Optional standard input"></textarea>

            <div class="playground-output-grid">
              <section class="playground-section">
                <div class="playground-section-head">Compile output</div>
                <pre class="playground-output" data-playground-compile-output>Waiting for code...</pre>
              </section>
              <section class="playground-section">
                <div class="playground-section-head">Runtime output</div>
                <pre class="playground-output" data-playground-runtime-output>RUN to see output.</pre>
              </section>
            </div>

            <div class="playground-status" data-playground-status>Closed</div>
          </div>
        </aside>
      </div>
    </div>
    """
    return render_page(f"{notebook.spec.title} - {card.title}", body, boot_data=boot_payload([notebook], persistent_state))


class FlashcardServer(BaseHTTPRequestHandler):
    notebooks: Tuple[Notebook, ...] = ()
    state_store: PersistentStateStore

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        sys.stderr.write("%s - - [%s] %s\n" % (self.address_string(),
                         self.log_date_time_string(), format % args))

    def do_GET(self) -> None:  # noqa: N802
        self.handle_request(send_body=True)

    def do_HEAD(self) -> None:  # noqa: N802
        self.handle_request(send_body=False)

    def do_POST(self) -> None:  # noqa: N802
        self.handle_post(send_body=True)

    def handle_request(self, send_body: bool) -> None:
        parsed = urlparse(self.path)
        route = parsed.path.rstrip("/") or "/"

        if route == "/":
            self.send_html(render_home(
                self.notebooks, self.state_store.snapshot()), send_body=send_body)
            return

        if route == "/_api/state":
            self.send_json(self.state_store.snapshot(), send_body=send_body)
            return

        if route in {"/_static/app.css", "/static/app.css"}:
            self.send_text(APP_CSS, "text/css; charset=utf-8",
                           send_body=send_body)
            return

        if route in {"/_static/app.js", "/static/app.js"}:
            self.send_text(
                APP_JS, "application/javascript; charset=utf-8", send_body=send_body)
            return

        if route.startswith("/_attachments/"):
            self.handle_attachment_request(route, send_body=send_body)
            return

        parts = [part for part in route.split("/") if part]
        if not parts:
            self.send_not_found(send_body=send_body)
            return

        slug = parts[0]
        try:
            notebook = notebook_by_slug(self.notebooks, slug)
        except KeyError:
            self.send_not_found(send_body=send_body)
            return

        if len(parts) == 1:
            self.send_html(render_overview(
                notebook, self.state_store.snapshot()), send_body=send_body)
            return

        if len(parts) == 2 and parts[1] == "random":
            self.send_redirect(
                card_url(notebook, random.choice(notebook.cards)))
            return

        if len(parts) == 2 and parts[1].isdigit():
            number = int(parts[1])
            card = notebook.by_number.get(number)
            if card is None:
                self.send_not_found(send_body=send_body)
                return
            self.send_html(render_card_page(
                notebook, card, self.state_store.snapshot()), send_body=send_body)
            return

        self.send_not_found(send_body=send_body)

    def handle_post(self, send_body: bool) -> None:
        parsed = urlparse(self.path)
        route = parsed.path.rstrip("/") or "/"

        if route == "/_api/compile":
            self.handle_compile(send_body=send_body)
            return

        if route == "/_api/state":
            self.handle_state_update(send_body=send_body)
            return

        if route == "/_api/note-attachment":
            self.handle_note_attachment_upload(send_body=send_body)
            return

        if route == "/_api/note-attachment-delete":
            self.handle_note_attachment_delete(send_body=send_body)
            return

        self.send_not_found(send_body=send_body)

    def handle_attachment_request(self, route: str, send_body: bool) -> None:
        parts = [part for part in route.split("/") if part]
        if len(parts) != 4:
            self.send_not_found(send_body=send_body)
            return

        notebook_slug = parts[1]
        card_id = parts[2]
        filename = parts[3]
        attachment_path = note_attachment_dir(
            self.state_store.state_dir, notebook_slug, card_id) / filename
        if not attachment_path.exists():
            self.send_not_found(send_body=send_body)
            return

        mime_type = mimetypes.guess_type(attachment_path.name)[
            0] or "application/octet-stream"
        self.send_file(attachment_path, mime_type, send_body=send_body)

    def handle_state_update(self, send_body: bool) -> None:
        content_length = int(self.headers.get("Content-Length", "0") or "0")
        raw_body = self.rfile.read(
            content_length) if content_length > 0 else b""
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            self.send_json(
                {"ok": False, "error": "Invalid JSON payload."}, status=400, send_body=send_body)
            return

        kind = payload.get("kind")
        if kind == "saved_cards":
            saved_cards = payload.get("savedCards", [])
            if not isinstance(saved_cards, list):
                self.send_json(
                    {"ok": False, "error": "savedCards must be a list."}, status=400, send_body=send_body)
                return
            saved_cards = [str(entry) for entry in saved_cards]
            self.state_store.save_saved_cards(saved_cards)
            self.send_json(
                {"ok": True, "savedCards": saved_cards}, send_body=send_body)
            return

        if kind == "notebook":
            notebook_slug = payload.get("notebookSlug", "")
            state = payload.get("state", {})
            if not isinstance(notebook_slug, str) or not notebook_slug:
                self.send_json(
                    {"ok": False, "error": "notebookSlug must be a string."}, status=400, send_body=send_body)
                return
            if not isinstance(state, dict):
                self.send_json(
                    {"ok": False, "error": "state must be an object."}, status=400, send_body=send_body)
                return
            self.state_store.save_notebook_state(notebook_slug, state)
            self.send_json(
                {"ok": True, "notebookSlug": notebook_slug}, send_body=send_body)
            return

        if kind == "note":
            notebook_slug = payload.get("notebookSlug", "")
            card_id = payload.get("cardId", "")
            note_state = payload.get("noteState", {})
            if not isinstance(notebook_slug, str) or not notebook_slug:
                self.send_json(
                    {"ok": False, "error": "notebookSlug must be a string."}, status=400, send_body=send_body)
                return
            if not isinstance(card_id, str) or not card_id:
                self.send_json(
                    {"ok": False, "error": "cardId must be a string."}, status=400, send_body=send_body)
                return
            if not isinstance(note_state, dict):
                self.send_json(
                    {"ok": False, "error": "noteState must be an object."}, status=400, send_body=send_body)
                return
            self.state_store.save_note_state(
                notebook_slug, card_id, note_state)
            self.send_json({"ok": True, "notebookSlug": notebook_slug,
                           "cardId": card_id}, send_body=send_body)
            return

        self.send_json({"ok": False, "error": "Unsupported state update kind."},
                       status=400, send_body=send_body)

    def handle_note_attachment_upload(self, send_body: bool) -> None:
        content_length = int(self.headers.get("Content-Length", "0") or "0")
        raw_body = self.rfile.read(
            content_length) if content_length > 0 else b""
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            self.send_json(
                {"ok": False, "error": "Invalid JSON payload."}, status=400, send_body=send_body)
            return

        notebook_slug = payload.get("notebookSlug", "")
        card_id = payload.get("cardId", "")
        filename = payload.get("filename", "")
        data_url = payload.get("dataUrl", "")
        if not isinstance(notebook_slug, str) or not notebook_slug:
            self.send_json(
                {"ok": False, "error": "notebookSlug must be a string."}, status=400, send_body=send_body)
            return
        if not isinstance(card_id, str) or not card_id:
            self.send_json(
                {"ok": False, "error": "cardId must be a string."}, status=400, send_body=send_body)
            return
        if not isinstance(filename, str) or not isinstance(data_url, str):
            self.send_json(
                {"ok": False, "error": "filename and dataUrl must be strings."}, status=400, send_body=send_body)
            return

        try:
            data, mime_type = decode_data_url(data_url)
            attachment = save_note_attachment_file(
                self.state_store.state_dir, notebook_slug, card_id, filename, data, mime_type)
        except (ValueError, OSError) as exc:
            self.send_json({"ok": False, "error": str(exc)},
                           status=400, send_body=send_body)
            return

        self.send_json({"ok": True, "attachment": attachment},
                       send_body=send_body)

    def handle_note_attachment_delete(self, send_body: bool) -> None:
        content_length = int(self.headers.get("Content-Length", "0") or "0")
        raw_body = self.rfile.read(
            content_length) if content_length > 0 else b""
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            self.send_json(
                {"ok": False, "error": "Invalid JSON payload."}, status=400, send_body=send_body)
            return

        notebook_slug = payload.get("notebookSlug", "")
        card_id = payload.get("cardId", "")
        attachment_url = payload.get("attachmentUrl", "")
        if not isinstance(notebook_slug, str) or not notebook_slug:
            self.send_json(
                {"ok": False, "error": "notebookSlug must be a string."}, status=400, send_body=send_body)
            return
        if not isinstance(card_id, str) or not card_id:
            self.send_json(
                {"ok": False, "error": "cardId must be a string."}, status=400, send_body=send_body)
            return
        if not isinstance(attachment_url, str) or not attachment_url:
            self.send_json(
                {"ok": False, "error": "attachmentUrl must be a string."}, status=400, send_body=send_body)
            return

        stored_name = attachment_url_to_stored_name(attachment_url)
        if not stored_name:
            self.send_json(
                {"ok": False, "error": "Invalid attachment URL."}, status=400, send_body=send_body)
            return

        delete_note_attachment_file(
            self.state_store.state_dir, notebook_slug, card_id, stored_name)
        self.send_json({"ok": True}, send_body=send_body)

    def handle_compile(self, send_body: bool) -> None:
        content_length = int(self.headers.get("Content-Length", "0") or "0")
        raw_body = self.rfile.read(
            content_length) if content_length > 0 else b""
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            self.send_json(
                {"ok": False, "error": "Invalid JSON payload."}, status=400, send_body=send_body)
            return

        source = payload.get("source", "")
        stdin_data = payload.get("stdin", "")
        language = payload.get("language", CPP_LANGUAGE)

        if not isinstance(source, str) or not isinstance(stdin_data, str) or not isinstance(language, str):
            self.send_json(
                {"ok": False, "error": "source, stdin and language must be strings."}, status=400, send_body=send_body)
            return

        notebook_slug = payload.get("notebook_slug", "")
        card_id = payload.get("card_id", "")
        if notebook_slug or card_id:
            sys.stderr.write(
                f"[compile] notebook={notebook_slug!r} card={card_id!r}\n")

        result = compile_cpp_submission(
            source=source, stdin_data=stdin_data, language=language)
        self.send_json(result, status=200, send_body=send_body)

    def send_html(self, content: str, status: int = 200, send_body: bool = True) -> None:
        payload = content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        if send_body:
            self.wfile.write(payload)

    def send_json(self, data: Dict[str, object], status: int = 200, send_body: bool = True) -> None:
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        if send_body:
            self.wfile.write(payload)

    def send_text(self, content: str, content_type: str, status: int = 200, send_body: bool = True) -> None:
        payload = content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        if send_body:
            self.wfile.write(payload)

    def send_file(self, path: Path, content_type: str, status: int = 200, send_body: bool = True) -> None:
        payload = path.read_bytes()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        if send_body:
            self.wfile.write(payload)

    def send_redirect(self, location: str, status: int = 302) -> None:
        self.send_response(status)
        self.send_header("Location", location)
        self.end_headers()

    def send_not_found(self, send_body: bool = True) -> None:
        self.send_html(
            render_page(
                "Not found", '<div class="app-shell"><p>Page not found.</p></div>'),
            status=404,
            send_body=send_body,
        )


def build_notebooks() -> Tuple[Notebook, ...]:
    return notebook_index()


def check_notebooks(notebooks: Sequence[Notebook]) -> None:
    for notebook in notebooks:
        if not notebook.cards:
            raise RuntimeError(
                f"No cards found in {notebook.spec.source_path}")
        first = notebook.cards[0]
        last = notebook.cards[-1]
        if first.number != 1:
            raise RuntimeError(
                f"{notebook.spec.slug}: expected first card to be #1, got #{first.number}")
        if last.number < first.number:
            raise RuntimeError(f"{notebook.spec.slug}: invalid card ordering")


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Serve the C++ flash card notebook locally.")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to.")
    parser.add_argument("--port", default=8000, type=int,
                        help="Port to bind to.")
    parser.add_argument("--no-browser", action="store_true",
                        help="Do not open a browser window.")
    parser.add_argument("--check", action="store_true",
                        help="Validate the notebook and exit.")
    args = parser.parse_args(argv)

    notebooks = build_notebooks()
    check_notebooks(notebooks)

    if args.check:
        for notebook in notebooks:
            print(f"{notebook.spec.slug}: {len(notebook.cards)} cards")
        return 0

    FlashcardServer.notebooks = notebooks
    FlashcardServer.state_store = PersistentStateStore(DEFAULT_STATE_DIR)
    server = ThreadingHTTPServer((args.host, args.port), FlashcardServer)
    url = f"http://{args.host}:{args.port}/"
    print(f"Serving flash cards at {url}")
    if not args.no_browser:
        # webbrowser.open(url) --- IGNORE ---
        pass

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
