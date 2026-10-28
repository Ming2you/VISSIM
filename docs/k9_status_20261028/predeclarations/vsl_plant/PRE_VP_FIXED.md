# PRE_VP_FIXED — 우리 plant(V-A 줄기) VSL 탐침 A·B 와 P1 편향 추적: 실행 전 고정, 검토 r2 (2026-10-27 KST)

- **이 문서가 정본입니다.** r1 = `VP/PRE_VP.md` (sha256 `4147f8595506bf2fdc8465a45eb2d94886116acef2535255654dff5e97317eac`, 바이트 그대로 `VP/PRE_VP_r1.md` 로도 둠)을 대체합니다. 고친 때는 탐침 자료(목록 상태의 plant 굴림, B·V-A 새 FZP 스캔, P1 입력)가 하나도 없을 때입니다 [실행 `GT/out` 없음 확인, LOG 17:12·17:16].
- 근거: 사용자 결정 D-K9-101~103 (`SP/K9_1_J1_NOTES_20261013.md` 337–344 줄). r1 이 인용한 sha `b33fe5e7…` 는 지금 파일의 앞 344 줄 sha 와 같습니다. 지금 파일 sha `efc3a722…` 는 D-K9-104(346 줄부터)를 덧붙인 것뿐입니다 [실행 `head -n 344 | sha256sum`].
- D-K9-104 와의 관계: 사용자는 Ω701 을 맞는 목적·보고 영역으로, FW_E 개선을 주 목표로 정했습니다. 이 문서의 J 는 **배포 plant 의 목적값**(V-A 튜닝의 Ω635 소유자 비용 합)입니다. Ω701 로 바꾸지 않고, Ω701 에 대한 말도 하지 않습니다. 대신 FW_E 소유자 비용 차를 J 와 나란히 적습니다(§3.3) [읽음 `VA_REPORT.md`:23 "Ω = 제어 영역 635링크"].
- 이 문서는 Q-V3(탐침 A·B)와 Q-V4(P1 원인 추적)만 다룹니다. Q-V5(φ 사잇값)는 하지 않습니다. Q-V6(C1 보고 VSL 줄)은 C1 쪽 일입니다.
- 고정 뒤에는 고치지 않습니다. 결함이 보이면 멈추고 보고합니다(사용자가 정함). 자료를 본 뒤의 분석은 "데이터 뒤" 라고 붙입니다. 판정 낱말은 쓰지 않습니다. 숫자·부호·띠·규칙 충족 여부만 적습니다. 시드는 망 이름을 붙여 적습니다(v3c3-s31 등). 이 문서에는 신호 녹색 지표가 없습니다(있다면 GREEN 만 셈).
- 표시: **[실행]** 돌려서 확인 · **[읽음]** 파일·코드를 읽어 확인 · **[추론]** 시험하지 않은 판단 · **[계산]** 산술.
- 경로 줄임: SP = `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8`, VP = `SP/vsl_plant`, GT = `D:/VISSIM-merge/k8_gate_trees/vsl_plant`(스크래치), FRZ_K92 = V-A 동결 트리 `D:/VISSIM-merge/frozen/sdmpc31_c20aff1d_202610230833`(읽기만, 사본 GT/code_va), RVP = 보고 사본 `D:/VISSIM_runs/20261001_v3c3/reports/k8/vsl_plant`. 코드 줄 번호는 FRZ_K92 기준입니다(EC = `evaluation/controllers`, AFA = `EC/area_freeway_accounting.py`, ADP = `EC/vissim_stackelberg_adapter.py`).

## R. 검토에서 찾은 것과 고친 것 (r1 → r2)

| # | 찾은 것 | 근거 | 고침 | 남은 것 |
|---|---|---|---|---|
| R-1 | r1 의 R3(재포장 J 비트 같음)는 구조상 참입니다. 재포장 계획의 토큰이 REC 와 같으면 `Query.evaluate` 가 물리 키 캐시로 한 번만 굴리고 둘 다 같은 결과를 돌려줍니다 | [읽음 `EC/sdmpc_tangent_surrogate.py`:202-211] [실행 smoke v4 `probe.json`: REC·REPACK·ARM110 토큰 `d178c1c1…` 같음, SCALAR 묶음 7계획에 작업자 5개] | R3 의 뜻을 "재포장 토큰 = REC 토큰" 으로 고쳐 적음(§3.4). 다른 프로세스에서의 재현은 R2(AD 대 스칼라, 다른 Query·다른 작업자)와 S-NULL(P 상태, 다른 요청 바이트)이 맡음 | 없음 |
| R-2 | P1 후보에 **셀 18 예견항의 차로 도약**이 없습니다. 예견항은 차로당 밀도 차(ρ₁₉ − ρ₁₈)를 씁니다. 셀 18 은 4차로, 셀 19 는 3차로라 같은 흐름에서도 ρ₁₉ 가 약 4/3 배입니다. φ_lane 을 0 으로 해도(C4) 이 항은 남습니다 | [읽음 `vendor/NumSim-mine/src/models/metanet.py`:113-121, AFA:193·:370·:392; ADP:9560-9567 이 셀 행의 ν 를 씀] [실행 smoke 훅 매개변수: τ 0.00333 h(12 s), ν 38.7, κ 17, 셀 18 길이 0.1754 km] [계산·추론, 단순 정상상태 어림: 흐름 5,000 veh/h·110 km/h 이면 ρ₁₈ 11.4, ρ₁₉ 15.2, 속도 결손 ν·Δρ/(L·(ρ+κ)) ≈ 38.7·3.8/(0.1754·28.4) ≈ 30 km/h 자릿수, 시험 아님] | C8(셀 18 ν = 0)과 C9(C4 + C8 함께)를 후보에 더함(§5.4). 도구 r2 에 절제 가지·도달 점검을 더하고 smoke v5 로 확인 | 없음 |
| R-3 | **출구 막힘 속도 상한**(셀 9·11·18·20)과 **출구 분율**이 후보에도, 측정에도 없습니다. 셀 18 의 출구 10481 은 이 일의 중심 자리입니다. FW_W 에서는 같은 기구(출구 저장 만차 → 단면 속도 상한)가 가짜 적체를 만들었습니다 | [읽음 AFA:346-354(막힘 → `boundary_speed_cap`), :399-401(상한 적용); `EC/lane_offramp_runtime.py`:138-146(출구 용량 = 저장 여유 × 3600), :56(10481·10491 은 SA 접근로 배수)] [읽음 기억 vissim-fww-offramp-drain-206-20261001, freeway-plant-status-20261004] | 훅이 매 걸음 반환값의 `offramp_flow_<o>`·`offramp_blocked_flow_<o>`·`speed_projection_count` 를 읽기만 해서 블록마다 쌓음(X1 막힘 차량, X2 출구 차량; §3.6·§5.3). 표 B5·P1-B 에 적음 | 출구 막힘·분율을 빼는 **절제**는 이번에 하지 않습니다. 출구 저장·포트 용량·SA 접근로를 함께 바꿔야 해서 설계가 따로 필요합니다(§5.5, 사용자 선택지) |
| R-4 | C2(ρ_c × 1.2)는 크기가 자료에서 오지 않습니다. plant 가 느린 쪽 편향이면 속도를 올리는 어떤 절제든 |e| 를 줄일 수 있어, 규칙 충족만으로는 ρ_c 를 가리킨다고 읽을 수 없습니다 | [계산 FD V = v_free·exp(−(ρ/ρ_c)^a/a): ρ = ρ_c 에서 ×1.2 는 V 를 약 17 % 올림, ρ = 10 에서는 약 1–2 % (a 1.7–2.0)] | C2 의 규칙 충족은 "충족(×1.2 민감도)" 로만 적고, 방향 근거 칸(NC3 의 최대 흐름 때 k 가 plant ρ_c 를 넘는 셀 수)을 함께 적음. C1 에도 방향 칸(plant FD 속도 − VISSIM 저밀도 속도)을 둠(§5.4) | 없음 |
| R-5 | 구역·셀 정의가 "PRE_O1O2 와 같음" 이라고만 적혀 있고 원천 sha 가 없습니다 | — | 원천을 sha 로 고정하고 대조함: 구역 = `o_analyze.py`:13 (sha `bc9ac1ef…`), CELL_B = `o2_fzp_cells.py`:17 (`cff42e34…`) = `vsl_cell_scan.py` (`fa5aeafd…`) = `o_analyze.py`:14 = `vp_common.py` CELL_B [실행 이번 검토: 32경계 모두 같음, 공통 구역 6개 셀 같음] | 없음 |
| R-6 | 실행된 블록의 VSL 근거가 행동 CSV 하나뿐이었고, EXEC 에 쓰는 T+150·T+300 결정의 적용 표지를 점검하지 않았습니다 | — | [실행] VISSIM 되읽기 `vsl_readback.csv` 와 대조: 21상태 × 3블록 = 63블록 모두 켬/끔이 같고, 되읽은 분포 번호 = 요청 값, ok = 1. [실행] 21상태의 T·T+150·T+300 결정 모두 `.applied` 있음(§2) | 없음 |
| R-7 | H1(FZP 스캔 9개) 어림 30–60 분은 과대입니다 | [읽음 `SP/vsl_v3c3/logs` 셀 스캔 29–35 s, `o1o2/logs` 프레임 스캔 22–25 s] | §8 을 약 5–10 분(+ 잠금 대기)으로 고침. C8·C9 로 H3 상태당 절제가 10굴림이 되어 시간을 고침 | 없음 |
| R-8 | `vp_probe.py` 설명 글이 R1 비용을 "bit-equal" 로, follower 행을 "21 parent segments" 로 잘못 적었습니다(코드는 1e-9, 31행) | [읽음 r1 `vp_probe_r1.py`:29-30, :368-369; LOG 16:53] | r2 에서 글을 고침(동작 같음) | 없음 |
| R-9 | (확인, 결함 아님) 팔은 정책 토큰 길을 바꾸지 않습니다. 모든 굴림이 기록 상태에서 `load_prices` 를 통과한 같은 요청 틀의 `Query` 로 갑니다. 기록 선택 계획의 비트 재현(R1)이 있습니다. 모든 굴림이 배포와 같은 작업자 경로입니다. ARM 의 VSL 키 처리(구역 키 = v, 길 키 = 구간 키 최솟값)는 AD 작업자가 하는 것과 같습니다. 상태 시드는 provenance 에서 읽습니다. 잠금은 일마다 배타 생성, 자기 것만 지움, 해제 뒤 20 s 쉼입니다 | [읽음 `vp_probe.py`(r2):147-176·:222-232, `EC/sdmpc_tangent_worker.py`:380-391·:303, `vp_states.py`, `vp_common.py` lock_acquire/lock_release] [실행 smoke v4·v5 R1 비트 같음, 자체 시험 잠금 쉼 시험] | — | — |
| R-10 | (참고) `vp_probe.py` 의 `probe.json.tmp` 는 PID 를 붙이지 않습니다 | [읽음 `vp_probe.py` write(): 일 폴더마다 쓰는 프로세스 하나, 주 스레드에서만 부름] | 고치지 않음(충돌 길 없음) | 없음 |

## 0. 줄임말 (처음 한 번)

- VSL = 가변 제한속도. DSD = VISSIM 희망속도 결정점(표지). plant = SDMPC(순차 분해 모형예측제어기) 안의 교통 예측 모형. V-A = 우리 줄기 폐루프 VISSIM 런 3개(`D:/VISSIM_runs/20261023_sdmpc31_k92`). NC3 = 같은 시드 무제어 런. VSL 단독 = DSD 63–66 에 91 을 고정한 native 런(`D:/VISSIM_runs/20261027_vsl_v3c3`). B = codex 제어기를 v3c3 로 옮긴 폐루프(VSL 110 고정, `D:/VISSIM_runs/20261026_codex_b_v3c3`). FZP = VISSIM 차량 궤적 기록(5 s 프레임). SA = 정지선 접근로(stop-line approach) 모형(K8).
- J = plant 의 모형 목적값 `objective_veh_h`(배포 목적, Ω635 소유자 합; 450 s = 150 s 블록 3개, veh·h). ΔJ = 두 팔의 J 차.
- 팔 = 같은 결정 상태에서 바꿔 굴리는 계획 하나. REC = 기록된 선택 계획. EXEC = VISSIM 이 그 450 s 동안 실제로 돌린 블록들. ARM v = REC 에서 VSL 구역 머리 10 만 v 로 바꾼 계획.
- AD 경로 = 미분을 함께 내는 작업자 굴림(기록된 선택 계획의 J 가 이 길에서 나왔음). 스칼라 경로 = 값만 내는 작업자 굴림. 작업자 = 결정이 plant 를 굴릴 때 띄우는 별도 python 프로세스(`EC/sdmpc_tangent_worker.py`). 둘 다 배포 결정과 같은 작업자 경로입니다(§1.2).
- 셀 = FW_E 본선 31셀(체인 0–10,784 m, 경계 = CELL_B). 구역(PRE_O1O2 와 같은 이름·범위, 원천 sha §R-5): U 0–7 · B1 8–13 · M1 14–15 · VSa 16–18 · VSb 19–25 · D 26–30. 셀 맞춤 구역: Mu′ 16–17 (6,315–6,666 m) · VS0′ 18 (6,666–6,842 m, 차로 감소 바로 앞 셀) · B2′ 19–24 (6,842–7,827 m). 프라임(′)은 VSL_REPORT 의 체인 구역(Mu 6,300–6,700 · VS0 6,700–6,800 · B2 6,800–8,100 m)을 셀 경계로 맞춘 근사입니다.
- φ_lane = 차로 감소항 계수(`freeway_lane_drop_phi`). φ_cd = 용량 감소 방류 계수(`capacity_drop_discharge_phi`). ν_cong 전환 = 혼잡 때 예견항 계수를 바꾸는 용량 감소 표현(`capacity_drop_anticipation`). ν = 예견항 계수(셀 행 `metanet_nu_km2_h`). τ = 이완 시간. κ = 예견항 분모 상수. δ = 합류 감속항 계수(`metanet_delta_merge`). ρ_c = 셀 임계 밀도. v_free = 셀 자유 속도. a = FD(기본도) 모양 지수. Carlson 법칙 = plant 의 VSL 준수 법칙(m_v = 측정 속도 척도). 코호트 = 표지를 지난 차가 지닌 명령 값 꼬리표(`VSLExposure`).
- X1 = plant 굴림의 출구 막힘 차량(출구가 받지 못한 흐름의 적분, veh). X2 = plant 굴림의 출구 차량(veh). 둘 다 훅이 읽기만 해서 셈(§3.6).
- R = 줄임 비율(§5.4). 띠 A·B·C = R 중앙값 구간(§5.4). S-* = 멈춤 규칙(§7).

## 1. 대상 plant 와 경로 (데이터 전 사실)

### 1.1 우리 plant 의 FW_E

- [실행 smoke 훅 스냅샷] V-A plant 의 FW_E 는 차로군 plant 가 없습니다. `LaneFreewayRuntime.advance` 가 길마다 `self.lanes.get(road)` 를 보고(EC/lane_freeway_runtime.py:107), 없으면 31셀 집계 METANET `_freeway_substep_events` 를 1 s 마다 부릅니다(같은 파일 :123; EC/lane_coupling.py:97). plant 구성 `plant_n31_v2.json:59` 도 `"lane_groups": false` 입니다 [읽음].
- [실행 smoke 스냅샷] 셀은 31개이고 경계가 CELL_B 와 같습니다(셀 12 길이 0.18424 km). 차로는 셀 0–18 이 4, 셀 19–30 이 3 입니다. 그래서 차로 감소항은 셀 18(VS0′)에만 걸립니다(ADP:9501-9545 무장, :9597-9602 항).
- [읽음 metanet.py:113-121, AFA:193·:370·:392] 예견항은 차로당 밀도 `rho_for_flow` 의 하류 차(ρ_{i+1} − ρ_i)를 씁니다. 셀 18 의 하류는 3차로 셀 19 라서, 같은 흐름에서도 이 차가 커집니다(§R-2). 셀 행의 ν 는 ADP:9560-9567 이 읽습니다.
- [읽음] VSL 명령 공간은 부모 21구간 키(`FW_E__seg0…seg20`)이고, 구역 머리는 FW_E [0, 5, 10, 15], 자유 구역은 0·1·2 입니다(`diagnostics/sdmpc_n31_20260924/config_n31_v2.json`:8058-8077). 31셀은 자기 구역 머리 키의 값을 받습니다(ADP `_zoned_segment_vsl`, :9126-9134).
- [읽음] V-A 가 110 밖을 쓴 결정은 모두 구역 머리 10(`FW_E__seg10…14`)의 100 이고, VISSIM 에는 분포 101 로 써졌습니다(`SP/k92/va/analysis/VA_REPORT.md`(b57022e6…):573; `plant_n31_v2.json` qualification "commands 80/90/100/110 are written as the distributions 81/91/101/110").
- [읽음] 한 걸음의 항(AFA): 목표 속도 V = 셀별 v_free·exp(−(ρ/ρ_c)^a / a)(셀 값은 ADP:9548) → 명령 < 109.5 일 때만 Carlson 법칙(AFA:382-384, EC/freeway_fd.py:115-152) → 코호트 혼합(AFA:385-387) → 이완·대류·예견 갱신(AFA:392, metanet.py:99-122; ν 는 ADP:9560-9567 의 셀 행 값, ν_cong 전환은 꺼짐) → 차로 감소항(ADP:9597-9602) → 합류 감속항 δ(AFA:162, :393-396) → 출구 막힘·끝 경계 속도 상한(AFA:346-362, :399-401) → 흐름 q = ρ·v·차로, φ_cd 방류 상한(AFA:133, :213-216). 출구 용량은 출구 저장 여유 × 3600 입니다(EC/lane_offramp_runtime.py:138-146). 상태 의존 τ·ν(`state_response`)는 설치 때 거부되어 쓰이지 않습니다 [읽음 `plant_n31_v2.json` qualification "state_response … refused at install (K6)"].
- [실행 smoke v2·v5 훅 스냅샷, 작업자가 본 FW_E 구성 값] φ_lane 3.0, δ 1.0(튜닝 `config_overrides.network.metanet_delta_merge` 는 0.3 이지만 FW_E 걸음은 구성 사본의 1.0 을 읽음, 방향별 값 없음), φ_cd 1.0, ν_cong 전환 꺼짐, α_vsl 0, 링크 ρ_c 37.8, τ 0.00333 h, κ 17, ν 38.7(셀 8–25 모두), 셀 행 키 v_free·rho_crit·metanet_a_m·metanet_tau_h·metanet_nu_km2_h·metanet_kappa_veh_km_lane·segment_length_km. 준수 법칙 Carlson A 1.33 · E 0.87 · m_v(80/90/100) 0.7225/0.8120/0.9007. 코호트 표지 셀 [0, 3, 5, 8, 14, 18, 26, 28]. 구역 머리 10 이 다스리는 셀 = 14–24. FW_E 출구 셀: 10643 → 9, 10682 → 11, 10481 → 18, 10483 → 20. FW_E 합류 램프: RM_C10639·10681·10490·10484. Hadi 수용 모형 없음.

### 1.2 배포 결정의 plant 경로

- [읽음] V-A 정책은 `surrogate_reuse` 가 켜져 있어 결정의 모든 plant 굴림이 `sdmpc_tangent_surrogate.Query` 를 거칩니다(EC/sdmpc.py:587-593). `Query.evaluate`(EC/sdmpc_tangent_surrogate.py:202-256)는 계획을 물리 키로 묶어(:209) 키마다 작업자 하나를 띄웁니다(`sdmpc_tangent._evaluate_single`, EC/sdmpc_tangent.py:48-71). 그래서 한 `evaluate` 묶음 안에서 물리적으로 같은 계획은 한 번만 굴러갑니다.
- [읽음] 기록된 선택 계획의 J(`metadata.joint_leader_selection.selected_objective`)는 AD 굴림에서 나왔습니다.
- [읽음 EC/sdmpc_tangent_worker.py:380-391] AD 작업자는 VSL 축 값을 그 구역 머리의 모든 구간 키에 넣고, 길 키를 구간 키 최솟값으로 둡니다. ARM 은 같은 꼴로 만듭니다(§3.2). 스칼라 작업자는 계획을 그대로 굴립니다(:303).

### 1.3 배관 시험 (목록 밖 상태 v3c3-s31 T=2,400, 결과로 쓰지 않음) [실행]

- smoke v1–v4 (16:16–16:51, r1 도구): r1 §1.3 그대로입니다. 요지: R1 목적값 비트 같음, 비용 최대 차 1.42e-14, R2 − R1 = 0.0, R3·null 비트 같음, 훅 14개 모두 450 걸음·오류 0, 기준(EXEC)과 다른 절제 C1·C2·C3·C4·C7, 블록 값까지 같은 절제 C5·C6. v4 벽시계 403 s.
- smoke v5 (r2 도구, §9 의 최종 바이트): 결과는 §1.4 에 적습니다.
- 배관 시험에서 화면에 나온 팔별·절제별 J 차는 smoke 상태의 값이라 결과로 쓰지 않고, 규칙·문턱을 정하는 데 쓰지 않았습니다. 검토자(r2)는 smoke 의 J 값을 보지 않았고, 참/거짓·토큰·도달 기록만 봤습니다.

### 1.4 smoke v5 (검토 r2 도구 확인)

- [실행] smoke v5 (17:15:33–17:25:42 KST, 공유 잠금 아래 — 다른 워크플로 잠금이 풀린 뒤 6 s 기다림, WMI 분리 PID 46848, BELOW_NORMAL, 목록 밖 v3c3-s31 T=2,400, 명세 `smoke/specs/spec_smoke_v5.json` = v2 명세 + C8·C9): 종료 0, 벽시계 609 s(준비 60 s, AD 148 s, 스칼라 묶음 100 s(작업자 5), 절제 10굴림 세 차례 약 283 s; 다른 워크플로가 함께 돌아 v4 의 403 s 보다 느림).
- [실행] R1 목적값 비트 같음, 비용 최대 차 ≤ 1e-13, R2 − R1 = 0.0. REPACK 토큰 = REC 토큰(그래서 R3 는 캐시 적중, §3.4). null 비트 같음이고 null 요청 sha ≠ EXEC_scalar 요청 sha(따로 굴린 재현). C5 요청 sha = null 요청 sha(구조상 0).
- [실행] 훅 파일 16개, 모든 평가 레이블에서 걸음 450·블록 150·셀 31·오류 0, 출구 기록(X1·X2) 모두 있음(`exit_missing` 0건), 셀 경계 차 0.000 m.
- [실행] 도달 점검 C1–C9 모두 참(C8 `cells {"18": {"old": 38.7, "new": 0.0}}`, C9 φ 3.0 → 0 + 같은 ν). 기준(EXEC)과 블록 값이 다른 절제 = C1·C2·C3·C4·C7·C8·C9, 같은 절제 = C5·C6(값은 보지 않고 같음·다름만 봄).
- [실행] `vp_jobcheck.py` 걸림 0(`smoke/jobcheck_v5.json` 75afe816…), `vp_smokecheck.py`(`smoke/smokecheck_v5.json` 097f3aa8…), `vp_tablesmoke.py` 멈춤 0(`smoke/tablesmoke_v5.json` 2656e36b…). 기록 `probe.json` d30ecbe6…, `job_summary.json` 4797c06b….
- 검토자는 smoke v5 의 J·편향·X1·X2 값을 보지 않았습니다. 이 문서의 규칙·문턱은 smoke 값으로 정하지 않았습니다.

## 2. 상태 (고정 목록, r1 그대로)

- 규칙과 목록 파일: `VP/decl/VP_STATES.json`(도구 `vp_states.py`, sha 는 §9). 시드는 run provenance 의 `seed` 입니다(폴더 이름 아님). 결정 기록 폴더는 읽기만 합니다.
- 탐침 A·B 상태(12): 시드마다 T_low = 행동 CSV 의 FW_E VSL 행에 110 미만이 있는 결정 시각. A1 = min(T_low) − 150 (110 결정), A2 = min(T_low) (101), A3 = T_low 의 아래 중앙값 (101), A4 = max(T_low) + 150 (110). 결정·블록의 "101" 은 VISSIM 에 쓴 값이고, 그 결정의 plant 명령은 100 입니다(§1.1).

| 시드 | A1 (110) | A2 (101) | A3 (101) | A4 (110) | T_low 수 |
|---|---:|---:|---:|---:|---:|
| v3c3-s31 | 3,300 | 3,450 | 4,050 | 4,800 | 9 |
| v3c3-s41 | 2,400 | 2,550 | 3,300 | 4,200 | 10 |
| v3c3-s43 | 2,700 | 2,850 | 3,750 | 5,100 | 14 |

- P1 상태(9, VSL 끔): 시드마다 T0 ∈ {1,800, 5,400, 7,200}. 결정 T, T+150, T+300 의 FW_E 행이 모두 110 이어야 합니다(아니면 T+150, +300, +450 순서로 대신). [실행] 9개 모두 T0 그대로 조건을 채웠습니다.
- 실행된 블록의 VSL(탐침 B 묶음용, 행동 CSV): s31 A1 = 110·101·101, A2 = 101·101·101, A3 = 101·101·101, A4 = 110·110·110; s41 A1 = 110·101·110, A2 = 101·110·101, A3 = 101·101·101, A4 = 110·110·110; s43 A1 = 110·101·101, A2 = 101·101·101, A3 = 101·101·101, A4 = 110·110·110 [실행 VP_STATES.json `written_fwe_T/T150/T300`]. 켬 22블록, 끔 14블록 [계산].
- [실행, 검토 r2] VISSIM 되읽기 대조: 각 런 `vsl_readback.csv` 에서 결정 시각 T, T+150, T+300 의 줄을 읽어, "요청 < 110 이고 되읽은 분포 < 110 이고 ok = 1" 이 있는지를 행동 CSV 의 켬/끔과 비교했습니다. 21상태(A 12 + P1 9) × 3블록 = 63블록 모두 같았고, 모든 줄이 ok = 1·요청 = 되읽음이었습니다.
- [실행, 검토 r2] 21상태의 결정 T, T+150, T+300 모두 `action_<T>.json.applied` 가 있습니다(EXEC 에 쓰는 결정이 VISSIM 에 적용된 결정임).
- 배관 시험 상태 v3c3-s31 T=2,400 은 어느 목록에도 없습니다(도구가 확인). V-A 제어 시작은 900 s 라 P1 의 T=1,800 도 SDMPC 결정입니다 [실행 `launch_plan.json` control_start_sec 900, 9개 P1 결정 모두 `joint_leader_selection.selected_objective` 있음].

## 3. 탐침 A — plant ΔJ (Q-V3)

### 3.1 무엇을 묻나

- 우리 plant 가 V-A 결정 상태에서 VSL 110·101·100·90 을 어떻게 값매기는가. V-A 가 VSL 을 쓴 상태(plant 100 → VISSIM 101; A2·A3)와 그 앞뒤 110 상태(A1·A4)에서 봅니다.

### 3.2 계획과 팔을 거는 방법

- 도구 `vp_probe.py`(sha §9)가 어댑터를 VBS 명령줄처럼 `__main__` 으로 돌리고, `sdmpc.solve` 하나만 탐침 함수로 바꿉니다. 탐침 함수는 `sdmpc.solve` 의 앞부분(EC/sdmpc.py:538-593)을 그대로 되풀이합니다: 직전 명령 영수증·가격 점검(`load_prices`, 정책 토큰이 기록과 같아야 통과), held 기준, 런타임 콜백, 결정 공유 질의, 3블록 좌표, `prepare_request(…)`. 그 뒤 모든 굴림은 같은 요청 틀로 만든 `Query` 의 `evaluate` 로 합니다(작업자 경로). 정책 토큰은 바뀌지 않습니다. 행동 파일은 쓰지 않습니다.
- 재생 묶음: `SP/j1/fix/gates/gprep.py`(sha `0482a538…`)가 결정 상태를 복사만 해서 만듭니다. 코드 뿌리는 FRZ_K92 의 바이트 사본 GT/code_va(FREEZE.json 10,569 파일 sha 대조 끝, 실행 전 §8 H0 에서 다시 대조). 환경은 `k92_replay.py` 꼴: provenance 의 RW_*, PYTHONPATH = 훅 폴더;deps\sdmpc;deps\sdmpc-numba, BLAS 스레드 1, PYTHONHASHSEED 0, NUMBA_NUM_THREADS 지움(D-K9-99), cwd = 코드 뿌리, python -B. 튜닝은 V-A 튜닝 그대로(sha `c8e3ee2c…`, 정책 토큰 `428e650d…`).
- REC = held(action_T) 를 블록 0 으로, action_T 에 기록된 미래 두 블록(`diagnostics.sdmpc_prediction_sequence`)을 블록 1·2 로 `sequence.pack`. held(x) = `control_from_json` → `physical_ramp_branches.held_actual_reference` → `expand_shared_vsl_action`(어댑터가 쓴 segment_vsl 함수) → `sequence.first_action` → `area_meter_finalization.prepare_held_actual_reference`. 다음 결정이 직전 명령을 읽는 길과 같습니다(ADP:13158-13180, EC/sdmpc.py:556-568).
- ARM v (v ∈ {110, 101, 100, 90}) = REC 의 세 블록 모두에서 구역 머리 10 의 키 `FW_E__seg10…seg14` 를 v 로, 길 키 `FW_E` 를 FW_E 구간 키의 최솟값으로 바꾼 계획(AD 작업자의 VSL 키 처리와 같은 꼴, §1.2). 다른 구역(머리 0·5·15), FW_W, 미터, 신호, 오프셋, N_P*·N_UF* 는 REC 그대로입니다. plant 안에서는 셀 14–24 가 이 값을 받습니다(표지 셀 14·18 에서 코호트 꼬리표가 바뀜).
- 101 팔의 뜻 [읽음 EC/freeway_fd.py:90-103, :147]: plant 명령 100 이 VISSIM 분포 101 로 써지는 값이고, plant 안의 101 은 같은 3차 m_v 곡선을 101 에서 읽은 명령입니다. 그래서 101 팔은 "VISSIM 101" 이 아니라 100 옆의 plant 기울기를 보는 점입니다. 100 팔이 V-A 가 실제로 쓴 plant 명령입니다.
- 굴림: REC 는 AD 경로 한 번(R1), REC·REPACK·ARM 넷·EXEC 는 스칼라 경로 한 `evaluate` 묶음. 물리적으로 같은 계획(보통 REPACK = REC, REC 머리 10 이 세 블록 모두 v 인 상태의 ARM v = REC)은 캐시로 한 번만 굴러갑니다(§1.2).

### 3.3 지표

- J(450 s, veh·h)와 ΔJ_v = J(ARM v) − J(ARM 110). 부호: |ΔJ| < 0.01 이면 0. ΔJ(101 − 100)도 적습니다. J(ARM v) − J(REC 스칼라)도 적습니다.
- 소유자별 비용 차(`sdmpc_omega_partition.costs`): FW_E 와 나머지 합(D-K9-104 에 맞춰 FW_E 줄을 J 와 나란히 둠).
- 훅(§3.6)에서: FW_E 입구 대기 veh·h, 구역별 속도·재고 차(블록 0·1·2, w300 = 블록 0–1, w450 = 블록 0–2), 셀 8–25 속도 차(w450), 구역 veh·h 차, 팔별 X1·X2(JSON).

### 3.4 점검 (어긋나면 멈춤)

- R1: REC 의 AD 경로 J 가 기록 `selected_objective` 와 비트까지 같고, 소유자별 비용 20개가 기록 `omega_partition.costs` 와 키가 같고 차가 모두 1e-9 veh·h 이하. 아니면 S-R1. (1e-9 는 smoke v1 의 비용 차 1.4e-14 를 보고 데이터 전에 정함.)
- R2: REC 스칼라 J − AD J 를 적습니다(배관 시험 0.0). 서로 다른 Query·작업자 프로세스의 재현 점검입니다. 0 이 아니면 모든 ΔJ 를 "스칼라 경로" 로 표시하고 그 차를 함께 적습니다(멈추지 않음; ΔJ 는 모두 스칼라 경로끼리라 비교는 같은 길).
- R3 (r2 에서 뜻 고침): 재포장(REPACK = `sequence.pack(sequence.actions(REC, 3))`)의 토큰이 REC 토큰과 같으면 재포장이 계획을 바꾸지 않은 것입니다. 이때 두 J·비용이 같은 것은 같은 캐시 항목이라서입니다. 토큰이 다르면 따로 굴러가고, 그때는 J·비용 비트 같음이 실제 재현 점검입니다. 어느 쪽이든 도구가 J·비용 비트 같음을 보고, 아니면 S-R3. 보고에는 상태마다 "REPACK 토큰 = REC 토큰" 여부를 함께 적습니다(`probe.json` 의 `plans.REPACK.token` 대 `plans.REC.token`, 표 도구 밖의 한 줄 대조).
- R0: REC 토큰이 기록 `plan_action_token` 과 같은지 적습니다(보고만; 배관 시험에서 다름, 진단 키 구성 차이).
- 훅: 스칼라 굴림마다 걸음 450, t = T … T+449, 블록마다 150 걸음, 셀 31, 훅 오류 0. 아니면 S-HOOK. 셀 경계: 훅이 본 셀 길이 누적이 CELL_B 와 1 m 안. 아니면 S-MAP. 출구 기록(X1·X2)이 없거나 빠진 키가 있으면 그 칸만 "못 냄" 이고 멈추지 않습니다.

### 3.5 표 (`vp_analyze.py tables`)

- A1: 상태별 R1·R3, ΔJ 101·100·90, ΔJ(101−100), 100 팔의 FW_E 비용 차·다른 소유자 차·입구 대기 차.
- A2: 결정 묶음(101 상태 = A2·A3, 110 상태 = A1·A4)별 ΔJ 부호 수와 범위.
- A3: 상태 × 팔(101·100·90)의 구역 속도 차(w450).
- JSON 에 블록별 값, 셀 8–25 속도 차, 구역 veh·h 차, 팔별 X1·X2 를 모두 둡니다.

### 3.6 훅 (작업자 안, 수동)

- `vp_hooks/sitecustomize.py`(sha §9). PYTHONPATH 로만 실리고 `VP_HOOK_DIR` 이 있을 때만 켜집니다. `sys.monitoring` 으로 `LaneFreewayRuntime.advance` 하나의 시작·끝만 보고, 지역 변수 `self`·`state` 와 구성의 속성, 그리고 (r2) 그 호출의 **반환값**을 읽기만 합니다(모형 메서드 호출 0, 쓰기 0). finder 순서 장치는 K8 SA 훅과 같습니다.
- 걸음마다 셀 재고 = 밀도 × 셀 길이 × 차로, 속도, 흐름, 입구 대기를 150 s 블록으로 쌓습니다. 첫 걸음 시작에 작업자가 본 FW_E 매개변수와 시작 상태를 적습니다(§5.3 도달 점검).
- (r2) 걸음마다 반환값 `(ttt, off_flows, diagnostics)[2]['FW_E']` 의 `offramp_flow_<o>`·`offramp_blocked_flow_<o>`(o = 10643·10682·10481·10483, veh/h)와 `speed_projection_count` 를 블록으로 쌓습니다(AFA:508-519 가 만드는 값). 키가 없거나 읽다 예외가 나면 `exit_missing` 에 적고 합에 넣지 않습니다. 이것은 훅 오류로 치지 않습니다.
- 훅이 계산을 바꾸지 않는다는 근거: 훅이 켜진 채로 R1 이 비트 같아야 합니다(smoke v1–v5 에서 같았음).

## 4. 탐침 B — plant 충실도 (Q-V3)

### 4.1 상태와 계획

- 탐침 A 와 같은 12상태. plant 쪽 주 계획 = EXEC = pack([held(action_T), held(action_{T+150}), held(action_{T+300})]) — VISSIM 이 [T, T+450) 에 실제로 돌린 블록 0 셋입니다(적용 표지 확인, §2). 보조 = REC. 스칼라 작업자 경로.
- 묶음은 블록 단위입니다: 블록 b 의 VSL = 결정 T+150b 의 FW_E 행. 켬 = 101, 끔 = 110.

### 4.2 VISSIM 쪽

- V-A FZP 3개를 `o2_fzp_cells.py`(sha `cff42e34…`, PRE_O1O2 도구 그대로)로 5 s 프레임 × 31셀 N·SV 로 셈. 창 [1,700, 7,700] s. 출력 `GT/out/fzp_frames/VA_v3c3-s<S>.json`.
- 블록 b = 프레임 T+150b ≤ t < T+150(b+1) (보통 30개). 150 s 당 프레임이 25개 미만이면 그 칸은 "못 냄".

### 4.3 지표와 편향

- 셀: 재고 = N/프레임 수(veh), 속도 = SV/N(km/h, Edie 공간평균), 흐름 = SV/(L·프레임 수)(veh/h, 모든 차로). plant 는 재고 = 걸음 평균, 속도 = 재고 가중 평균, 흐름 = 걸음 평균.
- 구역: 재고 = 합, 속도 = 재고 가중(plant)·SV/N(VISSIM), 흐름 = 길이 가중 평균.
- 편향 e = plant − VISSIM. 창: b0, b1, b2, w300, w450. 구역 9개(U·B1·M1·VSa·Mu′·VS0′·VSb·B2′·D), 셀 8–25.
- 시작 편향: plant 첫 걸음 전 상태 대 FZP 프레임 T−4.9·T+0.1 (셀·구역 재고·속도).
- 요약(B3): 36블록(12상태 × 3)을 블록의 실행 VSL(켬 22·끔 14)로 나눠 구역·양마다 n, 평균 e, 평균 |e|, 켬 − 끔. 한 상태의 블록끼리는 독립이 아니라서 n 은 블록 수일 뿐입니다. 검정은 하지 않습니다.
- (r2) B5: EXEC 굴림의 출구별 X1(막힘 veh)·X2(출구 veh), w450. VISSIM 출구 차량은 기존 스캔이 본선 사슬만 세어서 못 잽니다. 그래서 X2 는 plant 쪽 숫자만 적고 편향은 내지 않습니다.

### 4.4 표

- B1 구역 속도 편향(b0/b1/b2/w450), B2 재고·흐름 편향(w450), B3 블록 묶음 요약, B4 셀 8–25 속도 편향(w450), B5 출구 X1·X2(w450). JSON 에 REC 계획 편향, VISSIM 셀 속도(창별), 시작 편향을 둡니다.

### 4.5 읽는 법 단서 (데이터 전 고정)

- plant 의 수요는 결정 T 의 예보이고 VISSIM 은 실제 도착입니다. 이 차도 편향에 들어갑니다(P1 의 "목록 밖 항", §5.5).
- 시드마다 V-A 런 하나라서 흔들림은 모릅니다.
- 탐침 B 의 켬 − 끔 은 VSL 몫이 아닙니다. 켬 블록과 끔 블록은 시각·교통 상태가 다릅니다.

## 5. P1 — VSL 과 무관한 편향 추적 (Q-V4)

### 5.1 무엇을 찾나

- codex 판 plant 에서 VSL 끔 상태에도 VSa·VSb·M1 이 VISSIM 보다 느렸습니다(VSL_RESULTS r2 §1.6, sha `9bbf83a3…`). 여기서는 **우리 plant** 에서 같은 자리(셀 18 = VS0′, M1, VSb 재고)를 VSL 끔 상태로 재고, 어떤 항이 그 편향을 만드는지 항을 하나씩(그리고 차로 감소 두 항은 함께도) 빼서 봅니다.

### 5.2 FZP 쪽 (VISSIM 이 보인 것)

- 원천 12개 = NC3 · VSL 단독 · V-A · B × v3c3-s31·s41·s43 (`VP/decl/VP_FZP_SOURCES.json`, 선언 폴더만 열고 디렉터리 훑기 없음; 시드는 run.json·run_provenance 의 `seed`). 스캐너 `vsl_cell_scan.py`(sha `fa5aeafd…`): 31셀 × 60 s 창 × 차로 1–4 의 N·SV. NC3·VSL 출력은 기존 것을 sha 로 재사용, B·V-A 6개는 새로 셈(`GT/out/fzp_cell/`).
- 창 조건: 900 ≤ t0, t0 + 60 ≤ 9,000, 프레임 12. 저밀도 = k = (N/12)/(L·차로) ≤ 12 veh/km/차로.
- P1-F 지표(셀 8–25, 원천마다): 저밀도 창의 속도 중앙·k 중앙·창 수, 차로당 최대 60 s 흐름과 그때 k, 속도 < 60 km/h 창 비율, 저밀도 차로별 속도 중앙, 셀 18 에서 (셀 18 속도 − 셀 16–17 속도)의 저밀도 중앙. V-A 는 VSL 이 걸린 기간([min T_low, max T_low + 600) s)을 뺀 판도 적습니다.

### 5.3 plant 쪽

- P1 9상태에서 EXEC(세 블록 모두 110)를 스칼라 작업자 경로로 굴려 V-A FZP 와 대조합니다(정의는 §4.3). 이 상태들에서도 R1·R3 를 같은 규칙으로 점검합니다.
- 기준 편향 지표: m1 VSa 속도, m2 M1 속도, m3 VSb 재고, m4 VSb 속도, m5 VS0′(셀 18) 속도. 창 w450(C7 만 b0).
- (r2) X1·X2: 기준 굴림과 각 절제 굴림의 출구별 막힘·출구 차량(w450). 표 P1-B 에 10481(셀 18)·10483(셀 20) X1 을 적고, "기준 굴림에서 X1 ≥ 1 veh 인 상태 수 / 낸 상태 수" 를 출구마다 적습니다.
- 절제 = 요청 틀을 unpickle 한 사본(`t['owned']` 의 state·follower)에서 구성 값만 바꾸고, 그 사본으로 만든 `Query` 로 EXEC 를 굴림. 코드 객체는 바꾸지 않습니다. 바꾸는 곳은 FW_E 구성 사본 `state.lane_freeway_runtime.configs['FW_E'].network`(plant 걸음이 실제로 쓰는 구성)입니다. follower 구성의 셀 행은 행 수가 같을 때만 같이 맞춥니다(V-A 는 31행이라 같이 맞춤 [실행 smoke v4·v5 `follower_rows_patched` 참]).
- null 절제(아무것도 안 바꾼 사본)의 J·비용이 EXEC 와 비트 같아야 합니다(아니면 S-NULL). null 은 따로 Query·작업자로 굴러가고 요청 바이트도 EXEC 와 다릅니다 [실행 smoke v4: 요청 sha `a426e887…` 대 `00349319…`].
- 도달 점검: 각 절제 굴림의 훅 스냅샷(작업자가 본 값)이 바꾼 값과 같아야 합니다(아니면 S-REACH). C8·C9 는 셀 18 행의 ν = 0, ν_cong 전환 꺼짐, (C9) φ_lane = 0 을 봅니다.

### 5.4 후보 원인 목록 (고정, 9개)과 시험

| # | 후보(plant 항) | 코드 자리 | 절제(바꾸는 값) | 그 항을 가리키는 결과 |
|---|---|---|---|---|
| C1 | 셀 자유 속도 v_free | ADP:9548-9558 (행 `v_free`) | 셀 8–25 의 v_free 를 VISSIM 저밀도 점에 맞춘 값으로: v_free′ = s_med / exp(−(k_med/ρ_c)^a / a), (k_med, s_med) = NC3 세 시드를 모은 저밀도 창의 중앙(창 20개 미만인 셀은 바꾸지 않음), ρ_c·a 는 그 셀 plant 값 | 가리킴 규칙 충족. 방향 칸: 구역 셀들의 (plant FD 속도(같은 k) − VISSIM 저밀도 속도) 평균 |
| C2 | FD 혼잡 갈래(ρ_c) | ADP:9548-9558 (행 `rho_crit`) | 셀 8–25 의 ρ_c × 1.2 (φ_cd 문턱인 링크 스칼라 ρ_c 는 그대로) | 크기가 자료에서 오지 않은 민감도 시험입니다. 규칙 충족이면 "충족(×1.2 민감도)" 로만 적습니다. 방향 칸: 구역 셀 가운데 NC3 세 시드의 "차로당 최대 60 s 흐름 때 k" 중앙이 plant ρ_c 를 넘는 셀 수 / 셀 수(절반 넘으면 "근거 있음") |
| C3 | 합류 감속 δ | AFA :162, :393-396 | FW_E δ = 0 (구성 스칼라와 방향별 값) | 가리킴 규칙 충족 |
| C4 | 차로 감소항 φ_lane (셀 18) | ADP:9597-9602 | FW_E φ_lane = 0 | 가리킴 규칙 충족. 함께 P1-F 의 셀 18 − 셀 16–17 저밀도 속도 차를 적음 |
| C5 | 용량 감소(φ_cd 방류 상한 + ν_cong 전환) | AFA :133, :213-216; metanet.py:125-137 | φ_cd = 1.0, ν_cong 전환 끔 | V-A 는 두 값이 이미 꺼져 있어 요청 바이트가 null 과 같습니다 = "구조상 0" 으로 적음(표가 모든 상태 비트 같음이면 "· 구조상 0" 을 붙임) |
| C6 | 준수 법칙(Carlson + m_v)과 코호트 | AFA :200-209, :382-387; freeway_fd.py:115-152, :283- | FW_E 의 `freeway_vsl_fd_response`·`component_vsl_transport`·`component_vsl_initial_commands`·코호트 상태를 뺌 | VSL 끔 상태(명령 모두 110, 코호트는 마지막 적용 명령에서 시작하는데 P1 9상태의 결정 T−150 은 모두 110 [실행 VP_STATES.json T_low 에 T−150 없음])에서는 비트 같음이 예상 = "구조상 0" |
| C7 | 초기 상태 투영 | 관측 → plant 시작 상태 | 셀 8–25 의 시작 속도를 V-A FZP 프레임 T−4.9·T+0.1 의 셀 Edie 속도로(차가 없으면 그대로; 시작 밀도·재고는 그대로) | 창 b0 에서 가리킴 규칙 충족. 함께 시작 편향과 b0 편향의 비를 적음. τ 가 12 s 라 시작 속도 효과는 b0 안에서 빨리 줄어듭니다 [추론] |
| **C8** (r2) | **예견항의 차로 도약(셀 18)** | metanet.py:113-121, AFA:370·:392, ADP:9560-9567 | 셀 18 행의 ν(`metanet_nu_km2_h`) = 0. 셀 18 의 예견항 전체가 빠집니다(혼잡 때의 실제 예견도 함께 빠짐) | 가리킴 규칙 충족. C4 와 함께 셀 18 의 차로 감소 표현을 봄 |
| **C9** (r2) | **차로 감소 두 항 함께(C4 + C8)** | 위 둘 | φ_lane = 0 그리고 셀 18 ν = 0 | 가리킴 규칙 충족. C4·C8 이 각각은 못 미쳐도 함께는 미칠 수 있어 둠(두 항은 셀 18 에서 서로 얽힘: φ 항은 v² 에, 예견항은 ρ 에 걸림) |

- 줄임 비율 R_c,m = 1 − |e_c,m| / |e_0,m| (e_0 = 같은 상태 EXEC 의 기준 편향, e_c = 절제 굴림의 편향, 같은 VISSIM). |e_0| < 1 km/h(속도) 또는 < 1 veh(재고)이면 R 은 정의하지 않습니다.
- 가리킴 규칙(후보 c, 지표 m): 정의된 상태 수 n ≥ 6, R ≥ 0.5 인 상태가 ⌈2n/3⌉ 이상, 중앙 R ≥ 0.5. 충족하면 "c 가 m 편향을 가리킴" 으로 적습니다(C2 는 "×1.2 민감도 규칙 충족"). 중앙 R ≤ −0.2 이면 "c 를 빼면 m 편향이 커짐" 으로 적습니다. 띠: 중앙 R ≥ 0.5 = A, 0.2 ≤ 중앙 R < 0.5 = B, 그 밖 = C.
- 방향 칸은 규칙에 들어가지 않는 읽기 보조입니다. C1·C2 가 규칙을 채웠는데 방향 칸이 반대(C1: plant FD 속도가 이미 VISSIM 보다 빠름, C2: "근거 없음")면 표 옆에 "방향 근거 없음" 을 함께 적습니다.
- 여러 후보가 같은 지표를 가리킬 수 있습니다. C9 말고는 항끼리의 겹침을 가르지 않습니다.

### 5.5 목록 밖 항 (이번에 빼지 않음)

- **출구 막힘 속도 상한**(AFA:346-354·:399-401; 출구 셀 9·11·18·20): 이번에는 X1 로 작동 여부와 양만 잽니다. 빼는 절제는 하지 않습니다. 빼려면 출구 저장(`urban_link_storage`·`urban_link_storage_veh`), 포트 용량(`DelayedPort.capacity`), 10481 의 SA 접근로 배수를 함께 바꿔야 하고, 그 설계는 따로 정해야 합니다 [읽음 lane_offramp_runtime.py:56-61·:138-146, lane_plant_runtime.py:378-391].
- **출구 분율**(`off_ramp_split_ratio` 또는 경로 재고): plant 출구 차량(X2)만 적습니다. VISSIM 출구 차량은 기존 스캔에 없어서 편향을 못 냅니다.
- 이완 τ·κ, 셀 18 밖의 예견 ν, FD 모양 지수 a, 입구 원천 용량과 수요 예보, 끝 경계, 차로 프로파일의 출구 역류 감소, 신호·도시 쪽에서 오는 합류 램프 방출(미터 굴림은 REC·EXEC 그대로). Hadi 수용 상한은 V-A FW_E 에 없습니다.
- 아홉 후보가 모두 가리키지 않으면 "목록 밖 항에 남음" 으로 적고, X1 이 1 veh 이상인 상태 수를 함께 적습니다. 다음 단계(예: 출구 막힘 절제 설계)는 사용자가 정합니다.

### 5.6 표

- P1-F(원천 12 × 셀 8–25 저밀도 속도 중앙, 셀 18 − 셀 16–17), P1-P(작업자가 본 매개변수, VISSIM 저밀도 점, plant FD 속도, C1 값), P1-B(상태별 기준 편향 m1–m5, 시작 편향, X1 10481·10483, X1 요약 줄), P1-R(후보 9 × 지표 5 의 n, R ≥ 0.5 수, R ≤ −0.2 수, 중앙 R, 띠, 규칙 충족, 기준과 비트 같은 상태 수, 방향 근거). 도달 점검·비트 같음·절제별 X1·X2 는 JSON 에 상태별로 둡니다.

## 6. 산출물

- 결정 상태·원천: `VP/decl/VP_STATES.json`, `VP/decl/VP_FZP_SOURCES.json`, `VP/decl/jobs_fzp.json`, `VP/decl/specs/spec_A_*.json`·`jobs_A.json`(r1 그대로, A 명세에는 절제가 없어 바뀌지 않음).
- plant 일: `GT/out/plant_A/<시드>_T<T>/`, `GT/out/plant_P/<시드>_T<T>/` 마다 `probe.json`, `hooks/vphook_*.json`, `job_summary.json`, `bundle/`, 로그.
- FZP: `GT/out/fzp_cell/<원천>.json`, `GT/out/fzp_frames/VA_v3c3-s<S>.json`.
- P1 입력·명세(데이터 뒤 기계적 생성, 규칙은 §5.4, 절제 C1–C9): `GT/out/p1_specs/p1_inputs.json`, `spec_P_*.json`, `jobs_P.json`.
- 표: `GT/out/tables/vp_tables.json`, `vp_tables.md`. 보고: `VP/VP_RESULTS.md`(다음 단계), 사본 RVP.
- 검토 r2 기록: `VP/PRE_VP_r1.md`, r1 도구 사본(`tools/*_r1.*`, `tools/vp_hooks/sitecustomize_r1.py.txt`), r1 핀 목록(`SHA256SUMS_VP_r1.txt`, `SHA256SUMS_VP_EXT_r1.txt`), `VP/review_r2/`, smoke v5 기록.
- 로그: `VP/LOG.md`(KST 덧붙임), `VP/logs/<일 묶음>/queue.log`, plant 일마다 `jobcheck.json`.

## 7. 멈춤 규칙 (걸리면 남은 무거운 일을 하지 않고 보고, 사용자가 정함)

- S-R1: R1 이 어긋남(§3.4). 그 일에서 탐침이 스스로 멈추고(종료 코드 5), 큐가 `VP/STOP_VP` 를 씀.
- S-R3: REPACK 이 REC 와 비트 다름. S-NULL: null 절제가 EXEC 와 비트 다름. S-REACH: 절제 값이 작업자에 닿지 않음(C1–C9). S-HOOK: 훅 걸음·블록·셀 수가 어긋나거나 훅 오류. S-MAP: 셀 경계가 CELL_B 와 1 m 넘게 다름.
- S-ERR: 탐침 예외, 재생 묶음 실패, 핀 sha 다름, 디스크 < 8 GB.
- S-BLIND: 봉인 시드(37·59·61·67)·v3c3-s47·`sealed` 이름이 걸림(도구가 거부).
- 출구 기록(X1·X2)이 빠진 것은 멈춤 규칙이 아닙니다. 표에 "못 냄" 으로 적습니다.
- 각 plant 일(H2·H3)이 끝나면 큐가 `vp_jobcheck.py` 로 S-R1·S-R3·S-NULL·S-HOOK·S-MAP·S-REACH·S-ERR 를 바로 보고, 하나라도 걸리면 `VP/STOP_VP` 를 쓰고 남은 일을 하지 않습니다.
- 표 도구도 걸린 규칙을 "멈춤 규칙 걸림" 칸에 모두 적습니다. 걸림이 있으면 그 상태의 표 칸은 쓰지 않고 보고에 이유를 적습니다.
- 워치독: plant 일 하나가 45 분 동안 출력·진행 파일을 바꾸지 않으면 그 일의 자기 프로세스 트리만 끝냅니다(다른 세션의 VISSIM·python 은 건드리지 않음).

## 8. 순서와 비용 (가벼운 것 먼저)

| 단계 | 일 | 잠금 | 어림 시간 |
|---|---|---|---|
| L0 | 핀 대조(VP 에서 `sha256sum -c SHA256SUMS_VP.txt` 와 `sha256sum -c SHA256SUMS_VP_EXT.txt`; 하나라도 다르면 S-ERR), 자체 시험 다시(`vp_selftest.py`, 모두 참) | 없음 | 1 분 |
| H0 | 코드 사본 다시 대조(`vp_tree.py verify`, FREEZE.json 10,569 파일; 어긋나면 S-ERR) | 잡음 | 3–5 분 |
| L1 | `vp_analyze.py p1-fzp` — 이미 있는 NC3·VSL 스캔으로 P1-F 일부 | 없음 | 1 분 |
| H1 | FZP 스캔 9개(`decl/jobs_fzp.json`: B·V-A 셀 스캔 6, V-A 프레임 3) | 일마다 | 스캔 하나 약 25–35 s [읽음 기존 로그] + 일마다 쉼 20 s → 합 약 5–10 분(+ 잠금 대기) |
| L2 | `vp_analyze.py p1-inputs GT/out/p1_specs` — C1·C7 값, P1 명세 9개(절제 C1–C9) | 없음 | 1 분 |
| H2 | 탐침 A·B 12상태(`decl/specs/jobs_A.json`) | 일마다 | 상태당 약 4.5–7 분(준비 약 50–60 s + AD 약 130–235 s + 스칼라 묶음 약 70–100 s), 합 약 1–1.4 시간(+ 잠금 대기) |
| H3 | P1 9상태(`GT/out/p1_specs/jobs_P.json`) | 일마다 | 상태당 약 8–11 분(위 + 절제 10굴림(null + C1–C9)을 동시 4개씩 세 차례), 합 약 1.2–1.7 시간(+ 잠금 대기) |
| L3 | `vp_analyze.py tables GT/out/tables/vp_tables.json …md` | 없음 | 1 분 |

- 무거운 일은 `vp_launch.ps1` → `vp_queue.py`(WMI 분리, BELOW_NORMAL, PYTHONHASHSEED=0, python -B, NUMBA_NUM_THREADS 지움). 공유 잠금 `D:/VISSIM-merge/k8_gate_trees/heavy.lock` 을 일마다 배타 생성으로 잡고, 자기 것(owner + pid)만 지우며, 우리 마지막 해제에서 20 s 이상 지난 뒤에만 다시 잡습니다(C1 guard design·C1 워크플로와 차례). 폴링은 9 분 이하.
- 끊기면 다시 띄웁니다. 끝난 일(`.done`)은 건너뛰고, 중간에 끊긴 일의 출력은 `*_interrupted_*` 로 옮긴 뒤 다시 합니다.
- 탐침 B 와 P1 은 H2·H3 의 같은 굴림에서 나옵니다(굴림을 따로 하지 않음).

## 9. 도구 핀 (이 문서와 함께 고정)

- 핀 목록 파일 `VP/SHA256SUMS_VP.txt`(39줄, VP 기준 상대 경로, `sha256sum -c` 로 대조) sha256 `51f9f38bdd1c2b2806161f442ae4af0d1df24105d69050697ba44cd863430156`, 바깥 핀 `VP/SHA256SUMS_VP_EXT.txt`(15줄, 절대 경로) sha256 `5e84baf4b90c799efe1efb20911038ee8a17264a7934c76de59380ae82c21ad6`. 두 목록 모두 [실행] `sha256sum -c` 걸림 0. r1 목록은 `SHA256SUMS_VP_r1.txt`(5c36cffa…)·`SHA256SUMS_VP_EXT_r1.txt`(7ce3016b…)로 둠.
- 주요 sha (r2 에서 바뀐 것은 ★):
  - ★ `tools/vp_probe.py` `1c08ad5b76f570806dbb4dba8b7aab6d5619cabbbc9be8df61b9d87e9f1c6091` (r1 c38fc1a9…)
  - ★ `tools/vp_hooks/sitecustomize.py` `b498eee0a0a4715bea2ea5c22594ac9dd938d3eda3adfd6e60f95d0c9435a833` (r1 1c212040…)
  - ★ `tools/vp_analyze.py` `a3638816003144d2d910d1b474d07221fe7ac319ed68ed3a32cf6549885536a7` (r1 faff15d4…)
  - ★ `tools/vp_selftest.py` `8d3e33fb837465c56ea5a323dd1930482fc047bbcfc718e2bc7a46bce4bbc026` (r1 2834d829…; 결과 `selftest/selftest_final_r2.json` `48efab47c42837aef6e8283fcae65a7eccd7d44284e01d2274bd289dbe424a9a`, 65/65)
  - ★ `tools/vp_smokecheck.py` `bff8c49c2ccf6e7f91a22d32af96be95bd9b441251980755b898148274f80bfc` (r1 6ee274ee…)
  - ★ `tools/vp_pin.sh` `5325b9dde02233bb6296d55bd7583b034896d547ff8c15cb27c53fdb6141cb10` (r1 f40cdbcd…)
  - `tools/vp_job.py` `2164f97ed16bcbd3e2c095ea23435f9524ab0695c6a9a1533016dbe297d94baf`
  - `tools/vp_queue.py` `53efbad49aece715e05bf1c28ac473daac9f8a3ec8bcdf5da5790c5639c94e3d`
  - `tools/vp_jobcheck.py` `a922ab6d6bb7b8e06ad1b0d00123844a6931d7c9071787cca3cde980a54c0ae7` (바뀌지 않았지만 `vp_analyze.ABLATIONS` 를 읽어 C8·C9 도 점검함)
  - `tools/vp_common.py` `a8cdeff508c72ceb320a4dd98a555820016678e6b9d1c98d132a50ae2eed6691`
  - `tools/vp_states.py` `1ff348f5f96971118f68f626389b4547cb02093b824211d64598b77ff06d1dfe`
  - `tools/vp_fzp.py` `e93103526b2bfe5c1904b16ebf87e344d75944ac780558093f119c50e5a9b469`
  - `tools/vp_tree.py` `c84d53b07ca3f6b63a665bd51835f765160ff13d0d835546c4045a3cebe69cca`
  - `tools/vp_pinned.py` `eedaf1b73f8c4d46ec8471c2a3ec3205092e64333937f5a8a60002ee2e690b29`
  - `tools/vp_launch.ps1` `efbc4ebfb536f602fdf8e2438432016964b3b9aae91e676c59db85c8d3221247`
  - `tools/vp_tablesmoke.py` `570f38989095723bf7cfd1c1c42899858fc50c7951e54ab3320aa3569ea2a534`
  - `decl/VP_STATES.json` `8f09c649522e43fffa87ee9ce2042ea1b8e1c08175a3c6238bf1839410f44fc8`
  - `decl/VP_FZP_SOURCES.json` `2bdf0e7d75c14b78b4c0124861e4ec85bd08b84441fe9165318be84e8aaa5a14`
  - `decl/jobs_fzp.json` `3b4f96a4abe7d1a90dc41a7e46b7d9ad0f8164ae8be3cc1445d2d4d065165638`
  - `decl/specs/jobs_A.json` `b68e18f2860f9735ce93b9336f7a2f8e1bbc9750c1bbe6dca139e3d2e9587c3f` (spec_A 12개 sha 는 목록 파일)
  - `PRE_VP_r1.md` `4147f8595506bf2fdc8465a45eb2d94886116acef2535255654dff5e97317eac`
- 재사용(남의 도구·출력, 바이트 그대로 sha 로 씀): `SP/vsl_v3c3/tools/vsl_cell_scan.py` `fa5aeafd…`, `SP/vsl_v3c3/o1o2/tools/o2_fzp_cells.py` `cff42e34…`, 구역 정의 원천 `SP/vsl_v3c3/o1o2/tools/o_analyze.py` `bc9ac1ef32ee81de7ba6e4faa30a0657cbf64a2e0b8e5c284d5f21d828a5a518`(읽기만, 실행 안 함), `SP/j1/fix/gates/gprep.py` `0482a538…`(그 안에서 부르는 `make_replay_state_v2.py` `4adf41cf…`), NC3·VSL 셀 스캔 여섯 개(EXT 목록).
- 코드 뿌리 GT/code_va = FRZ_K92 사본, FREEZE.json sha `011f5be253fd31a5fb8342859b2b571375e49b4bbbbb42ea8f3ca93657b68476`, 대조 기록 `GT/code_va.tree.json` `53e4403f…`(10,569/10,569).
- 검토 r2 의 일회용 편집 스크립트 `VP/review_r2/edit_analyze_2.py`·`fill_fixed.py` 는 도구가 아닙니다(실행 경로에 없음).

## 10. 하지 않는 것

- VISSIM·COM·러너 실행 0, 동결 0, 커밋·푸시 0, GWT8 손대지 않음(c20aff1d 그대로), FRZ_K92·런 폴더 쓰기 0. 도구 고침은 VP 스크래치 안에서만.
- 금지 시험 0: test_b1a_watchdog_attempt_launch.py, run_plant_fidelity_matrix, test_runner_ps1_obs150.py, test_native_vbs_clock.py, test_tools_launch.py, test_tools_replay.py, real_watchdog.
- 봉인 시드 37·59·61·67 열기 0, codex 64cf-s59/s61/s67 숫자 0, v3c3-s47 값 0.
- φ 사잇값(Q-V5) 0. 새 VSL VISSIM 런(D-K9-102) 0.
- 바뀐 정책 토큰으로 결정 전체를 다시 푸는 재생 0(가격 적재에서 멈춤; 대신 기록 상태에서 한 결정짜리 plant 굴림만 함).
- 출구 막힘 절제 0(§5.5, 사용자 선택지).

## 11. 변경 기록

- r1 (16:54 KST): `PRE_VP.md` 4147f859….
- r2 (2026-10-27 17:28 KST): 이 문서. §R 의 R-1–R-8 을 고침. 바뀐 도구: `vp_probe.py`(C8·C9 가지, 설명 글), `vp_hooks/sitecustomize.py`(X1·X2 수동 기록), `vp_analyze.py`(C8·C9, X1·X2, 방향 칸, 표 B5), `vp_selftest.py`(검사 추가), `vp_smokecheck.py`(출구 기록 참/거짓), `vp_pin.sh`(핀 목록). 바뀌지 않은 도구: `vp_common.py`·`vp_states.py`·`vp_tree.py`·`vp_fzp.py`·`vp_pinned.py`·`vp_job.py`·`vp_queue.py`·`vp_launch.ps1`·`vp_jobcheck.py`·`vp_tablesmoke.py`, 선언 파일 전부.
