"""Check executed laws, conservation and held-period/action results after fit."""
import json, math
from pathlib import Path
import calibrate as c
from prepare import save,table
B=c.B;O=B/'literature_v2';ROOT=c.ROOT;K=B.parent/'cohort_dynamics_20260920'

def execution_name(row,role):
    if role=='selected':
        return 'lit_selected_width_corrected' if row['spec'].get('port_response',{}).get('spillback') else 'lit_selected_final'
    return 'lit_all_terms_width_corrected'

def audit_laws(p,spec):
    rows=next(d for d in p['diagnostics']['roads'] if d['road']=='FW_E').get('port_response_trace',[])
    counts={k:0 for k in ('merge_speed','diverge_density','spillback')};changed=dict(counts)
    losses={};pr=spec.get('port_response',{})
    for r in rows:
        kind=r['kind'];counts[kind]+=1
        if kind=='merge_speed':
            if r['accepted_in_veh']:
                assert abs(r['after_kmh']-r['velocity_moment']/r['accepted_in_veh'])<1e-10
            else:assert r['after_kmh']==r['before_kmh']
            changed[kind]+=abs(r['after_kmh']-r['before_kmh'])>1e-8
        elif kind=='diverge_density':
            off=r['off_density'] if isinstance(r['off_density'],list) else [r['off_density']]
            ds=[r['before_density']]+off;expected=sum(x*x for x in ds)/sum(ds) if sum(ds) else 0.
            assert abs(expected-r['after_density'])<1e-10
            changed[kind]+=abs(expected-r['before_density'])>1e-8
        else:
            sp=pr['spillback']
            if sp is None:continue
            i=r['cell'];widths=c.WIDTHS[i];loss=-math.expm1(-(r['off_n_veh']/(sp['gamma']*r['off_capacity_veh']))**sp['b']/sp['b'])
            assert abs(r['physical_lanes']-r['operational_lanes']-loss)<1e-10
            access=c.S['off_access'][r['connector']]['weights'];available=sum(w for w,a in zip(widths,access) if a)
            factors=[1-loss/available if a else 1 for a in access]
            expected=factors if sp['mode']=='replace_fifo' else [min(a,b) for a,b in zip(factors,r['original_fifo'])]
            assert all(abs(a-b)<1e-10 for a,b in zip(expected,r['used_fifo']))
            assert r['speed_fifo']==([1.]*len(widths) if sp['mode']=='replace_fifo' else r['original_fifo'])
            changed[kind]+=loss>1e-8
            losses.setdefault(r['connector'],[]).append(loss)
    return dict(calls=counts,changed=changed,lane_loss={k:dict(max=max(v),mean=sum(v)/len(v)) for k,v in losses.items()})

def main():
    candidates=c.load(O/'candidates.json');selected=c.load(O/'selected.json');full=c.load(O/'selected_all_terms.json')
    actual_path=B.parent/'response_chain_20260921/qualification.json';actual=c.load(actual_path)['gains']
    frozen={p:c.sha(O/p) for p in ['selected.json','selected_all_terms.json']}
    before=c.load(B/'refined_guard1_none.json');metrics=[];gains=[];audits={};numerics=[]
    cases=[('selected',selected)]
    if full['name']!=selected['name']:cases.append(('all_terms',full))
    for role,row in cases:
        name=execution_name(row,role);p=c.load(O/name/'refined_guard1_none.json')
        assert p==c.load(O/row['name']/'refined_guard1_none.json'),'Frozen NC changed in action replay'
        result=c.load(K/('segment_resolution_20260921_cal_'+name)/'result.json')
        for phase,lo,hi in [('train',0,10),('late',10,15)]:
            metrics.append(dict(case=role,phase=phase,**c.score(p,lo,hi)))
        for arm in ('none','rm_ramp','vsl','both'):
            forecast=c.load(O/name/f'refined_guard1_{arm}.json');base=c.load(B/f'refined_guard1_{arm}.json')
            numerics.append(dict(case=role,arm=arm,**c.screen(forecast)))
            audits[role+':'+arm]=audit_laws(forecast,row['spec'])
            if row['spec'].get('anticipation'):
                used=c.load(O/name/f'anticipation_{arm}.json')
                assert set(used)==set(row['spec']['anticipation'])
                for key,value in used.items():assert value['calls']>0 and value['nu']==row['spec']['anticipation'][key]
                audits[role+':'+arm]['anticipation']=used
            for key in ('cells','flows'):
                assert [r for r in forecast[key] if r['road']=='FW_W']==[r for r in base[key] if r['road']=='FW_W']
            if role=='selected' and row['name']=='lit_disabled':assert forecast==base
            if arm!='none':
                gains.append(dict(case=role,arm=arm,actual_total=actual[arm]['actual']['total'],
                    predicted_total=result['deltas'][arm]['total'],mainline=result['deltas'][arm]['mainline'],
                    on=result['deltas'][arm]['on'],off=result['deltas'][arm]['off']))
    for phase,lo,hi in [('train',0,10),('late',10,15)]:metrics.append(dict(case='baseline',phase=phase,**c.score(before,lo,hi)))
    table(O/'state_metrics.csv',metrics);table(O/'gain_check.csv',gains);table(O/'numerics.csv',numerics)
    source_checks=0
    aliases={
        'physical_lane_groups.py':[O/'physical_lane_groups.py.before.txt',O/'physical_lane_groups_double_clamp.py.txt'],
        'canonical_harness.py':[O/'canonical_harness.py.before.txt',O/'canonical_harness_failed_scope.py.txt']}
    # Valid cached cases did not use the corrected closure path; retain their
    # executed sources instead of rewriting historical pins to current files.
    for row in candidates:
        if row['exit_code']!=0:continue
        protocol=c.load(K/('segment_resolution_20260921_cal_'+row['name'])/'protocol.json')
        for path,pin in protocol['source_pins'].items():
            file=ROOT/path;choices=[file]+aliases.get(file.name,[])
            assert any(c.sha(p)==pin for p in choices),(path,row['name']);source_checks+=1
    for path,pin in c.load(O/'protocol.json')['source_pins'].items():assert c.sha(ROOT/path)==pin;source_checks+=1
    completed=sum(c.load(p)['forecasts'] for p in O.glob('*/refined_guard1_receipt.json'))
    failed=[p.stem.replace('_score','') for p in O.glob('*_score.json') if c.load(p)['exit_code']!=0]
    invalid_old=[p.parent.name for p in O.glob('*/refined_guard1_receipt.json')
                 if c.load(p)['fit'].get('port_response',{}).get('spillback') and 'width_corrected' not in p.parent.name]
    assert all(c.sha(O/p)==pin for p,pin in frozen.items())
    save(O/'validation.json',dict(status='LITERATURE_TERMS_IMPLEMENTED_CALIBRATION_NOT_QUALIFIED',
        selected=selected,selected_all_terms=full,state_metrics=metrics,gains=gains,numerics=numerics,
        executed_law_checks=audits,source_pins_verified=source_checks,candidate_count=len(candidates)-1,
        invalid_candidates=[r['name'] for r in candidates if r['exit_code']!=0 or not r['numerics']['passed']],
        default_four_forecasts_exact=True,west_forecasts_exact=True,total_completed_forecasts=completed,
        failed_attempts=failed,double_clamp_results_excluded=invalid_old,
        new_native_runs=0,fresh_seed_or_initial_state=False,production_adopted=False,fit_data='NC2400-2700 only',
        eq22_adaptation='Operational through-sending width; physical storage/density width remains fixed for conservation. Existing FIFO speed clamp is used only for actual FIFO blockage, never merely operational width loss.',
        papers={'anticipation':'https://www.dcsc.tudelft.nl/~bdeschutter/pub/rep/02_015.pdf','junction_and_lane_loss':'User-supplied equations9,10,22; source title not independently identified.'},
        files={str(p.relative_to(ROOT)):c.sha(p) for p in [Path(__file__),actual_path,O/'protocol.json',O/'state_metrics.csv',O/'gain_check.csv',O/'selected.json',O/'selected_all_terms.json']}))
    print(json.dumps(dict(metrics=metrics,gains=gains,checks=source_checks,completed=completed),indent=2))

if __name__=='__main__':main()
