# A0b 대조 선언 (첫 A0b 재생 전에 고정, 2026-10-25 KST)

- 대조 규칙: A0-CMP-1 그대로(`work/a0/COMPARE_RULE_A0.md`, sha256 a05f20716f5b6056deb0783482523d52dd89c3a60dfc4be6b27609bc2047a634). 고치지 않음.
- 대상: codex 64cf-s29 joint 런 기록 결정 T = 1050, 1200, 1350, 1500, 1650, 1800, 1950, 2100, 2250, 2400, 2550 (11개, 한 런·한 시드).
- 입력: `work/a0/s4_build_inputs.py`(바꾸지 않음)로 만든 `a0/pristine/T<T>`. 각 결정은 기록 상태 `state_T.json` 과 기록 직전 명령 `action_<T-150>.json/.csv/.json.applied` 에서 시작. 앞 재생의 출력은 쓰지 않음(사슬 아님).
- 환경: env_hsw(`OPENBLAS_CORETYPE=Haswell`, `NPY_DISABLE_CPU_FEATURES=AVX512F AVX512CD AVX512_SKX AVX512_CLX`, `NUMBA_CPU_NAME=haswell`) + `run_replay2.ps1`(바꾸지 않음)의 고정 env(PYTHONHASHSEED=0, OMP/OPENBLAS/MKL 스레드 1, RW_* 기록값, `python -B`). S1 안 넣음. 라벨 `a0b_hsw`. WMI 분리 발사, BELOW_NORMAL, 한 번에 하나.
- 결정마다 적는 것:
  1. R1(명령 CSV sha), R2(일곱 필드 다섯 칸), R3(채점 토큰) — `work/a0/s13_compare.py`(바꾸지 않음). R4 잎 비교는 부류별 개수만 적음(해시 잎 사슬 설명은 하지 않음).
  2. 다른 명령 행 목록과 크기 — `work/a0b/a0b_rows.py`: 파일 순서로 짝지은 행, 식별 칸(kind·id·dsd_no·sc_no·link·lane) 확인, 다른 칸마다 재생값·기록값·차. 종류별 행 수, 종류·칸별 최대 |차|, 이산 차 세 가지(신호 녹색 차 ≥ 1 s, 미터 rate_vph·green_sec 차, VSL speed_kph 차). 보조로 `work/a0/s20_cmdsummary.py`(바꾸지 않음).
  3. 진행 기록 첫 차이 — `a0b_summary.py` 안의 함수(`s29_progress_diff.py` 와 같은 시계 칸 정규식). 1부터 센 줄 번호와 0부터 센 번호를 함께 적음.
  4. 작업 수(요청·캐시 적중·스칼라·tangent 롤아웃, tangent 미분 수)와 기록의 같은 수.
  5. 시간: 재생 `decision_budget.json /wall_sec` 대 기록 같은 칸(주 비교), 재생 프로세스 벽시계(`replay_state.json wall_sec`) 대 codex runlog `CONTROLLER_DECISION wall_sec`(보조). 배수 = 재생/codex. CPU 부하(typeperf 5 s 평균).
- "처음 다른 T": T 오름차순으로 R1 이 다른 첫 T. 다른 행이 0 인데 R1 만 다르면(예: metadata 칸) 따로 적음.
- 판정 낱말 없음. 차이는 결과이며 실패가 아님. 재생이 돌지 못한 결정(종료 코드 ≠ 0, 명령 CSV 없음)만 "재생 실패" 로 적음.
- 이 선언과 도구 sha 는 LOG.md 에 첫 재생 전에 적음. 데이터를 본 뒤 고치지 않음.
