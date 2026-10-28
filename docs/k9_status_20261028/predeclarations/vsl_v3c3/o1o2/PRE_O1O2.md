# PRE_O1O2 — 오프라인 O1·O2 규칙 (실행 전 고정, 2026-10-27 KST)

- 근거 결정: D-K9-95 (`SP/K9_1_J1_NOTES_20261013.md:318`, sha256 bbfe77b0…). 앞선 탐침: `SP/c_port/VSL_OFFLINE.md` r2 (a8ff255e…) §3·§4.2.
- 이 문서는 O1·O2 를 **돌리기 전에** 고정합니다. 고정 sha 는 `VS/LOG.md` 에 적습니다(VS = `SP/vsl_v3c3`). 고정 뒤 이 문서는 고치지 않습니다. 도구 sha 는 시험(분석 밖 상태) 뒤, 분석 실행 전에 LOG 에 따로 적습니다.
- VISSIM·COM·폐루프 러너 0. 런 폴더·인계 사본·동결 트리(FRZ_B1 포함)·GWT8·sim3·Y: 는 읽기만. 코드·입력 사본과 작업 폴더는 `D:/VISSIM-merge/k8_gate_trees/vsl_v3c3/o1o2/`(GT2) 에만 씁니다. 무거운 python 은 공유 잠금 `D:/VISSIM-merge/k8_gate_trees/heavy.lock` 을 **일 하나마다** 잡고 풉니다. WMI 분리, BELOW_NORMAL, PYTHONHASHSEED=0, python -B, 스레드 1, env_hsw.
- 판정 낱말은 쓰지 않습니다. 숫자와 부호만 적습니다. 시드는 망 이름을 붙여 적습니다(64cf-s29, v3c3-s31 등). 봉인 시드·sealed/ 0.

## 줄임말

- VSL = 가변 제한속도. plant = SDMPC(순차 분해 모형예측제어기)의 예측 모형. φ = 용량 감소(capacity drop) 방류 계수 `capacity_drop_discharge_phi`. ρ_crit = 임계 밀도(veh/km/차로). J = plant 의 모형 Ω 목적값(veh·h, 450 s 예측 = 150 s 블록 3개). seg13 = FW_E VSL 구역 머리 13(표지 DSD 63–66). B 상태 = codex 제어기를 v3c3 로 옮긴 폐루프 런 B(`D:/VISSIM_runs/20261026_codex_b_v3c3`, VSL 110 고정)의 결정 상태. FZP = VISSIM 차량 궤적 기록(5 s).
- 구역(셀 번호, 31셀; 체인 m 는 `vsl_v3c3/tools/vsl_cell_scan.py` CELL_B): U 0–7 · B1 8–13 · M1 14–15 · VSa 16–18 · VSb 19–25 · D 26–30.

## 1. O1 — φ·ρ_crit 민감도 탐침

### 1.1 상태 (시드·망 명시)

- 64cf-s29 (VSL_OFFLINE 의 넷, 같은 입력 규칙으로 GT2 에 다시 만듦): A1 T=1,800 · A1 T=3,600 · codex joint T=1,800 · codex joint T=4,500. 코드 = VSL_OFFLINE 이 쓴 a0 코드 사본(`codexhandoff/vsl_off/code`)의 GT2 사본 `code64`.
- v3c3 (B 상태, 코드 = FRZ_B1 의 GT2 사본 `codeB1`, 튜닝 `diagnostics/b0_v3c3/config_b0_v3c3.json`):
  - 1차 3개: v3c3-s31·s41·s43 의 T=1,800.
  - 2차 2개(시간이 되면, 이 순서로): v3c3-s41 T=3,600, v3c3-s43 T=3,600.
  - 고른 까닭: 데이터를 보지 않고 정한 고정 시각입니다(64cf 상태와 같은 T=1,800, 그리고 3,600). FW_E 상태를 보고 고르지 않았습니다.

### 1.2 변형 (상태마다 같은 순서)

- plant 설정 13개: base(φ 1.0·ρ×1.0) → φ 0.95·0.90·0.85(ρ×1.0) → ρ×0.9·×1.1(φ 1.0) → φ{0.95, 0.90, 0.85} × ρ{×0.9} → φ{0.95, 0.90, 0.85} × ρ{×1.1} → base_repeat(결정성 점검).
- 설정마다 VSL 3개: seg13 을 세 블록 모두 110·100·90 으로(그 구역 머리에 딸린 `FW_E__seg<k>` 키 전부, 소유자 최솟값 다시 셈). 다른 구역·다른 레버는 운영 seed(held 를 저장 보호로 투영한 점) 그대로.
- 바꾸는 키(FW_E 만, 설정마다 저장한 원래 값에서 절대값으로 씀):
  - φ: `state.lane_freeway_runtime.configs['FW_E'].network.capacity_drop_discharge_phi`. 집계 경로(`area_freeway_accounting.py:133,228-231`)에서만 쓰입니다. 셀 밀도가 링크 ρ_crit 를 넘으면 송출을 φ·용량으로 자릅니다. 차로군 경로(`physical_lane_groups.py:253-254`)는 φ ≠ 1 을 생성 때 거부하고 걸음에서 φ 를 읽지 않습니다. 그래서 FW_E 가 차로군 경로인 상태는 "φ 받지 않음" 으로 적고 φ 칸은 비교하지 않습니다.
  - ρ_crit: (a) 같은 구성의 `network.rho_crit`(링크 스칼라; φ 문턱·끝 경계), (b) 같은 구성의 `network.freeway_segment_params['FW_E'][i]['rho_crit']` 31셀 전부(셀 FD, Carlson ρ_c(VSL), 예측 계수 전환), (c) 주 설정 `cfg.network.freeway_segment_params['FW_E'][i]['rho_crit']`(목적·자원 쪽 사본, `lane_plant_runtime.py:568`). 주 설정 링크 스칼라 `rho_crit`(27.0)와 FW_W 는 바꾸지 않습니다. 초기 상태(관측에서 만든 밀도·속도)는 바꾸지 않습니다.
  - 설정마다 새 공유 질의(작업자 0, 캐시 끔)를 만듭니다. 질의는 만들 때 (follower, state, reference, forecast)를 복사하므로 바꾼 값이 그 질의의 모든 굴림에 들어갑니다.
- 차로군 경로에서 ρ 변형이 결과를 바꾸지 않으면(세 VSL 의 J 가 base 와 비트까지 같으면) "ρ 변형이 이 경로에 닿지 않음" 으로 적습니다.

### 1.3 읽는 법 (실행 전 고정)

- ΔJ_v(c) = J_v(c) − J_110(c), v ∈ {100, 90}. 음수 = plant 가 VSL v 에서 비용이 준다고 봄.
- 부호: |ΔJ| < 0.01 veh·h 이면 0, 아니면 + 또는 −.
- **부호 바뀜**: 같은 상태·같은 v 에서 설정 c 의 부호가 base 의 부호와 다름. "엄격 바뀜" = + ↔ −. "느슨한 바뀜" = 0 을 낀 바뀜. 둘 다 셉니다.
- 함께 적는 것: FW_E 자기 비용 Δ, 구역별 시간평균 속도 Δ(v − 110)·흐름 Δ, 셀 16–25 와 8–15 에서 셀 밀도가 링크 ρ_crit 를 넘은 시간(초, φ 가 걸릴 수 있는 노출), plant 가 VSL 을 낮춘 셀 번호.
- 점검: base 와 base_repeat 의 J 차(같은 경로, 0 이어야 함). 64cf 넷은 base 의 J_110·J_100·J_90 을 VSL_OFFLINE V3 출력(`c_port/vsl/out/v3_*.json` 의 v110_all·v100_all·v90_all)과 대조합니다(같은 코드·같은 입력 규칙이면 같아야 함; 다르면 차이를 적고 Δ 만 씁니다).
- 경고: VSL_OFFLINE §3.1 처럼 작업자 경로(기록) 대 프로세스 안 경로(탐침)는 같은 seed 에서도 최대 0.294 veh·h 다릅니다. 이 탐침의 Δ 는 모두 같은 프로세스 안 경로의 차입니다.

## 2. O2 — VSL 켠 상태 plant 충실도 (열린 고리)

### 2.1 64cf-s29 (한 시드, 팔마다 한 런)

- 상태: window 팔(1,800–5,700 s 에 seg13 = 90 고정; VSL 켬)과 off 팔(110 고정; VSL 끔)의 T = 1,800·1,950·2,100·2,250·2,400·2,550 (팔마다 6, 합 12).
- VSL 단독 팔(`D:/VISSIM_runs/vsl_repro_s29/vsl`)은 native 고정 일정 런이라 결정 상태(state·lane_observations·obs150)가 없습니다 [읽음 폴더 목록]. 그래서 plant 재생은 못 합니다("못 냄"). 이 팔의 VISSIM 반응은 VSL_OFFLINE §2.1 에 있습니다.
- plant 계획: 운영 seed 그대로(그 팔의 고정 VSL 일정이 이미 들어 있음: window 는 seg13 = 90, off 는 110). 다른 레버(미터·신호)는 held 근사입니다. 실제로는 T, T+150, T+300 결정의 블록 0 이 실행되었으므로, 그 세 결정과 held(T−150)의 FW_E 미터 명령(rate·green)을 함께 적어 근사의 크기를 보입니다.
- 반사실(plant 만): window 상태에 seg13 = 110, off 상태에 seg13 = 90 을 하나 더 굴려 plant 의 VSL 반응(90 − 110)을 같은 상태에서 봅니다.
- VISSIM 쪽: 그 팔 FZP(`D:/VISSIM_handoff/20261024/raw/<팔>/sdmpc/vissim_eval/sdmpc31_sdmpc8100_s29_001.fzp`)를 5 s 프레임·31셀로 셈(`o2_fzp_cells.py`). 블록 b = [T+150b, T+150(b+1)) 프레임(보통 30개). 25개 미만이면 못 냄.
- 지표(블록 0·1·2, 구역별): 속도 = Σ(차량·속도)/Σ차량(Edie 공간평균, plant 는 셀 재고 가중 시간평균), 재고 = 셀 차량 수 합(veh, 시간평균), 흐름 = 구역 길이 가중 평균 k·v·차로(veh/h; VISSIM 은 Edie ΣSV/(프레임 수·L)). 오차 e = plant − VISSIM. 셀 14–25 는 셀별 속도 오차도 적습니다.
- 요약: 팔별(window = VSL 켬, off = VSL 끔)·블록별·구역별로 6상태의 평균 e(편향)와 평균 |e|. "켬 대 끔" = 평균 e(window) − 평균 e(off). 한 시드·팔마다 한 런·상태 6개라 흔들림은 모릅니다. 검정·판정 없음.
- 함께 적는 것: VISSIM window − off(같은 T·블록). 이 차는 미터·신호·궤적이 함께 다른 짝이라 VSL 몫으로 읽지 않습니다(VSL_OFFLINE §2.3: joint − off 도 VSa −35 km/h).

### 2.2 v3c3

- (가) VSL 끔 충실도: O1 의 B 상태(1차 3개, 2차를 돌렸으면 그것도)에서 base 설정 v110(= seed, B 는 110 고정) 예측을 그 B 런 FZP 의 같은 블록과 대조. 지표는 2.1 과 같음. B 런은 미터·신호가 움직인 런이므로 held 근사도 같습니다.
- (나) VSL 켬 충실도: v3c3 VSL 단독 런 3개(s31·s41·s43, DSD 63–66 → 분포 91, 900–9,000 s)는 native 런이라 결정 상태가 없습니다. 그래서 plant 열린 고리 재생은 런이 끝나도 못 합니다. 대신 **부호 대조**만 합니다: B 상태 base 설정의 plant Δ(90 − 110) 대 VISSIM Δ(VSL 단독 − NC3, 같은 시드, 같은 [T, T+450) 블록, 5 s 프레임 스캔), 구역별 속도·흐름. 속도 |Δ| < 0.5 km/h 는 ~0. plant 명령 90 ↔ VISSIM 분포 91(90–92 km/h). 상태가 다르므로(B 는 미터·신호 제어, VISSIM 짝은 무제어+VSL) 부호만 봅니다. VSL 런 FZP 가 이 보고를 쓸 때까지 없거나 끝나지 않았으면 "pending" 으로 적습니다.
- NC3 FZP: `D:/VISSIM_runs/20261001_v3c3/s<S>_v3c3nc/run/vissim_eval/baseline_s<S>_v3c3nc_001.fzp`. VSL 런 FZP: `D:/VISSIM_runs/20261027_vsl_v3c3/s<S>/` 아래(런이 끝난 뒤 위치 확인).

## 3. 실행 순서와 시간이 모자랄 때

- 순서: (1) 입력 만들기 → (2) FZP 프레임 스캔 window·off·B s31·s41·s43 → (3) O1 64cf 넷 → (4) O1 v3c3 1차 셋 → (5) O2 64cf 12 → (6) O1 v3c3 2차 둘 → (7) VSL 런이 끝났으면 VSL·NC3 프레임 스캔 여섯.
- 모자라면 위 순서에서 끝나지 않은 칸을 "못 냄(시간)" 으로 적습니다. 순서를 바꾸지 않습니다.

## 4. 도구 (sha 는 LOG 에, 분석 실행 전)

- `o1o2/tools/o_build_inputs.py` 입력 만들기(VSL_OFFLINE `v3_build_inputs.py`·관문 1 `g1_build_inputs.py` 규칙: 바이트 복사, 경로만 옮김).
- `o1o2/tools/o_probe.py` plant 탐침(VSL_OFFLINE `v3_plant_probe.py` 에서 나옴: sdmpc.solve 대신, 같은 결정 문맥, 최적화 없음, 행동 파일 안 씀).
- `o1o2/tools/o_run_probe.ps1` 상태 하나 돌리기(환경 = 그 런 provenance 의 RW_*, 튜닝 sha 대조).
- `o1o2/tools/o_heavy.ps1` 일 줄(일마다 공유 잠금).
- `o1o2/tools/o2_fzp_cells.py` FZP 5 s 프레임·셀 셈.
- `o1o2/tools/o_analyze.py` 표 만들기(§1.3·§2 규칙 그대로).
- 시험: 분석 밖 상태(64cf A1 T=1,650, v3c3-s31 B T=1,650, window T=1,650)로 배관만 봅니다. 그 출력은 결과로 쓰지 않습니다.
