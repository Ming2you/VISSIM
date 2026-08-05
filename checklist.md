# 램프 축 복구 — 체크리스트 (2026-08-04 착수)

## 단계 구분 (2026-08-04 사용자 결정)

**현 단계 = 플랜트 수정 + 레버 유효성 검증.** 각 레버가 플랜트에 실제로 영향을 주는지,
그리고 모델이 그 영향을 같은 부호·같은 크기로 보는지를 확정한다.
G6 는 이 단계의 계측기이지 목표가 아니다.

**다음 단계 = P-Stack 컨트롤러 얹기.** 위가 끝나야 시작한다.
이유는 단순하다 — MPC 가 후보를 고르는 근거가 곧 G6 가 재는 그 서열이다.
서열이 틀린 축 위에서 폐루프를 돌리면 컨트롤러가 확신 있게 틀린 방향으로 민다
(실측: green 축 예측 +27,082 대 관측 −2,938).

---

목표: G6 램프 축의 모델-플랜트 부호 불일치(2/6)를 없앤다.
근본 원인은 두 겹이다 — **모델이 온램프 수요를 3.4배 과소추정**(3번, 수정 완료), 그리고
**관측 목적함수가 도시부의 1.4 %만 잡는다**(3b번, 큐 실행 중).
근거·판단은 `context-notes.md`, 측정 결과는 `outputs/leader_objective_reduction_20260804.md`.

---

## 0. 선행 확정 (완료)

- [x] G6 v6 그리드 18/18 완주 + 채점 (`outputs/gates_v6_20260804`)
- [x] 리더 목적함수 환원 설정 작성 (`evaluation/configs/real_world_modi_pstack_v5_tttfar_20260804.json`)
- [x] v5 설정 검증 — 극단 상태에서 벌점 합 0, `J == base`, far 살아있음
- [x] v5 목적함수로 재채점 → rho −0.080 → **+0.705** (`outputs/gates_v6_tttfar_20260804`)
- [x] 한계가격 2×4 격자 (깊이 360/900s × TTT/+hinge/+far/+both) — 램프 못 살림 확인

## 1. 도시부 route design 을 IC 방향으로 — **불필요 판정**

- [x] 판정 근거 확보: 플랜트 온램프 유입 **4,436 veh/h** (그룹당 972~1,225)
- [x] 본선 유량 감소는 온램프 부족이 아니라 **오프램프 유출(6,681)이 더 크기 때문**
- [x] 결론 — 램프 수요는 충분하다. route design 변경 없이 진행한다.

## 2. 온램프 유량 관측 수단 — **완료**

- [x] 커넥터 기하가 `<geometry><linkPolyPts><linkPolyPoint>` 에 있음을 확인 (`point3D` 아님)
- [x] `q = (N/L)·v` 로 유량 산출 — `.inpx` 무수정, VISSIM 재실행 불필요
- [x] `scripts/measure_ramp_connector_flow.py` 저장소 승격
- [x] v6 앵커 실측 산출 (`outputs/ramp_flow_v6_anchor_20260804.json`)
- [x] 미터 구속 검증 — c15(그룹 600)에서 온램프 유입 4,436 → 2,849 (**−36 %**). 플랜트에서 metering 은 작동한다

## 3. 모델 `ramp_arrival` 재적합 — **완료**

- [x] 유도 경로 확정 — `calibration.prediction.local_ramp_arrival_forecast`,
      `observed_vph = ramp_counts × 3600/queue_drain_horizon_sec × multiplier`, cap 900
- [x] 결함 확정 — `queue_drain_horizon_sec` 가 **스칼라 120 s 고정**인데
      실제 소요시간은 램프별 25.7~116.6 s 로 4.5배 벌어진다. 게다가 cap 900 < 실측 최대 1,265
- [x] 어댑터에 `queue_drain_horizon_sec_by_ramp` (dict) 지원 추가 — `max_vph_by_ramp` 와 동일 규약
- [x] 실측에서 램프별 H 산출 — R_D_W 25.8 / R_F_W 116.6 / R_D_E 30.8 / R_F_E 25.7 s (16스텝 중앙값)
- [x] `max_vph_per_ramp` 900 → 1550 상향
- [x] 새 튜닝 leaf 생성 (`real_world_modi_pstack_v5_tttfar_rampdemand_20260804.json`)
- [x] 검증 — RED(−63.0 %, 전 그룹 FAIL) → GREEN(**+0.4 %, 전 그룹 PASS**, 그룹별 −0.7~+2.2 %)
      `scripts/verify_ramp_arrival_calibration.py` (시각별 대조 모드)
- [x] 회귀 — dict 미지정 시 수정 전 값(180/180/120/810, 합계 1290)과 **비트 동일** 확인
- [x] 효과 측정 — g6_v6 재채점(VISSIM 불필요, diagnostic 후보는 고정 액션이라 궤적 불변)
      rho +0.705 → **+0.714**, 램프 축 부호일치 2/6 → **3/6**,
      G5 `freeway_mean_speed_mape_link` 0.1023 FAIL → **0.0636 PASS**
      (단 `cell_count_mae` 는 22.83 → 26.78 로 악화)

## 3b. 관측 배선 결함 — **최상위 결함, 큐 실행 중**

G6 관측 목적함수가 도시부 차량의 **1.4 %**만 잡는다(플랜트 69,495 대 투영 987).
그래서 도시부로 차를 미는 레버(green, metering)가 전부 반대 부호로 채점된다.
VSL 만 맞는 이유는 그 효과가 고속도로 내부라 관측에 그대로 잡히기 때문이다.

- [x] 원인 확정 — 모델 저류 용량 부족 아님(용량 5,580 대에 점유 83.5, 상한 링크 0개). **입력이 없다.**
- [x] 배선 추적 — `run_real_world_single_watchdog.ps1` 이 `$vbsConfig` 를 base 로 **하드코딩**.
      그 config 가 `RW_LOCAL_OBSERVABLE_LINKS`(22개)와 `RW_DETECTOR_MAPPING_PATH`(base)를 정한다.
      분산 config(SC 15개 · 링크 175개)가 존재하는데 안 쓰였다.
- [x] 러너에 `-VbsConfig` 파라미터 추가 (기본값 기존 경로 = 하위호환)
- [x] 그리드에 `-VbsConfigOverride` 추가 + `$extra` 전달
- [x] 세 스크립트 파싱 검증
- [ ] 그리드 재실행 (수요·후보는 v6 와 동일 = 관측 결함만 격리한 A/B) → `g6_v7_obsfix_20260804`
- [ ] 관측 폭 검증 — 새 state json 의 `link_counts` 가 100개 초과인가
- [ ] v5r 목적함수로 채점 → 축별 부호가 개선됐는가

부수 확인
- [x] `RW_SIGNAL_SCS` 는 선언·대입만 있고 소비처 0 — 신호는 액션 CSV 행 전부에 적용된다(15개 정상)
- [x] 축 매핑은 정합 — 모델·플랜트 모두 p1=25/p2=75, 인터페이스 1개만 반전
- [x] SC1004 가 F측 인터체인지인데 일반 도시부로 분류돼 있다(역할 분류기가 커넥터 한 홉만 봄).
      축은 우연히 맞지만 분류는 정정 대상
- [ ] C-D 링크 31/68/69/70 을 `observable_links` · `U_D`/`U_F` `visible_links` 에 추가
      (커넥터는 포화하고 그 뒤 큐가 안 보인다 — 커넥터 16개 195대 대 C-D 6개 322대)

## 3c. 도시부 토폴로지 — 36교차로 연결형 (2026-08-04)

관측 배선(3b)을 고쳐 플랜트가 175링크를 기록하게 했는데도 **투영 도시부가 83.5 대에서
소수점까지 그대로**였다. 원인은 이름공간 불일치 — 플랜트·매핑·관측은 SC 이름공간인데
모델만 default.yaml 의 6노드 격자였다. 자세한 경위는 `context-notes.md`.

- [x] 원인 규명 — `link_to_origins` 의 origin 64개 중 60개가 모델 저류링크로 번역 실패
- [x] 분산 생성기가 **모델 토폴로지까지 이미 만들어 뒀음**을 확인. 우리 체인이 그 가지를 상속 안 함
- [x] `distributed_15core` 의 램프 결합이 전부 빈 리스트인 결함 발견 (`selector != "core15"` 하드코딩)
- [x] 생성기에 `--sc1-coupling` / `--ramp-interface-sc` / `--slug` / `--stamp` 추가
- [x] 램프 귀속을 SC1 단일 -> **SC1001(D) · SC1004(F) 분리**
- [x] 비통제 21 SC 도 **동일 모델**로 세우고 `uncontrolled_nodes` 로 내보내기
- [x] `scripts/derive_intersection_adjacency.py` 신설 — 인접쌍 116개, 평균 차수 3.2, 고립 0
- [x] 모델 코어 8방위 확장 + `leg_base_dir()` 복합 키 -> **인접 보존율 100 %**
- [x] `_token_leg_dir` 이 램프 leg 를 하드코딩 `"S"` 로 찾던 결함 수정
- [x] 생성기가 `type: grid` leg 를 심고 movement 는 모델이 자동 유도
- [x] 유령 저류링크 25개 0 무력화
- [x] 병합 leaf `real_world_modi_pstack_v7_urban36_20260804.json`
- [x] 4방위 격자 회귀 — 매 수정 후 비트 동일 확인(movement 78, storage 29)
- [ ] **NumSim 전체 테스트** — 변경 전/후 비교 실행 중. 실패가 기존 것인지 판정 필요
- [ ] **포착률 재측정** — 36교차로 연결형에서 얼마나 오르는가 (기존 1.7 % -> 15SC 37.6 % -> ?)
- [ ] 인접부 TTT 분해 배선 — `uncontrolled_node_movement_queue_veh` 등 2개가 정의만 있고 소비처 0

## 4. 램프 후보 재설계 — 논의 중

- [ ] 실측 그룹 수요(모델 기준 840~1,256)를 걸치는 그룹율 격자 확정 (180 배수, 지시=실현)
- [ ] `harness/g6/g6_core.py` 에 CANDIDATE_SET_V3 추가 + `G6_CANDIDATE_SET` 스위치
- [ ] `scripts/run_g6_branch_grid.ps1` 의 `$controllerByCandidate` 확장
- [ ] 어댑터에 신규 `diagnostic-ramp-*` 생성자 추가 + allowed list 등록
- [ ] `scripts/validate_g6_candidate_wiring.py` 통과 (4층 배선 검증)

## 5. 재측정

- [ ] 새 캘리브레이션 + V3 후보로 그리드 재실행 (VISSIM, 약 2.5 h)
- [ ] v5 목적함수로 G5/G6 채점
- [ ] 램프 축 부호일치가 2/6 에서 개선됐는가
- [ ] rho / pairwise 변화 기록

## 6. 남은 별건 (이번 범위 밖)

- [x] green 축 부호 결함 — 원인 규명됨(3b 관측 배선). 수정 효과는 v7 그리드로 판정
- [ ] G5 셀 게이트 임계가 플랜트 잡음 바닥 아래 (cell MAE 22.83 대 재현성 22.01).
      임계식 `max(5.0, 0.10 x mean)` 자체를 재검토해야 원리적으로 통과 가능
- [ ] SC1004 역할 재분류 (F측 인터체인지인데 일반 도시부. 분류기가 커넥터 한 홉만 봄)
- [ ] 오늘 작업 커밋 (커밋 `a9777b2` 이후 미커밋분)

---

## 7. 다음 단계 — P-Stack 얹기 전 선행조건

현 단계가 끝나면 넘어간다. 시작 전에 아래를 확인할 것.

**게이트 (v6 재채점 기준 · v7 로 갱신 예정)**

| 지표 | 현재 | 임계 | 상태 |
|---|---:|---:|---|
| Spearman rho | +0.714 | 0.70 | 경계 통과 |
| top-action pairwise | 0.559 | 0.80 | **미달** |
| spillback F1 | 0.031 | 0.80 | **미달** (관측 양성 1건뿐) |

rho 만 넘겼다. **pairwise 가 실제 MPC 가 쓰는 지표**(1등만 고른다)이므로 이게 더 중요하다.

**P-Stack 고유 미해결 (오늘 조사에서 확인)**

- [ ] 한계가격이 여전히 순수 TTT 다. `price_far_enabled` · `price_hinge_enabled` 둘 다 False.
      후보 채점은 `TTT + far` 인데 가격은 `TTT` — **리더가 서로 다른 목적함수로 고르고 값을 매긴다.**
- [ ] 램프 한계가격 크기가 1e-7~1.5e-4 h2 로 own-TTS 스케일 대비 4자리 작다.
      수요 정합(3번) 이후 다시 재야 한다 — 이전 측정은 램프 수요가 3.4배 틀린 상태였다.
- [ ] `v5_tttfar` 이 SUP_PFO 를 껐다. 폐루프에서 폴백 없이 도는 것이 안전한지 미검증
      (기존 발화율 scale170 13/76, scale135 11/76).
- [ ] 가격 롤아웃 깊이 = `horizon_steps(3) + leader_value_depth(3)` = 360 초.
      G6 채점 지평 900 초와 불일치. far 가 이 격차를 메우는지는 오프라인으로 확인했으나
      (깊이 6 의 `+far` 는 깊이 15 의 순수 TTT 를 근사) 폐루프 검증은 없다.
- [ ] 폐루프 A/B 설계 — no-control 대비 P-Stack, 동일 수요·시드, TTT 개선율
