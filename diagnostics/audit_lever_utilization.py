"""Read-only actual n7 actuator authority/utilization inventory."""
from collections import Counter, defaultdict
import csv
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT/'evaluation/runs/codex_n7_pure_s13_20260910'
DEC = RUN/'decisions_codex_n7_pure_s13_20260910'
START, END, PERIOD = 900, 5400, 150


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def rows(path):
    with path.open(encoding='utf-8-sig', newline='') as handle:
        return list(csv.DictReader(handle))


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def intervals(times):
    result = []
    for sec in sorted(times):
        if sec >= END:
            continue
        if result and result[-1][1] == sec:
            result[-1][1] = min(sec+PERIOD, END)
        else:
            result.append([sec, min(sec+PERIOD, END)])
    return result


def main():
    mapping_path = ROOT/'evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json'
    mapping = read(mapping_path)
    network_path=ROOT/'network/real_world_gaepo_modi/modi_eval_userfix Ver2.inpx'
    xml=ET.parse(network_path).getroot()
    signal_heads=list(xml.find('signalHeads'))
    sources = [mapping_path,network_path]
    paths = [DEC/f'action_{time:06}.json' for time in range(START, END+1, PERIOD)]
    actions = {int(path.stem.split('_')[-1]): read(path) for path in paths}
    commands = {}
    for time, path in zip(actions, paths):
        commands[time] = rows(path.with_suffix('.csv'))
        sources.extend([path, path.with_suffix('.csv')])
    applied_path = RUN/f'action_{RUN.name}.csv'
    applied = [r for r in rows(applied_path) if START <= float(r['sim_sec']) <= END]
    sources.append(applied_path)
    actual_audit_path = RUN/'analysis/actuation_audit.json'
    actual = read(actual_audit_path)
    sources.append(actual_audit_path)
    all_times = list(actions)
    active_times = [t for t in actions if t < END]
    by_type = {t: {kind: [r for r in commands[t] if r['kind'] == kind]
                   for kind in ('vsl', 'ramp', 'signal', 'signal_sg')} for t in actions}
    # Physical ramp rows use ramp_meter, unlike the four modeled ramp keys.
    for t in actions:
        by_type[t]['ramp'] = [r for r in commands[t] if r['kind'] == 'ramp_meter']
        assert len(by_type[t]['vsl']) == 66 and len(by_type[t]['signal']) == 17
        assert len(by_type[t]['ramp']) == 8
    summary = {'run': RUN.name, 'decision_times_sec': all_times, 'decisions': len(actions),
               'positive_duration_intervals': len(active_times), 'control_duration_sec': END-START,
               'denominator_note': 't5400 is a recorded decision with zero subsequent controlled duration; time fractions use t900..5250 only.'}
    vsl_sites = {}
    for segment in mapping['segments']:
        if not segment.get('dsds'):
            continue
        site = segment['segment_id']
        site_rows = {t: [r for r in by_type[t]['vsl'] if r['id'] == site] for t in actions}
        speeds = {t: sorted({float(r['speed_kph']) for r in rr}) for t, rr in site_rows.items()}
        assert all(len(value) == 1 for value in speeds.values())
        vsl_sites[site] = {'model_link': segment['model_link'], 'model_cell': segment['model_segment_index'],
            'physical_link': segment['link'], 'lanes': sorted({int(r['lane']) for r in site_rows[START]}),
            'dsd_ids': sorted(int(r['dsd_no']) for r in site_rows[START]),
            'dsd_chain_positions_m': sorted({d.get('chain_pos_m', segment['dsd_chain_pos_m']) for d in segment['dsds']}),
            'speed_decision_times': {str(int(cap)): [t for t, value in speeds.items() if value == [cap]] for cap in (80.,100.,120.)},
            'speed_controlled_seconds': {str(int(cap)): PERIOD*sum(speeds[t] == [cap] for t in active_times) for cap in (80.,100.,120.)}}
    vsl_readbacks = [r for r in applied if r['kind'] == 'vsl']
    vsl_mismatch = [r for r in vsl_readbacks if not r['readback'] or any(abs(float(v)-float(r['speed_kph']))>1e-6 for v in r['readback'].split('|'))]
    vsl = {'sites': vsl_sites, 'physical_dsd_count': sum(len(x['dsd_ids']) for x in vsl_sites.values()),
        'any_80_decisions': [t for t in actions if any(float(r['speed_kph']) == 80 for r in by_type[t]['vsl'])],
        'any_100_decisions': [t for t in actions if any(float(r['speed_kph']) == 100 for r in by_type[t]['vsl'])],
        'immediate_readback_rows_including_final': len(vsl_readbacks), 'immediate_mismatches': len(vsl_mismatch),
        'limitation': 'Desired-speed distribution readback establishes DSD commands at write time, not a hard speed cap on every existing vehicle or persistent vehicle compliance.'}
    meters, model_groups = [], {}
    for meter in mapping['ramp_meters']:
        key = meter['id']
        rr = {t: next(r for r in by_type[t]['ramp'] if r['id'] == key) for t in actions}
        green = {t: float(r['green_sec']) for t, r in rr.items()}
        assert all(abs(float(r['rate_vph']) - green[t]*meter['capacity_vph']/meter['cycle_sec'])<1e-6 for t,r in rr.items())
        signal_actual = next(r for r in actual['physical_ramps'] if r['connector'] == meter['connector'])
        expected_green=sum(PERIOD*green[t]/10 for t in active_times)
        expected_amber=sum(PERIOD/10 for t in active_times if 0<green[t]<10)
        assert abs(signal_actual['aspects_sec'].get('green',0)-expected_green)<1e-6
        assert abs(signal_actual['aspects_sec'].get('amber',0)-expected_amber)<1e-6
        assert abs(signal_actual['aspects_sec'].get('red',0)-(END-START-expected_green-expected_amber))<1e-6
        meter_heads=[n.attrib for n in signal_heads if n.attrib.get('sg')==f"{meter['sc_no']} {meter['sg_no']}"]
        assert meter_heads and all(n['lane'].split()[0]==str(meter['connector']) for n in meter_heads)
        meters.append({**meter, 'controlled_head_lanes': sorted({n['lane'] for n in meter_heads}), 'green_by_decision': green,
            'restricted_decisions': [t for t, g in green.items() if g < 10],
            'closed_decisions': [t for t, g in green.items() if g == 0],
            'restricted_intervals_sec': intervals(t for t,g in green.items() if g<10),
            'fully_closed_intervals_sec': intervals(t for t,g in green.items() if g==0),
            'actual_aspects_sec': signal_actual['aspects_sec'],
            'actual_green_fraction': signal_actual['green_fraction']})
    for group in ('R_D_W','R_F_W','R_D_E','R_F_E'):
        physical = [m for m in meters if m['model_ramp_key'] == group]
        records = []
        for t, action in actions.items():
            d = action['diagnostics']
            records.append({'time_sec': t, 'requested_model_rate': d['rw_meter_requested_'+group],
                'allocator_realized_rate': d['rw_meter_realized_'+group],
                'action_model_rate_after_writeback': action['ramp_metering'][group],
                'physical_command_encoding_rate_sum': sum(float(r['rate_vph']) for r in by_type[t]['ramp'] if r['id'] in {m['id'] for m in physical}),
                'allocator_estimated_branch_demand_sum': sum(d['rw_meter_demand_'+m['id']] for m in physical),
                'allocator_all_open': d['rw_meter_open_'+group],
                'any_physical_green_below_10': any(m['green_by_decision'][t] < 10 for m in physical)})
        model_groups[group] = {'records': records,
            'requested_rate_below_estimated_demand_decisions': [r['time_sec'] for r in records if r['requested_model_rate'] < r['allocator_estimated_branch_demand_sum']-1e-6],
            'any_physical_restriction_decisions': [r['time_sec'] for r in records if r['any_physical_green_below_10']],
            'model_rate_vs_encoding_difference_decisions': [r['time_sec'] for r in records if abs(r['action_model_rate_after_writeback']-r['physical_command_encoding_rate_sum'])>1e-6]}
    meter_result = {'physical': meters, 'model_groups': model_groups,
        'any_physical_restriction_decisions': [t for t in actions if any(m['green_by_decision'][t]<10 for m in meters)],
        'N_UF_star_7200_decisions': [t for t,a in actions.items() if abs(a['N_UF_star']-7200)<1e-6],
        'limitations': ['rate_vph is 900*g/10 encoding, not measured flow. Allocation has branch demand estimates and measured service tables; four model rates need not equal the sum of the eight encoded rates.',
                       'Command clipping alone does not prove binding actual metering; arrivals, receiving capacity, startup losses and queue stock matter.']}
    signals = {t: {r['sc_no']: r for r in by_type[t]['signal']} for t in actions}
    fields = [f'p{i}_green' for i in (1,2,3,4)]
    per_signal, clips = [], []
    phase_transition_changes, signal_transition_changes = 0, 0
    for sc in signals[START]:
        first = signals[START][sc]
        changed_first, changed_previous = [], []
        per_phase = {}
        for phase in fields:
            values = {t: float(signals[t][sc][phase]) for t in actions}
            per_phase[phase] = {'min_written_sec': min(values.values()), 'max_written_sec': max(values.values()),
                'decisions_different_from_first': [t for t,v in values.items() if abs(v-values[START])>1e-6],
                'changes_from_previous_decision': sum(abs(values[b]-values[a])>1e-6 for a,b in zip(all_times,all_times[1:]))}
            phase_transition_changes += per_phase[phase]['changes_from_previous_decision']
        for i,t in enumerate(all_times):
            current = signals[t][sc]
            if any(current[f] != first[f] for f in fields): changed_first.append(t)
            if i and any(current[f] != signals[all_times[i-1]][sc][f] for f in fields): changed_previous.append(t)
            for field in fields:
                raw = actions[t]['green_times'][f'SC{sc}_{field[:2]}']
                written = float(current[field])
                if abs(raw-written)>0.000501:
                    clips.append({'time_sec':t,'sc':int(sc),'phase':field[:2],'action_json_sec':raw,'written_sec':written,'difference_sec':written-raw})
        signal_transition_changes += len(changed_previous)
        per_signal.append({'sc':int(sc),'phases':per_phase,'different_from_first_decisions':changed_first,'changes_from_previous_decisions':changed_previous})
    secs_path = RUN/'analysis/signal_seconds_from_readback.csv'
    nc_secs_path = ROOT/'evaluation/runs/codex_nc_s13_6056c94_20260909_retry/analysis/signal_seconds_from_readback.csv'
    sources.extend([secs_path,nc_secs_path])
    green_seconds = []
    agg = []
    for path in (secs_path,nc_secs_path):
        table=Counter()
        for r in rows(path):
            if r['sc'] in signals[START] and int(r['sg'])<=8:
                table[r['sc'],r['sg']] += float(r.get('green') or 0)
        agg.append(table)
    for key in sorted(agg[0],key=lambda k:tuple(map(int,k))):
        green_seconds.append({'sc':int(key[0]),'sg':int(key[1]),'n7_green_sec':agg[0][key],
            'native_nc_green_sec':agg[1][key],'delta_sec':agg[0][key]-agg[1][key]})
    green = {'signals': sorted(per_signal,key=lambda r:r['sc']),
        'signal_previous_changes': signal_transition_changes,'signal_previous_opportunities':17*(len(actions)-1),
        'phase_previous_changes':phase_transition_changes,'phase_previous_opportunities':68*(len(actions)-1),
        'live_phase_count_at_first':sum(float(r[f])>0 for r in signals[START].values() for f in fields),
        'writer_nonrounding_differences':clips,'actual_green_seconds_vs_native':green_seconds,
        'actual_SGs_changed_vs_native':sum(abs(r['delta_sec'])>1e-6 for r in green_seconds),
        'actual_com_mismatches':actual['com_readback_mismatches']}
    controlled_heads=[n.attrib for n in signal_heads if n.attrib.get('sg','').split()[0] in signals[START] and int(n.attrib['sg'].split()[1])<=8]
    green['physical_signal_heads']=len(controlled_heads)
    green['physical_head_lane_addresses']=sorted({n['lane'] for n in controlled_heads})
    green['positive_duration_previous_signal_changes']=sum(sum(t<END for t in r['changes_from_previous_decisions']) for r in per_signal)
    offsets = []
    for t,a in actions.items():
        d,m=a['diagnostics'],a['metadata']; on=d['wu_faithful_offset_ttt_on']; off=d['wu_faithful_offset_ttt_off']
        offsets.append({'time_sec':t,'nonzero_search_result_signals':d['wu_faithful_offsets_searched_off_zero'],
            'offset_evaluations':d['wu_faithful_offset_evals'],'nonzero_final_action_signals':sum(abs(v)>1e-8 for v in a['offsets'].values()),
            'nonzero_written_signals':sum(abs(float(r['offset']))>1e-8 for r in by_type[t]['signal']),
            'writer_mode':m['offset_writer'],'model_gain_fraction':(off-on)/off if off else None})
    fdpath=ROOT/'outputs/freeway_segment_params_dlit_20260908.json'; sources.append(fdpath)
    fd=read(fdpath)
    critical={direction: [row['v_free']*math.exp(-1/row['metanet_a_m']) for key,row in fd['segments'].items() if key.startswith(direction+'_')] for direction in ('FW_E','FW_W')}
    result={'summary':summary,'VSL':vsl,'meter':meter_result,'green':green,'offset':{'decisions':offsets},
        'single_branch_equilibrium':{direction:{'critical_speed_min':min(vals),'critical_speed_max':max(vals),'cells_critical_speed_below_80':sum(v<80 for v in vals)} for direction,vals in critical.items()},
        'review_only':'Reads completed pure n7 and existing diagnostics only; no COM, production or live signal experiment edits.'}
    fshare_path=ROOT/'diagnostics/f_merge_actual_share.json'
    if fshare_path.exists():
        sources.append(fshare_path)
        result['actual_F_E_merge_cohorts']=read(fshare_path)
        order_path=ROOT/'diagnostics/direct_branch_order_audit.json'; sources.append(order_path)
        order=read(order_path)
        positions={p['connector']:p['physical_chain_pos_m'] for p in order['positions']}
        assert positions['10643']<positions['10639']<positions['10682']<positions['10681']
        chain_offsets=mapping['freeway_model_links']['FW_E']['chain_offsets_m']
        chain_links=mapping['freeway_model_links']['FW_E']['chain_links']
        link2_start=chain_offsets[chain_links.index(2)]
        for connector in ('10639','10681'):
            assert abs(result['actual_F_E_merge_cohorts']['sections_position_m']['after_'+connector]+link2_start-1-positions[connector])<1e-6
        result['F_E_physical_order']=order['positions']
    passages_path=RUN/'analysis/physical_connector_passages.csv'; sources.append(passages_path)
    passages=rows(passages_path)
    result['meter']['observed_sampled_passages_900_5250']={m['connector']:sum(int(float(r['departures_total'])) for r in passages
        if r['connector']==str(m['connector']) and START<=float(r['start_sec']) and float(r['end_sec'])<=5250) for m in meters}
    for name in ('vsl80_result_20260910.md','meter10639_result.md','signal_zero_result.md','signal_actuation_contract_review.md','spatial_lever_comparison.md'):
        sources.append(ROOT/'diagnostics'/name)
    result['sources']={str(p.relative_to(ROOT)):digest(p) for p in sources}
    target=ROOT/'diagnostics/lever_authority_utilization.json'
    target.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps({'summary':summary,'vsl80':vsl['any_80_decisions'],'vsl100':vsl['any_100_decisions'],
        'meter_restricted':meter_result['any_physical_restriction_decisions'],'NUF7200':meter_result['N_UF_star_7200_decisions'],
        'green_changes':[signal_transition_changes,phase_transition_changes],'writer_clips':len(clips),
        'offset_search_total':sum(d['nonzero_search_result_signals'] for d in offsets)},indent=2))


if __name__=='__main__': main()
