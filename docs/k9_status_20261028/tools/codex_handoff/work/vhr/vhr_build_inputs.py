# vhr_build_inputs.py - my own "as it existed at decision T" input tree for one joint decision replay.
# Rule (independent of the A0 builder): every raw file of the joint run folder that existed when decision T
# started; outputs of decision T itself (action_T.*, obs150/derived_T, obs150/vsl_cohorts_T) are left out;
# whole-run append files are cut back to the time T (readback CSV rows with sim_sec < T, mer_index entries <= T).
# Only the two absolute prefixes are relocated, as bytes, in state_T.json and run_provenance.
import hashlib, json, os, re, shutil, sys

T = int(sys.argv[1])
RAW = 'D:/VISSIM_handoff/20261024/raw/joint/sdmpc'
BASE = 'D:/VISSIM-merge/k8_gate_trees/codexhandoff/vhr'
RUN = f'{BASE}/runs/T{T:06d}/sdmpc'
DECN = 'decisions_sdmpc31_sdmpc8100_s29'
CODE_WIN = 'D:\\VISSIM-merge\\k8_gate_trees\\codexhandoff\\vhr\\code'
RUN_WIN = f'D:\\VISSIM-merge\\k8_gate_trees\\codexhandoff\\vhr\\runs\\T{T:06d}\\sdmpc'
OLD_RUN = 'E:\\VISSIM_runs\\20261012_adopted355_optimized_s29_8100\\sdmpc'
OLD_CODE = 'D:\\VISSIM_runtime\\20261012_adopted355_vsl_three\\frozen\\sdmpc31_ca181e84_202610121132'
if os.path.exists(RUN):
    raise SystemExit('run tree exists: ' + RUN)
log = {'T': T, 'run': RUN, 'files': []}


def sha(b):
    return hashlib.sha256(b).hexdigest()


def esc(s):  # JSON string escaping of backslashes
    return s.replace('\\', '\\\\').encode('utf-8')


def put(rel, data, how):
    p = f'{RUN}/{rel}'
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'wb') as f:
        f.write(data)
    log['files'].append({'path': rel, 'sha256': sha(data), 'bytes': len(data), 'how': how})


def relocate(b):
    n1 = b.count(esc(OLD_RUN)); n2 = b.count(esc(OLD_CODE))
    b = b.replace(esc(OLD_RUN), esc(RUN_WIN)).replace(esc(OLD_CODE), esc(CODE_WIN))
    left = len(re.findall(rb'E:\\\\VISSIM_runs|VISSIM_runtime\\\\20261012', b))
    return b, f'relocated run={n1} code={n2} left={left}'


def tnum(name):
    m = re.search(r'_(\d{6})(?:\.|_)', name)
    return int(m.group(1)) if m else None


# run root
for fn in os.listdir(RAW):
    p = f'{RAW}/{fn}'
    if fn.startswith('run_provenance_'):
        b, how = relocate(open(p, 'rb').read()); put(fn, b, how)
# network folder (inputs + whole-run VISSIM logs as received; no SHA256SUMS, no .results dir)
for fn in sorted(os.listdir(f'{RAW}/network')):
    p = f'{RAW}/network/{fn}'
    if fn == 'SHA256SUMS.txt' or os.path.isdir(p):
        continue
    put(f'network/{fn}', open(p, 'rb').read(), 'copy')
# decision folder
D = f'{RAW}/{DECN}'
for fn in sorted(os.listdir(D)):
    p = f'{D}/{fn}'
    if os.path.isdir(p) or fn == 'SHA256SUMS.txt':
        continue
    if fn in ('signal_readback.csv', 'vsl_readback.csv'):
        lines = open(p, 'rb').read().splitlines(keepends=True)
        keep = [lines[0]] + [l for l in lines[1:] if int(l.split(b',', 1)[0]) < T]
        put(f'{DECN}/{fn}', b''.join(keep), f'cut sim_sec<{T}: {len(keep)-1}/{len(lines)-1} rows')
        continue
    t = tnum(fn)
    if t is None:
        log.setdefault('skipped_untimed', []).append(fn); continue
    if fn.startswith('state_') and t == T:
        b, how = relocate(open(p, 'rb').read()); put(f'{DECN}/{fn}', b, how)
    elif t < T:
        put(f'{DECN}/{fn}', open(p, 'rb').read(), 'copy')
# obs150
for fn in sorted(os.listdir(f'{D}/obs150')):
    p = f'{D}/obs150/{fn}'
    if fn == 'SHA256SUMS.txt':
        continue
    if fn == 'mer_index.json':
        raw = open(p, 'rb').read(); doc = json.loads(raw)
        canon = (json.dumps(doc, sort_keys=True, separators=(',', ':'), ensure_ascii=False) + '\n').encode('utf-8')
        doc2 = dict(doc); doc2['entries'] = [e for e in doc['entries'] if e['sim_sec'] <= T]
        out = (json.dumps(doc2, sort_keys=True, separators=(',', ':'), ensure_ascii=False) + '\n').encode('utf-8')
        put(f'{DECN}/obs150/{fn}', out, f'cut entries<= {T}: {len(doc2["entries"])}/{len(doc["entries"])}; canonical_roundtrip_equal={canon == raw}')
        continue
    t = tnum(fn)
    if t is None:
        put(f'{DECN}/obs150/{fn}', open(p, 'rb').read(), 'copy untimed'); continue
    if fn.startswith(('derived_', 'vsl_cohorts_')):
        if t < T:
            put(f'{DECN}/obs150/{fn}', open(p, 'rb').read(), 'copy')
    elif t <= T:
        put(f'{DECN}/obs150/{fn}', open(p, 'rb').read(), 'copy')
# lane observations
for fn in sorted(os.listdir(f'{D}/lane_observations')):
    p = f'{D}/lane_observations/{fn}'
    if fn == 'SHA256SUMS.txt':
        continue
    t = tnum(fn)
    if t is None:
        put(f'{DECN}/lane_observations/{fn}', open(p, 'rb').read(), 'copy untimed'); continue
    if t <= T:
        put(f'{DECN}/lane_observations/{fn}', open(p, 'rb').read(), 'copy')
json.dump(log, open(f'{BASE}/inputs_T{T:06d}.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(len(log['files']), 'files;', [f for f in log['files'] if f['how'] != 'copy'], log.get('skipped_untimed'))
