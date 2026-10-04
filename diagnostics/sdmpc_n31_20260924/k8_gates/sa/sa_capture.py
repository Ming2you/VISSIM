"""Capture driver for the SA gates (one adapter process at a time, BELOW_NORMAL) + full deployed decisions with hooks.

    python -B sa_capture.py [--root R] [--out O] [--robs D] [--nc3 D] [--tree L] [--dry-run] <kind> <arm> [T ...]

kind      what                                                         default T            h_long
  tl3     TL3 template (R-obs3 state, arm tuning, code root)          GRID9 (9)            42
  dp      DP: the deployed-path capture itself (RS:185/:253 run)       DP_T (17)            3
  robs61  key-on initialization of all 61 R-obs3 states (G-EB-14)      ROBS61_T (61)        3
  fh      FH: TL3 capture of state frame_T with the FZP island of      GRID9                6
          seed s at T transplanted (sa_fh); --seeds, --frames (H-5:
          'T-150,T,T+150'), --fh-disabled (H-0: hook installed, no-op)
  full    full deployed decision (no capture) with the passive hooks  DP_FULL_T (2700 4950) -
          sa_hooks/sitecustomize.py (G-EB-13 capacity reads, G-EB-11(d) S3 31 sites chained + SA fold sites);
          --chain site|s3site, --s3-table <json from sa_anchors.py>
  t9c     BASE only: the scratch projection of T9c (amendment 1 r2      2700                 3
          section 8, AMENDMENT_5 section 4) = the deployed BASE tuning with
          observation.physical_support_repair pointing to a scratch copy of
          the deployed support table plus 10695 -> SC1001_to_SC2002 (written
          under <out>/sa/tuning/, never in the repository).  Read by
          tests/test_stopline_approach_captured.py T9c next to TL3/<T>/BASE.
arm: BASE | SAF | SAG (tunings from sa_arms.py).  --tree labels the code root (k86 = this K8-6 head; e.g. k85/k84 for
the previous runtime commit unpacked by `git archive` and passed as --root, G-EB-1).
Outputs <out>/sa/cap/<tree>/<KIND>/<T>[_s<seed>][_f<frameT>]/<arm>/ and <out>/sa/full/<tree>/<T>_<arm>[_<tag>]/.
A failed attempt leaves capture_failed.json (error_kind 'killed' when the child wrote no record, else the child's own
error_kind / error_site of its full traceback, sa_errors, K8 amendment 7 §2; the log tail is reported only,
log_error_kind); a new attempt first moves an earlier capture_failed.json to stale_capture_failed_<k>.json (review r3
B-r3-3; read by no gate).  A full run records in run.json the site of the traceback that ends its adapter log
(error_site, sa_errors.log_error_site) when it exits != 0.
Needs <out>/replays/<T> for every T used (k8_gates/prep.py; FH -frames also T-150 / T+150), sa_arms.py, and for fh
the x2 ext parquets (<out>/opt1v2/data or --data) and sa_fzp_frames.py output."""
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sa_common as sc  # noqa: E402

c = sc.c
KINDS = ('tl3', 'dp', 'robs61', 'fh', 'full', 't9c')
H_LONG = {'tl3': 42, 'dp': 3, 'robs61': 3, 'fh': 6, 't9c': 3}
T9C_LINK, T9C_TARGET, T9C_TO_LINK = '10695', 'SC1001_to_SC2002', '38'   # posthead_rehome of the evidence
GEOMETRY_REL = Path('diagnostics/demand_sweep/user_native_20260914/metanet_calibration_v1/v3c3_nc_20261001/'
                    'observations/s31_v3c3nc_observations/geometry.json')


def parse():
    ap = c.add_nc3(c.parser(__doc__))
    ap.add_argument('kind', choices=KINDS)
    ap.add_argument('arm', choices=sc.ARMS)
    ap.add_argument('T', nargs='*', type=int)
    ap.add_argument('--tree', default='k86', help='label of the code root (output folder level)')
    ap.add_argument('--seeds', default='31,41,43,47,53', help='fh: seeds (v3c3 NC fit seeds only)')
    ap.add_argument('--frames', default='T', help="fh: template frames relative to T, e.g. 'T-150,T,T+150' (H-5)")
    ap.add_argument('--fh-disabled', action='store_true', help='fh: install the hook but transplant nothing (H-0)')
    ap.add_argument('--data', help='x2 ext parquet folder (default <out>/opt1v2/data)')
    ap.add_argument('--chain', choices=('site', 's3site'), default='site', help='full: base site chained by sa_hooks')
    ap.add_argument('--s3-table', help='full --chain s3site: re-anchored 31-site table JSON (sa_anchors.py)')
    ap.add_argument('--tag', default='', help='full: output folder tag (e.g. hooks, base_recount)')
    ap.add_argument('--dry-run', action='store_true', help='print the plan and command lines only (writes nothing)')
    return ap.parse_args()


def frames_of(spec, T):
    out = []
    for part in spec.split(','):
        part = part.strip().replace(' ', '')
        if part == 'T':
            out.append(T)
        elif part.startswith('T+'):
            out.append(T + int(part[2:]))
        elif part.startswith('T-'):
            out.append(T - int(part[2:]))
        else:
            raise SystemExit('bad --frames item ' + part)
    return out


def plan(args):
    kind = args.kind
    Ts = args.T or {'tl3': list(sc.GRID9), 'dp': list(sc.DP_T), 'robs61': list(sc.ROBS61_T), 'fh': list(sc.GRID9),
                    'full': list(sc.DP_FULL_T), 't9c': [2700]}[kind]
    rows = []
    if kind == 'fh':
        seeds = [int(s) for s in args.seeds.split(',') if s]
        for s in seeds:
            sc.guard_seed(s)
        for s in seeds:
            for T in Ts:
                for f in frames_of(args.frames, T):
                    rows.append(dict(harness='FH', T=T, seed=s, frame_T=f))
    else:
        harness = {'tl3': 'TL3', 'dp': 'DP', 'robs61': 'ROBS61', 'full': 'FULL', 't9c': 'T9C'}[kind]
        rows = [dict(harness=harness, T=T, seed=31 if kind != 'full' else None, frame_T=T) for T in Ts]
    return rows


def tuning_of(arm, dry):
    if dry:
        try:
            import sa_arms
            return sa_arms.load_arms()[arm]
        except SystemExit as exc:
            return {'path': f'<sa_arms.py not run: {exc}>', 'sha256': None}
    import sa_arms
    return sa_arms.load_arms()[arm]


def t9c_tuning(base, dry):
    """Scratch tuning of the T9c projection: BASE + a support table that also fixes 10695 -> SC1001_to_SC2002.

    The support row copies the deployed 10368 / 10118 rows (actual connector endpoint, downstream origin = the target);
    projection_support.configure checks it against the network like any reviewed row.  Files go to <out>/sa/tuning/
    (outside the repository); the absolute support path resolves unchanged under the adapter's ROOT / path join."""
    tdir = sc.sa_out() / 'tuning'
    support_path, tuning_path = tdir / 'support_t9c_10695.json', tdir / 'config_n31_v2_t9c_scratch.json'
    if dry:
        return {'path': str(tuning_path), 'sha256': None, 'support': str(support_path)}
    doc = json.loads(Path(base['path']).read_text(encoding='utf-8-sig'))
    rel = (doc.get('observation') or {}).get('physical_support_repair')
    if not rel:
        raise SystemExit('BASE tuning has no observation.physical_support_repair; T9c scratch cannot be built')
    support = json.loads((c.R / rel).read_text(encoding='utf-8-sig'))
    if T9C_LINK in support['link_to_storage']:
        raise SystemExit('deployed support table already fixes 10695 (posthead_rehome would be empty)')
    support['link_to_storage'][T9C_LINK] = T9C_TARGET
    support['evidence'][T9C_LINK] = {
        'to_link': T9C_TO_LINK,
        'reason': 'K8-6 T9c scratch projection only (amendment 1 r2 section 8 T9c, AMENDMENT_5 section 4): the '
                  'connector endpoint and its downstream origin agree on one storage; not a deployment table.',
        'existing_origins': [T9C_TARGET, sc.GATE], 'downstream_origins': [T9C_TARGET],
        'zero_vehicle_support_reviewed': True}
    tdir.mkdir(parents=True, exist_ok=True)
    support_path.write_bytes(json.dumps(support, indent=1, ensure_ascii=False).encode('utf-8'))
    doc.setdefault('observation', {})['physical_support_repair'] = str(support_path.resolve())
    tuning_path.write_bytes(json.dumps(doc, indent=2, ensure_ascii=False).replace('\n', '\r\n').encode('utf-8'))
    return {'path': str(tuning_path), 'sha256': sc.sha256_file(tuning_path), 'support': str(support_path),
            'support_sha256': sc.sha256_file(support_path), 'base_sha256': base.get('sha256')}


def fh_spec_path(seed, island_T, frame_T):
    return sc.sa_out() / 'fh_specs' / f's{seed}_T{island_T:06d}_f{frame_T:06d}.json'


def build_fh_spec(args, seed, T, frame_T):
    import sa_fh
    data = Path(args.data) if args.data else c.OUT / 'opt1v2' / 'data'
    ext = data / f'e_s{seed}_ext.parquet'
    frames = sc.sa_out() / 'fzp' / f's{seed}_frames.parquet'
    spec = sa_fh.build_spec(seed, T, frame_T, ext, frames, c.R / GEOMETRY_REL)
    spec['inputs'] = {'ext_parquet': str(ext), 'ext_sha256': sc.sha256_file(ext), 'frames_parquet': str(frames),
                      'frames_sha256': sc.sha256_file(frames)}
    path = fh_spec_path(seed, T, frame_T)
    sc.write_json(path, spec)
    return path


def run_capture(args, row, tuning):
    out = sc.cap_dir(args.tree, row['harness'], row['T'], args.arm, seed=row.get('seed'), frame_T=row['frame_T'])
    if args.kind == 'fh' and args.fh_disabled:
        out = out.parent / (out.name + '_fhoff')
    replay = c.REPLAYS / f'{row["frame_T"]:06d}'
    if args.dry_run:
        ok = (replay / 'replay_manifest.json').is_file()
        print(f'DRY {row} -> {out}  replay={"ok" if ok else "MISSING " + str(replay)}  tuning={tuning["path"]}')
        if ok:
            _, a = c.adapter_args(replay, out, tuning=tuning['path'])
            print('  ' + ' '.join([c.PY, '-B', str(HERE / 'sa_cap_child.py'), str(out), '<capture_spec.json>',
                                   str(c.ADAPTER)] + a))
        return
    if (out / 'capture.json').is_file():
        print(f'SA_CAPTURE_SKIP exists {out}', flush=True)
        return
    out.mkdir(parents=True, exist_ok=True)
    stale = set_aside_failure(out)
    spec = {k: row.get(k) for k in ('harness', 'T', 'seed', 'frame_T')}
    spec.update(arm=args.arm, tree=args.tree, tuning={'path': tuning['path'], 'sha256': tuning['sha256']},
                h_long=H_LONG[args.kind], fh=None)
    if args.kind == 'fh':
        spec['fh'] = {'spec_path': str(build_fh_spec(args, row['seed'], row['T'], row['frame_T'])),
                      'enabled': not args.fh_disabled}
    spec_path = out / 'capture_spec.json'
    sc.write_json(spec_path, spec)
    _, a = c.adapter_args(replay, out, tuning=tuning['path'])
    cmd = [c.PY, '-B', str(HERE / 'sa_cap_child.py'), str(out), str(spec_path), str(c.ADAPTER)] + a
    code, wall = c.run(cmd, out / 'capture_log.txt', c.base_env())
    if not (out / 'capture.json').is_file():
        sc.write_json(out / 'capture_failed.json', failure_record(out, code, wall, stale))
    print(f'SA_CAPTURE {row} arm={args.arm} exit={code} wall={wall} out={out}', flush=True)


def set_aside_failure(out):
    """Review r3 B-r3-3: a capture_failed.json of an earlier attempt is moved to stale_capture_failed_<k>.json before
    a new attempt (kept for the record, read by no gate), so the parent never merges an old child record into the
    new attempt and a later good capture.json is not shadowed by an old failure.  Returns the new name or None."""
    old = out / 'capture_failed.json'
    if not old.is_file():
        return None
    k = 1
    while (out / f'stale_capture_failed_{k}.json').exists():
        k += 1
    dest = out / f'stale_capture_failed_{k}.json'
    os.replace(old, dest)
    return dest.name


def failure_record(out, code, wall, stale=None):
    """capture_failed.json of this attempt.  The child's own record (k8-sa-capture/v1, written by its handler) is
    kept and completed; without it (the process was stopped or died before its handler) the record is the parent's
    alone and its kind is 'killed' (unreadable -> INCOMPLETE, sc.capture_failure_kind), whatever the log tail says."""
    try:
        child = sc.read_json(out / 'capture_failed.json')
    except ValueError:                                   # a child stopped while writing (no record)
        child = None
    child = child if isinstance(child, dict) and child.get('schema') == sc.CAPTURE_SCHEMA else None
    fail = dict(child or {})
    log = out / 'capture_log.txt'
    tail = log.read_text(encoding='utf-8', errors='replace')[-4000:] if log.is_file() else ''
    fail.update(ok=False, exit=code, wall=wall, log_tail=tail, child_record=child is not None,
                log_error_kind=sc.error_kind(tail) or 'other', stale_failure_set_aside=stale)
    if child is None:
        fail['error_kind'] = 'killed'
    else:                                # the child's classification of its own traceback (amendment 7 §2)
        fail['error_kind'] = sc.record_kind(child)
        fail['error_site'] = sc.record_site(child)
    return fail


error_kind = sc.error_kind               # the one table (sa_errors, amendment 7 §2; review N-r4-2)


def run_full(args, row, tuning):
    out = sc.full_dir(args.tree, row['T'], args.arm, args.tag)
    replay = c.REPLAYS / f'{row["T"]:06d}'
    hook = out / 'hook'
    chain = sc.GATES_DIR / ('s3site' if args.chain == 's3site' else 'site') / 'sitecustomize.py'
    extra = {'K8_SA_CHAIN_SITE': str(chain), 'K8_SA_HOOK': '1'}
    if args.chain == 's3site':
        if not args.s3_table:
            raise SystemExit('--chain s3site needs --s3-table (sa_anchors.py output)')
        extra['K8_S3_TABLE_JSON'] = str(Path(args.s3_table).resolve())
    if args.dry_run:
        ok = (replay / 'replay_manifest.json').is_file()
        print(f'DRY full {row} arm={args.arm} -> {out} replay={"ok" if ok else "MISSING"} chain={chain} '
              f'chain_exists={chain.is_file()} env={extra}')
        if ok:
            _, a = c.adapter_args(replay, out, tuning=tuning['path'])
            print('  ' + ' '.join([c.PY, '-B', str(c.ADAPTER)] + a))
        return
    if (out / 'run.json').is_file():
        print(f'SA_FULL_SKIP exists {out}', flush=True)
        return
    if not chain.is_file():
        raise SystemExit(f'chained site missing: {chain}')
    out.mkdir(parents=True, exist_ok=True)
    env = c.base_env(extra=extra, hook_dir=hook)
    env['PYTHONPATH'] = str(HERE / 'sa_hooks') + ';' + env['PYTHONPATH'].split(';', 1)[1]
    _, a = c.adapter_args(replay, out, tuning=tuning['path'])
    code, wall = c.run([c.PY, '-B', str(c.ADAPTER)] + a, out / 'adapter_log.txt', env)
    rec = {'T': row['T'], 'arm': args.arm, 'tree': args.tree, 'exit': code, 'wall': wall,
           'tuning': tuning, 'chain': args.chain, 's3_table': args.s3_table}
    if code != 0:                       # amendment 7 §2: runtime traceback (failed) vs killed / harness (unfinished)
        log = out / 'adapter_log.txt'
        tail = log.read_text(encoding='utf-8', errors='replace')[-6000:] if log.is_file() else ''
        rec.update(error_site=sc.log_error_site(tail), error_kind=sc.error_kind(tail), log_tail=tail[-2000:])
    action = out / f'action_{row["T"]:06d}.json'
    if action.is_file():
        d = json.loads(action.read_text(encoding='utf-8'))
        m = d.get('metadata', {})
        rec.update(action_json_bytes=action.stat().st_size, objective=(m.get('joint_leader_selection') or {}).get('objective'),
                   held_objective=(m.get('joint_leader_selection') or {}).get('held_objective'),
                   csv_sha256=(sc.sha256_file(out / f'action_{row["T"]:06d}.csv')
                               if (out / f'action_{row["T"]:06d}.csv').is_file() else None))
    sc.write_json(out / 'run.json', rec)
    print('SA_FULL', json.dumps(rec, default=str), flush=True)


def main():
    args = parse()
    c.apply(args)
    rows = plan(args)
    tuning = tuning_of(args.arm, args.dry_run)
    if args.kind == 't9c':
        if args.arm != 'BASE':
            raise SystemExit('t9c is the BASE-arm scratch projection (key absent); arm must be BASE')
        tuning = t9c_tuning(tuning, args.dry_run)
    if not args.dry_run:
        c.lower_priority()
    print(f'SA_CAPTURE_PLAN kind={args.kind} arm={args.arm} tree={args.tree} root={c.R} n={len(rows)}', flush=True)
    for row in rows:
        if args.kind == 'full':
            run_full(args, row, tuning)
        else:
            run_capture(args, row, tuning)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
