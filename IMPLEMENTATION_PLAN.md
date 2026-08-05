# 구현 작업지시서 — 플랜트 충실도 복구 + 4현시 전환

작성 2026-08-05. 수행자: Codex. 순서대로 진행한다.

이 문서는 [`PLANT_FIDELITY_AUDIT_REQUEST.md`](PLANT_FIDELITY_AUDIT_REQUEST.md)(감사 요청)와
그 결과인 `reports/plant_fidelity_audit.md`(브랜치 `codex/plant-fidelity-audit-20260805`,
커밋 `eec5d9e`)의 **후속 실행 계획**이다. 감사 판정은 **불가**였고, 그 판정을 뒤집는 것이 목표다.

---

## 0. 이 문서를 읽는 법

### 0.1 근거의 등급

본문에 인용된 수치에는 출처 등급을 붙였다.

- **[실측]** — 메인 세션이 직접 실행해 확인. 명령과 출력이 대화 기록에 있다.
- **[에이전트]** — 서브에이전트 보고. 교차검토는 거쳤으나 메인 세션이 재현하지 않았다.
- **[감사]** — Codex 감사 보고서(`reports/plant_fidelity_audit.md`).

**[에이전트] 등급은 착수 전에 재현하라.** 아래 0.3 참조.

### 0.2 절대 제약

- **VISSIM 배치는 한 번에 하나만.** 워치독의 `Kill-Vissim` 이 모든 VISSIM200/cscript 를 죽인다.
- `.ps1` 은 **순수 ASCII**. PowerShell 5.1 이 BOM 없는 파일을 CP949 로 오독해 한글 경로를 깬다.
- PowerShell here-string 을 네이티브 exe 에 넘기지 마라 — 경계를 못 넘고 **조용히 실패**한다.
- **런이 이상하면 `network/real_world_gaepo_modi/modi_eval_rw_control.err` 를 먼저 읽어라.**
  정적 경로 하나가 끊겨도 VISSIM 은 시뮬을 시작 직후 중단·리셋한다. 그때 증상은
  `actual_sim_sec=0` 고정과 `FAILED_SET_SIGSTATE` 수만 건인데 **그 신호 오류는 결과지 원인이 아니다**.

### 0.3 우리가 실제로 저지른 오류 (같은 함정을 피하라)

이 프로젝트에서 실제로 난 오류다. 전부 **"입력이 맞는지 확인하지 않아서"** 생겼다.

1. **`.sig` 파일을 SC 번호로 찾았다.** `개포동 test-bed{N}.sig` 의 N 이 SC 번호라고 가정했으나
   **50개 중 18개가 다르다** [실측]. SC5→test-bed7, SC6→test-bed9, SC11→test-bed3, SC12→test-bed5.
   이 오류로 "SC12 는 1현시", "14개 SC 에 영구 적색", "`.sig` 는 구조의 출처로 못 쓴다" 는
   결론이 전부 틀렸다. **반드시 `signalController/@supplyFile2` 로 매핑하라.**
2. **glob 으로 엉뚱한 `.inpx` 를 파싱했다.** 정본은
   `network/real_world_gaepo_modi/modi_eval_rw_control.inpx` 다. `modi_eval_vsl_8seg.inpx` 는 구 가상격자다.
3. **방향을 뒤집어 쟀다.** `SC1001_to_SC1004` 를 "물리 8,896대 vs 모델 120대" 라고 보고했으나
   8,896은 반대 방향 회랑이었다. 실제 접근로는 421 m, 143.5대다.
4. **증상을 원인으로 보고했다.** 신호 COM 실패 28,056건을 원인으로 의심했으나 시뮬이 안 도는 결과였다.
5. **에이전트 진단을 무검증으로 전달했다.** "유령링크가 spillback F1 의 원인" 을 검증 없이 옮겼다가
   이미 적용돼 있고 효과가 없었음이 드러났다.

**따라서 각 항목 착수 전에 그 항목이 쓰는 입력 파일의 정체를 확인하고, 인용된 수치를 재계산하라.**

---

## 1. 확정 사실

착수 전에 [에이전트] 항목은 재현하라. 재현이 안 되면 그 항목의 후속 작업을 중단하고 보고하라.

### 1.1 소스 정본

| | |
|---|---|
| 네트워크 | `network/real_world_gaepo_modi/modi_eval_rw_control.inpx` |
| SC → `.sig` | `signalController/@supplyFile2` **만** 신뢰. 파일명 숫자 아님 [실측] |
| 모델 | `../NumSim-mine/src/` (사본은 `vendor/NumSim-mine/src/`, **수정 금지**) |
| 런타임 모델 경로 | `NUMSIM_REPO_ROOT` 환경변수, 없으면 절대경로 폴백 (`vissim_stackelberg_adapter.py:24`) |

### 1.2 규모

- 링크 1,219 = 일반 448 + 커넥터 771 [감사]
- 신호제어기 50개, active 42. 도시부 41 + 램프미터 8(SC9101~9108). SC9004 는 신호두 0개 [감사]
- 신호두가 달린 SG 250개 / 전체 424개. 미사용 174개 [에이전트]
- 지(leg) 수 = SG 이름 접두 {EB,WB,NB,SB} 개수 → **4지 25, 3지 11, 2지 5** [실측·에이전트 일치]
- 물리 교차로 클러스터(정지선 좌표, 임계 55~70 m): 41 SC → 1교차로 31, 2교차로 8, 3교차로 2 [에이전트]

### 1.3 신호 구조

- SG 이름은 `EBL/EBT/WBL/WBT/NBL/NBT/SBL/SBT`. `.inpx` 와 `.sig` 간 **이름 불일치 0건** [에이전트]
- **키는 `(SC, SG번호)`.** 이름으로 병합하지 마라 — 한 SC 가 복수 물리 교차로를 물어
  같은 이름이 여러 SG 번호에 걸린 SC 가 9개다(SC2,3,4,5,7,9,13,102,9001) [에이전트].
  반례: SC2 `EBT` = sg2/sg10/sg18 이 서로 다른 세 교차로의 동쪽 진입.
- **SG 번호 산술로 NEMA 상(相)을 유도하지 마라.** `((no-1) mod 8)+1` 은 424개 중 408개(96.2%)만 맞고
  SC102·SC9001 의 sg11~18 이 통째로 어긋난다 [에이전트]
- 좌/직은 **차로 단위**로 갈린다. L/T 이름이 2개 이상 붙은 (SC,링크) 80개 중 79개가 차로 서로소.
  **겹침 1건: SC7 링크 1220008601 차로2 에 SBT(head 140402)와 SBL(head 140701) 동시 배정** [에이전트]
- 나가는 커넥터가 없는 신호두 4개 — SC4 sg21, SC9003 sg4, SC9003 sg8, SC1001 sg1 [에이전트]

### 1.4 현시 구성 — 고정 규칙은 쓸 수 없다

- **기하 검증은 통과.** 교차로 클러스터 단위로 (EBT,WBT)/(NBT,SBT)/(EBL,WBL)/(NBL,SBL)
  **109쌍 전부 대향** — 링크 겹침 0, 방위차 중앙 178.7°, 최소 135.2° [에이전트].
  **단, SC 단위로 평균내면 깨진다**(SC2 NBL/SBL 110.8°, SC1001 EBL/WBL 83.1°) — 클러스터링 필수.
- **시간표 검증은 실패.** 표준 NEMA 고정 규칙(φ1={EBT,WBT} …)은
  건전성 95.5%(156쌍 중 7쌍 위반), 완전성 77.2%(193쌍 중 44쌍 누락),
  **SC 단위 완전일치 16/41** [에이전트]
- 원인: 이 네트워크가 **NEMA 대향형 + 한국식 직좌동시(분리신호) 혼합**이다.
  through 가 양쪽 다 있는 축 61개 중 **SPLIT 6, OPPOSING 55**이고
  **SPLIT 5개가 통제 15 SC 소속**(SC1 EW, SC11 EW, SC11 NS, SC12 EW, SC105 EW) [에이전트]
- 대안 규칙도 전부 실패 — 접근별 SPLIT 템플릿 41개 중 1개 일치, 기하 가설 73.8~75.4% [에이전트]

**결론 — 현시 구성은 규칙으로 유도하지 말고 `.sig` stage 분해로 얻는다.**

### 1.5 `.sig` 는 쓸 수 있다

올바른 `supplyFile2` 매핑 기준.

- 41 SC ↔ 41 파일 1:1, 중복 없음 [실측]
- **신호두 달린 SG 중 3개 prog 전부 영구 적색인 것은 2개뿐**(SC5 sg18 EBT, SC9 sg15 SBL) [에이전트]
- stage 수 분포 — 1개 6 SC, 2개 7, 3개 6, 4개 8, 5개 13, 6개 1 [에이전트]
- stage 시간합/주기 평균 **0.851** (나머지는 amber + all-red) [에이전트]
- **prog 3개의 stage 집합이 동일한 SC 는 22/41.** 19개 SC 는 prog 마다 현시 구조가 다르다.
  주기가 prog 별로 다른 SC 는 17개 [에이전트]
- prog0 주기 분포: 100s×1, 120s×2, 140s×1, **150s×23**, 160s×11, 170s×3 [실측]

**미확정 — VISSIM 이 3개 prog 중 어느 것을 쓰는가.** `dailyProgLists`, `stageProgs`, 기본 선택 규칙을
확정하라. **이게 틀리면 C 항목 산출이 통째로 틀린다.** A 착수 전에 해결한다.

### 1.6 성능 실측

- 논리 코어 20. 워커 기동(import 0.03s + build_runtime 0.22s), 컨트롤러 피클 610 KB / 왕복 수 ms [실측]
- **롤아웃 1회 0.44초** [실측]
- 가격 갱신의 **98.4%가 롤아웃** — `_predict` 125회 208.4s / 총 211.7s(cProfile) [실측]
  내역: offset walk 13회 90.3s(43%), green FD 30회 50.1s(24%)
- `_phase_green_fraction` 645만 회, 36.7s(17%) — (phase, step_idx) 메모이제이션은 순수 항등 [실측]
- production `decide_with_info` H=3 실측 **154.746초** [감사]. 목표는 p95 ≤30s, max ≤45s

### 1.7 SPSA 실측 (현행 2상, 신호 15레버)

| k | 시간 | 부호일치 | Spearman(FD 대비) | 중앙 크기비 |
|---:|---:|---:|---:|---:|
| 4 | 4.5s | 11/15 | +0.418 | 4.89 |
| 8 | 7.9s | 13/15 | +0.721 | 3.54 |
| 16 | 14.9s | 14/15 | +0.875 | 2.53 |
| 32 | 28.7s | 13/15 | +0.882 | 3.29 |

FD 기준 53.3초 [실측]. **판정 보류** — 표본 15개라 Spearman 표준오차가 약 0.06 이고,
0.875와 0.882는 통계적으로 구분되지 않는다. I 항목에서 결정적 진단을 한다.

---

## A. 링크 귀속 동률 해소 — **최우선**

Codex 감사 치명 결함 1번. **이걸 안 풀면 생성기가 fail-closed 로 막혀 C 이후가 진행되지 않는다.**

### 입력
- `network/real_world_gaepo_modi/modi_eval_rw_control.inpx`
- `reports/link_assignment_ties.json` (감사 브랜치 산출, 동률 전체 목록)
- `scripts/assign_links_to_players.py`

### 할 일
1. 하류 동률 **33건**, 상류 동률 **6건**을 해소한다 [감사].
   해소 근거로 다음을 **이 순서로** 쓴다.
   - 커넥터 route 의 실제 연결성 (정지선까지의 물리 경로)
   - 정적 경로(`vehicleRoutingDecisionStatic`)의 `relFlow` — 실제로 차가 가는 쪽
   - 정지선까지의 거리
2. 정렬에 의한 결정성은 **재현성 규칙이지 물리 규칙이 아니다.** 물리 근거 없이 최소 ID 를 고르지 마라.
3. `tie_status=CLEAR` 인 assignment 를 생성한다.

### 산출
- `outputs/link_player_assignment_<stamp>.json` — `tie_status=CLEAR`
- 해소 근거를 동률 항목마다 기록한 `reports/tie_resolution_<stamp>.md`

### 검증
- 동률 0건, 분할(중복 0·누락 0) 유지
- 진단용 signal-first 해석과의 차이(`973/6/226` vs `957/22/226`)가 왜 생기는지 설명 [감사]
- 귀속 결과가 실행마다 동일 (해시 비교 3회)

### 중단조건
물리 근거로 해소할 수 없는 동률이 남으면 **그 목록과 함께 중단**하고 보고한다. 임의 선택하지 마라.

---

## B. adjacency 임의 tie 제거

A 와 같은 뿌리(BFS 동률)다.

### 할 일
- `scripts/derive_intersection_adjacency.py` 의 인접쌍 **123쌍**을 실제 커넥터 route 로 재분류 [감사]
- single-path 선택이 임의인 tie 를 A 와 같은 근거로 해소
- `internal_link_members`(멤버 199개/고유 146개)의 **경로 기반 중복**을 정리 — 이 중복이
  고속도로 본선(링크 2, 26)을 도시부 내부 저류 멤버로 넣어 포착률 114.6% 를 만든 원인이다 [실측]

### 검증
- 인접쌍이 실행마다 동일
- `internal_link_members` 에 고속도로 링크(2,24,26,74,10699,10702)가 없음

---

## C. 신호 현시 아티팩트 + 모델 N현시 + 모니터 시간표

**플랜트 재실행 없이 진행·검증 가능한 구간.** 여기까지가 되돌리기 쉬운 범위다.

### C-1. 현시 아티팩트 생성기

새 스크립트 `scripts/derive_signal_phase_spec.py`.

**입력** — `.inpx` 1개 + `.sig` 41개(**`supplyFile2` 매핑**)

**stage 분해 알고리즘** [에이전트 제안, 검증 필요]
```
1. prog p 에서 SG 별 녹색 마스크를 초 단위로 만든다.
   녹색 구간 = [green cmd begin, red cmd begin − amber)
2. 녹색집합이 바뀌는 지점에서 주기를 자른다.
3. 지속 τ=5s 미만 구간과 공집합 구간을 버린다.
4. 남은 서로 다른 녹색집합이 stage 다.
5. 인접 stage 를 합치지 마라 — 합치면 양립 불가한 SG 를 양립한다고 말하게 된다.
```

**산출 스키마** (제안. 더 나은 안이 있으면 근거와 함께 바꿔라)
```json
{
  "source": {"inpx_sha256": "...", "sig_sha256": {"SC1001": "..."}},
  "signals": {
    "SC1001": {
      "supply_file": "개포동 test-bed1001.sig",
      "intersection_clusters": [{"id": 0, "stop_links": ["..."], "centroid": [x, y]}],
      "signal_groups": {
        "1": {"name": "WBL", "cluster": 0, "heads": [{"link": "...", "lane": "2", "turn_deg": 90.4}]}
      },
      "programs": {
        "0": {"name": "mor_peak", "cycle_sec": 150.0,
              "stages": [{"index": 0, "sgs": ["2", "6"], "start_sec": 0.0, "green_sec": 48.0}]}
      },
      "active_program": "0"
    }
  }
}
```

**검증**
- `.inpx`↔`.sig` SG 이름 불일치 **0건** 재확인
- SC 마다 `Σ stage green / cycle` 이 **0.851 ± 0.05** 안에 드는가. 벗어나는 SC 를 나열
- 교차로 클러스터 단위 대향성 **109쌍 전부 ≥135°** 재현
- 신호두 달린 SG 중 3 prog 전부 영구 적색인 것이 **2개**(SC5 sg18, SC9 sg15) 인가
- stage 수 분포가 {1:6, 2:7, 3:6, 4:8, 5:13, 6:1} 인가
- **재현성** — 두 번 돌려 산출 해시 동일

**중단조건**
- `active_program` 선택 규칙을 확정하지 못하면 **중단**. 임의로 prog0 을 쓰지 마라.
- SC7 링크 1220008601 차로2 의 SBT/SBL 겹침을 어떻게 처리할지 정하지 못하면 그 SC 만 표시하고 진행

### C-2. 모델 `_phase_green_fraction` N현시 일반화

`NumSim-mine/src/models/urban_queue_model.py:541`

현행 배치 `[p1][lost/2][p2][lost/2]` → N현시 일반화.

- 손실시간을 N 으로 나눌지, `.sig` 의 실제 amber+all-red 를 쓸지 결정하고 근거를 남겨라
  (stage 시간합/주기 0.851 은 손실이 15% 라는 뜻이다)
- offset 처리 `t0 = (urban_step_index * t_u − offset) % cycle` 이 N현시에서 맞는지 확인
- **`urban_step_index=None` 경로(주기 평균)도 N현시에서 맞춰야 한다**

**검증 — 통과 못 하면 다음 단계 금지**
- **N=2 에서 비트 동일.** 부동소수점 연산 순서까지 같아야 한다
- 4방위 6노드 격자 회귀 — movement 78 / storage 29, 결과 비트 동일

### C-3. `grid_topology` phase 배정을 아티팩트 주입식으로

`NumSim-mine/src/models/grid_topology.py:233` 부근.

현행은 `spec["phase"] = f"{node}_p1" if axis_dir in NS_AXIS else f"{node}_p2"`.

**핵심 난제 — movement 를 stage 에 잇는 방법.**
movement 는 (접근 leg, 진출 leg) 이고 stage 멤버는 SG 번호다. **방위로 잇지 마라** —
모델의 45° 이산화는 회전을 84%만 맞추고 램프 leg 방위는 허구다(SC1001 모델 N, 실측 W) [에이전트].

경로: 신호두 `lane="<링크> <차로>"` → 링크 → 커넥터 BFS 상류 SC → 모델 leg.
코어15 신호두 218개 중 **158개(72.5%)가 유일 leg 로 귀속**된다 [에이전트].
나머지 — 상류 SC 없음 35개(경계 유입), 상류 복수 25개.

**이 60개를 어떻게 처리할지 명시하고 근거를 남겨라.** 임의 배정 금지.

**검증**
- 아티팩트가 없으면 기존 p1/p2 경로 — 비트 동일
- movement→stage 배정률을 SC 별로 보고. **배정 안 된 movement 를 전부 나열**
- 배정된 movement 의 green fraction 합이 SC 별로 물리적으로 타당한가

### C-4. 모니터 26개에 `.sig` 고정 시간표

지금 모니터 movement 는 phase 가 빈 문자열이라 `_phase_green_fraction` 이 **1.0(항상 녹색)** 을 준다.
즉 **막혀 있는 접근을 뚫려 있다고 본다.** movement 1,422개 중 672개(47.8%), 관측 차량의 40.7% 가
여기 걸린다 [실측].

- `NetworkConfig` 에 3번째 부류를 만든다 — 지금은 `signals`(통제)와 `uncontrolled_nodes`(항상녹색) 둘뿐이다.
  "고정 시간표를 갖되 리더가 못 바꾸는" 부류가 필요하다
- 영구 적색은 녹색비 **0**
- 주기 경계를 넘는 녹색창(wrap) 처리
- 모니터 노드의 offset 도 `.sig` 에서 온다

**검증**
- 영구 적색 접근에 차가 실제로 쌓이는가
- 포착률 재측정 — `scripts/verify_urban_topology_merge.py`
- **`uncontrolled_node_movement_queue_veh` / `_storage_occupancy_veh` 가 0 이 아니게 되는가**
  (정의만 있고 소비처가 0인 상태였다)

---

## D. 실시간 링크 속도 관측

Codex P1-1.

- VBS 에 `linkSpeedSums` 는 있으나 `link_speeds` 로 안 내보낸다
- 어댑터가 이를 urban travel-time delay 에 쓰도록 한다. 현재는 고정 평균속도 경로가 남아 있다 [감사]
- **same-substep zero-delay** 를 단위시험으로 제거한다 [감사]

**검증** — 링크 길이 기반 지연 스텝이 실시간 속도로 바뀌었을 때 rollout 오차 변화를 정량화

**E 와 묶어 한 번의 VISSIM 재실행으로 처리한다.**

---

## E. 액션 계약 + VBS N현시 + 주기 통일

**여기서부터 플랜트가 바뀐다. 기준선을 다시 떠야 한다.**

### E-1. 액션 CSV 스키마

현재 헤더: `sim_sec,kind,id,dsd_no,sc_no,link,lane,speed_kph,major_green,minor_green,offset,rate_vph,green_sec,metadata,readback`

- N현시로 확장. 하위호환(옛 CSV 도 읽히게) 유지 여부를 결정하고 근거를 남겨라
- **이 CSV 를 읽는 소비자를 저장소 전체에서 찾아 전부 나열하라**(python·PS·VBS).
  하나라도 빠지면 조용히 깨진다

### E-2. VBS SG→stage 매핑

`scripts/run_real_world_stackelberg_controller.vbs` 의 `SignalStateForGroup`(893~906행 부근),
`SignalCompositeStateAt`, `sigMajor`/`sigMinor`/`sigOffset`.

현행은 이름에 EB/WB 면 major, NB/SB 면 minor 로 **일괄** 덮는다. 그 결과
통제 15 SC 에서 동시녹색으로 명령하는 SG 쌍 147개 중 **73개(49.7%)가 `.sig` 3개 prog 어디에도
없는 조합**이다 [에이전트]. SC12 EBL+WBT, SC11 EBT+WBT 같은 실제 상충을 명령한다.

- **SG번호 → stage 인덱스** 매핑 테이블로 교체. 테이블 출처는 C-1 아티팩트
- 주기 계산 `cycle = major+AMBER+ALLRED+minor+AMBER+ALLRED` 를 N현시로 일반화

### E-3. 부분 적용 방지 계약

**모델만 N현시이고 VBS 가 2상이면(또는 반대면) 에러 없이 틀린 신호가 나간다.**

- 아티팩트 해시를 액션·상태 양쪽에 실어 버전을 대조
- 불일치면 **fail-closed** — 실행을 막는다

### E-4. readback 에 상충 검사 추가

지금은 요청/판독 일치만 본다(10,448/10,448) [감사]. N현시에서는
**"상충 SG 가 동시에 녹색이 아님"** 을 검사할 수 있다. 아티팩트의 stage 멤버십이 그 근거다.

### E-5. 주기 통일

- 공통 주기 후보를 확정한다. **150s 가 유력**(41개 중 23개가 이미 150s, 램프 인터페이스 전부 150s) [실측]
- prog 3개 중 150s 인 것이 있는 SC 는 그걸 쓴다(SC1 `[160,150,160]`, SC107 `[170,160,170]` 등)
- 없는 SC 는 녹색 재배분. `.sig` 의 `minGreen` 제약을 지켜라
- **통일이 필요한 이유** — 주기가 다르면 인접 신호 위상이 매 주기 밀려 연동 밴드가 안 생긴다.
  offset 은 P-Stack 의 핵심 레버다. 그리고 모델 `cycle_length` 가 스칼라라 **이미 불일치**다

**검증**
- 통일 후 인접 신호 위상 관계가 고정되는가
- 주기 변경 SC 의 movement 별 녹색시간 변화를 정량 보고
- 플랜트 1회 실행 후 `.err` 확인, `actual_sim_sec` 이 정상 진행하는가

---

## F. 신호 타이밍 oracle

Codex P0-3.

- expected `.sig` transition oracle 을 만들어 immediate/post-step readback 과 **0.5초 이내**로 비교
- **offset 부호**와 적용 cycle boundary 를 검증한다
- 감사에서 `signal_event_timing` 이 `NOT_EVALUATED` 였던 이유가 이 oracle 부재다

**offset 제어 실험은 이 게이트 통과 후에만 허용한다.**

---

## G. exit stock 과 boundary 병렬 기록

Codex P0-4.

- 출구 226개(도시부 차량의 5.1%)를 **objective 에서만 빼고 plant 상태에는 남긴다.**
  physical downstream stock·supply·backpressure 까지 제거하면 상류 action 이 과도하게 유리해진다 [감사]
- boundary objective **포함/제외 두 버전을 병렬 보고**한다
- 관련: `boundary_in` 큐 122.7대가 목적함수 밖이다. 이들은 플레이어 approach 에 서 있는 차다 [실측].
  포함 시 포착률 76.8% → 약 89%. **목적함수 정의 변경이라 G6 에 직접 영향** — 결정 근거를 남겨라

---

## H. 저류 재분류 + 파라미터 holdout 재추정

Codex P1-2.

- storage **186개**를 lane connectivity 로 **직렬/병렬 분류**. 현재 `Σ(길이×차로)×jam` 은 직렬 가정이라
  병렬 접근로를 한 storage 로 합치면 과대 산정된다 [감사]
- **jam density 를 training/holdout 으로 분리 재추정.** 현재 140.5 veh/km/lane 은 관측 런의 혼잡도에
  의존한다 — 저수요 런에서는 99.1 이 나왔다 [실측]. 물리 상수여야 할 값이 관측 의존적이다
- storage fraction(0.35/0.50)과 ramp cap(93.0~145.9)도 같은 방식으로 검증

---

## I. 한계가격 — SPSA 재검증 + 상별 FD 병렬화

### I-1. SPSA 결정적 진단 (플랜트 무관, 먼저 돌려도 됨)

**1.7 의 판정 보류를 여기서 끝낸다.**

| 검사 | 방법 | 판정 |
|---|---|---|
| **I-1a** | **레버 1개**로 SPSA vs FD | 레버가 1개면 교차항이 없어 **수학적으로 동일**해야 한다. 다르면 **구현 버그** |
| **I-1b** | 레버 1·3·5·15개로 편향 측정 | 편향이 차원에 따라 어떻게 커지는가. **4상 45레버에서 무슨 일이 날지 예측** |
| **I-1c** | 독립 시드 수렴 | 현재 시드가 `100003·refresh_count + s_idx` 라 k=32 가 k=16 의 표본을 **포함**한다. 독립 추출로 다시 재라 |

레버 제한은 `signal_price_signals` 로, 다른 채널은 `metering_price_enabled` 등을 꺼서 한다.

### I-2. 상별 한계가격

- 레버를 신호당 1 → N−1 자유도로 확장
- `_spsa_global_price_gradients` 의 `build()`(917~919행)가 `p2 = total − p1` 로 **2상을 하드코딩**한다.
  N현시면 **심플렉스 위 섭동**으로 바꿔야 한다
- 팔로워의 trust region `|p1 − ref| ≤ trust` 를 **노름 기반**으로 재정의
- green 후보 격자가 1차원 → (N−1)차원 심플렉스가 된다. **조합 폭발을 정량화하고 대책을 세워라**

### I-3. 병렬 FD

메인 세션이 배선만 해 뒀다(**검증 안 됨**).

- `stackelberg_wu_metered.py` — `price_parallel_workers`(0/1 = 직렬), `_green_price_rollouts()`,
  모듈 레벨 워커 `_price_worker_init`/`_price_worker_green`
- **검증: workers=0 과 workers=5 의 가격이 비트 동일**
- 워커에서 `_price_rollout_count` 가 부모로 안 돌아오므로 수동 보정한 부분을 확인

### I-4. 목표

**production `decide_with_info` H=3 의 p95 ≤30초, max ≤45초** [감사 기준].
현재 154.746초. 롤아웃이 98.4% 이므로 병렬화가 주된 수단이고,
`_phase_green_fraction` 메모이제이션(17%)이 곱해진다.

---

## J. 동적 검증 — **승격 판정**

Codex P2. **여기가 실질적 종착점이다.** 앞의 모든 항목을 완료해도 J 없이는
"동역학 미검증"으로 남고 감사 판정이 안 바뀐다.

1. `scripts/run_plant_fidelity_matrix.ps1`(감사 브랜치 산출)로
   **demand 0.75/1.0/1.25 × seed 13/29/47** 의 3,600초 baseline 을 **순차** 실행.
   anchor 900/1500/2100/2700 고정. **VISSIM 은 한 번에 하나만**
2. 각 anchor 에서 **H=1/3/5/10/15** 의 VISSIM paired future 를 만들고
   count, queue, storage, speed, flux, TTT, spillback onset/release 를 비교
3. green/VSL/ramp 의 low/base/high 를 paired 실행. offset 은 **F 통과 후** 추가

**합격 기준** — Spearman ≥0.70, top-action pairwise ≥0.80, 반복 부호 반전 0.

**특히 H=1 을 보라.** 현재 rho 0.4378, pairwise **0.000** 이다(H=5/10/15 는 0.985/0.921/0.862) [감사].
MPC 는 첫 구간만 집행하므로 폐루프를 좌우하는 지평이 여기다. 매크로 평균 0.8015 가 이 퇴행을 흡수하고 있다.

---

## K. 전체 감사 재실행

- `scripts/audit_plant_fidelity.py` 를 새 hash/run ID 로 재실행
- 게이트 17개 전부. 이전 결과는 PASS 14 / FAIL 2(`assignment_ties`, `runtime`) / NOT_EVALUATED 1
- **nominal·혼잡의 모든 seed 가 통과한 뒤에만** P-Stack/G6 성능을 plant 근거로 쓴다

---

## 부록 — 항목별 의존성

```
A ──┬─> C ──> D ──> E ──> F
    │        │       │
B ──┘        │       └──> G
             │
             └──> H

I  (플랜트 무관 — 언제든 병행 가능. I-1 은 지금 바로 가능)

E, F, G, H, I 완료 후 ──> J ──> K
```

- **A·B 가 선행**이다. A 미해소 시 생성기가 fail-closed 로 막힌다
- **C 까지는 플랜트 재실행 불필요** — 되돌리기 쉬운 구간
- **D+E 를 묶어 한 번의 VISSIM 재실행**으로 처리한다
- **I 는 독립**이라 언제든 병행 가능. 특히 I-1 은 지금 착수 가능
- **J 가 승격 판정**. K 는 그 확인
