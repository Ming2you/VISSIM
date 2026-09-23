r"""Sort sim3's untracked files into what should and should not be pushed.

Classes, first match wins:
  cache      generated at run time (marshal/numba/pycache) -- never commit
  large      over 50 MB -- GitHub rejects >100 MB, and these are local artefacts
  required   referenced by the deployed SDMPC config or pinned by the lane plant
             manifest; without them sim3 cannot run the decision that was verified today
  today      created or modified on 2026-09-23 (today's configs, harness, restored inputs)
  backfill   everything else: the controller worktree's pre-existing untracked
             diagnostics, copied in only so the merged tree was complete on disk
Writes one path list per class next to this script's scratch output.
"""
import datetime
import io
import json
import os
import re
import sys

ROOT = r'D:\VISSIM-merge\sim3'
LIST = sys.argv[1]
OUT = sys.argv[2]
CONFIGS = ['diagnostics/sdmpc_pfo_caps_20260922/config_candidate_obs1.json',
           'diagnostics/sdmpc_pfo_caps_20260922/config_candidate.json']
TODAY = datetime.date(2026, 9, 23)
PAT = re.compile(r'"([A-Za-z0-9_./\\-]+\.(?:json|csv|vbs|py|inpx|sig|txt|md|pickle))"')


def required_set():
    need = set()
    for cfg in CONFIGS:
        p = os.path.join(ROOT, cfg.replace('/', os.sep))
        if os.path.exists(p):
            need.add(cfg)
            for ref in PAT.findall(io.open(p, encoding='utf-8-sig').read()):
                need.add(ref.replace('\\', '/'))
    plant = os.path.join(ROOT, 'diagnostics', 'lane_plant_20260921', 'plant.json')
    if os.path.exists(plant):
        need.add('diagnostics/lane_plant_20260921/plant.json')
        for pin in json.load(io.open(plant, encoding='utf-8-sig'))['sources'].values():
            need.add(pin['path'].replace('\\', '/'))
    return need


def main():
    paths = [l.strip().strip('"') for l in io.open(LIST, encoding='utf-8') if l.strip()]
    need = required_set()
    classes = {k: [] for k in ('cache', 'large', 'required', 'today', 'backfill')}
    for p in paths:
        f = os.path.join(ROOT, p.replace('/', os.sep))
        if not os.path.isfile(f):
            continue
        size = os.path.getsize(f)
        mdate = datetime.date.fromtimestamp(os.path.getmtime(f))
        if ('__tangentcache__' in p or '__pycache__' in p or p.endswith(('.nbi', '.nbc', '.pyc', '.mcode'))):
            cls = 'cache'
        elif size > 50e6:
            cls = 'large'
        elif p in need:
            cls = 'required'
        elif mdate >= TODAY:
            cls = 'today'
        else:
            cls = 'backfill'
        classes[cls].append((size, p))
    os.makedirs(OUT, exist_ok=True)
    for cls, rows in classes.items():
        io.open(os.path.join(OUT, cls + '.txt'), 'w', encoding='utf-8').write(
            '\n'.join(p for _, p in sorted(rows, key=lambda r: r[1])) + '\n')
        print('%-9s %5d files  %9.1f MB' % (cls, len(rows), sum(s for s, _ in rows) / 1e6))
    print('\nrequired (config-referenced / plant-pinned):')
    for s, p in sorted(classes['required'], key=lambda r: r[1]):
        print('  %8.2f MB  %s' % (s / 1e6, p))
    print('\ntoday:')
    for s, p in sorted(classes['today'], key=lambda r: r[1]):
        print('  %8.2f MB  %s' % (s / 1e6, p))
    print('\nrequired paths NOT present as untracked (already tracked or absent):',
          len([n for n in need if n not in {p for _, p in classes['required']}]))


if __name__ == '__main__':
    main()
