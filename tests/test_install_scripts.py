import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class InstallScriptTests(unittest.TestCase):
    def setUp(self):
        self.install = (ROOT / "install.sh").read_text()
        self.uninstall = (ROOT / "uninstall.sh").read_text()

    def test_release_scripts_do_not_accept_path_overrides(self):
        for script in (self.install, self.uninstall):
            self.assertNotRegex(script, r"ASH_AI_HOME|ASH_SOURCE_DIR")

    def test_uninstaller_requires_sentinel_before_deleting_root(self):
        sentinel_check = self.uninstall.index('[ ! -f "$SENTINEL" ]')
        delete_root = self.uninstall.index('rm -rf "$APP_ROOT"')
        self.assertLess(sentinel_check, delete_root)
        self.assertIn("exit 2", self.uninstall[sentinel_check:delete_root])
        self.assertIn('SENTINEL=$APP_ROOT/install.json', self.uninstall)

    def test_install_stages_and_verifies_before_replacing_app(self):
        self.assertLess(self.install.index('cp -R "$SOURCE_DIR/src" "$STAGE/app"'),
                        self.install.index('mv "$APP_DIR" "$BACKUP"'))
        self.assertIn('[ ! -f "$STAGE/app/ash.py" ]', self.install)

    def test_install_never_creates_a_shell_parent_directories(self):
        self.assertIn('DOCUMENTS_DIR=$HOME/Documents', self.install)
        self.assertIn('[ ! -d "$DOCUMENTS_DIR" ] || [ ! -w "$DOCUMENTS_DIR" ]', self.install)
        self.assertNotIn('mkdir -p "$HOME/Documents', self.install)
        self.assertNotIn('mkdir -p "$DOCUMENTS_DIR"', self.install)

    def test_launcher_guard_and_bounded_backups(self):
        self.assertIn("Refusing to overwrite non-ash launcher", self.install)
        self.assertIn('[ "$count" -ge 5 ]', self.install)
        self.assertIn('[ "$n" -le 5 ]', self.install)

    def test_uninstall_removes_only_marked_profile_block(self):
        self.assertIn('MARKER="# ash-ai PATH BEGIN"', self.uninstall)
        self.assertIn('END_MARKER="# ash-ai PATH END"', self.uninstall)
        self.assertIn('awk -v start="$MARKER" -v finish="$END_MARKER"', self.uninstall)
        self.assertNotIn('rm -rf "$HOME', self.uninstall)

    def test_docs_describe_extracted_install_and_plaintext_key_storage(self):
        for name in ("README.md", "SPEC.md"):
            content = (ROOT / name).read_text()
            self.assertRegex(content, re.compile(r"extracted", re.I))
            self.assertRegex(content, re.compile(r"plaintext", re.I))
            self.assertNotRegex(content, re.compile(r"curl\s+[^\n]*\|\s*sh", re.I))
            self.assertNotRegex(content, re.compile(r"Keychain.{0,50}(?:secure|equivalent)|(?:secure|equivalent).{0,50}Keychain", re.I))


if __name__ == "__main__":
    unittest.main()
