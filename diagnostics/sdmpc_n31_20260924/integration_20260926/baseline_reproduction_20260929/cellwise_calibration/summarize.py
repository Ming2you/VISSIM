"""Summarize two terminal, frozen fits. No optimization or plant rollout."""
import ast
import gzip
import importlib.util
import itertools
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
INTEGRATION=HERE.parents[1]
ROOT=INTEGRATION.parents[2]
spec=importlib.util.spec_from_file_location('joint_replay',INTEGRATION/'replay_congested_component.py')
helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)


def main():
    from evaluation.controllers import lane_plant_runtime as lpr
    from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.boundary_factory import ObservationData
    protocol=helper.load(HERE/'protocol.json');parameters=helper.load(HERE/'parameter_spec.json')
    for name,digest in protocol['core_pins'].items():assert helper.sha(ROOT/name)==digest
    archived=HERE/'helper_before_fit.py.txt'
    assert helper.sha(archived)==protocol['helper_sha256']
    def definitions(path):
        tree=ast.parse(path.read_text(encoding='utf-8'))
        return {n.name:ast.dump(n,include_attributes=False) for n in tree.body if isinstance(n,ast.FunctionDef)}
    old,new=definitions(archived),definitions(INTEGRATION/'replay_congested_component.py')
    assert all(old[name]==new[name] for name in ('_cellwise_measure','_cellwise_losses'))
    for path,digest in protocol['truth_file_pins'].items():assert helper.sha(path)==digest
    statuses={mode:helper.load(HERE/mode/'status.json') for mode in ('state','response')}
    assert all(s['stage']=='complete_frozen_check' for s in statuses.values()),statuses
    context=lpr.load_sources(parameters['initial_manifest']);model=context['component']
    catalog=helper.load(HERE/'data_catalog.json');checks=[r for r in catalog['checked_records'] if r['role']=='check']
    observations={r['arm']:ObservationData(r['truth']) for r in checks}
    def check_rows(folder):
        rows=[]
        for record in checks:
            with gzip.open(folder/(record['arm']+'_prediction.json.gz'),'rt',encoding='utf-8') as f:prediction=json.load(f)
            rows.append(helper._cellwise_measure(model,prediction,record,observations[record['arm']]))
        return rows
    def ranking(rows):
        result=[]
        for case in sorted({r['case'] for r in rows}):
            group=[r for r in rows if r['case']==case]
            for a,b in itertools.combinations(group,2):
                actual=b['actual']['ttt']-a['actual']['ttt'];pred=b['predicted']['ttt']-a['predicted']['ttt']
                result.append(dict(case=case,a=a['arm'],b=b['arm'],actual_delta=actual,predicted_delta=pred,
                    meaningful=abs(actual)>=protocol['meaningful_delta_veh_h'],correct=pred*actual>0))
        return result
    baseline_train=helper.load(HERE/'state/eval_000/result.json')
    baseline_check_rows=check_rows(HERE.parent/'component2220_s43_current_v2')
    baseline_check=helper._cellwise_losses(baseline_check_rows,[0.]*159,protocol)
    summary=dict(baseline_train=baseline_train['loss'],baseline_check=baseline_check,modes={},
        scope='East31 cells +8 connectors; not full Omega',production_adopted=False,gain_qualified=False,new_native=0)
    comparisons=[];coefficient_rows=[]
    for mode,status in statuses.items():
        selection=helper.load(HERE/mode/'selection.json');train=helper.load(HERE/mode/f"eval_{selection['best_index']:03d}"/'result.json')
        check=check_rows(HERE/mode/'check43');check_loss=helper._cellwise_losses(check,train['relative_values'],protocol)
        ti=1-train['loss']['response']/baseline_train['loss']['response'];ci=1-check_loss['response']/baseline_check['response']
        guard=lambda candidate,base:candidate['mean_n_rmse']<=1.1*base['mean_n_rmse'] and candidate['mean_q_rmse']<=1.1*base['mean_q_rmse']
        passed=ti>=.2 and ci>=.2 and train['loss']['meaningful_signs_pass'] and check_loss['meaningful_signs_pass'] and guard(train['loss'],baseline_train['loss']) and guard(check_loss,baseline_check)
        entry=dict(status=status,train=train['loss'],check=check_loss,train_response_improvement=ti,check_response_improvement=ci,
            provisional_gate_passed=passed,train_ranking=ranking(train['rows']),check_ranking=ranking(check),
            max_port_ramp_mass_residual=max(r['conservation_max'] for r in train['rows']+check),
            manifest=str(HERE/mode/f"eval_{selection['best_index']:03d}"/'manifest.json'))
        summary['modes'][mode]=entry
        for row in train['loss']['pairs']+check_loss['pairs']:
            comparisons.append(dict(mode=mode,case=row['case'],arm=row['arm'],actual_delta=row['actual']['ttt'],predicted_delta=row['predicted']['ttt']))
        for row,value in zip(parameters['variables'],selection['values']):
            coefficient_rows.append(dict(mode=mode,**row,selected=value,relative_change=value/row['initial']-1))
    summary['comparison']=comparisons
    summary['rollouts']=sum(s['training_rollouts']+s['check_rollouts'] for s in statuses.values())
    helper.save(HERE/'summary.json',summary);helper.save(HERE/'selected_coefficients.json',coefficient_rows)
    helper.save(HERE/'verification.json',dict(core_unchanged=True,archived_helper_matches_executed_pin=True,summary_functions_unchanged=True,all_truth_pins_unchanged=True,
        default_regressions={m:helper.load(HERE/m/'identity_verification.json') for m in statuses},
        no_future_truth_prediction_inputs=True,check_not_used_for_coefficient_selection=True,production_adopted=False))
    helper.save(HERE/'status.json',dict(stage='complete_bounded_joint_calibration',fit_completed=True,free_parameters=159,
        new_rollouts=summary['rollouts'],new_native=0,production_adopted=False,gain_qualified=False,
        mode_statuses=statuses,provisional_passes=[m for m,e in summary['modes'].items() if e['provisional_gate_passed']]))
    lines=['# 31셀 공동 보정 결과','',
        '같은 정본망·공통 초기 상태·실제 명령의 450초 재생으로 159개 독립 계수를 보정했다. 상태 오차만 학습하는 경우와 제어 반응까지 학습하는 경우를 같은 시작점·탐색 방향·최대 예산으로 비교했다. 물리 방정식은 변경하지 않았다.', '',
        f"총 **{summary['rollouts']}개 450초 예측**, 새 VISSIM·push 없음. 아래 비용은 **동측31셀+동측connector8개**이며 Ω 전체가 아니다.",'',
        '| 보정 방식 | 상태 손실 변화(학습) | 제어 반응 오차 개선(학습) | 제어 반응 오차 개선(seed43) | 임시 기준 |',
        '|---|---:|---:|---:|---|']
    for mode,e in summary['modes'].items():
        si=1-e['train']['state']/baseline_train['loss']['state']
        lines.append(f"| {mode} | {si*100:+.1f}% | {e['train_response_improvement']*100:+.1f}% | {e['check_response_improvement']*100:+.1f}% | {'통과' if e['provisional_gate_passed'] else '미통과'} |")
    lines+=['','상태/반응 오차 개선은 양수가 감소를 뜻한다. 제어 반응 오차는 ΔTTT·램프대기 차이·누적 유출 차이·램프별 합류 차이를 묶은 학습 지표다.','',
        '| 초기 상태 | 제어 비교 | 실측 ΔTTT | 기존 | 상태 보정 | 반응 포함 보정 |','|---|---|---:|---:|---:|---:|']
    base_pairs=baseline_train['loss']['pairs']+baseline_check['pairs']
    for r in base_pairs:
        vals=[next(x['predicted_delta'] for x in comparisons if x['mode']==m and x['case']==r['case'] and x['arm']==r['arm']) for m in statuses]
        lines.append(f"| {r['case']} | {r['arm']} | {r['actual']['ttt']:+.3f} | {r['predicted']['ttt']:+.3f} | {vals[0]:+.3f} | {vals[1]:+.3f} |")
    lines+=['','단위 veh·h. 음수는 기준 NC/hold 대비 개선. 각 비교군 내부의 초기 상태와 제어 전 이력은 동일하다.','',
        '## 채택과 해석','',
        '159개를 자유롭게 허용했지만, 이번 예산으로 모두 식별했거나 전역 최적점에 도달했다고 주장할 수 없다. 두 학습 초기 상태와 상관된8개 궤적이며, seed43도 과거에 열람한 확인 자료다. 실제 미사용 상태/seed와 full Ω·SDMPC 선택·미분·실행 검증은 별도로 남는다.', '',
        '관측된 하류 고밀도 분기가 드문 셀0·12·24 등의 계수는 특히 식별 근거가 약하다. prior 정규화는 불필요한 이동을 억제하지만 식별성 증명은 아니다. 계수별 값은 selected_coefficients.json에 보존했다.', '',
        '새 계수를 production에 채택하지 않았다. 동적 off-ramp 저장·배수·spillback, 실제 합류량과 램프 대기, VSL 이력 및 내부1초 적분은 유지했다. 외부 대기와 도시부까지 포함한 순이득을 이 구성요소 결과만으로 주장하지 않는다.', '',
        '각 실행의 조기 종료/갱신 수, 모든 후보·손실·설정 해시는 state/와 response/에 남겼다. 체크 결과에 맞춰 추가 계수를 선택하지 않았다. 임시 기준 미통과를 METANET의 모든 셀별 보정이 불가능하다는 증거로 해석하지 않는다.']
    (HERE/'RESULT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(dict(rollouts=summary['rollouts'],modes={m:dict(train_improvement=e['train_response_improvement'],check_improvement=e['check_response_improvement'],passed=e['provisional_gate_passed']) for m,e in summary['modes'].items()})))


if __name__=='__main__':main()
