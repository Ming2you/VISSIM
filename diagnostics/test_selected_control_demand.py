import csv
import io
import json
from pathlib import Path
import tempfile
import unittest
from diagnostics.prepare_selected_control_demand import convert,package,sha
from diagnostics.selected_control_completion import audit

ROOT=Path(__file__).resolve().parents[1]

class SelectedDemand(unittest.TestCase):
    def test_repackage_prepared_8050_preserves_every_physical_field(self):
        tuning=ROOT/'diagnostics/control_improvement/decision_common_anchor_20260911/ramp8_physical_v1/joint_config_v2.json'
        original=json.loads(tuning.read_text(encoding='utf-8-sig'))
        _,_,report,native,_,shared=package(ROOT/'diagnostics/demand_sweep/fw080_urban050/prepared',tuning,ROOT/'diagnostics/selected_control_demand/repackage_test_only')
        for key,new in (('native_internal_inputs',native),('shared_approach',shared)):
            source=ROOT/original['urban'][key]; before=source.read_bytes();old=json.loads(before)
            self.assertIn('selected_demand_derivation',old)
            self.assertEqual(new['selected_demand_derivation']['source_declaration']['sha256'],sha(source))
            restored=dict(new)
            for field in ('demand_profile','selected_demand_derivation'):restored[field]=old[field]
            self.assertEqual(restored,old)
            self.assertEqual(source.read_bytes(),before)
        self.assertLessEqual(report['max_abs_error_vph'],1e-10)

    def test_selected_7030_complete(self):
        profile,rows,report=convert(ROOT/'diagnostics/demand_sweep/fw070_urban030/prepared')
        self.assertEqual(len(rows),204)
        self.assertEqual(report['inputs'],34)
        self.assertLessEqual(report['max_abs_error_vph'],1e-10)
        factors={r['role']:float(r['multiplier']) for r in csv.DictReader(io.StringIO(profile))}
        for row in rows:
            self.assertEqual(row['profile_vph'],row['before_vph']*factors['no:'+row['input_no']])

    def test_nonexact_float_rows_are_reported(self):
        _,rows,report=convert(ROOT/'diagnostics/demand_sweep/fw070_urban030/prepared')
        self.assertEqual(report['float_exact_rows'],sum(r['abs_error_vph']==0 for r in rows))
        self.assertGreater(report['max_abs_error_vph'],0)

    def test_declaration_and_config_only_schedules_change(self):
        tuning=ROOT/'diagnostics/contract_candidate_configs_v4/n7_area_beta0.json'
        original=json.loads(tuning.read_text(encoding='utf-8-sig'))
        source=ROOT/original['urban']['native_internal_inputs']
        source_sha=sha(source)
        old=json.loads(source.read_text(encoding='utf-8-sig'))
        _,_,report,declaration,config,_=package(ROOT/'diagnostics/demand_sweep/fw070_urban030/prepared',tuning,ROOT/'diagnostics/selected_control_demand/synthetic_only')
        declaration.pop('selected_demand_derivation'); declaration['demand_profile']=old['demand_profile']
        config['urban']['native_internal_inputs']=original['urban']['native_internal_inputs']
        config['urban']['shared_approach']=original['urban']['shared_approach']
        self.assertEqual(declaration,old); self.assertEqual(config,original)
        self.assertEqual(sha(source),source_sha)
        self.assertEqual(report['config_changed_paths'],['urban.native_internal_inputs','urban.shared_approach'])

    def test_other_selected_case_7040(self):
        _,rows,report=convert(ROOT/'diagnostics/demand_sweep/fw070_urban040/prepared')
        self.assertEqual(len(rows),204)
        self.assertLessEqual(report['max_abs_error_vph'],1e-10)


class Completion(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.run=Path(self.temp.name)/'synthetic'; self.run.mkdir()
        self.asset=self.run/'input'; self.asset.write_bytes(b'unchanged')
        self.checks=self.run/'checks.json'
        self.checks.write_text(json.dumps({'source_sha256':{str(self.asset):sha(self.asset)},'generated_sha256':{str(self.asset):sha(self.asset)},'controller_tuning':str(self.asset),'network_sha256':sha(self.asset),'profile_sha256':sha(self.asset)}))
        self.launch=self.checks.with_name('launch.json')
        self.launch_arguments={'Name':'synthetic','OutDir':str(self.run),'SimPeriod':5400,'Seed':13}
        self.launch.write_text(json.dumps({'execute':True,'arguments':self.launch_arguments}),encoding='utf-8')
        self.obs=self.run/'observation.json'
        self.obs.write_text(json.dumps({'watchdog_exit_code':0,'owned_native':{'pid':123,'started':'fixed'},'owned_native_alive':False,'ownership_ambiguous':False}))
        item={'path':str(self.asset),'sha256':sha(self.asset)}
        (self.run/'run_provenance_synthetic.json').write_text(json.dumps({'run_id':'synthetic-id','name':'synthetic','sim_period_sec':5400,'seed':13,'files':dict.fromkeys(('network','tuning','demand_profile'),item)}))
        self.log=self.run/'runlog_synthetic.txt'
        self.log.write_bytes(b'native CP949 path: \xb0\xa1\nSTAGE=SIM_DONE\nSIM_SEC=5400\n'+b''.join((k+'=0\n').encode() for k in ('DECISIONS_FAILED','OBSERVATION_FAILURES','SIGNAL_FAILURES','ACTION_FORMAT_FAILURES','COM_FAILURES')))
        (self.run/'state_synthetic.csv').write_text('sim_sec,total_vehicles\n5400,12\n')
        (self.run/'vissim_simulation_001.err').write_bytes(b'')
        (self.run/'vissim_eval').mkdir()
        for suffix in ('fzp','lsa'): (self.run/'vissim_eval'/('synthetic.'+suffix)).write_bytes(b'not read as payload')

    def result(self): return audit(self.run,'synthetic',5400,self.obs,self.checks)

    def test_external_status_scope_and_native_exit(self):
        result=self.result(); self.assertTrue(result['completed'],result['errors'])
        self.assertIsNone(result['cscript_exit_code'])
        obs=json.loads(self.obs.read_text()); obs['owned_native_alive']=None; self.obs.write_text(json.dumps(obs))
        self.assertFalse(self.result()['completed'])

    def test_seed13_and_seed17_match_independent_launch_and_leave_sources_unchanged(self):
        provenance_path=self.run/'run_provenance_synthetic.json'
        for seed in (13,17):
            with self.subTest(seed=seed):
                self.launch.write_text(json.dumps({'execute':True,'arguments':dict(self.launch_arguments,Seed=seed)}),encoding='utf-8')
                provenance=json.loads(provenance_path.read_text()); provenance['seed']=seed
                provenance_path.write_text(json.dumps(provenance),encoding='utf-8')
                before={p:p.read_bytes() for p in self.run.rglob('*') if p.is_file()}
                result=self.result()
                self.assertTrue(result['completed'],result['errors'])
                self.assertEqual(result['launch_request'],{'path':str(self.launch),'sha256':sha(self.launch),'expected_seed':seed})
                self.assertEqual(before,{p:p.read_bytes() for p in self.run.rglob('*') if p.is_file()})

    def test_seed_mismatch_is_rejected_in_both_directions(self):
        provenance_path=self.run/'run_provenance_synthetic.json'
        for expected,actual in ((13,17),(17,13)):
            with self.subTest(expected=expected,actual=actual):
                self.launch.write_text(json.dumps({'execute':True,'arguments':dict(self.launch_arguments,Seed=expected)}),encoding='utf-8')
                provenance=json.loads(provenance_path.read_text()); provenance['seed']=actual
                provenance_path.write_text(json.dumps(provenance),encoding='utf-8')
                result=self.result()
                self.assertFalse(result['completed'])
                self.assertTrue(any('seed differs' in message for message in result['errors']),result['errors'])

    def test_seed_values_require_exact_integer_types(self):
        provenance_path=self.run/'run_provenance_synthetic.json'
        for invalid in (None,True,13.0,'13',0,-1):
            with self.subTest(launch_seed=invalid):
                self.launch.write_text(json.dumps({'execute':True,'arguments':dict(self.launch_arguments,Seed=invalid)}),encoding='utf-8')
                self.assertFalse(self.result()['completed'])
        self.launch.write_text(json.dumps({'execute':True,'arguments':self.launch_arguments}),encoding='utf-8')
        for invalid in (True,13.0,'13'):
            with self.subTest(provenance_seed=invalid):
                provenance=json.loads(provenance_path.read_text()); provenance['seed']=invalid
                provenance_path.write_text(json.dumps(provenance),encoding='utf-8')
                self.assertFalse(self.result()['completed'])

    def test_missing_launch_or_other_run_launch_cannot_authorize_seed(self):
        for field,value in (('Name','another'),('OutDir',str(self.run.parent/'another')),('SimPeriod',1050)):
            with self.subTest(field=field):
                self.launch.write_text(json.dumps({'execute':True,'arguments':dict(self.launch_arguments,**{field:value})}),encoding='utf-8')
                self.assertFalse(self.result()['completed'])
        for invalid in ({'execute':False,'arguments':self.launch_arguments},
                        {'arguments':self.launch_arguments}, [], {'execute':True,'arguments':[]}):
            with self.subTest(launch=invalid):
                self.launch.write_text(json.dumps(invalid),encoding='utf-8')
                self.assertFalse(self.result()['completed'])
        self.launch.unlink()
        self.assertFalse(self.result()['completed'])

    def test_failed_counter_and_changed_input_reject(self):
        self.log.write_bytes(self.log.read_bytes().replace(b'DECISIONS_FAILED=0',b'DECISIONS_FAILED=1'))
        self.assertFalse(self.result()['completed'])
        self.asset.write_bytes(b'changed')
        self.assertTrue(any('changed' in message for message in self.result()['errors']))

if __name__=='__main__': unittest.main()
