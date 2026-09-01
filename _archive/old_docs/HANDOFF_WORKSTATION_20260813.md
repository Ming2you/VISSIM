# 워크스테이션 인수인계 — 2026-08-13

성능 좋은 전용 기계로 옮겨서 이어갈 작업 안내다. 이 문서 하나만 보고 진행할 수 있게 적었다.

## 0. 지금 어디까지 왔나

**플랜트 배선은 끝났고, 작동 증명은 아직이다.** 이 둘을 구분해야 한다.

모든 층이 같은 망(`modi_eval_rw_control_n4dr150_20260812.inpx`)과 같은 4현시 어휘를 가리킨다.
그런데 **모델과 플랜트를 붙여 결정 한 번도 끝까지 돌린 적이 없다.**

| 항목 | 상태 | 근거 |
| --- | --- | --- |
| `.sig` 15개 150 s dual-ring | 완료 | VISSIM 실측 15 SC 전부 150 s |
| inpx 재배선 | 완료 | `LOAD_OK`, checkSum 거절 없음 |
| leg 방위 교정 | 완료 | 물리 방위와 일치 (W · SW) |
| movement 4현시 | 완료 | 698 중 511 이동 |
| map · 계획 정본 승격 | 완료 | 4현시 {4현시 12 SC, 3현시 3 SC} |
| SC별 녹색 예산 유도 | 완료 | 실측 녹색과 14/15 일치 |
| 살아 있는 현시 집합 배선 | **미검증** | 마지막 한 줄 수정 후 런을 못 돌림 |
| 커플드 런 완주 | **미완** | 결정 1회가 52분, 완주 이력 없음 |

## 1. 받을 것

```
VISSIM     origin/codex/plant-fidelity-v2-1   49e26ed   (이 문서를 담은 커밋)
NumSim     origin/freeway-zone-followers      0546d76
```

NumSim 은 **VISSIM 저장소의 형제 디렉터리 `NumSim-mine` 으로** 받는다. 이름과 위치가 고정이다 —
`scripts/tests/test_update_numsim_snapshot.py:21` 이 `REPO.parent / "NumSim-mine"` 을 본다.

```bash
git clone --branch freeway-zone-followers https://github.com/Ming2you/Numerical-Sim.git ../NumSim-mine
```

`vendor/NumSim-mine` 은 VISSIM 저장소 안의 스냅샷이라 그것 자체를 따로 받을 필요는 없다. 다만
상류를 고칠 때는 반드시 **상류에서 고치고 스냅샷 스크립트로 옮긴다**(직접 편집 금지, 4절 참조).

상류를 안 받으면 `test_upstream_sources_include_non_python_config` 가 실패한다. 이 검사만은
상류 부재를 skip 으로 처리하지 않는다(형제 검사
`test_vendor_config_matches_upstream_byte_for_byte` 는 skip 한다). **2026-08-13 실측.**

## 2. 받자마자 할 것 — 이걸 안 하면 전부 FAIL 한다

### 2-0. 줄바꿈(EOL) 정렬 — 2-1 보다 먼저 한다

**이 저장소는 워킹트리 줄바꿈이 섞여 있어야 맞는다.** git 이 체크아웃한 파일은 CRLF, 세션 중
파이썬이 직접 쓴 산출물은 LF 다. 봉인된 해시들이 그 혼합 상태를 가리키므로 **어느 한쪽으로
통일하면 검사가 깨진다.** 새 기계에서 클론하면 `git status` 는 깨끗한데 검사만 더 실패한다.

**2026-08-13 이관 실측.** `core.autocrlf=true`(Windows 기본) 로 클론했을 때:

| 파일 | 원 기계 워킹트리 | git blob | 봉인한 쪽 |
| --- | --- | --- | --- |
| `outputs/signal_group_actuation_plan_v3.json` | LF `5955cc18…` 52,214 B | 같음 | `_sgplan.vbs` 4개가 LF 를 봉인 |
| `evaluation/generated/*_sgplan.vbs` (4개) | LF 3,978 B | 같음 | 렌더 결과와 바이트 대조 |
| `network/…/modi_eval_rw_control_n4dr150_20260812.inpx` | CRLF `37f1cc1f…` 3,029,984 B | LF `da352bf3…` 2,995,729 B | 계획이 **CRLF** 를 봉인 |
| `outputs/movement_signal_group_map_v3.json` | CRLF `c937648b…` 73,624 B | LF `312b4dc8…` 70,844 B | 계획이 **CRLF** 를 봉인 |

`core.autocrlf` 는 **true 로 두고**, 그 위에서 파이썬 산출물 5개만 LF 로 되돌린다.

```bash
git config core.autocrlf true
python - <<'PY'
import pathlib
targets = [pathlib.Path("outputs/signal_group_actuation_plan_v3.json")]
targets += sorted(pathlib.Path("evaluation/generated").glob("*_sgplan.vbs"))
for p in targets:
    p.write_bytes(p.read_bytes().replace(b"\r\n", b"\n"))
    print(p, p.stat().st_size)
PY
```

**전체를 LF 로 통일하지 말 것.** 실제로 해 봤다 — `_sgplan.vbs` 5건은 낫지만 계획이 봉인한
`.inpx`·movement map 이 어긋나 `test_model_plant_native_share_identity` 2건이 새로 깨진다.
`tests/` 실패가 12 → 9 로 바뀌었을 뿐 7 이 되지 않았다.

**이 조치는 영구적이지 않다.** git 이 그 파일들을 다시 건드리면 CRLF 로 되돌아간다.
`git status` 가 ` M` 으로 표시해도 내용 차이가 아니다 — `git hash-object` 가 HEAD blob 과
같으면 EOL 부기일 뿐이다. `checkout`·`reset`·`stash` 뒤에는 위 블록을 다시 돌린다.

근본 해결은 `.gitattributes` 로 이 파일들의 EOL 을 고정하고 계획·vbs 를 함께 재생성하는
것이다. 생산 산출물을 덮는 일이라 이번에는 하지 않았다.

### 2-1. 정본 토폴로지 재생성 (필수)

`outputs/canonical_topology_v3.json` 은 `.gitignore:41` 대상이라 **푸시에 안 담긴다.**
새 기계에는 없거나 구판이다.

**`--inpx` 는 절대경로로 준다.** 이 스크립트는 컴파일러를 `cwd=plant` 로 띄우는데
(`build_canonical_topology.py:98-100`) 상대경로가 그 안에서 풀려
`plant\network\…` 를 찾다 `FileNotFoundError` 로 죽는다.

```powershell
$inpx = (Resolve-Path "network\real_world_gaepo_modi\modi_eval_rw_control_n4dr150_20260812.inpx").Path
python scripts/build_canonical_topology.py --inpx $inpx
```

기대 출력 — `signal_controllers=50 signal_groups=440 observation_operators=479`,
`inpx_sha256=37f1cc1f…`(2-0 의 CRLF 판). 약 25 s 걸린다.

안 하면 감사가 `canonical topology was compiled from a different .inpx than the audited
network` 로 FAIL 한다.

### 2-2. 환경변수

```bash
RW_PYTHON_EXE=<python.exe 절대경로>
```

승인 사슬(`verify_runtime_source.py`)이 이 값을 검사한다. 없으면 `python.executable_matches`
가 FAIL 한다.

VISSIM 2020 COM 등록도 필요하다 (`Vissim.Vissim` ProgID).

### 2-3. 상태 확인

```bash
python scripts/verify_runtime_source.py --out outputs/runtime_source_v2_1.json
python scripts/build_preflight_manifest.py --repo . --runtime-source outputs/runtime_source_v2_1.json --out outputs/preflight_manifest_v3.json
```

둘 다 `status: PASS` 여야 한다. **지문은 기계 간 비교 기준이 못 된다** — 지문 입력에
저장소 절대경로와 `python.exe` 바이너리 해시가 들어가서, 기계가 바뀌면 반드시 달라진다.
문서 초판이 적었던 `b36a6b8c…` 는 원 기계(`C:\Users\alsrj\…`, Python 3.13.5) 전용 값이다.
이관 기계에서는 `58f39377…` 이 나왔고 차이 161건을 전부 분류했더니 경로 126 · 파이썬 10 ·
지문 2 · 그 둘의 파생 23 이었다. **볼 것은 `status: PASS` 다.**

검사 스위트도 확인한다.

```bash
python -m unittest $(ls tests/test_*.py | sed 's|/|.|;s|\.py$||')
python -m unittest $(ls scripts/tests/test_*.py | sed 's|/|.|g;s|\.py$||')
```

기대값 — `tests/` 209개 중 **7 실패**(전부 수요 계약, 아래 6절, skip 5),
`scripts/tests` 643개 중 **8 실패**(skip 12, 약 16분).

**`scripts/tests` 8건은 원 기계에서만 통과한다.** 문서 초판의 "643개 전부 통과" 는
원 기계 한정 값이었다. `test_wrapper_network_wiring` 의
`test_every_wrapper_opens_the_network_its_artifacts_came_from` 이 옛 wrapper 8개에서 깨진다.
wrapper 는 죄가 없다 — 망을 `Join-Path $repo` 로 상대 참조한다. 원인은 짝이 되는
`player_config_*.json` 의 `source_files.network_inpx` 가 **원 기계 절대경로**
(`C:/Users/alsrj/Desktop/학술/찐찐막/Claude/VISSIM/…`)를 기록해 둔 것이고,
검사의 `_repo_relative()` 가 다른 기계에서는 그 접두사를 못 떼기 때문이다.

생성기는 그 뒤 고쳐졌다. 상대경로를 기록한 최신 4개는 통과한다 — `core15n41_20260805`,
`core15n41gated/ungated_20260811`, **`core15n41legfix_20260812`**. 즉 **5절에서 실제로 쓸
wrapper 는 깨끗하다.** 옛 8개는 이번 작업과 무관하므로 산출물을 덮어 고치지 않았다.

이 숫자와 다르면 2-0 이나 2-1 을 안 했거나 상류(`../NumSim-mine`)를 안 받은 것이다.
`scripts/tests` 전량은 약 17분 걸린다.

## 3. 첫 작업 — 병렬 백엔드 켜고 solve 시간 재기

### 왜 이게 첫 번째인가

결정 1회에 **약 52분**이 걸린다(실측: 12:47:14 → 13:39:15). 180 초 시뮬에 결정 3회면 2시간 반,
1시간 시뮬이면 52시간이다. 이게 줄지 않으면 나머지 작업이 전부 비현실적이다.

그런데 병렬 경로가 있는데 꺼져 있다.

```
mpc.grid_parallel_backend      serial     ← 여기
mpc.grid_parallel_max_workers  8          ← 워커 8개가 놀고 있다
mpc.grid_reuse_process_pool    true
mpc.grid_parallel_min_items    2
mpc.grid_parallel_chunk_size   8
```

허용값은 `serial | thread | process` 다(`src/models/state.py:904`). 클래스 기본값은 `thread`
인데 `src/config/default.yaml:249` 가 `serial` 로 덮고 있다.

### 어떻게 켜나

**vendor 를 직접 고치지 말 것.** config override 로 켠다. `evaluation/configs/` 에 새 config 을
만들고 부모를 legfix 로 둔다(원본은 안 덮는다).

```json
{
  "extends": "real_world_modi_pstack_distributed_core15n41legfix_20260812.json",
  "name": "real_world_modi_pstack_distributed_core15n41legfix_par_20260813",
  "description": "legfix 위에 병렬 백엔드만 켠다. 다른 필드는 부모와 같다.",
  "config_overrides": {
    "mpc": { "grid_parallel_backend": "thread" }
  }
}
```

`thread` 와 `process` 를 둘 다 재보는 것이 좋다. GIL 때문에 순수 파이썬 연산이면 `thread` 가
효과 없을 수 있고, `process` 는 직렬화 비용이 붙는다. **재보기 전에는 어느 쪽이 빠른지 모른다.**

### solve 시간 재는 법 (런 없이, 가장 싸다)

VISSIM 을 띄우지 않고 결정 한 번만 직접 호출한다. 이미 캡처된 상태 파일을 쓴다.

```bash
python evaluation/controllers/vissim_stackelberg_adapter.py \
  --state-json outputs/solve_timing_fixture_state_n4dr150_20260813.json \
  --out-action-json <임시>/action.json \
  --out-action-csv  <임시>/action.csv \
  --mapping-json    evaluation/real_world_modi_control_distributed_20260728/control_mapping_distributed_core15n41legfix_20260812.json \
  --detector-mapping-json evaluation/real_world_modi_control_distributed_20260728/detector_local_mapping_distributed_core15n41legfix_20260812.json \
  --calibration-json evaluation/calibration/real_world_prediction_calibration_pshb4500fix_20260724.json \
  --tuning-json     <위에서 만든 병렬 config> \
  --controller stackelberg
```

시작·종료 시각을 찍어 52분과 비교한다. **이 한 번으로 병렬화 효과가 나온다.**

이 상태 파일은 2026-08-13 커플드 런의 `sim_sec=1` 상태를 그대로 옮겨 둔 것이다. 원본은
`evaluation/runs/` 아래에 있는데 그 경로가 `.gitignore:6` 대상이라 전송되지 않는다. 그래서
`outputs/` 로 복사해 커밋했다 — **52분 측정과 같은 입력**이므로 비교가 성립한다.

### 병렬이 효과 없으면

다음 순서로 재본다. 각각 결정 1회 측정이다.

1. `mpc.leader_candidate_count` 9 → 5 (리더 후보 축소)
2. `mpc.horizon_steps` 3 → 2 (수평선 축소)
3. `mpc.follower_solver_mode` 를 바꿔본다

**어느 것도 그냥 바꾸지 말고 목적함수 값이 얼마나 나빠지는지 같이 기록한다.** 속도만 보고
줄이면 제어 품질이 조용히 나빠진다.

## 4. 두 번째 작업 — 현시 배정 수정이 실제로 통했는지 확인

### 무슨 일이 있었나

짝지은 런이 52분짜리 solve 끝에 이 오류로 죽었다.

```
SignalGroupPlanError: sc 107: action commands green on phases ('p1','p2','p3','p4')
                      but the actuation plan has signal groups on ('p2','p3','p4')
```

SC107·108·109 는 한 현시의 신호군이 `.sig` 에서 영구적색이라 플랜트가 3현시로 돈다. 모델이
죽은 현시에 녹색을 주면 그 시간이 전현시 적색으로 흘러간다.

두 번 고쳤다.

- `6bc3fd9` — `live_phases_by_signal` 집합 + 배분 함수 둘에 `signal` 개방
- `0546d76` — **`set_signal_green` 에도 `signal` 전달** ← 실 제어 경로가 여기였다

두 번째가 핵심이다. 첫 수정 후에도 같은 오류로 죽었는데, 분산 코디네이터가
`allocate_phase_green`/`distribute_phase_green` 이 아니라 `set_signal_green` 으로만 녹색을
쓰기 때문이었다(`distributed_coordinator.py:1260, 1312, 1393, 1415`).

### 확인 방법

3절의 결정 호출이 **예외 없이 끝나면** 통한 것이다. 죽으면 오류 메시지의 SC 번호를 보고
같은 종류의 경로가 하나 더 남은 것인지 본다.

배선 자체는 이미 확인됐다(참고).

```
live_phases_by_signal 항목수: 15
SC107 -> ['p2', 'p3', 'p4']
SC1   -> ['p1', 'p2', 'p3', 'p4']
```

## 5. 세 번째 작업 — 커플드 런 완주

```bash
scripts/run_real_world_single_watchdog_distributed_core15n41legfix.ps1 \
  -Name <이름> -SimPeriod 180 -ControlIntervalSec 60 -Seed 13 \
  -UrbanInputGateMap evaluation/real_world_modi_inventory/urban_input_gate_map_legfix_20260813.csv \
  -StallSec 3600
```

**두 인자가 핵심이다.**

- `-UrbanInputGateMap` 없으면 `urban_volume_vph_by_gate has gates the model does not know:
  in_SC1001_W` 로 죽는다. leg 방위를 고치며 SC1001 의 W 가 격자 leg 이 되어 경계 게이트가
  아니게 됐는데 러너 기본 맵이 아직 옛 판이다(`run_real_world_stackelberg_controller.vbs:4630`).
  기본값은 일부러 안 옮겼다 — 구 배선 런이 깨지기 때문이다.
- `-StallSec` 기본값 300 은 52분 solve 를 못 견딘다. 병렬화로 빨라지면 낮춰도 된다.

### 완주하면 확인할 것

`runlog_<이름>.txt` 끝에서 본다.

```
SIGNAL_SG_PLAN_ROWS      > 0 이어야 한다 (지금까지 0 이었다 — 결정이 죽어서)
DECISIONS_OK             > 0
DECISIONS_FAILED         0
ACTION_FORMAT_FAILURES   0
```

신호 쓰기 경로는 이미 건강한 것이 확인됐다(참고 — 죽기 전까지의 실측).

```
SIGNAL_WRITE_ATTEMPTS=296  SIGNAL_READBACK_OK=296  SIGNAL_FAILURES=0
SIGNAL_PERSISTENCE_OK=288  COM_FAILURES=0
SIGNAL_SG_PLAN_ENABLED=1   SG_PLAN_GROUPS=136
URBAN_GATE_ANCHOR_LOADED   mapped_inputs=18
```

완주하면 러너가 합성한 주기가 150 인지, SC107·108·109 가 3현시로 재생되는지도 같이 본다.

## 6. 네 번째 작업 — 수요 계약 7건

이 세션에서 한 번도 손대지 않은 영역이다.

```
6건  tests/test_demand_contract.py  test_urban_boundary_total_equals_plant_entry_total_each_interval
1건  tests/test_demand_contract.py  test_every_vissim_urban_entry_has_a_model_gate
```

계약 문서는 `evaluation/controllers/demand_contract.md` 다. 게이트 맵을 새로 유도했으므로
(`urban_input_gate_map_legfix_20260813.csv`, 게이트 19 → 18) 그 영향을 먼저 봐야 할 수 있다.

## 7. 규칙 — 지키지 않으면 되돌리기 어려워진다

- **`git add -A` 금지.** VISSIM 미추적 12개, NumSim 미추적 3개가 보존 대상이다. 파일을 명시해서 add 한다.
- **`vendor/` 직접 편집 금지.** 상류(`../NumSim-mine`)에서 고치고 옮긴다.

  ```bash
  python scripts/update_numsim_snapshot.py --workspace-root . --upstream ../NumSim-mine
  ```

- **스냅샷과 앵커는 같은 커밋에 넣는다.** 스냅샷은 `scripts/verify_runtime_source.py` 등 3개
  파일의 앵커 상수 11개를 같이 갱신한다. 따로 커밋하면 다른 체크아웃에서 사슬이 FAIL 한다.
  (이 세션에서 실제로 겪었다 — `fde3b01`.)
- **원본 덮어쓰기 금지.** 원 `.sig`, 원 inpx, 생산 config, `reports/`. 새 파일로 낸다.
- **`scripts/inventory_real_world_modi.py` 주의.** `--out-dir` 을 줘도
  `outputs/real_world_modi_player_definition_{json,md}` 는 생산 경로에 쓴다. 임시로 인벤토리를
  뽑을 때 그 둘이 오염된다. 돌린 뒤 `git status` 로 확인할 것.
- **`signal_controller_roles.csv` 의 `active` 열은 큐레이션 값이다.** inpx 원속성이 아니라
  "모델 컨트롤러인가" 를 담는다. 인벤토리를 통째로 재생성하면 그 의미가 지워지고
  `signal_roles.active_scope` 가 깨진다. 망이 바뀌면 `supplyFile2` 만 옮긴 망별 CSV 를 따로 둔다
  (`signal_controller_roles_n4dr150_20260812.csv` 가 그 예다).

## 8. 미해결로 남긴 것

- **solve 52분** — 3절이 첫 관문.
- **커플드 런 완주 이력 없음** — 5절.
- **수요 계약 7건** — 6절.
- **`canonical_topology_v3.json` 이 gitignore 대상** — 2-1 로 매번 재생성해야 한다. 근본적으로는
  `.gitignore:41` 을 재검토할 자리다.
- **N7 / N8 미착수** — production MPC rollout endpoint, marginal price 와 런타임 계약.
  계획 문서 `IMPLEMENTATION_PLAN_V3_LEAN.md:881, 910`.
- **상류 스위트 25건 실패** — 분산 코디네이터·예측·RL 영역이고 이번 작업과 무관하다.
  판 교체 대조로 사전 존재를 증명했다(현재 판과 부모 판 `9a57869` 에서 같은 이름이 같이 깨진다).

## 9. 이 세션에서 배운 것 (같은 실수 반복 방지)

- **"내 기계에서 나온 값"을 기준값으로 적지 않는다.** 지문 `b36a6b8c…` 와 "643개 전부 통과"
  둘 다 원 기계 전용이었다. 절대경로·인터프리터 바이너리·줄바꿈이 들어간 값은 이관하는
  순간 무의미해진다. 기준으로 적을 것은 **판정**(`status: PASS`)과 **실패의 정체**(어느
  검사가 왜)이지 해시가 아니다.
- **줄바꿈은 조용히 해시를 바꾼다.** 이관 첫 검사에서 5건이 더 깨졌는데 코드 문제가 하나도
  아니었다. 봉인 해시를 쓰는 저장소는 `.gitattributes` 로 EOL 을 고정해야 한다.

- **"고쳤다" 고 말하기 전에 실 경로를 확인한다.** 배분 함수 둘만 보고 고쳤다고 했다가
  `set_signal_green` 을 빠뜨려 52분짜리 solve 를 두 번 태웠다.
- **부재는 0 이 아니다.** tie 링크가 관측표에 없는 것을 "질량 0" 으로 읽었다가 정정했다.
  실제로는 커넥터라 링크 단위 관측에 안 잡히는 것이었다.
- **인벤토리 재생성 전에 그 열의 의미를 확인한다.** `active` 8건이 뒤집힌 것을 망 변경 탓으로
  볼 뻔했는데, 구 inpx 로 재생성해도 같이 뒤집혔다.
- **긴 경로에서 프로브를 돌리지 않는다.** 스크래치패드 경로가 깊어 Windows MAX_PATH 260 에
  걸렸고, 실제 검사와 다른 실패를 보고 진단을 잘못 시작했다.
