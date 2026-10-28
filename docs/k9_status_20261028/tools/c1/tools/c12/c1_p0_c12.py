"""C1-2 P0 additions (K8 amendment C1-2 dfe9809b7212bdc7..., section 8: P0-14, P0-15, P0-17, P0-18) + arms + values.

    python -B c1_p0_c12.py p0_17      light: the builder twice (two processes), C1D2/p0 four files (exclusive), (a)-(h)
    python -B c1_p0_c12.py arms       C1D/tools/arms_r2/: the seven first-probe arm files (bytes copied) + c1g + c1g_null
    python -B c1_p0_c12.py p0_18      heavy (LOCK): 330 V-A / B decision states on PT2 (runtime core vs occ.json and
                                      the independent recount)
    python -B c1_p0_c12.py p0_14      heavy (LOCK): configure-only runs on PT2 ((a) 5 x {c1, c1g}, (b) P0-3 25 + P0-6,
                                      (c) normaliser self-test with the new roots)
    python -B c1_p0_c12.py p0_15      heavy (LOCK): S_G categories K0-K6 on R-obs v3c3-s31 / s43, judging states skipped
    python -B c1_p0_c12.py values     C1D/C1_VALUES_C1_2.json (exclusive)
    python -B c1_p0_c12.py cfgrun <tag> <run> <T> <tuning file> --tree <name> [--controller C] [--out <dir>]
                                      one configure-only run (development smoke)
Outputs TC1/out/p0_c12/<step>/.  Stop rules: S-C1-21 (P0-17 / P0-18), S-C1-22 (P0-14), S-C1-20 (P0-15 S_G empty).
Run states are found by name + run_provenance sha256 (c1_states.json /runs); a seed is never read from a folder name.
BLIND: v3c3-s47 is never opened (c1common.blind_guard on every run name); no objective or prediction value is read.
Builder inputs (fixed with pin A): the network = INPX (sha256 3de889f0...), the plan and the tuning = the files of the
first probe tree PT (= git archive c20aff1d bytes, sha256 checked by the builder)."""
import gzip
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
import c1common as C  # noqa: E402
import c1g_build as B  # noqa: E402
import c1g_recount as RC  # noqa: E402

AMEND2_SHA = 'dfe9809b7212bdc7ac170143539b46e9c85a56303f2aed76585e36f061ba3bc4'
C1D2 = C.C1D / 'declared_c1_2'
OUT = C.TC1 / 'out' / 'p0_c12'
NUMBA = OUT / 'numba_cache'
LOG = C.make_logger(OUT / 'logs' / 'c1_p0_c12.log')
STATES = json.loads((C.DECL / 'c1_states.json').read_text(encoding='utf-8'))
RUNS = {r['name']: r for r in STATES['runs']}
PT = C.TC1 / 'trees' / 'probe_5cdc6eb1'
INPX = Path(r'D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s31/network/sdmpc31_sdmpc31_v3c3_k92va_s31.inpx')
PLAN_REL = 'diagnostics/controller_confidence_20260913/local_native_clock_v2/native_clock_plan_local.json'
GG = C.C1D / 'guard' / 'general'
SEGMENTS_JSON = C.TC1 / 'guard_general' / 'data' / 'segments.json'
SEGMENTS_SHA = 'ac374b01012c766a'
INVENTORY_JSON = GG / 'inventory.json'
INVENTORY_SHA = 'c8584f367c968888'
GR_CHECK_JSON = GG / 'work' / 'review' / 'gr_check.json'
GR_CHECK_SHA = 'be9385c6fb6c2fbc'
OCC_JSON = GG / 'work' / 'occ.json'
OCC_SHA = 'cd4ba7f4d5edce57'
RULE = C1D2 / 'c1g_guard_rule.json'
RULE_SHA = '938271380735313d5d2c1efde51423430cfe080c4c8c08c1e39c185e6d5806da'
EV_NAME, EV_NULL_NAME = 'c1g_storage_segments_v3c3.json', 'c1g_storage_segments_null_v3c3.json'
P0DIR = C1D2 / 'p0'
RG19 = {'A': 216, 'L': 9, 'F': 896, 'M': 10, 'MA': 10, 'R': 254, 'total': 1395, 'receiver_items': 261,
        'codex_heads': 210, 'feeder_links': 416, 'short_nonR': 156, 'short_F': 144, 'short_A': 10, 'short_L': 2,
        'short_R': 4, 'overlaps_nonR': 58, 'heads_without_receivers': 3}
SEC_SHA = '865cc354e498f1c77894f376e249682d52ee082639eaa585ec13af5f0d059654'
GUARD_ORDER = ('segments_name', 'segments_sha256', 'unit', 'full_rule', 'capacity_threshold', 'min_source_capacity_veh',
               'feeder_attribution', 'landing_sources', 'short_receiver_rule', 'reserve_green_sec', 'meter_rule')
GUARD_FIXED = {'unit': 'lane', 'full_rule': 'count_or_spill', 'capacity_threshold': 1.0,
               'min_source_capacity_veh': 2.0, 'feeder_attribution': 'cell_chain_max', 'landing_sources': True,
               'short_receiver_rule': 'count', 'reserve_green_sec': 2.0, 'meter_rule': 'approach_chain_or_m4'}
ARMS_R2 = C.TOOLS / 'arms_r2'
OLD_ARMS = ('off', 'omega', 'm', 'h', 'c1', 'm_cap1', 'm_noheld')
T_C1 = '522eec6f32f198a12ddb78ddec10962a73c7ebc32e2d1fcbb11f95975218d865'


# ================================================================================================ helpers
def short_sha_ok(path, prefix):
    return C.sha256_file(path).startswith(prefix)


def result_write(step, res):
    path = OUT / step / 'result.json'
    C.write_json(path, res)
    LOG('RESULT %s verdict=%s sha256=%s' % (step, res.get('verdict'), C.sha256_file(path)))
    return path


def run_rec(name):
    C.blind_guard(name)
    r = RUNS.get(name)
    if r is None:
        raise SystemExit('run not in c1_states.json /runs: ' + name)
    return r


def run_dir_of(name):
    """The run folder by name + run_provenance sha256 (never by a seed in a folder name)."""
    r = run_rec(name)
    base = C.RUNS[r['kind']]
    direct = base / name
    hits = [direct] if (direct / ('run_provenance_%s.json' % name)).is_file() else \
        [p.parent for p in base.glob('*/*/run_provenance_%s.json' % name)] + \
        [p.parent for p in base.glob('*/run_provenance_%s.json' % name)]
    hits = [h for h in hits if C.sha256_file(h / ('run_provenance_%s.json' % name)) == r['provenance_sha256']]
    if len(hits) != 1:
        raise SystemExit('run folder not found by provenance sha: %s (%d)' % (name, len(hits)))
    return hits[0]


def decisions_dir(name):
    return run_dir_of(name) / ('decisions_' + name)


def tree_of_patch_r2():
    man = json.loads((HERE / 'c1_probe_r2_manifest.json').read_text(encoding='utf-8'))
    return C.TC1 / 'trees' / ('probe_' + man['patch_sha256'][:8]), man


def child_env_tree():
    env = C.child_env(NUMBA)
    env['PYTHONPATH'] = C.DEPROOT + r'\sdmpc;' + C.DEPROOT + r'\sdmpc-numba'
    return env


# ================================================================================================ configure runs
def prepare(run, T, dest):
    dec = decisions_dir(run)
    rec = dest.parent / (dest.name + '.prep.json')
    if (dest / 'replay_manifest.json').is_file() and rec.is_file():
        return C.read_json(rec)
    if dest.exists():
        dest.rename(dest.parent / ('%s_interrupted_%d_%d' % (dest.name, os.getpid(), time.time_ns())))
    rc, _sec, _ = C.run_capture([C.PY, '-B', str(C.GPREP), str(dec), str(T), str(dest), str(rec)],
                                dest.parent / (dest.name + '.prepare.txt'), C.child_env(NUMBA))
    r = C.read_json(rec) or {}
    if rc != 0 or not r.get('all_copies') or not r.get('state_obs150_directory_is_bundle') \
            or r.get('history_count') != r.get('history_expected'):
        raise SystemExit('PREPARE_FAILED %s T=%s rc=%s' % (run, T, rc))
    return r


def adapter_call(rd, root, tuning, controller=None, out_dir=None):
    """c1_p0.py adapter_call (the k92_replay.py argument list and environment) with an explicit tuning file."""
    BS = chr(92)
    m = json.loads((rd / 'replay_manifest.json').read_text(encoding='utf-8-sig'))
    sec = int(m['sim_sec'])
    s6 = '%06d' % sec
    dec = Path(m['source_decisions'])
    run_dir = dec.parent
    run_name = re.sub(r'^decisions_', '', dec.name)
    C.blind_guard(run_name)
    prov = json.loads((run_dir / ('run_provenance_%s.json' % run_name)).read_text(encoding='utf-8-sig'))
    run_root = prov['workspace_root']

    def rebase(p):
        full = os.path.abspath(p)
        base = os.path.abspath(run_root).rstrip(BS) + BS
        return os.path.join(str(root), full[len(base):]) if full.lower().startswith(base.lower()) else p
    prev = str(dec / ('action_%06d.json' % int(m['previous_sec']))) if m.get('previous_sec') is not None else None
    if not controller:
        plan = json.loads((run_dir / 'launch_plan.json').read_text(encoding='utf-8-sig'))
        controller = plan['warmup_controller'] if sec < int(plan['control_start_sec']) else plan['controller']
    files = prov['files']
    mapping = rebase(files['control_mapping']['path'])
    calibration = rebase(files['calibration']['path'])
    runner_config = rebase(files['generated_vbs_config']['path'])
    det = ''
    for line in Path(runner_config).read_text(encoding='utf-8', errors='replace').splitlines():
        mm = re.match(r'^\s*RW_DETECTOR_MAPPING_PATH\s*=\s*"(.*)"\s*$', line)
        if mm:
            det = mm.group(1)
    adapter = str(root / 'evaluation' / 'controllers' / 'vissim_stackelberg_adapter.py')
    out_dir = Path(out_dir or rd / 'cfgonly')
    a = [adapter, '--state-json', m['state']['replay'], '--out-action-json', str(out_dir / ('action_%s.json' % s6)),
         '--out-action-csv', str(out_dir / ('action_%s.csv' % s6)), '--mapping-json', mapping, '--controller', controller]
    if det:
        a += ['--detector-mapping-json', det]
    a += ['--calibration-json', calibration, '--tuning-json', str(tuning)]
    if prev:
        a += ['--previous-action-json', prev]
    mode = str(prov['env'].get('RW_ADAPTER_MODE') or '')
    if mode:
        a += ['--mode', mode]
    env = C.child_env(NUMBA)
    env = {k: v for k, v in env.items() if not k.upper().startswith('RW_')}
    env.update({k: str(v) for k, v in prov['env'].items()})
    env['PYTHONPATH'] = C.DEPROOT + r'\sdmpc;' + C.DEPROOT + r'\sdmpc-numba'
    env.update(OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1', PYTHONUTF8='1', PYTHONHASHSEED='0',
               NUMBA_CACHE_DIR=str(NUMBA))
    env.pop('NUMBA_NUM_THREADS', None)
    return str(prov['env'].get('RW_PYTHON') or ''), a, env, {'sim_sec': sec, 'controller': controller,
                                                             'previous': prev, 'run': run_name}


def cfg_run(tag, run, T, tuning, tree, base, controller=None, tuning_sha=None):
    d = base / tag
    res_file = d / 'child' / 'configured.json'
    if res_file.is_file():
        return C.read_json(res_file)
    if (d / 'child' / 'configure_failed.json').is_file():
        return C.read_json(d / 'child' / 'configure_failed.json')
    C.require_space(LOG)
    if tuning_sha is not None and C.sha256_file(tuning) != tuning_sha:
        raise SystemExit('tuning changed: ' + str(tuning))
    prepare(run, T, d / 'bundle')
    python, a, env, info = adapter_call(d / 'bundle', tree, tuning, controller=controller, out_dir=d / 'adapter_out')
    (d / 'child').mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    rc, _sec, _ = C.run_capture([python, '-B', str(HERE / 'c12_child.py'), str(d / 'child')] + a, d / 'child.txt', env,
                                cwd=tree)
    rec = C.read_json(res_file) or C.read_json(d / 'child' / 'configure_failed.json') or {'ok': False, 'error': 'no record'}
    rec['_run'] = {'tag': tag, 'run': run, 'T': T, 'tuning_sha256': C.sha256_file(tuning), 'tree': Path(tree).name,
                   'exit': rc, 'wall_sec': round(time.time() - t0, 1), **info}
    C.write_json(d / 'run.json', rec['_run'])
    LOG('CFGRUN %s run=%s T=%s tree=%s exit=%s ok=%s wall=%.0f' % (tag, run, T, Path(tree).name, rc, rec.get('ok'),
                                                                    time.time() - t0))
    return rec


def leaves_of(d):
    with gzip.open(d / 'child' / 'cfgnet_leaves.json.gz', 'rt', encoding='utf-8') as g:
        return json.load(g)


def gen(path):
    return re.sub(r'/\[\d+\]', '/[*]', path)


def leaf_diff(a, b):
    """amendment C1 P0-3 form (c1_p0.py diff_set): every differing leaf path, list indices generalised."""
    return sorted({gen(k.lstrip('/')) for k in set(a) | set(b) if a.get(k) != b.get(k)})


def k7_diff(a, b):
    """K7 deep_diff form (c1common.deep_diff): a path present on one side only is reported at its first missing node."""
    def prefixes(keys):
        out = set()
        for k in keys:
            parts = k.lstrip('/').split('/')
            for i in range(1, len(parts) + 1):
                out.add('/'.join(parts[:i]))
        return out
    pa, pb = prefixes(a), prefixes(b)
    res = set()
    for k in set(a) | set(b):
        if k in a and k in b:
            if a[k] != b[k]:
                res.add(gen(k.lstrip('/')))
            continue
        other = pb if k in a else pa
        parts = k.lstrip('/').split('/')
        for i in range(1, len(parts) + 1):
            q = '/'.join(parts[:i])
            if q not in other:
                res.add(gen(q))
                break
    return sorted(res)


def state_tag(st, arm):
    return 't%06d_%s_%s' % (st['T'], st['run'].replace('sdmpc31_', '').replace('_', ''), arm)


# ================================================================================================ P0-17
def builder_inputs():
    return [str(INPX), str(PT / PLAN_REL), str(PT / C.OUC_REL)]


def p0_17():
    d = OUT / 'p0_17'
    d.mkdir(parents=True, exist_ok=True)
    runs = []
    for k in (1, 2):
        rd = d / ('run%d' % k)
        if not (rd / EV_NAME).is_file():
            rc, sec, text = C.run_capture([C.PY, '-B', str(HERE / 'c1g_build.py')] + builder_inputs()
                                          + [str(rd / EV_NAME), str(rd / EV_NULL_NAME)], d / ('build%d.txt' % k),
                                          C.child_env(NUMBA))
            LOG('P0_17 build %d exit=%s sec=%.1f' % (k, rc, sec))
        runs.append((rd / EV_NAME, rd / EV_NULL_NAME))
    b1, b2 = runs[0][0].read_bytes(), runs[1][0].read_bytes()
    n1, n2 = runs[0][1].read_bytes(), runs[1][1].read_bytes()
    S17, S17n = C.sha256_bytes(b1), C.sha256_bytes(n1)
    checks, rep = {}, {}
    checks['a_two_builds_same_bytes'] = b1 == b2 and n1 == n2
    # (a) the declared bytes (exclusive create; an existing file must be byte-identical)
    sec_raw = (C.DECL / 'c1_port_section.json').read_bytes()
    if C.sha256_bytes(sec_raw) != SEC_SHA:
        raise SystemExit('c1_port_section.json differs')
    section = json.loads(sec_raw)['c1_port']

    def guard(name, sha):
        g = {'segments_name': name, 'segments_sha256': sha}
        g.update(GUARD_FIXED)
        return {k: g[k] for k in GUARD_ORDER}
    sec_g = {'c1_port': dict(section, storage_capacity_guard=guard(EV_NAME, S17))}
    sec_gn = {'c1_port': dict(section, storage_capacity_guard=guard(EV_NULL_NAME, S17n))}
    want = {EV_NAME: b1, EV_NULL_NAME: n1, 'c1_port_section_c1g.json': C.data(sec_g),
            'c1_port_section_c1g_null.json': C.data(sec_gn)}
    written = {}
    if checks['a_two_builds_same_bytes']:
        for name, payload in want.items():
            p = P0DIR / name
            if p.exists():
                written[name] = p.read_bytes() == payload
            else:
                C.write_new(p, payload)
                written[name] = True
        C.log_md('P0-17 (a): S17 = %s, S17_0 = %s; C1D2/p0/ c1_port_section_c1g.json %s, _null %s (배타 생성 또는 같은 '
                 '바이트 확인 %s)' % (S17, S17n, C.sha256_bytes(want['c1_port_section_c1g.json']),
                                       C.sha256_bytes(want['c1_port_section_c1g_null.json']), written))
    checks['a_declared_bytes_written'] = bool(written) and all(written.values())
    checks['a_guard_repr'] = repr(sec_g['c1_port']['storage_capacity_guard']) == (
        "{'segments_name': 'c1g_storage_segments_v3c3.json', 'segments_sha256': '%s', 'unit': 'lane', "
        "'full_rule': 'count_or_spill', 'capacity_threshold': 1.0, 'min_source_capacity_veh': 2.0, "
        "'feeder_attribution': 'cell_chain_max', 'landing_sources': True, 'short_receiver_rule': 'count', "
        "'reserve_green_sec': 2.0, 'meter_rule': 'approach_chain_or_m4'}" % S17)
    ev = json.loads(b1.decode('utf-8'))
    p0_17_checks(ev, checks, rep)
    res = {'step': 'P0-17', 'amendment_c1_2_sha256': AMEND2_SHA, 'S17': S17, 'S17_null': S17n,
           'evidence_bytes': len(b1), 'null_bytes': len(n1),
           'section_c1g_sha256': C.sha256_bytes(want['c1_port_section_c1g.json']),
           'section_c1g_null_sha256': C.sha256_bytes(want['c1_port_section_c1g_null.json']),
           'builder_sha256': C.sha256_file(HERE / 'c1g_build.py'),
           'inputs': {'network': [INPX.name, C.sha256_file(INPX)], 'plan': C.sha256_file(PT / PLAN_REL),
                      'tuning': C.sha256_file(PT / C.OUC_REL)},
           'checks': checks, 'report': rep}
    res['verdict'] = 'PASS' if all(checks.values()) else 'STOP'
    result_write('p0_17', res)
    LOG('P0_17 checks %s' % json.dumps(checks))


def p0_17_checks(ev, checks, rep):
    """P0-17 (b)-(h) on one evidence document (the (a) checks are in p0_17)."""
    E = {s['id']: s for s in ev['segments']}
    cells = {c['id']: c for c in ev['cells']}
    # (b)
    if not short_sha_ok(SEGMENTS_JSON, SEGMENTS_SHA):
        raise SystemExit('segments.json differs from its pin')
    segs = [s for s in json.loads(SEGMENTS_JSON.read_text(encoding='utf-8'))['segments'] if not s['id'].startswith('D5')]
    S = {s['id']: s for s in segs}
    nonR = {k for k in E if E[k]['kind'] != 'R'}
    span_bad = [k for k, s in S.items() if k not in E or str(E[k]['link']) != str(s['link'])
                or int(E[k]['lane']) != int(s['lane']) or abs(E[k]['start_m'] - float(s['from_m'])) > 1e-6
                or abs(E[k]['end_m'] - float(s['to_m'])) > 1e-6
                or abs(E[k]['capacity_veh'] - (float(s['to_m']) - float(s['from_m'])) / 6.0) > 1e-6]
    checks['b_ids_1141_equal'] = set(S) == nonR and len(S) == 1141
    checks['b_spans_capacity'] = not span_bad
    rep['b_span_bad'] = span_bad[:40]
    # (c) codex 210 lanes vs B v3c3-s31 T=900 decision JSON (key = link, lane, head_no <-> head_id)
    b_runs = [r for r in STATES['runs'] if r['kind'] == 'b' and r['label'] == 'v3c3-s31']
    cx = None
    if len(b_runs) == 1:
        p = decisions_dir(b_runs[0]['name']) / 'action_000900.json'
        doc = json.loads(p.read_text(encoding='utf-8-sig'))
        cx = (((doc.get('metadata') or {}).get('joint_leader_selection') or {}).get('urban_storage_guard') or {}).get(
            'observation', {}).get('lanes')
        rep['c_source'] = {'run': b_runs[0]['name'], 'action_000900_sha256': C.sha256_file(p)}
    c_bad = []
    if cx:
        A = {(str(s['link']), int(s['lane']), str(s['head_no'])): s for s in ev['segments'] if s['kind'] == 'A'}
        for lane in cx:
            key = (str(lane['link']), int(lane['lane']), str(lane['head_id']))
            s = A.get(key)
            if s is None:
                c_bad.append(['missing', key])
                continue
            if abs(s['capacity_veh'] - float(lane['capacity_veh'])) > 1e-6:
                c_bad.append(['capacity', key])
            want_r = sorted((str(r['connector']), str(r['link']), int(r['lane']), float(r['position']),
                             float(r['position']) + float(r['capacity_veh']) * 6.0) for r in lane['receivers'])
            got_r = sorted((c, str(E[rid]['link']), int(E[rid]['lane']), E[rid]['start_m'], E[rid]['end_m'])
                           for c, rid in zip(s['receiver_connectors'], s['receivers']))
            if len(want_r) != len(got_r) or any(a[:3] != b[:3] or abs(a[3] - b[3]) > 1e-6 or abs(a[4] - b[4]) > 1e-6
                                                for a, b in zip(want_r, got_r)):
                c_bad.append(['receivers', key])
        rep['c_codex_lanes'] = len(cx)
    checks['c_codex_210_capacity_receivers'] = bool(cx) and len(cx) == 210 and not c_bad
    rep['c_bad'] = c_bad[:40]
    # (d) attribution servers within the inventory link-level servers
    if not short_sha_ok(INVENTORY_JSON, INVENTORY_SHA):
        raise SystemExit('inventory.json differs from its pin')
    inv = json.loads(INVENTORY_JSON.read_text(encoding='utf-8'))
    fs = {f['link']: {x for lab in f['dist_from_end_to_server_m'] for x in B.server_keys_of_inventory_label(lab)}
          for f in inv['feeders']}
    offs = {c: {x for lab in o['topology_servers'] for x in B.server_keys_of_inventory_label(lab)}
            for c, o in inv['offramps'].items()}
    d_bad = []
    for s in ev['segments']:
        allowed = fs.get(s['link'], set()) if s['kind'] == 'F' else offs.get(s['id'].split(':')[1], set()) \
            if s['kind'] == 'L' else None
        if allowed is not None and not set(s['servers']) <= allowed:
            d_bad.append([s['id'], sorted(set(s['servers']) - allowed)])
    checks['d_servers_within_inventory'] = not d_bad
    rep['d_bad_n'] = len(d_bad)
    rep['d_bad'] = d_bad[:80]
    # (e) receivers 261 = inventory [landing_pos_m, segment_end_m]
    inv_r = sorted((a['link'], int(a['lane']), str(a['head_no']), r['connector'], str(r['link']), int(r['lane']),
                    float(r['landing_pos_m']), float(r['segment_end_m']))
                   for a in inv['approach_lanes'] if a['role'] == 'controlled_phase' for r in a['receivers'])
    ev_r = sorted((s['link'], int(s['lane']), str(s['head_no']), c, str(E[rid]['link']), int(E[rid]['lane']),
                   E[rid]['start_m'], E[rid]['end_m'])
                  for s in ev['segments'] if s['kind'] == 'A' for c, rid in zip(s['receiver_connectors'], s['receivers']))
    e_ok = len(inv_r) == len(ev_r) == 261 and all(a[:6] == b[:6] and abs(a[6] - b[6]) <= 1e-6 and abs(a[7] - b[7]) <= 1e-6
                                                 for a, b in zip(inv_r, ev_r))
    reused = sum(1 for s in ev['segments'] if s['kind'] == 'A' for rid in s['receivers'] if not rid.startswith('R:'))
    checks['e_receivers_261_spans'] = e_ok
    checks['e_existing_reuse_0_and_new_R_254'] = reused == 0 and ev['counts']['R'] == RG19['R']
    # (f) cells
    lanes = defaultdict(list)
    for c in ev['cells']:
        lanes[c['link'], c['lane']].append(c)
    cover_bad = []
    for k, rows in lanes.items():
        rows.sort(key=lambda c: c['start_m'])
        if abs(rows[0]['start_m']) > 1e-6 or any(abs(a['end_m'] - b['start_m']) > 1e-6 for a, b in zip(rows, rows[1:])):
            cover_bad.append(list(k))
    union_bad = []
    for s in ev['segments']:
        if not (s['source'] or s['kind'] == 'R'):
            continue
        rows = lanes.get((s['link'], s['lane']), [])
        inner = [c for c in rows if c['start_m'] >= s['start_m'] - 1e-6 and c['end_m'] <= s['end_m'] + 1e-6]
        ok = bool(inner) and abs(inner[0]['start_m'] - s['start_m']) <= 1e-6 and abs(inner[-1]['end_m'] - s['end_m']) <= 1e-6 \
            and all(abs(a['end_m'] - b['start_m']) <= 1e-6 for a, b in zip(inner, inner[1:]))
        if not ok:
            union_bad.append(s['id'])
    checks['f_cells_cover_lanes'] = not cover_bad
    checks['f_sources_receivers_are_cell_unions'] = not union_bad
    rep['f_union_bad_n'] = len(union_bad)
    rep['f_union_bad'] = union_bad[:120]
    lc71 = any(a['segment'].startswith('F:10643:') and a['server'] == 'SC1004_p4' for a in ev['attribution'])
    checks['f_10643_reaches_A71_lanes4_5_by_lane_change'] = lc71
    c129 = [c for c in lanes.get(('129', 1), []) if abs(c['start_m'] - 239.38) < 0.01 and abs(c['end_m'] - 299.99) < 0.02]
    branch = False
    if len(c129) == 1:
        c = c129[0]
        nxt = [n for n, _k in c['next']]
        to10490 = any(cells[n]['link'] == '10490' for n in nxt)
        via = [cells[n] for n in nxt if cells[n]['link'] == '129' and cells[n]['short']]
        to10777 = any(cells[m]['link'] == '10777' for v in via for m, _k in v['next'])
        branch = to10490 and to10777
    checks['f_129_cell_branches_10490_10777'] = branch
    meter_bad = []
    ma_lanes = {}
    for s in ev['segments']:
        if s['kind'] == 'MA':
            ma_lanes.setdefault(s['servers'][0], []).append(s)
    for a in ev['attribution']:
        m = a['server']
        if m not in ev['meters']:
            continue
        m_cells = {c for c in a['cells'] if cells[c]['link'] == ev['meters'][m]['connector'] and not cells[c]['short']}
        ma_cells = {c for c in a['cells'] for s in ma_lanes.get(m, []) if cells[c]['link'] == s['link']
                    and cells[c]['lane'] == s['lane'] and cells[c]['start_m'] >= s['start_m'] - 1e-6
                    and cells[c]['end_m'] <= s['end_m'] + 1e-6 and not cells[c]['short']}
        for removed, label in ((m_cells, 'M'), (ma_cells, 'MA')):
            adj = defaultdict(list)
            for u, v in a['edges']:
                adj[u].append(v)
            seen, stack = set(), [a['start_cell']] if a['start_cell'] not in removed else []
            hit = False
            while stack:
                u = stack.pop()
                if u in seen:
                    continue
                seen.add(u)
                if u == a['head_cell']:
                    hit = True
                    break
                stack.extend(v for v in adj[u] if v not in removed)
            if hit:
                meter_bad.append([a['segment'], m, label])
    conn_on_meter = 0
    for c in ev['cells']:
        for n, k in c['next']:
            if k == 'connector' and cells[n]['link'] in {v['connector'] for v in ev['meters'].values()} \
                    and c['link'] not in {v['connector'] for v in ev['meters'].values()} \
                    and cells[n]['start_m'] > 1e-6:
                conn_on_meter += 1
    checks['f_meter_paths_pass_M_and_MA'] = not meter_bad
    checks['f_no_connector_lands_on_meter_connector'] = conn_on_meter == 0
    rep['f_meter_bad'] = meter_bad[:40]
    # (g) overlaps
    if not short_sha_ok(GR_CHECK_JSON, GR_CHECK_SHA):
        raise SystemExit('gr_check.json differs from its pin')
    gr = json.loads(GR_CHECK_JSON.read_text(encoding='utf-8'))
    G = {tuple(sorted([p['a'], p['b']])) for p in gr['overlaps']['pairs']
         if not (p['a'].startswith('D5') or p['b'].startswith('D5'))}
    Pairs = {tuple(p) for p in ev['overlap_pairs']}
    PnR = {p for p in Pairs if not (p[0].startswith('R:') or p[1].startswith('R:'))}
    sub_ok = True
    for srv, comps in ev['overlap_groups'].items():
        for comp in comps:
            members = set(comp)
            inner = {p for p in Pairs if p[0] in members and p[1] in members}
            sub_ok &= bool(inner)
    checks['g_nonR_pairs_equal_gr_check_58'] = PnR == G and len(G) == RG19['overlaps_nonR']
    checks['g_groups_from_pairs'] = sub_ok
    rep['g_R_pairs'] = len(Pairs - PnR)
    # (h)
    cnt = ev['counts']
    short = defaultdict(int)
    for s in ev['segments']:
        if s['short']:
            short[s['kind']] += 1
    codex_heads = sum(1 for s in segs if s.get('codex'))
    no_recv = sum(1 for s in ev['segments'] if s['kind'] == 'A' and not s['receivers'])
    feeder_links = len({s['link'] for s in ev['segments'] if s['kind'] == 'F'})
    counts_ok = (all(cnt[k] == RG19[k] for k in ('A', 'L', 'F', 'M', 'MA', 'R')) and len(ev['segments']) == RG19['total']
                 and ev['receiver_items'] == RG19['receiver_items'] and codex_heads == RG19['codex_heads']
                 and feeder_links == RG19['feeder_links'] and short['F'] == RG19['short_F']
                 and short['A'] == RG19['short_A'] and short['L'] == RG19['short_L'] and short['R'] == RG19['short_R']
                 and no_recv == RG19['heads_without_receivers'])
    rep['h_counts'] = {'counts': cnt, 'total': len(ev['segments']), 'receiver_items': ev['receiver_items'],
                       'codex_heads': codex_heads, 'feeder_links': feeder_links, 'short': dict(short),
                       'heads_without_receivers': no_recv}
    ids_unique = len({s['id'] for s in ev['segments']}) == len(ev['segments']) and len(cells) == len(ev['cells'])
    bad_strings = []

    def walk(x, p=''):
        if isinstance(x, dict):
            for k, v in x.items():
                walk(v, p + '/' + str(k))
        elif isinstance(x, list):
            for i, v in enumerate(x):
                walk(v, p + '/%d' % i)
        elif isinstance(x, str) and p != '/schema':
            if '/' in x or chr(92) in x or x.lower().endswith(('.json', '.inpx', '.py', '.csv', '.npz', '.fzp')):
                bad_strings.append(p)
    walk(ev)
    if C.sha256_file(RULE) != RULE_SHA:
        raise SystemExit('rule file differs')
    rule = json.loads(RULE.read_text(encoding='utf-8'))
    spill_ok = all(ev['spill_rule'].get(k) == rule['spill'].get(k) for k in
                   ('top_window_m', 'stop_speed_kph', 'max_clear_gap_m', 'bottom_reach', 'short_length_m')) and \
        set(ev['spill_rule']) == {'top_window_m', 'stop_speed_kph', 'max_clear_gap_m', 'bottom_reach', 'short_length_m'}
    checks['h_counts_rg19'] = counts_ok
    checks['h_ids_unique'] = ids_unique
    checks['h_no_path_strings'] = not bad_strings
    checks['h_spill_rule_equals_rule_file'] = spill_ok
    checks['h_min_source_2_and_short_flags'] = ev['min_source_capacity_veh'] == 2.0 and all(
        s['short'] == (s['capacity_veh'] < 2.0) for s in ev['segments']) and all(
        c['short'] == ((c['end_m'] - c['start_m']) / 6.0 < 2.0) for c in ev['cells'])
    checks['h_guard_rule_sha'] = ev['guard_rule_sha256'] == RULE_SHA
    rep['h_bad_strings'] = bad_strings[:20]
    return checks, rep


# ================================================================================================ arms (after P0-17)
def arms():
    ARMS_R2.mkdir(parents=True, exist_ok=True)
    old = json.loads((C.TOOLS / 'arms' / 'ARMS.json').read_text(encoding='utf-8'))['arms']
    out = {'schema': 'c1-probe-arms/v2', 'base': {'name': 'config_n31_v2.json', 'sha256': C.OUC_SHA}, 'arms': {}}
    for arm in OLD_ARMS:
        raw = (C.TOOLS / 'arms' / (arm + '.json')).read_bytes()
        if C.sha256_bytes(raw) != old[arm]['sha256']:
            raise SystemExit('first arm file differs: ' + arm)
        p = ARMS_R2 / (arm + '.json')
        digest = C.write_new(p, raw) if not p.exists() else C.sha256_file(p)
        if digest != old[arm]['sha256']:
            raise SystemExit('arms_r2 copy differs: ' + arm)
        out['arms'][arm] = dict(old[arm])
    c1 = json.loads((C.TOOLS / 'arms' / 'c1.json').read_text(encoding='utf-8'))
    for arm, sec_name in (('c1g', 'c1_port_section_c1g.json'), ('c1g_null', 'c1_port_section_c1g_null.json')):
        sec = json.loads((P0DIR / sec_name).read_text(encoding='utf-8'))['c1_port']
        doc = dict(c1)
        doc['c1_port'] = sec
        payload = C.data(doc)
        p = ARMS_R2 / (arm + '.json')
        digest = C.write_new(p, payload) if not p.exists() else C.sha256_file(p)
        if digest != C.sha256_bytes(payload):
            raise SystemExit('arms_r2 file differs: ' + arm)
        out['arms'][arm] = {'label': {'c1g': 'C1G', 'c1g_null': 'C1G0'}[arm], 'keys': list(sec), 'sha256': digest}
    p = ARMS_R2 / 'ARMS.json'
    payload = json.dumps(out, indent=1, ensure_ascii=False) + '\n'
    if not p.exists():
        C.write_new(p, payload)
    elif p.read_text(encoding='utf-8') != payload:
        raise SystemExit('ARMS.json differs')
    LOG('ARMS_R2 %s' % {a: v['sha256'][:16] for a, v in out['arms'].items()})


def arm_file(arm):
    reg = json.loads((ARMS_R2 / 'ARMS.json').read_text(encoding='utf-8'))['arms']
    p = ARMS_R2 / (arm + '.json')
    if C.sha256_file(p) != reg[arm]['sha256']:
        raise SystemExit('arm file changed: ' + arm)
    return p, reg[arm]['sha256']


# ================================================================================================ P0-18
def live_from_cfg():
    """signal_live_phases (cfg.network.signals order) and meter names from the C1G configure of V-A v3c3-s31 T=900 on
    PT2 (the same run P0-14 (a) uses)."""
    tree, _man = tree_of_patch_r2()
    st = [s for s in STATES['probe_decisions_T900'] if s['kind'] == 'va' and RUNS[s['run']]['label'] == 'v3c3-s31'][0]
    p, sha = arm_file('c1g')
    rec = cfg_run(state_tag(st, 'c1g'), st['run'], st['T'], p, tree, OUT / 'cfgruns', tuning_sha=sha)
    if not rec.get('ok'):
        raise SystemExit('C1G configure failed: %s' % (rec.get('error') or rec.get('collect_error')))
    return rec['signal_live_phases'], rec['meter_names'], rec['signals_order']


def p0_18_child(tree, ev_path, live_path, out_path):
    """Inside a python whose sys.path holds PT2 (p0_18 starts it): runtime core on every occ state + recount."""
    sys.path.insert(0, str(tree))
    from evaluation.controllers import c1_port as P
    from evaluation.controllers import obs150_contract as OC
    ev = json.loads(Path(ev_path).read_text(encoding='utf-8'))
    ix = P.guard_index(ev)
    params = json.loads(Path(live_path).read_text(encoding='utf-8'))
    live = {k: tuple(v) for k, v in params['live'].items()}
    meters = tuple(params['meters'])
    occ = json.loads(OCC_JSON.read_text(encoding='utf-8'))
    seg_ids = occ['segment_ids']
    pairs = params['pairs']                                        # [[occ key, run, T, state path]]
    raw_counts = {}
    for run_label, rows in occ['raw_counts'].items():
        for row in rows:
            raw_counts['%s:%d' % (run_label, row[0])] = row[1:]
    out = {'states': [], 'n': 0}
    for occ_key, run, T, path in pairs:
        st = json.loads(Path(path).read_text(encoding='utf-8-sig'))
        from evaluation.controllers.projection_support import complete_records
        records = complete_records(st)
        cur = st['obs150']['frames']['current']
        fpath = Path(path).parent / Path(*cur['path'].split('/'))
        frame = OC.load_frame(fpath, cur['sha256'], st['sim_sec'])
        lengths = {int(r[0]): float(r[5]) for r in frame['vehicles']}
        core = P.storage_capacity_core(records, lengths, ix, live, meters, capacity_threshold=1.0)
        rc = RC.recount(records, lengths, ev, live, meters, 1.0)
        counts = core['detail']['counts']
        occ_c = raw_counts[occ_key]
        a_diff, a_explained = [], []
        pos_by = defaultdict(list)
        for r in records:
            pos_by[str(r['link_no']), int(r['lane_no'])].append(float(r['position_m']))
        for i, sid in enumerate(seg_ids):
            if sid.startswith('D5'):
                continue
            got = counts.get(sid, 0)
            if got != occ_c[i]:
                s = ix['seg'][sid]
                near = [p for p in pos_by[str(s['link']), int(s['lane'])]
                        if abs(p - s['start_m']) <= 1e-9 or abs(p - s['end_m']) <= 1e-9]
                (a_explained if near and abs(got - occ_c[i]) <= len(near) else a_diff).append([sid, got, occ_c[i]])
        b_diff = [sid for sid, s in ix['seg'].items() if s['kind'] in ('L', 'R')
                  and counts.get(sid, 0) != rc['counts'].get(sid, 0)]
        c_diff = RC.compare(core, rc)
        out['states'].append({'run': run, 'T': T, 'a_diff': a_diff, 'a_explained': a_explained, 'b_diff': b_diff,
                              'c_diff': c_diff, 'full_n': len(core['full']),
                              'spill_ids': core['detail']['spill']})
        out['n'] += 1
    with open(out_path, 'x', encoding='utf-8') as f:
        json.dump(out, f)


def p0_18_pairs():
    """occ.json state keys <-> state files by run name (c1_states /runs) + state sha16 + T (never by the occ label)."""
    if not short_sha_ok(OCC_JSON, OCC_SHA):
        raise SystemExit('occ.json differs from its pin')
    occ = json.loads(OCC_JSON.read_text(encoding='utf-8'))
    by = {}
    for key, s16 in occ['state_sha16'].items():
        T = int(key.rsplit(':', 1)[1])
        by.setdefault((s16, T), []).append(key)
    pairs, seen = [], set()
    for r in STATES['runs']:
        if r['kind'] not in ('va', 'b'):
            continue
        dec = decisions_dir(r['name'])
        for p in sorted(dec.glob('state_*.json')):
            T = int(p.stem.split('_')[1])
            if T < 900:
                continue
            s16 = C.sha256_file(p)[:16]
            keys = by.get((s16, T), [])
            if len(keys) != 1:
                raise SystemExit('occ pairing failed: %s T=%d (%d)' % (r['name'], T, len(keys)))
            pairs.append([keys[0], r['name'], T, str(p)])
            seen.add(keys[0])
    if seen != set(occ['state_sha16']) or len(pairs) != 330:
        raise SystemExit('occ pairing incomplete: %d paired, %d in occ' % (len(seen), len(occ['state_sha16'])))
    return pairs


def p0_18():
    tree, man = tree_of_patch_r2()
    d = OUT / 'p0_18'
    d.mkdir(parents=True, exist_ok=True)
    live, meters, order = live_from_cfg()
    pairs = p0_18_pairs()
    params = {'live': {o: live[o] for o in order}, 'meters': meters, 'pairs': pairs}
    pfile = d / ('params_%d_%d.json' % (os.getpid(), time.time_ns()))
    C.write_new(pfile, json.dumps(params))
    outf = d / 'states.json'
    if not outf.is_file():
        C.lock_acquire('c1 P0-18 runtime core x 330 states', LOG)
        try:
            code = ('import sys; sys.path.insert(0, %r); import c1_p0_c12 as M; M.p0_18_child(%r, %r, %r, %r)'
                    % (str(HERE), str(tree), str(P0DIR / EV_NAME), str(pfile), str(outf)))
            rc, sec, _ = C.run_capture([C.PY, '-B', '-c', code], d / 'child.txt', child_env_tree(), cwd=tree)
            LOG('P0_18 child exit=%s sec=%.0f' % (rc, sec))
        finally:
            C.lock_release(LOG)
    res = C.read_json(outf) or {}
    rows = res.get('states') or []
    checks = {'states_330': len(rows) == 330,
              'a_occ_counts_equal_or_boundary': all(not r['a_diff'] for r in rows),
              'b_L_R_counts_equal_recount': all(not r['b_diff'] for r in rows),
              'c_runtime_equals_recount': all(not r['c_diff'] for r in rows)}
    res2 = {'step': 'P0-18', 'tree': tree.name, 'patch_sha256': man['patch_sha256'],
            'S17': C.sha256_file(P0DIR / EV_NAME), 'states_sha256': C.sha256_file(outf) if outf.is_file() else None,
            'a_explained_boundary_states': sum(1 for r in rows if r['a_explained']),
            'a_diff_states': [[r['run'], r['T'], r['a_diff'][:5]] for r in rows if r['a_diff']][:20],
            'c_diff_states': [[r['run'], r['T'], r['c_diff']] for r in rows if r['c_diff']][:20],
            'checks': checks}
    res2['verdict'] = 'PASS' if all(checks.values()) else 'STOP'
    result_write('p0_18', res2)


# ================================================================================================ P0-14
P0_3_ARMS = ('off', 'omega', 'm', 'h', 'c1')
TOKEN_ARMS = ('off', 'omega', 'h', 'm', 'm_cap1', 'm_noheld', 'c1', 'c1m', 'azg', 'srg', 'hr', 'mlc')


def p0_14():
    tree, man = tree_of_patch_r2()
    base = OUT / 'cfgruns'
    old_values = json.loads((C.C1D / 'C1_VALUES.json').read_text(encoding='utf-8'))
    old_reg = json.loads((C.TOOLS / 'arms' / 'ARMS.json').read_text(encoding='utf-8'))['arms']
    C.lock_acquire('c1 P0-14 configure runs on PT2', LOG)
    try:
        recs = {}
        for st in STATES['probe_decisions_T900']:
            ctl = 'wu-link' if st['kind'] == 'robs' else None
            for arm in P0_3_ARMS + ('c1g',):
                if arm == 'c1g':
                    p, sha = arm_file('c1g')
                else:
                    p, sha = C.TOOLS / 'arms' / (arm + '.json'), old_reg[arm]['sha256']
                recs[state_tag(st, arm)] = cfg_run(state_tag(st, arm), st['run'], st['T'], p, tree, base, controller=ctl,
                                                   tuning_sha=sha)
        st0 = STATES['probe_decisions_T900'][0]
        for arm in TOKEN_ARMS:
            if arm in P0_3_ARMS:
                continue
            recs[state_tag(st0, arm)] = cfg_run(state_tag(st0, arm), st0['run'], st0['T'], C.TOOLS / 'arms' / (arm + '.json'),
                                                tree, base, tuning_sha=old_reg[arm]['sha256'])
    finally:
        C.lock_release(LOG)
    res = {'step': 'P0-14', 'tree': tree.name, 'states': {}, 'checks': {}}
    a_ok, live_sets, meter_sets, b_ok = True, set(), set(), True
    for st in STATES['probe_decisions_T900']:
        old_key = '%s_t%06d' % (st['run'].replace('sdmpc31_', ''), st['T'])
        r1, rg = recs[state_tag(st, 'c1')], recs[state_tag(st, 'c1g')]
        row = {'ok': [bool(r1.get('ok')), bool(rg.get('ok'))]}
        if r1.get('ok') and rg.get('ok'):
            dk7 = k7_diff(leaves_of(base / state_tag(st, 'c1')), leaves_of(base / state_tag(st, 'c1g')))
            row['diff_c1_c1g_k7'] = dk7
            row['tokens'] = [r1.get('token'), rg.get('token')]
            row['live_phases'] = rg.get('signal_live_phases')
            row['meters'] = rg.get('meter_names')
            g = rg.get('metadata_c1_port_guard') or {}
            row['guard'] = {'full_by_kind': g.get('full_by_kind'), 'signals': g.get('signals'),
                            'meters_triggered': {m: v.get('triggered') for m, v in (g.get('meters') or {}).items()},
                            'minus_one_lanes': g.get('minus_one_lanes'), 'equal_weights_zeroed': g.get('equal_weights_zeroed')}
            live_sets.add(json.dumps(rg.get('signal_live_phases'), sort_keys=False))
            meter_sets.add(json.dumps(rg.get('meter_names')))
            a_ok &= dk7 == ['c1_port/storage_capacity_guard', 'c1_storage_capacity_guard'] and \
                row['tokens'] == [T_C1, T_C1] and bool(g)
            # (b) P0-3 again on PT2
            lv = {arm: leaves_of(base / state_tag(st, arm)) for arm in P0_3_ARMS}
            E = {arm: leaf_diff(lv['off'], lv[arm]) for arm in P0_3_ARMS if arm != 'off'}
            row['p0_3_equal'] = E == old_values['p0_3'][old_key]
            b_ok &= row['p0_3_equal']
        else:
            a_ok = False
            b_ok = False
            row['errors'] = [(r1 or {}).get('error'), (rg or {}).get('error')]
        res['states'][old_key] = row
    toks = {arm: (recs.get(state_tag(STATES['probe_decisions_T900'][0], arm)) or {}).get('token') for arm in TOKEN_ARMS}
    b_tok = toks == old_values['p0_6']['tokens']
    res['tokens_p0_6'] = toks
    res['checks'] = {'a_diff_tokens_guard_5_states': a_ok, 'a_live_phases_meters_same_5_states': len(live_sets) == 1
                     and len(meter_sets) == 1, 'b_p0_3_equal_C1_VALUES': b_ok, 'b_p0_6_tokens_equal': b_tok,
                     'c_normaliser_new_roots': p0_14_c()}
    res['live_phases'] = json.loads(next(iter(live_sets))) if len(live_sets) == 1 else None
    res['meters'] = json.loads(next(iter(meter_sets))) if len(meter_sets) == 1 else None
    res['verdict'] = 'PASS' if all(res['checks'].values()) else 'STOP'
    result_write('p0_14', res)


def p0_14_c():
    sys.path.insert(0, str(C.TOOLS))
    import c1_p0 as OLD          # noqa: E402  (the amendment C1 P0-13 comparator rules N_RULES, unchanged)
    cases = [('D:/VISSIM-merge/k8_gate_trees/c1/trees/probe_0123abcd/evaluation/controllers/c1_port.py',
              '<root>/evaluation/controllers/c1_port.py'),
             ('D:/VISSIM-merge/k8_gate_trees/c1/out/probe_r2/dec/t000900_robss31_c1g/replay/action_000900.json',
              '<bundle>/replay/action_000900.json'),
             ('D:\\VISSIM-merge\\k8_gate_trees\\c1\\out\\probe_r2\\d98\\t001500_robss31_omega\\bundle\\state_001500.json',
              '<bundle>/bundle/state_001500.json'),
             ('D:/VISSIM-merge/k8_gate_trees/c1/out/p0_c12/cfgruns/t000900_v3c3k92vas31_c1g/bundle/state_000900.json',
              '<bundle>/bundle/state_000900.json'),
             ('D:/VISSIM-merge/k8_gate_trees/c1/trees/c1_g_0123abcd_null/diagnostics/sdmpc_n31_20260924/c1/evidence/x',
              '<root>/diagnostics/sdmpc_n31_20260924/c1/evidence/x')]
    return all(OLD.n_norm(a) == b for a, b in cases)


# ================================================================================================ P0-15
def judging_states():
    """Z1 (f_blind) and Z2: J-1 leaf job states (gates_k91t.json judged items, the sa_gates.py map of the c20aff1d
    tree) and J-2 (22 v3c3-s47 states).  Only names and T values are read (no gate value)."""
    gates = Path(r'D:/VISSIM-merge/k8_gates_out_v4/sa/gates/gates_k91t.json')
    if C.sha256_file(gates) != '4e59f61d6d1b18ad588e95eaf6f215f44f6c66c981921735073d91f1c6c59b9f':
        raise SystemExit('gates_k91t.json differs')
    doc = json.loads(gates.read_text(encoding='utf-8'))
    it = doc['gates']['G-EB-14']['items']['i_init']
    sa_common = C.git_show('diagnostics/sdmpc_n31_20260924/k8_gates/sa/sa_common.py').decode('utf-8')
    m = re.search(r'^ROBS61_T = \(1,\) \+ tuple\(range\(150, 9001, 150\)\)', sa_common, re.M)
    if not m or it.get('pass_') is None:
        raise SystemExit('ROBS61_T / G-EB-14 i_init form differs')
    robs61 = (1,) + tuple(range(150, 9001, 150))
    seeds = set(int(s) for s in it['judged_seeds'])
    z = set()
    for r in STATES['runs']:
        if r['kind'] == 'robs' and int(r['seed_from_provenance']) in seeds:
            for T in robs61:
                z.add((r['name'], T))
    for st in STATES['f_blind']:
        z.add((st['run'], int(st['T'])))
    return z, {'G-EB-14 i_init judged_seeds': sorted(seeds), 'ROBS61_T': [robs61[0], robs61[1], robs61[-1], len(robs61)]}


def p0_15():
    z, why = judging_states()
    order = ('K0', 'K1', 'K2', 'K3', 'K4', 'K5')
    res = {'step': 'P0-15', 'z_rule': why, 'runs': {}}
    s_g = []
    skipped = []
    candidates = []
    for name in ('sdmpc31_v3c3_nc_s31', 'sdmpc31_v3c3_nc_s43'):
        run_rec(name)
        for T in range(1050, 8851, 150):
            if (name, T) in z:
                skipped.append([name, T])
            else:
                candidates.append([name, T])
    res['skipped_judging_states'] = skipped
    res['candidates_outside_z'] = candidates
    if candidates:
        tree, _man = tree_of_patch_r2()
        live, meters, sig_order = live_from_cfg()
        d = OUT / 'p0_15'
        d.mkdir(parents=True, exist_ok=True)
        params = {'live': {o: live[o] for o in sig_order}, 'meters': meters,
                  'states': [[n, T, str(decisions_dir(n) / ('state_%06d.json' % T))] for n, T in candidates]}
        pfile = d / ('params_%d_%d.json' % (os.getpid(), time.time_ns()))
        C.write_new(pfile, json.dumps(params))
        outf = d / 'observations.json'
        if not outf.is_file():
            C.lock_acquire('c1 P0-15 S_G observation', LOG)
            try:
                code = ('import sys; sys.path.insert(0, %r); import c1_p0_c12 as M; M.p0_15_child(%r, %r, %r, %r)'
                        % (str(HERE), str(tree), str(P0DIR / EV_NAME), str(pfile), str(outf)))
                C.run_capture([C.PY, '-B', '-c', code], d / 'child.txt', child_env_tree(), cwd=tree)
            finally:
                C.lock_release(LOG)
        obs = C.read_json(outf) or {}
        for name in ('sdmpc31_v3c3_nc_s31', 'sdmpc31_v3c3_nc_s43'):
            rows = [o for o in obs.get('states', []) if o['run'] == name]
            taken, cats = set(), {}
            for k in order:
                t = next((o['T'] for o in rows if o['T'] not in taken and o['cat'][k]), None)
                cats[k] = t
                if t is not None:
                    taken.add(t)
            k1 = next((o['T'] for o in rows if o['cat']['K1']), None)
            t6 = None if k1 is None else k1 - 150
            cats['K6'] = t6 if (t6 is not None and t6 >= 1050 and (name, t6) not in z and t6 not in taken) else None
            if cats['K6'] is not None:
                taken.add(t6)
            res['runs'][name] = cats
            for k, t in cats.items():
                if t is not None:
                    s_g.append({'run': name, 'kind': 'robs', 'T': t, 'category': k})
    else:
        for name in ('sdmpc31_v3c3_nc_s31', 'sdmpc31_v3c3_nc_s43'):
            res['runs'][name] = {k: None for k in order + ('K6',)}
    res['s_g'] = s_g
    res['checks'] = {'s_g_nonempty': bool(s_g)}
    res['verdict'] = 'PASS' if s_g else 'ASK (S-C1-20: S_G empty)'
    states_doc = {'schema': 'c1g-states/v1', 's_g': s_g,
                  'categories': {n: res['runs'][n] for n in sorted(res['runs'])},
                  'skipped_judging_states': skipped, 'c1g0_state': {'run': 'sdmpc31_v3c3_nc_s31', 'kind': 'robs', 'T': 900},
                  'seed_rule': STATES['seed_rule']}
    res['c1g_states_payload_sha256'] = C.sha256_bytes(C.data(states_doc))
    C.write_json(OUT / 'p0_15' / 'c1g_states_candidate.json', states_doc)
    result_write('p0_15', res)


def p0_15_child(tree, ev_path, params_path, out_path):
    sys.path.insert(0, str(tree))
    from evaluation.controllers import c1_port as P
    from evaluation.controllers import obs150_contract as OC
    from evaluation.controllers.projection_support import complete_records
    ix = P.guard_index(json.loads(Path(ev_path).read_text(encoding='utf-8')))
    params = json.loads(Path(params_path).read_text(encoding='utf-8'))
    live = {k: tuple(v) for k, v in params['live'].items()}
    meters = tuple(params['meters'])
    out = {'states': []}
    k2_links = {'71', '10641', '126', '10643'}
    for name, T, path in params['states']:
        C.blind_guard(name)
        st = json.loads(Path(path).read_text(encoding='utf-8-sig'))
        records = complete_records(st)
        cur = st['obs150']['frames']['current']
        frame = OC.load_frame(Path(path).parent / Path(*cur['path'].split('/')), cur['sha256'], st['sim_sec'])
        core = P.storage_capacity_core(records, {int(r[0]): float(r[5]) for r in frame['vehicles']}, ix, live, meters)
        w = core['signals']
        sc = core['detail']['scores']
        k2 = False
        for ph in ('SC1004_p3', 'SC1004_p4'):
            if w.get('SC1004', {}).get(ph, 0.) > 0:
                k2 |= any(score > 0 and str(ix['seg'][sid]['link']) in k2_links for sid, score in sc.get(ph, []))
        cat = {'K0': all(v == 0. for s in w.values() for v in s.values()) and not any(
                   m['triggered'] for m in core['meters'].values()),
               'K1': w.get('SC1001', {}).get('SC1001_p3', 0.) > 0,
               'K2': k2,
               'K3': any(core['meters'][m]['triggered'] for m in ('RM_C10639', 'RM_C10681', 'RM_C10490', 'RM_C10484')),
               'K4': any(sum(1 for v in s.values() if v > 0) >= 2 for s in w.values()),
               'K5': bool(core['minus_one_lanes'])}
        out['states'].append({'run': name, 'T': T, 'cat': cat})
    with open(out_path, 'x', encoding='utf-8') as f:
        json.dump(out, f)


# ================================================================================================ values
def values():
    path = C.C1D / 'C1_VALUES_C1_2.json'
    if path.exists():
        raise SystemExit('C1_VALUES_C1_2.json exists (never rewritten)')
    r = {s: C.read_json(OUT / s / 'result.json') for s in ('p0_14', 'p0_15', 'p0_17', 'p0_18')}
    doc = {'schema': 'c1-values-c1-2/v1', 'amendment_c1_2_sha256': AMEND2_SHA,
           'p0_17': {'segments_sha256': (r['p0_17'] or {}).get('S17'), 'null_sha256': (r['p0_17'] or {}).get('S17_null'),
                     'counts': ((r['p0_17'] or {}).get('report') or {}).get('h_counts')},
           'p0_18': {'checks': (r['p0_18'] or {}).get('checks')},
           'p0_14': {'live_phases': (r['p0_14'] or {}).get('live_phases'), 'meters': (r['p0_14'] or {}).get('meters'),
                     'states': {k: v.get('guard') for k, v in ((r['p0_14'] or {}).get('states') or {}).items()}},
           'p0_15': {'s_g': (r['p0_15'] or {}).get('s_g'), 'c1g_states_sha256': None},
           'verdicts': {k: (v or {}).get('verdict') for k, v in r.items()},
           'result_sha256': {k: (C.sha256_file(OUT / k / 'result.json') if (OUT / k / 'result.json').is_file() else None)
                             for k in r}}
    C.write_new(path, json.dumps(doc, indent=1, ensure_ascii=False, default=str) + '\n')
    LOG('C1_VALUES_C1_2 written sha256=%s' % C.sha256_file(path))


# ================================================================================================ main
if __name__ == '__main__':
    C.set_below_normal()
    step = sys.argv[1] if len(sys.argv) > 1 else ''
    LOG('START %s argv=%s' % (step, sys.argv[1:]))
    C.require_space(LOG)
    if step == 'cfgrun':
        a = sys.argv[2:]
        tree = C.TC1 / 'trees' / a[a.index('--tree') + 1]
        ctl = a[a.index('--controller') + 1] if '--controller' in a else None
        base = Path(a[a.index('--out') + 1]) if '--out' in a else OUT / 'dev'
        C.lock_acquire('c1 C1-2 cfgrun %s' % a[0], LOG)
        try:
            rec = cfg_run(a[0], a[1], int(a[2]), Path(a[3]), tree, base, controller=ctl)
        finally:
            C.lock_release(LOG)
        print('CFGRUN ok=%s error=%s' % (rec.get('ok'), (rec.get('error') or rec.get('collect_error') or '')[-400:]))
    elif step in ('p0_17', 'arms', 'p0_18', 'p0_14', 'p0_15', 'values'):
        globals()[step]()
    else:
        raise SystemExit(__doc__)
    LOG('END %s' % step)
