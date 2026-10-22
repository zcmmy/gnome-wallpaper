import hashlib,json,pathlib,tempfile,unittest
from verify_sources import verify

class SourceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=pathlib.Path(self.temp.name);payload=b'synthetic source'
        (self.root/'example.tar.gz').write_bytes(payload)
        digest=hashlib.sha256(payload).hexdigest()
        (self.root/'example.dsc').write_text(f'Format: 3.0 (native)\nSource: example\nVersion: 1:2.0\nChecksums-Sha256:\n {digest} {len(payload)} example.tar.gz\n')
        self.manifest={'libraries':[{'source_package':'example','source_version':'1:2.0'}]}
        self.index()
    def index(self):
        files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in self.root.iterdir() if p.name!='sources.json'}
        (self.root/'sources.json').write_text(json.dumps({'packages':[['example','1:2.0']],'files':files}))
    def test_exact_source(self):
        self.assertEqual(verify(self.manifest,self.root)['packages'],1)
    def test_modified_archive(self):
        (self.root/'example.tar.gz').write_bytes(b'wrong source');self.index()
        with self.assertRaisesRegex(ValueError,'Descriptor/index mismatch'):verify(self.manifest,self.root)
    def test_wrong_source_version(self):
        p=self.root/'example.dsc';p.write_text(p.read_text().replace('1:2.0','1:2.1'));self.index()
        with self.assertRaisesRegex(ValueError,'Missing exact source'):verify(self.manifest,self.root)
    def test_descriptor_required(self):
        (self.root/'example.dsc').unlink();self.index()
        with self.assertRaisesRegex(ValueError,'Missing exact source'):verify(self.manifest,self.root)

if __name__=='__main__':unittest.main()
