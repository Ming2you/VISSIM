# a1_table.py - A1 result table (rule COMPARE_RULE_A1_FULL.md, part C). Reads only tool outputs + membership/geometry files.
# usage: python -B a1_table.py [--smoke]
# Columns: A1, LNC, A1 - LNC, codex joint, codex NC, joint - NC, A1 - joint. Codex integration form 0-8100 s (main),
# ours form 0-8100 s (link cells only, side table). 4b pair difference = first-observation difference (main);
# native - NC level (route A / route B) as reference. No verdict words.
import json, sys

SMOKE = '--smoke' in sys.argv
SFX = '_smoke' if SMOKE else ''
W0 = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/codex_handoff/work'
F = W0 + '/a1/full'
B = 'D:/VISSIM_handoff/20261024'
# ---- partition: verbatim from work/rawcheck/metrics.py (b524b51b...) ----
inside = set(json.load(open(f"{B}/derived/omega_membership_exact.json", encoding="utf-8"))["inside_links"])
geo = json.load(open(f"{B}/code/diagnostics/sdmpc_n31_20260924/integration_20260926/selected/port_gain/geometry.json", encoding="utf-8"))
chain = {str(x["link"]): r for r, rows in geo["chains"].items() for x in rows}
on = {str(b["connector"]): b["road"] for b in geo["boundaries"] if b["kind"] == "ramp"}
off = {str(b["connector"]) for b in geo["boundaries"] if b["kind"] == "offramp"}
S7 = {"74", "10699", "2", "10613", "119", "10702", "24"}
S19 = S7 | {"10484", "10490", "10639", "10681", "10481", "10483", "10643", "10682", "129", "31", "68", "70"}
UPSTREAM = {"70": "FW_E", "68": "FW_E", "129": "FW_E", "31": "FW_E", "124": "FW_W", "32": "FW_W", "121": "FW_W", "69": "FW_W"}


def parts(res, alt=False):
    p = {k: 0.0 for k in ("FW_E", "FW_W", "onramps_E", "onramps_W", "urban_roads", "offramps", "outside")}
    for link, v in res.items():
        if link not in inside:
            g = "outside"
        elif link in chain:
            g = chain[link]
        elif link in on:
            g = "onramps_E" if on[link] == "FW_E" else "onramps_W"
        elif alt and link in UPSTREAM:
            g = "onramps_E" if UPSTREAM[link] == "FW_E" else "onramps_W"
        elif link in off:
            g = "offramps"
        else:
            g = "urban_roads"
        p[g] += v
    p["urban"] = p["urban_roads"] + p["offramps"]
    p["Omega701"] = p["FW_E"] + p["FW_W"] + p["onramps_E"] + p["onramps_W"] + p["urban"]
    p["Omega_minus_W_mainline"] = p["Omega701"] - p["FW_W"]
    p["whole_4a"] = p["Omega701"] + p["outside"]
    p["FW_E_7"] = sum(res.get(k, 0) for k in S7)
    p["local_19"] = sum(res.get(k, 0) for k in S19)
    return p
# ---- end verbatim ----


prev = set(json.load(open(f"{B}/derived/omega_membership_exact.json", encoding="utf-8"))["controlled_intersection_expansion"]["previous_inside_links"])
assert prev <= inside and len(prev) == 635 and len(inside) == 701
SCAN = {c: W0 + '/rawcheck/scan/' + c + '.json' for c in ('nc', 'joint', 'lnc')}
SCAN['a1'] = F + '/scan' + SFX + '/a1.json'
LR = {c: json.load(open(p))['link_residence_veh_h'] for c, p in SCAN.items()}
MET = json.load(open(F + '/metrics_out_a1' + SFX + '.json'))
U = json.load(open(F + '/unins_a1' + SFX + '.json'))
U2 = json.load(open(W0 + '/rawcheck/uninserted2_out.json'))
OURS = json.load(open(F + '/ours_a1' + SFX + '.json'))
NC4B = {'A': U2['nc_4b_routeA'], 'B': U2['nc_4b_routeB']}
checks = {}


def cells(lr, alt_lr=None):
    p = parts(lr); q = parts(lr, alt=True)
    o635 = sum(v for k, v in lr.items() if k in prev)
    return {'Omega701': p['Omega701'], 'Omega635': o635, 'Omega701_minus_635': p['Omega701'] - o635, 'link66': lr.get('66', 0.0),
            'a4': p['whole_4a'], 'FW_E7': p['FW_E_7'], 'local19': p['local_19'],
            'urban_roads_codex': p['urban_roads'], 'urban_roads_ours': q['urban_roads'],
            'onramps_E_codex': p['onramps_E'], 'onramps_W_codex': p['onramps_W'], 'onramps_E_ours': q['onramps_E'], 'onramps_W_ours': q['onramps_W'],
            'offramps': p['offramps'], 'FW_W': p['FW_W'], 'outside_links': p['outside']}


L = {c: cells(LR[c]) for c in LR}
# cross-checks against the pinned metrics output and between scans
checks['parts_vs_metrics_a1_max_abs'] = max(abs(parts(LR[c])[k] - MET['codex_rule'][c][k]) for c in LR for k in MET['codex_rule'][c])
checks['alt_vs_metrics_a1_max_abs'] = max(abs(parts(LR[c], alt=True)[k] - MET['alt_rule'][c][k]) for c in LR for k in MET['alt_rule'][c])
checks['lnc_vs_nc_link_max_abs'] = max(abs(LR['lnc'].get(k, 0) - LR['nc'].get(k, 0)) for k in set(LR['lnc']) | set(LR['nc']))
checks['ours_codexform_vs_scan_max_abs'] = {c: max(abs(OURS['runs'][c]['codex'].get(k, 0) - LR[c].get(k, 0)) for k in set(OURS['runs'][c]['codex']) | set(LR[c]))
                                           for c in ('a1', 'joint', 'lnc')}
# 4b levels and pair differences
b4 = {'a1': U['native']['a1']['delay_latent_veh_h'], 'joint': U['native']['joint']['delay_latent_veh_h'], 'lnc_A': NC4B['A'], 'lnc_B': NC4B['B']}
checks['native_to_sec'] = {c: U['native'][c]['to'] for c in U['native']}


def levels(c, b):
    x = dict(L[c]); x['b4'] = b; x['four'] = x['a4'] + b
    for om in ('Omega701', 'Omega635'):
        x['out_a_' + om] = x['four'] - x[om]; x['out_b_' + om] = x['a4'] - x[om]
    return x


LEV = {'a1': levels('a1', b4['a1']), 'lnc_A': levels('lnc', b4['lnc_A']), 'lnc_B': levels('lnc', b4['lnc_B']),
       'joint': levels('joint', b4['joint']), 'nc_A': levels('nc', b4['lnc_A']), 'nc_B': levels('nc', b4['lnc_B'])}


def pair(a, b, fo_key):
    d = {k: L[a][k] - L[b][k] for k in L[a]}
    fo = U[fo_key]
    d['b4_first_obs'] = fo['total']
    d['b4_1098'] = fo['l1098_link74']; d['b4_1099'] = fo['l1099_link26']; d['b4_urban'] = fo['other']
    d['four'] = d['a4'] + d['b4_first_obs']
    for om in ('Omega701', 'Omega635'):
        d['out_a_' + om] = d['four'] - d[om]; d['out_b_' + om] = d['a4'] - d[om]
    return d


P = {'a1-lnc': pair('a1', 'lnc', 'a1-lnc'), 'joint-nc': pair('joint', 'nc', 'joint-nc_raw'), 'a1-joint': pair('a1', 'joint', 'a1-joint')}
P['a1-lnc']['b4_native_minus_ncA'] = b4['a1'] - b4['lnc_A']; P['a1-lnc']['b4_native_minus_ncB'] = b4['a1'] - b4['lnc_B']
P['joint-nc']['b4_native_minus_ncA'] = b4['joint'] - b4['lnc_A']; P['joint-nc']['b4_native_minus_ncB'] = b4['joint'] - b4['lnc_B']
P['a1-joint']['b4_native_diff'] = b4['a1'] - b4['joint']
PCT = {pk: {k: 100.0 * P[pk][k] / LEV['lnc_B'][k] for k in ('Omega701', 'Omega635', 'a4', 'FW_E7', 'local19', 'urban_roads_codex', 'urban_roads_ours', 'four')
            if k in P[pk] and LEV['lnc_B'].get(k)} for pk in ('a1-lnc', 'joint-nc')}
# ours form 0-8100 (link cells), NC = LNC (same data rows as codex NC)
OL = {c: cells(OURS['runs'][c]['ours']) for c in ('a1', 'joint', 'lnc')}
OP = {'a1-lnc': {k: OL['a1'][k] - OL['lnc'][k] for k in OL['a1']}, 'joint-lnc': {k: OL['joint'][k] - OL['lnc'][k] for k in OL['joint']}}
for pk in OP:
    for om in ('Omega701', 'Omega635'):
        OP[pk]['out_b_' + om] = OP[pk]['a4'] - OP[pk][om]
out = {'smoke': SMOKE, 'checks': checks, 'b4_levels': b4, 'levels': LEV, 'pairs': P, 'pct_vs_nc_level_routeB': PCT,
       'ours_levels': OL, 'ours_pairs': OP, 'ours_windows': {c: OURS['runs'][c]['ours_window'] for c in OURS['runs']},
       'arrival_check': {k: U[k] for k in ('inserted_by_8100', 'inserted_by_8100_link74', 'inserted_by_8100_link26', 'inserted_by_8100_other',
                                           'A1099_8100', 'remain_err', 'lnc_equals_nc_raw_firstseen', 'validate_a1-joint', 'nc_U_0_8100_pathC_from_joint',
                                           'nc_U_0_8100_pathC_from_a1')}}
json.dump(out, open(F + '/a1_table' + SFX + '.json', 'w'), indent=1)
ROWS = ['Omega701', 'Omega635', 'Omega701_minus_635', 'link66', 'a4', 'b4', 'four', 'out_a_Omega701', 'out_b_Omega701', 'out_a_Omega635', 'out_b_Omega635',
        'FW_E7', 'local19', 'urban_roads_codex', 'urban_roads_ours', 'onramps_E_codex', 'onramps_W_codex', 'onramps_E_ours', 'onramps_W_ours']
print('checks', json.dumps(checks))
print('row'.ljust(20) + ''.join(h.rjust(11) for h in ('A1', 'LNC(B)', 'A1-LNC', 'joint', 'NC(B)', 'joint-NC', 'A1-joint')))
for k in ROWS:
    pk = 'b4_first_obs' if k == 'b4' else k
    print(k.ljust(20) + ''.join(('%11.1f' % v) for v in (LEV['a1'][k], LEV['lnc_B'][k], P['a1-lnc'][pk], LEV['joint'][k], LEV['nc_B'][k], P['joint-nc'][pk],
                                                         P['a1-joint'][pk])))
for k in ('b4_1098', 'b4_1099', 'b4_urban'):
    print(k.ljust(20) + ' ' * 22 + '%11.1f' % P['a1-lnc'][k] + ' ' * 22 + '%11.1f' % P['joint-nc'][k] + '%11.1f' % P['a1-joint'][k])
