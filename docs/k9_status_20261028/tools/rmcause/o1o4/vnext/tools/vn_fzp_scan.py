# VERIFY_NEXT fresh FZP scanner (read-only). Written 2026-10-24 for VERIFY_NEXT; shares no code with O1/O4/W264 tools.
# Usage: python -B vn_fzp_scan.py <fzp> <out.json>
# link 2 cells are stored as (minute, 5 m position bin); any chain offset is applied later.
# Reads one FZP once. Writes only <out.json>.
import sys, json, hashlib, zlib, time, math

fzp, out = sys.argv[1], sys.argv[2]

MAIN7 = [74, 10699, 2, 10613, 119, 10702, 24]
METERS_E = [10639, 10681, 10490, 10484]
METERS_W = [10480, 10482, 10646, 10644]
EXITS_E = [10481, 10483, 10643, 10682]
APPR_E = [129, 31, 68, 70]
FWW3 = [26, 10771, 120]
OTHER = [10491, 127, 10638, 10777, 10778, 124, 121]
SEL = set(MAIN7 + METERS_E + METERS_W + EXITS_E + APPR_E + FWW3 + OTHER)
TRACK_FROM = set(METERS_E + METERS_W)   # connectors whose leave events we keep
TRACK_TO = set(METERS_E)                # connectors whose enter events we keep
NF = 1802

t0 = time.time()
h = hashlib.sha256()
sel = {L: [0] * NF for L in SEL}
meterbound_e = [0] * NF
link_tot = {}
ins = {}          # link -> {k: n}
last = {}         # vid -> link
leave = {m: {} for m in TRACK_FROM}   # meter -> to_link -> [k...]
enter = {m: {} for m in TRACK_TO}     # meter -> from_link -> [k...]
first_on = {m: [] for m in TRACK_TO}  # vehicles whose first record is on the meter connector (k)
frame_rows = [0] * NF
frame_crc = [0] * NF
cells = {}        # (minute, cell) -> [n, speed_sum] on link 2
lane_max2 = 0
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
        p = line.split(b';', 15)
        if len(p) < 15:
            continue
        t = float(p[0])
        k = int(round((t - 0.1) / 5.0))
        if k < 0 or k >= NF:
            raise SystemExit('frame out of range %r' % t)
        vid = p[1]
        L = int(p[2])
        nrows += 1
        if k < kmin: kmin = k
        if k > kmax: kmax = k
        frame_rows[k] += 1
        frame_crc[k] = zlib.crc32(line, frame_crc[k])
        link_tot[L] = link_tot.get(L, 0) + 1
        if L in SEL:
            sel[L][k] += 1
        if L in METERS_E:
            meterbound_e[k] += 1
        elif L in (129, 31, 68, 70):
            nl = p[14]
            if nl:
                try:
                    if int(nl) in METERS_E:
                        meterbound_e[k] += 1
                except ValueError:
                    pass
        if L == 2:
            ln = int(p[3])
            if ln > lane_max2: lane_max2 = ln
            pos = float(p[4]); spd = float(p[6])
            key = (int(t // 60.0), int(pos // 5.0))
            c = cells.get(key)
            if c is None:
                cells[key] = [1, spd]
            else:
                c[0] += 1; c[1] += spd
        prev = last.get(vid)
        if prev is None:
            d = ins.get(L)
            if d is None:
                d = ins[L] = {}
            d[k] = d.get(k, 0) + 1
            if L in TRACK_TO:
                first_on[L].append(k)
        elif prev != L:
            if prev in TRACK_FROM:
                leave[prev].setdefault(L, []).append(k)
            if L in TRACK_TO:
                enter[L].setdefault(prev, []).append(k)
        last[vid] = L

res = {
    'tool': 'vn_fzp_scan.py', 'fzp': fzp, 'sha256': h.hexdigest(), 'rows': nrows,
    'k_min': kmin, 'k_max': kmax, 't_min': 5 * kmin + 0.1, 't_max': 5 * kmax + 0.1,
    'frame_convention': 'k = round((t-0.1)/5); frame t covers (t-5, t]',
    'link2_cells_bin_m': 5.0, 'link2_lane_max': lane_max2,
    'sel': {str(L): v for L, v in sel.items()},
    'meterbound_e': meterbound_e,
    'link_tot_frames': {str(L): n for L, n in link_tot.items()},
    'ins': {str(L): {str(k): n for k, n in d.items()} for L, d in ins.items()},
    'leave': {str(m): {str(L): v for L, v in d.items()} for m, d in leave.items()},
    'enter': {str(m): {str(L): v for L, v in d.items()} for m, d in enter.items()},
    'first_on': {str(m): v for m, v in first_on.items()},
    'frame_rows': frame_rows, 'frame_crc': frame_crc,
    'link2_cells': [[m, c, v[0], v[1]] for (m, c), v in sorted(cells.items())],
    'n_vehicles': len(last), 'elapsed_s': round(time.time() - t0, 1),
}
with open(out, 'w', encoding='utf-8') as g:
    json.dump(res, g)
print('OK', fzp, nrows, res['elapsed_s'])
