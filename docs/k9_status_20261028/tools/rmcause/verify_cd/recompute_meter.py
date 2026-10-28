"""VERIFY_code-data (2026-10-24): fresh, read-only recompute of meter requests per decision.

Reads one run folder. Writes only under verify_cd/out. No replay, no VISSIM.
Logic follows c20aff1d code read directly:
  QP step (sdmpc.py:457, :823; sdmpc_pfo.py:55): d = clip(-g/proximal, lo, hi), center 0.
  Decode (sdmpc.py:399-401): nearest allowed green to ref+scale*z, tie -> reference.
  Line search (sdmpc.py:843-844; sdmpc_pfo.py:65-66): z + 0.5**k * step, k = 0,1,2.
"""
import csv, ctypes, glob, json, math, os, sys
from collections import defaultdict

try:
    ctypes.windll.kernel32.SetPriorityClass(ctypes.c_void_p(-1), 0x4000)
except Exception:
    pass

run = sys.argv[1].rstrip('/\\')
tag = sys.argv[2]
out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out')
os.makedirs(out_dir, exist_ok=True)
name = os.path.basename(run)
dec = os.path.join(run, 'decisions_' + name)
PROX = 10.0
METERS = ['RM_C10480', 'RM_C10482', 'RM_C10646', 'RM_C10644', 'RM_C10639', 'RM_C10681', 'RM_C10490', 'RM_C10484']


def decode(ref, scale, z, allowed):
    raw = ref + z * scale
    return min(allowed, key=lambda g: (abs(g - raw), abs(g - ref)))


def load(p):
    with open(p, encoding='utf-8-sig') as f:
        return json.load(f)


def csv_meter_rows(p):
    rows = {}
    with open(p, encoding='utf-8-sig', newline='') as f:
        for r in csv.DictReader(f):
            if r['kind'] == 'ramp_meter':
                meta = dict(x.split('=', 1) for x in r['metadata'].split(';') if '=' in x)
                rows[r['id']] = (float(r['rate_vph']), float(r['green_sec']), float(meta.get('group_rate_vph', 'nan')), r['sc_no'])
    return rows


times = sorted(int(os.path.basename(p)[7:13]) for p in glob.glob(os.path.join(dec, 'action_[0-9][0-9][0-9][0-9][0-9][0-9].json')))
summary = dict(run=run, tag=tag, decisions=len(times), joint_decisions=0)
rows_out = []
sel_counts = defaultdict(int)          # (block, green) -> count over meters x decisions
csv_counts = defaultdict(int)          # (rate, green) -> count
grad = {'pfo': defaultdict(list), 'central': defaultdict(list)}   # (block) -> list of (g, T, meter, iter)
decoded_non10 = {'pfo': [], 'central': []}
step_check = []                        # central recorded step vs recomputed
allowed_seen = defaultdict(int)
raw_res = []
lead = []
nufjac = defaultdict(float)
nufjac_other = []

for T in times:
    act = load(os.path.join(dec, 'action_%06d.json' % T))
    diag = act['diagnostics']
    sel = {m: [diag['rw_meter_green_' + m]] for m in METERS}
    seq = diag.get('sdmpc_prediction_sequence')
    if seq:
        for fut in seq['future']:
            for m in METERS:
                sel[m].append(fut['diagnostics']['rw_meter_green_' + m])
    for m in METERS:
        for b, g in enumerate(sel[m]):
            sel_counts[(b, g)] += 1
    cm = csv_meter_rows(os.path.join(dec, 'action_%06d.csv' % T))
    for m in METERS:
        rate, green, grp, sc = cm[m]
        csv_counts[(rate, green)] += 1
        if abs(rate - 90.0 * green) > 1e-9 or green != sel[m][0]:
            rows_out.append(dict(T=T, meter=m, issue='csv_mismatch', rate=rate, green=green, sel=sel[m][0]))
        if abs(grp - act['ramp_metering'][m]) > 1e-9:
            rows_out.append(dict(T=T, meter=m, issue='group_rate_mismatch', grp=grp, rm=act['ramp_metering'][m]))
    jp = os.path.join(dec, 'action_%06d.joint.json' % T)
    if not os.path.exists(jp):
        continue
    summary['joint_decisions'] += 1
    j = load(jp)
    s = j['selection']
    lead.append(dict(T=T, max_leader_candidates=j['options']['max_leader_candidates'], candidates=len(s['candidates']),
                     finite_neighbor_audit_performed=s.get('finite_neighbor_audit_performed')))
    co = s['coordinates']
    owner_ix = defaultdict(list)
    for i, c in enumerate(co):
        owner_ix[c['owner']].append(i)
    for c in co:
        if c['kind'] == 'meter':
            allowed_seen[(c['block'], tuple(c['allowed']), c['reference_value'])] += 1
    # PFO: own gradient only (sdmpc_pfo.py:54-55)
    for r in s['pfo_warm_start']['local_rows']:
        ix = owner_ix[r['owner']]
        for pos, i in enumerate(ix):
            c = co[i]
            if c['kind'] != 'meter':
                continue
            g = r['own_gradient'][pos]
            lo = (min(c['allowed']) - c['reference_value']) / c['scale']
            hi = (max(c['allowed']) - c['reference_value']) / c['scale']
            d = min(max(-g / PROX, lo), hi)
            grad['pfo'][c['block']].append((g, T, c['key'], r['iteration'], d))
            for k in range(3):
                gk = decode(c['reference_value'], c['scale'], (0.5 ** k) * d, c['allowed'])
                if gk != c['reference_value']:
                    decoded_non10['pfo'].append((T, c['key'], c['block'], r['iteration'], k, g, gk))
    # Central: own + external + price (sdmpc.py:821-823), recorded step
    for r in s['local_rows']:
        ix = owner_ix[r['owner']]
        for pos, i in enumerate(ix):
            c = co[i]
            if c['kind'] != 'meter':
                continue
            g = r['own_gradient'][pos] + r['externality_gradient'][pos] + r['price_gradient'][pos]
            lo = (min(c['allowed']) - c['reference_value']) / c['scale']
            hi = (max(c['allowed']) - c['reference_value']) / c['scale']
            d_re = min(max(-g / PROX, lo), hi)
            d = r['step'][pos]
            step_check.append(abs(d - d_re))
            grad['central'][c['block']].append((g, T, c['key'], r['iteration'], d, r['own_gradient'][pos], r['externality_gradient'][pos], r['price_gradient'][pos]))
            for k in range(3):
                gk = decode(c['reference_value'], c['scale'], (0.5 ** k) * d, c['allowed'])
                if gk != c['reference_value']:
                    decoded_non10['central'].append((T, c['key'], c['block'], r['iteration'], k, g, gk))
    gr = s['gradient_rows']; n = len(co)
    for it in range(len(gr) // n):
        for r, c in zip(gr[it * n:(it + 1) * n], co):
            if c['kind'] == 'meter':
                nufjac[(c['key'], c['block'])] = max(nufjac[(c['key'], c['block'])], abs(r['resource_derivatives_scaled'][1]) * 1000.0)
            else:
                nufjac_other.append(abs(r['resource_derivatives_scaled'][1]) * 1000.0)
    for u in s.get('iteration_dual_updates', []):
        raw_res.append(dict(T=T, iteration=u['iteration'], raw=u['raw_residual_scaled'], before=u['before'], after=u['after']))

summary['selected_green_counts'] = {f'block{b}_g{g}': n for (b, g), n in sorted(sel_counts.items())}
summary['csv_rate_green_counts'] = {f'{r}vph_{g}s': n for (r, g), n in sorted(csv_counts.items())}
summary['csv_issues'] = rows_out[:20]
summary['csv_issue_count'] = len(rows_out)
summary['allowed_sets'] = {f'block{b}_{list(a)}_ref{r}': n for (b, a, r), n in sorted(allowed_seen.items())}
for src in ('pfo', 'central'):
    for b in sorted(grad[src]):
        vals = grad[src][b]
        pos = [v for v in vals if v[0] > 0]
        top = max(vals, key=lambda v: v[0])
        summary[f'{src}_block{b}'] = dict(n=len(vals), positive=len(pos), positive_gt_1e12=sum(v[0] > 1e-12 for v in vals),
                                          positive_gt_1e9=sum(v[0] > 1e-9 for v in vals), above_0p5=sum(v[0] > 0.5 for v in vals),
                                          max_positive=top[0] if top[0] > 0 else None,
                                          max_at=dict(T=top[1], meter=top[2], iteration=top[3], step_z=top[4], step_green_sec=top[4] * 10,
                                                      **({'own': top[5], 'ext': top[6], 'price': top[7]} if src == 'central' else {})),
                                          max_abs_step_green_sec=max(abs(v[4]) * 10 for v in vals),
                                          min_gradient=min(v[0] for v in vals),
                                          nonzero_price=sum(1 for v in vals if src == 'central' and abs(v[7]) > 0))
    summary[f'{src}_decoded_non10'] = decoded_non10[src][:20]
    summary[f'{src}_decoded_non10_count'] = len(decoded_non10[src])
summary['central_step_vs_recomputed_max_abs_diff'] = max(step_check) if step_check else None
summary['dual_raw_residual_nuf_max'] = max((r['raw'][1] for r in raw_res), default=None)
summary['dual_raw_residual_np_max'] = max((r['raw'][0] for r in raw_res), default=None)
summary['dual_after_nonzero_decisions'] = len({r['T'] for r in raw_res if any(abs(x) > 0 for x in r['after'])})
summary['dual_raw_nuf_positive'] = [(r['T'], r['iteration'], r['raw']) for r in raw_res if r['raw'][1] > 0][:20]
summary['nuf_jacobian_meter_max_abs_veh_h_per_z'] = {f'{m}_b{b}': v for (m, b), v in sorted(nufjac.items())}
summary['nuf_jacobian_non_meter_max_abs_veh_h_per_z'] = max(nufjac_other) if nufjac_other else None
summary['leader'] = dict(max_leader_candidates=sorted({l['max_leader_candidates'] for l in lead}),
                         candidates=sorted({l['candidates'] for l in lead}),
                         finite_neighbor_audit_performed=sorted({str(l['finite_neighbor_audit_performed']) for l in lead}))
with open(os.path.join(out_dir, f'recompute_{tag}.json'), 'w', encoding='utf-8') as f:
    json.dump(summary, f, indent=1, ensure_ascii=False)
print(json.dumps({k: summary[k] for k in summary if k not in ('csv_issues',)}, indent=1, ensure_ascii=False)[:6000])
