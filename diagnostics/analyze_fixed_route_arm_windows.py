"""Prepare bounded spatial evidence for fixed-control network arms.

New output only. Collection reuses the existing SC1004 analyzer sequentially;
summaries use its pinned selected-frame cache, never a second FZP scan.
No adapter, endpoint, optimizer, COM or simulator is called.
"""
from __future__ import annotations

import argparse
from bisect import bisect_right
from collections import Counter, defaultdict
from contextlib import ExitStack
import gzip
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
WINDOWS = ((750, 900), (900, 1050))
ARMS = ('baseline', 'lcd10635_2000', 'upstream1135')
OUTLETS = (10646, 10773, 10681)
EXTRA_ROADS = {52, 66, 46, 68, 121, 10629, 10633, 10625, 10772, *OUTLETS,
               10635, 10634, 10641, 10643, 10659, 10660}
ROUTE_VALIDATION = ROOT/'diagnostics/fixed_beta300v3_network_arms_v1/upstream1135/validation.json'


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream, 'sha256').hexdigest()


def load(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def workspace_path(value):
    path=Path(value)
    path=(path if path.is_absolute() else ROOT/path).resolve()
    if not path.is_relative_to(ROOT):raise ValueError('Analysis input is outside this workspace')
    return path


def command_value(command, key):
    if not isinstance(command,list) or command.count(key)!=1:
        raise ValueError('Missing or repeated batch command argument: '+key)
    index=command.index(key)
    if index+1==len(command):raise ValueError('Missing batch command value: '+key)
    return command[index+1]


def collect_window(run_name, network, output, start, end):
    """Existing analyzer, with scoped diagnostic globals restored on exception.

    This is deliberately sequential. It inherits the 64 MiB/45 s per-window
    indexed read budget and does not relax missing-frame checks.
    """
    from diagnostics import diagnose_sc1004_first_control_window as old
    original_clock = old.clock

    def split_clock(run):
        actual, proof = original_clock(run)
        native = old.native_signal_prefix(next(run.glob('vissim_eval/*.lsa')), end)
        def state(sc, sg, sec, stage='immediate'):
            # post_step900 still closes native warmup; immediate900 begins hold.
            if sec < 900 or (sec == 900 and stage == 'post_step'):
                events = native['groups'].get(f'{sc}:{sg}', [])
                i = bisect_right([row[0] for row in events], sec)-1
                if i < 0:raise ValueError('Missing native warmup SG initial state')
                return events[i][1]
            return actual(sc, sg, sec, stage)
        return state, {**proof, 'cutover':'native through post_step900; fixed control from immediate900'}

    output.mkdir(parents=True, exist_ok=False)
    tree = ET.parse(network).getroot()
    links = {node.get('no'):node for node in tree.findall('./links/link')}
    roads = old.ROADS | EXTRA_ROADS
    watched = set(roads)
    for no,node in links.items():
        a,b=node.find('fromLinkEndPt'),node.find('toLinkEndPt')
        if a is not None and b is not None and (int(a.get('lane').split()[0]) in roads or int(b.get('lane').split()[0]) in roads):
            watched.add(int(no))
    with ExitStack() as stack:
        for key,value in {'START':start,'END':end,'OUT':output,'ROADS':roads,'clock':split_clock}.items():
            stack.enter_context(patch.object(old,key,value))
        geo=old.geometry(network)
        payload=old.analyze('arm',run_name,geo,links,watched)
    result={'schema':'fixed-route-arm-selected-window/v1','window':[start,end],
            'network_path':str(network),'network_sha256':sha(network),'head_geometry':geo,
            'run':payload,'selected_links':sorted(watched),
            'reused_analyzer_sha256':sha(Path(old.__file__))}
    write(output/'diagnosis.json',result)
    return result


def route_observations(run, start, end):
    """Only actual current-route envelopes, never lane-based route inference."""
    result=defaultdict(list);pins={};missing=[]
    for sec in (750,900,1050):
        if not start <= sec <= end:continue
        path=run/('decisions_'+run.name)/f'state_{sec:06d}.json'
        if not path.exists():missing.append(sec);continue
        raw=load(path);pins[str(path)]=sha(path);env=raw.get('vehicle_routes')
        if sha(path)!=pins[str(path)]:raise ValueError('Route observation changed while reading')
        if env is None:missing.append(sec);continue
        if (env.get('complete') is not True or env.get('sim_sec_before') != sec
                or env.get('sim_sec_after') != sec or len(env['records']) != env['record_count']):
            raise ValueError('Incomplete or mismatched current-route envelope')
        ids=[row['veh_no'] for row in env['records']]
        if len(ids)!=len(set(ids)):raise ValueError('Duplicate route identity row')
        for row in env['records']:
            result[int(row['veh_no'])].append({'sec':sec,'decision':row['route_decision_no'],
                'route':row['route_no'],'type':row['route_decision_type']})
    return result, {'source_sha256':pins,'missing_snapshot_seconds':missing,
                    'scope':'150 s snapshots; missing current selections are not reconstructed.'}


def in_green(payload, group, sec):
    return any(a <= sec < b for a,b in payload['green_windows'][group])


def summarize_window(document, route_map, removals):
    start,end=document['window'];payload=document['run'];network=Path(document['network_path'])
    if sha(network)!=document['network_sha256']:raise ValueError('Network changed after extraction')
    cache=Path(payload['fzp']['selected_cache'])
    if sha(cache)!=payload['fzp']['selected_cache_sha256']:raise ValueError('Selected cache changed')
    with gzip.open(cache,'rt',encoding='utf-8') as stream:
        # One bounded selected-road window; reject accidental full-network dumps.
        raw=stream.read(128*1024*1024+1)
    if len(raw)>128*1024*1024:raise ValueError('Selected-frame cache exceeds 128 MiB limit')
    frames={int(t):{int(no):row for no,row in values.items()} for t,values in json.loads(raw).items()}
    del raw
    if sorted(frames)!=list(range(start,end+1)):raise ValueError('Expected complete one-second selected grid')
    tracks=defaultdict(list)
    for sec,values in frames.items():
        for no,row in values.items():tracks[no].append([sec,*row])
    run=ROOT/'evaluation/runs'/payload['run']
    observed,route_proof=route_observations(run,start,end)
    entries,exits=payload['road_entries'],payload['road_exits']
    removal_by_id=defaultdict(list)
    for event in removals:
        # Warning times and the first absent one-second sample may differ by1 s.
        if event['kind']=='lane_change_removal' and start-1 <= event['time_sec'] <= end:
            removal_by_id[event['vehicle_id']].append(event)

    # N closure includes every observed road departure, including separately
    # labelled global absences. Those absences are never treated as throughput.
    def stock(no,t):return sum(row[0]==no for row in frames[t].values())
    enter71=[e for e in entries if e['link']==71];leave71=[e for e in exits if e['link']==71]
    residual=stock(71,start)+len(enter71)-len(leave71)-stock(71,end)
    if residual:raise ValueError('Observed link71 stock does not close')
    lane_changes=[];blocked=defaultdict(list)
    heads={h['lane']:h for h in document['head_geometry']['71']['heads']}
    for sec in range(start,end):
        for no,row in frames[sec].items():
            if row[0]!=71:continue
            next_row=frames[sec+1].get(no)
            if next_row and next_row[0]==71 and next_row[1]!=row[1]:
                lane_changes.append({'vehicle':no,'lower_sec':sec,'upper_sec':sec+1,
                                     'from_lane':row[1],'to_lane':next_row[1],'positions_m':[row[2],next_row[2]]})
            head=heads.get(row[1])
            if head and row[3]<=1 and 0 <= head['pos_m']-row[2] <= 20 and in_green(payload,f"{head['SC']}:{head['sg']}",sec):
                behind=sum(other[0]==71 and other[1]==row[1] and other[2]<row[2] and other[3]<=1 for other in frames[sec].values())
                blocked[no].append({'sec':sec,'lane':row[1],'pos_m':row[2],'sg':head['sg'],'stopped_behind':behind})
    blockers=[]
    for no,rows in blocked.items():
        routes=[r for r in observed.get(no,[]) if r['type']=='STATIC' and r['decision']==1126 and r['route']==1]
        warnings=[r for r in removal_by_id.get(no,[]) if r['route_decision']==1126 and r['route_index']==1]
        blockers.append({'vehicle':no,'green_stopped_samples':rows,'sampled_green_stopped_seconds':len(rows),
            'route1126_1_snapshots':routes,'explicit_removal_route1126_1':warnings,
            'observed10635':any(row[1]==10635 for row in tracks[no]),
            'lane_changes':[r for r in lane_changes if r['vehicle']==no],
            'scope':'Near-head stopped sample during GREEN; causal blocking and unobserved lane-change intention are not inferred.'})

    tree=ET.parse(network).getroot()
    decisions={node.get('no'):node for node in tree.findall('./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic')}
    cohort_rows=[];cohort_summary={}
    for decision_no in ('1123','1124','1125'):
        decision=decisions[decision_no];source=int(decision.get('link'));gate=float(decision.get('pos'))
        mapping=[r for r in route_map if r['parent_decision']==decision_no]
        first_connector=int(mapping[0]['path'][1]);gates=[]
        for sec in range(start,end):
            for no,a in frames[sec].items():
                b=frames[sec+1].get(no)
                if a[0]==source and b and b[0]==source and a[2]<gate<=b[2]:
                    gates.append({'vehicle':no,'lower_sec':sec,'upper_sec':sec+1,'lane_pair':[a[1],b[1]],
                                  'linear_interpolation_sec':sec+(gate-a[2])/(b[2]-a[2])})
        duplicates={no for no,count in Counter(e['vehicle'] for e in gates).items() if count>1}
        outcomes=Counter();stem_outcomes=Counter();known=Counter();common_choices=Counter()
        stem=0;seen_selected=0;observed_common=0
        for entry in gates:
            no=entry['vehicle'];future=[r for r in tracks[no] if r[0]>=entry['upper_sec']]
            receipt=next((r for r in future if r[1]==first_connector),None)
            outlet=next((r for r in future if r[1] in OUTLETS),None)
            stem_outlet=next((r for r in future if receipt and r[0]>=receipt[0] and r[1] in OUTLETS),None)
            choices=[r for r in observed.get(no,[]) if entry['upper_sec']<=r['sec']<=end
                     and r['type']=='STATIC' and (r['decision']==int(decision_no) or r['decision']==1135)]
            chosen={r['route'] for r in choices if r['decision']==int(decision_no) and r['route'] in (4,5,6)}
            selected_branches={str(row['old_downstream_route']) for row in mapping for choice in choices
                if (choice['decision']==int(decision_no) and str(choice['route'])==str(row['new_route']))
                or (choice['decision']==1135 and str(choice['route'])==str(row['old_downstream_route']))}
            warnings=[r for r in removal_by_id.get(no,[]) if r['time_sec']>=entry['lower_sec']]
            status=('repeat_gate_ambiguous' if no in duplicates else 'outlet:'+str(outlet[1]) if outlet else
                    'explicit_removal_before_observed_outlet' if warnings else
                    'right_censored_in_selected_region' if no in frames[end] else 'left_selected_region_or_unresolved_absence')
            if no not in duplicates:
                outcomes[status]+=1;stem+=receipt is not None
                if receipt is not None:
                    stem_status=('outlet:'+str(stem_outlet[1]) if stem_outlet else
                                 'outlet_before_stem_order_unresolved' if outlet else status)
                    stem_outcomes[stem_status]+=1
                    if len(chosen)==1:known[str(next(iter(chosen)))]+=1;seen_selected+=1
                    if len(selected_branches)==1:common_choices[next(iter(selected_branches))]+=1;observed_common+=1
            cohort_rows.append({**entry,'decision':decision_no,'gate_link':source,'gate_pos_m':gate,
                'lane_change_at_gate':entry['lane_pair'][0]!=entry['lane_pair'][1],
                'replacement_stem_entry_sample':receipt,'outlet_entry_sample':outlet,'outcome':status,
                'outlet_after_observed_stem_sample':stem_outlet,
                'observed_outlet_departures':[e for e in exits if e['vehicle']==no and e['link'] in OUTLETS
                                              and e['lower_sec']>=entry['lower_sec']],
                'current_route_snapshots':choices,'conflicting_current_child_routes':len(chosen)>1,
                'observed_common1135_choices':sorted(selected_branches),
                'removal_warnings':warnings,'last_selected_sample':future[-1] if future else None})
        denom=len(gates)-sum(e['vehicle'] in duplicates for e in gates)
        resolved=sum(value for key,value in stem_outcomes.items() if key.startswith('outlet:'))
        cohort_summary[decision_no]={'physical_gate_crossings':len(gates),'excluded_repeated_gate_ids':sorted(duplicates),
            'observed_unique_gate_cohort':denom,'observed_replacement_stem_entries':stem,'all_gate_outcomes':dict(outcomes),
            'observed_stem_outcomes':dict(stem_outcomes),
            'physical_outlet_fractions_among_resolved_stem':{str(k):stem_outcomes['outlet:'+str(k)]/resolved if resolved else None for k in OUTLETS},
            'resolved_stem_outlet_denominator':resolved,
            'stem_outlet_resolution_coverage':resolved/stem if stem else None,
            'observed_current_newroute_counts':dict(known),
            'current_newroute_observation_coverage_of_stem':seen_selected/stem if stem else None,
            'observed_current_newroute_fractions':{str(k):known[str(k)]/seen_selected if seen_selected else None for k in (4,5,6)},
            'observed_common1135_choice_counts':dict(common_choices),
            'current_common_choice_coverage_of_stem':observed_common/stem if stem else None,
            'observed_common1135_choice_fractions':{str(k):common_choices[str(k)]/observed_common if observed_common else None for k in (2,3,4)},
            'declared_conditional_route_priors':{r['new_route']:r['conditional_branch_probability'] for r in mapping},
            'left_edge_source_postgate_count':sum(r[0]==source and r[2]>=gate for r in frames[start].values()),
            'source_entries_first_seen_after_gate':[e for e in entries if e['link']==source and e['pos']>=gate],
            'scope':'Gate is a same-road POS bracket; interpolation is an estimate and lane changes remain explicit. Conditional fractions require observed replacement-stem receipt, excluding other gate branches. Short skipped connectors and unobserved choices remain unresolved; 150 s route snapshots are a selected subset.'}

    arrivals420=[]
    for event in entries:
        if event['link']!=420:continue
        rows=tracks[event['vehicle']];arrival=event['upper_sec']
        prior=[r[1] for r in rows if r[0]<=arrival]
        future=[r for r in rows if r[0]>=arrival]
        downstream=next((r for r in future if r[1]==1220007200),None)
        stopped=next((r for r in future if r[1]==420 and r[4]<=1),None)
        arrivals420.append({**event,'observed_source_family':'127' if 127 in prior else '329' if 329 in prior else '72' if 72 in prior else 'unobserved',
            'SC105_green_at420_arrival':{sg:in_green(payload,'105:'+sg,arrival) if arrival<end else None for sg in ('4','7')},
            'downstream1220007200_first_sample':downstream,'first_stopped420_sample':stopped,
            'scope':'Downstream GREEN at420 arrival is temporal context; no implied zero travel time or assigned SG authority.'})
    result={'window':[start,end],'cache_sha256':sha(cache),'route_observation':route_proof,
        'stock71':{'initial':stock(71,start),'arrivals':len(enter71),'departures_including_absence':len(leave71),
            'final':stock(71,end),'residual':residual,'observed_connector_departures':dict(Counter(str(e['to']) for e in leave71 if e['to'] is not None)),
            'global_endpoint_absences':[e for e in leave71 if e['to'] is None]},
        'sg71_summary':payload['sg71_summary'],'near_head_green_stopped_cohorts':blockers,'lane71_changes':lane_changes,
        'decision_cohorts':cohort_rows,'decision_summary':cohort_summary,'arrivals420':arrivals420,
        'green_windows':payload['green_windows'],'explicit_removal_events':[r for rows in removal_by_id.values() for r in rows],
        'native_route_warnings':[e for e in removals if e['kind'] in ('ignored_static_routing','route_next_link_not_found')
                                 and start<=e['time_sec']<end],
        'endpoint_stopped':{str(link):sum(r[0]==link and r[3]<=1 for r in frames[end].values()) for link in (71,420,1220007200)}}
    if sha(cache)!=result['cache_sha256']:raise ValueError('Cache changed during summary')
    return result


def baseline_trajectory_certificate(manifest):
    """Check the driver's full-baseline result, without rereading the FZP."""
    baseline=manifest['arms'][0]
    proof=baseline.get('baseline_trajectory_comparison',{})
    reference=manifest.get('baseline_trajectory_reference',{})
    fields=['header','payload_sha256','payload_bytes','rows','first_sec','last_sec']
    if (proof.get('schema')!='fixed-beta300v3-baseline-trajectory/v1'
            or any(proof.get(k) is not True for k in ('valid','terminal1050_valid','ordered_payload_exact',
                                                       'reference_unchanged_since_preflight'))
            or proof.get('different_fields')!=[] or proof.get('compared_fields')!=fields):
        raise ValueError('Baseline full-trajectory equality certificate missing or invalid')
    actual,old=proof['actual'],proof['reference']
    if any(actual[k]!=old[k] for k in fields):raise ValueError('Baseline trajectory equality fields differ')
    for record in (actual,old):
        if (type(record['rows']) is not int or record['rows']<=0 or record['payload_bytes']<=0
                or not math.isfinite(record['first_sec']) or not 0<=record['first_sec']<1050
                or record['last_sec']!=1050):
            raise ValueError('Baseline trajectory has invalid extent')
    old_run=workspace_path(reference['run'])
    new_run=workspace_path(baseline['run'])
    if (proof.get('source_run')!=reference.get('source_run') or old_run.name!=reference.get('source_run')
            or old_run.parent!=(ROOT/'evaluation/runs').resolve()
            or workspace_path(old['path'])!=workspace_path(reference['fzp'])
            or not workspace_path(old['path']).is_relative_to(old_run)
            or not workspace_path(actual['path']).is_relative_to(new_run)
            or old['file_sha256']!=reference['fzp_sha256']):
        raise ValueError('Baseline trajectory certificate source identity differs')
    expected_provenance={new_run/('run_provenance_'+baseline['name']+'.json'),
                         old_run/('run_provenance_'+reference['source_run']+'.json')}
    if {workspace_path(p) for p in proof.get('provenance_sha256',{})}!=expected_provenance:
        raise ValueError('Baseline trajectory provenance set differs')
    old_provenance=old_run/('run_provenance_'+reference['source_run']+'.json')
    if next(key for p,key in proof['provenance_sha256'].items() if workspace_path(p)==old_provenance)!=reference['provenance_sha256']:
        raise ValueError('Baseline reference provenance SHA differs')
    return proof


def qualify_batch(manifest_path):
    """Consume the completed driver's certificate, and recheck analysis inputs.

    The historical runtime pin certificate is retained, not reinterpreted as a
    requirement that today's analysis use those old controller source bytes.
    No large native file is hashed or scanned by this qualification function.
    """
    path=workspace_path(manifest_path);manifest=load(path)
    if (manifest.get('schema')!='fixed-beta300v3-three-arm-experiment/v1'
            or manifest.get('status')!='all_three_execution_and_readback_passed'
            or manifest.get('completed') is not True or manifest.get('valid') is not True
            or manifest.get('source_changes')!=[]):
        raise ValueError('Completed three-arm execution/readback certificate required')
    if [row['arm'] for row in manifest['arms']]!=list(ARMS):raise ValueError('Wrong or reordered arm set')
    trajectory_proof=baseline_trajectory_certificate(manifest)
    pins={str(path):sha(path)};specs=[]
    def pin(raw_path, expected):
        target=workspace_path(raw_path)
        if sha(target)!=expected:raise ValueError('Analysis input SHA mismatch: '+str(target))
        pins[str(target)]=expected
        return target
    for name,key in trajectory_proof['provenance_sha256'].items():pin(name,key)
    for row in manifest['arms']:
        if (row.get('status')!='passed' or row.get('completed') is not True or row.get('valid') is not True
                or row.get('exit_code')!=0 or row.get('post_run_processes')!=[]):
            raise ValueError('Incomplete arm: '+row['arm'])
        run_dir=workspace_path(row['run']);command=row['command']
        if run_dir.parent!=(ROOT/'evaluation/runs').resolve() or run_dir.name!=row['name']:
            raise ValueError('Wrong arm run identity')
        if workspace_path(command_value(command,'-OutDir'))!=run_dir:raise ValueError('Command output differs from arm run')
        expected={'-SimPeriod':'1050','-Seed':'13','-ControlStartSec':'900','-ControlIntervalSec':'150',
                  '-WarmupController':'no-control','-Controller':'diagnostic-signal-profile','-StateLogIntervalSec':'30'}
        if any(str(command_value(command,key))!=value for key,value in expected.items()):
            raise ValueError('Arm clock/control contract differs')
        if command_value(command,'-Name')!=row['name']:raise ValueError('Command run name differs')
        network=pin(command_value(command,'-Network'),row['network_sha256'])
        validation=row['validation']
        if (validation.get('status')!='execution_and_command_readback_passed'
                or validation.get('window')!={'start':900,'end':1050,'include_post_step1050':True,'include_immediate1050':False}
                or validation.get('signal_ramp_readback',{}).get('valid') is not True
                or validation.get('vsl_apply_readback_rows')!=66):
            raise ValueError('Required same-window actuator certificate missing')
        commands=validation['commands']
        if [x['sim_sec'] for x in commands]!=[1,150,300,450,600,750,900,1050] or not all(x['physical_exact'] is True for x in commands):
            raise ValueError('Incomplete fixed-command certificate')
        decision_dir=run_dir/('decisions_'+row['name'])
        for item in commands:
            command_path=pin(item['path'],item['sha256'])
            if command_path!=decision_dir/f"action_{item['sim_sec']:06d}.csv":raise ValueError('Command belongs to another arm')
        if {workspace_path(x['path']) for x in validation['raw_states']}!={decision_dir/f'state_{sec:06d}.json' for sec in (900,1050)}:
            raise ValueError('Raw boundary states belong to another window/arm')
        for item in validation['raw_states']:pin(item['path'],item['sha256'])
        if not validation['readback_sources']:raise ValueError('Readback source pins absent')
        for name,key in validation['readback_sources'].items():
            if not pin(name,key).is_relative_to(run_dir):raise ValueError('Readback belongs to another run')
        native={}
        for suffix in ('.fzp','.lsa','.err'):
            values=[]
            for item in validation['native_outputs'][suffix]:
                target=workspace_path(item['path'])
                if not target.is_relative_to(run_dir) or target.suffix.lower()!=suffix or target.stat().st_size!=item['bytes']:
                    raise ValueError('Native file identity/length differs')
                values.append(target)
            native[suffix]=values
        for suffix in ('.fzp','.lsa'):
            # The reused analyzer selects from this directory. Refuse ambiguity
            # rather than silently selecting a different simulation replica.
            discovered=list(run_dir.glob('vissim_eval/*'+suffix))
            if len(native[suffix])!=1 or discovered!=native[suffix]:raise ValueError('Ambiguous native output '+suffix)
        if row['arm']=='baseline':
            recorded=trajectory_proof['actual']
            if workspace_path(recorded['path'])!=native['.fzp'][0] or recorded['file_bytes']!=native['.fzp'][0].stat().st_size:
                raise ValueError('Baseline trajectory certificate refers to another native output')
        err=run_dir/'vissim_simulation_001.err'
        if err not in native['.err']:raise ValueError('Final archived native ERR absent from driver evidence')
        pin(err,sha(err))
        specs.append({'arm':row['arm'],'run':run_dir,'network':network,'network_sha256':row['network_sha256'],
                      'err':err,'native_stats':{str(p):[p.stat().st_size,p.stat().st_mtime_ns] for paths in native.values() for p in paths},
                      'validation':validation})
    return manifest,specs,pins


def validate_route_map(path, upstream_network):
    rows=load(path)['route_mapping']
    if len(rows)!=9 or {(str(r['parent_decision']),str(r['new_route'])) for r in rows}!={
            (d,r) for d in ('1123','1124','1125') for r in ('4','5','6')}:
        raise ValueError('Expected exact nine expanded route identities')
    tree=ET.parse(upstream_network).getroot()
    decisions={x.get('no'):x for x in tree.findall('./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic')}
    if '1135' in decisions:raise ValueError('Treatment still contains downstream decision1135')
    for row in rows:
        decision=decisions[str(row['parent_decision'])]
        route=decision.find("./vehRoutSta/vehicleRouteStatic[@no='"+str(row['new_route'])+"']")
        # The native tree uses vehRoutSta; fail if its schema changes.
        if route is None:raise ValueError('Expanded native route missing')
        native_path=[decision.get('link')]+[x.get('key') for x in route.findall('./linkSeq/intObjectRef')]+[route.get('destLink')]
        if native_path!=row['path'] or route.get('relFlow')!=row['written_relFlow']:
            raise ValueError('Route proof path or weight differs from the actual treatment network')
        if route.get('destLink')!=row['destination']['link'] or route.get('destPos')!=row['destination']['pos_raw']:
            raise ValueError('Route proof destination differs')
    return rows


def run(manifest_path, output, route_path=ROUTE_VALIDATION):
    """Analyze only a finished, verified batch; create an entirely new output."""
    output=workspace_path(output)
    if output.exists():raise ValueError('New analysis directory required')
    manifest,specs,pins=qualify_batch(manifest_path)
    route_path=workspace_path(route_path)
    route_map=validate_route_map(route_path,next(x['network'] for x in specs if x['arm']=='upstream1135'))
    pins.update({str(route_path):sha(route_path),str(Path(__file__)):sha(__file__)})
    output.mkdir(parents=True)
    result={'schema':'fixed-route-arm-spatial-comparison/v1','windows':WINDOWS,'runs':{},'source_sha256':pins,
        'batch_manifest':str(workspace_path(manifest_path)),
        'qualification':'Driver completed all three1050-second fixed-command/readback runs. Analysis rechecks network, command, raw-state and readback bytes; no new vehicle-eligibility claim.',
        'historical_runtime_source_certificate':manifest['source_sha256'],
        'baseline_trajectory_reference':manifest['baseline_trajectory_reference'],
        'baseline_full_trajectory_certificate':manifest['arms'][0]['baseline_trajectory_comparison'],
        'baseline_trajectory_recheck_scope':'Completed driver certificate/header/payload/count/terminal equality and source/provenance identity checked; no second full FZP scan.',
        'limits':['Network changes apply from time0; equal warmup commands do not imply equal state900.',
                  'Common seed does not preserve per-vehicle RNG route choices after route-tree expansion; IDs are joined only within each run.',
                  'Pre750..900 and post900..1050 are separate150s windows; no assertion of full pre900 equivalence.',
                  'Connector presence and head crossings are different quantities. Missing connector samples are not forced routes or completions.',
                  'Current route fractions use observed150s envelopes only, with explicit coverage/censoring; they are not realized OD invariance tests.']}
    from diagnostics.capture_native_runtime_errors import parse_bytes
    for source in ('diagnose_sc1004_first_control_window.py','probe_e8_lane_receiving.py','probe_e8_window_passages.py',
                   'selected_signal_sampling_audit.py','audit_observer_control_pair.py','capture_native_runtime_errors.py'):
        path=ROOT/'diagnostics'/source;pins[str(path)]=sha(path)
    for spec in specs:
        arm,network,run_dir=spec['arm'],spec['network'],spec['run']
        parsed=parse_bytes(spec['err'].read_bytes())
        if parsed['partial_tail_bytes'] or parsed['unparsed_removal_lines']:raise ValueError('Incomplete/unknown native removal evidence')
        result['runs'][arm]={'run':str(run_dir),'network_sha256':spec['network_sha256'],'windows':{},
            'native_warning_counts':parsed['counts'],'native_unparsed_lines':parsed['unparsed'],
            'unfinished_input_events':[e for e in parsed['events'] if e['kind']=='unfinished_vehicle_input'],
            'input_remainder_scope':'Reported at run end; these are ungenerated vehicles, not explicit removals of recorded vehicles.'}
        for start,end in WINDOWS:
            folder=output/arm/f'{start}_{end}'
            doc=collect_window(run_dir.name,network,folder,start,end)
            summary=summarize_window(doc,route_map,parsed['events'])
            pins.update(summary['route_observation']['source_sha256'])
            write(folder/'summary.json',summary)
            result['runs'][arm]['windows'][f'{start}_{end}']={'summary':str(folder/'summary.json'),
                'summary_sha256':sha(folder/'summary.json'),'stock71':summary['stock71'],
                'sg71_summary':summary['sg71_summary'],'endpoint_stopped':summary['endpoint_stopped'],
                'decision_summary':summary['decision_summary']}
        for path,expected in spec['native_stats'].items():
            stat=Path(path).stat()
            if [stat.st_size,stat.st_mtime_ns]!=expected:raise ValueError('Completed native output changed during analysis')
    result['source_changes']=[path for path,key in pins.items() if sha(path)!=key]
    if result['source_changes']:raise ValueError('Analysis inputs changed')
    write(output/'comparison.json',result)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--batch-manifest',type=Path,required=True)
    parser.add_argument('--route-mapping-validation',type=Path,default=ROUTE_VALIDATION)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    run(args.batch_manifest,args.output,args.route_mapping_validation)
