import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from tools.flashcards_app import (
    build_notebooks,
    build_pwa_icon_png,
    build_service_worker_js,
    compile_cpp_submission,
    boot_payload,
    PersistentStateStore,
    PWA_MANIFEST,
    save_note_attachment_file,
    render_card_page,
    render_home,
    render_markdown,
    render_page,
    render_overview,
)


class FlashcardAppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.notebooks = build_notebooks()
        cls.beginner = next(notebook for notebook in cls.notebooks if notebook.spec.slug == "beginner")

    def test_beginner_notebook_card_count(self):
        self.assertEqual(9, len(self.notebooks))
        self.assertEqual("beginner", self.beginner.spec.slug)
        self.assertEqual(75, len(self.beginner.cards))
        intermediate = next(notebook for notebook in self.notebooks if notebook.spec.slug == "intermediate")
        advanced = next(notebook for notebook in self.notebooks if notebook.spec.slug == "advanced")
        code_examples = next(notebook for notebook in self.notebooks if notebook.spec.slug == "code-examples")
        self.assertEqual(45, len(intermediate.cards))
        self.assertEqual(40, len(advanced.cards))
        self.assertEqual(50, len(code_examples.cards))

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

    def test_home_saved_cards_render_matching_entries(self):
        html = render_home(
            self.notebooks,
            {
                "saved_cards": ["beginner:1", "missing:999"],
                "notebooks": {},
                "notes": {},
            },
        )
        self.assertIn("指针和引用有什么区别？", html)
        self.assertIn("<strong data-saved-count>1</strong> saved", html)
        self.assertNotIn("missing:999", html)

    def test_card_page_contains_answer_toggle(self):
        html = render_card_page(self.beginner, self.beginner.cards[0])
        self.assertIn("显示答案", html)
        self.assertIn("上一题", html)
        self.assertIn("下一题", html)
        self.assertIn("data-answer-wrap", html)
        self.assertIn("data-note-root", html)
        self.assertIn("My Note", html)

    def test_boot_payload_contains_persistent_state(self):
        payload = boot_payload([self.beginner])
        self.assertIn("persistentState", payload)
        self.assertIn("saved_cards", payload["persistentState"])
        self.assertIn("notebooks", payload["persistentState"])
        self.assertIn("notes", payload["persistentState"])

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
