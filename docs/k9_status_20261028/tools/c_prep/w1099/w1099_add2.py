# w1099_add2.py — W1099_RULE_ADD2 N1·N2 (데이터 뒤 선언; out/*.json 만 읽음, 가벼움)
import os, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, 'out')
SEEDS = (31, 41, 43); ARMS = ('b', 'nc', 'va')
R = {(a, s): json.load(open(os.path.join(OUT, '%s%d.json' % (a, s)), encoding='utf-8')) for a in ARMS for s in SEEDS}
def endspd(r):
    o = np.array(r['l26_occ'])[35:38, 0, :].sum(axis=0); sw = np.array(r['l26_spdw'])[35:38, 0, :].sum(axis=0)
    return np.where(o > 0, sw / np.where(o > 0, o, 1), np.nan)
res = {'N1': {}, 'N2': {}}
md = ['## N1 넣기 잡음 (300 s 칸, 두 런 모두 차로 1 끝 ≥ 70 km/h 인 칸만)', '', '| 짝 | 칸 수 | 평균 (대/300 s) | 표준편차 | 표준편차 × √7 |', '|---|---:|---:|---:|---:|']
for x, y, lab in (('b', 'nc', 'B − NC3'), ('va', 'nc', 'V-A − NC3'), ('b', 'va', 'B − V-A')):
    for s in SEEDS:
        ex, ey = endspd(R[(x, s)]), endspd(R[(y, s)])
        ix = np.array(R[(x, s)]['entrance']['n_ins_bin']); iy = np.array(R[(y, s)]['entrance']['n_ins_bin'])
        ks = [k for k in range(5, 30) if ex[k] >= 70 and ey[k] >= 70]
        d = (ix - iy)[ks].astype(float)
        sd = float(d.std(ddof=1)) if len(d) > 1 else float('nan')
        res['N1']['%s|%d' % (lab, s)] = {'bins': ks, 'n': len(ks), 'mean': float(d.mean()) if len(d) else None, 'sd': sd, 'rw7': sd * 7 ** 0.5}
        md.append('| %s v3c3-s%d | %d | %+.1f | %.1f | %.0f |' % (lab, s, len(ks), d.mean() if len(d) else float('nan'), sd, sd * 7 ** 0.5))
md += ['', '## N2 링크 26 차로 1 시공간 (100 m × 300 s; # < 20 km/h, + 20–40, . ≥ 40; 왼쪽 0 m → 오른쪽 3,818 m)', '']
for s in SEEDS:
    for a in ARMS:
        o = np.array(R[(a, s)]['l26_occ'])[:, 0, :]; sw = np.array(R[(a, s)]['l26_spdw'])[:, 0, :]
        md.append('**%s v3c3-s%d**' % ({'b': 'B', 'nc': 'NC3', 'va': 'V-A'}[a], s)); md.append('```')
        rows = []
        for k in range(6, 16):
            line = ''
            for p in range(39):
                if o[p, k] <= 0:
                    line += ' '
                else:
                    v = sw[p, k] / o[p, k]
                    line += '#' if v < 20 else ('+' if v < 40 else '.')
            rows.append(line)
            md.append('%5d %s' % (k * 300, line))
        res['N2']['%s%d' % (a, s)] = rows
        md.append('```')
json.dump(res, open(os.path.join(OUT, 'add2.json'), 'w', encoding='utf-8'))
open(os.path.join(OUT, 'add2.md'), 'w', encoding='utf-8').write('\n'.join(md) + '\n')
print('ADD2_DONE')
