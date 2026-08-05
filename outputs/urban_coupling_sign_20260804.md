# 도시부 신호 액션 부호 반전 — 원인 특정과 최소 수정안

작성 2026-08-04. 읽기 전용 조사다. VISSIM 실행·COM 접속 없음, 저장소 파일 수정 없음.
프로브는 전부 `C:/Users/alsrj/AppData/Local/Temp/claude/C--Users-alsrj-Desktop--------Claude/01a4e47a-5c39-4540-824b-c4f338c39ec8/scratchpad/ucprobe/` 에 있다.

---

## 0. 재현 기준선 — 이 보고서의 모든 숫자가 공식 산출과 일치한다

먼저 채점 조합을 확정했다. `evaluation/runs/g6_v4_signalfix_20260804/decisions_v4_c20_major75_seed13/action_002700.json` 의 metadata 가
`tuning_name = real_world_modi_pstack_vsl6_20260803`, `calibration_version = v3_postrepair_20260803` 을 적고 있다.
이 조합으로 `harness/gates/episode.py` + `harness/g6/g6_core.py` 경로를 그대로 태워 60 행(후보 15 × 지평 4)을 재계산했다.

| 항목 | 공식 (`outputs/gates_v4_20260804/`) | 내 재현 |
|---|---|---|
| max abs 오차 (model J) | — | **4.55e-13** |
| max abs 오차 (observed J) | — | **0.00** |
| `spearman_rho` (macro-mean, 4 결정) | 0.14477217577140827 | **0.144772** |
| `top_action_pairwise` | 0.5178571428571429 (29/56) | **0.517857 (29/56)** |

축별 rho 도 과제문의 값을 그대로 재현했다. anchor+vsl **+0.9145**, anchor+ramp **−0.3500**, anchor+green+offset **−0.4000**, 전체 15 후보 **+0.1448**.

**부기 — 지평 표기 정정.** 과제문 표의 `+2084.04 / −263.07` 은 지평 900 s 가 아니라 **H=5 (300 s)** 값이다.
공식 `g6_rows.json` 기준 지평별 c20_major75 는 아래와 같다.

| 지평 | 예측 ΔJ | 관측 ΔJ | 부호 |
|---|---:|---:|---|
| H=1 (60 s) | −25.33 | −15.00 | **일치** |
| H=5 (300 s) | +2084.04 | −263.07 | 불일치 |
| H=10 (600 s) | +11045.74 | −1534.86 | 불일치 |
| H=15 (900 s) | +27082.22 | −3321.68 | 불일치 |

부호 반전은 H=1 에서는 없고 H≥5 의 누적항에서 발현한다. 이것은 뒤에 나올 메커니즘(off-ramp storage 가 서서히 차오르며 실효 차로를 갉는 경로)과 정합한다.

---

## 1. 부호가 뒤집히는 정확한 지점 — **확정**

### 1.1 결론

> **`VISSIM/evaluation/controllers/vissim_stackelberg_adapter.py:3366-3367`**
> ```python
> control.green_times[f"{signal}_p1"] = float(minor_green_sec)
> control.green_times[f"{signal}_p2"] = float(major_green_sec)
> ```
> 이 두 줄이 **freeway 접속축을 담는 모델 phase 에 `minor` 를 넣는다.**
> 실 플랜트에서 freeway 접속축을 여는 신호그룹은 **major(EB/WB)** 다.

동치인 반대편 지점은 `NumSim-mine/src/models/grid_topology.py:143-147` + `:183` 이다. 둘은 같은 결함을 양끝에서 본 것이고, 어느 쪽을 고쳐도 부호는 맞는다. 어댑터를 고르는 이유는 §2.3 에 적었다.

부호 반전은 **이 한 지점뿐**이다. 이후 동역학 사슬(§1.4) 어디에도 추가 반전은 없다.

### 1.2 플랜트 축 정의 — `.inpx` 직독으로 확정 (기존 조사에서는 추론으로 남아 있던 부분)

선행 조사 네 갈래가 모두 "링크 방위와 SG 이름 규칙에서 추론했을 뿐 `.inpx` 를 열지 않았다"를 한계로 남겼고, 그중 한 반박은 램프 커넥터가 NS 방위라는 이유로 **정반대 결론**을 제시했다. 이 대립은 `.inpx` 를 읽어 해소된다. `.inpx` 파일을 읽는 것은 VISSIM 실행도 COM 접속도 아니다.

`VISSIM/network/real_world_gaepo_modi/modi_eval_rw_control.inpx` 를 파싱했다
(프로브 `ucprobe/uc_inpx_axis.py`. `signalHead@lane` 의 첫 토큰이 링크 번호라는 규약은 저장소 자신의 파서 `scripts/inventory_vissim_inpx.py:30-36` `lane_ref()` 를 따랐다).

**SC 1001 (유일한 `urban_freeway_interface_signal_controller`, `signal_controller_roles.csv` no=1001, interface_head_count=3)**

```
head 90030834  sg5 = EBL   link 32   EW   urban_freeway_interface_road
head 90030835  sg2 = EBT   link 32   EW   urban_freeway_interface_road
head 90030836  sg2 = EBT   link 32   EW   urban_freeway_interface_road

MAJOR (EB/WB) 접근 링크 = {29, 32, 10696}
MINOR (NB/SB) 접근 링크 = {37, 40}      ← 둘 다 role=urban_road, orientation=NS (교차 부도로)
```

그리고 링크 32 의 유입 커넥터는 **freeway 본선뿐**이다.

```
10481 : link 2  (freeway_mainline) → link 32     off-ramp
10491 : link 26 (freeway_mainline) → link 32     off-ramp
10490 : link 32 → link 2                          on-ramp
10482 : link 32 → link 26                         on-ramp
```

반대 방향 접속(도시부 → 본선)도 MAJOR 다. 링크 29(urban_road, EW) → 10119 → 링크 31(urban_freeway_interface_road, EW) → 10480 → 링크 26(본선). 링크 29 는 SC1001 의 MAJOR 집합에 있다.

`scripts/run_real_world_stackelberg_controller.vbs:893-903` `SignalStateForGroup` 이 SG 이름에 EB/WB 가 있으면 `majorState`, NB/SB 면 `minorState` 를 준다.

> **따라서 실 플랜트에서 `major_green` 은 freeway 접속축(유입·유출 양방향)을 열고, `minor_green` 은 NS 교차 부도로를 연다. 확정이다.**

이로써 "램프 커넥터 10479~10491 이 NS 방위이므로 램프축 = minor 일 것"이라는 반대 가설은 기각된다. 커넥터의 기하 방위는 정지선 SG 배정과 무관하다. 정지선 신호두는 커넥터가 아니라 **접근 링크 32 위에** 있고, 그 SG 는 EBT/EBL 이다.

### 1.3 모델 축 정의 — 런타임 덤프로 확정

`NumSim-mine/src/models/grid_topology.py`

```
:9    NS_AXIS = {"N", "S"}
:143  def _token_leg_dir(token):   # off*/on* 토큰은 무조건 "S" 를 돌려준다
:183  spec["phase"] = f"{node}_p1" if axis_dir in NS_AXIS else f"{node}_p2"
```
`:44`, `:55` 에서 D·F 노드의 **S leg 가 램프 leg**(`{"type":"ramp", "on":…, "off":…}`)다.

G6 채점 런타임 cfg 를 직접 덤프했다(`ucprobe/uc_final_repro.py`). tuning 체인 12 개(`vsl6_20260803` → … → `adapter_v0_20260719`) 어디에도 `network.urban_movements` / `grid_node_legs` override 가 없어 `state.py` 의 자동유도가 실제로 실행된다.

```
signals = ['A','B','C','D','F']
off_ramp movements : D_p1 6, F_p1 6      ← 12/12 전부 p1
on_ramp  movements : D_p1 2, D_p2 2, F_p1 2, F_p2 2
off_ramp_to_movement : OR_D_W 3, OR_D_E 3, OR_F_W 3, OR_F_E 3
```

> **모델에서 off-ramp 방출을 게이트하는 movement 는 12개 전부 p1 이다. 어댑터는 p1 에 `minor` 를 넣는다.**

즉 `major_green 57→75` 는 모델 안에서 "freeway 접속축 green 을 57→25 로 조르기"로 집행된다. 플랜트에서는 정확히 반대다.

**부수 확인 — 사이클 순서도 같은 방향으로 어긋나 있다.**
플랜트는 `run_real_world_stackelberg_controller.vbs:787-798` 에서 `[major GREEN][amber][all-red][minor GREEN][amber][all-red]` 로 **major 를 사이클 앞**에 둔다.
모델은 `NumSim-mine/src/models/urban_queue_model.py:567` `start = 0.0 if phase_id == "p1" else g1 + half_lost` 로 **p1 을 사이클 앞**에 둔다.
p1↔major 로 맞추면 offset 기준점까지 함께 정합된다. 이것은 §1.1 결론의 독립적인 두 번째 근거다.

### 1.4 부호 사슬 — 각 단계 부호를 실측했다 (H=5, c20_major75)

반전은 1 단계 하나뿐이고, 2~6 단계는 전부 정상 부호다.

| # | 지점 | 동작 | 부호 |
|---|---|---|---|
| 1 | `adapter.py:3366-3367` | major 57→75 가 `green_times[D_p1]` 을 57→**25** 로 만든다 | **반전 발생** |
| 2 | `urban_queue_model.py:541-580` `_phase_green_fraction` | p1 green fraction 0.475 → 0.208 (−56 %) | − (정상, 단조) |
| 3 | `urban_queue_model.py:446-515` `_drain_offramp_storage` (`:486` fraction, `:488` `intended = min(β·occ, dt_h·fraction·cap)`) | off-ramp 방출 용량 −56 % | − (정상) |
| 4 | off-ramp storage 점유 누적 | 584.69 → **981.31** veh·step (×1.68) | + |
| 5a | `leader.py:774` `base += off_ramp_storage_occupancy_veh(net)` (2026-06-17 재귀속 설계) | 도시부 정체가 **freeway base 로 계상** | + |
| 5b | off-ramp 백업 → 실효 차로 저하 → 본선 밀도 상승 | freeway 누적 9879.20 → **10419.77** (+540.57) | + |
| 6 | `leader.py:780-816` `_density_penalty`, `:911` `density_penalty = lc.w_F · density_excess` (w_F=3.0) | **+1499.74** | + |

합계 검산 (`leader.py:925-932`).

```
ΔJ = Δbase(+626.67) + Δdensity_penalty(+1499.74) + Δramp_queue_penalty(−42.37) = +2084.04   ✓
```

anchor J 도 항등식이 성립한다. `14816.135 = base 11891.66 + density 2836.00 + ramp_queue 88.48`.
`target_penalty` / `mfd_storage_penalty` / `boundary_in_queue_penalty` 는 **60 행 전부에서 정확히 0** 이다
(각각 `adapter.py:1532` 의 `mfd_penalty_mode="all_urban_halfcap"` 하드코딩으로 `leader.py:885` 가 False, 임계 0.5 미도달, `w_boundary_in=0.0` 때문).

**기각된 대안 가설.** "major green ↑ → on-ramp 방류 ↑ → 본선 유입 증가 → J 악화"는 성립하지 않는다.
실측 Δramp_queue_penalty = **−42.37 (음수)** 이고 Δramp_queue_veh = −7.06 이다. 램프 통로는 J 를 **낮추는** 방향이며 ΔJ 의 −2.0 % 에 불과하다.

### 1.5 반사실 확인

`green_times` 의 p1/p2 만 교환해 같은 앵커·같은 관측으로 재채점했다(`ucprobe/uc_final_repro.py`). 플랜트 궤적은 손대지 않았다.

| 축 | 현행 | 축 반전 후 |
|---|---:|---:|
| anchor+vsl | +0.9145 | **+0.9145 (완전 불변)** |
| anchor+ramp | −0.3500 | **−0.3500 (완전 불변)** |
| anchor+green+offset | −0.4000 | **+1.0000** |
| 전체 15 후보 (`spearman_rho`) | +0.1448 | **+0.7292** |
| `top_action_pairwise` | 0.5179 (29/56) | **0.9821 (55/56)** |

후보별 부호(4 지평 전부).

| 후보 | 현행 예측 | 반전 후 예측 | 관측 | 부호 |
|---|---:|---:|---:|---|
| c20_major75 (H=5) | +2084.04 ✗ | **−1083.57** | −263.07 | 일치 |
| c21_minor75 (H=5) | −1083.57 ✗ | **+2084.04** | +108.29 | 일치 |
| c30_offset30 (H=5) | −324.18 | −324.18 (불변) | −178.01 | 일치 유지 |

c20/c21 은 H=1/5/10/15 **네 지평 모두** 반전 후 부호가 맞는다.

> **정직한 단서 하나.** c20 과 c21 은 서로의 거울상이므로(c20 의 p1/p2 교환 = c21 의 액션) 이 두 후보에 대한 "반전"은 새 시뮬레이션이 아니라 **두 열의 라벨 교환**이다. 따라서 green 축 rho = +1.000 은 반전이 옳다는 **증명이 아니라 결과**다. 증명은 §1.2 의 `.inpx` 물증이 담당한다. c40/c41 은 VSL·램프가 함께 걸려 있어 진짜 새 rollout 이며, 이들은 §4 에서 따로 다룬다.

---

## 2. 최소 수정안

### 2.1 제약 — 무조건 하드코딩 스왑은 안 된다

합성 8-seg 망은 축 규약이 **정반대**다. `evaluation/signal_install/signal_manifest.csv` 의 minor 신호두 20개 purpose 가 문자 그대로 `"Minor/ramp-axis stop-line signal head"` 다. 그리고 그 망의 런은 같은 어댑터를 타며 signal id 가 `A~F` 라 모델 신호명과 **일치**한다(`evaluation/runs/8seg_sweet_w_20260714/action_nc_190w.csv` 의 signal 행 id = A,B,C,D,F / sc_no 1~5). 즉 `:3769-3770` 조회가 그 망에서는 적중하므로 무조건 스왑은 합성망 회귀를 깬다.

따라서 축 규약은 **매핑 파일이 선언**하게 해야 한다. 기본값은 현행 동작으로 두어 합성망을 건드리지 않는다.

`phase_map` 필드는 `scripts/generate_real_world_control_mapping.py:97` 이 쓰기만 하고 **런타임 소비처가 전 저장소에 0 건**이다(grep 확인). 이 필드에 소비 로직을 처음 붙이는 것이다.

### 2.2 diff (어댑터 4 지점 + 매핑 1 파일)

**(a) 축 규약 헬퍼 추가** — `vissim_stackelberg_adapter.py`, `_diagnostic_fixed_control` 정의부 앞 아무 곳.

```python
def _major_model_phase(mapping) -> str:
    """플랜트의 major(EB/WB) 축에 대응하는 모델 phase.

    실측 개포망: SC1001 의 EB SG 가 freeway 접속 링크 32 를 잡고, 모델에서 램프 leg
    movement 는 전부 p1 이다 → major ↔ p1.
    합성 8-seg 망: signal_manifest.csv 의 minor 가 램프축이다 → major ↔ p2 (기본값).
    """
    if isinstance(mapping, Mapping):
        for sig in (mapping.get("signals") or []):
            pm = (sig or {}).get("phase_map") or {}
            v = str(pm.get("major_model_phase", "")).strip().lower()
            if v in ("p1", "p2"):
                return v
    return "p2"          # 기본값 = 현행 동작. 선언이 없으면 아무것도 바뀌지 않는다.
```

**(b) `:3366-3367`** (`_diagnostic_fixed_control`) — 모델 액션 생성.

```diff
-        control.green_times[f"{signal}_p1"] = float(minor_green_sec)
-        control.green_times[f"{signal}_p2"] = float(major_green_sec)
+        _mp = _major_model_phase(mapping)          # 함수 시그니처에 mapping 추가 필요
+        _mn = "p2" if _mp == "p1" else "p1"
+        control.green_times[f"{signal}_{_mp}"] = float(major_green_sec)
+        control.green_times[f"{signal}_{_mn}"] = float(minor_green_sec)
```

**(c) `:3437-3438`** (`_diagnostic_signal_only_control`) — 같은 규약으로 교체.
G6 후보집합에서는 `EXCLUDED_VARIANTS`(`g6_core.py:129-136`)로 빠져 있어 이번 측정에는 영향이 없지만, 빼놓으면 두 생성기의 규약이 갈라진다.

**(d) `:2739-2740`** (`signal_green_freeze`) — 같은 규약으로 교체.
현재 유일 사용처 `evaluation/configs/tuning_turning_ratios_route_manifest_v2_pfo_green_frozen_20260715.json` 이 `green_sec: 57.0` 단일값이라 major=minor 여서 지금은 무해하다. 비대칭 freeze 가 생기는 순간 (e) 와 어긋난다.

**(e) `:3769-3770`** — CSV 되쓰기. **(b) 와 반드시 동시에** 바꿔야 플랜트로 나가는 값이 보존된다.

```diff
-                major = clamp(float(control.green_times.get(f"{signal}_p2", _maj_default)), 5.0, 90.0)
-                minor = clamp(float(control.green_times.get(f"{signal}_p1", _min_default)), 5.0, 90.0)
+                _mp = _major_model_phase(mapping)
+                _mn = "p2" if _mp == "p1" else "p1"
+                major = clamp(float(control.green_times.get(f"{signal}_{_mp}", _maj_default)), 5.0, 90.0)
+                minor = clamp(float(control.green_times.get(f"{signal}_{_mn}", _min_default)), 5.0, 90.0)
```

**(f) 매핑 파일 3 개에 선언 추가** — 실측 개포망 전부.

```jsonc
// evaluation/real_world_modi_control/control_mapping.json                       (signals[0], id="D")
// evaluation/real_world_modi_control_distributed_20260728/control_mapping_distributed_15core_20260728.json  (15개 전부)
// .../control_mapping_distributed_19sc_20260728.json                            (19개 전부)
"phase_map": {
  "major_model_phase": "p1",
  "major_axis": "east_west",
  "major_sg_name_prefixes": ["EB", "WB"],
  "minor_sg_name_prefixes": ["NB", "SB"],
  "evidence": "modi_eval_rw_control.inpx: SC1001 heads 90030834(sg5=EBL)/90030835,90030836(sg2=EBT) sit on link 32 (urban_freeway_interface_road, EW), fed only by off-ramp connectors 10481(2->32) and 10491(26->32). Model ramp-leg movements are all p1 (grid_topology.py:143-147,183)."
}
```

**(g) `:3754-3758` 주석 교체.** 현행 주석은 "SG1(MAJOR)=E-W = 모델 p2" 라는 **나침반 라벨** 근거만 적어 놓아 다음 사람이 또 되돌린다. 두 가지를 명기해야 한다.
- 그 검증(`evaluation/signal_install/signal_manifest.csv`, 20/20)은 **합성 8-seg 망**의 것이고 실측 개포망에는 적용되지 않는다. 두 망은 축 규약이 반대다.
- 모델 격자는 추상 6 노드라 실제 개포동 기하와 방위가 대응하지 않는다. 맞춰야 하는 것은 나침반 라벨이 아니라 **freeway 접속축이라는 물리적 역할**이다.

### 2.3 왜 어댑터인가 (모델 쪽 `grid_topology.py:183` 대신)

두 안 모두 부호를 고친다. 어댑터를 고르는 이유는 셋이다.
1. `grid_topology.py` 는 합성망과 실측망이 **공유**한다. 여기서 램프 토큰을 p2 로 보내면 합성망이 깨진다. 방위를 데이터로 주입하려면 `grid_node_legs` 스키마 확장이 필요해 파급이 훨씬 크다.
2. 어댑터 안은 (b)와 (e)가 왕복 상쇄되므로 **플랜트로 나가는 액션이 바뀌지 않는다**. 기존 관측 궤적 124 에피소드를 그대로 재사용할 수 있다.
3. 모델 쪽 수정은 `state.py` → `build_urban_movements` 자동유도를 타므로 turning ratio·movement 이름까지 연쇄로 바뀐다. 부호 확정 전에 감당할 파급이 아니다.

권고는 **어댑터로 부호를 먼저 확정**하고, 모델 토폴로지의 방위 주입은 별건으로 분리하는 것이다.

### 2.4 부작용 범위

**바뀌지 않는 것 (증명 가능).**
- **플랜트로 나가는 CSV 액션.** (b)와 (e)가 상쇄된다. 게다가 G6 v4 런에서는 애초에 `:3769-3770` 조회가 **전부 miss** 한다 — 매핑 signal id 는 `SC1…SC1005` 인데 모델 `green_times` 키는 `A_p1…F_p2` 라 교집합이 0 이고, 값은 `:3766-3767` 의 diagnostics 폴백에서 나온다(어댑터 주석 `:3759-3763` 이 이미 이 사실을 기록하고 있다). 따라서 이 런에 대해서는 (e)가 **무연산**이다.
- **VSL 축 rho +0.9145, ramp 축 rho −0.3500.** 후보집합 15 개 중 major≠minor 인 것은 **c20 / c21 / c40 / c41 넷뿐**이다(`g6_core.py:106-118`). 나머지 11 개(c00 앵커, c01~c06 VSL, c10~c12 ramp, **c30 offset 포함**)는 전부 major=minor=57.0 이라 p1/p2 배정 교환이 **항등 연산**이다. `green_times` 딕셔너리가 비트 동일 → rollout 비트 동일. 실측으로도 두 축 rho 가 소수점까지 불변임을 확인했다.
- **G5 재채점.** `harness/gates/run_gates.py:88-93` → `harness/gates/episode.py:145-153` `executed_control` 이 `control_from_json` 으로 **저장된 `action_*.json` 의 green_times 를 그대로** 복원한다. (b)(c)(d)(e)는 컨트롤 **생성기**와 CSV **송출기**라 이 경로에 없다. 기존 124 에피소드 G5 리포트는 비트 동일이다.
- **합성 8-seg 망.** `major_model_phase` 기본값이 `"p2"`(= 현행)이고 그 망 매핑에는 선언을 넣지 않으므로 변화 0 이다.

**바뀌는 것.**
- 모델 rollout: c20 / c21 / c40 / c41 네 후보만.
- **폐루프 런은 의미가 바뀐다.** `NumSim-mine/src/controllers/distributed_coordinator.py:1186-1189` 이 탐색한 p1 이 앞으로 VISSIM 의 major 칼럼으로 나간다(id 가 일치하는 매핑에 한해). 실컨트롤러는 앵커 근방에 머물지 않는다 — `evaluation/runs/new_baseline_ab_20260801/decisions_stackelberg_scale170_.../action_002280.json` 의 green_times 가 `A 28/86, B 22/92, C 22/92, D 92/22, F 92/22` 로 `default.yaml` 의 green_max 92 에 포화해 있다. 게다가 **노드별 비대칭 부호가 반대**다(D·F 는 p1 이 긴 쪽, A·B·C 는 p2 가 긴 쪽). 일괄 반전은 D·F 에서만 의도한 방향이고 A·B·C 에서는 긴 green 이 반대 축으로 간다. G6 green 후보는 15 SC 에 동일한 75/25 를 강제하므로 이 구조를 **원리적으로 관측할 수 없다**. 폐루프(G5 신규 수집 포함) 재측정 전에 A·B·C 의 축 대응을 §6 의 `.inpx` 절차로 별도 확인해야 한다.
- `green_min_fraction 0.2` / `green_max_fraction 0.8` (`NumSim-mine/src/config/default.yaml`) 의 대역이 p1 기준으로 튜닝돼 있다면, p1 의 의미가 "NS 부도로"에서 "freeway 접속축"으로 바뀌면서 물리적으로 부적절해질 수 있다. 재검토 대상이다.

**별건으로 발견한 결함 (이번 수정과 무관, 그러나 폐루프에 직접 영향).**
`evaluation/real_world_modi_control/control_mapping.json` 의 `signals[0]` 이 `sc_no: 1` 이고 note 에 "SC 1 is the only controller inventoried with freeway-interface signal heads" 라고 적혀 있는데, `signal_controller_roles.csv` 기준 SC 1 은 `role=urban_signal_controller, interface_head_count=0` 이고 freeway-interface 컨트롤러는 **no=1001** 이다. `.inpx` 로도 SC 1 의 접근 링크는 `1220007104 / 1210008401 / 1220008201 / 1220006903` 으로 인터페이스 링크(29/31/32/37/40)가 하나도 없다. **기본 매핑이 엉뚱한 교차로를 제어하고 있다.**

---

## 3. 램프 과소응답 — 원인과 수정안

### 3.1 원인 — 미터율이 불감대 안이다. "수요 과소추정"이 아니다

`coupling.py:168-174` 가 `compute_ramp_release_flows(..., include_current_arrivals=False)` 로 호출하므로 `metanet.py:300` 의 `available` 은 정확히 `w_r / T_f_h` 다. `:301-302` 의 `min(available, cap, q_cap·recv, requested)` 에서 argmin 이 미터율(`requested`)이 아니라 **램프 저수지 잔량**이다.

미터율 스윕 실측(H=5, D 램프쌍, `ucprobe/uc_final_ramp.py`).

| 미터율 (vph/램프) | D 램프 잔여 큐 q_end | 모델 ΔJ |
|---:|---:|---:|
| 1800 (앵커) | 1.603 | 0.00 |
| **1364 (c10)** | **1.603** | **+0.49** |
| **1253 (c11)** | **1.603** | **+0.72** |
| 900 | 1.603 | +1.98 |
| **691 (c12)** | **1.603** | **+4.48** |
| 650 | 1.603 | +5.46 |
| **620** | **1.870** | **+7.79**  ← 여기서 처음 구속 |
| 500 | 4.553 | +26.66 |
| 360 | 15.262 | +126.86 |
| 200 | 40.855 | +425.07 |
| 0 | 74.188 | +820.89 |

구속 임계는 **650~620 vph/램프 사이**다. 시험된 세 후보 1364 / 1253 / 691 은 **전부 임계 위**라 큐가 전혀 쌓이지 않는다(q_end 가 앵커와 소수점까지 동일). ΔJ +0.49 / +0.72 / +4.48 은 방출 타이밍이 T_f 경계에서 밀리며 생기는 수치 잔차일 뿐이다. 앵커 J 의 0.003~0.03 % 다.

**모델의 램프 부호 자체는 건강하다.** 620 아래로 내리면 ΔJ 가 단조 증가하고 큐 잔류와 정합한다. 문제는 시험점이 전부 불감대에 놓인 것이다.

### 3.2 플랜트도 같은 불감대 안에 있다

액션 CSV 를 보면 미터링은 플랜트에 **제대로 전달된다**(모델 램프당 rate 를 미터 2 기로 나눈다).

```
c10_rampd1364 : RM_C10480/10482/10484/10490 = 682.0 vph, green 8 s
c11_rampd1253 : 626.5 vph, green 7 s
c12_rampd691  : 345.5 vph, green 4 s
c00_anchor    : 900.0 vph, green 10 s
```

그런데 플랜트의 D 램프 대기대수는 자라지 않는다. `R_D_W + R_D_E` 를 t=2700/2760/2820/2880 에서 보면 앵커 14 / 21 / 12 / 18, c12(691) 14 / 17 / 12 / 16 으로 **오히려 약간 낮다**. 플랜트 램프 수요도 691 vph 아래다.

**즉 램프 축은 모델에서도 플랜트에서도 아무것도 재고 있지 않다.** 관측 ΔJ 는 잡음이다. 근거 둘.
- **지평마다 부호가 뒤집힌다.** c10: H1 −7.0, H5 +135.1, H10 +68.8, H15 −473.2. c12: H1 −26.0, H5 +21.7, H10 −150.7, H15 −437.1.
- **단조성이 깨진다.** 미터링이 가장 약한 c10(1364)이 H5 에서 가장 큰 벌점(+135.1)을 낸다.

따라서 과제문의 "275 배 / 31 배 / 4.8 배 과소"라는 비율은 **분모가 잡음**이라 성립하지 않는다. 램프 축 rho −0.350 은 현재 **해석 불가값**이다.

### 3.3 수정안

**[R1] 후보를 모델·플랜트 공통 작동대역으로 옮긴다 (모델 위험 0, 필수)**

`harness/g6/g6_core.py:113-115` 의 세 램프 후보를 구속 임계 아래로 내린다.

```diff
-    Candidate("c10_rampd1364", "diagnostic-ramp-d1364", "ramp", 120.0, 1364.0, _RAMP_OPEN, 57.0, 57.0, 0.0),
-    Candidate("c11_rampd1253", "diagnostic-ramp-d1253", "ramp", 120.0, 1253.0, _RAMP_OPEN, 57.0, 57.0, 0.0),
-    Candidate("c12_rampd691",  "diagnostic-ramp-hold",  "ramp", 120.0,  691.0, _RAMP_OPEN, 57.0, 57.0, 0.0),
+    Candidate("c10_rampd500", "diagnostic-ramp-d500", "ramp", 120.0, 500.0, _RAMP_OPEN, 57.0, 57.0, 0.0),
+    Candidate("c11_rampd360", "diagnostic-ramp-d360", "ramp", 120.0, 360.0, _RAMP_OPEN, 57.0, 57.0, 0.0),
+    Candidate("c12_rampd200", "diagnostic-ramp-d200", "ramp", 120.0, 200.0, _RAMP_OPEN, 57.0, 57.0, 0.0),
```
모델 ΔJ 가 +26.66 / +126.86 / +425.07 로 단조·분리 가능해진다. 어댑터의 대응 생성기(`diagnostic_ramp_d1364_control` `:3517`, `diagnostic_ramp_d1253_control` `:3528`, `diagnostic_ramp_hold_control` `:3506`)와 `--controller` variant 이름도 함께 바꾼다.

**선행 조건.** 플랜트 미터 green 은 `adapter.py:2614` `green = round(cycle · per_meter_rate / per_meter_capacity)` 로 양자화된다. cycle=10 s, per_meter_capacity=900 이므로 500→round(2.78)=3 s(실효 540 vph), 360→2 s(360), 200→round(1.11)=1 s(180). 200 목표가 실제 180 이 되는 −10 % 오차가 생긴다. **`real_world_ramp_metering.cycle_sec` 를 10 → 20~30 s 로 먼저 늘려 해상도를 확보한 뒤** R1 을 적용해야 모델·플랜트 액션 정의가 다시 어긋나지 않는다.

**[R2] 채점에 binding 게이트를 넣는다 (필수, 해석 위생)**

`objective_from_states` 반환에 램프 binding 진단을 실어, 앵커 대비 지평 누적 램프 방출량의 상대차가 1e-3 미만이면 그 후보를 `axis_inactive` 로 표시하고 순위 집계에서 제외한다.
**반드시 지평 누적으로 재야 한다.** 개별 T_f 경계에서는 1364 조차 argmin 이 되는 경우가 있어(순간 release 는 구속) per-step 비교는 오판한다. 불변인 것은 **지평 적분 유입**이다.
현 상태는 "모델이 0 을 예측하고 플랜트가 잡음을 냈다"를 순위 불일치로 채점하고 있다.

**[R3] 램프 수요 채널 결손은 별건으로 분리한다 (권고: 지금 건드리지 마라)**

사실관계는 이렇다. `state_002700.json` 의 `demand.ramp_volume_vph` 가 **0** 이고, `adapter.py:1581` 이 `demand.get("ramp_volume_vph", fallback)` 이라 키가 존재하므로 fallback 이 안 걸려 0 을 쓴다. 실제 값 240/180/720/120 vph 는 `prediction.local_ramp_arrival_forecast`(대기대수 × 3600/120)가 만든 대용값이지 수요 측정이 아니다. 이 네트워크 전용으로 작성된 route-aware 보정 `prediction.onramp_route_forecast`(`adapter.py:1635-1642`)는 활성 체인에 키가 없어 꺼져 있다.

그러나 수요를 키우는 처방은 **G6 를 악화시킨다**. 선행 조사의 측정에서 fallback 831.6 vph 를 적용하면 c12(691)가 살아나긴 하지만(ΔJ +297) anchor+ramp rho 는 −0.200 → −0.600 (H5), 전체 15 후보는 +0.311 → +0.282 로 내려간다. 관측 신호가 잡음인데 모델만 민감하게 만들면 **더 확신 있게 틀릴 뿐**이다.

근본 해법은 VISSIM 러너가 `demand.ramp_volume_vph` 에 실제 on-ramp 유량을 실어 보내게 고치는 것이다. 그것은 G5(예측 정확도) 과제이지 G6(순위) 과제가 아니다. 참고로 `outputs/gates_v4_20260804/g5_report.json` 의 `urban.levels.interface_ramp_queue` 는 mae 8.147, **bias −8.147**, mean_observed 8.81 로 모델 램프 큐가 관측 대비 상시 과소임을 이미 독립 계측해 두었다.

---

## 4. 수정 후 예상되는 G6 rho 변화 — 낙관하지 않는다

### 4.1 실측된 변화 (§1.5 반사실, seed13 / t0=2700 / 지평 4)

| 지표 | 현행 | 축 반전 후 | 게이트 임계 | 판정 |
|---|---:|---:|---:|---|
| `spearman_rho` | 0.1448 | **0.7292** | ≥ 0.70 | FAIL → **PASS** |
| `top_action_pairwise` | 0.5179 | **0.9821** | ≥ 0.80 | FAIL → **PASS** |
| `spillback_f1` | 0.000 | (불변, §4.3) | ≥ 0.80 | FAIL → **FAIL** |

지평별 `spearman_rho` 는 H1 0.606 / H5 0.688 / H10 0.824 / H15 0.799 다. **여유가 크지 않다** — H1·H5 는 임계 0.70 아래이고 macro-mean 0.729 가 0.70 을 넘는 것은 H10·H15 덕이다.

### 4.2 낙관하면 안 되는 이유 다섯

**(1) G6 는 여전히 FAIL 이다.** `spillback_f1 = 0.0` 은 축 반전으로 고쳐지지 않는다(§4.3). 세 기준 중 하나라도 FAIL 이면 게이트는 FAIL 이다.

**(2) 단일 셀이다.** seed13, t0=2700, 1 개 에피소드, `decision_count = 4`. 계약 §11 G5 가 요구하는 seed/demand/policy holdout 분리가 안 된 상태다. 0.7292 는 임계 0.70 을 **0.029** 차로 넘는다. 다른 셀에서 −0.03 만 나와도 뒤집힌다.

**(3) 크기 격차가 그대로 남는다.** 부호만 고쳐진다.

| 지평 | c20 모델/관측 배율 | c21 모델/관측 배율 |
|---|---:|---:|
| H=1 | 6.25× | 25.33× |
| H=5 | 4.12× | 19.24× |
| H=10 | 2.79× | 14.15× |
| H=15 | 3.04× | 12.55× |

비대칭이 크다. 램프축 green 을 **줄이는** 방향(c21)에서 모델이 12~25 배 과대반응한다. 게다가 freeway 성분만 떼어 봐도 과대다 — c20 반전 후 모델 Δfreeway = −239.34 veh·step 인데 관측은 −22.00 이다(**10.9 배**). 즉 이것은 §4.4 의 관측 결손만으로 설명되지 않고 **모델의 도시부→freeway 결합 이득 자체가 너무 세다**. Spearman 은 순위만 보므로 지금은 드러나지 않지만, 후보를 촘촘히 깔면 재발한다.

**(4) c40 / c41 은 안 고쳐진다.** 이들은 진짜 새 rollout 인데 결과가 갈린다.

| 후보 | H=1 | H=5 | H=10 | H=15 |
|---|---|---|---|---|
| c40 반전 후 예측 | −71.24 | −743.10 | −3362.25 | −8613.92 |
| c40 관측 | −9.00 | **+135.86** | −264.82 | −1682.87 |
| c41 반전 후 예측 | −27.56 | −404.87 | −1610.12 | −4408.01 |
| c41 관측 | −98.01 | −69.99 | **+194.12** | **+524.64** |

반전 후 8 개 중 5 개만 맞는다(현행은 3 개). 그러나 **관측 자체의 부호가 지평마다 뒤집힌다** — c40 은 H5 에서, c41 은 H10·H15 에서. 즉 combined 축의 플랜트 응답은 부호 안정성이 없어 어느 쪽 예측이 옳은지 판정할 수 없다. |ΔJo| 가 앵커 J 의 0.2~1.1 % 수준이라 잡음대에 있다. **c40/c41 이 맞아떨어지는 것을 성공 근거로 쓰면 안 된다.**

**(5) w_F 재가중은 하지 마라 — 반전 후에는 오히려 해롭다.**
J 는 `base(×1) + w_F·density_excess + w_ramp_queue·ramp_queue_veh` 이고 density_excess 는 임계 초과 **차량 수**라 base 가 이미 1× 로 센 차량을 다시 센다(순수 이중계상). 그래서 w_F 를 낮추는 처방이 자연스러워 보인다. 실제로 **현행(깨진) 축에서는 도움이 된다.** 그러나 축을 고치면 부호가 반대가 된다.

| 축 | w_F | anchor+vsl | anchor+ramp | green+offset | 전체 15 | pairwise |
|---|---:|---:|---:|---:|---:|---:|
| 현행 | 3.0 | +0.914 | −0.350 | −0.400 | +0.145 | 0.518 |
| 현행 | 1.0 | +0.955 | −0.500 | −0.500 | **+0.269** | 0.375 |
| 현행 | 0.0 | +0.982 | −0.150 | −0.500 | **+0.352** | 0.357 |
| **반전** | **3.0** | +0.914 | −0.350 | **+1.000** | **+0.729** | **0.982** |
| 반전 | 1.0 | +0.955 | −0.500 | +0.950 | +0.706 | 0.929 |
| 반전 | 0.0 | +0.982 | −0.150 | +0.950 | +0.717 | 0.911 |

반전 후에는 **w_F = 3.0 이 최선**이다. w_F 를 낮추면 VSL 축은 좋아지지만(+0.914 → +0.982) 전체와 pairwise 가 내려간다. `w_ramp_queue` 를 0 으로 내리면 전체가 0.729 → 0.575 로 붕괴한다. **축 수정과 가중치 재조정을 묶어 넣지 마라. 축만 고쳐라.**

같은 이유로 **총 green 비보존 보정도 크기 문제를 안 고친다.** `urban_queue_model.py:561` 이 `cycle = max(net.cycle_length, 1e-9)` 로 사이클을 120 에 고정해 75/25 후보가 총 green 100/120 = 0.833 (앵커 114/120 = 0.950) 로 −12.3 % 용량 충격을 함께 받는 반면, 플랜트는 `vbs:787-798` 에서 `cycle = major + minor + 10` 으로 재계산한다(75/25 → 0.909, 57/57 → 0.919, 손실 1 %). 그러나 총 green 을 114 로 재정규화해도 |ΔJ| 는 c21 −10.2 %, **c20 +19.3 %** 로 방향이 일관되지 않는다(H=5 기준 2084.04 → 1870.84, −1083.57 → −1292.73). 크기 문제의 주범이 아니다.

### 4.3 `spillback_f1` 은 왜 안 고쳐지는가

혼동행렬은 (모델 True, 관측 False) 45 / (False, False) 15 다. **관측 spillback 이 60 행 전부 False** 이고, 이것은 구조적이다. `g6_core.py` 의 `spillback_flag` 는 urban link 점유 ≥ 0.9·capacity 또는 ramp queue ≥ 0.9·180 을 본다. 관측 투영 앵커 상태에서

- urban link 29 개 중 점유가 0 이 아닌 것은 **4 개뿐**이고 전부 off-ramp storage 다 (`OR_D_W 2.5/60, OR_F_W 13.0/60, OR_D_E 10.0/60, OR_F_E 31.5/60` → 최대 0.525 < 0.9).
- ramp queue 최대 24/180 = 0.13 < 0.9.

즉 관측 쪽에서 spillback 이 **발생할 수 없다.** F1 은 축 수정과 무관하며 §4.4 의 관측 결손을 고쳐야 움직인다.

### 4.4 별건 — 관측 J 의 도시부 성분이 거의 비어 있다

관측 투영 상태에서 urban movement 큐는 78 개 중 12 개만 비영(합 57.0 veh)이고, urban link 점유는 29 개 중 4 개(전부 off-ramp storage)뿐이다. base 3 분할이 이를 명확히 보여준다(H=5 누적 veh·step).

| | freeway | off-ramp storage | urban |
|---|---:|---:|---:|
| 모델 앵커 | 9879.20 | 584.69 | 1747.61 |
| **관측 앵커** | 9703.00 | **324.00** | **324.00** |
| 관측 c20 | 9681.00 | 301.00 | 301.00 |
| 관측 c21 | 9710.00 | 375.00 | 375.00 |

관측의 `objective_urban_vehicles` 가 `off_ramp_storage_occupancy_veh` 와 **매 후보에서 정확히 같은 값**이다. 즉 관측 J 의 도시부 성분 = off-ramp storage 뿐이다.

`harness/g6/g6_core.py:4-11` 의 "같은 함수를 두 궤적에 적용하므로 J 정의 차이로 인한 오염은 없다"는 **함수 동일성에 대해서만 참**이고 **정보량에 대해서는 거짓**이다. docstring 을 정정하고, `leader_objective_base` 의 freeway/off-ramp/urban 3 분할을 진단으로 리포트에 남길 것을 권한다.

---

## 5. 검증 방법

### 5.1 VISSIM 재실행 없이 확인할 수 있는 것

**(V1) `.inpx` 신호두-링크 대조 — 이미 완료했다.**
`ucprobe/uc_inpx_axis.py`. SC1001 의 EBL/EBT 헤드가 링크 32 위에 있고, 링크 32 는 본선 커넥터 10481/10491 로만 채워진다. 재확인은 이 스크립트 재실행으로 충분하다. 폐루프까지 나갈 거라면 **나머지 14 개 SC 에 대해서도** 같은 표를 만들어 노드별 축 대응을 확정해야 한다(§2.4 의 A·B·C 문제).

**(V2) 플랜트 액션 불변 증명.**
수정 전후로 `evaluation/runs/g6_v4_signalfix_20260804/action_v4_*_seed13.csv` 를 재생성해 signal 행의 `major_green`/`minor_green` 이 **바이트 동일**한지 확인한다.
단, 이 런에서는 `:3769-3770` 조회가 항상 miss 해 diagnostics 폴백으로 값이 나오므로 **이 검사만으로는 공허하게 통과**한다. 반드시 **`green_times` 조회가 실제로 적중하는 매핑**에서도 함께 확인하라 — `evaluation/real_world_modi_control/control_mapping.json`(signal id = "D") 또는 합성 8-seg 런(id = A~F). 후자는 `major_model_phase` 미선언이므로 값이 변하지 않아야 한다.

**(V3) shadow 재채점.**
기존 `g6_v4_signalfix_20260804` 상태열로 `harness/gates/run_gates.py` 를 다시 돌린다. 예측만 바뀌고 관측은 그대로다. 기대값은 §4.1 표다.

**(V4) G5 비트 동일성.**
`outputs/gates_v4_20260804/g5_report.json` 을 재생성해 diff 가 비는지 본다. `executed_control` 이 저장된 action JSON 을 읽으므로 변화가 없어야 한다. 변화가 나오면 (b)(e) 중 하나가 G5 경로에 샜다는 뜻이다.

**(V5) 불변 후보 검사.**
c00 / c01~c06 / c10~c12 / c30 의 `model_objective` 11 개가 수정 전후 **비트 동일**한지 확인한다. 하나라도 움직이면 `major_model_phase` 분기가 major=minor 후보에 영향을 준 것이다.

**(V6) 합성망 회귀.**
`evaluation/runs/8seg_sweet_w_20260714/action_*.csv` 를 재생성해 `(major_green, minor_green)` 이 보존되는지 확인한다. 이 런에는 `(22.0, 90.0)` 같은 비대칭 행이 실제로 존재하므로 유효한 회귀 검사다.

**(V7) 램프 binding 재확인.**
`ucprobe/uc_final_ramp.py` 의 미터율 스윕을 그대로 돌려 임계가 650~620 구간에 있는지 확인한다. R1 후보값(500/360/200)이 임계 아래인지 확인하는 것이 목적이다.

### 5.2 VISSIM 재실행이 필요한 것

**(R-a) R1 의 새 램프 후보 3 개.** 새 미터율의 플랜트 궤적이 없다. `cycle_sec` 를 늘리는 변경도 함께 들어가므로 앵커 포함 재수집이 필요하다.

**(R-b) 셀 확장.** §4.2(2). 다른 seed / t0 / 수요 프로파일에서 `spearman_rho ≥ 0.70` 이 유지되는지. 0.029 마진은 단일 셀로 주장하기에 얇다.

**(R-c) 폐루프 / G5 신규 수집.** §2.4. 실컨트롤러가 22/92 같은 포화 비대칭을 내고 노드별 부호가 반대이므로, 축 반전 후의 폐루프 성능은 기존 베이스라인과 수치 연속성이 끊긴다. 회귀가 아니라 의미 교정이지만 재측정 없이는 비교할 수 없다.

**(R-d) `spillback_f1`.** 관측 도시부 커버리지를 늘리지 않으면 계속 0 이다. `detector_local_mapping` 확장과 재수집이 필요하다.

**(R-e) 크기 정합.** §4.2(3). 3~25 배 과대는 순위가 아니라 동역학 문제라 모델 수정 + 재수집 사이클이 필요하다.

### 5.3 성공 기준

1. c20 / c21 이 H=1/5/10/15 **네 지평 모두** 부호 일치.
2. anchor+vsl rho 가 **+0.9145 에서 변하지 않을 것** (변하면 수정이 의도 범위를 넘었다).
3. anchor+ramp rho 가 −0.3500 에서 변하지 않을 것 (R1 적용 전 기준).
4. G5 리포트 비트 동일.
5. 합성 8-seg 액션 CSV 비트 동일.
6. `spearman_rho ≥ 0.70` 은 **다중 셀에서** 확인될 때만 주장할 것.

---

## 6. 확인한 것과 추정한 것

### 6.1 확인 (코드 직독 또는 실행 재현)

| # | 사실 | 근거 |
|---|---|---|
| C1 | 공식 산출 재현. max abs 오차 4.55e-13, `spearman_rho` 0.144772, `top_action_pairwise` 29/56 | `ucprobe/uc_final_repro.py` vs `outputs/gates_v4_20260804/` |
| C2 | 어댑터가 모델 p1 ← minor, p2 ← major | `vissim_stackelberg_adapter.py:3366-3367` (동일 규약 `:2739-2740`, `:3437-3438`) |
| C3 | 모델의 off_ramp movement 12/12 가 p1 | `grid_topology.py:143-147, :183`; 런타임 cfg 덤프 |
| C4 | **플랜트 SC1001 의 링크 32 정지선 헤드는 EBL/EBT = MAJOR** | `modi_eval_rw_control.inpx` head 90030834/90030835/90030836 |
| C5 | **링크 32 는 본선 커넥터 10481(2→32)·10491(26→32)로만 유입** | 같은 `.inpx` |
| C6 | SC1001 MINOR(NB/SB) 접근 = 링크 37, 40 (둘 다 urban_road, NS) | 같은 `.inpx` + `link_roles.csv` |
| C7 | EB/WB → major, NB/SB → minor. major 가 사이클 앞 | `run_real_world_stackelberg_controller.vbs:787-798, :893-903` |
| C8 | 모델은 p1 이 사이클 앞 | `urban_queue_model.py:567` |
| C9 | 축 반전 시 green+offset rho −0.400 → +1.000, 전체 0.1448 → 0.7292, pairwise 0.5179 → 0.9821 | `ucprobe/uc_final_repro.py` |
| C10 | VSL 축 +0.9145, ramp 축 −0.3500 은 축 반전에 **완전 불변** | 같은 프로브. 후보 15 중 major≠minor 는 4 개뿐 |
| C11 | J = base + w_F·density_excess + w_ramp·ramp_queue. 나머지 3 항은 60 행 전부 0 | `leader.py:925-932`; `ucprobe/uc_final_ramp.py` |
| C12 | c20 ΔJ 분해 = base +626.67 + density +1499.74 + rampq −42.37 = +2084.04 | 같은 프로브 |
| C13 | 램프 구속 임계 650~620 vph/램프. 1364/1253/691 은 전부 불감대 (q_end 소수점까지 동일) | 같은 프로브 |
| C14 | 플랜트도 불감대. 미터링은 전달되나(682/626.5/345.5 vph) D 램프 큐가 안 자란다 | 액션 CSV + `state_*.json` |
| C15 | 관측 ramp ΔJ 는 지평마다 부호가 뒤집히고 단조성이 깨진다 | `g6_rows.json` |
| C16 | 관측 J 의 urban 성분 = off-ramp storage 뿐. urban link 4/29, movement 12/78 | `ucprobe/uc_final_ramp.py` |
| C17 | 관측 spillback 0/60. F1=0 은 구조적 | `g6_rows.json` + 점유율 계산 |
| C18 | v4 런에서 `:3769-3770` 조회는 항상 miss (id `SC1…SC1005` vs 키 `A_p1…F_p2`) | 액션 CSV + action JSON |
| C19 | 합성 8-seg 망은 minor = 램프축, 그리고 id 가 A~F 라 `:3769-3770` 이 적중한다 | `signal_manifest.csv`; `runs/8seg_sweet_w_20260714/action_nc_190w.csv` |
| C20 | `phase_map` 은 런타임 소비처가 0 건 | 전 저장소 grep. `generate_real_world_control_mapping.py:97` 이 쓰기만 함 |
| C21 | 기본 `control_mapping.json` 의 `sc_no: 1` 이 틀렸다. SC1 은 interface_head_count=0, 실제는 SC 1001 | `signal_controller_roles.csv` + `.inpx` |
| C22 | 반전 후 w_F=3.0 이 최선. 낮추면 전체 rho·pairwise 하락 | `ucprobe/uc_final_terms.py` |
| C23 | 총 green 재정규화는 |ΔJ| 를 c21 −10 %, c20 **+19 %** 로 비일관 변화시킨다 | `ucprobe/uc_final_mag.py` |
| C24 | 과제문 표는 H=5(300 s)다. H=1 에서는 c20 부호가 이미 일치 | `g6_rows.json` |

### 6.2 추정 (근거는 있으나 직접 확인하지 못했다)

| # | 추정 | 무엇이 부족한가 | 가리는 방법 |
|---|---|---|---|
| E1 | 모델의 D·F 노드가 플랜트 SC1001 에 대응한다 | 모델 신호명(A~F)과 매핑 id(SC*)의 대응표가 저장소에 없다. distributed 매핑에 `model_signal` 필드가 없다 | 매핑에 `model_signal` 을 채우고, `.inpx` 로 각 SC 의 접근 링크 역할을 대조 |
| E2 | 나머지 14 개 SC 의 축 대응도 major↔p1 이다 | `.inpx` 표(§1.2 프로브 출력)를 SC1001 외에는 역할 관점으로 해석하지 않았다. 이들은 freeway 접속이 없어 "램프축" 개념 자체가 없다 | `uc_inpx_axis.py` 출력을 SC 별로 검토. A·B·C 대응 노드는 **폐루프 전에 반드시** 확정 |
| E3 | 크기 과대(3~25 배)의 주원인은 off-ramp storage → 실효 차로 → 밀도 결합 이득 | Δfreeway 만 10.9 배 과대라는 것까지는 확인했으나 `ensure_freeway_lane_profile` 의 λ_eff 감쇠를 단독 계측하지 않았다 | λ_eff 를 고정한 반사실 rollout |
| E4 | 플랜트 D 램프 실수요가 691 vph 미만이다 | 대기대수 무성장에서 역추정했다. VehicleInput/route 유량을 직접 재지 않았다 | `.inpx` 의 `vehicleRouteStatic` / `timeIntervalVehVolume` 에서 램프 커넥터 유량 집계 |
| E5 | R1 후보(500/360/200)가 플랜트에서도 구속한다 | 모델에서만 확인했다. 플랜트 임계는 모른다 | E4 를 먼저 확정하거나, VISSIM 재실행(R-a) |
| E6 | c40/c41 관측 부호 불안정이 미시 시뮬레이션 잡음이다 | 반복 시드가 없어 잡음 크기를 추정할 수 없다 | 같은 후보를 다중 시드로 재수집 |

### 6.3 미확정으로 남기는 것

**부호 반전 지점 자체는 미확정이 아니다.** §1.2 의 `.inpx` 물증으로 확정했다.

미확정으로 남는 것은 **폐루프에서의 올바른 축 대응**이다. G6 는 15 개 SC 전부에 동일한 major/minor 를 강제하므로 SC 별 축 차이를 원리적으로 관측할 수 없다. 실컨트롤러는 노드별로 반대 부호의 비대칭을 낸다(D·F 는 p1 이 긴 쪽, A·B·C 는 p2 가 긴 쪽). 따라서 **G6 부호 수정은 지금 넣어도 되지만, 폐루프 적용은 E2 확정 이후**로 미뤄야 한다.

---

## 7. 권고 순서

1. **`.inpx` 축 표를 15 개 SC 전부로 확장한다** (V1 확장, VISSIM 불필요). E2 를 닫는다.
2. **§2.2 (a)~(g) 를 적용한다.** 매핑 파일 기반 분기, 기본값은 현행 동작.
3. **V2·V4·V5·V6 을 돌린다** (전부 VISSIM 불필요). 플랜트 액션·G5·불변 후보·합성망이 보존되는지.
4. **V3 shadow 재채점.** 기대값 §4.1.
5. **R2 (binding 게이트) 를 넣고 램프 축을 `axis_inactive` 로 표시한다.** 현재 −0.350 은 해석 불가값이므로 리포트에서 제외해야 한다.
6. **`cycle_sec` 를 늘린 뒤 R1 후보로 램프 축을 재수집한다** (VISSIM 필요).
7. **다중 셀로 rho 를 재확인한다** (VISSIM 필요). 0.729 의 마진은 얇다.
8. 크기 정합(E3)과 관측 도시부 커버리지(§4.4, R-d)는 별건 과제로 분리한다.

**하지 말 것.** w_F / w_ramp_queue 재가중을 축 수정과 묶지 마라 (§4.2(5)). 축이 고쳐지면 현행 가중치가 최선이다.


---

# 부록 — 주회로 독립 검증 (2026-08-04)

병렬 조사의 결론을 그대로 받지 않고, 부호 반전 사슬의 각 고리를 원본 파일에서 다시 확인했다.
아래 넷은 **직접 읽어 확인한 것**이다.

## 1. link 32 의 유입은 off-ramp 뿐이다

`network/real_world_gaepo_modi/modi_eval_rw_control.inpx` 를 파싱했다.

```
conn 10481 : link  2 @4092.3  ->  link 32 @1543.9     본선 FW_E 에서
conn 10491 : link 26 @3650.9  ->  link 32 @1270.0     본선 FW_W 에서
```

link 32 로 들어오는 커넥터는 이 둘뿐이고 둘 다 본선에서 온다.
대조로 MINOR 접근이라 지목된 link 37 / 40 의 유입은 각각 link 90/88/83, 425/47 로
본선과 무관한 부도로다. 즉 그 교차로에서 **간선(MAJOR) 축이 곧 freeway off-ramp 유출**이다.

## 2. 인터페이스 컨트롤러는 SC 1 이 아니라 SC 1001 이다

`evaluation/real_world_modi_inventory/signal_controller_roles.csv` (37 행).

```
   no  active  heads  freeway  interface  role
    1    true     14        0          0  urban_signal_controller            (구룡초교)
 1001    true     13        0          3  urban_freeway_interface_signal_controller
```

`interface_head_count > 0` 인 컨트롤러는 **전체에서 1 개**이고 그것이 SC 1001 이다.
그런데 `evaluation/real_world_modi_control/control_mapping.json` 의 `signals[0]` 은
`sc_no: 1` 이며 주석에 "SC 1 is the only controller inventoried with freeway-interface
signal heads" 라고 적혀 있다. **기본 매핑이 엉뚱한 교차로를 가리킨다.**

## 3. 모델은 램프 movement 를 p1 에 둔다

`NumSim-mine/src/models/grid_topology.py`.

```python
def _token_leg_dir(token: str) -> str:
    """approach/exit token의 leg 방위(phase 축 판정용). off*/on*은 램프 leg(S)다."""
    if token.startswith("off") or token.startswith("on"):
        return "S"
    return token
...
    axis_dir = _token_leg_dir(token)
    spec["phase"] = f"{node}_p1" if axis_dir in NS_AXIS else f"{node}_p2"
```

`off*` / `on*` 토큰은 방위 `S` 를 받고, `S` 는 `NS_AXIS` 에 속하므로 **phase = p1** 이다.

## 4. 어댑터는 p1 에 minor_green 을 넣는다

`evaluation/controllers/vissim_stackelberg_adapter.py:3366-3367`.

```python
control.green_times[f"{signal}_p1"] = float(minor_green_sec)
control.green_times[f"{signal}_p2"] = float(major_green_sec)
```

## 결론 — 사슬이 닫힌다

플랜트에서 freeway 접속 이동류는 **MAJOR** 이고(1), 그 교차로가 SC 1001 이며(2),
모델에서 같은 이동류는 **p1** 이고(3), 어댑터는 p1 에 **minor_green** 을 넣는다(4).
따라서 `major_green 57 -> 75` 는 모델 안에서 freeway 접속축을 **57 -> 25 로 조르는** 것으로
집행된다. 부호가 정확히 뒤집힌다. c20 과 c21 이 대칭적으로 어긋난 것이 이것으로 설명된다.

## 주의 — 전역 스왑은 처방이 아니다

어댑터의 규칙(major<-p2)은 **간선 교차로에서는 맞다.** 일반 도시부 교차로의 MAJOR 는
E-W 간선이고 모델은 그것을 p2 로 서비스한다(2026-06-30 주석 참조).
틀린 것은 **freeway 인터페이스 컨트롤러 한 곳**이다. 그 교차로에서만 MAJOR 축이 램프이기 때문이다.
전역으로 뒤집으면 SC 1001 은 고쳐지고 나머지 36 개 간선 신호가 깨진다.
수정은 **컨트롤러별로** 해야 하며, 판정 기준은 "그 교차로의 MAJOR 접근이 램프인가 간선인가" 다.
`signal_controller_roles.csv` 의 `interface_head_count` 가 그 판정에 쓸 수 있는 값이다.

G6 채점만 놓고 보면 목적함수가 freeway 상태만 재므로 전역 스왑이 rho 를 올리는 것처럼 보이지만,
운영 컨트롤러에는 그대로 쓰면 안 된다.

## 정정 — 램프 "30~300 배 과소" 는 성립하지 않는다

주회로가 앞서 그렇게 적었으나 틀렸다. 관측 ΔJ 를 지평별로 보면 부호가 뒤집힌다.

```
            c10_1364   c11_1253    c12_691
H1            -7.00     -25.00     -26.00
H5          +135.11     +22.13     +21.67
H10          +68.81    +103.85    -150.74
H15         -473.23    -137.17    -437.14
```

-473 에서 +135 까지 흔들린다. 분모가 안정적이지 않으므로 배율을 말할 수 없다.
모델 예측은 오히려 작고 단조롭다(0.15 -> 0.99, 1.31 -> 23.42).
병렬 조사의 "불감대" 진단(구속 임계 650~620 vph/램프, 시험 미터율은 전부 그 위)이 타당하다.
