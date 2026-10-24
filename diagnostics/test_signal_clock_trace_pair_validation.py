"""Small stdlib certificate guards. No trace DB, model, subprocess or simulator."""
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from diagnostics import signal_clock_trace_pair_validation as check


def sha(value): return hashlib.sha256(value).hexdigest()


class TracePairTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix='clock_pair_guards_')
        self.addCleanup(temp.cleanup);self.root=Path(temp.name).resolve()
        self.before,self.after=sha(b'before'),sha(b'cached')
        self.enterContext(patch.object(check,'ROOT',self.root))
        self.enterContext(patch.object(check,'CLOCK_SHA',(self.before,self.after)))
        self.folders=[self.root/'diagnostics/area_production_preflight'/side for side in ('before','clock')]
        for folder in self.folders:(folder/'evaluation_trace').mkdir(parents=True)
        def write(name,data):
            p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
            return sha(data)
        write(check.CLOCK,b'cached')
        runtime=write('evaluation/controllers/other.py',b'same runtime')
        common={name:write(name,name.encode()) for name in ('state.json','previous.json','mapping.json','detectors.json','calibration.json')}
        tracer={name:write(name,name.encode()) for name in check.REQUIRED_TRACERS}
        self.docs=[]
        for side,folder in enumerate(self.folders):
            tuning=f'diagnostics/family{side}/n7_area_beta300.json'
            config=write(tuning,b'{"same":"config"}')
            source={check.CLOCK:(self.before,self.after)[side],'evaluation/controllers/other.py':runtime}
            inputs={**source,**common,tuning:config}
            command=[sys.executable,'-X','utf8','adapter.py']
            for flag,path in (('--state-json','state.json'),('--previous-action-json','previous.json'),
                              ('--mapping-json','mapping.json'),('--detector-mapping-json','detectors.json'),
                              ('--calibration-json','calibration.json'),('--tuning-json',tuning)):
                command.extend((flag,str(self.root/path)))
            command.extend(('--out-action-json',str(folder/'action.json'),'--out-action-csv',str(folder/'action.csv')))
            pid=100+side*10
            env={'RW_OFFSET_WRITER':'experiment','NUMSIM_REPO_ROOT':str(self.root/'vendor'),
                 'RW_MAINLINE_SG_ONLY':'1','PYTHONPATH':os.pathsep.join((str(self.root),str(self.root/'diagnostics/evaluation_trace_bootstrap'))),
                 'RW_EVALUATION_TRACE_BACKEND':'monitor','RW_EVALUATION_TRACE_LOCALS':'1',
                 'RW_EVALUATION_TRACE_DIR':str(folder/'evaluation_trace'),
                 'RW_EVALUATION_TRACE_MANIFEST':str(folder/'manifest.json')}
            self.docs.append({'valid':True,'source_unchanged':True,'inputs_unchanged':True,'exit_code':0,
                'surviving_worker_pids':[],'adapter_pid':pid,'observed_worker_processes':[{'pid':pid+1}],
                'evaluation_trace_validation':{'valid':True,'errors':[],'trace_sources_unchanged':True,
                    'missing_observed_child_pids':[],'root_pid':pid,'process_pids':[pid,pid+1],
                    'process_count':2,'worker_task_count':4,'comparison_sha256':sha(b'normalized local'),
                    'v1_comparison_sha256':sha(b'parent and prices'),'identity_contracts':['fixture exact identity relation']},
                'environment':env,'python_hash_seed':{'explicit_cli':True,'adapter_and_workers':'20260910'},
                'command':command,'source_sha256':source,'input_sha256':inputs,'config_sha256':config,
                'read_only_evaluation_trace':tracer.copy(),'recorded_run':'fixture','recorded_sim_sec':900,
                'recorded_snapshot':'state.json'})
        self.save()

    def save(self):
        for folder,doc in zip(self.folders,self.docs):
            (folder/'manifest.json').write_text(json.dumps(doc),encoding='utf-8')

    def validate(self): return check.validate_trace_pair(*self.folders)

    def test_valid_pair_normalizes_only_scoped_execution_paths_and_clock(self):
        report=self.validate()
        self.assertTrue(report['passed']);self.assertEqual(report['process_count'],2)
        self.assertEqual(report['worker_task_count'],4)
        self.assertEqual(report['source_delta']['before'],self.before)
        self.assertNotIn('RW_EVALUATION_TRACE_DIR',report['environment'])
        self.assertEqual(report['comparison_sha256'],self.docs[0]['evaluation_trace_validation']['comparison_sha256'])

    def test_invalid_completion_and_trace_guards(self):
        original=copy.deepcopy(self.docs)
        mutations=[('valid',False),('source_unchanged',False),('inputs_unchanged',False),('exit_code',1),
                   ('surviving_worker_pids',[111]),('timed_out',True),('normal_process_counters',{})]
        for key,value in mutations:
            with self.subTest(key=key):
                self.docs=copy.deepcopy(original);self.docs[1][key]=value;self.save()
                with self.assertRaises(ValueError):self.validate()
        for key,value in [('valid',False),('errors',['unwind']),('trace_sources_unchanged',False),
                          ('comparison_sha256',sha(b'different')),('v1_comparison_sha256',sha(b'different')),
                          ('identity_contracts',['different']),('process_count',3),('worker_task_count',5),
                          ('missing_observed_child_pids',[111]),('root_pid',999),('process_pids',[110])]:
            with self.subTest(trace=key):
                self.docs=copy.deepcopy(original);self.docs[1]['evaluation_trace_validation'][key]=value;self.save()
                with self.assertRaises(ValueError):self.validate()

    def test_environment_and_cross_execution_paths_fail(self):
        original=copy.deepcopy(self.docs)
        changes=[('RW_EVALUATION_TRACE_DIR',self.docs[0]['environment']['RW_EVALUATION_TRACE_DIR']),
                 ('RW_EVALUATION_TRACE_MANIFEST',self.docs[0]['environment']['RW_EVALUATION_TRACE_MANIFEST']),
                 ('RW_EVALUATION_TRACE_BACKEND','profile'),('RW_EVALUATION_TRACE_LOCALS','0'),
                 ('RW_DECISION_PROFILE_DIR','leak'),('PYTHONPATH','wrong')]
        for key,value in changes:
            with self.subTest(key=key):
                self.docs=copy.deepcopy(original);self.docs[1]['environment'][key]=value;self.save()
                with self.assertRaises(ValueError):self.validate()
        self.docs=copy.deepcopy(original);self.docs[1]['python_hash_seed']['adapter_and_workers']='1';self.save()
        with self.assertRaises(ValueError):self.validate()

    def test_source_tracer_and_input_bytes_are_rechecked(self):
        for relative in ('state.json','evaluation/controllers/other.py','diagnostics/evaluation_trace_storage.py'):
            with self.subTest(path=relative):
                path=self.root/relative;before=path.read_bytes();path.write_bytes(before+b'changed')
                try:
                    with self.assertRaisesRegex(ValueError,'Evidence changed'):self.validate()
                finally:path.write_bytes(before)
        self.docs[1]['read_only_evaluation_trace'].pop('diagnostics/evaluation_trace_storage.py');self.save()
        with self.assertRaisesRegex(ValueError,'Missing required tracer'):self.validate()

    def test_clock_direction_config_and_command_state_are_not_generic_exclusions(self):
        original=copy.deepcopy(self.docs)
        self.docs[0]['source_sha256'][check.CLOCK]=self.after;self.save()
        with self.assertRaisesRegex(ValueError,'Clock source direction'):self.validate()
        self.docs=copy.deepcopy(original);self.docs[1]['config_sha256']=sha(b'wrong');self.save()
        with self.assertRaisesRegex(ValueError,'Config input pin'):self.validate()
        self.docs=copy.deepcopy(original);cmd=self.docs[1]['command'];cmd[cmd.index('--state-json')+1]=str(self.root/'previous.json');self.save()
        with self.assertRaisesRegex(ValueError,'Command state differs'):self.validate()


if __name__=='__main__':unittest.main()
