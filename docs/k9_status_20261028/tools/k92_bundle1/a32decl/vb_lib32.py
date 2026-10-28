"""K9-2 V-B helpers fixed by K8_PREDECLARATION_AMENDMENT_32 (sections 2, 3.5, 4.2).  Diagnostics only, never committed.
Standard library only at import; the K9-2-5 comparator module (k92_compare of the V-B tree) is passed in as `kc`.
BLIND form: paths, kinds, counts, sha and verdict words only -- no objective or prediction value is returned.

receipt_bytes(prev_T, csv_path, csv_size)
    The runner receipt <action>.json.applied exactly as scripts/run_real_world_stackelberg_controller.vbs:1281-1287
    writes it (CreateTextFile(path, True, True) = UTF-16 LE with BOM; WriteLine = CRLF): CStr(simSec), CStr(outCsvPath),
    CStr(size) -- three lines.  sdmpc.load_prices (sdmpc.py:513-533) reads it back.
write_receipt(out_json, out_csv)
    Writes <out_json>.applied only when <out_json>.sdmpc_pending exists (the VBS rule); never overwrites.
load_closed(path) / decision_type(closed, chain, T)
    The closed leaf list of VB_PRECHECK_STOP r2 section 2.2 (vb_closed_leaves.json, made by make_closed32.py).
reportonly(rep, dtype, closed)
    D-K9-62 report-only view of one compare() report of a chained OFF decision: the closed-list leaves of that decision
    type are taken out of the HARD differences (H2-H5 generalized paths) and of the unclassified entries; what is
    left is "outside the list".  No verdict.  H1 (CSV bytes) is never in the list.
zi_judge(kc, off_dir, on_dir, T, root)
    Amendment 32 section 3.5 zero-impact rule for one cell (hook off vs hook on, same prepared folder, same output
    paths): PASS iff the CSV bytes are equal, kc.compare(...) verdict is PASS, the progress last record is the same,
    and every leaf that differs between the two N-normalized action JSONs (kc.norm / kc.deep_diff) is a wall-clock
    leaf by kc.is_f3 (kind value/type, last key one of the 55 L_T names, numbers / ISO times / both null)."""
import hashlib
import json
from pathlib import Path

CLOSED_SCHEMA = 'k92vb-closed-leaves/v1'
TYPES = ('NN', 'SN', 'SS')
CAP_HARD = 80          # k92_compare keeps at most 80 generalized paths per HARD group
CAP_UNCL = 200         # and at most 200 unique unclassified entries


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


# ------------------------------------------------------------------------------------------------ receipt
def receipt_bytes(prev_T, csv_path, csv_size):
    if isinstance(prev_T, bool) or not isinstance(prev_T, int) or prev_T < 0:
        raise ValueError('prev_T must be a non-negative int (CStr of the integer decision time)')
    if isinstance(csv_size, bool) or not isinstance(csv_size, int) or csv_size < 0:
        raise ValueError('csv_size must be a non-negative int')
    text = '%d\r\n%s\r\n%d\r\n' % (prev_T, str(csv_path), csv_size)
    return b'\xff\xfe' + text.encode('utf-16-le')


def write_receipt(out_json, out_csv):
    out_json, out_csv = Path(out_json), Path(out_csv)
    pending = Path(str(out_json) + '.sdmpc_pending')
    target = Path(str(out_json) + '.applied')
    if not pending.is_file():
        return None
    if target.exists():
        raise SystemExit('receipt already exists: %s' % target)
    stem = out_json.name
    if not (stem.startswith('action_') and stem.endswith('.json') and stem[7:-5].isdigit()):
        raise SystemExit('unexpected action file name: %s' % stem)
    prev_T = int(stem[7:-5])
    data = receipt_bytes(prev_T, str(out_csv), out_csv.stat().st_size)
    target.write_bytes(data)
    return {'path': str(target), 'sha256': sha256_bytes(data), 'lines': [str(prev_T), str(out_csv),
                                                                         str(out_csv.stat().st_size)]}


# ------------------------------------------------------------------------------------------------ closed list
def load_closed(path):
    doc = json.loads(Path(path).read_text(encoding='utf-8'))
    if doc.get('schema') != CLOSED_SCHEMA or sorted(doc.get('types', {})) != sorted(TYPES):
        raise SystemExit('not a closed leaf list: %s' % path)
    return doc


def decision_type(closed, chain, T):
    for d in closed['decisions']:
        if d['chain'] == chain and int(d['T']) == int(T):
            return d['type']
    return None


def reportonly(rep, dtype, closed):
    leaves = closed['types'][dtype]['leaves']
    hard_list = {x['path'] for x in leaves if x['hard']}
    soft_list = {x['path'] for x in leaves if not x['hard']}
    out = {'dtype': dtype, 'verdict_reference_only': rep.get('verdict'), 'hard_verdict_reference_only':
           rep.get('hard_verdict'), 'incomplete': rep.get('verdict') == 'INCOMPLETE', 'why': rep.get('why')}
    if out['incomplete']:
        out.update(outside_n=None, sentence='비교가 INCOMPLETE입니다(출력 없음 또는 N 뒤 키 충돌): %s' % rep.get('why'))
        return out
    out['h1_csv_same'] = bool((rep.get('H1') or {}).get('same'))
    in_hard, out_hard, truncated = [], [], []
    for g in ('H2', 'H3', 'H4', 'H5'):
        blk = rep.get(g) or {}
        paths = list(blk.get('diff_paths_generalized') or [])
        if len(paths) >= CAP_HARD:
            truncated.append(g)
        for p in paths:
            (in_hard if p in hard_list else out_hard).append({'group': g, 'path': p})
    in_soft, out_soft = [], []
    uncl = list(rep.get('unclassified') or [])
    counted = sum(int(u.get('count') or 0) for u in uncl)
    if len(uncl) >= CAP_UNCL or counted != int(rep.get('unclassified_n') or 0):
        truncated.append('unclassified')
    for u in uncl:
        row = {'path': u.get('path'), 'kind': u.get('kind'), 'why': u.get('why'), 'count': u.get('count')}
        (in_soft if u.get('path') in soft_list else out_soft).append(row)
    seen = {x['path'] for x in in_hard} | {x['path'] for x in in_soft}
    out.update(in_list_hard=in_hard, in_list_unclassified=in_soft, outside_hard=out_hard, outside_unclassified=out_soft,
               truncated=truncated, listed_not_seen=sorted((hard_list | soft_list) - seen),
               allowed_counts=rep.get('allowed_counts') or {})
    n_out = len(out_hard) + len(out_soft) + (0 if out['h1_csv_same'] else 1) + len(truncated)
    out['outside_n'] = n_out
    if n_out == 0:
        out['sentence'] = '닫힌 목록 밖 차이 0개 (목록 안 HARD %d·미분류 %d 경로는 보고에서 뺌).' % (len(in_hard), len(in_soft))
    else:
        parts = []
        if not out['h1_csv_same']:
            parts.append('CSV 바이트 다름(H1)')
        parts += ['HARD %s %s' % (x['group'], x['path']) for x in out_hard]
        parts += ['미분류 %s (%s)' % (x['path'], x['why']) for x in out_soft]
        parts += ['목록 잘림(%s): 다 보지 못함' % t for t in truncated]
        out['sentence'] = '**닫힌 목록 밖 차이 %d개가 있습니다**: %s' % (n_out, '; '.join(parts))
    return out


# ------------------------------------------------------------------------------------------------ zero impact
def zi_judge(kc, off_dir, on_dir, T, root):
    off_dir, on_dir = Path(off_dir), Path(on_dir)
    s6 = '%06d' % int(T)
    res = {'T': int(T), 'off': str(off_dir), 'on': str(on_dir), 'checks': {}}
    files = {k: (off_dir / ('action_%s%s' % (s6, k)), on_dir / ('action_%s%s' % (s6, k))) for k in ('.csv', '.json')}
    if not all(a.is_file() and b.is_file() for a, b in files.values()):
        res['checks']['outputs_present'] = False
        res['pass'] = False
        return res
    res['checks']['outputs_present'] = True
    res['checks']['csv_bytes_same'] = sha256_file(files['.csv'][0]) == sha256_file(files['.csv'][1])
    rep = kc.compare(off_dir, on_dir, int(T), Path(root), keyed=None, old_root=Path(root), label='zi')
    res['compare_verdict'] = rep.get('verdict')
    res['checks']['compare_pass'] = rep.get('verdict') == 'PASS'
    po = kc.progress_last(off_dir / ('action_%s.joint.progress.jsonl' % s6))
    pn = kc.progress_last(on_dir / ('action_%s.joint.progress.jsonl' % s6))
    res['checks']['progress_last_same'] = (po is kc.MISSING and pn is kc.MISSING) or po == pn
    A = kc.norm(json.loads(files['.json'][0].read_text(encoding='utf-8-sig')))
    B = kc.norm(json.loads(files['.json'][1].read_text(encoding='utf-8-sig')))
    diffs = []
    kc.deep_diff(A, B, '', diffs)
    wall, other = set(), []
    for p, kind, va, vb in diffs:
        if kc.is_f3(p, kind, va, vb):
            wall.add(kc.gen(p))
        else:
            other.append({'path': kc.gen(p), 'kind': kind})
    res['n_diff_leaves'] = len(diffs)
    res['wallclock_paths'] = sorted(wall)
    res['other_diffs'] = other[:200]
    res['checks']['only_wallclock'] = not other
    res['pass'] = all(res['checks'].values())
    return res
