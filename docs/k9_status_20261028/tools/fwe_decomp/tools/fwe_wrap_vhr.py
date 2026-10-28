# -*- coding: utf-8 -*-
"""fwe_wrap_vhr.py - call the pinned CW/vhr/vhr_firstseen.run (sha 42e17585...) with only the output folder changed.

Usage: python -B fwe_wrap_vhr.py <tag> <fzp_path> <out_dir>
The original file is imported, never modified (python -B: no __pycache__ written next to it).
Writes <out_dir>/first_<tag>.json (same schema as the original tool). D-K9-106, 2026-10-27 KST.
"""
import hashlib, os, sys

VHR = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/codex_handoff/work/vhr'
PIN = '42e17585172e8c3cdc529ee0b0768ec958ab34729bbe686c590e70053ada4c94'


def main():
    tag, path, out_dir = sys.argv[1], sys.argv[2], sys.argv[3]
    src = os.path.join(VHR, 'vhr_firstseen.py')
    got = hashlib.sha256(open(src, 'rb').read()).hexdigest()
    if got != PIN:
        raise SystemExit(f'pin mismatch vhr_firstseen.py {got}')
    sys.dont_write_bytecode = True
    sys.path.insert(0, VHR)
    import vhr_firstseen as m
    os.makedirs(out_dir, exist_ok=True)
    m.OUT = out_dir
    m.run(tag, path)


if __name__ == '__main__':
    main()
