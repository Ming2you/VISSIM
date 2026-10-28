# FO gate (2026-10-27 KST, D-K9-113): build pristine causal T=900 replay inputs from the RECORDED B runs v3c3-s31/s41/s43
# (codex runner, FRZ_B1, B config; read-only source). Derived from work/gate1/g1_build_inputs.py (51aa645e..., gate 1 of B);
# the copy rules are the same: byte copies of the network .inpx/.sig/.err, the previous command (action_<T-150>.json/.csv and its
# .applied if any), vsl_readback.csv / signal_readback.csv, obs150 capture/mer/err <= T and derived/vsl_cohorts < T,
# obs150_install.json, mer_index.json, lane_observations frame <= T; only state_T.json and the run provenance are relocated
# (textual prefix swap). Differences from g1: sources = B runs (not V-A); relocation = B run folder -> gate working run folder
# and FRZ_B1 -> FRZ_FO (the obs150 detector table lives inside the frozen tree in B, so no separate obs swap); the provenance is
# always the FO runner -PreflightOnly output of the same seed and tuning, with run_id/name/network path of the recorded run and
# the real FRZ_FO freeze pin; the seed is read from the B provenance and must equal the label seed.
# Writes only under D:/VISSIM-merge/k8_gate_trees/codexhandoff/fo/gate/pristine/<label>/T<t6>.
# usage: python -B fog_build_inputs.py --preflight=<run_provenance.json> --frz=<FRZ_FO> [--g=<gate root, self-test only>] <label> T [T ...]
#        label: b_s31 b_s41 b_s43 (FO config) | b_s31b (B config control, same recorded state as b_s31)
import hashlib, json, os, re, shutil, sys
BS = chr(92)
SOURCES = {}
for _s in (31, 41, 43):
    SOURCES['b_s%d' % _s] = (_s, 'D:/VISSIM_runs/20261026_codex_b_v3c3/s%d/sdmpc' % _s, 'decisions_sdmpc31_sdmpc9000_s%d' % _s,
                             'run_provenance_sdmpc31_sdmpc9000_s%d.json' % _s,
                             'D:' + BS + 'VISSIM_runs' + BS + '20261026_codex_b_v3c3' + BS + ('s%d' % _s) + BS + 'sdmpc')
SOURCES['b_s31b'] = SOURCES['b_s31']
ORIG_FROZEN = 'D:' + BS + 'VISSIM-merge' + BS + 'k8_gate_trees' + BS + 'codexhandoff' + BS + 'b1' + BS + 'frozen' + BS + 'sdmpc31_a49981ff_202610261410'
G = 'D:/VISSIM-merge/k8_gate_trees/codexhandoff/fo/gate'
NET_SHA = '3de889f0257d998bed50611f798ea388bcf69396dbc40e5726b1e88ebdd31c2e'


def esc(s):
    return s.replace(BS, BS + BS)


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def build(label, T, preflight, new_code):
    seed, src_run, DEC, prov_name, orig_run = SOURCES[label]
    t6 = '%06d' % T
    new_run = G.replace('/', BS) + BS + 'runs' + BS + label + BS + 'T' + t6 + BS + 'run'
    top = G + '/pristine/' + label + '/T' + t6
    root = top + '/run'
    if os.path.exists(top):
        raise SystemExit('pristine input exists already (no rebuild): ' + top)
    os.makedirs(root + '/network')
    os.makedirs(root + '/' + DEC + '/obs150')
    os.makedirs(root + '/' + DEC + '/lane_observations')
    man = []

    def cp(rel):
        s, d = src_run + '/' + rel, root + '/' + rel
        shutil.copy2(s, d)
        man.append((rel, sha(d), 'copy'))

    def relocate_text(txt):
        n = {'run': txt.count(esc(orig_run)), 'frozen': txt.count(esc(ORIG_FROZEN))}
        out = txt.replace(esc(orig_run), esc(new_run)).replace(esc(ORIG_FROZEN), esc(new_code))
        return out, n

    rec_prov = json.loads(open(src_run + '/' + prov_name, 'rb').read().decode('utf-8-sig'))
    if rec_prov.get('seed') != seed:
        raise SystemExit('recorded provenance seed %s != label seed %s' % (rec_prov.get('seed'), seed))
    pre = json.loads(open(preflight, 'rb').read().decode('utf-8-sig'))
    assert pre['files']['network']['sha256'] == rec_prov['files']['network']['sha256'] == NET_SHA
    assert pre['seed'] == rec_prov['seed'] == seed and pre['sim_period_sec'] == rec_prov['sim_period_sec'] == 9000
    pre['run_id'] = rec_prov['run_id']
    pre['name'] = rec_prov['name']
    pre['files']['network']['path'] = rec_prov['files']['network']['path'].replace(orig_run, new_run)
    frz_freeze = new_code.replace(BS, '/') + '/FREEZE.json'
    pre['observation']['freeze'] = {'path': frz_freeze.replace('/', BS), 'sha256': sha(frz_freeze)}
    pout = json.dumps(pre, ensure_ascii=False, indent=2)
    pn = {'synthesized_from_preflight': preflight, 'preflight_sha256': sha(preflight)}
    open(root + '/' + prov_name, 'wb').write(pout.encode('utf-8'))
    man.append((prov_name, sha(root + '/' + prov_name), 'relocated %s' % json.dumps(pn)))
    for f in sorted(os.listdir(src_run + '/network')):
        if f.endswith(('.inpx', '.sig', '.err')):
            cp('network/' + f)
    D = DEC + '/'
    prev = '%06d' % (T - 150)
    for f in ('action_' + prev + '.json', 'action_' + prev + '.csv'):
        if os.path.exists(src_run + '/' + D + f):
            cp(D + f)
    ap = src_run + '/' + D + 'action_' + prev + '.json.applied'
    applied_prev = os.path.exists(ap)
    if applied_prev:
        raw = open(ap, 'rb').read()
        txt = raw.decode('utf-16')
        assert txt.encode('utf-16') == raw, 'utf-16 roundtrip differs'
        n_ap = txt.count(orig_run)
        outb = txt.replace(orig_run, new_run).encode('utf-16')
        open(root + '/' + D + 'action_' + prev + '.json.applied', 'wb').write(outb)
        man.append((D + 'action_' + prev + '.json.applied', sha(root + '/' + D + 'action_' + prev + '.json.applied'), 'relocated utf-16 run=%d' % n_ap))
    for f in ('vsl_readback.csv', 'signal_readback.csv'):
        if os.path.exists(src_run + '/' + D + f):
            cp(D + f)
    for f in sorted(os.listdir(src_run + '/' + D + 'obs150')):
        m = re.match(r'^(capture|mer|err|derived|vsl_cohorts)_(\d{6})\.', f)
        if f in ('obs150_install.json', 'mer_index.json'):
            cp(D + 'obs150/' + f)
        elif m:
            t = int(m.group(2))
            kind = m.group(1)
            if (kind in ('capture', 'mer', 'err') and t <= T) or (kind in ('derived', 'vsl_cohorts') and t < T):
                cp(D + 'obs150/' + f)
    for f in sorted(os.listdir(src_run + '/' + D + 'lane_observations')):
        m = re.match(r'^frame_(\d{6})\.json$', f)
        if m and int(m.group(1)) <= T:
            cp(D + 'lane_observations/' + f)
    txt = open(src_run + '/' + D + 'state_' + t6 + '.json', 'rb').read().decode('utf-8')
    out, sn = relocate_text(txt)
    # an absolute path left in the relocated state that is neither inside the working run folder nor inside FRZ_FO
    # (the match is cut at 80 characters, so a prefix in either direction counts as inside)
    left = [o for o in re.findall(r'[A-Za-z]:' + re.escape(BS + BS) + r'[^"]{0,80}', out)
            if not any(o.startswith(esc(x)) or esc(x).startswith(o) for x in (new_run, new_code))]
    d = root + '/' + D + 'state_' + t6 + '.json'
    open(d, 'wb').write(out.encode('utf-8'))
    json.loads(out)
    man.append((D + 'state_' + t6 + '.json', sha(d), 'relocated %s' % json.dumps(sn)))
    rec = {'label': label, 'seed': seed, 'T': T, 'source_run': src_run, 'pristine_root': root, 'working_run_dir': new_run,
           'relocation': {orig_run: new_run, ORIG_FROZEN: new_code},
           'state_source_sha256': sha(src_run + '/' + D + 'state_' + t6 + '.json'),
           'previous_action_source_sha256': sha(src_run + '/' + D + 'action_' + prev + '.json'),
           'previous_applied_present': applied_prev,
           'state_paths_unrelocated_after': left,
           'files': [{'path': a, 'sha256': b, 'how': c} for a, b, c in man]}
    json.dump(rec, open(top + '/INPUT_MANIFEST.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(label, T, 'files', len(man), 'state', json.dumps(sn), 'prov', json.dumps(pn), 'applied_prev', applied_prev, 'unrelocated', left)
    return 0 if not left else 1


args = sys.argv[1:]
PRE = FRZ = None
while args and args[0].startswith('--'):
    k, v = args.pop(0).split('=', 1)
    if k == '--preflight':
        PRE = v
    elif k == '--frz':
        FRZ = v
    elif k == '--g':
        G = v.replace(chr(92), '/').rstrip('/')   # self-test only: another gate root
if not PRE or not FRZ or len(args) < 2:
    raise SystemExit('usage: fog_build_inputs.py --preflight=<prov> --frz=<FRZ_FO> <label> T [T ...]')
FRZ_BS = FRZ.replace('/', BS).rstrip(BS)
code = 0
for T in [int(x) for x in args[1:]]:
    code |= build(args[0], T, PRE, FRZ_BS)
sys.exit(code)
