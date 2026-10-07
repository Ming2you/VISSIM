"""Aggregate the hooked runs for G-EB-11 (d) and G-EB-13 (reads hook files only; writes one JSON).

    python -B sa_hookcount.py [--root R] [--out O] [--tree k86] [--base-tag hooks] [--precount PATH] [--dry-run]
        -> <out>/sa/hooks_<tree>.json  (schema k8-sa-hooks/v1)

Runs read (sa_capture.py full ... --tag <tag>, and the hooked TL3 job of sa_jobs.py --hooks):
  full/<tree>/<T>_<arm>_<tag>/hook/     T in 2700 4950, arm SAF (judging) and BASE (N-A9 attribution, N12 recount)
  jobs/<tree>/<label>/hook/              every job folder that has a hook/ directory
Per run:
  s3      every hook_<pid>.json of the chained K8-0b s3site: per site id the summed counters (reached, ev_struct,
          ev_exact_nonzero, ev_exact_zero, ev_exact_cancellation_level, ev_unevaluated, patched) and the anchor
          mismatches / patch errors (a run with a mismatch or an unpatched site is INVALID for the count)
  fold    every sahook_<pid>.json: SA fold sites (calls, values_*, ev_exact_nonzero, kept, dropped,
          dropped_abs_tangent_sum, abs_dir_tangent_sum, ev_unevaluated)
  cap     capacity reads of the W members, classified by CLASSIFY below (plant / diagnostic / leader_or_other)
  instrument (G-EB-13 validity, review r3 B-r3-4): fold_extra.hook_errors / patch_errors / errors and the install
          list fold_extra.patched of the sahook files, setup_errors (sa_*error_*.txt, setup_error_*.txt); top level
          line_patch_expected = capacity token lines per plant module source under the code root (line_patch_expected)
          (G-EB-11(d) / G-EB-13 validity, K8 amendment 7 §3, review N-r4-1): s3_extra / fold_extra .non_final = the
          hook files whose last record is not the exit record (final true), .final_files = the others
CLASSIFY (G-EB-13, PREDECL §3.2 B6; fixed here before any count exists):
  diagnostic  any frame of the caller chain is in DIAGNOSTIC_FUNCS
  plant       the nearest caller frame outside urban_queue_model is in a PLANT_MODULES module (UFA, LOR, LC, AFA, SA)
  leader_or_other   everything else, keyed by that nearest module:function (judged only through a manual review
                    file, sa_gates.py --leader-review: {module:function: {service_rate_in_cost: bool, reason}})."""
import glob
import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sa_common as sc  # noqa: E402

c = sc.c
PLANT_MODULES = ('urban_flow_accounting', 'lane_offramp_runtime', 'lane_coupling', 'area_freeway_accounting',
                 'stopline_approach')
PLANT_SOURCE_DIR = 'evaluation/controllers'          # where the PLANT_MODULES sources live under the code root
CAP_TOKENS = ('cap_flow_of[', 'movement_capacity_by_movement_veh_h')   # = sa_hooks/sitecustomize.py CAP_TOKENS
CAPFLOW_PATCH = 'urban_queue_model._movement_capacity_flow'            # sa_hooks install entry (suffix)
DIAGNOSTIC_FUNCS = ('urban_queue_model:movement_balance_summary', 'urban_flow_accounting:movement_balance_summary')
RULE3_SITES = ('_fold_service_residual', '_fold_city_share', '_merge_tiny_transfer')
REPORT_SITES = ('_skip_tiny_port_share', '_skip_tiny_city_moving_share')   # K8b-3 adds site 5 (report form)


def _parts(chain):
    return [p.strip() for p in chain.split(' < ') if p.strip()]


def classify_chain(chain):
    parts = _parts(chain)
    funcs = [':'.join(p.split(':')[:2]) for p in parts]
    if any(f in DIAGNOSTIC_FUNCS for f in funcs):
        return 'diagnostic', next(f for f in funcs if f in DIAGNOSTIC_FUNCS)
    for f in funcs:
        mod = f.split(':', 1)[0]
        if mod == 'urban_queue_model':
            continue
        return ('plant' if mod in PLANT_MODULES else 'leader_or_other'), f
    return 'leader_or_other', funcs[0] if funcs else '?'


def classify_cap(cap_reads):
    out = {'plant': defaultdict(float), 'diagnostic': defaultdict(float), 'leader_or_other': defaultdict(float),
           'table': dict(cap_reads.get('table') or {}), 'unresolved_lines': dict(cap_reads.get('unresolved_lines') or {})}
    for key, n in (cap_reads.get('_movement_capacity_flow') or {}).items():
        chain = key.split(' | ', 1)[0]
        cls, f = classify_chain(chain)
        out[cls][f + ' [_movement_capacity_flow]'] += n
    for key, n in (cap_reads.get('member') or {}).items():
        own, _, chain = key.partition(' | ')
        fields = own.split(':')            # mod : func : line : token : member
        mod, func = fields[:2]
        token = fields[3] if len(fields) > 3 else ''
        cls, f = classify_chain(f'{mod}:{func}:0 < ' + chain)
        out[cls][f + f' [{token}]'] += n
    return {k: (dict(v) if isinstance(v, defaultdict) else v) for k, v in out.items()}


def merge_counters(files, field):
    total = defaultdict(lambda: defaultdict(float))
    extra = {'anchor_mismatch': [], 'errors': [], 'patched_files': [], 'patched': set(), 'anchors': set(), 'files': 0,
             'hook_errors': 0, 'patch_errors': 0, 'non_final': [], 'final_files': 0}
    for path in files:
        r = json.loads(Path(path).read_text(encoding='utf-8'))
        extra['files'] += 1
        if r.get('final') is True:                     # amendment 7 §3: every hook file must hold its exit record
            extra['final_files'] += 1
        else:
            extra['non_final'].append(Path(path).name)
        for sid, row in (r.get(field) or {}).items():
            for k, v in row.items():
                if isinstance(v, (int, float)):
                    total[sid][k] += v
        ex = r.get('extra') or {}
        extra['anchor_mismatch'] += ex.get('anchor_mismatch') or []
        extra['errors'] += [e for e in (ex.get('errors') or []) if e]
        extra['patched_files'] += ex.get('patched_files') or []
        extra['patched'].update(str(p) for p in (ex.get('patched') or []))     # sa_hooks install list (B-r3-4)
        if ex.get('anchors'):
            extra['anchors'].add(str(ex['anchors']))
        for k, v in (r.get('counters') or {}).items():
            if k in ('hook_errors', 'patch_errors'):
                extra[k] += v
    extra['anchors'] = sorted(extra['anchors'])
    extra['patched'] = sorted(extra['patched'])
    return {k: dict(v) for k, v in total.items()}, extra


def token_lines(text):
    """Source lines the SA hook line-patches: a CAP_TOKENS token before any '#' (the rule of sa_hooks/sitecustomize.py
    patch_module)."""
    return sum(1 for line in text.splitlines() if any(tok in line.split('#', 1)[0] for tok in CAP_TOKENS))


def line_patch_expected(root):
    """Review r3 B-r3-4: per plant module, the number of capacity token lines in its source under the code root (the
    hooked run must hold a '<module>:<n> lines' patch for every module with n > 0); None when the file is absent."""
    out = {}
    for mod in PLANT_MODULES:
        p = Path(root) / PLANT_SOURCE_DIR / f'{mod}.py'
        out[mod] = token_lines(p.read_text(encoding='utf-8')) if p.is_file() else None
    return out


def run_record(hook_dir):
    s3_files = sorted(glob.glob(str(Path(hook_dir) / 'hook_*.json')))
    sa_files = sorted(glob.glob(str(Path(hook_dir) / 'sahook_*.json')))
    s3, s3x = merge_counters(s3_files, 'by_site')
    fold, foldx = merge_counters(sa_files, 'fold')
    cap = defaultdict(lambda: defaultdict(float))
    for path in sa_files:
        r = json.loads(Path(path).read_text(encoding='utf-8'))
        for kind, rows in (r.get('cap_reads') or {}).items():
            for k, v in rows.items():
                cap[kind][k] += v
    cap = {k: dict(v) for k, v in cap.items()}
    errors = sorted(glob.glob(str(Path(hook_dir) / 'sa_*error_*.txt')) + glob.glob(str(Path(hook_dir) / 'setup_error_*.txt')))
    return {'dir': str(hook_dir), 's3_files': len(s3_files), 'sa_files': len(sa_files), 's3_sites': s3, 's3_extra': s3x,
            'fold_sites': fold, 'fold_extra': foldx, 'cap_reads': cap, 'cap_classified': classify_cap(cap),
            'setup_errors': [Path(e).read_text(encoding='utf-8', errors='replace')[:300] for e in errors]}


def main():
    ap = c.parser(__doc__)
    ap.add_argument('--tree', default='k86')
    ap.add_argument('--base-tag', default='hooks', help='tag of the full runs (sa_capture.py full --tag)')
    ap.add_argument('--precount', help='N12 BASE pre-count hooks JSON of the K7 code (<K8>/r, P5b)')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()
    c.apply(args)
    dest = sc.sa_out() / f'hooks_{args.tree}.json'
    runs = {}
    for T in sc.DP_FULL_T:
        for arm in ('SAF', 'BASE'):
            d = sc.full_dir(args.tree, T, arm, args.base_tag) / 'hook'
            runs[f'full_{T}_{arm}'] = d
    for d in sorted(glob.glob(str(sc.sa_out() / 'jobs' / args.tree / '*' / 'hook'))):
        runs['job_' + Path(d).parent.name] = Path(d)
    if args.dry_run:
        for k, d in runs.items():
            print(f'DRY {k:40s} {"ok " if Path(d).is_dir() else "MISSING"} {d}')
        print('DRY ->', dest)
        return 0
    out = {'schema': 'k8-sa-hooks/v1', 'tree': args.tree, 'classify': {'plant_modules': PLANT_MODULES,
                                                                       'diagnostic_funcs': DIAGNOSTIC_FUNCS},
           'line_patch_expected': line_patch_expected(c.R), 'line_patch_root': str(c.R),
           'runs': {k: (run_record(d) if Path(d).is_dir() else {'missing': str(d)}) for k, d in runs.items()}}
    if args.precount:
        out['precount'] = {'path': args.precount, 'sha256': sc.sha256_file(args.precount),
                           'data': json.loads(Path(args.precount).read_text(encoding='utf-8'))}
    sc.write_json(dest, out)
    print('SA_HOOKCOUNT ->', dest)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
