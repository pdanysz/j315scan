from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import DEFAULTS, default_pictures, load_config


class ConfigTests(unittest.TestCase):
    def test_default_outdir_is_pictures(self):
        pictures = default_pictures()
        self.assertEqual(pictures.name, "Pictures")
        self.assertEqual(Path(DEFAULTS["outdir"]).name, "Pictures")

    def test_load_has_required_keys(self):
        cfg = load_config()
        for key in ("host", "outdir", "language", "filename_prefix", "split"):
            self.assertIn(key, cfg)


if __name__ == "__main__":
    unittest.main()
