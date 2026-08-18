from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from extract import extract_objects, save_scan_set


class ExtractTests(unittest.TestCase):
    def _page(self) -> Image.Image:
        arr = np.full((800, 600, 3), 254, dtype=np.uint8)
        arr[40:300, 30:260] = (40, 80, 160)
        arr[360:720, 300:560] = (160, 40, 40)
        return Image.fromarray(arr, "RGB")

    def test_finds_two_blocks(self):
        crops = extract_objects(self._page(), min_area_ratio=0.02)
        self.assertEqual(len(crops), 2)
        self.assertGreater(crops[0].image.size[0], 100)

    def test_save_set(self):
        img = self._page()
        crops = extract_objects(img, min_area_ratio=0.02)
        with tempfile.TemporaryDirectory() as tmp:
            paths = save_scan_set(img, crops, tmp, stamp="test", prefix="scan")
            self.assertEqual(len(paths), 2)
            self.assertTrue(all(p.exists() for p in paths))
            self.assertTrue(paths[0].name.startswith("scan-test-"))


if __name__ == "__main__":
    unittest.main()
