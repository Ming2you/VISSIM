# Meter·VSL 변경 이력과 5% 개선 비교

2026-09-13. Git·기존 config·action·완료 진단을 읽은 제한적 검토다. 새 VISSIM/모델 실행이나 정본 수정은 없다.

**찾은 5.6781% 런도 VSL120km/h·8개 미터 g10을 유지했다.** 따라서 그 5%가 과거 meter/VSL의 효과였다가 사라졌다는 증거는 없다. 실제로 크게 달라진 것은 도시 신호 변경 방식과 수요·비교 길이이며, 미터 모델 의미도 별도로 달라졌다. 이를 같은 조건의 성능 회귀로 단정하지 않는다.

| 비교 | 이전5.6781% | 현재0.5704% |
|---|---|---|
| 제어 런 | codex_selected_fw070_u040_beta0_r02 | codex_fid_cl9000_s13_v3 |
| 수요/seed | 고속도로70%·도시40% /13 | 고속도로80%·도시50% /13 |
| Ω TTT 구간 | 0–5400초 | 0–8850초 중단 구간 |
| NC→CL TTT [veh·h] | 1938.977083→1828.880000 | 4155.383750→4131.682500 |
| 실제 freeway 명령 | VSL120, 미터 g10 | VSL120, 미터 g10 |
| 도시 변경 | 한 결정에 여러 owner 변경 | 대표2400/3150/4500 부분 sweep에서 한 owner 채택 |

이전 수치와 전체 CSV/readback 확인은 병행한 fast_np_patch_review의 역사 런 검토 근거다. 이 문서는 두 config와 각 action900을 직접 확인했다. 같은 물리 망 SHA도 수요·관측 상태·모델·신호계획·실행 조건이 모두 같다는 뜻은 아니다. 과거 fast NC는 현 정본 NC wrapper와 궤적 동치가 인증되지 않았으므로 두 개선율의 차이를 코드 회귀율로 계산하지 않는다.

## 실제로 바뀐 부분

### 네 그룹 요청률에서 여덟 물리 미터로

f61d95e에서 정본에 보존된 physical branch 경로는 네 그룹 재고·요청률을 여덟 connector별 재고·합류 위치·서비스 상한으로 바꾼다. 접근 링크의 기존 도시 재고는 별도로 유지하며 같은 차량을 다시 추가하지 않는다.

과거 action900의 그룹 요청률은 R_D_W1169.0635, R_F_W1484.5317, R_D_E1800, R_F_E962.6324veh/h이고 N_UF5416.2276이지만 실제 SG는 모두 g10이었다. 옛 allocator는 요청률이 Σmin(표상 서비스, 추정 수요) 이상이면 완전 개방하고 모델 요청값을 그대로 유지한다. **요청 숫자가 내려가도 native g10이 되는 문제와 현재 g8 상한이 예측 재고보다 높은 문제는 다른 원인이다.**

현재 action900은 1차로1512·2차로3024veh/h의 여덟 서비스 상한이며 N_UF2000.7406veh/h는 예측 실제 합류량이다. 둘을 같은 총량으로 비교하지 않는다.

### g10의 의미와 실제 명령 기준 ±2초

현재는 표가 g10에서도 각 램프의 고정 모델 용량을 정한다. 옛 표의 g2·g3은 실측 기반, g≥4는 외삽이라는 기존 주석이 있으나 이번에 원 측정을 재인증하지 않았다. 현재 RG 조건의 OPEN 포화방출 상한으로1512가 맞는지는 아직 검증되지 않았다.

| 녹색 [s] | 1차로 서비스 [veh/h] | 2차로 서비스 [veh/h] |
|---|---:|---:|
| 10 | 1512.0 | 3024.0 |
| 9 | 1328.4 | 2656.8 |
| 8 | 1166.4 | 2332.8 |

서비스 표 이후 별도의 출발손실을 반복 차감하는 항은 확인되지 않았다. Native g10은 계속 GREEN이며 주기마다 재출발하지 않는다. 모델은 평균 서비스 상한을 사용하고 native10초 RG 펄스 자체를 시간별로 복제하지 않는다.

사용자 지정 황색0·주기10초·직전 실제 녹색에서±2초를 지킨다. g10에서 g8/g9/g10만 가능하고 같은 결정 안에서 g8→g6로 box를 밀지 않는다. 동률이면 incumbent를 유지하며450초 동안 후보 하나를 유지한 예측이므로 미래10→8→6의 이득을 미리 평가하지 않는다. 영구 OPEN의 증명은 아니다.

### N_UF는 현재 유지 명령의 예측 합류량 주변으로 고정

현재 목표는 매 결정 실제 유지 명령의450초 예측에서 정한 뒤 모든 후보에 고정한다. 허용오차는±40veh/h=450초±5대다. 유지 명령보다 총 유입을 크게 낮추는 선택을 제한할 수 있다. 같은 총량 내 시간·램프 배분은 달라질 수 있다.

그러나2400초 제한 재현에서는 여덟 g8 후보가 모두 제약을 통과했다. 해당 시점 미터 미선택을 N_UF 기각으로 설명하지 않는다. E8의10639는45개10초 질의 전부 가용재고가 최소항이었고 최대2대가 g8의3.24대보다 작았다. 반면10490은5개 질의에서 g8 상한이 결합해 램프 TTT가 증가했다. 모델이 미터를 무시하거나 램프 대기를 TTT에서 빼먹은 결과는 이 재현에서 확인되지 않았다. 다른 시각이나 native RG 효과까지 입증한 것은 아니다.

### 후보 채택 방식이 더 직접적인 차이

joint_owner_game이 없던 이전5.678% 실행과 현재19-owner game은 같은 최적화 경로가 아니다. 현재 balanced traversal은 freeway owner도 초반에 방문하게 하지만, 한 고정 incumbent에서 비교한 뒤 가장 큰 **own-payoff 개선 하나**를 채택한다. 이는 global ΩTTT 개선 순위와 일반적으로 다르다. 마지막 gap 감사는 명령을 채택하지 않는다.

대표2400/3150/4500에서는 한 sweep도 완료하지 못했고 FW 이웃은3~4개만 완료했다. FW63개 후보 중 처음은 결합/VSL/미터 g9이고 순수 g8은6/12/18/22번째라 초반에는 미방문이었다. 관측된 작은 FW 이득보다 도시 이득이 커서 도시 owner 한 개가 선택됐다. 미방문 후보를 동률이나 열등으로 취급할 수 없다. 전체 시간 제한 해제와 별개로 후보120초 예산은 남아 있다.

이전 도시14~17 owner가 동시에 움직이던 정책과 현재 한 owner씩 움직이는 정책은 우선 비교할 대상이다. 수요·상태를 맞춘 재생이 없어 성능 저하의 인과효과를 수치로 배분하지 않는다.

### 방향별 two-branch 구현은 있지만 두 런 모두 사용하지 않았다

two-branch 배선은6056c94, 일관된 cell FD hook은c5dc618, 방향별 critical-density 지원은f61d95e에서 확인된다. 두 config에는 freeway.two_branch 절이 없고 **두 실제 action900도 two_branch_fd_enabled=0, freeway_fd_consistent_enabled=0을 기록했다.** 구현 코드 존재와 사용을 구분한다.

두 런의 segment_params 파일, VSL80/100/120·구역, 기본rho_crit27, freeway_capacity6937, lane_drop_phi3, merge delta0.3이 같다. 현재 모델에도 합류로 인한 속도 감소항이 있다. 이번 차이를 방향별 two-branch 또는 새 VSL capacity-gain 설정 때문이라고 설명할 근거는 없다. 모델의 모든 다른 항까지 같다는 주장은 아니다.

## Git 근거와 한계

- bc9078e(2026-09-10): 물리 미터 최종화 후 점수 계산, writer 일치 검사. 두 비교 런보다 앞선 변경이다.
- f61d95e(2026-09-13): 4→8, N_UF 정의/고정, 후보/예산/가격·game, 방향별 FD 등을 여러 날 작업 후 한꺼번에 보존한 인계 커밋이다. 세부 변경의 실제 적용 시각이나 회귀 원인 하나를 이 커밋만으로 특정할 수 없다.
- 옛 config 설명문에는 더 오래된 실험 주장이 섞여 있다. 이를 해당5.678% 런의 실제 실행 증거로 쓰지 않았다.
- 새 모델/native 실험 없는 코드·기록 대조다. 소스별 SHA, 정확한 action900 수치, config 비교는 동봉 JSON에 있다.

## 확인한 위치

**four_to_eight**: [physical_ramp_branches.py:35](../../evaluation/controllers/physical_ramp_branches.py#L35), [physical_ramp_branches.py:130](../../evaluation/controllers/physical_ramp_branches.py#L130), [physical_ramp_branches.py:142](../../evaluation/controllers/physical_ramp_branches.py#L142), [area_meter_finalization.py:132](../../evaluation/controllers/area_meter_finalization.py#L132)

**service_and_open**: [vissim_stackelberg_adapter.py:10452](../../evaluation/controllers/vissim_stackelberg_adapter.py#L10452), [vissim_stackelberg_adapter.py:10520](../../evaluation/controllers/vissim_stackelberg_adapter.py#L10520), [vissim_stackelberg_adapter.py:10524](../../evaluation/controllers/vissim_stackelberg_adapter.py#L10524), [physical_ramp_branches.py:73](../../evaluation/controllers/physical_ramp_branches.py#L73), [area_freeway_accounting.py:62](../../evaluation/controllers/area_freeway_accounting.py#L62)

**fixed_green_box**: [topology_routes_v2.json:35](../control_improvement/decision_common_anchor_20260911/ramp8_physical_v1/topology_routes_v2.json#L35), [physical_ramp_branches.py:327](../../evaluation/controllers/physical_ramp_branches.py#L327), [joint_owner_neighbors.py:1032](../../evaluation/controllers/joint_owner_neighbors.py#L1032), [joint_owner_game.py:785](../../evaluation/controllers/joint_owner_game.py#L785), [area_follower_objective.py:501](../../evaluation/controllers/area_follower_objective.py#L501)

**nuf**: [area_follower_objective.py:1301](../../evaluation/controllers/area_follower_objective.py#L1301), [area_leader_objective.py:730](../../evaluation/controllers/area_leader_objective.py#L730), [area_leader_objective.py:783](../../evaluation/controllers/area_leader_objective.py#L783), [config.json:7671](history_lever_sources/diagnostics/selected_control_demand/codex_fid_cl9000_s13_v3/config.json#L7671), [config.json:8102](history_lever_sources/diagnostics/selected_control_demand/codex_fid_cl9000_s13_v3/config.json#L8102)

**finite_game**: [joint_owner_game.py:44](../../evaluation/controllers/joint_owner_game.py#L44), [joint_owner_game.py:785](../../evaluation/controllers/joint_owner_game.py#L785), [joint_owner_game.py:808](../../evaluation/controllers/joint_owner_game.py#L808), [joint_owner_game.py:821](../../evaluation/controllers/joint_owner_game.py#L821), [joint_owner_game.py:879](../../evaluation/controllers/joint_owner_game.py#L879), [joint_owner_neighbors.py:108](../../evaluation/controllers/joint_owner_neighbors.py#L108), [area_follower_objective.py:2064](../../evaluation/controllers/area_follower_objective.py#L2064)

**fd_merge**: [vissim_stackelberg_adapter.py:8771](../../evaluation/controllers/vissim_stackelberg_adapter.py#L8771), [freeway_fd.py:66](../../evaluation/controllers/freeway_fd.py#L66), [freeway_fd.py:97](../../evaluation/controllers/freeway_fd.py#L97), [area_freeway_accounting.py:314](../../evaluation/controllers/area_freeway_accounting.py#L314), [evaluation\runs\codex_selected_fw070_u040_beta0_r02\decisions_codex_selected_fw070_u040_beta0_r02\action_000900.json:1407](history_lever_sources/evaluation/runs/codex_selected_fw070_u040_beta0_r02/decisions_codex_selected_fw070_u040_beta0_r02/action_000900.json#L1407), [evaluation\runs\codex_selected_fw070_u040_beta0_r02\decisions_codex_selected_fw070_u040_beta0_r02\action_000900.json:1428](history_lever_sources/evaluation/runs/codex_selected_fw070_u040_beta0_r02/decisions_codex_selected_fw070_u040_beta0_r02/action_000900.json#L1428), [evaluation\runs\codex_fid_cl9000_s13_v3\decisions_codex_fid_cl9000_s13_v3\action_000900.json:932](history_lever_sources/evaluation/runs/codex_fid_cl9000_s13_v3/decisions_codex_fid_cl9000_s13_v3/action_000900.json#L932), [evaluation\runs\codex_fid_cl9000_s13_v3\decisions_codex_fid_cl9000_s13_v3\action_000900.json:953](history_lever_sources/evaluation/runs/codex_fid_cl9000_s13_v3/decisions_codex_fid_cl9000_s13_v3/action_000900.json#L953)

**score_writer**: [area_meter_finalization.py:121](../../evaluation/controllers/area_meter_finalization.py#L121), [area_meter_finalization.py:176](../../evaluation/controllers/area_meter_finalization.py#L176)

기존2400초 검토: [lever_rejections.json](lever_rejections.json), [summary.json](lever_counterfactual2400/summary.json), [summary.json](lever_counterfactual2400/meter_g8_attempt01/summary.json), [meter_trace_summary.json](lever_counterfactual2400/meter_trace_summary.json)

다음 검증은 사용자 방향을 받은 뒤 같은 상태·수요에서 도시 명령 변화의 차이를 비교하고, 실제 병목의 미터 재고·서비스와 native RG 펄스 반응을 분리하는 것이 적절하다. 미터를 켜기 위해 수용량·N_UF를 임의 조정하는 것은 원인 검증이 아니다.

인계용 원본 사본과 직접 참조 위치는 [소스 manifest](history_lever_sources/manifest.json)에 있다. 본문 링크는 GitHub와 새 PC에서도 열리도록 바꿨으며, 원본 데이터와 소스는 수정하지 않았다.
