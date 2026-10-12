# K9-1 — W1·W2-A·F17b·Z1 (키 전용, D-K9-1…6)

구속: `K8_PREDECLARATION_AMENDMENT_19.md` r2(sha `4ccfd8fd1efb6f79c59161ab40d4aa9234fa729bc980c89c1c9ad3059cd420d8`), 사용자 결정 `K9_1_USER_DECISIONS_20261010.md`(sha `b09bed04…`, D-K9-1…6: K9-1 = W1 + W2-A + F17b C4 + 잠복 키 접촉 Z1, F14는 철회되어 K9-2), 보충 20(sha `2cfbddbf…`; F14 부분 무효, §2.4의 L1 과소 차단 기구 M1·M2는 아래 '알려진 결함'). 미니 탐침 `D:/VISSIM-merge/k9_1_probe/MINI_K91.md`(`6f779daf…`), 고정 패치 `patches/apply_k91.py`(`c0db9e89…`), 값 `K91_VALUES.json`(`713d232e…`). 판정 단계(보충 19 §5, 트리 k91t)는 이 폴더의 커밋들 뒤에 따로 시작합니다. 판정 상태에서 K9 키를 켠 계산은 여기까지 0회입니다(커밋 관문 G1·G2의 키 없는 §0.4 허용 목록만).

## 키 (config 키만; 모두 없으면 런타임은 K8b-5(7e079efb) 경로 + Z1-a 키 접촉)

| 키 | 항목 | 코드 | 증거(값의 단일 출처) |
|---|---|---|---|
| `urban.sc1001_wout_saturation` | W1: SC1001 → W_RAMP 신호 movement 3개 용량 C_m = s_g(m) × Σ_{l∈L(m)} β_m / Σ_{m′∈M(l)} β_m′ (29\|p3 1,727.1 measured ×2차로, 40\|p2 1,732.4 measured, 37\|p1 default 규칙값 1,726.1262230995364 × 차로 37\|1을 직진과 공유) | `runtime_setup.install_sc1001wout_saturation`(포착 시점, K8b-1 훅 직후) | `sc1001wout_saturation_v3c3_20261009.json` (`b64eadc4…`) |
| `urban.wout_side_handoff` | W2-A: SC2001 회랑 차량을 합류점(31 @350.718 m)에서 W_out으로 인계(가지 하나 `wout_handover`, 경로 78 → 10703 → 31, 출신 몫 1.0), W_out 출구 법칙에 부류 side(분할 0.4979069194779611 / 0.003447426742181729 / 0.4986456537798572, 길이 0.061282 / 0.384282 / 0.384282 km) | `runtime_setup.install_wout_side_handoff`, `sc2001_corridor.install_wout_handover`·`advance`(받는 여유 = `uqm._effective_available_space(W_out)`), `urban_flow_accounting.wout_side_handoff_land` | `wout_side_handoff_v3c3_20261009.json` (`4683484b…`) |
| `freeway.offramp_split_forecast` | F17b: FW_W 진출 4개(10479·10491·10638·10645) 분율 = C4 예보(끝이 (0, T]인 모든 150 s 창의 Σoff/Σelig, 같은 시드·같은 결정 묶음의 `obs150/derived_<T′>.json`), 지평 동안 고정 | `offramp_split_forecast.install`(RS, `lane_plant_runtime.initialize` 직전)·`apply`(LPR:456 `LaneFreewayRuntime` 직전) | `offramp_split_forecast_v3c3_20261009.json` (`48f7bfca…`) |
| (키 없음) Z1-a | LOR 직결 행 n ≤ 0에서 건너뛰는 예약 갈래의 due 키를 두 예약 버퍼에 값 없이 만듦(F-2 꼴) | `lane_offramp_runtime` LOR:89 블록 | — |

- 증거 빌더 `build_k9_evidence.py w1|w2a|f17b [--check]`: VISSIM 원자료에서 다시 유도(W1 = U4 F2 재측정, v3c3 NC 5시드; W2-A = K8b P-4 추출 규칙·에피소드 규칙; F17b = `f17b_select.py`(P0-3 규칙, s41·s53 시드 교차 선택, 기록 `inputs/f17b_selection_20261009.json`과 결과 필드 대조)), `--check`는 커밋된 `values`와 비트 비교. 커밋된 증거 파일은 탐침 P0 파일 바이트 그대로(`K91_VALUES.json` sha와 같음).
- 팔 파일(K9-1-4): `../config_n31_v2_stopline_observed_full_k91.json`(SAF-K91 ``5f0d0e40a39e44b3c7601f23177afbad8c2eee23d4421626482f2244a86c3341``)·`../config_n31_v2_stopline_geometric_k91.json`(SAG-K91 ``7b374787abee8788f4a9c545dd8fe835d93ffbccc8dd749d21e04aece6e188e0``) = K8b-4 팔(af2a7783 / f5189611) + K9 세 키. 생성: `python -B diagnostics/sdmpc_n31_20260924/make_config_n31.py --stopline-approach diagnostics/sdmpc_n31_20260924/stopline/sc1001eb_evidence_v3c3_20261004.json --stopline-storage observed_full|geometric --k91 [--check]`. 팔 동일성: `k8_gates/sa/sa_arms.py --source repo --k91`.

## 커밋과 커밋별 관문 (보충 19 §4; 출력 `D:/VISSIM-merge/k8b_commit_gates/<커밋>/`, 트리 `D:/VISSIM-merge/k8_gate_trees/<커밋>`, 기록 `D:/VISSIM-merge/k9_1_commit_gates/`)

| 커밋 | sha | U·B | G1 키 없음 = ec063ff | G2 키 끈 SAF = k86h | G3 키 켬 예상 차이 | G4 탐침 재현 | G5 K8b-5 패리티 | G6 adfull |
|---|---|---|---|---|---|---|---|---|
| K9-1-0 하네스(진단 전용) | `b6678a9c` | PASS (B: SA·p1·p2·p4·make_config `--k8b`) | PASS (DP 17·TL3 9×2·full 2700 = anchor) | PASS | — | — (A1 L2 기준 `k91_g4ref`, 아래) | PASS (26/26, 숫자 잎 1,071,003 / 9,889 / 475,650 차 0, 한쪽 0) | — (zdiag 보고: Z1 없는 트리의 직결 행 키 갈림 확인) |
| K9-1-0b Z1-a | `ca3c26e5` | PASS (+`test_k9_latent` 8) | PASS (**Z1-a 스칼라 비트 동일**) | PASS | — | — | PASS (26/26 차 0; Z1 접촉 6–33회/잡 = 비공허) | PASS (9/9 완전 일치, 1.62e-12…2.55e-11 = K8b-5 값; 직결 전체 상태 키 갈림 0) |
| K9-1-1 W1 | `95612e4f` | PASS (w1 `--check` b64eadc4 재유도, K91_VALUES 비트 같음) | PASS | PASS | PASS (첫 스텝 용량 3개 = §2.1 식 오차 0, 다른 movement 바이트 같음) | PASS (A1: H3 4상태·L2 H27 숫자 잎 차 0) | PASS | PASS (최대 1.18e-10) |
| K9-1-2 W2-A | `cd995ef4` | PASS (w2a `--check` 4683484b 재유도) | PASS | PASS | PASS (side 몫·길이·x_side = 증거, 가지 `wout_handover` 하나, shrink 0) | PASS (A2) | PASS | PASS (최대 2.05e-10) |
| K9-1-3 F17b | `ba9d5940` | PASS (f17b `--check` 48f7bfca, P0-3 선택 재계산 = 기록) | PASS (full 2700 = anchor) | PASS | PASS (예보 = 규칙 재계산 = J1 경로 = LFR 보유값, 오차 0·정수 계수 같음; FH s31 1650 E_W 분율 SAF-K91 = SAF-K8b 비트 같음) | PASS (A3: H3 4상태 objective 453.69278696702565 / 483.0167185008382 / 446.08002614665503 / 481.9583429860228, L2 H27 797.3329318528645, 숫자 잎 차 0) | PASS | PASS (최대 2.05e-10, 직결 키 갈림 0) |
| K9-1-4 팔·문서 | 이 커밋 | `k91_4/gate_B.json`(`make_config --k91 --check` 포함) | `k91_4/gate_G1.json` | `k91_4/gate_G2.json` | — | — | — | — (팔 동일성 `k91_4/gate_ARMID.json`) |

- 기록·sha: `D:/VISSIM-merge/k9_1_commit_gates/`(LOG.md, `k91_0_record.json` … `k91_3_record.json`, `K91_COMMITS.json`). 커밋마다 트리는 `git archive`, 런타임 파일 블롭 = 작업본(`git hash-object --no-filters`), 기존 블롭 줄끝 유지(LPR·LOR·SCC·UFA LF, RS 혼합 CRLF).
- K9-1-1 G4의 A1 장기(L2 s47 4800 H27) 기준: 탐침 계획(§3.3)이 A1 장기를 돌리지 않아, 같은 동결 탐침 트리와 같은 A1 팔(`2a0a37d0…`)로 새 폴더 `D:/VISSIM-merge/k8b_commit_gates/k91_g4ref/out`에 한 번 계산했습니다(objective 787.2800511472263; §4.2 G4 Z0 경우의 A1′ 선례 꼴, 값·식 변경 없음). A2·A3 L2는 탐침 자체 잡이 기준입니다.
- Z1: K9-1-0b 관문이 모두 통과해 **Z1-a**(키 없음, 모든 팔·BASE에서 켜짐)를 채택했습니다. Z1-b 키는 없습니다(`make_config_n31.K91_Z1B = False`). SAF-K91 값 = 탐침 A3 튜닝(`3a976943…`)에서 탐침 Z1 키 하나를 뺀 것(나머지 잎 같음).
- 수동 기록기 배치(D1, K9-1-0): `/k91` 기록은 K9 키 런에서만 summary.json에 넣고 모든 런은 `k91_record.json`에 씁니다. 키 없는 런(G1·G2·G5, 판정의 BASE)의 summary 잎 집합은 K8b-5와 같아 비교기에서 빼는 잎이 없습니다. Z1 on/off의 차이인 `z1_touch_events`는 이 때문에 G1·G5 비교 잎에 나타나지 않고 `k91_record.json`·G5 보고 행에만 있습니다.
- 알려진 하네스 시험 실패 1개(`test_sa_harness.py::test_hook_site_chain_fold_and_capacity_counts`, `fold site missing _skip_tiny_city_moving_share`)는 7e079efb 트리에서도 같으며 선언 U 밖입니다(보고만).

## 판정 단계로 넘길 것

- 판정 팔: BASE = `config_n31_v2.json`(319d07aa), SAF-K91 / SAG-K91 = 위 팔 파일(K8b 세 키 + K9 세 키). 머리 트리 `k91t` = `git archive <K9-1-4>`, 출력 루트 `D:/VISSIM-merge/k8_gates_out_v4`(새 폴더). 판정 상태에서 키를 켠 계산은 `--gates-stage k91t --declaration-sha 4ccfd8fd1efb6f79c59161ab40d4aa9234fa729bc980c89c1c9ad3059cd420d8`로만 열립니다(K9-1-0 가드; `k8bt`는 거부).
- F17b는 판정 리플레이에서 같은 시드 R-obs의 `obs150/derived_<T′>.json`(끝 ≤ T)을 결정 묶음에 복사해 읽습니다(`sa_common.k91_history_copy`, 복사 목록 `<out>/sa/k91_history_copies.json`).
- 순서·문턱·표본은 보충 19 r2 §5·§6(퇴행 막기 §6.2)·§7 그대로입니다.

## J1 단서 '알려진 결함'에 더할 것 (D-K9-6, 보충 20 §2.4 — 결정 문구의 '§1 L1 과소 차단 기구')

- **M1 W 접근 대기 수준**: 장기 L1(s43 2400 H42)에서 VISSIM 127 차로 1+2는 6150 s까지 107–140대로 유지되는데 모형 SA는 3750 s 뒤 줄어 6150 s에 46.4대. 방류는 같고(블록당 약 57대) 3600 s 이후 모형 SA 유입이 적음(W 접근 합 6150 s 81.9 대 177, 차이는 주로 도시 W 쪽 링크 32). 그래서 모형 10491 포트는 L1 기간 1–2에서 한 번도 막히지 않음(VISSIM 역류 창 비율 0.200 / 0.172) — 모든 팔 공통, F17b와 무관.
- **M2 10491 → 129 합류 간격**: VISSIM 10491 대기(느린 차 27–35대)는 127 차로 1이 관측 만차 아래일 때도 생김(10491이 129 차로 1 @239.38 m에 합류할 때의 간격 부족으로 보임). 모형 SA 포트 수용은 차로 여유 > 0이면 받음.
- F14(커넥터 + 링크 26 차로 1 저장)는 이 과소 차단을 움직일 수 없어(커넥터 재고 최대 3.72대) K9-2로 철회(D-K9-6).
