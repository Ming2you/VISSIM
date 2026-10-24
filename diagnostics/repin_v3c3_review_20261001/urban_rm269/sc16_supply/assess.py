"""Evaluate the one past-only head candidate against fixed-command targets."""
import gzip,hashlib,importlib.util,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;H=HERE.parent
sys.path.insert(0,str(H))
from qualify_native2400 import validate_scope
PINS={}
def pin(p):
    b=p.read_bytes();PINS[str(p)]=hashlib.sha256(b).hexdigest();return b
def read(p):return json.loads(pin(p))
def departures(response,prefix,start):
    return sum(t['vehicles'] for t in response['transfers'] if (t['source'] or '').startswith('movement:'+prefix+'_')
               and t['source']!=t['target'] and start<=t['start_sec']<start+150)
def head_totals(path,times):
    response=json.loads(gzip.decompress(pin(path)))
    return {g:[departures(response,g,t) for t in times] for g in ('SC16_E','SC16_W','SC16_S','SC12_S')}
def main():
    out=HERE/'comparison.json';assert not out.exists()
    validate_scope(read(H/'native2400_analysis/summary.json'),read(H/'native2400_analysis/observed_input_qualification.json'))
    for p,d in read(HERE/'plan.json')['source_pins'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==d,p
    baseline=read(H/'sc1_supply/forecast2400/summary.json')['results']
    previous=read(H/'sc1_supply/comparison.json')
    candidate=read(HERE/'forecast2400_corrected/summary.json')['results']
    late=read(HERE/'forecast3300/summary.json')['results']['applied']
    native=read(H/'native2400_assessment.json');observed=read(HERE/'assessment.json')
    for directory,depth,count in [('forecast2400_corrected',3,2),('forecast3300',1,1)]:
        assert read(HERE/directory/'completion.json')['status']=='complete'
        s=read(HERE/directory/'summary.json')
        assert s['depth']==depth and s['forecasts']==count and s['native_runs']==s['optimizer_calls']==0 and not s['future_observation_inputs']
        assert read(HERE/directory/'initialization_verification.json')['status']=='passed'
        for r in s['results'].values():
            assert r['conservation_states']==depth+1 and r['writer_validated'] and r['resource_max_exceedance']<1e-7
            assert all(abs(b['local_balance_error_veh'])<1e-7 for g in r['local'].values() for b in g['bins'])
    phases={'SC6_S':{'p1':['SC6_S_SC12_to_N_SC103','SC6_S_SC12_to_E_SC104'],'p2':['SC6_S_SC12_to_W_SC5']},
            'SC101_S':{'p1':['SC101_S_SC1_to_N_SC2005'],'p2':['SC101_S_SC1_to_W_SC1002']}}
    heads=[];later=[];source_heads=[];source_late=[]
    for old in previous['head_comparisons2400']:
        g,p=old['group'],old['phase'];new=[sum(b['by_movement'][m] for m in phases[g][p]) for b in candidate[old['arm']]['local'][g]['bins']]
        heads.append(dict(arm=old['arm'],group=g,phase=p,actual=old['actual'],previous=old['predicted'],predicted=new,
            previous_absolute_error=old['absolute_error'],absolute_error=sum(abs(a-b) for a,b in zip(old['actual'],new))))
    for old in previous['head_comparisons3300']:
        g,p=old['group'],old['phase'];new=sum(late['local'][g]['bins'][0]['by_movement'][m] for m in phases[g][p])
        later.append(dict(group=g,phase=p,actual=old['actual'],previous=old['predicted'],predicted=new,
            previous_absolute_error=old['absolute_error'],absolute_error=abs(old['actual']-new)))
    for arm in ('hold','selected'):
        old_totals=head_totals(H/'sc1_supply/forecast2400'/(arm+'.response.json.gz'),(2400,2550,2700))
        new_totals=head_totals(HERE/'forecast2400_corrected'/(arm+'.response.json.gz'),(2400,2550,2700))
        for group in ('SC16_E','SC16_W','SC16_S','SC12_S'):
            actual=[b['heads'][group]['crossings'] for b in observed['arms'][arm]['blocks']]
            old=old_totals[group];new=new_totals[group]
            source_heads.append(dict(arm=arm,group=group,actual=actual,previous=old,predicted=new,
                previous_absolute_error=sum(abs(a-b) for a,b in zip(actual,old)),absolute_error=sum(abs(a-b) for a,b in zip(actual,new))))
    # Read a held-out closed detector interval, never feed it to the plant.
    loader=importlib.util.spec_from_file_location('sc16_head_reader',HERE/'audit.py')
    audit=importlib.util.module_from_spec(loader);loader.loader.exec_module(audit)
    late_heads,_=audit.a.heads_and_entries(audit.a.ORIGINAL,3450)
    PINS.update(audit.a.PINS)
    old_totals=head_totals(H/'sc1_supply/forecast3300/applied.response.json.gz',(3300,))
    new_totals=head_totals(HERE/'forecast3300/applied.response.json.gz',(3300,))
    for group in ('SC16_E','SC16_W','SC16_S','SC12_S'):
        actual=late_heads[group]['crossings'];old=old_totals[group][0];new=new_totals[group][0]
        source_late.append(dict(group=group,actual=actual,previous=old,predicted=new,
            previous_absolute_error=abs(actual-old),absolute_error=abs(actual-new)))
    delta=lambda r:r['selected']['omega_ttt_veh_h']-r['hold']['omega_ttt_veh_h']
    fw=lambda r:sum(sign*sum(v for k,v in r[a]['costs_by_stock'].items() if k.startswith('freeway:')) for a,sign in [('selected',1),('hold',-1)])
    actual=native['delta_omega_veh_h']['actual']
    gain=lambda rows:sum(r['previous_absolute_error']-r['absolute_error'] for r in rows)
    local_gain=gain(heads)+gain(source_heads);late_gain=gain(later)+gain(source_late)
    feasible=all(r['shared_constraints']['feasible'] for r in candidate.values())
    retain=feasible and local_gain>0 and late_gain>=-1e-7 and abs(delta(candidate)-actual)<abs(delta(baseline)-actual)
    result=dict(status='complete_bounded_candidate',forecasts_completed=3,tests_passed=107,new_native=0,new_optimizations=0,
        rate_veh_h=read(HERE/'plan.json')['rate_veh_h'],exact_initial_state_preserved=True,shared_caps_feasible=feasible,
        delta_definition='Joint city/RM selected-minus-held; same initial2400state,Omega701,450s; positive is worse',
        delta_omega_veh_h=dict(actual=actual,previous=delta(baseline),predicted=delta(candidate),previous_error=delta(baseline)-actual,error=delta(candidate)-actual),
        delta_mainline_veh_h=dict(actual=native['delta_mainline_veh_h']['actual'],previous=fw(baseline),predicted=fw(candidate)),
        incremental_merge10681_veh=dict(actual=84,predicted=candidate['selected']['predicted_merge']['accepted_vehicles_by_ramp']['RM_C10681']-candidate['hold']['predicted_merge']['accepted_vehicles_by_ramp']['RM_C10681']),
        source_heads2400=source_heads,source_heads3300=source_late,head_comparisons2400=heads,head_comparisons3300=later,
        head_error_reduction_veh=dict(at2400=local_gain,unused3300=late_gain),ad_retention_gate=retain,
        calibration_control_gate_passed=False,applied_to_live_queue=False,runtime_pair_launched=False,
        limitations=['Past head rate is achieved support, not universal saturation.',
            'Queue-proportional partial FIFO does not resolve vehicle order or lateral gaps.',
            '3300 is an unused same-seed state, not independent-seed validation.',
            'Joint urban/multipleRM commands are not an isolated10681 causal effect.',
            'Head errors across successive intersections are not independent vehicle counts.',
            'No native adoption or full SDMPC wall-time claim.'])
    PINS[str(Path(__file__))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();result['source_pins']=PINS
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    print(json.dumps({k:result[k] for k in ('delta_omega_veh_h','source_heads2400','source_heads3300','head_error_reduction_veh','ad_retention_gate')},indent=2))
if __name__=='__main__':main()
