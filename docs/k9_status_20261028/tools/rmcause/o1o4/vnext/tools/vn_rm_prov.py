# VERIFY_NEXT: provenance of held v3c3 rule-RM arms s31/s41 (read-only, light reads only).
import json, hashlib, os, glob, csv, collections, sys
import xml.etree.ElementTree as ET

BASE = 'D:/VISSIM_runs/20261001_v3c3'
OUT = sys.argv[1]
FWE = ['RM_C10639', 'RM_C10681', 'RM_C10490', 'RM_C10484']
FWW = ['RM_C10480', 'RM_C10482', 'RM_C10646', 'RM_C10644']


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def sections(p):
    root = ET.parse(p).getroot()
    secs = collections.OrderedDict()
    for ch in root:
        secs.setdefault(ch.tag, []).append(hashlib.sha256(ET.tostring(ch)).hexdigest())
    sim = root.find('simulation')
    return root, secs, (dict(sim.attrib) if sim is not None else None)


res = {}
for S in (31, 41):
    rm = f'{BASE}/s{S}_v3c3rm'
    nc = f'{BASE}/s{S}_v3c3nc'
    r = {}
    run = json.load(open(f'{rm}/run/run.json', encoding='utf-8-sig'))
    r['run_json'] = {k: run.get(k) for k in ('seed', 'completed', 'error', 'started', 'finished', 'exit_code', 'requested_terminal_sec', 'fixed_profile')}
    r['run_json']['proof_network_sha256'] = run.get('fixed_profile_proof', {}).get('network_sha256')
    r['run_json']['proof_control_start_sec'] = run.get('fixed_profile_proof', {}).get('control_start_sec')
    r['run_json']['keys'] = sorted(run.keys())
    rm_inpx = f'{rm}/prepared/network/baseline_s{S}_v3c3rm.inpx'
    nc_inpx = f'{nc}/prepared/network/baseline_s{S}_v3c3nc.inpx'
    r['rm_inpx_sha256'] = sha(rm_inpx)
    r['nc_inpx_sha256'] = sha(nc_inpx)
    _, srm, simrm = sections(rm_inpx)
    _, snc, simnc = sections(nc_inpx)
    tags = list(dict.fromkeys(list(srm) + list(snc)))
    r['n_top_sections_rm'] = len(srm); r['n_top_sections_nc'] = len(snc)
    r['differing_sections'] = [t for t in tags if srm.get(t) != snc.get(t)]
    r['sim_attrs_rm'] = {k: simrm.get(k) for k in ('randSeed', 'simRes', 'simPeriod', 'numRuns', 'randSeedIncr')} if simrm else None
    r['sim_attrs_nc'] = {k: simnc.get(k) for k in ('randSeed', 'simRes', 'simPeriod', 'numRuns', 'randSeedIncr')} if simnc else None
    pol_p = f'{rm}/prepared/rule_policy.json'
    pol = json.load(open(pol_p, encoding='utf-8'))
    r['rule_policy_sha256'] = sha(pol_p)
    r['alinea'] = pol['rule']['alinea']
    r['rule_arm'] = pol['rule'].get('arm')
    r['meters_cfg'] = {m: {k: v for k, v in pol['meters'][m].items() if k != 'table'} for m in pol['meters']}
    r['tables'] = {m: pol['meters'][m].get('table') for m in ('RM_C10490', 'RM_C10681')}
    r['rule_runtime_txt'] = open(f'{rm}/prepared/rule_runtime.txt', 'rb').read().decode('utf-16', errors='replace')
    fv = json.load(open(f'{rm}/run/fixed_validation.json', encoding='utf-8'))
    win = fv.get('actual_green_windows', [])
    r['fixed_validation'] = {'passed': fv.get('passed'), 'event_readbacks': fv.get('event_readbacks'), 'n_windows': len(win),
                             'n_windows_obs_eq_cmd': sum(1 for w in win if abs(w['observed_green_seconds'] - 15 * w['green_sec_per10']) < 1e-9)}
    decs = sorted(glob.glob(f'{rm}/run/decision_*.json'), key=lambda p: int(p.split('_')[-1].split('.')[0]))
    secs = []; arms = collections.Counter(); g = {m: [] for m in FWE + FWW}; vsl_keys = collections.Counter()
    for p in decs:
        d = json.load(open(p, encoding='utf-8'))
        secs.append(d['sec']); arms[d['arm']] += 1
        for m in FWE + FWW:
            g[m].append(d['meters'][m]['green_sec'])
        for k in d:
            if 'vsl' in k.lower() or 'speed' in k.lower():
                vsl_keys[k] += 1
    r['decisions'] = {'n': len(decs), 'first': secs[0], 'last': secs[-1],
                      'contiguous_150': all(b - a == 150 for a, b in zip(secs, secs[1:])), 'arms': dict(arms),
                      'top_level_vsl_like_keys': dict(vsl_keys)}
    r['meters'] = {}
    for m in FWE + FWW:
        arr = g[m]
        idx = [i for i, x in enumerate(arr) if x < 10]
        run_max = cur = 0
        for x in arr:
            cur = cur + 1 if x < 10 else 0
            run_max = max(run_max, cur)
        r['meters'][m] = {'n_lt10': len(idx), 'min_g': min(arr), 'first_T': secs[idx[0]] if idx else None,
                          'last_T': secs[idx[-1]] if idx else None, 'longest_run': run_max,
                          'string': ''.join('A' if x == 10 else str(x) for x in arr)}
    # rule events: any non-meter rows?
    ev = f'{rm}/run/rule_events.csv'
    rows = list(csv.reader(open(ev, encoding='utf-8-sig')))
    r['rule_events_header'] = rows[0] if rows else None
    r['rule_events_n'] = len(rows) - 1
    kinds = collections.Counter()
    for row in rows[1:]:
        kinds[tuple(row[i] for i in range(len(row)) if rows[0][i].lower() in ('kind', 'type', 'target_kind', 'object', 'sc'))] += 1
    r['rule_events_kind_counts_top'] = [[list(k), n] for k, n in kinds.most_common(12)]
    txt = open(ev, encoding='utf-8-sig').read().lower()
    r['rule_events_mentions'] = {w: txt.count(w) for w in ('vsl', 'dsd', 'desspeed', 'speed', 'des_speed')}
    # vehicle inputs equality between rm and nc
    r['vehicleInputs_equal'] = srm.get('vehicleInputs') == snc.get('vehicleInputs')
    r['vehicleRoutingDecisionsStatic_equal'] = srm.get('vehicleRoutingDecisionsStatic') == snc.get('vehicleRoutingDecisionsStatic')
    res[f's{S}'] = r
for p in ('D:/VISSIM-merge/sim3/diagnostics/fast_fixed_profile.py', 'D:/VISSIM-merge/sim3/evaluation/controllers/diagnostic_profile.py',
          'D:/VISSIM-merge/sim3/diagnostics/fast_nc_run.ps1', 'D:/VISSIM-merge/sim3/diagnostics/fast_nc_runner.vbs',
          f'{BASE}/rm_build/build_v3c3rm.py', f'{BASE}/rm_build/v3c3rm_build_receipt.json', f'{BASE}/rm_build/v3c3rm_dryrun_receipt.json'):
    res.setdefault('files', {})[p] = {'sha256': sha(p) if os.path.exists(p) else None,
                                      'mtime': os.path.getmtime(p) if os.path.exists(p) else None}
json.dump(res, open(OUT, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print('done')
