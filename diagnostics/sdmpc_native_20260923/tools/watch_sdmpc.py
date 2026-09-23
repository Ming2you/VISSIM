r"""One line per SDMPC decision, as the native run produces them.

For every new decisions/action_<sec>.json this prints and appends to a log:
    sim_sec, decision wall, how many ramp meters are BELOW their table ceiling (i.e.
    actually restricting), how many VSL entries are below 120, the predicted objective
    and its reduction over the held command.

The run's action JSONs are ~58 MB, so reading them here spares the user from opening
them one by one. The log is the resume point: restarting the watcher never repeats a
decision it already reported. Exits when the launcher writes its EXIT line.

Usage: watch_sdmpc.py <run_dir> <launch_log> <summary_log>
"""
import glob
import io
import json
import os
import re
import sys
import time

CEILING = {1: 1512.0, 2: 3024.0}   # rule_policy / measured_table ceilings by lane count
TWO_LANE = {'RM_C10482', 'RM_C10681'}
STALL_SEC = 20 * 60   # a decision takes ~8.5 min and warmup steps ~5-12 min


def seen(summary):
    if not os.path.exists(summary):
        return set()
    return {int(m.group(1)) for m in re.finditer(r'^sim_sec=(\d+)', io.open(summary, encoding='utf-8').read(), re.M)}


def describe(path):
    a = json.load(io.open(path, encoding='utf-8'))
    md = a.get('metadata', {})
    meters = a.get('ramp_metering', {})
    restricted = {k: v for k, v in meters.items()
                  if v < CEILING[2 if k in TWO_LANE else 1] - 1e-6}
    vsl = a.get('vsl', {})
    limited = {k: v for k, v in vsl.items() if v < 120.0 - 1e-6}
    return md, restricted, limited, a


def objective(run_dir, sec):
    """sdmpc_completed carries objective and held_objective; warmup decisions have none."""
    p = os.path.join(run_dir, 'action_%06d.joint.progress.jsonl' % sec)
    if not os.path.exists(p):
        return None, None
    for line in reversed(io.open(p, encoding='utf-8').read().splitlines()):
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if (r.get('stage') or r.get('event')) == 'sdmpc_completed':
            return r.get('objective'), r.get('held_objective')
    return None, None


def main():
    run, launch_log, summary = sys.argv[1:4]
    decisions = glob.glob(os.path.join(run, 'decisions_*'))
    done = seen(summary)
    failed, stalled = set(), False
    while True:
        dirs = glob.glob(os.path.join(run, 'decisions_*'))
        if dirs:
            d = dirs[0]
            for path in sorted(glob.glob(os.path.join(d, 'action_[0-9]*.json'))):
                m = re.search(r'action_(\d+)\.json$', path)
                if not m:
                    continue
                sec = int(m.group(1))
                if sec in done:
                    continue
                # Wait until the writer is finished: the budget receipt is written last.
                if not os.path.exists(path[:-5] + '.decision_budget.json') and sec >= 900:
                    continue
                try:
                    md, restricted, limited, _ = describe(path)
                except (ValueError, OSError):
                    continue
                obj, held = objective(d, sec)
                wall = md.get('decision_wall_sec')
                parts = ['sim_sec=%d' % sec,
                         'wall=%s' % ('%.0f' % wall if isinstance(wall, (int, float)) else '?'),
                         'meters_restricting=%d/8' % len(restricted),
                         'vsl_below_120=%d' % len(limited)]
                if obj is not None:
                    parts.append('obj=%.3f' % obj)
                    if held is not None:
                        parts.append('gain=%.3f' % (held - obj))
                if restricted:
                    parts.append('meters{%s}' % ','.join('%s:%.0f' % (k[5:], v) for k, v in sorted(restricted.items())))
                if limited:
                    parts.append('vsl_min=%.0f' % min(limited.values()))
                line = '  '.join(parts)
                io.open(summary, 'a', encoding='utf-8').write(line + '\n')
                print(line, flush=True)
                done.add(sec)
            # A failed decision writes its report (<1 MB, "completed": false) and no
            # action JSON, and the adapter can then hang instead of exiting (sdmpc_lp_9000,
            # t=1050). Report it once; the launcher would only notice at StallSec.
            for jp in glob.glob(os.path.join(d, 'action_[0-9]*.joint.json')) if dirs else ():
                sec = int(re.search(r'action_(\d+)\.joint\.json$', jp).group(1))
                if sec in done or sec in failed or os.path.exists(jp[:-len('.joint.json')] + '.json'):
                    continue
                if time.time() - os.path.getmtime(jp) < 60 or os.path.getsize(jp) > 5e6:
                    continue
                try:
                    rep = json.load(io.open(jp, encoding='utf-8'))
                except (ValueError, OSError):
                    continue
                if rep.get('completed') is False:
                    msg = str((rep.get('error') or {}).get('message', ''))
                    line = 'DECISION FAILED sim_sec=%d  %s' % (sec, msg.strip().splitlines()[-1][:300] if msg.strip() else '?')
                    io.open(summary, 'a', encoding='utf-8').write(line + '\n')
                    print(line, flush=True)
                    failed.add(sec)
            newest = max((os.path.getmtime(p) for p in glob.glob(os.path.join(d, '*'))), default=None) if dirs else None
            if newest and time.time() - newest > STALL_SEC and not stalled:
                print('STALL no decision file written for %d min' % ((time.time() - newest) // 60), flush=True)
                stalled = True
            elif newest and time.time() - newest <= STALL_SEC:
                stalled = False
        if os.path.exists(launch_log) and re.search(r'^EXIT ', io.open(launch_log, encoding='utf-8', errors='replace').read(), re.M):
            tail = io.open(launch_log, encoding='utf-8', errors='replace').read().splitlines()[-2:]
            print('RUN ENDED  ' + ' | '.join(tail), flush=True)
            return 0
        time.sleep(30)


if __name__ == '__main__':
    raise SystemExit(main())
