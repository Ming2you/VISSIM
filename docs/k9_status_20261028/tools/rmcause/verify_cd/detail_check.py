"""VERIFY_code-data detail pass (read-only): NUF slack, duals, per-meter |gradient| maxima, one focus decision.
Usage: python -B detail_check.py <run> <tag> [focusT]"""
import ctypes, glob, json, os, statistics, sys
from collections import defaultdict
try:
    ctypes.windll.kernel32.SetPriorityClass(ctypes.c_void_p(-1), 0x4000)
except Exception:
    pass
run, tag = sys.argv[1].rstrip('/\\'), sys.argv[2]
focus = int(sys.argv[3]) if len(sys.argv) > 3 else None
name = os.path.basename(run)
dec = os.path.join(run, 'decisions_' + name)
nuf_res, np_res, dual_dec_after, dual_dec_union, dual_max = [], [], 0, 0, 0.0
gmax = defaultdict(float)
focus_rows = None
rates = defaultdict(list)
for jp in sorted(glob.glob(os.path.join(dec, 'action_*.joint.json'))):
    T = int(os.path.basename(jp)[7:13])
    j = json.load(open(jp, encoding='utf-8-sig'))
    s = j['selection']
    fc = s['final_constraints']
    for m, v in (s['budget_initialization'].get('accepted_rate_veh_h_by_ramp') or {}).items():
        rates[m].append(v)
    nuf_res.append(fc['nuf']['residual']); np_res.append(fc['np']['residual'])
    a = u_ = False
    for u in s.get('iteration_dual_updates', []):
        if any(abs(x) > 0 for x in u['after']): a = True
        if any(abs(x) > 0 for x in u['after'] + u['prices_used']): u_ = True
        dual_max = max([dual_max] + [abs(x) for x in u['after'] + u['prices_used']])
    dual_dec_after += a; dual_dec_union += u_
    co = s['coordinates']; ix = defaultdict(list)
    for i, c in enumerate(co): ix[c['owner']].append(i)
    for src, rows in (('pfo', s['pfo_warm_start']['local_rows']), ('central', s['local_rows'])):
        for r in rows:
            for pos, i in enumerate(ix[r['owner']]):
                c = co[i]
                if c['kind'] != 'meter': continue
                g = r['own_gradient'][pos] + (r['externality_gradient'][pos] + r['price_gradient'][pos] if src == 'central' else 0.0)
                gmax[(src, c['key'])] = max(gmax[(src, c['key'])], abs(g))
    if focus == T:
        n = len(co); gr = s['gradient_rows']
        focus_rows = []
        for it in range(len(gr) // n):
            for r in gr[it * n:(it + 1) * n]:
                if r['kind'] == 'meter' and r['key'] == 'RM_C10490':
                    focus_rows.append(dict(iteration=it, block=r['block'], own=r['own'], external=r['external'], total=r['total'],
                                           dNUF_dz_veh_h=r['resource_derivatives_scaled'][1] * 1000.0))
        focus_rows.append(dict(predicted_rate_RM_C10490=s['budget_initialization']['accepted_rate_veh_h_by_ramp'].get('RM_C10490'),
                               final_rate=fc.get('physical_ramp_merge', {}).get('rate_veh_h_by_ramp', {}).get('RM_C10490')))
out = dict(tag=tag, decisions=len(nuf_res),
           nuf_residual_final=dict(median=statistics.median(nuf_res), max=max(nuf_res), negative=sum(x < 0 for x in nuf_res)),
           np_residual_final=dict(median=statistics.median(np_res), max=max(np_res)),
           dual_nonzero_decisions_after_only=dual_dec_after, dual_nonzero_decisions_after_or_used=dual_dec_union, max_abs_dual=dual_max,
           pfo_predicted_merge_by_ramp={m: dict(median=statistics.median(v), max=max(v), n=len(v), above_g8_1lane=sum(x > 1166.4 for x in v), above_g8_2lane=sum(x > 2332.8 for x in v)) for m, v in sorted(rates.items())},
           max_abs_meter_gradient={f'{s}:{m}': v for (s, m), v in sorted(gmax.items())}, focus=focus, focus_rows=focus_rows)
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out', f'detail_{tag}.json'), 'w'), indent=1)
print(json.dumps(out, indent=1))
