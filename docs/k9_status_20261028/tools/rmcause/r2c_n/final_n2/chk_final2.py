# Read-only: U4 groups[20] keys + per-seed fields; unsignalized file top-level keys and where SC1004_N_SC1003_to_W sits.
import json, subprocess
SP = r'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad'
d = json.load(open(SP + '/urban-b2/u4_saturation_table.json', encoding='utf-8'))
g = d['groups'][20]
print(sorted(g.keys()))
def walk(o, path=''):
    if isinstance(o, dict):
        for k, v in o.items():
            if 'seed' in k.lower():
                print(path + '/' + k, json.dumps(v, ensure_ascii=False)[:700])
            walk(v, path + '/' + k)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            walk(v, path + '/%d' % i)
walk(g, '/groups/20')
raw = subprocess.run(['git', '-C', r'D:/VISSIM-merge/sim3-n31-k8', 'show',
    'c20aff1d:diagnostics/sdmpc_n31_20260924/urban/unsignalized_turns_v3c3_20261001.json'], capture_output=True).stdout
u = json.loads(raw.decode('utf-8'))
print('top keys', list(u.keys()))
for k, v in u.items():
    if isinstance(v, list) and any(isinstance(x, dict) and x.get('movement') == 'SC1004_N_SC1003_to_W' for x in v):
        print('found under', k)
