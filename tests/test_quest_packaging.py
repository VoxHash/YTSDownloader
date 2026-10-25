"""Host checks for Meta Quest hybrid packaging + immersive shell markers."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUEST_MANIFEST = ROOT / "android" / "app" / "src" / "quest" / "AndroidManifest.xml"
GRADLE = ROOT / "android" / "app" / "build.gradle.kts"
IMMERSIVE = (
    ROOT
    / "android"
    / "app"
    / "src"
    / "quest"
    / "java"
    / "dev"
    / "voxhash"
    / "ytscompanion"
    / "quest"
    / "ImmersiveShellActivity.kt"
)
CHECK_SCRIPT = ROOT / "scripts" / "check_quest_packaging.sh"


class QuestPackagingSourceTests(unittest.TestCase):
    def test_quest_manifest_hybrid_markers(self) -> None:
        text = QUEST_MANIFEST.read_text(encoding="utf-8")
        self.assertIn('android:installLocation="auto"', text)
        self.assertIn("android.hardware.vr.headtracking", text)
        self.assertIn('android:excludeFromRecents="true"', text)
        self.assertIn("com.oculus.supportedDevices", text)
        self.assertIn("com.oculus.intent.category.2D", text)
        self.assertIn("com.oculus.intent.category.VR", text)
        self.assertIn("ImmersiveShellActivity", text)
        self.assertIn("libossdk.oculus.so", text)
        self.assertIn("uses-horizonos-sdk", text)

    def test_immersive_shell_source_exists(self) -> None:
        self.assertTrue(IMMERSIVE.is_file())
        text = IMMERSIVE.read_text(encoding="utf-8")
        self.assertIn("AppSystemActivity", text)
        self.assertIn("VRFeature", text)
        self.assertIn("ActivityPanelRegistration", text)
        self.assertIn("createPanelEntity", text)

    def test_quest_flavor_sdk_spatial_and_abi(self) -> None:
        text = GRADLE.read_text(encoding="utf-8")
        self.assertIn("minSdk = 29", text)
        self.assertIn("targetSdk = 34", text)
        self.assertIn("arm64-v8a", text)
        self.assertIn("questRelease", text)
        self.assertIn('versionName = "0.15.2"', text)
        self.assertIn("meta-spatial-sdk", text)

    def test_check_quest_packaging_script_source_gate(self) -> None:
        self.assertTrue(CHECK_SCRIPT.is_file())
        proc = subprocess.run(
            ["bash", str(CHECK_SCRIPT), "/nonexistent-quest-release.apk"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("hybrid packaging markers", proc.stdout)
        self.assertIn("WARN: APK not built yet", proc.stdout)


if __name__ == "__main__":
    unittest.main()
