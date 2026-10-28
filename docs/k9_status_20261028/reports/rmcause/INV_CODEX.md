# INV_CODEX — codex 버전 추적: "미터가 움직여 FW_E 가 10% 넘게 줄었다"는 버전은 어디인가 (2026-10-24 KST)

질문(D-K9-73): "옛날에 코덱스가 깃허브에 푸시한 버전에서는 미터가 작동해서 FW_E 가 10% 넘게 개선됐는데, 지금은 아니다. 미터 원인 규정부터."
이 문서는 그중 **codex 쪽 고고학**만 다룹니다. 우리 컨트롤러 내부 원인은 다른 조사(INV_OURS·INV_PHYSICS·INV_PRIOR)의 몫입니다.

줄임말: RM = 램프 미터. ALINEA = 합류 하류 점유율을 목표값에 맞추는 되먹임 규칙 미터. SDMPC = 스타켈버그 분산 모형예측제어(우리·codex 컨트롤러). VSL = 가변 제한속도. TTT = 총 통행시간(veh·h). Ω = 목적함수 영역 링크 집합. NC = 무제어 런. FZP = VISSIM 차량 궤적 기록. DSD = 희망속도 결정점. 본선 7링크 = 동측 본선 링크 2·24·74·119·10613·10699·10702(우리 지표 ①). 국소 19링크 = 본선 7 + 동측 진입 커넥터 4 + 진출 커넥터 4 + 진입 접근로 4(우리 지표 ②).
태그: [실행] 내가 돌림, [읽음] 코드·자료·문서를 읽음, [추론] 시험 안 한 판단.
시드 표기는 망 접두어를 붙입니다(64cf-s29, v2-s31, v3c3-s31 …). 봉인 시드 37/59/61/67 자료는 열지 않았고 그 수치를 쓰지 않았습니다.

---

## 0. 결론 (먼저)

1. **codex 가 푸시한 자료에서 FW_E 10% 넘는 감소 수치는 딱 하나 찾았습니다.** [읽음]
   - 커밋 `d80faf99`(브랜치 `codex/control-full-review-20260909`, 2026-09-24 푸시) 파일 `diagnostics/vsl_handoff_20260924/evidence/accounting/east_link_sets_source.json` 의 `rows[5]`.
   - **64cf-s29, ALINEA 규칙 RM, 동측 본선 7링크 2249.69 → 1984.08 veh·h(−265.61, −11.81 %)**. 국소 19링크는 −8.90 %.
   - 미터 논리는 MPC 가 아니라 **규칙 ALINEA**(8개 미터, 150 s 갱신, 10 s 적·녹, 녹색 변화 ±2 s)입니다 [읽음 `85e3454b:diagnostics/sdmpc_n31_20260924/integration_20260926/BASELINE_REPRODUCTION_GATE_20260929.md:16`].
   - 같은 실험에서 Ω TTT 는 7263.267 → 7600.425(+4.64 %), 망 전체+미삽입 대기는 28944.770 → 30806.576(+6.43 %)입니다 [읽음 같은 파일 `:20,22`]. 같은 파일 64cf-s23 ALINEA 는 본선 −1.32 % 입니다 [읽음 `rows[1]`].
2. **codex SDMPC 버전에서 미터가 실제로 움직인 런도 이 PC 에 하나 있습니다.** [실행]
   - codex 커밋 `ca181e84`(`codex/sdmpc31-upstream-20260926`, 2026-10-06 푸시)의 `vsl_window264/config.json` 을 이 PC 에서 돌린 런입니다(10-07~10-08). 폴더 `D:/VISSIM-runs-window264-s29-9000-recovery-20261007`.
   - codex 상태 파일은 `requested_native_arms_complete_unanalyzed`(미분석)입니다 [읽음 `native_status.json`].
   - 내가 FZP 를 읽어 짝 무제어(64cf-s29 none)와 비교했습니다. **본선 7링크 2248.98 → 1987.79(−261.19, −11.61 %)**. 900 s 전 FZP 행 431,233개의 sha256 이 두 런에서 같습니다(짝 성립) [실행 `codex_scan/out/*.json`].
   - 단 이 런은 **VSL90 시간창(FW_E seg13, 1800–5700 s)과 도시 신호 SDMPC 를 함께** 켰습니다. 미터 몫만 떼어낼 수 없습니다 [읽음 `ca181e84:diagnostics/repin_v3c3_review_20261001/vsl_window264/README.md:8-12,24`].
3. 둘 다 **64cf 망·64cf-s29 한 시드**입니다. 64cf 의 서측 입구 1099 수요는 v3c3 의 평균 2.14배입니다 [읽음 `cmp355/COMPARE_355_K8.md:34,52`]. 무제어 본선 TTT 도 64cf-s29 2249 로, v3c3 NC 1817/1964/1877 보다 큽니다 [읽음 `k92/va/analysis/VA_REPORT.md:218,240,262`].
4. **codex 의 ALINEA 코드를 그대로 써서 우리가 돌린 규칙 RM 런**도 10% 를 넘었습니다. v2-s31 −13.17 %, v2-s41 −13.67 %. 그러나 망을 v3b 로 바꾸자 −3.75 %, −9.71 % 로 줄었습니다 [실행 stage-1 scan.json 합산]. v3c1·v3c3 의 같은 규칙 RM 팔(s31·s41)은 돌았지만 **열지 않았습니다**(GB-13 관행, §6 Q1).
5. codex 의 다른 SDMPC 버전들은 미터를 움직이지 않았거나(8개 모두 g10), FW_E 가 늘었습니다(+7.85 %, +7.84 %) [읽음 §2 표 행 5·6].

---

## 1. 범위와 방법

- 원격 codex 브랜치 8개와 로컬 ref 를 대조했습니다. 원격 `codex/sdmpc-plant-handoff-20261013` 은 로컬 ref(`ffa4861e`)보다 새 커밋 `9a8320ec`(10-23)가 있었습니다 [실행 `git ls-remote`]. 기존 저장소 ref 를 바꾸지 않으려고 별도 bare 저장소(`D:/VISSIM-merge/k8_gate_trees/rmcause/codex_remote.git`, alternates 사용)로 받았고, 끝난 뒤 지웠습니다 [실행].
- codex 문서·AGENTS.md·CLAUDE.md 는 자료로만 읽었습니다. 숫자는 원 JSON·CSV 나 FZP 로 다시 확인할 수 있는 것만 표에 넣었습니다.
- 새 VISSIM 런, COM, 러너, 동결, 커밋, 푸시, 기존 워크트리 체크아웃 = 0 [실행].
- FZP 읽기 스캔 1개 사슬만 돌렸습니다. WMI 분리, BELOW_NORMAL, `PYTHONHASHSEED=0`, `python -B`. 대상 3개(window264, 64cf-s29 none, v2-s31 NC 검산). 결정·plant 재생은 아닙니다 [실행 `codex_scan/chain.ps1`, `codex_scan/logs/chain.log`].
- 스캔 도구 검산: v2-s31 NC 본선 7링크 2175.04(사다리꼴) = stage-1 `scan.json` 2175.0 [실행]. 64cf-s29 none 2248.98(사다리꼴)·2249.33(직사각+끝 보유) 대 codex 2249.69, 차 0.016 % [실행·읽음].

---

## 2. 후보 버전 표

| # | 버전(커밋·브랜치·푸시일) | 미터 논리 | 망·수요 | 기준선 | 지표 | FW_E 변화 (주장/계산) | 근거 위치 | 로컬 자료로 숫자 재현? |
|---|---|---|---|---|---|---|---|---|
| 1 | `2c444774` (09-16, control-full-review 계열) | 고정 명령 시험(RM10490 g8→6→4 등) | 사용자 수정망, 1098만 ×0.8(east080), seed23/33 | 같은 시드 NC, 짧은 창 | 동측 본선 TTT(창) | 197.2308 → 193.3385(−1.97 %) | `docs/HANDOFF_20260916_geometry_actuator_response.md:76` [읽음] | 아니오. 런 폴더 이 PC 에 없음 [실행 `D:/VISSIM_runs` 목록] |
| 2 | `342c8699` (09-19, 우리 계보의 조상) | 규칙 ALINEA(목표 점유율 15 %, 이득 70, 최소 녹색 2 s, ±2 s/150 s, 적·녹 10 s) | 사용자 수정 램프 DSD 망, seed 13, DSD120, 0–3000 s | 같은 시드 NC | 동측 본선 TTT 900–3000 s | −20.28 veh·h(−4.65 %). Ω −0.21 % | `diagnostics/demand_sweep/ramp_dsd_20260916_v2/rules_v1/REPORT.md:3-8,33` [읽음] | 아니오. 런 폴더 없음 [실행 목록] |
| 3 | `00abbabe` (09-22, control-full-review 계열; 우리 계보의 조상) | 규칙 ALINEA 8개(위와 같은 값) | 86af FW80/U90, DSD120, 1099 v1(미삽입 10,725대), 86af-s23, 9000 s | NC 재사용(900 s 전 FZP 행 sha 같음 주장) | codex `TTT_FW_E` | 2044.93 → 1912.28(−132.64, **−6.49 %**). Ω −0.86 % | `diagnostics/control_comparison_20260922/README.md:5,40`, `performance.csv` [읽음] | 예(FZP 있음): `D:/VISSIM_runs/20260922_fw080_urban090_controls/rm/run`, NC `D:/VISSIM_runs/20260922_both_off_half/fw080_urban090_nc9000/run`. 이번엔 다시 세지 않음 |
| 4 | **`d80faf99`** (09-24, `codex/control-full-review-20260909` 끝) + 설명 `85e3454b`(10-04) | **규칙 ALINEA 8개**, 150 s, 적·녹 10 s, ±2 s. 동측 첫 제한 10484=1350, 10639=1500, 10681=1950, 10490=2100 s. 목표·이득 값은 푸시 문서에서 못 찾음 | **64cf**(E80/W80/U90, 입구 DSD110, 1099 v1), 9000 s | 같은 시드 NC | 동측 본선 7링크 / 국소 19링크 / Ω / 전체+미삽입 | **64cf-s29: 본선 2249.69 → 1984.08(−11.81 %)**, 국소 −8.90 %, Ω +4.64 %, 전체+미삽입 +6.43 %. 64cf-s23: 본선 −1.32 % | `d80faf99:diagnostics/vsl_handoff_20260924/evidence/accounting/east_link_sets_source.json` `rows[1]`,`rows[5]` ; `85e3454b:…/BASELINE_REPRODUCTION_GATE_20260929.md:13-25` ; `…/CALIBRATION_DATA_SCOPE_20261001.md:18` [읽음] | NC 는 예(`D:/VISSIM_runs/vsl_repro_s29/none`, 내 스캔 2248.98). **RM 팔은 아니오** — 원 자료가 codex PC(`C:\Users\alsrj\…\dsd110_20260923`)에만 있음 [읽음 `data_catalog.json`]. 새 VISSIM 런 없이는 재현 불가 |
| 5 | `85e3454b`~`26569d54` (10-04, sdmpc31-upstream) codex SDMPC closedloop9000 | SDMPC(가격·접선 미분). RM 유한차분 연결(`meter_activation_secant`, 기본 꺼짐) 시험 | 64cf-s29 | NC | Ω, 전체 | 3600 s 상태에서 **선택 RM 8개 모두 g10**. 9000 s 런 Ω +4.894 % | `85e3454b:…/rm_nonselection_live_20260929/METER_ACTIVATION_RESULT.md:20,42` [읽음] | 아니오. 런은 codex PC |
| 6 | `9a8320ec` 안 codex 기록(10-04 이후 SDMPC 9000 s 런들) | SDMPC | 64cf-s29 | NC | Ω coarse, East | East 1794.46 → 1935.31(**+7.85 %**), 다른 기록 1911.75 → 2061.61(+7.84 %) | `9a8320ec:AGENTS.md:19,272` [읽음] | 아니오. 런은 codex PC |
| 7 | **`ca181e84`** (10-06, `codex/sdmpc31-upstream-20260926`) `vsl_window264` 설정. **이 PC 에서 10-07~08 실행** | SDMPC `central-pfo-cap-v3` + **`sdmpc_meter_neighbor_audit: true`**(±2 s 유한 미터 후보를 전체 모형으로 다시 채점), RM 최소 녹색 2 s·변화 ±2 s, VSL90 시간창 고정 | 64cf(sha 64cf5f55), 64cf-s29, 9000 s, Ω701 | codex 기준선 없음(미분석). 내가 64cf-s29 none 과 짝지음(900 s 전 sha 같음) | 동측 본선 7링크 등(내 스캔) | **본선 2248.98 → 1987.79(−11.61 %)** [실행]. 국소 19링크 −5.46 %. 동측 진입 커넥터 +39.79, 진입 접근로 +101.04 veh·h. 전체+미삽입 28944.770 → 28305.698(−2.21 %) [실행 native 성능 JSON 계산] | `D:/VISSIM-runs-window264-s29-9000-recovery-20261007/sdmpc/…` ; 설정 `ca181e84:…/vsl_window264/config.json`(동결본과 `decision_timeout_sec` 한 줄만 다름) [실행 diff] | **예**(FZP·결정·readback 모두 로컬). 이번에 계산함 |
| 8 | `ffa4861e`(10-13)·`9a8320ec`(10-23) 355 인계 | SDMPC 공동/영역 모드, RM 2–10 s(0 금지), 유한 RM 이웃·조합 검사 | 64cf-s29, 0–8100 s, Ω701 | — | — | FW_E 개선 주장 없음. 스스로 성능·보정 미자격 | `ffa4861e:docs/sdmpc_plant_20261013/README.md:9-19,50` ; `9a8320ec:docs/sdmpc_vsl_20261023/README.md` [읽음] | 아니오. 런은 codex PC(E:) |

---

## 3. 버전별 세부

### 3.1 d80faf99 의 −11.81 % (codex 문서 안의 유일한 10% 초과 수치)

- 실험 이름은 codex PC 의 `dsd110_20260923` 결과 묶음입니다. 팔은 none / rm(ALINEA) / vsl(규칙 VSL) / both 네 개, 시드 23·29 입니다 [읽음 `east_link_sets_source.json` `source_sha256`·`rows`].
- 64cf-s29 rm 행: 본선 −265.61 veh·h(−11.81 %), 국소 −8.90 %, 확장(진출 수신 링크 포함) −10.63 %. 동측 삭제 2대 [읽음 `rows[5]`].
- 같은 행에서 동측 진입 커넥터 TTT 126.63 → 165.52, 진입 접근로 63.14 → 84.07 veh·h 로 늘었습니다 [읽음 `rows[4]`,`rows[5]`]. 본선에서 줄인 대기 일부가 램프로 옮겨 간 꼴입니다.
- 64cf-s23 rm 행은 본선 −1.32 %, 국소 +0.13 % 입니다 [읽음 `rows[1]`]. 같은 규칙이 시드에 따라 크게 달랐습니다.
- codex 스스로 "RM 순이득 누락"을 다음 과제로 적었습니다 [읽음 `d80faf99:diagnostics/vsl_handoff_20260924/README.md:82`].
- 10-01 에 사용자가 다시 지목한 그림이 이 실험의 `bottleneck90_rm_20260924/results/east_heatmap.png` 입니다 [읽음 `85e3454b:…/CALIBRATION_DATA_SCOPE_20261001.md:3`]. 그림·FINAL_REVIEW.md 는 푸시되지 않았고 이 PC 에 없습니다 [실행 폴더 검색 0건].
- 명령 전달 경로(같은 계열 ALINEA 런 기준): 150 s 마다 VBS 러너가 `fast_fixed_profile.py --rule-step` 를 부르고, 규칙이 1초 단위 GREEN/RED 사건을 `fixed_events.csv` 에 씁니다. VBS 가 COM 으로 미터 SC 9101–9108 SG1 의 `SigState` 를 쓰고 되읽어 확인합니다 [읽음 `c20aff1d:diagnostics/fast_fixed_profile.py:175-251`, `evaluation/controllers/diagnostic_profile.py:227-251`, `diagnostics/fast_nc_runner.vbs:368-376,420`]. 이 세 파일은 우리 head 에도 같은 바이트로 있습니다(규칙 RM 의 핀 sha `03c9567f…` = c20aff1d 파일) [실행 sha256].

### 3.2 window264 (codex SDMPC 에서 미터가 움직인 런)

- 미터 녹색(초, 결정 61회 중 10 미만 횟수) [실행 action csv 집계]: RM_C10639 42회(g4–g8), RM_C10681 49회(g2–g9), RM_C10484 49회(g2–g9), RM_C10490 16회(g3–g8), 서측 RM_C10480 55회(g2–g8). RM_C10482·10644·10646 은 늘 g10.
- 요청은 VISSIM 에 닿았습니다. 미터 readback 12,869행 모두 `ok=1`. RED 쓰기: SC9101 1,674, SC9105 1,263, SC9106 1,483, SC9107 491, SC9108 1,471 [실행 `signal_readback.csv`].
- 미터를 움직인 것은 **유한 미터 이웃 검사**입니다. 검사가 돈 결정 55회 중 49회가 기준 대신 미터 후보를 골랐습니다(RM_C10480 조임 22, RM_C10681 조임 6·풀기 4, FW_E 전체 조임 3, …). 예측 이득은 결정당 0.0001–1.46 veh·h 로 작았습니다 [실행 `action_*.json` `metadata.joint_leader_selection.meter_neighbor_audit` 집계].
- 이 검사(`meter_neighbor_audit`)는 `ca181e84` 에서 처음 들어왔고, `meter_activation_secant` 는 `85e3454b` 에서 들어왔습니다. **우리 c20aff1d 에는 둘 다 없습니다** [실행 `git log -S`, `git grep` 0건]. 코드 위치 `ca181e84:evaluation/controllers/sdmpc.py:1151-1168,1219` [읽음].
- 시간별 누적 차(window264 − none, 본선 7링크): 1800 s −0.5, 3600 s −24.3, 5700 s −206.9, 7200 s −249.8, 9000 s −261.2 veh·h [실행 150 s 칸]. VSL 창(1800–5700)과 미터 조임이 같은 시기라 둘을 나눌 수 없습니다.
- 참고: 같은 시드에서 VSL90 만(900–9000 s 고정) 켠 codex 런의 본선 변화는 −136.93 veh·h(−6.09 %) 입니다 [읽음 `D:/VISSIM_runs/vsl_repro_s29/REPRO_RESULT.md` 표]. 창 길이가 달라 window264 의 VSL 몫으로 그대로 빼면 안 됩니다 [추론].

### 3.3 codex 다른 SDMPC 버전

- `502168d4`(09-20)·`5fdfabde`(09-22) 계열 SDMPC 를 우리가 처음 native 로 돌렸을 때(21셀 lane plant 시나리오) 첫 결정은 미터 8개 모두 천장이었습니다 [읽음 메모리 `vissim-sdmpc-native-state-20260923.md`, 자료로만].
- 85e3454b 의 codex 기록: 3600 s 상태에서 g9/g10 평탄 구간 때문에 RM 미분이 0, 유한차분 연결을 넣어도 최종 선택은 8개 모두 g10 [읽음 `METER_ACTIVATION_RESULT.md:3-20`].

---

## 4. 우리 런 중 codex ALINEA 코드를 쓴 것 (망 사다리)

모두 stage-1 처방(codex 86af-s23 규칙 폴더에서 만든 ALINEA: 목표 15 %, 이득 70/140, 최소 255.6/511.2 veh/h)입니다 [읽음 `D:/VISSIM_runs/20260923_stage1/README.md:16-21`]. 지표는 같은 stage-1 스캐너, 프레임 5.1–8995.1 s 적분입니다.

| 망-시드 | NC 본선 7링크 | RM 본선 7링크 | 본선 변화 | Ω 변화 | 동·서 램프 8개 TTT 변화 | FW_W 본선 변화 | 근거 |
|---|---:|---:|---:|---:|---:|---:|---|
| v1-s31 | 2143.3 | 1877.2 | −266.1 (−12.42 %) | +68.7 (+0.97 %) | +90.1 | +353.8 | [실행 `20260923_stage1/s31_{nc,rm}/analysis/scan.json`] |
| v1-s41 | 2448.3 | 1867.2 | −581.0 (−23.73 %) | −23.9 (−0.32 %) | +166.9 | +559.3 | [실행 같은 꼴] |
| v2-s31 | 2175.0 | 1888.5 | −286.5 (−13.17 %) | +328.3 (+4.62 %) | +152.4 | +608.2 | [실행] |
| v2-s41 | 2176.0 | 1878.5 | −297.4 (−13.67 %) | +455.7 (+6.39 %) | +147.6 | +746.4 | [실행] |
| v3b-s31 | 1925.8 | 1853.5 | −72.3 (−3.75 %) | +293.4 (+4.21 %) | +128.3 | +347.9 | [실행 `20260925_v3b/s31_v3b{nc,rm}/analysis/scan.json`] |
| v3b-s41 | 2139.2 | 1931.4 | −207.8 (−9.71 %) | +71.4 (+0.98 %) | +97.9 | +317.6 | [실행] |
| v3c1-s31/s41 | — | — | 열지 않음 | | | | 런 있음 `D:/VISSIM_runs/20260927_v3c1/s{31,41}_v3c1rm` [실행 목록] |
| v3c3-s31/s41 | 1816.6 / 1963.8 | — | 열지 않음 | | | | NC 값 [읽음 `VA_REPORT.md:218,240`]; RM 런 있음 `D:/VISSIM_runs/20261001_v3c3/s{31,41}_v3c3rm`(결정 54개씩) [실행 목록] |
| (참고) v3c1-s31 하이브리드 | 2109.2 | 2181.4 | +72.2 (+3.42 %) | −186.5 | | | Carlson VSL + 다른 ALINEA 목표. [실행 `c20aff1d:diagnostics/worklog_20260930_1001/01_hybrid/final_compare.json` 합산] |

- v2 RM 팔에서 동측 미터는 실제로 깊게 조였습니다. v2-s31: RM_C10639 36/54회 10 미만(그중 g2 30회), RM_C10681 38회, RM_C10490 31회, RM_C10484 30회. 서측 4개는 늘 g10 [실행 `decision_*.json` 집계]. 실제 쓰기 검증도 통과했습니다(`fixed_validation.json` passed, readback 4,058) [실행].
- 무제어 본선 수준이 망마다 다릅니다: 64cf-s29 2249, v2 2175/2176, v3b 1926/2139, v3c3 1817/1964/1877 [실행·읽음]. 규칙 RM 팔의 본선 수준은 1854–1984 로 비슷했습니다(64cf-s29 1984, v2 1889/1879, v3b 1854/1931) [실행·읽음].

---

## 5. 네 층으로 나누기 (codex 쪽 증거만)

- **(a) 결정층 — 컨트롤러가 다른 미터를 요청하는가.**
  - codex 의 10% 초과 두 사례는 요청이 나왔습니다. 하나는 규칙 ALINEA(Ω 손익을 보지 않고 점유율로 조임), 하나는 SDMPC + 유한 미터 이웃 검사입니다 [읽음·실행 §3].
  - codex SDMPC 도 이웃 검사 없이는 8개 모두 g10 이었습니다 [읽음 §2 행 5].
  - 우리 c20aff1d 에는 이웃 검사도, 활성화 secant 도 없습니다 [실행 git grep]. V-A·J1 여섯 런 61회 모두 미터 명령이 900 vph·10 s 로 같았습니다 [읽음 `VA_REPORT.md:153,563,572`]. 이 차이는 결정층 쪽 후보입니다 [추론: 우리 런에서 이웃 검사를 켜 본 적은 없음].
- **(b) 작동층 — 요청이 VISSIM 에 닿는가.**
  - codex 의 두 경로(규칙 VBS, SDMPC 어댑터) 모두 RED 가 실제로 써졌고 readback 이 맞았습니다 [실행 §3.2, §4]. codex 쪽에서 작동층 문제의 증거는 없습니다.
- **(c) 물리·수요층 — 미터가 바뀌어도 FW_E 에 안 듣는가.**
  - 같은 규칙 ALINEA 가 v2·v3b 망에서는 본선을 줄였습니다(−3.75 % ~ −13.67 %) [실행 §4]. 그러니 적어도 v3b 까지 VISSIM 의 FW_E 는 미터에 반응합니다.
  - v3c3 망에서 같은 규칙의 효과는 **아직 모릅니다**. 답이 될 런(v3c3 RM 팔 s31·s41)은 있지만 열지 않았습니다(§6 Q1).
- **(d) 비교층 — 이득이 망·수요·기준선·지표에 달렸는가.**
  - 10% 초과 수치는 모두 **본선 7링크 하나의 지표**입니다. 같은 런에서 국소 19링크는 −8.90 %(ALINEA), −5.46 %(window264)로 작고, Ω 나 전체+미삽입은 ALINEA 에서 늘었습니다(+4.64 %, +6.43 %) [읽음·실행].
  - 64cf-s29 한 시드입니다. 같은 규칙이 64cf-s23 에서는 −1.32 % 였습니다 [읽음].
  - 64cf 는 1099 수요가 v3c3 의 약 2.14배이고 경로·DSD 도 다릅니다 [읽음 `COMPARE_355_K8.md:34,52`]. 무제어 본선도 v3c3 보다 많이 막혀 있습니다(2249 대 1817–1964) [실행·읽음].
  - 우리 망 사다리에서 무제어 본선이 덜 막힐수록 규칙 RM 의 본선 감소가 작아졌습니다(v2 → v3b) [실행]. v3c3 NC 본선(1817/1964)은 이미 규칙 RM 팔 수준(1854–1984)에 가깝습니다. 그래서 v3c3 에서는 **미터로 줄일 본선 대기 자체가 작을 수 있습니다** [추론, 시드 2개씩·v3c3 RM 미개봉].

---

## 6. 열린 질문

- **Q1. v3c3 규칙 RM 팔(v3c3-s31·s41)을 열어도 되는가.** 열면 (c)·(d) 를 바로 가릅니다(같은 ALINEA 가 v3c3 에서 본선을 몇 % 줄이는지). 지금은 GB-13 관행("v3c1 RM/NC 900 s 전 바이트 동일 확인 뒤 연다")에 따라 닫혀 있습니다 [읽음 `D:/VISSIM_runs/20261001_v3c3/reports/k7/K7_GB_J1_PREDECLARATION.md:343-348`, `c20aff1d:diagnostics/sdmpc_n31_20260924/REPIN_V3C3_REPORT.md:169`]. 사용자 결정이 필요합니다. v3c1 RM 팔도 같은 처지입니다.
- Q2. 사용자가 기억하는 "10% 넘게"가 어느 것인가. 후보는 (i) d80faf99 의 64cf-s29 ALINEA −11.81 %(그림 east_heatmap), (ii) 이 PC 에서 돈 window264 −11.61 %(codex 미분석), (iii) 우리 stage-1 v2 의 −13 % 대입니다. 셋 다 본선 7링크 지표입니다.
- Q3. window264 에서 미터 몫과 VSL 창 몫을 나누려면 같은 설정에서 이웃 검사만 끈 짝 런이 필요합니다. 새 런이라 이번 범위 밖입니다.
- Q4. d80faf99 64cf-s29 ALINEA 의 목표 점유율·이득 값은 푸시 문서에서 못 찾았습니다. 원 `settings.json` 은 codex PC 에만 있습니다.
- Q5. 지금 이 PC 에서 다른 프로세스가 codex `9a8320ec` 동결본을 돌리고 있습니다(PID 35780, `D:/VISSIM_runtime/20261023_rolling_cea/frozen/sdmpc31_9a8320ec_…`, 출력 `D:/VISSIM_runs/20261023_rolling_cea/ttt_only_s29_8100`). 내 것이 아니라 건드리지 않았습니다 [실행 프로세스 목록].
- Q6. 우리 stage-1 RM_GAIN_TRACE(`c20aff1d:diagnostics/sdmpc_n31_20260924/RM_GAIN_TRACE_20260924.md`)의 −374 등 숫자는 봉인 시드 37 이 섞인 평균이라 인용하지 않았습니다. 기구 설명(B2 대기를 붙잡아 B1 방류를 늘림, 대가는 램프 대기와 FW_W 역류)만 참고할 수 있습니다.

---

## 7. 산출물

- 이 문서: `scratchpad/k8/rmcause/INV_CODEX.md`
- 스캔 도구·결과: `scratchpad/k8/rmcause/codex_scan/cx_scan.py`, `jobs.txt`, `chain.ps1`, `out/cf_s29_window264.json`, `out/cf_s29_none.json`, `out/st1v2_s31_nc.json`, `logs/chain.log`
- sha256 은 LOG.md 마지막 항목과 반환값에 적었습니다.
- 지운 것: `D:/VISSIM-merge/k8_gate_trees/rmcause/codex_remote.git`(9a8320ec 를 받으려고 만든 임시 bare 저장소).
