"""One process-local, conservative two-compartment cell19 transport trial.

The31-cell speed model, costs, off-ramp/ramp models and control stay canonical.
No future native state enters the rollout. No new runner or production adapter.
"""
import copy
import gzip
import importlib.util
import inspect
import json
import math
from pathlib import Path
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def save(name, obj):
    (HERE/name).write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def gz(name, obj):
    with gzip.open(HERE/name, 'wt', encoding='utf-8') as stream:
        json.dump(obj, stream, allow_nan=False)


def main():
    assert not (HERE/'protocol.json').exists(), 'Do not duplicate or extend completed trial'
    spec = importlib.util.spec_from_file_location('reuse111', HERE.parent/'jin_macro111/run.py')
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    context, replay, Obs = helper.setup()
    from evaluation.controllers import offramp_routing as route, area_freeway_accounting as area
    from evaluation.controllers.projection_support import complete_records
    old_initialize, old_advance = route.initialize_inventory, route.advance_inventory
    old_step = area._freeway_substep_events
    pins = read(HERE.parent/'stop_population114/protocol.json')['core_pins']
    for p,h in pins.items():
        assert helper.sha(p) == h
    geometry = read(helper.I/'selected/port_gain/geometry.json')
    geom = next(x for x in geometry['cells'] if x['road']=='FW_E' and x['cell']==19)
    midpoint = (geom['start_m']+geom['end_m'])/2
    protocol = dict(
        previous_turn='PROGRESS118: lane-reaction conditional candidate rejected;9000 analysis remains stopped.',
        basis='106 observed boundary outflow differs from integrated N*v/L through changing spatial stock;91 frozen-position predictor and24/25 recovery subdivision already rejected.',
        change='Cell19 only: preserve current upstream/downstream half route stocks, advance internal flux2*v*U/L and send2*v*D/L, bounded by available stocks/half storage. No extra speed states or capacity benefit.',
        half_length_m=geom['length_km']*500, nominal_lanes=3,
        scope='FW_E31cells+4on/4off connectors. NOT wholeOmega. No9000 analysis/native/FZP.',
        equations='U_next=U+accepted_in-H; D_next=D+H-accepted_out; H=min(2*v*U/L, U/dt, free_D/dt)*dt; out=min(2*v*D/L,D/dt,canonical downstream supply); incoming bounded by free_U/dt.',
        route_classes='Initial halves from current physical position via original initialize_inventory lane partition; downstream-half route composition supplies accepted flow; all classes conserved.',
        limitations='Shared canonical mean speed drives both halves; this is a tested spatial transport closure, not a full refined METANET speed model or microscopic queue solver.',
        budget=dict(fits=0, first_forecasts=3, additional_only_if_pass=10, candidates=1),
        first_gate='67VSL90-release vs110-release: meaningful component andmainline gain sign correct; eachTTT response error>=20% reduction; all states/conservation valid; per-arm component absoluteTTT error may worsen<=1vehh.',
        pins=pins, helper_sha=helper.sha(HERE.parent/'jin_macro111/run.py'),
        STOP_sha=helper.sha(Path('D:/VISSIM_runs/20260928_sd31_d4e2_9000/STOP')))
    save('protocol.json', protocol)
    active = False
    traces = []
    max_residual = 0.

    def initialize(state, cfg, raw, *, lane_partition=None):
        if not active:
            return old_initialize(state, cfg, raw, lane_partition=lane_partition)
        assert lane_partition is None
        rt = cfg.network.offramp_route_inventory
        assert not any(v['freeway']=='FW_E' and v['source_cell']==19 for v in rt['branches'].values())
        assert not any(v['freeway']=='FW_E' and v['cell']==19 for v in rt['merges'].values())
        dimensions = {fw:[2 if fw=='FW_E' and i==19 else 1 for i in range(len(bounds)-1)] for fw,bounds in rt['bounds'].items()}
        assignments = {}
        for p in complete_records(raw):
            if str(p['link_no']) not in rt['physical']:
                continue
            fw,x,i = route._position(rt,p['link_no'],p['position_m'])
            assignments[p['veh_no']] = int(fw=='FW_E' and i==19 and x>=midpoint)
        metadata = old_initialize(state, cfg, raw, lane_partition=dict(groups_per_cell=dimensions,vehicle_group=assignments))
        partitions = state.offramp_route_inventory_state.pop('lane_cells')
        state._subcell119 = dict(halves=partitions['FW_E'][19], prepared=None)
        return metadata

    def prepare(state, cfg, fw, vehicles, speeds, lengths, lanes, flows, receiving, dt):
        if not active or fw!='FW_E':
            return
        data = state._subcell119
        upper, lower = data['halves']
        u,d = map(lambda x:math.fsum(x.values()), (upper,lower))
        assert abs(u+d-vehicles[19])<1e-7
        half_capacity = cfg.network.rho_max*3*lengths[19]/2
        assert min(u,d)>=-1e-8 and max(u,d)<=half_capacity+1e-7
        fraction = 2*speeds[19]*dt/lengths[19]
        assert 0<=fraction<=1, ('subcell CFL',fraction)
        transfer = min(u*fraction, max(0.,half_capacity-d))
        out = min(d*fraction,d)/dt
        # Preserve an already active canonical sending cap, if present.
        raw = vehicles[19]*speeds[19]/lengths[19]
        if flows[19] < raw-1e-8:
            out = min(out,flows[19])
        flows[19] = out
        receiving[19] = min(receiving[19],max(0.,half_capacity-u)/dt)
        data['prepared'] = dict(u=u,d=d,transfer=transfer,capacity=half_capacity)

    def advance(state, cfg, fw, **kwargs):
        nonlocal max_residual
        if not active or fw!='FW_E':
            return old_advance(state,cfg,fw,**kwargs)
        data = state._subcell119
        upper, lower = map(dict,data['halves'])
        prepared = data['prepared']
        assert prepared is not None
        u,d,transfer = (prepared[k] for k in ('u','d','transfer'))
        dt=kwargs['duration_h']
        out=kwargs['mainline'][19]*dt
        assert out<=d+1e-8
        residual_lower={k:n*(1-min(1.,out/d)) for k,n in lower.items()} if d else {}
        mid={k:n*transfer/u for k,n in upper.items()} if u else {}
        # Let canonical transport move exact old downstream classes. Restore
        # the separately retained upstream stock before its final assertions.
        state.offramp_route_inventory_state['cells'][fw][19]=lower
        value=old_advance(state,cfg,fw,**kwargs)
        new=state.offramp_route_inventory_state['cells'][fw][19]
        incoming={k:new.get(k,0.)-residual_lower.get(k,0.) for k in set(new)|set(residual_lower)}
        assert min(incoming.values(),default=0.)>=-1e-8
        incoming={k:max(0.,v) for k,v in incoming.items()}
        assert abs(sum(incoming.values())-kwargs['mainline'][18]*dt)<1e-7
        up={k:upper.get(k,0.)-mid.get(k,0.)+incoming.get(k,0.) for k in set(upper)|set(incoming)}
        down={k:residual_lower.get(k,0.)+mid.get(k,0.) for k in set(residual_lower)|set(mid)}
        assert all(v>=-1e-8 for row in (up,down) for v in row.values())
        assert max(sum(up.values()),sum(down.values()))<=prepared['capacity']+1e-7
        combined={k:up.get(k,0.)+down.get(k,0.) for k in set(up)|set(down)}
        state.offramp_route_inventory_state['cells'][fw][19]=combined
        data['halves']=[up,down]
        data['prepared']=None
        route._update_missed_target_diagnostics(state)
        error=abs(sum(combined.values())-(u+d+sum(incoming.values())-out))
        max_residual=max(max_residual,error)
        assert error<1e-7
        traces.append(dict(time=state.time_sec+dt*3600,u=sum(up.values()),d=sum(down.values()),
                           internal=transfer,inflow=sum(incoming.values()),outflow=out))
        return value

    source=inspect.getsource(old_step)
    anchor='        receiving_for_mainline = [max(0.0, receiving[i] - ramp_in_by_link[link][i]) for i in range(len(rho_for_flow))]\n'
    assert source.count(anchor)==1
    changed=source.replace(anchor,'        _subcell119_prepare(state,cfg,link,vehicles,speeds,lengths,lanes_now,q_values,receiving,dt_h)\n'+anchor)
    (HERE/'executed_step.py.txt').write_text(changed,encoding='utf-8')
    namespace=dict(old_step.__globals__,_subcell119_prepare=prepare)
    exec(compile(changed,'<subcell119 diagnostic>','exec'),namespace)
    route.initialize_inventory=initialize
    route.advance_inventory=advance
    area._freeway_substep_events=namespace['_freeway_substep_events']
    results=[]
    started=time.perf_counter()
    current=None
    try:
        records={r['arm']:r for r in helper.records(False)}
        for label,arm,enabled in [('disabled','release',False),('candidate110','release',True),('candidate90','release_vsl90',True)]:
            current=label;active=enabled;traces.clear();max_residual=0.
            save('status.json',dict(status='running',current=label,completed=len(results)))
            r=records[arm]
            pred,measure=helper.predict(context['component'],replay,Obs(r['truth']),r,450)
            if not enabled:
                with gzip.open(HERE.parent/'jin_macro111/baseline_release.json.gz','rt',encoding='utf-8') as stream:
                    archived=json.load(stream)
                parity={k:json.loads(json.dumps(pred[k]))==archived[k] for k in ('cells','flows','ports','ramps')}
                save('disabled_parity.json',parity)
                assert all(parity.values()),parity
            else:
                assert len(traces)==450
            gz(label+'.json.gz',pred)
            save(label+'_trace.json',traces)
            row=dict(version=label,**measure,max_subcell_balance_residual=max_residual)
            results.append(row);save('partial.json',results)
            print(json.dumps(dict(version=label,predicted=measure['predicted'],max_residual=max_residual)),flush=True)
        with gzip.open(HERE.parent/'jin_macro111/baseline_release_vsl90.json.gz','rt',encoding='utf-8') as stream:
            old90=json.load(stream)
        base90=replay._cellwise_measure(context['component'],old90,records['release_vsl90'],Obs(records['release_vsl90']['truth']),horizon_sec=450)
        native={k:results[2]['actual'][k]-results[1]['actual'][k] for k in ('ttt','mainline_ttt','ramp_ttt','off_ttt','end_n','exits')}
        baseline={k:base90['predicted'][k]-results[0]['predicted'][k] for k in native}
        candidate={k:results[2]['predicted'][k]-results[1]['predicted'][k] for k in native}
        improvement={k:1-abs(candidate[k]-native[k])/abs(baseline[k]-native[k]) for k in ('ttt','mainline_ttt')}
        gates=dict(response=all(improvement[k]>=.2 and candidate[k]*native[k]>0 for k in improvement),
                   valid=all(not r['score']['invalid'] for r in results),
                   absolute=all(abs(new['predicted']['ttt']-new['actual']['ttt'])<=abs(old['predicted']['ttt']-old['actual']['ttt'])+1
                                for new,old in ((results[1],results[0]),(results[2],base90))))
        save('assessment.json',dict(native=native,baseline=baseline,candidate=candidate,improvement=improvement,gates=gates,
                                    decision='EXPAND_SHORT_VALIDATION' if all(gates.values()) else 'REJECT_TRANSPORT_CANDIDATE',gain_qualified=False))
        save('status.json',dict(status='complete',completed=3,elapsed_seconds=time.perf_counter()-started))
        print(json.dumps(dict(native=native,baseline=baseline,candidate=candidate,gates=gates)),flush=True)
    except BaseException as exc:
        save('status.json',dict(status='failed',completed=len(results),current=current,error=repr(exc)))
        raise
    finally:
        route.initialize_inventory=old_initialize
        route.advance_inventory=old_advance
        area._freeway_substep_events=old_step
        for p,h in pins.items():
            assert helper.sha(p)==h
        save('restoration.json',dict(hooks_restored=True,production_pins_preserved=True,
                                    STOP_preserved=helper.sha(Path('D:/VISSIM_runs/20260928_sd31_d4e2_9000/STOP'))==protocol['STOP_sha']))


if __name__=='__main__':
    main()
