---
name: vissim-phase-price-backpressure
description: "현시가격 대체안 = 관측 역압(Vickrey 한계 외부효과) 가격 (2026-09-06). 정의·게이트·오프라인 검증에서 배운 세 가지 함정(램프 저수지 항, s_m 상한, 불감대)과 남은 문제"
metadata: 
  node_type: memory
  type: project
  originSessionId: ab16ebe2-114b-4182-9877-9977f80eb5f9
  modified: 2026-09-06T03:42:45.113Z
---

# 관측 역압 현시가격 (`phase_price.mode: "observed_backpressure"`, 2026-09-06)

**왜 바꿨나.** 롤아웃 현시가격 `[(ΔG) − (ΔL_phased)]/δ·(n−1)/n` 은 지평 3스텝 누적 TTT 가 망 내부 이동에 정확히 무감각(SC105: ΔG=+0.0000, p1 28~70 전부 G 1036.681)이라 `price ≡ −0.75·ΔL` = 국소 이득에 대한 세금. 큐 큰 현시 양수, 큐 0 현시 음수(보상). 롤아웃 '남들 지연' 변형도 모형 용량(206.5/차로) 탓에 하류가 가짜 포화로 보여 +0.023. 사용자 지시: 가격은 켜 둔 채 다른 방식으로.

**정의** (어댑터 `install_observed_backpressure_price` → `cfg.network.observed_backpressure_prices`, `install_observed_backpressure_controller` 가 `_refresh_phase_prices` 를 대체, 롤아웃 0회 → 결정 ~200→150 s):
- price[S][p] = w · Σ_{m∈p} s_m · (Σ_d share_d·e_d − r·e_o),  e_ℓ = λ_ℓ·T_ℓ/μ_ℓ, T_ℓ = min(n_ℓ/μ_ℓ, H)
- n_ℓ = plant 링크 재차, μ_ℓ/λ_ℓ = 직전 state 3개의 차량 레코드 차분(링크 이탈/유입)/시간, H = 지평 0.125 h, μ 바닥 48.
- s_m = β_m × 접근 차로수(커넥터 지도 turn lanes 합) × 차로당 방류/3600. 기본 `per_lane_veh_h_model 206.5`(국소 모형과 같은 척도 → w=1 자연). 실측 1300 이면 ×6.3.
- 하류 링크 = `movement_connector_map_20260824.json` 의 approach turn(dest_signal 일치) to_link; origin = 그 approach 의 from_link.
- 클립 ±max_price(1.0), 불감대 `min_abs_price 0.005`, `relief_weight r=1`, `ramp_reservoir false`.
- 첫 결정(직전 state 없음)은 롤아웃 가격으로 폴백(diag `observed_backpressure_fallback_rollout`).
- 하네스 `offline_harness_20260904.build` 에도 설치 호출 추가. 검증 스크립트 scratchpad `bp_validate.py <t> <run> <cfg>`.

**검증에서 배운 함정 셋 (h1 상태 t=1800/3600).**
1. 하류 항만 있으면 SC1001 p3(링크 32 서비스) 72→24: 자기 링크 해소 항 e_o 가 필요(옮김의 외부효과 = e_d − e_o, max-pressure 구조).
2. 램프 저수지 항(n=램프큐, μ=미터율)은 리더가 미터를 0 으로 잠글 때 e→상한이 되어 W 접근 전체를 잠근다(SC1001 p3 69→21, p1 77). 램프 결합은 리더(N_UF*·미터) 몫 → `ramp_reservoir: false`. s_m 도 movement 용량 상한(무신호 게이트 1800)이 아니라 β×차로로.
3. 국소비용이 평평해(용량 206/차로, W 정지선 큐 17) ±0.004 의 가격 차이로도 정련이 48 s 를 옮긴다 → 불감대 0.005.
통과 후: t=1800 SC105 34→64, SC1001 23/21/72/21 유지; t=3600 SC105 46→70, SC1001 23/20/75/20, SC1004 p3 유지.

**남은 문제.** 한 홉만 봄(SC5·SC101 이 포화 회랑으로 계속 밀어 넣음: 첫 하류 링크만 보고, 양쪽 T 가 H 에 걸리면 λ/μ 비로만 갈림) / e_o 와 L 의 이중계상 경계 / 150 s 계수 잡음 / L 의 용량 척도 자체(206/차로)가 평평함의 근본 원인 / 리더의 미터 폐쇄는 별도(h3 = +`mpc.stackelberg_fallback_guard_min_ttt_gain_frac 0.002`, config `h_bp_lg_20260906`).

**런.** h2 = `h_bp_20260906` (lcd1000, 12:16 발사, `scripts/chain_lcd1000_h2_20260906.py`, 로그 `chain_lcd1000_20260906.log`). 비교 기준 h0 8082.3 / h1 8629.0. h2 라이브 t=1050 에 p1=70 꼭짓점(SC105·SC1001·SC5): 런 초반 이탈이 적은 걸 저용량으로 오독(μ 바닥 48 → e 폭발). 관련: [[vissim-env-structural-20260906]], [[vissim-phase-price-surrogate-leak]], [[vissim-flat-local-cost-vertex]].

## 망 전체 압력(network pressure) 검토·모듈 (2026-09-06 오후, 사용자 제안 "ψ = e + Aψ, π = s(ψ_d − ψ_o)")
- **구조 결함**: ψ_o = e_o + Σ A ψ_d 라 Σ P ψ_d − ψ_o = −e_o + Σ P(1−γ)ψ_d → 자기 링크 항으로 퇴화(전망 항은 τ/τ_c ≈ 0.1~0.2 배). 원점은 국소 e_o 로 두더라도 **합산 전파는 하류를 홉 수만큼 과대**(SC5 p3 +0.68, SC101 p3 +0.94, SC105 p1 +0.10 → 전부 보류).
- **수정본** `evaluation/controllers/network_pressure.py` (+ 진단 `scripts/network_pressure_diag_20260906.py`, CSV `netpressure_<t>_*.csv`): 잠재 = 볼록결합 평균 ψ̄=(1−γr)e+γPψ̄ (척도 = e, ρ ≤ max γ), 원점은 후방 잠재 ψ↑(저장 장벽 켜진 링크만 전파) → π = s_eff(ψ̄↓_d − ψ↑_o). e = T + κB (T=min(n/μ̂,0.5h), B=저장 장벽 θ 0.5), μ̂ = n<8 이면 녹색한계 용량 gcap 아니면 실측 이탈, s_eff = 1300·lanes·min(1,q/5)·(1−B_d)/3600, q = max(모형 큐, β·n_o). 램프 노드 포함하되 부담 = κ·B_r 만(T_r 은 리더 미터율 몫; 미터 0 증폭 방지). boundary_in 레그(in_SC1001_W = 링크 32) 포함 필수 — 빠뜨리면 SC1001 p3 가 0 이 된다.
- **진단(h1 t=3600, 물리 단위, L 통화 ×0.159)**: SC105 p1 −0.225 / SC1001 p3 −0.187 / SC1002 p3·p4 −0.55·−0.18 / SC5 p3 +0.002 / SC101 p3 −0.016 (t=1800 SC101 p3 +0.079 회랑 적재 중 보류). ρ(A↓)=0.64, 30회 반복, 1 s 미만. 외부효과 변형(자기 항 삭제, 상류 해소는 장벽 게이트)은 모형 N 이 커서 장벽이 안 켜져 항상 양수 → 불가(N_eff 보정 선행).
- **성격**: heuristic 압력(max-pressure q_o − ΣPq_d 의 지연·저장·할인전망 변형). marginal-externality price 아님. 논문 표기 "observed network pressure".
- **D/A 팔**: `h_np_20260906.json`(full_network_pressure, avg, ramp storage, local_scale, 불감대 0.005) · `h_p0_20260906.json`(weight 0). 연결 스크립트 scratchpad `apply_np_wiring.py`(h2 종료 후 적용), 드라이버 `scripts/chain_lcd1000_np_20260906.py`, 지표 `scripts/stage6_metrics_20260906.py`.
