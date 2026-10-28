import json,sys
for T in map(int,sys.argv[1:]):
    r=json.load(open('ext/n5_%06d.json'%T,encoding='utf-8'))
    a=r['audit']
    print('=== T',T,'vsl block0',r['vsl_non110'],'future',[b['vsl_non110'] for b in r['future_blocks']], 'ref green',{k[15:]:v for k,v in r['reference_meter_green'].items()})
    print(' baseline',round(a['baseline_objective'],4),'selected',a['selected'],'final',round(r['final_total'],4),'held(PFO)',round(r['held_objective'],4),'pred_red',round(r['prediction_ttt_reduction'],4))
    for ba in a['budget_audits']:
        print('  incumbent nuf',round(ba['nuf_target'],1),'np',round(ba['np_cap'],1),'base',round(ba['baseline_objective'],4),'sel',ba['selected'],'tok',ba['incumbent_action_token'][:8])
    rows={}
    for c in a['candidates']:
        rows.setdefault(c['candidate'],[]).append((round(c['nuf_target']),round(c['delta_veh_h'],4),c['feasible']))
    for k in sorted(rows): print('   ',k.ljust(20),rows[k])
