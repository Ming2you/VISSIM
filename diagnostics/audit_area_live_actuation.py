"""Read-only audit of an explicit area-controller action interval.

Example: python diagnostics/audit_area_live_actuation.py --run <run-name>
 --start 1050 --end 1200 --reference diagnostics/area_production_preflight/<dir>
No simulator attachment, solver execution, process control, or production writes.
"""
from __future__ import annotations
import argparse
from collections import Counter
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from diagnostics.live_beta0_first_interval_audit import trace_audit, area_snapshot
from diagnostics.run_area_production_preflight import validate_result
from evaluation.controllers.signal_timing_oracle import decisions_from_action_rows


def sha(data): return hashlib.sha256(data).hexdigest()
def load(path): return json.loads(path.read_text(encoding='utf-8-sig'))


def read_csv_prefix(path,end=float('inf')):
    """Freeze file size, read complete lines only, stop beyond the requested time.

    These runner logs have one CSV record per physical line. The fingerprint is
    of the consumed prefix, not a claim to hash an actively growing whole file.
    """
    size=path.stat().st_size
    pieces=[]
    with path.open('rb') as file:
        while file.tell()<size:
            line=file.readline()
            if not line.endswith(b'\n') or file.tell()>size: break
            pieces.append(line)
            if len(pieces)>1:
                try: sec=float(line.split(b',',1)[0])
                except ValueError: continue
                if sec>end: break
    data=b''.join(pieces)
    rows=list(csv.DictReader(io.StringIO(data.decode('utf-8-sig'))))
    return rows,{'path':str(path),'captured_file_bytes':size,'read_complete_prefix_bytes':len(data),
                 'read_complete_prefix_sha256':sha(data)}


def parse_commands(data,start):
    rows=list(csv.DictReader(io.StringIO(data.decode('utf-8-sig'))))
    decisions=decisions_from_action_rows([{**row,'sim_sec':start} for row in rows])
    if len(decisions)!=1: raise ValueError('Expected one complete action CSV')
    ramps={str(int(row['sc_no'])):float(row['green_sec']) for row in rows if row['kind']=='ramp_meter'}
    if len(ramps)!=sum(row['kind']=='ramp_meter' for row in rows): raise ValueError('Duplicate ramp commands')
    return rows,decisions[0]['controllers'],ramps


def vsl_signature(row):
    return tuple(str(row[key]) for key in ('id','dsd_no','link','lane'))+(float(row['speed_kph']),)


def audit_interval(run,start,end,reference=None,trace_data=None,action_log_data=None):
    if end-start!=150 or start<0: raise ValueError('Expected one150s control interval')
    decisions=run/('decisions_'+run.name)
    out={'schema':'area-live-actuation/v1','run':run.name,'interval_sec':[start,end],
         'status':'pending','failures':[],'sources':{},'performance_comparison':False}
    action_path=decisions/f'action_{int(start):06d}.json'
    csv_path=decisions/f'action_{int(start):06d}.csv'
    if not action_path.exists() or not csv_path.exists():
        log_path=run/('runlog_'+run.name+'.txt')
        lines=log_path.read_text(encoding='utf-8-sig',errors='replace').splitlines() if log_path.exists() else []
        errors=[line for line in lines if 'ERROR=' in line and
                re.search(r'\bsim_sec='+str(int(start))+r'(?:\s|$)',line)]
        if errors:
            out['status']='fail';out['interval_errors']=errors
            out['failures'].append('Action was not produced and the runner reported a decision error at interval start.')
        else: out['pending_reason']='Interval action JSON/CSV is not yet available.'
        return out
    try:
        action=load(action_path)
    except json.JSONDecodeError:
        out['pending_reason']='Action JSON is incomplete or not yet parseable; no successful decision claimed.'
        return out
    try:
        beta=float(action['metadata']['control_area_beta_seconds'])
        out['decision_validation']=validate_result(action,beta)
        out['scoring_alignment']={key:action['diagnostics'][key] for key in (
            'control_area_phase_outer_matches_scored','control_area_meter_finalized_before_score')}
        out['scoring_alignment']['control_area_meter_writer_matches_scored']=action['metadata']['control_area_meter_writer_matches_scored']
        data=csv_path.read_bytes()
        commands,controllers,ramps=parse_commands(data,start)
        out['sources'].update({'action_json_sha256':sha(action_path.read_bytes()),'action_csv_sha256':sha(data)})
        out['commands']={'counts':dict(Counter(row['kind'] for row in commands)),
            'nonzero_offsets':sum(abs(float(node['offset_sec']))>1e-9 for node in controllers.values()),
            'physical_meter_green_sec':ramps,'group_meter_vph':action['ramp_metering']}
        if reference:
            ref=reference/'action.csv' if reference.is_dir() else reference
            refdata=ref.read_bytes()
            out['reference']={'path':str(ref),'sha256':sha(refdata),'csv_byte_identical':data==refdata}
            manifest_path=ref.parent/'manifest.json'
            if manifest_path.exists():
                command=load(manifest_path).get('command',[])
                if '--state-json' in command:
                    prior=Path(command[command.index('--state-json')+1])
                    actual=decisions/f'state_{int(start):06d}.json'
                    if prior.exists() and actual.exists():
                        first,second=load(prior),load(actual)
                        keys=('total_vehicles','urban_vehicles','freeway_vehicles','ramp_vehicles',
                              'mean_speed_kph','freeway_mean_speed_kph','stopped_vehicles','demand',
                              'ramp_counts','local_observation','vehicle_records','freeway_segments')
                        out['reference']['snapshot_sections_equal']={key:first.get(key)==second.get(key) for key in keys}
        raw_path=decisions/f'state_{int(start):06d}.json'
        if raw_path.exists():
            membership_path=ROOT/'diagnostics/control_area_membership.json'
            inside=set(map(str,load(membership_path)['inside_links']))
            out['sources']['initial_state_sha256']=sha(raw_path.read_bytes())
            out['sources']['physical_membership_sha256']=sha(membership_path.read_bytes())
            out['initial_area']=area_snapshot(load(raw_path),inside)
            out['initial_area']['model_omega_vehicles']=action['metadata']['control_area_initial_inside_veh']
            if abs(out['initial_area']['omega_vehicles']-out['initial_area']['model_omega_vehicles'])>1e-7:
                raise AssertionError('Initial model and complete physical Omega stocks differ')
        trace_rows,trace_source=trace_data or read_csv_prefix(decisions/'signal_readback.csv',end)
        applied_rows,applied_source=action_log_data or read_csv_prefix(run/('action_'+run.name+'.csv'),end)
        out['sources'].update({'signal_trace':trace_source,'action_log':applied_source})
        trace=trace_audit(trace_rows,controllers,ramps,start=start,end=end)
        out['actuation_trace']=trace
        expected=[r for r in commands if r['kind']=='vsl']
        applied=[r for r in applied_rows if float(r['sim_sec'])==start and r['kind']=='vsl']
        bad=[r for r in applied if not r.get('readback') or any(abs(float(v)-float(r['speed_kph']))>1e-6 for v in r['readback'].split('|'))]
        match=Counter(vsl_signature(r) for r in applied)==Counter(vsl_signature(r) for r in expected)
        out['vsl']={'expected_writes':len(expected),'actual_writes':len(applied),'command_rows_match':match,
                    'readback_mismatches':len(bad),'speed_values_kph':sorted(set(float(r['speed_kph']) for r in applied)),
                    'measurement':'DSD attribute readback, not a hard vehicle-speed guarantee.'}
        log_path=run/('runlog_'+run.name+'.txt')
        log=log_path.read_text(encoding='utf-8-sig',errors='replace')
        errors=[line for line in log.splitlines() if any(s in line for s in
            ('ERROR=','STRICT_DECISION_FAILED','EXPERIMENT_DECISION_FAILED','fallback_fixed','SIGSTATE_POST_STEP_MISMATCH'))]
        def time_of(line):
            m=re.search(r'\bsim_sec=([0-9.]+)',line)
            return float(m.group(1)) if m else None
        out['interval_errors']=[line for line in errors if time_of(line) is None or start<=time_of(line)<end]
        out['next_decision_errors']=[line for line in errors if time_of(line)==end]
        if out['interval_errors']: out['failures'].append('Runner reported an error in this action interval.')
        if trace['command_mismatch_count'] or trace['persistence_mismatch_count'] or trace['malformed_count']:
            out['failures'].append('Observed signal/ramp readbacks fail the exact command/persistence contract.')
        if bad: out['failures'].append('VSL write/readback mismatch.')
        if trace['interval_complete'] and not match: out['failures'].append('VSL command rows do not match the action CSV.')
        if out['failures']: out['status']='fail'
        elif trace['interval_complete'] and match: out['status']='pass'
        else: out['pending_reason']='Complete end-of-interval post-step samples are not yet available for every commanded group.'
    except Exception as error:
        out['status']='fail';out['failures'].append(type(error).__name__+': '+str(error))
    return out


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--run',required=True)
    ap.add_argument('--start',type=int,default=1050)
    ap.add_argument('--end',type=int)
    ap.add_argument('--reference',type=Path)
    ap.add_argument('--all-completed',action='store_true',help='Audit all available actions from start, retaining a pending last interval.')
    ap.add_argument('--output',type=Path)
    args=ap.parse_args()
    run=(ROOT/'evaluation/runs'/args.run).resolve()
    if run.parent!=(ROOT/'evaluation/runs').resolve() or not run.is_dir(): ap.error('Run must be an existing direct child of evaluation/runs')
    end=args.end or args.start+150
    reference=(ROOT/args.reference).resolve() if args.reference else None
    if args.all_completed:
        dec=run/('decisions_'+run.name)
        trace=read_csv_prefix(dec/'signal_readback.csv')
        applied=read_csv_prefix(run/('action_'+run.name+'.csv'))
        starts=sorted(int(p.stem.split('_')[-1]) for p in dec.glob('action_*.json') if int(p.stem.split('_')[-1])>=args.start)
        results=[audit_interval(run,start,start+150,reference if start==args.start else None,trace,applied) for start in starts]
        if not results: results=[audit_interval(run,args.start,end,reference,trace,applied)]
    else: results=[audit_interval(run,args.start,end,reference)]
    output=args.output or ROOT/f'diagnostics/live_{run.name}_actuation_{args.start}_{end}.json'
    output=(ROOT/output).resolve()
    if (ROOT/'diagnostics').resolve() not in output.parents: ap.error('Audit output must stay under diagnostics')
    payload={'run':run.name,'status_counts':dict(Counter(r['status'] for r in results)),'intervals':results,
             'audit_script_sha256':sha(Path(__file__).read_bytes()),
             'trace_helper_sha256':sha((ROOT/'diagnostics/live_beta0_first_interval_audit.py').read_bytes())}
    output.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    lines=[f'Area actuation audit: {run.name}.','']
    for result in results:
        lines.append(f"Interval {result['interval_sec']}: {result['status']}.")
        if result.get('pending_reason'): lines.append(result['pending_reason'])
        if result.get('reference'): lines.append(f"Reference CSV byte-identical: {result['reference']['csv_byte_identical']}.")
        if result.get('actuation_trace'):
            t=result['actuation_trace']
            lines.append(f"Signal/ramp groups {t['expected_groups']}; command mismatches {t['command_mismatch_count']}, persistence mismatches {t['persistence_mismatch_count']}, incomplete groups {len(t['incomplete_groups'])}.")
        lines.extend(result['failures']);lines.append('')
    lines.append('This is sampled action/readback validation, not a completed-run or performance claim. Zero optimized offsets are a legitimate command, not an audit failure.')
    output.with_suffix('.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'run':run.name,'status_counts':payload['status_counts'],'output':str(output)},ensure_ascii=False))


if __name__=='__main__': main()
