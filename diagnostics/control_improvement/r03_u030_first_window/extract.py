"""One completed excerpt; one bounded read, existing area accounting."""
import argparse
import csv
import gzip
import hashlib
import json
import math
from bisect import bisect_right
from collections import Counter, defaultdict
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from diagnostics.probe_e8_lane_receiving import IndexedFzp
from diagnostics.probe_e8_window_passages import frames
from diagnostics.audit_observer_control_pair import native_signal_prefix
from diagnostics.capture_native_runtime_errors import parse_bytes
from diagnostics.summarize_fast_nc import terminal_candidate
from evaluation.controllers.control_area_objective import physical_membership_from_ledger
from evaluation.controllers.network_provenance import snapshot_network_sha256
from scripts.measure_control_area import Frame, Vehicle, measure_frames, terminal_lengths

OUT = Path(__file__).resolve().parent
RUN = ROOT / 'evaluation/runs/codex_selected_fw070_u030_beta0_r03'
START, END = 900, 1050

def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write(name, rows, fieldnames=None):
    with (OUT / name).open('x', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames if fieldnames is not None else list(rows[0]))
        writer.writeheader(); writer.writerows(rows)

def save(name, value):
    with (OUT / name).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)

def command_artifact_names(start):
    return (f'action{start}_urban_written.csv', f'action{start}_vsl_meter_comparison.csv',
            f'native_{start-150}_{start}_observed_sg.csv')

def command_evidence(run, start, sources):
    """Read the start action and its preceding 150s action/recorded LSA interval."""
    prior = start-150
    decisions = run / ('decisions_'+run.name)
    commands, action_json, headers = {}, {}, {}
    for sec in (prior, start):
        path = decisions / f'action_{sec:06d}.csv'
        with path.open(encoding='utf-8-sig', newline='') as stream:
            reader = csv.DictReader(stream)
            commands[sec], headers[sec] = list(reader), reader.fieldnames
        sources[str(path)] = sha(path)
        path = decisions / f'action_{sec:06d}.json'
        action_json[sec] = load(path); sources[str(path)] = sha(path)
    current = commands[start]
    urban_name, comparison_name, native_name = command_artifact_names(start)
    write(urban_name, [r for r in current if r['kind']=='signal'], headers[start])
    changes = []
    for kind, fields in [('vsl',('speed_kph',)),('ramp_meter',('rate_vph','green_sec'))]:
        old = {(r['id'],r['dsd_no'],r['sc_no']):r for r in commands[prior] if r['kind']==kind}
        for row in current:
            if row['kind']!=kind:continue
            previous = old[(row['id'],row['dsd_no'],row['sc_no'])]
            for field in fields:
                changes.append({'kind':kind,'id':row['id'],'dsd_no':row['dsd_no'],'sc_no':row['sc_no'],
                    'field':field,'previous_written':float(previous[field]),'current_written':float(row[field]),
                    'changed':float(previous[field])!=float(row[field])})
    write(comparison_name, changes, ('kind','id','dsd_no','sc_no','field',
                                    'previous_written','current_written','changed'))
    lsa, = (run/'vissim_eval').glob('*.lsa')
    sources[str(lsa)] = sha(lsa)
    native = native_signal_prefix(lsa, start)
    selected_scs = {r['sc_no'] for r in current if r['kind']=='signal'}
    green_key, unknown_key = f'native_green_sec_{prior}_{start}', f'native_unknown_sec_{prior}_{start}'
    native_rows = []
    for key, events in native['groups'].items():
        if key.split(':')[0] not in selected_scs: continue
        points = sorted({float(prior),float(start),*(float(t) for t,_ in events if prior<t<start)})
        event_times = [t for t,_ in events]; durations = Counter()
        for a,b in zip(points,points[1:]):
            i=bisect_right(event_times,a)-1
            durations['UNKNOWN' if i<0 else events[i][1]] += b-a
        native_rows.append({'sc_sg':key,green_key:durations['GREEN'],
            unknown_key:durations['UNKNOWN'],'native_states_sec':json.dumps(dict(durations),sort_keys=True)})
    write(native_name, native_rows, ('sc_sg',green_key,unknown_key,'native_states_sec'))
    return {'command_counts':{str(t):dict(Counter(r['kind'] for r in rows)) for t,rows in commands.items()},
        'vsl_changed_rows':sum(r['kind']=='vsl' and r['changed'] for r in changes),
        'meter_changed_physical_greens':sum(r['field']=='green_sec' and r['changed'] for r in changes),
        f'meter_group_rates_{start}':action_json[start]['ramp_metering'],
        f'NUF_{start}':action_json[start]['N_UF_star'],
        'native_clock_prefix':{k:v for k,v in native.items() if k!='groups'},
        'command_observation_window':{'previous_action_sec':prior,'current_action_sec':start,
            'recorded_lsa_prefix_end_sec':start,'recorded_lsa_duration_window_sec':[prior,start],
            'selected_scs':sorted(selected_scs),'selected_sg_rows':len(native_rows)},
        'native_signal_scope':f'Observed LSA for SCs in the t{start} signal command rows only ({len(selected_scs)} SCs). '
            f'Green durations cover [{prior},{start}); the LSA prefix is read through t{start}. '
            'No phase/offset or uncontrolled-program attribution is inferred from action JSON. '
            'No selected signal commands means a header-only selected-SG table, not missing native signals.'}

def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',type=Path,default=RUN)
    parser.add_argument('--out','--output',dest='out',type=Path,default=OUT)
    parser.add_argument('--start',type=int,default=START)
    parser.add_argument('--end',type=int,default=END)
    args = parser.parse_args(argv)
    if args.start < 150 or args.start % 150:
        parser.error('--start must be a 150-second boundary at or after 150')
    if args.end <= args.start or args.end % 150:
        parser.error('--end must be a 150-second boundary after --start')
    return args

def provenance_seed(manifest, receipt=None):
    seed = manifest.get('seed')
    if type(seed) is not int or seed <= 0:
        raise ValueError('Run provenance requires a positive integer seed')
    if receipt is not None and 'seed' in receipt:
        if type(receipt['seed']) is not int or receipt['seed'] != seed:
            raise ValueError('Completion receipt and provenance seed mismatch')
    return seed

def window_read_limits(file_size, start, end):
    if type(file_size) is not int or file_size <= 0:
        raise ValueError('A nonempty completed FZP is required')
    if not (150 <= start < end and start % 150 == end % 150 == 0):
        raise ValueError('Invalid bounded excerpt window')
    return {'max_bytes':file_size+1024*1024, 'deadline_sec':45,
        'window_sec':[start,end], 'expected_frames':end-start+1,
        'method':'Binary seek to the requested start; stream only the requested frame interval. '
            'File size plus 1 MiB is a byte ceiling allowing seek/header overhead, not a full-scan request.'}

def boundary_metrics(all_frames, selected, membership, document, error_reports):
    terminals = terminal_lengths(document)
    # The canonical function assumes an empty time zero. Preserve its actual
    # transition rules, then remove the artificial empty->start padding row.
    measured, rows = measure_frames((Frame(sec-START+1,
        {no:Vehicle(str(row[0]),row[2],row[3]) for no,row in frame.items()})
        for sec,frame in all_frames.items()), membership, terminals,
        end_sec=END-START+1, max_tail_extrap_sec=0)
    assert len(rows) == END-START+1
    event_keys = ('observed_exit_events','terminal_exit_inferred_events',
                  'unresolved_inside_disappearances','observed_entry_events',
                  'appeared_inside_events','reappeared_inside_events')
    events = {key:sum(row[key] for row in rows[1:]) for key in event_keys}
    ttt = rows[-1]['ttt_veh_h_cumulative']-rows[0]['ttt_veh_h_cumulative']
    independent = math.fsum((len(selected[t])+len(selected[t+1]))*.5/3600 for t in range(START,END))
    assert math.isclose(ttt,independent,rel_tol=0,abs_tol=1e-10)
    delta = len(selected[END])-len(selected[START])
    entry = events['observed_entry_events']+events['appeared_inside_events']
    td = events['observed_exit_events']+events['terminal_exit_inferred_events']
    closure = delta-entry+td+events['unresolved_inside_disappearances']
    assert closure == 0 and all(row['stock_closure_residual_veh']==0 for row in rows[1:])
    # Reuse native ERR parsing and the existing one-second collision flag.
    # Duplicate copies of a warning in run-local ERR files retain both sources.
    removals = {}
    for path,report in error_reports.items():
        assert not report['partial_tail_bytes'] and not report['unparsed_removal_lines']
        for event in report['events']:
            if event['kind'] != 'lane_change_removal': continue
            key = (event['vehicle_id'],event['link'],event['time_sec'],event['position_m'])
            row = removals.setdefault(key,{**event,'sources':[]})
            row['sources'].append({'path':path,'line_number':event['line_number']})
    matches, used = [], set()
    for sec in range(START+1,END+1):
        previous,current = all_frames[sec-1],all_frames[sec]
        for no in previous.keys()-current.keys():
            old = previous[no]
            candidates = [(key,event) for key,event in removals.items()
                if event['vehicle_id']==no and event['link']==str(old[0])
                and abs(event['time_sec']-sec)<=1]
            if not candidates: continue
            unique = len(candidates)==1 and candidates[0][0] not in used
            used.update(key for key,_ in candidates)
            inside = membership[str(old[0])]
            matches.append({'vehicle_id':no,'link':old[0],'lower_sec':sec-1,'upper_sec':sec,
                'native_times_sec':[event['time_sec'] for _,event in candidates],
                'unique_match':unique,'inside':inside,'last_position_m':old[2],
                'native_sources':[event['sources'] for _,event in candidates],
                'terminal_TD_inference_collision':bool(inside and str(old[0]) in terminals
                    and terminal_candidate(old,terminals[str(old[0])]))})
    conflicts = [row for row in matches if row['terminal_TD_inference_collision']]
    return {'schema':'r03-u030-first-window-boundary-metrics/v1','run':str(RUN),
        'window_sec':[START,END],'frame_count':len(all_frames),'completed':True,
        'method':{'function':'scripts.measure_control_area.measure_frames',
            'relative_clock':f'real{START}..{END} -> relative1..{END-START+1}; subtract first cumulative row and exclude its event counts',
            'end_sec':END-START+1,'max_tail_extrap_sec':0,
            'excluded_padding_ttt_veh_h':rows[0]['ttt_veh_h_cumulative'],
            'excluded_padding_appeared_inside':rows[0]['appeared_inside_events'],
            'TTT':f'sum of {END-START} consecutive 1s endpoint-count trapezoids; [{START},{END}]',
            'terminal_treatment':measured['terminal_inference'],
            'appearance':f'First observation inside this window, not proven internal generation; pre{START} reappearance history unavailable'},
        'TTT_veh_h':ttt,'independent_count_trapezoid_veh_h':independent,
        'N_start':len(selected[START]),'N_end':len(selected[END]),'delta_N':delta,
        **events,'entry_total':entry,'TD':td,
        'closure':{'max_abs_residual_veh':max(abs(r['stock_closure_residual_veh']) for r in rows[1:]),
            'window_residual_veh':closure},
        'observed_exit_link_pairs':measured['exit_events_by_observed_link_pair'],
        'terminal_inferred_by_link':measured['terminal_inferred_by_link'],
        'unknown_by_link':measured['unresolved_inside_disappearances_by_link'],
        'native_errors':{'files':{p:{k:v for k,v in r.items() if k not in ('events','unparsed')}
                                 for p,r in error_reports.items()},
            'matches':matches,'terminal_removal_collisions':conflicts,
            'ambiguous_matches':[r for r in matches if not r['unique_match']],
            'unmatched_near_window_removals':[r for key,r in removals.items()
                if START-1<=r['time_sec']<=END+1 and key not in used],
            'scope':'ID + last link + warning within 1s of disappearance upper frame; flags do not subtract or relabel canonical TD/unknown'},
        'TD_requires_review':bool(conflicts or events['unresolved_inside_disappearances']
                                  or any(not r['unique_match'] for r in matches)),
        'time_rows':[dict(r,sim_sec=r['sim_sec']+START-1,
                         ttt_veh_h_cumulative=r['ttt_veh_h_cumulative']-rows[0]['ttt_veh_h_cumulative'])
                     for r in rows[1:]]}

def main():
    global RUN, OUT, START, END
    args = parse_args()
    START, END = args.start, args.end
    RUN,OUT = args.run.resolve(strict=True),args.out.resolve()
    names = ('inside_frames.json.gz','timeseries.csv',*command_artifact_names(START),
        'summary.json','boundary_metrics.json','outside123_context.json')
    if any((OUT/name).exists() for name in names):
        raise FileExistsError('Preserved output exists; use a fresh --out directory')
    manifest_path = RUN / ('run_provenance_' + RUN.name + '.json')
    manifest = load(manifest_path)
    seed = provenance_seed(manifest)
    assert manifest['sim_period_sec'] >= END
    assert manifest['control_interval_sec'] == 150, 'Command comparison requires a 150s action cadence'
    log_path = RUN / ('runlog_' + RUN.name + '.txt')
    assert b'STAGE=SIM_DONE' in log_path.read_bytes()
    membership_path = ROOT / 'diagnostics/control_area_membership.json'
    document = load(membership_path)
    physical_sha = snapshot_network_sha256({'network_path':manifest['files']['network']['path'],
        'run_provenance':{'manifest_path':str(manifest_path),'run_id':manifest['run_id']}})
    assert physical_sha == document['network']['sha256']
    membership = physical_membership_from_ledger(document)
    mapping_path = Path(manifest['files']['control_mapping']['path'])
    assert sha(mapping_path) == manifest['files']['control_mapping']['sha256']
    source_paths = [manifest_path,log_path,membership_path,mapping_path,Path(__file__),
        *(ROOT/name for name in ('scripts/measure_control_area.py',
            'diagnostics/capture_native_runtime_errors.py','diagnostics/summarize_fast_nc.py',
            'diagnostics/probe_e8_lane_receiving.py','diagnostics/probe_e8_window_passages.py',
            'diagnostics/audit_observer_control_pair.py',
            'evaluation/controllers/control_area_objective.py',
            'evaluation/controllers/network_provenance.py'))]
    sources = {str(path):sha(path) for path in source_paths}
    recording_copy = manifest['files']['network']['sha256'] != physical_sha
    receipt_path = RUN/'completion_receipt.json'
    if receipt_path.is_file():
        receipt = load(receipt_path)
        assert receipt['completed'] is True
        assert (Path(receipt['provenance_path']).resolve()==manifest_path.resolve()
                and receipt['provenance_sha256']==sources[str(manifest_path)]
                and receipt['terminal_sec']==manifest['sim_period_sec'])
        seed = provenance_seed(manifest, receipt)
        if recording_copy:
            assert receipt['native_execution_passed'] is True
        sources[str(receipt_path)] = sha(receipt_path)
        completion_scope = {'receipt':{'path':str(receipt_path),'sha256':sources[str(receipt_path)]},
            'completed':True,'native_execution_passed':receipt.get('native_execution_passed'),
            'native_lsa_com_coverage_passed':receipt.get('native_lsa_com_coverage_passed'),
            'scope':'Existing completion receipt only; no repeated native audit; independent LSA verdict unchanged'}
    else:
        legacy_default = ROOT/'evaluation/runs/codex_selected_fw070_u030_beta0_r03'
        assert RUN==legacy_default.resolve() and not recording_copy, 'A new run requires its completion receipt before FZP access'
        completion_scope = {'receipt':None,'native_execution_passed':None,
            'native_lsa_com_coverage_passed':None,
            'scope':'Legacy fallback: preserved STAGE=SIM_DONE and manifest extent only; no process/native execution certification'}
    mapping = load(mapping_path); chain = mapping['freeway_model_links']['FW_E']
    offsets = dict(zip(chain['chain_links'], chain['chain_offsets_m']))
    bounds = chain['segment_bounds_m']
    fzp, = (RUN / 'vissim_eval').glob('*.fzp')
    read_started = time.monotonic()
    before = fzp.stat()
    read_limits = window_read_limits(before.st_size, START, END)
    deadline = read_started+read_limits['deadline_sec']
    reader = IndexedFzp(fzp, max_bytes=read_limits['max_bytes'])
    proof, selected, series, all_frames = [], {}, [], {}
    try:
        for sec, frame in frames(reader, START, END, deadline, proof):
            if time.monotonic() > deadline:
                raise RuntimeError('45-second per-window read/processing deadline exhausted')
            assert sec == int(sec)
            all_frames[int(sec)] = frame
            inside = {}
            groups = defaultdict(list)
            for no, row in frame.items():
                link, lane, pos, speed = row
                assert str(link) in membership
                assert lane > 0 and math.isfinite(pos) and math.isfinite(speed) and speed >= 0
                if not membership[str(link)]: continue
                inside[no] = row
                groups[str(link)].append(row)
                if link in offsets:
                    cell = bisect_right(bounds, pos+offsets[link])-1
                    if cell in (8,9): groups['E'+str(cell)].append(row)
            selected[int(sec)] = inside
            for key in sorted(groups):
                rows = groups[key]
                series.append({'sec':int(sec),'link_or_cell':key,'n':len(rows),
                    'stop_le1_kph':sum(r[3]<=1 for r in rows),
                    'slow_lt30_kph':sum(r[3]<30 for r in rows),
                    'mean_speed_kph':sum(r[3] for r in rows)/len(rows)})
    finally:
        reader.handle.close()
    assert list(selected) == list(range(START,END+1))
    assert (before.st_size,before.st_mtime_ns) == (fzp.stat().st_size,fzp.stat().st_mtime_ns)
    read_elapsed = time.monotonic()-read_started
    OUT.mkdir(parents=True,exist_ok=True)
    with gzip.open(OUT/'inside_frames.json.gz','xt',encoding='utf-8') as stream:
        json.dump(selected,stream,separators=(',',':'))
    write('timeseries.csv',series)
    by_key = defaultdict(dict)
    for row in series: by_key[row['link_or_cell']][row['sec']] = row
    watched = ('E8','E9','10682','121','10639','10681','10646','71','420','329')
    all_keys = set(by_key) | set(watched)
    totals = []
    for key in sorted(all_keys):
        at = lambda t: by_key[key].get(t, {'n':0,'stop_le1_kph':0,'slow_lt30_kph':0,'mean_speed_kph':None})
        row = {'link_or_cell':key}
        for label, field in [('residence','n'),('stopped','stop_le1_kph'),('slow','slow_lt30_kph')]:
            row[label+'_veh_h'] = math.fsum((at(t)[field]+at(t+1)[field])*.5/3600 for t in range(START,END))
        row['snapshots'] = {str(t):at(t) for t in range(START,END+1,30)}
        row['window_max_stopped'] = max(at(t)['stop_le1_kph'] for t in range(START,END+1))
        totals.append(row)
    command_summary = command_evidence(RUN, START, sources)
    error_paths = sorted(RUN.glob('vissim_*.err'))
    assert any(p.name.startswith('vissim_simulation_') for p in error_paths)
    error_reports = {}
    for path in error_paths:
        data = path.read_bytes()
        sources[str(path)] = hashlib.sha256(data).hexdigest()
        error_reports[str(path)] = parse_bytes(data)
    boundary = boundary_metrics(all_frames,selected,membership,document,error_reports)
    boundary['seed'] = seed
    boundary['physical_membership'] = {'path':str(membership_path),
        'source_network_sha256':physical_sha,'record_only_runtime_network':manifest['files']['network'],
        'runtime_network_differs_from_verified_physical_source':recording_copy,'membership_unchanged':True}
    boundary['completion_evidence'] = completion_scope
    boundary['fzp'] = {'path':str(fzp),'size':before.st_size,'mtime_ns':before.st_mtime_ns,
        'bytes_read':reader.bytes_read,'read_elapsed_sec':read_elapsed,'selected_range':proof,
        'read_limits':read_limits,
        'scope':f'All vehicles in the same single bounded {END-START+1}-frame read; no full-run scan'}
    assert membership['123'] is False
    outside_series, outside_snapshots = [], []
    for sec,frame in all_frames.items():
        vehicles = [(no,row) for no,row in frame.items() if row[0]==123]
        record = {'sec':sec,'n':len(vehicles),
            'stopped_le1_kph':sum(row[3]<=1 for _,row in vehicles),
            'slow_lt30_kph':sum(row[3]<30 for _,row in vehicles),
            'mean_speed_kph':sum(row[3] for _,row in vehicles)/len(vehicles) if vehicles else None}
        outside_series.append(record)
        if (sec-START)%30==0:
            outside_snapshots.append({**record,'vehicles':[{'vehicle':no,'lane':row[1],
                'pos_m':row[2],'speed_kph':row[3]} for no,row in vehicles]})
    outside = {'physical_link':'123','inside_omega':False,'window_sec':[START,END],
        'scope':f'Same single complete {END-START+1}-frame read; outside Omega, excluded from inside aggregates. No throughput or full-run recovery inference.',
        'fzp_path':str(fzp),'fzp_stat':{'size':before.st_size,'mtime_ns':before.st_mtime_ns},
        'read_bytes':reader.bytes_read,'additional_fzp_read_bytes':0,'selected_range':proof,
        'snapshots':outside_snapshots,'time_rows':outside_series}
    for label,key in (('residence','n'),('stopped','stopped_le1_kph'),('slow','slow_lt30_kph')):
        outside[label+'_veh_h'] = math.fsum((a[key]+b[key])*.5/3600
            for a,b in zip(outside_series,outside_series[1:]))
    top = sorted((r for r in totals if not r['link_or_cell'].startswith('E')),key=lambda r:r['stopped_veh_h'],reverse=True)
    result = {'run':str(RUN),'seed':seed,'window_sec':[START,END], 'completed':True,
        'completion_evidence':completion_scope,
        'definitions':{'stop':'SPEED <= 1 km/h','slow':'SPEED < 30 km/h','integration':'trapezoid of consecutive complete 1s counts; same vehicle can contribute repeatedly; not individual waiting time',
        'E8_chain_m':[bounds[8],bounds[9]],'E9_chain_m':[bounds[9],bounds[10]],
        'scope':f'{END-START}s observation only; no global peak/recovery/full-run claim, no performance comparator; terminal action at {END} excluded. Intermediate action tables remain available in the run; the command summary here describes t{START}.'},
        'outside_context':{'123':f'Outside Omega; excluded from inside aggregates. See outside123_context.json from the same single {END-START+1}-frame read, with30s snapshots.'},
        'fzp':{'path':str(fzp),'size':before.st_size,'mtime_ns':before.st_mtime_ns,'bytes_read':reader.bytes_read,'selected_range':proof,
            'read_limits':read_limits,
            'read_elapsed_sec':read_elapsed,'inside_cache_sha256':sha(OUT/'inside_frames.json.gz')},'sources':sources,
        'inside_n':{str(t):len(selected[t]) for t in range(START,END+1,30)},
        'watched':{r['link_or_cell']:r for r in totals if r['link_or_cell'] in watched},
        'top_stopped_physical_links':top[:15],
        **command_summary,
        'all_physical_link_summaries':totals}
    assert (before.st_size,before.st_mtime_ns) == (fzp.stat().st_size,fzp.stat().st_mtime_ns)
    source_changes = [p for p,digest in sources.items() if sha(Path(p))!=digest]
    assert not source_changes, source_changes
    boundary.update(source_pins=sources,source_changes=source_changes)
    save('boundary_metrics.json',boundary)
    save('outside123_context.json',outside)
    save('summary.json',result)
    print(json.dumps({k:result[k] for k in ('inside_n','vsl_changed_rows','meter_changed_physical_greens',f'meter_group_rates_{START}')},ensure_ascii=False))
    print('read_bytes',reader.bytes_read,'top',[(r['link_or_cell'],r['stopped_veh_h']) for r in top[:10]])

if __name__=='__main__':main()
