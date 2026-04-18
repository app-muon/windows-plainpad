import tkinter as tk
import unittest
from types import SimpleNamespace

from plainpad import Notepad


class FakeSource:
    def __init__(self, text):
        self.text = text

    def get(self, *_args):
        return self.text


class FakePreview:
    def __init__(self):
        self.content = ""
        self.tags = []

    def config(self, **_kwargs):
        pass

    def delete(self, *_args):
        self.content = ""
        self.tags = []

    def index(self, index):
        if index == tk.END:
            return str(len(self.content) + 1)
        if index == "end-1c":
            return str(len(self.content))
        return str(index)

    def insert(self, _index, text, tags=()):
        start = len(self.content)
        self.content += text
        end = len(self.content)
        for tag in tags:
            self.tags.append((tag, start, end, text))

    def tag_add(self, tag, start, end):
        start = int(start)
        end = int(end)
        self.tags.append((tag, start, end, self.content[start:end]))


class MarkdownPreviewTests(unittest.TestCase):
    def render(self, source):
        app = object.__new__(Notepad)
        preview = FakePreview()
        doc = SimpleNamespace(
            preview=preview,
            preview_after_id=None,
            text=FakeSource(source),
        )

        app._refresh_markdown_preview(doc)
        return preview

    def test_atx_headings_support_levels_one_through_six(self):
        source = "\n".join(f"{'#' * level} Heading {level}" for level in range(1, 7))

        preview = self.render(source)

        heading_tags = [tag for tag in preview.tags if tag[0].startswith("heading")]
        self.assertEqual(
            heading_tags,
            [
                ("heading1", 0, 9, "Heading 1"),
                ("heading2", 10, 19, "Heading 2"),
                ("heading3", 20, 29, "Heading 3"),
                ("heading4", 30, 39, "Heading 4"),
                ("heading5", 40, 49, "Heading 5"),
                ("heading6", 50, 59, "Heading 6"),
            ],
        )

    def test_atx_heading_rules_do_not_convert_every_hash_line(self):
        source = "\n".join(
            [
                "   #### Trimmed ####",
                "####### Too many hashes",
                "#No separating space",
                "    # Four leading spaces",
            ]
        )

        preview = self.render(source)

        heading_tags = [tag for tag in preview.tags if tag[0].startswith("heading")]
        self.assertEqual(heading_tags, [("heading4", 0, 7, "Trimmed")])
        self.assertEqual(
            preview.content,
            "Trimmed\n"
            "####### Too many hashes\n"
            "#No separating space\n"
            "    # Four leading spaces\n",
        )


if __name__ == "__main__":
    unittest.main()
