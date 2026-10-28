import json
for T in [1800,1950,2100]:
    r=json.load(open('ext/n5_%06d.json'%T,encoding='utf-8'))
    base=r['audit']['baseline_objective']
    inc=[t for t in r['trial_rows'] if t['objective'] is not None and abs(t['objective']-base)<1e-9]
    fm=r['final_merge']
    print('T',T,'baseline',round(base,4),'n incumbent trial rows',len(inc),'final',round(r['final_total'],4))
    ks=['RM_C10639','RM_C10681','RM_C10490','RM_C10484','RM_C10480']
    if inc:
        im=inc[0]['merge']
        print('  incumbent accepted veh', {k[4:]:round(im['accepted_vehicles_by_ramp'][k],2) for k in ks}, 'FW_E rate', round(im['rate_veh_h_by_owner']['FW_E'],1))
    print('  selected  accepted veh', {k[4:]:round(fm['accepted_vehicles_by_ramp'][k],2) for k in ks}, 'FW_E rate', round(fm['rate_veh_h_by_owner']['FW_E'],1), fm['start_sec'], fm['end_sec'])
    print('  final omega FW_E', round(r['final_omega']['FW_E'],3), 'FW_W', round(r['final_omega']['FW_W'],3), 'PASSIVE', round(r['final_omega']['PASSIVE_OMEGA'],3))
    # tangent points omega
    for t in r['tangent']:
        print('   tangent', t['n'], 'obj', round(t['objective'],4), 'FW_E', round(t['omega']['FW_E'],3), 'PASSIVE', round(t['omega']['PASSIVE_OMEGA'],3), 'merge', {k[4:]:round(t['merge']['accepted_vehicles_by_ramp'][k],1) for k in ks})
