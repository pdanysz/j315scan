from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from changelog_extract import extract


class ChangelogTests(unittest.TestCase):
    def test_extract_current(self):
        text = Path(__file__).resolve().parents[1].joinpath("CHANGELOG.md").read_text()
        body = extract(text, "0.2.0")
        self.assertIn("English", body)
        self.assertNotIn("## [0.1.0]", body)

    def test_missing(self):
        with self.assertRaises(SystemExit):
            extract("## [1.0.0]\n\nhi\n", "9.9.9")


if __name__ == "__main__":
    unittest.main()
