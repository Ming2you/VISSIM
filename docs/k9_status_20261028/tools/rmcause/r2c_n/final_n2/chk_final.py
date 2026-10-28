# Read-only checks for the finalize step (VERIFY_N2 corrections). No writes except stdout.
import hashlib, json, subprocess
SP = r'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad'
U4 = SP + '/urban-b2/u4_saturation_table.json'
GWT8 = r'D:/VISSIM-merge/sim3-n31-k8'

b = open(U4, 'rb').read()
print('U4 sha256', hashlib.sha256(b).hexdigest())
d = json.loads(b.decode('utf-8'))
for idx in (20, 11):
    g = d['groups'][idx]
    print('groups[%d]' % idx, g.get('key'), g.get('status'))
    for k in ('per_seed', 'seeds', 'runs', 'sources'):
        if k in g:
            print('  ', k, json.dumps(g[k], ensure_ascii=False)[:900])

names = subprocess.run(['git', '-C', GWT8, 'ls-tree', '-r', '--name-only', 'c20aff1d'],
                       capture_output=True, text=True, encoding='utf-8').stdout.splitlines()
cand = [n for n in names if 'unsignalized_turns_v3c3_20261001.json' in n]
print('unsignalized files', cand)
for n in cand:
    raw = subprocess.run(['git', '-C', GWT8, 'show', 'c20aff1d:' + n], capture_output=True).stdout
    print('  sha256', hashlib.sha256(raw).hexdigest())
    s = raw.decode('utf-8')
    i = s.find('SC1004_N_SC1003_to_W')
    print('  ctx', s[max(0, i - 400):i + 600].replace('\n', ' ')[:1000])

# arithmetic for C2 (upper bound): 157 x (0.6/split) x (1436.3/885)
spl = json.loads(subprocess.run(['git', '-C', GWT8, 'show', 'c20aff1d:outputs/boundary_out_ramp_split_20260905_measured.json'],
                                capture_output=True).stdout.decode('utf-8'))
row = spl['links']['SC1004_W_out']
print('SPLIT row', json.dumps(row, ensure_ascii=False)[:400])
