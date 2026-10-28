r"""R2c build (D-K9-79): prepared folders s31_v3c3rm10681 / s41_v3c3rm10681 (rule ALINEA on RM_C10681 only).

Recipe (settings only; no code change):
  1. Copy D:\VISSIM_runs\20261001_v3c3\s<S>_v3c3rm\prepared as it stood when that arm was launched
     (2026-10-01 19:11 KST).  The three items the rm run itself created inside prepared\network
     (baseline_s<S>_v3c3rm.err, baseline_s<S>_v3c3rm_001.err, baseline_s<S>_v3c3rm.results\1.db) are left out.
  2. The network file is copied byte for byte and renamed baseline_s<S>_v3c3rm10681.inpx (fast_nc_run.ps1 finds
     its own VISSIM by the network file name in the window title; output files take this stem).
  3. rule_policy.json: "meters" reduced to {"RM_C10681": <the same entry>}.  Every other key is unchanged
     (canonical JSON round trip: indent 2, CRLF, utf-8 = the exact bytes of the rm file, checked).
     fast_fixed_profile.rule_step loops over cfg['meters'] only, so the other seven meters get no COM write at
     all and stay native OFF (their SCs have no signal program), as in NC3.
  4. prepared.json: the prepared-folder paths (key 'network' and the 53 snapshot_sha256 keys) point to the new
     folder, and the rule_policy.json pin is updated.  Nothing else changes.
No file under D:\VISSIM-merge is written; sim3 modules are imported read-only (python -B, no bytecode).
VISSIM / cscript are never started: fast_nc_run.ps1 is called only without -Execute (guarded).
Usage: python -B build_r2c.py <build|verify|dryrun|launchlines|copy|all> [--rehearse]
  --rehearse: same phases into <scratch>/r2c_n/rehearsal (no launch lines, no D: copy)."""
import argparse
import copy
import ctypes
import datetime
import hashlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import time
from ctypes import wintypes
from pathlib import Path

sys.dont_write_bytecode = True

SEEDS = (31, 41)
KEEP = 'RM_C10681'
ROOT = Path(r'D:\VISSIM_runs\20261001_v3c3')
SIM3 = Path(r'D:\VISSIM-merge\sim3')
SIM3D = SIM3 / 'diagnostics'
FFP = SIM3D / 'fast_fixed_profile.py'
FNP = SIM3D / 'fast_nc_prepare.py'
FFPV = SIM3D / 'fast_fixed_profile_verify.py'
RUN_PS1 = SIM3D / 'fast_nc_run.ps1'
RUNNER_VBS = SIM3D / 'fast_nc_runner.vbs'
DIAG = SIM3 / 'evaluation' / 'controllers' / 'diagnostic_profile.py'
RM_BUILD_RECEIPT = ROOT / 'rm_build' / 'v3c3rm_build_receipt.json'
RM_WMI_LINES = ROOT / 'wmi_launch_lines_rm.txt'
SRC23_DLL_ERR = Path(r'D:\VISSIM_runs\20260922_fw080_urban090_controls\rules\prepared_rm\network\VISSIG_Controller.dll.err')
RT_PYTHON = r'C:\Users\TRLAB\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
EXPECTED_SHA = {  # rm arm networks (= rm build receipt) and the ALINEA module at the rm launch (O1 §2)
    'net31': '046303541667838f30045a06d230fb5b31944a18db483770539dfcc873176f0d',
    'net41': 'e4953eaf8c8f983f28b9a14c684075757ddd45e180e63f2235dc9db8b4ed7524',
    str(DIAG): '389d81c8b06c6993b4e6028d637a3bb08b8ac0b698c65fab049f5762bdeb2dc9',
}
LAUNCH_FMT = ('cmd.exe /c powershell.exe -NoProfile -ExecutionPolicy Bypass -File {ps1} -Prepared {prep} '
              '-Output {run} -Execute -MinimumFreeGiB 8 -AllowConcurrent > {log} 2>&1')
BOM = b'\xef\xbb\xbf'
HERE = Path(__file__).resolve().parent
R2C = HERE.parent
# set in main()
DST_ROOT = ROOT
BUILD = R2C / 'build'
D_COPY = ROOT / 'rm10681_build'
LAUNCH_FILE = ROOT / 'launch_lines_rm10681.txt'
PRIORITY = {}


# ------------------------------------------------------------------------------------------------ helpers
def sha_b(b):
    return hashlib.sha256(b).hexdigest()


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 23), b''):
            h.update(b)
    return h.hexdigest()


def now():
    return datetime.datetime.now().astimezone().isoformat(timespec='seconds')


def canon(obj):
    """The serialisation of the prepared JSON files of the rm arm (checked byte-exact before use)."""
    return json.dumps(obj, indent=2, ensure_ascii=False).replace('\n', '\r\n').encode('utf-8')


def jbytes(obj):
    return (json.dumps(obj, indent=1, ensure_ascii=False) + '\n').encode('utf-8')


def load_json(p):
    return json.load(io.open(p, encoding='utf-8-sig'))


def src_tag(s):
    return 's%d_v3c3rm' % s


def dst_tag(s):
    return 's%d_v3c3rm10681' % s


def src_dir(s):
    return ROOT / src_tag(s) / 'prepared'


def dst_dir(s):
    return DST_ROOT / dst_tag(s) / 'prepared'


def dst_rel(rel, s):
    return rel.replace('baseline_%s.inpx' % src_tag(s), 'baseline_%s.inpx' % dst_tag(s))


def path_swap(p, s):
    """A path inside the rm prepared folder -> the same file in the new prepared folder."""
    a = str(src_dir(s))
    assert p.startswith(a + '\\'), p
    return str(dst_dir(s)) + '\\' + dst_rel(p[len(a) + 1:], s)


def prepared_swap(d, s):
    out = copy.deepcopy(d)
    out['network'] = path_swap(d['network'], s)
    out['snapshot_sha256'] = {path_swap(k, s): v for k, v in d['snapshot_sha256'].items()}
    return out


def strings_with(o, needle, path=''):
    hits = []
    if isinstance(o, dict):
        for k, v in o.items():
            if needle in k:
                hits.append(path + '/<key>')
            hits += strings_with(v, needle, path + '/' + (k if needle not in k else '<key>'))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            hits += strings_with(v, needle, '%s[%d]' % (path, i))
    elif isinstance(o, str) and needle in o:
        hits.append(path)
    return hits


def write_new(path, data):
    path = Path(path)
    guard_dest(path)
    if path.exists():
        assert path.read_bytes() == data, 'refusing to overwrite a different existing file: %s' % path
        return 'identical_existing'
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'xb') as f:
        f.write(data)
    assert path.read_bytes() == data
    return 'written'


def guard_dest(p):
    p = Path(p).resolve()
    allowed = [DST_ROOT / dst_tag(31), DST_ROOT / dst_tag(41), BUILD, D_COPY, LAUNCH_FILE]
    ok = any(p == r or str(p).startswith(str(r) + os.sep) for r in allowed)
    assert ok, 'write outside the allowed new folders: %s' % p


def below_normal():
    k = ctypes.WinDLL('kernel32', use_last_error=True)
    k.GetCurrentProcess.restype = wintypes.HANDLE
    k.SetPriorityClass.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    k.SetPriorityClass.restype = wintypes.BOOL
    k.GetPriorityClass.argtypes = [wintypes.HANDLE]
    k.GetPriorityClass.restype = wintypes.DWORD
    h = k.GetCurrentProcess()
    ok = bool(k.SetPriorityClass(h, 0x00004000))
    return {'set_ok': ok, 'priority_class': hex(k.GetPriorityClass(h))}


def obj_diff(a, b, path=''):
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in a:
            if k not in b:
                out.append((path + '/' + k, 'removed'))
            else:
                out += obj_diff(a[k], b[k], path + '/' + k)
        for k in b:
            if k not in a:
                out.append((path + '/' + k, 'added'))
        if [k for k in a if k in b] != [k for k in b if k in a]:
            out.append((path, 'key_order_changed'))
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append((path, 'list_length'))
        for i, (x, y) in enumerate(zip(a, b)):
            out += obj_diff(x, y, '%s[%d]' % (path, i))
    elif a != b or type(a) is not type(b):
        out.append((path, 'changed'))
    return out


def rm_launch_times():
    out = {}
    kst = datetime.timezone(datetime.timedelta(hours=9))
    for ln in RM_WMI_LINES.read_text(encoding='utf-8-sig').splitlines():
        parts = ln.split('  ')
        if len(parts) >= 3 and parts[1] in (src_tag(31), src_tag(41)):
            assert parts[0][19:20] == '.' and parts[0].endswith('+09:00'), parts[0]
            out[int(parts[1][1:3])] = datetime.datetime.strptime(parts[0][:19], '%Y-%m-%dT%H:%M:%S').replace(tzinfo=kst)
    assert set(out) == set(SEEDS), out
    return out


def inventory(root):
    rows = {}
    for dp, dn, fn in os.walk(root):
        for n in fn:
            p = Path(dp) / n
            st = p.stat()
            rows[str(p.relative_to(root))] = {'bytes': st.st_size, 'sha256': sha(p),
                                             'ctime': getattr(st, 'st_birthtime', st.st_ctime),  # creation time
                                             'mtime': st.st_mtime}
    return rows


def run_created(s):
    t = src_tag(s)
    return {'network\\baseline_%s.err' % t, 'network\\baseline_%s_001.err' % t,
            'network\\baseline_%s.results\\1.db' % t}


# ------------------------------------------------------------------------------------------------ build
def build():
    receipt = BUILD / 'r2c_build_receipt.json'
    assert not receipt.exists(), 'receipt exists'
    rmb = load_json(RM_BUILD_RECEIPT)
    launch = rm_launch_times()
    rec = {'created': now(), 'dest_root': str(DST_ROOT), 'rehearsal': DST_ROOT != ROOT,
           'purpose': 'D-K9-79 R2c: rule ALINEA on RM_C10681 only; the other 7 meters get no COM write '
                      '(native OFF, = NC3); everything else = s<S>_v3c3rm',
           'script': {'path': str(Path(__file__).resolve()), 'sha256': sha(Path(__file__).resolve())},
           'python': sys.executable, 'priority': PRIORITY,
           'rm_launch_kst': {str(k): v.isoformat() for k, v in launch.items()}, 'seeds': {}}
    for s in SEEDS:
        t0 = time.time()
        src, dst = src_dir(s), dst_dir(s)
        assert not dst.parent.exists(), 'refusing: %s exists' % dst.parent
        guard_dest(dst)
        inv = inventory(src)
        tl = launch[s].timestamp()
        created_by_run = sorted(r for r, v in inv.items() if v['ctime'] >= tl)
        assert set(created_by_run) == run_created(s), created_by_run
        modified_by_run = sorted(r for r, v in inv.items() if v['ctime'] < tl <= v['mtime'])
        assert modified_by_run == ['network\\VISSIG_Controller.dll.err'], modified_by_run
        assert inv['network\\VISSIG_Controller.dll.err']['sha256'] == sha(SRC23_DLL_ERR), 'dll.err differs from source'
        pj_src = src / 'prepared.json'
        rm_run = load_json(ROOT / src_tag(s) / 'run' / 'run.json')
        assert sha(pj_src) == rm_run['prepared_sha256'] == rmb['seeds']['s%d' % s]['prepared_sha256']
        d_src = load_json(pj_src)
        bad = [k for k, v in d_src['snapshot_sha256'].items() if sha(k) != v]
        assert not bad, bad
        other = [h for h in strings_with(d_src, src_tag(s)) if not (h == '/network' or h.startswith('/snapshot_sha256'))]
        assert not other, other
        # ---- copy all but the run-created items and the two JSON files that are rewritten
        copied = {}
        for rel in sorted(inv):
            if rel in run_created(s) or rel in ('rule_policy.json', 'prepared.json'):
                continue
            a, b = src / rel, dst / dst_rel(rel, s)
            guard_dest(b)
            assert not b.exists(), b
            b.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(a, b)
            hb = sha(b)
            assert hb == inv[rel]['sha256'], rel
            copied[dst_rel(rel, s)] = {'from': rel, 'sha256': hb, 'bytes': inv[rel]['bytes']}
        # ---- rule_policy.json: meters -> {KEEP}
        raw_rp = (src / 'rule_policy.json').read_bytes()
        rp = json.loads(raw_rp.decode('utf-8'))
        assert canon(rp) == raw_rp, 'rule_policy.json is not in the canonical form'
        assert KEEP in rp['meters'] and len(rp['meters']) == 8
        rp_new = copy.deepcopy(rp)
        rp_new['meters'] = {KEEP: copy.deepcopy(rp['meters'][KEEP])}
        new_rp = canon(rp_new)
        write_new(dst / 'rule_policy.json', new_rp)
        # ---- prepared.json: path swap + rule_policy pin
        raw_pj = pj_src.read_bytes()
        assert canon(d_src) == raw_pj, 'prepared.json is not in the canonical form'
        d_new = prepared_swap(d_src, s)
        rp_key = str(dst / 'rule_policy.json')
        assert rp_key in d_new['snapshot_sha256']
        d_new['snapshot_sha256'][rp_key] = sha_b(new_rp)
        new_pj = canon(d_new)
        write_new(dst / 'prepared.json', new_pj)
        bad = [k for k, v in d_new['snapshot_sha256'].items() if not Path(k).exists() or sha(k) != v]
        bad_in = [k for k, v in d_new['inputs'].items() if not Path(k).exists() or sha(k) != v]
        assert not bad and not bad_in, (bad, bad_in)
        rec['seeds']['s%d' % s] = {
            'source_prepared': str(src), 'prepared': str(dst),
            'left_out_created_by_rm_run': created_by_run,
            'modified_by_rm_run_but_copied': {'network\\VISSIG_Controller.dll.err': 'sha equals %s' % SRC23_DLL_ERR},
            'copied_byte_identical': len(copied), 'copied': copied,
            'rule_policy_sha256': {'rm': sha_b(raw_rp), 'rm10681': sha_b(new_rp)},
            'prepared_sha256': {'rm': sha_b(raw_pj), 'rm10681': sha_b(new_pj)},
            'network_sha256': sha(Path(d_new['network'])), 'network': d_new['network'],
            'snapshot_pins_valid': len(d_new['snapshot_sha256']), 'inputs_pins_valid': len(d_new['inputs']),
            'seconds': round(time.time() - t0, 1)}
        print('s%d: copied %d files byte-identical; rule_policy %s -> %s; prepared.json %s -> %s; network %s (%.1f s)'
              % (s, len(copied), sha_b(raw_rp)[:8], sha_b(new_rp)[:8], sha_b(raw_pj)[:8], sha_b(new_pj)[:8],
                 rec['seeds']['s%d' % s]['network_sha256'][:8], time.time() - t0), flush=True)
    rec['finished'] = now()
    write_new(receipt, jbytes(rec))
    print('receipt', receipt, sha(receipt)[:8])


# ------------------------------------------------------------------------------------------------ verify (static)
def verify():
    receipt = BUILD / 'r2c_build_receipt.json'
    rec = load_json(receipt)
    rmb = load_json(RM_BUILD_RECEIPT)
    rep = {'created': now(), 'dest_root': str(DST_ROOT), 'priority': PRIORITY, 'script_sha256': sha(Path(__file__).resolve()),
           'build_receipt_sha256': sha(receipt), 'checks': {}, 'failed': []}

    def check(name, fn):
        try:
            rep['checks'][name] = {'ok': True, 'detail': fn()}
        except Exception as e:  # noqa: BLE001 - record and continue
            rep['checks'][name] = {'ok': False, 'error': repr(e)[:4000]}
            rep['failed'].append(name)
        print('%-58s %s' % (name, 'OK' if rep['checks'][name]['ok'] else 'FAIL ' + rep['checks'][name]['error'][:300]),
              flush=True)

    def tools():
        now_sha = {str(p): sha(p) for p in (FFP, FNP, FFPV, RUN_PS1, RUNNER_VBS, DIAG)}
        for p in (FFP, FNP, FFPV, RUN_PS1, RUNNER_VBS):
            assert now_sha[str(p)] == rmb['tools'][str(p)], ('tool changed since the rm build', str(p))
        assert now_sha[str(DIAG)] == EXPECTED_SHA[str(DIAG)]
        g = subprocess.run(['git', '--no-optional-locks', '-C', str(SIM3), 'status', '--porcelain', '--',
                            'diagnostics/fast_fixed_profile.py', 'diagnostics/fast_nc_prepare.py',
                            'diagnostics/fast_fixed_profile_verify.py', 'diagnostics/fast_nc_run.ps1',
                            'diagnostics/fast_nc_runner.vbs', 'evaluation/controllers/diagnostic_profile.py'],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
        head = subprocess.run(['git', '--no-optional-locks', '-C', str(SIM3), 'rev-parse', 'HEAD'],
                              stdout=subprocess.PIPE, timeout=60)
        return {'sha256_now_equals_rm_build_receipt': now_sha, 'sim3_head': head.stdout.decode().strip(),
                'sim3_status_of_these_files': g.stdout.decode().strip().splitlines()}
    check('code_used_by_rm_arms_unchanged', tools)

    def code_facts():
        ffp = FFP.read_text(encoding='utf-8').splitlines()
        ver = FFPV.read_text(encoding='utf-8').splitlines()
        vbs = RUNNER_VBS.read_text(encoding='utf-8', errors='replace').splitlines()

        def where(lines, text):
            hits = [i + 1 for i, ln in enumerate(lines) if text in ln]
            assert hits, text
            return hits
        return {
            'fast_fixed_profile.py history init over cfg meters': where(ffp, "'greens': {m: 10 for m in cfg['meters']}"),
            'fast_fixed_profile.py rule loop over cfg meters': where(ffp, "for mid, meter in cfg['meters'].items():"),
            'fast_fixed_profile.py meter write inside that loop': where(ffp, "events.append([t, 'meter', meter['sc'], 1, value])"),
            'fast_fixed_profile.py observations need every station id': where(ffp, "if len(by_id) != len(obs) or set(by_id) != ids:"),
            'verify loops decision meters only': where(ver, "for mid, row in decision['meters'].items():"),
            'verify untargeted SG ownership must not change': where(ver, "'Untargeted DSD/SG ownership changed'"),
            'vbs applies only rule_events rows': where(vbs, 'ApplyEventFile fs.BuildPath(output,"rule_events.csv")'),
            'vbs untargeted SG ownership check': where(vbs, 'Untargeted SG ownership changed'),
        }
    check('selection_mechanism_code_lines', code_facts)

    for s in SEEDS:
        def one(s=s):
            src, dst = src_dir(s), dst_dir(s)
            inv_s, inv_d = inventory(src), inventory(dst)
            m = {dst_rel(k, s): k for k in inv_s if k not in run_created(s)}
            assert set(inv_d) == set(m), sorted(set(inv_d) ^ set(m))[:20]
            differ = sorted(k for k in inv_d if inv_d[k]['sha256'] != inv_s[m[k]]['sha256'])
            assert differ == ['prepared.json', 'rule_policy.json'], differ
            net_d = dst / 'network' / ('baseline_%s.inpx' % dst_tag(s))
            net_s = src / 'network' / ('baseline_%s.inpx' % src_tag(s))
            hn = sha(net_d)
            assert hn == sha(net_s) == EXPECTED_SHA['net%d' % s] == rmb['seeds']['s%d' % s]['network_sha256']
            # rule_policy
            rp_s, rp_d = load_json(src / 'rule_policy.json'), load_json(dst / 'rule_policy.json')
            rp_dif = obj_diff(rp_s, rp_d)
            exp = sorted(('/meters/' + x, 'removed') for x in rp_s['meters'] if x != KEEP)
            assert sorted(rp_dif) == exp and len(exp) == 7, rp_dif
            assert list(rp_d['meters']) == [KEEP] and rp_d['meters'][KEEP] == rp_s['meters'][KEEP]
            for k in rp_s:
                if k != 'meters':
                    assert rp_d[k] == rp_s[k], k
            al = rp_d['rule']['alinea']
            alinea_10681 = {k: (v[KEEP] if isinstance(v, dict) else v) for k, v in al.items()}
            assert alinea_10681 == {'gain_vph_per_pct': 140, 'target_occupancy_pct': 15, 'min_rate_vph': 511.2,
                                    'max_rate_vph': 3024.0}, alinea_10681
            assert rp_d['rule']['arm'] == 'rm' and rp_d['minimum_green'] == 2.0 and rp_d['max_green_change'] == 2
            assert canon(rp_d) == (dst / 'rule_policy.json').read_bytes()
            # prepared.json
            pj_s, pj_d = load_json(src / 'prepared.json'), load_json(dst / 'prepared.json')
            pj_dif = obj_diff(prepared_swap(pj_s, s), pj_d)
            assert pj_dif == [('/snapshot_sha256/' + str(dst / 'rule_policy.json'), 'changed')], pj_dif
            assert not strings_with(pj_d, src_tag(s) + '\\') and not strings_with(pj_d, 'baseline_%s.inpx' % src_tag(s))
            assert pj_d['snapshot_sha256'][str(dst / 'rule_policy.json')] == sha(dst / 'rule_policy.json')
            assert pj_d['network'] == str(net_d) and pj_d['seed'] == s and pj_d['mode'] == 'fixed_profile'
            bad = [k for k, v in pj_d['snapshot_sha256'].items() if sha(k) != v]
            bad_in = [k for k, v in pj_d['inputs'].items() if sha(k) != v]
            assert not bad and not bad_in and len(pj_d['snapshot_sha256']) == 53 and len(pj_d['inputs']) == 44
            assert all(k.startswith(str(dst) + '\\') for k in pj_d['snapshot_sha256'])
            assert canon(pj_d) == (dst / 'prepared.json').read_bytes()
            # profile compile (read-only import of the sim3 module; no events expected, initial/proof reproduced)
            if str(SIM3D) not in sys.path:
                sys.path.insert(0, str(SIM3D))
            spec = importlib.util.spec_from_file_location('ffp_ro', str(FFP))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            prof = load_json(dst / 'fixed_profile.json')
            assert prof['network_sha256'] == hn
            events, initial, proof = mod.compile_profile(net_d, prof)
            assert events == []
            fi = [ln.split(',') for ln in (dst / 'fixed_initial.csv').read_text(encoding='ascii').splitlines()]
            assert fi[0] == ['time_s', 'kind', 'no', 'veh_class', 'value'] and [[str(x) for x in r] for r in initial] == fi[1:]
            pr = json.loads(json.dumps(proof, ensure_ascii=False))
            assert pr == load_json(dst / 'fixed_profile_proof.json') == pj_d['fixed_profile_proof']
            # rule_runtime / station ids / meter SC present
            rt = (dst / 'rule_runtime.txt').read_bytes().decode('utf-16').splitlines()
            assert rt == [RT_PYTHON, str(FFP), '900'] and Path(rt[0]).is_file() and Path(rt[1]).is_file(), rt
            mids = [int(x) for x in (dst / 'rule_measurements.csv').read_text(encoding='ascii').split()[1:]]
            assert sorted(mids) == sorted(i for st in rp_d['detectors']['stations'] for i in st['measurement_ids'])
            assert rp_d['meters'][KEEP]['sc'] == 9106 and '9106' in pr['ldp_signal_groups']
            for p in (dst.parent / 'run', dst.parent / 'launch.log'):
                assert not p.exists(), p
            return {'files': len(inv_d), 'files_differing_from_rm_arm': differ,
                    'network': str(net_d), 'network_sha256': hn, 'network_sha256_equals_rm_arm': True,
                    'rule_policy_json_diff_vs_rm': rp_dif, 'rule_policy_meters': list(rp_d['meters']),
                    'alinea_RM_C10681': alinea_10681,
                    'prepared_json_diff_vs_rm_after_path_swap': pj_dif,
                    'snapshot_pins_valid': 53, 'inputs_pins_valid': 44,
                    'compile_profile_events': 0, 'fixed_initial_rows_reproduced': len(initial),
                    'proof_equals_file_and_prepared_json': True, 'rule_runtime': rt,
                    'run_dir_and_launch_log_absent': True}
        check('s%d_prepared_static' % s, one)
    rep['summary'] = {k: v['ok'] for k, v in rep['checks'].items()}
    p = BUILD / ('r2c_checks.json' if not rep['failed'] else 'r2c_checks_FAILED_%s.json' % datetime.datetime.now().strftime('%H%M%S'))
    write_new(p, jbytes(rep))
    print('checks', p, sha(p)[:8], 'failed =', rep['failed'])
    if rep['failed']:
        raise SystemExit(1)


# ------------------------------------------------------------------------------------------------ dry run
def guard_no_execute(tokens):
    low = [t.lower() for t in tokens]
    i = low.index('-file')
    assert tokens[i + 1] == str(RUN_PS1), tokens[i + 1]
    for t in tokens[i + 2:]:
        if t.startswith('-') and len(t) > 1:
            name = t[1:].split(':')[0].lower()
            assert name and not 'execute'.startswith(name), 'refusing: %r would bind -Execute' % t
        assert not any(ch in t for ch in '<>|&'), 'refusing redirection / chaining token %r' % t


def launch_line(s):
    rd = DST_ROOT / dst_tag(s)
    return LAUNCH_FMT.format(ps1=RUN_PS1, prep=rd / 'prepared', run=rd / 'run', log=rd / 'launch.log')


def dry_from_launch(line):
    head, sep, tail = line.partition(' > ')
    assert sep and tail.endswith(' 2>&1') and '>' not in head
    toks = head.split(' ')
    assert toks[:3] == ['cmd.exe', '/c', 'powershell.exe'] and toks.count('-Execute') == 1
    toks.remove('-Execute')
    toks = toks[2:]
    guard_no_execute(toks)
    return toks


def run_dry(toks):
    guard_no_execute(toks)
    t0 = time.time()
    p = subprocess.run(toks, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=0x4000, timeout=900)
    return p.returncode, p.stdout, p.stderr, round(time.time() - t0, 2)


ARG_KEYS = ('runner_vbs', 'network', 'prepared', 'output', 'seed', 'terminal_sec', 'mode')


def parse_arguments(a):
    import re
    m = re.match(r'^//nologo "([^"]+)" "([^"]+)" "([^"]+)" "([^"]+)" (\d+) (\d+) (\w+)$', a)
    assert m, a
    return dict(zip(ARG_KEYS, m.groups()))


def dryrun():
    out = {'created': now(), 'dest_root': str(DST_ROOT), 'priority': PRIORITY, 'script_sha256': sha(Path(__file__).resolve()),
           'runner': {'fast_nc_run.ps1': sha(RUN_PS1), 'fast_nc_runner.vbs': sha(RUNNER_VBS)}, 'seeds': {}}
    for s in SEEDS:
        rd = DST_ROOT / dst_tag(s)
        for p in (rd / 'run', rd / 'launch.log'):
            assert not p.exists(), p
        plain = ['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(RUN_PS1),
                 '-Prepared', str(rd / 'prepared'), '-Output', str(rd / 'run')]
        rc, so, se, dt = run_dry(plain)
        assert rc == 0, (rc, se[:2000])
        assert so and all(b < 0x80 for b in so)
        data = BOM + so
        state = write_new(rd / 'dryrun_check.txt', data)
        lf = dry_from_launch(launch_line(s))
        rc2, so2, se2, dt2 = run_dry(lf)
        assert rc2 == 0 and so2 == so, (rc2, se2[:2000])
        for p in (rd / 'run', rd / 'launch.log'):
            assert not p.exists(), 'the dry run created %s' % p
        rm_bytes = (ROOT / src_tag(s) / 'dryrun_check.txt').read_bytes()
        jb, jc = json.loads(rm_bytes.decode('utf-8-sig')), json.loads(so.decode('ascii'))
        assert list(jb) == list(jc)
        diff_fields = [k for k in jb if jb[k] != jc[k]]
        assert diff_fields == ['arguments'], diff_fields
        tb, tc = parse_arguments(jb['arguments']), parse_arguments(jc['arguments'])
        exp = {'runner_vbs': str(RUNNER_VBS), 'network': str(dst_dir(s) / 'network' / ('baseline_%s.inpx' % dst_tag(s))),
               'prepared': str(dst_dir(s)), 'output': str(rd / 'run'), 'seed': str(s), 'terminal_sec': '9000',
               'mode': 'fixed_profile'}
        assert tc == exp, (tc, exp)
        assert [k for k in tb if tb[k] != tc[k]] == ['network', 'prepared', 'output']
        assert jc['execute'] is False and jc['fixed_profile'] is True and jc['terminal_sec'] == 9000
        out['seeds']['s%d' % s] = {'plain_command': ' '.join(plain), 'exit_code': rc, 'seconds': dt,
                                   'stderr_bytes': len(se), 'dryrun_check.txt': {'path': str(rd / 'dryrun_check.txt'),
                                                                                 'state': state, 'sha256': sha_b(data)},
                                   'launch_form_without_execute': ' '.join(lf), 'launch_form_exit_code': rc2,
                                   'launch_form_stdout_identical': True,
                                   'fields_differing_from_rm_arm_dryrun_check': diff_fields,
                                   'arguments_differing_from_rm_arm': ['network', 'prepared', 'output'],
                                   'rm_arm_dryrun_check_sha256': sha_b(rm_bytes), 'arguments': tc,
                                   'run_dir_created': False, 'launch_log_created': False}
        print('s%d dry run exit %d (%.1f s); launch form (no -Execute) exit %d identical; = rm arm except paths'
              % (s, rc, dt, rc2), flush=True)
    write_new(BUILD / 'r2c_dryrun_receipt.json', jbytes(out))
    print('dry-run receipt', BUILD / 'r2c_dryrun_receipt.json', sha(BUILD / 'r2c_dryrun_receipt.json')[:8])


# ------------------------------------------------------------------------------------------------ launch lines
def launchlines():
    assert DST_ROOT == ROOT, 'launch lines only for the real build'
    rm_rows = {}
    for ln in (ROOT / 'launch_lines_rm.txt').read_text(encoding='utf-8-sig').splitlines():
        if ln and not ln.startswith('#'):
            tag, cmd = ln.split('  ', 1)
            rm_rows[tag] = cmd
    rows = []
    for s in SEEDS:
        mine = launch_line(s)
        assert rm_rows[src_tag(s)].replace(src_tag(s) + '\\', dst_tag(s) + '\\') == mine, 'launch form differs from the rm row'
        assert dry_from_launch(mine)
        rows.append('%s  %s' % (dst_tag(s), mine))
    head = ['# R2c (D-K9-79) rule-RM arms with ALINEA on RM_C10681 only. Exact WMI CommandLine per seed.',
            '# Written by <scratch>/k8/rmcause/r2c_n/tools/build_r2c.py launchlines after build + verify + dryrun.',
            '# Each row = the launch_lines_rm.txt row of the same seed with s<S>_v3c3rm\\ -> s<S>_v3c3rm10681\\.',
            '# Launch detached (parent WmiPrvSE), in PowerShell:',
            "#   Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine='<CommandLine>'; "
            "CurrentDirectory='%s'}" % ROOT,
            '# Before launching: at most 4 VISSIM on this PC; run\\ and launch.log must not exist; 8 GiB free on D:.',
            '# The launch record (time, ReturnValue, PID, VISSIM count before, cwd, command line) goes to',
            '#   wmi_launch_lines_rm10681.txt.']
    data = ('\r\n'.join(head + rows) + '\r\n').encode('ascii')
    state = write_new(LAUNCH_FILE, data)
    write_new(BUILD / 'r2c_launchlines.json', jbytes({'path': str(LAUNCH_FILE), 'state': state, 'sha256': sha_b(data),
                                                      'rows': rows}))
    print('launch lines', LAUNCH_FILE, state, sha_b(data)[:8])


def copy_to_d():
    assert DST_ROOT == ROOT, 'D: copy only for the real build'
    res = {}
    for p in [Path(__file__).resolve()] + sorted(BUILD.glob('*.json')):
        b = D_COPY / p.name
        write_new(b, p.read_bytes())
        res[p.name] = sha(b)
    write_new(D_COPY / 'SHA256SUMS.txt', ''.join('%s  %s\n' % (v, k) for k, v in sorted(res.items())).encode('ascii'))
    print('copied to', D_COPY, {k: v[:8] for k, v in res.items()})


def main():
    global DST_ROOT, BUILD, D_COPY, LAUNCH_FILE
    ap = argparse.ArgumentParser()
    ap.add_argument('phase', choices=('build', 'verify', 'dryrun', 'launchlines', 'copy', 'all'))
    ap.add_argument('--rehearse', action='store_true')
    a = ap.parse_args()
    if a.rehearse:
        DST_ROOT = R2C / 'rehearsal'
        BUILD = R2C / 'rehearsal' / 'build'
        D_COPY = R2C / 'rehearsal' / 'no_d_copy'
        LAUNCH_FILE = R2C / 'rehearsal' / 'no_launch_lines.txt'
    PRIORITY.update(below_normal())
    if a.phase == 'all':
        phases = ('build', 'verify', 'dryrun') + (() if a.rehearse else ('launchlines', 'copy'))
    else:
        phases = (a.phase,)
    for ph in phases:
        print('== phase', ph, 'dest', DST_ROOT, flush=True)
        {'build': build, 'verify': verify, 'dryrun': dryrun, 'launchlines': launchlines, 'copy': copy_to_d}[ph]()


if __name__ == '__main__':
    main()
