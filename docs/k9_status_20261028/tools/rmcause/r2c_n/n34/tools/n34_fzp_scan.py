# -*- coding: utf-8 -*-
"""N34 (2026-10-24, rmcause r2c_n): read-only FZP scanner for N3 (link 32/129/127 flows around RM_C10490) and
N4 (meter head crossings and queues on the 8 meter connectors). Shares no code with O1/O4/VN tools.

Usage: python -B n34_fzp_scan.py <fzp> <out.json>
Reads one FZP once (sequentially), writes only <out.json> (via .tmp + rename).

Frame index k = round((t - 0.1) / 5); frame t covers (t-5, t].
FZP columns used (header of these runs): 0 SimSec, 1 No, 2 Link, 3 Lane, 4 Pos, 6 Speed, 11 RoutDecNo, 12 RouteNo,
14 NextLink, 18 InteractTargType, 19 InteractTargNo.

N3 records
- ins32[k]: vehicles whose first record in the whole FZP is on link 32 (input 1102).
- tag: first static route tag seen on a parsed link among decisions 1136 (link 32), 1132 (link 26 -> 10491), 1131 (link 2 -> 10481).
- trans[(k, prev, new, tag)]: link changes where prev or new is in the parsed set.
- stock[(k, link, lane, tag, slow)] for links 32, 129, 127 (slow = speed < 15 km/h).
- veh32[vid] = [k_ins, tag, k_enter_10490, k_enter_10482, k_enter_127] for vehicles inserted on 32.
N4 records, per meter connector C and lane (head position from the run inpx signal heads)
- cross[(k, C, lane)]: head crossings (previous record on C before the head and current record on C at/after the head or
  on another link; also first record on C already past the head = 'entry_past_head', counted separately).
- mframe[(k, C, lane)] = [pre, pre_slow50, pre_sig, post, post_slow]: pre = pos < head; pre_slow50 = head-50 <= pos < head and
  speed < 15; pre_sig = pos < head and interaction target is a signal head; post = pos >= head; post_slow = post and speed < 15.
- leave[(k, C, lane, next)]: departures from C (merge onto the next link).
- appr[(k, C, slow)]: vehicles on C's approach link whose next link is C.
"""
import hashlib
import json
import os
import sys
import time

# head position (m on connector) per (connector, lane), from inpx 3de889f0 signal heads (same geometry in the rm inpx; checked separately)
HEAD = {(10639, 1): 314.83469380887993, (10681, 1): 290.72003141146473, (10681, 2): 290.72003141146473,
        (10490, 1): 272.6035592816065, (10484, 1): 377.1107628548054, (10480, 1): 145.641195575947,
        (10482, 1): 374.11967822309003, (10482, 2): 374.2173333514973, (10646, 1): 304.45039540874615,
        (10644, 1): 814.7799217676458}
METERS = {10639, 10681, 10490, 10484, 10480, 10482, 10646, 10644}
APPR = {70: 10639, 68: 10681, 129: 10490, 31: 10484, 124: 10480, 32: 10482, 121: 10646, 69: 10644}
S3 = {32, 10778, 129, 10777, 127, 10490, 10482, 10491, 10481, 10118, 10368, 10695}
STOCK_LINKS = {32, 129, 127}
SEL = S3 | METERS | set(APPR)
SEL_B = {str(x).encode() for x in SEL}
TAG_DEC = {b'1136', b'1132', b'1131'}
SIG = b'Signal head'


def headpos(c, lane):
    h = HEAD.get((c, lane))
    if h is None:
        h = HEAD[(c, 1)]
    return h


def main():
    fzp, out = sys.argv[1], sys.argv[2]
    t0 = time.time()
    h = hashlib.sha256()
    last = {}       # vid -> link int (every vehicle)
    tag = {}        # vid -> 'dec:route'
    lastm = {}      # vid -> (connector, lane, pos) while on a meter connector
    ins32 = {}
    trans = {}
    stock = {}
    veh32 = {}
    cross = {}
    cross_entry = {}
    mframe = {}
    leave = {}
    appr = {}
    nrows = 0
    kmin, kmax = 10 ** 9, -1
    in_data = False
    with open(fzp, 'rb') as f:
        for line in f:
            h.update(line)
            if not in_data:
                if line.startswith(b'$VEHICLE:'):
                    in_data = True
                continue
            q = line.split(b';', 3)
            if len(q) < 4:
                continue
            t = float(q[0])
            k = int(round((t - 0.1) / 5.0))
            vid = q[1]
            lb = q[2]
            nrows += 1
            if k < kmin:
                kmin = k
            if k > kmax:
                kmax = k
            L = int(lb)
            prev = last.get(vid)
            if lb not in SEL_B and (prev is None or prev not in SEL):
                last[vid] = L
                continue
            p = line.split(b';', 21)
            if lb in SEL_B:
                lane = int(p[3]); pos = float(p[4]); spd = float(p[6])
                rd = p[11]
                if rd in TAG_DEC and vid not in tag:
                    tag[vid] = (rd + b':' + p[12]).decode()
            tg = tag.get(vid, 'none')
            if prev is None:
                if L == 32:
                    ins32[k] = ins32.get(k, 0) + 1
                    veh32[vid] = [k, None, None, None, None]
            elif prev != L:
                key = (k, prev, L, tg)
                trans[key] = trans.get(key, 0) + 1
                v = veh32.get(vid)
                if v is not None:
                    if L == 10490 and v[2] is None:
                        v[2] = k
                    elif L == 10482 and v[3] is None:
                        v[3] = k
                    elif L == 127 and v[4] is None:
                        v[4] = k
                # leaving a meter connector
                if prev in METERS:
                    lm = lastm.pop(vid, None)
                    plane = lm[1] if lm else 0
                    kk = (k, prev, plane, L)
                    leave[kk] = leave.get(kk, 0) + 1
                    if lm is not None and lm[2] < headpos(prev, plane):
                        ck = (k, prev, plane)
                        cross[ck] = cross.get(ck, 0) + 1
            if lb in SEL_B:
                if vid in veh32 and veh32[vid][1] is None and tg != 'none':
                    veh32[vid][1] = tg
                if L in STOCK_LINKS:
                    sk = (k, L, lane, tg, 1 if spd < 15.0 else 0)
                    stock[sk] = stock.get(sk, 0) + 1
                if L in METERS:
                    hp = headpos(L, lane)
                    lm = lastm.get(vid)
                    if lm is not None and lm[0] == L:
                        if lm[2] < headpos(L, lm[1]) and pos >= hp:
                            ck = (k, L, lm[1])
                            cross[ck] = cross.get(ck, 0) + 1
                    elif pos >= hp:
                        ck = (k, L, lane)
                        cross_entry[ck] = cross_entry.get(ck, 0) + 1
                    lastm[vid] = (L, lane, pos)
                    fk = (k, L, lane)
                    r = mframe.get(fk)
                    if r is None:
                        r = mframe[fk] = [0, 0, 0, 0, 0]
                    if pos < hp:
                        r[0] += 1
                        if spd < 15.0 and pos >= hp - 50.0:
                            r[1] += 1
                        if p[18] == SIG:
                            r[2] += 1
                    else:
                        r[3] += 1
                        if spd < 15.0:
                            r[4] += 1
                if L in APPR:
                    nl = p[14]
                    if nl:
                        try:
                            nli = int(nl)
                        except ValueError:
                            nli = None
                        if nli == APPR[L]:
                            ak = (k, nli, 1 if spd < 15.0 else 0)
                            appr[ak] = appr.get(ak, 0) + 1
            last[vid] = L
    res = {
        'tool': 'n34_fzp_scan.py', 'fzp': fzp, 'sha256': h.hexdigest(), 'rows': nrows, 'k_min': kmin, 'k_max': kmax,
        'frame_convention': 'k = round((t-0.1)/5); frame t covers (t-5, t]',
        'head': {'%d|%d' % kk: v for kk, v in HEAD.items()},
        'ins32': {str(k): n for k, n in ins32.items()},
        'trans': [[k, a, b, tg, n] for (k, a, b, tg), n in trans.items()],
        'stock': [[k, L, ln, tg, s, n] for (k, L, ln, tg, s), n in stock.items()],
        'veh32': [[v[0], v[1], v[2], v[3], v[4]] for v in veh32.values()],
        'cross': [[k, c, ln, n] for (k, c, ln), n in cross.items()],
        'cross_entry': [[k, c, ln, n] for (k, c, ln), n in cross_entry.items()],
        'mframe': [[k, c, ln] + r for (k, c, ln), r in mframe.items()],
        'leave': [[k, c, ln, nx, n] for (k, c, ln, nx), n in leave.items()],
        'appr': [[k, c, s, n] for (k, c, s), n in appr.items()],
        'n_vehicles': len(last), 'n_tagged': len(tag), 'elapsed_s': round(time.time() - t0, 1),
    }
    tmp = out + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as g:
        json.dump(res, g)
    os.replace(tmp, out)
    print('OK', fzp, nrows, res['elapsed_s'], flush=True)


if __name__ == '__main__':
    main()
