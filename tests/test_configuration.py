import unittest

from configuration import ConfigurationError, validate_settings


class ConfigurationTests(unittest.TestCase):
    def test_supported_urls(self):
        for scheme in ("postgres", "postgresql", "postgresql+psycopg2"):
            with self.subTest(scheme=scheme):
                result = validate_settings({
                    "DB_URL": f"{scheme}://user:pass@localhost:5432/test?sslmode=require",
                    "SENHA_ADM": "test-password",
                })
                self.assertTrue(result.database_url.startswith("postgresql"))
                self.assertNotIn("test-password", repr(result))

    def test_invalid_settings_do_not_leak_values(self):
        for url in (None, 123, "", "secret-value", "sqlite:///test",
                    "postgresql+psycopg://u:p@host/db", "postgresql://host/db",
                    "postgresql://u:p@host", "postgresql://u:p@host:wrong/db",
                    "postgresql://u:p@host:70000/db"):
            with self.subTest(url=url):
                with self.assertRaises(ConfigurationError) as error:
                    validate_settings({"DB_URL": url, "SENHA_ADM": "secret-value"})
                self.assertNotIn("secret-value", str(error.exception))

    def test_admin_password_is_required(self):
        for password in (None, "", "  ", 123):
            with self.subTest(password=password):
                with self.assertRaises(ConfigurationError):
                    validate_settings({"DB_URL": "postgresql://u:p@host/db",
                                       "SENHA_ADM": password})
