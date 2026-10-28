# -*- coding: utf-8 -*-
"""W264 decision-side time series (read-only). 2026-10-24 rmcause/o1o4.

Reads: action CSV (per decision block-0 green per meter, VSL rows),
       decisions/signal_readback.csv (realized meter GREEN/RED writes),
       decisions/vsl_readback.csv (DSD readback).
Writes: o1o4/work/decisions.json
"""
import csv, json, collections

RUN = 'D:/VISSIM-runs-window264-s29-9000-recovery-20261007/sdmpc'
ACT = RUN + '/action_sdmpc31_sdmpc9000_s29.csv'
DEC = RUN + '/decisions_sdmpc31_sdmpc9000_s29'
SC = {9101: 'RM_C10480', 9102: 'RM_C10482', 9103: 'RM_C10646', 9104: 'RM_C10644',
      9105: 'RM_C10639', 9106: 'RM_C10681', 9107: 'RM_C10490', 9108: 'RM_C10484'}
NB, BIN = 60, 150

green = collections.defaultdict(dict)
rate = collections.defaultdict(dict)
vsl = collections.defaultdict(dict)
for r in csv.DictReader(open(ACT, encoding='utf-8', errors='replace')):
    t = int(float(r['sim_sec']))
    if r['kind'] == 'ramp_meter':
        green[r['id']][t] = float(r['green_sec'])
        rate[r['id']][t] = float(r['rate_vph'])
    elif r['kind'] == 'vsl':
        vsl[(r['id'], r['dsd_no'])][t] = float(r['speed_kph'])

# realized meter state timeline from 'immediate' writes (state persists until next write)
ev = collections.defaultdict(list)
for r in csv.DictReader(open(DEC + '/signal_readback.csv', encoding='utf-8', errors='replace')):
    sc = int(r['sc_no'])
    if sc in SC and r['stage'] == 'immediate' and r['ok'] == '1':
        ev[SC[sc]].append((int(float(r['sim_sec'])), r['readback_state']))
real = {}
for m, lst in ev.items():
    lst.sort()
    g = [0.0] * NB
    state, t0 = 'GREEN', 0
    for t, s in lst + [(9000, 'END')]:
        if state == 'GREEN':
            for x in range(t0, t):
                b = x // BIN
                if b < NB:
                    g[b] += 1
        state, t0 = s, t
    real[m] = [round(v / BIN, 3) for v in g]

# VSL readback for DSD 63-66 (any class): distinct values per 150 s bin
vr = collections.defaultdict(set)
for r in csv.DictReader(open(DEC + '/vsl_readback.csv', encoding='utf-8', errors='replace')):
    if r['dsd_no'] in ('63', '64', '65', '66') and r['ok'] == '1':
        vr[int(float(r['sim_sec'])) // BIN].add(float(r['readback_distribution_no']))
vsl_e13 = {}
for (i, d), s in vsl.items():
    if d in ('63', '64', '65', '66'):
        for t, v in s.items():
            vsl_e13.setdefault(t, set()).add(v)
non110 = sorted({(i, t, v) for (i, d), s in vsl.items() for t, v in s.items() if v != 110.0})
out = {
    'meters': sorted(green),
    'green_by_decision': {m: {str(t): g for t, g in sorted(d.items())} for m, d in green.items()},
    'rate_by_decision': {m: {str(t): g for t, g in sorted(d.items())} for m, d in rate.items()},
    'realized_green_frac_150': real,
    'vsl_dsd63_66_cmd': {str(t): sorted(v) for t, v in sorted(vsl_e13.items())},
    'vsl_dsd63_66_readback_by_bin': {str(b * BIN): sorted(v) for b, v in sorted(vr.items())},
    'vsl_non110_ids': sorted({(i) for (i, t, v) in non110}),
    'vsl_non110_times': [min(t for _, t, _ in non110), max(t for _, t, _ in non110)] if non110 else None,
}
json.dump(out, open('C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/rmcause/o1o4/work/decisions.json', 'w', encoding='utf-8'), indent=1)
print('meters', out['meters'])
print('vsl non110 ids', out['vsl_non110_ids'], out['vsl_non110_times'])
for m in out['meters']:
    d = green[m]
    print(m, ' '.join(f"{int(d.get(t, -1))}" for t in range(900, 9000, 150)))
print('realized green frac (150 s bins from 900 s):')
for m in out['meters']:
    print(m, ' '.join(f"{x:.2f}" for x in real.get(m, [])[6:]))
print('vsl readback by bin', {k: v for k, v in out['vsl_dsd63_66_readback_by_bin'].items() if int(k) >= 1650 and int(k) <= 5850})
