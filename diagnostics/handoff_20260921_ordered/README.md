# 모델 수정·속도 반응 진단 인계

`codex/control-full-review-20260909`의 `a5dcbd3` 이후 증분이다. 누적 plant 변경은 이전 커밋에 포함되어 있으며, 이번에는 기존 추종 helper의 선택적 상대속도 반응식과 완료된 오차 분해·차로 관측을 전달한다. **RM/VSL 순이득 보정은 여전히 NOT_QUALIFIED다. 실패 후보를 정본으로 채택하지 않았다.**

## 포함한 변경과 확인 결과

- `downstream_restart.py`: 기존 함수에 선택적 IDM 종방향 반응을 추가했다. 차량별 상대속도·간격을 사용하며 native 희망 가감속·CC0/CC1을 초기 파라미터로 가져온다. 이것은 Wiedemann과의 동등성을 입증한 변환이 아니다. 기본 `interaction=None`의 계산과 파라미터 반환은 이전과 정확히 같다. 과도한 감속이나 초기 차량 겹침을 위치 보정으로 숨기지 않고 실패로 남긴다.
- 속도 오차 장부: 360개 현재 상태의 1초 검사에서 29,354개 구간·차로 행과 2,160개 셀 행을 검사했다. NC2550초의 문제16셀 평균 오차 +4.148km/h는 차량 혼합 +0.302, 같은 차량 반응 +3.713, 재고 가중치 +0.133으로 나뉜다. 내부 정지·저속 선행 차량이 있어도 평균밀도 차이로 과도한 가속을 만드는 사례를 확인했다. 전체450초 오차의 기여율을 입증한 것은 아니다.
- 상대속도 후보: 완료20개30초 궤적과 초기 겹침으로 제외된4개 모드·차로 기록을 보존했다. 공통 표본30초 속도 RMSE는19.588→18.116km/h로 줄지만5초는10.980→11.569로 늘고 핵심2550초 구간도 나쁘다. native 감속 한계 초과도 남아 **기각**했다. 비교 대상은 기존 gap helper이며 정본 METANET 전체가 아니다.
- 차로 관측: NC 네 시점의164개 프레임에서 현재 PosLat·목적 차로·차폭을 복원했다. 네30초 창의80개 종방향 투영 겹침 중 측방 기준 단면이 분리되는 것은4개뿐이다. 측방 위치 보정만으로 대부분을 설명하지 못한다. 차체 방향·앞뒤2D좌표가 없으므로 실제 충돌이나 차로 폐쇄를 판정한 자료는 아니다. 복수 차로 점유는 공간 노출이며 차량 재고를 중복 계산하지 않는다.

`K = diagnostics/demand_sweep/ramp_dsd_20260916_v2/cohort_dynamics_20260920`.
세부 근거는 [속도 오차 장부](../demand_sweep/ramp_dsd_20260916_v2/cohort_dynamics_20260920/VELOCITY_MIXING_AND_REACTION_LEDGER.md), [상대속도 후보 판정](../demand_sweep/ramp_dsd_20260916_v2/cohort_dynamics_20260920/ORDERED_RELATIVE_RESPONSE_GATE.md), `K/lateral_body_observation_v1/result.json`에 있다. 과거 보고서의 ‘로컬·푸시 미포함’은 작성 당시 상태다.

## 유지한 조건과 미완료 사항

사용자 가속거리 수정 + 램프 DSD120 + 동측 본선 입력1098만0.8배 조건을 유지했다. 이번 증분에서 정본 core4파일·네트워크·수요·실행 설정은 바꾸지 않았다. 새 VISSIM 런이나 다른 프로세스 개입도 없다. 추가 작업은 국소 동역학 진단이며 전체 Ω·새 기하의 full GNE·미사용 seed 검증을 통과한 결과가 아니다.

**후속 확인할 단서:** 기준 `H/source_dsd/baseline.inpx`와 완료 NC 관측 런의 prepared manifest에 `simRes="1"`이 저장되어 있다. 1초 FZP 출력 간격과 내부 계산 해상도를 구분해야 한다. 현재 투영 겹침·차량 순서 변화에 이 설정이 기여하는지는 검증하지 않았다. runtime 실제값과 좌표·시각 규약을 먼저 확인하고, 필요할 때만 별도 복사 조건에서 짧은 해상도 진단을 한다. 기준 망의 SimRes를 조용히 바꾸거나 이것을 원인으로 단정하지 않는다.

다음은 현재·과거 좌표에서 순서/간격과 native target의 시차를 확인하고, 실제 차체 기하와 수치 진행 문제를 구분하는 것이다. 그 뒤 최소 자율 상태 갱신을 다시 검사한다. 실패한 IDM 계수·평균밀도·기억 가중치 sweep을 반복하지 않는다. 최종적으로 동일 초기 상태의 RM/VSL/동시 구성 비용·순이득·선택 순위와 무제어 보호를 통과해야 한다. seed13/23/33/43은 이미 개발에 사용했다.

## 다른 컴퓨터에서 복원

이전 README 순서대로 `handoff_20260916`부터 `handoff_20260921_acceleration`까지 복원한 뒤 저장소 루트에서 실행한다.

```powershell
python -B -X utf8 diagnostics/handoff_20260916/restore_evidence.py --package diagnostics/handoff_20260921_ordered --restore --verify
python -B -X utf8 diagnostics/demand_sweep/ramp_dsd_20260916_v2/cohort_dynamics_20260920/verify_velocity_ledger.py
python -B -X utf8 diagnostics/demand_sweep/ramp_dsd_20260916_v2/cohort_dynamics_20260920/verify_ordered_relative_response.py
python -B -X utf8 diagnostics/handoff_20260921_ordered/verify_records.py
```

검사는 저장 기록을 사용한다. ordered 검사는 작은1초 함수 계약도 계산하지만 VISSIM이나 전체 예측을 다시 실행하지 않는다. 과거 실험의 `downstream_restart.py` 해시는 `K/ordered_relative_response_v1/source_before.py`로 확인하며 이전 pin을 새 코드로 대체하지 않는다.

`direct_files.json`은 직접 전달 파일, `evidence_manifest.json`은 압축된 결과의 해시 목록이다. `restore_verification.json`에 빈 폴더 복원 검사 결과를 남긴다. 원시 FZP·대형 native DB는 이번 Git 증분에 포함하지 않고 로컬에 보존한다. 추출된164프레임·장부·초기 상태·완료20개 예측은 포함하므로 저장 결과 검사를 재현할 수 있다. 원시 재추출에는 기존 원본의 별도 전송이 필요하다.
