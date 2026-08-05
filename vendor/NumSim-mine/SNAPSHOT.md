# 모델 소스 스냅샷 (감사용 사본)

이 디렉터리는 **교통 모델·컨트롤러 소스의 사본**이다. 원본이 아니다.

| | |
|---|---|
| 원본 레포 | https://github.com/Ming2you/Numerical-Sim.git |
| 브랜치 | `freeway-zone-followers` |
| 커밋 | `35a5c82` — "NS_AXIS 대각축 정정 + 램프 큐 상한을 램프별로" |
| 복사 시각 | 2026-08-05 |
| 범위 | `src/` 전체 + `README.md` / `requirements.txt` / `AGENTS.md` |
| 제외 | `outputs/`(263 MB 런 산출물), `work/`, `__pycache__`, `.git` |

## 왜 사본을 두는가

`PLANT_FIDELITY_AUDIT_REQUEST.md` 의 감사는 **하네스(이 레포)와 모델을 같이** 봐야 한다.
두 레포를 따로 클론하게 하는 대신, 감사 시점 모델을 이 레포 안에 고정해 클론 하나로
전체를 재현할 수 있게 했다.

## 주의 — 이 사본을 수정하지 말 것

런타임이 실제로 import 하는 모델은 이 사본이 아니다.
`evaluation/controllers/vissim_stackelberg_adapter.py:24` 가 `NUMSIM_REPO_ROOT` 환경변수를
보고, 없으면 절대경로 `C:/Users/alsrj/Desktop/학술/찐찐막/Claude/NumSim-mine` 로 폴백한다.

- **코드 수정은 원본 레포(Numerical-Sim)에서** 한다. 여기 고치면 갈라진다.
- 이 사본으로 실행해 보려면 `NUMSIM_REPO_ROOT` 를 이 디렉터리로 지정한다.

```bash
export NUMSIM_REPO_ROOT="$(pwd)/vendor/NumSim-mine"   # 저장소 루트에서
```

## 감사에서 특히 볼 파일

| 파일 | 무엇 |
|---|---|
| `src/models/grid_topology.py` | leg 인접 → movement·내부링크 유도. `NS_AXIS`(31행), `leg_base_dir`, phase 배정(225행 부근) |
| `src/models/urban_queue_model.py` | 도시부 substep 동역학. `_phase_green_fraction`(541행) — **phase 가 비면 1.0 반환 = 항상 녹색** |
| `src/models/state.py` | `NetworkConfig`. `ramp_queue_max_veh_by_ramp` / `ramp_queue_cap`, `boundary_leg_vehicles`, `objective_urban_vehicles` |
| `src/controllers/leader.py` | `_state_accumulation_base`(경계 leg 제외), `_ramp_queue_pressure` |
| `src/controllers/f1_wu_faithful_follower.py` | 램프 큐 상한이 물리로 들어가는 지점(517행 부근) |
| `src/controllers/freeway_follower.py` | 램프 큐 상한 + overflow |
| `src/config/default.yaml` | 6노드 참조 격자. `signals`/`uncontrolled_nodes`(노드 E), 대각 방위 문자열 **0건** |
