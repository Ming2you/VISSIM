# SDMPC controller publication — 2026-09-20

이 브랜치(`codex/sdmpc-controller-20260920`)는 현재 워크스테이션에서 검증·실행한 SDMPC 컨트롤러의 스냅샷이다. 실행 중인 checkout의 HEAD와 소스를 유지하기 위해 별도 checkout에서 공개했다.

## 코드와 기준점

- 기반 커밋: `c4e646396deedf496c207526e0862b6a80b54cae`. 현재 실험의 네트워크·모델 기준이다.
- SDMPC 설계 참고: `Ming2you/Numerical-Sim`, `codex/sdmpc-source-20260919`, `b53ebd72e512fb365bc5ebbabf1e9f40e5c08ed5`.
- 원격 `codex/control-full-review-20260909`의 후속 커밋 `342c869`까지의 geometry/회계 변경은 이 실행 버전에 합치지 않았다. 이 브랜치를 기존 브랜치에 통합하려면 해당 차이를 검토하고 다시 검증해야 한다.
- 정본 진입점은 `evaluation/controllers/vissim_stackelberg_adapter.py` 그대로다. `evaluation/controllers/sdmpc.py`가 SDMPC 결정을 수행한다. vendor는 변경하지 않았다.
- 테스트된 실행 버전을 보존하기 위해 그 버전에 이미 적용된 response cache/worker, clock cache, 이웃 감사 생략 옵션 및 native 진단 변경도 함께 포함했다.

## 활성화와 계산

검증된 physical-eight/native-clock 전체 config의 `adapter.sdmpc`를 `"proxlinear-v1"`로 설정한다. 이 키가 없으면 SDMPC를 선택하지 않는다. NC와 warmup에서도 SDMPC를 실행하지 않는다. 기존 `adapter.joint_owner_game` 실행 설정은 worker·예산·물리 출력 검증에 계속 필요하다.

기존 전체 config에서 아래 키를 설정한다. 아래 JSON은 설명용 부분 설정이며, 단독 tuning 파일로 사용하지 않는다.

```json
{
  "adapter": {
    "sdmpc": "proxlinear-v1",
    "joint_owner_game": {
      "response_cache_enabled": true,
      "response_parallel_workers": 8,
      "ignore_wall_time_limits": true
    }
  }
}
```

SDMPC 수치 파라미터의 단일 출처는 `evaluation/parameters.json`의 `sdmpc`다. Python 환경에는 NumPy와 SciPy가 필요하다. 검증 시 SciPy 1.18.1을 사용했다. 8 workers는 예측 응답 계산의 병렬도이며 native VISSIM은 한 대에서 순차 실행한다. 150초 또는 300초 내 결정 완료를 보장하는 설정이 아니다.

현재 구현은 17개 도시·2개 freeway 주체, 8개 물리 미터, 6개 자유 VSL 구간을 다룬다. 공통 기준점에서 own+externality gradient, 결정 중 고정된 가격, 로컬 QP, 자원 projection, 원래 비선형 모델 재평가를 사용한다. 예측 지평은 450초다. 유한 반복 결과이며 Nash 수렴을 인증하지 않는다.

Ω TTT를 중복 없이 분할하고 무소유 재고 비용도 보존한다. N_P cap, 유지 명령의 실제 합류 예측에 고정한 N_UF(±40 veh/h), 신호/offset 및 미터 이동 제약을 유지한다. 가격의 다음 결정 반영은 native 명령 적용 receipt를 확인한 뒤 승인한다. 미터·VSL 차분은 실행 가능한 이산 값을 사용한다.

## 완료된 검증과 남은 작업

아래 결과는 워크스테이션의 `diagnostics/sdmpc_20260919/` 검증 기록에서 확인했다. 실행 설정, native 입력, 원본 FZP, saved-state 및 실행 로그는 로컬에 보관하며 이번 컨트롤러 공개에는 포함하지 않는다.

| 검증 | 결과 |
| --- | --- |
| 저장 상태 900 / 1350 / 2400초 | 명령·제약·213행 writer 및 8 workers 확인, 6개 VSL 좌표 모두 실제 탐색 |
| 위 세 결정 전체 처리시간 | 285.091 / 313.160 / 304.525초 |
| 위 세 결정의 예측 TTT 감소율 | 1.718% / 1.844% / 1.030%; native 성능 개선율 아님 |
| 선택 명령 | green/offset 변경; 세 상태에서 미터 g10·VSL120 유지 |
| native 1500초 | 완료, SDMPC 5회 적용, LDP/readback 및 직전 적용 이후 가격 승인 확인 |
| NC 9000초 | 완료, native 실행 검증 통과 |
| CL 9000초 및 NC/CL 비교 | 공개 시점 진행 중; 전체 성능 결론 미확정 |

최초 VSL 차분은 10 km/h probe가 격자에 다시 반올림되어 무효였다. 이를 실행 가능한 격자로 수정한 뒤 세 상태를 다시 검증했다. 위 결과는 수정 후 결과다. 미터/VSL이 현재 최종 선택에서 유지된 이유와 실제 freeway 제어 이득은 아직 확인해야 할 항목이다.

공개 checkout에서 SDMPC·worker·clock·감사 옵션·native 진단 관련 회귀검사 165개가 통과했고, 원본 설정의 파라미터 검사도 PASS였다. 검사기는 기존 calibration보다 parameters/config override를 우선하는 경고를 출력하며, 이번 공개 과정에서 calibration 값을 바꾸지 않았다. 핵심 51개 검사를 다시 실행하는 명령:

```powershell
python -B -X utf8 -m unittest diagnostics.test_sdmpc diagnostics.test_joint_main_integration diagnostics.test_decision_shared_response_cache diagnostics.test_parallel_shared_response diagnostics.test_native_clock_plan
```

파라미터 검사는 `python -B -X utf8 scripts/verify_parameters.py <준비한 전체 설정 경로>`로 실행한다. 위 PASS는 이 워크스테이션의 실제 실행 설정을 검사한 결과다.

기존 `test_joint_written_action`과 `test_signal_actuation_contract`의 전체 suite에는 유실되거나 오래된 fixture 문제가 있어 전체 통과로 계산하지 않았다. 실제 저장 상태와 native 런에서는 정본 writer 결합 검사를 통과했다.

## 다른 PC에서의 사용

기존 native-clock 및 실행 설정에는 워크스테이션별 절대경로가 들어 있어 이번 공개에서 제외했다. `verify_parameters.py` 통과는 파라미터 일관성 검사이며 다른 PC의 native 입력 준비 완료를 뜻하지 않는다.

새 PC에서는 `docs/HANDOFF_20260913_controller_runtime.md`의 망·수요·신호 준비 절차를 따르고, 실제 사용하는 physical-eight/native-clock 전체 설정에 위 SDMPC 선택을 적용한다. 누락된 native 입력을 과거 다른 정의의 파일로 대체하거나 원본 receipt의 경로/SHA를 일괄 수정하지 않는다. 준비한 새 설정으로 저장 상태와 짧은 native 검증을 먼저 수행한다. 현재 실행이 끝날 때까지 다른 PC에서 native를 동시에 시작하지 않는다.

공개 전 모든 controller 모듈·parameters·native VBS, 총 48개 소스 파일이 테스트한 실행 소스와 CRLF/LF 정규화 후 동일함을 검사했다. 원래 byte SHA 기록은 로컬에 보존한다. 다른 checkout의 byte SHA와 실행 receipt가 자동으로 호환된다는 의미는 아니다.
