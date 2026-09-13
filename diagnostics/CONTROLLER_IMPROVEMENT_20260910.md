# Controller 10% 개선 실험 진행

사용자 요청으로 controller 적용·진단·수정·5400초 검증을 재개한다. 10% 개선의 우선 지표는 Ω TTT이며, 선정 무제어와 같은 망·수요·seed를 사용한다. TTD·삭제·미삽입·Ω밖 체류도 함께 확인한다. 다른 수요의 TTT 차이를 controller 개선으로 계산하지 않는다.

최신 주 시험은 fw070_urban040이며 잠금 기준은 control_improvement/benchmark.json이다. TTT1938.9770833333293 veh·h에 대한 10% 문턱은1745.079375 veh·h다. 기존 fw070_urban030은 낮은 부하 대조로 보존한다. 이 변경은 사용자 도시30% 우려와 추가 무제어 결과에 따른 것이며, 아직 controller 결과를 보고 수요를 고른 것이 아니다.

사용자가 도시 입력30%가 너무 적지 않은지 질문했다. 기존 adaptive sweep에는70/40과70/50이 없어30%가필수임을 입증하지못했다는 점을 명시했다. 네트워크와 FW70을 고정하고 두 조건을 추가 확인한다. 기존30%결과·선정기록은역사자료로보존하며, 낮은도시수요가신호배분/차로접근문제를가릴가능성을검토한다.

- fw070_urban040: native5400/exit0/자연종료 완료. TTT1938.9770833333293, TTD17228, Ωend805, 삭제96(inside63),미삽입0,unknown181. E7/E8정체는종료전회복하나329후반9→7 감소는normalnet−11/native삭제13이다.127은139→73,normalnet66,소멸0.
- fw070_urban050: native5400/exit0/자연종료 완료. TTT2278.256805555557,TD18684,Ωend1065,삭제127(inside95),미삽입0,unknown206. E6–E8정체는종료전풀렸으나329는마지막900초41→46,normalnet−28/native삭제23이고326은53→61대증가. 원점204설정행외 geometry/route비율/SIG변경없음.

현재 controller 기준후보는 contract_candidate_configs_v4/n7_area_beta0.json의 새수요선언연결사본이다. β0의TTT목표와β300효과를섞지않는다. 최종실행변환·Ω재평가·writer검사는있지만fullgreen/offset의공동재방문과19owner최종candidate-gap는아직통합되지않았다. 첫실런은현재구현의baseline이며,all-lever GNE완성본으로명명하지않는다.

실제 VISSIM 실행은 root만 담당한다. 현재 실행 중인 VISSIM은 없다. native 런 도중 대형 FZP 분석·모델 추적은 수행하지 않는다.

## r01 초기 실패 보존

`codex_selected_fw070_u040_beta0_r01`: 수요204행 설정과 native 첫 step은완료했으나 t1의 no-control 초기모형구성에서 shared_approach의구profilepin으로실패했다. watchdog1, 소유VISSIM4744 자연종료확인. 제어성능결과가아니다. `failure_assessment.json` 및모든원출력보존. shared69 미래수요선언도새profile로명시연결후기록초기상태에서검증하고r02를시작한다.

## r02 실제 제어 실행

`codex_selected_fw070_u040_beta0_r02`는 동일한 70/40 수요에서 5400초를 완주하고 정상 종료했다. shared/native 입력의 미래 수요 선언을 모두 새 profile에 연결한 뒤 parameter 검증과 r01의 실제 초기 상태를 이용한 no-control 검증을 통과했다. 실제 r02의 t1 명령과 사전 검증 CSV는 바이트까지 같다. 빠른 무제어의 74개 주소와 비교해 VSL 66개는 120, 미터 8개는 녹색 10초로 일치한다. `meter`와 `ramp_meter`라는 파일 간 종류 이름의 차이는 정규화하여 비교했다. 증거는 `selected_control_preflight/r02/t1_physical_command_comparison.json`이다.

900초의 첫 제어 계산은 126.23초에 정상 완료했다. 실행 중 코드와 설정을 고정했다. 종료 후 동일 수요 무제어와 비교한 Ω TTT는 1938.977→1828.880 veh·h로 5.68% 감소했고 TTD는 17228→17287이었다. 70/40의 10% 문턱까지 83.801 veh·h가 남는다. Ω 밖 체류는 5.103 veh·h 증가했고, 71번 도로 삭제는 3→19대, 329번 도로 종료 시 정지 차량은 0→19대여서 전체 합계만으로 회복을 인증하지 않는다. 개선은 127·10481에 집중됐다. [완료 결과와 공간 진단](control_improvement/r02_fw070_urban040_aggregate_review.md)에 원자료와 한계를 보존했다. 이 결과는 모든 레버의 GNE 완성이나 원래 70/30 목표 달성의 증거가 아니다.

도시 입력 30%에 관한 추가 질문의 답: 최초 탐색은 성긴 적응적 탐색이며 30%의 필요성 또는 최적성을 입증하지 못했다. 같은 고속도로 70%에서 도시 40%와 50%를 추가 완주한 후, 제어 결과를 보기 전에 40%를 주 시험으로 고정했다. `demand_sweep/selection.json`과 `demand_sweep/DECISION_20260910.md`의 30% 선택은 이전 단계 기록이며 최신 잠금 기준은 위 `control_improvement/benchmark.json`이다. 도시 배율은 도시 외부 입력 32개에 적용하며 고속도로 기원 차량의 도시 진출까지 같은 배율로 줄이지 않는다.

활성 goal의 원래 70/30 수치 기준도 별도로 보존한다. 그 조건의 무제어 TTT는 1688.3473611111062 veh·h이고 10% 문턱은 1519.512625 veh·h다. 70/40 결과를 이 수치와 비교하거나 70/30에서 개선을 입증한 것처럼 표시하지 않는다. 70/40의 현 제어 실험이 끝나면 유효 후보의 70/30 재현 여부도 확인하여 원래 요청의 비교 범위를 잃지 않는다.

## 실행 최적화의 짧은 검증 완료

사용자의 추가 5400초 런 불필요 지시에 따라 COM 최적화는 고정 signal·ramp 각각 1200초, 폐루프 1050초의 old/new 비교로 검증했다. 기존 정본 runner·watchdog을 수정했으며 필수 1초 head 이력과 제어 조건을 유지했다. 세 비교 모두 순서 있는 FZP 데이터 행, 명령과 필요한 관측 이력, 실제 적용 시 readback이 대조 범위에서 일치했다. 폐루프의 계측 지점 COM 호출은 344096→250372회, 전체 경과시간은 563.374→522.400초였다. 단일 쌍의 결과이며 controller 계산 최적화나 10% 교통 개선으로 해석하지 않는다.

Native LSA가 COM 소유 신호·미터의 전환과 초기 적용 상태를 충분히 기록하지 않아 사용자 요구의 사후 검증 gate는 FAIL이다. 명령 CSV로 누락을 채우지 않았고, selected trial 기본 설정 채택은 보류했다. 유효·실패 런을 모두 보존했다. [실행 검증 결과](com_execution_equivalence/RESULTS.md)에 시간 분해와 범위가 있다. COM 검증을 위한 추가 풀 런은 하지 않는다.

## 미터 모델 표현 진단

보존된 r02의 t900 상태로 두 번의 450초 고정 명령 모델 평가만 수행했다. 같은 8개 미터 완전 개방 명령을 합계 5416.228 또는 기존 모델 상한 7200 veh/h로 표현하면 첫 10초 R_F_W 방출이 1484.532→1800 veh/h, Ω 예측 비용이 163.038149→163.027277 veh·h로 달라졌다. 물리 CSV의 주소·값 multiset은 같으며 직렬화 메타데이터는 다르다. [모델 진단 원본](control_improvement/open_meter_alias_t900_before_v1.json)은 실차 개선 실험이 아니다.

완전 개방의 모델 표현을 통일하려면 후보 생성·국소/전역 방출·가격 평가·leader/follower 수량 예산을 함께 맞춰야 한다. 채점 후 합계를 5416에서 7200으로 올리는 사후 수정은 적용하지 않았다. 이번 실행 최적화의 범위에서는 목적함수·물리 모델·후보 범위를 바꾸지 않는다. 모델 수정과 full-vector follower 통합은 별도 미완료 작업으로 남는다.

## 고정 후보 준비·평가 함수 구현

후속 작업에서 기존 meter finalizer에 예산 검사를 포함한 명시적 canonical candidate API를 추가했다. 고정7200 예산 아래 서로 다른 완전 개방 입력이 동일한 물리 명령·450초 모델 상태/유량/비용을 내는 것을 실제 저장 상태로 확인했다. 원래5416 예산은 cap/equality 모두 거부한다. legacy solver/가격 dispatch는 아직 이 API를 쓰지 않으므로 전체 alias 수선 완료로 표시하지 않는다.

기존 FW 국소 계산에서 고정 VSL+meter 한 후보 평가를 추출했고, 공통 Ω endpoint에는 선택적 accepted transfer/stock residence 응답을 연결했다. 응답 ON/OFF의450초 모델 비교는 상태·유량·비용 exact,34410개 accepted 사건의 TTT/TTD 재구성 오차0이다.63개 관련 검사와 파라미터 검사 PASS. [구현·검증·미완료 범위](control_improvement/fixed_candidate_preparation_v1.md)에 자세한 근거를 보존했다. 이 단계에서 새 VISSIM 런은 하지 않았다. 원래70/30 목표 및 최종19-owner 공동 follower/가격 연결은 계속 미완료다.

## 공동 응답의 도시부 비용 연결 — 2026-09-11

기존 `area_follower_objective.py`에서 공통 endpoint의 실제 재고·수용된 램프 유입을 17개 도시 owner의 기존 비용식에 전달하도록 연결했다. 이를 위해 선택적 residence 기록에 Ω 안팎을 합친 물리 재고를 별도로 담았다. Ω TTT 정의는 그대로다. 별도 국소 dynamics, 가격·수량 항, solver dispatch는 실행하지 않는다.

저장된 r02 t900에서 기존450초 endpoint 두 팔만 비교했다. FW_E의 자유 VSL head10(셀10–14)을120→100으로 바꾸고 다른 레버·예산·수요를 유지했다. 도시부 SC1001–1005의 국소 비용이 달라졌으며, 합계는41.353429→41.321314였다. 반면 Ω 목적함수는163.038149→163.352384로 악화됐다. 이는 공통 응답 전달을 확인한 것이며, VSL 개선 후보를 선택한 결과나 10% 실차 개선 증거가 아니다. [실제 모델 결과](control_improvement/shared_urban_cost_t900_v1.json)에 각 owner 비용과 입력·소스 pin을 보존했다. 미터는 기록 당시 해석을 유지했으며 canonical 예산 인증을 주장하지 않는다.

현재 소스로 응답 OFF/ON을 별도 비교한 [v2 결과](control_improvement/fixed_candidate_response_t900_v2.json)도 세 시점의 물리 상태·cohort·유량·일반 endpoint 출력이 일치하고,34410건의 TTT/TTD/진입 재구성 오차가0이다. 이전 프로세스의 pickle hash 전체와 일치한다고 주장하지 않는다. 현재 두 팔 사이 동치가 검증 범위다. 새 urban/FW 비용과 canonical CSV 행 iterator 관련 결합 검사48개 PASS(1.003초); 테스트 간 모델 import 간섭은 독립 프로세스 검사로 수정했다.

FW 공동 비용 함수는 추가했지만 현재 켜진 virtual blocked-ramp queue의 실제 물리 대응을 정하지 못해 명시적으로 거부한다. 이를0으로 채워 전체19-owner game이 완성됐다고 표시하지 않는다. 이번 작업에는 VISSIM 실행이 없고, COM 검증을 위한 추가5400초 런도 하지 않는다.

## 공동 응답의 전체 owner 비용 연결 — 2026-09-11 후속

위 단계에서 미정이었던 FW 접근 대기 항은 명시적으로 선택하는 새 공동 비용 경로에서 실제 목적지별 접근 재고로 정의했다. 이동 중인 잔여 cohort도 포함하며, 아직 생성되지 않은 차량은 제외한다. 기존 가상 blocked queue와 같은 함수라는 주장은 하지 않는다. 기존 실행 경로는 그대로이며, 향후 한계 외부비용의 유한차분에도 이 새 국소 비용을 일관되게 사용해야 한다.

[저장 상태 v3 결과](control_improvement/shared_owner_cost_t900_v3.json)는 r02 t900에서 기존 명령과 FW_E head10의 VSL120→100 두 후보를 각각450초 평가했다. 동일한 공통 예측 응답에서 도시17개와 FW2개, 전체19개 owner 비용을 계산했고 초기 상태·명령 및45개 Tf 프레임의 물리 재고를 검증했다. 다른 초기 상태를 같은 응답에 연결하는 시도는 거부했다. 전체 목적함수163.038149→163.352384로 이 VSL 변경은 개선 후보가 아니다. 최종 제어를 선택하거나 VISSIM에서 검증한 결과는 아니다.

고정 가격·수량 계산도 연결했으나 이번 실제 모델 검사는 가격과 dual이 비활성인 대수 검사다. 가격 재계산·한계 외부비용·공동 best response·leader 갱신을 검증한 것으로 해석하지 않는다. 실제 서비스 수량은 전체356개 movement를 검증하고, 제어251개를17개 owner에 배정하며 나머지105개의 동적 서비스는 별도 보존한다. 비제어 movement를 모두 제어 owner에 배정하려던 [v2 실패](control_improvement/shared_owner_cost_t900_v2.json)도 보존했다.

공유 head·수용 공간의 기존 할당 지점에서 각 후보11070건의 가용량/실제 수용량을 기록했다. 최대 초과량은 부동소수점 오차 범위인2.22e-16대였으나, 다른 모듈의 native/10634 자원 등은 아직 포괄하지 않아 전체 공유 제약 인증은 false다. 기록을 위해 물리 할당이나 수요를 변경하지 않았다.

최신 [응답 OFF/ON v3 비교](control_improvement/fixed_candidate_response_t900_v3.json)는 완료됐고 같은 프로세스 내 물리 상태·유량이 정확히 일치했다.34410건의 accepted transfer에서 TTT·TTD·진입량 재구성 오차는 모두0이다. 관련 결합 검사160개 PASS. 이 비교의 전체 경과시간27.797초는 저장 상태의 모델 검증 시간이며 VISSIM 실행 단축률이 아니다.

사용자의 최신 지시대로 COM 최적화를 위한 추가5400초 런은 하지 않는다. 지금까지의 짧은 실제 VISSIM 비교와 저장 상태 모델 비교를 구분해 보존한다. Native LSA 포괄성, 공동 game의 최종 실행 연결, 실제10% 교통 개선은 여전히 미완료다. 최종 성능 후보의 혼잡·회복 및 원래70/30 목표를 판정할 때만 필요한 전체 시간 구간을 실행한다.

## 공통 예측 재사용·일치하는 외부효과 계산 — 2026-09-11 후속

기존 `area_follower_objective.py`에 한 배치 안에서 같은 전체 action을 한 번만 예측하는 `evaluate_shared_owner_batch`를 추가했다. follower/config·초기 상태·참조 명령·수요를 복사하며, 성공·실패 모두 adapter 진단 누계를 복원한다. 물리적 미터 별칭은 모델 동치가 증명되지 않아 캐시에서 합치지 않는다. 원시 전체 궤적 대신 국소 비용·실제 서비스 수량·회계와 원응답 토큰을 보관하고 배치 사이에 재사용하지 않는다. 기존 solver dispatch와 기본 실행 설정은 바뀌지 않았다.

`area_leader_objective.py`의 새 `matched_external_secant`는 같은 공통 응답의 `ΔJΩ−ΔCi`를 실제 제어 변화량으로 나눈다. 가격·dual·β를 국소 비용에서 다시 빼지 않는다. 정본 CSV 행에서 얻은19개 owner 물리 토큰과 전체 모델 제어값을 모두 대조하며, 다른 owner의 모델 미터율이 같은 all-GREEN 물리 별칭 안에서 변하는 경우도 거부한다. full-phase 교환의 합 보존과 실제 offset 주기를 검사하지만 독립 per-phase gradient나 gauge는 만들지 않는다. 따라서 외부효과의 방향별 유한차분이지, 완성된 가격 갱신이나 GNE 인증은 아니다.

[실제 저장 상태 배치 v3](control_improvement/shared_owner_batch_t900_v3.json)는 기존 r02 70/40 t900 상태·450초 지평을 유지했다. 기존 명령 A와 동일한 FW_E VSL 변경 B를 A/B/A/B로 요청해 endpoint2회·cache hit2회를 확인했다.19개 국소 비용·Ω 회계·accepted 수량은 개별 평가와 exact이며 원입력과 adapter 진단도 보존됐다. 배치의 endpoint 시간4.715초, 채점/기록 시간0.299초, 캐시에 보관한 key와 직렬화 결과191822바이트다. 전체 프로세스38.250초에는 원자료 검증·설정 구성·별도 두 기준 평가가 포함되므로 일반 controller 속도 향상률로 해석하지 않는다.

같은 두 응답의 ΔJΩ=+0.3142341581, ΔC_FW_E=+0.3393395579, 외부효과 차이=−0.02510539984 veh·h다. 실제 VSL 변화−20km/h에 대한 방향 secant는+0.001255269992 veh·h/(km/h)다. 이 외부효과 이득보다 국소 손실이 커서 VSL 변경은 전체 목적함수를 악화시킨다. 이 가격을 실제 공동 game에 적용하거나 최종 후보를 선택한 결과는 아니다. 원래70/30 목표의 성능 증거로 쓰지 않는다.

정본 neighbor 모듈에는 기존 VSL·meter 후보 원천을 연결했다. VSL 앵커는 현재 incumbent, meter 이동 상자의 앵커는 이전 실제 명령이다. 둘을 혼동하면 다음 sweep의 VSL 후보를 부당하게 제한하므로 별도 회귀로 확인했다. 이웃은 명시한 유한 held-action 범위이며 기존 시간별 VSL sequence 탐색 전체와 동치라고 주장하지 않는다. [도메인 인계](current_freeway_domain_installed_v1/handoff.md)에 분기·필터·한계가 있다.

## SC11 기존 모델 예산 불일치와 기록 범위 정정

새 자원 기록을 실제 상태에 적용한 [첫 실패](control_improvement/shared_owner_batch_t900_v1.json)와 [상세 실패](control_improvement/shared_owner_batch_t900_v2_failed_resource.json)를 보존했다.925–930초에 SC11 p3의 reference budget은0.5736961451대지만 W0.5736961451+N0.2868480726대가 방류됐고 추가 left 통과는0이었다. 현재 W/N/left 용량은 각각413.0612245/206.5306122/206.5306122 veh/h다.

세 경로가 같은 상류 SG6 두 차로를 지나는 것은 기하로 확인했다. 그러나 현재 예산은 상류 SG6 실측치가 아니라 하류 left movement 용량×2×p3 녹색비율이며, 현재 W/N 방류와 같은 시각의 상류 통과를 같게 취급하는 근사다. 기존 source contract도 W/N이 이 reference를 초과할 수 있고 left에는 잔여만 주는 정책을 명시한다. 따라서 새 기록이 이 proxy 합계를 기존 allocator의 강제 한도처럼 검사한 것은 잘못이었다. 그 기록은 실제로 강제되는 left 잔여예산/수용량 검사로 정정했으며, 물리 배분·용량·수요는 바꾸지 않았다. W/N 불일치와 상류 capacity/통과시각 대응 미검증은 해결되지 않았다.

완료된 두 후보 모두450초의 reference overdraw1.6742342342대를 그대로 보고한다. 실제 할당/eligibility 기록은각30511건이며,SC8 timing eligibility는 포화용량 검증으로 해석하지 않는다. 부분 기록의 최대 초과는2.22e-16대지만 전체 공유 용량 인증은 계속false다. 이 문제를 기록 항목에서 지워서 해소한 것으로 표시하지 않는다.

최종 [OFF/ON v4](control_improvement/fixed_candidate_response_t900_v4.json)는 실제 저장 상태의 물리 상태·유량 exact,34410건의 TTT/TTD/진입 재구성 오차0을 확인했다. 결합 회귀186개 PASS(5.191초), residual tag 관련9개 별도 PASS. 이번에는 실제 VISSIM 프로세스나 추가5400초 런을 실행하지 않았다. 다음 공동 solve 연결에는 남은 자원·모형 타당성, 실제 가격 갱신과 leader/dual 문맥, 최종 실행 명령 불변 검증이 필요하다.

## 고정 문맥 공동 선택 연결과 실제 예산 게이트 — 2026-09-11 후속

기존 follower 모듈에 `solve_fixed_shared_game`을 연결했다. 정본 19-owner 후보·writer 콜백, 공통 응답의 국소 비용/accepted 수량, 고정 외부가격·dual, 구현된 모델 한도 검사를 함께 사용한다. 한 solve 안에서 전체 action이 정확히 같은 경우만 예측을 재사용한다. 모든 owner의 최종 유한 후보 검사가 끝나야 조건부 certificate를 내며, 시간·평가 예산 중단이나 기록 누락이면 gap을 null로 남긴다. 마지막 직렬화는 action 사본을 사용하고 전체 action 불변을 확인한다. 실제 controller dispatch와 기본 설정은 아직 이 경로로 전환하지 않았다.

Runtime query scope는 진단 누계뿐 아니라 lane/segment 문맥도 복원한다. 설치된 `_PHASE_VECTOR_FOLLOWER['ref']`는 사본으로 대체하지 않고 원래 객체 연결을 유지한다. 가격 helper는 matched secant로 전체 필드를 맞추지만, 현재 equality 미터의 고정합 tangent에 대한 gauge는 아직 미구현이다. 활성 가격을 알아낼 수 없는 경우 0으로 채우지 않는다.

[실제 OFF/ON v5](control_improvement/fixed_candidate_response_t900_v5_model_constraints.json)는 기존 r02 70/40 t900,450초 지평에서 상태·유량·일반 endpoint 출력을 정확히 보존했고34410건의 TTT/TTD/진입 재구성 오차는0이다(전체33.453초). [공통 배치 v4](control_improvement/shared_owner_batch_t900_v4_model_constraints.json)는 A/B/A/B의 실제 endpoint2회·재사용2회이며, 개별 평가와19개 비용·수량·Ω 회계가 exact였다. 각 후보의 구현 모델 allocator 방문1125/1125, allocation106651건, state bound32040건을 확인해 구현된 전이 한도의 조건부 witness는 true다. Native plant fidelity와 전체 물리 용량 certificate는 false다. SC11 참고 예산 overdraw1.6742342342대도 그대로 남는다.

이 배치의 endpoint8.455초/채점0.486초, 전체 프로세스43.516초는 추가 모델 검사 비용을 포함한다. COM 실행 단축이나 controller 계산 개선률로 해석하지 않는다. 실제 입력·소스는 실행 중 변경되지 않았다.

**앞선 `dual` 설명의 범위를 정정한다.** 기존 가격 대수 smoke의 `nuf_mode='dual'`은 진단 함수가 지정한 문맥이었다. 실제 설정으로 구성한 r02는 **NP cap / NUF equality**, leader budget ON, max_nash_iter4이다. [실제 설정 게이트](control_improvement/fixed_shared_game_t900_v1_actual_budget.json)는 기존 목표5416.227623335266veh/h를 보존한 채 실행했다. 같은8개 미터 모두 완전 개방 명령을 canonical near-capacity 모델값으로 표현하면4×1800=7200veh/h이므로 total equality 예산 위반으로 초기 준비가 실패했다(25.438초, 모델 endpoint와 공동 search 시작 전). 실패 자료와 원 명령을 보존했고 예산을 늘리지 않았다.

따라서 실제 저장 상태에서 공동 최종 선택이나 가격 refresh가 완료됐다고 주장하지 않는다. 해결할 것은 leader 후보를 채점하기 **이전**의 실현 가능한 예산 정의/검사, 실제 NP cap 제약, equality tangent 가격이다. 채점 후 meter 합계 또는 leader 목표를 바꿔 해결하지 않는다. 고정가격19-owner 선택·캐시·최종 명령 보존은 합성 전이와 실제 writer를 쓰는 회귀로 검증했다. 최종 결합218 tests PASS(17.254초). 이번에는 VISSIM 또는 추가5400초 런을 시작하지 않았으며, 원래70/30에서10% 실제 교통 개선 목표는 계속 미완료다.


## 실현 가능한 예산·NP cap 연결과 짧은 공동 선택 시험 — 2026-09-11 후속

기존 meter finalizer에 두 방향의 기존 요청 후보를 실제 양자화·writer로 실현하는 `reachable_meter_budgets`를 추가했다. 원래5416.227623335266veh/h equality를 통과시킨 것으로 취급하지 않는다. 저장된70/40 r02 t900의484개 요청 조합은20개 물리/모델 후보이며 고정 방향 비율과 맞는 후보는3개였다. 연결 시험에서는 원래 요청과 가장 가까운7200veh/h를 **모든 채점 전에 새로운 목표로 명시적으로 선택**했다. 이는 leader 목적함수로 고른 최적 예산이나 기록 당시 leader 계산의 재현이 아니다. 네트워크·수요·기본 실행 설정은 바뀌지 않았다.

기존 price helper에는 고정 방향별 NUF equality의 `(theta, -theta)` tangent gauge와 실제17-owner signed inflow 합에 대한 NP cap, 최종4개 meter율 합에 대한 NUF equality 검사를 추가했다. 제약 위반 후보는 가격 벌점으로 대체하지 않고 거부한다. 가격 필드의 이 기능은 회귀로 검사했으며 아래 실제 모델 시험에서는 가격 refresh와 leader/dual 갱신을 하지 않았다. 역사적 warmup 명령의 누락된42개 segment VSL 키는 기존 writer의 실효값을 바꾸지 않고 확장하며, 실제 병합된 actuation 설정을 사용하도록 연결을 정정했다.

[실제 저장 상태 v4](control_improvement/reachable_fixed_game_t900_v4.json)는450초 예측 지평을 그대로 사용했다. 전체268.000초, 게임241.031초에 시간 제한으로 정상 반환했으며 후보 요청44회·endpoint43회·cache hit1회였다. SC1의32개 후보를 검사한 뒤 국소 비용2.4546249694→2.4118506029veh·h인 업데이트1개를 보존했다. SC5 검사 중 제한에 도달했으므로 sweep 완료0회, 전체19-owner 최종 검사 미완료, maximum gap=null, certificate=false다. 프로세스 exit0과 JSON completed=true는 게임 수렴을 뜻하지 않는다.

반환된 부분 후보의 Ω 목적함수는163.0193411025veh·h이며 실제 NP297.9353774306≤cap367.2127894905대, NUF7200=새 목표7200veh/h를 만족한다. 정본 명령213행과 전체 owner 벡터를 반환했으나 이 진단의 metadata는 native 실행용 provenance를 포함하지 않으므로 그대로 VISSIM에 재생할 파일로 취급하지 않는다. 모델 내부 제약 witness와 native plant 타당성도 구분한다. SC11 reference overdraw1.6742342342대는 미해결이다.

실패했던 v1(이전 명령의 segment VSL 누락), v2(원시 tuning과 실효 actuation 혼동), v3(offset experiment 환경 선언 누락)도 보존했다. v4 실행 중 소스 변경은 없었다. 변경 부분의 결합94 tests PASS(1.778초), [receipt](control_improvement/reachable_fixed_game_integration_v1.json)에 명령·소스 hash·결과를 기록했다. 새 VISSIM 또는5400초 런은 시작하지 않았다.

사용자 지시대로 실행 방식 동치는 기존1050/1200초 실제 비교를 재사용하고, COM 소유 SG의 native LSA 누락은 별도의 짧은 전환 구간으로 해결한다. 추가 풀 런은 이 검증에 필요하지 않다. 실제 controller dispatch, matched 가격 갱신, 부분 미터 명령의 과거 write-back 기준 보존, 원래70/30 조건의10% 교통 개선은 계속 미완료다.


## 전체19-owner 실제 외부가격 측정 — 2026-09-11 후속

기존 `area_runtime.py`에 `evaluate_joint_prices`를 연결했다. 각 owner의 기존 정본 실행 후보에서 비용을 보기 전에 순서대로 독립 방향을 선택하고, 같은 공통 응답의 ΔJΩ−ΔCi로 가격을 측정한다. 이 가격 측정용 basis 선택은 follower 후보나 반복 수를 줄이는 변경이 아니다. 도시63개 green/offset 방향과 고속도로6개 VSL 방향, 기준점까지70개 실제450초 endpoint를 평가했다. 전체19개 owner의 활성 가격 좌표가 full rank이고 최대 basis 비용 적합 잔차는2.22e-16veh·h다. 정확한 gradient나 비선형 범위 전체의 선형 정확성을 뜻하지 않는다.

[실제 가격 결과](control_improvement/joint_prices_t900_v1.json)는 기존70/40 r02 t900 상태에서 채점 전 별도로 고른 NUF7200을 사용했다. 각 방향 목표3600=두 meter cap1800의 합이므로 이 leader 후보에서는 두 meter가 모두1800으로 고정된다. 그때만 meter 가격0을 실행 가능 변위가0인 축의 대표값으로 둔다. meter 외부효과가 원래0이라는 추정이 아니며, 더 낮은 budget에서는 움직일 수 있는 meter tangent를 계속 식별해야 한다. 검사하지 않은 가격을0으로 채우지 않는다. 가격 필드와 reference는 반환했지만 production holder 설치·leader 평가·공동 game 재실행은 아직 하지 않았다.

실제 가격 측정의 endpoint315.283초, 채점20.213초, 전체456.890초를 구분해 보존했다.70개 endpoint와 후보 생성·검증·로딩을 포함한 오프라인 측정이며 controller 또는 COM 단축률이 아니다. 실행 중 소스 변화는0이다. 이후 basis의 극소 meter interval 판정을 fitter와 같은 정확한 Fraction 계산으로 맞췄다. 이번정수1800/3600 사례의 고정축 판정은 같으며, 실행된 버전의 source hash는 원 결과에 그대로 남아 있다. [현재 통합 receipt](control_improvement/joint_price_measurement_integration_v1.json)에 변경 범위를 기록했다.

고정 game에서는 이미 복사한 follower/config·초기 상태·reference·forecast를 unique 후보마다 또 깊은 복사하던 부분을 제거했다. public batch의 private copy와 후보 복사, 입력·문맥 변조 검사, 실패시 복원은 유지한다. 원함수와 선택·토큰·가격·제약·호출 순서 exact인 합성 검사에서43후보의 반복 고정 문맥 복사43→1을 확인했다. 실제450초 endpoint 자체의315초 병목을 이 변경이 해소한다고 주장하지 않는다. 실제 solve 시간 비교는 아직 남는다. 관련 결합110 tests PASS(3.548초), 기존 r02 parameter 검사 PASS. 원래70/30의10% 목표는 미완료다.


## 60초 실제 VISSIM: COM 신호의 native LDP 기록 확인 — 2026-09-11

설치된2020 FIXEDTIME 예제의 `scDetRecConf` / `SG_BILD` 설정을 그대로 사용해 기준망 사본의 SC1004:5·SC9103:1·native 대조 SC1:1에만 출력 열을 추가했다. 그3개 설정을 제거하면 나머지 XML 구조가 원망과 exact이며42개 SIG 파일은 hash를 유지했다. 원 기준망을 수정하거나 이 사본을 수요·성능 시나리오로 승격하지 않았다.

[60초 완료 결과](native_signal_record_s13_60_v2/process.json)는 실제SimSec60, exit0, 전체21.219초이고 이 시험 소유 VISSIM은 종료됐다. COM 차량 스캔·수요 setter·controller 계산 없이 고정 전환만 시험했고1초 FZP, LSA, LDP, 오류 기록과 실제 적용 전후/매초 readback을 보존했다. 시작 전 VBScript setter 형식 오류로 실패한v1도 별도 보존했다. watchdog은 기존 정본의 PID+생성시각 확인 cleanup만 재사용하며300초 실제 진행 없음 기준이다.

[사후 검증](native_signal_record_s13_60_v2/verification.json)은 **LDP 3×60=180행 모두 같은 시각 after-step 실제 상태와 exact**, 누락·중복0, COM전환14건 모두 다음 native프레임에서 일치했다. nativeSC1의16초GREEN·47초AMBER·50초RED도 LDP/LSA3건 모두 일치한다. 반면COM전환14건은 LSA의 쓰기시각·다음프레임 모두0건으로, LSA coverage와 종합gate는 계속FAIL이다. LDP값으로 누락된 LSA를 채우지 않았다.

LDP는 현재SimSec의 simulation step 직후/그뒤COM쓰기 전 상태다. t1쓰기직후GREEN은 t2LDP부터 나타나므로 적용 직후 readback은 유지해야 한다. t0 COM읽기의 빈값은 unavailable이며OFF로 해석하지 않았다. 현재 증거는2개COM SG+1개native SG/60초에 한정한다. 전체제어SG, 정상writer의전환시각·초기상태, 기존실행과의FZP동치까지 이 LDP설정으로 검증하기 전에는 기본실행검증방식을 전환하지 않는다. 검증기 오류 반례8개도 통과했다. 추가5400초 런은 없었으며10%교통개선 판정에는 쓰지 않는다.


## 원래70/30 목표의 실행 설정 준비

권위 기준은 `evaluation/runs/fast_nc_fw070_urban030_s13_v1/run.json`의 seed13·실제종료5400·exit0이며, `diagnostics/demand_sweep/fw070_urban030/results/summary.json`은TTT1688.3473611111062veh·h/TD15684/삭제36/unknown120이다. **unknown120의 원인 분류는 미해결**이며 최종TTD/삭제비교에서 제외하고 좋아졌다고 판정하지 않는다.

기존 `prepare_selected_control_demand.py`로 [원래조건 제어설정](selected_control_demand/codex_selected_fw070_u030_beta0_r01/config.json)을 생성했다. network SHA085a10…317와원래204개절대수요를고정하며,200행 float exact/나머지4행 최대4.55e-13vph오차를그대로보고한다.생성profile SHA22470a90e4e00d863350a9d65be5d87e881fa01c7ec79b963001d3020aef4837.새수요선정·전체수요축소가아니라원래goal조건을정본controllerrunner에서재현할파일준비다.실제warmup삽입/FZP동치는아직검증하지않았다.현재70/40모델가격결과를70/30교통성능증거로쓰지않는다.
