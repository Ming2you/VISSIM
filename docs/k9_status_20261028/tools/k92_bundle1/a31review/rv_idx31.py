"""ReviewDeclare A31: the amended _seed47_path on the REAL sealed file names, from the seal indexes OUTSIDE the sealed
root (OK2/commit/K9-2-{0,1,2,3}/sealed_s47_index.json 'inventory' keys, OK2/a27/sealed_index.json runs,
OK2/a30/sealed_k92t_index.json files).  No file under the sealed root is opened or listed; no record value is read.
Output: counts only (RV31/out/rv_idx31.json); no path, no name is printed or written.

Counts: files per top; files named exactly k92_record.json per top; files whose name contains 'record' but is not
exactly k92_record.json; files named k92_vissim_ref.json; for the k92_record.json paths (SEALED/<top>/<rel>, also in
the lp() long-path form): new-rule s47 count, old-rule s47 count, and the count of records whose relative path has
an s47 piece by an independent piece split (relative to SEALED/<top>'s parent = SEALED).
"""
import importlib.util
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
KB = HERE.parent
AD31 = KB / 'a31decl'
OUT = HERE / 'out' / 'rv_idx31.json'
OK2 = Path(r'D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1')
TOPS = ('K9-2-0', 'K9-2-1', 'K9-2-2', 'K9-2-3')


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


NEW = load(AD31 / 'k92t31_judge.py', 'rv_new_judge')
OLD = load(AD31 / 'base' / 'k92t30_judge.py', 'rv_old_judge')
SEALED = str(NEW.SEALED)


def piece47(p):
    p = p.lower()
    return p == 's47' or p.endswith('_s47') or '_s47_' in p or p.startswith('s47_')


def main():
    res = {'schema': 'rv31-idx/v1', 'tops': {}, 'other': {}}
    tot = {'files': 0, 'records': 0, 'new': 0, 'new_lp': 0, 'old': 0, 'rel_piece': 0, 'record_like_other': 0,
           'vissim_ref': 0}
    for top in TOPS:
        d = json.loads((OK2 / 'commit' / top / 'sealed_s47_index.json').read_text(encoding='utf-8'))
        root_ok = str(d.get('root')).replace('/', '\\').lower() == (SEALED + '\\' + top).replace('/', '\\').lower()
        inv = d.get('inventory') or {}
        c = {'root_is_sealed_top': root_ok, 'files': len(inv), 'records': 0, 'new': 0, 'new_lp': 0, 'old': 0,
             'rel_piece': 0, 'record_like_other': 0, 'vissim_ref': 0}
        for rel in inv:
            name = rel.replace('\\', '/').split('/')[-1]
            if name == 'k92_vissim_ref.json':
                c['vissim_ref'] += 1
            if 'record' in name.lower() and name != 'k92_record.json':
                c['record_like_other'] += 1
            if name != 'k92_record.json':
                continue
            c['records'] += 1
            full = SEALED + '\\' + top + '\\' + rel.replace('/', '\\')
            c['new'] += bool(NEW._seed47_path(full))
            c['new_lp'] += bool(NEW._seed47_path('\\\\?\\' + full))
            c['old'] += bool(OLD._seed47_path(full))
            c['rel_piece'] += any(piece47(p) for p in ([top] + rel.replace('\\', '/').split('/')))
        res['tops'][top] = c
        for k in tot:
            tot[k] += c[k]
    a27 = json.loads((OK2 / 'a27' / 'sealed_index.json').read_text(encoding='utf-8'))
    a30 = json.loads((OK2 / 'a30' / 'sealed_k92t_index.json').read_text(encoding='utf-8'))
    res['other'] = {'a27_runs': len(a27.get('runs') or []),
                    'a27_record_named': sum(1 for r in a27.get('runs') or []
                                            if 'record' in str(r.get('stdout_file', '')).lower()),
                    'k92t_files': len(a30.get('files') or []),
                    'k92t_record_named': sum(1 for f in a30.get('files') or [] if 'record' in str(f.get('name')).lower()),
                    'k92t_tops_after': a30.get('tops_after')}
    res['total'] = tot
    res['expect'] = {'records': 134, 'new': 45, 'old': 134, 'by_top_records': {'K9-2-0': 26, 'K9-2-1': 54,
                                                                                  'K9-2-2': 54, 'K9-2-3': 0}}
    res['ok'] = (tot['records'] == 134 and tot['new'] == 45 and tot['new_lp'] == 45 and tot['old'] == 134
                 and tot['rel_piece'] == 45 and all(res['tops'][t]['records'] == n
                                                    for t, n in res['expect']['by_top_records'].items())
                 and all(res['tops'][t]['root_is_sealed_top'] for t in TOPS))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=1, ensure_ascii=False) + '\n', encoding='utf-8', newline='\n')
    print('RV31_IDX ok=%s total=%s' % (res['ok'], json.dumps(tot, sort_keys=True)))
    return 0 if res['ok'] else 3


if __name__ == '__main__':
    raise SystemExit(main())
