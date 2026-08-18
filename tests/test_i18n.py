from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from i18n import SUPPORTED, I18n, detect_language, resolve_language


class I18nTests(unittest.TestCase):
    def test_supported_keys_match_english(self):
        en = I18n("en")._load("en")
        self.assertTrue(en)
        for lang in SUPPORTED:
            table = I18n(lang)._load(lang)
            self.assertEqual(set(en), set(table), msg=lang)

    def test_fallback_unknown_key(self):
        self.assertEqual(I18n("en").t("not_a_real_key"), "not_a_real_key")

    def test_format(self):
        text = I18n("en").t("connecting", host="1.2.3.4")
        self.assertIn("1.2.3.4", text)

    def test_resolve(self):
        self.assertEqual(resolve_language("PL"), "pl")
        self.assertEqual(resolve_language("xx"), "en")
        self.assertIn(detect_language(), SUPPORTED)


if __name__ == "__main__":
    unittest.main()
