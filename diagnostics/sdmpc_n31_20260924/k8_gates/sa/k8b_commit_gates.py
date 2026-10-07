"""K8b per-commit gates G1-G4 (K8b-0 tool; K8_PREDECLARATION_AMENDMENT_16 r2 section 4.1 as corrected by
AMENDMENT_17, user decision D-K8b-4 variant A).  Diagnostics only: drives the SA harness of THIS tree (captures,
rollout jobs, full decisions, compares) against a separate code root, one process at a time, BELOW_NORMAL,
PYTHONHASHSEED=0, python -B.  VISSIM / COM is never started.

    python -B k8b_commit_gates.py extract --rev REV --dest DIR [--like DIR]
    python -B k8b_commit_gates.py prep    --out OUT --root R
    python -B k8b_commit_gates.py anchor  --root R                         (OUT = <gates>/anchor_k84v3, tree k84v3)
    python -B k8b_commit_gates.py g1      --commit L --root R [--unit-only]
    python -B k8b_commit_gates.py g2      --commit L --root R
    python -B k8b_commit_gates.py g3      --commit L --root R --part p1|p4|p2
    python -B k8b_commit_gates.py g4      --commit L --root R --part p1|all
    python -B k8b_commit_gates.py unit    --commit L --root R --name NAME FILE [FILE ...]
    python -B k8b_commit_gates.py chain   PLAN.json                        (steps = lists of the argv above)
Output root of a commit: D:/VISSIM-merge/k8b_commit_gates/<commit>/ (K8G_OUT; tree label = the commit label), result
files gate_<g>[_<part>].json there; the anchor root D:/VISSIM-merge/k8b_commit_gates/anchor_k84v3/.

Gates (section 4.1, fixed before any gate output):
  G1  key absent = the ec063ff runtime: BASE (no SA, no K8b key) DP 17 template numeric fields, TL3 s31 9 x {OBS, A1}
      H3 objective repr + numeric fields, full 2700 BASE objective / held repr (CSV sha reported) -- sa_compare.py g1
      against the anchor tree k84v3 (git archive ec063ffa, computed once with this harness and copied in byte-equal),
      T11 = sa_compare.py g9 (DP 17 BASE vs SAF with keys off), unit T2 / T10 / T10b (pytest -v log of
      tests/test_stopline_approach.py), judged by sa_gates.py --only G-EB-1.
  G2  K8b keys off SAF (the k86h arm file) = k86h: captures + H3 OBS jobs at the probe states s31 1650 and s43 3450,
      SAF (A1) and BASE (A0), equal the probe head outputs D:/VISSIM-merge/k8b_probe/out/sa/{cap,jobs}/k8bhead in
      every common numeric and string leaf (excluded: timing keys of the p3_compare rule, paths, tree / label names,
      template_sha256, the probe wrapper's k8b fields and the K8b-0 fields k8b0 / signal_queue -- one-sided leaves are
      listed); plus TL3 s31 2700 SAF OBS H3 (keys off, a judging state, allowed) = k8_gates_out_v2 k86h.
  G3  that commit's key alone on SAF at the probe states s31 1650 / s43 3450 (captures + H1 and H3 OBS jobs): runs ok
      (no stocks / SA / K8b invariant exception), capture metadata = evidence values, SC109 movements + the 8 meters
      byte-equal key on / off (G-EB-9 form); p1: SC1002 W first-step _movement_capacity_flow = the section 2.1 formula
      with the recorded beta (+-1e-9), every other movement capacity byte-equal; p4 / p2: the store shrink 0 on the
      probe rollouts and the ad_full job at s31 3300 (state_error <= 1e-8, complete match, AMENDMENT_10 S3 excluded 0,
      SA-created 0); unit tests of the part (separate log).
  G4  probe reproduction: p1 = the captures of the probe k8b_C1 (template numeric fields; probe metadata
      net.k8b_probe_capture.P1 <-> capture metadata k8b_p1, fixed map); all = SAF + P-1 + P-4 (variant A) + P-2 at
      s31 1650, s31 3300, s43 1500, s47 3450 (H3 OBS) and L2 s47 4800 H27 OBS = the mini-probe v2 A7p summaries
      (D:/VISSIM-merge/k8b_miniprobe/out/sa/jobs/k8b) in every common numeric leaf (timing excluded); a difference is
      accepted only when relative <= 1e-9 (listed with its cause), else STOP.
K8b-keyed captures / jobs run only at probe-sample states (sa_common.k8b_guard is called before each)."""
import hashlib
import json
import math
import os
import pickle
import shutil
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sa_common as sc  # noqa: E402

c = sc.c
GATES = Path(r'D:/VISSIM-merge/k8b_commit_gates')
ANCHOR_TREE = 'k84v3'
ANCHOR_OUT = GATES / 'anchor_k84v3'
PROBE = Path(r'D:/VISSIM-merge/k8b_probe')
MINI = Path(r'D:/VISSIM-merge/k8b_miniprobe')
V2 = Path(r'D:/VISSIM-merge/k8_gates_out_v2')
N31 = Path('diagnostics') / 'sdmpc_n31_20260924'
S31_PROBE = (1650, 3300)
G2_STATES = ((31, 1650), (43, 3450))
G4_H3 = ((31, 1650), (31, 3300), (43, 1500), (47, 3450))
G4_LONG = (47, 4800, 27)
ADFULL_STATE = (31, 3300)
TOL_REL = 1e-9
SKIP = ('wall', 'sec', 'time', 'rss', 'elapsed')
EXCLUDE = ('template_sha256', '/k8b0', 'signal_queue', '/k8b/', '/tree', '/label', '/template', '/forecast_long',
           '/coord', '/job_path', '/eo_dir', '/replay', '/robs', '/root', 'path', 'python_hash_seed', 'capture_spec')
LOG = None


def log(msg):
    line = time.strftime('%Y-%m-%d %H:%M:%S ') + msg
    print(line, flush=True)
    if LOG is not None:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG, 'a', encoding='utf-8') as h:
            h.write(line + '\n')


def sha(p):
    return sc.sha256_file(p)


def setup(root, out):
    global LOG
    c.configure(root=str(root), out=str(out), robs=c.DEFAULT_ROBS, nc3=c.NC3)
    LOG = Path(out) / 'commit_gates.log'
    c.lower_priority()


def robs_of(seed):
    return c.DEFAULT_ROBS if int(seed) == 31 else c.DEFAULT_ROBS.parent / sc.ROBS_NAME.format(seed=int(seed))


def free_space():
    low = {d: shutil.disk_usage(d + ':/').free / 1e9 for d in ('C', 'D')}
    if any(v < 8.0 for v in low.values()):
        raise SystemExit(f'LOW_SPACE {low} (< 8 GB): stop and report')
    return low


def write(path, obj):
    sc.write_json(path, obj)
    log(f'WROTE {path}')


# ------------------------------------------------------------------------------------------------ trees
def extract(rev, dest, like=None):
    """git archive <rev> of the K8 worktree into dest (checkout conversion; long paths), then optional byte compare
    with `like` (file list and bytes)."""
    repo = Path(__file__).resolve().parents[4]
    dest = Path(dest).resolve()
    if dest.exists():
        raise SystemExit(f'{dest} exists')
    import tarfile
    p = subprocess.Popen(['git', '-C', str(repo), 'archive', '--format=tar', rev], stdout=subprocess.PIPE)
    n = 0
    with tarfile.open(fileobj=p.stdout, mode='r|') as tf:
        for m in tf:
            target = '\\\\?\\' + os.path.join(str(dest), m.name.replace('/', os.sep))
            if m.isdir():
                os.makedirs(target, exist_ok=True)
                continue
            if m.issym():
                continue
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, 'wb') as out:
                out.write(tf.extractfile(m).read())
            n += 1
    if p.wait() != 0:
        raise SystemExit('git archive failed')
    rec = {'rev': rev, 'dest': str(dest), 'files': n,
           'rev_full': subprocess.run(['git', '-C', str(repo), 'rev-parse', rev], capture_output=True,
                                      text=True).stdout.strip()}
    if like:
        rec['like'] = compare_trees(dest, Path(like))
    print(json.dumps(rec, indent=1))
    (dest.parent / f'{dest.name}.extract.json').write_text(json.dumps(rec, indent=1), encoding='utf-8')
    return rec


def _files(root):
    out = {}
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in ('__pycache__', '__tangentcache__', '.pytest_cache')]
        for f in files:
            p = Path(base) / f
            out[p.relative_to(root).as_posix()] = p
    return out


def compare_trees(a, b):
    fa, fb = _files(a), _files(b)
    only_a, only_b = sorted(set(fa) - set(fb)), sorted(set(fb) - set(fa))
    differ = [k for k in sorted(set(fa) & set(fb)) if fa[k].read_bytes() != fb[k].read_bytes()]
    return {'files_a': len(fa), 'files_b': len(fb), 'only_a': only_a[:50], 'only_b': only_b[:50],
            'n_only_a': len(only_a), 'n_only_b': len(only_b), 'differ': differ[:50], 'n_differ': len(differ),
            'identical': not only_a and not only_b and not differ}


# ------------------------------------------------------------------------------------------------ prep
def prep(root, out):
    """Replay states (copies, make_replay_state_v2.prepare of the code root) for every state the gates open, and
    the keys-off arms.json (sa_arms.py --source repo of the code root; ec063ffa has no SA arm: BASE only)."""
    setup(root, out)
    free_space()
    if not (Path(out) / 'sa' / 'tuning' / 'arms.json').is_file():
        if (Path(root) / N31 / 'config_n31_v2_stopline_observed_full.json').is_file():
            subprocess.run([sys.executable, '-B', str(HERE / 'sa_arms.py'), '--root', str(root), '--out', str(out),
                            '--source', 'repo'], check=True, creationflags=c.BELOW_NORMAL,
                           env=dict(os.environ, PYTHONHASHSEED='0'))
        else:
            base = Path(root) / N31 / 'config_n31_v2.json'
            sc.write_json(Path(out) / 'sa' / 'tuning' / 'arms.json',
                          {'schema': 'k8-sa-arms/v1', 'root': str(root), 'k8b': False,
                           'arms': {'BASE': {'path': str(base), 'storage': None, 'source': 'root',
                                             'sha256': sha(base), 'k8b_keys': []}}})
    sys.path.insert(0, str(c.R / 'diagnostics/sdmpc_n31_20260924/tools'))
    import n31_common
    import make_replay_state_v2 as m

    def copy_only(source, target):
        source, target = Path(source), Path(target)
        n31_common.require(source.is_file(), f'Missing file to copy: {source}')
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(n31_common.long_path(source), n31_common.long_path(target))
        return 'copy'
    n31_common.link_or_copy = copy_only
    m.link_or_copy = copy_only
    states = sorted({(31, T) for T in set(sc.DP_T) | set(sc.GRID9) | set(S31_PROBE)}
                    | set(G2_STATES) | set(G4_H3) | {G4_LONG[:2]})
    for seed, T in states:
        c.configure(root=c.R, out=c.OUT, robs=robs_of(seed), nc3=c.NC3)
        dest = sc.replay_dir(T, seed)
        if dest.exists():
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        m.prepare(str(c.DEC), int(T), str(dest))
        log(f'PREP s{seed} {T} -> {dest}')
    c.configure(root=c.R, out=c.OUT, robs=c.DEFAULT_ROBS, nc3=c.NC3)
    return states


# ------------------------------------------------------------------------------------------------ harness calls
def tuning_rec(path):
    return {'path': str(path), 'sha256': sha(path)}


def arm_tuning(root, arm):
    if arm == 'BASE':
        return tuning_rec(Path(root) / N31 / 'config_n31_v2.json')
    return tuning_rec(Path(root) / N31 / f'config_n31_v2_stopline_{sc.STORAGE_OF_ARM[arm]}.json')


def capture(tree, kind, arm, seed, T, tuning):
    import sa_capture
    free_space()
    c.configure(root=c.R, out=c.OUT, robs=robs_of(seed), nc3=c.NC3)
    harness = {'tl3': 'TL3', 'dp': 'DP'}[kind]
    args = SimpleNamespace(kind=kind, arm=arm, tree=tree, dry_run=False, robs_seed=seed, fh_disabled=False,
                           gates_stage=None, declaration_sha=None, data=None)
    row = dict(harness=harness, T=int(T), seed=int(seed), frame_T=int(T))
    out = sc.cap_dir(tree, harness, T, arm, seed=seed)
    if not (out / 'capture.json').is_file():
        t0 = time.time()
        sa_capture.run_capture(args, row, tuning)
        log(f'CAP {tree} {harness} s{seed} {T} {arm} ok={(out / "capture.json").is_file()} '
            f'wall={round(time.time() - t0, 1)}')
    c.configure(root=c.R, out=c.OUT, robs=c.DEFAULT_ROBS, nc3=c.NC3)
    return out


def job(tree, harness, T, arm, entry, H, seed=31, variant='REF', mode='scalar', action=None):
    import sa_jobs
    free_space()
    c.configure(root=c.R, out=c.OUT, robs=robs_of(seed), nc3=c.NC3)
    args = SimpleNamespace(tree=tree, hooks=False, eo_root=str(sa_jobs.DEFAULT_EO), labels_only=False,
                           dry_run=False, plan_only=False, gates_stage=None, declaration_sha=None, chain='site',
                           s3_table=None)
    j = sa_jobs.base_job(args, harness, int(T), arm, entry, int(H), seed=(int(seed) if harness == 'TL3' else None),
                         variant=variant, mode=mode)
    if action is not None:
        j['action'] = action
    out = sc.job_dir(tree, j['label'])
    if not (out / 'summary.json').is_file():
        t0 = time.time()
        sa_jobs.run_job(args, j)
        s = sc.read_json(out / 'summary.json', {}) or {}
        log(f'JOB {tree} {j["label"]} ok={s.get("ok")} wall={round(time.time() - t0, 1)} '
            f'err={(s.get("error") or "")[-200:]!r}')
    c.configure(root=c.R, out=c.OUT, robs=c.DEFAULT_ROBS, nc3=c.NC3)
    return out


def full(tree, arm, T, tuning):
    import sa_capture
    free_space()
    args = SimpleNamespace(kind='full', arm=arm, tree=tree, dry_run=False, chain='site', s3_table=None, tag='',
                           gates_stage=None, declaration_sha=None)
    out = sc.full_dir(tree, T, arm, '')
    if not (out / 'run.json').is_file():
        t0 = time.time()
        sa_capture.run_full(args, dict(harness='FULL', T=int(T), seed=None, frame_T=int(T)), tuning)
        log(f'FULL {tree} {T} {arm} wall={round(time.time() - t0, 1)}')
    return out


def unit(root, out, name, files):
    """pytest -v of `files` under the code root (BELOW_NORMAL, PYTHONHASHSEED=0) -> <out>/sa/unit_<name>.log."""
    dest = Path(out) / 'sa' / f'unit_{name}.log'
    if dest.is_file():
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    code = ('import ctypes, os, sys\n'
            'k = ctypes.windll.kernel32\n'
            'k.GetCurrentProcess.restype = ctypes.c_void_p\n'
            'k.SetPriorityClass.argtypes = (ctypes.c_void_p, ctypes.c_uint32)\n'
            'k.SetPriorityClass(k.GetCurrentProcess(), 0x4000)\n'
            'assert os.environ.get("PYTHONHASHSEED") == "0"\n'
            'import pytest\n'
            'sys.exit(pytest.main(["-p", "no:cacheprovider", "-v", *sys.argv[1:]]))\n')
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith(('RW_', 'K8_'))}
    env.update(PYTHONHASHSEED='0', NUMBA_NUM_THREADS='1', PYTHONUTF8='1', K8G_OUT=str(out), K8G_ROOT=str(root))
    t0 = time.time()
    with open(dest, 'w', encoding='utf-8') as h:
        h.write(f'ROOT {root}\nFILES {files}\n')
        h.flush()
        rc = subprocess.run([sys.executable, '-B', '-c', code, *files], cwd=str(root), env=env, stdout=h,
                            stderr=subprocess.STDOUT, creationflags=c.BELOW_NORMAL).returncode
    log(f'UNIT {name} rc={rc} wall={round(time.time() - t0, 1)} -> {dest}')
    return dest


def unit_summary(path):
    text = Path(path).read_text(encoding='utf-8', errors='replace')
    tail = [ln for ln in text.splitlines() if ln.startswith('=') and (' passed' in ln or ' failed' in ln
                                                                       or ' error' in ln)]
    failed = [ln for ln in text.splitlines() if ln.startswith(('FAILED', 'ERROR', 'SUBFAILED'))]
    return {'log': str(path), 'session': tail[-1] if tail else None, 'failed_lines': failed[:30],
            'ok': bool(tail) and not failed and ' failed' not in tail[-1] and ' error' not in tail[-1]}


def python_in_root(root, code, *args):
    """Run `code` in a fresh python under the code root (sys.path as the worker), return its JSON stdout."""
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith(('RW_', 'K8_'))}
    env.update(PYTHONHASHSEED='0', NUMBA_NUM_THREADS='1', PYTHONUTF8='1')
    pre = ('import sys, json\n'
           f'sys.path[:0] = [{str(root)!r}, {str(Path(root) / "vendor/NumSim-mine")!r}, '
           f'{str(Path(root) / "evaluation/controllers")!r}]\n')
    out = subprocess.run([sys.executable, '-B', '-c', pre + code, *args], cwd=str(root), env=env,
                         capture_output=True, text=True, creationflags=c.BELOW_NORMAL)
    if out.returncode != 0:
        raise RuntimeError(out.stderr[-3000:])
    return json.loads(out.stdout.strip().splitlines()[-1])


# ------------------------------------------------------------------------------------------------ comparisons
def leaves(doc):
    import sa_compare as cmp
    strings = {}
    nums = cmp.flatten(doc, strings=strings)
    return nums, strings


def excluded(key):
    k = key.lower()
    return any(s in k for s in SKIP) or any(e.lower() in k for e in EXCLUDE)


def compare_docs(a, b, tol_rel=0.0):
    """Common numeric leaves equal (relative tol_rel, NaN = NaN) and common string leaves equal, after EXCLUDE /
    SKIP; one-sided leaves listed (never failing)."""
    na, sa_ = leaves(a)
    nb, sb_ = leaves(b)
    diffs, near = [], []
    for k in sorted(set(na) & set(nb)):
        if excluded(k):
            continue
        x, y = na[k], nb[k]
        if x == y or (math.isnan(x) and math.isnan(y)):
            continue
        rel = abs(x - y) / max(abs(x), abs(y), 1e-300)
        (near if rel <= tol_rel else diffs).append([k, x, y, rel])
    sdiff = [[k, sa_[k][:120], sb_[k][:120]] for k in sorted(set(sa_) & set(sb_))
             if not excluded(k) and sa_[k] != sb_[k]]
    one_a = sorted(k for k in (set(na) | set(sa_)) - (set(nb) | set(sb_)) if not excluded(k))
    one_b = sorted(k for k in (set(nb) | set(sb_)) - (set(na) | set(sa_)) if not excluded(k))
    return {'numeric_common': len(set(na) & set(nb)), 'string_common': len(set(sa_) & set(sb_)),
            'numeric_differ': len(diffs), 'numeric_near': len(near), 'string_differ': len(sdiff),
            'examples': diffs[:20], 'near_examples': near[:20], 'string_examples': sdiff[:10],
            'one_sided_a': len(one_a), 'one_sided_b': len(one_b), 'one_sided_a_examples': one_a[:15],
            'one_sided_b_examples': one_b[:15], 'equal': not diffs and not sdiff}


def load_template(root, path):
    for p in (str(root), str(Path(root) / 'vendor/NumSim-mine'), str(Path(root) / 'evaluation/controllers')):
        if p not in sys.path:
            sys.path.insert(0, p)
    return pickle.loads(Path(path).read_bytes())


def g9_rows(root, tpl_a, tpl_b, cap_a, cap_b):
    """G-EB-9 form on two templates of the same state: the 8 meters' service_by_green, the capture's normalisation
    metadata and the SC109 movements (spec + capacity) canonical JSON equal."""
    out = {}
    rows = {}
    for side, tp, cp in (('a', tpl_a, cap_a), ('b', tpl_b, cap_b)):
        t = load_template(root, tp)
        net = t['owned'][0].cfg.network
        cap = sc.read_json(cp, {}) or {}
        rows[side] = {'meters': json.dumps({r: row.get('service_by_green_veh_h') for r, row in
                                            net.physical_ramp_branches['ramps'].items()}, sort_keys=True, default=repr),
                      'normalisation': json.dumps((cap.get('metadata') or {}).get(
                          'lane_ramp_head_service_normalisation'), sort_keys=True, default=repr),
                      'sc109': json.dumps({m: {'spec': spec, 'capacity': net.movement_capacity_by_movement_veh_h.get(m)}
                                           for m, spec in net.urban_movements.items() if spec.get('signal') == 'SC109'},
                                          sort_keys=True, default=repr),
                      'n_meters': len(net.physical_ramp_branches['ramps']),
                      'n_sc109': sum(1 for s in net.urban_movements.values() if s.get('signal') == 'SC109')}
    for key in ('meters', 'normalisation', 'sc109'):
        out[key] = rows['a'][key] == rows['b'][key]
    out.update(n_meters=rows['a']['n_meters'], n_sc109=rows['a']['n_sc109'])
    out['equal'] = all(out[k] for k in ('meters', 'normalisation', 'sc109')) and out['n_meters'] == 8 \
        and out['n_sc109'] == 6
    return out


# ------------------------------------------------------------------------------------------------ G1
def g1_runs(root, out, tree, with_saf_dp=True):
    setup(root, out)
    base = arm_tuning(root, 'BASE')
    for T in sc.DP_T:
        capture(tree, 'dp', 'BASE', 31, T, base)
    if with_saf_dp:
        saf = arm_tuning(root, 'SAF')
        for T in sc.DP_T:
            capture(tree, 'dp', 'SAF', 31, T, saf)
    for T in sc.GRID9:
        capture(tree, 'tl3', 'BASE', 31, T, base)
    for T in sc.GRID9:
        for entry in sc.ENTRIES:
            job(tree, 'TL3', T, 'BASE', entry, 3)
    full(tree, 'BASE', 2700, base)


def copy_anchor(out):
    """Byte copies of the anchor's G1 inputs into this output root (tree k84v3), sha checked."""
    rows = []
    for rel in [Path('sa/cap') / ANCHOR_TREE / 'DP', Path('sa/cap') / ANCHOR_TREE / 'TL3',
                Path('sa/full') / ANCHOR_TREE / '002700_BASE']:
        src, dst = ANCHOR_OUT / rel, Path(out) / rel
        for p in sorted(src.rglob('*')):
            if p.is_dir() or p.name.endswith('.json') and p.name.startswith('action_002700.joint'):
                continue
            q = dst / p.relative_to(src)
            if q.is_file() and sha(q) == sha(p):
                continue
            q.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, q)
            if sha(q) != sha(p):
                raise SystemExit(f'anchor copy differs: {q}')
            rows.append(str(q))
    for T in sc.GRID9:
        for entry in sc.ENTRIES:
            label = sc.job_label('TL3', T, 'BASE', entry, 3)
            src, dst = ANCHOR_OUT / 'sa/jobs' / ANCHOR_TREE / label, Path(out) / 'sa/jobs' / ANCHOR_TREE / label
            for name in ('summary.json', 'job.pickle', 'vissim_counts.json'):
                if (src / name).is_file() and not (dst / name).is_file():
                    dst.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src / name, dst / name)
                    rows.append(str(dst / name))
    log(f'ANCHOR_COPY {len(rows)} files')


def g1(commit, root, unit_only=False):
    out = GATES / commit
    if not unit_only:
        g1_runs(root, out, commit)
    setup(root, out)
    ulog = unit(root, out, f'{commit}_T2_T10', [str(N31 / 'tests' / 'test_stopline_approach.py')])
    copy_anchor(out)
    harness_env = dict(os.environ, K8G_OUT=str(out), K8G_ROOT=str(root), PYTHONHASHSEED='0')
    for args in (['g1', '--tree', commit, '--base-tree', ANCHOR_TREE], ['g9', '--tree', commit]):
        subprocess.run([sys.executable, '-B', str(HERE / 'sa_compare.py'), '--root', str(root), '--out', str(out),
                        *args], env=harness_env, check=True, creationflags=c.BELOW_NORMAL)
    subprocess.run([sys.executable, '-B', str(HERE / 'sa_gates.py'), '--root', str(root), '--out', str(out),
                    '--tree', commit, '--base-tree', ANCHOR_TREE, '--unit-log', str(ulog), '--only', 'G-EB-1'],
                   env=harness_env, check=True, creationflags=c.BELOW_NORMAL)
    gates = sc.read_json(out / 'sa' / 'gates' / f'gates_{commit}.json')
    g = gates['gates']['G-EB-1']
    res = {'gate': 'G1', 'commit': commit, 'root': str(root), 'verdict': g['verdict'],
           'items': {k: {kk: v[kk] for kk in ('pass_', 'threshold')} for k, v in g['items'].items()},
           'unit_log': unit_summary(ulog), 'gates_json': str(out / 'sa' / 'gates' / f'gates_{commit}.json')}
    write(out / 'gate_G1.json', res)
    return res


def anchor(root):
    out = ANCHOR_OUT
    g1_runs(root, out, ANCHOR_TREE, with_saf_dp=False)
    res = {'anchor': ANCHOR_TREE, 'root': str(root), 'dp': sum(1 for T in sc.DP_T if (sc.cap_dir(
        ANCHOR_TREE, 'DP', T, 'BASE') / 'template.pickle').is_file()),
           'tl3_caps': sum(1 for T in sc.GRID9 if (sc.cap_dir(ANCHOR_TREE, 'TL3', T, 'BASE') / 'template.pickle')
                           .is_file()),
           'tl3_jobs_ok': sum(1 for T in sc.GRID9 for e in sc.ENTRIES
                              if (sc.read_json(sc.job_dir(ANCHOR_TREE, sc.job_label('TL3', T, 'BASE', e, 3))
                                               / 'summary.json', {}) or {}).get('ok')),
           'full2700': sc.read_json(sc.full_dir(ANCHOR_TREE, 2700, 'BASE', '') / 'run.json')}
    write(out / 'anchor.json', res)
    return res


# ------------------------------------------------------------------------------------------------ G2
def probe_cap(head_tree, seed, T, arm):
    return sc.cap_dir(head_tree, 'TL3', T, arm, seed=seed)


def g2(commit, root):
    out = GATES / commit
    setup(root, out)
    rows = {}
    ok = True
    for seed, T in G2_STATES:
        for arm, armid in (('SAF', 'A1'), ('BASE', 'A0')):
            mine_cap = capture(commit, 'tl3', arm, seed, T, arm_tuning(root, arm))
            mine_job = job(commit, 'TL3', T, arm, 'OBS', 3, seed=seed)
            # the probe head outputs (28c6ab55 = f7407ca5 runtime)
            pc = PROBE / 'out' / 'sa' / 'cap' / 'k8bhead' / 'TL3' / (f'{T:06d}' + ('' if seed == 31 else f'_s{seed}')) / arm
            pj = PROBE / 'out' / 'sa' / 'jobs' / 'k8bhead' / f'PROBE_{T}_s{seed}_{armid}_OBS_H3'
            r = {}
            r['capture_json'] = compare_docs(sc.read_json(mine_cap / 'capture.json'), sc.read_json(pc / 'capture.json'))
            r['template'] = compare_docs(load_template(root, mine_cap / 'template.pickle'),
                                         load_template(root, pc / 'template.pickle'))
            r['template']['strings_not_judged'] = True          # template strings hold paths of the two roots
            r['template']['equal'] = r['template']['numeric_differ'] == 0
            r['summary'] = compare_docs(sc.read_json(mine_job / 'summary.json'), sc.read_json(pj / 'summary.json'))
            r['ok'] = all(r[k]['equal'] for k in ('capture_json', 'template', 'summary')) and bool(
                (sc.read_json(mine_job / 'summary.json') or {}).get('ok'))
            ok &= r['ok']
            rows[f's{seed}_{T}_{arm}'] = r
    # TL3 s31 2700 SAF OBS H3 (keys off) = k86h
    capture(commit, 'tl3', 'SAF', 31, 2700, arm_tuning(root, 'SAF'))
    mj = job(commit, 'TL3', 2700, 'SAF', 'OBS', 3)
    r = compare_docs(sc.read_json(mj / 'summary.json'),
                     sc.read_json(V2 / 'sa' / 'jobs' / 'k86h' / 'TL3_2700_SAF_OBS_H3' / 'summary.json'))
    r['ok'] = r['equal'] and bool((sc.read_json(mj / 'summary.json') or {}).get('ok'))
    ok &= r['ok']
    rows['TL3_2700_SAF_OBS_H3_vs_k86h'] = r
    res = {'gate': 'G2', 'commit': commit, 'root': str(root), 'verdict': 'PASS' if ok else 'FAIL', 'rows': rows,
           'rule': 'common numeric and string leaves equal after the declared exclusions; one-sided leaves listed'}
    write(out / 'gate_G2.json', res)
    return res


# ------------------------------------------------------------------------------------------------ keyed arms
def keyed_tuning(root, out, parts):
    """SAF (k86h arm file) + the K8b keys of `parts` through make_config_n31.apply_k8b of the code root, written to
    <out>/sa/tuning/config_n31_v2_stopline_observed_full_k8b_<parts>.json (scratch, outside the repository)."""
    import importlib.util
    path = Path(root) / N31 / 'make_config_n31.py'
    spec = importlib.util.spec_from_file_location('k8b_make_config_n31_' + '_'.join(parts), path)
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(path.parent))
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.path.remove(str(path.parent))
    saf = json.loads((Path(root) / N31 / 'config_n31_v2_stopline_observed_full.json').read_text(encoding='utf-8-sig'))
    if sha(Path(root) / N31 / 'config_n31_v2_stopline_observed_full.json') != sc.K8B_K86H_ARM_SHA256['SAF']:
        raise SystemExit('SAF arm file is not the k86h pin')
    doc = mod.apply_k8b(saf, Path(root), parts=tuple(parts))
    dest = Path(out) / 'sa' / 'tuning' / ('config_n31_v2_stopline_observed_full_k8b_%s.json' % '_'.join(parts))
    dest.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(doc, indent=2, ensure_ascii=False).replace('\n', '\r\n').encode('utf-8')
    if not dest.is_file() or dest.read_bytes() != data:
        dest.write_bytes(data)
    want = sorted({'p1': 'urban.sc1002w_saturation', 'p4': 'urban.wout_exit_law',
                   'p2': 'urban.stopline_approach.city_arrival'}[p] for p in parts)
    if sorted(sc.k8b_keys_of(doc)) != want or json.dumps(sc.k8b_strip(doc), sort_keys=True) != json.dumps(
            saf, sort_keys=True):
        raise SystemExit(f'keyed tuning {dest}: keys {sc.k8b_keys_of(doc)} != {want} or differs outside them')
    return tuning_rec(dest), doc


def keyed_capture(tree, seed, T, tuning, H_kind='tl3'):
    args = SimpleNamespace(gates_stage=None, declaration_sha=None)
    sc.k8b_guard(tuning['path'], seed, T, args, f'commit gate capture {tree}')     # probe-sample states only
    return capture(tree, H_kind, 'SAF', seed, T, tuning)


def keyed_job(tree, seed, T, entry, H, tuning, **kw):
    args = SimpleNamespace(gates_stage=None, declaration_sha=None)
    sc.k8b_guard(tuning['path'], seed, T, args, f'commit gate job {tree}')
    return job(tree, 'TL3', T, 'SAF', entry, H, seed=seed, **kw)


def evidence_values(root, rel):
    return json.loads((Path(root) / rel).read_text(encoding='utf-8'))


# ------------------------------------------------------------------------------------------------ G3
CAPFLOW = '''
import pickle, math
from src.models import urban_queue_model as uqm
t = pickle.loads(open(sys.argv[1], 'rb').read())
follower, state, reference, forecast = t['owned']
cfg = follower.cfg
specs = uqm.movement_specs(cfg)
out = {}
for m in sys.argv[2].split(','):
    out[m] = float(uqm._movement_capacity_flow(reference, cfg, m, specs[m]))
print(json.dumps(out))
'''


def g3(commit, root, part):
    out = GATES / commit
    setup(root, out)
    tree_k = f'{commit}_{part}'
    tuning, doc = keyed_tuning(root, out, (part,))
    rows, ok = {}, True
    for seed, T in G2_STATES:
        cap_k = keyed_capture(tree_k, seed, T, tuning)
        cap_0 = capture(commit, 'tl3', 'SAF', seed, T, arm_tuning(root, 'SAF'))
        r = {'capture_ok': (sc.read_json(cap_k / 'capture.json', {}) or {}).get('ok') is True}
        meta = (sc.read_json(cap_k / 'capture.json', {}) or {}).get('metadata') or {}
        r['g9'] = g9_rows(root, cap_k / 'template.pickle', cap_0 / 'template.pickle', cap_k / 'capture.json',
                          cap_0 / 'capture.json')
        jobs = {}
        for H in (1, 3):
            jd = keyed_job(tree_k, seed, T, 'OBS', H, tuning)
            s = sc.read_json(jd / 'summary.json', {}) or {}
            last = (s.get('blocks') or [{}])[-1].get('k8b0') or {}
            jobs[f'H{H}'] = {'ok': s.get('ok'), 'error_kind': s.get('error_kind'), 'error': (s.get('error') or '')[-300:],
                             'recorder_errors': s.get('recorder_errors'),
                             'wout_counters_last': last.get('wout_counters'),
                             'city_arrival_last': last.get('city_arrival')}
        r['jobs'] = jobs
        if part == 'p1':
            r['p1'] = g3_p1(root, cap_k, cap_0, meta)
        elif part == 'p4':
            r['p4'] = {'meta': meta.get('k8b_p4'),
                       'shrink_zero': all(((j.get('wout_counters_last') or {}).get('shrink_veh', None) == 0.0)
                                          for j in jobs.values()),
                       'store_present': all(j.get('wout_counters_last') is not None for j in jobs.values())}
        elif part == 'p2':
            r['p2'] = {'meta_p2': meta.get('k8b_p2'), 'meta_p2_init': meta.get('k8b_p2_init'),
                       'city_present': all(j.get('city_arrival_last') is not None for j in jobs.values())}
        r['ok'] = (r['capture_ok'] and r['g9']['equal'] and all(j['ok'] for j in jobs.values())
                   and all(not j['recorder_errors'] for j in jobs.values())
                   and (part != 'p1' or r['p1']['ok'])
                   and (part != 'p4' or (r['p4']['shrink_zero'] and r['p4']['store_present']))
                   and (part != 'p2' or r['p2']['city_present']))
        ok &= r['ok']
        rows[f's{seed}_{T}'] = r
    if part in ('p4', 'p2'):
        seed, T = ADFULL_STATE
        keyed_capture(tree_k, seed, T, tuning)
        jd = keyed_job(tree_k, seed, T, 'A1', 3, tuning, variant='ADREF', mode='ad_full', action='REFERENCE')
        s = sc.read_json(jd / 'summary.json', {}) or {}
        par = s.get('s3_parity') or {}
        ad = {'ok': s.get('ok'), 'state_error': s.get('max_primal_state_error'),
              'complete_match': s.get('complete_primal_state_match'),
              's3': {k: par.get(k) for k in ('installed', 'compares', 'excluded_records', 'sa_created')},
              'error': (s.get('error') or '')[-600:]}
        ad['pass'] = bool(s.get('ok') and ad['complete_match'] is True and ad['state_error'] is not None
                          and ad['state_error'] <= sc.G11_STATE_ERROR and par.get('installed')
                          and par.get('compares') and par.get('excluded_records') == 0 and par.get('sa_created') == 0)
        ok &= ad['pass']
        rows['adfull_s31_3300'] = ad
    res = {'gate': 'G3', 'part': part, 'commit': commit, 'root': str(root), 'tuning': tuning,
           'k8b_keys': sc.k8b_keys_of(doc), 'verdict': 'PASS' if ok else 'FAIL', 'rows': rows}
    write(out / f'gate_G3_{part}.json', res)
    return res


def g3_p1(root, cap_k, cap_0, meta):
    m1 = meta.get('k8b_p1') or {}
    ev = evidence_values(root, N31 / 'k8b' / 'sc1002w_saturation_v3c3_20261007.json')['values']
    s3, s4 = float(ev['s_p3_veh_h_lane']), float(ev['s_p4_veh_h_lane'])
    mem = ev['members']
    beta = m1.get('beta') or {}
    want = {mem['E']: float(ev['lanes_p3']) * s3 * beta['E'] / (beta['E'] + beta['S']),
            mem['S']: float(ev['lanes_p3']) * s3 * beta['S'] / (beta['E'] + beta['S']),
            mem['N']: float(ev['lanes_p4']) * s4} if beta else {}
    got = python_in_root(root, CAPFLOW, str(cap_k / 'template.pickle'), ','.join(mem.values()))
    caps_k = load_template(root, cap_k / 'template.pickle')['owned'][0].cfg.network.movement_capacity_by_movement_veh_h
    caps_0 = load_template(root, cap_0 / 'template.pickle')['owned'][0].cfg.network.movement_capacity_by_movement_veh_h
    others = sorted(m for m in set(caps_k) | set(caps_0) if m not in mem.values()
                    and json.dumps(caps_k.get(m)) != json.dumps(caps_0.get(m)))
    err = {m: abs(got[m] - want[m]) for m in want}
    return {'meta': m1, 'want': want, 'first_step': got, 'abs_err': err, 'others_differ': others[:20],
            'meta_values_equal_evidence': (m1.get('s_p3') == s3 and m1.get('s_p4') == s4
                                           and m1.get('evidence_sha256') == sha(Path(root) / N31 / 'k8b'
                                                                                / 'sc1002w_saturation_v3c3_20261007.json')),
            'ok': bool(want) and all(v <= 1e-9 for v in err.values()) and not others
                  and m1.get('s_p3') == s3 and m1.get('s_p4') == s4}


# ------------------------------------------------------------------------------------------------ G4
P1_MAP = {'before': 'before', 'after': 'after', 'beta': 'beta', 's_p3': 's_p3', 's_p4': 's_p4'}


def g4(commit, root, part):
    out = GATES / commit
    setup(root, out)
    rows, ok = {}, True
    if part == 'p1':
        tree_k = f'{commit}_p1'
        tuning, _ = keyed_tuning(root, out, ('p1',))
        for seed, T in G2_STATES:
            cap_k = keyed_capture(tree_k, seed, T, tuning)
            pc = (PROBE / 'out' / 'sa' / 'cap' / 'k8b_C1' / 'TL3' / (f'{T:06d}' + ('' if seed == 31 else f'_s{seed}'))
                  / 'SAF')
            tk, tp = load_template(root, cap_k / 'template.pickle'), load_template(root, pc / 'template.pickle')
            probe_meta = getattr(tp['owned'][0].cfg.network, 'k8b_probe_capture', None) or {}
            try:
                delattr(tp['owned'][0].cfg.network, 'k8b_probe_capture')       # probe-only attribute (record)
            except AttributeError:
                pass
            r = {'template': compare_docs(tk, tp)}
            r['template']['equal'] = r['template']['numeric_differ'] == 0
            mine = ((sc.read_json(cap_k / 'capture.json', {}) or {}).get('metadata') or {}).get('k8b_p1') or {}
            pm = probe_meta.get('P1') or {}
            r['meta_map'] = {k: json.dumps(mine.get(v), sort_keys=True) == json.dumps(pm.get(k), sort_keys=True)
                             for k, v in P1_MAP.items()}
            r['capture_json'] = compare_docs(sc.read_json(cap_k / 'capture.json'), sc.read_json(pc / 'capture.json'))
            r['ok'] = r['template']['equal'] and all(r['meta_map'].values()) and r['capture_json']['equal']
            ok &= r['ok']
            rows[f's{seed}_{T}'] = r
    else:
        tree_k = f'{commit}_all'
        tuning, _ = keyed_tuning(root, out, ('p1', 'p4', 'p2'))
        states = [(s, T, 3) for s, T in G4_H3] + [G4_LONG]
        for seed, T, H in states:
            keyed_capture(tree_k, seed, T, tuning)
            jd = keyed_job(tree_k, seed, T, 'OBS', H, tuning)
            mj = MINI / 'out' / 'sa' / 'jobs' / 'k8b' / f'PROBE_{T}_s{seed}_A7p_OBS_H{H}'
            r = compare_docs(sc.read_json(jd / 'summary.json'), sc.read_json(mj / 'summary.json'), tol_rel=TOL_REL)
            r['mine_ok'] = (sc.read_json(jd / 'summary.json', {}) or {}).get('ok')
            r['objective_repr'] = [(sc.read_json(jd / 'summary.json', {}) or {}).get('objective_repr'),
                                   (sc.read_json(mj / 'summary.json', {}) or {}).get('objective_repr')]
            r['ok'] = bool(r['mine_ok']) and r['equal']
            ok &= r['ok']
            rows[f's{seed}_{T}_H{H}'] = r
    res = {'gate': 'G4', 'part': part, 'commit': commit, 'root': str(root), 'verdict': 'PASS' if ok else 'FAIL',
           'rows': rows, 'tolerance_rel': TOL_REL if part != 'p1' else 0.0}
    write(out / f'gate_G4_{part}.json', res)
    return res


# ------------------------------------------------------------------------------------------------ chain
def run_argv(argv):
    cmd = argv[0]
    kv = {}
    rest = []
    i = 1
    while i < len(argv):
        if argv[i].startswith('--'):
            if i + 1 < len(argv) and not argv[i + 1].startswith('--'):
                kv[argv[i][2:]] = argv[i + 1]
                i += 2
                continue
            kv[argv[i][2:]] = True
            i += 1
            continue
        rest.append(argv[i])
        i += 1
    if cmd == 'extract':
        return extract(kv['rev'], kv['dest'], kv.get('like'))
    if cmd == 'prep':
        return prep(kv['root'], kv['out'])
    if cmd == 'anchor':
        return anchor(kv['root'])
    if cmd == 'g1':
        return g1(kv['commit'], kv['root'], unit_only=bool(kv.get('unit-only')))
    if cmd == 'g2':
        return g2(kv['commit'], kv['root'])
    if cmd == 'g3':
        return g3(kv['commit'], kv['root'], kv['part'])
    if cmd == 'g4':
        return g4(kv['commit'], kv['root'], kv['part'])
    if cmd == 'unit':
        setup(kv['root'], GATES / kv['commit'])
        p = unit(kv['root'], GATES / kv['commit'], kv['name'], rest)
        res = unit_summary(p)
        write(GATES / kv['commit'] / f'unit_{kv["name"]}.json', res)
        return res
    raise SystemExit('unknown command ' + cmd)


def chain(plan_path):
    plan = json.loads(Path(plan_path).read_text(encoding='utf-8'))
    status = Path(plan_path).with_suffix('.status')
    stop = Path(plan_path).with_suffix('.STOP')
    for i, step in enumerate(plan['steps']):
        if stop.exists():
            status.write_text(f'STOPPED {i}', encoding='utf-8')
            return 3
        status.write_text(f'RUNNING {i}/{len(plan["steps"])} {json.dumps(step)}', encoding='utf-8')
        res = run_argv(step)
        verdict = res.get('verdict') if isinstance(res, dict) else None
        if verdict == 'FAIL' and plan.get('stop_on_fail', True):
            status.write_text(f'GATE_FAIL {i} {json.dumps(step)}', encoding='utf-8')
            return 4
    status.write_text(f'CHAIN_DONE {len(plan["steps"])}', encoding='utf-8')
    return 0


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ('-h', '--help'):
        print(__doc__)
        return 0
    if sys.argv[1] == 'chain':
        return chain(sys.argv[2])
    res = run_argv(sys.argv[1:])
    if isinstance(res, dict) and 'verdict' in res:
        print('K8B_COMMIT_GATE', res.get('gate'), res.get('part'), res['verdict'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
