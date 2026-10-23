"""Read completed coupled calibration; no forecast, fitting or native execution."""
import datetime,gzip,hashlib,json
from pathlib import Path

V=Path(__file__).resolve().parent
O=V/'cellwise_coupled_20261020'
A=V/'outflow_followup_20261019'
PINS={}
def read(p):
    b=p.read_bytes();PINS[str(p)]=hashlib.sha256(b).hexdigest()
    return json.loads(gzip.decompress(b) if p.suffix=='.gz' else b)
def save(p,value):p.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')

def main():
    assert not (O/'assessment.json').exists(), 'Reuse completed assessment.'
    done=read(O/'completion.json');selection=read(O/'selection.json');protocol=read(O/'protocol.json')
    for p,h in done['source_pins'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
    best,baseline=selection['selected'],selection['baseline']
    rows=[]
    for case in protocol['train_starts']:
        rows.append(dict(start=case,baseline=baseline['scores'][str(case)],selected=best['scores'][str(case)]))
    contacts=[]
    for key,z,l,u in zip(protocol['parameters'],best['relative'],protocol['relative_lower'],protocol['relative_upper']):
        if min(abs(z-l),abs(z-u))<1e-5:contacts.append(key)
    output=dict(status='coupled_fit_requires_further_qualification' if selection['eligible_for_development'] else 'coupled_fit_training_gate_not_met',
        previous_goal_turn='progress: completed independent-cell conditional fits and changed next stage to regime-inclusive coupled trajectories',
        goal_turn_classification='progress: measured regime-inclusive fifteen-parameter coupled trajectories and bounded updates',
        training_rows=rows,training_loss_reduction=1-best['data_loss']/baseline['data_loss'],
        parameters=protocol['parameters'],initial=protocol['initial'],selected=best['values'],bound_contacts=contacts,
        forecasts=done['forecasts'],updates=done['updates'],nonlinear_convergence_proven=False,
        new_native=0,production_edits=0,controller_optimizations=0,physical_checks=done['all_physical_checks_passed'],
        candidate_adopted=False,goal_complete=False,app_goal_status='active',independent_validation_complete=False)
    if (O/'development_response.json').exists():
        pair=read(O/'development_response.json')
        h,s=pair['hold'],pair['selected']
        hr=read(Path(h['response_cache']));sr=read(Path(s['response_cache']))
        assert PINS[h['response_cache']]==h['response_sha256'] and PINS[s['response_cache']]==s['response_sha256']
        native=read(A/'approach_flux.json')
        omega=read(V/'native_analysis_repaired_20261016/horizon_summary.json')
        response=[]
        def costs(source,end,outside=False):
            result={}
            for r in source['residence']:
                assert not (r['start_sec']<end-1e-8 and r['end_sec']>end+1e-8)
                if r['end_sec']>end+1e-8:continue
                for key,value in r['inside_veh'].items():
                    if outside:value=r['model_stock_veh'][key]-value
                    result[key]=result.get(key,0.)+value*r['dt_h']
            return result
        for j,horizon in enumerate((150,300,450)):
            old=next(r for r in native['rows'] if r['case']=='selected' and r['horizon_sec']==horizon)
            hc,sc=costs(hr,2250+horizon),costs(sr,2250+horizon)
            response.append(dict(horizon=horizon,native_flow=old['outgoing18_boundary_delta_if_no_loss_in_first_meter'],
                native_detector=old['outgoing18_detector_delta'],native_first_meter_storage=old['outgoing18_first_meter_storage_delta'],
                old_model_flow=old['outgoing18_model_delta'],selected_model_flow=s['through'][j]-h['through'][j],
                native_region_stock=old['native_region_stock_delta'],
                selected_model_region_stock=sum(s['frames'][j]['n'][14:19])-sum(h['frames'][j]['n'][14:19]),
                native_omega_delta=omega['comparisons']['selected'][str(horizon)]['native_delta_omega_veh_h'],
                selected_model_omega_delta=sum(sc.values())-sum(hc.values())))
        hc,sc=costs(hr,2700),costs(sr,2700)
        ho,so=costs(hr,2700,True),costs(sr,2700,True)
        assert abs(sum(hc.values())-h['ttt'])<1e-7 and abs(sum(sc.values())-s['ttt'])<1e-7
        output['development_response']=response
        output['model_inside_cost_delta']={k:sc.get(k,0)-hc.get(k,0) for k in hc.keys()|sc.keys()}
        output['model_outside_cost_delta']={k:so.get(k,0)-ho.get(k,0) for k in ho.keys()|so.keys()}
    output['limitations']=['All three OFF windows are training/development, not held-out performance.',
        'The optimizer budget is two updates, so no nonlinear convergence/global optimum is claimed.',
        'Native conditional VSL contrast is under the recorded city/RM policy, not complete8100s policy gain.',
        'Native first-meter/no-loss correction and 5s integration limits remain; terminal residual is not normal exit.',
        'No AD/NP/NUF full-controller selection or independent-seed qualification was performed in this stage.']
    output['source_pins']=PINS
    save(O/'assessment.json',output)
    print(json.dumps({k:output[k] for k in ('status','training_loss_reduction','training_rows','forecasts','updates','bound_contacts')},indent=2))
    if 'development_response' in output:print(json.dumps(output['development_response'],indent=2))

if __name__=='__main__':main()
