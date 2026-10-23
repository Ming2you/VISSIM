"""Summarize completed predictions; no fit, forecast, native scan or launch."""
import datetime, hashlib, json, math
from pathlib import Path

A = Path(__file__).resolve().parent
H = A.parent
O = A / 'refine15_joint_fit'
pins = {}
def read(path):
    data = path.read_bytes()
    pins[str(path)] = hashlib.sha256(data).hexdigest()
    return json.loads(data)
def save(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf8')
def rmse(values):
    return math.sqrt(sum(x*x for x in values)/len(values))

assert not (O/'decision.json').exists()
r = read(O/'assessment.json')
s = read(O/'selection.json')
done = read(O/'completion.json')
truth = read(O/'training_truth.json')
valid = read(O/'validation_truth.json')
length = read(A/'refine15_update_audit.json')['subcell_length_m']/1000
names = ['14', '15a', '15b', '15c', '16', '17', '18']
train_rows = [row for rows in truth.values() for row in rows]
def coverage(rows):
    speeds = [row['speed'][j] for row in rows for j in (1,2,3)]
    density = [row['n'][j]/(4*length) for row in rows for j in (1,2,3)]
    return dict(samples=len(speeds), speed_range_kmh=[min(speeds),max(speeds)],
                density_range_veh_km_lane=[min(density),max(density)], speed_below60=sum(v<60 for v in speeds))
train_errors = []
for j,name in enumerate(names):
    row = dict(cell=name)
    for label in ('baseline','fitted'):
        errors = {key:[] for key in ('n','speed')}
        for at in (1200,1650):
            pred = read(O/f'{label}_{at}.json')['frames']
            for p,q in zip(pred,truth[str(at)]):
                for key in errors: errors[key].append(p[key][j]-q[key][j])
        row[label] = {key:dict(rmse=rmse(vals),bias=sum(vals)/len(vals)) for key,vals in errors.items()}
    train_errors.append(row)
diag = dict(training_objective_endpoint_coverage=coverage(train_rows),
            validation_hold_endpoint_coverage=coverage(valid),
            train_cell_errors=train_errors,
            data_jacobian_condition=s['data_jacobian_singular_values'][0]/s['data_jacobian_singular_values'][-1],
            interpretation='The fitted cell15 objective targets cover no speed below60km/h. Validation does. This is a measured coverage limitation, not proof of the sole cause. The loss endpoint range is not the range of every intermediate training state.',
            source_pins=dict(pins))
save(O/'coverage_diagnostics.json',diag)
now = datetime.datetime.now(datetime.timezone.utc).isoformat()
save(O/'execution_closure.json',dict(verified_utc=now,exec_session=60058,tool_observed_exit_code=0,
     completion=str(O/'completion.json'),forecasts=done['forecasts'],new_native=0,
     note='Terminal tool returned normal process completion; no process was terminated.'))
next_step = ('Reuse the completed16 forecasts and frozen fit. Before another fit, inventory existing completed110 baseline observations for congested cell15/neighbor coverage and define a finite trajectory-calibration protocol with disjoint calibration and evaluation cases. Do not reuse the already inspected2250 validation as an untouched test or optimize its VSL-response sign. Check existing independent seed67/71 provenance and reserve evaluation cases before selecting data. No new native, coefficient grid or repeated current forecasts. Spatial refinement remains unresolved; this single nonconverged update is not a rejection of calibrated refinement. Automation PAUSED, goal ACTIVE/incomplete.')
decision = dict(status=r['status'],updated_utc=now,app_goal_status='active',goal_complete=False,
    current_goal_turn_classification='progress:one bounded five-parameter trajectory update,16 completed coupled forecasts, frozen holdout comparison and coverage diagnosis',
    new_forecasts=16,new_fits=1,new_native=0,new_optimizer_runs=0,new_fzp_scans=0,
    production_edits=0,candidate_adopted=False,remaining_native_budget=0,automation_status='PAUSED',
    fit_converged=False,spatial_model_class_rejected=False,train_loss_relative_reduction=1-s['fitted']['data_loss']/s['baseline']['data_loss'],
    next=next_step,evidence={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [O/'assessment.json',O/'coverage_diagnostics.json',O/'selection.json',O/'completion.json',O/'execution_closure.json']})
save(O/'decision.json',decision)
report = '''# 공간 세분화 후 FD·동역학 공동 보정 1단계

기존 계수를 그대로 옮긴 시험만으로 공간 분할 모델을 기각한 판정은 정정했다. 이번에는 임계밀도·FD 형상·완화시간·밀도차 반응 2계수를 함께 보정했다. 자유속도, 나머지 셀, 수요, VSL 법칙, 도시·램프 동역학과 제어 목적은 고정했다. 생산 채택은 아직 하지 않았다.

1200–1650초와1650–2100초의 실제110 명령·도시/RM 계획으로 전체 결합 모델의450초 재고·속도 궤적을 사용했다. 관측된 미래 경계 상태를 주입하지 않았다. 기준2회,5개 미분 근사×2회,갱신2회,검증2회로 총16예측,제한된 Gauss–Newton 갱신1회다. 계수 격자/새native/전체SDMPC 선택은0회다. 수렴된 보정해가 아니며 계수는2250 검증 전에 고정했다.

| 항목 | 보정 전 | 보정 후 |
|---|---:|---:|
| 보정 구간 속도 RMSE [km/h] | 15.9562 | 13.4811 |
| 보정 구간 차량 수 RMSE [대] | 5.5078 | 5.3206 |
| 별도110 검증 속도 RMSE [km/h] | 21.2655 | 22.2667 |
| 별도110 검증 차량 수 RMSE [대] | 8.6170 | 8.6788 |
| 450초 두 구역90 통과량 변화 [대] | −28.8796 | −29.4410 |
| 450초 두 구역90 접근부 재고 변화 [대] | +26.3844 | +27.3005 |
| 450초 두 구역90 전체Ω TTT 변화 [대·시간] | +1.10949 | +1.06881 |

마지막 세 행은90−110이며, 실제는 각각+31대/−30대/−0.04583대·시간이다. 통과량은18번 셀 하류 단면 기준이며450초 첫1m 재고 보정은0대다. 종료 잔여를 유출로 세지 않았다. 실제 전체TTT 차이는 매우 작아 부호를 강제로 맞추지 않는다. 보정 구간 손실은21.54% 줄었지만 별도 반응은 나아지지 않았다. 차량·목적지·VSL 이력 보존은1e−12 수준 이내이며 AD/NP/NUF와 독립시드 검증은 아직 수행하지 않았다.

보정 손실에 들어간15번 셀의 세 구간 속도 표본18개는80.28–112.49km/h, 밀도7.13–28.50대/(차로·km)였다. 별도 검증9개에는36.41km/h와45.60대/(차로·km)가 나타난다. 이는 정체 구간의 보정 자료가 부족하다는 구체적인 한계이며, 모든 중간 상태가 비혼잡이었다거나 이것만이 오차 원인이라는 뜻은 아니다. 다섯 계수의 데이터 Jacobian 조건수는약243으로 민감도 차이가 크다. 계수는 경계에 걸리지 않았지만 이것만으로 식별 완료라고 볼 수 없다.

다음은 기존 완료된110 자료에서 정체 상태의 범위를 확인하고, 보정·평가 사례를 먼저 분리하는 것이다. 이미 본2250 결과를 다시 학습하고 독립 검증이라고 부르지 않는다. 이 후보는 채택하지 않지만 보정된 공간 분할 모델 자체는 기각하지 않는다. 목표 ACTIVE·미완료, 유한 자동확인 PAUSED, 추가native 예산0을 유지한다.
'''
(O/'README.md').write_text(report,encoding='utf8')
meta = dict(status=r['status'],decision=str(O/'decision.json'),report=str(O/'README.md'),
            new_forecasts=16,new_fits=1,new_native=0,candidate_adopted=False,goal_complete=False)
for path in (H/'plan.json',H/'summary.json'):
    doc=json.loads(path.read_text(encoding='utf8'))
    doc['refinement_joint_fit_20261019']=meta
    doc['next']=next_step;doc['updated_utc']=now
    save(path,doc)
with (H/'README.md').open('a',encoding='utf8') as f:
    f.write('\n\n## 2026-10-19 공간 세분화의 공동 계수 보정 1단계\n\nFD·동역학5계수의 제한된 궤적 갱신1회와16예측을 완료했다. 보정 구간 속도 RMSE15.96→13.48km/h, 차량 수5.51→5.32대로 줄었으나 별도450초 통과량 반응은−28.88→−29.44대로 실제+31대와 불일치한다. 보정 목표 표본에는 저속 정체가 부족하다. 이 비수렴 후보는 채택하지 않으며 보정된 공간 모델 자체를 기각하지 않는다. 최신 다음단계와 근거는[공동 보정 보고서](outflow_followup_20261019/refine15_joint_fit/README.md),정본인계는같은폴더decision.json이다. 기존자료/완료예측재사용,새native0,목표ACTIVE·미완료.\n')
print(json.dumps(dict(status=decision['status'],coverage=diag['training_objective_endpoint_coverage'],validation=diag['validation_hold_endpoint_coverage'],condition=diag['data_jacobian_condition']),ensure_ascii=False,indent=2))
