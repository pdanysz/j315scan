import inspect
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app


class OfflineGuiTests(unittest.TestCase):
    def test_except_var_must_be_copied_before_after_lambda(self):
        def late_e():
            try:
                raise OSError("timed out")
            except OSError as e:
                cb = lambda: str(e)
            return cb()

        with self.assertRaises(NameError):
            late_e()

        def captured():
            try:
                raise OSError("timed out")
            except OSError as e:
                msg = f"No scanner: {e}"
                cb = lambda m=msg: m
            return cb()

        self.assertEqual(captured(), "No scanner: timed out")

    def test_tk_root_method_not_shadowed(self):
        src = inspect.getsource(app.ScannerApp._build)
        self.assertNotIn("self._root =", src)
        self.assertTrue(callable(app.ScannerApp._root))

    def test_error_text_built_before_after(self):
        conn = inspect.getsource(app.ScannerApp.check_connection)
        scan = inspect.getsource(app.ScannerApp.start_scan)
        self.assertIn('self.t("no_scanner", error=e)', conn)
        self.assertIn("lambda m=msg", conn)
        self.assertIn('self.t("scan_failed", error=e)', scan)
        self.assertIn("lambda m=msg", scan)


if __name__ == "__main__":
    unittest.main()
