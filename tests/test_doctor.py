import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ashlib import doctor


class DoctorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        self.app = self.home / "Documents" / ".ash-ai" / "app"
        (self.app / "src" / "ashlib").mkdir(parents=True)
        self.launcher = self.home / "Documents" / "bin" / "ash"
        self.launcher.parent.mkdir(parents=True)
        self.launcher.write_text("#!/bin/sh\n", encoding="utf-8")
        self.launcher.chmod(0o755)
        (self.home / ".profile").write_text(
            '# ash-ai PATH BEGIN\nexport PATH="$HOME/Documents/bin:$PATH"\n# ash-ai PATH END\n',
            encoding="utf-8",
        )
        self.stack = patch.multiple(
            "ashlib.doctor",
            **{
                "load_config": lambda: {"api_key": "x"},
                "data_root": lambda: self.home / "Documents" / ".ash-ai",
            },
        )
        self.stack.start()
        self.home_patch = patch("pathlib.Path.home", return_value=self.home)
        self.home_patch.start()
        self.path_patch = patch.dict(os.environ, {"PATH": str(self.launcher.parent)})
        self.path_patch.start()

    def tearDown(self):
        self.path_patch.stop()
        self.home_patch.stop()
        self.stack.stop()
        self.temp.cleanup()

    def test_healthy_install_passes_app_launcher_path_and_profile_checks(self):
        findings = doctor.diagnose()
        self.assertFalse(any(item.startswith("FAIL:") for item in findings), findings)
        self.assertTrue(any("app files are present" in item for item in findings))
        self.assertTrue(any("launcher is executable" in item for item in findings))
        self.assertTrue(any("directory is on PATH" in item for item in findings))
        self.assertTrue(any("marked ash PATH block is present" in item for item in findings))

    def test_missing_curl_is_warning(self):
        with patch("ashlib.doctor.shutil.which", return_value=None):
            findings = doctor.diagnose()
        self.assertTrue(any(item.startswith("WARN:") and "curl" in item for item in findings))
        self.assertFalse(any(item.startswith("FAIL:") and "curl" in item for item in findings))

    def test_broken_path_and_profile_are_failures(self):
        (self.home / ".profile").write_text("# unrelated\n", encoding="utf-8")
        with patch.dict(os.environ, {"PATH": "/usr/bin"}):
            findings = doctor.diagnose()
        self.assertTrue(any(item.startswith("FAIL:") and "not on PATH" in item for item in findings))
        self.assertTrue(any(item.startswith("FAIL:") and "PATH block" in item for item in findings))

    def test_missing_app_or_nonexecutable_launcher_fails(self):
        (self.app / "src" / "ashlib").rmdir()
        self.launcher.chmod(0o644)
        findings = doctor.diagnose()
        self.assertTrue(any(item.startswith("FAIL:") and "app files" in item for item in findings))
        self.assertTrue(any(item.startswith("FAIL:") and "launcher" in item for item in findings))


if __name__ == "__main__":
    unittest.main()
