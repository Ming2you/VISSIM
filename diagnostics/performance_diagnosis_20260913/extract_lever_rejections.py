"""Extract three existing V3 decision receipts; no model or trajectory import."""
from pathlib import Path
import collections
import hashlib
import json

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
RUN=ROOT/'evaluation/runs/codex_fid_cl9000_s13_v3/decisions_codex_fid_cl9000_s13_v3'
report={'schema':'recorded-lever-selection-diagnosis/v1','completed':False,
        'native_runs':0,'model_queries':0,'detail_times_sec':[2400,3150,4500],
        'scope':'Three existing completed V3 decisions; search history and final-gap audit separated. Own-payoff is not global Omega TTT.',
        'source_sha256':{},'decisions':[]}
for t in report['detail_times_sec']:
    path=RUN/f'action_{t:06d}.joint.json'
    raw=path.read_bytes()
    report['source_sha256'][str(path.relative_to(ROOT))]=hashlib.sha256(raw).hexdigest()
    j=json.loads(raw);selection=j['selection'];r=j['selected_diagnostics']['joint_shared_response']
    search=r['search']
    attempts=[]
    for c in selection['candidates']:
        if c['status']=='unvisited':continue
        row={k:c.get(k) for k in ('index','target_np_veh','target_nuf_veh_h','meter_bank_index','grouped_meter_rates_veh_h','status','objective_veh_h','elapsed_sec','game_error','evaluations')}
        if 'initializer_evidence' in c:
            row['initializer_evidence']=c['initializer_evidence']
        attempts.append(row)
    fs=[{'sweep':s['sweep'],'freeway':{o:s['owners'][o] for o in ('FW_W','FW_E')}} for s in search['search_sweeps']]
    selected=selection['candidates'][selection['selected_index']]
    holds=[c for c in selection['candidates'] if c['target_np_veh']==2400.0]
    report['decisions'].append({'sim_sec':t,'selected_index':selection['selected_index'],
        'leader_domain_count':selection['domain_count'],'attempted_indices':selection['attempted_indices'],
        'status_counts':dict(collections.Counter(c['status'] for c in selection['candidates'])),
        'hold_NP_cap_meter_seeds_unvisited':sum(c['status']=='unvisited' for c in holds),
        'attempted_candidates':attempts,'search_status':r['search_status'],
        'sweeps_started':r['sweeps_started'],'sweeps_completed':r['sweeps_completed'],
        'freeway_search':fs,
        'accepted_updates':[{k:v for k,v in a.items() if k not in ('lever_values','physical_command_key')} for a in search['accepted_updates']],
        'final_audit_freeway':{o:r['per_owner'][o] for o in ('FW_W','FW_E')},
        'final_check_complete':r['final_check_complete'],'maximum_finite_candidate_gap':r['maximum_finite_candidate_gap'],
        'selected_quantities':r['quantity_constraints'],
        'selected_initializer_seed_checks':selected['fast_np']['seed_checks']})
report['code_findings']=[
    {'path':'evaluation/controllers/joint_owner_game.py','line':785,'finding':'Strict lower own cost; ties retain incumbent.'},
    {'path':'evaluation/controllers/joint_owner_game.py','line':808,'finding':'Round-robin commit applies one greatest observed own-payoff improvement across all owners, including partial sweep stop.'},
    {'path':'evaluation/controllers/joint_owner_game.py','line':821,'finding':'Final audit visits owners sequentially and never commits improvements.'},
    {'path':'evaluation/controllers/joint_owner_neighbors.py','line':108,'finding':'Candidate family order is coupled, pure VSL, pure meter for freeway; first three distinct neighbors cover these families when all are present.'},
    {'path':'evaluation/controllers/joint_owner_neighbors.py','line':1030,'finding':'Each physical ramp has actual green +/-2s lattice. Service ceiling coordinates, not accepted throughput. g10 allows g9/g8, not g6 in same decision.'},
    {'path':'evaluation/controllers/area_follower_objective.py','line':1301,'finding':'NUF target is initialized from actual-hold accepted mainline merge forecast and fixed for every seed/candidate.'}]
report['conclusions']=[
    'All three recorded selected searches stop before one whole sweep. FW_E has a small positive feasible own-payoff improvement, but one larger urban improvement is committed.',
    'The inspected selected-game freeway neighbors have zero recorded constraint rejections. Their unchanged final commands cannot be attributed to NP/NUF infeasibility from these logs.',
    'Both alternative leader attempts use NP cap -250 and stop restoration with NP violation; NUF satisfies +/-40 in their saved initializer evidence. Other feasible-cap meter seeds remain unvisited.',
    'A target frozen at actual OPEN accepted flow mathematically disallows an aggregate450s merge decrease exceeding5vehicles unless compensated at another ramp; no positive lower target is explored here. This is a domain limitation, not proof that it rejected the inspected candidates.',
    'Per-candidate feasible payoff values/actions are absent in these receipts. West no-positive gap cannot distinguish exact ties from losses. Counterfactual rerun must preserve prices/state/forecast/command box.'
]
report['completed']=True
(OUT/'lever_rejections.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
lines=['# V3 VSL·meter 미선택: 기존 기록 확인','',
       '2400·3150·4500초의 기존 완료 결정만 검토했다. 전체 궤적이나 모델을 다시 계산하지 않았다. 아래 gap은 해당 owner의 local+price 비용 감소이며 Ω TTT 감소와 다르다.','',
       '| 시각 | W/E 탐색 완료 이웃 | W/E 제약 탈락 | E best own gap | 실제 채택 owner / own gap | W/E 최종 감사 완료 이웃 |',
       '|---:|---:|---:|---:|---|---:|']
for d in report['decisions']:
    fw=d['freeway_search'][0]['freeway'];au=d['final_audit_freeway'];u=d['accepted_updates'][0]
    lines.append(f"|{d['sim_sec']}|{fw['FW_W']['feasible_neighbors']}/{fw['FW_E']['feasible_neighbors']}|{fw['FW_W']['infeasible_neighbors']}/{fw['FW_E']['infeasible_neighbors']}|{fw['FW_E']['observed_gap_lower_bound']:.9f}|{u['owner']} / {u['gap']:.9f}|{au['FW_W'].get('feasible_neighbors',0)}/{au['FW_E'].get('feasible_neighbors',0)}|")
lines += ['',
    '- 각 freeway의 생성 후보는63개지만 탐색은3~4개의 이웃만 점수화했다. 세 결정 모두1 sweep 시작·0 완료다. 중단할 때19 owner 중 가장 큰 own-payoff 개선 한 개만 적용했다. 작은 동측 개선은 더 큰 도시 owner 개선에 밀렸다.',
    '- 최종 감사는 서측부터 순차 진행하며 명령을 갱신하지 않는다. 시간 만료로 동측 감사는 미방문이다. 이 감사의 미방문을 탐색도 미방문이었다고 읽으면 안 된다.',
    '- 다른 두 leader 후보는 각각NP cap−250를 시도했고 복원 예산으로 중단됐다. 저장된 복원 결과의NP는2400초291.689,3150초272.028,4500초198.933대이며 모두cap초과다. 같은 결과의NUF는±40veh/h안에 있었다. 후보가 수학적으로 불가능하다고 증명한 결과가 아니다.',
    '- NUF를현재OPEN 명령의예측수용량으로고정하면450초합류총량을5대넘게줄이는명령은다른램프증가로상쇄하지않는한탈락한다. 그러나위실제방문이웃은제약탈락0이므로현재미선택의직접원인을NUF로단정하지않는다.',
    '- g10→g8도여전히평균서비스상한이예측도착보다높을가능성이있다. 전체450초평균합류량만으로이것을증명할수없고,세부응답이동률인지손해인지기존로그는저장하지않았다. 같은실제상태제한재현결과는lever_counterfactual2400/에서별도로보관한다.',
    '', '추출 스크립트: `extract_lever_rejections.py`. 상세 값·원본 SHA·코드 위치: `lever_rejections.json`.']
(OUT/'lever_rejections.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps({'completed':True,'decisions':len(report['decisions'])}))
