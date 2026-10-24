"""Same initial2400 commands, autonomous450, paired native and baseline checks."""
from pathlib import Path
import gzip,hashlib,importlib.util,json,sys

HERE=Path(__file__).resolve().parent;H=HERE.parent
read=lambda p:json.loads(p.read_bytes())


def main():
    assert not (HERE/'pair_comparison.json').exists()
    sys.path.insert(0,str(H))
    from qualify_native2400 import validate_scope
    validate_scope(read(H/'native2400_analysis/summary.json'),
                   read(H/'native2400_analysis/observed_input_qualification.json'))
    native=read(H/'wout_response/assessment_integer_ids.json')['arms']
    mainline=read(H/'native2400_assessment.json')
    attribution=read(H/'connector_lane/response_attribution.json')['native_delta_veh_h']
    loader=importlib.util.spec_from_file_location('recovery_score',H/'recovery2700/compare.py')
    helper=importlib.util.module_from_spec(loader);loader.loader.exec_module(helper)
    models={};pins={}
    for label,folder in (('baseline',H/'connector_lane/forecast2400'),('candidate',HERE/'forecast2400')):
        assert read(folder/'completion.json')['status']=='complete'
        summary=read(folder/'summary.json');rows={}
        for arm,result in summary['results'].items():
            path=folder/(arm+'.response.json.gz')
            pins[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
            response=json.loads(gzip.decompress(path.read_bytes()))
            blocks=[]
            for index,cohorts in enumerate(result['known_endpoint_cohorts']):
                start=2400+150*index
                scored=helper.summarize(response,cohorts,start)
                observed=native[arm][index]['native']
                scored['native_arrival10681']=observed['ramps']['RM_C10681']
                scored['native_W_out_final']=observed['final']['total']
                scored['native_lane68_final']={str(l):observed['final']['lanes'].get('68:'+str(l),0) for l in range(1,5)}
                blocks.append(scored)
            cost=result['costs_by_stock']
            rows[arm]=dict(blocks=blocks,omega=result['omega_ttt_veh_h'],
                mainline=sum(v for k,v in cost.items() if k.startswith('freeway:')),
                W_out=cost['storage:SC1004_W_out'],ramp10681=cost['ramp:RM_C10681'],
                merge10681=result['predicted_merge']['accepted_vehicles_by_ramp']['RM_C10681'],
                feasible=result['shared_constraints']['feasible'],resource_exceedance=result['resource_max_exceedance'])
        delta={k:rows['selected'][k]-rows['hold'][k] for k in ('omega','mainline','W_out','ramp10681','merge10681')}
        models[label]=dict(arms=rows,delta=delta,
            arrival_abs_error=sum(abs(b['arrival10681']-b['native_arrival10681']) for row in rows.values() for b in row['blocks']),
            stock_abs_error=sum(abs(b['W_out_final']-b['native_W_out_final']) for row in rows.values() for b in row['blocks']))
    actual=dict(omega=mainline['delta_omega_veh_h']['actual'],mainline=mainline['delta_mainline_veh_h']['actual'],
        W_out=attribution['full_W_out'],ramp10681=attribution['ramp10681'],
        merge10681=mainline['ramp_incremental_merge_veh']['RM_C10681']['actual_added_merge'])
    report=dict(status='complete_diagnostic_pair',models=models,native_delta=actual,
        control_gain_qualified=False,new_native=0,new_fits=0,new_predictions=2,source_pins=pins,
        caveats=['Joint city and RM actions; not an isolated10681 causal effect.',
                 'Closed native arms have exact common prefix; original prediction replay has the previously recorded tiny native prefix discrepancy.',
                 '2400-2850 includes native lane-change deletions; preserved separately, not modeled as normal throughput.'])
    (HERE/'pair_comparison.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(native=actual,models={k:{x:r[x] for x in ('delta','arrival_abs_error','stock_abs_error')} for k,r in models.items()},
        candidate_blocks={a:[{k:b[k] for k in ('arrival10681','native_arrival10681','W_out_final','native_W_out_final')}
            for b in r['blocks']] for a,r in models['candidate']['arms'].items()}),indent=2))


if __name__=='__main__':main()
