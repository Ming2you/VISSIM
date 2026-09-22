"""Split observed paired arrival-time shifts from downstream travel delays."""
from pathlib import Path
import hashlib
import json
import statistics
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import matched_cohort_response as c

K,e=c.K,c.e
OUT=K/'matched_passage_response_v1'


def passage(car,points):
    trajectory=car['trajectory'];result={}
    for name,position in points.items():
        for index,row in enumerate(trajectory):
            if row is not None and row[0]>=position:
                result[name]=dict(t=2550+index,v=row[1],lane=row[2]);break
    return result


def stats(values):
    return dict(n=len(values),mean=statistics.mean(values) if values else None,
        median=statistics.median(values) if values else None,min=min(values,default=None),max=max(values,default=None))


def main():
    OUT.mkdir(exist_ok=False)
    gp=K/'matched_meter_midpoint_s33_v2/observations/rm8/geometry.json';geometry=e.load(gp)
    cells={r['cell']:r for r in geometry['cells'] if r['road']=='FW_E'}
    points={'merge10490':next(r['chain_pos_m'] for r in geometry['boundaries'] if r['connector']==10490),
            'merge10484':next(r['chain_pos_m'] for r in geometry['boundaries'] if r['connector']==10484),
            'start16':cells[16]['start_m'],'start20':cells[20]['start_m']}
    labels=list(points);results={};sources=[Path(__file__),Path(c.__file__),gp]
    for seed in (23,33):
        bank={}
        for arm in ('rm8','rm6','rm_ramp'):
            path=c.OUT/f's{seed}_{arm}.json';bank[arm]=e.load(path);sources.append(path)
        results[str(seed)]={}
        for arm in ('rm6','rm_ramp'):
            paired=[]
            for vid,base in bank['rm8']['cars'].items():
                if base['initial_cell']>12:continue
                controlled=bank[arm]['cars'][vid]
                a,b=passage(base,points),passage(controlled,points)
                if len(a)<len(points) or len(b)<len(points):continue
                # Only continuously observed mainline passages: no exit/reentry shortcut.
                for car,row in ((base,a),(controlled,b)):
                    assert all(v is not None for v in car['trajectory'][row['merge10490']['t']-2550:row['start20']['t']-2550+1])
                shifts={p:b[p]['t']-a[p]['t'] for p in points}
                legs={x+'_'+y:shifts[y]-shifts[x] for x,y in zip(labels,labels[1:])}
                assert sum(legs.values())==shifts['start20']-shifts['merge10490']
                paired.append(dict(vehicle=int(vid),baseline=a,controlled=b,arrival_shifts_s=shifts,
                                   travel_time_shifts_s=legs,speed_shifts_kmh={p:b[p]['v']-a[p]['v'] for p in points}))
            row=dict(matched_completed_passages=len(paired),
                arrival_shifts_s={p:stats([r['arrival_shifts_s'][p] for r in paired]) for p in points},
                travel_time_shifts_s={x+'_'+y:stats([r['travel_time_shifts_s'][x+'_'+y] for r in paired]) for x,y in zip(labels,labels[1:])},
                speed_shifts_kmh={p:stats([r['speed_shifts_kmh'][p] for r in paired]) for p in points},pairs=paired)
            results[str(seed)][arm]=row
            print(json.dumps(dict(seed=seed,arm=arm,n=len(paired),arrival={p:r['mean'] for p,r in row['arrival_shifts_s'].items()},
                travel={p:r['mean'] for p,r in row['travel_time_shifts_s'].items()},speed={p:r['mean'] for p,r in row['speed_shifts_kmh'].items()})),flush=True)
    e.save(OUT/'result.json',dict(qualified=False,future_inputs_to_model=False,new_native_runs=0,points_m=points,cases=results,
        limitations=['Post-run explanation,not a forecast or new calibration.',
            'Initial cells0-12 only; both runs must reach all four points by3000. Completion conditioning excludes censored/exit vehicles.',
            'Do not substitute these conditional mean travel times for full-component TTT or a causal contribution estimate.',
            'Native1s frame crossing times; no subsecond interpolation or interaction-target inference.'],
        source_pins={p.relative_to(e.ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}))


def initial_rm_passage():
    """Current 31-cell RM benefit: common initial IDs, not newly generated IDs.

    Retrospective identification only. No observation is passed into a forecast.
    The original 2550s experiment above and its outputs remain unchanged.
    """
    import bisect
    import csv
    import gzip
    import numpy as np
    B=K.parent/'segment_resolution_20260921'
    sys.path.insert(0,str(B))
    import calibrate as cal
    from prepare import native,save,table
    out=B/'matched_rm_passage_v1'
    assert out.is_dir() and not (out/'protocol.json').exists()
    sources=e.load(B/'sources.json');geo=e.load(B/'geometry_200_branch_guard.json')
    chain={r['link']:r for r in geo['chains']['FW_E']};bounds=geo['bounds']['FW_E']
    points={f'merge{x}':next(p['chain_pos_m'] for p in geo['boundaries'] if p['connector']==x)
            for x in (10490,10484)}
    points.update(after_ramps=bounds[25],end26=bounds[27],start_terminal=bounds[30])
    arms=('none','rm_ramp');start,end=2400,2850
    pins=[Path(__file__),B/'sources.json',B/'geometry_200_branch_guard.json',Path(cal.__file__),Path(native.__file__)]
    save(out/'protocol.json',dict(initial_s=start,end_s=end,arms=arms,seed=23,points_m=points,
        common_initial_only=True,new_native=0,new_forecasts=0,qualification=False,
        definition='End-second geometric mainline residence; conditional common completed passages separately reported.',
        sources={str(p.relative_to(e.ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in pins}))
    data={};initial={};proofs={};observed={};histories={}
    for arm in arms:
        proof={};spec=sources[arm+'_s23'];path=e.ROOT/spec['path']
        n=np.zeros((451,31));mom=n.copy();cohort=n.copy();history={};first={};rows=0
        for t,frame in native.native(path,proof):
            if not start<=t<=end:continue
            rows+=1;located={}
            for vid,r in frame.items():
                if r.link not in chain:continue
                x=chain[r.link]['offset_m']+r.pos
                if not 0<=x<bounds[-1]:continue
                cell=bisect.bisect_right(bounds,x)-1
                located[vid]=[t,x,cell,r.lane,r.speed,r.link]
                n[t-start,cell]+=1;mom[t-start,cell]+=r.speed
            if t==start:
                first=located.copy();history={vid:[] for vid in first}
            for vid in first.keys() & located.keys():
                row=located[vid];history[vid].append(row);cohort[t-start,row[2]]+=1
        assert rows==451 and proof['file_sha256']==spec['file_sha256']
        assert proof['prefix2249_2400_original9_sha256']==spec['prefix2249_2400_original9_sha256']
        assert int(cohort[1:].sum())==sum(len(rs)-1 for rs in history.values())
        cache=B/('calibration_v1/observed_none.npz' if arm=='none' else 'downstream_calibration_v1/observed_rm_ramp.npz')
        obs=dict(np.load(cache));pins.append(cache)
        assert np.allclose(n[1:].reshape(15,30,31).mean(1),obs['n'].sum(2),atol=1e-10,rtol=0)
        assert np.allclose(mom[1:].reshape(15,30,31).mean(1),obs['mom'].sum(2),atol=1e-9,rtol=0)
        np.savez_compressed(out/(arm+'_1s.npz'),n=n,mom=mom,initial_cohort=cohort)
        (out/(arm+'_initial_paths.json.gz')).write_bytes(gzip.compress(json.dumps(history,separators=(',',':')).encode()))
        initial[arm]=first;histories[arm]=history;proofs[arm]=proof;observed[arm]=obs
        cross=K.parent/f'lever_mechanisms_20260921/v2/{arm}_s23/crossings.csv';pins.append(cross)
        with cross.open() as stream:
            exits={int(r['vehicle']):r for r in csv.DictReader(stream)
                   if start<float(r['time_s'])<=end and r['kind'] in ('off_entry','terminal_inferred','removal','unverified_loss')}
        data[arm]=dict(n=n,mom=mom,cohort=cohort,exits=exits)
        print(arm,'native hash, 451 frames and existing 30s cache verified',flush=True)
    assert initial['none']==initial['rm_ramp']
    per_vehicle=[];pairs=[];groups={};labels=list(points)
    for vid,original in sorted(initial['none'].items()):
        values={};crossing={};modes={};first_difference=None
        for arm in arms:
            rs=histories[arm][vid];values[arm]=len(rs)-1
            event=data[arm]['exits'].get(vid)
            modes[arm]=None if event is None else (event['kind'],event['connector'])
            crossing[arm]={name:next((r[0] for r in rs if r[1]>=x),None) for name,x in points.items()}
            crossing[arm]['terminal']=int(float(event['time_s'])) if event and event['kind']=='terminal_inferred' else None
        a={r[0]:r for r in histories['none'][vid]};z={r[0]:r for r in histories['rm_ramp'][vid]}
        for t in sorted(a.keys() & z.keys()):
            if a[t]!=z[t]:
                first_difference=dict(time_s=t,base=a[t],controlled=z[t]);break
        group='initial_before10490' if original[1]<points['merge10490'] else 'initial_after10490'
        counter=groups.setdefault(group,dict(vehicles=0,residence_delta_s=0,completed_both=0,exit_changes=0,censored=0))
        counter['vehicles']+=1;counter['residence_delta_s']+=values['rm_ramp']-values['none']
        if all(modes.values()):
            counter['completed_both']+=1;counter['exit_changes']+=modes['none']!=modes['rm_ramp']
        else:counter['censored']+=1
        record=dict(vehicle=vid,initial_cell=original[2],initial_x=original[1],group=group,
            residence_s=values,delta_s=values['rm_ramp']-values['none'],exit_modes=modes,
            crossings=crossing,first_difference=first_difference)
        per_vehicle.append(record)
        if group=='initial_before10490' and all(t is not None for row in crossing.values() for t in row.values()):
            for arm in arms:
                rs=histories[arm][vid]
                assert all(y[0]==x[0]+1 for x,y in zip(rs,rs[1:])),(arm,vid,'exit/reentry')
                assert crossing[arm]['terminal']==rs[-1][0]+1
            shifts={k:crossing['rm_ramp'][k]-crossing['none'][k] for k in labels+['terminal']}
            legs={x+'_'+y:shifts[y]-shifts[x] for x,y in zip(labels,labels[1:]+['terminal'])}
            assert sum(legs.values())==shifts['terminal']-shifts['merge10490']
            assert shifts['terminal']==record['delta_s']
            pairs.append(dict(vehicle=vid,arrival_shifts_s=shifts,travel_time_shifts_s=legs))
    save(out/'vehicles.json',per_vehicle);save(out/'pairs.json',pairs)
    assert sum(r['delta_s'] for r in per_vehicle)==int((data['rm_ramp']['cohort'][1:]-data['none']['cohort'][1:]).sum())
    predicted={}
    for arm in arms:
        p=B/f'receiving_speed_v1/rs20260921_disabled/refined_guard1_{arm}.json.gz';pins.append(p)
        predicted[arm]=cal.predicted(json.loads(gzip.decompress(p.read_bytes())))
    cells=[]
    for j in range(15):
        for i in range(31):
            sl=slice(j*30+1,j*30+31)
            nv={a:float(data[a]['n'][sl,i].sum()) for a in arms}
            cv={a:float(data[a]['cohort'][sl,i].sum()) for a in arms}
            cells.append(dict(start_s=start+30*j,cell=i,end_m=bounds[i+1],
                actual_delta_ttt=(nv['rm_ramp']-nv['none'])/3600,
                initial_delta_ttt=(cv['rm_ramp']-cv['none'])/3600,
                later_delta_ttt=((nv['rm_ramp']-cv['rm_ramp'])-(nv['none']-cv['none']))/3600,
                predicted_delta_ttt=float((predicted['rm_ramp']['n'][j,i]-predicted['none']['n'][j,i]).sum()/120),
                actual_delta_q=None if i==30 else float(observed['rm_ramp']['q'][j,i]-observed['none']['q'][j,i]),
                predicted_delta_q=float(predicted['rm_ramp']['q'][j,i]-predicted['none']['q'][j,i])))
    table(out/'cell_time_response.csv',cells)
    total=sum(r['actual_delta_ttt'] for r in cells)
    check=e.load(B/'receiving_speed_v1/boundary_moments.json')
    save(out/'boundary_reference.json',check) # independent prior identity kept inspectable
    summary=dict(qualified=False,new_native=0,new_forecasts=0,initial_vehicles=len(per_vehicle),groups=groups,
        initial_cohort_delta_ttt=sum(r['delta_s'] for r in per_vehicle)/3600,mainline_delta_ttt=total,
        later_entrant_delta_ttt=sum(r['later_delta_ttt'] for r in cells),
        completed_pairs=len(pairs),arrival_shifts_s={p:stats([r['arrival_shifts_s'][p] for r in pairs]) for p in labels+['terminal']},
        travel_time_shifts_s={p:stats([r['travel_time_shifts_s'][p] for r in pairs]) for p in pairs[0]['travel_time_shifts_s']},
        first_initial_difference=min((r for r in per_vehicle if r['first_difference']),key=lambda r:r['first_difference']['time_s']),
        limitations=['Future trajectory is post-run evidence, not a forecast input.',
            'Common-completed upstream cohort is conditional; censored/other exits excluded only from passage means, never TTT.',
            'Arrival/travel decomposition is accounting, not independent causal attribution.',
            'Terminal events are geometrically inferred; no full-Omega deletion or GNE claim.'])
    save(out/'results.json',summary);save(out/'native_proofs.json',proofs)
    save(out/'verification.json',dict(source_pins={str(p.relative_to(e.ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in pins},
        original_hashes_exact=True,initial_mainline_exact=True,seconds_per_arm=451,native_30s_caches_exact=True,
        cohort_residence_exact=True,passage_shift_identity_exact=True,new_native=0,new_forecasts=0))
    print(json.dumps(summary,ensure_ascii=False),flush=True)


def verify_initial_rm_passage():
    """Independent stock check against the prior native boundary-event ledger."""
    import ast
    import csv
    import gzip
    import numpy as np
    B=K.parent/'segment_resolution_20260921';out=B/'matched_rm_passage_v1'
    result=e.load(out/'results.json');records=e.load(out/'vehicles.json')
    proofs=e.load(out/'native_proofs.json');ids={r['vehicle'] for r in records}
    reference=e.load(B/'receiving_speed_v1/boundary_moments.json')['rows']
    archive=out/'before_matched_passage_response.py.txt'
    # The original entry point is retained. Compare its two function ASTs,
    # rather than silently claiming that the edited helper hash is unchanged.
    def old_functions(path):
        tree=ast.parse(path.read_text(encoding='utf-8'))
        return {n.name:ast.dump(n,include_attributes=False) for n in tree.body
                if isinstance(n,ast.FunctionDef) and n.name in ('passage','stats','main')}
    assert old_functions(Path(__file__))==old_functions(archive)
    sources=[Path(__file__),archive,out/'results.json',out/'vehicles.json',out/'native_proofs.json']
    checks={};by_initial={}
    for arm in ('none','rm_ramp'):
        npz=out/(arm+'_1s.npz');hp=out/(arm+'_initial_paths.json.gz')
        raw=dict(np.load(npz));paths=json.loads(gzip.decompress(hp.read_bytes()))
        cp=K.parent/f'lever_mechanisms_20260921/v2/{arm}_s23/crossings.csv'
        with cp.open() as stream:events=[r for r in csv.DictReader(stream) if 2400<float(r['time_s'])<=2850]
        inflow=np.zeros(451);outflow=np.zeros(451);cohort_out=np.zeros(451)
        for r in events:
            t=int(float(r['time_s']))-2400;v=int(r['vehicle'])
            assert r['kind'] in ('source','merge','off_entry','terminal_inferred'),r
            if r['kind'] in ('source','merge'):inflow[t]+=1;assert v not in ids,'Initial mainline vehicle re-entered'
            else:
                outflow[t]+=1;cohort_out[t]+=v in ids
        assert np.array_equal(raw['n'].sum(1),len(ids)+np.cumsum(inflow-outflow))
        assert np.array_equal(raw['initial_cohort'].sum(1),len(ids)-np.cumsum(cohort_out))
        residence=raw['n'][1:].sum()/3600
        assert abs(residence-reference['native:'+arm]['ttt'])<1e-10
        for vid,rs in paths.items():
            assert all(y[0]==x[0]+1 for x,y in zip(rs,rs[1:])),(arm,vid)
            record=next(r for r in records if r['vehicle']==int(vid))
            assert len(rs)-1==record['residence_s'][arm]
        checks[arm]=dict(mainline_seconds=451,initial_cohort_seconds=451,vehicle_paths=len(paths),
            residence_veh_h=float(residence),native_sha256=proofs[arm]['file_sha256'])
        sources.extend([npz,hp,cp])
    for cell in range(31):
        selected=[r for r in records if r['initial_cell']==cell]
        by_initial[str(cell)]=dict(vehicles=len(selected),delta_s=sum(r['delta_s'] for r in selected))
    # Independent exit-time identity, including right-censored vehicles.
    changed=0;censored=0;exit_delta=0
    for r in records:
        for arm in ('none','rm_ramp'):
            t=r['crossings'][arm]['terminal']
            if t is not None:assert r['residence_s'][arm]==t-2401
        both=all(r['exit_modes'].values())
        changed+=both and r['exit_modes']['none']!=r['exit_modes']['rm_ramp']
        censored+=not both
        exit_delta+=r['delta_s']
    assert changed==0 and abs(exit_delta/3600-result['initial_cohort_delta_ttt'])<1e-12
    e.save(out/'independent_validation.json',dict(passed=True,qualified=False,checks=checks,
        unchanged_original_function_ast=True,changed_observed_exits=changed,censored_vehicles=censored,
        delta_by_initial_cell=by_initial,source_pins={str(p.relative_to(e.ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}))
    print(json.dumps(dict(passed=True,checks=checks,changed_exits=changed,censored=censored)),flush=True)


if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='initial-rm':initial_rm_passage()
    elif len(sys.argv)>1 and sys.argv[1]=='verify-initial-rm':verify_initial_rm_passage()
    else:main()
