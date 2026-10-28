# vhr_scan.py - fresh FZP scanner for VERIFY_HANDOFF_RESULTS (2026-10-25).
# Independent of the authors' scan_fzp.py / omega701_recount.py.
# Reads each FZP once (read-only), keeps per-frame per-link vehicle counts,
# then integrates per link in two forms x two windows, plus LF-normalised hashes.
import hashlib, json, sys, time
from collections import Counter

OUT = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/codex_handoff/work/vhr/scan_out'

RUNS = {
    'joint': 'D:/VISSIM_handoff/20261024/raw/joint/sdmpc/vissim_eval/sdmpc31_sdmpc8100_s29_001.fzp',
    'nc_raw': 'D:/VISSIM_handoff/20261024/raw/nc/vissim_eval/sdmpc31_nc9000_s29_001.fzp',
    'lnc': 'D:/VISSIM_runs/vsl_repro_s29/none/run/vissim_eval/vsl_seed29_none_001.fzp',
    'va_s31': 'D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s31/vissim_eval/sdmpc31_sdmpc31_v3c3_k92va_s31_001.fzp',
    'nc3_s31': 'D:/VISSIM_runs/20261001_v3c3/s31_v3c3nc/run/vissim_eval/baseline_s31_v3c3nc_001.fzp',
    'j1_s31': 'D:/VISSIM_runs/20261004_sdmpc31_k8/sdmpc31_v3c3_k8j1r_s31/vissim_eval/sdmpc31_sdmpc31_v3c3_k8j1r_s31_001.fzp',
    'window': 'D:/VISSIM_handoff/20261024/raw/window/sdmpc/vissim_eval/sdmpc31_sdmpc8100_s29_001.fzp',
    'off': 'D:/VISSIM_handoff/20261024/raw/off/sdmpc/vissim_eval/sdmpc31_sdmpc8100_s29_001.fzp',
    'freeway_only': 'D:/VISSIM_handoff/20261024/raw/freeway_only/sdmpc/vissim_eval/sdmpc31_sdmpc8100_s29_001.fzp',
    'urban_only': 'D:/VISSIM_handoff/20261024/raw/urban_only/sdmpc/vissim_eval/sdmpc31_sdmpc8100_s29_001.fzp',
    'va_s41': 'D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s41/vissim_eval/sdmpc31_sdmpc31_v3c3_k92va_s41_001.fzp',
    'j1_s41': 'D:/VISSIM_runs/20261004_sdmpc31_k8/sdmpc31_v3c3_k8j1_s41/vissim_eval/sdmpc31_sdmpc31_v3c3_k8j1_s41_001.fzp',
    'nc3_s41': 'D:/VISSIM_runs/20261001_v3c3/s41_v3c3nc/run/vissim_eval/baseline_s41_v3c3nc_001.fzp',
    'va_s43': 'D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s43/vissim_eval/sdmpc31_sdmpc31_v3c3_k92va_s43_001.fzp',
    'j1_s43': 'D:/VISSIM_runs/20261004_sdmpc31_k8/sdmpc31_v3c3_k8j1_s43/vissim_eval/sdmpc31_sdmpc31_v3c3_k8j1_s43_001.fzp',
    'nc3_s43': 'D:/VISSIM_runs/20261001_v3c3/s43_v3c3nc/run/vissim_eval/baseline_s43_v3c3nc_001.fzp',
}


def scan(tag, path):
    t0 = time.time()
    frames = {}          # tenths -> Counter(link)
    h_pre = hashlib.sha256(); n_pre = 0      # data rows t <= 895.1
    h_8100 = hashlib.sha256(); n_8100 = 0    # data rows t <= 8100
    h_all = hashlib.sha256(); n_all = 0      # all data rows
    fh = hashlib.sha256()                    # raw file bytes
    n_nondata_after_header = 0
    seen_header = False
    with open(path, 'rb') as f:
        for line in f:
            fh.update(line)
            if not seen_header:
                if line.startswith(b'$VEHICLE:'):
                    seen_header = True
                continue
            c = line[:1]
            if not (b'0' <= c <= b'9'):
                n_nondata_after_header += 1
                continue
            lf = line[:-2] + b'\n' if line.endswith(b'\r\n') else (line if line.endswith(b'\n') else line + b'\n')
            p = line.split(b';', 3)
            tt = int(round(float(p[0]) * 10))
            link = p[2].decode('ascii').strip()
            fr = frames.get(tt)
            if fr is None:
                fr = Counter(); frames[tt] = fr
            fr[link] += 1
            h_all.update(lf); n_all += 1
            if tt <= 81000:
                h_8100.update(lf); n_8100 += 1
            if tt <= 8951:
                h_pre.update(lf); n_pre += 1
    times = sorted(frames)
    res = {
        'tag': tag, 'path': path, 'file_sha256': fh.hexdigest(),
        'rows_all': n_all, 'rows_le_8100': n_8100, 'rows_le_895_1': n_pre,
        'lf_sha_all': h_all.hexdigest(), 'lf_sha_le_8100': h_8100.hexdigest(), 'lf_sha_le_895_1': h_pre.hexdigest(),
        'nondata_lines_after_header': n_nondata_after_header,
        'n_frames': len(times), 'first_frame_s': times[0] / 10, 'last_frame_s': times[-1] / 10,
        'has_0p1_frame': 1 in frames, 'rows_0p1': sum(frames[1].values()) if 1 in frames else 0,
        'integrals': {},
    }

    def integrate(seq, w_end=None):
        # seq: list of (tenths, Counter); trapezoid per link; optional hold of last stock to w_end
        acc = Counter()
        for (ta, ca), (tb, cb) in zip(seq, seq[1:]):
            dt = (tb - ta) / 10.0
            for l in set(ca) | set(cb):
                acc[l] += dt * (ca.get(l, 0) + cb.get(l, 0)) / 2.0
        if w_end is not None and seq:
            tl, cl = seq[-1]
            dt = w_end - tl / 10.0
            for l, n in cl.items():
                acc[l] += dt * n
        return {l: v / 3600.0 for l, v in acc.items()}

    for W in (8100, 9000):
        # codex form: empty network at t=0, all frames (incl. 0.1 s) with t <= W, hold last stock to W
        seq = [(0, Counter())] + [(t, frames[t]) for t in times if t <= W * 10]
        res['integrals'][f'codex_{W}'] = integrate(seq, W)
        # our form: frames from 5.1 s (skip 0.1 s frame) to last frame <= W, no extension
        seq2 = [(t, frames[t]) for t in times if t >= 51 and t <= W * 10]
        res['integrals'][f'ours_{W}'] = integrate(seq2, None)
    res['scan_sec'] = round(time.time() - t0, 1)
    with open(f'{OUT}/{tag}.json', 'w', encoding='utf-8') as g:
        json.dump(res, g)
    print(tag, res['rows_all'], res['scan_sec'], flush=True)


if __name__ == '__main__':
    import os
    os.makedirs(OUT, exist_ok=True)
    tags = sys.argv[1:] or list(RUNS)
    for t in tags:
        scan(t, RUNS[t])
    with open(f'{OUT}/DONE.txt', 'w') as g:
        g.write(time.strftime('%Y-%m-%d %H:%M:%S') + '\n')
