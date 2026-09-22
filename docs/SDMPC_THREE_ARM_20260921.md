> **2026-09-21 11:15 사용자 중단:** NC가 매초 전체 차량을 수집해 느리다고 사용자가 VISSIM을 종료했다. 확인 시 VISSIM/cscript/Python 감독·워커 모두 없었다. NC는1432초 관측까지이며9000초 미완료, SDMPC900초 전체 결정도 미완료다. pipeline_v6/status.json의 실행 중 표시는 종료 전 값이다. STOP_REQUESTED를 두었고 sdmpc-9000 자동화는 PAUSED다. 자동 재시작하지 않는다. 상세는 diagnostics/lane_storage_recovery_20260921/user_stop_20260921.json. 사용자는150초 수집을 원하며 이는 이전 인계의1초 관측 유지보다 우선한다. 다음 작업은150초 VISSIM 상태 수집과1초 plant 내부 적분을 분리하고, 1초 이력 의존 추정기를 명시적으로 대체·검증하는 것이다.
> **최신 우선순위:** 사용자는 이후 차량 관측을5초로 되돌리도록 했고, SDMPC 미분 방식 수정을 먼저 요청했다. 현재 `sdmpc-tangent-20260921`에서 연속 예측/직접 민감도 전파만 오프라인 검증한다. VISSIM과9000초 실험은 재시작하지 않는다. 상세는 `docs/SDMPC_CONTINUOUS_DERIVATIVES_20260921.md`; 위150초 수집 방향은 이후5초 요청으로 대체되었다.

# 2026-09-21 재고 차감 재현·복구 진행

현재 수정/다음 CL 루트: `C:/Users/TRLAB/Documents/ChatGPT/VISSIM/.worktrees/lane-inventory-20260921`.
브랜치 `codex/lane-inventory-20260921`; 커밋/푸시하지 않았다.
NC는 이전 `lane-storage-20260921/evaluation/runs/three_arm_nc9000_s13_v2`에서 계속 실행한다. 런처 PID19696, cscript9904, VISSIM4752를 재확인하며 새 NC를 시작하지 않는다.
이전 pipeline_v5 감독은900초 SDMPC 후보 계산 실패로 종료했다. 기존632개 고정 소스는 바꾸지 않았음을 확인했다.

새 감독 준비: `diagnostics/lane_storage_recovery_20260921/run_three_arm_v6.py pipeline_v6`.
2026-09-21 10:58 KST 감독v6를 시작했다. 상태는 `diagnostics/lane_storage_recovery_20260921/pipeline_v6/status.json`;637개 소스 고정 `sources_v6.json`. 기존 NC를 인계했으며 전체 SDMPC900초 검증 자식PID20044가 실행 중이다. PID는 다음 확인 때 실제 프로세스와 다시 대조한다. 실패 후보 단일450초 재현은184.637322초에 완료했다. 새 CL9000은 아직 시작하지 않았다.

## 이번 실패와 최소 수정

- 기존 전체 SDMPC900초 검증은4049.350877초 후 실패했다. 실패 결과를 통과로 바꾸지 않았다.
- 역순 후보 재현으로 원래 stencil index132, `FW_W__seg10` VSL 후보를 특정했다. action SHA256 `f23c060bf122533951624f95323e9f78207b0cbcf681f7f70bfe142d516c649b`.
- 예측927초 `SC1004_W_to_N_SC1003`에서 기존 mirror재고0.07671221302989878과 FIFO재고0.07671221302989883 사이 미세 차이가 있었다. 세 차로의 수락량0.035884276453469935,0.035884276453469935,0.004943660122958958을 순서대로 차감하면서 최종잔차-4.85722573273506e-17이 마지막 작은 피연산자의16ULP범위를 넘어 오류가 났다.
- 같은 movement의 실제 accepted receipts를 `math.fsum`으로 먼저 합한 후 한 번 차감한다. 기존16ULP 및 실질적 초과 차감 거부를 그대로 유지한다. allocator, FIFO 순서, route labels, native 명령, FD/anticipation/용량 파라미터는 변경하지 않는다.
- 29개 질량·초기화·경계 회귀 검사와 `verify_parameters.py` PASS. 실제 실패값 및 실질적 초과 차감 거부 회귀 검사를 추가했다.
- `inventory_repro_v1/status.json`, `inventory_repro_v2/status.json`은 실패 재현 기록이다. `inventory_fixed_v1/status.json`은 같은 후보450초 응답 재현이며 **전체 SDMPC나 native 적용 증거가 아니다**.
- 전체 검증에서는 여전히900초 및2400초 저장 상태, 짧은 실제 적용,9000초 CL의 모든 문턱을 통과해야 한다.

## 후속 실행 순서

1. 수정 후보450초 재현 완료 확인 → 새 소스 `sources_v6.json` 고정 → 감독v6 시작.
2. 현재 NC를 인계 관측하면서 수정본 전체 SDMPC900초 검증, NC2400초 관측 후 전체 SDMPC2400초 검증.
3. NC9000 완전성/실제 실행 증거 확인 → 새 lane plant CL1000 → CL9000.
4. 기존 METANET900/2400초 검증 → CL1000 → CL9000.
5. compare_v6.py는 NC를 **이전 lane-storage 루트**, 두 CL을 **새 lane-inventory 루트**에서 읽어 동일 준비 조건과9000초 FZP를 검증한다.

예측 워커8개, 결정 계산시간 제한 없음. 실제 VISSIM은 언제나 한 대씩 순차 실행한다. 실패한 감독을 중복 시작하거나 NC가 살아 있는 상태에서 runtime소스를 변경하지 않는다.

---

아래는 이전 복구 단계의 기록이다. 현재 단계와 충돌하면 위 내용을 따른다.

# SDMPC9000 세 조건 비교 — 저장·초기화 오류 복구

## 현재 실행 위치

현재 루트: `C:/Users/TRLAB/Documents/ChatGPT/VISSIM/.worktrees/lane-storage-20260921`
브랜치: `codex/lane-storage-20260921`. 아직 커밋/푸시하지 않았다.
현재 감독: `diagnostics/lane_storage_recovery_20260921/run_three_arm.py pipeline_v5`
상태: `diagnostics/lane_storage_recovery_20260921/pipeline_v5/status.json`
고정 소스: `diagnostics/lane_storage_recovery_20260921/sources_v5.json`.
2026-09-21 09:05 감독을 시작했고 NC가 실제1초 이후로 진행함과 첫 no-control 결정 성공을 확인했다. 감독 PID26876, NC 런처19696, cscript9904, VISSIM4752,900초 SDMPC 검증5468. 워커는8개 설정이며 초기 held 응답 뒤 병렬 후보 단계에서 모두 활성화된다.632개 소스/입력을 고정했다. PID와 실제 상태는 매 확인 때 대조하고 중복 시작하지 않는다.

## 승인 범위와 순서

동일한 최신 native 망·원래 수요·seed13에서 NC9000, 최신 lane plant SDMPC9000, 기존 METANET 격자에 최신 계수만 옮긴 SDMPC9000을 비교한다. 계산 워커8개, 결정 계산시간 제한 없음. Native VISSIM은 항상 하나씩 순차 실행한다.

관측용 NC2850이1950초에서 실패했으므로 새 NC9000을 관측 수집과 비교 baseline으로 함께 사용한다. 중간 NC2850 재실행을 줄이기 위한 순서 변경이며 세 비교 조건은 동일하다.

1. `three_arm_nc9000_s13_v2`를 시작한다. 동시에 이전 NC의 유효한900초 저장 상태에서 새 plant 전체 SDMPC 검증 `sdmpc_state900_v5`를 수행한다.
2. 새 NC의2400초 상태/실제 명령 수집 후 전체 SDMPC 검증 `sdmpc_state2400_v5`를 수행한다.
3. NC9000 완료 및 실제 native 실행 증거 확인 후 `lane_sdmpc_cl1000_s13_v3` → `lane_sdmpc_cl9000_s13_v3`.
4. 기존 METANET의900/2400초 SDMPC 검증 → `metanet_params_cl1000_s13_v2` → `metanet_params_cl9000_s13_v2`.
5. `diagnostics/metanet_compare_20260921/compare_v5.py`로 세 조건을 비교한다. 최종 출력은 `pipeline_v5/comparison/REPORT.md`, `comparison.json`, `comparison.csv`.

감독이 실패해도 별도로 시작한 NC는 관측 수집을 계속할 수 있다. `nc_child_pid`, native 프로세스, watchdog을 반드시 확인한 뒤 다음 행동을 정한다. `STOP_REQUESTED`는 다음 단계 시작을 막으며 진행 중 자식을 즉시 종료하지 않는다.

## 이번에 확인한 실패와 복구

과거 작업 폴더 `metanet-params`의 pipeline_v3/queue_v4는 종료했고, 원래 `sdmpc-lane-plant-20260921`의 `lane_native_nc2850_s13_v3`도1950초에서 실패 종료했다. 이 실패들을 통과로 바꾸거나 소스를 수정하지 않았다.

- 새 plant의150초 상태 SDMPC는5640.596623초(약94분)에 계산을 완료했으나, 보고서의 NumPy float64 저장을 지원하지 못해 종료코드1로 실패했다. 자체 `solution.pickle`의 SHA256 `8bfa76b8591535bbf0adda5f85110d526146f7a08ed1a4f65bbfdde474351b15`와 원래 소스 해시, 최종 action token을 확인해 재계산 없이 별도 복구했다. 원래 실패 결과는 그대로다.
- 복구 보고서: `../metanet-params/diagnostics/lane_plant_resume_20260921/sdmpc_state150_recovered_v4/result.json`. 모델 제약9900/9900 방문,1044041 allocation 및178200 상태 한계 검사, 최종 NP/NUF 제약 통과. 실제 적용 증거가 아니며 새 초기화 수정 전 모델의 결과다. query 시간별 통계는 복구하지 못했다.
- 저장기는 `diagnostics/sdmpc_qualification_report_v4.py`. 실제 보존 결과 전체를 JSON으로 저장하고 다시 읽어 응답·선택 결과가 동일함을 확인했다. 튜플 키, NumPy float64, 음수0을 유지하고 비유한 값은 거부한다.
- Native1950초 초기화 오류: connector10641 lane2의 길이45.291412m에 실제 정지차량8대가 존재하지만 평균6m 간격 모델의 한계는7.548569대였다. 실제 차량 길이는3.749–4.61m여서 평균 간격의 연속 모델과 순간 차량수 사이의 차이다. 차량을 삭제하거나 저장 한도를 올리지 않았다.
- 새 config 키 `freeway.lane_initial_spillback_projection: true`는10641에서만 초과하는 가장 상류 차량을 실제 연결된126의 같은 차로 여유 공간에 보수적으로 배치한다. 예측 초기 상태만 바뀌고 native 차량은 이동하지 않는다.1950초에는 차량9277 한 대를 connector 진입부에서5.194515m 상류 경계로 옮기는 공간 근사다. 차량·차로·목적지·총재고·기존 capacity를 보존하며, 상류 공간이 부족하면 여전히 실패한다. 이동 기록은 `lane_initial_spillback_projection`에 남는다. 없는 config는 기존 초기화를 유지한다.
- 상태 재현 후 예측에서 발견한 `OR_D_W_storage = -2.7755575615628914e-17` 차감 잔차는 기존16ULP 한정 차감 처리를 off-ramp landing/drain 및 local stock mirror에도 적용해 보완했다. 실질적 초과 차감과 전역 비음수/제약 검사는 계속 거부한다.

실패한 소스와 기존 evidence는 이전 두 작업 폴더에 그대로 남겼다. 이 작업 폴더는 이전 고정 입력/소스 중533개 파일을 복사한 별도 checkout이며 `source_copy.json`에 기록했다. vendor 및 실제 native network/demand는 수정하지 않았다.

## 확인한 검사

- 차량 이동/보존·실제1950초 관측·오프램프 반올림·lane 결합/관측·본선 회계27개 검사 통과.
- NumPy 숫자/튜플 키 왕복 및 비유한 값 거부 회귀 검사 통과.
- 새 설정의 `scripts/verify_parameters.py`: PASS.
- 실제1950초 초기화 및450초 held 예측 통과:228.127816초,9900/9900 제약 방문,1257128 allocation 및178200 상태 한계 검사. `state1950_held_v2.json`에 보존했으며 native 재개 전에 확인했다.

## 비교 조건과 해석

기존 METANET은 방향별21개 aggregate 셀과 기존 길이0.513441km를 유지한다. 새 FD의 v_free/rho_crit/a와 방향별 tau/nu/kappa/delta/phi만 이식한다. E:12/35/17/1/0, W:12/65/120/0/3 및 서쪽rho_crit 배율0.7. 수요는 최신 실제1098/1099 비대칭 입력이며 과거80/50 baseline은 재사용하지 않는다. 두 CL은 예측1초, 명령150초, 제어 시작900초,8워커다.

새 plant는 램프·일부 도시부 CTM 및 명시한 초기 상태 공간 투영도 포함하므로 두 CL 차이를 기하 하나의 인과 효과로 해석하지 않는다. 세 조건은 공통 실제 기하와 Ω membership으로 FZP를 분석한다.9000초 완전성, 명령 쓰기/적용/읽기 확인, 같은 준비 조건과 초기899초 차량 궤적을 확인한다. Ω TTT0–9000/900–9000, NC 대비 감소율, 본선/도시부·램프 영향과 계산시간을 보고한다. 제거/미확인 소실/종료 재고를 정상 완료 차량으로 합치지 않는다.

아직 세 조건 성능 결과는 없으며 단일seed 결과를 일반화하거나8–10% 개선으로 보장하지 않는다. automation `sdmpc-9000`은 의미 있는 완료·실패·사용자 판단이 필요한 변화만 알리고, 최종 비교 전달 뒤 비활성화한다.

