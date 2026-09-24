"""WP-B2 T10 (plan B7): every v1 local_observation key is produced by v2 or retired with a reason.

Source of the v1 key set: the saved run sdmpc_lp_9000c, state_000900.json. v2
produces a key when the runner writes it unconditionally (VBS WriteStateJson
local_observation block) or merge_into_state fills it. A retired key names its
consumer and why it is safe to drop: the VBS writes it only under
QueueWindowEnabled() (RW_QUEUE_WINDOW=1), which obs150 mode sets to 0, and the
adapter reads it only when urban.queue.window_stat is mean|max, which is "" in
the n31 tuning.
"""
from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_lane_support as sup  # noqa: E402
from test_lane_support import c, fx  # noqa: E402

from evaluation.controllers import obs150_observation as ob  # noqa: E402

VBS = sup.ROOT / 'scripts' / 'run_real_world_stackelberg_controller.vbs'
OBS1 = sup.ROOT / 'diagnostics' / 'sdmpc_pfo_caps_20260922' / 'config_candidate_obs1.json'
N31_CONFIG = sup.ROOT / 'diagnostics' / 'sdmpc_n31_20260924' / 'config_n31_v2.json'
ADAPTER = sup.ROOT / 'evaluation' / 'controllers' / 'vissim_stackelberg_adapter.py'


def local_block():
    """(unconditional keys, {guard: keys}) of the local_observation block of WriteStateJson."""
    text = VBS.read_text(encoding='utf-8', errors='replace')
    start = text.index('ts.WriteLine "  ""local_observation"": {"')
    end = text.index('ts.WriteLine "  },"', start)
    plain, guarded, guard = [], {}, None
    for line in text[start:end].splitlines()[1:]:
        stripped = line.strip()
        inline = re.match(r'If (.+?) Then ts\.WriteLine "\s*""(\w+)""', stripped)
        if inline:
            guarded.setdefault(inline[1], []).append(inline[2])
            continue
        block = re.match(r'If (.+?) Then$', stripped)
        if block:
            guard = block[1]
            continue
        if stripped == 'End If':
            guard = None
            continue
        key = re.match(r'ts\.WriteLine "\s*""(\w+)""', stripped)
        if key:
            (guarded.setdefault(guard, []) if guard else plain).append(key[1])
    return plain, guarded


def load_state(path):
    data = path.read_bytes()
    return json.loads(data.decode('utf-16') if data[:2] in (b'\xff\xfe', b'\xfe\xff') else data.decode('utf-8-sig'))


class Parity(unittest.TestCase):
    def test_lists_are_disjoint_and_complete(self):
        retired = [k for k, _, _ in ob.RETIRED_V2]
        self.assertFalse(set(ob.PRODUCED_V2) & set(retired))
        self.assertEqual(len(set(ob.PRODUCED_V2)), len(ob.PRODUCED_V2))
        for key, consumer, reason in ob.RETIRED_V2 + ob.NARROWED_V2:
            self.assertTrue(consumer and reason, key)
        self.assertTrue({k for k, _, _ in ob.NARROWED_V2} <= set(ob.PRODUCED_V2))

    @unittest.skipUnless(sup.OLD_STATE_900.is_file(), 'saved v1 run sdmpc_lp_9000c missing')
    def test_every_v1_key_is_produced_or_retired(self):
        old = set(load_state(sup.OLD_STATE_900)['local_observation'])
        covered = set(ob.PRODUCED_V2) | {k for k, _, _ in ob.RETIRED_V2}
        self.assertEqual(old - covered, set())
        self.assertEqual({k for k, _, _ in ob.RETIRED_V2} - old, set(), 'retire only keys v1 actually wrote')

    def test_runner_keys_are_written_unconditionally(self):
        plain, guarded = local_block()
        self.assertEqual(set(plain), set(ob.RUNNER_V2_KEYS))
        self.assertEqual(set(guarded.get('QueueWindowEnabled()', [])),
                         {k for k, _, _ in ob.RETIRED_V2} | {'link_departures_window'})
        self.assertEqual(guarded.get('obsEnabled'), ['signal_observation_window'])

    def test_retired_writers_and_consumers_are_off_in_obs150_mode(self):
        env = c.expected_runner_env(fx.manifest_v2(), 'C:\\x.csv')
        self.assertEqual(env['RW_QUEUE_WINDOW'], '0')            # QueueWindowEnabled() is false
        self.assertEqual(env['RW_SIGNAL_OBSERVATION'], '0')      # obsEnabled is false: merge fills the window
        for path in (OBS1, N31_CONFIG):
            if path.is_file():
                config = json.loads(path.read_text(encoding='utf-8-sig'))
                self.assertEqual(config['urban']['queue'].get('window_stat', ''), '', path.name)
        adapter = ADAPTER.read_text(encoding='utf-8')
        for key, _, _ in ob.RETIRED_V2:
            for match in re.finditer(re.escape(key), adapter):
                window = adapter[max(0, match.start() - 1500):match.start()]
                self.assertIn('queue_window_stat', window, f'{key} read outside the window_stat gate')

    def test_merge_fills_exactly_the_merged_keys(self):
        before, after = fx.merged(900)
        changed = {k for k in after['local_observation']
                   if before['local_observation'].get(k) != after['local_observation'][k]}
        self.assertEqual(changed, set(ob.MERGED_V2_KEYS) | {'far_measurement'})


if __name__ == '__main__':
    unittest.main()
