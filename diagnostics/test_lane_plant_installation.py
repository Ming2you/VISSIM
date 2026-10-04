"""A declared plant hook must match the installed values, not just be truthy."""
import copy
import json
import unittest
from pathlib import Path
from types import SimpleNamespace

from evaluation.controllers import lane_plant_runtime as lpr


class InstallationTests(unittest.TestCase):
    def setUp(self):
        self.freeway = {
            'vsl_fd_response': {'FW_E': {'law': 'carlson', 'A': .5, 'E': 2., 'alpha': 0.}},
            'component_vsl_transport': {'FW_E': {'activation_cell': 16, 'restore_cell': 26}},
            'state_response': {'FW_E': {'delta_merge': .4, 'cell_overrides': {
                '23': {'anticipation': {'downstream_ge_local': 10., 'downstream_lt_local': 20.}}}}},
            'physical_cell_fd': {'FW_E': {'0': {'v_free': 110.}}},
        }
        installed = copy.deepcopy(self.freeway['state_response'])
        installed['FW_E']['cell_overrides']['23']['delta_merge'] = .4
        self.component = SimpleNamespace(base=SimpleNamespace(network=SimpleNamespace(
            freeway_vsl_fd_response=copy.deepcopy(self.freeway['vsl_fd_response']),
            component_vsl_transport=copy.deepcopy(self.freeway['component_vsl_transport']),
            freeway_state_response=installed)), cell_fd=copy.deepcopy(self.freeway['physical_cell_fd']))

    def check(self):
        return lpr._validate_component_features(self.component, {'freeway': self.freeway})

    def test_exact_install_including_inherited_cell_response_passes(self):
        self.check()

    def test_truthy_but_wrong_vsl_coefficient_fails(self):
        self.component.base.network.freeway_vsl_fd_response['FW_E']['A'] = 1.33
        with self.assertRaises(ValueError): self.check()

    def test_truthy_but_wrong_exposure_position_fails(self):
        self.component.base.network.component_vsl_transport['FW_E']['activation_cell'] = 15
        with self.assertRaises(ValueError): self.check()

    def test_truthy_but_wrong_cell_response_fails(self):
        self.component.base.network.freeway_state_response['FW_E']['cell_overrides']['23']['delta_merge'] = .8
        with self.assertRaises(ValueError): self.check()

    def test_missing_install_fails(self):
        del self.component.base.network.freeway_vsl_fd_response
        with self.assertRaises(ValueError): self.check()

    def test_undeclared_active_install_fails(self):
        del self.freeway['vsl_fd_response']
        with self.assertRaises(ValueError): self.check()

    def test_absent_hooks_pass(self):
        lpr._validate_component_features(SimpleNamespace(base=SimpleNamespace(network=SimpleNamespace())), {})

    def test_physical_cell_fd_stays_supported_and_checked(self):
        self.component.cell_fd['FW_E']['0']['v_free'] = 100.
        with self.assertRaises(ValueError): self.check()


class SelectedPlantTest(unittest.TestCase):
    def test_selected_64cf_expanded036_manifest_loads(self):
        root = Path(__file__).resolve().parents[1]
        path = root / ('diagnostics/sdmpc_n31_20260924/integration_20260926/'
            'baseline_reproduction_20260929/cellwise_calibration/coupled_expanded_joint/candidate_manifest.json')
        context = lpr.load_sources(path)
        reference = json.loads(context['paths']['reference_config'].read_text(encoding='utf-8-sig'))
        lpr._validate_component_features(context['component'], reference)
        self.assertEqual(context['document']['sources']['network']['sha256'],
            '64cf5f55fe9990f3e25bc4fedebf4ab1e4634c8138dbcf5697a136c48cb559dc')
        self.assertEqual({k: len(v) for k,v in context['parents'].items()}, {'FW_E': 31, 'FW_W': 31})


if __name__ == '__main__':
    unittest.main()
