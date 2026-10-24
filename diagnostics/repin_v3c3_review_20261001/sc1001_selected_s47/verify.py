"""Verify existing artifacts and original resource caps without new forecasts."""
import ast
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
I=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'

def read(p):return json.loads(p.read_text(encoding='utf8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    assert not (HERE/'verification.json').exists()
    a=read(HERE/'assessment.json');p=read(HERE/'protocol.json')
    for name,h in a['source_pins'].items():assert sha(Path(name))==h,name
    wrapper=HERE.parent/'sc1001_connection/check_connection.py'
    for name,h in p['pins'].items():
        path=HERE/'wrapper_before.py.txt' if Path(name).resolve()==wrapper.resolve() else Path(name)
        assert sha(path)==h,name
    assert wrapper.read_bytes()==(HERE/'wrapper_executed.py.txt').read_bytes()
    for path in (wrapper,HERE/'assess.py',Path(__file__)):ast.parse(path.read_text(encoding='utf8'))
    assert a['forecasts']==2 and a['held_parity_exact'] and a['commands_exact']
    assert a['resource_max_exceedance']<1e-7 and not a['changed_production_functions']
    old_resources=I/'expanded036_9000_20260930/loss_onset2250/source_sc101/residual_timing/execution_quantities.json'
    original=read(old_resources)
    caps={k:original[0]['resource'][k]['target'] for k in ('np','nuf')}
    assert all(all(z['resource'][k]['target']==caps[k] for k in caps) for z in original)
    resources={}
    for arm,q in a['quantities'].items():
        np=sum(z['net_inflow_veh'] for z in q['owners'].values())
        nuf=q['predicted_ramp_merge']['total_rate_veh_h']
        assert len(q['owners'])==17 and len(q['predicted_ramp_merge']['accepted_vehicles_by_ramp'])==8
        resources[arm]=dict(np_veh=np,np_cap_veh=caps['np'],nuf_veh_h=nuf,nuf_cap_veh_h=caps['nuf'],
            passes_original_caps=np<=caps['np']+1e-7 and nuf<=caps['nuf']+1e-7)
    x=a['selected_minus_hold'];e=a['absolute_delta_error']
    assert x['native']['omega']<0 and x['after']['omega']<x['before']['omega']<0
    assert e['after']['omega']>e['before']['omega']
    assert x['native']['terminal']==-44 and x['after']['terminal']>0
    assert x['native']['omega_plus_tracked_outside']>0 and x['after']['omega_plus_tracked_outside']<0
    report=dict(status='VERIFIED_PAIR_GAIN_OVERESTIMATE_PERSISTS_NO_ADOPTION',forecasts=2,compute_sec=a['compute_sec'],
        resources_at_original_caps=resources,original_caps_sha256=sha(old_resources),
        resource_exceedance_max=a['resource_max_exceedance'],model_gain_qualified=False,
        new_native=0,fzp_reads=0,optimizer=0,fit=0,push=0,production_changed=False,
        completed_session=87327,goal='ACTIVE / NOT_QUALIFIED',
        limitations=['Original caps check only; no new PFO or optimizer selection.',
                     'Native execution and common prefix receipts are reused, not re-scanned.',
                     'This was a joint city/RM command. VSL remains110; no standaloneVSL conclusion.'],
        pins=a['source_pins'],artifacts={x.name:sha(x) for x in HERE.iterdir() if x.is_file()})
    (HERE/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('pins','artifacts')},ensure_ascii=False))

if __name__=='__main__':main()
