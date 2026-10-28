# A0b: list every command CSV row that differs between a replay and the codex record (A0-CMP-1 R1 detail).
# usage: a0b_rows.py T [label] [out_json]   -> default out/<label>/T<T>/rows_vs_recorded.json; prints a one-line summary.
# Rows are compared in file order (the adapter writes a fixed order; identity columns are checked, not assumed).
import csv, json, sys
T = int(sys.argv[1]); LABEL = sys.argv[2] if len(sys.argv) > 2 else 'a0b_hsw'
OUT = sys.argv[3] if len(sys.argv) > 3 else None
t6 = '%06d' % T
A0 = 'D:/VISSIM-merge/k8_gate_trees/codexhandoff/a0'
DEC = 'decisions_sdmpc31_sdmpc8100_s29'
REC = 'D:/VISSIM_handoff/20261024/raw/joint/sdmpc/' + DEC + '/action_' + t6 + '.csv'
REP = A0 + '/out/' + LABEL + '/T' + t6 + '/files/sdmpc/' + DEC + '/action_' + t6 + '.csv'
IDCOLS = ('kind', 'id', 'dsd_no', 'sc_no', 'link', 'lane')
a = list(csv.DictReader(open(REP, encoding='utf-8')))
b = list(csv.DictReader(open(REC, encoding='utf-8')))
res = {'T': T, 'label': LABEL, 'rows_replay': len(a), 'rows_record': len(b), 'header_equal': None, 'identity_mismatch': [],
       'differing_rows': [], 'differing_rows_by_kind': {}, 'max_abs_delta_by_kind_col': {}, 'nonnumeric_diffs': 0,
       'signal_green_diff_ge_1s': 0, 'ramp_meter_rate_or_green_diff': 0, 'vsl_speed_diff': 0}
res['header_equal'] = (list(a[0].keys()) if a else []) == (list(b[0].keys()) if b else [])
for i, (x, y) in enumerate(zip(a, b)):
    idx = {k: x.get(k) for k in IDCOLS}
    if any(x.get(k) != y.get(k) for k in IDCOLS):
        res['identity_mismatch'].append({'row': i + 1, 'replay': idx, 'record': {k: y.get(k) for k in IDCOLS}})
        continue
    cols = []
    for k in x:
        if x[k] == y[k]:
            continue
        try:
            d = float(x[k]) - float(y[k])
            cols.append({'col': k, 'replay': x[k], 'record': y[k], 'delta': round(d, 6)})
            key = x['kind'] + ':' + k
            res['max_abs_delta_by_kind_col'][key] = round(max(res['max_abs_delta_by_kind_col'].get(key, 0.0), abs(d)), 6)
            if x['kind'] in ('signal', 'signal_sg') and k.endswith('_green') and abs(d) >= 1.0:
                res['signal_green_diff_ge_1s'] += 1
            if x['kind'] == 'ramp_meter' and k in ('rate_vph', 'green_sec'):
                res['ramp_meter_rate_or_green_diff'] += 1
            if x['kind'] == 'vsl' and k == 'speed_kph':
                res['vsl_speed_diff'] += 1
        except ValueError:
            cols.append({'col': k, 'replay': x[k], 'record': y[k], 'delta': 'nonnumeric'})
            res['nonnumeric_diffs'] += 1
    if cols:
        res['differing_rows'].append({'row': i + 1, **idx, 'cols': cols})
        res['differing_rows_by_kind'][x['kind']] = res['differing_rows_by_kind'].get(x['kind'], 0) + 1
res['n_differing_rows'] = len(res['differing_rows'])
res['sc_with_diff'] = sorted({r['sc_no'] for r in res['differing_rows'] if r['sc_no']}, key=lambda s: int(s))
res['ids_with_diff_nonsignal'] = sorted({r['id'] for r in res['differing_rows'] if r['kind'] not in ('signal', 'signal_sg')})
json.dump(res, open(OUT or (A0 + '/out/' + LABEL + '/T' + t6 + '/rows_vs_recorded.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps({k: res[k] for k in ('T', 'rows_replay', 'rows_record', 'header_equal', 'n_differing_rows', 'differing_rows_by_kind',
                                       'max_abs_delta_by_kind_col', 'signal_green_diff_ge_1s', 'ramp_meter_rate_or_green_diff', 'vsl_speed_diff',
                                       'nonnumeric_diffs', 'sc_with_diff', 'ids_with_diff_nonsignal')}, ensure_ascii=False), 'identity_mismatch', len(res['identity_mismatch']))
