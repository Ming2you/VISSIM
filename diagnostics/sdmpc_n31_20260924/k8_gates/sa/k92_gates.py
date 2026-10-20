"""K9-2 bundle 1 per-commit gate calculators (K8_PREDECLARATION_AMENDMENT_24 sections 4.2-4.4; fixed d46db6dc...).
Diagnostics only; no VISSIM.  The judgments of every K9-2 commit gate are computed here (pinned with the K9-2-0 blobs,
section 3.1-8); the drivers only run captures / jobs / replays and call these functions.  BLIND: results are verdicts,
paths, counts and sha; no objective or prediction value is printed.

    python -B k92_gates.py plant  --side LABEL --root R --out O --part Pa|Pb|Pa_arm --arm OFF|W|B1 [--arm-file F]
    python -B k92_gates.py judge-plant --base-out O0 --base-label L0 --base-root R0 --new-out O1 --new-label L1
                                      --new-root R1 --part Pa|Pb --dest J.json
    python -B k92_gates.py selftest --root R --dest J.json        guard + section 3.1-3b + J-b calculator blobs

Gate rules (operationalizations fixed here before any gate data; the amendment text is the definition):
  G-K0 plant  P-a = the 26 K8b probe states (PROBE_SAMPLE.json 41aa5d87...: H3 24 + L1 s43 2400 H42 + L2 s47 4800
              H27), SAF-K91 (5f0d0e40...) TL3 captures + OBS jobs; P-b = DP 17 (s31, 900 + 450 k) captures with the
              keyless k86h SAF arm 178de6c2 (the K9-1 closed list; the only keyless DP arm present at b9734abe).  The
              commit tree and the git-archive b9734abe tree run in the same execution; per state the G5 rule of the
              K9-1 commit gates (k8b_commit_gates.compare_g5, tolerance 0: template / capture.json / summary numeric
              leaves bit-equal, string leaves equal except sha / hash keys (listed) and root path strings (listed),
              one-sided leaves: none allowed), jobs ok, no recorder error, objective repr equal.
  G-K0 decis. k92_compare.compare (keyed=None) of each declared pair -> every verdict PASS.
  G-K1 static configure snapshots (k92_cfgsnap) key off vs key on of one state: cfg.network flattened structurally;
              the differing paths must be the W capacity (new value repr 5209.8), for B1 also the left-turn capacity
              (only when its key-off value < s, new value = s by repr) and the attribute head_floor_seed (key-on side
              only); the configure metadata may differ only by the one-sided keys k92_w / k92_hb / k92_hb_seed_binding
              and the declared H5 floor key (amendment 24 section 4.2); the SDMPC ownership table equal.
  G-K1 dyn.   plant jobs key off vs key on of one state: every ledger stock key that differs is C0 (an entity of
              k92_common.C0_ENTITIES), C1 (a key reached from C0 through transfer edges seen in either run, with a
              first differing row not before the neighbour's) or C3 (anything else, listed with its first differing
              row); summary leaves are classed by their entity (signal queue of a signal, SC1001 / SA / FW_W
              families, totals = C2, the rest C3 listed); STOP when an SC1001 / SA / FW_W summary leaf or ledger key
              is C3, or when the first C3 row comes before the first C0 row (fixed-action jobs).
  G-K2        amendment 27 (D-K9-49; written after the K9-2-1 / K9-2-2 gate data, disclosed): judge_g2 = the
              amendment-21 section 6.4 four outcomes of k92_compare.compare -- PASS = HARD H1-H5 same (after the
              declared H5 difference) and 0 unclassified leaves; HOLD = HARD same and unclassified > 0; FAIL =
              HARD different; INCOMPLETE -- after the CR pair check of the two producing trees (k92_a27.cr_pair;
              not ok = INCOMPLETE).  Until amendment 27 this line read "hard_verdict SAME" (judge_hard); judge_hard
              is kept as a report and is not the G-K2 verdict.
  G-K4        amendment 27 (D-K9-50; same disclosure): decisions = judge_g4_decision_full -- k92_compare.compare
              of the probe arm output (old) and the commit arm output (new), every leaf, allowed sets as
              amendment 24 section 4.2, after k92_a27.cr_pair; PASS = full PASS; HOLD = HARD same and
              unclassified > 0; EXPLAIN = HARD differs only in H2-H5 numbers within relative 1e-9 (numeric_hard;
              H1 may differ) and 0 unclassified (an operation-order explanation is needed: report and stop);
              FAIL otherwise; INCOMPLETE.  Plant (v3c3-s31 1500 / v3c3-s43 1050 H3 OBS jobs vs the probe jobs,
              summary + k92_record) = judge_g4_plant, unchanged: PASS = compare_g5 equal; EXPLAIN = only numbers
              differ, all within relative 1e-9; FAIL otherwise.  judge_g4_decision (HARD numbers only) is kept as
              a report.
  G-K5        key-off pairs (A archive, B commit) per state A B A B, clean pairs only (VISSIM count 0 three times):
              median wall ratio B / A <= 1.05 / 1.033718118959995; the IQR is reported only (amendment 26).
  G-K0 D-d    the J1 record (RR decisions folder) vs the commit replay with the run's own tuning bytes (k92_replay.py
              --tuning), k92_compare (keyed=None, old_root = the record's frozen root) -> PASS.
  G-K1 N1-N14 (design section 2.6) are covered by the three comparisons of judge_static: cfg.network leaves (N1 other
              capacities, N2 per-lane constant and the corridor copy, N4 / N11 / N13 specs, capacities and storage,
              N8 receiving storage, N9 meter service where it lives in cfg.network, N10 SC1001 capacities, N12 absent
              keys), the configure metadata (N5 head_observation options and provenance hash, N6 other floors and
              head resources, N7 the backpressure flag, N10 k8b_* / k9_* meta, N14 head_observation_* counters) and
              the SDMPC ownership table (N8); N3 (lane files) = the tree bytes (the commit diff lists no lane file).
  G-K2 (e)    report only: hard_verdict, first differing generalized path, and a class per differing path (C0 = a path
              naming a C0 entity of k92_common.C0_ENTITIES, C2 = objective / totals, C3 = the rest).
  G-K3        child process in the commit root (g3 subcommand): (1) SHO.configure_head_floor_seed with the seed key and
              without the W key raises ValueError naming D-K9-31; (2) k92_guard refuses a seed-only tuning (SAF-K91 +
              the committed H-b pin); (3) sa_arms.py --k92b1 writes the SAF arm with both keys (k92_keys = W, H-b);
              (4) every bundle arm differs from its base in exactly /urban/sc109w_through_saturation and
              /urban/capacity/head_floor_seed, whose evidence = the committed repository-relative paths and
              evidence_sha256 = the K92_VALUES.json pins = sha256 of the committed bytes (SAF arm vs SAF-K91 5f0d0e40;
              CFG arm vs CFG d0f9ef39: the committed config_n31_v2_k92b1.json when present, else
              k92_common.apply_k92b1(CFG) in memory).
  Arm id.     K9-2-3: sha256 of the sa_arms --k92b1 SAF arm = the probe t74 B1 arm (65cac7ea...), sha256 of the committed
              config_n31_v2_k92b1.json = the probe t9b B1 arm (c8e3ee2c...); make_config_n31.py --k92b1 --check exit 0.
  B           build_k92_evidence.py w --check (root = the commit tree) and hb --check (root = a git archive b9734abe
              tree: the builder pins the rule code SHO d9bd5392 and the commit SHO is the changed file; the evidence
              compared is the commit's) exit 0, and the committed evidence sha256 = the K92_VALUES.json pin.
  U           messages are compared after normalizing the tree roots of both sides to <root>, hexadecimal addresses
              to 0x? and pytest temporary folder numbers to pytest-N (test ids and outcomes are compared as they are).
  K9-2-0 diff git diff --name-status b9734abe..K9-2-0 paths all under k8_gates/sa/ (harness, k92 tools, tests);
              git diff b9734abe..K9-2-0 -- evaluation vendor plant scripts empty."""
import argparse
import json
import math
import pickle
import statistics
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import k8b_commit_gates as cg  # noqa: E402
import k92_common as k92c  # noqa: E402
import k92_compare as k92cmp  # noqa: E402
import k92_a27 as k92a  # noqa: E402

sc = cg.sc
c = sc.c
N31 = Path('diagnostics') / 'sdmpc_n31_20260924'
SAF_K91 = N31 / 'config_n31_v2_stopline_observed_full_k91.json'
SAF_K91_SHA256 = '5f0d0e40a39e44b3c7601f23177afbad8c2eee23d4421626482f2244a86c3341'
K86H_SAF = N31 / 'config_n31_v2_stopline_observed_full.json'
K86H_SAF_SHA256 = '178de6c2c6a211eb811701455c7bfbb6b65d747b6e2698e2025c95bc766b7a6c'
W_KEY = 'SC109_W_SC108_to_E'
L_KEY = 'SC109_W_SC108_to_N_SC16'
W_VALUE_REPR = '5209.8'
WALL_LIMIT = 1.05 / 1.033718118959995
IQR_LIMIT = 0.006               # amendment 26 (D-K9-47): G-K5 reports the IQR against this line, never judges
TOL_REL = 1e-9
JB_FILES = ('sa_gates.py', 'sa_stats.py', 'sa_tl3m.py', 'sa_vissim_ref.py', 'sa_common.py')
JB_BLOB_B9734ABE = {}          # filled by the caller from git (git rev-parse b9734abe:<path>) -> recorded only
CFG_REL = N31 / 'config_n31_v2.json'
CFG_SHA256 = 'd0f9ef395d4f9c51e6c68412f7c33abd546217e0d8cdc59d3c620183fa7aaec6'
CFG_ARM_REL = N31 / 'config_n31_v2_k92b1.json'
K92_PIN_SHA256 = {'w': 'b4b7294df0369874ea53dd5f0538abd31bac1c946aebdf241bdc7837a7671712',
                  'hb': 'b9fa1d01b9d922e9fc327793aa428cd7b544dae221044704dea7f0af610f20ee'}   # K92_VALUES.json (P0)
PROBE_B1_ARM_SHA256 = {'t74': '65cac7ea0b33d8f0b5c8efc458307578bcae7a2e34d1d097ce448a18a65ada28',
                       't9b': 'c8e3ee2c99b66c255b2279f0aa18eaafc18d4c7689e59e260109fac3b7d71866'}  # probe build record
ARM_PATHS = ['/urban/capacity/head_floor_seed', '/urban/sc109w_through_saturation']
# expected (173, p4) floor key names of the G-K0 decision runs (P0-2 (f) rule; KB/k92_probe/gk1_floor_names.json
# cf1ae3fb..., tool gk1_names.py 38a5d960...; the J1 names = K92_VALUES.json P0-2 (f))
GK1_FLOOR_KEYS = {'sdmpc31_v3c3_nc_s31': 'head_discharge_floor_173_p4_e36d6761cfeac634',
                  'sdmpc31_v3c3_k8j1_s31': 'head_discharge_floor_173_p4_c6f585e4e035cf63',
                  'sdmpc31_v3c3_k8j1_s41': 'head_discharge_floor_173_p4_301ceabb95f116fa',
                  'sdmpc31_v3c3_k8j1_s43': 'head_discharge_floor_173_p4_3e3dc5ca5bf80727',
                  'sdmpc31_v3c3_k8j1r_s31': 'head_discharge_floor_173_p4_1170360c34e5b57b'}
K920_ALLOWED_PREFIX = 'diagnostics/sdmpc_n31_20260924/k8_gates/sa/'


# ------------------------------------------------------------------------------------------------ blind form
def _blind(cmp):
    """A compare_g5 / compare_docs record without values: example lists keep the leaf paths only."""
    out = {}
    for k, v in (cmp or {}).items():
        if k in ('examples', 'string_examples', 'near_examples', 'path_strings_differ', 'hash_strings_differ'):
            out[k] = [x[0] if isinstance(x, (list, tuple)) and x else x for x in (v or [])]
        else:
            out[k] = v
    return out


# ------------------------------------------------------------------------------------------------ G-K0 plant
def plant_side(label, root, out, part, tuning_path=None, arm=None):
    """Captures (+ OBS jobs for P-a) of one code root.  part Pa (SAF-K91, or `tuning_path` for a K9-2 arm of G-K1
    dynamic / G-K4) or Pb (k86h SAF)."""
    cg.setup(root, out)
    cg.free_space()
    rows = {}
    if part == 'Pb':
        tun = cg.tuning_rec(Path(root) / K86H_SAF)
        if tun['sha256'] != K86H_SAF_SHA256:
            raise SystemExit(f'{tun}: not the k86h SAF arm')
        cg.prep_states([(31, T) for T in sc.DP_T])
        for T in sc.DP_T:
            rows[(31, T, None)] = {'cap': cg.capture(label, 'dp', 'SAF', 31, T, tun)}
        return tun, rows
    tun = cg.tuning_rec(Path(tuning_path) if tuning_path else Path(root) / SAF_K91)
    if tuning_path is None and tun['sha256'] != SAF_K91_SHA256:
        raise SystemExit(f'{tun}: not SAF-K91')
    states = cg.probe_sample_states() if part == 'Pa' else part
    cg.prep_states([(s, T) for s, T, _H in states])
    for seed, T, H in states:
        cap = cg.capture(label, 'tl3', 'SAF', seed, T, tun)
        jd = cg.job(label, 'TL3', T, 'SAF', 'OBS', H, seed=seed)
        rows[(seed, T, H)] = {'cap': cap, 'job': jd}
    return tun, rows


def _paths(base_out, base_label, base_root, part, states):
    out = {}
    c.configure(root=str(base_root), out=str(base_out), robs=c.DEFAULT_ROBS, nc3=c.NC3)
    for seed, T, H in states:
        c.configure(root=str(base_root), out=str(base_out), robs=cg.robs_of(seed), nc3=c.NC3)
        if part == 'Pb':
            out[(seed, T, H)] = {'cap': sc.cap_dir(base_label, 'DP', T, 'SAF', seed=31)}
        else:
            out[(seed, T, H)] = {'cap': sc.cap_dir(base_label, 'TL3', T, 'SAF', seed=seed),
                                 'job': sc.job_dir(base_label, sc.job_label('TL3', T, 'SAF', 'OBS', H, seed=seed))}
    return out


def judge_plant(base_out, base_label, base_root, new_out, new_label, new_root, part):
    """G-K0 P-a / P-b: the K9-1 G5 rule between two code roots of the same execution (tolerance 0)."""
    states = cg.probe_sample_states() if part == 'Pa' else [(31, T, None) for T in sc.DP_T]
    b = _paths(base_out, base_label, base_root, part, states)
    n = _paths(new_out, new_label, new_root, part, states)
    roots = [base_root, new_root, base_out, new_out]
    rows, ok = {}, True
    for key in states:
        bb, nn = b[key], n[key]
        miss = [str(p) for side in (bb, nn) for p in ([side['cap'] / 'capture.json', side['cap'] / 'template.pickle']
                                                      + ([side['job'] / 'summary.json'] if 'job' in side else []))
                if not p.is_file()]
        if miss:
            rows['s%s_%s_H%s' % key] = {'ok': False, 'missing': miss[:6]}
            ok = False
            continue
        r = {'template': cg.compare_g5(cg.load_template(new_root, bb['cap'] / 'template.pickle'),
                                       cg.load_template(new_root, nn['cap'] / 'template.pickle'), roots, renamed=(),
                                       allowed_one_sided=()),
             'capture_json': cg.compare_g5(sc.read_json(bb['cap'] / 'capture.json'),
                                           sc.read_json(nn['cap'] / 'capture.json'), roots, renamed=(),
                                           allowed_one_sided=())}
        good = r['template']['equal'] and r['capture_json']['equal']
        r['template'], r['capture_json'] = _blind(r['template']), _blind(r['capture_json'])
        if 'job' in bb:
            sb, sn = sc.read_json(bb['job'] / 'summary.json', {}) or {}, sc.read_json(nn['job'] / 'summary.json', {}) or {}
            r['summary'] = _blind(cg.compare_g5(sb, sn, roots, renamed=(), allowed_one_sided=()))
            r['jobs_ok'] = [sb.get('ok'), sn.get('ok')]
            r['recorder_errors'] = [len(sb.get('recorder_errors') or []), len(sn.get('recorder_errors') or [])]
            r['objective_repr_equal'] = sb.get('objective_repr') is not None and sb.get('objective_repr') == sn.get(
                'objective_repr')
            r['summary_one_sided'] = r['summary']['one_sided_failing']
            r['wall_sec'] = [sb.get('wall_sec'), sn.get('wall_sec')]
            good = (good and r['summary']['equal'] and sb.get('ok') is True and sn.get('ok') is True
                    and not sb.get('recorder_errors') and not sn.get('recorder_errors') and r['objective_repr_equal'])
        r['ok'] = good
        ok &= good
        rows['s%s_%s_H%s' % key] = r
    return {'gate': 'G-K0 ' + part, 'verdict': 'PASS' if ok else 'FAIL', 'n': len(states), 'rows': rows,
            'base': {'out': str(base_out), 'label': base_label, 'root': str(base_root)},
            'new': {'out': str(new_out), 'label': new_label, 'root': str(new_root)},
            'rule': 'K9-1 G5 rule (k8b_commit_gates.compare_g5, tolerance 0, no one-sided leaf)'}


# ------------------------------------------------------------------------------------------------ G-K0 decisions
def judge_decisions(pairs):
    """pairs = [(label, old_dir, new_dir, T, new_root)]: k92_compare (keyed=None), all PASS."""
    rows, ok = {}, True
    for label, old, new, T, root in pairs:
        r = k92cmp.compare(old, new, T, root, label=label)
        rows[label] = {k: r.get(k) for k in ('verdict', 'hard_verdict', 'unclassified_n', 'unclassified', 'allowed_counts',
                                             'r3_checks', 'k92_checks', 'why', 'json_sha256')}
        rows[label]['hard_groups'] = {g: r[g]['same'] for g in ('H1', 'H2', 'H3', 'H4', 'H5') if g in r}
        ok &= r.get('verdict') == 'PASS'
    return {'verdict': 'PASS' if ok else 'FAIL', 'n': len(pairs), 'rows': rows}


# ------------------------------------------------------------------------------------------------ G-K1 static
def flatten_obj(obj, path='', out=None, seen=None, depth=0):
    """Structural leaves of an object graph (dict / list / tuple / set / numpy / __dict__ / __slots__): path -> repr of a
    plain leaf, or '<type>' for an opaque one.  Cycles are cut by id (a revisit is the leaf '<cycle>')."""
    if out is None:
        out, seen = {}, set()
    if depth > 40:
        out[path] = '<deep>'
        return out
    if obj is None or isinstance(obj, (bool, int, float, str, bytes)):
        out[path] = repr(obj)
        return out
    oid = id(obj)
    if oid in seen:
        out[path] = '<cycle>'
        return out
    seen.add(oid)
    tname = type(obj).__module__ + '.' + type(obj).__qualname__
    if isinstance(obj, dict):
        for k in sorted(obj, key=lambda x: repr(x)):
            flatten_obj(obj[k], path + '/' + (k if isinstance(k, str) else repr(k)), out, seen, depth + 1)
        if not obj:
            out[path] = '{}'
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            flatten_obj(v, '%s[%d]' % (path, i), out, seen, depth + 1)
        if not obj:
            out[path] = '[]' if isinstance(obj, list) else '()'
    elif isinstance(obj, (set, frozenset)):
        out[path] = repr(sorted(repr(x) for x in obj))
    elif tname.startswith('numpy.') and hasattr(obj, 'tobytes'):
        out[path] = 'ndarray:%s:%s' % (getattr(obj, 'dtype', ''), __import__('hashlib').sha256(obj.tobytes()).hexdigest())
    elif callable(obj) and hasattr(obj, '__qualname__'):
        out[path] = 'callable:%s.%s' % (getattr(obj, '__module__', ''), obj.__qualname__)
    elif hasattr(obj, '__dict__'):
        out[path + '#type'] = tname
        for k in sorted(vars(obj)):
            flatten_obj(vars(obj)[k], path + '/' + k, out, seen, depth + 1)
    elif hasattr(obj, '__slots__'):
        out[path + '#type'] = tname
        for k in obj.__slots__:
            if hasattr(obj, k):
                flatten_obj(getattr(obj, k), path + '/' + k, out, seen, depth + 1)
    else:
        out[path] = '<%s>' % tname
    return out


def judge_static(off_dir, on_dir, arm, *, seed=None, floor_key=None, root=None):
    """G-K1 static of one state (snapshots of k92_cfgsnap, key off / key on)."""
    off_dir, on_dir = Path(off_dir), Path(on_dir)
    rec = {'off': str(off_dir), 'on': str(on_dir), 'arm': arm}
    for d in (off_dir, on_dir):
        if not (d / 'network.pickle').is_file() or not (d / 'metadata.json').is_file():
            rec.update(verdict='INCOMPLETE', why='snapshot missing in %s' % d)
            return rec
    if root is not None:
        for p in (str(root), str(Path(root) / 'vendor/NumSim-mine'), str(Path(root) / 'evaluation/controllers')):
            if p not in sys.path:
                sys.path.insert(0, p)
    a = pickle.loads((off_dir / 'network.pickle').read_bytes())
    b = pickle.loads((on_dir / 'network.pickle').read_bytes())
    fa, fb = flatten_obj(a), flatten_obj(b)
    diff = sorted(set(k for k in set(fa) | set(fb) if fa.get(k) != fb.get(k)))
    capw = '/movement_capacity_by_movement_veh_h/' + W_KEY
    capl = '/movement_capacity_by_movement_veh_h/' + L_KEY
    bad, notes = [], []
    for p in diff:
        if p == capw:
            if fb.get(p) != W_VALUE_REPR:
                bad.append(p + ' new repr %s' % fb.get(p))
            continue
        if arm == 'B1' and p == capl:
            try:
                old, new = float(fa.get(p)), float(fb.get(p))
            except (TypeError, ValueError):
                bad.append(p + ' not numeric')
                continue
            if not (old < seed and new == seed and fb.get(p) == repr(seed)):
                bad.append(p + ' condition false')
            continue
        if arm == 'B1' and (p == '/head_floor_seed' or p.startswith('/head_floor_seed/') or
                            p.startswith('/head_floor_seed[')):
            if p in fa:
                bad.append(p + ' present key-off')
            continue
        bad.append(p)
    if capw not in diff:
        bad.append(capw + ' unchanged')
    rec['network_diff_paths'] = diff[:60]
    rec['network_diff_n'] = len(diff)
    rec['network_leaves'] = [len(fa), len(fb)]
    ma = json.loads((off_dir / 'metadata.json').read_text(encoding='utf-8'))
    mb = json.loads((on_dir / 'metadata.json').read_text(encoding='utf-8'))
    mdiff = sorted(k for k in set(ma) | set(mb) if json.dumps(ma.get(k), sort_keys=True) != json.dumps(mb.get(k),
                                                                                                     sort_keys=True))
    mbad = []
    one_sided_ok = ('k92_w',) if arm == 'W' else ('k92_w', 'k92_hb', 'k92_hb_seed_binding')
    for k in mdiff:
        if k in one_sided_ok and k not in ma and k in mb:
            continue
        if k.startswith('head_discharge_floor_173_p4_') and arm == 'B1' and k == floor_key \
                and mb.get('k92_hb_seed_binding') == 1.0 and mb.get(k) == seed \
                and (k not in ma or (isinstance(ma.get(k), (int, float)) and ma[k] < seed)):
            continue
        mbad.append(k)
    rec['metadata_diff'] = mdiff[:40]
    rec['metadata_bad'] = mbad
    oa, ob = off_dir / 'ownership.json', on_dir / 'ownership.json'
    rec['ownership'] = ('absent' if not oa.is_file() and not ob.is_file() else
                        'equal' if oa.is_file() and ob.is_file() and oa.read_bytes() == ob.read_bytes() else 'differ')
    if rec['ownership'] == 'differ':
        mbad.append('ownership table')
    rec['network_bad'] = bad
    rec['seed_binding'] = mb.get('k92_hb_seed_binding')
    rec['verdict'] = 'PASS' if not bad and not mbad else 'FAIL'
    return rec


# ------------------------------------------------------------------------------------------------ G-K1 dynamic
SC1001_TOKENS = ('SC1001', 'OR_D_', 'in_SC1001', 'RM_C1048', 'RM_C1049', 'W_out', 'W_RAMP', 'onE', 'onW')
FW_TOKENS = ('freeway:FW_W', 'FW_W', 'origin:FW_W')


def _series(job_dir):
    import numpy as np
    p = Path(job_dir) / 'k92_series.npz'
    if not p.is_file():
        return None
    z = np.load(p, allow_pickle=True)
    return {'keys': [str(k) for k in z['keys']], 'model': z['model'], 't_end': z['t_end'], 'stage': z['stage'],
            'edges': [tuple(map(str, e)) for e in z['edges']]}


def _summary_class(path, series_class):
    p = path.lower()
    if p in ('/objective', '/objective_repr') or p.startswith(('/costs', '/resources')) or '/ledger_ttt' in p:
        return 'C2'
    if '/signal_queue/' in path:
        sig = path.rsplit('/', 1)[-1]
        if sig == 'SC109':
            return 'C0'
        hit = [cl for k, cl in series_class.items() if k.split(':', 1)[-1].startswith(sig + '_')]
        return 'C1' if any(x in ('C0', 'C1') for x in hit) else 'C3'
    fw = any(t.lower() in p for t in ('fw_w', 'cell9', 'cell_v', 'samples30', 'vmin_steps', 'origin_fw_w', 'entry_applied',
                                      'onE_threshold'.lower()))
    if fw:
        hit = [cl for k, cl in series_class.items() if 'fw_w' in k.lower()]
        return 'C1_FW' if hit and all(x == 'C1' for x in hit) and hit else 'C3_FW'
    sa1001 = any(t in p for t in ('/w_', 'port', 'receivers', '/sa', 'sa_', 'k8b0', 'wout', 'gate', 'ramp_queue',
                                 'or_d_w', 'first_block_t', 'blocked_steps', '/steps/', '/cap/', 'w_departures',
                                 'e_recv', 'e_approach', 'k91'))
    if sa1001:
        hit = [cl for k, cl in series_class.items() if any(t.lower() in k.lower() for t in SC1001_TOKENS)]
        return 'C1_SC1001' if hit and any(x == 'C1' for x in hit) else 'C3_SC1001'
    return 'C3'


def judge_dynamic(off_job, on_job):
    """G-K1 dynamic of one fixed-action plant job pair (module docstring)."""
    import numpy as np
    so, sn = _series(off_job), _series(on_job)
    rec = {'off': str(off_job), 'on': str(on_job)}
    if so is None or sn is None:
        rec.update(verdict='INCOMPLETE', why='k92_series.npz missing')
        return rec
    if len(so['t_end']) != len(sn['t_end']) or not np.array_equal(so['t_end'], sn['t_end']):
        rec.update(verdict='INCOMPLETE', why='residence rows differ in number / time')
        return rec
    keys = sorted(set(so['keys']) | set(sn['keys']))
    io, inn = {k: i for i, k in enumerate(so['keys'])}, {k: i for i, k in enumerate(sn['keys'])}
    nrow = len(so['t_end'])
    first = {}
    for k in keys:
        if k not in io or k not in inn:
            first[k] = 0
            continue
        a, b = so['model'][:, io[k]], sn['model'][:, inn[k]]
        same = (a == b) | (np.isnan(a) & np.isnan(b))
        if not same.all():
            first[k] = int(np.argmin(same))
    adj = {}
    for s, t in set(so['edges']) | set(sn['edges']):
        adj.setdefault(s, set()).add(t)
        adj.setdefault(t, set()).add(s)
    cls = {}
    for k in first:
        if any(e in k for e in k92c.C0_ENTITIES):
            cls[k] = 'C0'
    changed = True
    while changed:
        changed = False
        for k in sorted(first, key=lambda x: first[x]):
            if k in cls:
                continue
            if any(j in cls and cls[j] in ('C0', 'C1') and first[j] <= first[k] for j in adj.get(k, ())):
                cls[k] = 'C1'
                changed = True
    for k in first:
        cls.setdefault(k, 'C3')
    c0_first = min((first[k] for k, v in cls.items() if v == 'C0'), default=None)
    c3_keys = sorted((k for k, v in cls.items() if v == 'C3'), key=lambda x: first[x])
    c3_first = min((first[k] for k in c3_keys), default=None)
    s_off = sc.read_json(Path(off_job) / 'summary.json', {}) or {}
    s_on = sc.read_json(Path(on_job) / 'summary.json', {}) or {}
    na, sa_ = cg.leaves(s_off)
    nb, sb_ = cg.leaves(s_on)
    leaf_diff = []
    for k in sorted(set(na) | set(nb)):
        if cg.excluded(k):
            continue
        x, y = na.get(k), nb.get(k)
        if x is None or y is None or not (x == y or (math.isnan(x) and math.isnan(y))):
            leaf_diff.append(k)
    for k in sorted(set(sa_) | set(sb_)):
        if not cg.excluded(k) and sa_.get(k) != sb_.get(k):
            leaf_diff.append(k)
    leaf_cls = {k: _summary_class(k, cls) for k in leaf_diff}
    bad_leaves = sorted(k for k, v in leaf_cls.items() if v in ('C3_SC1001', 'C3_FW'))
    other_c3 = sorted(k for k, v in leaf_cls.items() if v == 'C3')
    rec.update({'rows': nrow, 'keys_differ': len(first),
                'classes': {x: sum(1 for v in cls.values() if v == x) for x in ('C0', 'C1', 'C3')},
                'c0_first_row': c0_first, 'c3_first_row': c3_first,
                'c3_keys': [[k, first[k]] for k in c3_keys[:40]],
                'summary_leaves_differ': len(leaf_diff),
                'summary_classes': {x: sum(1 for v in leaf_cls.values() if v == x) for x in sorted(set(leaf_cls.values()))},
                'sc1001_sa_fw_c3_leaves': bad_leaves[:40], 'other_c3_leaves': other_c3[:40]})
    fam_c3 = [k for k in c3_keys if any(t.lower() in k.lower() for t in SC1001_TOKENS + FW_TOKENS)]
    rec['sc1001_sa_fw_c3_keys'] = fam_c3[:40]
    rec['c3_before_c0'] = c3_first is not None and (c0_first is None or c3_first < c0_first)
    stop = bool(bad_leaves) or bool(fam_c3) or rec['c3_before_c0']
    rec['verdict'] = 'STOP' if stop else 'PASS'
    return rec


# ------------------------------------------------------------------------------------------------ G-K2 / G-K4
def judge_hard(ref_dir, new_dir, T, new_root, keyed):
    r = k92cmp.compare(ref_dir, new_dir, T, new_root, keyed=keyed)
    return {'hard_verdict': r.get('hard_verdict'), 'verdict_full': r.get('verdict'), 'h5_declared': r.get('h5_declared'),
            'hard_groups': {g: r[g]['same'] for g in ('H1', 'H2', 'H3', 'H4', 'H5') if g in r},
            'hard_diff_paths': {g: r[g]['diff_paths_generalized'][:10] for g in ('H2', 'H3', 'H4', 'H5')
                                if g in r and not r[g]['same']},
            'unclassified_n': r.get('unclassified_n'), 'unclassified': r.get('unclassified'),
            'allowed_counts': r.get('allowed_counts'), 'k92_checks': r.get('k92_checks')}


def judge_g4_plant(probe_job, new_job, path_roots):
    """G-K4 plant: summary.json and k92_record.json of the probe job and the commit job of the same arm and state.
    PASS = compare_g5 equal (numeric bit-equal, strings equal up to the listed roots / sha keys, no bad one-sided leaf);
    EXPLAIN = only numeric leaves differ and all within relative 1e-9 (needs the operation-order explanation: report,
    stop); FAIL otherwise.  Blind form (paths and counts only)."""
    out, verdicts = {}, []
    for name in ('summary.json', 'k92_record.json'):
        a = sc.read_json(Path(probe_job) / name)
        b = sc.read_json(Path(new_job) / name)
        if a is None or b is None:
            return {'status': 'INCOMPLETE', 'why': name + ' missing'}
        g5 = cg.compare_g5(a, b, path_roots, renamed=(), allowed_one_sided=())
        tol = cg.compare_docs(a, b, tol_rel=TOL_REL)
        if g5['equal']:
            v = 'PASS'
        elif g5['string_differ'] == 0 and g5['one_sided_failing'] == 0 and tol['numeric_differ'] == 0:
            v = 'EXPLAIN'
        else:
            v = 'FAIL'
        verdicts.append(v)
        out[name] = {'verdict': v, 'g5': _blind(g5), 'tol_1e-9': _blind(tol)}
    status = 'FAIL' if 'FAIL' in verdicts else 'EXPLAIN' if 'EXPLAIN' in verdicts else 'PASS'
    return {'status': status, 'parts': out}


def judge_g4_decision(r):
    """r = k92_compare.numeric_hard: PASS = no difference at all (CSV bytes equal, 0 numeric differences); EXPLAIN =
    differences all within relative 1e-9 (operation-order explanation needed: report, stop); FAIL otherwise."""
    if r.get('status') == 'INCOMPLETE':
        return 'INCOMPLETE'
    if r.get('status') != 'PASS':
        return 'FAIL'
    return 'PASS' if r.get('numeric_diffs') == 0 and r.get('csv_same') else 'EXPLAIN'


# ------------------------------------------------------------------------------------------------ amendment 27
def judge_g2(ref_dir, new_dir, T, new_root, keyed, ref_root):
    """Amendment 27 (D-K9-49): the G-K2 (a)(b)(c) verdict = the four outcomes of k92_compare.compare (PASS only
    when no unclassified leaf) after the CR pair check of the two producing trees (ref_root = the tree of the
    reference output, new_root = the commit tree)."""
    r = judge_hard(ref_dir, new_dir, T, new_root, keyed)
    r['cr_pair'] = k92a.cr_pair(ref_root, new_root)
    full = r.get('verdict_full')
    r['verdict'] = full if r['cr_pair']['ok'] and full in ('PASS', 'HOLD', 'FAIL', 'INCOMPLETE') else 'INCOMPLETE'
    r['rule'] = 'amendment 27: amendment 21 section 6.4 four outcomes (PASS only when no unclassified leaf)'
    return r


def judge_g4_decision_full(probe_dir, commit_dir, T, commit_root, keyed, probe_root):
    """Amendment 27 (D-K9-50): one G-K4 decision row = every leaf of the probe arm output (old) vs the commit arm
    output (new) with the amendment 24 section 4.2 allowed sets, after the CR pair check of the two trees."""
    cr = k92a.cr_pair(probe_root, commit_root)
    full = k92cmp.compare(probe_dir, commit_dir, T, commit_root, keyed=keyed)
    num = (k92cmp.numeric_hard(probe_dir, commit_dir, T, tol_rel=TOL_REL) if full.get('verdict') != 'INCOMPLETE'
           else {'status': 'INCOMPLETE'})
    if not cr['ok'] or full.get('verdict') == 'INCOMPLETE' or num.get('status') == 'INCOMPLETE':
        v = 'INCOMPLETE'
    elif full.get('verdict') == 'PASS':
        v = 'PASS'
    elif full.get('hard_verdict') == 'SAME':
        v = 'HOLD'
    elif num.get('status') == 'PASS' and not full.get('unclassified_n'):
        v = 'EXPLAIN'
    else:
        v = 'FAIL'
    return {'verdict': v, 'cr_pair': cr, 'hard_verdict': full.get('hard_verdict'), 'verdict_full': full.get('verdict'),
            'hard_groups': {g: full[g]['same'] for g in ('H1', 'H2', 'H3', 'H4', 'H5') if g in full},
            'hard_diff_paths': {g: full[g]['diff_paths_generalized'][:10] for g in ('H2', 'H3', 'H4', 'H5')
                                if g in full and not full[g]['same']},
            'unclassified_n': full.get('unclassified_n'), 'unclassified': full.get('unclassified'),
            'allowed_counts': full.get('allowed_counts'), 'k92_checks': full.get('k92_checks'),
            'r3_checks': full.get('r3_checks'), 'h5_declared': full.get('h5_declared'),
            'numeric': {k: num.get(k) for k in ('status', 'csv_same', 'numeric_diffs', 'worst_rel', 'n_problem',
                                                 'non_numeric_or_above')},
            'rule': 'amendment 27: every leaf (amendment 21 section 6 + amendment 24 section 4.2), 1e-9 class from '
                    'numeric_hard'}


# ------------------------------------------------------------------------------------------------ G-K5
def judge_wall(rows):
    clean = [r['ratio'] for r in rows if r.get('clean') and r.get('ok') and r.get('ratio') is not None]
    if len(rows) != 8 or not clean:
        return {'verdict': 'INCOMPLETE', 'n_rows': len(rows), 'n_clean': len(clean)}
    q = statistics.quantiles(clean, n=4, method='inclusive') if len(clean) >= 2 else [clean[0]] * 3
    med = statistics.median(clean)
    res = {'n_rows': len(rows), 'n_clean': len(clean), 'median': med, 'iqr': q[2] - q[0], 'limit': WALL_LIMIT,
           'iqr_reference': IQR_LIMIT, 'iqr_over_reference': q[2] - q[0] > IQR_LIMIT, 'iqr_report_only': True,
           'rows': rows}
    res['verdict'] = 'FAIL' if med > WALL_LIMIT else 'PASS'      # amendment 26 (D-K9-47): the median only
    return res


# ------------------------------------------------------------------------------------------------ U
def junit_results(path):
    import xml.etree.ElementTree as ET
    out = {}
    if not Path(path).is_file():
        return None
    for tc in ET.parse(str(path)).getroot().iter('testcase'):
        tid = '%s::%s' % (tc.get('classname'), tc.get('name'))
        outcome, msg = 'passed', None
        for tag in ('failure', 'error', 'skipped'):
            node = tc.find(tag)
            if node is not None:
                outcome = {'failure': 'failed', 'error': 'error', 'skipped': 'skipped'}[tag]
                msg = (node.get('message') or '').splitlines()[0][:300] if node.get('message') else None
                break
        out[tid] = [outcome, msg]
    return out


def _norm_msg(msg, roots):
    import re
    if msg is None:
        return None
    out = re.sub(r'\\+', '/', str(msg))
    for r in sorted((re.sub(r'\\+', '/', str(x)).rstrip('/') for x in roots if x), key=len, reverse=True):
        out = re.sub(re.escape(r), '<root>', out, flags=re.IGNORECASE)
    out = re.sub(r'0x[0-9a-fA-F]+', '0x?', out)
    return re.sub(r'pytest-\d+', 'pytest-N', out)


def judge_u(base, new, new_tests, roots=()):
    """Declared existing tests: per test id the same outcome and the same first message line as b9734abe (after the
    module-docstring U normalization); the new test ids (prefix match on new_tests) all passed."""
    if base is None or new is None:
        return {'verdict': 'INCOMPLETE'}
    base = {t: [o, _norm_msg(m, roots)] for t, (o, m) in base.items()}
    new = {t: [o, _norm_msg(m, roots)] for t, (o, m) in new.items()}
    common = sorted(set(base) & set(new))
    differ = [[t, base[t], new[t]] for t in common if base[t] != new[t]]
    only_base = sorted(set(base) - set(new))
    only_new = sorted(t for t in set(new) - set(base))
    new_ids = [t for t in only_new if any(x in t for x in new_tests)]
    other_new = [t for t in only_new if t not in new_ids]
    new_bad = [[t, new[t]] for t in new_ids if new[t][0] != 'passed']
    ok = not differ and not only_base and not other_new and not new_bad and bool(new_ids or not new_tests)
    return {'verdict': 'PASS' if ok else 'FAIL', 'common': len(common), 'differ': differ[:30],
            'only_base': only_base[:30], 'other_new': other_new[:30], 'new_tests': len(new_ids), 'new_bad': new_bad[:30],
            'known_failures_same': [[t, base[t]] for t in common if base[t][0] != 'passed'][:10]}


# ------------------------------------------------------------------------------------------------ K9-2-0 diff / B
def judge_diff_k920(name_status_text, eval_diff_text):
    rows = [ln.split('\t') for ln in name_status_text.splitlines() if ln.strip()]
    paths = [r[-1] for r in rows]
    outside = [p for p in paths if not p.startswith(K920_ALLOWED_PREFIX)]
    ok = bool(paths) and not outside and eval_diff_text.strip() == ''
    return {'verdict': 'PASS' if ok else 'FAIL', 'paths': [[r[0], r[-1]] for r in rows], 'outside': outside,
            'eval_vendor_plant_scripts_diff_bytes': len(eval_diff_text)}


def judge_b(rows):
    """rows = {part: {'rc': exit code, 'stdout_last': line, 'committed_sha256': sha256 of the committed evidence}}."""
    bad = []
    for part, r in rows.items():
        if r.get('rc') != 0 or not str(r.get('stdout_last') or '').startswith('K92_EVIDENCE_CHECK_OK ' + part):
            bad.append(part + ' check')
        if r.get('committed_sha256') != K92_PIN_SHA256[part]:
            bad.append(part + ' sha')
    return {'verdict': 'PASS' if rows and not bad else 'FAIL', 'rows': rows, 'bad': bad}


# ------------------------------------------------------------------------------------------------ G-K2 (e) report
def report_g2e(ref_dir, new_dir, T, new_root, keyed):
    r = k92cmp.compare(ref_dir, new_dir, T, new_root, keyed=keyed)
    paths = []
    for g in ('H1', 'H2', 'H3', 'H4', 'H5'):
        if g in r and not r[g]['same']:
            paths += [(g, p) for p in r[g]['diff_paths_generalized']]

    def klass(p):
        low = p.lower()
        if any(e.lower() in low for e in k92c.C0_ENTITIES):
            return 'C0'
        if 'objective' in low or 'total' in low:
            return 'C2'
        return 'C3'
    classes = {}
    for g, p in paths:
        classes.setdefault(klass(p), []).append(g + ':' + p)
    return {'hard_verdict': r.get('hard_verdict'), 'same': r.get('hard_verdict') == 'SAME',
            'first_diff_path': (paths[0][0] + ':' + paths[0][1]) if paths else None,
            'classes': {k: {'n': len(v), 'paths': v[:12]} for k, v in sorted(classes.items())},
            'unclassified_n': r.get('unclassified_n')}


# ------------------------------------------------------------------------------------------------ G-K3 / arm identity
def _leaf_diff(a, b, path=''):
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                out.append(path + '/' + k)
            else:
                out += _leaf_diff(a[k], b[k], path + '/' + k)
    elif a != b or type(a) is not type(b):
        out.append(path)
    return out


def _arm_check(arm_doc, base_doc, root):
    diff = sorted(_leaf_diff(base_doc, arm_doc))
    rec = {'diff_paths': diff, 'paths_ok': diff == ARM_PATHS}
    pins = {'w': (arm_doc.get('urban') or {}).get('sc109w_through_saturation'),
            'hb': ((arm_doc.get('urban') or {}).get('capacity') or {}).get('head_floor_seed')}
    vals = {}
    for part, pin in pins.items():
        rel = k92c.K92_EVIDENCE[part]
        f = Path(root) / rel
        file_sha = sc.sha256_file(f) if f.is_file() else None
        vals[part] = {'pin': pin, 'file_sha256': file_sha,
                      'ok': isinstance(pin, dict) and sorted(pin) == ['evidence', 'evidence_sha256']
                      and pin.get('evidence') == rel and pin.get('evidence_sha256') == K92_PIN_SHA256[part] == file_sha}
    rec['values'] = vals
    rec['ok'] = rec['paths_ok'] and all(v['ok'] for v in vals.values())
    return rec


def g3_child(root, out):
    """G-K3 inside the commit root (module docstring); returns the record (no verdict on its own)."""
    import subprocess
    import types
    root = Path(root)
    for p in (str(root), str(root / 'vendor/NumSim-mine')):
        if p not in sys.path:
            sys.path.insert(0, p)
    from evaluation.controllers import signal_head_observation as SHO
    rec = {'root': str(root)}
    hb_pin = {'evidence': k92c.K92_EVIDENCE['hb'],
              'evidence_sha256': sc.sha256_file(root / k92c.K92_EVIDENCE['hb'])}
    net = types.SimpleNamespace(
        urban_movements={W_KEY: {'origin': 'SC108_to_SC109', 'kind': 'boundary_out'},
                         L_KEY: {'origin': 'SC108_to_SC109', 'kind': 'internal'}},
        movement_capacity_by_movement_veh_h={W_KEY: 619.5918367346939, L_KEY: 413.0612244897959},
        movement_capacity_veh_h=0.0)
    tun = {'urban': {'capacity': {'head_observation': {'enabled': True, 'min_green_sec': 30, 'min_crossings': 5},
                                  'head_floor_seed': hb_pin}}}
    plan = {'controllers': {'109': {'phase_signal_groups': {'p3': [2], 'p4': [5]}}}}
    try:
        SHO.configure_head_floor_seed(types.SimpleNamespace(network=net), tun, None, plan)
        rec['seed_only_valueerror'] = {'raised': False}
    except ValueError as e:
        rec['seed_only_valueerror'] = {'raised': True, 'names_dk931': 'D-K9-31' in str(e), 'message': str(e)[:200]}
    rec['seed_only_attribute_set'] = hasattr(net, 'head_floor_seed')
    # (2) harness refusal of a seed-only tuning
    from types import SimpleNamespace
    c.configure(root=str(root), out=str(Path(out) / 'g3_guard'), robs=c.DEFAULT_ROBS, nc3=c.NC3)
    saf = json.loads((root / SAF_K91).read_text(encoding='utf-8'))
    seed_only = json.loads(json.dumps(saf))
    seed_only['urban']['capacity']['head_floor_seed'] = hb_pin
    p = Path(out) / 'g3_seed_only.json'
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(seed_only), encoding='utf-8')
    try:
        k92c.k92_guard(str(p), 31, 1500, SimpleNamespace(gates_stage=None, declaration_sha=None), 'g3', op='job',
                       harness='TL3', arm='SAF', entry='OBS', H=3)
        rec['harness_refuses_seed_only'] = False
    except SystemExit:
        rec['harness_refuses_seed_only'] = True
    # (3) sa_arms --k92b1
    arms_out = Path(out) / 'g3_arms'
    done = subprocess.run([sys.executable, '-B', str(HERE / 'sa_arms.py'), '--root', str(root), '--out', str(arms_out),
                           '--source', 'generate', '--k92b1'], capture_output=True, text=True, encoding='utf-8',
                          errors='replace', env=dict(__import__('os').environ, PYTHONHASHSEED='0'))
    rec['sa_arms'] = {'rc': done.returncode, 'stdout_tail': done.stdout.strip().splitlines()[-2:],
                      'stderr_tail': done.stderr.strip().splitlines()[-2:]}
    arms = sc.read_json(arms_out / 'sa' / 'tuning' / 'arms.json', {}) or {}
    row = (arms.get('arms') or {}).get('SAF') or {}
    rec['sa_arms']['k92_keys'] = row.get('k92_keys')
    saf_arm_path = Path(row['path']) if row.get('path') else None
    rec['sa_arms']['arm_sha256'] = sc.sha256_file(saf_arm_path) if saf_arm_path and saf_arm_path.is_file() else None
    rec['sa_arms']['arm_path'] = str(saf_arm_path) if saf_arm_path else None
    # (4) the bundle arms against their bases
    if saf_arm_path and saf_arm_path.is_file():
        rec['saf_arm'] = _arm_check(json.loads(saf_arm_path.read_text(encoding='utf-8')), saf, root)
    cfg_raw = (root / CFG_REL).read_bytes()
    rec['cfg_sha256'] = sc.sha256_file(root / CFG_REL)
    cfg_doc = json.loads(cfg_raw.decode('utf-8'))
    committed = root / CFG_ARM_REL
    if committed.is_file():
        rec['cfg_arm_source'] = 'committed ' + CFG_ARM_REL.as_posix()
        rec['cfg_arm_sha256'] = sc.sha256_file(committed)
        cfg_arm = json.loads(committed.read_text(encoding='utf-8'))
    else:
        rec['cfg_arm_source'] = 'k92_common.apply_k92b1(CFG) in memory'
        data = k92c.dumps_tuning(k92c.apply_k92b1(cfg_doc, root))
        rec['cfg_arm_sha256'] = __import__('hashlib').sha256(data).hexdigest()
        cfg_arm = json.loads(data.decode('utf-8'))
    rec['cfg_arm'] = _arm_check(cfg_arm, cfg_doc, root)
    return rec


def judge_g3(rec, need_committed_cfg_arm=False):
    so = rec.get('seed_only_valueerror') or {}
    checks = {'seed_only_valueerror': so.get('raised') is True and so.get('names_dk931') is True
              and rec.get('seed_only_attribute_set') is False,
              'harness_refuses_seed_only': rec.get('harness_refuses_seed_only') is True,
              'sa_arms_both_keys': (rec.get('sa_arms') or {}).get('rc') == 0 and (rec.get('sa_arms') or {}).get(
                  'k92_keys') == ['urban.sc109w_through_saturation', 'urban.capacity.head_floor_seed'],
              'saf_arm_two_paths_values': (rec.get('saf_arm') or {}).get('ok') is True,
              'cfg_base_is_cfg': rec.get('cfg_sha256') == CFG_SHA256,
              'cfg_arm_two_paths_values': (rec.get('cfg_arm') or {}).get('ok') is True}
    if need_committed_cfg_arm:
        checks['cfg_arm_committed'] = str(rec.get('cfg_arm_source', '')).startswith('committed')
    return {'verdict': 'PASS' if all(checks.values()) else 'FAIL', 'checks': checks}


def judge_arm_identity(rec, make_config_check_rc):
    checks = {'saf_arm_is_probe_t74_B1': (rec.get('sa_arms') or {}).get('arm_sha256') == PROBE_B1_ARM_SHA256['t74'],
              'cfg_arm_is_probe_t9b_B1': rec.get('cfg_arm_sha256') == PROBE_B1_ARM_SHA256['t9b']
              and str(rec.get('cfg_arm_source', '')).startswith('committed'),
              'make_config_k92b1_check': make_config_check_rc == 0}
    return {'verdict': 'PASS' if all(checks.values()) else 'FAIL', 'checks': checks}


# ------------------------------------------------------------------------------------------------ self-tests
def selftest(root):
    """Guard self-test (section 3.1-3a), section 3.1-3b blindness, J-b calculator files (no child process)."""
    import tempfile
    from types import SimpleNamespace
    c.configure(root=str(root), out=tempfile.mkdtemp(prefix='k92_selftest_'), robs=c.DEFAULT_ROBS, nc3=c.NC3)
    closed = SimpleNamespace(gates_stage=None, declaration_sha=None)
    open_ = SimpleNamespace(gates_stage='k92t', declaration_sha=k92c.K92_AMENDMENT24_SHA256)
    tmp = Path(c.OUT)
    saf = str(Path(root) / SAF_K91)
    k86h = str(Path(root) / K86H_SAF)
    doc = json.loads(Path(saf).read_text(encoding='utf-8'))
    w = json.loads(json.dumps(doc))
    w['urban']['sc109w_through_saturation'] = {'evidence': 'x', 'evidence_sha256': '0' * 64}
    b1 = json.loads(json.dumps(w))
    b1['urban']['capacity']['head_floor_seed'] = {'evidence': 'y', 'evidence_sha256': '0' * 64}
    seed_only = json.loads(json.dumps(doc))
    seed_only['urban']['capacity']['head_floor_seed'] = {'evidence': 'y', 'evidence_sha256': '0' * 64}
    paths = {}
    for name, d in (('w', w), ('b1', b1), ('seed_only', seed_only)):
        paths[name] = str(tmp / (name + '.json'))
        Path(paths[name]).write_text(json.dumps(d), encoding='utf-8')
    kw = dict(op='job', harness='TL3', arm='SAF', entry='OBS', H=3)
    cases = []

    def case(name, expect, fn):
        try:
            fn()
            refused, why = False, None
        except SystemExit as e:
            refused, why = True, str(e)[:160]
        cases.append({'case': name, 'expect_refused': expect, 'refused': refused, 'ok': refused == expect, 'why': why})
    case('primary_keyed_refused', True, lambda: k92c.k92_guard(paths['b1'], 47, 2400, closed, 't', **kw))
    case('primary_keyless_refused', True, lambda: k92c.k92_guard(k86h, 47, 1050, closed, 't', op='capture',
                                                                 harness='TL3', arm='SAF'))
    case('k91_judging_keyed_refused', True, lambda: k92c.k92_guard(paths['w'], 31, 2700, closed, 't', **kw))
    case('dp_closed_list_keyless_allowed', False, lambda: k92c.k92_guard(k86h, 31, 4500, closed, 't', op='capture',
                                                                         harness='DP', arm='SAF'))
    case('second_sample_allowed', False, lambda: k92c.k92_guard(paths['b1'], 43, 1050, closed, 't', **kw))
    case('probe_sample_allowed', False, lambda: k92c.k92_guard(paths['b1'], 47, 4800, closed, 't', **kw))
    case('seed_alone_refused', True, lambda: k92c.k92_guard(paths['seed_only'], 41, 1500, closed, 't', **kw))
    case('old_token_k91t_refused', True, lambda: k92c.k92_guard(paths['b1'], 31, 1500, SimpleNamespace(
        gates_stage='k91t', declaration_sha=sc.K91_AMENDMENT19_SHA256), 't', **kw))
    case('old_token_k8bt_refused', True, lambda: k92c.k92_guard(paths['b1'], 31, 1500, SimpleNamespace(
        gates_stage='k8bt', declaration_sha=sc.K8B_AMENDMENT16_SHA256), 't', **kw))
    case('k92t_opens_primary', False, lambda: k92c.k92_guard(paths['b1'], 47, 2400, open_, 't', **kw))
    # section 3.1-3b: the recorder leaves the s47 VISSIM side null, k92_vissim_blind refuses s47 without the stage
    import k92_record
    rec47 = k92_record.build({'seed': 47, 'label': 't'}, 0.0, 150.0, 3, None)
    rec31 = k92_record.build({'seed': 31, 'label': 't'}, 0.0, 150.0, 3, None)
    blind = {'s47_record_vissim_null': rec47['vissim'] is None and rec47['vissim_reason'] == k92c.K92_BLIND_REASON,
             's31_record_reason': rec31['vissim_reason'] == 'k92_vissim_ref',
             's47_vissim_blind_closed': k92c.k92_vissim_blind(47, closed) is True,
             's47_vissim_blind_open': k92c.k92_vissim_blind(47, open_) is False,
             's31_not_blind': k92c.k92_vissim_blind(31, closed) is False}
    jb = {f: sc.sha256_file(HERE / f) for f in JB_FILES}
    ok = all(x['ok'] for x in cases) and all(blind.values())
    return {'schema': 'k92-selftest/v1', 'root': str(root), 'cases': cases, 'blind_3_1_3b': blind,
            'jb_calculator_sha256': jb, 'child_processes': 0, 'verdict': 'PASS' if ok else 'FAIL'}


# ------------------------------------------------------------------------------------------------ F (stage k92t)
def f_judge(rows_off, rows_b1, boot_n=2000, seed=0):
    """Section 5.3 F-1..F-3 (k92t only): rows = {state: {'M1_450': (model, vissim), 'M2_450': ..., 'M3_450': ...}}."""
    import random

    def errs(rows, m):
        return {s: r[m][0] - r[m][1] for s, r in rows.items() if r.get(m) and None not in r[m]}

    def mae(e):
        return sum(abs(x) for x in e.values()) / len(e)

    def bias(e):
        return sum(e.values()) / len(e)
    out = {}
    for m in ('M1_450', 'M2_450', 'M3_450'):
        out[m] = {'off': errs(rows_off, m), 'b1': errs(rows_b1, m)}
    f1 = mae(out['M1_450']['b1']) <= mae(out['M1_450']['off'])
    f2 = abs(bias(out['M2_450']['b1'])) <= abs(bias(out['M2_450']['off']))
    f3 = bias(out['M3_450']['b1']) - bias(out['M3_450']['off']) <= 5.0
    rng = random.Random(seed)
    states = sorted(out['M1_450']['off'])
    boot = []
    for _ in range(boot_n):
        pick = [rng.choice(states) for _ in states]
        boot.append(sum(abs(out['M1_450']['b1'][s]) - abs(out['M1_450']['off'][s]) for s in pick) / len(pick))
    boot.sort()
    return {'F-1': f1, 'F-2': f2, 'F-3': f3, 'n': len(states),
            'boot_mae_diff_90': [boot[int(0.05 * boot_n)], boot[int(0.95 * boot_n) - 1]]}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('plant')
    p.add_argument('--side', required=True)
    p.add_argument('--root', required=True)
    p.add_argument('--out', required=True)
    p.add_argument('--part', required=True)
    p.add_argument('--arm-file')
    p = sub.add_parser('judge-plant')
    for k in ('base-out', 'base-label', 'base-root', 'new-out', 'new-label', 'new-root', 'part', 'dest'):
        p.add_argument('--' + k, required=True)
    p = sub.add_parser('selftest')
    p.add_argument('--root', required=True)
    p.add_argument('--dest', required=True)
    p = sub.add_parser('g3')
    p.add_argument('--root', required=True)
    p.add_argument('--out', required=True)
    p.add_argument('--dest', required=True)
    p.add_argument('--need-committed-cfg-arm', action='store_true')
    args = ap.parse_args()
    c.lower_priority()
    if args.cmd == 'plant':
        part = args.part
        states = None
        if part.startswith('[') or part.startswith('states:'):
            states = [tuple(int(x) for x in s.split('-')) for s in part.split(':', 1)[1].split(',')]
        tun, rows = plant_side(args.side, args.root, args.out, states or part, tuning_path=args.arm_file)
        print('K92_PLANT_SIDE_DONE %s %s n=%d tuning=%s' % (args.side, part, len(rows), tun['sha256'][:16]), flush=True)
    elif args.cmd == 'judge-plant':
        r = judge_plant(Path(args.base_out), args.base_label, Path(args.base_root), Path(args.new_out), args.new_label,
                        Path(args.new_root), args.part)
        sc.write_json(args.dest, r)
        print('K92_JUDGE_PLANT %s %s' % (args.part, r['verdict']), flush=True)
    elif args.cmd == 'selftest':
        r = selftest(args.root)
        sc.write_json(args.dest, r)
        print('K92_SELFTEST %s bad=%s blind=%s' % (r['verdict'], [x['case'] for x in r['cases'] if not x['ok']],
                                                   r['blind_3_1_3b']), flush=True)
    elif args.cmd == 'g3':
        rec = g3_child(args.root, args.out)
        res = {'record': rec, 'judge': judge_g3(rec, need_committed_cfg_arm=args.need_committed_cfg_arm)}
        sc.write_json(args.dest, res)
        print('K92_G3 %s %s' % (res['judge']['verdict'], {k: v for k, v in res['judge']['checks'].items() if not v}),
              flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
