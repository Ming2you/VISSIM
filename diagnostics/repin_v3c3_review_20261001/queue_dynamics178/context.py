"""Saved-state failure localization only; no fits, rollouts or FZP scans."""
import math
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h
from diagnostics.repin_v3c3_review_20261001.queue_dynamics178.prepare import pressure

HERE=Path(__file__).resolve().parent


def main():
    from diagnostics.repin_v3c3_review_20261001.jin_macro111 import run as common
    from evaluation.controllers import lane_plant_runtime as lpr
    from evaluation.controllers.freeway_geometry import cell_lengths_km
    common.setup();ctx=lpr.load_sources(h.R/'lane_state132/eval_01/manifest.json')
    cfg=ctx['component']._config('FW_E',ctx['parameters']['by_direction']['FW_E'])
    L=cell_lengths_km(cfg.network,'FW_E',31);fd=cfg.network.freeway_segment_params['FW_E'];jam=cfg.network.rho_max
    coeff=h.read(HERE/'coefficients.json');results=[]
    for arm in ('hold','release','hold_vsl90','release_vsl90'):
        native=h.read(h.R/f'blocking176/{arm}_frames.json.gz');fr={float(t):v for t,v in native['frames'].items()}
        trace=h.read(HERE/f'forecast/queue/s67_late_{arm}_phase.json.gz')
        lookup={(round(x['time_s'],6),x['cell'],x['lane']):x for x in trace['rows']}
        events={(round(x['time_s'],6),x['cell'],x['lane']):x for x in trace['events']}
        for cell in (20,21,24,25):
            native_s=[];pred_s=[];native_p=[];pred_p=[];actual_stop=actual_clear=fit_stop=fit_clear=0.
            for j in range(90):
                t=round(2670.1+5*j,6);tn=round(t+5,6);a,b=fr[t],fr[tn]
                own={key:v for key,v in a.items() if v[0]==cell and v[3]==1}
                down=[v for v in a.values() if v[0]==cell+1 and v[3]==1]
                n=len(own);s=sum(v[1]<5 for v in own.values());dn=len(down);ds=sum(v[1]<5 for v in down)
                p=pressure(n,s,dn,ds,L[cell],L[cell+1],fd[cell]['rho_crit'],fd[cell+1]['rho_crit'],jam)
                native_s.append(s);native_p.append(p)
                pred_s.append(trace['initial'][str(cell)][0][0] if j==0 else lookup[t,cell,1]['s'])
                pred_p.append(events[t,cell,1]['pressure'])
                # Conditional ENDPOINT probabilities under frozen observed p;
                # score only same-cell/lane stayers to expose sampling scope.
                onset=-math.expm1(-coeff['formation_per_sec']*p)
                clear=-math.expm1(-coeff['release_per_sec']*(1-p))
                total=onset+clear
                ps=onset/total*(1-(1-total)**5) if total else 0.
                pc=clear/total*(1-(1-total)**5) if total else 0.
                for key,v in own.items():
                    w=b.get(key)
                    if w is None or w[0]!=cell or w[3]!=1:continue
                    if v[1]<5:actual_clear+=int(w[1]>=5);fit_clear+=pc
                    else:actual_stop+=int(w[1]<5);fit_stop+=ps
            avg=lambda a:sum(a)/len(a)
            results.append(dict(arm=arm,cell=cell,mean_native_s=avg(native_s),mean_model_s=avg(pred_s),
                mean_native_pressure=avg(native_p),mean_model_pressure=avg(pred_p),
                observed_stayer_onsets=actual_stop,conditional_expected_onsets=fit_stop,
                observed_stayer_clearances=actual_clear,conditional_expected_clearances=fit_clear))
    h.save(HERE/'failure_context.json',dict(scope='Same90left5s samples2670.1..3120.1; observed p held5s for diagnostic endpoint probabilities only.',
        future_runtime_observations=False,additional_fits=0,additional_rollouts=0,rows=results))
    for x in results:
        if x['cell']==20:print(x)


if __name__=='__main__':main()
