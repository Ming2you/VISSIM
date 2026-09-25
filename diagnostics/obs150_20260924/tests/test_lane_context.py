"""WP-B2, plan 1.6: load_context on the real sources.

The manifest pins the network the committed detector table was built from (its
sidecar; the N31D copy of v3b be0075bf since the 2026-09-25 re-pin, before that
v2 f475ce42: load_context refuses a table built from another network), that
network's s31 no-control 31-cell geometry (the sidecar's), the n31
reference config, a lane_native runner config (the chain lists are the ones
lane_native_b110.vbs copies) and a sig_manifest.json whose 42 .sig byte copies
sit next to it (written to a temporary folder here; WP-E owns the real one).
The detector table is the committed N31D CSV; load_context must re-derive it.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_lane_support as sup  # noqa: E402
from test_lane_support import c, fx  # noqa: E402

from evaluation.controllers import obs150_observation as ob  # noqa: E402

SIDECAR = Path(str(sup.ROOT / ob.DETECTOR_CSV_PATH)[:-4] + ob.SIDECAR_SUFFIX)


def _built_from():
    """(network path, geometry rel) the committed table records; None when the sidecar is absent."""
    try:
        built = json.loads(SIDECAR.read_text(encoding='utf-8'))
        return sup.ROOT / built['network']['path'], built['sources']['geometry']['path']
    except (OSError, ValueError, KeyError):
        return None, None


NET, GEOMETRY = _built_from()
REFERENCE = 'diagnostics/sdmpc_n31_20260924/reference_config_n31_v2.json'
RUNNER = 'diagnostics/lane_plant_20260921/scenario/lane_native.vbs'


def sha_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@unittest.skipUnless(NET is not None and NET.is_file() and (sup.ROOT / ob.DETECTOR_CSV_PATH).is_file(),
                     'pinned network or table missing')
class LoadContext(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        folder = Path(cls.tmp.name)
        net = ob.InpxNetwork(NET)
        files = {}
        for controller in net.controllers.values():
            name = controller['sig_file']
            if name:
                shutil.copyfile(NET.parent / name, folder / name)
                files[name] = sha_file(folder / name)
        (folder / 'sig_manifest.json').write_text(json.dumps({'schema': 'sdmpc31-sig-manifest/v1',
                                                              'files': dict(sorted(files.items()))}), encoding='utf-8')
        cls.paths = {'network': NET, 'geometry': sup.ROOT / GEOMETRY, 'reference_config': sup.ROOT / REFERENCE,
                     'runner_config': sup.ROOT / RUNNER, 'sig_manifest': folder / 'sig_manifest.json'}
        document = fx.manifest_v2()
        for key, path in cls.paths.items():
            document['sources'][key]['sha256'] = sha_file(path)
        document['sources']['runner_config']['path'] = RUNNER
        document['observation']['detectors'] = {'path': ob.DETECTOR_CSV_PATH,
                                                'sha256': sha_file(sup.ROOT / ob.DETECTOR_CSV_PATH)}
        cls.document = document
        cls.context = ob.load_context(document, cls.paths, manifest_sha256='d' * 64)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_context_is_valid_and_complete(self):
        ctx = self.context
        c.validate_context(ctx)
        self.assertEqual(ctx.manifest_sha256, 'd' * 64)
        self.assertEqual(ctx.network_sha256, self.document['sources']['network']['sha256'])
        self.assertEqual(len(ctx.head_groups), 105)
        self.assertEqual(sum(len(v) for v in ctx.head_groups.values()), 210)
        self.assertEqual(ctx.chain_links, {'FW_E': (74, 10699, 2, 10613, 119, 10702, 24), 'FW_W': (26, 10771, 120)})
        self.assertEqual(ctx.chain_internal_connectors, frozenset({10699, 10613, 10702, 10771}))
        self.assertEqual(sorted(ctx.offramps, key=int),
                         ['10479', '10481', '10483', '10491', '10638', '10643', '10645', '10682'])
        self.assertEqual(ctx.offramps['10643'].from_cell, 9)
        self.assertEqual(ctx.offramps['10643'].lanes, (1, 2))
        self.assertEqual({k for k, r in ctx.ramp_arrivals.items() if r.receiving}, {'RM_C10681', 'RM_C10484'})
        self.assertEqual(len(ctx.ramp_arrivals), 8)

    def test_10643_topology(self):
        self.assertEqual(self.context.lane_map_10643, {10643: {1: 1, 2: 2}, 126: {1: 1, 2: 2}, 10641: {1: 1, 2: 2},
                                                       10700: {1: 1}, 71: {1: 1, 2: 1, 3: 2}})
        self.assertEqual(self.context.route_destinations_10643, {1: 10635, 2: 10634, 3: 10642})

    def test_signal_programs_and_schedule(self):
        table = self.context.sig_table
        self.assertEqual(len(table), 42)
        self.assertEqual((table['1004'].prog_no, table['1004'].offset_s, table['1004'].cycle_s), (1, 75, 150))
        self.assertTrue(all(Path(p.path).parent == Path(self.tmp.name) for p in table.values()))
        schedule = self.context.source_schedule
        self.assertEqual([(r.start_sec, r.end_sec, r.vph) for r in schedule['FW_W']][:2],
                         [(0.0, 900.0, 4300.0), (900.0, 1800.0, 5600.0)])
        self.assertIsNone(schedule['FW_E'][-1].end_sec)

    def test_manifest_file_sha_is_required(self):
        with self.assertRaisesRegex(c.ObsContractError, 'manifest_sha256'):
            ob.load_context(self.document, self.paths)

    def test_a_changed_source_is_rejected(self):
        document = json.loads(json.dumps(self.document))
        document['sources']['geometry']['sha256'] = 'e' * 64
        with self.assertRaisesRegex(c.ObsContractError, 'geometry differs from its manifest pin'):
            ob.load_context(document, self.paths, manifest_sha256='d' * 64)

    def test_receiving_nodes_are_required(self):
        """No silent empty set: a reference config without the receiving-node ramps fails at load."""
        reference = json.loads((sup.ROOT / REFERENCE).read_text(encoding='utf-8-sig'))
        for value in (None, {}):
            with self.subTest(value=value):
                broken = json.loads(json.dumps(reference))
                if value is None:
                    broken['freeway'].pop('physical_ramp_receiving_nodes')
                else:
                    broken['freeway']['physical_ramp_receiving_nodes'] = value
                path = Path(self.tmp.name) / 'reference.json'
                path.write_text(json.dumps(broken), encoding='utf-8')
                document = json.loads(json.dumps(self.document))
                document['sources']['reference_config']['sha256'] = sha_file(path)
                with self.assertRaisesRegex(c.ObsContractError, 'physical_ramp_receiving_nodes'):
                    ob.load_context(document, dict(self.paths, reference_config=path), manifest_sha256='d' * 64)

    def test_a_table_the_sources_do_not_produce_is_rejected(self):
        runner = Path(self.tmp.name) / 'runner.vbs'
        text = (sup.ROOT / RUNNER).read_bytes().decode('latin-1')
        runner.write_bytes(text.replace('RW_FW_W_CHAIN_LINKS = "26,10771,120"',
                                        'RW_FW_W_CHAIN_LINKS = "26,10771,120,10645"').encode('latin-1'))
        paths = dict(self.paths, runner_config=runner)
        document = json.loads(json.dumps(self.document))
        document['sources']['runner_config']['sha256'] = sha_file(runner)
        with self.assertRaisesRegex(c.ObsContractError, 'Detector table assertion failed'):
            ob.load_context(document, paths, manifest_sha256='d' * 64)

    def test_a_pinned_table_that_differs_from_the_sources_is_rejected(self):
        geometry = json.loads((sup.ROOT / GEOMETRY).read_text(encoding='utf-8-sig'))
        geometry['bounds']['FW_E'][10] += 1.0                  # the through boundary of 10643 moves by 1 m
        path = Path(self.tmp.name) / 'geometry.json'
        path.write_text(json.dumps(geometry), encoding='utf-8')
        document = json.loads(json.dumps(self.document))
        document['sources']['geometry']['sha256'] = sha_file(path)
        with self.assertRaisesRegex(c.ObsContractError, 'differs from the table of the pinned sources'):
            ob.load_context(document, dict(self.paths, geometry=path), manifest_sha256='d' * 64)

    def test_sig_manifest_shapes(self):
        files = {'a.sig': 'a' * 64}
        self.assertEqual(ob.sig_manifest_files({'files': files}), files)
        self.assertEqual(ob.sig_manifest_files({'files': [{'name': 'a.sig', 'sha256': 'a' * 64}]}), files)
        for bad in ({'files': {'a.txt': 'a' * 64}}, {'files': {'x/a.sig': 'a' * 64}}, {'files': {'a.sig': 'A' * 64}},
                    {'sigs': files}):
            with self.assertRaises(c.ObsContractError):
                ob.sig_manifest_files(bad)

    def test_frozen_context_fields(self):
        self.assertTrue(dataclasses.is_dataclass(self.context))
        self.assertEqual(self.context.x10643_exit_ref, 'x10643_exit:10643')
        self.assertEqual(set(self.context.destination_refs), {'10634', '10635', '10642'})


PLANT = sup.ROOT / 'diagnostics' / 'sdmpc_n31_20260924' / 'plant_n31_v2.json'


@unittest.skipUnless(PLANT.is_file(), 'plant_n31_v2.json (WP-C) not written yet')
class RealManifest(unittest.TestCase):
    """The committed plant manifest, its pins resolved exactly as LPR read_pin does."""

    def test_load_context_from_the_plant_manifest(self):
        data = PLANT.read_bytes()
        document = json.loads(data.decode('utf-8-sig'))
        paths = {}
        for key, pin in document['sources'].items():
            path = sup.ROOT / pin['path']
            self.assertEqual(sha_file(path), pin['sha256'], key)
            paths[key] = path
        context = ob.load_context(document, paths, manifest_sha256=hashlib.sha256(data).hexdigest())
        c.validate_context(context)
        self.assertEqual(context.detector_csv_sha256, document['observation']['detectors']['sha256'])
        self.assertEqual(len(context.sig_table), 42)
        # the eight ramp meters are fixed-time SCs without a .sig file (G1 09-24, sim 150)
        self.assertEqual(context.programless_scs, frozenset(str(n) for n in range(9101, 9109)))
        self.assertTrue(all(Path(p.path).parent == sup.ROOT / 'diagnostics' / 'sdmpc_n31_20260924' / 'network'
                            for p in context.sig_table.values()))


if __name__ == '__main__':
    unittest.main()
