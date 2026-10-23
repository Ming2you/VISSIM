import hashlib
import json
import os
from pathlib import Path
import subprocess
import unittest
import tempfile
from unittest.mock import patch
from tools.sdmpc31 import runtime_package as rp

HERE=Path(__file__).resolve().parent
class RuntimePackageTests(unittest.TestCase):
    def fixture(self):
        temporary = tempfile.TemporaryDirectory(prefix='vissim-package-test-')
        self.addCleanup(temporary.cleanup)
        base = Path(temporary.name)
        source=base/'source';source.mkdir(parents=True)
        for rel,body in {
            'evaluation/controller.py':'VALUE=1\n',
            'config/main.json':'{"extends":"../config/base.json","command":"diagnostics/replay/commands/action.json"}',
            'config/base.json':'{"model":355}',
            'diagnostics/replay/commands/action.json':'{"vsl":90}',
            'diagnostics/old/evaluations.json':'{"old":true}',
            'diagnostics/handoff/evidence.part001':'DO NOT COPY',
        }.items():
            p=source/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(body,encoding='utf8')
        for args in [('init',),('add','--','evaluation/controller.py'),('-c','user.name=StorageTest','-c','user.email=storage@test.invalid','commit','-m','fixture')]:
            subprocess.run(['git','-C',str(source),*args],check=True,capture_output=True)
        spec=base/'inputs.json'
        result=rp.prepare(source,['config/main.json'],[],spec)
        return base,source,spec,result

    def test_selected_inputs_exclude_archives_and_keep_dependencies(self):
        _,_,_,r=self.fixture()
        self.assertIn('config/base.json',r['files'])
        self.assertIn('diagnostics/replay/commands/action.json',r['files'])
        self.assertNotIn('diagnostics/old/evaluations.json',r['files'])
        self.assertNotIn('diagnostics/handoff/evidence.part001',r['files'])

    def test_two_launches_share_objects_without_linking_editable_source(self):
        base,source,spec,r=self.fixture()
        a=base/'run1';b=base/'run2';store=base/'store'
        rp.freeze(source,spec,a,store);m=rp.freeze(source,spec,b,store)
        for rel,pin in r['files'].items():
            self.assertTrue(os.path.samefile(a/rel,b/rel))
            self.assertFalse(os.path.samefile(source/rel,a/rel))
            self.assertEqual(rp.digest(a/rel),pin)
        (source/'evaluation/controller.py').write_text('VALUE=2\n')
        self.assertEqual((a/'evaluation/controller.py').read_text(),'VALUE=1\n')
        actual={rel:rp.digest(p) for rel,p in rp.files(a) if rel!='FREEZE.json'}
        self.assertEqual(actual,m['files'])
        self.assertEqual(m['tree_sha256'],hashlib.sha256(json.dumps(actual,sort_keys=True,separators=(',',':')).encode()).hexdigest())

    def test_stale_inputs_refused_before_launch_tree_created(self):
        base,source,spec,_=self.fixture()
        (source/'config/base.json').write_text('{"changed":true}')
        with self.assertRaises(ValueError):rp.freeze(source,spec,base/'run',base/'store')
        self.assertFalse((base/'run').exists())

    def test_escaping_path_refused(self):
        base,source,spec,r=self.fixture()
        r['files']['../outside.json']='0'*64;rp.save(spec,r)
        with self.assertRaises(ValueError):rp.freeze(source,spec,base/'run',base/'store')

    def test_network_assets_follow_actual_inpx_references(self):
        base,source,_,_=self.fixture()
        network=source/rp.CANONICAL/'network.inpx'
        network.parent.mkdir(parents=True,exist_ok=True)
        network.write_text('<network><backgroundImage filename="#data#map.jpg"/>'
                           '<backgroundImage filename="missing-map.png"/>'
                           '<signalController supplyFile1="lights.sig"/></network>')
        (network.parent/'map.jpg').write_bytes(b'background data')
        (network.parent/'unreferenced.jpg').write_bytes(b'unused map')
        (network.parent/'lights.sig').write_bytes(b'signal program')
        r=rp.prepare(source,['config/main.json'],[],base/'assets-inputs.json')
        self.assertIn(rp.CANONICAL+'map.jpg',r['files'])
        self.assertIn(rp.CANONICAL+'lights.sig',r['files'])
        self.assertNotIn(rp.CANONICAL+'unreferenced.jpg',r['files'])
        self.assertEqual([x['original_reference'] for x in r['preexisting_unresolved_backgrounds']],['missing-map.png'])

    def test_full_object_uses_verified_shard_without_exceeding_link_limit(self):
        base,source,_,_=self.fixture()
        original=source/'evaluation/controller.py';digest=rp.digest(original)
        target=base/'objects'/digest
        with patch.object(rp,'SHARED_LINK_LIMIT',3):
            first=rp.put_object(original,target,digest)
            os.link(first,base/'alias1');os.link(first,base/'alias2')
            second=rp.put_object(original,target,digest)
            self.assertFalse(os.path.samefile(first,second))
            self.assertEqual(first.stat().st_nlink,3)
            self.assertEqual(rp.digest(second),digest)
            self.assertEqual(rp.put_object(original,target,digest),second)
            self.assertFalse(os.path.samefile(original,second))

if __name__=='__main__':unittest.main(verbosity=2)
