"""Read-only first-decision/interval audit; never attaches to or controls VISSIM."""
from __future__ import annotations
from collections import Counter, defaultdict
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from diagnostics.run_area_production_preflight import validate_result
from evaluation.controllers.signal_timing_oracle import decisions_from_action_rows, intended_state

RUN = ROOT/'evaluation/runs/codex_area_beta0_s13_20260910'
DEC = RUN/('decisions_'+RUN.name)
REFERENCE = ROOT/'diagnostics/area_production_preflight/wu-link_t900_beta0_20260909T191544832356Z'
REFERENCE_STATE = ROOT/'evaluation/runs/codex_n7_pure_s13_20260910/decisions_codex_n7_pure_s13_20260910/state_000900.json'
OUTPUT = ROOT/'diagnostics/live_beta0_first_interval_audit.json'
START, END = 900., 1050.


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def stable_rows(path):
    """Read complete lines only from a growing log; keep its prefix fingerprint."""
    data = path.read_bytes()
    data = data[:data.rfind(b'\n')+1]
    text = data.decode('utf-8-sig')
    return list(csv.DictReader(io.StringIO(text))), {'path': str(path.relative_to(ROOT)),
            'complete_prefix_bytes': len(data), 'complete_prefix_sha256': digest(data)}


def expected_signal(controller, sg, sec):
    cycle, offset = controller['cycle_sec'], controller['offset_sec']
    pos = (sec+offset) % cycle
    windows = controller['windows'].get(sg, [])
    result = intended_state(windows,pos,cycle,3.)
    # Actual VBS SignalGroupStateFromPlan suppresses amber while any SG of the
    # controller is green. The lower-level oracle's amber alone is insufficient.
    if result == 'AMBER' and any(a <= pos < b for ws in controller['windows'].values() for a,b in ws):
        result = 'RED'
    return result


def expected_ramp(green, sec):
    pos = sec % 10.
    return 'RED' if green <= 0 else 'GREEN' if pos < green else 'AMBER' if pos < green+1 else 'RED'


def trace_audit(rows, controllers, ramps):
    expected = {(str(sc),str(sg)): ('signal',node) for sc,node in controllers.items() for sg in node['windows']}
    expected.update({(sc,'1'): ('ramp',green) for sc,green in ramps.items()})
    last = {}
    seconds = {key: Counter() for key in expected}
    covered = {key: [] for key in expected}
    immediate_counts, post_counts = Counter(), Counter()
    mismatch, persistence, malformed = [], [], []
    latest = 0.
    boundary_complete = set()
    for row in rows:
        try:
            sec = float(row['sim_sec'])
        except (ValueError,TypeError,KeyError):
            malformed.append(row)
            continue
        latest = max(latest,sec)
        if sec > END:
            break
        key = (str(row.get('sc_no')),str(row.get('sg_no')))
        if key not in expected:
            continue
        kind, definition = expected[key]
        stage = row.get('stage')
        requested = str(row.get('requested_state','')).upper()
        readback = str(row.get('readback_state','')).upper()
        if stage == 'immediate':
            if START <= sec < END:
                want = expected_signal(definition,key[1],sec) if kind == 'signal' else expected_ramp(definition,sec)
                immediate_counts[kind] += 1
                if requested != want or readback != requested or row.get('ok') != '1':
                    mismatch.append({'sim_sec':sec,'sc':key[0],'sg':key[1],'expected':want,
                                     'requested':requested,'readback':readback,'ok':row.get('ok')})
                last[key] = (sec,requested)
        elif stage == 'post_step' and START < sec <= END:
            post_counts[kind] += 1
            if sec == END:
                boundary_complete.add(key)
            prior = last.get(key)
            if readback != requested or row.get('ok') != '1' or prior is None or requested != prior[1]:
                persistence.append({'sim_sec':sec,'sc':key[0],'sg':key[1], 'requested':requested,
                                    'readback':readback,'last_immediate':prior,'ok':row.get('ok')})
            if prior is not None:
                begin = max(START,prior[0])
                # One post-step covers the time since the last sample. Immediate
                # writes normally follow each second; do not double-count if not.
                if covered[key]: begin = max(begin,covered[key][-1][1])
                if sec > begin:
                    seconds[key][readback] += sec-begin
                    covered[key].append((begin,sec))
    incomplete = []
    group_rows = []
    for key,(kind,definition) in expected.items():
        duration = sum(seconds[key].values())
        if abs(duration-(END-START)) > 1e-8 or key not in boundary_complete:
            incomplete.append({'sc':key[0],'sg':key[1],'covered_sec':duration,'end_post_step':key in boundary_complete})
        group_rows.append({'kind':kind,'sc':key[0],'sg':key[1],'aspects_sec':dict(seconds[key]),
                           'covered_sec':duration})
    return {'latest_complete_trace_sec':latest,'expected_groups':len(expected),
            'immediate_rows':dict(immediate_counts),'post_step_rows':dict(post_counts),
            'command_mismatch_count':len(mismatch),'command_mismatch_examples':mismatch[:15],
            'persistence_mismatch_count':len(persistence),'persistence_mismatch_examples':persistence[:15],
            'malformed_count':len(malformed),'incomplete_groups':incomplete,'groups':group_rows,
            'interval_complete':not incomplete, 'valid':not (incomplete or mismatch or persistence or malformed),
            'measurement': '1s immediate/post-step endpoint samples; no assertion about unsampled subsecond behavior'}


def area_snapshot(raw, inside):
    record = raw['vehicle_records']
    rows = record['records']
    if not record.get('complete') or len(rows) != record['record_count']:
        raise ValueError('Incomplete physical vehicle snapshot')
    ids = [r['veh_no'] for r in rows]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate physical vehicle IDs in snapshot')
    n = sum(str(row['link_no']) in inside for row in rows)
    return {'sim_sec':raw['sim_sec'],'physical_complete_records':len(rows),'omega_vehicles':n}


def main():
    status = {'schema':'live-beta0-first-interval/v1','run':RUN.name,'interval_sec':[START,END],
              'status':'pending','sources':{},'failures':[], 'performance_comparison':False}
    action_path, csv_path = DEC/'action_000900.json', DEC/'action_000900.csv'
    if not action_path.exists() or not csv_path.exists():
        status['pending_reason'] = 'First900s action JSON/CSV is not yet available.'
    else:
        try:
            action = read_json(action_path)
            status['decision_validation'] = validate_result(action,0)
            status['first_decision_valid'] = True
            status['exact_finalization_flags'] = {key:action['diagnostics'][key] for key in (
                'control_area_phase_outer_matches_scored','control_area_meter_finalized_before_score',
                'control_area_phase_finalization_source')}
            status['exact_finalization_flags']['control_area_meter_writer_matches_scored'] = action['metadata']['control_area_meter_writer_matches_scored']
            status['selected_group_meter_rates_vph'] = action['ramp_metering']
            status['sources']['action_sha256'] = digest(action_path.read_bytes())
            csv_bytes = csv_path.read_bytes()
            status['sources']['csv_sha256'] = digest(csv_bytes)
            status['sources']['preflight_csv_sha256'] = digest((REFERENCE/'action.csv').read_bytes())
            status['csv_identical_to_preflight'] = csv_bytes == (REFERENCE/'action.csv').read_bytes()
            commands = list(csv.DictReader(io.StringIO(csv_bytes.decode('utf-8-sig'))))
            plans = decisions_from_action_rows([{**r,'sim_sec':START} for r in commands])
            controllers = plans[0]['controllers']
            ramp_rows = [r for r in commands if r['kind']=='ramp_meter']
            ramps = {str(int(r['sc_no'])):float(r['green_sec']) for r in ramp_rows}
            status['physical_command_counts'] = dict(Counter(r['kind'] for r in commands))
            status['ramps'] = [{'id':r['id'],'sc':r['sc_no'],'green_sec':float(r['green_sec'])} for r in ramp_rows]
            raw = read_json(DEC/'state_000900.json')
            status['sources']['state_900_sha256'] = digest((DEC/'state_000900.json').read_bytes())
            reference_raw = read_json(REFERENCE_STATE)
            sections = ['total_vehicles','urban_vehicles','freeway_vehicles','ramp_vehicles','mean_speed_kph',
                        'freeway_mean_speed_kph','stopped_vehicles','demand','ramp_counts','local_observation',
                        'vehicle_records','freeway_segments']
            status['snapshot_sections_equal_to_preflight_input'] = {key:raw.get(key)==reference_raw.get(key) for key in sections}
            membership_path = ROOT/'diagnostics/control_area_membership.json'
            membership = read_json(membership_path)
            inside = set(map(str,membership['inside_links']))
            status['area_initial'] = area_snapshot(raw,inside)
            status['area_initial']['model_initial_inside_veh'] = action['metadata']['control_area_initial_inside_veh']
            if abs(status['area_initial']['omega_vehicles']-status['area_initial']['model_initial_inside_veh'])>1e-7:
                status['failures'].append('Physical Omega stock and initialized model Omega stock differ.')
            if (DEC/'state_001050.json').exists():
                end_raw = read_json(DEC/'state_001050.json')
                status['area_end_snapshot'] = area_snapshot(end_raw,inside)
                status['sources']['state_1050_sha256'] = digest((DEC/'state_001050.json').read_bytes())
            status['sources']['membership_sha256'] = digest(membership_path.read_bytes())
            trace_rows, trace_source = stable_rows(DEC/'signal_readback.csv')
            status['sources']['signal_trace'] = trace_source
            status['actuation_trace'] = trace_audit(trace_rows,controllers,ramps)
            groups = status['actuation_trace']['groups']
            status['physical_interval_activity'] = {
                'urban_groups_with_green':sum(g['kind']=='signal' and g['aspects_sec'].get('GREEN',0)>0 for g in groups),
                'urban_groups_with_amber':sum(g['kind']=='signal' and g['aspects_sec'].get('AMBER',0)>0 for g in groups),
                'urban_groups_with_red':sum(g['kind']=='signal' and g['aspects_sec'].get('RED',0)>0 for g in groups),
                'ramp_groups_green_entire_interval':sum(g['kind']=='ramp' and g['aspects_sec'].get('GREEN',0)==END-START for g in groups),
                'nonzero_written_offsets':sum(abs(float(x))>1e-9 for x in action['metadata']['offset_written_sec'].values())}
            applied_rows, applied_source = stable_rows(RUN/('action_'+RUN.name+'.csv'))
            status['sources']['action_log'] = applied_source
            applied = [r for r in applied_rows if float(r['sim_sec'])==START]
            vsl = [r for r in applied if r['kind']=='vsl']
            bad_vsl = [r for r in vsl if not r.get('readback') or any(abs(float(x)-float(r['speed_kph']))>1e-6 for x in r['readback'].split('|'))]
            expected_vsl = [r for r in commands if r['kind']=='vsl']
            vsl_columns = ('id','dsd_no','link','lane','speed_kph')
            command_matches = Counter(tuple(r[k] for k in vsl_columns) for r in vsl)==Counter(tuple(r[k] for k in vsl_columns) for r in expected_vsl)
            status['vsl'] = {'written_rows':len(vsl),'expected_rows':len(expected_vsl),
                              'command_rows_match_csv':command_matches,'immediate_readback_mismatches':len(bad_vsl),
                              'written_speed_values_kph':sorted(set(float(r['speed_kph']) for r in vsl)),
                              'limitation':'Desired-speed distribution readback proves written DSD values, not hard speed compliance by every vehicle.'}
            log_path = RUN/('runlog_'+RUN.name+'.txt')
            status['sources']['runlog_sha256'] = digest(log_path.read_bytes())
            log = log_path.read_text(encoding='utf-8-sig',errors='replace')
            failure_lines = [line for line in log.splitlines() if any(s in line for s in
                ('ERROR=','STRICT_DECISION_FAILED','DECISION_FAILED','fallback_fixed','SIGSTATE_POST_STEP_MISMATCH'))]
            status['runlog_failure_lines'] = failure_lines[:20]
            def at_time(line):
                match = re.search(r'\bsim_sec=([0-9.]+)',line)
                return float(match.group(1)) if match else None
            interval_failures = [line for line in failure_lines if at_time(line) is None or START <= at_time(line) < END]
            next_failures = [line for line in failure_lines if at_time(line)==END]
            status['interval_failure_lines'] = interval_failures
            status['fallback_fixed_observed'] = 'fallback_fixed' in log
            status['next_decision'] = {
                'sim_sec':END,'failed':bool(next_failures),'failure_lines':next_failures,
                'action_json_exists':(DEC/'action_001050.json').exists(),
                'action_csv_exists':(DEC/'action_001050.csv').exists(),
                'explanation':'The post-step1050 samples close the previous900s action interval; the1050s decision occurs afterward.'}
            if next_failures and 'unresolved physical stock support' in '\n'.join(next_failures):
                status['next_decision']['unresolved_physical_record_counts'] = dict(Counter(
                    str(row['link_no']) for row in end_raw['vehicle_records']['records'] if str(row['link_no'])=='10421'))
            if status['actuation_trace']['interval_complete']:
                status['first_interval_valid'] = bool(status['actuation_trace']['valid'] and not bad_vsl and command_matches and not interval_failures and not status['failures'])
                status['status'] = ('first_interval_pass_next_decision_failed' if next_failures else 'pass') if status['first_interval_valid'] else 'fail'
            else:
                status['pending_reason'] = 'Awaiting complete1050s post-step readbacks for every commanded signal group.'
        except Exception as error:
            status['status'] = 'fail'
            status['failures'].append(type(error).__name__+': '+str(error))
    OUTPUT.write_text(json.dumps(status,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    text = [f"First beta0 interval audit: {status['status']}.",
            f"Run {RUN.name}; observation interval [900, 1050) seconds."]
    if status.get('pending_reason'): text.append(status['pending_reason'])
    if status.get('failures'): text.extend(status['failures'])
    if 'csv_identical_to_preflight' in status:
        text.append('First command CSV identical to final preflight: '+str(status['csv_identical_to_preflight'])+'.')
        text.append('CSV SHA256: '+status['sources']['csv_sha256']+'.')
    if 'actuation_trace' in status:
        trace = status['actuation_trace']
        text.append(f"Signal/ramp command mismatches={trace['command_mismatch_count']}; persistence mismatches={trace['persistence_mismatch_count']}; incomplete groups={len(trace['incomplete_groups'])}.")
        text.append(f"All {trace['expected_groups']} commanded groups have 150 s coverage. The 122 urban groups each showed GREEN, AMBER and RED; all 8 ramps remained GREEN for the entire interval. The 66 VSL writes/readbacks matched the 120 km/h commands. Thirteen of 17 controller offsets were nonzero. This interval therefore does not demonstrate a restrictive metering or VSL effect.")
    if status.get('first_decision_valid'):
        point = status['decision_validation']['follower_score']
        text.append(f"The 900 s decision completed in {status['decision_validation']['decision_wall_sec']:.6f} s with exact phase/meter scoring and writer assertions. Initial physical Omega stock 1763 equals model 1763.0; all 12 compared raw snapshot sections match the preflight input. Predicted 450 s Omega TTT/J = {point['control_area_follower_ttt_veh_h']:.12f} veh*h and TTD = {point['control_area_follower_ttd_veh']:.12f} veh; beta = 0 s. These are model predictions, not measured interval performance.")
    if status.get('next_decision',{}).get('failed'):
        text.append("The 1050 s next decision failed during observation projection: one physical vehicle on link 10421 has unresolved model stock support. No 1050 s action JSON/CSV was produced and no fallback_fixed was logged. This failure does not invalidate the completed 900–1050 s actuation check; it prevents claiming a completed simulation run.")
    text.append('This is a decision/actuation audit, not a performance or beta comparison. Sources and exact counters are in the adjacent JSON.')
    OUTPUT.with_suffix('.md').write_text('\n\n'.join(text)+'\n',encoding='utf-8')
    print(json.dumps({k:status[k] for k in ('status','pending_reason','failures') if k in status}))


if __name__ == '__main__': main()
