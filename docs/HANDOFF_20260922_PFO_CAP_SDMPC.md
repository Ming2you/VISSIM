# 2026-09-22 PFO warm start + budget upper caps 인계

**이번 푸시 범위:** 이 인계 문서와 실측 summary.json만 포함한다. 누적 컨트롤러·검사 도구·config 변경은 자동 승인 검토에서 범위가 크다는 이유로 푸시가 거절되어 위 로컬 worktree에 미커밋 상태로 보존했다. 아래 구현·명령·테스트 경로는 그 로컬 상태를 가리킨다. 원격 checkout에는 아직 새 구현이 없으므로 다음 담당자는 먼저 로컬 변경을 검토하고 기능별 커밋으로 나눠야 한다.

## 최신 합의와 구현

매 control interval마다 현재 plant의 own-cost만 사용하는 무가격 prox-linear PFO를 새로 실행한다. 선택 제어의 현재 450초 예측에서 달성한 NP 및 실제 본선 수용 합류량 NUF를 첫 budget으로 쓴다. 이전 interval budget이나 미터 명령 합을 시작점으로 쓰지 않는다. NP <= cap, NUF <= cap이며 각각 허용오차 1e-7이다. NUF 양측 band와 하한 가격을 제거했다.

`adapter.sdmpc="central-pfo-cap-v3"`로 켠다. 기존 proxlinear-v1 / central-reuse-v2는 보존한다. 새 설정은 `diagnostics/sdmpc_pfo_caps_20260922/config_candidate.json`이다. 상수 출처는 evaluation/parameters.json의 sdmpc_pfo_cap이다. vendor 수정 없음.

원본 WuFaithfulFollower PFO는 가변 길이 기하에서 legacy local freeway solver가 NotImplementedError를 발생시켰다. 사용자가 **현재 plant의 own-cost만 쓰는 무가격 prox-linear PFO**로 연결하기를 명시적으로 선택했다. 이 구현을 원본 Numerical-Sim PFO와 동일하다고 부르면 안 된다. 각 owner QP는 자기 비용 미분만 사용하고, line search merit은 19개 owner 비용 합이며 PASSIVE_OMEGA는 제외한다. 실제 actuator/이동 제한과 plant feasibility는 유지한다. 매 수락 iterate에서 미분을 갱신한다.

PFO의 최종 예측/Jacobian은 물리 제어 불변 및 달성 budget 출처를 검증하는 별도 binding으로 첫 SDMPC iteration에 재사용한다. 임의 NUF 후보는 이 예외로 재사용할 수 없다. budget caps는 QP projection, iteration dual update, 중앙 NNLS 승수, 최종 feasibility gate 모두에 연결했다. 이전 적용 receipt 확인 후 두 비음수 가격만 이어받으며 PFO와 시작 budget은 매 호출 새로 계산한다.

## 완료된 오프라인 실측

900초 저장 상태, H450=150초 독립 제어 3블록, 최대8워커, 시간제한 없음, budget 후보1개.

|계산|시간|iteration 상한/실행/수락|수렴|
|---|---:|---|---|
|PFO|370.711초|2 / 2 / 2|미확인, iteration_limit|
|이후 SDMPC|171.194초|후보1개 × 2 / 2 / 2|미확인, iteration_limit|
|초기화 포함 전체|544.512초|위 PFO와 SDMPC 모두 포함|미확인|

PFO rollout6회, 이후 SDMPC 추가3회, 총9회. PFO→SDMPC 시작 binding은 추가 rollout0회. 첫 budget은 NP564.110352576veh / NUF5216.792302019veh/h로 PFO 달성량과 정확히 일치했다. 최종 NP556.616597613 / NUF5213.646370020으로 상한 둘 다 만족했다. NUF는 8개 램프에서 실제 본선에 수용된 양의 평균율이다.

연속모델 Ω 예측비용: 이전 명령402.318539501 → PFO395.534958967 → SDMPC393.916124584veh·h. 단일 저장 상태의 예측값이며 native 성능 개선율/9000초 결과가 아니다. 중앙 stationarity8.18447로 최적성·수렴 인증 없음. 모델 feasibility, 10개 결정 증거 검사, 실행 중 소스 불변을 확인했다. 이번 작업으로 native VISSIM을 실행하지 않았다.

증거: `diagnostics/sdmpc_pfo_caps_20260922/summary.json`, `decision_v1.log`, `decision_v1/progress.jsonl`. 전체 result.json(약54MB), pickle, request는 로컬 진단 폴더에 보존하며 대용량 출력은 Git에 넣지 않는다. 로컬 실행 루트는 `C:\Users\TRLAB\Documents\ChatGPT\VISSIM\.worktrees\sdmpc-tangent-20260921`이다. 다른 머신에서 재현하려면 같은900초 request.pickle과 bootstrap 경로의 저장 상태/설정을 옮겨야 한다. Git checkout만으로 실행 재현이 완성된다고 주장하지 않는다.

## 다음 할 일: 이 순서대로

1. **신규 테스트 재실행.** cap 및 기존 관련 검사51개 PASS, 초기 연결 회귀67개 PASS, parameters PASS. 이후 확장한 PFO 테스트12개 중8개 통과,4개는 fixture 안 lambda pickle 오류였다. 테스트 fixture의 lambda를 제거했지만 재실행은 자동 승인 서비스 사용량 한도로 차단됐다. 수정 후 통과로 기록하면 안 된다. `diagnostics.test_sdmpc_pfo_caps`부터 재실행하고 아래 전체 관련 suite를 확인한다.
2. **원 actuator 모델 별도 사후 audit.** 이번 새 PFO/cap 결과에는 아직 하지 않았다. 아래 audit 명령의 source는 새 decision_v1로 지정해야 새 policy가 보존된다. 연속-model cap이 원 actuator 모델에서도 만족하는지 정직하게 보고한다. 실패하면 단순히 tolerance를 넓히거나 결과를 PASS로 바꾸지 않는다.
3. **다중 budget 탐색 검증.** 이번 실측은 후보1개라 실제 다음 budget 재최적화는 미검증. PFO 달성량을 center로 두고 상위 후보2개 이상에서 방향·중복방지·상한·가격 기록을 확인한다. signed NP가 옛 NP grid 밖이어도 첫 달성 budget을 clip하지 않는다.
4. **다음 control interval 재초기화 확인.** 새 관측/실제 적용 first block에서 PFO를 다시 실행하고, 이전 future plan·budget은 재사용하지 않는지 확인한다. 가격은 실제 적용 receipt와 정책 hash가 맞을 때만 이어받는다. 오류를 fixed hold 성공으로 바꾸지 않는다.
5. **그 뒤 짧은 native 적용 검증.** 5초 관측 수집 /150초 제어 주기, 8개 물리 meter, green/offset/VSL 명령과 실제 적용 receipt를 확인한다. native 런은 한 대에서 순차 실행한다.
6. **성능·장기 런은 검증 후 판단.** 매 interval PFO2회가370.7초를 더한다. PFO iteration 수를 줄일 경우 별도 config/parameters 실험과 같은 상태 비교가 필요하다. 현재는150초 실시간 계산조건을 충족하지 못한다. 이전 승인된 NC/새기하/기존METANET9000초 비교는 완료되지 않았다. 오래된 heartbeat 감독을 재가동하지 말고 실제 프로세스와 최신 사용자 지시를 확인한다.

RM/VSL 이득 예측은 이전 인계의 NOT_QUALIFIED가 유지된다. 현재 구현 검증과 plant 이득 검증을 구분한다. 계산시간에는 항상 PFO와 SDMPC 각각 iteration 상한/실행/수락/수렴 여부를 함께 적는다.

## 재개 명령

수치 Python은 기존 .review-deps/sdmpc 및 sdmpc-numba, OMP/OPENBLAS/MKL thread1 환경이 필요하다. 출력 폴더는 새 이름을 사용하고 실행 중 소스를 수정하지 않는다.

```powershell
python -B -m unittest diagnostics.test_sdmpc_pfo_caps diagnostics.test_sdmpc_central diagnostics.test_sdmpc_tangent diagnostics.test_sdmpc_reverse diagnostics.test_sdmpc_sequence diagnostics.test_sdmpc_surrogate_reuse diagnostics.test_sdmpc_initial_shared diagnostics.test_sdmpc_hotpath diagnostics.test_shared_joint_price_quantity diagnostics.test_validated_decision_hold
python scripts/verify_parameters.py diagnostics/sdmpc_pfo_caps_20260922/config_candidate.json
python -B diagnostics/measure_sdmpc_pfo_decision.py diagnostics/sdmpc_stream_summary_20260922/hotpath_h3_v1 diagnostics/sdmpc_pfo_caps_20260922/decision_v2 diagnostics/sdmpc_pfo_caps_20260922/config_candidate.json
python -B diagnostics/audit_sdmpc_surrogate.py diagnostics/sdmpc_pfo_caps_20260922 diagnostics/sdmpc_pfo_caps_20260922/decision_v1 diagnostics/sdmpc_pfo_caps_20260922/exact_audit_v1 decision_v1
```

첫 실측 source hash와 현재 source가 달라졌다면 audit을 속여 진행하지 말고 새 decision 측정 및 새 증거를 생성한다. test/doc 추가는 실측 controller source를 변경하지 않았다.
