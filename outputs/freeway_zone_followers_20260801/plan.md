# Freeway follower 4-zone 분산화 계획 (2026-08-01)

## 목표

real-world 개포동 망의 freeway follower를 단일 플레이어에서 **IC × 방향 4-zone 분산
컨트롤러**로 바꾼다. NumSim 8-seg 수치모델의 segment agent(SEG13) 구조를 따르되,
세그먼트당 1 에이전트(full distribution)가 아니라 **IC 구역당 1 에이전트**로 거칠게 묶는다.

## 확정된 기하 (2026-08-01 좌표 검증)

`modi_eval_rw_control.inpx`의 linkPolyPoint y좌표로 확정. y가 클수록 북쪽.

| 램프 그룹 | 연결 링크 | 평균 y | 남북 | IC |
|---|---|---|---|---|
| `R_D_*` | 31, 32 | −968,895 / −968,908 | 북 | **서초IC** |
| `R_F_*` | 68, 69, 70 | −971,013 ~ −971,791 | 남 | **양재IC** |

따라서 **FW_E = 북향(양재→서초)**, **FW_W = 남향(서초→양재)**.

## 4-zone 분할 (최근접 램프 기준, 사용자 선택)

각 세그먼트 중심에서 가장 가까운 소유 램프의 IC로 배정한다.

| Follower | 본선 | 세그먼트 | 소유 램프 |
|---|---|---|---|
| `fw_yangjae_E` | FW_E (link 2) | S0~S5 | RM_C10639, RM_C10681 (`R_F_E`) |
| `fw_seocho_E` | FW_E | S6~S7 | RM_C10490, RM_C10484 (`R_D_E`) |
| `fw_seocho_W` | FW_W (link 26) | S0~S4 | RM_C10480, RM_C10482 (`R_D_W`) |
| `fw_yangjae_W` | FW_W | S5~S7 | RM_C10646, RM_C10644 (`R_F_W`) |

FW_E가 6:2로 치우친다 — D 램프가 link 2 끝단(4414/4703m / 전체 4692m)에 몰려 있기 때문.
최근접 규칙에 충실한 결과이며, 경계는 cfg로 재지정 가능하게 노출한다.

## 설계

### 현행 대비 제어 해상도

| | VSL 결정 수 | metering 결정 수 |
|---|---|---|
| 현행 real-world (단일 freeway follower) | 2 (링크당 1) | 4 그룹 |
| **본 계획 (4-zone, v2)** | **16 (세그먼트당 1, 좌표하강)** | 4 그룹 (zone당 1) |
| NumSim SEG13 full distribution | 16 (세그먼트당 1) | 세그먼트별 |

**v2 정정(2026-08-01, 사용자 결정)**: 초판의 "zone 내부 균일 VSL"은 폐기했다. 균일 VSL은
16개 세그먼트 중 9개를 개별 최적과 반대로 무제어(120) 쪽으로 뒤집었고, merge 병목 2개가
모두 거기 포함됐다(원인: origin queue를 가진 seg0이 zone 전체를 끈다). 따라서 **zone은
에이전트 단위(own-TTS 회계·예산 사영·가격 집계)로만 유지하고, VSL은 소유 세그먼트별로
따로 정한다.** 후보 폭발(`|vsl_set|^k`)은 좌표하강으로 회피한다 — 앵커에서 시작해 세그먼트를
오름차순으로 돌며 나머지를 고정한 채 한 세그먼트씩 최적화, 무변화이거나 상한 sweep까지 반복
(`mpc.freeway_zone_vsl_max_sweeps`, 기본 3). 세그먼트가 1개인 zone은 좌표하강에 진입하지
않고 기존 열거 경로를 그대로 탄다(비트 동일 보장).

### 구현 위치

핵심 변경은 **NumSim-mine**이다. VISSIM 어댑터는 이 구조를 cfg로 지시만 한다.

- `src/controllers/segment_local_plant.py`
  - `SegmentAgentModel`이 단일 `seg` 대신 **세그먼트 구간**을 소유하도록 일반화
  - `build_segment_agent_models(cfg, link)`에 그룹 정의 인자 추가
- `src/controllers/wu_faithful_follower.py`
  - `_solve_freeway_segment_agents`가 다중 세그먼트 에이전트를 처리
    (own-TTS = 소유 세그먼트 합, VSL은 소유 세그먼트별 결정 + 좌표하강)
- `src/models/state.py`
  - `mpc.freeway_agent_groups` cfg 키 신설. **기본 None = 세그먼트당 1 에이전트**
    (= 현행 SEG13 동작 비트 동일). flagship 재현성 보호가 최우선 제약이다.

### VISSIM 쪽

- tuning JSON에 4-zone 정의 주입
- `player_config`/리포트에 freeway follower 4개로 반영
- action csv 계약은 불변 (kind=vsl 세그먼트 행 16개, kind=ramp_meter 8행)
- **actuation 정책(2026-08-01 추가)**: 상속 체인의
  `actuation.vsl_segment_override_policy="clear_when_mask_disabled"` + `active_lever_mask.enabled=false`
  조합이 `apply_actuation_guards_to_control`에서 `{link}__seg{i}` 키 16개를 전부 삭제해
  세그먼트 VSL이 액추에이터에 도달하지 못했다. 그래서 정책만 `keep`으로 되돌린 대조군
  `real_world_modi_pstack_flagship_segvsl_20260801.json`을 신설하고, zone4가 그것을 상속한다.
  zone4 ↔ segvsl 차이는 zone 구조 하나뿐이라 정책 변화와 zone 효과가 분리된다.

## 불변 조건 (반드시 지킬 것)

1. `freeway_agent_groups` 미설정 시 기존 SEG13 거동과 **비트 동일**. flagship 5셀 결과가
   재현되지 않으면 실패로 본다.
2. VISSIM action csv/json 스키마 불변.
3. 예산 simplex 사영의 **참가자 집합과 스코프가 링크 소유 ramp 전체와 일치**해야 한다.
   (2026-08-01 정정) 초판의 "Σmeter = ω_F·N_UF* 등식"은 **틀린 문구다** — 이 등식은
   zone4에서도 flagship에서도 성립하지 않는다. METER-BOX 회랑([m_prev−R, m_prev+R_up])과
   spillback 하한이 예산보다 우선하도록 설계돼 있어(`_scale_to`의 target clamp = 박스=하드,
   예산이 양보), 회랑이 예산을 담지 못하면 Σmeter는 의도적으로 예산에서 벗어난다.
   또 `seg13_budget_inequality` 회랑 예산 분기는 애초에 등식이 아니라 α·budget ≤ Σ ≤ budget이다.
   지켜야 하는 것은 "zone이 소유 ramp를 하나도 빠뜨리지 않아 전부 사영을 통과한다"이며,
   솔버가 zone 모드에서 `set(preferred_meter) == set(link_model.owned_ramps)`로 강제한다.
   검증: `scripts/test_freeway_zone_followers.py::budget_projection_scope`
   (N_UF_star>0인 가짜 leader로 사영 참가자 집합을 단언).
4. `pstack-flagship` 모드와 독립. 두 기능이 서로를 깨지 않아야 한다.

## 단계

1. `_solve_freeway_segment_agents`와 `SegmentAgentModel` 전수 독해 → 다중 세그먼트화
   영향 지점 목록화 (own-TTS 회계, 예산 사영, 가격 항, 궤적 교환)
2. `freeway_agent_groups` cfg 키 + 그룹 기반 에이전트 빌더
3. 솔버 다중 세그먼트 대응
4. VISSIM tuning/생성기 반영
5. 검증 — 기본값 회귀(비트 동일) + 4-zone 스모크 + 예산 제약 확인

## 미해결

- FW_E 6:2 편중이 제어 성능에 미치는 영향 (경계 재지정 A/B 필요)
- ~~zone 균일 VSL이 병목 세그먼트 대응력을 얼마나 잃는지~~ → 해결(v2). 균일 VSL 폐기,
  세그먼트별 VSL + 좌표하강으로 교체. 남은 질문은 좌표하강 sweep 예산 대비 해 품질이다
  (`wu_zone_cd_sweeps_*` / `wu_zone_cd_converged_*` 진단으로 실런에서 측정).
- 4-zone과 SUP_PFO 감독자의 상호작용 (PFO 에뮬레이션은 링크 모드라 zone 구조 미적용)
- 좌표하강으로 zone당 평가수가 늘어난다(zone 세그먼트 수 × sweep 배). 실런 wall-time
  영향은 미측정 — 필요하면 `freeway_zone_vsl_max_sweeps`를 1~2로 낮춘다.
