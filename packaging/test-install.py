import importlib.util,json,mmap,pathlib,tempfile,unittest,zipfile,hashlib,stat
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('installer',pathlib.Path(__file__).with_name('install.py'));installer=importlib.util.module_from_spec(spec);spec.loader.exec_module(installer)
class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=pathlib.Path(self.tmp.name)
    def archive(self,version='one',extra=None):
        files={'metadata.json':json.dumps({'uuid':installer.UUID}).encode(),'data':version.encode()}
        manifest={'format':1,'uuid':installer.UUID,'version':version,'backend_protocol':1,'files':{n:{'sha256':hashlib.sha256(b).hexdigest(),'mode':0o644} for n,b in files.items()}}
        files['package-manifest.json']=json.dumps(manifest).encode()
        if extra:files.update(extra)
        target=self.root/(version+'.zip')
        with zipfile.ZipFile(target,'w') as z:
            for name,content in files.items():
                info=zipfile.ZipInfo(name);info.external_attr=(stat.S_IFREG|0o644)<<16;z.writestr(info,content)
        return target
    def test_extract_and_atomic_update_mapped_file(self):
        old=self.root/'installed';old.mkdir();installer.extract(self.archive(),old)
        with (old/'data').open('rb') as f:
            memory=mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ)
            new=self.root/'stage';new.mkdir();installer.extract(self.archive('two'),new);backup=installer.exchange(new,old)
            self.assertEqual(memory[:],b'one');self.assertEqual((old/'data').read_bytes(),b'two');self.assertEqual((backup/'data').read_bytes(),b'one');memory.close()
    def test_tampered_and_unlisted_files(self):
        for extra in [{'unlisted':b'bad'},{'data':b'bad'}]:
            dest=self.root/'stage';dest.mkdir(exist_ok=True)
            with self.assertRaises(ValueError):installer.extract(self.archive(extra=extra),dest)
            import shutil;shutil.rmtree(dest)
    def test_traversal_rejected(self):
        dest=self.root/'stage';dest.mkdir()
        with self.assertRaises(ValueError):installer.extract(self.archive(extra={'../escape':b'bad'}),dest)
        self.assertFalse((self.root/'escape').exists())
    def test_legacy_settings_restore_only_program_keys(self):
        with patch.object(installer.subprocess,'run') as run:
            installer.restore_legacy_program_settings(self.root,{'wallpaperengine-path':'/old program/renderer','engine':'wallpaperengine'})
        self.assertEqual([c.args[0][3] for c in run.call_args_list],['wallpaperengine-path','engine'])
        self.assertNotIn('fps',str(run.call_args_list));self.assertNotIn('library-root',str(run.call_args_list))
    def test_rollback_preserves_user_data(self):
        current=self.root/'installed';current.mkdir();(current/'data').write_text('new');old=self.root/'old';old.mkdir();(old/'data').write_text('old');user=self.root/'wallpapers';user.mkdir();(user/'static.png').write_text('user')
        installer.exchange(old,current);self.assertEqual((current/'data').read_text(),'old');self.assertEqual((user/'static.png').read_text(),'user')
if __name__=='__main__':unittest.main()
