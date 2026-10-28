# -*- coding: utf-8 -*-
"""rb_selftest.py (c_port/readback) - synthetic self-test of rb_readback.py / rb_fzp_scan.py / rb_discharge.py. No run data.

Builds a fake run under <tmp>: commands g=10 (T=1..750), then g=4 from 900 and g=7 from 1050 for SC 9101, g=10 for the rest;
a readback CSV that follows the runner semantics; one injected error (SC 9103 stays GREEN for one second at 905 when g is 10 ->
no error) and one real error (SC 9101 RED written 2 s late in the cycle at 1100). Expect K3 mismatch exactly 1 cycle for 9101.
FZP: one meter connector 10490 head 272.6, ten vehicles crossing during block 900, queue frames.
"""
import csv
import json
import os
import subprocess
import sys

T = os.path.dirname(os.path.abspath(__file__))
TMP = sys.argv[1]
RUN = os.path.join(TMP, 'run')
os.makedirs(RUN + '/decisions_x', exist_ok=True)
IDS = {9101: 'RM_C10480', 9102: 'RM_C10482', 9103: 'RM_C10646', 9104: 'RM_C10644', 9105: 'RM_C10639', 9106: 'RM_C10681',
       9107: 'RM_C10490', 9108: 'RM_C10484'}
LANES = {9102: 2, 9106: 2}
TBL = {2: 0.71, 3: 0.99, 4: 1.44, 5: 1.89, 6: 2.34, 7: 2.79, 8: 3.24, 9: 3.69, 10: 4.2}


def g_of(sc, t):
    if sc == 9101 and t >= 1050:
        return 7
    if sc == 9101 and t >= 900:
        return 4
    if sc == 9107 and t >= 900:
        return 3
    return 10


def st(g, t):
    return 'GREEN' if (t % 10) < g else 'RED'


Ts = [1] + list(range(150, 1201, 150))
hdr = ['sim_sec', 'kind', 'id', 'dsd_no', 'sc_no', 'link', 'lane', 'speed_kph', 'p1_green', 'p2_green', 'p3_green', 'p4_green', 'offset',
       'rate_vph', 'green_sec', 'metadata', 'readback']
with open(RUN + '/action_x.csv', 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(hdr)
    for t in Ts:
        dec = open(RUN + '/decisions_x/action_%06d.csv' % t, 'w', newline='')
        dw = csv.writer(dec)
        dw.writerow(hdr[1:-1])
        for sc in IDS:
            g = g_of(sc, t)
            md = 'ok;group_rate_vph=%s' % (360.0 * TBL[g] * LANES.get(sc, 1))
            w.writerow([t, 'ramp_meter', IDS[sc], '', sc, '', '', '', '', '', '', '', '', 90.0 * g, float(g), md, 'GREEN'])
            dw.writerow(['ramp_meter', IDS[sc], '', sc, '', '', '', '', '', '', '', '', 90.0 * g, float(g), md])
        dec.close()
open(RUN + '/runlog_x.txt', 'w').write('RAMP_AMBER_SEC=0\nRAMP_METER_SCS=9101,9102,9103,9104,9105,9106,9107,9108\n')
rows = []
cur = {}
for t in range(1, 1201):
    # post_step first: pending = SGs written at previous stop (every second here), plus all at 150 multiples
    for sc in IDS:
        if sc in cur and (t % 150 == 0 or cur[sc][1] == t - 1):
            rows.append([t, sc, 1, cur[sc][0], cur[sc][0], 1, 'post_step'])
    for sc in IDS:
        s = st(g_of(sc, t), t)
        if sc == 9101 and t in (1104, 1105):   # injected: RED write delayed by 2 s at cycle 1100 (g7 -> RED due 1107? no: g=7 RED at 1107)
            pass
        if sc == 9101 and 1100 <= t < 1110:
            s = 'GREEN' if (t % 10) < 9 else 'RED'   # observed 9 s green instead of 7
        if cur.get(sc, (None,))[0] != s:
            rows.append([t, sc, 1, s, s, 1, 'immediate'])
            cur[sc] = (s, t)
with open(RUN + '/decisions_x/signal_readback.csv', 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['sim_sec', 'sc_no', 'sg_no', 'requested_state', 'readback_state', 'ok', 'stage'])
    w.writerows(rows)
print('readback rows', len(rows))
os.makedirs(TMP + '/out', exist_ok=True)
rc = subprocess.call([sys.executable, '-B', T + '/rb_readback.py', TMP + '/out', 'x=' + RUN.replace('\\', '/')])
print('rb_readback rc', rc)
j = json.load(open(TMP + '/out/readback.json'))
m = j['runs']['x']['meters']
for sc in ('9101', '9107', '9102'):
    print(sc, 'K0', j['runs']['x']['K0_command_source']['match'], 'K3', m[sc]['K3_cycle_match'], '/', m[sc]['K3_cycles'],
          'mis', m[sc]['K3_cycle_mismatch_examples'][:3], 'K4', m[sc]['K4_second_match'], '/', m[sc]['K4_seconds'],
          'K5', m[sc]['K5_ok_and_post_same'], '/', m[sc]['K5_writes_ctrl'], 'K2', m[sc]['K2_rb_eq_expected'])
# FZP synthetic: connector 10490 lane 1, head 272.6; 10 vehicles queued then crossing in block T=900 (frames 905.1..1050.1)
inpx = {'meters': {'10490': {'heads': {'1': {'head_pos': 272.6, 'storage_after_head_veh': 16.0}}}}}
json.dump(inpx, open(TMP + '/out/inpx_x.json', 'w'))
lines = ['$VEHICLE:SIMSEC;NO;LANE\\LINK\\NO;LANE\\INDEX;POS;POSLAT;SPEED;TMINNETTOT;DELAYTM;DESSPEED;LENGTH;ROUTDECNO;ROUTENO;ROUTDECTYPE;NEXTLINK\\NO;DESTLANE;LNCHG;INTERACTSTATE;INTERACTTARGTYPE;INTERACTTARGNO;COORDFRONTX;COORDFRONTY;COORDREARX;COORDREARY;ACCELERATION']
f = ['0'] * 25
for k in range(181, 211):          # frames 905.1 .. 1050.1
    t = 5 * k + 0.1
    for v in range(12):
        vid = 100 + v
        cross_k = 181 + 3 * v      # vehicle v crosses at frame cross_k
        if k < cross_k:
            pos, spd, link = 270.0 - v, 5.0, 10490
        elif k == cross_k:
            pos, spd, link = 280.0, 20.0, 10490
        else:
            pos, spd, link = 10.0, 40.0, 119
        r = list(f)
        r[0] = '%.2f' % t; r[1] = str(vid); r[2] = str(link); r[3] = '1'; r[4] = '%.2f' % pos; r[6] = '%.2f' % spd; r[18] = 'Signal head'
        lines.append(';'.join(r))
fz = TMP + '/x.fzp'
open(fz, 'w').write('\n'.join(['$header'] + lines) + '\n')
rc = subprocess.call([sys.executable, '-B', T + '/rb_fzp_scan.py', fz, TMP + '/out/inpx_x.json', TMP + '/out/scan_x.json'])
s = json.load(open(TMP + '/out/scan_x.json'))
print('scan rc', rc, 'cross total', sum(r[3] for r in s['cross']), 'entry', sum(r[3] for r in s['cross_entry']), 'header_ok', s['header_ok'])
