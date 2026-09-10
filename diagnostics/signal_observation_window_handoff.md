# 1초 물리 신호 관측창 수선안 — 생산 적용 및 회귀 완료
현재 상태(2026-09-10): 아래 역사적 제안의 네 파일을 생산에 적용했다. Root/VSL의 선행 objective adapter 변경을 명시적으로 확인하고 contextual apply-check를 통과했으며 그 변경을 보존했다. 실제 `evaluation.controllers.signal_head_observation` import와 설치 VBS/PS 함수를 사용하는11개 회귀 PASS(1.338s), 전체 설치 VBS compile-only exit0/EOF 중복선언 음성대조 exit1, 전체 설치 watchdog Parser.ParseFile 오류0을 확인했다. 검증 중 생산raw변화0, 임시파일3개는 정확경로 확인 후 삭제했다.

적용·전후SHA·기준예외·테스트와 문법 결과는 `diagnostics/signal_observation_integration_validation.json`에 있다. `test_signal_observation_window_patch.py`는 역사적 파일명만 유지하고 proposal builder/patch 로딩 없이 현재 설치 코드를 검사한다. OFF 비교는 Git109afeef5da0fded77b6b68848d271a68743933e의 고정원본을 사용한다. 실제 VISSIM smoke·벽시계 성능은 아직 root의 후속 검증이며 새 config/Git index는 이 작업에서 변경하지 않았다. 아래 제안/기존검증 기록은 역사적 범위로 보존한다.

역사적 제안 상태: 생산 파일·설정·현재 런 manifest를 수정하지 않은 제안이다. 실제 VISSIM/COM 또는 MPC 검증은 수행하지 않았다. `signal_observation_window.patch`는 기존 VBS/정본 adapter/공용 watchdog의 작은 호출 변경과 새 관측 consumer 한 파일을 포함한다. production 전체를 복사한 adapter나 별도 실행기는 만들지 않았다.

현재 30초 link-exit 표본은 같은 1초 FZP 자료의 720→870 창에서 335건 중 270건만 포착했다. 실행하지 않은 계획 녹색을 분모로 사용한 별도 오류도 있었다. 수치·창 정렬·통과/우회 구분은 `selected_signal_sampling_audit.md/json`에 보존했다. 이 패치는 표본 손실과 시간/녹색 분모 문제를 수선한다.

## 단일 설정과 출처

활성화의 유일한 출처는 `urban.capacity.head_observation`이다. 아래 값은 검증 harness의 명시적 예이며 현 실행 설정에 추가하지 않았다.

```json
{
  "urban": {
    "capacity": {
      "measured": true,
      "head_observation": {
        "enabled": true,
        "min_green_sec": 30,
        "min_crossings": 5
      }
    }
  }
}
```

필드가 없거나 `enabled:false`이면 기존 수집기/추정 경로를 유지한다. ON은 양의 정수 녹색초/통과수와 `measured:true`를 명시해야 한다. 문자열 boolean/숫자, 누락 품질값, 알 수 없는 옵션은 실패한다. 임계값은 코드의 숨은 기본값이 아니다.

watchdog의 `Read-HeadObservationSettings`가 extends 체인을 병합한다. `Set-HeadObservationTransport`는 config에서 `RW_SIGNAL_OBSERVATION=1/0`과 config SHA를 설정하여 상속된 env가 OFF를 켜지 못하게 한다. ON은 기존 필수조건인 `RW_QUEUE_WINDOW=1`도 설정한다. run provenance에 effective options/전체 config chain의 경로·SHA를 기록하고, child 실행 직전에 다시 읽어 동일성을 검사한다. 새 consumer는 state의 collector config SHA, run ID, manifest의 options/transport, config chain과 network 원본 SHA를 대조한다. env는 전달 수단이며 독립 스위치가 아니다. 공용 watchdog의 controller source 목록은 새 helper도 포함한다.

## 호출 순서와 관측 정의

1. 초기 SimSec=1에서 실제 차량/SG 상태를 수집한 뒤 첫 결정을 실행한다.
2. 매 실제 정수 초에서 기존 `RunSingleStep`과 `ValidateRuntimeSignalPersistence` 후 `CollectHeadObservation`을 호출한다.
3. 결정 시각 t의 관측까지 누적한 상태로 `WriteStateJson`을 쓴다. 같은 시각의 재호출은 누적하지 않는다.
4. JSON close와 기존 B1a publish/검증이 성공한 뒤에만 queue/far/head 창을 reset한다. audit의 `resetWindows=False`는 읽기만 한다. 다음 창의 첫 전이를 잇기 위해 직전 차량 프레임/held SG 상태는 유지한다.
5. 실제 신호/램프 명령을 적용한 뒤 `SealHeadSignalStates`로 다음 [t,t+1) 구간의 actual SG 상태/ContrByCOM 소유자를 보관한다. logger는 ON에서 창을 다시 누적하지 않는다.

`HeadObservationTime`은 COM의 실제 SimSec와 SimRes를 검증한다. 이 최소안은 **SimRes=1만 지원**하고 비정수 시각, 시각 불일치, 건너뛴 초, 변경된 SimRes를 누적 전에 거부한다. 같은 실제 시각의 중복 호출은 no-op이다. 기존 step loop를 임의의 subsecond scheduler로 일반화하지 않는다.

GREEN 노출은 실제 left-step hold convention의 1초 적분이다. 실제 두 끝 상태가 모두 GREEN이며 readback이 유효한 통과만 qualified 분자에 넣어 native/control 전환 경계 bracket을 제외한다. native/COM 소유 시간의 합도 유효한 창 길이와 일치해야 한다. held SG에는 유효성도 저장하므로 직전 ContrByCOM/readback 실패가 reset 때문에 사라지지 않는다. 실패한 held 1초는 `unverified_sec`로 따로 기록하며 native/COM 또는 GREEN 분모에 넣지 않고 다음 창도 invalid로 표시한다. 이후 실제 정상 held 구간부터 회복할 수 있다. 이것은 연속 subsecond 정확 계측 주장이 아니다.

INPX의 실제 link/lane/head 위치와 직접 connector의 진출 위치를 사용한다. 같은 차로 head 앞→뒤 또는 해당 head 뒤 직접 connector 진입만 통과로 계수한다. head 앞 우회와 head 없는 source lane의 출구는 별도 우회 계수다. lane 변경, skipped/미확인 경로, 사라진 차량, 처음부터 post-head인 차량은 통과를 추측하지 않는다. 동일 차량·source road의 두 번째 head 계수는 모호성으로 표시하여 중복하지 않는다.

## 현재 추정기로 반영하는 범위

새 `signal_head_observation.py`는 실제 head/lane이 유일하고 선택 SG→phase 대응이 유일한 그룹만 고려한다. head 구조·차종 범위·selected phase가 불명확하거나, 해당 source에 unresolved 전이가 있으면 그 창을 갱신 근거로 쓰지 않는다. 양수/유한성/시간/계수 정합을 검증한다.

각 lane의 명시적 최소 GREEN 노출과 그룹 최소 통과수를 충족한 **연속하고 겹치지 않는 두 창**의 방류율 중 작은 값을 사용한다. 예를 들어 2대/1초 한 창의 spike는 적용되지 않는다. 이것은 관측된 방류 하한이며 포화용량 식별 또는 EWMA 추정이 아니다. 이전의 검증된 하한과 현재 설치 용량보다 낮추지 않는다. run ID, config chain 원본 SHA, network SHA, geometry와 품질 설정을 식별자에 포함한다. 이전 action의 run ID와 metadata 시각/관측 시각이 맞아야 하며 미래·현재 동시각·겹친 관측창의 이전 값은 명시적으로 discard한다. 자료가 없는 현재 창에서도 current manifest/source binding을 검증한 뒤 같은 식별자의 하한만 유지한다. 없거나 다른 문맥이면 현재 용량을 유지하고 `head_observation_prior_discarded`를 보고한다. 기존 link exit/실행하지 않은 green/기하 seed로 대체하지 않는다.

**SC1004의 capacity consumer 문제는 남는다.** 현재 `selected_signal_capacity_audit`에서 46/66/71 관측 그룹의 기존 internal-only/seed member 집합이 비어 실제 분배는 0이었다. 이 패치는 그 member 필터·movement/공유 pool 소유권을 바꾸지 않는다. 새 collector가 정확해져도 해당 빈 집합에는 적용하지 않으며 `head_observation_no_model_members`와 갱신 0을 보고한다. 기존 fallback을 전역적으로 올리지 않는다. 실제 head service를 여러 destination alias가 공유하는 accepted service pool로 연결하는 수선은 별도 과제다. 빈집합 회귀는 619.59를 전달해도 설치 0임을 확인한다.

## 비용과 검증 한계

`ReadVerifiedVehicleTables`는 동일 실제 시각의 이미 검증된 네 COM bulk 배열을 재사용한다. 재사용 시에도 SimSec와 차량 수가 같아야 한다. decision/logger가 같은 초에 전체차량을 또 COM bulk 읽기 하지 않는다. CPU 집계 자체는 기존 호출에서 재실행될 수 있다. native SG는 기존 readback이 없으면 추가로 읽어야 한다.

1초 수집은 전체 bulk capture 수를 기존 30초 수집보다 늘린다. 벽시계 성능 개선을 주장하지 않는다. `HEAD_OBSERVATION_BULK_READS/CACHE_HITS`를 추가하여 후속 실제 smoke에서 비용을 확인할 수 있게 했다. VISSIM 접근 없이 해당 성능과 native 정수 경계 convention을 완전히 검증할 수는 없다.

검증: 미적용 diff `git apply --check --whitespace=error` PASS. 원본 byte SHA가 manifest와 같음을 매 harness 실행에서 확인한다. 제안 Python/PS/VBS 함수만 메모리 또는 임시 fake-COM harness로 추출하여 11개 회귀 PASS. 핵심은 OFF adapter AST 동일, config 상속/env 무효화/재실행 전 SHA 변조 거부, 물리 우회·경계·중복 제외, no-member 설치 0, 짧은 녹색/NaN 거부, 연속 두 창, 동일 초 bulk cache, 실제 시각/SimRes/변경된 count 거부, publish 이후 reset 순서이다. 추가 검토에서 기존 초안이 타 런의 이전 floor를 200→800으로 carry하고 invalid ContrByCOM held 구간을 reset 후 `clock_complete=True/native_sec=1`로 오분류함을 실제 추출 함수로 재현했다. 현재 회귀는 타 런/미래/겹침/config·network 원본 변경 시 carry 0과 invalid held 노출의 다음 창 보존을 검사한다. 전체 제안 VBS에 Option Explicit 직후 최초 실행문 WScript.Quit 0을 삽입한 임시 파일은 cscript compile-only exit0을 확인했다. quit 뒤 EOF의 중복 Dim 음성대조는 compile error/exit1이므로 뒤 본문도 컴파일됨을 확인했다. 전체 제안 watchdog도 Parser.ParseFile 오류0이다. 원본 삽입/복원·파일 SHA와 결과는 validation.full_script_syntax에 기록했다. 실제 COM/VISSIM smoke는 아직 하지 않았다.

필수 인계 파일:

- `diagnostics/signal_observation_window.patch`
- `diagnostics/signal_observation_window_patch_manifest.json`
- `diagnostics/test_signal_observation_window_patch.py`
- `diagnostics/signal_observation_window_handoff.md`
- `diagnostics/signal_observation_window_validation.json`

현재 런 종료 후 root가 patch의 base SHA와 apply-check를 다시 확인하고, config ON/OFF의 짧은 실제 VBS smoke에서 collector cadence/green/sourcehash/성능을 검증해야 한다. 이 인계는 생산 적용 완료 또는 SC1004 공유 용량 문제 해결을 뜻하지 않는다.

## 실제 150초 실패 후 정밀도 수정 (2026-09-10)

생산 적용 뒤 첫 NC smoke가 150초에서 엄격한 좌표 비교로 중단되었다. 235개 head의 신원/차로/SG는 모두 일치하며, 116개 좌표의 최대 4.55e-12 m 차이는 실제 VBS 15자리 직렬화와 정확히 일치했다. consumer의 기대 좌표만 동일 직렬화 정본으로 바꾸고 exact 비교를 유지했다. 실제 원본 fixture·변조·VBS 직렬화 및 기존 회귀 15개 PASS; 상세는 `observer_head_precision_failure.md/json`이다. 기존 제안/최초 적용 기록은 당시 결과로 보존한다. 첫 런의 1050초 완주를 주장하지 않으며 v2 런의 실제 창·녹색·궤적 검증은 별도 수행한다.
