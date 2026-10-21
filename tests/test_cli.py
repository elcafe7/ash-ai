import unittest
from unittest.mock import patch

from ashlib.cli import main


class CliTests(unittest.TestCase):
    def test_version(self):
        self.assertEqual(main(["version"]), 0)

    def test_unknown_command_is_task_and_needs_setup(self):
        self.assertEqual(main(["install", "jq"]), 1)

    def test_unknown_flag_is_usage_error_without_api_call(self):
        with patch("ashlib.cli.request_plan") as request:
            self.assertNotEqual(main(["--bogus"]), 0)
            request.assert_not_called()

    def test_run_yes_is_rejected(self):
        self.assertNotEqual(main(["run", "--yes"]), 0)

    def test_eof_and_interrupt_are_clean_cancellations(self):
        for exception in (EOFError(), KeyboardInterrupt()):
            with self.subTest(exception=type(exception).__name__), patch("builtins.input", side_effect=exception):
                self.assertEqual(main(["setup"]), 130)

    def test_setup_eof_is_clean_cancellation(self):
        with patch("builtins.input", side_effect=EOFError()):
            self.assertEqual(main(["setup"]), 130)

    def test_no_argument_starts_navigation_menu(self):
        with patch("builtins.input", return_value="q"):
            self.assertEqual(main([]), 0)
