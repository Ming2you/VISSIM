# O1/O2 input builder (vsl_v3c3, 2026-10-27 KST). Same rule as c_port/vsl/work/v3_build_inputs.py (sha 7c0d...see LOG)
# and codex_handoff/work/gate1/g1_build_inputs.py: byte copies of the causal inputs of ONE recorded decision state
# (network .inpx/.sig/.err, previous action json/csv/.applied, vsl/signal readback, obs150 files <= T, lane frames <= T,
# state_T.json, run provenance); only text paths (recorded run dir, recorded frozen code tree) are relocated in
# state/provenance/.applied. Sources are read-only. Writes ONLY under D:/VISSIM-merge/k8_gate_trees/vsl_v3c3/o1o2/pristine.
# Usage: python -B o_build_inputs.py <label> <source> <T>
import hashlib, json, os, re, shutil, sys
BS = chr(92)
ROOT = 'D:/VISSIM-merge/k8_gate_trees/vsl_v3c3/o1o2'
CODE64 = ROOT.replace('/', BS) + BS + 'code64'
CODEB1 = ROOT.replace('/', BS) + BS + 'codeB1'
F355 = 'D:' + BS + 'VISSIM_runtime' + BS + '20261012_adopted355_vsl_three' + BS + 'frozen' + BS + 'sdmpc31_ca181e84_202610121132'
FB1 = 'D:' + BS + 'VISSIM-merge' + BS + 'k8_gate_trees' + BS + 'codexhandoff' + BS + 'b1' + BS + 'frozen' + BS + 'sdmpc31_a49981ff_202610261410'
D64 = ('decisions_sdmpc31_sdmpc8100_s29', 'run_provenance_sdmpc31_sdmpc8100_s29.json')
SOURCES = {
    'a1': dict(src='D:/VISSIM_runs/20261025_codex_a1_s29/sdmpc', dec=D64,
               run='D:' + BS + 'VISSIM_runs' + BS + '20261025_codex_a1_s29' + BS + 'sdmpc',
               frozen='D:' + BS + 'VISSIM_runtime' + BS + '20261025_codex_a1' + BS + 'frozen' + BS + 'sdmpc31_a49981ff_202610251820',
               code=CODE64),
    'joint': dict(src='D:/VISSIM_handoff/20261024/raw/joint/sdmpc', dec=D64,
                  run='E:' + BS + 'VISSIM_runs' + BS + '20261012_adopted355_optimized_s29_8100' + BS + 'sdmpc', frozen=F355, code=CODE64),
    'window': dict(src='D:/VISSIM_handoff/20261024/raw/window/sdmpc', dec=D64,
                   run='E:' + BS + 'VISSIM_runs' + BS + '20261012_adopted355_window_s29_8100' + BS + 'sdmpc', frozen=F355, code=CODE64),
    'off': dict(src='D:/VISSIM_handoff/20261024/raw/off/sdmpc', dec=D64,
                run='E:' + BS + 'VISSIM_runs' + BS + '20261012_adopted355_off_s29_8100' + BS + 'sdmpc', frozen=F355, code=CODE64),
}
for s in (31, 41, 43):
    SOURCES['b%d' % s] = dict(src='D:/VISSIM_runs/20261026_codex_b_v3c3/s%d/sdmpc' % s,
                              dec=('decisions_sdmpc31_sdmpc9000_s%d' % s, 'run_provenance_sdmpc31_sdmpc9000_s%d.json' % s),
                              run='D:' + BS + 'VISSIM_runs' + BS + '20261026_codex_b_v3c3' + BS + 's%d' % s + BS + 'sdmpc',
                              frozen=FB1, code=CODEB1)


def esc(s):
    return s.replace(BS, BS + BS)


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def build(label, source, T):
    S = SOURCES[source]
    SRC, ORIG_RUN, ORIG_FROZEN, NEW_CODE = S['src'], S['run'], S['frozen'], S['code']
    DEC, PROV = S['dec']
    t6 = '%06d' % T
    new_run = ROOT.replace('/', BS) + BS + 'runs' + BS + label + BS + 'sdmpc'
    top = ROOT + '/pristine/' + label
    root = top + '/sdmpc'
    if os.path.exists(top):
        raise SystemExit('pristine exists: ' + top)
    os.makedirs(root + '/network')
    os.makedirs(root + '/' + DEC + '/obs150')
    os.makedirs(root + '/' + DEC + '/lane_observations')
    man = []

    def cp(rel):
        s, d = SRC + '/' + rel, root + '/' + rel
        shutil.copy2(s, d)
        man.append((rel, sha(d), 'copy'))

    def reloc(txt):
        n = (txt.count(esc(ORIG_RUN)), txt.count(esc(ORIG_FROZEN)))
        return txt.replace(esc(ORIG_RUN), esc(new_run)).replace(esc(ORIG_FROZEN), esc(NEW_CODE)), n

    ptxt = open(SRC + '/' + PROV, 'rb').read().decode('utf-8-sig')
    pout, pn = reloc(ptxt)
    json.loads(pout)
    open(root + '/' + PROV, 'wb').write(pout.encode('utf-8'))
    man.append((PROV, sha(root + '/' + PROV), 'relocated run=%d frozen=%d' % pn))
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
    for f in ('vsl_readback.csv', 'signal_readback.csv'):
        if os.path.exists(SRC + '/' + D + f):
            cp(D + f)
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
    txt = open(SRC + '/' + D + 'state_' + t6 + '.json', 'rb').read().decode('utf-8')
    out, sn = reloc(txt)
    left = [o for o in re.findall(r'[A-Za-z]:' + re.escape(BS + BS) + r'[^"]{0,80}', out)
            if not (o.startswith(esc(new_run)) or o.startswith(esc(NEW_CODE)))]
    d = root + '/' + D + 'state_' + t6 + '.json'
    open(d, 'wb').write(out.encode('utf-8'))
    json.loads(out)
    man.append((D + 'state_' + t6 + '.json', sha(d), 'relocated run=%d frozen=%d' % sn))
    rec = {'label': label, 'source': source, 'T': T, 'source_dir': SRC, 'decisions': DEC, 'provenance': PROV,
           'pristine_root': root, 'working_run_dir': new_run, 'code_root': NEW_CODE,
           'relocation': {ORIG_RUN: new_run, ORIG_FROZEN: NEW_CODE},
           'state_source_sha256': sha(SRC + '/' + D + 'state_' + t6 + '.json'),
           'state_paths_unrelocated_after': left,
           'files': [{'path': a, 'sha256': b, 'how': c} for a, b, c in man]}
    json.dump(rec, open(top + '/INPUT_MANIFEST.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(label, source, T, 'files', len(man), 'state reloc run/frozen', sn, 'prov reloc', pn, 'unrelocated', left)


if __name__ == '__main__':
    build(sys.argv[1], sys.argv[2], int(sys.argv[3]))
