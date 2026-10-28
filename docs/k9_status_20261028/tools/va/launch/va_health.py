"""V-A first SDMPC decision health check (amendment 34 sec.6.4, H1-H16, T1, T2).  READ ONLY toward the run folder.

python -B va_health.py <seed> <T> <out.json> [--min-age 300]   (test only: --rva <root> --name <run> --live <dir>)

The run is RVA\\sdmpc31_v3c3_k92va_s<seed>.  Files are COPIED to REPVA\\live\\<run>\\health\\T<T6>_<stamp>\\ (sha256 of
source == copy) and only the copies are parsed.  Decision files action_<t>.* are copied only when older than
--min-age seconds (amendment 34 sec.6.3).  Logs (still growing) are snapshot copies taken now (J1 rerun precedent
S31_RERUN_LAUNCH.md sec.7-3).  Output: T list, counts, booleans, sizes, mtimes, sha256, key NAMES, exit= / wall_sec of
CONTROLLER_DECISION lines, first tokens of hold / ERROR= lines.  Values compared for H14-H16 (5209.8, s, 1.0) are
compared in memory only and never printed.  It never reads or prints objective values, predictions, prices, Omega,
TTT, delays or command values.  H10 reading fixed before data (amendment 34 sec.6.4, D-K9-25): the WD policy line once
per WD call = 2 lines (preflight call before 'START <run>', run call after it), all hold, strict 0.
"""
import datetime
import glob
import hashlib
import json
import os
import re
import shutil
import sys
import time

sys.dont_write_bytecode = True
RVA = r'D:\VISSIM_runs\20261023_sdmpc31_k92'
LIVE = r'D:\VISSIM_runs\20261001_v3c3\reports\k8\k92_va\live'
HEAD = 'c20aff1d7bf0c432cb4f20e2922bd406d857aa5d'
FREEZE_SHA = '011f5be253fd31a5fb8342859b2b571375e49b4bbbbb42ea8f3ca93657b68476'
TUNING_SHA = 'c8e3ee2c99b66c255b2279f0aa18eaafc18d4c7689e59e260109fac3b7d71866'
NET_SHA = '3de889f0257d998bed50611f798ea388bcf69396dbc40e5726b1e88ebdd31c2e'
WD_LINE = 'RW_DECISION_ERROR_POLICY=hold_previous_on_exception (runtime.decision_error_policy)'
W_AFTER_REPR = '5209.8'
S_REPR = '1045.1612903225805'
FLOOR_RE = re.compile(r'^head_discharge_floor_173_p4_[0-9a-f]{16}$')


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def copy(src, dst_dir, min_age=None):
    if not os.path.isfile(src):
        return None, 'absent'
    if min_age is not None and time.time() - os.path.getmtime(src) < min_age:
        return None, 'too_new'
    os.makedirs(dst_dir, exist_ok=True)
    dst = os.path.join(dst_dir, os.path.basename(src))
    for _ in range(3):  # a log being appended can change during the copy; retry
        s1 = sha(src)
        shutil.copyfile(src, dst)
        s2, s3 = sha(src), sha(dst)
        if s1 == s2 == s3:
            return dst, 'ok'
        time.sleep(2)
    return None, 'unstable'


def text(p):
    if p is None:
        return None
    with open(p, encoding='utf-8', errors='replace') as f:
        return f.read()


def load(p):
    with open(p, encoding='utf-8') as f:
        return json.load(f)


def main():
    seed, t, out = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
    min_age = int(sys.argv[sys.argv.index('--min-age') + 1]) if '--min-age' in sys.argv else 300
    # test-only overrides (pre-launch tool test on a J1 run): --rva <RunsRoot> --name <run> --live <copy root>
    rva = sys.argv[sys.argv.index('--rva') + 1] if '--rva' in sys.argv else RVA
    live = sys.argv[sys.argv.index('--live') + 1] if '--live' in sys.argv else LIVE
    name = sys.argv[sys.argv.index('--name') + 1] if '--name' in sys.argv else 'sdmpc31_v3c3_k92va_s%d' % seed
    run = os.path.join(rva, name)
    dec = os.path.join(run, 'decisions_' + name)
    stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
    cdir = os.path.join(live, name, 'health', 'T%06d_%s' % (t, stamp))
    r = {'seed': seed, 'name': name, 'T': t, 'checked_at': datetime.datetime.now().astimezone().isoformat(timespec='seconds'),
         'copy_dir': cdir, 'tool_sha256': sha(os.path.abspath(__file__))}
    stem = 'action_%06d' % t
    names = sorted(os.listdir(dec)) if os.path.isdir(dec) else []
    r['decision_T'] = sorted(int(n[7:13]) for n in names if re.fullmatch(r'action_\d{6}\.json', n))
    r['decisions_count_le_T'] = sum(1 for x in r['decision_T'] if x <= t)
    r['error_files'] = [n for n in names if n.endswith('.error.txt')]
    r['hold_receipts'] = [n for n in names if n.endswith('.hold.json')]
    r['hold_error_files'] = [n for n in names if n.endswith('.hold_error.txt')]
    r['failed_decision_files'] = [n for n in names if n.endswith('.failed_decision')]
    files = {}
    for suf in ('.json', '.csv', '.json.applied', '.stdout.txt', '.stderr.txt', '.decision_budget.json',
                '.hold.json', '.hold_error.txt', '.error.txt'):
        p = os.path.join(dec, stem + suf)
        files[suf] = ({'present': True, 'bytes': os.path.getsize(p),
                       'mtime': datetime.datetime.fromtimestamp(os.path.getmtime(p)).strftime('%H:%M:%S')}
                      if os.path.isfile(p) else {'present': False})
    r['files_T'] = files
    logs = {'runlog': os.path.join(run, 'runlog_%s.txt' % name), 'runlog_err': os.path.join(run, 'runlog_%s.txt.err' % name),
            'launch': os.path.join(run, 'launch_%s.log' % name), 'wmi': os.path.join(rva, 'wmi_%s.log' % name),
            's6_stdout': os.path.join(dec, stem + '.stdout.txt'), 's6_stderr': os.path.join(dec, stem + '.stderr.txt')}
    lt, r['log_copy'] = {}, {}
    for k, p in logs.items():
        dst, st = copy(p, os.path.join(cdir, 'logs'), None if k in ('runlog', 'runlog_err', 'launch', 'wmi') else min_age)
        r['log_copy'][k] = st
        lt[k] = text(dst) if dst else None
    r['DECISION_FAILED'] = {k: (v.count('DECISION_FAILED') if v is not None else None) for k, v in lt.items()}
    rl = (lt['runlog'] or '').splitlines()
    cd = []
    for line in rl:
        if line.startswith('CONTROLLER_DECISION sim_sec='):
            m = re.match(r'CONTROLLER_DECISION sim_sec=(\d+)', line)
            e = re.search(r'exit=(-?\d+)', line)
            w = re.search(r'wall_sec=([0-9.]+)', line)
            cd.append({'sim_sec': int(m.group(1)), 'exit': int(e.group(1)) if e else None,
                       'wall_sec': float(w.group(1)) if w else None})
    r['controller_decisions'] = cd
    r['decision_exit_T'] = [x['exit'] for x in cd if x['sim_sec'] == t]
    r['runlog_policy_line_count'] = sum(1 for x in rl if x.strip() == 'DECISION_ERROR_POLICY=hold_previous_on_exception')
    r['runlog_policy_any_count'] = sum(1 for x in rl if 'DECISION_ERROR_POLICY=' in x)

    def simsecs(prefix):
        o = []
        for x in rl:
            if prefix in x:
                m = re.search(r'sim_sec=(\d+)', x)
                o.append({'sim_sec': int(m.group(1)) if m else None, 'first_token': x.split()[0] if x.split() else ''})
        return o
    r['runlog_hold_attempt'] = simsecs('DECISION_HOLD_ATTEMPT')
    r['runlog_held'] = simsecs('DECISION_HELD_ON_EXCEPTION')
    r['runlog_ERROR'] = simsecs('ERROR=')
    prog = [x for x in rl if x.startswith('NATIVE_SIM_PROGRESS')]
    m = re.search(r'sim_sec=(\d+)', prog[-1]) if prog else None
    r['last_native_sim_sec'] = int(m.group(1)) if m else None
    la = (lt['launch'] or '').splitlines()
    # the runner's own START line (the watchdog's 'WD <time>  START <run> attempt=' line is not it)
    start_idx = [i for i, x in enumerate(la) if re.match(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}  START %s out_dir=' % re.escape(name), x)]
    wd_pos = [i for i, x in enumerate(la) if WD_LINE in x]
    r['launch_start_line'] = [i + 1 for i in start_idx]
    r['launch_wd_policy_line_positions'] = [i + 1 for i in wd_pos]
    r['launch_wd_policy_line_count'] = len(wd_pos)
    r['launch_any_policy_line_count'] = sum(1 for x in la if 'RW_DECISION_ERROR_POLICY' in x)
    r['launch_strict_line_count'] = sum(1 for x in la if 'RW_DECISION_ERROR_POLICY=strict' in x)
    if len(start_idx) == 1:
        r['wd_policy_before_start'] = sum(1 for i in wd_pos if i < start_idx[0])
        r['wd_policy_after_start'] = sum(1 for i in wd_pos if i > start_idx[0])
    fv = [x for x in la if 'FREEZE_VERIFIED' in x]
    r['launch_freeze_verified_count'] = len(fv)
    r['launch_freeze_verified_values_ok'] = len(fv) == 1 and ('sha256=' + FREEZE_SHA) in fv[0] and ('head=' + HEAD) in fv[0]
    po = [x for x in la if 'PROVENANCE_OK' in x]
    r['launch_provenance_ok_count'] = len(po)
    r['launch_provenance_ok_values_ok'] = len(po) == 1 and ('freeze=' + FREEZE_SHA) in po[0]
    r['launch_refused_count'] = sum(1 for x in la if 'REFUSED' in x)
    r['launch_stage_exit_lines'] = [x[21:140] for x in la if ' STAGE=' in x or re.search(r'\bEXIT\b', x)]
    prov = {}
    for k, p in (('run', os.path.join(run, 'run_provenance_%s.json' % name)),
                 ('preflight', os.path.join(run, 'preflight', 'run_provenance_%s.json' % name))):
        dst, st = copy(p, os.path.join(cdir, 'prov_' + k))
        if dst:
            tx = text(dst)
            d = json.loads(tx)
            ft = (d.get('files') or {}).get('tuning')
            prov[k] = {'copy': st, 'sha256': sha(dst), 'tuning_sha_count': tx.count(TUNING_SHA),
                       'files_tuning_sha_ok': isinstance(ft, dict) and ft.get('sha256') == TUNING_SHA,
                       'network_sha_count': tx.count(NET_SHA), 'freeze_sha_count': tx.count(FREEZE_SHA),
                       'env_policy': (d.get('env') or {}).get('RW_DECISION_ERROR_POLICY'),
                       'env_fail_fast': (d.get('env') or {}).get('RW_DECISION_FAIL_FAST'), 'seed': d.get('seed')}
        else:
            prov[k] = {'copy': st}
    r['provenance'] = prov
    # ---------------- decision files (copies, min age) ----------------
    jd, st = copy(os.path.join(dec, stem + '.json'), cdir, min_age)
    r['action_json_copy'] = st
    if jd:
        doc = load(jd)
        md = doc.get('metadata') if isinstance(doc.get('metadata'), dict) else {}
        ic = md.get('stopline_approach_install_check')
        r['sdmpc_active'] = md.get('sdmpc_active')
        r['controller_status'] = md.get('controller_status') if isinstance(md.get('controller_status'), str) else None
        r['install_check_present'] = ic is not None
        r['install_check_passed'] = ic.get('passed') if isinstance(ic, dict) else None
        r['hold_previous_on_exception_in_metadata'] = 'hold_previous_on_exception' in md
        r['T_k92_w_present'] = isinstance(md.get('k92_w'), dict)
        r['T_k92_hb_present'] = isinstance(md.get('k92_hb'), dict)
        r['T_floor_keys'] = sorted(k for k in md if FLOOR_RE.match(k))
        r['action_json_sha256'] = sha(jd)
        del doc, md
    bd, st = copy(os.path.join(dec, stem + '.decision_budget.json'), cdir, min_age)
    r['budget_copy'] = st
    if bd:
        b = json.loads(text(bd))
        r['budget'] = {k: b.get(k) for k in ('unlimited_time', 'expired_stage', 'output_completed')}
    cs, st = copy(os.path.join(dec, stem + '.csv'), cdir, min_age)
    r['action_csv_sha256'] = sha(cs) if cs else st
    ap, st = copy(os.path.join(dec, stem + '.json.applied'), cdir, min_age)
    r['applied_copy'] = st
    # T = 1 (H14) and T = 150 (H15)
    h14 = {}
    j1p, st = copy(os.path.join(dec, 'action_000001.json'), os.path.join(cdir, 'T000001'), min_age)
    h14['copy'] = st
    if j1p:
        md = (load(j1p).get('metadata') or {})
        w = md.get('k92_w')
        hb = md.get('k92_hb')
        fk = sorted(k for k in md if FLOOR_RE.match(k))
        h14['k92_w_dict'] = isinstance(w, dict)
        h14['k92_w_after_float_repr_ok'] = isinstance(w, dict) and isinstance(w.get('after'), float) and repr(w.get('after')) == W_AFTER_REPR
        h14['k92_hb_present'] = isinstance(hb, dict)
        h14['floor_keys'] = fk
        h14['floor_value_repr_ok'] = (len(fk) == 1 and isinstance(md[fk[0]], float) and repr(md[fk[0]]) == S_REPR)
        b1 = md.get('k92_hb_seed_binding')
        h14['binding_float_1'] = isinstance(b1, float) and b1 == 1.0
        del md
    r['T1_meta'] = h14
    h15 = {}
    j150, st = copy(os.path.join(dec, 'action_000150.json'), os.path.join(cdir, 'T000150'), min_age)
    h15['copy'] = st
    if j150:
        md = (load(j150).get('metadata') or {})
        v = md.get('head_observation_prior_discarded')
        h15['prior_discarded_eq_1'] = (isinstance(v, (int, float)) and not isinstance(v, bool) and float(v) == 1.0)
        del md
    r['T150_meta'] = h15
    # ---------------- declared health items (amendment 34 sec.6.4) ----------------
    k = {}
    k['H1_json_csv_applied_present'] = all(files[s]['present'] for s in ('.json', '.csv', '.json.applied'))
    k['H2_sdmpc_active_true'] = r.get('sdmpc_active') is True
    k['H3_install_check_present_passed'] = r.get('install_check_present') is True and r.get('install_check_passed') is True
    k['H4_s6_capture_two'] = files['.stdout.txt']['present'] and files['.stderr.txt']['present']
    k['H5_error_txt_0'] = len(r['error_files']) == 0
    k['H6_DECISION_FAILED_0'] = all(v == 0 for v in r['DECISION_FAILED'].values())
    bu = r.get('budget') or {}
    k['H7_budget_true_null_true'] = (bu.get('unlimited_time') is True and 'expired_stage' in bu and bu.get('expired_stage') is None
                                     and bu.get('output_completed') is True)
    k['H8_decisions_count_7'] = (r['decisions_count_le_T'] == 7) if t == 900 else None
    k['H9_runlog_policy_line_exactly_1'] = r['runlog_policy_line_count'] == 1
    k['H10_wd_policy_one_per_wd_call'] = (r['launch_wd_policy_line_count'] == 2 and r.get('wd_policy_before_start') == 1
                                          and r.get('wd_policy_after_start') == 1 and r['launch_any_policy_line_count'] == 2
                                          and r['launch_strict_line_count'] == 0)
    k['H11_freeze_verified_1'] = r['launch_freeze_verified_values_ok']
    k['H12_provenance_ok_1_preflight'] = r['launch_provenance_ok_values_ok']
    k['H13_provenance_tuning_sha'] = (all(v.get('files_tuning_sha_ok') is True for v in prov.values() if 'sha256' in v)
                                      and any('sha256' in v for v in prov.values()))
    k['H14_T1_k92_and_floor'] = (h14.get('k92_w_after_float_repr_ok') is True and h14.get('k92_hb_present') is True
                                 and h14.get('floor_value_repr_ok') is True and h14.get('binding_float_1') is True)
    k['H15_T150_prior_discarded_1'] = h15.get('prior_discarded_eq_1') is True
    k['H16_T_k92_and_same_floor_name'] = (r.get('T_k92_w_present') is True and r.get('T_k92_hb_present') is True
                                          and r.get('T_floor_keys') is not None and r.get('T_floor_keys') == h14.get('floor_keys')
                                          and len(h14.get('floor_keys') or []) == 1)
    k['T1_decision_exit_0'] = r['decision_exit_T'] == [0]
    k['T2_no_hold_no_error'] = (not r['hold_receipts'] and not r['hold_error_files'] and not r['runlog_hold_attempt']
                                and not r['runlog_held'] and not r['runlog_ERROR'] and not r['error_files'])
    r['items'] = k
    r['hold_count'] = len(r['hold_receipts'])
    r['all_items_true'] = all(v is True for v in k.values() if v is not None)
    r['failed_items'] = [n for n, v in k.items() if v is not True and v is not None]
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(r, f, indent=1, ensure_ascii=False)
    print('HEALTH %s T=%d all_items_true=%s failed=%s decisions=%d hold=%d exit_T=%s action_json_copy=%s' % (
        name, t, r['all_items_true'], r['failed_items'], r['decisions_count_le_T'], r['hold_count'], r['decision_exit_T'],
        r.get('action_json_copy')))


if __name__ == '__main__':
    main()
