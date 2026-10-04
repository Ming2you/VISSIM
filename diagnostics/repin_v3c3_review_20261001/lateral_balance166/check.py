"""Compare observed endpoint lane transfers with saved model lane balances.

No FZP read, traffic rollout, fit or production mutation. Cross-cell/lane
changes are retained as ambiguous events, never counted as same-cell changes.
"""
import collections
import math
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE=Path(__file__).resolve().parent
CELLS=range(19,26)
LANES=range(1,4)
WINDOWS=((2670.1,2820.1),(2820.1,2970.1),(2970.1,3120.1))


def main():
    assert not (HERE/'protocol.json').exists()
    protected=h.read(h.R/'convection165/protocol.json')
    pins={str(Path(__file__)):h.sha(__file__)}
    def read(path):pins[str(path)]=h.sha(path);return h.read(path)
    h.save(HERE/'protocol.json',dict(previous_goal_turn='PROGRESS162--165',
        question='Does constant lateral exchange materially misallocate inventory or VSL lane-transfer response in19--25?',
        scope='Existing67release110/90 native5s frames and frozen148/164 one-second model histories only.',
        prior=['108 route-alignment fix failed VSL response','92 aggregate extra-state regression small gain',
               '114 corrected stopped-population labels failed','133 accepted momentum failed',
               '154 lane-specific ramp gap failed','Claude P_PLANT/structural review'],
        budget=dict(new_rollouts=0,new_fits=0,native=0,FZP=0),
        limits='Native5s endpoint same-cell lane changes are net observable transfers, not complete microscopic lane-change counts. Cross-cell plus lane-change events kept separate; cannot assign their lane change location. At18->19 map native upstream lanes2/3/4 to groups1/2/3 according to verified physical inlet; other outside-region lane comparisons remain unclassified. Missing frames are observed appearance/disappearance, not automatically births/exits. Model lane residual is exact under its own recorded flows, not native causal attribution.',
        next_rule='Locate >=5veh/150s lane-net or paired-response discrepancies before considering a new exchange law. Smaller net errors cannot exclude gross exchange or speed-mixing effects. No automatic fit or law adoption.',
        protected_sha256=protected['protected_sha256'],STOP=protected['STOP']))
    h.save(HERE/'status.json',dict(status='running'))
    native_rows=[];model_rows=[];witnesses=[];initials={};native_checks=0;matrix_checks=0;max_matrix_error=0.;max_cell_sum=0.
    for arm in ('release','release_vsl90'):
        doc=read(h.F/f'flow67/{arm}_frames.json.gz');fields=doc['fields']
        frames={round(float(t),6):{str(vid):dict(zip(fields,r)) for vid,r in frame.items()} for t,frame in doc['frames'].items()}
        ts=sorted(frames);assert len(ts)==91 and abs(ts[0]-2670.1)<1e-6 and abs(ts[-1]-3120.1)<1e-6
        initials[arm]=collections.Counter((r['cell'],r['lane']) for r in frames[ts[0]].values())
        for t,u in zip(ts,ts[1:]):
            assert abs(u-t-5)<1e-6
            a,b=frames[t],frames[u]
            start=collections.Counter((r['cell'],r['lane']) for r in a.values())
            end=collections.Counter((r['cell'],r['lane']) for r in b.values())
            changes=collections.defaultdict(collections.Counter)
            for vid in a.keys()|b.keys():
                x,y=a.get(vid),b.get(vid)
                if x and y:
                    sx,sy=(x['cell'],x['lane']),(y['cell'],y['lane'])
                    if sx==sy:continue
                    if x['cell']==y['cell']:
                        changes[sx]['lateral_out']+=1;changes[sy]['lateral_in']+=1
                    else:
                        changes[sx]['long_out']+=1;changes[sy]['long_in']+=1
                        xg,yg=x['lane'],y['lane']
                        comparable=x['cell'] in CELLS and y['cell'] in CELLS
                        if x['cell']==18 and y['cell']==19:
                            xg={2:1,3:2,4:3}.get(x['lane'])
                            comparable=xg is not None
                        if not comparable:
                            changes[sx]['boundary_unclassified_depart']+=1
                            changes[sy]['boundary_unclassified_arrive']+=1
                        elif xg!=yg:
                            changes[sx]['ambiguous_depart']+=1;changes[sy]['ambiguous_arrive']+=1
                            if x['cell'] in CELLS or y['cell'] in CELLS:
                                witnesses.append(dict(arm=arm,t=t,vehicle=vid,source=sx,destination=sy))
                elif x:changes[x['cell'],x['lane']]['disappear']+=1
                else:changes[y['cell'],y['lane']]['appear']+=1
            for cell in CELLS:
                assert sum(changes[cell,g]['lateral_in']-changes[cell,g]['lateral_out'] for g in LANES)==0
                for lane in LANES:
                    z=changes[cell,lane];lat=z['lateral_in']-z['lateral_out']
                    balance=start[cell,lane]+lat+z['long_in']-z['long_out']+z['appear']-z['disappear']
                    assert balance==end[cell,lane];native_checks+=1
                    native_rows.append(dict(arm=arm,lo=t,hi=u,cell=cell,lane=lane,n0=start[cell,lane],n1=end[cell,lane],
                        net_lateral=lat,**{k:z[k] for k in ['lateral_in','lateral_out','long_in','long_out','appear','disappear','ambiguous_depart','ambiguous_arrive','boundary_unclassified_depart','boundary_unclassified_arrive']}))
        for model,folder in [('148','spatial_context148'),('164','merge_restore164')]:
            doc=read(h.R/f'{folder}/forecast/training/s67_late_{arm}.json.gz')
            d=doc['diagnostics']['roads'][0]['joint_lane_region']
            assert d['specification']['off_access']=={'10483':0}
            assert d['specification']['cells']==list(CELLS)
            assert d['specification']['inlet_lane_to_group']=={'2':0,'3':1,'4':2}
            rates=d['specification']['exchange_rates_per_sec']
            by=collections.defaultdict(dict)
            for r in d['rows']:by[round(r['time_s'],6)][r['cell'],r['lane']]=r
            off={round(r['time_s']+1,6):r['off_accepted_veh'] for r in d['junction_rows']}
            assert len(by)==450
            old={k:float(initials[arm][k]) for k in [(i,g) for i in CELLS for g in LANES]}
            mapping=read(h.F/'route_inventory/mapping31.json')['freeway_model_links']['FW_E']['segment_bounds_m']
            for t,rr in sorted(by.items()):
                for cell in CELLS:
                    before=[old[cell,g]+rr[cell,g]['mainline_in_veh']+rr[cell,g]['merge_veh']-rr[cell,g]['mainline_out_veh']-(off[t] if cell==20 and g==1 else 0.) for g in LANES]
                    net=[rr[cell,g]['n_veh']-before[g-1] for g in LANES]
                    err=abs(sum(net));max_cell_sum=max(max_cell_sum,err);assert err<1e-8
                    # Cell19 uses two separately capacity-constrained subcells;
                    # record its exact net residual, not a false whole-cell matrix.
                    matrix=None
                    if cell!=19:
                        matrix=[[before[g]*(1-math.exp(-sum(rate)))*r/sum(rate) if sum(rate) else 0. for r in rate] for g,rate in enumerate(rates)]
                        storage=180*(mapping[cell+1]-mapping[cell])/1000
                        for k in range(3):
                            total=sum(row[k] for row in matrix)
                            factor=min(1.,max(0.,storage-before[k])/total) if total else 0.
                            for g in range(3):matrix[g][k]*=factor
                        for g in range(3):
                            expected=sum(matrix[k][g] for k in range(3))-sum(matrix[g])
                            err=abs(expected-net[g]);max_matrix_error=max(max_matrix_error,err);assert err<1e-8;matrix_checks+=1
                    for g in LANES:
                        r=rr[cell,g]
                        model_rows.append(dict(model=model,arm=arm,lo=round(t-1,6),hi=t,cell=cell,lane=g,n0=old[cell,g],n1=r['n_veh'],
                            mainline_in=r['mainline_in_veh'],mainline_out=r['mainline_out_veh'],merge=r['merge_veh'],
                            off=off[t] if cell==20 and g==1 else 0.,net_lateral=net[g-1],
                            gross_lateral_in=sum(matrix[k][g-1] for k in range(3)) if matrix else None,
                            gross_lateral_out=sum(matrix[g-1]) if matrix else None))
                old={key:r['n_veh'] for key,r in rr.items()}
    summaries=[]
    for arm in ('release','release_vsl90'):
        for lo,hi in WINDOWS:
            for cell in CELLS:
                for lane in LANES:
                    z=[r for r in native_rows if r['arm']==arm and r['cell']==cell and r['lane']==lane and lo-1e-6<=r['lo']<hi-1e-6]
                    out=dict(arm=arm,lo=lo,hi=hi,cell=cell,lane=lane,native={k:sum(r[k] for r in z) for k in ['net_lateral','lateral_in','lateral_out','long_in','long_out','appear','disappear','ambiguous_depart','ambiguous_arrive','boundary_unclassified_depart','boundary_unclassified_arrive']},models={})
                    assert len(z)==30
                    for model in ('148','164'):
                        m=[r for r in model_rows if r['model']==model and r['arm']==arm and r['cell']==cell and r['lane']==lane and lo-1e-6<=r['lo']<hi-1e-6]
                        assert len(m)==150
                        out['models'][model]={k:sum(r[k] for r in m) for k in ['net_lateral','mainline_in','mainline_out','merge','off']}
                        out['models'][model]['n_error_at_end']=m[-1]['n1']-z[-1]['n1']
                    summaries.append(out)
    response=[]
    for r in summaries:
        if r['arm']!='release':continue
        other=next(z for z in summaries if z['arm']=='release_vsl90' and (z['lo'],z['cell'],z['lane'])==(r['lo'],r['cell'],r['lane']))
        response.append(dict(lo=r['lo'],hi=r['hi'],cell=r['cell'],lane=r['lane'],
            native_net_delta=other['native']['net_lateral']-r['native']['net_lateral'],
            model_net_delta={m:other['models'][m]['net_lateral']-r['models'][m]['net_lateral'] for m in ('148','164')},
            ambiguous_endpoint_transitions=sum(x['native']['ambiguous_depart']+x['native']['ambiguous_arrive'] for x in (r,other))))
    for path,digest in {**pins,**protected['protected_sha256']}.items():assert h.sha(path)==digest,path
    assert h.sha(protected['STOP']['path'])==protected['STOP']['sha256']
    h.save(HERE/'native.json',native_rows);h.save(HERE/'model.json',model_rows);h.save(HERE/'ambiguous.json',witnesses)
    h.save(HERE/'summary.json',summaries);h.save(HERE/'response.json',response)
    h.save(HERE/'verification.json',dict(native_balances=native_checks,model_lateral_matrix_checks=matrix_checks,
        max_matrix_error=max_matrix_error,max_cell_lateral_sum=max_cell_sum,input_sha256=pins,core=True,STOP=True))
    h.save(HERE/'status.json',dict(status='complete_cached_diagnostic',fits=0,forecasts=0,native=0,FZP=0,goal='ACTIVE_NOT_QUALIFIED'))
    for r in summaries:
        if r['lane']==1 and r['cell'] in (19,20,21) and r['lo']==2820.1:print(r)
    print('largest paired net differences',sorted(response,key=lambda r:abs(r['native_net_delta']),reverse=True)[:5])


if __name__=='__main__':main()
