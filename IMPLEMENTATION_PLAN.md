# 구현 작업지시서 v2 — 플랜트 충실도 복구

작성 2026-08-05. 수행자: Codex. 순서대로 진행한다.

**v1 대비 개정** — Codex 검토 지적 8건을 전부 수용했다. 변경 내역은 부록 B.

이 문서는 [`PLANT_FIDELITY_AUDIT_REQUEST.md`](PLANT_FIDELITY_AUDIT_REQUEST.md)(감사 요청)와
그 결과인 [`reports/plant_fidelity_audit.md`](reports/plant_fidelity_audit.md)(판정 **불가**)의
후속 실행 계획이다. **그 판정을 뒤집는 것이 목표다.**

---

## 0. 이 문서를 읽는 법

### 0.1 근거 등급

- **[실측]** — 메인 세션이 직접 실행해 확인. 명령과 출력이 대화 기록에 있다.
- **[에이전트]** — 서브에이전트 보고. 교차검토는 거쳤으나 메인 세션이 재현하지 않았다.
- **[감사]** — Codex 감사 보고서.

**[에이전트] 등급은 착수 전에 재현하라.** 재현 실패 시 그 항목의 후속을 중단하고 보고한다.

### 0.2 절대 제약

- **VISSIM 배치는 한 번에 하나만.** 워치독 `Kill-Vissim` 이 모든 VISSIM200/cscript 를 죽인다.
- `.ps1` 은 **순수 ASCII**. PowerShell 5.1 이 BOM 없는 파일을 CP949 로 오독해 한글 경로를 깬다.
- PowerShell here-string 을 네이티브 exe 에 넘기지 마라 — **조용히 실패**한다.
- **런이 이상하면 `network/real_world_gaepo_modi/modi_eval_rw_control.err` 를 먼저 읽어라.**
  정적 경로 하나가 끊겨도 VISSIM 은 시작 직후 중단·리셋한다. `actual_sim_sec=0` 고정과
  `FAILED_SET_SIGSTATE` 수만 건은 **결과지 원인이 아니다.**
- **네트워크(`.inpx`) 변경은 코드·문서와 분리해 단독 커밋**하고
  `reports/network_change_*.md` 형식의 고지를 남긴다. baseline hash 가 바뀌기 때문이다.

### 0.3 우리가 실제로 저지른 오류

전부 **"입력이 맞는지 확인하지 않아서"** 생겼다. 착수 전 각 항목의 입력 파일 정체를 확인하고
인용된 수치를 재계산하라.

1. **`.sig` 를 SC 번호로 찾았다.** `개포동 test-bed{N}.sig` 의 N 이 SC 번호라고 가정했으나
   **50개 중 18개가 다르다** [실측]. SC5→test-bed7, SC6→test-bed9, SC11→test-bed3, SC12→test-bed5.
   이 오류로 "SC12 는 1현시", "14개 SC 영구 적색", "`.sig` 는 구조의 출처로 못 쓴다" 가 **전부 틀렸다.**
   **반드시 `signalController/@supplyFile2` 로 매핑하라.**
   정본 매핑표는 `reports/signal_reference_20260805.json` 의 `sc_to_sig`.
2. **glob 으로 엉뚱한 `.inpx` 를 파싱했다.** 정본은 `modi_eval_rw_control.inpx` 다.
3. **방향을 뒤집어 쟀다.** `SC1001_to_SC1004` 를 "물리 8,896대 vs 모델 120대" 라고 보고했으나
   8,896은 반대 방향 회랑이었다. 실제 접근로는 421 m, 143.5대다.
4. **증상을 원인으로 보고했다.** 신호 COM 실패 28,056건은 시뮬이 안 도는 결과였다.
5. **에이전트 진단을 무검증으로 전달했다.**
6. **브랜치 분기를 확인 안 하고 계획을 썼다.** v1 이 참조한 감사 산출물이 그 브랜치에 없었다.
7. **vendor 사본을 두고 원본을 미커밋으로 뒀다.** 스스로 경고해 놓고 갈라뜨렸다.

---

## S0. 기반 고정 — **완료**

Codex 지적 1·2·8. 메인 세션이 수행했다. 아래는 그 기록이며 남은 항목만 처리하면 된다.

### S0-1. 감사 커밋 통합 — 완료

`e737bf7`(작업지시서)과 `eec5d9e`(감사 구현)는 `dc216be` 에서 갈라진 **형제 커밋**이었다 [실측].
그래서 v1 의 A/J/K 가 참조하는 산출물이 브랜치에 하나도 없었다.
`34fb88e` 로 머지했다(자동 머지, **충돌 0건**).

통합으로 들어온 것 — `reports/link_assignment_ties.json`, `scripts/run_plant_fidelity_matrix.ps1`,
`scripts/audit_plant_fidelity.py`, `evaluation/controllers/fixed_signal_schedule.py`,
`assign_links_to_players.py` 의 `--tie-policy`(기본 `error`) fail-closed, generator 의 `tie_status` 게이트,
state schema v2, projection mass diagnostics, signal trace.

### S0-2. NumSim 정본 고정 — 완료

병렬 FD 가 미커밋 dirty(`95+/6−`)로 외부 `../NumSim-mine` 에만 있었고 vendor 는 `35a5c82` 를
가리켜 **런타임 소스와 감사 사본이 갈라져 있었다** [실측].

- NumSim `0240ba8` 로 커밋·푸시 (`freeway-zone-followers`)
- vendor 재복사, `SNAPSHOT.md` 갱신
- **원본 `src/` 와 vendor 불일치 0파일 확인** [실측]

**이후 규약** — NumSim 을 고치면 반드시 (a) 원본 커밋·푸시 (b) vendor 재복사
(c) `SNAPSHOT.md` 커밋 갱신 을 **같은 작업 단위**로 한다.

### S0-3. SC12 네트워크 변경 문서화 — 완료(단, 판정 미결)

신호두 2개의 SG 가 바뀌었다 [실측].

| 신호두 | 링크·차로 | 이전 | 현재 |
|---|---|---|---|
| 50201 | 1220012103 / 2 | `EBT` | `EBL` |
| 50601 | 1220013600 / 2 | `WBT` | `WBL` |

**물리적 타당성은 단정할 수 없다.** 두 차로 모두 직진·좌회전·우회전 셋 다로 이어지는
공용 차로다(head 50201: 직진 −12.4°, 좌 +90.7°, 우 −90.0°) [실측].

**남은 일** — `reports/network_change_sc12_heads_20260805.md` 의 세 근거로 확정하라.
① 정적 경로 `relFlow` 의 방향별 비중 ② 차로 표지·현장 자료 ③ `.sig`(`test-bed5.sig`) 의 sg5/sg1 녹색창.

---

## S1. active program 확정 + exact signal timeline

Codex 지적 6. **A 착수 전에 끝내야 한다.** 여기가 틀리면 C 산출이 통째로 틀린다.

### S1-1. 어느 prog 가 실제로 쓰이는가

- `.sig` 는 SC 당 prog 3개(`mor_peak`/`offpeak`/`aft_peak`).
- **prog 3개의 stage 집합이 동일한 SC 는 22/41.** 19개 SC 는 prog 마다 현시 구조가 다르고,
  주기가 prog 별로 다른 SC 는 17개다 [에이전트].
- `dailyProgLists`, `stageProgs`, VISSIM 기본 선택 규칙을 조사해 **확정**하라.
- 시뮬레이션 시작 시각과 `dailyProgLists` 의 관계도 확인하라 — 런마다 다른 prog 를 쓸 수 있다.

**중단조건** — 확정하지 못하면 중단하고 보고한다. **임의로 prog0 을 쓰지 마라.**

### S1-2. exact signal timeline (ms + clearance 보존)

v1 의 C-1 은 1초 마스크에 5초 미만 구간을 버렸는데, F 는 0.5초 event 정확도를 요구한다.
**두 기준이 모순이고, 1초 마스크로는 amber/all-red/intergreen 이 소실된다** (Codex 지적 6).

- `.sig` 의 **밀리초 `begin` 을 원본 그대로 보존**한 ordered SG timeline 을 만든다.
- display 1=Red, 3=Green, 4=Amber. **amber 와 all-red 를 버리지 마라.**
- `intergreenmatrices` 의 clearance 도 함께 보존한다.
- stage(동시녹색 집합)는 이 timeline에서 **파생**하되, timeline 자체를 대체하지 않는다.
- stage 분해 시 임계 τ 는 파라미터로 두고 민감도를 보고하라. τ 를 바꿔 stage 수가 어떻게
  변하는지 표로 남긴다.

**검증**
- SC 마다 `Σ stage green / cycle` 이 **0.851 ± 0.05** 안에 드는가 [에이전트]. 벗어나는 SC 를 나열
- stage 수 분포가 `{1:6, 2:7, 3:6, 4:8, 5:13, 6:1}` 인가 [에이전트]
- 재현성 — 두 번 돌려 산출 해시 동일

### S1-3. readback 해상도

**0.5초 게이트를 유지하려면 최소 2 Hz readback 이 필요하다** (Codex 지적 6).
현재 `SimRes=1` 로는 0.5초 정확도를 일반적으로 관측할 수 없다.

- readback 주기를 올릴 수 있는지 조사하고, 불가하면 **F 의 게이트 임계를 관측 가능한 값으로 바꿔라.**
- 임계를 바꾸면 그 근거를 남긴다. 관측 불가한 게이트는 `NOT_EVALUATED` 이지 PASS 가 아니다.

---

## A. 링크 귀속 동률 해소

Codex 감사 치명 결함 1번. **미해소 시 generator 가 fail-closed 로 막혀 C 이후가 진행되지 않는다.**

### 입력
`modi_eval_rw_control.inpx`, `reports/link_assignment_ties.json`, `scripts/assign_links_to_players.py`

### 할 일
하류 동률 **33건**, 상류 동률 **6건** [감사]. 해소 근거를 **이 순서로** 쓴다.
1. 커넥터 route 의 실제 연결성
2. 정적 경로(`vehicleRoutingDecisionStatic`)의 `relFlow` — 실제로 차가 가는 쪽
3. 정지선까지의 거리

**shared-route 인 경우** — 두 경로가 실제로 합류해 같은 정지선으로 간다면 동률이 아니라
**공유**다. 그 경우 링크를 쪼개지 말고 상류 비중(`relFlow`)으로 **가중 귀속**하는 안을 검토하라
(Codex 권장 순서의 "shared-route 가능한 귀속").

**정렬에 의한 결정성은 재현성 규칙이지 물리 규칙이 아니다.** 물리 근거 없이 최소 ID 를 고르지 마라.

### 산출
- `outputs/link_player_assignment_<stamp>.json` — `tie_status=CLEAR`
- `reports/tie_resolution_<stamp>.md` — 동률 항목마다 해소 근거

### 검증
- 동률 0건, 분할(중복 0·누락 0) 유지
- 진단용 signal-first 해석과의 차이(`973/6/226` vs `957/22/226`)를 설명 [감사]
- 실행마다 동일 (해시 비교 3회)

### 중단조건
물리 근거로 해소할 수 없는 동률이 남으면 **목록과 함께 중단**한다.

---

## B. adjacency 임의 tie 제거

A 와 같은 뿌리(BFS 동률).

- 인접쌍 **123쌍**을 실제 커넥터 route 로 재분류 [감사]
- `internal_link_members`(멤버 199개/고유 146개)의 **경로 기반 중복** 정리.
  이 중복이 고속도로 본선(링크 2, 26)을 도시부 내부 저류 멤버로 넣어 포착률 114.6% 를 만들었다 [실측]

**검증** — 인접쌍이 실행마다 동일. `internal_link_members` 에 고속도로 링크
(2,24,26,74,10699,10702)가 없음.

---

## C. 현시 아티팩트 + 모델 N현시 + 모니터 시간표

**플랜트 재실행 불필요 구간.** 되돌리기 쉽다.

### C-1. 현시 아티팩트 생성기

`scripts/derive_signal_phase_spec.py` 신설. 입력은 `.inpx` 1개 + `.sig` 41개(**`supplyFile2` 매핑**).
timeline 은 S1-2 산출을 쓴다.

**산출 스키마(제안)**
```json
{
  "source": {"inpx_sha256": "...", "sig_sha256": {"SC1001": "..."}},
  "signals": {
    "SC1001": {
      "supply_file": "개포동 test-bed1001.sig",
      "active_program": "0",
      "cycle_sec": 150.0,
      "intersection_clusters": [{"id": 0, "stop_links": ["..."], "centroid": [x, y]}],
      "signal_groups": {
        "1": {"name": "WBL", "cluster": 0,
              "heads": [{"link": "...", "lane": "2", "pos": 107.4,
                         "out_connectors": [{"connector": "...", "to_link": "...", "turn_deg": 90.7}]}]}
      },
      "timeline_ms": [{"sg": "1", "display": "3", "begin_ms": 48000}],
      "stages": [{"index": 0, "sgs": ["2", "6"], "start_sec": 0.0, "green_sec": 48.0}],
      "clearance": {"1-2": 3.0}
    }
  }
}
```

`reports/signal_reference_20260805.json` 에 신호두 541개의 (SC, SG번호, SG이름, 링크, 차로, pos,
진출 커넥터별 회전각)이 이미 있다 — 이걸 입력으로 써라.

**핵심 규약**
- **키는 `(SC, SG번호)`.** 이름으로 병합하지 마라 — 한 SC 가 복수 물리 교차로를 물어
  같은 이름이 여러 SG 번호에 걸린 SC 가 9개다(SC2,3,4,5,7,9,13,102,9001) [에이전트].
  반례: SC2 `EBT` = sg2/sg10/sg18 이 서로 다른 세 교차로의 동쪽 진입.
- **SG 번호 산술로 NEMA 상을 유도하지 마라.** `((no-1) mod 8)+1` 은 424개 중 408개(96.2%)만 맞고
  SC102·SC9001 의 sg11~18 이 통째로 어긋난다 [에이전트].
- **현시 구성을 고정 규칙으로 유도하지 마라.** 표준 NEMA 규칙은 건전성 95.5%, 완전성 77.2%,
  SC 단위 완전일치 **16/41** 이다 [에이전트]. 이 네트워크가 **NEMA 대향형 + 한국식 직좌동시 혼합**
  이기 때문이다 — through 가 양쪽 다 있는 축 61개 중 SPLIT 6, OPPOSING 55이고
  **SPLIT 5개가 통제 15 소속**(SC1 EW, SC11 EW, SC11 NS, SC12 EW, SC105 EW).
- 교차로 클러스터링 임계는 **55~70 m**. 90 m 이상에서 SC1001 EBL/WBL 이 합쳐져 대향성이 깨진다 [에이전트].

**검증**
- `.inpx`↔`.sig` SG 이름 불일치 **0건** 재확인 [에이전트]
- 클러스터 단위 대향성 **109쌍 전부 ≥135°**(중앙 178.7°, 최소 135.2°) 재현 [에이전트]
- 신호두 달린 SG 중 3 prog 전부 영구 적색인 것이 **2개**(SC5 sg18, SC9 sg15) 인가 [에이전트]
- **SC7 링크 1220008601 차로2 의 SBT/SBL 겹침** 처리 방침을 명시 [에이전트]
- 나가는 커넥터 없는 신호두 4개(SC4 sg21, SC9003 sg4/sg8, SC1001 sg1) 처리 방침 [에이전트]

### C-2. 모델 `_phase_green_fraction` N현시 일반화

`NumSim-mine/src/models/urban_queue_model.py:541`. 현행 `[p1][lost/2][p2][lost/2]` → N현시.

- 손실시간을 N 으로 나눌지 `.sig` 실제 amber+all-red 를 쓸지 결정하고 근거를 남겨라
  (stage 시간합/주기 0.851 은 손실이 약 15% 라는 뜻)
- offset 처리 `t0 = (urban_step_index * t_u − offset) % cycle` 이 N현시에서 맞는지 확인
- **`urban_step_index=None` 경로(주기 평균)** 도 맞춰야 한다

**검증 — 통과 못 하면 다음 금지**
- **N=2 에서 비트 동일.** 부동소수점 연산 순서까지 같아야 한다
- 4방위 6노드 격자 회귀 — movement 78 / storage 29, 결과 비트 동일

### C-3. movement→stage 매핑 — **경로를 끝까지 추적한다**

Codex 지적 4. v1 은 신호두에서 **접근 leg 까지만** 추적해 같은 접근의 좌/직을 구분할 수 없었다.

**필요한 경로**
```
signal head (link, lane)
  → 그 lane 의 outgoing connector
  → connector 의 destination link
  → destination link 의 leg (커넥터 BFS 상류 SC)
  → 모델 movement (approach leg, exit leg)
```

- **방위로 잇지 마라.** 모델의 45° 이산화는 회전을 84%만 맞추고 램프 leg 방위는 허구다
  (SC1001 모델 `N`, 실측 `W`) [에이전트].
- **VISSIM 커넥터 실측 기하는 99.1%** 정확하다(T 중앙 0°, L 중앙 +90°, 임계 +30°) [에이전트].
  회전 분류는 이걸 쓴다.
- 한 lane 이 직진·좌·우 셋 다로 이어지는 **공용 차로**가 있다(SC12 head 50201) [실측].
  이 경우 movement 별로 어느 SG 를 따르는지 결정 규약을 명시하라.

**fail-closed 게이트** (Codex 지적 4)
- **차량 가중 배정률**을 보고한다 — movement 개수가 아니라 그 movement 가 담는 차량 기준
- **unresolved 목록을 산출**하고, 임계 미달이면 아티팩트 생성을 **거부**한다
- 참고: 코어15 신호두 218개 중 158개(72.5%)가 유일 leg 로 귀속. 나머지 60개
  (상류 없음 35, 상류 복수 25) 처리 방침을 명시하라 [에이전트]

**검증**
- 아티팩트가 없으면 기존 p1/p2 경로 — 비트 동일
- SC 별 배정률(개수 기준 + 차량가중 기준) 보고, unresolved 전부 나열

### C-4. 모니터 26개에 `.sig` 고정 시간표

지금 모니터 movement 는 phase 가 빈 문자열이라 `_phase_green_fraction` 이 **1.0(항상 녹색)** 을 준다.
**막혀 있는 접근을 뚫려 있다고 본다.** movement 1,422개 중 672개(47.8%), 관측 차량의 40.7% [실측].

- `NetworkConfig` 에 3번째 부류 — 지금은 `signals`(통제)와 `uncontrolled_nodes`(항상녹색) 둘뿐이다.
  **"고정 시간표를 갖되 리더가 못 바꾸는"** 부류가 필요하다
- 영구 적색은 녹색비 **0**. 주기 경계를 넘는 창(wrap) 처리
- 모니터 노드의 offset 도 `.sig` 에서 온다
- 통합된 `evaluation/controllers/fixed_signal_schedule.py` 를 기반으로 하되,
  감사가 지적한 한계(**375 movement 가 angle/phase fallback, 425 가 multi-SG union,
  exact 단일 SG 연결은 약 145개**)를 C-3 의 커넥터 경로로 해소하라 [감사]

**검증**
- 영구 적색 접근에 차가 실제로 쌓이는가
- 포착률 재측정 — `scripts/verify_urban_topology_merge.py`
- **`uncontrolled_node_movement_queue_veh` / `_storage_occupancy_veh` 가 0 이 아니게 되는가**

---

## D. 실시간 링크 속도

Codex 감사 P1-1. E 와 묶어 한 번의 VISSIM 재실행으로 처리한다.

- VBS 에 `linkSpeedSums` 는 있으나 `link_speeds` 로 안 내보낸다
- 어댑터가 이를 urban travel-time delay 에 쓰도록 한다(현재 고정 평균속도 경로가 남아 있다) [감사]
- **same-substep zero-delay** 를 단위시험으로 제거 [감사]

---

## E. 액션 계약 + VBS N현시

**여기서부터 플랜트가 바뀐다.** ~~주기 통일은 E 에서 제외했다 — X 항목으로 분리.~~

### E-1. 액션 CSV 스키마
현재 헤더: `sim_sec,kind,id,dsd_no,sc_no,link,lane,speed_kph,major_green,minor_green,offset,rate_vph,green_sec,metadata,readback`
- N현시로 확장. 하위호환 유지 여부를 결정하고 근거를 남겨라
- **이 CSV 를 읽는 소비자를 저장소 전체에서 찾아 전부 나열하라**(python·PS·VBS)

### E-2. VBS SG→stage 매핑
`SignalStateForGroup`(893~906행 부근), `SignalCompositeStateAt`, `sigMajor`/`sigMinor`/`sigOffset`.
현행 이름 규칙 2분 때문에 통제 15 SC 에서 동시녹색으로 명령하는 SG 쌍 147개 중
**73개(49.7%)가 `.sig` 3개 prog 어디에도 없는 조합**이다 [에이전트].
- **SG번호 → stage 인덱스** 매핑 테이블로 교체. 출처는 C-1 아티팩트
- 주기 계산 `cycle = major+AMBER+ALLRED+minor+AMBER+ALLRED` 를 N현시로 일반화

### E-3. 부분 적용 방지 계약
**모델만 N현시이고 VBS 가 2상이면(또는 반대면) 에러 없이 틀린 신호가 나간다.**
- 아티팩트 해시를 액션·상태 양쪽에 실어 대조. 불일치면 **fail-closed**

### E-4. readback 상충 검사
지금은 요청/판독 일치만 본다(10,448/10,448) [감사].
아티팩트의 stage 멤버십을 근거로 **"상충 SG 가 동시에 녹색이 아님"** 을 검사한다.

---

## F. 신호 타이밍 oracle

- expected `.sig` transition oracle 로 immediate/post-step readback 과 비교
- **offset 부호**와 적용 cycle boundary 검증
- **임계는 S1-3 에서 확정한 관측 가능 해상도를 따른다.** 관측 불가한 임계는 `NOT_EVALUATED`
- 감사에서 `signal_event_timing` 이 `NOT_EVALUATED` 였던 이유가 이 oracle 부재다

**offset 제어 실험은 이 게이트 통과 후에만 허용한다.**

---

## G. exit stock 과 boundary 병렬 기록

- 출구 226개(도시부 차량의 5.1%)를 **objective 에서만 빼고 plant 상태에는 남긴다.**
  physical downstream stock·supply·backpressure 까지 제거하면 상류 action 이 과도하게 유리해진다 [감사]
- boundary objective **포함/제외 두 버전을 병렬 보고**
- 관련: `boundary_in` 큐 122.7대가 목적함수 밖이다. 플레이어 approach 에 서 있는 차다 [실측].
  포함 시 포착률 76.8% → 약 89%. **목적함수 정의 변경이라 G6 에 직접 영향** — 근거를 남겨라

---

## H. 저류 재분류 + 파라미터 holdout

- storage **186개**를 lane connectivity 로 **직렬/병렬 분류**. 현재 `Σ(길이×차로)×jam` 은 직렬 가정 [감사]
- **jam density 를 training/holdout 분리 재추정.** 현재 140.5 veh/km/lane 은 관측 런의 혼잡도에
  의존한다 — 저수요 런에서는 99.1 이 나왔다 [실측]. 물리 상수여야 할 값이 관측 의존적이다
- storage fraction(0.35/0.50)과 ramp cap(93.0~145.9)도 같은 방식으로 검증

---

## I. 한계가격 — SPSA parity gate + 상별 FD 병렬

**플랜트 무관. 언제든 병행 가능하고 I-1 은 지금 착수 가능.**

### I-1. SPSA parity gate (Codex 지적 7)

v1 의 "레버 1개면 FD 와 동일" 은 **endpoint 와 objective 가 같을 때만** 성립한다.
현재 production 경로는 forecast 전달, barrier derivative, offset relinearization 이 FD 와 SPSA 에서
다르다. 또 기존 부호일치(11/15, 13/15, 14/15)는 **near-zero gradient 를 구분하지 않아** 무의미하다.

**SPSA 활성화 전 통과해야 할 게이트**

| # | 게이트 |
|---|---|
| 1 | green/meter/VSL/offset **각 채널별로** 단일 레버 endpoint·objective **완전 동일성** |
| 2 | noise floor 이하 FD 는 **`INDETERMINATE`** 처리(PASS 도 FAIL 도 아님) |
| 3 | **material gradient 평균 부호 반전 0** |
| 4 | 정규화 **RMSE ≤ 0.20** |
| 5 | 효과 회귀기울기 **0.90 ~ 1.10** |
| 6 | 독립 perturbation batch 의 **부호오류 확률 95% 상한 ≤ 0.05** |
| 7 | N현시는 **simplex tangent-space 좌표**에서 FD 와 비교 |
| 8 | **실제 N현시 자유도 전체를 직접 시험.** 15레버 결과로 외삽하지 마라 |

참고 실측(현행 2상 15레버, FD 기준 53.3초) [실측] — **판정 근거로 쓰지 마라. 위 게이트로 다시 재라.**

| k | 시간 | 부호일치 | Spearman | 중앙 크기비 |
|---:|---:|---:|---:|---:|
| 4 | 4.5s | 11/15 | +0.418 | 4.89 |
| 8 | 7.9s | 13/15 | +0.721 | 3.54 |
| 16 | 14.9s | 14/15 | +0.875 | 2.53 |
| 32 | 28.7s | 13/15 | +0.882 | 3.29 |

표본 15개라 Spearman 표준오차가 약 0.06 이어서 0.875 와 0.882 는 구분되지 않는다.
`barrier_price_enabled` 는 기본 False 이고 config 에도 없어, SPSA 가 barrier 항을 버리는 것은
이 설정에서 무해하다 [실측].

### I-2. 상별 한계가격
- 레버를 신호당 1 → N−1 자유도로 확장
- `_spsa_global_price_gradients` 의 `build()`(917~919행)가 `p2 = total − p1` 로 **2상을 하드코딩**한다.
  N현시면 **심플렉스 위 섭동**으로 바꿔야 한다
- 팔로워 trust region `|p1 − ref| ≤ trust` 를 **노름 기반**으로 재정의
- green 후보 격자가 1차원 → (N−1)차원 심플렉스. **조합 폭발을 정량화하고 대책을 세워라**

### I-3. 병렬 FD — **미검증 상태로 들어와 있다**
`NumSim-mine 0240ba8` 에 배선만 있다.
- `price_parallel_workers`(0/1 = 직렬), `_green_price_rollouts()`,
  모듈 레벨 워커 `_price_worker_init`/`_price_worker_green`
- **검증: workers=0 과 workers=5 의 가격 비트 동일**
- 워커에서 `_price_rollout_count` 가 부모로 안 돌아와 수동 보정한 부분 확인

### I-4. 목표
**production `decide_with_info` H=3 의 p95 ≤ 30초, max ≤ 45초** [감사 기준]. 현재 **154.746초**.
가격 갱신의 98.4% 가 롤아웃이므로 병렬화가 주 수단이고,
`_phase_green_fraction` 메모이제이션(645만 회, 17%)이 곱해진다 [실측].
롤아웃 1회 0.44초, 논리코어 20, 컨트롤러 피클 610 KB [실측].

---

## J. 동적 검증 — **harness 를 먼저 만들어야 한다**

Codex 지적 3. **v1 은 기존 matrix runner 로 J 를 할 수 있다고 가정했으나 틀렸다.**

`scripts/run_plant_fidelity_matrix.ps1` 은 헤더 그대로 *"Run the fixed/no-control VISSIM fidelity
baseline matrix sequentially"* — **no-control baseline 9개만 실행**한다 [실측].
anchor 별 paired future, action perturbation, horizon 별 비교를 만들지 않는다.
기존 auditor 에도 queue/speed/TTT/spillback/action-ranking 게이트가 없다 [감사].

### J-1. paired-future harness 구축 (신규 작업)
- anchor 상태에서 **동일 seed·수요로 분기**해 H=1/3/5/10/15 의 VISSIM future 를 만든다
- 같은 anchor 에서 **action 을 low/base/high 로 바꾼 paired 실행**
- 모델 rollout 과 짝지어 저장하는 산출 규약

### J-2. 실행
- **demand 0.75/1.0/1.25 × seed 13/29/47**, 3,600초. anchor 900/1500/2100/2700
- **VISSIM 은 한 번에 하나만**

### J-3. 비교 지표
count, queue, storage, speed, flux, TTT, spillback onset/release, action ranking

### J-4. 합격 기준
Spearman ≥ 0.70, top-action pairwise ≥ 0.80, 반복 부호 반전 0.

**특히 H=1 을 보라.** 현재 rho **0.4378**, pairwise **0.000**(H=5/10/15 는 0.985/0.921/0.862) [감사].
MPC 는 첫 구간만 집행하므로 폐루프를 좌우하는 지평이 여기다. 매크로 평균 0.8015 가 이 퇴행을 흡수한다.

---

## K. 전체 감사 재실행 — **동적 게이트 추가 후**

- `scripts/audit_plant_fidelity.py` 에 **J 의 동적 게이트를 추가**한다.
  현재 게이트로는 K 를 재실행해도 동적 충실도를 합격 처리할 수 없다 [감사·Codex 지적 3]
- 새 hash/run ID 로 재실행. 이전 결과는 PASS 14 / FAIL 2(`assignment_ties`, `runtime`) / NOT_EVALUATED 1
- **nominal·혼잡의 모든 seed 가 통과한 뒤에만** P-Stack/G6 성능을 plant 근거로 쓴다

---

## X. 주기 통일 — **충실도 작업이 아니다. 별도 실험으로 분리**

Codex 지적 5. **v1 의 E-5 를 여기로 옮겼다.**

### 왜 분리하는가

주기 통일은 **VISSIM 을 모사하는 작업이 아니라 VISSIM 네트워크 자체를 재설계하는 작업**이다.
기존 주기가 서로 다른 것이 현실이라면 **plant 가 그것을 표현해야지**, 모델의 스칼라 `cycle_length` 에
맞춰 원본을 바꾸면 감사 대상이 달라진다. 순환논리다.

메인 세션은 "모델 `cycle_length` 가 스칼라라 이미 불일치" 를 통일의 근거로 들었으나,
**그것은 모델을 고칠 이유이지 플랜트를 바꿀 이유가 아니다.**

### 대신 할 일

**X-1. 모델이 SC 별 주기를 지원하게 한다** (충실도 작업. C-2 와 함께)
- `NetworkConfig` 에 `cycle_length_by_signal: Dict[str, float]`, 조회 실패 시 스칼라 폴백
- `cycle_length` 를 쓰는 **모든 지점을 찾아** 각각 SC 별 조회로 바꿀지 판단
- prog0 주기 분포: 100s×1, 120s×2, 140s×1, **150s×23**, 160s×11, 170s×3 [실측]

**X-2. 두 구성을 별도로 유지한다**
| 구성 | 목적 | 네트워크 |
|---|---|---|
| `native-cycle fidelity plant` | 충실도 감사·승격 판정 | **원본 그대로** |
| `150s normalized control experiment` | offset 연동 제어 실험 | 주기 통일본(별도 `.inpx`) |

**X-3. 정규화본을 만들 때**
- 150s prog 가 있는 SC 는 그걸 쓴다(SC1 `[160,150,160]`, SC107 `[170,160,170]` 등) [실측]
- 없는 SC 는 녹색 재배분. `.sig` 의 `minGreen` 제약 준수
- **별도 `.inpx` 로 저장하고 단독 커밋 + `reports/network_change_*.md` 고지**

**offset 제어 실험은 X-2 의 정규화본에서만 한다.** 주기가 다르면 인접 신호 위상이 매 주기 밀려
연동 밴드가 성립하지 않는다.

---

## 부록 A. 의존성

```
S0 (완료) ──> S1 ──┬──> A ──┬──> C ──> D ──> E ──> F
                   │        │        │
                   └──> B ──┘        └──> G
                                     └──> H
                                     └──> X-1 (모델 SC별 주기)

I  (플랜트 무관 — 병행 가능. I-1 은 지금 착수 가능)

C, D, E, F, G, H, I 완료 ──> J-1 harness 구축 ──> J-2/3/4 ──> K(동적 게이트 추가)

X-2/X-3 (주기 정규화본) ── 승격 판정과 무관한 별도 실험
```

- **S1 이 A 보다 앞선다** — active program 이 틀리면 C 산출이 통째로 틀린다
- **C 까지는 플랜트 재실행 불필요**
- **D+E 를 묶어 한 번의 VISSIM 재실행**
- **J-1(harness 구축)이 신규 작업**이다. 기존 matrix runner 로는 안 된다
- **J 가 승격 판정.** K 는 그 확인

## 부록 B. v1 → v2 변경 내역 (Codex 검토 수용)

| # | Codex 지적 | v2 반영 |
|---|---|---|
| 1 | 감사 구현이 브랜치에 없다 | **S0-1 통합 완료**(`34fb88e`, 충돌 0건) |
| 2 | NumSim 정본 불분명 | **S0-2 완료** — `0240ba8` 커밋, vendor 재복사, 불일치 0파일 |
| 3 | J/K 실행 불가 | **J-1 harness 구축을 신규 작업으로 추가.** K 에 동적 게이트 추가 명시 |
| 4 | movement→stage 매핑 부족 | **C-3 을 connector→destination leg 까지 확장.** 차량가중 배정률 + unresolved fail-closed |
| 5 | 주기 통일은 분리해야 | **E-5 를 X 항목으로 분리.** 모델이 SC별 주기 지원(X-1), 정규화본은 별도 실험(X-2/3) |
| 6 | 시간축 충돌 | **S1-2 exact ms timeline**(clearance 보존), S1-3 readback 해상도, F 임계를 관측가능값으로 |
| 7 | SPSA 게이트 부족 | **I-1 을 Codex 게이트 8개로 교체.** 기존 수치는 "판정 근거로 쓰지 마라" 명시 |
| 8 | 문서화 안 된 네트워크 변경 | **S0-3 + `reports/network_change_sc12_heads_20260805.md`.** 공용 차로라 판정 미결 |
