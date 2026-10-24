"""Unit tests for browser companion inbox handoff (desktop remains the downloader)."""

from __future__ import annotations

import json
import os
import tempfile
import unittest

from ytscore.companion import (
    CompanionItem,
    consume_companion_inbox,
    ensure_inbox_layout,
    parse_companion_payload,
    write_companion_items,
)


class ParseCompanionPayloadTests(unittest.TestCase):
    def test_plain_urls(self) -> None:
        text = "see https://example.com/a and https://example.com/b\n"
        items = parse_companion_payload(text)
        self.assertEqual(
            [i.url for i in items],
            ["https://example.com/a", "https://example.com/b"],
        )

    def test_json_object(self) -> None:
        payload = json.dumps(
            {
                "url": "https://example.com/v/1",
                "title": "Clip",
                "source": "browser-companion",
                "page_url": "https://example.com/watch",
            }
        )
        items = parse_companion_payload(payload)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].url, "https://example.com/v/1")
        self.assertEqual(items[0].title, "Clip")
        self.assertEqual(items[0].source, "browser-companion")
        self.assertEqual(items[0].page_url, "https://example.com/watch")

    def test_json_urls_array(self) -> None:
        payload = json.dumps(
            {
                "urls": [
                    "https://example.com/1",
                    {"url": "https://example.com/2", "title": "Two"},
                ]
            }
        )
        items = parse_companion_payload(payload)
        self.assertEqual([i.url for i in items], ["https://example.com/1", "https://example.com/2"])
        self.assertEqual(items[1].title, "Two")

    def test_ndjson(self) -> None:
        text = "\n".join(
            [
                json.dumps({"url": "https://example.com/a"}),
                json.dumps({"url": "https://example.com/b", "title": "B"}),
                "# comment",
                "https://example.com/c",
            ]
        )
        items = parse_companion_payload(text)
        self.assertEqual(
            [i.url for i in items],
            ["https://example.com/a", "https://example.com/b", "https://example.com/c"],
        )
        self.assertEqual(items[1].title, "B")

    def test_dedupe(self) -> None:
        items = parse_companion_payload(
            "https://example.com/x\nhttps://example.com/x\n"
        )
        self.assertEqual(len(items), 1)

    def test_quest_companion_document(self) -> None:
        payload = json.dumps(
            {
                "schema": 1,
                "source": "quest-companion",
                "urls": [
                    {
                        "schema": 1,
                        "url": "https://example.com/watch?v=quest",
                        "source": "quest-companion",
                    }
                ],
            }
        )
        items = parse_companion_payload(payload)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].url, "https://example.com/watch?v=quest")
        self.assertEqual(items[0].source, "quest-companion")


class ConsumeCompanionInboxTests(unittest.TestCase):
    def test_jsonl_and_drop_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            inbox_dir = os.path.join(tmp, "inbox")
            jsonl_path = os.path.join(tmp, "companion_inbox.jsonl")
            ensure_inbox_layout(inbox_dir=inbox_dir, jsonl_path=jsonl_path)

            write_companion_items(
                jsonl_path,
                [
                    CompanionItem(
                        url="https://example.com/from-jsonl",
                        title="JL",
                        source="ext",
                    )
                ],
            )
            drop_path = os.path.join(inbox_dir, "batch.json")
            with open(drop_path, "w", encoding="utf-8") as fh:
                json.dump(
                    {"urls": ["https://example.com/from-file", "https://example.com/from-jsonl"]},
                    fh,
                )

            items = consume_companion_inbox(inbox_dir=inbox_dir, jsonl_path=jsonl_path)
            urls = [i.url for i in items]
            self.assertIn("https://example.com/from-jsonl", urls)
            self.assertIn("https://example.com/from-file", urls)
            self.assertEqual(len(urls), 2)

            # Consumed: JSONL truncated, drop file renamed.
            with open(jsonl_path, "r", encoding="utf-8") as fh:
                self.assertEqual(fh.read().strip(), "")
            self.assertFalse(os.path.isfile(drop_path))
            self.assertTrue(os.path.isfile(drop_path + ".processed"))

            # Second poll is empty.
            again = consume_companion_inbox(inbox_dir=inbox_dir, jsonl_path=jsonl_path)
            self.assertEqual(again, [])


class CompanionSuiteSmokeTests(unittest.TestCase):
    def test_suite_creates_inbox_layout(self) -> None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication

        from ytsgui.main_window import SuiteWindow
        from ytscore.settings import Settings

        app = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as tmp:
            cwd = os.getcwd()
            try:
                os.chdir(tmp)
                cfg = os.path.join(tmp, "config.ini")
                with open(cfg, "w", encoding="utf-8") as fh:
                    fh.write("[SETTINGS]\nTHEME = SuiteDark\n")
                win = SuiteWindow(settings=Settings(theme="SuiteDark"), config_path=cfg)
                self.assertTrue(os.path.isdir(os.path.join(tmp, ".ytsdownloader", "inbox")))
                self.assertTrue(hasattr(win, "_companion_timer"))
                win.close()
            finally:
                os.chdir(cwd)
            del app


if __name__ == "__main__":
    unittest.main()
