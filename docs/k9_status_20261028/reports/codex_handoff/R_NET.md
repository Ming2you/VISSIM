# R_NET — 64cf 망과 v3c3 망 대조, codex 판 이식 범위 (2026-10-24 KST)

- 이 문서는 망 구조와 이식 범위만 다룹니다. 성능 판정은 하지 않습니다.
- 대상
  - **64cf 망** = codex 인계 브랜치 `codex/handoff-rmtsc-20261024` @ `a49981ff`의 `diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx`, sha256 `64cf5f55…59dc`, 3,168,966 바이트 [실행 sha256sum].
  - **v3c3 망** = 우리 GWT8(`D:/VISSIM-merge/sim3-n31-k8`, head c20aff1d)의 `diagnostics/sdmpc_n31_20260924/network/baseline_s31_v3c3nc.inpx`, sha256 `3de889f0…1c2e`, 3,159,490 바이트 [실행].
  - codex 판 = 위 브랜치의 공동제어 설정 `diagnostics/repin_v3c3_review_20261001/urban_rm269/aggregate270/native413_adopted355/optimized_config.json`(sha256 `c9088262…1df3`)과 그 코드 [실행].
- 표시: **[실행]** 이번에 읽기 전용 명령·스크립트로 계산함. **[읽음]** 파일·코드를 읽음. **[추론]** 시험하지 않은 판단. **[계산]** 산술.
- 약어(처음 한 번만 풉니다)
  - DSD = 희망속도 분포(desired speed distribution). "DSD 결정" = 그 분포를 바꾸는 표지(desSpeedDecision).
  - VSL = 가변 제한속도. RM = 램프 미터. TSC = 도시 신호 제어. S-DMPC = codex·우리 공통 계열의 모형예측 제어기.
  - TTT = 총 통행시간(veh·h). Ω701 = codex 목적 영역(링크 701개). Ω635 = 우리 목적 영역(링크 635개). Ω 밖 = 그 바깥 링크의 관측 체류. ④ = 전체 1,236링크 TTT + 미삽입 지체(우리 보고 지표).
  - 미삽입 = 차량 입력에서 생겼지만 망 첫 링크에 아직 들어가지 못한 차량. 미삽입 지체 = 그 대기(veh·h).
  - DCP = 자료수집점(data collection point). SC = 신호제어기. SG = 신호군. NC = 무제어 런. FZP = VISSIM 차량 궤적 기록.
  - relFlow = 정적 경로 결정의 상대 유량. "결정점 우회" = 앞 결정의 경로가 다음 결정점 뒤에서 끝나, 그 결정점이 그 차량에 작동하지 않는 꼴.
  - plant = S-DMPC 안의 예측 모형. sign cell = plant가 VSL 표지를 두는 셀 번호.
- 시드 표기: 늘 망 접두어를 붙입니다(64cf-s29, v3c3-s31). codex 성능 근거는 **64cf-s29 한 시드**뿐입니다. 봉인 시드(37·59·61·67) 폴더·수치는 열거나 옮기지 않았습니다.
- 작업 파일: `scratchpad/k8/codex_handoff/work/net/`(스크립트와 출력 json). 산출물 sha는 §8.

---

## §0 요약

1. **두 망은 기하·신호가 같고, 수요·경로·속도 분포·VSL 표지 하나·규칙용 DCP가 다릅니다.** 47개 최상위 묶음 가운데 38개는 공백 정리 뒤 원소까지 같습니다. 다른 것은 차량 입력 1개(1099), 정적 경로 결정 31개(v3c3 전용 8 + 내용 다름 23), DSD 1개(110) + v3c3 전용 3개(81·91·101), DSD 결정 4개(63–66 위치), DCP 65개(64cf 전용), 평가 출력 토글 8개, 저장 시드입니다 [실행 `inv2.py`].
2. **64cf는 v3c3의 후손이 아닙니다(구조로 확인).** 64cf의 정적 경로 130개는 우리 v2 망(f475ce42)과 원소 단위로 같고, v3b·v3c·v3c1·v3c2·v3c3와는 같은 23개가 다릅니다. v3c3 전용 요소(경로 결정 1160·1162–1168, DSD 81·91·101)가 64cf에 없습니다 [실행 `anc.py`]. 폴더 이름 `repin_v3c3_review_20261001` 아래 파일은 64cf를 가리키고 v3c3 sha는 0건입니다 [실행 `refs.py`].
3. **codex 판은 v3c3에서 그대로 돌지 않습니다.** 러너가 64cf sha가 아니면 멈추고(`run_closedloop3000.ps1:132`), 계약 파일 23개가 64cf sha로 묶여 있으며 런타임 검사가 이를 대조합니다. plant의 VSL sign cell 검사도 v3c3 표지 위치(셀 18)에서 예외를 냅니다(설정값 16) [읽음·실행 계산].
4. **"작은 재핀"으로 돌게 만들 수는 있습니다. 그러나 그것은 codex 숫자의 재현이 아닙니다.** 핀 바꾸기·경로 의존 계약 재생성은 기존 도구로 약 3–6 작업일, 새 VISSIM 0회입니다 [추론]. 남는 것은 64cf-s29(일부는 다른 망)로 맞춘 plant·도시 보정입니다. 이것까지 v3c3로 다시 맞추면 약 2–4주와 새 VISSIM 반응 런이 듭니다 [추론].
5. **Ω701 링크 집합은 v3c3에서 그대로 같습니다.** codex 함수로 v3c3에서 다시 뽑아 701/535가 같게 나왔습니다 [실행 `omega/run_omega.py`]. 그래서 우리 기존 v3c3 런에 Ω701을 새 런 없이 셀 수 있습니다 [추론].
6. **64cf 1099 수요(v3c3의 1.84–2.27배)는 FW_W 입구를 런 내내 포화시킵니다.** 0–8100 s 명목 수요 20,117대 가운데 joint(64cf-s29)는 런 끝에 10,217대가 미삽입입니다. 미삽입 지체(16,424 veh·h)는 망 안 TTT(8,546)의 1.9배이고, Ω701 차이(−494.7; 같은 런 Ω 밖 +45.7, 물리 망 관측 체류 −449.0, 64cf-s29 한 시드)의 약 33배입니다 [계산, HANDOFF:19–21,72]. Ω701과 "물리 망"은 이 항을 뺍니다. 0–8100 s 짝 NC의 미삽입 지체는 모름(raw 필요)입니다.

---

## §1 망 전체 대조 (47개 최상위 묶음)

[실행 `work/net/inv2.py` → `inv2.json`] 원소를 `no` 기준으로 짝짓고, 글자 사이 공백만 지운 뒤 XML 문자열을 비교했습니다.

| 묶음 | v3c3 | 64cf | 결과 |
|---|---|---|---|
| links(커넥터 포함) | 1,236 | 1,236 | 같음 |
| nodes / conflictAreas | 56 / 1,815 | 56 / 1,815 | 같음 |
| signalControllers / signalHeads / signalGroup | 50 / 537 / 440 | 50 / 537 / 440 | 같음 |
| queueCounters / vehicleTravelTimeMeasurements / delayMeasurements | 98 / 191 / 131 | 98 / 191 / 131 | 같음 |
| vehicleCompositions / vehicleTypes / drivingBehaviors / linkBehaviorTypes / timeIntervalSets | 14 / 8 / 5 / 5 / 10 | 같은 수 | 같음 |
| vehicleInputs | 34 | 34 | 1개 다름(1099) |
| vehicleRoutingDecisionsStatic | 138 | 130 | v3c3 전용 8, 내용 다름 23 |
| desSpeedDistributions | 47 | 44 | v3c3 전용 3(81·91·101), 다름 1(110) |
| desSpeedDecisions | 106 | 106 | 4개 위치 다름(63–66) |
| dataCollectionPoints / Measurements | 314 / 173 | 379 / 238 | 64cf 전용 65개씩 |
| evaluation(출력 설정) | – | – | 토글 8개 다름 |
| simulation | randSeed 31 | randSeed 29 | 저장 시드만 다름 |
| 그 밖 30개 묶음 | | | 같음 |

- `.sig` 42개는 바이트까지 같습니다 [실행 `cmp`]. 두 `sig_manifest.json`은 망 이름·sha·출처 경로만 다릅니다 [실행].
- `<detector>` 원소는 두 망 모두 0개입니다 [실행]. 검지는 DCP·대기행렬계수로 합니다.
- 평가 출력 토글(dataColl·delays·linkResults·queues·nodeRawData·scDetRec·vehTravTmRawData·vehTravTms)은 64cf에서 켜져 있습니다. codex 재핀 영수증은 "러너가 COM으로 설정"이라고 적습니다 [읽음 codex `selected/scenario/repin_receipt.json` `/native_changes_from_previous_pack/evaluation`]. 모형 차이가 아닙니다 [추론].

---

## §2 항목별 대조

### §2.1 차량 입력 34개

- 33개는 같습니다. 1098(FW_E 입구, 링크 74)도 같습니다. 다른 것은 **1099(FW_W 입구, 링크 26)** 하나입니다 [실행 `dem.py`].

| 구간 시작 s | 1098 (두 망) | 1099 v3c3 | 1099 64cf | 64cf/v3c3 |
|---|---|---|---|---|
| 0 | 7,096.32 | 4,300 | 8,870.4 | 2.063 |
| 900 | 10,137.6 | 5,600 | 12,672.0 | 2.263 |
| 1800 | 10,644.48 | 6,000 | 13,305.6 | 2.218 |
| 2700 | 9,123.84 | 5,200 | 11,404.8 | 2.193 |
| 3600 | 7,096.32 | 3,900 | 8,870.4 | 2.274 |
| 4500 | 5,068.8 | 3,450 | 6,336.0 | 1.837 |

- 64cf의 1099/1098은 여섯 구간 모두 정확히 1.25(= 1098 ÷ 0.8)입니다 [실행]. HANDOFF:187–188과 맞습니다.
- 두 망 다 1098·1099에 차량 구성 14("Freeway entry DSD110")를 씁니다 [실행].
- **수요 계보 [실행]:** 원천 망 `ramp_dsd_20260916_v2/source_dsd/baseline.inpx`(fcb349d3, 100 %)에서 64cf는 34개 입력 모두 정확히 ×0.8(1098·1099) 또는 ×0.9(나머지 32개)입니다. 원천에서 1099 = 1.25 × 1098이므로 0.8을 곱해도 1099 = 1098 ÷ 0.8이 됩니다. v3c3는 33개가 같은 배율이고 1099만 따로 정한 프로필(원천의 0.35–0.44배)입니다. 메모리 기록 이름으로는 64cf = "1099 v1 수요", v3c3 = "v2 수요"입니다 [읽음 메모리 `vissim-vsl-handoff-repro-20260924.md:8`].
- 사용자는 2026-10-13에 v3c3의 1099(v2)를 의도한 FW80으로 확인했습니다(D-K9-10) [읽음 `K9_1_USER_DECISIONS_20261010.md`, 인용 `j1/analysis/J1_REPORT.md:57`].
- 명목 수요 합(0–8100 s): 1099 v3c3 9,700대, 64cf 20,117대. 망 전체 v3c3 62,657대, 64cf 73,073대(+16.6 %). 구간별 망 전체 비는 1.147–1.180입니다 [계산 `dem.py`].
- codex `handoff/evidence/demand_34_inputs.csv` 204행은 64cf inpx와 모두 같습니다 [실행].

### §2.2 정적 경로 결정

[실행 `det4.py`, `bypass` 검사]
- v3c3 전용 8개: 1160(링크 21), 1162(256), 1163, 1164, 1165, 1166, 1167, 1168. 메모리의 "v3c 무경로 D형 V1–V7 새 결정점"입니다 [읽음 메모리 `vissim-network-v3c-20260927.md`].
- 내용이 다른 23개
  - relFlow + 목적지 위치: 33, 1115, 1117, 1118, 1119.
  - relFlow만: 283, 1011, 1044, 1120, 1122, 1140.
  - 목적지 위치만: 1032, 1111, 1112, 1113, 1116, 1124, 1128, 1131, 1132, 1133, 1136.
  - relFlow + 결정점 위치: 1061(링크 387).
- 이것은 우리 v3/v3b 편집과 같은 꼴입니다. A형 경로 끝을 건너뛴 결정점 앞으로 옮기고, 살아난 결정점 relFlow를 v2 NC 실측 분율로 바꾸고, 닿지 않던 1061을 옮겼습니다 [읽음 메모리 `vissim-network-v3-decisions-20260925.md:16,20`].
- **결정점 우회:** 같은 링크에서 결정점 뒤에 끝나는 다른 결정의 경로를 세었습니다.
  - 두 망 공통 3건(1132·1133 위의 장거리 본선 경로)은 빼고 셉니다.
  - 그러면 64cf는 9개 결정(33·1011·1044·1114·1115·1117·1118·1120·1122)에 20개 경로가 걸리고, v3c3는 0개입니다 [실행].
  - 앞선 대조 `cmp355/COMPARE_355_K8.md:56`과 같은 수입니다. 이번에는 들어오는 커넥터 위치를 따로 확인하지 않았습니다.
- 예: 결정 1117(링크 127 @228.92 m)
  - v3c3: 1131:2·1132:2·1136:2가 모두 127 @225.9 m(결정점 앞)에서 끝납니다.
  - 64cf: 같은 경로가 334.36 / 481.23 / 295.06 m(결정점 뒤)에서 끝납니다 [실행].
  - 그래서 64cf에 적힌 1117 relFlow(5/빈/빈)는 그 차량들에 작동하지 않습니다.

### §2.3 희망속도 분포

- 공통 44개 가운데 43개는 같습니다. **DSD 110만 다릅니다.** v3c3에는 81·91·101(각 ±1 km/h 좁은 분포)이 더 있습니다 [실행].

| DSD 110 | 점(km/h, 누적) | 평균 | 5 % / 50 % / 95 % |
|---|---|---|---|
| v3c3 | (98,0) (105,.03) (110,.10) (120,.70) (130,.91) (140,1) | 117.97 | 106.4 / 116.7 / 134.4 |
| 64cf | (75,0) (95,.03) (100,.10) (115,.68) (130,.91) (145,1) | 112.28 | 96.4 / 110.3 / 136.7 |

- [계산] 평균과 분위는 꺾은선 누적분포에서 셈했습니다.
- 두 망 모두 DSD 110을 차량 구성 14(입력 1098·1099)와 DSD 결정 76개가 씁니다 [실행].
- VSL 명령용 50·60·70(±5 좁은 분포)과 80·90·100(넓은 분포)은 두 망에서 같습니다 [실행].
- codex `desired_speed_cdfs.csv`(44개 분포)와 `dsd_locations.csv`(424행)는 64cf inpx와 모두 같습니다 [실행]. HANDOFF:189의 CDF 문장도 맞습니다.

### §2.4 DSD·VSL 표지 위치

- DSD 결정 106개 가운데 다른 것은 **63–66(FW_E, 링크 2, 차로 1–4)의 위치 하나**입니다. 가리키는 분포·차종·차로는 같습니다 [실행].
  - v3c3: 링크 2 @3,998.67 m. FW_E 사슬 거리 6,733.2 m. 31칸 셀 18(부모 21칸의 12). 차로 감소(커넥터 10613, 6,841.7 m)보다 108.5 m 상류.
  - 64cf: 링크 2 @3,607.22 m. 사슬 6,341.7 m. 셀 16(부모 12). 차로 감소보다 500 m 상류 [실행 codex `port_gain/geometry.json` 셀 경계로 계산].
- 우리 옛 망(v2·v3b·사용자 userfix Ver2·0814e·원천 fcb349d3)은 모두 3,998.67입니다. 64cf만 옮겼습니다 [실행 `anc2.py` 계열]. 메모리는 이것을 codex VSL90 병목 실험용 이동으로 적습니다 [읽음 `vissim-vsl-handoff-repro-20260924.md:8`].
- plant 설정의 FW_E sign cell
  - codex eval_036 `/freeway/component_vsl_transport/FW_E/sign_cells` = `[0,3,5,8,14,16,26,28]`.
  - 우리 `reference_config_n31_v2.json` 같은 경로 = `[0,3,5,8,14,18,26,28]`.
  - 다른 칸은 다섯 번째 값 하나입니다 [실행].
- codex `handoff/evidence/controlled_dsd_groups.csv`는 63–66을 `link 119, lane 1–4`로 적습니다. 이것은 러너 VBS 행동 키 표기(`RW_FW_E_S13|63|119|1`, `lane_native_b110.vbs:32`)를 옮긴 것입니다. inpx상 실제 위치는 링크 2입니다. 링크 119는 3차로라 lane 4가 없습니다 [실행·읽음]. 우리 VBS도 같은 키 글자를 씁니다.
- 동측 구역 이름: VBS의 21칸 경계에서 seg10 = DSD 59–62(셀 14), seg13 = DSD 63–66입니다. seg13 구역(6,841.7 m부터)의 표지는 그 상류 부모 칸 12에 있습니다 [실행·읽음 `lane_native_b110.vbs:14,32`]. HANDOFF:155와 맞습니다.

### §2.5 신호제어기·신호군·.sig

- SC 50개, SG 440개, 신호등 537개, `.sig` 42개가 같습니다 [실행]. 도시 17개 SC(1·5·6·7·11·12·16·101·105·107·108·109·1001–1005)와 그 SG 번호는 두 판이 그대로 씁니다 [읽음 VBS:28].

### §2.6 검지·DCP

- 64cf 전용 DCP·측정 65개(910117–910181)의 이름은 `RULE|ramps|RM_C…|laneN`(29개)과 `RULE|vsl_zones|FW_…|laneN`(36개)입니다 [실행 `det3.py`]. 규칙 기반 ALINEA/VSL 묶음용입니다 [추론, 이름].
- codex 설정·obs150 검지표·매핑 두 개·`evaluation/controllers`·`scripts`·`tools`에서 이 번호와 `RULE|`를 찾은 결과는 0건입니다 [실행 grep]. S-DMPC는 이 DCP를 쓰지 않습니다 [추론, 찾은 범위 안].
- S-DMPC 관측 검지표 `obs150_detectors_v2.csv`(294행, DCP 960001~)는 두 판이 바이트까지 같습니다 [실행 cmp].
- 대기행렬계수 98·통행시간 측정 191·지체 측정 131개는 같습니다 [실행].

### §2.7 미터 신호군

- 미터 8개: `RM_C10480·10482·10646·10644·10639·10681·10490·10484`. SC 9101–9108, 커넥터 같은 번호. 두 판 VBS가 같습니다 [읽음 VBS:23–27; 실행 diff].
- 두 판 `lane_native_b110.vbs`의 차이는 34행 `RW_ALLOWED_VSL_SPEEDS` 한 줄뿐입니다. codex는 "50,…,110", 우리는 "81,91,101,110"입니다 [실행 `pack.py`].
- 미터 SC와 SG는 §2.5대로 같습니다.

### §2.8 codex 설정이 쓰는 링크 번호

- **Ω701 소속**
  - Ω701 = Ω635 + 66링크. 추가 이유는 접근로 영역 39, 제어 신호등 링크 13, 포함 링크 사이 직결 커넥터 31입니다(중복 있음) [실행].
  - codex의 Ω635(`selected/scenario/control_area_membership_213a5d.json`)와 우리 v3c3 Ω635는 inside 635·outside 601 링크 집합이 같습니다. 두 파일의 차이는 relFlow 메타 기록과 핀뿐입니다(43개 잎) [실행].
  - codex 함수 `expand_controlled_intersection_area`를 복사본으로 v3c3에서 돌렸습니다. **v3c3 Ω701 = codex Ω701(701/535, 같은 집합)**입니다 [실행 `omega/run_omega.py` → `omega701_rederived.json`]. 함수 입력(매핑·영역 파일)은 우리 트리와 바이트가 같습니다. 빌더 파일 본문은 다릅니다 [실행].
- **FW_E 7링크 `74,10699,2,10613,119,10702,24`, 국소 19링크**: 모두 두 망에 같은 기하로 있습니다 [실행 links 같음].
- **미터·VSL 구역 키**: §2.4·§2.7과 같습니다.
- **plant 기하**: codex `port_gain/geometry.json`(91a584ab)과 우리 v3c3 geometry(2e3d8bfe)는 셀·사슬·경계·주소·직결 커넥터가 모두 같습니다. 3,416개 잎 가운데 다른 것은 14개입니다. 핀·경로 문자열 8개와 `desired_source_demand`의 1099 여섯 값입니다 [실행 `geo.py`]. 31칸 분할 파일(9769b3a4)은 같은 바이트입니다 [실행].

---

## §3 codex 판을 v3c3에서 돌리려면

### §3.1 그대로 돌리면 멈추는 곳 [읽음 코드, 실행 계산]

1. 러너 `diagnostics/sdmpc_n31_20260924/integration_20260926/run_closedloop3000.ps1:128`은 `native_seed29.inpx`를 복사합니다. `:132`는 sha가 64cf가 아니면 `throw 'Network differs'`를 냅니다. NC 재사용 조건 `:141`도 64cf sha입니다.
2. 계약 sha 대조
   - `lane_plant_runtime.py:120–122`(기하 추출 망), `:202–203`(현재 관측 망), `lane_freeway_runtime.py:110–111`(진출 경로 목록), `calibrated_urban_runtime.py:34–35`(도시 보정), `area_dynamic_routes.py:39`, `native_input_prehead.py:26`, `native_internal_input.py:56,92,124,273`, `head_service_resources.py:189`.
   - 런 출처의 망 sha(`network_provenance.snapshot_network_sha256`)나 파일 sha를 계약의 64cf sha와 비교하고, 다르면 예외를 냅니다.
3. VSL sign cell 검사 `lane_plant_runtime.py:771–792`
   - inpx의 DSD 위치로 셀을 다시 셉니다. `sign − cell ∉ {0,1}`이면 `ValueError('Calibrated sign is not at its native cell/boundary')`를 냅니다.
   - v3c3에서 DSD 63–66은 셀 18이고 설정 sign은 16이라 차이가 −2입니다 [실행 계산]. 핀을 모두 바꿔도 이 검사에서 멈춥니다.

### §3.2 런타임 참조 파일 분류

[실행 `refs.py`, `direct_refs_status.json`] 설정이 직접 가리키는 파일은 48개입니다. 기록용(`/_repin`·`/_area_revision`·`/safety`·`/diagnostic`·`/_canonical`)을 빼면 런타임 34개입니다. 이 가운데 23개가 64cf sha를 담고, 7개는 우리 트리에 같은 바이트로 있습니다. 설정에서 이어지는 파일 247개 가운데 64cf 핀은 54개, v3c3 핀은 0개입니다.

| 부류 | 뜻 | 파일(설정 경로) |
|---|---|---|
| 같음(7) | 손댈 것 없음 | `/mapping_json`, `/detector_mapping_json`, `/urban/capacity/queued_links_json`, `…/sustained_json`, `/urban/plan/actuation_plan_json`, `/urban/boundary_out/ramp_split_json`, `/freeway/geometry_profile` |
| P: 핀·가리킴만 | v3c3판이 우리 기본 팩에 이미 있거나, 기본 팩 + Ω701 가리킴 교체로 됨 | `head_free_service`, `dynamic_physical_route_topology`, `shared_approach`, `physical_ramp_branches`(topology_routes), `known_wout_route_evidence`, `native_input_signal_authority`, `sc2001_corridor`, `route_choice_corridor` 4개, `native_internal_inputs`, `observation/physical_support_repair`, `control_area_objective/membership_path`(Ω701, §2.8에서 같음 확인), `observation/physical_branch_projection/source/network/path`(망 자체), `execution/signal_vbs_config`(VSL 집합 결정 필요) |
| R: 경로 의존 재생성 | codex 새 계약. 다른 relFlow·경로 끝(§2.2)을 담음. 빌더 스크립트가 같은 폴더에 있음 | `urban_rm269/native_beta/physical_routes.json`(1061·1113·1116·1118·1119·1124·1128), `goal8_265/head47_right/authority.json`(1116·1122·1140, 빌더 위치 모름), `urban_rm269/sc6_queue/head_resources.json`(1113·1118·1122·1124, 관측 지원 일부 포함), `unrouted10646/route_contract.json`(1131·1132·1133 경로 끝), `urban_area263/approaches_only/route_contract.json`(movement/arrival 경로 계약 583 kB), `urban66_u7/contract.json`, `urban_rm269/sc1_supply/contract.json`, `urban_rm269/sc6_queue/head_lane_support.json` |
| D: 자료 보정 | 64cf-s29(또는 다른 망) 자료로 맞춘 값. v3c3 자료로 다시 맞춰야 뜻이 맞음 | `urban_rm269/aggregate270/native348/calibration.json`(`/training` = "Prior closed seed29 runs … in-sample"), `/freeway/lane_plant` → eval_036 `reference_config.json`(셀별 FD·상태 반응. 학습 = seed29 상태와 짝 반응 표본, `expanded_joint_fit.py:28,221,333,420`. sign cell 16 포함), `port_gain/parameters.json`·`port_profile.json`, `retained10638/local_protocol.json`, `/freeway/segment_params`(셀별 v_free 실측, 출처 망 sha `ebd90383…`, 09-08) |

- 기본 시나리오 팩 24개(`selected/scenario/`)의 v3c3판은 이미 우리 트리 `diagnostics/sdmpc_n31_20260924/scenario/`에 같은 파일 이름으로 있습니다. K7 C-4/V-6 커밋 `6472308e`가 같은 계열 도구 `repin_scenario_v2.py`로 만들었습니다 [실행 `pack.py`, git log].
  - 차이는 핀과 v3c3 경로 내용입니다. 예: 1083 권한의 결정 1160, 1117·1140 relFlow, 투영 지원의 경로 1162:1·1164:1·1165:1.
  - 단, codex판 `repin_scenario_v2.py`는 우리 것과 바이트가 다릅니다 [실행]. codex 도구로 다시 만들면 우리 팩과 다를 수 있습니다(모름).
- `urban_area263/approaches_only/evidence/`의 8개는 기본 팩 파일과 비교해 Ω701 소속 가리킴만 다릅니다(7개). 투영 지원 1개는 Ω701 커넥터를 더 담습니다(210개 잎) [실행].

### §3.3 공수 추정 [추론]

| 길 | 할 일 | 새 VISSIM | 기간 | 결과의 뜻 |
|---|---|---|---|---|
| 그대로 | 없음 | 0 | 0 | §3.1에서 설정 단계 예외. 돌지 않음 |
| 작은 재핀 | 러너 망 경로·sha 매개변수화. P 부류 핀 교체(우리 팩 재사용). Ω701 재생성. R 부류 빌더를 v3c3에 다시 돌림. geometry 1099 값 교체. sign cell 16→18. VBS VSL 집합 결정. 기존 v3c3 NC FZP로 configure·결정 재생 오프라인 점검 | 0 | 약 3–6 작업일 | **돌기는 하나 64cf로 맞춘 D 부류 계수를 v3c3에 얹은 새 변형**입니다. codex 64cf-s29 숫자의 재현도, v3c3에서 보정된 codex 판도 아닙니다. 특히 VSL 수송 계수는 sign 16(500 m 상류)에서 맞춘 것이고, DSD 110(평균 112 대 118)과 v_free(설정 120 대 우리 110)가 다릅니다 |
| 전면 재유도 | 위 + D 부류를 v3c3 자료로 다시 맞춤: 셀별 FD·상태 반응(codex는 seed29 섭동 8조건 + NC 5상태로 학습), 도시 집계 보정(codex는 폐루프 런 자료), 램프 배수·포트 값, VSL 수송, 셀별 v_free. 그 뒤 관문 점검과 짝 평가 | 반응·폐루프 런 필요. 수는 모름(codex 학습 꼴 `expanded_joint_fit.py:62–63` = seed29 섭동 8조건 + NC 상태 5개를 따르면 반응 런 약 8회 + 도시 보정용 폐루프 1–3회로 추정) + 평가 다시드 | 약 2–4주 + 런 시간 | codex 방법을 v3c3에서 재현한 판. 수치는 새로 나옴 |

- 정책 충돌(K3 미터 서비스 표, K6 셀별 FD 설치, 결정 실패 시 유지 대 런 정지, 5 s/10 s 멀티레이트 대 1 s SA 등)은 망 문제가 아니라 이 문서 범위 밖입니다. 앞선 대조 `cmp355/COMPARE_355_K8.md` §2.1–2.3과 다른 R_* 보고를 보십시오.
- 반대 방향 값싼 길 [추론]
  - (a) codex 판을 64cf 그대로 이 PC에서 한 번 재현하기. 64cf-s29 NC는 codex 원자료에 있음(raw 필요). joint 한 런은 약 4.8 h(HANDOFF:307).
  - (b) Ω701을 우리 기존 v3c3 런(NC3·J1·V-A)에 새 런 없이 다시 세기(§2.8).

---

## §4 64cf 1099 수요가 Ω701 개선의 뜻에 미치는 것

### §4.1 사실

- [계산·읽음] 1099 명목 수요와 런 끝 미삽입
  - joint(64cf-s29) 0–8100 s: 수요 20,117대, 런 끝 미삽입 10,217대(HANDOFF:72,75; evidence `run_metadata.json`) → 삽입 약 9,900대.
  - NC 0–9000 s: 수요 21,701대, 미삽입 10,857대 → 삽입 약 10,844대.
  - 대략 절반이 들어가지 못합니다. 무작위 수요의 표준편차는 약 ±140대입니다(√20,117).
- [계산] 평균 삽입률은 약 4,400 veh/h입니다(3차로 링크 26 기준 차로당 약 1,470). v3c3의 1099 명목 수요 9,700대(0–8100 s)와 총량이 비슷합니다. 다만 64cf는 첫 구간부터 끝까지 입구가 포화라 시간 모양이 평평하고, 마지막까지 줄이 남습니다 [추론].
- [읽음] 미삽입 지체: NC 0–9000 s 19,290.0 veh·h(망 안 TTT 9,654.8의 2.0배), joint 0–8100 s 16,423.6 veh·h(망 안 8,546.0의 1.92배) (HANDOFF:71–72).
- [계산 HANDOFF:19,27] Ω701 안 서측 본선 몫 = Ω701 − (Ω701 − 서측 본선). NC 1,387.16, joint 1,390.50 veh·h. 차이 +3.34(+0.24 %)입니다. 서측 본선은 포화 관으로 거의 움직이지 않습니다.
- [계산] 그래서 "Ω701 − 서측 본선" −8.27 %(−498.0/6,019.0)와 전체 Ω701 −6.68 %(−494.7/7,406.2)의 차이는 대부분 분모 차이입니다.
- 같은 런의 다른 지표(64cf-s29 한 시드, HANDOFF:19–21): Ω701 −494.7 veh·h(−6.68 %), Ω 밖 +45.7(+2.87 %), 물리 망 관측 체류 −449.0(−4.99 %). 셋 모두 미삽입 지체를 넣지 않았습니다.
- 비교용 우리 v3c3 NC3(v3c3-s31·s41·s43) 1099 미삽입 지체는 1,208.5 / 1,021.9 / 675.0 veh·h, 런 끝 남은 차는 122 / 0 / 0대입니다 [읽음 `k92/va/analysis/VA_REPORT.md:443`].

### §4.2 뜻 [추론]

1. **가장 큰 비용 항이 목적·보고 밖에 있습니다.** 64cf에서는 미삽입 지체가 망 안 TTT의 약 2배입니다. Ω701 차이(−494.7)는 미삽입 항이 3 %만 움직여도 덮일 크기입니다.
2. **FW_W 쪽 손해가 Ω701에 안 보일 수 있습니다.** 제어로 링크 26 입구까지 줄이 차면 삽입이 줄고, 그 비용은 미삽입(Ω701 밖, 물리 망 밖)으로 갑니다. 반대로 입구가 풀리면 더 많은 차가 Ω701에 들어와 Ω701이 커집니다. Ω701은 이 방향을 구분하지 못합니다.
3. **이번 한 짝에서 미삽입 항의 방향은 대략만 추정됩니다.**
   - 가정: 8100–9000 s에 1099만 줄이 있고, 수요 6,336 veh/h가 일정하고, 삽입률이 0과 수요 사이입니다.
   - 그러면 NC 8100 s 미삽입은 9,273–10,857대, NC 0–8100 s 미삽입 지체는 약 16,576–16,774 veh·h입니다. joint − NC ≈ −152 ~ −350 veh·h가 됩니다(삽입률 4,400 veh/h 중심값 ≈ −212).
   - 이 범위라면 이 한 시드에서 미삽입 항이 부호를 뒤집지는 않습니다. 그러나 가정 셋에 기대고, 짝 NC의 0–8100 s 값은 직접 기록이 없습니다(HANDOFF:74,314).
4. **FW_W를 거치는 도시 유입이 상한에 묶입니다.** 64cf에서 FW_W 처리량은 입구 포화로 거의 일정합니다. 그래서 진출 10491·10479 → SC1001 W 쪽 유입도 높은 수준에서 고정에 가깝습니다. codex 장치 일부(10480→10491 고리, 10480 대기 → 124 차로 1 → 10483 막힘 등, `cmp355` §2.1)는 이 부하에서 맞춘 것입니다. v3c3(1099 약 절반, 줄이 끝에 빠짐)에서 같은 효과가 날지는 모릅니다.
5. **"8 %"는 64cf의 이 체제에 묶인 숫자입니다.** 망·수요가 달라 v3c3로 옮겨 읽을 근거가 없습니다. 64cf-s29 한 시드라 시드 분산도 모릅니다.

### §4.3 raw 자료가 오면 할 수 있는 확인 (raw 필요)

- NC FZP(`raw/nc/vissim_eval/…fzp`)와 joint FZP에서 링크 26 첫 등장 시각으로 누적 삽입 I(t)를 셉니다.
- 같은 시드·같은 입력의 생성열이 두 런에서 같다면 미삽입 지체 차 = ∫₀⁸¹⁰⁰ [I_joint(t) − I_NC(t)] dt / 3600입니다. 이 가정은 900 s 전 접두 FZP 해시가 같다는 사실(HANDOFF:48)로 일부만 받쳐집니다. 900 s 뒤 생성열이 같은지는 따로 확인해야 합니다.
- 입력별 `.err` 경고, 1.db의 `VEHICLENETWORKPERFORMANCE…` 구간 값이 있는지도 봅니다(인계는 0–9000 누적 하나뿐이라고 적음, HANDOFF:74).

---

## §5 64cf는 v3c3의 후손인가 — 구조로 본 답

[실행 `anc.py` → `ancestry_distance.json`] 64cf와 각 후보 망의 원소 차이 수입니다(시뮬레이션·평가 설정 제외).

| 후보(sha 앞 8자) | 전체 차이 | 정적 경로(v전용/64cf전용/다름) | 구성 | DSD 분포 | DCP | 입력 | DSD 결정 |
|---|---|---|---|---|---|---|---|
| 사용자 userfix Ver2 (085a10c7) | 1,793 | 0/0/9 | 64cf +1 | 64cf +1 | 64cf +181 | 34 다름 | 76 다름·10 64cf 전용 |
| 원천 rampdsd_src (fcb349d3) | 387 | 0/0/2 | 64cf +1 | 64cf +1 | 64cf +123 | 34 다름 | 76 다름 |
| **v2nc (f475ce42)** | **138** | **0/0/0** | 64cf +1 | 1 다름 | 64cf +65 | 2 다름 | 4 다름 |
| v3bnc (be0075bf) | 161 | 0/0/23 | 64cf +1 | 1 다름 | 64cf +65 | 2 | 4 |
| v3cnc s31 (a9cdfd6c) | 170 | 9/0/23 | 64cf +1 | 1 | 64cf +65 | 2 | 4 |
| v3c1nc (2577209b) | 169 | 8/0/23 | 64cf +1 | 1 | 64cf +65 | 2 | 4 |
| v3c2nc s31 (597191ac) | 167 | 8/0/23 | 같음 | 1 | 64cf +65 | 1 | 4 |
| v3c3nc (3de889f0) | 170 | 8/0/23 | 같음 | v3c3 +3, 1 다름 | 64cf +65 | 1 | 4 |

- 판단 근거 [실행·추론]
  1. 64cf의 정적 경로는 v2와 원소 단위로 같습니다. v3 계열이 바꾼 23개 결정과 새로 넣은 8–9개 결정이 64cf에는 하나도 없습니다.
  2. v3c3 전용 DSD 81·91·101이 64cf에 없습니다.
  3. 64cf가 v3c2·v3c3와만 공유하는 요소는 차량 구성 14 하나입니다. 메모리 기록은 64cf에 먼저 있었고(09-24 codex VSL 인계 망) 우리가 v3c2(09-30)에서 들였다고 적습니다 [읽음 메모리 `vissim-freeway-entry-dsd40-defect-20260930.md:14–15`("64cf … 구성 14 … 이미 고쳐져 있었음 → v3c2 로 수정", 우리 줄기는 그 전 기준망 86af2ac8에서 갈라짐), `vissim-vsl-handoff-repro-20260924.md:8`]. 공유 방향은 64cf → v3c2입니다 [추론].
  4. codex 재핀 영수증의 망 출처는 codex PC의 `…/diagnostics/vsl_handoff_20260924/network`입니다. 이전 팩은 rampdsd_src입니다 [읽음 `selected/scenario/repin_receipt.json` `/inputs`].
- 결론적 사실: **64cf = v2 경로 세대의 망 + 다섯 편집**입니다. 편집은 구성 14, 1099 v1 수요, DSD 110 75–145, DSD 63–66 500 m 상류 이동, RULE DCP 65개입니다. v3c3에서 갈라져 나온 망이 아닙니다.
- 이름 문제: codex 폴더 `repin_v3c3_review_20261001` 아래 런타임 계약은 64cf를 가리키고, 3de889f0은 0건입니다 [실행 `refs.py`]. HANDOFF:173도 "이 인계판을 v3c3 실험으로 부르면 안 된다"고 적습니다.

---

## §6 HANDOFF 주장 대조

| HANDOFF 줄 | 주장 | 대조 결과 |
|---|---|---|
| 172 | inpx sha 64cf5f55…, 3,168,966 바이트 | 같음 [실행] |
| 173 | v3c3 3de889f0과 다른 파일 | 같음 [실행] |
| 176 | 34개 입력표 `demand_34_inputs.csv`, profile `__default__,1.0` | 표 204행 = inpx [실행]. profile.csv 두 판 같은 바이트 [실행] |
| 187 | 모든 구간 1099 = 1098 ÷ 0.8 | 같음 [실행] |
| 188 | v3c3 1099 = 4300/5600/6000/5200/3900/3450 | 같음 [실행] |
| 189–190 | DSD 110 CDF와 `desired_speed_cdfs.csv` | 같음 [실행] |
| 154 | `controlled_dsd_groups.csv` = 66개 DSD의 구역·번호·link·lane | 번호·구역은 VBS 키와 같음. **link 열은 VBS 키 표기이며 63–66은 실제로 링크 2(차로 1–4)**, 119/4는 없는 차로 [실행] |
| 155 | seg10 = DSD 59–62, seg13 = 63–66 | 같음 [실행·읽음] |
| 191 | plant 매니페스트 9개 입력 핀 | 9개 sha 모두 파일과 같음 [실행]. 그중 7개는 우리 트리에 없음(같은 경로 기준), 31칸 분할 1개만 같은 바이트 |
| 71–76 | 미삽입 표와 "0–8100 NC 미삽입 모름" | 수치는 `run_metadata.json`과 같음 [실행]. 0–8100 NC 값은 이 인계로 셀 수 없음(§4.3) |

---

## §7 열린 질문

1. **기준 망(사용자 결정).** v3c3(FW80, 1099 v2, D-K9-10)를 유지할지, 64cf(1099 v1, 입구 포화, 결정점 우회 20개)를 받을지 정해야 합니다. 64cf는 VSL90 병목 실험용으로 표지를 옮긴 망입니다(§2.4).
2. **64cf를 받는다면** 결정점 우회 20개(§2.2), 링크 26 입구 포화(§4), RULE DCP 65개를 그대로 둘지 정해야 합니다.
3. **v3c3로 옮긴다면** VSL 명령 집합(50–110 넓은 분포 대 81·91·101 좁은 분포), sign cell 18에서 VSL 수송 재보정, 셀별 v_free(DSD 110 다름)를 정해야 합니다.
4. codex판 `repin_scenario_v2.py`(우리와 다른 바이트)로 v3c3 팩을 다시 만들면 우리 팩과 같은지 모릅니다. 오프라인 diff로 확인할 수 있습니다.
5. `goal8_265/head47_right/authority.json`의 빌더 스크립트 위치를 찾지 못했습니다(같은 폴더에 없음).
6. §4.2-3의 미삽입 항 방향은 가정 추정입니다. raw 자료 도착 뒤 §4.3 절차로 확인해야 합니다(raw 필요).
7. 결정점 우회가 없는 v3c3에서 1117 등 실제 회전 몫이 64cf와 얼마나 다른지는 1117 한 곳만 알려져 있습니다(약 0.70–0.72, `cmp355:57`). 나머지 결정은 모릅니다(raw 필요, 64cf FZP).

---

## §8 한 일·안 한 일, 산출물

- 한 일: 두 inpx와 우리 옛 망 다섯 벌을 원소 단위로 비교했습니다. codex 설정의 참조 파일 247개 핀을 셌고, 우리 시나리오 팩과 비교했습니다. plant 기하·sign cell·VBS를 비교했습니다. codex Ω701 함수를 복사본으로 v3c3에 돌렸습니다.
- 안 한 일: VISSIM·COM·러너·재생·동결·커밋·푸시 0. codex 감사 스크립트를 트리 안에서 실행 0(Ω701 빌더 함수 1개만 work/로 복사해 `python -B` 실행, 트리 `git status --ignored` 0줄). sealed/ 열기 0. GWT8 변경 0.
- 산출물 sha256은 마지막 줄 목록(이 문서 밖 `work/net/SHA256SUMS_R_NET.txt`)에 있습니다.
