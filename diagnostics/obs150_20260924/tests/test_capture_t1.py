"""WP-B1 review fix 1: the t=1 decision with a passage counted and no .mer row yet.

The operational source station sits at 1.0 m. In the probe run (same network,
seed 31) the first vehicle crossed 40 m at 3.21 s, and link 26 takes 2.66-3.90 s
from 1 m to 40 m (gt_veh.csv, 157 vehicles), so Vehs of a 1.0 m station can be
1 at t=1. At t=1 the probe .mer was still inside its header. Two rules make
that decision exact instead of an ObsLagError:

- capture (obs150_capture, CONTRACT 4.4): t=1 consumes the header only. Every
  row of window 1, (0, 1] included, lands in the T=150 chunk, which
  assign_window needs whole ("rows of this interval are missing" otherwise);
- lag rule (OC lag_ok): (0, 1] is itself (T-1, T], so a t=1 tail needs no file
  evidence. OC belongs to WP-0, so the change ships as patches/OC_B1.patch
  (OC + CONTRACT.md) for the integrator.

While OC_B1.patch is pending these tests run the patched lag_ok (applied in
memory to the current OC) through the live assign_window; once it is applied
they run the live OC. A patch that neither applies nor reverses fails here.
"""
from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import contract_fixtures as fx  # noqa: E402
from contract_fixtures import c as oc  # noqa: E402
import test_capture_probe as probe  # noqa: E402
import test_capture_unit as unit  # noqa: E402
from test_head_b7_far_patch import apply_patch, changed_old_lines, function_from  # noqa: E402
from test_head_b7_far_patch import patch_state as b7_patch_state  # noqa: E402

ROOT = fx.ROOT
PATCHES = ROOT / 'diagnostics' / 'sdmpc_n31_20260924' / 'patches'
PATCH = PATCHES / 'OC_B1.patch'
OC_FILE = 'evaluation/controllers/obs150_contract.py'
CONTRACT_FILE = 'diagnostics/sdmpc_n31_20260924/CONTRACT.md'


def patch_state(patch=PATCH):
    """'pending' (applies), 'applied' (reverses) or 'broken'."""
    return b7_patch_state(patch)


def file_sections(patch_text):
    """{path: its part of a multi-file unified diff}."""
    sections, current = {}, None
    lines = patch_text.split('\n')
    for i, line in enumerate(lines):
        # a file header is '--- a/<path>' directly followed by '+++ b/<path>'
        if line.startswith('--- a/') and i + 1 < len(lines) and lines[i + 1].startswith('+++ b/'):
            current = line[len('--- a/'):]
            sections[current] = []
        if current is not None:
            sections[current].append(line)
    return {path: '\n'.join(body) + '\n' for path, body in sections.items()}


def function_lines(source, name):
    node = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == name)
    return node.lineno, node.end_lineno


def patched_function(patch, relative, module, name):
    """Function `name` of the file `relative` (imported as `module`) as the integrator will have it.

    The live function once the patch is applied, else the patch applied in memory
    and the one function executed in a copy of the module namespace.
    """
    state = patch_state(patch)
    if state == 'applied':
        return getattr(module, name)
    assert state == 'pending', f'{patch.name} neither applies nor reverses'
    source = (ROOT / relative).read_text(encoding='utf-8')
    patched = apply_patch(source, file_sections(patch.read_text(encoding='utf-8'))[relative])
    return function_from(patched, module, name, str(ROOT / relative))


def patched_lag_ok():
    """The lag_ok the integrator will have: the live one once applied, else the patch applied in memory."""
    return patched_function(PATCH, OC_FILE, oc, 'lag_ok')


def t1_obs(counts, mer):
    """The raw fields assign_window reads at t=1: C = the open-interval Vehs, records from the capture."""
    return {'sim_sec': 1, 'detectors': dict(counts), 'detectors_cum': dict(counts), 'mer': mer}


class OcPatch(unittest.TestCase):
    def test_patch_is_lag_ok_and_the_contract_text_only(self):
        state = patch_state()
        self.assertIn(state, ('pending', 'applied'))
        sections = file_sections(PATCH.read_text(encoding='utf-8'))
        self.assertEqual(set(sections), {OC_FILE, CONTRACT_FILE})
        if state == 'pending':
            first, last = function_lines((ROOT / OC_FILE).read_text(encoding='utf-8'), 'lag_ok')
            changed = changed_old_lines(sections[OC_FILE])
            self.assertTrue(changed and all(first <= n <= last for n in changed), (changed, first, last))

    def test_rule_is_unchanged_after_t1(self):
        lag_ok = patched_lag_ok()
        for end in (150, 300, 9000):
            for max_t in (None, end - 1.0, end - 0.995, end - 0.994, end - 0.5, float(end)):
                for tail in (0, 1, 3):
                    reference = tail == 0 or (max_t is not None and max_t > end - 1 + 0.005 + 1e-9)
                    with self.subTest(end=end, max_t=max_t, tail=tail):
                        self.assertEqual(lag_ok(max_t, end, tail), reference)

    def test_t1_tail_without_a_row(self):
        mer = {'records_cum_by_dcp': {'960001': 0, '960002': 0}, 'max_t_any': None}
        obs = t1_obs({'960001': 1, '960002': 0}, mer)
        if patch_state() == 'pending':
            with self.assertRaises(oc.ObsLagError):          # the review finding, on the unpatched OC
                oc.assign_window(obs, [])
        with mock.patch.object(oc, 'lag_ok', patched_lag_ok()):
            assignment = oc.assign_window(obs, [])
        self.assertEqual((assignment.start_s, assignment.end_s, assignment.k), (0, 1, None))
        self.assertEqual((assignment.sum_tail, assignment.tails, assignment.lag_ok), (1, {960001: 1, 960002: 0}, True))


class CaptureT1HeaderOnly(unittest.TestCase):
    """The capture side, on synthetic files (test_capture_unit helpers)."""

    def setUp(self):
        self.ws = unit.Workspace()
        self.addCleanup(self.ws.close)

    def test_t1_reads_no_row_and_window1_is_whole_at_150(self):
        head = unit.header(unit.table())
        early = unit.row(960002, 0.52, None, 1) + unit.row(910001, 0.61, None, 2) + unit.row(960002, None, 0.95, 1)
        meta1 = self.ws.capture(1, head + early + unit.row(960002, 1.3, None, 3)[:25], b'')
        self.assertEqual(self.ws.chunk(meta1), [])
        self.assertEqual((meta1['mer']['byte_start'], meta1['mer']['byte_end'], meta1['mer']['max_t_any']),
                         (0, len(head), None))
        self.assertEqual(meta1['mer']['records_cum_by_dcp'], {'960001': 0, '960002': 0, '960003': 0})
        with mock.patch.object(oc, 'lag_ok', patched_lag_ok()):
            assignment = oc.assign_window(t1_obs({'960001': 0, '960002': 1, '960003': 0}, meta1['mer']), [])
        self.assertEqual(assignment.tails[960002], 1)
        later = unit.row(960002, 1.3, None, 3) + unit.row(960001, 70.0, None, 4) + unit.row(960002, 149.5, None, 5)
        meta150 = self.ws.capture(150, head + early + later, b'')
        chunk = self.ws.chunk(meta150)
        self.assertEqual([(r.seq, r.dcp, r.t_entry, r.t_exit, r.ordinal) for r in chunk],
                         [(0, 960002, 0.52, None, 1), (2, 960002, None, 0.95, None), (3, 960002, 1.3, None, 2),
                          (4, 960001, 70.0, None, 1), (5, 960002, 149.5, None, 3)])
        self.assertEqual((meta150['mer']['byte_start'], meta150['mer']['max_t_any']), (len(head), 149.5))
        counts = {'960001': 1, '960002': 3, '960003': 0}
        obs = {'sim_sec': 150, 'detectors': counts, 'detectors_cum': dict(counts), 'mer': meta150['mer']}
        assignment = oc.assign_window(obs, chunk)
        self.assertEqual([r.t_entry for r in assignment.entries[960002]], [0.52, 1.3, 149.5])
        self.assertEqual(assignment.sum_tail, 0)

    def test_the_old_t1_cursor_would_have_split_window1(self):
        """What the review reproduced: a t=1 chunk holding ordinal 1 leaves window 1 short at T=150."""
        early = [oc.MerRow(5, 960001, 0.5, None, 7, 100, 30.0, 4.5, 1)]
        late = [oc.MerRow(9, 960001, 40.0, None, 8, 100, 30.0, 4.5, 2)]
        mer = {'records_cum_by_dcp': {'960001': 2}, 'max_t_any': 149.9}
        obs = {'sim_sec': 150, 'detectors': {'960001': 2}, 'detectors_cum': {'960001': 2}, 'mer': mer}
        with self.assertRaises(oc.ObsContractError):
            oc.assign_window(obs, late)
        self.assertEqual(len(oc.assign_window(obs, early + late).entries[960001]), 2)


@unittest.skipUnless(probe.HAVE_PROBE, probe.SKIP_REASON)
class ProbeT1(unittest.TestCase):
    """The probe files at t=1: the mid-header t1 copy, and a t=1 file that already holds rows (the t37 copy)."""

    def source_key(self):
        """The first lane of the probe's source station (one point per lane)."""
        return str(min(r.dcm_no for r in probe.probe_table() if r.role == 'source'))

    def test_t1_with_the_operational_count_passes(self):
        _, metas = probe.probe_chain()
        mer = metas[1]['mer']
        self.assertEqual((mer['max_t_any'], set(mer['records_cum_by_dcp'].values())), (None, {0}))
        counts = {str(r.dcm_no): 0 for r in probe.probe_table()}
        counts[self.source_key()] = 1                      # a 1.0 m station has counted the first vehicle
        with mock.patch.object(oc, 'lag_ok', patched_lag_ok()):
            assignment = oc.assign_window(t1_obs(counts, mer), [])
        self.assertEqual(assignment.sum_tail, 1)

    def test_t1_file_with_rows_changes_nothing_downstream(self):
        root = probe.new_workspace('obs150_b1_t1rows_')
        data = probe.snapshot_bytes('t37')
        meta1 = probe.capture_stop(root, 1, data, probe.err_prefix_at(1), probe.probe_table())
        header = probe.cap._mer_header(probe._BytesFile(data), len(data))
        self.assertIsNotNone(header['data_start'])
        self.assertGreater(len(data), header['data_start'])          # the file holds rows at this t=1
        self.assertEqual((meta1['mer']['byte_end'], meta1['mer']['max_t_any']), (header['data_start'], None))
        self.assertEqual(probe.chain_chunk(root, meta1), [])
        base_root, base = probe.probe_chain()
        closed, _ = probe.results()
        for t in probe.DECISION_STOPS[1:4]:
            meta = probe.capture_stop(root, t, probe.snapshot_bytes(f't{t}'), probe.err_prefix_at(t), probe.probe_table())
            chunk = probe.chain_chunk(root, meta)
            with self.subTest(t=t):
                self.assertEqual(chunk, probe.chain_chunk(base_root, base[t]))
                self.assertEqual(meta['mer']['records_cum_by_dcp'], base[t]['mer']['records_cum_by_dcp'])
                assignment = oc.assign_window(probe.bundle_obs(t, meta), chunk)
                for r in probe.probe_table():
                    self.assertEqual(assignment.tails[r.dcp_no] + len(assignment.entries[r.dcp_no]),
                                     closed[t][str(r.dcm_no)])


if __name__ == '__main__':
    unittest.main()
