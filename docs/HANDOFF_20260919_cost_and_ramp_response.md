# 2026-09-19 인계: 램프 반응·비용 집계·남은 보정

**최신 재개점(작은 상태의 자체 예측 기각):** `diagnostics/demand_sweep/ramp_dsd_20260916_v2/cohort_dynamics_20260920/COMPACT_STATE_PROPAGATION.md`와 `compact_moment_transport_v1/validation.json`을 읽는다. 하류6셀의현재평균/분산/접근상대속도/감속비중/가감속상태를학습하고과거30초유입만으로30초자체예측했다. 결과는혼합적이며일관개선실패. 실제미래보조상태oracle은도움이되지만경계oracle만으로는거의안됨(운영후보아님). 차량이동과모멘트전달을일치시킨후국소변화를재학습한후보도NC/VSL2550에서평균0·양의분산14건을만들어REJECTED_NONREALIZABLE_AUXILIARY_STATE.480보존단계/32exact/16말단exact/15pin통과가물리실패를덮지않는다. 다음은비음수차량집단·속도·보존전이로모멘트가실현가능한표현을검사하며독립선형분산갱신·임의clipping을반복하지않는다. 이는상류제어미연결6셀시험으로450초gain검증아님. 정본/기본config/망/수요/native/commit/push변경없음,자체작업종료,goalactive·NOT_QUALIFIED. 아래는역사적체크포인트다.

**최신 재개점(현재 간격·상대속도·가감속 이력 식별):** `diagnostics/demand_sweep/ramp_dsd_20260916_v2/cohort_dynamics_20260920/CURRENT_GAP_AND_MEMORY.md`, `current_gap_cohort_v2/result.json`, `current_gap_history_v1/validation.json`을 읽는다. NC900–2100초에서만 학습한 조건부 식에 상대속도·간격·직전 가감속을 넣으면 시간검증1초 RMSE5.363→3.385,10초24.699→22.111km/h. 매초실제현재상태로재시작하는식별이며정본METANET/450초gain개선아님. 최초국소초기집단의VSL노출부족을전체초기5,189대로확대검사했고, 이후생성ID는대응시키지않았다. RM/VSL/동시의회복크기와동시손해를여전히과소예측해미채택.19pin·전체학습표재현·과거입력/시간경계반례·기존core4hash검증. 다음은상대속도분포·접근압력·감속재고의작은차로군상태표현과자체갱신검사이며현재조건부표를450초모델처럼붙이지않는다. 새native/production/기본config/망/수요/commit/push변경없음,자체계산종료,goalactive·NOT_QUALIFIED. 아래는역사적체크포인트다.

**최신 재개점(첫 합류 순서·재출발 한계):** `diagnostics/demand_sweep/ramp_dsd_20260916_v2/cohort_dynamics_20260920/MERGE_ORDER_AND_RESTART_LIMITS.md`, `first_merge_response_v2/validation.json`, `restart_response_validation_v1/result.json`을 읽는다. 동일 초기5,189대/기존9열312,712행 검증. 첫10490 반응2410초→본선2418초: 같은 ramp18665가2417→2419초 합류하면서 본선17532와의 순서·간격5.890/103.836m가 바뀌고NC에만 즉시Brake AX.60초 합류량은둘다11대지만cell13–14반응은2460초실제−14.105km/h로뒤집혀단순capacitybonus불가. 고정차로20초pilot은지원범위/오차미달, 평균승용차가속cap은기존하류9,000단계초과0회로비작동. 채택하지않는다. 다음은현재간격·상대속도·합류/차로진입이후감속지속을제어전자료에서식별하고기존손익사례로반증하는작업. 미래합류펄스반복이나전역FD/nu/tau sweep은재개하지않는다. 정본/기본config/망/수요/native런/commit/push변경없음, 자체계산종료, NOT_QUALIFIED·goalactive. 아래 최신 표기는 역사적 체크포인트다.

**최신 재개점(실효 속도식·수송 시간·하류 이득):** `diagnostics/demand_sweep/ramp_dsd_20260916_v2/cohort_dynamics_20260920/CONTEXT_TIME_AND_DOWNSTREAM_GAIN.md`, `diagnostics/demand_sweep/ramp_dsd_20260916_v2/cohort_dynamics_20260920/partition_context_work_v1/verification.json`, `diagnostics/demand_sweep/ramp_dsd_20260916_v2/cohort_dynamics_20260920/transport_step_work_v1/verification.json`을 읽는다. 단일adapter의명시적공간길이와매속도호출segment문맥을수정했고기본비활성이다.1/2초수송은150초제어·10초미터주기·전체요청량을보존한다.32유효450초예측·12전체JSON exact·50+22검사·166pin.1초 RM+.00498/VSL+.04692/동시+.05204로여전히gain실패·미채택.2초도유사하여더짧은step sweep은중단한다. 새보존분해:실제RM합류−15/말단+16대,모델−12.21/−1.20대. 실제본선이득은주로10490합류뒤cell14–20(0-based)에서나오며모델이놓친다. VSL도여러off진입+38을못잡는다. 다음은그하류회복·방출의시공간/차로반응과공통경계예측오차분리다. 원본망/수요/native런/기본config/vendor/commit/push없음,자체작업종료, NOT_QUALIFIED·goal active. 아래는역사적체크포인트다.

**최신 재개점(공간별 이동률·실효 속도 인자):** `diagnostics/demand_sweep/ramp_dsd_20260916_v2/cohort_dynamics_20260920/SPATIAL_EXCHANGE_AND_TIME_RESOLUTION.md`와 `diagnostics/demand_sweep/ramp_dsd_20260916_v2/cohort_dynamics_20260920/partition_exchange_work_v1/verification.json`을 읽는다. 기본 비활성 physical_partition_exchange를 core/harness에 시험했다. 차로 순유입 오차는−34.69→−1.57대(실제+4)로 줄었지만450초 RM−.01401/VSL+.07919/동시+.06547, NC점수3.1343으로 gain 실패·미채택이다.12예측/비활성8전체JSON exact/5412도시보존/1080인터페이스/55pin/48+1검사/parameterPASS. Native 무차로변경270대 중97대가 같은10초 내176m를 통과했고, 제조 수송 반례는1/.5초 적분 수렴을 보였다. 더 우선할 구현 오류도 확인했다: adapter가 분기 앞176m를전체526m로 덮어쓰고 문맥을 소비하여 뒤 계산은다른길이/계수경로를쓴다(speed_context_trace.json). 다음은 매 공간·ODE단계 실효인자정합 수정, 이후 수치적분 비교다. transport_convergence.json은 일정속도 가정실패로무효, v2만유효. 새native/기본config/망/수요/adapter/vendor/commit/push없음,자체계산종료, NOT_QUALIFIED·goal active. 아래는 역사적 체크포인트다.

**최신 재개점(분기 전후 수송 구현):** `diagnostics/demand_sweep/ramp_dsd_20260916_v2/cohort_dynamics_20260920/BRANCH_PARTITION_IMPLEMENTATION.md`와 `diagnostics/demand_sweep/ramp_dsd_20260916_v2/cohort_dynamics_20260920/branch_partition_v1/verification_v4.json`을 읽는다. 기존core/harness에 config 기본 비활성 `physical_branch_partition`을 추가했다. 분기 앞뒤 재고·속도/실제 유량 기반 모멘트를 보존한다. 첫10초 방출0→3.8547대(실제5) 반례는 개선됐으나450초v4 ΔTTT RM−.01566/VSL+.07216/동시+.05664로gain 실패, NC점수2.6451도 기존2.1642보다 악화해 미채택.45검사(신규9), 도시27계약,16예측·비활성8전체JSON exact·7216보존·1440인터페이스·72pin·parameterPASS. 새native/기본config/망/수요/adapter/vendor/commit/push없음,자체계산종료. 열린3·4차로 분기앞 재고11.16vs실제4.89·속도60.9vs98.2가 남아 수송수량/공간별교환을 먼저 구분한다. NOT_QUALIFIED·goal active. 아래는 역사적 체크포인트다.


**최신 재개점(분기 전후 차단 적용):** `diagnostics/demand_sweep/ramp_dsd_20260916_v2/cohort_dynamics_20260920/BRANCH_POSITION_AND_INTENT.md`와 `diagnostics/demand_sweep/ramp_dsd_20260916_v2/cohort_dynamics_20260920/branch_position_audit_v1/result.json`을 읽는다. 목적지1/6 및 현재 지정 경로를 보강한450초 후보도 gain 실패다(RM−.0164/VSL+.0504/동시+.0341).12예측·4exact·5412보존·1080인터페이스·52pin 검증 완료. 새 native 분석에서2400초10643 분기 뒤2차로5대가 차로변경 없이2403–2408에 나갔으나 모델은같은10초방출0이다. 현재FIFO가분기뒤350m까지적용되는 공간 오류를 확인했다. 다음은 분기 전후 보존 수송 구분이며, 초기값만 분리하거나 전체FIFO를 풀지 않는다. 새native/core/기본config/망/수요/commit/push없음, 자체계산종료, NOT_QUALIFIED·goal active. 아래는 역사적 체크포인트다.


**현재 재개점(수용 공간 비교·반응 경로):** `diagnostics/demand_sweep/ramp_dsd_20260916_v2/cohort_dynamics_20260920/RECEIVING_COMPARISON_AND_CONTROL_PATH.md`와 `urban_route_transport_space_v1/verification.json`을 먼저 읽는다. 공간 비교 조건은NC2차로 방출30.82→27.59대(실제23)를 개선했지만VSL도27.59로 실제30대 반응을 놓쳐 미채택했다.450초5+40초8예측,27계약·45pin·기준JSON4개/NC중복exact. ΔTTT RM−.0208/VSL+.0414/동시+.0208로gain실패. 하류방출2408·본선수용상한2500부터 바뀌나NC 본선cell/flow/lane/ramp기록은 이전과exact로 callback 단절은 아니다. Native19204는2432/2434 진입, 하류2469/2468 도달; 최초로컬차이는 나중의off차로번호전이보다 빠르다. 다음은 binding 수용상한과 진입속도·지연·합류순서 연결이며 도시지연 sweep은 반복하지 않는다. 신규native/core/망/수요/commit/push없음,자체계산종료,NOT_QUALIFIED. 아래는 이전 체크포인트다.

**현재 재개점(차로별 진출 차단):** `diagnostics/demand_sweep/ramp_dsd_20260916_v2/cohort_dynamics_20260920/LANE_BLOCKING_DECISION.md`와 `urban_route_destination_ablation_v1/verification.json`을 먼저 읽는다. 기존 native에서10643 접속2차로의 국소 차단과 다른 차로 통과를 구분했다. 진행우선 변경을10635행/다른행으로 분리한NC450초2건은2차로 방출14.11/30.35대(실제23)로 일관된 개선을 만들지 못해 미채택했다.24계약·902도시보존·180인터페이스·34pin PASS, 선택자 없는 이전 국소450초2개 exact. 고정 폐쇄 계수나 삭제 회복법칙을 넣지 않는다. 신규native/core/망/수요/commit/push없음,이번 자체계산종료,NOT_QUALIFIED. 아래의 최신/active 표기는 이전 체크포인트 기록이다.

**최신 재개점(조기 차로 선택):** `diagnostics/demand_sweep/ramp_dsd_20260916_v2/cohort_dynamics_20260920/COHERENT_BODIES_AND_CHANGE_TIMING.md`와 `urban_route_transport_defer_v1_nc/verification.json`을 먼저 읽는다. 통째 차량25초8예측은 같은 cutoff의 유체4예측보다 낫지 않아 미채택(이전2510 대2523 비교 정정). 원래2510 예측을 정확 추적하니13038의0.969대가2523에4차로 입구에 잘못 묶이고, native는3차로73.39m까지 전진한 뒤 변경한다. 기존수송에진행가능시조기변경을미루는옵션을시험해두정상VSL차량95%진출2533/2535(실제2530/2536)로개선했으나,NC450초10643lane2방출9.026대(실제23,기존30.819)로기각했다. 23계약·기존8짧은JSONexact·451도시/90인터페이스·config동일/pin확인. 다음은공간과FIFO진행을함께고려한변경조건이며항상즉시/일괄지연sweep은반복하지않는다. 원본망/정본core/새native/commit/push없음,모든자체실행종료,목표active·NOT_QUALIFIED. 아래는이전체크포인트다.


**최신 재개점(정상 국소 예측):** `diagnostics/demand_sweep/ramp_dsd_20260916_v2/cohort_dynamics_20260920/LOCAL_RECOVERY_PREDICTION.md`와 `urban_local_recovery_v1/verification.json`을 먼저 읽는다. NC/VSL의2510/2810초에서40초 인과 국소 예측8개 완료. 현재 차량 길이+native간격의 셀 여유공간 조건은NC 두 정상 해제 시점을1초 개선했지만VSL13038/13301 정상2530/2536진출을 여전히 놓쳐 기각했다.2510구간은71삭제0이라 삭제만으로 실패를 설명할 수 없다.20계약·기존4예측160초ledger/trace정확·328도시보존·11pin확인. 다음은71 강제 차로 변경에서 한 차량의 점유/변경완료를 유지하는 국소 표현을 검토한다. 단순 임계값 sweep/45초삭제해제 가정/전체미시복제는 하지 않는다. 정본core/망/수요/새native/commit/push없음,모든자체계산종료,목표active·NOT_QUALIFIED. 아래는 이전 체크포인트다.


**최신 재개점(차로 틈·비정상 해제):** `diagnostics/demand_sweep/ramp_dsd_20260916_v2/cohort_dynamics_20260920/LANE_ACCESS_AND_ABNORMAL_CLEARANCE.md`와 `urban_access_head_outcomes_v2/verification.json`을 읽는다. 현재 차체가 들어갈 전체 틈·전진 여유·진행 중 변경을 구분하는 관측을 추가했다(정본 유량 법칙 아님). NC/VSL 저속·틈 부족 선두차각8대 중 정상진출2/삭제5/잔여1이며 full native hash·경로·ERR로 확인했다.45초 삭제 후 공간 회복을 정상 배수로 보정하지 않는다. nominal6m 때문에 제외했던 VSL63snapshot을 현재 기하 관측에서는 모두 보존한다.7계약·기존14관측exact. 다음은 정상 해제에 한정한 공간 회복/차로별 receiving 법칙 검증이다. 새native/core/망/수요/commit/push없음,모든자체분석종료,목표active·NOT_QUALIFIED. 아래는 이전 체크포인트다.


**현재 재개점(경로 종료·국소 간격):** `diagnostics/demand_sweep/ramp_dsd_20260916_v2/cohort_dynamics_20260920/ROUTING_CONTINUATION_AND_LOCAL_GAPS.md`와 `urban_route_exchange_verification_v1.json`을 먼저 읽는다.1133–2 종료 후ALL connector 진행과126/71 차로 교환을 인과적으로 시험했으나 NC10643 2차로 방출약60대(실제23)로 기각했다. 조각 폭증·첫 조각 크기에 의존하던 합류 배분 수치 결함을 고쳤고 이전25대 근접은30.819대로 정정했다. 다음은 현재 차체/앞뒤 간격/진행 중 차로 변경으로 국소 차단·해제를 검증한다. native head241/206초는 양수 셀 수용량에도 정지 차체 투영 겹침·다음1초 이동0회였으며 VSL63unsupported snapshot/257candidate초는 제외·보존했다.18계약·125pin·7완료NC·3157도시/630인터페이스·parameterPASS. 과거소스는source_before들로pin보존, 모든자체작업종료,신규native/core/망/수요/commit/push없음,목표active·NOT_QUALIFIED. 아래 내용은 이전 체크포인트다.

**현재 재개점(목적지별 차로 결합):** `diagnostics/demand_sweep/ramp_dsd_20260916_v2/cohort_dynamics_20260920/DESTINATION_LANE_COUPLING.md`와 `urban_route_transport_verification_v1.json`이 최신이다.10643 목적지/ID FIFO와126/10641/71 유한 차로 수용을 정본 harness에 진단용으로 연결했다.8causal+4oracle 계산 완료, gain실패로 미채택. 뒤 차량의 lateral 이동을 허용하여 NC2차로 방출5.982→24.995대(실제23)는 개선했지만 VSL도24.995대(실제30)다. 실제 경계유입 oracle도 증가 약1대만 설명한다. 다음은 누락된126의2→1 이동42/43회 및10643 내부교환과 공유 merge 공간이다.126 이동 중35대씩의 현재1133–2 경로는126에서 끝나71 목적지가 미확정이며 임의 배분하지 않는다.10계약·45pin·5,412도시 보존·720인터페이스·parameter PASS, 기존 source_before 아카이브로 소스pin을 보존했다. 이번 신규native/core/기본config/망/수요 변경·commit/push 없음. 모든 계산 종료, 목표active·NOT_QUALIFIED. 아래 '현재/최신'은 이전 단계 기록이다.

**현재 재개점(2026-09-20,현재 목적 경로 확보):** `diagnostics/demand_sweep/ramp_dsd_20260916_v2/cohort_dynamics_20260920/CURRENT_ROUTE_STATE.md`를 먼저 읽는다. 기존 runner로NC/VSL 관측 반복 두 건을3000초까지 완료했으며, 원래10개 궤적 열 각각11,788,963/11,791,383행 전부 동일·LDP/readback PASS다. 개입 전20개 전체 열8,646,345행도 두 조건 간 동일하다. 현재2400초10643 2차로45대 중40대는10635행(71의4·5차로 필요)이고1차로에는0대다. 같은 초기40대의 정상 포트 방출은22→28대, 포트 체류는2,028veh·s 감소했다(Ω TTT/TTD 아님). 미래 경고 없이 현재 경로 관측으로 목적지 재고를 구성할 수 있게 됐다. 다음은 차로별 FIFO·목적지별 보존과71 접근/인접 수용/신호 서비스를 연결한다. 빈 경로는 unknown으로 보존하고 목적 차로 불일치를 곧바로 서비스0으로 두지 않는다. 이 관측 검증은 보정 완료/독립 seed 검증이 아니다. 기존 gain실패는 `CUMULATIVE_BOUNDARY_AND_ROUTE_ACCESS.md`에 보존했다. 정본 core/기본 config/원본 망·수요 변경·commit/push 없음, 모든 실행·분석 종료, 목표active·NOT_QUALIFIED다. 아래의 '최신'은 당시 기록이며 이 문단이 우선한다.

**최신 재개점(2026-09-20,차로 공간·서비스 결합):** `diagnostics/demand_sweep/ramp_dsd_20260916_v2/cohort_dynamics_20260920/OFFRAMP_SPATIAL_SERVICE.md`, `off_spatial_transport_validation_v1.json`, `off_spatial_service_contract_v1.json`을 먼저 읽는다. seed23 현재 위치·차량 길이 기반 10643 두 차로 수송 네 후보는 계산·검증 완료, 모두 NOT_QUALIFIED다. 보존 검사는 통과했으나 추가 지속 방출 시험에서900대/h 입력이600대/h로 줄어드는 직렬 지연 결함을 확인했다. 실제 VSL의2차로 방출23→30대도 고정된 도시 상태 서비스로는 약25대 동일하게 예측한다. 다음은 출구 배수와 공간 회복을 중복하지 않는 작은 경계 검사, 하류126/71 수용·차로 이동 연결이다. 계수/서비스를 올려 오차를 상쇄하거나 실패 native 런을 반복하지 않는다. 이전2초×정지차량수 회복 근거는 `OFFRAMP_QUEUE_RECOVERY.md`에 보존했다. 이번 core/기본 config/원본 망·수요 변경·새 native 실행·commit/push는 없다. 모든 이번 계산 종료, 소유 실행 없음. 목표active, 보정미완료다. 이하의 '최신'은 당시 기록이므로 이 문단이 우선한다.

최신 추가(2026-09-20): `diagnostics/demand_sweep/ramp_dsd_20260916_v2/cohort_dynamics_20260920/MERGE_CONFLICT_POPULATION_AND_GAPS.md`와 `merge10681_conflict_v1/validation/result.json`을 먼저 읽는다. 이전cell9 실제평균유량은합류뒤차량을포함하므로합류전상충유량과다르다는해석수정이있다. 기존두core에선택설정 `physical_ramp_conflict_through_inventory`를추가했으나gain미통과로기본채택하지않았다.127검사·원래12/직전12전체JSON정확재현·후보24forecast/24guard·2160인터페이스검사PASS,guard10/12다. 실제합류점간격은865native사건과일치하며고정3/2초법칙으로seed33집중방출을설명하지못한다. 기준망의10681 conflict area2725는PASSIVE이고SimRes=1이다. 이사실은추종/차로변경제약부재나무제한합류를뜻하지않는다. gap상한만제거한메모리진단12forecast/12guard도11/12guard와gain실패·대기비용과소를남겼다. 수정전소스는 `merge10681_conflict_v1/source_before/`에보존했다. 다음은10643의차로입구차단·회복을현재위치/하류126·71정상배수로검증하고10681방출시각오차를별도로검증한다. 기존실패sweep/런을반복하지않는다. 모든이번계산종료,소유실행없음,신규native0회·망/수요변경없음·commit/push없음. 목표active,보정NOT_QUALIFIED다. 아래는역사적진행기록이며최신해석이우선한다.

이번 인계는 `2c44477` 이후 작업을 보존한다. **새 기하용 단독 진단 MPC의 TTT 집계 오류는 수정했지만, 여러 seed에서 RM/VSL의 순이득을 일관되게 예측하는 보정은 아직 완료하지 못했다.** 이전 full GNE의 제어 정체 원인을 모두 이번 오류로 소급하지 않는다.

## 시작점과 실행 조건

- branch: `codex/control-full-review-20260909`.
- 먼저 [복원 절차](../diagnostics/handoff_20260919/README.md)를 수행한다. 구 패키지와 이번 증분 패키지가 모두 필요하다.
- 이하 `H`는 `diagnostics/demand_sweep/ramp_dsd_20260916_v2`다. 최종 근거는 `H/merge_drain_response_20260919/REPORT.md`, `QUALIFICATION.json` 및 하위 검증 자료다.
- 망: 사용자 가속거리 수정 + 램프 DSD120, 동측 본선 입력1098만 0.8배. `H/source_dsd/baseline.inpx` 및 동봉 SIG/기하 pin을 사용한다. 과거 전역 80/50 조건으로 바꾸지 않는다.
- 실행은 기존 fast runner/writer를 사용한다. ALINEA·규칙 VSL의 실제 결정과 LDP·적용 시 readback, 1초 FZP를 검증했다. LSA의 COM 전환 누락은 사용자 허용에 따라 LDP로 검증하되 기록에 남긴다.
- 이번 마지막 비용 수정 뒤에는 새 VISSIM 런을 하지 않았다. 완료된 native 짝 비교를 재사용했다. 새로운 폐루프 성능 검증은 미완료다.

## 완료한 작업

1. 새 가속 기하·DSD 조건에서 무제어/RM/VSL/동시 제어, 4500초 및 별도 seed 비교를 보존했다. 초기 실패·재시도도 포함한다. 실제 제어 적용 여부와 성능을 분리했다.
2. 기존 METANET의 방향별 계수, 혼잡/회복 및 밀도차 조건, 진입·진출 저장과 배수, 램프 도착 시각·정지선 이후 이동·합류 수용량을 검토했다. 보정과 검증 seed를 구분했다. 구체적인 중간 채택·기각 결과는 `plant_completion_20260919`, `state_response_20260919`, `spatial_calibration_20260919`, `ramp_response_20260919` 보고서에 남겼다.
3. 단독 MPC의 후보 비용이 30초 간격 재고를 적분하던 문제를 고쳤다. `freeway.physical_component_residence=true`는 본선10초·진입램프1초·진출 저장고의 연속 사건 적분으로 내부 체류시간을 합산한다. 미방출·이동 중 차량도 비용에 남는다. 설정이 없으면 기존 결과가 유지된다.
4. seed13/23/33의 두 시점과 세 모델로 총18개 결정을 재현했다. 초기 후보 전부 평가되었으며 시간 예산으로 생략한 후보는 없다. 비용 수정만으로 일부 램프 선택이 바뀌었다.
5. 진출 진입 속도와 가속 시간을 반영하는 선택 설정을 구현·검증했으나, 국소 통과시간 개선이 인과적450초 예측 개선으로 이어지지 않아 기본 후보에서는 제외했다.

## 중요한 결과와 정정

seed33,2400–2850초,10490 RM−무제어의 동측 본선+진입4개+진출4개 connector 비용:

| ΔTTT [veh·h] | 이전30초 표본 | 각 자료의 내부 시간 간격 |
|---|---:|---:|
| VISSIM | −0.266667 | −0.162222 |
| 모델(동일 물리) | +0.010392 | −0.015433 |

이전 “seed33의 세 제어 모두 부호 실패”는 정정한다. 내부 비용으로 RM·동시 제어의 부호는 맞지만 크기는 크게 과소예측하며 VSL은 틀린다. seed23은 여전히 세 후보 모두 부호 실패다. 과거 보고서는 당시 결과로 보존하며 최신 판정은 이 인계와 최종 보고서를 따른다.

seed33의 새 선택은10490에 g8→g6→g4, 다른 미터는 미활성 native OFF, VSL120이다. 기존 완료된 VISSIM RM의 첫450초 계획과 같고 LDP의150초별 녹색120/90/60초도 일치한다. Ω 전체 TTT는426.584028→426.421667veh·h(약0.0381% 감소), TTD는3349→3343, 미확인 내부 소실은37→36이다. 작은 차이와 소실 때문에 강한 성능 개선으로 주장하지 않는다. 기존4500초 전체 RM의 Ω TTT는 오히려8.414veh·h 증가했다. 첫450초 계획 일치는 이후 폐루프 우열 검증이 아니다.

10484 접속 차로 ±100m의 실제 속도는 같은 창에서25.70→28.43km/h, 재고10.94→10.28대로 개선되지만 통과 유량은976→1000veh/h로 늘었다. 평균 유량만 쓰는 gap 수용 상한은 반대로1006.71→997.41veh/h로 낮아졌다. **낮은 평균 본선 유량을 유리한 합류 상태로 단정할 수 없다.** 접속 차로 재고·속도·차량 간격과 도로 전체 평균의 차이를 다음 최소 상태 후보로 검토해야 한다.

## 현재 사용할 진단 모델

`H/merge_drain_response_20260919/decisions_v1/internal_cost/`의 `config.json`, `selected_parameters.json`, `port_profile.json`을 함께 사용한다. 부모 공간 보정 계수와10484 수용 후보도 패키지에 들어 있다. 이는 진단용 component MPC의 후속 시작점이며 최종 성능 정본이라는 뜻이 아니다.

`entry_and_cost`는 진출 가속 후보까지 켠 실험이다. 실제 진입 속도를 준 통과시간 검증은 개선됐으나 모델이 예측한 진입 속도를 쓰는 결합 예측에서는 일부 진출 비용 오차가 커졌다. 후속 기본 설정에 켜지 않는다.

component 범위(본선+on/off connector)와 Ω(고속도로+도시 protected network)를 혼동하지 않는다. TTT는 각 범위 내부 체류시간, Ω TTD는 살아서 non-control area로 나가는 경우를 포함한 정상 유출 사건이다. 내부 이동·비정상 삭제·종료 잔여 차량은 TTD가 아니다.

## 검증과 다음 작업

- 이전 검증:56개 단위 검사 PASS, 기본12개 예측 전체 JSON 일치, 비용만 바꾼12개 셀·유량·램프 물리 기록 정확히 일치, 미래 관측 제거 후 창/예측 일치, parameter 검사 PASS(기존 경고 유지).
- 최종 실행 소스 pin은 `merge_drain_response_20260919/verification_v1/freeze.json` 및 결정별 model pin을 따른다. `causal_v1/freeze.json`은 비용 연결 이전의 역사적 pin이다.
- 이번 전달 검사는 `diagnostics/handoff_20260919/TRANSFER_VALIDATION.md`에 기록한다. raw FZP 없이 복원한 별도 경로에서 검사와 기록 상태450초 예측을 실행한다.

다음 순서:

1. 내부 시간 적분을 고정한 상태에서10484의 접속 차로 재고·속도와 도로 전체 상태를 연결하는 최소 상태를 검토한다. seed23의 RM 이득 과소예측과 VSL 부호 오류를 별도로 확인한다.
2. 실제로 방출량이 변하는 후보끼리 비교한다. 물리/지평/대기 비용/탐색 중 원인을 구분하고, lever를 움직이게 하려는 보상이나 임의 capacity drop을 추가하지 않는다.
3. 유망한 변경만 동일 초기 상태·seed·수요에서 짧은 VISSIM 짝 비교로 확인한다. 이후 필요할 때4500초 및 회복 구간으로 넓힌다. 아직 수행하지 않은10484 대10490 선택 비교와 재계산 폐루프 검증을 구분한다.
4. Ω의 도시 대기까지 포함한 비용과8개 독립 미터·green/offset/VSL의 full GNE 연결은 별도 남은 작업이다. 현재 component MPC를 full GNE 완료로 표시하지 않는다.

새 실런은 기존 사용자 프로세스와 조율하고 한 워크스테이션에서 순차 실행한다. 처음 실제 진행이300초 동안 없을 때 해당 런 소유 프로세스만 정리한다. 이 푸시 작업에서는 실행 중인 프로세스를 건드리지 않았다.

## 이후 로컬 작업: 차로군 이득 예측 후보 — 기본 채택 안 함

사용자의 후속 승인으로 `H/lane_group_response_20260919/REPORT.md`의 차로군 후보를 구현·검증했다. `evaluation/controllers/physical_lane_groups.py`를 기존 component harness에 연결했으며 `freeway.physical_mainline_lane_groups=true`와 현재 차로군 관측을 함께 요구한다. 기본 비활성이고, 기존12개 전체 예측 JSON 및 서측 물리는 정확히 유지된다. 단위 검사71개 PASS.

최종 기록 상태 검증은 `qualification_v6/`, 채택 판정·현재 소스 pin은 `QUALIFICATION.json`이다. 동측 cell5–14의 lane1/lane2/lanes3+ 재고와 수용량, 실제 lane2/3/4→lane1/2/3 연결, 보존되는 출구행 재고를 추가했다. seed13/23 무제어 상태만 보정한 뒤에도 seed23의 실제 RM/VSL ΔTTT −0.553/−0.982veh·h를 +0.008/+0.011로 예측했다. 동시 제어 상호작용과 일부 회복 구간도 실패했다. **NOT_QUALIFIED. 이 후보를 기본 controller plant로 승격하지 않는다.**

새 VISSIM 런은 시작하지 않았다. 완료된 FZP에서 같은 초기 상태4조건을 비교했다. 추가 실측 비교에서는 E7 lane1/2의 VSL 속도 변화 +15.10/+10.71km/h를 모델이 −0.073/−0.090으로 놓쳤다. 다음은 명령이 DSD 통과 차량의 속도·간격 및 접속 차로 방출에 반영되는 국소 반응을 확인할 차례다. 차로군 평균만으로 반응을 표현하기에 부족하다는 결과이며, METANET 전체가 불가능하다는 판정은 아니다.

`H/gain_response_20260919/`에는 그 직전 입력분리·계수·1초 합류 pulse·frozen speed-shape 진단이 있다. 모두 기본 채택하지 않았다. 이 추가 작업은 이전342c869 푸시 이후 로컬 결과이며, 9월19일 기존 전달 패키지에는 포함되지 않는다. 이전 manifest/hash를 현재 편집 소스에 맞춰 덮어쓰지 않았다. 현재 검사는 새 `validate.py`와 `run.py`를 따른다. 기존 config·계수·포트 profile은 계속 `internal_cost/`를 사용한다.

## 2026-09-20 로컬 후속: 표지 적용과 차로 교환 원인 분리

최신 근거는 `H/dsd_response_20260920/REPORT.md`, `QUALIFICATION.json`이다. seed23의 기존 VSL 고정 명령을3000초까지 재실행하며 native FZP에 DESSPEED만 추가했다. 원래9열11,791,383행 정확히 일치, LDP·적용 시 readback PASS. 성공 런은 `native_v2/run_retry1/`이며 종료됐다. 반복 표본이므로 독립 성능 검증으로 세지 않는다.

`evaluation/controllers/desired_speed_transport.py`의 분포 순위 보존 연산으로 실제 희망속도 변경1505건을 모두0.0018km/h 이내에서 재현했다. 이는 액추에이터 연산이며 본선 이동·차로 교환·FD에 연결한 완성 plant가 아니다. native DESSPEED는 위치상 표지 통과보다1프레임 뒤에 기록되므로 `clock_v2/`가 최종 정렬 검증이다. 이를 운전자1초 지연으로 더하지 않는다. `observed_v2/validation.json`의 큰 오차는 정렬 전 값이다.

본선link2의400–1305m에서 VSL은 유입684→683, 유출668→708, 끝 재고83→42로 바뀌며 보존 잔차0이다. 차로 변경366→217,30km/h 미만 차량·초5068→2402다. 진출10643 앞1305–1652m TTT도0.8975veh·h 감소하지만 이후 구간에는 감속 비용이 있다.

실제450초 차로군 이동률을 넣는 원인 분리 진단에서는 seed23 VSL ΔTTT가+0.0106→−0.1088로 바뀌지만 실제−0.9819에는 못 미친다. 미래 자료를 쓴 진단이라 온라인 예측 개선이 아니다. seed13·33 VSL,seed23 RM·동시 제어까지 확인했으며 RM과 상호작용,seed33 구성 비용은 여전히 실패한다. 이득 예측은 **NOT_QUALIFIED**. 기본 config와 full GNE는 변경하지 않았다.

다음은 진출10643 앞에서 제어에 따라 달라지는 차로 교환·접근 재고·막힘을 현재 관측만으로 연결하고, RM10490→10484의 접속 차로 회복을 별도로 검증하는 것이다. 램프 대기 비용을 임의로 낮추거나 VSL 용량 보너스를 주지 않는다. 이 후속 소스/실런은 아직 push·이전 전달 패키지 갱신을 하지 않았다.

## 2026-09-20 후속: 상태 교환 후보 기각·희망속도 분산 반례

최신 근거는 `H/state_exchange_20260920/REPORT.md`, `QUALIFICATION.json`이다. 현재 속도·속도차·밀도로 인접 차로군 이동률을 계산하는 `StateDependentExchange`를 기존 `physical_lane_groups.py`와 component harness에 추가했다. `freeway.physical_lane_exchange_model`이 있을 때만 활성화한다. 무제어seed13/23만 적합했고 미래 상태·교환률은450초 예측에 사용하지 않았다.81검사 PASS, 과거 기본12개+직전 후보12개 전체 예측 JSON 동일, 서측 동일이나 상태 오차 보호 조건은6/12만 통과했다. seed23 RM/VSL 실제 ΔTTT−0.553/−0.982veh·h를+0.0098/+0.0103으로 예측해 **NOT_QUALIFIED, 기본 채택 안 함**이다.

VISSIM 새4회를 기존 fast runner로3000초까지 완료했다. seed23에서 DSD120의 평균만100 분포 평균으로 낮춘 경우, 분산만100 분포 분산으로 줄인 경우, 둘 다 바꾼 경우의2400–2850초 동측 component ΔTTT는 각각−0.409/−1.311/−1.074veh·h다. 기존100 분포는−0.982다. 분산만 바꾸는 조건을 재보정 없이seed33에서 확인했지만 **+0.634veh·h 손해**로 반전됐다. 이4회는 진단용 CDF 실험이며 controller 개선 성과·운영 후보·Ω 지표가 아니다.

새4회 readback/LDP와 개입 전 FZP9열 정확 일치, 첫 DSD 분위수 변환을 확인했다. 모든 조건에서 앞쪽10643 진출 주변만 보면 개선돼도,seed33은10490 주변cell13과 하류link24 cell17/18의2700–2850초 비용 증가가 이를 상쇄했다. 최종 공간 자료는 `dispersion_spatial_v2/`이며 음수 위치로 기록된 입력 차량을 별도 보존해 기존 link 기반 TTT와 합계가 정확히 맞는다. lanes3+로 묶인3↔4 이동이 모델 교환 상태에 보이지 않는 한계도 확인했지만, 그 이동 감소 자체는 양seed에서 공통이므로 일반적인 이득 보너스로 쓸 수 없다.

다음은 검증한 DSD 분위수 전달을 실제 동역학에 연결할 최소 상태를 검토하고, 국소 이득과 하류 손실을 동시에 맞추는 것이다. RM은 seed23의 본선 회복 크기 과소예측을 별도 확인한다. 현재 상태 교환 후보를 확정본으로 쓰지 말고, 기본 모델은 `internal_cost/`를 유지한다. 소스·런 자료는 로컬 보존했으며 이번 후속 작업의 push·전달 패키지 갱신은 하지 않았다. 이전 manifest를 현재 소스에 맞춰 덮어쓰지 않는다.

## 2026-09-20 계속 작업: 셀 안 진출·진입 위치와 새 seed43

최신 작업은 `H/cohort_dynamics_20260920/REPORT.md`와 `PLAN.md`를 읽는다. 사용자는 이득 예측 보정이 검증을 통과할 때까지 진단→수정→확인을 계속하라고 요청했다. **목표는 active, 아직 완료 아님.** 이번 후속도 commit/push하지 않았다.

해당 폴더의 최종 `port_travel_fit_qualification_v1/verification.json`: 96개 단위/회귀 검사, 기본12개+직전12개 예측 JSON 동일, 보존 PASS. 무제어 상태 보호는8/12이고 seed23 RM/VSL ΔTTT 예측−0.03996/+0.02560veh·h로 실제−0.55333/−0.98194를 충분히 재현하지 못했다. 후보 기본 채택 금지, 단독 MPC 기준은 여전히 `internal_cost`다.

발견한 실제 기하 차이는 같은 약500m 셀 안에 진출이 먼저, 진입이 나중에 있다는 것이다. 특히10483 진출 직후10490 진입은 셀13 끝까지91.44m만 남는다. 모든 차량에 전체 셀 길이와 동일 진출비율을 적용하던 근사를, 선택적 `physical_port_travel_lengths`에서 같은 셀의 진입 출처 재고와 실제 이동거리로 구분했다. 미래 목적지는 쓰지 않고 현재 위치·과거 램프 통과 ID로 초기 출처를 관측한다. 현재 후보는 여전히 내부 균일혼합 근사이므로 이 발견만으로 정본이라고 부르지 않는다.

`fresh_s43_v1`의 망·프로토콜·기준/후보 모형은 실런 전 `model_freeze.json`에 고정했다. seed43 무제어·RM10490(g8→6→4)·동측VSL100(DSD51–58)·동시4조건을 기존 fast runner로3000초까지 순차 실행한다. 런 종료·LDP/readback·개입 전2400초 FZP 일치 검사를 먼저 통과해야 해석한다. 실행 중단 시 `*/run/run.json`으로 완료 여부와 소유 PID를 확인하고 유효한 실행을 건드리지 않는다.

후속 명령은 `cohort_dynamics_20260920/fresh_review.py --bank .../fresh_s43_v1 --phase verify`, 기존 `extract_response.py --pairs --runs .../fresh_s43_v1 --nested-runs --component-stocks`, `fresh_review.py ... --phase predict` 순이다. 대용량 추출은 네 native 런이 모두 끝난 뒤에 한다. 평가 구간2400–2850초, 동측 본선+4진입/4진출 connector 비용이며 Ω/full GNE가 아니다. 현재 좌표가 본선 시작점 전인 입력 차량은 별도 열로 보존한다. 상세 단계 상태는 K REPORT의 최신 절을 따른다.

## 2026-09-20 최신: seed43 완료·71 하류 접근/소실 원인 분리

위 seed43 네 런·native 검증·예측 비교는 **모두 완료했다. 재시작하지 않는다.** 고정 후보는VSL 이득/순위를 틀렸고 상태 보호2/3으로 NOT_QUALIFIED다. 원래14개 소스는 `fresh_s43_v1/source_snapshot_v2/manifest.json`과 평탄한 `.txt` 파일로 보존했다. 후속 core 수정 때문에 현재 소스와 옛 model_freeze hash는 다르다. 옛 pin을 덮어쓰거나 지금 코드로 옛 완료 검사를 재실행하지 않는다. 첫 source_snapshot은 긴 경로 오류로 불완전하다.

가장 먼저 `H/cohort_dynamics_20260920/BOUNDARY_IDENTIFICATION.md`를 읽는다. 최신 core 후보는 `port_origin_split_v1/config.json` + `port_travel_fit_v1/selected_parameters.json`,100검사 PASS와 기본12+직전12 결과 동일이나 이득 검증 실패로 미채택이다. 이후 이 체크포인트에서는 진단 코드만 바꿨다. 공간 분할/실측 속도 원인 분리만으로 실패를 해결하지 못했다.

새 관측은10643 진출램프 하류71의 차로 접근 실패를 확인했다.2400–2850초71 비정상 소실은 seed23 NC/VSL10/6대,seed33 NC/spread7/9대다. SC1004 신호는 두 조건에서 같고native와8,408표본 일치한다.4,200초 보존식은 소실을 정상 서비스에서 분리해야 맞는다. component 내부 삭제0이라는 이전 사실만으로 하류 배수가 삭제와 무관하다고 판단하면 안 된다. 동시에 최초 방출 차이는 차등 소실보다 먼저 발생하므로 이득을 전부 소실 탓으로 단정하지 않는다.

사용자에게 별도 시험망에서71 접근/경로를 정리할지, 현재 망을 유지하고 정상 응답·비정상 소실을 분리해 검증할지 **범위 선택 질문을 보냈고 아직 답변 전**이다. 원본 망과 수요·목적지 비율을 바꾸지 않았다. 네트워크 수정/새 native 런에 의존하지 않는 후속 자료 검증은 완료했다. 목표 active, 완료 아님. 이 시점 소유 실행 프로세스/백그라운드 작업은 없다. 새 commit/push도 없다. 이후 답변이 도착하면 이 대기 기록보다 우선한다.

## 2026-09-20 RM 독립 분석 추가

최신 체크포인트는 `H/cohort_dynamics_20260920/RM_RESPONSE_IDENTIFICATION.md`다. 망 선택 답변을 기다리는 동안 기존RM seed23/33/43의component 경계·초기/신규 차량군·램프별 비용을 검증했다.6개 native 회계와720개port 재고 대조가 통과했다.23/33의 본선 입력 시각 항은0이므로 RM 미예측을 source 차이로 설명할 수 없다.33의10484 체류 감소−0.23583veh·h는 모델−0.00163으로 거의 놓쳤지만23은 이 포트 비용이 증가한다. 고정 이득 보너스는 부적절하다.

말단 상한을 푸는 오프라인 시험은 무제어 상태12/12 보호를 통과해도 이득 예측을 개선하지 못해 채택하지 않았다. 실제 미래 속도를 대입한 추가RM 진단도 전체 모델의 부정확한 유량/재고 문제를 해결하지 못했다.부분 하류 속도 대체의 총량 일치는 상쇄 가능성이 있어 성공으로 부르지 않는다. 원인 분리용 미래 관측을 운영 예측에 넣지 않았다. 이번 변경은진단 코드/문서뿐, core·망·수요는 그대로이며 신규VISSIM 런/commit/push 없음. `rm_diagnostic_validation_v1.json` 검증PASS, 이득예측은 여전히NOT_QUALIFIED다.71 망 선택 질문은 아직 답변 전이다.

## 2026-09-20 추가: 국소 합류 후보 기각·71 수정 범위 감사 완료

`H/cohort_dynamics_20260920/LOCAL_CLEARANCE_AND_NETWORK_CHOICE.md`가 최신이다. 조건부 합류 공급에 속도·공간 시간을 넣은 후보,50m 국소 관측 반복, 실제 gap 시간순서 후보를 무제어seed13만으로 선택해 기존23/33 RM에 대조했다. 모두 이득 크기/방향을 일관되게 설명하지 못해 core에 채택하지 않았다. 미래 실제 상태/정지선 통과를 준 원인 분리 시험이며450초 인과 예측으로 부르지 않는다. `clearance_validation_v1.json`에서 자료·보존·학습 재현 검증PASS지만 이득예측은NOT_QUALIFIED다.

71은 이미lane change distance9,999m와경로 미리 보기가 설정돼 있다.도시10640은71의4·5차로에 들어와우회전하려면약34m 안에최소3개 차로를 옮겨야 한다.경로 정보만 상류로 옮기는 것으로 이 연결이 해결되지는 않는다.공식VISSIM2020 문서도 확인했고,일반 정적 route를하류 decision이항상 덮어쓴다는 가정을 배제했다.읽기 전용`route71_readonly_v1.json`에정확한 접근 관계와69 입력의6구간 설정 목적지 비율을 보존했다.

이 단계의 독립 진단/감사는 완료했고소유 실행 작업은 없다.다음검증의 기준망을고정하려는기존질문(별도71 수정 시험망 또는현망유지·정상/비정상 영향분리)이연속목표턴에서답변없이남아있다.미완료를완료로표시하지않으며,범위선택답변전에는망수정/기준망전환을하지않는다.목표상태는실제goal 도구의반환값을참조한다.신규VISSIM 런·core 변경·commit·push 없음.


## 2026-09-20 추가: input1101 수요90%·80% 무제어 시험 완료

사용자가 회전 제거보다 상류 vehicle input 감소를 우선하도록 방향을 바꿨다. 좌·우회전, connector와 route는 제거하지 않았다. 최신 근거는 `H/cohort_dynamics_20260920/input1101_sweep_v1/REPORT.md`와 `validation.json`이다. 기존무제어seed23 3000초를 기준으로 input1101/link69의6개volume만0.9/0.8배한별도망을 기존fast_nc_run.ps1로각각3000초 실행했고 둘 다완료·native검증PASS다. 원본·다른입력·신호·기하·DSD·미터·core/config은유지했다. 실행시간은각180.60/172.31초. 현재소유VISSIM 실행은없다.

1800–2850초71의평균정지차량은기준22.15→90%19.82→80%20.82대,비정상손실15→12→12대였다.10643 평균재고53.04→37.12→52.17대로단조개선하지않았고3000초잔여47/45/48대라회복완료가아니다.90%는1800초초기재고부터낮으므로방출능력향상으로단정하지않는다.기준71이용536건중1101출신67건(12.5%),본선입력1098출신255건(47.6%)이다.입력1101감소는on-ramp행도함께줄이며71전체수요를동일비율로줄이지않는다.설정수요표·출신추적·FZP/ERR/LSA/LDP와실패항목을보존했다.두조건외추가런/정본승격/commit/push없음.이전망선택보류문서는역사기록이며현재는회전보존·수요민감도시험을완료한상태다.이득예측보정과fullGNE는여전히미완료다.


## 2026-09-20 후속: 도시 수용 상태·차로 배수·초기 진출 의도 진단

최신은 `H/cohort_dynamics_20260920/URBAN_RECEIVING_FINDINGS.md`다. 직전 input1101 시험은 새 근거를 얻은 progress이며 기존망을 기준으로 보정을 계속했다. 신규 VISSIM 런 없이 기존 NC seed13만으로10초10643 정상 방출을 적합했다. 현재 차로 대기/속도·하류 상태로다른 기록조건 RMSE13–29% 개선, 비음수 녹색·지연 제약 후보8–19% 개선이나450초 이득 보정은 아니다. 단순 현재상태 고정 배수를 정본 component harness에 넣어도본선/진입 상태와순이득은 그대로였다.10643의 기존차로별 저장을연결해도gain은실패했다. 후보는기본에채택하지않았다.

현재진출 대기비율과과거통과비율도다르다. seed23 cell8현재 진출행6대를모델2.7523대로추정하지만,정확한초기목적지까지준진단도VSL이득을복원하지못했다.추적에쓴미래차량경로는oracle로분리했고온라인입력이아니다.다음은분기상류의목적지별재고·차로분포·이동시각의동역학이다.배수계수만더훑거나gain보너스를넣지않는다. `urban_receiving_validation_v1.json`:반복포함기준예측24개정확재현,64개보존·서측불변,core해시불변.원본망·수요·production설정/코드·과거결과를유지했고실행중인소유프로세스는없다.보정NOT_QUALIFIED,목표active,새commit/push없음.


## 2026-09-20 후속: 상류 진출 목적지 재고 수정, 후보 기각

최신은 `H/cohort_dynamics_20260920/UPSTREAM_INTENT_AND_RECEIVING.md`다. 기존 `physical_lane_groups.py`/`canonical_harness.py`에 `freeway.physical_upstream_exit_inventory` 선택 설정을 추가했다. 첫 진출10643의 설정 비율1/6을 이용해 초기 목적지 재고와 실제 수락된 입장·종방향·차로 이동·진출을 보존한다. 기본은 비활성, 다른 포트보다 먼저 있는 첫 출구에만 적용한다. 새7개 포함107검사PASS, 기본12+직전12+설정비율12 전체 예측JSON동일,48개 비교예측 보존/서측불변, 목적지 보존 잔차1.35e-13대, parameter검사PASS다. 소스 수정 전 사본은 `upstream_exit_inventory_v1/source_before/`의txt와manifest로 보존했다.

이득은 개선되지 않았다. seed23 RM/VSL 예측−0.03994/+0.01469veh·h, 실제 약−0.55333/−0.99111이다. 직전 미채택 후보 대비 상태 보호10/12로도 실패했다. cell5–8의 실제 초기 진출 목적지를 미래 경로로 확인한oracle진단도 결과가 거의 같았다. oracle은 온라인 입력 아님, 후보 기본 채택 금지, 보정NOT_QUALIFIED다.

새 `off_entry_space_audit_v1/result.json`은10643 lane2 입구6m안 정지차량이 있는30초 표본을13/23/33에서54/34/36건 확인했다. 이때 전체차로 명목 빈자리 중앙값9.17/11.17/10.17대다. 이 관측만으로 유입불가나 capacity를 단정하지 않는다. 기존store는하류방출직후 capacity-stock을수용량으로 써 공간의후방전파지연이없다. 다음은현재위치·차로별입구공간·하류배수의지연을조건부검증한다. 단순용량축소는정지간격중앙값약6m, 최대52대/차로 관측과 충돌할수있어 하지않는다. RM10490–10484 오차는별도이며 첫진출수정으로전체해결을가정하지않는다.

원본망·수요·신호·production 기본설정은변경하지않았다. input1101수요시험보존, 신규VISSIM실행없음, 소유실행세션모두종료. 목표active, 새commit/push없음.

## 2026-09-20 최신: 공간·차체 후보 기각, 말단/속도 결합 오차 확인

최신은 `H/cohort_dynamics_20260920/TERMINAL_AND_SPEED_RESPONSE.md`와 `SPACE_WAVE_AND_LENGTHS.md`다. 보정NOT_QUALIFIED, 목표active. 직전 완료한 seed23 native 길이/차종 추가 관측 `vehicle_lengths_native_v1/run_retry`는3000초 완료이며 원래10열11,788,963행이 정확히 같다.194.38초, 독립 성능 검증 아님. 첫실행 CScript접근거부와 실패로그 보존. 재시작하지 않는다. 현재차체길이·유한공간전달을 각각/함께450초예측에 넣어도 이득은 개선되지 않아 core에 채택하지 않았다.

이번 후속은 신규native런 없이21셀 RM 보존/유량 감사와 기존speed_oracle의 `--open-outlet` 진단 옵션을 추가했다. seed23 마지막cell20은 native10초RMΔTTT−0.34167인데 실제미래속도+기존말단상한 모형은+0.36691이었다. 같은미래속도를준채기존zero-gradient말단을쓰면 본선전체RMΔTTT−0.27989→−0.95307(실제1초−0.87972),VSL−0.42838→−0.78819(실제−0.86139)다. 변경된재고/유량셀은20뿐,진입·진출connector결과는완전히같다. seed33분산만축소는본선−0.22694→+0.40504(실제+0.93528)로방향이돌아왔다. 분산축소는VSL100과다르고source변동도있다.

이는미래속도진단이며보정성공이아니다. 미래속도없는열린말단시험은이미실패했고10484대기반응오차도남는다. 다음은실제자유말단기하에맞는출구조건에서하류15–20셀까지 causal속도·방출반응을검증하고10490→10484합류시각을별도개선하는것이다. 말단용량숫자를이득에맞추거나 진출모형복잡도를계속늘리지않는다. `terminal_response_validation_v1.json`:공간5검사,과거pin,RM기본4개전체JSON정확재현,8쌍의서측/connector불변,보존/비음수/저장검사PASS. 검증첫경로오류보존. core·기본config·망·수요변경없음,새commit/push없음. 이번도구실행은전부종료됐고VISSIM없음을확인했다. 다른Python프로세스는건드리지않았다.


## 2026-09-20 최신: 직접10484 native 반응과 합류 혼잡 오차

최신은 `H/cohort_dynamics_20260920/DIRECT10484_FINDINGS.md`다. 직전열린말단속도재적합/하류차로분리는 `OPEN_OUTLET_CAUSAL_CHECKS.md`에기각·검증완료로정리했다. established모델대비state guard는open reference/차로분리10/12,scalarfit2/12,regimefit3/12다. 이전12/12는직전미채택후보대비였음을구분한다.36새예측보존/서측불변,12기준전체JSON일치,parameter검사PASS지만gain실패다.

`direct10484_s23_v1`은10484/SC9108만2400부터g8→6→4로제어해3000초완료했다(193.656초). 원래수요이며1101감소망이아니다. 준비망byte동일,실행전예측고정,120명령readback/600SG표본검증,2400초까지8,646,345FZP행일치다. 현재소유프로세스없음. native450초동측component ΔTTT−0.458889인데기준+0.008984/open후보+0.003666으로이득을놓쳤다.10484합류97→86,자체대기비용+0.409167,본선−0.878889다.본선입력시각항0·component삭제0이며말단15대추가통과시간항−0.449167로순이득대부분을설명한다.

공간분석에서합류cell14마지막150초평균속도실제42.16→64.24km/h,모형80.18→81.96이다.상류유입예측부족만의문제가아니며2550–2700상류202대/예측201.38인데방출207/예측232.30이다.실제미래10484도착을준분리시험도순이득−0.02848정도로실패했다.첫반응은초기차량19383이cell14의2421초부터하류로전달한것으로확인한다.개입후새차량의같은숫자ID는다른생성차량일수있어초기cohort외개별매칭은증거로쓰지않는다.

다음은cell14의실효FD/완화/anticipation/합류항및방출을NC혼잡형성구간에서검증해근거있는국소보정을선택하고,기존450초gain/state suite와새10484조건에반증하는것이다.더큰전역계수sweep/임의capacity보너스/미래관측온라인사용은하지않는다.기본core/config승격없음,새commit/push없음.목표active,보정NOT_QUALIFIED이며fullGNE/Ω성과가아니다.이번런·도구작업은전부종료했다.

## 2026-09-20 최신: 직접10484 seed33 손해, 국소 보정 기각

최신 보고서는 `H/cohort_dynamics_20260920/DIRECT10484_REPEAT_AND_LOCAL_CHECKS.md`다. `direct10484_s33_v1`은3000초 정상 완료(189.622초), 실행 전 예측 고정,2400초까지8,606,202 FZP 행 일치,120 명령 readback/600 LDP SG 표본·비대상 신호 검증을 통과했다. 소유 VISSIM은 정상 종료했다. seed23/33 모두10484 합류가11대 줄고 종료 재고가10대 늘지만, 실제450초 component ΔTTT는−0.458889/+0.457500veh h로 반대다. seed33 본선+0.311111, 진입+0.197222, 진출−0.050833이다. cell14는−0.397500으로 개선되지만 상류cell13+0.596111 및 일부 하류 구간이 악화됐다. 본선 입력 수·시각항 동일, component 삭제/미확인 전이0, 말단8대 적게 통과한 시간항+0.543333을 포함한 외부 사건 원장이 총 비용 차이와 맞는다.

모델은 seed33 기준+0.000204/open 후보+0.018023으로 거의0을 예측하고 본선 비용 부호도 틀린다. 단일 총합 부호 일치로 성공 판정하지 않는다. 두 seed의 반대 효과만으로 평균 효과0이나10484 일반 무효를 주장하지 않는다. seed33 NC 상태는 이미 개발에 사용했으므로 미사용 상태 검증도 아니다. `direct10484_two_seed_summary_v1.json`과 각 `validation_summary.json`에 보존했다. 새 공간 비교는 개입 당시 실제 존재한 같은 차량 ID만 개별 매칭하고 전체 비용에는 모든 차량을 포함한다. 서측 차이까지 물리적 혼잡 전파라고 단정하지 않는다.

`downstream_fd_check_v2`는 기존 NC 보정으로39.2가 된 하류15–20 임계밀도를 원래 class28로 되돌린 단일 진단이다. `local_merge_response_v1`은 NC seed23의2400초 이전 자료만으로 cells13/14 tau60초/nu3을 선택했다. 각각 상태 guard9/12·11/12지만 VSL 및 직접10484 이득을 설명하지 못해 모두 기각했다. 후자10초 속도 RMSE도 persistence보다 나쁘다. 각13개 기준 JSON 정확 재현, 서측/보존/비음수/저장·parameter 검사 PASS. 실제 소비된 cell14 속도 항135개/예측을 수식으로 재구성했다. runtime 국소 override는 진단 인스턴스에만 있으며 production config 기능으로 추가하지 않았다. `fd_and_local_response_validation_v1.json` 참조. 수정 전 진단 script는 정확한 `.txt`로 보존했고 과거 pin을 덮어쓰지 않았다.

다음은 실제 합류cell14의 상류·합류 위치·하류를 나눈 작은 보존 수송 식별이다. 과거 격자 진단은 포트 없는 구간만 검사했으므로 이 셀은 제외돼 있었다. 기존 두 seed에서 미래 실측 속도/유입을 쓰는 원인 분리임을 명시하고, 차량 유입·유출·잔여를 모두 보존한다. 이 단계에서 개선되지 않으면 격자 확장이나 큰 계수 탐색을 반복하지 않는다. 유망할 때만 causal 상태·속도법칙과 기존 전체 gain/state 검사로 이어간다. input1101 감소 두 런 완료 자료, 회전 경로·원본 망·기본 설정은 보존, 새 commit/push 없음. 목표 active, 보정 NOT_QUALIFIED, full GNE/Ω 성과 아님.

## 2026-09-20 사용자 추가: 차로별 차단·off-ramp spillback

최신은 `H/cohort_dynamics_20260920/LANE_BLOCKING_AND_OFFRAMP.md`다. 사용자는 차로별로 보고 off-ramp로 인한 차로 폐쇄까지 고려하도록 요청했다. 이를 모델 내 동적 차로 통과 제한으로 검토했으며 VISSIM 실제 차로를 폐쇄하지 않았다. 새 native 런 없이 seed23/33의NC/VSL 네 기록2400–2850초를 조사했다.10643 진출램프 입구 정지와 본선2차로 연속 대기가 함께 있는 표본은172/133초와124/98초다. 같은 시각에 다른 차로는 계속 통과한다. 다른 세 동측 off-ramp에서는 같은 판정의 표본0이나 다른 시점의 spillback 부재를 뜻하지 않는다.71 차로3/4에도 대기가 집중돼 있고 기존 비정상 소실은 정상 방출과 구분한다.

기존 미채택 lane-group/open-outlet 후보의 partial FIFO는 네450초 예측 모두10643 차단0회였다. 총 진출 저장 공급이 요청보다 커 입구2차로 막힘이 제한으로 연결되지 않았다. `lane_blocking_model_audit_v3`는 읽기 전용 추적과4개 전체 예측 JSON 일치다. `lane_blocking_oracle_v2`는 미래 관측 막힘의10초 내 비율을 해당 진출 차로 수용 한계에 넣는 원인 분리다. NC2차로 속도는 seed23 실측22.69/기존41.66/진단19.64, seed33 실측30.96/기존83.92/진단35.88km/h다. 하지만 비차단 차로 속도와 진입·진출 대기 비용이 틀려 VSL total ΔTTT+0.030951/+0.023877로 순이득은 실패했다. 미래 표식은 운영 입력이나 검증된 causal 개선이 아니다.

`lane_blocking_validation_v1.json`:10,800차로 보존,256셀 스냅샷 재고,4개 읽기 전용/4개 비활성 gate 전체 JSON 동일, 활성 gate 서측/보존/비음수/저장 검증PASS. production/core/default config는 그대로다. 기존진단 source hash는 변경 전 `.txt`로 보존했다. 준비/trace 중복/시간 자료형 실패 폴더는 별도 보존했다. 전 파일 FZP hash를 다시 검사한 것이 아니라 기존 사건·스냅샷 및 읽는 중 size/mtime 불변을 확인했다.

다음 우선순위는 현재 차로 queue·입구 위치·알려진 도시 신호·예측 배수로 차단 시작과 회복을 예측하는 연결이다. 물리 차로 수/저장·차량·TTT·목적지 보존을 유지하며, 한 lane 막힘을 전체 본선 폐쇄로 번지게 하거나 목적지를 자동 변경하지 않는다. 기존cell14 수송 진단은 보존하되 이 사용자 지시를 우선 포함한다. 새VISSIM/core승격/commit/push 없음. 이번 진단 실행은 모두종료, 목표active, 보정NOT_QUALIFIED다.


## 2026-09-20 후속: 차로별 막힘과 열린 차로 속도 검증

최신은 `H/cohort_dynamics_20260920/LANE_BOUNDARY_AND_SPEED.md`다. 이번 오프라인 진단은 모두 완료, 소유 실행 세션 없음. 신규VISSIM·망/수요/production core/default 변경·commit/push는 없다. 목표active, gain NOT_QUALIFIED다.

`phase_drainage_v1`에서 직전150초10643 차로별 정상 방출을10초로 나눠 반복했다. 기존 평균432/144(seed23),480/120(seed33)veh/h 유지, 미래 절단 입력 동일. 일정 배수 대비 이득 변화가 거의 없고 유한파 조합도 실패해 채택하지 않았다. 관측 방출 패턴은 포화능력이나 향후 도시 상태 예측이 아니다.24예측 보존/서측/저장 검증,8개 전체JSON 반복 일치다.

`lane_speed_terms_v2`는 실제 속도 계산1,620개를 재구성했다. cell8 열린3·4차로 NC실측104.94/110.13 대비 예측84.92/89.21km/h이며,VSL100이 평형속도를 제한하는 step은0/45와3/45였다. aggregate 진출 복합부 rho_crit20이 열린 차로에도 쓰이며 과잉 재고,하류anticipation 및차로혼합도 함께 작용한다. v1은 시작재고와 교환후속도로 요약했으므로 v2만 속도 대조에 쓴다.

`lane_fd_class_check_v2`는 일반4차로의 기존rho_crit25를7–9cell의 열린3·4차로 평형속도에만 넣은 단일 식별 시험이다. 물리capacity까지 보정한FD가 아니다. NC예측99.20/100.68,VSL95.41/96.48로 개선되나VSLΔTTT+0.075920/+0.110678이고 무제어guard10/12라 기각했다. 최초v1은기존desired observer 때문에유효호출0개를 assertion이 탐지한실패이며소스/protocol보존.12개비활성 전체JSON일치,12개활성 보존PASS.

`lane_blocking_combined_v1`은 위평형속도와미래실측막힘을결합한oracle이다. NC막힘차로·열린차로속도는같이좋아지지만VSL합계+0.084323/+0.091212veh h로실패다. seed23본선−0.277366을진입+0.122783·진출+0.238906이상쇄하며 실제−0.991111과다르다. 미래막힘은온라인입력아님. `lane_boundary_speed_validation_v1.json`에20기준JSON일치·16변경예측보존·과거소스pin보존을확인했다. 변경전`lane_blocking_response.py`는`lane_blocking_oracle_v2/source_before_combined.txt`로원hash를보존했으므로옛pin을현재진단파일에대조하지않는다.

다음은cell8–9와10490–10484의차로별진출/직진/합류수량과방출시각을대기비용으로연결해남은오차를좁힌다. 같은배수주기/전역계수sweep을반복하지않는다. 동적차로차단은현재queue·입구위치·알려진신호/예측수용으로계산하고차량·목적지·저장·TTT를보존해야한다. 기존cell14공간수송분리와RM양seed반대손익검증도계속유지한다. 국소속도개선을전체gain검증통과로세지않는다.

## 2026-09-20 최신: 램프 차로 전달 수정·내부 차로 이동 누락 확인

최신은 `H/cohort_dynamics_20260920/LANE_COUPLING_AND_RAMP_EXCHANGE.md`와 `ramp_lane_followup_validation_v1.json`이다. 원래 망/수요로 기존 결과만 분석했고 새native 런은 없다. 목표active, 보정NOT_QUALIFIED, 소유 실행 세션은 모두 종료했다. commit/push 없음.

기존 `physical_ramp_boundary.py`, `physical_lane_groups.py`, `canonical_harness.py`에 config `freeway.physical_ramp_lane_coupling`을 추가했다.10681의 실제 차로별 합류를 계산하고도 본선/출처 재고에서50:50으로 다시 나누던 결합을 수정한다. 명시적 차로별 수용예산과 실제 수락량을 대응 본선group으로 전달하며 기존총합상한·gap계수는 유지한다. 후보설정은 `ramp_lane_coupling_v1/evaluation/config.json`, 매핑10681→[0,1]이다. 기본설정은 비활성이다.113검사·parameter검사PASS, 기존비활성12전체JSON일치,1080차로인터페이스/보존/서측불변검증PASS다. 실제기능에맞게metadata를추가수정했고12전체JSON은그metadata차이만있음을재실행해확인했다. 이전hash는 `ramp_lane_coupling_v1/source_before`와 `source_before_metadata`에있다. 이전pin을현재core로덮어쓰지않는다.

그러나무제어guard10/12,seed23 RM/VSL 예측−0.02083/+0.02505,seed33−0.01773/+0.05043veh h로이득실패다. 기본모델채택금지. 새native1초추적으로10681의1→2차로순이동을NC/VSL seed23 21/15대,seed33 13/14대확인했다. 대부분신호두상류다.1차로끝50m에는정지차량표본이없지만2차로는각382/383,230/195초대기한다. 낮은1차로합류를용량부족으로간주해임의폐쇄하면틀린다.3728개차로회계검증과기존port사건정확일치. 현재독립램프buffer는이내부차로이동을아직표현하지않는다.

`port_arrival_response_v1`의15360native재고대조와입장/합류시간가중분해도완료했다. 실제미래도착을준진단도이득을못복원한다. `merge_cell_transport_v1`은실제10484합류위치로cell14를1/2/4공간분할한보존수송진단이다. 미래속도·수락된유량을주면단일공간도두seed국소이득을맞추고세분화는주로절대재고를개선한다.5400차로보존/64셀재고대조PASS이나인과예측·수용능력qualification아님. 둘다새production기능이아니다.

다음은10681의신호두전후단계/차로별이동을남은주행시간·저장·TTT와함께보존하는최소수정의필요성을검증하는것이다. 먼저차로별수량/시각/대기비용을맞추고기존450초gain/state및손해반례로넓힌다. 별도로10643의차로별입구차단·회복을현재관측과예측배수로연결해야한다. 실제관측미래차단이나낮은차로방출을상수폐쇄로바꾸지않는다. 이번인터페이스수정만으로차로이동이나off-ramp차단을해결했다고주장하지않는다.

## 2026-09-20 최신: 램프 내부 차로 이동 구현, 방출 시각 오차로 범위 축소

최신 보고서는 `H/cohort_dynamics_20260920/RAMP_EXCHANGE_AND_RELEASE_TIMING.md`, 검증 영수증은 `ramp_exchange_v1/validation.json`이다. 직전 턴은 progress였고 이번에도 코드·관측 검증을 완료했다. 목표active, 보정NOT_QUALIFIED다. 신규native 런은0회, 이번 소유 실행 세션은 모두 종료했고 commit/push는 하지 않았다.

기존 `physical_ramp_boundary.py`의1초 진행 루프를 generator로 공유하고, `canonical_harness.py`의 선택 설정 `freeway.physical_ramp_lane_exchange`로10681의 인접 차로 이동을 연결했다. 신호두 전/후 단계, 남은ETA, 단계/차로 저장, 차량 수와TTT를 보존하고, 이동을 입장·합류로 중복 계상하지 않는다. 차로별1초 도착 프로필도 명시적으로 검증한다. 기본은 비활성이다. 후보는 `ramp_exchange_v1/evaluation/config.json`이고, 이동률은NC seed13 900–2100초만으로 산정했다. 제어 이득에 맞춘 계수 조정은 없다. 단계 내 동질 이동/합계 공간이라는 근사이며 미시적 gap 접근 가능성을 보장한 모델은 아니다.

123검사, Python -O의 신규10검사, parameter검사가 통과했다. 최종 코드로 원래 비활성12개 및 활성12개 전체JSON을 정확히 재현했고,28forecast 보존/저장·2520차로 보존식·1080차로→본선 인터페이스 검증도 통과했다. 그러나 무제어guard는10/12이고 seed23 RM/VSL 예측−0.02035/+0.02534,seed33−0.02145/+0.05231veh h로 이득은 실패했다. 기본 채택 금지. 수정 전source는 `ramp_exchange_v1/source_before`, 차로 도착 프로필 추가 전source는 `source_before_lane_profile`에 hash와 함께 보존했다. 과거pin을 현재 파일로 덮어쓰지 않는다.

실제 미래10681 차로별 도착·단계별 차로 이동비율을 준 원인 분리에서seed33 1차로 합류는NC5.01/VSL7.82로 실제4/7대에 가까워졌다. 하지만2차로는106/106으로 실제127/126대를 과소예측한다. cell9 본선의 실제 차로 평균유량을 gap 기회 계산에 추가해도 약109/105대다. 실제/기존예측 상충유량은비슷해서 평균 유량 오차만으로 부족한 방출을 설명할 수 없다. seed33 실제2차로 방출은150초별 NC53/35/39,VSL42/51/33이고 이 진단은각37/35/37,36/35/35 정도다. seed23은총합이실제와가까워도10681 VSL대기비용의부호가반대다. 미래정보를운영입력이나보정성공으로세지않는다.

다음은10681 대기중2차로의 합류점 실제 통과간격·platoon·양보와 램프 방출 시각을 대조한다. 실제 gap으로도 높은 초기/중기 방출을 설명하지 못하면,고정평균gap계수를다시훑지말고 합류우선권·협조양보·posthead 대기전파를 구분한다. 기존10484 실제gap시험 실패는 보존하되 이 다차로 램프 검증과 혼동하지 않는다. off-ramp10643의 차로별 입구 차단/회복도 별도 미완료다. 국소 수량·시각·대기비용을 개선하는 후보만 gain/state/손해조건/미사용 검증으로 넘기며, 현재 실패 후보로 native4조건을 반복하지 않는다.
# 2026-09-20 최신 추가: 하류 국소 정지와 RM 회복

`diagnostics/demand_sweep/ramp_dsd_20260916_v2/cohort_dynamics_20260920/DOWNSTREAM_LOCAL_STOP_RESPONSE.md`가 최신 체크포인트다. 기존seed23 RM/NC cell14–20의1초 native 재고·차로 정지와 시간별 손익을 대조했다. 평균 밀도에 가려진 정지가 줄지만 손익은 구간·시간에 따라 뒤집힌다. 기존 FD의 밀도 집계만75/100/150m로 바꾸는 조건부1초 검사는 기각했다. 따라서 단순 임계밀도/이진 폐쇄를 추가하지 않고 현재 대기·이동 재고와 간격에 따른 정지 해제/가속을 먼저 식별한다.1932관측·31318개입 전 원래9열·180canonical 평형속도 대조를 완료했다. 새native/정본모델 변경 없음, 자체 계산 모두 종료. **NOT_QUALIFIED, 목표 active**이며 미사용 검증/전체Ω/fullGNE는 미완료다.


## 2026-09-21 latest: positive speed populations and neighbor persistence

See `SPEED_POPULATION_AND_RECOVERY.md` (cohort_dynamics_20260920). The absolute transition kernel's zero-change mixing defect was corrected and archived. Positive speed populations preserve mass/realizable moments but still recover too quickly. Refining acceleration phases does not fix the local30s forecast; conditioning on current mean speed reduces some errors but remains worse than the simpler comparator on key states. Do not promote these candidates or continue broad bin/parameter sweeps. The newest local validation replays64forecasts and1920mass steps; canonical core4files unchanged. Current-state gap/history conditional reaction helps, but native geometric leaders persist only51.9% at10s and19.9% at30s among continuously observed pairs (616initial pairs). A frozen-neighbor rollout is not justified. Next distinguish current native interaction targets from geometric neighbors in same-cohort short-response identification before proposing a causal neighbor-change closure. Off-ramp spillback/ramp waiting, full450s costs/ranking, NC guards, fresh holdout and canonical integration remain outstanding. All owned work terminal; no native/network/default changes or commit/push. Goalactive, NOT_QUALIFIED.
# 최신 안내

2026-09-21 이후 재개는 [최신 모델·이득 예측 인계](HANDOFF_20260921_gain_prediction.md)와 `diagnostics/handoff_20260921/README.md`를 먼저 읽는다. 이 문서 아래의 반복된 최신/현재 문단은 각 시점의 역사적 기록이다.
