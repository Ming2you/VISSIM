# 3150초 실행 중단 — Codex 앱/실행 서비스 업데이트

`D:/VISSIM_runs/20260927_sd31_queue_origin9000/sdmpc`는9000초 완료 결과가 아니다. 실제3150초까지 진행하고 해당 제어 계산 중 중단됐다.3000초 명령 적용 기록은 존재하며3150초 명령은 미완료다. 기존 NC9000과 이전 실패 자료는 보존한다.

## 확인된 증거

- Native 로그 마지막:2026-09-27 16:02:22, `OBS150_BUNDLE sim_sec=3150`.
- SDMPC 마지막 progress:16:03:11,3150초 상태의 후보12개 예측 시작. PFO/미분 연결 단계는 통과했고 error/decision timeout 기록은 없다.
- Windows System `WindowsUpdateClient` event43:16:03:27.403, `OpenAI.Codex` 업데이트 설치 시작.
- `Service Control Manager` event7040:16:03:27.953, ChatGPT 실행 서비스 비활성화.
- event7045:16:03:28.934, 새 Codex26.924.2738.0의 sandbox service 설치.
- `WindowsUpdateClient` event19:16:03:30.247, Codex 업데이트 설치 완료.
- 재확인 시 exec77249는 소실됐고 런 소유 runner/cscript/VISSIM도 없다. 현재 Codex 엔진은16:40:41에 생성됐다. OS 마지막 부팅은9월23일이며 이번 OS 재부팅은 아니다.
- STOP 파일 없음. watchdog 종료/실패 꼬리 기록 없음.16:03 전후 조회 범위에서 관련 Application 충돌 이벤트도 발견되지 않았다.

원문 이벤트는 `queue_origin_interruption_events.json`에 보존했다. 앱/실행 서비스 업데이트 때 launch process tree가 함께 종료된 가능성이 높다. 직접 종료 호출자를 추적한 기록은 없으므로 VISSIM crash나 사용자의 직접 종료를 단정하지 않는다. 앞선3600초 큐 목적지 오류와 구분한다.

`closedloop9000_queue_origin_status.json`의 stale native_running을 명시적 interruption으로 정정했다. 원래 상태는 `closedloop9000_queue_origin_status.before_interruption.json`에 보존했다. 현재 재실행하지 않았고 동결 모델/설정/결과도 수정하지 않았다.

다음 재실행은 세션 수명에 종속된 장기 실행 방식을 먼저 점검해야 한다. 현재 관측 JSON은 VISSIM 전체 미시 상태 checkpoint가 아니므로3150초에서 동일 궤적으로 재개할 수 있다고 가정하지 않는다. 추가 METANET 계수 보정으로 이 환경 중단을 해결하려 하지 않는다. 목표 ACTIVE, 성능 검증 미완료.

## 실행 수명 분리 및 재시작 — 17:03

기존 `run_closedloop3000.ps1`에 선택적인 `-Detached` 실행만 추가했다. 새 adapter/물리 모델은 없다. 현재 로그인된 사용자 Interactive/Limited 권한의 Windows Task Scheduler가 기존 동결 runner를 즉시 한 번 실행한다. 트리거0, 자동 재시도0, 중복 실행IgnoreNew이며 PowerShell창은 숨긴다. 앱 업데이트 정책은 바꾸지 않았다. XML과 실제 명령은 결과 폴더의 `detached_*.json/.xml`에 보존한다.

- 사전검증: `Codex-VISSIM-sd31-preflight-20260927165650429`, PID12784. 도구 launcher가 종료된 뒤에도 별도로 실행하여16:58:53 `preflight_complete`, LastTaskResult0. 실제 VISSIM은 시작하지 않았다.17:03 성공과 프로세스 종료를 확인하고 이 소유 작업만 등록 해제했다. 이는 독립 부모/실행 확인이며 실제 앱 업데이트를 유발한 내성 시험은 아니다.
- 실제 런: `Codex-VISSIM-sd31-run-20260927170324562`; launcher34368 종료 후 pwsh13332(17:03:25.182809)가 실행 중이며 부모2396은 Schedule서비스다. watchdog38056, cscript37552(17:03:40.256492). 정확한 소유 기록은 `detached_run.json`과 별도 실행 증거를 참조한다.
- 결과: `D:/VISSIM_runs/20260927_sd31_detached9000/sdmpc`; 상태 `closedloop9000_detached_status.json`.17:05:34 확인에서 실제시각150초 및150초 warmup명령 정상 완료를 확인했다. 최초1초 진행은17:04:29.61로 watchdog시작 후 약49초다. VISSIM35308은17:03:42.259737 생성됐으며 COM서비스가 시작한 프로세스이므로 OS부모는1764다. 부모트리만으로 VISSIM소유를 판정하지 않고 기존 watchdog기록을 사용한다. 독립runner/launcher종료 증거는 `D:/VISSIM_runs/20260927_sd31_detached9000/detached_owner_verification.json`에 보존했다. Task상태Running만으로 시뮬레이션 진행을 판정하지 않는다.
- 동결본: `D:/VISSIM_runs/20260927_sd31_queue_origin9000_runtime/frozen/sdmpc31_886a014a_202609271409`. 기존 manifest 검증을 통과했고 수정하지 않았다. seed29, 기존80–90 DSD110망, 제어/관측/계수 동일.
- 완료된 무제어 `D:/VISSIM_runs/20260927_sd31_wiring9000/nc` 재사용.3150초 미완료 결과를 덮어쓰지 않고 SDMPC만0초부터 실행한다.9000초 완료 후 기존 `native_pair1200/analyze_pair.py --closed-loop-9000 --runs-root D:/VISSIM_runs/20260927_sd31_detached9000 --nc-run-dir D:/VISSIM_runs/20260927_sd31_wiring9000/nc --output-dir <I>/closedloop9000_detached_analysis --status-json <I>/closedloop9000_detached_status.json`으로 검증한다.

작업은 반복 예약이 아니다. 종료 후 소유 receipt의 task_name만 확인하여 등록 해제한다. 다른 사용자 프로세스/예약을 변경하거나 이전 중단 런을 자동 재시도하지 않는다. STOP와 기존 소유PID/생성시각300초 최초 진행 watchdog은 그대로 유지한다.

## 종료 후 분석 대기 연결

exec41624 / pwsh25912가 `closedloop9000_detached_analysis_wait.json`에 소유정보를 남기고 대기한다.60초 간격으로 위의 정확한 Windows task와 runner PID/생성시각만 읽으며 출력·COM조회·FZP분석·모델계산은 하지 않는다. task종료0 + native9000완료 + 소유VISSIM종료 + STOP부재 + analyzer소스해시불변을 확인한 뒤 기존 analyzer를 실행하고, 그다음 캐시 기반 공간/명령 진단을 한 번 실행한다. 결과는 `closedloop9000_detached_analysis/`, 로그는 `closedloop9000_detached_analysis.log` 및 `closedloop9000_detached_cached.log`다. 성공 후 완료된 소유Windows task만 등록 해제한다. 분석 완료도 이득/목표 완료 판정은 아니다.

후속 goal turn은 이 handle을 우선 대기하고, 중복 분석을 시작하지 않는다. exec41624 소실 시 native task는 독립적으로 계속될 수 있으므로 실제 task/소유PID를 먼저 확인한다. 대기 프로세스 종료만으로 시뮬레이션을 재시작하지 않는다.

## 재실행의 실제 통과 확인 — 20:40 이후

새 런에서 `action_003150.json.applied`와 `action_003600.json.applied`를 확인했다. 앱 업데이트 때 중단됐던3150초와 더 앞선 런의 큐 목적지 오류가 발생했던3600초를 모두 지나 실제4350초 관측까지 진행했다. 마지막 완료 명령은4200초(20:40:05)다. 근거는 새 결과 폴더의 native runlog와 `decisions_sdmpc31_sdmpc9000_s29/` 적용 기록이며, 실행·분석대기 exec41624도 실제 live 확인했다. 이는 해당 실행 구간의 통과 증거이고, 실제 앱 업데이트 재현 시험·9000초 완료·이득 검증 완료를 뜻하지 않는다. 동결 모델/설정은 그대로 유지했다.
