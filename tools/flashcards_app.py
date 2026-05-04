from __future__ import annotations

import base64
import argparse
import html
import json
import os
import mimetypes
import random
import re
import signal
import shutil
import sys
import subprocess
import threading
import uuid
import struct
import zlib
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


@dataclass(frozen=True)
class CodeFile:
    relative_path: str
    language: str
    content: str


@dataclass(frozen=True)
class CodeProject:
    number: int
    slug: str
    title: str
    root_path: Path
    files: Tuple[CodeFile, ...]


NOTEBOOKS: Tuple[NotebookSpec, ...] = (
    NotebookSpec(
        slug="beginner",
        title="C++ 面试笔记：初级篇",
        source_path=ROOT / "docs" / "zh" / "beginner.md",
        description="覆盖语法基础、面向对象、STL、智能指针和并发入门题。",
    ),
    NotebookSpec(
        slug="intermediate",
        title="C++ 面试笔记：中级篇",
        source_path=ROOT / "docs" / "zh" / "intermediate.md",
        description="聚焦资源管理、移动语义、模板、异常安全和常见工程取舍。",
    ),
    NotebookSpec(
        slug="advanced",
        title="C++ 面试笔记：高级篇",
        source_path=ROOT / "docs" / "zh" / "advanced.md",
        description="深入完美转发、内存模型、SFINAE、对象模型和现代 C++ 设计。",
    ),
    NotebookSpec(
        slug="coding-round",
        title="手写代码题",
        source_path=ROOT / "docs" / "zh" / "coding-round.md",
        description="训练常见手写实现、边界条件分析和代码表达能力。",
    ),
    NotebookSpec(
        slug="code-examples",
        title="C++ Code Examples：知识点代码库",
        source_path=ROOT / "docs" / "zh" / "code-examples.md",
        description="用可运行代码复习 C++ 高频知识点、常见坑和工程写法。",
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
    NotebookSpec(
        slug="cpp-awesome-cheatsheet",
        title="C++ Awesome Project Cheatsheet",
        source_path=ROOT / "cpp_awssome_project" / "NOTE-Cheatsheet.md",
        description="整理 CMake、CTest、类语法、lambda 捕获和 ThreadSafeQueue 的速查内容。",
    ),
    NotebookSpec(
        slug="cpp-awesome-notes",
        title="C++ Awesome Project Notes",
        source_path=ROOT / "cpp_awssome_project" / "NOTE.md",
        description="记录 lambda 捕获、CMake target 配置、移动语义和 const/mutable 的深入解释。",
    ),
)

NOTE_READER_SLUGS = {"cpp-awesome-cheatsheet", "cpp-awesome-notes"}
CODE_READING_SLUG = "code-reading"
CPP_LAB_SLUG = "cpp-lab"
CODE_PROJECT_ROOT = ROOT / "cpp_awssome_project"
CPP_LAB_ROOT = CODE_PROJECT_ROOT / "random_pj"
CPP_LAB_MAIN_FILE = "random_code.cpp"
CODE_PROJECT_FILE_NAMES = {"CMakeLists.txt"}
CODE_PROJECT_EXTENSIONS = {".cpp", ".cc", ".cxx", ".hpp", ".hh", ".h", ".hxx"}
CPP_LAB_FILE_NAMES = {"CMakeLists.txt"}
CPP_LAB_EXTENSIONS = {
    ".cpp",
    ".cc",
    ".cxx",
    ".h",
    ".hpp",
    ".hh",
    ".hxx",
    ".txt",
    ".md",
}
CPP_LAB_SOURCE_EXTENSIONS = {".cpp", ".cc", ".cxx"}
CODE_PROJECT_EXCLUDED_DIRS = {
    ".git",
    "__pycache__",
    "build",
    "cmake-build-debug",
    "cmake-build-release",
    "CMakeFiles",
    "Testing",
    "json",
    "thirdparty",
    "third_party",
    "vendor",
    "docs",
}
CARD_HEADING_RE = re.compile(r"^##\s+(\d+)\.\s+(.+?)\s*$", re.M)
GENERIC_CARD_HEADING_RE = re.compile(r"^##\s+(.+?)\s*$", re.M)
SECTION_HEADING_RE = re.compile(r"^###\s+(.+?)\s*$")
NOTE_HEADING_RE = re.compile(r"^Note:?\s*$")
FENCE_RE = re.compile(r"^```([A-Za-z0-9_+-]*)\s*$")
LIST_ITEM_RE = re.compile(r"^\s*-\s+(.*)$")
ORDERED_LIST_ITEM_RE = re.compile(r"^\s*\d+\.\s+(.*)$")
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
RESOURCE_TIME_BIN = shutil.which("time") or "/usr/bin/time"
RESOURCE_TIME_FORMAT = "\n".join(
    [
        "wall_seconds=%e",
        "user_seconds=%U",
        "sys_seconds=%S",
        "cpu_percent=%P",
        "max_rss_kb=%M",
        "minor_page_faults=%R",
        "major_page_faults=%F",
        "voluntary_context_switches=%w",
        "involuntary_context_switches=%c",
    ]
)
DEFAULT_STATE_DIR = Path(os.environ.get("FLASHCARDS_STATE_DIR", ROOT / "data"))
STATE_FILE_NAME = "flashcards-state.json"
PWA_THEME_COLOR = "#0f766e"
PWA_APP_NAME = "C++ 学习笔记卡片站"
PWA_SHORT_NAME = "C++ 卡片站"
PWA_ICON_180_PATH = "/_static/pwa-icon-180.png"
PWA_ICON_512_PATH = "/_static/pwa-icon-512.png"
PWA_MANIFEST_PATH = "/manifest.webmanifest"
PWA_SERVICE_WORKER_PATH = "/_static/sw.js"


def _png_chunk(kind: bytes, payload: bytes) -> bytes:
    crc = zlib.crc32(kind + payload) & 0xFFFFFFFF
    return struct.pack("!I", len(payload)) + kind + payload + struct.pack("!I", crc)


def _draw_line(buffer: bytearray, size: int, x0: int, y0: int, x1: int, y1: int, rgba:
               Tuple[int, int, int, int]) -> None:
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    while True:
        if 0 <= x0 < size and 0 <= y0 < size:
            index = (y0 * size + x0) * 4
            buffer[index:index + 4] = bytes(rgba)
        if x0 == x1 and y0 == y1:
            break
        twice = 2 * err
        if twice >= dy:
            err += dy
            x0 += sx
        if twice <= dx:
            err += dx
            y0 += sy


def _fill_rect(
    buffer: bytearray,
    size: int,
    x0: int,
    y0: int,
    x1: int,
    y1: int,
    rgba: Tuple[int, int, int, int],
) -> None:
    for y in range(max(0, y0), min(size, y1)):
        row = y * size
        for x in range(max(0, x0), min(size, x1)):
            index = (row + x) * 4
            buffer[index:index + 4] = bytes(rgba)


def _fill_circle(
    buffer: bytearray,
    size: int,
    cx: float,
    cy: float,
    radius: float,
    rgba: Tuple[int, int, int, int],
) -> None:
    radius_sq = radius * radius
    x0 = max(0, int(cx - radius))
    x1 = min(size, int(cx + radius) + 1)
    y0 = max(0, int(cy - radius))
    y1 = min(size, int(cy + radius) + 1)
    for y in range(y0, y1):
        for x in range(x0, x1):
            dx = x - cx
            dy = y - cy
            if dx * dx + dy * dy <= radius_sq:
                index = (y * size + x) * 4
                buffer[index:index + 4] = bytes(rgba)


def build_pwa_icon_png(size: int) -> bytes:
    if size <= 0:
        raise ValueError("Icon size must be positive.")

    buffer = bytearray(size * size * 4)
    bg = (15, 118, 110, 255)
    cream = (250, 247, 239, 255)
    white = (255, 255, 255, 255)
    accent = (180, 83, 9, 255)

    for y in range(size):
        row = y * size
        for x in range(size):
            index = (row + x) * 4
            buffer[index:index + 4] = bytes(bg)

    _fill_circle(buffer, size, size * 0.5, size * 0.5, size * 0.28, cream)

    left = int(size * 0.31)
    right = int(size * 0.69)
    top = int(size * 0.34)
    bottom = int(size * 0.66)
    notch = max(2, size // 32)

    _draw_line(buffer, size, left, top, left - notch, size // 2, white)
    _draw_line(buffer, size, left - notch, size // 2, left, bottom, white)
    _draw_line(buffer, size, right, top, right + notch, size // 2, white)
    _draw_line(buffer, size, right + notch, size // 2, right, bottom, white)

    plus_w = max(4, size // 24)
    plus_h = max(4, size // 24)
    cx = size // 2
    cy = size // 2
    _fill_rect(buffer, size, cx - plus_w, cy - plus_h *
               3, cx + plus_w, cy + plus_h * 3, accent)
    _fill_rect(buffer, size, cx - plus_h * 3, cy - plus_w,
               cx + plus_h * 3, cy + plus_w, accent)

    raw = bytearray()
    raw.extend(b"\x89PNG\r\n\x1a\n")
    ihdr = struct.pack("!IIBBBBB", size, size, 8, 6, 0, 0, 0)
    raw.extend(_png_chunk(b"IHDR", ihdr))
    scanlines = bytearray()
    stride = size * 4
    for y in range(size):
        scanlines.append(0)
        start = y * stride
        scanlines.extend(buffer[start:start + stride])
    raw.extend(_png_chunk(b"IDAT", zlib.compress(bytes(scanlines), level=9)))
    raw.extend(_png_chunk(b"IEND", b""))
    return bytes(raw)


PWA_ICON_180_PNG = build_pwa_icon_png(180)
PWA_ICON_512_PNG = build_pwa_icon_png(512)
PWA_MANIFEST = {
    "name": PWA_APP_NAME,
    "short_name": PWA_SHORT_NAME,
    "start_url": "/",
    "scope": "/",
    "display": "standalone",
    "background_color": PWA_THEME_COLOR,
    "theme_color": PWA_THEME_COLOR,
    "icons": [
        {
            "src": PWA_ICON_180_PATH,
            "sizes": "180x180",
            "type": "image/png",
            "purpose": "any maskable",
        },
        {
            "src": PWA_ICON_512_PATH,
            "sizes": "512x512",
            "type": "image/png",
            "purpose": "any maskable",
        },
    ],
}


def build_service_worker_js() -> str:
    precache = [
        "/",
        "/_static/app.css",
        "/_static/app.js",
        PWA_MANIFEST_PATH,
        PWA_ICON_180_PATH,
        PWA_ICON_512_PATH,
    ]
    precache_json = json.dumps(precache, ensure_ascii=False)
    return f"""
const CACHE_NAME = 'flashcards-pwa-v1';
const PRECACHE_URLS = {precache_json};

self.addEventListener('install', (event) => {{
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(PRECACHE_URLS))
  );
  self.skipWaiting();
}});

self.addEventListener('activate', (event) => {{
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(
      keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
    ))
  );
  self.clients.claim();
}});

self.addEventListener('fetch', (event) => {{
  const {{ request }} = event;
  if (request.method !== 'GET') {{
    return;
  }}

  const url = new URL(request.url);
  if (request.mode === 'navigate') {{
    event.respondWith(
      fetch(request)
        .then((response) => {{
          const copy = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
          return response;
        }})
        .catch(() => caches.match(request).then((cached) => cached || caches.match('/')))
    );
    return;
  }}

  if (url.origin === self.location.origin) {{
    event.respondWith(
      caches.match(request).then((cached) => {{
        if (cached) {{
          return cached;
        }}
        return fetch(request).then((response) => {{
          if (response.ok) {{
            const copy = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
          }}
          return response;
        }});
      }})
    );
  }}
}});
""".strip()


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
            "home_notes": {},
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
        home_notes = data.get("home_notes", {})
        if not isinstance(saved_cards, list):
            saved_cards = []
        if not isinstance(notebooks, dict):
            notebooks = {}
        if not isinstance(notes, dict):
            notes = {}
        if not isinstance(home_notes, dict):
            home_notes = {}
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
            "home_notes": {
                str(note_id): self._normalize_home_note_state(str(note_id), note_state)
                for note_id, note_state in home_notes.items()
                if isinstance(note_state, dict)
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
            filename = attachment.get("filename", "")
            url = attachment.get("url", "")
            mime_type = attachment.get("mimeType", "")
            created_at = attachment.get("createdAt", "")
            size_value = attachment.get("size", 0)
            normalized_attachments.append(
                {
                    "id": attachment_id,
                    "filename": filename if isinstance(filename, str) else "",
                    "url": url if isinstance(url, str) else "",
                    "mimeType": mime_type if isinstance(mime_type, str) else "",
                    "createdAt": created_at if isinstance(created_at, str) else "",
                    "size": int(size_value) if isinstance(size_value, int) else 0,
                    "storedName": attachment.get("storedName", "") if isinstance(attachment.get("storedName", ""), str) else "",
                }
            )
        return {
            "text": text,
            "attachments": normalized_attachments,
            "updatedAt": updated_at,
        }

    @staticmethod
    def _normalize_home_note_state(note_id: str, state: Dict[str, object]) -> Dict[str, object]:
        normalized = PersistentStateStore._normalize_note_state(state)
        title = state.get("title", "")
        if not isinstance(title, str):
            title = ""
        created_at = state.get("createdAt", "")
        if not isinstance(created_at, str):
            created_at = ""
        note_type = state.get("type", "text")
        if not isinstance(note_type, str) or note_type not in {"text", "cpp"}:
            note_type = "text"
        return {
            "id": note_id,
            "type": note_type,
            "title": title,
            "text": normalized["text"],
            "attachments": normalized["attachments"],
            "createdAt": created_at,
            "updatedAt": normalized["updatedAt"],
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

    def save_home_note_state(self, note_id: str, note_state: Dict[str, object]) -> None:
        with self._lock:
            home_notes = self._state.setdefault("home_notes", {})
            if not isinstance(home_notes, dict):
                home_notes = {}
                self._state["home_notes"] = home_notes
            home_notes[str(note_id)] = self._normalize_home_note_state(
                str(note_id), note_state)
            self._persist()

    def delete_home_note_state(self, note_id: str) -> None:
        with self._lock:
            home_notes = self._state.setdefault("home_notes", {})
            if isinstance(home_notes, dict):
                home_notes.pop(str(note_id), None)
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

.card-tile-full {
  grid-column: span 12;
  min-height: 0;
}

.card-tile-full:hover {
  transform: none;
}

.overview-card-body {
  display: grid;
  gap: 14px;
  max-height: none;
  color: var(--ink);
}

.overview-card-body .answer-section {
  border-radius: 8px;
  background: rgba(255, 250, 243, 0.62);
}

.overview-card-body .section-head {
  padding: 10px 12px;
}

.overview-card-body .section-body {
  padding: 12px;
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

.overview-with-jump,
.card-with-jump,
.reader-layout {
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr);
  gap: 18px;
  align-items: start;
}

.jump-sidebar,
.reader-sidebar {
  position: sticky;
  top: 16px;
  max-height: calc(100vh - 32px);
  overflow: auto;
  padding: 16px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: rgba(255, 250, 243, 0.9);
  box-shadow: 0 12px 28px rgba(73, 51, 30, 0.09);
}

.jump-sidebar-title,
.reader-sidebar-title {
  margin: 0 0 12px;
  color: var(--muted);
  font-size: 13px;
  font-weight: 800;
}

.jump-sidebar .question-grid {
  grid-template-columns: repeat(auto-fill, minmax(38px, 1fr));
  gap: 8px;
}

.jump-sidebar .question-cell {
  border-radius: 10px;
  font-size: 12px;
}

.reader-toc {
  display: grid;
  gap: 6px;
}

.reader-toc a {
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr);
  gap: 8px;
  align-items: start;
  padding: 8px;
  border-radius: 8px;
  color: var(--ink);
}

.reader-toc a:hover {
  background: rgba(15, 118, 110, 0.08);
}

.reader-toc-number {
  color: var(--accent);
  font-weight: 800;
  font-size: 12px;
}

.reader-toc-title {
  overflow-wrap: anywhere;
  font-size: 13px;
  line-height: 1.35;
}

.reader-content {
  display: grid;
  gap: 18px;
}

.code-project-grid {
  display: grid;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  gap: 16px;
}

.code-project-card {
  grid-column: span 6;
}

.code-file-layout {
  display: grid;
  grid-template-columns: 300px minmax(0, 1fr);
  gap: 18px;
  align-items: start;
}

.code-file-sidebar {
  position: sticky;
  top: 16px;
  max-height: calc(100vh - 32px);
  overflow: auto;
  padding: 16px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: rgba(255, 250, 243, 0.92);
  box-shadow: 0 12px 28px rgba(73, 51, 30, 0.09);
}

.code-file-tree {
  display: grid;
  gap: 6px;
}

.code-file-tree a {
  display: block;
  padding: 8px 10px;
  border-radius: 8px;
  color: var(--ink);
  font-family: var(--font-mono);
  font-size: 12px;
  line-height: 1.35;
  overflow-wrap: anywhere;
}

.code-file-tree a:hover {
  background: rgba(15, 118, 110, 0.08);
}

.code-file-list {
  display: grid;
  gap: 18px;
  min-width: 0;
}

.code-file-card {
  overflow: hidden;
}

.code-file-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  padding: 14px 18px;
  border-bottom: 1px solid rgba(81, 67, 57, 0.12);
  background: rgba(15, 118, 110, 0.06);
}

.code-file-title {
  margin: 0;
  font-family: var(--font-mono);
  font-size: 0.95rem;
  overflow-wrap: anywhere;
}

.code-reading-pre {
  overflow: auto;
  margin: 0;
  padding: 18px;
  background: #1e1e1e;
  color: #d4d4d4;
  font-family: var(--font-mono);
  font-size: 13px;
  line-height: 1.62;
  tab-size: 2;
}

.code-reading-pre code {
  font-family: inherit;
}

.code-token-comment {
  color: #6a9955;
}

.code-token-string {
  color: #ce9178;
}

.code-token-preprocessor {
  color: #c586c0;
}

.code-token-keyword {
  color: #569cd6;
}

.code-token-type {
  color: #4ec9b0;
}

.code-token-number {
  color: #b5cea8;
}

.code-token-function {
  color: #dcdcaa;
}

.code-token-member {
  color: #9cdcfe;
}

.code-token-namespace {
  color: #4ec9b0;
}

.cpp-lab-shell {
  display: grid;
  gap: 14px;
}

.app-shell[data-cpp-lab-root] {
  max-width: none;
  width: 100%;
  padding: 12px clamp(10px, 1.5vw, 24px) 18px;
}

.app-shell[data-cpp-lab-root] .hero {
  margin: 8px 0 12px;
}

.app-shell[data-cpp-lab-root] .hero h1 {
  font-size: clamp(1.7rem, 2vw, 2.4rem);
}

.app-shell[data-cpp-lab-root] .lede {
  margin-top: 8px;
}

.app-shell[data-cpp-lab-root] .top-nav {
  margin: 10px 0 12px;
}

.cpp-lab-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  justify-content: space-between;
  padding: 12px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: rgba(255, 250, 243, 0.68);
}

.cpp-lab-file-select {
  min-height: 40px;
  min-width: min(100%, 320px);
  border: 1px solid rgba(81, 67, 57, 0.16);
  border-radius: 8px;
  padding: 0 12px;
  background: #fffdf8;
  color: var(--ink);
  font: inherit;
  font-family: var(--font-mono);
  font-size: 13px;
}

.cpp-lab-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.cpp-lab-shortcuts {
  color: var(--muted);
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 700;
}

.cpp-lab-status {
  min-height: 20px;
  color: var(--muted);
  font-size: 13px;
  font-weight: 700;
}

.cpp-lab-layout {
  display: grid;
  grid-template-columns: minmax(0, 2fr) minmax(320px, 1fr);
  min-height: calc(100vh - 210px);
  border: 1px solid var(--line);
  border-radius: 8px;
  overflow: visible;
  background: #fffdf8;
  align-items: start;
}

.cpp-lab-pane {
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  background: #f8fafc;
}

.cpp-lab-pane + .cpp-lab-pane {
  border-left: 1px solid var(--line);
}

.cpp-lab-pane[data-cpp-lab-editor-pane] {
  min-height: calc(100vh - 210px);
}

.cpp-lab-pane[data-cpp-lab-output-pane] {
  position: sticky;
  top: 12px;
  height: calc(100vh - 24px);
  max-height: calc(100vh - 24px);
}

.cpp-lab-pane.is-dark {
  background: #111827;
  color: #e5e7eb;
}

.cpp-lab-pane-head {
  display: flex;
  gap: 10px;
  justify-content: space-between;
  align-items: center;
  min-height: 48px;
  padding: 8px 12px;
  border-bottom: 1px solid rgba(81, 67, 57, 0.12);
  background: rgba(255, 255, 255, 0.58);
}

.cpp-lab-pane.is-dark .cpp-lab-pane-head {
  border-bottom-color: rgba(229, 231, 235, 0.16);
  background: rgba(15, 23, 42, 0.86);
}

.cpp-lab-title {
  font-size: 13px;
  font-weight: 800;
  color: var(--muted);
}

.cpp-lab-pane.is-dark .cpp-lab-title {
  color: #cbd5e1;
}

.cpp-lab-editor-wrap {
  position: relative;
  flex: 1 1 auto;
  min-height: 0;
  overflow: hidden;
}

.cpp-lab-editor-mount {
  width: 100%;
  height: 100%;
  min-height: 100%;
  background: #dbeafe;
  color: #111827;
  font-family: var(--font-mono);
  font-size: 14px;
  line-height: 1.6;
}

.cpp-lab-editor-mount .cm-editor {
  height: 100%;
  min-height: 100%;
  background: #dbeafe;
  color: #111827;
  font-family: var(--font-mono);
  font-size: 14px;
  line-height: 1.6;
}

.cpp-lab-editor-mount .cm-scroller {
  font-family: var(--font-mono);
  line-height: 1.6;
}

.cpp-lab-pane.is-dark .cpp-lab-editor-mount,
.cpp-lab-pane.is-dark .cpp-lab-editor-mount .cm-editor {
  background: #1e1e1e;
  color: #d4d4d4;
}

.cpp-lab-editor-error {
  padding: 16px;
  color: #b91c1c;
  font-family: var(--font-mono);
  font-size: 13px;
  white-space: pre-wrap;
}

.cpp-lab-pane.is-dark .cpp-lab-editor-error {
  color: #fca5a5;
}

.cpp-lab-output {
  flex: 1 1 auto;
  min-height: 0;
  max-height: none;
  margin: 0;
  padding: 16px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
  background: #f8fafc;
  color: #111827;
  font-family: var(--font-mono);
  font-size: 14px;
  line-height: 1.6;
}

.cpp-lab-pane.is-dark .cpp-lab-output {
  background: #0f172a;
  color: #e5e7eb;
}

.cpp-lab-output.is-error {
  color: #b91c1c;
}

.cpp-lab-pane.is-dark .cpp-lab-output.is-error {
  color: #fca5a5;
}

.cpp-lab-bracket-match {
  border-radius: 4px;
  background: rgba(250, 204, 21, 0.38);
  box-shadow: 0 0 0 1px rgba(180, 83, 9, 0.55) inset;
  color: inherit;
}

.cpp-lab-pane.is-dark .cpp-lab-bracket-match {
  background: rgba(250, 204, 21, 0.26);
  box-shadow: 0 0 0 1px rgba(250, 204, 21, 0.72) inset;
}

.reader-article {
  scroll-margin-top: 18px;
}

.reader-article .question-block {
  border-radius: 8px;
}

.reader-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 16px;
}

.overview-grid-main {
  min-width: 0;
}

.home-saved-shell {
  margin-top: 24px;
}

.home-quick-shell {
  margin-top: 24px;
  padding: 18px;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: rgba(255, 250, 243, 0.44);
}

.home-note-shell {
  margin: 24px 0;
  padding: 18px;
  border: 1px solid rgba(15, 118, 110, 0.16);
  border-radius: 8px;
  background: rgba(255, 250, 243, 0.64);
  box-shadow: 0 12px 28px rgba(73, 51, 30, 0.08);
}

.home-note-composer {
  display: grid;
  gap: 14px;
  margin-top: 16px;
}

.home-note-title {
  width: 100%;
  border: 1px solid rgba(81, 67, 57, 0.16);
  border-radius: 8px;
  padding: 13px 14px;
  background: #fffdf8;
  color: var(--ink);
  font: inherit;
  font-weight: 700;
}

.home-note-title:focus,
.home-note-editor:focus {
  outline: 2px solid rgba(15, 118, 110, 0.3);
  outline-offset: 2px;
}

.note-type-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}

.note-type-option {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 38px;
  padding: 8px 12px;
  border: 1px solid rgba(81, 67, 57, 0.14);
  border-radius: 8px;
  background: #fffdf8;
  font-weight: 800;
  cursor: pointer;
}

.note-type-option input {
  margin: 0;
  accent-color: var(--accent);
}

.home-note-editor.is-code {
  min-height: clamp(420px, 58vh, 760px);
  max-height: 78vh;
  background: #151311;
  color: #f6f3ef;
  resize: vertical;
  tab-size: 2;
}

.home-note-card .card-number {
  width: 40px;
  height: 40px;
  background: rgba(180, 83, 9, 0.12);
  color: var(--accent-2);
}

.top-nav {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin: 18px 0 24px;
  padding: 10px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: rgba(255, 250, 243, 0.64);
}

.top-nav-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 40px;
  padding: 9px 13px;
  border: 1px solid rgba(81, 67, 57, 0.12);
  border-radius: 8px;
  background: rgba(255, 253, 248, 0.82);
  color: var(--ink);
  font-weight: 800;
  font-size: 13px;
}

.top-nav-link:hover,
.top-nav-link.is-active {
  color: #fff;
  border-color: rgba(15, 118, 110, 0.35);
  background: var(--accent);
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

.quick-grid {
  margin-top: 16px;
}

.quick-card {
  grid-column: span 3;
  min-height: 160px;
  padding: 18px;
  background: linear-gradient(180deg, rgba(255, 250, 243, 0.98), rgba(248, 242, 233, 0.9));
  position: relative;
  overflow: hidden;
}

.quick-card::before {
  content: "";
  position: absolute;
  inset: 0 auto auto 0;
  width: 100%;
  height: 5px;
  background: linear-gradient(90deg, rgba(15, 118, 110, 0.9), rgba(180, 83, 9, 0.68));
}

.quick-card h3 {
  font-size: 1.03rem;
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
  width: min(calc(100vw - 32px), max(66vw, 900px));
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

.playground-runner-layout {
  flex: 1 1 auto;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(0, 3fr) minmax(320px, 2fr);
  gap: 14px;
}

.playground-runner-code,
.playground-runner-side {
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.playground-runner-code .playground-editor {
  min-height: 0;
  flex: 1 1 auto;
}

.playground-runner-side .playground-stdin {
  min-height: 120px;
  flex: 0 0 18%;
}

.playground-runner-side .playground-output-grid {
  flex: 1 1 auto;
  min-height: 0;
  display: grid;
  grid-template-columns: 1fr;
  grid-template-rows: repeat(2, minmax(0, 1fr));
}

.playground-runner-side .playground-section {
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.playground-runner-side .playground-output {
  flex: 1 1 auto;
  min-height: 0;
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

.answer-section ol {
  margin: 0.25rem 0 0.95rem;
  padding-left: 1.45rem;
}

.answer-section li + li {
  margin-top: 0.45rem;
}

.answer-section h3,
.answer-section h4,
.answer-section h5,
.answer-section h6 {
  margin: 1.1rem 0 0.45rem;
  line-height: 1.35;
  color: var(--ink);
}

.answer-section h3 {
  font-size: 1rem;
}

.answer-section h4,
.answer-section h5,
.answer-section h6 {
  font-size: 0.94rem;
}

.answer-section blockquote {
  margin: 0.8rem 0;
  padding: 0.75rem 1rem;
  border-left: 4px solid rgba(15, 118, 110, 0.38);
  background: rgba(15, 118, 110, 0.06);
  color: var(--muted);
}

.answer-section blockquote p:last-child {
  margin-bottom: 0;
}

.answer-section hr {
  border: 0;
  border-top: 1px solid var(--line);
  margin: 1.1rem 0;
}

.table-wrap {
  width: 100%;
  overflow-x: auto;
  margin: 0.9rem 0;
}

.answer-section table {
  width: 100%;
  min-width: 520px;
  border-collapse: collapse;
  font-size: 0.92rem;
  line-height: 1.45;
}

.answer-section th,
.answer-section td {
  padding: 0.65rem 0.75rem;
  border: 1px solid rgba(81, 67, 57, 0.16);
  vertical-align: top;
  text-align: left;
}

.answer-section th {
  background: rgba(15, 118, 110, 0.08);
  color: var(--accent);
  font-weight: 800;
}

.answer-section tr:nth-child(even) td {
  background: rgba(255, 255, 255, 0.34);
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
  border-radius: 8px;
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

.note-summary {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
  color: var(--muted);
  font-size: 13px;
}

.note-summary strong {
  color: var(--ink);
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
  min-height: 150px;
  border: 1px solid rgba(81, 67, 57, 0.16);
  border-radius: 8px;
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
  border-radius: 8px;
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

.note-code {
  overflow: auto;
  margin: 10px 0;
  padding: 14px;
  border-radius: 8px;
  background: #151311;
  color: #f6f3ef;
  font-family: var(--font-mono);
  font-size: 13px;
  line-height: 1.55;
  white-space: pre;
}

.note-code code {
  font-family: inherit;
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

  .quick-card {
    grid-column: span 12;
  }

  .overview-with-jump,
  .card-with-jump,
  .reader-layout,
  .code-file-layout,
  .cpp-lab-layout {
    grid-template-columns: 1fr;
  }

  .cpp-lab-layout {
    min-height: 0;
  }

  .cpp-lab-pane {
    min-height: 52vh;
  }

  .cpp-lab-pane[data-cpp-lab-output-pane] {
    position: static;
    height: 42vh;
    max-height: 42vh;
  }

  .cpp-lab-pane + .cpp-lab-pane {
    border-left: 0;
    border-top: 1px solid var(--line);
  }

  .jump-sidebar,
  .reader-sidebar,
  .code-file-sidebar {
    position: static;
    max-height: none;
  }

  .code-project-card {
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

  .playground-drawer {
    width: 100vw;
    height: 88vh;
  }

  .playground-drawer[data-note-runner-root] .playground-editor {
    min-height: 44vh;
  }

  .playground-runner-layout {
    grid-template-columns: 1fr;
    grid-template-rows: minmax(44vh, 1fr) auto;
  }

  .playground-runner-side .playground-output-grid {
    grid-template-rows: none;
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

function firstTextLine(value) {
  return String(value || '')
    .split(/\\r?\\n/)
    .map((line) => line.trim())
    .find((line) => line && !line.startsWith('```')) || '';
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
    return { notebooks: [], persistentState: { saved_cards: [], notebooks: {}, notes: {}, home_notes: {} } };
  }

  return safeJsonParse(node.textContent || node.innerText || '{}', {
    notebooks: [],
    persistentState: { saved_cards: [], notebooks: {}, notes: {}, home_notes: {} },
  }) || { notebooks: [], persistentState: { saved_cards: [], notebooks: {}, notes: {}, home_notes: {} } };
}

function getBootPersistentState() {
  const boot = getBootData();
  const persistentState = boot.persistentState || {};
  return {
    saved_cards: Array.isArray(persistentState.saved_cards) ? persistentState.saved_cards : [],
    notebooks:
      persistentState.notebooks && typeof persistentState.notebooks === 'object'
        ? persistentState.notebooks
        : {},
    notes:
      persistentState.notes && typeof persistentState.notes === 'object'
        ? persistentState.notes
        : {},
    home_notes:
      persistentState.home_notes && typeof persistentState.home_notes === 'object'
        ? persistentState.home_notes
        : {},
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
  Object.entries(persistentState.home_notes || {}).forEach(([noteId, noteState]) => {
    localStorage.setItem(getStoreKey(`home-note:${noteId}`), JSON.stringify(noteState));
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
  const homeNotes = snapshot.home_notes && typeof snapshot.home_notes === 'object' ? snapshot.home_notes : {};

  localStorage.setItem(getStoreKey('saved'), JSON.stringify(savedCards));

  Object.keys(localStorage).forEach((key) => {
    if (
      !key.startsWith(getStoreKey('notebook:'))
      && !key.startsWith(getStoreKey('note:'))
      && !key.startsWith(getStoreKey('home-note:'))
    ) {
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

  Object.entries(homeNotes).forEach(([noteId, noteState]) => {
    localStorage.setItem(getStoreKey(`home-note:${noteId}`), JSON.stringify(noteState));
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

function normalizeAttachment(entry) {
  return {
    id: entry && typeof entry.id === 'string' ? entry.id : '',
    filename: entry && typeof entry.filename === 'string' ? entry.filename : '',
    url: entry && typeof entry.url === 'string' ? entry.url : '',
    mimeType: entry && typeof entry.mimeType === 'string' ? entry.mimeType : '',
    createdAt: entry && typeof entry.createdAt === 'string' ? entry.createdAt : '',
    size: entry && Number.isInteger(entry.size) ? entry.size : 0,
    storedName: entry && typeof entry.storedName === 'string' ? entry.storedName : '',
  };
}

function normalizeHomeNote(noteId, state) {
  const fallbackId = noteId || (window.crypto && window.crypto.randomUUID ? window.crypto.randomUUID() : String(Date.now()));
  const note = state && typeof state === 'object' ? state : {};
  const id = typeof note.id === 'string' && note.id ? note.id : fallbackId;
  return {
    id,
    type: note.type === 'cpp' ? 'cpp' : 'text',
    title: typeof note.title === 'string' ? note.title : '',
    text: typeof note.text === 'string' ? note.text : '',
    attachments: Array.isArray(note.attachments)
      ? note.attachments.map(normalizeAttachment).filter((entry) => entry.id && entry.url)
      : [],
    createdAt: typeof note.createdAt === 'string' ? note.createdAt : '',
    updatedAt: typeof note.updatedAt === 'string' ? note.updatedAt : '',
  };
}

function getHomeNotes() {
  return Object.keys(localStorage)
    .filter((key) => key.startsWith(getStoreKey('home-note:')))
    .map((key) => normalizeHomeNote(key.slice(getStoreKey('home-note:').length), safeJsonParse(localStorage.getItem(key), null)))
    .filter((note) => note.id)
    .sort((left, right) => (right.updatedAt || right.createdAt || '').localeCompare(left.updatedAt || left.createdAt || ''));
}

function saveHomeNoteState(note) {
  const normalized = normalizeHomeNote(note.id, note);
  localStorage.setItem(getStoreKey(`home-note:${normalized.id}`), JSON.stringify(normalized));
  syncPersistentState('home_note', { noteId: normalized.id, noteState: normalized });
  return normalized;
}

function deleteHomeNoteState(noteId) {
  localStorage.removeItem(getStoreKey(`home-note:${noteId}`));
  syncPersistentState('home_note_delete', { noteId });
}

function formatMetricSeconds(value) {
  return typeof value === 'number' && Number.isFinite(value) ? `${value.toFixed(3)} s` : 'n/a';
}

function formatMetricInteger(value) {
  return typeof value === 'number' && Number.isFinite(value) ? String(value) : 'n/a';
}

function formatMetricMemory(kb) {
  if (typeof kb !== 'number' || !Number.isFinite(kb)) {
    return 'n/a';
  }
  if (kb >= 1024 * 1024) {
    return `${(kb / 1024 / 1024).toFixed(2)} GB`;
  }
  if (kb >= 1024) {
    return `${(kb / 1024).toFixed(2)} MB`;
  }
  return `${kb} KB`;
}

function formatResourceMetrics(title, metrics) {
  if (!metrics || !metrics.available) {
    return `${title}: resource metrics unavailable`;
  }
  const cpu = typeof metrics.cpu_percent === 'number' && Number.isFinite(metrics.cpu_percent)
    ? `${metrics.cpu_percent.toFixed(1)}%`
    : 'n/a';
  return [
    `${title}:`,
    `  elapsed wall time : ${formatMetricSeconds(metrics.wall_seconds)}`,
    `  CPU time          : user ${formatMetricSeconds(metrics.user_seconds)} + sys ${formatMetricSeconds(metrics.sys_seconds)}`,
    `  CPU utilization   : ${cpu}`,
    `  peak memory RSS   : ${formatMetricMemory(metrics.max_rss_kb)}`,
    `  page faults       : minor ${formatMetricInteger(metrics.minor_page_faults)}, major ${formatMetricInteger(metrics.major_page_faults)}`,
    `  context switches  : voluntary ${formatMetricInteger(metrics.voluntary_context_switches)}, involuntary ${formatMetricInteger(metrics.involuntary_context_switches)}`,
  ].join('\\n');
}

function compileResultParts(result) {
  const compileParts = [];
  if (result && result.compile_stdout) {
    compileParts.push(result.compile_stdout);
  }
  if (result && result.compile_stderr) {
    compileParts.push(result.compile_stderr);
  }
  if (result && !compileParts.length && result.phase === 'validation' && result.error) {
    compileParts.push(result.error);
  }
  if (result && !compileParts.length && result.phase === 'compile') {
    compileParts.push('Compilation finished without diagnostics.');
  }
  if (result && result.compile_metrics) {
    compileParts.push('', '[compile resource usage]', formatResourceMetrics('Compile', result.compile_metrics));
  }

  const runtimeParts = [];
  if (result && result.run_stdout) {
    runtimeParts.push(result.run_stdout);
  }
  if (result && result.run_stderr) {
    runtimeParts.push(result.run_stderr);
  }
  if (result && result.phase === 'compile') {
    runtimeParts.push('Program was not executed because compilation failed.');
  } else if (result && result.phase === 'validation' && result.error) {
    runtimeParts.push('Program was not executed.');
  } else if (result && !runtimeParts.length && result.ok) {
    runtimeParts.push('Program finished without output.');
  }
  if (result && result.run_metrics && result.phase === 'run') {
    runtimeParts.push('', '[run resource usage]', formatResourceMetrics('Run', result.run_metrics));
  }

  let status = 'Waiting for code...';
  if (result) {
    if (result.phase === 'validation' && result.error) {
      status = result.error;
    } else if (result.phase === 'compile') {
      status = 'Compilation failed.';
    } else if (result.run_timed_out) {
      status = 'Runtime timed out.';
    } else if (result.ok) {
      status = `Done. Exit code ${result.run_returncode}.`;
    } else {
      status = `Runtime finished with exit code ${result.run_returncode}.`;
    }
  }

  return {
    compile: compileParts.join('\\n').trim() || 'Compilation succeeded.',
    runtime: runtimeParts.join('\\n').trim() || 'No runtime output.',
    status,
  };
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
  const data = safeJsonParse(
    root.dataset.playgroundData || '{}',
    { samples: [], defaultSource: '', defaultTemplate: '', language: 'cpp17' },
  ) || {};
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

    const parts = compileResultParts(result);
    if (compileOutput) {
      compileOutput.textContent = parts.compile;
    }
    if (runtimeOutput) {
      runtimeOutput.textContent = parts.runtime;
    }
    if (statusLabel) {
      statusLabel.textContent = parts.status;
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

const CPP_LAB_KEYWORDS = new Set([
  'alignas', 'alignof', 'asm', 'auto', 'break', 'case', 'catch', 'class', 'concept',
  'const', 'consteval', 'constexpr', 'constinit', 'continue', 'co_await', 'co_return',
  'co_yield', 'decltype', 'default', 'delete', 'do', 'else', 'enum', 'explicit',
  'export', 'extern', 'final', 'for', 'friend', 'goto', 'if', 'inline', 'mutable',
  'namespace', 'new', 'noexcept', 'operator', 'override', 'private', 'protected',
  'public', 'requires', 'return', 'sizeof', 'static', 'static_assert', 'struct',
  'switch', 'template', 'this', 'thread_local', 'throw', 'try', 'typedef', 'typename',
  'using', 'virtual', 'volatile', 'while',
]);

const CPP_LAB_TYPES = new Set([
  'bool', 'char', 'char8_t', 'char16_t', 'char32_t', 'double', 'float', 'int', 'long',
  'short', 'signed', 'unsigned', 'void', 'wchar_t', 'size_t', 'std', 'string', 'vector',
  'queue', 'mutex', 'thread', 'atomic', 'unique_ptr', 'shared_ptr', 'weak_ptr',
]);

function cppLabFindBracketPair(source, index) {
  const openToClose = { '(': ')', '[': ']', '{': '}', '<': '>' };
  const closeToOpen = { ')': '(', ']': '[', '}': '{', '>': '<' };
  let cursor = index;
  if (!openToClose[source[cursor]] && !closeToOpen[source[cursor]] && cursor > 0) {
    cursor -= 1;
  }
  const char = source[cursor];
  if (openToClose[char]) {
    const close = openToClose[char];
    let depth = 0;
    for (let i = cursor; i < source.length; i += 1) {
      if (source[i] === char) {
        depth += 1;
      } else if (source[i] === close) {
        depth -= 1;
        if (depth === 0) {
          return { open: cursor, close: i };
        }
      }
    }
  }
  if (closeToOpen[char]) {
    const open = closeToOpen[char];
    let depth = 0;
    for (let i = cursor; i >= 0; i -= 1) {
      if (source[i] === char) {
        depth += 1;
      } else if (source[i] === open) {
        depth -= 1;
        if (depth === 0) {
          return { open: i, close: cursor };
        }
      }
    }
  }
  return null;
}

function cppLabAppendHighlightedRange(output, source, start, end, tokenClass, bracketPair) {
  if (start >= end) {
    return;
  }
  if (tokenClass) {
    output.push(`<span class="${tokenClass}">`);
  }
  for (let index = start; index < end; index += 1) {
    const escaped = escapeHtml(source[index]);
    if (bracketPair && (index === bracketPair.open || index === bracketPair.close)) {
      output.push(`<span class="cpp-lab-bracket-match">${escaped}</span>`);
    } else {
      output.push(escaped);
    }
  }
  if (tokenClass) {
    output.push('</span>');
  }
}

function cppLabTokenClass(source, match) {
  const value = match[0];
  if (value.startsWith('//') || value.startsWith('/*')) {
    return 'code-token-comment';
  }
  if (value.startsWith('"') || value.startsWith("'")) {
    return 'code-token-string';
  }
  if (value.trimStart().startsWith('#')) {
    return 'code-token-preprocessor';
  }
  if (/^\\d/.test(value)) {
    return 'code-token-number';
  }
  if (CPP_LAB_KEYWORDS.has(value)) {
    return 'code-token-keyword';
  }
  if (CPP_LAB_TYPES.has(value)) {
    return 'code-token-type';
  }
  const previous = source.slice(Math.max(0, match.index - 2), match.index);
  if (previous === '::') {
    return 'code-token-member';
  }
  const after = source.slice(match.index + value.length);
  if (/^\\s*\\(/.test(after)) {
    return 'code-token-function';
  }
  return '';
}

function cppLabHighlightSource(source, bracketPair) {
  const tokenRe = /\\/\\/[^\\n]*|\\/\\*[\\s\\S]*?\\*\\/|"(?:\\\\.|[^"\\\\])*"|'(?:\\\\.|[^'\\\\])*'|^\\s*#[^\\n]*|\\b\\d+(?:\\.\\d+)?\\b|\\b[A-Za-z_]\\w*\\b/gm;
  const output = [];
  let cursor = 0;
  let match = tokenRe.exec(source);
  while (match) {
    cppLabAppendHighlightedRange(output, source, cursor, match.index, '', bracketPair);
    cppLabAppendHighlightedRange(
      output,
      source,
      match.index,
      match.index + match[0].length,
      cppLabTokenClass(source, match),
      bracketPair,
    );
    cursor = match.index + match[0].length;
    match = tokenRe.exec(source);
  }
  cppLabAppendHighlightedRange(output, source, cursor, source.length, '', bracketPair);
  return output.join('');
}

function bindCppLab() {
  const root = document.querySelector('[data-cpp-lab-root]');
  if (!root) {
    return;
  }

  const fileSelect = root.querySelector('[data-cpp-lab-file-select]');
  const editor = root.querySelector('[data-cpp-lab-editor]');
  const highlight = root.querySelector('[data-cpp-lab-highlight]');
  const output = root.querySelector('[data-cpp-lab-output]');
  const status = root.querySelector('[data-cpp-lab-status]');
  const saveButton = root.querySelector('[data-cpp-lab-save]');
  const runButton = root.querySelector('[data-cpp-lab-run]');
  const clearButton = root.querySelector('[data-cpp-lab-clear]');
  const editorPane = root.querySelector('[data-cpp-lab-editor-pane]');
  const outputPane = root.querySelector('[data-cpp-lab-output-pane]');
  const editorThemeButton = root.querySelector('[data-cpp-lab-editor-theme]');
  const outputThemeButton = root.querySelector('[data-cpp-lab-output-theme]');
  const dirtyFiles = {};
  let activePath = fileSelect ? fileSelect.value : '';
  let loading = false;
  let bracketPair = null;

  const setStatus = (message) => {
    if (status) {
      status.textContent = message;
    }
  };

  const setHighlight = (value) => {
    if (highlight) {
      highlight.innerHTML = value || cppLabHighlightSource(editor ? editor.value : '', bracketPair);
    }
  };

  const refreshHighlight = () => {
    setHighlight(cppLabHighlightSource(editor ? editor.value : '', bracketPair));
    syncScroll();
  };

  const setBracketPairFromIndex = (index) => {
    bracketPair = cppLabFindBracketPair(editor ? editor.value : '', index);
    refreshHighlight();
  };

  const editorCharWidth = () => {
    if (!editor) {
      return 8;
    }
    const styles = window.getComputedStyle(editor);
    const probe = document.createElement('span');
    probe.textContent = 'M';
    probe.style.position = 'absolute';
    probe.style.visibility = 'hidden';
    probe.style.fontFamily = styles.fontFamily;
    probe.style.fontSize = styles.fontSize;
    probe.style.fontWeight = styles.fontWeight;
    document.body.appendChild(probe);
    const width = probe.getBoundingClientRect().width || 8;
    probe.remove();
    return width;
  };

  const editorIndexFromMouse = (event) => {
    if (!editor) {
      return 0;
    }
    const styles = window.getComputedStyle(editor);
    const rect = editor.getBoundingClientRect();
    const lineHeight = parseFloat(styles.lineHeight) || 22;
    const paddingLeft = parseFloat(styles.paddingLeft) || 0;
    const paddingTop = parseFloat(styles.paddingTop) || 0;
    const x = event.clientX - rect.left - paddingLeft + editor.scrollLeft;
    const y = event.clientY - rect.top - paddingTop + editor.scrollTop;
    const line = Math.max(0, Math.floor(y / lineHeight));
    const column = Math.max(0, Math.floor(x / editorCharWidth()));
    const source = editor.value || '';
    const lines = source.split('\\n');
    let index = 0;
    for (let i = 0; i < Math.min(line, lines.length); i += 1) {
      index += lines[i].length + 1;
    }
    return Math.min(source.length, index + Math.min(column, (lines[line] || '').length));
  };

  const syncScroll = () => {
    if (!editor || !highlight) {
      return;
    }
    highlight.scrollTop = editor.scrollTop;
    highlight.scrollLeft = editor.scrollLeft;
  };

  const setTheme = (pane, button, storageKey, dark) => {
    if (pane) {
      pane.classList.toggle('is-dark', dark);
    }
    if (button) {
      button.textContent = dark ? 'Light' : 'Dark';
      button.setAttribute('aria-pressed', dark ? 'true' : 'false');
    }
    localStorage.setItem(getStoreKey(storageKey), dark ? 'dark' : 'light');
  };

  setTheme(
    editorPane,
    editorThemeButton,
    'cpp-lab:editor-theme',
    localStorage.getItem(getStoreKey('cpp-lab:editor-theme')) === 'dark',
  );
  setTheme(
    outputPane,
    outputThemeButton,
    'cpp-lab:output-theme',
    localStorage.getItem(getStoreKey('cpp-lab:output-theme')) === 'dark',
  );

  const markDirty = (path, dirty) => {
    if (!path) {
      return;
    }
    if (dirty) {
      dirtyFiles[path] = editor ? editor.value : '';
    } else {
      delete dirtyFiles[path];
    }
    const dirtyCount = Object.keys(dirtyFiles).length;
    setStatus(dirtyCount ? `${dirtyCount} unsaved file(s).` : 'Saved.');
  };

  const loadFile = async (path) => {
    if (!path || !editor) {
      return;
    }
    loading = true;
    activePath = path;
    setStatus(`Loading ${path}...`);
    try {
      const response = await fetch(`/_api/cpp-lab/file?path=${encodeURIComponent(path)}`);
      const result = await response.json();
      if (!response.ok || !result.ok) {
        throw new Error(result.error || 'Failed to load file.');
      }
      editor.value = result.content || '';
      bracketPair = null;
      refreshHighlight();
      markDirty(path, false);
      setStatus(`Loaded ${path}.`);
      syncScroll();
    } catch (error) {
      setStatus(error && error.message ? error.message : 'Failed to load file.');
    } finally {
      loading = false;
    }
  };

  const saveFile = async (path, content) => {
    const response = await fetch('/_api/cpp-lab/file', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path, content }),
    });
    const result = await response.json();
    if (!response.ok || !result.ok) {
      throw new Error(result.error || 'Failed to save file.');
    }
    if (path === activePath) {
      refreshHighlight();
    }
    markDirty(path, false);
    return result;
  };

  const outputResult = (result) => {
    const parts = compileResultParts(result);
    const lines = [];
    if (result.phase === 'compile') {
      lines.push(parts.compile);
    } else if (result.phase === 'validation' && result.error) {
      lines.push(result.error);
    } else {
      if (parts.runtime) {
        lines.push(parts.runtime);
      }
      if (result.compile_stderr || result.compile_stdout || result.compile_metrics) {
        lines.push('', '[compile diagnostics]', parts.compile);
      }
    }
    lines.push('', result.ok ? '=== Code Execution Successful ===' : `=== ${parts.status} ===`);
    if (output) {
      output.textContent = lines.join('\\n').trim();
      output.classList.toggle('is-error', !result.ok);
    }
    setStatus(parts.status);
  };

  if (fileSelect) {
    fileSelect.addEventListener('change', () => {
      loadFile(fileSelect.value);
    });
  }

  if (editor) {
    const applyEditorEdit = (start, end, value, nextStart, nextEnd) => {
      const source = editor.value || '';
      editor.value = source.slice(0, start) + value + source.slice(end);
      const cursorStart = nextStart === undefined ? start + value.length : nextStart;
      const cursorEnd = nextEnd === undefined ? cursorStart : nextEnd;
      editor.selectionStart = cursorStart;
      editor.selectionEnd = cursorEnd;
      bracketPair = cppLabFindBracketPair(editor.value, editor.selectionStart || 0);
      refreshHighlight();
      markDirty(activePath, true);
    };

    const lineStartAt = (source, index) => source.lastIndexOf('\\n', Math.max(0, index - 1)) + 1;

    const lineEndAt = (source, index) => {
      const nextNewline = source.indexOf('\\n', index);
      return nextNewline === -1 ? source.length : nextNewline;
    };

    const leadingIndent = (line) => {
      const match = String(line || '').match(/^[ \\t]*/);
      return match ? match[0] : '';
    };

    const currentLineBounds = () => {
      const source = editor.value || '';
      const start = editor.selectionStart || 0;
      return {
        source,
        start: lineStartAt(source, start),
        end: lineEndAt(source, start),
      };
    };

    const selectedLineBounds = () => {
      const source = editor.value || '';
      const start = editor.selectionStart || 0;
      const end = editor.selectionEnd || 0;
      const lineStart = lineStartAt(source, start);
      const adjustedEnd = end > start && source[end - 1] === '\\n' ? end - 1 : end;
      return {
        source,
        start,
        end,
        lineStart,
        lineEnd: lineEndAt(source, adjustedEnd),
      };
    };

    const indentSelection = () => {
      const start = editor.selectionStart || 0;
      const end = editor.selectionEnd || 0;
      const source = editor.value || '';
      if (start === end) {
        applyEditorEdit(start, end, '  ');
        return;
      }
      const lineStart = lineStartAt(source, start);
      const selected = source.slice(lineStart, end);
      const indented = selected.replace(/^/gm, '  ');
      applyEditorEdit(lineStart, end, indented, start + 2, end + (indented.length - selected.length));
    };

    const unindentSelection = () => {
      const start = editor.selectionStart || 0;
      const end = editor.selectionEnd || 0;
      const source = editor.value || '';
      const lineStart = lineStartAt(source, start);
      const selected = source.slice(lineStart, end);
      let removedBeforeStart = 0;
      let removedTotal = 0;
      const unindented = selected.replace(/^( {1,2}|\t)/gm, (match, indent, offset) => {
        const removed = indent.length;
        removedTotal += removed;
        if (lineStart + offset < start) {
          removedBeforeStart += removed;
        }
        return '';
      });
      const nextStart = Math.max(lineStart, start - removedBeforeStart);
      const nextEnd = Math.max(nextStart, end - removedTotal);
      applyEditorEdit(lineStart, end, unindented, nextStart, nextEnd);
    };

    const smartEnter = () => {
      const start = editor.selectionStart || 0;
      const end = editor.selectionEnd || 0;
      const source = editor.value || '';
      const lineStart = lineStartAt(source, start);
      const beforeCursor = source.slice(lineStart, start);
      let indent = leadingIndent(beforeCursor);
      if (/[{([:]\\s*$/.test(beforeCursor)) {
        indent += '  ';
      }
      const insert = `\\n${indent}`;
      const nextCursor = start + 1 + indent.length;
      applyEditorEdit(start, end, insert, nextCursor, nextCursor);
    };

    const nearestBlockIndent = () => {
      const source = editor.value || '';
      const cursor = editor.selectionStart || 0;
      let depth = 0;
      for (let index = cursor - 1; index >= 0; index -= 1) {
        const char = source[index];
        if (char === '}') {
          depth += 1;
        } else if (char === '{') {
          if (depth === 0) {
            const blockLineStart = lineStartAt(source, index);
            return leadingIndent(source.slice(blockLineStart, index));
          }
          depth -= 1;
        }
      }
      return '';
    };

    const smartClosingBrace = () => {
      const start = editor.selectionStart || 0;
      const end = editor.selectionEnd || 0;
      const source = editor.value || '';
      const lineStart = lineStartAt(source, start);
      const beforeCursor = source.slice(lineStart, start);
      if (start === end && /^\\s*$/.test(beforeCursor)) {
        const indent = nearestBlockIndent();
        applyEditorEdit(lineStart, end, `${indent}}`, indent.length + lineStart + 1, indent.length + lineStart + 1);
        return;
      }
      applyEditorEdit(start, end, '}');
    };

    const toggleLineComment = () => {
      const bounds = selectedLineBounds();
      const selected = bounds.source.slice(bounds.lineStart, bounds.lineEnd);
      const lines = selected.split('\\n');
      const nonEmptyLines = lines.filter((line) => line.trim());
      const shouldUncomment = nonEmptyLines.length > 0 && nonEmptyLines.every((line) => /^\\s*\\/\\//.test(line));
      const nextLines = lines.map((line) => {
        if (!line.trim()) {
          return line;
        }
        if (shouldUncomment) {
          return line.replace(/^(\\s*)\\/\\/?\\s?/, '$1');
        }
        return line.replace(/^(\\s*)/, '$1// ');
      });
      const replacement = nextLines.join('\\n');
      const delta = replacement.length - selected.length;
      applyEditorEdit(bounds.lineStart, bounds.lineEnd, replacement, bounds.start, bounds.end + delta);
    };

    const smartHome = (event) => {
      const bounds = currentLineBounds();
      const line = bounds.source.slice(bounds.start, bounds.end);
      const firstCodeColumn = (line.match(/^[ \\t]*/) || [''])[0].length;
      const firstCodeIndex = bounds.start + firstCodeColumn;
      const current = editor.selectionStart || 0;
      const target = current === firstCodeIndex ? bounds.start : firstCodeIndex;
      event.preventDefault();
      if (event.shiftKey) {
        editor.selectionEnd = target;
      } else {
        editor.selectionStart = target;
        editor.selectionEnd = target;
      }
      setBracketPairFromIndex(target);
    };

    const PAIRS = {
      '(': ')',
      '[': ']',
      '{': '}',
      '<': '>',
      '"': '"',
      "'": "'",
    };

    const insertPair = (open) => {
      const close = PAIRS[open];
      const start = editor.selectionStart || 0;
      const end = editor.selectionEnd || 0;
      const selected = editor.value.slice(start, end);
      if (start !== end) {
        applyEditorEdit(start, end, `${open}${selected}${close}`, start + 1, end + 1);
        return;
      }
      applyEditorEdit(start, end, `${open}${close}`, start + 1, start + 1);
    };

    const deleteEmptyPair = () => {
      const start = editor.selectionStart || 0;
      const end = editor.selectionEnd || 0;
      if (start !== end || start === 0) {
        return false;
      }
      const source = editor.value || '';
      const previous = source[start - 1];
      const next = source[start];
      if (PAIRS[previous] !== next) {
        return false;
      }
      applyEditorEdit(start - 1, start + 1, '', start - 1, start - 1);
      return true;
    };

    editor.addEventListener('keydown', (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key === '/') {
        event.preventDefault();
        toggleLineComment();
        return;
      }
      if (event.key === 'Home') {
        smartHome(event);
        return;
      }
      if (event.key === 'Enter') {
        event.preventDefault();
        smartEnter();
        return;
      }
      if (event.key === 'Backspace' && deleteEmptyPair()) {
        event.preventDefault();
        return;
      }
      if (event.key === '}') {
        event.preventDefault();
        smartClosingBrace();
        return;
      }
      if (Object.prototype.hasOwnProperty.call(PAIRS, event.key)) {
        event.preventDefault();
        insertPair(event.key);
        return;
      }
      if (event.key === 'Tab') {
        event.preventDefault();
        if (event.shiftKey) {
          unindentSelection();
        } else {
          indentSelection();
        }
      }
    });

    editor.addEventListener('input', () => {
      if (loading) {
        return;
      }
      bracketPair = cppLabFindBracketPair(editor.value, editor.selectionStart || 0);
      refreshHighlight();
      markDirty(activePath, true);
    });
    editor.addEventListener('scroll', syncScroll);
    editor.addEventListener('keyup', () => setBracketPairFromIndex(editor.selectionStart || 0));
    editor.addEventListener('click', () => setBracketPairFromIndex(editor.selectionStart || 0));
    editor.addEventListener('mousemove', (event) => {
      const index = editorIndexFromMouse(event);
      const nextPair = cppLabFindBracketPair(editor.value || '', index);
      if (
        (!nextPair && bracketPair)
        || (nextPair && (!bracketPair || nextPair.open !== bracketPair.open || nextPair.close !== bracketPair.close))
      ) {
        bracketPair = nextPair;
        refreshHighlight();
      }
    });
    editor.addEventListener('mouseleave', () => {
      if (bracketPair) {
        bracketPair = null;
        refreshHighlight();
      }
    });
  }

  if (saveButton) {
    const saveActiveFile = async () => {
      saveButton.disabled = true;
      try {
        await saveFile(activePath, editor ? editor.value : '');
        setStatus(`Saved ${activePath}.`);
      } catch (error) {
        setStatus(error && error.message ? error.message : 'Save failed.');
      } finally {
        saveButton.disabled = false;
      }
    };
    saveButton.addEventListener('click', saveActiveFile);
  }

  const runLab = async () => {
    if (!runButton || runButton.disabled) {
      return;
    }
    if (activePath && editor) {
      dirtyFiles[activePath] = editor.value;
    }
    runButton.disabled = true;
    runButton.textContent = 'Running...';
    setStatus('Saving and compiling...');
    if (output) {
      output.textContent = 'Saving files, then compiling...';
      output.classList.remove('is-error');
    }
    try {
      const files = Object.entries(dirtyFiles).map(([path, content]) => ({ path, content }));
      const response = await fetch('/_api/cpp-lab/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ files, runnable_path: activePath || '' }),
      });
      const result = await response.json();
      if (!response.ok && result.error) {
        throw new Error(result.error);
      }
      Object.keys(dirtyFiles).forEach((path) => delete dirtyFiles[path]);
      outputResult(result);
      if (activePath) {
        loadFile(activePath);
      }
    } catch (error) {
      if (output) {
        output.textContent = error && error.message ? error.message : 'Run failed.';
        output.classList.add('is-error');
      }
      setStatus(error && error.message ? error.message : 'Run failed.');
    } finally {
      runButton.disabled = false;
      runButton.textContent = 'Run Alt+C';
    }
  };

  if (runButton) {
    runButton.addEventListener('click', runLab);
  }

  document.addEventListener('keydown', (event) => {
    const key = String(event.key || '').toLowerCase();
    if (event.altKey && key === 'c') {
      event.preventDefault();
      runLab();
      return;
    }
    if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
      event.preventDefault();
      runLab();
      return;
    }
    if ((event.ctrlKey || event.metaKey) && key === 's') {
      event.preventDefault();
      if (saveButton) {
        saveButton.click();
      }
    }
  });

  if (clearButton) {
    clearButton.addEventListener('click', () => {
      if (output) {
        output.textContent = 'Output cleared.';
        output.classList.remove('is-error');
      }
      setStatus('Output cleared.');
    });
  }

  if (editorThemeButton) {
    editorThemeButton.addEventListener('click', () => {
      setTheme(
        editorPane,
        editorThemeButton,
        'cpp-lab:editor-theme',
        !(editorPane && editorPane.classList.contains('is-dark')),
      );
    });
  }

  if (outputThemeButton) {
    outputThemeButton.addEventListener('click', () => {
      setTheme(
        outputPane,
        outputThemeButton,
        'cpp-lab:output-theme',
        !(outputPane && outputPane.classList.contains('is-dark')),
      );
    });
  }

  if (activePath) {
    loadFile(activePath);
  }
}

function bindCppLab() {
  const root = document.querySelector('[data-cpp-lab-root]');
  if (!root) {
    return;
  }

  const fileSelect = root.querySelector('[data-cpp-lab-file-select]');
  const editorMount = root.querySelector('[data-cpp-lab-editor-mount]');
  const output = root.querySelector('[data-cpp-lab-output]');
  const status = root.querySelector('[data-cpp-lab-status]');
  const saveButton = root.querySelector('[data-cpp-lab-save]');
  const runButton = root.querySelector('[data-cpp-lab-run]');
  const clearButton = root.querySelector('[data-cpp-lab-clear]');
  const editorPane = root.querySelector('[data-cpp-lab-editor-pane]');
  const outputPane = root.querySelector('[data-cpp-lab-output-pane]');
  const editorThemeButton = root.querySelector('[data-cpp-lab-editor-theme]');
  const outputThemeButton = root.querySelector('[data-cpp-lab-output-theme]');
  const dirtyFiles = {};
  let activePath = fileSelect ? fileSelect.value : '';
  let editorView = null;
  let cm = null;
  let suppressChange = false;

  const CDN = {
    codemirror: 'https://esm.sh/codemirror@6.0.1?deps=@codemirror/state@6.5.2,@codemirror/view@6.38.8,@codemirror/language@6.11.3,@codemirror/commands@6.8.1',
    cpp: 'https://esm.sh/@codemirror/lang-cpp@6.0.3?deps=@codemirror/state@6.5.2,@codemirror/view@6.38.8,@codemirror/language@6.11.3',
    state: 'https://esm.sh/@codemirror/state@6.5.2',
    view: 'https://esm.sh/@codemirror/view@6.38.8?deps=@codemirror/state@6.5.2',
    commands: 'https://esm.sh/@codemirror/commands@6.8.1?deps=@codemirror/state@6.5.2,@codemirror/view@6.38.8,@codemirror/language@6.11.3',
    oneDark: 'https://esm.sh/@codemirror/theme-one-dark@6.1.3?deps=@codemirror/state@6.5.2,@codemirror/view@6.38.8,@codemirror/language@6.11.3',
  };

  const setStatus = (message) => {
    if (status) {
      status.textContent = message;
    }
  };

  const editorValue = () => (editorView ? editorView.state.doc.toString() : '');

  const setEditorValue = (content) => {
    if (!editorView) {
      return;
    }
    suppressChange = true;
    editorView.dispatch({
      changes: { from: 0, to: editorView.state.doc.length, insert: content || '' },
      selection: { anchor: 0 },
    });
    suppressChange = false;
  };

  const setThemeButton = (button, dark) => {
    if (button) {
      button.textContent = dark ? 'Light' : 'Dark';
      button.setAttribute('aria-pressed', dark ? 'true' : 'false');
    }
  };

  const outputDark = () => localStorage.getItem(getStoreKey('cpp-lab:output-theme')) === 'dark';
  const editorDark = () => localStorage.getItem(getStoreKey('cpp-lab:editor-theme')) === 'dark';

  const setOutputTheme = (dark) => {
    if (outputPane) {
      outputPane.classList.toggle('is-dark', dark);
    }
    setThemeButton(outputThemeButton, dark);
    localStorage.setItem(getStoreKey('cpp-lab:output-theme'), dark ? 'dark' : 'light');
  };

  const editorThemeExtension = (dark) => {
    if (!cm) {
      return [];
    }
    if (dark) {
      return cm.oneDark;
    }
    return cm.EditorView.theme({
      '&': {
        backgroundColor: '#dbeafe',
        color: '#111827',
      },
      '.cm-content': {
        caretColor: '#0f172a',
      },
      '.cm-gutters': {
        backgroundColor: '#dbeafe',
        color: '#64748b',
        borderRightColor: 'rgba(81, 67, 57, 0.16)',
      },
      '&.cm-focused .cm-cursor': {
        borderLeftColor: '#0f172a',
      },
      '&.cm-focused .cm-selectionBackground, .cm-selectionBackground, .cm-content ::selection': {
        backgroundColor: 'rgba(37, 99, 235, 0.26)',
      },
      '.cm-activeLine': {
        backgroundColor: 'rgba(255, 255, 255, 0.34)',
      },
      '.cm-activeLineGutter': {
        backgroundColor: 'rgba(255, 255, 255, 0.44)',
      },
    });
  };

  const applyEditorTheme = (dark) => {
    if (editorPane) {
      editorPane.classList.toggle('is-dark', dark);
    }
    setThemeButton(editorThemeButton, dark);
    localStorage.setItem(getStoreKey('cpp-lab:editor-theme'), dark ? 'dark' : 'light');
    if (editorView && cm) {
      editorView.dispatch({
        effects: cm.themeCompartment.reconfigure(editorThemeExtension(dark)),
      });
    }
  };

  const markDirty = (path, dirty) => {
    if (!path) {
      return;
    }
    if (dirty) {
      dirtyFiles[path] = editorValue();
    } else {
      delete dirtyFiles[path];
    }
    const dirtyCount = Object.keys(dirtyFiles).length;
    setStatus(dirtyCount ? `${dirtyCount} unsaved file(s).` : 'Saved.');
  };

  const saveFile = async (path, content) => {
    const response = await fetch('/_api/cpp-lab/file', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path, content }),
    });
    const result = await response.json();
    if (!response.ok || !result.ok) {
      throw new Error(result.error || 'Failed to save file.');
    }
    markDirty(path, false);
    return result;
  };

  const loadFile = async (path) => {
    if (!path || !editorView) {
      return;
    }
    activePath = path;
    setStatus(`Loading ${path}...`);
    try {
      const response = await fetch(`/_api/cpp-lab/file?path=${encodeURIComponent(path)}`);
      const result = await response.json();
      if (!response.ok || !result.ok) {
        throw new Error(result.error || 'Failed to load file.');
      }
      setEditorValue(result.content || '');
      markDirty(path, false);
      setStatus(`Loaded ${path}.`);
      editorView.focus();
    } catch (error) {
      setStatus(error && error.message ? error.message : 'Failed to load file.');
    }
  };

  const outputResult = (result) => {
    const parts = compileResultParts(result);
    const lines = [];
    if (result.phase === 'compile') {
      lines.push(parts.compile);
    } else if (result.phase === 'validation' && result.error) {
      lines.push(result.error);
    } else {
      if (parts.runtime) {
        lines.push(parts.runtime);
      }
      if (result.compile_stderr || result.compile_stdout || result.compile_metrics) {
        lines.push('', '[compile diagnostics]', parts.compile);
      }
    }
    lines.push('', result.ok ? '=== Code Execution Successful ===' : `=== ${parts.status} ===`);
    if (output) {
      output.textContent = lines.join('\\n').trim();
      output.classList.toggle('is-error', !result.ok);
    }
    setStatus(parts.status);
  };

  const runLab = async () => {
    if (!runButton || runButton.disabled || !editorView) {
      return;
    }
    if (activePath) {
      dirtyFiles[activePath] = editorValue();
    }
    runButton.disabled = true;
    runButton.textContent = 'Running...';
    setStatus('Saving and compiling...');
    if (output) {
      output.textContent = 'Saving files, then compiling...';
      output.classList.remove('is-error');
    }
    try {
      const files = Object.entries(dirtyFiles).map(([path, content]) => ({ path, content }));
      const response = await fetch('/_api/cpp-lab/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ files, runnable_path: activePath || '' }),
      });
      const result = await response.json();
      if (!response.ok && result.error) {
        throw new Error(result.error);
      }
      Object.keys(dirtyFiles).forEach((path) => delete dirtyFiles[path]);
      outputResult(result);
      if (activePath) {
        loadFile(activePath);
      }
    } catch (error) {
      if (output) {
        output.textContent = error && error.message ? error.message : 'Run failed.';
        output.classList.add('is-error');
      }
      setStatus(error && error.message ? error.message : 'Run failed.');
    } finally {
      runButton.disabled = false;
      runButton.textContent = 'Run Alt+C';
    }
  };

  const saveActiveFile = async () => {
    if (!saveButton || !activePath || !editorView) {
      return;
    }
    saveButton.disabled = true;
    try {
      await saveFile(activePath, editorValue());
      setStatus(`Saved ${activePath}.`);
    } catch (error) {
      setStatus(error && error.message ? error.message : 'Save failed.');
    } finally {
      saveButton.disabled = false;
    }
  };

  const showEditorLoadError = (error) => {
    if (editorMount) {
      editorMount.innerHTML = `<div class="cpp-lab-editor-error">CodeMirror failed to load from CDN.\\n${escapeHtml(error && error.message ? error.message : error)}</div>`;
    }
    setStatus('CodeMirror failed to load from CDN.');
  };

  const initEditor = async () => {
    if (!editorMount) {
      return;
    }
    setStatus('Loading CodeMirror...');
    try {
      const [codemirrorModule, cppModule, stateModule, viewModule, commandsModule, oneDarkModule] = await Promise.all([
        import(CDN.codemirror),
        import(CDN.cpp),
        import(CDN.state),
        import(CDN.view),
        import(CDN.commands),
        import(CDN.oneDark),
      ]);
      cm = {
        EditorView: codemirrorModule.EditorView,
        basicSetup: codemirrorModule.basicSetup,
        cpp: cppModule.cpp,
        Compartment: stateModule.Compartment,
        keymap: viewModule.keymap,
        indentWithTab: commandsModule.indentWithTab,
        oneDark: oneDarkModule.oneDark,
        themeCompartment: new stateModule.Compartment(),
      };
      const keyBindings = [
        {
          key: 'Alt-c',
          run: () => {
            runLab();
            return true;
          },
        },
        {
          key: 'Mod-Enter',
          run: () => {
            runLab();
            return true;
          },
        },
        {
          key: 'Mod-s',
          run: () => {
            saveActiveFile();
            return true;
          },
        },
        commandsModule.indentWithTab,
      ];
      if (commandsModule.toggleComment) {
        keyBindings.push({ key: 'Mod-/', run: commandsModule.toggleComment });
      }
      const shortcutMap = cm.keymap.of(keyBindings);
      editorMount.textContent = '';
      editorView = new cm.EditorView({
        doc: '',
        parent: editorMount,
        extensions: [
          cm.basicSetup,
          cm.cpp(),
          shortcutMap,
          cm.themeCompartment.of(editorThemeExtension(editorDark())),
          cm.EditorView.updateListener.of((update) => {
            if (update.docChanged && !suppressChange) {
              markDirty(activePath, true);
            }
          }),
        ],
      });
      applyEditorTheme(editorDark());
      if (activePath) {
        await loadFile(activePath);
      }
    } catch (error) {
      showEditorLoadError(error);
    }
  };

  setOutputTheme(outputDark());

  if (fileSelect) {
    fileSelect.addEventListener('change', () => {
      loadFile(fileSelect.value);
    });
  }

  if (saveButton) {
    saveButton.addEventListener('click', saveActiveFile);
  }

  if (runButton) {
    runButton.addEventListener('click', runLab);
  }

  if (clearButton) {
    clearButton.addEventListener('click', () => {
      if (output) {
        output.textContent = 'Output cleared.';
        output.classList.remove('is-error');
      }
      setStatus('Output cleared.');
    });
  }

  if (editorThemeButton) {
    editorThemeButton.addEventListener('click', () => applyEditorTheme(!editorDark()));
  }

  if (outputThemeButton) {
    outputThemeButton.addEventListener('click', () => setOutputTheme(!outputDark()));
  }

  document.addEventListener('keydown', (event) => {
    const key = String(event.key || '').toLowerCase();
    if (event.altKey && key === 'c') {
      event.preventDefault();
      runLab();
      return;
    }
    if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
      event.preventDefault();
      runLab();
      return;
    }
    if ((event.ctrlKey || event.metaKey) && key === 's') {
      event.preventDefault();
      saveActiveFile();
    }
  });

  initEditor();
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

function renderInlineNoteMarkdown(text) {
  let htmlText = escapeHtml(text || '');
  htmlText = htmlText.replace(/!\\[([^\\]]*)\\]\\(([^)]+)\\)/g, (match, alt, url) => {
    const safeAlt = escapeHtml(alt || '');
    return (
      `<figure class="note-image"><img src="${escapeHtml(url)}" alt="${safeAlt}">`
      + `<figcaption>${safeAlt || 'image'}</figcaption></figure>`
    );
  });
  htmlText = htmlText.replace(/\\[([^\\]]+)\\]\\(([^)]+)\\)/g, (match, label, url) => (
    `<a href="${escapeHtml(url)}" target="_blank" rel="noreferrer">${label}</a>`
  ));
  return htmlText;
}

function renderNotePreview(text) {
  const source = text || '';
  if (!source.trim()) {
    return (
      '<div class="note-empty">Paste text or screenshots here. '
      + '`Ctrl+V` works when the note editor is focused.</div>'
    );
  }

  const lines = source.split(String.fromCharCode(10));
  const blocks = [];
  let buffer = [];
  let codeBuffer = [];
  let codeLang = '';
  let inCode = false;

  const flushText = () => {
    if (!buffer.length) {
      return;
    }
    blocks.push(renderInlineNoteMarkdown(buffer.join(String.fromCharCode(10))).split(String.fromCharCode(10)).join('<br>'));
    buffer = [];
  };

  lines.forEach((line) => {
    const fence = line.match(/^```([A-Za-z0-9_+-]*)\\s*$/);
    if (fence) {
      if (inCode) {
        blocks.push(
          `<pre class="note-code"><code class="language-${escapeHtml(codeLang)}">${escapeHtml(codeBuffer.join(String.fromCharCode(10)))}</code></pre>`
        );
        codeBuffer = [];
        codeLang = '';
        inCode = false;
      } else {
        flushText();
        codeLang = fence[1] || 'text';
        inCode = true;
      }
      return;
    }

    if (inCode) {
      codeBuffer.push(line);
    } else {
      buffer.push(line);
    }
  });

  if (inCode) {
    blocks.push(
      `<pre class="note-code"><code class="language-${escapeHtml(codeLang || 'text')}">${escapeHtml(codeBuffer.join(String.fromCharCode(10)))}</code></pre>`
    );
  }
  flushText();

  return blocks.join('');
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
  const summaryLabel = root.querySelector('[data-note-summary]');
  const statusLabel = root.querySelector('[data-note-status]');

  let syncTimer = null;
  state.open = false;

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
          ? `
              <img
                src="${escapeHtml(attachment.url)}"
                alt="${escapeHtml(attachment.filename || 'attachment')}"
                class="note-attachment-preview"
              >
            `
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
              <button
                class="button-secondary"
                type="button"
                data-note-delete-attachment
                data-attachment-url="${escapeHtml(attachment.url)}"
              >
                Delete
              </button>
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
    if (summaryLabel) {
      const hasText = Boolean(state.text.trim());
      const parts = [];
      if (hasText) {
        parts.push('<strong>Text note saved</strong>');
      }
      if (state.attachments.length) {
        parts.push(`${state.attachments.length} attachment${state.attachments.length === 1 ? '' : 's'}`);
      }
      summaryLabel.innerHTML = parts.length
        ? parts.join('<span aria-hidden="true">/</span>')
        : 'No note yet';
    }
  };

  const setOpen = (open, focusEditor = false) => {
    state.open = open;
    if (noteBody) {
      noteBody.hidden = !open;
    }
    toggleButtons.forEach((button) => {
      button.textContent = open ? 'Done' : 'Edit note';
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
}

function bindSavedPage() {
  const root = document.querySelector('[data-saved-page-root]');
  if (!root) {
    return;
  }

  const boot = getBootData();
  const savedRoot = document.querySelector('[data-saved-root]');
  const savedEmpty = document.querySelector('[data-saved-empty]');
  const savedCount = document.querySelector('[data-saved-count]');
  const cardMap = new Map();

  boot.notebooks.forEach((notebook) => {
    notebook.cards.forEach((card) => {
      cardMap.set(cardKey(notebook.slug, card.number), { notebook, card });
    });
  });

  const renderSaved = () => {
    if (!savedRoot) {
      return;
    }

    const entries = getSavedCards();
    const validEntries = entries
      .map((key) => ({ key, pair: cardMap.get(key) }))
      .filter((entry) => entry.pair);

    if (validEntries.length !== entries.length) {
      saveSavedCards(validEntries.map((entry) => entry.key));
    }

    if (savedCount) {
      savedCount.textContent = String(validEntries.length);
    }

    if (!validEntries.length) {
      savedRoot.innerHTML = '';
      if (savedEmpty) {
        savedEmpty.hidden = false;
      }
      return;
    }

    if (savedEmpty) {
      savedEmpty.hidden = true;
    }

    savedRoot.innerHTML = validEntries
      .map((entry) => {
        const notebook = entry.pair.notebook;
        const card = entry.pair.card;
        return `
          <article class="card-tile saved-card" data-saved-card data-key="${escapeHtml(entry.key)}">
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
              <button class="button-secondary" type="button" data-unsave-button data-key="${escapeHtml(entry.key)}">Remove</button>
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
    if (!event.key || event.key.startsWith(getStoreKey('saved'))) {
      renderSaved();
    }
  });
}

function bindNotesPage() {
  const root = document.querySelector('[data-notes-root]');
  if (!root) {
    return;
  }

  const boot = getBootData();
  const savedRoot = document.querySelector('[data-saved-root]');
  const savedEmpty = document.querySelector('[data-saved-empty]');
  const savedCount = document.querySelector('[data-saved-count]');
  const collectionBodies = new Map(
    Array.from(document.querySelectorAll('[data-home-body]')).map((node) => [node.dataset.homeBody, node]),
  );
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

  const homeNoteList = document.querySelector('[data-home-note-list]');
  const homeNoteEmpty = document.querySelector('[data-home-note-empty]');
  const homeNoteCounts = Array.from(document.querySelectorAll('[data-home-note-count]'));
  const homeNoteTitle = document.querySelector('[data-home-note-title]');
  const homeNoteText = document.querySelector('[data-home-note-text]');
  const homeNotePreviewShell = document.querySelector('[data-home-note-preview-shell]');
  const homeNotePreview = document.querySelector('[data-home-note-preview]');
  const homeNoteAttachments = document.querySelector('[data-home-note-attachments]');
  const homeNoteStatus = document.querySelector('[data-home-note-status]');
  const homeNoteSave = document.querySelector('[data-home-note-save]');
  const homeNoteClear = document.querySelector('[data-home-note-clear]');
  const homeNoteNew = document.querySelector('[data-home-note-new]');
  const homeNoteDeleteCurrent = document.querySelector('[data-home-note-delete-current]');
  const homeNoteTypeInputs = Array.from(document.querySelectorAll('[data-home-note-type]'));
  const homeNoteAttachmentsShell = document.querySelector('[data-home-note-attachments-shell]');
  const noteRunnerRoot = document.querySelector('[data-note-runner-root]');
  const noteRunnerBackdrop = document.querySelector('[data-note-runner-backdrop]');
  const noteRunnerClose = document.querySelector('[data-note-runner-close]');
  const noteRunnerSave = document.querySelector('[data-note-runner-save]');
  const noteRunnerRun = document.querySelector('[data-note-runner-run]');
  const noteRunnerSource = document.querySelector('[data-note-runner-source]');
  const noteRunnerStdin = document.querySelector('[data-note-runner-stdin]');
  const noteRunnerCompileOutput = document.querySelector('[data-note-runner-compile-output]');
  const noteRunnerRuntimeOutput = document.querySelector('[data-note-runner-runtime-output]');
  const noteRunnerStatus = document.querySelector('[data-note-runner-status]');
  let currentHomeNote = null;
  let currentRunnerNoteId = '';

  const createHomeNoteDraft = () => {
    const now = new Date().toISOString();
    const id = window.crypto && window.crypto.randomUUID ? window.crypto.randomUUID() : `${Date.now()}-${Math.random()}`;
    return { id, type: 'text', title: '', text: '', attachments: [], createdAt: now, updatedAt: now };
  };

  const formatNoteTime = (value) => value ? value.replace('T', ' ').slice(0, 19) : '';

  const setHomeNoteStatus = (text) => {
    if (homeNoteStatus) {
      homeNoteStatus.textContent = text;
    }
  };

  const selectedHomeNoteType = () => {
    const selected = homeNoteTypeInputs.find((input) => input.checked);
    return selected && selected.value === 'cpp' ? 'cpp' : 'text';
  };

  const renderEditorMode = () => {
    if (!currentHomeNote) {
      return;
    }
    const isCode = currentHomeNote.type === 'cpp';
    homeNoteTypeInputs.forEach((input) => {
      input.checked = input.value === currentHomeNote.type;
    });
    if (homeNoteText) {
      homeNoteText.classList.toggle('is-code', isCode);
      homeNoteText.spellcheck = !isCode;
      homeNoteText.placeholder = isCode
        ? 'Write C++17 code here. Use RUN C++ on the saved note card to compile and run.'
        : 'Write a note. Paste text or screenshots with Ctrl+V. Markdown code blocks like ```cpp are displayed in preview.';
    }
    if (homeNotePreviewShell) {
      homeNotePreviewShell.hidden = isCode;
    }
    if (homeNoteAttachmentsShell) {
      homeNoteAttachmentsShell.hidden = isCode;
    }
    resizeHomeNoteEditor();
  };

  const resizeHomeNoteEditor = () => {
    if (!homeNoteText || !currentHomeNote || currentHomeNote.type !== 'cpp') {
      if (homeNoteText) {
        homeNoteText.style.height = '';
        homeNoteText.style.overflowY = '';
      }
      return;
    }
    const maxHeight = Math.max(420, Math.floor(window.innerHeight * 0.78));
    homeNoteText.style.height = 'auto';
    const nextHeight = Math.min(Math.max(homeNoteText.scrollHeight + 4, 420), maxHeight);
    homeNoteText.style.height = `${nextHeight}px`;
    homeNoteText.style.overflowY = homeNoteText.scrollHeight > maxHeight ? 'auto' : 'hidden';
  };

  const syncHomeNoteEditor = () => {
    if (!currentHomeNote) {
      currentHomeNote = createHomeNoteDraft();
    }
    if (homeNoteTitle) {
      homeNoteTitle.value = currentHomeNote.title || '';
    }
    if (homeNoteText) {
      homeNoteText.value = currentHomeNote.text || '';
    }
    if (homeNoteDeleteCurrent) {
      homeNoteDeleteCurrent.hidden = !getHomeNotes().some((note) => note.id === currentHomeNote.id);
    }
    renderEditorMode();
  };

  const renderHomeNoteAttachments = () => {
    if (!homeNoteAttachments || !currentHomeNote) {
      return;
    }

    if (!currentHomeNote.attachments.length) {
      homeNoteAttachments.innerHTML = '<div class="note-empty">No attachments yet.</div>';
      return;
    }

    homeNoteAttachments.innerHTML = currentHomeNote.attachments
      .map((attachment) => {
        const isImage = (attachment.mimeType || '').startsWith('image/');
        const previewHtml = isImage
          ? `<img src="${escapeHtml(attachment.url)}" alt="${escapeHtml(attachment.filename || 'attachment')}" class="note-attachment-preview">`
          : '<span class="note-file-icon">FILE</span>';
        return `
          <article class="note-attachment-card">
            <div class="note-attachment-top">
              ${previewHtml}
              <div class="note-attachment-meta">
                <div class="note-attachment-name">${escapeHtml(attachment.filename || 'attachment')}</div>
                <div class="note-attachment-sub">${escapeHtml(attachment.mimeType || '')}</div>
              </div>
            </div>
            <div class="note-attachment-actions">
              <a class="button-secondary" href="${escapeHtml(attachment.url)}" target="_blank" rel="noreferrer">Open</a>
              <button class="button-secondary" type="button" data-home-note-delete-attachment data-attachment-url="${escapeHtml(attachment.url)}">Delete</button>
            </div>
          </article>
        `;
      })
      .join('');

    homeNoteAttachments.querySelectorAll('[data-home-note-delete-attachment]').forEach((button) => {
      button.addEventListener('click', async () => {
        const attachmentUrl = button.dataset.attachmentUrl || '';
        if (!attachmentUrl || !currentHomeNote) {
          return;
        }
        button.disabled = true;
        try {
          await deleteNoteAttachment('home-notes', currentHomeNote.id, attachmentUrl);
          currentHomeNote.attachments = currentHomeNote.attachments.filter((item) => item.url !== attachmentUrl);
          currentHomeNote.text = currentHomeNote.text
            .replace(new RegExp(`!\\[[^\\]]*\\]\\(${escapeRegExp(attachmentUrl)}\\)\\n?`, 'g'), '')
            .replace(new RegExp(`\\[[^\\]]*\\]\\(${escapeRegExp(attachmentUrl)}\\)`, 'g'), '')
            .trim();
          currentHomeNote.updatedAt = new Date().toISOString();
          syncHomeNoteEditor();
          renderHomeNotePreview();
          renderHomeNoteAttachments();
          saveHomeNoteState(currentHomeNote);
          renderHomeNoteCards();
          setHomeNoteStatus(`Saved ${formatNoteTime(currentHomeNote.updatedAt)}`);
        } catch (error) {
          setHomeNoteStatus(error && error.message ? error.message : 'Failed to delete attachment.');
        } finally {
          button.disabled = false;
        }
      });
    });
  };

  const renderHomeNotePreview = () => {
    if (homeNotePreview && currentHomeNote) {
      if (currentHomeNote.type === 'cpp') {
        homeNotePreview.innerHTML = `<pre class="note-code"><code class="language-cpp">${escapeHtml(currentHomeNote.text || '')}</code></pre>`;
      } else {
        homeNotePreview.innerHTML = renderNotePreview(currentHomeNote.text || '');
      }
    }
  };

  const renderHomeNoteCards = () => {
    if (!homeNoteList) {
      return;
    }

    const notes = getHomeNotes();
    homeNoteCounts.forEach((node) => {
      node.textContent = String(notes.length);
    });
    if (homeNoteEmpty) {
      homeNoteEmpty.hidden = notes.length > 0;
    }
    if (!notes.length) {
      homeNoteList.innerHTML = '';
      return;
    }

    homeNoteList.innerHTML = notes
      .map((note) => {
        const preview = firstTextLine(note.text) || `${note.attachments.length} attachment(s)`;
        const isCode = note.type === 'cpp';
        return `
          <article class="card-tile note-card home-note-card" data-home-note-card data-note-id="${escapeHtml(note.id)}">
            <div class="card-meta">
              <span class="card-number">N</span>
              <span>${escapeHtml(formatNoteTime(note.updatedAt || note.createdAt))}</span>
            </div>
            <h3>${escapeHtml((note.title || '').trim() || 'Untitled note')}</h3>
            <p class="card-preview">${escapeHtml(preview)}</p>
            <div class="tag-row">
              <span class="tag">${isCode ? 'C++ code' : 'text note'}</span>
              ${isCode ? '<span class="tag">cpp17</span>' : `<span class="tag">${note.attachments.length} attachments</span>`}
            </div>
            <div class="reveal-actions">
              <button class="button" type="button" data-home-note-edit data-note-id="${escapeHtml(note.id)}">Edit</button>
              ${isCode ? `<button class="button" type="button" data-home-note-run data-note-id="${escapeHtml(note.id)}">RUN C++</button>` : ''}
              <button class="button-secondary" type="button" data-home-note-delete data-note-id="${escapeHtml(note.id)}">Delete</button>
            </div>
          </article>
        `;
      })
      .join('');

    homeNoteList.querySelectorAll('[data-home-note-edit]').forEach((button) => {
      button.addEventListener('click', () => {
        const note = getHomeNotes().find((entry) => entry.id === button.dataset.noteId);
        if (!note) {
          return;
        }
        currentHomeNote = normalizeHomeNote(note.id, note);
        syncHomeNoteEditor();
        renderHomeNotePreview();
        renderHomeNoteAttachments();
        setHomeNoteStatus(`Loaded ${formatNoteTime(currentHomeNote.updatedAt || currentHomeNote.createdAt)}`);
        if (homeNoteTitle) {
          homeNoteTitle.focus();
        }
      });
    });

    homeNoteList.querySelectorAll('[data-home-note-run]').forEach((button) => {
      button.addEventListener('click', () => {
        const note = getHomeNotes().find((entry) => entry.id === button.dataset.noteId);
        if (note) {
          openNoteRunner(note);
        }
      });
    });

    homeNoteList.querySelectorAll('[data-home-note-delete]').forEach((button) => {
      button.addEventListener('click', async () => {
        const noteId = button.dataset.noteId || '';
        const note = getHomeNotes().find((entry) => entry.id === noteId);
        if (!note) {
          return;
        }
        button.disabled = true;
        try {
          for (const attachment of note.attachments) {
            await deleteNoteAttachment('home-notes', note.id, attachment.url);
          }
          deleteHomeNoteState(note.id);
          if (currentHomeNote && currentHomeNote.id === note.id) {
            currentHomeNote = createHomeNoteDraft();
            syncHomeNoteEditor();
            renderHomeNotePreview();
            renderHomeNoteAttachments();
          }
          renderHomeNoteCards();
          setHomeNoteStatus('Deleted note.');
        } catch (error) {
          setHomeNoteStatus(error && error.message ? error.message : 'Failed to delete note.');
        } finally {
          button.disabled = false;
        }
      });
    });
  };

  const runnerStorageKey = (noteId) => getStoreKey(`home-note-runner:${noteId}`);

  const loadRunnerState = (noteId) => {
    const raw = safeJsonParse(localStorage.getItem(runnerStorageKey(noteId)), null) || {};
    return {
      source: typeof raw.source === 'string' ? raw.source : undefined,
      stdin: typeof raw.stdin === 'string' ? raw.stdin : '',
      lastResult: raw.lastResult && typeof raw.lastResult === 'object' ? raw.lastResult : null,
    };
  };

  const saveRunnerState = (noteId, state) => {
    localStorage.setItem(runnerStorageKey(noteId), JSON.stringify(state));
  };

  const setRunnerOutput = (result) => {
    const parts = compileResultParts(result);
    if (noteRunnerCompileOutput) {
      noteRunnerCompileOutput.textContent = result ? parts.compile : 'Waiting for code...';
    }
    if (noteRunnerRuntimeOutput) {
      noteRunnerRuntimeOutput.textContent = result ? parts.runtime : 'RUN to see output.';
    }
    if (noteRunnerStatus) {
      noteRunnerStatus.textContent = result ? parts.status : 'Closed';
    }
  };

  const setNoteRunnerOpen = (open) => {
    if (!noteRunnerRoot) {
      return;
    }
    noteRunnerRoot.classList.toggle('is-open', open);
    noteRunnerRoot.setAttribute('aria-hidden', open ? 'false' : 'true');
    if (noteRunnerBackdrop) {
      noteRunnerBackdrop.hidden = !open;
      noteRunnerBackdrop.classList.toggle('is-open', open);
    }
    document.body.classList.toggle('playground-open', open);
    if (open && noteRunnerSource) {
      noteRunnerSource.focus();
    }
  };

  const openNoteRunner = (note) => {
    if (!noteRunnerRoot || !note || note.type !== 'cpp') {
      return;
    }
    currentRunnerNoteId = note.id;
    const state = loadRunnerState(note.id);
    if (noteRunnerSource) {
      noteRunnerSource.value = state.source === undefined ? note.text : state.source;
    }
    if (noteRunnerStdin) {
      noteRunnerStdin.value = state.stdin;
    }
    setRunnerOutput(state.lastResult);
    if (noteRunnerStatus) {
      noteRunnerStatus.textContent = `Loaded ${note.title || 'C++ note'}.`;
    }
    setNoteRunnerOpen(true);
  };

  const persistCurrentRunnerState = (lastResult) => {
    if (!currentRunnerNoteId) {
      return;
    }
    const existing = loadRunnerState(currentRunnerNoteId);
    const state = {
      source: noteRunnerSource ? noteRunnerSource.value : existing.source,
      stdin: noteRunnerStdin ? noteRunnerStdin.value : existing.stdin,
      lastResult: lastResult === undefined ? existing.lastResult : lastResult,
    };
    saveRunnerState(currentRunnerNoteId, state);
  };

  const saveCurrentHomeNote = () => {
    if (!currentHomeNote) {
      currentHomeNote = createHomeNoteDraft();
    }
    currentHomeNote.type = selectedHomeNoteType();
    currentHomeNote.title = homeNoteTitle ? homeNoteTitle.value : currentHomeNote.title;
    currentHomeNote.text = homeNoteText ? homeNoteText.value : currentHomeNote.text;
    if (!currentHomeNote.createdAt) {
      currentHomeNote.createdAt = new Date().toISOString();
    }
    currentHomeNote.updatedAt = new Date().toISOString();
    currentHomeNote = saveHomeNoteState(currentHomeNote);
    syncHomeNoteEditor();
    renderHomeNotePreview();
    renderHomeNoteAttachments();
    renderHomeNoteCards();
    setHomeNoteStatus(`Saved ${formatNoteTime(currentHomeNote.updatedAt)}`);
  };

  const resetHomeNoteEditor = () => {
    currentHomeNote = createHomeNoteDraft();
    syncHomeNoteEditor();
    renderHomeNotePreview();
    renderHomeNoteAttachments();
    setHomeNoteStatus('Draft');
  };

  if (homeNoteTitle) {
    homeNoteTitle.addEventListener('input', () => {
      if (!currentHomeNote) {
        currentHomeNote = createHomeNoteDraft();
      }
      currentHomeNote.title = homeNoteTitle.value;
      setHomeNoteStatus('Draft');
    });
  }

  homeNoteTypeInputs.forEach((input) => {
    input.addEventListener('change', () => {
      if (!currentHomeNote) {
        currentHomeNote = createHomeNoteDraft();
      }
      currentHomeNote.type = selectedHomeNoteType();
      renderEditorMode();
      renderHomeNotePreview();
      setHomeNoteStatus('Draft');
    });
  });

  if (homeNoteText) {
    homeNoteText.addEventListener('input', () => {
      if (!currentHomeNote) {
        currentHomeNote = createHomeNoteDraft();
      }
      currentHomeNote.text = homeNoteText.value;
      resizeHomeNoteEditor();
      renderHomeNotePreview();
      setHomeNoteStatus('Draft');
    });

    homeNoteText.addEventListener('paste', async (event) => {
      const clipboardItems = Array.from((event.clipboardData && event.clipboardData.items) || []);
      const imageFiles = clipboardItems
        .map((item) => item.kind === 'file' ? item.getAsFile() : null)
        .filter((file) => file && file.type && file.type.startsWith('image/'));

      if (!imageFiles.length) {
        return;
      }
      if ((currentHomeNote && currentHomeNote.type === 'cpp') || selectedHomeNoteType() === 'cpp') {
        return;
      }

      event.preventDefault();
      if (!currentHomeNote) {
        currentHomeNote = createHomeNoteDraft();
      }
      const insertedSnippets = [];
      try {
        for (const file of imageFiles) {
          const attachment = await uploadNoteAttachment('home-notes', currentHomeNote.id, file);
          currentHomeNote.attachments.push(attachment);
          insertedSnippets.push(`![${attachment.filename}](${attachment.url})`);
        }
        insertTextAtCursor(homeNoteText, `${insertedSnippets.join(String.fromCharCode(10))}${String.fromCharCode(10)}`);
        currentHomeNote.text = homeNoteText.value;
        currentHomeNote.updatedAt = new Date().toISOString();
        saveHomeNoteState(currentHomeNote);
        renderHomeNotePreview();
        renderHomeNoteAttachments();
        renderHomeNoteCards();
        setHomeNoteStatus(`Saved ${formatNoteTime(currentHomeNote.updatedAt)}`);
      } catch (error) {
        setHomeNoteStatus(error && error.message ? error.message : 'Failed to upload clipboard image.');
      }
    });
  }

  if (homeNoteSave) {
    homeNoteSave.addEventListener('click', saveCurrentHomeNote);
  }

  if (homeNoteClear) {
    homeNoteClear.addEventListener('click', resetHomeNoteEditor);
  }

  if (homeNoteNew) {
    homeNoteNew.addEventListener('click', () => {
      resetHomeNoteEditor();
      if (homeNoteTitle) {
        homeNoteTitle.focus();
      }
    });
  }

  if (homeNoteDeleteCurrent) {
    homeNoteDeleteCurrent.addEventListener('click', async () => {
      if (!currentHomeNote || !getHomeNotes().some((note) => note.id === currentHomeNote.id)) {
        resetHomeNoteEditor();
        return;
      }
      homeNoteDeleteCurrent.disabled = true;
      try {
        for (const attachment of currentHomeNote.attachments) {
          await deleteNoteAttachment('home-notes', currentHomeNote.id, attachment.url);
        }
        deleteHomeNoteState(currentHomeNote.id);
        resetHomeNoteEditor();
        renderHomeNoteCards();
        setHomeNoteStatus('Deleted note.');
      } catch (error) {
        setHomeNoteStatus(error && error.message ? error.message : 'Failed to delete note.');
      } finally {
        homeNoteDeleteCurrent.disabled = false;
      }
    });
  }

  if (noteRunnerClose) {
    noteRunnerClose.addEventListener('click', () => setNoteRunnerOpen(false));
  }

  if (noteRunnerBackdrop) {
    noteRunnerBackdrop.addEventListener('click', () => setNoteRunnerOpen(false));
  }

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && noteRunnerRoot && noteRunnerRoot.classList.contains('is-open')) {
      setNoteRunnerOpen(false);
    }
  });

  if (noteRunnerSource) {
    noteRunnerSource.addEventListener('input', () => persistCurrentRunnerState(undefined));
  }

  if (noteRunnerStdin) {
    noteRunnerStdin.addEventListener('input', () => persistCurrentRunnerState(undefined));
  }

  if (noteRunnerSave) {
    noteRunnerSave.addEventListener('click', () => {
      if (!currentRunnerNoteId || !noteRunnerSource) {
        return;
      }
      const note = getHomeNotes().find((entry) => entry.id === currentRunnerNoteId);
      if (!note) {
        return;
      }
      note.type = 'cpp';
      note.text = noteRunnerSource.value;
      note.updatedAt = new Date().toISOString();
      saveHomeNoteState(note);
      persistCurrentRunnerState(undefined);
      renderHomeNoteCards();
      if (currentHomeNote && currentHomeNote.id === note.id) {
        currentHomeNote = normalizeHomeNote(note.id, note);
        syncHomeNoteEditor();
        renderHomeNotePreview();
      }
      if (noteRunnerStatus) {
        noteRunnerStatus.textContent = `Saved ${formatNoteTime(note.updatedAt)}.`;
      }
    });
  }

  if (noteRunnerRun) {
    noteRunnerRun.addEventListener('click', async () => {
      if (!currentRunnerNoteId) {
        return;
      }
      const payload = {
        source: noteRunnerSource ? noteRunnerSource.value : '',
        stdin: noteRunnerStdin ? noteRunnerStdin.value : '',
        language: 'cpp17',
        notebook_slug: 'home-notes',
        card_id: currentRunnerNoteId,
      };

      noteRunnerRun.disabled = true;
      const previousLabel = noteRunnerRun.textContent;
      noteRunnerRun.textContent = 'RUNNING...';
      if (noteRunnerStatus) {
        noteRunnerStatus.textContent = 'Compiling...';
      }

      try {
        const response = await fetch('/_api/compile', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        const result = await response.json();
        persistCurrentRunnerState(result);
        setRunnerOutput(result);
      } catch (error) {
        const result = {
          ok: false,
          phase: 'network',
          error: `Request failed: ${error && error.message ? error.message : error}`,
        };
        persistCurrentRunnerState(result);
        if (noteRunnerCompileOutput) {
          noteRunnerCompileOutput.textContent = result.error;
        }
        if (noteRunnerRuntimeOutput) {
          noteRunnerRuntimeOutput.textContent = 'Program was not executed.';
        }
        if (noteRunnerStatus) {
          noteRunnerStatus.textContent = result.error;
        }
      } finally {
        noteRunnerRun.disabled = false;
        noteRunnerRun.textContent = previousLabel;
      }
    });
  }

  window.addEventListener('resize', resizeHomeNoteEditor);

  resetHomeNoteEditor();
  renderHomeNoteCards();

  const renderSaved = () => {
    if (!savedRoot) {
      return;
    }

    const entries = getSavedCards();
    const validEntries = entries
      .map((key) => ({ key, pair: cardMap.get(key) }))
      .filter((entry) => entry.pair);

    if (validEntries.length !== entries.length) {
      saveSavedCards(validEntries.map((entry) => entry.key));
    }

    if (savedCount) {
      savedCount.textContent = String(validEntries.length);
    }

    if (!validEntries.length) {
      savedRoot.innerHTML = '';
      if (savedEmpty) {
        savedEmpty.hidden = false;
      }
      return;
    }

    if (savedEmpty) {
      savedEmpty.hidden = true;
    }

    savedRoot.innerHTML = validEntries
      .map((entry) => {
        const notebook = entry.pair.notebook;
        const card = entry.pair.card;
        return `
          <article class="card-tile saved-card" data-saved-card data-key="${escapeHtml(entry.key)}">
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
              <button
                class="button-secondary"
                type="button"
                data-unsave-button
                data-key="${escapeHtml(entry.key)}"
              >
                Remove
              </button>
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
    if (
      !event.key
      || event.key.startsWith(getStoreKey('saved'))
      || event.key.startsWith(getStoreKey('notebook:'))
      || event.key.startsWith(getStoreKey('home-note:'))
    ) {
      renderHomeNoteCards();
      renderSaved();
      const activeNotebook = document.querySelector('[data-overview-root]');
      if (activeNotebook) {
        updateQuestionGrid(activeNotebook.dataset.notebookSlug);
        renderProgress(activeNotebook, activeNotebook.dataset.notebookSlug);
      }
    }
  });
}

function registerServiceWorker() {
  if (!('serviceWorker' in navigator)) {
    return;
  }

  if (!window.isSecureContext) {
    console.info('Service worker registration requires HTTPS or localhost.');
    return;
  }

  navigator.serviceWorker.register('/_static/sw.js').catch((error) => {
    console.warn('Service worker registration failed:', error);
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
    bindSavedPage();
    bindNotesPage();
    bindOverviewPage();
    bindCardPage();
    bindPlaygroundPanel();
    bindCppLab();
    bindNotePanel();
    registerServiceWorker();
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

    if matches:
        heading_matches = matches
        numbered = True
    else:
        heading_matches = list(GENERIC_CARD_HEADING_RE.finditer(text))
        numbered = False

    for index, match in enumerate(heading_matches):
        number = int(match.group(1)) if numbered else index + 1
        title = match.group(2).strip() if numbered else match.group(1).strip()
        body_start = match.end()
        body_end = heading_matches[index + 1].start() if index + \
            1 < len(heading_matches) else len(text)
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
        raw = "\n".join(buffer).strip("\n")
        if raw.strip():
            sections.append(
                Section(
                    title=current_title or "内容",
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
    ordered_list_items: List[str] = []
    blockquote: List[str] = []
    table_rows: List[List[str]] = []
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
        nonlocal list_items, ordered_list_items
        if list_items:
            items = "".join(
                f"<li>{render_inline(item)}</li>" for item in list_items)
            output.append(f"<ul>{items}</ul>")
        list_items = []
        if ordered_list_items:
            items = "".join(
                f"<li>{render_inline(item)}</li>" for item in ordered_list_items)
            output.append(f"<ol>{items}</ol>")
        ordered_list_items = []

    def flush_blockquote() -> None:
        nonlocal blockquote
        if blockquote:
            body = render_markdown("\n".join(blockquote))
            output.append(f"<blockquote>{body}</blockquote>")
        blockquote = []

    def flush_table() -> None:
        nonlocal table_rows
        if len(table_rows) < 2:
            for row in table_rows:
                output.append(f"<p>{render_inline(' | '.join(row))}</p>")
            table_rows = []
            return

        header = table_rows[0]
        body_rows = table_rows[2:] if is_markdown_table_separator(table_rows[1]) else table_rows[1:]
        head_html = "".join(f"<th>{render_inline(cell)}</th>" for cell in header)
        body_html = "".join(
            "<tr>" + "".join(f"<td>{render_inline(cell)}</td>" for cell in row) + "</tr>"
            for row in body_rows
        )
        output.append(
            "<div class=\"table-wrap\"><table>"
            f"<thead><tr>{head_html}</tr></thead>"
            f"<tbody>{body_html}</tbody>"
            "</table></div>"
        )
        table_rows = []

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
            flush_blockquote()
            flush_table()
            continue

        table_row = parse_markdown_table_row(stripped)
        if table_row is not None:
            flush_paragraph()
            flush_list()
            flush_blockquote()
            table_rows.append(table_row)
            continue

        flush_table()

        if stripped in {"---", "***", "___"}:
            flush_paragraph()
            flush_list()
            flush_blockquote()
            output.append("<hr>")
            continue

        if stripped.startswith(">"):
            flush_paragraph()
            flush_list()
            quote_line = stripped[1:].strip()
            blockquote.append(quote_line)
            continue

        flush_blockquote()

        heading = re.match(r"^(#{3,6})\s+(.+?)\s*$", stripped)
        if heading:
            flush_paragraph()
            flush_list()
            level = len(heading.group(1))
            output.append(
                f"<h{level}>{render_inline(heading.group(2).strip())}</h{level}>")
            continue

        bullet = LIST_ITEM_RE.match(line)
        if bullet:
            flush_paragraph()
            flush_blockquote()
            list_items.append(bullet.group(1).strip())
            continue

        ordered = ORDERED_LIST_ITEM_RE.match(line)
        if ordered:
            flush_paragraph()
            flush_blockquote()
            ordered_list_items.append(ordered.group(1).strip())
            continue

        if list_items and line.startswith("  "):
            list_items[-1] = f"{list_items[-1]} {stripped}"
            continue
        if ordered_list_items and line.startswith("  "):
            ordered_list_items[-1] = f"{ordered_list_items[-1]} {stripped}"
            continue

        flush_list()
        paragraph.append(stripped)

    if in_code:
        flush_code()

    flush_paragraph()
    flush_list()
    flush_blockquote()
    flush_table()
    return "".join(output)


def parse_markdown_table_row(line: str) -> Optional[List[str]]:
    if "|" not in line:
        return None
    stripped = line.strip()
    if not stripped.startswith("|"):
        return None
    cells = stripped.strip("|").split("|")
    return [cell.strip() for cell in cells]


def is_markdown_table_separator(row: Sequence[str]) -> bool:
    return all(re.fullmatch(r":?-{3,}:?", cell.strip()) for cell in row)


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


def boot_payload(
    notebooks: Sequence[Notebook],
    persistent_state: Optional[Dict[str, object]] = None,
) -> Dict[str, object]:
    return {
        "notebooks": [notebook_payload(notebook) for notebook in notebooks],
        "persistentState": persistent_state or {"saved_cards": [], "notebooks": {}, "notes": {}, "home_notes": {}},
    }


def truncate_text(text: str, limit: int = MAX_CAPTURED_OUTPUT_CHARS) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "\n[output truncated]"


def empty_resource_metrics() -> Dict[str, object]:
    return {
        "available": False,
        "wall_seconds": None,
        "user_seconds": None,
        "sys_seconds": None,
        "cpu_percent": None,
        "max_rss_kb": None,
        "minor_page_faults": None,
        "major_page_faults": None,
        "voluntary_context_switches": None,
        "involuntary_context_switches": None,
    }


def parse_resource_time_metrics(metrics_path: Path) -> Dict[str, object]:
    metrics = empty_resource_metrics()
    try:
        raw_metrics = metrics_path.read_text(encoding="utf-8")
    except OSError:
        return metrics

    for line in raw_metrics.splitlines():
        key, separator, value = line.partition("=")
        if not separator:
            continue
        key = key.strip()
        value = value.strip()
        if key in {"wall_seconds", "user_seconds", "sys_seconds"}:
            try:
                metrics[key] = float(value)
            except ValueError:
                metrics[key] = None
        elif key == "cpu_percent":
            try:
                metrics[key] = float(value.rstrip("%"))
            except ValueError:
                metrics[key] = None
        elif key in {
            "max_rss_kb",
            "minor_page_faults",
            "major_page_faults",
            "voluntary_context_switches",
            "involuntary_context_switches",
        }:
            try:
                metrics[key] = int(value)
            except ValueError:
                metrics[key] = None

    metrics["available"] = any(value is not None for key, value in metrics.items() if key != "available")
    return metrics


def resource_time_command(command: Sequence[str], metrics_path: Path) -> List[str]:
    if not Path(RESOURCE_TIME_BIN).exists():
        return list(command)
    return [
        RESOURCE_TIME_BIN,
        "-f",
        RESOURCE_TIME_FORMAT,
        "-o",
        str(metrics_path),
        *command,
    ]


def run_resource_tracked_command(
    command: Sequence[str],
    cwd: str,
    timeout_seconds: int,
    metrics_path: Path,
    stdin_data: Optional[str] = None,
) -> Tuple[Optional[int], str, str, bool]:
    proc = subprocess.Popen(
        resource_time_command(command, metrics_path),
        cwd=cwd,
        stdin=subprocess.PIPE if stdin_data is not None else subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        stdout, stderr = proc.communicate(input=stdin_data, timeout=timeout_seconds)
        timed_out = False
    except subprocess.TimeoutExpired:
        timed_out = True
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        stdout, stderr = proc.communicate()
    return proc.returncode, stdout or "", stderr or "", timed_out


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
        compile_metrics_path = tmp_path / "compile_metrics.txt"
        run_metrics_path = tmp_path / "run_metrics.txt"
        source_path.write_text(source, encoding="utf-8")

        compile_cmd = [
            "g++",
            "-std=c++17",
            "-O0",
            "-pipe",
            "-Wall",
            "-Wextra",
            "-pedantic",
            "-pthread",
            str(source_path),
            "-o",
            str(executable_path),
        ]
        compile_returncode, compile_stdout_raw, compile_stderr_raw, compile_timed_out = run_resource_tracked_command(
            compile_cmd,
            cwd=tmpdir,
            timeout_seconds=COMPILE_TIMEOUT_SECONDS,
            metrics_path=compile_metrics_path,
        )
        if compile_timed_out:
            return {
                "ok": False,
                "phase": "compile",
                "compiled": False,
                "compile_returncode": None,
                "compile_stdout": truncate_text(compile_stdout_raw),
                "compile_stderr": truncate_text(
                    compile_stderr_raw
                    + f"\nCompilation timed out after {COMPILE_TIMEOUT_SECONDS} seconds."
                ),
                "compile_metrics": parse_resource_time_metrics(compile_metrics_path),
                "run_returncode": None,
                "run_stdout": "",
                "run_stderr": "",
                "run_timed_out": False,
                "run_metrics": empty_resource_metrics(),
            }

        compile_stdout = truncate_text(compile_stdout_raw)
        compile_stderr = truncate_text(compile_stderr_raw)
        compile_metrics = parse_resource_time_metrics(compile_metrics_path)

        if compile_returncode != 0:
            return {
                "ok": False,
                "phase": "compile",
                "compiled": False,
                "compile_returncode": compile_returncode,
                "compile_stdout": compile_stdout,
                "compile_stderr": compile_stderr,
                "compile_metrics": compile_metrics,
                "run_returncode": None,
                "run_stdout": "",
                "run_stderr": "",
                "run_timed_out": False,
                "run_metrics": empty_resource_metrics(),
            }

        run_returncode, run_stdout_raw, run_stderr_raw, run_timed_out = run_resource_tracked_command(
            [str(executable_path)],
            cwd=tmpdir,
            timeout_seconds=RUN_TIMEOUT_SECONDS,
            metrics_path=run_metrics_path,
            stdin_data=stdin_data,
        )

        run_stdout = truncate_text(run_stdout_raw)
        run_stderr = truncate_text(run_stderr_raw)
        if run_timed_out:
            run_stderr = (run_stderr + "\n" if run_stderr else "") + \
                f"Execution timed out after {RUN_TIMEOUT_SECONDS} seconds."

        return {
            "ok": (not run_timed_out) and run_returncode == 0,
            "phase": "run",
            "compiled": True,
            "compile_returncode": compile_returncode,
            "compile_stdout": compile_stdout,
            "compile_stderr": compile_stderr,
            "compile_metrics": compile_metrics,
            "run_returncode": run_returncode,
            "run_stdout": run_stdout,
            "run_stderr": run_stderr,
            "run_timed_out": run_timed_out,
            "run_metrics": parse_resource_time_metrics(run_metrics_path),
        }


def is_cpp_lab_file(path: Path) -> bool:
    return path.name in CPP_LAB_FILE_NAMES or path.suffix.lower() in CPP_LAB_EXTENSIONS


def is_cpp_lab_source_file(path: Path) -> bool:
    return path.suffix.lower() in CPP_LAB_SOURCE_EXTENSIONS


def cpp_lab_relative_path(path: Path, root: Optional[Path] = None) -> str:
    root = root or CPP_LAB_ROOT
    resolved_root = root.resolve()
    resolved_path = (resolved_root / path).resolve() if not path.is_absolute() else path.resolve()
    try:
        relative = resolved_path.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError("Path must stay inside the C++ lab project.") from exc
    if not relative.parts or any(part in {"", ".", ".."} for part in relative.parts):
        raise ValueError("Invalid file path.")
    if any(part in CODE_PROJECT_EXCLUDED_DIRS for part in relative.parts[:-1]):
        raise ValueError("Path is excluded from editing.")
    if not is_cpp_lab_file(resolved_path):
        raise ValueError("File type is not editable in the C++ lab.")
    return relative.as_posix()


def cpp_lab_file_path(relative_path: str, root: Optional[Path] = None) -> Path:
    root = root or CPP_LAB_ROOT
    relative = cpp_lab_relative_path(Path(relative_path), root)
    return (root.resolve() / relative).resolve()


def cpp_lab_files(root: Optional[Path] = None) -> Tuple[CodeFile, ...]:
    root = root or CPP_LAB_ROOT
    if not root.exists():
        return ()

    files: List[CodeFile] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or not is_cpp_lab_file(path):
            continue
        try:
            relative_path = cpp_lab_relative_path(path, root)
        except ValueError:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        files.append(
            CodeFile(
                relative_path=relative_path,
                language=code_file_language(relative_path),
                content=content,
            )
        )
    return tuple(files)


def cpp_lab_default_file(files: Sequence[CodeFile]) -> str:
    if any(file.relative_path == CPP_LAB_MAIN_FILE for file in files):
        return CPP_LAB_MAIN_FILE
    return files[0].relative_path if files else CPP_LAB_MAIN_FILE


def read_cpp_lab_file(relative_path: str, root: Optional[Path] = None) -> CodeFile:
    root = root or CPP_LAB_ROOT
    path = cpp_lab_file_path(relative_path, root)
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(relative_path)
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        content = path.read_text(encoding="utf-8", errors="replace")
    return CodeFile(
        relative_path=cpp_lab_relative_path(path, root),
        language=code_file_language(path.name),
        content=content,
    )


def save_cpp_lab_file(relative_path: str, content: str, root: Optional[Path] = None) -> CodeFile:
    root = root or CPP_LAB_ROOT
    if len(content) > MAX_SOURCE_CHARS:
        raise ValueError(f"Source too large; limit is {MAX_SOURCE_CHARS} characters.")
    path = cpp_lab_file_path(relative_path, root)
    if not path.parent.exists():
        raise ValueError("Parent directory does not exist.")
    path.write_text(content, encoding="utf-8")
    return read_cpp_lab_file(relative_path, root)


def compile_cpp_lab_project(
    stdin_data: str = "",
    root: Optional[Path] = None,
    runnable_path: Optional[str] = None,
) -> Dict[str, object]:
    root = root or CPP_LAB_ROOT
    if runnable_path is None:
        runnable_path = cpp_lab_default_file(cpp_lab_files(root))
    source_path = cpp_lab_file_path(runnable_path, root)
    relative_source_path = cpp_lab_relative_path(source_path, root)
    if not is_cpp_lab_source_file(source_path):
        return {
            "ok": False,
            "phase": "validation",
            "error": f"Selected file is not runnable C++ source: {relative_source_path}",
            "runnable_file": relative_source_path,
        }
    if not source_path.exists():
        return {
            "ok": False,
            "phase": "validation",
            "error": f"Missing runnable file: {relative_source_path}",
            "runnable_file": relative_source_path,
        }

    with tempfile.TemporaryDirectory(prefix="cpp_lab_compile_") as tmpdir:
        tmp_path = Path(tmpdir)
        executable_path = tmp_path / "main.out"
        compile_metrics_path = tmp_path / "compile_metrics.txt"
        run_metrics_path = tmp_path / "run_metrics.txt"
        compile_cmd = [
            "g++",
            "-std=c++17",
            "-O0",
            "-pipe",
            "-Wall",
            "-Wextra",
            "-pedantic",
            "-pthread",
            str(source_path),
            "-o",
            str(executable_path),
        ]
        compile_returncode, compile_stdout_raw, compile_stderr_raw, compile_timed_out = run_resource_tracked_command(
            compile_cmd,
            cwd=str(root),
            timeout_seconds=COMPILE_TIMEOUT_SECONDS,
            metrics_path=compile_metrics_path,
        )
        if compile_timed_out:
            return {
                "ok": False,
                "phase": "compile",
                "compiled": False,
                "compile_returncode": None,
                "compile_stdout": truncate_text(compile_stdout_raw),
                "compile_stderr": truncate_text(
                    compile_stderr_raw
                    + f"\nCompilation timed out after {COMPILE_TIMEOUT_SECONDS} seconds."
                ),
                "compile_metrics": parse_resource_time_metrics(compile_metrics_path),
                "run_returncode": None,
                "run_stdout": "",
                "run_stderr": "",
                "run_timed_out": False,
                "run_metrics": empty_resource_metrics(),
                "runnable_file": relative_source_path,
            }

        compile_stdout = truncate_text(compile_stdout_raw)
        compile_stderr = truncate_text(compile_stderr_raw)
        compile_metrics = parse_resource_time_metrics(compile_metrics_path)
        if compile_returncode != 0:
            return {
                "ok": False,
                "phase": "compile",
                "compiled": False,
                "compile_returncode": compile_returncode,
                "compile_stdout": compile_stdout,
                "compile_stderr": compile_stderr,
                "compile_metrics": compile_metrics,
                "run_returncode": None,
                "run_stdout": "",
                "run_stderr": "",
                "run_timed_out": False,
                "run_metrics": empty_resource_metrics(),
                "runnable_file": relative_source_path,
            }

        run_returncode, run_stdout_raw, run_stderr_raw, run_timed_out = run_resource_tracked_command(
            [str(executable_path)],
            cwd=str(root),
            timeout_seconds=RUN_TIMEOUT_SECONDS,
            metrics_path=run_metrics_path,
            stdin_data=stdin_data,
        )

        run_stdout = truncate_text(run_stdout_raw)
        run_stderr = truncate_text(run_stderr_raw)
        if run_timed_out:
            run_stderr = (run_stderr + "\n" if run_stderr else "") + \
                f"Execution timed out after {RUN_TIMEOUT_SECONDS} seconds."

        return {
            "ok": (not run_timed_out) and run_returncode == 0,
            "phase": "run",
            "compiled": True,
            "compile_returncode": compile_returncode,
            "compile_stdout": compile_stdout,
            "compile_stderr": compile_stderr,
            "compile_metrics": compile_metrics,
            "run_returncode": run_returncode,
            "run_stdout": run_stdout,
            "run_stderr": run_stderr,
            "run_timed_out": run_timed_out,
            "run_metrics": parse_resource_time_metrics(run_metrics_path),
            "runnable_file": relative_source_path,
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
    return (
        state_dir
        / "note-attachments"
        / safe_slug_path_component(notebook_slug)
        / safe_slug_path_component(str(card_id))
    )


def note_attachment_url(notebook_slug: str, card_id: str, filename: str) -> str:
    return (
        f"/_attachments/{safe_slug_path_component(notebook_slug)}"
        f"/{safe_slug_path_component(str(card_id))}/{filename}"
    )


def save_note_attachment_file(
    state_dir: Path,
    notebook_slug: str,
    card_id: str,
    filename: str,
    data: bytes,
    mime_type: str,
) -> Dict[str, object]:
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


def delete_note_attachment_tree(state_dir: Path, notebook_slug: str, card_id: str) -> None:
    attachment_dir = note_attachment_dir(state_dir, notebook_slug, card_id)
    try:
        shutil.rmtree(attachment_dir)
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


def flashcards_url(notebook: Notebook) -> str:
    return f"/{notebook.spec.slug}/cards"


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
  <meta name="theme-color" content="{PWA_THEME_COLOR}">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="default">
  <meta name="apple-mobile-web-app-title" content="{html.escape(PWA_SHORT_NAME, quote=True)}">
  <title>{html.escape(title)}</title>
  <link rel="manifest" href="{PWA_MANIFEST_PATH}">
  <link rel="apple-touch-icon" href="{PWA_ICON_180_PATH}">
  <link rel="icon" type="image/png" sizes="180x180" href="{PWA_ICON_180_PATH}">
  <link rel="icon" type="image/png" sizes="512x512" href="{PWA_ICON_512_PATH}">
  <link rel="stylesheet" href="/_static/app.css">
  {extra_head}
</head>
<body>
  {body}
  {boot_script}
  <script src="/_static/app.js" defer></script>
</body>
</html>"""


def nav_label(notebook: Notebook) -> str:
    words = notebook.spec.slug.replace("-", " ").split()
    return " ".join(word.capitalize() for word in words)


def notebook_default_url(notebook: Notebook) -> str:
    return overview_url(notebook)


def render_top_nav(notebooks: Sequence[Notebook], active: str = "home") -> str:
    notebook_links = "".join(
        f'<a class="top-nav-link {"is-active" if active == notebook.spec.slug else ""}" '
        f'href="{notebook_default_url(notebook)}">{html.escape(nav_label(notebook))}</a>'
        for notebook in notebooks
    )
    return f"""
      <nav class="top-nav" aria-label="Primary">
        <a class="top-nav-link {"is-active" if active == "home" else ""}" href="/">Home</a>
        {notebook_links}
        <a class="top-nav-link {"is-active" if active == CODE_READING_SLUG else ""}" href="/{CODE_READING_SLUG}">Code Reading</a>
        <a class="top-nav-link {"is-active" if active == CPP_LAB_SLUG else ""}" href="/{CPP_LAB_SLUG}">C++ Lab</a>
        <a class="top-nav-link {"is-active" if active == "saved" else ""}" href="/saved">Saved</a>
        <a class="top-nav-link {"is-active" if active == "notes" else ""}" href="/notes">My Notes</a>
      </nav>
    """


def saved_card_entries(
    notebooks: Sequence[Notebook],
    persistent_state: Optional[Dict[str, object]],
) -> Tuple[List[str], List[str]]:
    card_lookup = {}
    for notebook in notebooks:
        for card in notebook.cards:
            card_lookup[f"{notebook.spec.slug}:{card.number}"] = (
                notebook, card)

    saved_entries: List[str] = []
    valid_saved_keys: List[str] = []
    saved_state_root = (persistent_state or {}).get(
        "saved_cards", []) if persistent_state else []
    if isinstance(saved_state_root, list):
        for key in saved_state_root:
            pair = card_lookup.get(str(key))
            if pair is None:
                continue
            valid_saved_keys.append(str(key))
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
    return saved_entries, valid_saved_keys


def home_note_entries(persistent_state: Optional[Dict[str, object]]) -> List[str]:
    entries = []
    home_note_state_root = (persistent_state or {}).get(
        "home_notes", {}) if persistent_state else {}
    if isinstance(home_note_state_root, dict):
        for note_id, note_state in home_note_state_root.items():
            if not isinstance(note_state, dict):
                continue
            title = note_state.get("title", "")
            text = note_state.get("text", "")
            attachments = note_state.get("attachments", [])
            created_at = note_state.get("createdAt", "")
            updated_at = note_state.get("updatedAt", "")
            note_type = note_state.get("type", "text")
            if not isinstance(note_type, str) or note_type not in {"text", "cpp"}:
                note_type = "text"
            if not isinstance(title, str):
                title = ""
            if not isinstance(text, str):
                text = ""
            if not isinstance(attachments, list):
                attachments = []
            if not title.strip() and not text.strip() and not attachments:
                continue
            preview = first_paragraph(text) if text.strip(
            ) else f"{len(attachments)} attachment(s)"
            is_code = note_type == "cpp"
            secondary_tag = '<span class="tag">cpp17</span>' if is_code else f'<span class="tag">{len(attachments)} attachments</span>'
            run_button = (
                f'<button class="button" type="button" data-home-note-run data-note-id="{html.escape(str(note_id), quote=True)}">RUN C++</button>'
                if is_code
                else ""
            )
            entries.append(
                {
                    "updatedAt": updated_at if isinstance(updated_at, str) else "",
                    "createdAt": created_at if isinstance(created_at, str) else "",
                    "html": f"""
                      <article class="card-tile note-card home-note-card" data-home-note-card data-note-id="{html.escape(str(note_id), quote=True)}">
                        <div class="card-meta">
                          <span class="card-number">N</span>
                          <span data-home-note-time>{html.escape((updated_at or created_at)[:19].replace("T", " ") if isinstance(updated_at or created_at, str) else "")}</span>
                        </div>
                        <h3>{html.escape(title.strip() or "Untitled note")}</h3>
                        <p class="card-preview">{html.escape(preview)}</p>
                        <div class="tag-row">
                          <span class="tag">{"C++ code" if is_code else "text note"}</span>
                          {secondary_tag}
                        </div>
                        <div class="reveal-actions">
                          <button class="button" type="button" data-home-note-edit data-note-id="{html.escape(str(note_id), quote=True)}">Edit</button>
                          {run_button}
                          <button class="button-secondary" type="button" data-home-note-delete data-note-id="{html.escape(str(note_id), quote=True)}">Delete</button>
                        </div>
                      </article>
                    """,
                }
            )
    entries.sort(
        key=lambda entry: entry.get("updatedAt", "") or entry.get("createdAt", ""),
        reverse=True,
    )
    return [entry["html"] for entry in entries]


def render_cpp_lab_page(notebooks: Sequence[Notebook]) -> str:
    files = cpp_lab_files()
    default_file = cpp_lab_default_file(files)
    options = "".join(
        f'<option value="{html.escape(file.relative_path, quote=True)}" {"selected" if file.relative_path == default_file else ""}>{html.escape(file.relative_path)}</option>'
        for file in files
    )
    if not options:
        options = f'<option value="{CPP_LAB_MAIN_FILE}">{CPP_LAB_MAIN_FILE}</option>'

    body = f"""
    <div class="app-shell" data-cpp-lab-root>
      <section class="hero">
        <div>
          <p class="eyebrow">C++ code lab</p>
          <h1>C++ Lab</h1>
          <p class="lede">Edit files from `cpp_awssome_project/random_pj` with CodeMirror 6, save changes to disk, and run the selected C++ source with g++.</p>
        </div>
        <div class="hero-card">
          <div class="stat">{len(files)}</div>
          <div class="stat-label">files</div>
        </div>
      </section>
      {render_top_nav(notebooks, CPP_LAB_SLUG)}
      <section class="cpp-lab-shell">
        <div class="cpp-lab-toolbar">
          <select class="cpp-lab-file-select" data-cpp-lab-file-select aria-label="C++ lab file">
            {options}
          </select>
          <div class="cpp-lab-actions">
            <span class="cpp-lab-shortcuts">Alt+C run · Ctrl+Enter run · Ctrl+S save · Ctrl+/ comment</span>
            <button class="button-secondary" type="button" data-cpp-lab-save title="Save current file (Ctrl+S)">Save</button>
            <button class="button" type="button" data-cpp-lab-run data-cpp-lab-run-shortcut accesskey="c" title="Save dirty files and run the selected C++ source (Alt+C)">Run Alt+C</button>
            <button class="button-secondary" type="button" data-cpp-lab-clear>Clear</button>
          </div>
        </div>
        <div class="cpp-lab-status" data-cpp-lab-status>Loading project...</div>
        <div class="cpp-lab-layout">
          <section class="cpp-lab-pane" data-cpp-lab-editor-pane>
            <div class="cpp-lab-pane-head">
              <div class="cpp-lab-title">Code</div>
              <button class="button-secondary" type="button" data-cpp-lab-editor-theme aria-pressed="false">Dark</button>
            </div>
            <div class="cpp-lab-editor-wrap">
              <div class="cpp-lab-editor-mount" data-cpp-lab-editor-mount aria-label="C++ source editor"></div>
            </div>
          </section>
          <section class="cpp-lab-pane" data-cpp-lab-output-pane>
            <div class="cpp-lab-pane-head">
              <div class="cpp-lab-title">Output</div>
              <button class="button-secondary" type="button" data-cpp-lab-output-theme aria-pressed="false">Dark</button>
            </div>
            <pre class="cpp-lab-output" data-cpp-lab-output>Run code to see output.</pre>
          </section>
        </div>
      </section>
    </div>
    """
    return render_page("C++ Lab", body, boot_data=boot_payload(notebooks))


def render_home(notebooks: Sequence[Notebook], persistent_state: Optional[Dict[str, object]] = None) -> str:
    tiles = []
    for notebook in notebooks:
        card_count = len(notebook.cards)
        tiles.append(
            f"""
            <a class="card-tile" href="{overview_url(notebook)}">
              <div class="card-meta">
                <span class="card-number">{card_count}</span>
                <span>{card_count} cards</span>
              </div>
              <h3>{html.escape(notebook.spec.title)}</h3>
              <p class="card-preview">{html.escape(notebook.spec.description)}</p>
            </a>
            """
        )

    lab_files = cpp_lab_files()
    tiles.append(
        f"""
        <a class="card-tile" href="/{CPP_LAB_SLUG}">
          <div class="card-meta">
            <span class="card-number">{len(lab_files)}</span>
            <span>{len(lab_files)} files</span>
          </div>
          <h3>C++ Lab</h3>
          <p class="card-preview">Edit and run the files in cpp_awssome_project/random_pj directly from the browser.</p>
          <div class="tag-row">
            <span class="tag">editor</span>
            <span class="tag">g++</span>
          </div>
        </a>
        """
    )

    body = f"""
    <div class="app-shell" data-home-root data-notebook-root data-total-cards="{sum(len(n.cards) for n in notebooks)}">
      <section class="hero">
        <div>
          <p class="eyebrow">C++ interview practice</p>
          <h1>C++ 学习笔记卡片站</h1>
          <p class="lede">按难度和专题复习 C++ 面试题，集中管理学习进度、收藏题目和个人笔记。</p>
        </div>
        <div class="hero-card">
          <div class="stat">{len(notebooks)}</div>
          <div class="stat-label">notebooks</div>
        </div>
      </section>
      {render_top_nav(notebooks, "home")}
      <section class="overview-grid">
        {''.join(tiles)}
      </section>
    </div>
    """

    return render_page("C++ 学习笔记卡片站", body, boot_data=boot_payload(notebooks, persistent_state))


def render_notes_page(notebooks: Sequence[Notebook], persistent_state: Optional[Dict[str, object]] = None) -> str:
    note_tiles = home_note_entries(persistent_state)
    body = f"""
    <div class="app-shell" data-notes-root>
      <section class="hero">
        <div>
          <p class="eyebrow">Personal notes</p>
          <h1>My Notes</h1>
          <p class="lede">记录临时想法、复习日志、截图和代码片段。最新更新会排在最前面。</p>
        </div>
        <div class="hero-card">
          <div class="stat"><strong data-home-note-count>{len(note_tiles)}</strong></div>
          <div class="stat-label">notes</div>
        </div>
      </section>
      {render_top_nav(notebooks, "notes")}
      <section class="home-note-shell">
        <div class="home-collection-head">
          <div class="card-meta">
            <span class="muted">My Notes</span>
            <span class="muted"><strong data-home-note-count>{len(note_tiles)}</strong> notes</span>
          </div>
          <div class="home-collection-actions">
            <button class="button" type="button" data-home-note-new>New note</button>
          </div>
        </div>
        <div class="home-note-composer" data-home-note-composer>
          <input class="home-note-title" type="text" data-home-note-title placeholder="Title">
          <div class="note-type-row" role="radiogroup" aria-label="Note type">
            <label class="note-type-option">
              <input type="radio" name="home-note-type" value="text" data-home-note-type checked>
              <span>Text</span>
            </label>
            <label class="note-type-option">
              <input type="radio" name="home-note-type" value="cpp" data-home-note-type>
              <span>C++ Code</span>
            </label>
          </div>
          <textarea
            class="note-editor home-note-editor"
            data-home-note-text
            placeholder="Write a note. Paste text or screenshots with Ctrl+V. Markdown code blocks like ```cpp are displayed in preview."
          ></textarea>
          <div class="reveal-actions note-actions">
            <button class="button" type="button" data-home-note-save>Save note</button>
            <button class="button-secondary" type="button" data-home-note-clear>Clear editor</button>
            <button class="button-secondary" type="button" data-home-note-delete-current hidden>Delete note</button>
            <span class="note-status" data-home-note-status>Draft</span>
          </div>
          <section class="note-preview-shell" data-home-note-preview-shell>
            <div class="note-section-head">Preview</div>
            <div class="note-preview" data-home-note-preview></div>
          </section>
          <section class="note-attachments-shell" data-home-note-attachments-shell>
            <div class="note-section-head">Attachments</div>
            <div class="note-attachments" data-home-note-attachments></div>
          </section>
        </div>
        <p class="saved-empty" data-home-note-empty {'hidden' if note_tiles else ''}>还没有 note。点击 New note，写标题和正文后保存。</p>
        <div class="overview-grid saved-grid" data-home-note-list>{''.join(note_tiles)}</div>
      </section>
      <div class="playground-backdrop" data-note-runner-backdrop hidden></div>
      <aside class="playground-drawer" data-note-runner-root aria-label="My Notes C++ runner" aria-hidden="true">
        <div class="playground-shell">
          <div class="playground-head">
            <div>
              <div class="playground-title">My Notes C++ Runner</div>
              <div class="playground-subtitle">Compiles locally with `g++ -std=c++17`.</div>
            </div>
            <button class="button-secondary" type="button" data-note-runner-close>Close</button>
          </div>
          <div class="playground-toolbar">
            <button class="button-secondary" type="button" data-note-runner-save>Save back to note</button>
            <button class="button" type="button" data-note-runner-run>RUN</button>
          </div>
          <div class="playground-runner-layout">
            <div class="playground-runner-code">
              <label class="playground-label" for="note-runner-source">Code</label>
              <textarea
                id="note-runner-source"
                class="playground-editor"
                data-note-runner-source
                spellcheck="false"
                autocomplete="off"
                autocapitalize="off"
                autocorrect="off"
              ></textarea>
            </div>
            <div class="playground-runner-side">
              <label class="playground-label" for="note-runner-stdin">stdin</label>
              <textarea
                id="note-runner-stdin"
                class="playground-stdin"
                data-note-runner-stdin
                spellcheck="false"
                autocomplete="off"
                autocapitalize="off"
                autocorrect="off"
                placeholder="Optional standard input"
              ></textarea>
              <div class="playground-output-grid">
                <section class="playground-section">
                  <div class="playground-section-head">Compile output</div>
                  <pre class="playground-output" data-note-runner-compile-output>Waiting for code...</pre>
                </section>
                <section class="playground-section">
                  <div class="playground-section-head">Runtime output</div>
                  <pre class="playground-output" data-note-runner-runtime-output>RUN to see output.</pre>
                </section>
              </div>
            </div>
          </div>
          <div class="playground-status" data-note-runner-status>Closed</div>
        </div>
      </aside>
    </div>
    """
    return render_page("My Notes", body, boot_data=boot_payload(notebooks, persistent_state))


def render_saved_page(notebooks: Sequence[Notebook], persistent_state: Optional[Dict[str, object]] = None) -> str:
    saved_entries, valid_saved_keys = saved_card_entries(
        notebooks, persistent_state)
    saved_state = persistent_state
    if isinstance(persistent_state, dict):
        saved_state = dict(persistent_state)
        saved_state["saved_cards"] = valid_saved_keys
    body = f"""
    <div class="app-shell" data-saved-page-root>
      <section class="hero">
        <div>
          <p class="eyebrow">Saved cards</p>
          <h1>Saved</h1>
          <p class="lede">集中查看已经收藏的题目，适合面试前快速复盘。</p>
        </div>
        <div class="hero-card">
          <div class="stat"><strong data-saved-count>{len(saved_entries)}</strong></div>
          <div class="stat-label">saved</div>
        </div>
      </section>
      {render_top_nav(notebooks, "saved")}
      <p class="saved-empty" data-saved-empty {'hidden' if saved_entries else ''}>你还没有保存任何题目。点开题目页里的 SAVE 就会出现在这里。</p>
      <section class="overview-grid saved-grid" data-saved-root>
        {''.join(saved_entries)}
      </section>
    </div>
    """
    return render_page("Saved Cards", body, boot_data=boot_payload(notebooks, saved_state))


def is_code_project_file(path: Path) -> bool:
    return path.name in CODE_PROJECT_FILE_NAMES or path.suffix.lower() in CODE_PROJECT_EXTENSIONS


def code_file_language(path: str) -> str:
    if path.endswith("CMakeLists.txt"):
        return "cmake"
    suffix = Path(path).suffix.lower()
    if suffix in {".h", ".hpp", ".hh", ".hxx"}:
        return "cpp"
    if suffix in {".cpp", ".cc", ".cxx"}:
        return "cpp"
    return "text"


def is_excluded_code_path(path: Path, project_root: Path) -> bool:
    try:
        relative = path.relative_to(project_root)
    except ValueError:
        return True
    return any(part in CODE_PROJECT_EXCLUDED_DIRS for part in relative.parts[:-1])


def path_is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def discover_code_project_roots(base: Path = CODE_PROJECT_ROOT) -> List[Path]:
    if not base.exists():
        return []

    roots: List[Path] = []
    for cmake_file in sorted(base.rglob("CMakeLists.txt")):
        if any(part in CODE_PROJECT_EXCLUDED_DIRS for part in cmake_file.relative_to(base).parts[:-1]):
            continue
        project_root = cmake_file.parent
        if any(project_root == root or path_is_relative_to(project_root, root) for root in roots):
            continue
        roots.append(project_root)
    return roots


def load_code_project(root: Path, number: int) -> CodeProject:
    files: List[CodeFile] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or not is_code_project_file(path):
            continue
        if is_excluded_code_path(path, root):
            continue
        relative_path = path.relative_to(root).as_posix()
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        files.append(
            CodeFile(
                relative_path=relative_path,
                language=code_file_language(relative_path),
                content=content,
            )
        )
    slug = safe_slug_path_component(root.relative_to(CODE_PROJECT_ROOT).as_posix())
    return CodeProject(
        number=number,
        slug=slug,
        title=root.name,
        root_path=root,
        files=tuple(files),
    )


def code_projects() -> Tuple[CodeProject, ...]:
    return tuple(
        load_code_project(root, index + 1)
        for index, root in enumerate(discover_code_project_roots())
    )


def code_project_url(project: CodeProject) -> str:
    return f"/{CODE_READING_SLUG}/{project.slug}"


def code_project_by_slug(projects: Sequence[CodeProject], slug: str) -> CodeProject:
    for project in projects:
        if project.slug == slug:
            return project
    raise KeyError(slug)


CPP_KEYWORDS = {
    "alignas", "alignof", "asm", "auto", "break", "case", "catch", "class",
    "concept", "const", "consteval", "constexpr", "constinit", "continue",
    "co_await", "co_return", "co_yield", "decltype", "default", "delete", "do",
    "else", "enum", "explicit", "export", "extern", "final", "for", "friend",
    "goto", "if", "inline", "mutable", "namespace", "new", "noexcept",
    "operator", "override", "private", "protected", "public", "requires",
    "return", "sizeof", "static", "static_assert", "struct", "switch",
    "template", "this", "thread_local", "throw", "try", "typedef", "typeid",
    "typename", "union", "using", "virtual", "volatile", "while",
}

CPP_TYPES = {
    "bool", "char", "char8_t", "char16_t", "char32_t", "double", "float",
    "int", "long", "short", "signed", "unsigned", "void", "wchar_t",
    "size_t", "std", "string", "vector", "queue", "deque", "map", "set",
    "unordered_map", "unordered_set", "unique_ptr", "shared_ptr", "weak_ptr",
    "mutex", "lock_guard", "unique_lock", "condition_variable", "thread",
    "atomic", "future", "optional", "variant", "function",
}

CMAKE_KEYWORDS = {
    "add_executable", "add_library", "add_subdirectory", "add_test",
    "cmake_minimum_required", "enable_testing", "find_package", "include",
    "message", "project", "set", "target_compile_features",
    "target_compile_options", "target_include_directories",
    "target_link_libraries",
}


def code_span(css_class: str, value: str) -> str:
    return f'<span class="{css_class}">{html.escape(value)}</span>'


def highlight_cpp_code(source: str) -> str:
    token_re = re.compile(
        r"""
        (?P<comment>//[^\n]*|/\*.*?\*/)
        |(?P<string>"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')
        |(?P<preprocessor>^[ \t]*\#[^\n]*)
        |(?P<number>\b(?:0x[0-9A-Fa-f]+|\d+(?:\.\d+)?)(?:[uUlLfF]+)?\b)
        |(?P<identifier>\b[A-Za-z_][A-Za-z0-9_]*\b)
        """,
        re.M | re.S | re.X,
    )
    output: List[str] = []
    last = 0
    for match in token_re.finditer(source):
        output.append(html.escape(source[last:match.start()]))
        value = match.group(0)
        kind = match.lastgroup or ""
        if kind == "identifier":
            next_text = source[match.end():match.end() + 32]
            prev_text = source[max(0, match.start() - 4):match.start()]
            if value in CPP_KEYWORDS:
                output.append(code_span("code-token-keyword", value))
            elif value in CPP_TYPES or value[:1].isupper():
                output.append(code_span("code-token-type", value))
            elif next_text.lstrip().startswith("("):
                output.append(code_span("code-token-function", value))
            elif prev_text.endswith("::"):
                output.append(code_span("code-token-member", value))
            else:
                output.append(code_span("code-token-member", value))
        elif kind == "comment":
            output.append(code_span("code-token-comment", value))
        elif kind == "string":
            output.append(code_span("code-token-string", value))
        elif kind == "preprocessor":
            output.append(code_span("code-token-preprocessor", value))
        elif kind == "number":
            output.append(code_span("code-token-number", value))
        else:
            output.append(html.escape(value))
        last = match.end()
    output.append(html.escape(source[last:]))
    return "".join(output)


def highlight_cmake_code(source: str) -> str:
    token_re = re.compile(
        r'(?P<comment>#[^\n]*)|(?P<string>"(?:\\.|[^"\\])*")|(?P<variable>\$\{[^}]+\})|(?P<identifier>\b[A-Za-z_][A-Za-z0-9_]*\b)',
        re.M,
    )
    output: List[str] = []
    last = 0
    for match in token_re.finditer(source):
        output.append(html.escape(source[last:match.start()]))
        value = match.group(0)
        kind = match.lastgroup or ""
        lower_value = value.lower()
        if kind == "comment":
            output.append(code_span("code-token-comment", value))
        elif kind == "string":
            output.append(code_span("code-token-string", value))
        elif kind == "variable":
            output.append(code_span("code-token-member", value))
        elif kind == "identifier" and lower_value in CMAKE_KEYWORDS:
            output.append(code_span("code-token-function", value))
        elif kind == "identifier" and value.isupper():
            output.append(code_span("code-token-type", value))
        else:
            output.append(html.escape(value))
        last = match.end()
    output.append(html.escape(source[last:]))
    return "".join(output)


def highlight_code(source: str, language: str) -> str:
    if language == "cpp":
        return highlight_cpp_code(source)
    if language == "cmake":
        return highlight_cmake_code(source)
    return html.escape(source)


def render_code_reading_overview(notebooks: Sequence[Notebook], projects: Sequence[CodeProject]) -> str:
    cards = []
    for project in projects:
        file_count = len(project.files)
        preview = ", ".join(file.relative_path for file in project.files[:4])
        if len(project.files) > 4:
            preview += ", ..."
        cards.append(
            f"""
            <a class="card-tile code-project-card" href="{code_project_url(project)}">
              <div class="card-meta">
                <span class="card-number">{project.number:02d}</span>
                <span>{file_count} files</span>
              </div>
              <h3>{html.escape(project.title)}</h3>
              <p class="card-preview">{html.escape(preview or 'No C++ files found')}</p>
              <div class="tag-row">
                <span class="tag">project</span>
                <span class="tag">code reading</span>
              </div>
            </a>
            """
        )

    body = f"""
    <div class="app-shell" data-code-reading-root>
      <section class="hero">
        <div>
          <p class="eyebrow">Code reading</p>
          <h1>代码阅读记录</h1>
          <p class="lede">按项目整理 `cpp_awssome_project` 下的 C++ / CMake 文件，进入项目后可以从左侧文件树快速跳转。</p>
        </div>
        <div class="hero-card">
          <div class="stat">{len(projects)}</div>
          <div class="stat-label">projects</div>
        </div>
      </section>
      {render_top_nav(notebooks, CODE_READING_SLUG)}
      <section class="code-project-grid">
        {''.join(cards)}
      </section>
    </div>
    """
    return render_page("代码阅读记录", body, boot_data=boot_payload(notebooks))


def render_code_project_page(
    notebooks: Sequence[Notebook],
    projects: Sequence[CodeProject],
    project: CodeProject,
) -> str:
    toc = "".join(
        f"""
        <a href="#file-{index}">
          {html.escape(file.relative_path)}
        </a>
        """
        for index, file in enumerate(project.files, 1)
    )
    files = "".join(
        f"""
        <article class="panel code-file-card" id="file-{index}">
          <div class="code-file-head">
            <h2 class="code-file-title">{html.escape(file.relative_path)}</h2>
            <span class="tag">{html.escape(file.language)}</span>
          </div>
          <pre class="code-reading-pre"><code class="language-{html.escape(file.language, quote=True)}">{highlight_code(file.content, file.language)}</code></pre>
        </article>
        """
        for index, file in enumerate(project.files, 1)
    )
    project_index_links = "".join(
        f'<a class="top-nav-link {"is-active" if item.slug == project.slug else ""}" href="{code_project_url(item)}">{html.escape(item.title)}</a>'
        for item in projects
    )
    body = f"""
    <div class="app-shell" data-code-project-root>
      <div class="breadcrumb">
        <a href="/">Home</a>
        <span> / </span>
        <a href="/{CODE_READING_SLUG}">代码阅读记录</a>
        <span> / </span>
        <span>{html.escape(project.title)}</span>
      </div>
      <section class="hero">
        <div>
          <p class="eyebrow">Project code</p>
          <h1>{html.escape(project.title)}</h1>
          <p class="lede">{html.escape(project.root_path.relative_to(ROOT).as_posix())}</p>
        </div>
        <div class="hero-card">
          <div class="stat">{len(project.files)}</div>
          <div class="stat-label">files</div>
        </div>
      </section>
      {render_top_nav(notebooks, CODE_READING_SLUG)}
      <nav class="top-nav" aria-label="Code projects">
        <a class="top-nav-link" href="/{CODE_READING_SLUG}">All projects</a>
        {project_index_links}
      </nav>
      <div class="code-file-layout">
        <aside class="code-file-sidebar" aria-label="Project files">
          <div class="reader-sidebar-title">文件结构</div>
          <nav class="code-file-tree">{toc}</nav>
        </aside>
        <main class="code-file-list">
          {files if files else '<p class="saved-empty">No C++ or CMake files found.</p>'}
        </main>
      </div>
    </div>
    """
    return render_page(f"代码阅读记录 - {project.title}", body, boot_data=boot_payload(notebooks))


def render_question_cells(notebook: Notebook) -> str:
    cells = []
    for card in notebook.cards:
        search_text = " ".join(
            [card.title, card.preview, " ".join(card.labels)])
        cells.append(
            f"""
            <a
              class="question-cell is-new"
              data-question-cell
              data-card-id="{card.number}"
              data-search-text="{html.escape(search_text, quote=True)}"
              href="{card_url(notebook, card)}"
              aria-label="{html.escape(card.title, quote=True)}"
              title="{html.escape(card.title, quote=True)}"
            >
              {card.number:02d}
            </a>
            """
        )
    return "".join(cells)


def render_jump_sidebar(notebook: Notebook, title: str = "Quick jump") -> str:
    return f"""
      <aside class="jump-sidebar" aria-label="{html.escape(title, quote=True)}">
        <div class="jump-sidebar-title">{html.escape(title)}</div>
        <div class="card-meta" style="margin-bottom: 10px;">
          <span class="muted"><span data-progress-label>0 visited</span></span>
          <span class="muted"><span data-today-label>0 today</span></span>
        </div>
        <div
          class="question-grid"
          data-overview-root
          data-notebook-slug="{html.escape(notebook.spec.slug, quote=True)}"
        >
          {render_question_cells(notebook)}
        </div>
      </aside>
    """


def render_card_sections(card: Card) -> str:
    return "".join(
        f"""
        <section class="answer-section{' is-english' if section.title.lower() == 'english explanation' else ''}">
          <div class="section-head">
            <h2>{html.escape(section.title)}</h2>
            {
              '<span class="tag">For English interviews</span>'
              if section.title.lower() == 'english explanation'
              else ''
            }
          </div>
          <div class="section-body">
            {section.html}
          </div>
        </section>
        """
        for section in card.sections
    )


def render_reader_page(notebook: Notebook, persistent_state: Optional[Dict[str, object]] = None) -> str:
    toc = "".join(
        f"""
        <a href="#topic-{card.number}">
          <span class="reader-toc-number">{card.number:02d}</span>
          <span class="reader-toc-title">{html.escape(card.title)}</span>
        </a>
        """
        for card in notebook.cards
    )
    articles = "".join(
        f"""
        <article class="panel flashcard reader-article" id="topic-{card.number}">
          <div class="question-block">
            <div class="question-number">{card.number:02d}</div>
            <h1>{html.escape(card.title)}</h1>
            <div class="answer-summary">{section_badges(card.labels)}</div>
          </div>
          <div class="answer-wrap">
            {render_card_sections(card)}
          </div>
        </article>
        """
        for card in notebook.cards
    )
    body = f"""
    <div class="app-shell" data-reader-root>
      <div class="breadcrumb">
        <a href="/">Home</a>
        <span> / </span>
        <span>{html.escape(notebook.spec.title)}</span>
      </div>
      <section class="hero">
        <div>
          <p class="eyebrow">Reading mode</p>
          <h1>{html.escape(notebook.spec.title)}</h1>
          <p class="lede">{html.escape(notebook.spec.description)}</p>
          <div class="reader-actions">
            <a class="button" href="{flashcards_url(notebook)}">Flash cards</a>
            <a class="button-secondary" href="{random_url(notebook)}">随机抽题</a>
          </div>
        </div>
        <div class="hero-card">
          <div class="stat">{len(notebook.cards)}</div>
          <div class="stat-label">topics</div>
        </div>
      </section>
      {render_top_nav((notebook,), notebook.spec.slug)}
      <div class="reader-layout">
        <aside class="reader-sidebar" aria-label="Table of contents">
          <div class="reader-sidebar-title">目录</div>
          <nav class="reader-toc">{toc}</nav>
        </aside>
        <main class="reader-content">{articles}</main>
      </div>
    </div>
    """
    return render_page(notebook.spec.title, body, boot_data=boot_payload([notebook], persistent_state))


def render_overview(notebook: Notebook, persistent_state: Optional[Dict[str, object]] = None) -> str:
    tiles = []
    full_cards = notebook.spec.slug in NOTE_READER_SLUGS
    for card in notebook.cards:
        search_text = " ".join(
            [card.title, card.preview, " ".join(card.labels)])
        if full_cards:
            tiles.append(
                f"""
                <article
                  class="card-tile card-tile-full"
                  data-card-tile
                  data-search-text="{html.escape(search_text, quote=True)}"
                >
                  <div class="card-meta">
                    <span class="card-number">{card.number:02d}</span>
                    <span>{len(card.sections)} sections</span>
                  </div>
                  <h3>{html.escape(card.title)}</h3>
                  <div class="overview-card-body">{render_card_sections(card)}</div>
                  <div class="tag-row">{section_badges(card.labels)}</div>
                  <div class="reveal-actions">
                    <a class="button-secondary" href="{card_url(notebook, card)}">Open card</a>
                  </div>
                </article>
                """
            )
        else:
            tiles.append(
                f"""
                <a
                  class="card-tile"
                  data-card-tile
                  data-search-text="{html.escape(search_text, quote=True)}"
                  href="{card_url(notebook, card)}"
                >
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

    reader_link = (
        f'<a class="button-secondary" href="{overview_url(notebook)}">阅读模式</a>'
        if notebook.spec.slug in NOTE_READER_SLUGS
        else ""
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
        <input
          class="search"
          data-card-search
          type="search"
          placeholder="搜索题目、关键词、section..."
          aria-label="Search cards"
        >
        <a class="button" data-resume-button href="#" hidden>继续上次学习</a>
        <button class="button-secondary" data-clear-button type="button">清空搜索</button>
      </div>

      <div class="toolbar">
        <a class="button-secondary" href="{random_url(notebook)}">随机抽题</a>
        {reader_link}
        <span class="muted">当前显示 <strong data-visible-count>{len(notebook.cards)}</strong> 张卡片。</span>
      </div>

      <div class="overview-with-jump">
        {render_jump_sidebar(notebook, "题号导航")}
        <section class="overview-grid overview-grid-main">
          {''.join(tiles)}
        </section>
      </div>

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
    answer_sections = render_card_sections(card)
    show_answer_by_default = notebook.spec.slug in NOTE_READER_SLUGS
    answer_hidden_attr = "" if show_answer_by_default else " hidden"
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
          <p class="eyebrow">Practice card</p>
          <h2>{html.escape(notebook.spec.title)}</h2>
          <p class="lede">先看题目，再点“显示答案”。你也可以用上一题、下一题和随机题保持复习节奏。</p>
        </div>
        <div class="hero-card">
          <div class="stat">{card.number:02d}</div>
          <div class="stat-label">question {card.number} of {len(notebook.cards)}</div>
        </div>
      </section>

      <div class="card-with-jump">
        {render_jump_sidebar(notebook, "题号导航")}
        <div class="card-workspace">
        <article
          class="panel flashcard card-main"
          data-card-root
          data-notebook-slug="{html.escape(notebook.spec.slug, quote=True)}"
          data-card-id="{card.number}"
          data-reveal-key="flashcards:{html.escape(notebook.spec.slug, quote=True)}:reveal:{card.number}"
        >
          <div class="question-block">
            <div class="question-number">Question {card.number:02d}</div>
            <h1>{html.escape(card.title)}</h1>
            <div class="answer-summary">{section_badges(card.labels)}</div>
            <div class="reveal-actions">
              <button class="button" type="button" data-reveal-button>显示答案</button>
              <button class="button-secondary" type="button" data-save-button>SAVE</button>
              <button class="button-secondary" type="button" data-playground-open>RUN C++</button>
              <button class="button-secondary" type="button" data-note-toggle>My Note</button>
              <a class="button-secondary" href="{overview_url(notebook)}">返回总览</a>
              {
                '<a class="button-secondary" href="' + flashcards_url(notebook) + '">卡片总览</a>'
                if notebook.spec.slug in NOTE_READER_SLUGS
                else ''
              }
              <a
                class="button-secondary"
                href="{random_url(notebook)}"
                data-random-button
                data-target="{random_url(notebook)}"
              >
                随机题
              </a>
            </div>
          </div>

          <div class="answer-wrap" data-answer-wrap{answer_hidden_attr}>
            {answer_sections}
          </div>

          <section
            class="note-panel"
            data-note-root
            data-notebook-slug="{html.escape(notebook.spec.slug, quote=True)}"
            data-card-id="{card.number}"
          >
            <div class="note-panel-head">
              <div>
                <div class="note-title">My Note</div>
                <div class="note-subtitle">
                  Paste text, screenshots, or images. `Ctrl+V` works when the editor is focused.
                </div>
                <div class="note-summary" data-note-summary>No note yet</div>
              </div>
              <div class="note-head-actions">
                <span class="note-status" data-note-status>Draft</span>
                <span class="note-count"><strong data-note-count>0</strong> attachments</span>
                <button class="button-secondary" type="button" data-note-toggle>Edit note</button>
              </div>
            </div>

            <div class="note-body" data-note-body hidden>
              <textarea
                class="note-editor"
                data-note-text
                spellcheck="false"
                placeholder="Write markdown notes here. Paste text or screenshots with Ctrl+V."
              ></textarea>

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
            {
              '<a class="button-secondary" href="' + card_url(notebook, previous_card) + '">上一题</a>'
              if previous_card
              else '<span class="button-secondary" aria-disabled="true">上一题</span>'
            }
            {
              '<a class="button-secondary" href="' + card_url(notebook, next_card) + '">下一题</a>'
              if next_card
              else '<span class="button-secondary" aria-disabled="true">下一题</span>'
            }
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

            <div class="playground-runner-layout">
              <div class="playground-runner-code">
                <label class="playground-label" for="playground-source">Code</label>
                <textarea
                  id="playground-source"
                  class="playground-editor"
                  data-playground-source
                  spellcheck="false"
                  autocomplete="off"
                  autocapitalize="off"
                  autocorrect="off"
                ></textarea>
              </div>

              <div class="playground-runner-side">
                <label class="playground-label" for="playground-stdin">stdin</label>
                <textarea
                  id="playground-stdin"
                  class="playground-stdin"
                  data-playground-stdin
                  spellcheck="false"
                  autocomplete="off"
                  autocapitalize="off"
                  autocorrect="off"
                  placeholder="Optional standard input"
                ></textarea>

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
              </div>
            </div>

            <div class="playground-status" data-playground-status>Closed</div>
          </div>
        </aside>
        </div>
      </div>
    </div>
    """
    return render_page(
        f"{notebook.spec.title} - {card.title}",
        body,
        boot_data=boot_payload([notebook], persistent_state),
    )


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

        if route == "/notes":
            self.send_html(render_notes_page(
                self.notebooks, self.state_store.snapshot()), send_body=send_body)
            return

        if route == "/saved":
            self.send_html(render_saved_page(
                self.notebooks, self.state_store.snapshot()), send_body=send_body)
            return

        if route == f"/{CPP_LAB_SLUG}":
            self.send_html(render_cpp_lab_page(
                self.notebooks), send_body=send_body)
            return

        if route == f"/{CODE_READING_SLUG}":
            self.send_html(render_code_reading_overview(
                self.notebooks, code_projects()), send_body=send_body)
            return

        if route == "/_api/cpp-lab/files":
            self.handle_cpp_lab_files(send_body=send_body)
            return

        if route == "/_api/cpp-lab/file":
            self.handle_cpp_lab_file_read(parsed.query, send_body=send_body)
            return

        if route == "/_api/state":
            self.send_json(self.state_store.snapshot(), send_body=send_body)
            return

        if route == PWA_MANIFEST_PATH:
            self.send_text(
                json.dumps(PWA_MANIFEST, ensure_ascii=False),
                "application/manifest+json; charset=utf-8",
                send_body=send_body,
            )
            return

        if route == PWA_SERVICE_WORKER_PATH:
            self.send_text(
                build_service_worker_js(),
                "application/javascript; charset=utf-8",
                send_body=send_body,
            )
            return

        if route == PWA_ICON_180_PATH:
            self.send_bytes(PWA_ICON_180_PNG, "image/png", send_body=send_body)
            return

        if route == PWA_ICON_512_PATH:
            self.send_bytes(PWA_ICON_512_PNG, "image/png", send_body=send_body)
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

        if parts[0] == CODE_READING_SLUG:
            projects = code_projects()
            if len(parts) == 1:
                self.send_html(render_code_reading_overview(
                    self.notebooks, projects), send_body=send_body)
                return
            if len(parts) == 2:
                try:
                    project = code_project_by_slug(projects, parts[1])
                except KeyError:
                    self.send_not_found(send_body=send_body)
                    return
                self.send_html(render_code_project_page(
                    self.notebooks, projects, project), send_body=send_body)
                return
            self.send_not_found(send_body=send_body)
            return

        slug = parts[0]
        try:
            notebook = notebook_by_slug(self.notebooks, slug)
        except KeyError:
            self.send_not_found(send_body=send_body)
            return

        if len(parts) == 1:
            if notebook.spec.slug in NOTE_READER_SLUGS:
                self.send_html(render_reader_page(
                    notebook, self.state_store.snapshot()), send_body=send_body)
                return
            self.send_html(render_overview(
                notebook, self.state_store.snapshot()), send_body=send_body)
            return

        if len(parts) == 2 and parts[1] == "cards":
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

        if route == "/_api/cpp-lab/file":
            self.handle_cpp_lab_file_save(send_body=send_body)
            return

        if route == "/_api/cpp-lab/run":
            self.handle_cpp_lab_run(send_body=send_body)
            return

        if route == "/_api/note-attachment":
            self.handle_note_attachment_upload(send_body=send_body)
            return

        if route == "/_api/note-attachment-delete":
            self.handle_note_attachment_delete(send_body=send_body)
            return

        self.send_not_found(send_body=send_body)

    def read_json_body(self) -> Dict[str, object]:
        content_length = int(self.headers.get("Content-Length", "0") or "0")
        raw_body = self.rfile.read(
            content_length) if content_length > 0 else b""
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError("Invalid JSON payload.") from exc
        if not isinstance(payload, dict):
            raise ValueError("JSON payload must be an object.")
        return payload

    def cpp_lab_file_payload(self, code_file: CodeFile) -> Dict[str, object]:
        return {
            "ok": True,
            "path": code_file.relative_path,
            "language": code_file.language,
            "content": code_file.content,
            "highlighted": highlight_code(code_file.content, code_file.language),
        }

    def handle_cpp_lab_files(self, send_body: bool) -> None:
        files = cpp_lab_files()
        try:
            root_label = CPP_LAB_ROOT.relative_to(ROOT).as_posix()
        except ValueError:
            root_label = CPP_LAB_ROOT.as_posix()
        self.send_json(
            {
                "ok": True,
                "root": root_label,
                "defaultFile": cpp_lab_default_file(files),
                "files": [
                    {
                        "path": file.relative_path,
                        "language": file.language,
                        "size": len(file.content),
                    }
                    for file in files
                ],
            },
            send_body=send_body,
        )

    def handle_cpp_lab_file_read(self, query: str, send_body: bool) -> None:
        path = parse_qs(query).get("path", [""])[0]
        if not path:
            self.send_json({"ok": False, "error": "path is required."},
                           status=400, send_body=send_body)
            return
        try:
            code_file = read_cpp_lab_file(path)
        except FileNotFoundError:
            self.send_json({"ok": False, "error": "File not found."},
                           status=404, send_body=send_body)
            return
        except (OSError, ValueError) as exc:
            self.send_json({"ok": False, "error": str(exc)},
                           status=400, send_body=send_body)
            return
        self.send_json(self.cpp_lab_file_payload(code_file), send_body=send_body)

    def handle_cpp_lab_file_save(self, send_body: bool) -> None:
        try:
            payload = self.read_json_body()
        except ValueError as exc:
            self.send_json({"ok": False, "error": str(exc)},
                           status=400, send_body=send_body)
            return

        path = payload.get("path", "")
        content = payload.get("content", "")
        if not isinstance(path, str) or not isinstance(content, str):
            self.send_json({"ok": False, "error": "path and content must be strings."},
                           status=400, send_body=send_body)
            return

        try:
            code_file = save_cpp_lab_file(path, content)
        except (OSError, ValueError) as exc:
            self.send_json({"ok": False, "error": str(exc)},
                           status=400, send_body=send_body)
            return
        self.send_json(self.cpp_lab_file_payload(code_file), send_body=send_body)

    def handle_cpp_lab_run(self, send_body: bool) -> None:
        try:
            payload = self.read_json_body()
        except ValueError as exc:
            self.send_json({"ok": False, "error": str(exc)},
                           status=400, send_body=send_body)
            return

        files = payload.get("files", [])
        stdin_data = payload.get("stdin", "")
        runnable_path = payload.get("runnable_path") or None
        if (
            not isinstance(files, list)
            or not isinstance(stdin_data, str)
            or (runnable_path is not None and not isinstance(runnable_path, str))
        ):
            self.send_json({"ok": False, "error": "files must be a list, stdin must be a string, and runnable_path must be a string."},
                           status=400, send_body=send_body)
            return

        saved_files: List[str] = []
        try:
            for item in files:
                if not isinstance(item, dict):
                    raise ValueError("Each file entry must be an object.")
                path = item.get("path", "")
                content = item.get("content", "")
                if not isinstance(path, str) or not isinstance(content, str):
                    raise ValueError("Each file entry needs string path and content.")
                code_file = save_cpp_lab_file(path, content)
                saved_files.append(code_file.relative_path)
            result = compile_cpp_lab_project(
                stdin_data=stdin_data,
                runnable_path=runnable_path,
            )
        except (OSError, ValueError) as exc:
            self.send_json({"ok": False, "phase": "validation", "error": str(exc)},
                           status=400, send_body=send_body)
            return

        result["saved_files"] = saved_files
        self.send_json(result, status=200, send_body=send_body)

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

        if kind == "home_note":
            note_id = payload.get("noteId", "")
            note_state = payload.get("noteState", {})
            if not isinstance(note_id, str) or not note_id:
                self.send_json(
                    {"ok": False, "error": "noteId must be a string."}, status=400, send_body=send_body)
                return
            if not isinstance(note_state, dict):
                self.send_json(
                    {"ok": False, "error": "noteState must be an object."}, status=400, send_body=send_body)
                return
            self.state_store.save_home_note_state(note_id, note_state)
            self.send_json(
                {"ok": True, "noteId": note_id}, send_body=send_body)
            return

        if kind == "home_note_delete":
            note_id = payload.get("noteId", "")
            if not isinstance(note_id, str) or not note_id:
                self.send_json(
                    {"ok": False, "error": "noteId must be a string."}, status=400, send_body=send_body)
                return
            self.state_store.delete_home_note_state(note_id)
            delete_note_attachment_tree(
                self.state_store.state_dir, "home-notes", note_id)
            self.send_json({"ok": True, "noteId": note_id},
                           send_body=send_body)
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

    def send_bytes(self, payload: bytes, content_type: str, status: int = 200, send_body: bool = True) -> None:
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
