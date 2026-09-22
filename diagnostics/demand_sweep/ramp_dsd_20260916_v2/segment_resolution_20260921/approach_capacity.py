"""Isolate receiving vs operational-lane loss at the frozen recalibrated point.

These removals are diagnostic ablations, not calibrated controller candidates.
Physical storage, conserved flows, destination FIFO and queues remain active.
"""
import copy,json,subprocess,sys,time
from pathlib import Path
import vsl_response as v
from prepare import save,table
c=v.c;f=v.f;B=v.B;ROOT=v.ROOT;K=v.K;O=B/'approach_resolution_v1'


def main():
    assert not (O/'capacity_protocol.json').exists()
    initial=c.load(v.O/'vr_hadi_fd_cap_r2_validation.json')
    plan=[('no_ctm',False,True),('no_operational_loss',True,False),('neither',False,False)]
    save(O/'capacity_protocol.json',dict(purpose='Current fitted point has strong receiving losses absent in the older baseline; isolate two imposed bottleneck mechanisms.',
        ablations=plan,all_other_parameters_fixed=True,fit=False,future_inputs=False,qualified=False,
        gates='Numerics, original NC train/late errors, matched control deltas/components and response errors; no automatic adoption even if total gain sign changes.',
        preserved=['physical storage','conservation','actual accepted merge','hard destination FIFO','ramp and off queues','actuator commands','demand','dt1','31cell mesh'],
        source_pins={str(p.relative_to(ROOT)):c.sha(p) for p in [Path(__file__),B/'run.py',v.O/'vr_hadi_fd_cap_r2_validation.json',O/'ledger_summary.json']}))
    results=[]
    for label,ctm,operational in plan:
        spec=copy.deepcopy(initial);spec.update(name='ar_'+label,output_group=O.name,arms=list(f.ARMS))
        spec['hadiuzzaman']['ctm']=ctm
        if not operational:spec['port_response']['spillback']=None
        path=O/(spec['name']+'.json');save(path,spec);started=time.perf_counter()
        with (O/(spec['name']+'_process.log')).open('x',encoding='utf-8') as log:
            subprocess.run([sys.executable,'-B','-X','utf8',str(B/'run.py'),'refined_guard1',str(path)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
        elapsed=time.perf_counter()-started;checks={};arrays={}
        for arm in f.ARMS:
            p=f.load_prediction(O/spec['name']/f'refined_guard1_{arm}.json');checks[arm]=c.screen(p)
            reference=f.load_prediction(O/'ar_baseline'/f'refined_guard1_{arm}.json')
            for key in ('cells','flows'):
                assert [r for r in p[key] if r['road']=='FW_W']==[r for r in reference[key] if r['road']=='FW_W']
            if arm=='none':nc=dict(train=c.score(p),late=c.score(p,10,15))
            if arm in ('none','vsl'):arrays[arm]=c.predicted(p)
        effective=c.load(O/spec['name']/'effective_config.json');assert len(effective)==4
        for entry in effective:
            assert entry['receiving']['FW_E']==spec['hadiuzzaman'] and entry['port_response']['FW_E']==spec['port_response']
            assert entry['scalar']==spec['physical_coefficients'] and entry['state_response']['FW_E']==spec['state_response']
        response={}
        for phase,lo,hi in [('train',0,10),('late',10,15)]:_,response[phase]=v.response_metrics(arrays,lo,hi)
        result=c.load(K/('segment_resolution_20260921_cal_'+spec['name'])/'result.json')
        record=dict(label=label,numerics=checks,nc=nc,response=response,deltas=result['deltas'],seconds=elapsed,adopted=False)
        results.append(record);save(O/'capacity_results.json',dict(results=results,qualified=False));print(json.dumps(record),flush=True)


if __name__=='__main__':main()
