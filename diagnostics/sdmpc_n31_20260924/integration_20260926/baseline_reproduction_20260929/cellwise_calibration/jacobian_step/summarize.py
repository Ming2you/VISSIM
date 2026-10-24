"""Report the terminal Jacobian calibration without refitting or new rollouts."""
import ast
import gzip
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
PARENT=HERE.parent
INTEGRATION=PARENT.parents[1]
ROOT=INTEGRATION.parents[2]
spec=importlib.util.spec_from_file_location('jacobian_replay',INTEGRATION/'replay_congested_component.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)


def main():
    from evaluation.controllers import lane_plant_runtime as lpr
    from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.boundary_factory import ObservationData
    status=h.load(HERE/'status.json');assert status['stage']=='complete_jacobian_step'
    protocol=h.load(HERE/'protocol.json');loss_protocol=h.load(PARENT/'protocol.json')
    for path,digest in protocol['core_pins'].items():assert h.sha(ROOT/path)==digest
    archived=HERE/'executed_helper.py.txt'
    assert h.sha(archived)==protocol['helper_sha256']
    def definitions(path):
        tree=ast.parse(path.read_text(encoding='utf-8'))
        return {n.name:ast.dump(n,include_attributes=False) for n in tree.body if isinstance(n,ast.FunctionDef)}
    old,new=definitions(archived),definitions(INTEGRATION/'replay_congested_component.py')
    assert all(old[name]==new[name] for name in ('_cellwise_measure','_cellwise_losses'))
    for path,digest in loss_protocol['truth_file_pins'].items():assert h.sha(path)==digest
    selection=h.load(HERE/'selection.json');train=h.load(HERE/selection['selected']/'result.json')
    model=lpr.load_sources(HERE/selection['selected']/'manifest.json')['component']
    catalog=h.load(PARENT/'data_catalog.json');records=[r for r in catalog['checked_records'] if r['role']=='check'];rows=[]
    for r in records:
        with gzip.open(HERE/'check43'/(r['arm']+'_prediction.json.gz'),'rt',encoding='utf-8') as f:prediction=json.load(f)
        rows.append(h._cellwise_measure(model,prediction,r,ObservationData(r['truth'])))
    check=h._cellwise_losses(rows,selection['relative_values'],loss_protocol)
    old=h.load(PARENT/'summary.json');prior=old['modes']['response'];base_train=old['baseline_train'];base_check=old['baseline_check']
    ti=1-train['loss']['response']/base_train['response'];ci=1-check['response']/base_check['response']
    guard=lambda a,b:a['mean_n_rmse']<=1.1*b['mean_n_rmse'] and a['mean_q_rmse']<=1.1*b['mean_q_rmse']
    gate=ti>=.2 and ci>=.2 and train['loss']['meaningful_signs_pass'] and check['meaningful_signs_pass'] and guard(train['loss'],base_train) and guard(check,base_check)
    files=list(HERE.glob('*/result.json'));results=[h.load(p) for p in files]
    assert len(results)==169
    valid=[r for r in results if r['invalid'] is None]
    invalid=[dict(name=r['name'],reason=r['invalid']) for r in results if r['invalid'] is not None]
    sensitivity=h.load(HERE/'sensitivity.json');variables=h.load(PARENT/'parameter_spec.json')['variables']
    norms=sensitivity['data_column_norm'];response=sensitivity['response_column_norm']
    insensitive=[dict(index=i,**r,data_column_norm=norms[i],response_column_norm=response[i]) for i,r in enumerate(variables) if norms[i]<1e-8]
    strongest=[dict(index=i,**variables[i],norm=response[i]) for i in sorted(range(159),key=lambda i:response[i],reverse=True)[:10]]
    output=dict(status=status,selected=selection['selected'],train=train['loss'],check=check,prior_train=prior['train'],prior_check=prior['check'],
        original_train=base_train,original_check=base_check,train_response_improvement=ti,check_response_improvement=ci,provisional_gate_passed=gate,
        max_mass_residual=max(r['conservation_max'] for x in valid for r in x['rows']),
        max_scalar_vector_difference=max(x['scalar_vector_objective_difference'] for x in valid),invalid_candidates=invalid,
        insensitive_variables=insensitive,strongest_response_columns=strongest,half_step_checks=sensitivity['half_step_checks'],
        core_unchanged=True,truth_pins_unchanged=True,production_adopted=False,gain_qualified=False,new_native=0)
    h.save(HERE/'summary.json',output)
    lines=['# 31셀 공동 보정: 직접 민감도 갱신 결과','',
        '이전159변수 동시 섭동 보정의 학습 최선에서 시작해, 모든 변수의 유한차분 민감도를 한 번 계산했다. 같은 손실을 그대로 유지했다. 큰 목적 기울기6개는 절반 간격에서도 확인하고, 계수 변화±5/15/30%의 세 갱신을 실제450초 예측으로 비교했다. 최종 후보는 학습값으로 고정한 뒤 seed43에 적용했다.','',
        f"총 **{status['new_training_rollouts']+status['new_check_rollouts']}개 450초 예측**. 새 VISSIM/push/production 변경 없음. 선택 후보 `{selection['selected']}`. 후보 이름은 계수 상대 변화 허용폭이며 교통 수요 변경이 아니다.",'',
        '| 방식 | 학습 상태 손실 | 학습 반응 손실 | seed43 반응 손실 |','|---|---:|---:|---:|',
        f"| 기존 모델 | {base_train['state']:.5f} | {base_train['response']:.5f} | {base_check['response']:.5f} |",
        f"| 이전 동시 섭동 보정 | {prior['train']['state']:.5f} | {prior['train']['response']:.5f} | {prior['check']['response']:.5f} |",
        f"| 직접 민감도 갱신 | {train['loss']['state']:.5f} | {train['loss']['response']:.5f} | {check['response']:.5f} |",'',
        f"기존 모델 대비 반응 오차 개선: 학습 {ti*100:+.1f}%, seed43 {ci*100:+.1f}%. 미리 정한 임시 기준 {'통과' if gate else '미통과'}. 낮은 손실이 좋으며, 기준 통과여도 전체 목표 달성을 뜻하지 않는다.",'',
        '| 상태 | 비교 | 실측 ΔTTT | 기존 | 이전 보정 | 직접 민감도 갱신 |','|---|---|---:|---:|---:|---:|']
    old_pairs=base_train['pairs']+base_check['pairs'];prior_pairs=prior['train']['pairs']+prior['check']['pairs']
    for r in train['loss']['pairs']+check['pairs']:
        key=(r['case'],r['arm']);b=next(x for x in old_pairs if (x['case'],x['arm'])==key);p=next(x for x in prior_pairs if (x['case'],x['arm'])==key)
        lines.append(f"| {r['case']} | {r['arm']} | {r['actual']['ttt']:+.3f} | {b['predicted']['ttt']:+.3f} | {p['predicted']['ttt']:+.3f} | {r['predicted']['ttt']:+.3f} |")
    lines+=['','단위 veh·h, 음수는 해당 NC/hold 기준 개선. 동측31셀+8connector 비용이며 Ω 전체가 아니다.','',
        '## 선형 근사와 실제 재생','',
        '| 상대 변화 허용폭 | 선형 예상 목적값 | 실제 재생 목적값 |','|---|---:|---:|']
    for r in h.load(HERE/'trials.json'):
        actual='수치 검사 실패' if r['actual_objective'] is None else f"{r['actual_objective']:.5f}"
        lines.append(f"| ±{r['radius']*100:.0f}% | {r['predicted_objective']:.5f} | {actual} |")
    lines+=['',f"데이터 Jacobian에서 최대 특잇값의1%보다 큰 방향은 {sensitivity['singular_above_one_percent_max']}/159개다. prior 행을 제외한 수치이며 통계적 식별성 증명이 아니다. 관측 손실에 국소적으로 반응하지 않은 변수는 {len(insensitive)}개다.",'',
        f"전체169개 평가 중 유효 {len(valid)}개, 실패 {len(invalid)}개. 유효 평가의 최대 램프/진출 보존 잔차 {output['max_mass_residual']:.3g}대, 스칼라 손실과 잔차 제곱합의 최대 차이 {output['max_scalar_vector_difference']:.3g}. 실패 후보는 제외하고 원인을 보존한다.",'',
        '새 기하나 capacity 보너스 없이 기존 FD/이완/anticipation/merge 계수를 공동으로 갱신한 결과다. 하나의 Jacobian과 세 실제 후보만 평가했으므로 전역 최적점·모든 계수의 식별 또는 셀별 보정의 불가능성을 증명하지 않는다.','',
        '처음 실행은 설치된 SciPy 접근 제한으로 rollout 전에 실패했다. 기존 설치 접근을 확인해 동일 코드로 실행했으며 first_import_failure.log에 보존했다. 기존 코어와 관측 파일 해시는 그대로다.','',
        '도시부·외부 대기를 포함한 전체Ω와 실제 SDMPC 선택·미분·native 검증은 별도로 남는다. 목표 ACTIVE / NOT_QUALIFIED.']
    (HERE/'RESULT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(dict(selected=selection['selected'],train_improvement=ti,check_improvement=ci,provisional_gate=gate,insensitive_variables=len(insensitive),half_step_max=max(r['relative_column_difference'] for r in sensitivity['half_step_checks']))))


if __name__=='__main__':main()
