import os
import tempfile
import unittest
from pathlib import Path

from ashlib.config import runs_dir, write_config
from ashlib.debugger import debug_report


class DebuggerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old = os.environ.get("ASH_AI_HOME")
        os.environ["ASH_AI_HOME"] = self.temp.name

    def tearDown(self):
        if self.old is None: os.environ.pop("ASH_AI_HOME", None)
        else: os.environ["ASH_AI_HOME"] = self.old
        self.temp.cleanup()

    def test_no_log_is_offline(self):
        report = debug_report()
        self.assertIn("Offline debugger: no AI/API request was made.", report)
        self.assertTrue(any("no previous run log" in line for line in report))

    def test_diagnoses_and_redacts(self):
        write_config({"provider": "openai", "base_url": "https://example.test/v1", "model": "test", "api_key": "private-key"})
        runs_dir().mkdir(parents=True)
        (runs_dir() / "20261021T000000Z.log").write_text("command not found private-key", encoding="utf-8")
        report = "\n".join(debug_report())
        self.assertIn("A command is unavailable", report)
        self.assertNotIn("private-key", report)
