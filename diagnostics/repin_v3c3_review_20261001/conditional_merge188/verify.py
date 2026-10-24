"""Independent formula, stock, timing and historical-function checks."""
import ast
import math
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE=Path(__file__).resolve().parent


def main():
    from evaluation.controllers import lane_plant_runtime as lpr
    context=lpr.load_sources(h.R/'lane_state132/eval_01/manifest.json')
    cfg=context['component']._config('FW_E',context['parameters']['by_direction']['FW_E'])
    net=cfg.network;fd=net.freeway_segment_params['FW_E'][21]
    length=fd['segment_length_km'];jam=net.rho_max;critical=fd['rho_crit']
    capacity=critical*fd['v_free']*math.exp(-1/fd['metanet_a_m']);wave=capacity/(jam-critical)
    s=h.read(HERE/'summary.json');p=h.read(HERE/'protocol.json');budgets=h.read(HERE/'budgets.json');traces=h.read(HERE/'traces.json')
    assert len(s['rows'])==len(traces)==20 and len(budgets)==1800
    functions=lambda text:{n.name:ast.dump(n) for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)}
    before=functions((HERE/'analyzer_before188.py.txt').read_text(encoding='utf8'))
    after=functions((h.R/'flowbudget182/analyze.py').read_text(encoding='utf8'))
    assert all(after[k]==v for k,v in before.items())
    assert h.sha(HERE/'analyzer_before188.py.txt')==p['source_before']
    for z in budgets:
        n=z['right_n'];space=max(0.,jam*length-n)
        shared=min(space,capacity/3600.,max(0.,wave*(jam-n/length))/3600.)
        q=z['conflict_vph']/3600.;gap=q/math.expm1(q*1.5) if q else 1/1.5
        assert abs(shared-z['shared'])<1e-10
        assert abs(gap-z['gap'])<1e-10
        assert abs(z['observed_state_budget']-min(z['canonical'],shared,gap))<1e-10
    checks=0
    native=h.read(h.R/'ramp_motion187/summary.json')['rows']
    for arm in ('hold','release','hold_vsl90','release_vsl90'):
        rows={z['mode']:z['rows'] for z in traces if z['arm']==arm}
        stats={z['mode']:z for z in s['rows'] if z['arm']==arm}
        truth=next(z for z in native if z['case']=='s67_late' and z['arm']==arm and z['connector']=='10490')
        assert all(abs(z['actual_mean_post5']-truth['posthead_mean_native5_left'])<1e-10 for z in stats.values())
        for mode,rr in rows.items():
            n0=rr[0]['start_post'];arrived=merged=0.
            assert len(rr)==450
            for row in rr:
                arrived+=row['head'];merged+=row['merge']
                assert abs(n0+arrived-merged-row['post'])<1e-9
                assert row['storage_excess']==0
                assert abs(row['ready']+row['travelling']-row['post'])<1e-9
                checks+=1
            assert abs(merged-stats[mode]['merge_total'])<1e-9
        # Same receiver, same cumulative head by each5s boundary. Advancing
        # head entries cannot reduce cumulative output in this fixed queue.
        # These are bounds of the one-second surrogate, not continuous VISSIM.
        for receiver in ('saved_budget','observed_state_budget'):
            early=rows['first_bucket_'+receiver];late=rows['last_bucket_'+receiver]
            eh=lh=0.
            for i,(a,b) in enumerate(zip(early,late)):
                eh+=a['head'];lh+=b['head']
                assert a['cumulative_merge']+1e-9>=b['cumulative_merge']
                if (i+1)%5==0:
                    assert eh==lh and a['post']<=b['post']+1e-9
    for path,digest in {**s['input_sha256'],**p['protected_sha256'],p['STOP']['path']:p['STOP']['sha256']}.items():assert h.sha(path)==digest,path
    h.save(HERE/'verification.json',dict(status='verified',formula_checks=1800,stock_checks=checks,saved_parity_checks=s['checks']['saved_trace_parity'],
        maximum_errors=s['max_errors'],storage_excess=0,one_second_surrogate_timing_bracket=True,
        previous_functions_unchanged=list(before),core_inputs_STOP_unchanged=True,
        full_forecasts=0,fit=False,new_native=0,FZP=0,adopted=False,qualified=False,full_goal='ACTIVE_NOT_QUALIFIED',summary_sha256=h.sha(HERE/'summary.json')))
    print('VERIFIED188',checks,'stock checks;1800 supply formulas;5400 saved parity values')


if __name__=='__main__':main()
