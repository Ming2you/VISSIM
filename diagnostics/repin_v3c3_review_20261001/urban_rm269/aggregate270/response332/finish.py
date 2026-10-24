"""Record completed332 without another forecast, optimizer, or native run."""
from pathlib import Path
from datetime import datetime,timezone
import gzip,hashlib,json
HERE=Path(__file__).resolve().parent;A=HERE.parent;H=A.parent
OUT=Path('E:/VISSIM_analysis/20261010_response332/forecast3300')
read=lambda p:json.loads(Path(p).read_bytes())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
def main():
    assert not (HERE/'completion.json').exists()
    assessment=read(HERE/'assessment.json');summary=read(OUT/'summary.json')
    assert summary['forecasts']==3 and summary['status']=='complete'
    assert assessment['physical_checks_passed']
    pins=dict(summary['source_pins'])
    for p,h in pins.items():assert sha(p)==h,p
    clock={};arrivals={}
    for arm in ('hold','release','recorded'):
        path=OUT/(arm+'.response.json.gz');pins[str(path)]=sha(path)
        r=json.loads(gzip.decompress(path.read_bytes()))
        ff=r['freeway_frames'];rr=r['residence']
        assert len(ff)==90 and len(rr)==45
        assert all(abs(x['end_sec']-x['start_sec']-5)<1e-7 for x in ff)
        assert all(abs(x['end_sec']-x['start_sec']-10)<1e-7 for x in rr)
        clock[arm]=dict(freeway_intervals=90,freeway_step_sec=5,urban_intervals=45,urban_step_sec=10)
        key='ramp:RM_C10681'
        # Exchange reservations appear twice in the ledger. Subtract their
        # outgoing handoff before counting net arrival; never count both.
        net=sum(x['vehicles'] for x in r['transfers'] if x['target']==key)-sum(
            x['vehicles'] for x in r['transfers'] if x['source']==key and x['target']!='merge_pending:RM_C10681')
        states=read(OUT/(arm+'.stocks.json'))
        stock=lambda row:sum(row['stocks'][key].values())
        merge=read(OUT/(arm+'.json'))['predicted_merge']['accepted_vehicles_by_ramp']['RM_C10681']
        assert abs(stock(states[0])+net-merge-stock(states[-1]))<1e-7
        arrivals[arm]=net
    save(HERE/'clock_and_balance.json',dict(clock=clock,net_arrival10681=arrivals,source_pins={p:h for p,h in pins.items() if p.endswith('response.json.gz')}))
    stage=dict(status='complete_bounded_response_review',assessment=str(HERE/'assessment.json'),readme=str(HERE/'README.md'),
        new_forecasts450=3,native=0,fzp=0,ad=0,optimizer=0,new_fits=0,production_adopted=False,goal_complete=False,
        model_release_minus_hold_omega=assessment['release_minus_hold_cost']['omega'],
        recorded10681=assessment['recorded_merge_comparison']['RM_C10681'],
        clocks=dict(freeway_sec=5,urban_sec=10,control_sec=150,horizon_sec=450,terminal_cost=False,internal_stability_substeps_retained=True),
        remaining='52/58 and ramp arrival underprediction at3300 persists; whole city/joint ranking and latest AD/SDMPC integration remain unqualified')
    now=datetime.now(timezone.utc).isoformat()
    next_step=('KeepFW5/U10 and fixed coefficients. Reuse Claude and prior271/city-response records plus saved3300-3750 boundaries to separate52/58 upstream arrivals, head discharge and route transit causing understock/ramp arrival shortage. No small-sign fitting of the model-only -0.271vehh RM pair. Recorded10681 merge112 versus113.601 is close, but arrival110 versus96.915 and spatial stock errors remain. Then bound latest diagnostic AD and full-choice qualification based on material evidence. No duplicate forecasts/native, grids, or push;450s horizon and terminalOFF unchanged.')
    for parent in (A,H):
        path=parent/'plan.json';backup=parent/'plan.before332.json';assert not backup.exists()
        backup.write_bytes(path.read_bytes());p=read(path);p.update(response332=stage,
            current_stage='response332_rm3300_reviewed_arrival_shortage_remaining',
            latest_stage=str(HERE/'README.md'),next_step=next_step,current_workers=[],goal_complete=False,updated_utc=now,
            latest_goal_turn_audit=dict(previous='progress331_current3300_initialization_conserved',current='progress332_three_fixed450_forecasts_recorded_boundary_review_and_actual5_10_clock_verified'),
            last_goal_turn='progress332_bounded_response_complete_no_fit_or_native')
        save(path,p)
    for path in (*HERE.glob('*.py'),HERE/'README.md',HERE/'assessment.json',HERE/'clock_and_balance.json'):
        pins[str(path)]=sha(path)
    save(HERE/'completion.json',dict(completed_at=now,status='complete_stage_only',goal_complete=False,
        new_forecasts450=3,reused_predictions=0,new_native=0,new_ad=0,new_optimizer=0,new_fits=0,push=0,
        source_pins=pins,next_step=next_step))
    print('COMPLETE332',dict(clock=clock,arrivals=arrivals,goal_complete=False))
if __name__=='__main__':main()

