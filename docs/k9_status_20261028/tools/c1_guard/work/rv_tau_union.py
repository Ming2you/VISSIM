# Review helper (read-only): OR-union of decision-time snapshot thresholds for the guard trigger tau.
# Input: out/fd_series.json (existing output). Output: work/rv_tau_union.json. No new scans.
import json, hashlib, sys
from pathlib import Path

G = Path(__file__).resolve().parents[1]
src = G / 'out' / 'fd_series.json'
raw = src.read_bytes()
J = json.loads(raw.decode('utf-8'))
bins = J['bins_start_s']
Ts = list(range(900, 8851, 150))
options = {
    'ga_10491ge12_or_129ge20': [('10491', 12), ('129', 20)],
    'gb_ga_or_127ge140': [('10491', 12), ('129', 20), ('127', 140)],
    'gc_10491ge8_or_129ge15': [('10491', 8), ('129', 15)],
    'only_10491ge12': [('10491', 12)],
    'only_129ge20': [('129', 20)],
}
out = {'source_sha256': hashlib.sha256(raw).hexdigest(), 'tool_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
       'note': 'decision-time FZP snapshot (T+0.1 s) link counts; thresholds data-after', 'runs': {}}
for run, r in J['runs'].items():
    sn = r['snap_decision']
    # O1 bins from the 300 s series: 26 lane-1 3,200-3,700 m speed < 40 km/h
    sp = r['l26_l1_end']
    speeds = sp.get('speed') if isinstance(sp, dict) else None
    row = {}
    for name, conds in options.items():
        hits = []
        for T in Ts:
            s = sn.get(str(T))
            if s is None:
                continue
            on = any(s.get(k) is not None and s[k] >= th for k, th in conds)
            if on:
                hits.append(T)
        row[name] = {'n_true': len(hits), 'first_T': hits[0] if hits else None, 'true_T': hits}
    out['runs'][run] = row
(G / 'work' / 'rv_tau_union.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
for run, row in out['runs'].items():
    print(run, {k: (v['n_true'], v['first_T']) for k, v in row.items()})
