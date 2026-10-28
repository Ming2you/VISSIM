"""K9-2 bundle 1 judging stage k92t, resumed under amendment 30 (scratch tool in KB/a30decl, never committed).
Base = KB/k92t/k92t.py (b07ffb56..., pinned before any k92t data; it ran start .. ja and stopped in f: STOP_f.json
'persist rc=1').  Amendment 30 (D-K9-56, D-K9-57, D-K9-55 timing) keeps every record of start / prep / J-0 / J-a /
J wall, seals the three F job logs (seal30), judges F from the existing F data with the persistence report narrowed
to T - 450 >= 900 (f30), then runs J-b unchanged (O6) and the post steps (post30).  The judges are in
k92t30_judge.py.  Both files are fixed (sha256 in KB/LOG.md and KB/a30_pins.sha256) before any amendment-30 data.
The functions kept from the base are byte-equal in source text except require_prev / stop / finish / log_md and one
token of stage_jb (the judge path); the base's start / prep / J-0 / J-a / F / post stages are not in this file.

    python -B k92t30.py check30 --mode decl|apply --dest D    (read-only resume check; amendment 30 section 4.1)
    python -B k92t30.py inv --dest D                           (OUTK inventory: rel path, size, sha256; read-only)
    python -B k92t30.py seal30 [--dry-run --dest D]            (D-K9-57 5: move the three F job logs)
    python -B k92t30.py chain30   (check30 apply -> s29 -> seal30 -> s30 -> f30 -> s31 -> jb -> s32 -> post30 -> s33;
                                   once, from the STOP state; stops at the first STOP)
    python -B k92t30.py status30
    detached: powershell -NoProfile -File KI/launch.ps1 -Tag k92t30_chain -Script ..\\a30decl\\k92t30.py
              -ArgLine chain30     (stdout -> OK2/logs/k92t30_chain.txt; this driver prints no value)

Roots.  Tree TREE = TK/a27/k92t = git archive K9-2-5 e27ceac8 (harness tree label 'k92t'), byte-equal to the K9-2-5
judge tree TK/a27/k925 (caches excluded) and holding the 19 judge blobs of OUT29/k925_blobs.json.  Outputs OUTK =
OK2/k92t (a new empty folder at the start): ja = SAF-K91 + K9-1 BASE (J-0 SAF-K91 side, J-a), jb = SAF-K92b1 + K9-1
BASE (J-0 SAF-K92b1 side, J pairs, J-b), f_off / f_w / f_b1 = the F arms, f_vref = the F VISSIM side, f_persist =
VISSIM M1 at T (persistence report), inputs, judge, logs, stages.

Harness calls = the TREE's own tools with --root TREE --out <root> --tree k92t --gates-stage k92t --declaration-sha
<amendment 24 sha> (the K9-2-0 guard opens the judging states only with that token), one child at a time,
BELOW_NORMAL, PYTHONHASHSEED=0, python -B, child stdout to OUTK/logs/<step>.log (never echoed).

Operationalisations fixed here before data (the amendment text is the definition; disclosed in the report):
 O1 arms.  ja: SAF = the TREE's SAF-K91 file (5f0d0e40), BASE = a byte copy of the K9-1 BASE tuning
    (k8_gate_trees/k91t config_n31_v2.json, 319d07aa) in OUTK/inputs (arms.json written in the sa_arms form).
    jb: sa_arms.py --k92b1 --base-file <that copy> (SAF-K92b1 = 65cac7ea).  f_off: SAF = SAF-K91; f_w: SAF = SAF-K91
    + the W pin only (k92_common.k92_pin, dumps_tuning; bytes = probe t74_W d179f01d); f_b1: sa_arms.py --k92b1.
 O2 VISSIM-side and R-obs validity inputs are byte copies of the K9-1 judging inputs in V4 (sa/vissim_ref.json
    e5e3466f, sa/fzp/*, opt1v2/**, sa/tl3m/robs_validity_s{31,43,47}.json), sha recorded; replay states are prepared
    in each root by the harness (prep.py for v3c3-s31, sa_tl3m.py prep for s43 / s47; copies of R-obs decisions).
 O3 J-0 captures: sa_capture.py tl3 SAF (s31), --robs-seed 43 / 47 tl3 SAF, dp SAF, robs61 SAF, in ja then jb.
 O4 J-a: ja BASE captures tl3 BASE 900 2700 4950 and --robs-seed 43 / 47 tl3 BASE 900; jobs by the harness library
    (sa_jobs.base_job + run_job): first the 11 J pairs back to back (ja SAF-K91 job, then the same label in jb on
    SAF-K92b1: TL3 s31 GRID9 H3 OBS and TL3m s43 / s47 900 H3 OBS), then in ja per arm (SAF, then BASE):
    TL3m s43 / s47 900 H3 (BASE; SAF done in the pairs), TL3 2700 OBS H42, TL3 4950 OBS H27, TL3 900 OBS H3 C11,
    TL3 900 OBS H3 TAN ad; the S3 anchor table (sa_anchors.py --root GWT8 --from-rev 5eef6be, the K9-1 call) in ja
    and jb; the full 2700 decisions with the hooks (--tag hooks --chain s3site) SAF and BASE in ja.  Judges: J-a and
    J wall (k92t_judge.py).
 O5 F before J-b (amendment 24 section 5.1 lets either open the stage; F is the shorter one): per arm root prep
    (s47 22 primary, s31 / s43 second sample 8 + 8), captures tl3 SAF of those states, jobs TL3 H3 OBS SAF (library);
    VISSIM side k92_vissim_ref.py --states 47:<22> 31:<8> 43:<8> (f_vref) — all of this ran under the base driver.
    O5' (amendment 30 section 2): persistence VR k92_vissim_ref.py --states 47:<T-450 for the 21 primary T with
    T-450 >= 900> into OUTK/f_persist30; T = 1050 (T-450 = 600 < U4 T_FROM 900) is labelled 'not measurable
    (T_FROM=900)' and never asked from the VR.  The base call (--states 47:<all 22 T-450>, root OUTK/f_persist) is
    the one that stopped; it is not repeated.
 O6 J-b (after J-a PASS): byte copies from V4 k91t of every BASE and SAG job folder, every BASE / SAG / BASE_fhoff
    capture folder and full/002700_BASE, except the BASE runs a harness check compares within one code tree, which run
    again in jb on TREE: ROBS61 BASE T = 1 / 150 of s31 / s43 / s47 (the identical-failure rule compares the exception
    line, which holds the code-tree path), TL3 BASE 2700 and T9C BASE 2700 (the T9b / T9c captured-state tests),
    full BASE 2700 / 4950 hooks (G-EB-13 positive control; hookcount expects the TREE's line patches); the K9-1
    G-EB-13 review file leader_review_k91t.json is copied as the review input.  Then every SAF run of the K9-1 chain
    (SAF only): captures (robs61 s43 / s47, fh, fh --fh-disabled --seeds 31, fh --frames T-150,T,T+150), the 4c unit
    run (the K9-1 command and env, capture root jb), the families tl3, long, tl3m, fh, dp, adfull, tl3 --hooks --T
    2700, c11, tan, h4, h0, h3, h5 with --arms SAF, full SAF 2700 / 4950 hooks, sa_hookcount.py, sa_gates.py --only
    <the J-b gates>.  Not rerun (no J-b judged item reads them): compare g1 / g9 / h0 / h4, sa_smoke, wallpairs, the
    k84v3 base-tree runs, SAG runs (copied).
 O7 STOP: any judge not PASS (J-b: DIFF = STOP_ASK_J, F: FAIL = STOP_ASK_F), any INCOMPLETE, any harness step with
    rc != 0 that leaves a judged input missing -> STOP_<stage>.json, no next stage, nothing rerun.
    O7' (amendment 30 section 5.3): as coded (must()): every step with rc != 0 stops, whether or not a judged input is
    missing; amendment-30 STOP files are OUTK/STOP_a30_<stage>.json (STOP_f.json of the base stays as it is).
 O8 post: after the J / F judge files are written their sha go to the LOG; then (amendment 25 section 6.4, amendment
    29 section 5) the sealed-root k92_record.json part of the section 3.1-3b scan runs (k92t_judge.py sealedscan).
    O8' (amendment 30 section 4.5): post30 also checks the sealed k92t index (the three moved logs: size, sha) and
    the base judge records; the G-K4 plant raw recompute (amendment 29 section 5) is the independent verifier's,
    after post30."""
import json
import os
import re
import shutil
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
TK = Path(r'D:/VISSIM-merge/k8_gate_trees/k92b1')
TREE = TK / 'a27' / 'k92t'
K925 = TK / 'a27' / 'k925'
K91T_TREE = Path(r'D:/VISSIM-merge/k8_gate_trees/k91t')
OK2 = Path(r'D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1')
OUTK = OK2 / 'k92t'
V4 = Path(r'D:/VISSIM-merge/k8_gates_out_v4')
OUT29 = OK2 / 'a29'
DECL_OUT = HERE / 'out'
LOG_MD = KB / 'LOG.md'
LABEL = 'k92t'
SA_REL = 'diagnostics/sdmpc_n31_20260924/k8_gates/sa'
SA = TREE / SA_REL
N31 = 'diagnostics/sdmpc_n31_20260924'
HEAD = 'e27ceac86c01c1dcfd5b2bb2d9b522be3dc33c0d'
K8 = 'b9734abe1c83f95c9cec5fca5e42b7b18cd45991'
BRANCH = 'claude/k92-b1-20261016'
A = {24: 'd46db6dc3959b19525f0fce77ead5432682e3de0ef8060cdc3da09661559aadc',
     25: '4fd7b599fe0f6131143e911dd3ab2be264a175e3f90b185bade9482d60b9ff8e',
     26: '8f8356168a299c07960d86ef12aa9f7af6f2f040af08ba75e5233a5819edba37',
     27: '4ce8b27a2ebf08aa0e8ac3f647b4e4336a98f7be7ec8d6f006a0fd1d12005a13',
     28: '9881eb40c1129af0cdff48026dc8656b4235d43f0eb80566e4be9b66d9ac345e',
     29: '4bd6dc8de8b0a4a4ab0b8703c07d7a73d244c4a622b81585f06dc69d6d83599d'}
FIXED = {24: 'fbc3d59fe2e47fec00d87262d624aa9a163ed02e113609b06173841397df101a',
         25: 'd1338fbc40a2efaf6997667f59e7bd709951e1fd3f2b1a8a0a0881794c3d24ed',
         26: '6edc55acd5aa0976701456d956e33f33c52ae0853535f6a4d8cb8bf26a354581',
         27: '394ab15fdea0d945a3b766c208e692ee7e1086fca3c178f6b423079d71fedcdb',
         28: '14451cf4d46c5c0095bc896134112148ba5700ee70b2ed78b8ee38d0e62e20e5',
         29: '3ba1d0bdaab8a0189f903d10fc1024baed770080542cbd841f79d3a56df58e43'}
NOTES = SP / 'K9_1_J1_NOTES_20261013.md'
NOTES_174 = 'abe3cc058b7369148b28e9ccb9a9cff1a49dfd34bd30e01599ef48f5932395af'
STAGE = ['--gates-stage', 'k92t', '--declaration-sha', A[24]]
K925_BLOBS = OUT29 / 'k925_blobs.json'
K925_BLOBS_SHA = '3a8f24cd85afab288f55a2e0105a47457a150842a3deaae8c5b5bcedf99e8112'
VR_SHA = 'f3fcc574d72f67ed8ad43cc94387fc3138fca1e81ab2d14ecfd9768338344efd'
SAF_K91_REL = N31 + '/config_n31_v2_stopline_observed_full_k91.json'
SAF_K91_SHA = '5f0d0e40a39e44b3c7601f23177afbad8c2eee23d4421626482f2244a86c3341'
CFG_SHA = 'd0f9ef395d4f9c51e6c68412f7c33abd546217e0d8cdc59d3c620183fa7aaec6'
CFG_ARM_SHA = 'c8e3ee2c99b66c255b2279f0aa18eaafc18d4c7689e59e260109fac3b7d71866'
B1_ARM_SHA = '65cac7ea0b33d8f0b5c8efc458307578bcae7a2e34d1d097ce448a18a65ada28'
W_ARM_SHA = 'd179f01da7f2e1ca240c4efabeb9f396172532cebb458cd7b821a9f3ce1aba1a'
W_ARM_FILE = 'config_n31_v2_stopline_observed_full_k91_k92w.json'
EVID = {N31 + '/k92/sc109w_through_saturation_v3b_u4_20261016.json':
        'b4b7294df0369874ea53dd5f0538abd31bac1c946aebdf241bdc7837a7671712',
        N31 + '/k92/head_floor_seed_v3c3_robs_20261016.json':
        'b9fa1d01b9d922e9fc327793aa428cd7b544dae221044704dea7f0af610f20ee'}
K91_BASE_SRC = K91T_TREE / N31 / 'config_n31_v2.json'
K91_BASE_SHA = '319d07aac77472d4318ddf6266003916cb7afab98da35a06254952e393542bb8'
GATES_K91T_SHA = '4e59f61d6d1b18ad588e95eaf6f215f44f6c66c981921735073d91f1c6c59b9f'
LEADER_REVIEW = V4 / 'sa' / 'gates' / 'leader_review_k91t.json'
LEADER_REVIEW_SHA = 'ba80564c20120de48e4e89f5e7a0a6e63efe19b5d9abb8765f7bcc7304fe663b'
VREF_V4_SHA = 'e5e3466f960a88eef7a0f6f7f2379a89b61627ed366e165103025ae52ccffab0'
RUN_PYTEST_BN = SP / 'k8b_impl' / 'run_pytest_bn.py'
GIT_DIR = 'D:/VISSIM-merge/repo/.git/worktrees/sim3-n31-k8'
ANCHOR_FROM = '5eef6be'
GRID9 = (900, 1200, 1800, 2250, 2700, 3000, 3600, 4200, 4950)
DP_T = tuple(900 + 450 * k for k in range(17))
ROBS61_T = (1,) + tuple(range(150, 9001, 150))
F_PRIMARY = (1050, 1650, 1950, 2400, 3300, 3750, 3900, 4650, 5100, 5550, 6000, 6150, 6450, 6600, 6900, 7050, 7350,
             7500, 7800, 7950, 8250, 8400)
F_SECOND = {31: (1500, 2850, 3900, 5250, 6000, 6600, 7500, 8250), 43: (1050, 3300, 4800, 5550, 6450, 7050, 7800, 8400)}
ROOTS = {'ja': OUTK / 'ja', 'jb': OUTK / 'jb', 'f_off': OUTK / 'f_off', 'f_w': OUTK / 'f_w', 'f_b1': OUTK / 'f_b1',
         'f_vref': OUTK / 'f_vref', 'f_persist30': OUTK / 'f_persist30'}
JB_GATES = 'G-EB-2,G-EB-3,G-EB-4,G-EB-5,G-EB-6,G-EB-7,G-EB-8,G-EB-13,G-EB-14'
UNIT_FILES = ['test_stopline_approach.py', 'test_stopline_wiring.py', 'test_stopline_evidence.py',
              'test_stopline_approach_captured.py']

# ------------------------------------------------------------------------------------------------ amendment 30
JUDGE = HERE / 'k92t30_judge.py'
ORDER = ['start', 'prep', 'j0', 'ja', 'seal30', 'f', 'jb', 'post']
A30_DOC = SP / 'K8_PREDECLARATION_AMENDMENT_30.md'
A30_SHA_FILE = SP / 'K8_PREDECLARATION_AMENDMENT_30.md.sha256'
FIXED30 = KB / 'AMENDMENT30_FIXED.md'
A30_PINS = KB / 'a30_pins.sha256'
OLD_PINS = KB / 'k92t_pins.sha256'
OLD_PINS_SHA = '38a2ce147795bbe7613fa5b6633441b31b814e781d1948e550753db776ed7cdd'
OLD_PINS_N = 56
NOTES_N = 182
NOTES_182 = 'eae2e6faf3c13dc42e84ef545fef734ad5ed9650946de72a76cb392b028c8d99'
OUT30 = OK2 / 'a30'
SEALED = OK2 / 'sealed_s47'
SEALED_TOPS = ['K9-2-0', 'K9-2-1', 'K9-2-2', 'K9-2-3', 'a27']
SEALED_K92T = SEALED / 'k92t'
SEAL_INDEX = OUT30 / 'sealed_k92t_index.json'
INV_DECL = DECL_OUT / 'outk_inventory_decl.json'
TREE_BUILD_SHA = 'a1e98fa72f787c17f576f9c2de2ed479709849e4880b962624a31d28b892b0d8'
# base records the resume keeps (OUTK-relative path -> sha256; amendment 30 section 4.1 C8)
RECORDED = {'STOP_f.json': 'ebff59c96596baca6039647e3902b88881a45fe6227b7da438e99afe420d3f17',
            'k92_judging_stage.json': '34e63a991451ef8c3f1be0ef6f4765f009abc19745fe7e546ffaeda43fd1aaa5',
            'start/scans.json': '410fde88da1e97e0434d3df59f292a904ed87c153a17bb209ec918b7a074bfb8',
            'stages/start.json': 'f3ed1dcea6f86b6c750368e9b5b2082331a9c85f18d435b9eac6af46744eef13',
            'stages/prep.json': '9ef3a7edd7e5a7c1d5938161c27c1f1bde5394da84d7cc61181876d78cfbc533',
            'stages/j0.json': '3845def6bbc0d95935fac27f36a24b13a5938d111aa11f1f7d93548f3f216631',
            'stages/ja.json': 'b40593bb34f45074546d58c808912ee4cffa6ff95dd0b5d3ac3543c89368b03c',
            'judge/j0.json': '24ee9d3b66d16618f9c6bc255bcabaecbcbaa2a653c985a9fb0315d68a85aab1',
            'judge/ja.json': '74806cb0683582bc20eccb68eb086363a0ac0e8d100d2c6c5d48436da14b4d5c',
            'judge/jwall.json': '1fb5c60454169b9f10014691a9fae9aa4697ac5bd26323e146149b6600fb615a',
            'f_vref/sa/k92_vissim_ref.json': '09f9194b308703db4d1da87cc10e458fca85872fd1189ef5fda7b2bc8f3b601a'}
OLD_STAGES = ('start', 'prep', 'j0', 'ja')
OLD_JUDGES = ('j0', 'ja', 'jwall')
STEPS_N = 59
STEPS_SHA = '7edd53c959da62362d948a62d2a15ff0030738d3e0a19dd9a7cc93e60a32ed69'
DRIVER_LOG = (3434, '8140fd2fa2d04a3781d8a3068a7171be0e6a22d34ced1d3d45cb78e12d22d728')
CHAIN_LOG_SHA = '8140fd2fa2d04a3781d8a3068a7171be0e6a22d34ced1d3d45cb78e12d22d728'
# the F steps of the base run (steps.jsonl names) and their recorded exit codes (amendment 30 section 4.1 C9)
F_STEPS_RC0 = tuple(['prep_%s_s%d' % (a, s) for a in ('f_off', 'f_w', 'f_b1') for s in (31, 43, 47)]
                    + ['arms_ja_f', 'arms_f_b1']
                    + ['f_%s_%s' % (a, k) for a in ('f_off', 'f_w', 'f_b1')
                       for k in ('cap_s47', 'cap_s31', 'cap_s43', 'jobs')] + ['f_vref'])
F_STEP_RC1 = 'f_persist'
# D-K9-57 5: the F job logs (child stdout of the F jobs; SA_JOB lines with objective= of the v3c3-s47 jobs)
F_JOB_LOGS = {'f_f_off_jobs.log': (4996, '84a72fcb570c329558f091ea042513bfe4477638669d85e7c3284b101b563c3b'),
              'f_f_w_jobs.log': (4936, '56293384819e5e7afd22e054502cc97e0e45aa7b06e4c90052b79768a8f885c5'),
              'f_f_b1_jobs.log': (4971, '6218e3dfac46b715401407cfc9e3982d2371322ba6bc207eac0c3ac12eea3935')}
# D-K9-56: the persistence report (amendment 30 section 2)
T_FROM_U4 = 900
PERSIST_NAME = 'f_persist30'
PERSIST_MEASURED = tuple(T for T in F_PRIMARY if T - 450 >= T_FROM_U4)
PERSIST_NOT = tuple(T for T in F_PRIMARY if T - 450 < T_FROM_U4)
PERSIST_VR_STATES = tuple(T - 450 for T in PERSIST_MEASURED)
SNAPS30 = ('s29_a30_check', 's30_a30_seal', 's31_a30_after_f', 's32_a30_after_jb', 's33_a30_post')


# ------------------------------------------------------------------------------------------------ helpers
def now():
    return time.strftime('%Y-%m-%d %H:%M:%S')


def log(msg):
    line = '%s %s' % (now(), msg)
    print(line, flush=True)
    if OUTK.is_dir():
        with open(OUTK / 'driver.log', 'a', encoding='utf-8') as f:
            f.write(line + '\n')


def log_md(text):
    """Automatic LOG.md line (verdicts, counts and sha only); the base wording 'k92t 구동기' becomes 'k92t30 구동기'."""
    text = text.replace('k92t 구동기', 'k92t30 구동기', 1)
    with open(LOG_MD, 'a', encoding='utf-8') as f:
        f.write('- [%s +0900] %s\n' % (now(), text))


def sha(p):
    return L.sha256_file(p)


def write(p, obj):
    L.write_json(p, obj)


def read(p, default=None):
    return L.read_json(p, default)


def stop(stage, why, extra=None):
    """Amendment 30: OUTK/STOP_a30_<stage>.json (the base STOP_f.json stays); extra holds names / counts / sha only."""
    rec = {'stage': stage, 'why': why, 'when': now(), 'extra': extra, 'driver': 'k92t30'}
    if OUTK.is_dir():
        write(OUTK / ('STOP_a30_%s.json' % stage), rec)
    log('STOP %s: %s' % (stage, why))
    log_md('k92t30 구동기: STOP — 단계 %s, 까닭 %s (k92t30.py, 자동 기록)' % (stage, why))
    raise SystemExit(3)


def finish(stage, rec):
    rec = dict(rec, stage=stage, when=now(), ok=True, driver='k92t30', driver_sha256=sha(Path(__file__)),
               judge_sha256=sha(JUDGE), amendment30_sha256=sha(A30_DOC))
    write(OUTK / 'stages' / ('%s.json' % stage), rec)
    log('STAGE_DONE %s' % stage)


def require_prev(stage):
    """Amendment 30 section 4: the only STOP file allowed is the base STOP_f.json (recorded bytes); the base stage
    records start / prep / j0 / ja must keep their recorded bytes; the amendment-30 stages need their own records."""
    stops = sorted(p.name for p in OUTK.glob('STOP_*.json')) if OUTK.is_dir() else []
    if stops != ['STOP_f.json'] or sha(OUTK / 'STOP_f.json') != RECORDED['STOP_f.json']:
        raise SystemExit('STOP files differ from the amendment-30 resume state: %s' % stops)
    i = ORDER.index(stage)
    for prev in ORDER[:i]:
        p = OUTK / 'stages' / ('%s.json' % prev)
        if prev in OLD_STAGES:
            if not p.is_file() or sha(p) != RECORDED['stages/%s.json' % prev]:
                raise SystemExit('base stage record %s differs from the recorded bytes' % prev)
        else:
            r = read(p, {}) or {}
            if not r.get('ok') or r.get('driver') != 'k92t30' or r.get('amendment30_sha256') != sha(A30_DOC):
                raise SystemExit('stage %s needs %s first (amendment 30)' % (stage, prev))


def space():
    fs = L.free_space_gb()
    if any(v < 8.0 for v in fs.values()):
        stop('space', 'LOW_SPACE %s' % fs)
    return fs


def env_for(root):
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith(('RW_', 'K8_', 'K8G_', 'K92A_'))}
    env.update(PYTHONHASHSEED='0', PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1', K8G_ROOT=str(TREE))
    if root is not None:
        env['K8G_OUT'] = str(root)
    return env


def step(name, argv, root=None, cwd=None, env=None):
    """One child, BELOW_NORMAL, stdout to OUTK/logs/<name>.log (never echoed); a record in OUTK/steps.jsonl."""
    space()
    logp = OUTK / 'logs' / ('%s.log' % name)
    if logp.exists():
        k = 1
        while (OUTK / 'logs' / ('%s.r%d.log' % (name, k))).exists():
            k += 1
        logp = OUTK / 'logs' / ('%s.r%d.log' % (name, k))
    logp.parent.mkdir(parents=True, exist_ok=True)
    pre = L.vissim_count()
    t0 = time.time()
    with open(logp, 'w', encoding='utf-8', errors='replace') as f:
        rc = subprocess.run([str(a) for a in argv], cwd=str(cwd or SA), env=env or env_for(root), stdout=f,
                            stderr=subprocess.STDOUT, creationflags=L.BELOW_NORMAL).returncode
    rec = {'name': name, 'rc': rc, 'start': t0, 'sec': round(time.time() - t0, 1), 'log': str(logp),
           'root': None if root is None else str(root), 'vissim_pre': pre, 'vissim_post': L.vissim_count(),
           'argv': [str(a) for a in argv]}
    with open(OUTK / 'steps.jsonl', 'a', encoding='utf-8') as f:
        f.write(json.dumps(rec) + '\n')
    log('STEP %s rc=%s sec=%s' % (name, rc, rec['sec']))
    return rc


def tool(root, name, *args, stage=True, tree=True):
    argv = [PY, '-B', str(SA / name), '--root', str(TREE), '--out', str(root)]
    if tree:
        argv += ['--tree', LABEL]
    if stage:
        argv += STAGE
    return argv + [str(a) for a in args]


def must(rc, stage, what):
    if rc != 0:
        stop(stage, '%s rc=%s' % (what, rc))


def git(*args):
    return subprocess.run(['git', '--no-optional-locks', '-C', str(GWT8)] + list(args), capture_output=True,
                          text=True, encoding='utf-8', errors='replace').stdout.strip()


def copy_file(src, dst, want=None):
    src, dst = Path(src), Path(dst)
    if want is not None and sha(src) != want:
        stop('copy', 'source sha differs: %s' % src)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(L.lp(src), L.lp(dst))
    s = sha(dst)
    if want is not None and s != want:
        stop('copy', 'copy sha differs: %s' % dst)
    return s


def copy_tree_rec(src, dst, rec):
    """Byte copy of a folder (caches excluded) with a (rel, size, sha) record."""
    src, dst = Path(src), Path(dst)
    if dst.exists():
        stop('copy', 'target exists: %s' % dst)
    L.copy_tree(src, dst)
    for rel, full in sorted(L.files_of(dst).items()):
        rec.append([str(dst / rel), os.path.getsize(full), L.sha256_file(full)])


def table_path(name):
    return ROOTS[name] / 'sa' / 'anchors' / ('s3_table_%s.json' % HEAD[:12])


# ------------------------------------------------------------------------------------------------ stage jb
def _arm_of(name):
    toks = name.split('_')
    arms = [a for a in ('BASE', 'SAF', 'SAG') if a in toks]
    return arms[0] if len(arms) == 1 else None


def jb_copies(rec):
    jb = ROOTS['jb']
    src_jobs = V4 / 'sa' / 'jobs' / 'k91t'
    dst_jobs = jb / 'sa' / 'jobs' / LABEL
    rec['jobs'] = []
    for d in sorted(p for p in src_jobs.iterdir() if p.is_dir()):
        if _arm_of(d.name) in ('BASE', 'SAG'):
            copy_tree_rec(d, dst_jobs / d.name, rec['jobs'])
    rerun = {('ROBS61', '000001', 'BASE'), ('ROBS61', '000150', 'BASE'), ('ROBS61', '000001_s43', 'BASE'),
             ('ROBS61', '000150_s43', 'BASE'), ('ROBS61', '000001_s47', 'BASE'), ('ROBS61', '000150_s47', 'BASE'),
             ('TL3', '002700', 'BASE'), ('T9C', '002700', 'BASE')}
    rec['caps'], rec['caps_skipped_rerun'] = [], []
    src_cap = V4 / 'sa' / 'cap' / 'k91t'
    for h in sorted(p for p in src_cap.iterdir() if p.is_dir()):
        for t in sorted(p for p in h.iterdir() if p.is_dir()):
            for a in sorted(p for p in t.iterdir() if p.is_dir()):
                if a.name not in ('BASE', 'SAG', 'BASE_fhoff'):
                    continue
                if (h.name, t.name, a.name) in rerun:
                    rec['caps_skipped_rerun'].append('%s/%s/%s' % (h.name, t.name, a.name))
                    continue
                copy_tree_rec(a, jb / 'sa' / 'cap' / LABEL / h.name / t.name / a.name, rec['caps'])
    rec['full'] = []
    copy_tree_rec(V4 / 'sa' / 'full' / 'k91t' / '002700_BASE', jb / 'sa' / 'full' / LABEL / '002700_BASE', rec['full'])
    rec['side'] = []
    for sub in ('fzp',):
        copy_tree_rec(V4 / 'sa' / sub, jb / 'sa' / sub, rec['side'])
    copy_tree_rec(V4 / 'opt1v2', jb / 'opt1v2', rec['side'])
    rec['leader_review'] = copy_file(LEADER_REVIEW, jb / 'sa' / 'gates' / 'leader_review_k91t.json', LEADER_REVIEW_SHA)
    rec['n'] = {k: len(rec[k]) for k in ('jobs', 'caps', 'full', 'side')}


def stage_jb():
    require_prev('jb')
    jb = ROOTS['jb']
    rec = {}
    jb_copies(rec)
    write(OUTK / 'jb_copies.json', rec)
    log('JB_COPIES %s' % rec['n'])
    # BASE runs compared within one code tree (O6)
    must(step('jb_base_robs_s31', tool(jb, 'sa_capture.py', 'robs61', 'BASE', 1, 150), root=jb), 'jb', 'base robs s31')
    for s in (43, 47):
        must(step('jb_base_robs_s%d' % s, tool(jb, 'sa_capture.py', '--robs-seed', s, 'robs61', 'BASE', 1, 150),
                  root=jb), 'jb', 'base robs s%d' % s)
    must(step('jb_base_tl3_2700', tool(jb, 'sa_capture.py', 'tl3', 'BASE', 2700), root=jb), 'jb', 'base tl3 2700')
    must(step('jb_base_t9c', tool(jb, 'sa_capture.py', 't9c', 'BASE', 2700), root=jb), 'jb', 't9c')
    # SAF captures (the J-0 ones exist)
    for s in (43, 47):
        must(step('jb_cap_robs_s%d' % s, tool(jb, 'sa_capture.py', '--robs-seed', s, 'robs61', 'SAF'), root=jb),
             'jb', 'robs s%d' % s)
    must(step('jb_cap_fh', tool(jb, 'sa_capture.py', 'fh', 'SAF'), root=jb), 'jb', 'fh')
    must(step('jb_cap_h0', tool(jb, 'sa_capture.py', '--seeds', 31, '--fh-disabled', 'fh', 'SAF'), root=jb), 'jb', 'h0')
    must(step('jb_cap_h5', tool(jb, 'sa_capture.py', '--frames', 'T-150,T,T+150', 'fh', 'SAF'), root=jb), 'jb', 'h5')
    # 4c unit run (the K9-1 command and env, capture root jb)
    t = 'diagnostics/sdmpc_n31_20260924/tests/'
    env = env_for(jb)
    env.update(K8_SA_CAPTURE_ROOT=str(jb / 'sa' / 'cap' / LABEL), K8_SA_BASE_REV='ec063ffa', NUMBA_NUM_THREADS='1',
               GIT_DIR=GIT_DIR, TMP=str(jb / 'tmp'), TEMP=str(jb / 'tmp'))
    (jb / 'tmp').mkdir(parents=True, exist_ok=True)
    unit_log = jb / 'sa' / 'unit_k92t.log'
    space()
    t0 = time.time()
    with open(unit_log, 'w', encoding='utf-8', errors='replace') as fh:
        rc = subprocess.run([PY, '-B', str(RUN_PYTEST_BN), '-v'] + [t + f for f in UNIT_FILES], cwd=str(TREE),
                            env=env, stdout=fh, stderr=subprocess.STDOUT, creationflags=L.BELOW_NORMAL).returncode
    with open(OUTK / 'steps.jsonl', 'a', encoding='utf-8') as f:
        f.write(json.dumps({'name': 'jb_unit', 'rc': rc, 'start': t0, 'sec': round(time.time() - t0, 1),
                            'log': str(unit_log), 'root': str(jb)}) + chr(10))
    (jb / 'sa' / 'unit_k92t.meta.txt').write_text(
        'ROOT %s (git archive %s) GIT_DIR=%s\nK8_SA_CAPTURE_ROOT=%s K8_SA_BASE_REV=ec063ffa NUMBA_NUM_THREADS=1\n'
        'CMD python -B run_pytest_bn.py -v %s\nrc=%s\n' % (TREE, HEAD[:8], GIT_DIR, env['K8_SA_CAPTURE_ROOT'],
                                                          ' '.join(t + f for f in UNIT_FILES), rc), encoding='utf-8')
    log('STEP jb_unit rc=%s (pytest; failures are read by sa_gates from the log)' % rc)
    # SAF families (the K9-1 chain order, SAF only)
    fams = [('tl3', []), ('long', []), ('tl3m', []), ('fh', []), ('dp', []), ('adfull', []),
            ('tl3', ['--hooks', '--T', 2700]), ('c11', []), ('tan', []), ('h4', []), ('h0', []), ('h3', []),
            ('h5', [])]
    for fam, extra in fams:
        nm = 'jb_jobs_%s%s' % (fam, '_hooks' if '--hooks' in extra else '')
        must(step(nm, tool(jb, 'sa_jobs.py', '--arms', 'SAF', *extra, fam), root=jb), 'jb', nm)
    for arm in ('SAF', 'BASE'):
        for T in (2700, 4950):
            must(step('jb_full_%s_%d' % (arm, T), tool(jb, 'sa_capture.py', 'full', arm, T, '--tag', 'hooks', '--chain',
                                                       's3site', '--s3-table', table_path('jb')), root=jb),
                 'jb', 'full %s %d' % (arm, T))
    must(step('jb_hookcount', tool(jb, 'sa_hookcount.py', stage=False), root=jb), 'jb', 'hookcount')
    must(step('jb_gates', tool(jb, 'sa_gates.py', '--base-tree', 'k84v3', '--unit-log', unit_log, '--leader-review',
                               jb / 'sa' / 'gates' / 'leader_review_k91t.json', '--only', JB_GATES, stage=False),
              root=jb), 'jb', 'sa_gates')
    new = jb / 'sa' / 'gates' / ('gates_%s.json' % LABEL)
    dest = OUTK / 'judge' / 'jb.json'
    rc = step('judge_jb', [PY, '-B', str(JUDGE), 'jb', '--new', str(new), '--dest', str(dest)],
              root=jb, cwd=HERE)
    res = read(dest, {}) or {}
    log_md('k92t 구동기: J-b 판정 %s (판정 잎 %s, 같음 %s, 다름 %s), `OK2/k92t/judge/jb.json` sha256 `%s`, 새 판정 파일 '
           'sha256 `%s` — J 판정 값 고정 (자동 기록)' % (res.get('verdict'), res.get('n_judged_items'), res.get('n_same'),
                                                    res.get('differing'), sha(dest) if dest.is_file() else None,
                                                    res.get('new_sha256')))
    if rc != 0 or res.get('verdict') != 'PASS':
        stop('jb', 'J-b %s (STOP_ASK_J / INCOMPLETE)' % res.get('verdict'), {'differing': res.get('differing')})
    finish('jb', {'judge_sha256': sha(dest), 'new_gates_sha256': res.get('new_sha256')})
    return 0


def snap(name):
    """Read-only roots snapshot (KI/k92snap.py, metadata only) compared with s02; different -> STOP (S-K11)."""
    p = OK2 / 'snap' / ('%s.json' % name)
    rc = step('snap_' + name, [PY, '-B', str(KI / 'k92snap.py'), 'take', str(p)], root=None, cwd=KI)
    rc2 = step('snapdiff_' + name, [PY, '-B', str(KI / 'k92snap.py'), 'diff',
                                    str(OK2 / 'snap' / 's02_after_probe_stop.json'), str(p)], root=None, cwd=KI)
    log_md('k92t 구동기: 읽기 전용 뿌리 스냅숏 `OK2/snap/%s.json` sha256 `%s`, s02 대비 %s (자동 기록)' % (
        name, sha(p) if p.is_file() else None, 'SAME' if rc2 == 0 else 'DIFFERENT'))
    if rc != 0 or rc2 != 0:
        stop('snap', 'snapshot %s rc=%s diff rc=%s (S-K11)' % (name, rc, rc2))


# ================================================================================================ amendment 30
def wjson(p, obj):
    """LF JSON (sorted keys) for the amendment-30 records outside the base forms."""
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(p) + '.tmp')
    with open(tmp, 'w', encoding='utf-8', newline='\n') as f:
        f.write(json.dumps(obj, indent=1, sort_keys=True, default=str, ensure_ascii=False) + '\n')
    os.replace(tmp, p)


def a30_sha():
    """Amendment 30 fixed: sha256(file) = its .sha256 = a 64-hex word in KB/AMENDMENT30_FIXED.md."""
    if not (A30_DOC.is_file() and A30_SHA_FILE.is_file() and FIXED30.is_file()):
        raise SystemExit('amendment 30 / .sha256 / fixation file missing')
    s = sha(A30_DOC)
    rec = A30_SHA_FILE.read_text(encoding='utf-8').split()[0]
    fixed = FIXED30.read_text(encoding='utf-8')
    if s != rec or not re.search(r'(?<![0-9a-f])%s(?![0-9a-f])' % s, fixed):
        raise SystemExit('amendment 30 is not the fixed text (sha %s, .sha256 %s)' % (s[:16], rec[:16]))
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


def inventory(root=OUTK):
    """Every file under root: posix rel path -> [size, sha256].  Bytes are hashed, never parsed."""
    out = {}
    for base, dirs, names in os.walk(L.lp(root)):
        dirs.sort()
        for n in sorted(names):
            full = os.path.join(base, n)
            rel = os.path.relpath(full, L.lp(root)).replace('\\', '/')
            out[rel] = [os.path.getsize(full), L.sha256_file(full)]
    return {'schema': 'k92t30-inventory/v1', 'root': str(root), 'n_files': len(out),
            'bytes': sum(v[0] for v in out.values()), 'files': out}


def inv_diff(a, b):
    fa, fb = a.get('files') or {}, b.get('files') or {}
    only_a = sorted(set(fa) - set(fb))
    only_b = sorted(set(fb) - set(fa))
    changed = sorted(k for k in set(fa) & set(fb) if fa[k] != fb[k])
    return {'only_declared': only_a[:30], 'n_only_declared': len(only_a), 'only_now': only_b[:30],
            'n_only_now': len(only_b), 'changed': changed[:30], 'n_changed': len(changed),
            'same': not (only_a or only_b or changed)}


def f_labels(seed, Ts):
    return ['TL3_%d%s_SAF_OBS_H3' % (T, '' if seed == 31 else '_s%d' % seed) for T in Ts]


def f_inputs_check():
    """Amendment 30 section 4.1 C9 / C10: the F inputs of the base run, by names, exit codes and one sha (no value)."""
    out, ok = {}, True
    steps = [json.loads(ln) for ln in (OUTK / 'steps.jsonl').read_text(encoding='utf-8').splitlines() if ln.strip()]
    by = {}
    for r in steps[:STEPS_N]:
        by.setdefault(r['name'], []).append(r)
    rc0 = {n: [(r.get('rc'), r.get('vissim_pre'), r.get('vissim_post')) for r in by.get(n, [])] for n in F_STEPS_RC0}
    out['f_steps_rc0'] = {n: v == [(0, 0, 0)] for n, v in rc0.items()}
    out['f_persist_rc1'] = [r.get('rc') for r in by.get(F_STEP_RC1, [])] == [1]
    fnames = sorted(n for n in by if n.startswith(('f_', 'prep_f_')) or n in ('arms_ja_f', 'arms_f_b1'))
    out['f_step_names_declared'] = fnames == sorted(F_STEPS_RC0 + (F_STEP_RC1,))
    ok &= all(out['f_steps_rc0'].values()) and out['f_persist_rc1'] and out['f_step_names_declared']
    want_jobs = sorted(f_labels(47, F_PRIMARY) + f_labels(31, F_SECOND[31]) + f_labels(43, F_SECOND[43]))
    want_caps = sorted(['%06d_s47' % T for T in F_PRIMARY] + ['%06d' % T for T in F_SECOND[31]]
                       + ['%06d_s43' % T for T in F_SECOND[43]])
    for arm in ('f_off', 'f_w', 'f_b1'):
        jd = ROOTS[arm] / 'sa' / 'jobs' / LABEL
        cd = ROOTS[arm] / 'sa' / 'cap' / LABEL / 'TL3'
        jobs = sorted(p.name for p in jd.iterdir() if p.is_dir()) if jd.is_dir() else []
        caps = sorted(p.name for p in cd.iterdir() if p.is_dir()) if cd.is_dir() else []
        caps_saf = all((cd / t / 'SAF').is_dir() for t in caps)
        out[arm] = {'jobs': len(jobs), 'jobs_declared': jobs == want_jobs, 'caps': len(caps),
                    'caps_declared': caps == want_caps and caps_saf}
        ok &= out[arm]['jobs_declared'] and out[arm]['caps_declared']
    vr_files = sorted(inventory(ROOTS['f_vref'])['files'])
    out['f_vref_files'] = vr_files == ['sa/k92_vissim_ref.json']
    out['f_vref_sha'] = sha(ROOTS['f_vref'] / 'sa' / 'k92_vissim_ref.json') == RECORDED['f_vref/sa/k92_vissim_ref.json']
    out['f_persist_absent'] = not (OUTK / 'f_persist').exists()
    ok &= out['f_vref_files'] and out['f_vref_sha'] and out['f_persist_absent']
    out['ok'] = bool(ok)
    return out


def persist_argv():
    """Amendment 30 section 2.3: the one persistence VR call (21 VR states T-450 >= 900, never 600)."""
    if any(t < T_FROM_U4 for t in PERSIST_VR_STATES) or len(PERSIST_VR_STATES) != 21 or PERSIST_NOT != (1050,):
        raise SystemExit('persistence state set differs from amendment 30')
    return [PY, '-B', str(SA / 'k92_vissim_ref.py'), '--root', str(TREE), '--out', str(ROOTS['f_persist30']),
            '--states', '47:' + ','.join(str(t) for t in PERSIST_VR_STATES)] + STAGE


def stage_check30(mode, dest):
    """Amendment 30 section 4.1: read-only resume check (closed list C1-C15).  mode decl = before amendment 30 is
    fixed (C2 / C6 reported, C13 against the declare inventory if it exists); apply = every check binding."""
    chk, info = {}, {}
    for n in A:
        doc = SP / ('K8_PREDECLARATION_AMENDMENT_%d.md' % n)
        chk['C1_a%d' % n] = sha(doc) == A[n] and (SP / ('K8_PREDECLARATION_AMENDMENT_%d.md.sha256' % n)).read_text(
            encoding='utf-8').split()[0] == A[n]
        chk['C1_fixed%d' % n] = sha(KB / ('AMENDMENT%d_FIXED.md' % n)) == FIXED[n]
    if mode == 'apply':
        try:
            info['a30_sha256'] = a30_sha()
            chk['C2_a30_fixed'] = True
        except SystemExit as exc:
            info['a30_problem'] = str(exc)
            chk['C2_a30_fixed'] = False
    else:
        info['C2_a30'] = {'doc': A30_DOC.is_file(), 'sha_file': A30_SHA_FILE.is_file(), 'fixation': FIXED30.is_file()}
    lines = NOTES.read_bytes().splitlines(keepends=True)
    chk['C3_notes'] = len(lines) >= NOTES_N and L.sha256_bytes(b''.join(lines[:NOTES_N])) == NOTES_182
    chk['C4_head'] = git('rev-parse', 'HEAD') == HEAD
    chk['C4_branch'] = git('rev-parse', '--abbrev-ref', 'HEAD') == BRANCH
    chk['C4_k8_branch'] = git('rev-parse', 'claude/k8-sc1001eb-defects-20261004') == K8
    chk['C4_status_clean'] = git('status', '--porcelain') == ''
    chk['C4_no_remote_k92'] = 'k92' not in git('for-each-ref', '--format=%(refname)', 'refs/remotes')
    n, bad, s = pins_check(OLD_PINS)
    chk['C5_old_pins'] = s == OLD_PINS_SHA and n == OLD_PINS_N and not bad
    info['C5_old_pins_bad'] = bad[:10]
    if mode == 'apply':
        n, bad, s = pins_check(A30_PINS)
        listed = A30_PINS.read_text(encoding='utf-8') if A30_PINS.is_file() else ''
        mine = ['%s *%s' % (sha(p), str(p).replace('\\', '/')) for p in (Path(__file__).resolve(), JUDGE)]
        chk['C6_a30_pins'] = (s is not None and not bad and all(m in listed for m in mine)
                              and re.search(r'(?<![0-9a-f])%s(?![0-9a-f])' % s, FIXED30.read_text(encoding='utf-8'))
                              is not None)
        info['C6'] = {'n': n, 'bad': bad[:10], 'sha256': s}
    chk['C7_tree_build'] = sha(TK / 'a27' / 'k92t.build.json') == TREE_BUILD_SHA
    d = L.tree_diff(K925, TREE)
    chk['C7_tree_vs_k925'] = not d['changed'] and not d['only_a'] and not d['only_b']
    info['C7_tree_diff'] = {'changed': d['changed'][:10], 'only_k925': d['only_a'][:10], 'only_k92t': d['only_b'][:10]}
    chk['C7_vr'] = sha(SA / 'k92_vissim_ref.py') == VR_SHA
    chk['C8_recorded'] = all((OUTK / rel).is_file() and sha(OUTK / rel) == want for rel, want in RECORDED.items())
    info['C8_recorded_bad'] = [rel for rel, want in RECORDED.items()
                               if not (OUTK / rel).is_file() or sha(OUTK / rel) != want]
    chk['C8_stop_files'] = sorted(p.name for p in OUTK.glob('STOP_*.json')) == ['STOP_f.json']
    chk['C8_stage_records'] = sorted(p.name for p in (OUTK / 'stages').iterdir()) == sorted(
        '%s.json' % s for s in OLD_STAGES)
    chk['C8_judge_files'] = sorted(p.name for p in (OUTK / 'judge').iterdir()) == sorted(
        '%s.json' % s for s in OLD_JUDGES)
    raw = (OUTK / 'steps.jsonl').read_bytes().splitlines(keepends=True)
    chk['C8_steps'] = len(raw) == STEPS_N and L.sha256_bytes(b''.join(raw[:STEPS_N])) == STEPS_SHA
    dl = (OUTK / 'driver.log').read_bytes()
    chk['C8_driver_log'] = len(dl) == DRIVER_LOG[0] and L.sha256_bytes(dl) == DRIVER_LOG[1]
    chk['C8_chain_log'] = sha(OK2 / 'logs' / 'k92t_chain.txt') == CHAIN_LOG_SHA
    fi = f_inputs_check()
    info['C9_C10'] = fi
    chk['C9_C10_f_inputs'] = fi['ok'] and not ROOTS['f_persist30'].exists()
    logs = sorted(p.name for p in (OUTK / 'logs').glob('f_*_jobs*.log'))
    chk['C11_job_logs'] = logs == sorted(F_JOB_LOGS) and all(
        os.path.getsize(OUTK / 'logs' / n) == F_JOB_LOGS[n][0] and sha(OUTK / 'logs' / n) == F_JOB_LOGS[n][1]
        for n in logs)
    tops = sorted(p.name for p in SEALED.iterdir()) if SEALED.is_dir() else []
    chk['C12_sealed_tops'] = tops == SEALED_TOPS
    chk['C12_out30_absent'] = not OUT30.exists() if mode == 'apply' else True
    info['C12_out30_exists'] = OUT30.exists()
    now_inv = inventory(OUTK)
    if INV_DECL.is_file():
        dif = inv_diff(read(INV_DECL, {}) or {}, now_inv)
        chk['C13_inventory'] = dif['same']
        info['C13'] = dict(dif, n_files=now_inv['n_files'], bytes=now_inv['bytes'],
                           declared_sha256=sha(INV_DECL))
    else:
        chk['C13_inventory'] = mode != 'apply'
        info['C13'] = {'declared': None, 'n_files': now_inv['n_files'], 'bytes': now_inv['bytes']}
    cen = L.census()
    chk['C14_vissim_0'] = cen['vissim_any'] == 0
    chk['C14_foreign_0'] = not cen['foreign_runner_or_replay']
    fs = L.free_space_gb()
    chk['C15_space'] = all(v >= 8.0 for v in fs.values())
    info.update(census=cen['counts'], free_gb=fs, persist_vr_states=list(PERSIST_VR_STATES),
                persist_not_measurable=list(PERSIST_NOT), persist_argv_tail=persist_argv()[-6:])
    rec = {'schema': 'k92t30-check30/v1', 'mode': mode, 'when': now(), 'checks': chk, 'info': info,
           'driver_sha256': sha(Path(__file__)), 'judge_sha256': sha(JUDGE),
           'ok': all(chk.values())}
    wjson(dest, rec)
    print('K92T30_CHECK30 mode=%s ok=%s bad=%s' % (mode, rec['ok'], [k for k, v in chk.items() if not v]))
    return rec


def stage_seal30(dry=False, dest=None):
    """Amendment 30 section 4.2 (D-K9-57 5): move the three F job logs into OK2/sealed_s47/k92t/logs; the index (name,
    from, to, size, sha256, mtime, moved_at) goes to OK2/a30 outside the sealed root.  Bytes are hashed, never read
    as text, before and after the move."""
    if not dry:
        a30 = a30_sha()
        require_prev('seal30')
    logs = sorted(p.name for p in (OUTK / 'logs').glob('f_*_jobs*.log'))
    plan = []
    for name in sorted(F_JOB_LOGS):
        size, want = F_JOB_LOGS[name]
        src = OUTK / 'logs' / name
        st = os.stat(src) if src.is_file() else None
        plan.append({'name': name, 'from': str(src), 'to': str(SEALED_K92T / 'logs' / name), 'size': size,
                     'sha256': want, 'size_ok': bool(st) and st.st_size == size,
                     'sha_ok': bool(st) and sha(src) == want,
                     'mtime': time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(st.st_mtime)) if st else None})
    tops = sorted(p.name for p in SEALED.iterdir()) if SEALED.is_dir() else []
    pre_ok = (logs == sorted(F_JOB_LOGS) and all(r['size_ok'] and r['sha_ok'] for r in plan) and tops == SEALED_TOPS
              and not SEALED_K92T.exists())
    if dry:
        wjson(dest, {'schema': 'k92t30-seal-plan/v1', 'dry_run': True, 'ok': pre_ok, 'plan': plan, 'tops': tops,
                     'when': now()})
        print('K92T30_SEAL30 dry ok=%s n=%d' % (pre_ok, len(plan)))
        return 0
    if not pre_ok:
        stop('seal30', 'the job logs or the sealed root differ from amendment 30 (S-K42)',
             {'logs': logs, 'tops': tops, 'bad': [r['name'] for r in plan if not (r['size_ok'] and r['sha_ok'])]})
    (SEALED_K92T / 'logs').mkdir(parents=True)
    for r in plan:
        try:
            os.replace(r['from'], r['to'])
        except OSError as exc:
            stop('seal30', 'move failed: %s (%s)' % (r['name'], type(exc).__name__))
        r['moved_at'] = now()
        r['after_size_ok'] = os.path.getsize(r['to']) == r['size']
        r['after_sha_ok'] = sha(r['to']) == r['sha256']
        r['source_gone'] = not Path(r['from']).exists()
    idx = {'schema': 'k92t30-sealed-index/v1', 'amendment30_sha256': a30, 'n': len(plan), 'files': plan,
           'tops_after': sorted(p.name for p in SEALED.iterdir()), 'when': now(),
           'note': 'D-K9-57 5: sealed k92t job logs; open only per amendment 25 section 6.4 after the J / F values '
                   'are fixed (or for a k92t failure diagnosis), each opening logged'}
    wjson(SEAL_INDEX, idx)
    good = all(r['after_size_ok'] and r['after_sha_ok'] and r['source_gone'] for r in plan) and \
        idx['tops_after'] == sorted(SEALED_TOPS + ['k92t'])
    log_md('k92t30 구동기: D-K9-57 ⑤ 봉인 이동 %d파일(F 잡 로그 셋) → `OK2/sealed_s47/k92t/logs/`, 크기·sha 같음 %s, '
           '목록 `OK2/a30/sealed_k92t_index.json` sha256 `%s` (자동 기록)' % (len(plan), good, sha(SEAL_INDEX)))
    if not good:
        stop('seal30', 'moved bytes differ (S-K42)')
    finish('seal30', {'index_sha256': sha(SEAL_INDEX)})
    return 0


def stage_f30():
    """Amendment 30 section 2 / 4.3: F judged from the existing F data.  fcount (job success from the job files) ->
    persistence VR (21 states) -> F judge; nothing of the base F run is rerun."""
    a30_sha()
    require_prev('f')
    if sha(SA / 'k92_vissim_ref.py') != VR_SHA:
        stop('f', 'VR sha differs (S-K21)')
    fi = f_inputs_check()
    if not fi['ok']:
        stop('f', 'F inputs differ from the amendment-30 resume state (S-K41)',
             {k: v for k, v in fi.items() if k != 'f_steps_rc0'})
    dc = OUTK / 'judge' / 'f_jobs.json'
    for p in (dc, OUTK / 'judge' / 'f.json', ROOTS['f_persist30']):
        if p.exists():
            stop('f', '%s exists before f30 (S-K41)' % p.name)
    rc = step('judge_fcount', [PY, '-B', str(JUDGE), 'fcount', '--dest', str(dc)], root=None, cwd=HERE)
    rcnt = read(dc, {}) or {}
    log_md('k92t30 구동기: F 잡 정상 수(요약·기록·포착 파일로만 셈) %s, `OK2/k92t/judge/f_jobs.json` sha256 `%s` '
           '(자동 기록)' % (rcnt.get('verdict'), sha(dc) if dc.is_file() else None))
    if rc != 0 or rcnt.get('verdict') != 'PASS':
        stop('f', 'F job count %s (INCOMPLETE)' % rcnt.get('verdict'))
    must(step('f_persist30', persist_argv(), root=ROOTS['f_persist30']), 'f', 'persist30 (S-K43)')
    dest = OUTK / 'judge' / 'f.json'
    rc = step('judge_f', [PY, '-B', str(JUDGE), 'f', '--tree', str(TREE), '--dest', str(dest)],
              root=ROOTS['f_b1'], cwd=SA)
    res = read(dest, {}) or {}
    fj = res.get('f_judge') or {}
    pr = res.get('report_persistence_M1_450') or {}
    log_md('k92t30 구동기: F 판정 %s (F-1 %s, F-2 %s, F-3 %s, n %s; 지속성 보고 측정 %s·측정 불가 %s·완전 %s), '
           '`OK2/k92t/judge/f.json` sha256 `%s` — F 판정 값 고정 (자동 기록)' % (
               res.get('verdict'), fj.get('F-1'), fj.get('F-2'), fj.get('F-3'), fj.get('n'), pr.get('n'),
               sorted(pr.get('not_measurable') or {}), pr.get('complete'), sha(dest) if dest.is_file() else None))
    if rc != 0 or res.get('verdict') != 'PASS':
        stop('f', 'F %s (STOP_ASK_F / INCOMPLETE)' % res.get('verdict'), {'missing': res.get('missing')})
    if pr.get('complete') is not True:
        stop('f', 'persistence report incomplete (S-K43)', {k: pr.get(k) for k in (
            'missing', 'vr_states_equal_declared', 'overlap_with_f_vref', 'identity_ok')})
    finish('f', {'judge_sha256': sha(dest), 'fcount_sha256': sha(dc),
                 'persist_sha256': sha(ROOTS['f_persist30'] / 'sa' / 'k92_vissim_ref.json')})
    return 0


def stage_post30():
    """Amendment 30 section 4.5: after the J / F judge files are fixed in the LOG: the sealed-root k92_record scan
    (base function), the sealed k92t index, the base judge records."""
    a30_sha()
    require_prev('post')
    fixed = {n: sha(OUTK / 'judge' / ('%s.json' % n)) for n in ('f', 'jb')}
    text = LOG_MD.read_text(encoding='utf-8')
    if not all(s in text for s in fixed.values()):
        stop('post', 'the J / F judge sha are not in the LOG (amendment 30 section 4.5)')
    dest = OUTK / 'judge' / 'sealed_records.json'
    rc = step('post_sealedscan', [PY, '-B', str(JUDGE), 'sealedscan', '--dest', str(dest)], root=None, cwd=HERE)
    res = read(dest, {}) or {}
    idx = read(SEAL_INDEX, {}) or {}
    idx_ok = idx.get('n') == len(F_JOB_LOGS) and all(
        Path(r['to']).is_file() and os.path.getsize(r['to']) == r['size'] and sha(r['to']) == r['sha256']
        and not Path(r['from']).exists() for r in idx.get('files') or [])
    base_ok = all(sha(OUTK / rel) == want for rel, want in RECORDED.items())
    log_md('k92t30 구동기: J·F 판정 값 고정 확인(f.json `%s…`, jb.json `%s…`), 봉인 뿌리 k92_record.json 훑기 ok=%s '
           '(%s), 봉인 k92t 목록 같음 %s, 앞 기록 바이트 같음 %s, `OK2/k92t/judge/sealed_records.json` sha256 `%s` — '
           '이제 봉인 로그는 보충 25 §6.4대로 열 수 있음(열 때마다 LOG), G-K4 plant 원자료 재계산(보충 29 §5)은 독립 '
           '검증기 몫 (자동 기록)' % (fixed['f'][:16], fixed['jb'][:16], res.get('ok'), res.get('sealed_records'),
                                      idx_ok, base_ok, sha(dest) if dest.is_file() else None))
    if rc != 0 or not res.get('ok'):
        stop('post', 'sealed-root record scan not ok (S-K10)')
    if not idx_ok:
        stop('post', 'sealed k92t index differs (S-K42)')
    if not base_ok:
        stop('post', 'a base record changed (S-K41)')
    judges = {n: sha(OUTK / 'judge' / ('%s.json' % n)) for n in ('j0', 'ja', 'jwall', 'f_jobs', 'f', 'jb',
                                                                  'sealed_records')}
    finish('post', {'judges_sha256': judges, 'sealed_index_sha256': sha(SEAL_INDEX)})
    return 0


def chain30():
    """Once, from the STOP state: check30 apply -> s29 -> seal30 -> s30 -> f30 -> s31 -> jb -> s32 -> post30 -> s33."""
    a30_sha()
    if OUT30.exists() or any((OUTK / 'stages' / ('%s.json' % n)).exists() for n in ('seal30', 'f', 'jb', 'post')):
        raise SystemExit('chain30 runs once from the STOP state; an amendment-30 record exists (the user decides)')
    rec = stage_check30('apply', OUT30 / 'check30.json')
    log_md('k92t30 구동기: 이어 하기 점검 ok=%s, `OK2/a30/check30.json` sha256 `%s` (자동 기록)' % (
        rec['ok'], sha(OUT30 / 'check30.json')))
    if not rec['ok']:
        stop('check30', 'resume check false (S-K41)', [k for k, v in rec['checks'].items() if not v])
    snap(SNAPS30[0])
    stage_seal30()
    snap(SNAPS30[1])
    stage_f30()
    snap(SNAPS30[2])
    stage_jb()
    snap(SNAPS30[3])
    stage_post30()
    snap(SNAPS30[4])
    log('CHAIN30_DONE')
    log_md('k92t30 구동기: 사슬 끝 — check30·seal30·f·jb·post 모두 끝 (자동 기록)')
    return 0


def status30():
    out = {'stages': {}, 'stops': sorted(p.name for p in OUTK.glob('STOP_*.json')) if OUTK.is_dir() else []}
    for s in ORDER:
        r = read(OUTK / 'stages' / ('%s.json' % s))
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
    if cmd == 'check30':
        mode = opt('--mode')
        if mode not in ('decl', 'apply') or not opt('--dest'):
            raise SystemExit('check30 --mode decl|apply --dest D')
        return 0 if stage_check30(mode, opt('--dest'))['ok'] else 3
    if cmd == 'inv':
        if not opt('--dest'):
            raise SystemExit('inv --dest D')
        res = inventory(OUTK)
        wjson(opt('--dest'), res)
        print('K92T30_INV n=%d bytes=%d' % (res['n_files'], res['bytes']))
        return 0
    if cmd == 'seal30':
        if '--dry-run' in args:
            return stage_seal30(dry=True, dest=opt('--dest'))
        return stage_seal30()
    fn = {'chain30': chain30, 'status30': status30}.get(cmd)
    if fn is None:
        raise SystemExit('unknown command %s (amendment 30: check30 / inv / seal30 / chain30 / status30)' % cmd)
    return fn()


if __name__ == '__main__':
    raise SystemExit(main())
