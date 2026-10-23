"""Assess saved regime-inclusive calibration without another fit or rollout."""
import datetime,hashlib,json
from pathlib import Path
A=Path(__file__).resolve().parent;H=A.parent;O=A/'refine15_regime_fit_v3';PINS={}
def read(p):
    b=p.read_bytes();PINS[str(p)]=hashlib.sha256(b).hexdigest();return json.loads(b)
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
def main():
    assert not (O/'assessment.json').exists()
    done=read(O/'completion.json');sel=read(O/'selection.json')
    for p,h in done['source_pins'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
    report=dict(status='completed_regime_fit_pending_independent_validation' if sel['eligible'] else 'regime_fit_not_qualified',
        training=sel,new_forecasts=done['forecasts'],reused_forecasts=done['reused_forecasts'],updates=done['updates'],
        new_native=0,new_SDMPC_optimizations=0,production_edits=0,candidate_adopted=False,goal_complete=False,
        max_route_balance=done['max_route_balance'],max_vsl_balance=done['max_vsl_balance'],
        development2250_now_used_for_training=True,heldout_seeds_used_for_training=False,
        independent_validation_performed=False,nonlinear_convergence_claimed=False)
    if (O/'development_response.json').exists():
        p=read(O/'development_response.json');actual=read(A/'approach_flux.json');rows=[]
        for j,t in enumerate((150,300,450)):
            r=next(x for x in actual['rows'] if x['case']=='selected' and x['horizon_sec']==t)
            hold,selp=p['hold'],p['selected']
            rows.append(dict(horizon=t,native_flow_delta=r['outgoing18_detector_delta'],native_face_stock=r['outgoing18_first_meter_storage_delta'],
                predicted_flow_delta=selp['throughflow'][j]-hold['throughflow'][j],native_stock_delta=r['native_region_stock_delta'],
                predicted_stock_delta=sum(selp['snapshots'][j+1]['n']['FW_E'][14:19])-sum(hold['snapshots'][j+1]['n']['FW_E'][14:19])))
        report['development_response']=dict(rows=rows,predicted_omega_delta=selp['ttt']-hold['ttt'],native_omega_delta=read(A/'distribution_assessment.json')['whole_omega_delta']['native'],
            scope='Native hold2250 is now a calibration case. VSL90 outcomes are excluded from fit, but this is development response, not untouched validation.')
    report['source_pins']=PINS
    save(O/'assessment.json',report)
    print(json.dumps({k:v for k,v in report.items() if k not in ('source_pins','training')},indent=2))
if __name__=='__main__':main()
