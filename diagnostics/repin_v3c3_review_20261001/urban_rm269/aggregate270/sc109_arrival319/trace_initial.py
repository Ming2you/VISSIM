"""Passive initial-cohort attribution from saved aggregate flux; no model rerun."""
from pathlib import Path
from collections import deque
import gzip
import hashlib
import json
import pickle

HERE=Path(__file__).resolve().parent
A=HERE.parent
MODEL=Path('E:/VISSIM_analysis/20261010_source_boundary318/forecast2400')
MOVE='movement:SC109_W_SC108_to_E'
STORAGE='storage:SC108_to_SC109'
PINS={}


def raw(path):
    path=Path(path);b=path.read_bytes();PINS[str(path)]=hashlib.sha256(b).hexdigest();return b


def trace(response,cfg,state,policy):
    beta=cfg.network.urban_movements[MOVE.split(':',1)[1]]['beta']
    initial_q=state.urban_movement_queue[MOVE.split(':',1)[1]]
    initial_calendar={k*cfg.simulation.T_u_sec:v*beta for k,v in state.urban_arrival_buffer['SC108_to_SC109'].items()}
    parts=deque([['initial',initial_q]])
    outputs=[]
    for row in (r for r in response['residence'] if r['stage']=='urban'):
        t=row['start_sec']
        arrivals=sum(x['vehicles'] for x in response['transfers'] if x['source']==STORAGE and x['target']==MOVE and x['start_sec']==t)
        initial=initial_calendar.get(t,0.)
        assert initial<=arrivals+1e-8,(t,initial,arrivals)
        if initial>0:parts.append(['initial',initial])
        if arrivals-initial>1e-8:parts.append(['new',arrivals-initial])
        total=sum(p[1] for p in parts)
        discharge=sum(x['vehicles'] for x in response['transfers'] if x['source']==MOVE and x['target']!=MOVE and x['start_sec']==t)
        assert discharge<=total+1e-8
        initial_out=0.
        if policy=='fifo':
            left=discharge
            while left>1e-9:
                label,n=parts[0];take=min(n,left)
                initial_out+=take if label=='initial' else 0.
                parts[0][1]-=take;left-=take
                if parts[0][1]<1e-9:parts.popleft()
        else:
            fraction=min(1.,discharge/total) if total else 0.
            for part in parts:
                take=part[1]*fraction
                initial_out+=take if part[0]=='initial' else 0.
                part[1]-=take
        assert abs(sum(p[1] for p in parts)-row['model_stock_veh'][MOVE])<1e-7
        outputs.append(dict(start_sec=t,end_sec=row['end_sec'],initial_departed_veh=initial_out,
                            initial_queued_veh=sum(p[1] for p in parts if p[0]=='initial')))
    expected=initial_q+sum(initial_calendar.values())
    departed=sum(x['initial_departed_veh'] for x in outputs)
    assert abs(departed+sum(p[1] for p in parts if p[0]=='initial')-expected)<1e-7
    return dict(initial_total_veh=expected,departed_veh=departed,
                departure_time_cost_start=-sum(x['initial_departed_veh']*(2850-x['start_sec'])/3600 for x in outputs),
                departure_time_cost_end=-sum(x['initial_departed_veh']*(2850-x['end_sec'])/3600 for x in outputs),
                output=outputs)


def main():
    out=HERE/'initial_trace.json';assert not out.exists()
    cfg,state,_=pickle.loads(raw(A/'citysplit287/forecast2400/initial.pickle'))
    result={}
    for arm in ('hold','city'):
        response=json.loads(gzip.decompress(raw(MODEL/(arm+'.response.json.gz'))))
        result[arm]={policy:trace(response,cfg,state,policy) for policy in ('fifo','proportional')}
    native=json.loads(raw(A/'exit_timing309/sc109_chain.json'))
    cohorts=native['native_exit_cohorts']
    actual=cohorts['city']['initial_local']['cost']-cohorts['hold']['initial_local']['cost']
    delta={policy:{key:result['city'][policy][key]-result['hold'][policy][key]
                   for key in ('departed_veh','departure_time_cost_start','departure_time_cost_end')} for policy in result['hold']}
    raw(Path(__file__))
    report=dict(status='complete_initial_calendar_timing_attribution',results=result,city_minus_hold=delta,
                native_initial_local_exit_delta_veh_h=actual,source_pins=PINS,
                limitation='FIFO/proportional are passive diagnostic labels on the same aggregate flux, not implemented vehicle FIFO or a proven causal decomposition. Initial modeled through37.7703 and native36 exited local cohort are not identical sets.',
                new_forecasts=0,new_fits=0,production_changes=0,goal_complete=False)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('INITIAL_TRACE',json.dumps(delta),'NATIVE',actual)


if __name__=='__main__':main()
