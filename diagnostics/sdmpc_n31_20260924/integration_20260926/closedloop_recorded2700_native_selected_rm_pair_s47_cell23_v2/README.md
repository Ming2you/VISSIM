# 선택 명령의 짧은 실제 반응 검증 — 승인한 1회 완료

**2026-09-28 23:49 확인:** native3150초와 사후 검증을 완료하고 소유 프로세스 종료를 확인했다. 실제 Ω TTT−4.969대·시간(−1.067%), 예측−8.083. 실제10490 합류92→94대로 억제되지 않았고, native 전체+미삽입 비용은−0.0947대·시간으로 거의 같았다. 공통 초기 상태·FZP prefix·명령/LDP/readback 통과; LSA 실패 별도 유지. [완료 결과와 한계](RESULT.md), `analysis/completion_review.json`, `completion_receipt.json` 참조. 기존9000 STOP은 유지하며 다음 런은 없다. 아래는 승인·준비 이력이다.

사용자는 “준비한 1회만 실행”을 승인했다. `authorization.json`에 승인 범위를 기록하고 `protocol.json`의 `native_authorization_pending=false`를 반영했다. 기존9000 STOP은 유지한다. 승인 전 프로토콜은 `protocol_before_authorization.json`에 보존했다.

2026-09-28 23:25:55 KST에 실행·사후 검증 작업을 시작했다. 실행 작업 PID는29968이며 생성시각·명령·스크립트 SHA는 `D:/VISSIM_runs/20260928_sd31_selected2700_s47/launch_receipt.json`에 기록했다. 이 시각은 작업 시작이며 실제 simulation 진행 시각과 구분한다. 현재 상태는 같은 폴더의 `job_status.json`, 실제 실행 로그는 `native_launch.log`와 `selected/`에서 확인한다. 동결 runtime은 `D:/VISSIM_runs/20260928_sd31_selected2700_runtime/sdmpc31_886a014a_202609282319`이며 FREEZE 검사가 완료됐다. 새 native 런은 정확히1회이며, 종료 후 기존 분석기로 실행값·동일 초기 상태·TTT·램프 반응을 검증하고 종료한다. 재시도나 후속 런은 없다.

제안은 **seed47,3150초짜리 새 런1회**다. 이미 완료된 `D:/VISSIM_runs/20260928_rm_observation2700_s47_v3/hold`를 기준으로 재사용한다. 새 런에서는1–2550초의 실제22개 중앞18개 명령 JSON/CSV를 원본 바이트 그대로 재생한다. 도시 신호는2700초 전까지native로 유지하고,2700/2850/3000초부터 검증된 SDMPC 선택의 세 블록을 재생한다.3150초 마지막 명령은 평가 이후의 시간에만 영향을 준다.

선택은 도시 green/offset과10490 RM4/4/5초다.10484는2초를 유지하고 VSL은모두110이다. 망·수요·seed·SimRes10·FZP5초·입구110은 비교 기준과 같다. 협력적 차로 변경 또는 램프 우선권 시험이 아니며, 폐루프 재최적화나9000초 재시작도 아니다.

목적은 현재 plant의 예측 Ω TTT 변화−8.083대·시간을 실제로 검증하는 것이다. 추적 외부 체류를 더한 예측 변화는−0.928이고, 별도 레버 분리에서 RM만의 예측 이득은0.021대·시간으로 작았다. 그러므로 실제 총이득이 나타나도 큰 RM/VSL 효과의 증명으로 해석하지 않는다. 이전 실제 VSL9000은seed29 이득·seed43 손해였고, 공통 초기450초 결과도 대부분 미미하므로 작은 부호에 추가 계수를 맞추는 작업을 멈추고 이 선택 반응 확인을 제안한다.

## 준비 검사

- 기존 정본 `probe_selected_arrival_path.py`의 writer 준비 경로를 재사용했다. 새 optimizer/예측 호출0회, command22개 저장, 첫2700초 CSV의 모든 물리 필드는 실제 선택 writer 출력과 같다. 이후 두 블록도 이미 검증한 예측 명령과 일치한다.
- 기존 `native_pair1200/run_pair.ps1`에 **검증된 완료 baseline이 있을 때 selected1회만 허용**하는 경로를 추가했다. 이전 두arm 경로는 유지한다. baseline summary SHA와 counterfactual/prefix 검증을 요구한다. 제어 시작을2700으로 지정해 이전 도시 신호의 COM 전환을 막는다.
- 실제 watchdog의 `PreflightOnly` 검사 통과: network·manifest·관측 설정·실행 provenance 확인. 출력은 `D:/VISSIM_runs/20260928_sd31_selected2700_s47/selected/preflight.log`다. 사전 검사 시점에는 실제runlog/SIM_DONE/FZP가 없었다.
- 실제VBS `ApplyActionCsv`와 signal writer를 가짜COM으로22회 실행했다. 이전18개 명령은 도시 신호표0개, 이후4개는17개이며, SG 시간창·offset·VSL·RM 계약 검사를 통과했다. `writer_verification.json` 및 `writer_contract/` 참조. 이것은 native LDP나 실제 차량 반응 검증을 대신하지 않는다.
- 첫 가짜COM 검사에서 cscript의 Windows 설정 접근이 샌드박스에 막혔다. `writer_contract_sandbox_failure/`에 보존하고 같은 코드를 허용된 실행 환경에서 통과시켰다. VISSIM 재시도는 없었다.

기존 watchdog으로selected1회만 실행한다. 시작 전 사용자 VISSIM을 건드리지 않으며300초 최초 무진행 watchdog은 해당 런 소유 PID/생성시각에만 적용한다. 종료 후 기존 native verifier로 LDP/readback을 검사하고, 새 FZP의2700초 이전prefix를 완료된hold의 고정 SHA와 대조한다. prefix가 다르면 공통 상태 인과 비교는 실패 처리한다. Ω TTT·정상유출/삭제·미삽입/외부 비용·8램프 도착/합류/대기를 같은 범위에서 비교한다. 기존hold의 완료된 지표와 소규모관측은 재사용하며, 그 원시FZP를 다시 전수분석하지 않는다.

실제 완료·이득 여부는 사후 검증 전까지 미확인이다. 준비 검사를 통과했다고 이득 보정, 실제 SDMPC 이득 또는 전체 목표 완료를 선언하지 않는다. 사후 분석에서는 재사용hold 경로를 명시적으로 연결하며 기존VSL-only 두arm 가정을 그대로 적용하지 않는다.
