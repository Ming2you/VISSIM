"""A recorded calculation hold must not waive any native signal or command check."""
import copy
import csv
import json
from pathlib import Path
import tempfile
import unittest

from diagnostics.com_execution_equivalence import verify_pair as v
from diagnostics.com_execution_equivalence import test_verify_native_execution as fixtures
from diagnostics.com_execution_equivalence.test_verify_pair import save, table, ACTION_FIELDS


class RecoveredDecisionTests(unittest.TestCase):
    actual=staticmethod(fixtures.SingleRunTests.actual)
    verify=fixtures.SingleRunTests.verify

    def setUp(self):
        fixtures.SingleRunTests.setUp(self)
        assert self.root.resolve().parent==Path(tempfile.gettempdir()).resolve()
        for sec in (1,6,12):
            p=self.folder/f'action_{sec:06d}.csv'
            with p.open(newline='',encoding='utf-8-sig') as f:rows=list(csv.DictReader(f))
            rows[0]['id']='RW_FW_E_S13';table(p,ACTION_FIELDS,rows)
        self.prov.update(controller='wu-link')
        self.prov['env']['RW_DECISION_HOLD_PREVIOUS']='1'
        self.tuning=self.root/'tuning.json';save(self.tuning,{'runtime':{'decision_error_policy':'hold_previous'}})
        self.prov['files']['tuning']={'path':str(self.tuning),'sha256':v.sha(self.tuning)}
        save(self.pp,self.prov)
        old={'metadata':{'sim_sec':6,'run_provenance':{'run_id':'run-id'}},
             'run_provenance':{'run_id':'run-id'},'diagnostics':{},'vsl':{'FW_E':80},
             'ramp_metering':{'M':450},'green_times':{'S':[3,0,0,0]},'offsets':{'S':0}}
        self.previous=self.folder/'action_000006.json';save(self.previous,old)
        current=copy.deepcopy(old)
        current['metadata'].update(sim_sec=12,controller_status='hold_previous_error',prediction_status='not_computed',
            hold_previous={'source':str(self.previous),'source_sim_sec':6,'json_sha256':v.sha(self.previous),
                           'csv_sha256':v.sha(self.previous.with_suffix('.csv')),'native_application_pending':True})
        self.action=self.folder/'action_000012.json';save(self.action,current)
        with self.previous.with_suffix('.csv').open(newline='',encoding='utf-8-sig') as f:rows=list(csv.DictReader(f))
        for row in rows:row['metadata']+=';hold_previous_error=1'
        table(self.action.with_suffix('.csv'),ACTION_FIELDS,rows)
        self.log=self.run/'runlog_run.txt'
        self.log.write_text('STAGE=SIM_DONE\nSIM_SEC=12\n'+
            '\n'.join(k+'='+('1' if k=='DECISIONS_FAILED' else '0') for k in v.FAILURE_COUNTERS)+
            '\nDECISIONS_HELD_PREVIOUS=1\nDECISIONS_OK=2\nDECISION_HOLD_ATTEMPT sim_sec=12 cause=exit=1\n'+
            'DECISION_HELD_PREVIOUS sim_sec=12 source='+str(self.previous)+'\n',encoding='utf-8')

    def test_held_calculation_is_separate_from_native_success(self):
        result=self.verify();self.assertTrue(result['native_execution_passed'],result)
        self.assertFalse(result['passed']);self.assertFalse(result['native_lsa_com_coverage_passed'])
        self.assertFalse(result['decision_recovery']['no_calculation_failures'])
        self.assertEqual(result['decision_recovery']['calculation_failures'],1)
        self.assertEqual(result['decision_recovery']['held_decisions'],1)
        self.assertFalse(result['process_exit_verified'])

    def test_hold_cannot_hide_missing_native_ldp(self):
        (self.native/'actual_loaded_9101_001.ldp').unlink()
        self.assertFalse(self.verify()['native_execution_passed'])

    def test_hold_cannot_hide_com_failure(self):
        self.log.write_text(self.log.read_text().replace('COM_FAILURES=0','COM_FAILURES=1'))
        self.assertFalse(self.verify()['native_execution_passed'])

    def test_cp949_controller_stderr_does_not_change_execution_evidence(self):
        before=self.verify()
        warning=b'CONTROLLER_DECISION sim_sec=12 stderr='+('기하 경고'.encode('cp949'))+b' DECISIONS_FAILED=999\n'
        self.log.write_bytes(warning+self.log.read_bytes())
        after=self.verify()
        self.assertTrue(after['native_execution_passed'],after)
        self.assertEqual(after['decision_recovery'],before['decision_recovery'])

    def test_malformed_counter_still_rejected_in_mixed_encoding_log(self):
        blob=self.log.read_bytes().replace(b'COM_FAILURES=0',b'COM_FAILURES=\xff')
        self.log.write_bytes(blob)
        self.assertFalse(self.verify()['native_execution_passed'])

    def test_malformed_hold_path_still_rejected(self):
        blob=self.log.read_bytes().replace(str(self.previous).encode('utf-8'),b'\xff')
        self.log.write_bytes(blob)
        self.assertFalse(self.verify()['native_execution_passed'])

    def test_extra_calculation_failure_rejected(self):
        self.log.write_text(self.log.read_text().replace('DECISIONS_FAILED=1','DECISIONS_FAILED=2'))
        self.assertFalse(self.verify()['native_execution_passed'])

    def test_unlogged_hold_rejected(self):
        self.log.write_text(self.log.read_text().replace('DECISIONS_FAILED=1','DECISIONS_FAILED=0').replace('DECISIONS_HELD_PREVIOUS=1','DECISIONS_HELD_PREVIOUS=0').replace('DECISION_HELD_PREVIOUS sim_sec=12 source='+str(self.previous)+'\n',''))
        self.assertFalse(self.verify()['native_execution_passed'])

    def test_stale_source_hash_rejected(self):
        z=v.read(self.previous);z['offsets']['S']=1;save(self.previous,z)
        self.assertFalse(self.verify()['native_execution_passed'])

    def test_changed_physical_csv_rejected(self):
        p=self.action.with_suffix('.csv')
        with p.open(newline='',encoding='utf-8-sig') as f:rows=list(csv.DictReader(f))
        rows[1]['green_sec']='6';table(p,ACTION_FIELDS,rows)
        self.assertFalse(self.verify()['native_execution_passed'])

    def test_cross_run_or_stale_prediction_rejected(self):
        z=v.read(self.action);z['run_provenance']['run_id']='other';save(self.action,z)
        self.assertFalse(self.verify()['native_execution_passed'])
        z['run_provenance']['run_id']='run-id';z['prediction']={'old':'stale'};save(self.action,z)
        self.assertFalse(self.verify()['native_execution_passed'])

    def test_disabled_policy_rejected(self):
        self.prov['env'].pop('RW_DECISION_HOLD_PREVIOUS');save(self.pp,self.prov)
        self.assertFalse(self.verify()['native_execution_passed'])

    def test_scheduled_vsl_change_needs_actual_readback(self):
        cfg={'runtime':{'decision_error_policy':'hold_previous'},
             'adapter':{'sdmpc_fixed_vsl':{'start_sec':12,'base_kmh':80,'zone_kmh':{'FW_E__seg13':90}}},
             'freeway':{'vsl_zone_heads':{'FW_E':[0,13,30]}}}
        save(self.tuning,cfg);self.prov['files']['tuning']['sha256']=v.sha(self.tuning);save(self.pp,self.prov)
        for sec in (1,6,12):
            p=self.folder/f'action_{sec:06d}.csv'
            with p.open(newline='',encoding='utf-8-sig') as f:rows=list(csv.DictReader(f))
            rows[0]['id']='RW_FW_E_S13'
            if sec==12:rows[0]['speed_kph']='90'
            table(p,ACTION_FIELDS,rows)
        z=v.read(self.action);z['metadata']['hold_previous']['csv_sha256']=v.sha(self.previous.with_suffix('.csv'))
        z['vsl']['FW_E']=90;save(self.action,z)
        self.assertFalse(self.verify()['native_execution_passed'])
        for row in self.vslrows:
            if row[0]==12:row[3]=row[4]=90
        table(self.folder/'vsl_readback.csv',v.VSL_FIELDS,self.vslrows)
        self.assertTrue(self.verify()['native_execution_passed'])


if __name__=='__main__':unittest.main()
