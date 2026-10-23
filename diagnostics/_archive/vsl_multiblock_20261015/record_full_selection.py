import csv, hashlib, json
from pathlib import Path
HERE=Path(__file__).resolve().parent
read=lambda p:json.loads(Path(p).read_bytes())
out=HERE/'full_selection_verification.json'
assert not out.exists()
folder=HERE/'full_selection3300'
j=read(folder/'unused.joint.json');s=j['selection'];audit=s['vsl_schedule_audit']
completion=read(folder/'completion.json');written=read(folder/'unused.joint_written.json')
assert j['completed'] and s['feasible'] and s['final_constraints']['feasible']
assert completion['status']=='complete' and completion['full_selection']
assert s['policy']['vsl_schedule_audit'] and audit['additional_predictions']==len(audit['candidates'])==25
assert all(row['feasible'] for row in audit['candidates'])
assert audit['selected'] is None and all(row['delta_veh_h']>=-1e-7 for row in audit['candidates'])
assert written['prewrite_binding_passed'] and written['written_command_binding_passed']
assert hashlib.sha256((folder/'unused.csv').read_bytes()).hexdigest()==written['action_csv']['sha256']
assert hashlib.sha256((folder/'unused.json').read_bytes()).hexdigest()==written['action_json']['sha256']
commands=list(csv.DictReader((folder/'unused.csv').open(encoding='utf-8-sig')))
speeds={float(row['speed_kph']) for row in commands if row['kind']=='vsl'}
assert speeds=={110.}
exact=read(HERE/'exact_selected3300_v2/summary.json')
assert exact['status']=='complete' and exact['predictions']==2
assert exact['rows'][1]['physical_feasible'] and exact['rows'][1]['quantity_constraints']['feasible']
assert exact['selected_minus_held_veh_h']<0
assert exact['selected_sha256']==written['action_json']['sha256']
result=dict(status='search_full_path_and_exact_selected_model_verified',
    full_selection_seconds=completion['seconds'],new_vsl_audit_seconds=audit['seconds'],
    vsl_candidates=25,vsl_selected=False,final_vsl_speeds=sorted(speeds),
    held_surrogate_objective=s['held_objective'],selected_surrogate_objective=s['selected_objective'],
    final_quantity_constraints=s['final_constraints'],control_sequence=s['control_sequence'],
    converged=s['converged'],selection_status=s['selection_status'],
    exact_execution_model=exact,native_runs=0,plant_calibration_complete=False,
    caveat='Cold offline selection; no native benefit or general convergence claim. VSL candidate coverage is fixed, but current plant still predicts no gain.',
    sources={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in
        (folder/'completion.json',folder/'unused.joint.json',folder/'unused.joint_written.json',HERE/'exact_selected3300_v2/summary.json')})
out.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf8')
plan=read(HERE/'plan.json')
plan['status']='search_verified_native_multizone_preparation_pending'
plan['completed'].update(full_optimizer_runs=1,exact_selected_vs_held_predictions=2,baseline_reuse_metadata_checks=10)
plan['next_stage']['status']='native_multizone_preparation_pending'
plan['next_stage']['full_selection_verified']=str(out)
plan['next_stage']['full_selections_started']=1
plan['next']='Full selection and its2 exact execution checks are COMPLETE; do not rerun. All25 VSL schedules were feasible but no benefit predicted. Proceed only with next_stage single multizone native preparation after qualifying old hold reuse; current baseline metadata10checks passed. Keep plant goal incomplete.'
(HERE/'plan.json').write_text(json.dumps(plan,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
summary=read(HERE/'summary.json')
summary.update(status=plan['status'],full_optimizer_runs=1,exact_selected_validation_predictions=2,
               full_selection_verification=str(out))
(HERE/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf8')
with (HERE/'README.md').open('a',encoding='utf8') as f:
    f.write('\n## 전체선택 후속 검증 완료\n\n'
            f"전체 선택 {completion['seconds']:.1f}초, 새25개 VSL 검사 {audit['seconds']:.1f}초. 모든 후보가 동일cap·물리 제약을 통과했지만 비용 이득이 없어110을 유지했다. 최종 명령3블록·writer 바인딩이 통과했다.\n\n"
            f"선택 후 이산 실행모델2예측도 완료: 이전 명령 {exact['rows'][0]['objective_veh_h']:.6f}, 선택 명령 {exact['rows'][1]['objective_veh_h']:.6f}대·시간. 선택 명령의 물리·NP/NUF 제약 통과. native 개선 또는 수렴/최적해를 뜻하지 않는다. 탐색 구현 검증은 완료했고 동역학 보정은 진행 중이다.\n\n"
            '기존 OFF2250 기준선의 실행·관측·명령 바이트10개 검사는 통과했다. 다음은 정본 사전검사를 거쳐 기존 단일90 자료를 재사용하고 다구역90 조건만 최대1회 추가하는 작업이다.\n')
print(json.dumps(dict(status=result['status'],seconds=completion['seconds'],vsl_extra_seconds=audit['seconds'],
    exact_selected_minus_held=exact['selected_minus_held_veh_h'],native_runs=0),indent=2))
