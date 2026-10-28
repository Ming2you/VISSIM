# RB_RULE — 미터 readback 실행 대조 규칙 (데이터 뒤 선언, 2026-10-27 05:20 KST)

- 근거 결정: D-K9-93 ③ "signal_readback.csv 로 미터 신호 대조를 새 선언(데이터 뒤임을 밝힘)으로 실행" (`SP/K9_1_J1_NOTES_20261013.md:310`).
- **데이터 뒤 선언**: B 결과(B_RESULTS r2 152a2f6f…, VERIFY_B f2851f8b…)를 본 뒤 정한 규칙입니다. VERIFY_B D5 가 선언 밖으로 "810/810 주기 일치" 를 이미 냈고, 이 규칙을 쓴 작업자도 B v3c3-s31 readback 머리(900–931 s 의 SC 9101 행 등)와 SC 별 행 수를 형식 확인으로 봤습니다. 그래서 이 규칙의 결과는 "미리 정한 검정" 이 아니라 "정의를 고정한 다시 세기" 입니다. COMPARE_RULE_B·PINS_B 는 바꾸지 않습니다.
- 줄임: SP = `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8`, RB = `SP/c_port/readback`, FRZ_B1 = `D:/VISSIM-merge/k8_gate_trees/codexhandoff/b1/frozen/sdmpc31_a49981ff_202610261410`, FRZ_VA = `D:/VISSIM-merge/frozen/sdmpc31_c20aff1d_202610230833`.
- 줄임말: SG = 신호 그룹, SC = 신호 제어기(미터 SC 9101–9108, SG 1 하나씩), g = 10 s 주기 중 녹색 초, FZP = VISSIM 차량 궤적 파일(5 s 프레임).

## 1. 대상과 입력 (모두 읽기만)

| 런 | 폴더 | 비고 |
|---|---|---|
| B v3c3-s31·s41·s43 | `D:/VISSIM_runs/20261026_codex_b_v3c3/s<s>/sdmpc` | codex 제어기, FRZ_B1 |
| V-A v3c3-s31·s41·s43 (대조) | `D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s<s>` | 우리 묶음 B1, FRZ_VA |

- readback: `decisions_*/signal_readback.csv` (`sim_sec,sc_no,sg_no,requested_state,readback_state,ok,stage`), SC 9101–9108 행만.
- 명령: 런의 `action_*.csv` 에서 `kind=ramp_meter` 행(`sim_sec, id, sc_no, rate_vph, green_sec`, metadata 의 `group_rate_vph`). 교차 확인: `decisions_*/action_<T>.csv`.
- 런 로그 `runlog_*.txt` 의 `RAMP_AMBER_SEC=`, `RAMP_METER_SCS=`.
- 망: 런의 `network/*.inpx` 신호 헤드(sg `910x 1`)·커넥터 기하. FZP: 런의 `vissim_eval/*_001.fzp`.
- 모형 표: FRZ_B1 `diagnostics/b0_v3c3/config_b0_v3c3.json` `/actuation/real_world_ramp_metering/per_lane_veh_per_cycle` (B 가 읽은 설정; 값은 우리 c20aff1d CFG:7524-7534 와 같음 [읽음]).
- NC3 는 미터 명령이 없어 쓰지 않습니다.

## 2. 러너 의미 [읽음]

- `RampStateAt(g, t)` (FRZ_B1 vbs:1026-1038, FRZ_VA vbs:1006-1018): pos = t mod 10; g ≤ 0 → RED; pos < g → GREEN; pos < g + amber → AMBER; 그 밖 RED. amber 는 런 로그 `RAMP_AMBER_SEC`.
- 주 루프 (FRZ_B1 vbs:895-949, FRZ_VA :900-926): 정지 시각 t 마다 먼저 `ValidateRuntimeSignalPersistence(t)` 가 post_step 행을 씀(지난 정지에서 쓴 SG + 제어 경계·끝에서는 모든 SG, vbs:4139-4179), 그다음 결정·`ApplyRuntimeRampMeters(t)` 가 상태가 바뀐 SG 만 쓰고 immediate 행을 씀. 정지 시각에는 미터 전이 시각이 들어감(vbs:995-1011). 정지 사이는 `RunContinuous`.
- 그래서 post_step 행(t) 은 [이전 정지, t) 동안 유지된 상태, immediate 행(t) 은 t 부터의 상태입니다.

## 3. 정의

- 명령 g(t) = 그 SC 의 명령 행 중 sim_sec ≤ t 인 마지막 행의 green_sec. 기대 상태 E(t) = RampStateAt(g(t), t).
- 관측 상태 S(t) (정수 t, [t, t+1) 동안) = sim_sec ≤ t 인 마지막 readback 행(시각, 파일 순서)의 readback_state. 정지 사이 상태는 마지막 쓰기가 유지된다고 봅니다(한계 §6).
- 행의 관측 초: immediate t → t, post_step t → t − 1.
- 제어 창: 900 ≤ 초 < 9,000, 주기 c = 900, 910, …, 8,990 (미터당 810 주기). 워밍업(관측 초 < 900)은 따로 적습니다.

## 4. 지표 (런 × 미터마다; 시드 평균 안 냄)

- **K0 명령 출처**: 런 action CSV 미터 행 = `decisions/action_<T>.csv` 미터 행(green_sec·rate_vph·id) 일치 수 / 전체; rate_vph = 90 × green_sec 인 행 수; green 이 정수가 아닌 행 수.
- **K1 행 일치**: requested = readback ∧ ok = 1 인 행 수 / 전체 (창·단계별).
- **K2 행-기대 일치**: immediate 행(t) readback = E(t), post_step 행(t) readback = E(t − 1). 일치 수 / 전체 (창·단계별). 행이 없는 쓰기 누락은 K2 가 못 봄 → K3·K4.
- **K3 주기 녹색 초 (주 지표)**: G_obs(c) = #{t ∈ [c, c+10): S(t) = GREEN}, G_cmd(c) = #{pos ∈ 0..9: RampStateAt(g(c), c+pos) = GREEN}. 일치 주기 수 / 810. 어긋난 주기는 모두 세고 50개까지 적음.
- **K4 초 단위 일치**: #{t ∈ [900, 9000): S(t) = E(t)} / 8,100.
- **K5 쓰기 확인 쌍**: 제어 창 immediate 쓰기마다 (i) 그 행 requested = readback ∧ ok = 1, (ii) 같은 SG 의 다음 쓰기 시각까지(포함) post_step 행이 1개 이상이고 모두 같은 상태. (i)∧(ii) 수 / 쓰기 수. 제어 경계(150 s 배수) post_step 행 수도 적음.
- **K6 직접 확인 범위 (참고)**: 관측 초를 시간순으로 놓고 이웃한 두 관측이 같은 상태면 그 사이 초를 "양끝 확인" 으로 셈. 제어 창 8,100 초 중 양끝 확인 초 수와 관측 초 수.

FZP 방류 (N34 §3.1 정의를 바꾸지 않고 B 에 적용; `rmcause/r2c_n/N34_FLOWS.md:191-196`):

- **K7 녹색별 차로 통과율**: 블록 = [T, T+150], T = 900, 1,050, …, 8,850 (54 블록), 녹색 = T 의 명령 green_sec, 프레임 (T+0.1, T+150.1] 30개. 통과 = 헤드를 넘은 차 × 24 = veh/h/차로 (헤드 = 런 inpx 의 SG 910x 헤드, 차로별). Q = 30 프레임 모두 그 차로 헤드 앞 50 m 안에 15 km/h 미만 차 ≥ 1. B(뒤 안 막힘) = 헤드 뒤 그 차로 저속 차의 블록 평균 < 헤드 뒤 저장의 50 % (헤드 뒤 길이 ÷ 6.0 m, 길이 = inpx 커넥터 폴리라인). 1차 = Q ∧ B, 2차 = (Q 프레임 ≥ 24) ∧ B. 미터·차로·g 마다 블록 수(시드별), 1차 수(시드별), 1차 중앙 [최소–최대], 주기당 대(= 중앙/360), 모형 표 360 × per_lane_veh_per_cycle[g] 와의 비, 명령 90g/차로 와의 비, 2차 중앙(n). 참고 열: N34 규칙 RM 1차 중앙(다른 제어기, 같은 v3c3 망; N34_FLOWS.md:203-216). 1차 블록 0 이면 "알 수 없음(사유)".
- **K8 명령 rate 대 실현 방류 (모든 블록, 참고)**: 미터·g 마다 블록별 미터 방류(헤드 통과 + 헤드 뒤 첫 기록, 차로 합) × 24 의 중앙·범위, 명령 rate_vph(90g)·모형 group_rate_vph 와의 비 중앙, 명령·모형을 넘은 블록 수. 수요에 묶인 블록이 섞이므로 "미터 용량" 이 아님.
- **K9 검산**: 제어 창 프레임에서 미터별 헤드 통과 + 헤드 뒤 첫 기록 − 커넥터 이탈. 그리고 metadata `group_rate_vph` = 360 × 표[g] × 차로 수 인 행 수(K0b). inpx 헤드 위치를 N34 표와 대조.

V-A 는 같은 도구로 K0–K9 (늘 g10 이라 K7 은 g10 칸만).

## 5. 도구 (RB/tools; sha 는 실행 전 `SP/c_port/LOG.md` 에 고정)

| 도구 | 하는 일 | 무게 |
|---|---|---|
| `rb_inpx.py` | inpx → 미터 헤드·커넥터 길이·저장 | 가벼움(앞에서) |
| `rb_readback.py` | K0–K6, `out/readback.json`, `out/cycles_<run>.csv` | 가벼움(앞에서) |
| `rb_fzp_scan.py` + `rb_scan_chain.py` | FZP 6개 차례로 → `out/scan_<run>.json` | 무거움: `rb_launch.ps1` 로 WMI 분리, BELOW_NORMAL, `python -B`, PYTHONHASHSEED=0, env_hsw, 스레드 1, 한 번에 하나 |
| `rb_discharge.py` | K7–K9, `out/discharge.json` | 가벼움(앞에서) |
| `rb_selftest.py` | 합성 자료로 도구 자체 시험(런 자료 안 씀) | 가벼움 |

## 6. 한계와 쓰는 말

- readback 은 **SG 상태 수준**입니다. 차가 실제로 섰는지·지났는지는 K7–K8 의 FZP 셈으로 따로 봅니다.
- 해상도는 러너 정지 시각(정수 초)입니다. 정지 사이 상태 변화(COM 소유 상실 등)는 행이 없으면 못 봅니다. K6 이 직접 확인 범위를 적습니다.
- 판정 낱말(좋다·나쁘다·통과·실패)을 쓰지 않습니다. 시드는 망 접두(v3c3-s31 등)로 적고 평균 내지 않습니다. Ω 숫자는 이 작업에서 다루지 않습니다.
- 이 규칙을 고칠 일이 생기면 고친 판을 따로 두고 LOG 에 까닭과 sha 를 적은 뒤 다시 돌립니다.
