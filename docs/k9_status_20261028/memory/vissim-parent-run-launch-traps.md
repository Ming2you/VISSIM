---
name: vissim-parent-run-launch-traps
description: "VISSIM 부모런 발사 함정 — 게이트맵·StallSec·ControlStartSec·RW_ADAPTER_MODE·-Network 기본값, 그리고 config 의 백슬래시 경로가 JSON 에서 깨져 관측 없이 완주한다(2026-08-26 추가)"
metadata: 
  node_type: memory
  type: project
  originSessionId: ab16ebe2-114b-4182-9877-9977f80eb5f9
  modified: 2026-08-26T08:10:00.000Z
---

**발사 전에 기존 런의 `run_provenance_*.json` 을 열어 network sha·seed·period·
ControlStartSec 를 대조해라.** 기본값이 기준선과 같을 거라고 가정하지 마라 —
2026-08-22 에 이걸로 두 번 틀려 4시간 넘게 날렸다.

**`-Network` 기본값이 기준망이 아니다** (2026-08-22).
`run_real_world_single_watchdog_distributed_core17legs4b.ps1:86` 의 기본값은
`network/real_world_gaepo_modi/modi_eval_rw_control.inpx` (sha `f3ce390f`, **링크 1219**).
그런데 기준선 `nocontrol_native_20260821` · `mainline_on_20260821` 은
`modi_eval_userfix_20260814e.inpx` (sha `aff70f09`, **링크 1218**) 를 쓴다.
안 넘기면 조용히 다른 망으로 돌고 TTT 비교가 무효가 된다.
빠른 확인: 런로그의 `LINKS=` 가 **1218** 이어야 한다.

**`-ControlStartSec` 기본값 −1 은 워밍업 없음**이다. 기준선들은 **600** 을 명시로 받았다
(`WARMUP_CONTROLLER sim_sec=1·150·300·450` 네 줄이 그 증거). 안 넘기면 t=1 부터 제어해
워밍업 [0,600] 비트 동일이 깨지고, 첫 결정의 램프 미터링이 형식검사에 걸려
`ACTION_FORMAT_FAILURES=1` → 워치독이 3회 재시도 후 FAIL 한다(2h18m ×3 낭비).

**게이트맵 미지정 = 13.8% 조용한 오염.** `-UrbanInputGateMap` 기본값이 legs4b 라 보통 맞지만
런로그 `URBAN_GATE_ANCHOR_LOADED` 로 확인해라.

**StallSec 300** 은 수요 스케일링 중 kill 할 수 있다. 그리고 **런 도중 다른 무거운 작업을
같이 돌리지 마라** — 결정이 136초라 CPU 를 다투면 300초에 닿는다.

**`RW_ADAPTER_MODE` 누출** 주의.

**`-OutDir` 미지정이면** 산출물이 `evaluation/runs/real_world_modi_watchdog/` 로 간다.

**PowerShell `Start-Job` 으로 발사하지 마라** — PowerShell 툴 호출마다 세션이 새로 떠서
잡이 사라진다. 툴의 `run_in_background` 를 써라.

**config 의 윈도우 경로가 JSON 에서 조용히 깨진다** (2026-08-26, 92분 낭비).
tuning 에 `"evaluation\real_world..."` 처럼 백슬래시 한 개로 적으면
JSON 이 그것을 이스케이프로 먹는다 — `\r` 은 캐리지리턴이 되어 경로가
`evaluation<CR>eal_world...` 로 바뀐다. `load_optional_json` 은 없는 파일에 **빈 dict** 를
돌려주고, 어댑터는 `detector_mapping` 이 비면 관측 요약을 통째로 건너뛰고 그대로 결정한다.
map4etau_20260826 이 그렇게 **관측 없이 37번 결정하고 완주**했다(TTT 4806.7 = 무제어 4808.1).
진단의 `detector_mapping_effective` 는 **basename 만** 찍어 정상처럼 보였다.

  판별 한 줄: `local_observation_runtime_guard` 이 **1.0** 인가. 0.0 이면 눈감고 돈 것이다.
  그 다음: `projection_*` 키가 0개면 요약이 비었다는 뜻이다.

막는 자리는 **발사 전**이다 — 러너는 결정 실패를 세면서도 무제어로 완주하므로
어댑터 안의 가드로는 시간을 못 아낀다.

```bash
python scripts/preflight_tuning_paths.py <tuning.json>
```
extends 사슬을 병합해 유효값 기준으로 제어문자와 파일존재를 본다. leaf 가 직접 쓴 키만
FAIL, 조상만 가진 죽은 키(어댑터가 안 읽는 `calibration_json` 등)는 WARN.
`scripts/launch_map4e_20260826.ps1` 에 박아뒀다.

**같은 부류: 도구로 파일을 쓸 때 백슬래시가 접힌다.** heredoc 으로 파이썬을 넘기면
`\\n` 이 `\n` 으로 한 번 더 접혀 같은 사고가 난다. 하루에 **세 번** 걸렸다
(config 경로 · 어댑터 주석 · 발사기 경로). 소스에 백슬래시를 쓰지 말고 `chr(92)` 나
슬래시를 써라 — PowerShell 도 파이썬도 슬래시 경로를 받는다.

**PowerShell 5.1 은 BOM 없는 UTF-8 을 CP949 로 읽는다.** 파이썬으로 `.ps1` 을 고쳐 쓰면
BOM 이 날아가 한글 문자열이 깨지고 `The string is missing the terminator` 로 파싱이 실패한다.
`encoding='utf-8-sig'` 로 써라. 정본 러너는 BOM 이 있다.

발사 직후 `LINKS=` · `WARMUP_CONTROLLER` · provenance sha 를 확인하는 감시를 같이 걸어
2시간 뒤가 아니라 1분 뒤에 오발사를 잡아라.

관련: [[vissim-execution-gotcha]] [[vissim-watchdog-policy]] [[vissim-workstation-state]]
