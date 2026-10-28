---
name: vissim-sdmpc-native-state-20260923
description: "SDMPC 첫 native 폐루프 — 병합 트리 D:\\VISSIM-merge\\sim3, 발사 레시피·막혔던 결함 5개·결정 시간 505 s·첫 결정은 도시신호만"
metadata:
  node_type: memory
  type: project
  originSessionId: 491ef689-f002-4605-9dc5-e6d363495788
  modified: 2026-09-23T04:35:08.003Z
---

2026-09-23 SDMPC 가 **처음으로** native VISSIM 폐루프에서 결정을 완주했다. 그 전엔 오프라인
재생뿐이었다(controller 브랜치의 `lane_native_nc2850_s13_v3` 는 `controller = no-control`).

**트리**: `D:\VISSIM-merge\sim3` (00abbab plant + 5fdfabd controller 병합). 미커밋.

**발사 레시피** (`D:\VISSIM-merge\tools\run_sdmpc_laneplant.ps1`) — lane plant 가 sha256 으로
못박은 21셀 망을 써야 한다:
- `-Network` = lane-plant 워크트리의 `native_recording\baseline.inpx` + `-NetworkRecordingProof`
  (증명은 해시가 아니라 **절대경로 동일성**을 요구 → sim3 사본 못 씀)
- `-VbsConfig lane_native.vbs`, 게이트맵 **ver2**(legs4b 아님), 매핑 ver2n21
- tuning `config_candidate_obs1.json` (관측 간격 5→1, 아래 참조)
- env: RW_* 전부 비운 뒤 `RW_PYTHON` 과 `RW_OFFSET_WRITER=experiment` 만 세운다
  (워치독은 RW_* 를 상속만 하고 세우지 않는다)
- `-StallSec 2400`

**native 에서만 드러난 결함 (전부 수정)**:
1. SDMPC metadata 의 `ControlAction`/ndarray 를 JSON 이 못 씀 — 오프라인 하네스는
   `diagnostics/sdmpc_json_records.py` 를 거쳤지만 어댑터는 안 거쳤다. `_json_evidence` 를
   **결정 보고서(`finally` 블록, 제일 먼저 도는 writer)**·액션 JSON·joint_written 세 곳에.
   처음엔 액션 JSON 만 고쳐서 한 번 더 죽었다.
2. 관측 간격 5 s vs lane plant 의 매초 프레임 루프 → `KeyError: 2` at sim_sec=150.
3. 병합 스냅샷이 미추적 1,186개 + gitignore 된 `decisions_*` 핀을 놓쳤다.
4. `summarize_fast_nc.REFERENCE` 가 없는 런을 가리킴 → `--geometry-vbs` 추가.
5. 오늘 캡처된 요청 피클 대부분이 병합 전 plant (`hadi` 없음) — 병합 트리 것은
   `primal_angle/live_request.pickle` 등 2개뿐.

**결정 시간**: 900 s 결정 600.5 s → 504.7 s (중립 squeeze 3개 후). 목적함수
393.91612458424544 가 오프라인 아카이브·native·재현 모두 소수점 끝자리까지 같다.
상세 [[vissim-sdmpc-flags-rejected-not-unpromoted]] 와
`D:\VISSIM-merge\evidence\SQUEEZE_FINAL_20260923.md`.

**첫 결정(t=900)은 도시 신호만 썼다** — 미터 8개 전부 천장, VSL 44개 전부 120. 결정축
231 = green 138 + offset 51 + meter 24 + vsl 18. t=900 은 혼잡 전이라 합리적(native RM 도
1415~1925 s 에야 처음 차이를 냄). RM/VSL 판정은 9000 s 런(`sdmpc_lp_9000`)의 후반 결정으로.

**1050 s(첫 연속 결정)에서 죽었다 → 수정**: `lane_urban_runtime._debit_stock` 허용치가 현재
재고의 16 ULP 였는데 잔차는 재고의 **이력** 규모라 17 ULP 로 넘음. 1e-9 veh 바닥(5a86363).
어댑터는 오류 보고 후 **매달린다**(자식 없음) → watch_sdmpc.py 가 이제 `DECISION FAILED`·`STALL` 을
찍는다. 가격 상속(`sdmpc.py:505`)은 정상: 900 영수증 committed:true. 재발사 `sdmpc_lp_9000b` 13:32.
실패 런 폴더는 **이름 바꾸지 마라** — state_*.json 이 run_provenance 를 절대경로로 가리켜 재현이 깨진다.

**푸시**: `claude/sdmpc-native-20260923` @ e0164cc (Ming2you/VISSIM). 핀 입력은 `.gitattributes -text`
(이 PC 는 autocrlf=true 라 체크아웃 시 sha256 핀이 깨짐). 인수인계 README =
`diagnostics/sdmpc_native_20260923/README.md`. 50 MB 초과 33개·캐시·옛 미추적 1,154개는 제외.

**Why:** 다음 세션이 같은 함정(경로 증명·관측 간격·JSON·낡은 피클)을 하나씩 다시 밟지 않게.
**How to apply:** 새 SDMPC native 런은 위 스크립트를 복사해 쓰고, 결정 하나만 확인할 땐
`tools/replay_900.ps1` 처럼 저장된 state_*.json 으로 어댑터를 직접 부르는 오프라인 재현을
먼저 써라(60분 native 대신 10분). 21셀 lane plant 를 31셀 새 plant 로 재핀하는 건 미완
(핀 7개 중 lane_geometry·port_profile 재유도 필요). 관련 [[vissim-ramp-meter-actuation-is-binary]]

**⚠ SDMPC 네이티브 런은 전부 사용자의 기준 시나리오가 아니었다 (2026-09-23 16:00 확인).**
sdmpc_lp_v1/v2/9000/9000b/9000c 는 21셀 lane plant 시나리오(망 fcb349d3=4bad9195, **수요 100%**,
원래 출구 분할 1130/1131, seed 13, SimRes 1)에서 돌았다. 사용자 기준은 **FW80/U90**(86af2ac8,
both_off_half 분할, seed 23, SimRes 10)과 **31셀 METANET**(res10 boundary/Hadi/Wang). 물리 도로는
같다(링크·커넥터·DSD 동일). 09-22 02:08 에 "n21 은 최신 아님, 재핀 필요"라고 한 번 말하고 21셀로
동작 확인부터 한 게 그대로 유일 경로가 됐고, 요약에서 재핀 과제가 빠졌다.
- 31셀 = 21셀 부모 경계 보존 세분(램프 16곳을 각자 셀로, 최소 76 m). **차로군 없음·고속도로 전용**,
  램프는 관측 입력. lane plant 는 FW_E 셀5~14 차로군 + 도시·램프 결합. 서로 상위집합 아님.
- 31셀도 NOT_QUALIFIED(동측 회복 7건 놓침, RM/VSL 이득 부호 여전히 틀림).
- 전환은 "핀 5개 교체+2개 재유도"가 아니다: 31셀 geometry_profile 이 없고(refined_partition 만),
  load_sources·ver2n21 매핑·VSL 구역 머리·s23 차로 기하가 21셀 하드코딩. 그리고 lane plant 관측은
  SimRes 1 이 필수라 FW80/U90(SimRes 10) 을 그대로 못 쓴다 — SimRes 1 변형을 받아들여야 한다.
- 이날 RM 시드 비교(31/37/41)·omega TTT·오프라인 plant 분석은 **FW80/U90 맞다**.
