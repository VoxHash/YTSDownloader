"""Unit tests for native sidecar discovery, IPC fallbacks, and normalize helpers."""

from __future__ import annotations

import json
import os
import tempfile
import unittest

from ytscore import native_bridge
from ytscore.companion import CompanionItem, consume_companion_inbox, parse_companion_payload
from ytscore.normalize import normalize_paths, normalize_urls, normalize_urls_python
from ytscore.process_prio import apply_process_priority


class NativeBridgeFallbackTests(unittest.TestCase):
    def setUp(self) -> None:
        native_bridge.clear_native_cache()
        self._prev_use = os.environ.get("YTS_USE_NATIVE")
        self._prev_dir = os.environ.get("YTS_NATIVE_DIR")

    def tearDown(self) -> None:
        native_bridge.clear_native_cache()
        if self._prev_use is None:
            os.environ.pop("YTS_USE_NATIVE", None)
        else:
            os.environ["YTS_USE_NATIVE"] = self._prev_use
        if self._prev_dir is None:
            os.environ.pop("YTS_NATIVE_DIR", None)
        else:
            os.environ["YTS_NATIVE_DIR"] = self._prev_dir

    def test_natives_disabled_finds_nothing(self) -> None:
        os.environ["YTS_USE_NATIVE"] = "0"
        native_bridge.clear_native_cache()
        self.assertIsNone(native_bridge.find_binary("yts-normalize"))
        self.assertFalse(native_bridge.native_status()["enabled"])

    def test_normalize_urls_python_fallback(self) -> None:
        os.environ["YTS_USE_NATIVE"] = "0"
        native_bridge.clear_native_cache()
        urls = normalize_urls(
            [
                "https://example.com/a",
                "  https://example.com/a  ",
                "https://example.com/b).",
                "not-a-url",
            ]
        )
        self.assertEqual(urls, ["https://example.com/a", "https://example.com/b"])

    def test_normalize_paths_python_fallback(self) -> None:
        os.environ["YTS_USE_NATIVE"] = "0"
        native_bridge.clear_native_cache()
        with tempfile.TemporaryDirectory() as tmp:
            nested = os.path.join(tmp, "x", "y")
            os.makedirs(nested)
            paths = normalize_paths([os.path.join(tmp, "x", ".", "y", "..", "y")])
            self.assertEqual(len(paths), 1)
            self.assertTrue(os.path.isdir(paths[0]))

    def test_normalize_uses_rust_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake = os.path.join(tmp, "yts-normalize")
            # Emit fixed JSON so we prove the IPC path is taken.
            with open(fake, "w", encoding="utf-8") as fh:
                fh.write(
                    "#!/bin/sh\n"
                    "echo '{\"ok\":true,\"items\":[\"https://from-native.example/z\"]}'\n"
                )
            os.chmod(fake, 0o755)
            os.environ["YTS_NATIVE_DIR"] = tmp
            os.environ["YTS_USE_NATIVE"] = "1"
            native_bridge.clear_native_cache()
            urls = normalize_urls(["https://ignored.example/a"])
            self.assertEqual(urls, ["https://from-native.example/z"])

    def test_consume_inbox_falls_back_without_go(self) -> None:
        os.environ["YTS_USE_NATIVE"] = "0"
        native_bridge.clear_native_cache()
        with tempfile.TemporaryDirectory() as tmp:
            inbox = os.path.join(tmp, "inbox")
            os.makedirs(inbox)
            jsonl = os.path.join(tmp, "companion_inbox.jsonl")
            drop = os.path.join(inbox, "batch.txt")
            with open(drop, "w", encoding="utf-8") as fh:
                fh.write("https://example.com/one\nhttps://example.com/two\n")
            items = consume_companion_inbox(inbox_dir=inbox, jsonl_path=jsonl)
            self.assertEqual(
                [i.url for i in items],
                ["https://example.com/one", "https://example.com/two"],
            )
            self.assertTrue(os.path.isfile(drop + ".processed"))

    def test_consume_inbox_uses_go_sidecar(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake = os.path.join(tmp, "yts-inbox")
            payload = json.dumps({"url": "https://from-go.example/v", "title": "Go"})
            with open(fake, "w", encoding="utf-8") as fh:
                fh.write(f"#!/bin/sh\necho '{payload}'\n")
            os.chmod(fake, 0o755)
            os.environ["YTS_NATIVE_DIR"] = tmp
            os.environ["YTS_USE_NATIVE"] = "1"
            native_bridge.clear_native_cache()
            items = consume_companion_inbox(
                inbox_dir=os.path.join(tmp, "missing"),
                jsonl_path=os.path.join(tmp, "missing.jsonl"),
            )
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0].url, "https://from-go.example/v")
            self.assertEqual(items[0].title, "Go")

    def test_parse_payload_still_works_with_ruby_disabled(self) -> None:
        os.environ["YTS_USE_NATIVE"] = "0"
        native_bridge.clear_native_cache()
        items = parse_companion_payload(
            json.dumps({"url": "https://example.com/r", "title": "R"})
        )
        self.assertEqual(len(items), 1)
        self.assertIsInstance(items[0], CompanionItem)
        self.assertEqual(items[0].title, "R")

    def test_apply_process_priority_noop(self) -> None:
        status = apply_process_priority(nice=0, idle_io=False)
        self.assertTrue(status["ok"])
        self.assertEqual(status["via"], "noop")

    def test_apply_process_priority_native_mock(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake = os.path.join(tmp, "yts-prio")
            with open(fake, "w", encoding="utf-8") as fh:
                fh.write(
                    "#!/bin/sh\n"
                    "echo '{\"ok\":true,\"pid\":1,\"nice\":5,\"ionice_idle\":true,\"warnings\":[]}'\n"
                )
            os.chmod(fake, 0o755)
            os.environ["YTS_NATIVE_DIR"] = tmp
            os.environ["YTS_USE_NATIVE"] = "1"
            native_bridge.clear_native_cache()
            status = apply_process_priority(pid=1, nice=5, idle_io=True)
            self.assertEqual(status["via"], "native")
            self.assertEqual(status["nice"], 5)
            self.assertTrue(status["ionice_idle"])


class NativeNormalizeParityTests(unittest.TestCase):
    def test_python_helper_matches_extract_rules(self) -> None:
        text = "see https://a.example/1 and https://a.example/1 again"
        self.assertEqual(
            normalize_urls_python([text]),
            ["https://a.example/1"],
        )


class SuiteOffscreenWithoutNativesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        os.environ["YTS_USE_NATIVE"] = "0"

    def test_suite_window_starts(self) -> None:
        from PyQt6.QtWidgets import QApplication

        from ytscore.settings import Settings
        from ytsgui.main_window import SuiteWindow

        app = QApplication.instance() or QApplication([])
        win = SuiteWindow(settings=Settings(max_workers=1, process_idle_io=False))
        try:
            # Offscreen Suite boots with natives disabled; Settings expose priority controls.
            self.assertEqual(win.settings_process_nice.value(), 0)
            self.assertFalse(win.settings_process_idle_io.isChecked())
            self.assertTrue(hasattr(win, "_poll_companion_inbox"))
            self.assertTrue(callable(win._poll_companion_inbox))
        finally:
            win.close()
            _ = app


if __name__ == "__main__":
    unittest.main()
