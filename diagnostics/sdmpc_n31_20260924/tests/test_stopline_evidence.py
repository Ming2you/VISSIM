"""K8-6 SA evidence (stopline-approach-evidence/v2): builder pins, OPT1_V2_SPEC 1.9 reproduction, SA view.

Light: the builder reads the sha-pinned opt1v2/amend1 outputs (JSON only). The rebuild rows skip with a fixed
reason when those scratch inputs are not on this machine; the committed-evidence rows always run.
"""
from __future__ import annotations

import copy
import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
STOPLINE = HERE.parent / 'stopline'
for extra in (ROOT, ROOT / 'vendor/NumSim-mine', HERE, STOPLINE):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

import build_sc1001eb_evidence as B  # noqa: E402
import stopline_toy as T  # noqa: E402
from evaluation.controllers import stopline_approach as SA  # noqa: E402

EVIDENCE = ROOT / B.OUT_REL
INPUTS_PRESENT = all((B.DEFAULT_INPUTS / B.PINS[k][0]).is_file() for k in ('a1v2_visit', 's2_lanefull', 'g2_inpx')) \
    and B.DEFAULT_LOSO.is_file()
SKIP_REASON = 'sha-pinned evidence inputs (stopline/inputs) not present in this checkout'


def committed():
    data = EVIDENCE.read_bytes()
    return json.loads(data.decode('utf-8')), hashlib.sha256(data).hexdigest()


class CommittedEvidenceTests(unittest.TestCase):
    def test_spec_19_values(self):
        doc, _digest = committed()
        B.check_spec(doc)
        a = doc['approaches']['SC1001_EB']
        self.assertEqual(doc['schema'], SA.EVIDENCE_SCHEMA)
        self.assertEqual(doc['inputs']['g2_inpx']['extract_sha12'], SA.GEOMETRY_SHA12)
        self.assertEqual([a['lanes'][l]['s_veh_h_lane'] for l in '123'],
                         [2030.9375, 1581.7040358744396, 2101.923076923077])
        self.assertEqual([a['lanes'][l]['head_pos_m'] for l in '123'],
                         [621.666240433568, 621.5682806829368, 621.461546643362])
        self.assertEqual([a['lanes'][l]['storage_veh']['observed_full'] for l in '12'], [81.0, 63.0])
        self.assertEqual(a['lanes']['3']['storage_veh']['observed_full'], a['lanes']['3']['storage_veh']['geometric'])
        self.assertEqual(a['p_lane1_given_E'], 5768 / 11007)
        self.assertEqual(a['posthead_lane_prior']['1'], {'E': 5768 / 6850, 'S': 1082 / 6850})
        self.assertEqual(a['upstream_lane_frames'], {'1': 130861, '2': 111413, '3': 8064})
        self.assertEqual(a['judging_storage_arm'], 'observed_full')               # D-K8-1
        for key, (name, digest, declaration) in B.PINS.items():
            self.assertEqual(doc['inputs'][key]['sha256'], digest)
            if declaration:
                self.assertEqual(doc['inputs'][key]['declaration_sha16'], declaration)
        self.assertIs(doc['inputs']['s2_loso']['checked'], False)
        self.assertIs(doc['inputs']['network']['checked'], False)

    def test_builder_pin_is_current(self):
        doc, _digest = committed()
        self.assertEqual(doc['builder']['sha256'], B.sha256(ROOT / B.BUILDER_REL))
        self.assertEqual(doc['inputs']['mapping']['sha256'], B.sha256(ROOT / B.MAPPING[0]))
        self.assertEqual(doc['inputs']['support']['sha256'], B.sha256(ROOT / B.SUPPORT[0]))

    def test_spec_drift_is_refused(self):
        doc, _digest = committed()
        mutations = (
            lambda d: d['approaches']['SC1001_EB']['lanes']['2'].__setitem__('s_veh_h_lane', 1581.7040358744398),
            lambda d: d['approaches']['SC1001_EB']['lanes']['1']['storage_veh'].__setitem__('observed_full', 82.0),
            lambda d: d['approaches']['SC1001_EB']['posthead_lane_prior']['1'].__setitem__('E', 0.85),
            lambda d: d['approaches']['SC1001_EB'].__setitem__('posthead_rehome', {}),
            lambda d: d['approaches']['SC1001_EB'].__setitem__('pre_stopline_links', ['32', '129', '10777', '127']),
            lambda d: d['approaches']['SC1001_EB']['ports']['10491']['landing'].__setitem__(1, 239.5),
            lambda d: d['report']['origin_prior_sg2'].__setitem__('OFF_W', 0.61),
        )
        for index, mutate in enumerate(mutations):
            with self.subTest(index):
                broken = copy.deepcopy(doc)
                mutate(broken)
                with self.assertRaises(SystemExit):
                    B.check_spec(broken)

    def test_view_for_both_arms(self):
        doc, digest = committed()
        for arm, expected in (('observed_full', (81.0, 63.0)), ('geometric', (621.666240433568 / 6.0,
                                                                              621.5682806829368 / 6.0))):
            with self.subTest(arm):
                cfg = T.config()
                spec = SA.build_view(cfg, T.section(arm), doc, digest)
                self.assertEqual((spec['lanes'][1]['S'], spec['lanes'][2]['S']), expected)
                self.assertEqual(spec['lanes'][3]['S'], 621.461546643362 / 6.0)
                self.assertEqual(spec['lanes'][1]['sigma'], 621.666240433568 / spec['lanes'][1]['S'])
                self.assertEqual(spec['members'], (T.E, T.S, T.N))
                self.assertEqual(spec['posthead_rehome'], {'10695': 'SC1001_to_SC2002'})
                self.assertEqual((spec['connector_link'], spec['tail_link']), ('10777', '129'))
                self.assertEqual(round(spec['exit129_m'], 3), 301.926)
                self.assertEqual(spec['route_exit'], {'1117:3': 'E', '1117:1': 'S', '1117:2': 'N'})
                state = T.state(cfg, 120)
                cfg.network.stopline_approach = spec
                SA._bind_ports(state, cfg, spec)
                weights = spec['ports']['10491']['weights']
                self.assertAlmostEqual(weights[1] + weights[2] + weights[3], 1.0, places=12)


class RepositoryInputsTests(unittest.TestCase):
    """Amendment 5 section 6: the builder defaults to the sha-pinned byte copies inside the repository."""

    def test_defaults_are_the_pinned_repository_copies(self):
        self.assertEqual(B.DEFAULT_INPUTS, ROOT / B.INPUTS_REL)
        self.assertEqual(B.DEFAULT_LOSO, B.DEFAULT_INPUTS / 's2_loso_out.json')
        self.assertTrue(B.DEFAULT_INPUTS.resolve().is_relative_to(ROOT.resolve()))
        for key, (name, digest, _declaration) in B.PINS.items():
            with self.subTest(key):
                path = B.DEFAULT_LOSO if key == 's2_loso' else B.DEFAULT_INPUTS / name
                self.assertEqual(B.sha256(path), digest)
        self.assertEqual(sorted(p.name for p in B.DEFAULT_INPUTS.iterdir()),
                         sorted(row[0] for row in B.PINS.values()))
        self.assertNotIn('AppData', Path(B.__file__).read_text(encoding='utf-8'))      # no scratch default left


@unittest.skipUnless(INPUTS_PRESENT, SKIP_REASON)
class RebuildTests(unittest.TestCase):
    def test_rebuild_is_byte_identical(self):
        self.assertEqual(B.dumps(B.build()), EVIDENCE.read_bytes())
        B.main(['--check'])

    def test_input_pins_are_enforced(self):
        tmp = Path(tempfile.mkdtemp(prefix='_sa_evidence_', dir=HERE))
        try:
            for name in ('a1v2_visit.json', 's2_lanefull.json', 'g2_inpx_v3c3.json'):
                shutil.copyfile(B.DEFAULT_INPUTS / name, tmp / name)
            loso = tmp / 's2_loso_out.json'
            shutil.copyfile(B.DEFAULT_LOSO, loso)
            self.assertEqual(B.dumps(B.build(tmp, loso)), EVIDENCE.read_bytes())
            for name in ('s2_lanefull.json', 'g2_inpx_v3c3.json', 's2_loso_out.json'):
                with self.subTest(name):
                    original = (tmp / name).read_bytes()
                    (tmp / name).write_bytes(original + b' ')
                    with self.assertRaises(SystemExit):
                        B.build(tmp, loso)
                    (tmp / name).write_bytes(original)
        finally:
            shutil.rmtree(tmp)


if __name__ == '__main__':
    unittest.main()
