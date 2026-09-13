"""Explicit candidate mass, branch storage, and actual n7 replay regressions."""
from pathlib import Path
import copy
import json
import math
import sys
from types import SimpleNamespace as NS
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'vendor/NumSim-mine')]
from evaluation.controllers import link_predictor as fix
from src.models.state import TrafficState


def tiny(shares=None, stock=None):
    shares = shares or {'a': .5, 'b': .5}
    caps = {'sig_a': 10.0, 'sig_b': 10.0, 'tail': 10.0, 'recv': 20.0}
    net = NS(off_ramp_storage_link={'a': 'sig_a', 'b': 'sig_b'},
             offramp_direct_share_by_offramp=shares, offramp_direct_tail_by_offramp={'a':'tail','b':'tail'},
             urban_link_storage_veh=caps, urban_movements={}, boundary_out_ramp_split={},
             boundary_out_capacity_veh_h=3600.0, urban_boundary_link_length_m=50,
             urban_avg_speed_km_h=36, urban_avg_vehicle_length_m=6, boundary_queue_max_veh=100)
    cfg = NS(network=net, simulation=NS(T_f_h=10/3600,T_c_h=10/3600,T_u_h=5/3600,T_u_sec=5))
    state = NS(time_sec=0, urban_link_storage={k:v-(stock or {}).get(k,0) for k,v in caps.items()},
               urban_movement_queue={}, urban_link_speed_kph={}, ramp_queue={},
               urban_storage_release_buffer={}, offramp_transit_buffer={})
    follower = NS(cfg=cfg,_wu=NS(_offramp_drain_flow={},_specs={}),_local_offramp_drain=lambda *args:(0,{}))
    model = NS(owned_offramps=['a','b'],owned_ramps=[],link='FW')
    return fix.LocalLandingState(follower, model, state), follower, model, state


class BranchTests(unittest.TestCase):
    def test_zero_and_unit_share_only_constrain_used_branch(self):
        self.assertEqual(fix.branch_capacity(10,0,0,1),10)
        self.assertEqual(fix.branch_capacity(0,10,1,1),10)
        self.assertEqual(fix.branch_capacity(10,0,.5,1),0)
        for values in [(1,1,1.1,1),(1,1,.5,0),(-1,1,.5,1),(1,1,math.nan,1)]:
            with self.assertRaises(ValueError):fix.branch_capacity(*values)

    def test_shared_direct_space_is_reserved_once(self):
        landing,_,_,_=tiny()
        caps=landing.capacities(1)
        self.assertEqual(caps,{'a':10,'b':10,'FW':20})
        landing.land(caps,1)
        self.assertEqual(landing.stock,{'sig_a':5,'sig_b':5,'tail':10})
        self.assertEqual(landing.ledger['max_abs_residual_veh'],0)
        self.assertEqual(landing.capacities(1)['FW'],0)

    def test_candidate_state_is_private_and_repeatable(self):
        first,follower,model,state=tiny()
        baseline=copy.deepcopy(state)
        first.land({'a':10},1)
        second=fix.LocalLandingState(follower,model,state)
        self.assertEqual(second.stock,{'sig_a':0,'sig_b':0,'tail':0})
        self.assertEqual(state.__dict__,baseline.__dict__)
        second.land({'a':10},1)
        self.assertEqual(first.stock,second.stock)

    def test_full_tail_prevents_withdrawal_without_rejection(self):
        landing,_,_,_=tiny(stock={'tail':10})
        self.assertEqual(landing.capacities(1)['FW'],0)
        with self.assertRaises(RuntimeError):landing.land({'a':1},1)

    def test_direct_sink_and_signal_transit_keep_mass(self):
        landing,_,_,_=tiny()
        landing.land({'a':10},1)
        self.assertEqual(landing.arrived('sig_a'),0)
        landing.advance(NS(),{},10/3600)
        self.assertEqual(landing.stock['tail'],0)
        self.assertEqual(landing.stock['sig_a'],5)
        self.assertEqual(landing.ledger['departures_veh'],5)
        self.assertEqual(landing.ledger['max_abs_residual_veh'],0)

    def test_stopline_space_and_point_queue_reservations(self):
        landing,_,_,_=tiny()
        landing.net.urban_stopline_storage_veh={'tail':4}
        landing.point_queue['tail']=1
        self.assertEqual(landing.available('tail'),3)
        self.assertEqual(landing.capacities(1)['FW'],6)

    def test_shared_signal_receiver_is_filled_once(self):
        _,follower,model,state=tiny(stock={'sig_a':10,'sig_b':10,'recv':19})
        follower._wu._offramp_drain_flow={'a':[('s','ma')],'b':[('s','mb')]}
        follower._wu._specs={'ma':{'receiving_link':'recv'},'mb':{'receiving_link':'recv'}}
        follower.cfg.network.boundary_out_capacity_veh_h=1e-9
        def drain(off,occupied,receivers,control,dt):
            actual=min(occupied,max(0,20-receivers['recv']))/dt
            return actual,{'recv':actual}
        follower._local_offramp_drain=drain
        landing=fix.LocalLandingState(follower,model,state)
        landing.advance(NS(),{},10/3600)
        self.assertLessEqual(landing.stock['recv'],20)
        self.assertAlmostEqual(landing.stock['sig_a']+landing.stock['sig_b'],19,places=8)
        self.assertLess(landing.ledger['max_abs_residual_veh'],1e-8)

    def test_wout_owned_ramp_transfer_is_internal_and_replaces_coupling(self):
        _,follower,model,state=tiny(stock={'tail':10})
        model.owned_ramps=['r']
        net=follower.cfg.network
        net.boundary_out_ramp_split={'tail':{'free':.5,'ramps':{'r':.5}}}
        net.leg_ramp_split_enabled=True
        net.boundary_out_link_length_km={'tail':1}
        net.leg_ramp_split_wout_speed_kmh=36
        net.ramp_queue_cap=lambda ramp:100
        net.ramp_capacity_veh_h={'r':3600}
        landing=fix.LocalLandingState(follower,model,state)
        self.assertEqual(landing.replaced_coupling['r'],180)
        ramp_q={'r':0}
        landing.advance(NS(),ramp_q,10/3600)
        self.assertGreater(ramp_q['r'],0)
        external_exit=landing.ledger['departures_veh']-landing.ledger['own_ramp_transfers_veh']
        self.assertAlmostEqual(sum(landing.stock.values())+ramp_q['r']+external_exit,10)


class N7ReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from diagnostics.test_freeway_local_state import LocalStateRegression
        LocalStateRegression.setUpClass()
        cls.cfg=LocalStateRegression.cfg
        cls.follower=LocalStateRegression.follower
        cls.control=LocalStateRegression.control
        cls.demand=LocalStateRegression.demand
        from evaluation.controllers import vissim_stackelberg_adapter as adapter
        cls.adapter=adapter
        cls.tuning=adapter.load_optional_json(str(ROOT/'evaluation/configs/n21_n7_20260908.json'))
        cls.det=adapter.load_optional_json(str(ROOT/cls.tuning['detector_mapping_json']))
        cls.cal=adapter.deep_update(adapter.load_optional_json(str(ROOT/'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json')),cls.tuning.get('calibration_override',{}))
        adapter.install_offramp_direct_landing(cls.cfg,cls.tuning)
        from src.controllers.wu_faithful_follower import WuFaithfulFollower
        cls.original=WuFaithfulFollower._solve_freeway_agent_local
        fix.configure(cls.cfg,{'freeway':{'local_landing_state':True}})
        fix.install(cls.cfg)

    def real_runtime(self, raw, previous_path):
        from evaluation.controllers.runtime_setup import configure_runtime
        from src.models.state import ControlAction
        tuning=copy.deepcopy(self.tuning)
        tuning['freeway'].update(local_landing_state=True,local_lane_context=True,conservative_offramp_drain=True)
        self.adapter.install_config_switches(tuning)
        cfg=self.adapter.build_config(ROOT/'vendor/NumSim-mine',raw['control_interval_sec'],raw['sim_period_sec'],
              'fast-smoke',self.cal,tuning,local_observation=True,flagship=True)
        mapping=json.loads((ROOT/tuning['mapping_json']).read_text(encoding='utf-8'))
        detectors,_=self.adapter.filter_midblock_links_from_detector_mapping(copy.deepcopy(self.det),tuning)
        state,_,_=configure_runtime(self.adapter,cfg,tuning,mapping,raw,str(previous_path),detectors,self.cal,TrafficState)
        follower=self.adapter.build_priced_wu_link_controller(cfg,tuning).nash_solver
        control=self.adapter.control_from_json(previous_path,cfg,ControlAction)
        return cfg,follower,state,control

    def setUp(self):
        self.cfg.network.local_landing_state=True
        self.cfg.network.conservative_offramp_drain=True
        self.cfg.network.local_lane_context=True

    def test_disabled_flag_delegates_exactly(self):
        state=TrafficState.initial(self.cfg)
        self.cfg.network.local_landing_state=False
        n=self.cfg.network.freeway_segments_per_link
        args=('FW_E',state,{},self.demand,self.control)
        expected=type(self).original(self.follower,*args,vsl_override=[100.0]*n)
        actual=self.follower._solve_freeway_agent_local(*args,vsl_override=[100.0]*n)
        self.assertEqual(actual,expected)

    def test_actual_snapshots_candidates_are_bounded_and_reset(self):
        artifacts=[]
        for run, sec in [('codex_nc_s13_6056c94_20260909_retry',900),('codex_n7_s13_6056c94_20260909',3300)]:
            path=ROOT/'evaluation/runs'/run/('decisions_'+run)/f'state_{sec:06d}.json'
            if not path.exists():self.fail(f'Required real replay snapshot missing: {path}')
            raw=json.loads(path.read_text(encoding='utf-8-sig'))
            previous=path.parent/('action_000001.json' if sec==900 else 'action_003150.json')
            cfg,follower,state,control=self.real_runtime(raw,previous)
            demand=self.adapter.demand_from_state(raw,cfg,type(self.demand),1)[0]
            before=copy.deepcopy(state)
            coupling=follower._wu._coupling(state,control,demand)
            for link in cfg.network.freeway_links:
                n=follower._local_freeway_models[link].n_seg
                args=(link,state,coupling,demand,control)
                cfg.network.local_landing_state=False
                old=follower._solve_freeway_agent_local(*args,vsl_override=[80.0]*n)
                self.assertEqual(old,type(self).original(follower,*args,vsl_override=[80.0]*n))
                cfg.network.local_landing_state=True
                first=follower._solve_freeway_agent_local(*args,vsl_override=[80.0]*n)
                follower._solve_freeway_agent_local(*args,vsl_override=[100.0]*n)
                again=follower._solve_freeway_agent_local(*args,vsl_override=[80.0]*n)
                self.assertEqual(first,again)
                self.assertTrue(math.isfinite(first[1]))
                diagnostics=follower._last_local_landing_diagnostics[link]
                self.assertLess(diagnostics['maximum_candidate_mass_residual_veh'],1e-7)
                artifacts.append({'run':run,'sim_sec':sec,'link':link,'landing_flag_disabled_result':old,
                    'result':first,'diagnostics':copy.deepcopy(diagnostics)})
            self.assertEqual(state,before)
        (ROOT/'diagnostics/local_landing_replay.json').write_text(json.dumps(artifacts,indent=2,ensure_ascii=False),encoding='utf-8')


if __name__=='__main__':unittest.main()
