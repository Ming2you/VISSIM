"""Explain the finite-relaxation gate failure without fitting again."""
import hashlib,json,math
from pathlib import Path
A=Path(__file__).resolve().parent;O=A/'refine15_calibration'
read=lambda p:json.loads(p.read_bytes())
def main():
    target=O/'fit_diagnostics.json';assert not target.exists()
    data=read(O/'native_hold_cells.json');audit=read(A/'refine15_update_audit.json');fit=read(O/'fit.json')
    p=audit['parent_parameters'];rows={}
    for mode in ('parent','refined'):
        samples=[]
        for r in data['rows']:
            if not 900.1<=r['time']<=2100.1:continue
            if mode=='parent':
                n=sum(r['n'][1:4]);values=[(n,sum(n*v for n,v in zip(r['n'][1:4],r['speed'][1:4]))/n,sum(data['length_m'][1:4])/1000)]
            else:values=[(r['n'][i],r['speed'][i],data['length_m'][i]/1000) for i in (1,2,3)]
            for n,v,length in values:
                rho=n/(4*length);desired=p['v_free']*math.exp(-(rho/p['rho_crit'])**p['metanet_a_m']/p['metanet_a_m'])
                samples.append(dict(n=n,speed=v,rho=rho,desired=desired))
        def summarize(xs):
            total=sum(x['n'] for x in xs)
            return dict(samples=len(xs),vehicle_weight=total,**{key:sum(x['n']*x[key] for x in xs)/total for key in ('speed','rho','desired')})
        bins=[]
        for lo,hi in ((0,10),(10,20),(20,30),(30,40),(40,60),(60,100)):
            xs=[x for x in samples if lo<=x['rho']<hi]
            if xs:bins.append(dict(density_range=[lo,hi],**summarize(xs)))
        rows[mode]=dict(overall=summarize(samples),density_bins=bins,
            finite_relaxation_fit=fit['results'][mode]['coefficients'],linear_fit=fit['results'][mode]['linear_parameters'])
    actual=[dict(time=r['time'],middle_n=r['n'][2],middle_speed=r['speed'][2]) for r in data['rows'] if 2250<r['time']<2261]
    report=dict(status='completed_no_refit_diagnostic',native_initial_middle=actual,training_state_summaries=rows,
        fits_repeated=0,new_forecasts=0,new_native=0,goal_complete=False,
        interpretation='The existing desired-speed curve is below observed training speeds on average, increasingly at higher density. These transient samples are not equilibrium observations. Combined with the full-rank NNLS optimum at zero1/tau, this warrants checking FD/dynamic identification and Eulerian population turnover before treating the rejected finite-relaxation fit as a model-class failure.',
        next='Use the existing full-trajectory calibration method and current observational scope to preregister a bounded joint FD/dynamic identification experiment. Review prior momentum/turnover diagnostics first; do not constrain tau merely to obtain a finite or favorable answer. Keep VSL90 outcomes out of training, preserve nonoverlapping time validation and independent cases.',
        source_pins={str(path.resolve()):hashlib.sha256(path.read_bytes()).hexdigest() for path in (Path(__file__),O/'native_hold_cells.json',O/'fit.json',A/'refine15_update_audit.json')})
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(native_initial_middle=actual,training_state_summaries=rows),indent=2))
if __name__=='__main__':main()
