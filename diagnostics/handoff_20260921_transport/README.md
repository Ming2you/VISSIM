# 모델 수정·후속 검증 전달

브랜치 `codex/control-full-review-20260909`, `1fcca58` 이후 증분이다. 누적 정본 모델 수정은 이전 커밋에 포함되어 있으며, 이번에는 국소 수송 후보 코드와 완료된 RM 반응 진단을 추가한다. **RM/VSL 순이득 보정은 NOT_QUALIFIED**다. 실패한 후보를 기본 활성화하지 않았다.

## 이번에 전달하는 내용

- 기존 `downstream_spatial_rollout.py`에 선택적 면 재구성 수송을 추가했다. 수치적 퍼짐은 줄었지만 12개 중 10개 속도 오차가 커지고 이득을 설명하지 못해 기각했다. 기본값은 꺼져 있으며 정본 controller에 연결하지 않았다.
- 같은 초기 차량 2,706쌍의 체류시간과 900쌍의 공통 완료 통과를 분석했다. seed23에서는 합류부 이후 하류 지연이 늘고 seed33에서는 줄었다. 통과 차량만의 분석을 전체 TTT나 인과 효과로 대체하지 않는다.
- 동일 초기 상태의 열린 말단 조건 6개 예측을 보존했다. 앞서 맞았던 seed33 RM 순위가 말단 처리 변경 후 틀려, 이전 순위 일치를 검증 성공으로 볼 수 없음을 확인했다.
- 원래 소스 해시, 기각 결과, 최초 검증 실패와 수정된 검증, 전체 저장 예측을 보존한다. 기존 spatial 기록 검사기는 수정 전 소스 보존본도 해시로 확인하도록 보완했다.

자세한 근거는 [수송·통과시간 보고서](../demand_sweep/ramp_dsd_20260916_v2/cohort_dynamics_20260920/TRANSPORT_DIFFUSION_AND_PASSAGE.md), [초기 차량·말단 보고서](../demand_sweep/ramp_dsd_20260916_v2/cohort_dynamics_20260920/MATCHED_COHORT_AND_OUTLET.md)에 있다. 보고서의 “아직 푸시하지 않음”은 작성 시점의 기록이며 이 전달에서 포함했다.

## 유지하는 조건과 남은 작업

사용자 가속거리 수정 + 램프 DSD120 + 동측 본선 입력1098만 0.8배 조건을 유지한다. 과거 전역80/도시50 조건과 다르다. 이번 전달에서 core 4파일·기준망·수요·기본 설정을 추가 변경하지 않았고 새 VISSIM 런도 시작하지 않았다.

다음에는 현재/과거 자료로 관측 가능한 합류 이후 감속·추종 상태의 지속시간과 회복을 검토한다. 이 작업은 아직 착수 결과가 없다. 이미 실패한 전역 계수·공간 해상도·고정 차로 이동률 탐색을 반복하지 않는다. 후보는 차량 보존, 램프/진출 대기 비용, 자율 예측, RM/VSL/동시의 구성 비용과 순이득 순위, 무제어 보호를 함께 통과해야 한다. 개발 seed13/23/33/43을 미사용 검증 자료로 취급하지 않는다. 미사용 seed 검증·전체 Ω·full GNE 연결은 아직 남아 있다.

## 다른 컴퓨터에서 복원

이전 패키지를 순서대로 복원한다: `handoff_20260916` → `handoff_20260919` → `handoff_20260921` → `handoff_20260921_response` → `handoff_20260921_entry_speed` → `handoff_20260921_spatial` → `handoff_20260921_midpoint` → `handoff_20260921_matched_response`. 각 패키지 README를 따른 뒤 저장소 루트에서 실행한다.

```powershell
python -B -X utf8 diagnostics/handoff_20260916/restore_evidence.py --package diagnostics/handoff_20260921_transport --restore --verify
python -B -X utf8 diagnostics/handoff_20260921_transport/verify_records.py
python -B -X utf8 diagnostics/handoff_20260921_matched_response/verify_records.py
python -B -X utf8 diagnostics/handoff_20260921_spatial/verify_records.py
```

이 검사들은 저장 기록을 읽으며 새 예측이나 VISSIM을 실행하지 않는다. 복원 도구는 기존 파일이 다르면 덮어쓰지 않고 중단한다. `verification.json`은 전달 전 재검사 결과, `restore_verification.json`은 빈 폴더 복원 결과다. `evidence_manifest.json`과 `direct_files.json`에 전달 파일의 해시를 기록했다.

원시 FZP·native DB는 용량 때문에 Git에 포함하지 않았으며 로컬에 보존한다. 이번 패키지의 추출된 초기 차량 궤적·통과 기록과 이전 관측·예측 자료로 저장 결과 검사는 가능하다. 원시 FZP를 다시 추출하려면 이전 manifest의 원본 파일을 별도로 옮겨야 한다.
