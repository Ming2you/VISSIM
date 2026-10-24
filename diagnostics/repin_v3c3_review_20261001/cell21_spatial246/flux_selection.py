"""One bounded current-speed-moment closure fit against endpoint exits.

This screens information/selection only, not future speed or autonomous control.
"""
import ctypes
import math
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE=Path(__file__).resolve().parent/'flux_selection'


def metrics(rows,c):
    weight=sum(r['exit_count'] for r in rows)
    if not weight:return dict(groups=0,exits=0)
    def loss(value):return sum(r['exit_count']*(r['exit_pre_speed']-r['mean_speed']-value*r['selection_feature'])**2 for r in rows)/weight
    return dict(groups=len(rows),exits=weight,group_rmse_base=math.sqrt(loss(0)),group_rmse_full_moment=math.sqrt(loss(1)),group_rmse_fit=math.sqrt(loss(c)),
        mean_exit_minus_bulk=sum(r['exit_count']*(r['exit_pre_speed']-r['mean_speed']) for r in rows)/weight,
        mean_moment_correction=sum(r['exit_count']*r['selection_feature'] for r in rows)/weight)


def main():
    assert not (HERE/'protocol.json').exists();HERE.mkdir(exist_ok=True)
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.GetCurrentProcess.restype=ctypes.c_void_p
    kernel.SetPriorityClass.argtypes=[ctypes.c_void_p,ctypes.c_uint32]
    assert kernel.SetPriorityClass(kernel.GetCurrentProcess(),0x4000)
    files=[]
    for arm in ('hold','hold_vsl90','release','release_vsl90'):files.append(('67_'+arm,h.R/f'blocking176/{arm}_frames.json.gz',2670.1))
    for arm in ('hold','hold_vsl90'):files.append(('29_'+arm,h.F/f'vsl_native_exposure/s29_late_{arm}_frames.json.gz',2670.1))
    for arm in ('none','vsl'):files.append(('43_'+arm,h.F/f'cohort_early/s43_{arm}_frames.json.gz',2220.1))
    protected={str(p):h.sha(p) for p in (h.ROOT/'evaluation/controllers').glob('*.py')}
    stop=h.read(h.R/'vsl_response243/lateral_friction244/protocol.json')['STOP']
    pins={str(p):h.sha(p) for p in [Path(__file__),*[r[1] for r in files]]}
    protocol=dict(question='Does a bounded current-speed second-moment correction predict speeds of known outgoing vehicles better than donor mean?',
        equation='v_exit_surrogate=mean(v)+c*(sum(v^2)/sum(v)-mean(v)), c in[0,1]. Zero mean implies zero correction.',
        derivation='Under uniform spatial exposure, faster vehicles have greater boundary encounter probability. This is a proposed observation closure, not a claim that uniform exposure holds in the queued VISSIM cells.',
        target='Pre-step speed of vehicles present in source cell/lane at t and seen downstream at t+5. Not instantaneous crossing speed or next speed.',
        current_inputs='All current source-cell/lane speeds; no future state or command/seed/time feature.',
        population='Cells21--25, lane-wise. Bypasses entering from a ramp within the interval are not initial-stock departures and are excluded. Missing next record is unknown, not a normal departure.',
        fit='One exit-count-weighted bounded least squares coefficient from seed29 hold110; freeze then inspect29VSL/43pair/67four. Known states,not blind.',
        gate='Each other-seed pooled groupRMSE improves10%, no armRMSE worsens10%, c>0. Necessary information test only, not sufficient dynamic/benefit qualification.',
        prior='133 accepted transport uses uniform donor speed;178/179 moving/stopped selection and213 pressure gradient already tested. This is a separate observed exiting-population moment test.',
        limitations='Five-second exit selection and initial positions matter. Current variance must be autonomously predicted before deploying any moment closure; no variance state or capacity bonus is added here.',
        protected_sha256=protected,STOP=stop,input_pins=pins,fits=1,forecasts=0,native=0,FZP=0)
    h.save(HERE/'protocol.json',protocol)
    rows=[];observed_nonexit=0;missing_next=0
    for case,path,start in files:
        doc=h.read(path);ix={k:i for i,k in enumerate(doc['fields'])}
        vi=ix.get('speed',ix.get('speed_kmh'));ci=ix['cell'];li=ix['lane']
        frames={round(float(t),1):({str(k):v for k,v in a.items()} if isinstance(a,dict) else {str(int(v[ix['vehicle']])):v for v in a}) for t,a in doc['frames'].items()}
        for j in range(90):
            t=round(start+j*5,1);current=frames[t];future=frames[round(t+5,1)]
            for cell in range(21,26):
                for lane in (1,2,3):
                    stock={v:z for v,z in current.items() if z[ci]==cell and z[li]==lane}
                    if not stock:continue
                    exiting=[z[vi] for v,z in stock.items() if v in future and future[v][ci]>cell]
                    missing_next+=sum(v not in future for v in stock)
                    observed_nonexit+=sum(v in future and future[v][ci]<=cell for v in stock)
                    if not exiting:continue
                    speeds=[z[vi] for z in stock.values()];s1=math.fsum(speeds);s2=math.fsum(v*v for v in speeds);mean=s1/len(speeds)
                    feature=s2/s1-mean if s1>0 else 0.;assert feature>=-1e-10
                    rows.append(dict(case=case,cell=cell,lane=lane,time=t,n=len(stock),mean_speed=mean,
                        speed_second_moment=s2/len(speeds),selection_feature=max(0.,feature),exit_count=len(exiting),
                        exit_pre_speed=math.fsum(exiting)/len(exiting)))
    train=[r for r in rows if r['case']=='29_hold']
    numerator=math.fsum(r['exit_count']*r['selection_feature']*(r['exit_pre_speed']-r['mean_speed']) for r in train)
    denominator=math.fsum(r['exit_count']*r['selection_feature']**2 for r in train)
    assert denominator>0
    coefficient=max(0.,min(1.,numerator/denominator))
    gradient=denominator*coefficient-numerator
    assert (0<coefficient<1 and abs(gradient)<1e-7) or (coefficient==0 and gradient>=0) or (coefficient==1 and gradient<=0)
    h.save(HERE/'frozen_coefficient.json',dict(c=coefficient,numerator=numerator,denominator=denominator,gradient=gradient,train_groups=len(train)))
    bycase={case:metrics([r for r in rows if r['case']==case],coefficient) for case,_,_ in files}
    byseed={seed:metrics([r for r in rows if r['case'].startswith(seed+'_')],coefficient) for seed in ('43','67')}
    bycell=[dict(case=case,cell=cell,**metrics([r for r in rows if r['case']==case and r['cell']==cell],coefficient)) for case,_,_ in files for cell in range(21,26)]
    passed=coefficient>0 and all(m['group_rmse_fit']<=.9*m['group_rmse_base'] for m in byseed.values()) and all(m['group_rmse_fit']<=1.1*m['group_rmse_base'] for m in bycase.values())
    h.save(HERE/'rows.json',rows);h.save(HERE/'summary.json',dict(coefficient=coefficient,bycase=bycase,byseed=byseed,bycell=bycell,
        passed_information_gate=passed,missing_next=missing_next,observed_nonexit=observed_nonexit,operational_adopted=False,goal='ACTIVE_NOT_QUALIFIED'))
    assert all(h.sha(p)==v for p,v in {**pins,**protected,stop['path']:stop['sha256']}.items())
    print('COEFFICIENT',coefficient,'PASS',passed,'ROWS',len(rows))
    for case,m in bycase.items():print(case,m)


if __name__=='__main__':main()
