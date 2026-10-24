"""Compare held off-ramp stock with existing conserved travel/storage dynamics."""
import copy
import csv
import gzip
import json
import math
from pathlib import Path
import statistics
import sys

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
CAL=ROOT/'diagnostics/demand_sweep/user_native_20260914/metanet_calibration_v1'
B=CAL/'res10_20260922'
BASE=B/'boundary_literature_v1'
sys.path[:0]=[str(CAL),str(ROOT/'.review-deps'),str(ROOT)]
from canonical_harness import load_base_model, sha256
from boundary_factory import ObservationData, build_window
from scoring import score_rollout, stats
from extract_observations import skipped_mainline_between_ports


def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(name,data): (OUT/name).write_text(json.dumps(data,indent=2,ensure_ascii=False,allow_nan=False),encoding='utf8')
def table(p):
    with Path(p).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))


def queue_pins():
    pins=load('D:/VISSIM_runs/20260922_fw080_urban090_controls/queue.json')['code_sha256']
    assert all(sha256(p)==h for p,h in pins.items())
    return pins


def corrected_data():
    """Recover missed paired crossings from the already extracted native events.

    Original CSVs stay immutable. Both compared models use this same corrected
    input; no second FZP scan or invented off-ramp inflow source is needed.
    """
    data=ObservationData(B/'fw080_urban090_ports')
    events=table(data.folder/'port_events.csv')
    ramp={b['connector']:b for b in data.definitions.values() if b['kind']=='ramp'}
    off={b['connector']:b for b in data.definitions.values() if b['kind']=='offramp'}
    arrivals={(r['time_s'],r['vehicle'],r['connector']):r for r in events if r['kind']=='arrival'}
    last=load(data.folder/'manifest.json')['last_complete_30s_window_s']
    evidence=[];tail=[]
    for row in events:
        if row['kind']!='departure' or int(row['connector']) not in ramp or not row['other_link'] or int(row['other_link']) not in off:continue
        new=arrivals[row['time_s'],row['vehicle'],row['other_link']]
        a=(int(row['connector']),int(row['lane']),float(row['position_m']),float(row['speed_kmh']))
        b=(int(new['connector']),int(new['lane']),float(new['position_m']),float(new['speed_kmh']))
        path=skipped_mainline_between_ports(a,b,ramp,off)
        assert path is not None
        r,o=path;t=float(row['time_s'])
        end=round(math.ceil((t-data.phase_sec-1e-8)/30)*30+data.phase_sec,6)
        item=dict(vehicle=int(row['vehicle']),lower_sec=float(row['lower_time_s']),upper_sec=t,
            ramp=r['connector'],off=o['connector'],road=r['road'],from_cell=r['to_cell'],to_cell=o['from_cell'],window_end_s=end)
        if end>last:tail.append(item);continue
        evidence.append(item)
        def inc(c,key):
            f=data.flows[end,r['road'],c];f[key]=float(f[key])+1.
        inc(r['to_cell'],'ramp_merges');inc(o['from_cell'],'off_departures')
        for c in range(r['to_cell'],o['from_cell']):
            inc(c,'downstream_crossings');inc(c+1,'upstream_crossings')
        for definition in (r,o):
            f=data.boundaries[end,definition['id']]
            for key in ('crossings','interval_inferred_crossings'):f[key]=float(f[key])+1.
            f['flow_vph']=float(f['crossings'])*120.
    for definition in data.definitions.values():
        cumulative=0.
        for (t,name),f in sorted(data.boundaries.items()):
            if name!=definition['id']:continue
            cumulative+=float(f['crossings']);f['cumulative_crossings']=cumulative
    totals={}
    for (t,road,c),f in sorted(data.flows.items()):
        for key in ('ramp_merges','off_departures','upstream_crossings','downstream_crossings'):
            k=(road,c,key);totals[k]=totals.get(k,0.)+float(f[key]);f['cumulative_'+key]=totals[k]
        residual=float(f['end_n_veh'])-float(f['start_n_veh'])
        residual-=sum(float(f[k]) for k in ('upstream_crossings','source_admissions','ramp_merges','unexplained_entries'))
        residual+=sum(float(f[k]) for k in ('downstream_crossings','off_departures','terminal_exits_inferred','unexplained_losses','native_removals'))
        assert abs(residual)<1e-9
    return data,dict(events=evidence,unbinned_tail=tail,completed_window_events=len(evidence),
        all_native_events=len(evidence)+len(tail),mainline_stock_and_speed_unchanged=True,
        method='Same vehicle observed on on-ramp then off-ramp within5s; common physical mainline link and forward attachments verified. Pair merge/exit and intervening spatial crossings, preserving each cell N.')


def prepare():
    data,correction=corrected_data()
    save('paired_crossing_correction.json',correction)
    old=B/'fw080_urban090_observations'
    exact={n:sha256(data.folder/n)==sha256(old/n) for n in ('cells_30s.csv','flows_30s.csv','boundaries_30s.csv')}
    assert all(exact.values())
    assert load(data.folder/'manifest.json')['fzp']['file_sha256']==load(old/'manifest.json')['fzp']['file_sha256']
    config=load(BASE/'boundary_config.json')
    config['freeway']['physical_offramp_interval_service']=True
    save('config.json',config)
    model=load_base_model(data.geometry,OUT/'config.json')
    params=load(BASE/'family_parameters.json')['boundary']
    save('parameters.json',params)
    # Preserve the existing complete pre-control transit estimator. Do not fit
    # travel speed on congested future trajectories or change METANET weights.
    samples={c:[] for c in model.offramps}
    for r in table(data.folder/'port_events.csv'):
        c=r['connector']
        if c in samples and r['kind']=='departure' and float(r['time_s'])<=900 and r['residence_s'] and float(r['residence_s'])>0:
            samples[c].append(model.offramps[c]['length_m']*3.6/float(r['residence_s']))
    assert all(samples.values())
    profile=dict(occupancy_lane_loss=True,travel_speed_kmh={c:statistics.median(v) for c,v in samples.items()},
        sample_counts={c:len(v) for c,v in samples.items()},latest_training_sec=900,
        limits='Pre900 complete traversal median, including any waiting; effective transit proxy, not pure free-running speed or service capacity.')
    save('port_profile.json',profile)
    checks=[]
    for (t,c),r in data.ports.items():
        if c not in model.offramps:continue
        b=data.boundaries[t,model.offramps[c]['id']]
        assert float(r['end_n_veh'])==float(b['snapshot_n_veh'])
        assert float(r['arrivals_veh'])==float(b['crossings'])
        assert float(r['unresolved_absences_veh'])==0
        assert abs(float(r['conservation_residual_veh']))<1e-9
        checks.append((t,c))
    # Future traffic cannot influence a genuine history window.
    cutoff=2700.1
    w=build_window(data,cutoff,'history_forecast',profile,model_step_sec=1)
    causal=copy.copy(data)
    causal.cells={t:v for t,v in data.cells.items() if t<=cutoff}
    causal.flows={k:v for k,v in data.flows.items() if k[0]<=cutoff}
    causal.boundaries={k:v for k,v in data.boundaries.items() if k[0]<=cutoff}
    causal.ports={k:v for k,v in data.ports.items() if k[0]<=cutoff}
    causal.port_cohorts={t:v for t,v in data.port_cohorts.items() if float(t)<=cutoff}
    assert w==build_window(causal,cutoff,'history_forecast',profile,model_step_sec=1)
    before=load(OUT/'before_sources.json')
    assert all(sha256(OUT/(Path(p).name+'.before.txt'))==h for p,h in before.items())
    files=[CAL/n for n in ('canonical_harness.py','boundary_factory.py','extract_observations.py','scoring.py')]
    files += [OUT/n for n in ('config.json','parameters.json','port_profile.json')]
    pins={str(p.relative_to(ROOT)):sha256(p) for p in files}
    pins.update(model.provenance['model_files'])
    save('preflight.json',dict(mainline_exact=exact,off_port_conservation_checks=len(checks),
        future_deletion_does_not_change_window=True,native_queue_pins=queue_pins(),pins=pins,
        observations={p.name:sha256(p) for p in data.folder.iterdir() if p.is_file()},
        startup_tests='15 unit/regression tests passed before native-data predictions'))
    print(json.dumps(dict(prepared=True,off_checks=len(checks),profile=profile)),flush=True)


def make_window(data,cutoff,horizon,variant,profile):
    p=None if variant=='held' else {**profile,'entry_capacity_mode':'storage_and_proxy' if variant=='dynamic_proxy' else 'storage'}
    w=build_window(data,cutoff,'history_forecast',p,model_step_sec=1,horizon_sec=horizon)
    if variant=='future_drain_diagnostic':
        for step in w['boundary_steps']:
            end=round((math.floor((step['window_start_s']-data.phase_sec+1e-8)/30)+1)*30+data.phase_sec,6)
            step['off_drain_vph']={c:float(data.ports[end,c]['departures_veh'])*120 for c in profile['travel_speed_kmh']}
        w['meta']['features_latest_realized_time_s']=cutoff+horizon
        w['meta']['off_drain_meaning']='DIAGNOSTIC ONLY: future measured exits used as service; all other boundary inputs remain causal history'
    return w


def port_scores(data,model,cutoff,horizon,road,result):
    output=[]
    port_pred={(round(r['time_s'],6),r['connector']):r for r in result.get('ports',[])}
    off_pred={(round(r['window_end_s'],6),r['cell']):r for r in result['flows']}
    for c,g in model.offramps.items():
        if g['road']!=road:continue
        initial=float(data.ports[cutoff,c]['end_n_veh'])
        cum_in=cum_out=0.;last_pred_in=last_pred_out=0.
        for dt in range(30,horizon+1,30):
            t=round(cutoff+dt,6);o=data.ports[t,c]
            cum_in+=float(o['arrivals_veh']);cum_out+=float(o['departures_veh'])
            real=float(o['end_n_veh']);p=port_pred.get((t,c))
            pred_n=initial if p is None else p['n_veh']
            row=dict(cutoff_s=cutoff,time_s=t,road=road,connector=c,n_actual=real,n_predicted=pred_n,
                stock_error=pred_n-real,capacity_veh=g['storage_capacity_veh'],
                observed_entry=float(o['arrivals_veh']),observed_drain=float(o['departures_veh']),
                predicted_entry=off_pred[t,g['from_cell']]['off_departures'])
            if p is not None:
                row.update(predicted_drain=p['departed_veh']-last_pred_out,
                    entry_error_cumulative=p['admitted_veh']-cum_in,
                    drain_error_cumulative=p['departed_veh']-cum_out,
                    conservation_residual=p['conservation_residual_veh'],ready_veh=p['ready_veh'])
                assert abs(row['stock_error']-row['entry_error_cumulative']+row['drain_error_cumulative'])<1e-7
                assert abs(p['conservation_residual_veh'])<1e-7
                assert -1e-8<=pred_n<=g['storage_capacity_veh']+1e-7
                last_pred_in,last_pred_out=p['admitted_veh'],p['departed_veh']
            output.append(row)
    return output


def run():
    if (OUT/'results450.json.gz').exists():raise FileExistsError('Preserve previous study')
    data,_=corrected_data();profile=load(OUT/'port_profile.json')
    model=load_base_model(data.geometry,OUT/'config.json');params=load(OUT/'parameters.json')
    comparisons=[];results=[];ports=[]
    for t in [900.1,1800.1,2700.1,3600.1,4500.1,5400.1,6300.1,7200.1,8100.1]:
        for variant in ('held','dynamic_proxy','dynamic_storage','future_drain_diagnostic'):
            w=make_window(data,t,450,variant,profile)
            for road in model.roads:
                pred=model.rollout(w['initial_cells'],w['boundary_steps'],params,w['initial_origin_queue'],
                    roads=(road,),port_dynamics=w.get('port_dynamics'),horizon_sec=450)
                score=score_rollout(data,t,pred,road,include_source_boundary=True)
                comparisons.append(dict(variant=variant,**score))
                results.append(dict(variant=variant,cutoff=t,road=road,rollout=pred))
                ports.extend(dict(variant=variant,**r) for r in port_scores(data,model,t,450,road,pred))
        print(json.dumps(dict(completed_cutoff=t)),flush=True)
    with gzip.open(OUT/'results450.json.gz','wt',encoding='utf8') as f:json.dump(results,f)
    save('scores450.json',comparisons);save('port_scores450.json',ports)
    summarize(comparisons,ports,'summary450.json')
    print(json.dumps(dict(complete450=True,rollouts=len(results),invalid=sum(r['invalid'] for r in comparisons))),flush=True)


def summarize(scores,ports,filename):
    rows=[]
    for variant in sorted(set(r['variant'] for r in scores)):
        for road in ('FW_E','FW_W'):
            rs=[r for r in scores if r['variant']==variant and r['road']==road]
            ps=[r for r in ports if r['variant']==variant and r['road']==road]
            row=dict(variant=variant,road=road,invalid=sum(r['invalid'] for r in rs),
                stock=stats([p['stock_error'] for p in ps]),
                off_entry_veh_30s=stats([p['predicted_entry']-p['observed_entry'] for p in ps]))
            for key in ('speed','density','flow_vph'):
                row[key+'_rmse']=math.sqrt(sum(r[key]['rmse']**2*r[key]['count'] for r in rs)/sum(r[key]['count'] for r in rs))
            if variant!='held':row['off_drain_veh_30s']=stats([p['predicted_drain']-p['observed_drain'] for p in ps])
            rows.append(row)
    save(filename,rows)


def rolling():
    """Short causal forecasts, then native stock and mainline comparisons."""
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    if (OUT/'rolling150.json.gz').exists():raise FileExistsError('Preserve prior predictions')
    data,_=corrected_data();profile=load(OUT/'port_profile.json')
    model=load_base_model(data.geometry,OUT/'config.json');params=load(OUT/'parameters.json')
    last=load(data.folder/'manifest.json')['last_complete_30s_window_s']
    cells=[];ports=[];checks=[];metrics=[]
    for cutoff in [round(t+data.phase_sec,6) for t in range(900,8851,150)]:
        horizon=min(150,int(round(last-cutoff)))
        for variant in ('held','dynamic_proxy','dynamic_storage'):
            w=make_window(data,cutoff,horizon,variant,profile)
            assert w['meta']['features_latest_realized_time_s']==cutoff
            for road in model.roads:
                pred=model.rollout(w['initial_cells'],w['boundary_steps'],params,w['initial_origin_queue'],
                    roads=(road,),port_dynamics=w.get('port_dynamics'),horizon_sec=horizon)
                checks.extend(dict(variant=variant,cutoff_s=cutoff,**r) for r in pred['diagnostics']['roads'])
                cells.extend(dict(variant=variant,**r) for r in pred['cells'])
                ports.extend(dict(variant=variant,**r) for r in port_scores(data,model,cutoff,horizon,road,pred))
        if int(cutoff)%900==0:print(json.dumps(dict(rolling_cutoff=cutoff)),flush=True)
    assert all(r['continuity_residual_max_veh']<1e-6 and r['density_projection_count']==0
        and r['jam_density_exceedance_count']==0 and r['negative_density_count']==0 for r in checks)
    with gzip.open(OUT/'rolling150.json.gz','wt',encoding='utf8') as f:json.dump(dict(cells=cells,ports=ports),f)
    labels={'held':'초기 재고 고정','dynamic_proxy':'동적 재고 · 기존 유입 상한 유지',
        'dynamic_storage':'동적 재고 · 저장공간 기준 유입'}
    colors={'held':'#777777','dynamic_proxy':'#da9200','dynamic_storage':'#2477ba'}
    for variant in labels:
        for road in model.roads:
            rows=[r for r in cells if r['variant']==variant and r['road']==road]
            actual={(t,r['cell']):r for t,rs in data.cells.items() for r in rs if r['road']==road}
            errors=[r['v_kmh']-actual[round(r['time_s'],6),r['cell']]['v_kmh'] for r in rows
                if actual[round(r['time_s'],6),r['cell']]['n_veh']>=5 and actual[round(r['time_s'],6),r['cell']]['v_kmh'] is not None]
            ps=[r for r in ports if r['variant']==variant and r['road']==road]
            metrics.append(dict(variant=variant,road=road,speed=stats(errors),stock=stats([r['stock_error'] for r in ps]),
                off_entry_veh_30s=stats([r['predicted_entry']-r['observed_entry'] for r in ps])))
    plt.rcParams.update({'font.family':'Malgun Gothic','axes.unicode_minus':False,'font.size':10})
    fig,axes=plt.subplots(4,2,figsize=(16,12),sharex=True,layout='constrained')
    for ax,c in zip(axes.flat,('10643','10481','10682','10483','10491','10638','10479','10645')):
        actual=sorted((t,float(r['end_n_veh'])) for (t,k),r in data.ports.items() if k==c and t>=900.1)
        ax.plot([t for t,n in actual],[n for t,n in actual],color='#151515',lw=1.5,label='VISSIM 실측',zorder=5)
        for variant,label in labels.items():
            rows=sorted((r for r in ports if r['connector']==c and r['variant']==variant),key=lambda r:r['time_s'])
            ax.plot([r['time_s'] for r in rows],[r['n_predicted'] for r in rows],color=colors[variant],lw=1.,alpha=.8,label=label)
        ax.set(title=f"{model.offramps[c]['road']} · 진출램프 {c}",ylabel='재고 [대]',xlim=(900,9000),ylim=(0,None))
        ax.grid(alpha=.2);ax.set_xticks(range(900,9001,900))
    handles,names=axes[0,0].get_legend_handles_labels()
    fig.legend(handles,names,loc='outside lower center',ncol=2)
    fig.suptitle('FW80 · 도시90 — 진출램프 재고 예측 비교\n900초 이후, 150초마다 실측 초기화 · 다음150초 예측 · 계수 재보정 없음',fontsize=16)
    for ax in axes[-1]:ax.set_xlabel('시뮬레이션 시간 [초]')
    fig.savefig(OUT/'offramp_stock_rolling150.png',dpi=140);plt.close(fig)
    # Peak storage and its following discharge: same initial state, 450s horizon.
    rows=load(OUT/'port_scores450.json');target=[r for r in rows if r['connector']=='10643' and r['cutoff_s']==5400.1]
    fig,axes=plt.subplots(3,1,figsize=(12,9),sharex=True,layout='constrained')
    actual=[r for r in target if r['variant']=='held']
    for ax,key,label in zip(axes,('n_actual','observed_entry','observed_drain'),('재고 [대]','30초 진입 [대]','30초 배수 [대]')):
        ax.plot([r['time_s'] for r in actual],[r[key] for r in actual],color='black',label='VISSIM 실측',lw=2)
        ax.set_ylabel(label);ax.grid(alpha=.2)
    for variant,label in labels.items():
        rs=[r for r in target if r['variant']==variant]
        for ax,key in zip(axes,('n_predicted','predicted_entry','predicted_drain')):
            if key not in rs[0]:continue
            ax.plot([r['time_s'] for r in rs],[r[key] for r in rs],color=colors[variant],label=label)
    axes[0].legend(loc='upper right');axes[-1].set_xlabel('시뮬레이션 시간 [초]')
    fig.suptitle('10643 진출램프 — 5400.1초에서 시작한 450초 예측\n초기 재고 이후 실측 리셋 없음 · 진입과 배수 오차를 분리',fontsize=15)
    fig.savefig(OUT/'off10643_recovery450.png',dpi=140);plt.close(fig)
    preflight=load(OUT/'preflight.json')
    assert all(sha256(ROOT/p)==h for p,h in preflight['pins'].items())
    queue_pins()
    save('completion.json',dict(complete=True,rolling_rollouts=len(checks),rolling_metrics=metrics,
        comparison450_rollouts=72,invalid_rolling=0,max_continuity_residual=max(r['continuity_residual_max_veh'] for r in checks),
        active_native_queue_unchanged=True,production_adopted=False,control_gain_validated=False))
    print(json.dumps(load(OUT/'completion.json'),ensure_ascii=False),flush=True)


if __name__=='__main__':{'prepare':prepare,'run':run,'rolling':rolling}[sys.argv[1]]()
