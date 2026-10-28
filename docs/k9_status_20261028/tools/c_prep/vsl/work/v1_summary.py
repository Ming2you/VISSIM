# V1b (VSL_OFFLINE, data-after declaration): tabulate V1 output (VS/out/v1_dec_vsl.json) only.
# For each decision: written VSL; first-call secant rows of every VSL axis (own/ext/total, model dJ of
# 110->lower); positives; local QP VSL steps that round one legal step down (|step| >= 0.04545);
# price contribution on VSL axes; objectives. No model run.
import json, sys, collections
src, out = sys.argv[1], sys.argv[2]
d = json.load(open(src, encoding='utf-8'))
lines, js = [], []
for r in d['decisions']:
    if r.get('error'):
        lines.append(f"{r['arm']} {r['T']} ERROR {r['error']}")
        continue
    g0 = [g for g in r['grad_vsl_rows'] if g['call'] == 0]
    sec = [g for g in r['grad_vsl_rows'] if g['method'] == 'executable_secant_fallback']
    ad = [g for g in r['grad_vsl_rows'] if g['method'] != 'executable_secant_fallback']
    pos = [g for g in sec if g['total'] is not None and g['total'] > 1e-9]
    big = [g for g in sec if g['total'] is not None and g['total'] >= 0.4545]
    loc_down = [l for l in r['local_vsl_rows'] if l['rounds_to_lower']]
    loc_price = [l for l in r['local_vsl_rows'] if l['price'] and abs(l['price']) > 1e-9]
    loc_any = [l for l in r['local_vsl_rows'] if l['step'] and abs(l['step']) > 1e-9]
    s13 = {(g['call'], g['block']): g for g in r['grad_vsl_rows'] if g['key'] == 'FW_E__seg13'}
    row = dict(arm=r['arm'], T=r['T'], written_non110=r['vsl_written_non110'],
               n_secant=len(sec), n_ad=len(ad), n_pos=len(pos), n_ge_0_4545=len(big),
               max_secant_total=max((g['total'] for g in sec), default=None),
               min_secant_total=min((g['total'] for g in sec), default=None),
               pos_rows=[(g['call'], g['key'], g['block'], g['own'], g['external'], g['total'], g['dJ_lower_minus_anchor']) for g in pos],
               ad_rows=[(g['call'], g['key'], g['block'], g['anchor_z'], g['own'], g['external'], g['total']) for g in ad],
               seg13=[(c, b, s13[(c, b)]['method'][:6], s13[(c, b)]['anchor_z'], s13[(c, b)]['own'], s13[(c, b)]['external'],
                       s13[(c, b)]['total'], s13[(c, b)]['dJ_lower_minus_anchor']) for (c, b) in sorted(s13)],
               local_rounds_down=[(l['cap'], l['iteration'], l['key'], l['block'], l['own'], l['ext'], l['price'], l['step']) for l in loc_down],
               local_nonzero=[(l['cap'], l['iteration'], l['key'], l['block'], l['own'], l['ext'], l['price'], l['step']) for l in loc_any],
               local_price_rows=len(loc_price), max_abs_price=max((abs(l['price']) for l in loc_price), default=0.0),
               prices_scaled=r.get('prices_scaled'), dual_prices_used=sorted({tuple(x['prices_used']) for x in r.get('dual_updates', [])}),
               objective=r['objective'], candidates=[(c.get('np_cap'), c.get('nuf_target'), c.get('status'), c.get('accepted_steps'), c.get('objective')) for c in r['candidates']],
               trials=[(t['cap'], t['iteration'], t['objective'], t['feasible']) for t in r['trial_rows']],
               meter_audit=r.get('meter_audit_selected'), pfo_status=r['pfo']['status'],
               pfo_vsl_nonzero_own=[(p['iteration'], p['key'], p['block'], p['own']) for p in r['pfo']['vsl_rows'] if p['own'] and abs(p['own']) > 1e-12])
    js.append(row)
    lines.append(f"{row['arm']:12s} {row['T']:5d} out={row['written_non110'] or 110} sec={row['n_secant']} ad={row['n_ad']} pos={row['n_pos']} >=.4545={row['n_ge_0_4545']} "
                 f"max={row['max_secant_total']} min={row['min_secant_total']} down={len(loc_down)} price_rows={row['local_price_rows']} maxprice={row['max_abs_price']:.4f} "
                 f"obj held={row['objective']['held']} sel={row['objective']['selected']}")
    for x in row['seg13']:
        lines.append(f"      seg13 call{x[0]} b{x[1]} {x[2]} z={x[3]} own={x[4]} ext={x[5]} tot={x[6]} dJ={x[7]}")
    for x in row['local_rounds_down']:
        lines.append(f"      DOWN cap={x[0]} it={x[1]} {x[2]} b{x[3]} own={x[4]} ext={x[5]} price={x[6]} step={x[7]}")
    for x in row['pos_rows']:
        if x[1] != 'FW_E__seg13':
            lines.append(f"      POS call{x[0]} {x[1]} b{x[2]} own={x[3]} ext={x[4]} tot={x[5]} dJ={x[6]}")
json.dump(js, open(out + '.json', 'w', encoding='utf-8'), indent=1)
open(out + '.txt', 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
print('\n'.join(lines))
