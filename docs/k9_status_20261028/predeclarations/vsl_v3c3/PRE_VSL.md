# PRE_VSL — v3c3 고정 VSL 단독 런 3개: 사전 선언 (2026-10-27 KST, 첫 런 전 고정)

- 무엇: 사용자 결정 D-K9-95 의 VISSIM 부분입니다 [읽음 `SP/K9_1_J1_NOTES_20261013.md:318`, sha256 bbfe77b0…]. v3c3 망에서 VSL 만 켠 런 3개(v3c3-s31·s41·s43)를 무제어 NC3 와 같은 시드끼리 짝지어 봅니다. 이 문서는 팔 정의, 준비 폴더, 발사기, 비교 규칙, 도구를 **첫 런 전에** 고정합니다. sha256 은 `VS/LOG.md` 에 적습니다. 데이터를 본 뒤에는 고치지 않습니다. 쓰인 대로 못 하는 일이 생기면 고치지 않고 멈추고 보고합니다(그 칸은 "못 냄").
- 오프라인 O1(φ·ρ_crit 민감도)·O2(VSL 켠 상태 plant 충실도)는 이 문서 밖입니다. 그 규칙은 그 일을 돌리기 전에 따로 고정합니다.
- 판정 낱말은 쓰지 않습니다. Ω 는 늘 ④ 와 Ω 밖과 같은 표에 둡니다. ④b 는 첫 관측 차분이 주 값입니다. 시드 수는 표마다 적습니다.
- 표시: **[실행]** 이번에 돌려서 확인 · **[읽음]** 파일·코드를 읽어 확인 · **[추론]** 시험하지 않은 판단 · **[계산]** 이 문서의 산술.
- 경로 줄임: SP = `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8`, VS = `SP/vsl_v3c3`, RR = `D:/VISSIM_runs/20261027_vsl_v3c3`(런 뿌리), GT = `D:/VISSIM-merge/k8_gate_trees/vsl_v3c3`(설정 사본), V3 = `D:/VISSIM_runs/20261001_v3c3`(NC3·rule-RM 팔), SIM3 = `D:/VISSIM-merge/sim3/diagnostics`(러너, 읽기만), CW = `SP/codex_handoff/work`.

## 0. 줄임말 (처음 한 번)

- VSL = 가변 제한속도. DSD = VISSIM 희망속도 결정점(표지 자리). 분포 = VISSIM 희망속도 분포 번호.
- NC3 = 같은 시드 v3c3 무제어 런(`V3/s<S>_v3c3nc/run`). rule-RM 팔 = 같은 망·러너로 미터 규칙만 켠 런(`V3/s<S>_v3c3rm`). R2c = 10681 미터만 켠 런(`V3/s<S>_v3c3rm10681`).
- FZP = VISSIM 차량 궤적 기록(5 s 프레임). LDP = 신호 상태 초별 기록. plant = SDMPC 안의 예측 모형. codex 팔 = 사용자 codex 작업의 64cf 망 런.
- Ω635 = 우리 목적 영역 635링크, Ω701 = codex 목적 영역 701링크. ④a = 망 전체 링크 체류(veh·h), ④b = 미삽입 대기(망에 못 들어간 차의 대기), ④ = ④a + ④b, Ω 밖 (a) = ④ − Ω, (b) = ④a − Ω.
- ① = FW_E 본선 7링크 {74, 10699, 2, 10613, 119, 10702, 24}. ② = 동측 국소 19링크 = ① ∪ {10484, 10490, 10639, 10681, 10481, 10483, 10643, 10682, 129, 31, 68, 70}.
- B1 = 10639·10681 합류 병목(체인 약 4,200–5,300 m), B2 = 차로 감소·10490·10484 합류 병목(약 6,800–8,100 m). 체인 = FW_E 본선 거리(링크 74 시작 0 m).
- 번짐 분 = 100 m × 60 s 칸 혼잡(평균속도 < 60 km/h, 밀도 > 15 veh/km/차로)으로 잰 꼬리. B1 번짐 = B1 꼬리 < 4,500 m 인 분, M 번짐 = B2 꼬리 < 6,800 m 인 분(`SP/rmcause/o1o4/work/tails.py:6-15`).

## 1. 쉬운 요약

1. 무엇을 바꾸나: v3c3 FW_E 의 DSD 63·64·65·66(링크 2, 차로 1–4, 체인 6,733.2 m)을 **900 s 에 분포 91(90–92 km/h)로 한 번 쓰고 9,000 s 까지 둡니다**. 그 밖은 NC3 와 같습니다(도시 신호 native, 미터 쓰기 없음, 같은 수요·경로·시드·SimRes 10).
2. 왜 이 자리·이 값: codex VSL 단독 팔도 같은 번호의 DSD 63–66 을 900–9,000 s 에 "90" 으로 썼습니다. 다만 그 망(64cf)은 표지를 차로 감소 500 m 앞으로 옮겼고, v3c3 는 원래 자리(108.5 m 앞)입니다. "90" 은 v3c3 에서 우리 줄기가 분포 91 로 씁니다.
3. 준비 폴더 3개는 만들었고, 정적 점검·드라이런을 VISSIM 없이 통과했습니다 [실행]. 런은 띄우지 않았습니다.
4. 비교는 같은 시드 VSL − NC3 를 시드별로만 적습니다. 주 표는 Ω701·Ω635·④a·④b(첫 관측 차분)·④·Ω 밖·①·②·입력별 ④b, 그리고 B1·B2 셀별 속도·흐름, 번짐 분, VSL 구역 준수입니다.

## 2. VSL 단독 팔의 정의

### 2.1 표지(DSD) — codex seg13 DSD 63–66 의 v3c3 짝

| 항목 | v3c3 (이번 런) | 64cf (codex VSL 단독 팔) | 근거 |
|---|---|---|---|
| DSD 번호·이름 | 63·64·65·66, `RW_VSL_RW_FW_E_S5_L2_LN1..4` | 같음 | [실행] RR 망 inpx:4654-4685; [읽음] `D:/VISSIM_runs/vsl_repro_s29/prepared_vsl/network/*.inpx:4668` |
| 링크·차로 | 링크 2, 차로 1–4 | 같음 | [실행] 같은 줄 |
| 링크 위 위치 | 3,998.67 m | 3,607.22 m | [실행] 같은 줄 |
| 체인 위치 | **6,733.2 m** | 6,341.7 m | [계산] 링크 2 시작 2,734.527 m + 위치; [읽음 `codex_handoff/R_NET.md:117-118`] |
| 4→3 차로 감소(커넥터 10613, 6,841.743 m)까지 | **108.5 m** | 500.0 m | [계산]; [읽음 R_NET:117-118] |
| plant 31칸 셀 | 셀 18(6,666.3–6,841.7 m) | 셀 16 | [읽음 R_NET:117, `codex_handoff/VERIFY_TAKEOVER.md:134`]; [실행] 셀 경계 = `SP/c_port/vsl/out/v3_cx_T004500.json /geom/lengths_km` 누적 |
| 다음 하류 DSD | 67–69(링크 24 @652.70 m, 3차로) = 체인 8,090.8 m | 같음 | [실행] inpx:4686-4709 |
| VSL 이 걸리는 구간(표지 → 다음 DSD) | 6,733.2–8,090.8 m (1,357.6 m) | 6,341.7–8,090.8 m (1,749.1 m) | [계산] |
| 구간 안 진출입 | 진출 10481(6,826.8 m)·10483(7,240.3 m), 합류 10490(7,243.1 m)·10484(7,603.7 m) | 같음 | [읽음 `SP/rmcause/phys/fwe_scan.py:30-33`] |
| 쓰기 전 값 | 네 차종(10·20·30·70) 모두 분포 110 | 같음 | [실행] `RR/build/check_receipt.json /checks/s31/dsd_63_66` |

- 왜 "짝" 인가 [읽음·추론]: 번호·이름·링크·차로·행동 키(`RW_FW_E_S13`, R_NET:124-125)가 codex 팔과 같습니다. 다른 것은 위치 하나입니다. codex 는 64cf 에서 이 DSD 만 500 m 상류로 옮겼고(R_NET:116-119), 우리 옛 망과 v3c3 는 3,998.67 m 그대로입니다. 위치를 옮기면 망이 바뀌어 "NC3 와 같은 망" 조건이 깨지므로 옮기지 않습니다.
- 그래서 v3c3 에서는 감속이 차로 감소 108.5 m 앞에서 시작합니다. 감속 구간이 짧고, 진출 10481 갈림(6,826.8 m)이 표지 93.6 m 뒤입니다 [계산]. codex 팔과 같은 크기의 반응이 나올지는 모릅니다 [추론]. VSL_OFFLINE r2 §4.1(4) 도 이 점을 적었습니다 [읽음 `SP/c_port/VSL_OFFLINE.md:233`].
- 진입 램프 차(10490·10484)는 DSD 63–66 을 지나지 않아 분포 91 을 받지 않습니다 [추론, DSD 는 지나는 차에만 씀]. §6.6 의 준수 표가 이것을 셉니다.

### 2.2 속도 — 명령 90 = VISSIM 분포 91

- 쓰는 값: 분포 **91** = (90 km/h, 0)–(92 km/h, 1) 균등 [실행 inpx:5139, `check_receipt.json /checks/s31/distribution_91`].
- 까닭 1 (codex 팔과 같은 명령): codex VSL 단독 팔은 DSD 63–66 에 "90" 을 썼습니다 [읽음 `D:/VISSIM_runs/vsl_repro_s29/vsl.json`]. 이 PC 에 있는 VSL 반응 기록(64cf-s29 VSL 단독, window 팔)도 모두 90 입니다 [읽음 VSL_OFFLINE:30-31]. plant 탐침도 90 에서 4상태 모두 비용 증가를 냈습니다 [읽음 VSL_OFFLINE:28]. 그래서 90 이 plant 와 VISSIM 을 맞대기에 가장 정보가 많은 값입니다 [추론].
- 까닭 2 (v3c3 에서 "90" 이 뜻하는 분포): v3c3 는 단일값 VSL 망입니다. 우리 줄기는 명령 90 을 분포 91 로 씁니다 [읽음 GWT8 `evaluation/controllers/vsl_command_distribution.py:11-12`, `diagnostics/sdmpc_n31_20260924/config_n31_v2.json:7601-7609`]. plant 의 VSL 법칙 L2 도 81/91/101 단일값 런으로 맞췄습니다 [읽음 기억 `vissim-vsl-fixed-dsd-20260928.md`, `vissim-repin-v3c3-20261001.md`]. 그래서 O2(plant 충실도)와 나중 폐루프에 쓸 VISSIM 반응은 91 이어야 합니다 [추론].
- codex 와 다른 점(밝혀 둠): codex 는 64cf 에서 분포 **90**(넓은 분포 85–120 km/h, 평균 97.1 [계산 꺾은선 누적분포]; 두 망에서 같은 정의 [읽음 R_NET:111])을 썼습니다. v3b 에서 분포 90 과 91 은 B2 방류 차가 없었고(+0.56 %, 구간 [−1.74, +2.85]), 91 이 자유류에서 더 느렸습니다(−21.0 대 −18.8 km/h) [읽음 기억 `vissim-vsl-fixed-dsd-20260928.md` N1F 1단계]. 그러니 이번 결과와 codex 숫자의 차에는 망·표지 위치·분포가 함께 섞입니다.
- 러너 허용 범위: 110 → 91 은 150 s 당 20 이하 변화 조건을 지킵니다(|91 − 110| = 19) [읽음 `SIM3/fast_fixed_profile.py:94-95`; 실행 `check_receipt.json event_jump_le_20 true`].

### 2.3 시간 창

- **900 s 에 한 번 쓰고 9,000 s 까지 둡니다**(되돌리기 없음). codex VSL 단독 팔과 같습니다(`vsl.json`: time_s 900 네 줄, 끝 9,000) [읽음].
- VSL_OFFLINE r2 §4.3 R1 은 1,800–5,700 s 창을 적었습니다 [읽음 VSL_OFFLINE:247]. 이번 선언은 codex VSL 단독 팔과 같은 900–9,000 s 로 고정합니다(D-K9-95 와 이번 작업 지시).
- 0–900 s 는 NC3 와 같아야 합니다(§6.2 V3 로 확인).

### 2.4 그 밖은 NC3 와 같음 — 같은 것과 다른 것

| 항목 | VSL 팔 | NC3 | 근거 |
|---|---|---|---|
| 시드 | 31 · 41 · 43 (모두 fit 시드) | 같음 | [실행] 망 `<simulation randSeed>` |
| 끝 시각·해상도 | 9,000 s, SimRes 10, SimPeriod 9,001 | 같음 | [실행] `native_simulation.csv` |
| 수요·경로·도시 신호 | 망에 저장된 그대로, COM 쓰기 0 | 같음 | [읽음 `SIM3/fast_nc_runner.vbs:216-282`(수요·경로·신호 쓰기 없음)] |
| 미터 | 쓰기 없음 → native OFF | 같음 | [실행] `fixed_profile.json meter_commands []`; 끝에 미터 SG 소유가 처음과 같아야 검증 통과(`fast_fixed_profile_verify.py:160`) |
| VSL | DSD 63–66 × 4차종 = 91, 900 s, 16줄 | 쓰기 0 | [실행] `fixed_events.csv` |
| FZP | 5 s, 5.1 s 부터 | 같음 | [실행] `vehicle_recording.csv`; [읽음] NC3 FZP 첫 행 5.10 |
| 러너 모드 | fixed_profile(900 s 에 멈춰 쓰고 이어 감, 0·9,000 s 에 DSD·SG 상태 읽기) | native_fzp_only(한 번에 끝까지) | [읽음 `fast_nc_run.ps1:13-39`, `fast_nc_runner.vbs:319-383,444-476`] |
| 망 바이트 | NC3 망 + 기록 전용 절 | NC3 망 | 아래 |

- **망이 NC3 바이트와 다른 까닭** [읽음·실행]: fixed_profile 준비기는 LDP 기록이 켜진 망만 받습니다(`fast_fixed_profile.py:54-55`). 끝 검증도 LDP 파일을 읽습니다(`fast_fixed_profile_verify.py:75-79,163`). NC3 망은 `scDetRec writeFile="false"` 입니다(NC3 inpx:5423). 그래서 rule-RM 팔과 R2c 가 쓴 망을 그대로 씁니다.
  - 그 망 = NC3 망 + 기록 전용 차이: 검지 측정 58개·검지점 58개 삽입(각 59줄, 빈 줄 포함), 평가 켬 8줄(dataColl, delays, linkResults, nodeRawData writeFile, queues, scDetRec, vehTravTmRawData, vehTravTms) [실행 `check_receipt.json network_diff_vs_nc3_blocks`]. 차량 움직임 설정(수요·경로·속도분포·신호·DSD)은 바뀌지 않습니다 [실행 diff].
  - s31·s41 = rule-RM 팔 망과 바이트 같음(04630354…, e4953eaf…). s43 = rule-RM s31 망에서 `<simulation>` 한 줄만 NC3 s43 줄로 바꾼 것(94318d4d…). NC3 시드 파일끼리는 이 한 줄만 다르고(31013행), s43 의 NC3 대비 차이 내용은 rule-RM s31 의 NC3 s31 대비 차이와 같습니다 [실행 `build_receipt.json`, `check_receipt.json network_diff_vs_nc3_equals_rm31_vs_nc31 true`].
  - 이 망·모드가 교통을 바꾸지 않는다는 근거: rule-RM s31(같은 망 바이트, 같은 fixed_profile 모드, 900 s 부터 미터 COM GREEN)과 NC3 s31 의 FZP 데이터 행은 **2,410.1 s 까지 같았습니다**(첫 미터 RED 2,408 s 뒤) [실행 이번 자체 시험 `VS/selftest/firstdiff/firstdiff_selftest_rm31_vs_nc31.json`, O1 기록 `rmcause/o1o4/O1_RULE_RM_V3C3.md:68` 과 같음]. 895.1 s 까지 행 387,397개 sha 같음 [실행]. s41 은 O1 기록상 1,530.1 s 까지 같음 [읽음 O1:68]. s43 는 이번 런의 V3 점검이 처음입니다.
- 작업 지시의 "같은 망 sha 3de889f0…" 와 다른 점을 여기 밝힙니다: 3de889f0 은 NC3 s31 망이고, VSL 팔 s31 망은 04630354 입니다(기록 절만 다름). 위 근거로 교통 설정은 같다고 봅니다 [추론, V3 로 런마다 확인].

## 3. 준비 폴더 (만들었음, VISSIM 0)

### 3.1 만든 법 [실행]

- 빌더 `VS/tools/build_vsl.py`(sha256 55d3ae33…) 하위 명령 `build`:
  1. sim3 코드 6개 sha 가 rule-RM/R2c 빌드 때와 같은지 확인(fast_fixed_profile.py a05eb0c5, fast_nc_prepare.py eb1bd0f0, fast_fixed_profile_verify.py 91441391, fast_nc_run.ps1 269345da, fast_nc_runner.vbs bf07acda, validate_native_signal_record.py 4a647072). fast_fixed_profile.py 는 sim3 HEAD 673eece9 대비 작업 트리 수정(+7줄, rule_step 안 점유율 잡음 고정)이지만 RM·R2c 런이 쓴 바로 그 바이트입니다 [실행 git diff --stat, `r2c_checks.json`].
  2. 망 바이트를 §2.4 조리법으로 만들어 `RR/source/baseline_s<S>_v3c3vsl.inpx` 로 씀(창 제목으로 자기 VISSIM 을 찾으므로 망 파일 이름이 시드마다 유일, `fast_nc_run.ps1:119-121`). `#data#` 자산(.sig 41개·jpg)은 NC3 준비 폴더 핀과 sha 를 맞춰 복사.
  3. 프로필 `GT/profiles/vsl91_t900_s<S>.json` = rule-RM 팔 `fixed_profile.json` 과 같은 키, `vsl_commands` 만 4줄(900 s, DSD 63–66, 91), 망 sha·시드만 시드별.
  4. sim3 의 `fast_fixed_profile.prepare()` 를 그대로 불러 `RR/s<S>/prepared` 를 만듦(python -B, sim3 쓰기 0).
- 리허설(같은 단계를 scratch 트리에) 두 번 뒤 실제 위치에 만듦. 첫 리허설의 두 결함(시드 31 단언, 기대 인자 글의 replace)은 고친 뒤 실제 빌드 전에 sha 를 LOG 에 적었습니다 [실행 LOG 10:21 항목].

### 3.2 파일과 sha256 [실행]

| 시드 | 망 inpx | prepared.json | fixed_profile.json(=GT 프로필) | fixed_profile_proof.json | native_simulation.csv |
|---|---|---|---|---|---|
| 31 | 046303541667838f30045a06d230fb5b31944a18db483770539dfcc873176f0d | 79eefd753a3f0717e5cad254b120bb3a38ef52ea47979e6dbc0e667d8c91a52a | c832cfdc862183e22e2ac61a140baa7daf3be3012ae009d91feebea5259a0702 | 1c145d49f0d50943b959b9d30d29ea258d5f67a84a3a1a862ee812f337cd3839 | 68864caba5c49c6173591063a570bbfb158e43676609bd5639e581cec47c7136 |
| 41 | e4953eaf8c8f983f28b9a14c684075757ddd45e180e63f2235dc9db8b4ed7524 | 27ccd7ba91410153d28ca62709bbbeb68d99969f5ca4f9c1d360a53ff2a039ed | 7228d999913eb967bfbf8a155820a6fb5beda43afd45398761da024bf5df654e | 4933049e32caa326535d556a15298c947364d3a31ff67928b1f07cfa829ce86b | bdf93db36b044cfb1eeb7417ed3edb8ffccf8f5eb25aff78ac9b18de6532629b |
| 43 | 94318d4d1c235fa800da70cbcfff85e13567092a86c628e62010b9b03396549f | 36170f2d3fb1852e3002498b80d370bb5ddfe3e8f3fbcb3b30fc6360e76aed45 | 427e264affe834682e12fbdfc3df20072da8ec5f64d24e6a02cc760020f1e151 | ccc091c6ef78199f596faf7044ec4dc04e102e0efda820f69b6713e22e5cca8b | 99b7292e2939676d3427332c4264678ec3c84520b206b1a362d90a55c83d9cfa |

- 세 시드 같음: `fixed_events.csv` 17abe578c75e6a873fdd782c40eead3e69fa95bc961fb3b815cfe6c41efce0ce(머리 + 16줄 `900,vsl,{63..66},{10,20,30,70},91`), `fixed_initial.csv` 14e47ea34d13ce7166c5904db9213b1faf91a5724a9727d9fdb26564f5de4988(864줄), `vehicle_recording.csv` aa0603b2779936edeb97227e90c130071e1a53261c5d6301dd768fdb23c82c6b.
- 영수증: `RR/build/build_receipt.json` 51fb1b9e…, `RR/build/check_receipt.json` 119f6db6…, `RR/build/dryrun_receipt.json` b98b449a…. 64자 sha 는 LOG.

### 3.3 NC3·rule-RM 준비 폴더와의 차 [실행 `check_receipt.json`]

- rule-RM 팔(s31·s41) 대비: 같은 바이트 46파일(망 inpx·자산·native_simulation.csv·vehicle_recording.csv). 다른 것 5개: `fixed_events.csv`(VSL 16줄 대 머리만), `fixed_profile.json`(`/vsl_commands` 만), `fixed_profile_proof.json`(`/event_rows`·`/event_clock`·`/vsl_locations/63..66` 만), `prepared.json`(경로·핀·증명, rule-RM 의 `rule_policy`·`network_variant`·`demand_variant` 메타 키 없음), `fixed_initial.csv`(**줄바꿈만** 다름: 우리 CRLF, rule-RM LF; 내용 같음, `diff --strip-trailing-cr`). rule-RM 에만 있는 것: `rule_policy.json`·`rule_runtime.txt`·`rule_measurements.csv`. 이 셋이 없으므로 러너는 규칙 단계 대신 이벤트 파일을 씁니다(`fast_nc_runner.vbs:330-334`).
- NC3 대비: 같은 바이트 44파일(자산·vehicle_recording.csv), 다른 것 망 inpx(§2.4)·prepared.json(모드)·native_simulation.csv(fixed_profile 은 SimPeriod 줄 하나 더), VSL 팔에만 fixed_* 4파일.
- 우리 `fixed_initial.csv` 는 codex 64cf VSL 팔의 것과 바이트가 같습니다(DSD 배정과 SG 목록이 같음) [실행 cmp].
- sim3 러너가 이벤트 파일로 VSL 을 쓴 선례: stage-1 `D:/VISSIM_runs/20260923_stage1/s31_v2vsl` 은 같은 러너(bf07acda)로 VSL 쓰기 416개를 하고 검증 통과했습니다 [읽음 run.json·fixed_validation.json].

### 3.4 정적 점검 (`build_vsl.py check`, 모두 참) [실행]

시드마다: 모드 fixed_profile·시드·끝 9,000·시작 900·명령 16줄 / snapshot 핀 50개·입력 핀 44개 다시 해시 일치 / 망 이름 유일 / s31·s41 망 = rule-RM 바이트 / NC3 대비 차이 = rule-RM s31 대 NC3 s31 차이 / `scDetRec writeFile=true` / 저장 시뮬 randSeed=S·simRes 10·simPeriod 9001 / DSD 63–66 네 차종 110 / 분포 91 = [(90,0),(92,1)] / 이벤트 16줄 정확 / 이벤트 주소가 fixed_initial 에 있음(VBS 가 모르는 주소면 멈춤, `fast_nc_runner.vbs:365`) / 110→91 변화 ≤ 20 / 프로필 핀 / `compile_profile` 다시 돌린 이벤트·초기값·증명이 파일과 같음 / 증명 = prepared.json / LDP 신호군 있음 / 규칙 파일 없음 / run 폴더·launch.log 없음.

### 3.5 드라이런 (`build_vsl.py dryrun`, VISSIM 0) [실행]

- `fast_nc_runner.vbs --check` → `SYNTAX_OK`(COM 생성 없음, VBS:3-5).
- `fast_nc_run.ps1 -Prepared … -Output …\run -MinimumFreeGiB 8 -AllowConcurrent`(**-Execute 없음**) 세 시드 exit 0. 이 경로는 snapshot 핀을 모두 다시 해시하고(ps1:21-27) 실행 명령만 출력합니다(ps1:40-44). 출력: `execute false`, `fixed_profile true`, 인자 `… <S> 9000 fixed_profile`. rule-RM 팔 `dryrun_check.txt` 와 경로 3개만 다름(s31·s41). run 폴더 생성 0. 앞뒤 PC VISSIM 0개.

## 4. 런 수·시간·자원 [추론, 근거 읽음]

- 런 3개(v3c3-s31·s41·s43), 시드마다 1번(멈춤이면 한 번 재발사, §5). 다른 VISSIM 런 0.
- 시간: 같은 러너·망의 rule-RM·R2c 런이 98–110분(동시 2–4개) [읽음 run.json started/finished]. 세 런 동시면 벽시계 약 2시간.
- 디스크: 런당 약 1.2 GB(D:) [읽음 rule-RM·R2c run 폴더 du]. C·D 가 8 GB 미만이면 멈춤.

## 5. 자리 인식 발사기 (고정, 아직 띄우지 않음)

- 스크립트 `VS/tools/vsl_launcher.ps1`(sha256 cbc37aff…), 시작기 `VS/tools/vsl_launcher_start.ps1`(d038e32c…; 발사기 sha 대조·중복 실행 거부·디스크 확인 뒤 WMI `Win32_Process.Create` 로 분리 시작, 영수증 `RR/vsl_launcher_start_receipts.log`). 둘 다 PowerShell 5.1, ASCII.
- 매 60 s:
  1. 멈춤 조건: `RR/STOP_VSL_LAUNCHER`(또는 `RR/STOP`) 파일, 고정 파일 8개 sha 변화(러너 ps1·vbs·검증 py 2개·prepared.json 3개·발사 줄 파일), C 또는 D < 8 GB, 런의 비정상 끝 → `_launcher/LAUNCH_STOPPED.json`(재시작해도 유지). 이미 도는 런은 건드리지 않습니다.
  2. 자리: 배타 잠금 `_launcher/seat.lock` 아래에서 PC 전체 `^VISSIM` 프로세스 수 + 우리가 띄웠지만 VISSIM 이 아직 안 보이는 런(발사 뒤 600 s 안) 수 < 4 일 때만, 한 번에 한 시드(31 → 41 → 43).
  3. 한 번만: WMI 전에 `_launcher/launched_s<S>_run<A>.json` 을 CreateNew 로 만듦. 있으면 다시 띄우지 않음(재시작 뒤에도). 발사 줄 = `RR/launch_lines_vsl.txt`(0456cf45…) 의 줄과 같은 글(`cmd.exe /c powershell.exe … fast_nc_run.ps1 -Prepared RR\s<S>\prepared -Output RR\s<S>\run -Execute -MinimumFreeGiB 8 -AllowConcurrent > RR\s<S>\launch.log 2>&1`), CurrentDirectory RR. 영수증 `_launcher/receipt_*.json` + `RR/wmi_launch_lines_vsl.txt` 한 줄.
  4. 멈춤(사용자 방침 "정상보다 5분 넘게 진행 없으면 확인 → 그 런의 PID 만 죽이고 한 번 재발사 → 기록"): 러너 ps1 이 fixed_profile 모드에서 FZP 시각이 300 s 안 늘면 자기 cscript·VISSIM 만(PID + 시작 시각) 죽이고 `Startup300s`/`Progress300s` 로 끝냅니다(ps1:128-152). 발사기 뒷받침: `progress.csv` 가 600 s 안 늘었는데 런의 cmd 가 살아 있으면 run.json 의 cscript·VISSIM PID(시작 시각 대조)만 죽이고 `_launcher/backstop_kill_*.json` 기록. 이름으로 죽이지 않습니다. 멈춘 1차는 한 번만 2차로 재발사(`run_retry1`, `launch_retry1.log`). 2차도 멈추면 비정상 → 발사 중단.
  5. 끝: 도는 런이 없고 띄울 것도 없으면 종료. 24시간 넘으면 종료. 두 번째 발사기는 instance.lock 때문에 exit 2.
- 드라이런 시험 [실행 10:28]: `VS/tools/test_vsl_launcher.py`(b1725433…) 시나리오 9개 모두 PASS(자리 대기, 멈춤 뒤 한 번 재발사, 비정상 끝 → 중단, 디스크 부족, 재시작 뒤 중복 0, 뒷받침 kill 은 자기 PID 만, 두 번째 멈춤 → 중단, STOP 파일, sha 변화). WMI·kill·VISSIM 0. 결과 `VS/dryrun/test_result.json`(45101519…).
- 감시: 이 세션은 발사기 로그 `RR/vsl_launcher.log`, 각 `run/progress.csv`·`run.json` 을 읽기만 합니다. codex·다른 세션 VISSIM 은 세기만 합니다.

## 6. 비교 규칙 (데이터 전 고정)

### 6.1 짝·시드·형식

- 주 짝 = **VSL − NC3**, 같은 시드. 시드 3개(v3c3-s31·s41·s43), 시드마다 짝 하나. 시드끼리 평균·검정 없음. 표마다 "시드 n" 을 적습니다(못 낸 시드는 빼고 실제 수).
- 쓸 런 = 발사기 기록상 그 시드의 마지막 완료 시도(1차, 또는 1차가 멈춰 2차가 완료면 `run_retry1`). 재발사 런은 표에 "재발사" 표시.
- 두 적분 꼴(B 규칙과 같은 정의 [읽음 `codex_handoff/b/COMPARE_RULE_B.md` §2]): **주 = 우리 꼴 [0, 9000] s**(5.1–8,995.1 s 프레임 사다리꼴), 보조 = codex 꼴 [0, 8100] s(시각축 사다리꼴, 8,100 s 까지 마지막 재고 유지). ④b 첫 관측 창 끝 W = 9,000 / 8,100 s.
- veh·h 소수 첫째, km/h 소수 첫째, veh/h 정수, 몫 소수 셋째. 부호 표시. 반올림은 마지막 한 번. 파일이 없거나 런이 못 쓰면 "못 냄(까닭)", 0 으로 채우지 않음.
- 판정 낱말 없음. 문턱 없음. Ω 줄은 ④·Ω 밖 줄과 같은 표에서만 보고합니다.

### 6.2 유효성 점검 (미리 정함)

- **V1 런 완료**: run.json `completed true`, `exit_code 0`, `fixed_profile_validation_exit_code 0`, `fixed_validation.json passed true`, stdout 에 `STAGE=SIM_DONE`·`SIM_SEC=9000`. 실패 → 그 시드 모든 칸 "못 냄(V1)".
- **V2 명령**: `fixed_readback.csv` 쓰기 행 = 정확히 16개(900 s, vsl, DSD 63–66 × 차종 10·20·30·70, expected = actual = 91, ok 1), 미터 쓰기 0, 끝(9,000 s) DSD 63–66 읽기 = 91. 쓰지 않은 DSD·SG 상태가 처음과 같음은 검증기가 이미 요구(verify:153-161). 실패 → "못 냄(V2)".
- **V3 900 s 전 짝**: VSL 과 NC3 FZP 의 데이터 행 중 시각 ≤ 895.1 s 가 모두 같음(행 수·sha256, `vsl_firstdiff.py` 와 vhr 스캔 `lf_sha_le_895_1` 둘 다). 첫 다른 행의 시각을 적음(900.1 s 이상이 예상 [추론]). 다르면 그 시드 모든 칸에 "†접두 다름" 을 붙이고 따로 보고(런은 버리지 않음).
- **V4 도착 수**: 첫 관측 총수(9,000 s) VSL 대 NC3, 첫 링크 74(1098)·26(1099)·그 밖. 첫 관측 차분은 "같은 시드·같은 망이면 도착열이 같다" 는 가정 위의 값이므로 이 수를 함께 적습니다.
- **V5 준수 바탕**: NC3 의 VSL 구역 안 희망속도 89–93 몫(데이터 전 실행: 세 시드 모두 0, 구역 안 희망속도는 모두 98–141 칸 [실행 `VS/out/cell/nc3_s*.json`]).
- **V6 도구 일치 [STOP]**: `vsl_metrics.py` 가 같은 식으로 B 표의 `j1-nc3` 칸 72개(꼴 둘 × 지표 12 × 시드 3)를 `CW/vhr_b/v3c3_all.json`(f982fbff…)과 0.001 반올림까지 같게 다시 내야 합니다. 데이터 전 자체 시험에서 72/72 같음(최대 차 0) [실행]. 분석 때 다시 돌려 하나라도 다르면 VSL 숫자를 내지 않고 멈춥니다.

### 6.3 T1 — Ω·④·Ω 밖 (시드별 VSL − NC3, 꼴 둘)

| 줄 | 정의 |
|---|---|
| Ω635 · Ω701 · Ω701 − Ω635 | 해당 링크 체류 합의 차. Ω701 = `D:/VISSIM_handoff/20261024/derived/omega_membership_exact.json`(efdfaeb1…) inside, Ω635 = GWT8 `diagnostics/control_area_membership.json`(4863f5ee…) inside(읽기만) |
| ④a | 모든 링크·커넥터 체류 합의 차 |
| ④b (주) | 첫 관측 차분 dU = S_NC3 − S_VSL, S(W) = Σ_{첫 관측 ≤ W} (W − t_첫)/3600 |
| ④ | ④a + ④b |
| Ω 밖 (a)·(b), Ω701·Ω635 기준 | ④ − Ω, ④a − Ω |
| ① · ② | FW_E 본선 7링크 · 동측 국소 19링크 |
| 입력별 ④b | 첫 관측 링크 74 = 1098(FW_E 입구), 26 = 1099(FW_W 입구), 그 밖 = 도시 입력 |
| 수준값(참고) | VSL·NC3 각각의 링크 지표와 S(W) |

### 6.4 T2 — FW_E 구역·시간 (fwe_scan 100 m × 60 s 격자 + tails)

- 구역(칸 가운데 기준, m): U 0–4,200 · B1 4,200–5,300 · M1 5,300–6,300 · Mu 6,300–6,700(표지 바로 앞, codex 표지 자리 포함) · VS0 6,700–6,800(표지 6,733.2 가 든 칸) · B2 6,800–8,100(차로 감소·10483·10490·10484) · D 8,100–10,800.
- 창(s): 0–900(짝 확인, 0 이어야 함) · 900–1,350 · 1,350–1,800 · 1,800–2,250 · 2,250–2,700 · 2,700–3,600 · 3,600–4,500 · 4,500–6,300 · 6,300–8,100 · 8,100–9,000 · 900–4,500 · 4,500–9,000 · 900–9,000.
- 칸마다: 구역 공간평균 속도(Σv/N)와 veh·h, 단면 통과 흐름 4,200·5,300·6,300·6,800·7,300·7,700·8,500 m(veh/h), 합류 흐름 10639·10681·10490·10484, 램프 대기(속도 < 15 km/h) veh·h, 링크 74 삽입률, 6,700–8,000 m 차로별 속도, **B1 번짐 분·M 번짐 분**·꼬리 최상류. VSL·NC3 수준값과 차를 함께.

### 6.5 T3 — 셀별 병목 (31칸, vsl_cell_scan)

- 셀 8–14(B1 쪽: 진출 10643 셀 9, 합류 10639 셀 10, 진출 10682 셀 11, 합류 10681 셀 12)와 셀 16–25(표지 셀 18, 차로 감소 셀 19 시작, 진출 10483 셀 20, 합류 10490 셀 21, 10484 셀 23) [읽음 plant 기하 `/geom/ramps`·`/offramps`].
- 창: 900–1,350 · 1,350–1,800 · 1,800–2,250 · 2,250–2,700 · 2,700–3,600 · 3,600–4,500 · 4,500–6,300 · 6,300–9,000 · 900–9,000. 원자료는 60 s 칸으로 저장.
- 값: Edie 정의 — 속도 Σv/N, 흐름 q = Σv·5 s/(L·T)(모든 차로 합, veh/h), 밀도 k = N·5 s/(L·T)/차로(veh/km/차로), 희망속도 89–93 몫. VSL·NC3·차.

### 6.6 T4 — VSL 준수 (구역 6,733.2–8,090.8 m)

- 차량-프레임 중 희망속도 89–93 km/h 몫(VSL·NC3), 구역에 처음 들어온 차 중 그 몫, 희망 89–93 차의 실현 속도 평균과 칸별 몫(0–60·60–80·80–88·88–95·95–100·100 이상), 그 밖 차의 실현 속도, NC3 구역 전체 실현 속도. 창은 §6.5 와 같음(450 s 칸 저장).
- 읽는 법(정의만): 표지를 지난 본선 차는 91 을 받아야 하고 램프 합류 차는 받지 않습니다. 몫이 1 보다 작은 만큼은 합류 차·표지 전 진입 차입니다 [추론].

### 6.7 함께 적되 빼지 않는 참고값

- codex 64cf-s29 VSL 단독 − NC(한 시드, 다른 망·다른 표지 위치·분포 90, 0–8,100 s): Ω701 −165.2 / ④ −77.6 / Ω 밖 (a) +87.6, ④b 첫 관측 +79.6(1098 +73.9), ① −139.2, B1 번짐 62 → 0 분 [읽음 VSL_OFFLINE:30,161]. 이번 숫자 옆에 "다른 망 참고" 로만 둡니다.
- NC3 체제: B1 번짐 0/0/2 분, M 번짐 0/12/3 분(s31/41/43) [읽음 `rmcause/INV_PHYSICS.md:91-93`]. 64cf-s29 NC 는 62/19 분의 붕괴 체제였습니다.

## 7. 도구 (고정, sha256 은 LOG)

### 7.1 목록

| 파일 (VS/tools) | sha256 | 할 일 |
|---|---|---|
| `build_vsl.py` | 55d3ae335b8667fcbc89def7b35028352e357a7885c3e7b2d3f857f3042f164c | 준비 폴더 build·check·dryrun·launchlines (끝남) |
| `vsl_launcher.ps1` | cbc37aff191ef1cf53c247a8b2c29f4b1686e10bd4aadeef6bf34fb8bdebff4e | 자리 인식 발사기 (§5) |
| `vsl_launcher_start.ps1` | d038e32c4354421b3c841110a3822d03a27c8bfce62d1e5cd528548e34c89530 | 발사기 WMI 분리 시작 |
| `test_vsl_launcher.py` | b1725433b566ec73f65fa62600a598f6044b2b7e8894ab2e8ffea84a80c8034f | 발사기 드라이런 시나리오 9개 |
| `vsl_heavy.ps1` | 479a7e69b09190aa840d04d5a98ab42f67672bff7342bd25d286aa4611b52492 | 공유 잠금 `D:/VISSIM-merge/k8_gate_trees/heavy.lock` 아래 무거운 python 차례 실행(WMI·BELOW_NORMAL·PYTHONHASHSEED=0·python -B·스레드 1) |
| `vsl_vhr.py` | 52086b7c095f0164dace251f5a379d26e101b197a362348cf23a4648a7b85900 | 고정 B 사본 vhr_scan_b.py(0c445bc4…)·vhr_firstseen_b.py(d5c3c126…)를 sha 확인 뒤 모듈로 불러 출력 폴더만 바꿔 실행 |
| `vsl_cell_scan.py` | fa5aeafd01c99297652f8f5fce6d5f760cdbb223640b3258d2020cd03229a078 | 31셀·100 m 칸·VSL 구역 준수 스캔 |
| `vsl_firstdiff.py` | a8ec13d95e0cbcdffd93aeceebb9f68fd37da853e2ad8c5762e3bf40a81bdfa7 | 첫 다른 FZP 행·895.1 s 접두 sha |
| `vsl_metrics.py` | 160c23c76d354b769718ab31044782609b96e238196b2bf1817ef053aacca71c | T1–T4·V 점검·V6, 출력 `VS/out/vsl_metrics.json`·`vsl_tables.md` |
| `vsl_analysis_jobs.py` | 7d4a71cc29656832c434c33942b6f9ce018cd533c396cee44dfa951c45e969dd | 런 뒤 작업 목록 `jobs_analysis.json` 생성(도구 sha 대조, 런 고르기) |
| `analysis_tool_pins.json` | 260deb96d8d4345ccca1aa6c077216bd2b9f93495c782c5ee0fffe9fac41ff93 | 위 분석 도구 4개 sha |
| 고치지 않고 쓰는 것 | `SP/rmcause/phys/fwe_scan.py` 0619e9fc…, `SP/rmcause/o1o4/work/tails.py` cb6c0bd4…, `CW/vhr_b/vhr_scan_b.py` 0c445bc4…, `CW/vhr_b/vhr_firstseen_b.py` d5c3c126… | |

- NC3 쪽 입력(데이터 전부터 있음, 핀): vhr 스캔 `CW/vhr_b/scan_out/nc3_s31·41·43.json`(f3fe787c…·1ae351a8…·fb90d49b…)·`first_nc3_s*.json`(e1da8eb8…·97631212…·ebcf0b5b…), fwe 스캔 `SP/rmcause/phys/scan/nc_s31·41·43.json`(352bddd3…·65051df0…·7afd43e8…), 셀 스캔 `VS/out/cell/nc3_s31·41·43.json`(6345ce94…·70ef1f26…·a67a8751…, 이번에 데이터 전 생성).

### 7.2 데이터 전 자체 시험 [실행]

- 셀 스캔(NC3 세 시드, 각 29–32 s): 체인 veh·h 가 fwe_scan 의 `chain_veh_h_5s` 와 정확히 같음(s31 1,816.98, s41 1,964.12), 6,000–8,600 m 칸 차량-프레임 수도 fwe_scan 격자와 같음(293,680, 348,858). 구역 안 희망 89–93 몫 0.
- 첫 다른 행: rule-RM s31 대 NC3 s31 → 2,410.1 s(O1 행 내용 기준 값과 같음), 895.1 s 접두 같음(8.7 s).
- `vsl_metrics.py selftest`: V6 72/72 같음(B 표 Ω701 −157.0/−523.4/−222.2, ④ +175.1/−230.6/−450.6, Ω 밖 (a) +332.1/+292.9/−228.4, 1099 ④b +490.0/+468.4/+84.0 을 다시 냄), 물리·셀 부분(VSL 칸 = NC3)의 차 모두 0. 출력 `VS/selftest/vsl_metrics.json`(1055689f…).
- 런 모드 배관 시험: 가짜 런 트리(s31 완료, s41 재발사 완료, s43 미완)와 NC3 대역 스캔으로 `VSL_METRICS_TEST_ROOT` 아래 실행 → s41 은 2차 시도를 고르고 s43 은 모든 칸 "못 냄" [실행 `VS/runmode_test/out/vsl_tables.md`].
- 작업 목록 생성기: FZP 가 없을 때 metrics 한 줄만 냄을 확인하고, 그 시험 파일은 `VS/selftest/jobs_analysis_TEST_predata.json` 으로 옮김(실제 파일은 런 뒤 새로 만듦).

### 7.3 분석 차례 (세 런이 끝난 뒤)

1. `python -B VS/tools/vsl_analysis_jobs.py` → `VS/tools/jobs_analysis.json`(sha 를 LOG 에).
2. `vsl_heavy.ps1 -Jobs …\jobs_analysis.json` 을 WMI(BELOW_NORMAL)로 분리 시작. 잠금을 얻은 뒤 차례로: vsl_vhr(세 FZP) → 시드마다 fwe_scan·vsl_cell_scan·vsl_firstdiff(VSL 대 NC3) → vsl_metrics run. 잠금 heavy.lock 이 있으면 30 s 마다 기다림(C1 워크플로와 공유).
3. 보고서는 `VS/out/vsl_tables.md` 숫자를 옮겨 씁니다. 계획 밖 분석은 "사후(계획 밖)" 로 따로 표시합니다.

## 8. 이 런이 알려 주지 않는 것 [추론]

- 시드마다 짝 하나뿐입니다. 무제어 5시드 전체망 σ 약 1 % 입니다 [읽음 기억 `vissim-seed-variance.md`]. 900 s 뒤의 차에는 VSL 몫과 궤적 갈림(혼돈성) 몫이 섞입니다.
- codex 결과와의 차를 망·표지 위치(108.5 대 500 m)·분포(91 대 90)·수요(1099 다름) 중 어느 것 몫으로 가르지 못합니다.
- v3c3 NC3 는 B1 번짐이 거의 없는 체제라, codex 팔의 "B1 번짐 제거" 같은 길이 생길 자리 자체가 작을 수 있습니다.
- plant 가 이 반응을 맞추는지(O2)와 φ·ρ_crit(O1)는 이 런으로 답하지 않습니다.
- 폐루프 VSL 의 가치는 이 고정 처치로 알 수 없습니다.

## 9. 하지 않은 것

- VISSIM·COM 실행 0, 런 발사 0, 발사기 시작 0. kill 0.
- 커밋·푸시·동결 0. GWT8(`D:/VISSIM-merge/sim3-n31-k8`)·sim3·frozen·기존 런 폴더(V3·vsl_repro_s29·stage1)·Y: 쓰기 0(읽기만). 쓰기는 VS, RR, GT(프로필·리허설 영수증), 리허설 트리(지움)뿐.
- 금지 시험 0. sealed/ 열기 0, 봉인 시드 자료·숫자 0.
- 무거운 python 은 공유 잠금 아래 한 번(10:34:46–10:36:26 KST, NC3 셀 스캔 3개 + 첫 다른 행 시험 1개). 잠금은 끝에 지움.

## 10. 변경 기록

- 2026-10-27 KST: 첫 판(런 전).
