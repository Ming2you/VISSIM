# Adapter 정리·초기화 경로 인벤토리

2026-09-10 정리 완료: 정본 baseline 실런과 통합 main 검증 뒤, 사용자가 요청한 불필요한 어댑터 정리의 첫 단계로 `_superseded_20260827`의 Python 사본18개를 삭제했다. **7,314,989 bytes / 146,966행**을 제거했고 manifest와 git 복구 근거는 남겼다. 아래 초기화 분석·제안(§3 이후)은 주로 `6056c94` 시점의 역사적 검토 기록이다. 그 안의 "미적용/미수정" 문구를 현재 통합 상태로 읽지 않는다.

**삭제18개 완료.** 삭제 직전 현재 tracked/untracked 비무시 실행 소스에서18개 basename과 controller archive 경로를 다시 검색했고 active runtime caller는0이었다. 삭제 뒤 canonical adapter의 fresh import가 통과했다. `global_controller_api.py`는 별도 후보로 유지했다. 이번 정리에서 canonical adapter·VBS·vendor·config는 수정하지 않았다.

복구 검증은 삭제 전후 모두18/18 PASS다. 고정 커밋 `6056c94770bb45c19e0a32b90416444db2bce2d1`의 git blob을 엄격한 LF 정규화 후 CRLF로 변환하면 각 파일의 원래 raw SHA256과 정확히 같다. 혼합 줄바꿈·복구 불일치는0이었다. PowerShell에서 명시한18개 절대경로 모두의 parent가 정확히 해당 archive이며 worktree 안인지, 일반 파일인지, 검증 후 SHA가 바뀌지 않았는지 확인한 다음 `Remove-Item -LiteralPath`를 파일별로 호출했다. 재귀 삭제는 하지 않았다.

`MANIFEST_20260827.json`은 기존17개 entry의 run 목록·SHA·역사적 lines를 보존하며 각 entry에 commit/blob/raw SHA/실제 줄 수/복구 변환을 추가했다. 원래 빠져 있던 `legacy_base_20260827.py`도 mainline과 동일한 blob·raw SHA의 중복 entry로 추가했다. 삭제 전 원본 감사와 삭제 후 결과는 `diagnostics/retired_adapter_archive_audit.json`에 있다. 다음 명령은 구버전을 다시 설치하지 않고 git에서18개의 원래 raw SHA가 복구되는지만 검사한다.

```text
python diagnostics/verify_retired_adapters.py
```

개별 파일의 감사용 복구가 필요하면 Python에서 `subprocess.check_output(['git', 'show', '<commit>:<entry.original_relative_path>'])`로 바이트를 받고 `blob.replace(b'\r\n', b'\n').replace(b'\n', b'\r\n')`를 적용한다. SHA256이 manifest의 `entry.sha256`과 같음을 확인한 뒤 별도 감사 디렉터리에 `open('xb')`로 쓴다. PowerShell 텍스트 redirection이나 bare LF git blob을 원래 raw 파일이라고 취급하면 encoding/줄바꿈 때문에 같은 SHA가 되지 않는다. 정본 실행 경로에 옛 adapter를 되살리는 용도가 아니다.

## 1. 보관 지침과 사용자 cleanup 요청

- `AGENTS.md:3-4`: 실런 중 canonical adapter 편집 금지, 검증 후 adapter 사본 제거.
- `CLAUDE.md:19-21,42-43`: 정본1벌, 구버전 재사용 금지, 검증 후 사본 삭제.
- 원래 archived `MANIFEST_20260827.json`의 note: "여기 파일들은 run_provenance 의 adapter sha256 대조용 증거다. 지우지 마라." 이 문구는 현재 `historical_note`로 보존했다.
- 이번 사용자 지시는 **정본 검증 후 불필요한 adapter 정리**를 명시한다. 따라서 manifest의 기존 보관 문구만을 이유로 다시 허가를 요청할 필요는 없다. 대신 현재 byte/hash와 git object 회수경로를 남겨 감사 증거를 유지한다.
- `vendor/`의 anchor pin 문제(`CLAUDE.md:396-397`)는 별개다. 이 문서의 삭제 후보는 모두 `evaluation/controllers`이며 vendor 삭제를 제안하지 않는다.

## 2. 삭제 완료: archive adapter 18개

삭제한 합계 **7,314,989 bytes / 146,966행**. 아래 표는 삭제한 파일과 유지된 git object의 목록이다. 최초 `6056c94`의 controller tree33개 중18개였으며 현재 신규 domain helper 수와 혼동하지 않는다. Canonical adapter는 별도로 유지한다.

공통 디렉터리: `evaluation/controllers/_superseded_20260827/`.

| 삭제 후보 파일 | git blob @6056c94 | manifest run 수 |
|---|---|---:|
| legacy_base_20260827.py | c3a0cb1de182729ddd1ec9d46d3c86d1293bdc14 | 미등재 |
| vissim_stackelberg_adapter_allfix_20260825.py | 732f3f2538b02c21a90ab76ca559f9d181c5f84f | 1 |
| vissim_stackelberg_adapter_dual_20260826.py | a9c41f502fa9e410a6c321246b3996bc996150fe | 1 |
| vissim_stackelberg_adapter_mainline_20260825.py | c3a0cb1de182729ddd1ec9d46d3c86d1293bdc14 | 1 |
| vissim_stackelberg_adapter_map4e_20260826.py | de9bee16fe193a258d816655ffa02e411026dda6 | 3 |
| vissim_stackelberg_adapter_merge_20260824.py | c6628ae9ac6996db8f3b9922659418cec549e1aa | 4 |
| vissim_stackelberg_adapter_nfclean_20260824.py | 2c37f1861641063d044c191b793a2157c975b452 | 1 |
| vissim_stackelberg_adapter_ninref_20260825.py | 21d7d9edd6315110561efe326e567f7191d35aaa | 0 |
| vissim_stackelberg_adapter_npband_20260826.py | bf312361911960e001bee2be9634028bf563796a | 2 |
| vissim_stackelberg_adapter_offarm_20260825.py | 4ca9a76414bc7db42687b0ab5972fc7525faed28 | 2 |
| vissim_stackelberg_adapter_offset_20260824.py | c1284a37ed7ee83330b0dac8e6942551ecb0cf4d | 0 |
| vissim_stackelberg_adapter_qprice_20260825.py | 62846138b88c965c81c3dcc9ac47d05355c01795 | 0 |
| vissim_stackelberg_adapter_qstop_20260825.py | c82c2d04b4a9a8191fd4c5ea2927f45a03d0a456 | 0 |
| vissim_stackelberg_adapter_regret_20260824.py | f93d1f52d7ff33c414c7d179447831b64e02a416 | 1 |
| vissim_stackelberg_adapter_slew_20260826.py | 198bdb282b42106c89ccb7348096cc96828627f9 | 2 |
| vissim_stackelberg_adapter_subwin_20260824.py | fdd502e0bdb74077b66865f760968ee3dd1cf6cd | 1 |
| vissim_stackelberg_adapter_tau_20260825.py | 2d7d21a97a02f7acb1e4abaf41260db3ccfd1f4d | 1 |
| vissim_stackelberg_adapter_tauoff_20260825.py | 46a449944d41638239307e45a08ea86bead4079f | 1 |

`legacy_base_20260827.py`는 mainline 파일과 **git blob까지 동일한 완전중복**이다. 삭제 직전 manifest17개 entry의 SHA256은 원래 파일 byte와 전부 일치했다. legacy는 초기 manifest에 없어 당시 `manifest_match=False`였으며 파일 오염이 아니라 중복 미등재였다. 현재 manifest에는 중복관계를 명시한18번째 entry가 있다. 원래 `lines`는 실제 splitlines 수보다 각1 크게 기록되어 있으므로 해당 역사 필드는 보존하고 검증한 `actual_splitlines`를 따로 추가했다.

검색 범위와 결과:

1. `git ls-files evaluation/controllers`로 추적 파일 범위를 고정했다.
2. git-tracked 전체에서 18개 basename과 `_superseded_20260827` 경로를 `git grep`으로 찾았다.
3. archive 자체를 제외한 basename 참조는 **격리 config의 설명문1곳**뿐이다: `evaluation/configs/_superseded_20260827/real_world_modi_pstack_distributed_core17legs4b_regret_20260824.json:9`. 실행 경로나 import가 아니다.
4. active `.py/.ps1/.vbs/.json`에서 archive directory를 로드하는 경로도 찾지 못했다. manifest를 읽는 실행 스크립트도 없다.
5. 삭제 직전 확인한 canonical VBS 기본 adapter는 `scripts/run_real_world_stackelberg_controller.vbs:5467`의 `evaluation/controllers/vissim_stackelberg_adapter.py`이다. Archive 중 하나를 fallback으로 택하는 분기는 없다.

삭제 실행 기록:

- 18개 `.py`를 명시해서 삭제했다. 디렉터리는 유지했고 이 하위 작업에서는 staging/commit을 수행하지 않았다.
- `MANIFEST_20260827.json`에 `archive_storage: git`, 고정 commit, entry별 `git_blob`, raw SHA와 원래 상대경로, legacy의 중복 관계를 기록했다.
- Git에서 바이트를 읽고 LF→CRLF 변환하면 원래 raw를 복구한다. 삭제 전후18개 SHA를 모두 검증했다. History rewrite/GC/remote 삭제는 하지 않았다.
- 과거 run/hash를 새 canonical 파일의 hash로 바꾸지 않았다. §3의 `global_controller_api.py`는 이번 삭제 범위에 포함하지 않았다.

## 3. 나머지 controller 파일의 실제 소비자

| 파일 | 직접/실행 소비자 근거 | 판정 |
|---|---|---|
| vissim_stackelberg_adapter.py | canonical VBS `:91,5342`, 정본 PS1, 수백 진단·검증·실행 참조 | 유지: 유일 adapter |
| action_csv_schema.py | canonical adapter·signal_timing_oracle·VBS validator/contract tests | 유지 |
| fixed_signal_schedule.py | canonical adapter·signal actuation 생성기·native phase tests | 유지 |
| native_phase_green.py | canonical adapter·signal_group_plan·movement/SG timing 생성기 | 유지 |
| plant_cycle.py | canonical adapter·VBS·SG plan 생성기·실효 주기 tests | 유지 |
| signal_group_plan.py | adapter·plant_cycle·action schema·vendor state·VBS | 유지 |
| signal_timing_oracle.py | offset_promotion·run_readiness·verify_signal_timing_oracle | 유지 |
| offset_promotion.py | canonical adapter·VBS·readiness·experiment matrix | 유지: 실제 offset writer 경계 |
| network_pressure.py | `scripts/network_pressure_diag_20260906.py:18`에서 동적 import. h_np config/chain도 존재 | active canonical 미사용이어도 **진단 소비자가 살아 있으므로 단독삭제 금지** |
| global_controller_api.py | 외부 class/function import·실행 참조0. `evaluation/environment_setup_summary.md:196` 문서1곳 | **별도 삭제 후보**: 0단계 noop/fixed-time placeholder CLI |

`global_controller_api.py`의 `GlobalNoopController`/`FixedTimePlaceholderController`는 신호두가 없다는 전제를 가진 초기 산출물이다. 현재제어기의 facade가 아니다. 이 파일도 삭제한다면 문서의 단계0 역사 설명은 보존하거나 역사 경로로 표시한다.

`evaluation/controllers/README.md`는 아직 "현재 action GLOBAL_NOOP, 망에 signal이 없음"이라고 서술한다(`:7-9`). 실제 current 진입점을 안내하도록 정리가 필요하다. 나머지 contract `.md`는 executable adapter 사본이 아니므로 이 삭제 묶음에 넣지 않는다.

신규 `freeway_fd.py`, `freeway_local_state.py`는 canonical adapter의 domain helper이며 adapter 사본이 아니다. 부모·spawn 모두 동일 모듈을 읽는 설치 경로를 만들고 최종 기록에 포함한다.

## 4. main·price worker·offline 순서 차이

주요 위치: canonical `vissim_stackelberg_adapter.py:12216-12296`, worker `:4720-4739`, `scripts/offline_harness_20260904.py:46-96`.

| 요소 | main | offline harness | price worker | 판단 |
|---|---|---|---|---|
| config switches/calibration/config 생성 | 수행 | 수행, mode=`fast-smoke` 고정 | cfg를 pickle로 전달 | 부모/offline mode·controller 인자까지 맞춰야 함 |
| phase 수정→존재회전→dead beta→measured beta→dead beta 재적용 | 수행 | 같은 순서 | cfg로 전달 | 값 설치이므로 worker에서 재실행할 필요 없음 |
| geometry/phi/two-branch 값 | `:12246-12250`, movement fold 앞 | geometry/phi만 `:75-81`, urban 설치를 전부 마친 뒤 | cfg로 전달 | **offline two-branch 누락은 확정 오류** |
| zones→segment runtime→kbest→dedupe | main 값 설치 직후 | 마지막으로 뒤늦게 설치 | `:4736-4739` | 내부4개 순서는 같으나 전체 단계위치가 다름 |
| movement fold/merge/capacity/landing/native structure | geometry 이후 | geometry 이전 | cfg 값+일부 hooks 복원 | 지금 commutation을 추정하지 말고 main 순서를 공통화 |
| state 투영→monitor timing patch→local observation guard | 수행 | 수행 | 투영 안함, monitor만 복원 | worker는 완성state를 받으므로 전체투영 재실행 금지 |
| 신규 local-state 및 FD hook | 아직 실런미배선 | 아직 없음 | 아직 없음 | 세 군데 개별복사하지 말고 동일 helper로 넣기 |

offline의 `hasattr(qb, installer)` guard(`:75-90`)는 과거 adapter도 허용하려는 흔적이다. 정본1벌 체제에서는 누락을 조용한 no-op으로 만드는 원인이다. canonical helper를 필수 import하고 필요한 기능이 없으면 즉시 오류를 내는 편이 맞다.

worker bootstrap의 설명(`:4755-4757`)도 낡았다. "calibration v2는 cfg 속성이므로 모두 pickle로 간다"고 쓰지만 `install_vissim_calibration_runtime_patches:6494-6538`은 TrafficState 메서드를 monkeypatch하고, `:6559-6578`은 spillback 함수를 교체한다. 이는 cfg만 pickle한다고 복원되지 않는다. **n7의 현재 calibration에는 physical_inventory가 비어 있어 이번 런의 즉시손실이라고 할 수는 없다.** 그러나 공통 init을 만들 때 값설치와 함수patch를 실제 side effect로 구분해야 한다.

기존 `install_landing_storage_runtime`과 geometry profile wrapper도 main에서는 geometry→landing, worker에서는 landing→geometry다. 현재 n7은 landing_storage가 없어 비활성이다. 신규보관고 팔에서 이 wrapper 순서가 합성/보류검증을 통과하는지 확인해야 한다.

## 5. 공통 초기화 추출안

공개 호출은 canonical adapter의 **`initialize_vissim_model(...)` 한 곳**으로 모으고 내부를 명확한 두 단계로 분리하는 것이 안전하다. list 문자열과 getattr로 임의 registry를 만드는 대형 프레임워크는 필요 없다.

1. **configure 단계(부모와 offline)**: tuning/calibration/mapping/state_json에서 cfg 값과 구조를 만든다. 현재 main 순서를 그대로 추출한다. 값 재추정(measured rates 등) 및 mapping merge를 worker에서 다시 수행하지 않는다.
2. **install 단계(부모/offline/worker 공통)**: 이미 cfg에 적재된 값만 읽어 모듈/class hooks를 복원한다. cfg 밖 closure에 calibrated 숫자를 숨기지 않는다. worker에는 raw 차량자료 대신 필요한 network_path와 mapping만 전달한다.
3. **state projection(부모/offline)**: 완성cfg·같은 mapping으로 state를 만든다. worker는 전달받은 state를 사용한다. 함수 반환은 `(state, detector_mapping, metadata)`처럼 기존 harness 계약에 맞춘다.

작은 단계별 실행:

- **R1: freeway 초기화만 먼저 공통화.** 부모 configure 순서 `segment_lanes → lane_drop → two_branch → local_state.configure`. 공통 hook 순서 `zones → segment_runtime → local_state.install → freeway_fd.install → kbest → dedupe`. 부모/worker/harness에서 동일 함수를 호출한다. `freeway_fd.install`은 현재 adapter runtime과 같은 zone/segment wrapping 순서를 요구한다.
- **R2: main의 beta/urban configure 블록을 통째로 함수 추출.** 흐름·인자·순서·metadata 키를 그대로 두고 main과 harness가 호출한다. 수치수정과 리팩터를 같은 커밋에 넣지 않는다.
- **R3: runtime installer들의 side effect를 분리.** calibration/spillback 같은 숨은 함수patch도 cfg 기반으로 복원 가능하게 정리한다. 부모/worker의 동일 단일 install 함수를 쓴다.
- **R4: CLI/harness를 얇게.** 입력 파일해석·경로/실험provenance·결과쓰기만 남기고 init을 공유한다. `resolve_live_controller.py`의 하드코딩 설명(`segment_agents=False` 등)은 실제 빌드 객체를 읽도록 수정한다.
- **R5: archive 삭제 + README 교정.** 정본 검토런이 끝나면 코드사본18개와 선택된 phase0placeholder를 제거한다. 현재baseline 실런과 메커니즘 수정의 귀속을 분리한다.

검증은 단순히 installer 이름 목록이 같다는 테스트로 끝내지 않는다. 동일 n7 snapshot을 main 공통초기화와 harness에서 만들어 cfg의 실효값·lane profile·movement beta/capacity·3~4substep 상태를 비교한다. two-branch 팔도 포함해 새FD off/on 발동을 직접 확인한다. Windows spawn은 같은상태/후보에 대한 **가격벡터와 한계가격 분해**를 비교한다. 이번 FD 테스트의 spawn 확인은 speed/critical 함수동등성까지만 다룬다.

## 6. `freeway_local_state.py` 독립 검토

첫 독립검토에서 `diagnostics/test_freeway_local_state.py` **5개 PASS**를 확인했다. 아래 β 결함을 root에 전달했고, root가 신규 모듈을 수정해 **6개 PASS**를 보고했다. 후속코드도 다시 읽어 movement별 β·잔여stock·공유receiver 제한이 들어간 것을 확인했다. canonical adapter와 vendor는 여전히 미수정이다.

### 정상인 수정

- `current_lane_profile`은 실제 `_local_lane_profile(model, occupancy, demand)`의 반환을 각 substep마다 기록한다. 후보/링크가 바뀔 때 map을 통째로 교체하므로 이전 링크 profile을 무조건 재사용하지 않는다. 실제 phi가 읽는 context를 갱신한다는 root 진단에 부합한다.
- zero-stock에서 drain/intake를0으로 만드는 것과 `sum(drain)*dt<=occupied` 보장은 기존 유령 intake를 없앤다.
- 같은 receiving link를 향하는 movement들의 **합계**를 잔여공간에 제한하는 것은 올바르다. 원본은 각movement가 같은공간을 개별로 쓸 수 있었다.
- flag가 False일 때 원본을 호출하는 경로는 현재 tests에서 정확히 동일하다.

### P1 발견 후 root 수정 완료: movement β 보존

첫 wrapper는 `original_drain`이 돌려준 receiver 합계를 stock에 비례축소했다. 그러나 원본 `_local_offramp_drain`(`wu_faithful_follower.py:2015-2027`)은 movement β를 안 읽는다. 호출하는 `_signal_leaving_rate`는 β를 곱하지 않는다고 명시한다(`wu_distributed.py:194-203`). global `_drain_offramp_storage`는 `min(beta*occupancy, dt*green*cap)`을 쓴다(`urban_queue_model.py:585`).

합성 재현(수정 전 wrapper 호출): stock10veh, dt10s, A행β0.9/B행β0.1, 두movement 용량10000vph, A receiving은 만석, B는 공간충분. 결과는 **B로3600vph=10veh 전량배출**. global의 β 몫 상한이면 B로는1veh만 빠질 수 있다. 막힌90% 목적지 차량을 열린10% 목적지로 보낸 셈이다.

이 β누락은 원본부터 있던 오류이며 stock cap이 새로 만든 것은 아니다. receiver aggregate 뒤에서 scale하는 구조로는 원래 movement별 β를 복원할 수 없어서 root에 per-movement 계산을 요청했다.

root의 후속수정은 원본aggregate를 버리고 실제 movement 목록을 순회해 `intent_m=min(max(beta_m,0)*occupied/dt, max(signal_rate_m,0))`를 먼저 계산한다. 그 뒤 공유 receiving 잔여공간과 전체stock을 순차제한한다. 새90%blocked/10%open test에서1veh만 배출한다. beta0은0배출, beta합<1의 빠진 몫은 storage에 남고, 합>1도 전체stock을 넘길 수 없다. 이 부분의 요청된 수선은 코드에 반영됐다. 아래의 travel/relief 차이 때문에 전체global plant와 동등하다고 주장하지는 않는다.

### 추가로 검증할 경계

- `local_state.install`은 **geometry runtime 뒤**에 호출해야 한다. 앞에서 감싸면 context에 raw nominal4차로를 기록한 후 바깥 geometry wrapper가3차로로 바꿔 실제반환과context가 갈릴 수 있다.
- 현재 `dt_h<=0` 검사는0/negative를 막지만 NaN/Inf는 막지 않는다. cfg가 timestep을 검증한다면 중복검사는 불필요하나, 공용함수 계약상 positive finite를 요구할지 명확히 한다.
- hook의 `lane_context` dict는 최초설치 adapter 문맥을 capture한다. 같은프로세스에서 adapter를 임의 다른module명으로 재적재하는 tool은 실제 speed-wrapper가 읽는 dict와 같은객체를 전달해야 한다. canonical runtime 모듈이 한 번만 로드되는 초기화가 더 안전하다.
- 함수 stock cap은 **substep 시작 occupied만** drain하도록 한다. caller는 그 뒤 inflow를 더한다(`wu_faithful_follower.py:2340-2344`). 질량은 보존하지만 새inflow 즉시drain 여부가 global urban substep 타이밍과 다를 수 있으므로2개urban substep/1개freeway substep 예제로 시간정합을 확인한다.
- caller의 receiver relief는 off-ramp마다 적용된다(`:2348-2354`). 여러off-ramp가 같은 receiver를 공유하면 relief가 중복 적용될 수 있다. 새drain wrapper만으로 해결되지 않는 별도기존문제다. 현행 n7은 OR_D_W/E, OR_F_W/E 각각 다수receiver를 공유한다.
- global은 pending off-ramp transit을 drain가능stock에서 뺀다(`urban_queue_model.py:567-570`); local은 총occupied만 받는다. transit 스위치활성 팔에서 local/global 동등성을 다시 봐야 한다.

최소추가 test는 β가0인 movement, 막힌high-β/열린low-β, beta합<1, 두off-ramp sharedreceiver, 반복부모/worker설치 뒤 profile 동일성이다. 이 보고서에서는 production 함수나 root tests를 중복수정하지 않았다.

## 7. 공유 runtime 구현 준비 완료

root 요청으로 신규 `evaluation/controllers/runtime_setup.py`를 작성했다. `configure_runtime(adapter,cfg,tuning,mapping,state_json,previous_action_path,detector_mapping,calibration,TrafficState,physical_projection_input=None)`가 `(state,detector_mapping,metadata)`를 반환한다. `6056c94` main의 runtime metadata 초기화부터 forecast 앞까지 순서를 명시적함수호출로 추출했다. production에서 AST/exec는 사용하지 않는다.

`configure_freeway_runtime`은 geometry/phi/two-branch/local flags를 설정하고, `install_freeway_runtime`은 부모·worker에 동일한 zone/segment/local-state/FD/kbest/dedupe hook 순서를 제공한다. `install_worker_runtime`은 기존worker hook을 보존하면서 이 공통freeway helper를 호출한다. calibration의 숨은함수patch와 phase-vector 등 기존worker에서 복원되지 않던 기능까지 새로 재설계하는 것은 이번 추출의 범위가 아니다.

연결용 `diagnostics/runtime_setup.patch`는 canonical main, 기존worker callback, offline harness를 공통 helper에 연결한다. **아직 적용하지 않았다.** patch의 변경후두파일은 Python compile을 통과했고 `git apply --check`도 PASS였다. root가 진행런 종료 후 적용할 수 있다.

`diagnostics/test_runtime_setup.py` **3개 PASS**, 약4.5초. reference는 현재helper를 다시호출하는 방식이 아니라 git의 고정 `6056c94` main AST다. AST 실행은 진단test 안에만 있다. local `state_000900.json`을 사용한다(미보유 환경은 `VISSIM_RUNTIME_TEST_RUN` 지정).

- n7 비활성 flags: cfg/network, 투영state, detector mapping, 기존metadata, global4substep, 실제link-local 후보 TTT/action이 원래main과 정확히 같다.
- i1+새local flags: 원래main에 의도된새hook만 직접적용한 reference와 모든같은수치가 정확히 같다.
- worker hook2회재설치가 state를 변경하지 않고 n7/i1의 동일rollout/local 후보비용을 유지한다.

마지막검사가 처음에 n7에서 실패했다: 동일국소후보 TTT가 **76.491834→79.141879**로 바뀌었다. legacy segment wrapper가 inner zone marker를 가려 repeated zone installer가 cell을 head로 먼저바꾸는 문제였다. 공통 helper에서 segment설치 직후 zone marker를 보존해 이 반복초기화 오류를 수정했고 재검사PASS다. 단순installer 목록비교로는 놓칠 수 있는 동작차이였다.
