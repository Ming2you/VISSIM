"""Compare the single lateral-access candidate with untouched fixed-command data."""
import ctypes,gzip,hashlib,json,sys
from collections import Counter
from pathlib import Path
HERE=Path(__file__).resolve().parent;H=HERE.parent;ROOT=HERE.parents[3]
sys.path[:0]=[str(ROOT),str(H)]
from qualify_native2400 import validate_scope
from evaluation.controllers import obs150_contract as oc
from evaluation.controllers.obs150_observation import check_rule_crosscheck
PINS={}
def read(p,compressed=False):
    b=p.read_bytes();PINS[str(p)]=hashlib.sha256(b).hexdigest();return json.loads(gzip.decompress(b) if compressed else b)

def predicted(path,start,depth):
    r=read(path,True);out=[]
    for j in range(depth):
        lo=start+150*j;hi=lo+150
        arrivals=sum(t['vehicles'] for t in r['transfers'] if lo<=t['start_sec']<hi and t['source']=='storage:SC1004_W_out' and t['target']=='ramp:RM_C10681')
        urban=[x for x in r['residence'] if x['stage']=='urban' and x['end_sec']==hi]
        assert len(urban)==1
        out.append(dict(start_sec=lo,arrival10681=arrivals,final_W_out=urban[0]['model_stock_veh']['storage:SC1004_W_out']))
    return out

def late_native():
    folder=Path('D:/VISSIM_runs/20261007_goal8_prevention_s29_8100/sdmpc/decisions_sdmpc31_sdmpc8100_s29')
    raw=read(folder/'state_003450.json');bundle=oc.load_bundle(raw);obs=bundle.obs
    ds,_=oc.read_detector_csv(obs['detector_config']['path'],obs['detector_config']['sha256'])
    oc.validate_raw(obs,ds,expected_simres=10);check_rule_crosscheck(obs,ds)
    values=oc.evaluate_boundaries(obs,ds,bundle.frame_end,bundle.frame_start,bundle.err_rows)
    for p in (Path(obs['detector_config']['path']),folder/obs['mer']['chunk'],folder/obs['err']['chunk'],
              folder/obs['frames']['current']['path'],folder/obs['frames']['previous']['path']):
        PINS[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
    domain={68,121,10772,10625,10629,10633}
    return dict(start_sec=3300,arrival10681=values['ramp_arrival:RM_C10681'].cross,
        final_W_out=sum(v[1] in domain for v in bundle.frame_end['vehicles']))

def main():
    out=HERE/'comparison.json';assert not out.exists()
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(),0x4000)
    validate_scope(read(H/'native2400_analysis/summary.json'),read(H/'native2400_analysis/observed_input_qualification.json'))
    for p,d in read(HERE/'plan.json')['source_pins'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==d,p
    results={};checks=[]
    for at,count,depth in ((2400,2,3),(3300,1,1)):
        folder=HERE/f'forecast{at}';summary=read(folder/'summary.json')
        assert read(folder/'completion.json')['status']=='complete'
        assert summary['forecasts']==count and summary['depth']==depth and summary['native_runs']==summary['optimizer_calls']==0
        assert not summary['future_observation_inputs']
        before=read(H/f'sc1_supply/forecast{at}/state.json');after=read(folder/'state.json')
        assert before==after,'Candidate must preserve the complete observed initial state'
        for label,r in summary['results'].items():
            assert r['conservation_states']==depth+1 and r['writer_validated'] and r['resource_max_exceedance']<=1e-7
            assert all(abs(b['local_balance_error_veh'])<1e-7 for g in r['local'].values() for b in g['bins'])
            for cs in r['known_endpoint_cohorts']:
                for c in cs:
                    if c['vehicles']>1e-8 and 'lane68' in c:assert abs(sum(c['lane68']['shares'].values())-1)<1e-7
        results[at]=summary['results'];checks.append(dict(at=at,exact_complete_initial_state=True,forecasts=count))
    observed=read(H/'wout_response/assessment_integer_ids.json')['arms'];rows=[]
    for arm in ('hold','selected'):
        old=predicted(H/f'sc1_supply/forecast2400/{arm}.response.json.gz',2400,3)
        new=predicted(HERE/f'forecast2400/{arm}.response.json.gz',2400,3)
        for i in range(3):
            native=observed[arm][i]['native']
            rows.append(dict(arm=arm,start_sec=old[i]['start_sec'],
                arrival10681=dict(actual=native['ramps']['RM_C10681'],previous=old[i]['arrival10681'],predicted=new[i]['arrival10681']),
                final_W_out=dict(actual=native['final']['total'],previous=old[i]['final_W_out'],predicted=new[i]['final_W_out'])))
    actual_late=late_native();old=predicted(H/'sc1_supply/forecast3300/applied.response.json.gz',3300,1)[0]
    new=predicted(HERE/'forecast3300/applied.response.json.gz',3300,1)[0]
    late={k:dict(actual=actual_late[k],previous=old[k],predicted=new[k]) for k in ('arrival10681','final_W_out')}
    base=read(H/'sc1_supply/forecast2400/summary.json')['results'];candidate=results[2400]
    native=read(H/'native2400_assessment.json')
    delta=lambda r:r['selected']['omega_ttt_veh_h']-r['hold']['omega_ttt_veh_h']
    fw=lambda r:sum(sign*sum(v for k,v in r[a]['costs_by_stock'].items() if k.startswith('freeway:')) for a,sign in [('selected',1),('hold',-1)])
    errors={}
    for key in ('arrival10681','final_W_out'):
        errors[key]={version:sum(abs(r[key][version]-r[key]['actual']) for r in rows) for version in ('previous','predicted')}
    actual=native['delta_omega_veh_h']['actual'];constraints={a:r['shared_constraints'] for a,r in candidate.items()}
    useful=(all(e['predicted']<e['previous'] for e in errors.values())
        and abs(delta(candidate)-actual)<abs(delta(base)-actual)
        and all(abs(r['predicted']-r['actual'])<=abs(r['previous']-r['actual'])+1e-7 for r in late.values()))
    result=dict(status='complete_one_candidate',forecasts=3,new_native=0,new_full_selections=0,tests=34,
        initialization_checks=checks,physical_conservation_and_receiving=True,comparisons2400=rows,unused3300=late,
        absolute_errors2400=errors,
        delta_omega_veh_h=dict(actual=actual,previous=delta(base),predicted=delta(candidate)),
        delta_mainline_veh_h=dict(actual=native['delta_mainline_veh_h']['actual'],previous=fw(base),predicted=fw(candidate)),
        added10681merge_veh=dict(actual=84,previous=base['selected']['predicted_merge']['accepted_vehicles_by_ramp']['RM_C10681']-base['hold']['predicted_merge']['accepted_vehicles_by_ramp']['RM_C10681'],predicted=candidate['selected']['predicted_merge']['accepted_vehicles_by_ramp']['RM_C10681']-candidate['hold']['predicted_merge']['accepted_vehicles_by_ramp']['RM_C10681']),
        shared_constraints=constraints,ad_retention_gate=useful,calibration_control_gate_passed=False,
        production_enabled=False,runtime_comparison_started=False,
        limitations=['Current lane exchange is an aggregate gap-fraction approximation; connector reservation remains compressed onto68.',
            'One past effective rate, no refit using validation. Unused3300 is the same seed, not independent seed validation.',
            'Selected changes city and multiple RM controls; no isolated10681 effect.',
            'TTT match alone does not prove causal dynamics or a full SDMPC optimum.'])
    PINS[str(Path(__file__))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();result['source_pins']=PINS
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    print(json.dumps({k:result[k] for k in ('comparisons2400','unused3300','absolute_errors2400','delta_omega_veh_h','added10681merge_veh','ad_retention_gate')},indent=2))
if __name__=='__main__':main()
