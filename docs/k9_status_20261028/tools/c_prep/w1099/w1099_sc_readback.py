# w1099_sc_readback.py — SC1001·SC1002 SG2·SG5 녹색 초를 300 s 칸으로 (W1099_RULE_ADD1 A1, 데이터 뒤 선언; 읽기만, 가벼움)
# B·V-A: decisions_*/signal_readback.csv 의 immediate 줄(상태 바뀜)로 초별 상태를 다시 짬. 900 s 전(결정 전)은 기록 없음 → 칸 값 None.
# NC3: 고정 신호 파일 prog(망의 progNo)에서 주기당 녹색 초 → 300 s 칸 값(주기 150 s 가 300 s 를 나누므로 offset 무관).
import os, json, csv
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
RB = {
    ('b', 31): 'D:/VISSIM_runs/20261026_codex_b_v3c3/s31/sdmpc/decisions_sdmpc31_sdmpc9000_s31/signal_readback.csv',
    ('b', 41): 'D:/VISSIM_runs/20261026_codex_b_v3c3/s41/sdmpc/decisions_sdmpc31_sdmpc9000_s41/signal_readback.csv',
    ('b', 43): 'D:/VISSIM_runs/20261026_codex_b_v3c3/s43/sdmpc/decisions_sdmpc31_sdmpc9000_s43/signal_readback.csv',
    ('va', 31): 'D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s31/decisions_sdmpc31_v3c3_k92va_s31/signal_readback.csv',
    ('va', 41): 'D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s41/decisions_sdmpc31_v3c3_k92va_s41/signal_readback.csv',
    ('va', 43): 'D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s43/decisions_sdmpc31_v3c3_k92va_s43/signal_readback.csv',
}
NETDIR = 'D:/VISSIM_runs/20261001_v3c3/s31_v3c3nc/prepared/network'
SIG = {1001: NETDIR + '/개포동 test-bed1001_n4dr150.sig', 1002: NETDIR + '/개포동 test-bed1002_n4dr150.sig'}
TARGET = [(1001, 2), (1001, 5), (1002, 2), (1002, 5)]
NTB = 30


def tag(e):
    return e.tag.split('}')[-1]


def sig_green(path, prog_id=1):
    root = ET.parse(path).getroot()
    out = {}
    for p in root.iter():
        if tag(p) == 'prog' and p.get('id') == str(prog_id):
            cyc = int(p.get('cycletime')) / 1000.0
            for sg in p.iter():
                if tag(sg) == 'sg' and sg.get('sg_id'):
                    gs = ge = None
                    for c in sg.iter():
                        if tag(c) == 'cmd':
                            if c.get('display') == '3':
                                gs = int(c.get('begin')) / 1000.0
                            elif c.get('display') == '1':
                                ge = int(c.get('begin')) / 1000.0
                    if gs is not None and ge is not None:
                        out[int(sg.get('sg_id'))] = {'cycle': cyc, 'green_start': gs, 'green_end': ge,
                                                     'green_s': (ge - gs) % cyc, 'per_300s': (ge - gs) % cyc * 300.0 / cyc}
    return out


def readback_green(path):
    ev = {k: [] for k in TARGET}
    nrow = {k: 0 for k in TARGET}
    bad = 0
    with open(path, newline='', encoding='utf-8', errors='replace') as fh:
        for r in csv.DictReader(fh):
            try:
                k = (int(r['sc_no']), int(r['sg_no']))
            except ValueError:
                continue
            if k not in ev:
                continue
            nrow[k] += 1
            if r['ok'] != '1' or r['requested_state'] != r['readback_state']:
                bad += 1
            if r['stage'] == 'immediate':
                ev[k].append((int(float(r['sim_sec'])), r['readback_state']))
    res = {}
    for k, lst in ev.items():
        lst.sort()
        g = [0.0] * NTB
        cover = [0.0] * NTB
        for i, (t, st) in enumerate(lst):
            t_end = lst[i + 1][0] if i + 1 < len(lst) else 9000
            for s in range(t, min(t_end, 9000)):
                b = min(s // 300, NTB - 1)
                cover[b] += 1
                if st == 'GREEN':
                    g[b] += 1
        res['%d_%d' % k] = {'green_s_bin': g, 'covered_s_bin': cover, 'n_rows': nrow[k], 'first_event': lst[0] if lst else None}
    res['rows_bad'] = bad
    return res


out = {'nc3_sig': {str(sc): sig_green(p) for sc, p in SIG.items()}}
for (a, s), p in RB.items():
    out['%s%d' % (a, s)] = readback_green(p)
with open(os.path.join(OUT, 'sc_readback.json'), 'w', encoding='utf-8') as fh:
    json.dump(out, fh)
for k, v in out.items():
    if k == 'nc3_sig':
        print(k, {sc: {sg: (d['green_s'], d['per_300s']) for sg, d in g.items() if sg in (2, 5)} for sc, g in v.items()})
    else:
        print(k, 'bad', v['rows_bad'], {kk: (sum(vv['green_s_bin']), sum(vv['covered_s_bin'])) for kk, vv in v.items() if kk != 'rows_bad'})
print('SC_DONE')
