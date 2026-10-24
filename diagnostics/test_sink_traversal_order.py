"""Extract the canonical sink loop; pure fixtures only, no traffic rollout."""
import ast
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'evaluation/controllers/urban_flow_accounting.py'
sys.path.insert(0, str(ROOT/'vendor/NumSim-mine'))


def pure_sink_fixture():
    tree = ast.parse(SOURCE.read_text(encoding='utf-8-sig'))
    loops = [node for node in ast.walk(tree) if isinstance(node, ast.For)
             and isinstance(node.iter, ast.Call) and isinstance(node.iter.func, ast.Name)
             and node.iter.func.id == 'sorted' and len(node.iter.args) == 1
             and isinstance(node.iter.args[0], ast.Name) and node.iter.args[0].id == 'sink_links']
    if len(loops) != 1:
        raise AssertionError('Exactly one canonical sorted physical sink loop required')
    loop = ast.Module(body=[copy.deepcopy(loops[0])], type_ignores=[])
    ast.fix_missing_locations(loop)
    links = {'SC109_E_out', 'SC104_N_out', 'SC2003_N_out', 'SC2004_N_out'}
    observed_order, transfers, resources = [], [], []
    class Ledger:
        def record_resource_allocation(self, kind, link, available, accepted):
            resources.append((kind, link, available, accepted))
    def pending(buffer, link, step):
        observed_order.append(link)
        return 0.
    def emit(state, cfg, source, target, departed, **kw):
        transfers.append((source, target, departed, kw))
    capacities = dict.fromkeys(sorted(links), 10.)
    state = NS(urban_link_storage={link: float(i+1) for i, link in enumerate(sorted(links))},
               urban_storage_release_buffer={}, ramp_queue={})
    env = {'sink_links': links, 'defer_legsplit_sinks': False, 'ramp_split': {},
        'net': NS(urban_link_storage_veh=capacities, boundary_queue_max_veh=10.),
        'state': state, 'cfg': NS(), 'step_idx': 180,
        '_uqm': NS(_pending_in_transit=pending), 'exit_capacity_veh': 2., 'finite_exit': True,
        'resource_ledger': Ledger(), 'emit_transfer': emit, 'boundary_out_sink_veh': 0.,
        'boundary_out_ramp_blocked_veh': 0., 'boundary_out_ramp_released_veh': 0.}
    exec(compile(loop, str(SOURCE), 'exec'), env)
    return {'unordered_input': list(links), 'order': observed_order,
        'final_storage': state.urban_link_storage, 'transfers': transfers,
        'resources': resources, 'boundary_out_sink_veh': env['boundary_out_sink_veh']}


class SinkTraversalOrderTests(unittest.TestCase):
    def test_actual_sink_loop_processes_every_link_in_explicit_order(self):
        result = pure_sink_fixture()
        self.assertEqual(result['order'], sorted(result['order']))
        self.assertEqual(len(result['resources']), 8)
        self.assertEqual(len(result['transfers']), 4)
        self.assertEqual(result['boundary_out_sink_veh'], 8.)
        self.assertEqual(list(result['final_storage'].values()), [3., 4., 5., 6.])

    def test_distinct_process_hash_orders_keep_physics_and_evidence_exact(self):
        observed, bodies = [], []
        for seed in ('1', '2', '3'):
            env = os.environ.copy(); env['PYTHONHASHSEED'] = seed
            completed = subprocess.run([sys.executable, '-B', '-X', 'utf8', str(Path(__file__).resolve()), '--pure-fixture'],
                cwd=ROOT, env=env, capture_output=True, text=True, check=True, timeout=10)
            value = json.loads(completed.stdout)
            observed.append(value.pop('unordered_input'))
            bodies.append(value)
        self.assertGreater(len({tuple(x) for x in observed}), 1)
        self.assertTrue(all(value == bodies[0] for value in bodies[1:]))

    def test_archive_callback_requires_exact_manifest_and_only_one_source_edit(self):
        from diagnostics.check_fixed_candidate_response import _sink_order_original_callback, SINK_ORDER_ARCHIVE
        from evaluation.controllers import urban_flow_accounting as urban
        current = urban.urban_substep_accounted
        original, manifest = _sink_order_original_callback(urban)
        self.assertEqual(original.__name__, current.__name__)
        self.assertIsNot(original, current)
        self.assertIs(urban.urban_substep_accounted, current)
        self.assertEqual(manifest['sha256'], '3984c421ddc43e3a64d9971c64ccc9184d4663e122ed72e286c3b4b0482ddd28')
        with tempfile.TemporaryDirectory() as temporary:
            archived = Path(temporary)/'before.txt'
            archived.write_bytes(SINK_ORDER_ARCHIVE.read_bytes()+b'\n')
            archived.with_suffix('.sha256.json').write_bytes(SINK_ORDER_ARCHIVE.with_suffix('.sha256.json').read_bytes())
            with self.assertRaisesRegex(Exception, 'manifest'):
                _sink_order_original_callback(urban, archived)

    def test_exact_physical_values_and_record_multiplicity_not_just_totals(self):
        from diagnostics.check_fixed_candidate_response import _sink_order_graph_comparison as compare
        from src.models.state import ControlAction
        a = {'states': [{'density': [1., 2.], 'cohorts': Counter(inside=1.)}],
             'endpoint': {'objective': 3., 'control': ControlAction(vsl={'FW_E': 100.})}, 'response': {
                 'residence': [{'start': 0., 'stock': 1.}],
                 'transfers': [{'source': 'A', 'start': 0., 'vehicles': 1.}, {'source': 'B', 'start': 0., 'vehicles': 2.}],
                 'resource_allocations': [{'resource': 'A', 'cap': 3.}, {'resource': 'B', 'cap': 4.}]}}
        b = copy.deepcopy(a)
        b['response']['transfers'].reverse(); b['response']['resource_allocations'].reverse()
        result = compare(a, b)
        self.assertTrue(result['passed'])
        self.assertFalse(result['record_permutations']['transfers']['original_sequence_equal'])
        for kind in ('clock', 'multiplicity', 'flow', 'state', 'ieee-sign', 'control'):
            bad = copy.deepcopy(b)
            if kind == 'clock': bad['response']['transfers'][0]['start'] = 5.
            elif kind == 'multiplicity': bad['response']['transfers'].append(copy.deepcopy(bad['response']['transfers'][0]))
            elif kind == 'flow': bad['response']['transfers'][0]['vehicles'] += 1.
            elif kind == 'state': bad['states'][0]['density'].reverse()
            elif kind == 'control': bad['endpoint']['control'].vsl['FW_E'] = 90.
            else: bad['response']['residence'][0]['start'] = -0.
            self.assertFalse(compare(a, bad)['passed'], kind)

    def test_actual_callback_is_restored_when_mock_endpoint_fails(self):
        from diagnostics.check_fixed_candidate_response import compare_sink_order
        from evaluation.controllers import urban_flow_accounting as urban
        from src.controllers import rollout_endpoint
        original = urban.urban_substep_accounted
        report = {}
        with tempfile.TemporaryDirectory() as temporary, patch.object(
                rollout_endpoint, 'evaluate_price_point', side_effect=RuntimeError('synthetic failure')):
            with self.assertRaisesRegex(RuntimeError, 'synthetic failure'):
                compare_sink_order(NS(), NS(), (), NS(), report, Path(temporary)/'out.json')
        self.assertIs(urban.urban_substep_accounted, original)
        self.assertTrue(report['sink_order_comparison']['callback_restored'])


if __name__ == '__main__':
    if '--pure-fixture' in sys.argv:
        print(json.dumps(pure_sink_fixture()))
    else:
        unittest.main()
