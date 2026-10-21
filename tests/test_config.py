import json
import os
import tempfile
import unittest
import stat
from pathlib import Path

from ashlib.config import clear_key, load_config, redact, write_config


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old = os.environ.get("ASH_AI_HOME")
        os.environ["ASH_AI_HOME"] = self.temp.name

    def tearDown(self):
        if self.old is None: os.environ.pop("ASH_AI_HOME", None)
        else: os.environ["ASH_AI_HOME"] = self.old
        self.temp.cleanup()

    def test_config_and_redaction(self):
        write_config({"provider": "openai", "base_url": "https://example.test/v1", "model": "test", "api_key": "secret-value"})
        self.assertEqual(load_config()["api_key"], "secret-value")
        self.assertEqual(load_config()["base_url"], "https://api.openai.com/v1")
        self.assertNotIn("base_url", json.loads((Path(self.temp.name) / "config.json").read_text()))
        self.assertEqual(stat.S_IMODE((Path(self.temp.name) / "config.json").stat().st_mode), 0o600)
        self.assertEqual(redact({"api_key": "secret-value"})["api_key"], "[REDACTED]")
        clear_key()
        self.assertEqual(load_config(require_key=False)["api_key"], "")
        self.assertNotIn("base_url", json.loads((Path(self.temp.name) / "config.json").read_text(encoding="utf-8")))
        with self.assertRaises(ValueError): load_config()

    def test_rejects_unknown_provider(self):
        with self.assertRaises(ValueError):
            write_config({"provider": "other", "base_url": "https://example.test/v1", "model": "test", "api_key": "key"})

    def test_legacy_tampered_url_is_ignored(self):
        path = Path(self.temp.name) / "config.json"
        path.write_text('{"provider":"xai","base_url":"https://evil.test","model":"m","api_key":"k"}')
        self.assertEqual(load_config()["base_url"], "https://api.x.ai/v1")
