#!/usr/bin/env python3
"""Cleanup must protect live sessions, symlinks, mounts and non-whitelisted data."""
import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

module_path = Path(__file__).resolve().parents[1] / 'scripts/maintenance.py'
spec = importlib.util.spec_from_file_location('maintenance', module_path)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class MaintenanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.target = self.root / 'runtime/manager-test'
        self.target.mkdir(parents=True)
        (self.target / 'data').write_bytes(b'fixture')
        self.protected = self.root / 'runtime/live-extension'
        self.protected.mkdir()
        (self.protected / 'module.js').write_text('protected')

    def test_preview_and_whitelisted_removal(self):
        with patch.object(m, 'process_references', return_value=([], [])):
            preview = m.clean(self.root)
            self.assertTrue(self.target.exists())
            self.assertEqual(preview['removed'], [])
            result = m.clean(self.root, True)
        self.assertFalse(self.target.exists())
        self.assertTrue((self.protected / 'module.js').exists())
        self.assertEqual(result['removed'], ['runtime/manager-test'])
        self.assertTrue(list((self.root / 'reports/maintenance').glob('*.json')))
        with self.assertRaises(RuntimeError):
            m.validate_path(self.root, 'runtime/live-extension')

    def test_symlink_and_mount_protection(self):
        (self.target / 'data').unlink()
        self.target.rmdir()
        self.target.symlink_to(self.protected, target_is_directory=True)
        with self.assertRaises(RuntimeError):
            m.clean(self.root, True)
        self.target.unlink()
        self.target.mkdir()
        with patch.object(m, 'mounted_paths', return_value=[self.target / 'mounted']):
            with self.assertRaises(RuntimeError):
                m.clean(self.root, True)

    def test_inaccessible_process_refuses_removal(self):
        with patch.object(m, 'process_references', return_value=([], [{'pid': 1}])):
            with self.assertRaises(RuntimeError):
                m.clean(self.root, True)
        self.assertTrue(self.target.exists())

    def test_live_process_environment_and_cwd(self):
        env = dict(os.environ, XDG_CONFIG_HOME=str(self.target / 'config'))
        child = subprocess.Popen(['sleep', '30'], cwd=self.target, env=env)
        try:
            references, _ = m.process_references([self.target])
            self.assertIn(child.pid, [r['pid'] for r in references])
            with self.assertRaises(RuntimeError):
                m.clean(self.root, True)
            self.assertTrue(self.target.exists())
        finally:
            child.terminate()
            child.wait()

if __name__ == '__main__':
    unittest.main()
