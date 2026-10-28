# -*- coding: utf-8 -*-
"""VERIFY_A1_B0: B0 재핀 목록·코드 고침 독립 점검 (읽기만).

1) B 설정(config_b0_v3c3.json) 대 codex 튜닝(A1 동결본 optimized_config.json) 잎 대조:
   바뀐/더한/지운 잎을 B0.md §2.2 의 경로 목록(LISTED)에 묶고, 목록 밖 변경·변경 없는 목록 항목을 셈.
2) 주요 키 값 확인, 그룹키 대조 설정 대 B 설정 잎 대조.
3) 코드 트리: B0T/code 대 A1 동결 트리(파일 sha256), 고친·더한·빠진 파일 수와 고친 파일 sha 앞 12자.
4) FRZ_B0 FREEZE.json sha, lane plant manifest·reference config 대조.
5) V-A 세 시드 T=900 상태 파일 있음, 직전 명령(action_000750.json)의 metadata.sdmpc_state 유무.
"""
import json, os, sys, hashlib

OUT = sys.argv[1]
B0T = 'D:/VISSIM-merge/k8_gate_trees/codexhandoff/b0'
CODE = B0T + '/code'
A1F = 'D:/VISSIM_runtime/20261025_codex_a1/frozen/sdmpc31_a49981ff_202610251820'
FRZ = B0T + '/frozen/sdmpc31_a49981ff_202610260258'
CODEX_TUNING = A1F + '/diagnostics/repin_v3c3_review_20261001/urban_rm269/aggregate270/native413_adopted355/optimized_config.json'
B_CFG = CODE + '/diagnostics/b0_v3c3/config_b0_v3c3.json'
G_CFG = CODE + '/diagnostics/b0_v3c3/config_b0_v3c3_groupkeys.json'
VA = 'D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s%d/decisions_sdmpc31_v3c3_k92va_s%d'
LISTED = [
    '/control_area_objective/membership_path', '/route_contract_path',
    '/observation/physical_branch_projection/source/network/path', '/observation/physical_branch_projection/source/network/sha256',
    '/freeway/lane_plant',
    '/urban/capacity/head_free_service', '/urban/movements/dynamic_physical_route_topology', '/urban/shared_approach',
    '/urban/physical_ramp_branches', '/urban/known_wout_route_evidence/path', '/urban/known_wout_route_evidence/sha256',
    '/urban/movements/native_input_signal_authority', '/urban/sc2001_corridor', '/urban/native_internal_inputs',
    '/observation/physical_support_repair', '/urban/route_choice_corridor/evidence_paths',
    '/urban/movements/physical_route_topology', '/urban/movements/physical_phase_authority',
    '/urban/capacity/head_resource_contract', '/regular_alias_pool', '/urban/queue/head_lane_contract',
    '/urban/arrival/kinematic_contract', '/freeway/offramp_route_inventory',
    '/adapter/sdmpc_fixed_vsl', '/urban/calibrated_aggregate',
    '/calibration_override/prediction/local_ramp_arrival_forecast/queue_drain_horizon_sec_by_ramp',
    '/calibration_override/prediction/local_ramp_arrival_forecast/max_vph_by_ramp',
    '/calibration_override/prediction/local_ramp_arrival_forecast/strict_ramp_keys',
    '/runtime/decision_error_policy', '/runtime/decision_timeout_sec',
]
B0MD_PATCH = {  # B0.md §3 표: 파일 끝 이름 -> (codex 앞 12, b0 앞 12)
    'physical_movement_routes.py': ('8a1a70b1aead', '3b5df9f72eff'),
    'control_area_objective.py': ('71222de0e46d', 'e71a88c64857'),
    'lane_offramp_runtime.py': ('9203f59685eb', 'f07f7e1f499d'),
    'control_hold.py': ('68c19eb53fa2', 'bf3c28a42324'),
    'run_closedloop3000.ps1': ('8e95423b4b3c', '8b2da855da5b'),
}


def sha(p):
    # r2 고침(꼴만): Windows 260자 넘는 경로는 긴 경로 접두(\\?\)로 연다(값 판단과 무관).
    q = os.path.abspath(p).replace('/', os.sep)
    pre = os.sep * 2 + '?' + os.sep
    if len(q) >= 240 and not q.startswith(pre):
        q = pre + q
    h = hashlib.sha256()
    with open(q, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def jload(p):
    with open(p, 'rb') as f:
        return json.loads(f.read().decode('utf-8-sig'))


def flatten(x, p='', out=None):
    if out is None:
        out = {}
    if isinstance(x, dict):
        if not x:
            out[p] = {}
        for k, v in x.items():
            flatten(v, p + '/' + str(k), out)
    elif isinstance(x, list):
        if not x:
            out[p] = []
        for i, v in enumerate(x):
            flatten(v, p + '/%d' % i, out)
    else:
        out[p] = x
    return out


def get(d, path):
    cur = d
    for k in path.strip('/').split('/'):
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return '<<absent>>'
    return cur


def leafdiff(a, b):
    fa, fb = flatten(a), flatten(b)
    ch = sorted(k for k in set(fa) & set(fb) if fa[k] != fb[k])
    return ch, sorted(set(fb) - set(fa)), sorted(set(fa) - set(fb)), fa, fb


def under(k, listed):
    for p in listed:
        if k == p or k.startswith(p + '/'):
            return p
    return None


def walk_files(root):
    out = {}
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in ('__pycache__', '.git')]
        for f in fn:
            if f.endswith('.pyc'):
                continue
            full = os.path.join(dp, f)
            out[os.path.relpath(full, root).replace('\\', '/')] = full
    return out


def main():
    res = {}
    codex = jload(CODEX_TUNING)
    bcfg = jload(B_CFG)
    gcfg = jload(G_CFG)
    res['sha'] = {'codex_tuning': sha(CODEX_TUNING), 'b_cfg': sha(B_CFG), 'g_cfg': sha(G_CFG)}
    ch, add, rem, fa, fb = leafdiff(codex, bcfg)
    res['leafdiff_counts'] = {'changed': len(ch), 'added': len(add), 'removed': len(rem)}
    allk = [('changed', k) for k in ch] + [('added', k) for k in add] + [('removed', k) for k in rem]
    grouped = {}
    outside = []
    for kind, k in allk:
        p = under(k, LISTED)
        if p is None:
            outside.append([kind, k])
        else:
            grouped.setdefault(p, {'changed': 0, 'added': 0, 'removed': 0})[kind] += 1
    res['listed_with_change'] = grouped
    res['listed_without_change'] = [p for p in LISTED if p not in grouped]
    res['changes_outside_listed'] = outside[:200]
    res['n_changes_outside_listed'] = len(outside)
    keyvals = {}
    for p in ('/adapter/sdmpc_fixed_vsl', '/urban/calibrated_aggregate', '/runtime/decision_error_policy',
              '/runtime/decision_timeout_sec', '/freeway/lane_plant', '/execution/signal_vbs_config',
              '/calibration_override/prediction/local_ramp_arrival_forecast'):
        keyvals[p] = {'codex': get(codex, p), 'b': get(bcfg, p), 'groupkeys': get(gcfg, p)}
    res['key_values'] = keyvals
    res['b_cfg_text_has_calibrated_aggregate'] = 'calibrated_aggregate' in open(B_CFG, encoding='utf-8-sig').read()
    ca = get(codex, '/urban/calibrated_aggregate')
    res['codex_calibrated_aggregate'] = ca
    # codex calibrated_aggregate 가 가리키는 파일 sha
    cand = []
    if isinstance(ca, str):
        cand.append(ca)
    elif isinstance(ca, dict):
        for k, v in flatten(ca).items():
            if isinstance(v, str) and v.endswith('.json'):
                cand.append(v)
    res['codex_calibrated_aggregate_files'] = {c: (sha(os.path.join(A1F, c)) if os.path.isfile(os.path.join(A1F, c)) else 'missing') for c in cand}
    gch, gadd, grem, _, _ = leafdiff(bcfg, gcfg)
    res['groupkeys_vs_b'] = {'changed': gch, 'added': gadd, 'removed': grem}
    # 트리
    fb0 = walk_files(CODE)
    fa1 = walk_files(A1F)
    common = set(fb0) & set(fa1)
    mod = sorted(k for k in common if sha(fb0[k]) != sha(fa1[k]))
    res['tree'] = {'n_b0': len(fb0), 'n_a1frozen': len(fa1), 'modified': mod,
                   'modified_sha12': {k: [sha(fa1[k])[:12], sha(fb0[k])[:12]] for k in mod},
                   'n_added': len(set(fb0) - set(fa1)), 'added_top': sorted(set(fb0) - set(fa1))[:120],
                   'n_only_in_a1frozen': len(set(fa1) - set(fb0)), 'only_in_a1frozen': sorted(set(fa1) - set(fb0))[:40]}
    chk = {}
    for k in mod:
        base = k.rsplit('/', 1)[-1]
        if base in B0MD_PATCH:
            chk[k] = {'claim': B0MD_PATCH[base], 'mine': [sha(fa1[k])[:12], sha(fb0[k])[:12]],
                      'match': B0MD_PATCH[base] == (sha(fa1[k])[:12], sha(fb0[k])[:12])}
    res['patch_sha_check'] = chk
    # FRZ
    fz = FRZ + '/FREEZE.json'
    res['frz'] = {'freeze_json_sha': sha(fz) if os.path.isfile(fz) else 'missing'}
    try:
        fj = jload(fz)
        res['frz']['freeze_json_keys'] = list(fj.keys())[:30]
        for k in ('file_count', 'files', 'n_files', 'count'):
            if k in fj:
                v = fj[k]
                res['frz']['freeze_' + k] = len(v) if isinstance(v, (list, dict)) else v
    except Exception as e:
        res['frz']['err'] = str(e)
    res['frz']['n_files_on_disk_excl_git'] = len(walk_files(FRZ))
    # 모든 B0 고친 파일이 FRZ 에 같은 sha 로 있는지
    res['frz']['modified_equal_in_frz'] = {k: (os.path.isfile(FRZ + '/' + k) and sha(FRZ + '/' + k) == sha(fb0[k])) for k in mod}
    # lane plant
    lp_b = CODE + '/diagnostics/b0_v3c3/lane_plant/candidate_manifest.json'
    rc_b = CODE + '/diagnostics/b0_v3c3/lane_plant/reference_config_eval036_sign18.json'
    res['lane_plant'] = {'manifest_sha': sha(lp_b), 'refcfg_sha': sha(rc_b)}
    lp_codex_path = get(codex, '/freeway/lane_plant')
    if isinstance(lp_codex_path, str) and os.path.isfile(os.path.join(A1F, lp_codex_path)):
        mc = jload(os.path.join(A1F, lp_codex_path))
        mb = jload(lp_b)
        c2, a2, r2, fmc, fmb = leafdiff(mc, mb)
        res['lane_plant']['manifest_diff'] = {'changed': [[k, str(fmc[k])[:120], str(fmb[k])[:120]] for k in c2],
                                              'added': a2, 'removed': r2}
        # reference config: codex manifest 안에서 reference 경로 찾기
        refs = [(k, v) for k, v in fmc.items() if isinstance(v, str) and v.endswith('.json') and ('eval' in v or 'reference' in k.lower())]
        res['lane_plant']['codex_ref_candidates'] = refs[:10]
        for k, v in refs:
            p = os.path.join(A1F, v)
            if os.path.isfile(p) and ('reference' in k.lower() or 'eval_036' in v or 'eval036' in v):
                rc = jload(p)
                c3, a3, r3, f1, f2 = leafdiff(rc, jload(rc_b))
                res['lane_plant']['refcfg_vs_' + k] = {'src_sha': sha(p), 'changed': [[x, f1[x], f2[x]] for x in c3][:20],
                                                       'added': a3[:20], 'removed': r3[:20]}
    # V-A T=900
    va = {}
    for s in (31, 41, 43):
        d = VA % (s, s)
        st = os.path.isfile(d + '/state_000900.json')
        prev = d + '/action_000750.json'
        has = None
        ctrl = None
        if os.path.isfile(prev):
            j = jload(prev)
            has = 'sdmpc_state' in j.get('metadata', {})
            ctrl = j.get('metadata', {}).get('controller')
        va[s] = {'state_000900': st, 'prev750_exists': os.path.isfile(prev), 'prev750_has_sdmpc_state': has, 'prev750_controller': ctrl}
    res['va_t900'] = va
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(res, f, ensure_ascii=False, indent=1, default=str)
    print(json.dumps({'leafdiff_counts': res['leafdiff_counts'], 'n_listed_changed': len(grouped),
                      'listed_without_change': res['listed_without_change'], 'n_outside': len(outside),
                      'tree': {k: res['tree'][k] for k in ('n_b0', 'n_a1frozen', 'n_added', 'n_only_in_a1frozen')},
                      'modified': mod, 'patch_sha_check': chk, 'frz': res['frz'], 'va_t900': va}, ensure_ascii=False, default=str))


if __name__ == '__main__':
    main()
