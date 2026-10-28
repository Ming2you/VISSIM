# A1 wall-time estimate on this PC = codex-PC per-decision wall (runlog CONTROLLER_DECISION) x measured replay ratio
# + codex-PC non-decision time x VISSIM ratio. Inputs are read only. usage: s28_a1_estimate.py prof.json out.json
import json, re, sys

RUNLOG = 'D:/VISSIM_handoff/20261024/raw/joint/sdmpc/runlog_sdmpc31_sdmpc8100_s29.txt'
LAUNCH = 'D:/VISSIM_handoff/20261024/raw/joint/sdmpc/launch.log'
pat = re.compile(r'^CONTROLLER_DECISION sim_sec=(\d+) wall_sec=([0-9.]+) result=exit=(-?\d+)')
dec = [(int(m.group(1)), float(m.group(2)), int(m.group(3))) for m in (pat.match(l) for l in open(RUNLOG, encoding='utf-8', errors='replace')) if m]
elapsed = int(re.search(r'OK sdmpc31_sdmpc8100_s29 attempt=1 elapsed=(\d+)s', open(LAUNCH, encoding='utf-8', errors='replace').read()).group(1))
heavy = [d for d in dec if d[0] >= 900]
light = [d for d in dec if d[0] < 900]
sum_heavy = sum(w for _, w, _ in heavy)
sum_light = sum(w for _, w, _ in light)
non_decision = elapsed - sum_heavy - sum_light
prof = json.load(open(sys.argv[1], encoding='utf-8'))
rec = {r['T']: r['budget_wall_sec'] for r in prof if r.get('label') == 'recorded'}
ratios = {}
for r in prof:
    if r.get('label') in ('recorded', 'r900c_it01') or 'error' in r:
        continue
    ratios.setdefault(r['label'], {})[r['T']] = round(r['budget_wall_sec'] / rec[r['T']], 4)
allr = [v for d in ratios.values() for v in d.values()]
lo, hi = min(allr), max(allr)
# VISSIM part: codex NC 9000 s = 2829 s (raw nc launch.log); local LNC 9000 s = 6005 s with two other VISSIM runs (REPRO_RESULT.md:9-12)
vr = round(6005 / 2829, 4)
est = {'codex_elapsed_sec': elapsed, 'codex_decisions_ge900': len(heavy), 'codex_sum_ge900_sec': round(sum_heavy, 1),
       'codex_mean_ge900_sec': round(sum_heavy / len(heavy), 1), 'codex_max_ge900': max(heavy, key=lambda d: d[1]),
       'codex_exit_nonzero': [d for d in dec if d[2] != 0], 'codex_sum_lt900_sec': round(sum_light, 1),
       'codex_non_decision_sec': round(non_decision, 1), 'replay_ratios': ratios, 'ratio_range': [lo, hi], 'vissim_ratio': vr,
       'thisPC_decisions_sec': [round(sum_heavy * lo), round(sum_heavy * hi)],
       'thisPC_max_decision_sec': [round(max(w for _, w, _ in heavy) * lo), round(max(w for _, w, _ in heavy) * hi)],
       'thisPC_light_sec': [round(sum_light * lo), round(sum_light * hi)],
       'thisPC_non_decision_sec': round(non_decision * vr),
       }
tot_lo = est['thisPC_decisions_sec'][0] + est['thisPC_light_sec'][0] + est['thisPC_non_decision_sec']
tot_hi = est['thisPC_decisions_sec'][1] + est['thisPC_light_sec'][1] + est['thisPC_non_decision_sec']
est['thisPC_total_sec'] = [tot_lo, tot_hi]
est['thisPC_total_h'] = [round(tot_lo / 3600, 2), round(tot_hi / 3600, 2)]
est['decisions_over_1800_if_ratio_hi'] = sum(1 for _, w, _ in heavy if w * hi > 1800)
est['ratio_at_which_max_hits_1800'] = round(1800 / max(w for _, w, _ in heavy), 3)
est['ratio_at_which_max_hits_2390'] = round(2390 / max(w for _, w, _ in heavy), 3)
json.dump(est, open(sys.argv[2], 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps(est, ensure_ascii=False))
