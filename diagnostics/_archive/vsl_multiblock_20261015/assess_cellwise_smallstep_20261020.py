"""Assess one completed smaller coupled calibration step from saved records."""
import datetime,gzip,hashlib,json,os
from pathlib import Path

V=Path(__file__).resolve().parent
O=V/'cellwise_smallstep_20261020'
A=V/'outflow_followup_20261019'
PINS={}
def read(p):
    b=p.read_bytes();PINS[str(p)]=hashlib.sha256(b).hexdigest()
    return json.loads(gzip.decompress(b) if p.suffix=='.gz' else b.decode('utf-8-sig'))
def save(p,x):
    tmp=p.with_name(p.name+'.tmp');tmp.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8');os.replace(tmp,p)
def costs(response,end,outside=False):
    total={}
    for row in response['residence']:
        assert not(row['start_sec']<end-1e-8 and row['end_sec']>end+1e-8)
        if row['end_sec']>end+1e-8:continue
        for name,value in row['inside_veh'].items():
            if outside:value=row['model_stock_veh'][name]-value
            total[name]=total.get(name,0.)+value*row['dt_h']
    return total

def main():
    assert not (O/'assessment.json').exists(),'Reuse completed assessment'
    closure=read(O/'owner_closure.json')
    assert closure['recorded_pid_absent'] and closure['actual_exit_code']==0
    done=read(O/'completion.json');selection=read(O/'selection.json');protocol=read(O/'protocol.json')
    assert done['forecasts'] in (3,4) and done['new_native']==0
    for path,digest in done['source_pins'].items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest,path
    predicted=protocol['baseline']['data_loss']-protocol['linear_prediction_loss']
    observed=selection['baseline_loss']-selection['candidate_loss']
    report=dict(status='training_gate_passed_development_only' if selection['eligible_for_development'] else 'smaller_step_training_gate_not_met',
        created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        baseline_loss=selection['baseline_loss'],measured_loss=selection['candidate_loss'],training_reduction=selection['training_reduction'],
        linear_prediction_loss=protocol['linear_prediction_loss'],reduction_agreement_ratio=observed/predicted,
        training_scores=selection['scores'],baseline_scores=protocol['baseline']['scores'],retention_guard=selection['retention_guard'],
        forecasts=done['forecasts'],new_jacobian_probes=0,new_native=0,production_edits=0,controller_optimizations=0,
        all_physical_checks_passed=done['all_physical_checks_passed'],candidate_adopted=False,goal_complete=False,nonlinear_convergence_proven=False,
        validation='1650/2250/2850 are training/development, not independent validation. No production adoption or full-controller qualification.')
    if selection['eligible_for_development']:
        pair=read(O/'development_response.json');h,s=pair['hold'],pair['selected']
        hr=read(Path(h['response_cache']));sr=read(Path(s['response_cache']))
        assert PINS[h['response_cache']]==h['response_sha256'] and PINS[s['response_cache']]==s['response_sha256']
        flow=read(A/'approach_flux.json');omega=read(V/'native_analysis_repaired_20261016/horizon_summary.json')
        contrasts=[]
        for j,horizon in enumerate((150,300,450)):
            native=next(r for r in flow['rows'] if r['case']=='selected' and r['horizon_sec']==horizon)
            hc,sc=costs(hr,2250+horizon),costs(sr,2250+horizon)
            contrasts.append(dict(horizon=horizon,native_flow=native['outgoing18_boundary_delta_if_no_loss_in_first_meter'],
                old_model_flow=native['outgoing18_model_delta'],candidate_model_flow=s['through'][j]-h['through'][j],
                native_region_stock=native['native_region_stock_delta'],candidate_model_region_stock=sum(s['frames'][j]['n'][14:19])-sum(h['frames'][j]['n'][14:19]),
                native_omega_delta=omega['comparisons']['selected'][str(horizon)]['native_delta_omega_veh_h'],candidate_model_omega_delta=sum(sc.values())-sum(hc.values())))
        report['development_response']=contrasts
        hc,sc=costs(hr,2700),costs(sr,2700)
        ho,so=costs(hr,2700,True),costs(sr,2700,True)
        assert abs(sum(hc.values())-h['ttt'])<1e-7 and abs(sum(sc.values())-s['ttt'])<1e-7
        report['model_inside_cost_delta']={k:sc.get(k,0)-hc.get(k,0) for k in hc.keys()|sc.keys()}
        report['model_outside_cost_delta']={k:so.get(k,0)-ho.get(k,0) for k in ho.keys()|so.keys()}
        report['native_limits']='Conditional VSL contrast under fixed recorded city/RM; first-meter no-loss boundary correction and5s integration limits preserved; final stock is not normal exit; no full8100 policy claim.'
    report['source_pins']=PINS
    save(O/'assessment.json',report)
    print(json.dumps({k:v for k,v in report.items() if k not in ('source_pins','training_scores','baseline_scores')},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
