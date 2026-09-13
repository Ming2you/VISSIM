"""Native clock model/window contract, source-only; no rollout or COM."""
from copy import deepcopy
import json
from pathlib import Path
import random
import struct
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'vendor/NumSim-mine'), str(ROOT/'plant/src')]
from evaluation.controllers import signal_actuation_contract as contract, signal_group_plan as plans
from diagnostics.fixtures import signal_clock_dd13e08 as legacy
from vissim_strict.signal_program import parse_sig


class Net:
    def __init__(self, raw):
        self.signals = ['SC'+s for s in raw['controllers']]
        self.green_min = 20.
        self.cycle_length_by_signal = {'SC'+s: row['native_cycle_sec'] for s,row in raw['controllers'].items()}
        self.effective_green_total_by_signal = {'SC'+s: (114. if s=='7' else sum(row['axis_green_sec'].values())) for s,row in raw['controllers'].items()}
        self.live = {'SC'+s: tuple(p for p in plans.MODEL_PHASES if row['axis_green_sec'][p]>0) for s,row in raw['controllers'].items()}
        self.signal_actuation_contract = None
        self.native_signal_minimum_policy = 'include_source_reference'
    def signal_live_phases(self, signal): return self.live[signal]
    def signal_cycle_length(self, signal): return self.cycle_length_by_signal[signal]
    def signal_effective_green_total(self, signal): return self.effective_green_total_by_signal[signal]
    def signal_primary_phase(self, signal): return self.live[signal][0]


def fixture(native=True):
    raw=json.loads((ROOT/'outputs/signal_group_actuation_plan_mainline_20260825.json').read_text(encoding='utf-8'))
    source=json.loads((ROOT/'reports/20260911_decision_runtime/native_clock_basis_source_v1.json').read_text(encoding='utf-8'))
    if native:
        for sc,row in raw['controllers'].items(): row['native_clock_basis']=source['controllers'][sc]['native_clock_basis']
    cfg=SimpleNamespace(network=Net(raw),simulation=SimpleNamespace(T_u_sec=5.))
    if not native:
        for signal in cfg.network.signals:
            cfg.network.cycle_length_by_signal[signal]=150.
            cfg.network.effective_green_total_by_signal[signal]=150.-3*len(cfg.network.signal_live_phases(signal))
    tuning={'urban':{'physical_signal_contract':True},'actuation':{'real_world_signal_control':{'offset_writer':'experiment'}}}
    with patch.dict('os.environ',{'RW_OFFSET_WRITER':'experiment'}), patch.object(contract,'install_candidates'):
        contract.configure(cfg,tuning,raw)
    greens={};offsets={}
    for sc,row in raw['controllers'].items():
        signal='SC'+sc
        vals=row['axis_green_sec'] if native else contract.project_vector(cfg.network,signal,row['axis_green_sec'])
        greens.update({signal+'_'+p: v for p,v in vals.items()})
        offsets[signal]=row.get('native_clock_basis',{}).get('reference_offset_sec',0.)
    action=SimpleNamespace(green_times=greens,offsets=offsets,diagnostics={})
    return cfg,raw,source,action,tuning


class NativeSignalContractTests(unittest.TestCase):
    def setUp(self):
        contract.clear_clock_cache()
        self.cfg,self.raw,self.source,self.action,self.tuning=fixture()

    def test_all_native_source_phase_fractions_initial_and_full_cycle(self):
        checks=0
        for sc,row in self.raw['controllers'].items():
            signal='SC'+sc
            program=parse_sig(ROOT/self.source['controllers'][sc]['program'],1)
            vals=row['axis_green_sec']
            self.assertEqual(contract.project_vector(self.cfg.network,signal,vals),vals)
            contract.validate_vector(self.cfg.network,signal,vals)
            for phase in plans.MODEL_PHASES:
                sg=next((s['sg_no'] for s in row['phase_segments'][phase]),None)
                for step in range(int(program.cycle_length_sec/5)):
                    expected=0. if sg is None else sum(program.state_at(t,sg)=='GREEN' for t in range(step*5,step*5+5))/5
                    self.assertEqual(contract.phase_fraction(self.action,self.cfg,{'phase':signal+'_'+phase},step),expected,(signal,phase,step))
                    checks+=1
        self.assertEqual(checks,2016)

    def test_sc7_projection_preserves_independent_axis_and_pair_budget(self):
        net=self.cfg.network
        base=self.raw['controllers']['7']['axis_green_sec']
        self.assertEqual(contract.phase_bounds(net,'SC7'),{'p1':(20.,87.),'p2':(24.,90.),'p4':(24.,90.)})
        candidate=contract.project_vector(net,'SC7',dict(base,p1=73.))
        self.assertEqual(candidate,dict(base,p1=73.))
        rng=random.Random(13)
        for _ in range(100):
            vals=contract.project_vector(net,'SC7',{p:rng.uniform(-50,150) for p in plans.MODEL_PHASES})
            contract.validate_vector(net,'SC7',vals)
            self.assertEqual(vals['p2']+vals['p4'],114.)
            self.assertLessEqual(vals['p1']+3.,vals['p2']+1e-9)
        for bad in [dict(base,p1=88.),dict(base,p2=89.),dict(base,p3=.001),dict(base,p1=67.0001)]:
            with self.assertRaises(ValueError): contract.validate_vector(net,'SC7',bad)

    def test_explicit_source_minimum_only_lowers_sc16_p2(self):
        box=contract.phase_bounds(self.cfg.network,'SC16')
        self.assertEqual({p:v[0] for p,v in box.items()},{'p1':20.,'p2':17.,'p3':20.})
        base=self.raw['controllers']['16']['axis_green_sec']
        self.assertEqual(contract.project_vector(self.cfg.network,'SC16',base),base)
        for values in [dict(base,p2=16.,p1=64.),dict(base,p3=19.,p1=71.)]:
            with self.assertRaises(ValueError): contract.validate_vector(self.cfg.network,'SC16',values)
        self.cfg.network.native_signal_minimum_policy='strict'
        with self.assertRaises(ValueError): contract.validate_vector(self.cfg.network,'SC16',base)

    def test_configure_rejects_native_cycle_budget_or_strict_source_reference(self):
        for mutation in ('cycle','budget','minimum','source','order'):
            cfg=deepcopy(self.cfg);raw=deepcopy(self.raw);cfg.network.signal_actuation_contract=None
            if mutation=='cycle':cfg.network.cycle_length_by_signal['SC7']=150.
            if mutation=='budget':cfg.network.effective_green_total_by_signal['SC7']=181.
            if mutation=='minimum':cfg.network.native_signal_minimum_policy=None
            if mutation=='source':raw['controllers']['7']['axis_green_sec']['p1']=66.
            if mutation=='order':raw['controllers']['1']['native_clock_basis']['phase_order']=['p1','p2','p3','p4']
            with patch.dict('os.environ',{'RW_OFFSET_WRITER':'experiment'}),patch.object(contract,'install_candidates'):
                with self.assertRaises((ValueError,plans.SignalGroupPlanError)):
                    contract.configure(cfg,self.tuning,raw)

    def test_cache_keys_include_basis_cycle_and_minimum_policy(self):
        spec={'phase':'SC16_p2'}
        first=contract.phase_fraction(self.action,self.cfg,spec,13)
        self.assertEqual(contract.phase_fraction(self.action,self.cfg,spec,13),first)
        self.assertGreater(contract.clock_cache_info()['clock_hits'],0)
        for mutation in ('cycle','minimum','basis'):
            cfg=deepcopy(self.cfg)
            if mutation=='cycle':cfg.network.cycle_length_by_signal['SC16']=149.
            if mutation=='minimum':cfg.network.native_signal_minimum_policy=None
            if mutation=='basis':cfg.network.signal_actuation_contract['nodes']['SC16']['native_clock_basis']['idle_after_phase_sec']['p3']=33.
            with self.assertRaises((ValueError,plans.SignalGroupPlanError)):
                contract.phase_fraction(self.action,cfg,spec,13)
        changed=deepcopy(self.raw);changed['controllers']['16']['native_clock_basis']['program_offset_sec']+=1
        with self.assertRaisesRegex(ValueError,'bases differ'):
            contract.validate_writer(self.action,self.cfg,changed,'experiment')

    def test_installed_exchange_and_price_direction_use_sc7_coordinates(self):
        class Follower:
            def __init__(self,cfg):self.cfg=cfg
            def _urban_green_candidates(self,*args):return [20.,90.]
            def _phase_exchange_candidates(self,*args):raise AssertionError('legacy exchange must not run for nativeSC7')
        class Controller:
            def __init__(self,cfg):self.cfg=cfg;self.nash_solver=Follower(cfg)
            def _phase_direction(self,*args):raise AssertionError('legacy direction must not run for nativeSC7')
        owner=Controller(self.cfg);contract.install_controller(owner)
        base=self.raw['controllers']['7']['axis_green_sec']
        candidates=owner.nash_solver._phase_exchange_candidates('SC7',base,6.)
        self.assertEqual(len(candidates),3)
        self.assertIn(dict(base,p1=73.),candidates)
        self.assertIn(dict(base,p1=61.),candidates)
        self.assertIn(dict(base,p2=84.,p4=30.),candidates)
        self.assertEqual(owner._phase_direction('SC7',base,'p1',6.),dict(base,p1=73.))
        self.assertIsNone(owner._phase_direction('SC7',base,'p2',6.))
        # Source-compatible p2 floor17 remains reachable after a real step to19.
        serial=dict(self.raw['controllers']['16']['axis_green_sec'],p1=61.,p2=19.)
        serial_candidates=owner.nash_solver._phase_exchange_candidates('SC16',serial,2.)
        self.assertIn(dict(serial,p1=63.,p2=17.),serial_candidates)

    def test_absent_native_basis_matches_frozen_legacy_float_bits(self):
        cfg,raw,_,action,_=fixture(False)
        for signal in cfg.network.signals:
            self.assertEqual(contract.bounds(cfg.network,signal),legacy.bounds(cfg.network,signal))
            for phase in plans.MODEL_PHASES:
                for step in (None,0,1,29,30,31,179,180):
                    spec={'phase':signal+'_'+phase}
                    old=legacy.phase_fraction(action,cfg,spec,step)
                    new=contract.phase_fraction(action,cfg,spec,step)
                    self.assertEqual(struct.pack('!d',old),struct.pack('!d',new),(signal,phase,step))


if __name__=='__main__':unittest.main()
