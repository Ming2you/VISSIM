"""T1 (plan C11): the one switch loads the 31-cell v2 plant; v1 stays the 21-cell path."""
from __future__ import annotations

import copy
import unittest

import n31_fixtures as fx
from evaluation.controllers import lane_plant_runtime as lpr
from evaluation.controllers import obs150_contract as oc
from evaluation.controllers.freeway_refined_geometry import (apply_refined_partition, collapse_to_parents, parents,
                                                             validate_refinement, vsl_head_of_cell)


class RefinedGeometryTests(unittest.TestCase):
    """freeway_refined_geometry on the real C1 calibration geometry (no network parse)."""

    @classmethod
    def setUpClass(cls):
        cls.refined = fx.load_json(fx.GEOMETRY)
        cls.parent = collapse_to_parents(cls.refined)
        cls.partition = fx.load_json(fx.ROOT / fx.make_plant_n31.SOURCES['refined_partition'])

    def test_parents_and_counts(self):
        table = parents(self.refined)
        for road in ('FW_E', 'FW_W'):
            self.assertEqual(len(table[road]), 31)
            self.assertEqual(sorted(set(table[road])), list(range(21)))
            self.assertEqual(table[road], sorted(table[road]))

    def test_round_trip_through_parents(self):
        rebuilt = apply_refined_partition(self.parent, self.partition,
                                          pin={'path': 'x', 'sha256': self.refined['refined_partition']['sha256']})
        self.assertEqual(rebuilt['cells'], self.refined['cells'])
        self.assertEqual(rebuilt['bounds'], self.refined['bounds'])
        ports = lambda g: {b['id']: (b.get('from_cell'), b.get('to_cell')) for b in g['boundaries']}
        self.assertEqual(ports(rebuilt), ports(self.refined))

    def test_port_cells(self):
        by_id = {b['id']: b for b in self.refined['boundaries']}
        for ramp, cell in fx.EXPECTED_TO_CELL.items():
            self.assertEqual(by_id[ramp]['to_cell'], cell, ramp)
        offs = {str(b['connector']): b['from_cell'] for b in self.refined['boundaries'] if b['kind'] == 'offramp'}
        self.assertEqual(offs, fx.EXPECTED_FROM_CELL)

    def test_parent_vsl_tables(self):
        table = parents(self.refined)
        for road, expected in fx.EXPECTED_HEAD_OF_CELL.items():
            heads, head_of, zone_of = vsl_head_of_cell(table[road], [0, 5, 10, 15])
            self.assertEqual(heads, [0, 5, 10, 15])
            self.assertEqual(head_of, expected)
            self.assertEqual(zone_of, [[0, 5, 10, 15].index(h) for h in expected])
        with self.assertRaises(ValueError):
            vsl_head_of_cell(table['FW_E'], [5, 10])
        with self.assertRaises(ValueError):
            vsl_head_of_cell(table['FW_E'], [0, 21])

    def test_tampered_partitions_fail(self):
        pin = {'path': 'x', 'sha256': 'y'}
        shifted = copy.deepcopy(self.partition)
        shifted['bounds']['FW_E'][3] += 5.0
        with self.assertRaises(ValueError):
            apply_refined_partition(self.parent, shifted, pin=pin)
        moved = copy.deepcopy(self.partition)
        moved['boundaries'][0]['to_cell'] = 31
        with self.assertRaises(ValueError):
            apply_refined_partition(self.parent, moved, pin=pin)
        topology = copy.deepcopy(self.partition)
        topology['boundaries'][0]['chain_pos_m'] = topology['boundaries'][0].get('chain_pos_m', 0.0) + 7.0
        with self.assertRaises(ValueError):
            apply_refined_partition(self.parent, topology, pin=pin)
        with self.assertRaises(ValueError):
            apply_refined_partition(self.refined, self.partition, pin=pin)   # already refined

    def test_lane_km_is_kept(self):
        bad = copy.deepcopy(self.refined)
        cell = next(c for c in bad['cells'] if c['road'] == 'FW_W' and c['cell'] == 4)
        cell['lane_km'] += 0.01
        with self.assertRaises(ValueError):
            validate_refinement(self.parent, bad)


class V2LoadTests(unittest.TestCase):
    """load_sources on a v2 manifest (real network bytes, stubbed obs150 context)."""

    @classmethod
    def setUpClass(cls):
        cls.sandbox = fx.V2Sandbox().__enter__()
        with fx.obs150_stub():
            cls.context = lpr.load_sources(cls.sandbox.manifest)

    @classmethod
    def tearDownClass(cls):
        cls.sandbox.__exit__(None, None, None)

    def test_manifest_is_v2(self):
        self.assertEqual(oc.plant_mode(self.sandbox.document), 'v2')
        oc.validate_plant_manifest_v2(self.sandbox.document)
        self.assertEqual(self.context['plant_mode'], 'v2')

    def test_refined_component(self):
        component = self.context['component']
        for road in ('FW_E', 'FW_W'):
            self.assertEqual(len(component.base.network.freeway_segment_lanes[road]), 31)
            self.assertEqual(len([c for c in self.context['geometry']['cells'] if c['road'] == road]), 31)
        self.assertFalse(component.lane_groups_enabled)
        for key in lpr.V2_LANE_GROUP_FEATURES:
            self.assertFalse(getattr(component, key), key)
        self.assertEqual(component.component_boundary, {'source': 'admitted_interface', 'terminal': 'open_exit'})
        self.assertEqual(self.context['lane_geometry'], {})
        self.assertEqual({k: r['to_cell'] for k, r in component.ramps.items()}, fx.EXPECTED_TO_CELL)
        self.assertEqual({k: r['from_cell'] for k, r in component.offramps.items()}, fx.EXPECTED_FROM_CELL)

    def test_reference_capacities_and_receiving(self):
        component = self.context['component']
        self.assertEqual(component.ramps['RM_C10482']['service_capacity_veh_h'], 3600.0)
        self.assertEqual(component.ramps['RM_C10681']['service_capacity_veh_h'], 3600.0)
        self.assertEqual(set(component.ramp_receiving_nodes), {'RM_C10681', 'RM_C10484'})

    def test_live_geometry_equals_calibration(self):
        archived = fx.load_json(fx.GEOMETRY)
        self.assertEqual(self.context['geometry']['cells'], archived['cells'])
        self.assertEqual(self.context['geometry']['bounds'], archived['bounds'])
        self.assertEqual(self.context['parents'], parents(archived))

    def test_manifest_identity_reaches_obs150(self):
        self.assertEqual(self.context['obs150'].manifest_sha256, fx.sha256(fx.ROOT / self.sandbox.manifest))
        self.assertEqual(self.context['manifest_sha256'], fx.sha256(fx.ROOT / self.sandbox.manifest))

    def test_port_profile_is_c12(self):
        self.assertEqual(self.context['port_profile']['provenance']['schema'], 'sdmpc31-port-profile/v2')
        self.assertEqual(len(self.context['port_profile']['travel_speed_kmh']), 16)

    def _load_modified(self, change, stub=None):
        document = copy.deepcopy(self.sandbox.document)
        change(document)
        path = self.sandbox.dir / 'modified.json'
        path.write_bytes(fx.make_plant_n31.dumps(document))
        with fx.obs150_stub(**({} if stub is None else {'load_context': stub})):
            return lpr.load_sources(fx.rel(path))

    def test_v1_network_on_v2_key_fails(self):
        v1 = fx.load_json(fx.ROOT / fx.V1_PLANT)['sources']['network']

        def change(document):
            document['sources']['network'] = copy.deepcopy(v1)
        with self.assertRaisesRegex(ValueError, 'another network'):
            self._load_modified(change)

    def test_changed_pin_fails(self):
        def change(document):
            document['sources']['refined_partition']['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'Lane plant source changed'):
            self._load_modified(change)

    def test_lane_group_reference_config_fails(self):
        transport = fx.load_json(fx.ROOT / fx.V1_PLANT)['sources']['reference_config']

        def change(document):
            document['sources']['reference_config'] = copy.deepcopy(transport)
        with self.assertRaises(ValueError):
            self._load_modified(change)

    def test_foreign_obs150_context_fails(self):
        def other(document, paths, *, manifest_sha256=None):
            return fx.dataclasses.replace(fx.stub_context(document, paths, manifest_sha256=manifest_sha256),
                                          manifest_sha256='f' * 64)
        with self.assertRaisesRegex(ValueError, 'another plant manifest'):
            self._load_modified(lambda d: None, stub=other)

    def test_contract_rejects_mixed_manifest(self):
        document = copy.deepcopy(self.sandbox.document)
        document['lane_geometry'] = {'path': 'x', 'sha256': 'a' * 64}
        with self.assertRaises(oc.ObsContractError):
            oc.validate_plant_manifest_v2(document)


REAL_PLANT = 'diagnostics/sdmpc_n31_20260924/plant_n31_v2.json'


@unittest.skipUnless((fx.ROOT / REAL_PLANT).is_file() and (fx.ROOT / 'evaluation/controllers/obs150_observation.py').is_file(),
                     'plant_n31_v2.json (C8) or WP-B2 obs150_observation not present')
class RealPlantTests(unittest.TestCase):
    """The generated manifest with the real WP-E/B2 inputs and the real load_context."""

    @classmethod
    def setUpClass(cls):
        cls.document = fx.load_json(fx.ROOT / REAL_PLANT)
        cls.context = lpr.load_sources(REAL_PLANT)

    def test_identity_and_pins(self):
        oc.validate_plant_manifest_v2(self.document)
        self.assertEqual(self.context['manifest_sha256'], fx.sha256(fx.ROOT / REAL_PLANT))
        self.assertEqual(self.context['obs150'].manifest_sha256, self.context['manifest_sha256'])
        self.assertEqual(self.context['obs150'].network_sha256, fx.make_plant_n31.NETWORK_SHA256)
        self.assertEqual(self.context['obs150'].detector_csv_sha256, self.document['observation']['detectors']['sha256'])

    def test_context_agrees_with_the_component(self):
        component, obs = self.context['component'], self.context['obs150']
        self.assertEqual({k: r.from_cell for k, r in obs.offramps.items()},
                         {k: r['from_cell'] for k, r in component.offramps.items()})
        self.assertEqual({k for k, r in obs.ramp_arrivals.items() if r.receiving}, set(component.ramp_receiving_nodes))
        for road, rows in fx.calibration_schedules().items():
            self.assertEqual(tuple(obs.source_schedule[road]), rows)

    def test_observation_shapes_fit_the_lpr_consumers(self):
        """C4(h)/C5 preconditions on the real detector table: one ramp-arrival share per connector
        lane (LPR ramp specs), and the 10643 off entry on exactly the two lanes the port splits."""
        component, obs = self.context['component'], self.context['obs150']
        for name in component.ramp_receiving_nodes:
            ref = obs.ramp_arrivals[name]
            lanes = component.ramps[name]['lanes']
            self.assertEqual(tuple(ref.lanes), tuple(range(1, lanes + 1)), name)
            self.assertEqual(sorted(r.lane for r in obs.boundaries[ref.boundary_ref]), list(ref.lanes), name)
        off = obs.offramps['10643']
        self.assertEqual(tuple(off.lanes), (1, 2))
        self.assertEqual(sorted(r.lane for r in obs.boundaries[off.off_entry_ref]), [1, 2])
        for road in oc.ROADS:
            self.assertIn(obs.source_refs[road], obs.boundaries)

    def test_tuning_selects_this_manifest(self):
        tuning_path = fx.N31D / 'config_n31_v2.json'
        if not tuning_path.is_file():
            self.skipTest('config_n31_v2.json not generated')
        tuning = fx.load_json(tuning_path)
        self.assertEqual(tuning['freeway']['lane_plant'], REAL_PLANT)
        oc.validate_tuning_v2(tuning, self.document)


class V1PathTests(unittest.TestCase):
    """The v1 manifest keeps the 21-cell lane-group plant (one switch, v1 selectable)."""

    def test_v1_manifest_loads_21_cells(self):
        document = fx.load_json(fx.ROOT / fx.V1_PLANT)
        self.assertEqual(oc.plant_mode(document), 'v1')
        context = lpr.load_sources(fx.V1_PLANT)
        self.assertNotIn('plant_mode', context)
        self.assertTrue(context['lane_geometry'])
        for road in ('FW_E', 'FW_W'):
            self.assertEqual(len(context['component'].base.network.freeway_segment_lanes[road]), 21)
        self.assertTrue(context['component'].lane_groups_enabled)

    def test_v1_observe_state_is_observe_live(self):
        calls = []
        original = lpr.observe_live
        lpr.observe_live = lambda context, raw: calls.append(raw) or 'observation'
        try:
            raw = {'sim_sec': 900}
            state, observation = lpr.observe_state({'document': {}}, raw)
        finally:
            lpr.observe_live = original
        self.assertIs(state, raw)
        self.assertEqual(observation, 'observation')
        self.assertEqual(calls, [raw])

    def test_v2_context_refuses_v1_observer(self):
        with self.assertRaisesRegex(ValueError, 'observe_state'):
            lpr.observe_live({'plant_mode': 'v2'}, {})


if __name__ == '__main__':
    unittest.main()
