"""Keep the source-proven SC1005 lane1 bypass separate from controlled lanes."""
from copy import deepcopy
import json
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

from diagnostics.test_native_signal_contract import fixture, ROOT
from evaluation.controllers.signal_actuation_contract import phase_fraction

D = ROOT / 'diagnostics/control_improvement/decision_common_anchor_20260911/ramp8_physical_v1'
WEST = ('SC1005_N_SC105_to_W', 'SC1005_N_SC105_to_W_SC1004')


class NativeBypassTests(unittest.TestCase):
    def test_correction_changes_only_two_movement_flags(self):
        before = json.loads((D/'joint_config_fast_np_v2.json').read_text(encoding='utf-8-sig'))
        after = json.loads((D/'joint_config_fidelity_v1.json').read_text(encoding='utf-8-sig'))
        expected = deepcopy(before)
        for key in WEST:
            expected['config_overrides']['network']['urban_movements'][key]['unsignalized'] = True
        for key in ('name', 'description'):
            after.pop(key); expected.pop(key)
        self.assertEqual(after, expected)

    def test_merged_west_turn_has_no_head_and_east_turn_crosses_head(self):
        joined = json.loads((ROOT/'diagnostics/control_area_movement_join_physical_routes.json').read_text())['by_movement']
        west = joined[WEST[1]]
        east = joined['SC1005_N_SC105_to_E_SC107']
        self.assertEqual(set(west['merged_from']), set(WEST))
        self.assertEqual([r['connector'] for r in west['physical_turns']], ['10565'])
        self.assertEqual([r['connector'] for r in east['physical_turns']], ['10570'])
        doc = ET.parse(ROOT/'diagnostics/fixed_beta300v3_network_arms_flat_v1/baseline.inpx').getroot()
        links = {x.get('no'): x for x in doc.findall('./links/link')}
        self.assertEqual(links['10565'].find('fromLinkEndPt').get('lane'), '403 1')
        self.assertEqual(links['10570'].find('fromLinkEndPt').get('lane'), '403 2')
        self.assertEqual(len(links['10570'].findall('./lanes/lane')), 2)
        heads = [x for x in doc.iter('signalHead') if x.get('lane', '').startswith('403 ')]
        self.assertFalse(any(x.get('lane') == '403 1' for x in heads))
        self.assertEqual({x.get('lane') for x in heads}, {'403 2', '403 3'})
        self.assertEqual({x.get('sg') for x in heads}, {'1005 7'})
        self.assertTrue(all(float(x.get('pos')) < float(links['10570'].find('fromLinkEndPt').get('pos')) for x in heads))

    def test_bypass_ignores_red_but_controlled_sibling_does_not(self):
        cfg, _, _, action, _ = fixture()
        old = json.loads((D/'joint_config_fast_np_v2.json').read_text())['config_overrides']['network']['urban_movements']
        new = json.loads((D/'joint_config_fidelity_v1.json').read_text())['config_overrides']['network']['urban_movements']
        for key in WEST:
            red_steps = [i for i in range(30) if phase_fraction(action, cfg, old[key], i) == 0]
            self.assertTrue(red_steps)
            for i in red_steps:
                self.assertEqual(phase_fraction(action, cfg, new[key], i), 1.)
                self.assertEqual(phase_fraction(action, cfg, old[key], i), 0.)
        sibling = 'SC1005_N_SC105_to_E_SC107'
        self.assertEqual(old[sibling], new[sibling])
        self.assertTrue(any(phase_fraction(action, cfg, new[sibling], i) == 0 for i in range(30)))


if __name__ == '__main__':
    unittest.main()
