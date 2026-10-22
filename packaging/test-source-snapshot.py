import importlib.util,pathlib,subprocess,tempfile,unittest
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
if __name__=='__main__':unittest.main()
