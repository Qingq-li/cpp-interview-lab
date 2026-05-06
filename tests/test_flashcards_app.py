import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import tools.flashcards_app as flashcards_app
from tools.flashcards_app import (
    build_notebooks,
    build_pwa_icon_png,
    build_service_worker_js,
    STATIC_ASSET_VERSION,
    compile_cpp_submission,
    code_projects,
    boot_payload,
    APP_JS,
    FlashcardServer,
    highlight_code,
    PersistentStateStore,
    PWA_MANIFEST,
    delete_note_attachment_tree,
    save_note_attachment_file,
    render_card_page,
    render_code_project_page,
    render_code_reading_overview,
    render_cpp_lab_page,
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
        self.assertEqual(13, len(self.notebooks))
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
        self.assertGreaterEqual(len(notes.cards), 3)
        self.assertEqual("CMake Build Flow", cheatsheet.cards[0].title)
        self.assertIn("内容", cheatsheet.cards[0].labels)
        self.assertIn("<table>", cheatsheet.cards[0].sections[0].html)

    def test_groke_cpp_cheatsheet_is_loaded_as_flashcards(self):
        groke = next(notebook for notebook in self.notebooks if notebook.spec.slug == "groke-cpp-cheatsheet")
        self.assertEqual(110, len(groke.cards))
        self.assertEqual("What is the difference between C and C++?", groke.cards[0].title)
        self.assertEqual("GROKE C++ Interview Cheatsheet", groke.spec.title)
        self.assertIn("Answer Keyword", groke.cards[0].sections[0].raw)
        self.assertIn("<table>", groke.cards[0].sections[0].html)

    def test_cpp_news_versions_notebook_is_loaded_as_flashcards(self):
        versions = next(notebook for notebook in self.notebooks if notebook.spec.slug == "cpp-news-versions")
        self.assertEqual(44, len(versions.cards))
        self.assertEqual("C++11：`auto` 类型推导", versions.cards[0].title)
        self.assertEqual("C++ 版本新特性速查", versions.spec.title)
        section_titles = [section.title for section in versions.cards[0].sections]
        self.assertIn("中文简要介绍", section_titles)
        self.assertIn("English Brief", section_titles)
        self.assertIn("中文详细解释", section_titles)
        reader_html = render_reader_page(versions)
        cards_html = render_overview(versions)
        self.assertIn("C++11", reader_html)
        self.assertIn("<table>", cards_html)

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
        nav_html = html[html.index('<nav class="top-nav"'):html.index("</nav>")]
        self.assertIn('href="/notes"', nav_html)
        self.assertIn('href="/saved"', nav_html)
        self.assertNotIn('href="/beginner"', nav_html)
        self.assertIn('href="/cpp-news-versions"', nav_html)
        self.assertIn('href="/cpp-awesome-cheatsheet"', nav_html)
        self.assertIn('href="/groke-cpp-cheatsheet"', nav_html)
        self.assertIn('href="/code-reading"', nav_html)
        self.assertIn('href="/cpp-lab"', nav_html)
        self.assertIn("Cpp News Versions", nav_html)
        self.assertIn("Cpp Awesome Cheatsheet", nav_html)
        self.assertIn("Groke Cpp Cheatsheet", nav_html)
        self.assertIn("Code Reading", nav_html)
        self.assertIn("C++ Lab", nav_html)
        self.assertIn("Saved", nav_html)
        self.assertIn("My Notes", nav_html)
        self.assertNotIn("data-home-note-composer", html)
        self.assertNotIn("data-saved-root", html)

    def test_cpp_lab_page_contains_editor_output_controls(self):
        html = render_cpp_lab_page(self.notebooks)
        self.assertIn("data-cpp-lab-root", html)
        self.assertIn("data-cpp-lab-file-select", html)
        self.assertIn("data-cpp-lab-new-file-name", html)
        self.assertIn("data-cpp-lab-new-file", html)
        self.assertIn("data-cpp-lab-standard", html)
        self.assertIn('value="c++17" selected', html)
        self.assertIn('value="c++20"', html)
        self.assertIn("data-cpp-lab-editor-mount", html)
        self.assertIn("data-cpp-lab-output", html)
        self.assertIn("data-cpp-lab-save", html)
        self.assertIn("data-cpp-lab-run", html)
        self.assertIn("data-cpp-lab-run-shortcut", html)
        self.assertIn("⌥C Run", html)
        self.assertNotIn("Edit files from `cpp_awssome_project/random_pj`", html)
        self.assertIn("data-cpp-lab-clear", html)
        self.assertIn("data-cpp-lab-editor-theme", html)
        self.assertIn("data-cpp-lab-output-theme", html)
        self.assertIn("run selected file", html)

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
        self.assertIn("data-save-button", html)
        self.assertIn("data-note-root", html)
        self.assertIn("My Note", html)
        self.assertIn("playground-runner-layout", html)
        self.assertIn("playground-runner-code", html)
        self.assertIn("playground-runner-side", html)

    def test_overview_cards_hide_section_badges(self):
        html = render_overview(self.beginner)
        first_tile = html.split('data-card-tile', 1)[1].split("</a>", 1)[0]
        self.assertIn("指针和引用有什么区别？", first_tile)
        self.assertIn("sections", first_tile)
        self.assertNotIn('class="tag-row"', first_tile)
        self.assertNotIn('<span class="tag">核心答案</span>', first_tile)

    def test_boot_payload_contains_persistent_state(self):
        payload = boot_payload([self.beginner])
        self.assertIn("persistentState", payload)
        self.assertIn("saved_cards", payload["persistentState"])
        self.assertIn("notebooks", payload["persistentState"])
        self.assertIn("notes", payload["persistentState"])
        self.assertIn("home_notes", payload["persistentState"])

    def test_render_page_embeds_parseable_boot_json(self):
        boot_data = {
            "notebooks": [
                {
                    "slug": "demo",
                    "title": 'A "quoted" <notebook> & title',
                    "description": "",
                    "totalCards": 0,
                    "cards": [],
                }
            ],
            "persistentState": {"saved_cards": ["demo:1"], "notebooks": {}, "notes": {}, "home_notes": {}},
        }
        html = render_page("demo", "<main></main>", boot_data=boot_data)
        raw_json = html.split('<script id="flashcards-data" type="application/json">', 1)[1].split("</script>", 1)[0]
        self.assertNotIn("&quot;", raw_json)
        self.assertIn("\\u003cnotebook\\u003e", raw_json)
        self.assertEqual(boot_data, json.loads(raw_json))

    def test_saved_cards_merge_local_and_server_state(self):
        self.assertIn("function mergeSavedCards", APP_JS)
        self.assertIn("const currentSaved = getSavedCards();", APP_JS)
        self.assertIn("keepalive: true", APP_JS)

    def test_card_save_button_is_idempotent(self):
        self.assertIn("function saveCardIfNeeded", APP_JS)
        self.assertIn("saved.includes(key)", APP_JS)
        self.assertIn("saveCardIfNeeded(notebookSlug, cardId);", APP_JS)
        self.assertNotIn("toggleCardSaved(notebookSlug, cardId);", APP_JS)

    def test_pwa_assets_are_generated(self):
        html = render_page("demo", "<main></main>", boot_data=boot_payload([self.beginner]))
        self.assertIn('rel="manifest"', html)
        self.assertIn('apple-touch-icon', html)
        self.assertIn("apple-mobile-web-app-capable", html)
        self.assertIn(f"/_static/app.js?v={STATIC_ASSET_VERSION}", html)

        manifest = PWA_MANIFEST
        self.assertEqual("standalone", manifest["display"])
        self.assertIn("icons", manifest)

        sw = build_service_worker_js()
        self.assertIn("CACHE_NAME", sw)
        self.assertIn("flashcards-pwa-v6-clean-card-tags", sw)
        self.assertIn(f"/_static/app.js?v={STATIC_ASSET_VERSION}", sw)
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

    def test_saved_route_shows_cards_after_state_api_save(self):
        with TemporaryDirectory() as tmpdir:
            FlashcardServer.notebooks = self.notebooks
            FlashcardServer.state_store = PersistentStateStore(Path(tmpdir))
            server = ThreadingHTTPServer(("127.0.0.1", 0), FlashcardServer)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                host, port = server.server_address
                base_url = f"http://{host}:{port}"
                save_request = Request(
                    f"{base_url}/_api/state",
                    data=json.dumps(
                        {"kind": "saved_cards", "savedCards": ["advanced:2"]}
                    ).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urlopen(save_request, timeout=5) as response:
                    save_payload = json.loads(response.read().decode("utf-8"))
                with urlopen(f"{base_url}/saved", timeout=5) as response:
                    saved_html = response.read().decode("utf-8")
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)

        self.assertTrue(save_payload["ok"])
        self.assertIn("<strong data-saved-count>1</strong>", saved_html)
        self.assertIn("`std::move` 和 `std::forward` 的区别是什么？", saved_html)

    def test_cpp_lab_routes_and_apis(self):
        with TemporaryDirectory() as tmpdir:
            lab_root = Path(tmpdir) / "random_pj"
            lab_root.mkdir()
            main_file = lab_root / "random_code.cpp"
            main_file.write_text(
                '#include <iostream>\nint main() { std::cout << "api ok\\n"; }\n',
                encoding="utf-8",
            )
            old_root = flashcards_app.CPP_LAB_ROOT
            flashcards_app.CPP_LAB_ROOT = lab_root
            FlashcardServer.notebooks = self.notebooks
            FlashcardServer.state_store = PersistentStateStore(Path(tmpdir) / "state")
            server = ThreadingHTTPServer(("127.0.0.1", 0), FlashcardServer)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                host, port = server.server_address
                base_url = f"http://{host}:{port}"
                with urlopen(f"{base_url}/cpp-lab", timeout=5) as response:
                    lab_html = response.read().decode("utf-8")
                with urlopen(f"{base_url}/_api/cpp-lab/files", timeout=5) as response:
                    files_payload = json.loads(response.read().decode("utf-8"))
                with urlopen(f"{base_url}/_api/cpp-lab/file?path=random_code.cpp", timeout=5) as response:
                    file_payload = json.loads(response.read().decode("utf-8"))

                save_request = Request(
                    f"{base_url}/_api/cpp-lab/file",
                    data=json.dumps(
                        {
                            "path": "random_code.cpp",
                            "content": '#include <iostream>\nint main() { std::cout << "saved\\n"; }\n',
                        }
                    ).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urlopen(save_request, timeout=5) as response:
                    save_payload = json.loads(response.read().decode("utf-8"))

                create_request = Request(
                    f"{base_url}/_api/cpp-lab/new-file",
                    data=json.dumps({"path": "auto_demo"}).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urlopen(create_request, timeout=5) as response:
                    create_payload = json.loads(response.read().decode("utf-8"))

                duplicate_request = Request(
                    f"{base_url}/_api/cpp-lab/new-file",
                    data=json.dumps({"path": "auto_demo.cpp"}).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with self.assertRaises(HTTPError) as duplicate_error:
                    urlopen(duplicate_request, timeout=5)
                duplicate_payload = json.loads(duplicate_error.exception.read().decode("utf-8"))

                bad_create_request = Request(
                    f"{base_url}/_api/cpp-lab/new-file",
                    data=json.dumps({"path": "../escape.cpp"}).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with self.assertRaises(HTTPError) as bad_create_error:
                    urlopen(bad_create_request, timeout=5)
                bad_create_payload = json.loads(bad_create_error.exception.read().decode("utf-8"))

                bad_request = Request(
                    f"{base_url}/_api/cpp-lab/file",
                    data=json.dumps(
                        {"path": "../README.md", "content": "bad"}).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with self.assertRaises(HTTPError) as bad_error:
                    urlopen(bad_request, timeout=5)
                bad_payload = json.loads(bad_error.exception.read().decode("utf-8"))
                saved_content = main_file.read_text(encoding="utf-8")
                created_content = (lab_root / "auto_demo.cpp").read_text(encoding="utf-8")
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)
                flashcards_app.CPP_LAB_ROOT = old_root

        self.assertIn("data-cpp-lab-root", lab_html)
        self.assertTrue(files_payload["ok"])
        self.assertEqual("random_code.cpp", files_payload["defaultFile"])
        self.assertIn("random_code.cpp", [entry["path"] for entry in files_payload["files"]])
        self.assertTrue(file_payload["ok"])
        self.assertIn("code-token-preprocessor", file_payload["highlighted"])
        self.assertTrue(save_payload["ok"])
        self.assertIn("saved", saved_content)
        self.assertTrue(create_payload["ok"])
        self.assertEqual("auto_demo.cpp", create_payload["path"])
        self.assertIn("Hello from C++ Lab", created_content)
        self.assertFalse(duplicate_payload["ok"])
        self.assertFalse(bad_create_payload["ok"])
        self.assertFalse(bad_payload["ok"])
        self.assertIn("inside", bad_payload["error"])

    def test_cpp_lab_run_api_saves_then_compiles(self):
        with TemporaryDirectory() as tmpdir:
            lab_root = Path(tmpdir) / "random_pj"
            lab_root.mkdir()
            (lab_root / "random_code.cpp").write_text(
                '#include <iostream>\nint main() { std::cout << "old\\n"; }\n',
                encoding="utf-8",
            )
            old_root = flashcards_app.CPP_LAB_ROOT
            flashcards_app.CPP_LAB_ROOT = lab_root
            FlashcardServer.notebooks = self.notebooks
            FlashcardServer.state_store = PersistentStateStore(Path(tmpdir) / "state")
            server = ThreadingHTTPServer(("127.0.0.1", 0), FlashcardServer)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                host, port = server.server_address
                base_url = f"http://{host}:{port}"
                run_request = Request(
                    f"{base_url}/_api/cpp-lab/run",
                    data=json.dumps(
                        {
                            "files": [
                                {
                                    "path": "random_code.cpp",
                                    "content": '#include <iostream>\nint main() { std::cout << "new output\\n"; }\n',
                                }
                            ]
                        }
                    ).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urlopen(run_request, timeout=10) as response:
                    run_payload = json.loads(response.read().decode("utf-8"))

                fail_request = Request(
                    f"{base_url}/_api/cpp-lab/run",
                    data=json.dumps(
                        {
                            "files": [
                                {
                                    "path": "random_code.cpp",
                                    "content": "int main( { return 0; }",
                                }
                            ]
                        }
                    ).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urlopen(fail_request, timeout=10) as response:
                    fail_payload = json.loads(response.read().decode("utf-8"))
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)
                flashcards_app.CPP_LAB_ROOT = old_root

        self.assertTrue(run_payload["ok"])
        self.assertIn("random_code.cpp", run_payload["saved_files"])
        self.assertIn("new output", run_payload["run_stdout"])
        self.assertTrue(run_payload["compile_metrics"]["available"])
        self.assertGreaterEqual(run_payload["compile_metrics"]["wall_seconds"], 0)
        self.assertTrue(run_payload["run_metrics"]["available"])
        self.assertGreaterEqual(run_payload["run_metrics"]["max_rss_kb"], 0)
        self.assertFalse(fail_payload["ok"])
        self.assertEqual("compile", fail_payload["phase"])
        self.assertTrue(fail_payload["compile_stderr"])
        self.assertTrue(fail_payload["compile_metrics"]["available"])

    def test_cpp_lab_run_api_compiles_selected_file(self):
        with TemporaryDirectory() as tmpdir:
            lab_root = Path(tmpdir) / "random_pj"
            lab_root.mkdir()
            (lab_root / "random_classinherited_code.cpp").write_text(
                '#include <iostream>\nint main() { std::cout << "selected\\n"; }\n',
                encoding="utf-8",
            )
            old_root = flashcards_app.CPP_LAB_ROOT
            flashcards_app.CPP_LAB_ROOT = lab_root
            FlashcardServer.notebooks = self.notebooks
            FlashcardServer.state_store = PersistentStateStore(Path(tmpdir) / "state")
            server = ThreadingHTTPServer(("127.0.0.1", 0), FlashcardServer)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                host, port = server.server_address
                run_request = Request(
                    f"http://{host}:{port}/_api/cpp-lab/run",
                    data=json.dumps(
                        {
                            "runnable_path": "random_classinherited_code.cpp",
                            "standard": "c++20",
                            "files": [
                                {
                                    "path": "random_classinherited_code.cpp",
                                    "content": '#include <iostream>\nint main() { std::cout << "current file\\n"; }\n',
                                }
                            ],
                        }
                    ).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urlopen(run_request, timeout=10) as response:
                    run_payload = json.loads(response.read().decode("utf-8"))
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)
                flashcards_app.CPP_LAB_ROOT = old_root

        self.assertTrue(run_payload["ok"])
        self.assertEqual("random_classinherited_code.cpp", run_payload["runnable_file"])
        self.assertEqual("c++20", run_payload["standard"])
        self.assertIn("current file", run_payload["run_stdout"])

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
        self.assertTrue(result["compile_metrics"]["available"])
        self.assertGreaterEqual(result["compile_metrics"]["wall_seconds"], 0)
        self.assertTrue(result["run_metrics"]["available"])
        self.assertGreaterEqual(result["run_metrics"]["max_rss_kb"], 0)

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
