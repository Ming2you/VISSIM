"""WP-B2 V0-9: the detector generator (plan B1) on the v2 network.

The committed table N31D/obs150/obs150_detectors_v2.csv and its build manifest
must be exactly what the generator makes from the sources the manifest records.
Every B1 assertion is exercised, and the negative cases show each one bites.
"""
from __future__ import annotations

import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_lane_support as sup  # noqa: E402
from test_lane_support import c  # noqa: E402

from evaluation.controllers import obs150_observation as ob  # noqa: E402

CSV = sup.ROOT / ob.DETECTOR_CSV_PATH
SIDECAR = Path(str(CSV)[:-4] + ob.SIDECAR_SUFFIX)


def generator():
    spec = importlib.util.spec_from_file_location('build_obs150_detectors', sup.ROOT / 'scripts' / 'build_obs150_detectors.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@unittest.skipUnless(sup.NET.is_file() and CSV.is_file(), 'v2 network or committed table missing')
class Generator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gen = generator()
        cls.manifest = json.loads(SIDECAR.read_text(encoding='utf-8'))
        sources = cls.manifest['sources']
        cls.args = SimpleNamespace(tuning=None, network=cls.manifest['network']['path'], geometry=sources['geometry']['path'],
                                   plan=sources['plan']['path'], runner_config=sources['runner_config']['path'],
                                   head_resource_contract=sources['head_resource_contract']['path'],
                                   head_free_contract=sources['head_free_contract']['path'],
                                   sig_dir=sources['sig_dir'], out=cls.manifest['output']['path'], check=True)
        cls.out, cls.csv_bytes, cls.manifest_bytes, cls.built = cls.gen.build(cls.args)
        cls.rows = c.parse_detector_csv(cls.csv_bytes)
        cls.net = sup.network()
        cls.geometry = json.loads((sup.ROOT / sources['geometry']['path']).read_text(encoding='utf-8-sig'))
        cls.plan = json.loads((sup.ROOT / sources['plan']['path']).read_text(encoding='utf-8'))
        cls.runner = ob.parse_runner_config((sup.ROOT / sources['runner_config']['path']).read_bytes().decode('latin-1'))

    def test_committed_table_and_manifest_are_reproduced(self):
        self.assertEqual(CSV.read_bytes(), self.csv_bytes)
        self.assertEqual(SIDECAR.read_bytes(), self.manifest_bytes)
        if (sup.ROOT / self.gen.DEFAULT_TUNING).is_file():
            # One tuning decides every source (plan 1.1): the default run reproduces the committed files.
            self.assertEqual(self.gen.main(['--check']), 0)
            tuning = json.loads((sup.ROOT / self.gen.DEFAULT_TUNING).read_text(encoding='utf-8-sig'))
            plant = json.loads((sup.ROOT / tuning['freeway']['lane_plant']).read_text(encoding='utf-8-sig'))
            self.assertEqual(plant['observation']['detectors'],
                             {'path': ob.DETECTOR_CSV_PATH, 'sha256': self.manifest['output']['sha256']})

    def test_counts(self):
        self.assertEqual(self.built['report']['counts'],
                         {'chain_end': 7, 'destination': 6, 'head': 210, 'headfree': 3, 'meter_head': 10,
                          'off_entry': 11, 'ramp_arrival': 10, 'source': 7, 'through': 28, 'x10643_exit': 2})
        self.assertEqual((self.built['report']['head_groups'], self.built['report']['eligible_heads']), (105, 210))
        self.assertEqual([r.dcp_no for r in self.rows], list(range(960001, 960001 + 294)))
        self.assertEqual(self.built['sig_programs_whole_seconds'], 42)
        self.assertEqual(len(self.built['contract_heads']), 3)

    def test_placements(self):
        by_ref = c.group_boundaries(self.rows)
        placement = {off: (p['kind'], p['link']) for off, p in self.built['report']['through_placement'].items()}
        self.assertEqual(placement, {'10479': ('at', 26), '10481': ('down', 10613), '10483': ('at', 119),
                                     '10491': ('up', 10771), '10638': ('at', 120), '10643': ('at', 2),
                                     '10645': ('at', 120), '10682': ('at', 2)})
        self.assertEqual([(r.link, r.lane, r.pos) for r in by_ref['through:10643']],
                         [(2, lane, 1808.011862) for lane in (1, 2, 3, 4)])
        source = by_ref['source:FW_E']
        self.assertEqual([(r.link, r.pos, r.segment[0].from_m, r.segment[0].to_m) for r in source],
                         [(74, 40.0, 0.0, 40.0)] * 4)
        # The source stations share their points with the RULE measurements 910030-33 / 910045-47.
        self.assertEqual({(r.link, r.lane, r.pos) for r in by_ref['source:FW_E'] + by_ref['source:FW_W']},
                         {(74, lane, 40.0) for lane in range(1, 5)} | {(26, lane, 40.0) for lane in range(1, 4)})
        end = by_ref['chain_end:FW_W'][0]
        self.assertEqual((end.link, end.pos_mode, end.orientation), (120, 'end_minus', 'up'))
        self.assertGreaterEqual(end.segment[0].to_m, self.net.links[120].length_m)
        x = by_ref['x10643_exit:10643']
        self.assertEqual([(r.lane, r.pos) for r in x], [(1, 318.898328), (2, 318.898328)])
        heads = {r.ref.split('|')[0] for r in self.rows if r.role == 'head'}
        eligible = {h['head_id'] for members in
                    __import__('evaluation.controllers.signal_head_observation', fromlist=['x']).physical_groups(
                        str(sup.NET), self.plan).values() for h in members}
        self.assertEqual(heads, eligible)

    def test_source_stations_share_the_rule_points(self):
        """The 7 source stations sit on the RULE points 910030-33 / 910045-47 (raw.rule_crosscheck)."""
        by_ref = c.group_boundaries(self.rows)
        sources = by_ref['source:FW_E'] + by_ref['source:FW_W']
        self.assertEqual(self.built['report']['rule_crosscheck'],
                         {str(r.dcm_no): n for r, n in zip(sources, (910030, 910031, 910032, 910033,
                                                                     910045, 910046, 910047))})
        pairs = ob.rule_crosscheck_pairs(self.rows)
        self.assertEqual([(n, r.boundary_ref, r.lane) for n, r in pairs],
                         [(910030 + i, 'source:FW_E', i + 1) for i in range(4)]
                         + [(910045 + i, 'source:FW_W', i + 1) for i in range(3)])
        obs = {'detectors': {str(r.dcm_no): 0 for r in self.rows}, 'rule_crosscheck': {}}
        for n, r in pairs:
            obs['detectors'][str(r.dcm_no)] = n - 910000
            obs['rule_crosscheck'][str(n)] = n - 910000
        self.assertEqual(len(ob.check_rule_crosscheck(obs, self.rows)), 7)
        obs['rule_crosscheck']['910046'] += 1
        with self.assertRaisesRegex(c.ObsContractError, 'source:FW_W lane 2: Vehs 46 differs from RULE'):
            ob.check_rule_crosscheck(obs, self.rows)

    def test_a_moved_rule_point_is_refused(self):
        net = copy.copy(self.net)
        net.dcp_points = dict(self.net.dcp_points)
        net.dcp_points[910045] = (26, 1, 41.0)
        with self.assertRaisesRegex(c.ObsContractError, 'RULE measurement 910045 is exactly one point'):
            self.build(net=net)

    def build(self, net=None, geometry=None, plan=None, runner=None):
        return ob.build_detector_rows(net or self.net, geometry or self.geometry, plan or self.plan,
                                      runner or self.runner)

    def test_key_collision(self):
        net = copy.copy(self.net)
        net.dcp_keys = set(self.net.dcp_keys) | {960100}
        with self.assertRaisesRegex(c.ObsContractError, 'key 960100 is unused'):
            self.build(net=net)

    def test_bypass_pair(self):
        geometry = copy.deepcopy(self.geometry)
        ramp = next(b for b in geometry['boundaries'] if b.get('connector') == 10681)
        ramp['to_cell'] = 11                                  # 10682 diverges from cell 11 before it
        with self.assertRaisesRegex(c.ObsContractError, 'bypass pair'):
            self.build(geometry=geometry)

    def test_connector_between_diverge_and_through_station(self):
        geometry = copy.deepcopy(self.geometry)
        geometry['bounds']['FW_E'][12] = 5100.0               # through:10682 moves past the 10681 merge
        with self.assertRaisesRegex(c.ObsContractError, 'attaches between the diverge'):
            self.build(geometry=geometry)

    def test_head_set_must_be_the_eligible_210(self):
        plan = copy.deepcopy(self.plan)
        plan['controllers'].pop('1004')
        with self.assertRaisesRegex(c.ObsContractError, '210 unique eligible heads'):
            self.build(plan=plan)

    def test_chain_must_match_the_geometry(self):
        runner = {'chains': {'FW_E': self.runner['chains']['FW_E'][:-1], 'FW_W': self.runner['chains']['FW_W']},
                  'meters': self.runner['meters']}
        with self.assertRaisesRegex(c.ObsContractError, 'runner chain equals the geometry chain'):
            self.build(runner=runner)

    def test_offset_segment_touched_by_a_connector(self):
        net = copy.copy(self.net)
        links = dict(self.net.links)
        links[99999] = ob.InpxLink(99999, 10.0, 1, 10.0, 5, 1, 0.0, 10481, 1, 0.5)   # lands in off_entry [0, 1)
        net.links = links
        with self.assertRaisesRegex(c.ObsContractError, 'touches segment'):
            self.build(net=net)

    def test_a_new_chain_exit_is_refused(self):
        net = copy.copy(self.net)
        links = dict(self.net.links)
        links[99998] = ob.InpxLink(99998, 10.0, 1, 10.0, 74, 1, 20.0, 5, 1, 0.0)    # leaves 74 at 20 m
        net.links = links
        with self.assertRaisesRegex(c.ObsContractError, 'chain exits'):
            self.build(net=net)

    def test_rd_1126_must_apply_to_all_vehicle_types(self):
        net = copy.copy(self.net)
        net.route_decisions = {**self.net.route_decisions,
                               1126: {**self.net.route_decisions[1126], 'all_veh_types': False}}
        with self.assertRaisesRegex(c.ObsContractError, 'RD 1126 applies to all vehicle types'):
            self.build(net=net)

    def test_off_ramp_must_diverge_inside_its_from_cell(self):
        geometry = copy.deepcopy(self.geometry)
        off = next(b for b in geometry['boundaries'] if b['kind'] == 'offramp' and b.get('connector') == 10643)
        geometry['bounds']['FW_E'][int(off['from_cell'])] = float(off['chain_pos_m']) + 0.5   # cell 9 starts past it
        with self.assertRaisesRegex(c.ObsContractError, 'off 10643 diverges inside its from_cell 9'):
            self.build(geometry=geometry)

    def test_generator_record_survives_a_crlf_checkout(self):
        """core.autocrlf=true checks the committed script out CRLF; its manifest record must not move."""
        lf = (sup.ROOT / 'scripts' / 'build_obs150_detectors.py').read_bytes().replace(b'\r\n', b'\n')
        self.assertEqual(self.manifest['generator'],
                         {'path': 'scripts/build_obs150_detectors.py', 'sha256_lf': sup.sha(lf)})
        with tempfile.TemporaryDirectory() as tmp:
            crlf = Path(tmp) / 'build_obs150_detectors.py'
            crlf.write_bytes(lf.replace(b'\n', b'\r\n'))
            self.assertEqual(self.gen._text_sha_lf(crlf), sup.sha(lf))

    def test_other_network_is_refused(self):
        args = SimpleNamespace(**{**vars(self.args), 'network': str(sup.PROBE.parent / 'network' / 'obs150_probe.inpx')})
        if not Path(args.network).is_file():
            self.skipTest('probe network copy missing')
        # The probe copy is byte-identical to v2 (PRB): it is accepted; a different file is not.
        self.assertEqual(ob.InpxNetwork(args.network).sha256, self.gen.V2_NETWORK_SHA256)
        args.network = str(sup.ROOT / 'diagnostics' / 'demand_sweep' / 'ramp_dsd_20260916_v2' / 'source_dsd' / 'baseline.inpx')
        if Path(args.network).is_file():
            with self.assertRaisesRegex(c.ObsContractError, 'not the v2 network'):
                self.gen.build(args)


class Guards(unittest.TestCase):
    """Input guards that need no network."""

    RUNNER = ('RW_FW_E_CHAIN_LINKS = "74,2"\nRW_FW_W_CHAIN_LINKS = "26"\n'
              'RW_RAMP_METER_IDS = "RM_A,RM_B"\nRW_RAMP_METER_SCS = "9101,9102"\n'
              'RW_RAMP_METER_CONNECTORS = "{connectors}"\n')

    def test_ramp_meter_lists_must_have_equal_length(self):
        parsed = ob.parse_runner_config(self.RUNNER.format(connectors='10481,10483'))
        self.assertEqual(parsed['meters'], (('RM_A', '9101', 10481), ('RM_B', '9102', 10483)))
        for connectors in ('10481', '10481,10483,10491'):     # zip would silently cut the longer lists
            with self.subTest(connectors=connectors):
                with self.assertRaisesRegex(c.ObsContractError, 'differ in length'):
                    ob.parse_runner_config(self.RUNNER.format(connectors=connectors))

    def test_contract_head_group_must_exist(self):
        """groups.get(key) == row['heads'] would pass for a missing group with heads null."""
        gen = generator()
        empty = {'resources': {}}
        for heads in (None, []):
            with self.subTest(heads=heads):
                resource = {'resources': {'10565': {'group': '999|SC0_p1', 'heads': heads}}}
                with self.assertRaisesRegex(c.ObsContractError, 'not a physical group'):
                    gen.contract_head_checks(None, {}, resource, empty)


if __name__ == '__main__':
    unittest.main()
