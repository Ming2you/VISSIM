# 도시 묶음 2 — 단계 6 보고 (U6 W측 램프 분기 `physical_diverge_v1`)

- 작성: 2026-09-29 23:05 시작 → 2026-09-30 02:40 완료. 이전 시도의 단계 6 부분 결과는 없었습니다(`B/impl`에 `stage6` 없음, 시작 시 트리 diff `baabf7af…` = STAGE5 최종값 [실행]).
- 계획: `B/BATCH2_PLAN.md` §4.6(표 A1–A4·B1–B3·C, 재사용 구성요소, 건드리지 않는 것, 새 상태 필드), §5.1 U6 행, §5.5 LIVE, §6.5 G6(9상태 예비), §7 단계 6 행과 멈춤 규칙(G-ID 실패는 어느 단계든 멈춤), 설계 `B/u6_diagnosis.md` §7.1–7.5·§8·§9, 부록 C. 사용자 결정: C3 = U4+U5+U6(전부 아니면 전무), Q1·Q2, Q3 = v3b 폐루프 없음.
- 대상 트리: `D:/VISSIM-merge/sim3-n31-urban-b2` (브랜치 `claude/urban-batch2-20260928`, HEAD `cf3ce37`). 변경은 **커밋하지 않고** 작업 트리에 남겼습니다. push·다른 브랜치/워크트리 조작, VISSIM·cscript 시작/종료는 없습니다.
- 표기: **[실행]** 이번에 직접 돌리거나 계산한 값 / **[읽음]** 파일에서 읽은 값 / **[추론]** 직접 증거 없이 끌어낸 판단.
- 약어: B = `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/urban-b2`, S6 = `B/impl/stage6`, R6 = `S6/run6c`(최종 재생 연쇄), H = `B/harness`, W = b2 트리, RD = `W/evaluation/controllers/ramp_diverge.py`(새 모듈), A = 어댑터, UFA = `urban_flow_accounting.py`, LOR = `lane_offramp_runtime.py`, RS = `runtime_setup.py`, HSC = `head_saturation_capacity.py`, SHG = `shared_head_groups.py`, T2 = `W/diagnostics/sdmpc_n31_20260924/tests/test_n31_urban_batch2.py`, EV = `W/diagnostics/sdmpc_n31_20260924/urban/ramp_diverge_v3b_20260929.json`(U6 증거, `0aacabf1…`). 줄 번호는 최종 작업 트리 기준입니다.

---

## 0. 결론

**멈춤 규칙에 걸린 것은 없습니다(stop=false).** 키 없음 비트 동일(G-ID (a)(b) 122/122 IDENTICAL, SDMPC S1 3600 기록·단계 1과 같음)이 성립하고, U6 설치는 99상태 모두 통과했습니다. U6를 계획 §4.6 표대로 A1–A4·B1–B3·C 모두 한 키(`urban.ramp.admission_policy: "physical_diverge_v1"` + `urban.ramp.diverge_evidence`)로 구현했고, 단계 4·5의 "U6 미구현" 거부(`c3_not_implemented`)를 실제 U6 설치로 바꿨습니다. 이제 C3 세 키가 실제 코드로 설치됩니다(하네스 메모리 패치 없음).

| 항목 (계획 위치) | 결과 | 근거 |
|---|---|---|
| U6 모듈 (§4.6) | RD 새 모듈(693줄). 정책·증거 검증, 핀된 inpx 재계산 대조, 런타임 카탈로그 대조, A2 초기 저장고 태그, A3 게이트 지연 착지, 도착 분할, C 계수·결정 기록, 설치 끝 확인, 워커 확인 | [실행] §2 |
| A1 / A4 / B1 / B2 / B3 설치 자리 | A:3411-3415·:3440-3446(A1), A:3493-3498(A4), A:2897-2902(B1 τ), UFA:25-33(B1 진입 지연, 5곳에서 사용), A:3213-3219(B2), A:8632-8642(B3) | [실행] §2 |
| 단위 시험 (§5.1 U6 행) | T2 **94 OK**(단계 5의 74 + U6 20) | [실행] §3 |
| 스위트 | 40실행, 단계 5 대비 **회귀 0**, 사라진 실행 0(n31_batch2 94 OK) | [실행] §4 |
| 설치 전수 (fail-closed 확인) | C3 전체 튜닝으로 R-obs-b 61 + S1 19 + S0e 19 = **99/99 설치 통과**(U4·U5·U6 설치 끝 확인 포함). 개발 중 두 번 A2의 fail-closed가 걸렸고(연결로 위 저장고 차량, 정지선 뒤 회전 연결로 위 저장고 차량), 물리 규칙으로 고쳤습니다 | [실행] §5 |
| **G6 예비 (§6.5, 9상태)** | C3 실제 코드: **G6-1·2·4·6·7·8·9 통과, G6-3·G6-5 경계 실패**(G6-3 MAE 5.47 > 5, G6-5 편향 +5.69 > 5). U1+U3 기준은 G6-9 외 전부 실패 | [실행] §6 |
| S1·S0e 상태(무제어 행동, 서술) | G6-1~4가 R-obs-b와 같은 방향으로 좋아짐(두 런 모두 onW 큐 p90 115~118 → 0~0.9, 10490 유입 편향 +20~23 → −3.5) | [실행] §6.3 |
| 세 경로 스모크 (T2700, 450 s) | 정확 = 코호트(W측 전이 합 10종 차이 0.0, 목적값 차 2.3e-13), 연속(tangent 워커)이 RD를 AST 변환으로 적재해 완주. U5 단언 초과 최대 6.7e-16 | [실행] §7 |
| G-ID 키 없음 (a)(b) + SDMPC S1 3600 | R-obs-b 61 × 기본·U1+U3: `MRS compare` **IDENTICAL 122/122**, 한 스텝 포착 15필드·설치 스냅숏 61/61씩 단계 1과 같음, action 차이는 시간뿐. SDMPC S1 3600: 녹색·offset·목적값·tangent 계수가 기록 및 단계 1과 같음(action_contract만 다름, 알려진 VSL 100/110) | [실행] §8 |

---

## 1. 재개 확인

- `B/impl/stage6`가 없었고, 시작 시 `worktree_diff_sha256` `baabf7aff9f3…` = STAGE5 최종값이었습니다 [실행]. 새로 시작했습니다.
- 재사용: `H/_prov.py`, `H/u40_probe.py`, `H/sdmpc_replay.py`, `H/run_suites.py`, `H/compare_suites.py`, `H/u6_capture.py`(생성기의 원본), `H/u5_install.py`·`H/u5_paths.py`(생성기의 원본), `B/u6/analyze_u6.py`와 `B/u6/fzp/*.json`(u6 진단의 지표 정의·FZP 추출, 읽기만). 비교 기준: 단계 1 키 없음 재생(`B/impl/stage1/probe/b2_{base,u1u3}`, `…/sdmpc/b2_s1_T3600`), 단계 5 최종 스위트(`B/impl/stage5/suites`), u6 진단 캡처(`B/u6/capture/{base,u13_base,vFULLr,vFULLrK,base1004}`, cf3ce37 트리).

---

## 2. 바꾼 것 (작업 트리, 커밋 안 함)

| 파일 | 줄 | 내용 |
|---|---|---|
| RD 새 모듈 (693줄, LF) | 전체 | `policy` :129, `check_tuning` :143, inpx 파서 `_geometry` :170, `configure` :199, `capacity` :372(A1), `split_table` :380(B3), `initialize` :394(A2·A3 고정값), `split_arrival` :540, `land_gate` :563(A3), `observe_gate_ramp` :598(C), `finalize` :621, `check_worker_runtime` :662, `decision_diagnostics` :672 |
| A | :2897-2902 | B1: `_legsplit_wout_rate`의 길이 = 증거의 W_out 물리 길이(뷰가 있을 때만) |
|  | :3213-3219 | B2: `install_offramp_direct_landing` 끝에서 증거의 직행 착지(OR_D_E, 10483)를 `SC1001_W_tail`로(옛 규칙 값이 `SC1001_W_out`인지 먼저 확인) |
|  | :3411-3415, :3440-3446 | A1: `install_gate_onramp_queue`. 뷰가 있으면 `gate_onramp_queue_capacity_veh_h`를 읽지 않고 `ramp_diverge.capacity`(커넥터 차로 × 1800). 뷰 없이 `diverge_evidence`만 있으면 거부(죽은 키) |
|  | :3493-3498 | A4: `_apply_gate_onramp_beta`에서 퇴역 movement(`SC1004_W_to_onE`)의 몫을 기록하고 0으로, 형제는 기존 식으로 재정규화 |
|  | :4337-4342 | C3 설치 래퍼: HSC 설치(U4) 뒤 `ramp_diverge.configure` |
|  | :8632-8642 | B3: `install_boundary_out_ramp_split`에서 증거 분할(옛 램프 그룹 이름) |
|  | :14243-14248 | C: `projection_diagnostics['ramp_admission']`(뷰가 있을 때만) |
| UFA | :25-33 | `_entry_delay_steps`: W_out 저장고 진입은 1 스텝, 그 밖은 `_uqm._link_delay_steps` 그대로 |
|  | :41, :159, :661 | 회랑 수신(known-route 코호트 만기), 옛 off-ramp 배수, 정규 방류의 방출 예약이 위 도우미를 씀 |
|  | :208, :381-389, :416-423, :517-519 | 뷰 읽기 1회, A2 도착 분할 분기, A3 게이트 착지 분기, C 계수 |
| LOR | :81, :117, :125 | 직행 착지와 movement 배수의 방출 예약이 `_entry_delay_steps`를 씀 |
| RS | :237-241, :285-289, :329-331 | A2 초기화(짝 예약 뒤·lane plant 앞), 설치 끝 확인(U5 finalize 뒤), 워커 확인 |
| HSC | :269-270 | 단계 5의 `c3_not_implemented`를 지우고 U6의 `check_tuning`을 부름(U4 설치 전) |
| T2 | 설명, :1103-1171(U6 증거 핀·`c3_tuning`·`u4_install`·`c3_install`), U4 시험 4곳 갱신, :1970-2515(U6 시험 20개) | §3 |

- 키가 없으면 RD는 import되지 않습니다. 모든 import가 함수 안에 있고 C3 설치 또는 뷰 확인을 거쳐야 도달합니다(T2:2507 정적 시험). 키 없는 경로에서 새로 도는 것은 뷰 없음 확인(`getattr(net, 'ramp_diverge', None)`)과 `diverge_evidence` 키 부재 확인뿐입니다.
- 줄바꿈: 추적 파일은 원래 방식을 유지했습니다(UFA·A·HSC LF, LOR CRLF, RS 혼재는 편집한 자리의 방식). 단계 5의 줄바꿈 보존 치환 도구를 `S6/eol_edit.py`로 복사해 썼습니다 [실행: 편집 전후 CR 수 대조, UFA/A/HSC 0 → 0, LOR 176 → 176].

### 2.1 U6의 흐름 (계획 §4.6 표)

- **configure** (RD:199, 호출 A:4337-4342). U4 설치 직후, 게이트 큐 설치 전입니다.
  - 핀: `diverge_evidence` sha, 스키마 `ramp-diverge/v1`, 증거 망 sha = 스냅숏 sha = U4 표 망
  - **inpx 재계산 대조**(핀된 inpx 한 번 파싱): 게이트 on-ramp 둘(커넥터·차로·분기 링크·위치, 결정 1136 경로·relFlow 몫, 분기 앞 링크와 길이), 퇴역 10639(이 커넥터를 지나는 정적 경로 = 1134:3 하나), 정지선 경로 1136:2(경로·몫·저장고 링크 32/129/127), W_out 둘(결정 1137/1135의 위치, 링크 길이·합, 출구별 경로·분기 위치·relFlow 몫), 직행 착지 10483(착지 링크·위치, 지나는 정적 경로 1131:3, 그 경로가 W_out 램프 커넥터를 타지 않고 꼬리 출구로 나감)
  - **런타임 카탈로그**: 게이트 저장고가 boundary-in, 게이트 on-ramp movement가 그 저장고의 ramp movement이고 유지 목록(kept)에 있음, 유지 목록 = 증거의 셋, 물리 램프 스펙의 `out_link_receivers`로 옛 램프 그룹 이름 역변환, lane plant 매니페스트의 off-ramp 그룹 문서로 10483의 그룹(OR_D_E, 결정 1131) 확인
  - 결과 뷰 `cfg.network.ramp_diverge`: 용량, 게이트 거리·오프셋, 정지선 경로 지지점(링크와 연결로), 경로 사전(저장고 링크를 지나는 정적 경로 8개), W_out 길이·분할(옛/물리 이름), 직행 착지. pickle 약 2.2 kB [실행 T2700] (T2는 < 8 kB를 확인)
- **A1** 게이트 on-ramp 용량 = 커넥터 차로 × 1800: onW 3,600, onE 1,800, 퇴역 SC1004_W_to_onE 1,800(10639는 1차로라 옛 값과 같음) [실행 T2700 설치]
- **A2** (RD:394, RS:237-241). 짝 예약(`conservative_initial_transit`) 뒤, lane plant 앞입니다.
  - 전제(fail-closed): 도착 예약 = 방출 예약(정확히 같은 dict), 예약 합 = 저장고 점유(±1e-6), 투영 할당의 저장고 합 = 점유
  - 적격: 링크 32·129(와 그 사이 연결로 10778) 위 차량은 **관측 정적 경로의 남은 경로**로 정합니다. 10482 → onW, 10490 → onE, 둘 다 없음 → 정지선. 경로가 없는 차량만 게이트 β(129는 β_onE/(1−β_onW)). 경로가 있지만 그 경로에 현재 링크가 없으면 "unresolved"로 세고 β를 씁니다. 127·10777·정지선 뒤 링크 위 저장고 차량은 램프 몫 0
  - 도착: 분기까지 거리 ÷ max(차량 속도, 같은 링크 차량 평균 속도, 50/2.5 = 20 km/h), `ceil`, 최소 1 스텝
  - 정지선 몫: (저장고 − 램프 몫)을 원래 +15/+105 s 덩어리 비율로, 정지선 movement β 비율로 나눔
  - 도착·방출 예약을 태그 합으로 새로 씀(점유 불변). T2700: 저장고 244대 → 램프 146.55(onW 94.83, onE 51.72), 정지선 97.45, 예약 105스텝 [실행]
  - A3의 추가 지연(결정마다 고정): 게이트→분기 거리(onW 1,028.6 m, onE 1,329.6 m) ÷ max(링크 32 평균 속도, 20 km/h) − 유입 지연 34 스텝. T2700: 135 / 185 스텝 [실행]
- **도착 분할** (RD:540, UFA:381-389): 그 스텝의 태그를 그대로 movement에 넣고, 태그 밖 도착분(0이어야 함, 계수)은 β 분할. 태그가 방출보다 크면 `ArithmeticError`
- **A3** (RD:563, UFA:416-423): 게이트 착지에서 이 스텝의 지연분(태그)은 그 movement로, 새 착지분은 β로 나눠 램프 몫만 `transit:gate:in_SC1001_W`에 `extra` 스텝 뒤로 다시 예약합니다(재고 이동이 없으므로 전이 기록 없음). 지연분이 착지보다 크면 `ArithmeticError`
- **A4**: 퇴역 movement의 β = 0, 관측/폴백 몫은 `_LEGSPLIT_LAST['gate_onramp_beta_retired_share_…']`와 결정 기록에
- **B1** τ = 734.24 m / 60 km/h = 44.05 s(SC1001), 351.35 m → 21.08 s(SC1004). W_out 진입의 방출 예약은 1 스텝이며, known-route 코호트 만기(UFA:41)와 LOR 직행 착지(LOR:117)도 같은 도우미로 맞췄습니다
- **B2** 10483 → `SC1001_W_tail`(`lane_plant_tail_stores`에 이미 있음). 모든 소비자(LOR 포트, link_predictor, observation_projection, UFA 착지)가 같은 속성을 읽습니다
- **B3** SC1001_W_out: RM_C10484 0.5 / RM_C10480 1/3 / free 1/6, SC1004_W_out: RM_C10681 0.6 / RM_C10646 0.2 / free 0.2. SC1004 known-route prior도 같은 값을 읽습니다(route_choice_corridor의 prior가 `boundary_out_ramp_split`을 읽음) [읽음]
- **C** `projection_diagnostics['ramp_admission']`: 용량, 퇴역 몫, W_out τ·분할·출처, W_out 진입 방출 스텝(1), 직행 착지, A2 초기 사실(링크별 부류·평균 속도·추가 지연·예약 스텝), 이 프로세스의 계수(태그/태그 밖 도착, 게이트 착지·지연 착지 대수), 게이트 램프별 요청 초·용량/재고/진입 여유 구속 초·최소 진입 여유. 결정 JSON에서 약 2.5 kB(압축 JSON; action 안 들여쓰기 3.2–3.4 kB) [실행]
- **finalize** (RD:621, RS:285-289): 회계 substep과 leg split이 설치됨(아니면 vendor substep이 태그를 무시), A2가 돌았음, A1 용량·A4 β 0이 최종 런타임에 남음, LOR의 10483 포트 목표 = 꼬리, `offramp_direct_tail_by_offramp`·`lane_plant_tail_stores` 일치, B3 분할이 물리 이름으로 증거와 같음, 검지 매핑에서 W_out 링크(31·124, 68·121)와 게이트 링크(32·129·127)의 소유 저장고가 증거와 같음

### 2.2 계획이 정하지 않았거나 계획과 다르게 한 것 (판단, 확인 부탁)

1. **정책 값 `""`는 거부합니다.** u6 진단 §7.1은 `""`를 "현행"으로 적었지만, C3 결합은 키의 **존재**로 판정합니다(`c3_keys_present`). 그래서 `""`는 C3 키를 이름만 넣은 상태가 되고, 다른 두 키와 함께 오면 U4+U5만 돌게 됩니다. 명시적 오류로 막았습니다(RD:129).
2. **적격을 결정 1136만이 아니라 모든 정적 경로의 남은 경로로 판정합니다.** 계획 문구는 "1136 경로 1/2/3, 경로 없는 차량만 β"입니다. 129 위에는 off-ramp 10491로 들어온 1132:2 차량(정지선행)이 있고, 문구대로면 "경로 있음·1136 아님"의 처리가 정해지지 않습니다. 남은 경로에 램프 커넥터가 있는지로 정하면 1136은 계획과 같고, 1132:2는 정지선(물리적으로 맞음)입니다. 대리 변형 vFULLr는 이런 차량에 β를 줬습니다. 차이는 상태당 0~1대입니다 [실행 T2700: 129의 1132:2 1대].
3. **평균 속도는 링크별 평균(차량별 하한 없음)이고 전체 하한은 20 km/h입니다.** 계획 문구("같은 링크 평균 속도")를 따랐습니다. 대리 변형은 32+129를 합친 평균에 차량별 10 km/h 하한을 썼습니다. 도착 스텝은 `ceil`입니다(shared_approach 규약; 대리는 `round`). A3 속도는 링크 32 평균(차량이 없으면 `urban_avg_speed_km_h` 50)에 같은 하한입니다.
4. **저장고의 물리 지지점을 넓혔습니다(개발 중 fail-closed 두 건).** [실행]
   - T1800: 저장고 189대 중 2대가 정지선 경로의 1 m 연결로(10778: 32→129, 10777: 129→127)에 할당되어 "링크 합 ≠ 점유"로 설치가 멈췄습니다. 연결로 위 차량은 다음 링크 시작점으로 셉니다(증거의 거리 규약과 같음, 오차 ≤ 1 m).
   - T450·T600: 정지선 뒤 회전 연결로 10695(127→38) 위 차량이 저장고에 할당되어 있었습니다. 두 분기를 모두 지난 차량이므로 램프 몫 0으로 두고 기록합니다(`links_outside_route`). G6 9상태 중 4상태에 있었습니다.
   - 두 경우 모두 이전 시도의 산출(`S6/run6`, `S6/run6b`)은 버렸고, 최종 판정은 모두 고친 트리(R6)에서 받았습니다.
5. **B1은 방출 예약 지점 5곳을 한 도우미로 바꿨습니다**(계획은 UFA:607·LOR:95 두 곳). known-route 코호트 만기와 옛 off-ramp 배수, LOR movement 배수까지 같은 규칙을 써야 W_out 예약과 코호트가 어긋나지 않습니다. 결정 시각의 τ 진단(`_tau_diagnostics`, A:5215)은 여전히 plant 지연을 보고합니다. 진단 전용이며, LIVE 계수에서 도우미 밖 W_out 호출 2회가 전부 이것입니다 [실행].
6. **B2는 설치 속성(`offramp_direct_tail_by_offramp`)에서 바꿨습니다.** 대리 변형은 LOR 포트 목표만 바꿨습니다. 속성을 바꿔야 link_predictor·observation_projection·UFA 착지 함수가 같은 목표를 봅니다.
7. **퇴역 movement의 용량도 A1 식으로 둡니다**(10639 1차로 × 1800 = 옛 1800과 같은 값). 옛 키는 U6와 함께 쓸 수 없으므로 출처를 하나로 했습니다.
8. **A4는 v3b lane plant 런에서 무작동입니다** [실행]. RM_C10639 유입(G6-9) 지표가 U1+U3 기준과 C3에서 같고, 출처별 전이를 본 4상태(900·2700·4500·8100)에서는 상태마다 같습니다. SC1004_W_to_onE로 들어오는 차량은 전부 `storage:in_SC1004_W` → movement 전이(정수 대수)인데, 이것은 lane plant의 LUR이 링크 70/10637 위 1134:3 경로 차량을 태그로 넣은 것입니다(lane_plant_runtime `_initialize_upstream`). in_SC1004_W에는 게이트 유입이 없어 β 경로가 쓰이지 않습니다. u6 진단 §9-2가 "B5 폴백 β 경로 평균 2.0대"로 적은 몫은 사실 이 관측 경로 차량입니다 [추론, 전이 출처와 정수 대수로]. A4는 게이트 유입이 생기는 설정에서만 행동을 바꿉니다. 참고로 이번 C3 튜닝의 β 표(Q2 β, `routing_v3b2q2`; 묶음 1 표와 β가 같음)에서 이 movement의 spec β는 0.75였고 [실행 T2700 설치], 기본 튜닝의 폴백은 0.0714였습니다 [읽음 u6 §9-2].
9. **`diverge_evidence`만 있고 정책이 없으면 거부합니다**(A:3413-3415). 키 없는 경로에 확인 하나가 더해지지만, 커밋된 config에는 이 키가 없어 행동은 같습니다(G-ID로 확인).
10. **C 계수는 프로세스 단위입니다**(U5와 같음). no-control 결정은 기록된 한 스텝 예측 하나, SDMPC 결정은 부모 프로세스의 모든 후보 예측 합입니다.
11. **U6 새 상태(`state.ramp_diverge_state`)는 평범한 float dict입니다.** `TrafficState.copy()` 깊은 복사와 tangent 요청 pickle로 따라가고, 워커의 전체 상태 비교에도 들어갑니다 [읽음 `sdmpc_tangent_worker.state_error`]. 예측 캐시는 한 예측 범위 안에서만 쓰이고 결정 동안 초기 상태가 하나라, 캐시 키에 넣을 것이 없다고 판단했습니다 [추론]. 캐시 켜기/끄기 비트 동일은 단계 7의 세 경로 관문에서 받습니다.

---

## 3. 단위 시험 [실행]

`python -B -m unittest test_n31_urban_batch2` (cwd `N31/tests`, 스레드 1) → **Ran 94, OK** (단계 5의 74 + U6 20).

| 시험 (T2) | 계획 §5.1 U6 항목 |
|---|---|
| `U6PolicyTests` (:2062) | 정책 값(없음 / `""` / `physical_diverge_v1` / 그 밖), 대체 키 두 개(`gate_onramp_queue_capacity_veh_h`, `ramp_split_json`) 공존 오류, 증거 핀 누락, 필수 스위치 넷·물리 램프·lane plant 누락 오류, C3 설치가 U6 확인을 부름, 정책 없는 증거 키 단독 거부, 커밋된 config에는 두 키가 없음 |
| `U6ConfigureTests` (:2117) | 증거에서 만든 뷰(용량, 저장고 링크·지지점, W_out 길이, 분할 옛/물리 이름, 직행 착지, 경로 사전 8개, pickle < 8 kB), 두 번 설치 거부; 증거 변조 14종(분기 위치·차로·경로 몫·경로 번호·링크 길이·W_out 길이·링크·분할·결정 위치·직행 착지 목표·퇴역 경로·정지선 경로·스키마·망) 각각 오류, 핀 sha 불일치 오류(변조 사본은 트리 밖 시스템 임시 폴더); 런타임 카탈로그 불일치 5종 |
| `U6InstallTests` (:2200) | A1 용량(3,600/1,800/1,800)과 U4 소유자 기록, 증거 용량 없는 movement 오류; A4 β 0·형제 재정규화 비율·몫 기록·SC1001 무변화; B2 착지 목표(뷰 없음 = W_out, 뷰 = 꼬리, 나머지 그룹 무변화); B3 증거 분할·램프 이름 오류; B1 1/τ = v/L(뷰 있음/없음)과 W_out 진입 1 스텝(그 밖은 plant 지연); W_out 진입 예약 5곳이 모두 도우미를 씀(정적) |
| `U6ArrivalTests` (:2291) | A2 경로 1/2/3/없음/다른 경로/경로에 링크 없음, 127·10777·정지선 뒤 링크, 연결로 10778, 속도 규칙(차량·링크 평균·20 km/h), 램프 몫 태그 스텝·양, 정지선 몫, 도착 = 방출 = 태그 합 = 저장고, 링크별 부류, A3 추가 지연; 짝 없는 예약·합 불일치·투영 합 불일치·기록보다 많은 저장고 오류, 정지선 뒤 링크 허용; 도착 분할(태그 그대로, 태그 밖 β, 과다 태그 오류); A3 지연 착지의 전이 재고 보존·지연분 착지·과다 지연 오류; C 계수와 결정 기록 크기 |
| `U6FinalizeTests` (:2437) | 정상 finalize와 게이트 램프 이름; 거부 10종(leg split·태그·A1·A4·LOR 포트 목표·꼬리 규칙·B3·W_out 링크·게이트 링크·LOR 없음); vendor substep이면 finalize·워커 확인 오류 |
| `U6WiringTests` (:2486) | RS 순서(짝 예약 → A2 → shared_approach·lane plant, U5 finalize → U6 finalize, 워커 확인), 결정 기록은 뷰가 있을 때만, 래퍼 순서(U4 → U6), UFA 분기 순서; 어느 런타임 모듈도 import 시점에 RD를 부르지 않음 |
| U4 시험 갱신 | `c3_tuning`에 U6 증거 핀을 넣고 대체 키 둘을 뺌, U4 시험은 `hsc.install`(C3 설치의 U4 부분)을 부름, 게이트 큐 시험 셋은 C3 순서(U4 → U6 → 게이트 큐)로, "U6 미구현" 단언은 `c3_not_implemented`가 없음을 확인하도록 |

## 4. 스위트 [실행 `S6/suites`, 대조 `S6/suite_compare_vs_stage5.json`]

- `H/run_suites.py`(단계 3~5와 같은 40실행, codex 파이썬 + review-deps)를 최종 트리(`1dd86f3d…`)에서 돌렸고, 단계 5 최종 스위트(`B/impl/stage5/suites`)와 비교했습니다: **회귀 0, 개선 0, 사라진 실행 0, 새 실행 0.**
  - n31 OK(skip 3), n31_batch2 **94 OK**, u40_extra 11 passed, pyt 61 passed, obs_head 31 passed
  - diag11·extra_known 등은 이전 단계와 같은 실패 id(비교기가 회귀 0으로 판정)
  - 생성기 `--check` 15/15(check00–check14)
- 끝난 뒤 `git status` 40줄(단계 5의 39 + RD), diff sha는 그대로였습니다.

---

## 5. 설치 전수 (fail-closed 확인) [실행 `R6/u6_probe/{robsb,s1,s0e}`, 요약 `R6/census.json`, 도구 `H/u6_probe.py`, `H/u6_census.py`]

- C3 전체 튜닝 `R6/tunings/c3_full.json`(`f808532e…`, 도구 `H/u6_arm.py`) = U1+U3(`f137f711`) + C3 세 키(U4 표·U5 계약·U6 정책과 증거) + Q2 권한·β, U4·U5·U6가 대체한 키는 뺌. **메모리 패치 없음.**
- 각 상태에서 어댑터가 `configure_runtime` 끝(U4 verify_final, U5 finalize, U6 finalize 포함)까지 가면 멈춥니다.

| 런 | 설치 | 저장고(대) 최소/중앙/최대 | 램프 몫 중앙 | 정지선 몫 중앙 | 예약 스텝 중앙 | A3 추가 지연 onW / onE | 공통 |
|---|---|---|---|---|---|---|---|
| R-obs-b (1, 150 … 9000) | **61/61** | 0 / 164 / 286.5 | 67.1 | 94.9 | 53 | 41–141 / 62–192 | 퇴역 β 0, OR_D_E → SC1001_W_tail, LOR 10483 → 꼬리, SC1001 분할 1/6·1/3·1/2 |
| S1 (900 … 9000 step 450) | **19/19** | 66.5 / 88 / 217.5 | 54.7 | 36.3 | 46 | 60–152 / 88–206 | 같음 |
| S0e | **19/19** | 62 / 101 / 202 | 55.8 | 37.5 | 52 | 59–144 / 86–196 | 같음 |

- 설치 시간 약 13–14 s/상태(하네스 포함).
- 이전 두 시도(§2.2-4)는 `S6/run6/`(T1800 연결로), `S6/run6b/`(T450·T600 정지선 뒤 연결로)에 남겼습니다.

---

## 6. G6 예비 (계획 §6.5, R-obs-b 9상태) [실행 `R6/capture/{base_u13,c3}`, `R6/g6.json`, 도구 `H/u6_capture6.py`, `H/u6_g6.py`]

- 방법: R-obs-b 900, 1800, …, 8100 상태에서 기록된 no-control 결정을 재생하고 한 스텝 예측(150 s)을 초 단위로 추적합니다(u6 진단의 `u6_capture` 그대로, 녹색·용량 훅이 원 함수의 속성을 보존하도록만 고침: U5 native 행이 `_rw_native_head_green`을 읽는데 원 훅이 그것을 지웠습니다). 같은 창의 FZP와 비교합니다(지표 정의 `B/u6/analyze_u6.py` 그대로).
- 팔: **U1+U3 기준**(키 없음, b2 트리) / **C3 실제 코드**. 참고로 u6 진단의 대리 변형 vFULLrK(cf3ce37, U6 + U4/U5 대리)를 같은 9상태로 다시 계산했습니다.
- 18개 재생 모두 결정 exit 0, 예측 ok, 결정 비교(`MRS compare`) IDENTICAL(no-control 행동). 두 팔의 트리 diff는 같습니다(`1dd86f3d…`).

### 6.1 관문 표

| 관문 | 기준 | U1+U3 기준 | **C3 실제** | 참고: vFULLrK 대리 |
|---|---|---|---|---|
| G6-1 분기 대기 | onW·onE 큐 T+150 p90 ≤ 2대 | 150.9 / 21.3 ✗ | **0.3 / 0.0 ✓** | 0.0 / 0.3 |
| G6-2 10482 유입 | \|b\| ≤ FZP 평균 71.3의 10%, r ≥ 0.8 | −3.83, r 없음(상수) ✗ | **−3.08, r 0.97 ✓** (MAE 5.08) | −3.21, 0.98 |
| G6-3 RM_C10482 재고 | MAE ≤ 5, r ≥ 0.5 | 4.50, r 없음 ✗ | **5.47, r 0.76 ✗(MAE)** | 5.11, 0.78 ✗ |
| G6-4 10490 | 유입 \|b\| ≤ 5, 재고 \|b\| ≤ 3 | +28.3 / +11.1 ✗ | **−1.23(r 0.92) / −1.14 ✓** | −0.31 / −0.81 |
| G6-5 SC1004 W_out | \|b\| ≤ 5 | +54.9 ✗ | **+5.69(r 0.29, MAE 8.1) ✗** | +0.66 |
| G6-6 SC1001 W_out 출구분, 10484 / 10480 | W_out \|b\| ≤ 5, 램프 유입 \|b\| ≤ FZP 평균의 20% | +27.0 / −4.2% / −9.3% ✗ | **−4.82(r 0.69) / −5.1% / +9.6% ✓** | −4.23 / −3.0% / +10.8% |
| G6-7 W 정지선 큐 ~ 127 정지 | \|b\| ≤ 20, r ≥ 0.5 | −27.7, 0.03 ✗ | **+1.99, r 0.94 ✓** (MAE 9.0) | −16.9, 0.95 |
| G6-8 계측 | 진입 여유 구속 초 기록, 미터 개방에서 0 | 기록 없음 ✗ | **9/9 기록, onW·onE 0 s ✓** (미터 전부 10 s) | – |
| G6-9 SC1004 10639 유입 | \|b\| ≤ 2대/150 s, r ≥ 0.9 | +1.20, 0.96 ✓ | **+1.20, 0.96 ✓** (A4 무작동, §2.2-8) | 기록 없음 |
| G6-10 | G-v3b §6.6 | 단계 7 | 단계 7 | – |

- **G6-3 (경계 실패)**: MAE 5.47 대 기준 5, r 0.76은 통과. u6 진단의 대리도 9상태에서 5.11로 같은 경계였고, 계획은 "54상태로 재측정"입니다(단계 7). 두 폐루프 상태 묶음(§6.3)에서는 MAE 3.5로 통과합니다.
- **G6-5 (경계 실패)**: 편향 +5.69 대 기준 5, r 0.29. 분해 [실행 R6/capture 전이]: 150 s 유입이 대리보다 큽니다. SC1004 E→W 방류가 U4 척도에서 커졌고(예 T4500 `SC1004_E_SC1005_to_W` 50.5 대 대리 38.8), 10682 직행 착지가 일부 상태에서 큽니다(T4500 70.6 대 58.1, T6300 73.0 대 56.1). 두 상태(4500, 6300)에서 T+150 재고가 31·34대(FZP 21·1)로 편향 대부분을 만듭니다. U6 B1·B3가 아니라 U4 방류와 본선 측 착지량 차이입니다 [추론]. 54상태 재측정과 G-v3b (d) 본선 쪽 확인이 단계 7 몫입니다.
- G6-7이 대리(−16.9)보다 좋아진 것(+2.0)은 실제 U5가 127 공유 구성원(off-ramp 포함)을 예산으로 나눈 결과로 봅니다(대리 k4Wapp는 off-ramp 구성원을 빼서 방류를 후하게 봤다는 u6 §5.5 설명과 같은 방향) [추론].

### 6.2 LIVE (계획 §5.5, C3 9상태 모두 같음) [실행]

| 함수 | 결정당 호출 | 계획 기대 |
|---|---|---|
| `ramp_diverge.configure` / `initialize` / `finalize` | 1 / 1 / 1 | 설치 1, A2 1 |
| `split_arrival` | 150 (스텝당 1) | – |
| `land_gate` (A3 경로) | 116 (게이트 착지가 있는 스텝) | > 0 |
| 지연 착지 대수 (결정 기록 `process`) | 42.5–103.5대 지연, 150 s 안 착지 0–27.5대 | > 0 |
| `observe_gate_ramp` | 450 (게이트 램프 3개 × 150) | – |
| UFA `_entry_delay_steps` W_out / 그 밖 | 350–465 / 13,084–16,244 (기준 팔도 같은 도우미를 지나 plant 지연을 받음: 737–836 / 21,168–26,164) | – |
| 도우미 밖 `_link_delay_steps(W_out)` | 2 (결정 시각 τ 진단, 두 팔 모두) | 0 (예약 경로) |
| U5 `StepAllotment` / `close` | 150 / 150 | 스텝당 1 |
| 태그 밖 도착 (`untagged_veh`) | 0.0 | 0 |

- 기준 팔(U1+U3)은 RD 호출 0, U5 호출 0입니다.
- A2 사실(C3, 9상태): 저장고 101–274대, 램프 몫 onW 30–98 / onE 11.6–62.7, 정지선 몫 27–127, unresolved 0, 경로 없는 차량 0–4대, 게이트 속도 21.2–38.0 km/h, 추가 지연 onW 64–141 / onE 93–192 스텝, 정지선 뒤 회전 연결로 10695 위 저장고 차량이 4상태 [실행 결정 기록 `initial`].
- 예측 시간(한 스텝 150 s, 훅 포함): C3 12.5–16.6 s 대 기준 14.0–18.4 s, 비 중앙 0.89. 결정 JSON: C3가 기준보다 +5.8~6.2%(U4·U5·U6 기록과 예측값 포함), U6 기록 자체는 약 2.5 kB(no-control action 약 380 kB의 0.7%) [실행]. 공식 시간 관문은 단계 7입니다.

### 6.3 S1·S0e 상태 (무제어 행동, 서술; 계획 §6.5 끝) [실행 `R6/capture/{s1nc,s0enc}_{base_u13,c3}`]

u6 §6.2처럼 폐루프 런의 상태에 no-control 행동을 적용했습니다. 램프 쪽(미터 개방, 게이트 β·유입은 관측)만 비교가 유효합니다.

| 지표 (모형 ~ FZP, 9상태) | S1 기준 | S1 C3 | S0e 기준 | S0e C3 |
|---|---|---|---|---|
| G6-1 onW / onE 큐 p90 | 117.7 / 2.6 | **0.9 / 0.1** | 115.4 / 1.7 | **0.0 / 0.2** |
| G6-2 10482 유입 b, r | −2.61, 없음 | **−3.39, 0.96** | −4.94, 0.34 | **−2.48, 0.97** |
| G6-3 RM_C10482 재고 MAE, r | 5.94, 없음 | **3.50, 0.73** | 4.18, 0.28 | **3.46, 0.82** |
| G6-4 10490 유입 b / 재고 b | +23.3 / +6.4 | **−3.6 / −0.65** | +20.0 / +5.3 | **−3.5 / −0.64** |

- 방향이 R-obs-b와 같습니다(계획의 폐루프 서술 판정 성립).

---

## 7. 세 경로 스모크 (T2700, SDMPC 입구, 수평선 3 × 150 s) [실행 `R6/u6_paths/paths_T2700.json`, 도구 `H/u6_paths.py`]

| 경로 | 결과 |
|---|---|
| 정확(route-bins, 예측 캐시, 포착 원장) | 목적값 505.0981308854, U6 태그 244.0대 = 저장고, 태그 밖 0, 지연 착지 318.2대(450 s 안 착지 204.1), 진입 여유 구속 0 s(RM_C10482·10490·10639), U5 단언 450스텝·최대 초과 4.4e-16, 질량 대조 차 0.0, assert_stocks 3.7e-9, 62 s |
| 코호트(route-bins 끔) | 목적값 차 2.3e-13, **W측 전이 합 10종(두 게이트 movement, 램프 5개, W_out 둘, 꼬리) 차이 0.0**, U6·U5 계수 같음, 180 s |
| 연속(tangent 워커, 스칼라 대리) | 완주, 워커가 RD와 SHG를 AST 변환으로 적재(`transformed_source_sha256`에 둘 다), U5 원장 최대 초과 6.7e-16, 69 s |

- 계획 §5.3의 W측 행("세 경로 동일, 연속은 미터 보간 차이만")과 캐시 켜기/끄기, AD 대 FD는 단계 7 관문입니다. 이번은 U6 코드가 세 경로에서 모두 돈다는 확인입니다.

---

## 8. 키 없음 비트 동일 (§6.1 G-ID) [실행 `R6/probe/s6_{base,u1u3}`, `R6/sdmpc/s6_s1_T3600*`, 분석 `R6/stage6_gid.json`, 도구 `H/stage6_gid.py`]

단계 6은 UFA·LOR·RS·어댑터·HSC를 텍스트로 바꿨으므로 키 없는 경로를 전부 다시 받았습니다(단계 5와 같은 도구·정의). 비교 기준은 단계 1 b2 재생입니다.

| 관문 | 상태 | `MRS compare` | 한 스텝 포착 15필드 | 설치 스냅숏 | action JSON vs 단계 1 | 장부 |
|---|---|---|---|---|---|---|
| (a) 기본 튜닝 `d4327cbf` | R-obs-b 61 | **IDENTICAL 61/61** | 15필드 × 61 같음 | 용량 맵·urban_movements·`_LG_KINDS`·`_LTO`·`_SUS_*` 61/61, 설치 메타 비경로 차이 0 | 차이는 `/prediction/wall_sec`·`decision_wall_sec`·`prediction_wall_sec`뿐, **그 밖 0** (61/61) | 최대 8.6e-9, 실패 0 |
| (b) U1+U3 `f137f711` | R-obs-b 61 | **IDENTICAL 61/61** | 같음 | 같음 | 같음 | 같음 |

| S1 3600 (U1+U3), `replay_decision_n31.ps1 -Root W` | 결과 |
|---|---|
| compare 5검사 | derived·action_csv·action_controls·objective **같음**, action_contract 다름(알려진 VSL 100/110 혼재, 단계 1~5와 같은 정의로 제외) |
| 녹색 / offset | 같음 / 같음 |
| 선택·유지 목적값 (기록 = 재생 = 단계 1) | 491.4356825691444 / 493.5432636752482 |
| tangent 2개 operations·event_counts (기록 = 재생 = 단계 1) | 12,123,157 · (7,850,416, 335,580, 630,241) / 11,962,967 · (7,778,513, 336,378, 630,972) |
| action JSON vs 단계 1 재생 | 행동이 아닌 부류만 다름: 토큰(`request_sha256`·`frozen_context_token`·`response_token`), 시간 필드, `transformed_source_sha256` 8개(바뀐 `beta_source`·LOR·NIP·RCC·RS·AGG·UFA·A). 값 필드 차이 0 |
| 결정 벽시계 | 기록 461.6 s, 재생 651.9 s(다른 워크플로의 폐루프 VISSIM 1·cscript 1이 도는 중, 관문 아님) |

- `transformed_source_sha256`에 RD가 없습니다. 키가 없을 때 AD 변환기가 새 모듈을 읽지 않는다는 뜻입니다.
- **판정: G-ID (a)(b) 통과, SDMPC 한 상태 통과 → 멈춤 규칙 해당 없음.**

---

## 9. provenance와 안전 [실행]

| 트리 상태 | diff sha256 | 무엇으로 확인 |
|---|---|---|
| 단계 6 시작(= 단계 5 끝) | `baabf7af…` | 시작 시 계산 |
| 첫 연쇄 시도(연결로 fail-closed 전) | `5dabab90…` | `S6/run6/chain.log`(판정에 안 씀) |
| 둘째 시도(정지선 뒤 연결로 전) | `b3dc3cb6…` | `S6/run6b/chain.log`(판정에 안 씀) |
| **최종** | `1dd86f3d3ce04c114ab25b5c85c14a7c897923ca9fdf64c14cccfc38522a20b8` | R6 연쇄 두 번의 BEGIN = ALLDONE, 스위트 뒤 재계산, 모든 산출 provenance |

- 최종 트리 파일 sha(앞 12자): RD `2a4beb9ec611`, UFA `8a306878beca`, LOR `1a70607b2d54`, RS `10c488960a96`, A `3f1d3fdf37e7`, HSC `b07190787ec2`, T2 `422bd80eac97`. 그 밖의 파일은 단계 5와 같습니다.
- 새 파일 0(`find -newer S6/marker_stage6_start`, 23:15): R-obs-b·S1·S0e 런 폴더, NC 5시드 폴더(`D:/VISSIM_runs/20260925_v3b`), `frozen/sdmpc31_cf3ce374_202609261037`, `frozen/sdmpc31_886a014a_202609260935`, OLD `D:/VISSIM-merge/sim3-n31-urban`. `frozen/` 최상위에도 marker 뒤 새 항목이 없습니다(17:40의 `sdmpc31_92fa4b8e_202609291737`은 단계 5 때부터 있던 다른 워크플로의 것).
- OLD: `git status` 0줄, HEAD `cf3ce37`. `sim3-n31-v3c1`: HEAD `9ed2ef0`, `claude/repin-v3c1-20260928`, `git status` 0줄. 어떤 명령도 이 둘에 쓰지 않았습니다.
- W의 `__pycache__` 없음(모든 실행 `-B`, `PYTHONDONTWRITEBYTECODE=1`). `evaluation/controllers/__tangentcache__`에 새 파일 6개(바뀐 소스의 AD 변환 캐시, .gitignore 대상, `freeze_manifest`가 비교에서 뺌).
- 재생은 늘 하나씩, BELOW_NORMAL, 스레드 1, `nbc_b2i`, codex 파이썬 3.12.14 + review-deps(판정에 쓴 모든 재생·스위트). 전 구간에 다른 워크플로의 폐루프(VISSIM 1, cscript 1)가 돌았습니다. 제가 멈춘 것은 제 연쇄 두 개(fail-closed 발견 뒤)와 제 감시 작업뿐입니다. VISSIM·cscript를 시작·종료하지 않았습니다.
- 워치독·cscript·ps1 시험은 돌리지 않았습니다(`run_suites.py` 제외 목록). seed 37, RM 팔, 봉인 시드 59/61/67은 열지 않았습니다. 폐루프 런·커밋·push는 없습니다.
- 정리하지 못한 것: 둘째 시도가 중단되며 남긴 MRS 재생 사본 `S6/run6b/replay/`(약 3.5 MB, 스크래치 안). 삭제 명령이 안전 확인에 걸려 남겨 두었습니다. 지워도 됩니다.

---

## 10. 다음 단계로 넘기는 것 / 사용자 판단

1. **G6-3·G6-5 경계 실패(9상태)**: 단계 7의 54상태 재측정 대상입니다. G6-5는 U6가 아니라 U4 방류와 본선 착지량에서 오는 것으로 보이므로(§6.1), G-v3b (d) 본선·FW_E 확인과 함께 봐야 합니다.
2. **A4 무작동(판단 필요)**: v3b lane plant에서는 SC1004_W_to_onE로 β 경로가 흐르지 않습니다(§2.2-8). 그대로 두어도 행동 차이는 없고, 게이트 유입이 생기는 설정에서만 작동합니다. u6 §9-2의 "중복 경로 2.0대" 해석은 관측 경로 차량이었다는 점을 정정합니다.
3. **적격 일반화·평균 속도·ceil**(§2.2-2·3): 계획 문구와 대리 변형 사이의 선택입니다. 결과는 대리와 같은 수준입니다(G6-2 r 0.97 대 0.98).
4. **`""` 거부**(§2.2-1): u6 진단 문구와 다릅니다.
5. **후보 config(단계 9)**: C3 튜닝은 `urban.ramp.admission_policy`·`urban.ramp.diverge_evidence`(`0aacabf1…`)를 넣고, `urban.ramp.gate_onramp_queue_capacity_veh_h`·`urban.boundary_out.ramp_split_json`·`urban.capacity.head_resource_contract`와 U4가 대체한 네 키를 빼야 합니다. 이번 하네스 `H/u6_arm.py`가 그 모양입니다. 단계 5 이월(Q2 권한·`routing_v3b2q2` β)도 같습니다.
6. **승격 때 격리할 것(u6 §7.4)**: 키 없는 경로의 `urban.ramp.gate_onramp_queue_capacity_veh_h` 읽기(A:3424, U4-0 뒤 필수 키), `parameters.json`의 `boundary_out_link_length_km`, B4b 규칙의 OR_*_E → W_out 분기, ver2 분할표 `outputs/boundary_out_ramp_split_20260905_measured.json`. 묶음 2는 후보 config만 만들므로 지금은 키 없는 경로로 남습니다.
7. **τ 진단(§2.2-5)**: 결정 시각 τ 진단은 U6에서도 W_out의 plant 지연을 보고합니다. 진단 전용이라 두었습니다.
8. **이월(그대로)**: 단계 5의 native 행 녹색 정의, 포착 예측 시간 1.067배(단계 7 시간 관문 위험), 10634 동일 정의, 하한 비율, 순차 잔여 미발생, no-control action 크기, C6 키를 후보 config에(단계 9), C6 경계 경보 추이, `ControlAction.fixed`의 700 allocation, 계획 밖 1,400 사용처 둘, v3c1 재유도 때 생성기 상수 인자화, 동결 전 `__pycache__` 삭제(현재 없음).

## 부록: 산출 파일

- 보고서: `B/impl/STAGE6.md`
- 코드 백업(단계 5 판): `S6/backup_stage5/`. 편집 명세: `S6/edit_code.py`, `S6/edit_t2*.py`, `S6/spec_*.json`, 새 시험 블록 `S6/t2_u6_block.py.txt`, 줄바꿈 보존 도구 `S6/eol_edit.py`
- 하네스(새로): `H/u6_arm.py`, `H/u6_probe.py`(생성 `S6/make_u6_probe.py`), `H/u6_capture6.py`(생성 `S6/make_u6_capture6.py`), `H/u6_paths.py`(생성 `S6/make_u6_paths.py`), `H/stage6_chain.py`, `H/u6_census.py`, `H/u6_g6.py`, `H/stage6_gid.py`
- 연쇄: `R6/chain.log`, `R6/logs/`; 결과: 설치 `R6/u6_probe/`·`R6/census.json`, G6 `R6/capture/`·`R6/g6.json`, 세 경로 `R6/u6_paths/`, G-ID `R6/probe/`·`R6/sdmpc/`·`R6/stage6_gid.json`, 튜닝 `R6/tunings/c3_full.json`
- 이전 시도(판정에 안 씀): `S6/run6/`, `S6/run6b/`, 개발 `S6/dev/`
- 트리 새 파일: RD. 수정: UFA, LOR, RS, A, HSC, T2
