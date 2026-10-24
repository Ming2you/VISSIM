"""Explicit post-run checker review; never launch or rewrite a failed receipt."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
from diagnostics import run_no_control_network_arms as n

d = n.d
OLD_CHECKERS = {
    'diagnostics/run_no_control_network_arms.py': 'cc54228b1af9e1ef2b5c47ad480c72ded04f7dd671c3141f0cb9c17618e3f946',
    'diagnostics/audit_nc5400_native_signals.py': '94d92b803031bcb2358b0c98a354bde0a608ea6794f66db3964e00ccb892f2a0',
}
ERROR = 'ValueError: Native signals differ from old NC'


def source_review_exceptions(historical, current, runtime):
    d.require(all(historical.get(p) == h and current.get(p) == h for p,h in runtime.items()),
              'Baseline runtime differs; checker review cannot waive runtime changes')
    exceptions=[]
    for p,h in historical.items():
        actual=current.get(p)
        d.require(isinstance(actual,str) and len(actual)==64, 'Historical source missing: '+p)
        if actual != h:
            d.require(OLD_CHECKERS.get(p) == h, 'Unapproved historical source change: '+p)
            exceptions.append({'path':p,'recorded_sha256':h,'reviewed_sha256':actual,
                               'reason':'Post-run used-INPX-SIG selector and explicit baseline review only; no simulation/runtime/input change'})
    d.require({r['path'] for r in exceptions} == set(OLD_CHECKERS), 'Expected exactly two reviewed checker revisions')
    return exceptions


def review(path, digest, output):
    d.require(not output.exists(), 'New review certificate required')
    pins, runtime, flat, refs, old = n.gates()
    d.pin(pins, path, digest); prior = d.load(path)
    d.require(prior.get('schema') == 'no-control-network-arms5400/v1'
              and prior.get('status') == 'failed_preserved_stop' and prior.get('error') == ERROR
              and prior.get('source_changes') == [] and prior.get('nc_config', {}).get('sha256') == n.TUNING_SHA,
              'This review only covers the known unused-SIG comparison error')
    row = deepcopy(prior['arms'][0]); run = d.workspace_path(row['run'])
    d.require(row['arm'] == 'baseline' and row.get('completed') is True and row.get('exit_code') == 0
              and row.get('natural_exit', {}).get('valid') is True and row.get('validation', {}).get('valid') is True
              and run.parent == d.ROOT/'evaluation/runs' and row['name'] == run.name
              and run.name == f'codex_nc5400_{path.parent.name}_baseline_s13'
              and row['command'] == n.arm_command(run.name, 'baseline', run), 'Actual completed baseline identity differs')
    historical = {d.relative(d.workspace_path(p)): h for p,h in prior['source_sha256'].items()}
    exceptions=source_review_exceptions(historical,{p:d.sha(d.ROOT/p) for p in historical},
        {d.relative(d.workspace_path(p)):h for p,h in runtime['source_sha256'].items()})
    checked=n.validate_run(run,'baseline',flat['outputs']['baseline.inpx']['destination_sha256'],refs,old,runtime)
    d.require(checked == row['validation'], 'Saved physical input/commands/readback certificate changed')
    native=n.native_signal_reference(run)
    trajectory=n.baseline_trajectory(run); d.require(trajectory['valid'], 'Full baseline trajectory differs')
    for record in native['records'] + [trajectory['actual'], trajectory['historical']]:
        pins[d.relative(d.workspace_path(record['path']))] = record['file_sha256']
    for proof in native['programs']: pins.update(proof['source_sha256'])
    for p in (Path(__file__), run/('run_provenance_'+run.name+'.json'), run/('runlog_'+run.name+'.txt'),
              run/('action_'+run.name+'.csv'), run/('state_'+run.name+'.csv'),
              run/('decisions_'+run.name)/'signal_readback.csv'):
        d.pin(pins,p)
    for sec in (1,900):
        for suffix in ('csv','json'): d.pin(pins,run/('decisions_'+run.name)/f'action_{sec:06d}.{suffix}')
    original_status={key:row.get(key) for key in ('status','valid')}
    row.update(status='passed',valid=True,validation=checked,native_signal_reference=native,trajectory=trajectory)
    d.assert_pins(pins)
    result={'schema':'reviewed-nc5400-baseline/v1','valid':True,'completed':True,'reviewed_utc':d.utc(),
            'original_manifest':{'path':d.relative(path),'sha256':digest},'original_row_status':original_status,
            'original_error':ERROR,'source_review_exceptions':exceptions,'runtime_family':prior['current_runtime_family'],
            'source_sha256':pins,'source_changes':[],'receipt':row,'simulator_rerun':False,
            'scope':'Separate reviewer certificate. Original failed manifest/lock/raw run are unchanged. Only two post-run checker files differ.'}
    output.parent.mkdir(parents=True,exist_ok=True); d.save(output,result)
    return result


def validated_receipt(path, digest, pins, runtime):
    d.pin(pins,path,digest); proof=d.load(path)
    d.require(proof.get('schema')=='reviewed-nc5400-baseline/v1' and proof.get('valid') is True
              and proof.get('completed') is True and proof.get('source_changes')==[] and proof.get('simulator_rerun') is False,
              'Explicit valid review certificate required')
    old_path=d.workspace_path(proof['original_manifest']['path'])
    d.pin(pins,old_path,proof['original_manifest']['sha256'])
    for row in proof['source_review_exceptions']:
        d.require(OLD_CHECKERS.get(row['path'])==row['recorded_sha256']
                  and d.sha(d.ROOT/row['path'])==row['reviewed_sha256'], 'Checker review changed')
    d.require({r['path'] for r in proof['source_review_exceptions']}==set(OLD_CHECKERS), 'Wrong review exceptions')
    for p,h in proof['source_sha256'].items():d.pin(pins,p,h)
    d.require(all(proof['source_sha256'].get(d.relative(d.workspace_path(p)))==h for p,h in runtime['source_sha256'].items()), 'Runtime review mismatch')
    receipt=deepcopy(proof['receipt']); run=d.workspace_path(receipt['run'])
    d.require(receipt['arm']=='baseline' and receipt['name']==run.name and receipt.get('status')=='passed'
              and receipt.get('valid') is True and receipt.get('completed') is True and receipt.get('exit_code')==0
              and receipt.get('natural_exit',{}).get('valid') is True and receipt.get('validation',{}).get('valid') is True
              and receipt['command']==n.arm_command(run.name,'baseline',run)
              and receipt['trajectory']['valid'] is True and receipt['native_signal_reference']['valid'] is True,
              'Reviewed baseline identity/payload proof differs')
    return {**receipt,'reused_from':d.relative(path),'reused_review_sha256':digest,
            'reused_original_manifest':proof['original_manifest'],'revalidated_utc':d.utc()}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',required=True);p.add_argument('--manifest-sha256',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();r=review(d.workspace_path(a.manifest),a.manifest_sha256,d.workspace_path(a.output))
    print(json.dumps({'valid':r['valid'],'receipt_run':r['receipt']['run'],'output':a.output,'sha256':d.sha(d.workspace_path(a.output))}))


if __name__=='__main__':main()
