"""Independent grouped timing algebra and preserved-source check; no rollout."""
import ctypes
import json
import math
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE=Path(__file__).resolve().parent/'port_endpoint_repair'


def main():
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.GetCurrentProcess.restype=ctypes.c_void_p
    kernel.SetPriorityClass.argtypes=[ctypes.c_void_p,ctypes.c_uint32]
    assert kernel.SetPriorityClass(kernel.GetCurrentProcess(),0x4000)
    protocol=h.read(HERE/'protocol.json');pins=h.read(HERE/'pins.json')
    for p,d in {**pins,**protocol['protected_sha256'],protocol['STOP']['path']:protocol['STOP']['sha256']}.items():assert h.sha(p)==d,p
    bins=h.read(HERE/'bins.json.gz');groups=h.read(HERE/'groups.json');checks=h.read(HERE/'checks.json')
    assert len(bins)==1440 and len(groups)==72 and len(checks)==480
    assert all(r['actual']==r['reference'] for r in checks)
    worst=0.;model_checks=0
    for g in groups:
        part=[r for r in bins if all(r[k]==g[k] for k in ('case','arm','kind','block'))]
        assert len(part)==30
        times=[r['time_end'] for r in part]
        assert len(set(times))==30 and all(abs(b-a-5)<1e-8 for a,b in zip(times,times[1:]))
        key=g['assignment'];a=[r[key] for r in part];m=[r['merge10490'] for r in part]
        centered=0.
        for block in range(5):
            j=block*6;mean=math.fsum(m[j:j+6])/6
            centered+=math.fsum(a[t]*(m[t]-mean) for t in range(j,j+6))
        worst=max(worst,abs(centered-g['overlap_excess']))
        independent=math.fsum(g['cyclic_reference'])/6
        worst=max(worst,abs(independent-g['same30s_independent_phase_product']))
        assert abs(math.fsum(a)-g['main'])<1e-8 and abs(math.fsum(m)-g['merge'])<1e-8
        if g['kind']=='native':
            assert all(float(v).is_integer() and v>=0 for v in a+m)
            assert all(r[key]<=r['main20_all'] for r in part)
        else:
            assert 'native_uniform_multinomial_variance_reference' not in g
    # Model five-second sums must reproduce its independently saved30s ledger.
    for case,arm in sorted({(r['case'],r['arm']) for r in bins}):
        z=h.read(h.R/f'queue_dynamics178/forecast/baseline/{case}_{arm}.json.gz')
        part=[r for r in bins if r['case']==case and r['arm']==arm and r['kind']=='model']
        for j in range(15):
            segment=part[6*j:6*j+6];end=segment[-1]['time_end']
            ledger={r['cell']:r for r in z['flows'] if abs(r['window_end_s']-end)<1e-7}
            for cell in (19,20,21):
                error=math.fsum(r[f'main{cell}_all'] for r in segment)-ledger[cell]['downstream_crossings']
                assert abs(error)<1e-8;worst=max(worst,abs(error));model_checks+=1
            error=math.fsum(r['merge10490'] for r in segment)-ledger[21]['ramp_merges']
            assert abs(error)<1e-8;worst=max(worst,abs(error));model_checks+=1
    assert worst<1e-8
    result=dict(status='PASS',native_ledger_checks=len(checks),model_ledger_checks=model_checks,group_algebra=72,
        max_numeric_difference=worst,port_supported_boundaries=sum(r.get('port_supported_crossings',0) for r in bins),
        source_and_STOP_preserved=True,forecasts=0,fits=0,FZP=0,native=0,
        limitation='No within5s crossing-lane or causality validation; original endpoint-only failure preserved.')
    h.save(HERE/'verification.json',result);print(json.dumps(result))


if __name__=='__main__':main()
