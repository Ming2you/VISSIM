"""Same-density FD diagnostics on saved native/model states, not a forecast."""
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path

HERE=Path(__file__).resolve().parent
I=HERE.parent
CW=I/'baseline_reproduction_20260929/cellwise_calibration'
OUT=HERE/'fd_regime_comparison'


def read(path):return json.loads(path.read_bytes())
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read_gz(path):
    with gzip.open(path,'rt',encoding='utf-8') as stream:return json.load(stream)


def main():
    OUT.mkdir(exist_ok=True)
    assert not (OUT/'summary.json').exists(), 'Reuse completed diagnosis'
    ref=CW/'expanded_joint/eval_036/reference_config.json'
    assert digest(ref)=='7f6df2d14795b22d858aa772f5813e42b67f9d1ec4296cc6203bd854c28d83a4'
    fw=read(ref)['freeway'];spec=fw['vsl_fd_response']['FW_E']
    assert spec==dict(law='carlson',A=.5,E=2.,alpha=0.)
    tracepath=HERE/'vsl_response_trace/held_actual.json.gz';trace=read_gz(tracepath)
    geometrypath=I/'selected/port_gain/geometry.json'
    geometry={r['cell']:r for r in read(geometrypath)['cells'] if r['road']=='FW_E'}
    assert len(geometry)==31
    params={};max_vf_residual=0.
    # Recover the actually executed FD free speed from its audited nominal target.
    # This is algebra, not a fit. Check every saved one-second record.
    for r in trace:
        c=r['cell'];a=fw['physical_cell_fd']['FW_E'][str(c)]['metanet_a_m'];critical=r['critical']
        vf=r['nominal_fd_speed']*math.exp((r['rho']/critical)**a/a)
        if c not in params:params[c]=dict(vf=vf,critical=critical,shape=a)
        p=params[c];assert p['critical']==critical
        max_vf_residual=max(max_vf_residual,abs(vf-p['vf']))
    assert max_vf_residual<1e-8
    def speed(c,rho,command):
        p=params[c];b=command/110.;a=p['shape']*(spec['E']-(spec['E']-1)*b)
        return p['vf']*b*math.exp(-(max(0.,rho)/(p['critical']*(1+spec['A']*(1-b))))**a/a)
    def delta(c,rho):return speed(c,rho,90)-speed(c,rho,110)
    pins={str(p):digest(p) for p in (Path(__file__),ref,tracepath,geometrypath,CW/'data_catalog.json')}
    catalog=read(CW/'data_catalog.json')['checked_records']
    proofpath=CW/'freeway_first/ledger/summary.json'
    proof=read(proofpath);frozen=proof['source_pins'];pins[str(proofpath)]=digest(proofpath)
    rows=[];cases=[];verification=[]
    for case,arms,subdir in [('s29_early',('none','vsl'),'selected_predictions'),
                             ('s43_early',('none','vsl'),'checks'),
                             ('s29_late',('hold','hold_vsl90'),'selected_predictions')]:
        initial=[]
        for arm in arms:
            record=next(r for r in catalog if r['case']==case and r['arm']==arm)
            t0=record['cutoff'];nativepath=Path(record['truth'])/'cells_30s.csv'
            predpath=CW/'expanded_joint'/subdir/(case+'_'+arm+'.json.gz')
            for path in (nativepath,predpath):
                h=digest(path);assert frozen[str(path)]==h,('Prior immutable ledger pin mismatch',str(path))
                pins[str(path)]=h;verification.append(str(path))
            native={(round(float(r['time_s']),6),int(r['cell'])):r
                    for r in csv.DictReader(nativepath.open(encoding='utf-8-sig'))
                    if r['road']=='FW_E' and t0<=float(r['time_s'])<=t0+450}
            prediction=read_gz(predpath)['cells']
            initial.append({c:float(native[t0,c]['n_veh']) for c in range(31)})
            assert len(prediction)==31*15
            for p in prediction:
                t=round(p['time_s'],6);c=p['cell'];n=native[t,c];g=geometry[c]
                actual_n=float(n['n_veh']);actual_rho=float(n['rho_veh_per_km_lane'])
                assert abs(actual_rho-actual_n/g['lane_km'])<1e-7
                modeled_rho=float(p['rho_canonical']);modeled_n=p['n_veh']
                assert abs(float(p['rho_veh_per_km_lane'])-modeled_n/g['lane_km'])<1e-7
                assert abs(modeled_rho-modeled_n/(g['length_km']*p['effective_lanes']))<1e-7
                # Hold the model's latent lane support fixed, replace ONLY stock.
                actual_rho_model_lanes=actual_n/(g['length_km']*p['effective_lanes'])
                dmodel=delta(c,modeled_rho);dactual=delta(c,actual_rho)
                dstock=delta(c,actual_rho_model_lanes)
                rows.append(dict(case=case,arm=arm,time=t,cell=c,model_n=modeled_n,native_n=actual_n,
                    model_lanes=p['effective_lanes'],physical_lanes=g['effective_lanes'],
                    model_rho=modeled_rho,native_rho=actual_rho,native_rho_model_lanes=actual_rho_model_lanes,
                    model_V90_minus_V110=dmodel,native_V90_minus_V110=dactual,
                    native_stock_model_lanes_V90_minus_V110=dstock,
                    model_speed=p['v_kmh'],native_speed=float(n['v_kmh']),
                    model_V110=speed(c,modeled_rho,110),native_V110=speed(c,actual_rho,110)))
            selected=[r for r in rows if r['case']==case and r['arm']==arm and 16<=r['cell']<=25]
            cases.append(dict(case=case,arm=arm,rows=len(selected),
                model_positive=sum(r['model_V90_minus_V110']>0 for r in selected),
                native_positive=sum(r['native_V90_minus_V110']>0 for r in selected),
                positive_only_model=sum(r['model_V90_minus_V110']>0 and r['native_V90_minus_V110']<0 for r in selected),
                positive_only_native=sum(r['model_V90_minus_V110']<0 and r['native_V90_minus_V110']>0 for r in selected),
                stock_only_sign_flips=sum(r['model_V90_minus_V110']*r['native_stock_model_lanes_V90_minus_V110']<0 for r in selected)))
        assert initial[0]==initial[1]
    with (OUT/'states.csv').open('w',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    grouped=[]
    for case in ('s29_early','s43_early','s29_late'):
        for cell in range(16,26):
            part=[r for r in rows if r['case']==case and r['arm'] in ('none','hold') and r['cell']==cell]
            grouped.append(dict(case=case,cell=cell,samples=len(part),
                model_positive=sum(r['model_V90_minus_V110']>0 for r in part),
                native_positive=sum(r['native_V90_minus_V110']>0 for r in part),
                mean_model_n=sum(r['model_n'] for r in part)/len(part),mean_native_n=sum(r['native_n'] for r in part)/len(part),
                mean_model_delta=sum(r['model_V90_minus_V110'] for r in part)/len(part),
                mean_native_delta=sum(r['native_V90_minus_V110'] for r in part)/len(part),
                mean_model_speed=sum(r['model_speed'] for r in part)/len(part),
                mean_native_speed=sum(r['native_speed'] for r in part)/len(part)))
    summary=dict(stage='saved_state_fd_comparison_complete',cases=cases,cells=grouped,source_pins=pins,
        prior_pin_checks=len(verification),executed_free_speed_algebra_max_residual=max_vf_residual,
        new_rollouts=0,new_native_runs=0,fits=0,
        interpretation='Local same-density desired-speed law only. Observed future states used for diagnosis, never fed to a forecast. No net benefit or causal conclusion. Previously examined seeds, not unused holdouts.')
    assert all(digest(Path(p))==h for p,h in pins.items())
    (OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps(dict(cases=cases,cells=[r for r in grouped if r['cell'] in (16,18,20,23,24,25)]),indent=2))


if __name__=='__main__':main()
