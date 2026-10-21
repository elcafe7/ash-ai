import unittest

from ashlib.plan import validate_plan


def valid_plan():
    return {"schema_version": 1, "summary": "Install jq", "status": "ready", "reason": None,
            "steps": [{"command": "pkg install jq", "why": "Install jq", "risk": "network", "expected": "success"}]}


class PlanTests(unittest.TestCase):
    def test_accepts_valid_plan(self):
        self.assertEqual(validate_plan(valid_plan())["status"], "ready")

    def test_rejects_shell_operators(self):
        for command in ("rm x", "sh -c id", "python3 -c id", "curl x", "find . -exec id", "echo hi; whoami", "echo $(id)", "echo x > file", "echo x | cat"):
            plan = valid_plan()
            plan["steps"][0]["command"] = command
            with self.assertRaises(ValueError):
                validate_plan(plan)

    def test_display_fields_reject_controls(self):
        for field, value in (("summary", "bad\x1b[31m"), ("reason", "bad\x1b]0;x\x07"), ("why", "bad\x1b"), ("expected", "bad\x07")):
            plan = valid_plan()
            if field in {"summary", "reason"}:
                plan[field] = value
            else:
                plan["steps"][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_plan(plan)

    def test_read_only_is_not_a_command_authorization(self):
        plan = valid_plan()
        plan["steps"][0].update(command="rm -rf data", risk="read_only")
        with self.assertRaises(ValueError):
            validate_plan(plan)

    def test_rejects_unsupported_with_steps(self):
        plan = valid_plan()
        plan["status"] = "unsupported"
        plan["reason"] = "No compatible method"
        with self.assertRaises(ValueError):
            validate_plan(plan)
