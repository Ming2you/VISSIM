"""Read completed-run caches/snapshots only; no FZP, COM, model, or live-run access."""
import bisect
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
OUT = HERE / 'loss_diagnosis'
RUNS = {
    'nc': Path('D:/VISSIM_runs/20260927_sd31_wiring9000/nc'),
    'sdmpc': Path('D:/VISSIM_runs/20260930_expanded036_s29_9000_r2/sdmpc'),
}
RID = {'nc': 'sdmpc31_nc9000_s29', 'sdmpc': 'sdmpc31_sdmpc9000_s29'}
PINS = {}

def read(path):
    data = path.read_bytes()
    PINS[str(path)] = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
    return data.decode('utf-8-sig')

def js(path):
    return json.loads(read(path))

def write_json(name, data):
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')

def write_csv(name, rows):
    with (OUT / name).open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

def main():
    OUT.mkdir(exist_ok=True)
    geometry = js(BASE / 'selected/port_gain/geometry.json')
    membership = js(BASE / 'selected/scenario/control_area_membership_213a5d.json')
    inside = {str(x) for x in membership['inside_links']}
    addresses = geometry['addresses']
    cells = {road: sorted([x for x in geometry['cells'] if x['road'] == road], key=lambda c: c['cell']) for road in ('FW_E', 'FW_W')}
    ends = {road: [c['end_m'] for c in cc] for road, cc in cells.items()}
    def group(link):
        return addresses[link][0] if link in addresses else 'other_Omega'
    metrics = {a: js(HERE / f'analysis/{a}/area_metrics.json') for a in RUNS}
    series = {a: list(csv.DictReader(read(HERE / f'analysis/{a}/area_timeseries.csv').splitlines())) for a in RUNS}
    assert len(series['nc']) == len(series['sdmpc'])
    delta = []
    for nc, sd in zip(series['nc'], series['sdmpc']):
        assert nc['sim_sec'] == sd['sim_sec']
        delta.append({'sim_sec': float(nc['sim_sec']), 'delta_TTT_veh_h': float(sd['ttt_veh_h_cumulative']) - float(nc['ttt_veh_h_cumulative']),
                      'delta_stock_veh': int(sd['inside_vehicles']) - int(nc['inside_vehicles']),
                      'delta_exit_events': int(sd['ttd_observed_plus_terminal_cumulative']) - int(nc['ttd_observed_plus_terminal_cumulative'])})
    write_csv('omega_delta_5s.csv', delta)
    best = min(delta, key=lambda x: x['delta_TTT_veh_h'])
    crossing = next(r for r in delta if r['sim_sec'] > best['sim_sec'] and r['delta_TTT_veh_h'] > 0)
    periods = []
    for a, b in zip([0, 900, 1500, 2250, 3300, 4500, 6000, 7500], [900, 1500, 2250, 3300, 4500, 6000, 7500, 9000]):
        l = min(delta, key=lambda r: abs(r['sim_sec'] - a)) if a else {'sim_sec': 0, 'delta_TTT_veh_h': 0}
        r = min(delta, key=lambda r: abs(r['sim_sec'] - b))
        periods.append({'start_s': l['sim_sec'], 'end_s': r['sim_sec'], 'delta_TTT_veh_h': r['delta_TTT_veh_h'] - l['delta_TTT_veh_h']})
    write_csv('period_contributions.csv', periods)
    link_rows = []
    totals = defaultdict(lambda: {'nc': 0, 'sdmpc': 0})
    for link in sorted(inside, key=int):
        row = {'link': link, 'group': group(link)}
        for a in RUNS:
            data = metrics[a]['physical_link_residence'].get(link, {'ttt_veh_h': 0, 'slow_veh_h': 0})
            row[a + '_TTT_veh_h'] = data['ttt_veh_h']
            row[a + '_slow_veh_h'] = data['slow_veh_h']
            totals[row['group']][a] += data['ttt_veh_h']
        row['delta_TTT_veh_h'] = row['sdmpc_TTT_veh_h'] - row['nc_TTT_veh_h']
        row['delta_slow_veh_h'] = row['sdmpc_slow_veh_h'] - row['nc_slow_veh_h']
        link_rows.append(row)
    link_rows.sort(key=lambda r: r['delta_TTT_veh_h'], reverse=True)
    for vals in totals.values():
        vals['delta_TTT_veh_h'] = vals['sdmpc'] - vals['nc']
    assert abs(sum(x['delta_TTT_veh_h'] for x in link_rows) - delta[-1]['delta_TTT_veh_h']) < 1e-7
    write_csv('link_contributions_exact5s.csv', link_rows)
    detectors = list(csv.DictReader(read(BASE / 'selected/obs150/obs150_detectors_v2.csv').splitlines()))
    detector_rows, stocks, cell_rows, lane_rows, commands, sources = [], [], [], [], [], []
    urban_lane_rows, ramp_posthead, predictions = [], [], []
    heads = {r['link']: float(r['pos']) for r in detectors if r['role'] == 'meter_head'}
    capture_checks = []
    for a, run in RUNS.items():
        dec = run / ('decisions_' + RID[a])
        for path in sorted(dec.glob('state_*.json')):
            d = js(path)
            t = float(d['sim_sec'])
            rec = d['vehicle_records']
            assert rec['complete'] and rec['record_count'] == len(rec['records']) and rec['unobservable_count'] == 0
            assert rec['capture_sim_sec_before'] == rec['capture_sim_sec_after'] == t
            capture_checks.append({'arm': a, 'time_s': t, 'complete': True, 'record_count': rec['record_count']})
            links, bins, lanes = defaultdict(list), defaultdict(list), defaultdict(list)
            fw_count = 0
            for v in rec['records']:
                link = str(v['link_no'])
                links[link].append(v['speed_kph'])
                if link in addresses:
                    road, offset = addresses[link]
                    pos = offset + v['position_m']
                    assert -1e-3 <= pos <= ends[road][-1] + 1e-3, (a, t, link, pos)
                    c = min(bisect.bisect_right(ends[road], pos), len(ends[road])-1)
                    bins[road, c].append(v['speed_kph'])
                    lanes[road, c, v['lane_no']].append(v['speed_kph'])
                    fw_count += 1
            assert sum(len(v) for v in bins.values()) == fw_count
            for link in ('40', '127'):
                for lane in range(1, 5):
                    vv = [v for v in rec['records'] if str(v['link_no']) == link and v['lane_no'] == lane]
                    slow = [v for v in vv if v['speed_kph'] < 5]
                    urban_lane_rows.append({'arm': a, 'sim_sec': t, 'link': link, 'lane': lane, 'n': len(vv),
                        'slow_lt5': len(slow), 'lowest_slow_position_m': min((v['position_m'] for v in slow), default=None)})
            for link, pos in heads.items():
                nn = sum(str(v['link_no']) == link and v['position_m'] >= pos for v in rec['records'])
                ramp_posthead.append({'arm': a, 'sim_sec': t, 'connector': link, 'head_position_m': pos, 'posthead_n': nn})
            for link in inside | set(links):
                vv = links.get(link, [])
                stocks.append({'arm': a, 'sim_sec': t, 'link': link, 'group': group(link) if link in inside else 'outside_Omega',
                               'n': len(vv), 'slow_lt5': sum(x < 5 for x in vv), 'stopped_lt1': sum(x < 1 for x in vv), 'speed_kph': sum(vv)/len(vv) if vv else None})
            for road, cc in cells.items():
                for c in cc:
                    vv = bins.get((road, c['cell']), [])
                    cell_rows.append({'arm': a, 'sim_sec': t, 'road': road, 'cell': c['cell'], 'start_m': c['start_m'], 'end_m': c['end_m'],
                                      'n': len(vv), 'slow_lt5': sum(x < 5 for x in vv), 'speed_kph': sum(vv)/len(vv) if vv else None})
            for (road, c, lane), vv in lanes.items():
                lane_rows.append({'arm': a, 'sim_sec': t, 'road': road, 'cell': c, 'lane': lane, 'n': len(vv), 'slow_lt5': sum(x < 5 for x in vv), 'speed_kph': sum(vv)/len(vv)})
            obs = d['obs150']
            for det in detectors if obs.get('window') else []:
                no = det['dcm_no']
                detector_rows.append({'arm': a, 'sim_sec': t, 'window_start_s': obs['window']['start_s'], 'window_end_s': obs['window']['end_s'],
                                      'dcm_no': no, 'role': det['role'], 'ref': det['ref'], 'link': det['link'], 'lane': det['lane'],
                                      'count': obs['detectors'].get(no), 'cum_count': obs['detectors_cum'].get(no)})
            for road, n in (obs.get('source_cumulative_vehs') or {}).items():
                sources.append({'arm': a, 'sim_sec': t, 'road': road, 'admitted_cumulative_vehicles': n})
            action = dec / ('action_' + path.stem.split('_')[1] + '.csv')
            if t == 9000 and not action.exists():
                continue  # Terminal snapshot has no following control interval.
            for r in csv.DictReader(read(action).splitlines()):
                if r['kind'] in ('signal', 'signal_sg', 'ramp_meter', 'vsl'):
                    commands.append({'arm': a, 'sim_sec': t, **r})
            if a == 'sdmpc' and 900 <= t < 9000:
                pred = js(action.with_suffix('.json'))['prediction']
                if pred.get('status') == 'ok':
                    for road, nn in pred['state_summary']['freeway_segment_vehicles'].items():
                        for cell, n in enumerate(nn):
                            predictions.append({'from_sec': t, 'target_sec': pred['target_sim_sec'], 'road': road, 'cell': cell, 'predicted_n': n})
    write_csv('link_snapshots_150s.csv', stocks)
    write_csv('physical_cell_snapshots_150s.csv', cell_rows)
    write_csv('physical_cell_lane_snapshots_150s.csv', lane_rows)
    write_csv('detector_windows_150s.csv', detector_rows)
    write_csv('source_admissions.csv', sources)
    write_csv('command_timeline.csv', commands)
    write_csv('urban_lanes_150s.csv', urban_lane_rows)
    write_csv('ramp_posthead_stock.csv', ramp_posthead)
    actual_lookup = {(r['sim_sec'], r['road'], r['cell']): r for r in cell_rows if r['arm'] == 'sdmpc'}
    for r in predictions:
        actual = actual_lookup[r['target_sec'], r['road'], r['cell']]
        r['actual_n'] = actual['n']
        r['error_pred_minus_actual_n'] = r['predicted_n'] - actual['n']
    write_csv('saved_one_step_count_errors.csv', predictions)
    # Native LDP, not command CSV, supplies realized green seconds in completed windows.
    ldp_rows = []
    for a, run in RUNS.items():
        for sc in (1001, 1002, 1003, 1004, 1005, 11, 6, 108):
            path = run / 'vissim_eval' / (RID[a] + f'_{sc}_001.ldp')
            counts = defaultdict(lambda: defaultdict(int))
            n = 0
            for line in read(path).splitlines():
                try:
                    t = float(line[:7])
                    float(line[7:12])
                except ValueError:
                    continue
                chars = line[12:]
                assert len(chars) == 8 and set(chars) <= {'.', 'I', '/', 'i', '\\'}, repr(line)
                end = int((t - 1) // 150 + 1) * 150
                for sg, char in enumerate(chars, 1):
                    counts[end][sg, char] += 1
                n += 1
            assert n == 9000, (a, sc, n)
            for end, cc in sorted(counts.items()):
                for sg in range(1, 9):
                    ldp_rows.append({'arm': a, 'sc': sc, 'sg': sg, 'start_s': end - 150, 'end_s': end,
                                     'green_s': cc[sg, 'I'], 'amber_s': cc[sg, '/'], 'red_s': cc[sg, '.']})
    write_csv('native_green_windows_150s.csv', ldp_rows)
    native_root = ET.fromstring(read(BASE / 'selected/network/native_seed29.inpx'))
    dsd_locations = []
    for x in native_root.findall('./desSpeedDecisions/desSpeedDecision'):
        if x.get('no') in [str(i) for i in range(63, 70)]:
            link, lane = x.get('lane').split()
            dsd_locations.append({'dsd': int(x.get('no')), 'link': link, 'lane': lane, 'position_m': float(x.get('pos')),
                                  'chain_m': addresses[link][1] + float(x.get('pos'))})
    decisions = js(HERE / 'analysis/sdmpc_decisions.json')['decisions']
    validation = {'paired_5s_times_exact': True, 'snapshot_count': len(capture_checks), 'all_snapshots_complete': True,
                  'mainline_vehicle_mapping_conservative': True, 'physical_link_TTT_sum_residual_veh_h': sum(x['delta_TTT_veh_h'] for x in link_rows)-delta[-1]['delta_TTT_veh_h'],
                  'no_new_FZP_scan': True, 'no_model_or_live_run_access': True}
    result = {'scope': 'Completed seed29 expanded036 9000 vs completed matched NC. SDMPC minus NC. Accounting attribution, not lever-isolated causality.',
              'best_cumulative_TTT_gain': best, 'first_positive_cumulative_TTT_after_best': crossing, 'end': delta[-1],
              'periods': periods, 'group_exact_TTT': dict(totals), 'top_losses': link_rows[:12], 'top_gains': link_rows[-12:],
              'physical_boundaries_E': [b for b in geometry['boundaries'] if b['road']=='FW_E'], 'dsd_locations': dsd_locations,
              'slow_definition': 'speed <5 km/h; separate snapshot stopped<1 km/h',
              'snapshots_note': '150s instantaneous actual vehicle snapshots. Do not interpret interpolated residence as the 5s integrated TTT.',
              'vsl_restricted': [{'sim_sec': d['sim_sec'], 'commands': d['restricted_vsl']} for d in decisions if d['restricted_vsl']],
              'RM_restricted_steps': sum(bool(d['restricted_meters']) for d in decisions),
              'sdmpc_converged_steps': sum(d['sdmpc_converged'] for d in decisions), 'validation': validation}
    write_json('summary.json', result)
    write_json('source_pins.json', PINS)
    print(json.dumps({k: result[k] for k in ['best_cumulative_TTT_gain','first_positive_cumulative_TTT_after_best','group_exact_TTT','validation']}, ensure_ascii=False, indent=2))

def early_onset():
    """Close the physical boundary ledger before/after the first VSL change."""
    out = OUT / 'early_onset'
    out.mkdir(exist_ok=False)
    old_pins = js(OUT / 'source_pins.json')
    geometry = js(BASE / 'selected/port_gain/geometry.json')
    addresses = geometry['addresses']
    east_links = {k for k, v in addresses.items() if v[0] == 'FW_E'}
    def table(name):
        return list(csv.DictReader(read(OUT / name).splitlines()))
    detectors = table('detector_windows_150s.csv')
    cells = table('physical_cell_snapshots_150s.csv')
    posthead = table('ramp_posthead_stock.csv')
    commands = table('command_timeline.csv')
    prediction = table('saved_one_step_count_errors.csv')
    pos = list(csv.DictReader(read(BASE / 'selected/obs150/obs150_detectors_v2.csv').splitlines()))
    ramps = ('10484', '10490', '10639', '10681')
    exits = ('10643', '10682', '10481', '10483')
    cp = {(x['arm'], int(float(x['sim_sec'])), int(x['cell'])): x for x in cells if x['road'] == 'FW_E'}
    ph = {(x['arm'], int(float(x['sim_sec'])), x['connector']): int(x['posthead_n']) for x in posthead}
    locations = {}
    for role, ref in [('source', 'FW_E'), ('chain_end', 'FW_E')]+[('off_entry', e) for e in exits]:
        points = {(x['link'], float(x['pos'])) for x in pos if x['role'] == role and x['ref'] == ref}
        assert len(points) == 1, (role, ref, points)
        locations[role, ref] = points.pop()
    def subset(vs, role, ref, before):
        link, position = locations[role, ref]
        return sum(str(v['link_no']) == link and ((v['position_m'] < position) == before) for v in vs)
    states = {}
    for arm, root in RUNS.items():
        for sec in range(900, 2251, 150):
            path = root / ('decisions_'+RID[arm]) / f'state_{sec:06d}.json'
            raw = js(path)
            assert PINS[str(path)]['sha256'] == old_pins[str(path)]['sha256']
            rec = raw['vehicle_records']
            assert rec['complete'] and rec['unobservable_count'] == 0
            assert rec['capture_sim_sec_before'] == rec['capture_sim_sec_after'] == sec
            vs = rec['records']
            n = sum(str(v['link_no']) in east_links for v in vs)
            assert n == sum(int(cp[arm, sec, j]['n']) for j in range(31))
            states[arm, sec] = dict(n=n, source_buffer=subset(vs, 'source', 'FW_E', True),
                end_buffer=subset(vs, 'chain_end', 'FW_E', False),
                pre_off={e: subset(vs, 'off_entry', e, True) for e in exits})
    flows, deltas = [], []
    for sec in range(1050, 2251, 150):
        pair = {}
        for arm in RUNS:
            ds = [x for x in detectors if x['arm'] == arm and float(x['sim_sec']) == sec]
            def count(role, ref=None, link=None):
                rows = [x for x in ds if x['role'] == role and (ref is None or x['ref'] == ref)
                        and (link is None or x['link'] == link)]
                assert rows, (role, ref, link)
                return sum(int(x['count']) for x in rows)
            start, end = states[arm, sec-150], states[arm, sec]
            merges = {r: count('meter_head', link=r)+ph[arm, sec-150, r]-ph[arm, sec, r] for r in ramps}
            off = {e: count('off_entry', e)+end['pre_off'][e]-start['pre_off'][e] for e in exits}
            source = count('source', 'FW_E')+end['source_buffer']-start['source_buffer']
            terminal = count('chain_end', 'FW_E')-end['end_buffer']+start['end_buffer']
            expected = source+sum(merges.values())-sum(off.values())-terminal
            row = dict(arm=arm, start_s=sec-150, end_s=sec, start_n=start['n'], end_n=end['n'],
                source_detector=count('source', 'FW_E'), source_buffer_change=end['source_buffer']-start['source_buffer'],
                admitted=source, terminal=terminal, merges=merges, off_entries=off,
                through10481=count('through', '10481'), conservation_residual=end['n']-start['n']-expected)
            pair[arm] = row
            flows.append(row)
        nc, sd = pair['nc'], pair['sdmpc']
        delta = {k: sd[k]-nc[k] for k in ('start_n','end_n','admitted','source_detector','source_buffer_change','terminal','through10481')}
        delta.update(start_s=sec-150, end_s=sec, merges={r: sd['merges'][r]-nc['merges'][r] for r in ramps},
            off_entries={e: sd['off_entries'][e]-nc['off_entries'][e] for e in exits})
        delta['net_boundary_change'] = delta['admitted']+sum(delta['merges'].values())-sum(delta['off_entries'].values())-delta['terminal']
        delta['conservation_residual'] = delta['end_n']-delta['start_n']-delta['net_boundary_change']
        deltas.append(delta)
    before = [x for x in commands if x['kind'] == 'vsl' and float(x['sim_sec']) < 1650]
    assert before and all(float(x['speed_kph']) == 110 for x in before)
    rm = [x for x in commands if x['kind'] == 'ramp_meter' and float(x['sim_sec']) <= 2100]
    assert rm and all(float(x['green_sec']) == 10 for x in rm)
    changing = [x for x in commands if x['arm'] == 'sdmpc' and x['kind'] == 'vsl' and float(x['speed_kph']) < 110]
    assert min(float(x['sim_sec']) for x in changing) == 1650
    cell_changes = []
    for sec in range(900, 2251, 150):
        for j in range(31):
            nc, sd = cp['nc', sec, j], cp['sdmpc', sec, j]
            cell_changes.append(dict(sec=sec, cell=j, delta_n=int(sd['n'])-int(nc['n']),
                nc_speed=float(nc['speed_kph']) if nc['speed_kph'] else None,
                sdmpc_speed=float(sd['speed_kph']) if sd['speed_kph'] else None))
    errors = [x for x in prediction if x['road'] == 'FW_E' and 1350 <= float(x['from_sec']) <= 2100]
    payload = dict(scope='Saved native states/detectors: boundary accounting, not lever causal effect or autonomous model validation.',
        flows=flows, deltas=deltas, cells=cell_changes, saved_prediction_errors=errors,
        no_restriction_before_1650=True, meter_open=True, physical_locations={str(k): v for k,v in locations.items()},
        passed=all(x['conservation_residual'] == 0 for x in flows+deltas), source_pins=PINS,
        new_native=0, new_forecasts=0, new_fzp=0)
    (out/'summary.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    assert payload['passed'], [(x.get('arm'),x['end_s'],x['conservation_residual']) for x in flows if x['conservation_residual']]
    for path, pin in PINS.items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == pin['sha256']
    (out/'source_executed.py.txt').write_bytes(Path(__file__).read_bytes())
    print(json.dumps(dict(passed=True,windows=len(flows),deltas=deltas),ensure_ascii=False))


def early_bottleneck_balance():
    """Separate branch drainage, mainline delivery and merges in completed data."""
    import ast
    import statistics

    out = OUT / 'early_bottleneck_balance'
    out.mkdir(exist_ok=False)
    source = Path(__file__).read_text(encoding='utf-8')
    (out/'source_executed.py.txt').write_text(source, encoding='utf-8')
    old = js(OUT/'source_pins.json')
    ledger = js(OUT/'early_onset/summary.json')
    geo = js(BASE/'selected/port_gain/geometry.json')
    evidence = js(OUT/'mechanism_evidence.json')
    pos = list(csv.DictReader(read(BASE/'selected/obs150/obs150_detectors_v2.csv').splitlines()))
    ds = list(csv.DictReader(read(OUT/'detector_windows_150s.csv').splitlines()))
    def point(role, ref):
        values = {(r['link'], float(r['pos'])) for r in pos if r['role']==role and r['ref']==ref}
        assert len(values)==1, (role, ref, values)
        return values.pop()
    def coordinate(link, x):
        a=geo['addresses'].get(str(link))
        return a[1]+x if a and a[0]=='FW_E' else None
    cut_a = coordinate(*point('through','10481'))
    cut_b = coordinate(*point('through','10483'))
    cell21 = next(c for c in geo['cells'] if c['road']=='FW_E' and c['cell']==21)
    assert abs(cut_b-cell21['start_m'])<1e-6
    off_ids = ('10643','10682','10481','10483')
    assert all(evidence['removals_by_link'][a].get(k,0)==0 for a in RUNS for k in off_ids)
    states={}
    for arm, root in RUNS.items():
        for sec in range(900,2251,150):
            path=root/('decisions_'+RID[arm])/f'state_{sec:06d}.json'
            raw=js(path)
            assert PINS[str(path)]['sha256']==old[str(path)]['sha256']
            rec=raw['vehicle_records']
            assert rec['complete'] and rec['unobservable_count']==0
            assert rec['capture_sim_sec_before']==rec['capture_sim_sec_after']==sec
            vs=rec['records']; grouped={k:[v for v in vs if str(v['link_no'])==k] for k in off_ids}
            ports={k:dict(n=len(z),slow10=sum(v['speed_kph']<10 for v in z),
                mean_speed=statistics.mean(v['speed_kph'] for v in z) if z else None,
                first_vehicle_m=min(v['position_m'] for v in z) if z else None) for k,z in grouped.items()}
            positions=[coordinate(v['link_no'],v['position_m']) for v in vs]
            pre_link,pre_pos=point('off_entry','10483')
            pre=sum(str(v['link_no'])==pre_link and v['position_m']<pre_pos for v in vs)
            states[arm,sec]=dict(ports=ports,
                between_cuts_including_off_pre_detector=sum(x is not None and cut_a<=x<cut_b for x in positions)+pre,
                downstream21_30=sum(x is not None and x>=cut_b for x in positions))
    def count(arm, sec, role, ref):
        rows=[r for r in ds if r['arm']==arm and float(r['sim_sec'])==sec and r['role']==role and r['ref']==ref]
        assert rows
        return sum(int(r['count']) for r in rows)
    ports=[];slabs=[]
    for f in ledger['flows']:
        arm,stop=f['arm'],f['end_s'];start=stop-150
        s,t=states[arm,start],states[arm,stop]
        for k in off_ids:
            ports.append(dict(arm=arm,start_s=start,end_s=stop,offramp=k,
                start=s['ports'][k],end=t['ports'][k],entry=f['off_entries'][k],
                drain_by_conservation=s['ports'][k]['n']+f['off_entries'][k]-t['ports'][k]['n']))
        q_a=count(arm,stop,'through','10481');q_b=count(arm,stop,'through','10483')
        for name,arrive,depart in (
            ('between_cuts_including_off_pre_detector',q_a,q_b+count(arm,stop,'off_entry','10483')),
            ('downstream21_30',q_b+f['merges']['10490']+f['merges']['10484'],f['terminal'])):
            residual=t[name]-s[name]-arrive+depart
            assert residual==0,(arm,start,name,residual)
            slabs.append(dict(arm=arm,start_s=start,end_s=stop,region=name,start_n=s[name],end_n=t[name],
                upstream_through=q_a if name.startswith('between') else q_b,
                ramp_merge=0 if name.startswith('between') else f['merges']['10490']+f['merges']['10484'],
                total_in=arrive,total_out=depart,conservation_residual=residual))
    forecast=js(BASE/'closedloop_recorded1500_lever450_RM_C10484_trace10484_early1500/summary.json')['results']['held_actual']['first_interval']
    initial,final=forecast['physical_cell_states'][:2]
    n0,n1=[sum(x['vehicle_count']['FW_E'][21:]) for x in (initial,final)]
    terminal=sum(t['vehicles'] for t in forecast['transfers'] if t['source']=='freeway:FW_E' and t['target']=='external:terminal:FW_E')
    merge=sum(forecast['ramps'][k]['merge'] for k in ('RM_C10484','RM_C10490'))
    actual=next(x for x in slabs if x['arm']=='sdmpc' and x['end_s']==1650 and x['region']=='downstream21_30')
    assert n0==actual['start_n']
    model=dict(initial_n=n0,final_n=n1,terminal=terminal,merge=merge,
        upstream_through_reconstructed=n1-n0+terminal-merge)
    errors=dict(upstream=model['upstream_through_reconstructed']-actual['upstream_through'],
        merges=merge-actual['ramp_merge'],terminal=terminal-actual['total_out'],end_stock=n1-actual['end_n'])
    assert abs(errors['upstream']+errors['merges']-errors['terminal']-errors['end_stock'])<1e-8
    old_tree=ast.parse(read(OUT/'early_onset/source_executed.py.txt'))
    now={n.name:ast.dump(n,include_attributes=False) for n in ast.parse(source).body if isinstance(n,ast.FunctionDef)}
    prior={n.name:ast.dump(n,include_attributes=False) for n in old_tree.body if isinstance(n,ast.FunctionDef)}
    assert all(now[k]==v for k,v in prior.items())
    result=dict(status='complete',ports=ports,slabs=slabs,model_first150=model,actual_first150=actual,
        model_flow_error_cancellation=errors,model_offramps_first150=forecast['offramps'],
        source_pins=PINS,old_functions_unchanged=len(prior),cut_positions_m=[cut_a,cut_b],
        limitations=['Retrospective accounting, not causal attribution or native capacity identification.',
            '150s snapshots cannot exclude transient spillback between samples.',
            'Model upstream flux inferred from its conserved inventory; not a new independent flow observation.'],
        new_forecasts=0,new_native=0,new_fzp_reads=0,live_poll=0,adopted=False)
    for name,pin in PINS.items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==pin['sha256']
    (out/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps(dict(slabs=len(slabs),ports=len(ports),model_error=errors,old_functions_unchanged=len(prior)),ensure_ascii=False))


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--early-onset', action='store_true')
    parser.add_argument('--early-bottleneck-balance', action='store_true')
    args = parser.parse_args()
    if args.early_bottleneck_balance:
        early_bottleneck_balance()
    else:
        early_onset() if args.early_onset else main()
