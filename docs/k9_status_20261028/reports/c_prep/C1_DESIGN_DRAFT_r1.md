# C1 묶음 1 설계 초안 — 목적 경계 Ω701(접근로) + 미터 결정 묶음 (2026-10-27 KST, 초안 r0)

- 이 문서는 **설계 초안만** 적습니다. 코드 변경·커밋·푸시·동결·재생·VISSIM·COM·러너·시험은 0회입니다 [실행 `CP/LOG.md` 06:17 항목].
- 근거 결정: D-K9-91 "기구별 이식(C). codex 판 통째 교체 안 함. 첫 묶음 후보 = 목적 경계(Ω701 접근로) + 미터 결정 묶음(이웃 검사·cap 3·녹색 0 금지·저장 보호·머리 서비스 표); ③④ 결과 뒤 확정. K9-3(D1·D2) 보류 유지" [읽음 `SP/K9_1_J1_NOTES_20261013.md:308`]. ③ readback 대조(`CP/READBACK_METER.md`)와 ④ 입구 1099 분해(`CP/INPUT1099.md`)는 끝났습니다. D-K9-92 VSL 오프라인(`CP/VSL_OFFLINE.md`)도 첫 묶음이 끝났습니다.
- **데이터 뒤 선언**: 이 설계는 B 결과(`CH/B_RESULTS.md` r2 `152a2f6f…`, `CH/VERIFY_B.md` `f2851f8b…`)와 그 뒤 세 분석을 본 뒤 씁니다. 여기서 정하는 범위·관문·문턱·비교 규칙은 모두 데이터 뒤 선언입니다. B 자료에서 뽑은 문턱은 칸마다 출처를 적습니다(예: §8.9 의 SG2 100 s). COMPARE_RULE_B·PINS_B 는 바꾸지 않습니다. 이 초안에는 실행할 새 분석이 없습니다. 사용자 결정(§12) 뒤 이 설계를 선언 꼴(가칭 **보충 C1**)로 옮기고, 규칙과 도구 sha 를 실행 전에 `CP/LOG.md` 에 고정합니다.
- 꼴: K9-2 설계(`KB/K9_2_DESIGN.md` r2)와 K9-3 설계 초안(`N/K9_3_DESIGN_DRAFT.md` r2)을 따릅니다.
- 표시: **[실행]** 이번에 읽기 전용 명령으로 확인 · **[읽음]** 문서·코드·설정에서 확인(다른 보고서에서 옮긴 숫자는 그 보고서가 [실행] 으로 낸 값이고, 여기서는 [읽음 문서:줄] 로 적음) · **[추론]** 시험하지 않은 판단 · **[계산]** 이 문서의 산술. 판정 낱말은 쓰지 않습니다. 시드는 망 접두로 적고 평균 내지 않습니다. Ω 숫자는 늘 ④·Ω 밖과 같은 줄·표에 둡니다. 64cf 숫자에는 "다른 망, 한 시드" 표지를 붙입니다.

## 줄임말 (처음 한 번)

- SDMPC = 이 계열 분산 모형예측제어기. plant = 그 안의 교통 예측 모형. 결정 = 150 s 마다 내는 제어 명령. 재생 = 기록된 상태로 제어기 프로그램만 다시 돌리는 것(VISSIM 0). 연쇄 재생 = 재생 출력을 다음 결정의 직전 명령으로 이어 쓰는 재생(K9-2 V-B 꼴).
- RM = 램프 미터. g = 10 s 주기 중 녹색 초(g10 = 늘 초록). TSC = 도시 신호 제어(녹색·offset). VSL = 가변 제한속도. SC = 신호 제어기, SG = 신호 그룹. EBT = SC1001 동쪽행 직진(SG2, 링크 127 차로 1·2).
- 이웃 검사 = codex 미터 결정의 유한 후보 검사(미터·고속도로 묶음마다 "가장 조임 / 가장 풂" 3블록 계획을 전체 모형으로 채점). 조합 = 따로 이로운 후보 가운데 겹치지 않는 것을 한 번 묶어 다시 채점. cap 후보 = 리더가 시험하는 NP 상한 수. NP·NUF = 리더가 정하는 보호망 순유입 상한·예측 합류 상한. 저장 보호(storage guard) = 미터 머리 앞 저장이 90 % 차면 그 결정의 녹색 하한을 올리는 규칙. 머리 서비스 표 = 녹색 초별 미터 방류(대/주기).
- Ω635 = 우리 목적 영역(링크 635). Ω701 = codex 목적 영역 = Ω635 + 신호 17곳 접근로·머리 링크·직접 커넥터 66. ④a = 망 전체 링크 체류(veh·h). ④b = 미삽입 대기(입력에서 생겼지만 망에 못 들어간 차의 대기). ④ = ④a + ④b. Ω 밖 (a) = ④ − Ω, Ω 밖 (b) = ④a − Ω. 첫 관측 차분 = ④b 짝 차를 "차가 FZP 에 처음 보인 시각" 으로 내는 방법(D-K9-87 주 값). ① = FW_E 본선 7링크. ② = 동측 국소 19링크. 입력 1098 = FW_E 입구, 입력 1099 = FW_W 입구.
- PFO = SDMPC 첫 단계의 소유자별 자기 비용 따뜻한 시작. held = 직전 실행 명령. OUTW = 예측 지평 450 s 동안의 Ω 밖 모형 대기.
- D1–D5·S1–S5 = METER_NEXT2 의 결함·단계 번호(D1 결정점 1135 분할, D2 SC1004 서쪽행 용량, D3 게이트 진입 지연, D4 미터 서비스 표, D5 링크 129·70 저장 문턱; S1 본선 합류·용량 기구, S3 목적 경계, S4 유한 후보, S5 안전 장치). K1·K3·K6·K8-3·K8-9·K8b·K9-1 W1·K9-2 W/H-b = 우리 줄기 고침 이름(R_MECH §6). GB-7′·GB-9′ = 보충 34 오프라인 관문(무제어 61결정 재생 대조, 반사실 SDMPC 4상태) [읽음 VA_REPORT:21].
- B = codex 판(a49981ff)을 v3c3 로 옮긴 폐루프 런. V-A = 우리 묶음 B1(K9-2) 배포 폐루프 런. NC3 = v3c3 무제어 런. R-obs = 무제어 VISSIM 런에서 결정을 계산만 한 런. v3c3 = 우리 기준 망 FW80(`3de889f0…`). 64cf = codex 망. FZP = VISSIM 차량 궤적 파일(5 s).
- 경로 약칭
  - SP = `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8`, CP = `SP/c_port`, CH = `SP/codex_handoff`, RC = `SP/rmcause`, N = `RC/r2c_n`, KB = `SP/k92/bundle1`.
  - GWT8 = `D:/VISSIM-merge/sim3-n31-k8`(head `c20aff1d` = V-A 배포 커밋). **OU** 줄 번호는 모두 `git show c20aff1d:` 기준입니다(읽기 사본 `CP/c1d/ou_*`).
  - **CX** = `D:/VISSIM-merge/k8_gate_trees/codexhandoff/a49981ff`(codex 인계 HEAD). FRZ_B1 = `D:/VISSIM-merge/k8_gate_trees/codexhandoff/b1/frozen/sdmpc31_a49981ff_202610261410`(B 런 동결 트리). CFG_B = `FRZ_B1/diagnostics/b0_v3c3/config_b0_v3c3.json`(`729640af…`). OUC = OU `diagnostics/sdmpc_n31_20260924/config_n31_v2.json`(`c8e3ee2c…`).
  - 코드 약칭(모두 `evaluation/controllers/` 아래): SD `sdmpc.py`, PRB `physical_ramp_branches.py`, LPR `lane_plant_runtime.py`, RS `runtime_setup.py`, AR `area_runtime.py`, CAO `control_area_objective.py`, RCC `route_choice_corridor.py`, LOR `lane_offramp_runtime.py`, USG `urban_storage_guard.py`, SEQ `sdmpc_sequence.py`, ADP `vissim_stackelberg_adapter.py`. UQM = `vendor/NumSim-mine/src/models/urban_queue_model.py`. VBS = `scripts/run_real_world_stackelberg_controller.vbs`.

### 근거 문서와 코드 (sha256) [실행]

| 대상 | sha256 |
|---|---|
| 사용자 결정 `SP/K9_1_J1_NOTES_20261013.md` (D-K9-91~93) | c6c720eb6a366e8bb5fcfee68db9446b202b9c9b8ad8c544bd4d19c1e719caf0 |
| `CP/READBACK_METER.md` | 2fd9863934f93d09341e84df45f7c67cc404e0c4e97dcb85ed1ec465bbd7f980 |
| `CP/INPUT1099.md` | 1548316a36b5647ee2a0132af9814d91c5c25d0be1d489a170170b65c3e31285 |
| `CP/VSL_OFFLINE.md` | 6cca0baa715f4d0bb870bd5f7e2c2c05279bc168048961c106f95b430ba9debf |
| `CH/B_RESULTS.md` r2 | 152a2f6fe0fd6c5cfd1462ba7d7e444cd13a6bd0ba2554874d07a1390a8209f9 |
| `CH/VERIFY_B.md` | f2851f8b53f026ada64f52e51d877b8c0ddc7ac3bbaf7f19cd27097c21462104 |
| `CH/R_MECH.md` | 2fc879d62760621f9e40df92774fe4f74eb29fc9ce8edaf08360d3eaab0434e5 |
| `CH/TAKEOVER_PLAN.md` r2 | b75ad0418fa08dc0d0b64b70ffdd3c82e2ea101ab7ee73e75e27a67ab7482144 |
| `CH/b0/B0.md` r2 | 11fa75788e5457f95ab20a43ca2287e663f0390bef67940bcfb66dd8368c86bc |
| `CH/RAW_CHECK.md` | c8411d78e756a018… (앞 16자리) |
| `CH/A0_PROFILE.md` | 900bad3c82332705… (앞 16자리) |
| `RC/METER_CAUSE.md` r2 | 0b4036c62cd2e2983c9965dd6010a4c93a88d83635a98293e82acb3fe92c626c |
| `N/METER_NEXT2.md` r2 | acebbe738677eebc1cbb36b9efca2d9e905bdc9b2bddc8d5b229563cbc43b33c |
| `N/K9_3_DESIGN_DRAFT.md` r2 (꼴) | 549f20e2507cc4ebe9dda97e6fd95ebb745582732362fe5ffe7c3cdba14f89b4 |
| `KB/K9_2_DESIGN.md` r2 (꼴) | 1100f7af519839beb0bd1345f8d576e2ce64d6bb01162b03eea27830d5d7ad2a |
| `CH/b/COMPARE_RULE_B.md` (바꾸지 않음) | f902f7f0013bed0a0eb5dec27818e2bda4851995eae235130b7cb241e8b28f0c |
| `SP/k92/va/analysis/VA_REPORT.md` r3 | b57022e651adeefc… (앞 16자리) |
| CX SD = FRZ_B1 SD | 5c1ba251a3526cafa6574459e23627e59cb96e9373ff7d1c5588bcdde3c3a0c0 |
| CX PRB = FRZ_B1 PRB | 0ab140ac0967348b1b475d06668965284ac2170a93a7ee963cbd80b22c4dc966 |
| CX LPR = FRZ_B1 LPR | d774daee3ae12a58f76e660b3dc0ea919f7187e39c625000205ba57dc0cb9563 |
| CX RCC | 972e9f77a5f3c79ffe9598533e426ee3edea2f20179413acc1f15b36a68d984d |
| OU SD (`git show c20aff1d:` 바이트) | 352701a08b10628511119ff188a7cbcc1b577977f3445b648aba0dc2742c19a4 |
| OU PRB | 08cb370d20fb727c77ef1069a07869faf86fb583e83cf92fbf0727d0e4d39778 |
| OU LPR | 493a5bf2e026c1b7bfeb1b3915dddf5307ac85c9b9f4ac5255d0eb72ad43ac35 |
| OU RS | 70cca680ef9f5dd84ee506ff8857712466f3779039289ca79adadc3d8f1eceba |
| OU AR | 2c7cccdf01e8bcdbc2d0f26dc9fed59dbe2a5b41d52ab0512ba2e9370124a5bc |
| OU CAO | 2c21cd8cdeab50cba81a21321abccdcbdb1ea4c5f8f27977ecb61e589f52ad60 |
| OUC | c8e3ee2c99b66c255b2279f0aa18eaafc18d4c7689e59e260109fac3b7d71866 |
| CFG_B | 729640af754a90c8d7fbe8f81577b27bae02b86f1d504e18333c0fc99717f983 |
| Ω701 membership (FRZ_B1 `diagnostics/b0_v3c3/omega701/membership.json`) | 9bb740b321d28162c0e849b56e0e618adf4ec800caa60476c96f3fc469318d51 |
| Ω701 경로 계약 (같은 폴더 `route_contract.json`) | 08fec9c71b1c612ad3f95555173e372fd2f9428ef58d7010246a00bf0b77063a |

---

## 0. 쉬운 요약 (판정 아님)

1. **묶음 1 = 여섯 기구 + 딸린 것 둘** [읽음 CX 코드·CFG_B, 자리는 §3].
   - 목적 경계 Ω701(접근로 66 더함).
   - 미터 결정: 이웃 검사(+조합 1회), cap 후보 3, 녹색 0 금지, 저장 보호(문턱 0.9), FW_E 미터 4개 머리 서비스 표.
   - 딸린 것: 저장 보호가 만드는 "운영 seed" 투영과, 그 seed 를 다시 채점해 남기는 held 유지(codex SD:28-51, :1221-1230).
2. **1099 결과에서 FW_W 입구·엮임 보호 장치가 꼭 필요하다는 근거는 없습니다** [추론, 근거 읽음 INPUT1099].
   - B 의 ④b 1099(B − NC3 +490.0 / +468.4 / +84.0 veh·h, 세 시드)는 미터가 아니라 SC1001 EBT 녹색 단축 사슬을 따라 왔습니다(v3c3-s31·s41; v3c3-s43 은 잡음 크기 안). 미터 10480·10490 기구는 3/3 시드에서 반박되었습니다.
   - 같은 짝 B − NC3 의 Ω701 −157.0 / −523.4 / −222.2, ④ +175.1 / −230.6 / −450.6, Ω 밖 (a) +332.1 / +292.9 / −228.4 입니다.
   - 다만 C1 의 Ω701 이 TSC 목적을 바꿉니다. Ω701 이 SC1001 에 더하는 것은 북쪽 접근 링크 37 하나입니다 [실행 membership `/controlled_intersection_expansion/added_links`]. 그래서 장치 대신 **오프라인 SG2 대조 + 폐루프 사슬 줄 보고** 를 미리 선언하자고 권합니다(⟨Q2⟩·⟨Q3⟩).
3. **옮기지 않는 것**: 64cf 로 맞춘 계수(셀 FD·δ_merge·port 계수·segment_params 등), `calibrated_aggregate`, VSL 부분 전부(집합 50–110·구역 머리·secant·고정 일정·Carlson 계수), 도시 저장 보호·머리 자원 v11 등 도시 묶음(C5), 속도 캐시, 링크 124 공유 차로 기구(§4).
4. **설정 키는 새 구역 `c1_port` 하나**입니다. 하위 키가 없으면 c20aff1d 와 비트 같게 돕니다. 증거는 경로 문자열 없이 이름 + sha 로만 가리킵니다(§5).
5. **기대 모형 효과** [추론]
   - Ω701: TSC 목적에 접근로 66링크 체류가 들어갑니다. V-A − NC3 에서 이 66링크 몫은 +248.7 / +237.6 / +307.0 veh·h 였습니다(같은 짝 Ω701 −240.6 / −421.7 / −309.5, ④ −373.9 / −506.2 / −356.4, Ω 밖 (a) −133.3 / −84.5 / −46.9) [읽음 B_RESULTS:65-71·67].
   - 미터: V-A 상태(늘 g10)에서 새로 열리는 것은 조임 후보 10개(미터 8 + 고속도로 묶음 2, 계획 g8/6/4)뿐입니다 [계산 CX SD:556-599]. 우리 plant 는 조임에 Ω 가 늘거나 그대로인 쪽이었습니다(METER_CAUSE a2·a2-5). 그래서 **C1 만으로는 미터가 g10 에 머물 수 있습니다**. 탐침에서 먼저 보고, 조임이 한 번도 안 뽑히면 폐루프 전에 멈추고 묻습니다(§8.9 S-C1-7).
6. **관문**(§8): 키 끔 = c20aff1d(G-K0), 키 켬 차이 분류(G-K1), 식 재현(G-K2), 거부·묶기(G-K3), 탐침 재현(G-K4), 결정 벽시계 둘(G-K5a 키 끔 ≤ 1.0158, G-K5b 키 켬 최대 ≤ 1,500 s), 기록 대 재생(G-RR, 선언 차이 목록), 오프라인 재생 비교(R), K9-1·K9-2 판정 잎(J), 블라인드 충실도(F).
7. **폐루프 판정 꼴**(§9): C1 − NC3, C1 − V-A 가 주 짝, C1 − B 는 참고 짝. 세 시드, Ω701·Ω635 를 ④·Ω 밖 (a)(b)와 같은 표에, ④b 는 첫 관측 차분, 입력 1099 줄과 SC1001 사슬 줄을 같은 표에 둡니다.
8. **비용 어림**: 오프라인 약 55–85 h 계산(무거운 일 한 번에 하나, 약 5–8일) + 폐루프 3런 동시(런당 약 10–24 h, 결정 시간에 달림) [추론 §11].
9. 결정 거리는 ⟨Q1⟩–⟨Q19⟩ 입니다(§12). 권장안은 각 줄에 적었습니다.

---

## 1. 사용자 결정과 범위 [읽음 `SP/K9_1_J1_NOTES_20261013.md:303-310`]

| # | 결정 | 이 설계에서의 뜻 |
|---|---|---|
| D-K9-91 | 기구별 이식(C). 첫 묶음 후보 = 목적 경계 + 미터 결정 묶음. ③④ 뒤 확정. K9-3 보류 유지 | 묶음 1 범위 = §2.1. K9-3 D1·D2 는 이 묶음에 넣지 않고, 설치 자리가 겹치지 않게만 설계(§6.3) |
| D-K9-92 | VSL 오프라인부터 | VSL 은 C1 범위 밖. V-A 의 VSL 그대로 두고(⟨Q8⟩), VSL_OFFLINE 의 다음 실험 O1·O2 는 따로 감 |
| D-K9-93 ① | X6 칸 단위 | C1 비교 규칙도 칸 단위 "못 냄" 꼴(§9.3) |
| D-K9-93 ② | † 숫자 그대로 | C1 − NC3 의 900 s 전 접두 차(v3c3-s31·s41)도 † 로 둠(§9.3) |
| D-K9-93 ③ | readback 미터 대조 새 선언 | 끝남. 녹색 초 = 명령(세 시드 6,480/6,480 주기). 머리 표 근거로 씀(§3.6). 폐루프 C1 에도 같은 도구로 대조(§9.2) |
| D-K9-93 ④ | 1099 오프라인 분해 | 끝남. 보호 장치 판단(§2.2) |
| D-K9-93 ⑤ | 같은 시드 반복 런 안 함 | C1 에서도 같은 시드 반복 없음. 런 사이 흔들림은 모름으로 둠 |

---

## 2. 범위

### 2.1 들어가는 것 (기구별 키를 따로 둠, 배포는 함께 — ⟨Q11⟩)

| # | 기구 | 무엇을 하나 | 근거 |
|---|---|---|---|
| M0 | 목적 경계 Ω701 | Ω 를 701링크로 바꿈. 도로 링크 35(신호 17곳의 접근 영역·머리 링크) + 직접 커넥터 31 = 66 더함. NP 정의는 그대로("N_P remains the existing 17-player PN net inflow quantity") | [실행 membership `/counts/inside_total` 701, `/controlled_intersection_expansion/added_links` 66, `/np_rule`] |
| M1 | 미터 이웃 검사 + 조합 1회 | 미터마다·고속도로 묶음마다 3블록 "가장 조임/가장 풂" 후보를 전체 모형으로 채점, 이로운 것 중 겹치지 않는 것 한 번 묶기. 신호·VSL·cap 은 고정 | [읽음 CX SD:556-689] |
| M2 | cap 후보 3 | 리더 NP 상한 후보를 1 → 3(central 모드에서 `next_budget` 이 더함) | [읽음 CX SD:953-959, :1209-1215; OU SD:675-681, :925-930 같은 코드, 값만 다름 CFG_B:7696 = 3, OUC:7696 = 1] |
| M3 | 녹색 0 금지 | 새 후보에서 녹색 0 을 뺌(기록된 0 은 읽기만 허용) | [읽음 CX PRB:866-868, :50-53, :145; CFG_B:7541] |
| M4 | 저장 보호 0.9 | 머리 앞 저장 점유 / 차로 저장 ≥ 0.9 인 차로가 있으면 그 결정의 녹색 하한 = 직전 녹색 + 2 s. 명령 하한일 뿐 | [읽음 CX PRB:871-908, CFG_B:7542-7545] |
| M4a | (딸림) 운영 seed 투영 | 직전 명령이 새 하한 밖이면 미터 축만 하한으로 잘라 PFO 시작점으로 씀 | [읽음 CX SD:851-864 의 USG 아닌 가지, :898, :907, :919-922, :945] |
| M4b | (딸림) held 유지 | cap 모드 끝에서 운영 seed 를 고른 cap 아래 다시 채점해 더 낮으면 남김 | [읽음 CX SD:28-51, :1221-1230, :1300] |
| M5 | FW_E 미터 4개 머리 서비스 표 | RM_C10639·10490·10484 g2–g10 = 1.0·1.5·2.0·2.5·3.0·3.5·4.0·4.2·4.2 대/주기, RM_C10681 = 그 두 배(2차로) | [읽음 CFG_B:8161-8206; 설치 CX LPR:616-620] |

- 묶음 근거 [읽음 TAKEOVER_PLAN:109 = METER_CAUSE:25]: 이웃 검사만 켠 codex 런 233/235(**다른 망 64cf, 한 시드 64cf-s29**)는 0–6,600 s 중간 추정에서 FW_E 가 +7.85 % 늘었고, 10480 적색 → 링크 124 → 10483 역류로 7,959 s 에 멈췄습니다. 그 뒤 codex 는 녹색 0 금지·저장 보호·124 공유 차로를 더했습니다. 그래서 M1 을 M3·M4 없이 넣지 않습니다(⟨Q1⟩).

### 2.2 FW_W 입구·엮임 보호 장치가 필요한가 (1099 결과에서)

**사실** [읽음 `CP/INPUT1099.md`, 세 시드 v3c3-s31·s41·s43]

1. B − NC3 의 ④b 중 입력 1099 = +490.0 / +468.4 / +84.0 veh·h. 같은 짝 Ω701 −157.0 / −523.4 / −222.2, ④ +175.1 / −230.6 / −450.6, Ω 밖 (a) +332.1 / +292.9 / −228.4 [읽음 B_RESULTS:65-77].
2. 넣기는 멈추지 않았고 속도가 줄었습니다. 2,700–4,500 s 넣기 B − NC3 −10.4 / −15.2 / −2.8 %. 덜 넣은 차(4,500 s 에 +272 / +272 / +109 대)가 이월되어 veh·h 의 84 / 86 / 51 % 가 4,500 s 뒤에 쌓입니다 [읽음 INPUT1099:21-23].
3. 받쳐진 사슬(v3c3-s31·s41; v3c3-s43 은 잡음 크기 안): SC1001 SG2(EBT) 녹색 900–2,700 s 가 B 406 / 409 / 512 s(NC3 576, V-A 578 / 638 / 680) → 127→30 통과 감소 → 링크 127 시작 칸 7 / 4 / 6 km/h → 129·10491 느림 → 링크 26 차로 1 끝(3,200–3,700 m) 대기 → 300–600 s 안에 입구 [읽음 INPUT1099:136, :190-192].
4. 반박(3/3 시드): 미터 RM_C10480 대기 번짐(H1; 124 체류 B = NC3, 상관 −0.14 / −0.23 / −0.17), RM_C10490(H3a; 상관 0.18 / −0.12 / 0.16), 링크 120(H2, 느린 체류 0.0), 10479·125(H4), SC1002(H3c) [읽음 INPUT1099:187-195].
5. 링크 26·127·129·10491 은 Ω701·Ω635 모두 안이고, ④b 는 둘 다 밖입니다 [읽음 INPUT1099:30; 실행 membership 대조].
6. 입구 처리량(약 4,000–4,800 veh/h)이 수요(5,600–6,000 veh/h)보다 작아 세 팔 모두 서 있는 줄이고, 한 번 진 넣기가 이월되는 증폭기입니다 [읽음 INPUT1099:22, :103, :210].

**추론**

- 미터 기구(M1–M5) 쪽에서는 이 자료가 FW_W 입구 보호 장치를 요구하지 않습니다. B 에서 미터가 사슬에 닿은 흔적이 없습니다(사실 4).
- C1 에서 TSC 목적을 바꾸는 것은 M0(Ω701)뿐입니다. Ω701 이 SC1001 에 더하는 링크는 북쪽 접근 37 하나입니다 [실행 membership `added_links` 중 SC1001 = `{"link": "37", reasons: controlled_approach_territory:SC1001:N_SC2002, native_controlled_signal_head:SC1001}`]. 그 링크가 목적에 들면 SC1001 녹색이 EBT 에서 다른 현시로 옮겨질 수 있습니다. 옮겨질지는 모릅니다.
- B 가 왜 SG2 를 줄였는지는 결정 JSON 을 읽지 않아 모릅니다(INPUT1099 §6-1). B 에는 C1 이 옮기지 않는 도시 기구(도시 저장 보호·머리 자원 v11·무신호 처리·머리 현시 대기 귀속)가 함께 있었습니다 [읽음 R_MECH:138-143].
- 그래서 권장은 **장치를 넣지 않고 미리 선언한 감시** 입니다(⟨Q2⟩ (가)): (i) 키 켬 연쇄 재생에서 SC1001 SG2 계획 녹색을 키 끔(V-A 기록)과 대조(§8.6, 멈춤 문턱은 ⟨Q3⟩), (ii) 폐루프 표에 1099 줄과 사슬 줄(§9.1). 링크 129·10491 저장 한계 보호(METER_NEXT2 의 D5)나 1099 밀린 줄을 목적에 넣는 일은 다른 묶음 후보로 남깁니다.

---

## 3. codex 에서 옮기는 것 (파일:줄 양쪽)

- 원천 줄 번호는 CX(a49981ff) 입니다. SD·PRB·LPR 은 FRZ_B1 과 sha 가 같습니다 [실행]. 자리 줄 번호는 OU(c20aff1d) 입니다. 우리·codex SD 의 차는 CR 을 빼고 387줄입니다 [실행 `CP/c1d/diff_sdmpc.txt`]. 그 가운데 C1 에 드는 것만 아래에 적습니다.

### 3.1 M0 목적 경계 Ω701

| 무엇 | codex | 우리 자리 | 비고 |
|---|---|---|---|
| Ω 소속·경로 계약 | CFG_B:8323-8324 `membership_path`·`route_contract_path` → B0 가 v3c3 에 다시 만든 파일(membership `9bb740b3…` 701/535, 경로 계약 `08fec9c7…`, turn 57개 갱신, codex `approaches_only/route_contract.json` 과 바이트 같음) | OUC:8272-8273 이 지금 Ω635(`control_area_membership_213a5d.json` 30abb1db…) 와 바탕 경로 계약을 가리킴. 읽는 곳 AR:168-170(`read_required`) | [읽음 B0 §2.3; 실행 sha] |
| 소속에 묶인 우리 팩 문서 8개 | B0 REGEN 8: native_input_1083 권한 `8f65b25c…`, native_internal_inputs `a23a1363…`, physical_projection_support `7d092b3d…`(+커넥터 지원 29), 경로 선택 회랑 1099 `8e40f046…`·1100 `59fa5c59…`·1128 `d92f90aa…`·SC1004 `7067a661…`, sc2001 회랑 `cc5e6863…` | OUC:7870, :7922, :7925-7928, :7932, :8264 가 Ω635 판을 가리킴. 이 8개가 모두 Ω635 sha 를 품음 [실행 `git grep control_area_membership_213a5d`] | [실행 FRZ_B1 sha·`B0_REPIN_RECEIPT.json` `/files`] |
| lane plant manifest 의 소속 | B0 는 codex manifest 를 재핀 | 우리 `plant_n31_v2.json`(b119d6d9…) `/membership/path` 가 Ω635. 읽는 곳 LPR:299 | Ω701 판 manifest 는 P0 에서 새로 만듦(소속 한 칸만 바꿈) |
| 목적 계산 코드 | 없음(codex CAO 의 차이는 multirate·complete_source 쪽) | OU CAO:90-100 이 `schema`·`unresolved`·`inside_links`·`outside_links` 만 읽음. Ω701 파일은 schema `control-area-membership/v1`, `unresolved` 빈 목록, 안·밖 겹침 0 | [실행 diff CAO 73줄; Ω701 `/schema`·`/unresolved` 읽기] |
| 유령 경로 별칭 | B0 F2 가 우리 K8-9 별칭을 codex CAO 에 옮겼음 | OU CAO:252-273 그대로 | B0 시험: Ω701 경로 계약에서도 유령 키 3개가 확률 null → 별칭 필요·작동 [읽음 B0 §3.1] |

- 넣는 방법: RS `configure_runtime` 첫머리(OU RS:341-350, 어느 모듈도 경로를 읽기 전)에서 `c1_port.omega701` 이 있으면 묶음 목록 파일을 이름 + sha 로 찾고, 11개 파일(소속·경로 계약·문서 8·manifest)의 sha 를 확인한 뒤 튜닝 사본의 11자리를 바꿔 넣습니다. 튜닝 원본 파일은 바꾸지 않습니다 [추론, 설계].
- 확인할 위험 [추론]: Ω701 에서 모형 저장고 하나가 안·밖 링크에 걸치면 OU CAO:125-150 이 `unresolved model membership` 로 멈춥니다. codex plant 는 v3c3 에서 설정 단계를 끝까지 갔지만(B0 §5.1) 우리 plant 의 저장고–링크 지지는 다릅니다(K8b SC1001 정지선 모형 등). P0-3 이 먼저 봅니다.

### 3.2 M1 이웃 검사 + 조합

| 무엇 | codex | 우리 자리 |
|---|---|---|
| 후보 만들기 `meter_neighbors` | CX SD:556-599 | OU SD 에 없음 → 새 함수(OU SD:512 `load_prices` 앞, 모듈 수준) |
| 채점·조합 `audit_meter_neighbors` | CX SD:602-658 | 같음 |
| 예산별 검사 `audit_meter_budget_candidates` | CX SD:661-689 | 같음 |
| 3블록 필수 검사 | CX SD:197-198 | OU SD:166 다음(블록 검사 뒤) |
| 예산 후보 모음 | CX SD:963(`meter_budget_candidates = []`), :1216-1220 | OU SD:685 앞, OU SD:932-933 을 codex 꼴로 |
| 호출 | CX SD:1233-1239(held 유지 뒤, `best is None` 검사 뒤) | OU SD:934-935 다음 |
| 기록 | CX SD:1287-1289(`finite_neighbor_audit_performed`, `meter_neighbor_audit`) | OU SD:980 |
| 다른 축을 바꾸면 거부 | CX SD:622-626(`Finite meter candidate changed another actuator`) | 함께 옮김 |

- 쓰는 것: `coord.encode/decode/validate/valid`, `coord.move_box.entries`, `evaluate`, `feasible`, `finish_trial_derivatives` 는 우리 SD 에 이미 있습니다(OU SD:302-422, :612-622, :693) [읽음]. SEQ 의 차이는 VSL·미터 secant 갈고리 둘뿐이라(CX SEQ:116-117, :205-208) 옮기지 않습니다 [실행 diff].
- 켜는 값: codex `adapter.sdmpc_meter_neighbor_audit` true(CFG_B:7732)는 SD 옵션 이름 목록(CX SD:126-127)으로 policy 에 들어갑니다. 그래서 정책 토큰(OU SD:958 `token(policy)`)이 바뀝니다 [읽음]. 이것이 재생 설계(§8.6)를 정합니다.

### 3.3 M2 cap 후보 3

- 코드는 이미 같습니다(OU SD:681 `targets = ordered[:options['max_leader_candidates']]`, :925-930 `next_budget` 으로 더함) [읽음]. 바뀌는 것은 값 1 → 3 뿐입니다(OUC:7696 = 1, CFG_B:7696 = 3).
- codex 는 리더 seed 영역을 `np_only=True` 로 부릅니다(CX SD:934, :952; CX PRB:947-953). 영역에서 SD 가 쓰는 것은 `np_values` 뿐입니다(OU SD:675) [읽음]. np_only 는 같은 서비스를 가진 녹색이 여럿일 때 역산을 피하려는 것입니다(CX PRB:948-950 주석). ⟨Q4⟩ (나)를 고를 때만 함께 옮깁니다.
- 정책 토큰: `max_leader_candidates` 는 `joint_owner_game` 옵션이라 SD policy(OU SD:543 `cfg.network.sdmpc_options`)에는 들지 않는 것으로 봅니다 [추론, P0-6 에서 확인].

### 3.4 M3 녹색 0 금지

| 무엇 | codex | 우리 자리 |
|---|---|---|
| 설정 읽기·검사 | CX PRB:49-58, spec 에 `allow_zero_green` 저장 :145 | OU PRB:105-106 다음, spec :195-198 |
| 허용 판정 `operating_green_allowed` | CX PRB:866-868 | OU PRB 새 함수 |
| 미터 축 허용 집합 | CX SD:406-414(하한 `ramp_operating_green_floors` + 허용 판정; 빈 집합이면 ValueError) | OU SD:338-345(지금 `g == 0 or g ≥ min`) |
| 기록된 명령 읽기 | 기록된 0 은 읽기 허용(CX PRB:867 주석) | OU PRB:333(`prepare_control`) 은 그대로 |

### 3.5 M4 저장 보호 + M4a 운영 seed + M4b held 유지

| 무엇 | codex | 우리 자리 |
|---|---|---|
| 하한 만들기 `configure_operating_bounds` | CX PRB:871-908 | OU PRB 새 함수 |
| 부르기 | CX SD:827-828(직전 명령 `reference` 만든 뒤) | OU SD:571 다음 |
| 기록 | CX SD:1270 `meter_operating_bounds` | OU SD:965 근처 metadata |
| 운영 seed(USG 없는 가지) | CX SD:858-864: 기준이 새 범위 밖이면 미터 축만 자름 | OU SD:587 다음 |
| seed 를 PFO·NUF 초기화에 씀 | CX SD:907, :919-922, :945 | OU SD:629, :641-644, :667 |
| 가능 검사에 범위 포함 | CX SD:898 `coord.valid(coord.encode(action))` | OU SD:618-622 |
| held 유지 | CX SD:28-51 `retain_feasible_held`, :1221-1230, :1300 `original_held_candidate` | OU SD:27 다음, :933 다음, :990 |

- 쓰는 상태: `state.lane_ramp_runtime.buffers[ramp]` 의 `_lane_buffers`·`snapshot()`(`upstream_travelling_veh`·`head_ready_veh`)·`head_position_m`·`lanes`·`spacing_m`. 우리 줄기에도 이 이름이 있습니다(OU LPR:534 `LaneRampRuntime`, OU `physical_ramp_boundary.py:85-100, :154-155, :565`) [실행 `git grep`]. 같은 뜻인지는 P0-5 가 봅니다.
- 하한 식 [계산, CX PRB:897-901]: 문턱을 넘은 차로가 있으면 하한 = max(2, min(10, 직전 + 2)). 직전이 g10 이면 하한 10 → 그 결정은 g10 만 허용. 아니면 하한 2(녹색 0 금지).
- 변경 한도 2 s 는 두 줄기가 같은 spec 파일에서 읽습니다(`topology_routes_v2_8ac6fd.json` `/max_green_change_sec` = 2, 두 트리 sha 같음 `089238ed…`) [실행].

### 3.6 M5 FW_E 미터 4개 머리 서비스 표

| 녹색 g | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| codex 머리 표 (대/주기/차로) [읽음 CFG_B:8161-8206] | 1.0 | 1.5 | 2.0 | 2.5 | 3.0 | 3.5 | 4.0 | 4.2 | 4.2 |
| 우리 배분 표 (대/주기/차로) [읽음 OUC:7524-7534] | 0.71 | 0.99 | 1.44 | 1.89 | 2.34 | 2.79 | 3.24 | 3.69 | 4.2 |
| 비 codex / 우리 [계산] | 1.408 | 1.515 | 1.389 | 1.323 | 1.282 | 1.254 | 1.235 | 1.138 | 1.000 |
| VISSIM 1차 블록 ÷ codex 표 (B 세 시드, FW_E) [읽음 READBACK:95-110] | 0.93–1.00 | 0.89–0.98 | 0.90–0.95 | 1.01–1.09 | 0.93 | 0.67 (1블록) | 모름 | 모름 | 모름 |
| VISSIM 1차 블록 ÷ 우리 표 [읽음 READBACK:95-110] | 1.31–1.41 | 1.35–1.48 | 1.25–1.32 | 1.34–1.45 | 1.20 | 0.84 (1블록) | 모름 | 모름 | 모름 |

- codex 설치: CX LPR:616-620(`{'0': 0., g: n*3600/10}` 그대로). 우리 설치: OU LPR:512-520 → OU PRB:84-86 `measured_head_service_table` → OU PRB:36-81 정규화(K3) [읽음].
- **충돌** [읽음 OU PRB:75-77]: K3 정규화는 "최대 서비스 녹색이 서비스를 나누면" ValueError 입니다. codex 표는 g9 = g10 = 4.2(10681 은 8.4)라 그대로 넣으면 결정마다 멈춥니다. ⟨Q4⟩ 가 이것을 정합니다.
- B 는 g9 를 썼습니다: RM_C10490 g9 주기 240 / 0 / 165, RM_C10681 g9 75 / 30 / 45 (세 시드, 810 주기 중) [읽음 READBACK §2.2].
- FW_W 미터 4개(10480·10482·10646·10644)는 codex 도 배분 표입니다. 녹색별 VISSIM 값은 10480 g2 1차 3블록(v3c3-s41, 360 = 1.0 대/주기)뿐입니다 [읽음 READBACK:97, :131]. ⟨Q5⟩.
- 지금 우리 RM_C10490 머리 표(1.0·1.0·1.44·…, OUC:8092-8104)는 codex 10490 줄로 바뀝니다. g3 은 지금 정규화로 빠져 있고(같은 서비스 1.0), codex 줄에서는 1.5 로 다시 생깁니다 [읽음·계산].

---

## 4. 옮기지 않는 것

| 무리 | 항목 | 까닭 | 근거 |
|---|---|---|---|
| 64cf 로 맞춘 계수(D 부류) | eval_036 셀별 FD(ρ_crit·a_m)·상태 반응, 셀별 δ_merge(셀 10·12·21·23), `port_gain/parameters.json`·`port_profile.json`, `/freeway/segment_params`, `retained10638/local_protocol.json`, 램프 합류 수용 노드 4개, 램프 주행 속도, 단일 차로 인과 수용, known_wout 일곱 키, 망 핀만 바꾼 codex 계약 11개, native_beta 8묶음, goal8 권한 추가분 | 64cf-s29 자료로 맞춘 "자격 없음" 값. 우리 K6(셀 FD 거부)를 뒤집음. 본선 합류·용량 기구(S1·C4; METER_NEXT2 의 '본선 이득 기구')는 따로 | [읽음 R_MECH:113-124, :232; B0 §2.5; TAKEOVER_PLAN:84] |
| 표본 안 보정 | `/urban/calibrated_aggregate` | seed29 폐루프로 맞춘 표본 안 값. B 에서도 끔 | [읽음 R_MECH:139; B0 §2.2 Q6c] |
| VSL 부분 | 집합 50–110, 구역 머리 2·5·10·13, `sdmpc_vsl_activation_secant`, `sdmpc_fixed_vsl`, Carlson A0.5/E2.0, `physical_vsl_sign_binding`, `observed_vsl_history` | D-K9-92: VSL 은 오프라인 먼저. plant VSL 이 VISSIM 반응과 다름(VSL_OFFLINE §4.1 여섯 자리) | [읽음 R_MECH:84-93; VSL_OFFLINE:226-241] |
| 도시 묶음(C5) | 도시 저장 보호(USG, `/urban/storage_release_guard` 예비 녹색 2 s), 머리 실측 자원 v11, 무신호 10, 머리 현시 대기 귀속, SC1001 공유 접근 | 다른 묶음. B 의 SC1001 배분과 얽혔을 수 있으나 몫 모름 | [읽음 R_MECH:138-143; CFG_B:7958-7961] |
| 진입 지연(C3·D3) | 기원별 게이트 지연 | 다른 묶음 | [읽음 R_MECH:158] |
| 링크 124 공유 차로 | `sc1001_shared_lane_receiving`(CX RCC:1929-1975, LOR:659·722) | 우리 줄기에 바탕(`direct_exit_legsplit`)이 없음 [실행 `git grep` 0]. ⟨Q6⟩ | [읽음] |
| 속도 기구 | `sdmpc_response_cap_cache`(CX SD:59-88, :226-228, :758-767), `lazy_trial_derivatives`, geometry 캐시 | 결정 값을 바꾸지 않는 속도 기구로 적혀 있음. C1 은 기구 몫을 보는 묶음. ⟨Q9⟩ | [읽음 CX SD:758-767 주석; CFG_B 와 OUC adapter 차이 = fixed_vsl·audit·cap_cache·vsl_secant 넷 실행] |
| 미터 secant | `meter_activation_secant`(CX SD:547-553, SEQ:116-117) | codex 설정에서도 꺼짐 | [읽음 R_MECH:75] |
| 기타 codex 기구 | 종단 비용·거리 보상(CX SD:262-269, :338-364), 신호 1 ms 수리(CX SD:493-503), `hold_previous` 유지, 옛 그룹 램프 도착 키, 고속도로 5 s 다중 시계 | 다른 묶음이거나 우리 고침과 충돌 | [읽음 R_MECH:125, :171, :176] |

---

## 5. 설정 키 (경로 문자열 없음, 이름 + sha)

- 새 구역 `c1_port` 하나. 구역이 없으면 c20aff1d 그대로입니다. 하위 키는 정확한 키 집합만 받고(모르는 키 → ValueError), 기구별로 따로 켤 수 있습니다(탐침 팔용, ⟨Q11⟩).
- 증거 파일은 코드 상수 폴더(가칭 `diagnostics/c1_port/evidence/`) 안에서 **이름**으로만 찾습니다. 이름에 경로 구분자·`..`·절대 경로가 있으면 ValueError, sha 가 다르면 ValueError 입니다(K9-3 ⟨Q7⟩ (가) 꼴).

| 하위 키 | 값 꼴 | codex 대응 | 설치 자리(OU) |
|---|---|---|---|
| `c1_port.omega701` | `{"bundle_name": "omega701_v3c3_bundle.json", "bundle_sha256": <P0 고정>}`. 묶음 목록 = 파일 11개(이름·sha·바꿀 튜닝 자리): membership `9bb740b3…`, 경로 계약 `08fec9c7…`, 문서 8개(§3.1 sha), Ω701 판 lane plant manifest(P0 에서 만듦) | CFG_B:8323-8324 + B0 REGEN 8 + manifest | RS:341-350 첫머리 |
| `c1_port.meter_neighbor_audit` | `true` | `adapter.sdmpc_meter_neighbor_audit`(CFG_B:7732) | SD configure(OU SD:96-97 꼴로 options/policy) |
| `c1_port.max_leader_candidates` | `3` | `/adapter/joint_owner_game/max_leader_candidates`(CFG_B:7696) | adapter 의 leader 옵션 검사(OU ADP:12996-13013) 뒤에 덮음 |
| `c1_port.allow_zero_green` | `false` | `/actuation/real_world_ramp_metering/allow_zero_green`(CFG_B:7541) | PRB configure(OU PRB:105, :195-198) |
| `c1_port.storage_release_guard` | `{"enabled": true, "trigger_fraction": 0.9}` | 같은 자리(CFG_B:7542-7545) | 같음 |
| `c1_port.held_retention` | `true` | 키 없음(codex 는 cap 모드면 늘 켬) | SD(§3.5) |
| `c1_port.head_service` | `{"evidence_name": "head_service_fwe_c1.json", "evidence_sha256": <P0 고정>, "meters": ["RM_C10639","RM_C10681","RM_C10490","RM_C10484"], "full_service_rule": <⟨Q4⟩>}`. 증거 = codex 값(CFG_B:8161-8206) + READBACK K7 표(비교만, 값 출처 아님) | `/freeway/physical_ramp_head_service_veh_per_cycle` | LPR:512-520 설치 전 `component.ramp_head_service_veh_per_cycle` 에 씀 |

- `make_config --c1` 이 OUC + `c1_port` 전체를 쓴 배포 튜닝을 만듭니다. 튜닝 파일 sha 는 보충 C1 고정 때 적습니다.
- 메타 기록: 모든 결정에 `/metadata/c1_port`(켠 하위 키, 증거 sha, 망 sha `3de889f0…`)를 씁니다. 폐루프 관문의 선언 차이 E_C1(D-K9-71 의 E_K92 꼴)에 넣습니다.

---

## 6. 우리 고침·K9-3 과의 관계

### 6.1 K8·K9-1·K9-2 고침

| 고침 | 우리 자리 | C1 과 닿는 곳 | 처리 |
|---|---|---|---|
| K8-3 S1-OWN 미터 넘침 귀속 | OU SD:262-297, `meter_spill.py`(e2f3c214…) | 이웃 검사·held 유지는 소유자 합 `objective_veh_h` 로 고름(CX SD:620, :655, :46). S1-OWN 은 합을 바꾸지 않고 소유자 몫만 옮김(OU SD:263-266 주석) → 선택 기준 불변, PFO 소유자 비용은 영향 | 그대로 둠 [읽음; 결정 영향은 추론] |
| K3 서비스 표 정규화 | OU PRB:36-86, LPR:512-520 | codex 표 g9 = g10 과 충돌(§3.6) | ⟨Q4⟩ |
| K6 plant 기준 키 거부 | OU LPR:69-89 | C1 은 셀 FD·δ_merge 를 안 넣음 | 그대로 |
| K8-9 유령 경로 별칭 | OU CAO:252-273 | Ω701 경로 계약에서도 필요(B0 시험) | 그대로, G-K1 정적 (d) 로 확인 |
| K8b SC1001 동측 정지선·출구 법칙 등 26잎 | OUC `/urban/stopline_approach` 등 | Ω701 이 SC1001 북쪽 링크 37 을 더함 → SC1001 녹색 선택이 바뀔 수 있음 | 그대로, G-K1 동적·§8.6 SG2 대조 |
| K9-1 W1 (SC1001→W_RAMP) | OU RS:146-186, :422 | 같음(SC1001) | 그대로 |
| K9-2 W (SC109 서측 직진 5,209.8)·H-b 씨앗 | OU RS:242-286, :415, :423-424 | Ω701 이 SC109 접근 1·SC108 3 링크를 더함 → K9-2 판정 잎(SC109·링크 174)이 바뀔 수 있음 | 그대로, J 는 ⟨Q12⟩ |
| RM_C 램프 도착 키 + strict | OUC `/calibration_override/prediction/local_ramp_arrival_forecast` | 미터 후보 채점에 쓰이는 예측 | 그대로 |
| 예외 한정 유지 `hold_previous_on_exception` | OU VBS:1241-1250 | 결정 시간이 늘면 예외 아닌 시간 문제는 StallSec 로만 막힘 | 그대로, G-K5b |
| 정렬 합 PYTHONHASHSEED(K1) | UQM:1306 | — | 그대로 |
| 정책 토큰 | OU SD:527-528, :958 | M1 이 policy 에 들어가 토큰이 바뀜 → V-A 기록 상태(T > 900)에서 키 켬 재생은 `load_prices` 에서 멈춤(B0 R1–R3 와 같은 자리) | 재생 설계 §8.6 |

### 6.2 V-A 기록과의 사슬

- V-A 는 VSL 축이 살아 있었고(FW_E seg10 100 결정 9 / 10 / 14번), 미터는 61결정 × 8 내내 g10 이었습니다 [읽음 B_RESULTS §2.1; METER_CAUSE:18].
- C1 은 V-A 배포 튜닝(OUC) 위에 `c1_port` 만 더합니다. 그래서 C1 − V-A 는 "같은 줄기, C1 키만 다름" 짝입니다. VSL 은 ⟨Q8⟩ (가)면 같은 정책입니다.

### 6.3 미룬 K9-3 D1·D2 와의 관계

| 항목 | K9-3 | C1 | 관계 [추론, 근거 칸마다] |
|---|---|---|---|
| 바꾸는 자리 | RS:424 다음(D2), RS:430 다음(D1) [읽음 K9_3_DESIGN_DRAFT:56, :59] | RS:341-350 첫머리(Ω701), SD·PRB·LPR | 겹치지 않음 |
| 10681 모형 도착 | D1 만 × 3.6, D1 + D2 × 4.9–5.0 (VISSIM 대비 0.16 → 0.58 / 0.79) [읽음 K9_3_DESIGN_DRAFT:287] | 이웃 검사가 10681 조임·풂을 채점 | D1 없이는 10681 압력을 덜 봄 → 10681 후보 값이 작게 나올 수 있음 |
| 10646 모형 도착 | D1 로 × 0.4 [읽음 K9_3_DESIGN_DRAFT:290] | FW_W 미터 후보 | 같은 이유로 C1 위에 K9-3 를 얹으면 미터 선택이 바뀔 수 있음 |
| 벽시계 예산 | G-K5 1.0158(키 끔) | G-K5a 같은 예산(키 끔), G-K5b 키 켬 새 예산 | 키 끔 예산을 같이 씀 |
| 관문 J | K9-1·K9-2 잎 | 같은 잎 + C1 잎 | K9-3 재개 때 C1 켬 상태에서 J 를 다시 셈 |
| D1 의 codex 길 | codex `known_wout_native_choice_prior`(망 relFlow) [읽음 R_MECH:156] | C1 에 안 넣음 | D1 을 codex 길로 할지 K9-3 길로 할지는 K9-3 재개 때 |

- 권장 순서는 D-K9-91 그대로 C1 먼저입니다(⟨Q19⟩ (가)). METER_NEXT2 의 순서표는 D1·D2 → D4·D3 → D5 → S1 → S4·S5·S3 였습니다 [읽음 METER_NEXT2:265-275]. C1 은 그 가운데 S3(목적 경계)·S4(유한 후보)·S5(안전 장치)·D4(머리 표, FW_E 만)를 앞당기는 셈입니다. 앞 칸(D1·D2·D3·D5·S1)이 없는 상태라는 것을 위험(§10)에 적습니다.

---

## 7. 기대 모형 효과 [추론, 산술; 근거 태그는 칸마다]

| 대상 | 지금(V-A, OUC) | C1 | 근거 |
|---|---|---|---|
| 목적 영역 | Ω635 | Ω701 = Ω635 + 66(도로 35·커넥터 31; SC6 12·SC5 5·SC101 4·SC12 4·SC108 3·SC107 3·SC1001 1(37)·SC1004 1(66)·SC1002 1·SC109 1·SC16 1·SC1 1, 두 링크는 두 신호에 걸침) | [실행 membership] |
| 미터 상류 링크(124·32·121·69·70·68·129·31) | Ω635 안 | Ω701 안(같음) → 미터 대기 회계는 그대로 | [실행 membership 대조] |
| TSC 목적 | 접근로 66 체류 0 가중 | 체류 1 가중 → 접근로 대기를 줄이는 쪽 녹색 | B − V-A 66링크 −246.1 / −286.6 / −271.8, Ω635 +329.7 / +184.9 / +359.1, Ω701 +83.6 / −101.8 / +87.3, ④ +549.1 / +275.6 / −94.3, Ω 밖 (a) +465.5 / +377.3 / −181.6 [읽음 B_RESULTS:65-71; B 는 다른 제어기라 몫 아님] |
| 이웃 검사 후보 수(g10 상태, 시작안 하나) | 0 | 조임 10(미터 8 + 고속도로 묶음 2), 풂 0(g10 이라 시작안과 같아 빠짐), 조합 0–1 | [계산 CX SD:575-599] |
| 조임 계획(블록 0/1/2) | — | g8 / 6 / 4(변경 한도 2 s 를 블록마다) | [계산 CX SD:579-589] |
| 결정당 이웃 검사 예측 수 | 0 | 시작안 최대 4개(best + 예산 3, 같은 것 빼기) × (10–20) + 조합 → 대략 10–84 | [계산; codex 64cf-s29 joint 실제 22–53 (다른 망, 한 시드) 읽음 RAW_CHECK:171] |
| 조임이 뽑히는가 | — | 모형 Ω 감소 > 1e-7 일 때만(OU parameters `objective_tolerance` 1e-07). V-A 상태에서 우리 plant 는 조임에 Ω 가 늘거나 그대로(기울기 "열어라"/0, dNUF/dz ≤ 0.43 veh/h) → 거의 안 뽑힐 수 있음 | [읽음 METER_CAUSE a2·a2-5·a3; METER_NEXT2:228] |
| 머리 표(FW_E 4) | g2 255.6 veh/h/차로 | g2 360 (×1.41), g5 900 (×1.32), g8 1,440 (×1.23), g10 1,512 (같음) | [계산 §3.6] — 저녹색에서 모형 방류가 늘어 조임의 모형 구속이 약해짐 |
| cap 후보 | 1 | ≤ 3 | NUF 잔차가 늘 음수(중앙 −100 veh/h)라 리더 압력이 거의 없었음 → 작은 변화로 봄 [읽음 METER_CAUSE a5] |
| 녹색 0 금지 | 0 허용 | 0 금지 | g10 에서 ±2 s 한도라 0 은 처음부터 닿지 않음 → 미터가 2 s 근처로 내려간 뒤에만 뜻이 있음 [계산] |
| 저장 보호 | 없음 | 점유 ≥ 0.9 차로가 있으면 하한 = 직전 + 2 | g10 에서는 "조임 금지" 로만 작동 [계산 §3.5] |
| held 유지 | 없음 | 운영 seed 가 고른 안보다 낮으면 남김 | codex joint 64cf-s29 4,500 s 에서 held 437.20 이 후보 438.59·438.84 보다 낮아 남음(다른 망, 한 시드) [읽음 VSL_OFFLINE:26] |
| 결정 시간 | V-A SDMPC 평균 513.5 / 539.2 / 465.4 s, 최대 743.7 / 818.6 / 782.8 s | 늘 것(cap 2·3 + 이웃 검사). 크기는 탐침에서 잼 | [읽음 VA_REPORT:622]; codex 코드 이 PC 이웃 검사 49.6–57.2 s(예측 11) ~ 174.0–242.4 s(예측 35–36), cap 2·3 각 약 126–209 s (64cf-s29 상태, 다른 망, 한 시드) [읽음 A0_PROFILE:162-240] |
| SC1001 배분 | V-A SG2 900–2,700 s 578 / 638 / 680 s | 모름. 링크 37 이 목적에 들어감 | [읽음 INPUT1099:136; 추론] |
| ④b(입구 대기) | 목적 밖 | 목적 밖(그대로) | Ω701 도 ④b 를 세지 않음 [읽음] |

- 정리 [추론]: C1 의 큰 모형 변화는 Ω701 쪽(TSC)일 것이고, 미터 쪽은 앞 칸(S1 본선 기구, D1)이 없어 조임 후보의 모형 값이 작을 수 있습니다. 탐침이 "조임이 한 번이라도 뽑히는가" 를 먼저 보고, 0 이면 멈추고 묻습니다(§8.9 S-C1-7).

---

## 8. 관문 (보충 C1 에 미리 선언할 것)

### 8.1 단계 순서

1. 사용자 결정(§12) → 보충 C1 고정(sha 를 `CP/LOG.md` 에, 그 전 계산 0).
2. **P0**(읽기·증거 빌드·구조 점검) → 값 파일 `C1_VALUES.json` sha 를 첫 탐침 전에 LOG 에 고정.
3. **미니 탐침**(스크래치 트리 `D:/VISSIM-merge/k8_gate_trees/codexhandoff/c1_probe/`, 보고만).
4. 구현(GWT8 새 브랜치 `claude/c1-port-<날짜>` from c20aff1d, 미푸시; 이 초안 범위 밖, 사용자 결정 뒤) + 커밋별 관문.
5. **오프라인 재생 비교 R**(보고 + 미리 정한 멈춤).
6. 판정 단계 `c1t`: J + F. 블라인드 가드가 그 전 계산을 막습니다.
7. 독립 검증(하네스를 import 하지 않는 재계산).
8. 폐루프 비교 규칙 `COMPARE_RULE_C1` 고정(첫 C1 런 전) → 폐루프 발사는 따로 물음.

- 공통 실행 위생: 무거운 Python 한 번에 하나, BELOW_NORMAL, `python -B`, `PYTHONHASHSEED=0`, env_hsw, 스레드 1, 5분 넘는 일은 WMI 분리, 소유 PID 만 kill, FZP 스캔 한 번에 하나, C:·D: 8 GB 밑이면 멈춤, 금지 시험 7종 0, 동결본·런 폴더·GWT8 쓰기 0(구현 단계 전), 봉인 시드 0.

### 8.2 P0 (보충 고정 뒤, 탐침 전; 읽기·증거만)

| # | 내용 | 멈춤 |
|---|---|---|
| P0-1 | Ω701 묶음 증거: 소속·경로 계약을 우리 v3c3 Ω635(30abb1db…)에 codex 빌더(`diagnostics/build_control_area_membership.py:expand_controlled_intersection_area`, prepare_next 21–56줄 [읽음 B0 §2.3])로 다시 만들어 FRZ_B1 의 9bb740b3…·08fec9c7… 와 바이트 대조 | 다르면 STOP·질문 |
| P0-2 | 우리 팩 문서 8개를 같은 재결속 규칙(prepare_next 57–108줄 [읽음 B0 §2.3])으로 c20aff1d 판에서 다시 만들어 FRZ_B1 sha(§3.1)와 대조. Ω701 판 lane plant manifest(우리 b119d6d9… 에서 `/membership` 한 칸만 바꿈) 생성 | 다르면 STOP·질문 |
| P0-3 | 구조 점검(재생 0): c20aff1d + Ω701 묶음으로 설정 단계만 돌려 `configure_runtime` 끝까지 가는지(OU CAO:125-150 `unresolved model membership`, LPR:299, AR:168-185 `extend_gate_routes`·`extend_routes`). 상태 = V-A v3c3-s31 T=900 | 예외 → STOP·질문 |
| P0-4 | 머리 표 증거: codex 값(CFG_B:8161-8206) 복사 + ⟨Q4⟩ 규칙 적용 결과 + READBACK K7 표 sha(`RB/out/discharge.json` 34220b5c…, `headcurve.json` 1978197c…) | 규칙 결과가 §3.6 표와 다르면 STOP |
| P0-5 | 저장 보호 상태 이름 점검: V-A v3c3-s31 T=900 상태에서 `lane_ramp_runtime.buffers[RM_C*]` 의 `_lane_buffers`·`snapshot()` 키·`head_position_m`·`lanes`·`spacing_m` 이 있고 유한한지, 8미터 점유율 값을 적음 | 없음·비유한 → STOP |
| P0-6 | 정책 토큰 점검: 각 하위 키를 하나씩 켰을 때 `token(policy)` 가 바뀌는지 표(재생 0, configure 만) | 표만 |
| P0-7 | 블라인드 노출 목록: R-obs v3c3-s47 의 F 창에서 66링크·링크 37·127·129·10491 값을 담은 기존 산출을 이름·키 이름으로만 찾아 고정(값은 열지 않음). D-K9-84 Q3 의 Ω701 재집계는 V-A·J1·NC3 9런이었다는 점을 첫 줄에 적음 [읽음 NOTES:277] | 목록과 규칙 결과가 다르면 STOP |

### 8.3 미니 탐침 (스크래치, 보고만)

- 트리: `git archive c20aff1d` + 패치(선언 키로 M0–M5). 패치·팔 튜닝·`C1_VALUES.json` sha 를 첫 계산 전 LOG 에 고정.
- 팔: **OFF**(OUC), **Ω**(M0), **M**(M1–M4 + M4a·M4b), **H**(M5), **C1**(전부). 보고 팔: M 에서 cap 1(이웃 검사만 몫), M 에서 held 유지 끔.
- 상태(첫 SDMPC 결정이라 직전 sdmpc_state 없음 → `load_prices` 를 그대로 지남, OU SD:517-518): V-A v3c3-s31·s41·s43 T=900, R-obs v3c3-s31·s43 T=900(K9-2 탐침 표본 상태와 같은 런).
- plant 잡(기록 행동, 결정 없음): R-obs v3c3-s31·s43 각 8상태(K9-2 탐침 둘째 표본 규칙) × {OFF, Ω} — Ω 는 목적 합만 바꾸므로 셀·저장고 궤적은 같아야 함.
- 미리 정한 멈춤·질문
  1. 예외·장부·불변식 위반 1건 이상.
  2. Ω 팔 plant 잡에서 저장고·셀 궤적이 OFF 와 다름(목적 합 말고) → STOP.
  3. M·C1 팔에서 조임 후보가 5상태 모두 0번 뽑힘 → 구현 전 보고·질문(§8.9 S-C1-7 과 같은 꼴).
  4. 키 켬 결정 벽시계가 1,500 s 를 넘는 상태가 있음 → 보고·질문(G-K5b 미리 보기).
- 보고: 팔·상태별 이웃 검사 후보 표(이름·Δ 모형 Ω·가능 여부)·고른 후보, 블록별 미터 녹색, 저장 보호 하한·점유, cap 목표, held 유지 여부, Ω701/Ω635/OUTW, SC1001 SG2·SG5 계획 녹색, 결정 벽시계·예측 수.

### 8.4 커밋 계획 (구현 단계, 사용자 결정 뒤; GWT8 새 브랜치 from c20aff1d, 미푸시)

- 공통: 명시 경로만, 작성자 `Ming2you <alsrjsrb1915@snu.ac.kr>`, 메시지 끝 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`, 앞 관문 조건이 거짓이면 다음 커밋으로 가지 않음.

| 커밋 | 파일 | 런타임 변경 |
|---|---|---|
| C1-0 하네스(진단 전용) | `k8_gates/sa/` 기록기 새 필드(이웃 검사·하한·held·SG2 계획; `c1_record.json` 에만), 가드 `c1_judging_state`(R-obs v3c3-s47 F 표본 거부, 토큰 `c1t` + 보충 C1 sha), `sa_arms.py --c1`, 비교기(보충 21 §6 + A_C1) | 0 |
| C1-1 Ω701 | RS 로더 + `c1_port/evidence/` 묶음 + `tests/test_c1_omega.py` | 있음(키 없으면 0) |
| C1-2 미터 결정 | SD(§3.2·§3.3·§3.5), PRB(§3.4·§3.5), `tests/test_c1_meter.py` | 있음(키 없으면 0) |
| C1-3 머리 표 | LPR·PRB(⟨Q4⟩ 규칙), 증거, `tests/test_c1_head.py` | 있음(키 없으면 0) |
| C1-4 팔·문서 | `make_config_n31.py --c1`, `config_n31_v2_c1.json`, `c1/README.md` | 0 |

- 배포 CFG(OUC)에는 이 단계에서 키를 넣지 않습니다(승격은 확인 뒤 따로 결정).

### 8.5 관문 정의

**공통 비교 규칙** = 보충 21 §6(정규화 N, HARD H1–H5, 결정적 잎 D, 허용 V ∪ R3 ∪ F, 결과 넷) 그대로, 허용에 **A_C1** 만 더함.

- A_C1 = 변환 원천 목록 안 SD·PRB·LPR·RS 바이트 sha 차(새 값 = 새 쪽 sha).
- A_C1-M(키 켬 비교에서만): 한쪽에만 있는 `/metadata/c1_port`, `/metadata/meter_neighbor_audit`, `/metadata/meter_operating_bounds`, `/metadata/original_held_candidate`, `finite_neighbor_audit_performed` 값 변화(false → true), `/metadata/sdmpc_state/policy_sha256`. 그 안의 D 잎 조건: 증거 sha = 새 쪽 증거 바이트 sha, 망 sha = 3de889f0…. 다르면 미분류.

| 관문 | 무엇 | 참이어야 할 조건 |
|---|---|---|
| **U** | 기존 K8b·K9·K9-2 단위 + 새 `test_c1_*.py` | 기존 결과가 c20aff1d 와 시험별로 같음(알려진 거짓 결과 포함), 새 시험 전부 참 |
| **B** | 증거 빌더 `--check` | 증거 `values` 가 `C1_VALUES.json` 이 가리키는 P0 증거와 정규 JSON 비트 같음 |
| **G-K0** 키 끔 = c20aff1d | 결정: 보충 34 오프라인 관문 상태(GB-7′ 무제어 61, GB-9′ SDMPC 4) + V-A 세 런 각 4결정(900·2,700·4,950·6,300) 대 기록·보충 34 산출. plant: K9-1 탐침 표본 26 가운데 v3c3-s47 상태 뺀 것 + K9-2 탐침 둘째 표본 16. 기준 = 같은 실행 안 `git archive c20aff1d` 트리 | 결정: 보충 21 §6 결과 모두 동일 쪽. plant: 숫자 잎 차 0. `summary.json` 한쪽 잎 0 |
| **G-K1** 키 켬 차이 분류 | 정적 (a) Ω 소속 집합 차 = 정확히 66링크(링크 번호 목록 고정), 경로 계약 차 = turn 57개, 튜닝 경로 값 차 = 11개(키 8자리; 회랑 목록 안 4개 포함) (b) 미터 허용 집합 차 = 0 빠짐 + 하한 (c) 머리 표 차 = FW_E 4미터 행만 (d) 유령 별칭 키 3개 그대로 쓰임 (e) `configure_runtime` 끝 `cfg.network` 깊은 비교 차 경로 ⊆ 위 + `c1_*` 속성 (f) 작업자 프로세스 안 소속·표·하한이 주 프로세스와 같음. 동적: 잎을 C0(미터 축·미터 대기·Ω701 66링크 저장고 회계), C1(그 신호 17곳 녹색·offset, 리더 cap·NP), C2(합계), C3(그 밖)으로 | 정적 (a)–(f) 모두 참, 그 밖 경로가 하나라도 다르면 STOP. 동적: C3 은 첫 차이 스텝·경로와 함께 목록, **C3 첫 차이가 C0 첫 차이보다 앞서면 STOP** |
| **G-K2** 식 재현 | (a) g10 상태 시작안 하나의 이웃 후보 = 10개, 계획 g8/6/4 (b) 저장 보호 하한 = max(2, min(10, 직전 + 2))(점유 ≥ 0.9) 아니면 2 (c) 머리 설치 = n × 360 veh/h(10681 은 미터 값 그대로 = 2차로 합) (d) 같은 plant 기록에서 Ω701 목적 − Ω635 목적 = 66링크 모형 체류 (e) cap 목표 ≤ 3 | (a)(b)(e) 정확히, (c)(d) 상대 1e-9 |
| **G-K3** 거부·묶기 | 이름 구분자·`..`·절대 경로 → ValueError, sha 다름 → ValueError, 3블록 아닌데 이웃 검사 → ValueError(CX SD:197-198 꼴), 문턱 ∉ (0,1] → ValueError(CX PRB:55-58 꼴), 모르는 하위 키 → ValueError, ⟨Q4⟩ 규칙 밖 표 → ValueError, `make_config --c1` 이 하위 키 전부를 씀 | 모두 참 |
| **G-K4** 탐침 재현 | 커밋 코드로 탐침 상태를 돌려 스크래치 탐침 같은 팔과 대조 | 모든 차 상대 1e-9 이하, 연산 순서로 설명될 때만 |
| **G-K5a** 키 끔 벽시계 | 키 끔 결정 재생 짝(`git archive c20aff1d` 트리 대 커밋 트리, ABAB, VISSIM 0) | 중앙 비 ≤ **1.0158**(K9-1 G-EB-11(a) 남은 예산, K9-3 G-K5 와 같음). 사분위 > 0.006 이면 "가릴 수 없음" 보고·질문 |
| **G-K5b** 키 켬 결정 시간 | 탐침·R 의 C1 팔 결정 벽시계 | 최대 ≤ **1,500 s**(D-K9-88 관문 1 과 같은 값; 러너 무진행 상한 StallSec 2,400 s [읽음 B0 줄임말, TAKEOVER_PLAN Q5c] 아래. C1 러너의 값은 보충 C1 고정 때 확인). 평균·중앙 보고. 넘으면 STOP·질문(⟨Q9⟩ 선택지) |
| **G-RR** 기록 대 재생 (선언 차이) | (a) 키 끔 재생 대 V-A 기록: 차이 = GB-7′ 허용 목록 + 연쇄 재생 HARD 잎(V-B 꼴: `/prediction_error/source_action_json`, `/metadata/sdmpc_state/previous_application/{source,receipt_sha256}`)만. (b) 키 켬 재생 대 V-A 기록: 차이를 A_C1-M + C0–C3 로 분류. (c) 키 켬 재생 대 **B 기록**(B 세 시드 T=900 상태, 보고만): 미터 후보 이름 집합·후보 수·허용 집합·하한·cap 목표 수를 대조. 선언 차이 = §4 의 옮기지 않은 plant 부분 전부 + VSL 정책(B 110 고정) + 머리 표 g9(⟨Q4⟩) | (a) 선언 밖 차 0. (b) 미분류 0. (c) 보고만(우리 어댑터가 B 상태 파일을 못 읽으면 그 칸 "못 냄", 도구 고치지 않음 — X6 꼴) |

**커밋별**

| 커밋 | 관문 |
|---|---|
| C1-0 | `git diff --name-status c20aff1d..` ⊆ 하네스·c1 도구·시험, `git diff -- evaluation vendor plant scripts` 빈 결과, `py_compile`, 가드 자체 시험, G-K0(plant) |
| C1-1 | U, B(Ω), G-K0(전부), G-K1(Ω), G-K2(d), G-K3, G-K4(Ω), G-K5a |
| C1-2 | U, G-K0(전부), G-K1(M), G-K2(a)(b)(e), G-K3, G-K4(M), G-K5a, G-K5b(탐침 값) |
| C1-3 | U, B(H), G-K0(전부), G-K1(H), G-K2(c), G-K3, G-K4(H), G-K5a |
| C1-4 | G-K0(결정 일부·plant), G-K3, 팔 동일성(`sa_arms.py --c1`), `make_config --c1 --check` |

### 8.6 오프라인 재생 비교 R (이미 본 상태, 보고 + 미리 정한 멈춤)

- 까닭: M1 이 정책 토큰을 바꾸므로 V-A 기록 상태(T > 900)를 키 켬으로 한 번만 재생하면 `load_prices`(OU SD:527-528)에서 멈춥니다. B0 재생 R1–R3 이 같은 자리에서 멈췄습니다[읽음 B0 §6]. 그래서 두 꼴로 합니다.
  - **R-a 단일 결정**: T=900(첫 SDMPC 결정) 상태만. V-A v3c3-s31·s41·s43, R-obs v3c3-s31·s43. 팔 C1(키 끔 = 기록·G-K0).
  - **R-b 연쇄 재생**(K9-2 V-B 꼴, 영수증에 사슬 CSV 경로를 담음 [읽음 KB/LOG.md:946]): V-A v3c3-s31·s41·s43 의 900–2,700 s(결정 13개씩, 관측은 V-A 기록, 직전 명령은 사슬 출력). 팔 C1 만. 키 끔 기준 = V-A 기록(G-RR (a) 로 같음을 보인 뒤).
- 보고 표: 결정별 이웃 검사 후보·선택, 블록 0 미터 녹색(실행될 명령), 저장 보호 발동, cap 목표·NP, held 유지, Ω701·Ω635·OUTW 모형 값, **SC1001 SG2·SG5 계획 녹색(블록 0) 900–2,700 s 합**, 모형 링크 127·129·10491 저장고, 결정 벽시계.
- 표지: "이미 본 상태(V-A 기록), 독립 근거 아님". 판정에 쓰지 않습니다.
- 미리 정한 멈춤(⟨Q3⟩ (가)일 때): R-b 에서 어느 시드든 SC1001 SG2 계획 녹색 900–2,700 s 합이 V-A 기록보다 **100 s 넘게** 짧으면 멈추고 질문. 문턱 출처(데이터 뒤): B − V-A 실측 SG2 차 −172 / −229 / −168 s(VISSIM readback, INPUT1099:136)의 가장 작은 크기 168 s 의 약 0.6배.

### 8.7 J — K9-1·K9-2 판정 잎

- 키 끔에서는 G-K0 가 잎 같음을 봅니다.
- 키 켬에서는 목적이 Ω701 로 바뀌므로 잎이 다를 것으로 봅니다(설계상) [추론]. 그래서 ⟨Q12⟩ (가)는 J 를 보고·분류만(바뀐 값·크기, C0–C3, 첫 차이 스텝) 합니다. K9-2 판정 잎(SC109·링크 174)은 Ω701 이 SC109 접근 1·SC108 3 링크를 더한 길로 바뀔 수 있습니다 [실행 membership; 추론].

### 8.8 충실도 F (블라인드, NC 전용)

- 표본: R-obs v3c3-s47 T ∈ {1,050, 1,200, …, 8,400} 50상태(봉인 시드 아님). 표지 "부분 노출(다른 지표)"(K9-1·K9-2 판정에 쓴 상태). P0-7 노출 목록을 첫 줄로.
- 지표(plant 잡, 기록 native 동작)

| 지표 | 모형 | VISSIM (FZP) | 조건 |
|---|---|---|---|
| F-Ω 66링크 체류 (T, T+450] | Ω701 − Ω635 몫 모형 체류 | 같은 66링크 체류 | 보고만(⟨Q15⟩ (가); 절대 문턱 근거 없음) — 편향·MAE·지속 예측 대비 |
| F-S 링크 37·127·129·10491 저장고 | 모형 저장고 재고 T+150·T+450 | 링크별 차 수 | 보고만 |
| F-M 미터 머리 표 | — | — | **블라인드로 못 냄**: NC 는 미터가 늘 g10 이고, 머리 표 g10 은 바뀌지 않음(FW_E 4.2·10681 8.4 = 배분 표 g10 × 차로) [계산]. 비블라인드 대조는 READBACK K7(B 세 시드, "이미 본 자료" 표지) |

- 가드: 판정 단계 토큰 없이 C1 키를 켠 계산이 이 표본을 열면 자식 프로세스 전에 거부. 키 끔 계산도 판정 단계 전 0회.

### 8.9 STOP 규칙

- S-C1-1 보충 C1 고정 전에 P0·탐침·관문을 돌림, 또는 돌린 뒤 정의·값·문턱·표본을 바꿈 → 무효, STOP.
- S-C1-2 P0 대조·구조 점검 거짓 → STOP·질문.
- S-C1-3 탐침 멈춤 1·2 → 구현 전 보고·질문.
- S-C1-4 G-K0 동일 아님 → STOP.
- S-C1-5 G-K1 선언 밖 차이·작업자 불일치·C3 첫 차이가 C0 보다 앞섬 → STOP.
- S-C1-6 G-K2·G-K4 다름, G-K3 거짓, A_C1-M sha 조건 거짓 → STOP.
- **S-C1-7** 탐침 5상태와 R-b 39결정 모두에서 이웃 검사가 조임을 한 번도 고르지 않음 → 폐루프 전 멈추고 질문(선택지 예: Ω701 몫만 보는 폐루프로 감 / S1 본선 기구 묶음을 먼저 / D1 을 먼저).
- S-C1-8 G-K5a 1.0158 초과, G-K5b 1,500 s 초과 → STOP·질문.
- S-C1-9 R-b SG2 문턱(⟨Q3⟩) → 멈추고 질문.
- S-C1-10 블라인드 가드 위반 → 그 단계 무효, STOP.
- S-C1-11 봉인 시드(37·59·61·67) 열기, codex 64cf-s59/s61/s67 숫자 사용, 동결본·런 폴더 쓰기 → 중지·보고.
- S-C1-12 관문 결과를 본 뒤 판정기를 고쳐 결과가 바뀜 → 그 관문 STOP, 사용자.
- S-C1-13 사용자 결정 없이 폐루프 발사·동결·푸시 → 금지.
- S-C1-14 C:·D: 8 GB 밑 → 멈춤.

---

## 9. 폐루프에서 어떻게 비교하나 (`COMPARE_RULE_C1` 에 옮길 꼴; 숫자 없음)

### 9.1 런과 표

- 런: C1 팔(`config_n31_v2_c1.json`, 우리 러너·우리 동결본) v3c3-s31·s41·s43, 9,000 s. 짝: NC3(같은 시드), V-A(같은 시드, 같은 줄기), 참고 B(같은 시드, 다른 제어기 — codex 코드·64cf 계수·VSL 110 고정). 시드 3, 평균·신뢰구간 없음.
- 꼴 둘: 우리 꼴 [0, 9000] s, codex 꼴 [0, 8100] s(COMPARE_RULE_B §2 그대로).

| 줄 (veh·h; 시드 3, 시드마다 짝 하나) | C1 − NC3 (v3c3-s31 / s41 / s43) | C1 − V-A | 참고 C1 − B |
|---|---|---|---|
| Ω701 | | | |
| Ω635 | | | |
| Ω701 − Ω635 (66링크) | | | |
| ④a | | | |
| **④b (첫 관측 차분, 주 값)** | | | |
| **④ = ④a + ④b** | | | |
| **Ω 밖 (a) Ω701 기준 / Ω635 기준** | | | |
| Ω 밖 (b) Ω701 기준 | | | |
| ① FW_E 본선 7링크 / ② 동측 국소 19링크 | | | |
| **④b 중 입력 1099** / 1098 / 도시 입력 | | | |
| 링크 66 (SC1004 남측) | | | |
| 참고·선언 밖: FW_W 본선(26·120·10771), 링크 26 | | | |

- 사슬 줄(같은 표 아래, 세 짝 모두): SC1001 SG2·SG5 녹색 초 900–2,700·2,700–4,500 s(readback), 127→30 통과 수, 링크 127 0–50 m 차로 1·2 속도 1,800–2,700 s, 링크 129·10491 느린 체류 1,800–3,600 s, 링크 26 차로 1 끝(3,200–3,700 m) 대기 꼬리가 0 m 에 닿은 300 s 칸 수, 넣은 1099 차 2,700–4,500 s. 도구는 INPUT1099 의 고정 도구(`w1099_scan.py` 0ed864f2…, `w1099_scan2.py` e33c0807…, `w1099_sc_readback.py` c31227d7…)를 경로 상수만 바꾼 사본으로 씀(사본 sha 는 보충 C1 고정 때).
- 미터 줄: 결정별 미터 명령 분포(8미터 × 녹색), readback 대조 K3(주기 녹색 초 = 명령)·K7(녹색별 차로 방류) — READBACK 고정 도구(`rb_readback.py` cee5f262…, `rb_discharge.py` 4c385da9…, `rb_headcurve.py` 1466ff35…)를 같은 규칙으로. 링크 124·10483·10480, 링크 70·10639·10638·120 줄.
- 읽는 법 [추론]: Ω 줄은 ④·Ω 밖 줄과 함께만 인용합니다. Ω 가 줄고 Ω 밖 (a) 가 늘면 그 꼴을 그대로 적습니다(표시 규칙은 COMPARE_RULE_B 처럼 붙이지 않음, ⟨Q16⟩ 에서 고를 수 있음). C1 − V-A 는 "같은 줄기에서 C1 키만 다름", C1 − B 는 "다른 제어기" 로 따로 적습니다.

### 9.2 점검 (데이터 전 고정, COMPARE_RULE_B §5 꼴)

- X1 두 스캐너 차 ≤ 0.05 veh·h(보고). X3 고친 도구가 V-A·NC3 칸을 원본과 같게 냄(STOP). X5 시드마다 도착 수·입력 1099 도착 수(보고). **X6 도구가 C1 자료에서 쓰인 대로 못 돌면 그 칸만 "못 냄"**(D-K9-93 ① 칸 단위).
- X7 미터 실행: readback K3 어긋남 수, K1 요청 = 읽음 비율(보고). `RW_SIGNAL_READBACK_SEC` 는 쓰지 않음(⟨Q17⟩; OU VBS:4061 "for short audits").
- X8 결정: DECISIONS_OK/FAILED/HELD, 결정 벽시계 분포, `.err` 크기(보고; 유지가 있으면 T·예외 종류).

### 9.3 단서 (규칙에 그대로 적음)

- 900 s 전 FZP 접두: C1 − NC3 의 v3c3-s31·s41 은 † 일 것(B·V-A 와 같은 러너 접두) [추론, B_RESULTS §1.2]. 숫자는 그대로 두고 † 만 붙임(D-K9-93 ②).
- 런 사이 흔들림: 모름(같은 시드 반복 없음, D-K9-93 ⑤). 크기 참고만: A1 − joint(**다른 망 64cf, 한 시드 64cf-s29**) Ω701 −11.0 / ④ −28.9 / Ω 밖 (a) −17.9 veh·h [읽음 B_RESULTS:170-178]. 하위 줄에는 이 배수를 옮겨 쓰지 않음.
- 세 시드는 모두 우리 fit 시드입니다. 마지막 비교의 봉인 시드 사용은 따로 묻습니다.

---

## 10. 위험·한계

1. **미터가 여전히 g10 에 머물 수 있습니다** [추론]. 우리 plant 에서 조임은 Ω 를 늘리거나 그대로 두는 쪽이었고(METER_CAUSE a2·a2-5), 본선 합류·용량 기구(S1)와 D1 이 없습니다. 이웃 검사는 1e-7 보다 큰 모형 감소가 있어야 고릅니다. S-C1-7 이 이것을 폐루프 전에 잡습니다.
2. **Ω701 이 TSC 를 넓게 바꿉니다**. 접근로 대기를 줄이는 대신 Ω635 안이나 Ω 밖으로 대기를 옮길 수 있습니다. B − V-A 는 66링크 −246.1 / −286.6 / −271.8, Ω635 +329.7 / +184.9 / +359.1, Ω701 +83.6 / −101.8 / +87.3, ④ +549.1 / +275.6 / −94.3, Ω 밖 (a) +465.5 / +377.3 / −181.6 이었습니다(다른 제어기라 몫 아님) [읽음 B_RESULTS:65-71].
3. **SC1001 → 1099 사슬** [추론]. Ω701 이 SC1001 북쪽 링크를 목적에 넣으면 EBT 녹색이 줄 수 있고, 그러면 B 와 같은 사슬이 생길 수 있습니다. 목적은 ④b 를 보지 않습니다. 입구 처리량 한계가 증폭기입니다. §8.6·§9.1 이 봅니다.
4. **결정 시간**: cap 3 + 이웃 검사 + VSL 축(V-A 그대로) + cap 캐시 없음. 이 PC 에서 V-A 결정 평균 465–539 s 위에 얹힙니다. 런 하나가 61결정이라 결정당 +500 s 면 런 벽시계가 약 +8.5 h 입니다 [계산 61 × 500 s]. G-K5b 가 막습니다.
5. **정책 토큰·재생 기구**: 키 켬 단일 재생은 T=900 만 됩니다. 연쇄 재생(R-b)은 K9-2 V-B 에서 사슬 HARD 잎 문제로 일부 결정이 미완(VB_INCOMPLETE)이었던 기록이 있습니다 [읽음 KB/LOG.md:946].
6. **머리 표 g9**: ⟨Q4⟩ (가)면 C1 은 g9 를 고를 수 없고 B 는 g9 를 썼습니다(RM_C10490 240 / 0 / 165, RM_C10681 75 / 30 / 45 주기). C1 − B 의 미터 차에 섞입니다.
7. **FW_W 미터 표와 링크 124**: FW_W 녹색별 VISSIM 값은 10480 g2 3블록(v3c3-s41)뿐이고, 링크 124 공유 차로 기구는 옮기지 않습니다. B 에서 124 체류는 NC3 와 같았지만(3/3), 우리 plant 가 10480 조임을 어떻게 보는지는 모릅니다. codex 233/235(**다른 망 64cf, 한 시드**)는 이 자리에서 멈췄습니다.
8. **D1(1135 분할) 미수정**: 모형 10681 도착이 VISSIM 의 0.16배라 [읽음 K9_3_DESIGN_DRAFT:287] 이웃 검사의 10681 후보 값이 작게 나올 수 있습니다. K9-3 을 나중에 얹으면 미터 선택이 바뀔 수 있습니다.
9. **저장 보호 상태 이름**: 우리 버퍼 클래스가 codex 와 같은 이름을 갖지만(§3.5) 같은 뜻인지는 P0-5 전에는 모릅니다.
10. **Ω701 소속 해석**: 우리 plant 저장고가 Ω701 경계에 걸치면 `unresolved model membership` 로 멈출 수 있습니다(P0-3).
11. **B 는 다른 제어기**: B 의 미터 움직임·링크 66 감소를 C1 기구 몫으로 읽을 근거는 없습니다(64cf 계수·도시 기구가 함께 있음, COMPARE_RULE_B §4-10).
12. **데이터 뒤 선언**: 문턱 100 s(SG2)는 B 자료에서 뽑았습니다. 세 시드는 fit 시드이고, 블라인드는 NC 한 런(v3c3-s47)이며 미터 반응은 블라인드로 못 봅니다(§8.8 F-M).
13. **VSL 이 섞임**: C1 은 V-A 의 VSL 을 그대로 두고 B 는 110 고정입니다. C1 − B 의 ①·입력 1098 차에는 VSL 차가 섞입니다(B_RESULTS §2.1 과 같은 단서).

---

## 11. 비용 어림 [추론]

| 단계 | 어림 |
|---|---|
| P0 (Ω701 묶음 재생성·대조, 문서 8개 재결속, manifest, 구조 점검 1회, 머리 표 증거, 상태 이름, 토큰 표, 노출 목록) | 3–5 h |
| 미니 탐침 (T=900 5상태 × 5팔 + 보고 팔 2 × 결정 재생 약 15–35 분 + plant 잡 32) | 약 12–18 h |
| 구현 5커밋 + 관문(U·B·G-K0 결정 77·plant 42·G-K1–G-K5a) | 약 12–18 h |
| R-a (5상태, 탐침 C1 팔 재사용 가능) + G-RR (c) B T=900 3상태 | 약 1–2 h |
| R-b 연쇄 재생 (3시드 × 13결정 × 약 20–35 분, 한 번에 하나) | 약 13–23 h |
| J (보고·분류) | 약 8–12 h |
| F (R-obs v3c3-s47 50상태 plant 잡 OFF 하나 + FZP 대조) | 약 3–5 h |
| 독립 검증 | 3–4 h |
| 합 | **약 55–85 h 계산**(무거운 일 한 번에 하나, 약 5–8일) |
| 폐루프 C1 3런 (동시, 자리 날 때) | 런당 약 10 h(결정 평균이 V-A 와 비슷할 때; B 34,369–35,143 s, V-A 32,562–37,583 s) ~ 약 24 h(결정 평균이 2배일 때) [읽음 B_RESULTS:48-50, VA_REPORT:624; 2배 경우는 계산 61 × 1,000 s + 모의] |
| 폐루프 분석 | 1–2일 |
| 디스크 | 런당 약 6.5–7.6 GB(V-A v3c3-s31 6.5 GB, B v3c3-s31 7.6 GB [실행 du]) → 3런 약 20–23 GB, D: 에만. 지금 C: 27 GB, D: 223 GB [실행] |

---

## 12. 사용자 결정 ⟨Q⟩ (각 줄의 **권장**을 굵게)

| ⟨Q⟩ | 질문 | 선택지 | 까닭 (짧게) |
|---|---|---|---|
| ⟨Q1⟩ | 묶음 범위·몫 가르기 | **(가) M0–M5 + M4a·M4b 한 묶음, 키는 기구별(탐침 팔로 몫), 폐루프는 묶음 팔 하나(3런)** / (나) 폐루프도 둘로(C1a 미터만, C1b Ω701 만; 6런) / (다) Ω701 만 먼저 | 이웃 검사만 켠 codex 런이 멈춘 기록(다른 망 64cf, 한 시드 64cf-s29) 때문에 M1 은 M3·M4 와 함께. 몫은 오프라인 팔로 봄. 새 VISSIM 최소화 |
| ⟨Q2⟩ | FW_W 입구·엮임 보호 장치 | **(가) 넣지 않음. SG2 오프라인 대조(§8.6) + 폐루프 사슬 줄(§9.1)** / (나) 링크 129·10491 저장 한계 보호(D5 꼴)를 C1 에 더함 / (다) 1099 밀린 줄(④b)을 목적에 넣음 | 1099 항은 미터가 아니라 SC1001 SG2 사슬을 따라 왔고(v3c3-s31·s41), 미터 기구는 3/3 반박. C1 에서 TSC 를 건드리는 것은 Ω701 하나 |
| ⟨Q3⟩ | R-b SG2 멈춤 문턱 | **(가) 키 켬 연쇄 재생의 SC1001 SG2 계획 녹색(900–2,700 s 합)이 V-A 기록보다 100 s 넘게 짧은 시드가 있으면 멈추고 질문(데이터 뒤 문턱: B − V-A 168–229 s 의 약 0.6배)** / (나) 보고만 / (다) 다른 값을 지금 정함 | 폐루프 전에 B 꼴 사슬의 앞머리를 모형 안에서 봄 |
| ⟨Q4⟩ | 머리 표 g9 = g10 처리 | **(가) FW_E 4미터 표에서 g9 를 빼고 g10 을 남김(K3 정규화에 "최대 서비스 묶음은 g10 을 남김" 한 규칙 더함; 지금 설치된 표에는 해당 행이 없어 키 끔 불변)** / (나) codex 그대로 g9 = g10, 이 네 미터에서 K3 를 끄고 codex `np_only` 길(CX SD:934·952, PRB:947-953)도 옮김 / (다) g9 = 4.1 보간(실측 없음) | K3 는 같은 서비스 녹색 때문에 역산이 거부되어 결정이 멈춘 일(코드 주석 그대로 'hybrid s31 3000 s')을 막으려 넣은 것(OU PRB:38-45). g9 VISSIM 실측 없음(READBACK §7). (가)는 B 와 g9 사용이 다름(위험 6) |
| ⟨Q5⟩ | FW_W 미터 4개 표 | **(가) 배분 표 그대로(codex 와 같음), 10480 g2 3블록은 보고** / (나) FW_W 에도 머리 꼴(녹색 1초당 0.5 대/차로) / (다) FW_W 미터를 이웃 검사에서 빼고 늘 g10 | FW_W 녹색별 값이 거의 없음. codex 도 배분 표 |
| ⟨Q6⟩ | 링크 124 공유 차로(10480·10483) | **(가) 옮기지 않음, 124·10483·10480 줄을 폐루프 표에 둠** / (나) codex 기구(RCC:1929-1975, LOR:659·722) 이식(바탕 `direct_exit_legsplit` 이 우리 줄기에 없어 범위가 커짐) / (다) RM_C10480 을 늘 g10 으로 묶음 | v3c3 B 에서 124 체류 = NC3(3/3), 10480 기구 반박(3/3). 위험 7 로 남김 |
| ⟨Q7⟩ | 운영 seed·held 유지(M4a·M4b) | **(가) 저장 보호와 함께 옮김, held 유지는 키 따로(탐침에서 몫)** / (나) 운영 seed 투영만, held 재채점 없음 | codex 는 운영 seed 와 held 재채점을 한 몸으로 둠(CX SD:1222-1223 주석). B 도 그렇게 돌았음 |
| ⟨Q8⟩ | C1 의 VSL | **(가) V-A 그대로(우리 VSL 축·법칙·표지 18·집합 80–110, secant 없음). 이웃 검사는 VSL 을 고정** / (나) VSL 110 고정(codex `sdmpc_fixed_vsl` 이식 필요 → VSL 부분이라 범위 밖) | D-K9-92. C1 − V-A 를 같은 VSL 정책 짝으로 둠 |
| ⟨Q9⟩ | 결정 시간이 G-K5b 를 넘을 때 | **(가) C1 에 속도 기구 안 넣음. 넘으면 멈추고 질문(선택지: cap 캐시 이식·cap 2·예산 재선언)** / (나) 지금 `sdmpc_response_cap_cache` 를 비트 같음 관문과 함께 옮김 | C1 은 기구 몫을 보는 묶음. B 는 cap 캐시를 썼음(CFG_B 차이 넷 중 하나) |
| ⟨Q10⟩ | 증거 키 꼴 | **(가) 이름 + sha 만(코드 상수 폴더, 새 로더; Ω701 은 묶음 목록 하나로 11파일)** / (나) 기존 경로 키 값을 바꿈(경로 문자열) | 과제 규칙·K9-3 ⟨Q7⟩ (가)와 같음 |
| ⟨Q11⟩ | 키 묶기 | **(가) 런타임은 하위 키 단독 허용(탐침·몫), 배포·폐루프는 전부 함께(`make_config --c1`). 단 M1 은 M3·M4 없이 켜면 ValueError** / (나) 런타임에서 전부 묶음 | 몫 가르기와 안전 장치 함께 두기를 둘 다 지킴 |
| ⟨Q12⟩ | J (K9-1·K9-2 판정 잎) | **(가) 키 끔 같음은 G-K0 로, 키 켬 J 는 보고·C0–C3 분류만** / (나) 키 켬에서 다르면 STOP·질문(K9-3 ⟨Q9⟩ (가) 꼴) / (다) J 생략 | Ω701 은 목적 자체를 바꾸므로 키 켬 잎 차이는 설계상 생김 |
| ⟨Q13⟩ | 오프라인 재생 범위 | **(가) R-a T=900 5상태 + R-b V-A 세 시드 900–2,700 s 연쇄(키 켬만)** / (나) R-b 를 900–4,500 s 로 / (다) R-a 만 | 1099 사슬이 1,800–2,700 s 에 시작(INPUT1099 §3.8). 연쇄가 길수록 비용이 큼 |
| ⟨Q14⟩ | B 기록과의 대조(G-RR (c)) | **(가) B 세 시드 T=900 상태에서 C1 키 켬 재생, 미터 후보 이름·수·허용 집합·하한·cap 목표 수만 대조(보고, 못 읽으면 "못 냄")** / (나) 안 함 | 옮긴 기구가 codex 와 같은 꼴로 도는지 한 번 봄. 숫자 같음은 기대하지 않음(plant 다름) |
| ⟨Q15⟩ | 충실도 F 문턱 | **(가) F-Ω·F-S 보고만(절대 문턱 근거 없음), 폐루프 질문 때 함께 보임** / (나) 문턱을 지금 정함(데이터 전) | Ω701 은 plant 궤적을 바꾸지 않아 키 끔 대 키 켬 비교가 뜻이 없음 |
| ⟨Q16⟩ | 폐루프 | **(가) 관문·R 뒤 3시드 동시(자리 날 때, D-K9-90 꼴), 짝 NC3·V-A, 참고 B, 발사 전 다시 물음; "대기 이전" 같은 표시 규칙은 붙이지 않음** / (나) 한 시드 먼저 / (다) 관문까지만 하고 다음 묶음 설계로 | 새 VISSIM 최소화. 세 시드는 원인 분석용 fit 시드 |
| ⟨Q17⟩ | 폐루프 미터 실행 대조 | **(가) readback + FZP 헤드 통과(READBACK 고정 도구·규칙), `RW_SIGNAL_READBACK_SEC` 안 씀** / (나) 매초 readback 켬 | VBS 가 매초 모드를 "짧은 감사용" 으로 적음(OU VBS:4061). 러너 동작을 V-A 와 같게 둠 |
| ⟨Q18⟩ | 문턱 숫자 | **(가) G-K5a 1.0158, G-K5b 1,500 s, SG2 100 s, 탐침 멈춤 1–4 를 지금 고정** / (나) 다른 값을 지금 정함(데이터 전) | 결과 뒤 문턱 변경을 막음 |
| ⟨Q19⟩ | K9-3 순서 | **(가) C1 먼저(D-K9-91), K9-3 보류 유지. 설치 자리를 겹치지 않게 두고, K9-3 재개 때 C1 켬 상태에서 J 를 다시 셈** / (나) K9-3 먼저, C1 을 그 위에 / (다) 한 묶음으로 | D-K9-91 그대로. 위험 8 을 단서로 둠 |

---

## 13. 이 문서를 쓰며 한 일·하지 않은 일·파일

- 한 일 [실행, 모두 읽기 전용]
  - 입력 문서 읽기와 sha256(근거 표).
  - `git -C GWT8 show c20aff1d:` 로 SD·PRB·LPR·RS·CAO·SEQ·`lane_ramp_runtime.py`·OUC 를 `CP/c1d/ou_*` 에 읽기 사본으로 둠, `git grep`(`lane_ramp_runtime`, `control_area_membership_213a5d`, `direct_exit_legsplit`, `RW_SIGNAL_READBACK_SEC`, `max_leader_candidates`). GWT8 쓰기·체크아웃 0.
  - CX·FRZ_B1 코드·설정 읽기, sha 대조(SD·PRB·LPR·USG 두 트리 같음, CAO 는 B0 F2 로 다름), `diff --strip-trailing-cr` 우리/codex SD → `CP/c1d/diff_sdmpc.txt`(387줄).
  - 설정·증거 파일(CFG_B, Ω701 membership, `B0_REPIN_RECEIPT.json`, OUC)을 python 한 줄로 읽어 키·링크 집합만 셈. 런 결과 자료가 아니라 설정·증거 파일이라 규칙 고정 없이 셈 — LOG 06:17 항목에 밝힘.
  - `du -sh` B·V-A v3c3-s31 런 폴더(읽기만), `df`, 프로세스 확인(VISSIM·python 0, 06:16 KST).
- 하지 않은 일: 코드 변경 0, 커밋·푸시 0, 동결 0, 재생 0, plant 잡 0, VISSIM·COM·러너 0, 시험 0, FZP·결정 JSON·readback 새 분석 0, 동결본·런 폴더·GWT8·인계 사본·Y: 쓰기 0, kill 0, 봉인 시드 자료·sealed/ 0, codex 64cf-s59/s61/s67 숫자 0, 금지 시험 7종 0. COMPARE_RULE_B·PINS_B 바꾸지 않음.
- 파일: 이 문서 `CP/C1_DESIGN_DRAFT.md`(sha256 은 `CP/C1_DESIGN_DRAFT.md.sha256` 과 `CP/LOG.md` 마감 항목), 읽기 사본 `CP/c1d/`.

## 변경 기록

- r0 (2026-10-27 KST): 첫 초안.
