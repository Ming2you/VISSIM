# VSL 유지·다구역 반응 검증 — 2026-10-15

탐색 보완은 개발 소스에 구현했다. 동역학 보정과 새 기능의 native 채택은 아직 미완료다.

90km/h를 2·3블록 유지하는 단일 구역과 인접/방향 전체 구역 조합을 최대25개 직접 검사한다. 각 성분이 따로 손해여도 조합은 검사한다. 기존 전체비용과 NP/NUF·액추에이터·물리 제약을 통과한 경우에만 선택한다. 기본값은 OFF이며 별도 설정에만 활성화했다.

## 완료된 검증

- 신규 VSL9개 + 기존 RM9개 시험 통과. 파라미터 검사 PASS.
- 실제 저장2250/3300초 상태에서 각각27개, 총54개450초 예측 완료. 실제 좌표·신호 writer·RM 불변·차량보존 및 수용량 검사 통과.
- 이 단계는 전체 최적화나 VISSIM 실행이 아니다. 예측 NP/NUF까지 통과한 의사결정으로 주장하지 않는다.

|90 적용 방식|2250초 ΔΩ TTT|3300초 ΔΩ TTT|
|---|---:|---:|
|병목150초|+0.6490|+0.8275|
|병목300초|+0.9294|+1.1928|
|병목450초|+0.9416|+1.2053|
|동측 인접2구역450초|+1.1394|+1.4726|
|동측4구역450초|+1.9367|+2.3448|
|동서8구역450초|+5.1490|+4.9037|

단위는 대·시간, 양수는 모델이 예측한 손해다. 같은 저장상태와 같은 신호/RM 계획에서 VSL만 바꿨다. 실제 VISSIM 효과는 아니다.

## 동역학 판단과 다음 단계

기존 인과 대조의 회복 오차는 상태에 따라 다르다. seed67의450초 병목 재고는 실제116/모델151.16대인 반면, seed71의VSL+RM300초는 실제145/모델103.62대·속도32.46/53.74km/h다. 그래서 VSL에 공통 이득계수를 붙이지 않았다. 내부 경계 실측 유량이 없는 캐시는 미확인으로 남겼다.

완료된 OFF2250 hold·단일90 대조를 재사용할 수 있는지 검증하고, 같은 명령에서 인접2구역90의 추가 native 조건 최대1개만 준비한다. 새 탐색 경로의 전체 SDMPC 선택도 최대1회 검증한다. 세부 한도·중복 방지·실패 보존 규칙은 plan.json에 기록했다.

기존 앱 보정 목표는 blocked·미완료라 새 목표 등록이 거절됐다. 완료로 바꾸지 않았으며 이 후속 계획과 자동화를 통해 계속 작업한다.

## 전체선택 후속 검증 완료

전체 선택 395.4초, 새25개 VSL 검사 38.5초. 모든 후보가 동일cap·물리 제약을 통과했지만 비용 이득이 없어110을 유지했다. 최종 명령3블록·writer 바인딩이 통과했다.

선택 후 이산 실행모델2예측도 완료: 이전 명령 544.748127, 선택 명령 543.957228대·시간. 선택 명령의 물리·NP/NUF 제약 통과. native 개선 또는 수렴/최적해를 뜻하지 않는다. 탐색 구현 검증은 완료했고 동역학 보정은 진행 중이다.

기존 OFF2250 기준선의 실행·관측·명령 바이트10개 검사는 통과했다. 다음은 정본 사전검사를 거쳐 기존 단일90 자료를 재사용하고 다구역90 조건만 최대1회 추가하는 작업이다.

## 실행 준비 인계

선택 명령의 이산 실행모델 ΔTTT는 유지 명령 대비−0.790899대·시간이며 VSL은110이었다. 이는 다른 제어수단을 포함한 모델 내부 선택 결과이고 native 개선이 아니다. 검증 초기의 설정 객체 동일성 검사는 solve 내부 deep copy를 고려하지 않은 검증 코드 오류였으며, 예측 전 중단 자료를 보존하고 올바른 private context에서2예측을 완료했다.

원본49.45GB는D여유46.53GB를 초과했다. 기존 solo355 소형 패키징 정책으로 코드·실행입력1.65GB를 별도D패키지에 복사/해시 확인 중이며 원본과 과거 결과를 삭제하지 않았다. 복사 첫 시도의 Windows긴경로 오류와 스크립트를 보존했고, 기존 복사분의 해시를 확인하며 이어간다. 정확한 소유정보는package_copy_launch.json, 완료조건은native_package_receipt.json이다. 아직 정본 사전검사·동결·새native는0회다.

## 2026-10-15 새 목표 ACTIVE

사용자가 기존 목표를 삭제한 뒤, VSL 유지·다구역 손익 예측과 탐색 보정 목표를 실제 앱 목표로 등록했다. 과거 blocked/등록거절 문구는 현재 상태가 아니다. 실행 패키지 복사와 소유 종료가 확인됐다. 준비v1은 재생런에 없는 derived obs150 파일에서 예측 전에 중단됐고 자료를 보존했다. v2는 기존15시각 입력·prefix 일치 검증을 통과한 원래OFF 관측과 실제hold 명령을 사용한다. preparation_launch_v2.json이 현재 소유권 정본이며 아직 native 실행은0회다.

## 2026-10-15 17:22 KST continuation

The app goal is ACTIVE. The matched recorded-city/RM forecasts completed exactly once: held110 542.031074 vehh, single-zone90 +0.921683 vehh, adjacent-two-zone90 +1.111329 vehh. All three passed physical constraints. These are model predictions, not observed native effects. The completed 54 saved-plan forecasts and full selection were not repeated.

Preparation v1/v2 failed before forecasts (missing replay-derived observation sidecar / omitted packaged input), and both failures are preserved. v3 uses the original OFF observation history already proven identical to the completed hold baseline, with the actual hold city/RM commands. Three witnessed runtime dependencies were copied byte-identically; the original package import provenance is preserved. No plant coefficient or production source was changed by this repair.

Canonical preflight passed once. Canonical freeze was dispatched once (PID38064, UTC2026-10-15T08:18:59.0523529Z). The existing owned-run wrapper pattern was adapted to one selected arm and dispatched once (PID45304, UTC2026-10-15T08:21:34.1532414Z). At this checkpoint it is waiting for the existing freeze, runner_invocations0/native_launches0. Read current runtime pair_state.json and receipts; do not launch another wrapper/freezer/runner. The native budget is one additional2700s replay, zero retries. Active source and frozen files are immutable. Actual closure and conditional native comparison remain pending; calibration is not complete.

## 2026-10-15 17:48 KST: native failure and offline writer repair

The selected native attempt stopped at2250 before applying the first treatment command: ACTION_CSV_CONTRACT invalid=213, then ACTION_CSV_INCOMPLETE. Runner exit1 and all recorded owner identities, including VISSIM and wrapper, are confirmed closed in runtime/failure_owner_closure.json. This is not SIM_DONE2700 and supplies no multizone450 response. Native budget1 is consumed; retries0. Automatic monitor vissim-2 is PAUSED; the app calibration goal remains ACTIVE and incomplete. The prepared paired analyzer/horizon scripts are not eligible to run on this failed native.

Root cause is in this task's replay preparation: offset_writer='experiment' was passed to the canonical writer, but the metadata copied from the old action JSON lacked the three experiment declaration tokens present in the successful old CSV. The existing physical comparison intentionally excluded metadata and missed this. The native validator correctly rejected every row. This is a preparation error, not a plant-physics outcome.

The writer-only repair uses the production offset_promotion.action_metadata path and the already validated physical signal contract. It writes a separate command_metadata_repair folder and does not alter the failed source, frozen tree or results. All three blocks retain the exact city/RM/other VSL fields; only DSD59..66 change110to90. Every metadata field now matches the validated baseline. The exact ExperimentMetadataValid function extracted from the native VBS rejected639/639 original rows and accepted639/639 repaired rows; missing/duplicate declaration fixtures6/6 rejected. Native simulation, optimizer and forecast invocations during repair:0. Evidence: metadata_repair_verification.json and native_metadata_probe_source.json.

An explicit request for one replacement native attempt is pending because the prior finite authorization was one attempt with zero retries. No new native dispatch is authorized by this document. Independent offline work can continue from existing qualified cases; do not mark the overall calibration goal complete or treat this failed run as a VSL-response result.

## 저장된 VSL 전달·FD 경로 검사 완료

새 예측/최적화/native 없이 matched3 예측의 고정 유량으로 코호트를 복원했다. 상위 옵션이 없어도 실제 하위 플랜트에는 Carlson A0.5/E2가 활성화됨을 확인했다. 병목의90 노출은 첫150초 약49%, 이후 약92%여서 유지명령 미전달은 확인되지 않았다. 같은 밀도의 직접 FD 목표변화는 접근/병목에서 주로 감속 방향이며, 일부 고밀도에서는 반대 방향도 나타난다. 실제 손익이나 새 계수를 확정하는 증거는 아니다. 원본/동결본/계수 변경0; 상세는 cached_vsl_exposure_audit_v2/README.md와 summary.json. 첫 진단의5초프레임=내부사건구간 가정 실패를 보존했고 v2에서 실제207/208개 사건 구간을 사용했다. 추가 native 승인 질문은 여전히 미응답이며 재시작하지 않는다. 앱 목표 ACTIVE·보정 미완료, 자동 native 확인은 PAUSED.

## 추가 실행 승인 대기 — 앱 목표 BLOCKED

승인된 native1회/재시도0회 한도가 소진된 상태에서 추가실행 승인 미응답이3개 연속 목표 턴에 이어졌다. 독립 저장자료 검사는 완료했으며, 현재 새 두 구역 실제 반응자료가 없어 요구된 보정을 검증할 수 없다. 실제12개 소유PID의 종료와 runner exit1을 성공한 CIM 조회로 재확인했다(blocked_owner_revalidation_v2.json). 첫 CIM 접근실패 자료는 명시적으로 무효이며 종료 근거가 아니다. 앱 목표는 실제 BLOCKED로 변경됐고 미완료다. 기존 실패/수정/예측자료와 질문을 보존하며, 승인 없이는 추가실행하지 않는다. blocked_audit.json에 범위·차단조건·재개조건을 기록했다.

## 2026-10-16 승인된 수정본 추가1회

사용자가 "수정본으로 1회 추가 실행"을 명시적으로 승인했다. 이전2250초 실패와 동결본을 보존하고, 새 runtime/result/command packet에서 추가1회·재시도0으로 진행한다. 정본 사전검사는 통과했고, 동결PID45764와 대기wrapper PID19488이 각1회 시작됐다. 최신 소유·진행 기록은 D:/VISSIM_runtime/20261016_vsl_multizone2250_repaired 아래 영수증과 pair_state.json을 따른다.

이미 검증된639개 수정 명령을 복사했고 도시/RM/다른VSL 값은 이전 준비와 같다. 초기 설치 검사의 메타데이터 문자열 일치 가정은 램프 부가태그 때문에 쓰기/실행 전에 멈췄으며, 검증된 기준선의 전체 메타데이터와 행별 비교하도록 바로잡았다. native 추가실행을 소비한 실패가 아니다. 완료된 예측·writer·테스트를 재실행하지 않았다. 분석 경로만 새 실행으로 바꿨으며 SIM_DONE2700/runner exit0/모든 소유와wrapper 종료 전 분석하지 않는다. 앱 목표 도구가 마지막으로 반환한 상태는BLOCKED·미완료이며, 새 승인을 받아 실제 작업은 재개했다.

2026-10-16 실제진행 확인: FREEZE_DONE606.8초,54837files/3977461050bytes,manifest9fc42fe719be1fb6f871e04f09c5d8f5e1248828920936d205da0602c4e1a055. 정본runner PID14344 생성UTC2026-10-16T04:35:48.9066113Z, VISSIM PID3320 생성UTC2026-10-16T04:36:30.7586930Z. 추가native1회 시작,최초실제1초와 현재150초 이상 진행 확인. first_actual_progress.json 참조. 기존실패1회와 승인된추가1회를 구분하며 이후 재시도0. 완료/성능판정은 아직 하지 않았다.


## 2026-10-16 수정본 정상 완료 및 조건부 VSL 비교

추가 승인된 1회는 SIM_DONE2700/runner exit0이며 wrapper 포함 13개 소유 기록 종료를 확인했다. 명령 19회 모두 성공, 실패·유지 0회다. 이전 실패 자료와 STOP을 보존했고 자동 재시도는 없다. 실제 DSD 및 승인된 LDP 검증을 통과했으나 LSA coverage 누락은 유지했다. 입력 15시각·초기 미시상태·전체 prefix 일치로 기존 예측 대조 자격을 통과했다.

두 구역90의450초 Ω TTT는507.233169대·시간,110기준507.279002 대비−0.045833(약−0.009%)로 거의 중립이다. 모델은+1.111329 손해를 예측했다.150/300초 실제 차이는+0.041556/+0.138722다. 동측 본선의 모델 유출·진출 감소와 재고 회복 반응이 우선 점검 대상이며, 실제 내부 유량이 없는 현재 캐시로 특정 계수의 결함을 확정하지 않는다. 작은 부호를 맞추는 보정/생산 계수 변경은 하지 않았다.

분석 detached 프로세스의 도구 부모 종료에 따른 정리를 최소 생명주기 검사로 확인해 부모 대기 방식으로 실행했다. 성공한 native 분석1회/캐시 horizon 요약1회, 새 예측0이다. 상세 영역·외부대기·유출·잔여와 한계는 [결과 보고서](native_analysis_repaired_20261016/RESULTS.md), 정본 완료는 native_analysis_repaired_20261016/completion_receipt.json이다. 이 문단이 앞선 진행/승인 대기 상태보다 우선한다. 이번 유한 자동확인은 결과 보고 후PAUSED, 앱 목표의 실제 상태는BLOCKED·미완료다.


## 2026-10-19 오프라인 후속 — 목표 ACTIVE·미완료

실제 앱 목표는 ACTIVE로 확인했다. 앞선BLOCKED 문구는 역사이며 유한native 자동확인은PAUSED를 유지한다. 새 저장 관측에서 접근부14–18 통과량은 두 구역90 실제+31대/모델−28.868대, 재고는실제−30대/모델+26.052대로 확인했다. 속도 갱신3,115개를 정확히 복원했고 실제 분기 연결과240개 차로 단면, 기존seed67/71의6개horizon 비교를 추가했다. 모든 새native/예측/최적화/FZP/생산 변경은0이다. 일괄 방출 확대나차로 감소항 제거는채택하지 않았다. 상세와남은검증은[outflow followup](outflow_followup_20261019/README.md), 정본 결정은outflow_followup_20261019/decision.json이다. 보정 완료가 아니다.


희망속도분포 연결 후보의2026-10-19검증은[outflow distribution report](outflow_followup_20261019/distribution_README.md)에 기록했다. 최신인계는outflow_followup_20261019/distribution_decision.json이며 이전decision은역사로보존한다.


## 2026-10-19 공간 분할의 미보정 시험 판정 정정

공간 분할 2예측은 기존 부모 계수를 그대로 적용했으며 반응 개선에 실패했다. 이는 미보정 후보의 채택 실패이며 공간 분할 모델 자체의 기각이 아니다. 사용자 지적에 따라 판정 범위를 정정했다. 저장된 속도 갱신 3개를 복원해 밀도차 반응으로 가운데 구간 속도가5초 뒤 하한5km/h에 걸림을 확인했다. 보존/CFL 통과만으로 동역학 적합성을 확정하지 않는다. 다음은 시간 적분 민감도와 해상도별 제한적 기본 동역학 보정의 필요성을 분리하는 작업이다. [정정 및 근거](outflow_followup_20261019/refinement_qualification.md), 최신 인계 outflow_followup_20261019/refinement_decision.json. 기존 수치/실패 자료 보존, 새native0, 목표 ACTIVE·미완료.


## 2026-10-19 내부 시간간격 및 해상도별 기본 보정

내부1.25/0.625초의분할hold/selected4예측을완료했다. 초기속도하한충돌은줄지만통과량반응은약−28.9대이고실제+31대와차이가남는다. 완료된hold110에서새175m관측360프레임을추출하고사전분리한시간대에서두해상도의동역학3계수만각1회보정했다. 두해상도모두1/τ=0의퇴화해로가므로유한물리계수진입조건미통과이며생산채택/후속예측은없다. FD와동역학의공동식별문제를검토하는것이최신다음단계다. [상세](outflow_followup_20261019/refine15_calibration/README.md),최신인계outflow_followup_20261019/refine15_calibration/decision.json. 공간분할자체를기각하지않는다. 새native0/목표ACTIVE·미완료.


## 2026-10-19 공간 세분화의 공동 계수 보정 1단계

FD·동역학5계수의 제한된 궤적 갱신1회와16예측을 완료했다. 보정 구간 속도 RMSE15.96→13.48km/h, 차량 수5.51→5.32대로 줄었으나 별도450초 통과량 반응은−28.88→−29.44대로 실제+31대와 불일치한다. 보정 목표 표본에는 저속 정체가 부족하다. 이 비수렴 후보는 채택하지 않으며 보정된 공간 모델 자체를 기각하지 않는다. 최신 다음단계와 근거는[공동 보정 보고서](outflow_followup_20261019/refine15_joint_fit/README.md),정본인계는같은폴더decision.json이다. 기존자료/완료예측재사용,새native0,목표ACTIVE·미완료.


## 2026-10-19 정체·회복 포함 보정 및 독립 비교 완료

5개 계수의 제한된 갱신 두 번, 보정·개발38예측과 독립seed67/71의8예측을 완료했다. 학습 오차는2.57% 줄었지만 독립 반응의 개선은 일관되지 않았다. seed67 통과량 변화는7.46→7.94대(실제+33), seed71은−11.60→−4.34대(실제−24)로 바뀌었다. 반응시간은 상대변화 하한에 닿았고 비선형 수렴을 확인하지 않았다. 현재 계수는 미채택이며 보정된 공간 모델 자체의 기각이 아니다. [상세 보고서](outflow_followup_20261019/refine15_regime_fit_v3/README.md)와 같은 폴더decision.json이 최신 인계다. 다음은 저장자료의 구간별 오차·민감도 분리이며, 완료 예측을 반복하지 않는다. 새native0·생산변경0·목표ACTIVE미완료.


## 2026-10-19 앞뒤 구간 반응계수의 제한적 보정 완료

기존15번 분할 계수는 고정하고14·18번 구간의 반응시간/밀도차 반응4개 배율을 제한적으로 한 번 갱신했다.16예측 완료/3기준선 재사용/정상 소유종료이며 새로운 native·생산변경은0이다. 학습 오차는7.28% 줄었으나450초 두 구역90 통과량 변화는−31.49→−34.19대(실제+31), 재고 변화는+29.03→+31.52대(실제−30), ΩTTT 변화는+1.1051→+1.1397대·시간(실제−0.04583)로 바뀌었다. 이 후보는 미채택이며 추가 독립 예측을 하지 않았다. 제한된 갱신의 결과로 공간 분할 모델 전체나 충분한 보정의 가능성을 기각하지 않는다.

사용자가 인용한−28.9→−29.4대는 첫5계수 공동 보정 이후 수치다. 최초의 계수 고정 분할 시험과 혼동해 설명한 부분을 정정한다. 당시 보정은 한 번의 비수렴 갱신이고 정체 표본이 부족했으므로 충분한 보정이 끝났다는 근거가 없었다. 최신 근거/후속 범위는 outflow_followup_20261019/refine_boundary_fit/decision.json. 앱 목표 ACTIVE·미완료, 유한 자동확인 PAUSED.


## 2026-10-19 저장된 상호작용 및18번 구간 방출 원인 분리

정상종료와 실행 자격을 이미 확인한 hold/single90/twozone90의 FZP에서 새 희망속도·가속도·상호작용 필드만 세 번 읽어 저장했다. 각92프레임이며 기존 TTT 계산은 반복하지 않았다. 새 예측·계수 보정·native·생산변경은0이다. 모델18번 구간에서는 검사한 모든 블록의 요구 유량이 전부 수용돼, 이번 방출 감소를 해당 경계의 receiving 제한으로 설명할 수 없었다.

실제 두 구역90은450초 누적 Nv/L 수송량 차이+31.47대, 관측 본선 단면 통과량 차이+31대다. 따라서 셀 내부 차량 위치에 따른 저장량 보정만으로 모델의 음수 반응을 설명할 수 없다. 단일구역90은 각각−2.36대/+6대로, 작은 반응에서는 내부 위치 변화의 영향도 있다.5초 적분·반올림·진출 위치 및 단면 계측 한계를 유지하며 잔차를 정상유출로 바꾸지 않았다. 추종 상태만으로 VSL 반응을0으로 정하거나 미래 실측을 예측에 넣지 않는다.

공간 분할 후 계수 보정이 충분했는지는 여전히 미확정이다. 인용된−28.9→−29.4는5계수 공동 갱신 이후 결과지만 비선형 수렴과 정체 학습범위가 확보되지 않았다. 해당 후보의 미채택을 공간 세분화 모델 자체의 실패로 확대하지 않는다. 최신근거는[outflow interaction decision](outflow_followup_20261019/interaction_response/decision.json). 목표 ACTIVE·미완료, 자동확인 PAUSED.


## 2026-10-19 희망속도분포와 혼잡 제한의 결합 후보 준비

기존 평균배율 보정과 구별해,110 조건의 보정된 FD를 그대로 재현하는 공통 혼잡속도 제한을 역산하고 실제90 희망속도분포에 같은 제한을 적용하는 무보정 후보를 만들었다. 이는 Hegyi 등의 minimum 형태와 Vissim2020의 희망속도분포 의미를 참고한 새로운 집계 가설이며 Wiedemann의 구현 또는 검증된 교정식이 아니다. 추가 이득계수·수요·도시/RM·VSL 코호트 전달은 바꾸지 않았다. 새 식의 유출·TTT 이득은 미검증이다.

분포 적분·기준선 역산·110 동일성·비혼잡/고혼잡 극한 등8검사와 호출 연결 검사를 완료했다. 저장된19313점에서 기존 식을 오차0으로 복원했다. 두 구역90의18번 셀에서 기존 직접 목표속도 변화는 블록별−7.105/−8.160/−6.781km/h이고 후보는+0.068/+0.077/+0.030km/h다. 이는 동일한 과거 밀도·노출 비율에서 식만 비교한 값이다. 작은 양수는90분포의 가장 낮은 일부 백분위가110보다 높은 원래 입력 특성을 보존한 결과이며 용량 보너스가 아니다. 새 궤적·유출·TTT 향상으로 해석하지 않는다.

두 조건450초 예측과150/300/450 평가 스크립트는 준비됐지만 예측 시작 전 NumPy 읽기 권한 오류로 멈췄다. 권한 확대 요청 두 번은 자동 승인 검토 모델의 용량 부족으로 실행되지 않았다. 실패 자료 보존, 신규예측0/native0/보정0/생산변경0이다. 원래 자동 실행 제약은 유지한다. 준비된 run_cdf_cap_ready.ps1은 기존 launch가 있으면 재시도하지 않으며 완료 분석을 재사용한다.

상세: [후보와 실행 상태](outflow_followup_20261019/cdf_cap_candidate/decision.json). [Hegyi 등의 원문](https://www.dcsc.tudelft.nl/~bdeschutter/pub/rep/02_015.pdf), [PTV Vissim2020 희망속도 변경](https://cgi.ptvgroup.com/vision-help/VISSIM_2020_ENG/Content/5_Netzbearbeiten/Strassennetz_Wunschg_vWunsch_aendern.htm). 목표 ACTIVE·미완료, 자동확인 PAUSED.


## 2026-10-19 실행 권한 검토 장애로 목표 BLOCKED·미완료

자동 승인 검토 모델의 용량 부족이3개 연속 목표 턴에서 이어졌다. 총4개 권한 확대 요청은 프로세스 생성 전에 실패했으며 새450초 예측은0회다. 준비된 코드/입력 해시와 실행영수증 부재를 재확인했다. 사용 가능한 수식·저장자료 검사와 실행/평가 준비는 끝났지만 전체 결합 예측 및 독립 검증을 대체할 수 없다. 실제 앱 목표를BLOCKED로 변경했으며 완료가 아니다. 상세는 approval_review_blocked_audit_20261019.json. 권한 검토 복구 또는 사용자의 직접 실행 결과가 확인되면 기존 영수증부터 읽고 재개한다. 원본·native·STOP·실패자료는 보존하며 추가 실행을 만들지 않았다.


## 2026-10-19 사용자 재개: CDF 혼잡 제한 2예측 완료, 미채택

저장공간 정리 후 기존 코드·입력 해시를 확인하고 준비된 단일90/두 구역90의450초 예측 두 건을 한 번 실행했다. 과거 자동 승인 검토 장애는 해소됐다. 새 native·FZP 스캔·계수 보정·전체 최적화·생산 수정은0이다. Python14028의 생성시각과 정상 entrypoint exit0/소유 종료를 확인했고, 차량 보존·초기 상태·도시/RM 명령 동일성·조건부 물리 제약을 통과했다. 계산은 예측 자체만 각각6.05/6.22초이며 전체 SDMPC 결정 시간이 아니다. 초기화와 자료 읽기 시간은 별도다.

450초 변화(각110 기준):

| 조건·지표 | 실측 | 기존 모델 | CDF 후보 |
|---|---:|---:|---:|
| 단일90 통과량 [대] | +6 | −20.89 | −0.23 |
| 두 구역90 통과량 [대] | +31 | −28.87 | −0.22 |
| 두 구역90 관심영역 잔여 [대] | −30 | +26.05 | +0.22 |
| 두 구역90 ΩTTT [대·시간] | −0.04583 | +1.11133 | +0.00541 |

과도한 감속/손실 예측은 줄었으나 실제 방출 증가와 재고 감소는 재현하지 못했다. 두 구역 통과량 변화의 절대 오차는 약48% 감소했지만, 작은 전체 TTT 부호만으로 성공을 판정하지 않는다. 새 법칙은 미채택이며 독립 검증/AD/NP·NUF 최적화 검증으로 승격하지 않았다.

저장된5초 기록만 추가로 분해한 결과18번 셀의 누적 Nv/L 변화는 차로1/2/3/4에서−0.003/+11.681/+10.913/+8.882대였다. 합+31.472는 기존 수송 적분과 일치한다. 이는 차로별 출구 통과량이 아니며, 차량 수/속도의 대칭 분해도 인과효과 분해가 아니다. 같은 차량의 관측 차로변경 빈도 차이는 설명적 근거로만 보존했다.

2550초18번 셀의 실측 평균속도는110일 때31.72, 두 구역90일 때75.45km/h지만 모델은58.40/58.32다. 모델이 무제어 혼잡과 VSL하의 회복을 모두 평탄하게 예측하는 오차가 남는다. 다음은 이 구간의 활성 차로교환·속도 회복 식과 독립 기준선 자료로 원인을 좁히는 작업이다. 충분한 근거 없이 VSL 용량 보너스를 넣거나 추가 격자/실런을 하지 않는다.

상세: [완료 판정](outflow_followup_20261019/cdf_cap_candidate/decision.json), [차로별 잔차](outflow_followup_20261019/cdf_cap_candidate/residual_localization.json). 앱 목표 메타데이터는 과거BLOCKED 상태로 남아 있지만 분석은 사용자 요청에 따라 재개됐고, 보정 목표는 미완료다. 기존 실패/STOP/결과는 보존했다.


## 2026-10-20 사용자 요청: 셀별 재보정

현재31개 셀의 활성 FD·반응계수는 이미 개별 설정이다. 다만 마지막159계수 보정은12개 결합 방향, 최대3회 함수평가에서 비수렴 종료했음을 확인했다. 저장된 무제어 자료로16/17/18번의5계수를 각각1회 추정했고, 별도 시간대의 조건부5초 속도 RMSE는31.37→10.96 /23.56→16.71 /21.63→15.62km/h였다. 일부 계수가 기존 탐색 경계에 닿고 자유류·정체의 학습범위가 편중돼 생산 채택하지 않았다. 자율450초/VSL 이득 검증은 아직 아니다. 다음은 여러 기존 무제어 시간대에서 셀별 상태범위를 확보하는 결합 궤적 보정 준비다. 새native/FZP/자율예측/전체최적화/생산수정0, 완료를 주장하지 않는다. [상세 보고서](cellwise_recalibration_20261020/README.md), 최신 인계 cellwise_recalibration_20261020/decision.json. 앱 목표 메타데이터는 조회상BLOCKED이지만 사용자 요청으로 분석을 재개했다.


## 2026-10-20 셀별450초 결합 보정과 독립 검증 완료, 후보 미채택

16–18번15계수의 첫25% 갱신은 학습오차29.9% 악화로 폐기했다. 민감도를 재사용한5% 갱신은 학습오차3.53% 개선했으나 VSL 반응은 해결하지 못했다. 계수를 고정한seed67/71 독립 예측8건도 완료했다. 새native/전체최적화/생산변경0, 각 소유정상종료 확인. [수치와 다음 작업](cellwise_independent_20261020/README.md). 실제 앱 목표는 마지막 조회BLOCKED 메타데이터이지만 사용자 승인에 따라 분석을 재개했으며, 목표완료를 주장하지 않는다.
