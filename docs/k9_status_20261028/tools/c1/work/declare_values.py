"""C1 declaration values (amendment C1, 2026-10-27).  Read-only inputs, deterministic transforms only.

Inputs (sha-checked): GWT8 blobs at c20aff1d (`git show`), the codex B config CFG_B and the B0 Omega701 files
in FRZ_B1 (read only), the READBACK K7 outputs (sha only).  No run result data is read.
Writes ONLY under OUT (this scratch folder `declared/`): the reference bytes of the three new C1 evidence files
(head_service_fwe_c1.json, omega701_v3c3_bundle.json, plant_n31_v2_omega701.json), the c1_port section, the
closed lists (added links, provenance-only referrers, chain leaves, state lists) and SUMMARY.json.
Serialisation of every written JSON = codex prepare_next.py data(): json.dumps(x, ensure_ascii=False, indent=2,
allow_nan=False) + '\n', UTF-8, LF (prepare_next.py:11).
"""
import copy
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

GWT8 = 'D:/VISSIM-merge/sim3-n31-k8'
REV = 'c20aff1d7bf0c432cb4f20e2922bd406d857aa5d'
FRZ = Path('D:/VISSIM-merge/k8_gate_trees/codexhandoff/b1/frozen/sdmpc31_a49981ff_202610261410')
B0 = FRZ / 'diagnostics/b0_v3c3'
RB = Path(__file__).resolve().parents[2] / 'readback/out'
OUT = Path(__file__).resolve().parents[1] / 'declared'

CFG_B_SHA = '729640af754a90c8d7fbe8f81577b27bae02b86f1d504e18333c0fc99717f983'
OUC_SHA = 'c8e3ee2c99b66c255b2279f0aa18eaafc18d4c7689e59e260109fac3b7d71866'
MANIFEST_SHA = 'b119d6d90081ac0ffabef45e02c189055d2f3c6280c2f65b2ce806730537098f'
OMEGA635 = ('diagnostics/sdmpc_n31_20260924/scenario/control_area_membership_213a5d.json',
            '30abb1db4f549068cb7069971c60e7ade8205a882c7999a0d0f2ede4460e5f85')
NETWORK_SHA = '3de889f0257d998bed50611f798ea388bcf69396dbc40e5726b1e88ebdd31c2e'
B0_DIRS = {'omega701': 'diagnostics/b0_v3c3/omega701', 'pack': 'diagnostics/b0_v3c3/evidence',
           'c1': 'diagnostics/sdmpc_n31_20260924/c1/evidence'}
METERS = ('RM_C10639', 'RM_C10681', 'RM_C10490', 'RM_C10484')


def data(x):
    return (json.dumps(x, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf8')


def sha(b):
    return hashlib.sha256(b).hexdigest()


def canon_sha(x):
    return sha(json.dumps(x, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf8'))


def blob(path):
    return subprocess.run(['git', '-C', GWT8, 'show', REV + ':' + path], capture_output=True, check=True).stdout


def need(cond, msg):
    if not cond:
        raise SystemExit('DECLARE_STOP: ' + msg)


def write(name, payload):
    p = OUT / name
    with open(p, 'xb') as f:          # exclusive create: never overwrite a declared file
        f.write(payload)
    return sha(payload)


def main():
    OUT.mkdir(parents=True, exist_ok=False)
    summary = {'schema': 'c1-declared-values/v1', 'gwt8_rev': REV, 'files': {}}

    # ---- 1. Omega701 files of FRZ_B1 (B0 layout), byte shas --------------------------------------------
    omega = {'membership.json': '9bb740b321d28162c0e849b56e0e618adf4ec800caa60476c96f3fc469318d51',
             'route_contract.json': '08fec9c71b1c612ad3f95555173e372fd2f9428ef58d7010246a00bf0b77063a'}
    pack = {'native_input_1083_signal_authority_ver2_022a16.json': ('8f65b25c7af1e2f4f83e07890bab90b07d0fe0af283180e3d51052757670a3a1', ['/urban/movements/native_input_signal_authority']),
            'native_internal_inputs_c92673.json': ('a23a13632f20cdb81824a406e0c3a83fa9b88cd3eb7f8d32fb33ce318fd820d8', ['/urban/native_internal_inputs']),
            'physical_projection_support_635_proposal_ec2393.json': ('7d092b3db6e4107b47ecf751c60196e11a32120dc722d9221c1fb888d447faec', ['/observation/physical_support_repair']),
            'sc2001_corridor_nc13_2d0c62.json': ('cc5e6863ca8f9ade6f47689db0ca83744b2ce1186f0d56a92ca8f55074a00c62', ['/urban/sc2001_corridor']),
            'route_choice_corridor_sc1004_calibrated_9e6354.json': ('7067a6610b052830885bc56726d944f05fac48daf43dda8ba06fff4750f63716', ['/urban/route_choice_corridor/evidence_paths/0']),
            'route_choice_corridor_1128_ver2_0fd58c.json': ('d92f90aacb24f44849826ab0c9ed41dd5574a596d27c6d6637ea709e52b2f4b1', ['/urban/route_choice_corridor/evidence_paths/1']),
            'route_choice_corridor_1099_sc15_calibrated_e02d01.json': ('8e40f046558d921868bc2f5db435ba131eece073e41052107496f6a541620306', ['/urban/route_choice_corridor/evidence_paths/2']),
            'route_choice_corridor_1100_sc15_calibrated_05ed35.json': ('59fa5c59d58c97c7170de273484ebfb002b158b9f6a2325b23accc3a260c850e', ['/urban/route_choice_corridor/evidence_paths/3'])}
    for name, digest in omega.items():
        need(sha((B0 / 'omega701' / name).read_bytes()) == digest, 'FRZ_B1 omega701 ' + name)
    for name, (digest, _) in pack.items():
        need(sha((B0 / 'evidence' / name).read_bytes()) == digest, 'FRZ_B1 evidence ' + name)

    # c20aff1d tuning pointers and their present targets (before)
    ouc_bytes = blob('diagnostics/sdmpc_n31_20260924/config_n31_v2.json')
    need(sha(ouc_bytes) == OUC_SHA, 'OUC sha')
    ouc = json.loads(ouc_bytes)

    def at(doc, ptr):
        x = doc
        for part in ptr.strip('/').split('/'):
            x = x[int(part)] if isinstance(x, list) else x[part]
        return x

    # ---- 2. Omega701 lane plant manifest = prepare_next rewrite of b119d6d9 /membership ----------------
    man_bytes = blob('diagnostics/sdmpc_n31_20260924/plant_n31_v2.json')
    need(sha(man_bytes) == MANIFEST_SHA, 'manifest sha')
    man = json.loads(man_bytes)
    need(man['membership'] == {'path': OMEGA635[0], 'sha256': OMEGA635[1]}, 'manifest membership pin')
    new_man = copy.deepcopy(man)
    new_man['membership'] = {**man['membership'], 'path': B0_DIRS['omega701'] + '/membership.json',
                             'sha256': omega['membership.json']}
    man_out = data(new_man)
    summary['manifest'] = {'original_reserialised_equal_bytes': data(man) == man_bytes,
                           'json_diff_pointers': sorted(['/membership/path', '/membership/sha256'])}
    man_sha = write('plant_n31_v2_omega701.json', man_out)
    summary['files']['plant_n31_v2_omega701.json'] = man_sha

    # ---- 3. Bundle list (names + roles + sha + tuning pointers; no path strings) -----------------------
    entries = [
        {'role': 'membership', 'dir': 'omega701', 'name': 'membership.json', 'sha256': omega['membership.json'],
         'tuning_pointers': ['/control_area_objective/membership_path']},
        {'role': 'route_contract', 'dir': 'omega701', 'name': 'route_contract.json', 'sha256': omega['route_contract.json'],
         'tuning_pointers': ['/control_area_objective/route_contract_path']},
    ]
    for name, (digest, ptrs) in pack.items():
        entries.append({'role': 'pack', 'dir': 'pack', 'name': name, 'sha256': digest, 'tuning_pointers': ptrs})
    entries.append({'role': 'lane_plant_manifest', 'dir': 'c1', 'name': 'plant_n31_v2_omega701.json',
                    'sha256': man_sha, 'tuning_pointers': ['/freeway/lane_plant']})
    before = {}
    for e in entries:
        for ptr in e['tuning_pointers']:
            old = at(ouc, ptr)
            before[ptr] = {'name': old.rsplit('/', 1)[-1], 'sha256': sha(blob(old))}
    bundle = {
        'schema': 'c1-omega701-bundle/v1',
        'decision': 'D-K9-94 (amendment C1): Omega701 approaches (66 links) by name + sha',
        'network_sha256': NETWORK_SHA,
        'counts': {'inside_total': 701, 'outside_total': 535, 'controlled_intersection_added': 66,
                   'previous_inside_links': 635},
        'entries': entries,
        'before_c20aff1d': before,
        'not_rewritten': [
            {'name': 'sc1001eb_evidence_v3c3_20261004.json', 'pointer': '/inputs/support',
             'reason': 'K8b builder provenance; runtime reads only /inputs/g2_inpx/extract_sha12 (stopline_approach.py:343)'},
            {'name': 'wout_side_handoff_v3c3_20261009.json', 'pointer': '/derivation/corridor_evidence',
             'reason': 'K9-1 W2-A builder provenance; runtime reads only /values (runtime_setup.py:199-229)'},
            {'name': 'head_service_resource_contract_7b2da6.json', 'pointer': '/resources/10619/proof',
             'reason': 'HSR proof is read at its own pinned bytes (head_service_resources.py:15-19), file unchanged'},
        ],
        'rule': {'membership_builder': {'name': 'build_control_area_membership.py', 'function': 'expand_controlled_intersection_area',
                                        'sha256': '567bca5f4e4f955a5a27e762f4f242769dfa433bcffbc4b454aa75320f90dae5'},
                 'rebind': {'name': 'prepare_next.py', 'lines': '21-56 routes, 57-108 rebinding',
                            'sha256': '525897ada99ec2859bb83246c2dc95fb06e16a0d08000032ddc8bf444b8d3625'},
                 'source_bytes': 'FRZ_B1 sdmpc31_a49981ff_202610261410 diagnostics/b0_v3c3 (B run evidence)'},
    }
    bundle_sha = write('omega701_v3c3_bundle.json', data(bundle))
    summary['files']['omega701_v3c3_bundle.json'] = bundle_sha

    # ---- 4. Head service evidence (codex curves, rule keep_green_10) ------------------------------------
    cfgb_bytes = (B0 / 'config_b0_v3c3.json').read_bytes()
    need(sha(cfgb_bytes) == CFG_B_SHA, 'CFG_B sha')
    cfgb = json.loads(cfgb_bytes)
    curves = {m: cfgb['freeway']['physical_ramp_head_service_veh_per_cycle'][m] for m in METERS}
    need(set(cfgb['freeway']['physical_ramp_head_service_veh_per_cycle']) == set(METERS), 'CFG_B head table meters')
    installed, dropped = {}, {}
    for m, curve in curves.items():
        need(list(curve) == [str(g) for g in range(2, 11)], 'curve keys ' + m)
        table = {'0': 0., **{g: n * 3600 / 10 for g, n in curve.items()}}      # CX LPR:618 / OU PRB:86 expression
        top = max(table.values())
        group = [g for g, s in table.items() if s == top]
        need(group == ['9', '10'], 'top group ' + m)
        rest = {}
        for g, s in table.items():
            rest.setdefault(s, []).append(g)
        need(all(len(v) == 1 for s, v in rest.items() if s != top), 'other equal-service groups ' + m)
        installed[m] = {g: s for g, s in table.items() if g != '9'}
        dropped[m] = {'9': '10'}
    rb = {name: sha((RB / name).read_bytes()) for name in ('discharge.json', 'headcurve.json')}
    need(rb == {'discharge.json': '34220b5c7fc30cbcba9fa0f2def206301f08212a9d2a62200ae1b7f021e90a3d',
                'headcurve.json': '1978197cdf611e1e90f6d99eb9681de7224b3c03830a4b4f7b502a50f0b33bf8'}, 'READBACK K7 shas')
    head = {
        'schema': 'c1-head-service-fwe/v1',
        'decision': 'D-K9-94 Q4 (a): codex FW_E head curves; at install g9 is dropped and g10 kept (keep_green_10)',
        'values': {
            'meters': list(METERS),
            'curves_veh_per_cycle': curves,
            'full_service_rule': 'keep_green_10',
            'installed_service_by_green_veh_h': installed,
            'dropped': dropped,
            'install_expression': 'n*3600/10 (CX lane_plant_runtime.py:618, OU physical_ramp_branches.py:86)',
        },
        'source': {'name': 'config_b0_v3c3.json', 'sha256': CFG_B_SHA,
                   'pointer': '/freeway/physical_ramp_head_service_veh_per_cycle',
                   'codex_install_code': {'name': 'lane_plant_runtime.py', 'lines': '616-620',
                                          'sha256': 'd774daee3ae12a58f76e660b3dc0ea919f7187e39c625000205ba57dc0cb9563'},
                   'codex_head': 'a49981ff'},
        'report_only': {'readback_k7': {'discharge.json': rb['discharge.json'], 'headcurve.json': rb['headcurve.json'],
                                        'use': 'comparison only, not a value source (READBACK_METER.md section 2.2)'}},
    }
    head_sha = write('head_service_fwe_c1.json', data(head))
    summary['files']['head_service_fwe_c1.json'] = head_sha
    summary['head_installed_repr'] = {m: {g: repr(s) for g, s in t.items()} for m, t in installed.items()}

    # ---- 5. c1_port section (exact keys and values) -------------------------------------------------------
    section = {
        'omega701': {'bundle_name': 'omega701_v3c3_bundle.json', 'bundle_sha256': bundle_sha},
        'meter_neighbor_audit': True,
        'max_leader_candidates': 3,
        'allow_zero_green': False,
        'storage_release_guard': {'enabled': True, 'trigger_fraction': 0.9},
        'held_retention': True,
        'head_service': {'evidence_name': 'head_service_fwe_c1.json', 'evidence_sha256': head_sha,
                         'meters': list(METERS), 'full_service_rule': 'keep_green_10'},
    }
    sec_bytes = data({'c1_port': section})
    summary['files']['c1_port_section.json'] = write('c1_port_section.json', sec_bytes)
    summary['c1_port_canonical_sha256'] = canon_sha(section)
    summary['c1_port_repr'] = {k: repr(v) for k, v in section.items()}

    # ---- 6. Closed lists --------------------------------------------------------------------------------
    mem = json.loads((B0 / 'omega701/membership.json').read_bytes())
    added = mem['controlled_intersection_expansion']['added_links']
    need(len(added) == 66, '66 added')
    old_mem = json.loads(blob(OMEGA635[0]))
    need(sha(blob(OMEGA635[0])) == OMEGA635[1], 'Omega635 sha')
    ins_new, ins_old = set(map(str, mem['inside_links'])), set(map(str, old_mem['inside_links']))
    need(ins_new - ins_old == {a['link'] for a in added} and not (ins_old - ins_new), 'Omega701 - Omega635 = added')
    per_signal = {}
    for a in added:
        for r in a['reasons']:
            if r.startswith('controlled_approach_territory:') or r.startswith('native_controlled_signal_head:'):
                per_signal.setdefault(r.split(':')[1], set()).add(a['link'])
    links = {'schema': 'c1-omega701-added-links/v1', 'membership_sha256': omega['membership.json'],
             'omega635_sha256': OMEGA635[1], 'added_links': sorted({a['link'] for a in added}, key=int),
             'reasons': {a['link']: a['reasons'] for a in added},
             'links_by_signal': {k: sorted(v, key=int) for k, v in sorted(per_signal.items())}}
    summary['files']['omega701_added_links.json'] = write('omega701_added_links.json', data(links))

    leaves = {'schema': 'c1-chain-closed-leaves/v1',
              'scope': 'R-b chained key-on replays: previous-action paths and receipts; report-only (LESSONS)',
              'leaves': ['/prediction_error/source_action_json',
                         '/metadata/n31_binding/vsl_cohort_initialization/sha256',
                         '/metadata/n31_binding/vsl_cohort_initialization/source',
                         '/metadata/sdmpc_state/previous_application/source',
                         '/metadata/sdmpc_state/previous_application/receipt_sha256',
                         '/metadata/sdmpc_state/previous_application/committed',
                         '/metadata/joint_leader_selection/price_state/previous_application/source',
                         '/metadata/joint_leader_selection/price_state/previous_application/receipt_sha256',
                         '/metadata/joint_leader_selection/price_state/previous_application/committed',
                         '/metadata/head_observation_groups_carried',
                         '/metadata/head_observation_prior_discarded']}
    summary['files']['c1_chain_closed_leaves.json'] = write('c1_chain_closed_leaves.json', data(leaves))

    runs = {
        'va': ('D:/VISSIM_runs/20261023_sdmpc31_k92', 'sdmpc31_v3c3_k92va_s{}', (31, 41, 43)),
        'robs': ('D:/VISSIM_runs/20261001_sdmpc31_v3c3', 'sdmpc31_v3c3_nc_s{}', (31, 43, 47)),
        'b': ('D:/VISSIM_runs/20261026_codex_b_v3c3', 'sdmpc31_sdmpc9000_s{}', (31, 41, 43)),
    }
    run_rows = []
    for kind, (root, pattern, seeds) in runs.items():
        for s in seeds:
            name = pattern.format(s)
            folder = (Path(root) / ('s%d/sdmpc' % s if kind == 'b' else name))
            prov = folder / ('run_provenance_' + name + '.json')
            b = prov.read_bytes()
            seed = json.loads(b.decode('utf-8-sig'))['seed']
            run_rows.append({'kind': kind, 'name': name, 'provenance_sha256': sha(b), 'seed_from_provenance': seed,
                             'network': 'v3c3', 'label': 'v3c3-s%d' % seed})
    def state(kind, seed, T):
        r = [x for x in run_rows if x['kind'] == kind and x['seed_from_provenance'] == seed]
        need(len(r) == 1, 'state run')
        return {'run': r[0]['name'], 'kind': kind, 'T': T}
    k91 = [(31, t) for t in (1050, 1650, 2100, 2550, 3300, 4350, 5100, 6900)] + \
          [(43, t) for t in (1500, 2100, 2550, 2850, 3450, 3900, 4650, 6150)]
    second = [(31, t) for t in (1500, 2850, 3900, 5250, 6000, 6600, 7500, 8250)] + \
             [(43, t) for t in (1050, 3300, 4800, 5550, 6450, 7050, 7800, 8400)]
    states = {
        'schema': 'c1-states/v1',
        'seed_rule': 'seed = run_provenance_<name>.json /seed (never from a folder or file name)',
        'runs': run_rows,
        'probe_decisions_T900': [state('va', s, 900) for s in (31, 41, 43)] + [state('robs', s, 900) for s in (31, 43)],
        'probe_plant_jobs': [dict(state('robs', s, t), H=3) for s, t in second],
        'gk0_decisions': {'gb7_nocontrol_61': [state('robs', 31, t) for t in [1] + list(range(150, 9001, 150))],
                          'gb9_sdmpc_4': [state('robs', 31, t) for t in (900, 2700, 4950, 6300)],
                          'va_12': [state('va', s, t) for s in (31, 41, 43) for t in (900, 2700, 4950, 6300)]},
        'gk0_plant_jobs': [dict(state('robs', s, t), H=3) for s, t in k91] + [dict(state('robs', 43, 2400), H=42)]
                          + [dict(state('robs', s, t), H=3) for s, t in second],
        'r_a': [state('va', s, 900) for s in (31, 41, 43)] + [state('robs', s, 900) for s in (31, 43)],
        'r_b_chains': {('v3c3-s%d' % s): [state('va', s, t) for t in range(900, 2701, 150)] for s in (31, 41, 43)},
        'g_rr_c_b': [state('b', s, 900) for s in (31, 41, 43)],
        'f_blind': [dict(state('robs', 47, t), H=3) for t in range(1050, 8401, 150)],
    }
    need(len(states['gk0_decisions']['gb7_nocontrol_61']) == 61 and len(states['gk0_plant_jobs']) == 33
         and len(states['f_blind']) == 50 and all(len(v) == 13 for v in states['r_b_chains'].values()), 'state counts')
    summary['files']['c1_states.json'] = write('c1_states.json', data(states))
    summary['counts'] = {'gk0_plant_jobs': 33, 'f_blind': 50, 'r_b': 39, 'gb7': 61, 'gb9': 4, 'va_12': 12}
    summary['links_by_signal_counts'] = {k: len(v) for k, v in links['links_by_signal'].items()}
    (OUT / 'SUMMARY.json').write_bytes(data(summary))
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
