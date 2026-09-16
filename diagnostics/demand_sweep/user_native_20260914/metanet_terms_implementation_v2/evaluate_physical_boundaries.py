"""Fixed post-fit development checks; no search against seed17."""
from pathlib import Path
import sys,json,math,time,hashlib
ROOT=Path(__file__).resolve().parents[4]
HERE=Path(__file__).resolve().parent
CAL=HERE.parent/'metanet_calibration_v1'
sys.path[:0]=[str(ROOT/'diagnostics/rule_baseline_20260914/.plot-deps'),str(CAL)]
from canonical_harness import load_base_model
from boundary_factory import ObservationData,build_window
from scoring import score_rollout,stats
from evaluate import pooled

def main():
    out=HERE/'evaluation_dynamic_v1'
    if out.exists():raise FileExistsError('Preserve previous evaluations')
    out.mkdir()
    old=json.loads((CAL/'fit_v2/parameters.json').read_text(encoding='utf-8'))['parameters']
    fitted=json.loads((HERE/'fit_dynamic_v1/parameters.json').read_text(encoding='utf-8'))['parameters']
    profile=json.loads((HERE/'port_profile.json').read_text(encoding='utf-8'))
    records=[];failures=[]
    started=time.monotonic()
    hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in
        [CAL/'canonical_harness.py',CAL/'boundary_factory.py',CAL/'scoring.py',
         HERE/'fit_dynamic_v1/parameters.json',HERE/'physical_geometry21_v1.json',HERE/'port_profile.json']}
    for seed in (13,17):
        new_data=ObservationData(HERE/f'seed{seed}_observations')
        old_data=ObservationData(CAL/f'seed{seed}_observations')
        new_model=load_base_model(new_data.geometry)
        old_model=load_base_model(old_data.geometry)
        for version,data,model,params,dynamic in (
            ('original_grid_reference',old_data,old_model,old,False),
            ('aligned_grid_reference',new_data,new_model,old,False),
            ('aligned_dynamic_reference',new_data,new_model,old,True),
            ('aligned_dynamic_refit',new_data,new_model,fitted,True)):
            for mode in ('conditioned_diagnostic','history_forecast'):
                for cutoff in range(900,8551,450):
                    try:
                        w=build_window(data,cutoff,mode,profile if dynamic else None)
                        prediction=model.rollout(w['initial_cells'],w['boundary_steps'],params,
                            w['initial_origin_queue'],port_dynamics=w.get('port_dynamics'))
                        for road in ('FW_E','FW_W'):
                            score=score_rollout(data,cutoff,prediction,road)
                            if dynamic:
                                port_errors=[];drain_errors=[];previous={}
                                for row in prediction['ports']:
                                    if row['road']!=road or int(row['time_s'])%30:continue
                                    t,c=int(row['time_s']),row['connector']
                                    actual=data.ports[t,c]
                                    port_errors.append(row['n_veh']-float(actual['end_n_veh']))
                                    drain_errors.append((row['departed_veh']-previous.get(c,0.)-float(actual['departures_veh']))*120)
                                    previous[c]=row['departed_veh']
                                score.update(off_storage_n=stats(port_errors),off_drain_vph=stats(drain_errors))
                            records.append({'seed':seed,'version':version,'mode':mode,**score})
                    except (ValueError,ArithmeticError,OverflowError) as exc:
                        failures.append({'seed':seed,'version':version,'mode':mode,'cutoff_s':cutoff,
                                         'error':repr(exc)})
            print(json.dumps({'seed':seed,'version':version,'complete':True,'failures':len(failures)}),flush=True)
    for p,digest in hashes.items():
        if hashlib.sha256(Path(p).read_bytes()).hexdigest()!=digest:raise RuntimeError('Source changed during evaluation: '+p)
    summary=[]
    for seed in (13,17):
        for version in sorted({r['version'] for r in records}):
            for mode in ('conditioned_diagnostic','history_forecast'):
                for road in ('FW_E','FW_W'):
                    selected=[r for r in records if r['seed']==seed and r['version']==version and r['mode']==mode and r['road']==road]
                    events=[e for r in selected for e in r['onset_events'] if road=='FW_E' and e['cell']==13]
                    summary.append({'seed':seed,'version':version,'mode':mode,'road':road,'windows':len(selected),
                        'invalid_windows':sum(r['invalid'] for r in selected),
                        **{key:pooled(selected,key) for key in ('density','speed','flow_vph','off_flow_vph','off_storage_n','off_drain_vph')},
                        'cell14_observed_low_speed_windows':sum(e['observed_first_sustained_in_window_s'] is not None for e in events),
                        'cell14_missed_low_speed_windows':sum(e['status']=='miss' for e in events),
                        'mean_absolute_freeway_ttt_error_veh_h':sum(abs(r['freeway_ttt_predicted_veh_h']-r['freeway_ttt_observed_veh_h']) for r in selected)/len(selected)})
    result={'scope':'Post-fit development checks; seed17 not used by fitter but previously inspected under prior model. Not a fresh independent holdout.',
            'grid_warning':'Original and aligned spatial cells differ; cell14 is not the identical physical interval. Compare same-grid refit metrics and road totals; do not claim direct cell RMSE percent improvement due to geometry alone.',
            'summary':summary,'records':records,'failures':failures,'source_sha256':hashes,'elapsed_seconds':time.monotonic()-started}
    (out/'evaluation.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    for r in summary:
        if r['seed']==17 and r['mode']=='history_forecast':
            print(json.dumps({k:r[k] for k in ('version','road','invalid_windows','density','speed','flow_vph','cell14_missed_low_speed_windows')}))
if __name__=='__main__':main()

