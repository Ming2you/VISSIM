# build_vsl.py - v3c3 fixed VSL-only arm (D-K9-95): build, check and dry-run the prepared folders. 2026-10-27 KST.
#
# Arm = NC3 of the same seed with exactly one change of traffic settings: at t = 900 s the desired-speed decisions
# DSD 63, 64, 65, 66 (link 2 @ 3,998.67 m, lanes 1-4, FW_E chain 6,733.2 m) get distribution 91 (= command 90 of the
# v3c3 single-value VSL map) for vehicle classes 10/20/30/70, held to 9,000 s. Meters: no writes (native OFF as NC3).
#
# Runner = the unchanged sim3 fixed-profile runner used by the v3c3 rule-RM and R2c arms
# (D:/VISSIM-merge/sim3/diagnostics/fast_nc_run.ps1 + fast_nc_runner.vbs + fast_fixed_profile.py prepare()).
# Network = the v3c3 rule-RM arm network (NC3 network + recording-only sections: data-collection points/measurements
# and evaluation collect/write flags incl. scDetRec writeFile=true, which the fixed-profile verifier needs for LDP).
#   seed 31, 41: byte copy of the rule-RM arm network; seed 43: the s31 rule-RM network with its single
#   <simulation .../> line replaced by the NC3 s43 line (the seed files differ only in that line).
#
# Subcommands (python -B build_vsl.py <cmd>):
#   build      writes RR/source, GT/profiles, RR/s<S>/prepared, RR/build/build_receipt.json (refuses if any exists)
#   check      read-only static checks -> RR/build/check_receipt.json
#   dryrun     fast_nc_run.ps1 WITHOUT -Execute (no VISSIM, no COM) + fast_nc_runner.vbs --check (no COM)
#              -> RR/s<S>/dryrun_check.txt, RR/build/dryrun_receipt.json
#   launchlines writes RR/launch_lines_vsl.txt (exact WMI CommandLine per seed; NOT launched here)
import csv, difflib, hashlib, io, json, os, re, subprocess, sys, time
from pathlib import Path
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True
RR = Path('D:/VISSIM_runs/20261027_vsl_v3c3')
GT = Path('D:/VISSIM-merge/k8_gate_trees/vsl_v3c3')
if os.environ.get('BUILD_VSL_REHEARSAL') == '1':   # rehearsal: same steps into a scratch tree (never the real roots)
    RR = Path('D:/VISSIM-merge/k8_gate_trees/vsl_v3c3_rehearsal/runs')
    GT = Path('D:/VISSIM-merge/k8_gate_trees/vsl_v3c3_rehearsal/gt')
V3 = Path('D:/VISSIM_runs/20261001_v3c3')
SIM3D = Path('D:/VISSIM-merge/sim3/diagnostics')
SEEDS = (31, 41, 43)
DSDS = (63, 64, 65, 66)
CLASSES = (10, 20, 30, 70)
DIST = 91           # written distribution (v3c3 single-value map: command 90 -> 91)
T_ON = 900
TERMINAL = 9000
NC_SHA = {31: '3de889f0257d998bed50611f798ea388bcf69396dbc40e5726b1e88ebdd31c2e',   # NC3 networks (v3c3 README, sha256sum)
          41: '726af589bddb8c7267654bda446d2f1a4378451f51e1593857062fca0d32587e',
          43: '51478c397b3a2570fc2254a9fa8120a2415304942589f5fb5c2eb1b6858f2dda'}
RM_SHA = {31: '046303541667838f30045a06d230fb5b31944a18db483770539dfcc873176f0d',
          41: 'e4953eaf8c8f983f28b9a14c684075757ddd45e180e63f2235dc9db8b4ed7524'}
CODE = {  # sim3 files the runs execute or that build the folder; values = sha at the rule-RM / R2c builds
    SIM3D / 'fast_fixed_profile.py': 'a05eb0c5d06cad37d19c3c31a2b42687ad016c3b258aad3a592dc170c6615bbb',
    SIM3D / 'fast_nc_prepare.py': 'eb1bd0f0a4ccfef12f6b6b768ef1c7532d2bbf935f68488185b18166dc5514e0',
    SIM3D / 'fast_fixed_profile_verify.py': '914413913c41f6e085b840fa8e33bd7eda6dc7bc74cc10f88622d3c64084de7e',
    SIM3D / 'fast_nc_run.ps1': '269345dade5657a25e224728985a2a32e35fa0e1669404a631591a191fb67136',
    SIM3D / 'fast_nc_runner.vbs': 'bf07acdaaa678d764ccbd0fd237a5aad85c3419f0628790358dd478ffc5e2cf1',
    SIM3D / 'validate_native_signal_record.py': '4a647072d82afdb20cbf0c933b9d947a6a95450b3b84eac41ccff31220f501d3',
}
VERIFY_PY = r'C:\Users\TRLAB\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'


def sha_b(b):
    return hashlib.sha256(b).hexdigest()


def sha_f(p):
    return sha_b(Path(p).read_bytes())


def nc_net(s):
    return V3 / f's{s}_v3c3nc/prepared/network/baseline_s{s}_v3c3nc.inpx'


def rm_net(s):
    return V3 / f's{s}_v3c3rm/prepared/network/baseline_s{s}_v3c3rm.inpx'


def vsl_name(s):
    return f'baseline_s{s}_v3c3vsl'


def src_net(s):
    return RR / 'source' / (vsl_name(s) + '.inpx')


def prep(s):
    return RR / f's{s}' / 'prepared'


def profile_path(s):
    return GT / 'profiles' / f'vsl91_t900_s{s}.json'


def lines(b):
    return b.split(b'\n')


def changed_lines(a, b):
    A, B = lines(a), lines(b)
    out = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(a=A, b=B, autojunk=False).get_opcodes():
        if tag != 'equal':
            out.append([tag, i1 + 1, i2, j1 + 1, j2, [x.decode('utf-8', 'replace') for x in A[i1:i2]],
                        [x.decode('utf-8', 'replace') for x in B[j1:j2]]])
    return out


def strip_line_numbers(ch):
    return [[c[0], c[5], c[6]] for c in ch]


def check_code():
    out = {}
    for p, want in CODE.items():
        got = sha_f(p)
        out[str(p)] = {'sha256': got, 'equals_rm_r2c_build': got == want}
    return out


def build_network_bytes(s):
    """seed s VSL network = rule-RM s31 network with its <simulation> line replaced by NC3 seed-s line."""
    nc31, rm31, ncs = nc_net(31).read_bytes(), rm_net(31).read_bytes(), nc_net(s).read_bytes()
    assert sha_b(rm31) == RM_SHA[31], 'rule-RM s31 network changed'
    for k, b in ((31, nc31), (s, ncs)):
        assert sha_b(b) == NC_SHA[k], f'NC3 s{k} network changed'
    A, R, S = lines(nc31), lines(rm31), lines(ncs)
    sim_nc = [i for i, x in enumerate(A) if x.lstrip().startswith(b'<simulation ')]
    sim_rm = [i for i, x in enumerate(R) if x.lstrip().startswith(b'<simulation ')]
    assert len(sim_nc) == 1 and len(sim_rm) == 1
    d = [i for i, (x, y) in enumerate(zip(A, S)) if x != y]
    assert len(A) == len(S) and (d == sim_nc or (s == 31 and d == [])), ('NC3 seed files must differ only in the simulation line', d)
    R2 = list(R)
    R2[sim_rm[0]] = S[sim_nc[0]]
    out = b'\n'.join(R2)
    rec = {'recipe': 'rule-RM s31 network bytes with its single <simulation .../> line (line %d) replaced by the NC3 s%d '
                      '<simulation .../> line (line %d)' % (sim_rm[0] + 1, s, sim_nc[0] + 1),
           'nc_s31_sha256': sha_b(nc31), 'rm_s31_sha256': sha_b(rm31), f'nc_s{s}_sha256': sha_b(ncs),
           'nc_seed_files_differ_only_in_line': [x + 1 for x in d] or [sim_nc[0] + 1],
           'out_sha256': sha_b(out), 'out_bytes': len(out)}
    if s in RM_SHA:
        rec['equals_rule_rm_arm_network'] = sha_b(out) == RM_SHA[s] and out == rm_net(s).read_bytes()
        assert rec['equals_rule_rm_arm_network'], f'recipe does not reproduce rule-RM s{s} network'
    # same content change vs its NC3 network as rule-RM s31 vs NC3 s31
    ref = strip_line_numbers(changed_lines(nc31, rm31))
    got = strip_line_numbers(changed_lines(ncs, out))
    rec['diff_vs_nc3_equals_rm31_vs_nc31'] = (ref == got)
    rec['diff_vs_nc3_blocks'] = [[c[0], c[1], c[2], c[3], c[4], len(c[5]), len(c[6])] for c in changed_lines(ncs, out)]
    assert rec['diff_vs_nc3_equals_rm31_vs_nc31']
    return out, rec


def nc_assets(s):
    meta = json.loads((V3 / f's{s}_v3c3nc/prepared/prepared.json').read_text(encoding='utf-8-sig'))
    netdir = V3 / f's{s}_v3c3nc/prepared/network'
    out = {}
    for k, v in meta['snapshot_sha256'].items():
        p = Path(k)
        if p.parent.resolve() == netdir.resolve() and p.suffix.lower() != '.inpx':
            out[p.name] = v
    return out


def make_profile(s, net_sha):
    rm = json.loads((V3 / 's31_v3c3rm/prepared/fixed_profile.json').read_text(encoding='utf-8'))
    prof = dict(rm)
    prof['network_sha256'] = net_sha
    prof['seed'] = s
    prof['vsl_commands'] = [{'time_s': T_ON, 'dsd_no': n, 'speed_id': DIST} for n in DSDS]
    prof['meter_commands'] = []
    assert list(prof) == list(rm)
    return prof


def import_sim3():
    if str(SIM3D) not in sys.path:
        sys.path.insert(0, str(SIM3D))
    import fast_fixed_profile as ffp   # noqa: E402  (python -B: no .pyc written into sim3)
    return ffp


def cmd_build():
    for s in SEEDS:
        if prep(s).exists() or (RR / f's{s}' / 'run').exists():
            raise SystemExit(f'exists: {prep(s)}')
    code = check_code()
    if not all(v['equals_rm_r2c_build'] for v in code.values()):
        raise SystemExit('sim3 code differs from the rule-RM/R2c build: ' + json.dumps(code, indent=1))
    ffp = import_sim3()
    (RR / 'source').mkdir(parents=True, exist_ok=False)
    (RR / 'build').mkdir(parents=True, exist_ok=True)
    (GT / 'profiles').mkdir(parents=True, exist_ok=True)
    rec = {'created': time.strftime('%Y-%m-%dT%H:%M:%S+09:00'), 'tool': str(Path(__file__).resolve()),
           'tool_sha256': sha_f(__file__), 'python': sys.executable, 'python_version': sys.version,
           'code': code, 'seeds': {}}
    # assets (same in all three NC3 prepared folders)
    assets = {s: nc_assets(s) for s in SEEDS}
    assert assets[31] == assets[41] == assets[43] and assets[31], 'NC3 asset pins differ across seeds'
    for name, want in sorted(assets[31].items()):
        b = (V3 / 's31_v3c3nc/prepared/network' / name).read_bytes()
        assert sha_b(b) == want, 'NC3 asset changed: ' + name
        (RR / 'source' / name).write_bytes(b)
    rec['assets'] = assets[31]
    for s in SEEDS:
        b, nrec = build_network_bytes(s)
        src_net(s).write_bytes(b)
        prof = make_profile(s, sha_b(b))
        pp = profile_path(s)
        if pp.exists():
            raise SystemExit('profile exists: ' + str(pp))
        pp.write_text(json.dumps(prof, indent=2, ensure_ascii=False), encoding='utf-8')
        (RR / f's{s}').mkdir(parents=True, exist_ok=False)
        meta = ffp.prepare(src_net(s), pp, prep(s))
        rec['seeds'][str(s)] = {'network': nrec, 'source_network': str(src_net(s).resolve()), 'profile': str(pp),
                                'profile_sha256': sha_f(pp), 'prepared': str(prep(s).resolve()),
                                'prepared_json_sha256': sha_f(prep(s) / 'prepared.json'),
                                'command_rows': meta['command_rows'], 'mode': meta['mode']}
        print('built', s, sha_b(b)[:16], meta['command_rows'])
    out = RR / 'build' / 'build_receipt.json'
    out.write_text(json.dumps(rec, indent=1, ensure_ascii=False), encoding='utf-8')
    print('receipt', out, sha_f(out))


def read_csv(p):
    with open(p, encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def json_diff(a, b, path=''):
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b), key=str):
            if k not in a:
                out.append([path + '/' + str(k), 'only_in_second'])
            elif k not in b:
                out.append([path + '/' + str(k), 'only_in_first'])
            else:
                out += json_diff(a[k], b[k], path + '/' + str(k))
    elif a != b:
        out.append([path, 'differs'])
    return out


def cmd_check():
    ffp = import_sim3()
    res = {'created': time.strftime('%Y-%m-%dT%H:%M:%S+09:00'), 'tool_sha256': sha_f(__file__), 'checks': {}}
    C = res['checks']
    C['code_unchanged_since_rm_r2c_build'] = check_code()
    ok_all = all(v['equals_rm_r2c_build'] for v in C['code_unchanged_since_rm_r2c_build'].values())
    br = json.loads((RR / 'build/build_receipt.json').read_text(encoding='utf-8'))
    for s in SEEDS:
        P = prep(s)
        r = {}
        meta = json.loads((P / 'prepared.json').read_text(encoding='utf-8'))
        r['prepared_json_sha256'] = sha_f(P / 'prepared.json')
        r['prepared_json_equals_build_receipt'] = r['prepared_json_sha256'] == br['seeds'][str(s)]['prepared_json_sha256']
        r['mode'] = meta['mode']; r['seed'] = meta['seed']; r['terminal_sec'] = meta['terminal_sec']
        r['control_start_sec'] = meta['control_start_sec']; r['command_rows'] = meta['command_rows']
        bad = [k for k, v in meta['snapshot_sha256'].items() if sha_f(k) != v]
        r['snapshot_pins'] = len(meta['snapshot_sha256']); r['snapshot_pins_bad'] = bad
        badi = [k for k, v in meta['inputs'].items() if sha_f(k) != v]
        r['input_pins'] = len(meta['inputs']); r['input_pins_bad'] = badi
        net = Path(meta['network'])
        r['network'] = str(net); r['network_sha256'] = sha_f(net)
        r['network_name_unique_stem'] = net.stem == vsl_name(s)
        if s in RM_SHA:
            r['network_equals_rule_rm_arm_network_bytes'] = net.read_bytes() == rm_net(s).read_bytes()
        nb = net.read_bytes()
        r['network_diff_vs_nc3_blocks'] = [[c[0], c[1], c[2], c[3], c[4], len(c[5]), len(c[6])] for c in changed_lines(nc_net(s).read_bytes(), nb)]
        r['network_diff_vs_nc3_equals_rm31_vs_nc31'] = (strip_line_numbers(changed_lines(nc_net(s).read_bytes(), nb))
                                                         == strip_line_numbers(changed_lines(nc_net(31).read_bytes(), rm_net(31).read_bytes())))
        root = ET.fromstring(nb)
        r['scDetRec_writeFile'] = root.find('./evaluation/scDetRec').get('writeFile')
        sim = root.find('./simulation').attrib
        r['saved_simulation'] = {k: sim[k] for k in ('randSeed', 'simRes', 'simPeriod', 'numRuns')}
        dsd = {int(n.get('no')): n for n in root.findall('./desSpeedDecisions/desSpeedDecision')}
        r['dsd_63_66'] = {str(n): {'name': dsd[n].get('name'), 'lane': dsd[n].get('lane'), 'pos': dsd[n].get('pos'),
                                    'classes': {p.get('vehClass'): p.get('desSpeedDistr') for p in dsd[n].findall('./vehClassDesSpeedDistr/vehClassDesSpeedDistribution')}}
                          for n in DSDS}
        dist = {int(n.get('no')): [(p.get('x'), p.get('fx')) for p in n.findall('./speedDistrDatPts/speedDistributionDataPoint')]
                for n in root.findall('./desSpeedDistributions/desSpeedDistribution')}
        r['distribution_91'] = dist.get(91); r['distribution_90'] = dist.get(90); r['distribution_110'] = dist.get(110)
        # events
        ev = read_csv(P / 'fixed_events.csv')
        want = [{'time_s': str(T_ON), 'kind': 'vsl', 'no': str(n), 'veh_class': str(c), 'value': str(DIST)} for n in DSDS for c in CLASSES]
        r['fixed_events_rows'] = len(ev); r['fixed_events_exact'] = ev == want
        init = read_csv(P / 'fixed_initial.csv')
        addr = {(x['no'], x['veh_class']) for x in init if x['kind'] == 'vsl'}
        r['event_addresses_in_fixed_initial'] = all((e['no'], e['veh_class']) in addr for e in ev)
        r['initial_dsd_63_66'] = sorted({x['value'] for x in init if x['kind'] == 'vsl' and int(x['no']) in DSDS})
        r['event_jump_le_20'] = all(abs(int(e['value']) - 110) <= 20 for e in ev)
        # recompile from network + profile (pure) == files
        prof = json.loads(Path(meta['profile_source']['path']).read_text(encoding='utf-8'))
        r['profile_sha256'] = sha_f(meta['profile_source']['path'])
        r['profile_pin_ok'] = r['profile_sha256'] == meta['profile_source']['sha256']
        e2, i2, p2 = ffp.compile_profile(net, prof)
        buf = io.StringIO(); w = csv.writer(buf, lineterminator='\r\n'); w.writerow(['time_s', 'kind', 'no', 'veh_class', 'value']); w.writerows(e2)
        r['recompiled_events_equal_file'] = buf.getvalue().encode('ascii') == (P / 'fixed_events.csv').read_bytes()
        buf = io.StringIO(); w = csv.writer(buf, lineterminator='\r\n'); w.writerow(['time_s', 'kind', 'no', 'veh_class', 'value']); w.writerows(i2)
        r['recompiled_initial_equal_file'] = buf.getvalue().encode('ascii') == (P / 'fixed_initial.csv').read_bytes()
        pf = json.loads((P / 'fixed_profile_proof.json').read_text(encoding='utf-8'))
        r['recompiled_proof_equal_file'] = json.loads(json.dumps(p2)) == pf
        r['proof_equal_prepared_json'] = pf == meta['fixed_profile_proof']
        r['vsl_locations'] = pf['vsl_locations']
        r['ldp_signal_groups_n'] = len(pf['ldp_signal_groups'])
        r['no_rule_files'] = not any((P / n).exists() for n in ('rule_policy.json', 'rule_runtime.txt', 'rule_measurements.csv', 'mpc_policy.json'))
        r['run_dir_and_launch_log_absent'] = not (RR / f's{s}' / 'run').exists() and not (RR / f's{s}' / 'launch.log').exists()
        # compare with NC3 prepared and (s31, s41) rule-RM prepared
        files = sorted(str(p.relative_to(P)).replace('\\', '/') for p in P.rglob('*') if p.is_file())
        r['files'] = files
        def cmp_dir(other, rename):
            o_files = sorted(str(p.relative_to(other)).replace('\\', '/') for p in other.rglob('*') if p.is_file()
                             and not (p.parent.name == 'network' and (p.suffix in ('.err',) or p.name.endswith('.db'))) and '.results' not in str(p))
            same, differ = [], []
            mine = {f: f for f in files}
            for f in o_files:
                g = rename(f)
                if g in mine:
                    (same if (P / g).read_bytes() == (other / f).read_bytes() else differ).append(f)
            only_other = [f for f in o_files if rename(f) not in mine]
            only_mine = [f for f in files if f not in {rename(x) for x in o_files}]
            return {'same_bytes': same, 'differ': differ, 'only_in_other': only_other, 'only_in_vsl': only_mine}
        r['vs_nc3_prepared'] = cmp_dir(V3 / f's{s}_v3c3nc/prepared', lambda f: f.replace(f'baseline_s{s}_v3c3nc', vsl_name(s)))
        if s in RM_SHA:
            rmP = V3 / f's{s}_v3c3rm/prepared'
            r['vs_rule_rm_prepared'] = cmp_dir(rmP, lambda f: f.replace(f'baseline_s{s}_v3c3rm', vsl_name(s)))
            rmeta = json.loads((rmP / 'prepared.json').read_text(encoding='utf-8'))
            r['prepared_json_keys_vs_rule_rm'] = {'only_rm': sorted(set(rmeta) - set(meta)), 'only_vsl': sorted(set(meta) - set(rmeta)),
                                                  'differing': sorted(k for k in set(meta) & set(rmeta) if meta[k] != rmeta[k])}
            rproof = json.loads((rmP / 'fixed_profile_proof.json').read_text(encoding='utf-8'))
            r['proof_diff_vs_rule_rm'] = json_diff(rproof, pf)
            rprof = json.loads((rmP / 'fixed_profile.json').read_text(encoding='utf-8'))
            r['profile_diff_vs_rule_rm'] = json_diff(rprof, prof)
        else:
            rproof = json.loads((V3 / 's31_v3c3rm/prepared/fixed_profile_proof.json').read_text(encoding='utf-8'))
            r['proof_diff_vs_rule_rm_s31'] = json_diff(rproof, pf)
            rprof = json.loads((V3 / 's31_v3c3rm/prepared/fixed_profile.json').read_text(encoding='utf-8'))
            r['profile_diff_vs_rule_rm_s31'] = json_diff(rprof, prof)
            r['fixed_initial_equals_rule_rm_s31'] = (P / 'fixed_initial.csv').read_bytes() == (V3 / 's31_v3c3rm/prepared/fixed_initial.csv').read_bytes()
        ok = (r['mode'] == 'fixed_profile' and r['seed'] == s and r['terminal_sec'] == TERMINAL and r['control_start_sec'] == T_ON
              and r['command_rows'] == 16 and not bad and not badi and r['prepared_json_equals_build_receipt'] and r['network_name_unique_stem']
              and r.get('network_equals_rule_rm_arm_network_bytes', True) and r['network_diff_vs_nc3_equals_rm31_vs_nc31']
              and r['scDetRec_writeFile'] == 'true' and r['saved_simulation']['randSeed'] == str(s) and r['saved_simulation']['simRes'] == '10'
              and all(v['classes'] == {'10': '110', '20': '110', '30': '110', '70': '110'} for v in r['dsd_63_66'].values())
              and r['distribution_91'] == [('90', '0'), ('92', '1')] and r['fixed_events_exact'] and r['event_addresses_in_fixed_initial']
              and r['event_jump_le_20'] and r['profile_pin_ok'] and r['recompiled_events_equal_file'] and r['recompiled_initial_equal_file']
              and r['recompiled_proof_equal_file'] and r['proof_equal_prepared_json'] and r['no_rule_files'] and r['run_dir_and_launch_log_absent']
              and r['ldp_signal_groups_n'] > 0)
        r['ok'] = bool(ok)
        ok_all = ok_all and ok
        C[f's{s}'] = r
    res['all_ok'] = bool(ok_all)
    out = RR / 'build' / 'check_receipt.json'
    out.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding='utf-8')
    print('all_ok', ok_all, 'receipt', out, sha_f(out))
    return ok_all


def ps_cmdline(s, out_name='run', log_name='launch.log'):
    base = f'D:\\VISSIM_runs\\20261027_vsl_v3c3\\s{s}'
    return ('cmd.exe /c powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\\VISSIM-merge\\sim3\\diagnostics\\fast_nc_run.ps1 '
            f'-Prepared {base}\\prepared -Output {base}\\{out_name} -Execute -MinimumFreeGiB 8 -AllowConcurrent > {base}\\{log_name} 2>&1')


def cmd_dryrun():
    res = {'created': time.strftime('%Y-%m-%dT%H:%M:%S+09:00'), 'tool_sha256': sha_f(__file__), 'seeds': {}}
    vbs = subprocess.run(['cscript.exe', '//nologo', str(SIM3D / 'fast_nc_runner.vbs'), '--check'], capture_output=True, text=True)
    res['vbs_check'] = {'exit': vbs.returncode, 'stdout': vbs.stdout.strip(), 'stderr': vbs.stderr.strip()}
    ok = vbs.returncode == 0 and vbs.stdout.strip() == 'SYNTAX_OK'
    for s in SEEDS:
        base = RR / f's{s}'
        args = ['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(SIM3D / 'fast_nc_run.ps1'),
                '-Prepared', str(base / 'prepared'), '-Output', str(base / 'run'), '-MinimumFreeGiB', '8', '-AllowConcurrent']
        p = subprocess.run(args, capture_output=True)
        text = p.stdout.decode('utf-8', 'replace')
        (base / 'dryrun_check.txt').write_bytes(p.stdout)
        try:
            j = json.loads(text)
        except Exception:
            j = None
        r = {'exit': p.returncode, 'stderr': p.stderr.decode('utf-8', 'replace')[:2000], 'json': j,
             'dryrun_check_sha256': sha_b(p.stdout)}
        exp_args = ('//nologo "{0}" "{1}" "{2}" "{3}" {4} {5} fixed_profile'.format(
            SIM3D / 'fast_nc_runner.vbs', base / 'prepared' / 'network' / (vsl_name(s) + '.inpx'), base / 'prepared', base / 'run', s, TERMINAL))
        r['expected_arguments'] = exp_args
        r['run_dir_created'] = (base / 'run').exists()
        good = (p.returncode == 0 and j is not None and j.get('execute') is False and j.get('fixed_profile') is True
                and j.get('native_preserve') is False and j.get('terminal_sec') == TERMINAL and j.get('arguments') == exp_args
                and not r['run_dir_created'])
        if s in RM_SHA:
            rmj = json.loads((V3 / f's{s}_v3c3rm/dryrun_check.txt').read_text(encoding='utf-8-sig'))
            def norm(a, base, stem):
                return a.replace(stem, '<NET>').replace(base, '<BASE>')
            r['rule_rm_dryrun_keys_equal'] = sorted(rmj) == sorted(j or {})
            r['rule_rm_dryrun_differs_only_in_paths'] = (j is not None and all(rmj[k] == j.get(k) for k in rmj if k != 'arguments')
                and norm(rmj['arguments'], str(V3 / f's{s}_v3c3rm'), f'baseline_s{s}_v3c3rm') == norm(j['arguments'], str(base), vsl_name(s)))
            r['rule_rm_dryrun'] = rmj
            good = good and r['rule_rm_dryrun_keys_equal'] and r['rule_rm_dryrun_differs_only_in_paths']
        r['ok'] = bool(good)
        ok = ok and good
        res['seeds'][str(s)] = r
    res['all_ok'] = bool(ok)
    out = RR / 'build' / 'dryrun_receipt.json'
    out.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding='utf-8')
    print('all_ok', ok, 'receipt', out, sha_f(out))
    return ok


def cmd_launchlines():
    p = RR / 'launch_lines_vsl.txt'
    if p.exists():
        raise SystemExit('exists: ' + str(p))
    L = ['# v3c3 fixed VSL-only arm (D-K9-95): DSD 63-66 -> distribution 91 at 900 s, held to 9,000 s; native urban signals; meters not written (native OFF). Exact WMI CommandLine per seed.',
         '# NOT LAUNCHED by build_vsl.py. Launch only through the seat-aware launcher (VS/tools/vsl_launcher.ps1, PRE_VSL.md section 5), which creates the per-seed marker first.',
         '# Each row: <label><2 spaces><CommandLine>. CurrentDirectory D:\\VISSIM_runs\\20261027_vsl_v3c3. Before launch: PC-wide VISSIM < 4, run\\ and launch.log absent, C and D >= 8 GB free.',
         '# One-time relaunch after a stall (user policy): same row with run -> run_retry1 and launch.log -> launch_retry1.log.']
    for s in SEEDS:
        L.append(f's{s}_v3c3vsl  ' + ps_cmdline(s))
    p.write_text('\n'.join(L) + '\n', encoding='ascii')
    print(p, sha_f(p))


if __name__ == '__main__':
    {'build': cmd_build, 'check': cmd_check, 'dryrun': cmd_dryrun, 'launchlines': cmd_launchlines}[sys.argv[1]]()
