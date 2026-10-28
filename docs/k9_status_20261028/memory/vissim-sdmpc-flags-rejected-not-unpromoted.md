---
name: vissim-sdmpc-flags-rejected-not-unpromoted
description: config 에 없는 adapter.sdmpc_* 고속경로 5개는 미승격이 아니라 속도로 기각된 것 — 제안 전에 diagnostics/ 의 기각 영수증부터 찾아라
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 491ef689-f002-4605-9dc5-e6d363495788
  modified: 2026-09-22T18:48:57.384Z
---

`diagnostics/sdmpc_pfo_caps_20260922/config_candidate.json` 에 **없는**
`adapter.sdmpc_*` 플래그 다섯은 "만들어놓고 안 켠 것"이 아니다. 전부 **수치 동등성을
통과한 뒤 속도에서 기각**됐고, 각 폴더에 영수증이 있다 (2026-09-23 확인):

| 플래그 | 전체 결정 | 기록 |
|---|---|---|
| `sdmpc_persistent_urban_fifo` | 386.693 → 444.002 s | `NOT_SELECTED_FOR_SPEED` |
| `sdmpc_array_urban_pipeline` | 386.693 → 426.879 s | `selected_for_speed: false` |
| `sdmpc_flow_update_cache` | 386.693 → 387.376 s | "improvement not demonstrated" |
| `sdmpc_array_transport` | jacobian 143.419 → 146.886 s | `NOT_SELECTED_FOR_SPEED` |
| `sdmpc_spatial_receiving` | 143.419 → 150.297 s | `NOT_SELECTED_FOR_SPEED` |

**기구**: numba pack/unpack 경계 비용이 커널 이득보다 크다. `array_transport` 의 커널은
테이프 노드의 **0.45%** 만 덮고(`compiled_node_fraction: 0.004459`), 파이프라인 블록은
13.5 s 중 커널이 2.7 s 뿐이고 나머지 80% 가 811,550 입력 패킹이다.

같이 확인된 것(같은 날, 같은 조사):
- **numba 스레드는 막혀 있지 않다.** `OMP_NUM_THREADS=1` 을 세워도 prange 탐침이 7.4배
  확장하고, `NUMBA_NUM_THREADS` 는 어디에도 안 세워져 기본 20 이다. 유일한
  `set_num_threads` 는 기각된 spatial 안에 있다. OMP/MKL 해제는 이득 0 이고 BLAS
  축약 순서를 바꿔 **결정을 실제로 움직일 수 있는 유일한 변경**이므로 하지 마라.
- `sdmpc_derivative_workers` 는 8 에 **동결**이다(`sdmpc.py:178/:193/:196` 가
  surrogate_reuse·trial_derivative_overlap·spatial_receiving 에 8 을 요구하고,
  surrogate_reuse 는 `:186` 에서 central_multiplier 가 요구한다).
- 역방향 스윕은 8 이 이미 최적이고 1→8 전 구간이 120 s 롤아웃에서 0.3 s 다(영수증 77개).

**Why:** 나는 "개발 기록 디렉터리가 통째로 있는데 config 에 없다 → 승격을 잊었다" 로
읽고 사용자에게 그렇게 보고했다가 틀렸다. 이 프로젝트에는 측정하고 기각한 것을 지우지
않고 남겨두는 습관이 있어서, 남아 있는 것과 채택된 것이 겉보기로 구분되지 않는다.

**How to apply:** 속도 개선을 제안하기 전에 `diagnostics/<그 기능>/` 의
`qualification_summary.json` · `connection_summary.json` · `performance_summary.json` ·
`finalize_*.log` · `docs/SDMPC_*.md` 에서 **기각 기록을 먼저 찾아라.** 기각된 아이디어를
다시 발견하는 것이 이 코드베이스에서 가장 흔한 실패다. 하위 에이전트를 쓸 때도 이걸
최우선 지시로 줘라. 관련: [[vissim-gate-outside-config-is-dead]],
[[vissim-supersede-dont-flag]], [[vissim-metering-lever-structurally-dead]]
