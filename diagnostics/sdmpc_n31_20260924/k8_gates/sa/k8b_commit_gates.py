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
    python -B k8b_commit_gates.py g5      --commit L --base-root R0 --base-label L0 --root R1 --label L1
    python -B k8b_commit_gates.py g6      --commit L --root R --label L1 [--report-only]
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
  G4  probe reproduction: p1 = the captures of the probe k8b_C1 (template and capture.json numeric fields; probe
      metadata net.k8b_probe_capture.P1 <-> capture metadata k8b_p1, fixed map; string leaves -- the tuning file hash
      /tuning/sha256, tree and path strings -- and one-sided leaves are listed, outside the numeric rule: AMENDMENT_18
      section 2.4-1, D-K8b-6); all = SAF + P-1 + P-4 (variant A) + P-2 at
      s31 1650, s31 3300, s43 1500, s47 3450 (H3 OBS) and L2 s47 4800 H27 OBS = the mini-probe v2 A7p summaries
      (D:/VISSIM-merge/k8b_miniprobe/out/sa/jobs/k8b) in every common numeric leaf (timing excluded); a difference is
      accepted only when relative <= 1e-9 (listed with its cause), else STOP.
  G5  (AMENDMENT_18 section 3.3, K8b-5) K8b keys on, the probe-sample states (PROBE_SAMPLE.json sha checked: H3 24
      + L1 s43 2400 H42 + L2 s47 4800 H27, all OBS): two code roots (the base and the new commit tree) run by this
      tool and harness with the repository SAF-K8b arm file of each root (both sha256 equal, else refused); outputs
      <gates>/<commit>/g5/<label>/.  Per state the keyed capture's template numeric leaves, its capture.json numeric
      leaves and the job summary numeric leaves (the /k8b0 and signal_queue leaves included) are bit-equal (tolerance
      0); string leaves are equal, except leaves whose key names a sha / hash (listed with both values, not judged)
      and path strings of the two roots / outputs (listed); excluded: the timing rule (SKIP), path / root / tree /
      label names, template_sha256, capture_spec, python_hash_seed.  A one-sided leaf passes only as a renamed
      counter pair (G5_RENAMED: the old name on the base side with the new name on the new side, or neither); every
      other one-sided leaf fails.  Every job ok, no recorder error, objective repr equal.
  G6  (AMENDMENT_18 section 3.3) ad_full state parity at several probe states: the SAF-K8b arm, A1 H3, action
      REFERENCE (ADREF) at G6_STATES and ADM2ALL at s31 3300; pass = the G3 ad_full rule (ok, complete primal match,
      max_primal_state_error <= 1e-8, S3 wrapper installed, compares > 0, excluded 0, SA-created 0) for every job.
      --report-only (the base-tree control R-ctl) writes report_<label>.json with verdict REPORT.
K8b-keyed captures / jobs run only at probe-sample states (sa_common.k8b_guard is called before each).

K9-1 (K9-1-0, K8_PREDECLARATION_AMENDMENT_19 r2 section 4; outputs <gates>/<commit>/ as above):
    python -B k8b_commit_gates.py k9units --commit L --root R [K9 test file ...]
    python -B k8b_commit_gates.py k9build --commit L --root R --parts w1[,w2a[,f17b]] [--k91-arms]
    python -B k8b_commit_gates.py g5k9    --commit L --root R --label L1
    python -B k8b_commit_gates.py g6k9    --commit L --root R --label L1 [--parts w1,...] [--z1b] [--no-zdiag]
    python -B k8b_commit_gates.py g3k9    --commit L --root R --part w1|w2a|f17b
    python -B k8b_commit_gates.py g4k9    --commit L --root R --parts w1[,w2a[,f17b]]
    python -B k8b_commit_gates.py g4ref                                     (A1 L2 reference, frozen probe tree)
    python -B k8b_commit_gates.py armid   --commit L --root R
    python -B k8b_commit_gates.py zdiag   --commit L --root R            (report: the direct-row whole-state probe)
  U   K8b units 29 + the g1units SA files 90 (GIT_DIR of the K8 worktree, K8_SA_BASE_REV ec063ffa) + the harness units
      (test_k8b_harness, test_k91_harness) + the commit's K9 unit files; all passed, nothing skipped -> gate_U.json.
  B   evidence --check: SA (05c821f6), K8b p1 / p2 / p4 (32e48781 / ef75c8e6 / 314b5c8e), the commit's K9 parts;
      make_config_n31 --k8b --check (af2a7783 / f5189611); from K9-1-4 --k91 --check; r2 B-r1-10 the committed K9
      evidence 'values' = the K91_VALUES.json (713d232e) values bit for bit (canonical JSON) -> gate_B.json.
  G3  that commit's K9 key alone on SAF-K8b at s31 1650 / s43 3450 (captures + H1 / H3 OBS): runs ok, no recorder
      error, G-EB-9 rows key on / off byte-equal, capture metadata = evidence; w1 the first-step capacity flows of the
      three W1 movements = the section 2.1 formula (+-1e-9) and every other capacity byte-equal; w2a side class,
      shrink 0, the one branch wout_handover; f17b the forecast = the rule recomputed from the window documents
      (+-1e-12), the J1 equivalence (R-obs decision bundle: the same integer counts, s_hat +-1e-12) and the FH capture
      (fh --T 1650 --seeds 31 --frames T) E_W shares bit-equal to SAF-K8b's.
  G4  SAF-K8b + the K9 keys up to the commit at s31 1650 / s31 3300 / s43 1500 / s47 3450 H3 and L2 s47 4800 H27 OBS
      vs the frozen mini-probe arm (w1 A1, + w2a A2, + f17b A3): summary numeric leaves within relative 1e-9.
  G5  SAF-K8b (keys off) on the 26 probe states vs the K8b-5 outputs <gates>/k8b5/g5/k8b5 (read only, never rerun):
      the AMENDMENT_18 G5 rule, tolerance 0; one-sided leaves only under the K9-1-0 record (/k91).
  G6  SAF-K8b + the K9 keys up to the commit, the eight probe states A1 H3 ADREF + s31 3300 ADM2ALL (the G3 ad_full
      rule) + the direct-row whole-state probe (tests/k8b5_parity_probe.py direct_row, forward / reverse-v1): key
      divergence 0 (from K9-1-0b on)."""
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


def listed_leaves(a, b):
    """Report lists (never judged): every common string leaf that differs and every one-sided leaf, after EXCLUDE /
    SKIP (compare_docs gives counts and the first examples only)."""
    na, sa_ = leaves(a)
    nb, sb_ = leaves(b)
    return {'string_differ': [[k, sa_[k], sb_[k]] for k in sorted(set(sa_) & set(sb_))
                              if not excluded(k) and sa_[k] != sb_[k]],
            'one_sided_a': sorted(k for k in (set(na) | set(sa_)) - (set(nb) | set(sb_)) if not excluded(k)),
            'one_sided_b': sorted(k for k in (set(nb) | set(sb_)) - (set(na) | set(sa_)) if not excluded(k))}


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
            # AMENDMENT_18 section 2.4-1 (D-K8b-6): the declared rule of AMENDMENT_16 r2 section 4.1 judges numeric
            # fields only; string and one-sided leaves are listed, not judged.
            r['capture_json']['strings_not_judged'] = True
            r['capture_json']['strings_note'] = ('the tuning file hash (/tuning/sha256), tree and path strings are '
                                                 'outside the numeric rule')
            r['capture_json']['listed'] = listed_leaves(sc.read_json(cap_k / 'capture.json'),
                                                        sc.read_json(pc / 'capture.json'))
            r['capture_json']['equal'] = r['capture_json']['numeric_differ'] == 0
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
    if part == 'p1':
        res['rule'] = ('AMENDMENT_16 r2 section 4.1 G4 K8b-1 as declared (AMENDMENT_18 section 2.4-1): template numeric '
                       'leaves differ 0, capture.json numeric leaves differ 0 (timing excluded), meta map 5/5; string '
                       'leaves (the tuning file hash /tuning/sha256, trees, paths) and one-sided leaves listed only')
    write(out / f'gate_G4_{part}.json', res)
    return res


# ------------------------------------------------------------------------------------------------ G5 / G6 (K8b-5)
# AMENDMENT_18 sections 2.2-1 and 2.3.4 F-1: the renamed counter pairs (old name, new name); only the pairs a commit
# actually renames appear, the others are absent on both sides.
G5_RENAMED = (('shrink_tiny_events', 'near_balance_events'),
              ('direct_release_events', 'direct_release_band_events'),
              ('direct_matured_events', 'direct_matured_band_events'),
              ('p2_room_fallback_events', 'p2_room_fallback_band_events'))
# section 3.3 G5 exclusions: the timing rule (SKIP), path / root / tree / label names, template_sha256, capture_spec,
# python_hash_seed -- EXCLUDE without /k8b0, signal_queue and /k8b/ (those leaves are compared).
G5_EXCLUDE = ('template_sha256', '/tree', '/label', '/template', '/forecast_long', '/coord', '/job_path', '/eo_dir',
              '/replay', '/robs', '/root', 'path', 'python_hash_seed', 'capture_spec')
K8B_SAF_ARM = 'config_n31_v2_stopline_observed_full_k8b.json'          # repository SAF-K8b arm (K8b-4, af2a7783)
K8B_SAF_ARM_SHA256 = 'af2a7783dd68f285e6d9de13fd21259f16f0c2d3e28c5f7025bd11b28c8bf417'
G6_STATES = ((31, 3300), (31, 1650), (31, 2550), (31, 4350), (43, 2100), (43, 3450), (47, 2850), (47, 5250))
G6_M2ALL = (31, 3300)
_HASH_KEY = None


def probe_sample_states():
    """The probe sample (PROBE_SAMPLE.json, sha256 checked against sa_common): [(seed, T, H)] = H3 24 + L1 + L2."""
    path = PROBE / 'PROBE_SAMPLE.json'
    if sha(path) != sc.K8B_PROBE_SAMPLE_SHA256:
        raise SystemExit(f'{path}: sha256 differs from the declared probe sample; refused')
    doc = sc.read_json(path)
    h3 = [(int(r['seed']), int(r['T']), 3) for r in doc['h3']]
    lg = [(int(r['seed']), int(r['T']), int(r['H'])) for r in doc['long']]
    if {x[:2] for x in h3} != set(sc.K8B_PROBE_H3) or {x[:2] for x in lg} != set(sc.K8B_PROBE_LONG):
        raise SystemExit('PROBE_SAMPLE.json states differ from sa_common K8B_PROBE_H3 / K8B_PROBE_LONG; refused')
    return h3 + lg


def prep_states(states):
    """Replay states (copies; make_replay_state_v2.prepare of the configured code root, prep's rule) of `states`."""
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
    root, out = c.R, c.OUT
    for seed, T in sorted(set(states)):
        c.configure(root=root, out=out, robs=robs_of(seed), nc3=c.NC3)
        dest = sc.replay_dir(T, seed)
        if dest.exists():
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        m.prepare(str(c.DEC), int(T), str(dest))
        log(f'PREP s{seed} {T} -> {dest}')
    c.configure(root=root, out=out, robs=c.DEFAULT_ROBS, nc3=c.NC3)


def saf_k8b_tuning(root):
    rec = tuning_rec(Path(root) / N31 / K8B_SAF_ARM)
    if rec['sha256'] != K8B_SAF_ARM_SHA256:
        raise SystemExit(f'{rec["path"]}: sha256 {rec["sha256"]} is not the K8b-4 SAF-K8b arm; refused')
    return rec


def g5_side(label, root, out, states):
    """Keyed captures + OBS jobs of `states` under one code root (tree label = `label`, output root `out`)."""
    setup(root, out)
    free_space()
    prep_states([(s, T) for s, T, _H in states])
    tuning = saf_k8b_tuning(root)
    rows = {}
    for seed, T, H in states:
        cap = keyed_capture(label, seed, T, tuning)
        jd = keyed_job(label, seed, T, 'OBS', H, tuning)
        rows[(seed, T, H)] = {'cap': cap, 'job': jd}
    return tuning, rows


def _hash_key(key):
    global _HASH_KEY
    if _HASH_KEY is None:
        import re
        _HASH_KEY = re.compile(r'(?<![a-z])sha(1|256)?(?![a-z])|hash')
    return bool(_HASH_KEY.search(key.lower()))


def _norm(text):
    return str(text).replace('\\', '/').lower()


def compare_g5(a, b, path_roots, renamed=G5_RENAMED, allowed_one_sided=()):
    """Section 3.3 G5 rule: numeric leaves bit-equal (NaN = NaN), string leaves equal except sha / hash keys (listed
    when they differ) and path strings of `path_roots` (listed); one-sided leaves only as renamed counter pairs.
    K9-1-0 (amendment 19 r2 section 4.2 G5): `renamed` = the pairs allowed (default the K8b-5 ones) and a one-sided
    leaf whose path contains an `allowed_one_sided` prefix (the K9-1-0 new record, listed in the K9-1-0 commit
    message) passes and is listed."""
    def excl(key):
        k = key.lower()
        return any(s in k for s in SKIP) or any(e.lower() in k for e in G5_EXCLUDE)
    na, sa_ = leaves(a)
    nb, sb_ = leaves(b)
    roots = [_norm(p).rstrip('/') for p in path_roots]
    diffs = []
    for k in sorted(set(na) & set(nb)):
        if excl(k):
            continue
        x, y = na[k], nb[k]
        if x == y or (math.isnan(x) and math.isnan(y)):
            continue
        diffs.append([k, x, y])
    sdiff, hashed, paths, hashed_equal = [], [], [], 0
    for k in sorted(set(sa_) & set(sb_)):
        if excl(k):
            continue
        if _hash_key(k):
            if sa_[k] != sb_[k]:
                hashed.append([k, sa_[k], sb_[k]])
            else:
                hashed_equal += 1
            continue
        if sa_[k] == sb_[k]:
            continue
        if any(r and r in _norm(v) for v in (sa_[k], sb_[k]) for r in roots):
            paths.append([k, sa_[k][:200], sb_[k][:200]])
            continue
        sdiff.append([k, sa_[k][:200], sb_[k][:200]])
    old_new = dict(renamed)
    new_old = {n: o for o, n in renamed}

    def swap(key, mapping):
        head, _, last = key.rpartition('/')
        return head + '/' + mapping[last] if last in mapping else None
    keys_a, keys_b = set(na) | set(sa_), set(nb) | set(sb_)
    one_a = {k for k in keys_a - keys_b if not excl(k)}
    one_b = {k for k in keys_b - keys_a if not excl(k)}
    pairs, bad, allowed = [], [], []
    for k in sorted(one_a):
        if allowed_one_sided and any(p in k for p in allowed_one_sided):
            allowed.append(k)
            continue
        (pairs if swap(k, old_new) in one_b else bad).append(k)
    for k in sorted(one_b):
        if allowed_one_sided and any(p in k for p in allowed_one_sided):
            allowed.append(k)
            continue
        if swap(k, new_old) not in one_a:
            bad.append(k)
    return {'numeric_common': len(set(na) & set(nb)), 'string_common': len(set(sa_) & set(sb_)),
            'numeric_differ': len(diffs), 'string_differ': len(sdiff), 'examples': diffs[:20],
            'string_examples': sdiff[:20], 'hash_strings_differ': hashed, 'hash_strings_equal': hashed_equal,
            'path_strings_differ': paths[:50], 'n_path_strings_differ': len(paths),
            'renamed_pairs': len(pairs), 'renamed_examples': pairs[:10],
            'one_sided_allowed': len(allowed), 'one_sided_allowed_examples': allowed[:10],
            'one_sided_failing': len(bad), 'one_sided_failing_examples': bad[:20],
            'equal': not diffs and not sdiff and not bad}


def _last_counter(summary, group, keys):
    blocks = (summary or {}).get('blocks') or [{}]
    rec = ((blocks[-1] or {}).get('k8b0') or {})
    src = rec.get(group) or {}
    if group == 'city_arrival':
        src = src.get('counters') or {}
    return {k: src.get(k) for k in keys}


def g5(commit, base_root, base_label, root, label):
    """AMENDMENT_18 section 3.3 G5 (base side first, then the new side, then the comparison)."""
    out = GATES / commit
    states = probe_sample_states()
    sides = {}
    for lab, rt in ((base_label, base_root), (label, root)):
        sides[lab] = (rt, out / 'g5' / lab) + g5_side(lab, rt, out / 'g5' / lab, states)
    setup(root, out)
    t_base, t_new = sides[base_label][2], sides[label][2]
    if t_base['sha256'] != t_new['sha256']:
        raise SystemExit(f'G5 tuning sha256 differ: {t_base} vs {t_new}; refused')
    path_roots = [base_root, root, out / 'g5' / base_label, out / 'g5' / label]
    rows, ok, walls = {}, True, []
    for seed, T, H in states:
        b, n = sides[base_label][3][(seed, T, H)], sides[label][3][(seed, T, H)]
        sb, sn = sc.read_json(b['job'] / 'summary.json', {}) or {}, sc.read_json(n['job'] / 'summary.json', {}) or {}
        r = {'template': compare_g5(load_template(root, b['cap'] / 'template.pickle'),
                                    load_template(root, n['cap'] / 'template.pickle'), path_roots),
             'capture_json': compare_g5(sc.read_json(b['cap'] / 'capture.json'), sc.read_json(n['cap'] / 'capture.json'),
                                        path_roots),
             'summary': compare_g5(sb, sn, path_roots)}
        r['jobs_ok'] = [sb.get('ok'), sn.get('ok')]
        r['recorder_errors'] = [sb.get('recorder_errors'), sn.get('recorder_errors')]
        r['objective_repr'] = [sb.get('objective_repr'), sn.get('objective_repr')]
        r['near_balance_events_last'] = _last_counter(sn, 'wout_counters', ('near_balance_events',))
        r['shrink_tiny_events_last_base'] = _last_counter(sb, 'wout_counters', ('shrink_tiny_events',))
        vb = sc.read_json(b['job'] / 'vissim_counts.json', {}) or {}
        vn = sc.read_json(n['job'] / 'vissim_counts.json', {}) or {}
        r['vissim_counts'] = {'base': [vb.get('vissim_count_pre'), vb.get('vissim_count_post')],
                              'new': [vn.get('vissim_count_pre'), vn.get('vissim_count_post')]}
        r['wall_sec'] = [sb.get('wall_sec'), sn.get('wall_sec')]
        if sb.get('wall_sec') and sn.get('wall_sec'):
            walls.append(float(sn['wall_sec']) / float(sb['wall_sec']))
        r['ok'] = (all(r[k]['equal'] for k in ('template', 'capture_json', 'summary')) and sb.get('ok') is True
                   and sn.get('ok') is True and not sb.get('recorder_errors') and not sn.get('recorder_errors')
                   and sb.get('objective_repr') is not None and sb.get('objective_repr') == sn.get('objective_repr'))
        ok &= r['ok']
        rows[f's{seed}_{T}_H{H}'] = r
    walls.sort()
    res = {'gate': 'G5', 'commit': commit, 'base': {'root': str(base_root), 'label': base_label, 'tuning': t_base},
           'new': {'root': str(root), 'label': label, 'tuning': t_new},
           'probe_sample_sha256': sc.K8B_PROBE_SAMPLE_SHA256, 'states': [list(x) for x in states],
           'renamed_pairs_allowed': [list(x) for x in G5_RENAMED], 'exclude': list(G5_EXCLUDE), 'skip': list(SKIP),
           'verdict': 'PASS' if ok else 'FAIL', 'rows': rows,
           'report': {'wall_ratio_new_over_base_median': (walls[len(walls) // 2] if len(walls) % 2 else
                                                          0.5 * (walls[len(walls) // 2 - 1] + walls[len(walls) // 2]))
                      if walls else None, 'wall_pairs': len(walls)},
           'rule': 'AMENDMENT_18 section 3.3 G5 (tolerance 0)'}
    write(out / 'gate_G5.json', res)
    return res


def g6(commit, root, label, report_only=False):
    """AMENDMENT_18 section 3.3 G6 (or, with report_only, the base-tree control R-ctl)."""
    import sa_jobs
    out = GATES / commit
    side = out / 'g6' / label
    states = set((s, T) for s, T, _H in probe_sample_states())
    if not set(G6_STATES) <= states or G6_M2ALL not in states:
        raise SystemExit('G6 states outside the probe sample; refused')
    setup(root, side)
    free_space()
    prep_states(G6_STATES)
    tuning = saf_k8b_tuning(root)
    plan = [(s, T, 'ADREF', 'REFERENCE') for s, T in G6_STATES] + [G6_M2ALL + ('ADM2ALL', sa_jobs.ACTIONS_AD['M2ALL'])]
    rows, ok = {}, True
    for seed, T, variant, action in plan:
        keyed_capture(label, seed, T, tuning)
        jd = keyed_job(label, seed, T, 'A1', 3, tuning, variant=variant, mode='ad_full', action=action)
        s = sc.read_json(jd / 'summary.json', {}) or {}
        par = s.get('s3_parity') or {}
        ad = {'ok': s.get('ok'), 'state_error': s.get('max_primal_state_error'),
              'complete_match': s.get('complete_primal_state_match'),
              's3': {k: par.get(k) for k in ('installed', 'compares', 'excluded_records', 'sa_created')},
              'wall_sec': s.get('wall_sec'), 'error_kind': s.get('error_kind'), 'error_site': s.get('error_site'),
              'error': (s.get('error') or '')[-600:], 'job': str(jd)}
        ad['pass'] = bool(s.get('ok') and ad['complete_match'] is True and ad['state_error'] is not None
                          and ad['state_error'] <= sc.G11_STATE_ERROR and par.get('installed')
                          and par.get('compares') and par.get('excluded_records') == 0 and par.get('sa_created') == 0)
        ok &= ad['pass']
        rows[f's{seed}_{T}_{variant}'] = ad
    res = {'gate': 'G6' if not report_only else 'R-ctl', 'commit': commit, 'root': str(root), 'label': label,
           'tuning': tuning, 'rule': 'AMENDMENT_18 section 3.3 G6 = the G3 ad_full rule per job',
           'failures': sorted(k for k, v in rows.items() if not v['pass']), 'rows': rows,
           'verdict': ('PASS' if ok else 'FAIL') if not report_only else 'REPORT'}
    write(out / ('gate_G6.json' if not report_only else f'report_Rctl_{label}.json'), res)
    return res


# ------------------------------------------------------------------------------------------------ K9-1 (K9-1-0)
# K8_PREDECLARATION_AMENDMENT_19 r2 section 4 (sha sa_common.K91_AMENDMENT19_SHA256), user decisions D-K9-1..6.  The
# K9 commit gates: U (units), B (builders + K91_VALUES), G3 / G4 / G5 / G6 (K9 forms), the direct-row whole-state
# probe (key divergence), the G4 A1 long reference from the frozen probe tree (section 4.2 G4: the probe ran no A1 long
# job), and the K91 arm identity.  G1 / G2 are the K8b ones above (sa_common.k91_guard opens only the section 0.4 list
# on judging states).  Outputs <gates>/<commit>/ like the K8b gates.
K91_PROBE = Path(r'D:/VISSIM-merge/k9_1_probe')                        # read only (the mini-probe, MINI_K91.md)
K91_VALUES = K91_PROBE / 'K91_VALUES.json'
K91_VALUES_SHA256 = '713d232e8f390a72bc47e2bdf467b47c95515af808d5c9989b32941981974187'
K8B5_G5 = GATES / 'k8b5' / 'g5' / 'k8b5'                               # section 4.2 G5 reference (read only)
K8B5_ROOT = Path(r'D:/VISSIM-merge/k8_gate_trees/k8b5')
K8B5_LABEL = 'k8b5'
K91_PARTS = ('w1', 'w2a', 'f17b')
K91_KEY = {'w1': 'urban.sc1001_wout_saturation', 'w2a': 'urban.wout_side_handoff',
           'f17b': 'freeway.offramp_split_forecast'}
K91_EVIDENCE = {'w1': N31 / 'k9' / 'sc1001wout_saturation_v3c3_20261009.json',
                'w2a': N31 / 'k9' / 'wout_side_handoff_v3c3_20261009.json',
                'f17b': N31 / 'k9' / 'offramp_split_forecast_v3c3_20261009.json'}
K91_ARM = {('w1',): 'A1', ('w1', 'w2a'): 'A2', ('w1', 'w2a', 'f17b'): 'A3'}
K91_W1 = ('SC1001_E_SC1002_to_W_RAMP', 'SC1001_N_SC2002_to_W_RAMP', 'SC1001_S_SC1003_to_W_RAMP')
K91_EW = ('10479', '10491', '10638', '10645')
K91_G4_A1_LONG = GATES / 'k91_g4ref' / 'out' / 'sa' / 'jobs' / 'k91A1'   # frozen probe tree A1 L2 (k91_g4ref)
GIT_DIR = r'D:/VISSIM-merge/repo/.git/worktrees/sim3-n31-k8'
FORBIDDEN_TESTS = ('test_b1a_watchdog_attempt_launch.py', 'run_plant_fidelity_matrix', 'test_runner_ps1_obs150.py',
                   'test_native_vbs_clock.py', 'test_tools_launch.py', 'test_tools_replay.py', 'real_watchdog')
K8B_UNIT_FILES = ('test_k8b_p1.py', 'test_k8b_p4.py', 'test_k8b_p2.py')
SA_UNIT_FILES = ('test_stopline_approach.py', 'test_stopline_wiring.py', 'test_stopline_evidence.py')
HARNESS_UNIT_FILES = ('test_k8b_harness.py', 'test_k91_harness.py')
PYTEST_RUNNER = '\n'.join([
    'import ctypes, os, sys',
    'k = ctypes.windll.kernel32',
    'k.GetCurrentProcess.restype = ctypes.c_void_p',
    'k.SetPriorityClass.argtypes = (ctypes.c_void_p, ctypes.c_uint32)',
    'k.SetPriorityClass(k.GetCurrentProcess(), 0x4000)',
    'assert os.environ.get("PYTHONHASHSEED") == "0"',
    'import pytest',
    'sys.exit(pytest.main(["-p", "no:cacheprovider", "-v", *sys.argv[1:]]))', ''])


def _clean_env(extra=None):
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith(('RW_', 'K8_', 'K8G_'))}
    env.update(PYTHONHASHSEED='0', NUMBA_NUM_THREADS='1', PYTHONUTF8='1')
    env.update(extra or {})
    return env


def pytest_log(root, log, files, extra_env=None):
    """pytest -v of `files` (paths relative to the code root) -> log; the forbidden tests are never run."""
    for f in files:
        if any(x in f for x in FORBIDDEN_TESTS):
            raise SystemExit(f'forbidden test {f}')
    log = Path(log)
    log.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    with open(log, 'w', encoding='utf-8') as h:
        h.write(f'ROOT {root}\nFILES {files}\nENV {extra_env}\n')
        h.flush()
        rc = subprocess.run([sys.executable, '-B', '-c', PYTEST_RUNNER, *files], cwd=str(root),
                            env=_clean_env(extra_env), stdout=h, stderr=subprocess.STDOUT,
                            creationflags=c.BELOW_NORMAL).returncode
    text = log.read_text(encoding='utf-8', errors='replace')
    tail = [ln for ln in text.splitlines() if ln.startswith('=') and (' passed' in ln or ' failed' in ln
                                                                       or ' error' in ln)]
    passed = sorted(ln.split(' PASSED')[0].strip() for ln in text.splitlines() if ' PASSED ' in ln)
    bad = [ln for ln in text.splitlines() if ln.startswith(('FAILED', 'ERROR', 'SUBFAILED'))]
    skipped = [ln for ln in text.splitlines() if ' SKIPPED' in ln]
    log_ = f'UNIT {log.name} rc={rc} wall={round(time.time() - t0, 1)} {tail[-1] if tail else None}'
    globals()['log'](log_)
    return {'log': str(log), 'sha256': sha(log), 'rc': rc, 'session': tail[-1] if tail else None,
            'n_passed': len(passed), 'failed': bad[:30], 'skipped': skipped[:30],
            'wall_sec': round(time.time() - t0, 1), 'ok': rc == 0 and not bad and not skipped and bool(tail)}


def k9units(commit, root, k9_files=()):
    """Section 4.2 U: the K8b units (test_k8b_p1 / p4 / p2), the g1units SA files (git objects of the K8 worktree,
    K8_SA_BASE_REV = ec063ffa), the harness units (test_k8b_harness, test_k91_harness: the section 3.1-4 guard
    self-tests, k91_outcome, arm identity) and the new K9 unit files of the commit -> gate_U.json."""
    out = GATES / commit
    setup(root, out)
    t = N31 / 'tests'
    rows = {'k8b': pytest_log(root, out / 'u' / 'unit_k8b.log', [str(t / f) for f in K8B_UNIT_FILES]),
            'sa': pytest_log(root, out / 'u' / 'unit_sa.log', [str(t / f) for f in SA_UNIT_FILES],
                             {'GIT_DIR': GIT_DIR, 'K8_SA_BASE_REV': 'ec063ffa'}),
            'harness': pytest_log(root, out / 'u' / 'unit_harness.log',
                                  [str(N31 / 'k8_gates' / 'sa' / 'tests' / f) for f in HARNESS_UNIT_FILES])}
    if k9_files:
        rows['k9'] = pytest_log(root, out / 'u' / 'unit_k9.log', [str(t / f) for f in k9_files])
    ok = all(r['ok'] for r in rows.values())
    res = {'gate': 'U', 'commit': commit, 'root': str(root), 'rows': rows, 'k9_files': list(k9_files),
           'verdict': 'PASS' if ok else 'FAIL',
           'rule': 'amendment 19 r2 section 4.2 U: K8b units + g1units (SA three files) + harness units + K9 units, '
                   'all passed, no skip, no forbidden test'}
    write(out / 'gate_U.json', res)
    return res


def _run_py(root, args, log_name, out, timeout=None):
    t0 = time.time()
    done = subprocess.run([sys.executable, '-B', *args], cwd=str(root), env=_clean_env(), capture_output=True,
                          text=True, encoding='utf-8', errors='replace', creationflags=c.BELOW_NORMAL,
                          timeout=timeout)
    p = Path(out) / 'b' / log_name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(done.stdout + '\n--- stderr ---\n' + done.stderr, encoding='utf-8')
    return done.returncode, done.stdout, done.stderr, round(time.time() - t0, 1)


def _canon(x):
    return json.dumps(x, sort_keys=True, ensure_ascii=False)


def k9build(commit, root, parts, k91_arms=False):
    """Section 4.2 B: SA / K8b / K9 evidence --check, make_config --k8b --check (two arms), from K9-1-4 --k91 --check;
    r2 B-r1-10: each committed K9 evidence 'values' = the K91_VALUES.json P0 values bit for bit (canonical JSON)."""
    out = GATES / commit
    setup(root, out)
    if sha(K91_VALUES) != K91_VALUES_SHA256:
        raise SystemExit('K91_VALUES.json sha256 differs from the pin; refused')
    vals = json.loads(K91_VALUES.read_text(encoding='utf-8'))
    rows = {}
    rc, so, se, w = _run_py(root, [str(N31 / 'stopline' / 'build_sc1001eb_evidence.py'), '--check'], 'sa.log', out)
    rows['builder_sa'] = {'rc': rc, 'tail': so[-400:], 'wall_sec': w, 'ok': rc == 0,
                          'evidence_sha256': sha(Path(root) / N31 / 'stopline' / 'sc1001eb_evidence_v3c3_20261004.json')}
    rows['builder_sa']['ok'] &= rows['builder_sa']['evidence_sha256'].startswith('05c821f6')
    for p, want in (('p1', '32e48781'), ('p2', 'ef75c8e6'), ('p4', '314b5c8e')):
        rc, so, se, w = _run_py(root, [str(N31 / 'k8b' / 'build_k8b_evidence.py'), p, '--check'], f'k8b_{p}.log', out)
        line = next((ln for ln in so.splitlines() if 'K8B_EVIDENCE_CHECK_OK' in ln), None)
        rows[f'builder_{p}'] = {'rc': rc, 'line': line, 'wall_sec': w,
                                'ok': rc == 0 and line is not None and line.split()[-1].startswith(want)}
    for p in parts:
        rc, so, se, w = _run_py(root, [str(N31 / 'k9' / 'build_k9_evidence.py'), p, '--check'], f'k9_{p}.log', out)
        line = next((ln for ln in so.splitlines() if 'K9_EVIDENCE_CHECK_OK' in ln), None)
        doc = json.loads((Path(root) / K91_EVIDENCE[p]).read_text(encoding='utf-8'))
        want = vals['evidence'][p]
        same = _canon(doc['values']) == _canon(want['values'])
        vsha = hashlib.sha256(_canon(doc['values']).encode('utf-8')).hexdigest()
        rows[f'builder_{p}'] = {'rc': rc, 'line': line, 'wall_sec': w, 'stderr_tail': se[-600:],
                                'file_sha256': sha(Path(root) / K91_EVIDENCE[p]), 'probe_file_sha256': want['sha256'],
                                'values_equal_k91_values': same, 'values_canonical_sha256': vsha,
                                'ok': rc == 0 and line is not None and same and doc.get('schema') == want['schema']}
    for storage, want in (('observed_full', 'af2a7783'), ('geometric', 'f5189611')):
        args = [str(N31 / 'make_config_n31.py'), '--stopline-approach',
                'diagnostics/sdmpc_n31_20260924/stopline/sc1001eb_evidence_v3c3_20261004.json',
                '--stopline-storage', storage, '--k8b', '--check']
        rc, so, se, w = _run_py(root, args, f'mc_k8b_{storage}.log', out)
        rows[f'make_config_k8b_{storage}'] = {'rc': rc, 'tail': so[-300:], 'ok': rc == 0 and f'sha256={want}' in so}
        if k91_arms:
            rc, so, se, w = _run_py(root, args[:-2] + ['--k91', '--check'], f'mc_k91_{storage}.log', out)
            rows[f'make_config_k91_{storage}'] = {'rc': rc, 'tail': so[-300:], 'stderr_tail': se[-600:],
                                                  'ok': rc == 0 and 'CONFIG_N31_STOPLINE_K91_OK' in so}
    ok = all(r['ok'] for r in rows.values())
    res = {'gate': 'B', 'commit': commit, 'root': str(root), 'parts': list(parts), 'k91_arms': k91_arms,
           'rows': rows, 'verdict': 'PASS' if ok else 'FAIL',
           'rule': 'amendment 19 r2 section 4.2 B (+ r2 B-r1-10 K91_VALUES bit equality of every committed K9 values)'}
    write(out / 'gate_B.json', res)
    return res


def keyed_tuning_k9(root, out, parts, z1b=False):
    """SAF-K8b (the repository K8b-4 arm af2a7783) + the K9 keys of `parts` through make_config_n31.apply_k91 of the
    code root -> <out>/sa/tuning/config_n31_v2_stopline_observed_full_k91_<parts>.json (scratch).  No part: the
    SAF-K8b arm itself."""
    base = saf_k8b_tuning(root)
    if not parts and not z1b:
        return base, json.loads(Path(base['path']).read_text(encoding='utf-8-sig'))
    import importlib.util
    path = Path(root) / N31 / 'make_config_n31.py'
    spec = importlib.util.spec_from_file_location('k91_make_config_n31_' + '_'.join(parts), path)
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(path.parent))
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.path.remove(str(path.parent))
    saf = json.loads(Path(base['path']).read_text(encoding='utf-8-sig'))
    doc = mod.apply_k91(saf, Path(root), parts=tuple(parts), latent_touch=z1b)
    name = '_'.join(list(parts) + (['z1b'] if z1b else []))
    dest = Path(out) / 'sa' / 'tuning' / f'config_n31_v2_stopline_observed_full_k91_{name}.json'
    dest.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(doc, indent=2, ensure_ascii=False).replace('\n', '\r\n').encode('utf-8')
    if not dest.is_file() or dest.read_bytes() != data:
        dest.write_bytes(data)
    want = [k for k in sc.K91_ARM_KEYS if any(K91_KEY[p] == k for p in parts)] + ([sc.K91_Z1B_KEY] if z1b else [])
    if sc.k9_keys_of(doc) != want or _canon(sc.k9_strip(doc)) != _canon(saf):
        raise SystemExit(f'keyed K9 tuning {dest}: keys {sc.k9_keys_of(doc)} != {want} or differs outside them')
    return tuning_rec(dest), doc


def _ensure_history(seed, T, keys):
    """F17b-keyed capture: the same-seed R-obs obs150 derived documents T' < T in the replay (sa_common rule)."""
    if K91_KEY['f17b'] in keys:
        c.configure(root=c.R, out=c.OUT, robs=robs_of(seed), nc3=c.NC3)
        sc.k91_history_copy(sc.replay_dir(T, seed), c.DEC, T)
        c.configure(root=c.R, out=c.OUT, robs=c.DEFAULT_ROBS, nc3=c.NC3)


def k9_capture(tree, seed, T, tuning, kind='tl3'):
    args = SimpleNamespace(gates_stage=None, declaration_sha=None)
    keys = sc.k91_guard(tuning['path'], seed, T, args, f'commit gate capture {tree}', op='capture', harness='TL3',
                        arm='SAF')
    return capture(tree, kind, 'SAF', seed, T, tuning)


def k9_job(tree, seed, T, entry, H, tuning, **kw):
    args = SimpleNamespace(gates_stage=None, declaration_sha=None)
    sc.k91_guard(tuning['path'], seed, T, args, f'commit gate job {tree}', op='job', harness='TL3', arm='SAF',
                 entry=entry, H=H, variant=kw.get('variant', 'REF'), mode=kw.get('mode', 'scalar'))
    return job(tree, 'TL3', T, 'SAF', entry, H, seed=seed, **kw)


def _states_g5():
    return probe_sample_states()


def g5k9(commit, root, label):
    """Section 4.2 G5: K9 keys off (the repository SAF-K8b arm af2a7783 of the new root) on the 26 probe states vs the
    K8b-5 outputs <gates>/k8b5/g5/k8b5 (read only; never rerun): AMENDMENT_18 section 3.3 G5 rule (tolerance 0, the
    K8b-5 exclusions), one-sided leaves allowed only under the K9-1-0 new record (sa_common.K91_NEW_RECORD, listed in
    the K9-1-0 commit message), sha / hash string leaves listed with the file list, not judged."""
    out = GATES / commit
    states = _states_g5()
    base_side = {}
    for seed, T, H in states:                                  # the read-only base must be complete
        c.configure(root=str(K8B5_ROOT), out=str(K8B5_G5), robs=robs_of(seed), nc3=c.NC3)
        cap = sc.cap_dir(K8B5_LABEL, 'TL3', T, 'SAF', seed=seed)
        jd = sc.job_dir(K8B5_LABEL, sc.job_label('TL3', T, 'SAF', 'OBS', H, seed=seed))
        if not ((cap / 'capture.json').is_file() and (cap / 'template.pickle').is_file()
                and (jd / 'summary.json').is_file()):
            raise SystemExit(f'K8b-5 G5 output missing for s{seed} {T} H{H}: {cap} / {jd}')
        base_side[(seed, T, H)] = {'cap': cap, 'job': jd}
    t_new, new_rows = g5_side(label, root, out / 'g5' / label, states)
    setup(root, out)
    t_base = (sc.read_json(next(iter(base_side.values()))['cap'] / 'capture.json') or {}).get('tuning') or {}
    if t_base.get('sha256') != t_new['sha256'] or t_new['sha256'] != K8B_SAF_ARM_SHA256:
        raise SystemExit(f'G5 tuning sha256 differ: {t_base} vs {t_new}; refused')
    path_roots = [K8B5_ROOT, root, K8B5_G5, out / 'g5' / label]
    rows, ok, walls, hash_keys = {}, True, [], set()
    for seed, T, H in states:
        b, n = base_side[(seed, T, H)], new_rows[(seed, T, H)]
        sb, sn = sc.read_json(b['job'] / 'summary.json', {}) or {}, sc.read_json(n['job'] / 'summary.json', {}) or {}
        r = {'template': compare_g5(load_template(root, b['cap'] / 'template.pickle'),
                                    load_template(root, n['cap'] / 'template.pickle'), path_roots, renamed=(),
                                    allowed_one_sided=sc.K91_NEW_RECORD),
             'capture_json': compare_g5(sc.read_json(b['cap'] / 'capture.json'), sc.read_json(n['cap'] / 'capture.json'),
                                        path_roots, renamed=(), allowed_one_sided=sc.K91_NEW_RECORD),
             'summary': compare_g5(sb, sn, path_roots, renamed=(), allowed_one_sided=sc.K91_NEW_RECORD)}
        for part in ('template', 'capture_json', 'summary'):
            hash_keys |= {h[0] for h in r[part]['hash_strings_differ']}
        r['jobs_ok'] = [sb.get('ok'), sn.get('ok')]
        r['recorder_errors'] = [sb.get('recorder_errors'), sn.get('recorder_errors')]
        r['objective_repr'] = [sb.get('objective_repr'), sn.get('objective_repr')]
        k91rec = sc.read_json(n['job'] / 'k91_record.json') or {}
        r['k91_record'] = {'keyed': k91rec.get('keyed'), 'z1_touch_events': (k91rec.get('top') or {}).get('z1_touch_events')}
        vb = sc.read_json(b['job'] / 'vissim_counts.json', {}) or {}
        vn = sc.read_json(n['job'] / 'vissim_counts.json', {}) or {}
        r['vissim_counts'] = {'base': [vb.get('vissim_count_pre'), vb.get('vissim_count_post')],
                              'new': [vn.get('vissim_count_pre'), vn.get('vissim_count_post')]}
        r['wall_sec'] = [sb.get('wall_sec'), sn.get('wall_sec')]
        if sb.get('wall_sec') and sn.get('wall_sec'):
            walls.append(float(sn['wall_sec']) / float(sb['wall_sec']))
        r['ok'] = (all(r[k]['equal'] for k in ('template', 'capture_json', 'summary')) and sb.get('ok') is True
                   and sn.get('ok') is True and not sb.get('recorder_errors') and not sn.get('recorder_errors')
                   and sb.get('objective_repr') is not None and sb.get('objective_repr') == sn.get('objective_repr'))
        ok &= r['ok']
        rows[f's{seed}_{T}_H{H}'] = r
    walls.sort()
    res = {'gate': 'G5', 'commit': commit, 'base': {'root': str(K8B5_ROOT), 'out': str(K8B5_G5), 'label': K8B5_LABEL,
                                                     'tuning': t_base, 'read_only': True},
           'new': {'root': str(root), 'label': label, 'tuning': t_new},
           'probe_sample_sha256': sc.K8B_PROBE_SAMPLE_SHA256, 'states': [list(x) for x in states],
           'allowed_one_sided': list(sc.K91_NEW_RECORD), 'exclude': list(G5_EXCLUDE), 'skip': list(SKIP),
           'hash_keys_differ': sorted(hash_keys),
           'verdict': 'PASS' if ok else 'FAIL', 'rows': rows,
           'report': {'wall_ratio_new_over_base_median': (walls[len(walls) // 2] if len(walls) % 2 else
                                                          0.5 * (walls[len(walls) // 2 - 1] + walls[len(walls) // 2]))
                      if walls else None, 'wall_pairs': len(walls),
                      'z1_touch_events': {k: v['k91_record']['z1_touch_events'] for k, v in rows.items()}},
           'rule': 'AMENDMENT_19 r2 section 4.2 G5 = AMENDMENT_18 section 3.3 G5 vs the K8b-5 outputs (tolerance 0); '
                   'one-sided leaves only under the K9-1-0 new record'}
    write(out / 'gate_G5.json', res)
    return res


def zdiag(root, out):
    """Section 4.2 G6 (K9-1-0b on): the K8b-5 direct-row probe (tests/k8b5_parity_probe.py direct_row, forward and
    reverse-v1, the code root's own) -- its whole-state comparison (report-only in K8b-5) must show no key divergence
    (exception None) and the K8b parity true."""
    rows, ok = {}, True
    probe = Path(root) / N31 / 'tests' / 'k8b5_parity_probe.py'
    deps = Path(os.environ.get('K8G_DEPS', r'C:\Users\TRLAB\Documents\ChatGPT\VISSIM\.review-deps'))
    for backend in ('forward', 'reverse-v1'):
        extra = {'OMP_NUM_THREADS': '1'}
        if backend == 'reverse-v1':
            extra['PYTHONPATH'] = os.pathsep.join([str(deps / 'sdmpc'), str(deps / 'sdmpc-numba'),
                                                   os.environ.get('PYTHONPATH', '')])
        done = subprocess.run([sys.executable, '-B', str(probe), backend, 'direct_row', str(root)], cwd=str(root),
                              env=_clean_env(extra), capture_output=True, text=True, encoding='utf-8', errors='replace',
                              timeout=900, creationflags=c.BELOW_NORMAL)
        try:
            o = json.loads(done.stdout.strip().splitlines()[-1])
        except Exception:
            o = {'error': (done.stdout + done.stderr)[-2000:]}
        full = o.get('full_state_report_only') or {}
        r = {'rc': done.returncode, 'parity': o.get('parity'), 'full_state_exception': full.get('exception'),
             'full_state_error': full.get('error'), 'touch_or_keys': o.get('pend_keys_after_drain'),
             'error': o.get('error')}
        r['ok'] = done.returncode == 0 and o.get('parity') is True and 'exception' in full and full['exception'] is None
        ok &= r['ok']
        rows[backend] = r
    return {'rows': rows, 'ok': ok}


def g6k9(commit, root, label, parts=(), z1b=False, with_zdiag=True):
    """Section 4.2 G6: the SAF arm with the K9 keys up to the commit (none: SAF-K8b) at the eight probe states, A1 H3
    ADREF + s31 3300 ADM2ALL (the G3 ad_full rule), plus (K9-1-0b on) the direct-row whole-state key divergence 0."""
    import sa_jobs
    out = GATES / commit
    side = out / 'g6' / label
    states = set((s, T) for s, T, _H in probe_sample_states())
    if not set(G6_STATES) <= states or G6_M2ALL not in states:
        raise SystemExit('G6 states outside the probe sample; refused')
    setup(root, side)
    free_space()
    prep_states(G6_STATES)
    tuning, _doc = keyed_tuning_k9(root, side, parts, z1b=z1b)
    plan = [(s, T, 'ADREF', 'REFERENCE') for s, T in G6_STATES] + [G6_M2ALL + ('ADM2ALL', sa_jobs.ACTIONS_AD['M2ALL'])]
    rows, ok = {}, True
    for seed, T, variant, action in plan:
        _ensure_history(seed, T, sc.guard_keys_of(_doc))
        k9_capture(label, seed, T, tuning)
        jd = k9_job(label, seed, T, 'A1', 3, tuning, variant=variant, mode='ad_full', action=action)
        s = sc.read_json(jd / 'summary.json', {}) or {}
        par = s.get('s3_parity') or {}
        ad = {'ok': s.get('ok'), 'state_error': s.get('max_primal_state_error'),
              'complete_match': s.get('complete_primal_state_match'),
              's3': {k: par.get(k) for k in ('installed', 'compares', 'excluded_records', 'sa_created')},
              'wall_sec': s.get('wall_sec'), 'error_kind': s.get('error_kind'), 'error_site': s.get('error_site'),
              'error': (s.get('error') or '')[-600:], 'job': str(jd)}
        ad['pass'] = bool(s.get('ok') and ad['complete_match'] is True and ad['state_error'] is not None
                          and ad['state_error'] <= sc.G11_STATE_ERROR and par.get('installed')
                          and par.get('compares') and par.get('excluded_records') == 0 and par.get('sa_created') == 0)
        ok &= ad['pass']
        rows[f's{seed}_{T}_{variant}'] = ad
    res = {'gate': 'G6', 'commit': commit, 'root': str(root), 'label': label, 'parts': list(parts), 'z1b': z1b,
           'tuning': tuning, 'rule': 'AMENDMENT_19 r2 section 4.2 G6 = the G3 ad_full rule per job (+ direct-row '
                                     'whole-state key divergence 0 from K9-1-0b on)',
           'failures': sorted(k for k, v in rows.items() if not v['pass']), 'rows': rows}
    if with_zdiag:
        res['direct_row_whole_state'] = zdiag(root, side)
        ok &= res['direct_row_whole_state']['ok']
    res['verdict'] = 'PASS' if ok else 'FAIL'
    write(out / 'gate_G6.json', res)
    return res


CAPFLOW_K9 = CAPFLOW


def g3k9(commit, root, part):
    """Section 4.2 G3 (the commit's key alone on SAF-K8b) at the probe states s31 1650 / s43 3450: captures + H1 and
    H3 OBS jobs ok (no ledger / SA / K8b / K9 invariant exception), capture metadata = evidence values, the G-EB-9 rows
    key on / off byte-equal, and per part: w1 the first-step _movement_capacity_flow of the three W1 movements = the
    section 2.1 formula with the recorded beta (+-1e-9) and every other movement capacity byte-equal; w2a the side
    class present and the store shrink 0 on the probe rollouts; f17b the forecast = the evidence rule recomputed
    from the replay's window documents (+-1e-12), the J1 equivalence (the deployed path's window documents -- the
    R-obs decision bundle -- give the same integer counts and s_hat +-1e-12) and the FH capture (fh --T 1650 --seeds 31
    --frames T) E_W shares bit-equal to the SAF-K8b FH capture."""
    out = GATES / commit
    setup(root, out)
    tree_k, tree_0 = f'{commit}_{part}', f'{commit}_k8b'
    tuning, doc = keyed_tuning_k9(root, out, (part,))
    base, _ = keyed_tuning_k9(root, out, ())
    ev = json.loads((Path(root) / K91_EVIDENCE[part]).read_text(encoding='utf-8'))
    ev_sha = sha(Path(root) / K91_EVIDENCE[part])
    rows, ok = {}, True
    for seed, T in G2_STATES:
        _ensure_history(seed, T, sc.guard_keys_of(doc))
        cap_k = k9_capture(tree_k, seed, T, tuning)
        cap_0 = k9_capture(tree_0, seed, T, base)
        rec_k = sc.read_json(cap_k / 'capture.json', {}) or {}
        meta = rec_k.get('metadata') or {}
        r = {'capture_ok': rec_k.get('ok') is True,
             'g9': g9_rows(root, cap_k / 'template.pickle', cap_0 / 'template.pickle', cap_k / 'capture.json',
                           cap_0 / 'capture.json')}
        jobs = {}
        for H in (1, 3):
            jd = k9_job(tree_k, seed, T, 'OBS', H, tuning)
            s = sc.read_json(jd / 'summary.json', {}) or {}
            last = (s.get('blocks') or [{}])[-1] or {}
            jobs[f'H{H}'] = {'ok': s.get('ok'), 'error_kind': s.get('error_kind'),
                             'error': (s.get('error') or '')[-300:], 'recorder_errors': s.get('recorder_errors'),
                             'wout_counters_last': (last.get('k8b0') or {}).get('wout_counters'),
                             'k91_last': last.get('k91')}
        r['jobs'] = jobs
        if part == 'w1':
            r['w1'] = g3_w1(root, cap_k, cap_0, meta.get('k9_w1') or {}, ev, ev_sha)
            r['part_ok'] = r['w1']['ok']
        elif part == 'w2a':
            m = meta.get('k9_w2a') or {}
            v = ev['values']
            want_s = {'free': v['shares']['free'], v['ramp_of']['R_D_E']: v['shares']['R_D_E'],
                      v['ramp_of']['R_D_W']: v['shares']['R_D_W']}
            want_l = {'free': v['l_km']['free'], v['ramp_of']['R_D_E']: v['l_km']['R_D_E'],
                      v['ramp_of']['R_D_W']: v['l_km']['R_D_W']}
            r['w2a'] = {'meta': m, 'shares_equal': m.get('shares') == want_s, 'l_km_equal': m.get('l_km') == want_l,
                        'x_side_equal': m.get('x_side_m') == v['x_side_m'], 'sha_equal': m.get('evidence_sha256') == ev_sha,
                        'branches': [((j.get('k91_last') or {}).get('corridor') or {}).get('branches') for j in jobs.values()],
                        'side_present': all('side_handoff_veh' in (j.get('wout_counters_last') or {}) for j in jobs.values()),
                        'shrink_zero': all((j.get('wout_counters_last') or {}).get('shrink_veh', None) == 0.0
                                           for j in jobs.values())}
            r['part_ok'] = (r['w2a']['shares_equal'] and r['w2a']['l_km_equal'] and r['w2a']['x_side_equal']
                            and r['w2a']['sha_equal'] and r['w2a']['side_present'] and r['w2a']['shrink_zero']
                            and all(b == ['wout_handover'] for b in r['w2a']['branches']))
        else:
            r['f17b'] = g3_f17b(root, seed, T, cap_k, meta.get('k9_f17b') or {}, ev, ev_sha)
            r['part_ok'] = r['f17b']['ok']
        r['ok'] = (r['capture_ok'] and r['g9']['equal'] and all(j['ok'] for j in jobs.values())
                   and all(not j['recorder_errors'] for j in jobs.values()) and r['part_ok'])
        ok &= r['ok']
        rows[f's{seed}_{T}'] = r
    if part == 'f17b':
        rows['fh_s31_1650'] = g3_f17b_fh(root, out, tuning, base)
        ok &= rows['fh_s31_1650']['ok']
    res = {'gate': 'G3', 'part': part, 'commit': commit, 'root': str(root), 'tuning': tuning,
           'k9_keys': sc.k9_keys_of(doc), 'verdict': 'PASS' if ok else 'FAIL', 'rows': rows,
           'rule': 'amendment 19 r2 section 4.2 G3 (common + the part rule)'}
    write(out / f'gate_G3_{part}.json', res)
    return res


def g3_w1(root, cap_k, cap_0, m, ev, ev_sha):
    v = ev['values']
    beta = m.get('beta') or {}
    want = {}
    for key, mv in v['members'].items():
        s = float(v['s_veh_h_lane'][v['group_of'][key]])
        row = v['lanes'][key]
        tot = 0.0
        for lane in row['lanes']:
            group = v['lane_members']['%s|%s' % (row['link'], lane)]
            tot += beta[mv] / sum(beta[x] for x in group) if beta else 0.0
        want[mv] = s * tot
    got = python_in_root(root, CAPFLOW_K9, str(cap_k / 'template.pickle'), ','.join(K91_W1))
    caps_k = load_template(root, cap_k / 'template.pickle')['owned'][0].cfg.network.movement_capacity_by_movement_veh_h
    caps_0 = load_template(root, cap_0 / 'template.pickle')['owned'][0].cfg.network.movement_capacity_by_movement_veh_h
    others = sorted(x for x in set(caps_k) | set(caps_0) if x not in K91_W1
                    and json.dumps(caps_k.get(x)) != json.dumps(caps_0.get(x)))
    err = {mv: abs(got[mv] - want[mv]) for mv in want}
    after = m.get('after') or {}
    return {'want': want, 'first_step': got, 'abs_err': err, 'meta_after': after, 'others_differ': others[:20],
            'meta_values_equal_evidence': (m.get('s') == v['s_veh_h_lane'] and m.get('status') == v['status']
                                           and m.get('rule') == v['rule'] and m.get('evidence_sha256') == ev_sha),
            'ok': bool(beta) and all(e <= 1e-9 for e in err.values()) and not others
                  and all(abs(after.get(mv, float('nan')) - want[mv]) <= 1e-9 for mv in want)
                  and m.get('s') == v['s_veh_h_lane'] and m.get('evidence_sha256') == ev_sha}


F17B_RECOMPUTE = '''
from evaluation.controllers import offramp_split_forecast as F
from evaluation.controllers import obs150_contract as oc
values = json.loads(open(sys.argv[1], encoding='utf-8').read())['values']
T = int(sys.argv[2])
exits = [str(o) for o in values['exits']]
out = {}
for name, directory in (('replay', sys.argv[3]), ('deploy', sys.argv[4])):
    state = json.loads(open(sys.argv[5], encoding='utf-8-sig').read())
    obs = dict(state[oc.RAW_STATE_KEY])
    obs['directory'] = directory
    cur = F.window_counts(obs, T, exits)
    hist = {Tp: F.window_counts(obs, Tp, exits) for Tp in F.windows_of(values['candidate'], T) if Tp != T}
    fc, per, ws = F.forecast_values(values, T, cur, hist)
    out[name] = {'forecast': fc, 'current': {o: list(cur[o]) for o in exits},
                 'history': {str(Tp): {o: list(h[o]) for o in exits} for Tp, h in hist.items()}, 'windows': ws}
print(json.dumps(out))
'''


def _ew_splits(root, cap):
    """The E_W shares the lane freeway runtime holds over the horizon (LFR:34, the FW_W config of the captured
    state's lane_freeway_runtime), read from the template."""
    st = load_template(root, Path(cap) / 'template.pickle')['owned'][1]
    ratio = st.lane_freeway_runtime.configs['FW_W'].network.off_ramp_split_ratio
    return {o: (float(ratio[o]) if o in ratio else None) for o in K91_EW}


def g3_f17b(root, seed, T, cap_k, m, ev, ev_sha):
    """Forecast = the evidence rule (replay window documents, +-1e-12) and the J1 equivalence (the R-obs decision
    bundle = the deployed path's documents: the same integer counts and s_hat +-1e-12)."""
    c.configure(root=c.R, out=c.OUT, robs=robs_of(seed), nc3=c.NC3)
    replay, dec = sc.replay_dir(T, seed), c.DEC
    c.configure(root=c.R, out=c.OUT, robs=c.DEFAULT_ROBS, nc3=c.NC3)
    st = next(iter(sorted(replay.glob('state_*.json'))), None)
    if st is None:
        return {'ok': False, 'error': f'no state_*.json in {replay}'}
    got = python_in_root(root, F17B_RECOMPUTE, str(Path(root) / K91_EVIDENCE['f17b']), str(T), str(replay),
                         str(dec), str(st))
    per = m.get('per_exit') or {}
    meta_fc = {o: (per.get(o) or {}).get('forecast') for o in K91_EW}
    err_meta = {o: abs(got['replay']['forecast'][o] - meta_fc[o]) if meta_fc[o] is not None else None for o in K91_EW}
    err_j1 = {o: abs(got['replay']['forecast'][o] - got['deploy']['forecast'][o]) for o in K91_EW}
    counts_equal = (got['replay']['current'] == got['deploy']['current']
                    and got['replay']['history'] == got['deploy']['history'])
    held = _ew_splits(root, cap_k)
    applied = all(held[o] is not None and meta_fc[o] is not None and held[o] == float(meta_fc[o]) for o in K91_EW)
    return {'meta_forecast': meta_fc, 'recomputed': got['replay']['forecast'], 'deploy': got['deploy']['forecast'],
            'held_by_lfr': held, 'applied': applied,
            'abs_err_meta': err_meta, 'abs_err_j1': err_j1, 'counts_equal': counts_equal,
            'n_windows': len(got['replay']['windows']), 'candidate': m.get('candidate'),
            'sha_equal': m.get('evidence_sha256') == ev_sha,
            'ok': (all(e is not None and e <= 1e-12 for e in err_meta.values()) and all(e <= 1e-12 for e in err_j1.values())
                   and counts_equal and applied and m.get('candidate') == ev['values']['candidate']
                   and m.get('evidence_sha256') == ev_sha)}


def g3_f17b_fh(root, out, tuning_k, tuning_0, seed=31, T=1650):
    """r2 B-r1-8: sa_capture.py fh --T 1650 --seeds 31 --frames T with SAF-K8b + F17b and with SAF-K8b; the FH frames
    of T = 1650 come from sa_fzp_frames.py --grid 1650 (this output root; VISSIM side, read only) and the x2 ext
    parquet of the judging outputs (<V3>/opt1v2/data, read only)."""
    import sa_capture
    frames = sc.sa_out() / 'fzp' / f's{seed}_frames.parquet'
    if not frames.is_file():
        subprocess.run([sys.executable, '-B', str(HERE / 'sa_fzp_frames.py'), '--root', str(root), '--out', str(out),
                        '--grid', str(T), str(seed)], env=dict(os.environ, PYTHONHASHSEED='0'), check=True,
                       creationflags=c.BELOW_NORMAL)
    data = Path(r'D:/VISSIM-merge/k8_gates_out_v3/opt1v2/data')
    res = {}
    for name, tun in (('k91', tuning_k), ('k8b', tuning_0)):
        tree = f'{Path(out).name}_fh_{name}'
        args = SimpleNamespace(kind='fh', arm='SAF', tree=tree, dry_run=False, robs_seed=sc.ROBS_SEED,
                               fh_disabled=False, gates_stage=None, declaration_sha=None, data=str(data))
        row = dict(harness='FH', T=T, seed=seed, frame_T=T)
        doc = json.loads(Path(tun['path']).read_text(encoding='utf-8-sig'))
        _ensure_history(sc.ROBS_SEED, T, sc.guard_keys_of(doc))
        c.configure(root=c.R, out=c.OUT, robs=c.DEFAULT_ROBS, nc3=c.NC3)
        cap = sc.cap_dir(tree, 'FH', T, 'SAF', seed=seed, frame_T=T)
        if not (cap / 'capture.json').is_file():
            sa_capture.run_capture(args, row, tun)
            log(f'CAP_FH {tree} s{seed} {T} ok={(cap / "capture.json").is_file()}')
        rec = sc.read_json(cap / 'capture.json', {}) or {}
        res[name] = {'ok': rec.get('ok'), 'cap': str(cap),
                     'splits': _ew_splits(root, cap) if rec.get('ok') else None,
                     'transplant_f17b': (rec.get('transplant') or {}).get('f17b'),
                     'k9_f17b': (rec.get('metadata') or {}).get('k9_f17b')}
    k, b = res['k91'], res['k8b']
    equal = (k['splits'] is not None and k['splits'] == b['splits']
             and all(v is not None for v in k['splits'].values()))
    res['ok'] = bool(k['ok'] and b['ok'] and equal and (k['transplant_f17b'] or {}).get('neutralized') is True)
    res['splits_equal'] = equal
    return res


def compare_g4k9(a, b):
    """Section 4.2 G4: every common numeric summary leaf within relative 1e-9 (timing SKIP and the G5 path / name
    exclusions; /k8b0, signal_queue and /k91 compared); one-sided leaves listed."""
    def excl(key):
        k = key.lower()
        return any(s in k for s in SKIP) or any(e.lower() in k for e in G5_EXCLUDE)
    na, sa_ = leaves(a)
    nb, sb_ = leaves(b)
    diffs, near = [], []
    for k in sorted(set(na) & set(nb)):
        if excl(k):
            continue
        x, y = na[k], nb[k]
        if x == y or (math.isnan(x) and math.isnan(y)):
            continue
        rel = abs(x - y) / max(abs(x), abs(y), 1e-300)
        (near if rel <= TOL_REL else diffs).append([k, x, y, rel])
    one_a = sorted(k for k in (set(na) | set(sa_)) - (set(nb) | set(sb_)) if not excl(k))
    one_b = sorted(k for k in (set(nb) | set(sb_)) - (set(na) | set(sa_)) if not excl(k))
    sdiff = [[k, sa_[k][:120], sb_[k][:120]] for k in sorted(set(sa_) & set(sb_)) if not excl(k) and sa_[k] != sb_[k]]
    return {'numeric_common': len(set(na) & set(nb)), 'numeric_differ': len(diffs), 'numeric_near': len(near),
            'examples': diffs[:20], 'near_examples': near[:20], 'one_sided_a': one_a[:20], 'one_sided_b': one_b[:20],
            'n_one_sided': [len(one_a), len(one_b)], 'string_differ_listed': sdiff[:10], 'equal': not diffs}


def g4k9(commit, root, parts):
    """Section 4.2 G4: the commit code with the K9 keys up to the commit (SAF-K8b + parts; Z1-a has no key) at the
    probe H3 states s31 1650 / s31 3300 / s43 1500 / s47 3450 and L2 s47 4800 H27 = the frozen mini-probe arm
    (w1 -> A1, + w2a -> A2, + f17b -> A3; <k9_1_probe>/out/sa/jobs/k91<arm>, A1 L2 from the frozen probe tree run
    k91_g4ref): every common numeric summary leaf within relative 1e-9, else STOP."""
    out = GATES / commit
    setup(root, out)
    parts = tuple(parts)
    arm = K91_ARM[parts]
    tree_k = f'{commit}_g4'
    tuning, doc = keyed_tuning_k9(root, out, parts)
    rows, ok = {}, True
    for seed, T, H in [(s, T, 3) for s, T in G4_H3] + [G4_LONG]:
        _ensure_history(seed, T, sc.guard_keys_of(doc))
        k9_capture(tree_k, seed, T, tuning)
        jd = k9_job(tree_k, seed, T, 'OBS', H, tuning)
        label = sc.job_label('TL3', T, 'SAF', 'OBS', H, seed=seed)
        ref_dir = K91_PROBE / 'out' / 'sa' / 'jobs' / f'k91{arm}' / label
        if arm == 'A1' and H != 3:
            ref_dir = K91_G4_A1_LONG / label
        mine, ref = sc.read_json(jd / 'summary.json', {}) or {}, sc.read_json(ref_dir / 'summary.json')
        if ref is None:
            r = {'ok': False, 'error': f'probe reference missing: {ref_dir}'}
        else:
            r = compare_g4k9(mine, ref)
            r['ref'] = str(ref_dir)
            r['mine_ok'] = mine.get('ok')
            r['objective_repr'] = [mine.get('objective_repr'), ref.get('objective_repr')]
            r['ok'] = bool(mine.get('ok')) and r['equal']
        ok &= r['ok']
        rows[f's{seed}_{T}_H{H}'] = r
    res = {'gate': 'G4', 'parts': list(parts), 'arm': arm, 'commit': commit, 'root': str(root), 'tuning': tuning,
           'verdict': 'PASS' if ok else 'FAIL', 'rows': rows, 'tolerance_rel': TOL_REL,
           'rule': 'amendment 19 r2 section 4.2 G4 (summary numeric leaves, relative 1e-9; else STOP)'}
    write(out / f'gate_G4_{arm}.json', res)
    return res


def g4ref_a1_long():
    """The A1 L2 reference of section 4.2 G4 (the mini-probe ran no A1 long job): the frozen probe tree
    (<k9_1_probe>/tree, its own driver tools/k91_run.py and arm tuning A1) runs capture + H27 of s47 4800 into
    <gates>/k91_g4ref/out (a new folder; the probe folder stays read only).  The A1 tuning bytes must equal the probe's
    (sha 2a0a37d0...)."""
    ref_out = GATES / 'k91_g4ref' / 'out'
    code = (
        'import os, sys, json\n'
        f'sys.path.insert(0, {str(K91_PROBE / "tools")!r})\n'
        'import k91_run as K\n'
        f'K.OUT = __import__("pathlib").Path({str(ref_out)!r})\n'
        'K.LOG = K.OUT / "logs" / "k91_run.log"\n'
        'os.environ["K8G_OUT"] = str(K.OUT)\n'
        'K.setup()\n'
        't = K.tuning_of("A1", write=True)\n'
        'assert t["sha256"].startswith("2a0a37d0"), t\n'
        'K.capture("A1", 47, 4800)\n'
        'K.job("A1", 47, 4800, 27)\n'
        'print(json.dumps(t))\n')
    done = subprocess.run([sys.executable, '-B', '-c', code], cwd=str(K91_PROBE / 'tools'),
                          env=_clean_env(), capture_output=True, text=True, encoding='utf-8', errors='replace',
                          creationflags=c.BELOW_NORMAL)
    p = GATES / 'k91_g4ref' / 'g4ref_a1_long.log'
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(done.stdout + '\n--- stderr ---\n' + done.stderr, encoding='utf-8')
    s = sc.read_json(K91_G4_A1_LONG / 'TL3_4800_s47_SAF_OBS_H27' / 'summary.json') or {}
    res = {'gate': 'G4REF', 'rc': done.returncode, 'ok': bool(s.get('ok')), 'objective_repr': s.get('objective_repr'),
           'summary': str(K91_G4_A1_LONG / 'TL3_4800_s47_SAF_OBS_H27' / 'summary.json'),
           'verdict': 'PASS' if done.returncode == 0 and s.get('ok') else 'FAIL'}
    write(GATES / 'k91_g4ref' / 'g4ref.json', res)
    return res


def armid(commit, root):
    """K9-1-4: sa_arms.py --k91 --source repo of the code root (the section 2.6 arm identity) -> gate_ARMID.json."""
    out = GATES / commit
    setup(root, out)
    done = subprocess.run([sys.executable, '-B', str(HERE / 'sa_arms.py'), '--root', str(root), '--out', str(out),
                           '--source', 'repo', '--k91'], env=dict(os.environ, PYTHONHASHSEED='0'), capture_output=True,
                          text=True, encoding='utf-8', errors='replace', creationflags=c.BELOW_NORMAL)
    arms = sc.read_json(out / 'sa' / 'tuning' / 'arms.json') or {}
    ok = done.returncode == 0 and arms.get('k91') is True and all(
        (arms.get('arms') or {}).get(a, {}).get('k9_keys') in (list(sc.K91_ARM_KEYS), list(sc.K91_ARM_KEYS)
                                                              + [sc.K91_Z1B_KEY]) for a in ('SAF', 'SAG'))
    res = {'gate': 'ARMID', 'commit': commit, 'rc': done.returncode, 'stdout': done.stdout[-1500:],
           'stderr': done.stderr[-1500:], 'arms': {a: {k: r.get(k) for k in ('path', 'sha256', 'k8b_keys', 'k9_keys')}
                                                   for a, r in (arms.get('arms') or {}).items()},
           'verdict': 'PASS' if ok else 'FAIL'}
    write(out / 'gate_ARMID.json', res)
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
    if cmd == 'g5':
        return g5(kv['commit'], kv['base-root'], kv['base-label'], kv['root'], kv['label'])
    if cmd == 'g6':
        return g6(kv['commit'], kv['root'], kv['label'], report_only=bool(kv.get('report-only')))
    if cmd == 'k9units':
        return k9units(kv['commit'], kv['root'], rest)
    if cmd == 'k9build':
        return k9build(kv['commit'], kv['root'], [p for p in str(kv.get('parts') or '').split(',') if p],
                       k91_arms=bool(kv.get('k91-arms')))
    if cmd == 'g5k9':
        return g5k9(kv['commit'], kv['root'], kv['label'])
    if cmd == 'g6k9':
        return g6k9(kv['commit'], kv['root'], kv['label'],
                    parts=tuple(p for p in str(kv.get('parts') or '').split(',') if p and p is not True),
                    z1b=bool(kv.get('z1b')), with_zdiag=not kv.get('no-zdiag'))
    if cmd == 'g3k9':
        return g3k9(kv['commit'], kv['root'], kv['part'])
    if cmd == 'g4k9':
        return g4k9(kv['commit'], kv['root'], tuple(p for p in kv['parts'].split(',') if p))
    if cmd == 'g4ref':
        return g4ref_a1_long()
    if cmd == 'armid':
        return armid(kv['commit'], kv['root'])
    if cmd == 'zdiag':                                       # report only (the G6 part alone)
        out = GATES / kv['commit']
        setup(kv['root'], out)
        res = dict(zdiag(kv['root'], out), gate='ZDIAG', commit=kv['commit'], verdict='REPORT')
        write(out / 'report_zdiag.json', res)
        return res
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
