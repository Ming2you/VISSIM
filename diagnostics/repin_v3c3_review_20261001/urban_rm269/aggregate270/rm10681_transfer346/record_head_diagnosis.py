"""Record the completed bounded RM head/merge diagnosis; no model adoption."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
A = HERE.parent
ROOT = HERE.parents[4]
R = Path('E:/VISSIM_analysis/20261010_rm10681_transfer346')
REPORT = R / 'head_merge_diagnosis.json'
j = json.loads(REPORT.read_bytes())
assert j['status'] == 'complete_conditional_diagnosis'
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest() == h for p, h in j['source_pins'].items())
assert abs(j['clock_merge_delta_5_minus_1']) < 1
prior = ROOT / 'diagnostics/repin_v3c3_review_20261001'
reviewed = [prior / p for p in (
    'upstream_worklog/03_codex_review/REVIEW.md',
    'upstream_worklog/02_urban_b2/diag_c3_r2/C3V2_PROPOSAL.md',
    'rm_flow218/README.md', 'rm_flow218/service_source_verification.json',
    'rm_restart219/receiving227/README.md', 'rm_restart219/heldout223/README.md')]
pins = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in reviewed}

note = '''

## 10681 신호 통과·합류 오차 분리와5초 시계 점검

완료346 예측의 head-service 기록을 다시 합산했다. 이전에는180대를 상한으로만 보고했지만 실제 예측 통과량도180대임을 확인했다. 신호 앞/뒤 저장과 합류 지연은 이미 존재한다. 이번에 새 항이나 보정계수를 추가하지 않았다.

|150초 구간|실측 head/merge|예측 head/merge|구간말 실측/예측 신호 뒤 재고|
|---|---:|---:|---:|
|4650–4800|22 / 20|30 / 28|2 / 2|
|4800–4950|52 / 41|60 / 57.46|13 / 4.54|
|4950–5100|64 / 50|90 / 86.49|27 / 8.05|

총 합류 과대60.951대 = head 통과 과대42대 + 신호 뒤 재고 과소18.951대다. 이는 정확한 차량수 수지의 분해이며 독립적인 두 원인의 크기를 확정한 것이 아니다. 하류가 너무 빨리 비면 head도 더 많이 통과하므로 두 항을 각각 맞춰 이중 감속시키지 않는다.

별도 FZP 스캔 없이 저장된 실제4개 decision frame을 확인했다. 신호 뒤 평균속도는4800초56.60→4950초11.99→5100초5.28km/h이고, 마지막27대 중22대가2차로에 있다. 모형의147m 신호 뒤 구간은39.38km/h를 기본으로 사용하고, 본선 수용 예산은 두 램프 차로에 동일하게 나눈다. 이 차이가 어느 정도의 인과 오차인지는 아직 독립적으로 증명되지 않았다.

저장된 모델의 수용 예산·차로별 유입 요청을 고정한 국소 시계 비교2회를 수행했다.1초는 head180/merge172.733,5초는 head180/merge171.951대다. 차이는−0.782대여서 이 조건의61대 오차를5초 집계 때문에 생겼다고 볼 근거가 없다. 모든 램프 차로·스텝의 차량 보존을 확인했다. 상류 피드백을 다시 계산하지 않는 조건부 수치 점검이며 전체망 예측이나 성능 검증을 대신하지 않는다. 국소 재생에서 미수용 요청은 외부 backlog로 보존했다(1초2.582대,5초0.909대). 미래 실측 frame은 점검용으로만 사용했고 재생 입력으로 쓰지 않았다.

Claude의 head 서비스/시동 손실 및 차로 비대칭 기록, 기존218·223·227을 먼저 검토했다.218은 상위 measured_table과 실제 manifest의 선형 head 표가 다르다는 점을 이미 확인했다. 이번에도 임의로 다른 표로 교체하지 않았다.227에서는 연결 차로 통과량만 반영한 gap 확대가 과다 배수를 일으켜 기각됐다. 따라서 그 실패한 수정을 반복하지 않는다.

이번 진행은 저장 결과의 원인 범위 축소다. 새 전체예측0, AD0, 최적화0, VISSIM0, 적합0, 생산코드 변경0, push0. 이 진단에서는5초를 유지하며 작은 전체ΔTTT +0.407대·시간을 맞추는 추가 탐색을 하지 않는다. 본선 손해/램프·도시 대기 완화의 큰 방향은 이미 확인했지만,10681 방출 크기와 실제 실행가능한 제어 선택, 정본 집계 설치 연결, 큰 도시신호 손익 오차와 동일예산 wall 검증은 여전히 남는다.

정본: E:/VISSIM_analysis/20261010_rm10681_transfer346/head_merge_diagnosis.json
재현: diagnose_head_merge.py. 전체 목표 ACTIVE·미완료, 실행 중인 작업 없음.
'''

def atomic(path, text):
    temporary = path.with_name(path.name + '.head_diagnosis.tmp')
    assert not temporary.exists()
    temporary.write_text(text, encoding='utf8')
    temporary.replace(path)

for p in (HERE / 'README.md', R / 'README.md'):
    old = p.read_text(encoding='utf8')
    assert '## 10681 신호 통과·합류 오차 분리와5초 시계 점검' not in old
    atomic(p, old + note)

now = datetime.now(timezone.utc).isoformat()
next_step = (
    'Head/merge diagnosis complete:42 extra head crossings and18.951 fewer post-head vehicles account for60.951 extra merges; '
    'this is an accounting identity, not independent causal attribution. Conditional1s-vs5s replay differs by0.782 merge vehicles. '
    'Retain5s; do not fit the tiny4650 net sign or repeat rejected227 lane-gap pooling. '
    'Consolidate frozen331/current339 initialization and rollout hooks into the canonical aggregate path with explicit fixed calibration/current-state separation, '
    'then validate feasible SDMPC choice and matched-budget wall. The material city-control gain error and10681 discharge magnitude remain open. '
    'No automatic full native run, optimizer repetition, grid or push.')
record = dict(status='complete_conditional_head_merge_diagnosis', evidence=str(REPORT),
    evidence_sha256=hashlib.sha256(REPORT.read_bytes()).hexdigest(), reviewed_source_pins=pins,
    numerical_replays=2, new_full_forecasts=0, native_runs=0, fits=0, production_changes=0,
    accounting_identity=j['exact_error_identity'], clock_merge_delta=j['clock_merge_delta_5_minus_1'],
    goal_turn_classification='progress', goal_complete=False, updated_utc=now)
for p in (A / 'plan.json', A.parent / 'plan.json'):
    data = json.loads(p.read_bytes())
    data.update(current_stage='rm10681_head_merge_diagnosis_complete_canonical_integration_pending',
        current_workers=[], latest_evidence=str(REPORT), next_step=next_step,
        goal_complete=False, updated_utc=now, rm10681_head_merge346=record)
    atomic(p, json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
atomic(R / 'head_merge_completion.json', json.dumps(record, ensure_ascii=False, indent=2) + '\n')
print('Recorded bounded diagnosis; goal remains active and incomplete.')
