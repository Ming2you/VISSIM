"""User-requested stronger negative-gradient anticipation; bounded sensitivity.

Increase only nu_low from the frozen paired fit. No new capacity or reward.
"""
import json,traceback,sys
import vsl_response as v
from prepare import save,table
O=v.O


def main():
    specs=[]
    mild=len(sys.argv)>1 and sys.argv[1]=='mild'
    prefix='recovery_mild' if mild else 'recovery'
    for label in v.LABELS:
        values=v.c.load(O/(label+'_selected.json'))['selected']['spec']['calibration_values']
        if mild:
            if not label.startswith('wang'):continue
            for low in (60.,90.):
                specs.append(v.specification(label,'vr_recovery_'+label+'_low'+str(int(low)),{**values,'nu_low':low},v.f.ARMS))
            continue
        for strength,low_mult,high_mult in [('moderate',2.,1.5),('strong',3.,2.)]:
            proposed={**values,'nu_low':max(low_mult*values['nu_low'],high_mult*values['nu_high'])}
            specs.append(v.specification(label,'vr_recovery_'+label+'_'+strength,proposed,v.f.ARMS))
    save(O/(prefix+'_protocol.json'),dict(request='Increase anticipation during recovery',
        operational_definition='rho_downstream < rho_local; spatial negative gradient, not every temporal recovery event.',
        positive_gradient_unchanged=True,other_parameters_unchanged=True,capacity_drop_unchanged=True,
        values=specs,original_search_nu_upper=90,expanded_diagnostic_only=not mild,
        physical_gate='Mass, density, Courant and maxspeed180 checks, then actual discharge/stock and costs.',
        fit_scope='Finite sensitivity candidates, not a new joint optimization. No parameter selection from held-back late response.',
        independent_validation=False,production_adopted=False))
    actual=v.c.load(v.B.parent/'response_chain_20260921/qualification.json')['gains']
    results=[];metrics=[];gains=[]
    for spec in specs:
        try:
            row=v.execute(spec);results.append(row)
        except Exception as error:
            failure=dict(name=spec['name'],error=str(error),traceback=traceback.format_exc(),qualified=False)
            save(O/(spec['name']+'_failure.json'),failure);results.append(failure);continue
        pp={a:v.f.load_prediction(O/spec['name']/f'refined_guard1_{a}.json') for a in ('none','vsl')}
        arrays={a:v.c.predicted(p) for a,p in pp.items()}
        for phase,lo,hi in [('train',0,10),('late',10,15)]:
            _,metric=v.response_metrics(arrays,lo,hi)
            metrics.append(dict(name=spec['name'],phase=phase,nu_low=spec['calibration_values']['nu_low'],
                nu_high=spec['calibration_values']['nu_high'],**metric,**v.c.score(pp['none'],lo,hi)))
        result=v.c.load(v.K/('segment_resolution_20260921_cal_'+spec['name'])/'result.json')
        for a in v.f.ARMS[1:]:
            gains.append(dict(name=spec['name'],arm=a,actual=actual[a]['actual']['total'],**result['deltas'][a]))
    save(O/(prefix+'_results.json'),dict(results=results,metrics=metrics,gains=gains,production_adopted=False))
    if metrics:table(O/(prefix+'_metrics.csv'),metrics)
    if gains:table(O/(prefix+'_gains.csv'),gains)
    print(json.dumps(dict(metrics=metrics,gains=gains),indent=2),flush=True)


if __name__=='__main__':main()
