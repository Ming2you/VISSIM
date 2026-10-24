"""Default archive replay and installed regime vs isolated equation probe."""
from study import *

VARIANTS={
 'recovery':({'relaxation':{'acceleration_sec':24.,'deceleration_sec':12.}}, {'tau_acc_sec':24.,'tau_dec_sec':12.}),
 'gradient':({'anticipation':{'downstream_ge_local':70.,'downstream_lt_local':12.}}, {'nu_high':70.,'nu_low':12.}),
 'critical':({'congested_nu_multiplier':2.},{'nu_congested_factor':2.}),
}

def main():
    out=HERE/'installed_v1';out.mkdir(exist_ok=False)
    params=e.load(BASE/'selected_parameters.json')['parameters'];cases=build_cases();results={};count=0
    for name,(settings,probe) in VARIANTS.items():
        cfg=e.load(BASE/'config.json');cfg['freeway']['state_response']={'FW_E':settings}
        candidate=out/name;candidate.mkdir();e.save(candidate/'config.json',cfg)
        e.save(candidate/'selected_parameters.json',e.load(BASE/'selected_parameters.json'))
        e.save(candidate/'port_profile.json',e.load(BASE/'port_profile.json'))
        results[name]={}
        for seed,case in cases.items():
            base_model=case['model'];model=e.load_base_model(case['data'].geometry,candidate/'config.json')
            # Compare independently constructed diagnostic equation hooks with
            # the installed runtime over all states, not only scalar metrics.
            for item_name,item in case['items'].items():
                with mechanism(probe):expected=e.simulate(base_model,item['window'],params)
                pred=e.simulate(model,item['window'],params)
                for field in ['cells','flows','ports','ramps']:
                    if pred[field]!=expected[field]:raise AssertionError((name,seed,item_name,field))
                old=e.simulate(base_model,item['window'],params)
                for field in ['cells','flows']:
                    if [r for r in pred[field] if r['road']=='FW_W'] != [r for r in old[field] if r['road']=='FW_W']:
                        raise AssertionError(('Unconfigured west changed',name,seed,item_name,field))
                if item_name.startswith('pair_'):
                    arm=item_name[5:];era='early13' if seed==13 else 'late23'
                    archived=e.load(H/'plant_completion_20260919/response_installed_v2'/f'{era}_node_{arm}.json')
                    if json.loads(json.dumps(old))!=archived:raise AssertionError(('Default changed',seed,arm))
                count+=1
            installed_case={**case,'model':model}
            results[name][str(seed)]=assess(installed_case,{},params)
            print(name,seed,results[name][str(seed)]['absolute_loss'],results[name][str(seed)]['response_loss'],flush=True)
    e.save(out/'results.json',{'records':results,'installed_vs_probe_full_state_checks':count,
        'default_archive_exact':True,'unconfigured_west_exact':True,
        'qualification':'Experimental configs only; joint cost-direction gate remains required.'})

if __name__=='__main__':main()
