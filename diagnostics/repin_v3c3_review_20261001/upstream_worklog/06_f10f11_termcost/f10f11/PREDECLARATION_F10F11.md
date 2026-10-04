# F10·F11 설계와 사전 선언 (PREDECLARATION_F10F11)

- 동결 시각: 2026-09-30 KST. 이 파일의 sha256은 같은 폴더의 `PREDECLARATION_F10F11.sha256`에 적습니다.
- 단계: **설계와 사전 선언만 했습니다.** 코드는 바꾸지 않았고, 추정기 출력이나 관문 지표도 계산하지 않았습니다. 이번에 한 일은 네 가지입니다: 코드 읽기, 파일 존재·스키마·sha 확인, 자료가 있는지(행 수·결측) 확인, W의 git status 기록.
- 사용자 결정(2026-09-30)
  - v3c2를 채택했습니다(`D:/VISSIM_runs/20260930_v3c2/reports/DECISION_v3c2_adopt.md`).
  - F10은 (a)안입니다. 셀 0에 관측 입구 속도 경계를 두고, 두 방향 모두 적용하며, 셀 0 행 v_free도 함께 고칩니다.
  - F11은 FW_W 상류 셀에 셀별(구역) FD를 둡니다. 셀 0–6은 승인되었고, 셀 7과 11–15는 이 선언이 정당화할 때만 넣습니다.
  - 셀별 FD는 우리가 새로 구현합니다. codex 코드와 codex 값은 쓰지 않습니다.
  - 원칙: 구조를 먼저 고칩니다. 매개변수는 적게, 물리적 의미가 있는 것만 둡니다. 값은 v3c2 fit 시드에서 선언한 추정기로만 정하고, 폐루프 결과에 맞추지 않습니다.
  - 코드 재핀(v3c1 → v3c2)은 아직 하지 않았습니다. v3c2 결정 상태도 없습니다.
- 태그: [실행] 이번에 명령으로 확인 / [읽음] 코드·파일에서 확인 / [추론] 시험하지 않은 판단.
- 약어. 코드는 모두 W 기준입니다.
  - W = `D:/VISSIM-merge/sim3-n31-f10f11`. 브랜치 `claude/fw-inlet-wcap-20260930`, HEAD `9ed2ef0205c9`, `git status --porcelain` 0줄입니다(`f10f11/git_status_W_design_before.txt`) [실행].
  - AFA = `evaluation/controllers/area_freeway_accounting.py`(298d7968)
  - CH = `diagnostics/demand_sweep/user_native_20260914/metanet_calibration_v1/canonical_harness.py`(b539dcad)
  - BF = 같은 폴더의 `boundary_factory.py`(fd065484)
  - LPR = `evaluation/controllers/lane_plant_runtime.py`(9d996a74)
  - LFR = `evaluation/controllers/lane_freeway_runtime.py`(1707e476)
  - ADP = `evaluation/controllers/vissim_stackelberg_adapter.py`(66876d53)
  - FFD = `evaluation/controllers/freeway_fd.py`(111ae35b)
  - RS = `evaluation/controllers/runtime_setup.py`(0566d916)
  - OC = `evaluation/controllers/obs150_contract.py`(92bb5897)
  - OL = `evaluation/controllers/obs150_lane.py`(77195751)
  - OO = `evaluation/controllers/obs150_observation.py`(957a9a2f)
  - SDM = `evaluation/controllers/sdmpc.py`(de7fc196)
  - MRS = `diagnostics/sdmpc_n31_20260924/tools/make_replay_state_v2.py`(176a23f5)
  - RDN = `diagnostics/sdmpc_n31_20260924/tools/replay_decision_n31.ps1`(5d34109f)
  - DET = `diagnostics/sdmpc_n31_20260924/obs150/obs150_detectors_v2.csv`(108debbb)
  - REF = `diagnostics/sdmpc_n31_20260924/reference_config_n31_v2.json`(6c597e25)
  - MAN = `diagnostics/sdmpc_n31_20260924/plant_n31_v2.json`(aaf49170)
  - TUN = `diagnostics/sdmpc_n31_20260924/config_n31_v2.json`(33027258)
  - SP = `…/res10_b110_20260923/train_s31_v2nc/free_speed_b110/segment_params.json`(6b40550a)
  - PAR = `…/boundary_literature_v1/boundary_fit/parameters.json`(8e4f6047)
  - GEO = MAN이 핀한 geometry(8752f0cd)
  - FIT = `scripts/fit_fd21_150s_20260908.py`(1cd0dde6)
  - SCV = `D:/VISSIM_runs/20260930_v3c2/reports/nc_analysis/static_checks_v3c2`
  - P2B = `SCV/2b/fzp_pass/<seed>.json.gz`(동결 2b FZP 패스 배열)
  - EO = `D:/VISSIM_runs/20260930_v3c2/reports/nc_analysis/eo`
  - STATIC = `nc_analysis/STATIC_CHECKS_V3C2.md`
  - PD0 = 동결 정적 점검 선언 `scratchpad/static_checks/PREDECLARATION.md`(a992341e)
  - ROBS = `D:/VISSIM_runs/20260928_sdmpc31_v3c1/sdmpc31_v3c1_nc_s31`(v3c1-s31 R-obs, 결정 상태 61개)
  - OUT = `scratchpad/f10f11`

---

## 0. 한눈에

| | F10 입구 경계 | F11 FW_W 상류 FD |
|---|---|---|
| 고치는 곳 | 두 방향 셀 0의 가상 상류 속도(AFA:365)와 셀 0 행 v_free | FW_W 셀 0–6(구역 R1)의 유효 ρc |
| 새 설정 키 (REF `freeway.*`, 없으면 현행과 비트 동일) | `component_inlet_speed`(§2.2), `component_cell_fd.v_free_row_kmh`(§2.4) | `component_cell_fd.rho_crit_effective`(§2.4) |
| 추정하는 값 | 경계는 관측이라 매개변수가 없습니다. 셀 0 v_free 행만 2개(도로마다 1개)입니다 | 구역 R1의 ρc 1개 |
| 자료 | 배포: obs150 원점 검지(MER). 오프라인: v3c2 fit 5시드 FZP(P2B 배열) | v3c2 fit 5시드 P2B |
| 관문 | G-F10-1…6 (§2.6) | G-F11-0…4 (§3.4) |
| 서술만 (관문 아님) | EQ: 배포 추정기와 오프라인 추정기의 동등성(§2.5) | 선택 점검: v3c1 R-obs 4개 상태 재생(§5) |

---

## 1. 공통

### 1.1 사전 노출 (솔직하게 적습니다)
- **이미 읽은 문서**
  - `DECISION_v3c2_adopt.md`
  - STATIC 전문
  - `GATES_AND_COMPARISON.md`의 요약, T-G4, T-D1a–c 부분
  - PD0 전문
  - `scratchpad/hybrid/HYBRID_BUILD.md` §2.2, §2.3, §11.4
  - v3c2 `README.md`: s37 inpx sha가 들어 있지만, 결과는 없습니다.
- **그래서 이미 아는 값**
  - FW_E 셀 0의 bias와 MAE, 셀 1·2의 bias(5시드, 두 모드)
  - 2b 62셀의 C, p95, 필요 배율
  - FW_E 셀 0의 v3c2 자유가지 p85: 116.7–117.4, 시드별 프레임 79–144개
  - FW_W 셀 0의 p85: 82.9–118.1, 프레임 0–66개이고 v3c2-s31은 0개
  - FW_W 셀 0–5 평균 속도의 경사, 0–40 m 속도 분포, 삽입 직후 속도
- **결과를 사실상 미리 아는 항목이 둘 있습니다.**
  - F10(ii)의 FW_E 값은 약 117입니다.
  - 그러면 2b에서 FW_E 0이 통과합니다(C 약 9,900 > p95 7,771; STATIC §5.3).
  - 따라서 G-F10-5는 정보량이 적은 관문입니다.
- **모르는 것**
  - FW_W 셀 0–6의 150 s 창별 (k, v) 산점
  - E3 추정값(§3.2)
  - FW_W P-comp의 모든 팔(한 번도 계산된 적이 없습니다)
  - F10을 켠 P-comp
  - MER 원점 속도값
  - FW_W 셀 0의 시드별 정확한 자유 프레임 수
- **이번 단계에서 새로 본 것**
  - SP 행 값: FW_E_S0 85.97, S1 116.31, FW_W_S0 87.64, S1 113.27, S6 115.02, S7 114.36
  - `SCV/2a/plant_config_2a.json` 설정값: v_min 5.0, ρ_max 180, FW_W 셀 0 행 v_free 98.1568, ρc 19.04
  - ROBS 4개 상태의 원점 검지 MER 행 수: 창당 960–992행, 그중 진입 행 480–496, v_kmh 결측 0
  - 속도값은 계산하지 않았습니다.

### 1.2 금지 자료
- 봉인 s37은 v3c1·v3c2 모두 열지 않습니다(`s37_*` 폴더 전체).
- 다음도 열거나 쓰지 않습니다: `*_rm`, 59/61/67, 64cf-s59/s61/s67 수치, codex 코드와 값.
- `D:/VISSIM_runs/20260927_v3c1/{reports,work,scripts}`와 그 README는 PD0 §1.2를 이어받아 열지 않습니다.

### 1.3 표기
- 망 접두어를 붙입니다: v3c2-s31, v3c1-s31 R-obs.
- 망이 다르면 같은 시드 번호라도 짝 비교가 아닙니다.

### 1.4 자료·코드가 있는지 점검한 결과 (이번 단계)
1. **v3c2 fit 런에는 FZP만 있습니다** [실행 `ls s{31,41,43,47,53}_v3c2nc/run/vissim_eval`].
   - `.mer`, obs150, 결정 상태가 없습니다.
   - 그래서 배포 추정기(obs150)는 v3c2에서 바로 평가할 수 없습니다. 오프라인 등가물은 FZP로 만듭니다.
2. **P2B 배열 5시드** [실행, 모양만 확인]
   - n, sum_v, stopped, D_m은 각각 [1800 × 62]입니다. 프레임은 t = 5K + 0.1(K = 0..1799), 열은 도로×31 + 셀입니다.
   - v40 {n, sum_v}는 FW_E·FW_W 각각 1,800 프레임입니다.
   - 따라서 다음 입력이 FZP를 다시 읽지 않아도 모두 있습니다: F10 오프라인 특성(900.1 s 절단점의 755.1–900.1 s 창 포함), §2.3의 v_free, §3.2의 E3, LOSO.
   - P2B는 2a 패스와 비트 동일합니다(`SCV/2b/crosscheck_vs_2a_pass.json`, STATIC §7).
3. **`SCV/2b/cells_2b.csv`에 시드별 p95 열이 있습니다** [실행]: `p95_150_v3c2-s31` … `-s53`. LOSO 입력입니다.
4. **EO 5시드**에 `cells_30s.csv`, `flows_30s.csv`, `boundaries_30s.csv`, `geometry.json`, `manifest.json`이 있습니다 [실행]. BF(83-186)로 FW_W P-comp 경계를 만들 수 있습니다 [읽음].
5. **원점 검지** [실행 DET:279-285]
   - FW_E: 960278–960281. link 74 차로 1–4, pos 40.000000, orientation down, 조각 0–40 m.
   - FW_W: 960282–960284. link 26 차로 1–3, 같은 방식.
   - 동결 2a의 0–40 m 구역(`SCV/code/2a/fzp_pass.py:106-111`, PD0 §1.7)과 같은 곳입니다.
6. **결정 시점 state_json이 노출하는 것** [실행 ROBS `state_002250.json` 키]
   - 최상위 `obs150`(raw): window (T−150, T], detectors / detectors_cum, mer chunk(jsonl), err chunk, frames current(T) / previous(T−150), source_cumulative_vehs
   - `lane_plant_observation`: cadence `decision_150s`
   - `local_observation.link_speeds_kph`: 링크 전체 평균입니다(link 74는 2.70 km, link 26은 3.82 km). 입구 속도로는 쓸 수 없습니다.
   - 파생 문서와 관측 문서에는 원점 속도가 없습니다.
     - OL:337-353 `source_boundary`에는 대수만 있습니다(admitted_window, recent_vph, backlog).
     - OO:773-787 lane observation에는 `frames`(현재 프레임 1개)와 source_boundary만 있습니다.
   - **150 s 창의 인과적 입구 속도는 MER 행의 v_kmh(OC:339-355) 하나뿐입니다.** 원점 검지의 진입 행(ordinal ≠ None)만 쓰고, 창 배정은 OC:435-470 `assign_window`가 합니다 [읽음].
   - ROBS 2250/2700/3600/4950: 원점 검지 7개 모두 행이 있고 v_kmh 결측은 0입니다 [실행].
7. **ROBS `vissim_eval`**: FZP 1,183,596,914 B와 MER 165,836,282 B가 있습니다 → EQ(§2.5)를 할 수 있습니다 [실행].
8. **재생 도구** [읽음]
   - MRS prepare/compare는 MRS:1-43입니다. RDN `-Root`는 provenance 경로를 W로 다시 잡습니다(RDN:5-17).
   - 튜닝은 provenance 경로를 다시 잡을 뿐이고 덮어쓰는 인자가 없습니다(RDN:92-114).
   - SDMPC 컨트롤러 이름은 `wu-link`입니다(`D:/VISSIM_runs/20260929_hybrid_offline/base_wu_900/replay/replay_run.json`).
   - ROBS는 no-control 런이라 직전 행동에 `sdmpc_state`가 없습니다. SDM:503-505가 이것을 가격 0인 첫 SDMPC 결정으로 처리하므로, 네 상태 모두 SDMPC 재생이 됩니다.
9. **W@9ed2ef0과 ROBS 동결 루트(5323faa4)는 코드가 같습니다** [실행 `git diff --name-only`]. 다른 것은 worklog 문서 34개와 json 1개뿐입니다.
10. **잠복 결함은 이번 범위에서 고치지 않습니다** [읽음]
    - `state_response` 셀 번호 검사(FFD:322-330)는 RS:59를 거쳐 CH:301에서 돕니다. 그런데 31셀 분할(CH:302-317)은 그 뒤입니다.
    - F11은 state_response를 쓰지 않습니다. 새 키 검사는 분할 뒤(CH:318 이후)에 둡니다. 쓰는 셀 번호도 최대 6으로 21보다 작습니다.
11. **P-comp 비용**: 시드·모드당 약 24 s입니다(`SCV/2a/pcomp/*.json` elapsed). 팔을 늘려도 부담이 작습니다 [실행].

### 1.5 입력 핀 (sha256 앞 12자)
- 시작할 때 다시 확인합니다. 다르면 중단합니다 [실행 이번 값].

| 파일 | sha |
|---|---|
| P2B s31 / s41 / s43 / s47 / s53 | e0f15bb51e5d / 52993a21aa56 / cdede9a07c86 / a12ecd836c2c / f816df8fe4cd |
| `SCV/2a/fzp_pass` s31…s53 | aaf9cab9cb75 / 9cea16344814 / 02eba213ccd6 / 299d9f9c5ad1 / ae6ffb4aa281 |
| `SCV/2a/pcomp` conditioned s31…s53 | a41fd28765a1 / 570807e2d191 / 465f1bd54091 / ff46dc1233cc / 70dbc03a638d |
| `SCV/2a/pcomp` history s31…s53 | 5e49cbf5a2e8 / 319e9d374458 / e6710d4bec38 / 1301fe569add / 9f7beffef3a6 |
| `results_2a.json` / `results_2b.json` / `cells_2b.csv` | 5aed001b9fad / 84fdf7ec35b6 / c8242c41478d |
| `plant_config_2a.json` / `plant_config_2b.json` | 3aec519e1354 / da2863fd8dbc |
| MAN / REF / PAR / GEO / SP / 분할 / TUN / DET | aaf49170 / 6c597e25 / 8e4f6047 / 8752f0cd / 6b40550a / 9769b3a4 / 33027258 / 108debbb |

### 1.6 실행 규칙
- **쓰기**
  - W와 OUT에만 씁니다.
  - 런 폴더, 다른 워크트리(`sim3-n31-v3c1`, `-urban-b2`, `-termcost`, `-hybrid-base` 등), `D:/VISSIM-merge/frozen/*`은 읽기만 합니다.
- **금지 실행**
  - VISSIM과 cscript는 시작하거나 끄지 않습니다.
  - 다음 시험은 실행하지 않습니다: `test_b1a_watchdog_attempt_launch.py`, `run_plant_fidelity_matrix`, `test_runner_ps1_obs150.py`, `test_native_vbs_clock.py`, `test_tools_launch.py`, `test_tools_replay.py`, real_watchdog.
- **환경**
  - BELOW_NORMAL, `PYTHONHASHSEED=0`(vendor `src/models/state.py:1306`의 set 순회 합 때문), `python -B`, `PYTHONDONTWRITEBYTECODE=1`, `NUMBA_CACHE_DIR=OUT/nbc`
  - `NUMBA_NUM_THREADS`: 추정과 P-comp는 1, 재생은 4로 고정합니다(모든 팔 같게).
  - 무거운 작업은 한 번에 하나만 돌립니다.
- **git**
  - 작업 전후로 W의 `git status`를 저장합니다.
  - 커밋은 W 안에서만, 경로를 명시해서 합니다. 저자는 Ming2you / alsrjsrb1915@snu.ac.kr이고, 메시지 끝에 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`을 붙입니다.
  - push와 `--renormalize`는 하지 않습니다.
- **재생 폴더**: `OUT/replays/<이름>`(C:)에 둡니다. 런 폴더와 볼륨이 달라서 MRS가 sha를 확인한 사본을 만듭니다(HYBRID §11.4).

### 1.7 산출물 (OUT 아래)
- `estimators/`: §2.3·§3.2·LOSO 추정값 JSON과 sha
- `f10_2a/`: 2a 팔
- `f11_2b/`: 새 plant 62셀 C
- `loso/`
- `pcomp_fww/`: FW_W 팔
- `eq/`
- `replays/`
- `code/`: 하네스 사본과 동결본 대비 diff
- `logs/`
- `REPORT_F10F11.md`

---

## 2. F10 입구 경계

### 2.1 지금 plant가 셀 0 상류 속도를 정하는 곳 [읽음]
- **코드 한 줄을 두 방향이 같이 씁니다.**
  - AFA:365 `upstream_speed = (bu_v[-1] if buf_n > 0 else net.v_free) if i == 0 else speeds[i - 1]`
  - buf_n은 0이어야 합니다(AFA:116-117). 그래서 셀 0의 상류 속도는 늘 `net.v_free`입니다.
- **경로**
  - 배포: LPR:97 component → LFR:28 `component._config(road, PAR by_direction)`로 방향별 cfg를 만듦 → LFR:123 `AFA._freeway_substep_events`
  - 오프라인: CH:713 같은 `_config` → CH:1016-1017 같은 AFA
- **값**
  - `net.v_free`는 방향별 cfg의 스칼라입니다. CH:575 `net.v_free *= v_free_multiplier`를 거쳐 FW_E는 110.00000000000003, FW_W는 123.20000000000002입니다(`SCV/2a/plant_config_2a.json`) [실행].
  - 셀별 V(ρ)가 쓰는 행 v_free는 따로 있습니다: CH:583 → ADP:9440 `_fw_seg_param_dict` → ADP:9485-9495. 셀 0 행은 FW_E 85.97, FW_W 98.1568입니다.
  - 즉 셀 0 상류 속도는 관측값도 아니고 셀 0 행 값도 아닙니다. **방향 전체의 스칼라**입니다.

### 2.2 새 키 A: `freeway.component_inlet_speed`
REF에 추가합니다. 없으면 현행과 같습니다.

- **형태**
  - `{"FW_E": {"source": "obs150_source_station", "window_sec": 150, "statistic": "space_mean", "min_vehicles": 5}, "FW_W": {같은 필드}}`
  - 필드 집합은 고정입니다. 모르는 필드나 도로는 거부합니다.
- **의미**
  - 도로 r의 셀 0 가상 상류 속도를 u_r(T)로 둡니다.
  - u_r(T)는 결정 시각 T(오프라인은 절단점 T) 직전 150 s, 즉 (T−150, T] 동안 입구 0–40 m를 지난 차량의 **공간평균 속도**입니다.
  - 이 값을 지평 전체에 그대로 씁니다: 1 s 적분 단계 전부, 후보 롤아웃 전부, SDMPC 3블록 전부.
  - 값에 상한이나 하한을 두지 않습니다.
- **배포 추정기 (obs150, 인과적)**
  - 표본: T의 bundle에서 OC:435-470 `assign_window`가 이 구간에 배정한 진입 행(ordinal ≠ None) 중 검지 번호가 D_r이고 v_kmh ≠ None인 것
    - D_FW_E = {960278…960281}, D_FW_W = {960282…960284}
  - 계산: u_r = N / Σᵢ 1/max(vᵢ, v_min). 점 검지 속도에서 공간평균을 내는 표준식(조화평균)입니다.
    - v_min은 그 도로 cfg의 `net.v_min`(5.0 km/h)입니다. 0으로 나누는 것을 막는 하한입니다.
  - 아직 파일에 쓰이지 않은 꼬리((T−1, T], OC `tails`)는 빼고, 그 수를 감사 기록에 남깁니다.
  - N < 5이면 대체값을 씁니다. 대체값은 그 도로 cfg의 `net.v_free`로, 키가 없을 때와 같은 객체입니다. 대체했다는 표시도 남깁니다.
- **오프라인 등가물 (FZP, P-comp용)**
  - 프레임 K(T) = {t_k = 5k + 0.1 : T − 150 < t_k ≤ T}로 30개입니다.
  - P2B의 `v40[r]` n, sum_v를 씁니다. 정의는 `fzp_pass.py:106-111`과 같습니다(원점 링크 74/26, 0 ≤ POS < 40 m).
  - 계산: u_r = Σ_k sum_v / Σ_k n. 체류시간 가중 Edie 공간평균입니다.
  - Σ n < 5이면 같은 대체값을 씁니다.
  - 900.1 s 절단점은 755.1–900.1 s 프레임을 씁니다(J15).
- 두 추정기는 같은 물리량(입구 흐름의 공간평균 속도)을 서로 다른 방법으로 잽니다. 차이는 §2.5에서 잽니다.
- **코드 자리.** 의미는 여기서 고정하고, 구현 세부는 구현 단계가 정합니다.
  - a. CH: `__init__`에서 분할(:302-318) 뒤에 키를 검사하고 보관합니다.
  - b. `CH.rollout`에 키워드 `inlet_upstream_speed_kmh={road: float}`를 추가합니다.
    - 키가 있는 도로를 굴릴 때는 필수이고, 빠지면 오류입니다.
    - 키가 없는데 이 인자를 주면 거부합니다.
    - `_config`(:713) 직후에 `cfg.network.freeway_inlet_upstream_speed_kmh = {road: 값}`을 둡니다.
  - c. AFA:365의 `net.v_free`를 `(getattr(net, 'freeway_inlet_upstream_speed_kmh', None) or {}).get(link, net.v_free)`로 바꿉니다. 속성이 없으면 같은 float 객체가 나오므로 비트 동일합니다.
  - d. 배포(LPR v2): 키가 있을 때만 u_r를 계산합니다.
    - 입력: `observe_state`가 가진 현재 raw의 같은 bundle(OC `load_bundle` + `assign_window`)
    - 결과를 `freeway.configs[road].network`에 싣고, `binding['inlet_upstream_speed'] = {road: {value, n, fallback, tails}}`를 추가합니다.
    - obs150 derived 문서와 lane observation 문서는 바꾸지 않습니다. derived sha가 관측 신원의 일부이기 때문입니다(OO:786).
    - 값은 cfg와 함께 spawn 작업자에게 넘어갑니다(FFD:279와 같은 방식).
  - e. 오프라인 P-comp는 (b)의 인자로 FZP 값을 넣습니다.
- **키가 없을 때:** (b) 인자가 없고, (c)는 `net.v_free`이며, (d)는 계산도 기록도 하지 않습니다. 그래서 결정 CSV, 목표, derived가 비트 동일해야 합니다(§4).

### 2.3 셀 0 행 v_free 다시 구하기 (두 방향)
- **규칙.** SP S1 행 규칙("N>=5, rho<10; sample p85", SP `FW_E_S1.v_free_source`)을 동결 창에 적용합니다.
  - 자료: P2B n, sum_v의 셀 0 열(FW_E 열 0, FW_W 열 31). 프레임 K = 180..1799(900.1–8995.1 s), fit 5시드.
  - 선택: n ≥ 5이고 n/(L·λ) < 10 veh/km/차로인 프레임
    - FW_E: L 0.5263 km, λ 4 → n ≤ 21
    - FW_W: L 0.5461 km, λ 3 → n ≤ 16
  - 값: 프레임 평균 속도 sum_v/n을 5시드 합쳐 `numpy.percentile(·, 85)`(선형 보간)
  - 최소 자료: 합친 프레임이 150개 이상이고, 30 프레임 이상인 시드가 3개 이상일 것
    - FIT:90의 "자유 150 s 창 ≥ 5개"를 5 s 프레임 수로 옮긴 값(5 × 30)입니다.
    - 시드 조건은 3/5 관례를 따릅니다.
  - 못 채우면 현행 SP 행을 유지합니다(FW_E 85.97, FW_W 87.64). 대체했다는 사실을 보고합니다.
- **행 값의 뜻: 배율을 곱하기 전의 측정 원값입니다.**
  - SP의 다른 행도 모두 측정 p85이고, CH:583에서 `v_free_multiplier`가 한 번 곱해집니다.
  - 셀 0도 같은 경로를 탑니다. FW_W는 1.12, FW_E는 1.0000000000000002가 한 번 곱해집니다.
  - 스칼라 `net.v_free`는 바꾸지 않습니다.
- **F10(i)과 함께 적용합니다(사용자 결정).** 행 값만 올리면 혼잡 때 plant가 더 빨라져 2a 편향이 커질 수 있습니다(STATIC §5.3 [추론]). 이 효과는 팔 A_ii로 서술만 합니다.

### 2.4 새 키 B: `freeway.component_cell_fd`
F10(ii)와 F11이 함께 씁니다. REF에 추가하고, 없으면 현행과 같습니다.

- **형태**
  - `{"FW_E": {"0": {"v_free_row_kmh": x}}, "FW_W": {"0": {"v_free_row_kmh": y (대체되면 없음), "rho_crit_effective": ρ}, "1" … "6": {"rho_crit_effective": ρ}}, "provenance": {"estimator_json": 경로, "sha256": …}}`
- **검사 (CH `__init__`, 분할 뒤)**
  - 도로가 roads 안에 있어야 합니다.
  - 셀 번호는 10진 문자열이고 그 도로의 물리 셀 수(31)보다 작아야 합니다.
  - 필드는 {v_free_row_kmh, rho_crit_effective}의 부분집합이어야 하고, 값은 유한해야 합니다.
  - v_free_row_kmh ∈ [80, 140](FIT:30-31), rho_crit_effective ∈ [15, 60](FIT:33 물리 창)
- **적용 (CH `_config` 한 곳)**
  - v_free_row_kmh: CH:582 반복 **직전**에 행 v_free를 바꿉니다. 그러면 CH:583에서 배율이 한 번 곱해집니다.
  - rho_crit_effective: CH:582-589 반복 **직후**에 행 rho_crit에 그대로 넣습니다. 배율 0.68을 곱하지 않습니다.
  - 배포도 오프라인도 `_config`를 지나므로(LFR:28, CH:713) 적용 자리는 하나입니다.
  - 전체 cfg의 소비자도 LPR:441로 같은 행을 봅니다. 빈 셀 초기 속도(LPR:587, CH:727-728)도 새 행 v_free를 씁니다.
- **바꾸지 않는 것:** 스칼라 `net.rho_crit`는 그대로 둡니다.
  - 그것을 읽는 곳은 AFA:373(말단 셀)과 램프 수용 조회(`_mn.effective_rho_crit` = vendor `src/models/metanet.py:61-66`, AFA:63)입니다.
  - 해당 셀은 FW_W 셀 30과 합류 셀 8/10/18/22로, 모두 범위 밖입니다 [읽음·추론].
- **"배율 한 번" 점검.** 2b §3.1의 3단계를 이렇게 보정합니다.
  - 덮은 셀: 유효 v_free가 행 값 × 배율(부동소수 곱 그대로)과 같고, 유효 ρc가 선언값과 정확히 같아야 합니다.
  - 나머지 셀: 키가 없을 때의 cfg와 비트 동일해야 합니다.

### 2.5 측정 동등성 EQ (서술. 배포의 전제 조건)
- **목적.** 관문은 오프라인(FZP) 추정기로 판정하지만 배포는 MER 추정기로 동작합니다. 두 추정기가 같은 양을 재는지 확인합니다.
- **자료**
  - 두 추정기를 한 런에서 잴 수 있는 것은 ROBS뿐입니다(v3c1, 입구 DSD 40).
  - T ∈ {1050, 1200, …, 9000}(54개), 두 도로
  - 배포 쪽: 구현된 함수를 ROBS 상태의 bundle에 그대로 적용합니다(읽기만).
  - FZP 쪽: ROBS `vissim_eval` FZP의 (T−150, T] 프레임 중 0.1 (mod 5)인 것만 씁니다. SIMSEC 0.10 행은 버립니다.
- **보고:** 도로별로 |Δ| 중앙값·p90, 부호 평균, 대체 발생 수를 냅니다.
- **"동등"의 기준:** |Δ| 중앙값 ≤ 5 km/h이고 p90 ≤ 15 km/h(J17)
- **동등하지 않으면**
  - F10의 오프라인 판정은 그대로 둡니다.
  - 배포 제안은 사용자 결정으로 넘깁니다.
  - 추정기를 바꿔 다시 돌리지 않습니다.
- **한계.** v3c1에는 입구 자유류(> 100 km/h) 구간이 거의 없습니다. 그 영역의 동등성은 시험되지 않습니다.

### 2.6 F10 팔과 관문
- **하네스는 동결 2a 방법 그대로입니다.**
  - PD0 §2.2의 D1–D6, 절단점 53개, 지평 150 s, 1 s 적분, BF `build_window`, 유효성 ≥ 48/53
  - bias와 MAE 정의는 `SCV/code/2a/analyze_2a.py:117-146`과 같습니다.
  - 바뀌는 것은 plant 설정(키 A·B)과 u_E(T) 입력뿐입니다.
  - 코드는 `OUT/code/pcomp_f10.py`로 복사하고, `pcomp.py`와의 diff를 보고합니다.
- **팔 (FW_E, 두 모드)**
  - BASE: 동결 v3c2 결과(`SCV/2a/pcomp`, `results_2a.json` 5aed001b). W가 이것을 재현하는지는 ID-0로 확인합니다.
  - A_i: 키 A만
  - A_ii: 키 B(FW_E 0 v_free)만
  - NEW: A + B
- **관문 (NEW, 전부 만족하면 F10 PASS)**
  - G-F10-1: conditioned_diagnostic 모드에서 |bias₀| < 15대인 시드가 3/5 이상
  - G-F10-2: conditioned 모드 셀 0 MAE가 BASE보다 작은 시드가 5/5
  - G-F10-3: conditioned 모드 셀 1·2 각각 |bias_NEW| − |bias_BASE| ≤ 3.0대. 모든 시드에서
  - G-F10-4: history_forecast 모드에서 |bias₀| < 15인 시드가 3/5 이상
  - G-F10-5: 2b(§3.4 G-F11-1과 같은 계산)에서 FW_E 0이 위반이 아님(C ≥ 동결 p95 7,771). 사전 노출로 결과를 거의 아는 관문입니다(§1.1).
  - G-F10-6: 동일성 ID-0…ID-3(§4)
  - 유효 절단점이 48개 미만인 NA 시드는 그 조건을 채우지 못한 것으로 셉니다.
- **FW_W 쪽 F10**은 §3.4의 FW_W P-comp에 들어 있습니다.
  - F11이 FAIL일 때만 G-F10-W로 따로 판정합니다. 기준은 두 가지입니다.
    - F10 팔의 셀 0 MAE가 BASE보다 작은 시드가 3/5 이상
    - 셀 1–30 각각, "악화"(§3.4 정의)가 아닌 시드가 3/5 이상

---

## 3. F11 FW_W 상류 FD

### 3.1 범위: 구역 R1 = FW_W 셀 0–6. 셀 7과 11–15는 넣지 않습니다
- **범위는 위반 목록이 아니라 도로 구조로 정했습니다.**
  - R1은 link 26의 3차로 구간 중 포트가 없는 연속 구간입니다. 물리 셀 0–6, 0–3,400.95 m입니다. 셀 0–5는 각 0.5461 km, 셀 6은 0.1246 km입니다 [읽음 PD0 §1.6 표].
  - VISSIM에서 FW_W 대기열이 쌓이는 저장 구간이고, 엮임 병목(10479·10480·10491, 셀 7–9)의 상류입니다.
- **셀 7을 뺀 이유**
  - 셀 7에는 진출 10479(3,425.4 m)가 있습니다. 엮임 병목의 머리입니다.
  - 이 셀의 (k, v)에는 차로 변경·진출 차량이 섞여 있어서 도로 FD라고 보기 어렵습니다.
  - plant가 VISSIM처럼 엮임에서 대기열을 만들려면 셀 7–9의 용량이 R1보다 낮게 남아 있어야 합니다. R1에 맞춘 ρc를 셀 7에 주면 병목이 약해집니다 [추론].
  - 위반 크기도 작습니다: −41 veh/h이고, 150 s에서만(265창 중 18창) 위반이며, 300 s에서는 통과합니다(STATIC §3.2).
  - 반론: 셀 7은 부모 행 6을 셀 6·8·9와 함께 씁니다. 그러나 이 공유는 21셀 부모 격자에서 생긴 것입니다. 정제 분할이 이 부모를 나눈 이유가 바로 포트입니다.
- **셀 11–15를 뺀 이유**
  - link 120, 4차로 급, 합류 10482 하류로 R1과 다른 도로 구간입니다.
  - 150 s 단기 첨두에서만 위반이고 300 s에서는 통과합니다. 필요 배율은 0.681–0.695로 현행 0.68과 0.1–2.2%밖에 차이 나지 않습니다(STATIC §3.2).
  - 구조 기준으로 고치려면 link 120에서 포트가 없는 4차로 셀 전체(11–15, 17, 20, 21, 23–30)를 같이 봐야 합니다.
    - 위반한 다섯 셀만 고르면 범위를 위반 목록에 맞추는 셈이 됩니다.
    - 전체를 보면 방향 배율을 다시 적합하는 일이 되고, 승인 범위("상류 셀")를 벗어납니다.
- **결과 (명시합니다): 이 범위로는 "62셀 위반 0"에 결정적으로 닿을 수 없습니다.**
  - 범위 밖 셀의 C는 바뀌지 않습니다. p95는 VISSIM 자료입니다.
  - 그래서 FW_W 7, 11, 12, 13, 14, 15의 단기 첨두 위반 6개가 그대로 남습니다.
  - 따라서 2b 관문을 다음 세 조건으로 다시 적습니다(§3.4): 범위 셀 위반 0, 범위 밖 C 비트 동일, 남는 위반 집합이 정확히 이 6개.
  - 남는 6개는 후속 항목 F11b로 사용자에게 넘깁니다. F11b는 FW_W 엮임 구간과 4차로 구간의 FD를 v3c2 재핀 때 방향 재적합과 함께 다루는 항목입니다.
- **셀별 7개가 아니라 구역 하나로 한 이유**
  - 같은 링크, 같은 차로 수, 포트 없음이면 FD도 같아야 합니다.
  - 매개변수 7개는 잡음까지 맞춥니다.
  - 셀별 값은 이질성 서술로만 냅니다.

### 3.2 추정기 E3: 혼잡 가지만 쓰는 1-매개변수 FD 적합
- **자료:** P2B n, sum_v의 FW_W 셀 0–6 열. 창은 2b와 같은 150 s 창 j = 0..52(t_k ∈ [900.1 + 150j, 1045.1 + 150j], 30 프레임)입니다. fit 5시드라 셀당 265창입니다.
- **창 값**
  - k_w = Σn / (30·Lᵢ·λᵢ) [veh/km/차로]
  - v_w = Σ sum_v / Σ n [km/h]. 스냅숏 공간평균으로, plant 초기 상태를 만드는 추정기(LPR:429)와 같습니다.
  - 흐름(D_m)은 쓰지 않습니다. 그래서 2b 관문 통계(궤적 Edie 흐름 p95)와 독립입니다.
- **혼잡 창:** 평균 n ≥ 5이고 v_w < 60 km/h. 동결 2a의 혼잡 정의(V_CONG 60, NMIN 5; `analyze_2a.py:16-21`)를 창에 적용한 것입니다.
- **모형**
  - Vᵢ(k; ρc) = v_f,ᵢ · exp(−(1/aᵢ)(k/ρc)^aᵢ)
  - v_f,ᵢ는 셀 i의 유효 행 v_free입니다. 배율 1.12가 포함되고, 셀 0은 §2.3의 결과를 씁니다.
  - aᵢ는 행의 `metanet_a_m`(1.7029)입니다.
  - v_f와 a는 고정하고 ρc 하나만 추정합니다.
- **목적 함수**
  - ρc_R1 = argmin_{ρc ∈ [15.00, 60.00], 격자 0.01} Σ_{i∈R1} Lᵢ · Σ_{w∈혼잡} (v_w − Vᵢ(k_w; ρc))²
  - 동률이면 작은 값을 고릅니다.
  - FIT:36-53의 속도 잔차 최소제곱을 매개변수 1개로 줄인 것입니다.
- **식별 조건.** 하나라도 어기면 F11을 적용하지 않습니다(G-F11-0 실패). 보고하고 사용자 결정을 받습니다.
  - 합친 혼잡 창이 40개 이상
  - 그 창들의 k가 p95 − p05 ≥ 10 veh/km/차로
  - 해가 경계에서 0.05 안쪽이 아닐 것
- **혼잡 가지만 쓰는 이유** [추론]
  - 자유 가지에서는 v_f 불일치(plant가 1.12배)가 ρc를 아래로 끌어 용량을 깎는 인공물이 생깁니다.
  - ρc가 식별되는 곳은 혼잡 가지입니다.
- **제안된 두 추정기를 쓰지 않은 이유**
  - 흐름 최대점의 밀도: R1은 하류 병목의 저장 구간입니다. 관측 흐름은 이 구간 자체의 용량이 아니라 병목 방류에 막힙니다. 혼잡 가지의 흐름이 평평해서 최대점 위치가 잡음에 좌우됩니다 [추론].
  - p99 용량: 같은 이유로 병목 방류를 잽니다. 게다가 같은 표본에서는 p99 ≥ p95라서, 2b 관문이 표본 안에서 동어반복이 됩니다. 금지된 "p95 바로 위" 정의와 같은 성질입니다.
- **값 기록:** `OUT/estimators/f11_rho_c.json`에 적습니다(ρc_R1, 셀별 서술 ρc, 창 수, 목적함수 곡선, 입력 sha). 한 번 계산하고 고정합니다. 관문 결과를 본 뒤 다시 추정하지 않습니다.

### 3.3 적용
- **범위 셀:** 키 B FW_W "0"…"6"의 `rho_crit_effective` = ρc_R1입니다. 이 값은 이미 유효값이므로 방향 배율 0.68을 다시 곱하지 않습니다.
- **다른 셀:** SP 행 × 0.68 그대로입니다.
- **셀 0:** §2.3의 `v_free_row_kmh`(대체되었으면 없음)와 ρc를 함께 가집니다.
- **건드리지 않는 것:** v_free, a, τ, ν, κ, δ, φ

### 3.4 관문 (전부 만족하면 F11 PASS)
- **G-F11-0: E3가 식별됩니다.**
- **G-F11-1 (2b)**
  - 새 plant로 62셀 C를 동결 2b 절차로 다시 계산합니다: `plant_config_2b.py`, PD0 §3.1–§3.2. "배율 한 번" 점검은 §2.4의 보정판을 씁니다.
  - p95는 동결 값(`results_2b.json` 84fdf7ec)을 씁니다.
  - 통과 조건 세 가지:
    - 범위 S = {FW_E 0} ∪ {FW_W 0..6}에서 위반(C < p95)이 0개
    - 나머지 54셀의 C가 BASE와 비트 동일
    - 남는 위반 집합이 정확히 {FW_W 7, 11, 12, 13, 14, 15}
  - FW_E 0은 F10 몫입니다(G-F10-5).
- **G-F11-2 (LOSO, 한 시드 빼기)**
  - 시드 s를 뺀 4시드로 §2.3(FW_W 셀 0 v_free, 같은 최소 자료 규칙)과 E3를 다시 추정합니다.
  - 그 값으로 만든 C_i^(−s)(i = 0..6)가 빠진 시드 s의 셀별 p95_150(`cells_2b.csv` 시드 열) 이상이면 그 접힘은 통과입니다.
  - 통과 접힘이 4/5 이상이어야 합니다. 어느 접힘에서 식별이 실패하면 그 접힘은 실패로 셉니다.
- **G-F11-3 (FW_W 한 스텝 예측)**
  - P-comp를 FW_W에 똑같이 적용합니다: D1, D2, D3는 FW_W만, D4–D6, 절단점 53개, 150 s, conditioned_diagnostic 모드
  - 셀별 재고 MAEᵢ = 유효 절단점 평균 |n̂ᵢ(T+150) − nᵢ(T+150)|
  - 범위 셀 i = 0..6 각각: MAE_NEW,i < MAE_BASE,i인 시드가 3/5 이상
  - 범위 밖 셀 i = 7..30 각각: "악화"가 아닌 시드가 3/5 이상
    - 악화 = MAE_NEW > 1.10·MAE_BASE이고 동시에 MAE_NEW − MAE_BASE > 0.5대 (J11)
  - 유효 절단점이 48개 미만인 시드는 "개선 아님"이자 "악화"로 셉니다.
- **G-F11-4: 동일성 (§4)**
- **팔 (FW_W, 두 모드)**
  - BASE: 키 없음, W
  - F10: 키 A FW_W + 키 B FW_W 0 v_free
  - F11: 키 B ρc만
  - NEW: F10 + F11
  - 관문은 NEW로 판정합니다. 단 F10이 FAIL이면 F11 팔로 판정합니다. 이 전환은 F10 결과로만 정해집니다(§6).
  - history_forecast 모드와 나머지 팔은 서술만 합니다.
  - FW_W P-comp 기준선은 아직 한 번도 계산된 적이 없어서 노출이 없습니다.

---

## 4. 동일성 점검 (키가 없으면 비트 동일. F10·F11 공통 관문)
- **ID-0 (P-comp 재현)**
  - W 구현 커밋에 키 없는 REF로 FW_E P-comp를 5시드 × 2모드 돌립니다.
  - `SCV/2a/pcomp`의 모든 절단점 레코드(n_hat, v_hat, 진단 수치)와 같아야 합니다. 경과 시간과 우선순위 필드는 제외합니다.
- **ID-1 (결정 재생, 과제 지정)**
  - ROBS 900, 2250, 4950 s를 no-control로 재생합니다(launch_plan의 컨트롤러).
  - 순서: MRS prepare → RDN `-Root W`(구현 커밋) → MRS compare
  - 결과가 IDENTICAL이어야 합니다: derived, CSV 바이트, 제어 필드, 행 계약.
- **ID-2 (SDMPC 재생 짝)**
  - ROBS 2250, 2700, 3600, 4950에서 `-Controller wu-link`, 기본 튜닝으로 재생합니다.
  - A0 = W@9ed2ef0(코드를 바꾸기 **전에** 먼저 돌림), A1 = W@구현 커밋(키 없음)
  - A0과 A1이 같아야 하는 항목: CSV 바이트, 제어 필드, 목표·held의 repr, derived, n31_binding, 선택 후보와 trial rows. HYBRID §2.2와 같은 항목입니다.
  - 다르면 `NUMBA_NUM_THREADS=1`로 A0·A1을 한 번 더 돌려 스레드 비결정성인지 가린 뒤 판정합니다.
- **ID-3 (설정 재현)**
  - 키 없는 W로 `plant_config_2b.json`(da2863fd)과 `plant_config_2a.json`(3aec519e)을 다시 만듭니다. sha가 같아야 합니다.
- **단위 시험 (구현 단계)**
  - 키 검사의 거부 사례
  - 대체값 경로
  - 속성이 없으면 `net.v_free`와 같은 객체
  - 배율 한 번
- **하나라도 실패하면 중단합니다.** 관문은 판정하지 않습니다.
- ID-2를 따로 두는 이유: no-control 재생(ID-1)은 AFA 스텝을 거의 지나지 않을 수 있습니다 [추론].

## 5. 선택 점검 (서술. 관문이 아니고 v3c2 증거도 아닙니다)
- **상태**
  - ROBS T = 2250, 2700, 3600, 4950 s. v3c1 NC 궤적에서 FW_E 입구가 포화된 시기입니다.
  - 각 결정은 직전 no-control 행동에서 시작하므로 가격 0인 첫 SDMPC 결정입니다(SDM:503-505).
- **팔**
  - A1: 기본, 키 없음. ID-2와 같은 재생입니다.
  - A2: 키 A 두 방향 + 키 B(F10(ii)·F11 값)
    - F10 값은 그 상태의 MER에서 배포 추정기가 계산합니다. v3c1 입구는 DSD 40입니다.
    - F10(ii)·F11 값은 v3c2에서 추정한 값을 v3c1 망 상태에 얹은 것입니다.
- **보고 (T마다)**
  - F10 입력: u_E, u_W, N, 대체 여부, 꼬리
  - 선택 행동: VSL(66행 → 구역 명령), 미터 녹색 8개, 신호 17개의 녹색·offset 차이 개수와 크기
  - SDMPC 목표(선택·held, repr)와 A2 − A1
  - 후보 순위: trial rows 목표 기준 상위 10개, 겹침@10, 공통 후보의 Kendall τ, 각 팔의 선택 후보가 상대 팔에서 몇 위인지
  - 벽시계 시간
- **구현 방법 (J14)**
  - RDN에는 튜닝을 덮어쓰는 인자가 없습니다(RDN:92-114).
  - 그래서 A2는 W의 곁가지 커밋을 체크아웃한 상태에서 `-Root W`로 돌립니다. 곁가지 커밋은 REF에 키 A·B를 넣고 MAN의 reference_config sha 핀을 고친 것입니다.
  - 끝나면 구현 커밋으로 돌아옵니다.
  - 재생이 바뀐 MAN을 거부하면 거부 사유를 보고하고 선택 점검을 건너뜁니다. 관문에는 영향이 없습니다.
- 이 결과로는 어떤 값이나 문턱도 바꾸지 않습니다.

## 6. 판정 조합과 중단 조건

| F10 | F11 | 제안 (결정은 사용자) |
|---|---|---|
| PASS | PASS | 둘 다 채택 |
| PASS | FAIL | F10 FW_E 채택. FW_W F10은 G-F10-W로 판정. F11은 진단과 함께 사용자에게 |
| FAIL | F11 팔로 판정해 PASS | F11 단독 채택. F10은 사용자에게 |
| FAIL | FAIL | 채택 없음. 보고 |

- EQ가 동등하지 않으면, 어느 경우든 F10 배포는 사용자 결정입니다.
- 결과를 본 뒤 추정값, 문턱, 범위, 정의를 바꾸지 않습니다. 실패한 뒤의 새 시도는 새 선언으로 합니다.
- **중단 조건**
  - §1.5 핀 불일치
  - ID-0…ID-3 중 하나라도 실패
  - P-comp 설정 확인 실패(PD0 §2.2)
  - P2B 배열 모양이 [1800, 62]가 아님
- 코드 재핀(v3c2)과 배포 manifest 교체는 이 선언의 범위 밖입니다. 재핀 묶음에서 이 키들을 함께 옮깁니다.

## 7. 실행 순서 (각 단계 한 번에 하나)
0. W git status를 저장하고 §1.5 핀을 확인합니다.
1. A0 재생 4개를 돌립니다(W@9ed2ef0, 코드 변경 전).
2. 추정: §2.3, §3.2, LOSO용 접힘 추정값을 구합니다. `OUT/estimators/*.json`의 sha를 고정합니다. 관문 계산보다 먼저 합니다.
3. 구현 커밋을 만들고(코드만, 기본은 키 없음) 단위 시험을 돌립니다.
4. ID-0, ID-3, ID-1, ID-2를 돌립니다.
5. EQ를 돌립니다.
6. F10 2a 팔, 2b(NEW 설정), FW_W P-comp 팔, LOSO를 판정합니다.
7. 곁가지 커밋으로 A2 재생 4개를 돌리고 구현 커밋으로 돌아옵니다.
8. `REPORT_F10F11.md`를 씁니다.
- 예상 비용 [추론]
  - P-comp 전체 팔: 약 20분
  - 재생 약 11–12회 × 7–13분 ≈ 2–2.5시간
  - EQ용 FZP 한 번 읽기: 수 분

## 8. 판단으로 정한 것 (반론이 가능한 것)
- **J1. 배포 입구 속도의 출처**
  - 원점 검지 MER 진입 행의 v_kmh를 씁니다.
  - 현재 프레임 스냅숏 1개나 `link_speeds_kph`(링크 전체 평균)는 쓰지 않습니다.
- **J2. 통계는 공간평균입니다.**
  - 배포: 조화평균, 개별 속도 하한 v_min = 5
  - 오프라인: Edie 풀링 평균
  - 산술 시간평균도 가능했습니다. 다만 혼잡에서는 시간평균이 공간평균보다 큽니다.
- **J3. 최소 대수 5, 모자라면 `net.v_free`로 대체합니다.**
  - 배포의 5는 차량 수이고 오프라인의 5는 차량·프레임 수라서 뜻이 다릅니다.
  - 대체값을 키가 없을 때의 값으로 둔 것도 판단입니다.
- **J4. 지평 내내 값을 유지하고(지속 예측) 절단하지 않습니다.** 자유류 입구의 관측값이 110을 넘어도 그대로 씁니다.
- **J5. FW_W에도 F10을 적용합니다(사용자 결정).**
  - STATIC §5.1은 FW_W 입구 혼잡을 F11 문제로 보고, 입구 속도 경계가 증상을 가린다고 우려했습니다.
  - 여기서는 관측 입구 속도가 원인과 무관하게 올바른 경계조건이라고 봅니다.
  - 가림 여부는 FW_W 분해 팔(F10, F11, NEW)로 드러냅니다.
- **J6. v_free 재유도의 세부**
  - 표본 단위는 5 s 프레임입니다. SP S0 절차는 150 s 창이었습니다.
  - 5시드를 합치고, 최소 자료는 150 프레임이며 30 프레임 이상인 시드가 3개 이상이어야 합니다.
  - 대체는 현행 유지입니다(과제 지시).
  - 자료가 부족할 때 셀 1 행을 쓰는 물리적 사전값은 채택하지 않았습니다. 사용자 선택지로만 남깁니다.
  - 대체되면 FW_W 셀 0의 2b 통과는 ρc만으로 이뤄져야 합니다. 행 v_free 98.16에서는 ρc ≥ 약 31이 필요합니다 [추론 C 식].
- **J7. 덮어쓰는 방식이 비대칭입니다.**
  - v_free는 배율을 곱하기 전의 행을 덮습니다(× 1.12 적용).
  - ρc는 배율을 곱한 뒤의 유효값을 덮습니다.
  - 이유: v_free는 다른 행과 같은 "측정 → 배율" 경로를 타야 하고, ρc는 추정기가 유효값을 직접 냅니다.
- **J8. F11 범위는 구조 기준으로 셀 0–6이고, 7과 11–15는 제외합니다.** 그 결과 62셀 PASS가 불가능하다는 것을 받아들이고, 2b 관문을 범위형으로 다시 적었습니다.
- **J9. ρc는 구역 하나에 1개입니다.** 셀별 7개가 아닙니다.
- **J10. E3의 세부**
  - 혼잡 가지만, 속도 잔차, 길이 가중, v_f와 a 고정, 격자 0.01
  - 식별 조건: 혼잡 창 ≥ 40, k 폭 ≥ 10, 해가 경계가 아님
  - 과제가 제안한 두 추정기를 쓰지 않았습니다.
- **J11. 과제 문턱에 더한 것**
  - 과제 문턱: 15대, 5/5, 3대, 3/5, 10%
  - "악화"에 절대 하한 0.5대를 더했습니다.
  - "범위 셀 개선"을 셀마다 3/5로 읽었습니다(엄격한 해석).
- **J12. F10이 FAIL이면 F11을 F11 팔로 판정합니다.**
  - 이 전환은 F10 결과에만 의존합니다.
  - F11 팔의 ρc는 F10(ii) 셀 0 v_free로 적합한 값을 그대로 씁니다. 작은 불일치가 있습니다.
- **J13. 선택 점검 설정.** 상태는 2250/2700/3600/4950, 컨트롤러는 wu-link, 가격 0인 첫 결정입니다. 폐루프 궤적이 아닙니다.
- **J14. 키를 켠 재생은 W의 곁가지 커밋으로 합니다.** 튜닝 덮어쓰기 인자가 없기 때문입니다.
- **J15. 900.1 s 절단점의 F10 입력에는 900 s 이전 프레임을 씁니다.** PD0 §1.5가 막은 것은 보고 통계이지 입력이 아니라고 봤습니다.
- **J16. FW_W P-comp에 FW_E 하네스의 D1–D6를 그대로 씁니다.** D4는 진출 용량을 관측 방류율로 둡니다. 그래서 엮임 병목의 일부를 가릴 수 있습니다.
- **J17. EQ 문턱(중앙값 5, p90 15 km/h)과 그 역할.** EQ는 배포 전제 조건이지 관문이 아닙니다.
- **J18. 추정 입력으로 동결 P2B 배열을 씁니다.** FZP를 다시 읽지 않습니다.
- **J19. ID-2의 기준은 W@9ed2ef0입니다.** ROBS 동결 루트와 코드가 같고 문서만 다릅니다.
- **J20. 재생은 `NUMBA_NUM_THREADS=4`로 고정합니다.** 불일치가 나면 1로 한 번 더 확인합니다.
- **J21. 키를 REF에 둡니다.** SP 새 파일로 만들지 않았습니다.
  - 배포하려면 새 REF·MAN 핀이 필요합니다. v3c2 재핀 묶음과 함께 갑니다.
  - REF에는 `segment_params` 경로(REF freeway 키)가 이미 있지만, SP 핀은 바꾸지 않습니다.

## 9. 이 선언을 바꿀 때
- 동결 뒤에 바꿔야 할 일이 생기면 `OUT/AMENDMENT_F10F11.md`에 적습니다: 바뀐 곳, 이유, 결과를 본 전인지 뒤인지, 새 sha.
- 결과를 본 뒤 바꾼 기준은 판정에 쓰지 않습니다. 원래 기준으로 낸 판정을 함께 보고합니다.
- 중단 조건(§6)에 걸리면 판정을 내지 않습니다. 원인만 보고하고, 우회 계산으로 대신하지 않습니다.
