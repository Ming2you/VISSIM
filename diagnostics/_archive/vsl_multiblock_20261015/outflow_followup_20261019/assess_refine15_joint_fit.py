"""Evaluate the frozen single trajectory-fit update; never refit on validation."""
import hashlib,json,math
from pathlib import Path
A=Path(__file__).resolve().parent;O=A/'refine15_joint_fit';PINS={}
def read(p):
    b=p.read_bytes();PINS[str(p)]=hashlib.sha256(b).hexdigest();return json.loads(b)
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
def main():
    assert not (O/'assessment.json').exists()
    done=read(O/'completion.json');selection=read(O/'selection.json')
    for p,h in done['source_pins'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
    report=dict(status='complete_joint_step_pending_interpretation',training=selection,new_forecasts=done['forecasts'],fits=1,
        new_native=0,new_SDMPC_optimizations=0,candidate_adopted=False,goal_complete=False,
        max_route_balance=done['max_route_balance'],max_vsl_balance=done['max_vsl_balance'])
    if not selection['eligible']:
        report.update(status='bounded_joint_update_failed_training_gate',independent_validation_performed=False)
    else:
        validation={r['label']:r for r in read(O/'validation.json')};truth=read(O/'validation_truth.json')
        old={r['name']:r for r in read(A/'refine15_clock/forecasts/results.json')}
        oldclock=read(A/'refine15_clock/assessment.json');flux=read(A/'approach_flux.json')
        newhold,newselected=validation['validation_hold'],validation['validation_selected']
        ns=[a-b for p,q in zip(newhold['frames'],truth) for a,b in zip(p['n'],q['n'])]
        vs=[a-b for p,q in zip(newhold['frames'],truth) for a,b in zip(p['speed'],q['speed'])]
        rows=[]
        for j,t in enumerate((150,300,450)):
            actual=next(r for r in flux['rows'] if r['case']=='selected' and r['horizon_sec']==t)
            before=oldclock['contrasts'][2]
            rows.append(dict(horizon=t,native_flow_delta=actual['outgoing18_detector_delta'],native_first_meter_stock_delta=actual['outgoing18_first_meter_storage_delta'],
                baseline_flow_delta=before['delta_throughflow'][j],fitted_flow_delta=newselected['throughflow'][j]-newhold['throughflow'][j],
                native_stock_delta=actual['native_region_stock_delta'],baseline_stock_delta=before['delta_stock'][j],
                fitted_stock_delta=sum(newselected['snapshots'][j+1]['n']['FW_E'][14:19])-sum(newhold['snapshots'][j+1]['n']['FW_E'][14:19])))
        baseline_frames=[]
        trace=read(A/'refine15_clock/forecasts/hold0625_subcells.json')
        for j,t in enumerate((2400,2550,2700),1):
            fine=next(f for f in trace if abs(f['time']-t)<1e-8);snap=old['hold0625']['snapshots'][j]
            baseline_frames.append(dict(n=[snap['n']['FW_E'][14],*fine['n'],*snap['n']['FW_E'][16:19]],speed=[snap['speed']['FW_E'][14],*fine['speed'],*snap['speed']['FW_E'][16:19]]))
        bn=[a-b for p,q in zip(baseline_frames,truth) for a,b in zip(p['n'],q['n'])];bv=[a-b for p,q in zip(baseline_frames,truth) for a,b in zip(p['speed'],q['speed'])]
        rmse=lambda xs:math.sqrt(sum(x*x for x in xs)/len(xs))
        actualomega=read(A/'distribution_assessment.json')['whole_omega_delta']['native']
        native=rows[-1];delta=newselected['ttt']-newhold['ttt'];bd=oldclock['contrasts'][2]['delta_omega']
        gates=dict(holdout_stock_rmse=rmse(ns)<=rmse(bn),holdout_speed_rmse=rmse(vs)<=rmse(bv),
            response_flow_direction=native['fitted_flow_delta']>0,response_stock_direction=native['fitted_stock_delta']<0,
            response_flow_error=abs(native['fitted_flow_delta']-native['native_flow_delta'])<abs(native['baseline_flow_delta']-native['native_flow_delta']),
            response_stock_error=abs(native['fitted_stock_delta']-native['native_stock_delta'])<abs(native['baseline_stock_delta']-native['native_stock_delta']),
            omega_contrast_error=abs(delta-actualomega)<abs(bd-actualomega))
        # The2250 initial native partition must be identical to the earlier run.
        seeded=read(O/'capture_2250/isolated_capture.json')['initial_refinement'];previous=read(A/'refine15_candidate/initial_refinement.json')
        assert seeded==previous
        report.update(status='requires_independent_validation' if all(gates.values()) else 'bounded_joint_update_failed_validation_gate',
            validation_gates=gates,rows=rows,whole_omega_delta=dict(native=actualomega,same_grid_baseline=bd,fitted=delta),
            holdout_rmse=dict(stock_baseline=rmse(bn),stock_fitted=rmse(ns),speed_baseline=rmse(bv),speed_fitted=rmse(vs)),
            initial_refinement_exact=True,independent_seed_validation_performed=False)
    report['source_pins']=PINS
    report['limitations']=['This is a single bounded Gauss-Newton update, not completed nonlinear calibration or a converged optimum.',
        'Native conditional VSL response is under the recorded city/RM schedule; no autonomous8100-policy gain is claimed.',
        'Parameter boundaries and training-window coverage may limit transfer. Spatial refinement as a model class is not rejected by this candidate result.']
    save(O/'assessment.json',report)
    print(json.dumps({k:v for k,v in report.items() if k not in ('source_pins','training')},indent=2))
if __name__=='__main__':main()
