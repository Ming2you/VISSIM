"""Finalize already-completed 162--164; verify stored evidence, run no model."""
import hashlib
import json
from pathlib import Path

R = Path(__file__).resolve().parent.parent


def read(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def write(p, text):
    assert not p.exists(), p
    p.write_text(text, encoding='utf-8')


def main():
    # Verifiers pinned the executed helper rather than subsequently edited code.
    for name in ('joint_pressure163', 'merge_restore164'):
        folder = R / name
        pins = read(folder / 'verification_pins.json')
        for path, digest in pins.items():
            assert sha(Path(path)) == digest, path
        assessment = read(folder / 'assessment.json')
        assert assessment['status'] == 'complete_rejected'
        assert not assessment['production_adopted'] and not assessment['goal_complete']
        assert assessment['half_checks'] == 21600
        assert assessment['feedback_checks'] == 3600
        assert assessment['forecasts'] == 9 and assessment['new_fits'] == 0

    p162 = R / 'neighbor_split162'
    v162 = read(p162 / 'verification.json')
    assert v162['probes'] == 632 and v162['canonical_calls'] == 3160
    assert v162['parity160_error'] == 0
    for path, digest in v162['input_sha256'].items():
        assert sha(Path(path)) == digest, path
    protocol = read(p162 / 'protocol.json')
    for path, digest in protocol['protected_sha256'].items():
        assert sha(Path(path)) == digest, path
    assert sha(Path(protocol['STOP']['path'])) == protocol['STOP']['sha256']
    write(p162 / 'README.md', '''# 셀21의 상류 속도·하류 밀도 오차 분리

2026-10-04. 완료된160 자료를 재사용한 조건부 진단이다. 새 전체 예측·보정·VISSIM·FZP 읽기·push는0이다.

셀21의 현재 실측 N/v와 관측된 다음5초 합류량을 고정하고, 상류20 속도와 하류22 밀도를 각각 실측/저장된 예측으로 바꿨다. 매 표본5개의 정본1초 속도 갱신을 사용했다. 두 입력을 모두 실측 또는 모두 예측으로 둔 결과는160과 오차0이다. 632개 조건부 표본·3160호출을 검산했다.

2820.1–2970.1초의 셀21·1차로 실제 평균 변화율은−0.470km/h/s다.158 계수에서 두 이웃을 모델 상태로 두면−3.949, 상류 속도만 실측으로 바꾸면−1.918, 하류 밀도만 바꾸면−2.235, 둘 다 실측이면+0.062였다.148에서도 두 이웃이 모두 영향을 준다. 단일 이웃만 고쳐 해결됐다고 할 수 없다.

이는 미래 실측을 포함한 원인 분리이며 자율 예측이 아니다. 고정 밀도로 속도만 갱신한 혼합 상태는 차량 보존 궤적이나 실제 인과 기여율이 아니다. 평균 반응이 가까워도158 양쪽 실측 조건의5초 끝 속도 RMSE는18.53km/h였다. 미래 실측을 운용 입력에 넣지 않았다.

후속163은 새 격자 보정 없이 이미 추정된20·22 계수를 함께 검증했다. 결과는 해당 폴더에 별도 보존했다. 정본9파일·원 입력·STOP 유지. 전체 목표 ACTIVE / NOT_QUALIFIED.
''')

    for number, name, change, interpretation in (
        (163, 'joint_pressure163',
         '161의 다른 모든 설정과157 물리식을 유지하고, 셀22 nu_ge만20.1309219876에서 이미137에서 추정한3.7711325048040054로 변경했다. 새 fitting은 없다.',
         '재정체 구간의 셀20 진출량이46.36대로 실측29대를 넘었다. 두 제어 조건을 모두 너무 쉽게 풀어 RM 완화의 실제 손해까지 이득으로 뒤집었다. 절대 오차 개선으로 채택하지 않는다.'),
        (164, 'merge_restore164',
         '163의 다른 설정과 물리식을 그대로 두고, 조건부 보정에서0이 된 셀21 delta_merge를 기존132의3.2554915742700765로 복원했다. 실제 허용 합류량이 기존 감속항에 들어가며 새 수요·용량 보너스나 fitting은 없다.',
         'RM 완화 손해의 부호는 돌아왔지만 VSL 이득 부호는 틀렸다. 셀20 진출이 가운데150초45.55대(실측29), 마지막150초19.52대(실측45)로 혼잡과 회복 시점도 빗나갔다. 합류 감속이 필요하다는 단서이며 이 계수만 조절하면 해결된다는 증거가 아니다.'),
    ):
        folder = R / name
        a = read(folder / 'assessment.json')
        s = read(folder / 'forecast/status.json')
        pairs = [x for x in a['pairs'] if x['case'] == 's67_late']
        table = '\n'.join(
            f"|{x['left']} → {x['right']}|{x['actual']['ttt']:+.4f}|{x['predicted']['ttt']:+.4f}|"
            for x in pairs
        )
        write(folder / 'README.md', f'''# REVIEW{number} — 동결 계수의 결합 검증, 기각

2026-10-04. 기준 재현1회와8조건 자율450초 예측을 완료했다. 전부 정상 종료했지만 손익 관문을 통과하지 못했다. **미채택, 전체 목표 ACTIVE / NOT_QUALIFIED.**

{change}

seed29·67 후기의 RM 유지/완화 × VSL110/90을 기존 초기 상태·예측 입력으로 계산했다. 두 상태는 이미 검토한 자료이며 독립 검증이라고 부르지 않는다. 미래 실측 입력을 제공하지 않았다.

|seed67 명령 차이|실측 ΔTTT|예측 ΔTTT|
|---|---:|---:|
{table}

단위는veh·h, 오른쪽−왼쪽이다. 평가 영역은 동측31셀+진입4·진출4 커넥터이며 **전체 Ω·도시부 대기 검증이 아니다.** 부호를 맞추지 못해 다음 독립/전체망/SDMPC 관문으로 진행하지 않았다.

{interpretation}

기존 가중 점수는 절대오차 {a['scores']['baseline']['absolute']:.6f}→{a['scores']['candidate']['absolute']:.6f}, 명령쌍 반응오차 {a['scores']['baseline']['response']:.6f}→{a['scores']['candidate']['response']:.6f}다. 속도 RMSE나 TTT 개선률이 아니다.

다른 helper23함수 AST, 물리식, 다른 계수·FD를 검사했다. 기준4개 출력표 정확 일치,21600개 반셀 검사,3600개 진출 피드백 검사, 차량/목적지/램프 수지, 정본9파일·입력·STOP 보존을 확인했다. 실행 소스 사본과 실패 결과를 유지했다. 계산 {s['elapsed_sec']:.3f}초는9번 예측 시간이며 SDMPC 최적화 반복 시간이 아니다.

이번 기각은 모든 재보정의 한계라는 뜻이 아니다. 같은 계수 격자나 임의 조합을 더 반복하지 않고, 속도 전달·상태 갱신의 추가 근거를 먼저 확인한다. 새 VISSIM·FZP 읽기·9000 결과 분석·push는0이다. 근거: proposal/preflight, forecast/status/parity/preservation/training_assessment, assessment, verification_pins 및 실행 소스 사본.
''')

    for name in ('neighbor_split162', 'joint_pressure163', 'merge_restore164'):
        folder = R / name
        completion = dict(status='complete_conditional_only' if '162' in name else 'complete_rejected',
                          production_adopted=False, goal='ACTIVE_NOT_QUALIFIED',
                          previous_goal_turn='NO_PROGRESS: explanation of existing131/150 only',
                          this_turn='PROGRESS: existing162--164 completed results verified and reports finalized',
                          native=0, FZP=0, new_9000_analysis=0, push=0,
                          report_sha256=sha(folder/'README.md'))
        write(folder/'completion.json', json.dumps(completion, ensure_ascii=False, indent=2)+'\n')
    print('162/163/164 evidence rechecked; reports completed; no model execution')


if __name__ == '__main__':
    main()
