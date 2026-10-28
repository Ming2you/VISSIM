# COMPARE_RULE_B0 — B0 오프라인 결정 재생 선언 (2026-10-26 KST, 재생 데이터 전에 고정)

판정 낱말은 쓰지 않습니다. 재생 결과는 "코드가 v3c3 상태에서 결정 하나를 끝까지 도는가"와 "결정 시간"을 적는 일입니다.

## 1. 무엇을 돌리나 (VISSIM 0)

- 트리: `D:/VISSIM-merge/k8_gate_trees/codexhandoff/b0/code` (codex a49981ff + 복원 + 대역 + B0 재핀·코드 고침).
- 상태: 우리 V-A v3c3-s31 기록(`D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s31`, 읽기만). V-A 의 VSL 기록이 3,450 s 부터 101 을 담아 codex 의 VSL 노출 이력 검사(허용 50–110)를 못 지나므로 T ≤ 3,450 만 씁니다.
- 입력 꼴: `work/b0/b0_build_inputs.py` (기록 상태 + 기록 직전 명령, 사슬 아님). run_provenance 는 b0 워치독 `-PreflightOnly` 출력에서 만들고, run_id·name·망 경로·freeze 핀만 기록 상태에 맞춥니다(재생 장치 조정, B0.md 에 공개).
- 재생 셋, 이 순서, 한 번에 하나:
  - R1 = va_s31 T=3,450, B0 설정 `config_b0_v3c3.json`.
  - R2 = va_s31 T=3,450, `config_b0_v3c3_groupkeys.json` (R1 설정과 램프 도착 예측 객체 하나만 다름: codex 원래 그룹 키·strict 없음).
  - R3 = va_s31 T=1,800, B0 설정.
- 환경: env_hsw(OPENBLAS_CORETYPE=Haswell, NPY_DISABLE_CPU_FEATURES=AVX512F AVX512CD AVX512_SKX AVX512_CLX, NUMBA_CPU_NAME=haswell), PYTHONHASHSEED=0, OMP/OPENBLAS/MKL 스레드 1, python -B, WMI 분리 발사, BELOW_NORMAL.
- A1 보호: 재생 중 A1 의 진행 중 결정이 1,500 s 를 넘으면 그 재생의 내 PID 만 멈추고, 그 A1 결정이 끝난 뒤 같은 재생을 한 번 다시 돌립니다(라벨 `_r2`). 디스크 8 GB 미만이면 멈춥니다.

## 2. 무엇을 적나 (`b0_replay_summary.py`)

- 재생마다: 종료 코드, 예외 종류(있으면), 래퍼 벽시계, decision_budget wall·cpu, 진행 기록 줄 수, CPU 평균, 명령 CSV 행 수(kind 별), VSL 속도 집합, 미터 행, 램프 도착 예측 메타데이터, 유령 경로 별칭 언급 수, 유지(hold) 파일, 대역·도시 보정 파일 읽힘 여부(열기 기록).
- R1 대 R2: 명령 CSV 바이트 같음 여부, kind 별 다른 행 수, 숫자 칸별 최대 |차|, selection 스칼라(held/warm_start/selected objective 등) 두 값.
- V-A 의 기록 명령과는 비교하지 않습니다(다른 제어기). 결정 시간은 이 PC·이 env·A1 동시 실행 조건의 값으로만 적습니다.

## 3. 바꾸지 않음

- 이 선언과 도구(sha 는 LOG)는 데이터를 본 뒤 고치지 않습니다. 고칠 일이 생기면 새 판으로 따로 적고 "데이터 뒤 변경" 으로 밝힙니다.
