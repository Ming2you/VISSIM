# 합류 속도 입력과 완료된 RM 관측 전달

브랜치: `codex/control-full-review-20260909`. 이전 전달 `56fcfac` 이후의 증분이다. **RM/VSL 순이득 보정은 NOT_QUALIFIED**이며 새 입력은 기본 실행에 활성화하지 않았다.

## 이번 변경

- 기존 `evaluation/controllers/physical_lane_groups.py`에 선택적 `ramp_entry_speed_kmh`를 추가했다. 실제 수용한 합류 차량의 속도 모멘트를 전달하고 분기 전후 재고·횡방향 교환에서도 유지한다. 호출에 입력이 없으면 기존 동작이다. adapter/vendor/수요/기준망/목적함수는 바꾸지 않았다.
- 관련 단위 검사47개를 전달 직전 재실행해 통과했다. 기능 비활성4개 전체 예측 JSON 일치, 유효16개 예측의 보존·서측 불변·33,712개 혼합식·19,800개 ODE 입력 검사를 다시 확인했다. 실패한 첫12개 결과는 별도로 보존했다.
- 평균 합류 속도, 기존 merge 항 유지/대체, 짧은 합류 후 공간의 세 후보 모두 실제 RM/VSL 순이득 부호를 복원하지 못했다. 기본 모델로 승격하지 않는다. 자세한 수치는 `diagnostics/demand_sweep/ramp_dsd_20260916_v2/cohort_dynamics_20260920/RAMP_ENTRY_VELOCITY.md`에 있다.
- 같은 seed23·RM 명령의 추가 관측 런이3000초까지 완료됐다. LDP/readback 검증 PASS, 기존9열 FZP11,790,482행 정확 일치. 초기5,189대와61개 interaction 프레임을 포함했다. 첫 parser 실패와 수정 전 소스도 보존했다. 관측 반복은 새 독립 성능 표본이 아니다.

## 복원과 검사

저장소 루트에서 이전 증거 패키지를 차례로 복원한 후 이번 패키지를 복원한다. 다른 내용의 파일을 덮어쓰지 않는 기존 복원기를 그대로 사용한다.

```powershell
python -B -X utf8 diagnostics/handoff_20260916/restore_evidence.py --restore --verify
python -B -X utf8 diagnostics/handoff_20260916/restore_evidence.py --package diagnostics/handoff_20260919 --restore --verify
python -B -X utf8 diagnostics/handoff_20260916/restore_evidence.py --package diagnostics/handoff_20260921 --restore --verify
python -B -X utf8 diagnostics/handoff_20260916/restore_evidence.py --package diagnostics/handoff_20260921_response --restore --verify
python -B -X utf8 diagnostics/handoff_20260916/restore_evidence.py --package diagnostics/handoff_20260921_entry_speed --restore --verify
python -B -X utf8 diagnostics/handoff_20260921/verify_followup.py
python -B -X utf8 diagnostics/handoff_20260921_response/verify_response_records.py
python -B -X utf8 diagnostics/demand_sweep/ramp_dsd_20260916_v2/cohort_dynamics_20260920/verify_ramp_entry_velocity.py --check-only
python -B -X utf8 diagnostics/handoff_20260921_entry_speed/verify_native_records.py
```

위 검사는 저장된 기록을 읽는다. 새 예측이나 VISSIM 런을 시작하지 않는다. 이전 실험의 core pin은 당시 소스인 `ramp_entry_velocity_work_v1/physical_lane_groups_before.txt`로 확인한다. 과거 결과의 해시는 고치지 않았다. 최신 직접 파일 해시는 이번 `direct_files.json`을 마지막에 겹쳐 확인한다. 기존 entry 검사기에 읽기 전용 옵션만 추가했고 수정 전 검사기도 보존했다.

원본 FZP·DB·KNR/배경 이미지는 Git에 넣지 않았다. `evidence_manifest.json`의 `excluded_raw`에 경로와 크기를 기록했다. 9열 동등성은 완료된 전체 대조의 영수증과 데이터 prefix 해시를 전달하며, 원시 행 재대조를 반복하려면 원본 파일을 별도 전송해야 한다. 저장된 모델 예측·interaction 프레임·명령/LDP 증거·실패 기록은 복원할 수 있다.

## 이어서 할 일

1. `RAMP_ENTRY_VELOCITY.md`와 `route_state_native_v1/rm_ramp_s23/analysis_v2`부터 읽는다. 완료된 관측 런을 다시 돌리지 않는다.
2. 실제 추종 대상과 제동 지속시간을 보고 RM이 첫 제동을 피한 뒤 다른 차량/시점으로 교란을 옮겼는지 구분한다. 첫 차량 사례만으로450초 이득을 단정하지 않는다. off-ramp 배수·차로 접근으로 생기는 비용도 유지한다.
3. 평균 속도·전역 계수 sweep을 반복하지 말고 필요한 최소 반응 상태를 식별한다. 유리한 RM 사례와 해로운 강화 RM 사례를 모두 설명해야 한다.
4. 구성 비용·순위·무제어 보호를 통과한 뒤 미사용 seed로 확인한다. Ω 도시 대기·TTD 및 full GNE 연결은 여전히 별도 미완료다.

이번 전달에서는 새 시뮬레이션을 실행하거나 다른 프로세스에 개입하지 않았다. 기존 완료 결과를 정리한 커밋이다.
