"""Host checks for Meta Quest Horizon Store packaging readiness (source markers)."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUEST_MANIFEST = ROOT / "android" / "app" / "src" / "quest" / "AndroidManifest.xml"
GRADLE = ROOT / "android" / "app" / "build.gradle.kts"
CHECK_SCRIPT = ROOT / "scripts" / "check_quest_packaging.sh"


class QuestPackagingSourceTests(unittest.TestCase):
    def test_quest_manifest_store_packaging_markers(self) -> None:
        text = QUEST_MANIFEST.read_text(encoding="utf-8")
        self.assertIn('android:installLocation="auto"', text)
        self.assertIn("android.hardware.vr.headtracking", text)
        self.assertIn('android:required="false"', text)
        self.assertIn('android:excludeFromRecents="true"', text)
        self.assertIn("com.oculus.supportedDevices", text)
        self.assertIn("com.oculus.intent.category.2D", text)
        self.assertIn("com.oculus.application_type", text)
        self.assertIn("panel", text)
        # Immersive VR category must not sneak into the 2D panel slice.
        self.assertNotIn("com.oculus.intent.category.VR", text)

    def test_quest_flavor_sdk_and_abi(self) -> None:
        text = GRADLE.read_text(encoding="utf-8")
        self.assertIn("minSdk = 29", text)
        self.assertIn("targetSdk = 34", text)
        self.assertIn("arm64-v8a", text)
        self.assertIn("questRelease", text)
        self.assertIn('versionName = "0.13.0"', text)

    def test_check_quest_packaging_script_source_gate(self) -> None:
        self.assertTrue(CHECK_SCRIPT.is_file())
        # Source-only path: script exits 0 even when release APK is absent.
        proc = subprocess.run(
            ["bash", str(CHECK_SCRIPT), "/nonexistent-quest-release.apk"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("quest AndroidManifest.xml packaging markers", proc.stdout)
        self.assertIn("WARN: APK not built yet", proc.stdout)


if __name__ == "__main__":
    unittest.main()
