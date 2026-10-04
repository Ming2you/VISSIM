"""Consolidate S3 counting runs (an_s3.json of each) into one per-site table (JSON + markdown rows).

    python -B table_s3.py --run "2700 REF=<dir>" --run "2700 M2ALL=<dir>" --run "4950 REF=<dir>" --run "2700 full=<dir>"
                          --out-json <file> [--out-md <file>]

K8-0b port of the scratch amend1/s3/tools/table_s3.py (sha256 e9e46d4ee6744cc7...): same cell keys, same
markdown layout; the run list and outputs are arguments, and site order/patterns come from s3site/sitecustomize.py
(SITES_K81; ids are shared with SITES_K82). The scratch table for the K7 code is amend1/s3/out/table_s3.json.
"""
import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
KEYS = ('reached', 'values_rdual', 'drop_float', 'drop_float_nonzero_primal', 'ev_struct', 'ev_exact_nonzero',
        'ev_exact_zero', 'ev_exact_cancellation_level', 'ev_unevaluated', 'drop_rdual0')
REN = {'SA:': 'SHA:'}  # report name: shared_approach.py = SHA (module "SA" is the OPT1 v2 lane FIFO)


def site_rows():
    src = (HERE / 's3site' / 'sitecustomize.py').read_text(encoding='utf-8')
    ns = {'os': __import__('os')}
    exec(src[src.index('SITES_K81 = ['):src.index('def _setup_hooks')], ns)
    return ns['SITES_K81'], ns['SITES_K82']


def build(runs):
    data = {name: json.load(open(Path(p) / 'an_s3.json', encoding='utf-8')) for name, p in runs}
    sites = sorted(set().union(*(d['by_site'] for d in data.values())))
    table = {}
    for site in sites:
        table[site] = {name: {k: d['by_site'].get(site, {}).get(k, 0) for k in KEYS} for name, d in data.items()}
    return {'runs': [n for n, _ in runs], 'run_dirs': {n: str(p) for n, p in runs}, 'table': table,
            'totals': {n: d['totals'] for n, d in data.items()},
            'sweeps': {n: d['sweeps'] for n, d in data.items()},
            'validation': {n: d.get('sweep_validation') for n, d in data.items()},
            'processes': {n: d.get('processes') for n, d in data.items()}}


def markdown(out):
    k81, _ = site_rows()
    runs = out['runs']
    lines = ['| 위치 | 패턴 | 묶음 | ' + ' | '.join(f'{n} 도달/Dual/구조사건/정확≠0' for n in runs) + ' |',
             '|---|---|---|' + '---|' * len(runs)]
    for s in k81:
        sid = name = s[0]
        for a, b in REN.items():
            if name.startswith(a):
                name = b + name[len(a):]
        cells = []
        for n in runs:
            r = out['table'].get(sid, {}).get(n, {})
            cells.append(f"{r.get('reached', 0):,} / {r.get('values_rdual', 0):,} / {r.get('ev_struct', 0)} / "
                         f"{r.get('ev_exact_nonzero', 0)}")
        lines.append(f'| {name} | `{s[3]}` | {s[6]} | ' + ' | '.join(cells) + ' |')
    return '\n'.join(lines) + '\n'


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--run', action='append', required=True, help='"<name>=<run dir with an_s3.json>"')
    ap.add_argument('--out-json', required=True)
    ap.add_argument('--out-md')
    a = ap.parse_args()
    runs = [tuple(x.split('=', 1)) for x in a.run]
    out = build(runs)
    Path(a.out_json).write_text(json.dumps(out, indent=1), encoding='utf-8')
    md = markdown(out)
    if a.out_md:
        Path(a.out_md).write_text(md, encoding='utf-8')
    print(md)
