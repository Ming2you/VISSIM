# VERIFY_NEXT: Omega701 / previous Omega635 sums from vn_fzp_scan link totals (read-only)
import json, os
V = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
p = 'D:/VISSIM-runtime-window264-recovery/sdmpc31_ca181e84_202610070539/diagnostics/repin_v3c3_review_20261001/urban_area263/approaches_only/membership.json'
m = json.loads(open(p, 'rb').read())
pm = m['previous_membership']
prev = pm.get('inside_links') if isinstance(pm, dict) else None
if prev is None and isinstance(pm, dict):
    for k, v in pm.items():
        if isinstance(v, list) and len(v) == 635: prev = v
print('previous_membership keys', list(pm.keys())[:20] if isinstance(pm, dict) else type(pm))
om701 = set(m['inside_links']); om635 = set(prev or [])
print('n701', len(om701), 'n635', len(om635), '635 subset of 701', om635 <= om701)
res = {}
for t in ['nc3_s31', 'rm_s31', 'va_s31', 'nc3_s41', 'rm_s41', 'va_s41', 'nc_64cf_s29', 'w264_64cf_s29', 'vsl_64cf_s29']:
    r = json.load(open(os.path.join(V, 'out', t + '.json'), encoding='utf-8'))
    lt = r['link_tot_frames']
    res[t] = {'om701': sum(n for L, n in lt.items() if L in om701) * 5 / 3600, 'om635': sum(n for L, n in lt.items() if L in om635) * 5 / 3600}
    print(t, 'Om701 %.1f Om635 %.1f' % (res[t]['om701'], res[t]['om635']))
json.dump(res, open(os.path.join(V, 'out', 'vn_omega.json'), 'w'), indent=1)
