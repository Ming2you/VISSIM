# vhr_firstseen.py - first-seen frame and link of every vehicle number (fresh). Read-only on FZP.
# Output per run: cumulative distinct vehicles first seen by each frame, split by first link (74 / 26 / other),
# plus last frame stock. Used for arm-to-arm uninserted-wait differences (common arrival stream assumption).
import json, sys, time
from collections import defaultdict

OUT = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/codex_handoff/work/vhr_fo/scan_out'   # [FO copy 2026-10-27 KST, COMPARE_RULE_FO: path constants only; the slot that held B now holds FO] [B copy 2026-10-26 KST, COMPARE_RULE_B: path constants only; slot "j1" = B runs v3c3-s31/s41/s43] 
RUNS = {
    'joint': 'D:/VISSIM_handoff/20261024/raw/joint/sdmpc/vissim_eval/sdmpc31_sdmpc8100_s29_001.fzp',
    'nc_raw': 'D:/VISSIM_handoff/20261024/raw/nc/vissim_eval/sdmpc31_nc9000_s29_001.fzp',
    'va_s31': 'D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s31/vissim_eval/sdmpc31_sdmpc31_v3c3_k92va_s31_001.fzp',
    'nc3_s31': 'D:/VISSIM_runs/20261001_v3c3/s31_v3c3nc/run/vissim_eval/baseline_s31_v3c3nc_001.fzp',
    'j1_s31': 'D:/VISSIM_runs/20261028_codex_fo_v3c3/s31/sdmpc/vissim_eval/sdmpc31_sdmpc9000_s31_001.fzp',   # FO copy: slot j1 = FO
    'window': 'D:/VISSIM_handoff/20261024/raw/window/sdmpc/vissim_eval/sdmpc31_sdmpc8100_s29_001.fzp',
    'off': 'D:/VISSIM_handoff/20261024/raw/off/sdmpc/vissim_eval/sdmpc31_sdmpc8100_s29_001.fzp',
    'va_s41': 'D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s41/vissim_eval/sdmpc31_sdmpc31_v3c3_k92va_s41_001.fzp',
    'j1_s41': 'D:/VISSIM_runs/20261028_codex_fo_v3c3/s41/sdmpc/vissim_eval/sdmpc31_sdmpc9000_s41_001.fzp',   # FO copy: slot j1 = FO
    'nc3_s41': 'D:/VISSIM_runs/20261001_v3c3/s41_v3c3nc/run/vissim_eval/baseline_s41_v3c3nc_001.fzp',
    'va_s43': 'D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s43/vissim_eval/sdmpc31_sdmpc31_v3c3_k92va_s43_001.fzp',
    'j1_s43': 'D:/VISSIM_runs/20261028_codex_fo_v3c3/s43/sdmpc/vissim_eval/sdmpc31_sdmpc9000_s43_001.fzp',   # FO copy: slot j1 = FO
    'nc3_s43': 'D:/VISSIM_runs/20261001_v3c3/s43_v3c3nc/run/vissim_eval/baseline_s43_v3c3nc_001.fzp',
}


def run(tag, path):
    t0 = time.time()
    first = {}
    seen_header = False
    with open(path, 'rb') as f:
        for line in f:
            if not seen_header:
                seen_header = line.startswith(b'$VEHICLE:'); continue
            if not (b'0' <= line[:1] <= b'9'):
                continue
            p = line.split(b';', 3)
            no = int(p[1])
            if no not in first:
                first[no] = (int(round(float(p[0]) * 10)), p[2].decode('ascii').strip())
    by = defaultdict(lambda: defaultdict(int))
    for no, (tt, link) in first.items():
        cat = '74' if link == '74' else ('26' if link == '26' else 'other')
        by[cat][tt] += 1
    links = defaultdict(int)
    for no, (tt, link) in first.items():
        links[link] += 1
    res = {'tag': tag, 'vehicles': len(first), 'by_cat': {c: dict(v) for c, v in by.items()},
           'first_link_top': sorted(links.items(), key=lambda kv: -kv[1])[:40], 'max_no': max(first), 'sec': round(time.time() - t0, 1)}
    json.dump(res, open(f'{OUT}/first_{tag}.json', 'w'))
    print(tag, len(first), res['sec'], flush=True)


if __name__ == '__main__':
    for t in (sys.argv[1:] or list(RUNS)):
        run(t, RUNS[t])
    open(f'{OUT}/FIRST_DONE.txt', 'w').write(time.strftime('%Y-%m-%d %H:%M:%S\n'))
