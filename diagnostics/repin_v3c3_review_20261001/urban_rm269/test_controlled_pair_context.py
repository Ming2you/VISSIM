"""Reject mismatched model/native context before comparing replay gain."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
SOURCE = Path(sys.argv.pop(1)) if len(sys.argv) > 1 and sys.argv[1].endswith('.py') else ROOT / 'diagnostics/sdmpc_n31_20260924/integration_20260926/native_pair1200/analyze_pair.py'
spec = importlib.util.spec_from_file_location('controlled_pair_analyzer', SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def write(p, value):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value), encoding='utf8')


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


class ControlledPairContext(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='controlled_pair_context_')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'original/decisions'
        self.protocol_dir = self.root / 'pair'
        self.state = self.source / 'state_000300.json'
        self.area = self.root / 'membership.json'
        self.config = self.root / 'model.json'
        self.prediction_path = self.root / 'prediction.json'
        write(self.state, {'sim_sec': 300, 'vehicle_records': {'complete': True, 'records': []}})
        write(self.area, {'area': 'Omega701'})
        write(self.config, {'control_area_objective': {'membership_path': 'membership.json'}})
        for t in (1, 150):
            for suffix in ('.json', '.csv'):
                write(self.source / ('action_%06d%s' % (t,suffix)), {'t': t})
        write(self.source.parent / 'run_provenance_foo.json', {'seed':29, 'sim_period_sec':900,
            'files':{'network':{'sha256':'same-network'}}})
        self.prediction = {'status':'two_discrete_predictions_complete',
            'selected_model_caps_feasible':True, 'source_pins':{
                str(self.state):digest(self.state), str(self.config):digest(self.config)},
            'delta_omega_ttt_veh_h':-2., 'results':{}}
        for arm,cost in (('hold',10.),('selected',8.)):
            commands=[]
            for t in (300,450,600):
                path=self.protocol_dir/arm/'commands'/('action_%06d.csv' % t)
                write(path, {'arm':arm, 't':t})
                commands.append({'sim_sec':t, 'csv_sha256':digest(path)})
            self.prediction['results'][arm]={'omega_ttt_veh_h':cost, 'commands':commands,
                'shared_constraints':{'feasible':True, 'window':{'start_sec':300,'end_sec':750},
                    'np':{'target':100.},'nuf':{'target':1000.}}}
        write(self.prediction_path,self.prediction)
        self.protocol={'controller':'wu-link','arms':['hold','selected'],
            'start_sec':300,'end_sec':750,'control_start_sec':150,
            'future_observation_inputs':False,'controller_optimization':False,
            'sim_resolution':10,'vehicle_record_interval_sec':5,'seed':29,
            'network_sha256':'same-network','prediction_summary':str(self.prediction_path)}
        self.repin()

    def repin(self):
        self.protocol['command_pins']={str(p):digest(p) for p in self.root.rglob('*') if p.is_file()}

    def replace_prediction(self):
        write(self.prediction_path,self.prediction)
        self.repin()

    def check(self, area=None):
        return module.controlled_pair_context(self.protocol,self.source,self.config,area or self.area,
            protocol_dir=self.protocol_dir,root=self.root)

    def reject(self):
        with self.assertRaises((AssertionError,KeyError)):
            self.check()

    def test_valid_context_is_only_an_input_proof(self):
        result=self.check()
        self.assertEqual(result['predicted_delta_omega_veh_h'],-2.)
        self.assertNotIn('counterfactual_valid',result)

    def test_changed_original_command_rejected(self):
        write(self.source/'action_000150.csv',{'changed':True})
        self.reject()

    def test_wrong_seed_rejected(self):
        self.protocol['seed']=47
        self.reject()

    def test_incomplete_original_state_rejected_after_repin(self):
        write(self.state,{'sim_sec':300,'vehicle_records':{'complete':False}})
        self.repin()
        self.reject()

    def test_model_initialized_from_other_state_rejected(self):
        self.prediction['source_pins'][str(self.state)]='another-state'
        self.replace_prediction()
        self.reject()

    def test_different_area_rejected(self):
        other=self.root/'other_area.json'
        write(other,{'area':'narrower'})
        with self.assertRaises(AssertionError):
            self.check(other)

    def test_different_caps_rejected(self):
        self.prediction['results']['selected']['shared_constraints']['nuf']['target']=1100.
        self.replace_prediction()
        self.reject()

    def test_wrong_prediction_window_rejected(self):
        self.prediction['results']['hold']['shared_constraints']['window']['end_sec']=900
        self.replace_prediction()
        self.reject()

    def test_unpredicted_planned_command_rejected(self):
        write(self.protocol_dir/'selected/commands/action_000450.csv',{'changed':True})
        self.repin()
        self.reject()

    def test_infeasible_hold_rejected(self):
        self.prediction['results']['hold']['shared_constraints']['feasible']=False
        self.replace_prediction()
        self.reject()

    def test_delta_must_match_the_two_costs(self):
        self.prediction['delta_omega_ttt_veh_h']=2.
        self.replace_prediction()
        self.reject()


if __name__=='__main__':
    unittest.main()
