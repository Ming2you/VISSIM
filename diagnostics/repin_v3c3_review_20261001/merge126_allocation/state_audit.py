"""Conditional same-state receiving check on cached native samples only."""
import ast
import gzip
import hashlib
import json
from collections import defaultdict
from pathlib import Path

from evaluation.controllers.physical_urban_transport import ReceivingEnvelope

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
I=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'
PINS={}


def read(p):
    raw=p.read_bytes();PINS[str(p)]=hashlib.sha256(raw).hexdigest()
    return json.loads(gzip.decompress(raw) if p.suffix=='.gz' else raw)


def main():
    assert not (HERE/'state_assessment.json').exists()
    protocol=read(HERE/'state_protocol.json')
    for path,pin in protocol['production_pins'].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==pin,path
    trace=read(I/'closedloop_recorded2700_select_check_trace10681_entry10643/held_actual_RM_C10681_trace.json.gz')
    cache=read(HERE.parent/'lane10643_native/rows.json.gz')
    receipt=read(HERE.parent/'frozen10643_receiver/assessment.json')
    frame_path=next(Path(p) for p in receipt['source_pins'] if p.endswith('frame_002700.json') and 'hold' in Path(p).parts)
    initial_frame=read(frame_path)
    assert PINS[str(frame_path)]==receipt['source_pins'][str(frame_path)]
    assert initial_frame['time_s']==2700
    initial_rows=[[2700,v[0],v[1],v[2],v[3],v[4]] for v in initial_frame['vehicles'] if v[1] in (126,10641,71)]
    g=trace['local_receiver_diagnostics']['states'][0]['geometry']
    epochs=defaultdict(list)
    for r in cache['rows']:
        if r[2] in (126,10641,71) and 2700.1-1e-6<=r[0]<=3145.1+1e-6:
            epochs[round(r[0]-.1)].append(r)
    assert sorted(epochs)==list(range(2700,3150,5))
    baseline={}
    for r in trace['local_receiver_diagnostics']['resources']:
        if r['kind']=='lane_urban_receiving':
            baseline[int(r['start_sec']),ast.literal_eval(r['resource'])]=r['available_veh']
    initial={tuple(c['cell']):c['stock'] for c in trace['local_receiver_diagnostics']['states'][0]['cells']}
    rows=[];unsupported=[];max_initial_error=0.;max_mass_error=0.;max_projection=0.
    keys=[(126,1,7),(126,2,7),(10641,1,0),(10641,2,0),(10641,1,1),(10641,2,1),
          *[(71,l,c) for l in range(1,6) for c in (0,3)]]
    for t,records in [(-1,initial_rows),*sorted(epochs.items())]:
        states={};projections={}
        for road in (126,10641,71):
            edges=g['edges'][str(road)]
            for lane in range(1,6 if road==71 else 3):
                vehicles=[r for r in records if r[2]==road and r[3]==lane]
                try:
                    env=ReceivingEnvelope(edges[-1],g['spacing'],g['speed'],g['wave'],[min(edges[-1],r[4]) for r in vehicles])
                except ValueError as exc:
                    unsupported.append(dict(time=t,road=road,lane=lane,count=len(vehicles),capacity=edges[-1]/g['spacing'],error=str(exc)))
                    projections[road,lane]=None
                    for cell in range(len(edges)-1):states[road,lane,cell]=(None,None)
                    continue
                projections[road,lane]=env.projection_max_m
                max_projection=max(max_projection,env.projection_max_m)
                n_total=0.
                for cell,(a,b) in enumerate(zip(edges,edges[1:])):
                    n=sum(max(0.,min(b,p)-max(a,p-g['spacing']))/g['spacing'] for p in env.positions)
                    n_total+=n
                    room=max(0.,min(g['capacity_rate'],g['wave']/(b-a)*((b-a)/g['spacing']-n)))
                    states[road,lane,cell]=(n,room)
                    if t==-1:max_initial_error=max(max_initial_error,abs(n-initial[road,lane,cell]))
                max_mass_error=max(max_mass_error,abs(n_total-len(vehicles)))
        if t==-1:continue
        for key in keys:
            n,room=states[key]
            # Each native sample is evaluated independently. No resulting state
            # or future observation is supplied to a prediction/controller.
            rows.append(dict(time=t,native_time=t+.1,cell=list(key),native_projected_stock=n,
                same_law_native_receiving=room,autonomous_model_receiving=baseline[t,key],
                projection_max_m=projections[key[:2]]))
    assert max_mass_error<1e-8
    assert max_initial_error<1e-8,max_initial_error
    summaries=[]
    for b in range(3):
        for key in keys:
            rr=[r for r in rows if r['cell']==list(key) and 2700+150*b<=r['time']<2850+150*b]
            assert len(rr)==30
            valid=[r for r in rr if r['same_law_native_receiving'] is not None]
            summaries.append(dict(start=2700+150*b,cell=list(key),samples=len(rr),valid_samples=len(valid),
                mean_native_stock=sum(r['native_projected_stock'] for r in valid)/len(valid) if valid else None,
                same_law_native_mean_receiving=sum(r['same_law_native_receiving'] for r in valid)/len(valid) if valid else None,
                autonomous_mean_receiving=sum(r['autonomous_model_receiving'] for r in valid)/len(valid) if valid else None,
                native_low_room_samples=sum(r['same_law_native_receiving']<.1*g['capacity_rate'] for r in valid),
                autonomous_low_room_samples=sum(r['autonomous_model_receiving']<.1*g['capacity_rate'] for r in valid)))
    for path,pin in protocol['production_pins'].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==pin,path
    out=dict(status='completed_conditional_state_diagnosis_with_unsupported_native_states',samples=90,rows=rows,summary=summaries,unsupported_lane_epochs=unsupported,
        max_exact_COM_initial_cell_stock_difference=max_initial_error,
        max_projection_m=max_projection,max_mass_error=max_mass_error,source_pins=PINS,
        production_changed=False,new_native=0,full_forecasts=0,fit=0,new_fzp_scan=0,
        limitations=['Future native snapshots are diagnostic only, independently projected with the existing6m initialization law.',
          'Receiving at5s sample points is not exact cumulative native capacity or a feasible command.',
          'Native cached positions are atinteger time+.1s; autonomous budgets are atinteger time. Exact initialization parity uses the separate COM2700 frame, not the laterFZP sample.',
          'Finite spatial projection changes positions, not vehicle count; its maximum displacement is reported.',
          'This separates autonomous stock drift from same-state algebra but does not prove a microscopic node priority law.'])
    (HERE/'state_assessment.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('initial_stock_error',max_initial_error,'mass',max_mass_error,'max_projection_m',max_projection)
    print('unsupported_lane_epochs',len(unsupported))
    for row in summaries:print(row)


if __name__=='__main__':main()
