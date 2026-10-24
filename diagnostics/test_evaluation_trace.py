"""Synthetic-only trace QA: no traffic endpoint, optimizer or VISSIM runs."""
import cProfile
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace as NS

from diagnostics import evaluation_trace as trace

ROOT = Path(__file__).resolve().parents[1]


class EvaluationTraceTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ)
        self.env.start(); self.addCleanup(self.env.stop)
        for k in ('RW_DECISION_PROFILE_DIR','RW_PHASE_TRACE_DIR','RW_PHASE_COMMIT_TRACE_DIR',
                  'RW_EVALUATION_TRACE_DIR','RW_EVALUATION_TRACE_MANIFEST'):
            os.environ.pop(k,None)
        self.temp = tempfile.TemporaryDirectory(prefix='eval_trace_',dir=ROOT/'diagnostics')
        self.assertTrue(Path(self.temp.name).resolve().is_relative_to((ROOT/'diagnostics').resolve()))
        self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)

    def test_exact_float_and_timing_exclusion(self):
        from diagnostics.evaluation_trace_synthetic import toy_control
        a=toy_control(); b=toy_control()
        b.diagnostics['wu_faithful_solve_time_sec']=12345.
        self.assertEqual(trace.control(a),trace.control(b))
        b.vsl['FW']=float.fromhex(float(80).hex())+2**-45
        self.assertNotEqual(trace.control(a),trace.control(b))
        self.assertNotEqual(trace.canonical(0.),trace.canonical(-0.))
        self.assertNotEqual(trace.canonical({1:1}),trace.canonical({'1':1}))

    def test_nested_logical_calls_and_executed_controls(self):
        from diagnostics import evaluation_trace_synthetic as toy
        toy.init(); ctx=toy._PRICE_WORKER_CTX
        recorder=trace.install(self.path)
        answer=ctx['ctrl']._evaluate_full_candidate(0,ctx['previous'],ctx['state'],ctx['forecast'],ctx['previous'])
        doc=recorder.finish()
        self.assertTrue(doc['valid'],doc['errors'])
        enters=[r for r in doc['rows'] if r['event']=='enter']
        self.assertEqual(sum(r['kind']=='follower' for r in enters),1)
        self.assertEqual(sum(r['kind']=='endpoint' for r in enters),1)
        intervals=[r for r in enters if r['kind']=='executed_interval']
        self.assertEqual(len(intervals),2)
        self.assertNotEqual(intervals[0]['input']['control'],intervals[1]['input']['control'])
        self.assertEqual(answer.objective,81.)
        text=json.dumps(doc['comparison']);self.assertNotIn('wall_sec',text)

    def test_pfo_list_keeps_scores_not_performance_metadata(self):
        from diagnostics import evaluation_trace_synthetic as toy
        toy.init();ctx=toy._PRICE_WORKER_CTX
        rec=trace.install(self.path)
        ctx['ctrl']._evaluate_fallback_candidates(ctx['state'],ctx['forecast'],ctx['previous'],0)
        doc=rec.finish();self.assertTrue(doc['valid'],doc['errors'])
        row=[r for r in doc['rows'] if r['kind']=='leader_pfo' and r['event']=='return'][0]
        self.assertEqual(row['result'][0]['objective'],trace.canonical(-3.))
        # Timing provenance may legitimately contain the digits "456". Inspect
        # the excluded result metadata field, not unrelated performance clocks.
        self.assertNotIn('metadata',row['result'][0])
        self.assertNotIn('wall_time_sec',json.dumps(row['result']))

    def test_competing_hooks_refused_before_install(self):
        for name in ('RW_DECISION_PROFILE_DIR','RW_PHASE_TRACE_DIR','RW_PHASE_COMMIT_TRACE_DIR'):
            with patch.dict(os.environ,{name:'x'}):
                with self.assertRaises(RuntimeError):trace.install(self.path)
        profiler=cProfile.Profile();profiler.enable()
        try:
            with self.assertRaises(RuntimeError):trace.install(self.path)
        finally:profiler.disable()
        sys.settrace(lambda *args:None)
        try:
            with self.assertRaises(RuntimeError):trace.install(self.path)
        finally:sys.settrace(None)

    def test_exception_unwind_cannot_be_valid(self):
        def selected():raise ValueError('intentional toy error')
        rec=trace.install(self.path,selector=lambda code:'leader_proxy' if code is selected.__code__ else None)
        with self.assertRaises(ValueError):selected()
        doc=rec.finish();self.assertFalse(doc['valid']);self.assertTrue(doc['errors'])

    def test_order_and_worker_assignment_normalization(self):
        rows=[{'kind':'price_task','call':7,'parent_call':None,'context':'c','event':'enter','input':{'task':'x'},'ordinal':7},
              {'kind':'price_leaf','call':9,'parent_call':7,'context':'c','event':'enter','input':{},'ordinal':9},
              {'kind':'price_leaf','call':9,'parent_call':7,'context':'c','event':'return','result':trace.canonical(2.),'ordinal':10}]
        shifted=[{**r,'call':r['call']+100,'parent_call':r['parent_call']+100 if r['parent_call'] is not None else None} for r in rows]
        self.assertEqual(trace.normalized_process(rows),trace.normalized_process(shifted))
        self.assertNotEqual(trace.normalized_process(rows),trace.normalized_process(rows[::-1]))

    def test_streaming_comparison_keeps_first_difference_and_task_multiplicity(self):
        def document(parent,tasks=(),valid=True):
            return {'valid':valid,'comparison':{'parent':parent,'worker_tasks':list(tasks)}}
        left=document([{'score':1},{'score':2}])
        right=document([{'score':1},{'score':3}])
        report=trace.compare_collections(left,right)
        self.assertFalse(report['equal'])
        self.assertEqual(report['first_parent_difference'],{'index':1,'left':{'score':2},'right':{'score':3}})
        report=trace.compare_collections(left,document([{'score':1}]))
        self.assertEqual(report['first_parent_difference'],{'index':1,'left':{'score':2},'right':None})
        # An absent record is distinct even from an explicit None record.
        self.assertFalse(trace.compare_collections(document([]),document([None]))['equal'])
        task={'task_key':'same','trace':[{'score':trace.canonical(-0.)}]}
        self.assertFalse(trace.compare_collections(document([], [task]),document([], [task,task]))['equal'])
        self.assertFalse(trace.compare_collections(left,document(left['comparison']['parent'],valid=False))['equal'])

    def test_spawn_bootstrap_stdout_and_repeat_comparison(self):
        env=dict(os.environ)
        env['PYTHONPATH']=os.pathsep.join([str(ROOT/'diagnostics/evaluation_trace_bootstrap'),str(ROOT)])
        cmd=[sys.executable,'-X','utf8','-m','diagnostics.evaluation_trace_synthetic']
        baseline=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,text=True,timeout=40)
        self.assertEqual(baseline.returncode,0,baseline.stderr)
        results=[]
        for label in ('a','b'):
            dest=self.path/label
            env['RW_EVALUATION_TRACE_DIR']=str(dest)
            proc=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,text=True,timeout=40)
            self.assertEqual(proc.returncode,0,proc.stderr)
            self.assertEqual(proc.stdout,baseline.stdout)
            merged=trace.collection(dest)
            self.assertTrue(merged['valid'],merged['errors'])
            self.assertEqual(merged['worker_task_count'],4)
            self.assertEqual(merged['process_count'],3)
            results.append(merged)
        self.assertEqual(results[0]['comparison'],results[1]['comparison'])
        self.assertTrue(trace.compare_collections(results[0],results[1])['equal'])
        self.assertFalse(trace.collection(self.path/'a',root_pid=-1)['valid'])
        self.assertFalse(trace.collection(self.path/'a',expected_child_pids=[-1])['valid'])
        # Missing child finish is an incomplete trace, not zero work.
        child=next(p for p in (self.path/'b').glob('evaluation_*.json') if not p.name.endswith('.started.json'))
        child.rename(child.with_suffix('.hidden'))
        self.assertFalse(trace.collection(self.path/'b')['valid'])

    def test_bootstrap_conflict_fails_before_user_program(self):
        env=dict(os.environ,RW_DECISION_PROFILE_DIR='conflict',RW_EVALUATION_TRACE_DIR=str(self.path))
        env['PYTHONPATH']=os.pathsep.join([str(ROOT/'diagnostics/evaluation_trace_bootstrap'),str(ROOT)])
        proc=subprocess.run([sys.executable,'-X','utf8','-c','print("SHOULD_NOT_RUN")'],cwd=ROOT,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=10)
        self.assertNotEqual(proc.returncode,0)
        self.assertNotIn('SHOULD_NOT_RUN',proc.stdout)
        self.assertIn('EVALUATION_TRACE_INIT_FAILED',proc.stderr)

    def test_launcher_environment_modes_and_leaks(self):
        from diagnostics.run_area_production_preflight import diagnostic_environment
        env={'RW_DECISION_PROFILE_DIR':'old','RW_PHASE_COMMIT_TRACE_DIR':'old',
             'RW_EVALUATION_TRACE_DIR':'old','RW_EVALUATION_TRACE_MANIFEST':'old',
             'RW_EVALUATION_TRACE_BACKEND':'profile','RW_EVALUATION_TRACE_LOCALS':'0',
             'PYTHONPATH':os.pathsep.join([str(ROOT/'diagnostics/phase_trace_bootstrap'),str(ROOT/'diagnostics/decision_profile_bootstrap'),'kept'])}
        baseline=dict(env)
        plain=diagnostic_environment(env,self.path)
        self.assertEqual(env,baseline)
        self.assertEqual(plain['PYTHONPATH'],'kept')
        self.assertFalse(any(k.startswith('RW_') for k in plain))
        for selected,variable in [('phase_trace','RW_PHASE_COMMIT_TRACE_DIR'),('process_profile','RW_DECISION_PROFILE_DIR'),('evaluation_trace','RW_EVALUATION_TRACE_DIR')]:
            chosen=diagnostic_environment(env,self.path,**{selected:True})
            self.assertIn(variable,chosen)
            other={'RW_PHASE_COMMIT_TRACE_DIR','RW_DECISION_PROFILE_DIR','RW_EVALUATION_TRACE_DIR'}-{variable}
            self.assertFalse(other & chosen.keys())
            if selected == 'evaluation_trace':
                self.assertEqual(chosen['RW_EVALUATION_TRACE_BACKEND'], 'monitor')
                self.assertEqual(chosen['RW_EVALUATION_TRACE_LOCALS'], '1')
            else:
                self.assertNotIn('RW_EVALUATION_TRACE_BACKEND', chosen)
                self.assertNotIn('RW_EVALUATION_TRACE_LOCALS', chosen)
        with self.assertRaises(ValueError):diagnostic_environment(env,self.path,phase_trace=True,evaluation_trace=True)

    def test_cli_modes_mutually_exclusive_before_any_run(self):
        script=ROOT/'diagnostics/run_area_production_preflight.py'
        for other in ('--phase-trace','--profile-all-processes'):
            proc=subprocess.run([sys.executable,'-X','utf8',str(script),'--time','900','--beta','300',
                                 '--evaluation-trace',other],cwd=ROOT,capture_output=True,text=True,timeout=10)
            self.assertEqual(proc.returncode,2)
            self.assertIn('not allowed with argument',proc.stderr)


if __name__=='__main__':unittest.main()
