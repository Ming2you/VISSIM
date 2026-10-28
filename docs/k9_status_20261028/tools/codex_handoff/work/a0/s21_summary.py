# Collect every A0 replay: wall, budget, R1-R3 vs recorded, command-CSV diff summary. Writes a0_summary.json
import csv, glob, json, os, subprocess, sys
A0 = 'D:/VISSIM-merge/k8_gate_trees/codexhandoff/a0'
WORK = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/codex_handoff/work/a0'
DEC = 'decisions_sdmpc31_sdmpc8100_s29'
REC = 'D:/VISSIM_handoff/20261024/raw/joint/sdmpc/' + DEC


def csvdiff(pa, pb):
    a = list(csv.DictReader(open(pa, encoding='utf-8'))); b = list(csv.DictReader(open(pb, encoding='utf-8')))
    rows, kinds, mx = 0, {}, {}
    for x, y in zip(a, b):
        d = [k for k in x if x[k] != y[k]]
        if d:
            rows += 1; kinds[x['kind']] = kinds.get(x['kind'], 0) + 1
            for k in d:
                try: mx[k] = round(max(mx.get(k, 0.0), abs(float(x[k]) - float(y[k]))), 6)
                except ValueError: mx[k] = 'text'
    return {'rows': rows, 'by_kind': kinds, 'max_abs': mx, 'n': [len(a), len(b)]}


out = []
for st in sorted(glob.glob(A0 + '/out/*/T*/replay_state.json')):
    d = os.path.dirname(st); label = d.replace('\\', '/').split('/')[-2]; T = int(d[-6:])
    s = json.loads(open(st, encoding='utf-8-sig').read())
    row = {'label': label, 'T': T, 'exit': s.get('exit_code'), 'wall_sec': s.get('wall_sec'), 'start': s.get('start'),
           'extra_env': s.get('extra_env'), 'trace': s.get('trace')}
    f = d + '/files/sdmpc/' + DEC
    t6 = '%06d' % T
    try:
        b = json.load(open(f + '/action_' + t6 + '.decision_budget.json', encoding='utf-8-sig'))
        row['budget_wall_sec'] = round(b['wall_sec'], 3); row['main_cpu_sec'] = b['cpu_sec']
    except Exception:
        pass
    if os.path.exists(f + '/action_' + t6 + '.csv'):
        row['vs_recorded'] = csvdiff(f + '/action_' + t6 + '.csv', REC + '/action_' + t6 + '.csv')
        jw = json.load(open(f + '/action_' + t6 + '.joint_written.json', encoding='utf-8-sig'))
        jr = json.load(open(REC + '/action_' + t6 + '.joint_written.json', encoding='utf-8-sig'))
        row['R1'] = row['vs_recorded']['rows'] == 0 and open(f + '/action_' + t6 + '.csv', 'rb').read() == open(REC + '/action_' + t6 + '.csv', 'rb').read()
        row['R2'] = all(jw.get(k) == jr.get(k) for k in ('seven_action_fields_sha256', 'ordered_physical_rows_sha256', 'expected_live_metadata_sha256', 'expected_csv_sha256', 'ordered_row_count'))
        row['R3'] = jw.get('scored_action_token') == jr.get('scored_action_token')
    rb = json.load(open(REC + '/action_' + t6 + '.decision_budget.json', encoding='utf-8-sig'))
    row['codex_budget_wall_sec'] = round(rb['wall_sec'], 3)
    if row.get('budget_wall_sec'):
        row['ratio_to_codex'] = round(row['budget_wall_sec'] / rb['wall_sec'], 3)
    out.append(row)
json.dump(out, open(WORK + '/a0_summary.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
for r in out:
    print(r['label'], r['T'], 'exit', r['exit'], 'wall', r['wall_sec'], 'budget', r.get('budget_wall_sec'), 'ratio', r.get('ratio_to_codex'),
          'R1', r.get('R1'), 'R2', r.get('R2'), 'R3', r.get('R3'), 'diffrows', (r.get('vs_recorded') or {}).get('rows'), (r.get('vs_recorded') or {}).get('max_abs'))
