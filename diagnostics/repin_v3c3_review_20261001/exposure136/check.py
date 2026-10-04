"""Audit saved, unchanged rollouts and cached native sign passage; no forecasts."""
import collections
import math
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE=Path(__file__).resolve().parent


def main():
    assert not (HERE/'verification.json').exists(), 'Preserve prior audit'
    protocol=h.read(HERE/'protocol.json');pins={str(Path(__file__)):h.sha(__file__)}
    groups=[];target_error=mass_error=previous_trace_error=0.;total=0
    for arm in ('release','release_vsl90'):
        path=HERE/f'frozen132_{arm}_speed.json.gz';pins[str(path)]=h.sha(path)
        rows=h.read(path);old=h.read(h.R/'post_onset135'/path.name)
        assert len(rows)==len(old)==9450
        by_state=collections.defaultdict(list);by_group=collections.defaultdict(list)
        for x,y in zip(rows,old):
            assert all(x[k]==v for k,v in y.items()), 'Read-only trace differs'
            total+=1;p=x['segment_parameters'];rho=x['rho'];nom=p['v_free']*math.exp(-(rho/p['rho_crit'])**p['metanet_a_m']/p['metanet_a_m'])
            assert x['vsl_fd_response']==dict(law='carlson',A=.5,E=2.,alpha=0.)
            reconstructed=0.;stock=sum(x['cohorts'].values())
            for command,n in x['cohorts'].items():
                b=float(command)/x['maximum'];critical=p['rho_crit']*(1+.5*(1-b));shape=p['metanet_a_m']*(2-b)
                reconstructed+=n*p['v_free']*b*math.exp(-(rho/critical)**shape/shape)
            if stock>1e-12:
                err=abs(reconstructed/stock-x['target']);target_error=max(target_error,err);assert err<1e-9
            frac=sum(n for command,n in x['cohorts'].items() if float(command)<x['maximum']-.5)/stock if stock else 0.
            # target is computed from t-start state, although trace timestamp is t-end.
            t=round(x['time_s']-1,6);block=int(round(t-2670.1))//150
            assert 0<=block<3
            entry=dict(time_s=t,cell=x['cell'],lane=x['lane'],n=x['n_veh'],target=x['target'],nominal=nom,
                target_delta=x['target']-nom,limited_fraction=frac,speed=x['old_speed'],cap=x['exit_cap'] is not None)
            by_group[block,x['cell'],x['lane']].append(entry);by_state[t,x['cell']].append(x)
        for key,rr in by_state.items():
            assert len(rr)==3 and all(x['cohorts']==rr[0]['cohorts'] for x in rr)
            err=abs(sum(rr[0]['cohorts'].values())-sum(x['n_veh'] for x in rr));mass_error=max(mass_error,err);assert err<1e-7
        for (block,cell,lane),rr in sorted(by_group.items()):
            assert len(rr)==150
            n=sum(x['n'] for x in rr)
            groups.append(dict(arm=arm,block=block,cell=cell,lane=lane,samples=len(rr),
                means={k:sum(x[k] for x in rr)/len(rr) for k in ('n','target','nominal','target_delta','limited_fraction','speed','cap')},
                vehicle_weighted_limited_fraction=sum(x['n']*x['limited_fraction'] for x in rr)/n if n else None))
    h.save(HERE/'model_groups.json',groups)
    geometry=h.F/'vsl_native_exposure/protocol.json';pins[str(geometry)]=h.sha(geometry)
    signs=h.read(geometry)['signs'];active={s['x_m'] for s in signs if s['no'] in (63,64,65,66)}
    restore={s['x_m'] for s in signs if s['no'] in (67,68,69)}
    assert len(active)==len(restore)==1;start_sign=active.pop();end_sign=restore.pop()
    path=h.F/'flow67/release_vsl90_frames.json.gz';pins[str(path)]=h.sha(path);native=h.read(path)
    assert native['fields']==['cell','speed_kmh','x_m','lane','acceleration_mps2','desired_speed_kmh']
    frames=native['frames'];tags={};last={};native_groups=collections.defaultdict(list);snapshots=[]
    for stamp,frame in sorted(frames.items(),key=lambda a:float(a[0])):
        t=round(float(stamp),6);current=[]
        for vid,row in frame.items():
            cell,speed,pos,lane,acc,desired=row
            tag=tags.get(vid)
            if t==2670.1 or pos<start_sign or pos>=end_sign:tag=110
            elif vid in last:
                prev_t,previous=last[vid]
                if abs(t-prev_t-5)<1e-7 and previous[2]<start_sign<=pos:
                    tag=90 if prev_t>=2700 else 110 if t<=2700 else None
            else:
                # New in-zone appearances may be ramp arrivals. Do not infer
                # their desired-speed command from overlapping distributions.
                tag=None
            tags[vid]=tag
            if 19<=cell<=25:
                current.append(dict(cell=cell,lane=lane,tag=tag,desired=desired))
                if t<3120.1:
                    block=int(round(t-2670.1))//150
                    native_groups[block,cell,lane].append(dict(tag=tag,desired=desired))
        snapshots.append(dict(time_s=t,cells=[dict(cell=i,n=sum(x['cell']==i for x in current),
            limited=sum(x['cell']==i and x['tag']==90 for x in current),unknown=sum(x['cell']==i and x['tag'] is None for x in current)) for i in range(19,26)]))
        last={vid:(t,row) for vid,row in frame.items()}
    native_rows=[]
    for (block,cell,lane),rr in sorted(native_groups.items()):
        n=len(rr);lower=sum(x['tag']==90 for x in rr)/n;unknown=sum(x['tag'] is None for x in rr)/n
        native_rows.append(dict(block=block,cell=cell,lane=lane,vehicle_snapshots=n,limited_lower=lower,
            limited_upper=lower+unknown,unknown=unknown,mean_desired_kmh=sum(x['desired'] for x in rr)/n))
    h.save(HERE/'native_exposure.json',dict(sign_m=start_sign,restore_m=end_sign,command_change_s=2700.,groups=native_rows,snapshots=snapshots,
        limits='Geometric passage inference from5s frames, not exact command timestamps. Brackets crossing2700 and new in-zone appearances remain unknown. Initial stock110; cached command/readback history reused. No cross-arm matching of newly generated IDs. Native future samples never enter rollout.'))
    for p,digest in {**protocol['protected_sha256'],**protocol['input_sha256'],**pins}.items():assert h.sha(p)==digest,p
    assert h.sha(protocol['STOP']['path'])==protocol['STOP']['sha256']
    h.save(HERE/'verification.json',dict(target_rows=total,target_reconstruction_max_error=target_error,cohort_mass_max_error=mass_error,
        previous135_all_trace_fields_exact=True,original_physical_tables_exact=all(all(v.values()) for v in h.read(HERE/'parity.json').values()),
        core=True,STOP=True,pins=pins,new_native=0,new_FZP=0,new_fit=0))
    print('Verified',total,'targets, target error',target_error,'cohort mass error',mass_error)
    for x in groups:
        if x['arm']=='release_vsl90' and x['block']==1 and x['lane']==1:
            y=next(y for y in native_rows if (y['block'],y['cell'],y['lane'])==(x['block'],x['cell'],x['lane']))
            print(x['cell'],x['means']['target_delta'],x['vehicle_weighted_limited_fraction'],y['limited_lower'],y['limited_upper'])


if __name__=='__main__':main()
