# -*- coding: utf-8 -*-
"""gd_selftest.py — synthetic FZP check of gd_scan.py (no lock, no real FZP). Writes only under work/selftest_gd/."""
import json
import os
import subprocess
import sys

import numpy as np

G = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(G, 'work', 'selftest_gd')
os.makedirs(D, exist_ok=True)
HDR = ('$VEHICLE:SIMSEC;NO;LANE\\LINK\\NO;LANE\\INDEX;POS;POSLAT;SPEED;TMINNETTOT;DELAYTM;DESSPEED;LENGTH;ROUTDECNO;ROUTENO;'
       'ROUTDECTYPE;NEXTLINK\\NO;DESTLANE;LNCHG;INTERACTSTATE;INTERACTTARGTYPE;INTERACTTARGNO;COORDFRONTX;COORDFRONTY;COORDREARX;COORDREARY;ACCELERATION\n')
rows = []
vid = [0]


def add(t, link, lane, pos, spd, L=4.5):
    vid[0] += 1
    rows.append('%.2f;%d;%s;%d;%.2f;0.50;%.2f;0;0;50;%.3f;;;;;;None;Free;;;0;0;0;0;0\n' % (t, vid[0], link, lane, pos, spd, L))


# frame 5.1: 127 lane 1 full standing queue 3..621 m every 6 m
p = 621.0
while p >= 3.0:
    add(5.1, '127', 1, p, 0.0)
    p -= 6.0
# frame 10.1: 127 lane 1 queue 400..621 stopped + isolated stopped car at 5 m (gap > 20 m) -> S0 1, S 0
add(10.1, '127', 1, 5.0, 0.0)
p = 621.0
while p >= 400.0:
    add(10.1, '127', 1, p, 0.0)
    p -= 6.0
# frame 15.1: 129 lane 1 moving car at 5 m; 26 lane 1 slow car 50 m before diverge 3650.9; one fast car 400 m before
add(15.1, '129', 1, 5.0, 40.0)
add(15.1, '26', 1, 3600.0, 10.0)
add(15.1, '26', 1, 3250.0, 100.0)
# frame 20.1: 127 lane 1 queue 3..621 with a truck (10.2 m) near the head; speeds 3 km/h -> S 1; a car on link 999
p = 621.0
while p >= 3.0:
    add(20.1, '127', 1, p, 3.0, 10.2 if p > 600 else 4.5)
    p -= 6.0 if p <= 600 else 11.7
add(20.1, '999', 1, 10.0, 0.0)
fz = os.path.join(D, 'syn.fzp')
with open(fz, 'w', encoding='ascii', newline='\n') as g:
    g.write('$VISION\n* synthetic\n')
    g.write(HDR)
    g.writelines(rows)
out = os.path.join(D, 'syn_out.npz')
env = dict(os.environ, GD_SELFTEST_LOCK=os.path.join(D, 'never.lock'), PYTHONHASHSEED='0')
r = subprocess.run([sys.executable, '-B', os.path.join(G, 'tools', 'gd_scan.py'), 'one', os.path.join(G, 'inventory.json'), fz, out],
                   env=env, capture_output=True, text=True)
print(r.stdout, r.stderr)
z = np.load(out)
meta = json.load(open(out[:-4] + '.meta.json', encoding='utf-8'))
ids = meta['seg_ids']
fw = meta['fw_ids']
i127 = ids.index('A:127:1:2')
i129 = ids.index('F:129:1')
w26 = fw.index('W:10491')
ok = []
n0 = len([x for x in np.arange(621.0, 2.99, -6.0)])
ok.append(('frames', meta['frames'] == 4))
ok.append(('f0 count', int(z['cnt'][i127, 0]) == n0))
ok.append(('f0 S0,S', int(z['flg'][i127, 0]) == 3))
ok.append(('f0 lsum', abs(float(z['lsum'][i127, 0]) - n0 * (4.5 + 1.51)) < 1e-2))
ok.append(('f1 S0 only', int(z['flg'][i127, 1]) == 1))
ok.append(('f2 129 moving no flag', int(z['flg'][i129, 2]) == 0 and int(z['cnt'][i129, 2]) == 1))
ok.append(('f2 fw slow 1, n 2', int(z['w_s'][w26, 2]) == 1 and int(z['w_n'][w26, 2]) == 2))
ok.append(('f2 fw mean speed', abs(float(z['w_v'][w26, 2]) - 55.0) < 1e-3))
ok.append(('f3 S with truck', int(z['flg'][i127, 3]) == 3))
ok.append(('f3 nq', int(z['nq'][i127, 3]) == int(z['cnt'][i127, 3])))
ok.append(('times', list(np.round(z['times'], 1)) == [5.1, 10.1, 15.1, 20.1]))
for k, v in ok:
    print(k, v)
print('ALL_OK' if all(v for _, v in ok) else 'FAIL')
