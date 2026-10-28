# V4a (VSL_OFFLINE, data-after declaration): first-seen frame and first link of every vehicle in the
# 64cf-s29 VSL-only run FZP (read only). Same logic as the pinned codex_handoff/work/vhr/vhr_firstseen.py
# (sha 42e17585...), only the run list and output folder differ.
import json, sys, time
from collections import defaultdict
OUT = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/c_port/vsl/out'
RUNS = {'vsl': 'D:/VISSIM_runs/vsl_repro_s29/vsl/run/vissim_eval/vsl_seed29_vsl_001.fzp'}


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
    res = {'tag': tag, 'fzp': path, 'vehicles': len(first), 'by_cat': {c: dict(v) for c, v in by.items()},
           'first_link_top': sorted(links.items(), key=lambda kv: -kv[1])[:40], 'max_no': max(first), 'sec': round(time.time() - t0, 1)}
    json.dump(res, open(f'{OUT}/first_{tag}.json', 'w'))
    print(tag, len(first), res['sec'], flush=True)


if __name__ == '__main__':
    for t in (sys.argv[1:] or list(RUNS)):
        run(t, RUNS[t])
