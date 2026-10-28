# vc_meterhead.py -- independent meter-head discharge check (verify_c V6, added after V1-V5 results; data-after).
# B v3c3-s43 FZP: per 150 s decision block, head crossings per lane on meter connectors, with my own queue / blocking flags.
import json, sys, csv, collections

FZP = 'D:/VISSIM_runs/20261026_codex_b_v3c3/s43/sdmpc/vissim_eval/sdmpc31_sdmpc9000_s43_001.fzp'
CMD = 'D:/VISSIM_runs/20261026_codex_b_v3c3/s43/sdmpc/action_sdmpc31_sdmpc9000_s43.csv'
HEAD = {10639: 314.83469380887993, 10681: 290.72003141146473, 10484: 377.11076285480539, 10490: 272.60355928160652, 10480: 145.64119557594699}
SC = {10639: '9105', 10681: '9106', 10484: '9108', 10490: '9107', 10480: '9101'}
OUT = sys.argv[1]

cmds = collections.defaultdict(list)
for r in csv.DictReader(open(CMD, encoding='utf-8-sig')):
    if r['kind'] == 'ramp_meter':
        cmds[r['sc_no']].append((int(float(r['sim_sec'])), int(float(r['green_sec']))))
def g_at(sc, t):
    g = None
    for tc, gg in sorted(cmds[sc]):
        if tc <= t: g = gg
    return g

prev = {}                                    # vid -> (link, lane, pos)
cross = collections.Counter()                # (conn, lane, block) -> n
qframes = collections.Counter()              # (conn, lane, block) -> frames with stopped veh in [head-30, head)
bframes = collections.Counter()              # (conn, lane, block) -> frames with stopped veh in [head, head+30)
frames_in_block = collections.Counter()
seen_frame = set()
with open(FZP, encoding='latin-1') as f:
    for line in f:
        c0 = line[:1]
        if not ('0' <= c0 <= '9'): continue
        p = line.split(';', 7)
        t = float(p[0]); vid = int(p[1]); link = int(p[2]); lane = int(p[3]); pos = float(p[4]); spd = float(p[6])
        if t < 900 or t >= 9000:
            prev[vid] = (link, lane, pos); continue
        b = int((t - 900) // 150)
        if t not in seen_frame:
            seen_frame.add(t); frames_in_block[b] += 1
        pv = prev.get(vid)
        if pv is not None and pv[0] in HEAD and pv[2] < HEAD[pv[0]]:
            if (link == pv[0] and pos >= HEAD[pv[0]]) or link != pv[0]:
                cross[(pv[0], pv[1], b)] += 1
        if link in HEAD:
            h = HEAD[link]
            if spd < 5.0 and h - 30.0 <= pos < h: qframes[(link, lane, b, t)] = 1
            if spd < 5.0 and h <= pos < h + 30.0: bframes[(link, lane, b, t)] = 1
        prev[vid] = (link, lane, pos)

qn = collections.Counter((k[0], k[1], k[2]) for k in qframes)
bn = collections.Counter((k[0], k[1], k[2]) for k in bframes)
rows = []
for conn in HEAD:
    lanes = (1, 2) if conn == 10681 else (1,)
    for ln in lanes:
        for b in range(54):
            T = 900 + 150 * b
            rows.append(dict(conn=conn, lane=ln, T=T, g=g_at(SC[conn], T), cross=cross[(conn, ln, b)],
                             q_frames=qn[(conn, ln, b)], block_frames=bn[(conn, ln, b)], frames=frames_in_block[b]))
summary = collections.defaultdict(list)
for r in rows:
    if r['q_frames'] == r['frames'] and r['block_frames'] == 0:
        summary[f"{r['conn']}_L{r['lane']}_g{r['g']}"].append(r['cross'])
json.dump({'rows': rows, 'queued_unblocked_cross_per150': {k: sorted(v) for k, v in summary.items()}}, open(OUT, 'w', encoding='utf-8'), indent=1)
print('done')
