# W_out의 이미 선택된 목적지 보존 — 미적용 진단 제안

현재 선택된 `1130:3` 출구 차량이 `SC1004_W_out`에서 다시 `1135` 혼합비율로 분배되는 정보 손실은 확인됐습니다. 이를 차량 수의 별도 저장소를 만들지 않는 목적지 태그로 보존할 수 있습니다. 다만 아래 결과는 초기 관측 태그 보존에 **미래 모형 direct 유입의 native 단일경로 prior**도 명시적으로 포함합니다. 미래 차량의 실제 경로를 관측·복원한 실험은 아닙니다.

운영 파일, 활성 설정, 네트워크, Git은 수정하지 않았습니다. `known_wout_routes.patch`는 현재 정본의 `route_choice_corridor.py`, `urban_flow_accounting.py`, `runtime_setup.py`에만 적용하는 제안이며 아직 적용하지 않았습니다. 기존 legsplit이 재고와 Ω 이벤트를 계속 단독 작성합니다. 새 adapter나 vendor 모델 사본은 없습니다.

## 확인한 정보 손실과 물리 경로

초기 관측의 `physical_stock_assignment_by_link`는 W_out의 차량 수와 실제 링크를 보존하지만 해당 저장소에 목적지 태그가 없었습니다. 이후 `urban_flow_accounting.legsplit_substep_accounted`는 매5초 `arrived→reach`에 기존 `free=.3333/R_F_E=.1667/R_F_W=.5`를 다시 적용합니다. 수신 거절 뒤 남은 차량도 다음번에 재분배됩니다. 이는 초기 선택 경로 보존 오류이며, 이번 재생에서 차량을 이중 생성·인출했다는 뜻은 아닙니다.

| 현재 native route | 실제 경로 후반 | 보존할 기존 목적지 |
|---|---|---|
| 1130:3 | 10682→121→10773→123 | free |
| 1135:2 | 68→10772→121→10646→120 | R_F_W |
| 1135:3 | 68→10772→121→10773→123 | free |
| 1135:4 | 68→10681→2 | R_F_E |

Native1135의 선택 위치는68의7.491513m입니다. 1123:2는68의4.950656m,1125:1은6.322767m에서 끝나며,10625/10629/10633의68 진입점도 선택 위치 이전입니다. 이들 아직 선택 전 차량과 앞으로 해당 도시 movement에서 수신한 차량에만 기존1135 prior를 한 번 적용합니다. 선택 위치 이후 경로를 모르는 차량은 `unknown`으로 유지하여 방출하지 않으며 전체N과 residence에는 남습니다.

Ver2 XML 전체130개 static decisions에서10682를 포함하는 경로는1130:3 하나뿐입니다. 그래서 앞으로 모형 OR_F_E의 **direct 부분**이 W_out에 착지하면 이 native 단일경로 prior로 free 목적지를 부여합니다. 이는10682의 기하만으로 내린 결론이 아닙니다. 같은121의10646 분기가 존재하므로 기하만으로 free를 확정할 수 없습니다. 또한 앞선 FW scalar off 계산이 이미 다른 실제 cohort를 섞는 문제까지 복원하지는 않습니다. 제안은 이 구분을 `known_wout_future_direct_native_path_prior=1`로 표시합니다.

네트워크는 `network/real_world_gaepo_modi/modi_eval_userfix Ver2.inpx`, SHA256 `085a10c71874e897083c97097af8fa3f1f08da1ef7416fef2f7cfbedabdfc317`입니다. 정적 근거는 `known_wout_routes_ver2_proposal.json`이며 configure에서 snapshot의 네트워크 SHA, native 경로/종점,1135 위치,10682 경로 유일성, 기존 positive incoming movement와 물리 connector 대응을 재검증합니다.

## 초기 전체 재고 분류

| 시각 | W_out 전체N | 이미 free | 이미 R_F_W | 이미 R_F_E | 선택 전 | 선택 후 unknown |
|---|---:|---:|---:|---:|---:|---:|
|1200|20|12|4|0|4|0|
|3300|105|34|61|1|9|0|

`known_wout_initial_fixture.json`은 W_out의 모든 현재 기록과 배타적 소유 매핑을 포함합니다. 일부 선택한 차량으로 분모를 만든 표가 아닙니다. 해당 두 시점의 W_out release buffer는 비어 있습니다. 초기pending 합성 회귀는 기존 전체pending을 목적지 비율에 따라 나눠 ready 총량을 보존합니다. 관측하지 못한 ID와pending의 상관을 새로 식별했다고 주장하지 않습니다.

## 같은 행동을 유지한150초 예측

현재 정본 OFF 재생과 후보를 각각 순차 실행했습니다. 모든15회 FW step의 green/RM/VSL/offset이 원본 행동과 일치하며 cfg/state/action/forecast 입력 불변, Ω 전체 재고 closure, 기존 capacity/offratio/directshare/legsplit prior 불변을 확인했습니다. 최종 후보의 추가 validation/metadata는 먼저 실행한 후보와 수치가 정확히 같습니다. 현재 OFF 결과도 보존된 원본 interval 보고서의 model metrics와 정확히 같습니다.

| 시작시각 | ΩTTT 기존→후보 (veh·h) | ΩTD 기존→후보 (veh) | E8 최종 기존→후보 (km/h) | 실제 E8 최종, 평가참조만 |
|---|---|---|---|---|
|1200|111.600511→111.360171|484.779891→497.013899|96.115868→96.115868|40.484740|
|3300|223.728728→223.559246|465.384468→474.614060|12.885553→13.584375|1.952227|

1200에서는 W_out 총 방출30.947684veh와 최종 W_out 재고가 같습니다. 목적지 배분이 달라져 최종 R_F_W57.240509→48.788424,R_F_E19.478210→15.696286이며 ΩTD는12.234008 증가합니다. `flow_counts['legsplit:SC1004_W_out']`는 free와 두 내부램프를 합친 값이므로 이를 ΩTD로 읽으면 안 됩니다. 다른 모든 flow category가 같아 이 차이는 기존 내부램프 목적지와 free 출구 간 배분에서 나옵니다.

3300에서는 W_out 총 방출91.473149→91.350858veh, 최종 R_F_W80.190420→83.629350,R_F_E5.331907→1.419290입니다. R_F_E→본선 실제 수신은75→66.121805veh로 줄며, FE direct/signal 유출은 각각0.017080/0.018209veh 증가합니다. 다른 본선 terminal 유출은 같습니다. ΩTD 증가9.229592veh를 관측 처리량 또는 실제 제어 개선으로 보고하지 않습니다. 실제 R_F_W 최종65veh와의 오차는 오히려 커지며, R_F_E 관측47veh도 재현하지 못합니다.

이 수선은 E8의 빠른 회복 오류를 해결하지 않습니다. 기존10643 exit4386→10639merge4610→10682exit4746→10681merge4899의 물리 순서와 달리 모형의 FE off는cell8, 두 R_F_E merge는cell9에 계속 집계됩니다.1130:3 lane1 접근과38대의 필요한 차로교환 상태도 이번 목적지 태그가 복원하지 않습니다. lane-change 성공률, VSL capacity bonus, 고정 lost lanes 또는 임의 용량은 추가하지 않았습니다.

## 적용 계약과 검증 범위

- `urban.preserve_known_wout_routes`는 엄격한 bool이며 기본OFF입니다. ON에는 기존 corridor/legsplit와 `control_area_enabled=True`, `urban.known_wout_route_evidence={path,sha256}`가 필요합니다. ΩOFF scheduler까지 지원한다고 일반화하지 않으며 ON 조합은 초기 mutation 전 거부합니다.
- `configure_known_legsplit(cfg,tuning,state,raw)`는 `configure_runtime` 마지막의 모든 초기 projection/area 설치 뒤에 한 번 호출합니다. 저장고를 새로 만들거나 초기entry 이벤트를 기록하지 않습니다.
- 도시 `_receive_corridor`와 direct `schedule_offramp_arrivals_accounted`에서 **기존 owner가 실제 수신한 양**만 태그에 추가합니다. 기존ready 시각과 도시 `_link_delay_steps`를 그대로 사용합니다.
- legsplit 요청 전에 목적지별 요청을 만들고, 원래 수신 재조정·재고이동·Ω이벤트 뒤에 같은 actual receipts만 태그에서 차감합니다. receiver 거절은 해당 목적지에 남으며 다른 목적지로 바꾸지 않습니다.
- `known_wout_held_unknown_route_veh`와 별도 completeness를 기존 `route_choice_prediction_route_complete`에 합칩니다. unknown을 보존하면서 완전한 경로로 표시하지 않습니다.
- plain cfg/state 태그는 기존 deepcopy와 pickle로 후보 및 worker별 분리됩니다. 원본 OFF legsplit 한step의 출력과 전체state pickle이 정확히 같음을 확인했습니다.

`run_known_wout_fixture_tests.py`의 최종12회귀는 원래 `evaluation/runs`와 Git 접근을 금지한 test process 및 fresh runtime worker에서 통과했습니다. 수신 거절·잘못된 receipt의 부분차감 방지·unknown 보존·ready 경계·candidate copy·OFF·unsupported ΩOFF 거부를 포함합니다. full MPC, 모든 local follower proxy, 실제 제어효과까지 검증한 것은 아닙니다. 활성 MPC로 옮기기 전에는 local W_out 도착 proxy에도 같은 목적지/ready 계약이 필요한지 별도 점검해야 합니다.

기존 free legsplit의 Ω밖 인출 시점과 coarse travel은 그대로입니다. 실제10773/123의 전체 이동 및 수용을 별도 저장고로 재현하는 수정이 아닙니다. 이 한계를 숨긴 채 TD 증가를 물리적 성능 개선으로 사용하면 안 됩니다.

## 보존·재현 파일

`fixtures/known_wout_v1.zip`은 raw state1200/3300, prior1050/3150, held1200/3300, run provenance 총7파일을 byte-exact 보존합니다. ZIP585,110B, SHA256 `3b75e734296c3f672017a870907b7f579cb17d8fd3183c97ceb42c348ea75494`, CRC와 모든member 원본bytes 검증PASS입니다. 전체 현재 관측을 포함하며 운영 소스/설정의 사본이나 미래관측은 넣지 않았습니다. 기존 `review_fixtures.restore` 규칙에 따라 짧은 `.review-fixtures/kw_*` 아래 raw와 경로만 바꾼 JSON을 분리합니다.

최종 수치는 `known_wout_baseline_current_1200/3300.json`, `known_wout_replay_final_1200/3300.json`, `known_wout_route_comparison.json`에 있습니다. 이전 후보파일은 이력으로 보존합니다. 초기 provenance helper가 분석보고서 속 경로까지 따라가 역사 FZP 등을 hash한 항목은 predictor 입력이 아닙니다. 최종 portable driver는 그러한 불필요한 순회를 제거하고 명시한 fixture와 현재 runtime manifest의 소스/데이터만 pin합니다. 비교 보고서의 미래 실측은 이미 완료된 분석 artifact에서만 읽으며 predictor에는 전달하지 않습니다.

```powershell
python -X utf8 -m diagnostics.run_known_wout_fixture_tests
python -X utf8 -m diagnostics.prepare_known_wout_routes --refresh-patch
python -X utf8 -m diagnostics.probe_known_wout_initial --output diagnostics/NEW_initial.json
python -X utf8 -m diagnostics.probe_known_wout_replay --start 1200 --output diagnostics/NEW_candidate1200.json
python -X utf8 -m diagnostics.probe_known_wout_replay --baseline --start 1200 --output diagnostics/NEW_baseline1200.json
python -X utf8 -m diagnostics.summarize_known_wout_routes
```

실행 시 output은 존재하지 않는 새 diagnostics 파일이어야 합니다.3300도 같은 명령을 순차 사용합니다. `known_wout_routes.manifest.json`의 현재base SHA를 먼저 비교해야 하며, 다른 미적용 head-resource 패치가 먼저 통합되면 해당 새base에서 anchor를 다시 검토해야 합니다. 이번 작업은 Git stage/commit 또는 운영 적용을 하지 않았습니다.
