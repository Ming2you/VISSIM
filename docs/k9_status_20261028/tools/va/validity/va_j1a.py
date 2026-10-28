r"""V-A run validity (K8 amendment 34 sec.7.1) = amended J1-A (amendment 21 sec.4.1, policy-on run, D-K9-22 reading;
expected provenance = amendment 34 sec.7.1 table) + hold audit H-A1..H-A9 (amendment 21 sec.4.2) + J1-V pairing
(prefix form, same method as SP/j1/analysis/tools/pair_prefix_s31r.py) + report-only facts named in amendment 34
sec.7.1 (T = 150 head_observation_prior_discarded, T list of other 1.0 values) and in the V-A validity task
(K9-2 keys k92_w / k92_hb / one (173, p4) floor key per decision, decision wall clock, run folder unchanged after EXIT,
.err copies, FZP last frame time).

Usage (python -B, PYTHONHASHSEED=0; the process sets itself BELOW_NORMAL):
  va_j1a.py check   --profile {va|j1r|j1} --seed S --out <json>
  va_j1a.py pair    --profile {va|j1r|j1} --seed S --out <json>
  va_j1a.py freeze  --profile {va|j1r} --out <json>
  va_j1a.py ha_unit --dir <G-H1 case dir> --T <T> --out <json>   (self-test of the receipt-level H-A code on a gate output)
Profiles (seeds limited to 31 / 41 / 43; sealed seeds and v3c3-s47 are refused):
  va  = V-A run D:\VISSIM_runs\20261023_sdmpc31_k92\sdmpc31_v3c3_k92va_s<S>, FRZ_K92 sdmpc31_c20aff1d_202610230833,
        head c20aff1d7bf0..., FREEZE.json 011f5be2..., tuning c8e3ee2c..., network 3de889f0..., policy on.
  j1r = J1 s31 rerun (self-test only), FRZ_K8b, head b9734abe..., FREEZE.json 6143d3eb..., tuning d0f9ef39..., policy on.
  j1  = J1 s41 / s43 (self-test only), FRZ_K8, head 74cd495f..., tuning 5f0d0e40..., policy off. For a policy-off run the
        original J1-A definition applies (amendment 21 sec.4 head line); the items that exist only in the policy-on
        definition (freeze sha, env, runlog policy line, seed) are reported 'n/a' and not counted.
Read-only toward run folders, NC3 and frozen trees: files are only opened for reading; nothing is written there.
Blind (amendment 34 S-VA-4): no Omega, TTT, indicators 1-4, delay, objective or green value is put in the output. Action
JSONs are parsed one at a time; kept are key presence, statuses, the VSL and meter command values that the declared items
need (VSL box, U9-a, MTR), file hashes and the previous-action pin. The stage1 prefix scan computes prefix TTT internally
(tool structure); it is neither written nor printed.

Readings fixed here before any V-A data is read (amendment 21 sec.4.2 does not spell these out):
  H-A4 'previous-action source of T+150' = metadata.n31_binding.vsl_cohort_initialization {basename(source) ==
       action_<T>.json and sha256 == held JSON sha}; if T+150 is itself a hold, its receipt source.action_json.sha256 ==
       held JSON sha; if T+150 has an .error.txt, its frames / text carry no P-5 pair or message. T = 9000: vacuous.
  H-A6 rows of the runner action log action_<run>.csv at sim_sec T with the first (sim_sec) and last (readback) column
       removed == the held CSV data rows (same count, same order, raw CSV fields); vsl_readback.csv and
       signal_readback.csv have rows at T and every such row has ok == 1.
  Both comparators also run on every non-hold decision (report-only 'comparator_selftest') so that a wrong reading shows
  up on decisions that are known to be normal.
An item that cannot be computed is 'INCOMPLETE' (amendment 34 sec.7.1: INCOMPLETE -> STOP, never counted as true).
"""
import argparse
import csv
import ctypes
import datetime
import hashlib
import io
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from ctypes import wintypes

sys.dont_write_bytecode = True

RVA = r'D:\VISSIM_runs\20261023_sdmpc31_k92'
RR = r'D:\VISSIM_runs\20261004_sdmpc31_k8'
NC3_FMT = r'D:\VISSIM_runs\20261001_v3c3\s%s_v3c3nc\run'
STAGE1 = r'D:\VISSIM-merge\tools\stage1'
STAGE1_SHA = {
    'stage1_common.py': 'e000c69eebad2636c00299727ceb1624d408d5ac3c6ae26204301b1fa891fdae',
    'stage1_scan.py': '651c4f51fdddf49d46c77ed4c28b0626c410b3282426b9fd30f2a6ef43f7625f',
    'stage1_uninserted.py': '19eba94ed01bce47b591b47362aba13b2ac697cfbf2cb9156954b573e7727cd1',
    'stage1_report.py': 'cb4ccc3a431f32ebb6f716a0b67c148a71d82470c443b4851f80832d98d7a1b9',
}
NET_SHA = '3de889f0257d998bed50611f798ea388bcf69396dbc40e5726b1e88ebdd31c2e'
PROFILES = {
    'va': {'root': RVA, 'name': 'sdmpc31_v3c3_k92va_s%s', 'seeds': ('31', '41', '43'),
           'frz': r'D:\VISSIM-merge\frozen\sdmpc31_c20aff1d_202610230833',
           'head': 'c20aff1d7bf0c432cb4f20e2922bd406d857aa5d',
           'freeze': '011f5be253fd31a5fb8342859b2b571375e49b4bbbbb42ea8f3ca93657b68476',
           'tuning': 'c8e3ee2c99b66c255b2279f0aa18eaafc18d4c7689e59e260109fac3b7d71866', 'policy': True, 'k92': True},
    'j1r': {'root': RR, 'name': 'sdmpc31_v3c3_k8j1r_s%s', 'seeds': ('31',),
            'frz': r'D:\VISSIM-merge\frozen\sdmpc31_b9734abe_202610141821',
            'head': 'b9734abe1c83f95c9cec5fca5e42b7b18cd45991',
            'freeze': '6143d3eb0d455e5fde46b190b4d4d8c2a7068a96c7fc9178126b922af937c7b6',
            'tuning': 'd0f9ef395d4f9c51e6c68412f7c33abd546217e0d8cdc59d3c620183fa7aaec6', 'policy': True, 'k92': False},
    'j1': {'root': RR, 'name': 'sdmpc31_v3c3_k8j1_s%s', 'seeds': ('41', '43'),
           'frz': r'D:\VISSIM-merge\frozen\sdmpc31_74cd495f_202610131824',
           'head': '74cd495f3b08312eb11384f4fcf06109a26c0cba', 'freeze': None,
           'tuning': '5f0d0e40a39e44b3c7601f23177afbad8c2eee23d4421626482f2244a86c3341', 'policy': False, 'k92': False},
}
POLICY = 'hold_previous_on_exception'
WD_POLICY_LINE = 'WD RW_DECISION_ERROR_POLICY='
M = {80.0: 81.0, 90.0: 91.0, 100.0: 101.0, 110.0: 110.0}
CMD_SET = {80.0, 90.0, 100.0, 110.0}
TIMES = [1] + [150 * k for k in range(1, 61)]
MAX_VSL_STEP = 40.0
PHYS7 = ('N_P_star', 'N_UF_star', 'ramp_metering', 'vsl', 'green_times', 'offsets', 'inflow_outflow_allocation')
W_AFTER_REPR = '5209.8'
FLOOR_RE = re.compile(r'^head_discharge_floor_173_p4_[0-9a-f]{16}$')
# amendment 21 P-4 / P-5 (closed lists; same text as scripts/decision_hold.py, re-implemented here, not imported)
EXCLUDED_TYPES = ('DecisionDeadline', 'TimeoutError', 'MemoryError', 'KeyboardInterrupt', 'GeneratorExit',
                  'BrokenProcessPool', 'BrokenPipeError', 'ConnectionResetError')
CONTRACT_PAIRS = (('vissim_stackelberg_adapter.py', 'load_joint_historical_reference'),
                  ('vissim_stackelberg_adapter.py', 'joint_runtime_source_pins'),
                  ('vissim_stackelberg_adapter.py', 'control_from_json'),
                  ('sdmpc.py', 'load_prices'),
                  ('physical_ramp_branches.py', 'read_recorded_control'),
                  ('physical_ramp_branches.py', 'held_actual_reference'),
                  ('lane_plant_runtime.py', 'applied_vsl_from_previous'),
                  ('offramp_split_forecast.py', 'window_counts'),
                  ('area_meter_finalization.py', 'configure'))
CONTRACT_MESSAGES = ('Invalid applied central multiplier warm start',)
HEADER_RE = re.compile(r'^[A-Za-z_][\w.]*(: .*|:)?$')
FRAME_RE = re.compile(r'^\s*File "(.+)", line \d+, in (.+?)\s*$')
TRACEBACK_HEAD = 'Traceback (most recent call last):'
RECEIPT_KEYS = ('schema', 'hold_previous_on_exception', 'decision', 'exception', 'eligibility', 'source', 'held_output',
                'failed_partials', 'evidence', 'inputs', 'wall')
HOLD_DICT_KEYS = ('schema', 'policy', 'sim_sec', 'source_sim_sec', 'origin_sim_sec', 'chain_length', 'source_action_json',
                  'source_action_csv', 'carried_metadata_keys', 'removed', 'price_state', 'receipt')
REMOVED = ['prediction', 'prediction_error', 'projection_diagnostics', 'diagnostics.sdmpc_prediction_sequence']
CACHE_DIRS = ('__pycache__', '__tangentcache__', '.pytest_cache')
INC = 'INCOMPLETE'


def set_below_normal():
    k = ctypes.WinDLL('kernel32', use_last_error=True)
    k.GetCurrentProcess.restype = wintypes.HANDLE
    k.SetPriorityClass.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    k.GetPriorityClass.argtypes = [wintypes.HANDLE]
    k.GetPriorityClass.restype = wintypes.DWORD
    h = k.GetCurrentProcess()
    k.SetPriorityClass(h, 0x00004000)
    return k.GetPriorityClass(h)


def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def rd(p):
    with open(p, encoding='utf-8-sig', errors='replace') as f:
        return f.read()


def rcsv(p):
    with open(p, newline='', encoding='utf-8-sig') as h:
        return list(csv.DictReader(h))


def rcsv_raw(p):
    with open(p, newline='', encoding='utf-8-sig') as h:
        r = csv.reader(h)
        hdr = next(r, None)
        return hdr, list(r)


def lines_replace(p):
    with open(p, 'rb') as f:
        return [raw.decode('utf-8', errors='replace').rstrip('\r') for raw in f.read().split(b'\n')]


def header_type(line):
    if line == TRACEBACK_HEAD or not HEADER_RE.match(line):
        return None
    return line.split(':', 1)[0].split('.')[-1]


def frames(lines):
    out = []
    for line in lines:
        m = FRAME_RE.match(line)
        if m:
            out.append((re.split(r'[\\/]', m.group(1))[-1], m.group(2).strip()))
    return out


def parse_summary(line):
    rest = line[len('DECISION_FAILED type='):]
    head, sep, tb = rest.rpartition(' traceback=')
    if not sep:
        return None
    outer, _, rest2 = head.partition(' message=')
    message, _, root = rest2.partition(' root_error=')
    return {'type': outer.strip(), 'message': message.strip(), 'root_error': root.strip(), 'traceback': tb.strip()}


def typed_eq(a, b):
    """Equality that also requires the same Python type at every node and the same dict key order."""
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        return list(a.keys()) == list(b.keys()) and all(typed_eq(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(typed_eq(x, y) for x, y in zip(a, b))
    return a == b


def get(d, *path):
    for k in path:
        if not isinstance(d, dict):
            return None
        d = d.get(k)
    return d


def profile_paths(profile, seed):
    P = PROFILES[profile]
    if seed not in P['seeds']:
        raise SystemExit('seed %r not allowed for profile %s (allowed %s)' % (seed, profile, P['seeds']))
    name = P['name'] % seed
    run = os.path.join(P['root'], name)
    return P, name, run, os.path.join(run, 'decisions_' + name)


# ===================================================================================================== hold audit
def judge_error_text(err_lines, summary_line):
    """P-4 / P-5 re-judgement (H-A7): returns dict with hits (empty = not excluded / not contract)."""
    summary = parse_summary(summary_line) if summary_line else None
    types = [t for t in (header_type(x) for x in err_lines) if t]
    if summary:
        types += [t for t in (header_type(x) for x in (summary.get('type', ''), summary.get('root_error', '')) if x) if t]
    fr = frames(err_lines)
    text = '\n'.join(err_lines) + '\n' + (summary_line or '')
    return {'chain_types': types, 'excluded_hits': sorted({t for t in types if t in EXCLUDED_TYPES}),
            'contract_pair_hits': sorted({'%s:%s' % p for p in fr if p in CONTRACT_PAIRS}),
            'contract_message_hits': [m for m in CONTRACT_MESSAGES if m in text],
            'frames_last20': [f for _, f in fr][-20:]}


def signature(err_lines, summary_line):
    s = parse_summary(summary_line) if summary_line else None
    j = judge_error_text(err_lines, summary_line)
    root = re.sub(r'\d+', '', (s or {}).get('root_error', ''))
    return {'outer': (s or {}).get('type'), 'chain_types': sorted(set(j['chain_types'])), 'root_wo_digits': root}


def receipt_level_audit(dec_dir, T, src_dir, obs_dir):
    """H-A1, H-A2, H-A3, H-A5, H-A7 for one hold T (files only; no run log needed)."""
    t6, s6 = '%06d' % T, '%06d' % (T - 150)
    out = {'T': T}
    rp = os.path.join(dec_dir, 'action_%s.hold.json' % t6)
    if not os.path.isfile(rp):
        return {'T': T, 'error': 'receipt absent', 'HA1': INC, 'HA2': INC, 'HA3': INC, 'HA5': INC, 'HA7': INC}
    rec = json.loads(rd(rp))
    held_json_p = os.path.join(dec_dir, 'action_%s.json' % t6)
    held_csv_p = os.path.join(dec_dir, 'action_%s.csv' % t6)
    src_json_p = os.path.join(src_dir, 'action_%s.json' % s6)
    src_csv_p = os.path.join(src_dir, 'action_%s.csv' % s6)
    have = {p: os.path.isfile(p) for p in (held_json_p, held_csv_p, src_json_p, src_csv_p)}
    if not all(have.values()):
        out['missing'] = [os.path.basename(p) for p, v in have.items() if not v]
    held_json_sha = sha(held_json_p) if have[held_json_p] else None
    held_csv_sha = sha(held_csv_p) if have[held_csv_p] else None
    src_json_sha = sha(src_json_p) if have[src_json_p] else None
    src_csv_sha = sha(src_csv_p) if have[src_csv_p] else None
    # ---- H-A1 receipt items present, recorded sha == file sha
    c1 = {}
    c1['keys'] = all(k in rec for k in RECEIPT_KEYS)
    c1['schema'] = rec.get('schema') == 'hold-on-exception-receipt/v1'
    hd = rec.get('hold_previous_on_exception') or {}
    c1['hold_dict_keys'] = all(k in hd for k in HOLD_DICT_KEYS)
    dec = rec.get('decision') or {}
    c1['decision_keys'] = all(k in dec for k in ('exit_code', 'stdout', 'stderr', 'decision_failed_line', 'error_txt'))
    c1['decision_exit_1'] = dec.get('exit_code') == 1

    def pin_ok(pin, path):
        if pin == 'absent':
            return not os.path.isfile(path)
        return isinstance(pin, dict) and os.path.isfile(path) and pin.get('sha256') == sha(path)
    c1['stdout_pin'] = pin_ok(dec.get('stdout'), os.path.join(dec_dir, 'action_%s.stdout.txt' % t6))
    c1['stderr_pin'] = pin_ok(dec.get('stderr'), os.path.join(dec_dir, 'action_%s.stderr.txt' % t6))
    c1['error_txt_pin'] = pin_ok(dec.get('error_txt'), os.path.join(dec_dir, 'action_%s.error.txt' % t6))
    exc = rec.get('exception') or {}
    c1['exception_keys'] = all(k in exc for k in ('type', 'message_first_line', 'root_error', 'root_type',
                                                  'chain_header_types', 'traceback_functions_last20'))
    el = rec.get('eligibility') or {}
    c1['eligibility_all_pass'] = isinstance(el.get('checks'), dict) and sorted(el['checks']) == sorted('E%d' % i for i in range(1, 11)) \
        and all(v == 'pass' for v in el['checks'].values())
    c1['eligibility_lists'] = list(el.get('excluded_types') or []) == list(EXCLUDED_TYPES) and \
        [tuple(x) for x in (el.get('contract_pairs') or [])] == list(CONTRACT_PAIRS) and \
        list(el.get('contract_messages') or []) == list(CONTRACT_MESSAGES)
    src = rec.get('source') or {}
    c1['source_json_pin'] = get(src, 'action_json', 'sha256') == src_json_sha and get(src, 'action_json', 'name') == 'action_%s.json' % s6
    c1['source_csv_pin'] = get(src, 'action_csv', 'sha256') == src_csv_sha and get(src, 'action_csv', 'name') == 'action_%s.csv' % s6
    if src.get('kind') == 'sdmpc':
        ap = os.path.join(src_dir, 'action_%s.json.applied' % s6)
        c1['source_applied_or_receipt_pin'] = os.path.isfile(ap) and get(src, 'applied', 'sha256') == sha(ap)
    elif src.get('kind') == 'hold':
        pr = os.path.join(src_dir, 'action_%s.hold.json' % s6)
        c1['source_applied_or_receipt_pin'] = os.path.isfile(pr) and get(src, 'receipt', 'sha256') == sha(pr)
    else:
        c1['source_applied_or_receipt_pin'] = False
    c1['held_output_pins'] = get(rec, 'held_output', 'action_json', 'sha256') == held_json_sha and \
        get(rec, 'held_output', 'action_csv', 'sha256') == held_csv_sha
    ev = rec.get('evidence') or {}
    ev_bad = []
    for nm, want in ev.items():
        p = os.path.join(obs_dir, *nm.split('/')) if '/' in nm else os.path.join(dec_dir, nm)
        got = sha(p) if os.path.isfile(p) else 'absent'
        if got != want:
            ev_bad.append(nm)
    c1['evidence_pins'] = bool(ev) and not ev_bad
    out['HA1_detail'] = c1
    out['HA1_evidence_bad'] = ev_bad
    out['HA1'] = all(c1.values())
    # ---- H-A2 held CSV = source CSV (T-150)
    out['HA2'] = held_csv_sha is not None and held_csv_sha == src_csv_sha and get(hd, 'source_action_csv', 'sha256') == src_csv_sha \
        and hd.get('source_sim_sec') == T - 150
    # ---- H-A3 held JSON 7 physical fields (typed) = source JSON, metadata key set = P-6 set, no sdmpc_state, sim_sec = T
    if have[held_json_p] and have[src_json_p]:
        with open(held_json_p, 'rb') as f:
            hj = json.loads(f.read())
        with open(src_json_p, 'rb') as f:
            sj = json.loads(f.read())
        hm, sm = hj.get('metadata') or {}, sj.get('metadata') or {}
        want_keys = {'sim_sec', 'controller', 'controller_status', 'run_provenance', 'hold_previous_on_exception'}
        if 'controller_variant' in sm:
            want_keys.add('controller_variant')
        want_keys |= {k for k in sm if k.startswith(('far_rate_est_', 'sat_est_'))}
        c3 = {'phys7_typed_equal': all((k in hj) == (k in sj) and (k not in hj or typed_eq(hj[k], sj[k])) for k in PHYS7),
              'metadata_key_set': set(hm.keys()) == want_keys,
              'no_sdmpc_state': 'sdmpc_state' not in hm and 'sdmpc_state' not in hj,
              'sim_sec_T': isinstance(hm.get('sim_sec'), float) and hm.get('sim_sec') == float(T),
              'controller_status': hm.get('controller_status') == POLICY,
              'removed_absent': all(k not in hj for k in ('prediction', 'prediction_error', 'projection_diagnostics'))
              and 'sdmpc_prediction_sequence' not in (hj.get('diagnostics') or {}),
              'hold_dict_eq_receipt': typed_eq(hm.get('hold_previous_on_exception'), hd),
              'carried_far_sat_equal': all(typed_eq(hm.get(k), sm.get(k)) for k in sm if k.startswith(('far_rate_est_', 'sat_est_')))}
        out['HA3_detail'] = c3
        out['HA3'] = all(c3.values())
        del hj, sj
    else:
        out['HA3'] = INC
    # ---- H-A5 failed partials named .failed_decision with receipt sha; applied CSV is not the failed CSV
    fp = rec.get('failed_partials')
    on_disk = sorted(f for f in os.listdir(dec_dir) if f.startswith('action_%s.' % t6) and f.endswith('.failed_decision'))
    c5 = {'list': isinstance(fp, list)}
    if isinstance(fp, list):
        c5['names_match_disk'] = sorted(p.get('to') for p in fp) == on_disk
        c5['sha_match'] = all(os.path.isfile(os.path.join(dec_dir, p.get('to', ''))) and sha(os.path.join(dec_dir, p['to'])) == p.get('sha256')
                              for p in fp)
        failed_csv = [p for p in fp if p.get('from') == 'action_%s.csv' % t6]
        c5['held_csv_not_failed_csv'] = all(p.get('sha256') != held_csv_sha for p in failed_csv)
    out['HA5_detail'] = c5
    out['HA5'] = all(c5.values())
    # ---- H-A7 .error.txt re-judged by P-4 / P-5
    ep = os.path.join(dec_dir, 'action_%s.error.txt' % t6)
    stp = os.path.join(dec_dir, 'action_%s.stderr.txt' % t6)
    if os.path.isfile(ep) and os.path.isfile(stp):
        sl = [x for x in lines_replace(stp) if x.startswith('DECISION_FAILED type=')]
        el_ = lines_replace(ep)
        j = judge_error_text(el_, sl[0] if len(sl) == 1 else None)
        out['HA7_detail'] = {'summary_lines': len(sl), 'excluded_hits': j['excluded_hits'],
                             'contract_pair_hits': j['contract_pair_hits'], 'contract_message_hits': j['contract_message_hits']}
        out['HA7'] = len(sl) == 1 and not j['excluded_hits'] and not j['contract_pair_hits'] and not j['contract_message_hits']
        out['signature'] = signature(el_, sl[0] if len(sl) == 1 else None)
    else:
        out['HA7'] = INC
    return out


# ===================================================================================================== check
def check(profile, seed, out_path):
    t0 = time.time()
    prio = set_below_normal()
    P, NAME, RUN, DEC = profile_paths(profile, seed)
    POL = P['policy']
    res = {'tool': 'va_j1a.py check', 'tool_sha256': sha(os.path.abspath(__file__)), 'profile': profile, 'seed': seed,
           'name': NAME, 'run_dir': RUN, 'policy_on_definition': POL, 'priority': hex(prio),
           'started': datetime.datetime.now().astimezone().isoformat(timespec='seconds')}
    for p in (RUN, DEC):
        if not os.path.isdir(p):
            raise SystemExit('missing %s' % p)
    # ------------------------------------------------------------ runlog / launch / wmi
    runlog_p = os.path.join(RUN, 'runlog_%s.txt' % NAME)
    lines = rd(runlog_p).splitlines()
    kv = {}
    for l in lines:
        m = re.match(r'^([A-Z0-9_]+)=(\S*)$', l)
        if m:
            kv.setdefault(m.group(1), []).append(m.group(2))
    CNT = ('DECISIONS_OK', 'DECISIONS_FAILED', 'DECISIONS_HELD_ON_EXCEPTION', 'DECISION_ERROR_POLICY', 'STAGE', 'SIM_SEC',
           'OBSERVATION_FAILURES', 'SIGNAL_FAILURES', 'ACTION_FORMAT_FAILURES', 'COM_FAILURES', 'SIGNAL_NAME_RULE_FALLBACKS',
           'SIGNAL_MIDBLOCK_COM_SKIPS', 'SIGNAL_MIDBLOCK_PLAN_SKIPS', 'SIGNAL_WRITE_ATTEMPTS', 'SIGNAL_READBACK_OK',
           'SIGNAL_PERSISTENCE_CHECKS', 'SIGNAL_PERSISTENCE_OK', 'OBS150_BUNDLES', 'SIGNAL_COGREEN_BLOCKS',
           'OPTIONAL_ATT_SKIPS', 'SIGNAL_SG_PLAN_ENABLED')
    c = {k: kv.get(k) for k in CNT}
    res['runlog_counters'] = c
    res['runlog_error_lines'] = [l[:400] for l in lines if l.startswith('ERROR=')]
    res['runlog_warn_lines'] = [l[:200] for l in lines if l.startswith('WARN')]
    res['runlog_policy_lines'] = [l for l in lines if l.startswith('DECISION_ERROR_POLICY=')]
    res['runlog_held_summary_lines'] = [l for l in lines if l.startswith('DECISIONS_HELD_ON_EXCEPTION=')]
    hold_attempt_T = sorted(int(re.search(r'sim_sec=(\d+)', l).group(1)) for l in lines if l.startswith('DECISION_HOLD_ATTEMPT'))
    held_T = sorted(int(re.search(r'sim_sec=(\d+)', l).group(1)) for l in lines if l.startswith('DECISION_HELD_ON_EXCEPTION '))
    held_lines = {int(re.search(r'sim_sec=(\d+)', l).group(1)): l for l in lines if l.startswith('DECISION_HELD_ON_EXCEPTION ')}
    res['runlog_hold_attempt_T'] = hold_attempt_T
    res['runlog_held_T'] = held_T
    res['runlog_hold_failed_lines'] = [l[:300] for l in lines if 'DECISION_HOLD_FAILED' in l]
    cd, cd_idx = {}, {}
    for i, l in enumerate(lines):
        m = re.match(r'^CONTROLLER_DECISION sim_sec=(\d+) wall_sec=([0-9.]+) result=exit=(-?\d+)', l)
        if m:
            T = int(m.group(1))
            cd[T] = {'wall_sec': float(m.group(2)), 'exit': int(m.group(3)), 'decision_failed_in_line': l.count('DECISION_FAILED')}
            cd_idx[T] = i
    res['controller_decision_exit_wall'] = {str(k): [v['exit'], v['wall_sec']] for k, v in sorted(cd.items())}
    res['warmup_controller_T'] = [int(re.search(r'sim_sec=(\d+)', l).group(1)) for l in lines if l.startswith('WARMUP_CONTROLLER')]
    res['warmup_controller_names'] = sorted({re.search(r'controller=(\S+)', l).group(1) for l in lines if l.startswith('WARMUP_CONTROLLER')})
    res['run_mode'] = [l for l in lines if l.startswith('RUN_MODE=')]
    launch_p = os.path.join(RUN, 'launch_%s.log' % NAME)
    wmi_p = os.path.join(P['root'], 'wmi_%s.log' % NAME)
    launch = rd(launch_p).splitlines()
    wmi = rd(wmi_p).splitlines()
    res['launch_exit'] = [l for l in launch if re.search(r'\bEXIT %s code=' % re.escape(NAME), l)]
    res['wmi_exit'] = [l for l in wmi if re.search(r'\bEXIT %s code=' % re.escape(NAME), l)]
    res['watchdog_exit'] = [l for l in launch if 'WATCHDOG_EXIT' in l]
    res['watchdog_ok_fail'] = [l for l in launch if re.search(r'\b(OK|FAIL|EXIT_NO_DONE)\b %s' % re.escape(NAME), l)]
    res['freeze_verified'] = [l for l in launch if 'FREEZE_VERIFIED' in l]
    res['plan_detail'] = [l for l in launch if 'LAUNCH_PLAN_DETAIL' in l]
    res['netcopy'] = [l for l in launch if 'NETWORK_COPY_OK' in l]
    res['network_ok'] = [l for l in launch if 'NETWORK_OK' in l and 'NETWORK_COPY_OK' not in l]
    res['provenance_ok_lines'] = [l for l in launch if 'PROVENANCE_OK' in l]
    res['wd_policy_lines'] = [l for l in launch if WD_POLICY_LINE in l]
    res['wd_failfast_lines'] = [l for l in launch if 'WD RW_DECISION_FAIL_FAST=' in l]
    res['refused_or_not_launched_lines'] = [l for l in launch + wmi if 'REFUSED' in l or 'NOT_LAUNCHED' in l]
    res['start_lines'] = [l for l in launch if re.match(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}  START %s out_dir=' % re.escape(NAME), l)]
    res['attempt_dirs'] = sorted(f for f in os.listdir(RUN) if f.startswith('attempt_'))
    res['not_launched_files'] = sorted(f for f in os.listdir(RUN) if 'NOT_LAUNCHED' in f.upper())
    # ------------------------------------------------------------ decisions listing
    names = set(os.listdir(DEC))
    json_T = sorted(int(f[7:13]) for f in names if re.fullmatch(r'action_\d{6}\.json', f))
    err_files = sorted(f for f in names if f.endswith('.error.txt'))
    hold_error_files = sorted(f for f in names if f.endswith('.hold_error.txt'))
    receipt_T = sorted(int(f[7:13]) for f in names if re.fullmatch(r'action_\d{6}\.hold\.json', f))
    hold_cap = sorted(f for f in names if re.fullmatch(r'action_\d{6}\.hold\.(stdout|stderr)\.txt', f))
    failed_partials = sorted(f for f in names if f.endswith('.failed_decision'))
    error_T = sorted(int(f[7:13]) for f in err_files if re.fullmatch(r'action_\d{6}\.error\.txt', f))
    res.update({'error_files': err_files, 'hold_error_files': hold_error_files, 'hold_receipt_T': receipt_T,
                'hold_capture_files': hold_cap, 'failed_decision_files': failed_partials, 'decision_json_T': json_T,
                'n_json': len(json_T), 'n_warmup_json': sum(1 for t in json_T if t < 900),
                'n_sdmpc_json': sum(1 for t in json_T if t >= 900),
                'missing_expected_T': [t for t in TIMES if t not in json_T],
                'unexpected_T': [t for t in json_T if t not in TIMES]})
    res['other_file_kinds'] = dict(Counter(re.sub(r'\d+', 'N', f) for f in names
                                           if not re.fullmatch(r'action_\d{6}\.(json|csv|decision_budget\.json|stdout\.txt|stderr\.txt|'
                                                               r'joint\.json|joint_written\.json|joint\.progress\.jsonl|json\.applied|'
                                                               r'json\.sdmpc_pending)|state_\d{6}\.json', f)))
    # ------------------------------------------------------------ DECISION_FAILED everywhere
    df = {}
    for rel, p in (('runlog', runlog_p), ('runlog.err', runlog_p + '.err'), ('launch', launch_p), ('wmi', wmi_p),
                   ('WATCHDOG_PROGRESS.txt', os.path.join(RUN, 'WATCHDOG_PROGRESS.txt')),
                   ('vissim_simulation_001.err', os.path.join(RUN, 'vissim_simulation_001.err')),
                   ('vissim_network.err', os.path.join(RUN, 'vissim_network.err')),
                   ('network/sdmpc31_<run>.err', os.path.join(RUN, 'network', 'sdmpc31_%s.err' % NAME)),
                   ('network/sdmpc31_<run>_001.err', os.path.join(RUN, 'network', 'sdmpc31_%s_001.err' % NAME)),
                   ('network/VISSIG_Controller.dll.err', os.path.join(RUN, 'network', 'VISSIG_Controller.dll.err'))):
        df[rel] = rd(p).count('DECISION_FAILED') if os.path.isfile(p) else 'absent'
    cap_df = {}
    for f in sorted(names):
        if f.endswith('.stdout.txt') or f.endswith('.stderr.txt'):
            with open(os.path.join(DEC, f), 'rb') as h:
                n = h.read().count(b'DECISION_FAILED')
            if n:
                cap_df[f] = n
    res['decision_failed_counts_logs'] = df
    res['decision_failed_counts_captures'] = cap_df
    # ------------------------------------------------------------ provenance
    prov = json.loads(rd(os.path.join(RUN, 'run_provenance_%s.json' % NAME)))
    pre_prov_p = os.path.join(RUN, 'preflight', 'run_provenance_%s.json' % NAME)
    plan = json.loads(rd(os.path.join(RUN, 'launch_plan.json')))
    inpx = os.path.join(RUN, 'network', 'sdmpc31_%s.inpx' % NAME)
    FRZ = P['frz']
    frz_tuning = os.path.join(FRZ, 'diagnostics', 'sdmpc_n31_20260924', 'config_n31_v2.json')
    frz_freeze_p = os.path.join(FRZ, 'FREEZE.json')
    frz_freeze = json.loads(rd(frz_freeze_p))
    env = prov.get('env') or {}
    files = prov.get('files') or {}
    cao = [x for x in (prov.get('controller_sources') or []) if isinstance(x, dict)
           and str(x.get('path', '')).replace('\\', '/').endswith('evaluation/controllers/control_area_objective.py')]
    pv = {
        'plan_freeze_head': get(plan, 'freeze', 'head'), 'plan_freeze_sha256': get(plan, 'freeze', 'sha256'),
        'frz_FREEZE_json_git_head': get(frz_freeze, 'git', 'head'), 'frz_FREEZE_json_file_sha256': sha(frz_freeze_p),
        'plan_tuning_sha256': get(plan, 'tuning', 'sha256'), 'prov_files_tuning_sha256': get(files, 'tuning', 'sha256'),
        'prov_env_tuning_sha256': env.get('RW_SIGNAL_OBSERVATION_CONFIG_SHA256'), 'frz_tuning_file_sha256': sha(frz_tuning),
        'prov_files_network_sha256': get(files, 'network', 'sha256'), 'network_copy_file_sha256': sha(inpx),
        'prov_seed': prov.get('seed'), 'plan_seed': plan.get('seed'), 'prov_controller': prov.get('controller'),
        'prov_workspace_root': prov.get('workspace_root'), 'prov_workspace_git_commit': prov.get('workspace_git_commit'),
        'prov_env_RW_DECISION_ERROR_POLICY': env.get('RW_DECISION_ERROR_POLICY'),
        'prov_env_RW_DECISION_FAIL_FAST': env.get('RW_DECISION_FAIL_FAST'),
        'plan_expected_env_policy': get(plan, 'expected_env', 'RW_DECISION_ERROR_POLICY'),
        'plan_controller': [plan.get('controller'), plan.get('warmup_controller'), plan.get('control_start_sec'),
                            plan.get('control_interval_sec'), plan.get('sim_period')],
        'plan_warnings': plan.get('warnings'),
        'prov_vbs_sha256': get(files, 'main_vbs_runner', 'sha256'), 'prov_wd_sha256': get(files, 'watchdog_wrapper', 'sha256'),
        'prov_cao_sha256': cao[0].get('sha256') if cao else None,
        'frz_vbs_sha256': sha(os.path.join(FRZ, 'scripts', 'run_real_world_stackelberg_controller.vbs')),
        'frz_wd_sha256': sha(os.path.join(FRZ, 'scripts', 'run_real_world_single_watchdog_distributed_core17legs4b.ps1')),
        'frz_cao_sha256': sha(os.path.join(FRZ, 'evaluation', 'controllers', 'control_area_objective.py')),
    }
    if os.path.isfile(os.path.join(FRZ, 'scripts', 'decision_hold.py')):
        pv['frz_decision_hold_sha256'] = sha(os.path.join(FRZ, 'scripts', 'decision_hold.py'))
    if os.path.isfile(pre_prov_p):
        pp = json.loads(rd(pre_prov_p))
        pv['preflight_prov_env_policy'] = get(pp, 'env', 'RW_DECISION_ERROR_POLICY')
        pv['preflight_prov_tuning_sha256'] = get(pp, 'files', 'tuning', 'sha256')
    res['provenance'] = pv
    HEAD, TUN, FSHA = P['head'], P['tuning'], P['freeze']
    pc = {
        'PROV1_reading_A': len(res['freeze_verified']) == 1 and ('head=' + HEAD) in res['freeze_verified'][0]
        and pv['plan_freeze_head'] == HEAD and pv['frz_FREEZE_json_git_head'] == HEAD,
        'PROV1_reading_B_run_provenance_workspace_git_commit_eq_head (report only, amendment 34 sec.7.1)': pv['prov_workspace_git_commit'] == HEAD,
        'PROV2': pv['plan_tuning_sha256'] == TUN and pv['prov_files_tuning_sha256'] == TUN and pv['prov_env_tuning_sha256'] == TUN
        and pv['frz_tuning_file_sha256'] == TUN,
        'PROV3': pv['prov_files_network_sha256'] == NET_SHA and pv['network_copy_file_sha256'] == NET_SHA
        and any(('sha256=' + NET_SHA) in l and 'sig=42' in l for l in res['netcopy'])
        and any(('sha256=' + NET_SHA) in l for l in res['network_ok'])
        and any('network_sha=3de889f0' in l and 'controller=wu-link' in l and ('seed=%s' % seed) in l and 'sim_period=9000' in l
                for l in res['plan_detail']),
        'FREEZE': (FSHA is not None and pv['frz_FREEZE_json_file_sha256'] == FSHA and pv['plan_freeze_sha256'] == FSHA
                   and bool(res['freeze_verified']) and all(('sha256=' + FSHA) in l for l in res['freeze_verified'])
                   and bool(res['provenance_ok_lines']) and all(('freeze=' + FSHA) in l for l in res['provenance_ok_lines'])),
        'ENV': pv['prov_env_RW_DECISION_ERROR_POLICY'] == POLICY and pv['prov_env_RW_DECISION_FAIL_FAST'] == '1'
        and pv['plan_expected_env_policy'] == POLICY,
        'RUNLOG_policy_line_1': res['runlog_policy_lines'] == ['DECISION_ERROR_POLICY=' + POLICY],
        'RUNLOG_held_summary_1': len(res['runlog_held_summary_lines']) == 1,
        'SEED': pv['prov_seed'] == int(seed) and pv['plan_seed'] == int(seed),
        'plan_warnings_empty (report)': pv['plan_warnings'] == [],
        'controller_wu_link (report)': pv['plan_controller'] == ['wu-link', 'no-control', 900, 150, 9000] and pv['prov_controller'] == 'wu-link',
    }
    res['prov_checks'] = pc
    # ------------------------------------------------------------ per decision
    per = {}
    all_T = sorted(set(json_T) | {int(f[7:13]) for f in names if re.fullmatch(r'action_\d{6}\..*', f)})
    s6_missing = []
    for T in all_T:
        s = 'action_%06d' % T
        row = {'T': T}
        for suf in ('.json', '.csv', '.decision_budget.json', '.stdout.txt', '.stderr.txt', '.error.txt', '.json.applied',
                    '.json.sdmpc_pending', '.joint.json', '.joint_written.json', '.joint.progress.jsonl', '.hold.json',
                    '.hold.stdout.txt', '.hold.stderr.txt', '.hold_error.txt'):
            row['has' + suf] = (s + suf) in names
        if not (row['has.stdout.txt'] and row['has.stderr.txt']):
            s6_missing.append(T)
        bp = os.path.join(DEC, s + '.decision_budget.json')
        if os.path.isfile(bp):
            b = json.loads(rd(bp))
            row['budget'] = {k: b.get(k) for k in ('unlimited_time', 'expired_stage', 'output_completed', 'output_error')}
            row['budget_has_expired_key'] = 'expired_stage' in b
        per[T] = row
    adapter_raw = {}
    for T in json_T:
        p = os.path.join(DEC, 'action_%06d.csv' % T)
        rows = rcsv(p)
        hdr, raw = rcsv_raw(p)
        adapter_raw[T] = raw
        per[T]['csv_header_ok'] = hdr is not None and len(hdr) == 15 and hdr[0] == 'kind' and hdr[-1] == 'metadata'
        per[T]['csv_kinds'] = dict(Counter(r['kind'] for r in rows))
        per[T]['csv_vsl'] = [(r['id'], int(r['dsd_no']), float(r['speed_kph'])) for r in rows if r['kind'] == 'vsl']
        per[T]['csv_meter_RM_C10490_green'] = [r['green_sec'] for r in rows if r['kind'] == 'ramp_meter' and r['id'] == 'RM_C10490']
        per[T]['csv_meta_not_ok'] = sum(1 for r in rows if not (r.get('metadata') or '').startswith('ok'))
        per[T]['csv_sha256'] = sha(p)
    vsl_by_T, status_hold_T, hold_key_T, json_sha = {}, [], [], {}
    k92 = {}
    pin_prev = {}
    for T in json_T:
        p = os.path.join(DEC, 'action_%06d.json' % T)
        with open(p, 'rb') as f:
            raw = f.read()
        json_sha[T] = sha_bytes(raw)
        d = json.loads(raw)
        del raw
        md = d.get('metadata') if isinstance(d.get('metadata'), dict) else {}
        jl = md.get('joint_leader_selection') if isinstance(md.get('joint_leader_selection'), dict) else {}
        ic = md.get('stopline_approach_install_check')
        r = per[T]
        r['controller'] = md.get('controller')
        r['controller_status'] = md.get('controller_status')
        r['sim_sec_md'] = md.get('sim_sec')
        r['has_hold_key'] = 'hold_previous_on_exception' in md
        if md.get('controller_status') == POLICY:
            status_hold_T.append(T)
        if r['has_hold_key']:
            hold_key_T.append(T)
        r['sdmpc_active'] = md.get('sdmpc_active')
        r['install_check_present'] = ic is not None
        r['install_check_passed'] = ic.get('passed') if isinstance(ic, dict) else None
        r['phys7_present'] = [k for k in PHYS7 if k in d]
        r['vsl'] = {k: float(v) for k, v in (d.get('vsl') or {}).items()}
        vsl_by_T[T] = r['vsl']
        if jl:
            vc = [x for x in (jl.get('coordinates') or []) if isinstance(x, dict) and x.get('kind') == 'vsl']
            r['vsl_coords_block0'] = [(x.get('key'), x.get('allowed')) for x in vc if x.get('block') == 0]
        vci = get(md, 'n31_binding', 'vsl_cohort_initialization')
        pin_prev[T] = ({'source_base': os.path.basename(str(vci.get('source', '')).replace('\\', '/')), 'sha256': vci.get('sha256')}
                       if isinstance(vci, dict) else None)
        # K9-2 keys (presence / names / fixed-value repr only; values are never written)
        w, hb = md.get('k92_w'), md.get('k92_hb')
        fk = sorted(k for k in md if FLOOR_RE.match(k))
        pdv = md.get('head_observation_prior_discarded')
        k92[T] = {'k92_w_dict': isinstance(w, dict), 'k92_hb_dict': isinstance(hb, dict), 'floor_keys': fk,
                  'k92_w_after_repr_ok': isinstance(w, dict) and isinstance(w.get('after'), float) and repr(w.get('after')) == W_AFTER_REPR,
                  'prior_discarded_eq_1': isinstance(pdv, (int, float)) and not isinstance(pdv, bool) and float(pdv) == 1.0,
                  'prior_discarded_present': 'head_observation_prior_discarded' in md}
        del d, md, jl
    print('json parsed', len(json_T), 'in %.0fs' % (time.time() - t0), flush=True)
    # ------------------------------------------------------------ hold T sets (DEC1)
    hold_sets = {'receipts': receipt_T, 'runlog_DECISION_HOLD_ATTEMPT': hold_attempt_T,
                 'runlog_DECISION_HELD_ON_EXCEPTION': held_T, 'error_txt': error_T,
                 'json_controller_status_hold': sorted(status_hold_T)}
    res['hold_T_sets'] = hold_sets
    res['hold_metadata_key_T'] = hold_key_T
    HOLD = set(receipt_T) | set(hold_attempt_T) | set(held_T) | set(error_T) | set(status_hold_T)
    try:
        n_held_summary = int((kv.get('DECISIONS_HELD_ON_EXCEPTION') or ['-1'])[-1])
    except ValueError:
        n_held_summary = -1
    res['n_hold'] = len(HOLD)
    res['hold_T'] = sorted(HOLD)
    applied_missing = [T for T in json_T if T >= 900 and T not in HOLD and not (per[T]['has.json.applied'] and per[T]['has.json.sdmpc_pending'])]
    res['s6_missing_T'] = s6_missing
    res['sdmpc_applied_or_pending_missing_T'] = applied_missing
    # ------------------------------------------------------------ signal readback
    sr = rcsv(os.path.join(DEC, 'signal_readback.csv'))
    res['signal_readback'] = {'rows': len(sr), 'sg_no_ge_9': sum(1 for r in sr if int(r['sg_no']) >= 9),
                              'not_ok': sum(1 for r in sr if r['ok'] != '1'),
                              'mismatch_req_rb': sum(1 for r in sr if r['requested_state'] != r['readback_state']),
                              'stages': dict(Counter(r['stage'] for r in sr)), 'max_sg_no': max(int(r['sg_no']) for r in sr),
                              'times': len({r['sim_sec'] for r in sr}), 'last_sim_sec': max(int(float(r['sim_sec'])) for r in sr)}
    sr_T = defaultdict(lambda: [0, 0])
    for r in sr:
        t_ = int(float(r['sim_sec']))
        sr_T[t_][0] += 1
        sr_T[t_][1] += (r['ok'] != '1')
    # ------------------------------------------------------------ runner action log
    al_path = os.path.join(RUN, 'action_%s.csv' % NAME)
    al = rcsv(al_path)
    al_hdr, al_raw = rcsv_raw(al_path)
    al_by_T = defaultdict(list)
    for rr_ in al_raw:
        al_by_T[int(float(rr_[0]))].append(rr_[1:-1])
    res['action_log'] = {'rows': len(al), 'header_ok': al_hdr is not None and al_hdr[0] == 'sim_sec' and al_hdr[-1] == 'readback',
                         'times': len({int(float(r['sim_sec'])) for r in al})}
    al_vsl = {}
    m_green_rm = Counter()
    for r in al:
        T = int(float(r['sim_sec']))
        if r['kind'] == 'vsl':
            al_vsl.setdefault((T, int(r['dsd_no'])), []).append((float(r['speed_kph']), r['readback']))
        elif r['kind'] == 'ramp_meter' and r['id'] == 'RM_C10490':
            m_green_rm[r['green_sec']] += 1
    res['meter_K3'] = {'RM_C10490_green_3_rows': sum(n for g, n in m_green_rm.items() if g != '' and float(g) == 3.0),
                       'RM_C10490_rows': sum(m_green_rm.values()),
                       'adapter_csv_RM_C10490_green_3_decisions': sum(1 for T in json_T for g in per[T]['csv_meter_RM_C10490_green']
                                                                     if g not in (None, '') and float(g) == 3.0)}
    # ------------------------------------------------------------ VSL box (VSL1, VSL2)
    box = {'pairs': 0, 'violations': [], 'max_abs_step': 0.0, 'keys_n': set()}

    def resolved(v):
        o = {}
        for road in ('FW_E', 'FW_W'):
            o[road] = v.get(road)
            for i in range(21):
                k = '%s__seg%d' % (road, i)
                o[k] = v.get(k, v.get(road))
        return o
    prevT = None
    hold_vsl_delta_nonzero = []
    for T in json_T:
        box['keys_n'].add(len(vsl_by_T[T]))
        v = resolved(vsl_by_T[T])
        if prevT is not None:
            pv_ = resolved(vsl_by_T[prevT])
            box['pairs'] += 1
            for k in sorted(set(v) | set(pv_)):
                if k in v and k in pv_ and v[k] is not None and pv_[k] is not None:
                    dd = abs(v[k] - pv_[k])
                    box['max_abs_step'] = max(box['max_abs_step'], dd)
                    if dd > MAX_VSL_STEP + 1e-9:
                        box['violations'].append((prevT, T, k))
                    if T in HOLD and dd != 0.0:
                        hold_vsl_delta_nonzero.append((T, k))
                else:
                    box['violations'].append((prevT, T, k, 'key missing'))
        prevT = T
    box['keys_n'] = sorted(box['keys_n'])
    box['hold_T_vsl_delta_nonzero'] = hold_vsl_delta_nonzero
    b0, b0_bad = Counter(), []
    for T in json_T:
        if T >= 900 and T not in HOLD:
            for key, allowed in per[T].get('vsl_coords_block0') or []:
                b0[tuple(allowed or [])] += 1
                if [float(a) for a in (allowed or [])] != [80.0, 90.0, 100.0, 110.0]:
                    b0_bad.append((T, key))
    box['block0_allowed_sets'] = {str(k): n for k, n in b0.items()}
    box['block0_bad'] = b0_bad
    box['block0_coords_per_decision'] = sorted({len(per[T].get('vsl_coords_block0') or []) for T in json_T if T >= 900 and T not in HOLD})
    box['n_violations'] = len(box['violations'])
    box['violations'] = box['violations'][:20]
    res['vsl_box'] = box
    # ------------------------------------------------------------ U9-a chain
    vr = rcsv(os.path.join(DEC, 'vsl_readback.csv'))
    vr_by = defaultdict(list)
    for r in vr:
        vr_by[(int(float(r['sim_sec'])), int(r['dsd_no']))].append(r)
    u9 = {'rows_vsl_readback': len(vr), 'expected_rows': len(json_T) * 66 * 4, 'mismatch': [], 'n_rows_checked': 0,
          'below110_rows': 0, 'below110_T_count': 0, 'csv_speed_forbidden_rows': 0,
          'vr_not_ok': sum(1 for r in vr if r['ok'] != '1'), 'vr_stages': dict(Counter(r['stage'] for r in vr)),
          'vr_classes': sorted({r['veh_class_no'] for r in vr}), 'seg_fallback_rows': 0}
    b110_T = set()
    b110 = Counter()
    for T in json_T:
        v = vsl_by_T[T]
        rows = per[T]['csv_vsl']
        if len(rows) != 66:
            u9['mismatch'].append((T, 'csv vsl rows', len(rows)))
        for vid, dsd, spd in rows:
            u9['n_rows_checked'] += 1
            m = re.fullmatch(r'RW_(FW_[EW])_S(\d+)', vid)
            if not m:
                u9['mismatch'].append((T, dsd, 'bad id'))
                continue
            road, k = m.group(1), int(m.group(2))
            cmd = v.get('%s__seg%d' % (road, k))
            if cmd is None:
                cmd = v.get(road)
                u9['seg_fallback_rows'] += 1
            if cmd is None:
                u9['mismatch'].append((T, dsd, 'seg and road key missing'))
                continue
            if cmd not in CMD_SET:
                u9['mismatch'].append((T, dsd, 'cmd not in set'))
                continue
            mm = M[cmd]
            if spd in (80.0, 90.0, 100.0, 120.0):
                u9['csv_speed_forbidden_rows'] += 1
            if spd != mm:
                u9['mismatch'].append((T, dsd, 'csv speed != M(c)'))
            lg = al_vsl.get((T, dsd))
            if not lg or len(lg) != 1:
                u9['mismatch'].append((T, dsd, 'runner log rows', len(lg or [])))
            else:
                ls, rb = lg[0]
                parts = rb.split('|')
                if ls != spd or len(parts) != 2 or any(float(x) != mm for x in parts):
                    u9['mismatch'].append((T, dsd, 'runner log'))
            rr = vr_by.get((T, dsd), [])
            if sorted(x['veh_class_no'] for x in rr) != ['10', '20', '30', '70']:
                u9['mismatch'].append((T, dsd, 'vsl_readback classes'))
            for x in rr:
                if (float(x['requested_kph']) != mm or float(x['readback_distribution_no']) != mm or x['ok'] != '1'
                        or x['stage'] != 'immediate'):
                    u9['mismatch'].append((T, dsd, 'vsl_readback row'))
            if cmd < 110.0:
                b110[(road, cmd, mm)] += 1
                b110_T.add(T)
    u9['below110_rows'] = sum(b110.values())
    u9['below110_by_road_cmd'] = {'%s %s->%s' % k: n for k, n in sorted(b110.items())}
    u9['below110_T'] = sorted(b110_T)
    u9['below110_T_count'] = len(b110_T)
    u9['vsl_readback_extra_keys'] = len(set(vr_by) - {(T, dsd) for T in json_T for _, dsd, _ in per[T]['csv_vsl']})
    u9['n_mismatch'] = len(u9['mismatch'])
    u9['mismatch'] = u9['mismatch'][:30]
    u9['error_lines'] = [l[:300] for l in lines if 'ERROR=VSL_COM_WRITE_READBACK' in l or 'ERROR=ACTION_CSV_CONTRACT' in l]
    u9['hold_T_rows_present'] = all(any(k[0] == T for k in vr_by) for T in HOLD)
    res['u9a'] = u9
    # ------------------------------------------------------------ state csv
    st = rcsv(os.path.join(RUN, 'state_%s.csv' % NAME))
    res['state_csv'] = {'rows': len(st), 'status': dict(Counter(r.get('controller_status') for r in st))}
    # ------------------------------------------------------------ comparators run on every decision (report-only self-test of the H-A4 / H-A6 readings)
    cmp6 = {T: (al_by_T.get(T, []) == adapter_raw[T]) for T in json_T}
    cmp4 = {}
    for T in json_T:
        nxt = T + 150 if T > 1 else 150
        if nxt in pin_prev and pin_prev[nxt] is not None:
            cmp4[T] = (pin_prev[nxt]['source_base'] == 'action_%06d.json' % T and pin_prev[nxt]['sha256'] == json_sha[T])
        elif nxt in json_T:
            cmp4[T] = None
    res['comparator_selftest'] = {
        'HA6_runner_log_eq_adapter_csv_nonhold': {'n': sum(1 for T in json_T if T not in HOLD),
                                                  'equal': sum(1 for T in json_T if T not in HOLD and cmp6[T]),
                                                  'not_equal_T': [T for T in json_T if T not in HOLD and not cmp6[T]]},
        'HA4_next_pin_eq_prev_json_nonhold': {'n_with_pin': sum(1 for T, v in cmp4.items() if v is not None and T not in HOLD),
                                              'equal': sum(1 for T, v in cmp4.items() if v is True and T not in HOLD),
                                              'not_equal_T': [T for T, v in cmp4.items() if v is False and T not in HOLD],
                                              'next_without_pin_T': [T for T, v in cmp4.items() if v is None]},
    }
    # ------------------------------------------------------------ J1-A items
    sd = [T for T in json_T if T >= 900]
    sd_nh = [T for T in sd if T not in HOLD]
    wu = [T for T in json_T if T < 900]
    last = lambda k: (c.get(k) or [None])[-1]
    rl_df_outside_hold = sum(l.count('DECISION_FAILED') for i, l in enumerate(lines)
                             if not any(cd_idx.get(T) == i for T in HOLD))
    items = {}
    if POL:
        items['S1'] = last('DECISIONS_FAILED') == '0' and len(c.get('DECISIONS_FAILED') or []) == 1 and len(res['runlog_held_summary_lines']) == 1
    else:
        items['S1'] = last('DECISIONS_FAILED') == '0'
    items['S2'] = not res['runlog_error_lines']
    items['S3'] = len(res['launch_exit']) == 1 and res['launch_exit'][0].strip().endswith('code=0') and \
        len(res['wmi_exit']) == 1 and res['wmi_exit'][0].strip().endswith('code=0')
    items['S4'] = last('STAGE') == 'SIM_DONE' and last('SIM_SEC') == '9000'
    items['S5'] = all(last(k) == '0' for k in ('ACTION_FORMAT_FAILURES', 'COM_FAILURES', 'SIGNAL_FAILURES',
                                               'OBSERVATION_FAILURES', 'SIGNAL_NAME_RULE_FALLBACKS'))
    if POL:
        items['S6'] = set(error_T) == set(receipt_T) and len(err_files) == len(error_T) and not hold_error_files
        items['K8'] = all(v == 0 for k, v in df.items() if v != 'absent' and k != 'runlog') and rl_df_outside_hold == 0 and \
            all(int(f[7:13]) in HOLD and re.fullmatch(r'action_\d{6}\.stderr\.txt', f) is not None and n == 1 for f, n in cap_df.items()) and \
            all(cap_df.get('action_%06d.stderr.txt' % T) == 1 for T in HOLD) and \
            all(cd[T]['decision_failed_in_line'] in (0, 1) for T in HOLD if T in cd)
    else:
        items['S6'] = not err_files
        items['K8'] = all(v == 0 for v in df.values() if v != 'absent') and not cap_df
    items['SIG1'] = last('SIGNAL_MIDBLOCK_COM_SKIPS') is not None and int(last('SIGNAL_MIDBLOCK_COM_SKIPS')) > 0
    items['SIG2'] = res['signal_readback']['sg_no_ge_9'] == 0
    if POL:
        try:
            ok_plus = int(last('DECISIONS_OK')) + n_held_summary
        except (TypeError, ValueError):
            ok_plus = None
        items['DEC1'] = len(json_T) == 61 and len(wu) == 6 and len(sd) == 55 and not res['missing_expected_T'] and not res['unexpected_T'] \
            and ok_plus == 61 and all(sorted(s) == sorted(HOLD) for s in hold_sets.values()) and n_held_summary == len(HOLD)
    else:
        items['DEC1'] = len(json_T) == 61 and len(wu) == 6 and len(sd) == 55 and not res['missing_expected_T'] and last('DECISIONS_OK') == '61'
    items['DEC2'] = res['warmup_controller_T'] == wu and res['warmup_controller_names'] == ['no-control']
    if POL:
        items['DEC3'] = all(per[T].get('sdmpc_active') is True for T in sd_nh) and bool(sd_nh) and not applied_missing
    else:
        items['DEC3'] = all(per[T].get('sdmpc_active') is True for T in sd) and bool(sd)
    budget_T = [T for T in json_T if T not in HOLD] if POL else json_T
    items['DEC4'] = all(per[T].get('budget', {}).get('unlimited_time') is True and per[T].get('budget_has_expired_key') is True
                        and per[T].get('budget', {}).get('expired_stage') is None
                        and per[T].get('budget', {}).get('output_completed') is True for T in budget_T)
    if POL:
        items['DEC5'] = all(cd.get(T, {}).get('exit') == 0 for T in json_T if T not in HOLD) and \
            all(cd.get(T, {}).get('exit') == 1 and 'HOLD_OK' in held_lines.get(T, '') for T in HOLD) and len(cd) == 61
    else:
        items['DEC5'] = all(cd.get(T, {}).get('exit') == 0 for T in json_T) and len(cd) == 61
    items['PROV1'] = pc['PROV1_reading_A']
    items['PROV2'] = pc['PROV2']
    items['PROV3'] = pc['PROV3']
    items['PROV_freeze'] = pc['FREEZE'] if POL else 'n/a'
    items['PROV_env'] = pc['ENV'] if POL else 'n/a'
    items['PROV_runlog_policy_line'] = pc['RUNLOG_policy_line_1'] if POL else 'n/a'
    items['PROV_seed'] = pc['SEED'] if POL else 'n/a'
    items['VSL1'] = box['n_violations'] == 0 and not hold_vsl_delta_nonzero
    items['VSL2'] = not b0_bad and bool(b0)
    items['MTR'] = res['meter_K3']['RM_C10490_green_3_rows'] == 0 and res['meter_K3']['adapter_csv_RM_C10490_green_3_decisions'] == 0
    k8a_T = sd_nh if POL else sd
    items['K8a'] = all(per[T].get('install_check_present') and per[T].get('install_check_passed') is True for T in k8a_T) and bool(k8a_T)
    items['K8b'] = not s6_missing and all(per[T]['has.stdout.txt'] and per[T]['has.stderr.txt'] for T in json_T) and \
        all(per[T]['has.hold.stdout.txt'] and per[T]['has.hold.stderr.txt'] for T in HOLD)
    items['U9a'] = u9['n_mismatch'] == 0 and u9['vr_not_ok'] == 0 and not u9['error_lines'] \
        and u9['rows_vsl_readback'] == u9['expected_rows'] and u9['csv_speed_forbidden_rows'] == 0 and u9['hold_T_rows_present']
    res['items'] = items
    res['n_items_counted'] = sum(1 for v in items.values() if v != 'n/a')
    res['failed_items'] = [k for k, v in items.items() if v is not True and v != 'n/a']
    # ------------------------------------------------------------ hold audit H-A (per hold T)
    ha = {'n_hold_T': len(HOLD), 'per_T': {}, 'violations': [], 'incomplete': [], 'question_points_HA9': []}
    obs_dir = DEC
    sigs = {}
    for T in sorted(HOLD):
        a = receipt_level_audit(DEC, T, DEC, obs_dir)
        # H-A4: no applied / pending at T; next decision pins the held JSON; next did not fail on a P-5 pair
        t6 = '%06d' % T
        nxt = T + 150
        c4 = {'no_applied_pending': ('action_%s.json.applied' % t6) not in names and ('action_%s.json.sdmpc_pending' % t6) not in names}
        hsha = json_sha.get(T)
        if T == 9000:
            c4['next_pin'] = True
        elif nxt in HOLD:
            rpn = os.path.join(DEC, 'action_%06d.hold.json' % nxt)
            c4['next_pin'] = os.path.isfile(rpn) and get(json.loads(rd(rpn)), 'source', 'action_json', 'sha256') == hsha
        elif nxt in pin_prev and pin_prev[nxt] is not None:
            c4['next_pin'] = pin_prev[nxt]['source_base'] == 'action_%s.json' % t6 and pin_prev[nxt]['sha256'] == hsha
        else:
            c4['next_pin'] = INC
        enp = os.path.join(DEC, 'action_%06d.error.txt' % nxt)
        if os.path.isfile(enp):
            j = judge_error_text(lines_replace(enp), None)
            c4['next_not_contract_failure'] = not j['contract_pair_hits'] and not j['contract_message_hits']
        else:
            c4['next_not_contract_failure'] = True
        a['HA4_detail'] = c4
        a['HA4'] = INC if INC in c4.values() else all(c4.values())
        # H-A6: runner log rows at T == held CSV rows; readbacks at T present with ok == 1
        hc = os.path.join(DEC, 'action_%s.csv' % t6)
        if os.path.isfile(hc):
            _, hrows = rcsv_raw(hc)
            c6 = {'runner_log_eq_held_csv': al_by_T.get(T, []) == hrows and len(hrows) > 0,
                  'vsl_readback_rows_ok': any(k[0] == T for k in vr_by) and all(x['ok'] == '1' for k, xs in vr_by.items() if k[0] == T for x in xs),
                  'signal_readback_rows_ok': sr_T.get(T, [0, 0])[0] > 0 and sr_T.get(T, [0, 0])[1] == 0}
            a['HA6_detail'] = c6
            a['HA6'] = all(c6.values())
        else:
            a['HA6'] = INC
        # H-A8: runlog order CONTROLLER_DECISION exit=1 -> DECISION_HOLD_ATTEMPT -> DECISION_HELD_ON_EXCEPTION, no ERROR= at T
        i_cd = cd_idx.get(T)
        i_at = next((i for i, l in enumerate(lines) if l.startswith('DECISION_HOLD_ATTEMPT') and re.search(r'sim_sec=%d\b' % T, l)), None)
        i_hd = next((i for i, l in enumerate(lines) if l.startswith('DECISION_HELD_ON_EXCEPTION ') and re.search(r'sim_sec=%d\b' % T, l)), None)
        a['HA8'] = (i_cd is not None and i_at is not None and i_hd is not None and i_cd < i_at < i_hd and cd[T]['exit'] == 1
                    and not any(l.startswith('ERROR=') and re.search(r'sim_sec=%d\b' % T, l) for l in lines))
        a['P3_T_ge_1050'] = T >= 1050
        for k in ('HA1', 'HA2', 'HA3', 'HA4', 'HA5', 'HA6', 'HA7', 'HA8', 'P3_T_ge_1050'):
            if a.get(k) == INC:
                ha['incomplete'].append((T, k))
            elif a.get(k) is not True:
                ha['violations'].append((T, k))
        sigs[T] = a.get('signature')
        ha['per_T'][str(T)] = a
    for T in sorted(HOLD):
        if T + 150 in HOLD and sigs.get(T) is not None and sigs.get(T + 150) is not None and sigs[T] != sigs[T + 150]:
            ha['question_points_HA9'].append([T, T + 150])
    if not HOLD:
        ha['note'] = 'vacuous (no hold T)'
        ha['absence_evidence'] = {'receipts': len(receipt_T), 'hold_capture_files': len(hold_cap), 'hold_error_files': len(hold_error_files),
                                  'failed_decision_files': len(failed_partials), 'error_txt': len(err_files),
                                  'runlog_DECISION_HOLD_ATTEMPT': len(hold_attempt_T), 'runlog_DECISION_HELD_ON_EXCEPTION': len(held_T),
                                  'runlog_DECISION_HOLD_FAILED': len(res['runlog_hold_failed_lines']),
                                  'json_controller_status_hold': len(status_hold_T), 'json_metadata_hold_key': len(hold_key_T),
                                  'summary_DECISIONS_HELD_ON_EXCEPTION': n_held_summary,
                                  'controller_status_values': dict(Counter(str(per[T].get('controller_status')) for T in json_T)),
                                  'state_csv_status': res['state_csv']['status']}
    res['hold_audit'] = ha
    # ------------------------------------------------------------ report-only facts
    rep = {}
    walls = sorted(cd[T]['wall_sec'] for T in sd if T in cd)
    if walls:
        n = len(walls)
        med = walls[n // 2] if n % 2 else (walls[n // 2 - 1] + walls[n // 2]) / 2.0
        rep['sdmpc_wall_sec'] = {'n': n, 'min': walls[0], 'median': med, 'median_upper_index': walls[n // 2], 'max': walls[-1],
                                 'sum': round(sum(walls), 1), 'mean': round(sum(walls) / n, 1),
                                 'gt_900_T': [T for T in sd if cd[T]['wall_sec'] > 900], 'gt_2400_T': [T for T in sd if cd[T]['wall_sec'] > 2400]}
    ww = sorted(cd[T]['wall_sec'] for T in wu if T in cd)
    rep['warmup_wall_sec'] = {'min': ww[0], 'max': ww[-1], 'sum': round(sum(ww), 1)} if ww else None
    m = re.search(r'WATCHDOG_EXIT code=(-?\d+) wall_sec=(\d+)', ' '.join(res['watchdog_exit']))
    rep['watchdog_wall_sec'] = int(m.group(2)) if m else None
    if P['k92']:
        nh = [T for T in json_T if T not in HOLD]
        sdn = [T for T in sd if T not in HOLD]
        names_all = sorted({tuple(k92[T]['floor_keys']) for T in nh})
        rep['k92'] = {'n_nonhold_decisions': len(nh), 'n_nonhold_sdmpc': len(sdn),
                      'k92_w_present_all': sum(1 for T in nh if k92[T]['k92_w_dict']),
                      'k92_hb_present_all': sum(1 for T in nh if k92[T]['k92_hb_dict']),
                      'k92_w_present_sdmpc': sum(1 for T in sdn if k92[T]['k92_w_dict']),
                      'k92_hb_present_sdmpc': sum(1 for T in sdn if k92[T]['k92_hb_dict']),
                      'k92_w_after_repr_5209_8': sum(1 for T in nh if k92[T]['k92_w_after_repr_ok']),
                      'one_floor_key': sum(1 for T in nh if len(k92[T]['floor_keys']) == 1),
                      'floor_key_name_sets': [list(x) for x in names_all],
                      'missing_k92_T': [T for T in nh if not (k92[T]['k92_w_dict'] and k92[T]['k92_hb_dict'] and len(k92[T]['floor_keys']) == 1)]}
    else:
        rep['k92'] = {'k92_w_present_all': sum(1 for T in json_T if k92[T]['k92_w_dict']),
                      'k92_hb_present_all': sum(1 for T in json_T if k92[T]['k92_hb_dict']),
                      'floor_keys_any': sum(1 for T in json_T if k92[T]['floor_keys'])}
    rep['prior_discarded'] = {'T150_eq_1': k92.get(150, {}).get('prior_discarded_eq_1'),
                              'T_list_eq_1': [T for T in json_T if k92[T]['prior_discarded_eq_1']],
                              'n_present': sum(1 for T in json_T if k92[T]['prior_discarded_present'])}
    # run folder unchanged after EXIT (+60 s)
    m = re.match(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', res['launch_exit'][0]) if res['launch_exit'] else None
    if m:
        t_exit = time.mktime(time.strptime(m.group(1), '%Y-%m-%d %H:%M:%S'))
        later, n_files, last_m = [], 0, 0.0
        for dp, dn, fn in os.walk(RUN):
            for f in fn:
                pth = os.path.join(dp, f)
                mt = os.path.getmtime(pth)
                n_files += 1
                last_m = max(last_m, mt)
                if mt > t_exit + 60:
                    later.append(os.path.relpath(pth, RUN))
        rep['after_exit'] = {'exit_line_time': m.group(1), 'files': n_files, 'modified_after_exit_plus_60s': later[:20],
                             'n_modified_after_exit_plus_60s': len(later),
                             'last_mtime': datetime.datetime.fromtimestamp(last_m).strftime('%Y-%m-%d %H:%M:%S')}
    else:
        rep['after_exit'] = INC
    # .err copies (size, mtime, sha) -- not the content
    errs = {}
    for rel in ('vissim_simulation_001.err', 'network/sdmpc31_%s_001.err' % NAME, 'vissim_network.err', 'network/sdmpc31_%s.err' % NAME):
        pth = os.path.join(RUN, *rel.split('/'))
        errs[rel.replace(NAME, '<run>')] = ({'bytes': os.path.getsize(pth), 'sha256': sha(pth),
                                             'mtime': datetime.datetime.fromtimestamp(os.path.getmtime(pth)).strftime('%Y-%m-%d %H:%M:%S')}
                                            if os.path.isfile(pth) else 'absent')
    rep['err_files'] = errs
    rep['runlog_err_bytes'] = os.path.getsize(runlog_p + '.err') if os.path.isfile(runlog_p + '.err') else 'absent'
    rep['s6_stderr_nonempty'] = sum(1 for T in json_T if os.path.getsize(os.path.join(DEC, 'action_%06d.stderr.txt' % T)) > 0)
    fzp = os.path.join(RUN, 'vissim_eval', 'sdmpc31_%s_001.fzp' % NAME)
    rep['fzp'] = {'bytes': os.path.getsize(fzp), 'last_frame_sec': last_frame_time(fzp)} if os.path.isfile(fzp) else 'absent'
    rep['csv_meta_not_ok_total'] = sum(per[T]['csv_meta_not_ok'] for T in json_T)
    rep['sim_sec_md_matches_T'] = all(per[T].get('sim_sec_md') in (T, float(T)) for T in json_T)
    rep['csv_header_ok_all'] = all(per[T]['csv_header_ok'] for T in json_T)
    res['report'] = rep
    res['run_valid_by_tool'] = (not res['failed_items'] and not ha['violations'] and not ha['incomplete'])
    res['per_decision'] = {str(T): {k: v for k, v in per[T].items() if k not in ('csv_vsl', 'vsl', 'csv_meter_RM_C10490_green')}
                           for T in all_T}
    res['elapsed_sec'] = round(time.time() - t0, 1)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(res, f, indent=1, ensure_ascii=False, default=str)
    print('CHECK', profile, seed, 'failed_items', res['failed_items'], 'n_items', res['n_items_counted'], 'n_hold', len(HOLD),
          'HA_viol', ha['violations'], 'HA_inc', ha['incomplete'], 'HA9', ha['question_points_HA9'], 'valid_by_tool', res['run_valid_by_tool'])
    for k, v in items.items():
        print('  %-26s %s' % (k, v))
    print('elapsed', res['elapsed_sec'])


def last_frame_time(p):
    with open(p, 'rb') as f:
        f.seek(0, 2)
        n = f.tell()
        f.seek(max(0, n - 65536))
        tail = f.read().splitlines()
    for raw in reversed(tail):
        if raw[:1].isdigit():
            try:
                return float(raw.split(b';', 1)[0])
            except ValueError:
                continue
    return None


# ===================================================================================================== J1-V pairing (prefix)
class _Prefix(object):
    def __init__(self, f, skip, cut, stats):
        self._f, self._skip, self._cut, self._s = f, skip, cut, stats

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self._f.close()

    def __iter__(self):
        for raw in self._f:
            if raw[:1].isdigit():
                if self._skip and raw.startswith(self._skip):
                    self._s['skipped'] += 1
                    continue
                t = float(raw.split(b';', 1)[0])
                if t > self._cut:
                    self._s['stopped_at'] = t
                    return
                self._s['rows'] += 1
                self._s['last_t'] = t
            yield raw


class _IoShim(object):
    def __init__(self, target, skip, cut):
        self.target, self.skip, self.cut = os.path.normcase(os.path.abspath(target)), skip, cut
        self.stats = {'skipped': 0, 'rows': 0, 'last_t': None, 'stopped_at': None}

    def open(self, path, mode='r', *a, **kw):
        if 'b' not in mode or any(ch in mode for ch in 'wax+'):
            raise SystemExit('shim: unexpected mode %r' % mode)
        f = io.open(path, mode, *a, **kw)
        if os.path.normcase(os.path.abspath(path)) == self.target:
            return _Prefix(f, self.skip, self.cut, self.stats)
        return f


def pair(profile, seed, out_path, cut=950.0):
    t0 = time.time()
    prio = set_below_normal()
    P, NAME, RUN, DEC = profile_paths(profile, seed)
    for n, want in STAGE1_SHA.items():
        got = sha(os.path.join(STAGE1, n))
        if got != want:
            raise SystemExit('stage1 tool %s sha %s != pinned' % (n, got[:8]))
    sys.path.insert(0, STAGE1)
    import stage1_common as C
    import stage1_scan as S
    import stage1_report as R
    C.find_rule_policy = lambda run_dir: None  # no glob over sibling seed folders (sealed seeds)
    NC = NC3_FMT % seed
    nc = C.run_files(NC)
    nc['tag'] = 'nc3_s' + seed
    if not C.run_completed(nc):
        raise SystemExit('NC3 not completed')
    arm = {'run_dir': RUN, 'arm_dir': os.path.dirname(RUN), 'tag': profile + '_s' + seed,
           'run_json': {'completed': True, 'exit_code': 0, 'seed': int(seed), 'source': 'built by hand for a prefix scan'},
           'fzp': os.path.join(RUN, 'vissim_eval', 'sdmpc31_%s_001.fzp' % NAME),
           'inpx': os.path.join(RUN, 'network', 'sdmpc31_%s.inpx' % NAME),
           'err': os.path.join(RUN, 'network', 'sdmpc31_%s_001.err' % NAME), 'analysis_dir': None}
    out = {'tool': 'va_j1a.py pair', 'tool_sha256': sha(os.path.abspath(__file__)), 'profile': profile, 'seed': seed,
           'name': NAME, 'nc3': NC, 'cut_sec': cut, 't_act': 900, 'stage1_sha256': STAGE1_SHA, 'priority': hex(prio)}
    scans = {}
    real_io = S.io
    for tag, info, skip in (('nc3', nc, None), ('arm', arm, b'0.10;')):
        for k in ('fzp', 'inpx', 'err'):
            if not info.get(k) or not os.path.exists(info[k]):
                raise SystemExit('%s: %s missing' % (tag, k))
        shim = _IoShim(info['fzp'], skip, cut)
        S.io = shim
        try:
            sc, net = S.scan(info, force=True)
        finally:
            S.io = real_io
        sc['seed'] = int(seed)
        scans[tag] = sc
        out[tag] = {'fzp': info['fzp'], 'inpx_sha256': sha(info['inpx']), 'fzp_bytes': os.path.getsize(info['fzp']),
                    'fzp_last_frame_sec': last_frame_time(info['fzp']), 'shim': shim.stats, 'frames': sc['frames'],
                    'rows': sc['rows']}
    pc = R.pairing_check(int(seed), scans['nc3'], scans['arm'], 900)
    out['pairing_check'] = pc
    a, b = scans['nc3']['frame_series'], scans['arm']['frame_series']
    pre = [i for i, t in enumerate(a['t']) if t < 900.0]
    out['pre900_frames'] = len(pre)
    out['pre900_all_equal'] = all(a['all'][i] == b['all'][i] for i in pre) and a['t'][:len(pre)] == b['t'][:len(pre)]
    out['pre900_omega_equal'] = all(a['omega'][i] == b['omega'][i] for i in pre)
    ins_a, ins_b = scans['nc3']['insertions'], scans['arm']['insertions']
    out['pre900_entries_equal_inputs'] = sum(1 for k in ins_a if [e for e in ins_a[k]['entry_times'] if e < 900.0]
                                             == [e for e in ins_b.get(k, {}).get('entry_times', []) if e < 900.0])
    out['inputs'] = len(ins_a)
    out['pre900_entries_total'] = [sum(sum(1 for e in v['entry_times'] if e < 900.0) for v in ins_a.values()),
                                   sum(sum(1 for e in v['entry_times'] if e < 900.0) for v in ins_b.values())]
    out['elapsed_sec'] = round(time.time() - t0, 1)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=1, default=str)
    print('PAIR', profile, seed, json.dumps(pc), 'pre900', out['pre900_frames'], out['pre900_all_equal'], out['pre900_omega_equal'],
          out['pre900_entries_equal_inputs'], '/', out['inputs'], out['pre900_entries_total'],
          'arm_shim', out['arm']['shim'], 'elapsed', out['elapsed_sec'])


# ===================================================================================================== freeze rehash
def freeze(profile, out_path):
    set_below_normal()
    P = PROFILES[profile]
    FRZ = P['frz']
    fz = json.loads(rd(os.path.join(FRZ, 'FREEZE.json')))
    files = fz['files']
    ent = {k.replace('\\', '/'): v for k, v in files.items()} if isinstance(files, dict) else {x['path'].replace('\\', '/'): x for x in files}
    res = {'tool': 'va_j1a.py freeze', 'tool_sha256': sha(os.path.abspath(__file__)), 'profile': profile, 'frz': FRZ,
           'freeze_json_sha256': sha(os.path.join(FRZ, 'FREEZE.json')), 'expected_freeze_sha256': P['freeze'],
           'n_listed': len(ent), 'git_head': get(fz, 'git', 'head'), 'expected_head': P['head']}
    bad = []
    for rel, v in ent.items():
        p = os.path.join(FRZ, rel)
        want = v.get('sha256') if isinstance(v, dict) else v
        if not os.path.isfile(p):
            bad.append((rel, 'missing'))
        elif sha(p) != want:
            bad.append((rel, 'sha differs'))
    res['n_listed_bad'] = len(bad)
    res['listed_bad'] = bad[:50]
    extra, extra_noncache, cache_mt = Counter(), [], []
    for dp, dn, fn in os.walk(FRZ):
        for f in fn:
            rel = os.path.relpath(os.path.join(dp, f), FRZ).replace('\\', '/')
            if rel in ent or rel == 'FREEZE.json':
                continue
            parts = rel.split('/')
            if any(x in parts for x in CACHE_DIRS):
                extra[next(x for x in CACHE_DIRS if x in parts)] += 1
                cache_mt.append(os.path.getmtime(os.path.join(dp, f)))
            else:
                extra_noncache.append(rel)
    res['unlisted_cache_files'] = dict(extra)
    res['unlisted_cache_mtime_range'] = ([datetime.datetime.fromtimestamp(min(cache_mt)).strftime('%Y-%m-%d %H:%M:%S'),
                                          datetime.datetime.fromtimestamp(max(cache_mt)).strftime('%Y-%m-%d %H:%M:%S')]
                                         if cache_mt else None)
    res['n_unlisted_noncache'] = len(extra_noncache)
    res['unlisted_noncache_files'] = extra_noncache[:50]
    res['ok'] = (res['n_listed_bad'] == 0 and res['n_unlisted_noncache'] == 0 and res['git_head'] == P['head']
                 and (P['freeze'] is None or res['freeze_json_sha256'] == P['freeze']))
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(res, f, indent=1)
    print('FREEZE', profile, json.dumps({k: v for k, v in res.items() if k not in ('listed_bad', 'unlisted_noncache_files')}))


# ===================================================================================================== H-A unit self-test
def ha_unit(case_dir, T, out_path):
    set_below_normal()
    src = os.path.join(case_dir, 'previous')
    a = receipt_level_audit(case_dir, T, src, case_dir)
    a['tool_sha256'] = sha(os.path.abspath(__file__))
    a['case_dir'] = case_dir
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(a, f, indent=1, default=str)
    print('HA_UNIT', case_dir, {k: a.get(k) for k in ('HA1', 'HA2', 'HA3', 'HA5', 'HA7')}, 'HA1_evidence_bad', a.get('HA1_evidence_bad'),
          'HA1_detail_false', [k for k, v in (a.get('HA1_detail') or {}).items() if v is not True])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', choices=('check', 'pair', 'freeze', 'ha_unit'))
    ap.add_argument('--profile', choices=tuple(PROFILES))
    ap.add_argument('--seed')
    ap.add_argument('--out', required=True)
    ap.add_argument('--dir')
    ap.add_argument('--T', type=int)
    a = ap.parse_args()
    if a.seed is not None and a.seed not in ('31', '41', '43'):
        raise SystemExit('seed refused: %s' % a.seed)
    if a.mode == 'check':
        check(a.profile, a.seed, a.out)
    elif a.mode == 'pair':
        pair(a.profile, a.seed, a.out)
    elif a.mode == 'freeze':
        freeze(a.profile, a.out)
    else:
        ha_unit(a.dir, a.T, a.out)


if __name__ == '__main__':
    main()
