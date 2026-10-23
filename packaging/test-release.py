#!/usr/bin/env python3
"""Release assembly must accept make's empty exported build-directory variable."""
import os,pathlib,runpy,sys,tempfile,unittest
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[1]
class StopBeforeBuild(Exception):pass
class ReleasePaths(unittest.TestCase):
 def check_path(self,value,expected):
  with tempfile.TemporaryDirectory() as tmp:
   pathlib.Path(tmp,'sources.json').write_text('{}')
   with patch.dict(os.environ,{'WALLPAPER_DEPENDENCY_SOURCES':tmp}):
    if value is None:os.environ.pop('WALLPAPER_BUILD_DIR',None)
    else:os.environ['WALLPAPER_BUILD_DIR']=value
    with patch.object(sys,'argv',['package-release.py']),patch('subprocess.run',side_effect=StopBeforeBuild) as run:
     with self.assertRaises(StopBeforeBuild):runpy.run_path(str(ROOT/'integration/scripts/package-release.py'),run_name='__main__')
     args=run.call_args.args[0]
     self.assertEqual(args[args.index('--build-dir')+1],str(expected))
 def test_unset(self):self.check_path(None,ROOT/'build/package-renderer')
 def test_empty_from_make(self):self.check_path('',ROOT/'build/package-renderer')
 def test_explicit(self):self.check_path('/tmp/explicit-build','/tmp/explicit-build')
if __name__=='__main__':unittest.main()
