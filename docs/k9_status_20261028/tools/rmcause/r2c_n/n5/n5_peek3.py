import json,sys,os
D=r'D:/VISSIM-runs-window264-s29-9000-recovery-20261007/sdmpc/decisions_sdmpc31_sdmpc9000_s29'
f=os.path.join(D,sys.argv[1])
o=json.load(open(f,encoding='utf-8'))
md=o['metadata']; j=md['joint_leader_selection']
print('observed_vsl_history', json.dumps(md.get('observed_vsl_history'))[:1500])
sp=j['tangent_derivatives'][0]['surrogate_prediction']
q=sp['quantities']; print('quantities keys', {k:len(json.dumps(v)) for k,v in q.items()})
cp=sp['central_physical']; print('central_physical keys', {k:len(json.dumps(v)) for k,v in cp.items()} if isinstance(cp,dict) else type(cp))
ca=sp['control_area']; print('candidate_scores', ca['candidate_scores'], 'ttt', ca['ttt_veh_h'], 'near', ca['near_score_veh_h'], 'add', ca['additional_cost_veh_h'], 'approx', ca['prediction_approximation'])
fc=ca['flow_counts']; ks=[k for k in fc if 'FW_E' in k or 'RM_C10' in k]; print('flow keys sample', ks[:40], len(fc))
print('predicted_ramp_merge', json.dumps(ca['predicted_ramp_merge'])[:900])
tp=j['tangent_derivatives'][0]['central_physical']; print('td central_physical keys', {k:len(json.dumps(v)) for k,v in tp.items()} if isinstance(tp,dict) else type(tp))
print('control_sequence', json.dumps(j['control_sequence']))
print('policy', json.dumps(j['policy'])[:1700])
print('meter_operating_bounds', json.dumps(j['meter_operating_bounds'])[:2100])
for k in md:
    if any(s in k.lower() for s in ['vsl','state_response','lane_plant','delta','service_table','head_service']):
        print('MD', k, json.dumps(md[k])[:300])
