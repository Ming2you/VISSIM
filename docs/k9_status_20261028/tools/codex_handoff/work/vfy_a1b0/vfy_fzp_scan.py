# -*- coding: utf-8 -*-
"""VERIFY_A1_B0 독립 FZP 스캔 (저자 도구 재사용 없음).

한 FZP 를 한 번 읽어 다음을 gzip JSON 으로 냄:
  - frames: 데이터 프레임 시각(SIMSEC 글자 그대로, float) 목록
  - flc: 프레임마다 [링크, 차량수] 쌍 목록 (모든 링크·커넥터)
  - fh: 프레임마다 sha256(행들을 차량번호 순으로 정렬해 '\n' 으로 이은 바이트; 행 끝 CR/LF 제거)
  - prefix: t <= 895.1 데이터 행(파일 순서) 의 LF 정규화 sha256 과 행 수
  - first: 차량번호 -> [첫 관측 시각, 첫 관측 링크]
  - meta: 바이트, 데이터 행 수, 건너뛴 0.10 행 수, 격자(5.1+5k) 밖 프레임 수
옵션: --tmax T (T 보다 큰 프레임은 버림), --skip010 (SIMSEC 글자가 '0.10' 인 행 버림)
"""
import sys, json, gzip, hashlib, argparse, os, time


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('fzp')
    ap.add_argument('out')
    ap.add_argument('--tmax', type=float, default=1e18)
    ap.add_argument('--skip010', action='store_true')
    a = ap.parse_args()
    t0 = time.time()
    frames, flc, fh = [], [], []
    first = {}
    pre = hashlib.sha256()
    npre = 0
    nrows = 0
    nskip = 0
    cur_t = None
    cur_tf = None
    cur_cnt = {}
    cur_rows = []

    def flush():
        if cur_t is None:
            return
        frames.append(cur_tf)
        flc.append(sorted([int(k), v] for k, v in cur_cnt.items()))
        rows = sorted(cur_rows, key=lambda r: int(r.split(b';', 2)[1]))
        fh.append(hashlib.sha256(b'\n'.join(rows)).hexdigest())

    started = False
    with open(a.fzp, 'rb') as f:
        for line in f:
            if not started:
                if line.startswith(b'$VEHICLE:'):
                    started = True
                continue
            line = line.rstrip(b'\r\n')
            if not line:
                continue
            p = line.split(b';', 3)
            ts = p[0]
            if a.skip010 and ts == b'0.10':
                nskip += 1
                continue
            if ts != cur_t:
                tf = float(ts)
                if tf > a.tmax:
                    break
                flush()
                cur_t, cur_tf, cur_cnt, cur_rows = ts, tf, {}, []
            tf = cur_tf
            link = p[2]
            cur_cnt[link] = cur_cnt.get(link, 0) + 1
            cur_rows.append(line)
            veh = int(p[1])
            if veh not in first:
                first[veh] = [tf, int(link)]
            if tf <= 895.1 + 1e-9:
                pre.update(line + b'\n')
                npre += 1
            nrows += 1
    flush()
    off_grid = sum(1 for t in frames if abs(((t - 5.1) / 5.0) - round((t - 5.1) / 5.0)) > 1e-6)
    steps = [round(frames[i + 1] - frames[i], 6) for i in range(len(frames) - 1)]
    irregular = sum(1 for s in steps if abs(s - 5.0) > 1e-6)
    out = {
        'tool': 'vfy_fzp_scan.py',
        'fzp': a.fzp, 'bytes': os.path.getsize(a.fzp), 'tmax': a.tmax, 'skip010': a.skip010,
        'data_rows': nrows, 'skipped_010_rows': nskip, 'n_frames': len(frames),
        'first_frame': frames[0] if frames else None, 'last_frame': frames[-1] if frames else None,
        'off_grid_frames': off_grid, 'irregular_steps': irregular,
        'n_vehicles': len(first), 'prefix_le_895_1': {'rows': npre, 'sha256': pre.hexdigest()},
        'frames': frames, 'flc': flc, 'fh': fh,
        'first': {str(k): v for k, v in first.items()},
        'scan_sec': round(time.time() - t0, 1),
    }
    with gzip.open(a.out, 'wt', encoding='utf-8') as g:
        json.dump(out, g)
    print(json.dumps({k: out[k] for k in ('data_rows', 'skipped_010_rows', 'n_frames', 'first_frame', 'last_frame',
                                         'off_grid_frames', 'irregular_steps', 'n_vehicles', 'scan_sec')}))


if __name__ == '__main__':
    main()
