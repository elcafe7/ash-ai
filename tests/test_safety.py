import unittest

from ashlib.safety import validate_command


class SafetyTests(unittest.TestCase):
    def test_allowlist(self):
        allowed = [
            ("pkg install jq", "network"), ("pip install foo", "network"),
            ("pip3 install foo", "network"), ("python3 -m pip install foo", "network"),
            ("help -l", "read_only"), ("which python3", "read_only"),
            ("command -v ls", "read_only"), ("pwd", "read_only"),
            ("ls", "read_only"), ("ls Documents", "read_only"),
            ("pkg --version", "read_only"), ("pip --version", "read_only"),
            ("pip3 --version", "read_only"), ("python3 --version", "read_only"),
        ]
        for command, risk in allowed:
            with self.subTest(command=command):
                self.assertEqual(validate_command(command, risk)[0], command.split()[0])

    def test_rejects_unsafe_and_unlisted_commands(self):
        for command in ("rm -rf x", "sh -c id", "python3 -c x", "curl x", "find . -exec id", "echo okay", "ls ../x", "ls /tmp"):
            with self.subTest(command=command), self.assertRaises(ValueError):
                validate_command(command, "read_only")

    def test_network_install_requires_network_risk(self):
        with self.assertRaises(ValueError):
            validate_command("pkg install jq", "read_only")
        with self.assertRaises(ValueError):
            validate_command("pip install foo", "read_only")

