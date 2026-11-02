"""Process / window-manager identity must stay unique vs sibling VoxHash apps."""

from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from ytscore.desktop_identity import (
    APP_NAME,
    DESKTOP_FILE_ID,
    ORGANIZATION_DOMAIN,
    ORGANIZATION_NAME,
    apply_desktop_identity,
    configure_qt_identity,
)


class DesktopIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from PyQt6.QtWidgets import QApplication

        # Prefer configuring before first QApplication when possible.
        if QApplication.instance() is None:
            configure_qt_identity()
        cls._app = QApplication.instance() or QApplication([])
        apply_desktop_identity(cls._app)

    def test_constants_are_unique_and_stable(self) -> None:
        self.assertEqual(ORGANIZATION_NAME, "VoxHash")
        self.assertEqual(ORGANIZATION_DOMAIN, "voxhash.dev")
        self.assertEqual(APP_NAME, "YTSDownloader")
        self.assertEqual(DESKTOP_FILE_ID, "ytsdownloader")
        self.assertNotEqual(APP_NAME, DESKTOP_FILE_ID)
        sibling_names = {
            "ForexSmartBot",
            "DB Storage Manager",
            "Telegram Multi-Account Message Sender",
            "HandForge",
        }
        self.assertNotIn(APP_NAME, sibling_names)
        sibling_desktop_ids = {
            "forexsmartbot",
            "db-storage-manager",
            "telegram-multi-account-sender",
            "dev.voxhash.telegram-multi-account-sender",
            "HandForge",
        }
        self.assertNotIn(DESKTOP_FILE_ID, sibling_desktop_ids)

    def test_qt_identity_fields(self) -> None:
        self.assertEqual(self._app.organizationName(), ORGANIZATION_NAME)
        self.assertEqual(self._app.organizationDomain(), ORGANIZATION_DOMAIN)
        self.assertEqual(self._app.applicationName(), APP_NAME)
        self.assertEqual(self._app.applicationDisplayName(), APP_NAME)
        self.assertEqual(self._app.desktopFileName(), DESKTOP_FILE_ID)

    def test_install_local_and_isolated_launcher(self) -> None:
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        script = os.path.join(root, "scripts", "install_local.sh")
        launcher = os.path.join(root, "scripts", "run_ytsdownloader.sh")
        with open(script, encoding="utf-8") as fh:
            text = fh.read()
        self.assertIn(f"StartupWMClass={APP_NAME}", text)
        self.assertIn(f"{DESKTOP_FILE_ID}.desktop", text)
        self.assertIn("run_ytsdownloader.sh", text)
        self.assertTrue(os.path.isfile(launcher))
        with open(launcher, encoding="utf-8") as fh:
            launch = fh.read()
        self.assertIn("setsid", launch)
        self.assertIn("QT_PLUGIN_PATH", launch)
        self.assertIn("main.py", launch)


if __name__ == "__main__":
    unittest.main()
