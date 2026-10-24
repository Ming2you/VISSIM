"""Small offline conservation/geometry/regression checks; no VISSIM or COM."""
from __future__ import annotations

import copy
import json
import math
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OLD = HERE.parent/'metanet_calibration_v1'
sys.path[:0] = [str(ROOT),str(OLD)]
from canonical_harness import load_base_model
from boundary_factory import ObservationData,build_window
from evaluation.controllers import area_freeway_accounting as accounting
from evaluation.controllers import freeway_geometry as geometry
from evaluation.controllers import vissim_stackelberg_adapter as adapter
from evaluation.controllers import link_predictor
from evaluation.controllers.control_area_objective import ModelAreaLedger
from src.models.state import TrafficState,ControlAction
from src.models.demand import DemandStep


PROFILE = json.loads((HERE/'physical_geometry21_v1.json').read_text(encoding='utf-8'))
SOURCE = json.loads((OLD/'seed13_observations/geometry.json').read_text(encoding='utf-8'))
MAPPING = json.loads(Path(SOURCE['mapping']['path']).read_text(encoding='utf-8-sig'))


class PhysicalGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model=load_base_model(SOURCE)
        cls.tuning={'freeway':{'geometry_profile':str(HERE/'physical_geometry21_v1.json')}}

    def config(self,road='FW_E'):
        cfg=self.model._config(road,{})
        adapter.install_freeway_geometry_profile(cfg,self.tuning,MAPPING)
        for port in PROFILE['ports']:
            if port['road']!=road: continue
            if port['kind']=='ramp':cfg.network.ramp_merge_segment_index[port['id']]=port['to_cell']
            if port['kind']=='offramp':cfg.network.off_ramp_segment_index[str(port['connector'])]=port['from_cell']
        return cfg

    def state(self,cfg,road='FW_E',speed=60.):
        net=cfg.network;s=TrafficState.initial(cfg)
        s.freeway_density[road]=[15.+i for i in range(21)]
        s.freeway_speed[road]=[speed]*21
        s.freeway_effective_lanes[road]=list(net.freeway_segment_lanes[road])
        s.urban_link_storage=dict(net.urban_link_storage_veh)
        s.mainline_origin_queue[road]=0.
        return s

    def step(self,state,cfg,source=0.,releases=None,caps=None):
        net=cfg.network;road=net.freeway_links[0];dt=cfg.simulation.T_f_h
        releases={r:0. for r in net.ramps} if releases is None else releases
        caps={o:0. for o in net.off_ramps} if caps is None else caps
        before=accounting.continuity_vehicle_counts(state,cfg)[road]
        stocks={'freeway:'+road:{'inside':sum(before)},'origin:'+road:{'outside':state.mainline_origin_queue[road]},
                **{'merge_pending:'+r:{'outside':q*dt} for r,q in releases.items()}}
        ledger=ModelAreaLedger(stocks,capture_response=True)
        ledger.begin_response_step('freeway',0.,cfg.simulation.T_f_sec)
        ledger.expect_constraint_coverage('freeway_allocator');state._control_area_ledger=ledger
        ttt,diag=accounting._freeway_substep_events(state,ControlAction.uncontrolled(cfg),DemandStep({road:source},{},{}),cfg,
            offramp_capacity_veh_h=caps,ramp_release_veh_h=releases,
            ramp_release_diagnostics={'total_no_meter_flow':sum(releases.values()),'mean_ramp_receiving_factor':1.},
            update_ramp_queues=False,include_ramp_queue_ttt=False)
        return before,accounting.continuity_vehicle_counts(state,cfg)[road],ledger,ttt,diag

    def test_01_legacy_exact_two_complete_windows(self):
        # Includes every cell, accepted physical boundary flow and diagnostic.
        data=ObservationData(OLD/'seed13_observations')
        before=json.loads((HERE/'legacy_before.json').read_text(encoding='utf-8'))
        model=load_base_model(SOURCE)
        for t in (1350,3600):
            inputs=build_window(data,t,'history_forecast')
            actual=model.rollout(inputs['initial_cells'],inputs['boundary_steps'],initial_origin_queue=inputs['initial_origin_queue'])
            # Concurrent harness work added this explicit OFF flag only. Verify
            # it before comparing all previously recorded values exactly.
            if 'dynamic_off_storage' in actual['diagnostics']:
                self.assertIs(actual['diagnostics'].pop('dynamic_off_storage'),False)
            self.assertEqual(before[str(t)],actual)

    def test_02_all_cells_are_physically_single_lane_count(self):
        for road,row in PROFILE['roads'].items():
            self.assertEqual(len(row['segment_lanes']),21)
            for a,b,lane in zip(row['segment_bounds_m'],row['segment_bounds_m'][1:],row['segment_lanes']):
                for i,part in enumerate(SOURCE['chains'][road]):
                    end=SOURCE['chains'][road][i+1]['offset_m'] if i+1<len(SOURCE['chains'][road]) else row['segment_bounds_m'][-1]
                    if min(end,b)-max(part['offset_m'],a)>1e-7:self.assertEqual(lane,part['lanes'])
            self.assertGreaterEqual(min(row['segment_lengths_km']),.4)
            self.assertLess((155/3600*10)/min(row['segment_lengths_km']),1.)
        self.assertIn(6841.743,PROFILE['roads']['FW_E']['segment_bounds_m'])
        self.assertIn(3822.359,PROFILE['roads']['FW_W']['segment_bounds_m'])

    def test_03_ports_follow_physical_position_and_fingerprint(self):
        expected={'OR_D_E_signal':12,'OR_D_E_direct':13,'OR_D_W_signal':6,'OR_F_W_signal':11,'RM_C10644':12}
        for port in PROFILE['ports']:
            idx=port['from_cell'] if port['kind']=='offramp' else port['to_cell']
            edges=PROFILE['roads'][port['road']]['segment_bounds_m']
            self.assertLessEqual(edges[idx],port['chain_pos_m']);self.assertLess(port['chain_pos_m'],edges[idx+1])
            if port['id'] in expected:self.assertEqual(idx,expected[port['id']])
        altered=copy.deepcopy(SOURCE);altered['network']={'sha256':'different seed/control settings'};altered['bounds']={}
        self.assertEqual(geometry.geometry_fingerprint(SOURCE),geometry.geometry_fingerprint(altered))
        altered['boundaries'][0]['to_pos_m']+=1
        self.assertNotEqual(geometry.geometry_fingerprint(SOURCE),geometry.geometry_fingerprint(altered))

    def test_04_all_stock_getters_use_one_area(self):
        for road in ('FW_E','FW_W'):
            cfg=self.config(road);s=self.state(cfg,road)
            expected=[rho*length*lane for rho,length,lane in zip(s.freeway_density[road],PROFILE['roads'][road]['segment_lengths_km'],PROFILE['roads'][road]['segment_lanes'])]
            self.assertEqual(accounting.continuity_vehicle_counts(s,cfg)[road],expected)
            self.assertEqual(adapter._freeway_vehicle_count_by_link(s,cfg)[road],expected)
            self.assertEqual(s.freeway_vehicle_count_by_link(cfg.network)[road],expected)
            self.assertEqual(s.total_freeway_vehicles(cfg.network),sum(expected))

    def test_05_dynamic_lane_loss_does_not_create_or_delete_stock(self):
        cfg=self.config();s=self.state(cfg,speed=0.)
        for off in cfg.network.off_ramps:
            store=cfg.network.off_ramp_storage_link[off]
            s.urban_link_storage[store]=.3*cfg.network.urban_link_storage_veh[store]
        before,after,ledger,ttt,diag=self.step(s,cfg)
        for a,b in zip(before,after):self.assertAlmostEqual(a,b,places=11)
        self.assertAlmostEqual(ttt,sum(after)*cfg.simulation.T_f_h,places=12)
        self.assertEqual(diag['density_projection_count'],0)

    def test_06_every_cell_conserves_with_sources_merges_and_exits(self):
        for road in ('FW_E','FW_W'):
            cfg=self.config(road);s=self.state(cfg,road)
            cfg.network.off_ramp_split_ratio={o:.06 for o in cfg.network.off_ramps}
            releases={r:90.+30*i for i,r in enumerate(cfg.network.ramps)}
            caps={o:200. for o in cfg.network.off_ramps}
            for step in range(5):
                before,after,ledger,ttt,diag=self.step(s,cfg,source=7200.,releases=releases,caps=caps)
                main=[0.]*21;off=[0.]*21;merge=[0.]*21;entry=0.
                for row in ledger._response['resource_allocations']:
                    k,v=row['kind'],row['accepted_total_veh']
                    if k=='freeway_mainline_sending':main[int(row['resource'].rsplit(':',1)[1])]=v
                    elif k=='freeway_terminal_sending':main[-1]=v
                    elif k=='freeway_entry_request':entry=v
                    elif k=='freeway_offramp_sending':off[cfg.network.off_ramp_segment_index[row['resource']]]+=v
                for ramp,q in releases.items():merge[cfg.network.ramp_merge_segment_index[ramp]]+=q*cfg.simulation.T_f_h
                for i in range(21):
                    expected=before[i]+(entry if i==0 else main[i-1])+merge[i]-off[i]-main[i]
                    self.assertAlmostEqual(after[i],expected,places=10)
                self.assertAlmostEqual(ttt,sum(after)*cfg.simulation.T_f_h,places=12)
                self.assertEqual(diag['density_projection_count'],0)

    def test_07_merge_speed_term_uses_cell_length(self):
        cfg=self.config();s=self.state(cfg);cfg.network.metanet_delta_merge=.3
        releases={r:0. for r in cfg.network.ramps};ramp=next(iter(releases));releases[ramp]=120.
        i=cfg.network.ramp_merge_segment_index[ramp];n=cfg.network
        expected=50.-n.metanet_delta_merge*cfg.simulation.T_f_h*120*60/(geometry.cell_lengths_km(n,'FW_E',21)[i]*n.freeway_segment_lanes['FW_E'][i]*(s.freeway_density['FW_E'][i]+n.metanet_kappa_veh_km_lane))
        with patch.object(accounting._mn,'metanet_speed_update_kmh',return_value=50.):
            self.step(s,cfg,releases=releases)
        self.assertAlmostEqual(s.freeway_speed['FW_E'][i],expected,places=12)

    def test_08_bad_lengths_and_mapping_rejected(self):
        cfg=self.config();cfg.network.freeway_segment_length_profile_km['FW_E'].pop()
        with self.assertRaises(ValueError):accounting.continuity_vehicle_counts(self.state(cfg),cfg)
        cfg=self.config();cfg.network.freeway_segment_length_profile_km['FW_E'][0]=float('nan')
        with self.assertRaises(ValueError):accounting.cell_lengths_km(cfg,'FW_E',21)
        with self.assertRaises(ValueError):adapter.install_freeway_geometry_profile(self.model._config('FW_E',{}),self.tuning,{})

    def test_09_same_profile_load_is_idempotent(self):
        cfg=self.config();before=copy.deepcopy(cfg.network.freeway_segment_params)
        adapter.install_freeway_geometry_profile(cfg,self.tuning,MAPPING)
        self.assertEqual(before,cfg.network.freeway_segment_params)

    def test_10_unported_local_and_joint_solvers_rejected(self):
        cfg=self.config()
        with self.assertRaises(NotImplementedError):link_predictor._freeway_query_setup(SimpleNamespace(cfg=cfg),'FW_E',None)
        with self.assertRaises(NotImplementedError):adapter.run_joint_owner_decision(None,None,None,None,cfg,None,None,None,None,None,None,segment_vsl_func=None)

    def test_11_observation_projection_preserves_exact_vehicle_counts(self):
        cfg=self.config();rows=[]
        for i,(length,lane) in enumerate(zip(PROFILE['roads']['FW_E']['segment_lengths_km'],PROFILE['roads']['FW_E']['segment_lanes'])):
            rows.append({'count':17+i,'speed_sum':(17+i)*70.,'length_km':length,'lanes':lane})
        state=adapter.traffic_state_from_vissim({'sim_sec':900.,'freeway_segments':{'FW_E':rows}},cfg,TrafficState)
        actual=accounting.continuity_vehicle_counts(state,cfg)['FW_E']
        for i,n in enumerate(actual):self.assertAlmostEqual(n,17+i,places=12)
        bad=copy.deepcopy(rows);bad[13]['length_km']=.513441
        with self.assertRaises(ValueError):adapter.traffic_state_from_vissim({'freeway_segments':{'FW_E':bad}},cfg,TrafficState)

    def test_12_receiving_limit_uses_destination_cell_volume(self):
        cfg=self.config();s=self.state(cfg,speed=0.);net=cfg.network
        i=6;s.freeway_density['FW_E'][i]=net.rho_max-.1
        s.freeway_speed['FW_E'][i-1]=100.
        before,after,ledger,ttt,diag=self.step(s,cfg)
        row=next(r for r in ledger._response['resource_allocations'] if r['kind']=='freeway_mainline_sending' and r['resource']==f'FW_E:cell:{i-1}')
        available=.1*PROFILE['roads']['FW_E']['segment_lengths_km'][i]*net.freeway_segment_lanes['FW_E'][i]
        self.assertAlmostEqual(row['accepted_total_veh'],available,places=11)
        self.assertAlmostEqual(after[i]-before[i],available,places=11)

    def test_13_installed_default_local_branch_rejects_variable_geometry(self):
        from src.controllers.wu_faithful_follower import WuFaithfulFollower
        cfg=self.config();cfg.network.local_landing_state=False
        calls=[]
        def original(self,*args,**kwargs):
            calls.append(True)
            return 'legacy-result'
        with patch.object(WuFaithfulFollower,'_solve_freeway_agent_local',original):
            link_predictor.install(cfg)
            selected=WuFaithfulFollower._solve_freeway_agent_local
            with self.assertRaises(NotImplementedError):selected(SimpleNamespace(cfg=cfg))
            self.assertEqual(calls,[])
            cfg.network.freeway_variable_cell_lengths=False
            self.assertEqual(selected(SimpleNamespace(cfg=cfg)),'legacy-result')
            self.assertEqual(calls,[True])


if __name__=='__main__':
    unittest.main(verbosity=2)
