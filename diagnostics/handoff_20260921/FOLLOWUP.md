# 같은 상태의 RM 강화 및 경계 통과 진단 후속 전달

누적 모델 수정은 `6d7612b`에 들어 있다. 이번 후속은 모델이나 기본 설정을 추가로 바꾸지 않고, 그 뒤 완료한 진단 코드·저장 예측·검증 결과·인계 문서를 보존한다. **RM/VSL 순이득 보정은 NOT_QUALIFIED**다. 새 VISSIM 실행이나 진행 중 프로세스 조작은 하지 않았다.

## 다른 컴퓨터에서 복원

`codex/control-full-review-20260909` 브랜치를 최신으로 받은 뒤 저장소 루트에서 실행한다. 새 결과 JSON은 Git에 직접 포함되어 별도 압축 해제가 필요 없다. 이전 결과만 아래 패키지로 복원한다.

```powershell
python -B -X utf8 diagnostics/handoff_20260916/restore_evidence.py --restore --verify
python -B -X utf8 diagnostics/handoff_20260916/restore_evidence.py --package diagnostics/handoff_20260919 --restore --verify
python -B -X utf8 diagnostics/handoff_20260916/restore_evidence.py --package diagnostics/handoff_20260921 --restore --verify
python -B -X utf8 diagnostics/handoff_20260921/verify_followup.py
python -B -X utf8 diagnostics/handoff_20260921/verify_latest_records.py
```

`verify_followup.py`는 최초 직접 전달 manifest와 이번 증분 manifest를 함께 검사한다. 의도적으로 갱신한 문서는 새 해시로 확인하고 나머지 파일은 이전 해시를 유지한다. 이어서 저장된 입력 pin, 예측 검증 결과, 1초 경계 보존식과 구성 비용을 확인한다. 예측 재계산이나 native 실행은 하지 않는다. 최초 커밋의170개 단위 검사 PASS는 그대로 보존하며, 모델 변경이 없는 이번 전달에서 그 검사를 재실행했다고 주장하지 않는다.

원본 FZP 두 파일은 각각 약1.05GB로 기존 manifest의 별도 전송 대상이다. 이번 Git에는 추출한1초 경계 사건·재고·차량군 체류와 저장 예측을 담았다. 원시 추출 재실행에는 FZP 별도 전송이 필요하다. 원본 FZP 무결성 기록은 크기·수정 시각 및2550초 payload 해시이며 파일 전체 해시가 아니다.

## 완료된 새 결과

아래 `K`는 `diagnostics/demand_sweep/ramp_dsd_20260916_v2/cohort_dynamics_20260920`이다.

- `K/paired_response_identification.py` 및 `_v1/result.json`: 개발 seed23/33/43의 시차 반응식 비교. 실제 미래 경계 입력을 제공한 진단에서도 오차를 줄이지 못해 기각했다. 온라인 예측 또는 독립 holdout 성공으로 해석하지 않는다.
- `K/matched_meter_increment.py`, `matched_meter2550_v1`: 동일2550초 전 망5,208대 상태에서 g8 유지와 g6→g4→g4를450초 비교했다. 추가 비용은 실제+1.498611veh·h, 모델+.013486이며 본선 효과는 실제+.401389, 모델−.463971이다. 영역은 FW_E 본선+4on/4off connector이고 Ω 전체가 아니다.
- `K/verify_response_identification.py`, `response_identification_validation_v1/result.json`:65개 입력 pin,18개 식별 예측 정확 재현,270단계 보존 및 미래 관측을 모두 제거한2개 전체 예측 JSON 일치를 확인했다. 이 검사는 이미 완료된 기록이며 재실행 스크립트는 출력 폴더가 있으면 중단한다.
- `K/marginal_boundary_timing.py`, `marginal_boundary_timing_v1`: 두 조건 각각451개1초 재고,450개 연속 보존,315개 셀 스냅샷과 경계 사건을 확인했다. 기존1초 재고 CSV와 일치하고 미확인 본선 전이는0이다. 도시부 전체 삭제가0이라는 뜻은 아니다.

## 마지막 경계 장부가 말하는 것

2550초에 있던 본선676대가 두 조건에서 동일하다. 강화−유지의 누적 본선 ΔTTT는2700초−.038889,2850초+.038056,3000초+.401389veh·h다. 마지막 차이 중 초기 차량군은+.431389, 이후 유입 차량군은−.030000이다.

각 경계 사건에 `(구간 끝−통과 시각+1초)`를 부호와 함께 곱한 체류시간 장부에서 말단 방출 사건의 차이는+1.129167veh·h,10490 합류 사건은−.809722이다. 나머지 경계 기여를 더하면+.401389가 정확히 닫힌다. **이것은 회계 분해이며 말단 지연의 원인이나 각 경계를 독립적으로 조작한 효과를 식별한 결과가 아니다.** 시작 시 이미 본선에 있던 차량들의 하류 지연을 놓치는 문제를 우선 추적할 근거다.

본선 TTT는 기존 whole-link1초 말단 재고 규약을 유지했다. 입력점의 음수 위치 차량을 제외한 대안은+.400833veh·h로 따로 기록했다. 서로 다른 계산 규약을 섞어 이득을 주장하지 않는다.

다음 작업은 하류16–20셀에서 초기 차량군의 지연과 방출 시간차가 발생하는 조건을 정상 진출 배수·도착 예측과 구분하는 것이다. 이 해로운 추가 RM 사례를 기존 이로운 RM/VSL 사례와 함께 검증한다. 보정 후에도 무제어 보호·미사용 seed·정본 연결, 이후 Ω 비용/full GNE 검증이 남는다. 이 진단에서는 새 물리 모델을 채택하지 않았다.
