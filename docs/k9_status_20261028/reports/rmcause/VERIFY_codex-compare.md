# VERIFY_codex-compare — METER_CAUSE.md 의 codex 비교 주장 검토 (2026-10-24 KST)

- 대상: `RC/METER_CAUSE.md` sha256 `58c3c31bad7896a7d6ffe09a238a5297bea51313f60b854e2c227f05ee3dae52` [실행 sha256sum].
- 렌즈: codex 비교. codex 커밋·브랜치, 미터 논리, 망·수요, 기준선, 지표, "FW_E 10 % 넘게" 숫자의 출처와 비교 가능성. 그리고 "차이는 나열한 항목으로 설명된다"를 깨 보려 했습니다.
- 경로 약칭: SP = `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8`, RC = `SP/rmcause`, VX = `RC/verify_cx`(이번 검토의 읽기용 추출물). GWT8 = `D:/VISSIM-merge/sim3-n31-k8`(head c20aff1d, 깨끗함 [실행 git status]).
- W264 = codex 설정 `vsl_window264` 로 이 PC 에서 돈 런 `D:/VISSIM-runs-window264-s29-9000-recovery-20261007/sdmpc`.
- 줄임말(처음 한 번): RM = 램프 미터. ALINEA = 합류 하류 점유율 되먹임 규칙 미터. SDMPC = 분산 모형예측제어기. VSL = 가변 제한속도. Ω = 목적함수 영역 링크 집합. NC = 무제어 런. FZP = VISSIM 차량 궤적 기록. DSD = 희망속도 분포. TTT = 총 통행시간(veh·h). plant = 제어기 안의 예측 모형. δ_merge = 램프 합류가 본선 속도를 깎는 항. 본선 7링크 = 74·10699·2·10613·119·10702·24. 국소 19링크 = 본선 7 + 동측 진입·진출 커넥터 8 + 진입 접근로 4.
- 표시: [실행] = 이번 검토에서 직접 돌림. [읽음] = 코드·자료·문서를 읽음. [추론] = 시험 안 한 판단. 판정: **확인** / **부분 수정** / **반박** / **근거 없음**. "핵심" = 결론을 받치는 주장.
- 봉인 시드 37/59/61/67 자료는 열지 않았습니다. codex AGENTS.md 줄 가운데 그 시드가 나오는 줄의 숫자는 쓰지 않았습니다. 시드는 망 접두어를 붙입니다(64cf-s29 등).

---

## 0. 결론

1. **유지되는 것.** codex 쪽 "10 % 넘는" 두 숫자의 값은 맞습니다. d80faf99 ALINEA 64cf-s29 본선 −11.81 %, W264 64cf-s29 본선 −11.61 % [읽음·실행]. 둘 다 64cf 망·한 시드·본선 7링크 지표라는 METER_CAUSE 의 요지도 맞습니다. 우리 c20aff1d SDMPC 경로에 이웃 검사가 없다는 것도 맞습니다 [실행 git grep 0건].
2. **고쳐야 하는 핵심 다섯.**
   - (R1) "다른 SDMPC 9,000 s 런 East +7.85 %"는 이웃 검사가 **켜진** 런의 0–6,600 s 중간 추정치입니다. 같은 검사 계보에서 FW_E 가 나빠진 기록입니다(§2).
   - (R2) "이웃 검사가 핵심 차이"는 미터를 움직인 **직접 장치**로는 맞지만, FW_E 이득을 설명하는 **충분조건이 아닙니다**. codex 의 같은 검사 계보에서 녹색 0 허용·공유차로 역류 때문에 결과가 나빴고, W264 는 그 뒤 여러 수정이 더해진 상태였습니다(§2).
   - (R3) §2.1 6행 δ_merge "불명"은 틀렸습니다. 설정 층은 양쪽 모두 0.3 입니다. W264 plant 는 expanded036 셀별 보정으로 FW_E 셀 10·12·21·23 에 δ_merge 3.53·5.09·4.21·2.21 을 얹습니다. 우리 plant 는 FW_E 1.0 균일입니다(§1 C9).
   - (R4) §2.1 7행 "가장 많이 움직인 미터가 10681·10484"는 틀렸습니다. 서측 RM_C10480 이 55/61 로 가장 많습니다(§1 C10).
   - (R5) 사용자가 기억할 수 있는 숫자는 d80faf99 쪽뿐입니다. W264 −11.61 % 는 codex 가 분석·푸시한 적이 없고 오늘 처음 계산됐습니다. 또 codex 문서상 사용자가 10-01 에 지목한 그림의 동측 영역은 국소 19링크(−8.90 %)입니다(§1 C2·C3).
3. **빠진 차이.** W264 설정과 V-A 설정은 메모를 빼고도 186개 키가 다릅니다 [실행 `VX/cfgdiff2.py`]. METER_CAUSE 표에 없는 것: plant 보정 묶음(expanded036), 램프 서비스 표, 녹색 0 금지·저장 해제 guard, v_free 120, VSL 집합·구역, 도시 신호 조건(§3).
4. **판정: pass = false.** 핵심 주장 가운데 반박 3건(R1·R3·R4)과 부분 수정 2건(R2·R5)이 남습니다. 결론 "(a) 결정층이 우리 미터 고정의 원인"은 이 렌즈에서 흔들리지 않습니다. 흔들리는 것은 "codex 에서 무엇이 FW_E 10 %를 만들었나"의 설명입니다.

---

## 1. 주장별 판정

| # | METER_CAUSE 주장(위치) | 판정 | 근거 | 필요한 수정 |
|---|---|---|---|---|
| C1 | ALINEA 64cf-s29 본선 −11.81 %, Ω +4.64 %, 전체+미삽입 +6.43 %, 국소 −8.90 %, 64cf-s23 −1.32 % (§0.5, d1, d2) [핵심] | **확인** | `d80faf99:diagnostics/vsl_handoff_20260924/evidence/accounting/east_link_sets_source.json` rows[5] 본선 2249.692667→1984.080944(−11.8066 %), 국소 −8.9033 %; rows[1] 64cf-s23 −1.3191 % [읽음 `VX/els.json`]. `85e3454b:…/BASELINE_REPRODUCTION_GATE_20260929.md:20,22` Ω 7263.267→7600.425(+4.642 %), 28944.770→30806.576(+6.432 %) [읽음; 백분율 실행]. 같은 문서 :16 "도시신호는 native 고정" [읽음] | 없음. 단 ALINEA 팔은 동·서 8개를 함께 미터했습니다(json `limitations[0]` "BOTH-DIRECTION") [읽음]. 서측 미터 몫은 모릅니다. 한 줄 덧붙이기 |
| C2 | W264 본선 −11.61 %, 국소 −5.46 %, 진입 커넥터 +39.79, 접근로 +101.04, 전체+미삽입 −2.21 % (§0.5, 2.1) [핵심] | **확인(값)** / **부분 수정(출처)** | `codex_scan/out/cf_s29_window264.json`·`cf_s29_none.json` 재계산: 1987.791 vs 2248.982(−11.614 %), 국소 −5.461 %, 900 s 전 행 431,233개 sha `f1a0b040…` 같음 [실행]. native 성능 JSON (33,268,335.1+68,632,177.4)/3600 = 28,305.698 → −2.208 % [실행]. `DECISIONS_FAILED=0` [실행 runlog:6614]. codex 상태 `requested_native_arms_complete_unanalyzed` [읽음 `native_status.json`]. `ffa4861e:AGENTS.md:3` 은 "native time-window gain NOTyetvalidated" 뿐이고, 9a8320ec 의 `docs/sdmpc_vsl_20261023/README.md` 에도 W264 성과 기록이 없음 [실행 grep; 9a8320ec 는 임시 fetch] | "W264 −11.61 % 는 codex 가 분석·보고한 숫자가 아니다. 2026-10-24 INV_CODEX 가 처음 계산했다. 사용자가 codex 푸시에서 본 숫자일 수 없다"를 §0.5·§5 Q1 에 넣기 |
| C3 | §5 Q1 "(i) d80faf99 의 64cf-s29 ALINEA −11.81 %(그림 `east_heatmap.png`)" [핵심] | **부분 수정** | codex `85e3454b:…/CALIBRATION_DATA_SCOPE_20261001.md:3` 사용자가 10-01 지목한 그림 = `bottleneck90_rm_20260924/results/east_heatmap.png`(푸시 안 됨). 같은 문서 :18 "그림의 동측 지역은 … 19links", RM 단독 −8.90 % [읽음]. d80faf99 에 있는 `evidence/native9000_seed29/east_heatmap.png` 는 VSL90 단독 그림(제목 "RM OFF")이고 숫자 표기가 없습니다 [읽음 `VX/d80_vsl90_s29_east_heatmap.png`] | "(i) ALINEA: 본선 7링크 −11.81 %(east_link_sets_source rows[5]) / 그림 영역(국소 19링크, codex 문서 기준) −8.90 %. 그림 원본은 codex PC 에만 있음"으로 바꾸기 |
| C4 | "codex 에서 미터를 움직인 것은 '규칙'과 '이웃 검사'" (§0.6) | **확인** | W264 결정 55회 중 이웃 검사가 49회 미터 후보 선택 [실행 `VX/w264_audit.py` → `w264_audit.jsonl`]. codex 219 런 첫 결정도 유한 검사로 10681 g10→g8, 모형 이득 0.000194 veh·h [읽음 `ca181e84:AGENTS.md:91`] | 없음 |
| C5 | "우리 c20aff1d 에는 둘 다 없습니다" (§0.6) | **부분 수정** | 규칙 ALINEA 산술은 c20aff1d 에 있습니다: `evaluation/controllers/diagnostic_profile.py:227 alinea_meter_step`, 함수 본문 AST sha `97067baa…` 가 d80faf99(:271)와 같음 [실행]. V-A SDMPC 경로에서 안 쓰일 뿐입니다 | "우리 V-A SDMPC 경로에는 규칙 미터도 이웃 검사도 없다. 규칙 ALINEA 코드는 c20aff1d 에 있다(v3c3rm 팔이 이 경로)"로 |
| C6 | "codex SDMPC 도 이 검사가 없을 때는 8개 모두 g10" (§0.6, a1, §2.1) [핵심] | **확인(범위 한정)** | `85e3454b:…/METER_ACTIVATION_RESULT.md:13,20` = 64cf-s29 3,600 s 한 상태 오프라인 재선택. `BASELINE_REPRODUCTION_GATE:29` "현재 SDMPC9000 은 8미터 모두 g10" [읽음]. 반례 범위: 검사 도입 전(10-01) 64cf-s47 상태 오프라인 재선택에서 SDMPC 가 이어받은 10484 g2 를 유지하고 10490 을 g5→6 으로 바꿈 [읽음 `85e3454b:AGENTS.md:307`] | "g10 에서 시작한 상태에서는 g10 에 머문다. 이어받은 녹색이 낮으면 그 값을 유지했다(64cf-s47 기록)"로. METER_CAUSE §1.1 자기 유지 설명과 맞음 |
| C7 | "다른 SDMPC 9,000 s 런 East +7.85 %(64cf-s29, 9a8320ec AGENTS.md:19)" (§2.1 끝) [핵심] | **반박(성격 규정)** | 줄은 실재 [실행 임시 fetch: `9a8320ec:AGENTS.md:19`; 같은 글 `ca181e84:AGENTS.md:15`, `ffa4861e:AGENTS.md:17`]. 그러나 내용은 REVIEW255 **중간값**: 런 233/235(고정 VSL90 900 s~), **0–6,600 s**, 150 s 재고 사다리꼴 **추정**, "not 9000 completion". 이 런은 **유한 RM 검사가 켜져** 있었음: REVIEW235 "Production sdmpc now audits each solved feasible budget"(`ca181e84:AGENTS.md:57`), REVIEW241 첫 결정 "RM10681g10->8 … finiteRM"(`:43`). 7,959 s 에 중단, 원인 "10480RED->124lane1queue->10483blocked->Eastspillback"(`:13`) [읽음] | "codex 의 이웃 검사 계보 런(233/235, 64cf-s29, 고정 VSL90)은 미터를 움직였고, 0–6,600 s 중간 추정에서 East +7.85 %, Ω coarse +14.02 % 였다. 서측 10480 적색이 124 공유차로→10483 진출→동측 역류를 만들었다"로 교체 |
| C8 | §2.1 4행 "근접 계수·허용오차·NUF 여유·φ_cd 같음 → 이것만으로 차이 설명 안 됨" | **확인** | `ca181e84`·`c20aff1d` `evaluation/parameters.json` :8 proximal 10.0, :18 objective_tolerance 1e-7, :25 nuf_cap_margin 100.0, :65 φ 1.0 같음 [실행 git show] | 없음. 다만 plant 는 다름(C9·§3) |
| C9 | §2.1 6행 δ_merge "W264 설정 0.3, 배포값 확인 안 함 / 우리 배포 FW_E 1.0 / 불명" [핵심] | **반박** | (1) 우리 설정에도 `config_overrides.network.metanet_delta_merge 0.3` 이 있음(`config_n31_v2.json:7441`) [실행]. 설정 층은 같음. (2) W264 plant manifest = `urban_area263/approaches_only/evidence/candidate_manifest.json`(결정 기록 `lane_plant_manifest_sha256 8ae93aa3…` = 동결본 파일 sha [실행]). 그 `parameters` = `selected/port_gain/parameters.json` FW_E δ 1.0(sha `bd743989…` 일치), 우리 BF FW_E 1.0 [실행]. (3) 그 `reference_config` = expanded036 `eval_036/reference_config.json`(sha `7f6df2d1…`, 결정 기록에 경로·sha 있음)이 `freeway.state_response.FW_E.cell_overrides` 에 δ_merge 셀10 3.530·셀12 5.089·셀21 4.212·셀23 2.211 을 둠 [실행 `VX/eval036_ref.json`]. ca181e84 harness 는 이를 plant 에 설치함(`canonical_harness.py:303-307,326`) [읽음]. 우리 `reference_config_n31_v2.json` 에는 state_response·physical_cell_fd 가 없음 [실행], c20aff1d harness 에 state_response 경로 없음 [실행 git grep] | "δ_merge: 설정 층 양쪽 0.3. plant 층 우리 = FW_E 1.0 균일. W264 = FW_E 1.0 + 합류 셀 4곳 2.2–5.1(expanded036 셀별 반응). W264 모형의 미터 '이득 경로'가 더 클 수 있음 [추론]". 결정 기록의 `freeway_state_response_enabled 0.0` 은 부모 설정 쪽 표시로 보임 [추론] |
| C10 | §2.1 7행 간격 노드 값, 그리고 "window264 에서 가장 많이 움직인 미터가 바로 10681·10484(각 49/61회 < 10)" | **값 확인 / 결론 반박** | 간격 노드 W264 4개(10639 2.5/1.5·10681 3.5/1.5·10490 1.5/1.5·10484 2/1.5), 우리 2개(10681 3.0/2.0·10484 2.5/2.5) [실행 `VX/findkey.py`]. 녹색 < 10 횟수: RM_C10480 55(g2–8)·10484 49·10681 49·10639 42·10490 16·10482/10644/10646 0 [실행 `VX/w264_meters.py`]. 검사 선택도 RM_C10480 조임 22/49 가 최다 [실행] | "동측(FW_E) 미터 중 가장 많이 움직인 것이 10681·10484(각 49/61). 전체로는 서측 RM_C10480 55/61". 간격 노드 가설의 근거로는 약해짐 [추론] |
| C11 | §2.1 2행 이웃 검사 내용, 1e-7 채택 (CX:542-631, PAR:18) | **확인** | `RC/work/ca181e84_sdmpc.py:542-604` 미터별·소유자별 묶음, 블록마다 직전 값 ±한도 안 최소/최대; `:600`·`:629` `objective < best − tolerance`; 호출 `:1166-1168` `policy['objective_tolerance']` [읽음]. 사본 sha `ccdbf44c…` [실행] | 덧붙임: 검사는 풀린 예산 후보마다 돎(`audit_meter_budget_candidates`). W264 에서 서로 다른 예산 2개가 54/55 결정 [실행] |
| C12 | W264 이웃 검사 예측 이득 "결정당 0.0001–1.46 veh·h" | **부분 수정(작음)** | 내 집계 2.79e-5–1.465, 중앙 0.026, 49회 중 15회 < 0.01 [실행 `w264_audit.jsonl`]. FW_E 묶음 조임은 1,800·1,950·2,100 s(이득 0.031·0.599·1.465)로 VSL 창 시작과 같은 때 [실행] | 하한을 "약 0.00003"으로. "FW_E 조임 선택은 VSL 창이 열린 1,800 s 부터" 한 줄 |
| C13 | d4 "window264 는 VSL90 시간창을 함께 켬, 시간별 누적 차는 창 시기와 겹침", VSL90 단독 −6.09/−6.15 % | **확인** + **보충** | README:9 seg13 1,800≤t<5,700 [읽음]. 누적 차(본선) 1,800 −0.5, 2,700 +8.7, 3,600 −24.3, 4,500 −98.0, 5,700 −206.9, 7,200 −249.8, 9,000 −261.2 [실행]. 이득의 약 70 %가 3,600–5,700 s, 약 21 %가 5,700 s 뒤 [실행 산술]. `REPRO_RESULT.md:22-23` −6.0866 %·−6.1531 % [읽음] | d4 에 "W264 는 도시 신호도 SDMPC 였고, NC 와 ALINEA 팔은 native 고정이었다. 도시 쪽만으로도 FW_E 가 같은 크기로 흔들림(METER_CAUSE d7)"을 더함 |
| C14 | d3 "64cf: 1099 수요 2.14배, DSD110 이 75–145 라 FW_E 자유속도 96.6 km/h(v3c3 111.3)" [핵심] | **측정 확인 / 인과 부분 수정** | 1099 는 **서측 입구**. FW_E 입구 1098 포함 나머지 33개 입력은 같음(`SP/cmp355/COMPARE_355_K8.md:52`, DSD 행 :59) [읽음]. DSD110 점 표: 64cf 75/95/100/115/130/145 (fx 0/.03/.10/.68/.91/1), v3c3 98/105/110/120/130/140 [읽음 두 inpx]. 평균 112.275 vs 117.97 km/h(차 5.7) [실행 산술; 64cf 값은 codex `BASELINE…:33` 과 같음]. 0–900 s 300→10,500 m 통행시간 385.3 vs 344.8 s(+11.7 %) [읽음 `phys/out_all.json`] → 측정 자유속도 차(약 14.7)가 DSD 평균 차보다 큼 | "FW_E 입구 수요는 같다. 64cf FW_E 가 느린 것은 DSD 차(평균 5.7 km/h 낮고 아래 꼬리 75 km/h)로 일부만 설명된다. 나머지는 미확인(경로 31–32개 차, 결정점 우회 20경로, VSL 표지 위치, 서측 대기의 124/10483 결합) [추론]"으로 |
| C15 | d5 "무제어 본선: 64cf-s29 2,249 … v3c3 1,817/1,964/1,877. 같은 seed31 에서 v3c3 무제어 1,817.0 이 stage1v2 미터 팔 1,888.9 보다 이미 낮음" | **부분 수정** | 값은 맞음 [실행 PHYS·CODEX; 1,888.9(PHYS 스캐너) vs 1,888.5(stage-1 scan.json)]. 그러나 수준 비교에 두 혼입: (1) 64cf 자유속도 차 — 자유주행 시간만 약 +11.7 %, v3c3-s31 기준 약 190 veh·h 규모 [추론, 산술]. (2) stage1 입구 구성 1(40 km/h 삽입) — stage1v2 NC·RM 모두 U 구간(0–4.2 km) 150분 혼잡, 혼잡 km·h 1.168/0.588 vs v3c3-s31 113분·0.457 [실행 `phys/out_all.json` zones; 읽음 INV_PHYSICS:159] | "기준선이 더 막혔다"의 근거는 TTT 수준 대신 대기 번짐 분(62 vs 〔가림: 봉인·블라인드 시드 값〕)과 구역 지체(INV_PHYSICS §6.2, §3.2)로 대기. 수준 비교 문장에 위 두 혼입을 적기 |
| C16 | d6 "codex ALINEA 코드로 우리가 돌린 런 v2 −13.17/−13.67, v3b −3.75/−9.71. 무제어가 덜 막힐수록 감소가 작아짐" | **확인** + 보충 | 산술은 INV_CODEX §4 와 같음 [읽음]. alinea 함수 본문 동일(C5) [실행]. 같은 꼴이 64cf 에도: 64cf-s23 NC 1,993.7 → −1.32 %, 64cf-s29 NC 2,249.7 → −11.81 % [실행 산술 rows]. 단 사다리 안에 입구 구성 변경(v3c2 에서 1098·1099 DSD40 → 구성 14)이 섞임 [읽음 INV_PHYSICS:159; 메모리 자료] | 64cf-s23 점을 근거에 더하고, 입구 구성 혼입을 한 줄로 |
| C17 | §2.2-4 "v3c1-s31 하이브리드(규칙 미터가 실제로 조임)에서 FW_E 본선 +72.2 veh·h(+3.4 %)" | **값 확인 / 해석 부분 수정** | `c20aff1d:diagnostics/worklog_20260930_1001/01_hybrid/final_compare.json` M1 2,109.2 → 2,181.4(+3.42 %) [실행 합산]. 같은 런에 Carlson MTFC-VSL(S4) + 도시 SDMPC 가 함께 [읽음 `HYBRID_DESIGN.md` §0]. 메모리 자료는 FW_E 악화를 VSL S4 가동 구간(2,250–4,650 s) 상류 대기로 봄, 사용자가 하이브리드 방향을 중단함 [읽음 메모리, 자료로만] | "규칙 미터 몫은 분리 안 됨(VSL·도시 동시)"을 붙이기. 규칙층 미터의 FW_E 근거로 쓰지 않기 |
| C18 | §2.1 8행 "codex ALINEA 최소 2 s, ±2 s/150 s" / "블록 0 상자 {8,9,10} 에서는 무관" | **근거 없음(최소 2 s)** / **범위 한정** | 푸시 자료에는 ±2 s·150 s·적녹 10 s, 2,700 s 예시 녹색 6/8/3/4 만 있음(`BASELINE…:16`) [읽음]; 최소 녹색 값은 못 찾음 [실행 git grep]. 우리 c20aff1d 에는 `allow_zero_green` 스위치가 없음(0 이 늘 표에 있음, PRB:133) [실행 git grep 0건]. codex 는 기본 True, W264 만 false [읽음 `ca181e84:evaluation/controllers/physical_ramp_branches.py:50`; 설정 `/actuation/real_world_ramp_metering/allow_zero_green`] | "최소 녹색: 푸시 자료에 없음(≤ 3 s 만 확인)". "무관"은 "지금처럼 10 에 고정일 때만". 이웃 검사를 이식하면 결정 몇 번 만에 0 에 닿을 수 있음(10→8→…→0) [추론] → §2.2·§4 O2·V2 에 녹색 0 처리 명시 필요(§2) |
| C19 | §4.2 V1 "window264 약 28시간(10-07 05:47 → 10-08 09:39)" | **확인** + 보충 | FZP 생성 10-07 05:49, 마지막 기록 10-08 09:39:25, 상태 10:07 [실행 파일 시각]. 첫 시도 `D:/VISSIM-runs-window264-s29-9000` 은 3,300 s 에서 watchdog 실패 [읽음 `native_status.json`, 동결본 `docs/WINDOW264_RESTART_20261007.md`] | "유효 런은 recovery 판. 첫 시도는 실패" 한 줄 |
| C20 | W264 = "ca181e84" (§2.1 머리) | **부분 수정(작음)** | 동결본 `D:/VISSIM-runtime-window264-recovery/sdmpc31_ca181e84_202610070539/FREEZE.json` git status 7항목(비커밋 수정 5: 설정 timeout 1800→0, 러너 ps1, watchdog ps1, VBS, 시험 + 새 파일 2) [읽음]. sdmpc.py·sdmpc_sequence.py·sdmpc_central.py·sdmpc_budget.py·physical_ramp_branches.py·parameters.json 은 ca181e84 와 같음(CRLF 제외) [실행 sha]. VBS 변경은 출력 캡처 안정화뿐 [실행 diff] | "ca181e84 + 실행 안정화 비커밋 수정(제어·plant 변경 없음). codex 에이전트가 이 PC 에서 작업 스케줄러로 띄움(`Codex-VISSIM-sd31-run-20261007054749115`)" |
| C21 | 커밋·브랜치 식별: d80faf99 = control-full-review 끝, 85e3454b·ca181e84 = sdmpc31-upstream, 9a8320ec = handoff 원격 head | **확인** | `git branch -r --contains`, `git ls-remote`(9a8320ec = `refs/heads/codex/sdmpc-plant-handoff-20261013`) [실행]. 날짜는 커밋 시각이며 푸시 시각은 모름 | "푸시일" → "커밋일" |
| C22 | "codex 문서 속 10 % 초과 FW_E 수치는 d80faf99 하나"(C2 정리) | **확인** | 원격 codex 8개 head + 9a8320ec 의 .md 에서 "−1x %"·East/FW_E/본선 검색: 표본 수 −14.5 % 한 줄 외 없음 [실행 git grep; 봉인 시드 줄 제외]. JSON 은 east_link_sets_source 만 확인 | 없음 |
| C23 | §2.1 3·5·9·11·12·13·14행(리더 후보 3 vs 1, tangent-v1·역방향·3블록, ALINEA 팔 VSL 없음·W264 VSL90 창, NC 2,249.69/2,248.98, 시드, Ω 7,263·701·635, RM 팔 원자료 codex PC) | **확인** | 설정 `/adapter/joint_owner_game/max_leader_candidates` 3 vs 1, `sdmpc_derivatives` 같음 [실행]. 팔 목록 none/rm/vsl/both [읽음 rows]. README:12 Ω701 [읽음]. 이 PC `D:/VISSIM_runs` 에 bottleneck90_rm 폴더 없음 [실행] | 없음 |

---

## 2. "차이는 나열 항목으로 설명된다"를 깨 보기

METER_CAUSE 의 흐름: codex 에서 미터가 움직인 것은 규칙 또는 이웃 검사. 우리는 둘 다 없음. 10 %가 안 보이는 것은 (a)+(c)+(d). 이 가운데 "이웃 검사"를 codex FW_E 이득의 설명으로 읽을 수 있는지 시험했습니다.

- **codex 의 이웃 검사 계보(모두 64cf-s29, codex 기록, 자료로만)** [읽음 `ca181e84:AGENTS.md`]
  - REVIEW219(10-05): "Optional bounded finite RM profile audit max20 … after SDMPC" 도입, 고정 VSL90 9,000 s 런(`:97`). 결과 Ω NC 7,263.267 → 10,833.631(+49.156 %), 오류 유지 30구간(`:61`). 10480·10681 이 g0(닫힘)에 머묾(`:59`).
  - REVIEW235: 풀린 예산마다 검사(`:57`). 런 233/235: 첫 결정 10681 g10→8(`:43`). 0–6,600 s 중간 추정 East +7.85 %(`:15`). 7,959 s 에 중단, 원인 10480 적색 → 124 차로 1 대기 → 10483 진출 막힘 → 동측 역류(`:13`).
  - REVIEW256–264: 124 공유 수신 수정(`:13`), 녹색 최소 2 s·0 금지·prehead 90 % 저장 guard(`:9,11`), 도시 17신호 저장 guard·40 좌회전 투영(`:7`), Ω635→701(`:5`), VSL 창 1,800–5,700 s(`:1`). 그 뒤 W264 가 본선 −11.61 % [실행].
- **결론**
  - 이웃 검사는 codex SDMPC 에서 미터를 움직인 **필요한 장치**였습니다(C4·C6) [읽음·실행].
  - 그러나 **충분하지 않았습니다.** 같은 검사가 켜진 codex 런에서 FW_E 는 나빠졌습니다(중간 +7.85 %). 나쁜 경로는 녹색 0 과 공유차로 역류였습니다 [읽음].
  - W264 의 −11.61 %에는 검사 외에 위 수정들, expanded036 plant(C9), 평평한 서비스 표(§3), VSL 창, 도시 SDMPC 가 함께 들어 있습니다. 몫을 나눌 자료는 없습니다 [추론].
  - 그래서 METER_CAUSE §2.1 1행의 "**핵심 차이**"는 "미터를 움직인 직접 장치"로 좁혀야 합니다. FW_E 이득의 설명으로 쓰면 반박됩니다.
- **우리 쪽에 주는 뜻** [추론]
  - §2.2-1·§4 O2·V2(이웃 검사 이식)는 녹색 0 처리를 정해야 합니다. c20aff1d 는 0 을 늘 허용합니다(C18). codex 219·233/235 의 실패 경로를 다시 밟을 수 있습니다.
  - O2 를 할 때 "0 허용/0 금지" 두 경우를 같이 보고, 10480 류 서측 미터가 124·10483 을 막는지도 봐야 합니다.

---

## 3. METER_CAUSE §2.1 표에 빠진 차이 (W264 설정 vs V-A 설정)

[실행 `VX/cfgdiff2.py` → `VX/cfgdiff2.txt`, 186키. 아래는 미터·FW_E 와 닿는 것만]

| 항목 | W264 (`ca181e84:…/vsl_window264/config.json`) | 우리 V-A (`c20aff1d:…/config_n31_v2.json`) | 뜻 |
|---|---|---|---|
| plant manifest | `urban_area263/approaches_only/evidence/candidate_manifest.json`: parameters = expanded036 `port_gain`, reference = `eval_036`(셀별 FD·반응) | `plant_n31_v2.json`: parameters = BF, reference = `reference_config_n31_v2.json` | 미터 이득 경로 모양이 다름(C9) [읽음; 효과 추론] |
| 램프 서비스 표(대/주기/차로) | 동측 4개 모두 명시: g2 1.0 … g8 4.0, g9 4.2, g10 4.2 → g8 = g10 의 95 %, g9 = g10 | 10490 만 명시(g8 3.24, g9 3.69, g10 4.2), 나머지 기본(METER_CAUSE a4 의 g8 3.24) → g8 = 77 %, g9 = 88 % | W264 모형에서 첫 조임의 램프 대가가 훨씬 작음 [실행 비율; 효과 추론] |
| 녹색 0 / 저장 guard | `allow_zero_green false`, `storage_release_guard` 0.9 | 키 없음(0 허용, guard 없음) | §2 의 실패 경로와 직결 |
| 간격 노드 | 4개(C10) | 2개 | METER_CAUSE 에 있음 |
| v_free(설정) | 120 | 110 | — |
| VSL | 집합 50–110, 구역 머리 [0,2,5,10,13,15], 고정 창(최적화 안 함) | 집합 80–110(단일값 81/91/101), 머리 [0,5,10,15], 최적화 | METER_CAUSE 9행은 창만 적음 |
| 도시 신호 | SDMPC(ALINEA 팔·NC 는 native 고정) | SDMPC | ALINEA −11.81 %는 도시 native, W264 는 도시 SDMPC. 같은 비교가 아님 |
| Ω | 701 (ALINEA 시기 codex Ω 7,263 기준) | 635 | METER_CAUSE 13행에 있음 |
| 망 | 64cf `64cf5f55…`(결정 기록 경로 `native_seed29.inpx`) | v3c3 `3de889f0…` | METER_CAUSE 10행에 있음 |

---

## 4. 정확한 고침 문구 (METER_CAUSE 에 넣을 것)

1. §0.5 끝에 덧붙임: "W264 −11.61 % 는 codex 가 분석·보고한 적이 없고 2026-10-24 이 조사에서 처음 계산했다. codex 푸시 자료의 10 % 초과 숫자는 d80faf99 의 −11.81 %(본선 7링크) 하나다. codex 문서상 사용자가 10-01 지목한 그림의 동측 영역은 국소 19링크이고 그 값은 −8.90 %다."
2. §0.6 둘째·셋째 문장 교체: "codex SDMPC 는 g10 에서 시작한 기록 상태에서 이웃 검사 없이 g10 에 머물렀다(이어받은 녹색이 낮으면 그 값을 유지한 기록도 있음, 64cf-s47). 우리 V-A SDMPC 경로에는 규칙 미터도 이웃 검사도 없다. 규칙 ALINEA 코드는 c20aff1d 에 있다."
3. §2.1 1행 "(a) 핵심 차이" → "(a) 미터를 움직인 직접 장치. FW_E 이득의 충분조건은 아님(같은 검사 계보에서 FW_E 악화, §VERIFY 2)".
4. §2.1 6행 교체: "δ_merge: 설정 층 양쪽 0.3. plant 층 우리 FW_E 1.0 균일 / W264 FW_E 1.0 + expanded036 셀별 반응으로 셀10·12·21·23 에 3.53·5.09·4.21·2.21."
5. §2.1 7행 끝 교체: "W264 녹색 < 10 횟수는 서측 RM_C10480 55/61 이 최다, 동측 안에서는 10681·10484 각 49/61."
6. §2.1 8행: "codex ALINEA 최소 녹색: 푸시 자료에 없음." "블록 0 상자에서는 무관" 뒤에 "(지금처럼 10 고정일 때만. 이웃 검사를 이식하면 0 에 닿을 수 있고, c20aff1d 는 0 을 막는 스위치가 없다)".
7. §2.1 끝 문단의 "+7.85 %" 문장 교체: C7 의 교체 문구.
8. §2.1 표에 §3 의 빠진 행(plant manifest·서비스 표·녹색 0/guard·v_free·VSL 집합/구역·도시 신호)을 더함.
9. d3 교체: C14 의 문구. d4 에 C13 의 도시 신호 문장. d5 에 C15 의 두 혼입. d6 에 64cf-s23 점과 입구 구성 혼입.
10. §2.2-4 에 "같은 런에 Carlson VSL·도시 SDMPC 가 함께라 규칙 미터 몫은 분리 안 됨".
11. §4 O2·V2 조건에 "녹색 0 허용/금지를 명시하고 두 경우 모두 본다" 추가.
12. §5 Q1 의 (i)·(ii) 설명을 1번 문구에 맞춤.

---

## 5. 한 것·안 한 것·산출물

- 한 것 [실행]: git show·grep·ls-tree·ls-remote, 설정 JSON 평탄 비교, W264 action CSV·결정 JSON 55개에서 이웃 검사 행 추출(읽기만, 약 80 s), 기존 스캔 JSON 재계산, inpx DSD 점 읽기, 파일 시각·sha 확인.
- 9a8320ec 읽기: 임시 bare 저장소 `D:/VISSIM-merge/k8_gate_trees/rmcause/verify_cx_remote.git`(alternates, 기존 ref 무변경)로 받아 읽고 지움 [실행; LOG 에 기록].
- 안 한 것: 새 VISSIM 런·COM·러너·동결·결정/plant 재생·커밋·푸시·기존 워크트리 체크아웃·kill 0. 금지 시험 0. 봉인 시드 폴더·자료 열람 0. v3c3·v3c1 규칙 RM 팔 결과 열람 0.
- 디스크: 시작 C 32.2 GB, D 343.8 GB 여유 [실행].
- 산출물(전부 RC 아래):
  - 이 문서 `RC/VERIFY_codex-compare.md` (sha256 은 LOG 마지막 항목).
  - `VX/` 추출물: `els.json`(1f21247e…), `w264_cfg_git.json`(e93e627a…), `ours_cfg.json`(c8e3ee2c…, 동결본과 같음), `cfgdiff2.py`(54fffb74…)·`cfgdiff2.txt`(446609e7…), `w264_audit.py`(e7b102d3…)·`w264_audit.jsonl`(7a190498…), `w264_meters.py`, `findkey.py`, `eval036_ref.json`(7f6df2d1…), `ours_ref.json`, `w264_port_gain_params.json`(bd743989…), `ours_bf_params.json`(8e4f6047…), `hybrid_final_compare.json`(968b280e…), `dp_c20aff1d.py`·`dp_d80faf99.py`, `vbs_git.txt`·`vbs_frozen.txt`, `d80_vsl90_s29_east_heatmap.png`.
