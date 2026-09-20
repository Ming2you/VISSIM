"""Local METANET identifiability with measured start states and merge exposures.

Fit NCseed23 before2400 only. Future accepted merges are training exposures,
not online forecast inputs. No treatment label or TTT is part of the loss.
The diagnostic omits lateral momentum and endogenous FIFO; a fitted parameter
vector must still pass the full conserved rollout before any qualification.
"""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.probe import e,H,MODEL,CASES
import numpy as np
from collections import Counter
import math

HERE=Path(__file__).resolve().parent;LANE=H/'lane_group_response_20260919'
NAMES=['v_free_multiplier','rho_crit_multiplier','tau_sec','nu_km2_h','kappa_veh_km_lane','delta_merge']


def records(seed,arm,*,include_downstream=False):
    moments={(r['time_s'],r['cell'],r['lane']):r for r in e.load(HERE/f'moments_v1/s{seed}_{arm}.json')['rows']}
    case=next(r for r in CASES if r[0]==seed);data=e.ObservationData(case[1])
    model=e.load_base_model(data.geometry,MODEL/'config.json');net=model.base.network
    geo=e.load(LANE/f'observations_v1/s{seed}.json')['geometry'];widths=geo['widths'];matrix=geo['matrices']
    if arm=='none':event_path=data.folder/'port_events.csv'
    elif arm=='vsl':event_path=case[2]/'observations/vsl/port_events.csv'
    elif seed==33 and arm=='spread_only':event_path=H/'state_exchange_20260920/dispersion_seed33_analysis_v1/observations/spread_only/port_events.csv'
    else:raise ValueError('Unspecified observed port path')
    if not event_path.exists():
        # Desired-speed shape trials have their own native extraction layout.
        raise FileNotFoundError(event_path)
    departures=Counter((10*((int(float(r['time_s']))-1)//10),str(r['connector']))
        for r in e.rows(event_path) if r['kind']=='departure')
    def state(t,c,g):
        lanes=range(1,int(sum(widths[c]))+1) if len(widths[c])==1 else ([g+1] if g<2 else range(3,int(sum(widths[c]))+1))
        rows=[moments[t,c,str(l)] for l in lanes if (t,c,str(l)) in moments]
        n=sum(r['n'] for r in rows)
        return (n,sum(r['n']*r['speed_mean'] for r in rows)/n if n else None)
    samples=[]
    geometry={r['cell']:r for r in data.geometry['cells'] if r['road']=='FW_E'}
    for t in range(900,2991,10):
        for c in range(5,21 if include_downstream else 15):
            for g in range(len(widths[c])):
                n,v=state(t,c,g);nt,vt=state(t+10,c,g)
                if v is None or vt is None:continue
                us=[(row[g],state(t,c-1,k)[1]) for k,row in enumerate(matrix[c-1]) if row[g]]
                if any(x is None for _,x in us):continue
                up=sum(w*x for w,x in us)/sum(w for w,x in us) if us else v
                local_rho=n/(geometry[c]['length_km']*widths[c][g])
                down=(sum(w*state(t,c+1,k)[0]/(geometry[c+1]['length_km']*widths[c+1][k])
                    for k,w in enumerate(matrix[c][g]))/sum(matrix[c][g])
                    if c<len(matrix) and sum(matrix[c][g]) else local_rho)
                merge=sum(departures[t,str(model.ramps[r]['connector'])]*spec['weights'][g]/sum(spec['weights'])
                    for r,spec in geo['ramp_access'].items() if spec['cell']==c)
                row=net.freeway_segment_params['FW_E'][c]
                samples.append({'time_s':t,'cell':c,'group':g,'n':n,'target':vt,'v':v,'up':up,'down':down,
                    'rho':n/(geometry[c]['length_km']*widths[c][g]),'length':geometry[c]['length_km'],
                    'width':widths[c][g],'merge_veh':merge,'vfree':row.get('v_free',net.v_free),
                    'critical':row.get('rho_crit',net.rho_crit),'a':net.metanet_a_m,'v_min':net.v_min,
                    'cap':100. if arm=='vsl' and t>=2400 and 5<=c<=9 else math.inf})
    return samples


def predict(rows,p):
    vf,rc,tau,nu,kappa,delta=p
    a={k:np.array([r[k] for r in rows]) for k in rows[0]}
    desired=a['vfree']*vf*np.exp(-((a['rho']/(a['critical']*rc))**a['a'])/a['a'])
    desired=np.minimum(desired,a['cap'])
    return np.maximum(a['v_min'],a['v']+10/tau*(desired-a['v'])+
        (10/3600)/a['length']*a['v']*(a['up']-a['v'])-
        nu*10/tau/a['length']*(a['down']-a['rho'])/(a['rho']+kappa)-
        delta*a['merge_veh']*a['v']/(a['length']*a['width']*(a['rho']+kappa)))


def stats(rows,p):
    y=np.array([r['target'] for r in rows]);v=np.array([r['v'] for r in rows]);f=predict(rows,p)
    return {'samples':len(rows),'rmse':float(np.sqrt(np.mean((f-y)**2))),
            'bias':float(np.mean(f-y)),'persistence_rmse':float(np.sqrt(np.mean((v-y)**2)))}


def main():
    out=HERE/'local_speed_fit_v2';out.mkdir(exist_ok=False)
    old=e.load(LANE/'qualification_v6/parameters.json')['parameters'];p0=[old['by_direction']['FW_E'][k] for k in NAMES]
    banks={(23,'none'):records(23,'none'),(23,'vsl'):records(23,'vsl'),(33,'none'):records(33,'none')}
    train=[r for r in banks[23,'none'] if r['time_s']<2400]
    y=np.array([r['target'] for r in train])
    lower=np.array([.65,.6,12,3,5,0]);upper=np.array([1.25,1.4,60,90,120,1])
    selected=np.array(p0);best=float(np.mean((predict(train,selected)-y)**2));trace=[]
    # Small deterministic coordinate search, not a global-optimality claim.
    for scale in [1.,.5,.25,.125]:
        for sweep in range(2):
            for j,step in enumerate([.08,.2,12.,20.,30.,.4]):
                options=[]
                for direction in [-1,1]:
                    trial=selected.copy();trial[j]=np.clip(trial[j]+direction*step*scale,lower[j],upper[j])
                    loss=float(np.mean((predict(train,trial)-y)**2))
                    trace.append({'parameters':trial.tolist(),'mse':loss});options.append((loss,trial))
                loss,trial=min(options,key=lambda x:x[0])
                if loss<best:best,selected=loss,trial
    params=dict(zip(NAMES,map(float,selected)));result={'fit':params,'train':stats(train,selected),
        'old_train':stats(train,p0),'mse':best,'search':'96 bounded coordinate evaluations; no global-optimality claim',
        'nfev':len(trace),'validation':{}}
    for (s,a),rows in banks.items():
        selection=[r for r in rows if r['time_s']>=2400] if s==23 else rows
        result['validation'][f'{s}_{a}']={'baseline':stats(selection,p0),'fitted':stats(selection,selected)}
    old['by_direction']['FW_E'].update(params)
    e.save(out/'parameters.json',{'parameters':old});e.save(out/'result.json',result);e.save(out/'trace.json',trace)
    print(result,flush=True)


if __name__=='__main__':main()
