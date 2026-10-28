# VERIFY_A1_B0 대조 규칙 — 다시 세기 전에 고정 (2026-10-26 KST)

- 대상: `CH/A1_B0_RESULTS.md`(sha `dc062647…` LOG 기록값, 이번에 다시 잼) 와 그 근거 보고(`CH/a1/A1_RESULT.md`, `CH/b0/B0.md`, `CH/b0/PRE_B.md`, `AV/VA_REPORT_r4_CORRECTION.md`, `CH/A0B.md`).
- 방법: 저자 도구(a1_trace·a1_table·scan_fzp_a1·metrics_a1·vhr_*·unins_a1·r4_*·va_common·stage1_*)를 쓰지 않고 새로 쓴 도구 다섯 개로 원 자료(FZP·결정 파일·설정·코드)에서 다시 셈. 정의(링크 집합, 입력→링크 표)만 인계 파일에서 읽음.
- 이 규칙 전에 본 것(밝힘): 위 보고 본문 전부, r4 규칙 문서, A1 대조 규칙 문서, 자료의 꼴(FZP 머리·첫 행, 결정 CSV 머리, JSON 키 이름, runlog 한 줄 꼴, r3 va_metrics.json 키 구조), V-A s31 T=750/900/1650/3300 action JSON 의 `metadata.sdmpc_state` 유무(권장 1 전제 점검 중 먼저 봄), sdmpc.py:768-787. FZP 값·결정 행 값·설정 잎 값은 아직 세지 않음.
- 표시: [실행] 이번 도구로 셈, [읽음] 파일을 읽어 확인, [추론] 시험하지 않은 판단.

## 1. 도구 (sha 는 LOG 에 적음)

| 도구 | 하는 일 |
|---|---|
| `vfy_fzp_scan.py` | FZP 한 개를 한 번 읽어 프레임별 링크 재고, 프레임별 정렬 행 sha, t ≤ 895.1 접두 sha, 차량별 첫 관측(시각·링크) |
| `vfy_a1_table.py` | A1·joint·NC·LNC 스캔으로 codex 꼴 0–8,100 s 지표와 짝 차, 첫 관측 차분 ④b, 프레임 대조, 도착열 점검 |
| `vfy_trace.py` | A1 대 joint 결정 CSV·JSON·상태·runlog 대조, A0b T=1,050–2,550 대조 |
| `vfy_b0.py` | B 설정 대 codex 튜닝 잎 대조, 코드 트리 대조, FRZ_B0, lane plant, V-A T=900 전제 |
| `vfy_r4.py` | V-A·J1·NC3 9런 스캔으로 r4 ④b 짝 차·④·Ω 밖 (a)·통계·표시·누적·입력 몫 다시 셈 |

- 합성 자료 자기 시험: `selftest/syn.fzp` 로 스캐너만 시험함(0.10 행 건너뜀·첫 관측·프레임 재고 확인). 실제 자료로 시험하지 않음.

## 2. 정의

- codex 꼴(A1 표): 프레임 k 재고 n_k 를 다음 프레임까지 유지, 마지막 프레임은 8,100 s 까지. 0 s–첫 프레임은 0. TTT = Σ n_k Δ_k / 3600.
- 첫 관측 차분: S = Σ_{t첫 ≤ U} (U − t첫)/3600, d④b(a − b) = S_b − S_a. A1 표 U = 8,100. r4 U = 8,995.1, 0.10 행 건너뜀, 누적 c 는 U = c + 0.1(150 s 칸 중점 규칙과 같은 끝).
- 입력별: 첫 관측 링크 74 = 1098, 26 = 1099, 나머지 = 그 밖. 1083·1091·1092 몫은 인계 `demand_34_inputs.csv` 의 입력 링크로 첫 관측 링크를 맞춘 **근사**(stage-1 상류 추적 없음).
- 링크 집합: Ω701 = `omega_membership_exact.json` `inside_links`, Ω635 = `controlled_intersection_expansion.previous_inside_links`, ① = `scope_definitions.json` `FW_E_7`, ② = `local_19`, ④a = FZP 모든 행.
- r4 의 ③·④a·제거 A·B 는 r3 `va_metrics.json` 값을 읽어 씀(메모가 "r3 그대로" 라고 한 칸). 보조로 Ω635·④a·Ω701 을 두 꼴(F1 = 마지막 프레임 뺀 Σ n_k·5 s, F2 = 모든 프레임 Σ n_k·5 s)로 다시 내어 가까운 쪽과 대조.
- 통계: 평균, 표본 sd(n − 1), 90 % CI = 평균 ± 2.920·sd/√3, 엄격 부호 수. 표시 규칙: d③ ≥ 0 이면 해당 없음; N = (d④ ≤ 0 그리고 dΩ밖(a) ≤ 0), W_A/W_B = N 그리고 d④b ≤ 0 그리고 d제거(A/B) ≤ 0.

## 3. 허용 오차와 낱말

- 보고 소수 한 자리 칸: |내 값 − 보고 값| ≤ 0.06 veh·h. 세 자리 칸: ≤ 0.002. 근사·보조 칸(1083·1091·1092 몫, Ω701 참고 줄, Ω635·④a 재계산 대 r3): ≤ 0.5.
- 결정 대조: R1 = 명령 CSV 바이트 같음. 다른 행 = 행 순서와 키 열(kind,id,dsd_no,sc_no,link,lane)이 같을 때 행 전체 글자가 다른 수. 녹색 차 = p1–p4 녹색 |차| 최대.
- 상태 입력 잎: 경로꼴 문자열·64자리 hex·시각꼴·부속 키(run_id·byte_start·byte_end·max_t_any)를 뺀 "값" 잎 차 수.
- 결과 낱말: **확인**(다시 센 값이 허용 안), **반박**(허용 밖, 또는 인용한 파일·줄이 말한 내용을 담지 않음, 또는 산술 틀림 — 고친 값을 적음), **근거 부족**(가진 자료로 확인할 수 없거나 근거가 주장을 세우지 못함). 판정 낱말(효과 있음 등)은 쓰지 않음.
- 무게(load-bearing) 주장: A1_B0_RESULTS §0 쉬운 답 1–10, §1.3 표 값 가운데 §0 에 쓰인 것, §3 권장의 전제. 반환 pass = 무게 주장 가운데 반박·근거 부족이 0 일 때만 true.

## 4. 실행

- VISSIM·결정 재생 0. 원 자료 읽기만. 출력은 `CH/work/vfy_a1b0/out/`.
- 우선순위 BELOW_NORMAL, 한 번에 하나. 다른 세션 python(ChatGPT/RL td3) 이 돌고 있어 끄지 않음.
- 순서: 스캔 13개(A1 4개 `--tmax 8100`, r4 9개 `--skip010 --tmax 8995.1`) → `vfy_a1_table.py` → `vfy_trace.py` → `vfy_b0.py` → `vfy_r4.py`.
- 이 규칙과 도구는 자료를 본 뒤 고치지 않음. 실행이 꼴 문제로 죽으면(값 판단과 무관한 고침) 고친 판을 새 sha 로 LOG 에 적고 밝힘. 값을 맞추려는 고침은 하지 않음.
