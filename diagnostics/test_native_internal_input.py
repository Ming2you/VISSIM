"""Actual declared demand, finite admission and inside generation for1091."""
from copy import deepcopy
import json
from pathlib import Path
import pickle
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
from diagnostics import test_route_choice_projection_claim as fixture_module
from diagnostics.probe_model_area_integration import adapter
from evaluation.controllers import native_internal_input as native, projection_support, area_runtime
from evaluation.controllers.control_area_objective import physical_membership_from_ledger
from src.models.demand import DemandStep
from src.models.state import TrafficState

OPTION={'urban':{'native_internal_inputs':'diagnostics/native_internal_input_1091_ver2.json'}}


class NativeInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture_module.CorridorClaimTests.setUpClass()
        cls.f=fixture_module.CorridorClaimTests

    def fixture(self):
        f=self.f;cfg=deepcopy(f.cfg)
        native.configure(cfg,OPTION,f.raw,f.detectors)
        detectors,raw,_=native.prepare_projection(cfg,f.detectors,f.prepared)
        detectors,raw,_=projection_support.configure(cfg,f.tuning,detectors,raw)
        calibration=adapter.load_optional_json(str(ROOT/'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json'))
        calibration=adapter.deep_update(calibration,f.tuning.get('calibration_override',{}))
        state=adapter.traffic_state_from_vissim(raw,cfg,TrafficState,detectors,calibration)
        area_runtime.configure_initial_transit(cfg,f.tuning,state)
        native.initialize(state,cfg,raw,detectors)
        physical=physical_membership_from_ledger(json.loads((ROOT/'diagnostics/control_area_membership.json').read_text()))
        area_runtime.seed_from_projection(state,cfg,physical)
        native.extend_area_routes(cfg)
        return cfg,state,detectors,raw

    def test_recorded_run_schedule_and_all_interval_scaling(self):
        cfg,state,_,_=self.fixture()
        spec=cfg.network.native_internal_inputs
        self.assertEqual(spec['expected_internal_demand_veh_h'],2120.)
        self.assertEqual(spec['expected_internal_demand_veh_h'],spec['observed_internal_demand_veh_h'])
        schedule=spec['inputs']['1091']['schedule']
        self.assertEqual([r['rate_veh_h'] for r in schedule],[112.,160.,168.,144.,112.,80.])
        self.assertAlmostEqual(native.demand_amount(schedule,895,905),(112*5+160*5)/3600)
        self.assertAlmostEqual(native.demand_amount(schedule,0,5400),194.)
        self.assertAlmostEqual(spec['inputs']['1091']['minimum_approach_distance_m'],459.796362289654)
        self.assertEqual((state._control_area_ledger.entered_veh,state._control_area_ledger.ttd_veh,state._control_area_ledger.event_count),(0,0,0))

    def test_accepted_generation_adds_inventory_without_boundary_entry_and_pairs_buffers(self):
        cfg,state,_,_=self.fixture()
        target='in_SC1_E';ledger=state._control_area_ledger
        before=area_runtime.model_inventory(state,cfg)
        arrivals=sum(state.urban_arrival_buffer.get(target,{}).values())
        releases=sum(state.urban_storage_release_buffer.get(target,{}).values())
        index=state.native_internal_input_state['last_step']+1
        output=native.advance(state,None,DemandStep({}, {}, {}),cfg,index)['native_internal_input_step']['1091']
        admitted=output['generated_inside_veh']
        self.assertAlmostEqual(admitted,160*5/3600)
        after=area_runtime.model_inventory(state,cfg)
        self.assertAlmostEqual(after['storage:'+target]-before['storage:'+target],admitted)
        self.assertAlmostEqual(sum(state.urban_arrival_buffer[target].values())-arrivals,admitted)
        self.assertAlmostEqual(sum(state.urban_storage_release_buffer[target].values())-releases,admitted)
        self.assertEqual((ledger.entered_veh,ledger.ttd_veh),(0,0))
        self.assertAlmostEqual(ledger.flow_counts['input:internal:1091'],admitted)
        ledger.assert_stocks(after)
        self.assertEqual(output['boundary_entry_veh'],0.)

    def test_full_receiver_retains_unadmitted_demand_and_releases_when_space_exists(self):
        cfg,state,_,_=self.fixture()
        del state._control_area_ledger
        target='in_SC1_E';free=state.urban_link_storage[target]
        state.urban_link_storage[target]=0.
        index=state.native_internal_input_state['last_step']+1
        a=native.advance(state,None,DemandStep({}, {}, {}),cfg,index)['native_internal_input_step']['1091']
        self.assertEqual(a['generated_inside_veh'],0.)
        self.assertAlmostEqual(a['unadmitted_demand_veh'],160*5/3600)
        state.urban_link_storage[target]=free
        b=native.advance(state,None,DemandStep({}, {}, {}),cfg,index+1)['native_internal_input_step']['1091']
        self.assertAlmostEqual(b['generated_inside_veh'],160*10/3600)
        self.assertAlmostEqual(b['unadmitted_demand_veh'],0.)

    def test_candidate_private_state_duplicate_step_and_double_forecast_rejected(self):
        cfg,state,_,_=self.fixture()
        copied=state.copy();before=deepcopy(state.native_internal_input_state)
        index=copied.native_internal_input_state['last_step']+1
        native.advance(copied,None,DemandStep({}, {}, {}),cfg,index)
        self.assertEqual(state.native_internal_input_state,before)
        saved=pickle.dumps(copied)
        with self.assertRaisesRegex(ValueError,'sequential candidate state'):
            native.advance(copied,None,DemandStep({}, {}, {}),cfg,index)
        self.assertEqual(pickle.dumps(copied),saved)
        with self.assertRaisesRegex(ValueError,'duplicate an external forecast'):
            native.advance(state,None,DemandStep({}, {'in_SC1_E':1.}, {}),cfg,index)
        self.assertEqual(state.native_internal_input_state,before)

    def test_claim_cannot_be_forged_or_supplied_without_config(self):
        cfg,_,detectors,raw=self.fixture()
        detectors=deepcopy(detectors);detectors['native_internal_verified_physical_stock']['10381']='SC11_to_SC1'
        with self.assertRaisesRegex(ValueError,'differs from validated source contract'):
            projection_support.configure(cfg,self.f.tuning,detectors,raw)
        cfg=deepcopy(cfg);cfg.network.native_internal_inputs['inputs']['1091']['target_storage']='SC11_to_SC1'
        with self.assertRaisesRegex(ValueError,'verified stock contract differs'):
            native.projection_claims(cfg,cfg.network.native_internal_inputs['network_sha256'])

    def test_source_gate_profile_and_movement_tampering_rejected(self):
        f=self.f
        bad=deepcopy(f.raw);bad['demand']['urban_internal_volume_vph']+=1.
        with self.assertRaisesRegex(ValueError,'scaled schedule differs'):
            native.configure(deepcopy(f.cfg),OPTION,bad,f.detectors)
        bad=deepcopy(f.raw);bad['demand']['urban_volume_vph_by_gate']['in_SC1_E']=1.
        with self.assertRaisesRegex(ValueError,'already has external gate demand'):
            native.configure(deepcopy(f.cfg),OPTION,bad,f.detectors)
        document=json.loads((ROOT/OPTION['urban']['native_internal_inputs']).read_text())
        with tempfile.TemporaryDirectory(prefix='native-input-contract-',dir=ROOT/'diagnostics') as folder:
            path=Path(folder)/'bad.json'
            for field,value,pattern in [('physical_source','1220008203','unmapped internal source'),
                                        ('target_storage','in_SC1_N','canonical stopline'),
                                        ('approach_path',['236','10382','1210008203'],'Disconnected/backward')]:
                data=deepcopy(document);data['inputs']['1091'][field]=value;path.write_text(json.dumps(data),encoding='utf-8')
                option={'urban':{'native_internal_inputs':str(path)}}
                with self.subTest(field=field),self.assertRaisesRegex(ValueError,pattern):
                    native.configure(deepcopy(f.cfg),option,f.raw,f.detectors)

    def test_absent_flag_preserves_inputs_and_buffers(self):
        cfg=deepcopy(self.f.cfg);before=pickle.dumps(cfg)
        self.assertEqual(native.configure(cfg,{},self.f.raw,self.f.detectors),{})
        self.assertEqual(pickle.dumps(cfg),before)
        d,r,m=native.prepare_projection(cfg,self.f.detectors,self.f.raw)
        self.assertIs(d,self.f.detectors);self.assertIs(r,self.f.raw);self.assertEqual(m,{})
        self.assertEqual(native.advance(None,None,None,cfg,0),{})


if __name__=='__main__':unittest.main()
