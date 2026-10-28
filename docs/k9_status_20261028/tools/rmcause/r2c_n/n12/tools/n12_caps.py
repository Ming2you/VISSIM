"""N12 (D-K9-78 N1): static reconstruction of the c20aff1d movement capacity map for boundary movements.

Read-only.  Inputs: c20aff1d files extracted by `git show` into ../src, one existing V-A decision JSON
(catalog, metadata of the hooks that ran), the existing U4 FZP-derived saturation table (v3b).  No FZP scan,
no VISSIM, no decision or plant replay, no project code import.

Rule reproduced (file:line in ../src copies of c20aff1d):
  per_lane = equivalent_uniform x N_internal / sum(lanes_internal)          ADP:3832-3835 (value read from metadata)
  perimeter 'all': cap = per_lane x lanes_p[m], else median lanes of the resolved perimeter movements
  of the same turn, else the median of all resolved                          ADP:3860-3896
Then the hooks that overwrite single keys (metadata of the same decision): k8b_p1, k9_w1, k92_w,
route-choice merges (RCC:431-437), head resource 10629 pool (HSR:183-196), lane urban exits (LUR:104-125),
SA members (lane FIFO, UFA:584-586), ramp feeders (UFA:500-510).

python -B n12_caps.py <decision_json> <u4_table_json> <out_dir>
"""
import csv
import hashlib
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / 'src'
PERI = {'boundary_in', 'boundary_out', 'on_ramp', 'off_ramp'}
SA_MEMBERS = None
LANE_URBAN = {'SC1004_W_to_E_SC1005': '10634', 'SC1004_W_to_N_SC1003': '10635', 'SC1004_W_to_S': '10642',
              'SC1004_offW_to_E_SC1005': '10634', 'SC1004_offE_to_E_SC1005': '10634'}   # LUR:358-360, LUR:110-125
RAMP_FEEDERS = {'SC1001_W_to_onW': 'RM_C10482', 'SC1001_W_to_onE': 'RM_C10490', 'SC1004_W_to_onE': 'RM_C10639'}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_bytes().decode('utf-8-sig'))


def main(dec_path, u4_path, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    dec = load(dec_path)
    meta = dec['metadata']
    P = float(meta['movement_capacity_by_lanes_per_lane_veh_h'])
    cfgdoc = load(SRC / 'config_n31_v2.json')
    specs = dict(cfgdoc['config_overrides']['network']['urban_movements'])
    cap_section = cfgdoc['urban']['capacity']
    # ADP:3578-3613 exit-twin merge: new name sig_app_to_rep(exit); the spec of the kept name, else the first old.
    plan = load(SRC / 'movement_merge_plan_20260824.json')
    rep = plan.get('leg_representative') or {}
    leg = lambda s, x: str(rep.get('%s|%s' % (s, x), x))
    groups = defaultdict(list)
    for name, s in specs.items():
        sig, app, ext = str(s.get('signal', '')), str(s.get('approach', '')), leg(str(s.get('signal', '')), str(s.get('exit', '')))
        if leg(sig, app) == ext:
            continue
        groups['%s_%s_to_%s' % (sig, app, ext)].append(name)
    merged_from = {}
    for new, olds in groups.items():
        if new not in specs:
            base = olds[0]
            specs[new] = dict(specs[base], merged_spec_base=base)
            merged_from[new] = olds
    lanes_int = load(SRC / 'movement_lanes_core17legs4b_20260821.json')['movement_lanes']
    lanes_p = load(SRC / 'movement_lanes_perimeter_20260824.json')['movement_lanes_perimeter']
    sa = load(SRC / 'sc1001eb_evidence_v3c3_20261004.json')['approaches']['SC1001_EB']['members']
    sa_members = set(sa.values())

    tds = meta['joint_leader_selection']['tangent_derivatives']
    sp = tds[0]['surrogate_prediction']
    prov = sp['quantities']['provenance']
    catalog = {m: v['kind'] for m, v in prov['movement_catalog'].items()}
    signal_of = {m: v['owner'] for m, v in prov['movement_catalog'].items()}
    for m, v in prov['nonowner_movement_catalog'].items():
        catalog[m] = v['kind']
        signal_of[m] = v['signal']
    served = sp['quantities']['served_by_movement_veh']
    flows = sp['control_area']['flow_counts']
    greens = dec['green_times']

    # Perimeter set at install time (runtime_setup:400) = final perimeter + perimeter removed later.
    removed = []
    for path, row in (meta.get('route_choice_corridors') or {}).items():
        for mg in row.get('route_choice_merges', []):
            removed.append(mg['removed'])
    removed += list(meta.get('native_input_signal_removed_movements') or [])
    removed += [r['removed_movement'] for r in (meta.get('repairs') or []) if r.get('removed_movement')]
    if meta.get('removed_movement'):
        removed.append(meta['removed_movement'])
    removed = list(dict.fromkeys(removed))
    missing_spec = [m for m in list(catalog) + removed if m not in specs]
    install_peri = {m for m, k in catalog.items() if k in PERI}
    install_peri |= {m for m in removed if m in specs and str(specs[m].get('kind')) in PERI}
    install_int = {m for m, k in catalog.items() if k not in PERI}

    # ADP:3878-3886 medians from the resolved perimeter movements.
    by_turn = defaultdict(list)
    for m in install_peri:
        v = float(lanes_p.get(m, 0.0) or 0.0)
        if v > 0:
            by_turn[str(specs[m].get('turn', ''))].append(v)
    med = {t: sorted(v)[len(v) // 2] for t, v in by_turn.items()}
    allv = sorted(x for v in by_turn.values() for x in v)
    fallback = allv[len(allv) // 2] if allv else 1.0

    base, lane_src = {}, {}
    for m in install_peri:
        v = float(lanes_p.get(m, 0.0) or 0.0)
        if v > 0:
            base[m], lane_src[m] = P * v, ('resolved', v)
        else:
            t = str(specs[m].get('turn', ''))
            v = med.get(t, fallback)
            base[m], lane_src[m] = P * v, ('estimated_turn_median' if t in med else 'estimated_all_median', v)

    # Overrides (each with its code anchor).
    over = {}
    for key, anchor in (('k8b_p1', 'RS:111-140'), ('k9_w1', 'RS:146-184')):
        for m, v in ((meta.get(key) or {}).get('after') or {}).items():
            over[m] = (float(v), key + ' ' + anchor)
    if meta.get('k92_w'):
        over['SC109_W_SC108_to_E'] = (float(meta['k92_w']['after']), 'k92_w RS:242-286')
    for path, row in (meta.get('route_choice_corridors') or {}).items():
        for mg in row.get('route_choice_merges', []):
            over[mg['keep']] = (float(mg['single_capacity_veh_h']), 'route_choice_turn RCC:431-438 (' + Path(path).name + ')')
    if 'head_resource_final_rate_10629' in meta:
        for m in ('SC1004_E_SC1005_to_W', 'SC1004_E_SC107_to_W'):
            over[m] = (float(meta['head_resource_final_rate_10629']), 'head_pool_10629 HSR:183-196 (pool shared)')
    for m, c in LANE_URBAN.items():
        over[m] = (None, 'lane_urban_exit_' + c + ' LUR:104-125 (lane FD; value not logged)')
    # ADP:3380-3410 install_gate_onramp_queue (runtime_setup:401): the gate-origin on-ramp movements kept by the
    # leg-ramp fold get urban.ramp.gate_onramp_queue_capacity_veh_h (default 1800) and unsignalized=True.
    if float(meta.get('gate_onramp_queue_registered', 0)) == len(RAMP_FEEDERS):
        for m in RAMP_FEEDERS:
            over[m] = (1800.0, 'gate_onramp_queue ADP:3380-3410 (unsignalized; registered=3)')

    rows = []
    P_fam = lambda x: x is not None and abs(x / P - round(x / P)) < 1e-9 and round(x / P) >= 1
    for m in sorted(install_peri):
        kind = catalog.get(m, str(specs[m].get('kind')))
        final_present = m in catalog
        cap_base = base[m]
        cap_final, why = (over[m] if m in over else (cap_base, 'base ADP:3896'))
        if m in sa_members:
            path = 'SA lane FIFO s_l (UFA:584-586; table not read)'
        elif m in LANE_URBAN:
            path = 'lane urban CTM exit (UFA:73-86 returns 0; LUR)'
        elif m in RAMP_FEEDERS:
            path = 'ramp loop UFA:500-510 -> ' + RAMP_FEEDERS[m]
        elif kind == 'off_ramp':
            path = 'not read by plant (UFA:579-580 skip; LOR:46-77 ports: SA/local_upstream/direct use 1400 x lanes)'
        elif why.startswith('route_choice_turn'):
            path = 'route corridor budget RCC:691-709'
        elif why.startswith('head_pool'):
            path = 'regular loop + head pool HSR:216-238'
        else:
            path = 'regular loop UFA:589-591 -> UQM:730-764'
        spec = specs[m]
        g_now = greens.get(str(spec.get('phase', '')))
        sv = served.get(m)
        arr = flows.get('arrival:' + m)
        implied = (sv * 3600.0 / cap_final) if (sv is not None and cap_final) else None
        rows.append({
            'movement': m, 'kind': kind, 'present_in_final_catalog': final_present,
            'signal': signal_of.get(m, spec.get('signal')), 'phase': spec.get('phase'), 'origin': spec.get('origin'),
            'turn': spec.get('turn'), 'receiving_link': spec.get('receiving_link'), 'beta_config': spec.get('beta'),
            'lanes_source': lane_src[m][0], 'model_lanes': lane_src[m][1], 'cap_install_veh_h': cap_base,
            'cap_final_veh_h': cap_final, 'final_source': why,
            'family_206': bool(P_fam(cap_final)), 'k_lanes_206': (round(cap_final / P) if P_fam(cap_final) else None),
            'plant_path': path, 'green_now_s': g_now, 'served_450s_veh_decision0': sv, 'arrival_450s_veh_decision0': arr,
            'implied_green_sum_s': implied,
        })

    # U4 (v3b FZP, 5 NC seeds) join by membership listed in the table's plant.base members.
    u4 = load(u4_path)
    g_of = {}
    for g in u4['groups']:
        for name in ((g.get('plant') or {}).get('base') or {}).get('members', {}):
            g_of.setdefault(name, []).append(g)
    for r in rows:
        gs = g_of.get(r['movement'], [])
        if len(gs) == 1:
            g = gs[0]
            meas = g.get('measured') or {}
            r.update({'u4_group': g['key'], 'u4_status': g['status'], 'u4_group_lanes': g['n_lanes'],
                      'u4_sat_veh_h_lane': g.get('saturation_veh_h_per_lane'),
                      'u4_green_avg_flow_veh_h_lane': meas.get('green_average_flow_veh_h_lane'),
                      'u4_t1_cap_veh_h': g['plant']['base']['members'][r['movement']].get('cap_T1_veh_h'),
                      'ratio_206_over_u4_sat': (P / g['saturation_veh_h_per_lane']
                                                if g.get('saturation_veh_h_per_lane') else None)})
        else:
            r.update({'u4_group': (None if not gs else 'ambiguous:' + ','.join(x['key'] for x in gs))})

    fam = [r for r in rows if r['present_in_final_catalog'] and r['family_206']]
    read = [r for r in fam if r['plant_path'].startswith(('regular loop', 'ramp loop', 'route corridor'))]
    summary = {
        'per_lane_veh_h': P, 'per_lane_check_330x184/294': 330.0 * 184 / 294,
        'config_capacity': {k: cap_section.get(k) for k in ('per_lane', 'equivalent_uniform_veh_h', 'perimeter')},
        'install_perimeter_count': len(install_peri), 'install_internal_count_final': len(install_int),
        'resolved': sum(1 for m in install_peri if lane_src[m][0] == 'resolved'),
        'estimated': sum(1 for m in install_peri if lane_src[m][0] != 'resolved'),
        'turn_medians': med, 'fallback_median': fallback,
        'missing_spec': missing_spec, 'removed_after_install': removed,
        'final_perimeter_count': sum(1 for r in rows if r['present_in_final_catalog']),
        'final_family_206_count': len(fam),
        'final_family_206_by_kind': dict(Counter(r['kind'] for r in fam)),
        'final_family_206_by_path': dict(Counter(r['plant_path'].split(' (')[0].split(' ->')[0] for r in fam)),
        'family_206_read_by_plant_count': len(read),
        'family_206_read_by_plant_by_kind': dict(Counter(r['kind'] for r in read)),
        'family_206_read_by_plant_by_signal': dict(Counter(r['signal'] for r in read)),
        'not_family_final': [(r['movement'], r['cap_final_veh_h'], r['final_source']) for r in rows
                             if r['present_in_final_catalog'] and not r['family_206']],
        'inputs': {'decision_json': str(dec_path), 'decision_sha256': sha(dec_path), 'u4_table': str(u4_path),
                   'u4_sha256': sha(u4_path),
                   'src_sha256': {p.name: sha(p) for p in sorted(SRC.glob('*.json'))}},
    }
    (out_dir / 'n12_caps.json').write_text(json.dumps({'summary': summary, 'rows': rows}, indent=1, ensure_ascii=False),
                                           encoding='utf-8')
    with open(out_dir / 'n12_caps.csv', 'w', newline='', encoding='utf-8') as f:
        keys = list(rows[0].keys()) + [k for k in ('u4_group', 'u4_status', 'u4_group_lanes', 'u4_sat_veh_h_lane',
                                                   'u4_green_avg_flow_veh_h_lane', 'u4_t1_cap_veh_h',
                                                   'ratio_206_over_u4_sat') if k not in rows[0]]
        w = csv.DictWriter(f, fieldnames=keys, extrasaction='ignore')
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(json.dumps(summary, indent=1, ensure_ascii=False, default=str)[:6000])


if __name__ == '__main__':
    main(*sys.argv[1:4])
