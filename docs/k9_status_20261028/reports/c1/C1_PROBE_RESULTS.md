# C1 미니 탐침 결과 (탐침, 판정 아님) — 2026-10-27 KST

- 기록 판: `C1D/C1_PROBE_RESULTS.json` sha256 `5b0bcfb05246cc7099929c03b806ba4cb03a5cbc39c5e9de3bd0dcbde80a0b5a` (고정 도구 `c1_probe.py` `9446f028…` 의 `report` 단계, PINS_PROBE `5dfb83b1…`).
- 자세한 설명·질문은 `C1D/P0_PROBE.md` r2 §4–§6 에 있습니다. 이 쪽은 보충 C1 §5.4 가 이름 붙인 짧은 요약입니다.
- C1D = `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/c_port/c1`, TC1 = `D:/VISSIM-merge/k8_gate_trees/c1`.

## 돈 것 [실행]

| 항목 | 상태 |
|---|---|
| plant v3c3-s31 T=1,500 × {OFF, Ω, H} | 세 잡 끝남(ok, 기록기 오류 0) |
| plant 나머지 15상태 | 돌리지 않음 (HALT) |
| 결정 35 (5상태 × 7팔) | 돌리지 않음 (HALT) |

## plant v3c3-s31 T=1,500 [실행]

| 팔 | 모형 목적(veh·h, 그 팔의 Ω) | OUTW 450 s (veh·h) | 궤적(행별 `model_stock_veh`) = OFF |
|---|---|---|---|
| OFF (Ω635) | 434.995 | 861.539 | — |
| Ω (Ω701) | 504.165 | 792.620 | 다름: 82/638키, 22,144칸, 첫 행(t_end 1,501 s)부터 |
| H | 434.995 | 861.539 | 같음 (900 × 638 비트 같음) |

- 첫 행 차이: `storage:SC106_to_SC12` +1.0대, `storage:SC2005_to_SC101` +0.5대, `storage:SC101_to_SC1002` −0.5대. Ω701 지지 문서의 더한 커넥터 `link_to_storage`(29개 가운데 3개 → SC106_to_SC12, 6개 → SC2005_to_SC101)가 초기 재고 투영을 바꾼 것으로 봅니다 [추론].

## 멈춤 규칙 (보충 C1 §5.4)

| 규칙 | 결과 |
|---|---|
| 1 예외·장부·불변식 위반 | 0건 |
| 2 Ω·H plant 궤적 ≠ OFF | **걸림** (Ω) → S-C1-3 구현 전 STOP·질문 |
| 3 M·C1 조임 없음 | 셈 못 함 (결정 0) |
| 4 C1 결정 벽시계 중앙 > 1,500 s | 셈 못 함 (결정 0) |
| INCOMPLETE | 50항목 (HALT 로 돌리지 않음) |
