import contextlib,fcntl,importlib.util,io,json,pathlib,shutil,signal,tempfile,unittest
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('worker',ROOT/'gnome/extension/helpers/dataWorker.py');worker=importlib.util.module_from_spec(spec);spec.loader.exec_module(worker)
class DataTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.base=pathlib.Path(self.temp.name);self.root=self.base/'目标 数据';self.source=self.base/'来源';self.source.mkdir()
        self.scene=self.source/'测试 空格';self.scene.mkdir();(self.scene/'project.json').write_text(json.dumps({'type':'scene','file':'scene.json'}));(self.scene/'scene.pkg').write_bytes(b'fixture');(self.scene/'static-background.png').write_bytes(b'user still')
        self.assets=self.base/'公共 assets';self.assets.mkdir()
        for name in ['shaders','models','scripts']:(self.assets/name).mkdir();(self.assets/name/'fixture').write_bytes(name.encode())
    def runop(self,**request):
        with contextlib.redirect_stdout(io.StringIO()):return worker.run(self.root,request)
    def test_import_and_duplicate(self):
        r=self.runop(operation='import',source=str(self.source));self.assertEqual(r['imported'],[self.scene.name]);self.assertEqual((self.root/'wallpapers'/self.scene.name/'static-background.png').read_bytes(),b'user still')
        (self.scene/'static-background.png').write_bytes(b'new source')
        self.assertEqual(self.runop(operation='import',source=str(self.source))['skipped'],[self.scene.name]);self.assertEqual((self.root/'wallpapers'/self.scene.name/'static-background.png').read_bytes(),b'user still')
    def test_migration_and_assets_named_wallpaper(self):
        self.scene.rename(self.source/'assets');r=self.runop(operation='migrate',source=str(self.source),assets=str(self.assets));self.assertEqual(r['imported'],['assets']);self.assertTrue((self.root/'wallpapers/assets/project.json').exists());self.assertTrue((self.root/'assets/shaders/fixture').exists())
    def test_cancel_leaves_no_partial_or_source_changes(self):
        with patch.object(worker,'emit',side_effect=worker.Cancelled('cancel')):
            with self.assertRaises(worker.Cancelled):self.runop(operation='import',source=str(self.source))
        self.assertFalse(list((self.root/'wallpapers').iterdir()));self.assertFalse(list(self.root.glob('.transaction-*')));self.assertTrue((self.scene/'static-background.png').exists())
    def test_links_and_invalid_entry(self):
        (self.scene/'link').symlink_to('/etc/passwd')
        with self.assertRaises(ValueError):self.runop(operation='import',source=str(self.source))
        (self.scene/'link').unlink();(self.scene/'project.json').write_text('{"type":"scene","file":"../escape"}')
        with self.assertRaises(ValueError):self.runop(operation='import',source=str(self.source))
    def test_assets_replace_confirmation(self):
        self.runop(operation='assets',assets=str(self.assets))
        with self.assertRaises(ValueError):self.runop(operation='assets',assets=str(self.assets))
        (self.assets/'shaders/fixture').write_bytes(b'updated');self.runop(operation='assets',assets=str(self.assets),replace=True);self.assertEqual((self.root/'assets/shaders/fixture').read_bytes(),b'updated')
    def test_journal_resume(self):
        self.runop(operation='assets',assets=str(self.assets));stage=self.root/'.transaction-test';stage.mkdir();shutil.copytree(self.scene,stage/'item-0');worker.atomic_json(stage/'journal.json',{'moves':[{'source':'item-0','target':'wallpapers/resumed'}]})
        self.runop(operation='status');self.assertTrue((self.root/'wallpapers/resumed/static-background.png').exists());self.assertFalse(stage.exists())
    def test_lock_and_version(self):
        self.runop(operation='status')
        with (self.root/'.write.lock').open() as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            with self.assertRaises(ValueError):self.runop(operation='import',source=str(self.source))
        (self.root/'library.json').write_text('{"version":999}')
        with self.assertRaises(ValueError):self.runop(operation='import',source=str(self.source))
    def test_managed_symlink_rejected(self):
        self.root.mkdir();(self.root/'wallpapers').symlink_to(self.source,target_is_directory=True)
        with self.assertRaises(ValueError):self.runop(operation='import',source=str(self.source))
        self.assertTrue((self.scene/'project.json').exists())
    def test_plan_and_space(self):
        plan=self.runop(operation='import',source=str(self.source),plan=True);self.assertGreater(plan['bytes'],0);self.assertFalse(list((self.root/'wallpapers').iterdir()))
        with patch.object(shutil,'disk_usage',return_value=type('Space',(),{'free':0})()):
            with self.assertRaises(ValueError):self.runop(operation='import',source=str(self.source))
if __name__=='__main__':unittest.main()
