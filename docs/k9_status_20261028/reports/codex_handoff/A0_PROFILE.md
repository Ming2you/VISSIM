# A0_PROFILE — codex joint 결정 오프라인 재생: 기록 재현 정도, 시간 분해, 속도 후보 (2026-10-25 KST)

- 무엇: D-K9-83 의 A0 단계. codex 64cf-s29 joint 런의 기록 결정 셋(T = 900, 2700, 4950 s)을 이 PC 에서 VISSIM 없이 다시 계산했습니다. 그 결과를 codex 기록과 대조하고, 결정 한 번의 시간이 어디에 쓰이는지 나누고, 뜻을 바꾸지 않는 속도 후보를 시험했습니다.
- 입력 sha256 [실행]: NOTES `cb71c563…`(D-K9-82·83·84), HANDOFF `e2cef38c…`, TAKEOVER_PLAN r2 `b75ad041…`, 대조 규칙 A0-CMP-1 `a05f2071…`(첫 재생 전 고정), RAW_CHECK `c8411d78…`, OMEGA701_V3C3 `5c02894a…`.
- 범위: VISSIM·COM·폐루프 러너 0, 커밋·푸시 0. 재생은 scratch 트리 `D:/VISSIM-merge/k8_gate_trees/codexhandoff/a0/` 에서만, 한 번에 하나, WMI 분리 발사, BELOW_NORMAL, PYTHONHASHSEED=0, `python -B`. 공유 드라이브 쓰기 0, `sealed/` 0, 봉인 시드 0. GWT8·동결 트리·codex worktree 는 읽기만.
- 짝 개수: codex 증거는 64cf-s29 한 런(한 시드)입니다. 이 문서의 재생은 그 한 런의 결정 3개입니다.
- 함께 읽을 것: `codex_handoff/a0/PRE_A1.md`(A1 계획과 사용자 결정), `codex_handoff/LOG.md`(시각별 기록).

## 줄임말 (처음 한 번)

- A0 / A1: A 재현의 준비 단계(VISSIM 없음) / 64cf-s29 joint 8100 s 재현 런(VISSIM).
- 기록: codex PC 에서 돈 joint 런의 결정 파일(`D:/VISSIM_handoff/20261024/raw/joint/sdmpc/decisions_sdmpc31_sdmpc8100_s29/`).
- R1–R4: 대조 규칙 A0-CMP-1 의 네 단(R1 명령 CSV 바이트, R2 일곱 필드 해시 다섯 칸, R3 채점 토큰, R4 모든 JSON 잎). 시계 잎만 뺍니다.
- 시계 잎: 걸린 시간·시각을 담은 잎. 규칙 정규식에 걸리는 것과, 정규식 밖이지만 이름이 `_sec` 로 끝나는 소요시간 잎(`reverse_sec`, `tangent_sec`, `compile_or_load_sec` 등)을 따로 셉니다.
- env 이름
  - base: codex 러너 환경(run_closedloop3000.ps1:109-117, OMP·OPENBLAS·MKL 스레드 1)과 기록 RW_* 그대로, Python 3.12.2.
  - env_hsw: base + `OPENBLAS_CORETYPE=Haswell`, `NPY_DISABLE_CPU_FEATURES=AVX512F AVX512CD AVX512_SKX AVX512_CLX`, `NUMBA_CPU_NAME=haswell`(AVX-512 를 끄고 AVX2 경로로 계산).
  - S1: 속도 후보. `PYTHONPYCACHEPREFIX`(코드 트리 밖 바이트코드 캐시, compileall 로 미리 채움) + `NUMBA_NUM_THREADS=2`.
  - py31214: 인터프리터만 codex 런타임 Python 3.12.14 로 바꾼 재생.
- PFO: SDMPC 의 따뜻한 시작 단계(예측 6–7개). cap: 리더 자원 상한 후보(결정마다 3개). secant: VSL 기울기를 실제 롤아웃 차분으로 구하는 평가(cap 마다 24개). tangent: 역방향 AD 로 구하는 기울기. QP: 작은 볼록 2차 계획(scipy). 이웃 검사: 미터 이웃 후보 평가(`sdmpc_meter_neighbor_audit`).
- NC / LNC: 무제어 / 이 PC 에서 돈 64cf-s29 NC(`D:/VISSIM_runs/vsl_repro_s29/none/run`).

---

## 0. 쉬운 답

1. [실행] 재생은 됩니다. 인계 `code/` 바이트(SOURCE_FILES 3,638개 일치) 위에 빠진 데이터 파일 3,544개를 원래 동결 목록 sha 가 같을 때만 넣었고, 이 PC 어디에도 없는 설정 3개만 대역 파일로 두었습니다(§1).
2. [실행] 이 PC 안에서는 결정이 결정적입니다. 같은 입력·같은 수치 env 면 명령·토큰·모든 잎이 같고, 시계 잎만 다릅니다(재생 7쌍; 부하·캐시 상태·S1 유무가 서로 다른 쌍 포함, §3). 인터프리터만 바꾼 2쌍도 같았습니다(§8).
3. [실행] 그러나 **어떤 설정도 세 결정 모두에서 codex 기록을 비트 단위로 다시 내지 못했습니다.** env_hsw 는 T=900 에서 명령 CSV·일곱 필드가 기록과 같았지만(R1·R2), T=2700 은 40행·T=4950 은 17행이 녹색 최대 0.001 s, offset 최대 0.003 s 다릅니다. base 는 세 결정 모두 다르고, T=2700 에서는 미터 RM_C10480 녹색이 1 s(180 → 270 veh/h) 달라집니다(§4).
4. [실행] 차이는 첫 예측 묶음 직후 PFO 첫 걸음의 목적값에서 이미 보입니다(상대차 1e-10–1e-7). [추론] 코드·입력이 아니라 부동소수 계산 경로(CPU 명령 집합·BLAS 커널·numpy SIMD)의 차이로 봅니다. [실행] 인터프리터를 codex 판(3.12.14)으로 바꿔도 결과는 3.12.2 와 비트 동일했습니다(T=4950, 두 env, §8).
5. [실행] 결정 한 번은 이 PC 에서 codex PC 보다 2.30–2.63배 깁니다(이 PC 525.6–1,112.7 s, codex PC 228.8–425.0 s). 늦어지는 몫이 한 단계에 몰려 있지 않고 모든 단계가 1.9–3.6배로 고르게 늦습니다. 가장 큰 덩어리는 VSL secant 묶음, cap 2 의 QP 구간(주 프로세스 한 코어), 이웃 검사, PFO 입니다(§5).
6. [실행] 우리 줄기(GWT8, 886a014a 이후 65커밋)에는 속도·캐시·병렬·numba·tangent 동시성 커밋이 없습니다. 설정에서 다른 속도 키는 D-K9-83 이 금한 지름길(cap 1, 이웃 검사 없음)뿐입니다(§6.1–6.2).
7. [실행] 시험할 수 있는 뜻 없는 설정 후보는 S1 하나였습니다. S1 은 5개 재생(env_hsw 3결정, base T=900, 빈 PC 반복 T=900)에서 같은 env 기준과 R1·R2·R3 가 같고 설명 안 된 잎 차이가 0 입니다. 부하가 다른 때 잰 시간차(0.88–0.94배)는 대부분 부하 흔들림이었고, 빈 PC 에서 나란히 잰 몫은 결정당 −4.5 s(−0.85 %)입니다(§6.3).
7-1. [실행] 빈 PC(다른 세션 0)에서 T=900 은 codex PC 대비 2.31–2.33배였습니다. 그래서 배수의 대부분은 부하가 아니라 이 PC 의 한 코어 속도입니다(§5.3).
8. 그래서 D-K9-83 의 "기록 결정을 비트 단위로 다시 내는 것만" 이라는 기준은 이 PC 에서 수정 없는 codex 코드로도 채워지지 않습니다. 이 문서는 그 기준을 조용히 바꾸지 않습니다. env 선택과 재현 기준은 `PRE_A1.md` §2 의 사용자 결정으로 올렸습니다.

---

## 1. 재생 설정 [실행]

### 1.1 코드 트리

- `a0/code` = 인계 사본 `D:/VISSIM_handoff/20261024/code/` 를 robocopy(.git 제외). SOURCE_FILES.csv 3,638행이 사본·CX worktree·a0/code 모두에서 일치합니다. provenance `controller_sources` 116개도 sha 가 같습니다.
- 빠진 데이터 파일: 인계 부분집합에 없어 어댑터가 조용히 기능을 끄거나 실패했습니다(예: `outputs/movement_merge_plan_20260824.json` 이 없으면 병합이 꺼져 "Native choice must partition exactly one complete approach").
  - 규칙: 원래 동결 목록(`evidence/original_FREEZE.json`, 74,076 파일 sha)과 바이트가 같을 때만 넣음. 원천은 GWT8 작업 트리와 `D:/VISSIM-merge/repo` git blob(ca181e84·886a014a), 읽기만.
  - 결과: 3,544개(GWT8 3,543, git 1). `.py` 0개. 기록 `a0/RESTORED_FILES.json` sha256 `184a2604…`.
- 대역 3개(`a0/STANDIN_FILES.json`, sha256 `c80839a9…`): 이 PC 어디에도 원래 sha 의 바이트가 없는 설정입니다. 런타임이 읽는 키만 담았습니다.
  - `aggregate270/flow279/config_10686_free.json`(원래 `a26ab121…`): 런타임 독자는 `sc109_routes321/candidate.py:13` 의 membership_path 하나. 결과는 링크 1220012103·1210012600 의 안/밖에만 쓰이고(calibrated_urban_runtime.py:143,157), 이 PC 의 membership 4벌 모두에서 둘 다 "안" 입니다.
  - `aggregate270/sc107_shared316/config.json`(원래 `d884ea00…`): 독자 `sc107_shared316/candidate.py:13-17` 이 키 둘만 확인.
  - `aggregate270/sc109_transport317/config.json`(원래 `b2e83f62…`): 독자 `sc109_transport317/candidate.py:60-62` 가 키 둘만 확인.
  - [추론] 대역이 결정을 바꾸는지는 기록과의 대조로만 볼 수 있습니다. env_hsw T=900 이 기록과 명령 바이트까지 같으므로, 적어도 그 결정에서는 대역이 명령을 바꾸지 않았습니다.

### 1.2 입력 트리

- `a0/pristine/T000900·T002700·T004950`: 원자료 바이트 그대로. 바꾼 곳은 셋뿐입니다.
  1. 상태 JSON 과 run_provenance JSON 의 경로 접두 둘(E: 런 폴더 → `a0/runs/T<T>/sdmpc`, 동결 트리 → `a0/code`).
  2. 직전 명령 적용 영수증(`action_<T−150>.json.applied`, UTF-16) 의 CSV 경로 줄(같은 런 접두로). 없으면 "SDMPC prior price/application context mismatch"(sdmpc.py:774-783).
- 관측 checkpoint(`lane_observations/observer_checkpoint.json`)는 원자료에 없어 넣지 않았습니다.
- 재생마다 `run_replay.ps1` 이 pristine 을 작업 트리로 거울 복사한 뒤 VBS 와 같은 명령줄로 어댑터를 부릅니다. 바뀌거나 새로 생긴 파일만 `out/<라벨>/T<T>/files/` 에 모읍니다.

### 1.3 환경

- Python 3.12.2(시스템), 의존성 `D:/VISSIM-window264-deps`(numpy 2.3.5, numba 0.67.0, llvmlite 0.49.0, scipy 1.18.1, pandas 3.0.1; codex `current_environment_20261024.json` 과 같은 판). codex 기록은 Python 3.12.14.
- PYTHONHASHSEED=0(codex 런은 설정 안 함). 이 차이의 영향은 규칙상 시험하지 않았습니다.
- 이 PC: Intel Xeon Silver 4210R 2.4 GHz, 10코어 20스레드, AVX-512 있음. codex PC CPU 는 원자료에 기록이 없습니다(모름).
- 같은 때 다른 세션 프로세스가 돌았습니다(건드리지 않음). 초반에는 codex VISSIM 폐루프 1개, 이후 TD3 학습 python(BelowNormal)과 그 tangent 워커. 재생 중 이 PC CPU 전체 사용률 평균 34–61 %(우리 재생 포함, typeperf 5 s). 13:15 KST 뒤에는 다른 세션 프로세스가 없어 마지막 두 재생은 15–16 % 에서 돌았습니다("빈 PC").

---

## 2. 대조 규칙 A0-CMP-1 (요약)

- 규칙 파일 `work/a0/COMPARE_RULE_A0.md`(sha `a05f2071…`)는 첫 재생 발사(01:54:14 KST) 전에 고정했습니다. 첫 줄의 "02:20" 은 오기이며 LOG.md 에 고쳐 적었습니다.
- R1 명령 CSV sha 같음. R2 `joint_written.json` 의 `seven_action_fields_sha256`·`ordered_physical_rows_sha256`·`expected_live_metadata_sha256`·`expected_csv_sha256`·`ordered_row_count` 같음. R3 `scored_action_token` 같음. R4 JSON 여섯 개의 모든 잎 정확 일치(float repr 같음).
- 기록과 비교할 때 빼는 것: 시계 잎(정규식), 경로 잎(재배치 사상 적용 뒤), 경로에서 유도된 해시(사슬 근거를 하나씩 적음).
- 속도 후보 비교: 같은 env 의 이 PC 기준 재생과 R1–R4. 빼는 것은 시계 잎뿐입니다.
- 이번에 덧붙여 적는 것: 규칙 정규식이 못 잡는 `_sec` 소요시간 잎(결정당 14–21개)과 그것을 담은 action JSON 의 sha 한 칸이 기준 재생 사이에서도 늘 다릅니다. 이 문서는 그것을 "시계 잎(정규식 밖)" 으로 따로 셉니다. 규칙 파일은 고치지 않았습니다.

---

## 3. 이 PC 안 결정성 [실행]

| 대조 | T | R1 | R2 | R3 | 설명 안 된 잎 차이 | 근거 파일 |
|---|---|---|---|---|---|---|
| base_rep2(데운 캐시) 대 r900c_it01(차가운 numba·열기 추적) | 900 | 같음 | 같음 | 같음 | 0(시계 잎 + `_sec` 잎 14 + action JSON sha) | `out/base_rep2/T000900/compare_vs_r900c_it01.json` |
| spd_hsw 대 env_hsw | 900 | 같음 | 같음 | 같음 | 0(시계 82·152·6, `_sec` 14·14, sha 1) | `out/spd_hsw/T000900/candidate_vs_env_hsw.json` |
| spd_hsw 대 env_hsw | 2700 | 같음 | 같음 | 같음 | 0(시계 142·269·6, `_sec` 21·21, sha 1) | `out/spd_hsw/T002700/candidate_vs_env_hsw.json` |
| spd_hsw 대 env_hsw | 4950 | 같음 | 같음 | 같음 | 0(시계 146·277·6, `_sec` 21·21, sha 1) | `out/spd_hsw/T004950/candidate_vs_env_hsw.json` |
| spd_base 대 base_rep2 | 900 | 같음 | 같음 | 같음 | 0(시계 82·152·6, `_sec` 14·14, sha 1) | `out/spd_base/T000900/candidate_vs_base_rep2.json` |
| env_hsw_idle(빈 PC) 대 env_hsw | 900 | 같음 | 같음 | 같음 | 0(시계 82·152·6, `_sec` 14·14, sha 1) | `out/env_hsw_idle/T000900/candidate_vs_env_hsw.json` |
| spd_hsw_idle(빈 PC) 대 env_hsw_idle | 900 | 같음 | 같음 | 같음 | 0(시계 82·152·6, `_sec` 14·14, sha 1) | `out/spd_hsw_idle/T000900/candidate_vs_env_hsw_idle.json` |

- base_rep2 대 r900c_it01 은 `s27_candidate_check.py` 로도 다시 셌습니다: 시계 82·152·6, `_sec` 14·14, sha 1, 설명 안 된 차이 0(`out/base_rep2/T000900/candidate_vs_r900c_it01.json`).
- 위 쌍들은 부하(CPU 사용률 15–61 %), 캐시 상태(차가운/데운 numba, 차가운/데운 `__tangentcache__`), 열기 추적 유무가 서로 달랐습니다. [추론] 그래서 결과가 스레드 완료 순서나 시간에 기대지 않는다고 봅니다. 설정의 `ignore_wall_time_limits` 가 true 라 결정 안의 시간 한도도 꺼져 있습니다(`optimized_config.json` /adapter/joint_owner_game; decision_budget.json `scope_rule` "Wall limits explicitly disabled").
- 다만 env 를 바꾸면 이 PC 안에서도 결정이 바뀝니다. base_rep2 와 env_hsw 는 T=900 에서 R1 부터 다릅니다(23행).

---

## 4. codex 기록 재현 정도 [실행]

### 4.1 표

| env | T=900 | T=2700 | T=4950 |
|---|---|---|---|
| base | R1·R2·R3 다름. 23행(signal 3, signal_sg 20; SC6·107·1004). 녹색 ≤ 0.001 s, offset ≤ 0.004 s. 첫 차이: 진행 기록 20번째 줄(cap 1 첫 걸음 목적값) | R1·R2·R3 다름. 44행(signal 7, signal_sg 36, ramp_meter 1). 녹색 ≤ 0.008 s, offset ≤ 0.015 s, **RM_C10480 녹색 3 대 2 s(270 대 180 veh/h, group rate 356.4 대 255.6)**. 첫 차이: 5번째 줄(PFO 첫 걸음). 스칼라 롤아웃 112 대 113 | R1·R2·R3 다름. 33행(signal 5, signal_sg 28; SC1·6·11·1001·1004). 녹색 ≤ 0.001 s. 첫 차이: 5번째 줄. PFO 예측 6 대 7, tangent 롤아웃 14 대 15 |
| env_hsw | **R1·R2 같음**, R3 다름. 명령 CSV 0행 다름. 첫 차이: 32번째 줄(`sdmpc_derivatives_reused` key 해시) | R1·R2·R3 다름. 40행(signal 6, signal_sg 34; SC5·6·105·108·1001·1002). 녹색 ≤ 0.001 s, offset ≤ 0.003 s. 미터·VSL 행 같음. 첫 차이: 5번째 줄 | R1·R2·R3 다름. 17행(signal 3, signal_sg 14; SC1·107·1004). 녹색 ≤ 0.001 s. offset·미터·VSL 같음. 첫 차이: 20번째 줄 |
| env_hsw + S1 | env_hsw 와 같음 | env_hsw 와 같음 | env_hsw 와 같음 |
| base + S1 | base 와 같음 | (안 돌림) | (안 돌림) |
| py31214 + base | (안 돌림) | (안 돌림) | base 와 같음(33행) |
| py31214 + env_hsw | (안 돌림) | (안 돌림) | env_hsw 와 같음(17행) |

- 근거: `work/a0/a0_summary.json`, `out/<라벨>/T<T>/compare_vs_recorded.json`, `work/a0/progress_first_diff.json`(s29_progress_diff.py), s20_cmdsummary.py 출력.
- 명령 CSV 는 결정마다 213행(signal·signal_sg·ramp_meter 8·vsl 66 등)입니다.
- 작업 수: env_hsw(·S1)는 세 결정 모두 기록과 PFO 예측 수·롤아웃 수·요청 수·캐시 적중 수가 같습니다. base 는 T=2700·4950 에서 하나씩 다릅니다(§5 표 "작업 수" 줄).

### 4.2 첫 차이의 크기 [실행 `progress_first_diff.json`]

| 재생 | 첫 차이 줄 | 재생 값 | 기록 값 | 상대차 |
|---|---|---|---|---|
| base T=2700 | PFO 첫 걸음 omega_cost | 540.1224350071896 | 540.1224691429155 | 6.3e-8 |
| env_hsw T=2700 | PFO 첫 걸음 omega_cost | 540.122469288007 | 540.1224691429155 | 2.7e-10 |
| env_hsw T=2700 | PFO 첫 걸음 owned_cost | 335.5507667838243 | 335.5507655330638 | 3.7e-9 |
| base T=4950 | PFO 첫 걸음 omega_cost | 390.73034354605113 | 390.7303452990115 | 4.5e-9 |
| env_hsw T=4950 | cap 1 첫 걸음 objective | 389.71522909943474 | 389.71523037253365 | 3.3e-9 |
| base T=900 | cap 1 첫 걸음 objective | 424.6542073021855 | 424.65423030682797 | 5.4e-8 |

- [실행] PFO 첫 걸음 값은 첫 예측 묶음(롤아웃 1개, 미분 포함)과 owner 별 QP 한 바퀴 뒤에 나옵니다. 그래서 T=2700 에서는 plant 롤아웃 또는 첫 QP 에서 이미 마지막 자리가 갈립니다.
- [실행] 앞선 시도의 T=900 기록: 같은 PFO 안 `local_rows` 의 `own_gradient` 마지막 자리(−1.4638358840914507 대 …512)와 QP 반복 수(8 대 13)가 이미 다르고, tangent 테이프 노드 수(3,246,935 대 3,246,960) 등으로 번집니다(LOG 02:33·02:58 항목).
- [추론] 후보 원인: CPU 명령 집합(AVX-512 대 codex PC 의 모르는 CPU), OpenBLAS 커널, numpy SIMD 분기, numba 대상 CPU, Windows C 런타임 수학 함수, PYTHONHASHSEED. 인터프리터 판은 §8 에서 빠졌습니다. env_hsw 가 차이를 줄였으므로(T=2700 PFO 첫 걸음 omega_cost 상대차 6.3e-8 → 2.7e-10, T=900 은 명령 일치, 작업 수는 세 결정 모두 기록과 같아짐) 앞의 셋이 몫을 가집니다. 해시 시드는 규칙상 0 으로만 돌려 시험하지 않았습니다.
- [추론] 작은 차이가 이산 선택을 뒤집을 수 있습니다. base T=2700 의 RM_C10480 녹색 1 s 차이가 그 예입니다. 폐루프에서는 한 결정의 다른 명령이 다음 상태를 바꾸므로, 처음 다른 결정 뒤로는 기록과 같은 상태에서 결정하지 않게 됩니다.

---

## 5. 시간 분해 [실행]

### 5.1 방법

- `work/a0/s22_profile_all.py`: 진행 기록(`action_T.joint.progress.jsonl`)의 단계 시각, `decision_budget.json`(벽시계·주 프로세스 CPU·적재·마무리), `joint.json /physical_response_cache/rows`(롤아웃 한 번씩의 벽시계), `/selection/tangent_derivatives`(tangent 미분 한 번씩), `/selection/gradient_rows`(기울기 방법), typeperf CPU 표본을 읽습니다. 표는 `s26_tables.py`.
- 단계 이름과 코드 위치 [읽음]: cap 반복은 sdmpc.py:1088-1215. cap 마다 tangent(역방향 AD, 다른 프로세스에서 겹쳐 돎) + VSL secant 24평가(8 워커) + 걸음 예측. cap 2·3 은 cap 1 의 미분을 재사용합니다(`sdmpc_derivatives_reused`, `response_cap_cache`). cap 2 의 진행 기록 없는 구간은 owner 별 QP(`solve_qp`, scipy `minimize`, sdmpc.py:692-700, 1066-1079)와 중앙 복원(`central.recover`, nnls)입니다. 롤아웃이 없고 주 프로세스 한 코어에서 돕니다(복원 뒤 롤아웃 수 불변 검사, sdmpc.py:1200-1202).
- 기울기 행: green·offset·meter 는 `compiled_reverse_active_path`(AD), vsl 은 `executable_secant_fallback`(secant). 세 결정 모두 기록과 행 수가 같습니다.

### 5.2 표

(배수는 codex PC 기록 대비. "env_hsw+S1" 은 속도 후보 S1 을 켠 재생.)

#### T = 900 s

| 항목 | codex PC 기록 | 이 PC base(반복) | 이 PC env_hsw | 이 PC env_hsw+S1 | 이 PC base+S1 | 이 PC env_hsw (빈 PC) | 이 PC env_hsw+S1 (빈 PC) |
|---|---|---|---|---|---|---|---|
| 결정 전체 벽시계 (decision_budget wall_sec) | 228.8 | 601.2 (×2.63) | 588.1 (×2.57) | 525.6 (×2.30) | 526.7 (×2.30) | 534.1 (×2.33) | 529.5 (×2.31) |
| 주 프로세스 CPU (cpu_sec) | 94.6 | 269.1 (×2.85) | 250.4 (×2.65) | 216.3 (×2.29) | 232.8 (×2.46) | 242.4 (×2.56) | 239.8 (×2.54) |
| 적재·모형 준비 (load_and_model_prepare) | 6.6 | 18.4 (×2.78) | 21.0 (×3.17) | 16.1 (×2.43) | 15.5 (×2.34) | 19.0 (×2.87) | 17.6 (×2.66) |
| 마무리 검증·출력 (final_action_validation_and_output) | 4.0 | 11.3 (×2.86) | 12.5 (×3.16) | 11.4 (×2.87) | 11.9 (×3.01) | 11.5 (×2.91) | 11.2 (×2.83) |
| joint 밖 나머지 (전체 − joint 끝 − 적재 − 마무리) | 25.5 | 18.9 (×0.74) | 20.6 (×0.81) | 18.0 (×0.71) | 20.3 (×0.80) | 20.7 (×0.81) | 19.7 (×0.77) |
| PFO 따뜻한 시작 (sdmpc_pfo_done.seconds) | 47.0 | 106.3 (×2.26) | 114.9 (×2.44) | 103.6 (×2.20) | 92.6 (×1.97) | 100.5 (×2.14) | 96.9 (×2.06) |
| cap 1 전체 | 68.7 | 185.1 (×2.69) | 186.6 (×2.72) | 168.1 (×2.45) | 168.7 (×2.46) | 155.6 (×2.27) | 158.7 (×2.31) |
|   cap 1 VSL secant 묶음 (derivatives_start→done) | 48.6 | 122.6 (×2.52) | 126.6 (×2.60) | 118.3 (×2.43) | 116.9 (×2.40) | 103.3 (×2.12) | 105.7 (×2.17) |
|   cap 1 걸음 예측 묶음 | 18.8 | 58.3 (×3.11) | 56.3 (×3.00) | 46.7 (×2.49) | 48.3 (×2.57) | 48.7 (×2.59) | 48.8 (×2.60) |
|   cap 1 tangent (겹쳐 돎, 합) | 26.9 | 74.5 (×2.77) | 74.5 (×2.77) | 66.2 (×2.46) | 60.6 (×2.25) | 64.9 (×2.41) | 63.7 (×2.37) |
| cap 2 전체 (미분 재사용) | 54.8 | 199.0 (×3.64) | 174.1 (×3.18) | 150.6 (×2.75) | 163.8 (×2.99) | 169.2 (×3.09) | 168.4 (×3.08) |
|   cap 2 진행 기록 없는 구간 (QP·중앙 복원, 주 프로세스) | 54.8 | 199.0 (×3.64) | 174.1 (×3.18) | 150.6 (×2.75) | 163.8 (×2.99) | 169.2 (×3.09) | 168.4 (×3.08) |
| cap 3 전체 | 0.2 | 0.8 (×3.18) | 0.7 (×2.90) | 0.7 (×3.16) | 0.7 (×3.16) | 0.8 (×3.25) | 0.8 (×3.35) |
| 미터 이웃 검사 전체 | 20.2 | 57.2 (×2.84) | 53.3 (×2.64) | 53.1 (×2.63) | 49.6 (×2.46) | 52.7 (×2.61) | 52.4 (×2.60) |
| plant 스칼라 롤아웃 중앙값 (1회) | 7.9 | 19.2 (×2.44) | 19.5 (×2.47) | 19.5 (×2.47) | 18.9 (×2.40) | 16.6 (×2.11) | 16.9 (×2.14) |
| plant 스칼라 롤아웃 합 (워커 합) | 470.5 | 1204.0 (×2.56) | 1202.9 (×2.56) | 1145.7 (×2.43) | 1123.8 (×2.39) | 1008.6 (×2.14) | 1027.2 (×2.18) |
| plant tangent 롤아웃 중앙값 (1회) | 16.2 | 35.2 (×2.17) | 37.6 (×2.32) | 34.3 (×2.11) | 30.6 (×1.89) | 32.2 (×1.99) | 32.2 (×1.98) |
| tangent 미분 1회 tangent_sec 평균 | 9.8 | 31.4 (×3.21) | 31.5 (×3.22) | 27.7 (×2.83) | 24.8 (×2.54) | 26.4 (×2.70) | 26.1 (×2.67) |
| 진행 기록 두 줄 사이 최대 간격 (워치독 idle 상한 근거) | 54.7 | 198.9 (×3.64) | 174.0 (×3.18) | 150.6 (×2.75) | 163.6 (×2.99) | 169.0 (×3.09) | 168.2 (×3.08) |
| tangent 미분 1회 spawn 포함 벽시계 평균 | 13.5 | 37.2 (×2.77) | 37.3 (×2.77) | 33.1 (×2.46) | 30.3 (×2.25) | 32.4 (×2.41) | 31.8 (×2.36) |
| cap 후보 수 | 3 | 3 | 3 | 3 | 3 | 3 | 3 |
| PFO 예측 수 | 6 | 6 | 6 | 6 | 6 | 6 | 6 |
| VSL secant 평가 수 (cap 합) | 48 | 48 | 48 | 48 | 48 | 48 | 48 |
| 이웃 검사 예측 수 | 11 | 11 | 11 | 11 | 11 | 11 | 11 |
| plant 스칼라 롤아웃 수 | 61 | 61 | 61 | 61 | 61 | 61 | 61 |
| plant tangent 롤아웃 수 | 7 | 7 | 7 | 7 | 7 | 7 | 7 |
| 응답 요청 / 캐시 적중 | 86 / 18 | 86 / 18 | 86 / 18 | 86 / 18 | 86 / 18 | 86 / 18 | 86 / 18 |
| 기울기 행 (green·offset·meter: AD, vsl: secant) | 276/102/48/48 | 276/102/48/48 | 276/102/48/48 | 276/102/48/48 | 276/102/48/48 | 276/102/48/48 | 276/102/48/48 |
| 이 PC CPU 전체 사용률 평균 % (typeperf 5 s) | — | 58.1 | 56.5 | 41.7 | 38.2 | 15.4 | 16.0 |

#### T = 2700 s

| 항목 | codex PC 기록 | 이 PC base | 이 PC env_hsw | 이 PC env_hsw+S1 |
|---|---|---|---|---|
| 결정 전체 벽시계 (decision_budget wall_sec) | 425.0 | 1059.8 (×2.49) | 1112.7 (×2.62) | 993.5 (×2.34) |
| 주 프로세스 CPU (cpu_sec) | 118.8 | 317.1 (×2.67) | 277.8 (×2.34) | 251.0 (×2.11) |
| 적재·모형 준비 (load_and_model_prepare) | 13.2 | 38.6 (×2.93) | 38.6 (×2.93) | 35.6 (×2.71) |
| 마무리 검증·출력 (final_action_validation_and_output) | 6.6 | 18.2 (×2.77) | 17.3 (×2.63) | 17.8 (×2.71) |
| joint 밖 나머지 (전체 − joint 끝 − 적재 − 마무리) | 27.0 | 35.7 (×1.32) | 34.7 (×1.28) | 33.4 (×1.23) |
| PFO 따뜻한 시작 (sdmpc_pfo_done.seconds) | 63.5 | 145.2 (×2.29) | 154.8 (×2.44) | 135.9 (×2.14) |
| cap 1 전체 | 106.7 | 254.6 (×2.39) | 273.4 (×2.56) | 263.8 (×2.47) |
|   cap 1 VSL secant 묶음 (derivatives_start→done) | 74.1 | 176.2 (×2.38) | 192.3 (×2.59) | 184.9 (×2.50) |
|   cap 1 걸음 예측 묶음 | 31.4 | 75.2 (×2.40) | 78.0 (×2.49) | 75.9 (×2.42) |
|   cap 1 tangent (겹쳐 돎, 합) | 43.7 | 91.3 (×2.09) | 102.3 (×2.34) | 92.3 (×2.11) |
| cap 2 전체 (미분 재사용) | 57.3 | 191.4 (×3.34) | 153.2 (×2.67) | 131.5 (×2.29) |
|   cap 2 진행 기록 없는 구간 (QP·중앙 복원, 주 프로세스) | 57.3 | 191.4 (×3.34) | 153.2 (×2.67) | 131.5 (×2.29) |
| cap 3 전체 | 68.7 | 165.1 (×2.40) | 190.1 (×2.77) | 174.8 (×2.55) |
| 미터 이웃 검사 전체 | 78.7 | 202.2 (×2.57) | 242.4 (×3.08) | 193.1 (×2.45) |
| plant 스칼라 롤아웃 중앙값 (1회) | 11.8 | 28.8 (×2.44) | 33.0 (×2.79) | 29.8 (×2.52) |
| plant 스칼라 롤아웃 합 (워커 합) | 1322.7 | 3248.4 (×2.46) | 3880.0 (×2.93) | 3351.5 (×2.53) |
| plant tangent 롤아웃 중앙값 (1회) | 21.9 | 46.9 (×2.14) | 49.6 (×2.26) | 48.1 (×2.19) |
| tangent 미분 1회 tangent_sec 평균 | 14.6 | 37.9 (×2.59) | 41.7 (×2.85) | 40.9 (×2.80) |
| 진행 기록 두 줄 사이 최대 간격 (워치독 idle 상한 근거) | 57.3 | 191.3 (×3.34) | 153.2 (×2.67) | 131.4 (×2.29) |
| tangent 미분 1회 spawn 포함 벽시계 평균 | 22.1 | 46.3 (×2.10) | 50.7 (×2.30) | 48.7 (×2.21) |
| cap 후보 수 | 3 | 3 | 3 | 3 |
| PFO 예측 수 | 6 | 6 | 6 | 6 |
| VSL secant 평가 수 (cap 합) | 72 | 72 | 72 | 72 |
| 이웃 검사 예측 수 | 35 | 35 | 35 | 35 |
| plant 스칼라 롤아웃 수 | 113 | 112 | 113 | 113 |
| plant tangent 롤아웃 수 | 12 | 12 | 12 | 12 |
| 응답 요청 / 캐시 적중 | 129 / 4 | 128 / 4 | 129 / 4 | 129 / 4 |
| 기울기 행 (green·offset·meter: AD, vsl: secant) | 414/153/72/72 | 414/153/72/72 | 414/153/72/72 | 414/153/72/72 |
| 이 PC CPU 전체 사용률 평균 % (typeperf 5 s) | — | 38.4 | 61.1 | 45.3 |

#### T = 4950 s

| 항목 | codex PC 기록 | 이 PC base | 이 PC env_hsw | 이 PC env_hsw+S1 | 이 PC base, Py3.12.14 | 이 PC env_hsw, Py3.12.14 |
|---|---|---|---|---|---|---|
| 결정 전체 벽시계 (decision_budget wall_sec) | 381.7 | 942.9 (×2.47) | 960.9 (×2.52) | 904.1 (×2.37) | 924.7 (×2.42) | 928.6 (×2.43) |
| 주 프로세스 CPU (cpu_sec) | 109.8 | 262.5 (×2.39) | 280.8 (×2.56) | 254.7 (×2.32) | 266.1 (×2.42) | 281.8 (×2.57) |
| 적재·모형 준비 (load_and_model_prepare) | 10.2 | 30.8 (×3.01) | 32.7 (×3.20) | 29.0 (×2.83) | 29.4 (×2.87) | 32.0 (×3.12) |
| 마무리 검증·출력 (final_action_validation_and_output) | 6.0 | 17.9 (×3.00) | 18.4 (×3.08) | 15.6 (×2.61) | 17.8 (×2.99) | 18.3 (×3.06) |
| joint 밖 나머지 (전체 − joint 끝 − 적재 − 마무리) | 22.4 | 31.0 (×1.38) | 32.3 (×1.44) | 29.9 (×1.33) | 28.1 (×1.25) | 30.7 (×1.37) |
| PFO 따뜻한 시작 (sdmpc_pfo_done.seconds) | 52.3 | 114.2 (×2.18) | 142.6 (×2.73) | 123.6 (×2.36) | 117.3 (×2.24) | 115.8 (×2.21) |
| cap 1 전체 | 88.7 | 218.0 (×2.46) | 199.8 (×2.25) | 202.4 (×2.28) | 214.0 (×2.41) | 214.7 (×2.42) |
|   cap 1 VSL secant 묶음 (derivatives_start→done) | 61.5 | 147.6 (×2.40) | 136.8 (×2.22) | 139.2 (×2.26) | 147.4 (×2.40) | 147.2 (×2.39) |
|   cap 1 걸음 예측 묶음 | 26.2 | 67.2 (×2.57) | 59.7 (×2.28) | 60.0 (×2.29) | 63.4 (×2.42) | 64.4 (×2.46) |
|   cap 1 tangent (겹쳐 돎, 합) | 36.7 | 79.1 (×2.16) | 96.8 (×2.64) | 75.5 (×2.06) | 85.5 (×2.33) | 77.5 (×2.11) |
| cap 2 전체 (미분 재사용) | 72.3 | 191.3 (×2.65) | 201.5 (×2.79) | 188.7 (×2.61) | 194.4 (×2.69) | 209.2 (×2.89) |
|   cap 2 진행 기록 없는 구간 (QP·중앙 복원, 주 프로세스) | 56.3 | 149.1 (×2.65) | 164.6 (×2.92) | 148.5 (×2.64) | 157.4 (×2.80) | 166.4 (×2.96) |
| cap 3 전체 | 58.5 | 142.8 (×2.44) | 141.6 (×2.42) | 129.3 (×2.21) | 139.1 (×2.38) | 126.4 (×2.16) |
| 미터 이웃 검사 전체 | 68.8 | 188.8 (×2.75) | 184.0 (×2.68) | 179.4 (×2.61) | 176.8 (×2.57) | 174.0 (×2.53) |
| plant 스칼라 롤아웃 중앙값 (1회) | 10.1 | 24.4 (×2.43) | 22.5 (×2.24) | 22.9 (×2.28) | 23.2 (×2.31) | 22.4 (×2.23) |
| plant 스칼라 롤아웃 합 (워커 합) | 1122.6 | 2776.7 (×2.47) | 2604.4 (×2.32) | 2633.8 (×2.35) | 2655.5 (×2.37) | 2588.3 (×2.31) |
| plant tangent 롤아웃 중앙값 (1회) | 18.7 | 41.6 (×2.23) | 43.6 (×2.33) | 39.3 (×2.10) | 42.0 (×2.25) | 38.5 (×2.06) |
| tangent 미분 1회 tangent_sec 평균 | 11.6 | 33.4 (×2.87) | 32.4 (×2.79) | 29.7 (×2.55) | 36.0 (×3.10) | 30.5 (×2.63) |
| 진행 기록 두 줄 사이 최대 간격 (워치독 idle 상한 근거) | 56.1 | 148.7 (×2.65) | 164.2 (×2.93) | 148.1 (×2.64) | 157.1 (×2.80) | 166.1 (×2.96) |
| tangent 미분 1회 spawn 포함 벽시계 평균 | 18.6 | 40.5 (×2.18) | 46.7 (×2.51) | 36.6 (×1.97) | 43.2 (×2.33) | 38.0 (×2.05) |
| cap 후보 수 | 3 | 3 | 3 | 3 | 3 | 3 |
| PFO 예측 수 | 7 | 6 | 7 | 7 | 6 | 7 |
| VSL secant 평가 수 (cap 합) | 72 | 72 | 72 | 72 | 72 | 72 |
| 이웃 검사 예측 수 | 36 | 36 | 36 | 36 | 36 | 36 |
| plant 스칼라 롤아웃 수 | 114 | 114 | 114 | 114 | 114 | 114 |
| plant tangent 롤아웃 수 | 15 | 14 | 15 | 15 | 14 | 15 |
| 응답 요청 / 캐시 적중 | 133 / 4 | 132 / 4 | 133 / 4 | 133 / 4 | 132 / 4 | 133 / 4 |
| 기울기 행 (green·offset·meter: AD, vsl: secant) | 414/153/72/72 | 414/153/72/72 | 414/153/72/72 | 414/153/72/72 | 414/153/72/72 | 414/153/72/72 |
| 이 PC CPU 전체 사용률 평균 % (typeperf 5 s) | — | 49.5 | 39.2 | 44.3 | 41.9 | 34.0 |

### 5.3 읽기

- [실행] 결정 전체는 2.30–2.63배입니다(데운 캐시 재생 16개; 차가운 첫 완주 2.73배). 빈 PC 의 T=900 은 2.31–2.33배입니다. 주 프로세스 CPU 는 2.11–2.85배입니다.
- [실행] 늦어지는 몫이 고릅니다(데운 재생 기준). plant 스칼라 롤아웃 한 번 2.11–2.79배, tangent 롤아웃 1.89–2.33배, VSL secant 묶음 2.12–2.60배, 이웃 검사 2.45–3.08배, cap 2 QP 구간 2.29–3.64배, 적재·모형 준비 2.34–3.20배, 마무리 2.61–3.16배.
- [실행] 빈 PC 에서는 롤아웃·secant 가 2.11–2.17배로 내려갔지만 cap 2 QP 구간은 3.08–3.09배로 남았습니다(T=900).
- [추론] 특정 단계의 병목(스레드 부족, 캐시 미스, 프로세스 생성)이라기보다 이 PC 의 한 코어 속도 차가 주이고, 다른 세션 부하가 그 위에 0–15 % 를 더한다고 봅니다. 근거: 롤아웃 수·예측 수가 같고, 단계별 배수가 비슷하며, 빈 PC 에서도 2.3배가 남습니다. 주 프로세스 한 코어에서 도는 QP 구간(scipy)은 다른 단계보다 더 늦습니다.
- [실행] 이 PC 에서 시간이 가는 곳(env_hsw, 세 결정 합 2,661.7 s): cap 1 659.8 s(그 중 VSL secant 455.7 s), cap 2 528.8 s(그 중 QP 구간 491.9 s), 이웃 검사 479.7 s, PFO 412.2 s, cap 3 332.4 s(그 중 VSL secant 178.0 s), joint 밖(적재·마무리·나머지) 228.0 s, PFO 앞·사이 약 21 s. VSL secant 를 합치면 633.7 s(24 %)입니다.
- [실행] 진행 기록 두 줄 사이 최대 간격은 이 PC 131–199 s(codex PC 55–57 s)이고 모두 cap 2 QP 구간입니다. 워치독은 시간 무제한 결정에서 이 기록 쓰기도 진행으로 셉니다(watchdog:992-997). 그래서 StallSec 2,400 s 와는 여유가 큽니다.
- [실행] 차가운 시작 비용: 첫 완주(r900c_it01)에서 `evaluation/controllers/__tangentcache__` 116개 파일(5.2 MB)을 02:21:33–02:22:07 에 썼고, numba 캐시는 3개 함수(`sdmpc_tangent_reverse._reverse_row`, `sdmpc_tangent_constraints._forward_column_from`, `_mark_ancestors`)뿐입니다. NUMBA_CPU_NAME=haswell 은 별도 캐시 항목(.2.nbc)을 만듭니다. 차가운 첫 완주 623.6 s 대 데운 반복 601.2 s(열기 추적 포함 차 22 s).

### 5.4 재생별 결정 벽시계 [실행 `work/a0/prof_all_final.json`]

| 라벨 | T | env·변경 | 재생 프로세스 벽시계 s | 결정 벽시계 s (budget) | codex PC s | 배수 | 이 PC CPU 평균 % |
|---|---|---|---|---|---|---|---|
| r900c_it01 | 900 | base, 차가운 캐시·열기 추적 | 624.6 | 623.6 | 228.8 | 2.73 | 61.4 |
| base_rep2 | 900 | base | 602.2 | 601.2 | 228.8 | 2.63 | 58.1 |
| base | 2700 | base | 1061.1 | 1059.8 | 425.0 | 2.49 | 38.4 |
| base | 4950 | base | 944.1 | 942.9 | 381.7 | 2.47 | 49.5 |
| env_hsw | 900 | env_hsw | 589.0 | 588.1 | 228.8 | 2.57 | 56.5 |
| env_hsw | 2700 | env_hsw | 1114.1 | 1112.7 | 425.0 | 2.62 | 61.1 |
| env_hsw | 4950 | env_hsw | 962.3 | 960.9 | 381.7 | 2.52 | 39.2 |
| spd_hsw | 900 | env_hsw + S1 | 527.3 | 525.6 | 228.8 | 2.30 | 41.7 |
| spd_hsw | 2700 | env_hsw + S1 | 994.7 | 993.5 | 425.0 | 2.34 | 45.3 |
| spd_hsw | 4950 | env_hsw + S1 | 905.3 | 904.1 | 381.7 | 2.37 | 44.3 |
| spd_base | 900 | base + S1 | 527.6 | 526.7 | 228.8 | 2.30 | 38.2 |
| tmo2390_hsw | 900 | env_hsw, 시한 키 2390 | 531.4 | 530.4 | 228.8 | 2.32 | 38.5 |
| py31214_base | 4950 | base, Python 3.12.14 | 926.0 | 924.7 | 381.7 | 2.42 | 41.9 |
| py31214_hsw | 4950 | env_hsw, Python 3.12.14 | 929.9 | 928.6 | 381.7 | 2.43 | 34.0 |
| env_hsw_idle | 900 | env_hsw, 빈 PC | 535.1 | 534.1 | 228.8 | 2.33 | 15.4 |
| spd_hsw_idle | 900 | env_hsw + S1, 빈 PC | 530.7 | 529.5 | 228.8 | 2.31 | 16.0 |

- codex PC 값은 기록 `decision_budget.json /wall_sec` 입니다. 같은 결정의 runlog `CONTROLLER_DECISION wall_sec` 는 229.39·425.66·382.53 s 입니다.
- 실패한 준비 재생(base_cold_trace·…4, r900_it01·r900b_it01, env_hsw_fail_applied)은 데이터 파일·영수증 경로 문제로 결정 계산 전에 멈춘 것이라 표에서 뺐습니다(LOG 02:05–03:00 항목).

### 5.5 codex PC 결정 시간 전체 [실행 `work/a0/decision_times.json`, `work/a0/a1_estimate.json`]

- codex joint 런: 900–8100 s 결정 49개 합 14,088.1 s, 평균 287.5 s, 중앙 276.5 s, 최대 448.6 s(T=2400), 6900 은 11.45 s 만에 exit 1(ValueError, RAW_CHECK §7.5). 900 전 결정 6개 합 45.5 s. 런 전체 17,264 s(launch.log). 결정 밖 시간 3,130.4 s.
- codex 다섯 팔(window 12:32–16:25, joint 16:34–21:22, off 21:30–00:45 등)은 시간이 겹치지 않습니다(각 launch.log). [읽음] 인계 러너는 다른 VISSIM 이 열려 있으면 발사를 거부합니다(run_closedloop3000.ps1:164-172).
- 이 PC 의 W264(1,709 s/결정)는 다른 설정(`vsl_window264/config.json`, f181dc1d…)입니다. 그 설정에는 `sdmpc_response_cap_cache` 가 없고 시한이 0 입니다(설정 비교 [실행]). 그래서 A1 시간 어림에 쓰지 않습니다. W264 의 PFO 첫 예측 한 개가 130.4 s(joint 재생 약 50 s)인 까닭은 확인하지 않았습니다.

---

## 6. 속도 변경 목록과 시험

### 6.1 우리 줄기 git log [실행]

- GWT8 `D:/VISSIM-merge/sim3-n31-k8` HEAD c20aff1d, 공통 조상 886a014a(merge-base 확인). 886a014a..HEAD 65커밋.
- 메시지·diff 어디에도 속도·캐시·병렬·numba·tangent 동시성 변경이 없습니다. SDMPC 파일 변경은 `sdmpc.py`(+17/−2, 91bfa56e K8-3 meter spill 귀속)와 `sdmpc_dual.py`(+19, 5eef6bec K8-2 has_transfer) 뿐입니다. 새 팔 설정 파일들의 `response_parallel_workers` 8·`sdmpc_derivative_workers` 8 은 기존 값 그대로입니다.
- 참고: codex 쪽은 886a014a 대비 `sdmpc.py` +374, `sdmpc_tangent_surrogate.py` +98, 새 `sdmpc_aggregate_transport.py`·`sdmpc_terminal.py` 등 1,133줄을 더했습니다(공백 무시 diff). 그 가운데 속도 기구로 설정에 켜진 것은 `sdmpc_response_cap_cache` 입니다.

### 6.2 설정 비교 — 우리 V-A 설정 대 codex joint 설정 [실행 `work/a0/speedkeys_ours_vs_codex.json`]

- 대상: 우리 `diagnostics/sdmpc_n31_20260924/config_n31_v2.json`(GWT8) 대 codex `native413_adopted355/optimized_config.json`. 이름이 속도·캐시·병렬·예산·후보·검사에 관한 키 56개.
- 같음 49개. 다름 7개: `max_leader_candidates` 1 대 3, `sdmpc_meter_neighbor_audit` 없음 대 true, `sdmpc_response_cap_cache` 없음 대 true, `runtime.decision_timeout_sec` 없음 대 1800, 그리고 속도와 무관한 셋(`urban.preserve_direct_offramp_destinations`, `urban.storage_release_guard.reserve_green_sec`, `_area_revision`).
- [추론] 앞의 둘은 D-K9-83 이 금한 "덜 계산해서 빠른 것" 입니다. 우리 V-A 결정이 이 PC 에서 470–560 s 로 codex joint 재생(526–1,113 s)보다 짧은 것은 주로 이 차이로 봅니다. 옮길 우리 쪽 속도 기구는 없습니다.

### 6.3 설정 후보와 시험 결과

| 후보 | 뜻에 닿는가 | 시험 | 결과 |
|---|---|---|---|
| S1-a `PYTHONPYCACHEPREFIX`(코드 트리 밖, compileall 로 채움) | [읽음] 같은 소스에서 만든 바이트코드라 계산 바뀜 없음. 워치독·러너가 이 변수를 지우지 않음(grep) | env_hsw 3결정 + base T=900 + 빈 PC T=900 | 5개 모두 같은 env 기준과 R1·R2·R3 같음, 설명 안 된 잎 차이 0 [실행 §3] |
| S1-b `NUMBA_NUM_THREADS=2` | [읽음] prange 커널은 `sdmpc_tangent_spatial.py:152-157` 하나뿐이고 `sdmpc_spatial_receiving` 에서만 불림. codex 설정에 그 키가 없고, 그 캐시 파일도 a0 에 생기지 않음 [실행] → 이 설정에서는 계산 경로가 없음 | S1-a 와 함께 | 같음(위). 효과도 없을 것으로 봄 [추론] |
| tangent 워커 수(`sdmpc_derivative_workers`) | [읽음] 8 로 묶여 있음. `surrogate_reuse`·`trial_derivative_overlap`·`spatial_receiving` 이 8 을 요구(sdmpc.py:213-216, 236-242). 영수증 잎에 워커 수가 기록됨 | 안 함 | 바꾸면 설정 바이트와 영수증 잎이 바뀜 → 후보 아님 |
| 응답 워커 수(`response_parallel_workers` 8) | [읽음] 설정 키, 결정 기록에 남음 | 안 함 | 같은 까닭으로 후보 아님 |
| OMP/OPENBLAS/MKL 스레드 해제 | [읽음 메모리 vissim-sdmpc-flags-rejected] 이득 0, BLAS 축약 순서를 바꿔 결정을 움직일 수 있는 변경 | 안 함 | 후보 아님 |
| 기각된 고속 경로 키(`persistent_urban_fifo`·`array_urban_pipeline`·`flow_update_cache`·`array_transport`·`spatial_receiving`) | [읽음 같은 메모리] 수치 동등성 통과 뒤 속도로 기각된 영수증이 있음(예: 386.693 → 444.002 s) | 안 함 | 다시 시험하지 않음 |
| 프로세스 우선순위 Normal | [읽음] 시간 한도 꺼짐이라 계산에 닿지 않음. 규칙상 A0 재생은 BELOW_NORMAL 만 | 안 함 | A1 발사 방식 결정으로 넘김(PRE_A1 U5) |
| 차가운 캐시 미리 데우기(`__tangentcache__`, numba) | [읽음] freeze_manifest.py 가 `__pycache__`·`__tangentcache__` 를 동결 검사에서 뺌. 캐시는 소스 sha 로 찾음 | 안 함 | 첫 무거운 결정에서 한 번 수십 초. 12 h 런에서 무시할 만함 [추론] |

- S1 의 시간, 부하가 다른 때 [실행]: 같은 env 기준 대비 T=900 env_hsw 525.6/588.1 = 0.89, T=2700 993.5/1,112.7 = 0.89, T=4950 904.1/960.9 = 0.94, base T=900 526.7/601.2 = 0.88. 같은 때 CPU 사용률이 달랐습니다(S1 38.2–45.3 %, 기준 39.2–61.1 %).
- S1 의 시간, 빈 PC 에서 나란히 [실행]: env_hsw_idle 534.1 s 대 spd_hsw_idle 529.5 s = −4.5 s(−0.85 %). 적재·모형 준비 19.0 → 17.6 s, PFO 100.5 → 96.9 s, tangent 프로세스 생성 몫 약 0.4 s 줄어듦. QP 구간 169.2 대 168.4 s, 롤아웃 중앙값 16.6 대 16.9 s 로 같은 수준.
- [추론] S1 의 몫은 프로세스 시작·import 쪽 결정당 수 초(1 % 안팎)입니다. A1 49결정이면 약 3–4 분입니다. 앞의 0.88–0.94배는 부하 흔들림이었습니다.

---

## 7. 시한 키만 바꾼 tuning 시험 [실행]

- 왜: PRE_A1 의 시한 선택(U3)에서 "tuning 의 시한 키만 바꾸면 결정이 바뀌는가" 를 미리 보려고. 시한 자체는 VBS 가 쓰고 어댑터는 읽지 않습니다(grep 0) [실행].
- 무엇: a0 트리 안 tuning 사본 `optimized_config_t2390.json` = 원본(`c9088262…`)에서 `"decision_timeout_sec": 1800` 한 칸만 2390 으로(sha `9365141f…`, 287,486 B 같은 길이; `work/a0/s24_tuning_variant.py`). `RW_SIGNAL_OBSERVATION_CONFIG_SHA256` 도 새 sha 로(워치독이 그렇게 넘김, watchdog:231). env_hsw, T=900. 라벨 tmo2390_hsw. 같은 env 기준 env_hsw T=900 과 대조.
- 결과: 종료 0, 531.4 s. **R1·R2·R3 같음.** 명령 CSV 는 기록과도 0행 다름.
- R4 에서 시계 잎 말고 다른 것(모두 tuning 파일의 이름·sha 에서 온 것으로 설명됨):
  - 해시 잎: action JSON 16, joint.json 14. `budget_initialization/frozen_context_token`, `reference_response_token`, `tangent_derivatives/<i>/request_sha256`, `surrogate_prediction/frozen_context_token`·`response_token` 꼴.
  - 경로 잎 2: `run_provenance/inputs/tuning_json/path`(파일 이름이 다르므로).
  - joint.json `/source_sha256` 에 새 tuning 핀 1개가 더해짐.
- [추론] A1 에서 같은 이름의 파일을 고쳐 쓰면 경로 잎은 같고, 문맥 토큰 해시 30개 남짓만 바뀔 것입니다. 채점 토큰과 명령은 이 결정에서 바뀌지 않았습니다. 한 결정·한 env 만 본 결과입니다.

---

## 8. 인터프리터를 codex 판으로 바꾼 시험 [실행]

- 왜: codex 기록은 Python 3.12.14 이고 우리는 3.12.2 입니다. 이 PC 에 codex 런타임 Python 이 있습니다(`C:/Users/TRLAB/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe`, "3.12.14 (main, Aug 25 2026, 14:01:42) [MSC v.1944 64 bit (AMD64)]") [실행]. 인계 `derived/current_environment_20261024.json /python` 과 같은 빌드 문자열입니다. 당시 판은 `/historical_python` "모름" 입니다 [실행].
- 무엇: 인터프리터만 바꾸고(`run_replay2.ps1 -PyExe`) 의존성은 같은 `D:/VISSIM-window264-deps`(두 Python 모두 numpy 2.3.5·numba 0.67.0·scipy 1.18.1·llvmlite 0.49.0 을 거기서 읽음 [실행]). 차이가 가장 적게 남은 T=4950 에서 base·env_hsw 두 번.

| 재생 | 벽시계 | 같은 env 의 3.12.2 재생 대비 | 기록 대비 |
|---|---|---|---|
| py31214_base T=4950 | 926.0 s | R1·R2·R3 같음, 설명 안 된 잎 차이 0(시계 145·275·6, `_sec` 21·21, sha 1) | base 와 같은 33행 |
| py31214_hsw T=4950 | 929.9 s | R1·R2·R3 같음, 설명 안 된 잎 차이 0(시계 146·277·6, `_sec` 21·21, sha 1) | env_hsw 와 같은 17행 |

- [추론] 이 결정에서 인터프리터 판은 결과에 닿지 않습니다. 기록과의 남은 차이는 인터프리터 밖에 있습니다. 남은 후보는 CPU 명령 집합·OpenBLAS 커널·numpy SIMD 분기(env_hsw 가 일부를 맞춤), numba 대상 CPU, Windows C 런타임 수학 함수, PYTHONHASHSEED 입니다. codex PC 의 CPU·OS 를 모르므로 더 좁히는 시험(예: `OPENBLAS_CORETYPE` 다른 값)은 근거 없이 고르는 일이 됩니다. 그래서 하지 않았습니다(PRE_A1 U1).

---

## 9. 모름과 까닭

- codex PC 의 CPU·OS·C 런타임: 원자료에 기록 없음. 그래서 env_hsw 가 codex PC 계산 경로와 같은지 모릅니다.
- codex 런 당시 Python 빌드: `current_environment_20261024.json /historical_python` = "모름". 지금 판(3.12.14, 2026-08-25 빌드)으로 바꿔도 결과가 3.12.2 와 같았으므로(§8, T=4950 한 결정), 당시 판이 달랐더라도 이 차이의 주 원인일 가능성은 낮게 봅니다 [추론].
- 더 좁히는 env 시험(OpenBLAS 커널 이름, numpy 분기, numba 대상): codex PC CPU 를 몰라 고를 근거가 없어 하지 않았습니다.
- PYTHONHASHSEED 영향: codex 런은 설정 안 함, 우리는 규칙상 0 만. 시험 안 함.
- 대역 3개의 영향: env_hsw T=900 명령 일치로 그 결정에서는 영향이 없었다고 볼 뿐, 다른 결정은 모름.
- S1 의 순수 시간 몫: 빈 PC 한 쌍(T=900)만 잼. T=2700·4950 의 빈 PC 쌍은 없음. 같은 조건 반복도 한 번씩이라 ±수 s 흔들림은 가르지 못함.
- 빈 PC 배수: T=900 만 잼(2.31–2.33배). 가장 긴 결정 꼴(T=2400·2700)의 빈 PC 배수는 모름.
- 처음 다른 결정이 어디인가: 기록된 결정 55개 가운데 3개만 재생. env_hsw 로 T=900 은 같고 2700 은 다르므로 첫 차이는 1050–2700 사이 어딘가입니다(PRE_A1 §2 의 A0b 제안).
- 0.001 s 녹색 차이가 VISSIM 안에서 다른 상태를 만드는지: VBS 의 녹색 적용 해상도를 확인하지 않았습니다.
- W264 결정이 왜 joint 재생보다 길었는가: 설정 차(cap 캐시 없음) 외에 확인 안 함.

---

## 10. 산출물 sha256 [실행]

경로 기준: `work/` = `codex_handoff/work/`, `a0/` = `D:/VISSIM-merge/k8_gate_trees/codexhandoff/a0/`.

| 파일 | 바이트 | sha256 |
|---|---:|---|
| `work/a0/COMPARE_RULE_A0.md` | 3456 | `a05f20716f5b6056deb0783482523d52dd89c3a60dfc4be6b27609bc2047a634` |
| `work/a0/run_replay.ps1` | 7107 | `3765df238b5f144c2526040a7b1524256d1e43b7fe100a7d14bb6f81df1c773b` |
| `work/a0/run_replay2.ps1` | 7291 | `119bbd380a737dc58718c744fba0d8f33f43f84ee4657d274e9698cb9078dc2a` |
| `work/a0/run_speed_set2.ps1` | 2035 | `6831398973b101cda8fbafcd1659d22b0ca88d579176b057a18c0594840fb1f0` |
| `work/a0/run_queue2.ps1` | 2389 | `49d07c4cb462d4de054d53042ffb6aa1c41f85a685238a5461a46bd1309a9bb1` |
| `work/a0/run_queue3.ps1` | 1492 | `7467dc91f375b66ddeddd36ffcb1e83190742b1d8691ff70838fb175fd536d83` |
| `work/a0/run_compileall.ps1` | 851 | `840c5eebb1989feae2b53497875137860e1bff7aa0f55647daae34e67d697213` |
| `work/a0/launch_wmi_any.ps1` | 701 | `c528f66a712c62597ef1735dc2981880aecccfa291e308349fe63df11758c6eb` |
| `work/a0/s4_build_inputs.py` | 5045 | `72f7a5acdb2423cccfacde4f6ef8f163d7caee7327353e483461681dfea34e19` |
| `work/a0/s5_collect.py` | 1137 | `90b1a350f1c05f8f5aa3f39275d893a12af46b850da3aab53e718b3d0020dcb1` |
| `work/a0/s13_compare.py` | 5693 | `02aa1ee297cca2dd49e39b1b877f128ccf69f1133be9b2770f7d9c5ab002bba4` |
| `work/a0/s15_decision_times.py` | 1819 | `2412eeee7d5135d9dce66d09e002fa33d88194b59800f28b9122863fa86dbedc` |
| `work/a0/s20_cmdsummary.py` | 1326 | `7633c3d403885dd4b57ecad30cd22d51074fe286d22f5b4df7b6d963ea3c2852` |
| `work/a0/s21_summary.py` | 3220 | `e836d32cac0df049ecd2dab4ba18e8fe0413aec688d0bd79f57f37dcd93b0520` |
| `work/a0/s22_profile_all.py` | 7931 | `829e081ce5fe4458abb4bf7f6d7970f3c57d32c5e8869ee0b8782da5a037cac1` |
| `work/a0/s23_speedkeys.py` | 1536 | `b2590a508569888f3bc14cd08426ca992b8618df6e50be23a6f44d1ddae37cc7` |
| `work/a0/s24_tuning_variant.py` | 743 | `f59e1d2686e6ff51375882fc97be814a92897716eec16e356f5faceda521fa9f` |
| `work/a0/s25_make_tuning_runner.py` | 2015 | `a082368ebf3eb0021dd83c63ae37994b506280924d6be54a8c38f4dac153495a` |
| `work/a0/s26_tables.py` | 4810 | `43fdc100811d59854ff9bf9e201f1418d7390475ca3808491c6778cd2d6ba8e4` |
| `work/a0/s27_candidate_check.py` | 3231 | `d132d94cb2d70385f5f0bfbd0b1417706dddaddbcc6380b6f992fa7972318eb1` |
| `work/a0/s28_a1_estimate.py` | 3103 | `f45f56c940c62051d9b4de75a9f1c1663367da422c61eb9cbdc2705695d1b20f` |
| `work/a0/s29_progress_diff.py` | 2085 | `a856464879f9d104f9abc54aa8f3315336051f91be152a63df398aac1a9bcba8` |
| `work/a0/a0_summary.json` | 12662 | `df2450f39da8de72dac15257fdbd8c9117ae465164adb1aec8985785fdfeca8a` |
| `work/a0/prof_all_final.json` | 51649 | `af29aedfa0cb4d91eff4387c0bd1708342b438e4387c2fbb3912b1679e60bfd6` |
| `work/a0/prof_all_pre_spd.json` | 25653 | `0e0b7bf0f7061fbe223c772facecc330072568c00dd68d8e1fc820473a4f913e` |
| `work/a0/tables_final.md` | 10510 | `09a41e7f7d128fb41d55514dce173a34adf2e3b67864c3d90d31084bceaf56db` |
| `work/a0/a1_estimate.json` | 1338 | `ae72914aa0ba8c826f30f70a3c16f7bddf1f01fb7558683bcb76f5f4644d7943` |
| `work/a0/progress_first_diff.json` | 5517 | `63a417d3367e999945cd25e23b42d0a88ab5251e6fc240f83095849528d70a11` |
| `work/a0/speedkeys_ours_vs_codex.json` | 5652 | `3108b5840951ca65a9f9d33abe1f2b1d59d6fe18db9581f6125a27913beba65b` |
| `work/a0/decision_times.json` | 2524 | `6a013e8c1de0376928498b4d44b4845d2ef6330be1835a6986caf2f34153dc42` |
| `work/a0/speed_set2.state.txt` | 556 | `72e7e840d7fbea1924b943b92227b0aa35816e117f9873796ef9091deb493cee` |
| `work/a0/queue2.state.txt` | 510 | `66761f3d5322b8f2a6845b536e222f2844cfd866ef5a8916860ad75966f96442` |
| `work/a0/queue3.state.txt` | 310 | `b1b90ac016c959c243f46efe49354bbe5308e2e32f9635d574fc8c7c33f8c70d` |
| `work/a0/compileall.out.txt` | 217076 | `c387a8bf39b17e3ed5a61c6ec722f7668543c190e0d4091b9d189baf54a4ab6f` |
| `work/a0/compileall.state.txt` | 23 | `c672c95dd5a3d4ad7f7012875cf68bfcde9673fe37c02b68c13b76ec186b5942` |
| `a0/RESTORED_FILES.json` | 782214 | `184a26047350e0b8811eb31fdaafb013f82e52cc4d98c7c622a3b0fadcdb960f` |
| `a0/STANDIN_FILES.json` | 1969 | `c80839a9a5967860a3a49983607d6d6c2cf33f84a5feb5933769e852876167fb` |
| `a0/code/diagnostics/repin_v3c3_review_20261001/urban_rm269/aggregate270/native413_adopted355/optimized_config_t2390.json` | 287486 | `9365141f1e210d37a19049aa3b331fa114f054f1778241b6850b9e89a7285142` |
| `a0/out/base_rep2/T000900/candidate_vs_r900c_it01.json` | 1655 | `035df356e6ebfc2a6bf588ffc2439b1cef6dc8f44a61e4c1a0117a9b921eae56` |
| `a0/out/env_hsw_idle/T000900/candidate_vs_env_hsw.json` | 1655 | `b0d47aca8fa7742a509d1d94e5ae9548c4665e468eac8b7d0ac8a24ca6f45ef8` |
| `a0/out/py31214_base/T004950/candidate_vs_base.json` | 1654 | `349c8c11795a68d6ef756e4a424b31a9fa91543a15c16179fec3048e1bad291c` |
| `a0/out/py31214_hsw/T004950/candidate_vs_env_hsw.json` | 1656 | `a7fc16a63f6ed5a905d1419749b342462142351275004bbbc3c2c6760a816de2` |
| `a0/out/spd_base/T000900/candidate_vs_base_rep2.json` | 1653 | `98b79f18dcee8595a73b13e8d7aa4b696df316995e42912e7acc55e254abb0d1` |
| `a0/out/spd_hsw/T000900/candidate_vs_env_hsw.json` | 1650 | `22a739c5ca43011a43e20333cbd7ce610904d0380736141030d59e1a0fefe8c3` |
| `a0/out/spd_hsw/T002700/candidate_vs_env_hsw.json` | 1652 | `fdf1515b3b0609ebd86facb825d4bd275abe50ff92235d1b532bc53fc6072818` |
| `a0/out/spd_hsw/T004950/candidate_vs_env_hsw.json` | 1652 | `eef82e5c0ff4c5ae14b69e26ee684d68e0993bb3e509d724308dd4e8c3612754` |
| `a0/out/spd_hsw_idle/T000900/candidate_vs_env_hsw_idle.json` | 1660 | `2f647b01cd2bc8a92fc5157daa31b421da0a803bf74ec725fc723a093966be6d` |
| `a0/out/tmo2390_hsw/T000900/candidate_vs_env_hsw.json` | 4534 | `0db9a0557647edf683f9d8f665a07846625fe08a0a610058c5cb5dfb6cc3280a` |

- 재생 출력 폴더(`a0/out/<라벨>/T<T>/`: replay_state.json·stdout·stderr·cpu_load.csv·files/)는 라벨별로 남겼습니다. 라벨: base_cold_trace·…4(실패한 준비 재생), r900_it01·r900b_it01(준비 반복), r900c_it01, base_rep2, base, env_hsw, env_hsw_fail_applied, spd_hsw, spd_base, tmo2390_hsw, py31214_base, py31214_hsw, env_hsw_idle, spd_hsw_idle.
- 바이트코드 접두 캐시 `a0/pycache_prefix/`(compileall 224 s)는 코드 트리 밖입니다.
- 이 문서와 PRE_A1.md 의 sha256 은 LOG.md 와 반환값에 적습니다.
