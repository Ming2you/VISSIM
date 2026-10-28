# 미터 옛 발견 정리 (INV_PRIOR) — 2026-10-24

질문(D-K9-73): "왜 미터가 작동 안 했나? codex 가 푸시한 옛 버전에서는 미터가 작동해 FW_E 가 10 % 넘게 좋아졌는데." 이 문서는 그중 **옛 발견 정리**만 맡습니다. 메모리·보고서에 적힌 미터 관련 발견 하나하나가 (1) 무엇을 주장했고 (2) 어느 코드·망 상태 이야기였고 (3) 나중에 고쳐졌는지 (4) V-A(c20aff1d) 의 "미터 늘 고정"을 설명할 수 있는지 봅니다.

**쉬운 요약**
1. V-A 의 미터 8개가 늘 녹색 10 s(= 늘 초록)였던 이유는 옛 발견 가운데 **결정층 발견들이 지금 코드에 그대로 살아 있기 때문**입니다. 미터 경로 코드는 K7(6c4c740)부터 c20aff1d 까지 바뀐 것이 미터 넘침 귀속(S1-OWN) 하나뿐이고, 그것도 녹색 10 에서는 쉽니다 [실행 git diff].
2. V-A 결정 기록을 J1 렌즈와 같은 방법으로 다시 뽑았습니다. 기준 녹색 1,320/1,320 이 10, 블록 0 허용 {8, 9, 10}, 조이는 쪽 기울기 0 / 0 / 2개(최대 8.8e-6), 걸음 최대 |z| 6.0e-4 / 1.39e-2 / 2.7e-3 (녹색 9 로 바뀌려면 0.05 필요), RM_C10681·RM_C10484 기울기 전부 0, NUF 상한 잔차 중앙 −100 / −103 / −104 veh/h(늘 여유) [실행]. J1 과 같은 모양입니다.
3. 옛 발견 중 V-A 에 그대로 해당하는 것: 상자 ±2 s·위끝 시작·근접 계수 10(09-24 obs150), 용량 강하 φ_cd 꺼짐(09-09·10-01·10-04), 후보가 수요 위(09-09 격자 사각지대와 같은 꼴), 간격 수용 노드가 FW_E B1 합류 미터 RM_C10681 의 도함수를 0 으로 만듦(09-27), 리더 가격 없음(09-09 "권한 ≠ 방아쇠"와 같은 꼴). 모두 **(a) 결정층**입니다.
4. **(b) 작동층**에 관한 옛 발견(09-06 "3단계 미터")은 옛 어댑터 경로 이야기이고, V-A 경로는 그 코드를 건너뜁니다. V-A 에서는 명령이 한 번도 10 아래로 가지 않아 작동층은 시험조차 되지 않았습니다 [읽음·실행].
5. **(c) 물리층** 옛 증거: v2 망 규칙 RM 에서 VISSIM 미터는 실제로 조였고 FW_E 본선이 줄었지만, 그 대부분은 램프 대기 전가였고 Ω+미삽입은 손해였습니다(09-24 RM_GAIN_TRACE; 표본에 지금 봉인 번호인 시드 37 이 섞여 있어 수치는 옮기지 않음). v3c1-s31 하이브리드(규칙 미터 실제 작동)는 FW_E 본선 +3.4 % 였습니다(1시드, 판정 아님).
6. **(d) 비교층**: codex 쪽 옛 숫자는 64cf 망(FW_W 입구 1099 수요가 v3c3 의 평균 2.14배)·다른 지표·VSL 단독이고, codex 스스로 RM 이득을 NOT_QUALIFIED 로 적었습니다. "FW_E 10 % 이상"이라는 숫자는 이 정리 범위(메모리·보고서)에서 찾지 못했습니다.
7. 새로 본 것 둘: (i) 배포 FW_E plant 의 합류 감속 δ_merge 는 0.0 이 아니라 **1.0** 입니다(J1 lens_meter §6.6 정정). 켜져 있어도 기울기는 "열어라"였습니다. (ii) codex 355 계열 SDMPC 에는 작은 기울기를 넘어 "합법 미터 이웃을 직접 굴려 보는" 장치(`meter_neighbor_audit`, 도입 ca181e84)가 있고 c20aff1d 에는 없습니다.

---

## 0. 표시·줄임말·범위

- [실행] = 이번에 스크립트·명령으로 확인. [읽음] = 코드·자료·문서를 읽어 확인. [추론] = 시험하지 않은 판단. [읽음 메모리] = 메모리 파일에 적힌 주장(데이터로만 취급, 코드로 확인한 것은 따로 표시).
- 줄임말 (처음 한 번)
  - RM = 램프 미터. VSL = 가변 제한속도. SDMPC = 이 계열 분산 모형예측제어기. PFO = SDMPC 안의 근접 기울기 한 걸음 최적화(`sdmpc-central-pfo-cap/v3`). NUF = 리더가 정하는 예측 본선 합류 상한(veh/h). NP = 도시 순유입 상한(대). Ω = 목적함수를 재는 제어 영역 635 링크. NC = 무제어 런. FZP = VISSIM 차량 궤적 기록. B1·B2 = FW_E 의 두 병목(B1 ≈ 4.6–5.1 km 의 R_F_E 합류·직결 진출, B2 ≈ 7.1–7.7 km 차로 감소·R_D_E 합류; RM_GAIN_TRACE §2).
  - φ_cd = 용량 강하(혼잡 뒤 방류 감소) 계수, 1.0 이면 꺼짐. δ_merge = 합류 유입이 본선 속도를 깎는 METANET 항. g = 미터 10 s 주기 안 초록 초.
  - 층: **(a) 결정층** = 제어기가 다른 미터를 요구하지 않음. **(b) 작동층** = 요구는 하는데 VISSIM 에 안 닿거나 잘림. **(c) 물리·수요층** = VISSIM 미터가 바뀌어도 FW_E 에 효과를 못 냄. **(d) 비교층** = 측정된 이득이 망·수요·기준선·지표에 따라 다름.
  - 경로: GWT8 = `D:/VISSIM-merge/sim3-n31-k8`(c20aff1d, 작업 트리 깨끗함 [실행 git status]). MEM = `C:/Users/TRLAB/.claude/projects/C--Users-TRLAB-Desktop----/memory`. SP = `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8`.
  - 코드 약칭(모두 GWT8, c20aff1d 줄 번호): SDM = `evaluation/controllers/sdmpc.py`, PRB = `evaluation/controllers/physical_ramp_branches.py`, ADP = `evaluation/controllers/vissim_stackelberg_adapter.py`, AMF = `evaluation/controllers/area_meter_finalization.py`, PLG = `evaluation/controllers/physical_lane_groups.py`, LFR = `evaluation/controllers/lane_freeway_runtime.py`, LPR = `evaluation/controllers/lane_plant_runtime.py`, CH = `diagnostics/demand_sweep/user_native_20260914/metanet_calibration_v1/canonical_harness.py`, PAR = `evaluation/parameters.json`, TUN = `diagnostics/sdmpc_n31_20260924/config_n31_v2.json`, REF = `diagnostics/sdmpc_n31_20260924/reference_config_n31_v2.json`, TOPO = `diagnostics/sdmpc_n31_20260924/scenario/topology_routes_v2_8ac6fd.json`, VBS = `scripts/run_real_world_stackelberg_controller.vbs`, VEN = `vendor/NumSim-mine/src`.
- 범위: 읽기 전용. VISSIM·COM·러너·동결·커밋·푸시·체크아웃 0. 결정·plant 재생 0. 이번에 돌린 것은 J1 렌즈의 추출 스크립트 두 개를 V-A 런 폴더로만 바꾼 사본(기존 joint.json 읽기, §2)뿐입니다. 봉인 시드(37/59/61/67) 자료 파일은 열지 않았습니다. codex 64cf-s59/s61/s67 수치는 쓰지 않았습니다.
- 시드 표기는 망 접두어를 붙입니다(v3c3-s31, v2-s31, v3c1-s31, 64cf-s29).

## 1. 코드 기준: V-A 미터 경로는 K7 때와 같다

| 확인 | 결과 | 근거 |
|---|---|---|
| c20aff1d 작업 트리 = V-A 동결본 | SDM·PRB·PAR·PLG·ADP·`area_follower_objective.py`·VBS·TUN 이 `D:/VISSIM-merge/frozen/sdmpc31_c20aff1d_202610230833` 과 sha256 같음(SDM 은 CRLF 변환 차만: 작업 트리 8f91298a… = 동결본) | [실행 sha256sum, git show] |
| J1 동결본 74cd495f → c20aff1d | SDM·PRB·PAR·PLG·ADP·AFO·`sdmpc_sequence.py` 변경 0. VBS(유지 장치)·TUN(K9-2 도시 키 `head_floor_seed`, `sc109w_through_saturation`, `runtime.decision_error_policy`)만 다름 | [실행 git diff --numstat; git diff TUN] |
| K7 6c4c740 → 74cd495f | 미터 관련 파일 중 SDM 만 +15/−2(K8-3 S1-OWN, `omega_costs` 의 미터 넘침 귀속) | [실행 git diff --stat] |
| K7 → c20aff1d 미터 설정 | TUN `actuation.real_world_ramp_metering`, `urban.physical_ramp_branches`, `freeway.physical_ramp_receiving_nodes`, `freeway.physical_ramp_head_service_veh_per_cycle`, `freeway.physical_ramp_capacity_vph` 모두 같음. PRB·PAR·PLG·TOPO·REF·`plant_n31_v2.json` diff 0 | [실행 python 비교, git diff --stat] |

→ 미터에 관한 한 V-A 는 K7·J1 과 같은 결정 코드·같은 plant 로 돌았습니다 [실행]. 그래서 K7·J1 때 확인된 발견은 V-A 에 그대로 옮겨 올 수 있는지 "코드가 같다"는 근거로 판단할 수 있습니다 [추론].

## 2. V-A 미터 결정 변수 (J1 렌즈 방법 그대로 다시 뽑음) [실행]

방법: `SP/j1/causes/meter_work/meter_extract.py`·`meter_extract2.py` 를 ROOT·RUNS·OUT 세 줄만 바꿔 `SP/rmcause/prior_work/` 에 복사하고 실행했습니다(BELOW_NORMAL, PYTHONHASHSEED=0, python -B, 각 약 3.4 분). 읽은 것은 `D:/VISSIM_runs/20261023_sdmpc31_k92/<런>/decisions_<런>/action_*.joint.json` 165개뿐입니다.

| 항목 | v3c3-s31 V-A | v3c3-s41 V-A | v3c3-s43 V-A | J1 (lens_meter, 같은 순서) |
|---|---|---|---|---|
| 결정 알고리즘 | sdmpc-central-pfo-cap/v3 55/55 | 55/55 | 55/55 | 같음 |
| 근접 계수 / 미터 미분 폭 | 10 / 2 s | 10 / 2 s | 10 / 2 s | 같음 |
| 기준 녹색 = 10 | 1,320/1,320 | 1,320/1,320 | 1,320/1,320 | 1,320/1,320 ×3 |
| 허용 집합 블록 0 / 1 / 2 | [8,9,10] / [6..10] / [4..10] (각 440) | 같음 | 같음 | 같음 |
| 블록 0 유효 기울기 n · 음 / ≈0 / 양 | 768 · 480 / 288 / 0 | 776 · 474 / 302 / 0 | 832 · 543 / 287 / 2 | 2,432 중 양 1 |
| 양(조이는 쪽) 최대 | 1.9e-17 | 1.2e-17 | 8.8e-6 (T=2550, RM_C10480) | 7.7e-5 |
| 기울기 중앙 | −0.0018 | −0.0013 | −0.0019 | −0.0013 ~ −0.0019 |
| RM_C10490 중앙 / 최소 | −0.291 / −1.164 | −0.145 / −1.283 | −0.191 / −1.578 | −0.155~−0.218 / −1.15~−1.34 |
| RM_C10681 · RM_C10484 \|g\|≤1e-9 | 96/96 · 96/96 | 97/97 · 97/97 | 104/104 · 104/104 | 전부 0 |
| 도시 녹색 축 \|g\| 중앙 (비교) | 0.460 | 0.418 | 0.458 | 0.42–0.47 |
| PFO 미터 걸음 최대 \|z\| (녹색 9 문턱 0.05) | 6.0e-4 | 1.39e-2 | 2.7e-3 | 2.2e-5 / 5.7e-3 / 4.4e-5 |
| 예측 합류 > 녹색 8 상한인 결정 | RM_C10490 4 | RM_C10490 4 | RM_C10490 5 | 1 / 4 / 3 |
| NUF 잔차 중앙 / 가장 빠듯 (veh/h) | −100.0 / −53.8 | −103.0 / −87.2 | −104.2 / −71.2 | −101.9~−103.3 / −72~−85 |
| NUF·NP 만족 | 55·55 | 55·55 | 55·55 | 165·165 |
| 중앙 듀얼 ≠0 결정 / 최대 \|듀얼\| | 5 / 0.048 | 7 / 0.066 | 9 / 0.188 | 10/10/1 · 0.10/4.04/0.0016 |

- 산출: `SP/rmcause/prior_work/meter_extract_va.json`, `meter_extract2_va.json` (sha256 §8).
- 읽는 법: 근접 QP 걸음은 d = −g/10 이고, 녹색 9 로 해독되려면 z < −0.05, 곧 g > 0.5 가 필요합니다(SDM:399-402 가장 가까운 허용 녹색, 같으면 기준 쪽) [읽음]. V-A 의 조이는 쪽 기울기는 최대 8.8e-6 으로 그 문턱의 약 1/57,000 입니다 [실행 계산]. 음의 기울기는 "더 열어라"인데 10 이 상자 위끝이라 걸음이 0 입니다 [읽음 SDM:338-345, :447-487].
- 결론: V-A 는 J1 렌즈 §9 의 "다섯 겹" 원인(상자·부호·크기·상한·가격) + 간격 노드를 같은 크기로 보입니다. **(a) 결정층에서 이미 10 이 나옵니다** [실행·추론].

## 3. 옛 발견 표

열: 발견 | 날짜·출처(그때 경로·망) | 주장한 기구 | 고쳐졌나 (커밋) | c20aff1d 에 아직 있나 (file:line) | V-A 미터 고정과의 관계 (층)

| # | 발견 | 날짜·출처 | 주장한 기구 | 고쳐졌나 (커밋) | c20aff1d 에 아직 있나 | V-A 관계 |
|---|---|---|---|---|---|---|
| P0 | J1 미터 렌즈 "다섯 겹" | 10-15, `SP/j1/causes/lens_meter.md`(5bca72ee…) + CAUSES r2 §1.8(0d86ead8…); J1 = FRZ_K8 74cd495f·FRZ_K8b b9734abe, v3c3 | ① ±2 s 상자 위끝 시작 ② 기울기 "열어라"/0 ③ 크기 < 문턱 0.5 ④ 녹색 8 상한도 예측 합류 위 ⑤ NUF 여유 ⑥ φ_cd 1.0; 10681·10484 는 간격 노드로 도함수 0 | 고친 적 없음. K9-2(V-A)도 미터 영역 무변경 | 예. SDM:338-345(상자), :399-402(해독), :571(기준 = 직전 실제 명령), :823(지역 QP 기울기); PAR:8 근접 10, :11 미분 폭 2, :25 NUF 여유 100; TOPO:35 `max_green_change_sec 2` [읽음] | **(a) 강.** §2 에서 V-A 수치로 같은 모양 확인 [실행] |
| P1 | 미터 가격 정확히 0 ("구조적으로 죽은 지렛대") | 09-09, MEM `vissim-metering-lever-structurally-dead.md`; n21/Ver2, 옛 GNE 어댑터 유한차분 가격 탐침 | 탐침 반경 max(300, 0.20×1800)=360 이 실측 램프 수요 428–571 을 못 가로질러 두 코너 롤아웃이 같음 → 가격 0 | 안 고침(수정 제안 trust 0.75 미반영). 경로가 바뀜: 물리 8미터(f61d95e4, 09-13) + SDMPC(884d1d1f, 09-22)는 AD 기울기 | 키는 남음: ADP:7652-7653 기본 0.20. V-A 결정은 55/55 `sdmpc-central-pfo-cap/v3`라 이 탐침을 안 씀 [실행 §2] | **(a) 모양만 같음**: 지금은 "가격 0" 대신 NUF 상한 늘 여유·듀얼 ≈0(§2). 원인 코드는 다름 [추론] |
| P2 | 용량 강하 φ_cd 꺼짐 | 09-09(같은 메모) · 10-01 MEM `vissim-terminal-cost-and-f10f11-20261001.md` · 10-04 MEM `freeway-plant-status-20261004.md` | φ<1 이면 임계 위 셀 송출이 φ·용량으로 깎여 "임계 아래로 지키는" 미터 이득이 생김. 꺼져 있으면 조여서 얻는 것 없음 | 안 고침. φ 0.85 팔 기각(+128.8 veh·h, n21, MEM `vissim-capdrop-refuted-merge-structural.md`). B2/B1 용량 강하 측정 판정 불가(9ed2ef02, 09-29: 사건 3개, 90 % CI [−45, 525] veh/h). RM_GAIN_TRACE §1 은 "용량 강하는 원인이 아니다"라고 적음(그 수치는 봉인 번호 시드가 섞인 표본이라 생략) | 예. PAR:65 `capacity_drop_discharge_phi 1.0`(REF·TUN 덮어쓰기 없음 [실행]); PLG:255-256 은 φ_cd≠1 이면 차로군 plant 를 거부; 적용 자리 `area_freeway_accounting.py:133, 213-216, 431-432` [읽음] | **(a) 강**: 모형에 조이는 이득 기구가 없어 기울기가 "열어라". 단 VISSIM 쪽 이득 기구도 용량 강하가 아니었다는 기록(RM_GAIN_TRACE §1)이 있어, φ 만 켜는 것은 옳은 기구가 아닐 수 있음 [추론] |
| P3 | FW_E 미터 후보 격자 사각지대 | 09-09, MEM `vissim-metering-grid-blindspot.md`; 옛 wu_faithful_follower 등예산 탐색 | 후보 7개가 모두 모형 방출 상한(available) 위 → 롤아웃 비트 동일 → FW_E 미터 결정에 이득 정보 없음 | 안 고침(격자 하한 수정은 제안만). 경로가 SDMPC 로 바뀜 | 옛 코드 남음: VEN/controllers/wu_faithful_follower.py:3629 `linspace(lo, hi, 7)` (V-A 경로 밖). 같은 꼴이 새 경로에 있음: 블록 0 {8,9,10} 서비스 상한(1차로 1,166.4–1,512, 2차로 2,332.8–3,024 veh/h; PRB:129, TUN:7524)이 예측 합류 위, 예외 RM_C10490 4/4/5결정 [실행 §2] | **(a) 강(꼴)**: "고를 수 있는 후보가 전부 수요 위" |
| P4 | 미터 작동은 사실상 3단계 {0, ≥600–1000, 열림} | 09-06, MEM `vissim-ramp-meter-actuation-is-binary.md`; 옛 어댑터(rate→커넥터 균등 분할→round(10·rate/900)). 09-23 정정: FW80/U90 v2 규칙(ALINEA) 경로 정확 통과 계수는 g2 = 360/차로, g3 ≈ 520, g4 ≈ 680 의 단조 다단계 | 부분 rate 는 열림으로 실현, 0 만 효과 | 옛 어댑터: `measured_table` 배분(09-06 h3). 물리 8미터 경로(f61d95e4)는 녹색을 직접 씀. K3 de5ff5fe(10-01) 서비스 표 정규화(RM_C10490 {0,2,4..10}) | V-A 경로는 옛 배분·`spillback_guard`(floor 1800)를 건너뜀: ADP:11347-11351, AMF:133-134, :176-181. 러너는 녹색만 씀: VBS:1006-1017 `RampStateAt`, 기본 녹색 10 VBS:624 [읽음] | **(b) 해당 없음**: V-A 명령은 늘 10 = 매초 GREEN, VISSIM 에서 NC3 의 "프로그램 없는 미터"와 FZP 동일(GB-6; lens_meter §3) [읽음]. 작동층은 시험되지 않음. **(c) 참고**: 09-23 규칙 경로에서 VISSIM 미터는 실제로 조였으나 일부 미터는 목표 점유에 한 번도 안 닿았고 순 제거 유량 ≈ 0, Ω 평균 악화라고 메모리가 적음(시드 표본에 봉인 번호 37 포함 — 개수·수치는 여기 안 옮김) |
| P5 | 용량 강하 기각 · δ_merge 는 구조 문제 | 09-09, MEM `vissim-capdrop-refuted-merge-structural.md`; n21 | δ=0.3 은 격자 상한에 붙은 값, 셀별 v_free 가 합류 감속을 이미 흡수. 모형 장부: R_F_E 완전 폐쇄 때 본선 절감 0.0225 대 램프 대가 4.98 veh·h | 31셀 재적합(v2 NC s31)에서 FW_E δ_merge = 1.0(P0 09-27: 상한에 붙음, F2 (c) 안 넣음) | 예, **켜져 있음**: `plant_n31_v2.json` → `.../boundary_literature_v1/boundary_fit/parameters.json:18` FW_E `delta_merge 1.0`(FW_W :10 = 0.0), LFR:28 이 CH:590-591 `_config` 로 적용(REF 에 `component_literature` 없음 → CH:594 이하 0 리셋 분기 안 탐) [읽음·실행]. PAR:66 의 0.0 은 덮어써지는 기본값 | **(a) 중**: δ 가 켜져 있는데도 V-A 기울기는 "열어라" → δ 1.0 은 조일 이유를 만들지 못함 [추론, §2 부호로]. **정정**: lens_meter §6.6 "metanet_delta_merge 0.0" 은 배포 FW_E plant 기준으로 틀림 |
| P6 | FW_E 붕괴 = OR_F_E 진출 차로 1 | 09-09, MEM `vissim-fwe-collapse-is-offramp-lane1.md`; n21 x15 | 동측 on-ramp 미터는 원인 아닌 곳을 겨눔(동측 램프 = 합류 방류의 9–12 %) | 09-27 v3b 재검증에서 기원으로서 기각 → 10681 2차로 합류의 차로 2 | 코드 문제 아님 | **(c) 중**: 옛 망 결론. v3c3 FW_E 혼잡 기원·미터 권한은 이 정리에서 재확인 안 함(INV_PHYSICS 몫) |
| P7 | FW_E plant 구조(v3b) | 09-27, MEM `vissim-fwe-plant-structure-20260927.md` | B1 본선 방류 제약 없음(+150 s 에 B1 차량 134 vs VISSIM 216), 셀 12 속도 인공물, 간격 수용 노드가 혼잡 롤아웃 스텝 73–88 % 구속, VSL 이득 = Carlson 용량 허구 | F1·F3·F4·B1 방류 제약 미구현(10-04 현황). K8·K9-1·K9-2 묶음 1 은 SA·도시 키(7ed49cdf W, 2d5d95f0 H-b)만 [읽음 git log] | 예. TUN:8105-8116 `physical_ramp_receiving_nodes` RM_C10681(3.0/2.0 s)·RM_C10484(2.5/2.5 s) [읽음] | **(a) 강**: RM_C10681 은 FW_E B1 쪽 10681 합류 미터인데 V-A 블록 0 기울기 96/97/104 개 전부 0 [실행 §2]. 모형 안에서 이 미터는 아무 일도 할 수 없음 |
| P8 | off-ramp 차로폐쇄(λ_eff) 방아쇠 굶음 | 09-09, MEM `vissim-offramp-lane-closure-trigger-starved.md`; n21. 09-27 v3b: 배포 프로필에서 꺼짐 | 저장고 점유 관측 0 → 차로폐쇄 미발동 | 안 켬 | 예(꺼짐): `diagnostics/sdmpc_n31_20260924/port_profile_v2/port_profile.json:2` `occupancy_lane_loss false` → LPR:478 [읽음] | **(a) 약**: 본선 용량 모형 이야기. 미터 축과 직접 연결 증거 없음 |
| P9 | 권한 ≠ 방아쇠, 본선 제약 → 노력이 도시로 | 09-09/10, MEM `vissim-freeway-constraint-shifts-effort-urban.md`; n21 | two-branch FD 로 VSL 권한이 생겨도 붕괴 창에서 안 씀 — 임계 초과가 목적함수에서 행동으로 번역 안 됨 | 진단만 | `vsl_fd_two_branch` 기본 꺼짐 VEN/models/metanet.py:61-65 [읽음] | **(a) 중(꼴)**: V-A 에서도 리더 압력 없음(NUF 늘 여유, §2) |
| P10 | RM 보정 1–3라운드 선택 단계 정지; S0e 미터 전부 열림 | 09-26, MEM `vissim-urban-batch1-and-rmcal-20260926.md`; v3b | 결정론 plant 로 시드별 혼잡 위치를 동시에 못 맞춤. S0e 에서도 미터 900(열림) | 4·5라운드 안 함(새 사전등록 필요라 기록) | 미터 서비스 표·간격 노드 값은 그때와 같음(K8 G-EB-9 바이트 동일; §1) | **(a)+(d) 중**: 미터 늘 열림은 v3b S0e·v2 V5b 때부터 있던 현상, V-A 고유 아님 [읽음 메모리] |
| P11 | 하이브리드 Carlson MTFC-VSL + ALINEA × 도시 SDMPC | 09-30, MEM `vissim-hybrid-rulefw-sdmpc-urban-20260930.md`; v3c1-s31 1시드, 9000 s | 규칙층 미터가 VISSIM 에서 실제로 움직임(ALINEA 10639 3600 s 부터 g2 고착). FW_E 본선 +72.2 veh·h(+3.4 %), Ω −186.5(−2.6 %) | 사용자 중단, 브랜치 92fa4b8 로컬만. 이식 안 함(de5ff5fe 커밋 본문 "not ported") | 코드 없음 | **(c)/(d) 중**: v3c 계열에서 VISSIM 미터가 실제로 조인 유일 기록에서 FW_E 는 좋아지지 않음(1시드, 판정 아님) [읽음 메모리] |
| P12 | terminal cost 로도 RM 이득 없음 | 10-01, MEM `vissim-terminal-cost-and-f10f11-20261001.md`; v3c1 R-obs 8상태 × 23후보 | RM 조임이 C00(조임 없음)을 한 번도 못 이김 — plant φ_cd 1.0. 종단비용 TC1 은 미터링을 오히려 손해로 교정 | 배포 안 함 | SDM·AFO·`control_area_objective.py`·TUN 에 terminal cost 키 grep 0건(PAR:113 `_note_far` 는 옛 리더 것) [실행 grep] | **(a) 중**: 지평 끝 가치를 더해도 조일 이유가 안 생겼다는 기록 |
| P13 | 고속도로 plant 현황(K7) — 축 휴면 | 10-04, MEM `freeway-plant-status-20261004.md`; K7 6c4c740, v3c3 | B1/B2 방류 제약 없음, 차로감소 φ 3.0 살아 있음, φ_cd 1.0, GB-9 반사실 7/7 VSL 110·미터 10 → 고속도로 축 사실상 휴면. VISSIM(v2)에는 B2 대기를 붙잡아 B1 방류를 늘리는 RM 기구가 있으나 순손실 | 안 고침(F2 φ0 승인됐으나 미구현) | 예. REF:7955 `lane_drop_phi 3.0`, PAR:65 φ_cd 1.0; 미터 경로 K7→c20aff1d diff 0(§1) [읽음·실행] | **(a) 강**: K7 부터 같은 행동이고 그 뒤 미터 경로 변경 없음 |
| P14 | "Ω 에선 미터 안 함이 맞다" (RM 이득 추적) | 09-24, MEM `vissim-sdmpc31-obs150-state-20260924.md` + GWT8 `diagnostics/sdmpc_n31_20260924/RM_GAIN_TRACE_20260924.md`(75f01515); v2 망, VISSIM 규칙 RM 3시드 + V5b 상태 plant 예측 | VISSIM: 규칙 RM 의 FW_E 본선 이득은 B2 대기를 차로감소 하류에 붙잡아 B1 결합을 끊는 기구 + 램프 대기 전가가 대부분, Ω+미삽입은 FW_W 10491 역류로 손해. plant: B1 이 풀려(상류 진입 용량 부족·출구/진출 과다 유출) 그 기구가 안 생김 → plant 의 "미터 안 함"은 Ω 판정으로는 VISSIM 과 같은 방향. 명령공간: ±2 s/150 s → 블록 0 {8,9,10}, 근접 10 이라 dJ/dz ≥ 0.5 필요, g2 도달 불가 | 안 고침. 선택지 a–e(B1 해소 원인·B2 위치·지연 이득·명령공간·FW_W 역류 비용) 미착수 | 예. TOPO:35, PAR:8, SDM:338-345, :399-402(문서의 `sdmpc.py:325-332` 는 지금 :338-345) [읽음] | **(a) 강 + (c)·(d) 강**: 결정층 원인 + "미터가 VISSIM FW_E 본선을 줄인" 우리 쪽 유일한 다시드 기록. 표본(v2-s31·s37·s41)에 지금 봉인 번호 37 이 섞여 있어 이 문서의 FW_E 수치·비율은 여기서 옮기지 않음 |
| P15 | codex 85e3454b(64cf, REVIEW1–171) 검토 | 10-04, MEM `codex-85e3454b-review-k8-20261004.md` | codex 결론 NOT_QUALIFIED: 물리 후보 약 60개 기각, RM 단독 예측 과소, "Ω 이득 = Ω 밖 이전" 패턴 | 선별 이식만(K1·K6 취지, 공통 결함 S1·S3·S5·S6 = K8) | 64cf 값·plant 는 없음 | **(d) 강**: codex 쪽도 RM 이득을 자격 없음으로 적음. 수치는 어느 시드인지 메모리에 없어 옮기지 않음 |
| P16 | codex 355(ffa4861e) 대조 | 10-13, MEM `codex-355-handoff-compare-20261013.md` + `SP/cmp355/COMPARE_355_K8.md`(9cae27d9…) | 64cf 망: FW_W 입구 1099 수요가 v3c3 의 1.84–2.27배(평균 2.14배), 정적 경로 31–32개 차이, 64cf-s29 1시드·8100 s·Ω701, converged false → 숫자 비교 불가. 355 는 RM 녹색 0 금지, 간격 노드 4개(10639·10681·10490·10484) | 병합 안 함(K9-1 판정 무효 위험) | c20aff1d 에 `meter_neighbor_audit`·`meter_activation_secant` 0건 [실행 grep]. 355 트리 `D:/VISSIM-merge/sim3-handoff355/evaluation/controllers/sdmpc.py:135, :205-206, :605-738`(유한 합법 RM 이웃 검사), 도입 커밋 ca181e84(10-06) [실행 grep·git log -S] | **(a)+(d) 강**: 355 결정층에는 "기울기가 작아도 합법 미터 이웃을 직접 평가"하는 장치가 있음 → 같은 plant 라도 미터가 움직일 수 있는 결정층 차이 [추론, 시험 안 함]. 망·수요가 달라 숫자 비교 불가 |
| P17 | codex expanded036 동측 159계수 | 09-30, MEM `codex-expanded036-review-20260930.md`; 64cf, VSL Carlson A0.5/E2 | NOT_GAIN_QUALIFIED, seed43 순위 개선 없음; 계수가 우리 구조 결함을 보상하는 모양 | 값 불채택, 31셀 분할만 같음 | 해당 없음 | **(d) 중** |
| P18 | codex VSL90 인계 재현 | 09-24, MEM `vissim-vsl-handoff-repro-20260924.md`; 64cf-s29 | **VSL** 90 단독, 지표 ② 동측 국소 19링크 −6.1531 %, ④ 전체+외부 −0.2721 %. 같은 이름 우리 fix90(v2-s31)은 +358.8 veh·h | – | – | **(d) 중**: codex 쪽 "동측 %" 숫자는 VSL·지표 ②·64cf 기준. 미터 이야기 아님 [읽음 메모리] |
| P19 | density_penalty 가 램프를 닫음 | 09-05, MEM `vissim-density-penalty-closes-ramps.md`; 옛 Stackelberg 리더 | 리더 밀도 벌점(w_F 3.0)이 TTT 가 나쁜 미터 폐쇄를 채택(하한 1440 으로 "쾅", 결정당 +1200 기어오름). 가드 `min_ttt_gain_frac` 0. 강제 전개방은 오히려 +1,289 → 미터는 비인과 | 안 고침, 경로 교체 | 옛 코드 남음: VEN/models/state.py:722 기본 0.0, VEN/controllers/stackelberg_mpc.py:1691. SDMPC 의 NUF 상한은 "PFO 달성 + 100"(PAR:25) [읽음] | **(a)/(d) 중**: "예전엔 미터가 움직였다"의 한 가지 출처일 수 있음. 그때 움직임은 리더 벌점·듀얼 때문의 폐쇄였고 이득이 아니었음 [추론] |
| P20 | 램프 cap 수정이 듀얼로 증폭 | 09-04, MEM `vissim-ramp-cap-dual-amplification.md`; 옛 GNE λ_P | `ramp_queue_max` 0→111/153 이 nin 유출항을 살려 λ_P 가 17신호로 퍼지고 리더가 미터를 하한으로 닫음. 본선은 무변화(당시 δ_merge 0) | 안 고침, 경로 교체 | SDMPC 중앙 듀얼은 V-A 에서 거의 0(최대 0.048/0.066/0.188, §2) | **(a) 약**: V-A 에는 이 증폭 경로가 없음 |
| P21 | K8-3 S1·S1-OWN(미터 앞 저장 차용 금지, 넘침 비용을 미터 주인에) | 10-05, 91bfa56e; MEM `codex-85e3454b-review-k8-20261004.md` | 미터가 수요보다 적게 내보낼 때만 작동 | 구현됨(91bfa56e) | SDM `omega_costs`(K7 대비 +15/−2) [실행 git diff] | **(a) 없음**: 녹색 10 에서 쉼(lens_meter §7) [읽음] |
| P22 | K3 미터 서비스 표 정규화 | 10-01, de5ff5fe | RM_C10490 녹색 2·3 같은 서비스 → 3 제거 | 구현됨 | PRB 정규화 | **(a) 없음**: 녹색 10 근처와 무관 |

## 4. 층별 정리

**(a) 결정층 — 지금 V-A 미터 고정의 원인으로 살아 있는 옛 발견**
- P0·P14: 상자 ±2 s, 기준 = 직전 실제 명령 10, 근접 10 → 녹색 9 로 가려면 조이는 쪽 기울기 > 0.5 필요. V-A 최대 8.8e-6 [실행]. 그래서 한 번도 내려가지 않고, 내려가지 않으니 다음 결정도 10 에서 시작합니다(자기 유지) [추론].
- P2·P12·P13: plant 에 조여서 얻는 이득 기구(용량 강하, B1 방류 제약)가 없음. 램프 재고는 FW 소유자 Ω 비용에 들어가므로(SDM:248) 조이면 비용만 늘어 기울기 부호가 "열어라" [읽음·추론].
- P7: FW_E B1 쪽 미터 RM_C10681(과 RM_C10484)은 간격 수용 노드 때문에 도함수가 정확히 0 [실행 §2].
- P3·P9·P1(꼴): 블록 0 후보 상한이 예측 합류 위, NUF 상한 늘 여유(잔차 중앙 −100~−104 veh/h), 듀얼 ≈ 0 → 리더도 조이라고 하지 않음 [실행].
- P5: δ_merge 1.0 이 켜져 있어도 위 결과는 그대로 [실행·읽음].
- 이 가운데 c20aff1d 까지 고쳐진 것은 없습니다. K7→c20aff1d 미터 경로 변경은 S1-OWN 하나이고 녹색 10 에서는 쉽니다 [실행 §1].

**(b) 작동층 — 원인 아님(시험되지 않음)**
- 옛 "3단계 미터"(P4)는 옛 어댑터 경로 이야기입니다. V-A 경로는 그 배분·`spillback_guard` 를 건너뛰고(ADP:11347-11351, AMF:133-134·176-181) 녹색을 그대로 러너에 줍니다 [읽음].
- V-A 61회 × 8미터 모두 rate 900 · green 10 이 써졌고(VA_REPORT_r2 §7, `SP/k92/va/analysis/VA_REPORT_r2.md:558-571`), green 10 은 매초 GREEN(VBS:1006-1017)이며 VISSIM 에서 "미터 없음"과 FZP 가 같습니다(GB-6, lens_meter §3) [읽음]. 요구가 없으니 잘림도 없습니다.

**(c) 물리·수요층 — 옛 증거는 "미터가 움직여도 FW_E 이득은 조건부"**
- v2 망 규칙 RM(P14): VISSIM 에 B2–B1 결합을 끊는 실제 기구가 있었지만 이득의 대부분이 램프 대기 전가였고 Ω+미삽입은 손해(FW_W 10491 역류) [읽음 RM_GAIN_TRACE §1-2].
- v2 규칙 경로 정확 통과(P4 09-23): 일부 미터는 늘 열림(목표 점유 미도달), 조인 미터도 순 제거 ≈ 0 [읽음 메모리; 표본에 봉인 번호 포함이라 개수 생략].
- v3c1-s31 하이브리드(P11): 규칙 미터가 실제 조였는데 FW_E 본선 +3.4 % [읽음 메모리].
- v3c3 FW80 에서 VISSIM 미터가 FW_E 를 줄일 수 있는지는 옛 기록에 직접 증거가 없습니다(v3c3 RM 팔 런은 같은 rmcause LOG 33행 기록대로 결과를 열지 않는 관행) [읽음 LOG; 판단은 INV_PHYSICS 몫].

**(d) 비교층 — "FW_E 10 % 이상" 숫자의 출처는 이 정리에서 못 찾음**
- codex 쪽 옛 자료는 모두 64cf 망(FW_W 입구 1099 수요가 v3c3 의 평균 2.14배, P16)이고, 동측 % 숫자는 VSL 단독·지표 ②(P18), codex 스스로 RM/VSL 이득 NOT_QUALIFIED(P15, P17; GWT8 `docs/HANDOFF_20260921_gain_prediction.md:1-30` 도 같은 판정) [읽음].
- 크기 감: v3c3 NC3 fw_e_main(7링크)은 1,816.6 / 1,963.8 / 1,876.5 veh·h 이므로 10 % 는 약 182 / 196 / 188 veh·h 입니다. V-A − NC3 는 −12.3 / −72.6 / −5.3 veh·h(−0.7 / −3.7 / −0.3 %) [읽음 VA_REPORT_r2.md:378; 실행 계산]. 지표 정의가 다른 숫자(②, Ω, ④, 64cf)와 섞어 비교하면 안 됩니다(P18).
- P14 의 v2 규칙 RM FW_E 본선 이득이 사용자가 기억하는 숫자와 같은 출처인지는 확인하지 못했습니다(봉인 번호 시드가 섞여 비율을 계산하지 않음).

## 5. 정정·새로 본 것

1. **δ_merge**: 배포 FW_E plant 는 1.0(FW_W 0.0)입니다. 근거 = `plant_n31_v2.json` sources.parameters → `boundary_fit/parameters.json:10,18`, LFR:28 → CH:590-591. J1 lens_meter §6.6 의 "metanet_delta_merge 0.0"(PAR:66 기본값)은 배포 plant 기준으로 틀립니다 [읽음]. 결론(기울기 "열어라")은 바뀌지 않습니다 [실행 §2].
2. **줄 번호 이동**: obs150 메모·RM_GAIN_TRACE §4 의 `sdmpc.py:325-332` 는 c20aff1d 에서 SDM:338-345 입니다. lens_meter 의 VBS 줄 번호(FRZ_K8)는 c20aff1d 에서 `RampStateAt` 1006, 기본 녹색 624 입니다 [읽음].
3. **차로군 plant**: TUN:8119 `physical_mainline_lane_groups: true` 이고 LFR:36-38 은 관측에 `lane_group_dynamics` 가 있는 도로에만 PLG 를 만듭니다("서측 본선은 집계 유지" 주석). 메모리 `freeway-plant-status-20261004.md` 의 "31셀 집계 METANET(차로 구분 없음)"과 다를 수 있습니다. V-A 런에서 FW_E 가 실제로 PLG 로 돌았는지는 확인하지 않았습니다 [읽음, 미확인].
4. **codex 355 결정층 장치**: `meter_neighbor_audit`(유한 합법 RM 이웃 + 이로운 이웃 조합 하나 평가)와 `meter_activation_secant` 가 355 계열에 있고(ca181e84, 10-06), c20aff1d 에는 없습니다 [실행]. 이 장치가 v3c3 plant 에서 미터를 움직이게 하는지는 재생 없이는 모릅니다.

## 6. 열린 질문

1. 사용자가 기억하는 "codex 버전에서 미터가 작동해 FW_E 10 % 이상"의 정확한 커밋·런·지표·시드는 무엇인가? 이 정리 범위(메모리·보고서)에는 그런 숫자가 없습니다. 후보: (가) 09-21 codex 인계(`docs/HANDOFF_20260921_gain_prediction.md`, NOT_QUALIFIED), (나) 355 계열의 `meter_neighbor_audit` 이후 런(ca181e84 이후), (다) v2 규칙 RM(RM_GAIN_TRACE; 봉인 번호 포함). INV_CODEX 결과와 맞춰 봐야 합니다.
2. (a) 결정층 원인을 하나씩 풀면 어디서 미터가 움직이기 시작하는가? 예: 상자 확대·근접 계수·유한 이웃 검사(355식). 오프라인 결정 재생이 필요하고 이번에는 하지 않았습니다.
3. 결정층을 풀어 미터가 움직여도 plant 가 "조이면 손해"(P2·P7·P14)라면 다시 열림을 고를 것입니다 [추론]. 이득 기구(B1 방류 제약, B2–B1 결합, 용량 강하)를 plant 에 넣을지는 K9-2 범위 결정입니다.
4. v3c3 FW80 수요에서 VISSIM 미터가 FW_E 를 줄일 물리 여지가 있는가? (INV_PHYSICS 몫; v3c3 RM 팔 결과는 관행상 닫혀 있음.)
5. V-A 에서 FW_E 가 차로군 plant(PLG)로 돌았는가(§5-3)? φ_cd 를 바꾸는 수정은 PLG:255-256 거부와 부딪힙니다.

## 7. 하지 않은 것

- VISSIM·COM·러너·동결·커밋·푸시·체크아웃 0. 결정·plant 재생 0. 새 워크트리 0. kill 0(추출 두 개는 정상 종료, 남은 프로세스 없음).
- 봉인 시드 37/59/61/67 자료 파일 열지 않음. RM_GAIN_TRACE·RM_SEED_SWEEP 처럼 이미 쓰인 문서가 v2-s37 을 포함한 평균을 적은 경우, 그 수치·비율은 옮기지 않음. codex 64cf-s59/s61/s67 수치 0. 85e3454b·expanded036 수치는 어느 시드인지 메모리에 없어 옮기지 않음.
- v3c3 RM 팔(s31/s41_v3c3rm) 결과 열지 않음.

## 8. 파일·재현

| 파일 | sha256 |
|---|---|
| `SP/rmcause/prior_work/meter_extract_va.py` (`SP/j1/causes/meter_work/meter_extract.py` 2eba40f4… 에서 ROOT·RUNS·OUT·설명 줄만 바꿈) | 5574c0c2d017025a4fab2ae4910912f3cbe04b835cdbafe266dafbe75cebfe16 |
| `SP/rmcause/prior_work/meter_extract2_va.py` (`meter_extract2.py` 에서 ROOT·RUNS·OUT 만 바꿈) | 1a879964318c4147b7a93a7f7aa15941e33f3c1590703c1102abedfa3ed39e60 |
| `SP/rmcause/prior_work/meter_extract_va.json` | a50974d7520472e49a02038261280cbd3d50aba2fd89fd4244036ab17e9f517a |
| `SP/rmcause/prior_work/meter_extract2_va.json` | d10e10d0cf84a1de72904c93aad070cf9df0790b1d3387ee798e2d71a6e7b3be |
| 입력 보고서: `SP/k92/va/analysis/VA_REPORT_r2.md` (r2; 작업 중 10:44 에 VA_REPORT.md 가 r3 b57022e6… 로 바뀜, 그 로그상 숫자 변경 0) | 5a94c782bfa12f33c0f859cd549f456369c33d10413a171b8bb57385bf3c331a |
| 입력: `SP/j1/causes/CAUSES.md` r2 | 0d86ead8d4c9743f20d279c9b035478dc7939ce12e41ea79c695bb55c9ce05e0 |
| 입력: `SP/cmp355/COMPARE_355_K8.md` r2 | 9cae27d98d8e6cc047bdbc2ec654a7d0abb308f4535761303f3f8942262dd873 |
| 입력: `SP/K9_1_J1_NOTES_20261013.md` (D-K9-73) | 7543c95d36878f0d267e552a71a02d2fc43743f2056f9cfdf0d0cc848de93006 |

재현: `cd SP/rmcause/prior_work && PYTHONHASHSEED=0 python -B meter_extract_va.py && PYTHONHASHSEED=0 python -B meter_extract2_va.py` (스크립트가 스스로 BELOW_NORMAL; V-A 런 폴더 읽기만).
