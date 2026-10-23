import importlib.util,pathlib,subprocess,tempfile,unittest
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('package',pathlib.Path(__file__).with_name('build-package.py'));package=importlib.util.module_from_spec(spec);spec.loader.exec_module(package)
class SourceSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=pathlib.Path(self.tmp.name)
        self.git('init','-q');self.git('config','user.name','Test');self.git('config','user.email','test@example.invalid')
    def git(self,*args):return subprocess.check_output(['git','-C',str(self.root),*args],stderr=subprocess.DEVNULL)
    def commit(self):self.git('add','.');self.git('commit','-qm','fixture')
    def test_generated_link_rejected(self):
        (self.root/'deps').symlink_to('/private/build/deps');self.commit()
        with self.assertRaises(ValueError):package.check_source_snapshot(self.root)
    def test_escaping_link_rejected(self):
        (self.root/'helper').symlink_to('../outside');self.commit()
        with self.assertRaises(ValueError):package.check_source_snapshot(self.root)
    def test_relative_compatibility_link_allowed(self):
        (self.root/'source').mkdir();(self.root/'source/code').write_text('fixture');(self.root/'compat').symlink_to('source');self.commit();package.check_source_snapshot(self.root)
    def test_dirty_package_inputs_rejected(self):
        (self.root/'gnome/extension').mkdir(parents=True)
        code=self.root/'gnome/extension/extension.js';code.write_text('original');self.commit()
        package.check_package_checkout(self.root)
        code.write_text('uncommitted')
        with self.assertRaises(ValueError):package.check_package_checkout(self.root)
    def test_untracked_program_file_rejected(self):
        (self.root/'marker').write_text('original');self.commit()
        (self.root/'gnome/extension').mkdir(parents=True)
        (self.root/'gnome/extension/helper.js').write_text('untracked')
        with self.assertRaises(ValueError):package.check_package_checkout(self.root)
    def test_system_toolchain_without_private_deps(self):
        with patch.object(package,'ROOT',self.root):self.assertEqual(package.resolve_sysroot(),pathlib.Path('/usr'))
    def test_incomplete_private_toolchain_does_not_fall_back(self):
        (self.root/'deps').mkdir()
        with patch.object(package,'ROOT',self.root),self.assertRaises(ValueError):package.resolve_sysroot()
    def test_foreign_build_checkout_rejected(self):
        with patch.object(package,'ROOT',self.root):
            package.check_build_checkout(self.root/'renderer/source')
            with self.assertRaises(ValueError):package.check_build_checkout(self.root/'other/renderer/source')
if __name__=='__main__':unittest.main()
