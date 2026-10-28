# Gate 1 (copy of work/b0/b0_build_inputs.py 62dabb59..., path constants only): build pristine causal input trees from
# OUR recorded v3c3 closed-loop runs V-A v3c3-s31/s41/s43 (read-only source),
# in the same layout as work/a0/s4_build_inputs.py builds for the codex joint run.
# Writes only under D:/VISSIM-merge/k8_gate_trees/codexhandoff/gate1/pristine/<label>/T<t6>. Code root = FRZ_B0 (frozen).
# Rule: byte copies; only state_T.json, run_provenance and the previous .applied are relocated (textual prefix swap).
# usage: python -B g1_build_inputs.py --preflight=<run_provenance.json> <label> T [T ...]   (label: va_s31 va_s41 va_s43 va_s31gk)
import hashlib, json, os, re, shutil, sys
BS = chr(92)
SOURCES = {
    'va_s31': ('D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s31', 'decisions_sdmpc31_v3c3_k92va_s31',
               'run_provenance_sdmpc31_v3c3_k92va_s31.json',
               'D:' + BS + 'VISSIM_runs' + BS + '20261023_sdmpc31_k92' + BS + 'sdmpc31_v3c3_k92va_s31'),
}
SOURCES['va_s41'] = ('D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s41', 'decisions_sdmpc31_v3c3_k92va_s41',
                      'run_provenance_sdmpc31_v3c3_k92va_s41.json',
                      'D:' + BS + 'VISSIM_runs' + BS + '20261023_sdmpc31_k92' + BS + 'sdmpc31_v3c3_k92va_s41')
SOURCES['va_s43'] = ('D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s43', 'decisions_sdmpc31_v3c3_k92va_s43',
                      'run_provenance_sdmpc31_v3c3_k92va_s43.json',
                      'D:' + BS + 'VISSIM_runs' + BS + '20261023_sdmpc31_k92' + BS + 'sdmpc31_v3c3_k92va_s43')
SOURCES['va_s31gk'] = SOURCES['va_s31']   # same recorded run; inputs carry the provenance of the group-key tuning
ORIG_FROZEN = 'D:' + BS + 'VISSIM-merge' + BS + 'frozen' + BS + 'sdmpc31_c20aff1d_202610230833'
B0 = 'D:/VISSIM-merge/k8_gate_trees/codexhandoff/gate1'
NEW_CODE = 'D:' + BS + 'VISSIM-merge' + BS + 'k8_gate_trees' + BS + 'codexhandoff' + BS + 'b0' + BS + 'frozen' + BS + 'sdmpc31_a49981ff_202610260258'
OBS_OURS = ORIG_FROZEN + BS + 'diagnostics' + BS + 'sdmpc_n31_20260924' + BS + 'obs150' + BS + 'obs150_detectors_v2.csv'
OBS_CODEX_REL = 'diagnostics/sdmpc_n31_20260924/obs150/obs150_detectors_v2.csv'  # our v3c3 copy inside b0 (same CSV bytes as codex selected/obs150)
OBS_NEW = NEW_CODE + BS + OBS_CODEX_REL.replace('/', BS)


def esc(s):
    return s.replace(BS, BS + BS)


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def build(label, T):
    src_run, DEC, prov_name, orig_run = SOURCES[label]
    t6 = '%06d' % T
    new_run = B0.replace('/', BS) + BS + 'runs' + BS + label + BS + 'T' + t6 + BS + 'run'
    top = B0 + '/pristine/' + label + '/T' + t6
    root = top + '/run'
    if os.path.exists(top):
        shutil.rmtree(top)
    os.makedirs(root + '/network')
    os.makedirs(root + '/' + DEC + '/obs150')
    os.makedirs(root + '/' + DEC + '/lane_observations')
    man = []
    # obs150 detector table: ours must equal the codex copy byte for byte (R_NET §2.6)
    ours_obs = OBS_OURS.replace(BS, '/')
    codex_obs = NEW_CODE.replace(BS, '/') + '/' + OBS_CODEX_REL
    assert sha(ours_obs) == sha(codex_obs), 'obs150 detector table differs'

    def cp(rel):
        s, d = src_run + '/' + rel, root + '/' + rel
        shutil.copy2(s, d)
        man.append((rel, sha(d), 'copy'))

    def relocate_text(txt):
        n = {'obs': txt.count(esc(OBS_OURS)), 'run': txt.count(esc(orig_run)), 'frozen_other': 0}
        out = txt.replace(esc(OBS_OURS), esc(OBS_NEW)).replace(esc(orig_run), esc(new_run))
        n['frozen_other'] = out.count(esc(ORIG_FROZEN))
        out = out.replace(esc(ORIG_FROZEN), esc(NEW_CODE))
        return out, n

    ptxt = open(src_run + '/' + prov_name, 'rb').read().decode('utf-8')
    pout, pn = relocate_text(ptxt)
    json.loads(pout)
    if PREFLIGHT:
        # replay harness: the provenance a B launch would write (b0 watchdog -PreflightOnly output), adapted to the
        # recorded state: run_id/name of the recorded run, network path = the relocated recorded network copy
        # (same v3c3 bytes), freeze = pin of a stand-in file (the b0 tree is not frozen; only the pin format is read).
        va = json.loads(pout)
        pre = json.loads(open(PREFLIGHT, 'rb').read().decode('utf-8-sig'))
        assert pre['files']['network']['sha256'] == va['files']['network']['sha256'] == '3de889f0257d998bed50611f798ea388bcf69396dbc40e5726b1e88ebdd31c2e'
        assert pre['seed'] == va['seed'] and pre['sim_period_sec'] == va['sim_period_sec']
        pre['run_id'] = va['run_id']
        pre['name'] = va['name']
        pre['files']['network']['path'] = va['files']['network']['path']
        pre['observation']['freeze'] = {'path': FREEZE_STANDIN.replace('/', BS), 'sha256': sha(FREEZE_STANDIN)}
        pout = json.dumps(pre, ensure_ascii=False, indent=2)
        pn = {'synthesized_from_preflight': PREFLIGHT, 'preflight_sha256': sha(PREFLIGHT)}
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
    if os.path.exists(ap):
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
    left = [o for o in re.findall(r'[A-Za-z]:' + re.escape(BS + BS) + r'[^"]{0,80}', out)
            if not (o.startswith(esc(new_run)) or o.startswith(esc(NEW_CODE)))]
    d = root + '/' + D + 'state_' + t6 + '.json'
    open(d, 'wb').write(out.encode('utf-8'))
    json.loads(out)
    man.append((D + 'state_' + t6 + '.json', sha(d), 'relocated %s' % json.dumps(sn)))
    rec = {'label': label, 'T': T, 'source_run': src_run, 'pristine_root': root, 'working_run_dir': new_run,
           'relocation': {orig_run: new_run, OBS_OURS: OBS_NEW, ORIG_FROZEN: NEW_CODE},
           'state_source_sha256': sha(src_run + '/' + D + 'state_' + t6 + '.json'),
           'state_paths_unrelocated_after': left,
           'files': [{'path': a, 'sha256': b, 'how': c} for a, b, c in man]}
    json.dump(rec, open(top + '/INPUT_MANIFEST.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(label, T, 'files', len(man), 'state', json.dumps(sn), 'prov', json.dumps(pn), 'unrelocated', left)


FREEZE_STANDIN = NEW_CODE.replace(BS, '/') + '/FREEZE.json'   # the real FRZ_B0 pin (= the pin the runner preflight wrote)
args = sys.argv[1:]
PREFLIGHT = None
if args and args[0].startswith('--preflight='):
    PREFLIGHT = args.pop(0).split('=', 1)[1]
label = args[0]
for T in [int(x) for x in args[1:]]:
    build(label, T)
