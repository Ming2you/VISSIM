"""Read-only access to the precomputed SA gate inputs (JSON only; no model import).

The calculators (sa_smoke.py, sa_gates.py) see the harness outputs only through this class, so a gate run is a pure
function of files that already exist: job summaries (sa_worker.py), capture records (sa_cap_child.py), the VISSIM
reference (sa_vissim_ref.py), comparisons (sa_compare.py), hook counts (sa_hookcount.py), the smoke result
(sa_smoke.py) and the few logs named on the command line.  Every value read is resolved here with a declared key, and
a missing file is returned as None (the calculator then reports INCOMPLETE, never a default).  A job summary whose run
ended on its own missing capture input (sc.job_input_absent, review r4 B-r4-1) and a killed capture (review r3 B-r3-3)
are returned as absent too."""
from __future__ import annotations

import json
from pathlib import Path

import sa_common as sc


class Inputs:
    def __init__(self, tree='k86', base_tree=None):
        self.tree = tree
        self.base_tree = base_tree
        self._jobs = {}
        self._caps = {}
        self._ref = None
        self.missing = []

    # ------------------------------------------------------------------ jobs / captures
    def job(self, label, tree=None):
        key = (tree or self.tree, label)
        if key not in self._jobs:
            s = sc.read_json(sc.job_dir(key[0], label) / 'summary.json')
            absent = sc.job_input_absent(s, key[0])
            if s is None:
                self.missing.append(f'job {key[0]}/{label}')
            elif absent is not None:                  # ran without its capture input: an absent job (B-r4-1)
                self.missing.append(f'job input absent {key[0]}/{label}: {absent}')
                s = None
            self._jobs[key] = s
        return self._jobs[key]

    def jobx(self, harness, T, arm, entry, H, **kw):
        tree = kw.pop('tree', None)
        return self.job(sc.job_label(harness, T, arm, entry, H, **kw), tree=tree)

    def cap(self, harness, T, arm, *, seed=None, frame_T=None, fh_off=False, tree=None):
        d = sc.cap_dir(tree or self.tree, harness, T, arm, seed=seed, frame_T=frame_T)
        if fh_off:
            d = d.parent / (d.name + '_fhoff')
        key = str(d)
        if key not in self._caps:
            ok = sc.read_json(d / 'capture.json')
            if ok is not None:                                 # a capture_failed.json next to it is stale (B-r3-3)
                ok.setdefault('ok', True)
                self._caps[key] = ok
            else:
                fail = sc.read_json(d / 'capture_failed.json')
                if fail is None:
                    self.missing.append(f'capture {d}')
                elif sc.capture_failure_kind(fail) == 'killed':   # no child record: unreadable = absent (B-r3-3)
                    self.missing.append(f'capture killed (no child record) {d}')
                    fail = None
                else:
                    fail['ok'] = False
                self._caps[key] = fail
        return self._caps[key]

    # ------------------------------------------------------------------ VISSIM reference
    @property
    def ref(self):
        if self._ref is None:
            self._ref = sc.read_json(sc.sa_out() / 'vissim_ref.json')
            if self._ref is None:
                self.missing.append('vissim_ref.json')
                self._ref = {}
        return self._ref

    def state_ref(self, seed, T):
        try:
            return self.ref['seeds'][str(seed)]['states'][str(T)]
        except (KeyError, TypeError):
            return None

    def robs3(self, t):
        try:
            return self.ref['seeds']['31']['robs3'][str(int(t))]
        except (KeyError, TypeError):
            return None

    def fh_states(self):
        return [(s, T) for s in sc.FH_SEEDS for T in sc.GRID9]

    def event_states(self):
        return [(s, T) for s, T in self.fh_states() if (self.state_ref(s, T) or {}).get('event_state')]

    def nonevent_states(self):
        return [(s, T) for s, T in self.fh_states() if (self.state_ref(s, T) or {}).get('nonevent_state')]

    # ------------------------------------------------------------------ amendment 13 (TL3m)
    def robs_validity(self, seed):
        """R-obs validity record of a TL3m seed (sa_tl3m.py validity), or None (absent / unreadable)."""
        rec = sc.read_validity(seed)
        if rec is None:
            self.missing.append(f'R-obs validity record s{seed}')
        return rec

    def tl3m_job(self, T, arm, entry, H, seed):
        """TL3m job of an R-obs seed (s31 = the TL3 label without a seed tag).  A summary whose job does not name this
        seed and harness TL3 is not this job: None, listed missing."""
        s = self.jobx('TL3', T, arm, entry, H, seed=seed)
        job = (s or {}).get('job') or {}
        if s is not None and (job.get('seed') != int(seed) or job.get('harness') != 'TL3'):
            self.missing.append(f'job seed/harness mismatch TL3 s{seed} {T} {arm} {entry} H{H}: '
                                f'{job.get("seed")} {job.get("harness")}')
            return None
        return s

    # ------------------------------------------------------------------ side files
    def compare(self, name):
        d = sc.read_json(sc.sa_out() / 'compare' / f'{name}.json')
        if d is None:
            self.missing.append(f'compare {name}')
        return d

    def hooks(self):
        d = sc.read_json(sc.sa_out() / f'hooks_{self.tree}.json')
        if d is None:
            self.missing.append(f'hooks_{self.tree}.json')
        return d

    def smoke(self):
        d = sc.read_json(sc.sa_out() / 'gates' / f'smoke_{self.tree}.json')
        if d is None:
            self.missing.append(f'smoke_{self.tree}.json')
        return d

    def full_run(self, T, arm, tag=''):
        d = sc.read_json(sc.full_dir(self.tree, T, arm, tag) / 'run.json')
        if d is None:
            self.missing.append(f'full {T} {arm} {tag}')
        return d

    def full_action(self, T, arm, tag=''):
        p = sc.full_dir(self.tree, T, arm, tag) / f'action_{int(T):06d}.json'
        if not p.is_file():
            self.missing.append(f'action {p}')
            return None
        return json.loads(p.read_text(encoding='utf-8'))


# ------------------------------------------------------------------ summary accessors (declared keys)
def block(summary, k):
    if not summary or not summary.get('ok'):
        return None
    blocks = summary.get('blocks') or []
    return blocks[k - 1] if len(blocks) >= k else None


def w_ports_total(summary, k=1):
    b = block(summary, k)
    return None if b is None else b['w_ports']['total']


def port_stock(summary, off, k=1):
    b = block(summary, k)
    return None if b is None else b['w_ports'].get('port_' + off)


def blocked_any(summary, off, upto_k=None):
    if not summary or not summary.get('ok'):
        return None
    blocks = summary.get('blocks') or []
    blocks = blocks[:upto_k] if upto_k else blocks
    return any((b.get('blocked_steps') or {}).get(off, 0.0) > 0 for b in blocks)


def blocked_steps(summary, off):
    if not summary or not summary.get('ok'):
        return None
    return sum((b.get('blocked_steps') or {}).get(off, 0.0) for b in summary.get('blocks') or [])
