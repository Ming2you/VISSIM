# 인계 문서 — lcd1000 에서 제어가 무제어에 지는 이유와 다음 작업 (2026-09-07)

Codex(다른 머신)가 이어서 작업할 수 있게 09-06~07 이틀의 진행 방향·결과·발견한 문제·다음 할 일을 한 곳에 모았다.
규칙 문서는 `CLAUDE.md`(정본·함정·금지 목록). 이 문서는 그 위의 **현황**이다. 숫자는 전부 lcd1000 망·시드 13·5400 s·제어 시작 900 s·150 s 결정.

## 0. 30초 요약

- 망 `…_rampbn_qc_lcd1000.inpx` 로 바꾸자 **모든 제어 런이 무제어(8082.3)에 진다** (canon_0905 8629.0 = +547). lcd200 에서는 이겼다(7741.5 vs 7952.4 = −210).
- 두 망의 유일한 차이는 **램프미터 커넥터 8개의 차로변경거리 200→1000 m** 다(원래 x18 망이 1000, lcd200 이 09-03 의 수정판). 무제어는 lcd 에 거의 무관(+130).
- fzp 궤적으로 확정한 기구: **미터 폐쇄 → 커넥터 만차 → 1 km 사전정렬된 1차로를 따라 램프행 큐가 신호 접근로(링크 32)·줄기(링크 69)를 통째로 잠금**. lcd200 에선 큐가 커넥터 앞 200 m 에 국지화돼 안 보였다.
- 플랜트(canon·B 모두)는 이것을 못 본다: ① 램프 저수지 = 커넥터 위 차량만(`ramp_counts`), ② 링크 32 위 램프행 큐를 SC1001 **신호 접근 큐**로 오귀속(p3 상한 고정, 무효 녹색), ③ 링크 31·68·69·70 관측 0(러너 스캔 목록 293 vs 매핑 670), ④ 리더 밀도 벌점이 TTT 와 무관하게 램프를 닫음(램프큐 벌점 항상 0).
- 현재 lcd1000 최선 = **b1' 8282.2**(canon+RL+B0+METER+MF1+LG) 인데, LG 가 리더를 31/31 기각해 **리더 미터링을 끈 것**이라 실명을 고친 게 아니다. 사다리(+SAT/SAT2 → +PW25 → +B5) 진행 중.

## 1. 계보 — 헷갈리지 마라

| 이름 | 정체 |
|---|---|
| `canon_default_20260905` | 정본 물리정합 플랜트(09-01~05 승격분). **B 시리즈 아님.** `urban.ramp: {}` |
| B·B0·B3·B4·B5·RL·RS·P0 | 09-05 밤 lcd200 실험 팔(g2~g9), 전부 기각·정본 미반영. B0 = `leg_split + offramp_direct + 실측 방향분율`(깨끗한 B), B5 = `gate_onramp_queue`(게이트발 램프 movement 복원) |
| h1~h16 (09-06~07) | canon_0905 위에 METER/SAT/가격 옵션. B 키 없음 |
| b0~b4 (09-07) | canon_0905 + RL + B0 위에 누적 사다리 |
| lcd200 = `rampbn_qc.inpx` | 무제어 `nc_rampbn`/`nc_out` 7952.4 (무제어에 관해 rampbn ≡ rampbn_qc) |
| lcd1000 = `rampbn_qc_lcd1000.inpx` | 무제어 `h0_nocontrol_lcd1000` 8082.3 (= `nc_rampmax` 8082.3 정확히 일치) |

커넥터 기하(from 링크·1차로·pos → 본선): 10482 32@1029→26 · 10490 32@1331→2 · 10480 31@735→26 · 10484 31@412→24 · 10646 68@352→26 · 10681 68@117→2 · 10644 69@1740→26 · 10639 70@180→2.
링크: 32 SC1001 서측 접근(3차로 1963 m, 정지선 ~1955) · 31 SC1001_W_out(3차로 1959) · 68 SC1004_W_out(4차로 1990) · 69 SC1004 서측 줄기(4차로 1797) · 70 SC1004 W_RAMP 접근(2차로 338).

## 2. 런 결과표 (veh·h)

| 런 | 구성 | TTT | 본선/도시/램프 | 메모 |
|---|---|---|---|---|
| h0 | 무제어(native) | **8082.3** | 3769/4386/65 | 기준 |
| h1=h11 | canon_0905 | 8629.0 | 3522/4992/289 | 재런 비트 동일. R_D_W 폐쇄 19/31 → 링크 32 잠김 |
| h3 | +METER | 8469.3 | | 미터 전달함수(§4) |
| h5 | +SAT+SAT2 | 8652.1 | | 포화방출률 실측 |
| h7 | +PW25 | 8356.4 | 3940/4395/180 | canon 계열 최선. SC1001 p3 꼭짓점 30/31 |
| h8/h10 | TS / JOINT | 8725.7 / 8458.8 | | 가격 옵션 ①③ |
| **b0** | canon+RL+B0 | **8313.4** | 3751/4524/198 | "기존 B0". SC1001 꼭짓점 0/31 |
| b1(구) | +METER | 8361.6 | 3715/4544/252 | +48: 리더 TTT-악화 폐쇄가 METER 로 실현 + 한쪽 커넥터 폐쇄 |
| **b1'** | +METER+MF1+LG | **8282.2** | 3984/4329/124 | LG 가 리더 31/31 기각 = 미터링 OFF. 도시 −195·램프 −74·본선 +233 |
| b2 | +SAT+SAT2 | 8451.5 | | b1' 대비 **+169**. SAT 는 링크 32 를 못 건드리고 회랑(426)만 흔듦 — B 위에서 SAT/SAT2 는 해롭다 |
| **b3** | +PW25 | **8007.7** | 3810/4254/97 | **lcd1000 첫 무제어 승(−74.6)**. b2 대비 −444. 단 SC1001·SC1004 31/31 꼭짓점(22/23/71/23)·SC1002 25/21/26/66 고정 = 사실상 정적 계획 + 램프 개방. 링크 32 적분 384→219, 420 은 37→179 재발 |
| b4 | +B5 | (진행 중 09-07 14:19~) | | 로그 `evaluation/runs/chain_lcd1000_20260906.log` |

lcd200 참고: g1 canon_0905 7741.5(−210) 의 이득은 **고속도로 −408**(SC1001 EW 직진 p3 69~75 → off-ramp 10481 역류 제거 ≈−400, R_F_E 미터링 ≈−240) − 도시 손실 ≈+300(링크 420 +187). 회랑 신호 최적화 이득은 +32 로 없다.

## 3. fzp 진단 — 무엇이 생기고 무엇을 못 보나

산출물: `outputs/lcd_fzp_analysis_20260907/{A,B,C,D}` (CSV/PNG/py; parquet 는 gitignore. fzp 원본은 `evaluation/runs/<런>/vissim_eval/*.fzp` 5 s 궤적 ~310 MB, 러너 기본 출력). 4 agent 보고 전문: `outputs/lcd_fzp_analysis_20260907/REPORT_fzp_agents_20260907.md`.

**h11 손실 +545 분해**: ① 링크 420(SC105 접근) +201 — lcd200 g1 에도 +187, **lcd 무관한 canon_0905 결함**(SC1001 p3 72~75 과녹색이 30→420 으로 밀어넣고 SC105 p1 34~46 이 못 받음; b0 는 +1.8) ② R_D_W 폐쇄 역류 +268(10482 +108·32 +97·10480 +22·31 +23·10483 +18) ③ R_F_E 폐쇄 역류 +208(69 +77·10639 +40·10681 +30·70 +24·10638 +24·10637 +13). 이득 26 −148·2 −92·10481 −122.
**b0 +229** = ③(+240) + R_D_W 커넥터 +55. ①② 없음(R_D_W 를 2700 에 재개방).

**기구**: R_D_W 0 → 10482(2차로 381 m) 116~121 대 만차 → 링크 32 L1 정지큐 꼬리 1270→870(2100)→461→205→**4 m**(4350~) → 끝엔 pos<1029 에 정지 455 대(L1 160+L2/L3 295, 전부 램프행/미완주) → 3차로 잠김, 신호행이 정지선에 못 감, 경계 유입 39 대 미삽입. R_F_E 0 → 10639(47) 만차 → 70 L1 만차 → 10637 → 69 L1 157 대(꼬리 750 m = 1740−1000). 69 큐 주성분은 **열려 있던 R_F_W(10644)행** 차량 → 10644 진입 158→17/900 s 붕괴 → FW_W 오프램프 10638 만차 → 본선 26 6000~6500 m 97→33 km/h.

**lnChgDist 직접 효과**: 램프행 L1 점유율 링크 32 0~1000 m 0.32→0.55, 69 800~1500 m 0.27→0.79~0.99, 68 0~200 m 0.35→0.71~0.95. 무제어 체류시간 불변(무해). 큐 크기는 폐쇄 지속시간과 뒤섞여 단독 분리 못 함 → **결정 실험: h11 의 action 시계열을 lcd200 망에 그대로 재생**.
**lcd200 에서 없었던 이유**: 램프행이 커넥터 46 m 상류에서야 L1 에 붙어 큐가 커넥터 저장고(≈118)+L1 133 m 에 흡수, 상류 L2/L3 정지 0. 차량 제거(diffusion)는 4런 460~540 대로 같고 95% 가 도시 정지선(329·310·66) — 가려진 게 아니다. 폐쇄도 짧았다(R_D_W 0 11/31 vs 19/31, 관측 본선 속도 30~38 vs 22~23 km/h).

**플랜트 실명 (canon·B 동일, b0 스냅샷으로 재확인)**
1. `ramp_counts R_*` == 커넥터 재차(10482+10480 / 10681+10639) 와 전 결정 일치, 상한 153. 링크 32/69 위 역류(진짜 램프큐 262 vs 모형 140)는 저수지에 없다 → `leader_ramp_queue_penalty` 93결정 전부 0. 어댑터 `ramp_link_to_queues` 는 커넥터 8개만 등재.
2. 링크 32 는 관측되지만(`link_counts` 300~531, 정지 480, 큐꼬리 4 m) `link_to_movements[32]` 14개가 전부 W_RAMP 신호 접근 → SC1001 접근 저류/도착 seed → p3 72~75 상한 26/31(램프행은 정지선을 안 만나 무효). 모형 경로: in_SC1001_W 램프 몫 16.7%(p3 경유) vs 플랜트 88%(신호 상류 이탈, R_D_W 공급의 78% 가 10482). `vehicle_records` 에 차로 정보(L1 73·L2 78·L3 19 정지)가 있는데 귀속에 안 쓴다.
3. 러너 스캔 `core17legs4b_20260819` 293 링크 vs 어댑터 매핑 `…blindfix20260905b` observable 670 → 31·68·69·70 등 377 링크 `link_counts=None`.
4. 리더: `leader_density_penalty`(h11 중앙 457·stress 0.99 vs g1 314·0.62) 가 N_UF 를 1440 바닥에 붙임. 리더 롤아웃 TTT 이득은 어느 결정에서도 ±1 veh·h(≤0.05%). FW_E 링크 2 상류 잼(~460 대)은 R_F_E 개폐 무관(h0=h11)인데 모형은 램프 유입 혼잡으로 읽는다.
5. B(leg_split)는 폐쇄 비용을 **W_out(31/68) 재고**에 실는다 — 자리가 틀리다(실제는 32/69). B0 는 게이트발 램프 movement 18개를 신호 쪽으로 되접어(`folded_movements=18`) 신호 전 이탈 88% 를 canon 보다 더 못 본다. B5 만 게이트발 onW/onE 를 무신호 movement 로 복원(`kept=3`).

## 4. 09-06~07 에 넣은 수정 (전부 config 키 게이트, 없으면 비트 동일)

| 태그 | config 키 | 내용 | 결과 |
|---|---|---|---|
| METER | `actuation.real_world_ramp_metering.allocation: measured_table` 등 | 미터 액추에이션 전달함수. 종전 균등분할+round(10·rate/900) 은 plant 에서 {0, ≥600~1000, 열림} 3단계(요청 300 → 실측 ~770, plant/요청 중앙 1.79). 실측표 n(g)×차로×360 으로 커넥터 green 배정, 실현값 되쓰기 `real_world_ramp_meter_write_back` | canon −160(h3). B 위 +48(b1) → 원인 = 리더 폐쇄가 진짜가 됨 |
| **MF1** | `…close_penalty_mode: "demand"` | 요청 < 두 커넥터 최소치 합(767)이면 2차로 10482(수요 755)를 닫고 1차로에 몰아주던 것 수정(폐쇄 벌점 = 커넥터 수요). b1 결정 재현 31/31, 변경 13결정 | b1' 에 포함 |
| SAT/SAT2 | `urban.capacity.measured/seed=sustained/…` | 포화방출률: 종전 206.5/차로(흐름을 용량으로 오인) → lcd1000 무제어 차량기록의 큐 창 지속 방류 씨앗 + 이탈계수 온라인 EWMA. **internal movement 만** — 링크 32(boundary_in) 는 413 그대로 | h5 +183(단독) → PW25 와 함께 h7 |
| SAT3 | `lane_group_kinds: [internal, boundary_in, boundary_out]` | 링크 32/66 포함 | h6 8892.7 최악(32 방류↑→램프 유입↑→미터 폐쇄) |
| PW25 | `phase_price.weight: 0.25` | 현시가격 세금 1/4(가격 = −0.75·ΔL/δ 이고 ΔG≡0 이라 정련이 얼어붙음) | h7 −296 |
| QB | `urban.queue.attribution: beta` | 정지선 큐 β 귀속. **B5 와 충돌**(무신호 램프 movement 로 30~50% 새 나감) | h12 미완주 |
| CAP/V2/LG/JOINT/TS/OWN/PG/IG/H9 | 각 FRAG 참조 | CAP 추정상한·V2 씨앗 위생·LG 가드 0.002·JOINT 회랑 결합·TS 2단 정련 등 | JOINT 8458.8, TS 8725.7, 나머지 미검/중립 |
| RL | `phase_price.ramp_local_model: ramp_aware` | has_ramps 신호 정련 국소항이 drain≡0 → 램프 인지 롤아웃. B 의 전제 | 단독 +112(lcd200) |
| B0 | `urban.ramp.leg_split/offramp_direct` + `boundary_out.ramp_split_json` | W_out 재고 τ 분할 주입 + off-ramp 직행 착지 유입시점 분할 | b0 8313.4 |
| B5 수정 | 어댑터 `_apply_gate_onramp_beta` | origin 합 상한 0.85(kept 둘이면 형제 β −0.22 음수) | b4 에서 첫 사용 |
| LG | `mpc.stackelberg_fallback_guard_min_ttt_gain_frac: 0.002` | 리더가 폴백보다 0.2% 이상 좋아야 채택 | **리더 이득 ≤0.05% 라 항상 기각 = 리더 미터링 OFF** |

FRAG 정의: `scripts/chain_lcd1000_20260906.py` (`FRAG` dict, `make_config(tags)`, `run`, `ttt_of`). 사다리: `scripts/chain_b_ladder_20260907.py` + `scripts/run_b_ladder_20260907.sh`. 비교표: `scripts/compare_b_ladder_20260907.py`, `scripts/compare_options_20260907.py`. 기전 판정: `scripts/chain_lcd1000_h{2,3,4,5}_20260906.py`.
어댑터 수정 전 상태는 git 이력 `521625d`(09-06 아침).

## 5. 도구

- **오프라인 결정 재현기**(실런과 소수점까지 같음, ~3 분/결정): `scripts/offline_harness_20260904.py` 의 `OH.build(qb, TrafficState, tuning_path, state_path, prev_action_path)` → `qb.build_priced_wu_link_controller(cfg, tun)`; `controller.price_parallel_workers = 0` 필수(부트스트랩 없음). 예시 스크립트: `outputs/lcd_fzp_analysis_20260907/D/*.py`.
- fzp 파싱: 세미콜론, 헤더 `$VEHICLE:SIMSEC;NO;LANE\LINK\NO;LANE\INDEX;POS;POSLAT;SPEED;TMINNETTOT;DELAYTM`, pandas chunksize 2e6. TTT = 행수×5 s/3600 (보고값과 ±8 일치). 램프행 판정 = 다음 링크가 커넥터. `TMINNETTOT` 는 매 행 누적이라 완주 판정에 못 쓴다.
- 러너·VISSIM 은 **한 대(이 워크스테이션)만** 돈다. Codex 쪽은 모형/코드/오프라인 검증을 맡고 실런은 여기서 순차로 한다는 분담을 권한다(VISSIM 동시 실행 불가, 어댑터는 런 중 편집 금지 — 컨트롤러가 결정마다 재-import).

## 6. 다음 작업 (우선순위)

1. **저수지 관측에 링크 32/69 의 L1·L2 램프행 역류를 넣기** — `vehicle_records` 의 차로로 판정(램프행 ≈ L1/L2 정지, pos < 커넥터). 어댑터 `ramp_link_to_queues`(커넥터 8개) 확장 또는 별도 역류 항. 상한 153 을 넘는 진짜 큐(262+)가 `ramp_space=0` 과 far 램프항에 실려야 폐쇄 비용이 보인다. 이중계상 주의(같은 차량을 SC1001 접근 큐와 램프 큐 둘에 넣지 말 것).
2. **링크 32 램프행(88%)을 SC1001 접근 큐에서 제외** — `link_to_movements[32]` 귀속에 차로 필터, 또는 B5 의 게이트발 movement 에 L1/L2 정지 큐를 직접 귀속. QB 와 함께 쓰려면 kind 필터 필요.
3. **리더 밀도 벌점 vs TTT** — 벌점이 TTT-악화 후보를 채택시킨다. LG 0.002 는 리더를 통째로 죽이므로 대안: `min_ttt_gain_frac` 대신 `ttt_worse` 여유폭(현재 max(1.0, 0.1%))을 0 으로, 또는 밀도 벌점 가중 축소. `vendor/NumSim-mine/src/controllers/stackelberg_mpc.py:1650~1730`.
4. **canon_0905 의 SC1001 p3 과녹색 → 링크 420 +200** (lcd 무관, g1·h11 공통, b0 는 없음 = RL 이 고침). SC105 p1 이 못 받는 구조 확인.
5. **결정 실험**: h11 의 `action_*.json` 미터·녹색 시계열을 lcd200 망에 재생(러너에 고정 계획 재생 옵션이 있는지 확인) → lnChgDist 단독 효과 분리.
6. 관측 채널: 러너 스캔 목록을 매핑 observable 670 으로 확장(31·68·69·70 포함). 비용 5 초 스캔.
7. 미해결: FW_E 링크 2 0~2000 m 잼(~460 대, R_F_E 무관, 무제어 +138)의 기구 — off-ramp 10643/10682 + 합류 10639/10681 위빙 구간 의심.
8. SC1004_W 게이트 키 부재로 B5 의 `SC1004_W_to_onE` β 가 늘 폴백 0.083(진단 `gate_onramp_beta_fallback_*`). `urban.tau.length_cap` 을 켜면 spawn 워커만 무상한 tau(`_CFG_SWITCHES` 유실) — 이번 사다리는 false.

## 7. 로그·산출물 위치

- 체인 로그: `evaluation/runs/chain_lcd1000_20260906.log` (h·b 전부, 기전 판정 포함), `evaluation/runs/chain_gated_20260905.log` (lcd200 g 시리즈)
- 런 디렉터리(gitignore): `evaluation/runs/<런>/decisions_<런>/{state,action}_<t>.json`, `vissim_eval/*.fzp`
- 격리: `evaluation/runs/_killed_b2_rl_b0_meter_sat_sat2_lcd1000_x18_20260907`(23결정 중단), `g2_B3fail_x18_20260905`
- fzp 진단: `outputs/lcd_fzp_analysis_20260907/` (A 손실 지도·B lcd200 대조·C 무제어/제거·D 플랜트 실명)
- 씨앗 산출물: `outputs/lane_group_sustained_h0_20260906{,_v2}.json`, `outputs/link_queue_class_h0_20260906.json`

## 8. Ver2 망 채택 (2026-09-07 오후, 진행 중)

사용자가 램프 커넥터별 전용 상류 링크로 망을 쪼갬(`network/real_world_gaepo_modi/modi_eval_userfix Ver2.inpx`): 32→32·129·127(127 = SC1001 정지선 접근), 31→31·124·125, 68→68·121·123, 70→70·126, 69 단축(1746 m), 2→2·119(3차로), 26→26(3차로)·120, 24 3차로. 검토 결과 경로·신호두·큐카운터·수요 전부 정합(끊긴 경로 기준과 동일, relFlow 보존). 4차로 DSD 5개(70·74·78·82·86) 는 차로 삭제로 사라짐(의도).
**동시 실행 실패**: 두 번째 VISSIM 인스턴스는 뷰어 모드(ContrByCOM 되읽기 빈 값·capture mismatch) — 라이선스 1인스턴스. 런은 순차만.

생성물(전부 새 경로, 정본 파일 무수정):
- `evaluation/real_world_modi_control_ver2_20260907/` — `control_mapping_ver2.json`(체인 74·10699·2·10613·119·10702·24 / 26·10771·120, 미터 from_link 갱신), `real_world_modi_control_config_ver2.vbs`(정본 20260825 config 틀 + 본선/램프/관측 키 교체, 관측 링크 680 = blindfix 670+새 링크, VSL DSD 66) + `_sgplan.vbs`, `detector_local_mapping_ver2_20260907.json`(32 의 movement 14개→127, 새 링크 origin, off-ramp 착지 갱신, **`ramp_spillback_links`** 표), `freeway_mainline_chain_ver2.csv`, `freeway_control_manifest_ver2.csv`
- `outputs/urban_player_territory_v2_20260907.json`(decision_log `ver2-split-20260907`), `pn_boundary_turns_v2_20260907.json`(306 회전, 10482/10490/10639 는 신호 전 이탈이라 external 비통제), `pn_boundary_map_v2`, `urban_storage_capacity_ver2`(80키 v1 과 동일), `movement_connector_map_ver2`, `far_measurement_links_ver2.csv`, `urban_input_gate_map_ver2.csv`(mapped 21 동일)
- `evaluation/configs/canon_ver2_20260907.json`(canon_0905 + 매핑 v2) · 러너 `-NoGlobalKill` 스위치 · 생성기 env `RW_FREEWAY_CHAIN_CSV`
- **세그먼트별 차로(15:20 구현)**: 생성기가 세그먼트 중점이 속한 체인 링크의 차로수를 `freeway_model_links[*].segment_lanes`(FW_E 4,4,4,4,4,3,3,3 / FW_W 3,3,3,4,4,4,4,4)와 `segments[].lanes` 에 기록. 어댑터 `install_freeway_segment_lanes`(config `freeway.segment_lanes: "mapping"`, 패치 `scripts/apply_seglanes_patch_20260907.py`)가 `cfg.network.freeway_segment_lanes` 로 싣고 세그먼트 파서가 밀도 = count/(length·lanes_i) 로 재계산, `state.freeway_effective_lanes` 가 세그먼트별 배열이 된다(METANET·팔로워·리더가 이미 그 배열을 읽음). 합류 세그먼트별 파라미터 실험용 훅 `freeway_model_links[*].segment_params` → `cfg.network.freeway_segment_params`(소비처는 아직 없음). 오프라인 검증 h11 t=3600: FW_W 밀도 S0 59.9→79.9(×4/3), 차량 수 보존 985=985. VBS 의 bottleneck CSV 밀도는 아직 단일값(진단 전용). 정본 적용은 chain_ver2 시작 시 자동.

**스필백 제약(WP6, 오프라인 검증 완료·정본 적용은 런 사이 창에서 자동)**: `scratchpad/apply_spill_patch.py` → `urban.ramp.spillback_obs`(검지 링크 정지 차량을 저수지 큐에 합산, 요약 `ramp_spillback`) + `actuation.real_world_ramp_metering.spillback_guard {enabled, spill_threshold_veh 8, floor_vph 1800}`(문턱 초과 시 rate 강제 개방, write-back 앞). b0 t=3600 검증: R_F_W spill 49·R_F_E 28 → R_F_E 0→1800 강제. FRAG `SPILL`.

**Ver2 ablation(= B 수정 재검토)**: `scripts/chain_ver2_20260907.py` — a0 canon_ver2 → a1 +SPILL → a2 +RL → a3 +METER+MF1 → a4 +PW25 → a5 +B5 → a6 +B0 → **v0 무제어(Ver2)** → 씨앗 재생성(`derive_lane_group_sustained_ver2_20260907.py`, `derive_link_queue_class_ver2_20260907.py`; Ver2 는 정지선이 32→127 라 lcd1000 씨앗을 못 씀) → a7 +SATV2(SAT+SAT2, Ver2 씨앗) → a8 +SAT3(boundary_in 포함 = 127 접근로에 실측 용량). LG(리더 OFF)·QB(B5 충돌) 제외. 실행 순서가 이렇게 된 이유: Ver2 inpx 의 정적 경로 3건(1131-1/1131-3/1132-3) 이 GUI 분할로 미완성 → v0 가 시작 못 하고 죽어 대기 드라이버가 사다리로 넘어감; 경로 보완 뒤 a0 부터 정상. 드라이버: `scripts/run_after_ladder_v0_20260907.sh` → `run_after_v0_sat_20260907.sh`. 현시가격 대안은 사용자가 구상 중 — SAT 결과까지 보고 판단.

**v0 Ver2 무제어 기준선 = 7660.2** (16:17): 본선 3338 / 도시 4379 / 램프 71 — lcd1000 h0 8082.3(3769/4386/65) 대비 본선 −431(3차로 병목·10613 lnChgDist·경로 보완 효과), 도시 동일. Ver2 런은 이 값과만 비교한다. Ver2 씨앗(`outputs/lane_group_sustained_v0_ver2_20260907_v2.json`, `outputs/link_queue_class_v0_ver2_20260907.json`) 생성 완료 → 사다리 재개는 `python scripts/chain_ver2_20260907.py 0` 한 줄(어댑터 패치는 이미 적용, config v2 계약 상수 66 으로 수정됨). 사용자 지시로 사다리는 보류 중.
 결과는 `evaluation/runs/chain_lcd1000_20260906.log` 의 `TTT a*(`·`TTT v0` 줄.
