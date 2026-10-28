"""VERIFY_code-data: per-decision x per-meter table for one run (read-only).
Columns: requested greens (block 0/1/2 from action JSON), decision CSV rate/green, run-level action CSV
green/readback, signal_readback.csv requested/readback rows for that SC at that second, and the largest
"tighten" gradient over iterations for PFO (own) and central (own+ext+price) at block 0, with the
recomputed decoded green (sdmpc.py:399-401 rule)."""
import csv, ctypes, glob, json, os, sys
from collections import defaultdict
try:
    ctypes.windll.kernel32.SetPriorityClass(ctypes.c_void_p(-1), 0x4000)
except Exception:
    pass
run, tag = sys.argv[1].rstrip('/\\'), sys.argv[2]
name = os.path.basename(run)
dec = os.path.join(run, 'decisions_' + name)
M = ['RM_C10480', 'RM_C10482', 'RM_C10646', 'RM_C10644', 'RM_C10639', 'RM_C10681', 'RM_C10490', 'RM_C10484']
runcsv = defaultdict(dict)
for r in csv.DictReader(open(os.path.join(run, f'action_{name}.csv'), encoding='utf-8-sig')):
    if r['kind'] == 'ramp_meter':
        runcsv[int(r['sim_sec'])][r['id']] = (float(r['rate_vph']), float(r['green_sec']), r['readback'], r['sc_no'])
rb = defaultdict(list)
for r in csv.DictReader(open(os.path.join(dec, 'signal_readback.csv'), encoding='utf-8-sig')):
    if r['sc_no'] in {str(9100 + i) for i in range(1, 9)}:
        rb[(int(r['sim_sec']), r['sc_no'])].append(r['requested_state'] + '/' + r['readback_state'])
red_rows = sum(1 for v in rb.values() for x in v if 'RED' in x)
out_rows = []
for p in sorted(glob.glob(os.path.join(dec, 'action_[0-9][0-9][0-9][0-9][0-9][0-9].json'))):
    T = int(os.path.basename(p)[7:13])
    a = json.load(open(p, encoding='utf-8-sig'))
    d = a['diagnostics']
    seq = (d.get('sdmpc_prediction_sequence') or {}).get('future', [])
    dc = {}
    for r in csv.DictReader(open(os.path.join(dec, 'action_%06d.csv' % T), encoding='utf-8-sig')):
        if r['kind'] == 'ramp_meter':
            dc[r['id']] = (float(r['rate_vph']), float(r['green_sec']))
    grads = {}
    jp = os.path.join(dec, 'action_%06d.joint.json' % T)
    if os.path.exists(jp):
        s = json.load(open(jp, encoding='utf-8-sig'))['selection']
        co = s['coordinates']; ix = defaultdict(list)
        for i, c in enumerate(co): ix[c['owner']].append(i)
        for src, rows in (('pfo', s['pfo_warm_start']['local_rows']), ('cen', s['local_rows'])):
            for r in rows:
                for pos, i in enumerate(ix[r['owner']]):
                    c = co[i]
                    if c['kind'] != 'meter' or c['block'] != 0: continue
                    g = r['own_gradient'][pos] + (r['externality_gradient'][pos] + r['price_gradient'][pos] if src == 'cen' else 0.0)
                    k = (src, c['key'])
                    grads[k] = max(grads.get(k, -1e300), g)
    for m in M:
        sc = runcsv[T][m][3]
        def dec_green(g):
            if g is None: return ''
            raw = 10.0 + 10.0 * max(min(-g / 10.0, 0.0), -0.2)
            return min([8, 9, 10], key=lambda x: (abs(x - raw), abs(x - 10)))
        gp, gc = grads.get(('pfo', m)), grads.get(('cen', m))
        out_rows.append(dict(T=T, meter=m, req_b0=d['rw_meter_green_' + m],
                             req_b1=seq[0]['diagnostics']['rw_meter_green_' + m] if seq else '',
                             req_b2=seq[1]['diagnostics']['rw_meter_green_' + m] if seq else '',
                             json_ramp_metering=a['ramp_metering'][m], dec_csv_rate=dc[m][0], dec_csv_green=dc[m][1],
                             run_csv_rate=runcsv[T][m][0], run_csv_green=runcsv[T][m][1], run_csv_readback=runcsv[T][m][2],
                             sc_no=sc, signal_readback=';'.join(rb.get((T, sc), [])),
                             pfo_b0_max_g='' if gp is None else '%.3e' % gp, pfo_b0_decoded=dec_green(gp),
                             cen_b0_max_g='' if gc is None else '%.3e' % gc, cen_b0_decoded=dec_green(gc)))
fn = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out', f'per_decision_{tag}.csv')
with open(fn, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=list(out_rows[0].keys())); w.writeheader(); w.writerows(out_rows)
print('rows', len(out_rows), 'decisions', len({r['T'] for r in out_rows}))
print('req_b0 values', sorted({r['req_b0'] for r in out_rows}), 'dec_csv', sorted({(r['dec_csv_rate'], r['dec_csv_green']) for r in out_rows}),
      'run_csv', sorted({(r['run_csv_rate'], r['run_csv_green'], r['run_csv_readback']) for r in out_rows}))
print('signal_readback meter rows total', sum(len(v) for v in rb.values()), 'RED rows', red_rows,
      'decision-time rows matched', sum(1 for r in out_rows if r['signal_readback']))
print('decoded non-10 pfo', sum(1 for r in out_rows if r['pfo_b0_decoded'] not in ('', 10)), 'cen', sum(1 for r in out_rows if r['cen_b0_decoded'] not in ('', 10)))
print('json group rate values', sorted({(r['meter'], r['json_ramp_metering']) for r in out_rows}))
