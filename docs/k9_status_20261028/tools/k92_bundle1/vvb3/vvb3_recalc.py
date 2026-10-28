"""VerifyVB 3 -- independent recalculation of the V-B rerun (K8_PREDECLARATION_AMENDMENT_33 section 6.5, amendment 32
section 4.8, amendment 31 section 4.4).  Verification scratch tool, never committed.

Imports the standard library and numpy only.  It never imports the V-B driver (KV2/vb_chain.py), the recalculator
(KV2/vb_recalc.py), the hook (AD33/vbhook), the AD32 tools (vb_select / vb_lib32), KI, the harness (k92_compare,
k92_record, sa_*) or any VBT / GWT8 module.  The rules are written again from the amendment text:
  comparison N / HARD H1-H5 / F1-F3 (L_T 55) / D1-D5 / V / R3 / A_K92 ............ amendment 21 section 6, 24 section
                                                                                    4.2, 27 section 2.1, 29
  VB-I1 (4 chain-first decisions) and the report-only view of the 10 chained OFF .. amendment 32 sections 2.1-2.3
  VB-I2, VB-I3, VB-I4, VB-I6 ...................................................... amendment 24 section 14.1, 32 2.4
  VB-I7 and the four hook-name checks ............................................. amendment 32 2.5, 33 section 6.5
  record selection ................................................................ amendment 32 section 3.4
  ZI (z2)-(z6) ..................................................................... amendment 32 section 3.5
  VB-M1..M9 ........................................................................ amendment 24 section 14.1, 32 3.6
  archive listings ................................................................. amendment 33 section 5 (d)
The closed leaf list (AD32/vb_closed_leaves.json) and K92_VALUES.json are read as data.  Everything is computed from
raw files (decision JSON / CSV / progress, run records, hook folders, record folders, arm files, RR record decisions);
the driver's judge files are read only AFTER the recomputation, to compare.

    python -B vvb3_recalc.py selftest            synthetic self-test (no V-B file read) -> out/vvb3_selftest.json
    python -B vvb3_recalc.py run                 recompute + compare -> out/vvb3_recalc.json (+ out/vvb3_recalc.txt)

Stdout: counts, verdict words and sha only.  Numbers go to the output JSON."""
import hashlib
import json
import math
import os
import re
import sys
import tempfile
import time
from pathlib import Path

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
OUT = HERE / 'out'
SPK = Path(r'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/'
           r'491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8')
KB = SPK / 'k92' / 'bundle1'
OK2 = Path(r'D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1')
VBR = OK2 / 'vb2'
OLD_VBR = OK2 / 'vb'
RR = Path(r'D:/VISSIM_runs/20261004_sdmpc31_k8')
TK = Path(r'D:/VISSIM-merge/k8_gate_trees/k92b1')
VBT = TK / 'vb2_e27ceac8'
OLD_VBT = TK / 'vb_e27ceac8'
OLD_VBT_BUILD = TK / 'vb_e27ceac8.build.json'
FRZ8 = Path(r'D:/VISSIM-merge/frozen/sdmpc31_74cd495f_202610131824')
FRZ8B = Path(r'D:/VISSIM-merge/frozen/sdmpc31_b9734abe_202610141821')
N31 = 'diagnostics/sdmpc_n31_20260924'
VALUES = KB / 'k92_probe_a25' / 'K92_VALUES.json'
CLOSED = KB / 'a32decl' / 'vb_closed_leaves.json'
STOP_R1 = [KB / 'k92_vb' / 'K92_VB_REPORT_stop_r1.md', KB / 'VB_REPORT_stop_r1.md', OLD_VBR / 'K92_VB_REPORT.md']
STOP_R1_SHA = 'd7bf44f3e309aa4ae8e5084b0db238f9baeb2870b6d75b4bea7b6d854427ea00'
ARCH_VBT_SHA = 'd51f4deefc53b69cdadd9472a6ea2ca9197f694760f26c2380e1a101a1089680'     # amendment 33 section 5 (d)
ARCH_VBT_ROWS = 10660
ARCH_VBR_SHA = '392d10278514a2206fe9a6b5d22190708931ffabdecaf911037668f5f4ecd583'
ARCH_VBR_FILES = 1129

S = 1045.1612903225805                    # H-b seed (D-K9-34), repr fixed
LOW_P3 = 24.5                              # J1 onset definition (amendment 24 VB-M2)
BIG_DP3 = 0.5                              # amendment 24 VB-M3
ADAPTER = 'vissim_stackelberg_adapter.py'
SEL_OK = ('selected', 'no_candidate', 'no_match', 'match_conflict')
FLOOR_PREFIX = 'head_discharge_floor_173_p4_'
CHAIN3 = ('movement:SC109_W_SC108_to_E', 'movement:SC109_W_SC108_to_N_SC16', 'storage:SC108_to_SC109')
E_OUT = 'storage:SC109_E_out'
PHANTOM = 'movement:SC109_N_SC16_to_W_SC108'
CFG_B1_SHA = 'c8e3ee2c99b66c255b2279f0aa18eaafc18d4c7689e59e260109fac3b7d71866'
SAF_B1_SHA = '65cac7ea0b33d8f0b5c8efc458307578bcae7a2e34d1d097ce448a18a65ada28'
ARM_PATHS = sorted(['/urban/capacity/head_floor_seed', '/urban/sc109w_through_saturation'])
SAFB1_REL = 'arms/sa/tuning/config_n31_v2_stopline_observed_full_k91_k92b1.json'

T3000 = list(range(3000, 4501, 150))
TW = [1, 150, 300, 450, 600, 750, 900, 1050]
# amendment 24 section 14.1 table (chains, runs, record trees) and amendment 32 sections 2.1 / 2.2 (OFF times)
CHAINS = [
    {'chain': 'VB-41w', 'key': 'vb41w', 'run': 'sdmpc31_v3c3_k8j1_s41', 'seed': 41, 'old_root': FRZ8, 'times': TW,
     'off': TW},
    {'chain': 'VB-31', 'key': 'vb31', 'run': 'sdmpc31_v3c3_k8j1r_s31', 'seed': 31, 'old_root': FRZ8B, 'times': T3000,
     'off': [3000, 3150]},
    {'chain': 'VB-43', 'key': 'vb43', 'run': 'sdmpc31_v3c3_k8j1_s43', 'seed': 43, 'old_root': FRZ8, 'times': T3000,
     'off': [3000, 3150]},
    {'chain': 'VB-41', 'key': 'vb41', 'run': 'sdmpc31_v3c3_k8j1_s41', 'seed': 41, 'old_root': FRZ8, 'times': T3000,
     'off': [3000, 3150]},
]
ZI = [('z1_off', 'sdmpc31_v3c3_k8j1_s43', 1050), ('z1_b1', 'sdmpc31_v3c3_k8j1_s43', 1050),
      ('z2_b1', 'sdmpc31_v3c3_k8j1_s43', 750)]
R1_ACTION_TOKEN_PATHS = [   # amendment 33 section 9 (STOP r1 section 3.3)
    '/metadata/joint_leader_selection/budget_initialization/reference_action_token',
    '/metadata/joint_leader_selection/control_sequence/plan_action_token',
    '/metadata/joint_leader_selection/pfo_warm_start/iterations[*]/action_token',
    '/metadata/joint_leader_selection/pfo_warm_start/trial_rows[*]/action_token',
    '/metadata/joint_leader_selection/surrogate_query/rows[*]/action_token',
    '/metadata/joint_leader_selection/surrogate_query/warm_budget_binding/initialization/reference_action_token',
    '/metadata/joint_leader_selection/tangent_derivatives[*]/candidate_prediction_reused/requested_action_token',
    '/metadata/joint_leader_selection/tangent_derivatives[*]/candidate_prediction_reused/source_action_token',
    '/metadata/joint_leader_selection/tangent_derivatives[*]/candidate_prediction_reused/warm_budget_binding/'
    'initialization/reference_action_token',
    '/metadata/joint_leader_selection/tangent_derivatives[*]/surrogate_prediction/action_token',
    '/metadata/joint_leader_selection/trial_rows[*]/action_token',
]


# ================================================================================================ small helpers
def fsha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def jload(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        return default


def t6(T):
    return '%06d' % int(T)


def isnum(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def fnum(x):
    return float(x) if isnum(x) else None


def lp(p):
    s = os.path.abspath(str(p))
    return s if s.startswith('\\\\?\\') else '\\\\?\\' + s


# ================================================================================================ comparison rules
# amendment 21 section 6.1 + amendment 27 section 2.1 + amendment 29 (D-K9-54): normalization N
N_RULES = [re.compile(x) for x in (
    r'd:/vissim-merge/frozen/sdmpc31_[0-9a-f]{8}_[0-9]{12}',
    r'd:/vissim-merge/sim3-n31-k8',
    r'd:/vissim-merge/k8_gate_trees/(?:k92b1/(?:(?:a25|a26decl|a27)/)?|k92attrib/)'
    r'(?!(?:a25|a26decl|a27)(?![a-z0-9_]))[a-z0-9_]+(?=/|$)',
    r'd:/vissim-merge/k8_gate_trees/(?:s31fail/tree74(?:_base|_f1)?|(?!(?:k92b1|k92attrib)(?![a-z0-9_]))[a-z0-9_]+)',
)]
N_BUNDLE = re.compile(r'd:/vissim_runs/20261001_v3c3/reports/k8/(?:offline_gates|offline_gates_k8h)/'
                      r'(?:[a-z0-9_]+/)*?t[0-9]{6}(?:_[a-z0-9]+)*')
N_RUN = [re.compile(r'd:/vissim_runs/20261004_sdmpc31_k8/sdmpc31_v3c3_k8j1[a-z]*_s[0-9]+'),
         re.compile(r'd:/vissim_runs/20261001_sdmpc31_v3c3/sdmpc31_v3c3_nc_s[0-9]+')]
N_NAME = [re.compile(r'sdmpc31_v3c3_k8j1[a-z]*_s[0-9]+'), re.compile(r'sdmpc31_v3c3_nc_s[0-9]+')]


def nstr(s, post=None):
    s = s.lower().replace('\\\\', '/').replace('\\', '/')
    for rx in N_RULES:
        s = rx.sub('<root>', s)
    s = N_BUNDLE.sub('<bundle>', s)
    for rx in N_RUN:
        s = rx.sub('<run>', s)
    for rx in N_NAME:
        s = rx.sub('<name>', s)
    if post:
        for a, b in post:
            s = s.replace(a, b)
    return s


class Clash(Exception):
    pass


def nobj(x, post=None, where=''):
    if isinstance(x, dict):
        out = {}
        for k, v in x.items():
            nk = nstr(k, post)
            if nk in out:
                raise Clash('key clash after N at %s: %s' % (where, nk))
            out[nk] = nobj(v, post, where + '/' + nk)
        return out
    if isinstance(x, list):
        return [nobj(v, post, where + '[]') for v in x]
    if isinstance(x, str):
        return nstr(x, post)
    return x


class _Missing:
    def __repr__(self):
        return '<missing>'


MISS = _Missing()


def ddiff(a, b, p, out):
    """K7 gb_common.deep_diff path form (amendment 21 section 6.4): value / presence / type / list_length."""
    if a is MISS or b is MISS:
        if not (a is MISS and b is MISS):
            out.append((p, 'presence', a, b))
        return
    if type(a) is not type(b):
        out.append((p, 'type', a, b))
        return
    if isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a:
                out.append((p + '/' + k, 'presence', MISS, b[k]))
            elif k not in b:
                out.append((p + '/' + k, 'presence', a[k], MISS))
            else:
                ddiff(a[k], b[k], p + '/' + k, out)
    elif isinstance(a, list):
        if len(a) != len(b):
            out.append((p, 'list_length', None, None))
            return
        for i in range(len(a)):
            ddiff(a[i], b[i], '%s[%d]' % (p, i), out)
    elif a != b:
        out.append((p, 'value', a, b))


def gpath(p):
    return re.sub(r'\[\d+\]', '[*]', p)


def lastc(p):
    return re.sub(r'\[\d+\]$', '', p.split('/')[-1])


def parentc(p):
    parts = p.split('/')
    return re.sub(r'\[\d+\]$', '', parts[-2]) if len(parts) >= 3 else ''


# amendment 21 section 6.3 L_T (55 names)
LT = set('''candidate_elapsed_sec candidate_time_overrun_sec compile_or_load_sec cpu_sec cpu_started created_at
cyclic_gc_cleanup_cpu_sec cyclic_gc_cleanup_wall_sec deadline_monotonic decision_deadline_monotonic
decision_time_remaining_sec decision_wall_sec elapsed_sec elapsed_since_start_sec endpoint_cpu_sec endpoint_sec
finished_at first_call_sec initializer_cpu_sec initializer_generation_wall_sec initializer_wall_sec
leader_time_budget_overrun_sec local_score_cpu_sec local_score_sec overrun_sec pool_started_monotonic
post_guard_pfo_wall_sec prediction_wall_sec preparation_copy_cpu_sec preparation_copy_wall_sec preparation_cpu_sec
preparation_serialization_cpu_sec preparation_serialization_wall_sec preparation_wall_sec ready_monotonic reverse_sec
scalar_export_sec scalar_load_sec scalar_sec sdmpc_after_pfo_seconds seconds serialization_cpu_sec
serialization_wall_sec solve_wall_sec started started_at state_check_sec sweep_sec tangent_sec task_cpu_sec
task_wall_sec waiting_after_hold_sec waiting_after_trials_sec wall_sec wall_sec_including_spawn'''.split())
assert len(LT) == 55
ISO_T = re.compile(r'^\d{4}-\d{2}-\d{2}[tT ]\d{2}:\d{2}(:\d{2}(\.\d+)?)?([zZ]|[+-]\d{2}:?\d{2})?$')
HEXS = re.compile(r'^[0-9a-f]{16,128}$')
F2_NAME = re.compile(r'(sha256|sha1|sha|token|fingerprint|digest|hash)$', re.I)
V7 = {'/metadata/decision_wall_sec', '/metadata/prediction_wall_sec', '/prediction/wall_sec',
      '/run_provenance/inputs/state_json/path', '/run_provenance/inputs/state_json/sha256',
      '/metadata/run_provenance/inputs/state_json/path', '/metadata/run_provenance/inputs/state_json/sha256'}
_TAIL = r'(?:[/\[].*)?'
R3_ITEMS = [('R3-01', re.compile(r'/(?:metadata/)?run_provenance/(?:workspace_git_commit|execution_fingerprint_sha256)')),
            ('R3-02', re.compile(r'/(?:metadata/)?run_provenance/imported_modules' + _TAIL)),
            ('R3-03', re.compile(r'/(?:metadata/)?run_provenance/inputs/[^/]+/sha256')),
            ('R3-04', re.compile(r'/(?:metadata/)?run_provenance/(?:workspace_root|numsim_repo_root)')),
            ('R3-05', re.compile(r'/(?:metadata/)?run_provenance/inputs/(?:adapter_py|calibration_json|'
                                 r'control_mapping_json|detector_mapping_json|fixed_signal_schedule_py|'
                                 r'intersection_adjacency_json|link_assignment_json|main_vbs_runner|numsim_default_yaml|'
                                 r'parameters_json|parameters_py|storage_capacity_json|strict_signal_program_py|'
                                 r'tuning_json|watchdog_wrapper)/path')),
            ('R3-06', re.compile(r'/metadata/(?:detector_mapping_resolved_path|native_phase_share_map_path)')),
            ('R3-08', re.compile(r'/metadata/joint_leader_selection/tangent_derivatives\[\d+\]/'
                                 r'transformed_source_sha256' + _TAIL))]
R3_FILES = ('tuning_json', 'main_vbs_runner', 'watchdog_wrapper')
CAO = '<root>/evaluation/controllers/control_area_objective.py'
RSK = '<root>/evaluation/controllers/runtime_setup.py'
RS_REL = 'evaluation/controllers/runtime_setup.py'
CAO_REL = 'evaluation/controllers/control_area_objective.py'
D2_SET = {'territory_sha256', 'policy_sha256', 'receipt_sha256', 'lane_plant_manifest_sha256', 'numsim_src_sha256'}
D3_RX = re.compile(r'^/(metadata/)?run_provenance/(imported_modules/[^/]+/sha256|signal_program_sha256/.+|'
                   r'numsim_git_commit|numsim_snapshot_commit|run_id)$')
D4_RX = re.compile(r'^/(metadata/)?run_provenance/inputs/([^/]+)/sha256$')
D5_RX = re.compile(r'^/metadata/joint_leader_selection/tangent_derivatives\[\*\]/transformed_source_sha256/(.+)$')
KNOWN_OLD_RS = {'8a5aec79c79e24e568f5f419cb0d9a70f7580c2c8db62d1eadff3eab672f93e1',
                'ea79be3a6b60b300e660a88e7c3ec76c2df8321ca6c06a756e9b40b08a862a53',
                '0ba3fa61ef61c25a402b47429fdc666598c5a5f83c7a3dde45aed060570adc3b',
                '38c7a58010c9461c8180ed585db46ed45bdd50593980ee498a2c3a7d7cf7f70d',
                '472d7f9cc5174ab82d2a3767a3259e54798a436e7e10a36aa34710cf0a5d101a'}
K92M = ('/metadata/k92_w', '/metadata/k92_hb', '/metadata/k92_hb_seed_binding',
        '/metadata/k92_attrib_capacity_override', '/metadata/k92_attrib_head_173_p4_seed')
H2_FIELDS = ('n_p_star', 'n_uf_star', 'ramp_metering', 'vsl', 'green_times', 'offsets', 'inflow_outflow_allocation')
H3_JLS = ('selected_objective', 'held_objective', 'warm_start_objective', 'selection_status', 'converged', 'feasible')


def wallclock(path, kind, a, b):
    """F3 (amendment 21 section 6.3)."""
    if kind not in ('value', 'type'):
        return False
    name = lastc(path)
    if name not in LT or (name == 'seconds' and parentc(path) == 'final_check_reserve'):
        return False
    if isnum(a) and isnum(b):
        return True
    if isinstance(a, str) and isinstance(b, str) and ISO_T.match(a) and ISO_T.match(b):
        return True
    return a is None and b is None


def fkind(path, kind, a, b):
    if kind not in ('value', 'type'):
        return None
    if isinstance(a, str) and isinstance(b, str) and HEXS.match(a) and HEXS.match(b):
        return 'F1'
    if F2_NAME.search(lastc(path)) and ((isinstance(a, str) and isinstance(b, str)) or (a is None and b is None)):
        return 'F2'
    if wallclock(path, kind, a, b):
        return 'F3'
    return None


def drule(path):
    g, name = gpath(path), lastc(path)
    if name.endswith('action_token'):
        return 'D1'
    if name.endswith('evidence_sha256') or name in D2_SET or g.endswith('/physical_ramp_recorded_csv/sha256'):
        return 'D2'
    if g.startswith('/metadata/') and not g.startswith('/metadata/run_provenance') and \
            '/joint_leader_selection/' not in g and name.endswith('sha256'):
        return 'D2b'
    if D3_RX.match(g):
        return 'D3'
    m = D4_RX.match(g)
    if m and m.group(2) not in ('tuning_json', 'main_vbs_runner', 'watchdog_wrapper', 'state_json'):
        return 'D4'
    m = D5_RX.match(g)
    if m and m.group(1) != CAO:
        return 'D5'
    return None


def r3_of(path):
    for rid, rx in R3_ITEMS:
        if rx.fullmatch(path):
            return rid
    return None


def under(path, top):
    return path == top or path.startswith(top + '/') or path.startswith(top + '[')


def hard_path(path):
    """True for every leaf inside a HARD block (amendment 21 section 6.2), N form."""
    for f in H2_FIELDS + ('prediction', 'prediction_error'):
        if under(path, '/' + f):
            return True
    for top in ('/metadata/sdmpc_state', '/metadata/sdmpc_active', '/metadata/far_measured_seeded'):
        if under(path, top):
            return True
    if path.startswith('/metadata/far_rate_est_') or path.startswith('/metadata/head_'):
        return True
    return any(under(path, '/metadata/joint_leader_selection/' + k) for k in H3_JLS)


def progress_tail(p):
    p = Path(p)
    if not p.is_file():
        return MISS
    for line in reversed(p.read_text(encoding='utf-8').splitlines()):
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if (r.get('stage') or r.get('event')) == 'sdmpc_completed':
            return {'objective': repr(r.get('objective')), 'held_objective': repr(r.get('held_objective'))}
    return MISS


def hard_groups(doc, prog):
    md = doc.get('metadata') if isinstance(doc.get('metadata'), dict) else {}
    jls = md.get('joint_leader_selection') if isinstance(md.get('joint_leader_selection'), dict) else None
    g = {'H2': {('/' + k): doc.get(k, MISS) for k in H2_FIELDS}, 'H3': {}, 'H4': {}, 'H5': {}}
    if jls is not None:
        for k in ('selected_objective', 'held_objective', 'warm_start_objective'):
            g['H3']['/metadata/joint_leader_selection/' + k] = repr(jls[k]) if k in jls else MISS
        for k in ('selection_status', 'converged', 'feasible'):
            g['H3']['/metadata/joint_leader_selection/' + k] = jls.get(k, MISS)
    else:
        g['H3']['/#jls'] = MISS
    g['H3']['/#progress_last'] = prog
    g['H4']['/metadata/sdmpc_state'] = md.get('sdmpc_state', MISS)
    g['H5']['/metadata/sdmpc_active'] = md.get('sdmpc_active', MISS)
    g['H5']['/metadata/far_measured_seeded'] = md.get('far_measured_seeded', MISS)
    for k in md:
        if k.startswith('far_rate_est_') or k.startswith('head_'):
            g['H5']['/metadata/' + k] = md[k]
    g['H5']['/prediction'] = doc.get('prediction', MISS)
    g['H5']['/prediction_error'] = doc.get('prediction_error', MISS)
    return g


def raw_lookup(doc, npath):
    cur = doc
    for part in npath.strip('/').split('/'):
        if not isinstance(cur, dict):
            return MISS
        hit = [k for k in cur if k.lower() == part]
        if len(hit) != 1:
            return MISS
        cur = cur[hit[0]]
    return cur


def compare_dec(dir_old, dir_new, T, new_root, old_root, post_new=None, extra_allow=None):
    """One decision: amendment 21 section 6 rules + A_K92 (amendment 24 4.2, 29), keyed = None (key-off: any
    one-sided K92 metadata subtree is unclassified).  post_new = extra string substitutions applied to the NEW side
    after N (rerun segment only).  extra_allow(path, kind, va, vb, group) -> reason or None (rerun segment only)."""
    s = t6(T)
    do, dn = Path(dir_old), Path(dir_new)
    rep = {'T': int(T), 'old': str(do), 'new': str(dn)}
    files = {k: (do / ('action_%s%s' % (s, k)), dn / ('action_%s%s' % (s, k))) for k in ('.csv', '.json')}
    if not all(a.is_file() and b.is_file() for a, b in files.values()):
        rep.update(verdict='INCOMPLETE', why='output missing')
        return rep
    rep['csv_same'] = fsha(files['.csv'][0]) == fsha(files['.csv'][1])
    raw_o = json.loads(files['.json'][0].read_text(encoding='utf-8-sig'))
    raw_n = json.loads(files['.json'][1].read_text(encoding='utf-8-sig'))
    try:
        A = nobj(raw_o)
        B = nobj(raw_n, post_new)
    except Clash as e:
        rep.update(verdict='INCOMPLETE', why=str(e))
        return rep
    GA = hard_groups(A, progress_tail(do / ('action_%s.joint.progress.jsonl' % s)))
    GB = hard_groups(B, progress_tail(dn / ('action_%s.joint.progress.jsonl' % s)))
    hard = {'H1': {'same': rep['csv_same']}}
    extra_used = []
    for grp in ('H2', 'H3', 'H4', 'H5'):
        dd = []
        for key in sorted(set(GA[grp]) | set(GB[grp])):
            ddiff(GA[grp].get(key, MISS), GB[grp].get(key, MISS), key, dd)
        kept = []
        for p, kind, va, vb in dd:
            if p in V7 or wallclock(p, kind, va, vb):
                continue
            if extra_allow is not None:
                why = extra_allow(p, kind, va, vb, grp)
                if why:
                    extra_used.append({'group': grp, 'path': gpath(p), 'kind': kind, 'reason': why})
                    continue
            kept.append((p, kind))
        hard[grp] = {'same': not kept, 'n': len(kept), 'paths': sorted({gpath(p) for p, _ in kept})}
    rep['hard'] = hard
    rep['hard_same'] = all(v['same'] for v in hard.values())
    dd = []
    ddiff(A, B, '', dd)
    rep['n_diff_total'] = len(dd)
    allowed, uncl, a_k92, r3chk = {}, [], [], []
    for p, kind, va, vb in dd:
        if hard_path(p):
            continue
        g = gpath(p)
        if p in K92M or any(p.startswith(x + '/') for x in K92M):
            uncl.append((g, kind, 'K92M key-off'))
            continue
        m5 = D5_RX.match(g)
        if m5 and m5.group(1) == RSK:
            nf, of = Path(new_root) / RS_REL, (Path(old_root) / RS_REL if old_root is not None else None)
            new_rs = fsha(nf) if nf.is_file() else None
            old_rs = fsha(of) if of is not None and of.is_file() else None
            new_is = new_rs is not None and vb == new_rs
            old_is = old_rs is not None and va == old_rs
            ok = kind == 'value' and isinstance(va, str) and isinstance(vb, str) and new_is and old_is \
                and va in KNOWN_OLD_RS
            a_k92.append({'path': g, 'ok': ok, 'new_is_root_rs': new_is, 'old_is_root_rs': old_is,
                          'old_known': isinstance(va, str) and va in KNOWN_OLD_RS})
            if ok:
                allowed['A_K92'] = allowed.get('A_K92', 0) + 1
            else:
                uncl.append((g, kind, 'A_K92 false'))
            continue
        d = drule(p)
        if d:
            why = extra_allow(p, kind, va, vb, 'D') if extra_allow is not None else None
            if why:
                extra_used.append({'group': 'D', 'path': g, 'kind': kind, 'reason': why})
                continue
            uncl.append((g, kind, d))
            continue
        if p in V7:
            allowed['V'] = allowed.get('V', 0) + 1
            continue
        rid = r3_of(p)
        if rid == 'R3-03':
            name = p.split('/')[-2]
            if name in R3_FILES:
                rp = raw_lookup(raw_n, p[:-len('/sha256')] + '/path')
                rs = raw_lookup(raw_n, p)
                ok = isinstance(rp, str) and isinstance(rs, str) and Path(rp).is_file() and fsha(rp) == rs
                r3chk.append({'path': g, 'ok': ok})
                if ok:
                    allowed[rid] = allowed.get(rid, 0) + 1
                else:
                    uncl.append((g, kind, 'R3-03 file'))
                continue
            uncl.append((g, kind, 'R3-03 other'))
            continue
        if rid == 'R3-08':
            m = D5_RX.match(g)
            if m and m.group(1) == CAO:
                cf = Path(new_root) / CAO_REL
                ok = cf.is_file() and isinstance(vb, str) and vb == fsha(cf)
                r3chk.append({'path': g, 'ok': ok})
                if ok:
                    allowed[rid] = allowed.get(rid, 0) + 1
                else:
                    uncl.append((g, kind, 'R3-08 CAO file'))
                continue
            uncl.append((g, kind, 'R3-08 other'))
            continue
        if rid is not None:
            allowed[rid] = allowed.get(rid, 0) + 1
            continue
        fk = fkind(p, kind, va, vb)
        if fk:
            allowed[fk] = allowed.get(fk, 0) + 1
            continue
        if extra_allow is not None:
            why = extra_allow(p, kind, va, vb, 'other')
            if why:
                extra_used.append({'group': 'other', 'path': g, 'kind': kind, 'reason': why})
                continue
        uncl.append((g, kind, 'not allowed'))
    agg = {}
    for u in uncl:
        agg[u] = agg.get(u, 0) + 1
    rep['allowed'] = allowed
    rep['unclassified_n'] = len(uncl)
    rep['unclassified'] = [{'path': k[0], 'kind': k[1], 'why': k[2], 'count': n} for k, n in sorted(agg.items())]
    rep['a_k92'] = a_k92
    rep['r3_checks'] = r3chk
    rep['extra_allowed'] = extra_used
    rep['verdict'] = 'FAIL' if not rep['hard_same'] else ('HOLD' if uncl else 'PASS')
    rep['only_wallclock'] = all(wallclock(p, k, a, b) for p, k, a, b in dd)
    rep['n_wallclock'] = sum(1 for p, k, a, b in dd if wallclock(p, k, a, b))
    rep['progress_same'] = (GA['H3']['/#progress_last'] is MISS and GB['H3']['/#progress_last'] is MISS) or \
        (GA['H3']['/#progress_last'] is not MISS and GA['H3']['/#progress_last'] == GB['H3']['/#progress_last'])
    del A, B, raw_o, raw_n
    return rep


def outside_closed(rep, dtype, closed):
    """Amendment 32 section 2.3: what lies outside the closed leaf list of that decision type (no verdict)."""
    leaves = closed['types'][dtype]['leaves']
    hard_l = {x['path'] for x in leaves if x['hard']}
    soft_l = {x['path'] for x in leaves if not x['hard']}
    out_h, in_h, out_s, in_s = [], [], [], []
    for grp in ('H2', 'H3', 'H4', 'H5'):
        for p in rep['hard'][grp]['paths']:
            (in_h if p in hard_l else out_h).append([grp, p])
    for u in rep['unclassified']:
        (in_s if u['path'] in soft_l else out_s).append(u)
    seen = {p for _, p in in_h} | {u['path'] for u in in_s}
    n_out = len(out_h) + len(out_s) + (0 if rep['csv_same'] else 1)
    return {'dtype': dtype, 'csv_same': rep['csv_same'], 'outside_n': n_out, 'outside_hard': out_h,
            'outside_unclassified': out_s, 'outside_leaves': sum(u['count'] for u in out_s),
            'in_list_hard': in_h, 'in_list_unclassified_paths': len(in_s), 'listed_not_seen': sorted((hard_l | soft_l)
                                                                                                    - seen),
            'would_truncate': any(len(rep['hard'][g]['paths']) >= 80 for g in ('H2', 'H3', 'H4', 'H5'))
            or len(rep['unclassified']) >= 200}


# ================================================================================================ selection (3.4)
def wsig(doc):
    def fmap(d):
        if not isinstance(d, dict):
            return None
        return {str(k): (float(v) if isnum(v) else ('#nonnum', repr(v))) for k, v in d.items()}
    diag = doc.get('diagnostics') if isinstance(doc.get('diagnostics'), dict) else {}
    seq = diag.get('sdmpc_prediction_sequence')
    fut = None
    if isinstance(seq, dict) and isinstance(seq.get('future'), list):
        fut = [fmap(r.get('green_times')) if isinstance(r, dict) else None for r in seq['future']]
    return {'g': fmap(doc.get('green_times')), 'o': fmap(doc.get('offsets')), 'f': fut}


def map_eq(c, w):
    if not isinstance(c, dict) or not isinstance(w, dict) or set(c) != set(w):
        return False
    for k in c:
        a, b = c[k], w[k]
        if isinstance(b, tuple) or not isnum(a) or float(a) != b:
            return False
    return True


def sig_ok(cs, w):
    if not isinstance(cs, dict):
        return False
    if not map_eq(cs.get('green_times'), w['g']) or not map_eq(cs.get('offsets'), w['o']):
        return False
    cf, wf = cs.get('future_green_times'), w['f']
    if cf is None or wf is None:
        return cf is None and wf is None
    if len(cf) != len(wf):
        return False
    for a, b in zip(cf, wf):
        if a is None or b is None:
            if not (a is None and b is None):
                return False
        elif not map_eq(a, b):
            return False
    return True


def near(a, b, rel=1e-9):
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b
    if isnum(a) and isnum(b):
        a, b = float(a), float(b)
        if math.isnan(a) or math.isnan(b):
            return math.isnan(a) and math.isnan(b)
        return abs(a - b) <= rel * max(1.0, abs(a), abs(b))
    if isinstance(a, dict) and isinstance(b, dict):
        return set(a) == set(b) and all(near(a[k], b[k], rel) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(near(x, y, rel) for x, y in zip(a, b))
    return a == b


def reselect(hook, doc, T):
    hook = Path(hook)
    w = wsig(doc)
    errs = []
    names = sorted(p.name for p in hook.iterdir()) if hook.is_dir() else []
    errs += [n for n in names if n.startswith('hook_error_') or n.startswith('hook_setup_error_')]
    loaded = []
    for n in names:
        if n.startswith('loaded_') and n.endswith('.json'):
            j = jload(hook / n)
            if j is None:
                errs.append('unreadable ' + n)
                continue
            loaded.append(j)
    if any(x.get('recorder_ok') is not True for x in loaded):
        errs.append('recorder_ok')
    cands = []
    for n in names:
        d = hook / n
        if not (n.startswith('c_') and d.is_dir()):
            continue
        if not (d / 'cand.json').is_file() or not (d / 'k92_record.json').is_file():
            errs.append('incomplete ' + n)
            continue
        m = jload(d / 'cand.json') or {}
        m1 = sig_ok(m.get('signature'), w)
        m2 = (m.get('first_row_start_sec') == float(T) and m.get('dt_sec') == 150.0
              and isinstance(m.get('n_residence_rows'), int) and not isinstance(m.get('n_residence_rows'), bool)
              and m.get('n_residence_rows') > 0)
        cands.append({'folder': n, 'pid': m.get('pid'), 'seq': m.get('seq'), 'is_ad': bool(m.get('is_ad')),
                      'time_ns': m.get('time_ns'), 'm1': m1, 'm2': m2, 'match': m1 and m2,
                      'n_states': m.get('n_states'), 'g_equal_written': map_eq((m.get('signature') or {}).get(
                          'green_times'), w['g'])})
    match = sorted([c for c in cands if c['match']],
                   key=lambda c: (c['is_ad'], c['time_ns'] or 0, c['pid'] or 0, c['seq'] or 0))
    res = {'n_candidates': len(cands), 'n_match': len(match), 'candidates': cands, 'errors': errs, 'chosen': None}
    if errs:
        res['status'] = 'hook_error'
    elif not any(x.get('argv0') == ADAPTER for x in loaded):
        res['status'] = 'no_hook'
    elif not cands:
        res['status'] = 'no_candidate'
    elif not match:
        res['status'] = 'no_match'
    else:
        recs = [jload(hook / c['folder'] / 'k92_record.json') or {} for c in match]
        if all(near(r.get('blocks'), recs[0].get('blocks')) and near(r.get('horizon'), recs[0].get('horizon'))
               for r in recs[1:]):
            res['status'] = 'selected'
            c = match[0]
            res['chosen'] = {'folder': c['folder'], 'record_sha256': fsha(hook / c['folder'] / 'k92_record.json'),
                             'series_sha256': fsha(hook / c['folder'] / 'k92_series.npz')
                             if (hook / c['folder'] / 'k92_series.npz').is_file() else None,
                             'n_states': c['n_states']}
        else:
            res['status'] = 'match_conflict'
    return res


# ================================================================================================ hook names (33 6.5)
TOKEN = r'[0-9]+_[0-9]+_[0-9a-f]{16}'
RX_LOADED = re.compile(r'^loaded_(%s)\.json$' % TOKEN)
RX_CAND = re.compile(r'^c_(%s)_([0-9]{4,})$' % TOKEN)
RX_ERR = re.compile(r'^hook_error_(%s)\.txt$' % TOKEN)
RX_SERR = re.compile(r'^hook_setup_error_(%s)\.txt$' % TOKEN)
RX_SERR_NT = re.compile(r'^hook_setup_error_[0-9]+_notoken\.txt$')
RX_OLDFORM = re.compile(r'^(loaded_[0-9]+\.json|c_[0-9]+_[0-9]{4,}|hook_error_[0-9]+\.txt|hook_setup_error_[0-9]+\.txt)$')


def hook_names(hook):
    hook = Path(hook)
    out = {'present': hook.is_dir()}
    if not hook.is_dir():
        out['ok'] = False
        return out
    loaded, cands, bad, errs, old = {}, {}, [], [], []
    inner_bad, inner_missing = [], []
    for p in sorted(hook.iterdir(), key=lambda q: q.name):
        n = p.name
        m = RX_LOADED.match(n)
        if m and p.is_file():
            loaded[m.group(1)] = jload(p) or {}
            continue
        m = RX_CAND.match(n)
        if m and p.is_dir():
            inner = sorted(q.name for q in p.iterdir())
            c = jload(p / 'cand.json') or {}
            cands.setdefault(m.group(1), []).append({'seq_name': int(m.group(2)), 'seq': c.get('seq'),
                                                     'pid': c.get('pid'), 'time_ns': c.get('time_ns')})
            if not ('cand.json' in inner and 'k92_record.json' in inner):
                inner_missing.append(n)
            if not ('cand.json' in inner and 'k92_record.json' in inner and
                    set(inner) <= {'cand.json', 'k92_record.json', 'k92_series.npz'}):
                inner_bad.append(n)
            continue
        if (RX_ERR.match(n) or RX_SERR.match(n) or RX_SERR_NT.match(n)) and p.is_file():
            errs.append(n)
            continue
        if RX_OLDFORM.match(n):
            old.append(n)
        bad.append(n)
    toks = sorted(set(loaded) | set(cands))
    pair = all(t in loaded for t in cands)
    pid_ok = True
    for t in toks:
        tp = int(t.split('_')[0])
        if t in loaded and loaded[t].get('pid') != tp:
            pid_ok = False
        for c in cands.get(t, []):
            if c['pid'] != tp:
                pid_ok = False
    seq_ok = all(sorted(c['seq_name'] for c in cs) == list(range(1, len(cs) + 1)) and
                 all(c['seq'] == c['seq_name'] for c in cs) for cs in cands.values())
    by_pid = {}
    for t in toks:
        by_pid.setdefault(int(t.split('_')[0]), []).append(t)
    groups = {pid: ts for pid, ts in by_pid.items() if len(ts) > 1}
    overlaps = []
    for pid, ts in groups.items():
        spans = []
        for t in ts:
            tn = [c['time_ns'] for c in cands.get(t, []) if isnum(c['time_ns'])]
            if tn:
                spans.append((min(tn), max(tn), t))
        spans.sort()
        for i in range(len(spans)):
            for k in range(i + 1, len(spans)):
                if spans[k][0] <= spans[i][1]:
                    overlaps.append([pid, spans[i][2], spans[k][2]])
    n_adapter = sum(1 for v in loaded.values() if v.get('argv0') == ADAPTER)
    out.update({'n_names': len(list(hook.iterdir())), 'n_loaded': len(loaded), 'n_tokens': len(toks),
                'n_tokens_with_candidates': len(cands), 'n_candidates': sum(len(v) for v in cands.values()),
                'n_errors': len(errs), 'errors': errs, 'bad_names': bad, 'old_form': old,
                'inner_bad': inner_bad, 'inner_missing': inner_missing, 'n_adapter_loaded': n_adapter,
                'recorder_ok_all': all(v.get('recorder_ok') is True for v in loaded.values()),
                'c1_name': not bad and not inner_bad, 'c2_no_error': not errs, 'c3_pair': pair and pid_ok,
                'c4_seq': seq_ok, 'same_pid_groups': {str(k): v for k, v in groups.items()},
                'same_pid_time_overlap': overlaps})
    out['ok'] = out['c1_name'] and out['c2_no_error'] and out['c3_pair'] and out['c4_seq']
    return out


# ================================================================================================ VB-I2 .. VB-I7
def dec_files_of_T(dec, T):
    s = t6(T)
    return sorted(p.name for p in Path(dec).iterdir() if p.is_file() and s in p.name) if Path(dec).is_dir() else []


def count_text(p, needle):
    p = Path(p)
    if not p.is_file():
        return 0
    return sum(1 for line in p.read_text(encoding='utf-8', errors='replace').splitlines() if needle in line)


def i2_one(doc, names, T, exits, dfc, exception=None):
    md = doc.get('metadata') if isinstance(doc, dict) and isinstance(doc.get('metadata'), dict) else {}
    c = {'exit0': all(e == 0 for e in exits) and len(exits) >= 1,
         'no_hold_name': not [n for n in names if 'hold' in n.lower()],
         'no_error_txt': not [n for n in names if n.endswith('.error.txt')],
         'no_decision_failed': dfc == 0,
         'controller_status_ok': md.get('controller_status') == 'ok',
         'no_exception_key': not [k for k in md if 'exception' in k.lower()],
         'snapshot_sec_T': isnum(md.get('head_observation_snapshot_sec')) and
         float(md['head_observation_snapshot_sec']) == float(T)}
    pdisc = md.get('head_observation_prior_discarded')
    if exception is None:
        c['prior_discarded_0'] = isnum(pdisc) and float(pdisc) == 0.0
    else:
        k = exception['key']
        md1 = (exception['t1'] or {}).get('metadata') or {}
        c['prior_discarded_exception'] = isnum(pdisc) and float(pdisc) == 1.0 and isnum(md.get(k)) and \
            float(md[k]) == S and isnum(md1.get(k)) and float(md1[k]) == S
    return {'ok': all(c.values()), 'checks': c}


def jdiff_paths(a, b, p=''):
    if isinstance(a, dict) and isinstance(b, dict):
        out = []
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                out.append(p + '/' + k)
            else:
                out += jdiff_paths(a[k], b[k], p + '/' + k)
        return out
    return [] if (type(a) is type(b) and a == b) else [p]


def i3_arm(base, arm, want):
    A, B = jload(base), jload(arm)
    paths = jdiff_paths(A, B)
    u = (B or {}).get('urban') or {}
    ev = {'sc109w_through_saturation': u.get('sc109w_through_saturation') or {},
          'head_floor_seed': (u.get('capacity') or {}).get('head_floor_seed') or {}}
    evs = {}
    for k, v in ev.items():
        f = VBT / str(v.get('evidence') or '')
        evs[k] = {'evidence': v.get('evidence'), 'pinned': v.get('evidence_sha256'),
                  'file_sha256': fsha(f) if f.is_file() else None}
        evs[k]['ok'] = evs[k]['file_sha256'] is not None and evs[k]['pinned'] == evs[k]['file_sha256']
    c = {'paths_exactly_two': sorted(paths) == ARM_PATHS, 'evidence_ok': all(v['ok'] for v in evs.values()),
         'file_sha': fsha(arm) == want}
    return {'ok': all(c.values()), 'checks': c, 'paths': paths, 'evidence': evs, 'arm_sha256': fsha(arm)}


# ================================================================================================ VB-M (24 14.1, 32 3.6)
def doc_fields(doc, fkey):
    md = doc.get('metadata') if isinstance(doc.get('metadata'), dict) else {}
    jls = md.get('joint_leader_selection') if isinstance(md.get('joint_leader_selection'), dict) else {}
    g = doc.get('green_times') if isinstance(doc.get('green_times'), dict) else {}
    w, h, s = fnum(jls.get('warm_start_objective')), fnum(jls.get('held_objective')), fnum(jls.get('selected_objective'))
    return {'p2': fnum(g.get('SC109_p2')), 'p3': fnum(g.get('SC109_p3')), 'p4': fnum(g.get('SC109_p4')),
            'floor': fnum(md.get(fkey)), 'floor_keys_n': sum(1 for k in md if k.startswith(FLOOR_PREFIX)),
            'seed_binding': fnum(md.get('k92_hb_seed_binding')),
            'groups_carried': fnum(md.get('head_observation_groups_carried')),
            'groups_updated': fnum(md.get('head_observation_groups_updated')),
            'k92_w': 'k92_w' in md, 'k92_hb': 'k92_hb' in md,
            'selection_status': jls.get('selection_status') if jls else None, 'omega': s,
            'warm_gt_held': (w > h) if (w is not None and h is not None) else None,
            'selected_gt_held': (s > h) if (s is not None and h is not None) else None,
            'decision_wall_sec': fnum(md.get('decision_wall_sec')), 'sdmpc_active': md.get('sdmpc_active')}


REC_KEYS = ('chain_T450', 'chain_blocks', 'chain_max_450', 'w_bound_ratio', 'e_out_over_220', 'outw', 'feed4',
            'feed4_ratio', 'phantom_end', 'n_states')


def record_fields(rec_dir, T, sel):
    import numpy as np
    if sel['status'] != 'selected':
        return dict({k: None for k in REC_KEYS}, rec_status=sel['status']), None
    r = jload(Path(rec_dir) / 'k92_record.json') or {}
    hz = r.get('horizon') or {}
    blocks = r.get('blocks') or []
    out = {'rec_status': 'selected', 'chain_T450': fnum(hz.get('m1_chain_T450')),
           'chain_blocks': [fnum(b.get('chain_sum')) for b in blocks[:3]],
           'e_out_over_220': fnum(hz.get('e_out_max_over_220')), 'outw': fnum(hz.get('outw_veh_h_450')),
           'feed4': fnum(hz.get('feed4_veh_h_450')), 'phantom_end': fnum(hz.get('phantom_end_450')),
           'n_states': sel['chosen'].get('n_states')}
    wb, wd = hz.get('w_capacity_bound_steps'), hz.get('w_steps_with_departures')
    out['w_bound_ratio'] = float(wb) / float(wd) if isnum(wb) and isnum(wd) and wd != 0 else None
    out['feed4_ratio'] = out['feed4'] / out['outw'] if out['outw'] is not None and out['feed4'] is not None \
        and out['outw'] > 0 else None
    cons = {}
    z = np.load(Path(rec_dir) / 'k92_series.npz', allow_pickle=True)
    keys = [str(k) for k in z['keys']]
    te = np.asarray(z['t_end'], dtype=float)
    mod = np.asarray(z['model'], dtype=float)
    col = {k: keys.index(k) for k in CHAIN3 + (E_OUT, PHANTOM) if k in keys}
    best = None
    if all(k in col for k in CHAIN3):
        for i in range(len(te)):
            if T < te[i] <= T + 450.0:
                vals = [float(mod[i, col[k]]) for k in CHAIN3]
                if all(math.isfinite(v) for v in vals):
                    sm = math.fsum(vals)
                    best = sm if best is None or sm > best else best
    out['chain_max_450'] = best
    # consistency of the record with its own series (report only)
    for k in (1, 2, 3):
        tk = T + 150.0 * k
        idx = [i for i in range(len(te)) if abs(te[i] - tk) < 1e-6]
        if idx and all(c in col for c in CHAIN3):
            vals = [float(mod[idx[-1], col[c]]) for c in CHAIN3]
            v = math.fsum(vals) if all(math.isfinite(x) for x in vals) else None
        else:
            v = None
        cons['block%d_chain' % k] = near(v, out['chain_blocks'][k - 1] if len(out['chain_blocks']) >= k else None,
                                         1e-12)
    if E_OUT in col:
        eo = [float(mod[i, col[E_OUT]]) for i in range(len(te)) if te[i] <= T + 450.0 + 1e-9
              and math.isfinite(float(mod[i, col[E_OUT]]))]
        cons['e_out_max_over_220'] = near(max(eo) / 220.0 if eo else None, out['e_out_over_220'], 1e-12)
    if PHANTOM in col:
        idx = [i for i in range(len(te)) if abs(te[i] - (T + 450.0)) < 1e-6]
        pv = float(mod[idx[-1], col[PHANTOM]]) if idx else None
        pv = pv if pv is not None and math.isfinite(pv) else None
        cons['phantom_end_450'] = near(pv, out['phantom_end'], 1e-12)
    return out, cons


def chain_summary(rows):
    rs = sorted(rows, key=lambda r: r['T'])
    p3 = [(r['T'], r['p3']) for r in rs]
    low = [T for T, v in p3 if v is not None and v <= LOW_P3]
    deltas = [b - a for (Ta, a), (Tb, b) in zip(p3, p3[1:]) if a is not None and b is not None]
    big = [d for d in deltas if abs(d) >= BIG_DP3]
    flips = sum(1 for x, y in zip(big, big[1:]) if (x > 0) != (y > 0))
    st = {}
    for r in rs:
        st[str(r['selection_status'])] = st.get(str(r['selection_status']), 0) + 1
    out = {'n': len(rs), 'n_p3_le_24_5': len(low), 'first_T_p3_le_24_5': min(low) if low else None,
           'n_deltas': len(deltas), 'sign_changes': flips,
           'mean_abs_dp3': math.fsum(abs(d) for d in deltas) / len(deltas) if deltas else None,
           'n_k92_w': sum(1 for r in rs if r['k92_w']), 'n_k92_hb': sum(1 for r in rs if r['k92_hb']),
           'selection_status_counts': st, 'n_warm_gt_held': sum(1 for r in rs if r['warm_gt_held'] is True),
           'n_selected_gt_held': sum(1 for r in rs if r['selected_gt_held'] is True),
           'n_seed_binding_1': sum(1 for r in rs if r['seed_binding'] == 1.0)}
    if rs and rs[0]['side'] != 'REC':
        d = [r['T'] for r in rs if not r['csv_same_as_rec']]
        out['first_T_csv_differs'] = min(d) if d else None
        out['n_select_selected'] = sum(1 for r in rs if r.get('select_status') == 'selected')
    return out


# ================================================================================================ archive (33 5 (d))
def listing(root, extra=None):
    rows = []
    base = lp(root)
    for d, dirs, names in os.walk(base):
        dirs.sort()
        rel = os.path.relpath(d, base).replace('\\', '/')
        for n in sorted(names):
            st = os.stat(os.path.join(d, n))
            rows.append([rel + '/' + n, st.st_size, round(st.st_mtime, 6)])
    if extra is not None:
        st = os.stat(lp(extra))
        rows.append(['../' + Path(extra).name, st.st_size, round(st.st_mtime, 6)])
    return {'rows': len(rows), 'sha256': hashlib.sha256(json.dumps(rows).encode()).hexdigest(),
            'bytes': sum(r[1] for r in rows), 'max_mtime': max((r[2] for r in rows), default=None)}


# ================================================================================================ compare with driver
class Cmp:
    def __init__(self):
        self.n, self.diffs, self.maxrel = 0, [], 0.0

    def eq(self, where, mine, theirs):
        self.n += 1
        ok = self._eq(mine, theirs)
        if not ok:
            self.diffs.append({'where': where, 'mine': mine, 'driver': theirs})
        return ok

    def _eq(self, a, b):
        if isinstance(a, bool) or isinstance(b, bool):
            return a is b
        if isnum(a) and isnum(b):
            a, b = float(a), float(b)
            if math.isnan(a) or math.isnan(b):
                return math.isnan(a) and math.isnan(b)
            r = abs(a - b) / max(1.0, abs(a), abs(b))
            self.maxrel = max(self.maxrel, r)
            return r <= 1e-12
        if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
            return len(a) == len(b) and all(self._eq(x, y) for x, y in zip(a, b))
        if isinstance(a, dict) and isinstance(b, dict):
            return set(a) == set(b) and all(self._eq(a[k], b[k]) for k in a)
        return a == b


# ================================================================================================ run
def whyc(w):
    """Reason words differ between tools except the D codes and 'not allowed'; compare those only."""
    return w if w in ('D1', 'D2', 'D2b', 'D3', 'D4', 'D5', 'not allowed') else '*'


def dec_paths(key, arm, T):
    cd = VBR / 'chain' / ('%s_%s' % (key, arm))
    s = t6(T)
    return {'cd': cd, 'dec': cd / 'dec', 'json': cd / 'dec' / ('action_%s.json' % s),
            'csv': cd / 'dec' / ('action_%s.csv' % s), 'hook': cd / 'hook' / ('t' + s), 'rec': cd / 'rec' / ('t' + s),
            'done': cd / 'done' / ('t%s.json' % s), 'run': cd / 'dec' / ('run_t%s.json' % s),
            'prog': cd / 'dec' / ('action_%s.joint.progress.jsonl' % s)}


def rr_dir(run):
    return RR / run / ('decisions_' + run)


def run_all():
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    closed = jload(CLOSED)
    fkeys = jload(VALUES)['p0_2']['f_expected_floor_keys']
    res = {'tool_sha256': fsha(__file__), 'started': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
           'closed_sha256': fsha(CLOSED), 'values_sha256': fsha(VALUES)}
    log = []

    def say(msg):
        line = '%s %s' % (time.strftime('%H:%M:%S'), msg)
        log.append(line)
        print(line, flush=True)

    # ---------------------------------------------------------------- inventory
    stages = sorted(p.name for p in (VBR / 'stages').glob('*.json'))
    stops = sorted(p.name for p in VBR.glob('STOP_vb_*'))
    res['inventory'] = {'stages': stages, 'stop_files': stops}
    say('inventory stages=%d stops=%d' % (len(stages), len(stops)))

    # ---------------------------------------------------------------- VB-I1 (4) + report-only (10)
    i1, ro = {}, {}
    for c in CHAINS:
        for idx, T in enumerate(c['off']):
            P = dec_paths(c['key'], 'off', T)
            rep = compare_dec(rr_dir(c['run']), P['dec'], T, VBT, c['old_root'])
            name = '%s/T%s' % (c['chain'], t6(T))
            if idx == 0:
                sd = T >= 900
                d5 = (len(rep.get('a_k92', [])) >= 1 and all(x['ok'] and x['new_is_root_rs'] and x['old_is_root_rs']
                                                             for x in rep['a_k92'])) if sd else None
                i1[name] = {'verdict': rep['verdict'], 'hard_same': rep.get('hard_same'),
                            'unclassified_n': rep.get('unclassified_n'), 'allowed': rep.get('allowed'),
                            'a_k92_rows': len(rep.get('a_k92', [])), 'd5_root_check': d5,
                            'pass': rep['verdict'] == 'PASS' and d5 is not False, 'csv_same': rep.get('csv_same'),
                            'unclassified': rep.get('unclassified')}
            else:
                dtype = [d['type'] for d in closed['decisions'] if d['chain'] == c['chain'] and int(d['T']) == T][0]
                view = outside_closed(rep, dtype, closed) if rep['verdict'] != 'INCOMPLETE' else {'incomplete': True}
                ro[name] = {'chain': c['chain'], 'T': T, 'prev_T': c['off'][idx - 1], 'dtype': dtype,
                            'verdict_reference_only': rep['verdict'], 'view': view,
                            'unclassified_n': rep.get('unclassified_n'), 'allowed': rep.get('allowed')}
            say('compare %s %s' % (name, rep['verdict']))
    res['VB_I1'] = i1
    res['VB_I1_pass'] = len(i1) == 4 and all(v['pass'] for v in i1.values())
    tok_paths, non_tok = set(), []
    a_dec, b_paths, b_leaves = 0, 0, 0
    for k, v in ro.items():
        vw = v['view']
        n = vw.get('outside_n')
        if n:
            a_dec += 1
        b_paths += n or 0
        b_leaves += vw.get('outside_leaves') or 0
        for u in vw.get('outside_unclassified') or []:
            if 'action_token' in u['path']:
                tok_paths.add(u['path'])
            else:
                non_tok.append([k, u])
        for h in vw.get('outside_hard') or []:
            non_tok.append([k, {'hard': h}])
        if not vw.get('csv_same', True):
            non_tok.append([k, 'csv differs'])
    r1 = set(R1_ACTION_TOKEN_PATHS)
    res['reportonly'] = {'decisions': ro, 'a_decisions_with_outside': a_dec, 'b_outside_paths_total': b_paths,
                         'b_outside_leaves_total': b_leaves, 'action_token_distinct': sorted(tok_paths),
                         'vs_r1_same': len(tok_paths & r1), 'vs_r1_new': sorted(tok_paths - r1),
                         'vs_r1_gone': sorted(r1 - tok_paths), 'non_action_token_outside': non_tok}

    # ---------------------------------------------------------------- per decision: VB-I2, VB-I7, names, selection, M
    rows_all, i2_rows, i7_rows, names_rows, sel_rows, cons_rows = [], [], [], [], [], []
    plan = []
    for arm in ('off', 'b1'):
        for c in CHAINS:
            for T in (c['off'] if arm == 'off' else c['times']):
                plan.append((arm, c, T))
    i4 = []
    docs_floor = {}
    t1_b1_doc_md = None
    for arm, c, T in plan:
        P = dec_paths(c['key'], arm, T)
        i4.append({'chain': c['chain'], 'arm': arm, 'T': T, 'json': P['json'].is_file(), 'csv': P['csv'].is_file()})
        doc = jload(P['json'])
        names = dec_files_of_T(P['dec'], T)
        runrec = jload(P['run']) or {}
        done = jload(P['done']) or {}
        exits = [runrec.get('exit'), done.get('exit')]
        dfc = count_text(P['dec'] / ('action_%s.stdout.txt' % t6(T)), 'DECISION_FAILED') + \
            count_text(P['dec'] / ('action_%s.stderr.txt' % t6(T)), 'DECISION_FAILED')
        fkey = fkeys[c['run']]
        exc = None
        if c['chain'] == 'VB-41w' and arm == 'b1' and T == 150:
            exc = {'key': fkey, 't1': {'metadata': t1_b1_doc_md or {}}}
        i2 = i2_one(doc or {}, names, T, exits, dfc, exc)
        i2['ok'] = i2['ok'] and doc is not None
        if c['chain'] == 'VB-41w' and arm == 'b1' and T == 1 and doc is not None:
            md = doc.get('metadata') or {}
            t1_b1_doc_md = {k: md[k] for k in md if k.startswith(FLOOR_PREFIX)}
        i2_rows.append({'chain': c['chain'], 'arm': arm, 'T': T, 'ok': i2['ok'], 'checks': i2['checks'],
                        'dfc': dfc, 'exits': exits})
        # hook names + VB-I7 + selection
        hn = hook_names(P['hook'])
        sel = reselect(P['hook'], doc or {}, T)
        drv_sel = jload(P['rec'] / 'k92_select.json') or {}
        i7 = {'c1_loaded': hn.get('n_loaded', 0) >= 1 and hn.get('n_adapter_loaded') == 1 and hn.get('recorder_ok_all'),
              'c2_no_hook_error': hn.get('n_errors', 1) == 0,
              'c3_candidates_complete': hn.get('present', False) and not hn.get('inner_missing'),
              'c4_select_status': drv_sel.get('status') in SEL_OK}
        i7_rows.append({'chain': c['chain'], 'arm': arm, 'T': T, 'ok': all(i7.values()), 'checks': i7})
        names_rows.append(dict({'chain': c['chain'], 'arm': arm, 'T': T}, **{k: hn.get(k) for k in (
            'ok', 'c1_name', 'c2_no_error', 'c3_pair', 'c4_seq', 'n_loaded', 'n_tokens', 'n_tokens_with_candidates',
            'n_candidates', 'n_errors', 'bad_names', 'old_form', 'same_pid_groups', 'same_pid_time_overlap',
            'n_adapter_loaded')}))
        rec_sha = fsha(P['rec'] / 'k92_record.json') if (P['rec'] / 'k92_record.json').is_file() else None
        npz_sha = fsha(P['rec'] / 'k92_series.npz') if (P['rec'] / 'k92_series.npz').is_file() else None
        sel_rows.append({'chain': c['chain'], 'arm': arm, 'T': T, 'status': sel['status'],
                         'n_candidates': sel['n_candidates'], 'n_match': sel['n_match'],
                         'chosen': (sel['chosen'] or {}).get('folder'),
                         'record_bytes_equal': (sel['chosen'] is None and rec_sha is None) or
                         (sel['chosen'] is not None and sel['chosen']['record_sha256'] == rec_sha
                          and sel['chosen']['series_sha256'] == npz_sha),
                         'driver': {'status': drv_sel.get('status'), 'n_candidates': drv_sel.get('n_candidates'),
                                    'n_match': drv_sel.get('n_match'),
                                    'chosen': (drv_sel.get('chosen') or {}).get('folder')},
                         'sdmpc_active': ((doc or {}).get('metadata') or {}).get('sdmpc_active'),
                         'cands_m1': sum(1 for x in sel['candidates'] if x['m1']),
                         'cands_m2': sum(1 for x in sel['candidates'] if x['m2']),
                         'cands_green_equal': sum(1 for x in sel['candidates'] if x['g_equal_written'])})
        # metrics row
        row = {'chain': c['chain'], 'side': arm.upper(), 'T': T}
        row.update(doc_fields(doc or {}, fkey))
        row['csv_sha256'] = fsha(P['csv']) if P['csv'].is_file() else None
        row['wall_run_sec'] = fnum(runrec.get('wall_sec'))
        rf, cons = record_fields(P['rec'], T, sel)
        row.update(rf)
        row['select_status'] = sel['status']
        if cons is not None:
            cons_rows.append({'chain': c['chain'], 'arm': arm, 'T': T, 'cons': cons})
        if arm == 'b1':
            docs_floor.setdefault(c['chain'], []).append((T, {k: v for k, v in ((doc or {}).get('metadata') or
                                                                               {}).items()
                                                              if k.startswith(FLOOR_PREFIX)}))
        row['green_times'] = (doc or {}).get('green_times')
        rows_all.append(row)
        del doc
        say('decision %s %s T=%d i2=%s i7=%s names=%s sel=%s' % (c['chain'], arm, T, i2['ok'], all(i7.values()),
                                                                 hn.get('ok'), sel['status']))
    # REC side (RR record decisions)
    for c in CHAINS:
        for T in c['times']:
            jp, cp = rr_dir(c['run']) / ('action_%s.json' % t6(T)), rr_dir(c['run']) / ('action_%s.csv' % t6(T))
            doc = jload(jp) or {}
            row = {'chain': c['chain'], 'side': 'REC', 'T': T}
            row.update(doc_fields(doc, fkeys[c['run']]))
            row['csv_sha256'] = fsha(cp)
            row['wall_run_sec'] = None
            row.update({k: None for k in REC_KEYS})
            row['green_times'] = doc.get('green_times')
            rows_all.append(row)
            del doc
    rec_csv = {(r['chain'], r['T']): r['csv_sha256'] for r in rows_all if r['side'] == 'REC'}
    for r in rows_all:
        if r['side'] != 'REC':
            r['csv_same_as_rec'] = r['csv_sha256'] == rec_csv[(r['chain'], r['T'])]
        if r['side'] == 'B1' and r['chain'] == 'VB-41w':
            recf = [x for x in rows_all if x['side'] == 'REC' and x['chain'] == 'VB-41w' and x['T'] == r['T']][0]['floor']
            want = max(recf, S) if recf is not None else S
            r['floor_eq_max_rec_seed'] = r['floor'] is not None and r['floor'] == want
    chains_m = []
    for c in CHAINS:
        for side in ('REC', 'OFF', 'B1'):
            rs = [r for r in rows_all if r['chain'] == c['chain'] and r['side'] == side]
            chains_m.append(dict({'chain': c['chain'], 'side': side}, **chain_summary(rs)))
    # VB-I6
    i6 = {}
    for c in CHAINS:
        lst = sorted(docs_floor.get(c['chain'], []), key=lambda x: x[0])
        vals, okk = [], True
        for T, md in lst:
            ks = sorted(md)
            v = fnum(md[ks[0]]) if len(ks) == 1 else None
            okk = okk and len(ks) == 1 and ks[0] == fkeys[c['run']] and v is not None
            vals.append(v)
        nondec = all(a is not None and b is not None and b >= a for a, b in zip(vals, vals[1:]))
        ent = {'n': len(lst), 'one_key_right_name': okk, 'non_decreasing': nondec, 'values': vals}
        if c['chain'] == 'VB-41w':
            tv = {T: v for (T, _), v in zip(lst, vals)}
            ent['t150_eq_t1_eq_seed'] = tv.get(1) == S and tv.get(150) == S
        ent['ok'] = okk and nondec and ent.get('t150_eq_t1_eq_seed', True)
        i6[c['chain']] = ent
    # VB-I3
    i3 = {'CFG-B1': i3_arm(VBT / N31 / 'config_n31_v2.json', VBT / N31 / 'config_n31_v2_k92b1.json', CFG_B1_SHA),
          'SAF-B1': i3_arm(VBT / N31 / 'config_n31_v2_stopline_observed_full_k91.json', VBR / SAFB1_REL, SAF_B1_SHA)}
    res['VB_I2'] = {'ok': all(r['ok'] for r in i2_rows), 'rows': i2_rows}
    res['VB_I3'] = dict(i3, ok=all(v['ok'] for v in i3.values()))
    res['VB_I4'] = {'ok': len(i4) == 55 and all(x['json'] and x['csv'] for x in i4) and
                    sum(1 for x in i4 if x['arm'] == 'b1') == 41 and sum(1 for x in i4 if x['arm'] == 'off') == 14,
                    'n': len(i4), 'missing': [x for x in i4 if not (x['json'] and x['csv'])]}
    res['VB_I6'] = dict(i6, ok=all(v['ok'] for v in i6.values()))
    res['VB_I7'] = {'ok': all(r['ok'] for r in i7_rows), 'rows': i7_rows}
    res['VB_I2_off_ok'] = all(r['ok'] for r in i2_rows if r['arm'] == 'off')
    res['VB_I7_off_ok'] = all(r['ok'] for r in i7_rows if r['arm'] == 'off')
    res['selection'] = {'rows': sel_rows,
                        'sdmpc_counts': {}, 'agree_with_driver': True, 'record_bytes_equal_all': True}
    for r in sel_rows:
        if r['sdmpc_active']:
            res['selection']['sdmpc_counts'][r['status']] = res['selection']['sdmpc_counts'].get(r['status'], 0) + 1
        if (r['status'], r['n_candidates'], r['n_match'], r['chosen']) != (
                r['driver']['status'], r['driver']['n_candidates'], r['driver']['n_match'], r['driver']['chosen']):
            res['selection']['agree_with_driver'] = False
        if not r['record_bytes_equal']:
            res['selection']['record_bytes_equal_all'] = False
    res['record_series_consistency'] = {'rows': cons_rows,
                                        'all_true': all(all(v for v in x['cons'].values()) for x in cons_rows)}

    # ---------------------------------------------------------------- ZI (z2)-(z6) + names of the 3 ZI hook folders
    zi = {}
    for cell, run, T in ZI:
        cd = VBR / 'zi' / cell
        rep = compare_dec(cd / 'replay_off', cd / 'replay_on', T, VBT, VBT)
        stray = [str(p) for p in cd.rglob('loaded_*') if 'hook_on' not in p.relative_to(cd).parts] + \
            [str(p) for p in cd.rglob('c_*') if 'hook_on' not in p.relative_to(cd).parts]
        ron = jload(cd / 'replay_on' / ('run_t%s.json' % t6(T))) or {}
        roff = jload(cd / 'replay_off' / ('run_t%s.json' % t6(T))) or {}
        hn = hook_names(cd / 'hook_on')
        doc_on = jload(cd / 'replay_on' / ('action_%s.json' % t6(T))) or {}
        sel = reselect(cd / 'hook_on', doc_on, T)
        drv_sel = jload(cd / 'rec_on' / 'k92_select.json') or {}
        del doc_on
        zi[cell] = {'z2_csv_same': rep.get('csv_same'), 'z3_verdict': rep['verdict'],
                    'z4_progress_same': rep.get('progress_same'), 'z5_only_wallclock': rep.get('only_wallclock'),
                    'n_diff_leaves': rep.get('n_diff_total'), 'n_wallclock': rep.get('n_wallclock'),
                    'z6_no_stray_hook_files': not stray, 'stray': stray[:10],
                    'exit_off': roff.get('exit'), 'exit_on': ron.get('exit'),
                    'wall_ratio_on_off': (fnum(ron.get('wall_sec')) / fnum(roff.get('wall_sec')))
                    if fnum(ron.get('wall_sec')) and fnum(roff.get('wall_sec')) else None,
                    'names': {k: hn.get(k) for k in ('ok', 'c1_name', 'c2_no_error', 'c3_pair', 'c4_seq', 'n_loaded',
                                                     'n_tokens', 'n_candidates', 'same_pid_groups',
                                                     'same_pid_time_overlap', 'n_adapter_loaded')},
                    'select': {'status': sel['status'], 'n_candidates': sel['n_candidates'], 'n_match': sel['n_match'],
                               'chosen': (sel['chosen'] or {}).get('folder'),
                               'driver_status': drv_sel.get('status'),
                               'driver_chosen': (drv_sel.get('chosen') or {}).get('folder')}}
        zi[cell]['pass_z2_z6'] = bool(rep.get('csv_same')) and rep['verdict'] == 'PASS' and \
            bool(rep.get('progress_same')) and bool(rep.get('only_wallclock')) and not stray
        names_rows.append(dict({'chain': 'ZI', 'arm': cell, 'T': T}, **zi[cell]['names'], bad_names=hn.get(
            'bad_names'), old_form=hn.get('old_form'), n_errors=hn.get('n_errors'),
            n_tokens_with_candidates=hn.get('n_tokens_with_candidates')))
        say('ZI %s z2..z6=%s' % (cell, zi[cell]['pass_z2_z6']))
    res['ZI'] = zi
    tot = lambda k: sum((r.get(k) or 0) for r in names_rows)  # noqa: E731
    res['hook_names'] = {'n_folders': len(names_rows), 'all_ok': all(r['ok'] for r in names_rows),
                         'loaded': tot('n_loaded'), 'tokens': tot('n_tokens'), 'candidates': tot('n_candidates'),
                         'errors': tot('n_errors'), 'bad_names': sum(len(r.get('bad_names') or []) for r in names_rows),
                         'old_form': sum(len(r.get('old_form') or []) for r in names_rows),
                         'same_pid_groups': [[r['chain'], r['arm'], r['T'], r['same_pid_groups']] for r in names_rows
                                             if r.get('same_pid_groups')],
                         'overlaps': [[r['chain'], r['arm'], r['T'], r['same_pid_time_overlap']] for r in names_rows
                                      if r.get('same_pid_time_overlap')],
                         'adapter_loaded_one_each': all(r.get('n_adapter_loaded') == 1 for r in names_rows),
                         'rows': names_rows}

    # ---------------------------------------------------------------- derived report numbers (B1 - OFF, same T)
    def row(chain, side, T):
        x = [r for r in rows_all if r['chain'] == chain and r['side'] == side and r['T'] == T]
        return x[0] if x else None
    shared = []
    for c in CHAINS:
        for T in c['off']:
            b, o = row(c['chain'], 'B1', T), row(c['chain'], 'OFF', T)
            if b and o and b['outw'] is not None and o['outw'] is not None:
                shared.append({'chain': c['chain'], 'T': T, 'd_omega': b['omega'] - o['omega']
                               if b['omega'] is not None and o['omega'] is not None else None,
                               'd_outw': b['outw'] - o['outw'], 'd_feed4': b['feed4'] - o['feed4'],
                               'd_p3': (b['p3'] - o['p3']) if b['p3'] is not None and o['p3'] is not None else None})
    res['derived'] = {'b1_minus_off_shared': shared, 'n_shared': len(shared)}
    for k in ('d_omega', 'd_outw', 'd_feed4'):
        v = [x[k] for x in shared if x[k] is not None]
        res['derived'][k + '_range'] = [min(v), max(v)] if v else None
    no_match = [r for r in sel_rows if r['status'] == 'no_match']
    nm = []
    for r in no_match:
        c = [x for x in CHAINS if x['chain'] == r['chain']][0]
        times = c['off'] if r['arm'] == 'off' else c['times']
        i = times.index(r['T'])
        cur = row(r['chain'], r['arm'].upper(), r['T'])
        prev = row(r['chain'], r['arm'].upper(), times[i - 1]) if i > 0 else None
        nm.append({'chain': r['chain'], 'arm': r['arm'], 'T': r['T'], 'n_candidates': r['n_candidates'],
                   'cands_m1': r['cands_m1'], 'cands_m2': r['cands_m2'], 'cands_green_equal': r['cands_green_equal'],
                   'green_equal_previous_decision': (cur or {}).get('green_times') == (prev or {}).get('green_times')
                   if prev else None, 'selection_status': (cur or {}).get('selection_status')})
    res['derived']['no_match'] = nm

    # ---------------------------------------------------------------- archive (amendment 33 section 5 (d), 6.5)
    v0 = jload(VBR / 'check_v0.json') or {}
    at = v0.get('archive_tree') or {}
    lv = listing(OLD_VBT, OLD_VBT_BUILD)
    lr = listing(OLD_VBR)
    res['archive'] = {'v0_archive_tree': at, 'v0_ok': at.get('sha256') == ARCH_VBT_SHA and at.get('files') == ARCH_VBT_ROWS,
                      'old_vbt_now': lv, 'old_vbt_ok': lv['sha256'] == ARCH_VBT_SHA and lv['rows'] == ARCH_VBT_ROWS,
                      'old_vbr_now': lr, 'old_vbr_ok': lr['sha256'] == ARCH_VBR_SHA and lr['rows'] == ARCH_VBR_FILES,
                      'stop_r1_copies': [[str(p), fsha(p) == STOP_R1_SHA] for p in STOP_R1]}
    res['archive']['ok'] = res['archive']['v0_ok'] and res['archive']['old_vbt_ok'] and res['archive']['old_vbr_ok'] \
        and all(x[1] for x in res['archive']['stop_r1_copies'])
    say('archive ok=%s' % res['archive']['ok'])

    # ================================================================ compare with the driver's files
    C = Cmp()
    dv1 = jload(VBR / 'judge' / 'vb_i1.json') or {}
    for k, v in i1.items():
        d = (dv1.get('VB_I1') or {}).get(k) or {}
        drep = d.get('report') or {}
        C.eq('VB_I1/%s/verdict' % k, v['verdict'], d.get('verdict'))
        C.eq('VB_I1/%s/hard' % k, 'SAME' if v['hard_same'] else 'DIFFERENT', d.get('hard_verdict'))
        C.eq('VB_I1/%s/unclassified_n' % k, v['unclassified_n'], drep.get('unclassified_n'))
        C.eq('VB_I1/%s/allowed' % k, v['allowed'], drep.get('allowed_counts'))
        C.eq('VB_I1/%s/a_k92_rows' % k, v['a_k92_rows'], d.get('a_k92_rows'))
        C.eq('VB_I1/%s/d5' % k, v['d5_root_check'], d.get('d5_root_check'))
        C.eq('VB_I1/%s/pass' % k, v['pass'], d.get('pass'))
    C.eq('VB_I1_pass', res['VB_I1_pass'], dv1.get('VB_I1_pass'))
    C.eq('VB_I2_off_ok', res['VB_I2_off_ok'], dv1.get('VB_I2_off_ok'))
    C.eq('VB_I7_off_ok', res['VB_I7_off_ok'], dv1.get('VB_I7_off_ok'))
    dro = jload(VBR / 'judge' / 'vb_reportonly.json') or {}
    for k, v in ro.items():
        d = ((dro.get('decisions') or {}).get(k) or {}).get('view') or {}
        C.eq('RO/%s/outside_n' % k, v['view'].get('outside_n'), d.get('outside_n'))
        C.eq('RO/%s/outside_unclassified' % k,
             sorted([u['path'], u['kind'], whyc(u['why']), u['count']] for u in v['view'].get('outside_unclassified')
                    or []),
             sorted([u.get('path'), u.get('kind'), whyc(u.get('why')), u.get('count')]
                    for u in d.get('outside_unclassified') or []))
        C.eq('RO/%s/outside_hard' % k, sorted(v['view'].get('outside_hard') or []),
             sorted([x.get('group'), x.get('path')] for x in d.get('outside_hard') or []))
        C.eq('RO/%s/in_list_hard' % k, sorted(v['view'].get('in_list_hard') or []),
             sorted([x.get('group'), x.get('path')] for x in d.get('in_list_hard') or []))
        C.eq('RO/%s/csv_same' % k, v['view'].get('csv_same'), d.get('h1_csv_same'))
        C.eq('RO/%s/listed_not_seen' % k, v['view'].get('listed_not_seen'), d.get('listed_not_seen'))
        C.eq('RO/%s/verdict_ref' % k, v['verdict_reference_only'], d.get('verdict_reference_only'))
    dvi = jload(VBR / 'judge' / 'vb_i.json') or {}
    drows = {(r['chain'], r['arm'], r['T']): r for r in dvi.get('rows') or []}
    for r in i2_rows:
        d = drows.get((r['chain'], r['arm'], r['T'])) or {}
        C.eq('VB_I2/%s/%s/%s' % (r['chain'], r['arm'], r['T']), r['ok'], (d.get('VB_I2') or {}).get('ok'))
    for r in i7_rows:
        d = drows.get((r['chain'], r['arm'], r['T'])) or {}
        C.eq('VB_I7/%s/%s/%s' % (r['chain'], r['arm'], r['T']), r['ok'], (d.get('VB_I7') or {}).get('ok'))
    for k in ('VB_I2', 'VB_I3', 'VB_I4', 'VB_I6', 'VB_I7'):
        C.eq('%s_ok' % k, res[k]['ok'], dvi.get('%s_ok' % k))
    for ch, v in i6.items():
        d = (dvi.get('VB_I6') or {}).get(ch) or {}
        C.eq('VB_I6/%s/values' % ch, v['values'], [r.get('value') for r in d.get('rows') or []])
    C.eq('select_counts_sdmpc', res['selection']['sdmpc_counts'], dvi.get('select_counts_sdmpc'))
    dvm = jload(VBR / 'judge' / 'vb_m.json') or {}
    dmr = {(r['chain'], r['side'], r['T']): r for r in dvm.get('rows') or []}
    FIELDS = ('p2', 'p3', 'p4', 'floor', 'floor_keys_n', 'seed_binding', 'groups_carried', 'groups_updated', 'k92_w',
              'k92_hb', 'selection_status', 'omega', 'warm_gt_held', 'selected_gt_held', 'decision_wall_sec',
              'csv_sha256', 'wall_run_sec', 'chain_T450', 'chain_blocks', 'chain_max_450', 'w_bound_ratio',
              'e_out_over_220', 'outw', 'feed4', 'feed4_ratio', 'phantom_end', 'n_states')
    C.eq('VB_M/n_rows', len(rows_all), len(dvm.get('rows') or []))
    for r in rows_all:
        d = dmr.get((r['chain'], r['side'], r['T']))
        if d is None:
            C.eq('VB_M/%s/%s/%s/present' % (r['chain'], r['side'], r['T']), True, False)
            continue
        for f in FIELDS:
            C.eq('VB_M/%s/%s/%s/%s' % (r['chain'], r['side'], r['T'], f), r.get(f), d.get(f))
        if r['side'] != 'REC':
            C.eq('VB_M/%s/%s/%s/select_status' % (r['chain'], r['side'], r['T']), r['select_status'],
                 d.get('select_status'))
            C.eq('VB_M/%s/%s/%s/csv_same_as_rec' % (r['chain'], r['side'], r['T']), r['csv_same_as_rec'],
                 d.get('csv_same_as_rec'))
        if 'floor_eq_max_rec_seed' in r:
            C.eq('VB_M/%s/%s/%s/floor_eq_max_rec_seed' % (r['chain'], r['side'], r['T']), r['floor_eq_max_rec_seed'],
                 d.get('floor_eq_max_rec_seed'))
    dmc = {(x['chain'], x['side']): x for x in dvm.get('chains') or []}
    for x in chains_m:
        d = dmc.get((x['chain'], x['side'])) or {}
        for f, v in x.items():
            if f in ('chain', 'side', 'n_seed_binding_1'):
                continue
            C.eq('VB_M_chain/%s/%s/%s' % (x['chain'], x['side'], f), v, d.get(f))
    zij = jload(VBR / 'zi' / 'zi.json') or {}
    for cell, v in zi.items():
        dz = jload(VBR / 'zi' / cell / 'zi_judge.json') or {}
        ck = dz.get('checks') or {}
        C.eq('ZI/%s/z2' % cell, v['z2_csv_same'], ck.get('z2'))
        C.eq('ZI/%s/z3' % cell, v['z3_verdict'] == 'PASS', ck.get('z3'))
        C.eq('ZI/%s/z4' % cell, v['z4_progress_same'], ck.get('z4'))
        C.eq('ZI/%s/z5' % cell, v['z5_only_wallclock'], ck.get('z5'))
        C.eq('ZI/%s/z6' % cell, v['z6_no_stray_hook_files'], ck.get('z6'))
        C.eq('ZI/%s/ratio' % cell, v['wall_ratio_on_off'], (dz.get('report_only') or {}).get('wall_on_over_off'))
        C.eq('ZI/%s/select' % cell, v['select']['status'], (dz.get('z7') or {}).get('status'))
        C.eq('ZI/%s/n_diff' % cell, v['n_diff_leaves'], (dz.get('zi_judge') or {}).get('n_diff_leaves'))
    C.eq('ZI/pass', all(v['pass_z2_z6'] for v in zi.values()), zij.get('pass'))
    rc = jload(VBR / 'recalc' / 'recalc.json') or {}
    res['driver_recalc'] = {'equal': rc.get('equal'), 'n_compared': rc.get('n_compared'), 'n_diff': rc.get('n_diff')}
    res['compare_with_driver'] = {'n_compared': C.n, 'n_diff': len(C.diffs), 'max_rel_numeric': C.maxrel,
                                  'diffs': C.diffs[:300]}
    for r in rows_all:
        r.pop('green_times', None)
    res['VB_M_rows'] = rows_all
    res['VB_M_chains'] = chains_m
    res['log'] = log
    res['sec'] = round(time.time() - t0, 1)
    dest = OUT / 'vvb3_recalc.json'
    if dest.exists():
        raise SystemExit('output exists (never reused): %s' % dest)
    dest.write_text(json.dumps(res, indent=1, default=str, ensure_ascii=False), encoding='utf-8')
    print('VVB3_RECALC done compare n=%d diff=%d maxrel=%.3g sec=%.1f sha=%s' % (
        C.n, len(C.diffs), C.maxrel, res['sec'], fsha(dest)), flush=True)
    return 0


# ================================================================================================ self-test
def selftest():
    """Synthetic cases only (no V-B file is read)."""
    global KNOWN_OLD_RS  # noqa: PLW0603
    out = {}
    tmp = Path(tempfile.mkdtemp(prefix='vvb3st_'))
    try:
        root = tmp / 'root'
        (root / 'evaluation' / 'controllers').mkdir(parents=True)
        (root / RS_REL).write_bytes(b'rs')
        (root / CAO_REL).write_bytes(b'cao')
        old_root = tmp / 'oldroot'
        (old_root / 'evaluation' / 'controllers').mkdir(parents=True)
        (old_root / RS_REL).write_bytes(b'rs-old')

        base = {'green_times': {'SC109_p3': 30.0}, 'offsets': {'SC109': 0.0},
                'metadata': {'controller_status': 'ok', 'decision_wall_sec': 10.0,
                             'joint_leader_selection': {'selected_objective': 1.5, 'held_objective': 2.0,
                                                        'warm_start_objective': 1.7, 'selection_status': 'improved',
                                                        'trial_rows': [{'action_token': 'aa', 'wall_sec': 1.0}],
                                                        'frozen_context_token': 'ab' * 16},
                             'run_provenance': {'inputs': {'state_json': {'path': 'D:\\x\\a\\state.json'}}}},
                'prediction': {'wall_sec': 3.0}}

        def mk(name, doc, csv=b'a,b\r\n'):
            d = tmp / name
            d.mkdir()
            (d / 'action_003000.json').write_text(json.dumps(doc), encoding='utf-8')
            (d / 'action_003000.csv').write_bytes(csv)
            return d

        import copy
        o = mk('o', base)
        cases = {}
        n1 = copy.deepcopy(base)
        n1['metadata']['decision_wall_sec'] = 99.0
        n1['prediction']['wall_sec'] = 9.0
        n1['metadata']['joint_leader_selection']['trial_rows'][0]['wall_sec'] = 5.0
        n1['metadata']['run_provenance']['inputs']['state_json']['path'] = 'D:\\y\\b\\state.json'
        n1['metadata']['joint_leader_selection']['frozen_context_token'] = 'cd' * 16
        cases['wall_V_F1_pass'] = compare_dec(o, mk('n1', n1), 3000, root, old_root)['verdict'] == 'PASS'
        n2 = copy.deepcopy(base)
        n2['green_times']['SC109_p3'] = 31.0
        cases['green_fail'] = compare_dec(o, mk('n2', n2), 3000, root, old_root)['verdict'] == 'FAIL'
        n3 = copy.deepcopy(base)
        n3['metadata']['joint_leader_selection']['trial_rows'][0]['action_token'] = 'bb'
        r3 = compare_dec(o, mk('n3', n3), 3000, root, old_root)
        cases['d1_hold'] = r3['verdict'] == 'HOLD' and r3['unclassified'][0]['why'] == 'D1'
        cases['csv_fail'] = compare_dec(o, mk('n4', base, b'x'), 3000, root, old_root)['verdict'] == 'FAIL'
        n5 = copy.deepcopy(base)
        n5['metadata']['joint_leader_selection']['selected_objective'] = 1.5000000001
        cases['objective_fail'] = compare_dec(o, mk('n5', n5), 3000, root, old_root)['verdict'] == 'FAIL'
        n6 = copy.deepcopy(base)
        n6['metadata']['head_discharge_floor_173_p4_x'] = 5.0
        cases['head_key_fail'] = compare_dec(o, mk('n6', n6), 3000, root, old_root)['verdict'] == 'FAIL'
        # A_K92: RS key on both sides, old = old_root RS sha (made a known value by the test), new = root RS sha
        rsk = 'D:\\VISSIM-merge\\k8_gate_trees\\k92b1\\vb2_e27ceac8\\evaluation\\controllers\\runtime_setup.py'
        known = next(iter(KNOWN_OLD_RS))
        (old_root / RS_REL).write_bytes(b'rs-old')
        b7o = copy.deepcopy(base)
        b7o['metadata']['joint_leader_selection']['tangent_derivatives'] = [{'transformed_source_sha256': {rsk: known}}]
        b7n = copy.deepcopy(base)
        b7n['metadata']['joint_leader_selection']['tangent_derivatives'] = [
            {'transformed_source_sha256': {rsk: fsha(root / RS_REL)}}]
        o7 = mk('o7', b7o)
        r7 = compare_dec(o7, mk('n7', b7n), 3000, root, old_root)
        cases['a_k92_old_root_mismatch_hold'] = r7['verdict'] == 'HOLD' and r7['a_k92'][0]['old_is_root_rs'] is False
        saved = KNOWN_OLD_RS
        KNOWN_OLD_RS = saved | {fsha(old_root / RS_REL)}
        b7o2 = copy.deepcopy(base)
        b7o2['metadata']['joint_leader_selection']['tangent_derivatives'] = [
            {'transformed_source_sha256': {rsk: fsha(old_root / RS_REL)}}]
        r7b = compare_dec(mk('o7b', b7o2), tmp / 'n7', 3000, root, old_root)
        cases['a_k92_pass'] = r7b['verdict'] == 'PASS' and r7b['allowed'].get('A_K92') == 1
        KNOWN_OLD_RS = saved
        cases['n_tree_root'] = nstr('D:\\VISSIM-merge\\k8_gate_trees\\k92b1\\vvb3_e27ceac8\\evaluation\\a.py') == \
            '<root>/evaluation/a.py' and nstr('D:/VISSIM-merge/k8_gate_trees/k92b1/a25/k92b1_probe.build.json') != \
            '<root>.build.json'
        cases['n_run'] = nstr('D:\\VISSIM_runs\\20261004_sdmpc31_k8\\sdmpc31_v3c3_k8j1r_s31\\x') == '<run>/x'
        # outside_closed
        closed = {'types': {'SS': {'leaves': [{'path': '/prediction_error/source_action_json', 'hard': 'H5'},
                                              {'path': '/metadata/x/source', 'hard': None}]}}}
        rep = {'csv_same': True, 'hard': {'H2': {'paths': []}, 'H3': {'paths': []}, 'H4': {'paths': []},
                                          'H5': {'paths': ['/prediction_error/source_action_json']}},
               'unclassified': [{'path': '/metadata/x/source', 'kind': 'value', 'why': 'not allowed', 'count': 1},
                                {'path': '/metadata/y/action_token', 'kind': 'value', 'why': 'D1', 'count': 3}]}
        oc = outside_closed(rep, 'SS', closed)
        cases['outside_closed'] = oc['outside_n'] == 1 and oc['outside_leaves'] == 3 and not oc['listed_not_seen']
        # selection
        hook = tmp / 'hook'
        hook.mkdir()
        tok1, tok2 = '4242_100_' + '0' * 16, '4242_200_' + '1' * 16
        (hook / ('loaded_%s.json' % tok1)).write_text(json.dumps({'pid': 4242, 'argv0': ADAPTER, 'recorder_ok': True}))
        (hook / ('loaded_%s.json' % tok2)).write_text(json.dumps({'pid': 4242, 'argv0': 'w.py', 'recorder_ok': True}))
        doc = {'green_times': {'A': 1.0, 'B': 2}, 'offsets': {'A': 0.0}}

        def cand(tok, seq, g, tns, ad=False, start=3000.0):
            d = hook / ('c_%s_%04d' % (tok, seq))
            d.mkdir()
            (d / 'cand.json').write_text(json.dumps({'seq': seq, 'pid': 4242, 'time_ns': tns, 'is_ad': ad,
                                                     'signature': {'green_times': g, 'offsets': {'A': 0.0},
                                                                   'future_green_times': None},
                                                     'first_row_start_sec': start, 'dt_sec': 150.0,
                                                     'n_residence_rows': 9, 'n_states': 3}))
            (d / 'k92_record.json').write_text(json.dumps({'blocks': [1], 'horizon': {'a': 1.0}}))
        cand(tok2, 1, {'A': 1.0, 'B': 2.0}, 300, ad=True)
        cand(tok2, 2, {'A': 1.0, 'B': 2.0}, 400)
        cand(tok2, 3, {'A': 1.5, 'B': 2.0}, 200)
        s1 = reselect(hook, doc, 3000)
        cases['select_nonad_first'] = s1['status'] == 'selected' and s1['chosen']['folder'].endswith('_0002')
        s2 = reselect(hook, doc, 3150)
        cases['select_T_no_match'] = s2['status'] == 'no_match'
        hn = hook_names(hook)
        cases['names_ok'] = hn['ok'] and hn['n_tokens'] == 2 and list(hn['same_pid_groups']) == ['4242']
        (hook / 'c_4242_0005').mkdir()
        hn2 = hook_names(hook)
        cases['names_oldform_caught'] = not hn2['ok'] and hn2['old_form'] == ['c_4242_0005']
        (hook / 'c_4242_0005').rmdir()
        cand(tok1, 2, {'A': 1.0, 'B': 2.0}, 500)
        hn3 = hook_names(hook)
        cases['seq_gap_caught'] = not hn3['c4_seq']
        # metrics: M3 flips
        rows = [{'T': T, 'p3': v, 'side': 'REC', 'k92_w': False, 'k92_hb': False, 'selection_status': None,
                 'warm_gt_held': None, 'selected_gt_held': None, 'seed_binding': None}
                for T, v in ((3000, 30.0), (3150, 31.0), (3300, 30.2), (3450, 30.4), (3600, 29.0))]
        cs = chain_summary(rows)
        cases['m3_flips'] = cs['n_deltas'] == 4 and cs['sign_changes'] == 1 and abs(cs['mean_abs_dp3'] - 0.85) < 1e-12
        # archive listing form
        lt = tmp / 'lst'
        (lt / 'a').mkdir(parents=True)
        (lt / 'z.txt').write_bytes(b'1')
        (lt / 'a' / 'b.txt').write_bytes(b'22')
        ls = listing(lt)
        rows_l = []
        for d, dirs, names in os.walk(str(lt)):
            dirs.sort()
            for n in sorted(names):
                st = os.stat(os.path.join(d, n))
                rows_l.append([os.path.relpath(d, str(lt)).replace('\\', '/') + '/' + n, st.st_size,
                               round(st.st_mtime, 6)])
        cases['listing_prefix_free_same'] = ls['sha256'] == hashlib.sha256(json.dumps(rows_l).encode()).hexdigest() \
            and rows_l[0][0] == './z.txt'
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)
    out['cases'] = cases
    out['ok'] = all(cases.values())
    out['tool_sha256'] = fsha(__file__)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'vvb3_selftest.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
    print('VVB3_SELFTEST ok=%s %s' % (out['ok'], {k: v for k, v in cases.items() if not v}), flush=True)
    return 0 if out['ok'] else 1


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    if cmd == 'selftest':
        sys.exit(selftest())
    if cmd == 'run':
        sys.exit(run_all())
    print(__doc__)
    sys.exit(2)
