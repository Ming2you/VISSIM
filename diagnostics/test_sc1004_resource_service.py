"""Focused proof and consumer regression. No full optimizer or trajectory scan."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import hashlib,json,math,pickle,tempfile,unittest,xml.etree.ElementTree as ET
from diagnostics.test_route_choice_corridor import base,synthetic
from evaluation.controllers import route_choice_corridor as rc
ROOT=Path(__file__).resolve().parents[1]
EVIDENCE='diagnostics/route_choice_corridor_sc1004_calibrated.json'
CALIBRATION=ROOT/'diagnostics/sc1004_resource_service_calibration.json'
MEMBERS=('SC1004_W_to_E_SC1005','SC1004_offE_to_E_SC1005','SC1004_offW_to_E_SC1005')


def configure(module,enabled):
    (cfg,_,detectors,tuning,raw,_,metadata),_=deepcopy(base())
    tuning['urban']['route_choice_corridor']={'evidence_path':EVIDENCE if enabled else 'diagnostics/route_choice_corridor_ver2.json','unknown_policy':'hold_diagnostic'}
    observed=(pickle.dumps(raw),pickle.dumps(detectors),pickle.dumps(tuning))
    result=module.configure(cfg,tuning,raw,detectors,per_lane_capacity_veh_h=metadata['movement_capacity_by_lanes_per_lane_veh_h'])
    if observed!=(pickle.dumps(raw),pickle.dumps(detectors),pickle.dumps(tuning)):raise AssertionError('Caller input mutated')
    return cfg,result


class ResourceServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.module=rc

    def test_train_only_and_exact_observed_resource(self):
        data=json.loads(CALIBRATION.read_text())
        self.assertEqual(data['train']['crossing_events'],566)
        self.assertEqual(data['train']['unique_vehicle_ids'],565)
        self.assertEqual(data['train']['native_green_exposure_sec'],1350)
        self.assertAlmostEqual(data['resource']['selected_service_veh_h'],1509.3333333333333)
        self.assertEqual([v['crossing_events'] for v in data['holdout_observed']],[50,52])
        self.assertEqual(data['full_observed']['crossing_events'],668)
        for event in data['train']['events']:
            self.assertFalse(any(event['lower_sec']<=b and event['upper_sec']>=a for a,b in data['time_holdouts_excluded_from_fit_sec']))
        # Repeated visits are counted as service, never as distinct vehicle IDs.
        self.assertEqual(len(data['train']['events'])-len({e['vehicle_id'] for e in data['train']['events']}),1)

    def test_absent_original_configuration_exact(self):
        fixture=ROOT/'diagnostics/fixtures/sc1004_configure_before_calibration.py'
        proof=json.loads(fixture.with_suffix('.json').read_text())
        self.assertEqual(hashlib.sha256(fixture.read_bytes()).hexdigest(),proof['fixture_sha256'])
        namespace=dict(vars(rc));exec(compile(fixture.read_text(),str(fixture),'exec'),namespace)
        with patch.object(rc,'_configure_one',namespace['_configure_one']):reference=configure(rc,False)
        actual=configure(rc,False)
        self.assertEqual(pickle.dumps(reference),pickle.dumps(actual))
        self.assertNotIn('calibrated_service_resources',actual[0].network.route_choice_corridor)

    def test_three_views_one_rate_only_and_unchanged_betas(self):
        before,_=configure(rc,False); after,_=configure(self.module,True)
        for movement,old in before.network.urban_movements.items():
            self.assertEqual(old,after.network.urban_movements[movement])
        self.assertEqual(before.network.urban_link_storage_veh,after.network.urban_link_storage_veh)
        rate=json.loads(CALIBRATION.read_text())['resource']['selected_service_veh_h']
        for movement,old in before.network.movement_capacity_by_movement_veh_h.items():
            self.assertEqual(after.network.movement_capacity_by_movement_veh_h[movement],rate if movement in MEMBERS else old)
        for movement,turn in after.network.route_choice_corridor['turns'].items():
            self.assertEqual(turn['service_veh_h'],rate if movement in MEMBERS else before.network.route_choice_corridor['turns'][movement]['service_veh_h'])
        self.assertEqual(set(after.network.route_choice_corridor['calibrated_service_resources']),{'10634'})
        # Config carries the numerical prior and immutable path/hash to workers.
        clone=pickle.loads(pickle.dumps(after))
        self.assertEqual(clone.network.route_choice_corridor,after.network.route_choice_corridor)

    def test_corrupt_proof_holdout_duplicates_scale_and_physical_heads_rejected(self):
        (cfg,_,_,_,_,_,meta),_=deepcopy(base())
        original=json.loads(CALIBRATION.read_text());document=json.loads((ROOT/EVIDENCE).read_text())
        tree=ET.parse(ROOT/document['network']['path']).getroot()
        links={x.get('no'):x for x in tree.findall('./links/link')};heads={x.get('no'):x for x in tree.findall('./signalHeads/signalHead')}
        for kind in ('holdout','duplicate','wrong_head','wrong_member','three_lane_multiplier','changed_exposure','nan','nan_exposure','nan_inherited'):
            changed=deepcopy(original)
            if kind=='holdout':changed['train']['events'][0]['lower_sec']=975.;changed['train']['events'][0]['upper_sec']=976.
            elif kind=='duplicate':changed['train']['events'][1]=deepcopy(changed['train']['events'][0])
            elif kind=='wrong_head':changed['resource']['head_by_lane']['3']='90030879'
            elif kind=='wrong_member':changed['resource']['members'].pop()
            elif kind=='three_lane_multiplier':changed['resource']['selected_service_veh_h']*=3
            elif kind=='changed_exposure':changed['train']['native_green_exposure_sec']+=1
            elif kind=='nan':changed['resource']['selected_service_veh_h']=float('nan')
            elif kind=='nan_exposure':changed['train']['native_green_exposure_sec']=float('nan')
            elif kind=='nan_inherited':changed['resource']['inherited_service_veh_h']=float('nan')
            with tempfile.TemporaryDirectory(dir=ROOT/'diagnostics') as directory:
                file=Path(directory)/'invalid.json';file.write_text(json.dumps(changed),encoding='utf-8')
                doc=deepcopy(document);doc['service_resource_calibration']={'path':str(file.relative_to(ROOT)),'sha256':hashlib.sha256(file.read_bytes()).hexdigest()}
                with self.subTest(kind=kind),self.assertRaises(ValueError):
                    self.module._calibrated_turn_services(doc,tree,links,heads,cfg.network.urban_movements,meta['movement_capacity_by_lanes_per_lane_veh_h'])

    def test_same_global_budget_partial_green_and_accepted_only(self):
        configured,_=configure(self.module,True)
        cfg,state,control,index=synthetic([])
        # Only transfer the same actual consumer's rate fields to an initialized
        # empty corridor fixture; physical stock/projection remain canonical.
        cfg.network.movement_capacity_by_movement_veh_h=deepcopy(configured.network.movement_capacity_by_movement_veh_h)
        cfg.network.route_choice_corridor['turns']=deepcopy(configured.network.route_choice_corridor['turns'])
        cfg.network.route_choice_corridor['calibrated_service_resources']=deepcopy(configured.network.route_choice_corridor['calibrated_service_resources'])
        from evaluation.controllers import local_signal_service
        local_signal_service.configure(cfg,{'urban':{'shared_local_service_pool':True}})
        from src.models import urban_queue_model as uqm
        from evaluation.controllers.control_area_objective import emit_transfer
        receiver=cfg.network.route_choice_corridor['prefix_storage'];fraction=.4
        rate=cfg.network.route_choice_corridor['turns'][MEMBERS[0]]['service_veh_h'];limit=rate*cfg.simulation.T_u_h*fraction
        with patch.object(uqm,'_phase_green_fraction',return_value=fraction):
            rc.advance(state,control,None,cfg,index)
            wanted={m:rc.intended_departure(state,control,cfg,m,100.,index) for m in MEMBERS}
            feasible=rc.limit_intended_batch(state,cfg,wanted,index)
            self.assertAlmostEqual(sum(feasible.values()),limit)
            # Receiving permits only half. The unaccepted remainder is reusable.
            member=MEMBERS[1];amount=limit/2
            source=cfg.network.off_ramp_storage_link[cfg.network.urban_movements[member]['off_ramp']]
            state.urban_link_storage[source]+=amount
            state.urban_link_storage[receiver]-=amount
            emit_transfer(state,cfg,'storage:'+source,'storage:'+receiver,amount,preserve_area=True)
            rc.receive_accepted(state,cfg,member,amount,index)
            self.assertAlmostEqual(rc.intended_departure(state,control,cfg,MEMBERS[1],100.,index),limit/2)
            clone=state.copy();clone.route_choice_corridor_state['service_used_veh']['10634']=limit
            self.assertAlmostEqual(state.route_choice_corridor_state['service_used_veh']['10634'],limit/2)
            self.assertEqual(rc.intended_departure(clone,control,cfg,MEMBERS[2],100.,index),0.)
            rc.advance(state,control,None,cfg,index+1)
            self.assertAlmostEqual(rc.intended_departure(state,control,cfg,MEMBERS[2],100.,index+1),limit)

    def test_calibration_requires_the_actual_local_pool_main_and_worker(self):
        cfg,_=configure(rc,True)
        from evaluation.controllers import local_signal_service
        with self.assertRaises(ValueError):local_signal_service.configure(cfg,{'urban':{'shared_local_service_pool':False}})
        with self.assertRaises(ValueError):local_signal_service.install(cfg)
        local_signal_service.configure(cfg,{'urban':{'shared_local_service_pool':True}})
        clone=pickle.loads(pickle.dumps(cfg))
        local_signal_service.install(clone)
        self.assertEqual(clone.network.local_service_pool['groups']['10634']['service_veh_h'],1509.3333333333333)


if __name__=='__main__':unittest.main()
