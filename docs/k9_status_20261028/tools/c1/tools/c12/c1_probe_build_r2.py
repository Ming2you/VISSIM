"""C1-2 probe patch r2 (K8 amendment C1-2 dfe9809b..., sections 6, 8.1, 9.1) and trees.

    python -B c1_probe_build_r2.py patch final            -> C1D/tools/c12/c1_probe_r2.patch + c1_probe_r2_manifest.json
                                                            (evidence = C1D2/p0/c1g_storage_segments_v3c3.json (S17) and
                                                            C1D2/p0/c1g_storage_segments_null_v3c3.json (S17_0))
    python -B c1_probe_build_r2.py patch dev <ev> <null>  -> TC1/work/c12dev/patch_<pid>_<ns>/ (development only)
    python -B c1_probe_build_r2.py tree <kind> [<manifest>] -> TC1/trees/<kind>_<patch sha8> = git archive c20aff1d + patch

Patch r2 = every change of the first probe patch (c1_probe_build.py edits() and NEW files, patch 5cdc6eb1...) + the
amendment C1-2 edits E23 (RS), E24-E27 (SD), C1P r2 (c12/src_r2/c1_port.py: E28 E29 E30) + the guard evidence files.
Edits: exact anchors (consecutive lines, one match only), applied after the first patch's edits on the same file;
inserted lines take the anchor line's ending.  The manifest records pre / post sha256; every file the guard does not
touch (AFO, LPR, PRB, ADP, the B0 batch 10, the C1 evidence 3) must keep the first manifest's post sha256 (S-C1-22)."""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import c1common as C  # noqa: E402
import c1_probe_build as P1  # noqa: E402

C12 = HERE
C1D2 = C.C1D / 'declared_c1_2'
FINAL_PATCH = C12 / 'c1_probe_r2.patch'
FINAL_MANIFEST = C12 / 'c1_probe_r2_manifest.json'
OLD_MANIFEST = C.TOOLS / 'c1_probe_patch_manifest.json'
OLD_PATCH_SHA = '5cdc6eb1e42492945e7d412d194d6f4b1a125e9b948a46607b1b939fad2c8993'
C1P_REL = 'evaluation/controllers/c1_port.py'
EV_DIR = 'diagnostics/sdmpc_n31_20260924/c1/evidence/'
EV_NAME = 'c1g_storage_segments_v3c3.json'
EV_NULL_NAME = 'c1g_storage_segments_null_v3c3.json'
UNTOUCHED = (P1.AFO, P1.LPR, P1.PRB, P1.ADP) + tuple(k for k in P1.NEW if k != C1P_REL)


def guard_edits():
    """E23-E27 on the post-first-patch text (amendment C1-2 section 6 table)."""
    E = {P1.RS: [], P1.SD: []}
    E[P1.RS].append((['    metadata.update(physical_ramp_metadata)',
                      "    metadata.update(install_wout_exit_law(cfg, tuning))     # K8b-2 P-4' / P-4b (urban.wout_exit_law); {} absent"],
                     ['    metadata.update(physical_ramp_metadata)',
                      "    if 'storage_capacity_guard' in getattr(cfg.network, 'c1_port', {}):",
                      "        c1_meta['storage_capacity_guard'] = c1_port.observe_storage_capacity(cfg, tuning, state_json)",
                      "    metadata.update(install_wout_exit_law(cfg, tuning))     # K8b-2 P-4' / P-4b (urban.wout_exit_law); {} absent"]))
    E[P1.SD].append((['        self.lower, self.upper = np.array(self.bounds).T',
                      '        self.owners = tuple(net.signals)+tuple(net.freeway_links)'],
                     ['        self.lower, self.upper = np.array(self.bounds).T',
                      '        self.owners = tuple(net.signals)+tuple(net.freeway_links)',
                      "        if getattr(net, 'c1_storage_capacity_guard', None):",
                      '            from evaluation.controllers import c1_port',
                      '            c1_port.constrain_storage_capacity(self)']))
    E[P1.SD].append((["        coord = coordinate_type(cfg, reference, callbacks['move_box'], policy)",
                      '        operating_seed = reference',
                      '        if meter_operating_bounds is not None and not coord.valid(coord.encode(reference)):'],
                     ["        coord = coordinate_type(cfg, reference, callbacks['move_box'], policy)",
                      "        guard_rows = any(r.get('status') == 'constrained' for b in getattr(coord, 'blocks', [coord])",
                      "                         for r in getattr(b, 'c1_storage_capacity_receipt', []))",
                      '        operating_seed = reference',
                      '        if guard_rows:',
                      '            from evaluation.controllers import c1_port',
                      '            operating_seed = c1_port.storage_capacity_seed(coord, reference, policy)',
                      '        elif meter_operating_bounds is not None and not coord.valid(coord.encode(reference)):']))
    E[P1.SD].append((['            if meter_operating_bounds is not None and not bool(coord.valid(coord.encode(action))):'],
                     ['            if (meter_operating_bounds is not None or guard_rows) and not bool(coord.valid(coord.encode(action))):']))
    E[P1.SD].append((["        metadata = {'algorithm': SCHEMA, 'converged': False, 'feasible': True,",
                      "            **({'meter_operating_bounds': meter_operating_bounds} if meter_operating_bounds is not None else {}),"],
                     ["        guard_present = getattr(cfg.network, 'c1_storage_capacity_guard', None) is not None",
                      '        if guard_present:',
                      '            from evaluation.controllers import c1_port',
                      "        metadata = {'algorithm': SCHEMA, 'converged': False, 'feasible': True,",
                      "            **({'meter_operating_bounds': meter_operating_bounds} if meter_operating_bounds is not None else {}),",
                      "            **({'c1_storage_capacity_guard': c1_port.storage_capacity_meta(coord, bool(guard_rows) and operating_seed is not reference)}",
                      '               if guard_present else {}),']))
    return E


def build_patch(dest_dir, ev_path, ev_null_path, repo_dir):
    old = json.loads(OLD_MANIFEST.read_text(encoding='utf-8'))
    if old['patch_sha256'] != OLD_PATCH_SHA:
        raise SystemExit('first patch manifest differs')
    dev = Path(repo_dir)
    patch, manifest = dest_dir / 'c1_probe_r2.patch', dest_dir / 'c1_probe_r2_manifest.json'
    if dev.exists() or patch.exists() or manifest.exists():
        raise SystemExit('patch repo / patch / manifest already exist (never overwritten)')
    base = P1.archive_members(P1.CHANGED)
    dev.mkdir(parents=True)
    for rel, b in base.items():
        p = dev / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b)
    P1.git('init', '-q', cwd=dev)
    (dev / '.git' / 'info' / 'attributes').write_text('* -text\n', encoding='utf-8')
    P1.git('add', '--', *P1.CHANGED, cwd=dev)
    P1.git('-c', 'user.name=c1probe', '-c', 'user.email=c1probe@localhost', 'commit', '-q', '-m', 'base c20aff1d', cwd=dev)
    first, second = P1.edits(), guard_edits()
    rec = {'schema': 'c1-probe-patch/v2', 'rev': C.REV, 'first_patch_sha256': OLD_PATCH_SHA, 'pre': {}, 'post': {},
           'edits': {}}
    for rel in P1.CHANGED:
        raw = base[rel]
        rec['pre'][rel] = C.sha256_bytes(raw)
        for anchor, new in first[rel]:
            raw = P1.edit(raw, anchor, new)
        for anchor, new in second.get(rel, []):
            raw = P1.edit(raw, anchor, new)
        (dev / rel).write_bytes(raw)
        rec['post'][rel] = C.sha256_bytes(raw)
        rec['edits'][rel] = [len(first[rel]), len(second.get(rel, []))]
        compile(raw.decode('utf-8'), rel, 'exec')
    new = dict(P1.NEW)
    new[C1P_REL] = C12 / 'src_r2' / 'c1_port.py'
    new[EV_DIR + EV_NAME] = Path(ev_path)
    new[EV_DIR + EV_NULL_NAME] = Path(ev_null_path)
    for rel, src in new.items():
        b = Path(src).read_bytes()
        if rel in P1.NEW_SHA and C.sha256_bytes(b) != P1.NEW_SHA[rel]:
            raise SystemExit('new file differs from its declared sha: ' + rel)
        p = dev / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b)
        rec['post'][rel] = C.sha256_bytes(b)
        if rel.endswith('.py'):
            compile(b.decode('utf-8'), rel, 'exec')
    untouched_bad = {rel: [old['post'].get(rel), rec['post'].get(rel)] for rel in UNTOUCHED
                     if old['post'].get(rel) != rec['post'].get(rel)}
    rec['untouched_files'] = list(UNTOUCHED)
    rec['untouched_equal_first_post'] = not untouched_bad
    rec['untouched_differences'] = untouched_bad
    P1.git('add', '--', *P1.CHANGED, *new, cwd=dev)
    diff = P1.git('diff', '--cached', '--binary', '--full-index', cwd=dev)
    with open(patch, 'xb') as f:
        f.write(diff)
    rec['patch_sha256'] = C.sha256_file(patch)
    rec['patch_bytes'] = patch.stat().st_size
    rec['new_files'] = sorted(new)
    rec['changed_files'] = sorted(P1.CHANGED)
    rec['evidence_sha256'] = {EV_NAME: C.sha256_file(ev_path), EV_NULL_NAME: C.sha256_file(ev_null_path)}
    with open(manifest, 'x', encoding='utf-8') as f:
        f.write(json.dumps(rec, indent=1, sort_keys=True))
    print('C1_PATCH_R2 sha256=%s bytes=%d untouched_equal=%s manifest=%s' % (
        rec['patch_sha256'], rec['patch_bytes'], rec['untouched_equal_first_post'], C.sha256_file(manifest)))
    if untouched_bad:
        raise SystemExit('S-C1-22: a file the guard does not touch differs from the first patch post sha256')
    return rec


def cmd_tree(kind, manifest_path):
    man = json.loads(Path(manifest_path).read_text(encoding='utf-8'))
    patch = Path(manifest_path).with_name('c1_probe_r2.patch')
    psha = C.sha256_file(patch)
    if psha != man['patch_sha256']:
        raise SystemExit('patch bytes differ from its manifest')
    if not kind.replace('_', '').isalnum() or kind != kind.lower():
        raise SystemExit('tree kind must be lowercase [a-z0-9_]')
    name = '%s_%s' % (kind, psha[:8])
    dest = C.TC1 / 'trees' / name
    if dest.exists():
        raise SystemExit('tree exists: %s' % dest)
    C.require_space()
    import shutil
    import tarfile
    members = set()
    proc = subprocess.Popen(['git', '-C', str(C.GWT8), 'archive', '--format=tar', C.REV], stdout=subprocess.PIPE)
    with tarfile.open(fileobj=proc.stdout, mode='r|') as tf:
        for m in tf:
            if not m.isfile():
                continue
            p = C.lp(dest / m.name)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, 'wb') as f:
                shutil.copyfileobj(tf.extractfile(m), f)
            members.add(m.name)
    if proc.wait() != 0:
        raise SystemExit('git archive failed')
    P1.git('apply', '--binary', '--whitespace=nowarn', str(patch), cwd=dest)
    bad = {}
    for rel, digest in man['post'].items():
        got = C.sha256_file(dest / rel)
        if got != digest:
            bad[rel] = got
    count = sum(len(fs) for _, _, fs in os.walk(C.lp(dest)))
    added = [r for r in man['new_files'] if r not in members]
    rec = {'tree': name, 'rev': C.REV, 'patch_sha256': psha, 'archive_files': len(members), 'files_after': count,
           'expected_files_after': len(members) + len(added), 'post_check_bad': bad,
           'ok': not bad and count == len(members) + len(added)}
    C.write_json(C.TC1 / 'trees' / (name + '.build.json'), rec)
    print('C1_TREE_R2 %s ok=%s files=%d bad=%d' % (name, rec['ok'], count, len(bad)))
    if not rec['ok']:
        raise SystemExit(3)


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[:2] == ['patch', 'final'] and len(a) == 2:
        build_patch(C12, C1D2 / 'p0' / EV_NAME, C1D2 / 'p0' / EV_NULL_NAME, C.TC1 / 'work' / 'patchdev_r2')
    elif a[:2] == ['patch', 'dev'] and len(a) == 4:
        d = C.TC1 / 'work' / 'c12dev' / ('patch_%d_%d' % (os.getpid(), time.time_ns()))
        d.mkdir(parents=True)
        build_patch(d, a[2], a[3], d / 'repo')
        print('DEV_DIR %s' % d)
    elif a[:1] == ['tree'] and len(a) in (2, 3):
        cmd_tree(a[1], a[2] if len(a) == 3 else FINAL_MANIFEST)
    else:
        raise SystemExit(__doc__)
