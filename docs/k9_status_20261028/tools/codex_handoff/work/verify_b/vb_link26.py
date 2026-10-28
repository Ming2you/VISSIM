# vb_link26.py — 검증자 참고(선언 밖): 링크 26(FW_W 입구·본선)과 그 둘레 링크의 체류를 위치 250 m 칸으로 나눔 (우리 꼴, 읽기만)
import json, os, sys
import numpy as np, pandas as pd
V = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(V, 'out')
F = {
 'b31': 'D:/VISSIM_runs/20261026_codex_b_v3c3/s31/sdmpc/vissim_eval/sdmpc31_sdmpc9000_s31_001.fzp',
 'nc31': 'D:/VISSIM_runs/20261001_v3c3/s31_v3c3nc/run/vissim_eval/baseline_s31_v3c3nc_001.fzp',
 'b41': 'D:/VISSIM_runs/20261026_codex_b_v3c3/s41/sdmpc/vissim_eval/sdmpc31_sdmpc9000_s41_001.fzp',
 'nc41': 'D:/VISSIM_runs/20261001_v3c3/s41_v3c3nc/run/vissim_eval/baseline_s41_v3c3nc_001.fzp',
}
LINKS = [26, 10480, 10491, 10771, 120]


def hl(p):
    n = 0
    with open(p, 'r', encoding='utf-8', errors='replace') as fh:
        for line in fh:
            n += 1
            if line.startswith('$VEHICLE:'):
                return n


res = {}
for k, p in F.items():
    df = pd.read_csv(p, sep=';', skiprows=hl(p), header=None, usecols=[0, 2, 3, 4], names=['t', 'link', 'lane', 'pos'],
                     dtype={'t': np.float64, 'link': np.int64, 'lane': np.int64, 'pos': np.float64}, engine='c', encoding='latin-1')
    df = df[(df['t'] >= 1.0) & (df['t'] <= 9000.0) & df['link'].isin(LINKS)]
    # ours_9000 weights: 5 s each, first (5.1) and last (8995.1) half
    w = np.where((np.round(df['t'], 1) == 5.1) | (np.round(df['t'], 1) == 8995.1), 2.5, 5.0) / 3600.0
    df = df.assign(w=w)
    o = {}
    for L in LINKS:
        d = df[df['link'] == L]
        o[str(L)] = {'total': float(d['w'].sum())}
        if L == 26:
            b = (d['pos'] // 250).astype(int) * 250
            o['26_bins'] = {str(int(x)): float(v) for x, v in d.groupby(b)['w'].sum().items()}
            o['26_lane'] = {str(int(x)): float(v) for x, v in d.groupby('lane')['w'].sum().items()}
            tb = (d['t'] // 900).astype(int) * 900
            o['26_time'] = {str(int(x)): float(v) for x, v in d.groupby(tb)['w'].sum().items()}
    res[k] = o
    print(k, flush=True)
json.dump(res, open(os.path.join(OUT, 'link26.json'), 'w', encoding='utf-8'), indent=1)
print('ALL_DONE', flush=True)
