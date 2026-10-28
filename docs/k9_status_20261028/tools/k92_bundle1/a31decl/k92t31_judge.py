"""K9-2 bundle 1 judging stage k92t, resumed under amendment 30: judges (scratch tool in KB/a30decl, never committed).
Base = KB/k92t/k92t_judge.py (eb4c113a..., pinned before any k92t data); amendment 30 changes only the F judge
(cmd_f: the persistence report narrowed to the states with T - 450 >= 900 = U4 T_FROM, D-K9-56; per-arm job counts
from the summary / record files, D-K9-57 5) and this text.  Every other function is byte-equal in its source text to
the base (amendment 30 section 3.3; checked by dry_a30.py static).  J-0 / J-a / J wall were judged by the base file
before amendment 30 (OUTK/judge/j0.json, ja.json, jwall.json); this file does not judge them again.
Fixed (sha256 in KB/LOG.md and KB/a30_pins.sha256) before any amendment-30 data.  Amendment 24 sections 5.1-5.3 are
the definitions; amendments 25-30 bind k92t as they say (sealing A', VR network identity, K9-2-5 judge blobs,
old_root, four outcomes, the persistence narrowing).  The operationalisations below are the readings fixed before
data (disclosed in the report).

BLIND form: verdicts, counts, generalized paths, sha.  The F judge file carries the declared F numbers (MAE / bias per
arm and metric, per-state table) because amendment 24 section 6 STOP_ASK_F shows them; the J-b file carries the
differing K9-1 judged values only when they differ (STOP_ASK_J report form).  Nothing here opens a sealed log.

    python -B k92t30_judge.py sealedscan --dest D                        (after the J / F values are fixed)
    python -B k92t30_judge.py jb    --new <gates_k92t.json> --dest D
    python -B k92t30_judge.py f     --tree T --dest D                    (child process)
    (scans / j0 / ja / jwall: the base functions, kept byte-equal; not run under amendment 30)

J-0 (amendment 24 section 5.2 row J-0).  States: TL3m 27 = TL3 captures of R-obs v3c3-s31 / s43 / s47 x GRID9,
DP 17 = DP captures at DP_T, R-obs3 61 = ROBS61 captures of R-obs3 (= v3c3-s31, sa_common.ROBS_SEED) at ROBS61_T.
Arms: SAF-K91 = output root JA (arm folder SAF, tuning 5f0d0e40) and SAF-K92b1 = output root JB (arm folder SAF,
tuning 65cac7ea), both in the same k92t tree.  Per state:
  outcome  both captures ok (capture.json ok) -> rows (a)-(d); both failed is allowed only for ROBS61 T in {1, 150}
           and only with equal sa_errors.traceback_signature of action_<T>.error.txt (else the record error) = the
           amendment-13 G-EB-14 'identical failure' rule (the K9-1 record shows every arm fails there; such a state
           counts in "61/61" as an identical failure, reported); one side failed, or failed elsewhere = FAIL;
           a missing record = INCOMPLETE.
  (a) meta metadata k8b_p1, k8b_p2, k8b_p2_init, k8b_p4, k9_w1, k9_w2a, k9_f17b canonical JSON equal.
  (b) SA   SA initial state = metadata.stopline_approach_install_check (members), metadata.stopline_approach_initial
           (incl. posthead_veh = vehicles past the head after initialisation), probes.sa, probes.ports,
           probes.records, probes.provenance['127'], probes.occupancy['SC1001_W_out'] canonical JSON equal.
  (c) cap  template follower cfg.network.movement_capacity_by_movement_veh_h: the differing keys = {W} with the
           SAF-K92b1 value repr 5209.8, plus L exactly when the SAF-K91 value of L < s (repr 1045.1612903225805) and
           then the SAF-K92b1 value of L repr = s (amendment 24 section 4.3 G-K1 static condition).
  (d) init ROBS61 / every state: install_check present and passed on both sides (G-EB-14 (i) form); "61/61" =
           initialized + identical T = 1 / 150 failures on the SAF-K92b1 side.
  report   every other differing capture.json leaf (generalized path) and the one-sided metadata keys (the K9-2 keys
           k92_w / k92_hb / k92_hb_seed_binding on the SAF-K92b1 side are expected); not judged.
  PASS iff 105 states present and every state passes; INCOMPLETE when a record is missing; FAIL otherwise.

J-a (row J-a).  Items (fixed here, the first state of the family where a choice is open):
  SAF-K91 jobs TL3_<T>_SAF_OBS_H3, T in GRID9 (9);
  per arm SAF-K91 and K9-1 BASE (319d07aa): TL3m H3 TL3_900_s43_<arm>_OBS_H3, TL3_900_s47_<arm>_OBS_H3; long
  TL3_2700_<arm>_OBS_H42, TL3_4950_<arm>_OBS_H27; c11 TL3_900_<arm>_OBS_H3_C11; tan TL3_900_<arm>_OBS_H3_TAN_ad;
  "DP 훅 한 결정" = the full deployed decision 2700 with the hooks (sa_capture.py full <arm> 2700 --tag hooks
  --chain s3site; G-EB-13's DP full-decision runs).
  Rule: job items = "summary numeric leaves equal": k8b_commit_gates.leaves of both summary.json, the G5 exclusions
  (SKIP timing keys and G5_EXCLUDE), every numeric leaf present on both sides and bit-equal (NaN = NaN); string /
  hash / path leaves reported only.  Decision items (amendment 29 section 6.1-3): k92_compare.compare(old = the k91t
  output, new = the JA output, T, new_root = k92t tree, keyed None, old_root = k8_gate_trees/k91t) four outcomes,
  PASS only; run.json objective / held_objective / exit reported.  J-a PASS iff every item present and same / PASS.

J wall (amendment 24 section 5.2 note; RG-6): pairs = the 11 SAF H3 OBS jobs of J-a (TL3 s31 GRID9 + TL3m s43 900
+ s47 900) on SAF-K91 (JA) and the same label on SAF-K92b1 (JB), run back to back (A then B); clean = the four
vissim_counts.json counts known and 0; ratio = summary wall_sec B / A; PASS iff median of clean ratios <= 1.05 /
1.033718118959995; no clean pair = INCOMPLETE; IQR reported only.

J-b (row J-b).  Judged items = every item of G-EB-2, 3, 4, 5, 6, 7, 8, 13, 14 in gates_k91t.json (sha 4e59f61d...)
whose pass_ is not null; the new file = sa_gates.py --only <those gates> on the JB root (SAF-K92b1).  Same iff the
item is present and json.dumps(value, sort_keys=True, allow_nan=True) of both files are equal (repr of every float).
PASS iff every judged item is the same; otherwise DIFF (STOP_ASK_J); missing gates file = INCOMPLETE.

F (section 5.3).  Rows of the 22 primary states (v3c3-s47) per arm OFF / B1 (W reported): model = k92_record.json
horizon m1_chain_T450 / m2_w_dep_T450 / m3_l_dep_T450 of TL3_<T>_s47_SAF_OBS_H3 in the arm root; VISSIM =
k92_vissim_ref.json (root F_VREF) m1_T450 / m2_T450 / m3_T450; network identity raw sha of the seed = 1895ca30 (s47),
3de889f0 (s31), 51478c39 (s43) (amendment 25 section 3.3-9).  Verdict = k92_gates.f_judge of the k92t tree (function
text unchanged since K9-2-0; the file blob changed in K9-2-4 / K9-2-5): F-1, F-2, F-3 all true, n = 22 -> PASS; any
false -> FAIL (STOP_ASK_F); any missing -> INCOMPLETE.  Reports: the same at T+150, the W arm, per-state table,
persistence MAE, f_judge's bootstrap, OUTW / FEED-4 / SC109_E_out max / 220, capacity-bound step share,
k92_hb_seed_binding counts, the P0-4 exposure-excluded versions (raw list and effective list), the second sample
(v3c3-s31 / s43, 16, "partly exposed").

Persistence report (amendment 30 section 2, D-K9-56; report only, never part of the verdict).  Persistence error of
a primary state T = VISSIM M1 at T (= m1_T450 of the VR state T-450 in root OUTK/f_persist30, frame T+0.1) minus
VISSIM M1 at T+450 (= m1_T450 of the state T in F_VREF).  The U4 measurer behind the VR keeps a window (a, b] only
when a >= T_FROM = 900 (k8b/u4/derive_head_saturation.py:72, :379), so a state T with T - 450 < 900 is labelled
PERSIST_LABEL = 'not measurable (T_FROM=900)' (report text '측정 불가(T_FROM=900)') and is not asked from the VR:
of the 22 primary states that is T = 1050 only; the other 21 are measured (VR states 1200 ... 7950).  The report
holds n, the MAE, the measured state list, the labelled states, the 15 states where the VR state T-450 is itself a
primary state (its m1_T450 must equal the F_VREF value: same FZP frame) and 'complete' = the persist file has the
seed s47 network identity 1895ca30..., exactly the 21 declared VR states, every one with an integer m1_T450, the 15
overlaps equal, and the OFF-arm VISSIM side present for the 21.  'complete' false -> the driver STOPs after the F
judge file is written (amendment 30 S-K43); the verdict fields are not changed by it.

Job counts (amendment 30 section 4.2, D-K9-57 5): per arm and sample group (s47 primary 22, s31 8, s43 8) the number
of job folders, of summary.json with ok true, of k92_record.json present, of records with an empty errors list, and
of captures with capture.json ok; counts only (no value)."""
import argparse
import hashlib
import json
import math
import os
import re
import statistics
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
KB = HERE.parent
OK2 = Path(r'D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1')
OUTK = OK2 / 'k92t'
SEALED = OK2 / 'sealed_s47'
V4 = Path(r'D:/VISSIM-merge/k8_gates_out_v4')
K91T_TREE = Path(r'D:/VISSIM-merge/k8_gate_trees/k91t')
KPA = KB / 'k92_probe_a25'
SA_REL = 'diagnostics/sdmpc_n31_20260924/k8_gates/sa'
GATES_K91T = V4 / 'sa' / 'gates' / 'gates_k91t.json'
GATES_K91T_SHA = '4e59f61d6d1b18ad588e95eaf6f215f44f6c66c981921735073d91f1c6c59b9f'
JB_GATES = ('G-EB-2', 'G-EB-3', 'G-EB-4', 'G-EB-5', 'G-EB-6', 'G-EB-7', 'G-EB-8', 'G-EB-13', 'G-EB-14')
GRID9 = (900, 1200, 1800, 2250, 2700, 3000, 3600, 4200, 4950)
DP_T = tuple(900 + 450 * k for k in range(17))
ROBS61_T = (1,) + tuple(range(150, 9001, 150))
F_PRIMARY = (1050, 1650, 1950, 2400, 3300, 3750, 3900, 4650, 5100, 5550, 6000, 6150, 6450, 6600, 6900, 7050, 7350,
             7500, 7800, 7950, 8250, 8400)
F_SECOND = {31: (1500, 2850, 3900, 5250, 6000, 6600, 7500, 8250), 43: (1050, 3300, 4800, 5550, 6450, 7050, 7800, 8400)}
INPX_RAW = {47: '1895ca30542cd50542a9376d5e3c77ff184d65a009d97dbe55a65f0b31bbced0',
            31: '3de889f0257d998bed50611f798ea388bcf69396dbc40e5726b1e88ebdd31c2e',
            43: '51478c397b3a2570fc2254a9fa8120a2415304942589f5fb5c2eb1b6858f2dda'}
W_KEY = 'SC109_W_SC108_to_E'
L_KEY = 'SC109_W_SC108_to_N_SC16'
W_REPR = '5209.8'
SEED_REPR = '1045.1612903225805'
META7 = ('k8b_p1', 'k8b_p2', 'k8b_p2_init', 'k8b_p4', 'k9_w1', 'k9_w2a', 'k9_f17b')
K92_META = ('k92_w', 'k92_hb', 'k92_hb_seed_binding')
WALL_LIMIT = 1.05 / 1.033718118959995
PAIR_LABELS = (['TL3_%d_SAF_OBS_H3' % T for T in GRID9]
               + ['TL3_900_s43_SAF_OBS_H3', 'TL3_900_s47_SAF_OBS_H3'])
JA_JOBS = (['TL3_%d_SAF_OBS_H3' % T for T in GRID9]
           + [lab % arm for arm in ('SAF', 'BASE') for lab in
              ('TL3_900_s43_%s_OBS_H3', 'TL3_900_s47_%s_OBS_H3', 'TL3_2700_%s_OBS_H42', 'TL3_4950_%s_OBS_H27',
               'TL3_900_%s_OBS_H3_C11', 'TL3_900_%s_OBS_H3_TAN_ad')])
JA_FULL = ('002700_SAF_hooks', '002700_BASE_hooks')
# P0-4 exposure records (KPA/p0, pinned in K92_VALUES.json 296c6595...)
P0_4_SAMPLES = KPA / 'p0' / 'p0_4_samples.json'
P0_4_SAMPLES_SHA = '1851f6cc92f9a339d4bfbb0b9dcd15ea715634a8ba9f8b5e1aa11c5560bc30c3'
P0_4_REVIEW = KPA / 'p0' / 'p0_4_exposure_review.json'
P0_4_REVIEW_SHA = '21fd54e7ce3bf50719339cd0ba1d56f935eb6c9c41d59e3e2b7d618f324fba74'
# amendment 25 section 6.5-4 (fixed rule text)
NAME_RE = re.compile(r'_s47_|s47_|_s47(?![0-9A-Za-z])')
VALUE_RE = re.compile(r'objective=[^\s`<]*\d|continuous_scalar\w*[\s=:]+[^\s`<]*\d')
SAJOB_RE = re.compile(r'SA_JOB [^\s`<]*(?:_s47_|s47_|_s47(?![0-9A-Za-z]))')
TEXT = ('.txt', '.log', '.jsonl', '.md')
VR_TOKENS = (b'"m1_T150"', b'"m1_T450"', b'"m2_T150"', b'"m2_T450"', b'"m3_T150"', b'"m3_T450"', b'"m1_by_link_T',
             b'"m2_by_head_T', b'"m3_by_head_T')
# amendment 30 section 2 (D-K9-56): the persistence report
PERSIST_NAME = 'f_persist30'
T_FROM_U4 = 900
PERSIST_LABEL = 'not measurable (T_FROM=900)'
PERSIST_LABEL_KO = '측정 불가(T_FROM=900)'
PERSIST_MEASURED = tuple(T for T in F_PRIMARY if T - 450 >= T_FROM_U4)
PERSIST_NOT = tuple(T for T in F_PRIMARY if T - 450 < T_FROM_U4)
PERSIST_VR_STATES = tuple(T - 450 for T in PERSIST_MEASURED)
PERSIST_OVERLAP = tuple(t for t in PERSIST_VR_STATES if t in F_PRIMARY)


def sha_file(p):
    h = hashlib.sha256()
    with open(lp(p), 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def lp(p):
    s = os.path.abspath(str(p))
    return s if s.startswith('\\\\?\\') else '\\\\?\\' + s


def read_json(p, default=None):
    try:
        return json.loads(Path(lp(p)).read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        return default


def write_json(p, obj):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(p) + '.tmp')
    tmp.write_text(json.dumps(obj, indent=1, default=str, ensure_ascii=False, allow_nan=True), encoding='utf-8')
    os.replace(tmp, p)


def canon(x):
    return json.dumps(x, sort_keys=True, allow_nan=True, default=repr)


# ================================================================================================ start scans
def scan_sealed():
    """Amendment 25 section 6.5 items 3 and 5: every sealed file re-hashed = its index; file set = index set; the
    number of runs = the index count.  Names, sizes and sha only."""
    out, ok = {}, True
    tops = sorted(d.name for d in SEALED.iterdir()) if SEALED.is_dir() else []
    out['top'] = tops
    want_tops = ['K9-2-0', 'K9-2-1', 'K9-2-2', 'K9-2-3', 'a27']
    if tops != want_tops:
        ok = False
        out['top_problem'] = 'sealed root folders %s != %s' % (tops, want_tops)
    for commit in ('K9-2-0', 'K9-2-1', 'K9-2-2', 'K9-2-3'):
        idx_path = OK2 / 'commit' / commit / 'sealed_s47_index.json'
        idx = read_json(idx_path)
        row = {'index': str(idx_path), 'index_sha256': sha_file(idx_path) if idx_path.is_file() else None}
        if not isinstance(idx, dict):
            row['problem'] = 'index missing'
            ok = False
            out[commit] = row
            continue
        inv = idx.get('inventory') or {}
        root = SEALED / commit
        have = {}
        for base, dirs, names in os.walk(lp(root)):
            for n in names:
                full = os.path.join(base, n)
                have[os.path.relpath(full, lp(root)).replace('\\', '/')] = full
        missing = sorted(set(inv) - set(have))
        extra = sorted(set(have) - set(inv))
        bad = []
        for rel in sorted(set(inv) & set(have)):
            want = inv[rel]
            size, sha = want[0], want[-1]
            st = os.stat(have[rel])
            if st.st_size != size or sha_file(have[rel]) != sha:
                bad.append(rel)
        runs = idx.get('runs') or []
        stdout_missing = [r.get('stdout_file') for r in runs if r.get('stdout_file') not in inv]
        row.update(n_inventory=len(inv), n_files=len(have), missing=missing[:20], n_missing=len(missing),
                   extra=extra[:20], n_extra=len(extra), changed=bad[:20], n_changed=len(bad),
                   n_runs=idx.get('n_runs'), runs_listed=len(runs), stdout_missing=stdout_missing,
                   runs_rc=[r.get('rc') for r in runs])
        if missing or extra or bad or idx.get('n_runs') != len(runs) or stdout_missing:
            ok = False
        out[commit] = row
    idx_path = OK2 / 'a27' / 'sealed_index.json'
    idx = read_json(idx_path) or {}
    runs = idx.get('runs') or []
    root = SEALED / 'a27'
    have = {}
    for base, dirs, names in os.walk(lp(root)):
        for n in names:
            full = os.path.join(base, n)
            have[os.path.relpath(full, lp(root)).replace('\\', '/')] = full
    want = {'logs/' + r.get('stdout_file', ''): r.get('size') for r in runs}
    row = {'index': str(idx_path), 'index_sha256': sha_file(idx_path) if idx_path.is_file() else None,
           'runs': len(runs), 'files': sorted(have), 'sizes_equal': all(
               rel in have and os.stat(have[rel]).st_size == size for rel, size in want.items()),
           'set_equal': set(want) == set(have),
           'sha256': {rel: sha_file(p) for rel, p in have.items()}}
    if not runs or not row['sizes_equal'] or not row['set_equal']:
        ok = False
    out['a27'] = row
    out['ok'] = ok
    return out


def _scan_lines(path):
    n = 0
    with open(lp(path), 'rb') as f:
        for raw in f:
            line = raw.decode('utf-8', 'replace')
            if NAME_RE.search(line) and (VALUE_RE.search(line) or SAJOB_RE.search(line)):
                n += 1
    return n


def scan_leak(extra_roots=()):
    """Amendment 25 section 6.5-4: the declared non-sealed record files; a leak line = a v3c3-s47 job-name form
    together with a value form or a job-line form.  File names and line counts only."""
    declared = [(OK2 / 'commit', TEXT + ('.json',)), (OK2 / 'probe', TEXT), (OK2 / 'probe_a25', TEXT),
                (OK2 / 'logs', TEXT), (KB, TEXT)]
    res = {'declared': {}, 'report_only': {}}
    for key, roots in (('declared', declared), ('report_only', [(r, TEXT + ('.json',)) for r in extra_roots])):
        files, hits = 0, {}
        for root, exts in roots:
            if not Path(root).exists():
                continue
            for base, dirs, names in os.walk(lp(root)):
                for n in names:
                    if os.path.splitext(n)[1].lower() not in exts:
                        continue
                    full = os.path.join(base, n)
                    files += 1
                    k = _scan_lines(full)
                    if k:
                        hits[full.replace('\\\\?\\', '')] = k
        res[key] = {'files_scanned': files, 'files_with_leak_lines': len(hits),
                    'leak_lines': sum(hits.values()), 'files': sorted(hits)[:50]}
    # positive / negative controls of the rule (synthetic strings only)
    ctrl = {'SA_JOB TL3_2400_s47 exit=0 wall=12.0 ok=True objective=4711.25': True,
            'continuous_scalar_done 4711.2 job_s47_x': True,
            'k92t scan: `_s47_` with `objective=` / `continuous_scalar` / `SA_JOB `': False,
            'SA_JOB x_s47 objective=np.float64(4711.2)': True,
            'SA_JOB TL3_2400_s47 exit=1 wall=3.0 ok=False objective=None': True}
    res['controls_ok'] = all(bool(NAME_RE.search(s) and (VALUE_RE.search(s) or SAJOB_RE.search(s))) == want
                             for s, want in ctrl.items())
    res['ok'] = res['declared']['leak_lines'] == 0 and res['controls_ok']
    return res


def _seed47_path(path):
    """Amendment 31 (D-K9-58): an s47 piece is a path piece p (lower case) with p == 's47', p ending in '_s47',
    '_s47_' in p, or p starting with 's47_' (the amendment-30 piece rule, unchanged).  A path at or under the sealed
    root SEALED is read by its pieces RELATIVE to SEALED: the sealed root's own name ('sealed_s47') and every piece
    above it are not pieces of that path; a deeper piece of the same name still counts.  Any other path is read by
    all its pieces, as in amendment 30.  The long-path prefix \\\\?\\ is dropped first; the prefix test is
    case-insensitive (os.path.normcase) and needs a separator after the root."""
    s = str(path)
    if s.startswith('\\\\?\\'):
        s = s[4:]
    full = os.path.normcase(os.path.abspath(s))
    root = os.path.normcase(os.path.abspath(str(SEALED))).rstrip('\\/')
    if full == root:
        s = ''
    elif full.startswith(root + os.sep):
        s = full[len(root) + 1:]
    parts = [p.lower() for p in re.split(r'[\\/]', s)]
    return any(p == 's47' or p.endswith('_s47') or '_s47_' in p or p.startswith('s47_') for p in parts)


def scan_vissim_blind(sealed=False):
    """Amendment 24 section 3.1-3b + amendment 25 sections 6.5 / 8.2: no v3c3-s47 K9-2 VISSIM reference value in
    OK2/probe, OK2/commit, KB/k92_probe, OK2/probe_a25, KB/k92_probe_a25.  The sealed root part (k92_record.json files
    only: VISSIM side null with reason k92_blind_s47) runs only with sealed=True, i.e. after the J / F judge values
    are fixed in the LOG (amendment 29 section 5: nobody parses a sealed data file before that; the start check
    re-hashes every sealed file instead, so their bytes are those of the commit gates).  File names and counts only."""
    roots = [OK2 / 'probe', OK2 / 'commit', KB / 'k92_probe', OK2 / 'probe_a25', KB / 'k92_probe_a25']
    if sealed:
        roots = []
    bad, notes = [], {'vissim_ref_files': 0, 'record_files': 0, 'record_s47': 0, 'json_with_vr_tokens': 0,
                      'json_scanned': 0}
    for root in roots:
        if not root.exists():
            continue
        for base, dirs, names in os.walk(lp(root)):
            for n in names:
                if not n.lower().endswith('.json'):
                    continue
                full = os.path.join(base, n)
                shown = full.replace('\\\\?\\', '')
                notes['json_scanned'] += 1
                if n == 'k92_vissim_ref.json':
                    notes['vissim_ref_files'] += 1
                    d = read_json(full) or {}
                    s47 = ((d.get('seeds') or {}).get('s47'))
                    if s47 is not None:
                        extra = sorted(k for k in s47 if k != 'states')
                        states = s47.get('states') or {}
                        nonnull = [T for T, v in states.items()
                                   if not (isinstance(v, dict) and set(v) == {'value', 'reason'}
                                           and v.get('value') is None and v.get('reason') == 'k92_blind_s47')]
                        if extra or nonnull:
                            bad.append([shown, 's47 entry not blind', len(nonnull), extra])
                    continue
                if n == 'k92_record.json':
                    notes['record_files'] += 1
                    d = read_json(full) or {}
                    if str(d.get('seed')) == '47' or _seed47_path(full):
                        notes['record_s47'] += 1
                        if d.get('vissim') is not None or d.get('vissim_reason') != 'k92_blind_s47':
                            bad.append([shown, 's47 record VISSIM side not blind'])
                    continue
                try:
                    with open(full, 'rb') as f:
                        data = f.read()
                except OSError:
                    continue
                if any(t in data for t in VR_TOKENS):
                    notes['json_with_vr_tokens'] += 1
                    if _seed47_path(full) or b'"s47"' in data:
                        bad.append([shown, 'VR key names in a file with an s47 context'])
    sealed_rec = {'files': 0, 's47': 0, 'bad': 0, 'ran': bool(sealed)}
    for base, dirs, names in (os.walk(lp(SEALED)) if sealed else ()):
        for n in names:
            if n != 'k92_record.json':
                continue
            full = os.path.join(base, n)
            sealed_rec['files'] += 1
            d = read_json(full) or {}
            if str(d.get('seed')) == '47' or _seed47_path(full):
                sealed_rec['s47'] += 1
                if d.get('vissim') is not None or d.get('vissim_reason') != 'k92_blind_s47':
                    sealed_rec['bad'] += 1
                    bad.append([full.replace('\\\\?\\', ''), 'sealed s47 record VISSIM side not blind'])
    return {'ok': not bad, 'bad': bad[:50], 'n_bad': len(bad), 'notes': notes, 'sealed_records': sealed_rec}


def scan_primary_absent():
    """S-K10: no output of an F primary-sample state (v3c3-s47, 22) exists before k92t: capture folders
    <harness>/<T:06d>_s47... and job labels <H>_<T>_s47_... under OK2 (k92t excluded) and TK.  Names only."""
    pats = [re.compile(r'(?:^|[\\/])0*%d_s47(?:[\\/_]|$)' % T) for T in F_PRIMARY]
    labs = [re.compile(r'(?:^|[\\/])[A-Z0-9]+_%d_s47_' % T) for T in F_PRIMARY]
    hits, n = [], 0
    for root in (OK2, Path(r'D:/VISSIM-merge/k8_gate_trees/k92b1')):
        for base, dirs, names in os.walk(lp(root)):
            rel = base.replace('\\\\?\\', '')
            if Path(rel).resolve() == OUTK.resolve() or str(Path(rel).resolve()).startswith(str(OUTK.resolve())):
                dirs[:] = []
                continue
            for d in dirs + names:
                n += 1
                p = os.path.join(rel, d)
                if any(r.search(p) for r in pats) or any(r.search(p) for r in labs):
                    hits.append(p)
    return {'ok': not hits, 'n_names': n, 'hits': hits[:50], 'n_hits': len(hits)}


def cmd_sealedscan(args):
    """After the J / F judge files are fixed in the LOG: the sealed-root part of the section 3.1-3b scan."""
    res = scan_vissim_blind(sealed=True)
    res['when'] = time.strftime('%Y-%m-%dT%H:%M:%S')
    write_json(args.dest, res)
    print('K92T_SEALEDSCAN ok=%s files=%s s47=%s bad=%s' % (res['ok'], res['sealed_records']['files'],
                                                           res['sealed_records']['s47'], res['sealed_records']['bad']))
    return 0 if res['ok'] else 3


def cmd_scans(args):
    t0 = time.time()
    res = {'schema': 'k92t-start-scans/v1', 'when': time.strftime('%Y-%m-%dT%H:%M:%S'),
           'sealed': scan_sealed(), 'leak': scan_leak(extra_roots=(OK2 / 'a27', OK2 / 'a29')),
           'vissim_blind': scan_vissim_blind(), 'primary_absent': scan_primary_absent()}
    res['ok'] = all(res[k]['ok'] for k in ('sealed', 'leak', 'vissim_blind', 'primary_absent'))
    res['sec'] = round(time.time() - t0, 1)
    write_json(args.dest, res)
    print('K92T_SCANS ok=%s sealed=%s leak=%s blind=%s primary=%s' % (
        res['ok'], res['sealed']['ok'], res['leak']['ok'], res['vissim_blind']['ok'], res['primary_absent']['ok']))
    return 0 if res['ok'] else 3


# ================================================================================================ harness (child)
def harness(tree):
    sa = Path(tree) / SA_REL
    if str(sa) not in sys.path:
        sys.path.insert(0, str(sa))
    import sa_common as sc
    import k8b_commit_gates as cg
    return sc, cg


def _cap_rec(d):
    ok = read_json(Path(d) / 'capture.json')
    if isinstance(ok, dict):
        return ok, 'ok' if ok.get('ok') is not False else 'failed'
    fail = read_json(Path(d) / 'capture_failed.json')
    if isinstance(fail, dict):
        return fail, 'failed'
    return None, 'missing'


def _signature(sc, d, T, rec):
    import sa_errors
    p = Path(d) / ('action_%06d.error.txt' % int(T))
    text = p.read_text(encoding='utf-8', errors='replace') if p.is_file() else (rec or {}).get('error')
    return sa_errors.traceback_signature(text)


def _sa_state(rec):
    md = rec.get('metadata') or {}
    pr = rec.get('probes') or {}
    return {'install_check': md.get('stopline_approach_install_check'),
            'initial': md.get('stopline_approach_initial'),
            'sa': pr.get('sa'), 'ports': pr.get('ports'), 'records': pr.get('records'),
            'provenance_127': (pr.get('provenance') or {}).get('127'),
            'occupancy_SC1001_W_out': (pr.get('occupancy') or {}).get('SC1001_W_out')}


def _caps(cg, tree, cap_dir):
    tpl = cg.load_template(tree, Path(cap_dir) / 'template.pickle')
    caps = tpl['owned'][0].cfg.network.movement_capacity_by_movement_veh_h
    return {str(k): (float(getattr(v, 'value', v)) if v is not None else None) for k, v in dict(caps).items()}


def _leaf_paths(a, b, path=''):
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b), key=str):
            if k not in a or k not in b:
                out.append(path + '/' + str(k) + ' (one side)')
            else:
                out += _leaf_paths(a[k], b[k], path + '/' + str(k))
    elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for i, (x, y) in enumerate(zip(a, b)):
            out += _leaf_paths(x, y, path + '[%d]' % i)
    elif canon(a) != canon(b):
        out.append(path)
    return out


def j0_state(sc, cg, tree, d_off, d_on, harness_name, T):
    r_off, k_off = _cap_rec(d_off)
    r_on, k_on = _cap_rec(d_on)
    row = {'outcome': [k_off, k_on]}
    if 'missing' in (k_off, k_on):
        row['verdict'] = 'INCOMPLETE'
        return row
    if k_off == 'failed' or k_on == 'failed':
        if k_off == k_on == 'failed' and harness_name == 'ROBS61' and int(T) in (1, 150):
            a, b = _signature(sc, d_off, T, r_off), _signature(sc, d_on, T, r_on)
            same = a is not None and a == b and bool(a[1])
            row.update(identical_failure=same, exception=(a or [''])[0][:200] if a else None)
            row['verdict'] = 'PASS' if same else 'FAIL'
            row['init_count'] = 'identical_failure' if same else 'failure'
        else:
            row['verdict'] = 'FAIL'
        return row
    md_off, md_on = r_off.get('metadata') or {}, r_on.get('metadata') or {}
    row['meta7'] = {k: canon(md_off.get(k)) == canon(md_on.get(k)) for k in META7}
    row['meta7_present'] = {k: [k in md_off, k in md_on] for k in META7}
    so, sn = _sa_state(r_off), _sa_state(r_on)
    row['sa_state'] = {k: canon(so[k]) == canon(sn[k]) for k in so}
    ic_off, ic_on = so['install_check'] or {}, sn['install_check'] or {}
    row['init'] = [bool(ic_off) and ic_off.get('passed') is True, bool(ic_on) and ic_on.get('passed') is True]
    try:
        c0, c1 = _caps(cg, tree, d_off), _caps(cg, tree, d_on)
        diff = sorted(k for k in set(c0) | set(c1) if canon(c0.get(k)) != canon(c1.get(k)))
        want = {W_KEY}
        l_off = c0.get(L_KEY)
        if l_off is not None and l_off < float(SEED_REPR):
            want.add(L_KEY)
        cap_ok = (set(diff) == want and repr(c1.get(W_KEY)) == W_REPR
                  and (L_KEY not in want or repr(c1.get(L_KEY)) == SEED_REPR))
        row['capacity'] = {'differing': diff, 'expected': sorted(want), 'ok': cap_ok,
                           'w_new_repr_ok': repr(c1.get(W_KEY)) == W_REPR,
                           'l_bound_by_seed': L_KEY in want}
    except Exception as exc:  # noqa: BLE001
        row['capacity'] = {'ok': None, 'error': repr(exc)[:300]}
    one_off = sorted(k for k in md_off if k not in md_on)
    one_on = sorted(k for k in md_on if k not in md_off)
    row['meta_one_sided'] = {'off_only': one_off, 'on_only': one_on,
                             'on_only_declared': all(k in K92_META for k in one_on) and not one_off}
    skip = {'/tuning', '/tree', '/template_sha256', '/capture_wall_sec', '/metadata/k92_w', '/metadata/k92_hb',
            '/metadata/k92_hb_seed_binding'}
    other = [p for p in _leaf_paths(r_off, r_on) if not any(p == s or p.startswith(s + '/') or
                                                            p.startswith(s + ' ') for s in skip)]
    row['report_other_differing'] = other[:30]
    row['report_other_differing_n'] = len(other)
    good = (all(row['meta7'].values()) and all(row['sa_state'].values()) and row['init'][0] == row['init'][1]
            and row['init'][1] is True and row['capacity'].get('ok') is True)
    if row['capacity'].get('ok') is None:
        row['verdict'] = 'INCOMPLETE'
    else:
        row['verdict'] = 'PASS' if good else 'FAIL'
    row['init_count'] = 'initialized' if row['init'][1] else 'not_initialized'
    return row


def cmd_j0(args):
    tree = Path(args.tree)
    sc, cg = harness(tree)
    ja, jb = Path(args.ja), Path(args.jb)
    label = args.label

    def cdir(root, harness_name, T, seed):
        rel = sc.cap_dir(label, harness_name, T, 'SAF', seed=seed).relative_to(sc.sa_out())
        return root / 'sa' / rel
    states = ([('TL3', T, s) for s in (31, 43, 47) for T in GRID9] + [('DP', T, None) for T in DP_T]
              + [('ROBS61', T, 31) for T in ROBS61_T])
    rows, verdicts = {}, []
    for h, T, s in states:
        key = '%s_%d%s' % (h, T, '' if s in (None, 31) else '_s%d' % s)
        r = j0_state(sc, cg, tree, cdir(ja, h, T, s), cdir(jb, h, T, s), h, T)
        rows[key] = r
        verdicts.append(r['verdict'])
    robs = [rows['ROBS61_%d' % T] for T in ROBS61_T]
    init61 = {'initialized': sum(1 for r in robs if r.get('init_count') == 'initialized'),
              'identical_failure': sum(1 for r in robs if r.get('init_count') == 'identical_failure')}
    init61['count'] = init61['initialized'] + init61['identical_failure']
    if 'INCOMPLETE' in verdicts or len(rows) != 105:
        v = 'INCOMPLETE'
    elif all(x == 'PASS' for x in verdicts) and init61['count'] == 61:
        v = 'PASS'
    else:
        v = 'FAIL'
    res = {'schema': 'k92t-j0/v1', 'verdict': v, 'n_states': len(rows),
           'counts': {x: verdicts.count(x) for x in ('PASS', 'FAIL', 'INCOMPLETE')},
           'robs61_init_61': init61, 'seed_bound_states': sorted(k for k, r in rows.items()
                                                              if (r.get('capacity') or {}).get('l_bound_by_seed')),
           'failed_states': sorted(k for k, r in rows.items() if r['verdict'] != 'PASS'),
           'rows': rows, 'ja': str(ja), 'jb': str(jb), 'tree': str(tree), 'label': label}
    write_json(args.dest, res)
    print('K92T_J0 %s n=%d counts=%s init61=%s' % (v, len(rows), res['counts'], init61))
    return 0


def _numeric_same(cg, a, b, roots):
    r = cg.compare_g5(a, b, roots, renamed=(), allowed_one_sided=())
    na, _ = cg.leaves(a)
    nb, _ = cg.leaves(b)

    def excl(key):
        k = key.lower()
        return any(s in k for s in cg.SKIP) or any(e.lower() in k for e in cg.G5_EXCLUDE)
    one = sorted(k for k in set(na) ^ set(nb) if not excl(k))
    same = r['numeric_differ'] == 0 and not one
    return same, {'numeric_common': r['numeric_common'], 'numeric_differ': r['numeric_differ'],
                  'numeric_examples': [x[0] for x in r['examples']], 'numeric_one_sided': one[:20],
                  'string_differ': r['string_differ'], 'string_examples': [x[0] for x in r['string_examples']],
                  'hash_strings_differ': [x[0] for x in r['hash_strings_differ']],
                  'n_path_strings_differ': r['n_path_strings_differ']}


def cmd_ja(args):
    tree = Path(args.tree)
    sc, cg = harness(tree)
    import k92_compare as k92cmp
    ja = Path(args.ja)
    roots = [str(tree), str(K91T_TREE), str(ja), str(V4)]
    rows, ok_all, incomplete = {}, True, False
    for lab in JA_JOBS:
        old = read_json(V4 / 'sa' / 'jobs' / 'k91t' / lab / 'summary.json')
        new = read_json(ja / 'sa' / 'jobs' / args.label / lab / 'summary.json')
        if old is None or new is None:
            rows[lab] = {'verdict': 'INCOMPLETE', 'present': [old is not None, new is not None]}
            incomplete = True
            continue
        same, det = _numeric_same(cg, old, new, roots)
        det['ok'] = [old.get('ok'), new.get('ok')]
        det['verdict'] = 'SAME' if same and new.get('ok') is True else 'DIFF'
        rows[lab] = det
        ok_all &= det['verdict'] == 'SAME'
    for name in JA_FULL:
        od = V4 / 'sa' / 'full' / 'k91t' / name
        nd = ja / 'sa' / 'full' / args.label / name
        T = int(name.split('_')[0])
        rep = k92cmp.compare(str(od), str(nd), T, str(tree), keyed=None, old_root=str(K91T_TREE), label=name)
        ro, rn = read_json(od / 'run.json') or {}, read_json(nd / 'run.json') or {}
        row = {k: rep.get(k) for k in ('verdict', 'hard_verdict', 'unclassified_n', 'unclassified', 'allowed_counts',
                                        'r3_checks', 'k92_checks', 'why', 'json_sha256')}
        row['run_json'] = {k: [ro.get(k), rn.get(k)] for k in ('exit',)}
        row['run_json_equal'] = {k: canon(ro.get(k)) == canon(rn.get(k)) for k in ('objective', 'held_objective',
                                                                                   'exit', 'csv_sha256')}
        rows[name] = row
        if rep.get('verdict') == 'INCOMPLETE':
            incomplete = True
        ok_all &= rep.get('verdict') == 'PASS'
    v = 'INCOMPLETE' if incomplete else ('PASS' if ok_all else 'FAIL')
    res = {'schema': 'k92t-ja/v1', 'verdict': v, 'n_items': len(rows), 'rows': rows,
           'failed': sorted(k for k, r in rows.items() if r.get('verdict') not in ('SAME', 'PASS')),
           'old_root_decisions': str(K91T_TREE), 'roots': roots}
    write_json(args.dest, res)
    print('K92T_JA %s n=%d failed=%s' % (v, len(rows), res['failed']))
    return 0


def cmd_jwall(args):
    ja, jb = Path(args.ja), Path(args.jb)
    rows = []
    for lab in PAIR_LABELS:
        a_dir = ja / 'sa' / 'jobs' / args.label / lab
        b_dir = jb / 'sa' / 'jobs' / args.label / lab
        sa_, sb = read_json(a_dir / 'summary.json') or {}, read_json(b_dir / 'summary.json') or {}
        va, vb = read_json(a_dir / 'vissim_counts.json') or {}, read_json(b_dir / 'vissim_counts.json') or {}
        counts = [va.get('vissim_count_pre'), va.get('vissim_count_post'), vb.get('vissim_count_pre'),
                  vb.get('vissim_count_post')]
        clean = all(x == 0 for x in counts)
        wa, wb = sa_.get('wall_sec'), sb.get('wall_sec')
        rows.append({'label': lab, 'wall_A': wa, 'wall_B': wb, 'counts': counts, 'clean': clean,
                     'order_A_then_B': (va.get('end') is not None and vb.get('start') is not None
                                        and va['end'] <= vb['start']),
                     'ratio': (wb / wa) if (wa and wb) else None, 'ok': [sa_.get('ok'), sb.get('ok')]})
    ratios = [r['ratio'] for r in rows if r['clean'] and r['ratio'] is not None]
    if not ratios:
        v, med, iqr = 'INCOMPLETE', None, None
    else:
        med = statistics.median(ratios)
        q = statistics.quantiles(ratios, n=4, method='inclusive') if len(ratios) > 1 else [ratios[0]] * 3
        iqr = q[2] - q[0]
        v = 'PASS' if med <= WALL_LIMIT else 'FAIL'
    res = {'schema': 'k92t-jwall/v1', 'verdict': v, 'n_pairs': len(rows), 'n_clean': len(ratios), 'median': med,
           'limit': WALL_LIMIT, 'iqr_inclusive_report_only': iqr, 'rows': rows}
    write_json(args.dest, res)
    print('K92T_JWALL %s clean=%d/%d median=%s' % (v, len(ratios), len(rows), med))
    return 0


def judged_items(doc):
    out = {}
    for gid in JB_GATES:
        g = ((doc or {}).get('gates') or {}).get(gid) or {}
        for k, it in (g.get('items') or {}).items():
            out[(gid, k)] = it
    return out


def cmd_jb(args):
    if sha_file(GATES_K91T) != GATES_K91T_SHA:
        raise SystemExit('gates_k91t.json sha differs')
    old = read_json(GATES_K91T)
    new = read_json(args.new)
    if new is None:
        res = {'schema': 'k92t-jb/v1', 'verdict': 'INCOMPLETE', 'why': 'new gates file missing: %s' % args.new}
        write_json(args.dest, res)
        print('K92T_JB INCOMPLETE')
        return 0
    oi, ni = judged_items(old), judged_items(new)
    judged = sorted(k for k, it in oi.items() if it.get('pass_') is not None)
    rows, diff = [], []
    for key in judged:
        o, n = oi[key], ni.get(key)
        same = n is not None and canon(o.get('value')) == canon(n.get('value'))
        row = {'gate': key[0], 'item': key[1], 'present': n is not None, 'same': same,
               'pass_old': o.get('pass_'), 'pass_new': None if n is None else n.get('pass_'),
               'judged_old': o.get('judged'), 'judged_new': None if n is None else n.get('judged')}
        if not same:
            row['old_value'] = o.get('value')
            row['new_value'] = None if n is None else n.get('value')
            diff.append(key)
        rows.append(row)
    gates_present = sorted(g for g in JB_GATES if g in ((new.get('gates') or {})))
    verdicts = {g: ((new.get('gates') or {}).get(g) or {}).get('verdict') for g in JB_GATES}
    old_verdicts = {g: ((old.get('gates') or {}).get(g) or {}).get('verdict') for g in JB_GATES}
    if len(gates_present) != len(JB_GATES):
        v = 'INCOMPLETE'
    else:
        v = 'PASS' if not diff else 'DIFF'
    res = {'schema': 'k92t-jb/v1', 'verdict': v, 'n_judged_items': len(judged), 'n_same': len(judged) - len(diff),
           'differing': ['%s/%s' % k for k in diff], 'gate_verdicts_new': verdicts, 'gate_verdicts_k91t': old_verdicts,
           'new_missing_inputs': new.get('missing_inputs'), 'new_file': str(args.new),
           'new_sha256': sha_file(args.new), 'old_file': str(GATES_K91T), 'old_sha256': GATES_K91T_SHA, 'rows': rows}
    write_json(args.dest, res)
    print('K92T_JB %s judged=%d same=%d differing=%s' % (v, len(judged), len(judged) - len(diff), res['differing']))
    return 0


# ================================================================================================ F
def _rec(root, label, lab):
    return read_json(Path(root) / 'sa' / 'jobs' / label / lab / 'k92_record.json')


def _cap_meta(root, label, T, seed):
    tag = '%06d' % T + ('' if seed == 31 else '_s%d' % seed)
    return (read_json(Path(root) / 'sa' / 'cap' / label / 'TL3' / tag / 'SAF' / 'capture.json') or {}).get(
        'metadata') or {}


def _lab(seed, T):
    return 'TL3_%d%s_SAF_OBS_H3' % (T, '' if seed == 31 else '_s%d' % seed)


def f_rows(root, label, vref, seed, Ts):
    rows, info, missing = {}, {}, []
    for T in Ts:
        rec = _rec(root, label, _lab(seed, T))
        summ = read_json(Path(root) / 'sa' / 'jobs' / label / _lab(seed, T) / 'summary.json') or {}
        vs = (((vref.get('seeds') or {}).get('s%d' % seed) or {}).get('states') or {}).get(str(T))
        if not rec or not vs or vs.get('m1_T450') is None or summ.get('ok') is not True or rec.get('errors'):
            missing.append(T)
            continue
        hz = rec.get('horizon') or {}
        rows[T] = {'M1_450': (hz.get('m1_chain_T450'), vs.get('m1_T450')),
                   'M2_450': (hz.get('m2_w_dep_T450'), vs.get('m2_T450')),
                   'M3_450': (hz.get('m3_l_dep_T450'), vs.get('m3_T450')),
                   'M1_150': (hz.get('m1_chain_T150'), vs.get('m1_T150')),
                   'M2_150': (hz.get('m2_w_dep_T150'), vs.get('m2_T150')),
                   'M3_150': (hz.get('m3_l_dep_T150'), vs.get('m3_T150'))}
        bound, steps = hz.get('w_capacity_bound_steps'), hz.get('w_steps_with_departures')
        info[T] = {'outw_veh_h_450': hz.get('outw_veh_h_450'), 'feed4_veh_h_450': hz.get('feed4_veh_h_450'),
                   'e_out_max_over_220': hz.get('e_out_max_over_220'),
                   'w_capacity_bound_share': (bound / steps) if (bound is not None and steps) else None,
                   'w_receiving_limited_steps': hz.get('w_receiving_limited_steps'),
                   'phantom_end_450': hz.get('phantom_end_450'),
                   'k92_errors': len(rec.get('errors') or []),
                   'seed_binding_capture': _cap_meta(root, label, T, seed).get('k92_hb_seed_binding')}
        if any(v is None for pair in rows[T].values() for v in pair):
            missing.append(T)
    return rows, info, missing


def as450(rows, suffix):
    return {s: {'M1_450': r['M1_' + suffix], 'M2_450': r['M2_' + suffix], 'M3_450': r['M3_' + suffix]}
            for s, r in rows.items()}


def table(rows):
    def stat(m):
        e = [r[m][0] - r[m][1] for r in rows.values()]
        n = len(e)
        return {'n': n, 'mae': sum(abs(x) for x in e) / n if n else None, 'bias': sum(e) / n if n else None}
    return {m: stat(m) for m in ('M1_450', 'M2_450', 'M3_450', 'M1_150', 'M2_150', 'M3_150')}


def job_counts(roots, label):
    """Amendment 30 section 4.2 (D-K9-57 5): job success counted from the job / capture files only (summary.json ok,
    k92_record.json present and its errors list empty, capture.json ok), per arm and sample group.  Counts only."""
    out = {}
    groups = (('s47_primary', 47, F_PRIMARY), ('s31_second', 31, F_SECOND[31]), ('s43_second', 43, F_SECOND[43]))
    keys = ('job_dirs', 'summary_ok_true', 'record_present', 'record_errors_empty', 'capture_ok')
    for arm, root in roots.items():
        row = {}
        for name, seed, Ts in groups:
            c = {'planned': len(Ts)}
            c.update({k: 0 for k in keys})
            for T in Ts:
                d = Path(root) / 'sa' / 'jobs' / label / _lab(seed, T)
                if d.is_dir():
                    c['job_dirs'] += 1
                if (read_json(d / 'summary.json') or {}).get('ok') is True:
                    c['summary_ok_true'] += 1
                rec = read_json(d / 'k92_record.json')
                if isinstance(rec, dict):
                    c['record_present'] += 1
                    if not rec.get('errors'):
                        c['record_errors_empty'] += 1
                tag = '%06d' % T + ('' if seed == 31 else '_s%d' % seed)
                cap = read_json(Path(root) / 'sa' / 'cap' / label / 'TL3' / tag / 'SAF' / 'capture.json')
                if isinstance(cap, dict) and cap.get('ok') is not False:
                    c['capture_ok'] += 1
            c['all_ok'] = all(c[k] == c['planned'] for k in keys)
            row[name] = c
        out[arm] = row
    return out


def cmd_fcount(args):
    """Amendment 30 section 4.2: the job-success count before the F judge (counts only, no value)."""
    roots = {'OFF': OUTK / 'f_off', 'W': OUTK / 'f_w', 'B1': OUTK / 'f_b1'}
    jc = job_counts(roots, args.label)
    ok = all(g['all_ok'] for row in jc.values() for g in row.values())
    res = {'schema': 'k92t-f-jobcount/v1', 'verdict': 'PASS' if ok else 'INCOMPLETE', 'job_counts': jc,
           'when': time.strftime('%Y-%m-%dT%H:%M:%S')}
    write_json(args.dest, res)
    print('K92T_FCOUNT %s %s' % (res['verdict'], {a: {g: '%d/%d' % (v['summary_ok_true'], v['planned'])
                                                       for g, v in row.items()} for a, row in jc.items()}))
    return 0


def persistence_report(pers, vref, off_rows, ident_ok):
    """Amendment 30 section 2 (D-K9-56).  off_rows = the OFF-arm primary rows {T: {'M1_450': (model, vissim), ...}};
    the VISSIM M1 at T+450 is the second element.  Report only."""
    ps = ((pers.get('seeds') or {}).get('s47') or {}).get('states') or {}
    vs = ((vref.get('seeds') or {}).get('s47') or {}).get('states') or {}
    states, pe, missing = {}, [], []
    for T in F_PRIMARY:
        if T in PERSIST_NOT:
            states[str(T)] = PERSIST_LABEL
            continue
        a = (ps.get(str(T - 450)) or {}).get('m1_T450')
        b = ((off_rows.get(T) or {}).get('M1_450') or (None, None))[1]
        if isinstance(a, int) and not isinstance(a, bool) and b is not None:
            pe.append(a - b)
            states[str(T)] = 'measured'
        else:
            states[str(T)] = 'missing'
            missing.append(T)
    keys = sorted(ps)
    bad_keys = [k for k in keys if not str(k).isdigit()]
    got = sorted(int(k) for k in keys if str(k).isdigit())
    overlap = {}
    for t in PERSIST_OVERLAP:
        a = (ps.get(str(t)) or {}).get('m1_T450')
        overlap[str(t)] = a is not None and a == (vs.get(str(t)) or {}).get('m1_T450')
    complete = (bool(ident_ok) and not bad_keys and got == sorted(PERSIST_VR_STATES) and not missing
                and len(pe) == len(PERSIST_MEASURED) and all(overlap.values()))
    return {'rule': 'measured iff T - 450 >= %d (U4 T_FROM); VR state = T - 450' % T_FROM_U4,
            'n': len(pe), 'mae': (sum(abs(x) for x in pe) / len(pe)) if pe else None, 'states': states,
            'measured': [T for T in F_PRIMARY if states[str(T)] == 'measured'],
            'not_measurable': {str(T): PERSIST_LABEL for T in PERSIST_NOT}, 'label_ko': PERSIST_LABEL_KO,
            'missing': missing, 'vr_states_declared': list(PERSIST_VR_STATES), 'vr_states_in_file': got,
            'vr_state_keys_not_int': bad_keys, 'vr_states_equal_declared': got == sorted(PERSIST_VR_STATES),
            'overlap_with_f_vref': {'n': len(overlap), 'n_equal': sum(1 for v in overlap.values() if v)},
            'identity_ok': bool(ident_ok), 'complete': complete}


def cmd_f(args):
    tree = Path(args.tree)
    sa = tree / SA_REL
    sys.path.insert(0, str(sa))
    import k92_gates as G
    label = args.label
    roots = {'OFF': OUTK / 'f_off', 'W': OUTK / 'f_w', 'B1': OUTK / 'f_b1'}
    vref = read_json(OUTK / 'f_vref' / 'sa' / 'k92_vissim_ref.json') or {}
    pers = read_json(OUTK / PERSIST_NAME / 'sa' / 'k92_vissim_ref.json') or {}
    ident = {s: ((vref.get('seeds') or {}).get('s%d' % s) or {}).get('network_identity') for s in (47, 31, 43)}
    ident_ok = {s: bool(ident[s]) and ident[s].get('raw_sha256') == INPX_RAW[s]
                and ident[s].get('normalized_sha256') == 'b7f05dcd07042fce8a439529853429a642f4de7b998c96ede51ce8c2d1230eb3'
                for s in ident}
    pid = ((pers.get('seeds') or {}).get('s47') or {}).get('network_identity')
    prim, info, missing = {}, {}, {}
    for arm, root in roots.items():
        prim[arm], info[arm], missing[arm] = f_rows(root, label, vref, 47, F_PRIMARY)
    complete = all(not missing[a] and len(prim[a]) == 22 for a in ('OFF', 'B1')) and ident_ok[47]
    res = {'schema': 'k92t-f/v1', 'amendment30': True, 'n_primary': {a: len(prim[a]) for a in prim},
           'missing': missing, 'network_identity_ok': ident_ok,
           'persist_identity_ok': bool(pid) and pid.get('raw_sha256') == INPX_RAW[47],
           'job_counts': job_counts(roots, label)}
    if not complete:
        res['verdict'] = 'INCOMPLETE'
    else:
        fj = G.f_judge(as450(prim['OFF'], '450'), as450(prim['B1'], '450'))
        res['f_judge'] = fj
        res['verdict'] = 'PASS' if (fj['F-1'] and fj['F-2'] and fj['F-3'] and fj['n'] == 22) else 'FAIL'
        res['table'] = {a: table(prim[a]) for a in prim if len(prim[a]) == 22}
        res['report_T150'] = G.f_judge(as450(prim['OFF'], '150'), as450(prim['B1'], '150'))
        if len(prim['W']) == 22:
            res['report_W_vs_OFF'] = G.f_judge(as450(prim['OFF'], '450'), as450(prim['W'], '450'))
        res['per_state'] = {str(T): {a: {m: prim[a][T][m] for m in prim[a][T]} for a in prim if T in prim[a]}
                            for T in F_PRIMARY}
        # persistence (amendment 30 section 2): VISSIM M1 at T (frame T+0.1) = m1_T450 of the VR state T-450 in
        # OUTK/f_persist30, measured only where T - 450 >= T_FROM_U4; the rest labelled PERSIST_LABEL
        res['report_persistence_M1_450'] = persistence_report(pers, vref, prim['OFF'], res['persist_identity_ok'])
        # P0-4 exposure lists
        exp_raw, exp_eff = None, None
        if sha_file(P0_4_SAMPLES) == P0_4_SAMPLES_SHA:
            exp_raw = (read_json(P0_4_SAMPLES) or {}).get('exposed_primary_states')
        if sha_file(P0_4_REVIEW) == P0_4_REVIEW_SHA:
            exp_eff = (read_json(P0_4_REVIEW) or {}).get('exposed_primary_states')
        res['report_exposure_sources'] = {'raw': exp_raw, 'effective': exp_eff,
                                          'raw_file': str(P0_4_SAMPLES), 'effective_file': str(P0_4_REVIEW)}
        for name, src in (('raw', exp_raw), ('effective', exp_eff)):
            if not isinstance(src, list):
                res['report_exposure_%s' % name] = {'error': 'exposure list unreadable'}
                continue
            ex = {int(x) for x in src} & set(F_PRIMARY)
            keep = [T for T in F_PRIMARY if T not in ex]
            if keep:
                sub = {a: {T: prim[a][T] for T in keep} for a in ('OFF', 'B1')}
                rj = G.f_judge(as450(sub['OFF'], '450'), as450(sub['B1'], '450'), boot_n=2000, seed=0)
            else:
                rj = None
            res['report_exposure_%s' % name] = {'excluded': sorted(ex), 'n_kept': len(keep), 'f_judge': rj}
        res['report_info'] = {a: {str(T): info[a][T] for T in info[a]} for a in info}
        res['report_seed_binding_states'] = {a: sorted(T for T, x in info[a].items()
                                                       if x.get('seed_binding_capture') == 1.0) for a in info}
    # second sample (report, "partly exposed")
    sec = {}
    for arm, root in roots.items():
        rows_all, miss_all = {}, []
        for seed, Ts in F_SECOND.items():
            r, _i, m = f_rows(root, label, vref, seed, Ts)
            rows_all.update({'s%d_%d' % (seed, T): v for T, v in r.items()})
            miss_all += ['s%d_%d' % (seed, T) for T in m]
        sec[arm] = {'n': len(rows_all), 'missing': miss_all, 'table': table(rows_all) if rows_all else None}
    res['report_second_sample'] = sec
    res['vref_sha256'] = sha_file(OUTK / 'f_vref' / 'sa' / 'k92_vissim_ref.json') if (
        OUTK / 'f_vref' / 'sa' / 'k92_vissim_ref.json').is_file() else None
    res['persist_sha256'] = sha_file(OUTK / PERSIST_NAME / 'sa' / 'k92_vissim_ref.json') if (
        OUTK / PERSIST_NAME / 'sa' / 'k92_vissim_ref.json').is_file() else None
    write_json(args.dest, res)
    pr = res.get('report_persistence_M1_450') or {}
    print('K92T_F %s n=%s persistence_complete=%s measured=%s not_measurable=%s' % (
        res['verdict'], res['n_primary'], pr.get('complete'), pr.get('n'), sorted(pr.get('not_measurable') or {})))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    # amendment 30: only the commands of the resumed stage (scans / j0 / ja / jwall were judged by the base file)
    ap.add_argument('cmd', choices=('sealedscan', 'jb', 'fcount', 'f'))
    ap.add_argument('--dest', required=True)
    ap.add_argument('--tree')
    ap.add_argument('--new')
    ap.add_argument('--label', default='k92t')
    args = ap.parse_args()
    return {'sealedscan': cmd_sealedscan, 'jb': cmd_jb, 'fcount': cmd_fcount, 'f': cmd_f}[args.cmd](args)


if __name__ == '__main__':
    raise SystemExit(main())
