# Codex 작업 의뢰 — 어댑터 정본화와 배선 복구

작성 2026-08-27 · 브랜치 `codex/plant-fidelity-v2-1` · 작성자 Claude (Opus 5)

이 문서의 모든 수치는 아래 "재현" 절의 명령으로 다시 뽑을 수 있다. 추론이 아니라 측정값만 적었고,
측정 방법에 결함이 있었던 항목은 그렇게 표시했다.

---

## 0. 왜 이 작업이 필요한가

`evaluation/controllers/` 에 어댑터가 **19벌** 있다. 팔(arm)을 하나 만들 때마다 8천 행짜리
파일을 통째로 복사해 한두 함수만 고치는 방식이 누적된 결과다.

```
어댑터 19벌 · 총 155,827행 · 최대 8,843행
최상위 함수 이름 217개
  2벌 이상에 정의된 것        195개
    그중 전부 바이트 동일      178개
    구현이 갈린 것            17개   <- 문제
```

그 결과 두 가지가 깨졌다.

**(1) 실험 팔들이 비교 불가능하다.** TTT 사다리의 11개 팔이 서로 다른 어댑터 9개, 서로 다른
sha 10종으로 돌았다. "A 가 B 보다 119.7 veh·h 좋다"가 설정 차이인지 코드 차이인지 분리되지 않는다.

| 런 | 어댑터 | sha256(앞 8) |
|---|---|---|
| default_20260825 | `vissim_stackelberg_adapter.py` | `2b81231d` |
| mainline_20260825 | `..._mainline_20260825.py` | `785d58ca` |
| tau_20260826 | `..._tau_20260825.py` | `797a15e0` |
| tauoff_20260826 | `..._tauoff_20260825.py` | `2d38c2a4` |
| allfix_20260825 | `..._allfix_20260825.py` | `b94d73c7` |
| offarm_20260825 | `..._offarm_20260825.py` | `988fa820` |
| map4etau_20260826 · map4ftau_20260826 | `..._map4e_20260826.py` | `fc1af2b7` |
| dualg0p02 · dualg0p1_20260826 | `..._npband_20260826.py` | `77b928ac` |
| slew15_20260826 | `..._slew_20260826.py` | `a9d77060` |
| merge_20260824 | `..._merge_20260824.py` | `d3bd0709` |
| nocontrolstep_20260826 | `..._qbind_20260826.py` | `ae2ef63e` |
| plantfix_20260827 · bstoA_20260827 | `..._qbind_20260826.py` | `31ba2242` |

전체 154런 기준 어댑터 파일 15개 / sha 47종.

**(2) 수정이 한 벌에만 반영되고 다른 벌로 안 넘어간다.** 갈린 17개 함수 전체:

| 함수 | 정의된 벌 | 서로 다른 구현 |
|---|---|---|
| `main` | 19 | **10** |
| `install_config_switches` | 11 | **9** |
| `build_priced_wu_link_controller` | 19 | 7 |
| `build_local_observation_summary` | 19 | 5 |
| `control_to_json_dict` | 19 | 4 |
| `write_action_csv` | 19 | 3 |
| `traffic_state_from_vissim` | 19 | 3 |
| `install_price_worker_bootstrap` | 19 | 3 |
| `profiled_demand_rates` | 19 | 2 |
| `native_fixed_control` | 19 | 2 |
| `load_signal_group_actuation_plan` | 19 | 2 |
| `install_monitor_fixed_signal_runtime_patch` | 19 | 2 |
| `build_patched_phase_green_fraction` | 19 | 2 |
| `install_phased_price_local` | 13 | 2 |
| `_stopped_storage_fraction` | 13 | 2 |
| `_stopped_split_enabled` | 13 | 2 |
| `install_signal_aware_green_box` | 12 | 2 |

---

## 1. 정본 후보와 결손

`vissim_stackelberg_adapter_qbind_20260826.py` (8,843행) 가 가장 최신이고 기능이 가장 많다.
다만 **정본이 되려면 결손 14개를 흡수해야 한다.**

qbind **에만** 있는 함수 11개 (다른 벌로 안 넘어간 것):
```
_boundary_inflow_seed_enabled   _dead_phase_beta_zero_enabled   _midblock_stopline_links
_movements_by_origin            _queue_origin_binding_enabled   _storage_length_m
_tau_length_cap_enabled         apply_dead_phase_beta_zero      install_price_worker_runtime_patches
install_tau_length_cap_patch    seed_boundary_inflow
```

qbind 에 **없는** 함수 14개 (다른 팔에만 있는 것 — 병합 시 소실 주의):
```
_apply_offset_slew              _native_fixed_cycle_safe_signals   _nin_ref_enabled
_np_state_band_enabled          _offset_slew_sec                   _subwindow_enabled
build_subwindow_fraction_table  install_dual_scale_arm             install_forced_native_offsets
install_nin_reference_fix       install_np_state_band              install_offset_arm
```
(2개는 헬퍼로 위 목록에 흡수됨)

출처: `_slew_20260826`(offset slew), `_subwin_20260824`(subwindow), `_npband_20260826`(np band),
`_dual_20260826`(dual scale), `_ninref_20260825`(nin reference), `_offset_20260824`(offset arm).

---

## 2. 배선이 끊긴 채로 살아 있는 결함

### 2-A. perimeter movement 용량이 안 걸려 있다 (실제 런에 영향 있음)

`install_movement_capacity_by_lanes` 가 **internal 184개만** 차로비례 용량을 받고,
perimeter 184개(boundary_in 116 · boundary_out 50 · off_ramp 18)는 전역 스칼라 1400 에 남는다.

```
internal    184개    207 ~ 826 veh/h   (per_lane 206.53 x 차로수)
perimeter   184개    1400 veh/h 고정
                     -> 6.8배 비대칭
```

방류가 `min(available, T_u_h x green x cap_flow)` 로 cap 에 **선형**이라(`urban_queue_model.py:1148`),
리더가 현시를 고를 때 경계 접근로에 구조적으로 유리하게 작용한다.

원인은 스위치다. `urban.capacity.perimeter` 의 기본값이 `"off"` 다
(`vissim_stackelberg_adapter_qbind_20260826.py:2399`). 값은 `off` / `resolved` / `all`.

2026-08-24 에 코드 경로, vendor 수정(`urban_queue_model._movement_capacity_flow` 의 perimeter
분기가 `per_movement` 를 읽고 안 쓰던 것), 회귀 테스트
(`test_perimeter_movement_honours_per_movement_capacity`), 그리고 A/B 팔 두 개까지 다 만들었다:

- `evaluation/configs/real_world_modi_pstack_distributed_core17legs4b_cap_resolved_20260824.json` (`"perimeter": "resolved"`, 물리 확인된 78개만)
- `evaluation/configs/real_world_modi_pstack_distributed_core17legs4b_cap_all_20260824.json` (`"perimeter": "all"`, 미해결 212개는 같은 turn 중앙값)

**두 팔 다 한 번도 실행되지 않았다** (`evaluation/runs/` 에 결과 없음). 그리고 2026-08-25 에
`default_20260825` 가 새 기준 스택이 되면서 이 항목이 실리지 않은 채 넘어갔다. 지금 체인
(`plantfix_20260826` -> ... -> `default_20260825`) 어디에도 `urban.capacity.perimeter` 가 없다.

참고: `outputs/movement_lanes_perimeter_20260824.json` 에 movement 78개가 있고, 병합 후
이름과 일치하는 것은 66개다. `resolved` 팔이면 66개가 적용된다.

### 2-B. FD 재적합값이 컨트롤러에 도달하지 않는다

```
현재 cfg.network       v_free 100.0 · rho_crit 33.500 · capacity 4000.0
2026-08-02 재적합값     v_free 119.505 · rho_crit 16.354 · capacity 4914
```

무제어 런 전수 측정에서 freeway 세그먼트 밀도는 수요를 1.4배로 올려도 **최대 32.7** 이라
현행 `rho_crit` 33.5 를 **한 번도 넘지 않는다(0.0%)**. 재적합 기준이면 16.5~18.5% 가 초과다.

| 런 | 중앙 | p99 | 최대 | ρ>33.5 | ρ>16.354 |
|---|---|---|---|---|---|
| 무제어 1.0× | 8.4 | 20.8 | 24.1 | 0.0% | 3.6% |
| fw12_ramp1 | 10.0 | 26.4 | 32.7 | 0.0% | 8.1% |
| fw14_ramp1 | 11.9 | 31.2 | 32.7 | 0.0% | 16.5% |
| fw14_ramp2 | 12.2 | 31.7 | 32.7 | 0.0% | 18.5% |

즉 현행 FD 로는 VSL 이 작동할 물리적 근거가 없다. 오프라인 검사에서 재적합값을
`config_overrides.network` 로 먹이면 미터링은 반응했고(R_F_W 중앙 1721 -> 1529, 최소 1062)
VSL 은 72/72 전부 120 유지였다.

같이 확인된 인접 항목 (전부 꺼짐 / 중립값):
```
capacity_drop_discharge_phi   1.0     (= 용량 강하 없음)
capacity_drop_anticipation    False
metanet_delta_merge           0.0     (= merge 교란 없음)
vsl_fd_two_branch             속성 없음
rho_crit_for_vsl              속성 없음
```

`calibration_override` 로 넣으려던 시도는 실패한다 — 대상 섹션이 런의 calibration 파일에 없다.
`config_overrides.network` 경로는 동작한다.

### 2-C. 분석 하네스에 단일 진입점이 없다 (오늘 실제로 오측정을 냈다)

러너 부트스트랩은 설치 함수를 **순서대로 8회** 부른다
(`vissim_stackelberg_adapter_qbind_20260826.py:8309~8341`). 주석이 순서 자체를 고정한다 —
"회전분율은 병합보다 먼저", "병합은 용량 설치 앞", "동시현시 배율은 용량 맵 뒤".

```python
install_adapter_calibration_fingerprints(cfg, tuning)
install_vissim_calibration_runtime_patches(cfg, calibration)
install_tau_length_cap_patch(cfg)
apply_dead_phase_beta_zero(cfg)
install_vsl_metanet_rollout_runtime_patch(cfg, tuning)
install_urban_stopline_storage(cfg, tuning)
install_measured_turn_beta(cfg, tuning)              # 병합보다 먼저
detector_mapping, _ = install_merged_movements(cfg, tuning, detector_mapping)
install_movement_capacity_by_lanes(cfg, tuning)
install_native_signal_structure(cfg, tuning)         # 용량 맵 뒤
install_measured_movement_capacity(cfg, tuning, state_json, prev_action)
```

이걸 재현하는 공개 함수가 없어서, 오프라인 분석 스크립트가 매번 손으로 일부만 골라 부른다.
2026-08-27 에 `install_merged_movements` 와 용량 설치 3종이 빠진 채로 측정이 돌아,
movement 수를 **474(실제 368)**, movement 용량을 **전부 1400(실제 internal 207~826)** 으로
잘못 읽었다. 그 위에서 세운 분석 결론 여러 개가 무효가 됐다.

---

## 3. 의뢰 내용

### 3-1. 조사 (먼저)

1. 어댑터 19벌의 갈린 함수 17개에 대해, 각 구현이 **왜** 갈렸는지 확인하라. 팔 전용 기능인가,
   버그 수정이 한 벌에만 반영된 것인가, 아니면 단순 표류인가. 함수마다 판정과 근거를 남긴다.
2. `main` 10종과 `install_config_switches` 9종을 특히 상세히. 이 둘이 나머지 배선을 결정한다.
3. qbind 에 없는 14개 함수가 각각 어떤 config 키로 켜지는지 확인하고, 그 키가 지금 체인
   어디에 있는지 조사하라. **2-A 처럼 "코드는 있는데 스위치가 꺼진 채 잊힌" 항목이 더 있는지가
   이 조사의 핵심 산출물이다.**
4. `evaluation/configs/` 전체를 훑어 만들어졌지만 한 번도 실행되지 않은 팔을 목록화하라
   (`evaluation/runs/` 대조). `cap_all` / `cap_resolved` 가 그 예다.

### 3-2. 정본화

1. `vissim_stackelberg_adapter_qbind_20260826.py` 를 기준으로 정본 어댑터를 만든다.
   이름은 `vissim_stackelberg_adapter.py` (기존 파일 대체) 또는 새 정본명 — Codex 판단.
2. 갈린 17개 함수는 **팔 전용 분기를 config 키로 흡수**해 하나의 구현으로 합친다.
   키가 없으면 기존과 비트 동일한 경로가 되도록 한다(no-op 기본값). 이 프로젝트의 기존
   관례(`install_tau_length_cap_patch` 등)가 그렇다.
3. qbind 에 없는 14개 함수를 정본으로 가져오되, 전부 기본 꺼짐으로 둔다.
4. **`bootstrap_for_analysis(state_json=None, tuning_path=None)` 를 공개 함수로 추가**해
   위 8단계 설치 순서를 한 번에 재현하게 한다. 러너의 `main` 도 이 함수를 쓰도록 바꿔서
   순서가 두 곳에 중복되지 않게 한다. 반환값에 설치 메타를 포함해
   `movement_merge_enabled` · `movement_capacity_by_lanes_count` 등으로 검증 가능하게 한다.
5. 구버전 어댑터 18벌을 삭제한다. **단 삭제 전에 아래 6절을 반드시 읽을 것.**

### 3-3. 배선 복구

1. `urban.capacity.perimeter` 를 정본 config 체인에서 명시적으로 결정하라. 값을 정하는 것이
   아니라, **결정이 기록되도록** 하는 것이 목적이다. 기본 `off` 를 유지하더라도 그 이유를 config
   notes 에 남긴다. A/B 를 돌릴지는 사람이 정한다 — Codex 는 실행하지 말 것.
2. FD 파라미터(2-B)도 같은 방식으로. `config_overrides.network` 경로가 유효하다는 것만 확인하고,
   값을 바꾸는 것은 사람 결정으로 남긴다.

---

## 4. 수용 기준

- [ ] 정본 어댑터 1벌 + 삭제된 18벌. `evaluation/controllers/vissim_stackelberg_adapter*.py` 가 1개.
- [ ] 정본으로 `nocontrolstep_20260826` 과 동일 조건 스모크 런이 성공하고, 결정 JSON 의
      `movement_merge_after == 368` · `movement_capacity_by_lanes_count == 184` 를 만족한다.
- [ ] 갈린 17개 함수 각각에 대해 판정과 근거가 문서로 남는다.
- [ ] 켜지지 않은 config 키 목록이 문서로 남는다(2-A 유형).
- [ ] `bootstrap_for_analysis` 가 존재하고, 러너 `main` 이 그것을 사용한다.
- [ ] 기존 팔의 config 키가 정본에서 전부 인식된다(알 수 없는 키가 있으면 오류를 내도록).

---

## 5. 재현 명령

모든 수치는 아래로 재현된다. 파이썬은 `C:/ProgramData/Anaconda3/python.exe`.

**어댑터 중복 실태**
```python
import ast, hashlib
from collections import defaultdict
from pathlib import Path
files = sorted(Path("evaluation/controllers").glob("vissim_stackelberg_adapter*.py"))
fn = defaultdict(dict)
for f in files:
    src = f.read_text(encoding="utf-8", errors="replace"); body = src.splitlines()
    for n in ast.parse(src).body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            seg = "\n".join(body[n.lineno-1:(n.end_lineno or n.lineno)])
            fn[n.name][f.name] = hashlib.sha256(seg.encode()).hexdigest()[:8]
diff = {k: v for k, v in fn.items() if len(set(v.values())) > 1}
print(len(files), len(fn), len(diff))
```

**팔별 어댑터 sha** — `evaluation/runs/*/run_provenance_*.json` 의 `files.adapter.{path,sha256}`.

**설치 후 상태(정본 하네스)** — 러너 부트스트랩과 같은 순서로 설치 함수를 부른 뒤
`len(cfg.network.urban_movements)` (368 기대),
`len(cfg.network.movement_capacity_by_movement_veh_h)` (184 — 이게 368 이 되는 것이 2-A 의 목표),
`cfg.network.v_free / rho_crit` (100.0 / 33.5).

**freeway 밀도** — `evaluation/runs/*/decisions_*/state_*.json` 의 `freeway_segments`,
`density = count / (length_km * lanes)`, `sim_sec >= 900` 만.

---

## 6. 건드리지 말 것 (CLAUDE.md 및 사용자 지시)

- `git add -A` 금지. 경로를 명시해 스테이징한다.
- 원본 `.sig`, 원본 `.inpx`, 프로덕션 config, `reports/` 를 덮어쓰지 않는다.
- `vendor/` 직접 수정은 원칙적으로 금지. 2-A 의 vendor 수정은 이미 반영돼 있으니 추가 수정 불필요.
- push 는 별도 승인 사항이다.
- **어댑터 삭제 전에**: `evaluation/runs/*/run_provenance_*.json` 이 참조하는 어댑터 파일은
  기존 런의 증거다. 삭제하면 과거 런의 코드 출처를 잃는다. 삭제 대신
  `evaluation/controllers/_superseded_20260827/` 로 이동하고, 이동 목록과 sha 를 문서로 남기는 편이
  안전하다. 이 프로젝트에 `outputs/_superseded_20260819/` 선례가 있다.
- 리더 목적함수에서 TTT 와 lever 한계가격을 끄는 것은 금지(사용자 지시). 가중치 조절은 허용.
- 현시 가격은 임의로 끄지 말 것(사용자 지시).
- SG 9 이상은 미드블록이다. 본선은 1~8.

---

## 7. 이 문서에서 신뢰도가 낮은 것

정직하게 밝힌다. 아래는 **측정 결함이 확인되어 무효**이므로 근거로 쓰지 말 것.

2026-08-27 에 병합·용량 설치가 빠진 하네스로 낸 수치 전부:
- movement 큐 분포, "혼잡 원점 6개 = 20 movement", "현시 용량 110배"
- 현시 한계이득 상관(용량 r=+0.144 / 큐 r=+0.526)
- 녹색 좌표탐색 결과(−0.96% ~ −2.19%) 및 SC1002 축 궤적

반대로 **유효한 것**은 실제 VISSIM 런에서 나온 것들이다 — TTT 계보, 전수 차량 기반 혼잡 판정,
freeway 밀도 분포, 차량번호 추적 유입/유출. 이건 러너를 탔으므로 설치가 전부 적용된 상태다.
