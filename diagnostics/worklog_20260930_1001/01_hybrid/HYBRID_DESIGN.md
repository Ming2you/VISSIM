# 하이브리드 설계서 — 고속도로 규칙(Carlson MTFC-VSL + ALINEA) × 도시 SDMPC, v3c1 s31 9,000 s 탐색 런

- 작성 2026-09-29. 설계와 보정만 했다. **코드는 한 줄도 쓰지 않았고 런도 띄우지 않았다.**
- 태그: [실행] 이 세션에서 돌려서 확인 / [읽음] 파일·문서를 읽어서 확인 / [추론] 근거는 있으나 직접 확인 못 함
- 기준 코드: `D:/VISSIM-merge/sim3-n31-v3c1` (브랜치 claude/repin-v3c1-20260928, 9ed2ef0). 이 트리는 읽기만 했고 `git status` 는 끝까지 깨끗했다 [실행].
- 파라미터 원본(기계용): `hybrid/hybrid_parameters.json`. 보정 산출물: `hybrid/calib/`.

---

## 0. 결론 먼저

1. **기존 `diagnostic-rule-profile` 은 그대로 못 쓴다.** 도시 신호를 끄고(`diagnostic_profile.py:110-115`, 어댑터 `:13751-13753` suppress_signal_rows), 게임·탐색도 끈다(`vissim_stackelberg_adapter.py:12861-12862`). VSL 은 옛 120 망용 임계값 결정 트리(`diagnostic_profile.py:209-224`)이고, v3c1 허용 집합 {80..110} 에 120 이 없어서 `:39-40` 에서 바로 예외가 난다 [읽음]. 재사용할 것은 ALINEA 산술(`alinea_meter_step`, `:227-251`)과 물리 미터 녹색 검증(`physical_ramp_branches.candidate_from_greens`, `:325-346`)뿐이다.
2. **통합 방식**: 결정마다 규칙층이 먼저 고속도로 명령(미터 8개 녹색, VSL 구역값)을 정한다. 그 명령을 SDMPC 의 기준 행동(reference)에 박아 넣고, 미터·VSL 축을 폭 0 으로 만든다. SDMPC 는 **그 고속도로 명령을 450 s 지평 내내 고정(zero-order hold)한 채** 도시 신호만 최적화한다. 기록은 기존 writer 한 벌로 한다(§8).
3. **보정 결과(사전 선언 후 계산)** [실행]
   - ALINEA 목표 점유율: 10681 **17.5 %**, 10490 **19.5 %**, 10484 **18.5 %**, 10639 **10.5 %**(쌍봉, 사용자 결정 필요). FW_W 네 곳은 NC 에서 한 번도 임계에 안 닿아 **식별 불가**이며, 선언대로 대체값 18.0 % 를 쓴다(실질적으로 안 미터링).
   - B2 임계밀도(셀 22–23): **31.0 veh/km/lane** [부트스트랩 5–95 % 25–35], 최대 유량 포락 약 7,334 veh/h.
   - MTFC 목표는 런타임에 실제로 보는 양, 즉 10484 측정소 점유율 **18.5 %** 로 둔다(§4.1).
4. **적용 구역**: FW_E 표지판 S4(DSD 59–62, 5,386.5 m) 한 개만 쓴다. 그 다음 표지판 S5(DSD 63–66, 6,733.2 m)는 110 으로 고정한다. 그러면 가속 구역이 B2 셀 시작까지 601 m, 합류 노즈까지 871 m 남는다. 이를 위해 FW_E 구역 머리를 [0,5,10,**12**,15] 로 나눈다(§5). 12 여야 plant 표지판 셀과 CSV writer 가 같은 값을 읽는다.
5. **Carlson 이득의 원문 수치는 확인하지 못했다.** 원문이 유료이고, 파일 내려받기는 사용자 승인 사항이다(09-28 무단 PDF 삭제 결정). 2차 출처의 cascade 이득을 단일 루프로 환산한 **잠정값**(K_P 0.0133, K_I 0.0813 /%p)을 제안한다. 발사 전에 원문으로 확인하는 것을 권한다(§3, §12).
6. **정직한 기대치**: {80..110} 로는 MTFC 가 흐름을 병목 용량 아래로 붙잡을 권한이 거의 없다. B2 임계속도가 약 79 km/h 이고, L1 의 80 km/h 용량 감소는 ≤ 3.6 % 이며, N1/N1F 에서 VSL 방류 이득이 0 이었다. B2 를 실제로 제어하는 것은 ALINEA(10484·10490)다. 또 이 런은 s31 **한 시드 탐색**이라 J1 에 따라 FW_E 결론을 낼 수 없다.

---

## 1. 요청과 범위

- **사용자 요청(2026-09-29)**: 코어가 남으면 고속도로는 VSL(Carlson) + RM(ALINEA), 도시만 SDMPC 로 9,000 s 한 번 돌린다.
- **워크플로 지정 선택**
  - (1) Carlson PI, B2 병목, 목표밀도는 v3c1 NC 에서 재서 고정, 문헌 이득, 출력은 {80,90,100,110} 로 양자화, 가속 구역을 남기는 적용 구역
  - (2) 미터 8개 모두 ALINEA, 목표는 합류별 임계점유율(NC fit 5시드), 이득 70 veh/h/%/lane, min/max 는 기존 규칙 정책
  - (3) 도시 = `config_n31_v2.json`(v3c1 재핀 배포본)
  - (4) seed 31 한 번. 짝은 R-obs(900 s 까지 NC s31 과 동일)
- **안전**
  - 동결·다른 워크트리·런 폴더는 쓰지 않았다(읽기만).
  - s37·RM 팔 산출·봉인 시드는 열지 않았다. RM 빌드 스크립트의 README 와 grep 결과만 봤다.
  - VISSIM·cscript 는 시작하지도 끄지도 않았다. 금지 시험도 돌리지 않았다.
  - 계산은 한 프로세스, BELOW_NORMAL 이었다(스크립트 안에서 SetPriorityClass). 각 FZP 약 25 s, 합계 약 3 분.

---

## 2. 기존 코드에서 확인한 것

| 항목 | 사실 | 근거 |
|---|---|---|
| rule profile 의 도시 처리 | 도시 신호 제어 끔 + 신호 행 억제 → 하이브리드에 부적합 | `diagnostic_profile.py:110-115`, 어댑터 `:13751-13753` [읽음] |
| rule profile 게임 | `joint_owner_game_settings` 가 RULE 이면 None → SDMPC 불가 | 어댑터 `:12861-12862` [읽음] |
| rule VSL | 흐름·점유율·속도 임계 결정 트리(60/80/120). Carlson 아님. 120 필수 | `diagnostic_profile.py:209-224`, `:39-40` [읽음] |
| ALINEA 산술 | `r = r_prev + K(ô − o)`, [min,max] 제한, 녹색은 직전 실제 녹색 ±2 안의 표 값 중 가장 가까운 것, 적분기는 도달 가능 범위로 자름(anti-windup) | `diagnostic_profile.py:227-251` [읽음] |
| 기존 규칙 정책 | 목표 15 %(탐색값), 이득 70 veh/h/%/차로(2차로 미터 140), min=표[2], max=표[10], ±2 s, 최소 녹색 2, **큐 override 없음**, 150 s, 900 s 시작 | `diagnostics/handoff_20260922_control_choice/native_receipts/rm/records/rule_policy.json` [읽음] |
| 서비스 표 | 차로당 veh/cycle {2:0.71 … 10:4.2} → 표[2]=255.6, 표[10]=1,512 veh/h/차로 | `config_n31_v2.json` actuation.real_world_ramp_metering, `physical_ramp_branches.py:73-77` [읽음] |
| fast 러너 규칙 | `fast_fixed_profile.rule_step` 은 fast NC 러너 전용(측정 CSV 를 id 로 읽음). SDMPC 러너와 무관 | `diagnostics/fast_fixed_profile.py:175-259` [읽음] |
| rule_observation 생산 | VBS 가 **controller = diagnostic-rule-profile 일 때만** state JSON 에 씀 | `run_real_world_stackelberg_controller.vbs:2821` [읽음] |
| rule_observation 내용 | `DataCollectionMeasurements (Current,k,All)` 의 Vehs·SpeedAvgArith·OccupRate(×100). 측정소별 차로 평균과 차로 행(measurement_no 포함) | VBS `:2937-2996` [읽음] |
| **이름 중복 결함** | v3c1 망에 `RULE|ramps|*` 가 **같은 이름으로 두 벌** 있다: 910001–058(합류 끝 **상류** 37–154 m), 910059–116(합류 끝 **+50 m**). VBS 는 이름으로 묶으므로(`:2913-2929`) 측정소 값이 상·하류 섞임 | 망 XML 파싱 [실행] |
| obs150 모드의 검지 | DataColl 150 s 수집이 켜진다(`:4935-4941`). mer 청크는 960xxx 만, rule_crosscheck 는 910030–047 의 Vehs 만. **R-obs state 에 rule_observation 없음** | VBS [읽음], R-obs `state_002100.json`·`mer_002100.jsonl` [실행] |
| VSL 쓰기 경로 | CSV 행 검증 = 표지판 키 + `RW_ALLOWED_VSL_SPEEDS`(VBS `:1341-1343`), 적용 = `DesSpeedDistr(10/20/30/70)=속도` 후 되읽기(`:1444-1464`, `:1938-1968`). 분포 80/90/100/110 은 v3c1 망에 있다 | [읽음], 망 [실행] |
| VSL<110 실기록 | "SDMPC 러너가 110 미만을 쓴 적 없다"는 **v3c1 에만 해당**. v3b S0e(`sdmpc31_v3b_s31e`)는 DSD 59–66 에 80/90/100 을 썼고, 되읽기 16,104행(80: 32, 90: 864, 100: 2,032, 110: 13,176) 중 실패 0 | `vsl_readback.csv` [실행] |
| 러너 | `-Controller` 는 wu-link/no-control 만(`run_sdmpc_n31.ps1:40`). RW_* 만 지움(`:205`). 감시자는 `Start-Process` 로 cscript 를 띄워 환경을 상속(동결본 watchdog `:911-912`). VBS 는 `shell.Exec` 로 python 을 띄움 | [읽음] |
| 재생 도구 | `make_replay_state_v2.py compare --tuning` 은 VSL 전부 110 을 요구(`:234-242`, `:322`) → 하이브리드 재생은 `--tuning` 없이 비교 | [읽음] |

---

## 3. Carlson MTFC — 문헌에서 확인한 것과 못 한 것

- **확인(2차 문헌 원문 텍스트, 이전 세션 추출본)**
  - Grumert et al. 2018(ETRR 10:21) §3.4(`scratchpad/vsl-fixed-dsd/work/grumert2018.txt:394-417`) [읽음]. Müller et al. 을 따른 MTFC 구현이다.
    - 병목 점유율을 임계점유율 추정치 쪽으로 몰아가는 **적분형** 법칙이다. 속도 제한 비율 b 를 적분기로 갱신한다.
    - 목표는 임계보다 1 %p 낮게 잡는다.
    - 제한은 원래 제한의 20–100 %, 10 km/h 단위로 반올림한다.
    - 병목 주변 검지기 넷의 최대 점유율을 쓴다.
    - 적용 구역 300 m 를 병목 275 m 상류에 둔다. 갱신 주기는 30 s 이다.
  - Conran 2017 학위논문(`work/vt_thesis.txt:981-993`) [읽음]. Carlson 계열 MTFC 개념을 이렇게 요약한다.
    - 혼잡을 VSL 로 병목에서 통제 구역으로 옮긴다.
    - 차량은 병목에 닿기 전에 임계속도로 다시 가속한다.
    - 병목 밀도를 임계밀도와 비교해 목표 유량을 정하고, VSL 유출과 비교해 VSL 을 정한다(cascade).
- **2차 요약만 있음(미검증)**: 웹 검색 요약에 cascade MTFC 이득이 나온다 [실행: 검색]. 1차(밀도→유량) 이득 "9 km/h, 55 km/h", 2차(유량→b) 적분 이득 "0.0015 h/veh" 이다. 출처 논문을 특정하지 못했고, 두 이득의 순서(K_P/K_I)도 확인하지 못했다.
- **1차 원문(Carlson, Papamichail, Papageorgiou 2011, IEEE T-ITS 12(4):1261–1276)은 확인하지 못했다.**
  - IEEE·ACM·ResearchGate 는 403 이었다.
  - Semantic Scholar 에 녹색 OA 기록(infoscience.epfl.ch/record/180988)이 있지만 PDF 를 받는 것은 파일 다운로드이고, 사용자가 09-28 에 무단 PDF 를 지우라고 결정했으므로 받지 않았다.
  - 과정에서 WebFetch 가 arXiv PDF 1개(무관 논문)를 도구 캐시에 자동 저장해서 곧바로 지웠다 [실행].
  - 도구 캐시에는 이전 세션의 `webfetch-*.pdf` 2개가 남아 있다(손대지 않음).
- **구조 요약(원문 대조 필요)** [추론: 2차 문헌 + 기억]
  - 적용 구역(VSL) → 가속 구역 → 병목 순서다. 제어 변수는 VSL 비율 b ∈ [b_min, 1] 이다.
  - 기본은 병목 밀도 되먹임 I 형이고, 비례항을 더한 PI 형(속도형 증분)과, 밀도→목표유량→b 의 cascade 형이 있다.
  - 목표는 병목의 임계밀도(또는 약간 아래)다.

---

## 4. 이산 VSL 제어기 명세 (150 s)

### 4.1 상태와 목표

- **측정 o(k)**: 결정 시각 t_k 의 창 (t_k−150, t_k] 에 대해, `RULE|ramps|RM_C10484` **두 번째 묶음**(측정 910085–910087) 3차로 OccupRate 의 차로 평균(%)이다.
  - 위치: link 24 @215.7 m = FW_E 7,653.7 m. B2 셀 23 안이고, 10484 합류 노즈 50 m 하류, q23 계수선 9 m 상류다 [실행].
  - 스냅숏 밀도(state 의 vehicle_records)는 결정당 한 장뿐이라 150 s 시간평균 검지값을 쓴다. Carlson/Müller 의 검지 기반 구현과 같은 형태다 [추론].
- **목표 ô = 18.5 %**: 이 측정소의 O1(§7)이다. 밀도 단위 목표(셀 22–23) ρ̂ = 31.0 veh/km/lane 은 따로 보고한다.
  - NC 5시드의 창 295개 회귀: o_10484 = 3.65 + 0.356·ρ₂₂₋₂₃ (r 0.93) [실행]. 이 식으로 ρ̂ 31 은 o 14.7 % 에 해당한다.
  - 포락이 13.5–19.5 % 에서 평탄해서 두 목표가 어긋난다(§7.3). 사전 선언은 측정소 O1 을 MTFC 목표로 정했으므로 18.5 % 를 쓴다. 14.7 % 는 민감도 대안이다.

### 4.2 법칙

```
b~(k) = clip[b_min, 1]( b~(k-1) + K_P·(o(k-1) − o(k)) + K_I·(ô − o(k)) )      # 속도형 PI, 적분기 = b~ 자체
v*(k) = nearest{80, 90, 100, 110}(110 · b~(k))                                 # 동률이면 높은 쪽
v(k)  = nearest-level( clip[v(k-1) − 20, v(k-1) + 20]( v*(k) ) )                # 결정당 ≤ 20 km/h
```

- **b_min** = 80/110 = 0.727. 행동 집합 하한이다. 문헌 구현은 0.2 까지 내린다(§3).
- **anti-windup**: 연속 상태 b~ 를 [b_min, 1] 로 자른다(조건부 적분). 양자화·속도제한은 출력에만 걸고, 적분기는 양자화 전 값을 보존한다. ALINEA 의 next_request 와 같은 방식이다.
- **속도 제한 20 km/h/결정**
  - 러너 규칙 가운데 가장 엄한 것을 따랐다. fast 러너는 150 s 당 분포 ID 20 까지다(`fast_fixed_profile.py:94-95`).
  - SDMPC 이동 상자의 `max_vsl_step` 40(`config_n31_v2.json`, `area_follower_objective.py:1294`)보다 작다.
  - VBS 는 값만 검사하고 변화폭은 검사하지 않는다 [읽음].
- **이득(잠정)**: K_P = 0.0133 /%p, K_I = 0.0813 /%p. 도출은 다음과 같다 [추론].
  - 2차 요약의 cascade 이득을 문자 그대로의 순서로 읽는다: K_P^ρ = 9 km/h, K_I^ρ = 55 km/h, 내부 0.0015 h/veh.
  - 내부 루프가 준정적이라고 보고 b ≈ q̂/Q_app 로 단일 루프에 접는다. Q_app = 1,900 veh/h/lane 이다. NC 에서 10681 측정소(4차로) 포락 최대 7,544 veh/h ≈ 1,886/lane 에서 가져왔다.
  - 밀도 단위로 K_P 0.00474, K_I 0.0289 km·lane/veh 가 된다.
  - 0.356 %/(veh/km/lane) 로 나누어 점유율 단위로 바꾼다.
- **150 s 로 재척도하지 않는다** [추론].
  - 적용 구역(5,386 m)에서 측정소(7,654 m)까지의 수송 지연이 80–110 km/h 에서 약 75–100 s 로 한 주기보다 짧다. 그래서 플랜트가 한 주기 안에 거의 정착하고, 주기당 루프 이득이 안정성을 정한다.
  - ALINEA 관행도 K_R 70 을 주기와 무관하게 쓴다.
  - 원문 T_c 와 이득이 확인되면 사용자가 다시 정한다.
- **시작과 끝**
  - 첫 결정은 t = 900 이고 창 (750, 900] 을 본다. 이때 P 항은 0, b~ = 1 이다.
  - 그 전(워밍업 no-control)에는 110 이다.
  - 끝내는 규칙은 따로 없다. o < ô 이면 b~ 가 1 로 되돌아와 110(끄기)이 된다.
- **open-loop 재생(되먹임 없음, 활성 빈도만)** [실행] `calib/openloop_replay.json`
  - ô 18.5 에서 잠정 이득은 결정의 15–33 % 가 110 미만, 80 은 7–28 %, 첫 작동 1,350–2,550 s, 결정 54개 중 전환 6–16회였다.
  - 순서를 뒤집은 이득(K_P 0.0813)은 전환 24–31회로 떨림이 심했다.

### 4.3 FW_W

- 110 으로 고정한다. FW_W 합류 측정소 네 곳은 NC 에서 혼잡 창(v<60)이 0–1개로 합류 병목이 없다 [실행].
- FW_W 의 알려진 정체(10491 진출 역류)는 분류부 현상이라 MTFC 대상이 아니다 [추론].

---

## 5. 적용 구역과 가속 구역 (FW_E)

| 표지판(망 이름) | DSD | 위치 | 21셀 매핑 | plant 표지판 셀(31셀) → 부모 |
|---|---|---|---|---|
| S0 | 36–39, 43–46 | 11.5–40 m | seg0 | 0 → 0 |
| S1 | 47–50 | 1,346.6 m | seg2 | 3 |
| S2 | 51–54 | 2,782.7 m | seg5 | 5 |
| S3 | 55–58 | 4,039.9 m | seg7 | 8 |
| **S4** | **59–62** | **5,386.5 m** | seg10 | 14 → **10** |
| **S5** | **63–66** | **6,733.2 m** | "S13"(idx 13) | 18 → **12** |
| S6 | 67–69 | 8,090.7 m | seg15 | 26 → 16 |
| S7 | 71–73 | 9,437.3 m | seg18 | 28 |

- 망 XML [실행], plant `EXPECTED_SIGN_CELLS=[0,3,5,8,14,18,26,28]`(`make_reference_config.py:68`) [읽음], 셀→부모는 EO geometry [실행].
- **VISSIM DSD 의 뜻**: 희망속도 결정은 다음 DSD 를 만날 때까지 유지된다. 그래서 현재 구역 10(S4+S5 가 같은 값)을 쓰면 제한이 S6(8,091 m)까지 이어진다. B2(합류 7,603.7 m, 셀 22–23 = 7,334.5–7,663.1 m)가 적용 구역 **안**에 들어가 가속 구역이 0 이 된다.
- **선택: S4 만 제어하고 S5 = 110**
  - 적용 구역 5,386.5–6,733.2 m(1,346.7 m, link 2 통과 3 + 보조 1 차로)
  - 가속 구역 6,733.2 m 부터: B2 셀 22 시작까지 601 m, 합류 노즈까지 871 m, 측정소까지 921 m
  - 가속 구역 안의 요소: 진출 10481(6,826.8 m), 10483(7,240.3 m), 진입 10490(7,243.1 m)
- **기각한 대안**
  - (a) 구역 10 을 나누지 않기: 가속 구역 0 이라 요청을 위반한다.
  - (b) 구역 5(S2–S3)를 적용 구역으로: 제한이 S4 에서 110 으로 풀려 가속 구역이 2.2 km 가 되지만, 적용 구역이 B1(10681 합류 5,041.9 m)과 10639 합류를 덮는다. 먼저 켜지는 병목 B1 위에 VSL 을 거는 셈이다.
- **구역 분할 설정**: 하이브리드 튜닝에서만 `freeway.vsl_zone_heads.FW_E = [0,5,10,12,15]`.
  - 머리 12 로 해야 plant 와 writer 가 같은 값을 읽는다. plant 는 표지판 셀 18(부모 12)을, writer 는 매핑 세그먼트 "S13"(`segment_vsl(..., 13)` → `head_of_cell[13] = 12`)을 쓴다(`freeway_fd.py:150-157`, 어댑터 `:9062-9071`, `:12654-12667`) [읽음].
  - 13 으로 나누면 plant 는 S5 를 v 로, 실제 CSV 는 110 으로 써서 서로 어긋난다 [추론].
  - FW_W 는 [0,5,10,15] 그대로다. `vsl_zone_free` [0,1,2] 는 그대로 두고, 구역 3(머리 12)은 비자유(110)가 된다.
- **임계속도 관점** [실행]: B2 포락 최대 7,334 veh/h @ ρ 31(3차로) → v_cr ≈ 79 km/h. 삼각 적합으로는 7,665 @ 25.2 → 101 km/h. 80 km/h 로 내려도 가속 요구가 크지 않고 871 m 로 충분하다.

---

## 6. ALINEA 명세 (8개, 150 s)

```
r(k)   = clip[r_min, r_max]( r~(k-1) + K_R·(ô_m − o_m(k)) )
g(k)   = argmin_{g ∈ {0,2..10}, |g − g_act(k-1)| ≤ 2} |S(g) − r(k)|   (동률: 직전 녹색에 가까운 쪽, 긴 녹색)
r~(k)  = clip[ min S(도달가능 g), max S(도달가능 g) ]( r(k) )            # anti-windup
```

- 구현은 `diagnostic_profile.alinea_meter_step` 을 그대로 부른다.
- S(g) 는 물리 서비스 표이고, g_act 는 직전 **실제 적용** 녹색(SDMPC reference 의 `rw_meter_green_*`)이다.
- **K_R**: 70 veh/h/% × 미터 차로(10482·10681 = 140). 문헌(Papageorgiou et al. 1991 ALINEA)의 70 veh/h/% 를 기존 규칙 정책처럼 차로 배로 쓴다 [읽음: rule_policy]. 150 s 재척도는 하지 않는다(§4.2 논리).
- **r_min / r_max** = 표[2] / 표[10] = 255.6 / 1,512 veh/h × 차로. 최소 녹색 2 s, 주기 10 s(RED/GREEN), 변화 ±2 s/결정(`physical_ramp_branches` 사양).
- **측정 o_m(k)**: 측정소 m 의 두 번째 묶음 차로 행 평균이다(ID 는 json `measurement.stations`). 합류 끝 +50 m, 수용 링크 전 차로.
- **큐 override**: 없다. 기존 정책에도 없다. 결과적으로 램프 대기가 도시로 역류할 수 있다(§11 R4).
- **시작**: t = 900. 직전 녹색 10, r~ = 표[10].
- **목표 ô_m** 은 §7 표. 식별 불가 측정소는 선언 대체값 18.0 % 이다.
- **open-loop 재생** [실행]
  - FW_W 4개는 5시드 모두 한 번도 녹색 < 10 이 나오지 않았다.
  - 10681: 4–50 %, 10490: 26–43 %, 10484: 11–41 % 의 결정에서 제한했다.
  - 10639 는 ô 10.5 로 **65–83 %** 제한했고 녹색 2 까지 내려갔다.

---

## 7. 보정 (v3c1 NC fit 5시드)

### 7.1 방법 (계산 전 선언)

- 사전 선언: `calib/PREDECLARATION_CALIB.md` [실행]
  - 최초 sha 0d9f0f7e, 10:40:30
  - 선언 변경 1 추가 후 sha e94a7de5, 10:42:52, FD·임계값 계산 전
- **자료**
  - `D:/VISSIM_runs/20260927_v3c1/s{31,41,43,47,53}_v3c1nc` FZP(5 s 프레임)
  - s31 은 R-obs `.mer`(VISSIM 진입·이탈 시각 = 정확한 시간점유율)로 교차검증
- **창**: 150 s, 창 끝 300–9,000 s, 시드당 59창, 합계 295창.
- **양**
  - o: ±30 m 구간 공간점유율(선언 변경 1)
  - q: 같은 구간 Edie 유량
  - v: 공간평균 속도
  - B2 는 셀 22–23 차량 수 밀도와 셀 23 끝 통과 계수 q23
- **선언 변경 1(이유)** [실행]: s31 58창에서 .mer 정확값과 비교했다.
  - 5 s 점 표본: RMSE 1.8–4.1 %p
  - ±30 m 구간: RMSE 0.37–0.48 %p. 예외는 10646 1.15, 10639 1.89(편향 +1.5, 10682 분류 노즈 1.8 m 하류)
  - 통과 계수는 .mer 진입 수와 창 평균 ±0.1대 일치(10646 −4.7)
- **추정량**
  - O1(주): 합동, 1 %p 칸(밀도 2 veh/km/lane), 칸당 ≥ 8창, 칸별 q 90 백분위, 3칸 이동평균, 최대 칸 중심
  - 불확실성: 시드 군집 부트스트랩 1,000회(씨앗 20260929) 5–95 % + 시드별 O1(칸당 ≥ 3)
  - O2: 시드별 5분 최대 유량 창의 o
  - O3: 삼각 FD 교점
  - 식별 = 혼잡 창 ≥ 10 이고 O1 칸이 최상위 칸이 아닐 것
- 산출물: `calib/extract_windows.py`, `estimate_critical.py`, `openloop_replay.py`, `windows_s*.json`, `mer_s31_robs.json`, `critical_estimates.json`, `openloop_replay.json`

### 7.2 결과 — 합류 임계점유율 [실행]

| 미터 | 측정소 | 식별 | **O1 (%)** | 부트스트랩 5–95 | 시드별 O1 | O2 중앙[범위] | O3 | 혼잡창 | NC 최대 o |
|---|---|---|---|---|---|---|---|---|---|
| RM_C10480 (FW_W) | 26@3675.8 | 아니오 | 5.5 → **18.0** | 5.5–6.5 | 5.5×5 | 5.0 [4.7, 5.4] | – | 1 | 6.8 |
| RM_C10482 (FW_W) | 120@208.6 | 아니오 | 8.5 → **18.0** | 8.5–8.5 | 7.5–8.5 | 7.8 [7.4, 8.5] | – | 0 | 9.1 |
| RM_C10646 (FW_W) | 120@2390.1 | 아니오 | 5.5 → **18.0** | 4.5–5.5 | 4.5–5.5 | 5.1 [4.8, 12.8] | – | 1 | 18.1 |
| RM_C10644 (FW_W) | 120@3208.6 | 아니오 | 5.5 → **18.0** | 5.5–5.5 | 4.5–5.5 | 5.4 [4.7, 6.0] | – | 0 | 6.3 |
| RM_C10639 (FW_E) | 2@2014.2 | 예(쌍봉) | **10.5** | **10.5–25.5** | 21.5–27.5 | 12.5 [9.0, 24.6] | – | 170 | 33.7 |
| RM_C10681 (FW_E, B1) | 2@2357.4 | 예 | **17.5** | 16.5–19.5 | 15.5–18.5 | 17.5 [16.6, 18.2] | 10.2 | 185 | 28.3 |
| RM_C10490 (FW_E) | 119@445.1 | 예(평탄) | **19.5** | 13.5–20.5 | 12.5–19.5 | 17.7 [14.4, 22.7] | 11.9 | 79 | 32.2 |
| RM_C10484 (FW_E, B2) | 24@215.7 | 예(평탄) | **18.5** | 14.5–18.5 | 13.5–19.5 | 16.6 [15.9, 19.5] | – | 49 | 23.1 |

- FW_W 네 곳의 O1 은 최상위 칸이다. 즉 임계가 아니라 관측 상한이다. 선언대로 식별된 넷의 O1 중앙값 **18.0 %** 로 대체한다. 결과적으로 FW_W 미터는 사실상 열린 채로 남는다. v2 규칙 RM 의 FW_W 역류 손해(+1,530) 경로를 피한다 [추론].
- **10639**: 포락이 쌍봉이다. 자유류 봉우리 10.5 %(7,141)와 B1 대기열 봉우리 21–28 %(7,000–7,250)가 거의 같은 높이다.
  - 측정소가 B1 합류(5,041.9 m) 293 m 상류라, B1 이 켜지면 대기열 안에 들어간다.
  - 선언 규칙의 답은 10.5 이지만 부트스트랩 폭이 15 %p 다. **사용자 결정 필요**(§12).
- s31 한 시드로 .mer 정확값과 구간 추정의 O1 을 비교했다: 10484 17.5/17.5, 10681 17.5/15.5, 10490 16.5/15.5, 10639 25.5/27.5, FW_W 넷은 같거나 1 %p 안.

### 7.3 결과 — B2 임계밀도 (셀 22–23, 3차로) [실행]

| 추정 | 값 |
|---|---|
| **O1** | **31.0 veh/km/lane**, 포락 최대 7,334 veh/h |
| 부트스트랩 5–95 | 25.0–35.0 |
| 시드별 O1 | 31: 49, 41: 31, 43: 29, 47: 49, 53: 31 (쌍봉) |
| O2 | 중앙 35.3 [31.0, 38.8], 5분 최대 7,284–7,512 veh/h |
| O3 | 25.2 (q 7,665) |
| 혼잡창 / 창 | 63 / 295 |
| o_10484 ↔ ρ | o = 3.65 + 0.356 ρ (r 0.93) → ρ̂ 31 ≈ o 14.7 % |

- 포락이 ρ 25–31 에서 7,290–7,334 로 평탄하다. 그래서 임계값의 식별력은 약하다. 이는 합류 병목에서 흔한 모양이다 [추론].

---

## 8. 하이브리드 통합 계획 (코드 단위, 아직 안 씀)

### 8.1 스위치 (전부 config 키, 없으면 비트 동일)

- `adapter.sdmpc_freeway_rule`: `{mtfc_vsl: {...}, alinea: {...}}`(json 의 두 절 그대로). 없으면 None 이고, 모든 경로가 종전과 같다.
- `freeway.vsl_zone_heads.FW_E = [0,5,10,12,15]`: 하이브리드 튜닝 사본에만 둔다.
- `execution.signal_vbs_config` → `scenario/lane_native_b110_rule.vbs`: 기존 파일 + `RW_RULE_OBSERVATION = True` 한 줄.
- 튜닝 파일: `diagnostics/sdmpc_n31_20260924/config_n31_v2_hybrid_rule.json` = config_n31_v2 + 위 세 가지. `max_vsl_step` 40 은 그대로 둔다.

### 8.2 새 모듈 `evaluation/controllers/freeway_rule_hybrid.py`

- `configure(tuning, cfg)` 는 다음을 검증한다.
  - wu-link + `adapter.sdmpc` 존재
  - physical8
  - `vsl_set ⊇ {80,90,100,110}`
  - FW_E 머리에 12
  - 측정 ID 가 망의 두 번째 묶음과 일치
  - 목표·이득이 유한하고 양수
- `observe(state_json, spec)`
  - `rule_observation.completed_interval_available`, `window_end_sec == sim_sec`, `window_start_sec == sim_sec−150` 을 확인한다(어댑터 `:13740-13747` 과 같은 검사).
  - **차로 행을 measurement_no 로만 골라** 측정소 o 를 계산한다. 측정소 집계값은 쓰지 않는다.
- `decide(reference, history, obs, spec, cfg)`
  - ALINEA 8개: `alinea_meter_step`, 직전 녹색은 reference 에서 가져온다.
  - MTFC: §4.2.
  - 반환: 녹색 8, 구역값 {FW_E 머리 10 = v, 0/5/12/15 = 110, FW_W 전부 110}, `next_history`(r~ 8, b~, o(k), v(k)), 감사 기록
  - 직전 **실제** 명령 대비 녹색 ±2, VSL ≤ 20 을 스스로 검사한다.
- `apply(reference, command, cfg)`
  - `physical_ramp_branches.candidate_from_greens(reference, reference, cfg, greens)` 로 녹색을 반영한다.
  - 모든 셀 `vsl[f'{link}__seg{i}'] = 구역값[head_of_cell[i]]`, 링크 키 = 최솟값(`diagnostic_profile.py:72-74`, `sdmpc.py:405` 와 같은 규칙).

### 8.3 SDMPC 안에서 고정하는 방법

1. 어댑터가 `run_joint_owner_decision` 전에 규칙 명령을 계산한다. 이력은 `previous_path` 의 `diagnostics.hybrid_rule_next_history` 에서 읽는다. runner 는 적용 영수증이 있는 행동만 넘긴다.
2. `run_joint_owner_decision(..., freeway_rule=cmd)` → `sdmpc.solve(..., freeway_rule=cmd)` 로 넘긴다. 키워드 기본값은 None 이다.
3. `sdmpc.py:558` 직후 `reference = hybrid.apply(reference, cmd)` 한다. 즉 `callbacks`(`:562`, 이동 상자·NUF 초기화·PFO 온기동)와 `Coordinates`(`:573`)가 **모두 규칙 명령에 앵커**된다.
4. `Coordinates`(`sdmpc.py:325-341`)에서 정책 `freeway_fixed` 이면 미터·VSL 축의 `allowed = [a]` 로 폭을 0 으로 만든다(I1).
   - V0 확인 재생에서 `max_vsl_step 0` 인 폭-0 VSL 축이 문제없이 돌았다(worklog §2, V0_CHECK).
   - 미터 폭 0 은 `build_fixed_move_box` 가 사양 ±2 와 다른 한계를 거부하므로(`joint_owner_neighbors.py:69-71`) 상자가 아니라 좌표 쪽에서 만든다.
   - 대안 I2(축 삭제)는 미분·서로게이트 코드가 축 종류를 가정하는지 전수 확인해야 해서 이번 1회 런에는 권하지 않는다.
5. `SequenceCoordinates`(`sdmpc_sequence.py:108-167`)는 블록 1–2 도 같은 폭-0 축을 가진다. 따라서 **예측 지평 450 s 내내 규칙 명령 유지(zero-order hold)** 다. 실제로는 규칙이 다음 결정에 명령을 바꾸므로 예측과 다를 수 있고, 이는 알려진 한계다.
6. 쓰기: 기존 `write_action_csv`(어댑터 `:12795-12840`)가 그대로 쓴다.
   - 미터 = `physical_commands`
   - VSL 66행 = `segment_vsl` → 구역 분할로 DSD 59–62 = v, 63–66 = 110
   - `verify_joint_written_action` 이 응답과 CSV 가 같은지 확인한다.
7. 기록: 행동 JSON diagnostics 에 다음을 남긴다.
   - `hybrid_rule`: 관측 차로 행, raw·bounded 요청, b~, v*, v, 녹색, 목표, 이득
   - `hybrid_rule_next_history`
   - `python_hash_seed`: `os.environ.get('PYTHONHASHSEED')`. 하이브리드일 때만 기록해서 기본 경로를 비트 동일하게 둔다.

### 8.4 VBS

- `run_real_world_stackelberg_controller.vbs`
  - `:226-229` Dim 목록에 `RW_RULE_OBSERVATION` 을 추가한다. Option Explicit 이고 config 를 ExecuteGlobal 하기 때문이다(`:228` 주석).
  - `:2821` 조건에 `Or RW_RULE_OBSERVATION = True` 를 추가한다. 변수가 없으면 Empty 라 거짓이므로 다른 런의 state JSON 은 바이트가 같다.
- 150 s DataColl 은 obs150 이 이미 켠다(`:4935-4941`). 측정 간격이 결정 간격과 같아 `RuleObservationJson` 의 `(Current,k,All)` 이 성립한다.
- 대안 M2(VBS 무수정): 어댑터가 state 의 `obs150.mer` 바이트 범위를 다시 읽어 910059–087 의 진입·이탈로 점유율을 계산한다. 창을 넘는 점유(정지 차량)를 이력으로 넘겨야 해서 코드가 더 크다. M1 을 권한다.

### 8.5 발사와 환경

- 새 브랜치(예: `claude/hybrid-rule-20260929`, 9ed2ef0 에서)에 커밋해서 깨끗한 트리로 만든다.
- `run_sdmpc_n31.ps1 -Freeze -Tuning diagnostics\sdmpc_n31_20260924\config_n31_v2_hybrid_rule.json -Name sdmpc31_v3c1_hyb_s31 -SimPeriod 9000 -Seed 31 -PreflightOnly` 를 먼저 돌리고, FRZ 에서 WMI 로 분리 발사한다.
- **PYTHONHASHSEED=0**
  - WMI `Win32_Process.Create` 는 호출자 환경을 넘기지 않는다 [추론: Windows 동작]. 그래서 명령줄 안에서 세운다: `powershell -NoProfile -Command "$env:PYTHONHASHSEED='0'; & 'D:\VISSIM-merge\tools\run_sdmpc_n31.ps1' ..."`.
  - 이후 사슬(runner → watchdog `& powershell` → `Start-Process cscript` → `shell.Exec python` → spawn 워커)은 모두 상속하고, 지우는 곳은 RW_* 와 PATH 뿐이다 [읽음].
  - vendor `state.py:1306` 은 고치지 않는다. 적용 여부는 §8.3-7 의 `python_hash_seed` 로 런 중에 확인한다.
- 좌석: 전체 ≤ 3·dev 0(또는 `-AllowConcurrentDev`: 전체 ≤ 2·dev ≤ 1). 결정당 SDMPC 워커가 8+8 이라 한창일 때 코어 약 16개를 쓴다 [추론: 설정값].
- 예상 벽시계: 결정 340–600 s × 55 ≈ 8–11 h(V5b 30,204 s 실적 기준) [읽음].

---

## 9. 발사 전 오프라인 관문 (한 번에 하나, BELOW_NORMAL, NUMBA_CACHE_DIR=…/nbc_hyb)

| # | 시험 | 통과 기준 |
|---|---|---|
| H0 | 키 부재 비트 동일: 기본 튜닝으로 R-obs 결정 재생 | T5 61/61 IDENTICAL(기존 도구, `--tuning` 있음) |
| H1 | 단위: ALINEA 한 단계 = `alinea_meter_step`, MTFC 양자화·속도제한·anti-windup·첫 결정 P=0, 경계값 | 전부 통과 |
| H2 | 관측 선택: 이름 중복 두 묶음이 섞인 합성 rule_observation 에서 측정 ID 로만 고름. 측정소 집계를 쓰면 실패하도록 | 통과 |
| H3 | 구역 분할: `vsl_zone_heads.FW_E=[0,5,10,12,15]` + FW_E 머리10=90 일 때 CSV DSD 59–62=90, 63–66=110, 나머지 110, 66행. plant 결합표 `vsl_zone_head_of_cell` 에서 표지판 셀 14→10, 18→12 | 통과 |
| H4 | 결정 재생(t=900, 1,050, 2,100): R-obs state 에 R-obs .mer 로 만든 rule_observation 을 넣어 하이브리드로 재생 | 예외 0, 미터·VSL 축 폭 0, 결정 시간 기록, verify_joint_written_action 통과. `make_replay_state_v2.py compare` 는 **`--tuning` 없이** |
| H5 | 결정론: H4 한 결정을 PYTHONHASHSEED=0 으로 두 번 | 바이트 동일, `python_hash_seed == "0"` |
| H6 | 발사 뒤 조기 확인(런 폴더 읽기만) | `state_000150.json` 에 rule_observation 이 있고 910059–087 차로 행이 있음. t=900 행동 JSON 에 hybrid_rule |

- 금지 시험(watchdog·cscript·ps1 시험 6종)은 쓰지 않는다. VBS 변경은 H6 으로만 확인한다.

---

## 10. 짝과 판정

- 짝: R-obs `sdmpc31_v3c1_nc_s31`(NC s31 과 FZP 바이트 동일). 900.1 s 까지 프레임이 같아야 유효한 짝이다(V5b 관례).
- 지표 넷(① fw_e_main, ② 동측 19, ③ Ω, ④ 전체+미삽입)을 따로 보고한다.
- 네 층으로 분해한다: 미터 명령 이력, VSL 명령 이력, 램프 대기, 도시 링크.
- **판정하지 않는다**: 한 시드이고 탐색 런이다. FW_E 결론은 J1(≥ 3시드 짝)으로만 낸다.

---

## 11. 위험

- **R1 MTFC 권한 거의 0** [실행+추론]: B2 임계속도 ≈ 79 km/h, 적용 구역은 4차로(용량 약 1,900/차로 × 4)이고 L1 의 80 km/h 용량 감소는 ≤ 3.6 %, B1 방류(≈ 7,000–7,500)가 이미 상류를 막고 있다. 그래서 S4 의 VSL 로 B2 유입을 용량 아래로 붙잡을 수 없다. 효과는 대부분 속도 저하(TTT 비용)다. N1/N1F 와 같은 결론이다.
- **R2 10639 과잉 미터링**: ô 10.5 에서 open-loop 로 65–83 % 결정이 녹색 2–8 이다. 측정소가 B1 대기열 안에 있다. 하류 병목에 반응하는 ALINEA 의 알려진 한계이며, 원격 병목용은 PI-ALINEA 다 [추론]. 램프 대기가 link 70 쪽 도시로 역류할 수 있다.
- **R3 B2 이중 적분**: ALINEA 10484(ô 18.5)와 MTFC 가 같은 측정소·같은 목표를 적분한다. 10490 도 가깝다. 진동 위험이 있다. Carlson et al. 2014 는 split-range(RM 이 포화될 때만 VSL)로 묶었다 [추론]. 선택지로만 제시한다.
- **R4 큐 override 없음**: 기존 정책 그대로라 램프 대기가 도시로 역류할 수 있다. SDMPC plant 는 램프 저장고를 보지만 규칙층은 모른다.
- **R5 예측의 zero-order hold**: 도시 계획이 규칙의 다음 명령 변화를 모른다.
- **R6 관측 결함**: 이름 중복 두 묶음. 차로 행을 ID 로 고르지 않으면 상·하류가 섞인다(H2).
- **R7 이득 미검증**: 1차 원문을 확인하지 못했다. 잠정값은 2차 요약 + 환산식에서 나왔다.
- **R8 목표 식별력 약함**: 10484·10490 포락 평탄, 10639 쌍봉, B2 밀도 시드별 쌍봉(29–49).
- **R9 J1 결함 둘**: PYTHONHASHSEED 는 환경으로 완화한다. 재생 비교는 `--tuning` 없이 한다.
- **R10 자원**: 결정당 코어 약 16개, 8–11 h. 도시 묶음 2·N1F 와 동시 실행이다.
- **R11 새 VBS 분기**: `:2821` 확장은 런에서만 검증된다(H6). 실패하면 t=900 결정에서 관측 누락 예외로 멈춘다(어댑터 검사 복제).
- **R12 구역 분할**: 110 이 아닌 값에서만 plant 에 영향이 있다. H3 로 확인한다.

---

## 12. 사용자 결정이 필요한 것

1. **Carlson 이득**: (a) 원문(SNU 접근)으로 K_P·K_I·T_c 를 확인해 넣는다, 또는 (b) 잠정값 K_P 0.0133·K_I 0.0813 /%p 를 받아들인다. 대안으로 I 형만(K_P 0)도 가능하다.
2. **10639 목표**: 선언값 10.5(과잉 미터링 위험) / 시드별 O1 중앙 25.5 / 10639 는 열어 두기(표[10] 고정). 권고는 규칙 준수 쪽이면 10.5 를 쓰되 R2 를 감수하는 것이고, 운영 쪽이면 25.5 다.
3. **MTFC 목표 단위**: 측정소 O1 18.5 %(선언) 또는 셀 밀도 ρ̂ 31 ↔ 14.7 %.
4. **B2 이중 제어**: 요청 그대로 독립 / split-range(RM 포화 시에만 VSL).
5. **VBS 수정(M1)** 또는 .mer 재독(M2).
6. 구현·커밋·푸시 여부(요청에는 "한 번 돌려 달라"만 있다. 이 문서는 설계까지다).

---

## 13. 파일

- `hybrid/HYBRID_DESIGN.md`(이 문서), `hybrid/hybrid_parameters.json`
- `hybrid/calib/PREDECLARATION_CALIB.md` (sha e94a7de5…), `extract_windows.py`, `estimate_critical.py`, `openloop_replay.py`, `stations.json`, `windows_s{31,41,43,47,53}.json`, `mer_s31_robs.json`, `critical_estimates.json`, `estimate_run.txt`, `openloop_replay.json`
- 읽은 자료
  - 문헌 추출본: `scratchpad/vsl-fixed-dsd/work/{grumert2018,vt_thesis}.txt`
  - 결과: EO `scratchpad/vsl-fixed-dsd/capdrop/eo/s31_v3c1nc/geometry.json`, R-obs `D:/VISSIM_runs/20260928_sdmpc31_v3c1/sdmpc31_v3c1_nc_s31/`, v3b S0e `vsl_readback.csv`
