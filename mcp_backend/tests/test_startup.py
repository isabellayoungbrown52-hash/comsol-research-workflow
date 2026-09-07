"""Exercise the real Windows launcher token lifecycle without COMSOL or a server."""
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
POWERSHELL = shutil.which("powershell.exe")


@unittest.skipUnless(os.name == "nt" and POWERSHELL, "Windows PowerShell required")
class StartupTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="comsol-launcher-test-")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        scripts = self.root / "scripts"
        scripts.mkdir()
        self.launcher = scripts / "start-mcp.ps1"
        shutil.copyfile(ROOT / "scripts/start-mcp.ps1", self.launcher)
        self.token_file = self.root / ".mcp-token"

    def prepare(self, token=None, transport="streamable-http"):
        env = {k: v for k, v in os.environ.items() if k.upper() != "COMSOL_MCP_TOKEN"}
        if token is not None:
            env["COMSOL_MCP_TOKEN"] = token
        return subprocess.run(
            [POWERSHELL, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
             "-File", str(self.launcher), "-Transport", transport, "-PrepareTokenOnly"],
            env=env, cwd=self.root, capture_output=True, timeout=20,
        )

    def assert_success(self, process):
        self.assertEqual(process.returncode, 0, process.stderr.decode(errors="replace"))

    def test_first_setup_and_fresh_shell_restart_reuse_token(self):
        first = self.prepare()
        self.assert_success(first)
        value = self.token_file.read_bytes()
        self.assertGreaterEqual(len(value), 32)
        self.assertNotIn(value, first.stdout + first.stderr)
        second = self.prepare()
        self.assert_success(second)
        self.assertEqual(value, self.token_file.read_bytes())
        self.assertNotIn(value, second.stdout + second.stderr)

    def test_existing_environment_is_preserved_on_migration(self):
        value = secrets.token_urlsafe(32)
        self.assert_success(self.prepare(value))
        self.assertEqual(self.token_file.read_text(), value)
        self.assert_success(self.prepare())
        self.assertEqual(self.token_file.read_text(), value)

    def test_conflicting_environment_does_not_replace_saved_token(self):
        value = secrets.token_urlsafe(32)
        self.token_file.write_text(value)
        other = secrets.token_urlsafe(32)
        result = self.prepare(other)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.token_file.read_text(), value)
        self.assertNotIn(value.encode(), result.stdout + result.stderr)
        self.assertNotIn(other.encode(), result.stdout + result.stderr)

    def test_corrupt_file_fails_without_regeneration(self):
        for invalid in ("", "short", "a" * 40):
            with self.subTest(invalid=invalid):
                self.token_file.write_text(invalid)
                result = self.prepare()
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(self.token_file.read_text(), invalid)

    def test_http_and_sse_share_the_same_token(self):
        self.assert_success(self.prepare())
        value = self.token_file.read_bytes()
        self.assert_success(self.prepare(transport="sse"))
        self.assertEqual(self.token_file.read_bytes(), value)

    def test_invalid_environment_is_not_saved(self):
        result = self.prepare("Bearer " + secrets.token_urlsafe(32))
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.token_file.exists())


if __name__ == "__main__":
    unittest.main()
