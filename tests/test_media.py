"""PC-seitige Prüfungen für die synthetische Demo und das Dateiformat."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from check_loop import check, STRIDE


class MediaTests(unittest.TestCase):
    def test_demo_layout(self):
        demo = ROOT / "media" / "DEMO_10S.LOOP"
        count, duration = check(demo)
        self.assertEqual(count, 200)
        self.assertEqual(duration, 10.0)
        self.assertEqual(demo.stat().st_size, 200 * STRIDE)

    def test_firmware_values(self):
        source = (ROOT / "src" / "main.c").read_text(encoding="utf-8")
        self.assertIn('#define BUTTON_PIN       26u', source)
        self.assertIn('#define W                320u', source)
        self.assertIn('#define H                240u', source)
        self.assertIn('#define AUDIO_BYTES      6400u', source)
        self.assertIn('#define VIDEO_FILE       "0:/TEST.LOOP"', source)


if __name__ == '__main__':
    unittest.main()
