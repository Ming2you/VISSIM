r"""One line per SDMPC-31 decision of an obs150 run (plan D3; sdmpc_native_20260923/tools/watch_sdmpc.py).

    watch_sdmpc.py <run_dir | decisions_dir> <launch_log> <summary_log> [--stall-min 40] [--once]

For every finished decisions/action_<T>.json it prints and appends to <summary_log>:

    sim_sec=900  wall=505  meters_restricting=2/8  vsl_below_max=0(110)  obj=393.916  gain=1.619
      obs150 lag_ok=True sum_tail=3 max_t=899.93 amb=0 removals=1 dets=290/4411 exit=212
             cons=0 lane_inexact=0 edie_max=0.04 err_lag=0.4

- VSL reference is max(vsl_set) of the run's effective tuning (provenance files.tuning), not a
  fixed 120: the v2 config allows [50, 60, ..., 110] (10 km/h steps).
- A meter restricts when its rate is below the rate the latest no-control (warmup) decision wrote
  for it (no-control writes every meter open); before any warmup decision, the v1 table ceilings
  1512/3024 by lane count.
- The obs150 part reads the state's obs150 raw block and obs150/derived_<T>.json (the audit
  file the decision wrote): lag verdict, sum of tails, file max time, boundary-ambiguous count,
  removals in the window, detector rows / summed Vehs, freeway_exit_count, the conservation
  residual, boundaries whose lane terms are not exact, max |Edie residual|, and T - (.err max sim
  second).
- cons (conservation residual, exact 0 when every boundary term is right): the freeway region is
  the chain links (RW_FW_*_CHAIN_LINKS of the run's runner config, internal connectors included)
  plus the on-ramp connectors downstream of their arrival station x = connector start; NEW-7 says
  nothing else enters or leaves it. cons = N(frame_T) - N(frame_{T-150})
  - [sum cross(source:*) + sum cross(ramp_arrival:*) - sum cross(off_entry:*) - sum cross(chain_end:*)
  - window removals on the region], N counting frame rows on region links at Pos >= 0 (the
  identity's q >= x rule; a just-inserted vehicle at Pos < 0 has not entered).
- A decision is finished when its .decision_budget.json exists (written last). A failed decision
  is reported once: from a completed=false joint report, or from the runner's
  'ERROR=DECISION_EXIT_NONZERO sim_sec=' line (an obs150 lag/contract failure stops the adapter
  before any joint report exists).
- Progress is the newest mtime in the decisions folder, including *.joint.progress.jsonl; a STALL
  line is printed once per quiet period longer than --stall-min.
- The summary log is the resume point: a restarted watcher never repeats a decision.
- Ends when <launch_log> has run_sdmpc_n31.ps1's 'EXIT ' line; prints the runner's
  DECISIONS_OK/DECISIONS_FAILED summary when present.
"""
from __future__ import annotations

import argparse
import glob
import io
import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from n31_common import ToolError, effective_vsl_max, load_effective_tuning, oc, vbs_constants  # noqa: E402

CEILING = {1: 1512.0, 2: 3024.0}   # rule_policy / measured_table meter ceilings by lane count (watch_sdmpc v1)
TWO_LANE = {'RM_C10482', 'RM_C10681'}
DEFAULT_CONTROL_START = 900
FAILED_RE = re.compile(r'ERROR=DECISION_EXIT_NONZERO sim_sec=(\d+)')
# run_sdmpc_n31.ps1's own last line '<yyyy-MM-dd HH:mm:ss>  EXIT <Name> code=<n>'; relayed watchdog lines
# carry a 'WD ' prefix after the stamp and never match.
LAUNCH_EXIT_RE = re.compile(r'^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d  EXIT \S+ code=-?\d+\s*$', re.M)


def seen(summary):
    if not os.path.exists(summary):
        return set(), set()
    text = io.open(summary, encoding='utf-8').read()
    done = {int(m.group(1)) for m in re.finditer(r'^sim_sec=(\d+)', text, re.M)}
    failed = {int(m.group(1)) for m in re.finditer(r'^DECISION FAILED sim_sec=(\d+)', text, re.M)}
    return done, failed


def read_json(path):
    with io.open(path, encoding='utf-8-sig') as handle:
        return json.load(handle)


def objective(decisions, sec):
    """sdmpc_completed carries objective and held_objective; warmup decisions have none."""
    p = os.path.join(decisions, 'action_%06d.joint.progress.jsonl' % sec)
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


def describe_action(path, vsl_max, ceilings=None):
    """ceilings: per-meter rates of the latest no-control (warmup) decision, which writes every meter open."""
    a = read_json(path)
    md = a.get('metadata', {})
    meters = a.get('ramp_metering', {})
    ceiling = lambda k: (ceilings or {}).get(k, CEILING[2 if k in TWO_LANE else 1])
    restricted = {k: v for k, v in meters.items() if v < ceiling(k) - 1e-6}
    limited = {k: v for k, v in a.get('vsl', {}).items() if v < vsl_max - 1e-6}
    return md, restricted, limited, len(meters)


_RAMP_LINKS = {}      # detector CSV sha -> frozenset of on-ramp connector links (role ramp_arrival)


def ramp_arrival_links(raw):
    config = raw['detector_config']
    if config['sha256'] not in _RAMP_LINKS:
        rows, _ = oc.read_detector_csv(config['path'], config['sha256'])
        _RAMP_LINKS[config['sha256']] = frozenset(r.link for r in rows if r.role == 'ramp_arrival')
    return _RAMP_LINKS[config['sha256']]


def conservation_residual(raw, derived, chain_links):
    """cons of the module docstring; raises (caller prints '-') when an input is missing."""
    ramps = ramp_arrival_links(raw)
    region = set(chain_links) | set(ramps)
    frames = raw['frames']
    start = raw['window']['start_s'] if raw.get('window') else 0

    def count(pin, time_s):
        frame = oc.load_frame(oc.resolve(raw, pin['path']), pin['sha256'], time_s)
        return sum(1 for row in frame['vehicles'] if int(row[1]) in region and float(row[3]) >= 0)

    stock = count(frames['current'], raw['sim_sec']) - count(frames['previous'], start)
    crossed = lambda prefix: sum(v['cross'] for k, v in derived['boundaries'].items() if k.startswith(prefix))
    removed = sum(1 for r in derived['removals']['rows'] if r.get('on_chain') or int(r['link']) in ramps)
    return stock - (crossed('source:') + crossed('ramp_arrival:') - crossed('off_entry:') - crossed('chain_end:')
                    - removed)


def describe_obs150(decisions, sec, chain_links=None):
    """The obs150 part of the line, from the state's raw block and the decision's derived file."""
    state_path = os.path.join(decisions, 'state_%06d.json' % sec)
    if not os.path.exists(state_path):
        return 'obs150 state=missing'
    raw = read_json(state_path).get(oc.RAW_STATE_KEY)
    if not isinstance(raw, dict):
        return 'obs150 state=not_v2'
    detectors = raw.get('detectors', {})
    err_max = raw.get('err', {}).get('max_sim_sec')
    parts = ['dets=%d/%d' % (len(detectors), sum(v for v in detectors.values() if isinstance(v, int))),
             'err_lag=%s' % ('%.1f' % (sec - err_max) if isinstance(err_max, (int, float)) else '-')]
    derived_path = os.path.join(decisions, *oc.derived_path(sec).split('/'))
    if not os.path.exists(derived_path):
        return 'obs150 derived=missing ' + ' '.join(parts)
    d = read_json(derived_path)
    lag = d.get('lag', {})
    boundaries = d.get('boundaries', {})
    edie = [abs(v) for v in d.get('edie_residuals', {}).values() if isinstance(v, (int, float))]
    head = ['lag_ok=%s' % lag.get('ok'), 'sum_tail=%s' % lag.get('sum_tail'),
            'max_t=%s' % lag.get('max_t_any'), 'amb=%s' % d.get('boundary_ambiguous'),
            'removals=%s' % d.get('removals', {}).get('window_total')]
    cons = '-'
    if chain_links:
        try:
            cons = '%d' % conservation_residual(raw, d, chain_links)
        except (ValueError, KeyError, TypeError, OSError):
            cons = 'unreadable'
    tail = ['exit=%s' % d.get('freeway_exit_count', {}).get('value'), 'cons=%s' % cons,
            'lane_inexact=%d' % sum(1 for b in boundaries.values() if b.get('lane_exact') is False),
            'edie_max=%s' % ('%.3g' % max(edie) if edie else '-')]
    return 'obs150 ' + ' '.join(head + parts[:1] + tail + parts[1:])


def chain_links_of(provenance):
    """Chain links (with internal connectors) of both roads from the run's runner config."""
    constants = vbs_constants(provenance['files']['generated_vbs_config']['path'])
    return frozenset(int(x) for road in ('E', 'W') for x in constants[f'RW_FW_{road}_CHAIN_LINKS'].split(',') if x)


def decision_line(decisions, sec, vsl_max, ceilings=None, chain_links=None):
    md, restricted, limited, meters = describe_action(os.path.join(decisions, 'action_%06d.json' % sec), vsl_max,
                                                      ceilings)
    obj, held = objective(decisions, sec)
    wall = md.get('decision_wall_sec')
    parts = ['sim_sec=%d' % sec,
             'wall=%s' % ('%.0f' % wall if isinstance(wall, (int, float)) else '?'),
             'meters_restricting=%d/%d' % (len(restricted), meters),
             'vsl_below_max=%d(%g)' % (len(limited), vsl_max)]
    if obj is not None:
        parts.append('obj=%.3f' % obj)
        if held is not None:
            parts.append('gain=%.3f' % (held - obj))
    if restricted:
        parts.append('meters{%s}' % ','.join('%s:%.0f' % (k.replace('RM_C', ''), v) for k, v in sorted(restricted.items())))
    if limited:
        parts.append('vsl_min=%.0f' % min(limited.values()))
    return '  '.join(parts) + '\n    ' + describe_obs150(decisions, sec, chain_links)


class Watch:
    def __init__(self, target, launch_log, summary, stall_min):
        self.target, self.launch_log, self.summary = Path(target), launch_log, summary
        self.stall_sec = stall_min * 60
        self.done, self.failed = seen(summary)
        self.stalled = False
        self.decisions = self.run_dir = self.name = None
        self.vsl_max = None
        self.control_start = DEFAULT_CONTROL_START
        self.ceilings = None
        self.chain_links = None

    def emit(self, line):
        with io.open(self.summary, 'a', encoding='utf-8') as handle:
            handle.write(line + '\n')
        print(line, flush=True)

    def locate(self):
        if self.decisions is None:
            if self.target.name.startswith('decisions_') and self.target.is_dir():
                self.decisions = self.target
            else:
                found = sorted(p for p in self.target.glob('decisions_*') if p.is_dir())
                if len(found) == 1:
                    self.decisions = found[0]
            if self.decisions is not None:
                self.run_dir, self.name = self.decisions.parent, self.decisions.name[len('decisions_'):]
        if self.decisions is not None and self.vsl_max is None:
            prov = self.run_dir / f'run_provenance_{self.name}.json'
            if prov.is_file():
                provenance = read_json(prov)
                self.vsl_max = effective_vsl_max(load_effective_tuning(provenance['files']['tuning']['path'])[0])
                try:
                    self.chain_links = chain_links_of(provenance)
                except (KeyError, OSError, ValueError):
                    self.chain_links = None            # the line then prints cons=-
                plan = self.run_dir / 'launch_plan.json'
                if plan.is_file():
                    self.control_start = int(read_json(plan)['control_start_sec'])
        return self.decisions is not None and self.vsl_max is not None

    def scan(self):
        d = str(self.decisions)
        if self.ceilings is None:                     # also after a restart that skips reported warmups
            warm = [p for p in sorted(glob.glob(os.path.join(d, 'action_[0-9]*.json')))
                    if re.search(r'action_(\d{6})\.json$', p) and int(p[-11:-5]) < self.control_start]
            if warm:
                try:
                    self.ceilings = dict(read_json(warm[-1]).get('ramp_metering') or {}) or None
                except (ValueError, OSError):
                    pass
        for path in sorted(glob.glob(os.path.join(d, 'action_[0-9]*.json'))):
            m = re.search(r'action_(\d{6})\.json$', path)
            if not m:
                continue
            sec = int(m.group(1))
            if sec in self.done:
                continue
            # The budget receipt is written last; warmup decisions may lack it.
            if not os.path.exists(path[:-5] + '.decision_budget.json') and sec >= self.control_start:
                continue
            try:
                if sec < self.control_start:
                    self.ceilings = dict(read_json(path).get('ramp_metering') or {}) or self.ceilings
                line = decision_line(d, sec, self.vsl_max, self.ceilings, self.chain_links)
            except (ValueError, OSError, KeyError):
                continue
            self.emit(line)
            self.done.add(sec)
        # A failed decision writes its joint report (completed=false) and no action JSON.
        for jp in glob.glob(os.path.join(d, 'action_[0-9]*.joint.json')):
            sec = int(re.search(r'action_(\d+)\.joint\.json$', jp).group(1))
            if sec in self.done or sec in self.failed or os.path.exists(jp[:-len('.joint.json')] + '.json'):
                continue
            if time.time() - os.path.getmtime(jp) < 60 or os.path.getsize(jp) > 5e6:
                continue
            try:
                rep = read_json(jp)
            except (ValueError, OSError):
                continue
            if rep.get('completed') is False:
                msg = str((rep.get('error') or {}).get('message', '')).strip()
                self.emit('DECISION FAILED sim_sec=%d  %s' % (sec, msg.splitlines()[-1][:300] if msg else '?'))
                self.failed.add(sec)
        runlog = self.run_dir / f'runlog_{self.name}.txt'
        if runlog.is_file():
            for m in FAILED_RE.finditer(runlog.read_text(encoding='utf-8', errors='replace')):
                sec = int(m.group(1))
                if sec not in self.failed and sec not in self.done:
                    self.emit('DECISION FAILED sim_sec=%d  runner: adapter exit nonzero (see runlog/stderr)' % sec)
                    self.failed.add(sec)
        newest = max((os.path.getmtime(p) for p in glob.glob(os.path.join(d, '**', '*'), recursive=True)),
                     default=None)
        if newest and time.time() - newest > self.stall_sec and not self.stalled:
            print('STALL no decision file written for %d min' % ((time.time() - newest) // 60), flush=True)
            self.stalled = True
        elif newest and time.time() - newest <= self.stall_sec:
            self.stalled = False

    def ended(self):
        if not os.path.exists(self.launch_log):
            return False
        text = io.open(self.launch_log, encoding='utf-8', errors='replace').read()
        if not LAUNCH_EXIT_RE.search(text):
            return False
        tail = text.splitlines()[-2:]
        summary = ''
        if self.run_dir is not None:
            runlog = self.run_dir / f'runlog_{self.name}.txt'
            if runlog.is_file():
                found = re.findall(r'DECISIONS_(?:OK|FAILED)=\d+', runlog.read_text(encoding='utf-8', errors='replace'))
                summary = ' '.join(found[-2:])
        print('RUN ENDED  ' + ' | '.join(tail) + ('  ' + summary if summary else ''), flush=True)
        return True

    def run(self, once=False):
        while True:
            if self.locate():
                self.scan()
            if self.ended() or once:
                return 0
            time.sleep(30)


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('target')
    parser.add_argument('launch_log')
    parser.add_argument('summary_log')
    parser.add_argument('--stall-min', type=float, default=40.0)
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args(argv)
    return Watch(args.target, args.launch_log, args.summary_log, args.stall_min).run(once=args.once)


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv[1:]))
    except ToolError as error:
        print(f'WATCH_ERROR {error}')
        sys.exit(1)
