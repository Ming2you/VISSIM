"""Small external-watchdog completion receipt; no COM, model or FZP payload reads."""
import argparse
import csv
import hashlib
import json
import sys
import time
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path): return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def audit(run,name,terminal,observation,checks):
    run=Path(run).resolve(strict=True); checks=Path(checks).resolve(strict=True)
    obs=read(observation); proof=read(checks); errors=[]
    record={'schema':'selected-control-completion/v1','name':name,'run_directory':str(run),
        'run_id':None,'exit_code':obs.get('watchdog_exit_code'),'cscript_exit_code':None,
        'exit_code_scope':'External canonical watchdog process; no child cscript exit inference',
        'owned_native_alive':obs.get('owned_native_alive'),'owned_native':obs.get('owned_native'),
        'wrapper_observation':{'path':str(Path(observation).resolve()),'sha256':sha(observation)},
        'preparation_checks':{'path':str(checks),'sha256':sha(checks)},'terminal_sec':None,
        'completed':False,'errors':errors,'error_files':[]}
    try:
        if run.name!=name: raise ValueError('Run name/directory differ')
        # The launcher saves this independent request beside checks.json before
        # starting the watchdog; do not infer the expected seed from its output.
        launch_path=checks.with_name('launch.json'); launch_bytes=launch_path.read_bytes()
        launch=json.loads(launch_bytes.decode('utf-8-sig'))
        if not isinstance(launch,dict) or launch.get('execute') is not True:
            raise ValueError('Executed launch request required')
        launch_args=launch['arguments']
        if not isinstance(launch_args,dict): raise ValueError('Launch arguments must be an object')
        expected_seed=launch_args['Seed']
        if type(expected_seed) is not int or expected_seed<1:
            raise ValueError('Launch seed must be a positive integer')
        launch_out=launch_args['OutDir']
        if (launch_args['Name']!=name or type(launch_args['SimPeriod']) is not int
                or launch_args['SimPeriod']!=terminal or not isinstance(launch_out,str)
                or not Path(launch_out).is_absolute() or Path(launch_out).resolve(strict=True)!=run):
            raise ValueError('Launch request identity/period differs')
        record['launch_request']={'path':str(launch_path),
            'sha256':hashlib.sha256(launch_bytes).hexdigest(),'expected_seed':expected_seed}
        if obs.get('watchdog_exit_code')!=0: errors.append('External watchdog exit is not zero')
        if not obs.get('owned_native') or obs.get('ownership_ambiguous') or obs.get('owned_native_alive') is not False:
            errors.append('Exact owned native process exit was not confirmed')
        for scope in ('source_sha256','generated_sha256'):
            for path,expected in proof[scope].items():
                if sha(path)!=expected: errors.append('Preparation input changed: '+path)
        p=run/('run_provenance_'+name+'.json'); provenance=read(p)
        record.update(run_id=provenance['run_id'],provenance_path=str(p),provenance_sha256=sha(p))
        if not provenance['run_id'] or provenance['name']!=name or provenance['sim_period_sec']!=terminal or type(provenance['seed']) is not int or provenance['seed']!=expected_seed:
            errors.append('Canonical provenance identity/period/seed differs')
        network_sha = proof.get('runtime_network_sha256',proof['network_sha256'])
        for field,expected in [('network',network_sha),('tuning',proof['generated_sha256'][proof['controller_tuning']]),('demand_profile',proof['profile_sha256'])]:
            item=provenance['files'][field]
            if item['sha256']!=expected or sha(item['path'])!=expected: errors.append('Canonical input differs: '+field)
        log=run/('runlog_'+name+'.txt'); record['runlog_path']=str(log)
        # WSH uses native CP949. Only deliberate ASCII status rows are parsed;
        # arbitrary path/log text is never replacement-decoded as evidence.
        lines=log.read_bytes().splitlines()
        if lines.count(b'STAGE=SIM_DONE')!=1 or lines.count(('SIM_SEC='+str(terminal)).encode('ascii'))!=1:
            errors.append('Canonical terminal status missing or duplicate')
        for key in ('DECISIONS_FAILED','OBSERVATION_FAILURES','SIGNAL_FAILURES','ACTION_FORMAT_FAILURES','COM_FAILURES'):
            matched=[row for row in lines if row.startswith((key+'=').encode('ascii'))]
            if matched!=[(key+'=0').encode('ascii')]: errors.append('Canonical failure counter: '+key)
        if any(row.startswith(b'ERROR') or b'STAGE=ERROR' in row for row in lines): errors.append('Canonical error log entry')
        state=run/('state_'+name+'.csv'); record['state_csv_path']=str(state)
        last=None
        with state.open(encoding='utf-8-sig',newline='') as f:
            for row in csv.DictReader(f): last=row
        if last is None or float(last['sim_sec'])!=terminal: errors.append('State terminal differs')
        else: record['terminal_sec']=terminal
        for path in sorted(run.glob('vissim_*.err')):
            record['error_files'].append({'name':path.name,'path':str(path),'bytes':path.stat().st_size,'sha256':sha(path)})
        if not any(row['name'].startswith('vissim_simulation_') for row in record['error_files']):
            errors.append('Archived numbered native ERR missing')
        record['native_files']=[{'path':str(p),'name':p.name,'bytes':p.stat().st_size}
            for extension in ('*.fzp','*.lsa','*.ldp') for p in sorted((run/'vissim_eval').glob(extension))]
        for extension in ('.fzp','.lsa'):
            if not any(Path(row['name']).suffix==extension and row['bytes']>0 for row in record['native_files']):
                errors.append('Native output missing: '+extension)
        if proof.get('native_signal_record'):
            from evaluation.controllers.network_provenance import snapshot_network_sha256
            physical_sha = snapshot_network_sha256({'network_path':provenance['files']['network']['path'],
                'run_provenance':{'manifest_path':str(p),'run_id':provenance['run_id']}})
            if physical_sha != proof['network_sha256']:
                errors.append('Recording copy physical source differs from selected network')
            from diagnostics.com_execution_equivalence.verify_pair import verify_native_execution
            validation_started = time.monotonic()
            execution = verify_native_execution(run,terminal)
            record['post_native_validation_wall_sec'] = time.monotonic()-validation_started
            record['native_execution_verification'] = execution
            record['native_lsa_com_coverage_passed'] = execution['native_lsa_com_coverage_passed']
            record['native_execution_passed'] = execution['native_execution_passed']
            record['native_verification_note'] = 'Completion uses actual LDP + immediate readbacks; the independent LSA verdict is not overridden.'
            if execution['native_execution_passed'] is not True:
                errors.append('Required actual native execution evidence failed')
    except (KeyError,ValueError,OSError,TypeError) as exc:
        errors.append(type(exc).__name__+': '+str(exc))
    record['completed']=not errors
    return record


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',type=Path,required=True);p.add_argument('--name',required=True)
    p.add_argument('--terminal',type=int,required=True);p.add_argument('--observation',type=Path,required=True)
    p.add_argument('--checks',type=Path,required=True);a=p.parse_args()
    result=audit(a.run,a.name,a.terminal,a.observation,a.checks)
    with (a.run/'completion_receipt.json').open('x',encoding='utf-8') as f: json.dump(result,f,indent=2)
    print(json.dumps({'completed':result['completed'],'errors':result['errors']}))
    raise SystemExit(0 if result['completed'] else 1)


if __name__=='__main__': main()
