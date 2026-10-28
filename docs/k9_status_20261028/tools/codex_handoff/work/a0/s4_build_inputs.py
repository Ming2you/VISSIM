# A0 step 4: build pristine causal input trees for recorded joint decisions.
# Reads D:/VISSIM_handoff/20261024/raw/joint (read-only); writes only under a0/pristine.
# Rule: copy byte-identical; only state_T.json is relocated (two path prefixes, textual).
import hashlib, json, os, re, shutil, sys
BS = chr(92)
SRC = 'D:/VISSIM_handoff/20261024/raw/joint/sdmpc'
DEC = 'decisions_sdmpc31_sdmpc8100_s29'
A0 = 'D:/VISSIM-merge/k8_gate_trees/codexhandoff/a0'
ORIG_RUN = 'E:' + BS + 'VISSIM_runs' + BS + '20261012_adopted355_optimized_s29_8100' + BS + 'sdmpc'
ORIG_FROZEN = 'D:' + BS + 'VISSIM_runtime' + BS + '20261012_adopted355_vsl_three' + BS + 'frozen' + BS + 'sdmpc31_ca181e84_202610121132'
NEW_CODE = A0.replace('/', BS) + BS + 'code'


def esc(s):
    return s.replace(BS, BS + BS)


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def build(T):
    t6 = '%06d' % T
    new_run = A0.replace('/', BS) + BS + 'runs' + BS + 'T' + t6 + BS + 'sdmpc'
    root = A0 + '/pristine/T' + t6 + '/sdmpc'
    if os.path.exists(A0 + '/pristine/T' + t6):
        shutil.rmtree(A0 + '/pristine/T' + t6)
    os.makedirs(root + '/network')
    os.makedirs(root + '/' + DEC + '/obs150')
    os.makedirs(root + '/' + DEC + '/lane_observations')
    man = []

    def cp(rel):
        s, d = SRC + '/' + rel, root + '/' + rel
        shutil.copy2(s, d)
        man.append((rel, sha(d), 'copy'))

    ptxt = open(SRC + '/run_provenance_sdmpc31_sdmpc8100_s29.json', 'rb').read().decode('utf-8')
    np_run, np_fz = ptxt.count(esc(ORIG_RUN)), ptxt.count(esc(ORIG_FROZEN))
    pout = ptxt.replace(esc(ORIG_RUN), esc(new_run)).replace(esc(ORIG_FROZEN), esc(NEW_CODE))
    json.loads(pout)
    open(root + '/run_provenance_sdmpc31_sdmpc8100_s29.json', 'wb').write(pout.encode('utf-8'))
    man.append(('run_provenance_sdmpc31_sdmpc8100_s29.json', sha(root + '/run_provenance_sdmpc31_sdmpc8100_s29.json'), 'relocated run=%d frozen=%d' % (np_run, np_fz)))
    for f in sorted(os.listdir(SRC + '/network')):
        if f.endswith(('.inpx', '.sig', '.err')):
            cp('network/' + f)
    D = DEC + '/'
    prev = '%06d' % (T - 150)
    for f in ('action_' + prev + '.json', 'action_' + prev + '.csv'):
        if os.path.exists(SRC + '/' + D + f):
            cp(D + f)
    ap = SRC + '/' + D + 'action_' + prev + '.json.applied'
    if os.path.exists(ap):
        raw = open(ap, 'rb').read()
        txt = raw.decode('utf-16')
        assert txt.encode('utf-16') == raw, 'utf-16 roundtrip differs'
        n_ap = txt.count(ORIG_RUN)
        outb = txt.replace(ORIG_RUN, new_run).encode('utf-16')
        open(root + '/' + D + 'action_' + prev + '.json.applied', 'wb').write(outb)
        man.append((D + 'action_' + prev + '.json.applied', sha(root + '/' + D + 'action_' + prev + '.json.applied'), 'relocated utf-16 run=%d' % n_ap))
    cp(D + 'vsl_readback.csv')
    cp(D + 'signal_readback.csv')
    for f in sorted(os.listdir(SRC + '/' + D + 'obs150')):
        m = re.match(r'^(capture|mer|err|derived|vsl_cohorts)_(\d{6})\.', f)
        if f in ('obs150_install.json', 'mer_index.json'):
            cp(D + 'obs150/' + f)
        elif m:
            t = int(m.group(2))
            kind = m.group(1)
            if (kind in ('capture', 'mer', 'err') and t <= T) or (kind in ('derived', 'vsl_cohorts') and t < T):
                cp(D + 'obs150/' + f)
    for f in sorted(os.listdir(SRC + '/' + D + 'lane_observations')):
        m = re.match(r'^frame_(\d{6})\.json$', f)
        if m and int(m.group(1)) <= T:
            cp(D + 'lane_observations/' + f)
    # relocated state
    txt = open(SRC + '/' + D + 'state_' + t6 + '.json', 'rb').read().decode('utf-8')
    n_run = txt.count(esc(ORIG_RUN))
    n_fz = txt.count(esc(ORIG_FROZEN))
    other = re.findall(r'[A-Za-z]:' + re.escape(BS + BS) + r'[^"]{0,60}', txt)
    out = txt.replace(esc(ORIG_RUN), esc(new_run)).replace(esc(ORIG_FROZEN), esc(NEW_CODE))
    left = [o for o in re.findall(r'[A-Za-z]:' + re.escape(BS + BS) + r'[^"]{0,80}', out)
            if not (o.startswith(esc(new_run)) or o.startswith(esc(NEW_CODE)))]
    d = root + '/' + D + 'state_' + t6 + '.json'
    open(d, 'wb').write(out.encode('utf-8'))
    json.loads(out)
    man.append((D + 'state_' + t6 + '.json', sha(d), 'relocated run=%d frozen=%d' % (n_run, n_fz)))
    rec = {'T': T, 'pristine_root': root, 'working_run_dir': new_run, 'relocation': {ORIG_RUN: new_run, ORIG_FROZEN: NEW_CODE},
           'state_source_sha256': sha(SRC + '/' + D + 'state_' + t6 + '.json'),
           'state_paths_before': len(other), 'state_paths_unrelocated_after': left,
           'files': [{'path': a, 'sha256': b, 'how': c} for a, b, c in man]}
    json.dump(rec, open(A0 + '/pristine/T' + t6 + '/INPUT_MANIFEST.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(T, 'files', len(man), 'relocated run', n_run, 'frozen', n_fz, 'unrelocated', left)


for T in [int(x) for x in sys.argv[1:]]:
    build(T)
