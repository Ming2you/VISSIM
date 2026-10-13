# S-DMPC controller and adopted mixed-network plant — 2026-10-13

이 인계는 공동 S-DMPC 컨트롤러, 채택된 도시부·고속도로부 플랜트, 실행 입력, VSL 세 설정, 영역별 정보 분리 두 설정을 함께 전달한다. 기준 이력은 `ca181e843058872ac4726758625e5c4057daba5f`, 실제 전달 소스는 채택355를 가져온 `solo355` 패키지의 `2f28000ab0ea61b646badade70c172200e9c7f1a`이다. 별도 저장소의 소스와 아직 Git에 등록되지 않았던 실행 의존성을 원래 upstream 이력에 통합했다. `source_manifest.json`이 전달 파일의 SHA256 정본이다.

현재 로컬 native 큐의 원본·동결본·프로세스는 이 전달 작업에서 바꾸지 않았다. 아래 구성은 새 실행 허가나 현재 큐 재시작 지시가 아니다. 역사적 계획/검증 영수증의 `prepared`, `native_runs: 0` 및 로컬 절대경로는 당시 기록이며 현재 실행 상태를 나타내지 않는다.

## 현재 사용할 설정

공통: FW80/U90 수요, seed29, 150초 제어, 450초 예측(3블록), 말단비용 OFF, 고속도로 명목5초/도시10초, RM 최소 녹색2초·변경폭2초. 명목 시간격자와 내부 보존/안정성 서브스텝은 구별한다. 실험·성능 비교 구간은 0–8100초다.

| 설정 | 제어수단 | 목적·정보 |
|---|---|---|
| joint/window | 신호 green/offset와 RM 최적화. FW_E__seg13만 1800≤t<5700에90, 나머지110km/h | 전체 Ω701 TTT, 결합 예측 |
| joint/optimized | 신호·RM·VSL 최적화. 동서 내부4구역씩50–110/10단위, 입구·마지막110 | 전체 Ω701 TTT, 결합 예측 |
| joint/off | 신호·RM 최적화, VSL 전체110 | 전체 Ω701 TTT, 결합 예측 |
| freeway_only | VSL·RM 최적화, 도시신호 native baseline | 본선+진입램프 TTT, 자기 영역 관측 |
| urban_only | 신호만 최적화, VSL110·RM OPEN | 도시도로+진출램프 TTT, 자기 영역 관측 |

공동제어 설정은 `diagnostics/repin_v3c3_review_20261001/urban_rm269/aggregate270/native413_adopted355/{window,optimized,off}_config.json`이다. 영역별 설정은 `diagnostics/solo355_local_20261013/{freeway_only,urban_only}_config.json`이다. 기존 `diagnostics/solo355_20261012/` 설정은 제어수단만 분리한 이전 단계이므로 자기 정보만 사용하는 실험에는 쓰지 않는다. Window와 optimized는 적용 구역도 다르므로 타이밍만의 비교가 아니다.

## 컨트롤러

진입점은 `evaluation/controllers/vissim_stackelberg_adapter.py` 한 곳이다. 관측 투영·실행 제약·작동 가능한 초기 명령을 준비하고 `sdmpc.solve`를 호출하며, 검증된 첫150초 명령을 기존 writer로 보낸다. `sdmpc.py`, `sdmpc_pfo.py`, `sdmpc_central.py`, `sdmpc_budget.py`, `sdmpc_dual.py`가 공통 기준점, own+externality 가격, PFO/리더 자원 제약 및 원 모델 재평가를 처리한다. `sdmpc_sequence.py`가 3블록의 실행 제약을 연결한다. N_P/N_UF 자원과 주체 비용은 단순한 본선 보상 하나로 대체하지 않는다.

`sdmpc_aggregate.py`와 `sdmpc_aggregate_transport.py`는 경로 집계 예측, `sdmpc_tangent_*`는 reverse AD·제약·비용 응답을 담당한다. 공동제어에는 동일 물리 상태/명령에서만 쓰는 응답 재사용, 공유 primal, 집계 수송과 hotpath가 반영돼 있다. VSL 실행 후보 secant 검사와 유한 RM 이웃/조합 검사도 포함하며 최종 후보는 같은 cap·비용·물리/실행 제약으로 재검증한다. 이전 명령 유지와 신규 명령 성공은 제어 건강성에서 따로 센다.

정보 분리 모드는 `sdmpc_actuator_scope.py`, `sdmpc_regional_context.py`, `sdmpc_regional_contracts.py`, `sdmpc_regional_prototype.py`를 사용한다. 상대 상태·예측·비용·가격·예산은 결정 그래프에서 제외한다. 경계 유입은 자기 측 최근 완료150초 통과량의 일정 미래 요청이고 수용량 자체가 아니다. 수용 불가 요청은 외부 backlog에 보존한다. 출구는 기존 정적 용량의 open-outlet 근사이며 상대편 spillback을 예측하지 않는다. VISSIM 실제 물리 연결은 유지된다. 목적함수·정보·제어수단이 함께 바뀌므로 정보교환만의 효과를 분리한 실험은 아니다.

## 전체 플랜트의 채택 내용

| 영역 | 주요 모듈 | 반영 내용 |
|---|---|---|
| 관측·비용 | observation_projection, calibrated_initial_projection, control_area_objective, area_follower_objective | 물리 재고와 경로/차로 귀속, Ω 비용, 수용/외부 대기 보존 |
| 본선 | lane_freeway_runtime, area_freeway_accounting, multirate_freeway | 기존 보정된 셀/차로 파라미터, 속도·밀도·흐름과 VSL 반응, 명목5초 적분 |
| 진입램프·합류 | lane_ramp_runtime, physical_ramp_boundary, ramp_entry_receiving | 유한 저장공간, 실제 수용/합류, RM head 이전·이후 재고와 입구 막힘 전달 |
| 도시부 | lane_urban_runtime, calibrated_urban_runtime, route_choice_corridor, urban_flow_accounting | 경로 집계 수송, 신호 service와 유한 차로 수용량, 하류 막힘의 상류 방출 제한 |
| 진출램프·접속 | lane_offramp_runtime, lane_coupling, multirate_coupling | 본선 진출·도시부 수용과 교환량 보존, 진입램프 합류와 별도의 경로/상태 |
| 신호·저장공간 | head_service_resources, local_signal_service, urban_storage_guard | 도시17신호 저장공간 보호,40좌회전 차로 배분 및 head/service 귀속 수정 |

68번은 자체 차로 저장공간과10681 램프 앞 재고를 상류 방출에 연결하며121의 빈 공간을 빌리지 않는다. 채택355의 추가 보정은10639/10484의 `single_lane_causal_receiving`, wave `3.2557309454394003 m/s`이다. 410 service uplift 등 기각된 후보는 실행 설정에 채택하지 않았다. 진입램프의 대기는 고속도로 영역, 진출램프는 도시부 영역에 포함하는 단독제어 구분을 사용한다. 전체 사후평가 Ω701은 동일하게 유지한다.

공통 값은 `evaluation/parameters.json`과 그 로더, 승인된 명시적 tuning으로 관리한다. `vendor/NumSim-mine`는 upstream 기준과 동일한 바이트를 유지했다. `plant/src/vissim_strict` 및 compiler/topology/관측·실행 증거 코드도 전달 범위에 포함된다. `diagnostics/**/source_before`와 과거 후보 코드는 재현/감사 기록이며 현재 생산 경로가 아니다. 현재 채택 여부는 위5개 설정으로 판단한다.

## 검증과 남은 한계

채택355 기존 증거:22시험,213축 scalar/AD 최대 비용 오차2.84e-14, 저장 전체선택219.509초. 지역 모드 기존 증거:66회귀시험과 후속 context5시험, 자기 관측 민감도·상대 입력 비간섭,3블록 writer/보존·수용량 검사. 저장900초 전체선택은 FW180.619초, 도시62.622초이고 두 결과 모두 `converged:false`, `best_observed_feasible_sdmpc`이다. 이 시간은 전체 선택이며 단일 미분예측 시간이 아니다. 두 outer iteration/세 line-search 설정에서 얻은 최선 관측 실행가능 명령으로, GNE/최적해 인증이 아니다. 세부 수락/평가 횟수는 보존된 task-5 보고서와 영수증을 따른다.

지역 모드는 정보 분리를 검증하기 위해 일부 공동제어 hotpath를 껐고8 reverse workers를 유지한다. 따라서 공동제어의 이전 계산시간과 동일하다고 주장하지 않는다. 정확한 설정 차이는 `diagnostics/solo355_local_20261013/config_delta.json`에 있다.

차로 횡방향 gap/FIFO의 완전한 미시 재현은 아니다. 도시 재고와 제어 이득 방향 오차, VSL의 실측 순이득 보정은 남아 있다. 물리·미분·writer 검사 통과와 시뮬레이션 완료만으로 전체망 성능 개선을 선언하지 않는다. 기존 seed29 보정은 독립 holdout 검증이 아니며 신호/RM도 달라지는 정책 비교는 순수 VSL 인과 효과가 아니다. 종료 잔여를 정상 유출로 세지 않고, 삭제·미삽입·외부대기·실행 검증을 TTT와 함께 보고한다. LSA 누락은 보존하고 승인된 LDP 대체 여부를 별도 기록한다.

## 다른 컴퓨터에서 확인·실행

Windows와 라이선스가 있는 VISSIM COM 설치, Git, PowerShell7, Python3.12 계열 및 `numpy`, `scipy`가 필요하다. `pytest`는 시험용, `matplotlib`/`pandas`는 분석용이다. 이 컨트롤러 실행에는 RL용 torch를 설치할 필요가 없다. 아래 경로는 해당 컴퓨터에서 정한다. 프로젝트 기본값의 이전 사용자 C/D/E 경로를 그대로 사용하지 않는다.

```powershell
$repo = (Get-Location).Path
$python = (Get-Command python).Source
$pwsh = (Get-Command pwsh).Source
& $python -B tools/sdmpc31/verify_publication.py
& $python -B scripts/verify_parameters.py diagnostics/repin_v3c3_review_20261001/urban_rm269/aggregate270/native413_adopted355/optimized_config.json
```

새 실행을 별도로 결정했을 때만 기존 정본 freezer를 한 번 호출한다. 출력은 사용하지 않은 디렉터리여야 한다. 로그의 `FREEZE_DONE`와 실제 `FRZ=` 경로를 확인해 `$frozen`에 넣는다.

```powershell
& $pwsh -NoProfile -File tools/sdmpc31/freeze_worktree.ps1 -Source $repo -FrozenRoot D:/VISSIM_runtime/new_publication/frozen -Python $python
$frozen = 'D:/VISSIM_runtime/new_publication/frozen/REPLACE_WITH_ACTUAL_FRZ'
$results = 'D:/VISSIM_runs/new_unique_condition'
$tuning = 'diagnostics/repin_v3c3_review_20261001/urban_rm269/aggregate270/native413_adopted355/optimized_config.json'
$runner = Join-Path $frozen 'diagnostics/sdmpc_n31_20260924/integration_20260926/run_closedloop3000.ps1'
$runArgs = @{FrozenTree=$frozen; ResultsRoot=$results; StatusPath="$results/native_status.json"; SimPeriod=8100; Arms='sdmpc'; TuningRelativePath=$tuning; PythonExe=$python; PowerShellExe=$pwsh; DependenciesPath=''}
& $runner @runArgs -PreflightOnly
# 사전검사 성공과 다른 VISSIM 부재를 확인한 뒤 한 번만:
& $runner @runArgs -Detached
```

정본 manifest, NoGlobalKill, MaxAttempts1, 최초 실제진행300초 watchdog을 유지한다. STOP·기존 실행 영수증·실패 출력은 지우지 않는다. 진행 중 다른 VISSIM을 종료하지 않는다. 같은 컴퓨터의 조건은 순차 실행하고 SIM_DONE8100·실제 runner exit0·정확한 소유 프로세스 종료·control health를 모두 확인한다. 이 푸시 작업에서는 freezer/native/전체 최적화를 새로 실행하지 않았다.

`publication_validation.json`은 이번 전달 체크아웃의 검사 결과다. 나머지 리뷰/검증 영수증은 기존 완료 검증의 사본이며 외부 대용량 관측/피클/FZP를 자동 다운로드하거나 포함하지 않는다. 저장상태에 의존하는 오프라인 qualification은 해당 입력을 별도로 보유해야 재현된다. 새 native 실행은 포함된 정적 망·수요·매핑·신호 입력을 쓴다.
