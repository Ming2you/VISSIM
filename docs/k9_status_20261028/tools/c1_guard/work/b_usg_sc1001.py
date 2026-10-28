"""Read-only: codex urban storage guard observation for SC1001 in B decision JSONs (existing outputs)."""
import json, glob, os, sys, hashlib
out = {}
for seed in ('s31', 's41', 's43'):
    dd = f'D:/VISSIM_runs/20261026_codex_b_v3c3/{seed}/sdmpc/decisions_sdmpc31_sdmpc9000_{seed}'
    rows = []
    for f in sorted(glob.glob(dd + '/action_*.json')):
        T = int(os.path.basename(f)[7:13])
        if T < 900:
            continue
        t = open(f, encoding='utf-8').read()
        try:
            j = t.index('"joint_leader_selection"')
            i = t.index('"urban_storage_guard": {', j)
        except ValueError:
            rows.append(dict(T=T, missing=True)); continue
        u, _ = json.JSONDecoder().raw_decode(t, i + len('"urban_storage_guard": '))
        o = u['observation']
        lanes = [l for l in o['lanes'] if l['signal'] == 'SC1001' and l['link'] == '127']
        rec = [r for blk in u['blocks'] for r in (blk if isinstance(blk, list) else [blk])
               if isinstance(r, dict) and r.get('signal') == 'SC1001']
        rows.append(dict(T=T, scores=o['signals'].get('SC1001'),
                         lanes={str(l['lane']): [l['vehicles'], round(l['fill_fraction'], 4), l['crowded'],
                                                 l['all_receivers_full']] for l in lanes},
                         receipts=rec, any_constrained=sum(1 for blk in u['blocks'] for r in (blk if isinstance(blk, list) else [blk]) if isinstance(r, dict) and r.get('status') == 'constrained')))
    out[seed] = rows
p = sys.argv[1]
open(p, 'w', encoding='utf-8').write(json.dumps(out, indent=1))
print(hashlib.sha256(open(p, 'rb').read()).hexdigest())
for seed, rows in out.items():
    mx = {ln: max((r['lanes'].get(ln, [0, 0])[1] for r in rows if 'lanes' in r), default=None) for ln in ('1', '2', '3')}
    nz = [r['T'] for r in rows if r.get('scores') and any(v != 0 for v in r['scores'].values())]
    con = [r['T'] for r in rows if r.get('any_constrained')]
    print(seed, 'n', len(rows), 'max127fill', mx, 'SC1001 nonzero score T', nz, 'any-signal constrained T', con[:20])
