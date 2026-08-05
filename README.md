# VISSIM ↔ Numerical-Sim 통합 워크스페이스

PTV Vissim 2020 (SP14) 플랜트와 Stackelberg MPC 계층 제어 모델을 COM 으로 결합해
컨트롤러를 라이브 평가한다.

> **지금 이 저장소를 처음 여는 사람에게 —**
> 현재 진행 중인 작업은 **플랜트 충실도 검증**이다. 무엇을 어떻게 만들었고 무엇이 아직
> 불확실한지는 [`PLANT_FIDELITY_AUDIT_REQUEST.md`](PLANT_FIDELITY_AUDIT_REQUEST.md) 에
> 전부 정리돼 있다. 그 문서부터 읽는 것이 가장 빠르다.

---

## 현재 구성 (2026-08-05)

| | |
|---|---|
| 플랜트 | `network/real_world_gaepo_modi/modi_eval_rw_control.inpx` — **개포동 실제 도로망** |
| 규모 | 링크 1,219(일반 448 + 커넥터 770), 신호제어기 50개(active 42) |
| 모델 | 41노드 = 통제 15 + 모니터 26, movement 1,422, 링크 저류 302 |
| 결정 주기 | 60 초 |
| 모델 소스 | [`vendor/NumSim-mine/src/`](vendor/NumSim-mine/) — 원본은 [Numerical-Sim](https://github.com/Ming2you/Numerical-Sim) `freeway-zone-followers` |

결합 경로.

```
PTV Vissim 2020
   └ network/real_world_gaepo_modi/modi_eval_rw_control.inpx
        ↕ COM
   scripts/run_real_world_stackelberg_controller.vbs      전 차량 스캔 + 신호 기입
        ↕ state JSON / action JSON
   evaluation/controllers/vissim_stackelberg_adapter.py   관측 → 모델 상태 투영
        ↕
   vendor/NumSim-mine/src/                                모델 rollout + 컨트롤러
```

관측은 `Vissim.Net.Vehicles.GetMultiAttValues("Lane"/"Pos"/"Speed")` 로 **전 차량**을 읽고,
링크별로 집계해 state JSON 으로 내보낸다.

### 플랜트 모사 현황

| 지표 | 값 |
|---|---:|
| 도시부 포착률 (리더 목적함수 기준) | 76.8 % |
| 도시부 포착률 (투영 기준) | 96.3 % |
| 고속도로 포착률 | 100.0 % |

도시부 링크 1,205개가 **분할**로 귀속된다 — 플레이어 957 + freeway follower 22 + 출구 226,
중복 0·누락 0. 규칙은 "하류로 훑어 처음 만나는 것"(신호 정지선 / 고속도로 / 종단).

**미해결 중 가장 큰 것**: 모니터 전용 26개 SC 의 movement 는 `phase=''` 이라
`urban_queue_model._phase_green_fraction` 이 1.0 을 돌려준다 — 즉 **그 교차로들엔 빨간불이
없다**(movement 의 47.8%, 관측 차량의 40.7%). 나머지 미해결은 감사 문서 6장 참조.

---

## 실행

**PowerShell 에서 실행한다.** 한글 경로 때문에 Git Bash 는 인코딩이 깨진다.
`.ps1` 은 순수 ASCII 여야 한다(BOM 없는 파일을 PowerShell 5.1 이 CP949 로 오독한다).

```powershell
powershell -File scripts\run_real_world_single_watchdog_distributed_core15n41.ps1 `
  -Name <run_name> -Controller diagnostic-fixed57 -Seed 13 `
  -SimPeriod 3000 -StateLogIntervalSec 300 -OutDir evaluation\runs\<dir>
```

`-Controller` 에 `stackelberg` 를 주면 실제 P-Stack 이 돈다. `diagnostic-*` 은 고정 액션이라
플랜트 궤적이 모델 변경에 불변이므로 재채점에 쓴다.

**VISSIM 배치는 반드시 한 번에 하나만.** 워치독의 `Kill-Vissim` 이 모든 VISSIM200/cscript
프로세스를 죽여서, 동시에 돌리면 서로를 파괴한다.

**런이 이상하면 `network/real_world_gaepo_modi/modi_eval_rw_control.err` 를 먼저 읽어라.**
정적 경로 하나가 끊겨도(`Static Vehicle Route ... is not complete`) VISSIM 은 시뮬을 시작
직후 중단·리셋한다. 그때 증상은 `actual_sim_sec=0` 고정과 `FAILED_SET_SIGSTATE` 수만 건인데,
**그 신호 오류들은 원인이 아니라 결과다.**

### 아티팩트 생성 파이프라인

네트워크를 고쳤으면 이 순서로 다시 만든다.

```bash
python scripts/inventory_real_world_modi.py --inpx <inpx>            # SC·링크 인벤토리
python scripts/derive_intersection_adjacency.py --network <inpx> --json-out <adj.json>
python scripts/assign_links_to_players.py --network <inpx> --json-out <assign.json>
python scripts/derive_urban_storage_capacity.py --links-csv <bottleneck_links.csv> --json-out <cap.json>
python scripts/derive_ramp_queue_capacity.py --capacity-json <cap.json> --write
python scripts/generate_real_world_distributed_players.py --selector core15 --sc1-coupling on \
    --slug <slug> --stamp <YYYYMMDD> \
    --adjacency-json <adj.json> --storage-capacity-json <cap.json> --link-assignment-json <assign.json>
```

### 검증

```bash
python scripts/verify_phase_axis_assignment.py --adjacency <adj.json>     # phase 축 vs 실측 방위각
python scripts/verify_urban_topology_merge.py --state-json <state.json> \
    --link-assignment-json <assign.json> --case "<label>:<tuning>:<mapping>:<detector>"
```

`verify_phase_axis_assignment.py` 는 회귀 검증까지 확인해 두었다 — 수정본 123/123 PASS,
`NS_AXIS` 를 되돌리면 34.5% FAIL.

---

## 저장소 구성

```
network/real_world_gaepo_modi/   VISSIM 플랜트 (.inpx 10개, 신호 프로그램 .sig 41개)
scripts/                         COM 러너·워치독·인벤토리·유도·검증 (134개)
evaluation/controllers/          어댑터 (vissim_stackelberg_adapter.py)
evaluation/real_world_modi_inventory/    SC·링크 roles CSV (inpx 에서 기계 추출)
evaluation/real_world_modi_control_distributed_20260728/   control/detector 매핑
evaluation/configs/              튜닝 config
evaluation/calibration/          캘리브레이션 json
evaluation/generated/            VBS 전역 config (생성물)
harness/g6/                      G6 채점
outputs/                         유도 산출물·게이트 리포트 (outputs/README.md 로 현행/이력 구분)
vendor/NumSim-mine/src/          모델 소스 스냅샷 (수정 금지, SNAPSHOT.md 참조)
context-notes.md                 작업 중 내린 결정과 근거 (계속 append)
checklist.md                     할 일
```

`.gitignore` 로 제외되는 것 — `evaluation/runs/`(런 산출물, 대용량), `**/decisions_*/`,
`*.inp0`·`*.bak_*`(VISSIM 자동/수동 백업), `*.err`, `__pycache__`.
**즉 위의 포착률 수치를 재현하려면 런을 직접 돌려야 한다.**

---

## 이전 단계 아카이브 (2026-07, 8-seg 가상 격자)

현재 플랜트로 넘어오기 전에는 `network/modi_eval_vsl_8seg.inpx`(A–F 6교차로 가상격자 +
방향당 8세그먼트 freeway)로 작업했다. 결정 주기 180초, 러너는
`scripts/run_stackelberg_vissim_controller_8seg.vbs`. **그 구성의 수치는 현재와 비교 불가**다.

그때 얻은 교훈 중 지금도 유효한 것.

1. **파생 문서 말고 원본에서 재구축.** 감사 diag 표가 경계 유출 β 를 조용히 제외하고 있었고
   그걸 신뢰해 모델이 mass 를 내보낼 출구를 몰랐다(urban bias −474). route manifest 원본에서
   다시 만들어 해결.
2. **구조 수정 전에 오프라인 replay 로 가설을 죽여라.** "movement 용량 상수가 병목" 가설은
   replay 에서 4% 효과로 기각됐다.
3. **PFO 의 urban green 채널은 이 플랜트에서 부러져 있다.** 상태 예측이 정확해진 뒤에도
   실패했다(+21.77%). 원인은 예측이 아니라 green 응답 민감도 — 모델이 green 재배분 이득을
   과대평가해 major 축을 굶긴다. green 응답 곡선 재캘리브레이션이 남은 구조 타깃이다.
4. **운영 gotcha**: 한글 경로 CP949 오독(무BOM PS 스크립트 27회 전멸), PowerShell 함수
   반환값이 파이프라인을 오염시켜 실패가 "all OK" 로 오보, here-string 을 네이티브 exe 에
   넘기면 조용히 실패, VISSIM COM 의 무증상 hang(→ 워치독 필수).
