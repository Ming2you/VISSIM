# vb_scan.py — VERIFY_B 용 새 FZP 스캐너 (작성자 도구 재사용 없음, 읽기만)
# 입력: 이름=FZP경로 쌍들. 출력: out/<이름>.json
#  - 링크별 체류 적분 (veh*h) 두 꼴: ours_9000 (5.1..<=9000 프레임 사다리꼴, t<1 행 버림),
#    codex_8100 (t=0 빈 망에서 시작, <=8100 모든 프레임(0.1 포함) 실제 시각 사다리꼴, 마지막 프레임 재고를 8100 까지 유지)
#  - 첫 관측: 차 번호별 파일 첫 행 (시각, 링크). S(W)=sum_{t1<=W}(W-t1)/3600, 링크 74 / 26 / 그 밖 으로 나눔
import sys, json, time, os
import numpy as np
import pandas as pd

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out')
os.makedirs(OUT, exist_ok=True)


def header_len(path):
    n = 0
    with open(path, 'r', encoding='utf-8', errors='replace') as fh:
        for line in fh:
            n += 1
            if line.startswith('$VEHICLE:'):
                return n
    raise RuntimeError('no $VEHICLE header')


def frame_weights(times, form):
    t = np.asarray(times, dtype=float)
    if form == 'ours_9000':
        sel = (t >= 1.0) & (t <= 9000.0 + 1e-9)
        ts = t[sel]
        w = np.zeros_like(ts)
        if len(ts) >= 2:
            d = np.diff(ts)
            w[:-1] += d / 2.0
            w[1:] += d / 2.0
        return ts, w
    if form == 'codex_8100':
        sel = (t <= 8100.0 + 1e-9)
        ts = t[sel]
        w = np.zeros_like(ts)
        # segment 0 -> ts[0] with n(0)=0: contributes n0*ts0/2
        w[0] += ts[0] / 2.0
        d = np.diff(ts)
        w[:-1] += d / 2.0
        w[1:] += d / 2.0
        w[-1] += (8100.0 - ts[-1])
        return ts, w
    raise ValueError(form)


def scan(name, path):
    t0 = time.time()
    hl = header_len(path)
    df = pd.read_csv(path, sep=';', skiprows=hl, header=None, usecols=[0, 1, 2],
                     names=['t', 'no', 'link'], dtype={'t': np.float64, 'no': np.int64, 'link': np.int64},
                     engine='c', encoding='latin-1')
    nrows = int(len(df))
    # frame times
    tr = np.round(df['t'].to_numpy(), 2)
    df['t'] = tr
    frames = np.unique(tr)
    res = {'name': name, 'path': path, 'rows': nrows, 'n_frames': int(len(frames)),
           'first_frame': float(frames[0]), 'last_frame': float(frames[-1]),
           'frames_lt1': [float(x) for x in frames[frames < 1.0]],
           'rows_lt1': int((tr < 1.0).sum())}
    # check spacing
    fr_ge = frames[frames >= 1.0]
    dd = np.diff(fr_ge)
    res['frame_gap_min_max'] = [float(dd.min()), float(dd.max())]
    res['links'] = {}
    for form in ('ours_9000', 'codex_8100'):
        ts, w = frame_weights(frames, form)
        wmap = pd.Series(w, index=ts)
        rw = df['t'].map(wmap)
        rw = rw.fillna(0.0).to_numpy()
        g = pd.Series(rw).groupby(df['link'].to_numpy()).sum() / 3600.0
        res['links'][form] = {str(int(k)): float(v) for k, v in g.items() if v != 0.0}
        res['frames_' + form] = [float(ts[0]), float(ts[-1]), int(len(ts))]
    # first observation
    fo = df.drop_duplicates('no', keep='first')
    t1 = fo['t'].to_numpy()
    l1 = fo['link'].to_numpy()
    cat = np.where(l1 == 74, 'in1098', np.where(l1 == 26, 'in1099', 'urban'))
    res['first_seen'] = {}
    for W in (9000.0, 8100.0):
        sel = t1 <= W + 1e-9
        d = {'n_all': int(sel.sum())}
        S_all = float(((W - t1[sel])).sum() / 3600.0)
        d['S_all'] = S_all
        for c in ('in1098', 'in1099', 'urban'):
            m = sel & (cat == c)
            d['n_' + c] = int(m.sum())
            d['S_' + c] = float(((W - t1[m])).sum() / 3600.0)
        res['first_seen'][str(int(W))] = d
    res['n_vehicles'] = int(len(fo))
    res['scan_sec'] = round(time.time() - t0, 1)
    with open(os.path.join(OUT, name + '.json'), 'w', encoding='utf-8') as fh:
        json.dump(res, fh)
    print(name, nrows, res['n_frames'], res['scan_sec'], flush=True)


if __name__ == '__main__':
    args = sys.argv[1:]
    for a in args:
        name, path = a.split('=', 1)
        scan(name, path)
    print('ALL_DONE', flush=True)
