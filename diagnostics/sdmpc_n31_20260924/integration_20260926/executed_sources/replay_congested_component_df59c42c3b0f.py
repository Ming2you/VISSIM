"""Bridge completed response inputs into the selected checkout's sole plant.

Capture runs in a separate process against the historical input builder and
stops BEFORE its rollout/scoring. Prediction imports only the selected checkout.
Prediction commands do not start native runs or fit coefficients. The explicit
prepare-seed53 command freezes a finite new response test for the existing runner.
"""
import copy
import csv
import gzip
import hashlib
import json
from pathlib import Path
import pickle
import pickletools
import io
import math
import sys
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
OLD=ROOT.parent/'control-full-review'
OUT=HERE/'congested_replay'


def load(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x): Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')


def read_primitive_capture(path, expected_sha):
    raw=Path(path).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==expected_sha
    allowed={'PROTO','FRAME','STOP','MARK','MEMOIZE','BINGET','LONG_BINGET',
        'NONE','NEWTRUE','NEWFALSE','BININT','BININT1','BININT2','LONG1','LONG4','BINFLOAT',
        'SHORT_BINUNICODE','BINUNICODE','BINUNICODE8','EMPTY_DICT','EMPTY_LIST','EMPTY_TUPLE',
        'APPEND','APPENDS','SETITEM','SETITEMS','TUPLE','TUPLE1','TUPLE2','TUPLE3'}
    assert all(op.name in allowed for op,arg,pos in pickletools.genops(raw)), 'Non-data capture opcode'
    class DataOnly(pickle.Unpickler):
        def find_class(self,*args):raise ValueError('Class/function resolution forbidden')
        def persistent_load(self,*args):raise ValueError('External reference forbidden')
    return DataOnly(io.BytesIO(raw)).load()


def capture():
    sys.path.insert(0,str(OLD))
    from diagnostics.metanet_net_gain_goal_20260924 import extract as e
    c=e.c
    data,ctx,_,_=c.inputs()
    prior=e.HERE/'legal_release2670'
    assert load(prior/'status.json')['stage']=='complete_response_validation'
    protocol=load(prior/'protocol.json')
    assert protocol['source_sha']==load(HERE/'selected/plant_n31_v2.json')['sources']['network']['sha256']
    ctx=list(copy.deepcopy(ctx));ctx[3]=protocol['port_profile']
    model=c.prior.one.base.load_base_model(data['rm'].geometry,e.HERE/'local_fd/candidate.json')
    OUT.mkdir(exist_ok=False)
    class Captured(BaseException): pass
    records=[]
    for arm in ('hold','release','hold_vsl90','release_vsl90'):
        commands={int(k):v for k,v in load(prior/f'{arm}_commands.json').items()}
        def intercept(*args,**kwargs):
            # Native future truth is scored only after model.rollout, which
            # this capture deliberately never enters.
            json.dumps([args,kwargs],allow_nan=False)
            payload=pickle.dumps((args,kwargs),protocol=5)
            path=OUT/(arm+'_input.pickle');path.write_bytes(payload)
            records.append(dict(arm=arm,input=path.name,sha256=sha(path),
                truth=str(prior/'observations'/arm),previous_native_result=str(prior/f'{arm}_result.json'),
                previous_prediction=str(prior/f'{arm}_prediction.json.gz'),
                command_sha256=sha(prior/f'{arm}_commands.json')))
            raise Captured()
        model.rollout=intercept
        try:
            c.prior.forecast(model,protocol['parameters'],data['rm'],data['rm'],2670.1,450,
                             *ctx[:-1],commands,True)
            raise AssertionError('Rollout input not captured')
        except Captured: pass
    save(OUT/'capture.json',dict(source_network=protocol['source_sha'],cutoff=2670.1,horizon=450,
        geometry_sha256=sha(data['rm'].folder/'geometry.json'),records=records,
        parameter_source=str(prior/'protocol.json'),parameter_sha256=sha(prior/'protocol.json'),
        builder_sources={str(p):sha(p) for p in (Path(c.prior.__file__),Path(c.prior.one.__file__),Path(__file__))},
        cutoff_truncation_assertion_passed=True,native_started=False,future_truth_read_for_prediction=False))
    print(json.dumps(dict(captured=len(records),folder=str(OUT))),flush=True)


def predict():
    sys.path.insert(0,str(ROOT))
    from evaluation.controllers import lane_plant_runtime as lpr
    from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.boundary_factory import ObservationData
    from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.scoring import score_rollout
    context=lpr.load_sources(HERE/'selected/plant_n31_v2.json')
    model=context['component'];manifest=load(OUT/'capture.json')
    assert context['document']['sources']['network']['sha256']==manifest['source_network']
    results=[]
    for row in manifest['records']:
        p=OUT/row['input'];assert sha(p)==row['sha256']
        args,kwargs=pickle.loads(p.read_bytes()) # only our locally generated pinned primitives
        assert args[2]==context['parameters'], 'Selected coefficients differ; do not silently replace them'
        assert kwargs['roads']==['FW_E'] and kwargs['horizon_sec']==450
        started=time.perf_counter();pred=model.rollout(*args,**kwargs)
        wall=time.perf_counter()-started
        with gzip.open(OUT/(row['arm']+'_prediction.json.gz'),'wt',encoding='utf-8') as f:
            json.dump(pred,f,allow_nan=False)
        # Open future observations ONLY after completing this prediction.
        truth=ObservationData(row['truth']);t0=manifest['cutoff']
        initial_n=sum(x['n_veh'] for x in args[0] if x['road']=='FW_E')
        times=[round(t0+d,6) for d in range(0,451,30)]
        port_ids={str(v['connector']) for v in model.ramps.values() if v['road']=='FW_E'}
        port_ids|={str(k) for k,v in model.offramps.items() if v['road']=='FW_E'}
        observed_main={t:sum(x['n_veh'] for x in truth.cells[t] if x['road']=='FW_E') for t in times}
        observed_port={t:sum(float(truth.ports[t,c]['end_n_veh']) for c in port_ids) for t in times}
        predicted_main={t:sum(x['n_veh'] for x in pred['cells'] if abs(x['time_s']-t)<1e-6) for t in times[1:]}
        predicted_port={t:sum(x['n_veh'] for x in pred['ports'] if abs(x['time_s']-t)<1e-6)+
            sum(x['end']['connector_veh'] for x in pred['ramps'] if abs(x['end_sec']-t)<1e-6) for t in times[1:]}
        assert observed_main[t0]==initial_n
        predicted_main[t0]=initial_n;predicted_port[t0]=observed_port[t0]
        integral=lambda values:sum((values[a]+values[b])*(b-a)/7200 for a,b in zip(times,times[1:]))
        flows={}
        for label,records in [('predicted',pred['flows']),('actual',[dict(v,window_end_s=t)
                for (t,r,c),v in truth.flows.items() if r=='FW_E' and t0<t<=times[-1]])]:
            flows[label]={key:sum(float(x[key]) for x in records) for key in
                          ('source_admissions','off_departures','terminal_exits' if label=='predicted' else 'terminal_exits_inferred')}
        merges={r:sum(x['accepted_merge_veh'] for x in pred['ramps'] if x['ramp']==r) for r,v in model.ramps.items() if v['road']=='FW_E'}
        actual_merges={r:sum(float(truth.ports[t,str(model.ramps[r]['connector'])]['departures_veh']) for t in times[1:]) for r in merges}
        score=score_rollout(truth,t0,pred,'FW_E',include_source_boundary=True)
        assert not score['invalid']
        residual=max([abs(x['conservation_residual_veh']) for x in pred['ports']]+[abs(x['conservation_residual_veh']) for x in pred['ramps']])
        assert residual<1e-7
        previous=load(row['previous_native_result'])
        item=dict(arm=row['arm'],wall_sec=wall,score=score,conservation_max=residual,
            predicted_mainline_ttt=integral(predicted_main),actual_mainline_ttt=integral(observed_main),
            predicted_port_ttt=integral(predicted_port),actual_port_ttt=integral(observed_port),
            predicted_merge=merges,actual_merge=actual_merges,flows=flows,
            native_total_cost=previous['native'])
        item['predicted_component_ttt']=item['predicted_mainline_ttt']+item['predicted_port_ttt']
        item['actual_component_ttt']=item['actual_mainline_ttt']+item['actual_port_ttt']
        results.append(item);save(OUT/(row['arm']+'_result.json'),item)
        print(json.dumps(dict(arm=row['arm'],wall_sec=wall,predicted=item['predicted_component_ttt'],actual=item['actual_component_ttt'])),flush=True)
    base=results[0]
    for row in results:
        row['deltas']={k:row[k]-base[k] for k in ('predicted_component_ttt','actual_component_ttt','predicted_mainline_ttt','actual_mainline_ttt','predicted_port_ttt','actual_port_ttt')}
        row['deltas']['predicted_merge']=sum(row['predicted_merge'].values())-sum(base['predicted_merge'].values())
        row['deltas']['actual_merge']=sum(row['actual_merge'].values())-sum(base['actual_merge'].values())
    save(OUT/'summary.json',dict(results=results,gain_qualified=False,calibration=False,
        scope='East31 cells plus8 ramp connectors; not full urban/Omega prediction',
        total_native_cost_scope='All network plus latent waiting; independent scope, not compared numerically to component prediction',
        independent_holdout=False,source_file_pins={str(p):sha(p) for p in
            (Path(lpr.__file__),Path(sys.modules[model.__class__.__module__].__file__),HERE/'selected/plant_n31_v2.json',Path(__file__))}))


def compare_saved():
    manifest=load(OUT/'capture.json');checks=[]
    for item in manifest['records']:
        now=OUT/(item['arm']+'_prediction.json.gz')
        before=Path(item['previous_prediction'])
        with gzip.open(now,'rt',encoding='utf-8') as f: actual=json.load(f)
        with gzip.open(before,'rt',encoding='utf-8') as f: old=json.load(f)['rollout']
        for key in ('cells','flows','ports','ramps'):
            assert actual[key]==old[key], (item['arm'],key,'physical replay changed')
        checks.append(dict(arm=item['arm'],arrays_exact=['cells','flows','ports','ramps'],
                           current_sha256=sha(now),previous_sha256=sha(before)))
    save(OUT/'historical_parity.json',dict(passed=True,checks=checks,
        interpretation='Selected current component reproduces the prior wrong response; no new gain calibration',
        no_new_rollouts=True))
    print(json.dumps(dict(parity_cases=len(checks),physical_arrays_exact=True)))


def decompose_saved():
    """Accounting audit of cached outcomes, never forecast inputs or capacity fits."""
    manifest=load(OUT/'capture.json');t0=manifest['cutoff'];end=t0+manifest['horizon']
    steps=[round(t0+x,6) for x in range(0,451,30)]
    all_rows={};pins={};events={};ports={}
    for item in manifest['records']:
        arm=item['arm'];truth=Path(item['truth']);native_manifest=load(truth/'manifest.json')
        def read_csv(name):
            path=truth/name
            assert sha(path)==native_manifest['files'][name],str(path)
            pins[str(path)]=sha(path)
            with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
        cells={(round(float(r['time_s']),6),int(r['cell'])):float(r['n_veh'])
               for r in read_csv('cells_30s.csv') if r['road']=='FW_E'}
        flows={(round(float(r['window_end_s']),6),int(r['cell'])):r
               for r in read_csv('flows_30s.csv') if r['road']=='FW_E'}
        ports[arm]=[r for r in read_csv('ports_30s.csv') if r['road']=='FW_E']
        events[arm]=read_csv('port_events.csv')
        path=OUT/(arm+'_prediction.json.gz');pins[str(path)]=sha(path)
        with gzip.open(path,'rt') as f:p=json.load(f)
        predicted={(round(r['time_s'],6),r['cell']):r['n_veh'] for r in p['cells']}
        pf={(round(r['window_end_s'],6),r['cell']):r for r in p['flows']}
        for c in range(31):predicted[t0,c]=cells[t0,c]
        all_rows[arm]={}
        for c in range(31):
            row={}
            for label,stocks,ff in [('actual',cells,flows),('predicted',predicted,pf)]:
                row[label+'_ttt']=sum((stocks[a,c]+stocks[b,c])*(b-a)/7200 for a,b in zip(steps,steps[1:]))
                for key in ('source_admissions','ramp_merges','off_departures','terminal_exits','downstream_crossings'):
                    source='terminal_exits_inferred' if label=='actual' and key=='terminal_exits' else key
                    row[label+'_'+key]=sum(float(ff[t,c][source]) for t in steps[1:])
                row[label+'_n_final']=stocks[end,c]
            all_rows[arm][c]=row
    base=all_rows['hold'];summary={};series=[];matches={}
    off_ids={r['connector'] for r in ports['hold'] if r['kind']!='ramp'}
    assert off_ids=={'10643','10682','10481','10483'},off_ids
    for arm,rows in all_rows.items():
        if arm=='hold':continue
        differences=[]
        for c,row in rows.items():
            delta={key:row[key]-base[c][key] for key in row}
            delta.update(cell=c,arm=arm,ttt_response_error=delta['predicted_ttt']-delta['actual_ttt'])
            series.append(delta);differences.append(delta)
        ports_delta={}
        for connector in sorted(off_ids):
            def total(name,key):return sum(float(r[key]) for r in ports[name]
                if r['connector']==connector and t0<float(r['window_end_s'])<=end)
            ports_delta[connector]={key:total(arm,key)-total('hold',key) for key in ('arrivals_veh','departures_veh')}
        # Same IDs reaching the same exit; missing IDs are NOT assumed deleted,
        # rerouted, or queued because this event cache cannot distinguish them.
        def exits(name):
            out={}
            for r in events[name]:
                if r['connector'] in off_ids and r['kind']=='arrival' and float(r['time_s'])>t0:
                    out.setdefault(int(r['vehicle']),[]).append((r['connector'],float(r['time_s'])))
            return out
        hold,changed=exits('hold'),exits(arm)
        by_port={}
        for connector in sorted(off_ids):
            ids={v for v,ee in hold.items() if any(c==connector and t<=end for c,t in ee)}
            categories=dict(same_exit_within_horizon=0,same_exit_after_horizon=0,
                            different_exit_only_observed=0,no_east_exit_observed=0)
            later=[]
            for v in ids:
                same=[t for c,t in changed.get(v,[]) if c==connector]
                if same:
                    key='same_exit_within_horizon' if min(same)<=end else 'same_exit_after_horizon'
                    categories[key]+=1
                    h=min(t for c,t in hold[v] if c==connector)
                    later.append(min(same)-h)
                elif changed.get(v):categories['different_exit_only_observed']+=1
                else:categories['no_east_exit_observed']+=1
            assert sum(categories.values())==len(ids)
            by_port[connector]=dict(hold_exit_ids=len(ids),categories=categories,
                                   matched_same_exit_mean_delay_s=sum(later)/len(later) if later else None)
        matches[arm]=by_port
        summary[arm]=dict(component_mainline_deltas={key:sum(r[key] for r in differences)
            for key in ('actual_ttt','predicted_ttt','actual_off_departures','predicted_off_departures',
                        'actual_terminal_exits','predicted_terminal_exits')},
            largest_underestimated_cost_cells=sorted(differences,key=lambda r:r['ttt_response_error'])[:6],
            actual_port_delta=ports_delta)
    checked=load(OUT/'summary.json')
    for r in checked['results']:
        if r['arm']=='hold':continue
        for label in ('actual','predicted'):
            assert abs(summary[r['arm']]['component_mainline_deltas'][label+'_ttt']-
                       r['deltas'][label+'_mainline_ttt'])<1e-7
    with (OUT/'cell_response.csv').open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(series[0]));writer.writeheader();writer.writerows(series)
    save(OUT/'spatial_audit.json',dict(summary=summary,matched_exit_events=matches,pins=pins,
        no_new_rollouts=True,no_future_prediction_inputs=True,
        limits='Port events alone do not identify initial destination, final location, removals, or causal rerouting'))
    print(json.dumps({arm:dict(total=x['component_mainline_deltas'],ports=x['actual_port_delta'],
        cells=[(r['cell'],round(r['actual_ttt'],3),round(r['predicted_ttt'],3))
               for r in x['largest_underestimated_cost_cells']]) for arm,x in summary.items()}))


def initial_cohort_exits():
    """Separate known common vehicles from arrivals after the initial snapshot.

    Only the missing whole-network initial frame is read from native FZP.
    All post-initial outcomes come from previously validated event caches.
    """
    source=OLD/'diagnostics/metanet_net_gain_goal_20260924/legal_release2670'
    meta=load(source/'current_route_snapshot/manifest.json');t0=meta['cutoff'];end=t0+450
    path=Path(meta['source']);stat=path.stat()
    assert (stat.st_size,stat.st_mtime_ns)==(meta['size'],meta['mtime_ns'])
    assert meta['network_sha256']==load(OUT/'capture.json')['source_network']
    cache=OUT/'initial_network_cohort.json'
    assert not cache.exists(),'Reuse the completed initial cohort audit, do not rescan'
    digest=hashlib.sha256();initial={};count=0
    with path.open('rb') as f:
        header=None
        for raw in f:
            if raw.startswith(b'$VEHICLE:'):
                header=raw.decode('ascii').strip().split(':',1)[1].split(';')
                fields={k:header.index(k) for k in ('NO','LANE\\LINK\\NO','LANE\\INDEX','POS','ROUTDECNO','ROUTENO')}
                digest.update(raw);continue
            if header is None or raw.startswith((b'*',b'$')) or not raw.strip():
                digest.update(raw);continue
            sec=float(raw.split(b';',1)[0])
            if sec>t0+1e-7:break
            digest.update(raw);count+=1
            if abs(sec-t0)>1e-7:continue
            z=raw.decode('ascii').strip().split(';');row={k:z[i].strip() for k,i in fields.items()}
            no=int(row['NO']);assert no not in initial;initial[no]=row
    assert digest.hexdigest()==meta['prefix_sha256'] and count==meta['scanned_data_rows']
    assert (path.stat().st_size,path.stat().st_mtime_ns)==(stat.st_size,stat.st_mtime_ns)
    prior_snapshot=load(source/'current_route_snapshot/snapshot.json')
    assert len(prior_snapshot)==1035
    for row in prior_snapshot:
        assert all(initial[int(row['NO'])][k]==row[k] for k in fields)
    pins={str(source/'current_route_snapshot/manifest.json'):sha(source/'current_route_snapshot/manifest.json'),
          str(source/'current_route_snapshot/snapshot.json'):sha(source/'current_route_snapshot/snapshot.json')}
    east={int(r['NO']) for r in prior_snapshot};offs={'10643','10682','10481','10483'}
    events={};prefix=None
    for arm in ('hold','release','hold_vsl90','release_vsl90'):
        result=load(source/(arm+'_result.json'))
        if prefix is None:prefix=result['prefix_exact']
        assert result['prefix_exact']==prefix
        p=source/'observations'/arm/'port_events.csv';m=load(p.parent/'manifest.json')
        assert sha(p)==m['files'][p.name];pins[str(p)]=sha(p)
        with p.open(encoding='utf-8-sig',newline='') as f:
            events[arm]=[r for r in csv.DictReader(f) if r['kind']=='arrival'
                         and r['connector'] in offs and float(r['time_s'])>t0]
    totals={};paired={}
    for arm,rows in events.items():
        totals[arm]={}
        for off in sorted(offs):
            totals[arm][off]={label:sum(r['connector']==off and float(r['time_s'])<=end and test(int(r['vehicle'])) for r in rows)
                for label,test in [('initial_east',lambda v:v in east),
                                   ('initial_elsewhere',lambda v:v in initial and v not in east),
                                   ('not_present_at_initial',lambda v:v not in initial)]}
        if arm=='hold':continue
        paired[arm]={}
        for off in sorted(offs):
            hold={int(r['vehicle']):float(r['time_s']) for r in events['hold']
                  if r['connector']==off and float(r['time_s'])<=end and int(r['vehicle']) in initial}
            same={int(r['vehicle']):float(r['time_s']) for r in rows if r['connector']==off}
            other={int(r['vehicle']) for r in rows if r['connector']!=off}
            matched=[v for v in hold if v in same]
            differences=[dict(vehicle=v,initial_link=initial[v]['LANE\\LINK\\NO'],
                initial_route=initial[v]['ROUTDECNO']+':'+initial[v]['ROUTENO'],
                changed_exit=[(r['connector'],float(r['time_s'])) for r in rows if int(r['vehicle'])==v])
                for v in hold if v not in same and v in other]
            paired[arm][off]=dict(initial_hold_exit_count=len(hold),
                same_exit_within_horizon=sum(same[v]<=end for v in matched),
                same_exit_after_horizon=sum(same[v]>end for v in matched),
                different_exit_only_observed=differences,
                unresolved_by_end_of_cache=[v for v in hold if v not in same and v not in other],
                matched_delay_sum_s=sum(same[v]-hold[v] for v in matched),
                matched_delay_mean_s=sum(same[v]-hold[v] for v in matched)/len(matched) if matched else None)
    save(cache,dict(cutoff=t0,vehicles=initial,source_meta=meta))
    pins[str(cache)]=sha(cache)
    summary=dict(initial_network_count=len(initial),initial_east_count=len(east),totals=totals,paired=paired,
        pins=pins,precontrol_prefix=prefix,future_model_inputs=False,new_rollouts=0,
        limits='Known initial IDs are comparable; later creation identities are not certified. Missing cached exit is not proof of deletion or rerouting. Exit timing includes full network interaction and is not an identified local capacity.')
    save(OUT/'initial_cohort_exit_audit.json',summary)
    print(json.dumps(dict(initial_network=len(initial),initial_east=len(east),totals=totals,paired=paired)))


def cohort_delay_bounds():
    audit=load(OUT/'initial_cohort_exit_audit.json')
    cache=OUT/'initial_network_cohort.json'
    assert sha(cache)==audit['pins'][str(cache)]
    initial=load(cache);ids=set(map(int,initial['vehicles']));t0=initial['cutoff'];end=t0+450
    source=OLD/'diagnostics/metanet_net_gain_goal_20260924/legal_release2670/observations'
    rows={}
    for arm in ('hold','release','hold_vsl90','release_vsl90'):
        p=source/arm/'port_events.csv';assert sha(p)==audit['pins'][str(p)]
        with p.open(encoding='utf-8-sig',newline='') as f:
            rows[arm]={(int(r['vehicle']),r['connector']):r for r in csv.DictReader(f)
                       if r['kind']=='arrival' and int(r['vehicle']) in ids and float(r['time_s'])>t0}
    result={}
    for arm in ('release','hold_vsl90','release_vsl90'):
        result[arm]={}
        for off,expected in audit['paired'][arm].items():
            matched=[(r,rows[arm][key]) for key,r in rows['hold'].items() if key[1]==off
                     and float(r['time_s'])<=end and key in rows[arm]]
            assert len(matched)==expected['same_exit_within_horizon']+expected['same_exit_after_horizon']
            lower=sum(float(b['lower_time_s'])-float(a['upper_time_s']) for a,b in matched)
            upper=sum(float(b['upper_time_s'])-float(a['lower_time_s']) for a,b in matched)
            measured=sum(float(b['time_s'])-float(a['time_s']) for a,b in matched)
            assert lower<=measured<=upper
            result[arm][off]=dict(matched=len(matched),delay_mean_s=measured/len(matched),
                mean_lower_s=lower/len(matched),mean_upper_s=upper/len(matched))
    save(OUT/'initial_cohort_delay_bounds.json',dict(results=result,source_audit_sha256=sha(OUT/'initial_cohort_exit_audit.json'),
        interpretation='Deterministic crossing-time brackets from FZP5; not a confidence interval or local capacity estimate. Same-exit matching conditions on the eventual outcome.',
        new_scans=0,new_rollouts=0))
    print(json.dumps(result))


DECISIONS=HERE/'decision_response'


def capture_decisions():
    """Reuse past-only builders for two training and two checking contexts."""
    sys.path.insert(0,str(OLD))
    from diagnostics.metanet_net_gain_goal_20260924 import extract as e
    c=e.c;data,ctx,_,_=c.inputs()
    DECISIONS.mkdir(exist_ok=False)
    records=[]
    # Already captured, same current selected component; no repeated forecast.
    previous=load(OUT/'capture.json')
    for row in previous['records']:
        p=OUT/row['input'];assert sha(p)==row['sha256']
        records.append(dict(row,case='s29_late',role='train',reference='hold',
                            cutoff=2670.1,input=str(p)))
    frozen=load(e.HERE/'heldout43/freeze.json')
    model=c.prior.one.base.load_base_model(data['none'].geometry,e.HERE/'local_fd/candidate.json')
    parameters=load(HERE/'selected/port_gain/parameters.json')['parameters']
    class Captured(BaseException):pass
    for seed in (29,43,47):
        late=seed==47
        case=f's{seed}_'+('late' if late else 'early')
        cutoff=2670.1 if late else 2220.1
        if late:
            folder=e.HERE/'release2670_seed47'
            state=c.prior.ObservationData(folder/'observations/hold')
            port_profile=load(folder/'protocol.json')['port_profile']
            arms=('hold','release_10490','release_10484','hold_vsl90')
        else:
            state=data['none'] if seed==29 else c.prior.ObservationData(e.r.HERE/'gain_response/seed43/none')
            port_profile=frozen['port_profile'];arms=('none','vsl','rm','both')
        local_ctx=list(copy.deepcopy(ctx));local_ctx[3]=port_profile
        for arm in arms:
            commands=({int(t):v for t,v in load(folder/f'{arm}_commands.json').items()}
                      if late else c.exp.commands(arm,ctx[0],ctx[-1]))
            if late:truth=folder/'observations'/arm
            elif arm=='none':truth=state.folder
            elif seed==43:truth=e.HERE/'heldout43/observations'/arm
            else:truth=c.exp.HERE/'observations'/arm
            assert (truth/'cells_30s.csv').is_file(),str(truth)
            def intercept(*args,**kwargs):
                json.dumps([args,kwargs],allow_nan=False)
                p=DECISIONS/f'{case}_{arm}.pickle'
                p.write_bytes(pickle.dumps((args,kwargs),protocol=5))
                records.append(dict(case=case,role='train' if seed==29 else 'check',
                    reference=arms[0],arm=arm,cutoff=cutoff,input=str(p),sha256=sha(p),
                    truth=str(truth),commands_sha256=hashlib.sha256(json.dumps(commands,sort_keys=True).encode()).hexdigest()))
                raise Captured()
            model.rollout=intercept
            try:
                c.prior.forecast(model,parameters,state,state,cutoff,450,*local_ctx[:-1],commands,True)
                raise AssertionError('Input capture failed')
            except Captured:pass
    save(DECISIONS/'capture.json',dict(records=records,source_network=previous['source_network'],
        new_rollouts=0,future_truth_used_as_input=False,
        role_note='29 early+late training;43 early and47 late checking only, previously inspected development data, NOT pristine holdout',
        builder_sha256={str(p):sha(p) for p in (Path(c.prior.__file__),Path(__file__))}))
    print(json.dumps(dict(captured=len(records),path=str(DECISIONS))),flush=True)


def decision_screen():
    """Finite direct-response calibration of existing physical coefficients.

    Costs retain physical stocks. No fitted objective correction, command bonus,
    future input or per-vehicle timing calibration is introduced.
    """
    sys.path.insert(0,str(ROOT))
    from evaluation.controllers import lane_plant_runtime as lpr
    from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.boundary_factory import ObservationData
    from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.scoring import score_rollout
    assert not (DECISIONS/'screen.json').exists(),'Preserve completed screening'
    manifest=load(DECISIONS/'capture.json');context=lpr.load_sources(HERE/'selected/plant_n31_v2.json')
    model=context['component'];records=manifest['records'];payloads={};truths={};actual={}
    port_ids={str(r['connector']) for r in model.ramps.values() if r['road']=='FW_E'}
    port_ids|={str(k) for k,v in model.offramps.items() if v['road']=='FW_E'}
    def integral(values,times):
        return sum((values[a]+values[b])*(b-a)/7200 for a,b in zip(times,times[1:]))
    def key(r):return r['case']+'/'+r['arm']
    for r in records:
        p=Path(r['input']);assert sha(p)==r['sha256']
        payloads[key(r)]=pickle.loads(p.read_bytes())
        assert payloads[key(r)][0][2]==context['parameters']
        truth=ObservationData(r['truth']);truths[key(r)]=truth
        times=[round(r['cutoff']+d,6) for d in range(0,451,30)]
        main={t:sum(x['n_veh'] for x in truth.cells[t] if x['road']=='FW_E') for t in times}
        port={t:sum(float(truth.ports[t,c]['end_n_veh']) for c in port_ids) for t in times}
        actual[key(r)]=dict(main=integral(main,times),port=integral(port,times))
        actual[key(r)]['total']=sum(actual[key(r)].values())
    train=[r for r in records if r['role']=='train'];check=[r for r in records if r['role']=='check']
    baseline_response=copy.deepcopy(model.base.network.freeway_state_response)
    baseline_fd=copy.deepcopy(model.base.network.freeway_vsl_fd_response)
    # Two bounded, existing coefficients only. Freeze this finite design before
    # scoring candidates; no adaptive enlargement if the result is unfavourable.
    grid=[(d,e) for d in (0.,1.,2.,4.,6.) for e in (1.,2.,4.)]
    protocol=dict(delta_merge=sorted({d for d,e in grid}),carlson_E=sorted({e for d,e in grid}),
        fixed_carlson_A=baseline_fd['FW_E']['A'],fit_scope='All four east physical merge cells share delta; original FD and all other terms retained',
        objective='Mean per-state squared error of signed component DeltaTTT, normalized by max(1,max absolute measured contrast) within state',
        counts=dict(train_cases=2,train_arms=8,check_cases=2,check_arms=8,max_training_rollouts=120,max_check_rollouts=16),
        physical_cost_scope='East31 cells plus4 on/4 off connectors; no full urban/external cost claim',
        production_changed=False,source_pins={str(p):sha(p) for p in (Path(__file__),Path(lpr.__file__),Path(sys.modules[model.__class__.__module__].__file__),HERE/'selected/plant_n31_v2.json')})
    protocol_path=DECISIONS/'protocol.json'
    if protocol_path.exists():
        previous=load(protocol_path)
        assert {k:v for k,v in previous.items() if k!='source_pins'}=={k:v for k,v in protocol.items() if k!='source_pins'}
        save(DECISIONS/'resume.json',dict(reason='Runtime tuple versus JSON list comparison only; physical arrays exact',
            previous_protocol_sha256=sha(protocol_path),current_helper_sha256=sha(Path(__file__)),
            reused_candidates=sorted(p.name for p in DECISIONS.glob('train_d*_e*.json'))))
    else:save(protocol_path,protocol)
    def evaluate(delta,e,rows):
        model.base.network.freeway_state_response=copy.deepcopy(baseline_response)
        for ramp in model.ramps.values():
            if ramp['road']=='FW_E':
                cell=str(ramp['to_cell'])
                model.base.network.freeway_state_response['FW_E']['cell_overrides'].setdefault(cell,{})['delta_merge']=delta
        model.base.network.freeway_vsl_fd_response=copy.deepcopy(baseline_fd)
        model.base.network.freeway_vsl_fd_response['FW_E']['E']=e
        out=[]
        for r in rows:
            args,kwargs=copy.deepcopy(payloads[key(r)])
            t0=r['cutoff'];times=[round(t0+d,6) for d in range(0,451,30)]
            pred=model.rollout(*args,**kwargs)
            score=score_rollout(truths[key(r)],t0,pred,'FW_E',include_source_boundary=True)
            assert not score['invalid'],score['diagnostics']
            residual=max([abs(x['conservation_residual_veh']) for x in pred['ports']+pred['ramps']])
            assert residual<1e-7
            main={t:sum(x['n_veh'] for x in pred['cells'] if abs(x['time_s']-t)<1e-6) for t in times[1:]}
            port={t:sum(x['n_veh'] for x in pred['ports'] if abs(x['time_s']-t)<1e-6)+sum(x['end']['connector_veh'] for x in pred['ramps'] if abs(x['end_sec']-t)<1e-6) for t in times[1:]}
            truth=truths[key(r)]
            main[t0]=sum(x['n_veh'] for x in args[0] if x['road']=='FW_E')
            port[t0]=sum(float(truth.ports[t0,c]['end_n_veh']) for c in port_ids)
            pp=dict(main=integral(main,times),port=integral(port,times));pp['total']=sum(pp.values())
            if delta==1. and e==4. and r['case']=='s29_late':
                with gzip.open(OUT/(r['arm']+'_prediction.json.gz'),'rt') as f:old=json.load(f)
                assert all(json.loads(json.dumps(pred[k]))==old[k] for k in ('cells','flows','ports','ramps')),'Baseline physical arrays changed'
            out.append(dict(case=r['case'],arm=r['arm'],reference=r['reference'],predicted=pp,actual=actual[key(r)],
                merge=sum(x['accepted_merge_veh'] for x in pred['ramps']),conservation_max=residual,
                speed_rmse=score['speed']['rmse'],mainline_n_rmse=score['cell_n']['rmse']))
        choices=[];losses=[]
        for case in sorted({r['case'] for r in out}):
            group=[r for r in out if r['case']==case];base=next(r for r in group if r['arm']==r['reference'])
            for r in group:
                r['actual_delta']=r['actual']['total']-base['actual']['total']
                r['predicted_delta']=r['predicted']['total']-base['predicted']['total']
            scale=max(1.,max(abs(r['actual_delta']) for r in group))
            losses.append(sum(((r['predicted_delta']-r['actual_delta'])/scale)**2 for r in group if r!=base)/(len(group)-1))
            picked=min(group,key=lambda r:r['predicted']['total']);best=min(group,key=lambda r:r['actual']['total'])
            choices.append(dict(case=case,selected=picked['arm'],observed_best=best['arm'],
                component_regret=picked['actual']['total']-best['actual']['total']))
        return dict(delta_merge=delta,carlson_E=e,loss=sum(losses)/len(losses),rows=out,choices=choices)
    candidates=[];started=time.perf_counter()
    for d,e in grid:
        path=DECISIONS/f'train_d{d:g}_e{e:g}.json'
        if path.exists():
            result=load(path)
            assert result['delta_merge']==d and result['carlson_E']==e and len(result['rows'])==len(train)
        else:
            result=evaluate(d,e,train)
            save(path,result)
        candidates.append(result)
        print(json.dumps(dict(delta=d,E=e,loss=result['loss'],choices=result['choices'])),flush=True)
    selected=min(candidates,key=lambda r:r['loss'])
    # Freeze training selection before loading held-back outcome values into
    # any calibration objective. These are developmental checks, not untouched data.
    save(DECISIONS/'selection.json',dict(delta_merge=selected['delta_merge'],carlson_E=selected['carlson_E'],training_loss=selected['loss']))
    checks=[evaluate(1.,4.,check)]
    if (selected['delta_merge'],selected['carlson_E'])!=(1.,4.):
        checks.append(evaluate(selected['delta_merge'],selected['carlson_E'],check))
    save(DECISIONS/'screen.json',dict(candidates=candidates,checks=checks,elapsed_sec=time.perf_counter()-started,
        training_rollouts=len(grid)*len(train),check_rollouts=len(checks)*len(check),selected=load(DECISIONS/'selection.json'),
        gain_qualified=False,production_adopted=False,new_native_runs=0,independent_holdout=False))
    print(json.dumps(dict(selected=load(DECISIONS/'selection.json'),checks=[x['choices'] for x in checks],elapsed_sec=time.perf_counter()-started)),flush=True)


def anticipation_response(*, merge_speed=False, lane_drop=False):
    """Two bounded shock-response alternatives; signed cost and choice, no speed fit."""
    sys.path.insert(0,str(ROOT))
    from evaluation.controllers import lane_plant_runtime as lpr
    context=lpr.load_sources(HERE/'selected/plant_n31_v2.json')
    model=context['component'];records=load(DECISIONS/'capture.json')['records']
    assert not (merge_speed and lane_drop)
    out=HERE/('lane_drop_response' if lane_drop else 'merge_speed_response' if merge_speed else 'anticipation_response')
    out.mkdir(exist_ok=False)
    cached=load(DECISIONS/'screen.json')
    baseline_rows=next(r for r in cached['candidates'] if r['delta_merge']==1. and r['carlson_E']==4.)['rows']
    baseline_rows+=next(r for r in cached['checks'] if r['delta_merge']==1. and r['carlson_E']==4.)['rows']
    baseline={(r['case'],r['arm']):r for r in baseline_rows}
    response=copy.deepcopy(model.base.network.freeway_state_response)
    affected=sorted(response['FW_E']['cell_overrides'],key=int)
    nu=context['parameters']['by_direction']['FW_E']['nu_km2_h']
    assert nu==36.75
    assert all(response['FW_E']['cell_overrides'][c]['anticipation']==
               {'downstream_ge_local':18.375,'downstream_lt_local':18.375} for c in affected)
    variants={'formation_nominal':dict(downstream_ge_local=nu,downstream_lt_local=nu/2),
              'both_nominal':dict(downstream_ge_local=nu,downstream_lt_local=nu)}
    if merge_speed:
        variants={'flow_weighted_merge': None}
    if lane_drop:
        assert model.base.network.freeway_lane_drop_phi==3.
        assert not any('freeway_lane_drop_phi' in p for p in
                       (getattr(model.base.network,'metanet_parameters_by_direction',{}) or {}).values())
        variants={'no_extra_lane_drop_deceleration':None}
    rollout_count=2+len(variants)*len(records)
    save(out/'protocol.json',dict(variants=variants,affected_cells=affected,
        reason=('Only phi3 to0 ablation: retain physical4-to3 lanes, off storage/lane loss, merge and FD. Existing model underfeeds downstream merges while falsely slowing cell18. No capacity bonus.' if lane_drop else
                'METANET virtual inlet uses actual accepted mainline/ramp flows and causal calibrated ramp travel speed; no new capacity or reward.' if merge_speed else
                'Current ramp-neighbour anticipation is half the directional nominal. Test stronger upstream braking and separately symmetric nominal recovery.'),
        unchanged='All other coefficients, physical controls, arrivals, geometry, waiting costs and initial states.',
        cutoff_and_seed='29early2220.1+late2670.1 development;43early+47late checking, previously inspected, not pristine holdout',
        evaluation='Signed component DeltaTTT and candidate regret; no speed RMSE objective',
        cost_scope='East31 plus4 on/4 off connectors, NOT whole Omega or external input waiting',
        max_rollouts=rollout_count,production_adopted=False,native_runs=0,
        sources={str(p):sha(p) for p in (Path(__file__),Path(lpr.__file__),
            HERE/'selected/plant_n31_v2.json',DECISIONS/'capture.json',DECISIONS/'screen.json')}))
    payloads={}
    for r in records:
        p=Path(r['input']);assert sha(p)==r['sha256']
        args,kwargs=read_primitive_capture(p,r['sha256'])
        assert args[2]==context['parameters']
        payloads[r['case'],r['arm']]=(args,kwargs)
    parity=[]
    for arm in ('hold','release'):
        args,kwargs=copy.deepcopy(payloads['s29_late',arm]);pred=model.rollout(*args,**kwargs)
        with gzip.open(OUT/(arm+'_prediction.json.gz'),'rt') as f: previous=json.load(f)
        assert all(json.loads(json.dumps(pred[k]))==previous[k] for k in ('cells','flows','ports','ramps'))
        parity.append(dict(arm=arm,all_physical_arrays_exact=True))
    save(out/'baseline_parity.json',parity)
    variants_results=[]
    for name,coefficients in variants.items():
        model.base.network.freeway_state_response=copy.deepcopy(response)
        if lane_drop:
            model.base.network.freeway_lane_drop_phi=0.
        elif merge_speed:
            model.aggregate_merge_speed=True
        else:
            for c in affected:
                model.base.network.freeway_state_response['FW_E']['cell_overrides'][c]['anticipation']=copy.deepcopy(coefficients)
        rows=[]
        for r in records:
            key=r['case'],r['arm'];args,kwargs=copy.deepcopy(payloads[key])
            started=time.perf_counter();pred=model.rollout(*args,**kwargs)
            t0=r['cutoff'];times=[round(t0+d,6) for d in range(0,451,30)]
            main={t:sum(x['n_veh'] for x in pred['cells'] if abs(x['time_s']-t)<1e-6) for t in times[1:]}
            port={t:sum(x['n_veh'] for x in pred['ports'] if abs(x['time_s']-t)<1e-6)+
                  sum(x['end']['connector_veh'] for x in pred['ramps'] if abs(x['end_sec']-t)<1e-6) for t in times[1:]}
            main[t0]=sum(x['n_veh'] for x in args[0] if x['road']=='FW_E')
            # Read the common initial port stock only after the forecast. Future
            # observations are scoring evidence, never rollout inputs.
            from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.boundary_factory import ObservationData
            truth=ObservationData(r['truth'])
            ids={str(v['connector']) for v in model.ramps.values() if v['road']=='FW_E'}
            ids|={str(k) for k,v in model.offramps.items() if v['road']=='FW_E'}
            port[t0]=sum(float(truth.ports[t0,c]['end_n_veh']) for c in ids)
            integral=lambda v:sum((v[a]+v[b])*(b-a)/7200 for a,b in zip(times,times[1:]))
            costs=dict(main=integral(main),port=integral(port));costs['total']=sum(costs.values())
            residual=max(abs(x['conservation_residual_veh']) for x in pred['ports']+pred['ramps'])
            assert residual<1e-7
            flows={k:sum(float(x[k]) for x in pred['flows']) for k in
                   ('source_admissions','off_departures','terminal_exits')}
            row=dict(case=r['case'],arm=r['arm'],reference=r['reference'],predicted=costs,
                actual=baseline[key]['actual'],merge=sum(x['accepted_merge_veh'] for x in pred['ramps']),
                flows=flows,conservation_max=residual,wall_sec=time.perf_counter()-started)
            rows.append(row)
            print(json.dumps(dict(variant=name,case=r['case'],arm=r['arm'],ttt=costs['total'])),flush=True)
        choices=[]
        for case in sorted({r['case'] for r in rows}):
            group=[r for r in rows if r['case']==case];held=next(r for r in group if r['arm']==r['reference'])
            for r in group:
                r['predicted_delta']=r['predicted']['total']-held['predicted']['total']
                r['actual_delta']=r['actual']['total']-held['actual']['total']
            chosen=min(group,key=lambda r:r['predicted']['total']);best=min(group,key=lambda r:r['actual']['total'])
            choices.append(dict(case=case,selected=chosen['arm'],observed_best=best['arm'],
                                component_regret=chosen['actual']['total']-best['actual']['total']))
        result=dict(name=name,coefficients=coefficients,rows=rows,choices=choices)
        save(out/(name+'.json'),result);variants_results.append(result)
    save(out/'summary.json',dict(variants=variants_results,baseline_rows=baseline_rows,
        new_rollouts=rollout_count,production_adopted=False,gain_qualified=False,native_runs=0))
    print(json.dumps(dict(choices={r['name']:r['choices'] for r in variants_results})),flush=True)


def receiving_audit():
    """Observe shared storage allocation without substituting a capacity law."""
    sys.path.insert(0,str(ROOT))
    from evaluation.controllers import lane_plant_runtime as lpr
    from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.boundary_factory import ObservationData
    context=lpr.load_sources(HERE/'selected/plant_n31_v2.json');model=context['component']
    from evaluation.controllers import area_freeway_accounting as accounting
    out=HERE/'receiving_audit';out.mkdir(exist_ok=False)
    manifest=load(OUT/'capture.json');original=accounting._freeway_substep_events
    save(out/'protocol.json',dict(max_rollouts=2,coefficient_changes=False,production_changed=False,
        hypothesis='Determine whether the joint mainline+ramp allocation binds storage, and whether an existing equilibrium FD peak is a defensible hard inflow cap.',
        scope='Same2670.1 state hold/release; observation only. An equilibrium peak is NOT assumed to be a transient upper bound.',
        sources={str(p):sha(p) for p in (Path(__file__),Path(accounting.__file__),OUT/'capture.json',HERE/'selected/plant_n31_v2.json')}))
    all_rows=[];summaries=[]
    for arm in ('hold','release'):
        record=next(r for r in manifest['records'] if r['arm']==arm)
        args,kwargs=read_primitive_capture(OUT/record['input'],record['sha256'])
        assert args[2]==context['parameters'];observations=[];tick=0
        def observe(state,control,demand,cfg,**options):
            nonlocal tick
            net=cfg.network;road='FW_E';dt=cfg.simulation.T_f_h
            assert net.capacity_drop_discharge_phi==1 and not getattr(net,'freeway_hadiuzzaman',None)
            assert not accounting._routing.inventory_enabled(cfg)
            lanes,_=accounting._mn.effective_lane_profile(state,cfg,demand)
            stocks=accounting.continuity_vehicle_counts(state,cfg)[road]
            lengths=accounting.cell_lengths_km(cfg,road,len(stocks))
            q=[n/length*v for n,length,v in zip(stocks,lengths,state.freeway_speed[road])]
            assert len(set(net.ramp_merge_segment_index.values()))==len(net.ramps)
            for ramp in net.ramps:
                i=net.ramp_merge_segment_index[ramp];assert i>0
                split=sum(net.off_ramp_split_ratio[o] for o in net.off_ramps if net.off_ramp_segment_index[o]==i-1)
                requested=q[i-1]*(1-split)
                merge=options['ramp_release_veh_h'][ramp]
                storage=max(0.,net.rho_max*lanes[road][i]*lengths[i]-stocks[i])/dt
                accepted=min(requested,max(0.,storage-merge))
                fd=net.freeway_segment_params[road][i]
                peak=lanes[road][i]*fd['v_free']*fd['rho_crit']*math.exp(-1/fd['metanet_a_m'])
                observations.append(dict(arm=arm,time_s=manifest['cutoff']+tick,ramp=ramp,cell=i,
                    main_requested_vph=requested,main_accepted_vph=accepted,merge_vph=merge,
                    combined_vph=accepted+merge,storage_supply_vph=storage,nominal_fd_peak_vph=peak,
                    storage_binding=accepted<requested-1e-7,above_fd_peak=accepted+merge>peak+1e-7))
            tick+=1
            return original(state,control,demand,cfg,**options)
        accounting._freeway_substep_events=observe
        try:pred=model.rollout(*args,**kwargs)
        finally:accounting._freeway_substep_events=original
        with gzip.open(OUT/(arm+'_prediction.json.gz'),'rt') as f:old=json.load(f)
        assert all(json.loads(json.dumps(pred[k]))==old[k] for k in ('cells','flows','ports','ramps'))
        truth=ObservationData(record['truth'])
        for ramp,spec in model.ramps.items():
            if spec['road']!='FW_E':continue
            i=spec['to_cell'];group=[r for r in observations if r['ramp']==ramp]
            rate_mean=lambda key:sum(r[key] for r in group)/len(group)
            main_count=sum(r['downstream_crossings'] for r in pred['flows'] if r['cell']==i-1)
            merge_count=sum(r['ramp_merges'] for r in pred['flows'] if r['cell']==i)
            assert abs(main_count-rate_mean('main_accepted_vph')*450/3600)<1e-7
            assert abs(merge_count-rate_mean('merge_vph')*450/3600)<1e-7
            actual_main=sum(float(v['downstream_crossings']) for (t,road,cell),v in truth.flows.items()
                            if road=='FW_E' and cell==i-1 and manifest['cutoff']<t<=manifest['cutoff']+450)
            actual_merge=sum(float(v['ramp_merges']) for (t,road,cell),v in truth.flows.items()
                             if road=='FW_E' and cell==i and manifest['cutoff']<t<=manifest['cutoff']+450)
            summaries.append(dict(arm=arm,ramp=ramp,cell=i,steps=len(group),
                storage_binding_steps=sum(r['storage_binding'] for r in group),
                above_fd_peak_steps=sum(r['above_fd_peak'] for r in group),
                storage_supply_min_vph=min(r['storage_supply_vph'] for r in group),
                nominal_fd_peak_mean_vph=rate_mean('nominal_fd_peak_vph'),
                model_combined_mean_vph=rate_mean('combined_vph'),
                actual_combined_mean_vph=(actual_main+actual_merge)*3600/450,
                model_main_veh=main_count,actual_main_veh=actual_main,
                model_merge_veh=merge_count,actual_merge_veh=actual_merge))
        all_rows+=observations
        print(json.dumps(dict(arm=arm,baseline_arrays_exact=True,recorded_steps=tick)),flush=True)
    with (out/'allocation_steps.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(all_rows[0]));writer.writeheader();writer.writerows(all_rows)
    save(out/'summary.json',dict(rows=summaries,new_rollouts=2,baseline_arrays_exact=True,
        predicted_allocation_reconstruction_passed=True,new_native_runs=0,production_changed=False))
    print(json.dumps(summaries),flush=True)


def decision_regret_check():
    """Reuse the finite grid; freeze by training choice loss, check eight arms."""
    cached=load(DECISIONS/'screen.json');out=HERE/'decision_regret_check'
    out.mkdir(exist_ok=False)
    ranking=[]
    for candidate in cached['candidates']:
        ranking.append(dict(delta_merge=candidate['delta_merge'],carlson_E=candidate['carlson_E'],
            train_choice_loss=sum(c['component_regret'] for c in candidate['choices']),
            train_choices=candidate['choices'],previous_delta_cost_loss=candidate['loss']))
    # Among identical training choices, prefer the smaller merge change and
    # the VSL coefficient closest to the existing E=4. No checking outcomes.
    ranking.sort(key=lambda r:(r['train_choice_loss'],r['delta_merge'],-r['carlson_E']))
    selected=ranking[0]
    save(out/'selection.json',dict(selected=selected,ranking=ranking,
        policy='Minimize sum of observed candidate regret on the two existing training states; exact ties: smaller delta, then larger E. No new grid or fitted reward.',
        evidence_sha256=sha(DECISIONS/'screen.json'),independent_holdout=False,
        selection_frozen_before_check_predictions=True,max_new_rollouts=8))
    sys.path.insert(0,str(ROOT))
    from evaluation.controllers import lane_plant_runtime as lpr
    from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.boundary_factory import ObservationData
    from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.scoring import score_rollout
    context=lpr.load_sources(HERE/'selected/plant_n31_v2.json');model=context['component']
    for ramp in model.ramps.values():
        if ramp['road']=='FW_E':
            cell=str(ramp['to_cell'])
            model.base.network.freeway_state_response['FW_E']['cell_overrides'].setdefault(cell,{})['delta_merge']=selected['delta_merge']
    model.base.network.freeway_vsl_fd_response['FW_E']['E']=selected['carlson_E']
    baseline=next(r for r in cached['checks'] if r['delta_merge']==1 and r['carlson_E']==4)
    actual={(r['case'],r['arm']):r['actual'] for r in baseline['rows']}
    records=[r for r in load(DECISIONS/'capture.json')['records'] if r['role']=='check']
    assert len(records)==8
    ids={str(v['connector']) for v in model.ramps.values() if v['road']=='FW_E'}
    ids|={off for off,v in model.offramps.items() if v['road']=='FW_E'}
    rows=[]
    for record in records:
        args,kwargs=read_primitive_capture(record['input'],record['sha256'])
        assert args[2]==context['parameters']
        pred=model.rollout(*args,**kwargs)
        with gzip.open(out/(record['case']+'_'+record['arm']+'.json.gz'),'wt',encoding='utf-8') as f:json.dump(pred,f,allow_nan=False)
        truth=ObservationData(record['truth'])
        score=score_rollout(truth,record['cutoff'],pred,'FW_E',include_source_boundary=True)
        assert not score['invalid']
        t0=record['cutoff'];times=[round(t0+d,6) for d in range(0,451,30)]
        main={t:sum(x['n_veh'] for x in pred['cells'] if abs(x['time_s']-t)<1e-6) for t in times[1:]}
        port={t:sum(x['n_veh'] for x in pred['ports'] if abs(x['time_s']-t)<1e-6)+
            sum(x['end']['connector_veh'] for x in pred['ramps'] if abs(x['end_sec']-t)<1e-6) for t in times[1:]}
        main[t0]=sum(x['n_veh'] for x in args[0] if x['road']=='FW_E')
        port[t0]=sum(float(truth.ports[t0,off]['end_n_veh']) for off in ids)
        integral=lambda v:sum((v[a]+v[b])*(b-a)/7200 for a,b in zip(times,times[1:]))
        residual=max(abs(x['conservation_residual_veh']) for x in pred['ports']+pred['ramps'])
        assert residual<1e-7
        costs=dict(main=integral(main),port=integral(port));costs['total']=sum(costs.values())
        rows.append(dict(case=record['case'],arm=record['arm'],reference=record['reference'],
            predicted=costs,actual=actual[record['case'],record['arm']],conservation_max=residual))
        print(json.dumps(dict(case=record['case'],arm=record['arm'],ttt=costs['total'])),flush=True)
    choices=[]
    for case in sorted({r['case'] for r in rows}):
        group=[r for r in rows if r['case']==case];reference=next(r for r in group if r['arm']==r['reference'])
        for r in group:
            r['predicted_delta']=r['predicted']['total']-reference['predicted']['total']
            r['actual_delta']=r['actual']['total']-reference['actual']['total']
        ordered=sorted(group,key=lambda r:r['predicted']['total']);pick=ordered[0]
        best=min(group,key=lambda r:r['actual']['total'])
        choices.append(dict(case=case,selected=pick['arm'],observed_best=best['arm'],
            component_regret=pick['actual']['total']-best['actual']['total'],
            predicted_margin_to_second=ordered[1]['predicted']['total']-pick['predicted']['total']))
    save(out/'summary.json',dict(selected=selected,rows=rows,choices=choices,
        previous_choices=baseline['choices'],new_rollouts=8,new_training_rollouts=0,
        production_adopted=False,gain_qualified=False,native_runs=0,
        scope='East31 plus8 connectors only; seed43/47 previously inspected development checks, not pristine validation.',
        pins={str(p):sha(p) for p in (Path(__file__),HERE/'selected/plant_n31_v2.json',DECISIONS/'capture.json')}))
    print(json.dumps(dict(choices=choices)),flush=True)


def off_entry_response():
    """Identify a binding observed-entry proxy; eight fixed diagnostic forecasts."""
    sys.path.insert(0,str(ROOT))
    from evaluation.controllers import lane_plant_runtime as lpr
    from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.boundary_factory import ObservationData
    from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.scoring import score_rollout
    context=lpr.load_sources(HERE/'selected/plant_n31_v2.json');model=context['component']
    from evaluation.controllers import area_freeway_accounting as accounting
    manifest=load(OUT/'capture.json');out=HERE/'off_entry_response'
    out.mkdir(exist_ok=False)
    assert context['document']['sources']['network']['sha256']==manifest['source_network']
    save(out/'protocol.json',dict(
        hypothesis='A held observed off-entry rate is used as receiving capacity even with spare physical storage; identify binding before changing any production setting.',
        variants=['storage_and_proxy','storage'],max_rollouts=8,
        unchanged='Initial state, all parameters, splits, arrival/drain forecasts, controls, storage, travel time and cost.',
        source='Existing common2670.1 state seed29; development evidence, not an independent holdout.',
        scope='East31 and4on/4off connector residence; not whole Omega or all outside waiting.',
        production_adopted=False,native_runs=0,
        pins={str(p):sha(p) for p in (Path(__file__),OUT/'capture.json',HERE/'selected/plant_n31_v2.json',
            Path(accounting.__file__),Path(sys.modules[model.__class__.__module__].__file__))}))
    original=accounting._freeway_substep_events;rows=[]
    for mode in ('storage_and_proxy','storage'):
        for record in manifest['records']:
            args,kwargs=read_primitive_capture(OUT/record['input'],record['sha256'])
            assert args[2]==context['parameters']
            assert kwargs['port_dynamics']['entry_capacity_mode']=='storage_and_proxy'
            kwargs['port_dynamics']['entry_capacity_mode']=mode
            counters={off:dict(steps=0,binding_steps=0,proxy_below_storage_steps=0,
                blocked_request_veh=0.,accepted_veh=0.,min_storage_room_veh=float('inf'))
                for off,spec in model.offramps.items() if spec['road']=='FW_E'}
            def observe(state,control,demand,cfg,**options):
                dt=cfg.simulation.T_f_h
                caps=options['offramp_capacity_veh_h']
                available={off:float(state.urban_link_storage[cfg.network.off_ramp_storage_link[off]])
                           for off in counters}
                value=original(state,control,demand,cfg,**options);diag=value[1]
                for off,counter in counters.items():
                    blocked=diag['offramp_blocked_flow_'+off]
                    counter['steps']+=1
                    counter['binding_steps']+=int(blocked>1e-7)
                    counter['proxy_below_storage_steps']+=int(caps[off]*dt<available[off]-1e-7)
                    counter['blocked_request_veh']+=blocked*dt
                    counter['accepted_veh']+=diag['offramp_flow_'+off]*dt
                    counter['min_storage_room_veh']=min(counter['min_storage_room_veh'],available[off])
                return value
            accounting._freeway_substep_events=observe
            try:pred=model.rollout(*args,**kwargs)
            finally:accounting._freeway_substep_events=original
            arm=record['arm']
            if mode=='storage_and_proxy':
                with gzip.open(OUT/(arm+'_prediction.json.gz'),'rt') as f:old=json.load(f)
                assert all(json.loads(json.dumps(pred[k]))==old[k] for k in ('cells','flows','ports','ramps'))
            with gzip.open(out/(mode+'_'+arm+'.json.gz'),'wt',encoding='utf-8') as f:json.dump(pred,f,allow_nan=False)
            truth=ObservationData(record['truth']) # Future evidence opened after prediction only.
            score=score_rollout(truth,manifest['cutoff'],pred,'FW_E',include_source_boundary=True)
            assert not score['invalid']
            t0=manifest['cutoff'];times=[round(t0+d,6) for d in range(0,451,30)]
            ids={str(v['connector']) for v in model.ramps.values() if v['road']=='FW_E'}|set(counters)
            main={t:sum(x['n_veh'] for x in pred['cells'] if abs(x['time_s']-t)<1e-6) for t in times[1:]}
            port={t:sum(x['n_veh'] for x in pred['ports'] if abs(x['time_s']-t)<1e-6)+
                sum(x['end']['connector_veh'] for x in pred['ramps'] if abs(x['end_sec']-t)<1e-6) for t in times[1:]}
            main[t0]=sum(x['n_veh'] for x in args[0] if x['road']=='FW_E')
            port[t0]=sum(float(truth.ports[t0,off]['end_n_veh']) for off in ids)
            integral=lambda v:sum((v[a]+v[b])*(b-a)/7200 for a,b in zip(times,times[1:]))
            residual=max(abs(x['conservation_residual_veh']) for x in pred['ports']+pred['ramps'])
            assert residual<1e-7
            previous=load(OUT/(arm+'_result.json'))
            row=dict(mode=mode,arm=arm,main_ttt=integral(main),port_ttt=integral(port),
                actual_component_ttt=previous['actual_component_ttt'],off_entry=counters,
                flows={k:sum(float(x[k]) for x in pred['flows']) for k in
                    ('source_admissions','off_departures','terminal_exits')},
                conservation_max=residual,invalid=score['invalid'])
            row['component_ttt']=row['main_ttt']+row['port_ttt'];rows.append(row)
            save(out/(mode+'_'+arm+'_summary.json'),row)
            print(json.dumps(dict(mode=mode,arm=arm,ttt=row['component_ttt'])),flush=True)
    for row in rows:
        held=next(r for r in rows if r['mode']==row['mode'] and r['arm']=='hold')
        row['predicted_delta']=row['component_ttt']-held['component_ttt']
        row['actual_delta']=row['actual_component_ttt']-held['actual_component_ttt']
    save(out/'summary.json',dict(rows=rows,new_rollouts=8,baseline_arrays_exact=True,
        production_adopted=False,gain_qualified=False,native_runs=0))


def prepare_seed53_response():
    """Freeze the previously selected partial improvement before new traffic."""
    import os,re,shutil,subprocess
    from evaluation.controllers import lane_plant_runtime as lpr
    out=HERE/'heldout53_response_v2';runs=Path('D:/VISSIM_runs/20260928_release2670_s53_v2')
    assert not out.exists() and not runs.exists(), 'Preserve previous attempts; no automatic retry'
    context=lpr.load_sources(HERE/'selected/plant_n31_v2.json')
    chosen=load(HERE/'decision_regret_check/selection.json')['selected']
    assert chosen['delta_merge']==4. and chosen['carlson_E']==2.
    out.mkdir();runs.mkdir();(runs/'source').mkdir();(runs/'runtime').mkdir()
    baseline=load(HERE/'selected/plant_n31_v2.json')
    original_config=ROOT/baseline['sources']['reference_config']['path']
    config=load(original_config)
    cells=sorted({int(r['to_cell']) for r in context['component'].ramps.values() if r['road']=='FW_E'})
    assert cells==[10,12,21,23]
    for cell in cells:
        config['freeway']['state_response']['FW_E']['cell_overrides'].setdefault(str(cell),{})['delta_merge']=4.
    assert config['freeway']['vsl_fd_response']['FW_E']['E']==4.
    config['freeway']['vsl_fd_response']['FW_E']['E']=2.
    save(out/'candidate_config.json',config)
    candidate=copy.deepcopy(baseline)
    candidate['sources']['reference_config']=dict(path=(out/'candidate_config.json').relative_to(ROOT).as_posix(),sha256=sha(out/'candidate_config.json'))
    candidate['qualification']='FROZEN EXPERIMENTAL delta4/E2: partial choice-loss improvement, not gain qualified or production adopted.'
    save(out/'candidate_manifest.json',candidate)
    check=lpr.load_sources(out/'candidate_manifest.json')['component']
    assert check.base.network.freeway_vsl_fd_response['FW_E']['E']==2.
    assert all(check.base.network.freeway_state_response['FW_E']['cell_overrides'][str(c)]['delta_merge']==4. for c in cells)
    source=ROOT/baseline['sources']['network']['path'];raw=source.read_bytes()
    assert sha(source)=='64cf5f55fe9990f3e25bc4fedebf4ab1e4634c8138dbcf5697a136c48cb559dc'
    revised,count=re.subn(rb'(<simulation\b[^>]*\brandSeed=")29(")',rb'\g<1>53\2',raw)
    assert count==1 and re.sub(rb'(<simulation\b[^>]*\brandSeed=")53(")',rb'\g<1>29\2',revised)==raw
    prior=Path('D:/VISSIM_runs/20260924_release2670_s29')
    for p in (prior/'source').iterdir():
        if p.is_file() and p.suffix.lower()!='.inpx':shutil.copy2(p,runs/'source'/p.name)
    arms=['hold','release','hold_vsl90','release_vsl90'];profiles={};plans=[];pins={}
    for arm in arms:
        profile=load(prior/(arm+'.json'));assert profile['network_sha256']==sha(source) and profile['seed']==29
        network=runs/'source'/f'release2670_s53_{arm}.inpx';network.write_bytes(revised)
        profile.update(network_sha256=sha(network),seed=53)
        path=runs/(arm+'.json');save(path,profile);profiles[arm]=profile
        prepared=runs/('prepared_'+arm)
        env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(OLD))
        command=[sys.executable,'-B',str(OLD/'diagnostics/fast_fixed_profile.py'),
            '--network',str(network),'--profile',str(path),'--output',str(prepared)]
        result=subprocess.run(command,cwd=OLD,env=env,text=True,encoding='utf-8',capture_output=True)
        (out/(arm+'_prepare.log')).write_text(result.stdout+result.stderr,encoding='utf-8')
        assert result.returncode==0, result.stderr[-2000:]
        metadata=load(prepared/'prepared.json');metadata['concurrent_identity_network_stem']=network.stem
        save(prepared/'prepared.json',metadata)
        pins.update(metadata['snapshot_sha256']);pins[str(prepared/'prepared.json')]=sha(prepared/'prepared.json')
        plans.append(dict(arm=arm,prepared=str(prepared),output=str(runs/arm/'run')))
    prefix=lambda p:{k:[r for r in p[k] if r['time_s']<2700] for k in ('meter_commands','vsl_commands')}
    assert all(prefix(p)==prefix(profiles['hold']) for p in profiles.values())
    for name in ('fast_nc_run.ps1','fast_nc_runner.vbs','fast_fixed_profile_verify.py','validate_native_signal_record.py'):
        original=OLD/'diagnostics'/name;dest=runs/'runtime'/name;shutil.copy2(original,dest)
        assert sha(dest)==sha(original);pins[str(dest)]=sha(dest)
    sources=[HERE/'selected/plant_n31_v2.json',HERE/'decision_regret_check/selection.json',Path(__file__)]
    sources.extend(ROOT/p for p in context['component'].provenance['model_files'])
    sources.extend(ROOT/v['path'] for v in baseline['sources'].values())
    sources.extend([out/'candidate_config.json',out/'candidate_manifest.json'])
    model_pins={str(p):sha(p) for p in sources}
    save(out/'protocol.json',dict(seed=53,cutoff_sec=2670.1,horizon_sec=450,intervention_sec=2700,terminal_sec=3300,
        arms=arms,plans=plans,results_root=str(runs),source_network_sha256=sha(source),seed53_network_sha256=hashlib.sha256(revised).hexdigest(),
        candidate=dict(delta_merge=4.,carlson_E=2.,cells=cells,production_adopted=False),
        model_pins=model_pins,execution_pins=pins,parameters_frozen_before_new_traffic=True,
        controls='Replay the previously verified seed29 ALINEA command history on fresh seed53 traffic; same history through2550. Then hold or legal+2s/150s east-meter release, with/without90kph atDSD63..66. Not liveALINEA or unconditionalNC.',
        unchanged='All demand/routes/geometry/urban signals/entryDSD110, SimRes10,FZP5s,RED/GREEN meter timing; only traffic seed changes.',
        evaluation='Compare frozen baseline and delta4/E2 on identical fresh-state inputs. Predict before reading future targets. Costs: east31+8connector and separately wholeOmega/outside/native latent costs. No coefficient refit using this seed.',
        finite_run_count=4,max_concurrent=4,automatic_retries=0,native_started=False))
    save(runs/'preflight.json',dict(passed=True,plans=plans,pins=pins,seed=53,terminal_sec=3300,
        common_command_prefix_exact=True,model_protocol=str(out/'protocol.json'),model_protocol_sha256=sha(out/'protocol.json')))
    print(json.dumps(dict(prepared=str(out),runs=str(runs),native_started=False,profiles=4)),flush=True)


def recovery_response(*, local_merge=False, recovery_pair=False):
    """Bounded one-parameter recovery test, selected on seed29 reference flows.

    Existing causal recovery relaxation only; no new model equation. Independent
    seed/control responses are evaluated AFTER freezing the selection.
    """
    from evaluation.controllers import lane_plant_runtime as lpr
    from evaluation.controllers.freeway_fd import configure_state_response
    from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.boundary_factory import ObservationData
    out=HERE/'closedloop9000_d4e2_analysis'/('recovery_cells24_25' if recovery_pair else 'local_merge_cell23' if local_merge else 'recovery_response')
    out.mkdir(exist_ok=recovery_pair)
    assert not (out/'protocol.json').exists(), 'Preserve completed calibration'
    source=HERE/'heldout53_response_v2/candidate_manifest.json'
    ctx=lpr.load_sources(source);model=ctx['component']
    response=copy.deepcopy(model.base.network.freeway_state_response)
    records=load(DECISIONS/'capture.json')['records']
    for r in load(HERE/'heldout53_response_v2/capture.json')['records']:
        records.append(dict(r,case='s53_late',cutoff=2670.1,reference='hold',
            truth=str(HERE/'heldout53_response_v2/observations'/r['arm'])))
    # Contiguous two ramp-group influence interval, same coefficient in all
    # cells. Existing rho-gradient and desired>current predicates stay intact.
    affected=list(range(21,26)) if local_merge else list(range(9,26))
    variants={'baseline':None,'tau8':8.,'tau6':6.,'tau4':4.}
    if local_merge:
        variants={'baseline':None}
        nominal=response['FW_E']['cell_overrides']['23']['anticipation']['downstream_lt_local']
        for fraction in (0.,0.25,0.5,1.):
            for delta in (1.,2.,4.):
                if fraction==1. and delta==4.:continue
                variants[f'nu{fraction:g}_delta{delta:g}']=dict(nu_lower_downstream=nominal*fraction,delta_merge=delta)
    reused={}; new_count=0
    if recovery_pair:
        affected=[24,25]
        prior=out.parent/'local_merge_cell23'
        variants={'baseline':None,'cell23':None}
        candidates={
            'acc6':{'recovery_relaxation':{'acceleration_sec':6.}},
            'dec24':{'relaxation':{'acceleration_sec':12.,'deceleration_sec':24.}},
            'acc6_dec24':{'relaxation':{'acceleration_sec':12.,'deceleration_sec':24.},
                          'recovery_relaxation':{'acceleration_sec':6.}},
        }
        for name,setting in candidates.items():
            variants['recovery_'+name]=setting
            variants['combined_'+name]=setting
    protocol=dict(variants=variants,affected_cells=affected,model_reference=str(source),
        train='Only seed29 early/late reference commands; no DeltaTTT fitting',
        selection='Mean normalized stock RMSE plus downstream-count RMSE; each training metric must not worsen >5% versus baseline.',
        check='Frozen selection on all saved commands, seed43/47/53; these seeds were inspected earlier, not pristine blind holdouts.',
        unchanged='FD, critical densities, sending/receiving, merge, lane loss, VSL response, route fractions, objective and horizon.',
        coefficient='Existing recovery_relaxation acceleration_sec; nu/tau pressure ratio preserved.',
        max_rollouts=44,new_native=0,optimizer_iterations=0,production_adopted=False,
        pins={str(p):sha(p) for p in (source,HERE/'decision_response/capture.json',HERE/'heldout53_response_v2/capture.json',Path(__file__))})
    if local_merge:
        protocol.update(train='Seed29 late2670.1 hold and gradual release; physical state/flow errors, no cost/rank fitting',
            affected_cells=[23],score_cells=affected,variants=variants,max_rollouts=62,
            coefficient='Existing cell23 downstream-lower-density anticipation and delta_merge only. No new equations.',
            unchanged='All other cells, formation anticipation, FD, recovery time, conservation, demand, command, objective and horizon.',
            selection='Minimize local normalized stock+flow+speed RMSE; whole east31 stock and flow RMSE in each training arm must stay within5% of baseline.')
    if recovery_pair:
        protocol.update(train='Seed29 late2670.1 hold/release only; coefficients frozen before scoring other cases',
            variants=variants,affected_cells=[24,25],diagnostic_cells=[21,22,23,24,25],
            selection='One shared24/25 parameter set: mean normalized N/v/q+terminal RMSE across both cell23 contexts. Each whole31 N/q training RMSE <=1.05 its matching context. No DeltaTTT fitting.',
            max_rollouts=48,max_coefficient_candidates=3,max_wall_sec=1800,
            coefficient='Existing recovery acceleration6s; asymmetric deceleration24s; their combination.24/25 always share coefficients. Deceleration tau also reduces nu/tau; recovery override preserves pressure ratio.',
            unchanged='Cell21/22 and all other cells except existing cell23 variant; FD, critical density, convection coefficient, conservation, actual merges, dynamic off storage/drain/spillback, demand, objective, control and forecast horizon.',
            comparison='baseline/cell23/recovery-only/combined;40 completed baseline/cell23 predictions reused with hashes',
            state_condition='Canonical current predicted desired>speed/downstream<=rho/downstream<critical for recovery; desired>=speed for general relaxation. No seed/time/control bonus.',
            event_definition='30s snapshots. Congestion<60kmh, recovery>=80kmh for3 consecutive snapshots after congestion; censored within450s. Diagnostic thresholds, not coefficient selection targets.',
            stop_rule='Single grid only. If no admitted improvement, preserve least-error candidate as rejected diagnostic; no repeated parameter search. Reject premature clearing of sustained release congestion.',
            known_data_limit='seed47 VSL90 has4 unexplained losses and is excluded from clean ranking. Other seeds were historically inspected, not pristine blind holdouts.')
    save(out/'protocol.json',protocol)
    overall_begin=time.perf_counter()
    inputs={};results={};truth_cache={}
    for r in records:
        inputs[r['case'],r['arm']]=read_primitive_capture(r['input'],r['sha256'])
    def run(name,r):
        nonlocal new_count
        key=(name,r['case'],r['arm'])
        if key in results:return results[key]
        spec=copy.deepcopy(response)
        if recovery_pair and (name=='cell23' or name.startswith('combined_')):
            spec['FW_E']['cell_overrides']['23']['anticipation']['downstream_lt_local']=4.59375
            spec['FW_E']['cell_overrides']['23']['delta_merge']=2.
        if variants[name] is not None:
            if recovery_pair:
                for cell in affected:
                    spec['FW_E']['cell_overrides'][str(cell)].update(copy.deepcopy(variants[name]))
            elif local_merge:
                local=spec['FW_E']['cell_overrides']['23']
                local['anticipation']['downstream_lt_local']=variants[name]['nu_lower_downstream']
                local['delta_merge']=variants[name]['delta_merge']
            else:
                for cell in affected:
                    spec['FW_E']['cell_overrides'].setdefault(str(cell),{})['recovery_relaxation']={'acceleration_sec':variants[name]}
        configure_state_response(model.base,{'freeway':{'state_response':spec}})
        a,k=copy.deepcopy(inputs[r['case'],r['arm']]);assert a[2]==ctx['parameters']
        folder=out/name;folder.mkdir(exist_ok=True)
        pred_path=folder/(r['case']+'_'+r['arm']+'.json.gz')
        if recovery_pair and name in ('baseline','cell23'):
            pred_path=prior/('baseline' if name=='baseline' else 'nu0.25_delta2')/pred_path.name
            reused[str(pred_path)]=sha(pred_path)
            with gzip.open(pred_path,'rt',encoding='utf-8') as f:pred=json.load(f)
            wall=0.
        else:
            if recovery_pair:
                assert new_count<48 and time.perf_counter()-overall_begin<1800, 'Predeclared budget exhausted'
            begin=time.perf_counter();pred=model.rollout(*a,**k);wall=time.perf_counter()-begin
            new_count+=1
            with gzip.open(pred_path,'wt',encoding='utf-8') as f:json.dump(pred,f,allow_nan=False)
        if recovery_pair:save(folder/'state_response.json',spec)
        # Targets enter only scoring, after autonomous prediction has finished.
        if r['truth'] not in truth_cache:truth_cache[r['truth']]=ObservationData(r['truth'])
        truth=truth_cache[r['truth']];t0=r['cutoff'];times=[round(t0+d,6) for d in range(0,451,30)]
        observed={(t,int(z['cell'])):z for t in times for z in truth.cells[t] if z['road']=='FW_E'}
        predicted={(round(z['time_s'],6),z['cell']):z for z in pred['cells']}
        n_pairs=[(predicted[t,c]['n_veh'],float(observed[t,c]['n_veh'])) for t in times[1:] for c in affected]
        # Includes terminal because its timing changes the residence objective.
        selected_cells=affected+[30]
        pflows={(round(z['window_end_s'],6),z['cell']):z for z in pred['flows']}
        q_pairs=[]
        for t in times[1:]:
            for c in selected_cells:
                pn='terminal_exits' if c==30 else 'downstream_crossings'
                an='terminal_exits_inferred' if c==30 else 'downstream_crossings'
                q_pairs.append((pflows[t,c][pn],float(truth.flows[t,'FW_E',c][an])))
        def error(pairs):
            rmse=math.sqrt(sum((a-b)**2 for a,b in pairs)/len(pairs))
            return dict(rmse=rmse,normalized=rmse/max(1.,sum(b for _,b in pairs)/len(pairs)))
        errors=dict(stock=error(n_pairs),flow=error(q_pairs))
        whole_errors=None
        if local_merge or recovery_pair:
            v_pairs=[(predicted[t,c]['v_kmh'],float(observed[t,c]['v_kmh'])) for t in times[1:] for c in affected if observed[t,c]['v_kmh'] not in ('',None)]
            errors['speed']=error(v_pairs)
            whole_errors=dict(stock=error([(predicted[t,c]['n_veh'],float(observed[t,c]['n_veh'])) for t in times[1:] for c in range(31)]),
                flow=error([(pflows[t,c]['terminal_exits' if c==30 else 'downstream_crossings'],
                    float(truth.flows[t,'FW_E',c]['terminal_exits_inferred' if c==30 else 'downstream_crossings'])) for t in times[1:] for c in range(31)]))
        ids={str(v['connector']) for v in model.ramps.values() if v['road']=='FW_E'}|{str(o) for o,v in model.offramps.items() if v['road']=='FW_E'}
        costs={}
        for kind in ('predicted','actual'):
            main={t:sum(float(z['n_veh']) for (stamp,c),z in (predicted if kind=='predicted' else observed).items() if stamp==t) for t in times}
            ports={t:(sum(z['n_veh'] for z in pred['ports'] if abs(z['time_s']-t)<1e-6)+sum(z['end']['connector_veh'] for z in pred['ramps'] if abs(z['end_sec']-t)<1e-6)
                if kind=='predicted' else sum(float(truth.ports[t,no]['end_n_veh']) for no in ids)) for t in times}
            main[t0]=sum(float(z['n_veh']) for (stamp,c),z in observed.items() if stamp==t0)
            ports[t0]=sum(float(truth.ports[t0,no]['end_n_veh']) for no in ids)
            integ=lambda d:sum((d[a]+d[b])*(b-a)/7200 for a,b in zip(times,times[1:]))
            costs[kind]=dict(main=integ(main),ports=integ(ports),total=integ(main)+integ(ports))
        residual=max(abs(z['conservation_residual_veh']) for z in pred['ports']+pred['ramps']);assert residual<1e-7
        result=dict(variant=name,case=r['case'],arm=r['arm'],reference=r['reference'],wall_sec=wall,
            errors=errors,whole_errors=whole_errors,score=sum(v['normalized'] for v in errors.values()),costs=costs,conservation_max=residual,
            source_admissions=sum(z['source_admissions'] for z in pred['flows']),
            off_departures=sum(z['off_departures'] for z in pred['flows']),terminal_exits=sum(z['terminal_exits'] for z in pred['flows']),
            merge=sum(z['accepted_merge_veh'] for z in pred['ramps']))
        if recovery_pair:
            def events(series):
                low=[t for t,v in series if v<60.]
                onset=low[0] if low else None
                recovered=next((series[i][0] for i in range(len(series)-2)
                    if onset is not None and series[i][0]>onset and all(v>=80. for t,v in series[i:i+3])),None)
                return dict(onset_sec=onset,recovered_sec=recovered,low_speed_sample_sec=30*len(low),
                    recovery_censored=onset is not None and recovered is None)
            metrics=[]
            for c in range(21,26):
                z=dict(cell=c)
                for kind,table in [('predicted',predicted),('actual',observed)]:
                    cells=[table[t,c] for t in times[1:]]
                    velocities=[(t,float(table[t,c]['v_kmh'])) for t in times[1:] if table[t,c]['v_kmh'] not in ('',None)]
                    z[kind]=dict(mean_speed_kmh=sum(v for _,v in velocities)/len(velocities),
                        end_n_veh=float(cells[-1]['n_veh']),
                        downstream_veh=sum(float((pflows[t,c] if kind=='predicted' else truth.flows[t,'FW_E',c])['downstream_crossings']) for t in times[1:]),
                        events=events(velocities))
                metrics.append(z)
            result.update(prediction=str(pred_path),prediction_sha256=sha(pred_path),cell_metrics=metrics,
                end_stock=sum(float(predicted[times[-1],c]['n_veh']) for c in range(31)),
                scope='East31+8connector residence; urban waiting and full Omega require coupled check')
        save(folder/(r['case']+'_'+r['arm']+'_result.json'),result);results[key]=result
        print(json.dumps(dict(variant=name,case=r['case'],arm=r['arm'],score=result['score'],cost=costs['predicted']['total'])),flush=True)
        return result
    train=[r for r in records if r['case'].startswith('s29_') and r['arm']==r['reference']]
    if local_merge or recovery_pair:train=[r for r in records if r['case']=='s29_late' and r['arm'] in ('hold','release')]
    assert len(train)==2
    scores=[]
    for name in variants:
        rows=[run(name,r) for r in train]
        admitted=all(row['errors'][m]['rmse']<=1.05*results['baseline',row['case'],row['arm']]['errors'][m]['rmse'] for row in rows for m in ('stock','flow'))
        if local_merge or recovery_pair:
            context='cell23' if recovery_pair and name.startswith('combined_') else 'baseline'
            admitted=all(row['whole_errors'][m]['rmse']<=1.05*results[context,row['case'],row['arm']]['whole_errors'][m]['rmse'] for row in rows for m in ('stock','flow'))
        scores.append(dict(name=name,score=sum(z['score'] for z in rows)/len(rows),admitted=admitted))
    selected=min((s for s in scores if s['admitted']),key=lambda s:s['score'])['name']
    selection=dict(selected=selected,training_scores=scores,heldout_read_for_selection=False)
    comparison=list(dict.fromkeys(['baseline',selected]))
    if recovery_pair:
        score_map={s['name']:s for s in scores}
        paired=[dict(name=n,score=sum(score_map[p+n]['score'] for p in ('recovery_','combined_'))/2,
            admitted=all(score_map[p+n]['admitted'] for p in ('recovery_','combined_'))) for n in candidates]
        baseline_score=(score_map['baseline']['score']+score_map['cell23']['score'])/2
        feasible=[s for s in paired if s['admitted']]
        selected=min(feasible or paired,key=lambda s:s['score'])['name']
        improves=bool(feasible) and next(s['score'] for s in paired if s['name']==selected)<baseline_score
        selection.update(selected=selected,paired_scores=paired,baseline_score=baseline_score,training_improved=improves,
            adopted=False,status='frozen_for_validation' if improves else 'rejected_training_diagnostic_only')
        comparison=['baseline','cell23','recovery_'+selected,'combined_'+selected]
    save(out/'frozen_selection.json',selection)
    choices=[]
    for name in comparison:
        for r in records:run(name,r)
        for case in sorted({r['case'] for r in records}):
            rows=[z for (v,c,a),z in results.items() if v==name and c==case and not (recovery_pair and c=='s47_late' and a=='hold_vsl90')]
            held=next(z for z in rows if z['arm']==z['reference'])
            for z in rows:
                z['predicted_delta']=z['costs']['predicted']['total']-held['costs']['predicted']['total']
                z['actual_delta']=z['costs']['actual']['total']-held['costs']['actual']['total']
            best=min(rows,key=lambda z:z['costs']['predicted']['total']);actual=min(rows,key=lambda z:z['costs']['actual']['total'])
            choices.append(dict(variant=name,case=case,selected=best['arm'],actual_best=actual['arm'],
                regret=best['costs']['actual']['total']-actual['costs']['actual']['total']))
    save(out/'summary.json',dict(selected=selected,training_scores=scores,rows=list(results.values()),choices=choices,
        rollouts=len(results),new_native=0,production_adopted=False,gain_qualified=False,optimizer_iterations=0,
        new_rollouts=new_count,reused_predictions=reused,wall_sec=time.perf_counter()-overall_begin,
        comparison=comparison,selection=selection,
        scope='East31+8connector costs only; not full Omega or outside waiting.'))
    print(json.dumps(dict(selected=selected,choices=choices)),flush=True)


def local_speed_balance(*, recovery_pair=False):
    """Conditional speed-term audit, no fitting or autonomous rollout.

    Existing 30s snapshots and only the preceding30s merge count are supplied
    to the canonical1s speed update. The observed next30s trend is a descriptive
    comparator, NOT a same-vehicle acceleration measurement or forecast input.
    """
    sys.path.insert(0,str(ROOT/'vendor/NumSim-mine'))
    from evaluation.controllers import lane_plant_runtime as lpr
    from evaluation.controllers import area_freeway_accounting as accounting
    from evaluation.controllers.freeway_fd import cell_state_response, state_response_coefficients, literature_desired_speed
    from src.models.state import ControlAction
    out=HERE/'closedloop9000_d4e2_analysis'/('recovery_cells24_25/conditional_terms' if recovery_pair else 'recovery_response/seed47_audit/speed_balance')
    out.parent.mkdir(parents=True,exist_ok=True)
    out.mkdir(exist_ok=True)
    assert not (out/'summary.json').exists(), 'Preserve the completed speed audit'
    records={r['arm']:r for r in load(DECISIONS/'capture.json')['records'] if r['case']=='s47_late'}
    pins={};native={};rows=[]
    for arm in ('hold','release_10484'):
        folder=Path(records[arm]['truth']);manifest=load(folder/'manifest.json')
        data={}
        for name,time_key in [('cells_30s.csv','time_s'),('flows_30s.csv','window_end_s')]:
            path=folder/name;assert sha(path)==manifest['files'][name];pins[str(path)]=sha(path)
            with path.open(encoding='utf-8-sig',newline='') as f:
                data[name]={(round(float(z[time_key]),6),int(z['cell'])):z for z in csv.DictReader(f) if z['road']=='FW_E'}
        native[arm]=data
    manifests={'baseline':HERE/'heldout53_response_v2/candidate_manifest.json',
               'tau4':out.parents[1]/'candidate_manifest.json'}
    if recovery_pair:
        manifests={'baseline':HERE/'heldout53_response_v2/candidate_manifest.json',
                   'cell23':HERE/'closedloop9000_d4e2_analysis/local_merge_cell23/candidate_manifest.json'}
    bases=('native','autonomous_prediction')
    if recovery_pair:
        bases=tuple(f'local{a}_up{b}_down{c}' for a in (0,1) for b in (0,1) for c in (0,1))
    for variant,manifest in manifests.items():
        pins[str(manifest)]=sha(manifest)
        ctx=lpr.load_sources(manifest);model=ctx['component']
        cfg=model._config('FW_E',ctx['parameters']['by_direction']['FW_E']);net=cfg.network
        maximum=max(cfg.freeway_follower.vsl_set);assert maximum==110
        control=ControlAction(vsl={'FW_E':maximum})
        for arm in native:
            path=(HERE/'closedloop9000_d4e2_analysis/local_merge_cell23'/('nu0.25_delta2' if variant=='cell23' else 'baseline')/f's47_late_{arm}.json.gz'
                  if recovery_pair else out.parents[1]/variant/f's47_late_{arm}.json.gz');pins[str(path)]=sha(path)
            with gzip.open(path,'rt',encoding='utf-8') as f:pred=json.load(f)
            pc={(round(z['time_s'],6),int(z['cell'])):z for z in pred['cells']}
            pf={(round(z['window_end_s'],6),int(z['cell'])):z for z in pred['flows']}
            for basis in bases:
                states=native[arm]['cells_30s.csv'] if basis=='native' else pc
                flows=native[arm]['flows_30s.csv'] if basis=='native' else pf
                if recovery_pair:
                    observed_local,observed_up,observed_down=(int(x[-1]) for x in basis.split('_'))
                    states=native[arm]['cells_30s.csv'] if observed_local else pc
                    flows=native[arm]['flows_30s.csv'] if observed_local else pf
                for j in range(1,15):
                    stamp=round(2670.1+30*j,6)
                    for cell in (21,22,23,24,25):
                        local=states[stamp,cell];up=states[stamp,cell-1];down=states[stamp,cell+1]
                        if recovery_pair:
                            up=(native[arm]['cells_30s.csv'] if observed_up else pc)[stamp,cell-1]
                            down=(native[arm]['cells_30s.csv'] if observed_down else pc)[stamp,cell+1]
                        v=float(local['v_kmh']);vu=float(up['v_kmh'])
                        rho=float(local['rho_veh_per_km_lane']);rd=float(down['rho_veh_per_km_lane'])
                        p=net.freeway_segment_params['FW_E'][cell]
                        length=p['segment_length_km'];lanes=net.freeway_segment_lanes['FW_E'][cell]
                        assert abs(lanes-3)<1e-10 and abs(net.freeway_segment_lanes['FW_E'][cell+1]-3)<1e-10
                        vsl=accounting._mn.segment_vsl(control,'FW_E',cell,cfg)
                        desired=accounting._mn.effective_desired_speed_kmh(rho,net.v_free,net.rho_crit,vsl,
                            net.alpha_vsl,False,net.metanet_a_m,False,net.rho_max,0.)
                        desired=literature_desired_speed((getattr(net,'freeway_vsl_fd_response',{}) or {}).get('FW_E'),
                            cfg,'FW_E',cell,rho,desired,vsl,False)
                        nu0=accounting._mn.select_anticipation_nu(rho,net,vsl)
                        spec=cell_state_response(net,'FW_E',cell)
                        tau,nu=state_response_coefficients(spec,v,desired,rho,rd,p['rho_crit'],p['metanet_tau_h'],nu0)
                        kappa=p['metanet_kappa_veh_km_lane'];dt=1/3600
                        relaxation=dt/tau*(desired-v)
                        convection=dt/length*v*(vu-v)
                        anticipation=-nu*dt/(tau*length)*(rd-rho)/(rho+kappa)
                        canonical=accounting._mn.metanet_speed_update_kmh(v,vu,rho,rd,desired,dt,length,
                            net.metanet_tau_h,nu0,net.metanet_kappa_veh_km_lane,net.v_min)
                        reconstructed=max(net.v_min,v+relaxation+convection+anticipation)
                        assert abs(canonical-reconstructed)<1e-10,(variant,arm,basis,stamp,cell,canonical,reconstructed)
                        rate=float(flows[stamp,cell]['ramp_merges'])*120
                        delta=spec.get('delta_merge',net.metanet_delta_merge)
                        merge=delta*dt*rate*v/(length*lanes*(rho+kappa))
                        final=max(net.v_min,canonical-merge)
                        following=float(states[round(stamp+30,6),cell]['v_kmh'])
                        rows.append(dict(variant=variant,arm=arm,basis=basis,time_s=stamp,cell=cell,
                            speed_kmh=v,upstream_speed_kmh=vu,rho=rho,downstream_rho=rd,desired_speed_kmh=desired,
                            preceding30_merge_vph=rate,tau_sec=tau*3600,nu=nu,delta_merge=delta,
                            relaxation_kmh_per_s=relaxation,convection_kmh_per_s=convection,
                            anticipation_kmh_per_s=anticipation,merge_loss_kmh_per_s=merge,
                            total_kmh_per_s=final-v,next30_snapshot_trend_kmh_per_s=(following-v)/30,
                            canonical_reconstruction_error=abs(canonical-reconstructed)))
    groups=[]
    for variant in manifests:
        for arm in native:
            for basis in bases:
                for cell in (21,22,23,24,25):
                    selected=[r for r in rows if (r['variant'],r['arm'],r['basis'],r['cell'])==(variant,arm,basis,cell)]
                    metrics=('relaxation_kmh_per_s','convection_kmh_per_s','anticipation_kmh_per_s',
                        'merge_loss_kmh_per_s','total_kmh_per_s','next30_snapshot_trend_kmh_per_s')
                    groups.append(dict(variant=variant,arm=arm,basis=basis,cell=cell,samples=len(selected),
                        means={k:sum(r[k] for r in selected)/len(selected) for k in metrics},
                        positive_acceleration_samples=sum(r['total_kmh_per_s']>0 for r in selected),
                        recovery_active_samples=sum(r['tau_sec']<12 for r in selected)))
    save(out/'summary.json',dict(groups=groups,rows=rows,pins=pins,source_sha256=sha(Path(__file__)),
        new_rollouts=0,new_native=0,new_coefficients=0,canonical_evaluations=len(rows),
        exact_reconstruction=True,scope='Conditional local derivative audit. Next30 snapshot changes include vehicle mixing and sampling; not observed individual acceleration.'))
    with (out/'terms.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    print(json.dumps(dict(evaluations=len(rows),cell23=[g for g in groups if g['cell']==23])),flush=True)


def cached_wave_audit():
    """Locate discharge-response errors in existing 30s caches; no forecasting."""
    manifest=load(OUT/'capture.json'); t0=manifest['cutoff']; end=t0+manifest['horizon']
    assert manifest['horizon']==450
    target=OUT/'wave_response_20260928.json'
    if target.exists():raise ValueError('Preserve the previous cached wave audit')
    pins={str(OUT/'capture.json'):sha(OUT/'capture.json')}; data={}
    for arm in ('hold','release'):
        record=next(r for r in manifest['records'] if r['arm']==arm)
        truth=Path(record['truth']); native_manifest=load(truth/'manifest.json')
        cells={}; flows={}
        for name,dest,time_key in (('cells_30s.csv',cells,'time_s'),
                                    ('flows_30s.csv',flows,'window_end_s')):
            path=truth/name; digest=sha(path); assert digest==native_manifest['files'][name]
            pins[str(path)]=digest
            with path.open(encoding='utf-8-sig',newline='') as f:
                for row in csv.DictReader(f):
                    time=round(float(row[time_key]),6)
                    if row['road']=='FW_E' and t0<time<=end:
                        dest[time,int(row['cell'])]=row
        path=OUT/(arm+'_prediction.json.gz');pins[str(path)]=sha(path)
        with gzip.open(path,'rt',encoding='utf-8') as f:pred=json.load(f)
        data['actual',arm]=(cells,flows)
        data['predicted',arm]=({(round(r['time_s'],6),int(r['cell'])):r for r in pred['cells']},
            {(round(r['window_end_s'],6),int(r['cell'])):r for r in pred['flows']})
    rows=[]
    for cell in range(31):
        for block in range(3):
            a=t0+150*block;b=a+150;times=[round(a+30*j,6) for j in range(1,6)]
            row=dict(cell=cell,start_sec=a,end_sec=b)
            for kind in ('actual','predicted'):
                arms={}
                for arm in ('hold','release'):
                    cells,flows=data[kind,arm]; c=[cells[t,cell] for t in times]; f=[flows[t,cell] for t in times]
                    eligible=[r for r in c if r['v_kmh'] not in ('',None) and float(r['n_veh'])>0]
                    weight=sum(float(r['n_veh']) for r in eligible)
                    arms[arm]=dict(downstream_veh=sum(float(r['downstream_crossings']) for r in f),
                        merge_veh=sum(float(r['ramp_merges']) for r in f),
                        off_veh=sum(float(r['off_departures']) for r in f),
                        end_stock_veh=float(c[-1]['n_veh']),
                        mean_density=sum(float(r['rho_veh_per_km_lane']) for r in c)/5,
                        vehicle_weighted_snapshot_speed_kmh=(sum(float(r['n_veh'])*float(r['v_kmh']) for r in eligible)/weight if weight else None))
                row[kind]=dict(arms=arms,delta={k:(arms['release'][k]-arms['hold'][k]
                    if arms['release'][k] is not None and arms['hold'][k] is not None else None) for k in arms['hold']})
            rows.append(row)
    with (OUT/'cell_response.csv').open(encoding='utf-8-sig',newline='') as f:
        reference={int(r['cell']):r for r in csv.DictReader(f) if r['arm']=='release'}
    for cell in range(31):
        for kind in ('actual','predicted'):
            value=sum(r[kind]['delta']['downstream_veh'] for r in rows if r['cell']==cell)
            assert abs(value-float(reference[cell][kind+'_downstream_crossings']))<1e-7
    save(target,dict(rows=rows,pins=pins,new_rollouts=0,new_native_runs=0,fzp_rescans=0,
        full_horizon_flow_parity=True,control='release minus hold at the same2670.1s microscopic state',
        speed_basis='Vehicle-weighted mean of five30s endpoint speed snapshots per150s; not a continuous trajectory mean.',
        limitations=['Retrospective localization only; not future prediction inputs or a capacity estimate.',
                     'Cell-specific speed, density and discharge differences do not alone identify their causal mechanism.']))
    print(json.dumps({'output':str(target),'cells22_23_24':[
        dict(cell=r['cell'],start_sec=r['start_sec'],actual=r['actual']['delta'],predicted=r['predicted']['delta'])
        for r in rows if r['cell'] in (22,23,24)]}),flush=True)


if __name__=='__main__':
    {'capture':capture,'predict':predict,'compare':compare_saved,'decompose':decompose_saved,
     'initial-cohort':initial_cohort_exits,'delay-bounds':cohort_delay_bounds,
     'capture-decisions':capture_decisions,'decision-screen':decision_screen,
     'anticipation-response':anticipation_response,
     'merge-speed-response':lambda:anticipation_response(merge_speed=True),
     'lane-drop-response':lambda:anticipation_response(lane_drop=True),
     'decision-regret-check':decision_regret_check,
     'receiving-audit':receiving_audit,'cached-wave-audit':cached_wave_audit,
     'recovery-response':recovery_response,'local-speed-balance':local_speed_balance,
     'local-merge-calibration':lambda:recovery_response(local_merge=True),
     'recovery-pair-terms':lambda:local_speed_balance(recovery_pair=True),
     'recovery-pair-calibration':lambda:recovery_response(recovery_pair=True),
     'prepare-seed53':prepare_seed53_response,
     'off-entry-response':off_entry_response}[sys.argv[1]]()
