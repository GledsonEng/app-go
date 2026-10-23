from pathlib import Path
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest


APP = Path(__file__).resolve().parents[1] / "app.py"


class StartupTests(unittest.TestCase):
    def test_missing_secrets_stop_with_actionable_message(self):
        app = AppTest.from_file(str(APP)).run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.error), 1)
        self.assertIn("DB_URL", app.error[0].value)

    def test_home_needs_no_connection_or_package_installer(self):
        app = AppTest.from_file(str(APP))
        app.secrets.update(DB_URL="postgresql://user:pass@localhost/test",
                           SENHA_ADM="test-password")
        with patch("subprocess.run", side_effect=AssertionError("Runtime subprocess")), \
             patch("subprocess.call", side_effect=AssertionError("Runtime installer")), \
             patch("sqlalchemy.engine.Engine.connect", side_effect=AssertionError("DB on home")):
            app.run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.error), 0)
