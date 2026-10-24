"""Reconstruct interval cell flux from completed counters and conserved stocks."""
import hashlib
import json
from pathlib import Path

from evaluation.controllers import obs150_contract as oc
from evaluation.controllers.obs150_observation import check_rule_crosscheck

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
I = ROOT / 'diagnostics/sdmpc_n31_20260924/integration_20260926'
pins = {}


def read(path):
    data = path.read_bytes()
    pins[str(path)] = hashlib.sha256(data).hexdigest()
    return json.loads(data)


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False), encoding='utf-8')


def cell_flux(initial, final, source, terminal, merges, exits):
    """Backward continuity; return net through-flow, not a speed-based estimate."""
    result = {30: terminal}
    for cell in reversed(range(31)):
        result[cell - 1] = (result[cell] + final[cell] - initial[cell]
                            - merges.get(cell, 0.) + exits.get(cell, 0.))
    assert abs(result[-1] - source) < 1e-7, (result[-1], source)
    assert min(result.values()) >= -1e-7
    return result


def main():
    assert not (HERE / 'flow_assessment82.json').exists()
    protocol = read(HERE / 'protocol_selected.json')
    for path, digest in protocol['source_pins'].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest, path
    assert read(HERE / 'completion81.json')['status'] == 'COMPLETE_DIAGNOSTIC_NOT_GAIN_QUALIFICATION'
    geo = read(I / 'selected/port_gain/geometry.json')
    ports = [b for b in geo['boundaries'] if b['road'] == 'FW_E']
    ramps = [b for b in ports if b['kind'] == 'ramp']
    offramps = [b for b in ports if b['kind'] == 'offramp']
    chain_links = {int(b['link']) for b in geo['chains']['FW_E']}
    actual = {}
    for row in read(HERE.parent / 's67_full_observation/snapshot_errors76.json'):
        actual[row['arm'], row['time_sec'], row['cell']] = row['actual_stock']
    for row in read(HERE.parent / 's67_selected_vsl78/observed_snapshots80.json'):
        for cell in row['east_cells']:
            actual[row['arm'], row['time_sec'], cell['cell']] = cell['n']
    predictions = read(Path(protocol['completed_release_output']) / 'summary.json')['results']
    selected = read(Path(protocol['jobs'][0]['output']) / 'summary.json')['results']
    cases = {name: predictions[name + '_actual'] for name in ('release', 'release_vsl90')}
    cases.update({name: selected[name]['execution'] for name in ('selected', 'vsl90')})
    a76 = read(HERE.parent / 's67_full_observation/analysis/summary.json')
    a80 = read(HERE.parent / 's67_selected_vsl78/analysis/summary.json')
    assert a80['counterfactual_valid'] and a80['prefixes']['selected'] == a76['prefixes']['release']
    audits = {
        'release': read(I / 'closedloop_recorded2700_lever450_s67_service66_20261003_actuator_equivalent/ramp_response_audit.json'),
        'selected': read(HERE.parent / 's67_selected_vsl78/analysis/ramp_response_audit.json'),
    }
    save(HERE / 'flow_protocol82.json', dict(
        previous_goal_turn='PROGRESS: REVIEW81 completed exact unchanged diagnostic replays.',
        hypothesis='Separate accumulation from incoming and outgoing flux errors in the current coupled plant; do not refit recovery speed from a stock-biased rollout.',
        prior_checks=['Claude REVIEW_CHECK K3/K4', 'freeway_first/local_fd24_25/README.md',
                      'freeway_first/first_recovery_divergence/README.md', 'recovery_subcells/README.md'],
        method='F_i=F_terminal+sum_downstream(delta N - merge + off); check whole-road closure and every cell error identity.',
        limits=['Aggregate net flux inferred by continuity, not a directly observed cell-face detector.',
                'Native cell states at150s instants cannot identify subinterval onset or causal ordering.',
                'No new independent seed, parameter fit, rollout or native execution.'],
        new_forecasts=0, new_native=0, new_fzp_reads=0))
    rows = []
    for name, prediction in cases.items():
        selected_case = name in ('selected', 'vsl90')
        run = Path('D:/VISSIM_runs') / ('20261003_s67_selected_vsl78' if selected_case else '20261003_s67_vsl_observation2700')
        audit = audits['selected' if selected_case else 'release']['arms'][name]
        cum_actual, cum_pred = {i: 0. for i in range(-1, 31)}, {i: 0. for i in range(-1, 31)}
        cum_merge_error, cum_off_error = {i: 0. for i in range(31)}, {i: 0. for i in range(31)}
        for block in prediction['executed_intervals']:
            start, end = block['start_sec'], block['end_sec']
            raw = read(run / name / f'decisions_sdmpc31_g_2700_{name}_s67' / f'state_{int(end):06d}.json')
            obs = raw['obs150']
            detectors, _ = oc.read_detector_csv(obs['detector_config']['path'], obs['detector_config']['sha256'])
            oc.validate_raw(obs, detectors, expected_simres=10)
            check_rule_crosscheck(obs, detectors)
            bundle = oc.load_bundle(raw)
            boundaries = oc.evaluate_boundaries(obs, detectors, bundle.frame_end, bundle.frame_start, bundle.err_rows)
            removed = oc.window_removals(bundle.err_rows, start, end)
            assert not [r for r in removed if int(r['link']) in chain_links], (name, end, removed)
            assert obs['window'] == dict(start_s=start, end_s=end)
            n0 = [actual[name, start, c] for c in range(31)]
            n1 = [actual[name, end, c] for c in range(31)]
            am = {}
            for ramp in ramps:
                windows = audit[ramp['id']]['actual']['windows']
                w = next(w for w in windows if w['end_sec'] == end)
                assert w['start_sec'] == start
                am[ramp['to_cell']] = w['merge']
            ao = {b['from_cell']: boundaries['off_entry:' + str(b['connector'])].cross for b in offramps}
            af = cell_flux(n0, n1, boundaries['source:FW_E'].cross, boundaries['chain_end:FW_E'].cross, am, ao)
            transfers = block['transfers']
            flow = lambda source, target: sum(r['vehicles'] for r in transfers if r['source'] == source and r['target'] == target)
            pm = {b['to_cell']: flow('merge_pending:' + b['id'], 'freeway:FW_E') for b in ramps}
            stores = {v['connector']: v['storage'] for v in block['offramps'].values()}
            po = {b['from_cell']: flow('freeway:FW_E', 'storage:' + stores[b['connector']]) for b in offramps}
            s0, s1 = block['physical_cell_states']
            p0, p1 = s0['vehicle_count']['FW_E'], s1['vehicle_count']['FW_E']
            pf = cell_flux(p0, p1, flow('origin:FW_E', 'freeway:FW_E'), flow('freeway:FW_E', 'external:terminal:FW_E'), pm, po)
            for c in range(-1, 31):
                cum_actual[c] += af[c]
                cum_pred[c] += pf[c]
            for c in range(31):
                cum_merge_error[c] += pm.get(c, 0.) - am.get(c, 0.)
                cum_off_error[c] += po.get(c, 0.) - ao.get(c, 0.)
                incoming = cum_pred[c - 1] - cum_actual[c - 1] + cum_merge_error[c]
                outgoing = cum_pred[c] - cum_actual[c] + cum_off_error[c]
                # All arms start from the same native2700 stock, verified below.
                initial_error = prediction['executed_intervals'][0]['physical_cell_states'][0]['vehicle_count']['FW_E'][c] - actual[name, 2700, c]
                assert abs(initial_error) < 1e-7
                residual = (p1[c] - n1[c]) - (initial_error + incoming - outgoing)
                assert abs(residual) < 1e-7
                rows.append(dict(case=name, start_sec=start, end_sec=end, cell=c,
                    native_through=af[c], predicted_through=pf[c], cumulative_native_through=cum_actual[c],
                    cumulative_predicted_through=cum_pred[c], actual_stock=n1[c], predicted_stock=p1[c],
                    cumulative_incoming_error=incoming, cumulative_outgoing_error=outgoing,
                    conservation_error=residual))
    for path, digest in pins.items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest, path
    save(HERE / 'cell_flux82.json', rows)
    summary = dict(status='COMPLETE_CACHE_ONLY_CONTINUITY_DIAGNOSIS', rows=len(rows),
        max_cell_error_identity=max(abs(r['conservation_error']) for r in rows),
        new_forecasts=0, new_native=0, new_fzp_reads=0, new_coefficients=0,
        inputs_sha256=pins)
    save(HERE / 'flow_assessment82.json', summary)
    print(json.dumps({k: v for k, v in summary.items() if k != 'inputs_sha256'}))


def assess_boundary_time88():
    """Native boundary first moments; not a causal fixed-inflow counterfactual."""
    from collections import Counter, defaultdict
    from evaluation.controllers import obs150_capture as capture
    dest = HERE.parent / 'boundary_time88'
    assert not (dest / 'assessment.json').exists(), 'Preserve completed assessment'
    protocol = read(dest / 'protocol.json')
    for p, h in protocol['production_pins'].items():
        assert hashlib.sha256(Path(p).read_bytes()).hexdigest() == h, p
    stop = protocol['old_STOP']
    assert hashlib.sha256(Path(stop['path']).read_bytes()).hexdigest() == stop['sha256']
    geo = read(I / 'selected/port_gain/geometry.json')
    assert geo['network']['sha256'] == '64cf5f55fe9990f3e25bc4fedebf4ab1e4634c8138dbcf5697a136c48cb559dc'
    road = {int(v['link']) for v in geo['chains']['FW_E']}
    ramps = [v for v in geo['boundaries'] if v['road'] == 'FW_E' and v['kind'] == 'ramp']
    exits = [v for v in geo['boundaries'] if v['road'] == 'FW_E' and v['kind'] == 'offramp']
    ramp_links = {v['connector'] for v in ramps}
    domain = road | ramp_links
    refs = {'source:FW_E': 1, 'chain_end:FW_E': -1}
    refs.update({'ramp_arrival:' + v['id']: 1 for v in ramps})
    refs.update({'off_entry:' + str(v['connector']): -1 for v in exits})
    native71 = I / 'native_rm_observation2700_s71_four84/analysis'
    groups = [
        ('67_release', 67, 2700, ('release', 'release_vsl90'),
         Path('D:/VISSIM_runs/20261003_s67_vsl_observation2700'), HERE.parent / 's67_full_observation/analysis'),
        ('67_selected', 67, 2700, ('selected', 'vsl90'),
         Path('D:/VISSIM_runs/20261003_s67_selected_vsl78'), HERE.parent / 's67_selected_vsl78/analysis'),
        ('71_four', 71, 2250, ('nc', 'rm', 'vsl', 'both'),
         Path('D:/VISSIM_runs/20261003_independent_s71_four84'), native71),
    ]
    cases = {}; events_out = []; late = []; common = {}
    for group, seed, start, arms, runs, analysis in groups:
        end = start + 450
        proof = read(analysis / 'summary.json')
        if seed == 71:
            assert proof['counterfactual_valid'] and proof['paired_prefix_exact']
        elif group == '67_selected':
            assert proof['counterfactual_valid']
        else:
            alignment = read(HERE.parent / 's67_full_observation/recording_start_alignment76.json')
            assert alignment['overlap_exact'] and alignment['cutoff_s'] == start
            assert proof['paired_prefix_exact'] and proof['common_start_vehicle_records_exact']
        for arm in arms:
            key = group + '/' + arm
            folder = runs / arm / f'decisions_sdmpc31_g_{start}_{arm}_s{seed}'
            bundles = {t: oc.load_bundle(read(folder / f'state_{t:06d}.json'))
                       for t in range(start, end + 1, 150)}
            first = bundles[start].frame_end['vehicles']
            if seed in common:
                assert first == common[seed], 'Same-seed common initial native frame differs'
            else:
                common[seed] = first
            initial_ids = {v[0] for v in first}; initial_domain = {v[0] for v in first if v[1] in domain}
            last = bundles[end].obs['mer']; source = Path(last['source'])
            pins[str(source)] = hashlib.sha256(source.read_bytes()).hexdigest()
            table, _ = oc.read_detector_csv(bundles[end].obs['detector_config']['path'])
            with source.open('rb') as handle:
                header = capture._mer_header(handle, source.stat().st_size)
                capture._check_header_points(header['points'], table, True)
                seq = capture._count_lines(handle, header['data_start'], last['byte_end'])
                handle.seek(last['byte_end']); tail = handle.read()
            assert not tail or tail.endswith(b'\n'), 'MER final suffix incomplete'
            counters = {int(k): v for k, v in last['records_cum_by_dcp'].items()}
            extra, _ = capture.parse_mer_rows(tail, header['columns'], seq, set(counters), counters)
            by_ordinal = defaultdict(dict)
            for event in [v for b in bundles.values() for v in b.mer_rows] + extra:
                if event.ordinal is None:
                    continue
                old = by_ordinal[event.dcp].get(event.ordinal)
                assert old is None or old == event
                by_ordinal[event.dcp][event.ordinal] = event
            moment = {ref: 0. for ref in refs}; observed = Counter(); physical = Counter()
            population = {ref: Counter() for ref in refs}; buffer_rows = []; removed = []
            for t, bundle in bundles.items():
                obs = bundle.obs
                detectors, _ = oc.read_detector_csv(obs['detector_config']['path'], obs['detector_config']['sha256'])
                oc.validate_raw(obs, detectors, expected_simres=10)
                check_rule_crosscheck(obs, detectors)
                dg = oc.group_boundaries(detectors)
                stocks = {}
                for ref in refs:
                    ds = dg[ref]; orientation = ds[0].orientation
                    ids = set().union(*(oc.vehicles_in_segment(bundle.frame_end['vehicles'], d.segment, orientation) for d in ds)) if orientation != 'at' else set()
                    stocks[ref] = len(ids)
                buffer_rows.append(dict(time_sec=t, stocks=stocks))
                if t == start:
                    continue
                assert obs['window'] == dict(start_s=t-150, end_s=t)
                assigned = oc.assign_window(obs, bundle.mer_rows)
                boundary = oc.evaluate_boundaries(obs, detectors, bundle.frame_end, bundle.frame_start, bundle.err_rows)
                removed.extend(v for v in oc.window_removals(bundle.err_rows, t-150, t) if int(v['link']) in domain)
                for ref, sign in refs.items():
                    physical[ref] += boundary[ref].cross
                    for d in dg[ref]:
                        high = obs['detectors_cum'][str(d.dcp_no)]
                        low = high - obs['detectors'][str(d.dcp_no)]
                        missing = [n for n in range(low+1, high+1) if n not in by_ordinal[d.dcp_no]]
                        assert not missing, (key, t, ref, missing)
                        entries = [by_ordinal[d.dcp_no][n] for n in range(low+1, high+1)]
                        assert len(entries)-len(assigned.entries[d.dcp_no]) == assigned.tails[d.dcp_no]
                        if assigned.tails[d.dcp_no]:
                            late.append(dict(case=key, end=t, ref=ref, dcp=d.dcp_no, count=assigned.tails[d.dcp_no]))
                        for event in entries:
                            assert start-.005 < event.t_entry <= end+.005, (key, event)
                            contribution = sign * (end-event.t_entry) / 3600
                            cohort = ('initial_domain' if event.veh in initial_domain else
                                      'initial_elsewhere' if event.veh in initial_ids else 'post_cutoff_population')
                            moment[ref] += contribution; observed[ref] += 1
                            population[ref][cohort] += contribution
                            events_out.append(dict(case=key, ref=ref, time_sec=event.t_entry,
                                vehicle=event.veh, cohort=cohort, signed_moment_veh_h=contribution))
            assert not removed, (key, 'Domain deletion needs explicit residence decomposition', removed)
            final_domain = {v[0] for v in bundles[end].frame_end['vehicles'] if v[1] in domain}
            residual = len(initial_domain) + sum(refs[r]*physical[r] for r in refs) - len(final_domain)
            assert residual == 0, (key, 'Physical domain count balance', residual)
            metric = read(analysis / arm / 'area_metrics.json')
            costs = {part: sum(v['ttt_veh_h'] for link, v in metric['physical_link_residence'].items() if int(link) in links)
                     for part, links in [('east_mainline', road), ('east_onramps', ramp_links)]}
            cases[key] = dict(seed=seed, start_sec=start, end_sec=end, initial_stock=len(initial_domain),
                final_stock=len(final_domain), physical_counts=dict(physical), detector_counts=dict(observed),
                signed_detector_moments_veh_h=moment, moments_by_population_veh_h=population,
                initial_and_final_offset_stocks=buffer_rows, full_run_component_TTT_veh_h=costs,
                domain_TTT_full_run_veh_h=sum(costs.values()), physical_count_residual=residual)
            print('Complete native event moments', key, flush=True)
    contrasts = {}
    comparisons = [('67_release/release', '67_release/release_vsl90'),
                   ('67_selected/selected', '67_selected/vsl90'),
                   ('71_four/nc', '71_four/rm'), ('71_four/nc', '71_four/vsl'),
                   ('71_four/rm', '71_four/both')]
    for baseline, arm in comparisons:
        a, b = cases[baseline], cases[arm]
        assert a['initial_stock'] == b['initial_stock']
        delta = {ref: b['signed_detector_moments_veh_h'][ref]-a['signed_detector_moments_veh_h'][ref] for ref in refs}
        grouped = dict(source=delta['source:FW_E'], ramp_arrival=sum(v for k,v in delta.items() if k.startswith('ramp_arrival:')),
                       off_entry=sum(v for k,v in delta.items() if k.startswith('off_entry:')), terminal=delta['chain_end:FW_E'])
        cost = b['domain_TTT_full_run_veh_h']-a['domain_TTT_full_run_veh_h']
        remainder = cost-sum(delta.values())
        contrasts[arm+' minus '+baseline] = dict(actual_domain_delta_TTT_veh_h=cost,
            signed_event_contributions_veh_h=grouped, contributions_by_boundary_veh_h=delta,
            event_sum_veh_h=sum(delta.values()), physical_minus_detector_residual_veh_h=remainder,
            residual_within_declared_limit=abs(remainder)<=protocol['accounting_residual_limit_veh_h'],
            actual_delta_minus_source_accounting_term=cost-grouped['source'],
            warning='Subtracting source term is bookkeeping, NOT a rerun with common source. Remaining traffic already responded to different inflow; source causality and input randomness are not isolated.')
    for p,h in pins.items():
        assert hashlib.sha256(Path(p).read_bytes()).hexdigest() == h, p
    output = dict(status='COMPLETE_NATIVE_EVENT_MOMENTS_NOT_MODEL_VALIDATION', cases=cases, contrasts=contrasts,
        resolved_late_mer=late, inputs_sha256=pins, new_forecasts=0,new_native=0,fzp_scans=0,fit=0,
        interpretation=['Positive contribution increases East mainline+four on-ramp TTT; negative decreases it.',
            'Merge is internal to this domain, so ramp waiting is included and cannot disappear from accounting.',
            'Moments use detector crossings, not exact physical boundaries. Full-run paired TTT prefix cancels; remaining offset/sampling discrepancy is reported, never allocated silently.',
            'Actual routing, stochastic coupling and source backpressure are not isolated causal effects. No fitting/qualification from source-subtracted number.',
            'Omega objective, normal exit definition, and external costs are unchanged; this subdomain is only a physical diagnosis.'])
    save(dest / 'events.json', events_out); save(dest / 'assessment.json', output)
    print(json.dumps(contrasts, indent=2))


def boundary_cohorts88():
    """Reuse saved events to localize the initial population's departure response."""
    import bisect
    from collections import Counter, defaultdict
    dest = HERE.parent / 'boundary_time88'
    assert not (dest/'cohorts.json').exists()
    result = read(dest/'assessment.json'); events = read(dest/'events.json')
    geo = read(I/'selected/port_gain/geometry.json')
    chain = {int(v['link']):v for v in geo['chains']['FW_E']}
    ends = [c['end_m'] for c in sorted((c for c in geo['cells'] if c['road']=='FW_E'),key=lambda c:c['cell'])]
    ramps = {b['connector'] for b in geo['boundaries'] if b['kind']=='ramp' and b['road']=='FW_E'}
    initial = {}
    for seed, start, folder in [
        (67,2700,Path('D:/VISSIM_runs/20261003_s67_vsl_observation2700/release/decisions_sdmpc31_g_2700_release_s67')),
        (71,2250,Path('D:/VISSIM_runs/20261003_independent_s71_four84/nc/decisions_sdmpc31_g_2250_nc_s71'))]:
        raw = read(folder/f'state_{start:06d}.json')
        initial[seed] = {}
        for v in raw['vehicle_records']['records']:
            link = int(v['link_no'])
            if link in chain:
                c = min(bisect.bisect_right(ends,chain[link]['offset_m']+float(v['position_m'])),30)
                group = ('cells00_15' if c<16 else 'cells16_20' if c<21 else 'cells21_23' if c<24 else
                         'cells24_25' if c<26 else 'cells26_30')
            else:
                group = 'initial_onramp' if link in ramps else 'initial_elsewhere'
            initial[seed][int(v['veh_no'])] = group
    cases = {}; bycase = defaultdict(list)
    for e in events:bycase[e['case']].append(e)
    for case, rows in bycase.items():
        seed = result['cases'][case]['seed']; values = defaultdict(Counter); count = defaultdict(Counter)
        for e in rows:
            group = initial[seed].get(e['vehicle'],'post_cutoff_population')
            assert (group in ('initial_elsewhere','post_cutoff_population')) == (e['cohort']!='initial_domain')
            category = ('source' if e['ref'].startswith('source:') else 'ramp_arrival' if e['ref'].startswith('ramp_arrival:') else
                        'terminal' if e['ref'].startswith('chain_end:') else 'off_entry')
            values[group][category] += e['signed_moment_veh_h'];count[group][category] += 1
        cases[case] = dict(moments_veh_h=values,detector_event_counts=count)
        assert abs(sum(sum(g.values()) for g in values.values())-sum(result['cases'][case]['signed_detector_moments_veh_h'].values()))<1e-9
    contrasts = {}
    for name, comparison in result['contrasts'].items():
        arm, baseline = name.split(' minus ')
        a,b = cases[baseline]['moments_veh_h'],cases[arm]['moments_veh_h']
        groups = sorted(set(a)|set(b))
        changes = {g:{k:b.get(g,{}).get(k,0)-a.get(g,{}).get(k,0) for k in ('source','ramp_arrival','off_entry','terminal')} for g in groups}
        assert abs(sum(sum(g.values()) for g in changes.values())-comparison['event_sum_veh_h'])<1e-9
        contrasts[name] = changes
    output = dict(status='COMPLETE_SAVED_EVENT_COHORT_DECOMPOSITION',cases=cases,contrasts=contrasts,
        warnings=['Initial locations are common pre-control positions, not positions when each effect occurs.',
                  'Event moments retain detector-offset limitations; these are not exact physical-boundary per-vehicle TTT values.',
                  'Common initial vehicles are still influenced by later arriving traffic; no isolated causal capacity claim.'],
        input_sha256=pins,new_native=0,new_forecasts=0,new_fzp_scans=0,fit=0)
    save(dest/'cohorts.json',output)
    print(json.dumps(contrasts,indent=2))


def assess_cohort_departure89():
    """Compare passive model tags with common initial native mainline IDs."""
    import bisect
    import gzip
    from collections import Counter
    dest=HERE.parent/'cohort_departure89';assert not (dest/'assessment.json').exists()
    status=read(dest/'status.json');assert status['phase']=='complete_pending_assessment'
    assert status['physical_result_bit_exact']==['release_actual','release_vsl90_actual']
    with gzip.open(dest/'traces.json.gz','rt',encoding='utf-8') as f:traces=json.load(f)
    assert len(traces)==2
    events=read(HERE.parent/'boundary_time88/events.json')
    geo=read(I/'selected/port_gain/geometry.json')
    chains={int(r['link']):r for r in geo['chains']['FW_E']}
    ends=[v['end_m'] for v in sorted((c for c in geo['cells'] if c['road']=='FW_E'),key=lambda c:c['cell'])]
    native_root=Path('D:/VISSIM_runs/20261003_s67_vsl_observation2700')
    results={};snapshots=[];curves=[];common=None
    def position(v):return min(bisect.bisect_right(ends,chains[v[1]]['offset_m']+v[3]),30)
    for trace in traces:
        arm=trace['arm'];folder=native_root/arm/f'decisions_sdmpc31_g_2700_{arm}_s67'
        frames={}
        for t in (2700,2850,3000,3150):
            raw=read(folder/f'state_{t:06d}.json')
            frames[t]=read(Path(raw['lane_plant_observation']['directory'])/f'frame_{t:06d}.json')
            assert frames[t]['time_s']==t and frames[t]['complete']
            assert len(frames[t]['vehicles'])==len(raw['vehicle_records']['records'])
        initial={v[0]:position(v) for v in frames[2700]['vehicles'] if v[1] in chains}
        if common is None:common=initial
        else:assert initial==common
        counts=[sum(c==i for c in initial.values()) for i in range(31)]
        # Initial NULL-route fractions sum to integer physical counts up to
        # floating-point roundoff (observed maximum4.27e-14 vehicles).
        assert max(abs(a-b) for a,b in zip(counts,trace['initial_vehicles_by_cell']))<1e-7
        native=[dict(e,initial_cell=initial[e['vehicle']],vehicles=1.) for e in events
                if e['case']=='67_release/'+arm and e['vehicle'] in initial and e['ref'].startswith(('off_entry:','chain_end:'))]
        model=trace['events'];assert all(2700<e['time_sec']<3150 for e in model)
        # Native detector events are not silently promoted to physical boundaries.
        raw=read(folder/'state_003150.json');table,_=oc.read_detector_csv(raw['obs150']['detector_config']['path'])
        refs=oc.group_boundaries(table);physical=Counter(e['vehicle'] for e in native)
        for ref in {e['ref'] for e in native}:
            ds=refs[ref];orientation=ds[0].orientation
            first=set().union(*(oc.vehicles_in_segment(frames[2700]['vehicles'],d.segment,orientation) for d in ds))&set(initial)
            last=set().union(*(oc.vehicles_in_segment(frames[3150]['vehicles'],d.segment,orientation) for d in ds))&set(initial)
            if orientation=='down':physical.update(last);physical.subtract(first)
            elif orientation=='up':physical.update(first);physical.subtract(last)
            else:assert orientation=='at'
        assert all(n in (0,1) for n in physical.values())
        final={v[0] for v in frames[3150]['vehicles'] if v[1] in chains and v[0] in initial}
        departed={v for v,n in physical.items() if n}
        assert not final&departed and final|departed==set(initial),'Initial vehicle fate unresolved'
        bins={}
        for name,cs in [('cells00_15',set(range(16))),('cells16_20',set(range(16,21))),
                        ('cells21_23',set(range(21,24))),('cells24_25',{24,25}),('cells26_30',set(range(26,31)))]:
            an=[e for e in native if e['initial_cell'] in cs];pn=[e for e in model if e['initial_cell'] in cs]
            bins[name]=dict(initial_stock=sum(counts[i] for i in cs),
                native_physical_departures=sum(physical[v] for v,c in initial.items() if c in cs),
                native_detector_departures=len(an),model_departures=sum(e['vehicles'] for e in pn),
                native_departure_moment_veh_h=-sum((3150-e['time_sec'])/3600 for e in an),
                model_departure_moment_veh_h=-sum(e['vehicles']*(3150-e['time_sec'])/3600 for e in pn),
                native_final_remaining=sum(initial[v] in cs for v in final),
                model_final_remaining=sum(sum(row[g] for g in cs) for row in trace['frames'][-1]['initial_cell_by_current_cell']))
            for t in range(2700,3151,30):
                curves.append(dict(arm=arm,initial_group=name,time_sec=t,
                    native_detector_departures=sum(e['time_sec']<=t+.005 for e in an),
                    model_departures=sum(e['vehicles'] for e in pn if e['time_sec']<=t)))
        for t,frame in frames.items():
            model_frame=next(x for x in trace['frames'] if x['time_sec']==t)
            native_stock=[[0]*31 for _ in range(31)]
            for v in frame['vehicles']:
                if v[0] in initial and v[1] in chains:native_stock[position(v)][initial[v[0]]]+=1
            snapshots.append(dict(arm=arm,time_sec=t,native_initial_cell_by_current_cell=native_stock,
                model_initial_cell_by_current_cell=model_frame['initial_cell_by_current_cell']))
        results[arm]=bins
    delta={}
    for group,a in results['release'].items():
        b=results['release_vsl90'][group]
        delta[group]={k:b[k]-a[k] for k in a if k!='initial_stock'}
    output=dict(status='COMPLETE_PASSIVE_COHORT_RESPONSE_DIAGNOSIS',cases=results,vsl_minus_release=delta,
        physical_results_bit_exact=status['physical_result_bit_exact'],native_initial_population=1057,
        limitations=['Only initial mainline population is traced; initial on-ramp/urban stock and new entrants are excluded, not lost from objective.',
            'Model tags follow the existing uniform mixing within each currently accepted through/exit class; they are expected mass, not native vehicle identities.',
            'Native events occur at detector offsets; endpoint physical departure counts use offset inventory correction and close every initial identity.',
            'Native moment is not exact physical per-vehicle TTT. Model events use the midpoint of its unchanged1s updates.',
            'Initial positions are pre-control positions, not the location where response occurs; cohorts remain affected by all later traffic.',
            'Unchanged-model diagnostic only. No forecast data leakage, parameter adoption, independent validation pass or9000 qualification.'],
        input_sha256=pins,new_native=0,forecasts=2,fit=0,fzp_reads=0)
    save(dest/'assessment.json',output);save(dest/'native_model_snapshots.json',snapshots);save(dest/'departure_curves.json',curves)
    print(json.dumps(dict(results=results,vsl_minus_release=delta),indent=2))


def native_pair_choices89():
    """Separate same observed exit timing from exit-choice/censoring differences."""
    import bisect
    from collections import defaultdict
    dest=HERE.parent/'cohort_departure89';assert not (dest/'native_choices.json').exists()
    assessment=read(dest/'assessment.json');events=read(HERE.parent/'boundary_time88/events.json')
    geo=read(I/'selected/port_gain/geometry.json')
    chain={int(v['link']):v for v in geo['chains']['FW_E']}
    ends=[v['end_m'] for v in sorted((c for c in geo['cells'] if c['road']=='FW_E'),key=lambda c:c['cell'])]
    folder=Path('D:/VISSIM_runs/20261003_s67_vsl_observation2700/release/decisions_sdmpc31_g_2700_release_s67')
    raw=read(folder/'state_002700.json')
    frame=read(Path(raw['lane_plant_observation']['directory'])/'frame_002700.json')
    initial={v[0]:dict(cell=min(bisect.bisect_right(ends,chain[v[1]]['offset_m']+v[3]),30),route=v[6:9])
             for v in frame['vehicles'] if v[1] in chain}
    lookup={arm:{} for arm in ('release','release_vsl90')}
    for e in events:
        if e['vehicle'] not in initial or not e['ref'].startswith(('off_entry:','chain_end:')):continue
        for arm in lookup:
            if e['case']=='67_release/'+arm:
                assert e['vehicle'] not in lookup[arm],'Multiple exits require explicit reentry analysis'
                lookup[arm][e['vehicle']]=e
    groups=defaultdict(list);matrix=defaultdict(list)
    for vid,init in initial.items():
        if init['cell']>=16:continue
        a=lookup['release'].get(vid);b=lookup['release_vsl90'].get(vid)
        aref=a['ref'] if a else 'remaining';bref=b['ref'] if b else 'remaining'
        category=('both_remaining' if a is None and b is None else 'same_exit' if aref==bref else
                  'different_observed_exits' if a is not None and b is not None else 'one_exit_one_remaining')
        value=(b['signed_moment_veh_h'] if b else 0)-(a['signed_moment_veh_h'] if a else 0)
        row=dict(vehicle=vid,initial=init,baseline_exit=aref,vsl_exit=bref,
            baseline_time=a['time_sec'] if a else None,vsl_time=b['time_sec'] if b else None,delta_departure_moment_veh_h=value)
        groups[category].append(row);matrix[aref+' -> '+bref].append(row)
    summary={k:dict(vehicles=len(v),delta_departure_moment_veh_h=sum(x['delta_departure_moment_veh_h'] for x in v)) for k,v in groups.items()}
    assert sum(v['vehicles'] for v in summary.values())==616
    assert abs(sum(v['delta_departure_moment_veh_h'] for v in summary.values())-assessment['vsl_minus_release']['cells00_15']['native_departure_moment_veh_h'])<1e-9
    out=dict(status='COMPLETE_NATIVE_EXIT_CHOICE_VS_TIMING_ACCOUNTING',population='Common initial mainline cells0..15,616 vehicles',summary=summary,
        transitions={k:dict(vehicles=len(v),delta_departure_moment_veh_h=sum(x['delta_departure_moment_veh_h'] for x in v)) for k,v in matrix.items()},
        vehicle_witnesses=groups,input_sha256=pins,
        limitations=['Same observed exit is a post-outcome subgroup, not an ex-ante control group or causal fixed-route effect.',
            'Different observed exits may reflect later random route choices or route access; initial route keys retained but no cause assigned without route-path audit.',
            'Remaining is horizon censoring, not proof of a different intended destination; no disappearing vehicle is called completed.',
            'Native events keep detector-offset timing limitations; no new fitting or forecast.'])
    save(dest/'native_choices.json',out);print(json.dumps(dict(summary=summary,transitions=out['transitions']),indent=2))


def assess_local_transport91():
    """Score the predeclared two-run candidate; no new prediction or fit."""
    import gzip
    import math
    dest=HERE.parent/'local_transport91'
    assert not (dest/'assessment.json').exists()
    protocol=read(dest/'protocol.json');status=read(dest/'status.json')
    assert status['phase']=='complete_pending_assessment' and not status['future_observation_inputs']
    for p,h in {**protocol['protected_sha256'],**protocol['input_sha256']}.items():
        assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
    old=read(I/'closedloop_recorded2700_lever450_s67_service66_20261003_actuator_equivalent_trace81_path/summary.json')['results']
    new=read(Path(status['output'])/'summary.json')['results']
    actual=read(HERE.parent/'s67_full_observation/response_assessment76.json')
    witnesses=read(dest/'witness.json');geo=read(I/'selected/port_gain/geometry.json')
    lengths=[c['length_km'] for c in geo['cells'] if c['road']=='FW_E']
    details={};max_balance=0.;port_residual=0.
    def metrics(row):
        transfers=[t for block in row['executed_intervals'] for t in block['transfers']]
        return dict(omega=row['ttt_omega_veh_h'],east=row['cost_by_stock']['freeway:FW_E'],
            ramp_cost=sum(v for k,v in row['cost_by_stock'].items() if k.startswith('ramp:')),
            outside=row['tracked_outside_residence_veh_h'],
            terminal=sum(t['vehicles'] for t in transfers if t['source']=='freeway:FW_E' and t['target']=='external:terminal:FW_E'),
            off=sum(block['offramps'][k]['arrival'] for block in row['executed_intervals'] for k in ('10643','10682','10481','10483')),
            merge=sum(row['ramps'][k]['merge'] for k in ('RM_C10639','RM_C10681','RM_C10490','RM_C10484')))
    for arm in ('release','release_vsl90'):
        label=arm+'_actual';before=old[label];after=new[label]
        assert after['commands']==before['commands'] and after['physical_cell_states'][0]==before['physical_cell_states'][0]
        assert len(after['ramps'])==8 and len(after['executed_intervals'])==3
        assert after['validation']['all_actuator_and_step_constraints_checked']
        assert abs(sum(after['cost_by_stock'].values())-after['ttt_omega_veh_h'])<1e-7
        assert not any(b['future_observation_inputs'] for b in after['executed_intervals'])
        wit=next(w for w in witnesses if w['arm']==arm);assert wit['resource_max']<1e-7
        transfers=[t for b in after['executed_intervals'] for t in b['transfers']]
        start=wit['stocks'][0]['stock'];end=wit['stocks'][-1]['stock']
        for key in set(start)|set(end):
            change=sum(t['vehicles'] for t in transfers if t['target']==key)-sum(t['vehicles'] for t in transfers if t['source']==key)
            residual=end.get(key,0.)-start.get(key,0.)-change
            max_balance=max(max_balance,abs(residual));assert abs(residual)<1e-7,(key,residual)
        for b in after['executed_intervals']:
            assert len(b['offramps'])==8
            for key,p in b['offramps'].items():
                residual=p['initial_stock']+p['arrival']-p['drain']-p['final_stock']
                port_residual=max(port_residual,abs(residual));assert abs(residual)<1e-7,(key,residual)
        local=[]
        for label2,model in [('baseline',before),('candidate',after)]:
            for state in model['physical_cell_states'][1:]:
                for cell in (18,19,20,21,24):
                    local.append(dict(model=label2,time_sec=state['time_sec'],cell=cell,
                        n=state['density']['FW_E'][cell]*state['effective_lanes']['FW_E'][cell]*lengths[cell],
                        v=state['speed_kmh']['FW_E'][cell]))
        details[arm]=dict(baseline=metrics(before),candidate=metrics(after),cells=local,
            off10483_intervals={label2:[b['offramps']['10483'] for b in model['executed_intervals']]
                for label2,model in [('baseline',before),('candidate',after)]})
    delta={label:{key:details['release_vsl90'][label][key]-details['release'][label][key]
                 for key in details['release'][label]} for label in ('baseline','candidate')}
    truth={'omega':actual['actual_delta_omega_veh_h'],'terminal':
        actual['arms']['release_vsl90']['mainline']['FW_E']['actual']['terminal']-actual['arms']['release']['mainline']['FW_E']['actual']['terminal']}
    improvements={k:1-abs(delta['candidate'][k]-v)/abs(delta['baseline'][k]-v) for k,v in truth.items()}
    gate=all(improvements[k]>=protocol['gate'][k+'_effect_error_reduction_min'] for k in truth)
    with gzip.open(dest/'steps.json.gz','rt',encoding='utf-8') as stream:steps=json.load(stream)
    applied={arm:sum(any(abs(row['before_vph'][k]-row['after_vph'][k])>1e-8 for k in row['before_vph'])
        for row in steps if row['arm']==arm and row['kind']=='request') for arm in details}
    assert all(n>0 for n in applied.values())
    out=dict(status='COMPLETE_CANDIDATE_EVALUATION',adopted=False,passes_response_gate=gate,
        actual_delta=truth,predicted_delta=delta,effect_error_reduction=improvements,details=details,
        stats=status['stats'],changed_sending_queries=applied,max_full_stock_balance_residual_veh=max_balance,
        max_8off_port_residual_veh=port_residual,successful_forecasts=2,exact_compute_seconds=sum(x['wall_sec'] for x in new.values()),
        preserved_initial_state_and_commands=True,future_observation_inputs=False,input_sha256=pins,
        limitation=protocol['limitations'])
    save(dest/'assessment.json',out)
    print(json.dumps({k:v for k,v in out.items() if k not in ('details','input_sha256')},indent=2))


def assess_state_residual93():
    """Assess actual component residual forecasts against the fixed response gate."""
    import gzip
    import math
    dest=HERE.parent/'state_residual93';run=dest/'attempt3'
    assert not (dest/'assessment.json').exists()
    protocol=read(dest/'protocol.json');status=read(run/'status.json')
    assert status['phase']=='complete_pending_assessment' and not status['future_observation_inputs']
    for p,h in {**protocol['protected_sha256'],**protocol['input_sha256']}.items():
        assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
    old=read(I/'closedloop_recorded2700_lever450_s67_service66_20261003_actuator_equivalent_trace81_path/summary.json')['results']
    new=read(Path(status['output'])/'summary.json')['results']
    actual=read(HERE.parent/'s67_full_observation/response_assessment76.json')
    witnesses=read(run/'witness.json');details={};stock_error=0.;port_error=0.
    def metrics(row):
        transfers=[t for b in row['executed_intervals'] for t in b['transfers']]
        return dict(omega=row['ttt_omega_veh_h'],east=row['cost_by_stock']['freeway:FW_E'],
            ramp_cost=sum(v for k,v in row['cost_by_stock'].items() if k.startswith('ramp:')),
            outside=row['tracked_outside_residence_veh_h'],
            terminal=sum(t['vehicles'] for t in transfers if t['source']=='freeway:FW_E' and t['target']=='external:terminal:FW_E'),
            off=sum(b['offramps'][k]['arrival'] for b in row['executed_intervals'] for k in ('10643','10682','10481','10483')),
            merge=sum(row['ramps'][k]['merge'] for k in ('RM_C10639','RM_C10681','RM_C10490','RM_C10484')))
    for arm in ('release','release_vsl90'):
        label=arm+'_actual';before=old[label];after=new[label]
        assert before['physical_cell_states'][0]==after['physical_cell_states'][0]
        assert before['commands']==after['commands']
        assert len(after['ramps'])==8 and len(after['executed_intervals'])==3
        assert after['validation']['all_actuator_and_step_constraints_checked']
        assert abs(sum(after['cost_by_stock'].values())-after['ttt_omega_veh_h'])<1e-7
        assert not any(b['future_observation_inputs'] for b in after['executed_intervals'])
        witness=next(w for w in witnesses if w['arm']==arm)
        assert witness['resource_max']<1e-7
        transfers=[t for b in after['executed_intervals'] for t in b['transfers']]
        initial=witness['stocks'][0]['stock'];final=witness['stocks'][-1]['stock']
        for key in set(initial)|set(final):
            change=math.fsum(t['vehicles']*((t['target']==key)-(t['source']==key)) for t in transfers)
            error=final.get(key,0.)-initial.get(key,0.)-change
            stock_error=max(stock_error,abs(error));assert abs(error)<1e-7,(key,error)
        for b in after['executed_intervals']:
            assert len(b['offramps'])==8
            for k,p in b['offramps'].items():
                error=p['initial_stock']+p['arrival']-p['drain']-p['final_stock']
                port_error=max(port_error,abs(error));assert abs(error)<1e-7,(k,error)
        details[arm]=dict(baseline=metrics(before),candidate=metrics(after))
    deltas={label:{k:details['release_vsl90'][label][k]-details['release'][label][k]
                   for k in details['release'][label]} for label in ('baseline','candidate')}
    truth=dict(omega=actual['actual_delta_omega_veh_h'],terminal=
        actual['arms']['release_vsl90']['mainline']['FW_E']['actual']['terminal']-
        actual['arms']['release']['mainline']['FW_E']['actual']['terminal'])
    reduction={k:1-abs(deltas['candidate'][k]-v)/abs(deltas['baseline'][k]-v) for k,v in truth.items()}
    passed=deltas['candidate']['omega']<0 and all(v>=.2 for v in reduction.values())
    with gzip.open(run/'steps.json.gz','rt',encoding='utf-8') as f:steps=json.load(f)
    assert len(steps)==1800
    stats={}
    for arm in details:
        rows=[r for r in steps if r['arm']==arm]
        assert len(rows)==900 and {r['cell'] for r in rows}=={19,20}
        assert {r['time_sec'] for r in rows}==set(range(2700,3150))
        stats[arm]=dict(updates=len(rows),changed=sum(abs(r['v_after']-r['canonical_v'])>1e-9 for r in rows),
            projections=sum(r['speed_projection'] for r in rows),outside_box=sum(r['outside_train_box'] for r in rows),
            mean_correction_kmh_per_sec=math.fsum(r['residual_per_sec'] for r in rows)/len(rows),
            max_abs_correction=max(abs(r['residual_per_sec']) for r in rows))
        assert stats[arm]['changed']>0
    out=dict(status='COMPLETE_REJECTED_RESIDUAL' if not passed else 'COMPLETE_PAIR_PENDING_BROADER_VALIDATION',
        adopted=False,passes_response_gate=passed,actual_delta=truth,predicted_delta=deltas,
        effect_error_reduction=reduction,details=details,correction_stats=stats,
        max_full_stock_balance_residual_veh=stock_error,max_off_port_balance_residual_veh=port_error,
        successful_forecasts=2,exact_compute_seconds=sum(x['wall_sec'] for x in new.values()),
        nominal_config_failure_preserved=True,actual_component_screen=read(run/'fit.json')['scores'],
        protected_and_input_pins_unchanged=True,future_observation_inputs=False,source_sha256=pins)
    save(dest/'assessment.json',out)
    print(json.dumps({k:v for k,v in out.items() if k not in ('source_sha256','details')},indent=2))


def assess_response_horizon98():
    """Compare control-difference propagation using completed observation bundles."""
    import ast
    dest = HERE.parent / 'response_horizon98'
    assert not (dest / 'assessment.json').exists(), 'Preserve completed assessment'
    protocol = read(dest / 'protocol.json')
    geo = read(I / 'selected/port_gain/geometry.json')
    assert geo['network']['sha256'] == '64cf5f55fe9990f3e25bc4fedebf4ab1e4634c8138dbcf5697a136c48cb559dc'
    ports = [b for b in geo['boundaries'] if b['road'] == 'FW_E']
    ramps = [b for b in ports if b['kind'] == 'ramp']
    exits = [b for b in ports if b['kind'] == 'offramp']
    links = {int(x['link']) for x in geo['chains']['FW_E']}
    folder = I / 'closedloop_recorded2700_lever450_s73_replication95'
    summary = read(folder / 'summary.json')
    audit = read(folder / 'ramp_response_audit.json')['arms']
    snap = read(HERE.parent / 'replication_s73_95/snapshot_errors95.json')
    stock = {(r['arm'],r['time_sec'],r['cell']):r['actual_stock'] for r in snap}
    for cell in range(31):
        assert stock['release',2700,cell] == stock['release_vsl90',2700,cell]
    rows = [dict(seed=67, **r) for r in read(HERE / 'cell_flux82.json')
            if r['case'] in ('release','release_vsl90')]
    boundaries = []
    for arm in ('release','release_vsl90'):
        pred = summary['results'][arm+'_actual']
        ca, cp = {c:0. for c in range(-1,31)}, {c:0. for c in range(-1,31)}
        cm, co = {c:0. for c in range(31)}, {c:0. for c in range(31)}
        for b in pred['executed_intervals']:
            start,end = b['start_sec'],b['end_sec']
            raw_path = (Path('D:/VISSIM_runs/20261003_s73_vsl_replication95') / arm /
                        f'decisions_sdmpc31_g_2700_{arm}_s73' / f'state_{int(end):06d}.json')
            raw = read(raw_path)
            obs = raw['obs150']
            detectors,_ = oc.read_detector_csv(obs['detector_config']['path'],obs['detector_config']['sha256'])
            oc.validate_raw(obs,detectors,expected_simres=10)
            check_rule_crosscheck(obs,detectors)
            bundle = oc.load_bundle(raw)
            boundary = oc.evaluate_boundaries(obs,detectors,bundle.frame_end,bundle.frame_start,bundle.err_rows)
            assert obs['window'] == dict(start_s=start,end_s=end)
            assert not [x for x in oc.window_removals(bundle.err_rows,start,end) if int(x['link']) in links]
            am = {r['to_cell']:next(w['merge'] for w in audit[arm][r['id']]['actual']['windows']
                                 if w['start_sec']==start and w['end_sec']==end) for r in ramps}
            ao = {r['from_cell']:boundary['off_entry:'+str(r['connector'])].cross for r in exits}
            n0 = [stock[arm,start,c] for c in range(31)]
            n1 = [stock[arm,end,c] for c in range(31)]
            af = cell_flux(n0,n1,boundary['source:FW_E'].cross,boundary['chain_end:FW_E'].cross,am,ao)
            flow = lambda s,t:sum(x['vehicles'] for x in b['transfers'] if x['source']==s and x['target']==t)
            pm = {r['to_cell']:flow('merge_pending:'+r['id'],'freeway:FW_E') for r in ramps}
            stores = {v['connector']:v['storage'] for v in b['offramps'].values()}
            po = {r['from_cell']:flow('freeway:FW_E','storage:'+stores[r['connector']]) for r in exits}
            s0,s1 = b['physical_cell_states']
            p0,p1 = s0['vehicle_count']['FW_E'],s1['vehicle_count']['FW_E']
            pf = cell_flux(p0,p1,flow('origin:FW_E','freeway:FW_E'),
                           flow('freeway:FW_E','external:terminal:FW_E'),pm,po)
            for c in range(-1,31):
                ca[c] += af[c]
                cp[c] += pf[c]
            for c in range(31):
                cm[c] += pm.get(c,0.)-am.get(c,0.)
                co[c] += po.get(c,0.)-ao.get(c,0.)
                incoming = cp[c-1]-ca[c-1]+cm[c]
                outgoing = cp[c]-ca[c]+co[c]
                assert abs(pred['executed_intervals'][0]['physical_cell_states'][0]['vehicle_count']['FW_E'][c]-stock[arm,2700,c]) < 1e-7
                residual = p1[c]-n1[c]-incoming+outgoing
                assert abs(residual) < 1e-7
                rows.append(dict(seed=73,case=arm,start_sec=start,end_sec=end,cell=c,
                    native_through=af[c],predicted_through=pf[c],cumulative_native_through=ca[c],
                    cumulative_predicted_through=cp[c],actual_stock=n1[c],predicted_stock=p1[c],
                    cumulative_incoming_error=incoming,cumulative_outgoing_error=outgoing,conservation_error=residual))
            boundaries.append(dict(seed=73,arm=arm,start_sec=start,end_sec=end,
                actual_source=af[-1],predicted_source=pf[-1],actual_terminal=af[30],predicted_terminal=pf[30],
                actual_merge=am,predicted_merge=pm,actual_off=ao,predicted_off=po))
    prior = read(HERE.parent / 'replication_s73_95/response_assessment95.json')
    # Reconcile the new150-second reconstruction to the prior completed450 totals.
    checks = []
    for arm in ('release','release_vsl90'):
        bs = [b for b in boundaries if b['arm']==arm]
        totals = dict(source=sum(b['actual_source'] for b in bs),terminal=sum(b['actual_terminal'] for b in bs),
                      merge=sum(sum(b['actual_merge'].values()) for b in bs),off=sum(sum(b['actual_off'].values()) for b in bs))
        previous = prior['arms'][arm]['native_boundaries450']
        assert totals['source']==previous['source:FW_E']
        assert totals['terminal']==previous['chain_end:FW_E']
        assert totals['off']==sum(previous['off_entry:'+str(r['connector'])] for r in exits)
        assert totals['merge']==sum(audit[arm][r['id']]['actual']['merge'] for r in ramps)
        checks.append(dict(arm=arm,totals=totals,agrees_with_previous450=True))
    paired = []
    for seed in (67,73):
        for end in (2850,3000,3150):
            for c in range(31):
                a = next(r for r in rows if (r['seed'],r['case'],r['end_sec'],r['cell'])==(seed,'release',end,c))
                b = next(r for r in rows if (r['seed'],r['case'],r['end_sec'],r['cell'])==(seed,'release_vsl90',end,c))
                paired.append(dict(seed=seed,start_sec=end-150,end_sec=end,cell=c,
                    actual_interval_through_delta=b['native_through']-a['native_through'],
                    predicted_interval_through_delta=b['predicted_through']-a['predicted_through'],
                    actual_cumulative_through_delta=b['cumulative_native_through']-a['cumulative_native_through'],
                    predicted_cumulative_through_delta=b['cumulative_predicted_through']-a['cumulative_predicted_through'],
                    actual_stock_delta=b['actual_stock']-a['actual_stock'],
                    predicted_stock_delta=b['predicted_stock']-a['predicted_stock'],
                    baseline_stock_error=a['predicted_stock']-a['actual_stock'],
                    differential_stock_error=(b['predicted_stock']-a['predicted_stock'])-(b['actual_stock']-a['actual_stock'])))
    tree = ast.parse(Path(__file__).read_text(encoding='utf-8'))
    functions = {n.name:ast.dump(n,include_attributes=False) for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
    assert all(functions[k]==v for k,v in protocol['helper_old_ast'].items())
    for p,h in protocol['production_pins'].items():
        assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h,p
    stop=protocol['old_STOP'];assert hashlib.sha256(Path(stop['path']).read_bytes()).hexdigest()==stop['sha256']
    save(dest/'cell_flux.json',rows)
    save(dest/'paired_cell_flux.json',paired)
    save(dest/'boundaries73.json',boundaries)
    save(dest/'assessment.json',dict(status='COMPLETE_CACHED_PAIRED_RESPONSE_DIAGNOSTIC',
        new_forecasts=0,new_native=0,fits=0,fzp_scans=0,seed73_bundle_windows=6,paired_cell_windows=len(paired),
        max_conservation_error=max(abs(r['conservation_error']) for r in rows),
        production_and_stop_unchanged=True,old_helper_functions_unchanged=len(protocol['helper_old_ast']),
        totals_checks=checks,inputs_sha256=pins,limits=protocol['limits']))
    print(json.dumps(dict(rows=len(rows),paired=len(paired),checks=checks),indent=2))


def assess_recovery_band102():
    """Conserved recovery-band attribution using completed current-model replays."""
    import ast
    import math
    dest = HERE.parent / 'recovery_band102'
    assert not (dest/'assessment.json').exists(), 'Preserve completed result'
    protocol = read(dest/'protocol.json')
    source = [dict(seed=67, **r) for r in read(HERE/'cell_flux82.json')]
    source += [r for r in read(HERE.parent/'response_horizon98/cell_flux.json') if r['seed']==73]
    grouped = {(r['seed'],r['case'],r['end_sec'],r['cell']):r for r in source}
    assert len(grouped)==len(source)
    cases = sorted({(r['seed'],r['case']) for r in source})
    rows, checks = [], []
    components = ('mainline_in_error','merge10490_error','merge10484_error','discharge_error')
    for seed, case in cases:
        prior = {k:0. for k in components}
        last_stock_error = 0.
        for end in protocol['sample']['ends']:
            band = {c:grouped[seed,case,end,c] for c in range(20,26)}
            through_error = lambda c: band[c]['cumulative_predicted_through']-band[c]['cumulative_native_through']
            values = dict(mainline_in_error=through_error(20),
                merge10490_error=band[21]['cumulative_incoming_error']-through_error(20),
                merge10484_error=band[23]['cumulative_incoming_error']-through_error(22),
                discharge_error=through_error(25))
            actual_n = math.fsum(band[c]['actual_stock'] for c in range(21,26))
            predicted_n = math.fsum(band[c]['predicted_stock'] for c in range(21,26))
            nerr = predicted_n-actual_n
            balance = values['mainline_in_error']+values['merge10490_error']+values['merge10484_error']-values['discharge_error']
            assert abs(nerr-balance)<1e-7
            inc = {k:values[k]-prior[k] for k in components}
            incremental_balance = inc['mainline_in_error']+inc['merge10490_error']+inc['merge10484_error']-inc['discharge_error']
            assert abs(nerr-last_stock_error-incremental_balance)<1e-7
            row=dict(seed=seed,case=case,end_sec=end,actual_stock=actual_n,predicted_stock=predicted_n,
                     stock_error=nerr,carried_stock_error=last_stock_error,cumulative=values,interval=inc,
                     balance_residual=nerr-balance,
                     actual_discharge=band[25]['cumulative_native_through'],predicted_discharge=band[25]['cumulative_predicted_through'])
            rows.append(row)
            for c in range(21,26):
                r=band[c]
                residual=r['predicted_stock']-r['actual_stock']-r['cumulative_incoming_error']+r['cumulative_outgoing_error']
                assert abs(residual)<1e-7
                checks.append(dict(seed=seed,case=case,end_sec=end,cell=c,stock_error=r['predicted_stock']-r['actual_stock'],
                                   incoming_error=r['cumulative_incoming_error'],outgoing_error=r['cumulative_outgoing_error'],residual=residual))
            prior=values;last_stock_error=nerr
    pairs=[]
    for seed,nominal,reduced in ((67,'release','release_vsl90'),(67,'selected','vsl90'),(73,'release','release_vsl90')):
        for end in protocol['sample']['ends']:
            a=next(r for r in rows if (r['seed'],r['case'],r['end_sec'])==(seed,nominal,end))
            b=next(r for r in rows if (r['seed'],r['case'],r['end_sec'])==(seed,reduced,end))
            pairs.append(dict(seed=seed,nominal=nominal,reduced=reduced,end_sec=end,
                actual_stock_delta=b['actual_stock']-a['actual_stock'],predicted_stock_delta=b['predicted_stock']-a['predicted_stock'],
                actual_discharge_delta=b['actual_discharge']-a['actual_discharge'],predicted_discharge_delta=b['predicted_discharge']-a['predicted_discharge'],
                error_delta={k:b['cumulative'][k]-a['cumulative'][k] for k in components}))
    funcs={n.name:ast.dump(n,include_attributes=False) for n in ast.parse(Path(__file__).read_text(encoding='utf-8')).body if isinstance(n,ast.FunctionDef)}
    assert all(funcs[k]==v for k,v in protocol['old_helper_ast'].items())
    for p,h in protocol['protected_sha256'].items():
        assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h,p
    assert hashlib.sha256(Path(protocol['STOP']['path']).read_bytes()).hexdigest()==protocol['STOP']['sha256']
    assessment=dict(status='COMPLETE_CURRENT_MODEL_RECOVERY_BAND_DIAGNOSTIC',cases=cases,regional_balances=len(rows),cell_balances=len(checks),
        maximum_residual=max(abs(r['balance_residual']) for r in rows),input_sha256=pins,limits=protocol['limits'],
        new_forecasts=0,new_native=0,fzp_scans=0,fit=False,production_changed=False,gain_qualified=False)
    for name,value in [('assessment',assessment),('regions',rows),('cells',checks),('paired',pairs)]:
        save(dest/(name+'.json'),value)
    print(json.dumps(dict(first150=[r for r in rows if r['end_sec']==2850],pairs=pairs),indent=2))


def prepare_ramp_timing103():
    """Isolate the existing initial-position option; no service/receiving fit."""
    import ast
    import copy
    dest = HERE.parent / 'ramp_timing103'
    assert not dest.exists(), 'Preserve completed or failed attempts'
    dest.mkdir()
    source = Path(__file__).read_bytes()
    (dest / 'assessor_setup.py').write_bytes(source)
    p67 = read(HERE / 'protocol_path.json')['jobs'][0]
    p73 = read(HERE.parent / 'replication_s73_95/postprocess_plan.json')
    base = HERE.parent / 'rm47_service66_response/candidate_config.json'
    config = read(base)
    assert 'initial_gate_geometry_timing' not in config['urban']['ramp']
    assert config['urban']['ramp']['initial_gate_city_lock']
    assert config['urban']['ramp']['native_gate_travel']
    candidate = copy.deepcopy(config)
    candidate['urban']['ramp']['initial_gate_geometry_timing'] = True
    save(dest / 'candidate_config.json', candidate)
    restored = copy.deepcopy(candidate)
    del restored['urban']['ramp']['initial_gate_geometry_timing']
    assert restored == config
    jobs = []
    for seed, argv, old_output in (
        (67, p67['argv'], p67['output']),
        (73, p73['commands']['forecast'], p73['prediction']),
    ):
        argv = [a for a in argv if not a.startswith('--output-suffix=')]
        argv = [('--tuning-json=' + str(dest / 'candidate_config.json') if a.startswith('--tuning-json=')
                 else '--probe-label=s%d_timing103' % seed if a.startswith('--probe-label=') else a)
                for a in argv]
        output = I / ('closedloop_recorded2700_lever450_s%d_timing103' % seed)
        assert not output.exists()
        jobs.append(dict(seed=seed, argv=argv, baseline=old_output, output=str(output)))
    rows = []
    for job in jobs:
        seed = job['seed']
        folder = Path(job['baseline'])
        summary = read(folder / 'summary.json')['results']
        audit_path = (I / 'closedloop_recorded2700_lever450_s67_service66_20261003_actuator_equivalent/ramp_response_audit.json'
                      if seed == 67 else folder / 'ramp_response_audit.json')
        actual = read(audit_path)['arms']
        job['audit'] = str(audit_path)
        for arm in ('release', 'release_vsl90'):
            for block, interval in enumerate(summary[arm + '_actual']['executed_intervals']):
                for ramp, predicted in interval['ramps'].items():
                    a = actual[arm][ramp]['actual']['windows'][block]
                    arrival_error = predicted['arrival'] - a['arrival']
                    head_error = predicted['head'] - a['head']
                    merge_error = predicted['merge'] - a['merge']
                    # Delta-stock error, not absolute stock: initial interval error may persist.
                    prehead_change_error = arrival_error - head_error
                    posthead_change_error = head_error - merge_error
                    end_error = predicted['final_stock'] - a['final_stock']
                    initial_actual = (actual[arm][ramp]['actual']['initial_stock'] if block == 0
                                      else actual[arm][ramp]['actual']['windows'][block-1]['final_stock'])
                    initial_error = predicted['initial_stock'] - initial_actual
                    assert a['removals'] == 0
                    assert abs(end_error-initial_error-prehead_change_error-posthead_change_error) < 1e-7
                    rows.append(dict(seed=seed, arm=arm, ramp=ramp, start_sec=interval['start_sec'],
                        end_sec=interval['end_sec'], actual=a, predicted=predicted,
                        arrival_error=arrival_error, head_error=head_error, merge_error=merge_error,
                        prehead_stock_change_error=prehead_change_error,
                        posthead_stock_change_error=posthead_change_error))
    save(dest / 'baseline_decomposition.json', rows)
    prior = read(HERE.parent / 'recovery_band102/protocol.json')
    for path, digest in prior['protected_sha256'].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest, path
    save(dest / 'protocol.json', dict(
        previous_goal_turn='PROGRESS: REVIEW102 completed independent regional and cell flux balances; final report pending.',
        hypothesis='Initial gate cohorts arrive too early; reuse existing geometry timing alone on current service66 model.',
        difference={'urban.ramp.initial_gate_geometry_timing': [False, True]},
        prior_work=['loss_onset2250/head10490_timing', 'head10490_timing/response',
                    'posthead_clock10490/response43'],
        novelty='Current service66 model, geometry timing alone without origin-supply or posthead-speed candidates;67/73 unchanged executed commands.',
        max_forecasts=4, optimizer_iterations=0, new_native_runs=0, fzp_scans=0, fit=False,
        acceptance=['Check first150 arrival/head/merge and all eight ramp balances.',
                    'Separate absolute state error from same-initial-state VSL delta cost.',
                    'Do not promote if material control ranking worsens or remaining gain errors persist.',
                    'No parameter grid, future traffic inputs, automatic retries, or live runtime edits.'],
        protected_sha256=prior['protected_sha256'], STOP=prior['STOP'], source_sha256=pins,
        helper_ast={n.name:ast.dump(n,include_attributes=False) for n in ast.parse(source).body
                    if isinstance(n,ast.FunctionDef)}, jobs=jobs))
    print(json.dumps(dict(prepared=True, rows=len(rows), max_forecasts=4,
        first150_10490=[r for r in rows if r['ramp']=='RM_C10490' and r['end_sec']==2850]), indent=2))


def assess_ramp_timing103(seed):
    dest = HERE.parent / 'ramp_timing103'
    target = dest / ('assessment%d.json' % seed)
    assert not target.exists(), 'Reuse the completed assessment'
    protocol = read(dest / 'protocol.json')
    job = next(j for j in protocol['jobs'] if j['seed'] == seed)
    status = read(dest / ('run%d_fixed.json' % seed))
    assert status['stage'] == 'COMPLETE' and status['exit_code'] == 0
    baseline = read(Path(job['baseline']) / 'summary.json')['results']
    candidate = read(Path(status['output']) / 'summary.json')['results']
    native = read(Path(job['audit']))['arms']
    horizon = read(HERE.parent / 'horizon97/assessment.json')
    rows = []
    for arm in ('release','release_vsl90'):
        old, new = baseline[arm+'_actual'], candidate[arm+'_actual']
        assert old['commands'] == new['commands']
        assert old['executed_control_blocks'] == new['executed_control_blocks']
        assert len(new['executed_intervals']) == 3
        for b,(ob,nb) in enumerate(zip(old['executed_intervals'],new['executed_intervals'])):
            assert nb['future_observation_inputs'] is False
            assert (ob['start_sec'],ob['end_sec']) == (nb['start_sec'],nb['end_sec'])
            for ramp,pred in nb['ramps'].items():
                a=native[arm][ramp]['actual']['windows'][b]
                assert abs(pred['initial_stock']+pred['arrival']-pred['merge']-pred['final_stock']) < 1e-7
                if b==0:assert pred['initial_stock']==ob['ramps'][ramp]['initial_stock']
                rows.append(dict(seed=seed,arm=arm,ramp=ramp,end_sec=nb['end_sec'],actual=a,
                    old=ob['ramps'][ramp],new=pred))
    cost=[]
    for index,lead in enumerate((150,300,450)):
        actual=next(r for r in horizon['pair_intervals'] if
            (r['seed'],r['reference'],r['candidate'],r['lead_end_sec']) == (seed,'release','release_vsl90',lead))
        values={}
        for name,model in [('old',baseline),('new',candidate)]:
            values[name]=model['release_vsl90_actual']['executed_intervals'][index]['ttt_omega_veh_h']-model['release_actual']['executed_intervals'][index]['ttt_omega_veh_h']
        cost.append(dict(lead_end_sec=lead,actual=actual['actual_delta_ttt_veh_h'],**values))
    totals={key:sum(x[key] for x in cost) for key in ('actual','old','new')}
    first=[r for r in rows if r['end_sec']==2850]
    errors={ramp:{model:{metric:sum(abs(r[model][metric]-r['actual'][metric]) for r in first
                                      if ramp=='all8' or r['ramp']==ramp)
                for metric in ('arrival','head','merge','final_stock')} for model in ('old','new')}
            for ramp in ('RM_C10490','RM_C10482','all8')}
    runt=read(Path(status['output'])/'runtime.json')
    for path,digest in protocol['protected_sha256'].items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest
    stop=protocol['STOP'];assert hashlib.sha256(Path(stop['path']).read_bytes()).hexdigest()==stop['sha256']
    assessment=dict(status='COMPLETE_RESPONSE_DIAGNOSTIC_NOT_PROMOTED',seed=seed,
        first150_absolute_error_sum=errors,delta_omega_vsl90_minus110=totals,
        disjoint150_delta_omega=cost,ramp_windows=rows,
        same_commands=True,initial8ramps_identical=True,ramps_conserved=True,
        native_reused=True,new_native=0,fit=False,future_observation_inputs=False,
        limits=['Two policies within a seed are correlated, not independent replications.',
                'Initialization only: downstream recovery and autonomous VSL response may still fail.',
                'RM schedules held identical within each pair; no new RM choice or SDMPC derivative validation.'],
        source_sha256=pins)
    save(target,assessment)
    print(json.dumps({k:assessment[k] for k in ('seed','first150_absolute_error_sum',
        'delta_omega_vsl90_minus110','disjoint150_delta_omega')},indent=2))


def finish_ramp_timing103():
    import ast
    dest=HERE.parent/'ramp_timing103'
    assert not (dest/'completion.json').exists()
    protocol=read(dest/'protocol.json')
    actual={}
    for r in read(HERE/'cell_errors.json'):
        actual[67,r['case'],r['time_sec'],r['cell']]=(r['observed_stock'],r['observed_speed_kmh'])
    for r in read(HERE.parent/'replication_s73_95/snapshot_errors95.json'):
        actual[73,r['arm'],r['time_sec'],r['cell']]=(r['actual_stock'],r['actual_speed_kmh'])
    spatial=[];posthead=[];decisions=[]
    for seed in (67,73):
        a=read(dest/('assessment%d.json'%seed))
        job=next(j for j in protocol['jobs'] if j['seed']==seed)
        run=read(dest/('run%d_fixed.json'%seed))
        old=read(Path(job['baseline'])/'summary.json')['results']
        new=read(Path(run['output'])/'summary.json')['results']
        for arm in ('release','release_vsl90'):
            for ob,nb in zip(old[arm+'_actual']['executed_intervals'],new[arm+'_actual']['executed_intervals']):
                assert ob['physical_cell_states'][0]==nb['physical_cell_states'][0] if ob['start_sec']==2700 else True
                o,n=ob['physical_cell_states'][-1],nb['physical_cell_states'][-1]
                for cell in (19,21,22,23,24,25):
                    stock,speed=actual[seed,arm,ob['end_sec'],cell]
                    spatial.append(dict(seed=seed,arm=arm,time_sec=ob['end_sec'],cell=cell,
                        actual_stock=stock,actual_speed=speed,
                        old_stock=o['vehicle_count']['FW_E'][cell],new_stock=n['vehicle_count']['FW_E'][cell],
                        old_speed=o['speed_kmh']['FW_E'][cell],new_speed=n['speed_kmh']['FW_E'][cell]))
        for row in a['ramp_windows']:
            if row['ramp']=='RM_C10490' and row['end_sec']==2850:
                native_change=row['actual']['head']-row['actual']['merge']
                posthead.append(dict(seed=seed,arm=row['arm'],
                    old_error=(row['old']['head']-row['old']['merge'])-native_change,
                    new_error=(row['new']['head']-row['new']['merge'])-native_change))
        decisions.append(dict(seed=seed,**a['delta_omega_vsl90_minus110']))
    nodes={n.name:ast.dump(n,include_attributes=False) for n in ast.parse(Path(__file__).read_bytes()).body
           if isinstance(n,ast.FunctionDef)}
    assert all(nodes[k]==v for k,v in protocol['helper_ast'].items())
    for path,digest in protocol['protected_sha256'].items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest
    for name in ('physical_ramp_branches.py','lane_offramp_runtime.py'):
        assert (dest/'migration_fix'/(name+'.executed')).read_bytes()==(ROOT/'evaluation/controllers'/name).read_bytes()
    stop=protocol['STOP'];assert hashlib.sha256(Path(stop['path']).read_bytes()).hexdigest()==stop['sha256']
    assert read(dest/'migration_fix/default_parity.json')['passed']
    save(dest/'spatial.json',spatial)
    save(dest/'decision.json',dict(status='NOT_PROMOTED_GAIN_RESPONSE_STILL_FAILS',cost=decisions,
        first150_posthead_stock_change_errors=posthead,
        finding='10490 merge totals improve but posthead stock errors remain; independent73 initial arrival gets worse. VSL gain still missed.',
        next='Reuse current model regional discharge evidence; do not repeat geometry/FD parameter grids or override receiving to force gain.'))
    save(dest/'completion.json',dict(status='COMPLETE_DIAGNOSTIC_OPTION_DEFAULT_OFF_NOT_GAIN_QUALIFIED',
        previous_goal_turn='PROGRESS',this_goal_turn='PROGRESS',successful_forecasts=6,
        regression_forecasts=2,candidate_forecasts=4,failed_initializations=1,optimizer_iterations=0,
        new_native=0,fzp_scans=0,fit=False,push=False,live_frozen_runtime_changed=False,
        migration_tests='53 passed, 8 subtests passed',same_effective_commands=True,
        initial_freeway_and8ramp_states_identical=True,all8ramp_interval_balances_pass=True,
        old_helper_functions_preserved=len(protocol['helper_ast']),protected7_and_STOP_unchanged=True,
        changed_production_files=['evaluation/controllers/physical_ramp_branches.py','evaluation/controllers/lane_offramp_runtime.py'],
        adoption='Default disabled; compatible reservation migration retained. No claim of improved gain model.',source_sha256=pins))
    print(json.dumps(dict(cost=decisions,posthead=posthead),indent=2))


def assess_discharge104():
    """Audit cached flow and velocity identities; no simulator or fitting calls."""
    import ast
    import gzip
    import math
    import statistics

    dest = HERE.parent / 'discharge104'
    assert not (dest / 'completion.json').exists()
    protocol = read(dest / 'protocol.json')
    binding = read(HERE.parent / 'physical_binding94/binding.json')
    geo = read(I / 'selected/port_gain/geometry.json')
    flux = read(HERE.parent / 'response_horizon98/cell_flux.json')
    flows = {(r['seed'], r['case'], r['start_sec'], r['cell']): r for r in flux}
    off_cells = {b['from_cell'] for b in geo['boundaries']
                 if b['road'] == 'FW_E' and b['kind'] == 'offramp'}
    lanes = binding['expected']['FW_E']['lanes']
    tested = (16, 17, 19, 21, 22, 23, 24, 25)
    assert not set(tested) & off_cells
    folders = {
        67: I / 'closedloop_recorded2700_lever450_s67_service66_20261003_actuator_equivalent_trace81_path',
        73: I / 'closedloop_recorded2700_lever450_s73_replication95',
    }
    identities, differences, dynamics, term_differences = [], [], [], []
    max_recurrence = max_equation_residual = 0.
    keys = ('relaxation', 'convection', 'anticipation', 'lane_drop_raw',
            'post_equation_change', 'clip_correction')
    for seed, folder in folders.items():
        traces = {}
        for arm in ('release', 'release_vsl90'):
            path = folder / (arm + '.terms.gz')
            data = path.read_bytes()
            pins[str(path)] = hashlib.sha256(data).hexdigest()
            rows = json.loads(gzip.decompress(data))
            assert len(rows) == 4500
            trace = {(r['cell'], r['time_sec']): r for r in rows}
            assert len(trace) == len(rows)
            traces[arm] = trace
            for cell in range(16, 26):
                for time in range(2700, 3150):
                    r = trace[cell, time]
                    assert all(math.isfinite(v) for v in r.values())
                    assert min(r['rho'], r['speed_before']) >= 0
                    raw = (r['speed_before'] + r['relaxation'] + r['convection']
                           + r['anticipation'] - r['lane_drop_raw'])
                    r['clip_correction'] = r['after_speed_equation'] - raw
                    if time < 3149:
                        max_recurrence = max(max_recurrence, abs(
                            r['speed_final'] - trace[cell, time+1]['speed_before']))
                for start in (2700, 2850, 3000):
                    window = [trace[cell, time] for time in range(start, start+150)]
                    terms = {k: math.fsum(r[k] for r in window) for k in keys}
                    change = window[-1]['speed_final'] - window[0]['speed_before']
                    reconstructed = sum(terms[k] for k in keys if k != 'lane_drop_raw') - terms['lane_drop_raw']
                    max_equation_residual = max(max_equation_residual, abs(change-reconstructed))
                    dynamics.append(dict(seed=seed, arm=arm, cell=cell, start_sec=start,
                        end_sec=start+150, velocity_change_kmh=change, term_sums_kmh=terms,
                        means={k: statistics.mean(r[k] for r in window) for k in
                            ('speed_before', 'rho', 'downstream_rho', 'desired')},
                        max_abs_clip_correction=max(abs(r['clip_correction']) for r in window)))
                    if cell not in tested:
                        continue
                    potential = math.fsum(r['rho']*r['speed_before']*lanes[cell]/3600 for r in window)
                    f = flows[seed, arm, start, cell]
                    identities.append(dict(seed=seed, arm=arm, cell=cell, start_sec=start,
                        end_sec=start+150, integrated_rho_v_lanes_veh=potential,
                        accepted_through_veh=f['predicted_through'], native_through_veh=f['native_through'],
                        suppression_veh=potential-f['predicted_through'],
                        model_minus_native_veh=f['predicted_through']-f['native_through']))
        for cell in range(16, 26):
            for start in (2700, 2850, 3000):
                dr = [next(r for r in dynamics if (r['seed'], r['arm'], r['cell'], r['start_sec'])
                           == (seed, arm, cell, start)) for arm in ('release', 'release_vsl90')]
                terms = {k: dr[1]['term_sums_kmh'][k]-dr[0]['term_sums_kmh'][k] for k in keys}
                term_differences.append(dict(seed=seed, cell=cell, start_sec=start,
                    velocity_change_difference_kmh=dr[1]['velocity_change_kmh']-dr[0]['velocity_change_kmh'],
                    term_difference_sums_kmh=terms))
                if cell not in tested:
                    continue
                pairs = [(traces['release'][cell, time], traces['release_vsl90'][cell, time])
                         for time in range(start, start+150)]
                density = math.fsum(lanes[cell]*(b['rho']-a['rho'])*(b['speed_before']+a['speed_before'])/7200
                                    for a, b in pairs)
                speed = math.fsum(lanes[cell]*(b['speed_before']-a['speed_before'])*(b['rho']+a['rho'])/7200
                                  for a, b in pairs)
                a, b = (flows[seed, arm, start, cell] for arm in ('release', 'release_vsl90'))
                delta = b['predicted_through']-a['predicted_through']
                assert abs(density+speed-delta) < 1e-7
                differences.append(dict(seed=seed, cell=cell, start_sec=start, end_sec=start+150,
                    actual_delta_through_veh=b['native_through']-a['native_through'],
                    predicted_delta_through_veh=delta, density_product_component_veh=density,
                    speed_product_component_veh=speed))
    assert len(identities) == 96 and len(differences) == 48 and len(dynamics) == 120
    max_suppression = max(abs(r['suppression_veh']) for r in identities)
    assert max_suppression < 1e-7 and max_recurrence < 1e-9 and max_equation_residual < 1e-8
    old = {n.name: hashlib.sha256(ast.dump(n, include_attributes=False).encode()).hexdigest()
           for n in ast.parse(Path(__file__).read_bytes()).body if isinstance(n, ast.FunctionDef)}
    assert all(old[name] == digest for name, digest in protocol['helper_ast_sha256'].items())
    for path, digest in protocol['protected_sha256'].items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest() == digest, path
    stop = protocol['STOP']
    assert hashlib.sha256(Path(stop['path']).read_bytes()).hexdigest() == stop['sha256']
    for path, digest in list(pins.items()):
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest, path
    save(dest/'flow_identities.json', identities)
    save(dest/'flow_response.json', differences)
    save(dest/'speed_terms.json', dynamics)
    save(dest/'speed_response.json', term_differences)
    result = dict(status='COMPLETE_CACHED_DISCHARGE_DIAGNOSTIC_NOT_GAIN_QUALIFIED',
        previous_goal_turn='PROGRESS', this_goal_turn='PROGRESS',
        flow_checks=len(identities), paired_flow_checks=len(differences), speed_update_checks=len(dynamics)*150,
        max_suppression_veh=max_suppression, max_recurrence_error_kmh=max_recurrence,
        max_velocity_identity_error_kmh=max_equation_residual,
        source_sha256=pins.copy(), old_helper_functions_unchanged=len(protocol['helper_ast_sha256']),
        protected9_and_STOP_unchanged=True, forecast=0, fit=0, native=0, fzp=0, push=False,
        scope=protocol['scope'], limitations=protocol['limits'],
        finding='Tested internal through-flow already equals rho*v*lanes. Raising receiving limits cannot repair these cached discharge deficits. Seed73 response differs at cell19, before recovery cells24/25.',
        next='Inspect baseline congestion formation/transport around cells18-20 jointly with downstream recovery. Do not repeat rejected FD/tau/nu/joint-lane grids or infer a VSL capacity bonus.')
    save(dest/'completion.json', result)
    print(json.dumps({k:v for k,v in result.items() if k != 'source_sha256'}, indent=2))


def assess_lane_drop105():
    """One nominal current-state coefficient screen, never an autonomous claim."""
    import ast
    import copy
    import gzip
    import math
    from evaluation.controllers import lane_plant_runtime as lpr

    dest = HERE.parent/'lane_drop105'
    assert not (dest/'completion.json').exists()
    protocol = read(dest/'protocol.json')
    context = lpr.load_sources(ROOT/protocol['manifest'])
    from evaluation.controllers import area_freeway_accounting as accounting
    from evaluation.controllers import vissim_stackelberg_adapter as adapter
    from evaluation.controllers.freeway_fd import state_response_coefficients
    from src.models.state import ControlAction
    cfg = context['component']._config('FW_E', context['parameters']['by_direction']['FW_E'])
    net = cfg.network
    mn = accounting._mn
    control = ControlAction(vsl={'FW_E': 110})
    binding = read(HERE.parent/'physical_binding94/binding.json')['expected']['FW_E']
    assert net.freeway_segment_params['FW_E'][18] == binding['cells'][18]
    rows, excluded = [], []
    for seed_text, name in protocol['inputs'].items():
        path = ROOT/name
        data = path.read_bytes()
        pins[str(path)] = hashlib.sha256(data).hexdigest()
        source = json.loads(gzip.decompress(data))
        frames = {round(float(t), 6): z for t, z in source['frames'].items()}
        for time in sorted(frames)[:-1]:
            now, later = frames[time], frames[round(time+5, 6)]
            groups = {c: [z for z in now.values() if z[0] == c] for c in (17, 18, 19)}
            future = [z for z in later.values() if z[0] == 18]
            if min(map(len, groups.values())) == 0 or not future:
                excluded.append(dict(seed=int(seed_text), time_sec=time))
                continue
            speed = {c: math.fsum(z[1] for z in a)/len(a) for c, a in groups.items()}
            density = {c: len(a)/(net.freeway_segment_params['FW_E'][c]['segment_length_km']
                                  *net.freeway_segment_lanes['FW_E'][c]) for c, a in groups.items()}
            vsl = mn.segment_vsl(control, 'FW_E', 18, cfg)
            ctx = copy.deepcopy(adapter._FW_SEG_CTX)
            assert ctx['armed'] and ctx['phi'] == 3.0 and abs(ctx['dlam']-1.) < 1e-8
            p = ctx['p']
            desired = mn.effective_desired_speed_kmh(density[18], net.v_free, net.rho_crit,
                vsl, net.alpha_vsl, False, net.metanet_a_m, False, net.rho_max, 0.)
            nu0 = mn.select_anticipation_nu(density[18], net, vsl)
            tau, nu = state_response_coefficients(ctx['state_response'], speed[18], desired,
                density[18], density[19], ctx['response_rho_crit'], p['metanet_tau_h'], nu0)
            length = p['segment_length_km']
            relaxation = (desired-speed[18])/(tau*3600)
            convection = speed[18]*(speed[17]-speed[18])/(length*3600)
            anticipation = -nu*(density[19]-density[18])/(tau*length*3600*(density[18]+p['metanet_kappa_veh_km_lane']))
            base = relaxation+convection+anticipation
            unit = ctx['dlam']*density[18]*speed[18]**2/(3600*length*ctx['lanes']*p['rho_crit'])
            checked = mn.metanet_speed_update_kmh(speed[18], speed[17], density[18], density[19],
                desired, 1/3600, length, p['metanet_tau_h'], nu0, p['metanet_kappa_veh_km_lane'], net.v_min)
            expected = max(net.v_min, max(net.v_min, speed[18]+base)-3*unit)
            assert abs(checked-expected) < 1e-8
            observed = (math.fsum(z[1] for z in future)/len(future)-speed[18])/5
            rows.append(dict(seed=int(seed_text), time_sec=time, base_rate=base,
                unit_lane_drop=unit, observed_rate=observed, speed=speed[18], density=density[18],
                relaxation=relaxation, convection=convection, anticipation=anticipation,
                baseline_one_second_clipped=abs(checked-(speed[18]+base-3*unit)) > 1e-8))
    train = [r for r in rows if r['seed'] == 29]
    denominator = math.fsum(r['unit_lane_drop']**2 for r in train)
    assert denominator > 0
    raw = math.fsum(r['unit_lane_drop']*(r['base_rate']-r['observed_rate']) for r in train)/denominator
    fitted = min(6., max(0., raw))
    groups = []
    for seed in (29, 43, 67):
        selected = [r for r in rows if r['seed'] == seed]
        for label, subset in [('all', selected),
                ('accelerating', [r for r in selected if r['observed_rate'] > .2]),
                ('decelerating', [r for r in selected if r['observed_rate'] < -.2])]:
            assert subset, (seed, label)
            result = dict(seed=seed, phase=label, samples=len(subset))
            for name, phi in [('baseline', 3.), ('fitted', fitted)]:
                errors = [r['base_rate']-phi*r['unit_lane_drop']-r['observed_rate'] for r in subset]
                result[name] = dict(rmse_kmh_per_sec=math.sqrt(math.fsum(e*e for e in errors)/len(errors)),
                    bias_kmh_per_sec=math.fsum(errors)/len(errors))
            groups.append(result)
    passed = True
    for g in groups:
        if g['seed'] == 29:
            continue
        b, c = g['baseline'], g['fitted']
        passed &= c['rmse_kmh_per_sec'] <= (.9 if g['phase']=='all' else 1.1)*b['rmse_kmh_per_sec']
        if g['phase'] == 'all':
            passed &= abs(c['bias_kmh_per_sec']) <= abs(b['bias_kmh_per_sec'])
    for path, digest in protocol['protected_sha256'].items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest() == digest, path
    stop = protocol['STOP']
    assert hashlib.sha256(Path(stop['path']).read_bytes()).hexdigest() == stop['sha256']
    old = {n.name: hashlib.sha256(ast.dump(n, include_attributes=False).encode()).hexdigest()
           for n in ast.parse(Path(__file__).read_bytes()).body if isinstance(n, ast.FunctionDef)}
    assert all(old[k] == v for k, v in protocol['helper_ast_sha256'].items())
    for path, digest in list(pins.items()):
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest, path
    save(dest/'rows.json', rows)
    save(dest/'assessment.json', dict(fitted_phi=fitted, unconstrained_phi=raw, groups=groups,
        screen_passed=bool(passed), excluded=excluded,
        baseline_clipped_count=sum(r['baseline_one_second_clipped'] for r in rows),
        interpretation='Conditional coefficient screen only; population changes and finite5s labels are not isolated vehicle forces.'))
    save(dest/'completion.json', dict(status='COMPLETE_SCREEN_NOT_GAIN_QUALIFIED',
        previous_goal_turn='PROGRESS', this_goal_turn='PROGRESS', fit_count=1, forecast=0, native=0, fzp=0,
        fitted_phi=fitted, screen_passed=bool(passed), production_adopted=False, push=False,
        samples=len(rows), old_helper_functions_preserved=len(protocol['helper_ast_sha256']),
        protected9_and_STOP_unchanged=True, source_sha256=pins.copy()))
    print(json.dumps(dict(phi=fitted, unconstrained_phi=raw, screen_passed=bool(passed), groups=groups), indent=2))


if __name__ == '__main__':
    import sys
    if sys.argv[1:] == ['--lane-drop105']:
        assess_lane_drop105()
    elif sys.argv[1:] == ['--discharge104']:
        assess_discharge104()
    elif sys.argv[1:]==['--finish-ramp-timing103']:
        finish_ramp_timing103()
    elif len(sys.argv)==3 and sys.argv[1]=='--assess-ramp-timing103':
        assert sys.argv[2] in ('67','73')
        assess_ramp_timing103(int(sys.argv[2]))
    elif sys.argv[1:] == ['--prepare-ramp-timing103']:
        prepare_ramp_timing103()
    elif sys.argv[1:] == ['--recovery-band102']:
        assess_recovery_band102()
    elif sys.argv[1:] == ['--response-horizon98']:
        assess_response_horizon98()
    elif sys.argv[1:] == ['--state-residual93']:
        assess_state_residual93()
    elif sys.argv[1:] == ['--local-transport91']:
        assess_local_transport91()
    elif sys.argv[1:] == ['--boundary-time88']:
        assess_boundary_time88()
    elif sys.argv[1:] == ['--boundary-cohorts88']:
        boundary_cohorts88()
    elif sys.argv[1:] == ['--cohort-departure89']:
        assess_cohort_departure89()
    elif sys.argv[1:] == ['--native-choices89']:
        native_pair_choices89()
    else:
        assert not sys.argv[1:]
        main()
