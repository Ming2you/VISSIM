"""Amendment 30 declare-time checks without data (scratch tool in KB/a30decl, never committed).

    python -B dry_a30.py static  --tag T    py_compile, LF, function-source equality with the base files, the diff
    python -B dry_a30.py synth   --tag T    the new F judge parts on synthetic inputs (cases S1-S8) + mutants M1-M7
    python -B dry_a30.py drive   --tag T    the driver's read-only commands: check30 --mode decl, seal30 --dry-run,
                                            the persistence argv; and the chain plan text

Outputs: KB/a30decl/dry/<tag>/dry_a30_<step>.json (LF, sorted keys).  Nothing here reads a k92t F value, a sealed log,
or a v3c3-s47 result: synth builds its own inputs under KB/a30decl/dry/<tag>/synth; drive only runs the read-only
driver commands (names, sizes, exit codes, sha).  The synthetic judge imports k92_gates from a 1.7 MB copy of the
K9-2-5 k8_gates folder (TK/a30decl/tc, made from TK/a27/k925 by this tool when absent)."""
import ast
import difflib
import importlib.util
import json
import os
import random
import shutil
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
KB = HERE.parent
BASE_DRIVER = HERE / 'base' / 'k92t.py'
BASE_JUDGE = HERE / 'base' / 'k92t_judge.py'
NEW_DRIVER = HERE / 'k92t30.py'
NEW_JUDGE = HERE / 'k92t30_judge.py'
BASE_SHA = {'k92t.py': 'b07ffb56789c30c8ef2f60f098ae7212fec52eec8a307b959bf26c44c6f02bec',
            'k92t_judge.py': 'eb4c113a6b7194cdf00d193d5faf07b426aae61a49ff84ae442bcf29b59fb28e'}
K925 = Path(r'D:/VISSIM-merge/k8_gate_trees/k92b1/a27/k925')
TC = Path(r'D:/VISSIM-merge/k8_gate_trees/k92b1/a30decl/tc')
GATES_REL = 'diagnostics/sdmpc_n31_20260924/k8_gates'
PY = sys.executable
# declared changes (amendment 30 section 3.3)
DRIVER_CHANGED = {'log_md', 'stop', 'finish', 'require_prev', 'stage_jb', 'main'}
DRIVER_REMOVED = {'stage_pre', 'stage_tree', 'stage_start', 'child', 'run_child', 'job_item', 'prep_root',
                  'stage_prep', 'stage_j0', 'stage_ja', 'stage_f', 'stage_post', 'chain', 'status'}
DRIVER_NEW = {'wjson', 'a30_sha', 'pins_check', 'inventory', 'inv_diff', 'f_labels', 'f_inputs_check',
              'persist_argv', 'stage_check30', 'stage_seal30', 'stage_f30', 'stage_post30', 'chain30', 'status30'}
# the amendment-30 text values the synthetic inputs are built from (never from the module under test)
F_PRIMARY = (1050, 1650, 1950, 2400, 3300, 3750, 3900, 4650, 5100, 5550, 6000, 6150, 6450, 6600, 6900, 7050, 7350,
             7500, 7800, 7950, 8250, 8400)
F_SECOND = {31: (1500, 2850, 3900, 5250, 6000, 6600, 7500, 8250), 43: (1050, 3300, 4800, 5550, 6450, 7050, 7800, 8400)}
INPX_RAW = {47: '1895ca30542cd50542a9376d5e3c77ff184d65a009d97dbe55a65f0b31bbced0',
            31: '3de889f0257d998bed50611f798ea388bcf69396dbc40e5726b1e88ebdd31c2e',
            43: '51478c397b3a2570fc2254a9fa8120a2415304942589f5fb5c2eb1b6858f2dda'}
PERSIST_DIR = 'f_persist30'
VR_STATES_TEXT = [T - 450 for T in F_PRIMARY if T - 450 >= 900]
LABEL_TEXT = 'not measurable (T_FROM=900)'


def lab_text(seed, T):
    return 'TL3_%d%s_SAF_OBS_H3' % (T, '' if seed == 31 else '_s%d' % seed)
JUDGE_CHANGED = {'cmd_f', 'main'}
JUDGE_NEW = {'job_counts', 'cmd_fcount', 'persistence_report'}


def sha(p):
    import hashlib
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def wjson(p, obj):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, 'w', encoding='utf-8', newline='\n') as f:
        f.write(json.dumps(obj, indent=1, sort_keys=True, default=str, ensure_ascii=False) + '\n')


def lf_text(p):
    return Path(p).read_bytes().replace(b'\r\n', b'\n').decode('utf-8')


def funcs(src):
    t = ast.parse(src)
    return {n.name: ast.get_source_segment(src, n) for n in t.body if isinstance(n, ast.FunctionDef)}


def assigns(src):
    t = ast.parse(src)
    out = {}
    for n in t.body:
        if isinstance(n, ast.Assign):
            for tg in n.targets:
                if isinstance(tg, ast.Name):
                    out[tg.id] = ast.get_source_segment(src, n)
    return out


# ------------------------------------------------------------------------------------------------ static
def cmd_static(tag):
    res = {'when': time.strftime('%Y-%m-%dT%H:%M:%S')}
    res['base_sha'] = {n: sha(HERE / 'base' / n) == s for n, s in BASE_SHA.items()}
    res['base_equals_pinned'] = {'k92t.py': sha(KB / 'k92t' / 'k92t.py') == BASE_SHA['k92t.py'],
                                 'k92t_judge.py': sha(KB / 'k92t' / 'k92t_judge.py') == BASE_SHA['k92t_judge.py']}
    comp = {}
    for p in (NEW_DRIVER, NEW_JUDGE, Path(__file__)):
        try:
            compile(p.read_text(encoding='utf-8'), str(p), 'exec')
            comp[p.name] = True
        except SyntaxError as exc:
            comp[p.name] = repr(exc)
    res['compile'] = comp
    res['cr_bytes'] = {p.name: p.read_bytes().count(b'\r') for p in (NEW_DRIVER, NEW_JUDGE, Path(__file__))}
    bd, nd = lf_text(BASE_DRIVER), lf_text(NEW_DRIVER)
    bj, nj = lf_text(BASE_JUDGE), lf_text(NEW_JUDGE)
    fb, fn = funcs(bd), funcs(nd)
    same = sorted(k for k in fb if k in fn and fb[k] == fn[k])
    changed = sorted(k for k in fb if k in fn and fb[k] != fn[k])
    removed = sorted(k for k in fb if k not in fn)
    new = sorted(k for k in fn if k not in fb)
    jb_token = fb['stage_jb'].replace("str(HERE / 'k92t_judge.py')", 'str(JUDGE)') == fn['stage_jb']
    res['driver'] = {'same': same, 'changed': changed, 'removed': removed, 'new': new,
                     'changed_declared': set(changed) == DRIVER_CHANGED,
                     'removed_declared': set(removed) == DRIVER_REMOVED,
                     'new_declared': set(new) == DRIVER_NEW,
                     'stage_jb_only_judge_path': jb_token}
    ab, an = assigns(bd), assigns(nd)
    res['driver_constants'] = {'removed': sorted(set(ab) - set(an)), 'added': sorted(set(an) - set(ab)),
                               'changed': sorted(k for k in set(ab) & set(an) if ab[k] != an[k])}
    gb, gn = funcs(bj), funcs(nj)
    jsame = sorted(k for k in gb if k in gn and gb[k] == gn[k])
    jchanged = sorted(k for k in gb if k in gn and gb[k] != gn[k])
    jremoved = sorted(k for k in gb if k not in gn)
    jnew = sorted(k for k in gn if k not in gb)
    res['judge'] = {'same': jsame, 'changed': jchanged, 'removed': jremoved, 'new': jnew,
                    'changed_declared': set(jchanged) == JUDGE_CHANGED, 'removed_none': not jremoved,
                    'new_declared': set(jnew) == JUDGE_NEW}
    jab, jan = assigns(bj), assigns(nj)
    res['judge_constants'] = {'removed': sorted(set(jab) - set(jan)), 'added': sorted(set(jan) - set(jab)),
                              'changed': sorted(k for k in set(jab) & set(jan) if jab[k] != jan[k])}
    # the unified diff (base bytes CRLF -> LF; new files LF)
    d = []
    for (a, b, na, nb) in ((bd, nd, 'base/k92t.py', 'k92t30.py'), (bj, nj, 'base/k92t_judge.py', 'k92t30_judge.py')):
        d += difflib.unified_diff(a.splitlines(keepends=True), b.splitlines(keepends=True), fromfile=na, tofile=nb,
                                  n=3)
    diff = ''.join(d)
    out = HERE / 'A30_DRIVER.diff'
    with open(out, 'w', encoding='utf-8', newline='\n') as f:
        f.write(diff)
    res['diff'] = {'path': str(out), 'sha256': sha(out), 'lines': diff.count('\n')}
    res['ok'] = (all(res['base_sha'].values()) and all(res['base_equals_pinned'].values())
                 and all(v is True for v in comp.values()) and not any(res['cr_bytes'].values())
                 and res['driver']['changed_declared'] and res['driver']['removed_declared']
                 and res['driver']['new_declared'] and jb_token and res['judge']['changed_declared']
                 and res['judge']['removed_none'] and res['judge']['new_declared'])
    wjson(HERE / 'dry' / tag / 'dry_a30_static.json', res)
    print('DRY_A30 static ok=%s' % res['ok'])
    return 0 if res['ok'] else 3


# ------------------------------------------------------------------------------------------------ synth
def load_judge(path, name):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def ensure_tc():
    src = K925 / GATES_REL
    dst = TC / GATES_REL
    if not dst.is_dir():
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns('__pycache__', '__tangentcache__'))
    bad = []
    for base, dirs, names in os.walk(src):
        dirs[:] = [x for x in dirs if x not in ('__pycache__', '__tangentcache__')]
        for n in names:
            a = os.path.join(base, n)
            b = os.path.join(dst, os.path.relpath(a, src))
            if not os.path.isfile(b) or sha(a) != sha(b):
                bad.append(os.path.relpath(a, src))
    return {'tc': str(TC), 'equal_to_k925': not bad, 'bad': bad[:10]}


def build(root, J, rng, case):
    """Synthetic OUTK under root for case (no real value).  Returns the expected persistence numbers."""
    if root.exists():
        shutil.rmtree(root)
    lab = F_PRIMARY

    def wj(p, obj):
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(obj), encoding='utf-8')
    vref = {'schema': 'synthetic', 'seeds': {}}
    ident = {'raw_sha256': INPX_RAW[47],
             'normalized_sha256': 'b7f05dcd07042fce8a439529853429a642f4de7b998c96ede51ce8c2d1230eb3'}
    states = {}
    for T in lab:
        states[str(T)] = {'m1_T150': rng.randint(5, 40), 'm1_T450': rng.randint(5, 40), 'm2_T150': rng.randint(50, 90),
                          'm2_T450': rng.randint(150, 250), 'm3_T150': rng.randint(5, 20),
                          'm3_T450': rng.randint(15, 50)}
    vref['seeds']['s47'] = {'network_identity': ident, 'states': states}
    for s in (31, 43):
        ident_s = {'raw_sha256': INPX_RAW[s], 'normalized_sha256': ident['normalized_sha256']}
        vref['seeds']['s%d' % s] = {'network_identity': ident_s, 'states': {
            str(T): {k: rng.randint(5, 200) for k in ('m1_T150', 'm1_T450', 'm2_T150', 'm2_T450', 'm3_T150',
                                                       'm3_T450')} for T in F_SECOND[s]}}
    wj(root / 'f_vref' / 'sa' / 'k92_vissim_ref.json', vref)
    for arm, off in (('f_off', 3.0), ('f_w', 2.0), ('f_b1', 1.0)):
        for seed, Ts in ((47, lab), (31, F_SECOND[31]), (43, F_SECOND[43])):
            for T in Ts:
                d = root / arm / 'sa' / 'jobs' / 'k92t' / lab_text(seed, T)
                vs = (vref['seeds']['s%d' % seed]['states'][str(T)])
                hz = {'m1_chain_T450': vs['m1_T450'] + off, 'm2_w_dep_T450': vs['m2_T450'] - off,
                      'm3_l_dep_T450': vs['m3_T450'] + off / 2, 'm1_chain_T150': vs['m1_T150'] + off,
                      'm2_w_dep_T150': vs['m2_T150'] - off, 'm3_l_dep_T150': vs['m3_T150'] + off / 2,
                      'w_capacity_bound_steps': 2, 'w_steps_with_departures': 10, 'outw_veh_h_450': 1.0,
                      'feed4_veh_h_450': 0.5, 'e_out_max_over_220': 0.1, 'w_receiving_limited_steps': 0,
                      'phantom_end_450': 0.0}
                ok = True
                rec = {'horizon': hz, 'errors': []}
                if case == 'S6' and arm == 'f_w' and seed == 47 and T == 3300:
                    ok = False
                if case == 'S7' and arm == 'f_off' and seed == 47 and T == 3300:
                    rec = None
                wj(d / 'summary.json', {'ok': ok})
                if rec is not None:
                    wj(d / 'k92_record.json', rec)
                tag = '%06d' % T + ('' if seed == 31 else '_s%d' % seed)
                wj(root / arm / 'sa' / 'cap' / 'k92t' / 'TL3' / tag / 'SAF' / 'capture.json',
                   {'ok': True, 'metadata': {'k92_hb_seed_binding': 1.0 if arm == 'f_b1' and T == 1050 else 0.0}})
    pst = {}
    for t in VR_STATES_TEXT:
        pst[str(t)] = {'m1_T450': states[str(t)]['m1_T450'] if str(t) in states else rng.randint(5, 40),
                       'm1_T150': 0, 'm2_T450': 0, 'm3_T450': 0}
    pid = dict(ident)
    if case == 'S2':
        pst['600'] = {'m1_T450': 7}
    if case == 'S3':
        del pst['1200']
    if case == 'S4':
        pst['1950'] = {'m1_T450': states['1950']['m1_T450'] + 1}
    if case == 'S5':
        pid = {'raw_sha256': '0' * 64}
    if case == 'S8':
        pst['x1200'] = {'m1_T450': 1}
    wj(root / PERSIST_DIR / 'sa' / 'k92_vissim_ref.json', {'seeds': {'s47': {'network_identity': pid,
                                                                                'states': pst}}})
    # independent expected persistence (written from the amendment text, not from the judge)
    pe = []
    for T in lab:
        if T - 450 < 900:
            continue
        a = (pst.get(str(T - 450)) or {}).get('m1_T450')
        if isinstance(a, int):
            pe.append(a - states[str(T)]['m1_T450'])
    return {'n': len(pe), 'mae': sum(abs(x) for x in pe) / len(pe) if pe else None}


EXPECT = {  # case -> (F verdict, persistence complete, persistence n, fcount verdict)
    'S1': ('PASS', True, 21, 'PASS'),
    'S2': ('PASS', False, 21, 'PASS'),
    'S3': ('PASS', False, 20, 'PASS'),
    'S4': ('PASS', False, 21, 'PASS'),
    'S5': ('PASS', False, 21, 'PASS'),
    'S6': ('PASS', True, 21, 'INCOMPLETE'),
    'S7': ('INCOMPLETE', None, None, 'INCOMPLETE'),
    'S8': ('PASS', False, 21, 'PASS'),
}
MUTANTS = {  # name -> (old text, new text) in the judge; each must make at least one case differ from EXPECT
    'M1': ('PERSIST_MEASURED = tuple(T for T in F_PRIMARY if T - 450 >= T_FROM_U4)',
           'PERSIST_MEASURED = tuple(T for T in F_PRIMARY if T - 450 >= 0)'),
    'M2': ('and len(pe) == len(PERSIST_MEASURED) and all(overlap.values()))',
           'and len(pe) == len(PERSIST_MEASURED))'),
    'M3': ("if (read_json(d / 'summary.json') or {}).get('ok') is True:",
           "if (read_json(d / 'summary.json') or {}).get('ok') is not None:"),
    'M4': ("PERSIST_NAME = 'f_persist30'", "PERSIST_NAME = 'f_persist'"),
    'M5': ('complete = (bool(ident_ok) and not bad_keys and got == sorted(PERSIST_VR_STATES) and not missing',
           'complete = (bool(ident_ok) and not bad_keys and not missing'),
    'M6': ('complete = (bool(ident_ok) and not bad_keys', 'complete = (True and not bad_keys'),
    'M7': ('complete = (bool(ident_ok) and not bad_keys', 'complete = (bool(ident_ok)'),
}


def run_cases(judge_path, tag, name):
    J = load_judge(judge_path, name)
    # a mutant copy lives in dry/<tag>/mutants: point its P0-4 exposure inputs at the real KPA files (read-only)
    J.P0_4_SAMPLES = KB / 'k92_probe_a25' / 'p0' / 'p0_4_samples.json'
    J.P0_4_REVIEW = KB / 'k92_probe_a25' / 'p0' / 'p0_4_exposure_review.json'
    out = {}
    for case in sorted(EXPECT):
        root = HERE / 'dry' / tag / 'synth' / name / case / 'k92t'
        rng = random.Random(30)
        exp = build(root, J, rng, case)
        J.OUTK = root
        dest = root.parent / 'f.json'
        dc = root.parent / 'f_jobs.json'
        J.cmd_f(SimpleNamespace(tree=str(TC), dest=str(dest), label='k92t'))
        J.cmd_fcount(SimpleNamespace(dest=str(dc), label='k92t'))
        r = json.loads(dest.read_text(encoding='utf-8'))
        c = json.loads(dc.read_text(encoding='utf-8'))
        pr = r.get('report_persistence_M1_450') or {}
        got = (r.get('verdict'), pr.get('complete'), pr.get('n'), c.get('verdict'))
        row = {'got': got, 'expect': EXPECT[case], 'equal': list(got) == list(EXPECT[case])}
        if case == 'S1':
            row['label_1050'] = (pr.get('states') or {}).get('1050') == LABEL_TEXT
            row['not_measurable'] = pr.get('not_measurable') == {'1050': LABEL_TEXT}
            row['measured_21'] = pr.get('measured') == [T for T in F_PRIMARY if T != 1050]
            row['mae_independent'] = (exp['mae'] is not None and isinstance(pr.get('mae'), float)
                                      and abs(pr.get('mae') - exp['mae']) < 1e-12)
            row['overlap'] = pr.get('overlap_with_f_vref') == {'n': 15, 'n_equal': 15}
            row['vr_states'] = pr.get('vr_states_declared') == VR_STATES_TEXT
            row['job_counts_all_ok'] = all(g['all_ok'] for a in r['job_counts'].values() for g in a.values())
            row['equal'] = row['equal'] and all(row[k] for k in ('label_1050', 'not_measurable', 'measured_21',
                                                                  'mae_independent', 'overlap', 'vr_states',
                                                                  'job_counts_all_ok'))
        if case == 'S6':
            row['w_s47_count'] = r['job_counts']['W']['s47_primary']['summary_ok_true'] == 21
            row['equal'] = row['equal'] and row['w_s47_count']
        out[case] = row
    return out


def cmd_synth(tag):
    res = {'when': time.strftime('%Y-%m-%dT%H:%M:%S'), 'tc': ensure_tc()}
    os.environ.setdefault('K8G_ROOT', str(TC))
    os.environ['K8G_OUT'] = str(HERE / 'dry' / tag / 'k8g_out')
    res['cases'] = run_cases(NEW_JUDGE, tag, 'cand')
    res['cases_ok'] = all(v['equal'] for v in res['cases'].values())
    base_text = NEW_JUDGE.read_text(encoding='utf-8')
    mut = {}
    for m, (old, new) in sorted(MUTANTS.items()):
        if base_text.count(old) != 1:
            mut[m] = {'applied': False}
            continue
        p = HERE / 'dry' / tag / 'mutants' / ('k92t30_judge_%s.py' % m)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, 'w', encoding='utf-8', newline='\n') as f:
            f.write(base_text.replace(old, new))
        cases = run_cases(p, tag, m)
        mut[m] = {'applied': True, 'caught': not all(v['equal'] for v in cases.values()),
                  'differing_cases': sorted(k for k, v in cases.items() if not v['equal'])}
    res['mutants'] = mut
    res['mutants_ok'] = all(v.get('applied') and v.get('caught') for v in mut.values())
    res['ok'] = res['tc']['equal_to_k925'] and res['cases_ok'] and res['mutants_ok']
    wjson(HERE / 'dry' / tag / 'dry_a30_synth.json', res)
    print('DRY_A30 synth ok=%s cases=%s mutants=%s' % (res['ok'], res['cases_ok'], res['mutants_ok']))
    return 0 if res['ok'] else 3


# ------------------------------------------------------------------------------------------------ drive
def cmd_drive(tag):
    out = HERE / 'dry' / tag
    env = dict(os.environ, PYTHONHASHSEED='0', PYTHONDONTWRITEBYTECODE='1')
    res = {'when': time.strftime('%Y-%m-%dT%H:%M:%S')}
    r1 = subprocess.run([PY, '-B', str(NEW_DRIVER), 'check30', '--mode', 'decl', '--dest',
                         str(out / 'check30_decl.json')], capture_output=True, text=True, env=env)
    res['check30_decl'] = {'rc': r1.returncode, 'stdout_tail': r1.stdout.strip().splitlines()[-1:]}
    c = json.loads((out / 'check30_decl.json').read_text(encoding='utf-8'))
    res['check30_decl']['ok'] = c.get('ok')
    res['check30_decl']['bad'] = [k for k, v in c['checks'].items() if not v]
    r2 = subprocess.run([PY, '-B', str(NEW_DRIVER), 'seal30', '--dry-run', '--dest', str(out / 'seal30_dry.json')],
                        capture_output=True, text=True, env=env)
    s = json.loads((out / 'seal30_dry.json').read_text(encoding='utf-8'))
    res['seal30_dry'] = {'rc': r2.returncode, 'ok': s.get('ok'), 'n': len(s.get('plan') or []),
                         'names': [p['name'] for p in s.get('plan') or []]}
    spec = importlib.util.spec_from_file_location('k92t30_mod', str(NEW_DRIVER))
    D = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(D)
    argv = D.persist_argv()
    states = [int(x) for x in argv[argv.index('--states') + 1].split(':')[1].split(',')]
    J = load_judge(NEW_JUDGE, 'k92t30_judge_mod')
    res['persist'] = {'states': states, 'n': len(states), 'min': min(states),
                      'equal_judge': tuple(states) == J.PERSIST_VR_STATES, 'equal_text': states == VR_STATES_TEXT,
                      'not_measurable': list(D.PERSIST_NOT), 'judge_not': list(J.PERSIST_NOT),
                      'root': argv[argv.index('--out') + 1], 'seed_47_only': argv[argv.index('--states') + 1]
                      .startswith('47:') and argv.count('--states') == 1,
                      'token': argv[-4:]}
    res['chain_order'] = list(D.ORDER)
    res['snaps'] = list(D.SNAPS30)
    res['ok'] = (r1.returncode == 0 and c.get('ok') is True and r2.returncode == 0 and s.get('ok') is True
                 and res['seal30_dry']['n'] == 3 and res['persist']['n'] == 21 and res['persist']['min'] == 1200
                 and res['persist']['equal_judge'] and res['persist']['equal_text']
                 and res['persist']['not_measurable'] == [1050]
                 and res['persist']['judge_not'] == [1050] and res['persist']['seed_47_only'])
    wjson(out / 'dry_a30_drive.json', res)
    print('DRY_A30 drive ok=%s' % res['ok'])
    return 0 if res['ok'] else 3


def main():
    if len(sys.argv) < 4 or sys.argv[2] != '--tag':
        print(__doc__)
        return 2
    return {'static': cmd_static, 'synth': cmd_synth, 'drive': cmd_drive}[sys.argv[1]](sys.argv[3])


if __name__ == '__main__':
    raise SystemExit(main())
