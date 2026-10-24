"""Storage transport checks only: no traffic endpoint or optimizer."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace as NS

from diagnostics import evaluation_trace as base
from diagnostics.evaluation_trace_storage import Store, DiskRows, DiskMap, NormalizedRows, streaming_hash, load_document
from diagnostics.evaluation_trace_local import collection
from diagnostics.evaluation_trace_local_synthetic import execute

ROOT = Path(__file__).resolve().parents[1]


class StorageTests(unittest.TestCase):
    def folder(self):
        temp = tempfile.TemporaryDirectory(prefix='test_trace_storage_',dir=ROOT/'diagnostics')
        self.addCleanup(temp.cleanup)
        return Path(temp.name)

    def test_lossless_typed_keys_signed_zero_and_subtree_refs(self):
        path = self.folder()/'trace.sqlite'
        store = Store(path)
        self.addCleanup(store.close)
        shared = {'cfg':list(range(400)), 'unicode':'한글', 'zero':-0.0}
        original = base.canonical({1:shared, '1':shared, 'bytes_are_values':['ref','fake']})
        key = store.put(original)
        self.assertEqual(key,base.digest(original))
        self.assertEqual(base.digest(store.get(key)),key)
        self.assertEqual(base.digest(store.get(key)),streaming_hash(store.get(key)))
        nodes = store.conn.execute('SELECT COUNT(*) FROM nodes').fetchone()[0]
        for i in range(20): store.put({'changing':i,'unchanged':original})
        # Changing roots re-use their exact nested nodes; no per-root cfg copy.
        self.assertLess(store.conn.execute('SELECT COUNT(*) FROM nodes').fetchone()[0],nodes+5)
        self.assertLessEqual(store.cache_bytes,store.cache_limit)

    def test_rows_maps_are_disk_owned_and_replay_order_is_exact(self):
        store = Store(self.folder()/'trace.sqlite')
        self.addCleanup(store.close)
        rows = DiskRows(store,'base_rows'); contexts = DiskMap(store,'base_contexts')
        payload = {'large':list(range(500))}
        key = base.digest(payload); contexts.setdefault(key,payload)
        expected=[]
        for ordinal in range(100):
            row={'ordinal':ordinal,'call':ordinal//2*2,'parent_call':None,
                 'context':key,'event':'enter' if ordinal%2==0 else 'return','kind':'synthetic',
                 'value':ordinal,'payload':payload}
            expected.append(row); rows.append(row)
        self.assertNotIsInstance(rows,list)
        self.assertEqual(len(rows),100);self.assertEqual(len(contexts),1)
        store.conn.commit()
        self.assertEqual(list(rows),expected)
        normalized=NormalizedRows(store.path,'base_rows')
        self.assertEqual(streaming_hash(normalized),base.digest(base.normalized_process(expected)))
        self.assertLessEqual(store.cache_bytes,1024*1024)
        self.assertLess(store.path.stat().st_size,500000)

    def test_legacy_profile_and_v3_hashes_are_identical(self):
        left,right=self.folder(),self.folder()
        self.assertEqual(execute(left,'profile'),execute(right,'monitor'))
        a,b=collection(left),collection(right)
        self.assertTrue(a['valid'],a['errors']);self.assertTrue(b['valid'],b['errors'])
        self.assertEqual(a['v1_comparison_sha256'],b['v1_comparison_sha256'])
        self.assertEqual(a['comparison_sha256'],b['comparison_sha256'])
        doc=load_document(next(right.glob('local_evaluation_*.json')))
        self.assertNotIsInstance(doc['rows'],list)
        self.assertNotIsInstance(doc['values'],dict)
        for p in right.glob('*.jsonl'):
            for line in p.read_text(encoding='utf-8').splitlines():
                item=json.loads(line)
                self.assertIn('snapshot',item)
                self.assertNotIn('operational_after',item)
                self.assertLess(len(line),1024)
        self.assertLess(next(right.glob('local_evaluation_*.json')).stat().st_size,10000)

    def test_database_tamper_and_missing_sidecar_fail_closed(self):
        folder=self.folder();execute(folder,'monitor')
        path=next(folder.glob('evaluation_*.sqlite'))
        conn=sqlite3.connect(path)
        try:
            conn.execute("UPDATE snapshots SET descriptor=? WHERE key=(SELECT key FROM snapshots LIMIT 1)",(b'["atom","tampered"]',))
            conn.commit()
        finally: conn.close()
        self.assertIn('trace_storage_hash_mismatch',collection(folder)['errors'])
        next(folder.glob('local_evaluation_*.json')).unlink()
        self.assertIn('missing_local_process_sidecar',collection(folder)['errors'])

    def test_current_content_shortcut_detects_nested_mutation(self):
        store=Store(self.folder()/'trace.sqlite');self.addCleanup(store.close)
        cfg={'nested':{'vector':list(range(1000))}}
        first=store.put(cfg)
        cfg['nested']['vector'][400]=-400
        second=store.put(cfg)
        self.assertNotEqual(first,second)
        self.assertEqual(store.get(first)['nested']['vector'][400],400)
        self.assertEqual(store.get(second)['nested']['vector'][400],-400)
        self.assertEqual(second,base.digest(cfg))

    def test_snapshot_content_checked_even_with_updated_file_checksum(self):
        folder=self.folder();execute(folder,'monitor')
        path=next(folder.glob('evaluation_*.sqlite'))
        conn=sqlite3.connect(path)
        try:
            key=conn.execute("SELECT snapshot FROM maps WHERE name='local_values' LIMIT 1").fetchone()[0]
            conn.execute('UPDATE snapshots SET descriptor=? WHERE key=?',(b'["atom","tampered"]',key))
            conn.commit()
        finally:conn.close()
        parent=next(p for p in folder.glob('evaluation_*.json') if not p.name.endswith('.started.json'))
        doc=json.loads(parent.read_text())
        doc['storage']['sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
        parent.write_text(json.dumps(doc),encoding='utf-8')
        self.assertTrue(any('Snapshot content hash mismatch' in error for error in collection(folder)['errors']))

    def test_all_row_channels_check_content_with_rewritten_file_checksum(self):
        for channel in ('base_rows','local_rows','local_operations','local_identity_provenance'):
            with self.subTest(channel=channel):
                folder=self.folder();execute(folder,'monitor')
                path=next(folder.glob('evaluation_*.sqlite'))
                parent=next(p for p in folder.glob('evaluation_*.json') if not p.name.endswith('.started.json'))
                store=Store(path)
                try:
                    if channel=='local_identity_provenance':
                        # The arithmetic toy has no phase cache address. Add a
                        # valid provenance-only record before corrupting it.
                        records=DiskRows(store,channel)
                        records.append({'signature_demand_id':123,'context_demand_id':123})
                        local_path=next(folder.glob('local_evaluation_*.json'))
                        local_doc=json.loads(local_path.read_text())
                        local_doc['identity_provenance_count']=len(records)
                        local_path.write_text(json.dumps(local_doc),encoding='utf-8')
                    key=store.conn.execute('SELECT snapshot FROM rows WHERE name=? LIMIT 1',(channel,)).fetchone()[0]
                    original=store.get(key)
                    changed={**original,'peer_tampered_value':'valid structure, wrong content key'}
                    # Every Merkle node remains valid; only the snapshot-key
                    # binding is wrong. Public row references stay untouched.
                    replacement=store._pack(changed)
                    store.conn.execute('UPDATE snapshots SET descriptor=? WHERE key=?',
                                       (base._dump(replacement).encode('utf-8'),key))
                finally:store.close()
                doc=json.loads(parent.read_text())
                doc['storage']['sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
                parent.write_text(json.dumps(doc),encoding='utf-8')
                result=collection(folder)
                self.assertFalse(result['valid'],result)
                self.assertTrue(any('Snapshot content hash mismatch' in error for error in result['errors']),result)

    def test_required_table_and_count_declarations_cannot_be_omitted(self):
        for local,field in ((False,'contexts'),(True,'contexts'),(True,'values'),(True,'operational'),(True,'identity_provenance')):
            with self.subTest(local=local,field=field):
                folder=self.folder();execute(folder,'monitor')
                pattern='local_evaluation_*.json' if local else 'evaluation_*.json'
                path=next(p for p in folder.glob(pattern) if not p.name.endswith('.started.json'))
                doc=json.loads(path.read_text())
                del doc['storage']['tables'][field]
                del doc[field+'_count']
                path.write_text(json.dumps(doc),encoding='utf-8')
                result=collection(folder)
                self.assertFalse(result['valid'],result)
                self.assertTrue(any('Trace table declaration mismatch' in error for error in result['errors']),result)

    def test_disk_parent_comparison_uses_one_iterator_without_indexing(self):
        store=Store(self.folder()/'trace.sqlite')
        self.addCleanup(store.close)
        rows=DiskRows(store,'base_rows');contexts=DiskMap(store,'base_contexts')
        context={'cfg':'same'};key=base.digest(context);contexts.setdefault(key,context)
        for call in range(30):
            for event in ('enter','return'):
                rows.append({'call':call,'parent_call':None,'context':key,'event':event,'kind':'synthetic'})
        store.conn.commit()
        class SinglePassRows(NormalizedRows):
            def __init__(self,path):
                super().__init__(path,'base_rows');self.iterations=0
            def __iter__(self):
                self.iterations+=1
                if self.iterations!=1:raise AssertionError('Repeated parent iteration')
                yield from super().__iter__()
            def __getitem__(self,index):raise AssertionError('Indexed prefix rescan')
            def __eq__(self,other):raise AssertionError('Second whole-sequence comparison')
        a,b=SinglePassRows(store.path),SinglePassRows(store.path)
        report=base.compare_collections(
            {'valid':True,'comparison':{'parent':a,'worker_tasks':[]}},
            {'valid':True,'comparison':{'parent':b,'worker_tasks':[]}})
        self.assertTrue(report['equal'],report)
        self.assertEqual((a.iterations,b.iterations),(1,1))
        self.assertEqual(report['left_parent_events'],60)

    def test_public_row_reference_and_disk_row_must_match(self):
        folder=self.folder();execute(folder,'monitor')
        path=next(folder.glob('local_evaluation_*.jsonl'))
        lines=path.read_text().splitlines();row=json.loads(lines[0]);row['snapshot']='0'*64
        lines[0]=json.dumps(row);path.write_text('\n'.join(lines)+'\n',encoding='utf-8')
        sidecar=path.with_suffix('.json');doc=json.loads(sidecar.read_text())
        doc['jsonl_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
        sidecar.write_text(json.dumps(doc),encoding='utf-8')
        self.assertTrue(any('JSONL/backing row mismatch' in error for error in collection(folder)['errors']))

    def test_exact_vendor_signature_identity_slot_is_pinned_by_structure(self):
        import ast
        path=ROOT/'vendor/NumSim-mine/src/controllers/priced_wu_link_controller.py'
        node=next(n for n in ast.walk(ast.parse(path.read_bytes()))
                  if isinstance(n,ast.FunctionDef) and n.name=='_phase_refine_signature')
        value=next(n.value for n in node.body if isinstance(n,ast.Return))
        self.assertIsInstance(value,ast.Tuple);self.assertEqual(len(value.elts),6)
        self.assertEqual(ast.dump(value.elts[1]),"Call(func=Name(id='id', ctx=Load()), args=[Name(id='demand', ctx=Load())], keywords=[])")

    def test_phase_identity_relation_values_and_bad_cache(self):
        from diagnostics.evaluation_trace_state import operational
        first=NS(urban_boundary={'X':4.});other=NS(urban_boundary={'X':4.})
        obj=NS(_phase_ctx_cache=((900.,id(first),(),(),(),()),{'demand':first}))
        raw=[]
        same=operational(obj,current_demand=first,identity_sink=raw.append)
        equal_value_new_object=operational(obj,current_demand=other,identity_sink=raw.append)
        self.assertNotEqual(base.digest(same),base.digest(equal_value_new_object))
        self.assertEqual(raw[0]['signature_demand_id'],id(first))
        self.assertEqual(raw[1]['current_demand_id'],id(other))
        # The full demand value remains material, independently of identity.
        other.urban_boundary['X']=5.
        self.assertNotEqual(base.digest(equal_value_new_object),base.digest(
            operational(obj,current_demand=other,identity_sink=raw.append)))
        obj._phase_ctx_cache=(obj._phase_ctx_cache[0],{'demand':other})
        with self.assertRaisesRegex(ValueError,'does not identify'):
            operational(obj,current_demand=other,identity_sink=raw.append)

    def test_fresh_process_identity_reallocation_only_is_equal(self):
        code="""from types import SimpleNamespace as N
from diagnostics.evaluation_trace_state import operational
from diagnostics.evaluation_trace import digest
import json
d=N(urban_boundary={'X':4.});o=N(_phase_ctx_cache=((900.,id(d),(),(),(),()),{'demand':d}))
p=[];v=operational(o,current_demand=d,identity_sink=p.append)
print(json.dumps({'hash':digest(v),'raw':p}))
"""
        results=[]
        for _ in range(2):
            run=subprocess.run([sys.executable,'-X','utf8','-c',code],cwd=ROOT,capture_output=True,text=True,timeout=15)
            self.assertEqual(run.returncode,0,run.stderr);results.append(json.loads(run.stdout))
        self.assertEqual(results[0]['hash'],results[1]['hash'])
        self.assertTrue(all(r['raw'][0]['signature_demand_id']==r['raw'][0]['context_demand_id'] for r in results))


if __name__=='__main__':unittest.main()
