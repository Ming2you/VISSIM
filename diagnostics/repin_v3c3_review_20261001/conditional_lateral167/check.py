"""One future-conditioned lateral-transfer diagnostic, never a controller model."""
import copy
import gzip
import json
import math
import time
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h
from diagnostics.repin_v3c3_review_20261001.jin_macro111 import run as common

HERE=Path(__file__).resolve().parent


def main():
    assert not (HERE/'status.json').exists()
    protected=h.read(h.R/'convection165/protocol.json')
    pins={str(Path(__file__)):h.sha(__file__)}
    def read(p):pins[str(p)]=h.sha(p);return h.read(p)
    source=read(h.R/'spatial_context148/forecast/executed_function_sources.json')
    old='''            matrix = []
            for g,rates in enumerate(self.rates):
                hazard = sum(rates)
                matrix.append([ns[g]*(1.-math.exp(-hazard*dt*3600))*r/hazard if hazard else 0. for r in rates])
'''
    new='''            matrix = _lateral167_matrix(self, i, ns, state.time_sec, dt*3600)
'''
    assert source['RouteLaneRegion'].count(old)==1
    changed=dict(source,RouteLaneRegion=source['RouteLaneRegion'].replace(old,new))
    assert all(changed[k]==v for k,v in source.items() if k!='RouteLaneRegion')
    h.save(HERE/'executed_function_sources.json',changed)
    protocol=dict(previous_goal_turn='PROGRESS162--165;166 current cached lane balance completed.',
        hypothesis='Missing state-dependent lateral redistribution20--25 may affect both recovery and VSL response.',
        scope='One baseline148 parity, then67release110/90 two450s future-conditioned diagnostics, no fit.',
        treatment='For each observed5s interval, same-cell endpoint transfers g->k divided by donor native startN and5s give per-second transfer fraction. Multiply by model donor stock; retain actual receiving-space cap, destination classes, speed moment transport. Cell19 split lateral law unchanged.',
        limitations='Native5s cross-cell+lane changes excluded; fractions are a partial endpoint-transfer proxy, not full microscopic hazard. All future lane transfers are diagnostic conditioning, not autonomous validation, causal attribution, a rigorous best-case bound, or a plant to deploy. No command-specific bonus or new parameter is calibrated.',
        budget=dict(parity450=1,conditional450=2,new_fits=0,native=0,FZP=0,push=0),
        next_rule='Compare VSL discharge/TTT response, actual mass and redistribution. Improvement would justify current-state closure identification, not adoption. A failure does not exclude unobserved boundary lane changes or all lateral mechanisms.',
        protected_sha256=protected['protected_sha256'],STOP=protected['STOP'])
    h.save(HERE/'protocol.json',protocol)
    schedules={}
    for arm in ('release','release_vsl90'):
        doc=read(h.F/f'flow67/{arm}_frames.json.gz');fields=doc['fields']
        frames={round(float(t),6):{str(vid):dict(zip(fields,r)) for vid,r in f.items()} for t,f in doc['frames'].items()}
        ts=sorted(frames);schedule={}
        for t,u in zip(ts,ts[1:]):
            n={i:[0]*3 for i in range(20,26)}
            moves={i:[[0]*3 for _ in range(3)] for i in range(20,26)}
            for vid,x in frames[t].items():
                cell=x['cell']
                if cell not in n:continue
                g=x['lane']-1;n[cell][g]+=1
                y=frames[u].get(vid)
                if y and y['cell']==cell and y['lane']!=x['lane']:moves[cell][g][y['lane']-1]+=1
            for i in n:
                assert all(sum(moves[i][g])<=n[i][g] for g in range(3))
                for g in range(3):
                    for k in range(3):assert not moves[i][g][k] or n[i][g]>0
            schedule[t]={i:[[a/(5*n[i][g]) if n[i][g] else 0. for a in moves[i][g]] for g in range(3)] for i in n}
        schedules[arm]=schedule
    context,replay,Obs=common.setup()
    from evaluation.controllers import lane_plant_runtime as lpr,physical_lane_groups as lanes,offramp_routing as routing,area_freeway_accounting as area
    manifest=h.R/'lane_state132/eval_01/manifest.json';read(manifest)
    model=lpr.load_sources(manifest)['component']
    spec=read(h.F/'joint_lane_25/protocol.json')['candidate']
    spec.update(congested_receiving_cells=[21],reciprocal_off='10483')
    contract=read(h.F/'route_inventory/contract.json')
    raw=read(h.F/'route_inventory/s67_late/initial_raw.json')
    records={r['arm']:r for r in common.records(False)}
    control=dict(active=False,arm=None,trace=[])
    def matrix(obj,i,ns,t,dt):
        assert i in range(20,26) and abs(dt-1)<1e-8
        if not control['active']:
            result=[]
            for g,rate in enumerate(obj.rates):
                hazard=sum(rate)
                result.append([ns[g]*(1-math.exp(-hazard*dt))*r/hazard if hazard else 0. for r in rate])
            return result
        index=math.floor((t-2670.1+1e-6)/5)
        key=round(2670.1+5*index,6)
        fractions=schedules[control['arm']][key][i]
        result=[[ns[g]*r*dt for r in row] for g,row in enumerate(fractions)]
        assert all(sum(row)<=ns[g]+1e-9 for g,row in enumerate(result))
        # The following trace stores requests before the unchanged receiving cap.
        control['trace'].append(dict(time_s=t,cell=i,donor_stock=list(ns),fractions=fractions,requested=copy.deepcopy(result)))
        return result
    hooks=[];instances=[];forecasts=0;rows=[];started=time.perf_counter()
    h.save(HERE/'status.json',dict(status='running',forecasts=0))
    def run(arm,active):
        nonlocal forecasts
        rec=records[arm];pins[rec['input']]=rec['sha256']
        args,kw=copy.deepcopy(replay.read_primitive_capture(rec['input'],rec['sha256']))
        args_before=copy.deepcopy(args)
        assert kw['horizon_sec']==450 and args[2]==context['parameters']
        kw.update(offramp_inventory=dict(contract=copy.deepcopy(contract),raw=copy.deepcopy(raw)),
                  route_lane_regions={'FW_E':copy.deepcopy(spec)})
        kw['port_dynamics']['entry_capacity_mode']='storage'
        control.update(active=active,arm=arm,trace=[])
        pred=model.rollout(*args,**kw);forecasts+=1
        assert args==args_before
        assert len(instances)==1
        obj=instances.pop();assert len(obj.split19_rows)==2700 and obj.split19_error<1e-8
        diag=pred['diagnostics']['roads'][0]
        assert diag['negative_density_count']==0 and diag['continuity_residual_max_veh']<1e-7
        assert diag['joint_lane_region']['route_marginal_max_error']<1e-7
        assert max(abs(r['conservation_residual_veh']) for r in pred['ramps'])<1e-7
        if not active:
            ref=read(h.R/f'spatial_context148/forecast/training/s67_late_{arm}.json.gz')
            parity={k:json.loads(json.dumps(pred[k]))==ref[k] for k in ('cells','flows','ports','ramps')}
            h.save(HERE/'parity.json',parity);assert all(parity.values());return
        assert len(control['trace'])==2700
        measure=replay._cellwise_measure(model,pred,rec,Obs(rec['truth']));measure.pop('score',None)
        for name in ('cells_30s.csv','flows_30s.csv','ports_30s.csv'):
            p=Path(rec['truth'])/name;pins[str(p)]=h.sha(p)
        with gzip.open(HERE/f'{arm}.json.gz','wt',encoding='utf-8') as f:json.dump(pred,f,allow_nan=False)
        with gzip.open(HERE/f'{arm}_transfers.json.gz','wt',encoding='utf-8') as f:json.dump(control['trace'],f,allow_nan=False)
        rows.append(measure);h.save(HERE/'rows.json',rows)
        h.save(HERE/'status.json',dict(status='running',forecasts=forecasts))
    try:
        assert not hasattr(lanes,'RouteLaneRegion') and not hasattr(lanes,'_lateral167_matrix')
        lanes._lateral167_matrix=matrix;hooks.append((lanes,'_lateral167_matrix',None))
        ns={};exec(compile(changed['RouteLaneRegion'],'167class','exec'),lanes.__dict__,ns)
        lanes.RouteLaneRegion=ns['RouteLaneRegion'];hooks.append((lanes,'RouteLaneRegion',None))
        original_init=lanes.RouteLaneRegion.__init__
        def record_instance(obj,*a,**kw):original_init(obj,*a,**kw);instances.append(obj)
        lanes.RouteLaneRegion.__init__=record_instance
        for target,name in ((routing,'initialize_inventory'),(routing,'advance_inventory'),(area,'_freeway_substep_events'),(type(model),'rollout')):
            old_fn=getattr(target,name);ns={};exec(compile(changed[name],'167_'+name,'exec'),old_fn.__globals__,ns)
            hooks.append((target,name,old_fn));setattr(target,name,ns[name])
        run('release',False)
        run('release',True)
        run('release_vsl90',True)
        a,b=rows
        deltas={kind:{k:b[kind][k]-a[kind][k] for k in ('ttt','ramp_ttt','end_n','exits')} for kind in ('actual','predicted')}
        h.save(HERE/'assessment.json',dict(status='complete_conditional_only',deltas=deltas,
            forecasts=forecasts,elapsed_sec=time.perf_counter()-started,production_adopted=False,goal_complete=False,
            autonomous=False,scope='FW_E31+4on+4off, not Omega'))
        h.save(HERE/'status.json',dict(status='complete_conditional_only',forecasts=forecasts))
        print(deltas)
    except BaseException as exc:
        h.save(HERE/'status.json',dict(status='failed',forecasts=forecasts,error=repr(exc)));raise
    finally:
        for target,name,old_fn in reversed(hooks):
            if old_fn is None:delattr(target,name)
            else:setattr(target,name,old_fn)
        for path,digest in {**pins,**protected['protected_sha256']}.items():assert h.sha(path)==digest,path
        assert h.sha(protected['STOP']['path'])==protected['STOP']['sha256']
        h.save(HERE/'preservation.json',dict(core=True,STOP=True,input_sha256=pins,hooks_restored=True))


if __name__=='__main__':main()
