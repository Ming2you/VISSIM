"""Post-run evidence only: desired distribution gate and recovery diagnostics."""
import csv,json
from pathlib import Path
import numpy as np
import vsl_response as v
from prepare import save,table
c=v.c;f=v.f;B=v.B;ROOT=v.ROOT;O=B/'distribution_response_v1'


def speeds(a):
    return np.divide(a['mom'],a['n'],out=np.zeros_like(a['n']),where=a['n']>0)


def main():
    baseline='vr_hadi_fd_cap_r2_validation'
    obs={a:v.observed(a) for a in ('none','vsl')}
    variants={'disabled':'dd_disabled','mean_cap':'dd_mean_cap_v2','distribution_cap':'dd_distribution_cap_v2'}
    pins=[];audits=[];scores=[];cellrows=[];preds={}
    for filename in ('protocol.json','protocol_v2.json'):
        for path,digest in c.load(O/filename)['source_pins'].items():
            p=ROOT/path
            if c.sha(p)!=digest and p.name=='distribution_response.py':p=O/'source_failed_frame.py.txt'
            assert c.sha(p)==digest,(filename,path)
            pins.append(dict(protocol=filename,original=path,resolved=str(p.relative_to(ROOT)),sha256=digest))
    for mode,name in variants.items():
        pp={a:f.load_prediction(O/name/f'refined_guard1_{a}.json') for a in obs}
        preds[mode]={a:c.predicted(p) for a,p in pp.items()}
        config=c.load(O/name/'effective_config.json');spec=c.load(O/(name+'.json'))
        assert [x['arm'] for x in config]==['none','vsl']
        for entry in config:
            assert entry['scalar']==spec['physical_coefficients']
            assert entry['state_response']['FW_E']==spec['state_response']
            assert entry['receiving']['FW_E']==spec['hadiuzzaman']
            assert entry['port_response']['FW_E']==spec['port_response']
        for arm,p in pp.items():
            assert c.screen(p)['passed']
            reference=f.load_prediction(v.O/baseline/f'refined_guard1_{arm}.json')
            if mode=='disabled':assert p==reference
            for key in ('cells','flows'):
                assert [r for r in p[key] if r['road']=='FW_W']==[r for r in reference[key] if r['road']=='FW_W']
            if mode!='disabled':
                audit=c.load(O/name/f'diagnostic_desired_{arm}.json')
                assert audit==p['diagnostics']['future_desired_distribution']
                assert audit['calls']==audit['supported_calls']+audit['empty_observed_group_calls']
                assert 0<audit['changed_calls']<=audit['supported_calls']<=audit['calls']
                assert audit['not_for_controller'] and audit['future_native_desired_speed']
                assert audit['mode']==mode
                audits.append(dict(arm=arm,**audit))
        for phase,lo,hi in [('train',0,10),('late',10,15)]:
            _,metric=v.response_metrics(preds[mode],lo,hi)
            scores.append(dict(mode=mode,phase=phase,**metric,**c.score(pp['none'],lo,hi)))
        for i in range(30):
            ng=len(c.WIDTHS[i]);row=dict(mode=mode,cell=i,parent=c.PARENTS[i])
            for label,data in [('actual',obs),('predicted',preds[mode])]:
                row[label+'_mainline_delta_ttt']=float(np.sum(data['vsl']['n'][:,i,:ng]-data['none']['n'][:,i,:ng])*30/3600)
                row[label+'_boundary_delta_veh']=float(np.sum(data['vsl']['q'][:,i]-data['none']['q'][:,i]))
            cellrows.append(row)
    # Temporal recovery is not identical to a negative spatial density gradient.
    # Define the diagnostic from observations, never use it as a future model input.
    # Exclude the internally partitioned cell and its upstream neighbor: the
    # model consumes pre/post densities there, not whole-cell mean density.
    widths=c.WIDTHS;lengths={r['cell']:r['length_km'] for r in c.G['cells'] if r['road']=='FW_E'}
    matrices=c.S['matrices'];recovery=[];summaries=[]
    strong={a:c.predicted(f.load_prediction(v.O/'vr_recovery_hadi_fd_cap_r2_moderate'/f'refined_guard1_{a}.json')) for a in obs}
    for arm in obs:
        a=obs[arm];av=speeds(a);bv=speeds(preds['disabled'][arm]);sv=speeds(strong[arm])
        for j in range(1,15):
            for i in range(30):
                if i in (8,9):continue
                for g in range(len(widths[i])):
                    if min(a['n'][j-1,i,g],a['n'][j,i,g])<1:continue
                    # Traffic was congested, then sped up while stock fell.
                    if not (av[j-1,i,g]<60 and av[j,i,g]-av[j-1,i,g]>=5 and a['n'][j,i,g]<a['n'][j-1,i,g]):continue
                    weights=np.array(matrices[i][g]);assert weights.sum()>0
                    rho=a['n'][j-1,i,g]/(lengths[i]*widths[i][g])
                    down=float(np.dot(weights,a['n'][j-1,i+1,:len(weights)]/np.array(widths[i+1])/lengths[i+1])/weights.sum())
                    pa=preds['disabled'][arm]
                    prho=pa['n'][j-1,i,g]/(lengths[i]*widths[i][g])
                    pdown=float(np.dot(weights,pa['n'][j-1,i+1,:len(weights)]/np.array(widths[i+1])/lengths[i+1])/weights.sum())
                    recovery.append(dict(arm=arm,start_s=2400+j*30,cell=i,group=g,
                        observed_prior_speed=av[j-1,i,g],observed_next_speed=av[j,i,g],
                        observed_speed_change=av[j,i,g]-av[j-1,i,g],observed_prior_gradient=down-rho,
                        predicted_prior_gradient=pdown-prho,base_speed=bv[j,i,g],strong_speed=sv[j,i,g],
                        base_speed_change=bv[j,i,g]-bv[j-1,i,g],strong_speed_change=sv[j,i,g]-sv[j-1,i,g]))
        rows=[r for r in recovery if r['arm']==arm]
        summaries.append(dict(arm=arm,count=len(rows),
            observed_negative_gradient=int(sum(r['observed_prior_gradient']<0 for r in rows)),
            model_negative_gradient=int(sum(r['predicted_prior_gradient']<0 for r in rows)),
            base_speed_rmse=float(np.sqrt(np.mean([(r['base_speed']-r['observed_next_speed'])**2 for r in rows]))),
            strong_speed_rmse=float(np.sqrt(np.mean([(r['strong_speed']-r['observed_next_speed'])**2 for r in rows]))),
            base_change_rmse=float(np.sqrt(np.mean([(r['base_speed_change']-r['observed_speed_change'])**2 for r in rows]))),
            strong_change_rmse=float(np.sqrt(np.mean([(r['strong_speed_change']-r['observed_speed_change'])**2 for r in rows])))))
    prior=c.load(v.O/'completion.json')
    for path,digest in prior['core_hashes_unchanged'].items():assert c.sha(ROOT/path)==digest
    assert c.sha(O/'before_run.py.txt')==prior['source_pins'][str((B/'run.py').relative_to(ROOT))]
    save(O/'verification.json',dict(source_pins=pins,default_two_entire_json_exact=True,
        west_cells_flows_exact=6,core_hashes_unchanged=prior['core_hashes_unchanged'],effective_config_entries_checked=6,
        completed_forecasts=6,failed_before_first_step=1,new_native=0,qualified=False,production_adopted=False))
    save(O/'analysis.json',dict(audits=audits,metrics=scores,recovery_summary=summaries,
        recovery_definition='30s bins; prior observed speed<60, speed gain>=5, stock decreases, both stocks>=1; cells8/9 excluded. Spatial gradients are descriptive prior30s means, not exact model integration frames.',
        future_diagnostic_only=True,qualified=False))
    table(O/'metrics.csv',scores);table(O/'cell_response.csv',cellrows);table(O/'recovery_events.csv',recovery)
    print(json.dumps(dict(metrics=scores,recovery=summaries),indent=2))


if __name__=='__main__':main()
