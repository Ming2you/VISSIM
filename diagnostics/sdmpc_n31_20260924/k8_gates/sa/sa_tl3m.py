"""K8 amendment 13 (595eb450, D-K8-7) TL3m inputs: R-obs run validity, replay states of the new R-obs seeds, status.

    python -B sa_tl3m.py [--root R] [--out O] [--robs D] [--nc3 D] validity --seed S [--seed S2 ...] [--recheck]
    python -B sa_tl3m.py [...] prep --seed S [T ...]          (default T: the 61 R-obs decision states)
    python -B sa_tl3m.py [...] status                          (light: what exists per TL3m seed; writes nothing)
    every command takes --dry-run (prints the plan; reads no run folder, writes nothing)

TL3m = R-obs seeds {31, 43, 47} x GRID9 on each seed's own deployed template (amendment 13).  Order of the stage:
  1 validity  each seed (heavy IO: two ~1.1 GB FZP reads per seed, BELOW_NORMAL, one at a time)
              -> <out>/sa/tl3m/robs_validity_s<S>.json (schema k8-sa-robs-validity/v1)
  2 prep      s43 / s47 replay states (copies; make_replay_state_v2.prepare)   -> <out>/replays/s<S>/<T>/
              (s31 keeps <out>/replays/<T> of k8_gates/prep.py)
  3 captures  sa_capture.py tl3 BASE|SAF --robs-seed S ; robs61 SAF --robs-seed S ; robs61 BASE 1 150 --robs-seed S
  4 jobs      sa_jobs.py tl3m (BASE + SAF H3 OBS, SAF H6 OBS on the seed's event states)
  5 gates     sa_gates.py (G-EB-3 / G-EB-6 judged on TL3m, G-EB-14 per R-obs seed, G-EB-2 list with TL3m)

validity (binding, amendment 13; sa_common.OPERATIONALISATIONS 'R-obs validity'):
  (1) run exit 0: the last line 'EXIT <name> code=<n>' of <runs root>/wmi_<name>.log has n = 0.  Without an EXIT line
      the run is not finished: status not_finished and NOTHING in the run folder is read (a run in progress is never
      touched).  No wmi log -> error.
  (2) 61 decisions: decisions_<name>/state_<T>.json and action_<T>.json for every T of the 61 R-obs decision states
      and no other state file; runlog_<name>.txt DECISIONS_OK=61, DECISIONS_FAILED=0, STAGE=SIM_DONE (no runlog ->
      error).
  (3) FZP trajectory identical to the same-seed v3c3 NC FZP by the GB-6 method (gb6_result.json c1-c3, P10
      pair/fzp_bytecompare.py split): header = lines before the first data line, pre = data lines with SIMSEC < 5.1,
      body = the rest.  c1 the headers have the same line count and differ only in lines starting '* File:' /
      '* Date:'; c2 every R-obs pre line is the 0.10 s frame, the NC file has no pre line, the bodies are byte-
      identical (sha256 + first differing offset reported; GB-6 found exactly that one 0.10 s frame in R-obs3);
      c3 size difference = header difference + pre bytes.
      R-obs FZP absent -> false; NC FZP absent -> error.
  status: valid (1)-(3) true; invalid any of them false on a finished run (the seed leaves the judging sample,
  reported); not_finished / error otherwise (INCOMPLETE).  A record with status valid / invalid is kept (skip) unless
  --recheck, which moves it to robs_validity_s<S>.stale_<k>.json first.
Nothing under the run folders, NC3 or the code root is written.  VISSIM / COM is never started."""
import hashlib
import io
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sa_common as sc  # noqa: E402

c = sc.c
CH = 1 << 20
PRE_LIMIT_S = 5.1                         # GB-6: the R-obs-only frame lies before the first 5.10 s frame
PRE_FRAME_S = 0.10
HEADER_MAY_DIFFER = (b'* File:', b'* Date:')
_EXIT = re.compile(r'\bEXIT (\S+) code=(-?\d+)')
_WATCHDOG_EXIT = re.compile(r'\bWATCHDOG_EXIT code=(-?\d+)')
_KV = re.compile(r'^(DECISIONS_OK|DECISIONS_FAILED|STAGE|SIM_SEC)=(\S+)\s*$')


# ------------------------------------------------------------------------------------------------ (1) exit
def check_exit(wmi_log, name):
    """{'state': 'missing'|'not_finished'|'finished', 'code', 'line', 'watchdog_exit'} from the launcher log."""
    p = Path(wmi_log)
    if not p.is_file():
        return {'state': 'missing', 'path': str(p)}
    text = p.read_bytes().decode('utf-8', errors='replace')
    hits = [(m.group(1), int(m.group(2)), m.group(0)) for m in _EXIT.finditer(text)]
    hits = [h for h in hits if h[0] == name]
    wd = [int(m.group(1)) for m in _WATCHDOG_EXIT.finditer(text)]
    rec = {'path': str(p), 'sha256': sc.sha256_file(p), 'watchdog_exit': wd[-1] if wd else None}
    if not hits:
        rec['state'] = 'not_finished'
        return rec
    rec.update(state='finished', code=hits[-1][1], line=hits[-1][2])
    return rec


# ------------------------------------------------------------------------------------------------ (2) decisions
def check_decisions(run_dir, name):
    """{'ok': True|False|None, ...}: 61 state + action files and the runlog counters (None = runlog absent)."""
    run_dir = Path(run_dir)
    dec = run_dir / f'decisions_{name}'
    want = {f'{int(T):06d}' for T in sc.ROBS61_T}
    states = {p.name[len('state_'):-len('.json')] for p in dec.glob('state_*.json')} if dec.is_dir() else set()
    actions = {p.name[len('action_'):-len('.json')] for p in dec.glob('action_*.json')
               if re.fullmatch(r'action_\d{6}\.json', p.name)} if dec.is_dir() else set()
    rec = {'decisions_dir': str(dec), 'n_state': len(states), 'n_action': len(actions),
           'state_missing': sorted(want - states)[:10], 'state_extra': sorted(states - want)[:10],
           'action_missing': sorted(want - actions)[:10]}
    files_ok = states == want and want <= actions
    runlog = run_dir / f'runlog_{name}.txt'
    if not runlog.is_file():
        rec.update(ok=None if files_ok else False, runlog=None, reason='runlog absent')
        return rec
    kv = {}
    for line in runlog.read_bytes().decode('utf-8', errors='replace').splitlines():
        m = _KV.match(line.strip())
        if m:
            kv[m.group(1)] = m.group(2)                   # the last value wins (the end-of-run summary)
    rec['runlog'] = {'path': str(runlog), 'sha256': sc.sha256_file(runlog), **kv}
    counters_ok = (kv.get('DECISIONS_OK') == str(len(sc.ROBS61_T)) and kv.get('DECISIONS_FAILED') == '0'
                   and kv.get('STAGE') == 'SIM_DONE')
    rec['ok'] = bool(files_ok and counters_ok)
    return rec


# ------------------------------------------------------------------------------------------------ (3) FZP (GB-6)
def split_fzp(path):
    """(header bytes, pre lines, body offset): header = lines before the first data line, pre = data lines with
    SIMSEC < 5.1, body = from the first data line with SIMSEC >= 5.1 (P10 pair/fzp_bytecompare.py)."""
    head, pre, off = [], [], 0
    with io.open(path, 'rb') as f:
        for raw in f:
            if raw[:1].isdigit():
                t = float(raw.split(b';', 1)[0])
                if t >= PRE_LIMIT_S - 1e-9:
                    return b''.join(head), pre, off
                pre.append(raw)
            else:
                if pre:
                    raise ValueError(f'header line after data in {path}')
                head.append(raw)
            off += len(raw)
    raise ValueError(f'no data line with SIMSEC >= 5.1 in {path}')


def compare_fzp(a, b):
    """GB-6 c1-c3 of R-obs FZP a against NC FZP b (read only, 1 MiB chunks)."""
    ha, pa, oa = split_fzp(a)
    hb, pb, ob = split_fzp(b)
    sa_, sb_ = os.path.getsize(a), os.path.getsize(b)
    la, lb = ha.splitlines(True), hb.splitlines(True)
    differing = [[x.decode('cp949', 'replace').rstrip('\r\n'), y.decode('cp949', 'replace').rstrip('\r\n')]
                 for x, y in zip(la, lb) if x != y]
    c1 = len(la) == len(lb) and all(x.startswith(HEADER_MAY_DIFFER) and y.startswith(HEADER_MAY_DIFFER)
                                     and x.split(b':', 1)[0] == y.split(b':', 1)[0]
                                     for x, y in zip(la, lb) if x != y)
    pre_frames = sorted({round(float(x.split(b';', 1)[0]), 2) for x in pa})
    ga, gb = hashlib.sha256(), hashlib.sha256()
    first, n = None, 0
    with io.open(a, 'rb') as fa, io.open(b, 'rb') as fb:
        fa.seek(oa)
        fb.seek(ob)
        while True:
            x, y = fa.read(CH), fb.read(CH)
            if not x and not y:
                break
            ga.update(x)
            gb.update(y)
            if first is None and x != y:
                m = min(len(x), len(y))
                first = n + next((j for j in range(m) if x[j] != y[j]), m)
            n += max(len(x), len(y))
    body_identical = first is None and (sa_ - oa) == (sb_ - ob)
    c2 = body_identical and not pb and all(f == PRE_FRAME_S for f in pre_frames)
    pre_a, pre_b = sum(len(x) for x in pa), sum(len(x) for x in pb)
    c3 = (sa_ - sb_) == (len(ha) - len(hb)) + (pre_a - pre_b)
    return {'robs_fzp': str(a), 'nc_fzp': str(b), 'size_robs': sa_, 'size_nc': sb_,
            'c1_header': {'ok': c1, 'lines_robs': len(la), 'lines_nc': len(lb), 'differing': differing[:6]},
            'c2_payload': {'ok': c2, 'pre51_frames_robs': pre_frames, 'pre51_lines_robs': len(pa),
                           'pre51_lines_nc': len(pb), 'body_identical': body_identical,
                           'body_sha256_robs': ga.hexdigest(), 'body_sha256_nc': gb.hexdigest(),
                           'first_diff_body_offset': first},
            'c3_size': {'ok': c3, 'diff': sa_ - sb_, 'header_diff': len(ha) - len(hb), 'pre51_bytes_robs': pre_a,
                        'pre51_bytes_nc': pre_b},
            'ok': bool(c1 and c2 and c3)}


def robs_fzp_of(run_dir):
    hits = sorted((Path(run_dir) / 'vissim_eval').glob('*_001.fzp'))
    return hits[0] if len(hits) == 1 else None, [str(h) for h in hits]


# ------------------------------------------------------------------------------------------------ validity
def validity(seed, *, run_dir=None, wmi_log=None, nc_fzp=None):
    """The amendment 13 validity record of R-obs `seed` (paths default to the configured roots)."""
    run_dir = Path(run_dir or sc.robs_dir(seed))
    name = run_dir.name
    wmi_log = Path(wmi_log or (run_dir.parent / f'wmi_{name}.log'))
    nc = Path(nc_fzp or sc.nc_fzp(seed))
    rec = {'schema': sc.VALIDITY_SCHEMA, 'seed': int(seed), 'name': name, 'run_dir': str(run_dir),
           'written_at': time.strftime('%Y-%m-%d %H:%M:%S'), 'tool_sha256': sc.sha256_file(__file__),
           'rule': 'amendment 13: run exit 0, 61 decisions, FZP = same-seed v3c3 NC FZP (GB-6 c1-c3)',
           'checks': {}, 'reasons': []}
    ex = check_exit(wmi_log, name)
    rec['checks']['exit'] = ex
    if ex['state'] == 'missing':
        rec.update(status='error', reasons=[f'launcher log absent: {wmi_log}'])
        return rec
    if ex['state'] == 'not_finished':
        rec.update(status='not_finished', reasons=[f'no "EXIT {name} code=" line in {wmi_log} (run not finished; '
                                                   'the run folder was not read)'])
        return rec
    false, unknown = [], []
    if ex['code'] != 0:
        false.append(f'run exit {ex["code"]} (not 0)')
    dec = check_decisions(run_dir, name)
    rec['checks']['decisions'] = dec
    if dec['ok'] is False:
        counters = {k: (dec.get('runlog') or {}).get(k) for k in ('DECISIONS_OK', 'DECISIONS_FAILED', 'STAGE')}
        false.append(f'decisions: {dec["n_state"]} state / {dec["n_action"]} action files, runlog {counters}')
    elif dec['ok'] is None:
        unknown.append('decisions: ' + dec.get('reason', 'not readable'))
    if false:
        rec['checks']['fzp'] = {'skipped': 'run already invalid'}
    else:
        a, hits = robs_fzp_of(run_dir)
        if a is None:
            rec['checks']['fzp'] = {'ok': False, 'robs_fzp_candidates': hits}
            false.append(f'R-obs FZP: {len(hits)} *_001.fzp files in {run_dir / "vissim_eval"} (one expected)')
        elif not nc.is_file():
            rec['checks']['fzp'] = {'ok': None, 'nc_fzp': str(nc)}
            unknown.append(f'NC FZP absent: {nc}')
        else:
            try:
                f = compare_fzp(a, nc)
            except (OSError, ValueError) as exc:
                f = {'ok': False, 'error': repr(exc)[:300]}
            rec['checks']['fzp'] = f
            if not f['ok']:
                false.append('FZP trajectory differs from the same-seed NC FZP (GB-6 ' + ', '.join(
                    k for k in ('c1_header', 'c2_payload', 'c3_size') if not (f.get(k) or {}).get('ok')) + ')'
                             + (': ' + f['error'] if 'error' in f else ''))
    if false:
        rec.update(status='invalid', reasons=false + unknown)
    elif unknown:
        rec.update(status='error', reasons=unknown)
    else:
        rec.update(status='valid')
    return rec


def write_validity(seed, recheck=False):
    dest = sc.validity_path(seed)
    old = sc.read_validity(seed)
    if isinstance(old, dict) and old.get('status') in ('valid', 'invalid') and not recheck:
        print(f'SA_TL3M_VALIDITY_SKIP s{seed} status={old["status"]} (kept; --recheck to redo) {dest}', flush=True)
        return old
    if dest.is_file():
        k = 1
        while dest.with_name(f'{dest.stem}.stale_{k}.json').exists():
            k += 1
        os.replace(dest, dest.with_name(f'{dest.stem}.stale_{k}.json'))
    rec = validity(seed)
    sc.write_json(dest, rec)
    print(f'SA_TL3M_VALIDITY s{seed} status={rec["status"]} reasons={rec["reasons"]} -> {dest}', flush=True)
    return rec


# ------------------------------------------------------------------------------------------------ prep
def prep(seed, Ts, dry=False):
    """Replay states of a valid R-obs seed other than s31 (copies, make_replay_state_v2.prepare of the code root, as
    k8_gates/prep.py does for s31) -> <out>/replays/s<seed>/<T>/."""
    sc.guard_tl3m_seed(seed)
    if sc.is_robs3(seed):
        raise SystemExit('s31 replay states are <out>/replays/<T> (k8_gates/prep.py)')
    status, why = sc.validity_status(sc.read_validity(seed), seed)
    if dry:
        print(f'DRY prep s{seed} validity={status or "unknown"} ({why}) from {sc.robs_dir(seed)} -> '
              f'{sc.replay_dir(Ts[0], seed).parent} T={Ts[0]}..{Ts[-1]} ({len(Ts)})')
        return
    if status != 'valid':
        raise SystemExit(f'R-obs s{seed} not usable ({status or "unknown"}: {why}); run sa_tl3m.py validity first')
    c.configure(root=c.R, out=c.OUT, robs=sc.robs_dir(seed), nc3=c.NC3)
    c.lower_priority()
    sys.path.insert(0, str(c.R / 'diagnostics/sdmpc_n31_20260924/tools'))
    import n31_common  # noqa: E402
    import make_replay_state_v2 as m  # noqa: E402

    def copy_only(source, target):
        source, target = Path(source), Path(target)
        n31_common.require(source.is_file(), f'Missing file to copy: {source}')
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(n31_common.long_path(source), n31_common.long_path(target))
        return 'copy'
    n31_common.link_or_copy = copy_only
    m.link_or_copy = copy_only
    for T in Ts:
        out = sc.replay_dir(T, seed)
        if out.exists():
            print('exists', out, flush=True)
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        m.prepare(str(c.DEC), int(T), str(out))
        print('prepared', seed, T, out, flush=True)


# ------------------------------------------------------------------------------------------------ status
def status(tree):
    """Light read of what exists per TL3m seed (validity, replays, captures, jobs).  Writes nothing."""
    events = None
    try:
        import sa_jobs
        events = sa_jobs.event_states()
    except SystemExit:
        pass
    for seed in sc.TL3M_SEEDS:
        st, why = sc.validity_status(sc.read_validity(seed), seed)
        rep = sum(1 for T in sc.ROBS61_T if (sc.replay_dir(T, seed) / 'replay_manifest.json').is_file())
        cap = {arm: sum(1 for T in sc.GRID9 if (sc.cap_dir(tree, 'TL3', T, arm, seed=seed) / 'capture.json').is_file())
               for arm in ('BASE', 'SAF')}
        robs = {arm: sum(1 for T in sc.ROBS61_T if any((sc.cap_dir(tree, 'ROBS61', T, arm, seed=seed) / n).is_file()
                                                    for n in ('capture.json', 'capture_failed.json')))
                for arm in ('BASE', 'SAF')}
        ev = sorted(T for s, T in (events or ()) if s == seed)
        jobs = {f'{arm}_H{H}': sum(1 for T in (ev if H == 6 else sc.GRID9)
                                   if (sc.job_dir(tree, sc.job_label('TL3', T, arm, 'OBS', H, seed=seed))
                                       / 'summary.json').is_file())
                for arm, H in (('BASE', 3), ('SAF', 3), ('SAF', 6))}
        print(f'TL3M s{seed} validity={st or "unknown"}{" (" + why + ")" if why else ""} replays={rep}/61 '
              f'TL3 captures={cap}/9 ROBS61 records={robs} (SAF 61, BASE needs 1/150) events={ev} jobs={jobs}')


def main():
    ap = c.add_nc3(c.parser(__doc__))
    sub = ap.add_subparsers(dest='cmd', required=True)
    v = sub.add_parser('validity')
    v.add_argument('--seed', type=int, action='append', required=True)
    v.add_argument('--recheck', action='store_true')
    v.add_argument('--dry-run', action='store_true')
    p = sub.add_parser('prep')
    p.add_argument('--seed', type=int, required=True)
    p.add_argument('T', nargs='*', type=int)
    p.add_argument('--dry-run', action='store_true')
    s = sub.add_parser('status')
    s.add_argument('--tree', default='k86')
    s.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()
    c.apply(args)
    if args.cmd == 'validity':
        for seed in args.seed:
            sc.guard_tl3m_seed(seed)
        if args.dry_run:
            for seed in args.seed:
                d = sc.robs_dir(seed)
                print(f'DRY validity s{seed} run={d} wmi={sc.robs_wmi_log(seed)} '
                      f'(exists={sc.robs_wmi_log(seed).is_file()}) nc_fzp={sc.nc_fzp(seed)} -> {sc.validity_path(seed)}')
            return 0
        c.lower_priority()
        for seed in args.seed:                           # one seed at a time (heavy IO)
            write_validity(seed, recheck=args.recheck)
        return 0
    if args.cmd == 'prep':
        prep(args.seed, args.T or list(sc.ROBS61_T), dry=args.dry_run)
        return 0
    status(args.tree)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
