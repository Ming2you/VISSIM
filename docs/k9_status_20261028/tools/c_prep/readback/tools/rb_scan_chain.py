# -*- coding: utf-8 -*-
"""rb_scan_chain.py (c_port/readback, 2026-10-27 KST) - runs rb_fzp_scan.py over the six FZPs one after another (one job).

Usage: python -B rb_scan_chain.py <out_dir>
Read-only toward run folders; writes <out_dir>/scan_<tag>.json and prints one line per FZP.
"""
import os
import subprocess
import sys
import time

TOOLS = os.path.dirname(os.path.abspath(__file__))
RUNS = [
    ('b31', 'D:/VISSIM_runs/20261026_codex_b_v3c3/s31/sdmpc/vissim_eval/sdmpc31_sdmpc9000_s31_001.fzp'),
    ('b41', 'D:/VISSIM_runs/20261026_codex_b_v3c3/s41/sdmpc/vissim_eval/sdmpc31_sdmpc9000_s41_001.fzp'),
    ('b43', 'D:/VISSIM_runs/20261026_codex_b_v3c3/s43/sdmpc/vissim_eval/sdmpc31_sdmpc9000_s43_001.fzp'),
    ('va31', 'D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s31/vissim_eval/sdmpc31_sdmpc31_v3c3_k92va_s31_001.fzp'),
    ('va41', 'D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s41/vissim_eval/sdmpc31_sdmpc31_v3c3_k92va_s41_001.fzp'),
    ('va43', 'D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s43/vissim_eval/sdmpc31_sdmpc31_v3c3_k92va_s43_001.fzp'),
]


def main():
    out = sys.argv[1]
    for tag, fzp in RUNS:
        t0 = time.time()
        rc = subprocess.call([sys.executable, '-B', os.path.join(TOOLS, 'rb_fzp_scan.py'), fzp,
                              os.path.join(out, 'inpx_%s.json' % tag), os.path.join(out, 'scan_%s.json' % tag)])
        print('CHAIN', tag, 'rc', rc, 'sec', round(time.time() - t0, 1), flush=True)
        if rc != 0:
            sys.exit(rc)
    print('CHAIN_DONE', flush=True)


if __name__ == '__main__':
    main()
