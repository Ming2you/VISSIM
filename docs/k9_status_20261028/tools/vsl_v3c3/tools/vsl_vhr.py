# -*- coding: utf-8 -*-
"""Run the pinned B-copy FZP scanners on the VSL runs (read-only on FZP). 2026-10-27 KST, vsl_v3c3 (PRE_VSL.md section 7).

Usage: python -B vsl_vhr.py <out_dir> <tag>=<fzp_path> [...]
  e.g. vsl_s31=D:/VISSIM_runs/20261027_vsl_v3c3/s31/run/vissim_eval/baseline_s31_v3c3vsl_001.fzp

Loads, after a sha256 check, the unchanged B copies of vhr_scan.py and vhr_firstseen.py
(SP/codex_handoff/work/vhr_b/, pinned in COMPARE_RULE_B section 7.2) as modules, points their output constant OUT to
<out_dir>, and calls scan(tag, path) (per-link integrals in two forms, LF-normalised hashes incl. lf_sha_le_895_1) and
run(tag, path) (first-seen frame and first link of every vehicle). No formula is copied or changed here.
"""
import hashlib, importlib.util, os, sys

CW = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/codex_handoff/work'
PINS = {CW + '/vhr_b/vhr_scan_b.py': '0c445bc4bf05f45f7638be8227f0f29c2b036c0f276083958ff6bac87a85466e',
        CW + '/vhr_b/vhr_firstseen_b.py': 'd5c3c126490e4d1260063b51a9b97b4948b7c1ac35846c32761423c90088471b'}


def load(path, name):
    got = hashlib.sha256(open(path, 'rb').read()).hexdigest()
    if got != PINS[path]:
        raise SystemExit('pinned scanner changed: %s %s' % (path, got))
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main():
    out = sys.argv[1]
    pairs = [a.split('=', 1) for a in sys.argv[2:]]
    os.makedirs(out, exist_ok=True)
    sc = load(CW + '/vhr_b/vhr_scan_b.py', 'vhr_scan_b')
    fs = load(CW + '/vhr_b/vhr_firstseen_b.py', 'vhr_firstseen_b')
    sc.OUT = out
    fs.OUT = out
    for tag, path in pairs:
        sc.scan(tag, path)
        fs.run(tag, path)
    print('vsl_vhr done', [t for t, _ in pairs])


if __name__ == '__main__':
    main()
