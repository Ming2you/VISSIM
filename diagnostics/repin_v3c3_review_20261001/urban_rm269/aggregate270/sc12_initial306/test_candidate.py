import copy, hashlib, json, pickle, unittest
from pathlib import Path
from candidate import project, SOURCE, LINK, MOVEMENTS
from evaluation.controllers import vissim_stackelberg_adapter as adapter
from evaluation.controllers.control_area_objective import get_ledger
from evaluation.controllers.physical_ramp_branches import split_tagged_arrival
from src.models.urban_queue_model import approach_routing
from state_check import equal

HERE=Path(__file__).resolve().parent; A=HERE.parent; ROOT=HERE.parents[4]
RAW=Path('D:/VISSIM_runs/20261007_goal8_prevention_s29_8100/sdmpc/decisions_sdmpc31_sdmpc8100_s29/state_002400.json')

def inputs():
    proof=json.loads((A/'sc12_phase305/current_projection.json').read_bytes())
    for p,h in proof['source_pins'].items():
        if hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h: raise ValueError('Evidence source changed: '+p)
    cfg,state,_=pickle.loads((A/'citysplit287/forecast2400/initial.pickle').read_bytes())
    raw=json.loads(RAW.read_bytes()); frame_path=RAW.parent/raw['obs150']['frames']['current']['path']
    assert hashlib.sha256(frame_path.read_bytes()).hexdigest()==raw['obs150']['frames']['current']['sha256']
    frame=json.loads(frame_path.read_bytes())
    tuning=json.loads((A/'flow279/config_10686_free.json').read_bytes())
    membership_path=ROOT/tuning['control_area_objective']['membership_path']
    membership=json.loads(membership_path.read_bytes())
    assert LINK in membership['inside_links'] or int(LINK) in membership['inside_links']
    network=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx'
    return cfg,state,raw,frame,network.read_bytes(),True,adapter._contiguous_stopline_queue(raw,per_lane=True)

class ProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.data=inputs()
    def apply(self, data=None):
        cfg,state,raw,frame,net,inside,lanes=data or self.data
        return project(state,cfg,raw,frame,net,inside,lanes)
    def test_exact_subset_preserves_mass_eta_and_other_owners(self):
        cfg,state,*_=self.data
        before=pickle.dumps(state,protocol=5)
        result,receipt=self.apply()
        self.assertEqual(before,pickle.dumps(state,protocol=5))
        self.assertEqual(receipt['parent_veh'],7.)
        self.assertEqual(receipt['untouched_parent_veh'],5.)
        self.assertEqual(receipt['due_sec'],2420.)
        self.assertEqual(result.urban_arrival_buffer,state.urban_arrival_buffer)
        self.assertEqual(result.urban_storage_release_buffer,state.urban_storage_release_buffer)
        self.assertEqual(result.urban_link_storage,state.urban_link_storage)
        changed={k for k,v in vars(result).items() if not equal(v,vars(state)[k])}
        self.assertEqual(changed,{'urban_movement_queue','local_observation_summary','gate_initial_route_tags','_control_area_ledger'})
        self.assertAlmostEqual(sum(receipt['queue_after'].values()),2.)
        self.assertEqual(receipt['tagged_residual'],{'SC12_W_SC11_to_N_SC6':2.})
        for m,n in state.urban_movement_queue.items():
            if m not in MOVEMENTS:self.assertEqual(result.urban_movement_queue[m],n)
        for k,v in state.gate_initial_route_tags.items():self.assertEqual(result.gate_initial_route_tags[k],v)
        for side in ('inside','outside'):
            self.assertAlmostEqual(sum(x[side] for x in get_ledger(result).stocks.values()),
                                   sum(x[side] for x in get_ledger(state).stocks.values()))
    def test_known_routes_and_explicit_lane_feasible_unknown(self):
        _,r=self.apply()
        self.assertEqual(sum(x['known'] for x in r['vehicles']),3)
        unknown=[x for x in r['vehicles'] if not x['known']]
        self.assertEqual(len(unknown),1)
        self.assertNotIn('SC12_W_SC11_to_S_SC16',unknown[0]['weights'])
        self.assertAlmostEqual(sum(unknown[0]['weights'].values()),1.)
        self.assertEqual(r['queue_after']['SC12_W_SC11_to_S_SC16'],0.)
    def test_existing_arrival_consumer_tags_only_two_of_seven(self):
        cfg=self.data[0]; state,r=self.apply()
        routing=approach_routing(cfg)[SOURCE]
        values=dict(split_tagged_arrival(state,cfg,SOURCE,242,7.,routing))
        self.assertAlmostEqual(sum(values.values()),7.)
        for m,b in routing:self.assertAlmostEqual(values[m],5*b+(2. if m.endswith('_N_SC6') else 0.))
        self.assertEqual(state.gate_initial_route_tags[SOURCE],{})
        self.assertIsNone(split_tagged_arrival(state,cfg,SOURCE,242,7.,routing))
    def test_reject_mismatched_time_duplicate_and_ambiguous_reservation(self):
        data=list(copy.deepcopy(self.data));data[3]['time_s']+=.1
        with self.assertRaises(ValueError):self.apply(data)
        data=list(copy.deepcopy(self.data));data[1].gate_initial_route_tags[SOURCE]={}
        with self.assertRaises(ValueError):self.apply(data)
        data=list(copy.deepcopy(self.data));data[1].urban_arrival_buffer[SOURCE]={242:2.,243:5.}
        data[1].urban_storage_release_buffer[SOURCE]={242:2.,243:5.}
        with self.assertRaises(ValueError):self.apply(data)
    def test_reject_conflicting_current_route_and_wrong_provenance(self):
        data=list(copy.deepcopy(self.data))
        next(v for v in data[3]['vehicles'] if v[0]==10356)[9]=10241.
        with self.assertRaises(ValueError):self.apply(data)
        data=list(copy.deepcopy(self.data))
        data[1].local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link'][LINK]['storage:'+SOURCE]=7.
        with self.assertRaises(ValueError):self.apply(data)

if __name__=='__main__':unittest.main(verbosity=2)
