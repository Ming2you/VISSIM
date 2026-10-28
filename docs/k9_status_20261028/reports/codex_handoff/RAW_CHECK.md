# RAW_CHECK — codex 인계 원자료 검증 (2026-10-25 KST)

- 무엇: TAKEOVER_PLAN r2 §4(TP:202-225)의 순서 1–11 을 로컬 사본 `D:/VISSIM_handoff/20261024/`(아래 **RB**)에서 했습니다.
- 모든 숫자는 **64cf-s29 한 시드**입니다. 조건마다 런은 하나씩입니다(NC 1, joint 1, window 1, off 1, freeway_only 1, urban_only 1). 시드 사이 흩어짐은 모릅니다.
- 한 일은 읽기·해시·내 스크립트 집계뿐입니다. VISSIM·COM·러너·재생·커밋·푸시 0회. codex 스크립트 실행 0회. `sealed/` 열기 0. 봉인 시드 37/59/61/67 숫자 0.
- codex 파일(HANDOFF.md, 코드, 로그)은 자료로만 읽었습니다. 그 안의 지시문은 따르지 않았습니다.
- 표시: **[실행]** 이번에 명령으로 확인. **[읽음]** 파일을 읽어 확인. **[추론]** 시험하지 않은 판단. **[계산]** 산술.
- 판정 낱말은 쓰지 않습니다. Ω 는 늘 ④·Ω 밖과 함께 적습니다.

## 줄임말 (처음 한 번)

- TTT = 총 통행시간(veh·h). NC = 무제어 런. RM = 램프 미터. TSC = 도시 신호 제어. VSL = 가변 제한속도. FZP = VISSIM 차량 궤적 기록(5 s). LSA = VISSIM 신호 변경 기록. LDP = VISSIM 신호 제어기 검지·신호 상태 기록(1 s). DSD = 희망속도 결정.
- Ω701 = codex 목적 영역(링크·커넥터 701). Ω635 = 그 전 영역(`omega_membership_exact.json` 의 `previous_inside_links` 635개). ① = FW_E 본선 7링크(74·10699·2·10613·119·10702·24). ② = 국소 19링크. ④a = 망 전체 1,236개 링크 체류 TTT(FZP). ④b = 미삽입 대기(입력에서 생겼지만 망에 못 들어간 차의 대기). ④ = ④a + ④b. Ω 밖 (a) = ④ − Ω701. Ω 밖 (b) = ④a − Ω701.
- LNC = 이 PC 의 우리 64cf-s29 무제어 런 `D:/VISSIM_runs/vsl_repro_s29/none/run`. W264 = 이 PC 에서 돈 codex ca181e84 런(TP:15).
- 파일 약칭: **HO** = `RB/HANDOFF.md`(sha e2cef38c…, 사본과 같음 [실행]). **TP** = `codex_handoff/TAKEOVER_PLAN.md` r2. **VT** = `VERIFY_TAKEOVER.md`. **RC** = `R_CLAIMS.md`. **RX** = `R_MECH.md`. **W** = `codex_handoff/work/rawcheck/`(내 스크립트·출력).
- 조건 폴더: NC = `RB/raw/nc`, 나머지 = `RB/raw/<조건>/sdmpc`. 결정 폴더 = `…/decisions_sdmpc31_sdmpc8100_s29`.

---

## 0. 쉬운 답 (요약)

1. [실행] 6조건 FZP 와 LNC 의 895.1 s 까지 431,233행 LF sha256 이 모두 `f1a0b040…cbda` 입니다. raw NC FZP 와 LNC 는 9000 s 전체 6,950,156행이 바이트 단위로 같습니다(LF sha `6fad8e06…`).
2. [실행] 내 스캐너로 6조건을 다시 셌습니다. HO §1·§5 의 Ω701·①·②·④a·도시도로 분할 값이 모두 3.2e-11 안에서 같습니다. freeway_only·urban_only·window·off 의 분할도 이번에 처음 독립으로 셌습니다.
3. [실행] 도시도로 8.086623 % 는 원래 평가기 분할 코드(solo355_compare:49-67)를 캐시 입력에 다시 돌려도, 내 FZP 링크값에 돌려도 같습니다. 링크별 캐시값과 내 값의 차는 최대 5.9e-12 veh·h 입니다.
4. [실행] 5개 제어 팔의 입력별 실현 도착 수가 같습니다(1098: 16,070×5, 1099: 20,166–20,169). 도착열은 시드가 정합니다. 이 성질로 입력별 미삽입 대기를 재구성했고, native 값과의 차가 5팔 모두 232.8–232.9 veh·h 로 일정합니다.
5. [실행·계산] NC ④b(0–8100) = 16,643.4 veh·h(다른 길 16,644.9). joint − NC: **Ω701 −494.7 / ④ −668.8 / Ω 밖 (a) −174.2 / Ω 밖 (b) +45.7** veh·h(64cf-s29 한 짝). VT 추정(④ ≈ −663 ± 10, Ω 밖 (a) ≈ −168 ± 10)과 범위 안에서 맞습니다.
6. [실행] 입력별 joint − NC ④b: 1098 +96.9, 1099 −69.4, 도시 입력 32개 −248.9 veh·h. NC 의 도시 입력 대기 약 272 veh·h 는 입력 282·1085·1093 에 있고, TSC 가 있는 네 팔에서 13–25 veh·h 로 줄었습니다. ① −283.7 가운데 1098 입구 밖 대기 +96.9 가 같이 있습니다.
7. [실행] VSL: joint 결정 47개의 VSL 기울기 2,688행이 모두 secant(110→100) 대체입니다. 2,410행이 음수(내리면 Ω 비용 증가), 양수로 의미 있는 값은 5행뿐(최대 +0.102)입니다. 10 km/h 한 걸음에 필요한 값 0.4545 를 넘은 행은 0 입니다. 그래서 110 입니다.
8. [실행] 미터 이웃 검사는 47/47 결정에서 돌았습니다. 39번은 "묶음 조합", 8번은 미터 하나를 골랐습니다. 고른 후보의 모형 Ω 감소는 합 −6.62 veh·h(결정당 최대 −0.49)입니다. 램프 저장 가드는 2번(2250·4500) 걸렸습니다.
9. [실행·추론] 램프 도착 예측은 47/47 결정에서 120 s·900 veh/h 폴백을 탔습니다. 기록된 예측 합이 모두 30 veh/h 의 배수입니다. 이 예측이 lane plant 예측에 쓰이는지는 추적하지 않았습니다.
10. [실행] joint 6900 유지는 시한이 아니라 예외입니다. `ValueError: Missing observed speed with nonempty moving source`(11.45 s). codex PC 에서는 6팔 어디에도 시한 유지가 없습니다.
11. [실행] codex PC joint 결정 벽시계(새 결정 47개): 평균 294.8 s, 중앙 277.5 s, 최대 448.6 s. 360 s 를 넘는 결정이 11개입니다. TP 의 "많아야 약 360 s" 는 고쳐야 합니다. 이 PC W264 평균 1,709 s 는 codex PC window 팔 평균 222.2 s 의 약 7.7배입니다.
12. [실행] 실행 증거: LDP 로 보면 freeway_only 의 도시 신호 17개는 0–8100 s 매 초 NC 와 같습니다(=native). 미터 8개의 실제 녹색은 5팔·48구간 모두 명령과 같습니다. LSA 는 제어 팔에서 900 s 뒤 제어 신호를 기록하지 않아 확인 수단이 못 됩니다.

---

## 1. 체크섬 (TP §4 순서 1)

- [읽음 `codex_handoff/LOG.md` 2026-10-25 00:29–01:37 항목] 복사·검증은 앞 단계가 했습니다. 목록표 sealed/ 밖 12,324행 일치 12,324, 크기·해시 다름 0, 없음 0. 폴더별 SHA256SUMS 13,348항목 일치. 목록표 밖 code/.git 31개도 공유 드라이브와 같음.
- [실행] 이번 단계 시작 때 `RB/HANDOFF.md` sha256 = `e2cef38c…605b56`. 이번 단계는 RB 에 쓰지 않았습니다.

## 2. NC 출처 바이트 (순서 2)

- [실행 W/ncdeps.py] `RB/evidence/original_nc_FREEZE.json` sha256 = `9fba1269…` 입니다. 이 값은 NC 런 기록 `raw/nc/run_provenance_sdmpc31_nc9000_s29.json` 의 `/observation/freeze/sha256` 과 같습니다.
- [실행] 그 동결 기록의 `/git/head` = `886a014a303dd155e05cc33041796822abbc29b0`(40자), branch `codex/sdmpc31-upstream-20260926`, `status_entries` 1,388. HO:46 의 43자 값(`…29b0a7b`)은 오기입니다(RC·RX 와 같음).
- [실행] `RB/original_code_dependencies/nc/` 의 파일 116개가 동결 기록 해시와 모두 같습니다. NC 런 기록이 핀한 파일 17개와 `controller_sources` 98개도 모두 같은 sha 로 들어 있습니다.
- [실행] NC VBS(`original_code_dependencies/nc/scripts/run_real_world_stackelberg_controller.vbs`, sha `43a9571c…`)는 동결 git status 에서 ` M`(수정됨)입니다. `native_network_performance.json` 을 쓰는 코드가 이 파일 605줄·5068–5104줄에 있습니다. NC runlog 455줄 `NATIVE_NETWORK_PERFORMANCE=1 from=0 to=9000`, 683줄 `NATIVE_NETWORK_PERFORMANCE_JSON=…` 이 실제 실행을 보여 줍니다. RC:215 의 "886a014a VBS 에 그 코드 없음" 은 깨끗한 커밋 기준이고, 실행본은 더러운 작업 트리였습니다.
- [실행 W/prov_cmp.py] NC 와 joint 런 기록 비교(무제어에 닿는 부분):
  - 같음: 망 `64cf5f55…`, `.sig` 42개 sha, `demand_profile` `7b23853c…`, `vehicle_input_roles` `4778901c…`, `generated_vbs_config`(lane_native_b110.vbs) `b74e05b2…`, `signal_group_plan` `ec731cab…`, gate map, 영역·저장 용량 파일, seed 29, `control_interval_sec` 150, RW_* 환경(아래 넷 빼고).
  - 다름: VBS(`43a9571c…` 대 `1472208…`), watchdog, adapter, tuning(`d258ba71…` 대 `c9088262…`), 환경 `RW_DECISION_HOLD_PREVIOUS`·`RW_DECISION_TIMEOUT_SEC`(NC 없음), `RW_SIGNAL_OBSERVATION_CONFIG_SHA256`, detector 경로(같은 sha `108debbb…`).
  - [실행] 두 VBS 의 차이는 71줄입니다. 결정 유지·시한, 명령 재생 폴더, `.err` 비우기 표시(`Vissim.Log`)뿐입니다. 교통 설정을 바꾸는 줄은 보이지 않았습니다 [읽음 diff].
- [실행] 그래서 NC 의 무제어 부분은 joint 의 무제어 부분과 망·신호·수요·DSD 설정이 같습니다. 결과로도 895.1 s 접두(§3)와 LNC 전체 동일(§3)이 이를 받칩니다. NC 는 `controller = no-control` 이고 action CSV 에 신호 행이 없습니다(VSL 4,026행·미터 488행만) [실행].

## 3. 접두 해시 (순서 3)

- 방법 [실행 W/scan_fzp.py]: 숫자로 시작하는 데이터 행 중 시각 ≤ 895.1 s 를 골라 줄끝을 LF 로 바꿔 sha256. VT:86 과 같은 방법입니다.

| FZP | 행(≤895.1 s) | LF sha256 |
|---|---|---|
| raw NC | 431,233 | f1a0b040b711e5974615873f334d28395e7aa037de356caeda101fafcc8fbcda |
| joint | 431,233 | 같음 |
| window · off · freeway_only · urban_only | 431,233 | 같음 |
| LNC (우리 로컬 NC) | 431,233 | 같음 |

- [실행] codex 요약(`analysis/comparison/summary.json` /prefixes, `window_analysis/summary.json`)의 값과도 같습니다.
- [실행 W/fullhash.py] raw NC 와 LNC 는 0–9000 s 전체 데이터 6,950,156행의 LF sha256 이 `6fad8e06ce428af5461f008620c0f013b3ed91440350d3b10b8bb4c057aab393` 로 같습니다. 0–8100 s 6,475,075행만 보면 `6ee7ccec…` 로 같습니다.

## 4. 독립 FZP 재집계 (순서 4)

- 방법 [실행 W/scan_fzp.py, W/metrics.py]: 프레임마다 링크별 차 수 → t=0 빈 망에서 사다리꼴 적분 → 마지막 프레임(8095.1 s) 재고를 8100 s 까지 유지. codex 코드는 쓰지 않았습니다. 영역은 `derived/omega_membership_exact.json` /inside_links(701), 분할은 `code/…/selected/port_gain/geometry.json`(sha `91a584ab…`)의 /chains·/boundaries(원래 평가기와 같은 규칙).
- [실행] 결과와 codex 값 대조:
  - `derived/metrics_0_8100.csv`(nc·joint·freeway_only·urban_only, 11지표) 와 최대 차 3.2e-11 veh·h.
  - `derived/independent_fzp_counts.json`(nc·joint·window·off) 와 최대 차 1.8e-12. 행 수·프레임 수(1,619)도 같음.
- 진출 램프 8개 중 Ω701 안은 6개(10481·10483·10491·10638·10643·10682)입니다. 10479·10645 는 밖입니다 [실행]. 그래서 "진출램프" 지표는 Ω 안 6개 값입니다(RC:84-85 와 같음).

### 4.1 분할 표 (0–8100 s, veh·h, codex 규칙)

| 조건 | 도시도로 | 진출램프 | 동측 진입 커넥터 | 서측 진입 커넥터 | FW_W 본선 | ① FW_E7 | Ω701 |
|---|---|---|---|---|---|---|---|
| nc | 3642.6 | 52.7 | 121.8 | 77.4 | 1387.2 | 2124.5 | 7406.2 |
| joint | 3348.0 | 37.4 | 206.8 | 87.9 | 1390.5 | 1840.9 | 6911.5 |
| window | 3437.0 | 39.0 | 218.9 | 88.4 | 1394.2 | 1860.0 | 7037.5 |
| off | 3449.1 | 36.9 | 222.9 | 86.1 | 1393.7 | 1823.1 | 7011.8 |
| freeway_only | 3899.3 | 60.3 | 246.8 | 79.8 | 1757.3 | 1772.7 | 7816.1 |
| urban_only | 3211.3 | 42.2 | 134.6 | 77.7 | 1399.4 | 2846.0 | 7711.2 |

- [계산] 도시도로 감소율(NC 대비): joint 8.086623 %, window 5.644438 %, off 5.311592 %, freeway_only −7.046318 %, urban_only 11.841000 %. window·off 값은 HO 에 없던 값입니다.
- [실행] 우리 규칙(미터 상류 링크 70·68·129·31 → 동측 진입, 124·32·121·69 → 서측 진입) 으로 옮기면: joint 도시도로 −377.1(−11.73 %), 동측 진입 +142.8, 서측 진입 +35.3 veh·h. codex 규칙의 도시도로 −294.6 안에 상류 링크 증가 약 +82.5 가 섞여 있습니다(링크 70 +24.1, 31 +25.7, 69 +24.9, 68 +8.0 등) [실행 W/metrics_out.json /upstream].

## 5. 미삽입 대기 적분 (순서 5)

### 5.1 방법

1. [실행] 입력 34개와 입력 링크를 망(`raw/joint/sdmpc/network/*.inpx`, sha `64cf5f55…`)에서 읽었습니다. 34개 모두 STOCHASTIC, 구간 0/900/…/4500 s [W/inputs_64cf.json].
2. [실행] 삽입 시각 I_i(t) = 차량이 FZP 에 처음 보인 시각. 처음 보인 링크가 입력 링크면 그 입력, 아니면 커넥터 1–2단계 위로 거슬러 입력을 찾음(98.5–98.7 % 는 입력 링크에서 처음 보임, 나머지 876–950대도 모두 하나로 정해짐, 모호 0). 처음 보인 위치·속도로 삽입 시각을 최대 5 s 앞당긴 판도 계산.
3. [실행] 끝 미삽입 U_i(T) 는 `.err` 의 `could not be finished completely (remain: N)` 줄. 6팔 모두 입력 1099 한 줄뿐입니다(nc 10,857 @9000, joint 10,217, window 10,235, off 10,285, freeway_only 11,409, urban_only 10,334). 다른 입력은 0.
4. [실행] **도착열 공통성**: 5개 제어 팔의 실현 도착 I_i(8100)+U_i(8100) 이 1098 은 16,070 다섯 번, 1099 는 20,166/20,167/20,167/20,169/20,166 입니다. 도시 입력도 팔마다 같은 수입니다. NC 의 I_1098(8100) 도 16,070 입니다. [추론] VISSIM 도착 생성은 시드가 정하고 제어와 무관합니다.
5. 도착 A_i(t) 추정: 도시 입력 32개 = 6팔 I_i(t)(앞당긴 판)의 위 포락선. 1098·1099 = 기대 수요 곡선을 실현 도착(8100 s 16,070·20,166)에 맞춘 것과 포락선 중 큰 값. 8100–9000 s 는 NC 실현 도착(1099: 21,815, 1098: 17,315)에 맞춤.
6. U_i(t) = max(0, A_i(t) − I_i(t)), 1 s 격자 적분 [W/uninserted2.py].
7. 검산 [실행]: native DelayLatent(`native_network_performance.json`)과 재구성 합의 차가 joint 232.8, window 232.8, off 232.9, freeway_only 232.8, urban_only 232.9, NC(0–9000) 231.4 veh·h 입니다. [추론] 이 일정한 차는 모든 팔에 같은 A(t) 모양 오차입니다. 그래서 팔 사이 차는 이 오차 없이 나옵니다.
8. NC ④b(0–8100): 경로 A = native(0–9000) 19,290.0 − 재구성 꼬리(8100–9000) 2,646.6 = **16,643.4**. 경로 B = 재구성 0–8100 16,412.0 + 제어 팔 평균 차 232.9 = **16,644.9** [계산]. VT:96-105 의 16,638 ± 10 범위 안입니다. 남은 불확실성은 꼬리 구간 도착 시각 흩어짐(어림 ±5 veh·h) [추론].

### 5.2 표: Ω·④·Ω 밖 (0–8100 s, veh·h, 64cf-s29 한 시드)

| 조건 | Ω701 | Ω635 | ① | ② | ④a | ④b | ④ | Ω 밖 (a) | Ω 밖 (b) |
|---|---|---|---|---|---|---|---|---|---|
| nc | 7406.2 | 6754.4 | 2124.5 | 2347.4 | 8994.9 | 16643.4 | 25638.4 | 18232.2 | 1588.8 |
| joint | 6911.5 | 6346.5 | 1840.9 | 2190.8 | 8545.9 | 16423.6 | 24969.5 | 18058.0 | 1634.4 |
| window | 7037.5 | 6466.4 | 1860.0 | 2253.2 | 8669.5 | 16332.1 | 25001.6 | 17964.1 | 1632.0 |
| off | 7011.8 | 6425.4 | 1823.1 | 2199.8 | 8650.0 | 16453.2 | 25103.2 | 18091.4 | 1638.1 |
| freeway_only | 7816.1 | 7087.2 | 1772.7 | 2217.3 | 9379.8 | 17536.6 | 26916.3 | 19100.3 | 1563.7 |
| urban_only | 7711.2 | 7124.0 | 2846.0 | 3081.1 | 9321.2 | 16441.2 | 25762.4 | 18051.2 | 1610.0 |

| 조건 − NC | Ω701 | Ω635 | ① | ② | ④a | ④b | ④ | Ω 밖 (a) | Ω 밖 (b) |
|---|---|---|---|---|---|---|---|---|---|
| joint | −494.7 | −407.9 | −283.7 | −156.6 | −449.0 | −219.9 | −668.8 | −174.2 | +45.7 |
| window | −368.7 | −288.0 | −264.6 | −94.2 | −325.4 | −311.4 | −636.8 | −268.1 | +43.3 |
| off | −394.3 | −329.0 | −301.5 | −147.6 | −345.0 | −190.2 | −535.2 | −140.8 | +49.4 |
| freeway_only | +409.9 | +332.8 | −351.8 | −130.1 | +384.8 | +893.1 | +1278.0 | +868.1 | −25.1 |
| urban_only | +305.0 | +369.6 | +721.4 | +733.7 | +326.2 | −202.2 | +124.0 | −181.0 | +21.2 |

- 출처: ④a = 내 FZP 집계. 제어 팔 ④b = native DelayLatent(0–8100). NC ④b = §5.1 경로 A. Ω635 = `previous_inside_links`(635개, Ω701 의 부분집합 [실행]); [추론, RX:7] TP 의 Ω635 와 같은 집합으로 봅니다(우리 멤버십 파일과 직접 대조는 안 함).
- [계산] joint 대 NC 백분율: Ω701 −6.679 %, Ω635 −6.039 %, ④ −2.609 %, Ω 밖 (a) −0.955 %, Ω 밖 (b) +2.875 %.
- [계산] joint − off(VSL 출력이 같은 두 팔): Ω701 −100.3 / ④ −133.7 / Ω 밖 (a) −33.4 / Ω 밖 (b) −3.7. RC:177 과 같습니다(④ 는 native 값으로 −133.6).

### 5.3 입력별 ④b (재구성, 공통 차 232.9 빼기 전, veh·h)

| 조건 | 1098 (FW_E 입구, 링크 74) | 1099 (FW_W 입구, 링크 26) | 도시 입력 32개 합 |
|---|---|---|---|
| nc | 1811.4 | 14328.8 | 271.8 |
| joint | 1908.4 | 14259.5 | 22.9 |
| window | 1793.1 | 14293.1 | 13.0 |
| off | 1867.1 | 14328.8 | 24.5 |
| freeway_only | 1776.0 | 15233.3 | 294.5 |
| urban_only | 1810.6 | 14382.5 | 15.2 |
| joint − NC | +96.9 | −69.4 | −248.9 |

- [실행] NC 의 도시 입력 대기는 입력 282(링크 1220011200) 102.6, 1085(링크 138) 85.0, 1093(링크 225) 68.8, 1102(링크 32, 서측 램프 상류) 11.8 veh·h 입니다. 신호가 native 인 freeway_only 도 98.6·79.0·62.9·50.2 입니다. TSC 가 있는 네 팔은 282 가 0.1–10.3, 1085·1093 이 0.0–0.3 입니다.
- [추론] joint 의 Ω 밖 (a) −174.2 중 약 −249 가 도시 입구 대기 감소입니다. 그 대기는 Ω701 에도 Ω 밖 (b) 에도 안 잡힙니다.
- [계산] ① −283.7 과 1098 입구 밖 대기 +96.9 를 더하면 −186.8 입니다. [추론] ① 감소의 약 1/3 은 1098 대기가 망 밖으로 옮겨진 몫과 겹칩니다(VT:108 질문). window 는 1098 −18.3, off +55.6, freeway_only −35.5, urban_only −0.8 입니다.
- [실행] NC U_1099(8100) ≈ 10,323(공통 도착 기준). VT 의 10,393 은 기대 도착 기준 값입니다.
- [실행] 1098 대기 정점: NC 약 1,797대(3,600 s), joint 약 1,851대(3,610 s) [W/uninserted_out.json].

## 6. 결정 JSON — VSL (순서 6)

- 읽은 칸 [실행 W/dec_extract.py, W/vsl_peek.py]: `action_<t>.json` /metadata/joint_leader_selection 의 `gradient_rows`(kind=vsl), `local_rows`(owner FW_E·FW_W 의 `step`), `trial_rows`, `candidates`, `policy`.
- [실행] 설정 값(`policy`): `fd_vsl_kmh` 10, `proximal` 10, `vsl_activation_secant` true, `objective_tolerance` 1e-7, `line_search_steps` 3. 블록 0 허용 집합 [70, 80, 90, 100, 110](직전 110, 최대 변경 40).
- [실행] joint 새 결정 47개(900–7950 s, 6900 제외)의 VSL 기울기 행 2,688개:
  - 방법: 2,688행 모두 `derivative_method = executable_secant_fallback`, `fallback_reason = inactive_vsl_legal_step`, `stencil = [−0.0909, 0]` (110 → 100 할선).
  - 부호: 음수 2,410, 0 이 204, 양수 74. 1e-9 를 넘는 양수는 5행(1050 s FW_E seg2 블록 1·2: +0.029·+0.027·+0.001; 1800 s FW_E seg13 블록 1: +0.1017). 최소 −8.997.
  - [계산] 10 km/h 한 걸음으로 반올림되려면 |걸음| ≥ 0.5 × 10/110 = 0.04545, 곧 기울기 ≥ 0.4545(proximal 10). 이 값을 넘은 행 0.
  - [계산] 기울기 −4.58(900 s FW_E seg13)은 110 → 100 에서 모형 Ω 비용 약 +0.42 veh·h, −8.997 은 약 +0.82 veh·h 입니다.
  - own(고속도로 자기 비용) 항 최대 +0.064, 대부분 음수. external 항은 0.0–0.6 의 작은 양수가 많음 [실행 900 s 예].
  - `local_rows` 의 VSL 걸음: 1050·1800·3900 s 에서 |걸음| ≤ 0.0102(≈ 1.1 km/h) → 110 으로 반올림. 4500 s 반복 1 에서는 NP 쌍대 가격(65.9, scaled)이 걸음을 −0.259(≈ −28 km/h, FW_E seg5 블록 1), 블록 0 은 −0.0723·−0.0806 까지 밀었습니다. 그래도 적용 출력은 110 입니다. `trial_rows` 에 VSL 칸이 없어 어느 단계(선탐색 1·0.5·0.25배, 반올림, 전체 재채점)에서 돌아왔는지는 **모름** → A0 재생 필요.
  - 출력: 49개 결정(6900 유지·8100 포함) 모두 VSL 110 [실행].
- [실행 대조] freeway_only(고속도로 목적·자기 정보, 같은 시드): VSL 행 4,152개 중 71행은 AD 경로, 4,081행 secant. 0.4545 넘는 행 53, 최대 +23.9(own −2.99, external +26.8 꼴). 출력 100 이 10번, 90 이 1번. [추론] 같은 plant 라도 목적에 따라 VSL 기울기 부호가 바뀝니다. joint 에서는 own 음수가 이깁니다.
- [추론] TP:152 의 길 1("secant 기울기 ≥ 0 이면 상한 110 에 막힘")이 47개 중 대부분에 해당하고, 1800 s 한 행은 길 2(작은 양수 → 반올림)입니다. 4500 s 는 가격이 걸음을 만들었으나 채택되지 않은 경우입니다.

## 7. 결정 JSON — RM·유지 (순서 7)

### 7.1 cap 후보·수렴

- [실행] 결정마다 cap 후보 3개(같은 NP cap, NUF 목표 ±1000 veh/h). 141개 상태: iteration_limit 86, no_feasible_nonlinear_step 27, linear_resource_qp_failed 20, no_improving_step 7, no_executable_step 1.
- [실행] `selection_status` 47/47 = `best_observed_feasible_sdmpc`, `converged` 0/47.
- [실행] 모형 예측 감소(`prediction_ttt_reduction` = 유지안 − 선택안): 평균 1.87, 중앙 1.69, 최소 0.17, 최대 6.32 veh·h.
- [실행] 3600 s: 후보 상태 (iteration_limit, no_feasible_nonlinear_step, iteration_limit), 예측 감소 0.74. 4500 s: (no_improving_step, no_feasible_nonlinear_step, iteration_limit), 0.30. [추론] RC:27 의 "17 SC 중 15·14개 plan 이 직전과 같음" 은 작은 모형 개선(걸음이 일부 SC 에만 생김)과 맞습니다. 확정은 재생 필요.

### 7.2 미터 이웃 검사

- [실행] `finite_neighbor_audit_performed` 47/47 true. `meter_neighbor_audit` /selected: `combined_meter_owners` 39, 미터 하나 8(RM_C10681:release 3, RM_C10480:tighten 1, RM_C10484:tighten 1, RM_C10681:tighten 1, RM_C10639:release 1, RM_C10646:release 1).
- [실행] 결정당 후보 22–53개(`additional_predictions` 같은 수, 예산별 반복 포함), 불가능 후보 합 128. `exhaustive` false, 범위 문구 "Finite legal RM neighbors of every solved feasible budget; each cap remains fixed".
- [실행] 고른 후보의 모형 Ω 변화(`delta_veh_h`, 기준 = 최선 SDMPC 안): 46/47 음수, 합 −6.62, 최소 −0.49(3450 s). 2850 s 는 +0.0002.
- [실행] 실제 미터 녹색(49결정, 6900·8100 포함, `diagnostics/rw_meter_green_*`): RM_C10644 49번 모두 10 s, RM_C10482 48번 10 s·1번 9 s, RM_C10480 2 s 가 36번, RM_C10639 2 s 가 30번, RM_C10681·10490·10484 는 2–10 s 사이 여러 값.

### 7.3 저장 가드

- [실행] 램프 저장 가드(`meter_operating_bounds`, 발동 문턱 0.9, 녹색 0 금지): 발동 2번. 2250 s RM_C10681(직전 3 s → 하한 5 s), 4500 s RM_C10639(2 s → 4 s).
- [실행] 도시 저장 가드(문턱 0.9, 예비 녹색 2 s): `blocks` 에 `status = constrained` 가 있는 결정 42개(8100 포함), 신호·블록 288개 [W/h10633.py].

### 7.4 램프 도착 예측 폴백

- [읽음] 설정 `optimized_config.json` /calibration_override/prediction/local_ramp_arrival_forecast 의 표 키는 R_D_W·R_F_W·R_D_E·R_F_E(지평 33.5/77.2/30.7/6.5 s, 상한 865/1394/1079/638 veh/h), `strict_ramp_keys` 없음. 실행 램프 키는 RM_C10480 등 8개입니다.
- [읽음] 코드 `code/evaluation/controllers/vissim_stackelberg_adapter.py:9433-9500`: 키가 안 맞으면 지평 120 s, 상한 900 veh/h. `state_<t>.json` /ramp_counts 키도 R_*·D·F 뿐이라(W/ramp_fc.py) 링크 관측 경로로 들어갑니다.
- [실행] 47개 새 결정의 `forecast_ramp_arrival_total_vph` 가 모두 30 veh/h(= 3600/120)의 배수입니다(예: 900 s 2,730, 2250 s 5,160, 7950 s 1,470). R_* 표가 쓰였다면 대당 107.5/46.6/117.3/553.8 veh/h 단위가 나옵니다. `forecast_ramp_arrival_R_*_vph` 4칸은 모두 0.0.
- [추론] 폴백은 47/47 결정에서 탔습니다. 이 값을 쓰는 곳은 `area_freeway_accounting.py:165`, `urban_flow_accounting.py:444` 등입니다. SDMPC lane plant 예측에 들어가는지는 추적하지 않았습니다(**모름**).

### 7.5 joint 6900 유지 원인

- [실행] `raw/joint/sdmpc/runlog_sdmpc31_sdmpc8100_s29.txt:5296-5298`: `CONTROLLER_DECISION sim_sec=6900 wall_sec=11.45 result=exit=1 … DECISION_FAILED type=ValueError message=Missing observed speed with nonempty moving source` → `DECISION_HOLD_ATTEMPT` → `DECISION_HELD_PREVIOUS … action_006750.json`.
- [실행] 호출 경로(`decisions…/action_006900.error.txt`): adapter:13082 `configure_runtime` → runtime_setup.py:336 → calibrated_urban_runtime.py:160 `sc10_north325.candidate.install` → candidate.py:139 → calibrated_initial_projection.py:46 → :25 예외.
- [실행] 같은 예외가 window 6750, off 4500·4800·5100·5850·6000·6150·6900, urban_only 1950·6000·6150 에서 났습니다. off 7950·8100, urban_only 5700·7800 은 `ValueError: Terminal queue count changed` 입니다. 6팔 어디에도 시한(timeout) 유지는 없습니다.
- [실행] 머리 자원 10633 관측 하한(`head_resource_observed_floor_10633_…`): 900 s 1,330.4 → 2700–4500 s 1,836.7 → 4650–6750 s 1,858.1 → **7050 s 0.0** → 7200–7350 s 960.0 → 7500–8100 s 1,103.2 veh/h. 7050 s 의 0.0 이 6900 예외와 이어지는지는 **모름**.

## 8. 결정 시간 (순서 8)

- 출처 [실행 W/walltimes.py]: runlog `CONTROLLER_DECISION … wall_sec`(VBS 가 잰 값). `decision_budget.json` /wall_sec 도 같은 크기(joint 평균 292.6 s).

| 팔 (codex PC) | 새 결정 n (900–7950) | 평균 s | 중앙 s | 최대 s | > 360 s | > 1800 s |
|---|---|---|---|---|---|---|
| joint | 47 | 294.8 | 277.5 | 448.6 | 11 | 0 |
| window | 47 | 222.2 | 222.9 | 320.0 | 0 | 0 |
| off | 40 | 203.9 | 193.8 | 264.1 | 0 | 0 |
| freeway_only | 48 | 268.5 | 262.9 | 369.8 | 2 | 0 |
| urban_only | 43 | 98.0 | 93.4 | 178.1 | 0 | 0 |
| (NC, 무제어 55개) | 55 | 8.8 | 8.9 | 9.8 | 0 | 0 |

- [계산] joint 새 결정 47개 합 13,857 s 는 런 벽시계 17,264 s(HO:307)의 80 % 입니다.
- [계산] 이 PC W264(window 꼴, 시한 0) 평균 1,709 s(TP:80)는 codex PC window 평균 222.2 s 의 약 7.7배, joint 평균의 약 5.8배입니다. [추론] 이 PC 에서 joint 꼴은 W264 보다 더 길 수 있습니다(joint 이 window 보다 codex PC 에서 1.33배).
- [실행] TP:52·79·132 의 "결정당 많아야 약 360 s" 는 런 시간에서 나눈 어림입니다. 실제 joint 결정 11개가 360 s 를 넘고 최대 448.6 s 입니다. 시한 1800 s(설정 `optimized_config.json:8466`)는 codex PC 에서는 한 번도 닿지 않았습니다.

## 9. 실행 증거 (순서 9)

- [읽음 `analysis/comparison/joint/execution.json`] `passed` false, `native_execution_passed` true, `native_lsa_com_coverage_passed` false. `checks/native_ldp` 202,500행 통과 표시, `checks/native_lsa` 실패 표시(28,482 행, COM 사건 27,094). freeway_only·urban_only 도 같은 꼴. window 는 `native_execution_failed_checks = ['sources_and_terminal_log']`(`window_analysis/summary.json`).
- [실행 W/lsa_cmp.py] LSA 는 제어 팔 5개 모두 0–8100 s 28,482행이고, 제어 신호 17개는 약 900 s 뒤 기록이 없습니다(SC1 146행 대 NC 1,298행). 나머지 33개 SC 는 NC 와 같습니다. [추론] VISSIM LSA 는 COM 으로 바꾼 신호 상태를 적지 않아 `native_lsa` false 는 기록 방식 때문입니다. LSA 로는 신호 실행을 확인할 수 없습니다.
- [실행 W/ldp_cmp.py] LDP(1 s 신호 상태) 를 NC 와 비교:
  - freeway_only: 제어 SC 17개 모두 0–8100 s 매 초 NC 와 같습니다 → 도시 신호는 native 그대로입니다. 다른 곳은 미터 SC 9101–9108 중 7개뿐입니다(909 s 부터; 늘 10 s 인 9104 = RM_C10644 는 같음).
  - urban_only: 미터 SC 9101–9108 이 NC 와 같습니다 → 미터는 native(열림) 그대로입니다.
  - joint·window·off: 제어 SC 17개와 미터 SC 5–7개가 901 s 부터 다릅니다.
- [실행] freeway_only action CSV 는 신호 명령 833행을 쓰지만 SC 마다 plan 이 1종입니다(예: SC1 54/21/32/31 s, offset 19). joint 는 SC 마다 46–48종, window 44–47, off 38–40, urban_only 43–44 [W/act_audit.py].
- [실행 W/rm_exec.py] 미터 실행: 150 s 구간마다 명령 녹색(action CSV `green_sec`)과 LDP 녹색 초 / 15주기를 비교. 5팔 × 미터 8 × 48구간 = 1,920구간 모두 차 ≤ 0.5 s(어긋남 0).
- [실행] VSL 명령·되읽기: joint 3,630행 모두 `110|110`. window 90 이 104행, freeway_only 100 이 68행·90 이 11행. 신호 되읽기 칸은 6팔 모두 833/833 `stored` 입니다(RC:150 과 같음).
- 하지 않은 것: 도시 신호의 명령 녹색 길이와 LDP 녹색 길이 대조(현시 → SG 대응표 필요). **열림**.

## 10. 원래 평가기 (순서 10)

- [읽음] `analysis/original_scripts/solo355_compare_20261014.py`(sha `7fc91d60…`)와 `analyze.py`(sha `6df4be75…`)는 그대로는 돌 수 없습니다. 절대 경로(`E:/VISSIM_analysis/…`, `D:/VISSIM_runtime/…`), `plan.json` 핀 검사, closure 파일 검사를 합니다(solo355_compare:13-26, analyze.py:4-24).
- [실행 W/orig_eval.py] 그 분할 코드(solo355_compare:49-67)를 그대로 옮겨 캐시 `analysis/comparison/{nc,joint,freeway_only,urban_only}/area_metrics.json` 에 돌렸습니다. `summary.json` /reporting_partition/parts 와 차 0.0 입니다.
- [실행] 캐시의 링크별 체류(`physical_link_residence`, 982–984 링크)와 내 FZP 링크별 값의 차는 최대 5.9e-12 veh·h 입니다. 내 값에 같은 분할을 돌리면 도시도로 3,642.612417 → 3,348.048083, **8.086623 %** 가 나옵니다(§4).
- 결론 문장 대신 사실: 8.09 % 분할은 캐시만의 값이 아니라 FZP 에서 독립 재현됩니다. 다만 "도시도로" 는 미터 상류 링크를 포함한 정의입니다(§4.1 대안 규칙 −11.73 %).

## 11. 결정 재생 입력 (순서 11)

- [실행] joint 결정 폴더에 `state_000001.json`–`state_008100.json` 57개, `obs150/` 278개, `lane_observations/` 57개, 결정 JSON(`action_<t>.json`·`.joint.json`·진행 로그)이 있습니다. 결정 입력 관측은 있습니다. 재생 가능 여부·비트 동일 여부는 A0 에이전트 몫입니다(이번 단계 재생 0).

---

## 12. 모름과 열린 질문

1. 4500 s 에 가격이 만든 VSL 걸음(최대 ≈ −28 km/h)이 왜 출력 110 으로 돌아왔는가. `trial_rows` 에 VSL 칸이 없음. A0 재생으로만 답함.
2. 120 s·900 veh/h 램프 도착 폴백 값이 SDMPC lane plant 예측에 실제로 들어가는가(코드 추적 안 함).
3. 도시 신호 명령 녹색 길이 대 LDP 실제 녹색 길이(현시-SG 대응 필요).
4. 머리 자원 10633 하한이 7050 s 에 0.0 이 된 까닭.
5. NC ④b 꼬리(8100–9000) 도착 시각 흩어짐 몫(어림 ±5 veh·h). 정확값은 8100 s NC 한 번(TP:74)으로만.
6. Ω635 가 우리 멤버십 파일과 같은 집합인지 직접 대조(이번엔 codex 파일의 `previous_inside_links` 사용).
7. 공통 차 232.9 veh·h 의 원인(1098·1099 대기 구간의 도착 모양 오차로 봄 [추론]).
8. 모든 숫자는 64cf-s29 한 시드·조건당 한 런입니다. 시드 흩어짐·신뢰구간은 모릅니다.

## 13. TP·VT·HO 에 고칠 곳

| 위치 | 지금 문장 | 이번 결과 |
|---|---|---|
| TP:52, TP:79, TP:132 | codex PC 결정당 "많아야 약 360 s" | 실측 평균 294.8 s, 최대 448.6 s, 47개 중 11개 > 360 s(§8) |
| TP:45, VT:96-105 | NC ④b ≈ 16,638 ± 10, ④ ≈ −663, Ω 밖 (a) ≈ −168 | 16,643.4(경로 B 16,644.9), ④ −668.8, Ω 밖 (a) −174.2(범위 안) |
| TP:46 | joint 쪽 원자료 미검증 | 접두 해시·FZP 재집계·분할·미삽입·결정 JSON 확인(§3–§7) |
| TP:43, RC:30 | 8.09 % 분할은 캐시뿐 | FZP 독립 재현(§10) |
| RC:215 | 886a014a VBS 에 native 성능 코드 없음 | 실행본 VBS 는 수정본(` M`), 605·5068–5104줄에 있음(§2) |
| HO:46 | NC HEAD 43자 | 40자 `886a014a303dd155e05cc33041796822abbc29b0`(§2) |
| HO:75, HO:247, HO:314 | 입력별 대기 적분 모름 | 입력별 재구성 + native 검산(§5) |

## 14. 하지 않은 것·규칙

- VISSIM·COM·폐루프 러너·결정 재생·동결·커밋·푸시 0. codex 스크립트(`verify_sha256.py`, `audit_handoff.py`, `check_fzp.py`, 원래 평가기) 실행 0. 원래 평가기는 분할 코드 19줄을 내 스크립트에 옮겨 캐시 입력에 돌렸을 뿐입니다.
- 공유 드라이브 Y: 접근 0. RB·GWT8·동결 트리·codex worktree 쓰기 0. `sealed/` 열기·해시 0. 봉인 시드 숫자 0.
- FZP 스캔 9번(raw 6 + LNC 1 + 전체 해시 2)은 한 번에 하나, BELOW_NORMAL, 공유 잠금 `work/omega/fzp.lock`. 각 30–43 s. kill 0.
- 디스크: 시작 C 34 GB, D 290.9 GB. 끝은 LOG.md 에 적음.

## 15. 산출물 sha256 (모두 `W` = `codex_handoff/work/rawcheck/`)

| 파일 | sha256 |
|---|---|
| scan_fzp.py | c8a6e5c4ee873a698b660b32662ec09d4f5f280765a2413764259372a5ddc425 |
| uninserted2.py | bc3b48493166cefe42f286c6f69029327ab43ee565fd701a8ddd4fbedf4e6d95 |
| orig_eval.py | 8b00c41e50541f68c74883cfe83ac7f28cfc9dafebfb73308f91e93fc6506790 |
| metrics_out.json | 5d9cb879d4731b524f3f2e903a1e0a09f0f105f7a3179a885ab6401ed5d4344d |
| uninserted2_out.json | c83fa2a74d4013428c41b38b9eb7a289e79782a6fad79e2021f95eb2a1a73729 |
| final_table.json | c2da1c54c2c696add84f840ff15d7b47e159cdf4145346fedd3a0a16240451f3 |
| dec_joint.json | 4c51bcc607d291f7debe4d9cde56e4c20d96e4a06a11d199c3f7cfb1630f3e0a |
| dec_freeway_only.json | ff4511c2da63e430e4fde4eaac68287c3111e7df1f5ae177121cdf601eb36724 |
| walltimes_out.json | e62255b5e457ae97f063525354b6dada841d3b538b704f22298d277639420b3b |
| ramp_fc_out.json | 213f466b3e3c4497a372720d4a095c3e110b927127d60ec68d764feb8fe3936d |
| ldp_cmp_out.json | 481292a571bf89746ed9b04c27bc522aca7150f3f66a2334e8d9a3b217cdc7f8 |
| rm_exec_out.json | ef0d51fef8ac2885dba465eee9c1812d65197b2f3568f05fe6c9a2cfaecf4a42 |
| lsa_cmp_out.json | ea3bb81d98ac59900eefdbf84498b58caad243a4b8220625e4bcdaaa28cbd320 |
| h10633_out.json | 390959776d31ff65c188fbb17ec5c9b40e053bab5be5c2a1697faf5fcdb20aa9 |
| SHA256SUMS_RAWCHECK.txt (52개 파일 목록) | 3e3b53077eb3a3d43a737b14e996ede96852cfa72d67994566d03e6e2b69ceac |

- 이 문서의 sha256 은 LOG.md 와 반환값에 적습니다.
