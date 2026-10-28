# PRE_FWE — FW_E 개선 분해 사전 고정 (D-K9-106, 2026-10-27 KST, r1)

- 무엇: 사용자 결정 D-K9-106 "FW_E 개선 분해를 지금 오프라인으로" 의 **데이터 전 고정 문서**입니다. 질문 R1–R4, 지표 정의, 도구 핀, 순서, 멈춤 규칙, 종합 출력의 꼴을 여기서 정합니다. 이 문서를 쓴 뒤에만 새 숫자를 셉니다.
- 이 단계에서 한 일: 문서·캐시 머리 읽기, 작은 파일 sha256, 목록 만들기(도구 `fwe_inventory.py`). **FZP 를 한 번도 열지 않았습니다.** VISSIM·COM·러너·동결·결정 재생·코드 변경·커밋·푸시 0. kill 0. 남의 잠금·프로세스는 건드리지 않았습니다. 주의 한 건: `SP/rmcause/INV_PHYSICS.md` 를 grep 으로 찾을 때 출력 줄에 v3c3-s47·s53 무제어 값이 섞여 보였습니다. 그 값은 어디에도 옮기거나 쓰지 않았고, 앞으로 그 문서는 s31/s41/s43·64cf-s29 줄(64-66·91-93·96·139)만 줄 번호로 읽습니다(LOG 16:2x).
- 규칙: 시드는 망 이름을 붙입니다(v3c3-s31, 64cf-s29). 같은 시드 짝만 뺍니다. 시드끼리 평균 내지 않습니다. 64cf 와 v3c3 는 서로 빼지 않고 나란히만 둡니다. 판정 낱말을 쓰지 않습니다. Ω701 을 적을 때는 늘 ④ 와 Ω 밖을 같이 적습니다.
- 표시: **[실행]** 명령·도구로 확인 · **[읽음]** 파일을 읽어 확인 · **[추론]** 시험하지 않은 판단 · **[계산]** 이 문서의 산술. 줄 인용은 "파일:줄".
- 경로 줄임: SP = `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8`, FD = `SP/fwe_decomp`, CH = `SP/codex_handoff`, CW = `CH/work`, H = `D:/VISSIM_handoff/20261024`(codex 인계 사본, `sealed/` 제외), NT = `SP/K9_1_J1_NOTES_20261013.md`.

---

## 0. 쉬운 요약

1. 목적 영역은 **Ω701** 하나입니다. 도시도로는 **codex 분할** 하나만 씁니다. **FW_W 는 개선 대상이 아니라 감시만** 합니다. **FW_E 가 주 개선 대상**입니다 [읽음 NT:346-349, D-K9-104].
2. 묻는 것은 넷입니다. R1 무제어 FW_E 가 얼마나 막히나. R2 제어 팔의 ①·② 차가 어느 링크·어느 시간·어느 구역에서 나오나. R3 미터가 언제 조였고, 램프 합류·램프 재고·입구 대기가 어떻게 바뀌었나. R4 codex 분할 팔(64cf-s29)에서 기구별로 ①·②·도시도로·Ω701·④·Ω 밖이 어떻게 갈리나.
3. 결과로 두 가지를 냅니다. (가) 기구 후보 표(꼬리표 붙음). (나) **C1 FW_E 기준 줄** = C1 이 FW_E 를 움직이는지 볼 때 나란히 놓을 보고 칸(판정 문턱 없음).
4. 자료는 기존 런·캐시가 먼저입니다. 새 FZP 스캔은 없는 숫자에만, 공용 잠금 아래 하나씩 합니다(§9). 꼭 필요한 새 스캔은 B 세 런의 FW_E 물리 스캔, codex urban_only·freeway_only 의 빠진 스캔, 링크×시간 칸이 없는 팔의 링크 스캔입니다.

---

## 1. 사용자 지시와 범위 [읽음]

- 사용자 말(이 워크플로를 띄운 요청, 요지): "Ω701 은 보호망에 바깥에서 안으로 들어오는 접근로를 더한 것이고, 701 이 목적 영역이 맞다. FW_W 는 거의 제어도 안 되고 개선도 안 된다. 개선의 대부분은 FW_E 이고 FW_E 가 안 움직이는 게 더 문제다. 도시도로 정의는 codex 판을 따른다."
- 결정 기록: D-K9-104(NT:346-349), D-K9-106(NT:354). 이 문서의 범위는 그 둘입니다.
- Ω701 의 실제 구성 [읽음 `CH/R_NET.md:147`]: Ω701 = Ω635 + 66링크. 더한 까닭은 접근로 영역 39, 제어 신호등 링크 13, 포함 링크 사이 직결 커넥터 31 입니다(겹침 있음). 그래서 사용자 말 "바깥→안 접근로를 더함" 이 큰 몫이고, 신호등 자체 링크와 짧은 연결 커넥터도 함께 들어 있습니다. v3c3 Ω701 = codex Ω701(같은 701 집합)입니다 [읽음 같은 곳].
- 정의 파일: Ω701 = `H/derived/omega_membership_exact.json` `/inside_links`(sha256 `efdfaeb1…`), 도시도로 = codex 분할(`H/derived/reporting_partition.json` `3142f69c…`, 규칙 `H/analysis/original_scripts/solo355_compare_20261014.py:49-61` `7fc91d60…`) [읽음 `CH/OMEGA701_V3C3.md:16`, sha 는 [실행] `FD/out/pins_existing.json`].
- FW_W 다루기: FW_W 미터(RM_C10480·10482·10646·10644)·입력 1099 대기·FW_W 본선(26·10771·120)은 **감시 칸**에만 둡니다. 기구 후보 표와 C1 기준 줄의 주 칸에 넣지 않습니다.

## 2. 줄임말 (처음 한 번)

- FW_E = 동측 고속도로, FW_W = 서측 고속도로. TTT = 총 통행시간(veh·h). NC = 무제어 런. RM = 램프 미터. TSC = 도시 신호 제어. VSL = 가변 제한속도. SDMPC = 분산 모형예측제어기. plant = 제어기 안의 예측 모형.
- FZP = VISSIM 차량 궤적 기록(5 s 프레임). LDP = VISSIM 신호 상태 초별 기록. readback = 러너가 신호 상태를 쓴 뒤 VISSIM 에서 다시 읽은 기록(`signal_readback.csv`).
- ① = FW_E 본선 7링크 74·10699·2·10613·119·10702·24. ② = 동측 국소 19링크 = ① + 진입 커넥터 10639·10681·10490·10484 + 진출 커넥터 10643·10682·10481·10483 + 진입 접근 링크 70·68·129·31 [읽음 `SP/HANDOFF_codex_a49981ff.md:244`, codex `check_fzp.py:4-5`].
- 미터와 합류 짝 [읽음 `SP/rmcause/phys/fwe_scan.py:24-27`]: RM_C10639 ← 링크 70, 합류 체인 4,698.7 m · RM_C10681 ← 68, 5,041.9 m · RM_C10490 ← 129, 7,243.1 m · RM_C10484 ← 31, 7,603.7 m. 진출: 10643(4,386.3 m, 신호 배수) · 10682(4,746.9 m) · 10481(6,826.8 m, 신호 배수) · 10483(7,240.3 m).
- 체인 = FW_E 본선 거리(링크 74 시작 0 m, 끝 10,784.0 m). 4차로는 6,841.7 m 까지, 그 하류 3차로 [읽음 fwe_scan.py:19-22, tails.py:21-22].
- Ω635 = 우리 옛 목적 영역(Ω701 의 부분집합). ④a = 망 전체 링크 체류. ④b = 미삽입 대기(입력에서 생겼지만 망에 못 들어간 차의 대기). ④ = ④a + ④b. Ω 밖 (a) = ④ − Ω701, Ω 밖 (b) = ④a − Ω701. 입력 1098 = FW_E 입구(첫 관측 링크 74), 1099 = FW_W 입구(링크 26).
- 첫 관측 차분 = 같은 시드 두 런의 ④b 차를 "차가 FZP 에 처음 보인 시각" 으로 내는 방법(D-K9-87 주 값) [읽음 `CW/vhr/vhr_unins.py:1-4`].
- 팔: NC3 = v3c3 무제어 세 런. V-A = 우리 묶음 B1 폐루프. B = codex 판을 v3c3 로 옮긴 폐루프(VSL 110 고정). VSL = v3c3 고정 VSL 91 단독(미터 열림, 도시 native). J1 = K8 동결본 폐루프(참고). 64cf 쪽: codex NC·joint·window·off·freeway_only·urban_only(인계 원자료 사본), A1 = codex 코드로 이 PC 에서 다시 돈 joint, LNC = 이 PC 의 64cf-s29 무제어, vsl_repro vsl = 64cf-s29 고정 VSL 90 단독, historical = 옛 ALINEA·VSL90 팔.
- 구역(fwe_analyze 다섯, 주): U 0–4,200 · B1 4,200–5,300 · M 5,300–6,800 · B2 6,800–7,900 · D 7,900–10,800 m [읽음 `SP/rmcause/phys/fwe_analyze.py:7-13`]. 구역(vsl_metrics 일곱, 보조): U · B1 · M1 5,300–6,300 · Mu 6,300–6,700 · VS0 6,700–6,800 · B2 6,800–8,100 · D 8,100–10,800 m [읽음 `SP/vsl_v3c3/tools/vsl_metrics.py:56`]. 셀 = plant 31셀(경계 32개, `vsl_cell_scan.py` 출력 `cell_bounds_m`) [실행 `SP/vsl_v3c3/out/cell/nc3_s31.json`].
- 창 = 300 s 칸(0–300, …, 8,700–9,000 s). 보고 표는 900 s 칸으로 묶고, JSON 은 300 s 그대로 둡니다. 0–900 s 는 제어 전(워밍업)입니다.

---

## 3. 팔·자료 목록 (Declare 1) [실행 `FD/tools/fwe_inventory.py`]

- 전체 표(팔 28줄 × 런 파일·캐시 133개·sha256 전부): **`FD/out/INVENTORY.md`**, 원본 `FD/out/inventory.json`. sha 는 §13.
- 시드는 폴더 이름이 아니라 provenance `/seed` 에서 읽었습니다. 28줄 모두 기대 시드와 같았습니다(v3c3 31/41/43, 64cf 29) [실행].
- FZP sha256 은 FZP 를 다시 읽지 않고 기존 캐시가 적은 값을 경로로 맞춰 옮겼습니다. 캐시가 둘 이상인 FZP 는 모두 값이 같았습니다(불일치 0) [실행]. 새 스캔은 읽으면서 sha 를 다시 내고 이 값과 맞춥니다(멈춤 S-1).

### 3.1 팔 요약

| 묶음 | 팔 · 시드 | FZP sha256 앞 16 (캐시) | 결정·readback | 미터 LDP |
|---|---|---|---|---|
| v3c3 | NC3 s31 / s41 / s43 | `f8476f83e2c70821` / `f63f00807b27d692` / `048823b966f60a66` | 결정 없음 | 0 |
| v3c3 | V-A s31 / s41 / s43 | `d3a440aff8db8ee5` / `eeea360784a1a914` / `a38437a45019fee5` | action CSV 61 · signal_readback | 0 |
| v3c3 | B s31 / s41 / s43 | `5932e6e195bae4ee` / `8ac58a253c6a5d87` / `2f7011a33ef6d500` | action CSV 61 · signal_readback | 0 |
| v3c3 | VSL s31 / s41 / s43 | `63a827fe47606bee` / `ea91826e675e899b` / `5492358d78386b8b` | 고정 VSL readback | 8 |
| v3c3 (참고) | J1 s31(재실행) / s41 / s43 | `80c03a8d993b6a79` / `7785ab17a4b5eec9` / `1d1b20e42732d1d7` | action CSV 61 · signal_readback | 0 |
| 64cf-s29 | codex NC | `1eaad57ff4029634` | 없음 | 8 |
| 64cf-s29 | codex joint / window / off | `c0aa41bbdfc1cee4` / `ce2742b7f6934dda` / `73a20cbb813152f0` | action CSV 55 · signal_readback | 8 |
| 64cf-s29 | codex freeway_only / urban_only | `05b45b03ed323ad6` / `a8a4b4e2a681be36` | action CSV 55 · signal_readback | 8 |
| 64cf-s29 | A1 / LNC / vsl_repro vsl | `9bf7c8c6f56099fb` / `9c097cc7e1f2840a` / `c874323fef14500d` | A1 만 결정 55 | 8 |
| 64cf-s29 (선택) | historical ALINEA rm / both, historical VSL none / bottleneck90 | 캐시 없음(새 스캔 때 셈) | 없음 | 8 |

- [실행] 망: NC3 s31, V-A ×3, B ×3, J1 ×3 (10런)의 inpx 는 `3de889f0…`. NC3 s41·s43 은 randSeed 한 줄만 다른 `726af589…`·`51478c39…`(OMEGA701_V3C3.md:69). VSL 세 런의 prepared inpx 는 시드마다 다른 sha(`04630354…`·`e4953eaf…`·`94318d4d…`)이고, 차이는 기록 전용 줄과 VSL 쓰기라고 검증 문서가 적었습니다 [읽음 `SP/vsl_v3c3/VSL_RESULTS.md:13`]. 64cf 팔은 `64cf5f55…`.
- [읽음] codex NC 와 LNC 는 다른 파일(4 bytes 차)이지만 같은 시뮬레이션입니다(9000 s 6,950,156행 모두 같음, `CH/HANDOFF_RESULTS.md:154`; 링크별 차 0, `CH/a1/A1_RESULT.md:249`). 이 문서는 64cf NC 로 codex NC(링크 적분·첫 관측)와 LNC(물리 스캔·링크 칸)를 함께 씁니다. 둘이 같은지 R4 에서 다시 대조합니다(멈춤 S-5).
- [실행] historical VSL none 은 LNC 보다 15 bytes, bottleneck90 은 vsl_repro vsl 보다 33 bytes 큽니다. 같은 시뮬레이션인지 모릅니다(선택 스캔 H13 에서 LF 해시로 대조).
- 범위 밖으로 둔 것: `H/raw/historical_vsl_s43`(64cf-s43, 이 질문의 시드 아님), `sealed/`(열지 않음).

### 3.2 링크·시간 재고를 이미 가진 캐시 [실행 INVENTORY §2]

| 캐시 종류 (도구) | 담은 것 | 가진 팔 | 없는 팔 |
|---|---|---|---|
| omega npz (`omega701_recount.py` `5b7826f6…`, B 는 `omega_b/omega701_recount_b.py` `3d5160da…`) | **링크 × 5 s 프레임 대수**(M = 프레임 × 그 런에 나온 링크), 차량별 첫 관측 | NC3 ×3, V-A ×3, B ×3(`CW/omega_b/cache/j1_s*.npz`, j1 자리 = B), J1 ×3, LNC | VSL ×3, codex 팔 전부, A1, historical |
| linkbin (`rmcause/o1o4/work/linkbin_scan.py` `a22d5fa6…`) | 링크 × 150 s 재고·대기(속도<15)·삽입·최대 대기 | LNC, vsl_repro vsl (`rmcause/o1o4/scan/lb_*.json`) | 나머지 전부 |
| fwe_scan (`rmcause/phys/fwe_scan.py` `0619e9fc…`) | FW_E 체인 100 m × 60 s 대수·속도, 차로 칸(3,800–8,000 m), 검지선 통과, 램프 합류·진입·연결로/접근 링크 재고·대기, 진출 재고, 링크 74 삽입 | NC3 ×3, V-A ×3, J1 ×3, VSL ×3, LNC, vsl_repro vsl, codex joint·window·off·freeway_only, A1 | **B ×3, codex urban_only**, historical |
| vhr 링크 적분 (`CW/vhr/vhr_scan.py` `a19942b8…`, B 는 `vhr_b/vhr_scan_b.py` `0c445bc4…`) | 링크별 적분 네 꼴(우리·codex × 0–8100·0–9000) | NC3·V-A·B·J1·VSL ×3, codex NC·joint·window·off·freeway_only·urban_only, LNC. A1 은 `a1/full/scan/a1.json`(0–8100 링크 체류 한 꼴) | **vsl_repro vsl**(bin 꼴 `lb_vsl_s29.json` 만), historical |
| 첫 관측 (`CW/vhr/vhr_firstseen.py` `42e17585…`, B 는 `vhr_firstseen_b.py` `d5c3c126…`, A1·LNC 는 `vhr_firstseen_a1.py` `c66f95e2…`) | 첫 링크(74/26/그 밖)별 프레임마다 새로 보인 차 수 | NC3·V-A·B·J1·VSL ×3, codex NC·joint·window·off, A1, LNC, vsl_repro vsl | **codex freeway_only·urban_only**, historical |
| readback 주기 (`c_port/readback/tools/rb_readback.py` `cee5f262…`) | 미터별 10 s 주기 명령·읽은 GREEN 초 | B ×3, V-A ×3 (`c_port/readback/out/cycles_*.csv`) | 64cf 팔(LDP 로 대신) |
| vsl_cell (`vsl_cell_scan.py` `fa5aeafd…`) | 셀·차로 60 s(체인 6,000–8,600 m) | NC3 ×3, VSL ×3 | 나머지 |
| o4_merge, w1099, rb_meter_scan | 10681 합류·연결로(V-A·J1), FW_W 입구(감시), 미터 헤드 통과(B·V-A) | 표 INVENTORY §2 | — |

- [실행] 경로가 이 목록의 런과 맞지 않은 캐시는 `rmcause/o1o4/scan/w264_s29.json`·`lb_w264_s29.json`(codex window264 9000 s 회복 런, 이 질문 밖) 둘입니다.
- [읽음] `SP/rmcause/phys/out_all.json` 은 v3c3-s47·s53 무제어 값이 같은 파일에 있어 **읽지 않습니다**. R1 은 런별 스캔 파일에서 다시 셉니다.

---

## 4. 이미 아는 숫자 (데이터 전 바탕, 새로 세지 않음)

### 4.1 v3c3 같은 시드 짝 (우리 꼴 [0, 9000] s, veh·h, s31 / s41 / s43)

| 짝 | Ω701 | ④ | Ω 밖 (a) | ① | ② | ④b 1098 | 출처 |
|---|---|---|---|---|---|---|---|
| V-A − NC3 | −240.6 / −421.7 / −309.5 | −373.9 / −506.2 / −356.4 | −133.3 / −84.5 / −46.9 | −12.3 / −72.6 / −5.3 | −51.5 / −187.1 / −92.5 | +214.1 / −0.9 / +63.8 | [읽음 `CH/B_RESULTS.md:65-79`] |
| B − NC3 | −157.0 / −523.4 / −222.2 | +175.1 / −230.6 / −450.6 | +332.1 / +292.9 / −228.4 | −37.3 / −178.1 / −88.9 | +28.2 / −245.2 / −34.7 | −25.5 / −19.3 / −113.5 | [읽음 같은 곳] |
| VSL − NC3 | +70.3 / −162.0 / −50.5 | +10.6 / +68.6 / −109.9 | −59.8 / +230.6 / −59.4 | +36.1 / −126.1 / −8.0 | +67.8 / −184.0 / −45.3 | −2.3 / +89.0 / −121.9 | [읽음 `SP/vsl_v3c3/VSL_RESULTS.md:63-72`] |

- codex 꼴 [0, 8100] 의 ①: V-A − NC3 −21.5 / −66.7 / −6.9, B − NC3 −37.0 / −172.5 / −89.6 [읽음 `CH/HANDOFF_RESULTS.md:86`, `CH/B_RESULTS.md:98`].
- ①·1098 차에는 VSL 정책 차가 섞입니다: V-A 는 FW_E VSL 101 을 55결정 중 9 / 10 / 14번 썼고, B 는 110 고정입니다 [읽음 `SP/vsl_v3c3/VSL_RESULTS.md:197-199`].

### 4.2 64cf-s29 (한 시드, codex 꼴 [0, 8100], v3c3 와 빼지 않음)

| 짝 | Ω701 | ④ | Ω 밖 (a) | ① | ② | ④b 1098 | 출처 |
|---|---|---|---|---|---|---|---|
| codex joint − NC | −494.7 | −670.3 | −175.6 | −283.7 | −156.6 | +97.0 | [읽음 `CH/HANDOFF_RESULTS.md:77-89`] |
| A1 − LNC | −505.7 | −699.2 | −193.5 | −251.1 | −181.8 | +94.8 | [읽음 `CH/a1/A1_RESULT.md:33-34`] |

- codex 분할 팔의 ①·② [계산 ← 읽음 `SP/HANDOFF_codex_a49981ff.md:226-233` 수준값]: window − NC ① −264.6 · ② −94.2; off − NC ① −301.5 · ② −147.6; freeway_only − NC ① −351.8 · ② −130.1; urban_only − NC ① +721.4 · ② +733.7. 이 팔들의 Ω701·④·Ω 밖은 아직 ④ 가 없어 여기 적지 않습니다(R4 에서 함께 냄).
- 팔의 뜻 [읽음 같은 문서 :215-218, :223]: window = RM+TSC, seg13 시간창 VSL. off = RM+TSC, VSL 110 고정. freeway_only = VSL+RM, 자기 정보·고속도로 목적, 도시 native(100/90 VSL 도 골랐으므로 순수 RM 단독 아님). urban_only = TSC 만, VSL 110·미터 열림.

### 4.3 무제어 FW_E 의 막힘 크기 (이미 잰 것)

- B1 번짐 분(B1 꼬리 < 4,500 m): NC3 0 / 0 / 2, 64cf-s29 NC 62. M 번짐 분(B2 꼬리 < 6,800 m): NC3 0 / 12 / 3, 64cf-s29 NC 19 [읽음 `SP/rmcause/INV_PHYSICS.md:91-93, 96`; 정의 `rmcause/o1o4/work/tails.py:4-12`].
- [읽음 INV_PHYSICS.md:139] v3c3-s41 의 V-A ① −72.6 은 미터·VSL 이 아니라 10643 진출 대기 역류가 줄어서라고 적혀 있습니다(10643 은 도시 신호로 배수되는 진출). [읽음 `SP/rmcause/o1o4/O4_MERGE_10681.md` §0-9] 10681 은 늘 초록인데도 대기열이 서 있고, 합류의 77–84 % 가 연결로 차로 2 에서 나옵니다.
- [추론] 그래서 v3c3 에서 FW_E 가 잘 안 움직이는 까닭 후보는 "무제어가 거의 붕괴하지 않아 미터가 막을 번짐이 작다" 와 "보이는 ① 차의 일부가 진출 역류(도시 신호) 몫" 입니다. R1·R2·R3 는 이 두 후보를 숫자로 가르려는 것입니다. 이것은 가설이고 결론이 아닙니다.

---

## 5. 질문과 지표 (Declare 2)

### 5.0 짝 (모두 같은 시드)

| 이름 | 짝 | 시드 | 쓰는 곳 |
|---|---|---|---|
| P-VA | V-A − NC3 | v3c3-s31/s41/s43 | R2·R3·종합·C1 기준 줄 |
| P-B | B − NC3 | 같음 | R2·R3·종합·C1 기준 줄 |
| P-VSL | VSL − NC3 | 같음 | R2·R3·종합·C1 기준 줄(VSL 단서) |
| P-BVA | B − V-A | 같음 | R2(총합·구역만)·C1 기준 줄 |
| P-J1 (참고) | J1 − NC3 | 같음 | R2·R3 참고 칸(종합 표 밖) |
| Q-joint / Q-window / Q-off / Q-fw / Q-urb | codex 팔 − NC | 64cf-s29 | R4, R2·R3 의 64cf 칸 |
| Q-A1 (참고) | A1 − LNC, A1 − joint | 64cf-s29 | R4 흔들림 잣대 |
| Q-VSL64 (참고) | vsl_repro vsl − LNC | 64cf-s29 | R4 참고 |
| Q-hist (선택) | ALINEA rm − none, both − none (none = `historical_vsl_s29/none`; LNC 와 LF 해시가 같으면 LNC 캐시를 씀) | 64cf-s29 | R4 선택(새 스캔 H13–H16 이 끝날 때만; 9000 s 옛 코드·ALINEA 라 SDMPC 팔과 같은 표에 섞지 않고 따로 둠) |

- 64cf 짝의 NC: 링크 적분·첫 관측은 codex NC(`vhr/scan_out/nc_raw.json`, `first_nc_raw.json`), 물리·링크 칸은 LNC(`rmcause/phys/scan/cf_s29_none.json`, `lb_nc_s29.json`, `omega/cache/lnc_64cf_s29.npz`). A1 − LNC 는 LNC 만.

### 5.1 R1 — 무제어 FW_E 는 얼마나 막히나 (NC3 세 시드 주, LNC 나란히)

| 칸 | 정의 | 도구·출처 |
|---|---|---|
| R1-a ① 수준 | ① 7링크 합, 우리 꼴 [0, 9000] 과 codex 꼴 [0, 8100] | vhr 링크 적분 `integrals/ours_9000`, `codex_8100` |
| R1-b 구역 재고·속도 | 다섯 구역(주)·일곱 구역(보조)별 veh·h(대수 × 5 s)와 평균 속도(ΣV/ΣN), 300 s 창 | fwe_scan `gN`·`gV` (60 s × 100 m) |
| R1-c 혼잡 칸 | 100 m × 60 s 칸이 평균 속도 < 60 km/h 이고 밀도 > 15 veh/km/차로 이면 혼잡. 구역·셀별 혼잡 분(혼잡 칸이 하나라도 있는 60 s 창 수) | `fwe_analyze.py:14,56` 규칙 그대로 |
| R1-d 막힘 시작 | 구역: 혼잡 칸 ≥ 2 인 창이 두 번 이어지는 첫 창(`fwe_analyze.py:63-67`). 셀: 같은 규칙에서 "≥ 1 칸" 으로(셀이 2–5칸뿐이라). 시작 위치 = 그 창의 병목 머리(아래 R1-e) 와 그 셀 번호 | fwe_analyze 함수 import + 새 셀 집계 |
| R1-e 병목 링크·차로 | 머리 = 혼잡 칸인데 하류 두 칸이 70 km/h 이상(`fwe_analyze.py:81-91`). 머리별 분·첫 시각. 10분 이상 머리마다 [머리 − 300 m, 머리 + 100 m] 차로 칸에서 혼잡 창 평균 속도가 가장 낮은 차로(차로 칸은 3,800–8,000 m 만; 밖이면 "차로 못 냄"). 링크 = 머리 칸 가운데가 놓인 체인 링크 | fwe_scan `lN`·`lV`, `CHAIN` 오프셋(fwe_scan.py:19-20) |
| R1-f 번짐 분 | B1 번짐(B1 꼬리 < 4,500 m)·M 번짐(B2 꼬리 < 6,800 m) 분, 꼬리 최상류 위치·시각. 구역별 혼잡 분(R1-c) | `tails.py` `tails()` import(`cb6c0bd4…`) |
| R1-g 램프·진출·입구 | 진입 연결로+접근 링크 재고·대기 veh·h, 진출 커넥터 대기 veh·h, 합류율·삽입율(300 s 창 veh/h), 지체(108 km/h 기준, `fwe_analyze.py:16,70`) | fwe_analyze `analyse()` 출력 |

- 재현 점검(데이터 전 고정): R1-f 의 NC3 세 시드·LNC 값은 INV_PHYSICS.md:91-93·96 의 같은 칸과 같아야 합니다(멈춤 S-7).

### 5.2 R2 — 제어 팔의 ①·② 차는 어디서·언제 나오나

| 칸 | 정의 | 도구·출처 |
|---|---|---|
| R2-a 총합 | 짝마다 d①, d② 를 우리 꼴 [0, 9000](v3c3 주)과 codex 꼴 [0, 8100](64cf 주, v3c3 보조) 둘 다. **Ω701·④·Ω 밖 (a)(b) 를 같은 줄에** | vhr 링크 적분 + 기존 짝 표(§4) |
| R2-b 링크 × 300 s | 19링크마다 d veh·h. 꼴 = **bin 꼴**(아래 §7.2): 링크 × 150 s 차량-프레임 × 5 s, 300 s = 두 칸 | v3c3 NC3·V-A·B·J1·LNC 는 omega npz 에서 유도, vsl_repro vsl 은 기존 `lb_vsl_s29.json`, 나머지(codex 다섯 팔·VSL ×3)는 linkbin_scan 새 스캔(H4–H11) |
| R2-c 구역 × 300 s | 다섯 구역(주)·일곱 구역(보조)의 d veh·h 와 d 평균 속도(km/h) | fwe_scan(B·urban_only 는 새 스캔 H1–H4) |
| R2-d 셀 × 900 s | 31셀 d 평균 속도, d veh·h | fwe_scan 칸을 셀에 배정(칸 가운데 기준) |
| R2-e ②−① 쪽 | 진입 쪽(연결로 4 + 접근 링크 4)과 진출 쪽(커넥터 4)을 나눠 링크 × 300 s | R2-b 와 같은 원천 |
| R2-f 시간 모양 | 누적 d①(900 s 부터). **이득 시작** T_gain_a = d① ≤ −2.0 veh·h 인 첫 300 s 창(≥ 900 s). T_gain_b = 그 창부터 끝까지 누적 d① 가 늘 ≤ −5.0 veh·h 인 가장 이른 창. T_half = 누적이 최종값의 절반에 처음 닿는 창(최종 < 0 일 때) | R2-c 의 ① 합(구역 합 = ①) |

- 조정 줄: 300 s 창의 합(bin 꼴)과 총합(우리·codex 꼴)의 차를 링크 묶음마다 적습니다(멈춤 S-4).
- 64cf 짝은 0–8,100 s, 27창. v3c3 짝은 0–9,000 s, 30창.

### 5.3 R3 — 미터가 언제 조였고, 합류·재고·입구 대기는 어떻게 바뀌었나

| 칸 | 정의 | 도구·출처 |
|---|---|---|
| R3-a 미터 녹색 (GREEN 만) | FW_E 미터 4개의 10 s 주기마다 **GREEN 상태 초 수**(노랑·적색은 셈 밖). B·V-A = readback 주기 표 `obs_green_count`. codex 팔·A1·VSL·NC(64cf) = 미터 LDP(SC 9105–9108)에서 주기 [c, c+10) 의 c+1.0 … c+10.0 초 상태가 `I` 인 초 수(`CW/rawcheck/rm_exec.py:14-23` 규칙). v3c3 NC3 는 미터 LDP·결정 readback 이 없어 "기록 없음". J1 은 미터 LDP·readback 주기 표가 없고(원자료 `signal_readback.csv` 는 있음), `SP/rmcause/METER_CAUSE.md:18` 의 "61결정 × 미터 8개 내내 녹색 10" 을 [읽음]으로 적음. FW_W 미터 4개는 감시 칸 | readback `cycles_*.csv`, LDP, 새 `fwe_meter_ldp.py` |
| R3-b 처음 조임 | 미터마다 T_tight10 = GREEN < 10 인 첫 주기(≥ 900 s), T_tight6 = GREEN ≤ 6 인 첫 주기. 300 s 창마다 조인 주기 몫(GREEN < 10 인 주기 / 30) | R3-a |
| R3-c 합류 유량 | 합류마다(10639·10681·10490·10484) 300 s 창 veh/h(fwe_scan `merge` = 연결로에서 체인으로 옮긴 차 수 × 12), 짝 차 | fwe_scan |
| R3-d 램프·접근 재고 | 연결로 커넥터(`conn_stock`·`conn_q`)와 접근 링크 70·68·129·31(`from_stock`·`from_q`)의 veh·h·대기 veh·h(속도 < 15), 창 최대 대기 대수(`ramp_qmax`). linkbin `vf`·`qf` 로 대조 | fwe_scan, linkbin |
| R3-e 입구 대기 ④b 1098 | 첫 관측 차분을 창으로 나눔: 창 [a, b) 몫 = ∫ₐᵇ (I_NC(t) − I_팔(t)) dt / 3600, I = 첫 링크 74 인 차의 첫 관측 누적. 창 합 = 기존 첫 관측 총합. 링크 74 삽입율(fwe_scan `ins`) 함께 | 첫 관측 캐시(없는 팔은 H4·H5), `vhr_unins.py` `S_int`·`dU` 규칙 |
| R3-f 때 맞춤 | 미터마다 T_gain_a − T_tight10, T_gain_b − T_tight10 (s). 조임이 없으면 "조임 없음" | R2-f, R3-b |
| R3-g 비용 자리 | 짝마다 d > 0 인 칸: ②−① 링크 × 창 상위 10칸, 진출 커넥터, ④b 1098 창, Ω701 − ② 나머지, Ω 밖 (a)(b) 총합 | R2·R3 칸 |
| R3-h VSL 단서 | V-A 의 VSL < 110 결정 수·시각(run action CSV `kind=vsl` 행), B = 110 고정, VSL 팔 = 900 s 부터 91 | action CSV, VSL_RESULTS §1.8 |

### 5.4 R4 — codex 분할 팔 (64cf-s29, codex 꼴 [0, 8100])

| 칸 | 정의 |
|---|---|
| R4-a 팔별 짝 차 | 팔 − NC 마다 ①, ②, 도시도로(codex 분할), Ω701, ④a, ④b(첫 관측 차분, 합과 1098·1099·도시 입력별), ④ = ④a + ④b, Ω 밖 (a) = ④ − Ω701, Ω 밖 (b) = ④a − Ω701, 링크 66. FW_W 본선(26·10771·120)·④b 1099 는 감시 칸 |
| R4-b 팔별 FW_E 물리 | R1-b·R1-f·R3-c·R3-d 와 같은 정의(구역 속도, 번짐 분, 합류 유량, 램프 재고), 팔 − NC |
| R4-c 팔별 미터 | R3-a·R3-b 정의(LDP), `H/derived/decision_greens.csv` 명령과 대조 |
| R4-d 흔들림 잣대 | A1 − joint(같은 시드, 수치 경로만 다른 두 런)의 같은 칸. 이미 아는 ① +32.5 [읽음 `CH/a1/A1_RESULT.md:266`] |
| R4-e 대조 | 팔·NC 의 Ω701·①·② 수준값을 `H/derived/metrics_0_8100.csv`(joint·freeway_only·urban_only·nc)와 `independent_fzp_counts.json`(window·off)에 맞춤(멈춤 S-5) |

- 원천: 링크 적분 = vhr `codex_8100`(codex NC 와 다섯 팔 모두 있음). Q-A1 의 총합 칸은 A1_RESULT r2 값을 [읽음]으로 옮기고 새로 세지 않음. Q-VSL64 는 vhr 적분이 없어 bin 꼴(`lb_vsl_s29.json`·`lb_nc_s29.json`)로만 내고 "bin 꼴" 이라 표시(참고). ④b = 첫 관측(joint·window·off·NC·A1·LNC·vsl_repro 있음, freeway_only·urban_only 는 H4·H5). 물리 = fwe_scan(urban_only 는 H4). 선택 Q-hist 는 H13–H16 이 끝나야만.
- 해석 단서(데이터 전 고정): freeway_only 는 VSL 도 움직였고 목적·정보가 함께 다르므로 "미터 몫" 으로 읽지 않습니다. 팔 사이 차는 기구가 둘 이상 함께 달라진 한 시드 차입니다 [읽음 HANDOFF_codex:222-224].

---

## 6. 종합 출력 (Declare 3)

### 6.1 기구 후보 표 (짝 × 시드마다 한 줄)

- 칸: d① 우리·codex 꼴 / d① 구역별(U·B1·M·B2·D) / d(진입 쪽) / d(진출 쪽) / d④b 1098 / Ω701·④·Ω 밖 (a)(b) / FW_E 미터 조인 주기 수와 T_tight10 / 이득 창에서 합류별 유량 차 / 이득 창에서 10643·10481 진출 재고 차 / 이득 창과 겹친 V-A VSL < 110 결정 수.
- **이득 창** G = d①(구역 합) ≤ −2.0 veh·h 인 300 s 창(≥ 900 s)의 모임.
- 조건 깃발(지금 고정, 값은 [계산] 참/거짓; 여럿이 함께 참일 수 있음; 판정이 아니라 칸 정리):

| 깃발 | 참이 되는 조건 (모두 G 안에서 합) |
|---|---|
| C-RM (미터 붙잡기) | 어떤 FW_E 미터 m 이 G 의 주기 중 30 % 이상 조였고(GREEN < 10), 그 합류 유량이 NC 보다 60 veh/h 이상 낮고, m 의 합류 하류 구역(10639·10681 → B1, 10490·10484 → B2) d① ≤ −1.0 veh·h |
| C-OFF1 (10643 진출 역류 완화) | d(10643 커넥터 재고) ≤ −1.0 veh·h 이고 d①(U + B1) ≤ −1.0 veh·h |
| C-OFF2 (10481 진출 역류 완화) | d(10481 커넥터 재고) ≤ −1.0 veh·h 이고 d①(M + B2) ≤ −1.0 veh·h |
| C-VSL | V-A: VSL < 110 결정의 150 s 칸이 G 와 겹친 수 ≥ 1. VSL 팔: 늘 참(처치 자체). B: 늘 거짓 |
| C-ENT (입구 붙잡기) | d④b 1098 ≥ +1.0 veh·h 이고 d①(U) ≤ −1.0 veh·h |
| C-NONE | 위 깃발이 모두 거짓 |

- 꼬리표: 깃발 값은 [계산], "그 기구가 몫을 냈다" 는 말은 늘 [추론] 입니다. 문턱(2.0·5.0·1.0 veh·h, 30 %, 60 veh/h)은 보고 칸을 나누는 선이지 판정 문턱이 아닙니다.
- 64cf 짝(Q-*)도 같은 표 꼴로 따로 둡니다(v3c3 와 빼지 않음).

### 6.2 C1 FW_E 기준 줄 (보고 전용 칸, 판정 문턱 없음)

- 뜻: C1 결과가 나오면 C1 − NC3 · C1 − V-A · C1 − B 를 **이 칸들로** 같은 시드마다 적고, 아래 기준 값과 나란히 둡니다. C1 이 아직 데이터가 없으므로 C1 쪽에서는 "데이터 전 보고 칸" 입니다(C1 규칙·문턱은 바꾸지 않음).
- 기준 값으로 채울 짝: P-VA, P-B, P-VSL, P-BVA (시드 3). P-J1 은 참고 열. 64cf joint − NC 는 나란히 놓는 별도 열.

| 칸 | 내용 |
|---|---|
| RF1 | d① 우리 꼴 [0, 9000] · codex 꼴 [0, 8100] |
| RF2 | d② 같은 두 꼴 |
| RF3 | d① 다섯 구역 × 900 s 창 |
| RF4 | FW_E 미터마다 GREEN < 10 주기 수, T_tight10, T_tight6, GREEN 초 분포(readback) |
| RF5 | 합류 넷의 유량 차 × 900 s 창 (veh/h) |
| RF6 | 미터별 연결로+접근 링크 재고·대기 veh·h 차 |
| RF7 | d④b 1098 합과 × 900 s 창 |
| RF8 | 진출 커넥터 넷 재고 차 |
| RF9 | B1·M 번짐 분(팔, NC3) |
| RF10 | VSL < 110 결정 수·시각(C1 은 V-A VSL 그대로, D-K9-101) |
| RF11 | T_gain_a·T_gain_b·T_half, T_gain − T_tight10 |
| 함께 | Ω701·④·Ω 밖 (a)(b) (Ω701 을 적을 때 늘 함께) |

- 출력 파일: `FD/out/FWE_REF_C1.json`(+ 같은 내용 표 `FWE_REF_C1.md`). C1 워크플로가 읽어 쓰도록 칸 이름을 고정합니다.

---

## 7. 지표 정의 공통

### 7.1 링크 집합 [읽음]

- ①·② = §2. 진입 쪽 = 10639·10681·10490·10484·70·68·129·31. 진출 쪽 = 10643·10682·10481·10483.
- Ω701 = `omega_membership_exact.json` `/inside_links`. 도시도로 = codex 분할(Ω701 − 양방향 본선 사슬 − 진입 커넥터 8 − Ω701 안 진출 커넥터) [읽음 OMEGA701_V3C3.md:16]. FW_W 본선 = 26·10771·120(감시) [읽음 OMEGA701_V3C3.md:86].

### 7.2 적분 꼴 셋

| 이름 | 정의 | 쓰는 곳 |
|---|---|---|
| 우리 꼴 | 프레임 5.1 s 부터 창 안 마지막 프레임까지 사다리꼴, 0.1 s 행 건너뜀, 양끝 늘림 없음 | v3c3 총합 주 (OMEGA701_V3C3.md:18) |
| codex 꼴 | t = 0 빈 망에서 시작, 모든 행, 창 끝 넘는 행 버림, 마지막 프레임 재고를 창 끝까지 유지 | 64cf 총합 주, v3c3 보조 (`check_fzp.py` `1a2cf568…`) |
| bin 꼴 | t ≥ 1.0 s 행만, 링크 × 칸(칸 = ⌊t / 150⌋ 또는 ⌊t / 60⌋)의 차량-프레임 × 5 s / 3600 (사각형) | 창 분해(R2-b·c·d, R3) (`linkbin_scan.py:1-14`, `fwe_scan.py:92-105`) |

- omega npz → bin 꼴 유도: `t ≥ 1.0` 인 프레임만, 칸 = ⌊t / 150⌋, M 의 링크 열 합 × 5 / 3600. 이 유도가 linkbin_scan 과 같은지 LNC 에서 맞춤(멈춤 S-3).
- fwe_scan 의 구역 합(체인 칸 `gN` 합)은 ① 의 bin 꼴과 차량-프레임이 같아야 합니다. 연결로·접근·진출 재고(`conn_stock`·`from_stock`·`off_stock`)를 더하면 ② 의 bin 꼴과 같아야 합니다(멈춤 S-8, 보고만).

### 7.3 ④b 창 분해

- 같은 시드 두 런은 입력 도착열이 같다고 봅니다(첫 관측 차분의 가정, vhr_unins.py:1-4). 입력 범주 c(74·26·그 밖)의 첫 관측 누적 I_c(t). 짝 차(팔 − NC)의 창 몫 = ∫ₐᵇ (I_c,NC(t) − I_c,팔(t)) dt / 3600. [0, W] 창 합은 기존 `dU(팔, NC, W)` 와 같아야 합니다(멈춤 S-6).

### 7.4 미터 GREEN 만

- 녹색 = GREEN 상태 초만. readback 은 `obs_green_count`(READBACK_METER.md:37-38 K3), LDP 는 상태 문자 `I`(rm_exec.py:17,23). 노랑·적색·빈 초는 녹색이 아닙니다. 주기 = 900 s 부터 10 s 칸(900, 910, …).

---

## 8. 도구 핀

### 8.1 기존 도구·정의 (바꾸지 않음; sha256 은 [실행] `FD/out/pins_existing.json`)

| 도구·파일 | sha256 | 쓰임 |
|---|---|---|
| `SP/rmcause/phys/fwe_scan.py` | `0619e9fcbe14fd1b2e53d1cf884a8d740c0542f5686df33ef26f450a2b08bae7` | 새 FW_E 물리 스캔(H1–H4), 기존 스캔 읽기 |
| `SP/rmcause/phys/fwe_analyze.py` | `5c055dd44b0ae8be6ca4907186e0ba8f25afb8626c3adfc097a5135c918e3aaf` | R1 규칙·`analyse()` import |
| `SP/rmcause/o1o4/work/tails.py` | `cb6c0bd4407fbaad8b403ccc34fc2bcfb1f9b9af318a67ee963b120a8bfb5569` | 번짐 분 `tails()` import |
| `SP/rmcause/o1o4/work/linkbin_scan.py` | `a22d5fa69aff12b5206041437613ad0b7a0decdf56cb5ec7d7e5a071d974b82b` | 새 링크 × 150 s 스캔(H4–H12) |
| `CW/vhr/vhr_firstseen.py` | `42e17585172e8c3cdc529ee0b0768ec958ab34729bbe686c590e70053ada4c94` | 첫 관측 `run()` (래퍼가 출력 폴더만 바꿔 부름, H4·H5·H13–H14) |
| `CW/vhr/vhr_scan.py` | `a19942b8358b353329c30818c59b63cc88ff4b65e8b3dfa291de89e4c1de1865` | 링크 적분 네 꼴 `scan()` (선택 H13–H16 만) |
| `CW/vhr/vhr_unins.py` | `fc233013623d797657c19e0efbb59b6ccad720a19a84e723491ad73a34337532` | ④b 첫 관측 차분 규칙(`S_int`·`dU`) |
| `CW/vhr/vhr_v3c3_all.py` | `b42372512a26960530cfe89b1dc731a74f7fc83531c17f4ec04c4706409d2c99` | Ω·④·Ω 밖 식(읽음, 같은 식으로 다시 냄) |
| `CW/vhr_b/vhr_v3c3_all_b.py` | `d91ded54904eb43a78a49f0d2a1382396258a0cf0621fbf6e7ba2410fb7283ed` | 같은 식, B 짝 |
| `CW/omega/omega701_recount.py` | `5b7826f65c58a883c2dc4a3eccd6de92563bb12f812dd0d6579be8a42c92a5ac` | npz 캐시의 뜻(읽음) |
| `H/code/handoff/check_fzp.py` (= `CW/omega/check_fzp_copy.py`) | `1a2cf5681fc18c653328bb460c0af2519760a11fa4744c35d85a0f15e0506a19` | codex 꼴 정의 |
| `SP/vsl_v3c3/tools/vsl_metrics.py` | `160c23c76d354b769718ab31044782609b96e238196b2bf1817ef053aacca71c` | 일곱 구역(:56)·구역 속도 식 |
| `SP/vsl_v3c3/tools/vsl_cell_scan.py` | `fa5aeafd01c99297652f8f5fce6d5f760cdbb223640b3258d2020cd03229a078` | 31셀 경계 |
| `CW/rawcheck/rm_exec.py` | `27f6402205d6c7cbd3524a44ee35632e19a90f681a10d21fffa3b5518dbb1c10` | LDP GREEN 규칙 |
| `SP/c_port/readback/tools/rb_readback.py` | `cee5f2629b8accc602655cbcbf2dc706796f57b97a69f66ee25966ac550a96cb` | readback 주기 표의 뜻 |
| `H/derived/omega_membership_exact.json` | `efdfaeb1b9d0d670119c8e158eabd615033bb1127cabd84d187b064ba64cd473` | Ω701 |
| `H/derived/reporting_partition.json` | `3142f69c0502f6d9d12416b5b6131d57799bf8f2d17d207b4b0312e854f1dd2b` | 도시도로 codex 분할 |
| `H/analysis/original_scripts/solo355_compare_20261014.py` | `7fc91d604214b3ea757c2e7c34f59a694a801ac21bf83c7e02fd57cde27e7fd1` | 분할 규칙(:49-61) |
| `H/derived/metrics_0_8100.csv` | `a2757f7288ba3f0e0d91222c25d353c0f3f015af28e2f9ebdb594508e3cfc37a` | R4 대조(joint·freeway_only·urban_only·nc) |
| `H/derived/independent_fzp_counts.json` | `f55be7114af7b1d9049e7daee9748e667491dd486a07c1e92b6bc0aa010e09b4` | R4 대조(window·off) |
| `H/derived/decision_greens.csv` | `5f63309329ab26f1a7269b77ac9f1c964bfb2115fbcd4b18a455ff87086792e0` | 64cf 팔 미터 명령 |

- 전체 63개 파일(도구 20·정의 5·문서 22·결과 표 16)의 전체 sha256 은 `FD/out/pins_existing.sha256`(sha256sum -c 꼴)에 있습니다. 첫 숫자 계산 전과 끝에 `sha256sum -c` 로 다시 맞춥니다.

### 8.2 새 도구 (이 문서 뒤, 첫 숫자 전에 씀)

- 새 도구는 아래 일만 합니다. 쓰고 나면 sha256 을 `FD/PINS_FWE.sha256` 과 LOG 에 고정한 뒤, 합성 자료 자기 시험(`FD/selftest/`)을 통과해야 실제 자료에 돌립니다. 고정 뒤 고치면 새 핀·LOG 줄을 남기고, 그 전 출력은 버립니다.

| 새 도구 | 하는 일 |
|---|---|
| `fwe_heavy.py` + `fwe_launch.ps1` | 무거운 일 차례 실행: 잠금 잡기·풀기, 기존 도구 부르기, 새로 낸 FZP sha 를 목록과 대조, 소유 PID 기록 |
| `fwe_wrap_vhr.py` | `vhr_firstseen.run`·`vhr_scan.scan` 을 import 해 출력 폴더 변수만 `FD/out/heavy/` 로 바꿔 부름(원본 파일 불변) |
| `fwe_npz_bins.py` | omega npz → bin 꼴 링크 × 150 s, LNC 를 `lb_nc_s29.json` 과 맞춤 |
| `fwe_meter_ldp.py` | 미터 LDP → 10 s 주기 GREEN 초(§7.4) |
| `fwe_r1.py` · `fwe_r2.py` · `fwe_r3.py` · `fwe_r4.py` | §5 칸 계산(캐시만 읽음) |
| `fwe_synth.py` · `fwe_compose.py` | §6 표와 FWE_REF_C1, 보고 글(숫자는 모두 도구 출력에서 채움) |
| `selftest/test_fwe.py` | 합성 자료: 창 합 = 총합, ④b 창 분해 합 = dU, npz→bin = 직접 셈, 깃발 경계값 |

---

## 9. 순서

- 가벼운 일(L) 먼저, 무거운 일(H)은 공용 잠금 아래 하나씩. FZP 를 읽는 일은 크기와 무관하게 모두 무거운 일로 봅니다.

| 차례 | 일 | 종류 | 어림 |
|---|---|---|---|
| L0 | 목록·핀(이 문서) | L | 끝남 |
| L1 | 새 도구 쓰기·핀·자기 시험 | L | — |
| L2 | R1 (NC3 ×3, LNC: 기존 fwe_scan·vhr) + 재현 점검 S-7 | L | < 1 min |
| L3 | npz → bin 꼴(NC3·V-A·B·J1·LNC) + S-3, V-A·J1·VSL 의 R2-c·R3(B 는 H1–H3 뒤) | L | < 2 min |
| H1–H3 | fwe_scan: B v3c3-s31 → s41 → s43 | H | 각 약 45 s |
| H4 | codex urban_only: fwe_scan + 첫 관측 + linkbin | H | 약 2 min |
| H5 | codex freeway_only: 첫 관측 + linkbin | H | 약 1 min |
| H6–H8 | linkbin: codex joint → window → off | H | 각 약 40 s |
| H9–H11 | linkbin: VSL v3c3-s31 → s41 → s43 | H | 각 약 40 s |
| H12 (선택) | linkbin: A1 | H | 약 40 s |
| H13–H16 (선택) | historical: ALINEA rm·both (링크 적분 + 첫 관측 + fwe_scan), VSL none·bottleneck90 (링크 적분만, LNC·vsl_repro 와 LF 해시 대조) | H | 각 1–2 min |
| L4 | 미터 LDP(64cf 팔·A1·VSL·NC) GREEN 주기, R2·R3 마무리, R4 | L | < 2 min |
| L5 | 종합(§6), 보고 글, 핀 재확인, 보고 사본 | L | — |

- 무거운 일 규칙(작업 지시 그대로):
  - 잠금 `D:/VISSIM-merge/k8_gate_trees/heavy.lock` 을 **배타 생성**(있으면 30 s 뒤 다시). 안에 주인 `fwe_decomp`·PID·시각·일 이름. 내 것만 지움. 풀고 나면 **20 s 이상 쉬고** 다시 잡음(C1·VSL-plant 작업 차례 보장). 일 하나 = 잠금 한 번(FZP 하나, 그 FZP 에 도구 1–3개).
  - WMI(`Win32_Process.Create`)로 세션과 분리해 띄움. BELOW_NORMAL, `PYTHONHASHSEED=0`, `python -B`, `OMP/OPENBLAS/MKL_NUM_THREADS=1`. 출력은 `FD/out/heavy/` 와 `D:/VISSIM-merge/k8_gate_trees/fwe_decomp/` 에만.
  - 소유 PID 만 kill. 남의 VISSIM·python 은 건드리지 않음.
- 하지 않는 일: VISSIM·COM·러너·동결·결정 재생·코드 변경·커밋·푸시(GWT8 `D:/VISSIM-merge/sim3-n31-k8` 는 c20aff1d 그대로). 다음 시험 파일은 돌리지 않음: `test_b1a_watchdog_attempt_launch.py`, `run_plant_fidelity_matrix`, `test_runner_ps1_obs150.py`, `test_native_vbs_clock.py`, `test_tools_launch.py`, `test_tools_replay.py`, `real_watchdog`.

---

## 10. 멈춤 규칙

| # | 조건 | 할 일 |
|---|---|---|
| S-1 | 새 스캔이 낸 FZP sha256 ≠ 목록의 캐시 sha | 그 팔의 새 출력 안 씀, LOG·보고에 적고 그 칸 "못 냄" |
| S-2 | 짝의 provenance 시드가 다르거나, 망 sha 가 §3.1 의 허용 묶음 밖 | 그 짝 멈춤 |
| S-3 | LNC 의 npz → bin 꼴 `vf` 가 `lb_nc_s29.json` 과 링크·칸 하나라도 다름 | npz 유도 링크 칸(R2-b) 멈춤, 사용자에게 물음(그 팔들을 linkbin 으로 다시 스캔할지) |
| S-4 | (가) npz 가 있는 런: npz 프레임으로 다시 낸 우리·codex 꼴 ①·② 총합이 vhr 적분과 0.001 veh·h 넘게 다름. (나) 모든 런: 총합(우리 꼴 v3c3 / codex 꼴 64cf) − 창 합(bin 꼴)이 ① 또는 ② 에서 1.0 veh·h 넘게 다름(정상 차는 양끝 프레임 재고 × 2.4–2.5 s 뿐이라 [추론] 1 veh·h 아래) | 그 런 창 표 멈춤, 원인 적음 |
| S-5 | R4 다시 센 Ω701·①·② 수준이 codex 표와 0.01 veh·h 넘게 다르거나, codex NC 와 LNC 의 링크 적분이 1e-6 veh·h 넘게 다름 | R4 표 멈춤 |
| S-6 | ④b 창 합 − 기존 첫 관측 총합 > 0.05 veh·h | R3-e 멈춤 |
| S-7 | R1 번짐 분이 INV_PHYSICS.md:91-93·96 과 다름 | R1 멈춤(도구 차 확인 뒤 다시) |
| S-8 | fwe_scan 구역 합과 ① bin 꼴(또는 ② 합)이 다름 | 보고만(정의 차 적음) |
| S-9 | 무거운 일 하나가 잠금을 60 분 넘게 못 잡음 | 남은 무거운 일 멈춤, 가벼운 일만 마치고 그 칸 "못 냄" |
| S-10 | 무거운 일 하나가 10 분 넘게 끝나지 않음(어림 < 2 min) | 소유 PID 만 kill, 한 번 다시; 또 넘으면 "못 냄" |
| S-11 | 봉인 시드 37/59/61/67·`sealed/`·codex 64cf-s59/s61/s67·v3c3-s47 자료에 닿을 일 | 열지 않음. 출력에 섞이면 그 출력 버리고 멈춤 |
| S-12 | 이 문서에 없는 칸·자르기를 보고 싶어짐 | "데이터 뒤" 따로 절에만, 깃발·기준 줄에 쓰지 않음 |
| S-13 | C: 여유 < 5 GB | 쓰기 멈춤 |
| S-14 | 900 s 전 창의 ② 링크 \|d\| 합 > 0.05 veh·h | 보고만(접두 다름 표시 †) |

---

## 11. 산출물 (계산 단계에서)

- `FD/out/R1_nc.json`, `R2_pairs.json`, `R3_meters.json`, `R4_codex.json`, `FWE_ATTRIB.json`, `FWE_REF_C1.json`(+ `.md`), `FD/out/heavy/*`(새 스캔), 보고 `FD/FWE_RESULTS.md`(+ sha256).
- 보고 사본: `D:/VISSIM_runs/20261001_v3c3/reports/k8/fwe_decomp/`.
- 모든 보고 숫자는 도구 출력에서 채웁니다. 시드마다 따로, 평균 없음. 64cf 는 따로 묶음.

## 12. 모름 (지금 아는 한계)

1. 같은 시드라도 900 s 뒤 궤적이 갈리므로, 한 짝 차 안에 "기구 몫" 과 "궤적 갈림 몫" 이 섞입니다. 64cf 의 A1 − joint 가 그 크기의 한 표본일 뿐이고, v3c3 의 짝 잡음 크기는 모릅니다 [추론, VSL_RESULTS.md:82].
2. 미터 readback·LDP 는 신호 상태 수준입니다. 차가 그 녹색만큼 지났는지는 합류 유량(R3-c)으로만 봅니다 [읽음 READBACK_METER.md:26].
3. 진출 역류(10643·10481)가 도시 신호 몫이라는 것은 위치·배수 구조로 본 추론입니다. 신호 녹색 대조는 이 질문 밖입니다.
4. 기구 깃발은 조건이 맞는지만 말합니다. 몫의 크기를 기구별로 나누는 식은 정하지 않았습니다(구역·링크 차를 그대로 적음).

---

## 13. 이 단계 파일 sha256 [실행]

| 파일 | sha256 |
|---|---|
| `FD/tools/fwe_inventory.py` | `19316cfc5219dbd348ec3ee834e9a12b668436c91e53b0c266bd484ebe2dc04c` |
| `FD/tools/fwe_inventory_md.py` | `2741c59ffaa2c4faffa604856fb65e211802802eddce83e18130503e880c3441` |
| `FD/tools/fwe_pins_existing.py` | `22ad6c34312117253aa71cebd189180397091d3cf5d21143f599cb4d5b90159c` |
| `FD/out/inventory.json` | `f51abd202cef209d1b1b5e79b4d3eb4ea13661fe9e0d2ec7d68bd8c5467c94e6` |
| `FD/out/INVENTORY.md` | `6227c08f698a9eafd0b5fb42bfd3c2e7f6229008d35a801cc8da3c49efaa163c` |
| `FD/out/pins_existing.json` | `f9e89ecb67d7bb5b5be67794bf769aeda30e6dacccccc5fa7cef45d08381afb3` |
| `FD/out/pins_existing.sha256` | `1518af1e2753fbe0780eb995935efc6f70ed90e0e81847652f3bb8eaeee9a8b3` |
| 이 문서 PRE_FWE.md | 자기 sha 는 안에 적을 수 없어 `FD/PRE_FWE.md.sha256`·`FD/SHA256SUMS_DECLARE.txt`·LOG 마감 줄에 적음 |
| 결정 기록 NT | `efc3a7220aa1d1b3…`(지금 파일). 작업 지시가 적은 `a11fc94c…` 와 다름: NT 는 16:11 KST 에 더 고쳐진 판이고 D-K9-104·106 줄(346–354)은 그대로 있음 [실행 sha256, 읽음 줄] |
