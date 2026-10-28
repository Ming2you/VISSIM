# FO build summary (2026-10-27 KST, D-K9-113). Descriptive checks, written before the chain runs. Read-only.
# Derived from work/b1/b1_summary.py (B1). Tree: pre-overlay source == FRZ_B1 (0 diff); overlay record pass; post-overlay source
#   and FRZ_FO FREEZE.json vs FRZ_B1 = exactly the 13 changed + 5 extra declared files; same git head; runner and network bytes
#   unchanged; FO config in FRZ_FO == overlay record sha; freeze log FREEZE_OK; verify before/after the preflights.
# Preflights s31/s41/s43 (FO config) and s31b (B config on FRZ_FO, gate control input only): the B1 preflight checks with the
#   FRZ_FO pin and the right tuning sha, StallSec 3600 in the watchdog command line and status arguments, and a leaf compare
#   with the B1 (FRZ_B1) preflight of the same seed after replacing the tree root and results root: allowed differing leaves =
#   /created_at, /run_id, /observation/freeze/sha256, and (FO config only) leaves whose B1 value is the B config path or sha and
#   whose FO value is the FO config path or sha. Anything else -> check false.
# Pairing (per seed, seeds read from provenance / run.json, never from folder names): NC3 prepared.json + run.json seed and
#   completion, NC3 prepared network sha == its recorded source sha; B provenance seed / network 3de889f0 / runlog SIM_DONE 9000;
#   V-A provenance seed / network 3de889f0; the 42 .sig files byte-equal in FRZ_FO network, NC3 prepared, B run, V-A run;
#   the FO results root does not exist yet.
# usage: python -B fo_summary.py <FRZ_FO> <out.json>
import glob, hashlib, json, os, re, sys
W = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/')
FOR = 'D:/VISSIM-merge/k8_gate_trees/codexhandoff/fo'
B1 = 'D:/VISSIM-merge/k8_gate_trees/codexhandoff/b1'
FRZ1 = B1 + '/frozen/sdmpc31_a49981ff_202610261410'
FRZ1_SHA = '558de2c1b80799a9bedfb192b40b6f5cfa2775853b3431eb181f7b25beca10d1'
HEAD = 'a49981ffb258707c9a5e837d56f8cad829dab0ac'
RUNREL = 'diagnostics/sdmpc_n31_20260924/integration_20260926/run_closedloop3000.ps1'
RUN_SHA = '6ff68b385a4bf6dab23a26bea5a6015641a77808230bfc8366bbc5d2554b38f7'
NETREL = 'diagnostics/sdmpc_n31_20260924/network/baseline_s31_v3c3nc.inpx'
NET_SHA = '3de889f0257d998bed50611f798ea388bcf69396dbc40e5726b1e88ebdd31c2e'
B_TUN_REL = 'diagnostics/b0_v3c3/config_b0_v3c3.json'
FO_TUN_REL = 'diagnostics/b0_v3c3/config_fo_v3c3.json'
B_TUN_SHA = '729640af754a90c8d7fbe8f81577b27bae02b86f1d504e18333c0fc99717f983'
PLANT_SHA = '1184249889cc8ceeb0e730176ea058cf5a7e53aa98732bbb14e0dd113411f25c'
DET_SHA = '108debbb4b021796b195927ba2140dafab571e1d976734190f5d8f5bd255cfbc'
CTRL = 'evaluation/controllers/'
CH13 = [CTRL + n for n in ('area_follower_objective.py', 'joint_owner_neighbors.py', 'runtime_setup.py', 'sdmpc.py', 'sdmpc_budget.py',
        'sdmpc_central.py', 'sdmpc_pfo.py', 'sdmpc_sequence.py', 'sdmpc_tangent.py', 'sdmpc_tangent_constraints.py',
        'sdmpc_tangent_surrogate.py', 'sdmpc_tangent_worker.py', 'vissim_stackelberg_adapter.py')]
EX5 = [CTRL + n for n in ('sdmpc_actuator_scope.py', 'sdmpc_regional_context.py', 'sdmpc_regional_contracts.py',
       'sdmpc_regional_prototype.py')] + [FO_TUN_REL]
NC3 = 'D:/VISSIM_runs/20261001_v3c3/s%d_v3c3nc'
BRUN = 'D:/VISSIM_runs/20261026_codex_b_v3c3/s%d/sdmpc'
VA = 'D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s%d'
FO_RUNS = 'D:/VISSIM_runs/20261028_codex_fo_v3c3'
SOLO_SHA = {}   # rel -> solo sha (filled from the overlay record), plus '__b1_adapter__' = FRZ_B1 adapter sha


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def jl(p):
    return json.load(open(p, encoding='utf-8-sig'))


def txt(p):
    if not os.path.exists(p):
        return ''
    raw = open(p, 'rb').read()
    if raw[:2] in (b'\xff\xfe', b'\xfe\xff'):
        return raw.decode('utf-16')
    return raw.decode('utf-8-sig', errors='replace')


def leaves(o, pre=''):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from leaves(v, pre + '/' + str(k))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from leaves(v, pre + '/' + str(i))
    else:
        yield pre, o


def norm(v, roots):
    if isinstance(v, str):
        s = v.replace('\\', '/')
        for a, b in roots:
            s = re.sub(re.escape(a), b, s, flags=re.I)
        return s
    return v


def stall_tokens(seq):
    seq = [str(x) for x in seq]
    return [seq[i + 1] for i in range(len(seq) - 1) if seq[i] == '-StallSec']


def preflight(seed, tag, frz, frz_sha, fo_tun_sha):
    lab = 's%d%s' % (seed, tag)
    tun_sha = B_TUN_SHA if tag == 'b' else fo_tun_sha
    root, w = FOR + '/runner_preflight/' + lab, FOR + '/runner_preflight/_wrapper/' + lab
    r = {'label': lab, 'seed': seed, 'tuning_expected_sha256': tun_sha}
    end = jl(w + '/end.json') if os.path.exists(w + '/end.json') else {}
    r['runner_exit'], r['wall_sec'] = end.get('runner_exit'), end.get('wall_sec')
    r['wrapper_error'] = jl(w + '/error.json').get('error') if os.path.exists(w + '/error.json') else None
    log = txt(w + '/runner.log')
    m = re.search(r'FREEZE_VERIFIED path=(\S+) sha256=([0-9a-f]{64})', log)
    r['freeze_verified_line'] = m.group(0) if m else None
    r['runner_err_log_bytes'] = os.path.getsize(w + '/runner.err.log') if os.path.exists(w + '/runner.err.log') else None
    st = w + '/preflight_status.json'
    r['status_stage'] = jl(st).get('stage') if os.path.exists(st) else None
    wd = jl(w + '/watchdog_cmdline.json') if os.path.exists(w + '/watchdog_cmdline.json') else None
    r['watchdog_cmdline'] = wd.get('command_line') if wd else None
    r['stall_in_watchdog_cmdline'] = re.findall(r'-StallSec\s+"?(\d+)', r['watchdog_cmdline'] or '')
    sp = w + '/preflight_status_stage_preflight.json'
    r['stall_in_status_arguments'] = stall_tokens(jl(sp)['details']['arguments']) if os.path.exists(sp) else []
    prov = root + '/sdmpc/preflight/run_provenance_sdmpc31_sdmpc9000_s%d.json' % seed
    r['provenance'] = prov if os.path.exists(prov) else None
    if not os.path.exists(prov):
        r['pass'] = False
        return r
    p = jl(prov)
    r['provenance_sha256'] = sha(prov)
    env = p.get('env', {})
    r['env_empty_values'] = sorted(k for k, v in env.items() if v == '')
    r['hold_env'] = {k: env.get(k) for k in ('RW_DECISION_ERROR_POLICY', 'RW_DECISION_HOLD_PREVIOUS', 'RW_DECISION_TIMEOUT_SEC')}
    r['rw_config_sha'] = env.get('RW_SIGNAL_OBSERVATION_CONFIG_SHA256')
    obs = p.get('observation') or {}
    r['network_sha256'] = p['files']['network']['sha256']
    r['tuning_sha256'] = (p['files'].get('tuning') or {}).get('sha256')
    r['freeze_pin'], r['plant_manifest'], r['detectors'] = obs.get('freeze'), obs.get('plant_manifest'), obs.get('detectors')
    r['seed_in_provenance'], r['sim_period_sec'], r['controller'] = p.get('seed'), p.get('sim_period_sec'), p.get('controller')
    r['workspace_root'] = p.get('workspace_root')
    det = r['detectors']
    r['checks'] = {
        'exit0': r['runner_exit'] == 0,
        'freeze_verified_frz_fo': bool(m) and m.group(2) == frz_sha and os.path.normcase(os.path.dirname(m.group(1))) == os.path.normcase(frz.replace('/', '\\')),
        'network_sha': r['network_sha256'] == NET_SHA,
        'hold_policy_env': r['hold_env'] == {'RW_DECISION_ERROR_POLICY': 'hold_previous_on_exception', 'RW_DECISION_HOLD_PREVIOUS': '1', 'RW_DECISION_TIMEOUT_SEC': '0'},
        'tuning_sha': r['tuning_sha256'] == tun_sha,
        'rw_config_sha': r['rw_config_sha'] == tun_sha,
        'freeze_pin_frz_fo': isinstance(r['freeze_pin'], dict) and r['freeze_pin'].get('sha256') == frz_sha,
        'plant_manifest_pin': isinstance(r['plant_manifest'], dict) and r['plant_manifest'].get('sha256') == PLANT_SHA,
        'detector_pin': isinstance(det, dict) and det.get('sha256') == DET_SHA and det.get('rows') == 294,
        'controller_wu_link': r['controller'] == 'wu-link',
        'seed': r['seed_in_provenance'] == seed, 'sim_period_9000': r['sim_period_sec'] == 9000,
        'workspace_root_frz_fo': str(r['workspace_root']).replace('\\', '/').lower() == frz.lower(),
        'no_empty_rw_value': not r['env_empty_values'] or r['env_empty_values'] == ['RW_OBS150_GT'],
        'stall_3600_watchdog_cmdline': r['stall_in_watchdog_cmdline'] == ['3600'],
        'stall_3600_status_arguments': r['stall_in_status_arguments'] == ['3600'],
        'status_preflight_complete': r['status_stage'] == 'preflight_complete',
    }
    # leaf compare with the B1 (FRZ_B1) preflight provenance of the same seed
    g = B1 + '/runner_preflight/s%d/sdmpc/preflight/run_provenance_sdmpc31_sdmpc9000_s%d.json' % (seed, seed)
    pb1 = jl(g)
    roots_a = [(FRZ1, '<FRZ>'), (B1 + '/runner_preflight/s%d' % seed, '<RES>')]
    roots_b = [(frz, '<FRZ>'), (FOR + '/runner_preflight/' + lab, '<RES>')]
    a = {k: norm(v, roots_a) for k, v in leaves(pb1) if not k.startswith('/controller_sources/')}
    b = {k: norm(v, roots_b) for k, v in leaves(p) if not k.startswith('/controller_sources/')}
    diff = sorted(k for k in a.keys() & b.keys() if a[k] != b[k])
    base_allowed = {'/created_at', '/run_id', '/observation/freeze/sha256'}
    swap = {('<FRZ>/' + B_TUN_REL, '<FRZ>/' + FO_TUN_REL), (B_TUN_SHA, fo_tun_sha)}
    adapter_pair = (SOLO_SHA.get('__b1_adapter__'), SOLO_SHA.get(CTRL + 'vissim_stackelberg_adapter.py'))
    undeclared = [k for k in diff if k not in base_allowed and not (tag != 'b' and (a[k], b[k]) in swap)
                  and not (k == '/files/adapter/sha256' and (a[k], b[k]) == adapter_pair)]
    # controller_sources (all .py of evaluation/controllers with sha): compared as path -> sha; allowed = the 13 changed files
    # with the solo sha and the 4 new solo modules with the solo sha, nothing else
    ca = {norm(x['path'], roots_a): x['sha256'] for x in pb1.get('controller_sources', [])}
    cb = {norm(x['path'], roots_b): x['sha256'] for x in p.get('controller_sources', [])}
    c_changed = sorted(k for k in ca.keys() & cb.keys() if ca[k] != cb[k])
    c_extra, c_missing = sorted(cb.keys() - ca.keys()), sorted(ca.keys() - cb.keys())
    want_changed = sorted('<FRZ>/' + r for r in CH13)
    want_extra = sorted('<FRZ>/' + r for r in EX5 if r.startswith(CTRL))
    cs_ok = (c_changed == want_changed and c_extra == want_extra and not c_missing
             and all(cb[k] == SOLO_SHA.get(k[len('<FRZ>/'):]) for k in c_changed + c_extra))
    r['vs_b1'] = {'b1_provenance': g, 'b1_sha256': sha(g), 'leaves_b1': len(a), 'leaves_fo': len(b),
                  'only_b1': sorted(a.keys() - b.keys()), 'only_fo': sorted(b.keys() - a.keys()),
                  'differing': {k: [a[k], b[k]] for k in diff}, 'undeclared_differing': undeclared,
                  'controller_sources': {'b1_count': len(ca), 'fo_count': len(cb), 'changed': c_changed, 'extra': c_extra,
                                         'missing': c_missing, 'declared_only_solo_bytes': cs_ok}}
    r['checks']['vs_b1_only_declared'] = not undeclared and not r['vs_b1']['only_b1'] and not r['vs_b1']['only_fo']
    r['checks']['controller_sources_only_solo17'] = cs_ok
    r['pass'] = all(r['checks'].values())
    return r


def pairing(seed):
    o = {'seed': seed}
    nc = NC3 % seed
    prep, run = jl(nc + '/prepared/prepared.json'), jl(nc + '/run/run.json')
    o['nc3'] = {'prepared_seed': prep.get('seed'), 'run_seed': run.get('seed'), 'completed': run.get('completed'), 'exit_code': run.get('exit_code'),
                'source_network_sha256': prep.get('source_network_sha256'),
                'prepared_network_sha256': sha(nc + '/prepared/network/baseline_s%d_v3c3nc.inpx' % seed) if os.path.exists(nc + '/prepared/network/baseline_s%d_v3c3nc.inpx' % seed) else None,
                'fzp': os.path.exists(nc + '/run/vissim_eval/baseline_s%d_v3c3nc_001.fzp' % seed)}
    bp = jl(BRUN % seed + '/run_provenance_sdmpc31_sdmpc9000_s%d.json' % seed)
    bl = txt(BRUN % seed + '/runlog_sdmpc31_sdmpc9000_s%d.txt' % seed)
    o['b'] = {'seed': bp.get('seed'), 'network_sha256': bp['files']['network']['sha256'], 'tuning_sha256': bp['files']['tuning']['sha256'],
              'sim_done': bool(re.search(r'(?m)^STAGE=SIM_DONE\r?$', bl)), 'sim_sec_9000': bool(re.search(r'(?m)^SIM_SEC=9000\r?$', bl))}
    vp = jl(VA % seed + '/run_provenance_sdmpc31_v3c3_k92va_s%d.json' % seed)
    o['va'] = {'seed': vp.get('seed'), 'network_sha256': vp['files']['network']['sha256']}
    o['checks'] = {
        'nc3_seed': o['nc3']['prepared_seed'] == seed and o['nc3']['run_seed'] == seed,
        'nc3_completed': o['nc3']['completed'] is True and o['nc3']['exit_code'] == 0 and o['nc3']['fzp'],
        'nc3_network_is_recorded_source': o['nc3']['prepared_network_sha256'] == o['nc3']['source_network_sha256'] is not None,
        'b_seed_net_tuning_done': o['b']['seed'] == seed and o['b']['network_sha256'] == NET_SHA and o['b']['tuning_sha256'] == B_TUN_SHA and o['b']['sim_done'] and o['b']['sim_sec_9000'],
        'va_seed_net': o['va']['seed'] == seed and o['va']['network_sha256'] == NET_SHA,
    }
    return o


def sigset(d):
    return {os.path.basename(p): sha(p) for p in glob.glob(d + '/*.sig')}


def main(frz, out):
    frz = frz.replace('\\', '/').rstrip('/')
    res = {'frz_fo': frz}
    f = frz + '/FREEZE.json'
    d1, dfo = jl(FRZ1 + '/FREEZE.json'), jl(f)
    frz_sha = sha(f)
    res['freeze_fo'] = {'sha256': frz_sha, 'file_count': dfo['file_count'], 'total_bytes': dfo['total_bytes'], 'tree_sha256': dfo['tree_sha256'],
                        'git_head': dfo['git']['head'], 'git_branch': dfo['git']['branch'], 'git_status_entries': dfo['git']['status_entries'],
                        'git_status_sha256': dfo['git']['status_sha256'], 'source': dfo['source']}
    res['freeze_b1'] = {'sha256': sha(FRZ1 + '/FREEZE.json'), 'file_count': d1['file_count'], 'total_bytes': d1['total_bytes']}
    ov = jl(W + '/overlay_record.json')
    fo_tun_sha = ov.get('fo_config_sha256')
    for row in ov['files']:
        SOLO_SHA[row['rel']] = row['solo_sha256']
    SOLO_SHA['__b1_adapter__'] = d1['files'].get(CTRL + 'vissim_stackelberg_adapter.py')
    pre, post, frzd = jl(W + '/diff_src_preoverlay_vs_frzb1.json'), jl(W + '/diff_src_postoverlay_vs_frzb1.json'), jl(W + '/diff_frzfo_vs_frzb1.json')
    flog = txt(FOR + '/freeze.log')
    v1, v2 = txt(FOR + '/freeze_verify_1.txt'), txt(FOR + '/freeze_verify_2.txt')
    res['tree_checks'] = {
        'frz_b1_sha_unchanged': res['freeze_b1']['sha256'] == FRZ1_SHA,
        'source_preoverlay_equals_frz_b1': pre['ok'] and not pre['changed'] and not pre['extra'] and not pre['missing'],
        'overlay_record_pass': ov.get('pass') is True,
        'source_postoverlay_declared': post['ok'] and sorted(post['changed']) == sorted(CH13) and sorted(post['extra']) == sorted(EX5) and not post['missing'],
        'frz_fo_vs_frz_b1_declared': frzd['ok'] and sorted(frzd['changed']) == sorted(CH13) and sorted(frzd['extra']) == sorted(EX5) and not frzd['missing'],
        'frz_fo_files_are_solo_bytes': all(dfo['files'].get(r['rel']) == r['solo_sha256'] for r in ov['files']) and len(ov['files']) == 17,
        'frz_fo_config_is_overlay': dfo['files'].get(FO_TUN_REL) == fo_tun_sha is not None,
        'frz_fo_b_config_unchanged': dfo['files'].get(B_TUN_REL) == B_TUN_SHA,
        'runner_unchanged': dfo['files'].get(RUNREL) == d1['files'].get(RUNREL) == RUN_SHA,
        'network_unchanged': dfo['files'].get(NETREL) == d1['files'].get(NETREL) == NET_SHA,
        'git_same_head': dfo['git']['head'] == d1['git']['head'] == HEAD,
        'file_count_plus5': dfo['file_count'] == d1['file_count'] + 5,
        'freeze_ok_in_log': ('FREEZE_OK' in flog and frz_sha in flog),
        'freeze_verified_before_preflights': ('FREEZE_VERIFIED' in v1 and frz_sha in v1),
        'freeze_verified_after_preflights': ('FREEZE_VERIFIED' in v2 and frz_sha in v2),
        'fo_results_root_absent': not os.path.exists(FO_RUNS),
    }
    res['fo_config_sha256'] = fo_tun_sha
    res['preflights'] = [preflight(31, '', frz, frz_sha, fo_tun_sha), preflight(41, '', frz, frz_sha, fo_tun_sha),
                         preflight(43, '', frz, frz_sha, fo_tun_sha), preflight(31, 'b', frz, frz_sha, fo_tun_sha)]
    res['pairing'] = [pairing(s) for s in (31, 41, 43)]
    ref = sigset(frz + '/diagnostics/sdmpc_n31_20260924/network')
    sets = {'NC3_s%d' % s: sigset((NC3 % s) + '/prepared/network') for s in (31, 41, 43)}
    sets.update({'B_s%d' % s: sigset((BRUN % s) + '/network') for s in (31, 41, 43)})
    sets.update({'VA_s%d' % s: sigset((VA % s) + '/network') for s in (31, 41, 43)})
    res['sig_files'] = {'count_frz_fo': len(ref), 'equal_to_frz_fo': {k: v == ref for k, v in sets.items()}}
    res['sig_check'] = len(ref) == 42 and all(res['sig_files']['equal_to_frz_fo'].values())
    res['pass'] = (all(res['tree_checks'].values()) and all(p['pass'] for p in res['preflights'])
                   and all(all(x['checks'].values()) for x in res['pairing']) and res['sig_check'])
    json.dump(res, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('FREEZE_FO', json.dumps(res['freeze_fo']))
    print('TREE', json.dumps(res['tree_checks']))
    for p in res['preflights']:
        print('PREFLIGHT', p['label'], 'pass', p['pass'], 'wall', p.get('wall_sec'), json.dumps(p.get('checks')))
        if 'vs_b1' in p:
            print('  vs_b1 differing', json.dumps(sorted(p['vs_b1']['differing'])), 'undeclared', json.dumps(p['vs_b1']['undeclared_differing']))
    for x in res['pairing']:
        print('PAIRING s%d' % x['seed'], json.dumps(x['checks']), 'nc3_net', x['nc3']['source_network_sha256'][:16])
    print('SIG', res['sig_check'], json.dumps(res['sig_files']))
    print('FO_BUILD_PASS', res['pass'])


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
