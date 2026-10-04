> **셀23 후보 SDMPC 연결 검증 완료 — 2026-09-28:** 저장4500초 상태의 실제 선택1회 완료. PFO2/2·SDMPC2/2 수락, 미수렴; 근사예측30회+정본450초5회, native0. 도시 신호만 변경하고8RM g10·VSL직전값 유지. 실행모델 ΩΔTTT−0.9462, 추적외부 포함+0.0962대·시간.10484 단독g8 합류거의동일, g8→6→4 이득−0.0139로작음. 초기29/43 조합오차는 경계유입 차이와 분리; 작은이득에 추가재보정하지 않음. [선택과 한계](closedloop9000_d4e2_analysis/local_merge_cell23/CONTROLLER_CHECK.md), [경계분해](closedloop9000_d4e2_analysis/local_merge_cell23/interaction_audit/README.md). 모든소유계산 종료·정본미채택·STOP/Ω목적 유지, 이득미완료/목표ACTIVE. 다음은 실제합류가 충분히바뀌는 상태의 국소후보 순위와 제한된SDMPC 탐색을 비교한다. 아래는 이전 이력이다.

> **셀23 국소 재보정·검증 완료 — 2026-09-28:** 사용자 제안대로10484 합류 셀 하나의 기존 δmerge/하류저밀도 anticipation만12조합 비교. seed29 유지·완화의 물리 오차로 δ2/ν4.59375 선택·동결, 국소 점수6.50% 개선. seed47의10484 완화 실측+1.679 손해를 기존−0.216→+0.180으로 방향 수정, seed53 큰 완화 손해+0.276→+1.246으로 개선. 초기29/43 RM도 방향 개선.10490 완화·43 RM+VSL·53 VSL 오판은 남음.450초63회/결합150초1회·함수560평가 완료, optimizer0/native0. 기본20사례 배열exact, 후보manifest 배열exact, parametersPASS, 8램프보존PASS. 정본 미채택·STOP 유지·Ω목적 불변. [결과와 한계](closedloop9000_d4e2_analysis/local_merge_cell23/README.md). 다음은 남은 큰 조합 손익과 실제 SDMPC 선택 연결. 아래는 이전 이력이다.

> **10484 오판 원인 분해 완료 — 2026-09-28:** seed47 공통2670.1→3120.1초에서 미터 g2→4/6/8 완화의 실제 동측31셀+8커넥터 비용+1.6792대·시간, τ4 예측−0.2397. 도시→램프 유입차 기여−0.0167로 작고, 실제 진출 배수+0.4125·말단+1.2875 손실을 놓쳤다. 합류 셀23 실제 통과−52대/모델+43.10대, 상류 전파가 약하다. 실측N·v의 q=Nv/L 근사도 감소 방향이므로 임의 평형 용량 상한보다 정본 속도항의 공통상태 반응 검사가 다음이다. 원본SHA·명령·동일초기·재고/유량 비용 정합PASS. 별도 VSL창 미해명 소실4대는 실패 보존. 새예측0/optimizer0/native0, Ω목적·selected·STOP 유지, 미채택/이득미완료. [보고서](closedloop9000_d4e2_analysis/recovery_response/seed47_audit/README.md). 아래는 이전 이력이다.

> **회복 시간 후보 검증 완료 — 2026-09-28:** 기존 가속 회복시간8/6/4초를 seed29 기준명령의 재고·통과량 오차로 비교해4초 선택 후 고정. 초기 RM방향은29·43에서 이득으로 바뀌었지만 예측크기는 작고 후기47의10484완화 손해를 여전히 이득으로 오판한다. VSL도 미해결.450초44회+전체6000초 상태150초1회 완료, optimizer0/native0. 후보 별도 보존·정본 미채택, 기본4조건 전체배열 exact·파라미터 PASS. 다음은10484완화의 합류→셀22–24 통과→하류 방출/목적지 구성. [보고서](closedloop9000_d4e2_analysis/recovery_response/README.md). Ω목적함수·선택config·STOP 유지, 목표ACTIVE/이득미완료, push없음. 아래는 이전 이력이다.

> **독립 검증·기각 완료 — 2026-09-28:** 10681 post-head 수용/과거 차로 유량 보정은6000초 합류26.53→38.41대(실측37)를 개선했지만 seed53에서140.63→170.29–175.46대(실측148)로 악화하여 기각했다. 정본5파일은 실험 전 바이트 복원, 앞선 도시 목적지 수정은 보존.28회 오프라인 전진 예측, optimizer0/native0. seed53 RM완화 추가합류는 실측94/모델95.78대이나 진출+말단 방출변화는−101/−8.08대: 다음은 방출·배수·회복 응답이다. 비용 분해는 동측31셀+8커넥터 범위이며 전체Ω로 대체하지 않는다. Ω목적함수·STOP 유지, 새9000 재시작 금지. [결과와 다음 순서](closedloop9000_d4e2_analysis/posthead_receiving/README.md). 이득 미완료, 목표ACTIVE, push없음. 아래 상태는 이전 이력이다.

> **오프라인 수정·비교 완료 — 2026-09-28:** 도시행 초기 재고의 램프 재선택을 막는 후보를남겼다.10490 도착예측66.71→54.39(실측40),31.42→27.62(실측15).10681 차로별 순간/직전검지비중 후보는4500초를악화시켜기각하고관련3소스를작업전그대로복원했다. 기능OFF150초전체trace·seed53 component2회물리배열exact.69테스트통과,과거입력부재21개미실행. [검증·한계](closedloop9000_d4e2_analysis/offline_repairs/README.md). Ω목적함수·selected설정불변,STOP유지·새native없음·이득미검증. 아래내용은이력이다.

> **오프라인 수정·검증 승인 — 2026-09-28:** 사용자 승인으로 초기 도시행 재고 보존과10681 차로별 합류 수용을 기존 코드에서 검토·수정한다. 저장된4500/6000초 상태와 기존 독립 응답 자료로 검증한다. Ω TTT 목적함수 불변, STOP 유지, 새 VISSIM·push 없음. 아래 승인 대기 문구는 이전 이력이다.

> **목적함수 유지·진단만 — 2026-09-28:** 기존 FZP 두 짧은 구간을1회 읽어10681 실제 진입/head/합류와 native 기록의 정확 일치를 확인했다.6000–6150초 실제 합류37대 중 마지막 램프2차로35대,1차로2대(5초 관측). 모델2차로 수용은23.41대. 실제 상류2차로912대/h,4차로 평균1524대/h, 기존 gap식에서 역산한 모델 등가 경쟁류 평균1871대/h라 평균 경쟁류·균등 차로 배분을 우선 검토한다. 초기 도시행 재배정 오류 최소16.4/5.1대도 유지. [진단·한계](closedloop9000_d4e2_analysis/STOPPED_RESPONSE_DIAGNOSIS.md). 목적함수·계수 불변, 새 예측/보정/native0회·STOP 유지·이득 미검증. 아래 실행 상태는 과거 이력이다. **진단의 다음 수정 범위까지 정리했으며, 사용자에게 오프라인 수정·검증 전환을 요청한 상태다. 답변 전에는 모델·설정 변경이나 새 런을 진행하지 않는다.**

> **사용자 중단 후 검증 완료 — 2026-09-28:**8400초에서 런을 중단했고 소유 계산/native/후처리는 모두 종료됐다. STOP 유지,9000 재시작 금지. 완전한 공통0–8100초5초FZP·LDP/readback 검증 완료: ΩTTT +52.5561대·시간(+0.7781%), Ω 밖 +247.4598, TTD −300, 명시적 차량 삭제233→373. 동측 본선TTT +6.2041%;8RM은48회 모두g10, VSL은22회100km/h 선택. 미삽입 대기는 미측정이며 정상9000 완료·이득 보정 완료가 아니다. [결과·한계](closedloop9000_d4e2_analysis/stopped_prefix8100/README.md), `user_stop_analysis_status.json` 참조. 새 런·재보정·push 없음. 아래 실행 상태는 과거 이력이다.

> **사용자 요청으로 중단·기록 검증 — 2026-09-28:** 사용자가 현재 지점에서 런을 멈추고 검증하도록 지시했다.8400초 관측에서 소유 runner/계산/native를 종료했으며 모든 해당 PID 종료를 확인했다. 원래 실행 폴더의 STOP을 유지하고 재시작·9000 자동 후처리를 하지 않는다. `closedloop9000_d4e2_analysis/user_stop_receipt.json` 참조. 종료 직전 일부 LDP/ERR 버퍼가 잘렸으므로 완전한 공통0–8100초 기록을 기존 무제어와 비교 중이다. 새 분석 session62902, `stopped_analysis2.log`; 첫 진단 스크립트의 분포 키 표기 오류 로그도 보존했다. 원래9000 정상 완료로 표현하지 않으며 이득 검증은 미완료다. 아래 실행 중 상태는 과거 이력이다.

> **관리 프로세스 종료·native 계속 — 2026-09-28:** 10:33:19에 owner31020·watchdog884가 종료되어 기존 task가3221225786을 반환했지만, 원래 cscript31064·VISSIM16776은 살아서7350초까지 계속 진행했다. 종료 원인은 아직 미확인이다. **native를 재시작하거나 중단하지 않았다.** 첫 후속 작업은 부모 종료만 보고 실패로 멈췄고, 해당 상태/코드는 `closedloop9000_d4e2_analysis/supervisor_exit_103319`에 보존했다. 현재는 `finish_after_native.ps1 -RecoverAfterSupervisorExit` 세션75820이 원래 native 두 PID의 생성시각을 확인해 종료 대기 중이다. 최신 상태는 `closedloop9000_d4e2_analysis/recovery_postprocess_status.json`이다(이전 postprocess_status.json은 실패 이력). 종료 후 실제9000·전체 LDP/readback·native interval counters를 먼저 검증해야 별도 recovered_native_completion.json을 만들고 기존 비교 분석을 실행한다. 원래 supervisor status/실패 코드를 성공으로 덮어쓰지 않는다. 살아 있으면 중복 실행·분석·동결본 수정 금지. 목표ACTIVE, 이득미검증.

> **종료 후 자동 비교 대기 — 2026-09-28 10:09:** SDMPC9000 소유 PID31020 종료 뒤 기존 동결 `native_pair1200/analyze_pair.py`를 한 번 호출하는 후속 작업을 연결했다. 상태는 `closedloop9000_d4e2_analysis/postprocess_status.json`, 실행 세션89263, 코드 `closedloop9000_d4e2_analysis/finish_after_native.ps1`. 현재 stage가 waiting/analyzing/cached이면 중복 사후 분석 금지. 정상 native9000·소유 프로세스 종료·task 종료 코드0·STOP 부재를 확인한 뒤 TTT/TTD/native 외부 대기 및 cached 공간 결과를 계산한다. `complete_pending_interpretation`이어도 목표/이득 완료 아님. failed_preserved이면 자료·로그 보존하고 원인부터 확인한다. 이 후속 작업은 새 native·계수 보정·git 작업을 수행하지 않는다. 기존 단순 대기 세션10616도 살아 있으나 분석을 호출하지 않는다.

> **현재 실행 — 2026-09-28 06:07:** δ4/E2 SDMPC1200 연결 검증 통과 후 같은 동결본의 SDMPC9000(seed29)을 시작했다. 실제150초 이상 진행 및 소유 PID 확인. 실행 폴더 `D:/VISSIM_runs/20260928_sd31_d4e2_9000`, 일회성 작업 `Codex-VISSIM-sd31-run-20260928060432474`; owner31020(06:04:32.784764+09), watchdog884(06:04:47.321372), cscript31064(06:04:48.475490), VISSIM16776(06:04:50.007707). 정확한 근거는 `heldout53_response_v2/native9000_launch.json`. 살아 있으면 중복 실행·중단·동결본 수정·큰 분석 금지. 종료 뒤 기존 `native_pair1200/analyze_pair.py --closed-loop-9000`으로 `D:/VISSIM_runs/20260927_sd31_wiring9000/nc`와 비교한다. 짧은 결과는 `native_short1200_d4e2_analysis/README.md`: LDP/readback·이력 통과, 제어 전431,233 FZP행 정확 일치, LSA 실패 별도 보존. 짧은 런의900/1050 첫 RM/VSL은 유지됐으며 혼잡 성능은 미검증. 추가 계수 보정 없음, 목표ACTIVE, push 없음. 아래 실행 상태는 과거 기록이다.

> **실제 런 시작 — 2026-09-28 05:40:** δ4/E2 시험 설정의 SDMPC1200(seed29) 한 런이 D:/VISSIM_runs/20260928_sd31_d4e2_short1200 에서 실행 중이다. 먼저 status.json·detached_run.json과 실제 PID 생성시각을 확인한다. 일회성 task Codex-VISSIM-sd31-run-20260928054027157; owner1204(05:40:27.478453+09), watchdog37212(05:40:42.781972), cscript37724(05:40:43.726256), VISSIM30088(05:40:45.222323). 살아 있으면 중복 런·분석·중단 금지. 동결본 D:/VISSIM_runs/20260928_sd31_d4e2_runtime/frozen/sdmpc31_886a014a_202609280537 은 수정하지 않는다. 최초 진행300초 watchdog·자동 재시도0. 종료 후 실행값/관측/제약을 검증하고 같은 동결본의 SDMPC9000 및 matched NC 비교로 진행한다. 이번1200은 연결 검증이며 혼잡 순이득 완료가 아니다. 아래 내용은 완료 이력이다.
> **최신 상태 — 2026-09-28 05:36:** seed53 네 런·8예측 비교와 후보 SDMPC4500 한 주기/실행 모델 확인 모두 완료. 큰 미터 해제 손해의 방향은 개선했고, SDMPC는 S13 첫90→100을 선택했다(8미터g10 유지). 실행 모델 Ω−1.20951·추적 외부+1.23217·합계+0.02266대·시간으로 전체 이득은 미검증이다. 미세한 오차의 재보정은 중단하고 δ4/E2를 다음 native 시험용 selected 설정으로 고정했다. 이전 설정 보존; 최종 이득 정본 선언 아님. [결과·근거](heldout53_response_v2/README.md), heldout53_response_v2/provisional_adoption.json. 모든 소유 런·계산 종료, 일회성 seed53 task 해제. 기존 도구로 D드라이브 실행본을 동결한 후 짧은 폐루프→9000 비교로 진행한다. 목표ACTIVE, push 없음. 아래 상태는 과거 이력이다.
> **최신 상태 — 2026-09-28:** 새 seed53의 네3300초 native 런과 동결 기준/δ4·E2 후보의8개450초 예측 비교 완료. 실제 미터 해제 비용 증가+5.929대·시간을 기존 모델은−0.308로, 후보는+0.276으로 예측했다. 동측 후보 선택 손실6.025→0.150. VSL의 미세한 이득은 여전히 오판하므로 일반 이득 보정 완료로 선언하지 않는다. 추가 계수 탐색 대신 같은4500초 저장 상태의 실제 SDMPC 선택 검증(session68585)으로 진행한다. 생산 기본 설정 유지, 시험 config는 heldout53_response_v2/controller_config.json. 과거30구간 VSL 이력은 별도 캐시에서 원본과 정확 일치; 최초 식별자 불일치 실패도 보존. [결과·실행 상태](heldout53_response_v2/README.md). 네 native/사후 분석은 종료됐고 새 native·push 없음. 목표ACTIVE. 아래 실행 상태는 과거 기록이다.
> **최신 상태 — 2026-09-28 04:46:** 새seed53 네 조건(미터 유지/점진 해제, 각VSL90 유무)3300초 유한 동시 런 시작. 기존15후보에서 고른 δ4/E2 부분 개선안을 교통 생성 전에 동결했으며 생산 모델은 유지한다. 실제 큐 D:/VISSIM_runs/20260928_release2670_s53_v2/task_status.json, 일회성 task Codex-VISSIM-seed53-20260928-044547(owner9116,start04:45:48.1085787+09). [프로토콜·동결·후속 판단](heldout53_response_v2/README.md). 먼저 현재 PID/생성시각과 런 상태를 확인하고, 실행 중에는 분석·계수 수정·중복 실행을 하지 않는다. 완료 후 공통 초기450초에서 기준/후보의 방향성과 전체 비용을 검증한다. 목표ACTIVE, 새 이득미검증. 아래 실행 문구는 과거 이력이다.

> **최신 상태 — 2026-09-28 04:35:** 관측10633·10698과 신호 이전 분기10625 연결 수정 완료. 새 설정으로4500초 SDMPC 한 주기·237축 미분·writer·450초 실행 모델 확인 완료. 선택−유지 ΩTTT 예측−0.84944대·시간이나 추적 외부 재고까지는−0.06018뿐이며,8RM·VSL은3블록 모두 유지됐다. 이 미세한 전체 비용 차이를 이유로 새 native를 시작하지 않았다. 기존2670.1초 미터 해제 자료에서는23셀 방출 감소와22셀 상류 정체 반응을 모델이 놓치는 위치·시간을 확인했다. [근거·남은 작업](RAMP_RESPONSE_20260928.md). 모든 소유 계산 종료, 목표ACTIVE·새 이득미검증. 아래 실행 상태는 과거 이력이다.

> **최신 상태 — 2026-09-28 03:35:** S13 VSL90 유지/110 해제의 두6450초 런·분석 완료.6000초 이전5,319,738행이 원래 런까지 정확히 일치, LDP/readback PASS. 해제−유지 실제 ΩTTT−0.06156대·시간, 사전 예측+0.29696; 이 미세한 차이를 맞추는 추가 보정은 하지 않는다. 고정 명령450초의10681 실제/예측 진입85/55.41대,10484는52/89.47대로 방향이 다른 큰 도착 오차가 남는다. 검증된 기존 관측으로8램프 사후 대조 완료(새예측/FZP재스캔/native0회). 일회성 task는 종료 코드0·소유 프로세스 종료 확인 후 해제했다. [결과·다음 판단](closedloop_recorded6000_native_vsl_release_detached_v2/README.md). 새 보정·폐루프 이득은 아직 미검증이며 목표ACTIVE. 아래 실행 중 문구는 과거 이력이다.

> **최신 상태 — 2026-09-28 01:52:** 6000초 공통 실제이력에서S13 VSL90유지/110해제의450초 비교 런 시작. 기존runner·명령재생·동결본 사용, 첫hold 실제300초 진행 확인. 일회성 작업 `Codex-VISSIM-vsl6000-20260928015020004`(owner15232,01:50:20.342533+09)에서 두6450초 런을 순서대로 실행한 뒤 기존분석기를 한 번 호출한다. **먼저 D:/VISSIM_runs/20260928_sd31_vsl_release6000/task_status.json과 실제 task/PID를 확인하고, 살아 있으면 런·분석을 중복 시작하거나 설정을 바꾸지 않는다.** [프로토콜](closedloop_recorded6000_native_vsl_release_detached_v2/README.md). 완료된SDMPC9000 ΩTTT+1.36%; 유지명령누락 수정은46검사·3750한주기검증PASS지만 새native이득은미검증. 계수보정 없음, 목표ACTIVE. 아래 현재/실행중 문구는 과거 이력이다.

> **현재 상태 — 2026-09-27:** 정밀 속도·궤적 보정을 확대하지 않는다. native1135 목적지 비율·이동 시간의 기존 연결을 활성화했고,6000초 SDMPC 한 결정(session84342 exit0)을 완료했다. 근사 Ω 비용−0.468%, RM·VSL 첫 명령 유지, 신호·offset 변경. 새 native 이득은 미검증이며 추가 계수 탐색 없이 선택 명령의 실행 모델·대기 비용 확인으로 넘어간다. [범위와 완료 근거](CONTROL_CHOICE_SCOPE_20260927.md). 아래 최신/실행 중 문구는 역사 기록이며 현재 계산은 종료됐다.

# 31셀 제어 이득과 SDMPC 실행 목표 — 2026-09-26

## 사용자 방향 수정 — 정밀 재현보다 제어 선택

**최신 연결 수정 완료:** SC1001의40번 도로4차로/SG3→10698→31 한 연결에 기존 head 서비스 관측을 전달했다. 기존 kind 필터에서 제외되던`boundary_out`을 전체 확장하지 않고, 이미 검증된 native 경로1119:1의 단일 movement에만 연결했다. 해당 head만 과거4개 녹색 창을 누적한다. 서비스율206.53→1931.71대/h,450초 방출3.442→32.195대;4500/6000초 이후 실제 통과33/29대(실제는재계획하므로 동일 명령 인과 검증 아님). 다른 서비스율 불변·옵션OFF 기존450초 예측 정확 일치·47검사+19subtest PASS·파라미터PASS. **선택config의 서비스 연결만 채택**, 초기큐 head-phase 후보는미채택, METANET 계수불변, 동결native불변. `closedloop9000_analysis/head10698_connection_validation.json` 및README 최신절 참조.

**다음 판단:** 미세한 녹색 비용 차이를 더 보정하지 않는다. 별도 사후 detector 확인에서10681 실제450초 진입은4500상태125대/6000상태101대인데 held 모델은28.26/17.24대다. 실제 재계획의 영향을 분리해야 하지만, RM의0미분을 충분히 설명할 수 있는 큰 도착량 누락 후보다. 실제 첫150초 명령 재생 또는 유한 RM 후보에서 해당 도착/방출과 비용 반응을 확인한다. 미터head 통과를 본선 합류로 혼동하지 않는다. `late_ramp_arrival_audit.json` 참조. 이번 추가native/최적화/계수탐색0회, 세션70121·67355·67187 모두exit0.

**작업 범위 재확인:** 절대 속도·궤적·모든 후보 순위를 맞출 때까지 보정을 계속하지 않는다. 이미 완료된 9000초에서 발생한 실질적인 손해를 설명하는 액추에이터→방출→대기 비용 연결만 점검한다. 40번 도로의 차로/현시별 초기 큐 배정을 바로잡는 opt-in 후보는 네 유한 녹색 후보의 순위를 바꾸지 못했으므로 정본에 채택하지 않았다. 추가 계수 탐색을 하지 않는다. 다음 한 가지는 SC1001 좌회전 서비스 관측이 `boundary_out` 종류 필터 및 30초 최소 녹색 조건 때문에 적용되지 않는지 확인하는 것이다. 실제 4500–4950초 SG3 통과33대와 held 모델3.442대의 차이는 중요한 단서지만, 실제 offset이 갱신되어 동일 명령 인과 비교는 아니다. `closedloop9000_analysis/sc1001_head_response_audit.json` 참조. 모든 진단은 종료했고 새 VISSIM은 시작하지 않았다.

**후반 선택 확인:** 4500/6000초의 held·selected4회 고정 예측 완료(최적화0회, 새native0회). 근사/실행 모델의 ΔΩ 부호는 동일했고 차이는0.05대·시간 미만.4500초는 추적 외부 체류까지 더하면+0.196대·시간 손해,6000초는−0.490 이득이다. 실제LDP에서40번 도로SG8 녹색46→약20–21초,SG3 23→20초;6000초40번 재고130→257대.4500초 저속차량은SG3의4차로에166대가 집중되어SG8 감소만으로 원인을 단정하지 않는다. 다음은SC1001의 합법 녹색 교환·목적지별 방출/공유 차로 대기·외부 비용을 확인한다. `closedloop9000_analysis/README.md` 후속 절 참조. 추가 계수 보정·새native는 실행하지 않았고 모든 진단은 종료했다.

**최신 완료 결과(2026-09-27):** 무제어와 SDMPC9000초가 session9778 exit0으로 모두 종료됐고 기존 분석도 완료했다. `closedloop9000_analysis/README.md`: 제어 전431,233 FZP행 정확히 일치, LDP/readback PASS, Ω TTT **+3.653%**, native 전체 도로 체류+미삽입 대기 **+1.852%**. 초기3000.1초 Ω 이득−53.231대·시간이4500초 이후 증가로 최종+265.354로 뒤집혔다. 54주기 내내8RM 개방, 동측 국소 미터 미분1248/1248행0; VSL 제한47주기. 계수 재보정·새 런 없이, 다음은 후반 도시 신호·VSL 선택의 비용 오판과 실제 합류량을 바꾸는 유한 RM 후보를 분리한다. 순이득 목표는 미완료이며 실행 성공으로 대체하지 않는다. 아래 실행 중 문구는 과거 이력이다.

**현재 실행:** 미삽입 대기를 native로 기록하는 정본 runner 보완과150초 실제 대조가 통과했다. `native_cost150_validation.json`: 이전 방식과18,745 FZP행 전체 일치, LDP/readback PASS, 실제 native `DelayLatent` 수집 확인. 새 계수 보정 없이 동결본으로 **무제어→SDMPC9000초** 유한 큐를 시작했다(session9778, `D:/VISSIM_runs/20260927_sd31_closedloop9000`). 아래 과거의9000미시작 문구는 이 기록으로 대체한다. 이 실행은 남은 이득 검증이며 완료·순이득을 아직 주장하지 않는다. 런 중 추가 예측·보정·FZP 분석은 하지 않는다. 종료 후 기존 분석기 `native_pair1200/analyze_pair.py --closed-loop-9000 --runs-root D:/VISSIM_runs/20260927_sd31_closedloop9000`, 이어 `--cached-diagnostics`를 사용한다. 사용자STOP과 현재 세션을 확인하고 중복 실행하지 않는다.

최신 재확인: 보정 범위를 반복해서 넓히지 않는다. 절대 속도·개별 도착 시각·모든 후보 순위의 일치를 다음 실험의 선행 조건으로 삼지 않는다. 차량 보존, 명령 실행, 비용 누락 여부를 유지하면서 실제 선택에 영향을 주는 큰 오차만 수정한다. 작은 예측 차이는 불확실한 것으로 다루고, 실제 폐루프 비교에서 유용성을 판단한다. 아래 미완료 진단과 기각한 계수 후보를 모두 해결해야 9000초 비교가 가능하다는 뜻은 아니다. 전체 비용을 유리하게 바꾸거나 순이득 확인 없이 성공을 선언하지 않는 원칙은 유지한다.

METANET으로 VISSIM의 개별 차량 도착·속도·재고를 완벽히 맞추는 것은 목표가 아니다. 아래 기존 단계에서 절대 예측 정합을 별도 통과 조건처럼 읽지 않는다. 목표는 유지하되, 의사결정을 뒤집는 오차에만 다음 수정을 집중한다.

- 평가 중심은 공통 초기 상태에서 실제 실행 가능한 후보의 ΔTTT, 램프·도시·외부 대기를 포함한 순비용, 후보 순위다. 비교 영역과 비용 정의가 다른 수치는 섞지 않는다.
- 미세한 차이는 무조건 부호 일치를 요구하지 않고 불확실한 동률로 남긴다. 유의미한 이득·손해의 구분, 자유류에서 불필요한 제한 회피, 혼잡 예방과 회복 시 해제의 선택을 확인한다. 관측 변동을 확인하지 않고 임의 허용오차로 통과시키지 않는다.
- 차량 보존, 실제 액추에이터/변경 한도, 비용 누락·이중계상은 유지해야 할 기본 조건이다. 속도 RMSE나 개별 차량 시각의 정밀 일치는 완료 조건이 아니다.
- 모든 후보의 정확한 부호·순위 일치도 완료 조건이 아니다. 선택한 명령 때문에 발생하는 실질적인 손실과 대기 전가를 기준으로 판단한다. 거의 같은 후보의 순위가 바뀌는 것은 보정을 계속할 이유가 아니다. 한 실패 상태를 완벽히 맞추려고 계수·물리항을 계속 추가하지 않는다.
- 기존 혼잡2670.1초 공통 상태에서 미터 해제의 동측 본선+램프 ΔTTT는 실측+4.7042, 예측−0.1794대·시간이다. 이미 확인된 이 선택 오류를 우선 다룬다. 전체 Ω 비용으로 확대 해석하지 않는다.
- 기존 반응 자료로 가장 단순한 수정을 평가하고, 별도 상태에서 선택 방향을 확인한 뒤 제한된 SDMPC 한 주기 선택·짧은 실행으로 넘어간다. 모든 도시 링크와 개별 차량의 도착 오차를 해결할 때까지 연결을 미루지 않는다. 전체 목표의 9000초 비교는 유지한다.

이번에 막 작성하던 공간별 gate 도착 시간 세분화는 미검증 상태로 보류했다. `physical_ramp_branches.py`는 마지막 검증본 SHA35792503cd08로 바이트 일치 복원했고, 미검증 수정은 `executed_sources/physical_ramp_branches_paused_spatial_ac693d175bb6.py.txt`에 보존했다. `gate_projection10695.json`도 미사용 후보이며 채택하지 않았다. 완료된 수정·자료는 보존했고 새 예측·VISSIM 런은 수행하지 않았다.

## 기존 진행 이력

사용자가 선택지 1을 확정하여 작업 재개. 실수로 삭제한 목표를 2026-09-26 다시 생성했고 목표 도구 상태는 active다. 9000초 실행은 아래 물리·선택·실행 검증 통과 후 수행한다.
작업 기준은 upstream 886a014이며 기존 sd31/control-full-review의 변경과 결과를 보존한다.

1. **완료 — 기준 선택·초기 연결:** 대조 완료. 기존 gain 네트워크 SHA64cf5f55와 최신 코드 886a014를 선택했다. 선택한 망의 입력·경로·DSD를 보존한 설정 묶음을 구성했고 실제900초 관측 초기화가 통과했다. SELECTION.md 참조. 다른 망의 결과를 같은 실험으로 합치지 않는다. 새 upstream의 현행 v3b는 별도 검증 대상이다.
2. **진행 중 — 물리 반응·도착 예측:** native1135 미래 경로·목적지별 이동 지연·과거 짧은 녹색 누적·10633 실제 head 연결을 선택적으로 구현했다.900·1050·1200초에서10681 도착 예측이 개선됐지만10646 등 잔여 오차가 남는다. 선택망6개 VSL 구역의 ownership 오류도 수정했다.1200초 동일 초기 상태에서9개450초 합법 후보를 비교했으며, RM 총합류량 변화는 작고 VSL 비용은 증가했다(HEAD_AND_LEVER_REVIEW.md). 혼잡2670.1초 공통 상태4조건 재생에서 실측 미터 해제 손해+4.704대·시간을 예측−0.179로 잘못 판단했으며 이전 물리 배열과 정확히 일치했다. 실제 합류 → 병목 방출·회복 → 대기 비용의 반응 오차를 계속 좁힌다(CONGESTED_REPLAY_AND_NEIGHBORS.md).10625 신호 전 분기와 목적지 배정, 관측된 방출 하한과 실제 포화 서비스율의 구분도 남는다. 이미 기각한 반응/분산 후보는 승격하지 않는다.
3. **대기 — 이득 검증:** 공통 초기 상태 NC/RM/VSL/both와 독립 상태/seed에서 유량·재고·대기 포함 ΔTTT·후보 순위가 맞는지 검증한다. 짧은 물리 검증 실패 시 긴 검증을 늘리지 않고 원인을 좁힌다. 항상 양의 이득을 강제하지 않는다.
4. **부분 진행 — SDMPC 연결:** 선택망6구역 후보·가격 차원·입구 고정 회귀 검사는76개 테스트·57 subtest 통과. 이어 1200초 저장 상태의 실제 한 주기 최적화·미분·선택·명령 출력 완료(343.26초, PFO2회/SDMPC2회 각각 수락, 수렴 미확인). VSL100→90→90과 도시 신호를 선택하고8미터는 개방했다. 근사 Ω TTT−0.71466%. 별도 실행 모델의 과거−0.46009%는 진단 helper의 다중 블록 적용 누락으로 검증 근거에서 철회했다. 이후 native3000 비교 완료: Ω TTT−2.263%, Ω 밖 실제 체류 포함−0.256%, 미삽입 대기 적분은 미측정. 실제 선택·실행 연결은 확인됐으나 전체 순이득 검증은 남는다. `DECISION_RESPONSE_AND_SELECTION.md`, `closedloop3000_analysis/README.md` 참조.
5. **대기 — 실제 9000초:** 짧은 native 실행과 LDP/적용 readback 검증 후, 동일 망·수요·seed·평가 영역의 무제어와 비교한다. TTT는 Ω 체류시간이며 외부 미삽입 대기는 별도 및 합계로 보고한다. TTD는 정상 Ω 외부 유출 사건이고 내부 이동·삭제·종료 잔여는 제외한다.

VSL 50/60/70/80/90/100/110, 입구110 고정, RM 녹색 변경±2초, SimRes10/FZP5초를 유지한다. seed31/37/41은 새 런에 쓰지 않는다. 내부 적분 간격은 native 기록 간격과 별개이며 현재 검증된 간격을 임의로 늘리지 않는다. 300초 최초 실제 무진행 시 해당 런 소유 PID·생성시각을 확인해 처리한다. 다른 프로세스 개입·자동 재시도·별도 승인 없는 push는 하지 않는다.

완료 기준: 비용·유량을 유리하게 보이도록 바꾸지 않고, 실제 유리한 명령과 불리한 명령을 구별한 뒤 SDMPC의 실행 결과까지 확인한다. 결과가 불리하면 실패 근거를 보존하고 원인을 수정한다.

## 최신 실행: 1200초 재생 완료,3000초 폐루프 진행

`native_pair1200/README.md`: 두1650초 런 종료. 제어 전658,679행 FZP 원본까지 일치, 실제 명령·VSL readback·168SG LDP 검증PASS(LSA는 별도FAIL).450초 선택의 실측 Ω ΔTTT−0.042667대·시간, Ω 밖 체류+0.199889대·시간으로 명확한 순이득은 확인하지 못했다. 이 작은 차이에 대한 재보정은 하지 않는다.

`closedloop3000_status.json`: 같은 동결 코드·선택망·seed29의 무제어→실제 SDMPC3000초 유한 큐를 시작했다. 고정 명령 재생과 달리 매150초 새 관측으로 최적화한다. `run_closedloop3000.ps1`은 기존 watchdog/runner를 호출하며, 실패하면 멈추고 다른 프로세스나 성공한 결과는 건드리지 않는다. 통합 실행 session90504; `D:/VISSIM_runs/20260926_sd31_closedloop3000`. 런 중 FZP 분석/보정은 하지 않는다. 전체 이득 검증과9000초 런은 여전히 미완료다.

첫3000초 비교의 NC1350 수치 오류는 재현·수정·검증했고, 실패본은 보존했다(`NC1350_NUMERICAL_FIX.md`). 현재 유효 큐는 `D:/VISSIM_runs/20260926_sd31_closedloop3000_v2`, session28012이며 새 동결SHAec097d6890…를 사용한다. 계수나 물리 조건을 바꾸지 않은 부동소수점 방어 수정이다. 원본 큐는 종료됐고 새 큐를 중복 실행하지 않는다. 두 arm 종료 후에만 기존 분석기의 `--closed-loop-3000 --runs-root D:/VISSIM_runs/20260926_sd31_closedloop3000_v2`로 비교한다.
# Latest continuation: NC3000 complete, SDMPC3000 remaining

The v2 NC arm completed normally at 3000 s (`STAGE=SIM_DONE`, watchdog `OK`).
The driver then stopped at its next-arm VISSIM guard. Session 28012 is terminal
(exit 1); the subsequent CIM snapshot confirmed that no VISSIM/cscript remained.
The failure receipt is preserved as `nc_complete_queue_transition_failure.json`.
The existing driver now supports explicit `-ResumeAfterCompletedNc`, requiring
the completed matching seed/network/frozen-runtime provenance, and waits up to
30 seconds for a COM server to close before refusing a new arm. It terminates
no process and never replays the completed NC arm.

Resume preflight passed. Session **77438** now runs only the remaining SDMPC arm
in `D:/VISSIM_runs/20260926_sd31_closedloop3000_v2`, with the same frozen runtime
SHA `ec097d6890d60bbb90d8fbeec42a279ad198afaaa7be5dfe6fcca7ef433798b8`.
No model coefficients or traffic conditions changed. Wait for this session;
do not launch another run or analyze FZP until both arms have closed.

## 2026-09-27 3000s comparison complete

Session77438 finished exit0; both native arms closed. See `closedloop3000_analysis/README.md`: Omega TTT -2.263%, physical network residence -0.256%, uninserted queue-time not measured. Native LDP/readback PASS; RM stayed open. All324 east-meter local derivatives were zero. The bounded existing probe now evaluates held plus8 legal one-meter sequences from the completed2700s state (session71853). No fitting, no optimizer, no VISSIM. Do not restart the completed3000s queue;9000 remains unstarted and gain NOT_QUALIFIED.

## Latest: bounded meter audit complete

Corrected9 fixed predictions completed (session42535 exit0), with actual control blocks0/1/2 verified. See `closedloop3000_meter2700_sequence_v1/README.md`. No material predicted gain at this2700s state; no coefficient change, no forced meter reward. The diagnostic helper previously ignored future blocks; `closedloop3000_meter2700` and `select1200v3_check` are marked invalid as multiblock evidence. Production SDMPC already uses the scope; native results stand. All owned jobs are now closed. Next use existing matched physical RM-response evidence to distinguish weak legal actuation from a missed material gain; avoid broad absolute-speed fitting. Goal active,9000 NOT_STARTED,NOT_QUALIFIED.

## Latest: bounded physical alternatives closed; no adoption

The two anticipation alternatives (34 rollouts including parity) and flow-weighted merge inlet (18 including parity) did not improve choices in four development states. Keep production parameters unchanged and the optional merge-inlet path OFF. Ten accounting tests passed; implementation correctness is not gain qualification. See the latest section of `DECISION_RESPONSE_AND_SELECTION.md`. No new native run, no running owned job. Do not widen the parameter search to pursue exact trajectories or exact ranks among nearly tied choices.

## Latest: proxy diagnosis and decision-regret check complete

16 bounded forecasts completed (sessions99084/11179 exit0). Removing the held off-entry proxy improves some absolute flows but worsens the release cost response; not adopted. Re-ranking the existing15 candidates by training choice regret selects delta4/E2, frozen before8 checking forecasts. Checking-state regret decreases3.7458→2.9542veh-h but10484 release is still selected incorrectly; partial diagnostic improvement only, no production adoption. No new training grid/native run. Next inspect the existing mainline/ramp receiving allocation against the observed downstream discharge response, distinguishing free storage from sustainable flow. Keep the complete9000 goal active; do not demand exact speed trajectories or call this partial result qualified.

## Latest: receiving audit closed; extended diagnostic incomplete

The shared-receiving audit (2 parity rollouts) found no double allocation of storage. Its storage bound did not bind; the equilibrium FD peak is not established as a hard transient capacity. The lane-drop ablation (18 forecasts including parity) did not improve choices and is not adopted. Reports: receiving_audit/README.md and lane_drop_response/summary.json.

The fixed 900-second meter-tail diagnostic is incomplete. Session98579 exited1 after the held arm's first three150-second blocks: continuation beyond the existing450-second aggregate prediction window raised a clock/horizon mismatch. Preserve closedloop3000_meter_tail_v2.log and the partial folder; no conclusion about the900-second RM effect, no automatic retry. An earlier separate ledger roundoff error was reproduced and corrected without relaxing stock/overdraw checks (52tests passed). No owned calculation/native job remains running. This extended diagnostic is not itself a requirement for precise VISSIM reproduction. Production horizon, parameters and native results are unchanged;9000 remains not started.

