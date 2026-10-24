"""Exact phase-speed ledger from saved forecasts; no extra rollout or fit."""
from pathlib import Path
from collections import defaultdict
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE=Path(__file__).resolve().parent


def main():
    from diagnostics.repin_v3c3_review_20261001.jin_macro111 import run as common
    common.setup()
    from evaluation.controllers import lane_plant_runtime as lpr
    from evaluation.controllers.freeway_fd import cell_state_response, state_response_coefficients
    cfgctx=lpr.load_sources(h.R/'lane_state132/eval_01/manifest.json')
    cfg=cfgctx['component']._config('FW_E',cfgctx['parameters']['by_direction']['FW_E'])
    fd=cfg.network.freeway_segment_params['FW_E']
    pins={str(Path(__file__)):h.sha(__file__)}
    def read(p):pins[str(p)]=h.sha(p);return h.read(p)
    collected=defaultdict(list);maxerr=0.;skipped=0
    for arm in ('hold','release','hold_vsl90','release_vsl90'):
        trace=read(HERE/f'forecast/queue/s67_late_{arm}_phase.json.gz')
        by={(round(z['time_s'],6),z['cell'],z['lane']):z for z in trace['rows']}
        for e in trace['events']:
            if e['lane']!=1 or e['cell'] not in (20,21,23,24,25):continue
            t=e['time_s'];i=e['cell'];n=e['n_next'];s=e['transport_s'];release=e['release'];onset=e['onset']
            moving_before=n-s;moving_after=e['moving_n']
            if n<=1e-10 or e['n0']<=1e-10 or moving_before-onset<=1e-10 or s-release<=1e-10:
                # w is undefined only if slow stock is zero; its moment then zero.
                if n<=1e-10 or e['n0']<=1e-10 or moving_before-onset<=1e-10:skipped+=1;continue
            w=e['slow_moment']/(s-release) if s-release>1e-10 else 0.
            u_before=(moving_after*e['phase_u']-release*w)/(moving_before-onset)
            v_transport=(s*w+moving_before*u_before)/n
            v_changed=(e['slow_moment']+moving_after*e['phase_u'])/n
            phase_change=-onset*u_before/n
            assert abs((v_changed-v_transport)-phase_change)<1e-8
            old=by.get((round(t,6),i,1))
            old_moment=old['slow_moment']+old['moving_moment'] if old else sum(trace['initial'][str(i)][0][1:])
            old_v=old_moment/e['n0']
            new=by[(round(t+1,6),i,1)]['v']
            response=cell_state_response(cfg.network,'FW_E',i)
            # These frozen132 cell responses have no downstream-dependent
            # recovery override. Their acceleration/deceleration tau MUST be
            # selected; the raw FD-row tau is not the executed coefficient.
            assert 'recovery_relaxation' not in response
            tau_h,_=state_response_coefficients(response,e['phase_u'],e['moving_target'],
                e['n0']/fd[i]['segment_length_km'],0.,fd[i]['rho_crit'],
                fd[i].get('metanet_tau_h',cfg.network.metanet_tau_h),0.)
            tau_sec=tau_h*3600
            relax=moving_after/n*(e['moving_target']-e['phase_u'])/tau_sec
            other=new-v_changed-relax
            transported=v_transport-old_v
            residual=new-old_v-(transported+phase_change+relax+other)
            maxerr=max(maxerr,abs(residual));assert abs(residual)<1e-8
            block=int((round(t,1)-2670.1+1e-6)//150)
            collected[arm,i,block].append(dict(transport=transported,stop_conversion=phase_change,
                relaxation=relax,other_speed=other,total=new-old_v,mean_v=new,mean_n=n,
                mean_s=by[(round(t+1,6),i,1)]['s'],pressure=e['pressure'],onset=onset,release=release))
    rows=[]
    for (arm,i,block),series in collected.items():
        rows.append(dict(arm=arm,cell=i,block=block,samples=len(series),
            mean={k:sum(z[k] for z in series)/len(series) for k in series[0]}))
    assert all(h.sha(p)==d for p,d in pins.items())
    h.save(HERE/'term_ledger.json',dict(scope='Model lane1 speed changes per1s; no actual acceleration truth or attribution of residual to a single term.',
        other_speed='Anticipation plus actual-merge/lane-drop decrement and speed clipping; analytic convection already zero. Relaxation uses actual cell state-response acceleration/deceleration tau.',
        units='km/h per1s for velocity increments; N/S in vehicles; pressure dimensionless. Unweighted means, not TTT.',
        max_closure_error=maxerr,skipped_empty_or_all_slow=skipped,input_sha256=pins,rows=rows))
    for z in rows:
        if z['cell']==20:print(z)


if __name__=='__main__':main()
