"""Completed ON/OFF NC evidence only: no FZP, adapter, optimizer or simulator."""
import argparse
from collections import defaultdict
import csv
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from diagnostics.verify_signal_observation_pair import check


def sha(blob):return hashlib.sha256(blob).hexdigest()
def json_hash(value):return sha(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode())
def load(path):return json.loads(path.read_text(encoding='utf-8-sig'))


def native_signal_prefix(path,end):
    digest=hashlib.sha256();count=read=0;groups=defaultdict(list)
    before=path.stat()
    with path.open('rb') as stream:
        for line in stream:
            read+=len(line);parts=line.decode('cp949',errors='replace').strip().split(';')
            if len(parts)<5:continue
            try:t=float(parts[0]);sc=int(parts[2]);sg=int(parts[3])
            except ValueError:continue
            if t>end:break
            digest.update(line);count+=1
            groups[f'{sc}:{sg}'].append([t,parts[4].strip().upper()])
    after=path.stat()
    if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):
        raise ValueError('Native signal file changed during read')
    return {'path':str(path),'bytes_read':read,'raw_event_rows':count,
            'raw_event_sha256':digest.hexdigest(),'groups':dict(groups)}


def command_rows(path,end):
    groups=defaultdict(list)
    with path.open(encoding='utf-8-sig',newline='') as stream:
        for row in csv.DictReader(stream):
            t=float(row['sim_sec'])
            if t<=end:
                groups[t].append({k:v for k,v in row.items() if k not in ('sim_sec','metadata')})
    return {str(t):sorted(rows,key=lambda row:json.dumps(row,sort_keys=True)) for t,rows in groups.items()}


def source_rows(manifest):
    return {str(Path(row['path']).resolve()):row['sha256']
            for row in [*manifest['files'].values(),*manifest['signal_programs'],
                        *manifest.get('controller_sources',[])] if row.get('exists',True)}


def audit(on_name,off_name):
    runpaths=[ROOT/'evaluation/runs'/name for name in (on_name,off_name)]
    manifests=[];logs=[]
    for run in runpaths:
        log=(run/f'runlog_{run.name}.txt').read_bytes()
        if b'STAGE=SIM_DONE' not in log:raise ValueError('Both runs must be complete')
        logs.append(log);manifests.append(load(run/f'run_provenance_{run.name}.json'))
    on,off=manifests
    common=('seed','sim_period_sec','control_interval_sec','state_log_interval_sec','demand_scale','controller')
    if any(on[k]!=off[k] for k in common) or on['controller']!='no-control':
        raise ValueError('NC pair simulation arguments differ')
    if (off['env'].get('RW_SIGNAL_OBSERVATION')!='0'
            or b'RUN_MODE=STEPWISE controller=no-control' not in logs[1]):
        raise ValueError('OFF run did not record stepwise execution and disabled collector')
    if 'RW_FORCE_STEPWISE' in off['env'] and off['env']['RW_FORCE_STEPWISE']!='1':
        raise ValueError('Contradictory recorded ForceStepwise transport')
    if on['env'].get('RW_SIGNAL_OBSERVATION')!='1':raise ValueError('ON collector is not recorded')
    configs=[]
    for m in manifests:
        source=m['files']['tuning'];blob=Path(source['path']).read_bytes()
        if sha(blob)!=source['sha256']:raise ValueError('Recorded pair config changed')
        configs.append(json.loads(blob.decode('utf-8-sig')))
    differences=check(*[configs[0],{'urban':{'capacity':{'head_observation':{'enabled':False}}}},configs[1]])
    physical_sources=('network','main_vbs_runner','watchdog_wrapper','generated_vbs_config',
                      'control_mapping','vehicle_input_roles','demand_profile','urban_input_gate_map')
    unequal=[key for key in physical_sources if on['files'][key]['sha256']!=off['files'][key]['sha256']]
    if unequal:raise ValueError('Physical run source mismatch: '+repr(unequal))
    rows=[];end=on['sim_period_sec']
    expected=[1,*range(on['control_interval_sec'],end+1,on['control_interval_sec'])]
    for second in expected:
        paths=[run/f'decisions_{run.name}'/f'state_{second:06d}.json' for run in runpaths]
        a,b=map(load,paths)
        if 'signal_observation_window' not in a['local_observation'] or 'signal_observation_window' in b['local_observation']:
            raise ValueError('Actual head ON/OFF window presence differs from intended contrast')
        top_keys=(a.keys()|b.keys())-{'run_provenance','local_observation'}
        local_keys=(a['local_observation'].keys()|b['local_observation'].keys())-{'signal_observation_window'}
        top_diff=[k for k in sorted(top_keys) if a.get(k)!=b.get(k)]
        local_diff=[k for k in sorted(local_keys) if a['local_observation'].get(k)!=b['local_observation'].get(k)]
        rows.append({'sim_sec':second,'source_sha256':[sha(p.read_bytes()) for p in paths],
                     'top_level_changed_fields':top_diff,'legacy_local_changed_fields':local_diff,
                     'on_window':[a['local_observation']['signal_observation_window'][k] for k in ('start_sec','end_sec')],
                     'off_has_head_window':False,
                     'queue_window_samples':[x['local_observation']['queue_window_samples'] for x in (a,b)],
                     'vehicle_record_canonical_sha256':[json_hash(x['vehicle_records']) for x in (a,b)],
                     'route_record_canonical_sha256':[json_hash(x['vehicle_routes']) for x in (a,b)]})
    commands=[command_rows(run/f'action_{run.name}.csv',end) for run in runpaths]
    required_times={str(float(t)) for t in expected}
    if any(set(group)!=required_times for group in commands):
        raise ValueError('Forced-stepwise applied-action timestamps missing or duplicated')
    command_diffs=[t for t in sorted(required_times,key=float) if commands[0][t]!=commands[1][t]]
    native=[native_signal_prefix(next(run.glob('vissim_eval/*.lsa')),end) for run in runpaths]
    native_diffs=[k for k in sorted(native[0]['groups'].keys()|native[1]['groups'].keys())
                  if native[0]['groups'].get(k)!=native[1]['groups'].get(k)]
    sources=[source_rows(m) for m in manifests]
    source_diffs={k:{'on':sources[0][k],'off':sources[1][k]}
                  for k in sources[0].keys()&sources[1].keys() if sources[0][k]!=sources[1][k]}
    return {'schema':'observer-control-pair/v1','status':'complete','on_run':on_name,'off_run':off_name,
            'run_ids':[m['run_id'] for m in manifests],'config_differences':differences,
            'force_stepwise_basis':{'actual_run_mode':'STEPWISE controller=no-control',
                'env_value_in_manifest':off['env'].get('RW_FORCE_STEPWISE'),
                'limit':'The wrapper manifest omits this transport key; actual run-mode log and the pinned launcher/watchdog branch provide execution evidence.'},
            'physical_source_equality':True,'common_source_hash_differences':source_diffs,
            'snapshot_comparisons':rows,'applied_command_different_times':command_diffs,
            'applied_command_rows_per_time':[{k:len(v) for k,v in x.items()} for x in commands],
            'native_signal_different_groups':native_diffs,
            'native_signal_prefix':[{k:v for k,v in x.items() if k!='groups'} for x in native],
            'run_log_sha256':[sha(x) for x in logs],
            'producer_sha256':sha(Path(__file__).read_bytes()),
            'limits':['No FZP is read by this audit. Use --trajectory-only in audit_signal_observation_smoke.py separately.',
                      'Same physical sources/config leaves do not erase recorded model source changes. Physical commands, snapshots and native signal events are compared explicitly.',
                      'Whole raw JSON bytes differ by run provenance. Physical and legacy observation fields are compared exactly; only run provenance and intentional head-window presence are excluded.']}


def main():
    p=argparse.ArgumentParser();p.add_argument('--on-run',required=True);p.add_argument('--off-run',required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args();out=a.output.resolve()
    if not out.is_relative_to(ROOT/'diagnostics') or out.exists():raise ValueError('New diagnostic output required')
    result=audit(a.on_run,a.off_run)
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'output':str(out),'status':result['status'],
                      'commands_equal':not result['applied_command_different_times'],
                      'native_signals_equal':not result['native_signal_different_groups']}))


if __name__=='__main__':main()
