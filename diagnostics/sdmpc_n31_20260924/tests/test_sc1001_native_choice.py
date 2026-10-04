"""Selected SC1001 native choices preserve a complete approach partition."""
import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from evaluation.controllers.physical_movement_routes import configure_native_choice_groups

ROOT = Path(__file__).resolve().parents[3]
FOLDER = ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/baseline_reproduction_20260929/sc1001_native_choices'


class SC1001NativeChoiceTests(unittest.TestCase):
    def setUp(self):
        self.tuning = json.loads((FOLDER/'candidate_config.json').read_bytes())
        self.document = json.loads((FOLDER/'physical_routes.json').read_bytes())
        self.detectors = json.loads((ROOT/self.tuning['detector_mapping_json']).read_bytes())
        specs = {name:dict(spec,beta=1/3) for row in self.document['native_choice_groups'].values()
                 for name,spec in row['expected_specs'].items()}
        self.cfg = SimpleNamespace(network=SimpleNamespace(urban_movements=specs))
        self.raw = {'network_path':str(ROOT/self.document['network']['path']),
                    'run_provenance':{'files':{'network':self.document['network']}}}

    def apply(self, document=None):
        tuning = copy.deepcopy(self.tuning)
        with tempfile.TemporaryDirectory() as folder:
            if document is not None:
                p=Path(folder)/'proof.json';p.write_text(json.dumps(document),encoding='utf8')
                tuning['urban']['movements']['physical_route_topology']=str(p)
            return configure_native_choice_groups(self.cfg,self.detectors,tuning,state_json=self.raw)

    def test_all_three_partitions_preserve_total_and_only_change_beta(self):
        before = copy.deepcopy(self.cfg.network.urban_movements)
        result = self.apply()
        for name,row in result['native_choice_groups'].items():
            self.assertAlmostEqual(sum(row['after'].values()),1.)
            for movement,beta in row['after'].items():before[movement]['beta']=beta
        self.assertEqual(self.cfg.network.urban_movements,before)
        for approach,value in [('N_SC2002',.4),('E_SC1002',.625),('S_SC1003',10/12)]:
            self.assertAlmostEqual(before[f'SC1001_{approach}_to_W_RAMP']['beta'],value)

    def test_missing_choice_or_wrong_receiver_fails_atomically(self):
        for failure in ('missing','receiver'):
            with self.subTest(failure=failure):
                self.setUp();before=copy.deepcopy(self.cfg.network.urban_movements)
                doc=copy.deepcopy(self.document)
                if failure=='missing':
                    doc['native_choice_groups']['SC1001_E_SC1002']['route_to_movement'].pop('1118:1')
                else:self.detectors['link_to_origins']['31']=['wrong']
                with self.assertRaises(ValueError):self.apply(doc)
                self.assertEqual(self.cfg.network.urban_movements,before)

    def test_omitted_new_groups_leave_their_betas_unchanged(self):
        doc=copy.deepcopy(self.document)
        for name in list(doc['native_choice_groups']):
            if name.startswith('SC1001_'):del doc['native_choice_groups'][name]
        before={m:s for m,s in copy.deepcopy(self.cfg.network.urban_movements).items() if m.startswith('SC1001_')}
        self.apply(doc)
        self.assertEqual(before,{m:s for m,s in self.cfg.network.urban_movements.items() if m.startswith('SC1001_')})


if __name__=='__main__':unittest.main()
