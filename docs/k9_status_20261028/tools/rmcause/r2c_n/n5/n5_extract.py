"""N5: compact read-only extraction from W264 decision JSONs (no replays)."""
import json,sys,os,re,hashlib,time
D=r'D:/VISSIM-runs-window264-s29-9000-recovery-20261007/sdmpc/decisions_sdmpc31_sdmpc9000_s29'
OUT=os.path.join(os.path.dirname(os.path.abspath(__file__)),'ext')
OWN=None
def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as s:
        for b in iter(lambda:s.read(1<<20),b''): h.update(b)
    return h.hexdigest()
def phys(cp, pats):
    out={}
    for n,v in zip(cp['names'],cp['values']):
        if isinstance(n,str) and any(p in n for p in pats): out[n]=v
    return out
def pr_merge(q):
    if not q: return None
    m=q.get('physical_ramp_merge') or q.get('predicted_ramp_merge')
    return None if m is None else {k:m.get(k) for k in ('start_sec','end_sec','accepted_vehicles_by_ramp','rate_veh_h_by_ramp','rate_veh_h_by_owner')}
for T in sys.argv[1:]:
    t0=time.time()
    f=os.path.join(D,'action_%06d.json'%int(T))
    o=json.load(open(f,encoding='utf-8'))
    md=o['metadata']; j=md['joint_leader_selection']
    owners=list(j['omega_partition']['costs'].keys())
    coord=j['coordinates']
    mi=[i for i,a in enumerate(coord) if a['kind']=='meter']
    rec={'T':int(T),'file':f,'sha256':sha(f),
         'action':{k:o[k] for k in ('N_P_star','N_UF_star','ramp_metering')},
         'vsl_non110':{k:v for k,v in o['vsl'].items() if v!=110},
         'reference_meter_green':{k:v for k,v in o['diagnostics'].items() if k.startswith('rw_meter_green_')},
         'owners':owners,
         'meter_axes':[dict(idx=i,key=coord[i]['key'],owner=coord[i]['owner'],block=coord[i].get('block'),ref=coord[i].get('reference_value'),allowed=coord[i].get('allowed'),scale=coord[i]['scale']) for i in mi],
         'axis_kinds':{k:sum(1 for a in coord if a['kind']==k) for k in set(a['kind'] for a in coord)},
         'audit':j.get('meter_neighbor_audit'),
         'budget_candidates':j.get('candidates'),
         'held_objective':j.get('held_objective'),'selected_objective':j.get('selected_objective'),
         'warm_start_objective':j.get('warm_start_objective'),'prediction_ttt_reduction':j.get('prediction_ttt_reduction'),
         'final_omega':j['omega_partition']['costs'],'final_total':j['omega_partition']['total_veh_h'],
         'final_constraints':{k:j['final_constraints'].get(k) for k in ('np','nuf','meter_rate_veh_h_by_owner')},
         'final_merge':pr_merge(j['final_constraints']),
         'control_sequence':j.get('control_sequence'),
         'policy_fixed_vsl':j['policy'].get('fixed_vsl'),
         'policy_tol':j['policy'].get('objective_tolerance'),
         'meter_operating_bounds':j.get('meter_operating_bounds'),
         'trial_rows':[dict(cap=r.get('cap'),iteration=r.get('iteration'),objective=r.get('objective'),feasible=r.get('feasible'),token=r.get('action_token'),
                             np=(r['quantities'].get('np') or {}).get('actual'),nuf=(r['quantities'].get('nuf') or {}).get('actual'),
                             meter_rate=r['quantities'].get('meter_rate_veh_h_by_owner'),merge=pr_merge(r['quantities'])) for r in j.get('trial_rows',[])],
         'pfo':{k:j['pfo_warm_start'].get(k) for k in ('initial_omega_objective','selected_omega_objective','selected_owned_objective','status')},
         'tangent':[],
         'prediction_state':o.get('prediction',{}).get('state_summary'),
         'prediction_error':o.get('prediction_error'),
         'future_blocks':[dict(vsl_non110={k:v for k,v in b.get('vsl',{}).items() if v!=110}, ramp_metering=b.get('ramp_metering')) for b in o['diagnostics'].get('sdmpc_prediction_sequence',{}).get('future',[])],
         'observed_vsl_history':md.get('observed_vsl_history'),
         'lane_plant':{k:md.get(k) for k in md if k.startswith('lane_plant') or k=='freeway_state_response_enabled'},
         'ramp_reference_contract':md.get('ramp_reference_contract'),
        }
    gr=j.get('gradient_rows',[])
    for n,t in enumerate(j.get('tangent_derivatives',[])):
        sp=t.get('surrogate_prediction',{})
        cj=t.get('cost_jacobian')
        tr=dict(n=n,objective=sp.get('objective_veh_h'),token=sp.get('action_token'),costs=t.get('costs'),
                omega=(sp.get('sdmpc_omega_partition') or {}).get('costs'),
                cost_jac_meter=[[row[i] for i in mi] for row in cj] if cj else None,
                merge=pr_merge(sp.get('control_area',{})),
                ttt=sp.get('control_area',{}).get('ttt_veh_h'),
                phys=phys(sp.get('central_physical',{'names':[],'values':[]}),['freeway_density/FW_E/','ramp_queue/RM_C10','merge_pending','mainline_origin_queue/FW_E']))
        tr['grad_meter']=[dict(key=g['key'],block=g['block'],own=g.get('own'),external=g.get('external'),total=g.get('total'),anchor_z=g.get('anchor_z')) for g in gr[n*len(coord):(n+1)*len(coord)] if g['kind']=='meter']
        rec['tangent'].append(tr)
    out=os.path.join(OUT,'n5_%06d.json'%int(T))
    json.dump(rec,open(out,'w',encoding='utf-8'),ensure_ascii=False,indent=1)
    print(T,'done',round(time.time()-t0,1),'s', flush=True)
