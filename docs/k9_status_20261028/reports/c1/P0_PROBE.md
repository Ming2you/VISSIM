# C1 P0·미니 탐침 보고 r2 (2026-10-27 KST) — **STOP: 탐침 멈춤 2 (Ω 팔 궤적이 OFF 와 다름), 구현 전 사용자 결정 필요**

- 한 줄 요약: P0 는 모두 끝났고 점검 단계는 모두 PASS 입니다(P0-1·2·3·4·5·6·11·13). 보고 단계(P0-7·8·9·10·12)도 끝났습니다. 미니 탐침은 plant 첫 상태(v3c3-s31 T=1,500)에서 Ω 팔의 행별 장부 재고 궤적이 OFF 와 첫 행부터 달라 **멈춤 2** 에 걸렸습니다. 규칙대로 남은 plant 15상태와 결정 35개는 돌리지 않았습니다.
- 이 판(r2)은 r1(`C1D/P0_PROBE_r1.md`, sha256 `5755da898b6f653c90dec23a50abf69664529bd72dafaca0e2ad2a97c92d91c9`, P0-4 INCOMPLETE 멈춤 보고)을 이어 씁니다. r1 은 그대로 남겼습니다.
- 판정 낱말은 쓰지 않습니다. 결과는 PASS / STOP / 보고 와 숫자로만 적습니다.
- 표시: [실행] 이번에 돌려서 확인 · [읽음] 문서·코드에서 확인 · [추론] 시험하지 않은 판단.

## 0. 줄임말 (처음 한 번만)

- SP = `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8`, C1D = `SP/c_port/c1`, TC1 = `D:/VISSIM-merge/k8_gate_trees/c1`(C1 스크래치 뿌리), RC1 = `D:/VISSIM_runs/20261001_v3c3/reports/k8/c_port/c1`(보고 사본), GWT8 = `D:/VISSIM-merge/sim3-n31-k8`, CX = codex 인계 트리 `D:/VISSIM-merge/k8_gate_trees/codexhandoff/a49981ff`, B0F = B 런 동결 트리 안의 `diagnostics/b0_v3c3`.
- 보충 C1 = `SP/K8_PREDECLARATION_AMENDMENT_C1.md`(고정판). P0 = 탐침 전 점검(보충 C1 §4). 미니 탐침 = 구현 전 보고용 재생(§5).
- Ω701 = codex 목적 영역(링크 701개 = 우리 Ω635 + 신호 17곳 접근로 66링크). OFF = c1_port 키가 없는 팔(지금 코드 길). Ω 팔 = Ω701 키만 켠 팔. H 팔 = FW_E 미터 4개 머리 서비스 표 키만 켠 팔. M 팔 = 미터 결정 묶음 키 5개.
- plant = 제어기 안의 교통 예측 모형. plant 잡 = 기록된 행동을 그대로 두고 plant 만 굴리는 오프라인 계산. 궤적 = 행(약 0.5 s 마다)별 장부 재고 `model_stock_veh`(키 638개). OUTW = 예측 450 s 동안 Ω 밖 모형 대기(veh·h). LOCK = 무거운 일 공유 잠금 `D:/VISSIM-merge/k8_gate_trees/heavy.lock`.
- SG2 = SC1001 동쪽행 직진 신호 그룹(EBT), SG5 = 동쪽행 좌회전(EBL). GREEN 만 = 노랑·전적색을 뺀 녹색 초.

## 1. 고정 확인과 사용자 결정 적용 [실행]

- 보충 C1 sha256 `a98580dd2d787007ab961d692668c4a4042c79d7993f87af972cbc19d1f53acf` = 고정점 `C1D/AMENDMENT_C1_FIXED.md`(`7083d136…`) 값. 결정 기록 `SP/K9_1_J1_NOTES_20261013.md` = `cb84bf22154b7c989b5a9a1cac2938b0ec7b88976e9655244879b75b3fd43e65`(D-K9-96·97 행 :320-326).
- **D-K9-96** 적용: `C1D/tools/c1_p0.py` 의 `git grep` 세 호출(:314·:316 P0-2, :589 P0-4)에만 `encoding='utf-8', errors='replace'` 를 더했습니다. 셈 줄 변경 0, 줄 끝 CRLF 그대로. diff 는 LOG 의 "P0 도구 고침(D-K9-96)과 다시 고정 PINS_P0_r2" 항목에 그대로 있습니다. 도구 sha `a7f1c479…` → `4cd1bb1655eeca7887dfb3b8436a4803fcd45d58d335482c8c1710c40eaa11d8`. 새 고정 목록 **`C1D/PINS_P0_r2.sha256` = `75ead5ba4b770d7e9ed2747e37a33a3dd7fcc46fba64fd91dbea47bf19c9e11a`**(28줄, 28/28 OK). 옛 목록과 다른 줄은 `c1_p0.py` 한 줄뿐입니다. 고침과 고정은 새 계산(13:35:51) 전에 LOG 에 적었습니다.
- P0-1(`ee39291f…`)·P0-2(`e25f8f0f…`) PASS 는 다시 돌리지 않고 유지했습니다. 탐침 멈춤 4(C1 팔 결정 중앙 > 1,500 s)는 고정 그대로입니다.
- **D-K9-97**(RV-1 `np_only` 함께 옮김, RV-2 저장 보호 하한 표 내림)은 이미 보충 C1 고정판과 탐침 패치(`5cdc6eb1…`)에 들어 있습니다. 이번에 바꾼 것은 없습니다.

## 2. P0 결과

| # | 결과 | 숫자·근거 (`TC1/out/p0/<단계>/result.json` sha) |
|---|---|---|
| P0-1 Ω701 소속·경로 계약 재현 | **PASS** (r1) | 소속 바이트 `9bb740b3…`, 안 701 / 밖 535, 경로 계약 `08fec9c7…`, turn 57. CX 쓰기 0. `ee39291f…` |
| P0-2 재결속 재현 | **PASS** (r1) | 다시 쓰인 문서 9, 지지 문서 차이 63, `4863f5ee…` 두 판, 연결자 지원 29, 경로 핀 111/106/5. `e25f8f0f…` |
| P0-3 구조(설정만, 5상태 × 5팔 = 25회) | **PASS** [실행] | 25회 모두 끝까지 감. 5상태 모두: E_M = 10경로(허용 목록 안), E_H = 35경로(허용 목록 안), E_C1 = E_Ω ∪ E_M ∪ E_H(같음), `input:` 차이 = 7 gate(밖 생성 → 생성), S_add = 36키(5상태 같음), Ω 에서 빠진 키 0. `6a41a995e09a4a62a9980f9699bc004ea7096f44f24495b6e9e7c58cebab472e` |
| P0-4 머리 표 증거 | **PASS** [실행] | 재생성 바이트 `3933a882…` = 선언 바이트, 설치 표 repr = 보충 C1 §2.7, CFG_B `729640af…`. Q26 출처는 §3-4. `db9440380776293d913d587abf5fa7ca2a3e827145566d3cba57c9a217039abd` |
| P0-5 저장 보호 상태 이름 | **PASS** [실행] | 8미터 모든 차로 부분이 `snapshot()` 두 키·`head_position_m`·`lanes`·`spacing_m` 를 가짐, 용량 유한·양수, 점유 유한·0 이상. 5상태 모두 보호 발동 0(차로 점유율 최대 0.227), 하한 2. `c1a0857ba94b96006ca54d8affac5c4ccebf059c0d9c3e95eb0e151d05e226d5` |
| P0-6 정책 토큰 표 | **PASS** [실행] | OFF·Ω·H·C1⁻·{allow_zero_green}·{storage_release_guard}·{held_retention}·{max_leader_candidates} = `428e650d…`(키 끔 그대로). M·M_cap1·M_noheld·C1 = **`522eec6f32f198a12ddb78ddec10962a73c7ebc32e2d1fcbb11f95975218d865`** 하나. joint cap = 키 있으면 3, 없으면 1. `2a4c6b3762b7700727085d81e79b81f4e154be59252df7277273d149c4f97bc0` |
| P0-7 블라인드 노출 목록 | 보고 [실행] | 첫 줄 "D-K9-84 Q3 의 Ω701 재집계는 V-A·J1·NC3 9런, R-obs 아님". 이름·키 이름만 훑음(값 안 엶): 이름에 s47 이 든 파일 39,721개(F 창 T 37,373, 키 이름 걸림 10,451, 봉인 폴더 이름만 12,542). 목록 `exposure_list.json` = `4df3b1cc7375b52f39d179d7a7078f6f72c3d463588ae3fbf75290afa2e6120e`. `34ca1825…` |
| P0-8 B 저장 보호(RM_C10639) | 보고 [실행] | §3-1. `fe0aed0b235b2f666fa56a50e980912d6a837d62fed221651a677e873bfe9739` |
| P0-9 B 의 SG2 단축 까닭 | 보고 [실행] | §3-2. `bb90e1370b051d881abfed98e504b3fbbf988ebfef120987d60b3c00161d3f96` |
| P0-10 plant 사슬 표현 | 보고 [실행] | §3-3. `4922cc0cad1334e2f1ef188242906e55d8bcf0351a8cd089585ae288f4db8316` |
| P0-11 기대 이웃 후보 수 | **PASS** [실행] | 합성 식 시험 참. 5상태 모두 u_E 4, u_W 4 → 조임 후보 N = 10, 풂 0, 계획 g8/g6/g4. `78df18b44efa7e8de1d0333938009b19a93dfa668b0d96075bdf6a028109e858` |
| P0-12 문서 | 끝 (r1) | 정정 메모 `SP/codex_handoff/B_RESULTS_ERRATA_20261027.md` `6276c4a7…`, `C1D/NETWORK_CANDIDATES_C1.md` `fed31a8a…`. B_RESULTS r2 `152a2f6f…`·VERIFY_B `f2851f8b…` 원본 그대로 [실행 sha] |
| P0-13 비교기 정규화 자기 시험 | **PASS** [실행] | 합성 경로 12/12 가 `<root>`·`<bundle>`·`<run>`·`<name>` 로 바뀜. `62d30a487c0e9c452f427f39942bed515abb2303a046ad74835d65398b1747e4` |

- **`C1D/C1_VALUES.json` = `7106e2403a61755ea09165c5fcd7be54a2169d6df7c48511c3aa31d87432421d`** [실행 13:56:19, 배타 생성]. P0-3 차이 집합·S_add, P0-5 점유·하한, P0-6 토큰 표, P0-7 목록 sha, P0-11 기대 수가 들어 있습니다. 첫 탐침 계산 전에 LOG 에 고정했고 그 뒤 바꾸지 않았습니다.

## 3. P0 읽기 결과 (보고만, 값·문턱은 바꾸지 않음)

1. **Q20 / P0-8 — B 저장 보호가 10639 g2 대기를 왜 안 풀었나** [실행 B 결정 JSON T = 900 … 8,100, 시드마다 49개]: B 의 RM_C10639 보호는 세 시드 모두 **한 번도 발동하지 않았습니다**(0/49, 0/49, 0/49). 모형 차로 용량은 52.47대이고, 발동 문턱 0.9 는 47.2대입니다. 관측 점유율 최대는 0.858 / 0.819 / 0.877(v3c3-s31 / s41 / s43)로 문턱 밑이었습니다. 실행 녹색 g2 인 결정에서 미터 앞 대수 중앙은 42.5 / 13 / 44 대였습니다(READBACK g2 블록 미터 앞 중앙 42.6대 [읽음 RB:175]). 그래서 하한은 늘 2 였습니다. [추론] B 의 g2 대기는 보호 문턱 바로 밑에 머문 상태였습니다.
2. **Q21 / P0-9 — B 가 900–2,700 s 에 SG2 를 왜 줄였나** [실행 B 결정 JSON·CSV, GREEN 만 식]: SG2 계획 합 S_SG2 = B 408.9 / 410.5 / 512.4 s, V-A 기록 575.7 / 640.6 / 680.1 s, NC3 540 s(GREEN 만). B − V-A = −166.8 / −230.1 / −167.7 s 로 readback 차(−172 / −229 / −168 s)와 비슷합니다. 이 창에서 B 의 가격은 모두 0 입니다(`next_prices_scaled` 0·0, SC1001 `price_gradient` 0, 36결정 모두). SG2(= 현시 p3)는 T=900 의 39.0–48.0 s/150 s 에서 1,500–1,800 s 에 25.8–38.3 s 까지 줄고, SG5(= p4)는 25.2–30.0 에서 42.0–46.4 s 로 늘었습니다. v3c3-s43: SG5 합 481.0 s(NC3 288 s 대비 +193 s), p1 은 40.0 → 24.0 s 로 줄고, offset 은 0.0 → 61.6 s 사이에서 움직임. [추론] 단축은 가격(외부 신호)이 아니라 SC1001 자기 비용 쪽 선택이고, 줄인 녹색이 좌회전(SG5)으로 갔습니다. "Q2·Q3 를 다시 볼지" 는 이번 질문에 함께 올립니다(§6).
3. **Q22 / P0-10 — plant 가 127 → 129 → 10491 → 26 사슬을 보는가** [실행 P0 트리 코드 훑기; `stopline_approach.py` 는 패치 밖이라 줄 번호 = c20aff1d]:
   - 링크 127: SC1001 EB 정지선 링크(받는 곳 `in_SC1001_W`) — `stopline_approach.py:349, :394, :413, :431`.
   - 링크 129: 접근 사슬 32 / 10778 / 129 / 10777 의 한 고리, OR_D_W 착지에서 온 "129 꼬리" 차량 — `:33, :482, :929, :955, :1195-1199`.
   - 10491: OR_D_W 포트(지퍼 상류), 막힘·만차 계수 `port_blocked_steps_10491`·`port_full_steps_10491`·`port_release_veh_10491` — `:116-118, :134-135, :413-419, :1502-1504`.
   - 링크 26(FW_W 본선 차로 1 끝): 코드·plant manifest·OUC 걸림 0 → F-S 의 그 줄은 **"모형 대응 없음"**.
4. **Q26 / P0-4 — 머리 곡선(녹색 1초당 0.5대/차로, 상한 4.2)의 출처** [실행]: 인계 문서(`D:/VISSIM_handoff/20261024` 의 .md, raw·derived 밖) 걸림 0. CX 코드에서는 곡선을 reference config 의 `/freeway/physical_ramp_head_service_veh_per_cycle` 에서 읽고(CX `diagnostics/demand_sweep/user_native_20260914/metanet_calibration_v1/canonical_harness.py:400`), codex 시험이 꼴 `min(0.5·g, 4.2)` 를 적습니다(CX `diagnostics/sdmpc_n31_20260924/tests/test_meter_activation.py:36`; `tests/test_meter_neighbors.py:76` 에 '9' = '10' = 4.2). 실측에서 뽑았다는 문서는 찾지 못했습니다. 값은 Q4 규칙대로 그대로입니다.

## 4. 미니 탐침 — 한 일

- **고정** [실행 13:57, 첫 탐침 계산 전]: `C1D/PINS_PROBE.sha256` = `5dfb83b1e8a3a9bc2221610f0b2a473609e6d74f66bcffe87120d117c5d4886d`(23줄, 23/23 OK). 들어 있는 것: `C1_VALUES.json` `7106e240…`, 탐침 도구 `c1_probe.py` **`9446f0287fbaea33b123321f393b682332755b66027ae04ae963611635b0e799`**, 자체 시험 `c1_probe_selftest.py` `55dc58cb…`·출력 사본 `e07ba741…`(90/90), 패치 `5cdc6eb1…`, 팔 튜닝 7개 + ARMS, 탐침 트리의 `k92_replay.py`·`k8b_commit_gates.py`·`c1_port.py`·`sdmpc.py`. 탐침 트리 `probe_5cdc6eb1` 은 패치 manifest `post` 20파일 sha 와 모두 같음.
- 탐침 도구는 r1 때 초안(`f40cd799…`, 고정 전)이었습니다. 고정 전에 고친 것 [개발]: 시드·이름표를 `c1_states.json` `/runs` 의 provenance 값으로(폴더 이름에서 읽지 않음), 결정 JSON 의 실제 키 이름(held·하한·점유·후보 표), 직전 명령 = `action_000750.json` `diagnostics.rw_meter_green_*`(S-C1-7 정의), 멈춤이면 `HALT.json` 을 쓰고 다음 계산을 하지 않음, plant 먼저 → 결정(팔 순서 c1, m, omega, h, off, m_cap1, m_noheld). 자체 시험 첫 판 89/90 에서 "DECISION_FAILED 수 없음(None)을 깨끗하다고 봄" 결함을 찾아 고쳤습니다(합성·개발 스모크 출력만 씀, 탐침 데이터 0).
- **plant 단계** [실행 13:57:40 발사, WMI 분리·BELOW_NORMAL; LOCK 기다림 13:57–14:07(VSL 워크플로), 계산 14:07–14:12:51]: v3c3-s31 T=1,500 에서 세 팔 모두 capture·job 이 끝났습니다(exit 0, `ok` 참, 기록기 오류 0). 그 뒤 HALT.
- **report 단계** [실행 14:13:55 발사, LOCK 14:24:19–14:24:20]: `C1D/C1_PROBE_RESULTS.json` = `5b0bcfb05246cc7099929c03b806ba4cb03a5cbc39c5e9de3bd0dcbde80a0b5a`.

## 5. 미니 탐침 — 결과 (탐침, 판정 아님)

**plant v3c3-s31 T=1,500 (H3, OBS)** [실행 `TC1/out/probe/plant/sa/jobs/c1p<팔>/TL3_1500_SAF_OBS_H3/`]

| 팔 | 끝남 | 모형 목적(veh·h, 그 팔의 Ω) | OUTW 450 s (veh·h) | 목적 + OUTW | 궤적 = OFF |
|---|---|---|---|---|---|
| OFF (Ω635) | ok | 434.995 | 861.539 | 1,296.534 | — |
| Ω (Ω701) | ok | 504.165 | 792.620 | 1,296.785 | **다름** (638키 가운데 82키, 22,144칸, 첫 행부터) |
| H | ok | 434.995 | 861.539 | 1,296.534 | 같음 (900행 × 638키 비트 같음) |

- Ω 팔 궤적 차이의 꼴 [실행, 내 출력 읽기만]: 첫 행(t_end 1,501 s)에서 다른 키는 3개 — `storage:SC106_to_SC12` +1.0대, `storage:SC2005_to_SC101` +0.5대, `storage:SC101_to_SC1002` −0.5대(합 +1.0대). 그 뒤 퍼져 450 s 끝 합 차 +1.033대, 키별 최대 |차| 1.0대. 다른 82키 가운데 S_add(66링크 재고 키) 안 16, 밖 66. 종류별로 movement 키 45·storage 키 32·`freeway:FW_W` 1·`ramp:` 2(RM_C10480·RM_C10484)·`merge_pending:` 2.
- 기구 [실행 읽기 + 추론]: Ω701 묶음의 지지 문서(`physical_projection_support_635_proposal_ec2393.json`, B0 판 `7d092b3d…`)는 더한 커넥터 29개에 `link_to_storage` 를 줍니다(글: "restore its native initial stock channel"). 그 가운데 3개(10049·10225·10229)가 `SC106_to_SC12`, 6개(10485·10502·10503·10505·10506·10507)가 `SC2005_to_SC101` 로 갑니다. [추론] 그 커넥터 위의 관측 차량이 Ω701 에서는 하류 저장고로 투영되어 **초기 재고가 바뀝니다.** 그래서 회계만이 아니라 궤적이 첫 행부터 달라집니다. 목적 + OUTW 차 +0.25 veh·h 는 이 1대 남짓의 초기 재고 차와 같은 크기입니다[추론].
- 보충 C1 의 기대와 다른 점: §2.2 [검토 RV-20] 과 §5.3 은 "Ω 팔은 장부 회계(안/밖 코호트·생성 표지)만 바뀌고 셀·저장고 궤적은 OFF 와 같다" 를 [추론] 으로 적었습니다. 이번 결과는 그 추론과 다릅니다. P0-2 의 "지지 문서 차이 63잎(link_to_storage 29·evidence 33·revision 1)" 은 바이트로 맞았지만, 그 29개가 초기 재고에 닿는지는 선언 단계에서 보지 않았습니다.

**멈춤 규칙 (보충 C1 §5.4)** [실행 `C1_PROBE_RESULTS.json` `/stop_rules`]

| 규칙 | 결과 |
|---|---|
| 1 예외·장부·불변식 위반 | 0건 (돈 3잡 모두 끝남) |
| 2 Ω·H plant 궤적이 OFF 와 다름 | **걸림** — Ω 팔, v3c3-s31 T=1,500 (H 팔은 같음) |
| 3 M·C1 팔 5상태 모두 조임 없음 | 셈 못 함 (결정 0개 — HALT 뒤 돌리지 않음) |
| 4 C1 팔 결정 벽시계 중앙 > 1,500 s | 셈 못 함 (결정 0개). 참고: 개발 스모크 C1 결정 1개 1,869.5 s(판정 아님) |
| 끝나지 않음(INCOMPLETE) | 결정 35 + plant 15상태 = 50항목, 모두 HALT 때문에 돌리지 않음 |

- S-C1-3: 멈춤 2 는 **구현 전 STOP·질문** 입니다. 브랜치 `claude/c1-port-20261027` 만들기·커밋·관문은 하지 않았습니다.

## 6. 사용자에게 묻는 것

Ω701 이 초기 재고 투영을 바꿔 궤적이 달라지는 것을 어떻게 다룰지 정해 주셔야 합니다. 선택지 [추론, 판정 아님]:

- (가) **새 보충으로 기대를 바로잡고 이어 함**: "Ω701 의 지지 문서 29 커넥터가 초기 재고 투영을 바꾼다" 를 선언 차이로 적고, 멈춤 2·G-K1 동적·G-K2 (d) 의 Ω 조건을 "첫 행 차이는 그 29 커넥터의 하류 저장고 키에서만 시작" 같은 꼴로 데이터 전에 다시 고정한 뒤 탐침을 처음부터(또는 HALT 지운 뒤 이어서) 돌림. codex B 와 같은 묶음을 유지합니다.
- (나) **Ω701 을 소속·경로 계약만으로 줄임**: 지지 문서의 29 커넥터 `link_to_storage`·`evidence` 추가를 빼고 옮김(초기 재고 경로는 지금 그대로). 그러면 B 의 Ω701 묶음과 바이트가 달라지고, 그 29 커넥터 위 차량은 지금처럼 투영됩니다. 새 보충 필요.
- (다) **Ω701 을 C1 에서 떼고 미터 묶음(M·H)만 먼저**: Ω 는 따로 묶음으로 미룸. H 팔은 이번 상태에서 궤적이 비트 같았습니다.
- (라) 다른 방법.
- 함께 볼 것: Q21(§3-2)의 "Q2·Q3 를 다시 볼지"(B 의 SG2 단축은 가격 0 상태의 SC1001 자기 비용 선택이었음), 그리고 개발 스모크의 1,869.5 s 가 멈춤 4 문턱을 넘을 수 있다는 점.

## 7. 알릴 것 (막힘 아님)

1. **스레드 환경 글 차이**: 보충 C1 §3 은 "`NUMBA_NUM_THREADS=1`(K9-2 재생 꼴)" 이라 적었지만, K9-2 재생 도구는 이 변수를 빼고 돌았습니다(`SP/k92/bundle1/a25decl/tools/k92lib.py:99` `env.pop('NUMBA_NUM_THREADS', None)`) [읽음]. 이번 P0·탐침도 그 꼴(c1common `child_env`, PINS_P0 고정)이었습니다. 다음 단계 전에 어느 쪽인지 정해 주시면 좋겠습니다.
2. **LOG 머리 시각 두 번 바로잡음**(13:37 → 실제 13:35, 13:38 → 실제 13:36:53). 덧붙임으로만 고쳤습니다.
3. 개발용 자체 시험 출력 두 개(`TC1/out/selftest/c1_probe_selftest_dev1.json` 89/90, `dev2` 90/90)는 TC1 에 남겼습니다(판정에 쓰지 않음).
4. P0-3 참고: 모형 소속을 풀지 못한 장부 키가 OFF 303 / Ω 302 개(키별 `resolve_model_membership` 로 셈, 보고만).

## 8. 지킨 것

- VISSIM·COM·폐루프 러너·동결 0. 브랜치·커밋·푸시 0: GWT8 head `c20aff1d7bf0c432cb4f20e2922bd406d857aa5d`(브랜치 `claude/k92-b1-20261016`), status 0줄, `claude/c1-port-*` 0, K8 브랜치 `b9734abe…` 그대로 [실행 14:25]. 금지 시험 0.
- 무거운 일(P0-3·6·7·8·9, 탐침 plant·report)은 모두 LOCK 을 배타 생성으로 잡고 끝나면 내 LOCK 만 지웠습니다. 다른 세션(VSL 워크플로)의 LOCK·VISSIM·python 은 건드리지 않았습니다. 끈 프로세스 0. 끝에 내 프로세스 0 [실행].
- 읽기만: CX(status 0줄), B0F·FRZ_B1, 런 폴더(V-A·R-obs·B·NC3), 동결 트리, 인계 사본, Y:. CX 코드는 r1 의 TC1 사본으로만 돌렸습니다.
- 블라인드: 봉인 시드 37·59·61·67 열람 0(P0-7 은 봉인 폴더 안 파일 이름만 지나감), codex 64cf-s59/s61/s67 숫자 0, R-obs v3c3-s47 값 0(P0-7 은 이름·키 이름만). 시드는 망 접두로 적었습니다.
- 디스크 [실행 14:25]: C: 21 GB, D: 206 GB(8 GB 문턱 위). TC1 출력 1.7 GB.

## 9. 파일 (sha256)

| 파일 | sha256 |
|---|---|
| `C1D/PINS_P0_r2.sha256` | `75ead5ba4b770d7e9ed2747e37a33a3dd7fcc46fba64fd91dbea47bf19c9e11a` |
| `C1D/tools/c1_p0.py` (고친 판) / 옛 판 사본 `C1D/work/p0r2/c1_p0_r1_a7f1c479.py` | `4cd1bb16…` / `a7f1c479…` |
| `C1D/C1_VALUES.json` | `7106e2403a61755ea09165c5fcd7be54a2169d6df7c48511c3aa31d87432421d` |
| `C1D/PINS_PROBE.sha256` | `5dfb83b1e8a3a9bc2221610f0b2a473609e6d74f66bcffe87120d117c5d4886d` |
| `C1D/tools/c1_probe.py` | `9446f0287fbaea33b123321f393b682332755b66027ae04ae963611635b0e799` |
| `C1D/C1_PROBE_RESULTS.json` | `5b0bcfb05246cc7099929c03b806ba4cb03a5cbc39c5e9de3bd0dcbde80a0b5a` |
| `TC1/out/probe/HALT.json` | LOG 14:13 항목 |
| P0 결과 `TC1/out/p0/p0_{3,4,5,6,7,8,9,10,11,13}/result.json` | §2 표 |
| 기록 `TC1/out/logs/{p0_light_2, p0_3_1, p0_5_11_1, p0_6_1, p0_789_1, probe_plant_1, probe_report_1}.txt`, `TC1/out/probe/logs/plant_robss31_t001500.txt` | — |
| r1 보고 `C1D/P0_PROBE_r1.md` | `5755da898b6f653c90dec23a50abf69664529bd72dafaca0e2ad2a97c92d91c9` |
