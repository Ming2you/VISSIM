r"""Resolve the lane plant manifest's pinned sources into the merged tree.

`lane_plant_runtime.read_pin` resolves each source with strict=True and then
checks its sha256, so a missing pin aborts the very first decision of a run. The
files it points at live under `decisions_*/` directories, which `.gitignore:3`
excludes -- so they were never in the merge snapshot and an untracked-file sweep
does not see them either.

Copies only what sim3 lacks, and verifies every pin's digest afterwards so a
silent mismatch cannot survive this script.
"""
import hashlib
import io
import json
import os
import shutil
import sys

SIM = r'D:\VISSIM-merge\sim3'
CTRL = r'C:\Users\TRLAB\Documents\ChatGPT\VISSIM\.worktrees\sdmpc-tangent-20260921'
MANIFEST = os.path.join('diagnostics', 'lane_plant_20260921', 'plant.json')


def digest(path):
    return hashlib.sha256(io.open(path, 'rb').read()).hexdigest()


def main():
    apply = '--apply' in sys.argv
    document = json.load(io.open(os.path.join(SIM, MANIFEST), encoding='utf-8-sig'))
    sources = document['sources']
    copied, ok, broken = [], [], []

    for key, pin in sources.items():
        rel = pin['path'].replace('/', os.sep)
        dst, src = os.path.join(SIM, rel), os.path.join(CTRL, rel)
        if not os.path.exists(dst):
            if not os.path.isfile(src):
                broken.append((key, pin['path'], 'absent from both trees'))
                continue
            print('  MISSING %-18s %s' % (key, pin['path']))
            if apply:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
                copied.append(key)
            else:
                continue
        actual = digest(dst)
        if actual != pin['sha256']:
            broken.append((key, pin['path'], 'sha256 %s != pinned %s' % (actual[:16], pin['sha256'][:16])))
        else:
            ok.append(key)

    print('\npins: %d   verified: %d   copied: %d   broken: %d'
          % (len(sources), len(ok), len(copied), len(broken)))
    for key, path, why in broken:
        print('  BROKEN %-18s %s\n         %s' % (key, path, why))
    if not apply:
        print('(dry run -- pass --apply)')
    return 1 if broken else 0


if __name__ == '__main__':
    raise SystemExit(main())
