# A0 driver: repeat one traced replay of decision T; after each failed attempt, restore every file that the
# ORIGINAL frozen tree had (evidence/original_FREEZE.json) and that the attempt was missing under a0/code,
# taking bytes only from read-only local sources whose sha256 equals the freeze record. Stops on success,
# on a non-file error, or when a needed file has no verified source.
import csv, hashlib, json, os, re, subprocess, sys, time
BS = chr(92)
T = int(sys.argv[1])
PREFIX = sys.argv[2]
MAXIT = int(sys.argv[3]) if len(sys.argv) > 3 else 25
A0 = 'D:/VISSIM-merge/k8_gate_trees/codexhandoff/a0'
CODE_W = A0.replace('/', BS) + BS + 'code' + BS
WORK = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/codex_handoff/work/a0'
REC = A0 + '/RESTORED_FILES.json'
LOG = A0 + '/iterate_' + PREFIX + '.jsonl'
FRZ = json.load(open('D:/VISSIM_handoff/20261024/evidence/original_FREEZE.json', encoding='utf-8'))['files']


def lp(p):
    return BS + BS + '?' + BS + os.path.abspath(p).replace('/', BS)


def sha_file(p):
    h = hashlib.sha256()
    with open(lp(p), 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


# sha -> candidate source paths (read-only)
index = {}
for r in csv.DictReader(open('D:/VISSIM_handoff/20261024/FILE_MANIFEST.csv', encoding='utf-8-sig')):
    if r['path'].startswith('sealed/'):
        continue
    index.setdefault(r['sha256'], []).append('D:/VISSIM_handoff/20261024/' + r['path'])
trees = ['D:/VISSIM-runtime-window264-recovery/sdmpc31_ca181e84_202610070539']
trees += sorted('D:/VISSIM_runtime/20261023_rolling_cea/frozen/' + d for d in os.listdir('D:/VISSIM_runtime/20261023_rolling_cea/frozen'))
for t in trees:
    try:
        fz = json.load(open(t + '/FREEZE.json', encoding='utf-8'))['files']
    except Exception:
        continue
    for p, h in fz.items():
        index.setdefault(h, []).append(t + '/' + p)
GWT8 = 'D:/VISSIM-merge/sim3-n31-k8'
COMMITS = ['ca181e843058872ac4726758625e5c4057daba5f', '886a014a303dd155e05cc33041796822abbc29b0']


def find_bytes(rel, want):
    for src in index.get(want, []):
        if os.path.isfile(lp(src)) and sha_file(src) == want:
            return open(lp(src), 'rb').read(), 'sha-index:' + src
    p = GWT8 + '/' + rel
    if os.path.isfile(lp(p)) and sha_file(p) == want:
        return open(lp(p), 'rb').read(), 'tree:' + p
    for c in COMMITS:
        r = subprocess.run(['git', '-C', 'D:/VISSIM-merge/repo', 'show', c + ':' + rel], capture_output=True)
        if r.returncode == 0:
            for v, b in (('raw', r.stdout), ('crlf', r.stdout.replace(b'\r\n', b'\n').replace(b'\n', b'\r\n'))):
                if hashlib.sha256(b).hexdigest() == want:
                    return b, 'git:%s:%s' % (c[:8], v)
    return None, None


def log(d):
    d['time'] = time.strftime('%Y-%m-%d %H:%M:%S')
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(json.dumps(d, ensure_ascii=False) + '\n')


rec = json.load(open(REC, encoding='utf-8')) if os.path.exists(REC) else []
for it in range(1, MAXIT + 1):
    label = '%s_it%02d' % (PREFIX, it)
    t0 = time.time()
    subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', WORK.replace('/', BS) + BS + 'run_replay.ps1',
                    '-T', str(T), '-Label', label, '-Trace', '-Note', 'iterate restore'], check=False)
    out = A0 + '/out/' + label + '/T%06d' % T
    st = json.loads(open(out + '/replay_state.json', encoding='utf-8-sig').read())
    err = open(out + '/stderr.txt', encoding='utf-8', errors='replace').read()[-4000:] if os.path.exists(out + '/stderr.txt') else ''
    trace = open(out + '/trace_opens.tsv', encoding='utf-8').read().splitlines() if os.path.exists(out + '/trace_opens.tsv') else []
    cand = set()
    for line in trace:
        kind, _, path = line.partition(chr(9))
        if kind == 'stat_missing' and path.upper().startswith(CODE_W.upper()):
            cand.add(path[len(CODE_W):].replace(BS, '/'))
    for m in re.finditer(r"No such file or directory: '([^']+)'", err):
        p = m.group(1).replace(BS + BS, BS)
        if p.upper().startswith(CODE_W.upper()):
            cand.add(p[len(CODE_W):].replace(BS, '/'))
    in_frz = sorted(c for c in cand if c in FRZ and not os.path.exists(lp(A0 + '/code/' + c)))
    not_frz = sorted(c for c in cand if c not in FRZ)
    restored, nosrc = [], []
    for rel in in_frz:
        b, src = find_bytes(rel, FRZ[rel])
        if b is None:
            nosrc.append(rel)
            continue
        dst = A0 + '/code/' + rel
        os.makedirs(os.path.dirname(lp(dst)), exist_ok=True)
        open(lp(dst), 'wb').write(b)
        rec.append({'path': rel, 'sha256': FRZ[rel], 'bytes': len(b), 'source': src, 'found_by': label})
        restored.append(rel)
    json.dump(rec, open(REC, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    last = err.strip().splitlines()[-1][:600] if err.strip() else ''
    log({'it': it, 'label': label, 'exit': st.get('exit_code'), 'wall': st.get('wall_sec'), 'restored': restored,
         'no_source': nosrc, 'missing_not_in_freeze': not_frz, 'last_stderr': last})
    if st.get('exit_code') == 0:
        log({'stop': 'success'})
        break
    if nosrc:
        log({'stop': 'needed file without verified source'})
        break
    if not restored:
        log({'stop': 'failure without restorable missing file'})
        break
