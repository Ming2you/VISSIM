from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from types import SimpleNamespace as NS

from diagnostics import evaluation_trace as base
from diagnostics.evaluation_trace_local import Targets,collection
from diagnostics.evaluation_trace_local_synthetic import ToyLocal,specs,selector,enable,disable,execute
from diagnostics.evaluation_trace_synthetic import toy_control

ROOT=Path(__file__).resolve().parents[1]


class LocalTraceTests(unittest.TestCase):
    def folder(self):
        folder=tempfile.TemporaryDirectory(prefix='test_local_trace_',dir=ROOT/'diagnostics')
        self.addCleanup(folder.cleanup)
        return Path(folder.name)

    def docs(self,folder):
        from diagnostics.evaluation_trace_storage import load_document
        return [load_document(p,expand=True) for p in folder.glob('local_evaluation_*.json')]

    def test_actual_source_targets_counter_operands(self):
        targets=Targets()
        self.assertEqual(len(targets.targets),26)
        meters=[s for s in targets.targets.values() if s.get('score')=='meter_branch'][0]
        self.assertEqual(len(meters['meter_operands']),10)
        self.assertEqual(sum(o['score']=='best_cost' for o in meters['meter_operands'].values()),5)
        self.assertEqual(sum(o['meter']=='trial' for o in meters['meter_operands'].values()),4)
        self.assertEqual(targets.changed(),[])

    def test_selected_complete_scores_and_transport_hashes(self):
        baseline=execute(self.folder(),'off')
        collections=[]
        for backend in ('profile','monitor'):
            folder=self.folder()
            self.assertEqual(execute(folder,backend),baseline)
            col=collection(folder)
            self.assertTrue(col['valid'],col['errors']);collections.append(col)
            doc=self.docs(folder)[0]
            candidates=[r for r in doc['rows'] if r['event']=='candidate']
            self.assertEqual(len(candidates),5)
            self.assertEqual([float.fromhex(r['score']['float_hex']) for r in candidates],[4.,11.,15.,16.,17.])
            phases=[r for r in doc['rows'] if r['kind']=='phase_candidate' and r['event']=='return']
            self.assertEqual([float.fromhex(r['result']['float_hex']) for r in phases],[4.,7.])
            # Four component calculations coexist with two phase candidate scores;
            # the component is explicitly a nested layer, not another candidate.
            self.assertEqual(sum(r['kind']=='local_physical_component' and r['event']=='return' for r in doc['rows']),4)
        self.assertEqual(collections[0]['v1_comparison_sha256'],collections[1]['v1_comparison_sha256'])
        self.assertEqual(collections[0]['comparison'],collections[1]['comparison'])

    def test_exception_is_unchanged_and_trace_invalid(self):
        folder=self.folder();handle=enable(folder,'monitor')
        try:
            with self.assertRaisesRegex(ValueError,'synthetic selected failure'):
                ToyLocal().fail(NS(stock=2.),NS(rate=1.),toy_control())
        finally:disable(handle)
        doc=self.docs(folder)[0]
        self.assertFalse(doc['valid']);self.assertEqual(doc['unmatched_calls'],0)
        self.assertTrue(any(e.get('event')=='unwind' for e in doc['errors']))

    def test_foreign_first_call_does_not_disable_main_selected_code(self):
        folder=self.folder();handle=enable(folder,'monitor')
        obj=ToyLocal();args=(NS(stock=2.),NS(rate=1.),toy_control())
        try:
            thread=threading.Thread(target=obj.run,args=args);thread.start();thread.join()
            expected=obj.run(*args)
        finally:disable(handle)
        self.assertEqual(expected[0],(20.,4.,2))
        doc=self.docs(folder)[0]
        self.assertTrue(doc['valid'],doc['errors'])
        self.assertEqual(sum(r['event']=='candidate' for r in doc['rows']),5)
        parent=json.loads(next(p for p in folder.glob('evaluation_*.json') if not p.name.endswith('.started.json')).read_text())
        self.assertGreater(parent['monitoring']['counts']['foreign_thread_events'],0)
        self.assertEqual(parent['monitoring']['counts']['frame_mismatch'],0)

    def test_missing_and_changed_snapshot_rejected(self):
        # Retain the legacy JSON corruption regression; v3 DB/node corruption
        # has its own bounded-storage test.
        folder=self.folder();execute(folder,'profile')
        path=next(folder.glob('local_evaluation_*.json'));doc=json.loads(path.read_text())
        key=next(iter(doc['values']));doc['values'][key]='tampered'
        path.write_text(json.dumps(doc),encoding='utf-8')
        self.assertIn('local_snapshot_hash_mismatch',collection(folder)['errors'])
        path.unlink()
        self.assertIn('missing_local_process_sidecar',collection(folder)['errors'])

    def test_source_counter_count_change_rejected(self):
        config=specs();config[0]['count']=2
        with self.assertRaisesRegex(ValueError,'counter count changed'):Targets(config)

    def test_operational_flow_memory_changes_comparison_without_changing_result(self):
        columns=[];outputs=[]
        for flow in (1.,2.):
            folder=self.folder();handle=enable(folder,'monitor');obj=ToyLocal()
            obj._wu=NS(_last_offramp_flow={'OR':flow},_has_last_offramp_flow=True)
            obj._prev_coupling={'arr_S_p1':3.}
            try:outputs.append(obj.run(NS(stock=2.),NS(rate=1.),toy_control()))
            finally:disable(handle)
            columns.append(collection(folder))
        self.assertEqual(outputs[0],outputs[1])
        self.assertEqual(columns[0]['v1_comparison_sha256'],columns[1]['v1_comparison_sha256'])
        self.assertNotEqual(columns[0]['comparison_sha256'],columns[1]['comparison_sha256'])
        self.assertEqual(len(columns[0]['comparison']['parent']['operational']),2)

    def test_monitor_disables_unselected_locations_and_installs_no_global_profile(self):
        folder=self.folder();handle=enable(folder,'monitor')
        def noise():return sum((1,2,3))
        try:
            self.assertIsNone(sys.getprofile());self.assertIsNone(sys.gettrace())
            noise()
            before=handle.counts['discovery_callbacks']
            for _ in range(5000):noise()
            after=handle.counts['discovery_callbacks']
        finally:disable(handle)
        self.assertLess(after-before,5)

    def test_monitor_real_callback_ownership_is_checked(self):
        folder=self.folder();handle=enable(folder,'monitor')
        sys.monitoring.register_callback(handle.tool_id,sys.monitoring.events.PY_RETURN,lambda *a:None)
        result=disable(handle)
        self.assertFalse(result['valid'])
        self.assertTrue(any(e['event']=='monitor_callback_replaced' for e in result['errors']))
        self.assertIsNone(sys.monitoring.get_tool(handle.tool_id))
        self.assertIsNone(sys.getprofile());self.assertIsNone(sys.gettrace())

    def test_conflicting_profile_monitoring_and_trace_rejected(self):
        from diagnostics.evaluation_trace_monitor import install
        callback=lambda *a:None
        for setter in (sys.setprofile,sys.settrace):
            setter(callback)
            try:
                with self.assertRaisesRegex(RuntimeError,'coexist'):install(self.folder(),include_local=False)
            finally:setter(None)
        sys.monitoring.use_tool_id(2,'test competing profiler')
        try:
            with self.assertRaisesRegex(RuntimeError,'coexist'):install(self.folder(),include_local=False)
        finally:sys.monitoring.free_tool_id(2)

    def test_fresh_spawn_task_keys_and_stdout_exact(self):
        results=[];cols=[]
        for backend in ('off','profile','monitor'):
            folder=self.folder()
            run=subprocess.run([sys.executable,'-X','utf8','-m','diagnostics.evaluation_trace_local_synthetic',str(folder),
                                '--backend',backend,'--spawn'],cwd=ROOT,capture_output=True,text=True,timeout=30)
            self.assertEqual(run.returncode,0,run.stderr)
            self.assertEqual(run.stderr,'');results.append(run.stdout)
            if backend!='off':
                col=collection(folder)
                self.assertTrue(col['valid'],col['errors']);self.assertEqual(col['worker_task_count'],4)
                self.assertEqual(col['process_count'],3);cols.append(col)
        self.assertEqual(results[0],results[1]);self.assertEqual(results[1],results[2])
        self.assertEqual(cols[0]['v1_comparison_sha256'],cols[1]['v1_comparison_sha256'])
        self.assertEqual(cols[0]['comparison'],cols[1]['comparison'])


if __name__=='__main__':unittest.main()
