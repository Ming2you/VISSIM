# vhr_cmp.py - my bit-identity check for one replayed joint decision (fresh; not the A0 s13/s27 scripts).
import csv, hashlib, io, json, sys

T = int(sys.argv[1]); LAB = sys.argv[2]
t6 = f'{T:06d}'
REC = 'D:/VISSIM_handoff/20261024/raw/joint/sdmpc/decisions_sdmpc31_sdmpc8100_s29'
MINE = f'D:/VISSIM-merge/k8_gate_trees/codexhandoff/vhr/runs/T{t6}/sdmpc/decisions_sdmpc31_sdmpc8100_s29'
A0 = 'D:/VISSIM-merge/k8_gate_trees/codexhandoff/a0/out'
OTHERS = {'a0_env_hsw': f'{A0}/env_hsw/T{t6}/files/sdmpc/decisions_sdmpc31_sdmpc8100_s29',
          'a0_base_rep2': f'{A0}/base_rep2/T{t6}/files/sdmpc/decisions_sdmpc31_sdmpc8100_s29',
          'a0_base': f'{A0}/base/T{t6}/files/sdmpc/decisions_sdmpc31_sdmpc8100_s29',
          'a0_spd_hsw': f'{A0}/spd_hsw/T{t6}/files/sdmpc/decisions_sdmpc31_sdmpc8100_s29',
          'a0_env_hsw_idle': f'{A0}/env_hsw_idle/T{t6}/files/sdmpc/decisions_sdmpc31_sdmpc8100_s29'}
R2 = ['seven_action_fields_sha256', 'ordered_physical_rows_sha256', 'expected_live_metadata_sha256', 'expected_csv_sha256', 'ordered_row_count']


def fsha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def load(d):
    try:
        w = json.load(open(f'{d}/action_{t6}.joint_written.json', encoding='utf-8'))
        return dict(csv_sha=fsha(f'{d}/action_{t6}.csv'), r2={k: w[k] for k in R2}, r3=w['scored_action_token'],
                    rows=list(csv.reader(io.StringIO(open(f'{d}/action_{t6}.csv', encoding='utf-8').read()))))
    except FileNotFoundError:
        return None


rec = load(REC); mine = load(MINE)
out = {'T': T, 'label': LAB, 'record': {k: v for k, v in rec.items() if k != 'rows'}}


def compare(x, name):
    if x is None:
        return {'present': False}
    r = {'present': True, 'R1_csv_equal': x['csv_sha'] == rec['csv_sha'], 'csv_sha': x['csv_sha'],
         'R2_equal': {k: x['r2'][k] == rec['r2'][k] for k in R2}, 'R3_equal': x['r3'] == rec['r3'], 'r3': x['r3']}
    hdr = rec['rows'][0]
    diffs = [i for i, (a, b) in enumerate(zip(x['rows'], rec['rows'])) if a != b]
    r['rows'] = len(x['rows']) - 1; r['rows_record'] = len(rec['rows']) - 1; r['rows_differing'] = len(diffs)
    kinds = {}
    for i in diffs:
        kinds[x['rows'][i][0] if x['rows'][i] else '?'] = kinds.get(x['rows'][i][0] if x['rows'][i] else '?', 0) + 1
    r['differing_by_first_col'] = kinds; r['header'] = hdr
    return r


out['mine'] = compare(mine, 'mine')
for k, d in OTHERS.items():
    o = load(d)
    if o is not None:
        out[k] = compare(o, k)
        out[k]['equal_to_mine_csv'] = (mine is not None and o['csv_sha'] == mine['csv_sha'])
        out[k]['equal_to_mine_r3'] = (mine is not None and o['r3'] == mine['r3'])


# first different progress line vs record (ignore elapsed_sec)
def prog(d):
    L = []
    for line in open(f'{d}/action_{t6}.joint.progress.jsonl', encoding='utf-8'):
        o = json.loads(line); o.pop('elapsed_sec', None); L.append(o)
    return L


try:
    a, b = prog(MINE), prog(REC)
    first = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), None)
    out['progress'] = dict(lines_mine=len(a), lines_record=len(b), first_diff_line_1based=(None if first is None else first + 1),
                           mine=(a[first] if first is not None else None), record=(b[first] if first is not None else None))
except FileNotFoundError as e:
    out['progress'] = str(e)
json.dump(out, open(f'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/codex_handoff/work/vhr/cmp_{LAB}_T{t6}.json', 'w'), indent=1, ensure_ascii=False)
print(json.dumps({k: (v if k in ('T', 'label') else {kk: vv for kk, vv in v.items() if kk not in ('header',)} if isinstance(v, dict) else v) for k, v in out.items()}, ensure_ascii=False, indent=0)[:4000])
