"""Use closed native/cache evidence; inspect only the three new fixed forecasts."""
import ctypes,gzip,hashlib,json,re,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;H=HERE.parent;ROOT=HERE.parents[3]
sys.path[:0]=[str(ROOT),str(H)]
from qualify_native2400 import validate_scope
PINS={}
def read(p,compressed=False):
    data=p.read_bytes();PINS[str(p)]=hashlib.sha256(data).hexdigest()
    return json.loads(gzip.decompress(data) if compressed else data)
def prediction(folder,arm,at,depth):
    r=read(folder/(arm+'.response.json.gz'),True);rows=[]
    for j in range(depth):
        lo=at+150*j;hi=lo+150
        final=[x for x in r['residence'] if x['stage']=='urban' and x['end_sec']==hi]
        assert len(final)==1
        rows.append(dict(start_sec=lo,arrival10681=sum(t['vehicles'] for t in r['transfers']
            if lo<=t['start_sec']<hi and t['source']=='storage:SC1004_W_out' and t['target']=='ramp:RM_C10681'),
            final_W_out=final[0]['model_stock_veh']['storage:SC1004_W_out']))
    return rows
def main():
    assert not (HERE/'comparison.json').exists()
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(),0x4000)
    validate_scope(read(H/'native2400_analysis/summary.json'),read(H/'native2400_analysis/observed_input_qualification.json'))
    for p,d in read(HERE/'plan.json')['source_pins'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==d,p
    old=read(H/'lateral_access/comparison.json')
    # Prior report is a reusable cache of actual/sc1_supply values. Its rejected
    # lateral-candidate predictions are never a calibration input or baseline.
    for p,d in old['source_pins'].items():
        if any(token in p for token in ('sc1_supply','assessment_integer_ids.json','native2400_assessment.json','state_003450.json','frame_003450.json','frame_003300.json','mer_003450.jsonl','err_003450.jsonl')):
            data=Path(p).read_bytes();assert hashlib.sha256(data).hexdigest()==d,p;PINS[p]=d
    results={};checks=[]
    opaque=('lane_urban_runtime','lane_offramp_runtime','lane_freeway_runtime','lane_ramp_runtime','sc1001_approach','_component_vsl_exposure','_control_area_ledger')
    for at,depth,count in ((2400,3,2),(3300,1,1)):
        folder=HERE/f'forecast{at}';s=read(folder/'summary.json')
        assert read(folder/'completion.json')['status']=='complete'
        assert s['forecasts']==count and s['depth']==depth and s['native_runs']==s['optimizer_calls']==0
        assert not s['future_observation_inputs']
        before=read(H/f'sc1_supply/forecast{at}/state.json');after=read(folder/'state.json')
        changed=('known_legsplit_route_state','urban_storage_release_buffer')
        assert set(before)==set(after)
        for key in before:
            if key in changed:continue
            if key in opaque:
                norm=lambda v:re.sub(r' at 0x[0-9A-Fa-f]+>',' at ADDRESS>',json.dumps(v))
                assert norm(before[key])==norm(after[key]),key
            else:assert before[key]==after[key],key
        oldbuf=before['urban_storage_release_buffer'];newbuf=after['urban_storage_release_buffer']
        assert {k:v for k,v in oldbuf.items() if k!='SC1004_W_out'}=={k:v for k,v in newbuf.items() if k!='SC1004_W_out'}
        initial=after['known_legsplit_route_state']['cohorts']
        assert sum(c['vehicles'] for c in initial)==sum(c['vehicles'] for c in before['known_legsplit_route_state']['cohorts'])
        assert not any('connector68' in c and 'lane68' in c for c in initial)
        for label,r in s['results'].items():
            assert r['conservation_states']==depth+1 and r['writer_validated'] and r['resource_max_exceedance']<=1e-7
            assert all(abs(b['local_balance_error_veh'])<1e-7 for g in r['local'].values() for b in g['bins'])
            for cohorts in r['known_endpoint_cohorts']:
                assert not any('connector68' in c and 'lane68' in c for c in cohorts)
                for c in cohorts:
                    for tag in ('connector68','lane68'):
                        if tag in c and c['vehicles']>1e-8:assert abs(sum(c[tag]['shares'].values())-1)<1e-7
        results[at]=s['results'];checks.append(dict(at=at,physical_numeric_initial_state_unchanged=True,changed_aliases=changed,opaque_runtime_type_only=opaque))
    comparisons=[]
    for arm in ('hold','selected'):
        new=prediction(HERE/'forecast2400',arm,2400,3)
        for i,row in enumerate(x for x in old['comparisons2400'] if x['arm']==arm):
            comparisons.append(dict(arm=arm,start_sec=row['start_sec'],**{k:dict(actual=row[k]['actual'],previous=row[k]['previous'],predicted=new[i][k]) for k in ('arrival10681','final_W_out')}))
    new=prediction(HERE/'forecast3300','applied',3300,1)[0]
    late={k:dict(actual=old['unused3300'][k]['actual'],previous=old['unused3300'][k]['previous'],predicted=new[k]) for k in ('arrival10681','final_W_out')}
    base=read(H/'sc1_supply/forecast2400/summary.json')['results'];candidate=results[2400]
    delta=lambda r:r['selected']['omega_ttt_veh_h']-r['hold']['omega_ttt_veh_h']
    fw=lambda r:sum(sign*sum(v for k,v in r[a]['costs_by_stock'].items() if k.startswith('freeway:')) for a,sign in [('selected',1),('hold',-1)])
    errors={k:{v:sum(abs(r[k][v]-r[k]['actual']) for r in comparisons) for v in ('previous','predicted')} for k in ('arrival10681','final_W_out')}
    result=dict(status='complete_one_connector_lane_composition',forecasts=3,new_native=0,new_full_selections=0,new_fitted_coefficients=0,tests=45,
        initialization_checks=checks,physical_conservation_and_receiving=True,comparisons2400=comparisons,unused3300=late,
        absolute_errors2400=errors,delta_omega_veh_h=dict(actual=old['delta_omega_veh_h']['actual'],previous=delta(base),predicted=delta(candidate)),
        delta_mainline_veh_h=dict(actual=old['delta_mainline_veh_h']['actual'],previous=fw(base),predicted=fw(candidate)),
        added10681merge_veh=dict(actual=84,previous=old['added10681merge_veh']['previous'],predicted=candidate['selected']['predicted_merge']['accepted_vehicles_by_ramp']['RM_C10681']-candidate['hold']['predicted_merge']['accepted_vehicles_by_ramp']['RM_C10681']),
        shared_constraints={a:r['shared_constraints'] for a,r in candidate.items()},
        endpoint_stage_counts={a:[{tag:sum(c['vehicles'] for c in cs if tag in c) for tag in ('connector68','lane68')} for cs in r['known_endpoint_cohorts']] for a,r in candidate.items()},
        calibration_control_gate_passed=False,production_enabled=False,runtime_comparison_started=False,
        limitations=read(HERE/'plan.json')['limitations']+['Selected changes urban signals and multiple RM commands; not isolated10681 causal effect.'])
    attribution=read(H/'connector_attribution/assessment.json')
    original=read(HERE/'forecast2400/state.json')['known_legsplit_route_state']['cohorts']
    original=[c for c in original if c['target']=='RM_C10681']
    original_by_order={tuple(c['lane68']['order']):c for c in original}
    assert len(original_by_order)==len(original)==40
    group=lambda c:'initial_RM_lane'+next(iter(c['lane68']['shares']))
    grouped_initial={g:sum(c['vehicles'] for c in original if group(c)==g) for g in {group(c) for c in original}}
    response_groups={}
    for arm,record in candidate.items():
        previous=grouped_initial.copy();bins=[]
        for i,cohorts in enumerate(record['known_endpoint_cohorts']):
            still={g:0. for g in previous}
            for c in cohorts:
                if c['target']!='RM_C10681' or c['source']!='initial_current_route' or 'lane68' not in c:continue
                initial=original_by_order.get(tuple(c['lane68']['order']))
                if initial is not None:still[group(initial)]+=c['vehicles']
            entered={g:previous[g]-still[g] for g in still}
            assert all(n>=-1e-8 for n in entered.values())
            native=attribution['arms'][arm][i]['native']
            total=next(x['arrival10681']['predicted'] for x in comparisons if x['arm']==arm and x['start_sec']==2400+150*i)
            bins.append(dict(start_sec=2400+150*i,native=native['by_initial_group'],predicted_initial_entries=entered,
                predicted_noninitial_entries=total-sum(entered.values()),predicted_initial_remaining=still,
                native_initial_disposition=native['initial_RM_disposition']))
            previous=still
        response_groups[arm]=bins
    result['initial_RM_cohort_attribution']=response_groups
    PINS[str(Path(__file__))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();result['source_pins']=PINS
    (HERE/'comparison.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    print(json.dumps({k:result[k] for k in ('absolute_errors2400','delta_omega_veh_h','delta_mainline_veh_h','added10681merge_veh','unused3300')},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
