"""VERIFY_VP extra reads, written AFTER the recompute (data-after, verifier, 2026-10-27 KST).  Read-only.

    python -B vv_extra.py <out.json>

(1) X1 (exit blocked veh, w450) of every hook file of all 21 jobs (every plan incl. REC and R1 AD), max per job.
(2) VISSIM (V-A FZP frames) speed of cell 18 minus cells 16-17 (Edie, w450) and the plant EXEC VS0' bias for all
    21 states; flags the states where VISSIM itself is slower at cell 18 by more than 5 km/h."""
import json
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True
VP = Path(r'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/'
          r'491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/vsl_plant')
OUT = Path(r'D:/VISSIM-merge/k8_gate_trees/vsl_plant/out')


def load(p):
    with open(p, 'r', encoding='utf-8-sig') as f:
        return json.load(f)


def vz(fr, T, cells):
    idx = [i for i, t in enumerate(fr['frames']) if T <= t < T + 450]
    N = sum(fr['N'][i][c] for i in idx for c in cells)
    SV = sum(fr['SV'][i][c] for i in idx for c in cells)
    return SV / N


def main():
    st = load(VP / 'decl' / 'VP_STATES.json')
    res = {'x1': [], 'cell18': []}
    for kind, lst in (('plant_A', st['probe_A']), ('plant_P', st['p1'])):
        for s in lst:
            jd = OUT / kind / ('%s_T%06d' % (s['label'], int(s['T'])))
            mx, n = 0.0, 0
            for f in sorted((jd / 'hooks').glob('vphook_*.json')):
                h = load(f)
                n += 1
                for b in h['blocks'].values():
                    for v in (b.get('exit_blocked_dt') or {}).values():
                        mx = max(mx, abs(float(v)) / 3600.0)
            res['x1'].append([kind, s['label'], int(s['T']), n, mx])
            fr = load(OUT / 'fzp_frames' / ('VA_%s.json' % s['label']))
            T = int(s['T'])
            d = vz(fr, T, [18]) - vz(fr, T, [16, 17])
            res['cell18'].append([kind, s['label'], T, round(vz(fr, T, [18]), 2), round(vz(fr, T, [16, 17]), 2), round(d, 2)])
    res['x1_max'] = max(x[4] for x in res['x1'])
    res['hook_files'] = sum(x[3] for x in res['x1'])
    res['cell18_vissim_slower_gt5'] = [x for x in res['cell18'] if x[5] < -5.0]
    outp = Path(sys.argv[1])
    tmp = outp.with_name(outp.name + '.tmp%d' % os.getpid())
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    os.replace(tmp, outp)
    print('VV_EXTRA x1_max=%s hook_files=%d cell18_slower_gt5=%s' % (res['x1_max'], res['hook_files'],
                                                                    res['cell18_vissim_slower_gt5']))


if __name__ == '__main__':
    main()
