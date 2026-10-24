"""WP-B1 B7: the adapter patch AD_B1.patch (AD:8053-8081, install_measured_far_reservoir_rates).

The adapter is shared, so B1 ships its change as a unified diff for the
integrator. The tests follow the patch through integration (patch_state):
- pending (the patch applies): the patched function is the patch applied in
  memory and exec'd in the adapter's own namespace; the unpatched one is live;
- applied (the patch reverses): the patched function is live; the unpatched
  one is the patch reversed in memory;
- broken (neither): every test fails.
They check:
- the diff touches only its range (old-side line numbers of the patch);
- v2 (a state with the obs150 bundle): far freeway_exit_count must be the
  merged conservation count (int >= 0, provenance conservation_v2), else
  ValueError. Unpatched, None/-1 silently turned the g_fw update off;
- v1 (no obs150 key): the patched function returns exactly what the
  unpatched one returns.
The patch helpers here are shared by the other patch tests (test_capture_t1,
test_clock_unit): hunks are placed the way git apply places them without fuzz,
the exact pre-image nearest to the hunk header.
"""
from __future__ import annotations

import ast
import copy
import re
import subprocess
import sys
import types
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import contract_fixtures as fx  # noqa: E402
from contract_fixtures import c as oc  # noqa: E402

ROOT = fx.ROOT
PATCH = ROOT / 'diagnostics' / 'sdmpc_n31_20260924' / 'patches' / 'AD_B1.patch'
ADAPTER = 'evaluation/controllers/vissim_stackelberg_adapter.py'
OWNED = (8053, 8081)
FUNCTION = 'install_measured_far_reservoir_rates'
HUNK = re.compile(r'^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@')


def hunks(patch_text, *, reverse=False):
    """[(pre-image start, [(op, text)])] of a one-file unified diff (reverse: the undo diff)."""
    out = []
    swap = {'+': '-', '-': '+', ' ': ' '}
    for line in patch_text.split('\n'):
        match = HUNK.match(line)
        if match:
            out.append((int(match[3] if reverse else match[1]), []))
        elif out and line[:1] in (' ', '+', '-'):
            out[-1][1].append((swap[line[0]] if reverse else line[0], line[1:]))
    return out


def apply_patch(source_text, patch_text, *, reverse=False):
    """source_text with the diff applied (or undone): each hunk's pre-image must match exactly,
    at its header line or at the nearest offset, as git apply places it without fuzz."""
    lines = source_text.split('\n')
    for start, body in reversed(hunks(patch_text, reverse=reverse)):
        old = [text for op, text in body if op != '+']
        new = [text for op, text in body if op != '-']
        expected = start - 1 if old else start
        found = [i for i in range(len(lines) - len(old) + 1) if lines[i:i + len(old)] == old]
        assert found, 'patch context not found (hunk at %d)' % start
        index = min(found, key=lambda i: abs(i - expected))
        lines[index:index + len(old)] = new
    return '\n'.join(lines)


def git_apply_check(patch, *extra):
    result = subprocess.run(['git', 'apply', '--check', *extra, str(patch)], cwd=str(ROOT), capture_output=True)
    return result.returncode == 0


def patch_state(patch):
    """'pending' (applies), 'applied' (reverses) or 'broken'."""
    if git_apply_check(patch):
        return 'pending'
    if git_apply_check(patch, '-R'):
        return 'applied'
    return 'broken'


def function_from(source_text, module, name, filename):
    """The top-level function `name` of source_text, exec'd in a copy of module's namespace."""
    node = next(n for n in ast.parse(source_text).body if isinstance(n, ast.FunctionDef) and n.name == name)
    namespace = dict(vars(module))
    exec(compile(ast.Module(body=[node], type_ignores=[]), filename, 'exec'), namespace)
    return namespace[name]


def changed_old_lines(patch_text):
    """Old-file line numbers the diff changes (a '+' counts at the old line it follows)."""
    changed = []
    for old_start, body in hunks(patch_text):
        line = old_start - 1
        for op, _ in body:
            if op == ' ':
                line += 1
            elif op == '-':
                line += 1
                changed.append(line)
            else:
                changed.append(line)
    return changed


class FarExitPatch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from evaluation.controllers import vissim_stackelberg_adapter as adapter
        cls.adapter = adapter
        cls.patch = PATCH.read_text(encoding='utf-8')
        cls.state = patch_state(PATCH)
        if cls.state == 'broken':
            raise AssertionError('AD_B1.patch neither applies to nor reverses from the current adapter')
        source = (ROOT / ADAPTER).read_text(encoding='utf-8')
        applied = cls.state == 'applied'
        other = function_from(apply_patch(source, cls.patch, reverse=applied), adapter, FUNCTION, str(ROOT / ADAPTER))
        live = getattr(adapter, FUNCTION)
        cls.patched = staticmethod(live if applied else other)
        cls.original = staticmethod(other if applied else live)

    def test_diff_is_inside_the_owned_range_and_applies(self):
        self.assertTrue(self.patch.startswith('--- a/' + ADAPTER + '\n+++ b/' + ADAPTER + '\n'))
        changed = changed_old_lines(self.patch)
        self.assertTrue(changed and all(OWNED[0] <= n <= OWNED[1] for n in changed), changed)
        self.assertIn(self.state, ('pending', 'applied'))

    def test_v1_needs_no_new_import(self):
        # the v2 branch keys on the literal (the adapter imports no obs150 module for a v1 state)
        self.assertEqual(oc.RAW_STATE_KEY, 'obs150')
        added = [text for _, body in hunks(self.patch) for op, text in body if op == '+']
        guard = next(i for i, text in enumerate(added) if text.strip().startswith('if "obs150" in state_json:'))
        imports = [i for i, text in enumerate(added) if 'import' in text and not text.strip().startswith('#')]
        self.assertTrue(imports and all(i > guard and added[i].startswith(' ' * 8) for i in imports), added)

    def call(self, function, far, *, v2, measured=True):
        cfg = types.SimpleNamespace(mpc=types.SimpleNamespace(), network=types.SimpleNamespace(ramp_capacity_veh_h={}))
        state = {'local_observation': {} if far is None else {'far_measurement': copy.deepcopy(far)}}
        if v2:
            state[oc.RAW_STATE_KEY] = {'schema': oc.RAW_SCHEMA}
        tuning = {'rollout_far': {'measured': measured, 'measured_seed': False}}
        out = function(cfg, tuning, state, ROOT / 'no_such_previous_state.json')
        return out, vars(cfg.mpc)

    def far(self, count, provenance=oc.FREEWAY_EXIT_PROVENANCE):
        far = {'interval_sec': 150, 'link_volume_veh_h': {}, 'freeway_exit_count': count}
        if provenance is not None:
            far['freeway_exit_count_provenance'] = provenance
        return far

    def test_v2_needs_the_merged_conservation_count(self):
        for far in (None, self.far(None), self.far(-1), self.far(700.0), self.far(True), self.far(700, None),
                    self.far(700, 'vbs_chain_scan')):
            with self.subTest(far=far):
                with self.assertRaises(ValueError):
                    self.call(self.patched, far, v2=True)
                self.call(self.original, far, v2=True)       # the unpatched function stays silent
        out, mpc = self.call(self.patched, self.far(700), v2=True)
        self.assertEqual((out['far_rate_obs_fw'], out['far_measured_g_fw'], mpc['leader_mfd_far_g_fw']),
                         (700.0, 700.0, 700.0))
        self.assertEqual(self.call(self.patched, self.far(700), v2=True), self.call(self.original, self.far(700), v2=True))

    def test_v1_is_unchanged(self):
        for far in (None, self.far(None, None), self.far(-1, None), self.far(700, None), self.far(12.5, None)):
            with self.subTest(far=far):
                self.assertEqual(self.call(self.patched, far, v2=False), self.call(self.original, far, v2=False))

    def test_measured_off_is_untouched(self):
        self.assertEqual(self.call(self.patched, None, v2=True, measured=False),
                         ({'far_measured_enabled': 0.0}, {}))


if __name__ == '__main__':
    unittest.main()
