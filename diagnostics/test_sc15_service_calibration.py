from copy import deepcopy
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import hashlib,json,multiprocessing,pickle,tempfile,unittest
from diagnostics.prepare_sc15_service_calibration import blocks_from_rows
from diagnostics.test_native_route_choice import fixture,cohort,endpoint_worker
from evaluation.controllers import route_choice_corridor as rc,area_runtime
ROOT=Path(__file__).resolve().parents[1]

class CalibrationEvidence(unittest.TestCase):
    def test_consecutive_block_bounds_do_not_accumulate_per_gap_frame_error(self):
        crosses={('1086',i):{'vehicle_id':i,'lower_sec':10+2*i,'upper_sec':11+2*i,'linear_estimate_sec':10.5+2*i} for i in range(3)}
        gaps=[{'input_no':'1086','previous_vehicle_id':i,'vehicle_id':i+1,'queued_after_third_departure':True,'green_start_sec':10} for i in range(2)]
        blocks,excluded=blocks_from_rows(gaps,crosses,[])
        self.assertFalse(excluded);self.assertEqual(len(blocks),1);self.assertEqual(blocks[0]['gap_count'],2)
        self.assertEqual(blocks[0]['duration_upper_sec'],5.) # separate gap upper sum would be6
        self.assertEqual(blocks[0]['duration_lower_sec'],3.)
        blocks,excluded=blocks_from_rows(gaps,crosses,[(13,14)])
        self.assertFalse(blocks);self.assertEqual(len(excluded),2)

    def test_identity_selected_rate_and_holdout_leak_rejected(self):
        path=ROOT/'diagnostics/route_choice_corridor_1099_sc15_calibrated.json';doc=json.loads(path.read_text(encoding='utf-8'))
        proof=doc['native_fixed_service'];original=json.loads((ROOT/proof['calibrated_discharge']['path']).read_text(encoding='utf-8'))
        with tempfile.TemporaryDirectory(dir=ROOT/'diagnostics',prefix='sc15_calibration_test_') as temporary:
            out=Path(temporary)/'evidence.json'
            for kind in ('wrong_head','changed_rate','holdout_leak'):
                bad=deepcopy(original);row=bad['inputs']['1086']
                if kind=='wrong_head':row['signal_group']='1'
                elif kind=='changed_rate':row['selected_service_veh_h']+=1
                else:row['blocks'][0]['first_crossing_lower_sec']=900
                out.write_text(json.dumps(bad),encoding='utf-8');changed=deepcopy(proof)
                changed['calibrated_discharge']={'path':str(out.relative_to(ROOT)),'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'input_no':'1086'}
                with self.subTest(kind=kind),self.assertRaises(ValueError):rc._calibrated_native_service(doc,changed)

    def test_sc15_specific_override_leaves_global_movement_and_other_corridors_identical(self):
        legacy=fixture()[0];new=fixture(calibrated=True)[0]
        self.assertEqual(legacy.network.movement_capacity_by_movement_veh_h,new.network.movement_capacity_by_movement_veh_h)
        oldspec={s['decision']:s for s in rc._specs(legacy)};newspec={s['decision']:s for s in rc._specs(new)}
        for decision in ('1128','1129'):self.assertEqual(oldspec[decision],newspec[decision])
        for decision in ('1099','1100'):
            self.assertEqual(oldspec[decision]['per_lane_capacity_veh_h'],newspec[decision]['per_lane_capacity_veh_h'])
            self.assertNotIn('calibrated_service_veh_h',oldspec[decision]['native_fixed_service'])
            self.assertGreater(newspec[decision]['native_fixed_service']['calibrated_service_veh_h'],1000.)

    def test_shared_serial_branch_uses_same_new_budget_and_red_still_holds(self):
        cfg,state,action,_,_=fixture([cohort('1',4.),cohort('2',4.)],5,calibrated=True)
        spec=next(s for s in rc._specs(cfg) if s['decision']=='1099');rate=spec['native_fixed_service']['calibrated_service_veh_h']
        rc.advance(state,action,None,cfg,5)
        self.assertAlmostEqual(state.route_choice_corridor_state['departed_veh'],rate*cfg.simulation.T_u_h)
        self.assertGreater(state.route_choice_corridor_state['departed_veh'],spec['per_lane_capacity_veh_h']*cfg.simulation.T_u_h)
        state._control_area_ledger.assert_stocks(area_runtime.model_inventory(state,cfg))
        cfg,state,action,_,_=fixture([cohort('1',4.),cohort('2',4.)],20,calibrated=True)
        rc.advance(state,action,None,cfg,20);self.assertEqual(state.route_choice_corridor_state['departed_veh'],0.)

    def test_calibrated_full_receiver_still_holds(self):
        cfg,state,action,_,_=fixture([cohort('1')],5,calibrated=True);target='SC1_to_SC101'
        state.urban_link_storage[target]=0.;state._control_area_ledger.stocks['storage:'+target]={'inside':cfg.network.urban_link_storage_veh[target],'outside':0.}
        rc.advance(state,action,None,cfg,5);self.assertEqual(rc._tracked(state.route_choice_corridor_state,'native_1086_choice'),2.)
        self.assertEqual(state._control_area_ledger.event_count,0)

    def test_actual_450_repeat_copy_and_fresh_worker(self):
        cfg,state,action,raw,detectors=fixture(calibrated=True);payload=pickle.dumps((cfg,state,action,raw,detectors,3))
        expected=endpoint_worker(payload);self.assertEqual(expected,endpoint_worker(payload))
        with ProcessPoolExecutor(max_workers=1,mp_context=multiprocessing.get_context('spawn')) as pool:actual=pool.submit(endpoint_worker,payload).result(timeout=45)
        self.assertEqual(actual,expected);self.assertEqual(payload,pickle.dumps((cfg,state,action,raw,detectors,3)))
        for no in ('1086','1087'):self.assertAlmostEqual(expected[2]['inputs'][no]['unadmitted_demand_veh'],0.)

    def test_actual_450_omega_off_same_physics(self):
        cfg,state,action,raw,detectors=fixture(calibrated=True)
        from evaluation.controllers import vissim_stackelberg_adapter as adapter,area_meter_finalization
        from src.models.demand import DemandStep
        from src.simulation import coupling
        action=area_meter_finalization.finalize(action.copy(),cfg);forecast=adapter.demand_from_state(raw,cfg,DemandStep,3);states=[]
        for enabled in (True,False):
            private=deepcopy(cfg);private.network.control_area_enabled=enabled;current=state.copy()
            if not enabled:del current._control_area_ledger
            for demand in forecast:coupling.run_coupled_interval(current,action.copy(),demand,private);current.time_sec+=private.simulation.T_c_sec
            states.append((area_runtime.model_inventory(current,private),current.freeway_speed,current.route_choice_corridor_state,
                current.native_internal_input_state,current.urban_arrival_buffer,current.urban_storage_release_buffer))
        self.assertEqual(pickle.dumps(states[0]),pickle.dumps(states[1]))

if __name__=='__main__':unittest.main()
