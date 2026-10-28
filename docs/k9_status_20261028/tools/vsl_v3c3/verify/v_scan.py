# v_scan.py — VERIFY_VSL (2026-10-27 KST). Fresh FZP scanner (no reuse of the authors' tools). Read-only on the FZP.
# One pass over a VISSIM .fzp (5 s frames). Writes one JSON with:
#   frames: frame times; per-frame vehicle counts for link groups (ALL, O701, O635, M1, M2);
#   per-link sum of counts over all frames + counts at first/last frame (trapezoid later);
#   first observation per vehicle No: [t, link, lane, pos, desspeed, length];
#   VSL zone (link 2 pos>=3998.666 .. link 24 pos<652.70) and B2 zone (chain 6800-8100) per-frame n / speed sums,
#   VSL-zone per-link desired-speed compliance counts (89<=des<=93) for frames t>=900.
# Usage: python -B v_scan.py <fzp> <out.json>
import sys, json, hashlib, time

FZP, OUT = sys.argv[1], sys.argv[2]
T0 = time.time()
O701 = set(json.load(open('D:/VISSIM_handoff/20261024/derived/omega_membership_exact.json', encoding='utf-8'))['inside_links'])
O635 = set(json.load(open('D:/VISSIM-merge/sim3-n31-k8/diagnostics/control_area_membership.json', encoding='utf-8'))['inside_links'])
M1 = {'74', '10699', '2', '10613', '119', '10702', '24'}
M2 = M1 | {'10484', '10490', '10639', '10681', '10481', '10483', '10643', '10682', '129', '31', '68', '70'}
assert len(O701) == 701 and len(O635) == 635 and len(M1) == 7 and len(M2) == 19
GROUPS = ['ALL', 'O701', 'O635', 'M1', 'M2']
SIGN_POS = 3998.6659943877257          # DSD 63-66 on link 2 (inpx)
L24_DSD = 652.70                       # DSD 67-69 on link 24 (next downstream)
L2_START = 2734.527                    # chain start of link 2
L24_START = 8090.8 - 652.70            # chain start of link 24 (DSD 67-69 at chain 8090.8)
B2_L2_FROM = 6800.0 - L2_START         # link 2 pos where chain 6800 is
B2_L24_TO = 8100.0 - L24_START         # link 24 pos where chain 8100 is
ZONE_MID = {b'10613', b'119', b'10702'}

mask_cache = {}


def gmask(link):
    m = mask_cache.get(link)
    if m is None:
        s = link.decode()
        m = (True, s in O701, s in O635, s in M1, s in M2)
        mask_cache[link] = m
    return m


h = hashlib.sha256()
frames, gcount = [], {g: [] for g in GROUPS}
zone_n, zone_comp, zone_vsum, b2_n, b2_vsum = [], [], [], [], []
link_sum, link_first, link_last = {}, {}, {}
first = {}
comp_link = {}   # link -> [n, n_comp] for t >= 900
cur_t, cur_cnt = None, {}
zn = zc = 0
zv = 0.0
bn = 0
bv = 0.0
n_rows = 0
in_data = False


def finalize():
    global cur_cnt, zn, zc, zv, bn, bv
    frames.append(float(cur_t))
    tot = [0] * len(GROUPS)
    for link, c in cur_cnt.items():
        link_sum[link] = link_sum.get(link, 0) + c
        m = gmask(link)
        for i in range(len(GROUPS)):
            if m[i]:
                tot[i] += c
    for i, g in enumerate(GROUPS):
        gcount[g].append(tot[i])
    if len(frames) == 1:
        for link, c in cur_cnt.items():
            link_first[link.decode()] = c
    zone_n.append(zn); zone_comp.append(zc); zone_vsum.append(zv); b2_n.append(bn); b2_vsum.append(bv)
    cur_cnt = {}
    zn = zc = 0; zv = 0.0; bn = 0; bv = 0.0


last_cnt = None
with open(FZP, 'rb') as f:
    for line in f:
        h.update(line)
        if not in_data:
            if line.startswith(b'$VEHICLE:'):
                in_data = True
            continue
        p = line.split(b';', 11)
        t = p[0]
        if t != cur_t:
            if cur_t is not None:
                last_cnt = cur_cnt
                finalize()
            cur_t = t
        link = p[2]
        cur_cnt[link] = cur_cnt.get(link, 0) + 1
        n_rows += 1
        no = p[1]
        if no not in first:
            first[no] = (float(t), link.decode(), int(p[3]), float(p[4]), float(p[9]), float(p[10]))
        if link == b'2' or link == b'24' or link in ZONE_MID:
            pos = float(p[4])
            if link == b'2':
                inz = pos >= SIGN_POS
                inb = pos >= B2_L2_FROM
            elif link == b'24':
                inz = pos < L24_DSD
                inb = pos < B2_L24_TO
            else:
                inz = inb = True
            if inz or inb:
                v = float(p[6])
                if inz:
                    d = float(p[9])
                    ok = 89.0 <= d <= 93.0
                    zn += 1; zv += v
                    if ok:
                        zc += 1
                    if float(t) >= 900.0:
                        lk = link.decode() + ('_pastsign' if link == b'2' else '')
                        a = comp_link.setdefault(lk, [0, 0])
                        a[0] += 1
                        if ok:
                            a[1] += 1
                if inb:
                    bn += 1; bv += v
    if cur_t is not None:
        last_cnt = cur_cnt
        finalize()

link_last = {k.decode(): v for k, v in last_cnt.items()}
out = dict(schema='verify_vsl_scan/1', fzp=FZP, fzp_sha256=h.hexdigest(), n_rows=n_rows, n_frames=len(frames),
           frames=frames, groups=gcount, link_sum={k.decode(): v for k, v in link_sum.items()},
           link_first=link_first, link_last=link_last,
           first={k.decode(): v for k, v in first.items()},
           zone=dict(n=zone_n, comp=zone_comp, vsum=zone_vsum, b2_n=b2_n, b2_vsum=b2_vsum, comp_link=comp_link,
                     def_=dict(sign_pos=SIGN_POS, l24_dsd=L24_DSD, b2_l2_from=B2_L2_FROM, b2_l24_to=B2_L24_TO)),
           wall_sec=time.time() - T0)
with open(OUT + '.tmp', 'w', encoding='utf-8') as g:
    json.dump(out, g)
import os
os.replace(OUT + '.tmp', OUT)
print('done', FZP, n_rows, len(frames), out['fzp_sha256'][:12], round(time.time() - T0, 1))
