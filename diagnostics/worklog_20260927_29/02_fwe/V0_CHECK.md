# V0 (b) 확인 재생 (P0 보고 Q15, 2026-09-27)

## 설정
- 튜닝: `config_n31_v2_v0.json` (sha 1e15aef5)
  - 886a014 의 `config_n31_v2.json` 사본입니다.
  - `config_overrides.freeway_follower.max_vsl_step` 을 40 에서 0 으로 바꿨습니다. 바꾼 것은 이것 하나입니다.
- 재생 대상: S0e(`sdmpc31_v3b_s31e`) 900 s 결정
  - 코드는 동결 트리 `sdmpc31_886a014a_202609260935` 입니다.
  - 도구는 `xreplay/alt_replay.ps1` 이고, 같은 결정을 두 번(r900_a, r900_b) 재생했습니다. 각 525 s, 538 s 걸렸고 BELOW_NORMAL 로 돌렸습니다.

## 결과 [실행]
- 예외는 없었습니다. 두 번 모두 exit 0, `controller_status` ok, `selection_status` best_observed_feasible_sdmpc 입니다.
- **VSL 명령이 전부 110 입니다.** 동측 34행, 서측 32행입니다.
  - 원래 S0e 900 결정은 동측 8행이 100 이었습니다.
- **결과가 결정적입니다.** r900_a 와 r900_b 의 `action_000900.csv` 가 바이트까지 같고, green_times 와 offsets 도 같습니다.
- 원래 결정과 비교하면 녹색의 L1 차이 합이 8.30 s 입니다. 미터는 모두 900(열림)으로 같습니다.

## 판정
- V0 경로 (b) 를 쓸 수 있습니다.
  - 조건: 900 s 에 VSL 110 으로 시작하는 새 런에만 씁니다. 기준값 a 가 직전 확정 행동이기 때문입니다.
  - 폭이 0 인 VSL 축으로도 SDMPC 가 정상적으로 결정을 냅니다.
- 한계: 이 확인은 결정 하나만 봤습니다. 9000 s 전체 런에서는 폐루프를 발사할 때 확인합니다.
