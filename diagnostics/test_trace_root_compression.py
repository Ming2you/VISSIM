"""Transport-only root-compression QA; never import a traffic model."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
import zlib

from diagnostics import evaluation_trace as base
from diagnostics import evaluation_trace_storage as legacy
from diagnostics.prepare_trace_root_compression_patch import proposal_module, installed_proposal, ROOT


class RootCompressionTests(unittest.TestCase):
    def folder(self):
        temp=tempfile.TemporaryDirectory(prefix='test_root_blob_',dir=ROOT/'diagnostics')
        self.addCleanup(temp.cleanup)
        return Path(temp.name)

    def test_same_key_and_bytes_old_dag_new_root_and_mutable_content(self):
        proposed=proposal_module();path=self.folder()/'mixed.sqlite'
        value=base.canonical({1:{'cfg':list(range(1000))},'1':[-0.0,0.0,'한글']})
        old=legacy.Store(path);key=old.put(value);old.close()
        new=proposed.Store(path);self.addCleanup(new.close)
        self.assertEqual(proposed.dump(new.get(key)),legacy.dump(value))
        changed=deepcopy(value);changed['extra']=['new root']
        other=new.put(changed)
        self.assertEqual(other,base.digest(changed))
        blob=new.conn.execute('SELECT descriptor FROM snapshots WHERE key=?',(other,)).fetchone()[0]
        self.assertTrue(blob.startswith(proposed._ROOT_JSON_ZLIB))
        self.assertEqual(proposed.dump(new.get(other)),legacy.dump(changed))
        self.assertEqual(new.put(changed),other)
        changed['extra'].append('mutation')
        third=new.put(changed)
        self.assertNotEqual(third,other)
        self.assertEqual(new.get(other)['extra'],['new root'])
        self.assertLessEqual(new.cache_bytes,new.cache_limit)

    def test_wrong_valid_content_truncation_trailing_stream_and_size_rejected(self):
        proposed=proposal_module();store=proposed.Store(self.folder()/'trace.sqlite');self.addCleanup(store.close)
        key=store.put({'value':-0.0});blob=store.conn.execute('SELECT descriptor FROM snapshots').fetchone()[0]
        def encode(value):
            raw=proposed.dump(value).encode()
            return proposed._ROOT_JSON_ZLIB+len(raw).to_bytes(8,'big')+zlib.compress(raw,1)
        wrong=encode({'value':'other'})
        badlen=bytearray(blob);badlen[len(proposed._ROOT_JSON_ZLIB)+7]^=1
        huge=blob[:len(proposed._ROOT_JSON_ZLIB)]+b'\xff'*8+blob[len(proposed._ROOT_JSON_ZLIB)+8:]
        for bad in (wrong,blob[:-1],blob+b'junk',bytes(badlen),huge,proposed._ROOT_JSON_ZLIB):
            with self.subTest(kind=len(bad)):
                store.conn.execute('UPDATE snapshots SET descriptor=? WHERE key=?',(bad,key))
                with self.assertRaises(ValueError):store.get(key)
        store.conn.execute('UPDATE snapshots SET descriptor=? WHERE key=?',(blob,key))
        self.assertEqual(store.get(key),{'value':-0.0})

    def test_legacy_synthetic_capture_reencoded_all_snapshots_exact(self):
        from diagnostics.evaluation_trace_local_synthetic import execute
        from diagnostics.evaluation_trace_local import collection
        source=self.folder();target=self.folder()
        execute(source,'monitor')  # Current DAG writer, small arithmetic fixture.
        before=collection(source)
        self.assertTrue(before['valid'],before['errors'])
        proposed=proposal_module()
        for item in source.iterdir():
            if item.suffix!='.sqlite':(target/item.name).write_bytes(item.read_bytes())
        src=next(source.glob('evaluation_*.sqlite'));dst=target/src.name
        original=sqlite3.connect(src);clone=sqlite3.connect(dst)
        original.backup(clone);original.close();clone.close()
        store=proposed.Store(dst)
        keys=[row[0] for row in store.conn.execute('SELECT key FROM snapshots')]
        for key in keys:
            value=store.get(key);store.conn.execute('DELETE FROM snapshots WHERE key=?',(key,))
            self.assertEqual(store.put(value),key)
            self.assertEqual(proposed.hash_json(store.get(key)),key)
        store.close()
        for path in target.glob('*.json'):
            doc=json.loads(path.read_text())
            if 'storage' in doc:
                doc['storage']['sha256']=hashlib.sha256(dst.read_bytes()).hexdigest()
                path.write_text(json.dumps(doc),encoding='utf-8')
        with installed_proposal():
            after=collection(target)
        self.assertTrue(after['valid'],after['errors'])
        self.assertEqual(before['v1_comparison_sha256'],after['v1_comparison_sha256'])
        self.assertEqual(before['comparison_sha256'],after['comparison_sha256'])

    def test_fresh_interpreter_uses_root_writer_and_collector(self):
        folder=self.folder()
        code="""import json,sys,sqlite3
from pathlib import Path
from diagnostics.prepare_trace_root_compression_patch import installed_proposal
with installed_proposal() as storage:
 from diagnostics.evaluation_trace_local_synthetic import execute
 from diagnostics.evaluation_trace_local import collection
 folder=Path(sys.argv[1]);value=execute(folder,'monitor');report=collection(folder)
 db=sqlite3.connect(next(folder.glob('evaluation_*.sqlite')))
 descriptors=[row[0] for row in db.execute('SELECT descriptor FROM snapshots')];db.close()
 assert descriptors and all(x.startswith(storage._ROOT_JSON_ZLIB) for x in descriptors)
 assert report['valid'],report['errors']
 print(json.dumps({'valid':True,'snapshot_count':len(descriptors),'value':value}))
"""
        run=subprocess.run([sys.executable,'-X','utf8','-c',code,str(folder)],cwd=ROOT,capture_output=True,text=True,timeout=20)
        self.assertEqual(run.returncode,0,run.stderr)
        self.assertTrue(json.loads(run.stdout)['valid'])


if __name__=='__main__':unittest.main()
