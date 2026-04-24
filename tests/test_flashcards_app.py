import unittest

from tools.flashcards_app import (
    build_notebooks,
    compile_cpp_submission,
    render_card_page,
    render_markdown,
    render_overview,
)


class FlashcardAppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.notebooks = build_notebooks()
        cls.beginner = next(notebook for notebook in cls.notebooks if notebook.spec.slug == "beginner")

    def test_beginner_notebook_card_count(self):
        self.assertEqual(8, len(self.notebooks))
        self.assertEqual("beginner", self.beginner.spec.slug)
        self.assertEqual(57, len(self.beginner.cards))

    def test_first_and_last_cards(self):
        self.assertEqual(1, self.beginner.cards[0].number)
        self.assertEqual("指针和引用有什么区别？", self.beginner.cards[0].title)
        self.assertEqual(57, self.beginner.cards[-1].number)

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

    def test_card_page_contains_answer_toggle(self):
        html = render_card_page(self.beginner, self.beginner.cards[0])
        self.assertIn("显示答案", html)
        self.assertIn("上一题", html)
        self.assertIn("下一题", html)
        self.assertIn("data-answer-wrap", html)

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
