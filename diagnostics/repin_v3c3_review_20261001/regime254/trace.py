"""Two unchanged current71 forecasts to retain missing interval transfers."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
from collections import defaultdict
import copy
from pathlib import Path
import sys
import time
from diagnostics.repin_v3c3_review_20261001.deceleration248 import run as d
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h
from diagnostics.repin_v3c3_review_20261001.jin_macro111 import run as common

HERE=Path(__file__).resolve().parent/'timing'


def main():
    HERE.mkdir(exist_ok=False);d.HERE=HERE
    common.setup()
    protected={str(p):h.sha(p) for p in (h.ROOT/'evaluation/controllers').glob('*.py')}
    stop=h.read(HERE.parent/'protocol.json')['STOP']
    source=h.R/'vsl_fd253/verified/capture_s71.json'
    args=h.read(source)['argv']
    args=[x for x in args if not x.startswith(('--probe-label=','--output-suffix=','--tuning-json='))]
    tuning=h.read(h.R/'rm_restart219/budget235/config.json');tuning['adapter'].pop('sdmpc_fixed_vsl')
    h.save(HERE/'tuning.json',tuning)
    args+=['--probe-label=timing254','--output-suffix=timing254','--tuning-json='+str(HERE/'tuning.json')]
    h.save(HERE/'protocol.json',dict(scope='Current233/235, same2250seed71 RM/both; no physical changes.',
        purpose='Old248forecast summary retained only450totals. Retain true modelstep transfer timestamps to distinguish transient delay from equal450outflow.',
        budget=dict(forecasts=2,fits=0,native=0,FZP=0),protected=protected,STOP=stop,
        source=str(source),source_sha256=h.sha(source),future_observation_inputs=False))
    from diagnostics.sdmpc_n31_20260924.integration_20260926 import probe_selected_arrival_path as probe
    from evaluation.controllers import obs150_contract as oc
    old_probe,old_writer=probe.probe_levers,oc.write_derived
    def existing(raw,derived):
        obs=raw[oc.RAW_STATE_KEY];path=oc.resolve(obs,oc.derived_path(obs['sim_sec']))
        assert path.read_bytes()==oc.derived_bytes(derived)
        return path
    def capture(captured,candidates,coord,output):
        assert set(candidates)=={'held_actual','rm','vsl','both'}
        d.CAPTURES['s71']=(captured,{('nc' if k=='held_actual' else k):v for k,v in candidates.items()},coord)
    def intercepted(*a,**kw):return old_probe(*a,prepared_probe_callback=capture,**kw)
    started=time.perf_counter()
    try:
        probe.probe_levers=intercepted;oc.write_derived=existing;sys.argv=args;probe.main()
    finally:probe.probe_levers=old_probe;oc.write_derived=old_writer
    from src.controllers import rollout_endpoint as endpoint
    old_endpoint=endpoint.evaluate_price_point
    for arm in ('rm','both'):
        output={}
        def collect(*a,**kw):
            point=old_endpoint(*a,**kw)
            output['transfers']=[r for r in point.control_area_response['transfers'] if r['source']=='freeway:FW_E']
            return point
        endpoint.evaluate_price_point=collect
        try:row=d.forecast('s71',arm,1.,'current')
        finally:endpoint.evaluate_price_point=old_endpoint
        baseline=h.read(h.R/f'deceleration248/verified/s71_base_{arm}.json')
        omit={'seconds','label'}
        assert {k:v for k,v in row.items() if k not in omit}=={k:v for k,v in baseline.items() if k not in omit}
        aggregate=defaultdict(float);timed=defaultdict(float)
        for tr in output['transfers']:
            start,end=tr['start_sec'],tr['end_sec'];assert 2250<=start<end<=2700
            block=int((end-2250-1e-8)//150);assert 0<=block<=2
            assert start>=2250+150*block-1e-7
            aggregate[block,tr['target']]+=tr['vehicles']
            timed[tr['target']]+=tr['vehicles']*(2700-(start+end)/2)/3600
        for tr in row['transfers']:
            if tr['source']=='freeway:FW_E':
                assert abs(sum(n for (b,t),n in aggregate.items() if t==tr['target'])-tr['vehicles'])<1e-7
        h.save(HERE/(arm+'_timing.json'),dict(transfers=output['transfers'],
            intervals=[dict(block=b,target=t,vehicles=v) for (b,t),v in aggregate.items()],
            remaining_time_weighted_outflow=timed,clock='Midpoint of existing numerical accepted-flow step; not native exact crossingtime.'))
    assert all(h.sha(p)==sha for p,sha in {**protected,stop['path']:stop['sha256']}.items())
    h.save(HERE/'completion.json',dict(status='COMPLETE',forecasts=2,seconds=time.perf_counter()-started,
        old_full_forecasts_exact=True,fit=0,native=0,FZP=0,protected=True,adopted=False))
    print('timing254 complete;2unchangedforecasts, old outputs EXACT')


if __name__=='__main__':main()
