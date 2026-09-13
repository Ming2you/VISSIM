# 선정 수요의 기존 제어기 실행 준비

후속 수선: r01은 첫 t1에서 `Shared native demand profile differs from its pinned scenario source`로 종료되었다. 아래 최초 6개 검사 증거는 그 이전 버전의 범위를 기록한 것이다. 현재 준비기는 `urban.native_internal_inputs`와 `urban.shared_approach` 두 선언을 파생하며, 각 원문의 `demand_profile` 및 별도 derivation만 바꾼다. 원래 helper/tests의 raw bytes는 `selected_control_shared_profile_proposal_v1/r01_helper_sources.zip`에 보존했다. 최신 9개 검사 PASS(0.476초); r01 실런 입력·결과는 수정하지 않았다. 새 r02는 fresh directory를 사용한다.

새 래퍼는 `SelectedPrepared`의 전체 34입력 × 6구간 수요를 기존 VBS의 입력별 multiplier로 변환한다. 70/30 및 70/40은 204행 모두 절대오차 1e-10 veh/h 이내다. 70/30의 200행은 float exact이며 나머지 최대 오차는 4.547473508864641e-13 veh/h다. 이는 연산 순서 차이이고 실제 첫 900초 궤적 일치는 아직 실행 검증 대상이다.

주 시험은 70/40이고 70/30은 낮은 부하 대조다. 다음 명령은 기본적으로 계획만 출력한다. 실제 실행은 root가 `-Execute`를 붙인다.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File diagnostics/run_selected_control_trial.ps1 -SelectedPrepared diagnostics/demand_sweep/fw070_urban040/prepared -Tuning diagnostics/contract_candidate_configs_v4/n7_area_beta0.json -Name codex_selected_fw070_u040_beta0_r01
```

실행 시 새 `diagnostics/selected_control_demand/<Name>` 아래 profile.csv, comparison.csv, native_internal_inputs.json, shared_approach.json, config.json, checks.json, launch.json을 생성한다. 기존 파일을 덮어쓰지 않는다. config 변경은 위 두 선언 경로뿐이다. 새 두 선언은 `demand_profile`과 별도 `selected_demand_derivation`만 바뀐다. 원래 선언의 물리 정의·모든 다른 핀은 보존하며 현재 validator를 끄거나 바꾸지 않는다. 선택 네트워크 SHA가 원래 선언과 다르면 거부한다.

초기 900초는 no-control, seed13, 원래 flat baseline 네트워크다. 제어는 기존 v4 beta0 설정이며 all-lever GNE 완료본이 아니다. StartupStallSec=300, 계산 중 StallSec=2400, MaxAttempts=1, NoGlobalKill을 사용한다. 기존 VISSIM이 있으면 실제 실행을 거부한다. 래퍼는 종료용 kill을 추가하지 않고 canonical watchdog의 정확 PID 정책을 사용한다.

`RW_STATE_LOG=decision`과 150초 로그는 추가 30초 상태 행/스캔을 줄인다. head observation ON의 필수 1초 차량·SG 관측은 유지된다. legacy measured capacity이면서 head observation OFF이면 기존 full/30 설정을 명시해야 한다. 상속된 네 가지 진단 bootstrap 경로 및 RW 환경은 제거한다.

외부 child PowerShell의 watchdog 종료 후 `<run>/completion_receipt.json`을 쓴다. schema는 `selected-control-completion/v1`. `exit_code`는 watchdog 프로세스 값이며 `cscript_exit_code=null`을 유지한다. 정확 native PID/생성시각 종료, 원본/생성 수요 입력 SHA, canonical provenance, SIM_DONE/SIM_SEC, 실패 카운터 5개, 마지막 상태 시각, native FZP/LSA 존재, 보존된 numbered ERR를 검사한다. ERR 경고 자체는 완료 실패로 바꾸지 않고 원본과 SHA를 기록해 분석기가 손실을 계산하게 한다. native ownership이 불분명하거나 아직 살아 있으면 completed=false다.

검증: 작은 6회귀 PASS(0.270초), Windows PowerShell 5.1 실제 plan 및 AST PASS. 모델/COM/실런은 0회다. 상세 SHA와 계획은 `selected_control_trial_validation.json`, `selected_control_trial_plan_fw070_urban040.json`에 저장했다. 실제 모델 validator 통과, 제어 전 warmup 궤적 일치, 실제 종료 receipt는 root의 실행으로 확인해야 한다.
