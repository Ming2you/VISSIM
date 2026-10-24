"""Small byte/receipt fixtures only; no simulation or recorded native files."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from decimal import Decimal

from diagnostics.com_execution_equivalence import compare_timing as m


def log():
    timers = {'startup.load_net': (8,1), 'startup.demand': (105,1),
              'startup.demand.volume_before_read': (.5,2), 'startup.demand.volume_set': (1.5,2),
              'startup.demand.volume_after_read': (101,2), 'sim.first_step': (1,1),
              'sim.step': (20,1199), 'decision.total': (18,9),
              'com.input_volume.setter': (0,2), 'com.input_volume.read': (0,4)}
    lines = [b'Korean path: \xc7\xd1\xb1\xdb', b'RUN_MODE=STEPWISE_PHYSICAL_HEAD_OBSERVATION']
    lines += [b'DEMAND_WRITE_BEGIN no=1082 time_int=1-4 before=10 target=4 timer_sec=10.00',
              b'DEMAND_WRITE_DONE no=1082 time_int=1-4 timer_sec=10.50',
              b'DEMAND_WRITE_BEGIN no=1082 time_int=1-5 before=10 target=4 timer_sec=111.50',
              b'DEMAND_WRITE_DONE no=1082 time_int=1-5 timer_sec=112.50']
    lines += [f'PERF name={k} sec={sec} n={n}'.encode() for k,(sec,n) in timers.items()]
    lines += [(k+'=0').encode() for k in m.FAILURES]+[b'STAGE=SIM_DONE',b'SIM_SEC=1200']
    return b'\r\n'.join(lines)+b'\r\n'


def provenance(name='case', fast=False):
    return {'name':name, 'run_id':'run1', 'sim_period_sec':1200, 'seed':13,
            'control_interval_sec':150, 'state_log_interval_sec':30, 'demand_scale':1,
            'controller':'diagnostic-signal-profile', 'audit_anchors_sec':[], 'signal_observation':{'enabled':True},
            'files':{k:{'path':k, 'exists':True, 'sha256':'a'*64}
                     for k in ['network','tuning','demand_profile','main_vbs_runner']},
            'controller_sources':[{'path':'controller.py','exists':True,'sha256':'b'*64}],
            'signal_programs':[{'path':'native.sig','exists':True,'sha256':'c'*64}],
            'env':{'RW_PERF':'1','RW_SIGNAL_WRITE_ON_CHANGE':'1' if fast else '0',
                   'RW_SIGNAL_READBACK_SEC':'0' if fast else '1'}}


class TimingTests(unittest.TestCase):
    def test_ascii_markers_in_cp949_log_and_count_scope(self):
        d=m.parse_log(log(),1200)
        self.assertEqual(d['completed_interval_setters'],2)
        self.assertEqual(d['largest_between_setter_gaps'][0]['gap_sec'],101)
        self.assertEqual(d['simulation_call_total_sec'],21)
        self.assertEqual(d['perf']['com.input_volume.setter']['kind'],'count_only')

    def test_bad_or_duplicate_perf_never_silent_zero(self):
        for bad in (log()+b'PERF name=sim.step sec=20 n=1199\n',
                    log().replace(b'name=sim.step sec=20',b'name=sim.step sec=NaN'),
                    log().replace(b'name=sim.step sec=20',b'name=sim.step sec=-1'),
                    log().replace(b'name=com.input_volume.read sec=0',b'name=com.input_volume.read sec=2')):
            with self.subTest(bad=bad[-100:]), self.assertRaises(ValueError):m.parse_log(bad,1200)

    def test_missing_failure_or_terminal_rejected(self):
        for old,new in [(b'COM_FAILURES=0',b'COM_FAILURES=1'),(b'STAGE=SIM_DONE',b''),
                        (b'SIM_SEC=1200',b'SIM_SEC=1199')]:
            with self.assertRaises(ValueError):m.parse_log(log().replace(old,new),1200)

    def test_demand_order_counts_and_midnight(self):
        self.assertEqual(m.timer_gap(Decimal('86399.75'),Decimal('.25')),Decimal('.5'))
        with self.assertRaises(ValueError):m.timer_gap(Decimal('86400'),Decimal('1'))
        for old,new in [(b'DONE no=1082 time_int=1-4',b'DONE no=1082 time_int=1-3'),
                        (b'name=com.input_volume.read sec=0 n=4',b'name=com.input_volume.read sec=0 n=3')]:
            with self.assertRaises(ValueError):m.parse_log(log().replace(old,new),1200)

    def fixture(self, p):
        p.mkdir(); (p/'runlog.txt').write_bytes(log())
        owned={'pid':12,'started':'2026-09-10T13:00:01Z'}
        wrapper={'watchdog_exit_code':0,'owned_native_alive':False,'ownership_ambiguous':False,
                 'owned_native':owned,'started':'2026-09-10T13:00:00Z','finished':'2026-09-10T13:08:00Z'}
        def write(name,d):
            f=p/name;f.write_text(json.dumps(d),encoding='utf-8');return str(f),hashlib.sha256(f.read_bytes()).hexdigest()
        wp,ws=write('wrapper.json',wrapper);pp,ps=write('provenance.json',provenance(p.name))
        receipt={'schema':'selected-control-completion/v1','completed':True,'exit_code':0,
                 'errors':[],'owned_native_alive':False,'owned_native':owned,'run_directory':str(p),
                 'name':p.name,'run_id':'run1','terminal_sec':1200,'runlog_path':str(p/'runlog.txt'),
                 'wrapper_observation':{'path':wp,'sha256':ws},'provenance_path':pp,'provenance_sha256':ps,
                 'native_files':[{'path':'DO_NOT_READ.fzp'}]}
        rp,_=write('completion.json',receipt)
        return Path(rp),receipt

    def test_completed_reads_only_four_small_evidence_files(self):
        with tempfile.TemporaryDirectory() as t:
            p,r=self.fixture(Path(t)/'case');d=m.read_completed(p)
            self.assertEqual(d['wrapper_wall_sec'],480)
            self.assertEqual(len(d['source_sha256']),4)
            self.assertFalse(any(k.endswith('.fzp') for k in d['source_sha256']))

    def test_incomplete_rejected_before_missing_run_outputs(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'incomplete.json';p.write_text(json.dumps({'completed':False}))
            with self.assertRaisesRegex(ValueError,'not completed'):m.read_completed(p)

    def test_wrapper_digest_or_live_owner_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p,r=self.fixture(Path(t)/'case')
            wp=Path(r['wrapper_observation']['path']);w=json.loads(wp.read_text());w['owned_native_alive']=True
            wp.write_text(json.dumps(w))
            with self.assertRaisesRegex(ValueError,'SHA mismatch'):m.read_completed(p)
            r['wrapper_observation']['sha256']=hashlib.sha256(wp.read_bytes()).hexdigest();p.write_text(json.dumps(r))
            with self.assertRaisesRegex(ValueError,'ownership'):m.read_completed(p)

    def test_pair_scopes_startup_confound_and_foreign_input_change(self):
        old=m.parse_log(log(),1200)
        old.update(terminal_sec=1200,wrapper_wall_sec=480,provenance=provenance())
        new=deepcopy(old);new['provenance']=provenance(fast=True);new['wrapper_wall_sec']=380
        new['perf']['startup.demand.volume_after_read']['sec']=1
        pair=m.compare(old,new)
        self.assertEqual(pair['wall_delta_sec'],-100)
        self.assertEqual(pair['startup_confound_sensitivity']['excluding_demand_after_read']['delta_sec'],0)
        self.assertEqual(pair['physical_equivalence_verdict'],'not_evaluated_by_timing_helper')
        del new['perf']['sim.step']
        self.assertIsNone(m.compare(old,new)['buckets']['sim.step']['delta_sec'])
        new['provenance']['files']['network']['sha256']='d'*64
        with self.assertRaises(ValueError):m.compare(old,new)


if __name__=='__main__':unittest.main()
