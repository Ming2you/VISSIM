"""K9-2 bundle 1, amendment 31 (D-K9-58, D-K9-59): (1) the sealed-root k92_record scan again, with the amended s47 rule
of k92t31_judge.py (only _seed47_path differs from k92t30_judge.py), and (2) the jb_unit base check: the 4c unit
selection run once at K8 head b9734abe in a temporary detached worktree, judged against the recorded jb_unit log by
k92t31_unit.py.  Scratch tool in KB/a31decl, never committed; fixed (sha256 in KB/LOG.md and KB/a31_pins.sha256)
before any amendment-31 data.

Writes only: OUT31 = OK2/a31 (records, logs, the base-run root unit_base), OK2/snap/s35-s37, KB/LOG.md (automatic
lines), and the temporary worktree TK/a31_wt_b9734abe (a TK/<name> place of amendment 27 section 2.1) with its git
admin folder (both removed in unit31).
Never writes OUTK (= OK2/k92t: the k92t archive, STOP_a30_post.json and judge/sealed_records.json included), the
sealed root, TREE, GWT8's branch / index / work files, the K8 branch, V4, frozen trees or run folders.  Runs no
VISSIM, COM, runner, freeze or decision replay.  No k92t step of amendment 30 runs again.

    python -B k92t31.py check31 --mode decl|apply --dest D    (read-only pre-check; amendment 31 section 4.1)
    python -B k92t31.py chain31     (check31 apply -> s35 -> scan31 -> s36 -> unit31 -> s37; once; stops at the
                                     first STOP; amendment 31 section 4)
    python -B k92t31.py status31
    detached: powershell -NoProfile -File KI/launch.ps1 -Tag k92t31_chain -Script ..\\a31decl\\k92t31.py
              -ArgLine chain31   (stdout -> OK2/logs/k92t31_chain.txt; this driver prints names, counts, verdicts)
"""
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
KB = HERE.parent
SP = KB.parent.parent
KI = KB / 'impl'
sys.path.insert(0, str(KI))
import k92lib as L  # noqa: E402

PY = L.PY
GWT8 = Path(r'D:/VISSIM-merge/sim3-n31-k8')
REPO_GITDIR = Path(r'D:/VISSIM-merge/repo/.git')
TK = Path(r'D:/VISSIM-merge/k8_gate_trees/k92b1')
TREE = TK / 'a27' / 'k92t'
B9_REF = TK / 'b9_ref'
OK2 = Path(r'D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1')
OUTK = OK2 / 'k92t'
OUT30 = OK2 / 'a30'
OUT31 = OK2 / 'a31'
SEALED = OK2 / 'sealed_s47'
JB = OUTK / 'jb'
CAP = JB / 'sa' / 'cap' / 'k92t'
UNIT_LOG_K92 = JB / 'sa' / 'unit_k92t.log'
UNIT_META_K92 = JB / 'sa' / 'unit_k92t.meta.txt'
WT_NAME = 'a31_wt_b9734abe'
WT = TK / WT_NAME
WT_ADMIN = REPO_GITDIR / 'worktrees' / WT_NAME
UB = OUT31 / 'unit_base'
GIT_DIR_K92 = 'D:/VISSIM-merge/repo/.git/worktrees/sim3-n31-k8'        # the jb_unit GIT_DIR (k92t30.py GIT_DIR)
LOG_MD = KB / 'LOG.md'
JUDGE31 = HERE / 'k92t31_judge.py'
UNIT31 = HERE / 'k92t31_unit.py'
JUDGE30 = KB / 'a30decl' / 'k92t30_judge.py'
JUDGE30_SHA = 'a1937942f06cb7d7e0be400dfc367691e9e6575061ed5aa00cee370f697fe7bf'
A31_DOC = SP / 'K8_PREDECLARATION_AMENDMENT_31.md'
A31_SHA_FILE = SP / 'K8_PREDECLARATION_AMENDMENT_31.md.sha256'
FIXED31 = KB / 'AMENDMENT31_FIXED.md'
A31_PINS = KB / 'a31_pins.sha256'
HEAD = 'e27ceac86c01c1dcfd5b2bb2d9b522be3dc33c0d'
K8 = 'b9734abe1c83f95c9cec5fca5e42b7b18cd45991'
BRANCH = 'claude/k92-b1-20261016'
K8_BRANCH = 'claude/k8-sc1001eb-defects-20261004'
N_K92_COMMITS = 6
A = {24: 'd46db6dc3959b19525f0fce77ead5432682e3de0ef8060cdc3da09661559aadc',
     25: '4fd7b599fe0f6131143e911dd3ab2be264a175e3f90b185bade9482d60b9ff8e',
     26: '8f8356168a299c07960d86ef12aa9f7af6f2f040af08ba75e5233a5819edba37',
     27: '4ce8b27a2ebf08aa0e8ac3f647b4e4336a98f7be7ec8d6f006a0fd1d12005a13',
     28: '9881eb40c1129af0cdff48026dc8656b4235d43f0eb80566e4be9b66d9ac345e',
     29: '4bd6dc8de8b0a4a4ab0b8703c07d7a73d244c4a622b81585f06dc69d6d83599d',
     30: 'ba556227a6356b1733bfa8125b334cfef180c1eed97e8d69ae4ba53a3106a56a'}
FIXED = {24: 'fbc3d59fe2e47fec00d87262d624aa9a163ed02e113609b06173841397df101a',
         25: 'd1338fbc40a2efaf6997667f59e7bd709951e1fd3f2b1a8a0a0881794c3d24ed',
         26: '6edc55acd5aa0976701456d956e33f33c52ae0853535f6a4d8cb8bf26a354581',
         27: '394ab15fdea0d945a3b766c208e692ee7e1086fca3c178f6b423079d71fedcdb',
         28: '14451cf4d46c5c0095bc896134112148ba5700ee70b2ed78b8ee38d0e62e20e5',
         29: '3ba1d0bdaab8a0189f903d10fc1024baed770080542cbd841f79d3a56df58e43',
         30: 'ad3fafadd59985b3b71f33d5523ceb2324aa8267395d7280039228669cb83e9c'}
NOTES = SP / 'K9_1_J1_NOTES_20261013.md'
NOTES_N = 193
NOTES_SHA = '09974cfc3e1412735ba6cf3228f4a2e4c08ad01294327d534290011b4a8042cc'
PINS_K92T = (KB / 'k92t_pins.sha256', '38a2ce147795bbe7613fa5b6633441b31b814e781d1948e550753db776ed7cdd', 56)
PINS_A30 = (KB / 'a30_pins.sha256', '7afabd03f315c8925c4a8bb1b1566d246cbfb9273470876963df9e7fe4f3d30e', 83)
# the k92t archive the amendment keeps (OUTK-relative path -> sha256; amendment 31 section 4.1 C7)
RECORDED31 = {
    'STOP_f.json': 'ebff59c96596baca6039647e3902b88881a45fe6227b7da438e99afe420d3f17',
    'STOP_a30_post.json': '8fa7524342517c020715aa26757f38a54473cdcf30cdd1d18d9b5414dcf8e18e',
    'k92_judging_stage.json': '34e63a991451ef8c3f1be0ef6f4765f009abc19745fe7e546ffaeda43fd1aaa5',
    'start/scans.json': '410fde88da1e97e0434d3df59f292a904ed87c153a17bb209ec918b7a074bfb8',
    'stages/start.json': 'f3ed1dcea6f86b6c750368e9b5b2082331a9c85f18d435b9eac6af46744eef13',
    'stages/prep.json': '9ef3a7edd7e5a7c1d5938161c27c1f1bde5394da84d7cc61181876d78cfbc533',
    'stages/j0.json': '3845def6bbc0d95935fac27f36a24b13a5938d111aa11f1f7d93548f3f216631',
    'stages/ja.json': 'b40593bb34f45074546d58c808912ee4cffa6ff95dd0b5d3ac3543c89368b03c',
    'stages/seal30.json': '3084d2bdb4eaf57910cc2d5dceeee4ff37cd21549bff79c2bc481bb6744f2b12',
    'stages/f.json': '6f9818e8fa4eef4860aebe40793adb153f7177b5cfab6b4c312d57a708855d33',
    'stages/jb.json': '57bdfa181841d0d2925cf2a229fc3df2e07e8692d5ef5891d2975577ccd106fc',
    'judge/j0.json': '24ee9d3b66d16618f9c6bc255bcabaecbcbaa2a653c985a9fb0315d68a85aab1',
    'judge/ja.json': '74806cb0683582bc20eccb68eb086363a0ac0e8d100d2c6c5d48436da14b4d5c',
    'judge/jwall.json': '1fb5c60454169b9f10014691a9fae9aa4697ac5bd26323e146149b6600fb615a',
    'judge/f_jobs.json': '26959c474c9cc0ec0b107c4d38aa260cb2f123d0b6b8094ea18ed77d90fb0666',
    'judge/f.json': '04cfa2e0a9ac754bd13d5c5ca2d4cd5790acb34fda64fafdce7f7382027ac792',
    'judge/jb.json': 'f8a273ef9b6e2f02f539b4193a39d35516959d8799e3cd89a2b060c006faa200',
    'judge/sealed_records.json': '517582ad15adc98d936199cc9d4c1e9e9c9cc6bbc3d359722b4d7a06941d6eb5',
    'f_vref/sa/k92_vissim_ref.json': '09f9194b308703db4d1da87cc10e458fca85872fd1189ef5fda7b2bc8f3b601a',
    'f_persist30/sa/k92_vissim_ref.json': '8fc0e979e28130fb446be6c2ce7b5ec5f7eac9ed1eba5e94d94ad7357c2afa0b',
    'jb_copies.json': 'ba598ee3d959885fc2569266fe01c01343d0e82bb613de50c068e7c247a542a6',
    'jb/sa/gates/gates_k92t.json': '4b0cf22ea96fdd09f57320e3130fea2a3078676015a1008631ad14d82560fdfb',
    'jb/sa/unit_k92t.log': 'ef8033f54eb342c3431cdf2f756bce6ecaaab3832e90babff6150136466dc3eb',
    'jb/sa/unit_k92t.meta.txt': 'e235e0ad2e8eb1997a29b674fc1834bd3e80f0754943a362b3d51a1e0072afdf',
    'steps.jsonl': '1fdef90665711ac849a6a09cff933b5392acc196d452a95364073bde08609123',
    'driver.log': 'a7ae60589baf3c40ea04702dd97043ab28ff6a56166ad3104b57dc5b2b5102de'}
OTHER31 = {OUT30 / 'check30.json': 'f5b35a857edc293b733d22b33e52f1aad4ebb5f8feabb9f38427972da90a4df9',
           OUT30 / 'sealed_k92t_index.json': '3946b3fcb2104ac5ca6a52a847e80fd6a04cccdfd7783c8e1f47cde08f47ce0a',
           OK2 / 'logs' / 'k92t30_chain.txt': '7b734c3c47ac898b5db9045891f127112b8e4c773d00ee1cc9cb23e47629646e'}
STOPS_NOW = ['STOP_a30_post.json', 'STOP_f.json']
STAGES_NOW = sorted('%s.json' % s for s in ('start', 'prep', 'j0', 'ja', 'seal30', 'f', 'jb'))
JUDGES_NOW = sorted('%s.json' % s for s in ('j0', 'ja', 'jwall', 'f_jobs', 'f', 'jb', 'sealed_records'))
STEPS_N = 102
JF_SHA = ('04cfa2e0a9ac754bd13d5c5ca2d4cd5790acb34fda64fafdce7f7382027ac792',
          'f8a273ef9b6e2f02f539b4193a39d35516959d8799e3cd89a2b060c006faa200')
SEALED_TOPS = ['K9-2-0', 'K9-2-1', 'K9-2-2', 'K9-2-3', 'a27', 'k92t']
SEALED_K92T_LOGS = {'f_f_b1_jobs.log': 4971, 'f_f_off_jobs.log': 4996, 'f_f_w_jobs.log': 4936}
SCAN_OUT = OUT31 / 'sealed_records_a31.json'
SCAN_EXPECT = {'files': 134, 's47': 45, 'bad': 0, 'ran': True}
N31_TESTS = 'diagnostics/sdmpc_n31_20260924/tests/'
UNIT_FILES = ['test_stopline_approach.py', 'test_stopline_wiring.py', 'test_stopline_evidence.py',
              'test_stopline_approach_captured.py']
RUN_PYTEST_BN = SP / 'k8b_impl' / 'run_pytest_bn.py'
RUN_PYTEST_BN_SHA = 'fe4451e431a74e7653c5f064e7f2331f17ca9302148da86e51eb4e81c033489e'
TREE_BUILD_SHA = 'a1e98fa72f787c17f576f9c2de2ed479709849e4880b962624a31d28b892b0d8'
PYTEST_TIMEOUT = 1800            # s; the recorded jb_unit run took 107.2 s (steps.jsonl)
UNIT_LOG_BASE = UB / 'unit_b9734abe.log'
UNIT_JUDGE_OUT = OUT31 / 'unit_judge.json'
SNAPS31 = ('s35_a31_check', 's36_a31_scan', 's37_a31_unit')
ORDER31 = ('check31', 'scan31', 'unit31')


# ------------------------------------------------------------------------------------------------ helpers
def now():
    return time.strftime('%Y-%m-%d %H:%M:%S')


def log(msg):
    line = '%s %s' % (now(), msg)
    print(line, flush=True)
    if OUT31.is_dir():
        with open(OUT31 / 'driver31.log', 'a', encoding='utf-8', newline='\n') as f:
            f.write(line + '\n')


def log_md(text):
    """Automatic LOG.md line (verdicts, counts, names and sha only)."""
    with open(LOG_MD, 'a', encoding='utf-8', newline='\n') as f:
        f.write('- [%s +0900] %s\n' % (now(), text))


def sha(p):
    return L.sha256_file(p)


def read(p, default=None):
    return L.read_json(p, default)


def wjson(p, obj):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(p) + '.tmp')
    with open(tmp, 'w', encoding='utf-8', newline='\n') as f:
        f.write(json.dumps(obj, indent=1, sort_keys=True, default=str, ensure_ascii=False) + '\n')
    os.replace(tmp, p)


def git(*args, at=None):
    """git -C <at> (default: GWT8, read at call time); (rc, stdout, stderr)."""
    at = GWT8 if at is None else at
    done = subprocess.run(['git', '--no-optional-locks', '-C', str(at)] + [str(a) for a in args], capture_output=True,
                          text=True, encoding='utf-8', errors='replace')
    return done.returncode, done.stdout.strip(), done.stderr.strip()


def gout(*args, at=None):
    return git(*args, at=at)[1]


def worktree_paths():
    rc, out, _ = git('worktree', 'list', '--porcelain')
    return [ln[len('worktree '):].strip().replace('\\', '/').lower() for ln in out.splitlines()
            if ln.startswith('worktree ')]


def wt_listed():
    return str(WT).replace('\\', '/').lower() in worktree_paths()


def a31_sha():
    """Amendment 31 fixed: sha256(file) = its .sha256 = a 64-hex word in KB/AMENDMENT31_FIXED.md."""
    if not (A31_DOC.is_file() and A31_SHA_FILE.is_file() and FIXED31.is_file()):
        raise SystemExit('amendment 31 / .sha256 / fixation file missing')
    s = sha(A31_DOC)
    rec = A31_SHA_FILE.read_text(encoding='utf-8').split()[0]
    fixed = FIXED31.read_text(encoding='utf-8')
    if s != rec or not re.search(r'(?<![0-9a-f])%s(?![0-9a-f])' % s, fixed):
        raise SystemExit('amendment 31 is not the fixed text (sha %s, .sha256 %s)' % (s[:16], rec[:16]))
    return s


def pins_check(path):
    """sha256sum -c of a pin list ('<sha> *<abs path>' lines); returns (n_lines, bad_lines, sha of the list)."""
    if not Path(path).is_file():
        return 0, ['list missing'], None
    lines = [ln for ln in Path(path).read_text(encoding='utf-8').splitlines() if ln.strip()]
    bad = []
    for ln in lines:
        want, _, p = ln.partition(' *')
        if not Path(p).is_file() or sha(p) != want:
            bad.append(p)
    return len(lines), bad, sha(path)


def stop(stage, why, extra=None):
    """OUT31/STOP_a31_<stage>.json (names / counts / sha only); the k92t archive in OUTK is never written."""
    rec = {'stage': stage, 'why': why, 'when': now(), 'extra': extra, 'driver': 'k92t31'}
    OUT31.mkdir(parents=True, exist_ok=True)
    wjson(OUT31 / ('STOP_a31_%s.json' % stage), rec)
    log('STOP %s: %s' % (stage, why))
    log_md('k92t31 구동기: STOP — 단계 %s, 까닭 %s (k92t31.py, 자동 기록)' % (stage, why))
    raise SystemExit(3)


def finish(stage, rec):
    rec = dict(rec, stage=stage, when=now(), ok=True, driver='k92t31', driver_sha256=sha(Path(__file__)),
               judge31_sha256=sha(JUDGE31), unit31_sha256=sha(UNIT31), amendment31_sha256=sha(A31_DOC))
    wjson(OUT31 / 'stages' / ('%s.json' % stage), rec)
    log('STAGE_DONE %s' % stage)


def require_prev(stage):
    """Amendment 31 section 4: check31 -> scan31 -> unit31, each needing the records of the ones before it."""
    i = ORDER31.index(stage)
    for prev in ORDER31[:i]:
        r = read(OUT31 / 'stages' / ('%s.json' % prev), {}) or {}
        if not r.get('ok') or r.get('driver') != 'k92t31' or r.get('amendment31_sha256') != sha(A31_DOC):
            raise SystemExit('stage %s needs %s first (amendment 31)' % (stage, prev))
    stops = sorted(p.name for p in OUT31.glob('STOP_*.json')) if OUT31.is_dir() else []
    if stops:
        raise SystemExit('an amendment-31 STOP file exists: %s (the user decides)' % stops)


def space():
    fs = L.free_space_gb()
    if any(v < 8.0 for v in fs.values()):
        stop('space', 'LOW_SPACE %s' % fs)
    return fs


def child(name, argv, cwd, env=None, logp=None, timeout=None):
    """One child, BELOW_NORMAL, stdout+stderr to a log file (never echoed); a record in OUT31/steps31.jsonl.
    rc None = the timeout passed and the child was stopped (only the base pytest run has a timeout)."""
    space()
    logp = Path(logp or (OUT31 / 'logs' / ('%s.log' % name)))
    if logp.exists():
        stop(name, 'log exists (never reused): %s' % logp)
    logp.parent.mkdir(parents=True, exist_ok=True)
    pre = L.vissim_count()
    t0 = time.time()
    if env is None:
        env = dict(os.environ, PYTHONHASHSEED='0', PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1')
    with open(logp, 'w', encoding='utf-8', errors='replace') as f:
        try:
            rc = subprocess.run([str(a) for a in argv], cwd=str(cwd), env=env, stdout=f, stderr=subprocess.STDOUT,
                                creationflags=L.BELOW_NORMAL, timeout=timeout).returncode
        except subprocess.TimeoutExpired:
            rc = None
    post = L.vissim_count()
    rec = {'name': name, 'rc': rc, 'start': t0, 'sec': round(time.time() - t0, 1), 'log': str(logp),
           'vissim_before': pre, 'vissim_after': post}
    with open(OUT31 / 'steps31.jsonl', 'a', encoding='utf-8', newline='\n') as f:
        f.write(json.dumps(rec) + '\n')
    log('STEP %s rc=%s sec=%s' % (name, rc, rec['sec']))
    if any(isinstance(c, int) and c > 0 for c in (pre, post)):
        stop(name, 'VISSIM count before / after = %s / %s (amendment 31: VISSIM 0)' % (pre, post))
    return rc


def snap(name):
    """Read-only roots snapshot (KI/k92snap.py, metadata only) compared with s02; different -> STOP (S-K11)."""
    p = OK2 / 'snap' / ('%s.json' % name)
    if p.exists():
        stop('snap', 'snapshot %s exists (never reused)' % name)
    rc = child('snap_' + name, [PY, '-B', KI / 'k92snap.py', 'take', p], cwd=KI)
    rc2 = child('snapdiff_' + name, [PY, '-B', KI / 'k92snap.py', 'diff', OK2 / 'snap' / 's02_after_probe_stop.json',
                                     p], cwd=KI)
    log_md('k92t31 구동기: 읽기 전용 뿌리 스냅숏 `OK2/snap/%s.json` sha256 `%s`, s02 대비 %s (자동 기록)' % (
        name, sha(p) if p.is_file() else None, 'SAME' if rc2 == 0 else 'DIFFERENT'))
    if rc != 0 or rc2 != 0:
        stop('snap', 'snapshot %s rc=%s diff rc=%s (S-K11)' % (name, rc, rc2))


def jf_fixed():
    text = LOG_MD.read_text(encoding='utf-8')
    return all(s in text for s in JF_SHA) and all(sha(OUTK / 'judge' / n) == s
                                                   for n, s in zip(('f.json', 'jb.json'), JF_SHA))


def jb_unit_rc():
    """The recorded jb_unit exit code: the one steps.jsonl line named jb_unit (names / rc only)."""
    rows = [json.loads(ln) for ln in (OUTK / 'steps.jsonl').read_text(encoding='utf-8').splitlines() if ln.strip()]
    hits = [r for r in rows if r.get('name') == 'jb_unit']
    return hits[0].get('rc') if len(hits) == 1 else None


def selection_at(rev):
    """The 4c unit selection restricted to the files that exist at rev (git cat-file -e)."""
    return [N31_TESTS + f for f in UNIT_FILES if git('cat-file', '-e', '%s:%s%s' % (rev, N31_TESTS, f))[0] == 0]


# ================================================================================================ check31
def stage_check31(mode, dest):
    """Amendment 31 section 4.1: read-only pre-check (closed list C1-C15).  mode decl = before amendment 31 is fixed
    (C2 / C6 reported only); apply = every check binding."""
    chk, info = {}, {}
    for n in A:
        doc = SP / ('K8_PREDECLARATION_AMENDMENT_%d.md' % n)
        chk['C1_a%d' % n] = sha(doc) == A[n] and (SP / ('K8_PREDECLARATION_AMENDMENT_%d.md.sha256' % n)).read_text(
            encoding='utf-8').split()[0] == A[n]
        chk['C1_fixed%d' % n] = sha(KB / ('AMENDMENT%d_FIXED.md' % n)) == FIXED[n]
    if mode == 'apply':
        try:
            info['a31_sha256'] = a31_sha()
            chk['C2_a31_fixed'] = True
        except SystemExit as exc:
            info['a31_problem'] = str(exc)
            chk['C2_a31_fixed'] = False
    else:
        info['C2_a31'] = {'doc': A31_DOC.is_file(), 'sha_file': A31_SHA_FILE.is_file(), 'fixation': FIXED31.is_file()}
    lines = NOTES.read_bytes().splitlines(keepends=True)
    chk['C3_notes'] = len(lines) >= NOTES_N and L.sha256_bytes(b''.join(lines[:NOTES_N])) == NOTES_SHA
    chk['C4_head'] = gout('rev-parse', 'HEAD') == HEAD
    chk['C4_branch'] = gout('rev-parse', '--abbrev-ref', 'HEAD') == BRANCH
    chk['C4_k8_branch'] = gout('rev-parse', K8_BRANCH) == K8
    chk['C4_status_clean'] = gout('status', '--porcelain') == ''
    chk['C4_commits'] = gout('rev-list', '--count', '%s..HEAD' % K8) == str(N_K92_COMMITS)
    chk['C4_no_remote_k92'] = 'k92' not in gout('for-each-ref', '--format=%(refname)', 'refs/remotes')
    for key, (path, want, n_want) in (('C5_k92t_pins', PINS_K92T), ('C5_a30_pins', PINS_A30)):
        n, bad, s = pins_check(path)
        chk[key] = s == want and n == n_want and not bad
        info[key] = {'n': n, 'bad': bad[:10], 'sha256': s}
    if mode == 'apply':
        n, bad, s = pins_check(A31_PINS)
        listed = A31_PINS.read_text(encoding='utf-8') if A31_PINS.is_file() else ''
        mine = ['%s *%s' % (sha(p), str(p).replace('\\', '/')) for p in (Path(__file__).resolve(), JUDGE31, UNIT31)]
        chk['C6_a31_pins'] = (s is not None and not bad and all(m in listed for m in mine)
                              and re.search(r'(?<![0-9a-f])%s(?![0-9a-f])' % s, FIXED31.read_text(encoding='utf-8'))
                              is not None)
        info['C6'] = {'n': n, 'bad': bad[:10], 'sha256': s}
    chk['C7_recorded'] = all((OUTK / rel).is_file() and sha(OUTK / rel) == want for rel, want in RECORDED31.items())
    info['C7_recorded_bad'] = [rel for rel, want in RECORDED31.items()
                               if not (OUTK / rel).is_file() or sha(OUTK / rel) != want]
    chk['C7_other'] = all(Path(p).is_file() and sha(p) == want for p, want in OTHER31.items())
    chk['C7_stop_files'] = sorted(p.name for p in OUTK.glob('STOP_*.json')) == STOPS_NOW
    chk['C7_stage_records'] = sorted(p.name for p in (OUTK / 'stages').iterdir()) == STAGES_NOW
    chk['C7_judge_files'] = sorted(p.name for p in (OUTK / 'judge').iterdir()) == JUDGES_NOW
    chk['C7_steps_lines'] = len((OUTK / 'steps.jsonl').read_bytes().splitlines()) == STEPS_N
    chk['C8_jf_fixed'] = jf_fixed()
    tops = sorted(p.name for p in SEALED.iterdir()) if SEALED.is_dir() else []
    chk['C9_sealed_tops'] = tops == SEALED_TOPS
    logs = SEALED / 'k92t' / 'logs'
    names = sorted(p.name for p in logs.iterdir()) if logs.is_dir() else []
    chk['C9_sealed_k92t_logs'] = names == sorted(SEALED_K92T_LOGS) and all(
        os.path.getsize(logs / k) == v for k, v in SEALED_K92T_LOGS.items())
    chk['C10_out31_absent'] = not OUT31.exists()
    chk['C10_wt_absent'] = not WT.exists() and not WT_ADMIN.exists() and not wt_listed()
    sel = selection_at(K8)
    info['C11_selection_b9734abe'] = sel
    chk['C11_selection'] = sel == [N31_TESTS + f for f in UNIT_FILES]
    info['C11_blobs_equal'] = {f: gout('rev-parse', '%s:%s%s' % (K8, N31_TESTS, f)) ==
                               gout('rev-parse', '%s:%s%s' % (HEAD, N31_TESTS, f)) for f in UNIT_FILES}
    chk['C12_tree_build'] = sha(TK / 'a27' / 'k92t.build.json') == TREE_BUILD_SHA and TREE.is_dir()
    chk['C12_run_pytest_bn'] = sha(RUN_PYTEST_BN) == RUN_PYTEST_BN_SHA
    chk['C12_judge30_copy'] = sha(JUDGE30) == JUDGE30_SHA and sha(HERE / 'base' / 'k92t30_judge.py') == JUDGE30_SHA
    chk['C12_jb_unit_rc'] = jb_unit_rc() == 1
    chk['C12_cap_root'] = CAP.is_dir()
    cen = L.census()
    chk['C13_vissim_0'] = cen['vissim_any'] == 0
    chk['C13_foreign_0'] = not cen['foreign_runner_or_replay']
    fs = L.free_space_gb()
    chk['C14_space'] = all(v >= 8.0 for v in fs.values())
    info.update(census=cen['counts'], free_gb=fs)
    rec = {'schema': 'k92t31-check31/v1', 'mode': mode, 'when': now(), 'checks': chk, 'info': info,
           'driver_sha256': sha(Path(__file__)), 'judge31_sha256': sha(JUDGE31), 'unit31_sha256': sha(UNIT31),
           'ok': all(chk.values())}
    wjson(dest, rec)
    print('K92T31_CHECK31 mode=%s ok=%s bad=%s' % (mode, rec['ok'], [k for k, v in chk.items() if not v]))
    return rec


# ================================================================================================ scan31
def stage_scan31():
    """Amendment 31 section 2 (D-K9-58): the sealed-root k92_record scan with the amended _seed47_path, once."""
    a31_sha()
    require_prev('scan31')
    if not jf_fixed():
        stop('scan31', 'the J / F judge sha are not in the LOG or the files changed (amendment 30 section 4.5)')
    if SCAN_OUT.exists():
        stop('scan31', 'output exists (never reused): %s' % SCAN_OUT)
    log_md('k92t31 구동기: 봉인 열람 기록(보충 25 §6.4, 보충 31 §2.4) — 파일 = `OK2/sealed_s47/**/k92_record.json`의 '
           'seed·vissim·vissim_reason 칸(판정기 메모리 안), 목적 = 보충 31 봉인 뿌리 기록 훑기(D-K9-58), 출력 = 개수·참거짓·'
           '경로만 (자동 기록)')
    rc = child('scan31', [PY, '-B', JUDGE31, 'sealedscan', '--dest', SCAN_OUT], cwd=HERE)
    res = read(SCAN_OUT, {}) or {}
    counts = res.get('sealed_records')
    archive_same = all(sha(OUTK / rel) == RECORDED31[rel] for rel in ('STOP_a30_post.json',
                                                                      'judge/sealed_records.json'))
    verdict = 'PASS' if (rc == 0 and res.get('ok') is True and res.get('n_bad') == 0 and counts == SCAN_EXPECT
                         and archive_same) else 'STOP'
    rec = {'verdict': verdict, 'rc': rc, 'ok': res.get('ok'), 'n_bad': res.get('n_bad'), 'counts': counts,
           'expected_counts': SCAN_EXPECT, 'archive_unchanged': archive_same,
           'output': str(SCAN_OUT), 'output_sha256': sha(SCAN_OUT) if SCAN_OUT.is_file() else None}
    wjson(OUT31 / 'scan31.json', rec)
    log_md('k92t31 구동기: 보충 31 봉인 뿌리 기록 훑기 %s (rc %s, ok %s, %s, 기대 %s, 보관 파일 그대로 %s), '
           '`OK2/a31/sealed_records_a31.json` sha256 `%s` (자동 기록)' % (
               verdict, rc, res.get('ok'), counts, SCAN_EXPECT, archive_same, rec['output_sha256']))
    if verdict != 'PASS':
        stop('scan31', 'sealed-root record scan not PASS (S-K10, S-K46)', {k: rec[k] for k in ('rc', 'ok', 'counts')})
    finish('scan31', rec)
    return rec


# ================================================================================================ unit31
def base_env():
    """The jb_unit environment (k92t30.py stage_jb + env_for) with the tree-bound values moved to the base side."""
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith(('RW_', 'K8_', 'K8G_', 'K92A_'))}
    env.update(PYTHONHASHSEED='0', PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1', K8G_ROOT=str(WT), K8G_OUT=str(UB))
    env.update(K8_SA_CAPTURE_ROOT=str(CAP), K8_SA_BASE_REV='ec063ffa', NUMBA_NUM_THREADS='1',
               GIT_DIR=gout('rev-parse', '--absolute-git-dir', at=WT), TMP=str(UB / 'tmp'), TEMP=str(UB / 'tmp'))
    return env


def gwt8_state():
    return {'head': gout('rev-parse', 'HEAD'), 'branch': gout('rev-parse', '--abbrev-ref', 'HEAD'),
            'k8': gout('rev-parse', K8_BRANCH), 'status_lines': len(gout('status', '--porcelain').splitlines())}


def stage_unit31():
    """Amendment 31 section 3 (D-K9-59): base results at b9734abe (temporary detached worktree, removed here), then
    the k92t31_unit.py judge against the recorded jb_unit log."""
    a31_sha()
    require_prev('unit31')
    want_state = {'head': HEAD, 'branch': BRANCH, 'k8': K8, 'status_lines': 0}
    if gwt8_state() != want_state:
        stop('unit31', 'GWT8 / K8 state differs before the worktree (S-K48)', gwt8_state())
    if WT.exists() or WT_ADMIN.exists() or wt_listed():
        stop('unit31', 'the temporary worktree path or admin folder exists (S-K48)')
    sel = selection_at(K8)
    if sel != [N31_TESTS + f for f in UNIT_FILES]:
        stop('unit31', 'selection at b9734abe differs from the 4 files (S-K47)', sel)
    new_rc = jb_unit_rc()
    rec = {'wt': str(WT), 'wt_admin': str(WT_ADMIN), 'selection': sel, 'new_rc': new_rc}
    WT.parent.mkdir(parents=True, exist_ok=True)
    UB.mkdir(parents=True, exist_ok=True)
    (UB / 'tmp').mkdir(parents=True, exist_ok=True)
    removed = None
    try:
        rc_add = child('unit31_wt_add', ['git', '-C', GWT8, 'worktree', 'add', '--detach', str(WT).replace('\\', '/'),
                                         K8], cwd=KI)
        rec['wt_add_rc'] = rc_add
        if rc_add != 0:
            raise RuntimeError('git worktree add rc=%s' % rc_add)
        rec['wt_head'] = gout('rev-parse', 'HEAD', at=WT)
        rec['wt_status_lines_before'] = len(gout('status', '--porcelain', at=WT).splitlines())
        rec['wt_git_dir'] = gout('rev-parse', '--absolute-git-dir', at=WT)
        if rec['wt_head'] != K8 or rec['wt_status_lines_before'] != 0:
            raise RuntimeError('worktree head %s / status lines %s' % (rec['wt_head'], rec['wt_status_lines_before']))
        if gwt8_state() != want_state:
            raise RuntimeError('GWT8 / K8 state changed by the worktree add')
        # report only: worktree bytes against the archive tree of b9734abe (TK/b9_ref), caches and '.git' left out
        try:
            d = L.tree_diff(WT, B9_REF)
            rec['report_wt_vs_b9_ref'] = {'n_changed': len(d['changed']), 'changed': d['changed'][:20],
                                          'only_wt': [p for p in d['only_a'] if p != '.git'][:20],
                                          'n_only_wt': len([p for p in d['only_a'] if p != '.git']),
                                          'only_b9_ref': d['only_b'][:20], 'n_only_b9_ref': len(d['only_b']),
                                          'b9_ref_build_sha256': sha(TK / 'b9_ref.build.json')}
        except Exception as exc:  # noqa: BLE001  (a report item never stops the run)
            rec['report_wt_vs_b9_ref'] = {'error': '%s: %s' % (type(exc).__name__, exc)}
        env = base_env()
        rec['env'] = {k: env[k] for k in ('K8G_ROOT', 'K8G_OUT', 'K8_SA_CAPTURE_ROOT', 'K8_SA_BASE_REV',
                                          'NUMBA_NUM_THREADS', 'GIT_DIR', 'TMP', 'TEMP', 'PYTHONHASHSEED',
                                          'PYTHONDONTWRITEBYTECODE', 'PYTHONUTF8')}
        argv = [PY, '-B', RUN_PYTEST_BN, '-v'] + sel
        rec['argv'] = [str(a) for a in argv]
        rc = child('unit31_pytest', argv, cwd=WT, env=env, logp=UNIT_LOG_BASE, timeout=PYTEST_TIMEOUT)
        rec['base_rc'] = rc
        if rc is None:
            raise RuntimeError('base pytest run exceeded %s s and was stopped' % PYTEST_TIMEOUT)
        (UB / 'unit_b9734abe.meta.txt').write_text(
            'ROOT %s (git worktree --detach %s) GIT_DIR=%s\nK8_SA_CAPTURE_ROOT=%s K8_SA_BASE_REV=ec063ffa '
            'NUMBA_NUM_THREADS=1 TMP=TEMP=%s K8G_OUT=%s K8G_ROOT=%s\nCMD python -B run_pytest_bn.py -v %s\nrc=%s\n' % (
                WT, K8[:8], env['GIT_DIR'], CAP, UB / 'tmp', UB, WT, ' '.join(sel), rc), encoding='utf-8')
        st = gout('status', '--porcelain', '--untracked-files=all', at=WT).splitlines()
        rec['report_wt_status_after'] = {'n': len(st), 'first': st[:20]}
    except RuntimeError as exc:
        rec['problem'] = str(exc)
    finally:
        if WT.exists() or wt_listed():
            rc_rm = child('unit31_wt_remove', ['git', '-C', GWT8, 'worktree', 'remove', '--force',
                                               str(WT).replace('\\', '/')], cwd=KI)
            rec['wt_remove_rc'] = rc_rm
        removed = (not WT.exists()) and (not WT_ADMIN.exists()) and (not wt_listed()) and gwt8_state() == want_state
        rec['wt_removed_and_state_same'] = removed
        rec['gwt8_state_after'] = gwt8_state()
        wjson(OUT31 / 'unit31_run.json', rec)
    if 'problem' in rec:
        stop('unit31', 'base run not made: %s (S-K47 / S-K48)' % rec['problem'])
    if not removed:
        stop('unit31', 'temporary worktree not removed or GWT8 / K8 state changed (S-K48)', rec['gwt8_state_after'])
    roots = [str(WT), str(TREE), str(UB), str(JB), str(CAP), rec['wt_git_dir'], GIT_DIR_K92]
    rcj = child('unit31_judge', [PY, '-B', UNIT31, 'judge', '--base', UNIT_LOG_BASE, '--new', UNIT_LOG_K92,
                                 '--base-root', WT, '--new-root', TREE, '--base-rc', rec['base_rc'],
                                 '--new-rc', new_rc, '--roots', json.dumps(roots), '--files', json.dumps(sel),
                                 '--dest', UNIT_JUDGE_OUT], cwd=HERE)
    res = read(UNIT_JUDGE_OUT, {}) or {}
    verdict = res.get('verdict') if rcj in (0, 3, 4) else 'INCOMPLETE'
    out = {'verdict': verdict, 'judge_rc': rcj, 'judge_out': str(UNIT_JUDGE_OUT),
           'judge_out_sha256': sha(UNIT_JUDGE_OUT) if UNIT_JUDGE_OUT.is_file() else None,
           'base_log_sha256': sha(UNIT_LOG_BASE) if UNIT_LOG_BASE.is_file() else None,
           'new_log_sha256': sha(UNIT_LOG_K92), 'base_rc': rec['base_rc'], 'new_rc': new_rc,
           'n_common': res.get('n_common'), 'n_differ': res.get('n_differ'), 'only_base': res.get('only_base'),
           'only_new': res.get('only_new'), 'n_non_passed_common': res.get('n_non_passed_common'),
           'run_record_sha256': sha(OUT31 / 'unit31_run.json')}
    wjson(OUT31 / 'unit31.json', out)
    log_md('k92t31 구동기: jb_unit 기준 대조(b9734abe 임시 작업 트리, 지움 %s) %s (기준 rc %s, K9-2 rc %s, 공통 %s, '
           '다름 %s, 기준만 %s, K9-2만 %s, 통과 아닌 공통 %s), `OK2/a31/unit_judge.json` sha256 `%s` (자동 기록)' % (
               removed, verdict, rec['base_rc'], new_rc, res.get('n_common'), res.get('n_differ'),
               len(res.get('only_base') or []), len(res.get('only_new') or []), res.get('n_non_passed_common'),
               out['judge_out_sha256']))
    if verdict != 'PASS':
        stop('unit31', 'jb_unit rule not PASS: %s (S-K47)' % verdict)
    finish('unit31', out)
    return out


# ================================================================================================ chain
def chain31():
    """Once: check31 apply -> s35 -> scan31 -> s36 -> unit31 -> s37."""
    a31_sha()
    if OUT31.exists():
        raise SystemExit('chain31 runs once; OUT31 exists (the user decides)')
    rec = stage_check31('apply', OUT31 / 'check31.json')         # C10 sees OUT31 absent; wjson then creates it
    log_md('k92t31 구동기: 사전 점검 ok=%s, `OK2/a31/check31.json` sha256 `%s` (자동 기록)' % (
        rec['ok'], sha(OUT31 / 'check31.json')))
    if not rec['ok']:
        stop('check31', 'pre-check false (S-K49)', [k for k, v in rec['checks'].items() if not v])
    finish('check31', {'check31_sha256': sha(OUT31 / 'check31.json')})
    snap(SNAPS31[0])
    stage_scan31()
    snap(SNAPS31[1])
    stage_unit31()
    snap(SNAPS31[2])
    out = {'scan31': read(OUT31 / 'scan31.json'), 'unit31': read(OUT31 / 'unit31.json'), 'when': now(),
           'driver_sha256': sha(Path(__file__)), 'amendment31_sha256': sha(A31_DOC)}
    wjson(OUT31 / 'chain31.json', out)
    log('CHAIN31_DONE')
    log_md('k92t31 구동기: 사슬 끝 — check31·scan31·unit31 모두 PASS, `OK2/a31/chain31.json` sha256 `%s` (자동 기록)' % (
        sha(OUT31 / 'chain31.json')))
    return 0


def status31():
    out = {'stages': {}, 'stops': sorted(p.name for p in OUT31.glob('STOP_*.json')) if OUT31.is_dir() else []}
    for s in ORDER31:
        r = read(OUT31 / 'stages' / ('%s.json' % s))
        out['stages'][s] = None if r is None else r.get('ok')
    print(json.dumps(out))
    return 0


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    cmd = sys.argv[1]
    args = sys.argv[2:]

    def opt(name, default=None):
        return args[args.index(name) + 1] if name in args else default
    L.set_below_normal()
    if cmd == 'check31':
        mode, dest = opt('--mode'), opt('--dest')
        if mode not in ('decl', 'apply') or not dest:
            raise SystemExit('check31 --mode decl|apply --dest D')
        if Path(dest).resolve().is_relative_to(OUT31.resolve()) or Path(dest).resolve().is_relative_to(OUTK.resolve()):
            raise SystemExit('check31 --dest inside OUT31 / OUTK runs only inside chain31')
        return 0 if stage_check31(mode, dest)['ok'] else 3
    fn = {'chain31': chain31, 'status31': status31}.get(cmd)
    if fn is None:
        raise SystemExit('unknown command %s (amendment 31: check31 / chain31 / status31)' % cmd)
    return fn()


if __name__ == '__main__':
    raise SystemExit(main())
