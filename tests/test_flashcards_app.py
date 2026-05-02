import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.request import urlopen

from tools.flashcards_app import (
    build_notebooks,
    build_pwa_icon_png,
    build_service_worker_js,
    compile_cpp_submission,
    code_projects,
    boot_payload,
    FlashcardServer,
    highlight_code,
    PersistentStateStore,
    PWA_MANIFEST,
    delete_note_attachment_tree,
    save_note_attachment_file,
    render_card_page,
    render_code_project_page,
    render_code_reading_overview,
    render_home,
    render_markdown,
    render_notes_page,
    render_page,
    render_overview,
    render_reader_page,
    render_saved_page,
)


class FlashcardAppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.notebooks = build_notebooks()
        cls.beginner = next(notebook for notebook in cls.notebooks if notebook.spec.slug == "beginner")

    def test_beginner_notebook_card_count(self):
        self.assertEqual(11, len(self.notebooks))
        self.assertEqual("beginner", self.beginner.spec.slug)
        self.assertEqual(75, len(self.beginner.cards))
        intermediate = next(notebook for notebook in self.notebooks if notebook.spec.slug == "intermediate")
        advanced = next(notebook for notebook in self.notebooks if notebook.spec.slug == "advanced")
        code_examples = next(notebook for notebook in self.notebooks if notebook.spec.slug == "code-examples")
        self.assertEqual(45, len(intermediate.cards))
        self.assertEqual(40, len(advanced.cards))
        self.assertEqual(50, len(code_examples.cards))

    def test_cpp_awssome_markdown_notebooks_are_loaded(self):
        cheatsheet = next(notebook for notebook in self.notebooks if notebook.spec.slug == "cpp-awesome-cheatsheet")
        notes = next(notebook for notebook in self.notebooks if notebook.spec.slug == "cpp-awesome-notes")
        self.assertGreaterEqual(len(cheatsheet.cards), 9)
        self.assertGreaterEqual(len(notes.cards), 20)
        self.assertEqual("CMake Build Flow", cheatsheet.cards[0].title)
        self.assertIn("内容", cheatsheet.cards[0].labels)
        self.assertIn("<table>", cheatsheet.cards[0].sections[0].html)

    def test_cpp_awssome_default_reader_and_cards_overview(self):
        cheatsheet = next(notebook for notebook in self.notebooks if notebook.spec.slug == "cpp-awesome-cheatsheet")
        reader_html = render_reader_page(cheatsheet)
        cards_html = render_overview(cheatsheet)
        self.assertIn("data-reader-root", reader_html)
        self.assertIn("reader-toc", reader_html)
        self.assertIn('href="/cpp-awesome-cheatsheet/cards"', reader_html)
        self.assertIn("CMake Build Flow", reader_html)
        self.assertIn("<table>", reader_html)
        self.assertIn("card-tile-full", cards_html)
        self.assertIn("overview-card-body", cards_html)
        self.assertIn("题号导航", cards_html)

    def test_code_reading_projects_are_scanned_and_rendered(self):
        projects = code_projects()
        titles = [project.title for project in projects]
        self.assertIn("demo-sensor-logger-project", titles)
        self.assertIn("test-sensor-logger-project", titles)
        demo = next(project for project in projects if project.title == "demo-sensor-logger-project")
        self.assertTrue(any(file.relative_path == "CMakeLists.txt" for file in demo.files))
        self.assertTrue(any(file.relative_path.endswith(".cpp") for file in demo.files))
        self.assertFalse(any("/build/" in f"/{file.relative_path}/" for file in demo.files))

        overview_html = render_code_reading_overview(self.notebooks, projects)
        self.assertIn("data-code-reading-root", overview_html)
        self.assertIn("demo-sensor-logger-project", overview_html)
        self.assertIn("/code-reading/", overview_html)

        detail_html = render_code_project_page(self.notebooks, projects, demo)
        self.assertIn("data-code-project-root", detail_html)
        self.assertIn("文件结构", detail_html)
        self.assertIn("code-reading-pre", detail_html)
        self.assertIn("CMakeLists.txt", detail_html)

    def test_code_reading_syntax_highlight_uses_vscode_like_tokens(self):
        html = highlight_code(
            '#include <iostream>\n// note\nint main() { std::cout << "ok"; return 0; }\n',
            "cpp",
        )
        self.assertIn("code-token-preprocessor", html)
        self.assertIn("code-token-comment", html)
        self.assertIn("code-token-keyword", html)
        self.assertIn("code-token-function", html)
        self.assertIn("code-token-string", html)
        self.assertIn("code-token-number", html)

    def test_first_and_last_cards(self):
        self.assertEqual(1, self.beginner.cards[0].number)
        self.assertEqual("指针和引用有什么区别？", self.beginner.cards[0].title)
        self.assertEqual(75, self.beginner.cards[-1].number)

    def test_sections_are_parsed(self):
        card = self.beginner.cards[6]
        titles = [section.title for section in card.sections]
        self.assertIn("核心答案", titles)
        self.assertIn("代码讲解", titles)
        self.assertIn("Note", titles)

    def test_markdown_renderer_handles_lists_and_code(self):
        html = render_markdown(
            """- one
- two

```cpp
int main() {}
```
"""
        )
        self.assertIn("<ul>", html)
        self.assertIn("<code", html)
        self.assertIn("int main()", html)

    def test_markdown_renderer_handles_tables_quotes_and_headings(self):
        html = render_markdown(
            """> important

### Details

| A | B |
|---|---:|
| `x` | **yes** |

---
"""
        )
        self.assertIn("<blockquote>", html)
        self.assertIn("<h3>Details</h3>", html)
        self.assertIn("<table>", html)
        self.assertIn("<code>x</code>", html)
        self.assertIn("<hr>", html)

    def test_overview_page_contains_navigation(self):
        html = render_overview(self.beginner)
        self.assertIn("搜索题目", html)
        self.assertIn("/beginner/random", html)
        self.assertIn("cards visited", html)

    def test_home_page_uses_production_copy(self):
        html = render_home(self.notebooks)
        self.assertNotIn("把原始 Markdown 按题拆开", html)
        self.assertNotIn("Markdown 是唯一内容源", html)
        self.assertNotIn("本地启动后可以直接", html)
        self.assertNotIn("进入 beginner 卡片站", html)
        self.assertIn("C++ interview practice", html)

    def test_home_page_contains_compact_navigation(self):
        html = render_home(self.notebooks)
        self.assertIn('href="/notes"', html)
        self.assertIn('href="/saved"', html)
        self.assertIn('href="/beginner"', html)
        self.assertNotIn("data-home-note-composer", html)
        self.assertNotIn("data-saved-root", html)

    def test_saved_page_render_matching_entries(self):
        html = render_saved_page(
            self.notebooks,
            {
                "saved_cards": ["beginner:1", "missing:999"],
                "notebooks": {},
                "notes": {},
                "home_notes": {},
            },
        )
        self.assertIn("指针和引用有什么区别？", html)
        self.assertIn("<strong data-saved-count>1</strong>", html)
        self.assertIn("<div class=\"stat-label\">saved</div>", html)
        self.assertNotIn("missing:999", html)

    def test_card_page_contains_answer_toggle(self):
        html = render_card_page(self.beginner, self.beginner.cards[0])
        self.assertIn("显示答案", html)
        self.assertIn("上一题", html)
        self.assertIn("下一题", html)
        self.assertIn("data-answer-wrap", html)
        self.assertIn("data-note-root", html)
        self.assertIn("My Note", html)
        self.assertIn("playground-runner-layout", html)
        self.assertIn("playground-runner-code", html)
        self.assertIn("playground-runner-side", html)

    def test_boot_payload_contains_persistent_state(self):
        payload = boot_payload([self.beginner])
        self.assertIn("persistentState", payload)
        self.assertIn("saved_cards", payload["persistentState"])
        self.assertIn("notebooks", payload["persistentState"])
        self.assertIn("notes", payload["persistentState"])
        self.assertIn("home_notes", payload["persistentState"])

    def test_pwa_assets_are_generated(self):
        html = render_page("demo", "<main></main>", boot_data=boot_payload([self.beginner]))
        self.assertIn('rel="manifest"', html)
        self.assertIn('apple-touch-icon', html)
        self.assertIn("apple-mobile-web-app-capable", html)

        manifest = PWA_MANIFEST
        self.assertEqual("standalone", manifest["display"])
        self.assertIn("icons", manifest)

        sw = build_service_worker_js()
        self.assertIn("CACHE_NAME", sw)
        self.assertIn("self.addEventListener('fetch'", sw)

        icon = build_pwa_icon_png(180)
        self.assertTrue(icon.startswith(b"\x89PNG\r\n\x1a\n"))

    def test_note_state_roundtrip(self):
        with TemporaryDirectory() as tmpdir:
            store = PersistentStateStore(Path(tmpdir))
            store.save_note_state(
                "beginner",
                "1",
                {
                    "text": "hello note",
                    "attachments": [
                        {
                            "id": "abc",
                            "filename": "shot.png",
                            "url": "/_attachments/beginner/1/abc.png",
                            "mimeType": "image/png",
                            "createdAt": "2026-04-24T00:00:00Z",
                            "size": 3,
                        }
                    ],
                    "updatedAt": "2026-04-24T00:00:00Z",
                },
            )
            reloaded = PersistentStateStore(Path(tmpdir))
            snapshot = reloaded.snapshot()
            self.assertEqual("hello note", snapshot["notes"]["beginner"]["1"]["text"])
            self.assertEqual(1, len(snapshot["notes"]["beginner"]["1"]["attachments"]))

    def test_home_note_state_roundtrip_and_delete(self):
        with TemporaryDirectory() as tmpdir:
            store = PersistentStateStore(Path(tmpdir))
            store.save_home_note_state(
                "note-1",
                {
                    "id": "note-1",
                    "type": "cpp",
                    "title": "Idea",
                    "text": "hello home note",
                    "attachments": [
                        {
                            "id": "abc",
                            "filename": "shot.png",
                            "url": "/_attachments/home-notes/note-1/abc.png",
                            "mimeType": "image/png",
                            "createdAt": "2026-04-24T00:00:00Z",
                            "size": 3,
                        }
                    ],
                    "createdAt": "2026-04-24T00:00:00Z",
                    "updatedAt": "2026-04-24T00:01:00Z",
                },
            )
            snapshot = store.snapshot()
            self.assertEqual("cpp", snapshot["home_notes"]["note-1"]["type"])
            self.assertEqual("Idea", snapshot["home_notes"]["note-1"]["title"])
            self.assertEqual("hello home note", snapshot["home_notes"]["note-1"]["text"])
            self.assertEqual(1, len(snapshot["home_notes"]["note-1"]["attachments"]))

            store.delete_home_note_state("note-1")
            self.assertNotIn("note-1", store.snapshot()["home_notes"])

    def test_home_note_state_normalizes_invalid_fields(self):
        with TemporaryDirectory() as tmpdir:
            store = PersistentStateStore(Path(tmpdir))
            store.save_home_note_state(
                "note-1",
                {
                    "id": "",
                    "type": "python",
                    "title": 123,
                    "text": ["bad"],
                    "attachments": ["bad"],
                    "createdAt": 456,
                    "updatedAt": None,
                },
            )
            note = store.snapshot()["home_notes"]["note-1"]
            self.assertEqual("note-1", note["id"])
            self.assertEqual("text", note["type"])
            self.assertEqual("", note["title"])
            self.assertEqual("", note["text"])
            self.assertEqual([], note["attachments"])
            self.assertEqual("", note["createdAt"])
            self.assertEqual("", note["updatedAt"])

    def test_note_attachment_file_saved(self):
        with TemporaryDirectory() as tmpdir:
            attachment = save_note_attachment_file(
                Path(tmpdir),
                "beginner",
                "1",
                "screen.png",
                b"png",
                "image/png",
            )
            self.assertTrue(attachment["url"].startswith("/_attachments/beginner/1/"))
            stored = Path(tmpdir) / "note-attachments" / "beginner" / "1" / attachment["storedName"]
            self.assertTrue(stored.exists())

    def test_home_note_attachment_tree_deleted(self):
        with TemporaryDirectory() as tmpdir:
            attachment = save_note_attachment_file(
                Path(tmpdir),
                "home-notes",
                "note-1",
                "screen.png",
                b"png",
                "image/png",
            )
            stored = Path(tmpdir) / "note-attachments" / "home-notes" / "note-1" / attachment["storedName"]
            self.assertTrue(stored.exists())
            delete_note_attachment_tree(Path(tmpdir), "home-notes", "note-1")
            self.assertFalse(stored.exists())

    def test_notes_page_contains_home_note_composer(self):
        html = render_notes_page(self.notebooks)
        self.assertIn("data-home-note-composer", html)
        self.assertIn("data-home-note-title", html)
        self.assertIn("data-home-note-text", html)
        self.assertIn('value="text" data-home-note-type', html)
        self.assertIn('value="cpp" data-home-note-type', html)
        self.assertIn("data-note-runner-root", html)
        self.assertIn("还没有 note", html)

    def test_notes_page_renders_newest_first(self):
        html = render_notes_page(
            self.notebooks,
            {
                "saved_cards": [],
                "notebooks": {},
                "notes": {},
                "home_notes": {
                    "old": {
                        "id": "old",
                        "type": "text",
                        "title": "Old note",
                        "text": "older",
                        "attachments": [],
                        "createdAt": "2026-04-24T00:00:00Z",
                        "updatedAt": "2026-04-24T00:00:00Z",
                    },
                    "new": {
                        "id": "new",
                        "type": "text",
                        "title": "New note",
                        "text": "newer",
                        "attachments": [],
                        "createdAt": "2026-04-25T00:00:00Z",
                        "updatedAt": "2026-04-25T00:00:00Z",
                    },
                },
            },
        )
        self.assertIn("data-home-note-card", html)
        self.assertLess(html.index("New note"), html.index("Old note"))
        self.assertNotIn("RUN C++", html)

    def test_notes_page_cpp_note_renders_run_button(self):
        html = render_notes_page(
            self.notebooks,
            {
                "saved_cards": [],
                "notebooks": {},
                "notes": {},
                "home_notes": {
                    "cpp-note": {
                        "id": "cpp-note",
                        "type": "cpp",
                        "title": "Vector demo",
                        "text": "#include <iostream>\nint main() { std::cout << 1; }",
                        "attachments": [],
                        "createdAt": "2026-04-25T00:00:00Z",
                        "updatedAt": "2026-04-25T00:00:00Z",
                    },
                },
            },
        )
        self.assertIn("C++ code", html)
        self.assertIn("RUN C++", html)
        self.assertIn('data-home-note-run data-note-id="cpp-note"', html)

    def test_notes_and_saved_routes_render(self):
        with TemporaryDirectory() as tmpdir:
            FlashcardServer.notebooks = self.notebooks
            FlashcardServer.state_store = PersistentStateStore(Path(tmpdir))
            server = ThreadingHTTPServer(("127.0.0.1", 0), FlashcardServer)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                host, port = server.server_address
                with urlopen(f"http://{host}:{port}/notes", timeout=5) as response:
                    notes_html = response.read().decode("utf-8")
                with urlopen(f"http://{host}:{port}/saved", timeout=5) as response:
                    saved_html = response.read().decode("utf-8")
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)

        self.assertIn("data-notes-root", notes_html)
        self.assertIn("data-saved-page-root", saved_html)

    def test_cpp_compile_success(self):
        result = compile_cpp_submission(
            """
#include <iostream>

int main() {
    std::cout << "hello\\n";
    return 0;
}
""".strip()
        )
        self.assertTrue(result["ok"])
        self.assertEqual("run", result["phase"])
        self.assertTrue(result["compiled"])
        self.assertIn("hello", result["run_stdout"])

    def test_cpp_compile_failure(self):
        result = compile_cpp_submission("int main( { return 0; }")
        self.assertFalse(result["ok"])
        self.assertEqual("compile", result["phase"])
        self.assertFalse(result["compiled"])
        self.assertNotEqual(0, result["compile_returncode"])
        self.assertTrue(result["compile_stderr"])

    def test_cpp_runtime_timeout(self):
        result = compile_cpp_submission(
            """
int main() {
    for (;;) {}
}
""".strip()
        )
        self.assertFalse(result["ok"])
        self.assertEqual("run", result["phase"])
        self.assertTrue(result["compiled"])
        self.assertTrue(result["run_timed_out"])
        self.assertIn("timed out", result["run_stderr"])


if __name__ == "__main__":
    unittest.main()
