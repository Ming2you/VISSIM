# FO overlay (2026-10-27 KST, user decision D-K9-113 = O2 "actuator scope only"). Writes ONLY inside <SRC> (= fo/source).
# 1) the 17 codex solo files (13 changed + 4 new, all evaluation/controllers) are copied byte for byte from the handoff copy
#    HO/original_code_dependencies/solo. Checks: every solo file sha == codex solo FREEZE (f55ecec3...) entry; every one of the
#    13 files currently in <SRC> == codex joint FREEZE (f980fcce...) entry == FRZ_B1 FREEZE entry (so the overlay replaces
#    exactly joint bytes); the 4 new files are absent in <SRC> and in FRZ_B1; after the copy each file sha == solo sha.
# 2) the FO config <SRC>/diagnostics/b0_v3c3/config_fo_v3c3.json = the B config (729640af...) with ONE added key
#    adapter.sdmpc_actuator_scope (value = deep copy of the codex freeway_only config cd193948... /adapter/sdmpc_actuator_scope),
#    serialized like the B config (json indent=2, ensure_ascii=False, CRLF, trailing CRLF; reproduces the B config bytes).
#    Checks: B config re-serialization == B bytes; adapter has no sdmpc_actuator_scope / sdmpc_information_scope before;
#    the baseline (green_times 68 + offsets 17) == the green_times/offsets of the B no-control commands t=1 and t=750 of
#    v3c3-s31/s41/s43 (seed taken from each run's provenance, not from the folder name); leaf diff new vs B = only
#    /adapter/sdmpc_actuator_scope/... ; sdmpc_information_scope absent; sdmpc_fixed_vsl unchanged (base 110).
# usage: python -B fo_overlay.py <SRC> <out_record.json>
import copy, hashlib, json, os, shutil, sys

HO = 'D:/VISSIM_handoff/20261024'
SOLO = HO + '/original_code_dependencies/solo'
SOLO_FREEZE = (HO + '/evidence/original_solo_FREEZE.json', 'f55ecec3bf442d5491b8f091abf800d05f5d2c1d76160dd44516ecf93b72f174')
JOINT_FREEZE = (HO + '/evidence/original_FREEZE.json', 'f980fcce97f4dfa207a39dfe5151e6b1c3c3775340a8ac70dac6fac40d45e2d0')
FRZ_B1 = 'D:/VISSIM-merge/k8_gate_trees/codexhandoff/b1/frozen/sdmpc31_a49981ff_202610261410'
FRZ_B1_FREEZE_SHA = '558de2c1b80799a9bedfb192b40b6f5cfa2775853b3431eb181f7b25beca10d1'
CX_FO_CONFIG = (SOLO + '/diagnostics/solo355_local_20261013/freeway_only_config.json', 'cd193948e7267c40373ea9bcd92013f7ffe34dff36438239113db58b7d433778')
B_CONFIG_REL = 'diagnostics/b0_v3c3/config_b0_v3c3.json'
B_CONFIG_SHA = '729640af754a90c8d7fbe8f81577b27bae02b86f1d504e18333c0fc99717f983'
FO_CONFIG_REL = 'diagnostics/b0_v3c3/config_fo_v3c3.json'
B_RUNS = 'D:/VISSIM_runs/20261026_codex_b_v3c3'
CTRL = 'evaluation/controllers/'
CHANGED13 = ['area_follower_objective.py', 'joint_owner_neighbors.py', 'runtime_setup.py', 'sdmpc.py', 'sdmpc_budget.py',
             'sdmpc_central.py', 'sdmpc_pfo.py', 'sdmpc_sequence.py', 'sdmpc_tangent.py', 'sdmpc_tangent_constraints.py',
             'sdmpc_tangent_surrogate.py', 'sdmpc_tangent_worker.py', 'vissim_stackelberg_adapter.py']
NEW4 = ['sdmpc_actuator_scope.py', 'sdmpc_regional_context.py', 'sdmpc_regional_contracts.py', 'sdmpc_regional_prototype.py']


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def pinned_json(p, want):
    got = sha(p)
    if got != want:
        raise SystemExit('PIN MISMATCH %s %s != %s' % (p, got, want))
    return json.load(open(p, encoding='utf-8-sig'))


def leaves(o, pre=''):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from leaves(v, pre + '/' + str(k))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from leaves(v, pre + '/' + str(i))
    else:
        yield pre, o


def dump_like_b(obj):
    return (json.dumps(obj, indent=2, ensure_ascii=False).replace('\n', '\r\n') + '\r\n').encode('utf-8')


def main(src, out):
    src = src.replace('\\', '/').rstrip('/')
    rec = {'src': src, 'files': [], 'checks': {}}
    solo_fz = pinned_json(*SOLO_FREEZE)['files']
    joint_fz = pinned_json(*JOINT_FREEZE)['files']
    b1_fz = pinned_json(FRZ_B1 + '/FREEZE.json', FRZ_B1_FREEZE_SHA)['files']
    ok = True
    # ---- 1) the 17 solo files
    for name in CHANGED13 + NEW4:
        rel = CTRL + name
        s = SOLO + '/' + rel
        d = src + '/' + rel
        s_sha = sha(s)
        row = {'rel': rel, 'kind': 'changed' if name in CHANGED13 else 'new', 'solo_sha256': s_sha,
               'solo_freeze_sha256': solo_fz.get(rel), 'joint_freeze_sha256': joint_fz.get(rel), 'frz_b1_sha256': b1_fz.get(rel)}
        row['src_before_sha256'] = sha(d) if os.path.exists(d) else None
        good = s_sha == solo_fz.get(rel)
        if name in CHANGED13:
            good = good and row['src_before_sha256'] == joint_fz.get(rel) == b1_fz.get(rel) and joint_fz.get(rel) is not None
        else:
            good = good and row['src_before_sha256'] is None and rel not in b1_fz and rel not in joint_fz
        row['pre_ok'] = good
        if good:
            shutil.copyfile(s, d)
            row['src_after_sha256'] = sha(d)
            row['post_ok'] = row['src_after_sha256'] == s_sha
        else:
            row['post_ok'] = False
        ok = ok and row['pre_ok'] and row['post_ok']
        rec['files'].append(row)
    rec['checks']['solo17_copied'] = ok and len(rec['files']) == 17
    # ---- 2) the FO config
    braw = open(src + '/' + B_CONFIG_REL, 'rb').read()
    bcfg = json.loads(braw.decode('utf-8'))
    rec['b_config_sha256'] = hashlib.sha256(braw).hexdigest()
    rec['checks']['b_config_sha'] = rec['b_config_sha256'] == B_CONFIG_SHA
    rec['checks']['b_config_reserialize_equal'] = dump_like_b(bcfg) == braw
    ad = bcfg['adapter']
    rec['checks']['b_has_no_scope_keys'] = 'sdmpc_actuator_scope' not in ad and 'sdmpc_information_scope' not in ad
    cx = pinned_json(*CX_FO_CONFIG)
    scope = copy.deepcopy(cx['adapter']['sdmpc_actuator_scope'])
    rec['checks']['scope_mode_freeway_only'] = scope.get('mode') == 'freeway_only' and set(scope) == {'mode', 'baseline'}
    base = scope['baseline']
    rec['checks']['scope_baseline_shape'] = set(base) == {'green_times', 'offsets'} and len(base['green_times']) == 68 and len(base['offsets']) == 17
    # baseline == B no-control commands t=1 and t=750, three seeds (seed from provenance)
    cmp = []
    for s in (31, 41, 43):
        run = B_RUNS + '/s%d/sdmpc' % s
        prov = json.load(open(run + '/run_provenance_sdmpc31_sdmpc9000_s%d.json' % s, encoding='utf-8-sig'))
        pseed = prov.get('seed')
        dec = run + '/decisions_sdmpc31_sdmpc9000_s%d' % pseed
        for T in (1, 750):
            a = json.load(open(dec + '/action_%06d.json' % T, encoding='utf-8-sig'))
            dg = max(abs(float(a['green_times'][k]) - float(v)) for k, v in base['green_times'].items())
            do = max(abs(float(a['offsets'][k]) - float(v)) for k, v in base['offsets'].items())
            same_keys = set(a['green_times']) == set(base['green_times']) and set(a['offsets']) == set(base['offsets'])
            cmp.append({'seed_dir': 's%d' % s, 'seed_provenance': pseed, 'T': T, 'controller': a.get('metadata', {}).get('controller'),
                        'has_sdmpc_state': 'sdmpc_state' in a.get('metadata', {}), 'max_abs_green_diff': dg, 'max_abs_offset_diff': do,
                        'same_keys': same_keys})
    rec['baseline_vs_b_nocontrol'] = cmp
    rec['checks']['baseline_equals_b_nocontrol'] = all(c['max_abs_green_diff'] == 0 and c['max_abs_offset_diff'] == 0 and c['same_keys']
                                                       and c['seed_provenance'] == int(c['seed_dir'][1:]) for c in cmp) and len(cmp) == 6
    fo = copy.deepcopy(bcfg)
    fo['adapter']['sdmpc_actuator_scope'] = scope
    fraw = dump_like_b(fo)
    dst = src + '/' + FO_CONFIG_REL
    if os.path.exists(dst):
        raise SystemExit('FO config exists already: ' + dst)
    if all(rec['checks'].values()):
        with open(dst, 'xb') as f:
            f.write(fraw)
        rec['fo_config_sha256'] = sha(dst)
        back = json.load(open(dst, encoding='utf-8'))
        la, lb = dict(leaves(bcfg)), dict(leaves(back))
        only_b, only_fo = sorted(set(la) - set(lb)), sorted(set(lb) - set(la))
        changed = sorted(k for k in set(la) & set(lb) if la[k] != lb[k])
        rec['leaf_diff_fo_vs_b'] = {'only_b': only_b, 'only_fo_count': len(only_fo), 'changed': changed,
                                    'only_fo_prefixes': sorted({'/'.join(k.split('/')[:3]) for k in only_fo})}
        rec['checks']['leaf_diff_only_scope'] = (not only_b and not changed and len(only_fo) == 86
                                                 and all(k.startswith('/adapter/sdmpc_actuator_scope/') for k in only_fo))
        rec['checks']['information_scope_absent'] = 'sdmpc_information_scope' not in back['adapter']
        rec['checks']['fixed_vsl_unchanged'] = back['adapter'].get('sdmpc_fixed_vsl') == bcfg['adapter'].get('sdmpc_fixed_vsl') == {'start_sec': 0, 'base_kmh': 110, 'zone_kmh': {}}
        rec['checks']['name_unchanged'] = back.get('name') == bcfg.get('name')
        rec['fo_config_bytes'] = len(fraw)
    else:
        rec['fo_config_sha256'] = None
    rec['pass'] = all(rec['checks'].values())
    json.dump(rec, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('OVERLAY', 'pass=%s' % rec['pass'], json.dumps(rec['checks']), 'fo_config_sha256=%s' % rec.get('fo_config_sha256'))
    return 0 if rec['pass'] else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1], sys.argv[2]))
