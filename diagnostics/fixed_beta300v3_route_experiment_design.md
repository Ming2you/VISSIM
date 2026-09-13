# β300v3 실제 명령을 고정한 물리 경로 실험 준비

우선안은 **기존 `diagnostic-signal-profile`과 기존 watchdog/VBS를 그대로 사용**하는 것이다. 새 adapter나 runner는 만들지 않는다. 실제 β300v3 900초 정책은 VSL 전부120km/h, 물리 meter 8개 전부10초 GREEN/900veh/h여서 기존 신호 진단 프로필의 고정 VSL/meter와 일치한다. 녹색시간과 offset만 해당 실제 정책으로 교체하면 된다. 현재 표준라이브러리 generator와 config/manifest까지 준비했고, 실제 CSV writer·모델·COM·VISSIM은 실행하지 않았다.

## 준비된 자료와 검증 범위

`prepare_fixed_beta300v3_signal_profile.py`는 기존 `signal_profile_config_zero.json`을 템플릿으로 읽고 원본에 쓰지 않는다. 다음 새 파일만 만든다.

- `fixed_beta300v3_900_signal_profile/template.json`: 모델의 Ω/경로/head resource 계약을 명시적으로 끈 기존 진단 프로필 템플릿.
- `frozen_greens.json`: 실제 CSV에서 읽은 17교차로×4현시 녹색시간. 원 action JSON과 모든 값이 같은지 확인했다.
- `config.json`: frozen green SHA, selected SG plan 내용 SHA, 17개 actual writer offset, 빈 delta/relative-shift를 넣은 최종 config.
- `manifest.json`: 입력/출력 SHA, 213행 구성, warmup, 환경 설정, 미검증 항목. generator 재실행은 기존 출력 bytes가 다르면 거부한다.

기준 실행은 `evaluation/runs/codex_contract_beta300_s13_1050_v3_20260910`이다. 원본 CSV/action은 보존했다.

| 항목 | 파일 확인 결과 |
|---|---|
| action900.csv | SHA `becee44cef1cfd96fc0dc7be4be70b3a424210a362f52d87aa9ee70388e9940a`; 213행=VSL66+signal17+signal_sg122+meter8 |
| action900.json | SHA `48d68ceddc7c4fd4431457b5dcf1ba01ce19e946a696c0360faf8942c3cbd34d`; CSV의68greens/17offsets와 값 일치 |
| VSL | 물리66주소 모두120.0km/h. 같은 segment ID가 여러 DSD/차로에 반복되므로 ID 하나를 unique key로 쓰지 않는다. |
| meter | 9101..9108 모두 green10/rate900. 모델4그룹의1800이라는 값만 보고 판단하지 않고8개 물리 행을 확인했다. |
| offset | 11개 nonzero. SC1004=56.25, SC1001=75.0초. 기존 zero profile의 offset0은 이 정책과 다르다. |
| warmup | 1/150/300/450/600/750 CSV 여섯 개 모두74행, SHA `76fb1f0a6a47fe87bbeaff0f7082e2433fa357242052ea25e609211f9297871d`; native urban, VSL120, meter10초 |
| terminal1050 | 원 CSV SHA `8c9cb1d9a86f672661db226b4b0c9efbd905b7df2989ff7091ae33d811979d07`로900과 다르다. 이후 새 정책은 이번150초 비교에 포함하지 않는다. |

이것은 **기록된 원천값 검사**다. generator 초안의 unique ID 검사는 lane별 VSL 반복 ID를 잘못 중복으로 보아 실패했으며, 물리 `(kind,id,dsd_no,sc_no,link,lane)` 주소213개로 바로잡아 통과했다. 원본/생산 문제는 아니었다. 실제 `build_control`/`write_action_csv`의 출력 동치는 아직 실행하지 않았고 manifest에도 pending이다.

## 기존 진단 모드가 거치는 코드

`vissim_stackelberg_adapter.main:12325`는 `configure_runtime`을 호출한 다음 `12576`에서 `diagnostic-signal-profile`을 선택한다. 따라서 controller 이름만 바꿔도 활성 model SHA 계약을 우회하는 것은 아니다. `runtime_setup`의 physical phase/topology, head resource, shared/route-choice/native/SC2001, support 및 Ω 초기화는 설정이 활성일 때 먼저 실행된다. 예를 들어 `route_choice_corridor:296`, `native_internal_input:267`, `sc2001_corridor:74`, `physical_movement_routes:145`는 raw network SHA와 증거를 맞추고, `head_service_resources:45`도 실제 raw network bytes와 증거를 대조한다.

기존 v3/v4 MPC config에 실험 INPX만 바꾸면 이 단계에서 실패하는 것이 맞다. 원본 증거의 SHA만 새 네트워크 값으로 바꾸어 통과시키지 않는다. 준비된 config는 기존 진단 template에 기반하여 이 optional 모델 계약을 끄고, `urban.physical_signal_contract=false`, `urban.shared_local_service_pool=false`, `control_area_objective.enabled=false`, head observation/resource OFF를 명시했다. **물리 고정 명령 진단이며 수정 네트워크의 모델 예측/Ω 목적 정합을 인증하지 않는다.** 기존 shape/mapping/SG-plan 및 VBS CSV 검증은 유지한다.

이 모드는 `diagnostic_signal_profile.fixed_actuation`에서 writer를 `test_only`로 정한다. 그러므로 runner 환경도 `RW_OFFSET_WRITER=test_only`여야 한다. 원 β300 실행의 `experiment`를 그대로 남기면 `offset_promotion.validate_experiment_declaration`의 양쪽 선언 검사 또는 model/writer authority 검사에 걸린다. 여기의 test_only는 **이미 기록된 offset을 명시적인 고정 표로 재생**하는 용도이고 promotion으로 바꾸지 않는다.

profile은 policy/spillback/post-guard 및 meter write-back의 재선택을 건너뛰지만, main:12766의 `build_one_step_prediction`은 여전히 실행한다. 따라서 기존 경로에는 MPC 검색은 없어도 endpoint 예측 시도는 있다. 이번 준비에서는 실행하지 않았다. 앞으로 실행하여 생성된 prediction은 variant 모델 정확도 근거에서 제외한다. 모든 모델 실행도 금지해야 한다면 이 기존 모드만으로는 충족되지 않으므로 별도 변경 계획·검증을 거쳐야 한다.

## root가 할 다음 사전검사

1. 생성 config와 원900자료를 기존 `diagnostic_signal_profile.build_control`→`fixed_actuation`→실제 `write_action_csv`로 통과시킨다. 이 pure-writer 검사에서는 필요한 cfg 생성 범위를 명시하고 전체 MPC는 실행하지 않는다. native/variant raw를 쓰는 실제 main 경로 검사는 그 다음 별도 gate다.
2. 원213행과 새213행을 물리 주소로 join하고 **metadata를 제외한 모든 열**이 같아야 한다. 숫자 문자열 차이는 별도 기록하고 파싱 후 숫자 및 SG schedule을 정확히 대조한다. metadata의 `experiment/physical_signal_contract=1`과 새 `test_only`는 합법적인 진단 차이이므로 전체 CSV bytes 동치라고 주장하지 않는다. 비교 대상으로 green/offset 열만 골라 meter/VSL 또는 SG window 차이를 놓치면 안 된다.
3. 원750 warmup의74행과 진단 config에서 생성한 no-control warmup을 같은 기준으로 검사한다. no-control의 signal/signal_sg 행은0이어야 한다. native SIG는 원본 bytes와 같아야 한다.
4. 기존 fake-COM `test_profile_runner_invocation` 또는 actual CSV consumer 하니스를 사용해 `ApplyActionCsv`의 전체 행 검증·기존 writer·offset표를 확인한다. 소스 복제 adapter를 만들지 않는다. 이후 새 baseline 고정 명령 VISSIM 실행의[900,1050]을 기존 β300 smoke와 대조해 재생 자체를 먼저 검증한다.

검증 전 이 config는 **ready-to-run 또는213행 재현 PASS가 아니다**. 기록값/manifest 생성만 완료했다.

## 향후 실행 경로와 시간 경계

`diagnostics/run_area_beta_trial.ps1`는 network를 정본 Ver2로 고정하고 controller를 wu-link/no-control로 제한하므로 경로 대조용 wrapper로는 맞지 않는다. root는 그 안에서 사용하던 정본 `scripts/run_real_world_single_watchdog_distributed_core17legs4b.ps1`에 명명 인자를 직접 전달하면 된다. `-Adapter`는 지정하지 않아 정본 adapter를 사용한다.

공통 인자는 controller=`diagnostic-signal-profile`, tuning=`diagnostics/fixed_beta300v3_900_signal_profile/config.json`, control interval150, start900, warmup=`no-control`, simPeriod1050, seed13, stateLog30, `-ForceStepwise`, `-MaxAttempts 1`, `-NoGlobalKill`이다. mapping/config는 기존 ver2n21, demand profile은 `ver2_fdsweep_x15_20260907.csv`, scale1, roles와 gate map도 원 β300과 같다. network와 새 run/output 이름만 arm별로 달라야 한다. `-StartupStallSec 300` 및 root의 bounded run 감시 규칙을 유지한다.

필수 환경은 `RW_OFFSET_WRITER=test_only`, `RW_SIGNAL_READBACK_SEC=1`, `RW_SIGNAL_WRITE_ON_CHANGE=0`, `RW_VEHREC_RESOLUTION=1`, `RW_VEHICLE_ROUTES=1`, `RW_QUEUE_COUNTER=1`, `RW_QUEUE_WINDOW=1`; Python 경로는 기존 host runtime이다. 모드/이전실험 환경 누출은 기록·해소하고 `RW_ADAPTER_MODE`는 비운다. mainline SG는 template의 mainline plan과 wrapper 해석을 그대로 사용한다. 모든 arm에서 동일한 환경을 사용한다.

VBS `RunStepwiseMode:642–652`는 step1050을 먼저 실행하고 이전 정책의 post_step1050을 검사한 다음 terminal decision1050을 쓴다. 따라서 한 정책900을1050에도 다시 쓰는 진단 모드는 **[900,1050) 물리 운행과 post_step1050** 비교에 충분하다. immediate1050은 다음 hold에 속하므로 대조에서 제외한다. 이후1050..1200까지 이어가려면 원1050 정책을 포함한 새로운 계약이 필요하다.

현재 1초 readback은 신호/ramp의 immediate와 post_step이다. VSL은 command apply 때 네 class에 write/readback하고 두 class값을 action log에 보존하며 매초 DSD를 되읽지는 않는다. 따라서 “모든 레버 매초 readback”으로 확대해서 말하지 않는다. 신호/ramp는 `signal_readback_cadence.strict_signal_trace(..., start=900,end=1050)`로 실제 예상 SG 전체를 도출하고 exact grid·중복·NaN·불일치를 검사한다. documented 시작 meter 동일 재적용 예외는 원행을 유지한다. VSL66주소는 command log와 class readback을 모두 대조한다.

## 두 네트워크 개입을 분리한다

아직 variant INPX는 생성하지 않았다. 아래는 root의 추후 생성·검증 계약이다.

| arm | 허용되는 XML 변화 | 그대로 보존할 내용 | 주요 비교 |
|---|---|---|---|
| 기준 재생 | 원 Ver2와 완전히 같은 bytes의 별도 실험용 사본 | 모든 route/SG/lane/input/SIG | 기존 β300 900의213행 및 물리 재생 동치부터 검사 |
| 1135 상류9route | 1123:2/1124:1/1125:1만3개 child로 전개, 기존6개 sibling 보존; complete coverage 확인 후1135 제거 여부 명시 | 목적 위치·차종·0초 routing interval·3:1:1 합성 가중치·기존1134와69 input·모든 geometry/lnChgDist/SG | parent×child 실현 목적, 추가 LookAhead 효과 유무, 선택/미도달/제거/검열; same-seed 실현 OD 보존을 가정하지 않음 |
| 10635 lane-change distance | connector10635의 `lnChgDist` 하나만1000→2000 | `lnChgDistIsPerLn=false`, lane71/4→47/3, 양끝 위치, route1126 및 모든 가중치/목적지, Combine/LookAhead, 모든 신호/다른 lane-change 파라미터 | 1126:1의10643→126→10641→71→10635→47 선택 차량의 차로 접근/대기/ERR제거, SG2 head/lane3 방해와 SG5/lane4 서비스 구분 |

10635는 도시47향이고 on-ramp route 전개와 다른 개입이다. 두 변경을 한 번에 넣으면 효과를 분리할 수 없다. 1000→2000은 필요한 차로를 인식하는 거리 파라미터 실험이며 차로 수나 포화용량 변경이 아니다. 모든10635 이용 cohort가 영향을 받을 수 있어4725 한 ID만의 수정으로 표현하지 않는다. 네트워크를0초부터 바꾸면900 이전 경로 선택/정체도 달라질 수 있으므로, 명령 warmup이 같다는 것과 raw900 상태가 같다는 것은 구분한다.

variant마다 새로운 directory의 INPX와 참조 SIG 파일을 사용한다. 상대 `supplyFile` 해석이 같은 파일 bytes를 가리키도록 하고 원 signal programs를 덮어쓰지 않는다. 기존 `prepare_native_offset_network.py`의 원본 bytes pin/사본/변경 범위 검증 관례는 참고할 수 있지만 SIG shift 기능을 호출할 이유는 없다. 별도 manifest에 원본 SHA `085a10c71874e897083c97097af8fa3f1f08da1ef7416fef2f7cfbedabdfc317`, variant SHA, 정확한 XML diff whitelist, 모든 SIG/명령/config/runner SHA를 기록하고 실행 전후 재확인한다. 알려진 variant SHA와 diff가 맞을 때만 root가 실행한다.

원 모델의 route/head evidence, 기존 membership, 원 area/config manifest는 수정하지 않는다. 원 area SHA guard를 느슨하게 만드는 것도 이 물리 진단에 필요하지 않다. 새 output directory는 존재하면 거부하고 과거 run/decision/ERR/FZP를 건드리지 않는다. watchdog의 일반 `Clear-DecisionDir`와 재시도 정리 동작이 있으므로 고유 directory·MaxAttempts1이 특히 필요하다.

## 결과 묶음

각 arm은 준비 manifest/XML diff, 실제 run provenance/선택 network SHA, 원/실제 action CSV와 semantic 비교, SG/ramp 1초 trace와 strict QA, VSL readback, raw/route envelope, FZP/LSA 및 ERR, native 선택 count/physical branch count/미도달·제거·검열 표를 남긴다. 선택은 부모/차종/발생 cohort로, 처리는 connector 진입/route 목적 단면으로 분리한다. 150초 raw route snapshots만으로 모든 차량의 선택을 완전히 보았다고 주장하지 않는다. 더 촘촘한 targeted route capture가 필요하면 별도 수집 계획·검증을 거쳐 보완하고 원 collector를 즉석 변경하지 않는다.

비교 기준과 RNG 제한은 `onramp_early_route_tree_peer_review.md`를 따른다. 이번 준비에서는 큰 FZP를 읽지 않았고 config 산출을 위한 CSV/JSON/소스 파일만 읽었다. 새 generator/template/config/manifest와 이 설계 문서 외에 변경한 파일은 없다.
