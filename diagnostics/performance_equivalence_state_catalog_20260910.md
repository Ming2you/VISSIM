# 실제 기록 기반 성능 동치 검증 상태

**첫 주실험은 v4 설정 + 실제 NC 900초 raw + 같은 런의 이전 750초 action으로 유지한다.** 이후 상태는 기존 head-OFF 설정을 양쪽 코드에 동일하게 적용하는 별도 보조군이 적합하다. 1050초 이후의 실제 head GREEN/crossing 창은 없으며, 후반부 v4 누적 관측 이력을 만들어 넣을 수 없다.

JSON catalog는 14개 선택 상태와 5개 실행의 전체 snapshot 파일 목록, raw/이전 action/manifest/config/source의 SHA를 담는다. 작은 JSON과 기존 요약만 읽었고 생산 코드 import·투영·MPC·VISSIM·FZP 재스캔을 하지 않았다. 읽은 45개 근거의 변경은 0건이다.

| 권장 역할 | 실제 기록 | Ω N / FW N [veh] | E8 N / 평균속도 [veh, km/h] | 실제 head 창 |
|---|---|---:|---:|---|
| 주실험 초기 | head-ON NC v2, 900 | 1763 / 841 | 19 / 112.11 | 750–900, 150개의 1초 전이 |
| 발생 직전 | 기존 source β0, 1200 | 2405 / 1070 | 60 / 36.17 | 없음 |
| 지속 저속 발생 | 기존 source β0, 1500 | 2917 / 1177 | 87 / 22.33 | 없음 |
| 심한 혼잡 | 기존 source β0, 3300 | 5126 / 2973 | 263 / 2.42 | 없음 |
| 거의 정지 | 기존 source β0, 3600 | 5364 / 3100 | 310 / 0.67 | 없음 |
| W0 부분 회복 | 기존 source β0, 4950 | 5285 / 3267 | 267 / 1.81 | 없음 |
| 후반 지속 혼잡 | 기존 source β0, 5100 | 5241 / 3289 | 281 / 2.54 | 없음 |

`source β0`의 정확한 실행명은 `codex_area_sources_beta0_s13_20260910`이다. 각 행의 이전 action은 같은 실행에서 직전에 실제 작성된 파일을 선택했으며 JSON에 경로와 hash가 있다. 4950초는 이후 450초 자료가 남는 마지막 선택점이다. 5100은 300초, 5400은 0초만 남으므로 5400을 450초 예측의 관측 검증 상태로 쓰면 안 된다.

망 전체 또는 E8의 해소 상태는 이번 완료 자료에 없다. 5400초 E8 속도는 무제어 9.25, 기존 β0 0.73km/h다. W0만 보면 β0의 4740/4770/4800초가 30km/h 미만이고 4830–5040초는 30 이상으로 일시 회복한다. 4950초 W0는 36.63km/h이며 5070초 다시 28.90이다. 이 부분 회복을 전체 정체 해소로 부르지 않는다. 물리적 해소 상태가 꼭 필요하면 현재 catalog의 해당 범위는 미확보다.

## 구성과 관측 이력

- 주실험 설정: `diagnostics/contract_candidate_configs_v4/n7_area_beta300.json`. 기록 raw는 `codex_contract_observed_nc_s13_1050_v2_20260910/state_000900.json`, 이전 입력은 같은 decisions 폴더의 `action_000750.json`이다. 실제 두 파일 경로는 JSON에서 고정한다. raw의 네트워크·tuning provenance는 원본 v2 런 그대로이며 현재 v4 모델을 적용하는 재구성임을 명시한다.
- v4 900초 기존 main 결과에서 `head_observation_prior_discarded=0`이고 실제 예전 관측 후보/기본 floor 이력은 존재한다. 그러나 새 관리 자원 10619/10629의 observed-resource floor는 둘 다 0이다. 따라서 이 상태를 “후반까지 누적된 v4 resource floor”라고 부르지 않는다.
- head-ON raw는 1050초까지이며 NC v2의 native 900–1050창과 β300 v3의 실제 제어 900–1050창 둘 다 보존되어 있다. 서로 다른 실행의 물리 상태와 GREEN 창을 한 입력으로 섞지 않는다. 두 1050 raw는 해당 짧은 실행의 끝이므로 후속 관측 검증 구간이 없다.
- 후반 동치 보조군 설정: 현재 존재하는 `diagnostics/contract_observer_off_configs_v3/n7_area_beta300.json`을 baseline/optimized 양쪽에 똑같이 사용한다. 원래 1초 head 관측이 없는 같은 raw·이전 action·config·workers로 비교하므로 clock 계산/후반 혼잡 동치에 한정된다. v4 head-resource 적용 성능을 대신 입증하지 않는다.
- v4의 head flag만 OFF로 바꾸면 resource contract가 enabled-head를 요구하여 실패한다. head-OFF manifest를 그대로 ON consumer에 넣어도 provenance guard가 실패한다. 이런 경우는 “빈 자료 cold fallback”이 아니다. 이번 catalog는 설정이나 raw를 바꾸지 않았다.
- 모든 snapshot 재구성은 그 시점의 실제 경로·위치로 cohort를 다시 초기화한다. 이전 모형 rollout의 숨은 상태를 연속 이관하는 실험과 구분한다. 양쪽 비교 입력 bytes와 초기화 경로를 동일하게 고정해야 한다.

## 같은 네이티브 물리 자료의 보조 근거

현재 코드의 완료 head-OFF NC5400(`codex_contract_nc_headoff_continuous_s13_5400_v3_20260910`)은 900/1500/1800/2100/2700/3600/4500/5400 anchor를 보유한다. 이번에 직접 읽은 1500/3600/4500/5400은 원래 NC의 차량 records·route records·FW42셀 객체가 모두 정확히 같았다. 기존 full-FZP 비교도 26,693,633행 payload SHA 일치를 기록한다. 이번 작업에서 FZP를 다시 읽지는 않았다.

이 원래 NC의 tuning 파일 경로는 이후 갱신되어 현재 bytes가 당시 manifest SHA와 다르다. 따라서 원래 NC의 현재 경로를 “당시 정확한 설정”이라고 재사용하지 않는다. 현재 head-OFF v3의 기록 tuning은 원본 manifest와 일치한다. 전체 소스 commit, 실제 adapter/VBS SHA 및 이 차이는 JSON의 `runs`에 구분되어 있다.

재생성: `python -X utf8 -m diagnostics.catalog_performance_equivalence_states`. 산출물은 `performance_equivalence_state_catalog_20260910.json`; 이 작업은 후보를 실행하거나 생성하지 않는다.
