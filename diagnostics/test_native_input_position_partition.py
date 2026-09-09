"""Actual source21 records, exact projection and first selected service."""
from copy import deepcopy
import json
from pathlib import Path
import pickle
import tempfile
import unittest

from diagnostics.probe_model_area_integration import ROOT, adapter, build_projected
from diagnostics.route_input_fixtures import fixture_path
from evaluation.controllers import native_internal_input as native, projection_support, area_runtime
from src.models.demand import DemandStep
from src.models.state import ControlAction


class NativePositionPartitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tuning=json.loads((ROOT/'diagnostics/area_candidate_configs/n7_area_beta0.json').read_text())
        tuning['urban']['route_choice_corridor']['evidence_paths'] = [
            'diagnostics/route_choice_corridor_ver2.json',
            'diagnostics/route_choice_corridor_1128_ver2.json']
        cls.directory=tempfile.TemporaryDirectory(dir=ROOT/'diagnostics')
        folder_path=Path(cls.directory.name)
        data=json.loads((ROOT/'diagnostics/native_internal_inputs_extended_ver2.json').read_text())
        data['inputs']={key:row for key,row in data['inputs'].items() if key in {'1091','1085','1095','1097','1083'}}
        source_path=folder_path/'inputs.json';source_path.write_text(json.dumps(data))
        tuning['urban']['native_internal_inputs']=str(source_path)
        tuning['urban']['movements']['native_input_signal_authority']='diagnostics/native_input_1083_signal_authority_ver2.json'
        folder=ROOT/'evaluation/runs/codex_area_observed_nc_s13_20260910/decisions_codex_area_observed_nc_s13_20260910'
        cls.source=fixture_path(folder/'state_000900.json');cls.source_bytes=cls.source.read_bytes()
        path=folder_path/'config.json';path.write_text(json.dumps(tuning))
        cls.built=build_projected(path,cls.source,fixture_path(folder/'action_000001.json'),fixture_inputs=False)
        cls.action=adapter.control_from_json(fixture_path(folder/'action_000001.json'),cls.built[0],ControlAction)

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def test_actual_pre_and_post_records_count_once_with_zero_initial_events(self):
        cfg,state,detectors,tuning,raw,_,metadata=self.built
        rows=detectors['physical_record_storage_projection']['21']
        self.assertEqual({k:v['count'] for k,v in rows.items()},{'in_SC108_W':1.,'SC108_to_SC109':1.})
        assigned=state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']
        self.assertEqual(assigned['21'],{'storage:in_SC108_W':1.,'storage:SC108_to_SC109':1.})
        self.assertEqual(assigned['10112'],{'storage:SC108_to_SC109':1.})
        self.assertEqual((state._control_area_ledger.entered_veh,state._control_area_ledger.ttd_veh,state._control_area_ledger.event_count),(0,0,0))
        self.assertEqual(state.urban_arrival_buffer['in_SC108_W'],{182:1.})
        self.assertEqual(state.urban_storage_release_buffer['in_SC108_W'],{182:1.})
        self.assertEqual(self.source.read_bytes(),self.source_bytes)
        state._control_area_ledger.assert_stocks(area_runtime.model_inventory(state,cfg))

    def test_partition_proof_counts_mapping_and_lane_tampering_fail(self):
        cfg,_,detectors,tuning,raw,_,_=self.built
        for kind in ('count','proof','mapping'):
            changed=deepcopy(detectors)
            if kind=='count':changed['physical_record_storage_projection']['21']['in_SC108_W']['count']=2.
            elif kind=='proof':changed['native_internal_record_partition_proof']['21']['source_sha256']='0'*64
            else:changed['link_to_origins']['21']=['SC108_to_SC109']
            with self.subTest(kind=kind),self.assertRaisesRegex(ValueError,'partition'):
                projection_support._verified_native_record_partitions(cfg,changed,raw,
                    json.loads((ROOT/tuning['observation']['physical_support_repair']).read_text()))
        changed=deepcopy(raw)
        next(r for r in changed['vehicle_records']['records'] if str(r['link_no'])=='21')['lane_no']=3
        with self.assertRaisesRegex(ValueError,'unverified signal lane'):native.record_partition(cfg,changed)

    def test_vehicle_exactly_at_head_is_still_pre_head_and_area_proof_cannot_change(self):
        cfg,_,_,_,raw,_,_=self.built;changed=deepcopy(raw)
        proof=cfg.network.native_input_signal_authority['inputs']['1083']
        for row in changed['vehicle_records']['records']:
            if str(row['link_no'])=='21':row['position_m']=proof['head_position_by_lane_m'][str(row['lane_no'])]
        partition,_=native.record_partition(cfg,changed)
        self.assertEqual(partition['21']['in_SC108_W']['count'],2.)
        self.assertEqual(partition['21']['SC108_to_SC109']['count'],0.)
        changed_cfg=deepcopy(cfg);changed_cfg.network.native_input_signal_authority['inputs']['1083']['movement_area_route']['target_inside']=False
        with self.assertRaisesRegex(ValueError,'area path differs'):native.record_partition(changed_cfg,raw)

    def test_future_generation_is_inside_finite_delayed_and_candidate_private(self):
        cfg,state,_,_,_,_,_=self.built;frozen=pickle.dumps(state);copy=state.copy()
        before=area_runtime.model_inventory(copy,cfg)
        native.advance(copy,self.action,DemandStep({}, {}, {}),cfg,180)
        count=copy.native_internal_input_state['inputs']['1083']['admitted_veh']
        self.assertAlmostEqual(count,400*5/3600)
        self.assertAlmostEqual(area_runtime.model_inventory(copy,cfg)['storage:in_SC108_W']-before['storage:in_SC108_W'],count)
        self.assertEqual((copy._control_area_ledger.entered_veh,copy._control_area_ledger.ttd_veh),(0,0))
        self.assertAlmostEqual(copy._control_area_ledger.flow_counts['input:internal:1083'],count)
        for name in ('urban_arrival_buffer','urban_storage_release_buffer'):
            self.assertAlmostEqual(sum(getattr(copy,name)['in_SC108_W'].values()),1+count)
        copy._control_area_ledger.assert_stocks(area_runtime.model_inventory(copy,cfg))
        self.assertEqual(pickle.dumps(state),frozen)

    def test_closed_first_signal_holds_and_open_first_signal_serves_existing_receiver(self):
        from evaluation.controllers.urban_flow_accounting import legsplit_substep_accounted
        from src.models import urban_queue_model as uqm
        cfg,initial,*_=self.built;state=initial.copy();action=self.action.copy()
        movement='SC108_W_to_E_SC109';key='movement:'+movement;red=green=0
        for step in range(180,210):
            fraction=uqm._phase_green_fraction(action,cfg,cfg.network.urban_movements[movement],urban_step_index=step)
            before=state._control_area_ledger.flow_counts.get(key,0.)
            legsplit_substep_accounted(state,action,DemandStep({}, {}, {}),cfg,urban_step_index=step,
                                      ramp_release_veh_h={r:0. for r in cfg.network.ramps})
            change=state._control_area_ledger.flow_counts.get(key,0.)-before
            if fraction==0:
                self.assertEqual(change,0.);red+=1
            elif change>0:green+=1
            state._control_area_ledger.assert_stocks(area_runtime.model_inventory(state,cfg))
        self.assertGreater(red,0);self.assertGreater(green,0)


if __name__=='__main__':unittest.main()
