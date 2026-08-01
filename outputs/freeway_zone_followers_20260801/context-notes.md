# 4-zone freeway follower 컨텍스트 노트 (2026-08-01)

구현 중 내린 결정과 근거. 다음 세션이 재유도하지 않도록 이유까지 적는다.

## 1. 단일 경로 일반화 + 골든 회귀 (이중 경로 복제 기각)

`_solve_freeway_segment_agents`는 METER-BOX/VSL-BOX/회랑 예산/spillback 하한/보호큐 벌점이
층층이 쌓인 실측 휴리스틱 덩어리다. `_solve_freeway_zone_agents`를 따로 만들면 반드시
드리프트한다. 대신 데이터 모델(`SegmentAgentModel.segs`)만 분기하고 솔버 본문에는
`if groups` 분기를 두지 않았다. `segs=[i]`면 산술 경로가 기존과 완전히 같다.

검증은 코드 리뷰가 아니라 골든 스냅샷으로 했다. 리팩터 **전** 커밋(HEAD 7f10393)과 **후**
작업트리에서 동일 스크립트를 돌려 `(vsl_out, meter_out, evals, _seg13_diag, _seg_traj,
_last_offramp_flow)`를 `repr` 수준으로 비교 → 4 케이스 × 78줄 완전 일치.

케이스 구성(모두 8-seg default.yaml, `segment_agents=True`, `metering_enabled=True`):
- A: METER-BOX 300/450 + VSL-BOX 20 + 4채널 가격 + leader(N_UF*=3200), 궤적 교환 3 iteration
- B: 박스 OFF·가격 OFF·leader None (자율 best-response), 고밀도
- C: A + `seg13_neighbor_weight=0.3` (radius-1 이웃 경로 발화)
- D: 박스 OFF + 가격 ON + leader, 포화 상태

가격 g_vsl은 세그먼트마다 부호를 뒤집어 per-segment VSL 분기가 실제로 출력에 나오게
했다(초기 버전은 전 세그먼트 동일값이 나와 판별력이 없었다).

부동소수 결합순서 보존 규약:
- own-TTS 누적은 여전히 **한 개의 `cost += (…) * dt_h`**. 세그먼트별로 쪼개지 않았다.
- 집계는 전부 `sum(iterable)`. Python `sum([x]) == 0.0 + x == x`(IEEE754 정확)라
  단일 원소에서 항등이다. `math.fsum`·정렬 합산으로 바꾸지 않았다.
- 후보 열거 순서 고정: v 바깥 루프, m 안쪽 루프, m은 `sorted(..., reverse=True)`.
  `itertools.product`는 ramp가 1개면 원래 `m_cands` 순서를 그대로 낸다 → argmin의
  strict `<` tie-break가 보존된다.
- 에이전트 순회는 세그먼트 오름차순(zone 순서도 빌더가 오름차순 강제).
- `preferred_meter` 삽입 순서 = 에이전트 순회 순서 유지(`_scale_to`의 `sorted(..., key=)`가
  동점에서 dict 순서로 갈리므로).

## 2. 해석이 갈렸던 지점의 확정

| 지점 | 확정 | 이유 |
|---|---|---|
| VSL 후보 앵커 | `min(직전 VSL over zone segs)` | 보수적 — 상향 폭을 과대허용하지 않음. 평균/최빈은 `vsl_set` 격자 위에 없는 값이 앵커가 될 수 있어 기각. 단일 세그먼트면 그 값 자체라 비트 동일 |
| VSL 마찰 | `w · Σ_{s∈zone} \|v − prev_v[s]\|` | zone당 1회만 부과하면 8-seg 링크 총 마찰이 1/4로 줄어 VSL이 과민해진다. 합산이어야 zone 경계를 재지정해도 마찰 강도가 안 흔들린다 |
| g_vsl 가격 | 소유 세그먼트 **합** | 가격 키는 세그먼트 해상도(`stackelberg_wu_metered.py` op_vsl 생성). zone 균일 v에 대한 방향미분 = 소유 세그먼트 편미분의 합. 대표 1개만 읽으면 나머지 leader 신호가 통째로 유실 |
| 이웃 정의 | `{min(segs)−1, max(segs)+1} \ segs` | 물리 결합은 세그먼트 경계에서 일어난다. zone 내부를 이웃으로 잡으면 own-TTS가 가중치 1.0과 w_nbr로 이중계상. 이 정의가 성립하려면 zone이 연속이어야 해서 빌더가 연속성을 강제 |
| origin queue | seg0 소유 zone에서 **1회만** | `SegmentLocalState.origin_queue`는 스칼라. zone 내 여러 세그먼트에 실으면 중복 |
| h 교차항의 v | zone 균일 v 그대로 | 가격 h는 ramp별로 선형화되고 v_ref는 merge 세그먼트 기준. 빌더가 merge 세그먼트를 zone 소유로 보장하므로 타당. zone이 커질수록 정합이 느슨해지는 건 알려진 근사 |
| 가격층(leader) | **무변경** | 세그먼트 해상도 유지. zone화하면 leader FD 측정 대상이 바뀌어 flagship 재현성에 직접 영향 |
| 예산 사영 | **무변경** | 사영 스코프는 링크(ω_F는 링크별 몫). 코드가 이미 일반 n명(dict comprehension + 정렬 재분배). zone이 소유 ramp를 전부 `preferred_meter`에 넣기만 하면 성립 |

## 3. `owned_ramps[0]` 절삭 제거

기존 코드는 에이전트당 ramp 1개를 강제 가정했다(`agent.owned_ramps[0]`). 현행 배치에서는
링크당 2 ramp가 서로 다른 merge 세그먼트라 발화하지 않았지만, zone이 2 ramp를 품으면 둘째
ramp가 `preferred_meter`에서 조용히 빠져 사영을 우회한다(Σmeter가 예산 초과 = 조용한 제약
위반). 소비 지점(후보 격자·`_local_ramp_release`·큐 적재·blocked 회계·보호큐 벌점·
g_meter/h/λ_UF·궤적 교환 release)을 전부 ramp 루프로 일반화했다.

복수 ramp zone의 후보 공간은 `itertools.product`(곱집합, |m|^k)로 처리한다. 4-zone 배치는
zone당 ramp가 정확히 1개(R_F_E@seg3, R_D_E@seg7, R_D_W@seg3, R_F_W@seg6)라 곱집합이
발생하지 않는다. k≥3이면 폭발하므로 그때는 좌표하강이 필요하다 — 지금 넣지 않았다.

방어망으로 사영 직전에 `set(preferred_meter) == set(link_model.owned_ramps)`를 검사하고
불일치면 RuntimeError(zone 모드에서만 — 기본 경로 거동 불변).

## 4. 침묵 무효화 방지 (BUDGET_OFF 20런 사고 재발 패턴)

- `freeway_agent_groups`가 설정됐는데 `segment_agents`/`metering_enabled`가 꺼져 있으면
  `_solve_followers` 진입부에서 RuntimeError. seg13 박스 키의 기존 규약과 동일.
- 파티션이 링크 세그먼트를 전수·비중복·연속으로 덮지 않으면 빌더에서 RuntimeError.
  이게 없으면 `vsl_out[link] = min(...)`이 누락 키를 `vsl_max`로 채우고(조용히 틀린 대표값),
  궤적 교환 게이트 `len == n_seg`가 그냥 교환을 건너뛴다 — 둘 다 예외 없이 다른 결과를 낸다.

## 5. SUP_PFO 상호작용 (plan.md의 미해결 3번 확정)

`vissim_stackelberg_adapter.py`의 SUP_PFO는 `WuFaithfulFollower(sup_cfg)`를 새로 만든다 —
`segment_agents`는 기본 False(링크 모드)다. `sup_cfg`에 groups가 남아 있으면 위 4번 가드에
걸려 즉사한다. seg13 박스 키를 None으로 되돌리는 기존 블록에 `freeway_agent_groups = None`을
추가했다. plan.md L88("PFO 에뮬레이션은 링크 모드라 zone 구조 미적용")과 정합이고,
**코드상 자동 배제 경로는 없었다**(가드가 없으면 조용히 무시됐을 자리).

## 6. (해결됨 — 아래 §8~§13 참조) 발견: zone VSL이 VISSIM 액추에이터에 도달하지 않는다

zone4 스모크에서 확인한 것 — tuning 체인
(`real_world_modi_pstack_vsl_rollout_unmasked_20260725`)이
`actuation.vsl_segment_override_policy = "clear_when_mask_disabled"`이고 mask가 disabled라
`apply_actuation_guards_to_control`이 action의 `{link}__seg{i}` 키를 **전부 지운다**
(metadata `vsl_segment_overrides_cleared: 16.0`). 그 위에
`real_world_modi_pstack_vsl_rollout_consensus_20260725`의 `finalize_agent_consensus: true`가
링크 대표 VSL을 agent consensus의 min으로 덮어쓴다.

결과: 컨트롤러는 zone별로 VSL을 4개 정하지만 VISSIM DSD에 나가는 값은 링크당 1개다.
metering은 ramp 단위라 영향 없다. 즉 **현재 zone4 tuning의 VSL 해상도 이득은 0**이고,
zone 효과는 own-TTS 회계·가격 합산·metering 결정 경로로만 나타난다.

건드리지 않은 이유: 이 정책은 flagship이 캘리브레이션된 조건이라 바꾸면 zone 효과와
액추에이터 정책 변화가 뒤섞여 A/B가 무의미해진다. 켜려면 zone4 tuning에
`actuation.vsl_segment_override_policy: "keep"`(또는 mask 활성화) + consensus finalize 해제를
넣고, **flagship 쪽에도 같은 정책의 대조군**을 따로 만들어야 한다.

## 7. 검증 명령

```
# 골든 비트 동일(리팩터 전/후) — 스크래치패드 스크립트, 저장소 밖
"C:/Users/alsrj/anaconda3/python.exe" seg13_golden.py after.txt
git stash && "C:/Users/alsrj/anaconda3/python.exe" seg13_golden.py before.txt && git stash pop
diff before.txt after.txt        # → 무차이

# 기능 테스트
cd VISSIM && "C:/Users/alsrj/anaconda3/python.exe" scripts/test_freeway_zone_followers.py   # 5/5 PASS
cd VISSIM && "C:/Users/alsrj/anaconda3/python.exe" scripts/test_pstack_flagship_adapter.py  # 4/4 PASS
# 초점 서브셋(실행함): 3 failed, 24 passed, 2 skipped — 3건 모두 변경 전에도 실패(사전 실패)
cd NumSim-mine && "C:/Users/alsrj/anaconda3/python.exe" -m pytest \
    src/tests/test_segment_local_plant.py src/tests/test_wu_faithful_follower.py \
    src/tests/test_nuf_dual.py src/tests/test_nuf_cap_mode.py \
    src/tests/test_b3_b4_price_channels.py -q

# 전수 스위트(미완): 50분+ 소요라 이번 세션에서 완료하지 못했다. 재실행 필요.
cd NumSim-mine && "C:/Users/alsrj/anaconda3/python.exe" -m pytest src/tests/ -q --ignore=src/tests/test_rl_ddqn.py
```

사전 실패 3건(변경 전 HEAD 7f10393에서도 동일):
- `test_segment_local_plant.py::TestSegmentCouplingResponsiveness::test_neighbor_ramp_release_in_y_moves_own_outflow`
- `test_segment_local_plant.py::TestSegmentCouplingResponsiveness::test_own_metering_displaced_when_receiving_bound`
- `test_wu_faithful_follower.py::TestLambdaDualIntegralUpdate::test_commit_green_equals_last_consensus_sweep`

`src/tests/test_rl_ddqn.py`는 `torch` 미설치로 collection 에러(환경 문제, 변경과 무관).

---

# 2026-08-01 2차: 적대 검증 확정 결함 수정

아래는 적대 검증(실측 재현)에서 확정된 결함에 대한 수정과 그 근거다. §1~§7은 1차 세션의
기록이며, 상충하는 부분은 이 절이 우선한다.

## 8. [차단] 세그먼트 VSL이 액추에이터에 도달하지 않던 문제 — actuation 정책 분리

**실측 진단**: zone4 tuning이 상속하는 체인
(`real_world_modi_pstack_vsl_rollout_unmasked_20260725`)의
`actuation.vsl_segment_override_policy="clear_when_mask_disabled"` + `active_lever_mask.enabled=false`
조합이 `apply_actuation_guards_to_control`(`vissim_stackelberg_adapter.py:2683-2690`)에서
`control.vsl`의 `{link}__seg{i}` 키 16개를 전부 삭제했다
(`metadata.vsl_segment_overrides_cleared=16.0`). 결과적으로 zone4와 flagship의 action 값이
완전히 같았다.

**수정**: 정책만 되돌린 **대조군 tuning**
`evaluation/configs/real_world_modi_pstack_flagship_segvsl_20260801.json`을 신설했다
(`actuation.vsl_segment_override_policy: "keep"`). zone4는 flagship이 아니라 이 대조군을
상속한다 — 그래야 zone4 ↔ 대조군의 차이가 `freeway_agent_groups` **하나**로 좁혀져
정책 변화와 zone 효과가 분리된다.

`keep`을 고른 이유(mask 활성화 + `allowed_vsl_segments` 전개를 기각한 이유):
- 정책이 `{clear_all, clear_when_mask_disabled}`에 없으면 clear 분기가 통째로 no-op다.
  액추에이터 코드 변경이 0이고, 부작용 표면이 가장 작다.
- mask를 켜면 `allowed_vsl_segments`에 없는 세그먼트를 `vsl_max`로 **강제 상향**하는
  별개 경로(L2703)가 켜진다. 16개를 전부 나열해 무력화할 수는 있지만, 그건 "무해한
  mask"를 유지하는 코스트만 늘리고 세그먼트 목록이 zone 경계 재지정 때마다 따라다닌다.

`finalize_agent_consensus`(consensus 체인)는 건드리지 않았다 — 실측상 pstack-flagship에서는
휴면이다. 그 패치는 `DistributedCoordinator.solve`를 감싸는데 flagship 경로는
`F1StackelbergWuMeteredController`/`WuFaithfulFollower`를 쓴다. 만약 발화했다면 세그먼트
키가 그 시점에 이미 지워져 `vsl_segment_overrides_cleared`가 0이었을 것이다(실측 16).
불필요한 키를 추가하지 않는다는 원칙에 따라 보류했다.

**실측 확인**(테스트 스모크 결정 1회, 동일 state):

| tuning | metadata.vsl_segment_overrides_cleared | action csv kind=vsl 고유 speed |
|---|---|---|
| flagship (미변경) | 16.0 | {100} (링크 대표값 1개) |
| segvsl 대조군 | 없음 | {100, 120} (S1만 100) |
| zone4 | 없음 | {120} |

flagship과 segvsl은 컨트롤러 결정이 동일하다(`flagship_sup_v_pstack` 등 일치). 차이는
액추에이터 정책뿐 — 대조군으로서 정확히 원하는 성질이다.

zone4 tuning의 notes에서 사실과 달랐던 문장을 고쳤다:
- "zone 내부는 균일 VSL(1차원 탐색)이다" → 세그먼트별 VSL + 좌표하강(§9)
- "zone당 램프가 1개라 예산 simplex 사영 참가자 수는 링크당 2로 flagship과 동일" →
  참가자 **집합**이 링크 소유 ramp 전체와 일치한다는 표현으로 교정(불변조건 3 정정, §13)
- 진단 키 이름을 link 네임스페이스 반영본으로 갱신

## 9. [중대 1] zone 균일 VSL → 세그먼트별 VSL + 좌표하강

**사용자 결정**: zone은 에이전트 단위(own-TTS 회계·예산 사영·가격 집계)로 유지하되
VSL은 소유 세그먼트별로 따로 정한다. 균일 VSL이 16개 중 9개 세그먼트를 개별 최적과
반대로 무제어(120) 쪽으로 뒤집었고 merge 병목 2개가 모두 거기 포함됐다(원인: origin
queue를 가진 seg0이 zone 전체를 끈다).

**구현**(`wu_faithful_follower.py::_solve_freeway_segment_agents`):
- 후보 채점 본문을 `_score(v_by_seg, m_map)` 클로저로 뽑았다. 본문은 기존 균일-VSL
  열거의 본문 **그대로**이고, `v_cand` 참조만 `v_by_seg[s]`로 바뀌었다. 균일 입력을 주면
  연산이 한 개씩 대응한다.
- 후보 격자·마찰 기준·앵커를 전부 세그먼트별로 만들었다(`v_cands_by_seg`,
  `v_anchor_by_seg`). 기존 zone 앵커는 `min(직전 VSL over zone segs)`였는데, 세그먼트별
  결정에서는 그 세그먼트 자신의 직전 VSL이 앵커다. 단일 세그먼트면 두 정의가 같다.
- **`len(segs)==1`이면 기존 열거 경로를 그대로 탄다**(좌표하강 진입 금지).
  `for v_cand in v_cands: for m_map in m_combos:` 순서와 strict `<` tie-break가 그대로라
  비트 동일이 구조적으로 보장된다. `len(segs)>1`에서만 좌표하강.
- 좌표하강 규약(저장소의 `_solve_freeway_agent_metered` PFO 분기 규약을 따름):
  1. 앵커에서 시작. 앵커가 후보 격자에 없으면 격자 첫 원소(Gauss-Seidel 초기점 관행).
  2. 초기점에서 `m_combos` 전수 열거로 첫 incumbent 확정.
  3. 세그먼트 **오름차순** 순회. 각 세그먼트에서 나머지 VSL 고정, 그 세그먼트의 후보 ×
     `m_combos`를 훑는다. incumbent와 동일한 (v_s, m)은 재채점하지 않는다.
  4. 한 sweep에서 incumbent가 안 바뀌면 수렴 종료. 아니면 `mpc.freeway_zone_vsl_max_sweeps`
     (기본 3)까지 반복.
- metering 결합: 좌표 스텝마다 `m_combos`를 함께 훑어 기존 (v,m) 공동 열거 규약을
  보존했다. v와 m이 동시에 움직여야 하는 레짐 전환을 좌표하강이 놓치지 않는다.
- 가격 항: g_vsl은 소유 세그먼트별 `g_vsl[s]·(v_s − ref[s])`의 합(기존과 동일 형태이나
  이제 v가 세그먼트마다 다르다). 마찰도 `Σ_s w·|v_s − prev_v[s]|`.
- h 교차가격의 v: zone 균일 v 대신 **그 ramp의 merge 세그먼트 VSL**
  (`v_by_seg[link_model.ramp_merge_idx[r]]`)을 쓴다. v_ref가 merge 세그먼트 기준으로
  선형화된 값이라 이쪽이 정합적이고, 단일 세그먼트면 자기 자신이라 기존과 동일하다.
- 진단: `wu_zone_cd_sweeps_{link}_{zid}`(sweep 수), `wu_zone_cd_converged_{link}_{zid}`
  (수렴 1 / 상한 도달 0), `wu_zone_vsl_{link}_{zid}`(zone 최소), `wu_zone_vsl_max_{...}`.

**비용**: zone당 평가수가 `len(segs) × |v_cands| × |m_combos| × sweep` 규모로 늘어난다.
합성 프로브(8-seg, zone당 4~6 세그먼트)에서 2 sweep 수렴을 확인했다. wall-time 영향이
문제가 되면 `freeway_zone_vsl_max_sweeps`를 낮춘다.

## 10. [중대 2] 알 수 없는 링크 키 침묵 무효화 → RuntimeError

`_normalize_zone_groups`가 `raw.get(link)`만 봐서, `raw`의 키가 `cfg.network.freeway_links`에
없어도 조용히 None을 반환했다. 오타 하나로 zone4 런 전체가 flagship으로 퇴화하고
영수증도 남지 않는다(BUDGET_OFF 20런 사고와 동일 패턴).

수정: `build_segment_agent_models`가 `cfg.network.freeway_links`를 넘기고,
`unknown = set(raw) - set(valid_links)`가 비어 있지 않으면 RuntimeError. **링크 부분 지정**
(FW_E만 zone화)은 계속 허용된다 — 미지정 링크는 세그먼트당 1 에이전트로 남는다.
검사 대상은 "raw의 모든 키가 실재 링크인가"이지 "모든 링크가 raw에 있는가"가 아니다.

테스트: `test_partition_guards`의 "알 수 없는 링크"/"알 수 없는 링크(유효 키 동반)"가
RuntimeError를 단언하고, 부분 지정 허용은 **유효한 링크 이름**(`{FW_E: ...}`로 `FW_W`를
빌드)으로 따로 검증한다. 이전 테스트(L234-238)는 이 침묵을 정답으로 단언하고 있었다.

## 11. [중대 3] 다중 ramp 일반화를 zone 경로로 게이트

1차 세션이 `own_ramp = agent.owned_ramps[0]` 절삭을 제거하면서 `own_ramps =
list(agent.owned_ramps)`를 **groups=None에서도 무조건** 적용했다. 한 세그먼트에 ramp 2개가
merge하는 구성에서 거동이 바뀐다(검증자 재현: meter `{R_D_W:1100}` → `{R_D_W:550,
R_F_W:550}`, evals 46→126). `NetworkConfig` 데이터클래스 기본 `ramp_merge_segment_index`가
정확히 그 위험 구성이다(4 ramp 전부 seg2). `src/config/default.yaml`은 3/5로 갈라져 있어서
1차 세션의 골든 회귀가 이 경로를 밟지 못했다.

수정: `own_ramps = list(agent.owned_ramps) if zone_mode else agent.owned_ramps[:1]`.
기본 경로는 기존 절삭을 유지하고, 다중 ramp 일반화는 zone 경로에서만 발화한다.

회귀 테스트 2종:
- 골든 스냅샷에 케이스 E/F 추가 — `ramp_merge_segment_index`를 전부 같은 세그먼트로
  바꾼 구성. HEAD 7f10393 대비 비트 동일(meter `{R_D_W: ...}` 1개, evals 48).
- `test_freeway_zone_followers.py::multi_ramp_gating` — 같은 구성에서 groups 미지정이면
  meter 키 1개, zone 지정이면 소유 ramp 2개 전부 + evals 증가를 단언.

## 12. [부수] 처리 내역

- **zone_mode 판정**: `any(len(a.segs) > 1)` 휴리스틱을 버리고 빌더가 명시적으로 채우는
  `SegmentAgentModel.zone_mode`로 바꿨다. 전부 단일 세그먼트인 zone 지정에서 영수증
  (`wu_zone_count_*`)과 안전망(사영 스코프 검사)이 꺼지던 false-negative를 제거한다.
  테스트 `single_segment_zone_parity`가 (a) 결정이 기본 경로와 동일, (b) 영수증은 켜짐,
  (c) 좌표하강 sweep=0을 동시에 단언한다.
- **zone_id 링크 내 중복**: RuntimeError. 진단 키가 서로를 덮어쓰는 걸 막는다.
- **진단 키 link 네임스페이스화**: `wu_zone_vsl_{zid}` → `wu_zone_vsl_{link}_{zid}`
  (cong/cd_sweeps/cd_converged/vsl_max 동일). zone_id가 링크 간 겹쳐도 안전하다.
- **세그먼트 인덱스 정수성 검사**: `int(s)`가 3.7을 3으로 조용히 절삭하던 것을
  `_as_segment_index`로 교체 — 정수가 아니면 RuntimeError. JSON이 정수를 float으로
  싣는 경우(3.0)는 허용한다. 테스트에 3.7·문자열·정수 float 케이스를 모두 넣었다.
- **테스트 `_run_adapter` 프로덕션 매핑**: `--mapping-json
  evaluation/real_world_modi_control/control_mapping.json`, `--calibration-json
  evaluation/calibration/real_world_modi_control_v0_20260719.json`을 넘긴다. `_build_cfg`도
  같은 캘리브레이션을 쓰도록 맞췄다(어댑터 기본값은 8seg 진단용이라 실행 경로와 다르다).
- **회귀 방지 검사 추가**: `_segment_vsl_actuation_checks` — action json에 세그먼트 VSL
  키 16개가 살아 있는지, `metadata.vsl_segment_overrides_cleared`가 없는지, csv kind=vsl
  고유 speed 수가 결정 단위 수 이내인지. 반대로 `no_zone_regression`은 flagship에서
  `vsl_segment_overrides_cleared > 0`을 단언해 대조군 설계의 전제를 고정한다.
  (이전 테스트는 zone4/flagship 행 지문 동일성만 봐서 차단 결함을 못 잡았다.)

## 13. [부수] plan.md 불변조건 3 정정

"Σmeter = ω_F·N_UF* 등식의 simplex 사영이 zone 단위에서도 성립" → **틀린 문구**였다.
이 등식은 zone4에서도 flagship에서도 성립하지 않는다.
- `_scale_to`의 `target = min(max(target, Σ_rl_lo), Σ_rl_hi)` — METER-BOX 회랑이 예산을
  담지 못하면 **예산이 양보한다**(박스=하드, 설계된 거동).
- spillback 하한이 회랑 lo에 합류하므로 하한이 예산을 밀어낼 수 있다.
- `seg13_budget_inequality` 분기는 애초에 등식이 아니라 α·budget ≤ Σ ≤ budget이다.

지켜야 하는 것은 **사영 참가자 집합과 스코프가 링크 소유 ramp 전체와 일치**하는 것이고,
솔버가 zone 모드에서 `set(preferred_meter) == set(link_model.owned_ramps)`로 강제한다.
테스트 `budget_projection_scope`가 N_UF_star>0인 가짜 leader(ω_F=0.5)로 flagship/zone4
양쪽에서 사영 참가자 집합과 영수증 키를 단언한다. 등식은 단언하지 않는다.

## 14. 2차 검증 결과

```
# 골든 비트 동일 — HEAD 7f10393 vs 작업트리, 6 케이스 × 102줄 완전 일치
"C:/Users/alsrj/anaconda3/python.exe" seg13_golden.py after.txt
git stash push -- src/controllers/wu_faithful_follower.py \
    src/controllers/segment_local_plant.py src/models/state.py
"C:/Users/alsrj/anaconda3/python.exe" seg13_golden.py before.txt
git stash pop
diff before.txt after.txt        # → 무차이

cd VISSIM && "C:/Users/alsrj/anaconda3/python.exe" scripts/test_freeway_zone_followers.py   # 9/9 PASS
cd VISSIM && "C:/Users/alsrj/anaconda3/python.exe" scripts/test_pstack_flagship_adapter.py  # 4/4 PASS
```

골든 케이스(1차의 A~D + 2차 신규 E/F):
- A: METER-BOX 300/450 + VSL-BOX 20 + 4채널 가격 + leader(N_UF*=3200), 궤적 교환 3 iteration
- B: 박스 OFF·가격 OFF·leader None (자율 best-response), 고밀도
- C: A + `seg13_neighbor_weight=0.3` (radius-1 이웃 경로 발화)
- D: 박스 OFF + 가격 ON + leader, 포화 상태
- **E: 한 세그먼트에 ramp 2개**(`ramp_merge_segment_index` 전부 3) + 박스·가격 ON + leader
- **F: E와 같은 구성 + 박스·가격 OFF + leader None**

E/F가 [중대 3]의 위험 구성을 직접 밟는다. 1차 세션의 A~D는 `default.yaml`이 merge
세그먼트를 3/5로 갈라놔서 이 경로를 못 밟았다 — 골든이 "구성 의존적"이었던 이유다.

미실행(이번 세션에서도 완료 못 함): NumSim 전수 pytest 스위트(50분+). 재실행 필요.

## 15. VSL 타이브레이크 규약 정합(P1) · 예측-플랜트 vsl 배선(P2) — 2026-08-01

근거 문서: `outputs/vsl_sensitivity_20260801.md` §1-3(C1/C2), §6(P1/P2), §7-1. 결과는 같은 문서 §9에 기록했다.
**P3~P6은 손대지 않았다**(사용자 결정 대기).

### 15-1. 왜 zone4 A/B가 무효였나 (§7-1 재확인)

두 경로의 동률 처리가 서로 달랐다.

| 경로 | 초기값 | 동률 시 결과 |
|---|---|---|
| 단일 세그먼트 열거 | `best_cost = inf` → 첫 후보 무조건 채택 | vsl_set 오름차순이라 **최저 VSL** |
| zone 좌표하강 | `_cur_v` = 앵커(previous/snapshot) | **앵커 유지** |

`V_eff = min(V(ρ), VSL)`이라 ρ_bind(80)=25.84 위에서는 메뉴 전 rung이 비구속 → 궤적이 **비트 동일** →
cost 차이가 정확히 0. 그래서 ρ≳26에서 나오던 VSL 차이는 zone 구조 효과가 아니라 tie-break 규약 차이였다.
실측으로 15셀 중 11셀이 불일치했다.

### 15-2. 무엇을 고쳤나

`wu_faithful_follower.py` 모듈 수준에 `_vsl_no_control_key`(소유 세그먼트 VSL 합) /
`_vsl_candidate_better`를 두고, `_solve_freeway_segment_agents` 안에 공용 클로저 `_accept()`를 만들어
후보 갱신 **3곳**(단일 세그먼트 열거 1 + zone 좌표하강 초기화 1 + zone sweep 1)을 전부 이걸로 통일했다.
세 곳이 같은 함수를 부르므로 **규약이 갈라질 수 없다** — 이게 이번 수정의 핵심이다(값 한 개를 바꾼 게 아니다).

핵심 설계 결정 3개.

1. **무제어 근접도 = VSL 합.** 좌표하강은 한 번에 한 좌표만 바꾸므로 합 비교가 "그 좌표에서 더 높은 VSL"과
   정확히 일치하고, 단일 세그먼트에서는 VSL 값 자체와 같다. 별도 규약 없이 두 경로가 자동으로 맞는다.
2. **동률 + 근접도 동률 = 기각.** 그래야 먼저 열거된 후보가 남고, `m_list`가 내림차순(전량 방류 우선)이므로
   **metering 축의 무개입 우선이 보존**된다. 만약 `>=`로 받았다면 VSL 동률 상태에서 m이 낮은 쪽으로
   흘러 metering 규약을 깨뜨렸을 것이다. 실제로 이게 가장 위험한 함정이었다.
3. **동률 채택 시 앵커는 `min(best_cost, cost)`.** 채택 후보의 비용을 그대로 앵커로 쓰면 ε 동률 채택이
   연쇄될 때 앵커가 계속 위로 밀려 순서 의존이 생긴다.

ε는 상대 1e-12 + 절대 1e-12. 근거는 두 방향에서 잡았다 — (하한) 비구속 동률은 원리상 cost 차이가 **정확히 0**
이라 ε=0으로도 되지만 합산 순서 차이의 마지막 자리 반올림 여유를 뒀다. (상한) 진단이 측정한 **진짜** spread 중
최소가 ρ=45의 5e-5 상대이므로 1e-12는 7자리 아래다 — 물리 감도를 삼킬 수 없다. 절대항은 가격항 상쇄로
cost가 0 근처일 때 상대 허용오차가 붕괴하는 것을 막는 방어다.

게이팅은 `cfg.mpc.vsl_tie_prefer_no_control`, **기본 False**. real-world는
`real_world_modi_pstack_flagship_segvsl_20260801.json`에만 `config_overrides.mpc`로 걸었고 zone4가 상속한다.
부모 flagship(`..._flagship_20260731.json`)·`default.yaml`·`work/run_job.sh`는 미변경.

P2는 `local_freeway_plant.py`의 `select_anticipation_nu(rho, net)` → `(rho, net, vsl_i)` 한 줄이다.
§6이 적은 L623은 실제로 **L304**였다(grep 재특정). `capacity_drop_anticipation=False`라 정의상 no-op이지만
P3를 켜는 순간 follower만 ν 전환 회피 이득을 못 보는 비정합이 되므로 지금 넣는 게 무비용이다.

### 15-3. 검증

플래그 OFF 비트 동일을 **수정 전 실측 골든**으로 잡았다(`seg13_golden.py`는 이번 세션 시작 시점에 없었다).

- 수정 전에 `diagnose_vsl_channel_20260801.py tiebreak`를 먼저 돌려 15셀 + 래칫 궤적을 기록.
- 수정 후 플래그 OFF로 같은 셀을 재측정 → 단일 세그먼트 6셀(VSL·metering·evals) + zone 15셀(VSL·evals) 전부 일치.
- 래칫 궤적 `[120,100,80,80,80,80]`도 OFF에서 그대로 재현된다. **래칫은 버그지만 플래그 OFF에서는
  보존돼야 하는 기존 거동**이라 이걸 테스트로 박았다(테스트 10).

래칫 해소 실측(ρ=35 고정, seg3, previous=직전 결정).

```
전(OFF): flagship 120 -> 100 -> 80 -> 80 -> 80 -> 80
         zone4    120 -> 120 -> 120 -> 120 -> 120 -> 120   (규약 불일치)
후(ON) : flagship 120 -> 120 -> 120 -> 120 -> 120 -> 120
         zone4    120 -> 120 -> 120 -> 120 -> 120 -> 120   (일치)
```

경로 일치 셀 수: 4/15 → **15/15**. 자유류 ρ=12는 전후 불변(엄격 우열 구간이라 tie-break 미개입).
비용은 zone 좌표하강 evals 206 → 234(+13.6%), 단일 세그먼트는 불변.

테스트 5개 추가(`scripts/test_freeway_zone_followers.py` 10~14) — 9/9 → **14/14 PASS**.
`test_pstack_flagship_adapter.py` 4/4 PASS.
테스트 13은 "OFF에서 두 경로가 **달라야 한다**"는 음성 대조를 함께 단언한다. 이게 없으면 두 경로가
원래부터 같았을 때 ON 단언이 아무것도 증명하지 못한 채 통과한다.

### 15-4. 이 변경이 zone4 작업에 갖는 의미

§7-2의 **1단계 완료**다. 이제 zone4 A/B에서 VSL 채널의 교란 변수(tie-break 규약 차이)가 제거됐다.
다만 P1은 **이득을 만들지 않는다** — 근거 없는 개입을 없앨 뿐이다. 현행 설정에서 VSL 이득 셀은 여전히
0건(§2-1)이므로 2단계 권고(VSL을 `[120.0]` 등으로 고정하고 metering 채널로 A/B)는 그대로 유효하다.
그리고 과거 런 로그의 `vsl_active_steps`는 **최적화 근거 없이 타이브레이크가 만든 값**이므로
과거 런과의 VSL 활성 통계 비교는 무효다.

### 15-5. 미해결 / 보류

- 비-SEG13(PFO) 경로의 VSL 후보 갱신 strict `<` 5곳(`_solve_with` 계열)은 손대지 않았다. flagship은
  SEG13만 쓰지만 PFO baseline·SUP_PFO 감독자는 옛 규약이다. 공정비교상 맞출지는 별도 결정.
- `metanet.py:680`(완충 체인)의 vsl 없는 `select_anticipation_nu` 호출 — 그 셀은 무제어 고정(`vsl=v_free`)이라
  P2 범위 밖으로 뒀다. two_branch를 켜면 재검토 대상.
- **NumSim 유닛 7건 선행 실패**(P1/P2와 무관, 이번 세션에서 원인 확인만 하고 고치지 않음).
  `test_wu_faithful_follower::test_commit_green_equals_last_consensus_sweep`,
  `test_segment_local_plant::TestSegmentCouplingResponsiveness`(2건),
  `test_constraints::ConstraintTests`(4건). 관련 6개 모듈 기준 132 passed / 7 failed / 2 skipped.
  **확인 방법** — 3개 파일을 백업하고 P1/P2 편집만 되돌려 같은 7건을 재실행 → 실패 목록·assertion 값이
  완전히 동일(`fake_freeway_substep_local() got an unexpected keyword argument 'buffer_bc'`,
  `115.0 not found in [100.0]`, `324.13735 not less than 319.2366625`, …). 이후 백업에서 복원하고
  `test_freeway_zone_followers.py` 14/14 PASS 재확인. `buffer_bc` 건은 파라미터 도입 이전의 낡은
  test double이 명백하고, 나머지는 미커밋 zone 작업(또는 그 이전)에서 온 것으로 보인다. **별도 티켓 대상**.
- NumSim 전수 pytest는 여전히 장시간 작업이다(`test_rl_ddqn`은 torch 미설치로 collection error).
  이번 세션에서 백그라운드로 착수했으나 위 revert/restore와 시간대가 겹쳐 결과를 신뢰할 수 없어 중단했다.
  깨끗한 상태에서 재실행 필요.
- 실상태(프로덕션 `control_timeseries.csv`) 기반 재검증은 산출물이 없어 못 했다(§8과 동일한 미해결).
