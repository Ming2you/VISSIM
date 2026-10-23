"""Assess completed time-step sensitivity using existing native observations."""
import gzip,hashlib,json,math
from pathlib import Path
A=Path(__file__).resolve().parent;C=A/'refine15_clock';F=C/'forecasts';PINS={}
def read(p):
    b=p.read_bytes();PINS[str(p)]=hashlib.sha256(b).hexdigest()
    return json.loads(gzip.decompress(b) if p.suffix=='.gz' else b)
def main():
    assert not (C/'assessment.json').exists()
    done=read(F/'completion.json'); assert done['new_forecasts']==4
    for p,h in done['source_pins'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h
    cases={r['name']:r for r in read(F/'results.json')}
    prior={r['name']:r for r in read(A/'refine15_candidate/results.json')}
    observed=read(A/'observed_variance.json')['subcells']
    results={};response={};stock={};speed={}
    for name in ('hold','selected','hold125','selected125','hold0625','selected0625'):
        folder=A/'refine15_candidate' if name in prior else F
        trace=read(folder/f'{name}_subcells.json');r=read(folder/f'{name}_response.json.gz')
        previous=2250.;floor_sec=0.;initial_min=200.;steps=[]
        for frame in trace:
            dt=frame['time']-previous;steps.append(dt)
            if frame['time']<=2260+1e-7:
                floor_sec+=dt*(frame['speed'][1]<=5+1e-9)
                initial_min=min(initial_min,frame['speed'][1])
            previous=frame['time']
        assert abs(sum(steps)-450)<1e-7
        if name.endswith('125'):assert max(steps)<=1.25+1e-7
        if name.endswith('0625'):assert max(steps)<=.625+1e-7
        frames=[next(f for f in trace if abs(f['time']-t)<1e-7) for t in (2400,2550,2700)]
        stock[name]=[n for f in frames for n in f['n']];speed[name]=[v for f in frames for v in f['speed']]
        arm='hold' if name.startswith('hold') else 'selected'
        native=[next(x for x in observed if (x['seed'],x['arm'],x['elapsed'],x['cell'],x['piece'])==(29,arm,e,15,j)) for e in (150,300,450) for j in range(3)]
        response[name]=[sum(x['accepted_total_veh'] for x in r['resource_allocations'] if x['kind']=='freeway_mainline_sending' and x['resource']=='FW_E:cell:18' and x['end_sec']<=t+1e-7) for t in (2400,2550,2700)]
        results[name]=dict(steps=len(trace),max_dt_sec=max(steps),first10_middle_floor_sec=floor_sec,first10_middle_min_speed=initial_min,
            holdout_subcell_speed_rmse=math.sqrt(sum((v-x['mean'])**2 for v,x in zip(speed[name],native))/9),
            holdout_subcell_stock_rmse=math.sqrt(sum((n-x['n'])**2 for n,x in zip(stock[name],native))/9))
    contrasts=[]
    for label,h,s in [('original','hold','selected'),('cap1.25','hold125','selected125'),('cap0.625','hold0625','selected0625')]:
        table=prior if label=='original' else cases
        contrasts.append(dict(grid=label,delta_throughflow=[b-a for a,b in zip(response[h],response[s])],delta_omega=table[s]['ttt_veh_h']-table[h]['ttt_veh_h'],
            delta_stock=[sum(table[s]['snapshots'][i]['n']['FW_E'][14:19])-sum(table[h]['snapshots'][i]['n']['FW_E'][14:19]) for i in (1,2,3)]))
    screen=dict(hold_subcell_max_speed_change_kmh=max(abs(a-b) for a,b in zip(speed['hold125'],speed['hold0625'])),
        hold_subcell_max_stock_change_veh=max(abs(a-b) for a,b in zip(stock['hold125'],stock['hold0625'])),
        response_throughflow_change_veh=max(abs(a-b) for a,b in zip(contrasts[1]['delta_throughflow'],contrasts[2]['delta_throughflow'])),
        omega_contrast_change_veh_h=abs(contrasts[1]['delta_omega']-contrasts[2]['delta_omega']))
    thresholds=read(C/'protocol.json')['preregistered_screen']
    verdict={k:screen[k]<=thresholds[k] for k in screen}
    report=dict(status='completed_time_step_sensitivity_not_adopted',results=results,contrasts=contrasts,screen=screen,screen_pass=verdict,
        max_tag_balance=done['max_tag_balance'],max_cohort_balance=done['max_vsl_balance'],new_forecasts=4,new_native=0,new_fits=0,
        candidate_adopted=False,goal_complete=False,source_pins=PINS,
        interpretation='Shorter internal steps do not establish a calibrated spatial model. Inspect speed-floor contact separately from450s response convergence; native gain is not an acceptance target for choosing a grid.')
    for p,h in PINS.items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h
    (C/'assessment.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:report[k] for k in ('results','contrasts','screen','screen_pass')},indent=2))
if __name__=='__main__':main()
