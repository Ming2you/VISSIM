# -*- coding: utf-8 -*-
"""rb_fzp_scan.py (c_port/readback, 2026-10-27 KST) - read-only FZP scanner for meter head crossings and queues.

Usage: python -B rb_fzp_scan.py <fzp> <inpx_json from rb_inpx.py> <out.json>
Reads one FZP once (sequentially), writes only <out.json> (via .tmp + rename).
Crossing / frame logic is the N4 part of N34 n34_fzp_scan.py (sha 4e644837...2030), re-written here; heads come from the
run's own inpx (rb_inpx.py) instead of a fixed table.

Frame index k = round((t - 0.1) / 5); frame t covers (t-5, t].
FZP columns used: 0 SIMSEC, 1 NO, 2 LINK, 3 LANE, 4 POS, 6 SPEED, 18 INTERACTTARGTYPE (header checked at run time).
Records per meter connector C and lane:
- cross[(k, C, lane)]: head crossings (previous record on C before the head and current record on C at/after the head, or
  current record on another link); 'cross_entry' = first record on C already past the head (counted separately).
- mframe[(k, C, lane)] = [pre, pre_slow50, pre_sig, post, post_slow]: pre = pos < head; pre_slow50 = head-50 <= pos < head and
  speed < 15 km/h; pre_sig = pos < head and interaction target is a signal head; post = pos >= head; post_slow = post and speed < 15.
- leave[(k, C, lane, next)]: departures from C.
- maxpos[(C, lane)]: largest POS seen (length cross-check).
"""
import hashlib
import json
import os
import sys
import time

EXPECT_HDR = b'$VEHICLE:SIMSEC;NO;LANE\\LINK\\NO;LANE\\INDEX;POS;POSLAT;SPEED;TMINNETTOT;DELAYTM;DESSPEED;LENGTH;ROUTDECNO;ROUTENO;ROUTDECTYPE;NEXTLINK\\NO;DESTLANE;LNCHG;INTERACTSTATE;INTERACTTARGTYPE;INTERACTTARGNO'
SIG = b'Signal head'


def main():
    fzp, inpxj, out = sys.argv[1], sys.argv[2], sys.argv[3]
    ij = json.load(open(inpxj, encoding='utf-8'))
    HEAD = {}
    for c, m in ij['meters'].items():
        for ln, h in m['heads'].items():
            HEAD[(int(c), int(ln))] = float(h['head_pos'])
    METERS = {c for c, _ in HEAD}
    SEL_B = {str(x).encode() for x in METERS}

    def headpos(c, lane):
        h = HEAD.get((c, lane))
        if h is None:
            h = HEAD[(c, 1)]
        return h

    t0 = time.time()
    hs = hashlib.sha256()
    last = {}
    lastm = {}
    cross, cross_entry, mframe, leave, maxpos = {}, {}, {}, {}, {}
    nrows = 0
    kmin, kmax = 10 ** 9, -1
    in_data = False
    hdr_ok = None
    with open(fzp, 'rb') as f:
        for line in f:
            hs.update(line)
            if not in_data:
                if line.startswith(b'$VEHICLE:'):
                    in_data = True
                    hdr_ok = line.strip().startswith(EXPECT_HDR)
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
            if lb not in SEL_B and (prev is None or prev not in METERS):
                last[vid] = L
                continue
            p = line.split(b';', 21)
            if prev is not None and prev != L and prev in METERS:
                lm = lastm.pop(vid, None)
                plane = lm[1] if lm else 0
                kk = (k, prev, plane, L)
                leave[kk] = leave.get(kk, 0) + 1
                if lm is not None and lm[2] < headpos(prev, plane):
                    ck = (k, prev, plane)
                    cross[ck] = cross.get(ck, 0) + 1
            if L in METERS:
                lane = int(p[3]); pos = float(p[4]); spd = float(p[6])
                mk = (L, lane)
                if pos > maxpos.get(mk, -1.0):
                    maxpos[mk] = pos
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
            last[vid] = L
    res = {
        'tool': 'rb_fzp_scan.py', 'fzp': fzp, 'sha256': hs.hexdigest(), 'header_ok': hdr_ok, 'rows': nrows, 'k_min': kmin, 'k_max': kmax,
        'inpx_json': inpxj, 'frame_convention': 'k = round((t-0.1)/5); frame t covers (t-5, t]',
        'head': {'%d|%d' % kk: v for kk, v in HEAD.items()},
        'cross': [[k, c, ln, n] for (k, c, ln), n in cross.items()],
        'cross_entry': [[k, c, ln, n] for (k, c, ln), n in cross_entry.items()],
        'mframe': [[k, c, ln] + r for (k, c, ln), r in mframe.items()],
        'leave': [[k, c, ln, nx, n] for (k, c, ln, nx), n in leave.items()],
        'maxpos': [[c, ln, v] for (c, ln), v in maxpos.items()],
        'still_on_meter_at_end': len(lastm),
        'n_vehicles': len(last), 'elapsed_s': round(time.time() - t0, 1),
    }
    tmp = out + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as g:
        json.dump(res, g)
    os.replace(tmp, out)
    print('OK', fzp, nrows, res['elapsed_s'], 'header_ok', hdr_ok, flush=True)


if __name__ == '__main__':
    main()
