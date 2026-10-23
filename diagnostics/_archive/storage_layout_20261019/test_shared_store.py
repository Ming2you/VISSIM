import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest
import uuid

HERE = Path(__file__).resolve().parent
SHELL = shutil.which('pwsh') or shutil.which('powershell')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def record(p, root, exists=True):
    st = p.stat() if exists else None
    return dict(path=str(p), allowed_root=str(root), exists=exists,
                bytes=st.st_size if st else 120000,
                last_write_utc_ticks=st.st_mtime_ns//100+621355968000000000 if st else 0)

class SharedStoreTests(unittest.TestCase):
    def fixture(self):
        root = HERE/'tests'/'fixtures'/uuid.uuid4().hex
        root.mkdir(parents=True)
        run = root/'run'; run.mkdir()
        source = run/'a.json'; source.write_bytes(b'input-data\n'*12000)
        duplicate = run/'b.json'; shutil.copy2(source,duplicate)
        digest = sha(source)
        anchor = record(source,run)
        anchor['copy_required'] = False
        plan = dict(schema='vissim-shared-store-migration/v1',status='planned_not_applied',
                    review={'extension_summary':{'':{'bytes':0}}},
                    manifest_pins={},groups=[dict(sha256=digest,object=str(root/'store'/digest),
                    anchor=anchor,aliases=[record(source,run),record(duplicate,run),record(run/'restored.json',run,False)])])
        return root, run, plan

    def invoke(self,root,plan,execute=True):
        path=root/'plan.json'; path.write_text(json.dumps(plan),encoding='utf8')
        cmd=[SHELL,'-NoProfile','-File',str(HERE/'apply_shared_store.ps1'),'-PlanPath',str(path),
             '-ExpectedSha256',sha(path),'-TestFixture']
        if execute: cmd.append('-Execute')
        return subprocess.run(cmd,capture_output=True,encoding='utf-8',errors='replace',
                              creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))

    def test_shared_identity_content_readonly_and_repeat_guard(self):
        root,run,plan=self.fixture()
        p=self.invoke(root,plan)
        self.assertEqual(p.returncode,0,p.stdout+p.stderr)
        obj=Path(plan['groups'][0]['object'])
        for alias in ('a.json','b.json','restored.json'):
            self.assertTrue(os.path.samefile(obj,run/alias))
            self.assertEqual(sha(obj),sha(run/alias))
        with self.assertRaises(PermissionError):
            (run/'b.json').write_bytes(b'corrupt')
        self.assertNotEqual(self.invoke(root,plan).returncode,0)

    def test_stale_source_refused_before_mutation(self):
        root,run,plan=self.fixture()
        (run/'b.json').write_bytes(b'changed')
        self.assertNotEqual(self.invoke(root,plan).returncode,0)
        self.assertFalse((root/'migration_journal.jsonl').exists())
        self.assertEqual((run/'b.json').read_bytes(),b'changed')

    def test_path_escape_refused(self):
        root,run,plan=self.fixture()
        plan['groups'][0]['aliases'][1]['allowed_root']='C:/Windows'
        self.assertNotEqual(self.invoke(root,plan).returncode,0)
        self.assertFalse((root/'migration_journal.jsonl').exists())
        self.assertFalse(os.path.samefile(run/'a.json',run/'b.json'))

    def test_long_historical_paths_remain_readable(self):
        root,run,plan=self.fixture()
        target=run/('historical_'+'x'*70)/('nested_'+'y'*70)/'output.json'
        extended=Path('\\\\?\\'+str(target))
        extended.parent.mkdir(parents=True)
        shutil.copy2(run/'b.json',extended)
        item=record(extended,run)
        item['path']=str(target)
        plan['groups'][0]['aliases'].append(item)
        p=self.invoke(root,plan)
        self.assertEqual(p.returncode,0,p.stdout+p.stderr)
        self.assertTrue(os.path.samefile(extended,Path(plan['groups'][0]['object'])))
        self.assertEqual(extended.read_bytes(),(run/'a.json').read_bytes())

    def test_manifest_hashes_are_enforced_with_hashtable_parser(self):
        root,run,plan=self.fixture()
        pin=root/'frozen_manifest.json';pin.write_text('{"frozen":true}')
        plan['manifest_pins']={str(pin):sha(pin)}
        p=self.invoke(root,plan)
        self.assertEqual(p.returncode,0,p.stdout+p.stderr)
        root,run,plan=self.fixture()
        pin=root/'frozen_manifest.json';pin.write_text('{"frozen":true}')
        plan['manifest_pins']={str(pin):'0'*64}
        self.assertNotEqual(self.invoke(root,plan).returncode,0)
        self.assertFalse((root/'migration_journal.jsonl').exists())

if __name__=='__main__': unittest.main(verbosity=2)
