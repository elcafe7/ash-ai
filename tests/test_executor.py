import os
import tempfile
import unittest
import stat
from types import SimpleNamespace

from ashlib.executor import _log_path, execute_plan
from ashlib.plan import save_current


PLAN = {"schema_version": 1, "summary": "Check", "status": "ready", "reason": None,
        "steps": [{"command": "pwd", "why": "Test", "risk": "read_only", "expected": "okay"}]}


class ExecutorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old = os.environ.get("ASH_AI_HOME")
        os.environ["ASH_AI_HOME"] = self.temp.name

    def tearDown(self):
        if self.old is None: os.environ.pop("ASH_AI_HOME", None)
        else: os.environ["ASH_AI_HOME"] = self.old
        self.temp.cleanup()

    def test_decline_does_not_run(self):
        called = []
        code, _ = execute_plan(PLAN, confirm=lambda _: "no", runner=lambda *args, **kwargs: called.append(args))
        self.assertEqual(code, 1)
        self.assertEqual(called, [])

    def test_literal_yes_runs_without_shell(self):
        seen = []
        def runner(args, **kwargs):
            seen.append((args, kwargs))
            return SimpleNamespace(stdout="okay\n", returncode=0)
        code, log = execute_plan(PLAN, confirm=lambda _: "yes", runner=runner)
        self.assertEqual(code, 0)
        self.assertEqual(seen[0][0], ["pwd"])
        self.assertTrue(log.exists())
        self.assertEqual(stat.S_IMODE(log.stat().st_mode), 0o600)

    def test_read_only_still_requires_literal_yes(self):
        called = []
        code, _ = execute_plan(PLAN, confirm=lambda _: "y", runner=lambda *args, **kwargs: called.append(args))
        self.assertEqual(code, 1)
        self.assertEqual(called, [])

    def test_plan_mode_and_log_names(self):
        old = os.umask(0o022)
        try:
            save_current(PLAN)
        finally:
            os.umask(old)
        from ashlib.config import plan_path, runs_dir
        self.assertEqual(stat.S_IMODE(plan_path().stat().st_mode), 0o600)
        first, second = _log_path(), _log_path()
        self.assertNotEqual(first, second)
        self.assertEqual(stat.S_IMODE(runs_dir().stat().st_mode), 0o700)

    def test_credentials_rejected_before_display(self):
        bad = {**PLAN, "steps": [{**PLAN["steps"][0], "command": "pkg install token=secret"}]}
        with self.assertRaises(ValueError): execute_plan(bad, confirm=lambda _: "yes")

    def test_configured_key_redacted_from_command(self):
        from ashlib.config import write_config
        write_config({"provider": "openai", "model": "demo", "api_key": "secret-value"})
        from ashlib.config import redact_text
        self.assertEqual(redact_text("$ command --token secret-value", load_config_for_test()), "$ command --token [REDACTED]")


def load_config_for_test():
    from ashlib.config import load_config
    return load_config()
