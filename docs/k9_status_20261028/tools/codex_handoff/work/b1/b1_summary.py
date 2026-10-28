# B1 summary (2026-10-26, D-K9-90). Descriptive checks, written before the chain runs. Read-only.
# Tree: pre-edit source == FRZ_B0 (0 diff); post-edit source vs FRZ_B0 = runner only; FRZ_B1 FREEZE.json vs FRZ_B0 FREEZE.json =
#       runner only, same git head/branch/status sha; FRZ_B1 runner sha == edited sha; freeze log FREEZE_OK; verify before and after
#       the preflights FREEZE_VERIFIED with the FRZ_B1 sha; seat logic test N=0..3 allowed, N=4..6 refused.
# Preflights s31/s41/s43 (same checks as gate 1, g1_summary_r2.py preflight(), with the FRZ_B1 freeze pin) + StallSec 3600 seen in
#       the watchdog child command line and in the runner status 'arguments' at stage preflight; provenance compared leaf by leaf
#       with the gate-1 (FRZ_B0) preflight of the same seed after replacing the two tree roots and the two results roots.
# usage: python -B b1_summary.py <FRZ_B1> <out.json>
import hashlib, json, os, re, sys
W = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/')
B1 = 'D:/VISSIM-merge/k8_gate_trees/codexhandoff/b1'
G1 = 'D:/VISSIM-merge/k8_gate_trees/codexhandoff/gate1'
FRZ0 = 'D:/VISSIM-merge/k8_gate_trees/codexhandoff/b0/frozen/sdmpc31_a49981ff_202610260258'
FRZ0_SHA = '853d1c4fb97ed3de4cf62a409b06b9001648ce56171e2ed826236bdddb1506c6'
RUNREL = 'diagnostics/sdmpc_n31_20260924/integration_20260926/run_closedloop3000.ps1'
NET_SHA = '3de889f0257d998bed50611f798ea388bcf69396dbc40e5726b1e88ebdd31c2e'
TUN_SHA = '729640af754a90c8d7fbe8f81577b27bae02b86f1d504e18333c0fc99717f983'
PLANT_SHA = '1184249889cc8ceeb0e730176ea058cf5a7e53aa98732bbb14e0dd113411f25c'
DET_SHA = '108debbb4b021796b195927ba2140dafab571e1d976734190f5d8f5bd255cfbc'


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


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


def preflight(seed, frz1, frz1_sha):
    lab = 's%d' % seed
    root, w = B1 + '/runner_preflight/' + lab, B1 + '/runner_preflight/_wrapper/' + lab
    r = {'label': lab, 'seed': seed}
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
    obs = p.get('observation') or {}
    r['network_sha256'] = p['files']['network']['sha256']
    r['tuning_sha256'] = (p['files'].get('tuning') or {}).get('sha256')
    r['freeze_pin'], r['plant_manifest'], r['detectors'] = obs.get('freeze'), obs.get('plant_manifest'), obs.get('detectors')
    r['seed_in_provenance'], r['sim_period_sec'], r['controller'] = p.get('seed'), p.get('sim_period_sec'), p.get('controller')
    r['workspace_root'], r['startup_stall_sec'] = p.get('workspace_root'), p.get('startup_stall_sec')
    det = r['detectors']
    r['checks'] = {
        'exit0': r['runner_exit'] == 0,
        'freeze_verified_frz_b1': bool(m) and m.group(2) == frz1_sha and os.path.normcase(os.path.dirname(m.group(1))) == os.path.normcase(frz1.replace('/', '\\')),
        'network_sha': r['network_sha256'] == NET_SHA,
        'hold_policy_env': r['hold_env'] == {'RW_DECISION_ERROR_POLICY': 'hold_previous_on_exception', 'RW_DECISION_HOLD_PREVIOUS': '1', 'RW_DECISION_TIMEOUT_SEC': '0'},
        'tuning_sha': r['tuning_sha256'] == TUN_SHA,
        'freeze_pin_frz_b1': isinstance(r['freeze_pin'], dict) and r['freeze_pin'].get('sha256') == frz1_sha,
        'plant_manifest_pin': isinstance(r['plant_manifest'], dict) and r['plant_manifest'].get('sha256') == PLANT_SHA,
        'detector_pin': isinstance(det, dict) and det.get('sha256') == DET_SHA and det.get('rows') == 294,
        'controller_wu_link': r['controller'] == 'wu-link',
        'seed': r['seed_in_provenance'] == seed, 'sim_period_9000': r['sim_period_sec'] == 9000,
        'workspace_root_frz_b1': os.path.normcase(str(r['workspace_root'])) == os.path.normcase(frz1.replace('/', '\\')) or str(r['workspace_root']).replace('\\', '/').lower() == frz1.lower(),
        'no_empty_rw_value': not r['env_empty_values'] or r['env_empty_values'] == ['RW_OBS150_GT'],
        'stall_3600_watchdog_cmdline': r['stall_in_watchdog_cmdline'] == ['3600'],
        'stall_3600_status_arguments': r['stall_in_status_arguments'] == ['3600'],
        'status_preflight_complete': r['status_stage'] == 'preflight_complete',
    }
    r['pass'] = all(r['checks'].values())
    # leaf compare with the gate-1 (FRZ_B0) preflight provenance of the same seed
    g = G1 + '/runner_preflight/%s/sdmpc/preflight/run_provenance_sdmpc31_sdmpc9000_s%d.json' % (lab, seed)
    if os.path.exists(g):
        roots0 = [(FRZ0, '<FRZ>'), (G1 + '/runner_preflight/' + lab, '<RES>')]
        roots1 = [(frz1, '<FRZ>'), (B1 + '/runner_preflight/' + lab, '<RES>')]
        a = {k: norm(v, roots0) for k, v in leaves(jl(g))}
        b = {k: norm(v, roots1) for k, v in leaves(p)}
        diff = sorted(k for k in a.keys() & b.keys() if a[k] != b[k])
        r['vs_gate1'] = {'gate1_provenance': g, 'gate1_sha256': sha(g), 'leaves_a': len(a), 'leaves_b': len(b),
                         'only_gate1': sorted(a.keys() - b.keys()), 'only_b1': sorted(b.keys() - a.keys()),
                         'differing': {k: [a[k], b[k]] for k in diff}}
    return r


def main(frz1, out):
    frz1 = frz1.replace('\\', '/').rstrip('/')
    res = {'frz_b1': frz1}
    f1 = frz1 + '/FREEZE.json'
    d0, d1 = jl(FRZ0 + '/FREEZE.json'), jl(f1)
    frz1_sha = sha(f1)
    res['freeze_b1'] = {'sha256': frz1_sha, 'file_count': d1['file_count'], 'total_bytes': d1['total_bytes'], 'tree_sha256': d1['tree_sha256'],
                        'git_head': d1['git']['head'], 'git_status_entries': d1['git']['status_entries'], 'git_status_sha256': d1['git']['status_sha256'],
                        'source': d1['source']}
    res['freeze_b0'] = {'sha256': sha(FRZ0 + '/FREEZE.json'), 'file_count': d0['file_count'], 'total_bytes': d0['total_bytes'],
                        'git_status_sha256': d0['git']['status_sha256']}
    ed = jl(W + '/edit_record.json')
    pre, post, frzd = jl(W + '/diff_src_preedit_vs_frzb0.json'), jl(W + '/diff_src_postedit_vs_frzb0.json'), jl(W + '/diff_frzb1_vs_frzb0.json')
    seat = jl(W + '/seat_test_b1.json')
    seat_ok = [x['outcome'] for x in seat['results']]
    flog = txt(B1 + '/freeze.log')
    v1, v2 = txt(B1 + '/freeze_verify_1.txt'), txt(B1 + '/freeze_verify_2.txt')
    res['tree_checks'] = {
        'frz_b0_sha_unchanged': res['freeze_b0']['sha256'] == FRZ0_SHA,
        'source_preedit_equals_frz_b0': pre['ok'] and not pre['changed'],
        'source_postedit_only_runner': post['ok'] and post['changed'] == [RUNREL],
        'frz_b1_only_runner_vs_frz_b0': frzd['ok'] and frzd['changed'] == [RUNREL],
        'runner_b0_sha': d0['files'][RUNREL] == ed['sha256_before'],
        'runner_b1_sha_is_edited': d1['files'][RUNREL] == ed['sha256_after'],
        'git_same_head_branch_status': (d1['git']['head'], d1['git']['branch'], d1['git']['status_sha256']) == (d0['git']['head'], d0['git']['branch'], d0['git']['status_sha256']),
        'file_count_same': d1['file_count'] == d0['file_count'],
        'freeze_ok_in_log': ('FREEZE_OK' in flog and frz1_sha in flog),
        'freeze_verified_before_preflights': ('FREEZE_VERIFIED' in v1 and frz1_sha in v1),
        'freeze_verified_after_preflights': ('FREEZE_VERIFIED' in v2 and frz1_sha in v2),
        'seat_logic_0to3_allowed_4to6_refused': seat_ok[:4] == ['allowed'] * 4 and all(o.startswith('refused') for o in seat_ok[4:]) and len(seat_ok) == 7,
        'seat_test_on_b1_runner': seat['runner_sha256'] == ed['sha256_after'],
    }
    res['runner'] = {'sha256_b0': ed['sha256_before'], 'sha256_b1': ed['sha256_after'], 'lines_b0': ed['lines_before'], 'lines_b1': ed['lines_after']}
    res['preflights'] = [preflight(s, frz1, frz1_sha) for s in (31, 41, 43)]
    res['pass'] = all(res['tree_checks'].values()) and all(p['pass'] for p in res['preflights'])
    json.dump(res, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('FREEZE_B1', json.dumps(res['freeze_b1']))
    print('TREE', json.dumps(res['tree_checks']))
    for p in res['preflights']:
        print('PREFLIGHT', p['label'], 'pass', p['pass'], 'wall', p.get('wall_sec'), json.dumps(p.get('checks')))
        if 'vs_gate1' in p:
            print('  vs_gate1 differing', json.dumps(sorted(p['vs_gate1']['differing'])), 'only_gate1', len(p['vs_gate1']['only_gate1']), 'only_b1', len(p['vs_gate1']['only_b1']))
    print('B1_PASS', res['pass'])


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
