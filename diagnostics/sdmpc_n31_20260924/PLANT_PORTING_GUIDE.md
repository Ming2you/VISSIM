# SDMPC-31 플랜트 이식 안내서 (2026-09-24)

따로 보정한 본선 플랜트를 SDMPC-31 제어기에 끼워 넣는 절차입니다. 다른 PC에서 작업하는 경우를 기준으로 썼습니다.

- **기준 코드:** `Ming2you/VISSIM` 브랜치 `claude/sdmpc-n31-20260924` @ `7216e25`. 이 안내서는 그 바로 위 커밋에 들어갑니다. 따로 적지 않은 줄 번호는 모두 `7216e25` 기준입니다.
- **사용자 보정 라인:** 브랜치 `codex/control-full-review-20260909` @ `d80faf9`. 두 브랜치의 공통 조상은 `00abbab`입니다. 이 라인의 줄 번호는 `(d80faf9)`로 표시합니다.
- **근거:** 두 커밋의 코드와 파일을 읽고 썼습니다. 이 안내서를 쓰려고 VISSIM이나 저장소 시험을 새로 돌리지는 않았습니다. 망 비교, 생성기 검사, 3-way 병합은 메모리와 스크래치 폴더에서만 확인했고, 해당 항목에 그렇게 적었습니다. **(확인 안 됨)** 표시는 코드를 읽고 추론만 했다는 뜻입니다.

**약어**

| 약어 | 뜻 |
|---|---|
| W | 이 브랜치의 작업 트리 루트 |
| FRZ | 발사용 동결 사본 (`freeze_worktree.ps1`이 만듦) |
| N31D | `diagnostics/sdmpc_n31_20260924` |
| B110 | `diagnostics/demand_sweep/user_native_20260914/metanet_calibration_v1/res10_b110_20260923` |
| CH | `diagnostics/demand_sweep/user_native_20260914/metanet_calibration_v1/canonical_harness.py` |
| LPR / LFR / AFA | `evaluation/controllers/` 의 `lane_plant_runtime.py` / `lane_freeway_runtime.py` / `area_freeway_accounting.py` |
| OC | `evaluation/controllers/obs150_contract.py` |
| HO | `diagnostics/vsl_handoff_20260924` (사용자 인계 폴더, d80faf9) |
| PY / DEP / RUNS | Python 3.12 실행 파일 / 의존성 폴더 / 런 출력 루트 |

> **작성 뒤 추가 (09-24 저녁, 바로 다음 커밋에 들어감):**
> - **VSL 모형 이식:** 사용자 A0.5_E4 모형(Carlson FD, `VSLExposure` 수송)을 FW_E에 이식했습니다.
>   - 표지판 셀은 v2 망에서 다시 뽑아 `[0,3,5,8,14,18,26,28]`입니다.
>   - 명령이 모두 110이면 옛 결과와 비트 단위로 같습니다(G1b 900 상태, 수치 1,329만 개. V5b 3000 상태 목적값 538.152115708005).
>   - 사용자 국소 보정(v_free 108.159, anticipation 18.375, head-service, physical_cell_fd)은 v2 보정을 덮어쓰므로 **넣지 않았습니다**.
>   - 110에서 한쪽 도함수가 살아 있습니다(FW_E seg10 +0.034 veh·h/(km/h)). 아래 §3(d)-3 4번과 §7.1의 "110 불감대" 서술은 이식 전 기준입니다.
> - **VSL 행동 집합 {50,60,70,80,90,100,110}:** 튜닝, reference, 러너 VBS가 같은 집합입니다(`make_config_n31.py:54`, `make_reference_config.py:55-56`, `repin_scenario_v2.py:131`).
>   - 블록 0은 한 결정에 ±40까지 움직입니다(`max_vsl_step`). 110에서 {70..110}입니다.
>   - v2 망에는 일곱 속도 모두 같은 번호의 희망속도 분포가 있습니다. 50·60·70은 좁은 균등, 80–110은 오른쪽 꼬리가 긴 분포라 한 계열이 아닙니다.
> - **VSL 코호트 초기화:** 결정마다 직전에 실제 적용된 행동의 블록 0 VSL을 표지 셀과 그 하류 셀에 심습니다(없으면 110). 출처는 결정 metadata `n31_binding.vsl_cohort_initialization`에 남습니다.
> - **현재 sha:** plant `17871460`, config `3a5cacef`, reference `2c4857f4`, 러너 VBS `b74e05b2`, 검지기 CSV `108debbb`(그대로). 본문 표의 옛 sha는 이 값으로 읽으십시오.
>   - config는 2026-09-25에 `1e58e6bf` → `3a5cacef`로 바뀌었습니다. 램프 도착 예측 표(`local_ramp_arrival_forecast`의 drain·cap)의 키를 옛 그룹 `R_D_W…`에서 런타임 램프 키 `RM_C<커넥터>` 8개로 바꾸고 `strict_ramp_keys: true`를 넣었습니다(`make_config_n31.py`의 `RAMP_FORECAST`). 전에는 키가 맞지 않아 모든 미터가 120 s·900 veh/h로 폴백했습니다. plant·reference는 그대로입니다.
>   - 미터별 drain·cap은 처음에 `f475ce42`의 무제어 런(s31/s41/s37)에서 뽑았습니다. 2026-09-25 v3b 재핀 때 v3b 무제어 런으로 다시 뽑았습니다(아래 절). `--check`가 `RAMP_FORECAST`와 대조합니다.
> - **RM:** V5b(9000 s)에서 SDMPC가 **램프 미터를 한 번도 조이지 않았습니다**. 추적 결과는 VISSIM stage-1의 FW_E 이득 대부분(82%)이 램프 대기로의 전가이고, Ω 전체로는 규칙 RM도 손해(+1530 veh·h, FW_W 역류)라는 것입니다. 플랜트가 틀린 것은 FW_E 내부 구성(B1 대기가 너무 빨리 풀림, 상류 진입 부족)입니다. 세부는 `N31D/RM_GAIN_TRACE_20260924.md`에 있습니다.

> **망 v3b 재핀 (2026-09-25, 사용자 결정 — 이 절이 위 "현재 sha"를 대신합니다):**
> - **핀 망:** `N31D/network/baseline_s31_v3bnc.inpx` = `be0075bf4d5e9e239ffc1e9efb6d70d11c6ec6136e46f1a92d910bc79d813cdc`(원본 `D:\VISSIM_runs\20260925_v3b\s31_v3bnc\prepared\network\`). 옛 `baseline_s31_v2nc.inpx`(`f475ce42`)는 트리에서 지웠습니다.
>   - v3b는 `f475ce42`와 **정적 경로만** 다릅니다: route 목적지 19개(이 중 `33:2`, `1133:2`는 링크열도 짧아짐), 결정 1061 pos 2.341→6.0 m, relFlow 32개(RD 1119 + 되살린 결정 31개). 링크·신호·입력·검지기·`.sig` 42개는 같습니다.
>   - 파일 이름의 "v2"(`config_n31_v2.json`, `plant_n31_v2.json`, `obs150_detectors_v2.csv`, `repin_scenario_v2.py`, `port_profile_v2/`)는 플랜트/시나리오 세대 이름이고 망 버전이 아닙니다.
> - **재핀 도구(`repin_scenario_v2.py`):** `CHANGE_RULES`는 넓히지 않았습니다.
>   - `V3B_ROUTE_EDITS`(:316): v3·v3b 편집 영수증(`147bc732…`, `e0d4bccb…`)을 그대로 옮긴 열거표입니다. 경로가 relFlow 밖에서 바뀐 결정이 이 표의 결정과 정확히 같고, 옛 값·새 값이 모두 맞을 때만 통과합니다(`characterize_changes(route_edits=…)`, :412).
>   - `refresh_membership_relflow`(:791): membership의 relFlow 사본 중 바뀐 결정(1117·1140의 6개)을 v3b 값으로 채웁니다. 경로가 같을 때만 합니다. 런타임은 이 사본을 읽지 않습니다.
>   - `route_path_audit`(:836) + `V3B_PATH_CHANGE_REVIEW`(:826): 경로가 바뀐 route를 인용하는 선언은 검토 표에 있어야 통과합니다. 해당은 `dynamic_area_routes`의 `SC1004_offW_to_E_SC107`(`1133:2`) 하나입니다. v3b에서 (70,10776)·(10776,126) 간선은 `1140:2`만 증명합니다.
> - **v3b 무제어 런에서 다시 뽑은 것:**
>   - 관측: `metanet_calibration_v1/v3b_nc_20260925/observations/s{31,41,37}_v3bnc_observations` (`extract_observations.py`, 영수증은 같은 폴더의 `s*_v3bnc_extraction_receipt.json`). s37에 FW_E 셀 30의 미설명 손실 1대(3460–3465 s)가 있습니다. 램프 행과는 무관합니다.
>   - 플랜트 기하: s31 `geometry.json` `7d330bd2…`. v2 기하(`89011be0`)와 출처 키만 다릅니다.
>   - 포트 프로필 `666fd1a8…`: 10491 +3.80, 10638 −3.33, 10646 −3.02 km/h, 나머지 |Δ| ≤ 1.47. 한 시드, 900 s입니다.
>   - 램프 예측 `RAMP_FORECAST`(`make_config_n31.py:90`): drain 17.4/43.3/30.9/88.0/42.6/161.7/33.3/43.3 s, cap 219/2312/405/514/526/1216/839/611 veh/h (RM_C10480/10482/10646/10644/10639/10681/10490/10484). v2 값은 `derive_ramp_forecast_n31.py` docstring에 남겼습니다.
>   - movement beta: `N31D/beta/movement_beta_routing_v3b_20260925.json`(`e81d545f…`, 370개), 튜닝 `urban.beta.source: routing_v3b`(어댑터 `BETA_EVIDENCE_JSON`). 유도 명령과 sha 핀은 `make_config_n31.py`의 `BETA_*` 상수에 있고, 재현은 `tests/test_n31_beta_source.py`가 확인합니다.
>     - **명시 배정(사용자 결정 2026-09-25):** `scripts/derive_routing_turn_beta.py`의 목적지집합 역추론이 램프 교차로에서 틀렸습니다. SC1004 서측 결정 1124·1126·1138·1140이 전부 E_SC107에 붙었고(1140만 4558대), SC1001 서측 1117은 W/offW/offE 동률로 버려졌습니다. `--explicit-approach N31D/beta/explicit_approach_v3b_20260925.json`(`36162d50`)이 다음과 같이 붙입니다: 1117 → SC1001 W·offW·offE, 1140 → SC1004 W·offW, 1138 → SC1004 W, 1126 → SC1004 offE, 1124 → SC1004 S. 근거는 v3b 무제어 FZP 세 시드의 출처별 실측 출구 분율이며, 같은 파일에 들어 있습니다. 예를 들어 link 127은 출처와 무관하게 0.70/0.20/0.07로 나가고, 1117 relFlow는 0.72/0.21/0.07입니다. 값은 여전히 relFlow(외생)에서 뽑고, 명시 배정은 어느 접근로에 적용할지만 정합니다. 옵션이 없으면 0824 표(`a70222d8`)와 명시 배정 전 표(`f020e36c`)를 바이트 그대로 재현합니다.
>     - 결과: SC1001 W 0.7193/0.2091/0.0716(기본값 0.5/0.25/0.25). SC1004 E_SC107은 설정 기본값으로 돌아갑니다. 0824 표 대비 24개 접근로 movement 73개(유효값 기준), v2 망 표 대비 18개 접근로 58개가 바뀌고 최대 |Δ|는 0.5입니다(예: RD 1119 `SC1001_S_SC1003_to_W` 0.8333→0.3333).
>     - 남은 한계(도시 플랜트 수정 단계로 넘김): (1) 증거가 닿지 않는 movement는 기본 몫을 지킵니다. 예를 들어 `SC1001_offW/offE_to_W` 1/6은 link 127에 서쪽 출구가 없는데도 남습니다. (2) 이름 없는 경계 유출 경로는 그 접근로의 경계 유출 movement들에 균등 분배됩니다. (3) 1126은 실측 0.38/0.39/0.23으로 1:1:1과 다르고, 1138은 실측 약 20%가 세 출구 어디에도 닿지 않습니다. (4) SC1004 W는 1140(계수 4558)과 1138(단위 3)을 relFlow로 합칩니다. 실제 출처 비율은 약 2:1이라 movement당 0.05 이내로 어긋납니다. (5) 런타임 492개 중 474개 밖의 램프 movement 18개는 표에 없어 config 기본 몫을 지킵니다. **정정(2026-09-25):** 표 단계에서는 접근로 합이 1을 넘지만(예: SC1001 E 1.25), 런타임에서는 합이 1을 넘지 않습니다. leg_split 되접기(`install_leg_ramp_split_fold`)가 on-ramp 몫을 W 출구 형제에 더하고, 출구 병합(`install_merged_movements`)이 모든 접근로를 1로 재정규화합니다. 그래서 결과는 합 초과가 아니라 **분율 왜곡**입니다(예: SC1001 S 좌회전 표 0.333 → 런타임 0.429, v3b FZP 0.32–0.34; 설치 단계별 덤프로 확인).
>     - **도시 plant 묶음 1 후보(2026-09-25/26, 기본값 아님, 커밋 전 리드 검토):** `make_config_n31.py --urban-batch1 [--components U1,U3]`이 후보를 따로 씁니다. 전부(U1+U2+U3)는 `config_n31_v2_urban_b1.json`, 일부는 `config_n31_v2_urban_b1_<u1u3…>.json`입니다(U1은 항상 포함). **S1(폐루프) 후보는 U1+U3 `config_n31_v2_urban_b1_u1u3.json`입니다.** U2는 한 스텝 오차를 늘려서 묶음 2(U4)와 함께 다시 잽니다(아래 관문).
>       - **U1(값):** `urban.beta.source: routing_v3b2` + 표 핀 `urban.beta.sha256`(`scripts/derive_routing_beta_physical.py`, 492개 전부, 물리 경로 없으면 0·있으면 relFlow, 재정규화 전 접근로 합 = 1). 이 원천에서는 되접기·병합·off-ramp 직행·`area_dynamic_routes`가 옮기는 β가 0이 아니거나 합이 1이 아니면 실패합니다(`evaluation/controllers/beta_source.py`; 설치와 가드가 같은 술어를 씁니다). 물리 현시 권한 전의 선언 현시로 판정하는 `urban.movements.dead_phase_beta_zero`는 이 원천과 함께 켤 수 없습니다(설치가 거부하고, 후보 생성기도 false를 요구합니다; 2026-09-26 검토). 상태를 받는 `check_complete_beta_runtime`이 표의 망 sha를 스냅샷과 대조하고, 최종 현시(현시 보정·물리 현시 권한 뒤)에서 흐름이 전부 0인 현시가 표의 `phases_without_flow`(이제 SC109_p1 하나) 밖에 생기거나, 흐름(β > 0)이 있는 신호 movement가 선택 계획에서 네이티브 녹색이 없는 현시에 있으면(무신호 제외) 멈춥니다. 유도기도 런타임 현시(병합 가족 단위의 2026-08-28 현시 보정 + 핀된 물리 현시 권한, 병합이 버리는 자기 leg U턴 제외, 표 `runtime_phases`)로 굶김을 판정합니다. 설치(`install_measured_turn_beta`)는 튜닝의 `urban.movements.nonexistent_declaration`·`physical_phase_authority`(파일 sha)·`phase_correction`·`merge_exits`가 표의 `inputs`/`runtime_phases`와 같을 때만 됩니다. `urban.ramp.offramp_direct_route_prior`(relFlow 직행 몫, 그룹별)와 아래 SC7 선언 정정의 키 셋도 U1입니다.
>       - **경계 유출 이름(2026-09-26 수정).** 경계 유출은 물리 out 링크 표(`outputs/out_link_storage_ver2_20260909.json`, 41개 중 24개)가 경로의 링크를 가지면 그 out 링크로, 아니면 커넥터 뒤 링크의 나침반 방향(첫 방향)으로 이름 붙입니다. 한 신호의 경계 유출이 같은 끝 링크에서 서로 다른 out movement가 되면 유도가 실패합니다. 옛 방향 규칙은 SC104 S_SC106 10171(→ 65, 15.5 m, 북향 → 1220061100 = E out)을 N으로 보내 `SC104_S_SC106_to_E`를 0으로 만들었습니다(표 `boundary_exits_decided_by_out_link_table`에 기록). 정지선을 지나는 정적 경로가 없는 접근로라 이제 세 물리 movement의 config 기본값 0.5/0.25/0.25입니다(FZP N 0.66 / E 0.28 / W_SC6 0.06).
>       - **0인 movement 150개(표 `reason`, SC7 정정 뒤; 전에는 152).** 출구 쌍둥이 69, 자기 leg U턴 36, W_out 경유 on-ramp 14, 경로 없음 12, 물리 경로·무증거 9, 회랑 되접기 8, 선언된 비존재 1(`SC109_N_SC16_to_W_SC108`, 물리 경로 없음), 진입표 제외 1. SC1001/SC1004 명세 25개(on-ramp 14 + 공유 커넥터 `SC1004_{W,offW,offE,N_SC1003,S}_to_E_SC107` 5 + 경로 없음 6)가 모두 들어 있습니다. 물리 경로·무증거 9개(SC104 E/N/W_SC6의 6개, `SC107_W_SC100{4,5}_to_N_SC1`, `SC1005_E_SC107_to_W_SC1004`)는 독립 T1에서도 실측 0입니다.
>       - **SC7 E → N_SC11 선언 정정(사용자 결정 2026-09-26, U1, 후보 전용).** 옛 런타임 비존재 선언(`outputs/movement_phase_correction_20260828.json` `known_nonexistent_movements`, 문구 "10332 → SC7_S_SC108"은 v2 해석)이 `SC7_E_to_N_SC11`·`SC7_E_SC16_to_N_SC11`을 0으로 두고, 모형은 이 회전을 녹색 0인 p3로 서비스했습니다. v3b에서는 단일 차로 1210009600에서 10332(→ 1220008701 → 10334 → SC11, 정적 경로 252:3 relFlow 63)와 10333(252:1, 84)이 나가고, 헤드 140101(SG 7-1, pos 114.46 m)이 두 커넥터 상류에 있습니다. SG 1은 선택 계획의 p4(녹색 24 s, `.sig` 개포동 test-bed14 prog 1: 93 s 녹색 시작, 3 s 황색)이고 p3(SG 2/6)는 늘 적색입니다. 바꾼 것:
>         - 선언: `N31D/urban/movement_nonexistent_v3b_20260926.json`(`3135dcda`, 사용자 결정 기록, 두 유도기가 망과 대조). 비존재는 `SC109_N_SC16_to_W_SC108` 하나이고 SC7 둘은 `corrected`입니다. 키 `urban.movements.nonexistent_declaration` {path, sha256}이 있으면 `apply_nonexistent_movement_beta_zero`가 이 파일을 읽고, 없으면 옛 절 그대로입니다(기본·옛 튜닝 비트 동일).
>         - 현시: `scripts/derive_phase_authority_v3b.py` → `N31D/urban/physical_phase_authority_v3b_20260926.json`(`e729cdc4`; 검토 전 `67f46db9`) = 기본 증거(`scenario/physical_phase_authority_local_1df35c.json`) 그대로 + 두 행(헤드 140101, SG 1 → SC7_p4, 경로 252:3). 후보의 `urban.movements.physical_phase_authority`가 이 파일을 가리키고, 런타임 `configure_phase_authority`가 inpx·계획으로 다시 검증합니다. 현시가 바뀌는 movement는 이 둘뿐입니다. 두 행은 기록 전용 필드 둘을 더 가집니다(런타임은 읽지 않음, 망 sha 핀이 최신성을 지킴): `source_lane_connectors`(헤드 뒤에서 같은 정지선 차로를 떠나는 커넥터: 10332·10333)와 `crossed_heads_after_source`(경로가 출발 헤드 뒤에 지나는 헤드와 그 계획 역할).
>         - 값: 표에서 두 접근로 모두 N_SC11 63/147 = 0.4286, S_SC108 84/147 = 0.5714(reason relflow). 유도기의 예외 목록(`DECLARED_NONEXISTENT_PENDING`)은 지웠습니다. 선언된 movement에 물리 커넥터·경로가 닿거나, `corrected` movement에 닿지 않거나 현시 권한이 그 커넥터·현시를 대지 않으면 유도가 실패합니다. 표 `corrected_declarations`·`declared_nonexistent`·`runtime_phases`에 기록합니다.
>         - 면적 경로: 떠나는 `SC7_E_SC16_to_N_SC11`는 기본 계약(`diagnostics/control_area_route_contract_physical_routes.json`)에서 'no_match'였습니다(착지 1220008701이 S_SC108 저장고로 관측돼 'different_model_storage'). β 0이라 드러나지 않았고, 값을 주면 예측이 "unresolved destination"으로 멈춥니다. `scripts/derive_area_routes_v3b.py` → `N31D/urban/control_area_route_contract_v3b_20260926.json`(`fdc21f06`, 사이드카 `.provenance.json` `db5826a1`; 검토 전 `0548ec8e`, 현시 권한 sha만 다름) = 기본 계약 + 그 출발 경로(10332, inside → inside, 수신 SC7_to_SC11은 10334에서 관측) 하나. 후보의 `control_area_objective.route_contract_path`가 이 파일입니다. `SC7_E_to_N_SC11`(가상 경계 leg in_SC7_E)은 파일에서 형제 S_SC108처럼 미해결로 두고, 런타임 gate alias 확장이 둘 다 E_SC16 경로로 풉니다(T2700: 34 → 35).
>         - 가드: 완결 원천은 튜닝의 선언·현시 권한·phase_correction·merge_exits가 표를 유도한 것과 같아야 설치되고, `check_complete_beta_runtime`은 녹색 없는 현시의 흐름을 거부합니다(옛 p3 배치면 여기서 멈춤).
>         - **검토 정정(2026-09-26).** 수정 자체(p4, relFlow 0.429)는 그대로이고, 기록과 설명 셋을 고쳤습니다.
>           - 용량은 β로 나뉘지 않습니다. 10332·10333이 헤드 140101 뒤에서 1210009600의 단일 차로를 함께 쓰지만, `install_movement_capacity_by_lanes`가 movement마다 자기 커넥터 차로수(각 1)를 줍니다. 그래서 N_SC11과 S_SC108이 각각 206.53 veh/h를 받고, 이 차로의 모형 방류 상한은 2 × 206.53입니다. T2700 U1+U3 재생에서 두 movement 모두 용량 206.53, 한 스텝 방류 1.3769대(= 206.53 × 24/3600)였습니다. 헤드 관측 하한(`head_observation`)은 p4 녹색 24 s가 `min_green_sec` 30보다 짧아 이 그룹에 걸리지 않습니다. 걸려도 멤버 용량 합에서 출발해 β로 다시 나눌 뿐입니다. 이것은 공유 정지선 차로 전반의 규칙입니다. 같은 재생에서 흐름 있는 목적지 둘 이상이 한 물리 차로를 나눠 쓰는 정지선 차로가 81개이고, 그중 39개는 그 링크에 헤드 관측 하한이 없습니다(SC16 E·W는 1차로에서 3갈래). 옛 caveat("같은 헤드의 다른 커넥터가 차로군 용량을 β로 나눈다")은 틀렸고, 정정 뒤 방류 합 증가(1.67 → 3.15대/150 s)는 relFlow 효과가 아니라 N_SC11이 자기 커넥터 차로 용량을 따로 받기 때문입니다. 차로군 분할은 용량 모형 변경(U4)이라 사용자 결정으로 남깁니다. FZP 7.96대/150 s보다는 여전히 적습니다.
>           - 경로 위에 SC7 헤드가 하나 더 있습니다. N_SC11 차량은 착지 링크 1220008701(2차로)에서 SG 16 헤드 141802(차로 1)·141801(차로 2, 31.8 m)을 지나 유일한 출구 10334(35.7 m)로 나갑니다(정적 경로 252:3은 1220008701 3.6 m에서 끝남). SG 16은 미드블록 SG(계획 `midblock_native_signal_groups`, 어느 현시에도 없음)라 네이티브로 돕니다. `.sig` prog 1에서 85–111 s가 적색이라 p4 녹색 93–117 s 중 18 s와 겹칩니다. 모형은 이 SG로 어떤 movement도 막지 않습니다. 같은 헤드를 지나는 S_SC108 → N_SC11 직진은 p1 녹색(0–67 s)이 SG 16 녹색 안에 있습니다. 현시 판정(출발 헤드 140101 = p4)은 그대로입니다. 10332 실측이 1.82대/150 s이고 저장 공간이 약 30 m라 지금 영향은 작습니다. "헤드 차로 위에 SC7 다른 헤드 없음"은 출발 차로에 한해서만 참입니다.
>           - `dead_phase_beta_zero`는 측정 β 바로 뒤, 병합·물리 현시 권한 전에 선언 현시로 판정합니다. 그래서 정정 뒤 이 키를 켜면 SC7 두 movement의 relFlow 0.429(선언 p3)를 옮기려다 옮긴-몫 가드에 걸렸습니다(정정 전에는 β 0이라 항등이었습니다). 이제 `install_measured_turn_beta`(`_check_complete_table_declarations`)가 완결 원천에서 이 키를 원인과 함께 거부합니다. `make_config_n31.py --urban-batch1`도 기본 튜닝의 false를 요구합니다. 녹색 없는 현시의 흐름은 `check_complete_beta_runtime`이 런타임 현시로 거부합니다. 키가 false이거나 없으면 동작이 같습니다.
>         - 결과(아래 관문): 옛 후보에서 `SC7_E_SC16_to_N_SC11`는 54전이 중 34번 큐가 그대로 얼어 있었고(방류 0) 이제 p4로 떠납니다. T1은 여전히 ±0.05 밖입니다(0.429 대 FZP 0.21–0.23, 규칙상 허용). FZP를 출처별로 나누면 결정 252 차량의 우회전은 0.418–0.486(3시드)으로 relFlow와 맞고, 나머지 약 절반(링크 201 입력 1096의 단일 경로 1102 + 199로 들어온 차량)은 전부 좌회전입니다. 유도기는 단일 경로 결정 1102를 증거로 쓰지 않습니다(`single_route_decisions_ignored`). 이 모집단 가중을 어떻게 할지는 열린 문제입니다.
>       - **열린 문제(사용자 결정):** `urban.sc2001_corridor`는 link 78 유출(R_D_E / R_D_W / outside_125)을 NC13(다른 망 계보, 실현 완료 코호트) 사전으로 나눕니다(W 0.66/0/0.34, N 0.67/0/0.33, E_SC2002 0.11/0.02/0.88). 78에서 오는 차량은 경로가 78에서 끝나고 78·10703·10774·124에 경로 결정이 없어 relFlow가 없습니다. 1137(31 pos 28.5, 착지 350.7 상류, 3:1:2 = R_D_E 0.5 / outside 0.17 / R_D_W 0.33)은 이 차량에 물리적으로 적용되지 않습니다. v3b 무제어 FZP 실현(3시드): W 0.67–0.72/0/0.28–0.33, N 0.79–0.81/≤0.004/0.19–0.21, E_SC2002 0.25–0.27/0.003–0.012/0.73–0.74. 후보는 NC13 값을 그대로 씁니다. 선택지: 현행 유지, v3b 무제어 재적합(D-B 결정의 재적합과 같은 종류, 실현값), config 기본값. 결정되면 config 키로 두고 키가 없을 때 비트 동일을 지킵니다.
>       - **U2(`urban.queue.attribution: route` + `route_evidence` 핀, v2 규칙):** 차량 경로의 첫 정지선 통과 → 경로가 접근로 정지선에서 끝나면 그 정지선 movement의 β → 경로가 접근로 전에 갈라지면 movement 큐가 아니라 그 링크의 저류(용량 초과분은 큐에 남김) → 경로 없음이면 정지선 링크에서는 차로 → β, 그 밖에서는 접근로 안 β·접근로 사이 detector 가중. β 0 movement로 가는 통과(SC7 정정 뒤 표에는 경로가 지나는 β 0 물리 커넥터가 없음)와, 무신호 movement를 그 커넥터가 떠나지 않는 차로에서 가리키는 통과는 차로 규칙으로 넘깁니다. 헤드 창 길이는 핀된 v3b inpx 폴리라인 길이(증거 `link_lengths_m`)입니다. off-ramp 출신 저장고 규칙은 구현하지 않습니다(그 저장고는 lane plant 물리 포트, `assert_mirrors`); `origins`/`offramp_origin_veh`는 진단 전용입니다.
>       - **U3(`urban.movements.unsignalized_evidence` 핀):** 헤드 없음 + 배타 차로 + FZP 정지 ≤ 5%(≥ 100대) 규칙을 망 전체에 적용해 23개입니다. 이 movement들은 옛 현시의 헤드 차로군 용량 분배(헤드 관측 멤버 포함)에서 빠지고 자기 커넥터 차로 용량을 유지합니다(`cfg.network.unsignalized_evidence_movements`). FZP 검증표는 `scripts/derive_unsignalized_validation.py`(세 FZP 스트리밍, `--check`)가 만듭니다. 옛 55개 커넥터 값은 바이트 단위로 재현되고, 이제 도시 접근 링크에서 나가는 커넥터 727개 전부를 담습니다.
>       - **offramp_direct_share:** 기본 config에 옛 코드 기본값 그대로 명시(런타임 불변). 키가 있으면 SC1001·SC1004를 정확히 둘 다 적어야 합니다(빈 값·일부 값 거부). 키가 없는 옛 튜닝만 `OFFRAMP_DIRECT_SHARE_LEGACY_DEFAULT`를 씁니다. 후보에서는 route prior가 네 그룹을 모두 덮어씁니다(metadata `offramp_route_prior_provenance.previous_shares`).
>       - **오프라인 관문(2026-09-26 재측정, VISSIM 없음, R-obs-b `sdmpc31_v3b_nc_s31b` 61상태 재생, 팔 5개 base/U1/U1+U2/U1+U3/전부).** 기본 튜닝 재생 61/61이 기록된 결정과 IDENTICAL이고 action JSON 차이는 경로·시간·실행 출처뿐입니다. 모든 팔 61(또는 55)상태 종료 0·예측 ok, 장부 최대 차이 9.9e-9. **T1(독립 판정:** 차량 자신의 궤적으로 첫 out 링크·다음 신호 영역을 찾고 β 표 매핑은 쓰지 않음, ±0.05, 200대 이상 119개): 기본 48, U1 포함 팔 모두 105 통과, 정지선 커넥터별 FZP 우세 출구와 표 출구 불일치 0. 실패 14개: 경로 없는 차량 집단 9, SC1001 W 게이트 β 1(U6), SC104 S_SC106 config 기본값 1, SC109 W_SC108 1, SC7 E·E_SC16 2(정정 전에는 예외 0, 정정 뒤에는 relFlow 0.429 대 FZP 0.22로 규칙상 남는 실패). **T3(한 스텝, 54전이, 짝 비교):** U1+U3는 기본 대비 방류 오차(C) 11.42 → 11.03(54/54 개선), 300/450 s 접근로 재고(A2/A3) 9.05 → 8.92, 11.84 → 11.61, 물리 그룹(B2/B3) 10.30 → 10.08, 13.19 → 12.91로 좋아지고, 한 스텝 접근로 재고(A1)만 6.30 → 6.37로 나빠집니다. U2 증분은 A1 +0.12~+0.21, B1 +0.16~+0.19로 두 쌍 모두 신뢰구간이 0을 넘습니다. U1 단독도 A1 +0.08(SC104 E/N, SC107 N_SC1처럼 β가 한 movement에 모이면 차로당 206.5 veh/h 용량에 묶임: U4). 10377 한 스텝 방류는 U1+U3 6.65 대 FZP 6.15(+8%), 전부 3.47(U2가 줄임). 10686은 8.3 대 FZP 33.1(자기 차로 용량 206.5, U4). T2(V5b)는 재핀 전 트리가 없고 증거가 v3b 망에 핀돼 있어 여전히 못 돌립니다. 그래서 기본 튜닝은 바꾸지 않았습니다.
>       - **SC7 정정 뒤 재측정(2026-09-26, 같은 R-obs-b, U1+U3 후보 `efde6b24`, 전부 후보 `436bc6e4`; 검토 정정 뒤 후보는 U1+U3 `f88d05f1`, 전부 `0f78bfa6`이고 핀만 다릅니다 — T2700 U1+U3 재생의 β·용량·큐·재고·방류·녹색·예측 요약이 정정 전 후보와 같고, 기본 튜닝 T2700·T6300은 묶음 1 기본 포착과 같음).** 기본 튜닝 재생 6상태(1/900/2700/4500/6300/9000) IDENTICAL, action JSON 비경로 차이 0, 한 스텝 포착값(β·큐·재고·방류·녹색)이 묶음 1 기본 포착과 같습니다. U1+U3 61상태 종료 0·예측 ok·IDENTICAL, 장부 최대 9.9e-9, depth3 14/14. 정정 전 U1+U3와 공통 55상태에서 바뀐 것은 SC7 두 movement의 현시(p3 → p4)와 SC7 E 접근로 β 넷뿐이고 녹색은 55/55 같습니다. **T1:** 105/119 그대로(SC7 E·E_SC16 최대 편차 0.223 → 0.206, 여전히 실패), 커넥터 불일치 0. **T3(54전이, 정정 후 − 정정 전):** A1 6.370 → 6.361(−0.009, CI [−0.014, −0.004]), A2 8.915 → 8.892, A3 11.606 → 11.587, B1 7.204 → 7.191, B2 10.075 → 10.041, B3 12.911 → 12.884, C 11.026 → 11.011(−0.015, 54전이 모두 개선). 바뀐 키는 A1 123개 중 6개(SC7 E_SC16 4.72 → 3.63, SC11 S_SC7 3.38 → 3.35, 나머지 |Δ| < 0.002), C 100개 중 3개(SC7 E 6.44 → 4.97). 한 스텝 방류(FZP 10332 1.82 / 10333 6.15 대/150 s): N_SC11 0 → 1.49, S_SC108 1.67 → 1.66(두 movement가 각자 커넥터 차로 용량 206.5를 받음 — 차로 용량이 β로 나뉘지 않음, 위 검토 정정; U4). 세 예측 경로(T2700): 캐시·반복 차이 0, no_agg ≤ 1.6e-13, AD 대 스칼라 0 / 3.6e-15, 연속 완화 대 정확 도시 소유자 최대 0.013; tangent 대 FD(h = 0.01) SC1001 3.003/2.975, SC1002 0.913/0.916(정정 전과 같음), SC7 p1 −0.238/−0.209(한쪽 −0.299/−0.119, 꺾임점). Ω 목적 504.863 → 504.825(U1+U3), 501.931 → 501.891(전부).
> - **v2 사전값 (재적합 안 함):** B110 `segment_params.json`(`6b40550a`), boundary fit `parameters.json`(`8e4f6047`)·`freeze.json`·`boundary_config.json`, reference의 수송 키와 VSL 모형은 **v2 NC s31(`f475ce42`)에서 맞춘 값**입니다. 관문 대역 FW_E 20–25 / FW_W 13–17 km/h도 v2 기록입니다. D-B 사전 7개도 그대로 이월했습니다.
>   - 오프라인 확인(2026-09-25, 읽기 전용, `test_tools_plant_gate.RealComponent`와 같은 계산): b110 boundary family를 VSL 110으로 두고 history_forecast 450 s를 굴렸습니다. v2 s31 2700.1에서는 기록값 FW_E 23.92 / FW_W 15.89가 그대로 나옵니다. v3b 무제어 3시드 × 차단 시각 5개(900.1–4500.1 s), 15창의 결과는 다음과 같습니다. FW_E는 5창이 대역 밖이고 최대 29.86입니다. FW_W는 3창이 대역 밖이고 최대 22.50입니다. 2배를 넘는 창(STOP_ASK)은 없습니다. 같은 계산으로 v2 s31 5창은 FW_W만 2창이 대역 밖입니다(17.15, 24.20). 창마다 표본이 하나라 판정은 아닙니다. 5창 평균 속도 RMSE는 v2 s31 FW_W 16.3 / FW_E 22.7, v3b s31/s41/s37 FW_W 14.7/15.2/13.3 / FW_E 25.1/23.0/24.1 km/h로, 학습 런 자신과 비교해 뚜렷한 악화가 없습니다. 그래서 재적합하지 않고 v2 사전값을 유지합니다(2026-09-25 보고, 기존 결정 유지).
> - **산출물 diff 없이 바뀌는 것:** LPR가 1140 relFlow를 실시간으로 읽습니다. 그래서 SC1004 동측 로컬 미래 분율이 1:1:1에서 804:1774:1980으로 바뀝니다.
> - **현재 sha (재핀 뒤):** plant `a087aa67`, config `82688d2f`(2026-09-26: `urban.ramp.offramp_direct_share`를 옛 코드 기본값 그대로 명시만 함, 런타임 비트 동일; 그 전 `16c5f8bc`), reference `2c4857f4`(그대로), 러너 VBS `b74e05b2`(그대로), 검지기 CSV `108debbb`(그대로, 사이드카만 바뀜), sig_manifest `d9483693`, 포트 프로필 `666fd1a8`.
> - **과거 런 재생:** V5b·G1b·V3처럼 `f475ce42`에서 돈 런은 재핀 전 트리(`75f0151` + 램프 키 수정)에서만 재생됩니다. LPR가 망 sha를 대조합니다.

---

## 0. 요약

- **SDMPC-31이란:** v2 망(`f475ce42`) 위에서 150초마다 결정하는 SDMPC 제어기입니다.
  - 본선 예측 모형: 31셀로 나눈 METANET 성분(b110 경계군, 기준 FD).
  - 관측: 결정 시각마다 150초 창을 차량 단위로 정확히 읽습니다(obs150).
  - 도함수: 유한차분이 아닙니다. 같은 파이썬 코드를 Dual 수로 다시 돌리는 순방향 자동미분입니다.
- **여기서 "플랜트"란:** 튜닝 키 `freeway.lane_plant`가 가리키는 manifest 파일 하나(`coupled-lane-plant/v2`)입니다. 이 파일이 망, 31셀 기하, 보정 계수, 성분 설정(reference config), 포트 프로필, 검지기 표를 모두 sha로 핀합니다. 물리는 두 곳에 있습니다.
  - 성분 설정: `CanonicalFreewayModel.__init__`과 `_config` (CH:272-623)
  - 1초 전진: `AFA._freeway_substep_events`. 도시·램프·오프램프 런타임과 매초 결합됩니다(`lane_coupling.run_interval`, AFA:495-497).
- **스위치는 하나입니다:** 튜닝의 `freeway.lane_plant` → manifest의 `schema`(OC:114-117, `plant_mode` OC:155-160). 다른 플랜트를 넣는다는 것은 이 manifest의 핀들을 새 산출물로 바꿔 다시 생성하는 일입니다.
- **네이티브로 확인한 현재 상태 (09-24)**
  - **G1b** (1350 s, 정답 창 750:900 / 1050:1200)
    - D6: 검지기, 경계, 헤드, 원점, 10643 대장, 오프 분기, 램프 분율이 두 창 모두 정확했습니다.
    - 판정 종료 코드는 1(FAIL)입니다. 다만 실패 항목은 `gt_anomalies` 하나이고, SC1002 헤드의 출구가 애매해서 정답으로 판정할 수 없는 경우입니다. 창별 `gt_anomalies` 항목은 6건과 12건이고, 차량으로는 2대와 4대입니다(차량 한 대에 pid 3개 `dcp`/`xl`/`x:head`가 붙습니다).
    - D10 = 1 s (154/154 일치).
  - **V3 재생:** 900초와 1050초 결정 모두 IDENTICAL.
  - **V3b 플랜트 관문:** PASS (속도 RMSE FW_E 21.4, FW_W 12.3 km/h).
  - **V5b** (9000 s, `sdmpc31_v2_s31b`, FRZ `sdmpc31_7216e253_202609241509`): 17:59 기준 3300초 결정까지 모두 exit 0이고, runlog에 오류 줄이 없습니다(`.err` 0바이트). SDMPC 결정(900 s부터) 하나의 벽시계 실측은 270–509 s입니다.
- **알려진 한계:** 플랜트의 VSL 도함수가 110에서 0입니다. 그래서 SDMPC는 VSL을 움직이지 않습니다(§7.1).
- **사용자 후보 A0.5_E4는 데이터만 바꿔서는 들어가지 않습니다.**
  - `vsl_fd_response`와 `component_vsl_transport`는 7216e25에서 **조용히 무시**됩니다. 읽는 코드가 없습니다.
  - `state_response`는 셀 21–25에서 거부됩니다.
  - 그래서 d80faf9의 코드 5개 파일을 가져오고, 추가 작업 여섯 가지(§3(d)-3)를 한 뒤에야 의미가 있습니다.
  - 망도 다릅니다(§7.2). **권장:** 먼저 사용자 모형을 v2 망에 얹고(경로 A) 검증 사다리를 오릅니다.

---

## 1. 받는 법

### 1.1 코드

```powershell
git clone https://github.com/Ming2you/VISSIM.git <repo>        # 이미 있으면 생략
cd <repo>
git config core.autocrlf true                                   # 이 PC와 같게 (§5.4)
git fetch origin claude/sdmpc-n31-20260924 codex/control-full-review-20260909
git worktree add -b <내-브랜치> <W> origin/claude/sdmpc-n31-20260924
```

- **W는 짧은 경로에 둡니다.** 예: `D:\sdmpc31\w`. 동결 사본(FRZ)도 짧은 루트에 만듭니다(long path 회피).
- **사용자 브랜치를 통째로 merge하지 않습니다.** 필요한 파일만 가져옵니다(§3(d)-2).
  - `.gitattributes`가 양쪽에서 다르게 끝나서 충돌합니다.
  - 매핑 파일 `control_mapping_ver2n21.json`도 blob이 다릅니다: 7216e25는 CRLF blob에 `-text`(.gitattributes:5613), d80faf9는 LF blob에 `text eol=crlf`.
  - 두 쪽 모두 체크아웃 바이트는 `d0a7bb9f…`로 같고, CH:288이 이 sha를 대조합니다. 이 파일은 7216e25 쪽을 유지합니다.
- **알려진 차이:** 이 PC는 동결 사본에 W의 미추적 파일까지 담아서 돌렸습니다(`status_entries=1179`, FRZ 11,805개 대 추적 10,209개). 깨끗한 체크아웃만으로 네이티브 결정이 도는지는 **확인된 적이 없습니다.** §4 L6의 t=1 결정이 첫 판정입니다. 09-23에도 같은 종류의 누락 16건을 찾아 커밋했습니다(2bf00cf, §6).

### 1.2 Python과 의존성

| 항목 | 이 PC 값 | 비고 |
|---|---|---|
| Python | 3.12.2 (`C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe`) | |
| numpy | 2.1.3 (기본 설치) | 재생 결과가 끝자리까지 같으려면 같은 버전을 권합니다 |
| `DEP\sdmpc` | scipy 1.18.1, pytest 9.1.1(+colorama, iniconfig, packaging, pluggy, pygments) | PYTHONPATH로 붙입니다 |
| `DEP\sdmpc-numba` | numba 0.67.0, llvmlite 0.49.0 | PYTHONPATH로 붙입니다 |
| VISSIM | 2020 COM | 사용자 인계 README는 원본을 2020.00-14 [95957]로 적었습니다. 버전이 다르면 같은 seed여도 궤적이 같다는 보장이 없습니다 |

- 발사기는 `PYTHONPATH=DEP\sdmpc;DEP\sdmpc-numba`를 세웁니다(`tools/sdmpc31/run_sdmpc_n31.ps1:206`).
- 이 PC가 DEP를 어떤 명령으로 만들었는지는 기록이 없습니다. 같은 구성을 만드는 권장안은 아래와 같습니다(불확실). numpy가 target 폴더에 따로 들어가지 않게 `--no-deps`를 씁니다.

```powershell
& $PY -m pip install numpy==2.1.3
& $PY -m pip install --no-deps --target $DEP\sdmpc scipy==1.18.1
& $PY -m pip install --target $DEP\sdmpc pytest==9.1.1
& $PY -m pip install --no-deps --target $DEP\sdmpc-numba numba==0.67.0 llvmlite==0.49.0
```

### 1.3 이 PC 경로가 박힌 곳 (다른 PC에서는 인자로 넘기거나 고칩니다)

| 위치 | 값 | 조치 |
|---|---|---|
| `tools/sdmpc31/run_sdmpc_n31.ps1:47-52` | `-FrozenRoot`, `-FreezeTool`, `-RunsRoot`, `-PrepareNetworkTool`, `-Python`, `-DepRoot` | 모두 인자로 넘깁니다. 도구는 저장소 사본 `W\tools\sdmpc31\{freeze_worktree.ps1, prepare_sdmpc31_network.py}`를 가리킵니다 |
| `tools/sdmpc31/freeze_worktree.ps1:15-18` | `-Source`, `-FrozenRoot`, `-Python` | 발사기가 `-Source`, `-FrozenRoot`, `-Python`을 넘깁니다(:161) |
| `N31D/tools/n31_common.py:26-27` | `RUNS_ROOT`, `PYTHON` | `launch_plan.py`는 발사기가 넘기는 `--runs-root`를 씁니다 |
| `N31D/tools/replay_decision_n31.ps1:27` | `-DepRoot` | 인자로 넘깁니다. Python은 런 provenance의 `RW_PYTHON`을 씁니다(:126) |
| `N31D/copy_b110.py:28` | `SOURCE_ROOT = D:\VISSIM-merge\sim3` | §3(a) 참고. `--check`도 이 경로를 읽습니다 |
| `N31D/repin_scenario_v2.py:76` | `NET_DIR` (stage-1 런 폴더) | `build --network-from copy`, `verify --no-net`로 피합니다 |
| `N31D/port_profile_v2/extract_port_profile.py:56` | `RUN` (stage-1 무제어 런) | 망을 바꿀 때만 필요합니다. 새 무제어 런 경로로 바꿉니다. 같은 파일의 `GEOMETRY`(:57), `NETWORK_SHA256`(:60), `FZP_SHA256`(:61)도 함께 고칩니다(§3(c)) |
| `N31D/tests/n31_fixtures.py:34,43`, `tests/test_prepare_sdmpc31_network.py:19`, `tools/tests/test_tools_integration.py:30` | `D:\VISSIM_runs\…`, `D:\VISSIM-merge\…` | 없으면 해당 시험이 skip됩니다. **skip은 통과가 아닙니다** |

---

## 2. 플랜트 인터페이스

### 2.1 스위치와 로드 순서

`runtime_setup.configure_runtime` (evaluation/controllers/runtime_setup.py):

1. 튜닝 `freeway.lane_plant` → `lane_plant_runtime.load_sources(manifest)` (:73-81). schema가 v2이면 `_load_sources_v2`(LPR:70-127)로 갑니다.
2. v2이면 `validate_tuning_v2(tuning, document)` (:83-87)
3. `observe_state`, `bind_current_routes` (:88-89): 150초 번들 → derived → 병합한 상태
4. `lane_plant_runtime.initialize` (:232): 31셀 상태, 본선·램프·오프램프·도시 런타임, A1 원점 경계
5. `bind_area` (:242)

`freeway.lane_initial_spillback_projection: true`(config_n31_v2.json:8082)는 lane plant가 있을 때만 허용됩니다(runtime_setup.py:74-76). 71/10641/126 초기 투영을 켭니다(§6).

### 2.2 v2 manifest 필드 (`validate_plant_manifest_v2`, OC:163-189)

키 집합이 정확히 맞아야 합니다(OC:119-124). 핀은 모두 `{path, sha256}`이고, path는 저장소 상대경로에 `/`만 씁니다. 절대경로, `..`, `:`는 거부합니다(OC:146-152). 아래 값은 `N31D/plant_n31_v2.json`(`2dc45b2e`, VSL 이식 전) 기준입니다. 현재 값은 맨 위 추가 노트를 보십시오.

| 필드 | 현재 값 | 만드는 곳 | 플랜트에서 하는 일 |
|---|---|---|---|
| `sources.network` | `N31D/network/baseline_s31_v2nc.inpx` (`f475ce42`) | `repin_scenario_v2.py build` | 기하를 다시 추출하고, 도시 경로와 출구를 읽습니다(LPR:91,110). 결정마다 상태의 망 sha와 대조합니다(LPR:141-142) |
| `sources.geometry` | `B110/observations/s31_v2nc_observations/geometry.json` (`89011be0`) | 보정 추출기 → `copy_b110.py` | 31셀, 경계, 포트, 주소, 원점 수요표. 재추출 결과와 같아야 합니다(LPR:86-96) |
| `sources.refined_partition` | `…/segment_resolution_20260921/geometry_200_branch_guard.json` (`9769b3a4`) | 추적 파일, 고정 | 21셀 → 31셀 분할(LPR:92) |
| `sources.reference_config` | `N31D/reference_config_n31_v2.json` (`b049dcc0`) | `make_reference_config.py` | `CanonicalFreewayModel(geometry, reference_config)`의 설정입니다(LPR:97). 성분 FD, 포트, 램프가 여기서 옵니다 |
| `sources.parameters` | `B110/train_s31_v2nc/boundary_literature_v1/boundary_fit/parameters.json` (`8e4f6047`) | 보정 → `copy_b110.py` | `['parameters']['by_direction'][road]` → `component._config` (LPR:112, LFR:28) |
| `sources.port_profile` | `N31D/port_profile_v2/port_profile.json` (`e62df12c`) | `port_profile_v2/extract_port_profile.py` | 커넥터 16개의 주행속도(LPR:106-109), 차로손실 on/off(LPR:447) |
| `sources.reference_protocol` | `…/transport_step1_exchange_off_v2/protocol.json` | 고정 | 파속도, 도시 자유속도, 측방 접근 규칙(LPR:314-327) |
| `sources.runner_config` | `N31D/scenario/lane_native_b110.vbs` (`b74e05b2`) | `repin_scenario_v2.py` | 러너 VBS 설정. 튜닝 `execution.signal_vbs_config`와 같아야 합니다(OC:205-206) |
| `sources.sig_manifest` | `N31D/network/sig_manifest.json` | `repin_scenario_v2.py` | `.sig` 42개 표 |
| `membership` | `N31D/scenario/control_area_membership_213a5d.json` | repin 팩 | 권역 멤버십(LPR:274) |
| `off_groups` | `…/ramp8_physical_v1/offramp_route_inventory_v1.json` | 고정 | 오프램프 신호·직결 그룹(LPR:353) |
| `observation.detectors` | `N31D/obs150/obs150_detectors_v2.csv` (`108debbb`, 294행) | `scripts/build_obs150_detectors.py` | obs150 관측 경계 전부 |
| `observation.expected_simres`, `vehrec_interval_sec` | 10, 5 | 상수 | |
| `source_boundary` | `{calibrated_history_forecast, 150, 10}` | 상수(OC:125) | A1 원점 경계 |
| `lane_groups` | `false` | 상수 | 차로군을 켜는 reference config는 거부합니다(LPR:98-99) |
| `fw_e_terminal` | `component` | 선택 | FW_E 말단 = 성분의 open exit (LPR:440-443) |
| `vsl_command_space` | `parent_21` | 상수 | 정제셀이 부모 구역 머리의 명령을 읽습니다(LPR:590-597) |
| `future_observations` | `false` | 상수 | |
| `qualification` | 상태 문장 | `make_plant_n31.QUALIFICATION` (:60-65) | 기록 전용. 지금 문구는 "G1 D6 pending"이라 낡았습니다(§7.4) |

### 2.3 플랜트 물리는 어디서 도는가

- **SDMPC 런타임은 `CanonicalFreewayModel.rollout`을 부르지 않습니다.** 쓰는 것은 셋입니다.
  - 생성자: FD·세그먼트 훅(CH:301), 정제 분할(CH:302-317), 포트와 램프(CH:340-497)
  - `_config(road, parameters)`: 방향 배수, τ, ν, κ, δ를 적용합니다(CH:551-623)
  - `DelayedPort`: 오프램프 포트(LPR:363-365)
- **1초 전진:** `lane_coupling.run_interval` → `LaneFreewayRuntime.advance` → 도로마다 `AFA._freeway_substep_events(..., cfg=도로별 성분 cfg)` (LFR:103-127)
  - 도로별 cfg는 `_config`가 `self.base`를 깊은 복사한 것입니다(CH:552). 그래서 **base cfg에 세운 속성은 SDMPC까지 갑니다.**
  - 보정 rollout도 같은 커널을 부릅니다(CH:1005).
- **그래서 사용자 코드는 두 부류로 나뉩니다.**
  - SDMPC에 닿는 것: 생성자와 `_config`가 세우는 것, 커널 안의 것
  - 닿지 않는 것: `rollout` 안에만 있는 것. 사용자 브랜치의 `_head_service`(정의 (d80faf9) CH:594-604)와 `ramp_arrival_lane_profile`이 여기에 해당합니다. 둘 다 rollout의 `ramp_dynamics` 경로 안에서만 쓰입니다. `ramp_buffers`는 `ramp_dynamics`가 준 램프에만 만들어지고((d80faf9) CH:732, :736-741, :798-801), 둘을 쓰는 곳은 그 루프 안의 CH:974, :980뿐입니다.
  - SDMPC에는 같은 역할의 경로가 따로 있습니다. 헤드 서비스는 LPR:480-484(`physical_ramp_head_service_veh_per_cycle` → `service_by_green_veh_h`), 램프 차로 도착 분율은 LPR:457-462(obs150 실측)입니다.
- **오프라인 도구 `plant_gate.py`는 `rollout`을 씁니다**(plant_gate.py:387). 그래서 V3b 관문은 "보정 rollout 경로"를 시험하지, SDMPC의 결합 경로를 시험하지 않습니다. 관문 창 파일에는 `ramp_dynamics`가 없으므로(:336-350) 이 rollout은 램프 버퍼 경로도 타지 않습니다(§4 L5).
- **도함수 워커**
  - 성분을 다시 만들지 않습니다. 부모가 만든 상태를 피클로 받습니다.
  - 저장소 모듈의 `float`, `min`, `max`, `math`를 Dual용으로 바꿔 다시 로드합니다(sdmpc_tangent_runtime.py:36-73, :133-148).
  - VSL 축은 연속 Dual로 심습니다(sdmpc_tangent_worker.py:380-384).
  - 따라서 새 식은 도함수에도 그대로 들어갑니다. 대신 **Dual이 지나갈 수 있는 코드**여야 하고, 새 상태는 모듈 전역이 아니라 cfg나 state에 실려야 합니다.

### 2.4 플랜트와 러너가 반드시 맞아야 하는 것

| 항목 | 강제하는 곳 | 조건 |
|---|---|---|
| 망 바이트 | LPR:87-89, :141-142; make_plant_n31.py:97-101; `launch_plan.py`(:133) | manifest 망 = 보정 기하의 `network.sha256` = 검지기 표의 망 = 런 사본 = 결정마다 상태의 망 sha |
| 31셀 분할 | LPR:88, :94-96, :102-105 | 보정 기하가 이 분할로 정제된 것이고, 핀된 망에서 재추출한 결과와 셀·경계·포트·지문이 같아야 합니다 |
| 원점 수요 | LPR:611-620; obs150_observation.py:641-647 | 망 시간표(input 1098/1099) = 보정 기하 `desired_source_demand` = obs150 스케줄 |
| 검지기 CSV | OC:240-249; LPR:124-125 | manifest 핀 = 러너 `RW_OBS150_DETECTORS_SHA256`. 핀된 소스로 다시 유도한 표와도 바이트가 같아야 합니다 |
| VSL 명령 공간 | OC:186; LPR:590-597; sdmpc.py:333-341 | `parent_21`. 튜닝 `freeway.vsl_zone_heads` {FW_E, FW_W: [0,5,10,15]}, `vsl_zone_free` [0,1,2](config_n31_v2.json:7987-8005). 구역 3(부모 머리 15, 정제셀 25–30)은 SDMPC 축이 아니라 vsl_max로 고정됩니다 |
| VSL 속도 | `lane_native_b110.vbs:34`; make_config_n31.py:54-55; make_reference_config.py:58; repin_scenario_v2.py:129 | 60/80/110. 러너 허용 집합, 튜닝 `vsl_set`, reference `vsl_set`이 같아야 하고 망에 해당 분포가 있어야 합니다. `v_free`는 110입니다 |
| 미터와 포트 | CH:349-361; LFR:98-99; LPR:106-109 | 온램프 8, 오프램프 8, 커넥터 16개의 주행속도. 2차로 램프 용량 3600(make_reference_config.py:52-54). 미터 주기 10 s |
| 1초 적분 | CH:293-300; LPR:263-264; LFR:18-19 | reference `physical_integration_step_sec: 1`, 튜닝 T_f = T_u = 1 |
| 성분 경계 | LPR:100-101; make_reference_config.py:55-56 | `component_boundary` = {admitted_interface, open_exit} |
| 차량 간격 | LPR:271-273 | 플랜트와 도시 저장 용량이 같은 간격을 씁니다 |
| 원점 대기열 | LPR:567-569 | backlog는 A1이 나르므로, 본선 origin queue는 0에서 시작합니다 |
| 매핑 | CH:287-289 | reference의 `mapping_json` 바이트 sha = 보정 기하 `mapping.sha256` (`d0a7bb9f`) |
| 튜닝 규칙 | OC:192-206 | `head_observation.enabled` true이고 `sample_interval_sec` 없음, `native_signal_record` false, `signal_vbs_config` = runner_config 핀 |

---

## 3. 이식 절차

### 3.0 경로 선택

| | 경로 A (권장): 사용자 모형을 v2 망에 얹기 | 경로 B: SDMPC-31을 사용자 망으로 재핀 |
|---|---|---|
| 망 | `f475ce42` 그대로 | `HO/network/native_seed29.inpx` (`64cf5f55`) |
| 기하 | 우리 b110 기하(`89011be0`) | 핀할 망에서 다시 추출해야 합니다(`HO/geometry.json`은 또 다른 망 `401b6558`에서 뽑은 것) |
| 다시 만들 것 | reference, parameters, freeze, segment_params, plant manifest | 위 전부 + 망 사본, 시나리오 팩 20개, 러너 config, 검지기 CSV, 포트 프로필 |
| 네이티브로 검증된 것 | obs150 관측과 러너(G1b) 그대로 | 모두 새로(G1부터) |
| 대가 | 계수가 다른 수요·분포에서 맞춘 값입니다 | 재핀 도구가 세 곳에서 거부합니다(§3(c)) |

obs150 관측과 러너가 네이티브로 검증된 망은 `f475ce42`뿐입니다. 그래서 A로 코드, 도함수, 관문을 먼저 통과시키고, 사용자 망이 꼭 필요할 때 B로 가기를 권합니다. 최종 선택은 사용자 몫입니다.

### (a) 보정 산출물을 생성기가 기대하는 자리에 두기

1. **새 작업공간 폴더를 만듭니다.** 예: `diagnostics/demand_sweep/user_native_20260914/metanet_calibration_v1/<이름>_<날짜>/`
   - `res10_b110_20260923/`에 덮어쓰지 않습니다(출처가 섞입니다).
   - 하위 `.gitattributes`(`* -text`)를 같이 둡니다. B110에 있는 것과 같은 방식입니다.
2. **아래 다섯 파일을 B110과 같은 상대 배치로 둡니다.**

| 파일 | 요구 형식 | 검사하는 곳 |
|---|---|---|
| `…/boundary_config.json` | canonical_harness가 읽는 튜닝입니다. `freeway.segment_params`는 아래 segment_params의 **저장소 안 경로**. `component_boundary` {admitted_interface, open_exit}, `physical_integration_step_sec` 1, 차로군 키 12개 없음, `vsl_set`과 `v_free`는 SDMPC와 같게 | copy_b110.py:55-57; make_reference_config.py:44-59; LPR:98-101 |
| `…/boundary_fit/parameters.json` | `{"parameters": {"by_direction": {"FW_E": {…}, "FW_W": {…}}}, …}`. 키와 값은 `PARAMETER_BOUNDS`/`OPTIONAL_PARAMETER_BOUNDS` 안(CH:556-563) | LPR:112; LFR:28 |
| `…/boundary_fit/freeze.json` | `parameters_sha256` = parameters.json sha. `code_pins`에 segment_params 경로와 sha | copy_b110.py:48-52; make_plant_n31.py:104-105 |
| `…/segment_params.json` | 21셀 격자(`grid.segments_per_link: 21`). 분할 뒤 정제셀은 부모 행을 복사해 씁니다(CH:312) | CH:309-312 |
| `…/geometry.json` | 31셀. `network.sha256` = 핀할 망, `refined_partition.sha256` = `9769b3a4`, `geometry_profile.sha256` = `7829dc11`, `mapping.sha256` = `d0a7bb9f`, `desired_source_demand` = 망 시간표. **경로 A에서는 새로 두지 않습니다**(아래 주의) | LPR:86-96; CH:279-289 |

- **경로 A의 기하 주의:** 경로 A는 우리 기하(`89011be0`)를 그대로 씁니다. 그러니 `copy_b110.py`의 `FILES` 중 geometry 줄(:35)과 `make_plant_n31.py`의 `SOURCES['geometry']`(:45)는 B110 경로 그대로 둡니다. 같은 바이트라도 새 작업공간으로 복사해 경로를 바꾸면, 검지기 사이드카의 `sources.geometry.path`가 달라져 `build_obs150_detectors.py --check`가 `OBS150_DETECTORS_DIFFER`로 끝납니다(§3(b)).

3. **`N31D/copy_b110.py`를 새 폴더로 돌립니다.**
   - `WORKSPACE`와 `FILES`(:29-36)를 고칩니다.
   - 영수증 `b110_copy_receipt.json`에 원본의 **절대경로**가 들어갑니다(:85-86). 그래서 다른 PC에서 기존 영수증에 `--check`를 하면 `D:\VISSIM-merge\sim3`를 읽으려다 실패합니다. 새 작업공간에는 영수증 파일 이름을 따로 두고(:38 `RECEIPT`), `--source-root <보정 사본 루트>`로 쓴 뒤 같은 인자로 `--check`합니다.

### (b) reference / plant / config 재생성 (`--check`까지)

**A0.5_E4이면 먼저 §3(d)-2(코드 가져오기)와 §3(d)-1의 1·2번(생성기 수정)을 적용한 뒤 (b)를 돌립니다.** 그러지 않으면 첫 명령부터 실패합니다.
- `make_reference_config.py:44-46`: 후보에 수송 키 3개가 이미 있어 `only`가 달라지고, `ValueError('Transport-only freeway keys changed')`가 납니다.
- `make_reference_config.py:57-59`: 후보의 `vsl_set` [60,80,90,100,110]과 `v_free` 120을 거부합니다.
- 코드를 가져오지 않으면 성분을 만드는 단계(L1 시험, L5 관문)에서 `state_response` 셀 21–25가 거부됩니다(freeway_fd.py:97-99).

W 루트에서 순서대로 돌립니다. 모든 생성기는 `--check`에서 메모리로 다시 만들어 바이트를 비교하고, 아무것도 쓰지 않습니다.

```powershell
$env:PYTHONPATH = "$DEP\sdmpc;$DEP\sdmpc-numba"; $env:PYTHONUTF8 = '1'; $env:PYTHONDONTWRITEBYTECODE = '1'
& $PY -B diagnostics/sdmpc_n31_20260924/make_reference_config.py            # BOUNDARY(:24-25)를 새 boundary_config로
& $PY -B diagnostics/sdmpc_n31_20260924/make_reference_config.py --check    # REFERENCE_CONFIG_OK
& $PY -B scripts/build_obs150_detectors.py --geometry <새 geometry 경로>    # 기하의 경로 또는 sha가 바뀔 때만
& $PY -B scripts/build_obs150_detectors.py --geometry <같은 경로> --check
& $PY -B diagnostics/sdmpc_n31_20260924/make_plant_n31.py                   # SOURCES geometry/parameters, FREEZE(:43-54), QUALIFICATION(:60-65)
& $PY -B diagnostics/sdmpc_n31_20260924/make_plant_n31.py --check           # PLANT_N31_OK sha256=…
& $PY -B diagnostics/sdmpc_n31_20260924/make_config_n31.py                  # SEGMENT_PARAMS(:47-48); 필요하면 VSL_SET, V_FREE(:54-55)
& $PY -B diagnostics/sdmpc_n31_20260924/make_config_n31.py --check          # CONFIG_N31_OK sha256=… (한 줄)
& $PY -B diagnostics/sdmpc_n31_20260924/repin_scenario_v2.py verify --no-net  # REPIN_VERIFY_OK files=70 pins=122 (망을 안 바꿨을 때)
```

- **검지기 표:** 기하의 **경로 또는** sha가 바뀌면 검지기 manifest(사이드카)가 바뀝니다. 사이드카는 `sources.geometry`를 `{path, sha256}`로 적고, `--check`는 CSV와 사이드카 바이트를 둘 다 비교합니다(build_obs150_detectors.py:158, :184-186). 셀과 포트가 같으면 CSV 바이트는 그대로(`108debbb`)여야 합니다.
  - 실행 중의 `read_sidecar`(obs150_observation.py:503-510)는 CSV sha만 보고 기하 경로는 보지 않습니다. 그래서 사이드카 불일치는 L0 `--check`에서만 걸립니다.
  - 경로 A에서는 `sources.geometry`를 B110 경로 그대로 둡니다(§3(a) 주의).
- **preflight:** `make_config_n31.py`는 `preflight_tuning_paths`를 `--quiet`로 돌립니다. 성공하면 `CONFIG_N31_OK sha256=…` 한 줄만 찍고, 실패하면 `preflight_tuning_paths failed`로 멈춥니다(make_config_n31.py:202-206).
- **config:** plant를 경로로만 가리키므로, segment_params 경로가 그대로면 config 바이트도 그대로일 수 있습니다(통합 기록 §2에 선례: `eddfd19f` 유지).
- **이 PC의 현재 기준값 (v3b 재핀 뒤):** plant `a087aa67`, config `82688d2f`(옛 코드 기본값 `offramp_direct_share` 명시만, 런타임 비트 동일; 그 전 `16c5f8bc`), reference `2c4857f4`, 검지기 `108debbb`(294행), routing beta `e81d545f`. (v3b 재핀 전 v2 망에서는 plant `17871460`, config `3a5cacef`. VSL 이식 전에는 plant `2dc45b2e`, config `eddfd19f`, preflight PASS(43). 램프 예측 키 수정 전(2026-09-25)에는 config `1e58e6bf`.)
  - 램프 예측 표는 망에 묶여 있습니다. 망을 바꾸면(경로 B) 무제어 런을 새로 돌린 뒤 `derive_ramp_forecast_n31.py`의 입력 핀을 바꾸고 다시 뽑아 `RAMP_FORECAST`에 옮기고, `make_config_n31.py --check`와 `derive_ramp_forecast_n31.py --check`를 둘 다 통과시키십시오.
  - `derive_ramp_forecast_n31.py`의 입력은 v3b 무제어 세 시드의 `metanet_calibration_v1/v3b_nc_20260925/observations/s*_v3bnc_observations/boundaries_30s.csv`입니다. 이 셋과 manifest, 추출 영수증, 플랜트가 핀하는 s31 `geometry.json`만 git에 추적합니다. `cells_30s.csv`, `flows_30s.csv`, 전이·제외 증거(시드당 약 4.5 MB)는 추적하지 않으므로 필요하면 영수증의 명령으로 FZP에서 다시 뽑으십시오. v2 입력(stage-2 `control_response_v2/`)은 추적되지 않은 기록입니다.

### (c) 재핀

- **플랜트 재핀 (항상):** (b)에서 `make_plant_n31.py`를 다시 돌리면 끝입니다. 발사 계획 `launch_plan.py`가 FRZ 안에서 모든 manifest 핀의 바이트를 다시 대조합니다(:61-66, :133-144). 그래서 손으로 고친 파일은 발사 단계에서 걸립니다.
- **시나리오 재핀 (망을 바꿀 때만, 경로 B):**
  - 도구: `repin_scenario_v2.py build [--network-from copy]` → `verify [--no-net]`. 출력은 N31D의 `network/`(inpx, `.sig` 42개, `sig_manifest.json`)와 `scenario/`(팩 20개, `lane_native_b110.vbs`, `config_n31_v2.base.json`, 영수증)입니다(docstring :10-21).
  - **사용자 망은 규칙 세 곳에서 거부됩니다.** `characterize_changes`(:285-327)는 fcb349d3 대비 차이를 `CHANGE_RULES`(:270-282)로만 허용합니다.
    1. `desSpeedDecisions` 63–66의 `pos` 변경: 규칙은 분포만 허용합니다. **이 안내서를 쓰며 첫 거부를 직접 확인했습니다.**
    2. `vehicleCompositions` 14 추가: 검토되지 않은 섹션입니다.
    3. 1098/1099의 `vehComp` 변경: 규칙은 `volume`만 허용합니다.
    - 이 안내서를 쓰며 읽기 전용으로 확인했습니다: 원본 `CHANGE_RULES`로는 1번에서 거부되고, 세 규칙을 차례로 넓히면 2번, 3번에서 거부된 뒤 셋을 모두 넓히면 `characterize_changes`가 통과합니다(메모리 안에서 규칙만 바꿔 호출, 파일은 쓰지 않음). `stale_evidence_audit` 등 다른 검사는 돌려 보지 않았습니다.
    - 각 변경이 팩 선언(경로, 헤드, 커넥터 기반)에 무해한지 검토한 뒤에 규칙을 넓힙니다.
  - **망 sha가 상수로 박힌 곳 (v3b 재핀 뒤, `git grep be0075bf4d5e9e239ffc`):** `repin_scenario_v2.py:89-91`(`NET_DIR`, `NET_INPX`, `V2_SHA256`; 망 경로 변경은 `V3B_ROUTE_EDITS`처럼 열거표로 허용), `make_plant_n31.py:63`, `make_config_n31.py:57`, `scripts/build_obs150_detectors.py:52`(`NETWORK_SHA256`), `N31D/port_profile_v2/extract_port_profile.py:64`(:95, :98에서 검사). 망 파일 이름은 `make_plant_n31.py:48`, `make_config_n31.py:56`, `make_reference_config.py:53`, `repin_scenario_v2.py:90`, 시험 `tests/n31_fixtures.py:35`, `tests/test_prepare_sdmpc31_network.py`, `tools/tests/launch_world.py`, `tools/tests/test_tools_launch.py`에 있습니다. v3b 재핀에서는 여기에 더해 기하(`make_plant_n31.py:49`, `make_reference_config.py:54`), 램프 예측 입력(`derive_ramp_forecast_n31.py:37-43`), routing beta(`make_config_n31.py:62-63`, 어댑터 `BETA_EVIDENCE_JSON`)를 바꿨습니다(위 머리 노트).
  - **다시 만들 것:**
    - 포트 프로필: 새 망의 무제어 FZP ≤ 900 s로 `extract_port_profile.py`를 돌립니다. RUN(:56)과 함께 GEOMETRY(:57), NETWORK_SHA256(:60), FZP_SHA256(:61, :118에서 검사)을 고칩니다. `:56`만 고치면 `scan()`이 망 sha 검사(:91)에서 멈춥니다.
    - 보정 기하: 핀할 망 파일에서 추출
    - 검지기 CSV: 생성기가 키 충돌과 원점 스테이션 1:1을 검사합니다
    - 사전 보정 팩 7개는 `prior_mismatch` 영수증과 함께 이월합니다(§7.3)
  - DSD 63–66은 러너 키 `RW_FW_E_S13`에 묶여 있습니다(lane_native_b110.vbs:32). DSD 번호로 묶이므로 위치가 바뀌어도 키는 그대로일 것으로 봅니다(확인 안 됨).

### (d) 사용자 후보 A0.5_E4 대응

#### (d)-1 파일 대응 (HO = `diagnostics/vsl_handoff_20260924/`, d80faf9)

| 사용자 파일 | SDMPC 슬롯 | 그대로? | 조치 |
|---|---|---|---|
| `HO/candidate.json` | 보정 `boundary_config.json` (make_reference_config `BOUNDARY`) | 아니오 | 아래 "candidate.json 처리"의 다섯 항목 |
| `HO/parameters.json` | `sources.parameters` | 아니오 | 최상위가 `by_direction`입니다. `{"parameters": <이 내용>}`으로 감싸고 freeze.json을 새로 만듭니다(LPR:112, make_plant_n31.py:104). 값: FW_E v_free×1.0, ρ_c×1.4, τ 12 s, ν 36.75, κ 5, δ 1.0 / FW_W v_free×1.09, ρ_c×0.68, τ 12, ν 43.05, κ 5, δ 0 |
| `HO/segment_params.json` | `freeway.segment_params` (reference와 튜닝 둘 다) | 형식은 맞음(21셀) | `source_calibration.network_sha256`가 `ebd90383`(또 다른 망)입니다. v2 망은 DSD110 분포가 달라서 셀 자유속도를 다시 재야 할 수 있습니다 |
| `HO/geometry.json` | `sources.geometry` | 경로 A: 쓰지 않음 | 셀, 경계, 포트, 주소는 우리 것과 같습니다. 망 sha(`401b6558`)와 FW_W 원점 수요가 다릅니다. 경로 A는 우리 기하(`89011be0`)를 씁니다 |
| `HO/network/native_seed29.inpx` + `.sig` 42개 | `sources.network`, `sig_manifest` | 경로 B에서만 | `.sig` 42개는 우리 사본과 바이트가 같습니다(메모리 확인) |
| `HO/case_29.json.gz` | 없음 (회귀 fixture) | — | §4 L3에서 씁니다 |

**candidate.json 처리.** 후보의 freeway 키는 b110 boundary config에 6개를 더한 것입니다: `vsl_fd_response`, `component_vsl_transport`, `state_response`, `physical_ramp_capacity_vph`, `physical_ramp_receiving_nodes`, `physical_offramp_interval_service`. 다른 공통 키는 `segment_params` 경로만 다릅니다.

1. **수송 키 충돌:** 뒤의 셋은 make_reference_config가 수송 설정에서 덧붙이는 키입니다.
   - 그래서 `only != TRANSPORT_KEYS | LANE_GROUP_KEYS` 검사(:44-46)에서 거부됩니다.
   - 검사를 풀어도 생성기가 그 키들을 수송 쪽 값으로 덮어씁니다(:49-51).
   - 수용 노드 사양 중 어느 쪽을 쓸지 먼저 정합니다.
     - 사용자: 4개(RM_C10639/10681/10490/10484), 3.0/1.5 s
     - 현재 SDMPC: 2개, RM_C10681 3.0/2.0, RM_C10484 2.5/2.5
   - 생성기 수정은 사용자 몫입니다. 예: 후보 쪽 값을 우선하도록 바꾸고 `_n31_note`에 적습니다.
   - **수용 노드 선택은 obs150 관측 출력도 바꿉니다.**
     - obs150 관측은 핀된 reference config의 `physical_ramp_receiving_nodes`를 읽어 `RampArrivalRef.receiving`을 정합니다(obs150_observation.py:605, :623-639). 이 키가 없거나 비어 있으면 거부합니다(:625-627).
     - 램프 차로 분율은 수용 노드 램프에 대해서만 나옵니다(obs150_lane.py:102-108). 그래서 수용 노드가 4개가 되면 `derived_T.json`의 `ramp_arrival_shares` 키도 4개가 됩니다.
     - 그 결과 이전 플랜트의 결정을 재생하면 `derived.ok`가 설계상 false가 됩니다(§4 L4).
2. **VSL 집합과 v_free:** 후보는 `vsl_set` [60,80,90,100,110], `v_free` 120입니다. 이 브랜치는 이제 [50,60,70,80,90,100,110]을 씁니다(생성기 `make_reference_config.py:55-56`, `make_config_n31.py:54`). v_free는 110 그대로입니다.
   - 후보 README는 90 밖으로 외삽하지 않는다고 적었습니다. SDMPC 명령 집합에는 90이 없습니다.
   - 90을 넣으려면 핀 연쇄를 따라 함께 바꿉니다: `repin_scenario_v2.py:129 VSL_SPEEDS` → `lane_native_b110.vbs` → 검지기 manifest → plant → `make_config_n31.py:54`, `make_reference_config.py:58`. v2 망에는 분포 90이 있습니다.
   - `v_free`는 셀 행 값이 우선하지만, `net.v_free`는 셀 0의 상류 속도와 기본값으로 쓰입니다(AFA:347). 120으로 바꿀지는 결정이 필요합니다.
3. **표지판 셀 (`component_vsl_transport.FW_E.sign_cells`):** 망의 표지판 위치에서 나옵니다.
   - 사용자 값 [0,3,5,8,14,16,26,28]은 "각 DSD에서 가장 가까운 셀 경계" 규칙과 8개 모두 일치합니다. 이 규칙은 코드에 없고, 결과를 보고 추정한 것입니다.
   - v2 망에서 DSD 63–66은 link 2의 3998.67 m(FW_E 누적 6733.2 m)이고, 사용자 망은 3607.22 m(6341.7 m)입니다.
   - 같은 규칙이면 v2 값은 **[0,3,5,8,14,18,26,28]**입니다. 이 안내서를 쓰며 v2 기하로 직접 계산했습니다.
   - 셀 16과 18은 모두 SDMPC 구역 2(정제셀 14–24, 부모 머리 10)에 속합니다. 26과 28은 구역 3으로, SDMPC가 바꾸지 않습니다.
   - 사용자 네이티브 실험은 DSD 63–66 한 표지판만 90이었습니다. SDMPC의 구역 명령은 구역의 모든 셀에 같은 값을 씁니다(sdmpc.py:390-394). 비교 실험을 설계할 때 주의합니다.
4. **헤드 서비스 곡선:** 후보에는 `physical_ramp_head_service_veh_per_cycle`이 없습니다. 생성기가 수송 설정의 곡선(현재 RM_C10490 하나)을 넣습니다. 사용자가 따로 보정한 헤드 서비스 곡선이 있다면 그 곡선을 이 키로 넣어야 SDMPC에 닿습니다(LPR:480-484). rollout의 `_head_service`는 SDMPC에 닿지 않고, L5 관문도 이것을 시험하지 않습니다(§2.3, §4 L5).
5. **`state_response` 셀 번호:** 정제셀(31셀) 번호입니다. 7216e25는 정제 전 21행 기준으로 검사하므로 21–25를 거부합니다(freeway_fd.py:97-99). d80faf9는 분할 뒤에 다시 설정합니다((d80faf9) CH:301-307, :324-325).

#### (d)-2 코드 가져오기 (d80faf9 → 이 브랜치)

| 파일 | 00abbab 대비 변경 | 방법 |
|---|---|---|
| CH | 사용자만 | `git checkout d80faf9 -- <CH>` |
| `evaluation/controllers/freeway_fd.py` | 사용자만 | `git checkout d80faf9 -- <파일>` |
| `evaluation/controllers/area_freeway_accounting.py` | 양쪽 | 3-way |
| `evaluation/controllers/runtime_setup.py` | 양쪽 | 3-way |
| `evaluation/controllers/physical_lane_groups.py` | 양쪽 | 3-way (v2는 차로군을 안 쓰지만 같은 함수로 정리됨) |
| `tests/test_literature_vsl_fd.py` | 사용자만 | 선택. 가져오면 시험도 같이 옵니다 |
| HO (`diagnostics/vsl_handoff_20260924/`, 79개 파일) | 사용자만 | `git checkout d80faf9 -- diagnostics/vsl_handoff_20260924` (또는 같은 저장소 경로로 복사). L3에 필요합니다 |

- **HO를 같은 저장소 경로에 두는 이유:** `candidate.json`의 `freeway.segment_params`가 `diagnostics/vsl_handoff_20260924/segment_params.json`을 저장소 상대경로로 가리킵니다. 또 `reproduce.py`는 `ROOT = HERE.parents[1]`에서 CH를 import합니다((d80faf9) reproduce.py:11-12, :98-99). 그래서 병합한 코드로 사용자 fixture 회귀(L3)를 보려면 HO가 병합 W의 같은 경로에 있어야 합니다. HO에는 하위 `.gitattributes`(`-text`)가 있어 체크아웃 바이트가 바뀌지 않습니다.

- **줄끝이 섞여 있습니다.** AFA는 00abbab와 d80faf9가 CRLF 혼합이고 7216e25는 LF입니다. runtime_setup은 7216e25만 CRLF 혼합입니다. 그대로 `git merge-file`을 하면 파일 전체가 충돌처럼 보입니다.
- CR을 뺀 사본으로 3-way 병합하면 세 파일 모두 **충돌 0**이었습니다(스크래치 확인, 실행 트리에는 적용해 보지 않음).
- 이 다섯 파일의 sha는 기록 파일(b110 `freeze.json` code_pins, 요약 JSON)에만 있습니다. 실행 중에 검사하는 코드 핀은 없습니다(copy_b110.check는 segment_params 핀만 검사, :50-52). 그래서 결과를 LF로 커밋해도 실행에는 영향이 없습니다.

```python
# W 루트, 이 브랜치 HEAD에서. PowerShell의 > 리다이렉트는 BOM/UTF-16을 섞으므로 파이썬으로 합니다.
import pathlib, subprocess
def blob(ref, f):
    return subprocess.run(['git', 'cat-file', 'blob', f'{ref}:{f}'], capture_output=True, check=True).stdout.replace(b'\r\n', b'\n')
for f in ('evaluation/controllers/area_freeway_accounting.py', 'evaluation/controllers/runtime_setup.py',
          'evaluation/controllers/physical_lane_groups.py'):
    tmp = [pathlib.Path(f'_merge_{i}.py') for i in range(3)]
    for p, ref in zip(tmp, ('HEAD', '00abbab', 'd80faf9')):   # ours, base, theirs
        p.write_bytes(blob(ref, f))
    r = subprocess.run(['git', 'merge-file', '-p', *map(str, tmp)], capture_output=True)
    print(f, 'conflicts =', r.returncode)                        # 0이어야 합니다
    pathlib.Path(f).write_bytes(r.stdout)
    for p in tmp: p.unlink()
```

- 병합 뒤 매핑 파일이 `d0a7bb9f`인지, `.gitattributes`가 7216e25 그대로인지 확인합니다(§1.1).
- `vsl_fd_response`는 **reference config(성분)에만** 둡니다. SDMPC 튜닝(config_n31_v2.json)에 넣으면 병합된 runtime_setup이 거부합니다((d80faf9) runtime_setup.py:37-39, 성분 전용).

#### (d)-3 병합만으로는 부족한 것 (추가 작업)

1. **조용한 무시를 막는 검사**
   - 병합이 빠진 트리에서 같은 reference config를 쓰면 에러 없이 기준 FD로 돕니다. 7216e25가 바로 그렇습니다.
   - `_load_sources_v2`에 검사를 하나 둡니다: reference에 `vsl_fd_response`, `component_vsl_transport`, `physical_cell_fd`, `state_response`가 있으면, `component.base.network`에 해당 속성(`freeway_vsl_fd_response`, `component_vsl_transport`, `freeway_state_response`)과 `component.cell_fd`가 실제로 설치됐는지 확인합니다.
2. **Dual과 dict 키 (도함수 워커에서 멈출 것으로 예상, 확인 안 됨)**
   - `VSLExposure`는 VSL 명령값을 코호트 dict의 키로 씁니다: `{float(commands[i]):1.}` ((d80faf9) freeway_fd.py:134). 커널은 명령을 `float(vsl_i)`로 넘깁니다((d80faf9) AFA:371).
   - 도함수 워커에서는 `float`이 Dual을 그대로 돌려줍니다(`float_keep`, sdmpc_dual.py:149-150). VSL은 Dual로 심어집니다(sdmpc_tangent_worker.py:380-384).
   - `Dual`은 `__eq__`만 정의하고 `__hash__`가 없으므로 해시할 수 없습니다(sdmpc_dual.py:153, :283).
   - 그래서 표지판 셀의 첫 `advance`에서 `TypeError: unhashable type`이 날 것으로 봅니다. **110 기준점에서도** 같습니다.
   - 방향: 코호트 키는 primal 값으로 두고, 명령의 도함수는 목표 속도 계산으로 따로 흘립니다.
3. **코호트 초기화**
   - 커널은 결정마다 첫 스텝에서 `state._component_vsl_exposure`를 만들고 모든 차량을 `initial_command` 코호트로 둡니다((d80faf9) AFA:192-198).
   - SDMPC는 결정마다 상태를 새로 만듭니다. 그래서 직전 결정에서 80을 받은 차량도 110 코호트로 다시 시작합니다.
   - `lane_plant_runtime.initialize`에서 직전에 적용한 표지 명령(또는 관측)으로 코호트를 심는 코드가 필요합니다.
   - 후보 롤아웃 사이에 상태를 복사할 때 `_component_vsl_exposure`가 함께 복사되는지도 확인합니다(확인 안 됨).
4. **110 불감대:** 사용자 모형에서도 110 기준점의 VSL 도함수는 0입니다.
   - 커널의 `vsl_active_i = vsl_i < vsl_max - 0.5`(AFA:357)와 `literature_desired_speed`의 `if spec is None or not active: return target`((d80faf9) freeway_fd.py:71)이 같은 조건입니다.
   - `VSLExposure.target`도 모든 코호트 명령이 표시 명령과 같으면 기존 값을 돌려줍니다((d80faf9) freeway_fd.py:109-110).
   - (갱신) VSL 모형 이식이 이 브랜치에 커밋되었습니다. 110에서 한쪽 도함수가 살아 있습니다(맨 위 추가 노트).
5. **결합 경로에서 코호트 보존 (확인 필요)**
   - `VSLExposure.advance`는 코호트 합과 셀 재고의 차가 1e-7을 넘으면 `ArithmeticError`를 냅니다((d80faf9) freeway_fd.py:128-139).
   - 보정 rollout에서는 통과했습니다. SDMPC 결합 경로(램프 방출과 오프 용량이 도시 쪽에서 오는 경로)에서 통과하는지는 돌려 본 적이 없습니다.
6. **full cfg 소비자 (확인 필요):** `initialize`는 성분 셀 행(`freeway_segment_params`)만 full cfg로 복사합니다(LPR:436-439). 목적함수나 자원 계산 중 full cfg로 본선 속도를 계산하는 곳이 있다면, 그곳은 `vsl_fd_response`, 노출 수송, `state_response`를 보지 못합니다.

### (e) 바꾸지 말 것

- **계약:** OC의 스키마·검증기, obs150 러너 VBS와 워치독 PS1, 검지기 CSV(생성기로만 만듭니다).
- **망:** 재핀 없이 망 바이트를 바꾸지 않습니다. `.sig`를 망 사본 옆에서 따로 바꾸지 않습니다.
- **명령 공간:** `vsl_command_space: parent_21`, `vsl_zone_heads` [0,5,10,15], `vsl_zone_free` [0,1,2], 매핑 파일 바이트.
- **적분과 경계:** `physical_integration_step_sec` 1, `lane_groups: false`, `component_boundary` {admitted_interface, open_exit}, 본선 origin queue 0.
- **생성물:** `reference_config_n31_v2.json`, `plant_n31_v2.json`, `config_n31_v2.json`을 손으로 고치지 않습니다. 생성기를 고치고 `--check`를 통과시킵니다.
- **v1 경로:** `diagnostics/lane_plant_20260921/plant.json`(v1)은 바이트 그대로 둡니다. CH를 고치면 v1 경로도 바뀝니다(v1도 같은 `CanonicalFreewayModel`을 씁니다, LPR:42-57). 그래서 §4 L2의 V1 회귀를 봅니다.
- **줄끝:** `.gitattributes`의 `-text` 줄(:5665-5670, B110 하위 `* -text`)을 지우지 않습니다. `git add --renormalize`는 쓰지 않습니다.
- **작업공간:** B110 작업공간에 덮어쓰지 않습니다. `qualification`에는 사실만 씁니다. 예: "계수는 사용자 망(401b6558/ebd90383)에서 보정, v2 재보정 없음".
- **튜닝:** SDMPC 튜닝에 성분 전용 키(`vsl_fd_response` 등)를 넣지 않습니다.

---

## 4. 검증 사다리 (싼 것부터)

명령은 모두 W 루트(또는 FRZ)에서, 아래 환경으로 돌립니다.

- **순서 주의:** 기존 N31 시험 일부는 현재 b110 플랜트의 값을 단언합니다. 그래서 reference를 바꾸면 설계상 실패합니다. L1은 먼저 **병합만 하고 플랜트는 그대로인 트리**(L2 단계)에서 통과시킵니다. 플랜트를 바꾼 뒤에는 해당 단언을 새 값으로 고칩니다.
  - `tests/test_n31_plant_load.py:117`: 수용 노드 == {RM_C10681, RM_C10484}. 후보는 4개입니다.
  - `tests/test_n31_generators.py`의 `test_c7_reference_config`(:63-79): reference freeway에서 수송 키를 뺀 것 == boundary freeway(:73-74), `vsl_set` == [50,60,70,80,90,100,110]
  - T9 `tests/test_n31_ad_smoke.py:57-61`: `vsl_max == 110.0`, `max_abs_tangent == 0.0`. `vsl_max`는 max(`vsl_set`)입니다(n31_ad_smoke.py:149).

```powershell
$env:PYTHONPATH = "$DEP\sdmpc;$DEP\sdmpc-numba"; $env:PYTHONUTF8 = '1'; $env:PYTHONDONTWRITEBYTECODE = '1'
$env:OMP_NUM_THREADS = '1'; $env:OPENBLAS_NUM_THREADS = '1'; $env:MKL_NUM_THREADS = '1'
```

### L0 생성기

- **명령:** §3(b)의 `--check` 전부. 경로 B이면 `repin_scenario_v2.py verify`도 돌립니다.
- **합격:** 모두 `…_OK`로 끝납니다. preflight는 `make_config_n31.py` 안에서 `--quiet`로 돌기 때문에, 성공하면 `CONFIG_N31_OK` 줄이 곧 preflight 통과입니다.

### L1 안전한 시험 (VISSIM, 워치독, cscript 없음)

```powershell
& $PY -m pytest -q -p no:cacheprovider diagnostics/obs150_20260924/tests --ignore=diagnostics/obs150_20260924/tests/test_runner_ps1_obs150.py
& $PY -m pytest -q -p no:cacheprovider diagnostics/sdmpc_n31_20260924/tests
& $PY -m pytest -q -p no:cacheprovider diagnostics/sdmpc_n31_20260924/tools/tests `
    --ignore=diagnostics/sdmpc_n31_20260924/tools/tests/test_tools_launch.py `
    --ignore=diagnostics/sdmpc_n31_20260924/tools/tests/test_tools_replay.py `
    --deselect "diagnostics/sdmpc_n31_20260924/tools/tests/test_tools_integration.py::RealNeighbours::test_real_watchdog_preflight_provenance_matches_the_plan"
$env:RW_OFFSET_WRITER = 'experiment'
& $PY -B -m unittest diagnostics.test_sdmpc_pfo_caps diagnostics.test_sdmpc_central diagnostics.test_sdmpc_tangent `
    diagnostics.test_sdmpc_reverse diagnostics.test_sdmpc_sequence diagnostics.test_sdmpc_surrogate_reuse `
    diagnostics.test_sdmpc_initial_shared diagnostics.test_sdmpc_hotpath diagnostics.test_shared_joint_price_quantity `
    diagnostics.test_validated_decision_hold diagnostics.test_lane_initial_projection
```

- **이 PC 기준값 (바꾸지 않은 트리):** obs150 300 passed / 1 skipped, N31 162 passed / 3 skipped, tools 60 passed / 1 deselected, 기존 SDMPC 10개 모듈 Ran 118 OK(통합 기록 §4). `test_lane_initial_projection`은 7216e25에서 추가됐습니다.
- 이 기준값은 병합만 하고 플랜트는 그대로인 트리에서 맞춰 봅니다. 플랜트를 바꾼 트리에서는 §4 첫머리의 단언들이 설계상 실패하므로, 그 단언을 새 값으로 고친 뒤 다시 돌립니다.
- **다른 PC에서는** 이 PC 경로를 읽는 시험이 skip으로 바뀝니다(§1.3). skip 수가 늘었으면 어떤 시험인지 적어 둡니다.
- **주의:** N31 픽스처는 tests 폴더 안에 임시 폴더를 만들었다가 지웁니다(n31_fixtures.py:1-9). obs150 묶음의 `test_runner_obs150_vbs.py`는 모의 COM을 cscript로, `test_runner_static_obs150.py`는 PowerShell을 띄웁니다. 둘 다 kill은 없지만, VISSIM 런이 도는 동안에는 빼는 편이 안전합니다.
- **이식 뒤 새로 넣을 시험**
  - T9 AD 스모크(`tests/test_n31_ad_smoke.py`)의 `test_vsl_anchor_at_vsl_max_is_a_zero_column`(:57-61)은 110 불감대가 남아 있는 한 계속 통과합니다. 통과해도 VSL 도함수가 살아 있다는 뜻은 아닙니다.
  - 활성 기준점(예: 80)에서 VSL 축의 AD와 중앙차분을 비교하는 시험. 형식은 T9의 `test_forward_ad_equals_central_fd`(:49-55)를 따릅니다.
  - T3 패리티(`tests/test_n31_parity.py`, `n31_parity_roles.py`)에 사용자 키를 켠 reference와 VSL 80 명령인 경우를 추가합니다. 새 상태 필드 `_component_vsl_exposure`가 워커 상태 비교(`state_error`, sdmpc_tangent_worker.py:18-)를 통과하는지 봅니다.

### L2 병합 무작용 항등 (사용자 키가 없는 reference로)

병합한 코드는 사용자 키가 없으면 아무것도 바꾸지 않아야 합니다. `literature_desired_speed`는 spec이 없으면 입력을 그대로 돌려주고, 노출 수송은 spec이 없으면 만들어지지 않습니다.

1. **(다른 PC) 기준 G1:** 병합 전 7216e25 트리로 G1형 런을 한 번 돌립니다(L6와 같은 명령). 이 런이 그 PC와 VISSIM 버전에 대한 기준입니다.
2. **(다른 PC) 병합 트리로 재생:** 그 런의 900과 1050 결정을 병합 트리로 재생합니다.
   ```powershell
   & $PY -B <FRZ>\diagnostics\sdmpc_n31_20260924\tools\make_replay_state_v2.py prepare <run>\decisions_<Name> 900 <ReplayDir>
   powershell -NoProfile -ExecutionPolicy Bypass -File <FRZ>\diagnostics\sdmpc_n31_20260924\tools\replay_decision_n31.ps1 -ReplayDir <ReplayDir> -Root <병합 W> -DepRoot $DEP
   ```
   **합격:** `REPLAY_COMPARE verdict=IDENTICAL`, 종료 코드 0.
3. **(이 PC에서만) V1 회귀:** 옛 21셀 경로 900초 재생의 `metadata.leader_objective`가 기본 cap margin에서 **393.9163955132781**, margin 0에서 **393.91612458424544**여야 합니다(통합 기록 §3). 원본 런 `D:\VISSIM_runs\20260923_sdmpc\sdmpc_lp_9000`이 이 PC에만 있습니다. 도구는 `diagnostics/sdmpc_native_20260923/tools/{make_replay_state.py, replay_decision.ps1}`입니다.

### L3 110 유지 항등 (사용자 모형 안에서)

사용자 모형은 우리 플랜트와 다릅니다(파라미터, 셀 v_free, anticipation). 그래서 우리 결정과는 IDENTICAL이 나올 수 없습니다. 항등은 사용자 모형 안에서 봅니다.

1. **사용자 fixture 회귀**
   - `HO/reproduce.py offline`은 176개 파일의 sha manifest부터 검사합니다(`verify_manifest`, reproduce.py:26-50). 병합 트리에서는 그 단계에서 멈춥니다.
   - rollout과 해시 비교 부분(:98-117)만 부르는 작은 스크립트를 씁니다. `load_base_model(geometry, candidate.json)` → `model.rollout(*args, **kwargs)` → 배열 sha 비교입니다.
   - HO가 병합 W의 같은 경로(`diagnostics/vsl_handoff_20260924/`)에 있어야 합니다(§3(d)-2).
   - **합격:** `rollout_sha256`가 frozen 값과 같고, 예측 TTT가 NC **140.690656672765**, VSL **140.421537434149** veh·h입니다(HO README).
2. **VSL 무작용**
   - `none` 팔로 두 번 돌립니다: 원래 candidate.json 한 번, `vsl_fd_response`와 `component_vsl_transport`를 뺀 사본 한 번.
   - **합격:** 네 배열(cells, flows, ports, ramps)의 sha가 같아야 합니다.
   - 먼저 `none` 팔의 `vsl_commands`가 전부 110인지 확인합니다(확인 안 됨). 110이 아닌 명령이 있으면 이 항등은 성립하지 않습니다.
3. **SDMPC 쪽 무작용:** 사용자 reference로 만든 플랜트에서 네이티브 110 유지 결정(예: 자기 G1의 900)을 재생합니다. 비교 대상인 원 결정도 같은 플랜트로 나왔어야 합니다. 다음 절(L4)의 결정론 확인이 이것을 겸합니다.

### L4 오프라인 재생 (새 플랜트)

- **명령:** L2-2와 같고, `-Root`만 새 플랜트를 넣은 트리로 바꿉니다.
- **다른 플랜트의 결정을 재생할 때** (예: 7216e25 트리로 돌린 G1의 결정)
  - `DIFFERENT`(종료 코드 2)가 정상입니다.
  - 합격은 세 가지입니다: `REPLAY_<T> exit=0`(어댑터 성공), `replay_compare.json`의 `derived.ok` true, `action_contract.ok` true.
  - 단, `derived.ok` true는 **수용 노드 집합이 같을 때만** 기대합니다. compare는 derived를 `inputs.raw_sha256`만 빼고 전부 비교합니다(make_replay_state_v2.py:263-269). 수용 노드가 바뀌면 `ramp_arrival_shares` 키가 달라지므로(§3(d)-1 1번) `derived.ok`는 false가 됩니다. 이때는 `derived.differences`가 `ramp_arrival_shares`뿐인지 확인합니다.
- **새 플랜트로 돌린 네이티브 런의 결정을 같은 트리로 재생할 때:** `IDENTICAL`이어야 합니다(결정론).
- **110 전제가 코드에 박힌 곳:** VSL이 실제로 움직이는 플랜트에서는 아래 둘이 설계상 깨집니다. 의도적으로 바꿉니다.
  - 재생 비교 `action_contract`(make_replay_state_v2.py:234-242): VSL 66행, 미터 8행, 그리고 `--vsl-expected`가 있으면 속도 = [기댓값]. 재생 PS1은 항상 `--tuning`을 넘기므로(replay_decision_n31.ps1:144) 기댓값은 max(vsl_set) = 110입니다. → 허용 집합 소속 검사로 바꿉니다.
  - T9 `max_abs_tangent == 0.0` 단언 → 0이 아닌 AD 대 중앙차분 검사로 바꿉니다.
- **실패한 결정 재생:** 원본 action이 없으므로 compare는 구조적으로 DIFFERENT(종료 코드 2)입니다. `REPLAY_<T> exit=0`과 `action_contract` ok가 합격입니다. 실례: `replay_v5_1950_fix`(wall 438 s).
- 재생은 런 폴더의 절대경로에 묶여 있습니다. prepare는 `obs150.directory`가 그 decisions 폴더와 같아야 한다고 요구합니다(make_replay_state_v2.py:116-117). 그래서 **다른 PC로 옮긴 런은 그대로 재생할 수 없습니다.** 그 PC에서 돌린 런으로 합니다.

### L5 V3b 플랜트 관문 (`N31D/tools/plant_gate.py`)

- `<REF>`: 관문용 reference입니다. 사용자 플랜트면 **수용 노드 키(`physical_ramp_receiving_nodes`)를 뺀 사용자 reference(후보) 사본**을 씁니다(아래 "수용 노드가 있으면 거부합니다"). b110 플랜트를 다시 볼 때는 G1b처럼 보정 `boundary_config.json`을 씁니다.

```powershell
$TOOLS = 'diagnostics\sdmpc_n31_20260924\tools'
$T = 'diagnostics\sdmpc_n31_20260924\config_n31_v2.json'
& $PY -B $TOOLS\plant_gate.py extract --run <G1 런> --cutoff 900.1 --tuning $T --out <gate>\obs
& $PY -B $TOOLS\plant_gate.py window --observations <gate>\obs --cutoff 900.1 --tuning $T --reference-config <REF> --out <gate>\window.json
& $PY -B $TOOLS\plant_gate.py run --tuning $T --decisions <G1 런>\decisions_<Name> --window <gate>\window.json --cutoff 900 `
    --reference-config <REF> --band FW_E=<held-out>,FW_W=<held-out> --out <gate>\gate.json
```

- **동작:** 900초 결정의 VSL을 유지한 채 31셀 성분을 450 s rollout합니다. +150/+300/+450 s에서 G1 프레임과 셀 속도를 비교합니다(관측 N ≥ 5인 셀만).
- **판정:** 도로별 세 lead를 묶은 속도 RMSE로 PASS(≤ 밴드) / OUTSIDE_BAND(≤ 2×밴드) / STOP_ASK(그 위, 멈추고 판단) / NO_SPEED_SAMPLES. 종료 코드는 전부 PASS면 0, 아니면 1, 도구 오류는 2입니다(plant_gate.py:201-207, :465-476).
- **밴드:** 기본 FW_E 25, FW_W 17 km/h는 b110 보정의 held-out 값입니다(:77). 사용자 플랜트는 **자기 held-out 수치**를 `--band`로 넘깁니다. 표본이 하나뿐이라 점검이지 통계 검정이 아닙니다.
- **수용 노드가 있으면 거부합니다.**
  - window 파일에는 `ramp_dynamics`가 없습니다(build_window_file, :336-350). reference에 `physical_ramp_receiving_nodes`가 있으면 `run`이 거부합니다(:367-370).
  - G1b는 수용 노드가 없는 보정 `boundary_config.json`을 `--reference-config`로 넘겨 돌렸습니다.
  - 사용자 candidate에는 수용 노드 4개가 있습니다. 관문용으로 그 키를 뺀 사본을 쓰거나, plant_gate에 ramp_dynamics 구성을 추가합니다.
- **관문은 rollout 경로를 시험합니다**(§2.3). 관문 창 파일에는 `ramp_dynamics`가 없으므로(build_window_file :336-350, `run`은 창에 있을 때만 넘김 :367-370, :386), 병합으로 들어온 `_head_service`와 `ramp_arrival_lane_profile`은 관문 rollout에서 한 번도 불리지 않습니다((d80faf9) CH:732, :798-801, :974). **관문은 이 둘을 시험하지 않습니다.** 헤드 서비스는 SDMPC 쪽 LPR:480-484 경로로만 들어갑니다.
- **G1b 실측:** `PLANT_OBSERVATIONS_OK checks=1860 removals=14`, lane_loss_off 기준 FW_E 21.44 / FW_W 12.31 km/h, PASS.

### L6 네이티브 확인 런 G1 (1350 s, 정답 창)

```powershell
Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{
  CommandLine = 'cmd.exe /c powershell -NoProfile -ExecutionPolicy Bypass -File <W>\tools\sdmpc31\run_sdmpc_n31.ps1 -Freeze -Tuning diagnostics\sdmpc_n31_20260924\config_n31_v2.json -Name sdmpc31_g<x> -SimPeriod 1350 -Seed 31 -GroundTruthWindows 750:900,1050:1200 -FrozenRoot <짧은 경로> -FreezeTool <W>\tools\sdmpc31\freeze_worktree.ps1 -PrepareNetworkTool <W>\tools\sdmpc31\prepare_sdmpc31_network.py -RunsRoot <RUNS> -Python <PY> -DepRoot <DEP> > <콘솔 로그> 2>&1'
  CurrentDirectory = '<W>'
}
```

- **결정:** t=1과 150…750은 no-control 준비 결정(`CONTROL_START_SEC` 900), 900/1050/1200/1350은 SDMPC입니다.
- **고정 값:** 결정 간격 150, StartupStall 300, StallSec ≥ 2400, MaxAttempts 1, NoGlobalKill(launch_plan.py:39-43; run_sdmpc_n31.ps1:115).
- **이름:** 정답 창은 이름이 `sdmpc31_g`로 시작하는 dev 런에서만 허용됩니다(OC:128). 창은 150의 배수이고 정렬, 비겹침이어야 합니다. 시작이 150 미만이거나 붙은 창(`750:900,900:1050`)은 거부되므로 합쳐서 씁니다.
- **G1b 벽시계:** 워치독 3626 s. 결정 900 = 605.8, 1050 = 547.7, 1200 = 494.5, 1350 = 153.9 s.
- **먼저 볼 것:**
  - runlog의 t=1 결정 exit 0. 깨끗한 체크아웃에서 빠진 파일(§1.1)은 여기서 드러납니다.
  - 150…750 결정 exit 0, `derived_*` 지연 OK
- **D6 정답 대조:**
  ```powershell
  & $PY -B <FRZ>\diagnostics\sdmpc_n31_20260924\tools\obs150_verify_gt.py <run>
  ```
  - 기본은 `--sig-rule next --com-head-delay 1`입니다. 결과는 `<run>\obs150_gt_verdict.json`에 쓰입니다.
  - 종료 코드: PASS 0, FAIL 1, GT_ERROR 2, INCOMPLETE 3. **3은 통과가 아닙니다.**
  - **종료 코드만 보지 말고 `failed` 목록을 봅니다.** G1b는 1이었지만, 두 창 모두 실패 항목이 `gt_anomalies`(SC1002 헤드 90030858/90030859의 애매한 출구) 하나였습니다. 항목 수는 6건과 12건이고, 차량으로는 2대와 4대입니다(차량 한 대에 pid 3개).
  - `GT_D10 ok=True`여야 합니다(G1b: delay 1, 154/154).
  - 교차 확인: `--com-head-delay 0`으로 돌리면 FAIL이 나야 합니다.
- **G1 상태로 돌리는 시험:** T5는 `N31_G1_STATE=<run>\decisions_<Name>\state_000900.json`으로 `test_n31_initialize.test_g1_frame`을 돌립니다. T6는 `tests/t6_guarded_decision.py`로 21셀 조용한 폴백을 예외로 바꿔 한 결정을 돌립니다(종료 코드 0 통과, 2 가드 위반).
- **그다음:** 이 런으로 L4(자기 결정 재생 = IDENTICAL)와 L5를 합니다.

### L7 9000 s (V5b 방식)와 짝 무제어

- **발사:** L6 명령에서 `-Name sdmpc31_<이름> -SimPeriod 9000`로 바꾸고, `-GroundTruthWindows`를 뺍니다. `-StallSec`은 max(2400, 2 × G1에서 잰 최대 결정 벽시계)로 둡니다.
  - 이미 FRZ 안에서 발사하면 `-Freeze`를 빼고 CurrentDirectory를 FRZ로 둡니다.
  - 벽시계는 결정 55회 × 결정당 시간 + 약 1.5시간으로 잡습니다.
- **짝 무제어 V4:** 같은 FRZ에서 `-Name sdmpc31_nc_<이름> -SimPeriod 9000 -Seed 31 -Controller no-control [-AllowConcurrentDev]`.
- **감시:**
  ```powershell
  & $PY -B <FRZ>\diagnostics\sdmpc_n31_20260924\tools\watch_sdmpc.py <run> <run>\launch_<Name>.log <run>\watch.txt --stall-min 40
  ```
  결정마다 한 줄을 쓰고, `DECISION FAILED`와 `STALL`을 찍으며, 발사기의 `EXIT` 줄에서 끝납니다.
- **합격:**
  - `EXIT <Name> code=0`, 요약의 `DECISIONS_FAILED=0`
  - V4와 V5의 `frame_000150…000900` `vehicles`가 같음(결정론)
  - FZP Omega TTT는 stage-1과 같은 방법으로 셉니다

---

## 5. 운영 수칙

### 5.1 발사는 세션 밖에서

- 1시간이 넘는 런은 `Invoke-CimMethod -ClassName Win32_Process -MethodName Create`로 띄웁니다. 부모가 WmiPrvSE가 되도록 하기 위해서입니다(`tools/sdmpc31/README.md:10`).
- Claude Code 세션의 백그라운드 셸로 띄운 런은 세션이 끝날 때 함께 죽을 수 있습니다. 09-24 11:10 stage-1 재실행 3런이 7200–7500 s에서 동시에 멈췄습니다(원인은 추정).
- 콘솔은 `> log 2>&1`로 따로 남깁니다. 동결 단계 로그는 런 폴더가 생기기 전이라 발사기 로그에 늦게 들어갑니다.
- 발사기 종료 코드: 0 ok, 1 워치독 실패, 2 인자, 3 동결·계획 거부, 4 망, 5 자리 없음, 6 preflight, 7 provenance 불일치(run_sdmpc_n31.ps1:31-32).
- `-PreflightOnly`는 VISSIM 없이 계획, 망 사본, 워치독 preflight, provenance 대조까지 합니다. 새 PC에서 첫 G1 전에 돌려 볼 만합니다.

### 5.2 자리 규칙 (VISSIM 동시 실행)

- **보통 발사:** 발사 전 VISSIM 합계 ≤ 3, dev 제목(`obs150|sdmpc|probe`) 0개.
- **`-AllowConcurrentDev`:** 합계 ≤ 2, 다른 dev ≤ 1(run_sdmpc_n31.ps1:84-87). 어느 경우든 총합은 4를 넘지 않습니다. 이 PC에서는 5번째 VISSIM의 COM 생성이 거부됩니다.
- 자리는 계획 전과 발사 직전에 두 번 확인합니다. 발사 직전에 자리가 없으면 `NOT_LAUNCHED.txt`를 남기고 code 5로 끝납니다. 이때는 새 `-Name`을 씁니다(:229-235).
- 망 사본 이름 `sdmpc31_<Name>.inpx`가 창 제목에 들어가서 이 런이 dev로 셈해집니다.
- 이 규칙은 이 PC의 stage-1 큐에 맞춘 것입니다. 다른 PC의 라이선스 한도에 맞게 판단합니다.

### 5.3 동결 (FRZ)

- 발사는 FRZ에서만 합니다. 튜닝 위쪽에 `FREEZE.json`이 없으면 code 3입니다(:172).
- `freeze_worktree.ps1`이 하는 일:
  - W를 robocopy로 `<FrozenRoot>\sdmpc31_<head8>_<yyyyMMddHHmm>`에 복사합니다. `.git`, `__pycache__`, `.pytest_cache`, `__tangentcache__`, `*.pyc`는 뺍니다(:48).
  - git HEAD, `git status`의 sha, 전 파일 sha를 `FREEZE.json`에 적습니다.
  - 복사 중 W가 바뀌면 실패합니다. 기존 FRZ는 이름을 바꾸거나 지우지 않습니다.
- **미추적 파일도 FRZ에 들어갑니다.** 실행 트리는 W가 아니라 FRZ입니다. FrozenRoot는 짧은 경로에 둡니다.
- `__tangentcache__`: 도함수 코드 캐시입니다. 런이 FRZ 안에 새 항목을 씁니다(G1b는 87개). 그래서 b5f1104 전 FRZ는 `FREEZE_VERIFIED`가 실패했습니다. 지금은 제외됩니다(freeze_manifest.py:35-37).

### 5.4 바이트 핀

- 이 PC는 `core.autocrlf=true`입니다.
- `-text` 줄: `N31D/**`, `diagnostics/obs150_20260924/**`, `diagnostics/lane_plant_20260921/scenario/lane_native_sgplan.vbs`, `tools/sdmpc31/**`(.gitattributes:5665-5670). B110은 하위 `.gitattributes`(`* -text`)로 지킵니다.
- 확인 명령: `git check-attr text -- <path>`. `git add --renormalize`는 금지입니다.
- 20358cf 사례: 새 체크아웃에서 매핑 파일 줄끝이 바뀌어 첫 결정이 `Geometry profile mapping mismatch`로 실패했습니다. 파일 215개를 `-text`로 고정해 해결했습니다.
- 새로 만든 sha 핀 대상 파일은 `-text` 폴더 안에 두거나 `.gitattributes`에 추가합니다.

### 5.5 전역 kill 위험

- 옛 워치독 `run_real_world_single_watchdog_distributed_core15n41.ps1`의 `Kill-Vissim`은 **이름으로** PC 전체의 VISSIM200, VISSIM200CL, cscript를 죽입니다. 09-24 03:15에 시험 한 번이 동시 런 3개를 날렸습니다.
- **런이 도는 동안 돌리지 않을 시험**
  - 옛 워치독을 띄우거나 cscript를 쓰는 것: `scripts/tests/test_b1a_watchdog_attempt_launch.py`, `scripts/tests/test_run_plant_fidelity_matrix.py`, `diagnostics/test_native_vbs_clock.py`, `diagnostics/test_signal_actuation_contract.py`, `diagnostics/test_signal_observation_window_patch.py`
  - SDMPC-31 쪽에서 뺄 것: `test_runner_ps1_obs150.py`, `tools/tests/test_tools_launch.py`, `tools/tests/test_tools_replay.py`, `test_tools_integration`의 real_watchdog 1건(L1 명령이 이미 뺍니다)
- v2 워치독(core17legs4b)은 `NoGlobalKill`을 강제하고, `Kill-Vissim`을 throw로 막고, `MaxAttempts > 1`을 거부합니다(scripts/run_real_world_single_watchdog_distributed_core17legs4b.ps1:453-461, :740-751). 정지는 PID와 시작 시각으로 확인한 자기 프로세스에만 합니다.

### 5.6 실패한 런

- **이름을 바꾸지 않습니다.** 상태 파일이 decisions 폴더의 절대경로를 담고 있어 재생이 깨집니다(make_replay_state_v2.py:116-117). `launch_plan`은 기존 폴더를 거부합니다(:170). 새 이름으로 재발사합니다(G1 → G1b, V5 → V5b).
- **실패는 즉시 드러납니다.**
  - 발사기가 `RW_OFFSET_WRITER=experiment`를 세웁니다(:212). 결정 하나가 실패하면 VBS가 `ERROR=EXPERIMENT_DECISION_FAILED`를 찍고 멈춥니다. 워치독은 한 번만 시도하므로 발사기는 code 1로 끝납니다.
  - 원인은 runlog의 `ERROR=DECISION_EXIT_NONZERO sim_sec=T … stderr=<traceback>` 줄에 있습니다.
- **복구 순서:** traceback → `prepare`로 그 결정을 격리 → `-Root <고친 W>`로 재생(L4의 실패 결정 재생) → 새 이름으로 재발사.

---

## 6. 네이티브에서만 드러난 결함 (새 플랜트 점검표)

단위시험과 오프라인 검사를 모두 통과한 뒤 네이티브 런에서만 나온 결함입니다. 새 플랜트에서도 같은 자리를 먼저 봅니다.

| 커밋 | 결함 | 드러난 곳 | 새 플랜트에서 확인할 것 |
|---|---|---|---|
| ea14026 | 램프 미터 SC 9101–9108은 `.sig`가 없는 FIXEDTIME이라 신호 시계가 `Native SG 9101-1 has no .sig program`으로 실패했습니다 | G1 t=150 (no-control) | 망을 바꿨다면 계획표 없는 SC 목록(`Obs150Context.programless_scs`)이 맞는지 봅니다 |
| b5f1104 | D6 대조기가 입력 링크(26, input 1099) 중간에 커넥터 10480이 붙은 경우를 몰라, FW_W 원점 진입 189/199를 설명하지 못했습니다(도구 결함) | G1b D6 첫 판 | D6 FAIL이면 `unexplained` 목록부터 봅니다. 컨트롤러가 아니라 도구일 수 있습니다 |
| b5f1104 | obs150 러너는 0.1 s에 FZP 첫 프레임을 남기는데, B110 FZP에는 없어서 plant_gate extract가 실패했습니다 | V3b 첫 시도 | 다른 러너로 만든 FZP를 쓰면 프레임 위상을 확인합니다 |
| b5f1104 | 런이 FRZ 안 `__tangentcache__`에 87개를 써서 `FREEZE_VERIFIED`가 실패했습니다 | V3 재생 | 새 캐시나 런타임 쓰기 폴더를 만들면 동결 제외 목록에 넣습니다 |
| 7216e25 | link 71 차로 3에 14대가 있었는데 모형 저장 용량은 81.24 m / 6.0 m = 13.5대라 초기화가 `Initial vehicles exceed physical storage`로 실패했습니다(VISSIM 큐 간격은 약 5.8 m) | V5 1950 s | 초기화의 저장 용량 검사를 바꾸는 플랜트라면 `lane_initial_projection`(opt-in, config :8082)과 같은 보존 투영이 필요한지 봅니다 |
| cd87e76 (09-23, v1) | ControlAction과 ndarray를 JSON으로 못 씀, numpy 예산 스칼라, 헤드 관측 5 s 간격 대 매초 프레임 | v1 첫 네이티브 결정들 | 새 메타데이터 필드는 `_json_evidence`를 거치게 합니다 |
| 5a86363 (09-23) | 재고 차감 허용치 16 ULP를 17 ULP 잔차가 넘음 | 첫 연속 결정 1050 | 새 보존 검사(예: `VSLExposure`의 1e-7)는 결합 경로 잔차로 한 번 재 봅니다 |
| 20358cf (09-23) | autocrlf 새 체크아웃에서 sha 핀이 깨짐 | 새 체크아웃 첫 결정 | §5.4 |
| 2bf00cf (09-23) | 코드가 경로를 직접 만드는 미추적 입력 16개가 빠짐. `sys.addaudithook`으로 연 파일 798개를 추적해 찾음 | 새 체크아웃 | §1.1의 미추적 차이. 같은 방법으로 다른 PC의 첫 결정을 추적할 수 있습니다 |

**교훈**
- 결정이 실패하면 거기서 멈춥니다. 저장된 상태로 오프라인에서 고치고 재생으로 확인한 뒤, 다시 동결해서 새 이름으로 재발사합니다.
- 판정기 FAIL은 항목별로 봅니다.
- 한 번 통과한 결정 시각을 넘어서야(예: 1950 s) 드러나는 결함이 있습니다. 9000 s 런은 끝까지 감시합니다.

---

## 7. 알려진 한계와 열린 문제

### 7.1 VSL 도함수가 110에서 0

- 기준점 110에서는 VSL이 비활성입니다(AFA:357). 그래서 VSL 축의 도함수가 0이고 SDMPC는 VSL을 움직이지 않습니다.
- T9가 이것을 단언합니다(`test_vsl_anchor_at_vsl_max_is_a_zero_column`). V3b의 유지 명령도 8개 구역 모두 110이었습니다.
- 사용자 모형을 넣어도 불감대는 그대로입니다(§3(d)-3 4번).
- (갱신) 사용자 VSL 모형 이식과 {50..110} 집합이 이 브랜치에 커밋되었습니다. 위 서술은 이식 전 상태입니다. 현재 동작은 맨 위 추가 노트를 보십시오.

### 7.2 사용자 망과 v2 망의 시나리오 차이

`section_diff`로 확인했습니다: `N31D/network/baseline_s31_v2nc.inpx`(`f475ce42`) 대 `HO/network/native_seed29.inpx`(`64cf5f55`).

| 항목 | SDMPC v2 | 사용자 |
|---|---|---|
| input 1098 (FW_E, link 74) | 7096.32/10137.6/10644.48/9123.84/7096.32/5068.8, vehComp 1 | 같은 수요, vehComp 14 |
| input 1099 (FW_W, link 26) | 4300/5600/6000/5200/3900/3450, vehComp 1 | 8870.4/12672/13305.6/11404.8/8870.4/6336 (**×2.06**), vehComp 14 |
| vehicleComposition 14 | 없음 (comp 1의 진입 희망속도 분포는 40/30) | "Freeway entry DSD110" (진입 분포 110) |
| DSD 110 분포 | 98–140 km/h | 75–145 km/h |
| DSD 63–66 (FW_E, link 2) | 3998.67 m → 정제셀 18 | 3607.22 m → 정제셀 16 |
| 검지기 910117–910181 | 없음 | 65개 추가 |
| randSeed | 31 | 29 |
| 같은 것 | 링크, 헤드, 신호 제어기, 경로, `.sig` 42개 | |

- **SDMPC가 강제하는 것:** 망 sha와 "망 시간표 = 보정 원점 수요"를 강제합니다(LPR:611-620). 그래서 1099 수요가 다른 기하는 v2 망에 쓸 수 없습니다.
- **사용자 결과의 범위:** 이득은 seed 29에서만 확인됐고, seed 43에서는 손해였습니다(+67.6 veh·h, HO README). 90 밖은 검증되지 않았습니다.
- **seed:** SDMPC-31의 검증 런은 모두 seed 31입니다.

### 7.3 이월한 사전 보정 팩 7개 (D-B)

`repin_scenario_v2.PRIOR_DECLARATIONS`(:120-128)는 fcb349d3 망에서 보정한 값을 v2로 그대로 이월하고 `prior_mismatch` 영수증을 붙입니다.

- `dynamic_area_routes_ver2`
- `native_input_1093_prehead_ver2`
- `native_internal_inputs`
- `route_choice_corridor_1099_sc15_calibrated`
- `route_choice_corridor_1100_sc15_calibrated`
- `route_choice_corridor_sc1004_calibrated`
- `sc2001_corridor_nc13`

첫 9000 s 런 뒤에 다시 맞출 대상입니다. `prior_mismatch`는 아직 런 provenance에 기록되지 않습니다.

### 7.4 그 밖의 열린 항목 (통합 기록 §9, 7216e25 기준)

- **manifest `qualification`:** 문구가 "G1 D6 pending", "D10 pending the G1 D6 re-check"로 낡았습니다. 다음 재생성 때 G1b 결과로 고칩니다. 이 줄을 바꾸면 plant sha가 바뀝니다.
- **D11:** .err 실시간성. 보고만 합니다.
- **R항 누락:** `route_next_link_not_found` 차량이 R항에서 빠집니다.
- **잘못된 시간초과 보고:** `RunCapture3Timeout`의 stderr가 4 KB를 넘으면 EXEC_TIMEOUT으로 잘못 보고됩니다.
- **GT 누락:** 정답 기록이 체인 커넥터 10699/10702를 기록하지 않습니다.
- **O5:** PS1 :439가 `Log`를 정의(:444)하기 전에 부릅니다. vbs config가 없을 때만 문제가 됩니다.
- **D10 판정의 민감도:** 모순 하나로 FAIL이 되고, `LEAD_GAP_M = 3.0`은 거짓 FAIL을 낼 수 있습니다. FAIL이면 `contradiction_samples`를 직접 봅니다.
- **이식 관련 (확인 안 됨):**
  - Dual dict 키 TypeError(§3(d)-3 2번)
  - 코호트 초기화와 후보 간 복사(3번)
  - 결합 경로의 코호트 보존(5번)
  - full cfg 소비자(6번)
  - 깨끗한 체크아웃의 미추적 입력(§1.1)
