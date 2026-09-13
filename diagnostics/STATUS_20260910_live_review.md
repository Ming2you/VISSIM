# 제어 검토 진행 상태 — 2026-09-10

**이후 사용자 요청: controller 10% 개선 반복을 재개했다.** 도시30% 우려에 따라 고속도로70% 고정·도시40/50%의 추가 무제어를 완료하고, 첫 controller 결과 전 도시40%를 주 시험으로 지정했다. 현재 기준·문턱은 `control_improvement/benchmark.json`, 진행은 `CONTROLLER_IMPROVEMENT_20260910.md`를 우선한다. 아래 controller 보류 표시는 이전 시점 기록이다.

**최신 우선순위와 결과:** 사용자 요청으로 아래 controller/GNE/예측 추적 및 네트워크 전수 비교를 보류했다. 소유 프로세스만 정리한 뒤 빠른 무제어5400초 수요 탐색을 완료했다. 첫 제어 비교 수요는 고속도로 원점70%·도시 원점30%, seed13이다. 현재 상태는 `demand_sweep/DECISION_20260910.md`와 `demand_sweep/selection.json`을 우선한다. 아래 '실행 중'·'다음 실행'은 과거 시점의 기록이며 재개 지시가 아니다. 과거 유효 결과와 코드 수정은 보존했다.

작업 브랜치는 `codex/control-full-review-20260909`, 작업 폴더는 `.worktrees/control-full-review`다. 시작점은 6056c94이며 주 작업 폴더의 기존 변경과 vendor 원본은 보존했다. 전체 검토는 아직 진행 중이고, 수정 MPC의 가중치 비교와 정본 정리가 남았다.

Ω는 제어 고속도로와 도시 protected network의 합집합이다. TTT는 Ω 내부 체류시간, TTD는 Ω 밖으로 나간 경계 통과 사건이다. 도시↔고속도로 내부 이동은 제외한다. β=0/60/150/300초 후보를 비교하며 가중치는 아직 선택하지 않았다.

## 17시대 사용자 보완: 무제어5400초 비교를 우선

18시대 최신: NC전용config `native_nc5400_config_v1/config.json` SHA851d8e3e…는원201b에서모델hook14개만명시OFF,actuation/수요/망/매핑은유지한다. 실패LCD t1을canonicaladapter로offline검사해74행CSV전체가원NC76fb1f0a…와exact였다. r02baseline는17:48:55 시작→17:57:57 5400완주/exit0. 전체26,693,633행 FZP는원NCpayload2a0747…와exact다. post-run 검사가SIG폴더전체old73 vsflat42를비교하여실패했지만, 실제30845개LSAevent와File/Date제외header는원문bytesexact였다.

검사는INPX의SC별supplyFile2가참조하는실제42SIG를기록provenance와연결하도록고쳤다. 미사용31개를성과에섞지않는다. 옛driver/audit/tests는ZIP에보존했다. r02원failed manifest/lock은변경하지않고 `r02/reviewed_baseline_v1.json` SHA58e012d938203ad3f40120ebbb0b4bbf496eeb9f882ec1d450ecd7e25e99a4f4에서명령/수요/137runtime/원366pins(검사기2개변경만명시예외)/사용SIG/LSA/FZP를재검증했다. `r03`은이실제r02baseline의name/run/command를그대로재사용하고두variant만실행중이다(root session29209). driverSHA dd38a14b44ae446b84cc572b542857e4e9b6b37b6cbd47204fc455ea480df16f, source동결,12회귀PASS. 거리arm은3720초까지진행했다.

완료r01baseline전체분석은 `no_control_5400_baseline_diagnosis_v1/assessment.md`와`no_control_5400_corridors_baseline_v1/diagnosis.md`, E8기전은`nc_r01_e8_onset.md`다. ΩTTT5578.610277778veh*h,TD26203(살아있는outside이동18272+terminal추론7931),unknown398,Nend4670,peak5106@3665초. native486삭제는inside240/outside246,미투입1845. terminal120삭제27349는끝까지4875m남아terminal추론False,4107→4108unknown으로TD오염0. FullE8지속정체1350→E0도달2730,끝5400까지지속. 66의마지막창N301+in101-out100-delete31=N271이라겉보기감소는삭제로설명되며lane4접근실패가남는다. native1124위치는head1265.9m앞이며실제currentroute도충분히앞에서보여단순늦은route정보가설은부족하다.

E8발단의선택60frame12.59MB분석은1350초10682분류직전lane1과입구정지를확인했으나1380/1440에직접branch가풀려도E8저속잔류했다. 10639 through합류와10682exit는136m간격으로같은lane1이며10681은별도branch다. 이희소표본을150초capacity추정으로쓰지않는다. 모델의물리순서/목적지별lane권한과8physicalmeter의독립제어가능성은후속검토중이다.

현재모형의4개150초NC조건부예측은별도 `no_control_5400_baseline_prediction_v1`에완료됐다. 후반E8속도/재고를낙관적으로회복하지만nativeNC SIG와equal-green/offset0 모델action이달라FW모형단독오차로단정하지않는다. liveNoControl에도같은신호미일치경로가있고기존helper flagship True/live False 차이는8MPC필드뿐(network/simulation/urban/freewayfollower같음)이며소비경로검토중이다. 전레버GNE/최종리팩터링은아직미완료다.

17:36:47 r01 baseline5400이466.437초/exit0으로 완주하고 원 NC의26,693,633행·payload SHA2a0747f1…와 정확히 일치했다. 명령1/900의74행, native readback, runtime/source핀도통과했다. 뒤 LCD는17:37:39 t1에서 `physical_movement_routes.configure_phase_authority: Snapshot and phase authority network hashes differ`로 실패했다. 원NC201b의 model evidence가원래망SHA에묶였기때문이며 native첫주행은시작됐지만 full런은아니다. r01은 failed_preserved_stop·거리실패·상류pending 그대로보존, driver session42781 exit1, native/WSH잔존0 확인했다.

단순 evidence SHA 복제는 하지 않는다. sc2001의원 membership하드코딩 및 역사 calibration출처계약도있어 새망모델검증을위조하게된다. 이번 native무제어비교에는 불필요한 선택적 controller-model 준비를 명시OFF한 NC전용config를원201b에서별도생성하기로했다. 74개실제기준명령·VBS·수요·mapping·native관측은유지하고 모델예측은검증근거로사용하지않는다. 새r02에서baseline5400부터다시전체궤적검증할계획이며 이시점아직시작전이다. 기존1050 profile이이modelhook들을OFF했다는범위도재확인했다.

완료r01 baseline의1초전체FZP 공간집계는 `no_control_5400_corridors_baseline_v1/summary.json`에5400frames/172800road bookkeeping closure/source_changes[]로완료했다. source9b35fb12…; road71nativeLSA첫event전신호는unknown으로남기고1초전체crossing bracket GREEN만방출조건으로분류한다. nativeWARN486차로변경삭제, 미투입1098/1099/1105 각각1182/572/91대를기록했다. 삭제중terminal120 차량27349 t4107 pos2082.4는 Ω출구추정과혼동되는지추가점검중이다. 이값들은전체망상태이며모두Ω내부사건이라고단정하지않는다.

17:29:02 `diagnostics/no_control_network_arms/r01`에서 baseline 실제 watchdog/WSH 실행을 시작했고17:29:22 VISSIM15404를 확인했다. 2700초까지 실제 native 시간이 정상 진행 중이다. 새 드라이버 `run_no_control_network_arms.py` SHA d8a480ba6e2da7285b6d41dbada652f1fbbf53a1ba8e069119dd89dcc2e8bb78, 현재359입력핀·7회귀 통과, 독립NC lock을 사용하며 r03 stale lock은 보존한다. 이 기록 시점에는 아직5400완주나세망성능결론을 주장하지 않는다.

사용자가1050초/한 제어창만으로 네트워크 효과를 판단하지 말고 무제어5400초 full run을 요청했다. 원래 망·LCD2000·하류1135 제거/상류분할 세 망을 동일 seed13·수요·native 고정신호/기준 VSL·meter 명령으로 순차 비교한다. SC1004 녹색시점 반사실은 읽기 준비만 보존하고 후순위로 둔다. 전체 Ω 지표,900초 수요창6개,정체 발생·전파·해소 및 차로별 방류를 함께 평가한다.

16:51:50 시작한 새 전체후보 trace는 진행 중 다른 native run과 source를 섞지 않기 위해 중간 기록을 보존하고 우선순위를 변경했다. 정확한 PID36944/parent31104/시작시각을 확인하여 그 trace adapter만 종료했고 부모pair23440도 exit1로종료했다. native VISSIM은 당시0이었다. 이 실행은 timeout이나모형실패가 아니라 사용자full-NC 실험우선에 따른 불완료다. `trace_pair_t900_20260910T075150593308Z/recovery/priority_interruption.json`과 원래 실패기록을 보존했다.

17:13:19에 독립CIM의 Python/VISSIM/cscript/wscript잔존0 확인 뒤 ZIP에서 cached clock9581813…를 복원하고 새runtime137pins 전부일치를 확인했다. VBS는 검증한30a279…를 유지한다. 실제5400 NC는 이 source를 다시 동결하여 실행하며 아직 시작 전이다. 전체 후보 동일성검증·all-lever follower game·최종리팩터링은 여전히 미완료다.

## 16:36 시작 단계 수선 검증

r03 거리 실험은 simulation 첫 step 전 ApplyDemandMultipliers 안에서 `DEMAND_INTERVAL_SET_FAILED no=1097 time_int=1-5 target=0.000000 err=`로 실패했다. 따라서 당시 무진행을 RunSingleStep의 초기화 지연이나 lane-change distance 자체의 영향이라고 단정할 수 없다. 모든 flat 망의 204개 input interval은 동일하고 Cont=false이며 input1097의1-5 원본 수요는112, 배율은1이다.

canonical VBS는 기존 QuickMode/SuspendUpdateGUI 블록을 LoadNet 직후로 이동하고 startup/개별 수요 write 시간을 기록한다. 실패한 Volume 읽기가 SafeAtt→ToDbl 경로에서0이 되던 문제는 strict read/empty/nonnumeric 검사를 통해 중단시킨다. 정상 수요의 모든 write 순서·값·readback은 유지한다. 기존 SHA71ec5f8d… 원문은 `fixtures/startup_gui_original_vbs_v1.zip`에 보관했고 새 SHA는30a279cb…다. fake 회귀6/6, child cscript10개 종료를 확인했다(`startup_demand_gui_validation_20260910T073057861796Z/evidence.json`). Num이 setter 오류 설명을 지운다는 가설은 재현되지 않아 배제했다.

`codex_startup_gui_s13_1050_v1` 실제 기준 런을16:36:03 시작하여1050초 완주했다(wall141.296초, exit0, 소유 native 잔존0). 수요204개 설정2.78초, 첫native step0.92초다. 전체 명령/native readback/원래1,990,205행 FZP ordered payload 동치 검사가 모두 통과했다. source137개 중 변경은 검토한 VBS 하나이며 옛 source manifest를 덮어쓰지 않고 `startup_gui_actual_v1/result.json`에 새 검증 범위를 기록한다(완료 SHA62b1fe89…).

동일 수정으로 거리2000m 실험도1050초 완주했다(wall141.875초, exit0, source_changes=[]). 수요204구간 write의 순서·before·target은 기준과 exact, 수요설정2.63초/첫step1.03초다. 기존300초 timeout과수요setter실패가 재발하지 않았다. 교통 개선 여부는 공간 분석 전이므로 아직 판정하지 않는다.16:44에는 하류1135 제거/상류분할 망을 동일 수요·제어로 실행 중이다.

## 15시대 진행: 전체 후보 추적 timeout 보존, 고정 명령 실제 교통 실험 시작

16시대 보완: r01 baseline1050은182.922초에 watchdog exit0으로 완주했고 FZP1,990,205행/header/100,983,296 data bytes는 원beta300 v3와 exact(`fixed_beta300v3_experiments/r01/baseline_payload_only.json`)다. 그러나 종료 직후 VISSIM 자연 종료를 기다리지 않은 driver race와 nested Windows PowerShell의 Get-FileHash 모듈 경로 오류로 batch gate는 실패했다. r01은 failed로 보존하고 빈 provenance hash를 사후 덮어쓰지 않았다. 자연 종료 최대30초 대기/새 PID+StartTime 거부와 native PSMODULEPATH/hash 사전검사를 수선했고21개 회귀가 통과했다. 실패 lock은 소유 프로세스 부재 확인 후 r01 폴더로 보관했다.16:02에 새 r02 batch를 시작했으며 원본 SHA 기록은 정상이다.

r02 baseline은 실제명령/신호/전체1,990,205행 궤적과137개 runtime source 일치를 모두 통과했다. 로그 지연을 무진행으로 잘못 판단해16:08:46에 남은 VISSIM을 수동 종료했으나, 실제 state1/action1은16:07:03(시작약285초), FZP1050과SIM_DONE은 각각16:08:36/42에 이미 완료돼 있었다. 잘못된 초기 판단과 정정 근거를 `r02/manual_startup_timeout_review.json`에 보존하며 이것을watchdog 실패로 사용하지 않는다. 뒤이은 거리2000m arm은 실제 state/action이 없었고16:14:02에STARTUP_TIMEOUT300으로 자동 종료됐다. r02 batch 실패는 보존했다.

16:17에 r03을 시작했다. driver는 이미 통과한baseline만 manifest SHA/전체 runtime/명령/readback/원본FZP전수 동치를 다시 검사하여 재사용하는 명시 옵션을 추가했고 기존21회귀가 다시 통과했다. 새 r03은 r02 baseline을 재사용하고 거리2000m와상류1135를 새폴더에서 실행한다. 부분실패 런을통과로 바꾸거나진행중 실행을재사용하지 않는다.

추적 저장은 검토된 lossless root 압축으로 교체했다(`trace_root_compression_install_v1.json`, storage SHA a371891e…). 실제SC1004 국소 한 점의 전후 trace cost bits·후보 기록·운영 snapshot 및 normalized 전체 hash가 exact이고 instrumented scope는0.80464→0.20279초였다. 이는 전체MPC 성능 수치가 아니다. 전체 후보 추적의 재실행은 교통 세 실험 이후이며 여전히 미완료다.

14:43에 시작한 v3 전체 후보 추적의 원본 실행은3600초 제한에 걸렸다(elapsed3613.516초). worker116개 작업 기록은 수집됐지만 부모의 최종 trace가 없어 valid=false이며 전후 후보 동일성은 여전히 미확인이다. 정상 실행의15~19% 단축 근거와 이 실패를 섞지 않는다.15:52에 Python/VISSIM/script host 잔존0을 독립 확인한 뒤 보존된 ZIP에서 캐시 소스9581813…를 복구했고137개 runtime source pin이 다시 모두 일치했다. 실패 pair.json은 수정하지 않았으며 `signal_clock_performance_v1/trace_pair_t900_20260910T054355735292Z/recovery/cached_source_restore.json`에 복구 증거를 별도 저장했다.

15:52에 `run_fixed_beta300v3_route_experiment --name r01`로1050초 고정 명령 VISSIM 실험을 시작했다. baseline 전체1초 FZP가 원래 beta300 v3의 header와 모든 ordered data byte를 재현해야만 거리2000m와 상류1135 분할 실험으로 넘어간다. driver18개 작은 회귀가 통과했고 새 실행은300초 startup/stall guard와 단일 라이선스 순차 실행을 사용한다. 이 시점에는 baseline 실행 중이며 실제 교통 개선은 아직 미확인이다.

동일 문제·입력·탐색을 유지하는 신호 clock 캐시를 정본 `signal_actuation_contract.py`에 적용했다. 설치 소스 SHA는 `9581813d96fb27a7275ba41766763bd0bf123a200fb15b8cec8bf42e484227b5`이며 원본 전체 바이트는 `fixtures/signal_clock_original_module.zip`에 보존했다. 설치된 코드의 focused 회귀 12개와 19,763개 exact outcome을 확인했다. 모든 레버를 같은 follower game에 통합하는 변경은 아직 적용 전이다.

동일한 명시 `PYTHONHASHSEED=20260910`과 실제 900초 입력에서 정상 실행을 전후 두 번씩 완료했다. 원본 183.333262/178.866052초, 캐시 150.172396/144.019732초로 평균 181.099657→147.096064초, 18.776% 단축이다. CSV와 반환 결과는 부동소수점 허용오차 없이 일치했다. 경로·실행 fingerprint는 실제 입력 SHA와 fingerprint 재계산을 통과한 provenance만 구분했으며 수치 필드는 제외하지 않았다. 한 번은 150초를 넘었으므로 안정적인 제어 주기 여유를 확보했다고 선언하지 않는다. 상세 근거는 `signal_clock_performance_v1/assessment.md`다.

혼잡 발생 1500초·심화 3300초·부분 회복 4950초는 기록된 동일 raw state/직전 action으로 원본과 캐시를 순차 비교했다. 각각174.092018→142.101813초(18.375%),145.012834→122.803255초(15.316%),144.861000→120.657184초(16.708%)다. 각 상태 한 쌍이므로 변동성 추정이나 통합 평균 단축률로 쓰지 않는다. 세 상태 모두 CSV와 반환값의 엄격 비교를 통과했다.1500초의 최초 FAIL은 새로 나타난 두 candidate wall-time 필드였고, 실제 perf_counter 생산 경로·metadata 복제를 확인한 뒤 해당 시간 필드만 제외해 재비교했다. 최초 FAIL과 사후 검토는 모두 보존했다. 상세는 `signal_clock_performance_v1/representative_states_v1/assessment.md`다.

이 세 상태는 실제 head warm-history가 없는 OFF 설정이므로 초기 ON 상태와 별도로 기록한다.4950초에는 서측 일부가 회복하지만 E8은 여전히 혼잡해 망 전체 해소의 증거는 없다. 원본/캐시 source 교체는 해당 실행만 소유하고, 비정상 종료 시 잔존 프로세스 확인 전 자동 복원을 보류한다.

반복 snapshot을 메모리에 모두 쌓던 v2 계측기를 lossless SQLite 저장 방식으로 수정했다. v3의 snapshot 무결성·table 누락·비교 순회 검토와35개 focused 검사가 통과했다.14:43의 전체 추적은 약190MiB working set을 유지했으나 위 시간 제한으로 미완료다. 최종 출력의 일치와 모든 국소 후보의 일치는 별도 검증이며 후자는 미확인이다. 프로파일/추적 실행 시간은 정상 실행 성능 수치에 섞지 않는다. 완료·소유 프로세스 종료 전 source 교체나 tracer 수선은 하지 않았다. lossless root 압축 저장의 미적용 제안은39개 작은 검사를 통과했으나 실제 전체 추적 속도는 아직 측정하지 않았다.

추가 lane-change 검토에서는10635의 거리 설정이 이미1000m이고,71 진입 후 물리적 차로 이동 여유가 약77.7m라는 점을 확인했다.1135의 downstream 분기를 upstream1123/1124/1125에 합치는9개 경로는 회전 비율·연결·목적 위치를 보존한다. 실제 VISSIM read-only COM LoadNet이25.22초에 완료됐고80개 설정행에서 오류0, Combine/LookAhead 활성 및 거리1000m를 확인했다. simulation은 진행하지 않았다. 같은 seed의 차량별 실현 OD까지 보존되는 것은 아니며 추가 효과는 미확인이다.

원본·10635 거리2000m·상류1135 분할의 별도 INPX 실험본을 만들었고 원본 network는 보존했다. 상대 배경 JPG 의존성도 공통 asset 폴더로 보완했다. `fixed_beta300v3_network_arms_flat_v1`의47파일은 INPX3개+SIG42개+JPG1개+manifest이며 manifest SHA는 `1e7544ee22fa52b0eed3a8eb23696a4b8b7117bd5fcf5daf75adf704da495367`다.

실험본 세 망의 native LoadNet/readback도 완료했다. `flat_network_native_readback_v3/native_gate.json` SHA는 `56b3f9ff9e608e680482392ceb75f2109984194d7423ab5eac00cc265af09dbd`이며 각210행의 key/type/value가 XML과 exact, 거리1000/2000/1000m, routing decision 수130/130/129, 종료코드0, 잔존 소유 프로세스0, source_changes=[]다. 원본/거리/상류 망의 경과시간은27.73/30.35/26.04초다. 최초 v1은 PS5.1 UTF-8 읽기 누락으로 COM 전 실패했고 v2는 baseline LoadNet 성공 뒤 Process.ExitCode=null 때문에 fail-closed했다. 별도0/7 프로세스로 handle 취득 수선을 검증한 뒤 v3가 통과했으며 앞선 실패를 보존했다. 이는 교통 simulation이나 차량별 경로 선택 검증이 아니다. 읽기 전용 COM은 정상 성능 측정에 쓰지 않는 후보 추적과 독립적으로 병행했다.

실제 beta300 v3의900초213개 명령은 기존 adapter/VBS/writer를 통한 fake-COM 호출에서 metadata를 제외한 모든 CSV 열과1792개 readback이 일치했다. 이 검사도 실제 교통 런이 아니다. 동일 명령1050초 VISSIM 대조 실행과 공간 분석이 남았다. `lane_change_10635_distance_audit.md`, `onramp_early_route_tree_audit.md`, `native_settings_validation.md`, `fixed_beta300v3_route_experiment_design.md`에 초기 근거와 판정 기준을 기록했다. 초기 문서의 pending 문구는 당시 범위이며 최신 완료 근거는 위 native v3/fake-COM v2 산출물이다.

GNE 공유 제약 설계는 다른 owner의 제어만 고정하고 수용 유량·대기는 후보마다 함께 재계산하도록 정정했다. 다른 owner의 과거 방출량을 보장하는 예약권을 새 hard constraint로 추가하지 않는다. 실제 공유 용량의 보존, local/global 흐름 정합성, 검사 후보의 개선 잔차는 별도 검증이다. `joint_owner_shared_feasibility_design.md`와 `fixed_candidate_price_direction_design.md`는 구현 전 설계이며 수렴이나 교통 개선의 증거가 아니다.

## 13시대 우선순위 보완 (당시 기록)

추가 일반 기준 실행은172.496245/172.071095초다. 캐시 적용 전 반복이므로 개선 수치가 아니다. 첫 반복은 CSV/반환 결과가 정확히 같았고, 두 번째는 `leader_boundary_leg_excluded_veh` 및 metadata 복제 두 필드에1ULP 차이가 나 엄격 비교 FAIL을 보존했다. unordered set 합산의 기존 hash-seed 의존이며 현재 Ω/follower_ttt 경로에서 선택·λ·전이로 재입력되지 않음을 소스로 확인했다(`boundary_leg_diagnostic_readback_review.md`). 새 후보 전체 전후 추적은 명시한 동일 `PYTHONHASHSEED=20260910`을 adapter 시작 전에 주입하고 worker가 상속하도록 한다. 이 환경 차이를 기존 기본-seed 실행과 숨겨 섞지 않는다.

국소 후보 v2 monitoring observer의22개 통합 검사가 통과했고, 실제 SC1004 국소 비용 한 점에서 무계측 대비 비용 bits와 입력 불변을 확인했다. 그러나 `043126158133Z`의 실제900초 전체 후보 추적은 첫 follower 단계에서 약8.2GB의 메모리와615MB의 부모 local JSONL을 사용해 종료했다. 반복 cfg/operational snapshot을 보유하는 계측기 문제이며, 이 실행은 valid=false/불완료로 보존한다. 당시 worker는 이미 모두 끝났고 소유 adapter만 종료했다. bounded-memory 저장 방식으로 계측기를 수선하는 동안 정상 기준 두 번과 신호 캐시 실제 적용을 진행한다. 현재 production은 dd13e08 그대로이며 네 레버 GNE 통합은 적용 전이다.

사용자 추가 요청에 따라 실제 장기 비교에 앞서 **같은 결과를 유지하는 계산 최적화**를 먼저 진행한다. 그 다음 전 레버를 같은 follower game에 넣고 최종 실행값에서 공유 제약·검사 후보의 추가 개선 잔차를 검증한다. 원문은 `docs/REQUEST_20260910_gne_and_performance.md`다. TTD 보상은 필수가 아니며 TTT/cost-to-go 대안도 이후 비교하되 성능 단계에서 목적함수를 바꾸지 않는다.

v4 head-resource canonical warm-history/국소/fresh-worker16개 검증은 통과했다. 동일900초 cold-history 전체 MPC 일반 기준180.057479초를 고정했고 부모·worker 전체 cProfile과 후보 경계 추적을 완료했다. 최종 CSV와 반환 결과는 exact다. Python3.12 cProfile의 thread 혼합 귀속 오류는 최소 프로그램으로 재현해 잘못된 pool 종료 시간 해석을 배제했다. 상세 계측 한계는 `decision_profile_v4_assessment.md`다.

신호 clock의 검증된 불변 값 재사용은 독립 반례 수선·12개 focused 회귀·tuple 강참조 검토를 통과했으며 아직 production 적용 전이다. Native prehead config 인덱스는 nested 값 무효화가 부족해 보류했다. 정상 실행 반복과 모든 국소 후보 추적을 준비 중이다. v4 실제 장기 VISSIM은 아직 실행하지 않았다. 후반 warm head 관측과 망 전체 해소 기록은 현재 없다는 범위를 `performance_equivalence_state_catalog_20260910.md`에 명시했다.

## 12시대 후속 진행

아래 초기 실행 기록 이후 실제 source β0 장기 런, 관측기 대조, 순수 Ω 목적함수와 shared service 통합을 추가 검증했다. 이 절을 현재 상태로 읽고 아래의 과거 ‘다음 실행’은 당시 계획으로 구분한다.

- source β0 5,400초 제어는 정상 실행됐지만 Ω TTT +6.83%, TTD −1,378건으로 악화됐다. E8 첫 정체를 90초 늦춰도 장기 전파를 막지 못했다. 완주를 제어 성공으로 판정하지 않았다.
- v3의 동일 900초 상태에서 β=0/60/150/300 전체 MPC가 모두 통과했다. 실제 채점·출력 신호/offset/미터의 일치와 순수 Ω 목적값을 검증했다. 이는 예측 후보 비교이며 네 가중치의 실제 장기 성능표가 아니다.
- v3 β300의 실제 1,050초 런이 완료됐다. [900,1050]의 Ω TTT는 NC 80.15861→79.80875 veh·h, TTD 708→730건이지만 관측 유입도 319→295건이다. 127의 대기는 줄고 420·10682 및 E8/E9 최저 관측 속도는 악화됐다. 해당 150초의 개선을 장기 제어 성공으로 확장하지 않는다.
- 71에서 SG5 목적 차량이 SG2 차로3에서 녹색 중 막히다 native lane-change 제거된 사례, 그 뒤10641 잔류, 127 방출 차량의420 도착과 하류 SC105 녹색 종료의 어긋남을 실제 ID·경로·시간으로 확인했다. 자세한 근거는 `sc1004_first_control_window/assessment.md`다.
- 현재 v3 OFF continuous 5,400초 NC는 원래 NC의 전체 26,693,633행과 exact이다. 같은 길이 기준의 재현을 확보했다. 관측기 ON/OFF와 stepwise/continuous의 세 1,050초 NC도 전부 exact였지만, 긴 런과는 마지막20초가 달라 같은 요청 길이끼리 비교한다.
- 관측 head의 방출 근거를 실제10619/10629 resource에 연결하는 수정을 정본에 적용했다. v4의 실제 main 900초 cold-history β300 MPC가 통과했으며, canonical warm-history/fresh-worker 검증과 실제 장기 런을 준비 중이다.
- W_out의 이미 선택된 출구 목적지를 보존하는 수정은 진단 패치 단계다. 지역 follower와 전역 모형의 같은 목적지·ready 계약이 아직 닫히지 않아 활성화하지 않았다. E8의 route/lane·물리 분기 순서 오류도 남아 있다. VSL 용량 보너스나 임의 two-branch 이득으로 덮지 않는다.

새 근거: `contract_weight_preflight_v3_t900/comparison.json`, `contract_beta300_v3_smoke_comparison_1050/assessment.md`, `current_nc_v3_reproduction.md`. 시작 300초 동안 simulation이 진행하지 않으면 해당 런 소유 VISSIM을 종료하는 설정은 모든 새 실제 런에 적용됐으며, 최근 완료 런들에서는 발동하지 않았다.

## 실제 VISSIM 결과

| 실험 | 전역 TTT [veh·h] | Ω TTT [veh·h] | Ω TTD | 측정과 상태 |
|---|---:|---:|---:|---|
| NC |7403.8872|5578.6601|26070|5초 FZP, 마지막 4초 재고 유지 적분|
| pure n7 |7248.5122|5508.4361|25992|5초+마지막 완전 snapshot, 원래 n7 재현|
| VSL80 상류 두 구역 |7389.0914|5546.2331|26133|5초+마지막 snapshot, 실제 DSD 확인|
| 동일 NC 궤적의 1초 측정 |7403.8872|5578.6103|26203|실패한 미터 시도의 무개입 궤적을 전수 동일성 검증해 측정에만 사용|
| RM10639 g5 |7386.5289|5550.4406|26235|1초 FZP, 정상 완료|
| 고정 녹색·offset0 |7281.7622|5473.8889|26574|1초 FZP, 정상 완료|
| SC1004 green10 |7253.8414|5435.0782|26681|1초 FZP, 정상 완료; 현 MPC 하한 밖의 진단 설정|
| SC1001 +10 / SC1004 −10 |7201.3372|5399.1310|26721|1초 FZP, 정상 완료; 녹색 총시간 동일|

5초·1초의 TTD를 직접 비교하지 않는다. TTD는 관측 이탈과 물리 종단 인근의 제한된 소멸 추론을 합한 값이며 미확정 내부 소멸은 제외했다. 반복 이탈과 고유 차량 수도 구분한다.

처음 n7 계측은 감사 snapshot이 관측창을 초기화하는 오류로 정책에 영향을 줬다. 읽기 전용 감사로 수정한 뒤 추가 audit 없는 pure n7가 7248.5122로 원래 결과를 재현했다. 고정 신호 세 실험의 녹색은 첫 계측 n7의 t2100에서 가져온 정적 벡터다. Native 또는 pure n7로 부르지 않는다.

## 위치별 반응

- VSL80은 첫 지속 정체를 늦췄지만 장기 상류 전파를 막지 못했다.
- RM10639 g5는 Ω TTT가 28.17 줄었어도 공통 구간 통과량은 258대로 같고 램프 정지 대기는 늘었다.
- 고정 녹색은 D 동측 10481/127 대기를 크게 줄이는 동시에 F 동측과 도시부 대기를 재배치했다.
- 고정 녹색 대조 대비 green10은 Ω TTT −38.81 / TTD +107이다. 10639 대기는 줄고 420은 늘었다. p1=10초는 현재 최적화기 하한 20초보다 작으므로 실현 가능한 MPC 후보라는 주장은 하지 않는다.
- 상대 offset은 Ω TTT −74.76 / TTD +147이다. E8 최초 지속 정체는 90초 늦어졌지만 일부 상류 셀은 빨라지고 40/420 대기는 늘었다. Ω 내부 강제 제거도 157→170건으로 늘어 최종 우월성 선언의 근거로 쓰지 않는다.

[전체 검토](../docs/REVIEW_20260910_control_diagnosis.md), [공간 비교](spatial_lever_comparison.md), [미터링](meter10639_result.md), [고정 신호](signal_zero_result.md), [green10](signal_green10_result.md), [offset](signal_offset10_result.md)에 실제 명령, readback, 측정 창과 한계를 기록했다.

## 코드 통합과 검증

공유 초기화, 관측의 단일 귀속, 실제 차로/연속식 좌표에서의 차량 수, 후보별 local landing 재고, 명시 accepted-transfer Ω 장부, finite SC2001 경로를 통합했다. 초기 pure n7 31개 상태의 전체 Ω 재고는 관측과 정확히 일치했다. 양수 미확정 물리 지원은 링크를 명시하고 실패한다.

실제 탐색에서 램프 공간 중복 예약과 W_out 이중 인출을 발견했다. 일반 sink 인출을 유예하고 실제 수용량만 한 번 이동시키도록 수정했다. 실패했던 두 full main과 고정 후보 651개 450초 rollout에서 보존 검사를 통과했다.

신호 계약도 실제 정본에 통합했다. 선택된 SG plan, live 현시 순서, 물리 green 상한과 CSV 정밀도, VBS의 t+offset 및 정수 event 유지시간을 후보 채점 전에 공유한다. 실제 설치 코드 신호/offset 회귀 15개가 통과했다. Experiment offset은 config와 환경의 명시 선언이 모두 필요하며 생산 승격 증거를 조작하지 않는다.

offset·leader fallback의 최종 비교도 Ω 목적값으로 바꿨다. 평가 후 녹색 정련과 미터 양자화·spillback 강제 개방을 채점 전에 확정하도록 수정했다. bc9078e의 최종 실제 main은 no-control t1 1.56초, wu-link t900 β0 122.71초, t3300 β300 115.64초에 통과했다. 미터·보존·preflight 22개, phase/follower 10개, 원래 runs와 Git 접근을 차단한 portable 49개 검사가 통과했다.

첫 live `codex_area_beta0_s13_20260910`은 1050초에서 물리 재고 지원 오류로 중단됐다. 900초 CSV는 최종 preflight와 byte-identical이고 900–1050초 도시·램프 130개 SG 및 VSL readback 불일치는 0이었다. 다음 snapshot에 미확정 Ω 링크 10421의 차량 1대가 나타나면서 failfast가 발생했다. VISSIM 초기 렉이나 timeout이 아니며, 이 미완료 run은 가중치 성능표에서 제외한다. 실제 경로에 근거한 귀속 보완을 진행한다.

10421과 같은 오류를 막기 위해 45개를 검토하고, 실제 신호 이후 회전·하류 저장소가 유일한 16개만 추가 지원했다. 29개 미확정 링크의 양수 차단은 유지된다. 9개 회귀에서 실제 1050초 재고 2,083대와 기존 31개 상태의 Ω 재고 일치, 초기 유입·유출 0, 186개 합성 차량의 단독 귀속과 29개 각각의 차단을 확인했다. 실패했던 1050초의 실제 정본 main도 115.30초에 통과했고, 관측한 worker 36개가 모두 종료됐다. 새 CSV의 VBS 모의 COM 검사 144행에도 불일치가 없었다. 프로덕션 Python·교통류 계수·가중치는 그대로이며 관측 지원 데이터만 수선했다.

## 남은 물리 모형 문제

E8의 1200→1350초 속도 예측은 96.41 km/h, 실제는 23.27이다. 정체 후 27구간의 +150초 평균 속도 편의는 +20.04 km/h다. 회계 수정만으로 이 오차는 거의 줄지 않는다.

실제 순서는 10643 진출→10639 합류→136m 뒤 10682 진출→10681 합류다. 집계 모형은 이 순서를 보존하지 않고, direct 10682 점유도 기존 본선 차로 피드백의 전용 storage에서 빠져 있다. 초기에 직접 출구의 queue tail이 본선까지 닿았다고 입증한 것은 아니므로 이를 유일 원인으로 단정하거나 임의 capacity 감소를 넣지 않는다. 분기별 재고·실제 수용 flow·이동 순서를 함께 표현해야 한다.

3301초 차로별 실제 위치에서는 진출 직전 1–3차로의 정지열과 빠른 4차로가 공존한다. E9의 낮은 평균 밀도를 전체 차로의 수용 여유로 해석하면 이 분류 병목을 놓친다. [차로 그림](e8_diverge_snapshot_3301.png), [150초 통과량 검증](e8_window_passages_review.md)을 추가했다. 확인된 강제 제거 1대를 별도로 처리하면 48개 구간의 재고·물리 통과량 잔차가 모두 0이다. 이것이 새로운 용량 함수까지 식별했다는 뜻은 아니다.

## 다음 실행

1. 보완한 16개 물리 지원과 실패 snapshot의 재검증은 통과했다. 새 입력 manifest로 β0 VISSIM을 재실행한다.
2. 수정 MPC를 seed13에서 β=0/60/150/300으로 실행한다. 1초 Ω 측정과 혼잡 시작·차로·전파·실제 레버를 함께 확인한다.
3. 유망한 결과는 독립 seed에서 다시 확인한다. NC13에서 얻은 경험적 경로 prior의 holdout도 필요하다.
4. 미사용 adapter 18개와 placeholder 1개 삭제는 완료했다. 과거 파일의 git blob/hash 복원을 확인했으며, 진단용 임시 사본·패치 생성기는 실제 소비자를 확인해 추가 정리한다.

추가로 통합이 끝난 진단 patch·candidate·generator 37개를 삭제했다. 생산 코드·입력·원시 실험 증거는 삭제하지 않았다. 실제 회귀 18개를 통과했고, 삭제 범위와 복원 가능성은 [정리 감사](diagnostic_cleanup_execution.md)에 기록했다.

사용자 요청대로 시작 후 300초 동안 양수 simulation 시각이 없으면 해당 런의 cscript와 식별된 VISSIM만 종료한다. 실제 VISSIM은 한 라이선스에서 순차 실행하며, 진행 중인 런의 코드는 동결한다.
