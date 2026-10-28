# rmcause LOG

## 2026-10-24 10:37 KST (INV_PHYSICS 시작)
- 디스크: C 32.2 GB, D 344.5 GB 여유 [실행]
- 과제: v3c3 FW80 FW_E 물리 조사 (읽기 전용, 새 VISSIM 런 없음)



## 2026-10-24 10:37 KST INV_CODEX 시작
- 과제: codex 가 푸시한 버전 중 미터가 움직이고 FW_E 10% 넘게 개선을 주장한 버전 찾기.
- 디스크: C 32.2 GB, D 344.5 GB 여유 [실행].
- 원격 codex/sdmpc-plant-handoff-20261013 head = 9a8320ec (ls-remote), 로컬 origin ref = ffa4861e. 로컬에 9a8320ec 객체 없음 [실행].


## 2026-10-24 10:40 KST (INV_PRIOR 시작)
- 디스크: C 32.2 GB, D 344.5 GB 여유 [실행]
- 과제: 미터 관련 옛 발견 정리(메모리 19개 + VA_REPORT r2 + CAUSES r2 + COMPARE_355 r2), c20aff1d 코드 대조. 읽기 전용, 새 런·재생 없음.

## 2026-10-24 01:39:09 KST (FixVA r3 시작 — V-A 보고 글 결함 D1–D3, 미터 질문과 따로)
- 디스크: C 32.2 GB, D 344.5 GB 여유 [실행]
- 과제: VERIFY_VA_r2.md §5 D1(VA_REPORT 줄임말 COM), D2(VALIDITY GB-7′ 풀이), D3(VALIDITY §3 항목 이름 한 줄)만 고침. 숫자·도구·정의·표시 규칙 변경 0. VISSIM·COM·러너·재생·커밋·푸시 0.
- 시작 sha [실행 sha256sum]: VA_REPORT.md r2 5a94c782…331a, VALIDITY_VA.md r2 8f57c3ab…81f8, report_body.txt 8b576550…, report_src.txt 1ff87390…, assemble_src.py 9da28752…, va_report_build.py 651812cd…(고정 목록 값과 같음).
# rmcause LOG

## 2026-10-24 01:43 KST — INV_OURS 시작
- 과제: 우리 미터 파이프라인(결정층·작동층) V-A 3런 + J1 대조. 새 VISSIM 런·COM·재생 없음.
- 디스크: C 32.2 GB, D 344.5 GB 여유 [실행].
- 코드 확인: GWT8 head c20aff1d. 미터 경로 파일(PRB·SDM·sdmpc_sequence·ADP·AFO·PLG·parameters.json·area_meter_finalization) sha256 이 FRZ_K8(74cd495f)·FRZ_VA(c20aff1d) 동결본과 같음(sdmpc.py·sdmpc_sequence.py 는 CRLF 만 다름). VBS 만 다름(hold 장치) [실행].
- 읽기 전용 추출 스크립트 work/meter_inv.py (BELOW_NORMAL, PYTHONHASHSEED=0, python -B). 런 폴더는 읽기만.
- 10:55 KST INV_PRIOR: 메모리 19개·VA_REPORT·CAUSES·lens_meter·RM_GAIN_TRACE 읽음. 미터 경로 파일(sdmpc.py·PRB·parameters.json·physical_lane_groups·ADP·AFO) c20aff1d = FRZ_K8 74cd495f 바이트 동일(CRLF 차만) [실행].
- 10:56 KST INV_PRIOR: j1/causes/meter_work/meter_extract{,2}.py 를 V-A 런 3개로만 바꾼 사본(prior_work/) 실행 — 기존 joint.json 읽기 전용 추출, 재생 아님. BELOW_NORMAL, PYTHONHASHSEED=0, python -B.
- 10:46 FZP 읽기 스캔 3줄 WMI 분리 발사(BELOW_NORMAL, python -B, PYTHONHASHSEED=0). 체인 PID 36736/24876/39328. 대상 20개 FZP(NC3 5·V-A 3·J1 3·64cf-s29 none 1·stage1 v1/v2 NC/RM s31·s41 8). 쓰기는 rmcause/phys 아래만. 결정·plant 재생 아님 [실행]
- v3c3 RM 팔(s31/s41_v3c3rm)은 GB-13·보류 관행 때문에 결과를 열지 않음. run.json 머리(완료 true)와 파일 이름 목록만 봄 [읽음]
- 2026-10-24 01:46:53 KST (FixVA r3 끝) [실행] VA_REPORT.md r3 b57022e651adeefcaf1484993c20fd940b2e13012f0437e3a5b6c5ad6a20fc1b, VALIDITY_VA.md r3 609d2869eeca2d82834f250c0a87289ed0c5855d75afc6354b968ef3b164dc5f. r2는 _r2 이름으로 보관(5a94c782…, 8f57c3ab…). D1·D2·D3 들어감, 표 줄·인용 줄·숫자 변경 0. REPVA SHA256SUMS_ANALYSIS.txt 044bb09f…(99/99), SHA256SUMS_VALIDITY.txt 15bc52fd…(24/24). 공개: a34_pins 82/83 — 결정 기록 K9_1_J1_NOTES 가 10:35:33 에 D-K9-73 덧붙어 sha 바뀜(이 작업 아님; 보고서 §18.1에 적음). 자세한 기록 = VA/LOG.md [FixVA r3] 두 줄. 런·재생·VISSIM 0.
- 10:51 KST INV_PRIOR: 추출 끝(각 약 3.4 분, 종료 코드 1 은 마지막 tail 명령 탓, 두 JSON 정상). V-A 블록0 미터 기울기 양수 0/0/2(최대 8.8e-6), 걸음 최대 |z| 6.0e-4/1.39e-2/2.7e-3(<0.05), RM_C10681·RM_C10484 전부 |g|≤1e-9, NUF 잔차 중앙 −100/−103/−104 veh/h [실행]. 남은 프로세스 없음.
- 10:51 KST INV_PRIOR: K7 6c4c740 → c20aff1d 미터 경로(PRB·parameters.json·physical_lane_groups·topology_routes·REF·plant 매니페스트) diff 0, 튜닝 미터 키 같음 [실행]. FW_E plant δ_merge=1.0(boundary_fit parameters.json:18 → canonical_harness:590-591) — lens_meter §6.6 '0.0' 정정 [읽음].
- 10:53 KST INV_PRIOR 정정: 30–31행 '10:55·10:56' 은 어림 시각이었고 실제는 약 10:44–10:45 KST. VA_REPORT.md 는 10:44 에 r3(b57022e6…)로 바뀜 — INV_PRIOR 는 r2 사본 VA_REPORT_r2.md(5a94c782…) 줄 번호로 인용.
- 10:56 KST INV_PRIOR 끝: INV_PRIOR.md sha256 bf07cb5d4aa6599d64732676283ca23e378c7ca7bd1bcf3a342640999357edff. 표 23행(P0–P22), 결정층 (a) 원인이 c20aff1d 에 그대로, (b) 작동층은 시험 안 됨, '10 % 이상' 출처는 범위 안에서 못 찾음. 봉인 번호 시드 포함 문서(RM_GAIN_TRACE·RM_SEED_SWEEP) 수치는 옮기지 않음. 런·재생·VISSIM·커밋 0.

## 2026-10-24 10:58 KST INV_CODEX 진행
- 9a8320ec(원격 handoff 최신, 10-23) 를 별도 bare 저장소 D:/VISSIM-merge/k8_gate_trees/rmcause/codex_remote.git 로 fetch(기존 repo ref 무변경, alternates 사용) [실행]. 끝나면 지움.
- 핵심 발견: d80faf99 (codex/control-full-review-20260909, 09-24 푸시) diagnostics/vsl_handoff_20260924/evidence/accounting/east_link_sets_source.json rows: 64cf-s29 ALINEA RM 동측 본선 7링크 2249.69→1984.08 (−11.81%), 국소19 −8.90% [읽음]. codex 문서 중 10% 넘는 FW_E 수치는 이것 하나.
- codex window264(ca181e84 config, 이 PC 에서 10-07~08 실행) SDMPC 런은 미터가 실제로 움직임(action csv) [실행 읽기]. FW_E 미분석 → 읽기 전용 FZP 스캔 1줄 사슬 WMI 분리 발사(PID 41916, BELOW_NORMAL, PYTHONHASHSEED=0, python -B). 대상 3 FZP(window264, 64cf-s29 none, stage1 v2 s31 nc 검산). 쓰기는 rmcause/codex_scan 아래만. 결정·plant 재생 아님.
- v3c3 RM 팔(s31/s41_v3c3rm)·v3c1 RM 팔은 열지 않음(GB-13 관행, INV_PHYSICS 와 같음). s37 폴더 안 열음.

## 2026-10-24 02:02 KST — 코드 추적·첫 추출
- V-A s31 추출 완료(124 s). 미터 8개 × 블록 3 모두 선택 녹색 10, 중앙 걸음 |z| 최대 6e-4, 문턱 0.05 [실행].
- 새로 찾은 것: 리더 예산 탐색이 꺼져 있음 — config_n31_v2.json:7696 max_leader_candidates 1, sdmpc.py:925 조건이 거짓이라 central.next_budget(sdmpc_central.py:109) 호출 안 됨. 결정당 후보 1개 [읽음·실행].
- NUF 상한 = PFO 달성 + 100(sdmpc_budget.py:42-45) → 시작부터 100 veh/h 여유 [읽음].
- 작동층 반례 확인: hybrid v3c1 s31b 런은 같은 CSV 부호(rate=g×90)로 녹색 2–9 를 썼고 signal_readback 에 9105–9108 RED 431–1020 회 [읽음 run folder]. 우리 경로도 녹색<10 이면 VISSIM 에 RED 가 간다는 정황.
- 실수: 출력 파일명에 ':' 를 넣어 NTFS 대체 스트림이 생김(빈 파일 meter_inv_VA·meter_rows_VA). 지우고 이름 규칙 고쳐 6런 재추출(run_all.log).
- 10:53 스캔 20/20 끝, 내 PID 모두 종료 확인 [실행]
## 2026-10-24 11:2x KST INV_PHYSICS 완료
- 산출: INV_PHYSICS.md sha256 00d94e900a67c5edbe91079e5fce4bcbf55035327c7ded9c3a548f47358574c9; phys/out_all.json, phys/authority.json, phys/scan/*.json 20개, 스크립트 5개. 전체 sha 목록 phys/SHA256SUMS_physics.txt [실행]
- 요지: v3c3 무제어 FW_E는 대부분 비붕괴(B1 꼬리<4.5km 〔가림: 봉인·블라인드 시드 값〕분), 미터 본선 상한 평균 약 〔가림: 봉인·블라인드 시드 값〕%(stage1 잔여 바닥)·〔가림: 봉인·블라인드 시드 값〕%(관대), stage1 규칙 RM은 붕괴 기준선에서 FW_E −12~−24% [실행]
- 봉인 시드·v3c3 RM 팔 결과 열지 않음. 새 VISSIM·COM·커밋·푸시·워크트리 없음 [실행]

## 2026-10-24 02:09 KST INV_CODEX 끝
- 스캔 사슬 끝(CHAIN_DONE 10:59:30), 소유 PID 41916·31808·37956·48304·13004 모두 종료 확인 [실행].
- 결과 [실행]: window264(ca181e84 설정, 64cf-s29) 본선 7링크 2248.98→1987.79 (−11.61 %), 900 s 전 FZP 행 sha 같음(f1a0b040…, 431,233행). 미터는 meter_neighbor_audit 로 움직임(55회 중 49회 미터 후보 선택), readback 12,869행 ok. 단 VSL90 창 동시.
- codex 문서 속 10 % 초과 FW_E 수치는 d80faf99 east_link_sets_source.json rows[5] 64cf-s29 ALINEA −11.81 % 하나 [읽음].
- 우리 stage-1(codex ALINEA 코드) 본선: v2-s31 −13.17 %, v2-s41 −13.67 %, v3b-s31 −3.75 %, v3b-s41 −9.71 % [실행 scan.json].
- 임시 bare 저장소 D:/VISSIM-merge/k8_gate_trees/rmcause/codex_remote.git 지움 [실행].
- 산출 sha256: INV_CODEX.md 8774df9c4730e60614b21995409992a871b75f8b22d7503c447d499e7c6de737; codex_scan/cx_scan.py 703209a3…; out/cf_s29_window264.json 8359a119…; out/cf_s29_none.json ca4fd04e…; out/st1v2_s31_nc.json e409a120….
- 열지 않음: v3c3·v3c1 규칙 RM 팔 결과, s37 폴더 전부. 다른 프로세스 PID 35780(codex 9a8320ec rolling_cea) 건드리지 않음.

## 2026-10-24 02:19 KST — 6런 추출 완료 (905 s)
- 산출: work/meter_inv_all.json, work/meter_rows_all.csv(2,640행 = 6런 × 55결정 × 8미터), work/per_meter_summary.csv.
- 선택 녹색: 6런 × 61결정 × 8미터 블록0 모두 10, 미래 블록 1·2 도 기록된 것 모두 10(V-A 53/52/55, J1 54/51/55 결정; 나머지는 reference 유지 결정이라 sequence 없음). CSV 900·10, 러너 488행 900·10·GREEN, signal_readback 미터 SC 488행 모두 GREEN [실행].
- 조이는 쪽 기울기 최대(아무 블록): V-A PFO 0.0086/0.216/0.082, 중앙 0.006/0.139/0.027; J1 PFO 0.0048/0.080/0.0006, 중앙 0.0002/0.057/0.0004. 모두 RM_C10490, 블록 1·2. 걸음 문턱 0.5 [실행].
- J1 lens_meter 수치(블록0 2,432개 중 양수 1개 7.7e-5, 듀얼 0 아닌 결정 10/10/1) 재현 [실행].
- RM_C10490 열어라 기울기와 예측 합류 상관 −0.62 ~ −0.89 [실행].

## 2026-10-24 02:23 KST — INV_OURS.md 작성 완료
- 결론: (a) 결정층이 원인. 요청·롤아웃 모두 녹색 10만. 막는 겹: 부호(열어라/0), 크기(조여라 최대 0.22 < 0.5), NUF 상한 = PFO+100·리더 탐색 꺼짐(max_leader_candidates 1), 상자 {8,9,10} 수요 위, 용량 강하·종단비용 없음, 간격 노드 미터 기울기 0.
- (b) 작동층: 요청 0이라 손실 0. 정수 녹색은 그대로 전달, 제약은 ±2 s/결정.
- 새 런·재생·커밋·kill 0. 봉인 시드·codex 64cf 수치 0.

## 2026-10-24 11:29 KST — METER_CAUSE 종합 시작
- 디스크: C 33 GB, D 344 GB 여유 [실행].
- 입력 sha256 [실행]: INV_OURS 2b22466c…46a1, INV_CODEX 8774df9c…e737, INV_PHYSICS 00d94e90…74c9, INV_PRIOR bf07cb5d…7edff.
- 종합 중 직접 확인(읽기만): δ_merge 배포값(boundary_fit parameters.json:18 FW_E 1.0, canonical_harness.py:341·:590-602), 간격 노드 CFG:8105-8116, 미터 설정 CFG:7492-7536·:7696, ca181e84 sdmpc.py 이웃 검사(:555-650, :1151-1168)·window264 설정, REPRO_RESULT.md:21-23, window264 action CSV 미터 녹색 집계 [실행]. 새 VISSIM·COM·재생·커밋 0.
- 시각 주의: 이 LOG 의 01:xx·02:xx 항목은 Git Bash TZ 해석 탓에 9시간 어긋난 값으로 보임(기기 시간대 = Korea Standard Time, 같은 작업이 10:xx–11:xx 에 있었음) [실행 PowerShell 시간대 확인; 해석은 추론].

## 2026-10-24 11:34 KST — METER_CAUSE 종합 끝
- 산출: METER_CAUSE.md sha256 58c3c31bad7896a7d6ffe09a238a5297bea51313f60b854e2c227f05ee3dae52; 읽기용 사본 work/ca181e84_sdmpc.py sha256 ccdbf44c65ee3a784a190169e2c246327c1147e7652e1b2be2650d0749c5b974 (git show ca181e84:evaluation/controllers/sdmpc.py) [실행].
- 요지: 미터 고정 = (a) 결정층(P: 기울기 ≤ 0.5 → QP 걸음 10, Q: 유한 후보·리더 탐색 경로 없음). (b) 원인 아님. codex 10 % 초과 = 64cf-s29 규칙 ALINEA −11.81 %, window264(이웃 검사 + VSL90 창) −11.61 %, 둘 다 본선 7링크·붕괴 기준선. v3c3 상한 평균 〔가림: 봉인·블라인드 시드 값〕 %(추정).
- 정리한 모순: δ_merge 배포 FW_E 1.0(PRIOR 맞음), VSL90 단독 −6.09 %(본선)·−6.15 %(국소) 둘 다 맞음 등 11건. 열린 것: FW_E 차로군 plant 여부, 10681 모형 합류 과소, g2 서비스 실측 vs 표.
- 새 VISSIM·COM·재생·커밋·푸시·kill 0. 봉인 시드·codex 64cf-s59/61/67 수치 0. v3c3·v3c1 규칙 RM 팔 미개봉.

## 2026-10-24 11:35 KST — VERIFY_codex-compare 시작
- 과제: METER_CAUSE.md(58c3c31b…) 의 codex 비교 주장 적대 검토. 읽기 전용. 새 VISSIM·COM·러너·재생·커밋·푸시 0 예정.
- 디스크: C 32.2 GB, D 343.8 GB 여유 [실행].

## 2026-10-24 11:35 KST — VERIFY_code-data 시작 (적대 검토, 코드·자료 렌즈)
- 대상: METER_CAUSE.md sha256 58c3c31b…dae52 [실행].
- 디스크: C 32.2 GB, D 343.8 GB 여유 [실행].
- 방법: c20aff1d 코드를 `git show` 로 직접 읽고, V-A 런 자료를 새 스크립트(rmcause/verify_cd/ 아래)로 다시 셈. 조사자 스크립트 재사용 안 함. 새 VISSIM·COM·러너·재생·커밋·푸시·체크아웃 0.
- 2026-10-24 11:54 KST: 9a8320ec 를 임시 bare 저장소 D:/VISSIM-merge/k8_gate_trees/rmcause/verify_cx_remote.git(alternates) 로 fetch(읽기용, 기존 ref 무변경). 끝나면 지움.
- 2026-10-24 11:54 KST: 임시 bare 저장소 verify_cx_remote.git 지움 [실행]. 9a8320ec AGENTS.md:19 = REVIEW255 중간값 줄(ca181e84:AGENTS.md:15·ffa4861e:AGENTS.md:17 과 같은 글).
- 12:01 KST VERIFY_code-data 진행: c20aff1d 코드(sdmpc.py·sdmpc_pfo.py·sdmpc_sequence.py·PRB·BUD·CEN·CONT·AFO·ADP·AMF·LFR·LPR·PLG·VBS·CFG·PAR·CH·BF)를 `git show` 로 verify_cd/src 에 뽑아 읽음 [실행]. 새 스크립트 verify_cd/recompute_meter.py·projection_check.py·nuf_jacobian_scan.py·detail_check.py 로 V-A 3런·J1 3런 joint.json·action JSON·CSV·readback 을 다시 셈(읽기만, python -B, PYTHONHASHSEED=0, BELOW_NORMAL; 첫 V-A 3회는 ctypes 우선순위 호출이 실패해 Normal 로 돌았고, 실행 중 내 PID 3452 를 BelowNormal 로 낮춘 뒤 스크립트를 고침) [실행]. 다른 python PID 26424(codex 9a8320ec rolling 런)는 건드리지 않음.
- 읽기만: window264 action CSV·progress.jsonl·config, codex 커밋 ca181e84·d80faf99·85e3454b 파일(`git show`), gb6_result.json, VA_REPORT_r2, REPRO_RESULT.md. 봉인 시드 자료·codex 64cf-s59/61/67 수치 열람·인용 0.
- 2026-10-24 12:02 KST — VERIFY_codex-compare 끝. 산출 VERIFY_codex-compare.md sha256 5b0334b0cd39ede788cc265db43f923514c6b5e39cd37d5611a04986206ace99, 추출물 verify_cx/ [실행].
  - 판정 pass=false: 반박 3(+7.85 % 런 성격=이웃 검사 켜진 0–6600 s 중간값 / δ_merge 행 '불명'→W264 plant 셀별 2.2–5.1 / '가장 많이 움직인 미터'=서측 10480), 부분 수정 2(이웃 검사는 필요하지만 충분하지 않음 / W264 −11.61 % 는 codex 미보고·그림 영역은 19링크 −8.90 %) 외 보조 수정 다수.
  - 새 VISSIM·COM·러너·동결·재생·커밋·푸시·체크아웃·kill 0. 봉인 시드 자료 0. v3c3·v3c1 RM 팔 미개봉. 임시 bare 저장소 지움. GWT8 head c20aff1d 깨끗함.
- 12:19 KST VERIFY_code-data 끝: VERIFY_code-data.md sha256 dc82fab09b58a7717eb8a64f7c1cc611d71c6d2f66838cba7bbe78fb1d11afea [실행]. 디스크 C 32.2 GB, D 341.8 GB [실행].
  - 다시 셈 [실행]: 6런 × 61결정 블록 0 요청 488/488 g10, 미래 블록 기록분 모두 g10, 결정·러너 CSV 488/488 900 vph·10 s, V-A s31 signal_readback 미터 488행 RED 0, 기울기→걸음 재해독 ≠10 0건(PFO·중앙, 블록 0–2, k=0–2). 표 verify_cd/out/per_decision_va_s31.csv.
  - 판정: (a) 결정층 P∧Q 확인, 상위 원인 a2·a3·a1 반박 못 함. 고칠 것: F1 PLG 거부는 V-A plant v2 경로 아님(C7·O5 닫힘), F2 §1.6 a5 필요성 모순·a1 필요성 근거 없음, G2 §0-2 기구 문장 근거 없음(V-A 큰 '열어라'가 NUF 자코비안 0 에서 나옴). 새로 찾음: V-A NUF 의 미터 자코비안 ≤0.43 veh/h/z(J1 s41 T=1650 만 457–612). pass=false(PARTIAL).
  - 프로세스: 내 python 모두 종료. PID 26424(codex) 무접촉. 새 VISSIM·COM·재생·커밋·푸시·체크아웃 0.

## 2026-10-24 12:21 KST — METER_CAUSE r2 마무리(Finalize) 시작
- 과제: VERIFY_code-data(dc82fab0…)·VERIFY_codex-compare(5b0334b0…) 정정을 METER_CAUSE.md 에 넣음. r1 은 METER_CAUSE_r1.md 로 보관. 최종본을 D:/VISSIM_runs/20261001_v3c3/reports/k8/rmcause/ 로 복사.
- 디스크: C 32.2 GB, D 341.8 GB 여유 [실행]. 새 VISSIM·COM·러너·동결·재생·커밋·푸시·체크아웃 0 예정.

## 2026-10-24 12:28 KST — METER_CAUSE r2 마무리 끝
- 산출 [실행 sha256]: METER_CAUSE.md r2 0b4036c62cd2e2983c9965dd6010a4c93a88d83635a98293e82acb3fe92c626c. 앞 판 METER_CAUSE_r1.md 58c3c31b…dae52 (r1 과 같은 바이트).
- 넣은 정정: VCD F1(PLG 거부는 V-A 경로 아님, C7 닫힘·O5 삭제), F2(§1.6 두 열, a1 필요성 미확인·a5 불필요), F3·G2(§0-2 기구 문장·a2-4 해석 철회, a2-5 '미확인' 새 노드), G1·G3–G8; VCX R1–R5(+7.85 % = 이웃 검사 켜진 233/235 중간값, 검사는 직접 장치이나 충분조건 아님, δ_merge plant 층 셀별 3.53·5.09·4.21·2.21, W264 최다 미터 = 서측 RM_C10480, W264 −11.61 % 는 codex 미보고), C1·C5·C6·C12–C21, §3 빠진 행(plant manifest·서비스 표·녹색 0/guard·v_free·VSL 집합·도시 신호). 변경 기록 §7.
- 마무리 직접 확인(읽기만) [실행]: git show c20aff1d MAN:59 lane_groups false · LPR:120-121 · CFG:7441 metanet_delta_merge 0.3 · DP:227 alinea_meter_step; git grep allow_zero_green c20aff1d evaluation 0건; git show ca181e84 PRB:50 allow_zero · AGENTS.md :13 :15 :43 :57; VX/eval036_ref.json FW_E 셀 10 δ_merge 3.53 등; VX/cfgdiff2.txt 서비스 표(W264 g9=g10=4.2, 우리 RM_C10490 g9 3.69).
- 복사: D:/VISSIM_runs/20261001_v3c3/reports/k8/rmcause/ 에 METER_CAUSE.md·METER_CAUSE_r1.md·VERIFY_code-data.md·VERIFY_codex-compare.md 와 SHA256SUMS.txt(63ab5abc…6afe), 원본과 sha 같음 [실행].
- 새 VISSIM·COM·러너·동결·재생·커밋·푸시·체크아웃·kill 0. 봉인 시드 자료 0. v3c3·v3c1 규칙 RM 팔 미개봉. 디스크 C 32.2 GB, D 341.8 GB [실행].

## 2026-10-24 12:34 KST — O4 시작 (10681 합류: 모형 예측 vs VISSIM 실측, 같은 창)
- 과제: D-K9-75 O4. V-A(및 J1) 결정 JSON 의 예측 합류(NUF·램프 합류)와 같은 런 VISSIM 실측 합류를 같은 창으로 맞춰 비율. RM_C10681 주, RM_C10490·RM_C10484 빠른 비율. 코드 경로 c20aff1d file:line.
- 디스크: C 32.2 GB, D 341.8 GB 여유 [실행]. 새 VISSIM·COM·러너·동결·재생·커밋·푸시·체크아웃 0 예정. FZP 읽기는 한 번에 하나, WMI 분리, BELOW_NORMAL.

## 2026-10-24 12:40 KST — O1 시작 (D-K9-75: 보류된 v3c3 규칙 RM 팔 s31_v3c3rm·s41_v3c3rm 개봉)
- 사용자 결정 D-K9-75 로 두 팔을 엶. s37_v3c3rm(봉인)은 폴더 목록·파일 어느 것도 열지 않음.
- 디스크: C 32.2 GB, D 341.8 GB 여유 [실행].
- 계획: 출처 기록(빌드 영수증·rule_policy·fast_fixed_profile·diagnostic_profile·run.json·fixed_validation) → stage-1 스캔(같은 고정 도구 stage1_scan/uninserted, 출력은 rmcause/o1o4/o1 아래만, 런 폴더 쓰기 0) → NC3·V-A 스캔 재사용(sha16 확인) → 지표·시계열·미터 기록.
- 새 VISSIM·COM·러너·동결·재생·커밋·푸시·체크아웃 0 예정.

## 2026-10-24 12:38 KST — W264_READ 시작 (D-K9-74, 읽기 전용)
- 과제: codex SDMPC W264(ca181e84 window264, 64cf-s29, 이 PC 10-07~08)와 짝 NC `vsl_repro_s29/none` 의 출처 기록 + 150 s 시간 분해. 산출 `o1o4/W264_READ.md`.
- 디스크: C 32.2 GB, D 341.8 GB 여유 [실행].
- 계획: FZP 읽기 3회(W264 fwe_scan, W264 linkbin, NC linkbin)를 한 사슬로 WMI 분리·BELOW_NORMAL·PYTHONHASHSEED=0·python -B 로 하나씩. 쓰기는 `rmcause/o1o4/` 아래만. 새 VISSIM·COM·러너·동결·재생·커밋·푸시·체크아웃 0 예정. 봉인 시드·codex 64cf-s59/61/67 열람 0.
- 12:45 KST O4: 읽기 전용 FZP 사건 스캔 사슬 WMI 분리 발사(PowerShell PID 34840, BELOW_NORMAL, PYTHONHASHSEED=0, python -B). 대상 6개 FZP 를 한 번에 하나씩(V-A v3c3-s31/41/43, J1 v3c3-s31r/41/43). 스크립트 o1o4/work/o4_fzp.py(합류·진입·미터헤드 통과·150 s 재고·상류 차로 통과). 쓰기는 o1o4/fzp, o1o4/work/logs 아래만. 결정·plant 재생 아님. 다른 세션 PID 건드리지 않음.
- 12:40–12:42 KST 사슬 1 (WMI PID 44628, BELOW_NORMAL): W264 fwe_scan(42 s)·linkbin(30 s), NC linkbin(30 s) 끝 [실행 `o1o4/logs/chain.log`]. W264 FZP sha a4f2afc7…, NC FZP sha 9c097cc7… [실행].
- 12:48 KST 사슬 2 추가(WMI PID 44052): codex VSL90 단독 팔(`vsl_repro_s29/vsl`, 900–9,000 s, 미터 없음·도시 native) fwe_scan·linkbin. VSL 몫의 시간 모양을 보려는 것(창이 달라 그대로 빼지 않음).
- 12:50 KST O4: 사슬 1 끝(CHAIN_DONE 12:50:24, 6/6 rc=0, 각 20–120 s). 사슬 2 WMI 분리 발사(PowerShell PID 27020, BELOW_NORMAL): 공급 링크 68/31/129/70 이탈 목적지 스캔(o4_fzp_split.py, FZP 6개 하나씩) 뒤 결정 JSON 추출(o4_model.py, 6런 하나씩). 읽기 전용, 쓰기는 o1o4/fzp·o1o4/model·o1o4/work/logs 아래만.
- 12:59 KST W264_READ 끝. 산출 `o1o4/W264_READ.md` sha256 cb53536164c52cf717271e5f9b599e6d8a0bcbde31a00495196914e65b6b1e01 [실행].
  - 핵심 [실행]: 본선 7링크(74·10699·2·10613·119·10702·24) 2,249.35 → 1,988.17(−261.17, −11.61 %). 창 앞 −0.57(0.2 %), VSL 창 1,800–5,700 s −206.19(79 %; 첫 900 s +9.34), 창 뒤 −54.42(21 %). 링크 2 가 −240.8(92 %). NC B1 번짐 62분·M 번짐 19분 → W264 0·6분(VSL 단독 0·18분). 동측 램프 +140.8, 국소 19 −135.6(−5.46 %), Ω701 −463.8, 전체+미삽입 −639.1(−2.21 %, VISSIM). v3c3 NC3 B1 번짐 0/0/2분.
  - 번짐 꼬리 정의를 다시 짜 INV_PHYSICS 표 56값을 모두 재현(`o1o4/work/tails_variants2.py`). 미삽입 대리 계산 차 −220.0 vs VISSIM −225.5.
  - 프로세스: 내 사슬 PID 44628·44052 와 자식 python 모두 끝남. 다른 세션 python·VISSIM(26288·32812·50396·49024 등) 무접촉. 주의: 내 사슬(12:40–12:42, 12:48–12:50)이 O4 FZP 사슬(12:45–12:50)과 겹쳐 조사 사이 동시 FZP 읽기가 있었음(읽기만).
  - 새 VISSIM·COM·러너·동결·결정/plant 재생·커밋·푸시·체크아웃·kill 0. 봉인 시드 자료 0. codex 64cf-s59/61/67 숫자 0. 쓰기는 `rmcause/o1o4/`(W264_READ.md, work/·scan/·logs/ 내 파일)와 이 LOG 뿐. 디스크 C 32 GB, D 342 GB [실행].
- 13:00 KST O4: 사슬 2 끝(CHAIN_DONE 13:00:35, split 6/6·model 6/6 rc=0). 사슬 3 WMI 분리 발사(PowerShell PID 22560, BELOW_NORMAL): o4_model2.py(도함수 기록별 예측 합류·블록 끝 램프 재고·공급 흐름 수) 6런 하나씩. 읽기 전용.

## 2026-10-24 13:02 KST — O1 끝 (v3c3 규칙 RM 팔 s31·s41 개봉)
- 산출: o1o4/O1_RULE_RM_V3C3.md sha256 7af4a16ff0b75cb3f11c1910b53c2a7b87616a4caad4f0b193086cdcb8c1a6d5. 도구·출력·스캔은 o1o4/o1/ (sha 는 보고서 §9).
- 출처 [실행·읽음]: 망 = v3c3nc + RM 3절(46절 중 3절만 다름, 수요 같음), 시드 31/41, 결정 54개(900–8,850 s) 연속, 실패 0, fixed_validation passed(미터 창 432/432 관측=명령), run.json completed·exit 0. 규칙 = sim3 fast_fixed_profile.py(a05eb0c5, HEAD 673eece9 + 7줄 자르기) → diagnostic_profile.py alinea_meter_step(389d81c8, c20aff1d 판과 바이트 같음). ALINEA 목표 15 %, 이득 70/140, 하한 255.6/511.2, 상한 1512/3024, ±2 s/150 s. VSL 이벤트 0.
- 짝 확인 [실행]: NC3 와 첫 RED 전까지 프레임 같음(첫 갈림 s31 2,500.1 s, s41 1,690.1 s), 900 s 전 차 0. V-A − NC3 값은 V-A 보고와 같게 재현.
- 미터 [실행]: FW_E 4개만 조임(s31 6/22/18/22회, s41 8/37/28/29회; 10490·10484 최소 g2). FW_W 4개 54/54 g10(점유율 최대 5.2–8.6 %).
- 주 지표 ① FW_E 본선 7링크(74, 10699, 2, 10613, 119, 10702, 24) RM−NC3: s31 −11.6 (−0.64 %), s41 −153.6 (−7.82 %), 평균 −82.6 (−4.37 %). 같은 표: FW_E 미터 대기 +9.5/+49.4, ② +4.0/−165.1, ③ −10.3/−75.8, ④ −58.4/+515.3, Ω 밖 (a) −48.1/+591.1, 1099 미삽입 −26.5/+644.6(끝 remain 665), FW_W 본선 −2.0/+256.1, 1098 −18.6/−39.3, ③u +4.0/−22.6. V-A−NC3 같은 시드 ① −12.3/−72.6, ④ −367.7/−518.1.
- 기구 [실행 FZP 계수; 사슬은 추론]: s41 링크 129 공유(10490 접근 = FW_W 진출 10491 착지) → 10491 재고 2.3–2.8 배 → 링크 26 저속 차 3.0 배 → 1099 미삽입. 2,700–4,500 s 본선 차 −69.7 은 RM 에만(V-A −1.7), 6,300–8,100 s −59.2 는 V-A 도 −58.6.
- 무거운 읽기: stage-1 스캔 2회(WMI PID 41404), FZP 결합 스캔 4파일(PID 43548) 한 번에 하나, BELOW_NORMAL, python -B, PYTHONHASHSEED=0. 내 프로세스 모두 끝남. 다른 세션 python·cscript 무접촉.
- 새 VISSIM·COM·러너·동결·재생·커밋·푸시·체크아웃·kill 0. 런 폴더·frozen 쓰기 0. 봉인 시드·codex 64cf-s59/61/67 수치 0. s37_v3c3rm 출력 미개봉. 디스크 C 31.7 GB, D 341.8 GB [실행].
- 13:08 KST O4: 사슬 3 끝(CHAIN_DONE 13:08:19, 6/6 rc=0). 내 분리 프로세스 모두 종료(상태 파일 CHAIN_DONE 3개).
- 13:20 KST O4 끝: o1o4/O4_MERGE_10681.md sha256 fb178ef4beee4354678098151aadc3aa3251205c128e375eec2c1c6c940b5407, 산출 목록 o1o4/SHA256SUMS_O4.txt sha256 bd34659c72cad507d43bd33469f1a2cff6fff23930ff52e414eff59706c12811(44파일) [실행].
  - 요지 [실행]: 10681 같은 창 [T,T+450] 모형/VISSIM 합류 비 중앙 0.468(312결정, p10 0.198, p90 0.576, 최대 0.641). 창 평균 모형 34.1+20.2−1.2=53.1대 vs VISSIM 34.1+121.8−34.2=121.8대. 도착 비 중앙 0.160: 링크 68 결정점 1135 의 10681 사전 몫 0.1667(outputs/boundary_out_ramp_split_20260905_measured.json) vs inpx relFlow 0.6·FZP 실현 0.598, 링크 68 유입 0.54배(SC1004 S→W·N→W 27.6·29.1 vs 280·328 veh/h, 206.53×녹색비와 일치). g10 상한 비활성(최대 0.255), 간격 노드는 블록 0 만. 10681·10484 dNUF·비용 기울기 모두 0, 10490 비용 312/312 음수(FW_E 99.8 %)·dNUF>1 은 J1 v3c3-s41 T=1650 하나. 10490 비 1.20, 10484 0.89.
  - 새 VISSIM·COM·러너·동결·재생·커밋·푸시·체크아웃·kill 0. 내 분리 프로세스 3사슬 모두 끝(CHAIN_DONE). 다른 세션 python(codex 9a8320ec) 무접촉. 봉인 시드·codex 64cf 수치 0. 디스크 여유 C 31.5 GB, D 341.8 GB [실행].

## 2026-10-24 13:24 KST — METER_NEXT 종합 시작 (O1·O4·W264 → 다음 단계)
- 입력 sha256 [실행]: O1_RULE_RM_V3C3.md 7af4a16f…d5, O4_MERGE_10681.md fb178ef4…07, W264_READ.md cb535361…01, METER_CAUSE.md 0b4036c6…6c, K9_1_J1_NOTES 7dcbcf8d…a4.
- 계획: 위 문서와 기존 JSON(o1/out/o1_metrics.json, work/w264_analysis.json)만 읽어 표를 만듦. FZP 읽기 0, 새 VISSIM·COM·러너·동결·재생·커밋·푸시·체크아웃 0. 출력 o1o4/METER_NEXT.md.
- 디스크: C 31.5 GB, D 341.8 GB [실행].
- 2026-10-24 13:32 KST METER_NEXT 끝: o1o4/METER_NEXT.md sha256 221b8e4ee842fd44677824cd844f2458b8b9c8dd9127e880b35db29656be5a41 [실행].
  - 내용: §0 쉬운 답 8줄, §1 한 표(v3c3 NC3/V-A/규칙 RM s31·s41 + 64cf-s29 NC/W264/VSL 단독, 주 지표 FW_E 본선 7링크 74·10699·2·10613·119·10702·24 와 옮겨 간 대기), §2 결함 D1–D5 와 설계 선택 S1–S6·순서, §3 오프라인 N1–N5·재생 P1–P3(승인 필요)·새 VISSIM R1–R4(시간), §4 질문 8개.
  - 표 값은 o1/out/o1_metrics.json(/per_run/UC|*)·work/w264_analysis.json(/periods/0-9000, /checks) 에서 다시 뽑음, O1·W264 표와 일치 [실행].
  - 새 VISSIM·COM·러너·동결·재생·커밋·푸시·체크아웃·kill 0. FZP 읽기 0. 런 폴더·frozen 쓰기 0. 봉인 시드·codex 64cf-s59/61/67 숫자 0. 디스크 C 31.5 GB, D 341.8 GB.

## 2026-10-24 13:34 KST — VERIFY_NEXT 시작 (METER_NEXT·O1·O4·W264 적대 재검증)
- 과제: METER_NEXT.md(221b8e4e…5a41)와 O1(7af4a16f…)·O4(fb178ef4…)·W264(cb535361…) 의 쉬운 답 주장을 새 스크립트(읽은이 스크립트 재사용 0)로 다시 계산해 반박 시도. 출력 o1o4/VERIFY_NEXT.md, 작업 o1o4/vnext/.
- 계획: FZP 새 스캐너(링크별 차량-프레임·10681 합류 사건)를 WMI 분리·BELOW_NORMAL·PYTHONHASHSEED=0·python -B 로 한 번에 하나씩(NC3-s31, RM-s31, V-A-s31, 64cf-s29 NC, W264, 여력 되면 s41 짝). RM 출처(run.json·rule_policy·inpx sha·결정)·결정 JSON 5개 10681 예측 합류 재추출.
- 안 함: 새 VISSIM·COM·러너·동결·결정/plant 재생·커밋·푸시·체크아웃. 런 폴더·frozen 쓰기 0. 봉인 시드 37/59/61/67·codex 64cf-s59/61/67 0.
- 13:41 KST VERIFY_NEXT: 새 FZP 스캐너 `o1o4/vnext/tools/vn_fzp_scan.py`(읽은이 도구 재사용 0) 사슬 WMI 분리 발사(PowerShell PID 21200, BELOW_NORMAL, PYTHONHASHSEED=0, python -B). 한 번에 하나씩 FZP 9개(NC3/RM/V-A s31, 64cf-s29 NC/W264/VSL, NC3/RM/V-A s41) 다음 V-A 결정 JSON 7개 추출(vn_model_extract.py). 쓰기는 o1o4/vnext/ 아래만. 다른 세션 프로세스 무접촉.
- 13:49 KST VERIFY_NEXT: 사슬 1 끝(CHAIN_DONE 13:48:55, FZP 9개 각 45–55 s, 결정 JSON 7개 10 s). 내 프로세스 모두 종료.
- 13:51 KST VERIFY_NEXT: 사슬 2 WMI 분리 발사(PowerShell PID 33640, BELOW_NORMAL): V-A v3c3-s31 FZP 한 개에서 링크 68·31·129·70 이탈·진입 계수(vn_fzp_split.py). 읽기만.
- 2026-10-24 14:03 KST VERIFY_NEXT 끝: o1o4/VERIFY_NEXT.md sha256 49cc05f7134934e17ba162ee8d6f636e2a588a6065c141c7cc3aaadee283fa22 [실행]. 사슬 2 끝(CHAIN_DONE 13:52:01). 내 프로세스 모두 종료.
  - 확인 [실행]: FW_E 본선 7링크(74·10699·2·10613·119·10702·24) 짝 차 6쌍 모두 보고 0.1 veh·h 안(RM−NC3 −11.60/−153.59, V-A−NC3 −12.35/−72.57, W264−NC −261.17(−11.61 %), VSL−NC −136.94). v3c3 수준만 +0.32–0.38 일정 차. RM 출처(망 sha·3절 차·정책 df8acd08·결정 54·녹색 문자열·VSL 0·검증) 모두 같음. W264 VSL 창 78.9 %·링크 2 92.2 %·+9.34. B1 번짐 NC 62분/W264 0분(새 꼬리 코드). 10681 모형/VISSIM 7결정 21쌍 O4 출력과 같음, 링크 68→10681 0.592, SC1004 S→W = 206.53×20/150 (1e−14).
  - 반박 [실행]: MN:17 "미터 조임과 시기가 겹치는 몫은 2,700–4,500 s −69.7"(10681 은 6,300–7,350 s 에도 g5–8), MN:154 "D1·D2 → 3.6배"(D1 만; D1+D2 약 5.8배 추론), MN:128 10484 끝 재고 <3 312/312(실제 66/312), W264:66 27개→26개, O1:23 "미터가 거의 풀린 뒤". 부분 수정: D2 0.54배 몫(N·S 74 %), D4 크기(녹색별 1.2–1.7배). 표현: "정확히 0"→반올림 수준, 14배 이상→약 14–17배, −78.7→−78.8, D3 괄호.
  - pass=false(쉬운 답 2번·결함 표 수치 정정 필요). 새 VISSIM·COM·러너·동결·재생·커밋·푸시·체크아웃·kill 0, 분리 트리 미생성. 런 폴더·frozen 쓰기 0. 봉인 시드·codex 64cf-s59/61/67 0. 다른 세션(codex 9a8320ec rolling_cea, 13:37~ cscript·VISSIM·python) 무접촉. 디스크 C 31.4 GB, D 341.5 GB.

## 2026-10-24 14:08 KST — METER_NEXT r2 마무리 시작 (VERIFY_NEXT 정정 C1–C9 반영)
- 입력 sha256 [실행]: METER_NEXT.md 221b8e4e…5a41(= r1), VERIFY_NEXT.md 49cc05f7…fa22, O1_RULE_RM_V3C3.md 7af4a16f…a6d5, W264_READ.md cb535361…1e01, O4_MERGE_10681.md fb178ef4…5407.
- r1 보관 [실행]: o1o4/METER_NEXT_r1.md(221b8e4e…), o1o4/O1_RULE_RM_V3C3_r1.md(7af4a16f…), o1o4/W264_READ_r1.md(cb535361…). C1·C5 는 O1, C9 는 W264 줄도 가리키므로 두 조사 문서도 r2 로 고침(반박 진술을 남기지 않기 위해).
- 점검 [실행, 가벼운 읽기만]: vnext/out/rm_prov.json 녹색 문자열 해독(v3c3-s41 RM_C10681 6,300–6,900 s g5, 7,050 g6, 7,200 g7, 7,350 g8; 10490·10484·10639 마지막 조임 T 6,000/5,700/4,500), vn_analysis.json 창 값(RM−NC3 s41 2,700–4,500 −69.75, 6,300–8,100 −59.29; V-A−NC3 같은 창 −1.64 / −58.58), out/o4_final_rows.csv(10484 끝 재고 <3 66/312, 중앙 3.72, 최대 8.79; 10681 312/312, 최대 |기울기·dNUF/dz| 1.6e−16).
- 할 것: FZP 0, 새 VISSIM·COM·러너·동결·재생·커밋·푸시·체크아웃·kill 0. 쓰기는 o1o4/ 와 D:/VISSIM_runs/20261001_v3c3/reports/k8/rmcause/o1o4/(보고서 사본)만. 디스크 C 31.4 GB, D 341.5 GB.
- 2026-10-24 14:15 KST METER_NEXT r2 끝 [실행].
  - o1o4/METER_NEXT.md r2 sha256 5f3c5ce80ea79e9afb6356471fd68dd5ad1ddf3cce04bc5644e00fe901c74cfe (r1 = METER_NEXT_r1.md 221b8e4e…5a41). §6 변경 기록 16줄.
  - o1o4/O1_RULE_RM_V3C3.md r2 1be05d8a9f741ae661e664986f108edc08dadd465ac994aa3031104c220dead3 (r1 7af4a16f…): C1(늦은 창 10681 g5–8), C5(419 대 572, 1.36배), §5.2 seg5 10681 녹색 범위, §2 첫 갈림 두 정의.
  - o1o4/W264_READ.md r2 8db20647d3174140ab145212fa7b6a8ed3d9ad2c64356d23fbf707ded0ad5a6e (r1 cb535361…): C9(27 → 26 결정).
  - O4·VERIFY_NEXT 는 바꾸지 않음. 목록 o1o4/SHA256SUMS_NEXT.txt sha256 b4ee79c6fa8cdd36003a3722992817242b554c0754a1bdbab6b37940e67f0155.
  - 반박 진술 R1(쉬운 답 2번)·R2(D1·D2 → 3.6배)·R3(10484 끝 재고 312/312)은 본문에서 지우고 변경 기록에만 r1 문구로 남김. grep 으로 본문 잔존 0 확인 [실행].
  - 사본: D:/VISSIM_runs/20261001_v3c3/reports/k8/rmcause/o1o4/ 에 10개 파일 복사, sha256sum -c 모두 OK [실행].
  - 새 VISSIM·COM·러너·동결·재생·커밋·푸시·체크아웃·kill 0. FZP 읽기 0. 분리 작업 트리 미생성. 런 폴더·frozen 쓰기 0. 봉인 시드·codex 64cf-s59/61/67 0. 디스크 C 32 GB, D 342 GB.

## 2026-10-24 14:20 KST — N12 시작 (D-K9-78 N1·N2, 코드 읽기 전용)
- 과제: N1 = SC1004 S→W·N→W 경계 movement 의 206.53 계열 값이 c20aff1d 에서 plant 서비스율까지 들어가는 file:line 사슬, 같은 값을 받는 다른 경계 movement 목록, K9-2 W 키가 SC109 에만 바꾼 것. N2 = 링크 129·70(미터 접근 = FW_W 진출 착지) 의 plant 표현(저수지 하나인지, 미터 큐 역류 가능한지).
- 방법: git show c20aff1d 로 r2c_n/n12/src 에 뽑아 읽기. FZP 스캔 0(기존 FZP 파생 표만 읽음). 새 VISSIM·COM·러너·동결·재생·커밋·푸시·체크아웃·kill 0. 쓰기는 r2c_n/ 아래와 이 LOG 만.
- 디스크: C 31.5 GB, D 341.1 GB [실행].

## 2026-10-24 14:26 KST — R2c 준비·사전 고정·발사 시작 (D-K9-79: 10681 미터만 켠 규칙 ALINEA 두 런)
- 과제: s31_v3c3rm10681·s41_v3c3rm10681 준비 폴더를 기존 rm 팔과 같게 만들되 규칙 미터 집합만 RM_C10681 하나로. 분석 계획(PRE_R2C.md)과 분석 도구 sha 를 발사 전에 고정한 뒤 WMI 분리 발사. 완료는 기다리지 않음.
- 디스크: C 31.5 GB, D 341.1 GB 여유 [실행]. PC 전체 VISSIM 1개(PID 53324, codex 9a8320ec rolling_cea, 무접촉) [실행].
- 읽기만: rm 팔 준비 폴더·발사 줄·rm_build, sim3 fast_fixed_profile.py(a05eb0c5)·diagnostic_profile.py(389d81c8)·fast_nc_run.ps1(269345da)·fast_nc_runner.vbs(bf07acda)·fast_fixed_profile_verify.py(914413913)·stage1 도구. sim3 수정 0. s37_v3c3rm 무접촉.

## 2026-10-24 14:31 KST — N34 시작 (D-K9-78 N3·N4, 읽기 전용)
- 과제: N3 = V-A 런 [T, T+450] 창에서 모형 RM_C10490 도착이 VISSIM 의 약 1.2배인 까닭 분해(결정점 1136 분할·사전값, 게이트 수요, 상류 movement 서비스, 링크 129 공유 흐름 vs FZP 실측). N4 = 규칙 RM 팔 s31·s41 에서 미터별(10639·10681·10490·10484, FW_W 4개) 명령 녹색별 실제 헤드 통과율(차로당) vs 모형 서비스 표·g×90.
- 계획: 새 FZP 스캐너 r2c_n/n34/tools/n34_fzp_scan.py 로 FZP 5개(V-A v3c3-s31/41/43, RM v3c3-s31/41)를 하나씩, 스캔마다 r2c_n/fzp.lock 을 배타 생성으로 잡고 끝나면 지움. WMI 분리·BELOW_NORMAL·PYTHONHASHSEED=0·python -B. 그 뒤 V-A 결정 JSON 3런 흐름 추출(n34_model.py, FZP 아님). 쓰기는 r2c_n/n34/ 와 이 LOG, 최종 r2c_n/N34_FLOWS.md 만.
- 안 함: 새 VISSIM·COM·러너·동결·결정/plant 재생·커밋·푸시·체크아웃·kill. 런 폴더·frozen 쓰기 0. 봉인 시드·codex 64cf-s59/61/67 0. 다른 세션 PID(VISSIM 53324, cscript 10992, python 34808 = codex rolling_cea; python 22948 = 이 워크플로 다른 에이전트) 무접촉.
- 디스크: C 32 GB, D 342 GB [실행].
- 2026-10-24 14:35 KST N34: 분리 사슬 WMI 발사(cmd PID 56036 → python n34_chain.py, BELOW_NORMAL, PYTHONHASHSEED=0, python -B). FZP 5개(V-A v3c3-s31/41/43, RM v3c3-s31/41)를 하나씩, 스캔마다 r2c_n/fzp.lock 배타 생성·해제. 그 뒤 V-A 결정 JSON 3런 추출. 도구 sha256: n34_fzp_scan.py 4e644837…2030, n34_model.py 748d40ce…23ef, n34_chain.py 0e1557c7…10bc8. 쓰기는 r2c_n/n34/ 아래만.
- 2026-10-24 14:36 KST R2c 준비 폴더 생성 끝 [실행]: `r2c_n/tools/build_r2c.py` (sha256 acdd600cdfeb8f67b3f7b7974a3a635bb620f17e50535c6b26aa0bab094a9baf) `all`. 먼저 스크래치 리허설(`r2c_n/rehearsal/`, 모두 통과) 뒤 실제로 돌림.
  - 새 폴더: D:/VISSIM_runs/20261001_v3c3/s31_v3c3rm10681/prepared, s41_v3c3rm10681/prepared. 각 58파일 = rm 팔 prepared 61파일 − rm 런이 만든 3개(network/baseline_s<S>_v3c3rm.err, _001.err, .results/1.db). 56개 바이트 같음. 다른 것 둘: rule_policy.json(meters 8개 → RM_C10681 1개, sha df8acd08 → 98887f2d), prepared.json(경로 54줄 + rule_policy 핀; s31 7d14dd25 → 6c54c683, s41 d556c865 → 1e944b1d). 망 이름만 baseline_s<S>_v3c3rm10681.inpx, sha 04630354…/e4953eaf… = rm 팔.
  - 정적 확인 `r2c_n/build/r2c_checks.json` 1e5f7275… 4항목 OK. 드라이런(-Execute 없음) `r2c_dryrun_receipt.json` c6e18d29… exit 0, rm 팔 dryrun_check 와 arguments 의 경로 3개만 다름. 빌드 영수증 c6ca754a…, 줄 차이 `prepared_diff_rm_vs_rm10681.txt` 1653faca…. 발사 줄 D:/VISSIM_runs/20261001_v3c3/launch_lines_rm10681.txt 8c528f8f…. D: 사본 D:/VISSIM_runs/20261001_v3c3/rm10681_build/ (SHA256SUMS.txt).
  - 방식 = 설정만(rule_policy 의 meters 선택). 코드 사본·수정 0. 나머지 7 미터는 COM 쓰기 0 = native OFF(NC3 와 같음). rm 팔은 900 s 에 8개 모두 GREEN 을 썼으므로, 그 7개는 rm 팔의 COM GREEN 대 이번 native OFF 차이가 남음(O1 §2 짝 확인: 첫 RED 전까지 같은 교통).
  - sim3 쓰기 0(새 __pycache__ 0, git 은 --no-optional-locks, worktree index mtime 09-23 그대로). VISSIM 시작 0(fast_nc_run.ps1 은 -Execute 없이만).

## 2026-10-24 14:43 KST — N5 기록 (W264 결정 JSON 이웃 검사 비용 읽기, 시작 약 14:22 KST)
- 과제: D-K9-78 N5. W264(codex ca181e84, 64cf-s29) 결정 JSON 의 1,200·1,650·1,800·1,950 s 이웃 검사 후보 비용, VSL 90 시작과 FW_E 묶음 조임이 같은 1,800 s 결정에 겹친 까닭(우연 대 모형 비용 구조), δ_merge 셀값·서비스 표.
- 방법: 결정 JSON 55개(action_000900 … 009000.json)를 python -B, PYTHONHASHSEED=0, BELOW_NORMAL 로 하나씩 읽어 r2c_n/n5/ext/ 에 요약 JSON 으로 뽑음(n5_extract.py). obs150/vsl_cohorts_*.json, 동결 트리 코드·plant 참조 파일 읽기만. FZP 읽기 0 → fzp.lock 안 잡음.
- 안 함: 새 VISSIM·COM·러너·동결·결정/plant 재생·커밋·푸시·체크아웃·kill 0. 런 폴더·D:/VISSIM-merge/frozen·동결 트리 쓰기 0. 봉인 시드·codex 64cf-s59/61/67 0. 다른 세션 PID(VISSIM 53324, python 34808 등) 무접촉.
- 디스크: C 31.5 GB, D 341.1 GB [실행].
- 2026-10-24 14:44 KST R2c 분석 계획 고정 (발사 전) [실행 sha256]:
  - `r2c_n/PRE_R2C.md` b3bf5a0c8148159479556326e78deaa3e07f253b84448a663d09f71edbf88fac (이후 바꾸지 않음).
  - 도구 `r2c_n/tools/`: r2c_scan.py 7cb45615cc656fbbf8de68b03b3a4ae4bb545ff4492e44ab3c6a719ea9cfd519, r2c_metrics.py ece90b129d793ac657ecbab3ddd741e52710f2a26edafba814f7f08a2ffcab2b, run_py.ps1 f3e3993559a5b802573f14e051974ca97ff89ad7a447db58d7c4690749713364 (= O1 판), build_r2c.py acdd600cdfeb8f67b3f7b7974a3a635bb620f17e50535c6b26aa0bab094a9baf, log_append.py 3a4e5ac84d81abef5baed7c2ef1dde541112c14e8a050c59c53802cd884cafb3.
  - 자체 시험 [실행]: r2c_metrics.py --standin-rm (R1 자리에 O1 RM 스캔) → R1−RM 0, R1−NC3 = O1 RM−NC3, 재현 점검 V5 모두 참; 출력 r2c_n/selftest/ (r2c_metrics.json dd654057…, r2c_tables.md 0674b8be…). r2c_scan.py 는 런 미완료에서 거부, 잠금 안 만듦. 이 시험은 기존 스캔 JSON 만 읽음(FZP 읽기 0).
  - 주 지표 = FW_E 본선 7링크, 같은 표에 옮겨 간 대기; 창 300 s 칸, 이른 2,700–4,500, 늦은 6,300–8,100, 전체 900–9,000; 비교 R1−NC3·RM−NC3·VA−NC3·R1−RM·R1−VA(같은 시드, 31·41); 미터 몫 = 창 합 a, b, c 와 a−b, a−c, a/b, a/c 보고만(문턱 없음).
- 2026-10-24 14:52 KST N5 끝 [실행].
  - r2c_n/N5_W264_JSON.md sha256 367473ea270daf48efc3a9d9e2d4e30299921c680f995897b3d6557503bafb13. 목록 r2c_n/n5/SHA256SUMS_N5.txt sha256 34312255e3765eb6d30ff2a0b8427ea03edd8552adf0e5e6f8c7332d6d00d18c (81줄, sha256sum -c 모두 OK).
  - 핵심: FW_E:tighten Δ 1,650 s 에 처음 음수(−0.0090; 그때 RM_C10480:tighten −0.0350 이 선택됨). 1,800 s 엔 RM_C10480 이 3블록 g2 라 조임 후보 없음 → FW_E:tighten −0.0311 선택. 모형은 1,500 s(블록 2)·1,650 s(블록 1·2)부터 VSL 90 을 봄(control_hold.py:57-66). 묶음 값은 B2 미터(10490·10484)뿐, 10639·10681 단독 0.0000. 열린 미터 기울기 900–1,800 s 정확히 0(g9 = g10). 같은 1,650 s 에 관측 B2 셀 22·23 밀도 25.4 → 49.7. 후보별 주인 분해는 기록 없음 → 모름.
  - 새 VISSIM·COM·러너·동결·재생·커밋·푸시·체크아웃·kill 0. FZP 읽기 0(fzp.lock 미사용). 런 폴더·frozen·동결 트리 쓰기 0. 봉인 시드·codex 64cf-s59/61/67 0.

## 2026-10-24 14:52 KST — N12 끝 (D-K9-78 N1·N2, 코드 읽기 전용)
- 산출: r2c_n/N12_CODE_PLANT.md sha256 1f630c3e851fc4e44afc254897ed40ea5ce4e8d77414677575fccb89c650d55c, 목록 r2c_n/SHA256SUMS_N12.txt b74136aef07badfa57cca78031078c992b5136cea3bce514449220f058940805. 도구 n12/tools/n12_caps.py d38a032e…a309, n12_validate.py 64c17a4e…680e [실행].
- N1 요지 [실행·읽음]: 206.53 = 330 × 184/294 (CFG:7823-7825 → RS:400 → ADP:3832-3836), 경계는 ADP:3860-3896 에서 차로 × 206.53, 실측 하한은 내부만(ADP:4355, :4588-4598). plant UFA:579-591 → UQM:730-764. SC1004 S→W 3.4422 대/450 s = 206.53 × 60/3600, N→W 3.6256·3.5339 = 206.53 × 63.197·61.6 s/3600. V-A 최종 경계 179 중 206.53 계열 165, plant 가 읽는 것 148(일반 루프 146·회랑 2). 재구성 검산: perimeter 187/66/121 일치, 런 기록 '이전 값' 14/14 일치. K9-2 W 는 SC109_W_SC108_to_E 619.59 → 5209.8 하나만. U4(v3b) 측정 23개 차로당 206.53/포화 0.105–0.164(중앙 0.109).
- N2 요지 [읽음·실행 .inpx]: 129 = in_SC1001_W(설정 1,237.8대), 70 = in_SC1004_W(lane plant 재구성 약 285.6대) 한 저장고. 미터 대기(점 대기열) → S_eff → 진출 포트(10491 38.58대 SA 지퍼, 10638 96.05대) → AFA:322-354 FW_W 셀 막힘 길은 있음. 진출 → 반대 방향 미터 흐름은 모형에서 0. VISSIM 기하는 착지-미터 출발 60.6 m(129 차로 1)·139.9 m(70 차로 1).
- 읽기만: git show c20aff1d(GWT8 D:/VISSIM-merge/sim3-n31-k8, head c20aff1d), V-A v3c3-s31 action_001950.json(fd5763de…555e)·s41/s43 action_004950.json metadata, U4 표(22384c00…292b), o1o4/vnext/out/split_va_s31.json, 동결 .inpx(3de889f0…). FZP 스캔 0, 새 VISSIM·COM·러너·재생·커밋·푸시·체크아웃·동결·kill 0. 런 폴더·frozen 쓰기 0. 봉인 시드·codex 64cf-s59/61/67 0. 다른 세션 프로세스 무접촉.
- 주의: 14:20 시작 항목의 시각을 고칠 때 LOG.md 를 한 번 통째로 다시 썼습니다(내용 변경은 그 줄의 시각뿐). 디스크 C 30.9 GB, D 340.1 GB [실행].- 2026-10-24 14:44 KST R2c 발사 [실행] (계획 sha 기록 14:44 뒤): `r2c_n/tools/launch_r2c.ps1` (sha256 0a8922c7e03037aaa989573a6622d8aa597b3f1b1db74233e3cd65a4f6866298) 로 launch_lines_rm10681.txt 두 줄을 Invoke-CimMethod Win32_Process Create, CurrentDirectory D:\VISSIM_runs\20261001_v3c3, 20 s 간격. 기록 D:/VISSIM_runs/20261001_v3c3/wmi_launch_lines_rm10681.txt (sha256 369c4103…).
  - s31_v3c3rm10681: 14:44:26 KST, RV=0, cmd PID 40592 → powershell 54900 → cscript 5456, VISSIM 41832(14:44:27, 창 제목 baseline_s31_v3c3rm10681.inpx). 발사 전 VISSIM 1개.
  - s41_v3c3rm10681: 14:44:46 KST, RV=0, cmd PID 1316 → powershell 36928 → cscript 21932, VISSIM 48156(14:44:47). 발사 전 VISSIM 2개.
  - 다른 세션 VISSIM 53324(codex 9a8320ec rolling_cea)와 그 python 은 세기만 함. 지금 PC 전체 VISSIM 3개.
  - 14:52 확인 [실행]: 두 런 모두 decision_900·1050 생김, decision_failure 0, 900 s 결정의 meters = [RM_C10681], 이벤트 = 900 s SC 9106 GREEN 하나. 진행 sim 1,090 / 1,045 s. 속도는 rm 팔과 비슷(rm 팔 1,000 s 에 6.5–6.7분, 이번 6.4–6.8분).
  - 끝 예상: rm 팔 104 / 110분 기준 약 16:30 / 16:35 KST(범위 16:25–16:50).
  - 계획·도구 D: 사본 D:/VISSIM_runs/20261001_v3c3/rm10681_build/plan/ (SHA256SUMS.txt). 디스크 C 30.9 GB, D 340.3 GB [실행].
  - 내가 띄운 것 외 프로세스 kill 0. sim3·기존 런 폴더·frozen 쓰기 0. 봉인 시드·s37_v3c3rm 무접촉. 커밋·푸시·동결·체크아웃 0. FZP 읽기 0(이번 단계).
- 2026-10-24 14:53 KST N34 끝: r2c_n/N34_FLOWS.md sha256 4b5677b7bfa293cef0491f6c1ce49c499340463edb9616b2de7ab9f85dd6e3da, 목록 r2c_n/n34/SHA256SUMS_N34.txt sha256 7282f0ae3be67d111a14f4870d4dc54f17939132c840473140f7b7951fee353a(43파일) [실행].
  - 사슬 끝(CHAIN_DONE 14:41:52): FZP 5개 각 26–30 s, 잠금 r2c_n/fzp.lock 스캔마다 잡고 해제(14:35:38–14:38:06), V-A 결정 JSON 3런 각 70–83 s. 내 PID(54612·56036·자식 8개) 모두 종료, 잠금 파일 없음 [실행]. 스캔 FZP sha 가 VN·O4 값과 5/5 같음.
  - N3 [실행]: V-A 3시드 156창 모형 RM_C10490 도착/129→10490 진입 1.254(창별 중앙 1.258). 게이트 1.007배, 1136 몫 2/9 vs 0.223. 차 +2,890 중 +2,869(99 %)가 파이프라인 항: 모형 ≈ S3_0 + 2/9·G(모형 진입 지연 34 s 상수), VISSIM 삽입→10490 중앙 135 s 라 창 끝 경로3 재고 S3_1 24.8대/창. 첨두 1.33–1.35(통행 189–200 s, 링크 32 에 10482행 저속 16–22대). onE movement 무신호·서비스=도착. V-A 링크 129 저속 0.07대. 진단 gate_onramp_beta 는 실효 분할과 무관해 보임(열림).
  - N4 [실행]: 정지 대기+뒤 안 막힘 블록. 10490 g2/3/4/5 = 360/600/696/984, 10484 = 360/480/708/960 veh/h/차로(표의 1.34–1.68배; g2 26블록 모두 주기당 1대). 10681 차로 2 g4/5/6 = 648/816/840(1.25/1.20/1.00배), g7+ 합류 묶임. 10639·FW_W·g6+ 는 대기 블록 없어 알 수 없음. s41 10490 2,400–4,200 s 572 veh/h 재현.
  - 결과를 본 뒤 덧붙인 서술용 분해(n34_n3_static.py, 고정 몫 2/9)는 문서에 그렇게 표시함.
  - 새 VISSIM·COM·러너·동결·재생·커밋·푸시·체크아웃·kill 0. 런 폴더·frozen 쓰기 0. 봉인 시드·codex 64cf-s59/61/67 0. 다른 세션 프로세스 무접촉. 디스크 C 31 GB, D 341 GB.
  - 주의: 14:35 줄의 발사 시각은 처음 14:38 로 잘못 적었다가 sed 로 고쳤음(이 LOG 파일을 한 번 다시 썼음).

## 2026-10-24 16:29 KST — R2c 두 런 끝, 분석 시작 전 확인
- 기다림: 14:54–16:27 KST, 약 9분 간격 읽기 전용 확인(`r2c_n/work/poll_r2c.ps1`). 5분 무진행 0회, 재발사 0회, kill 0회 [실행].
- s31_v3c3rm10681: run.json completed true, exit_code 0, error 없음, fixed_profile_validation_exit_code 0, 시작 14:44:27 → 끝 16:22:56 KST(98.5분). fixed_validation passed, event_readbacks 811. 결정 54, decision_failure 0. FZP `run/vissim_eval/baseline_s31_v3c3rm10681_001.fzp` 1,142,406,030 B [실행].
- s41_v3c3rm10681: completed true, exit_code 0, error 없음, 검증 exit 0, 14:44:47 → 16:27:25 KST(102.6분). fixed_validation passed, event_readbacks 1,021. 결정 54, decision_failure 0. FZP 1,181,381,273 B [실행].
- 내 PID(41832·5456·54900, 48156·21932·36928) 모두 스스로 끝남. PC VISSIM 1개 남음(다른 세션 53324, 무접촉).
- 사전 고정 확인 [실행 sha256]: PRE_R2C.md b3bf5a0c…8fac = LOG 14:44 값. r2c_scan.py 7cb45615…d519, r2c_metrics.py ece90b12…ab2b, run_py.ps1 f3e39935…3364, build_r2c.py acdd600c…a9baf, log_append.py 3a4e5ac8…cb3 모두 고정값과 같음.
- 다음: PRE §6 순서대로 run_py.ps1 로 r2c_scan.py(FZP 잠금) → r2c_metrics.py. 인자 없음(재발사 없음).
- 2026-10-24 16:45 KST R2c 분석 끝 (PRE_R2C §6 순서 그대로, 인자 없음) [실행]:
  - 16:28:18 run_py.ps1 → r2c_scan.py (WMI PID 34628, BelowNormal). fzp.lock 배타 생성 → R1 두 FZP 차례로 각 17.5 s → 잠금 지움(16:28:56 에 잠금 없음 확인). 스캔 sha: r1_s31 scan 7d12bd3f…4066 / uninserted 4156b985…cca1, r1_s41 scan 0d51425d…8cc9 / uninserted ce41a987…03fc. 행 6,672,558 / 6,894,516, 1,799 프레임, zone_policy_match true.
  - 16:29:03 run_py.ps1 → r2c_metrics.py (PID 50864). out/r2c_metrics.json 1e2df9fc…a6a6, r2c_tables.md ef3f3b60…b285, r2c_bins300.csv 93f4b09f…8035, r2c_zone300.csv c6e4b77f…cf7d, r2c_scan_log.json 9ce90c26…9bfb. stderr 비어 있음.
  - 유효성 V1–V5 모두 참(V3: s31 R1/NC3 2,510.1 ≥ 2,409, R1/RM 2,500.1 ≥ 2,408; s41 2,350.1 ≥ 2,259, 1,690.1 ≥ 1,509. V4 T = 3,300 / 1,950. V5 70값 최대 차 0.0, s41 창 값 VN 0.1 안). fixed_events 는 SC 9106 만(s31 406/405, s41 511/510).
  - 도구 상수 하나: r2c_metrics.py:52 O1_METRICS_SHA 가 63자(…40d792… ← 실제 …40da792…). checks.o1_metrics_sha_pinned false. 실제 파일 sha = O1_RULE_RM_V3C3.md:269 값, 파일 시각 12:42 < 계획 14:44. selftest 에서도 false 였음(그때 못 봄). 계획·도구 안 고침.
  - 핵심 숫자 ① FW_E 본선 7링크(같은 시드 짝, 2시드): 늦은 창 s41 a=R1−NC3 −50.4, b=RM−NC3 −59.3, c=VA−NC3 −58.6 (a/b 0.85, a/c 0.86); s31 +1.8 / −5.7 / +5.2. 이른 창 s41 −21.0 / −69.8 / −1.6 (a/b 0.30); s31 +13.1 / −6.7 / −14.8. 전체 R1−NC3 +36.9 / −82.0, ④ +13.7 / −244.7, Ω 밖 (a) −13.2 / −119.6, 1099 −37.1 / −89.6 (RM s41 +644.6). s41 늦은 창 seg5 는 NC3 만 52–70 km/h, R1·RM·V-A 91–110.
  - 보고서 r2c_n/R2C_RESULT.md sha256 4bbe03b7cac35f8b4e57dc51a0a9da4d6d95bedaa7b26d4c3917fd11faa7f441. D: 사본 D:/VISSIM_runs/20261001_v3c3/reports/k8/rmcause/r2c_n/ (27파일, SHA256SUMS.txt sha256 19478a723bea16146228c152580a0487e9dd7070ca093a4c8d3202ae8dbbd76b, sha256sum -c 27/27 OK). 보조 스크립트(work/r2c_report_extract.py, make_result_tables.py, merge_result.py)는 out/ 과 R1 fixed_events.csv 만 읽음, 계획 밖 분석 0.
  - 새 VISSIM·COM·러너·재생·커밋·푸시·동결·체크아웃·kill 0(이 단계). 기존 런 폴더·frozen·sim3 쓰기 0. 다른 세션 VISSIM 53324·python 무접촉. 봉인 시드·codex 64cf-s59/61/67 0. 디스크 C 31 GB, D 337 GB.

## 2026-10-24 17:03 KST — 종합: METER_NEXT2 + K9-3 설계 초안 (D-K9-77·78·79 뒤)
- 쓴 파일 [실행 sha256]:
  - r2c_n/METER_NEXT2.md sha256 95be62750085f4e7018e62f183d071ee0f27fc52b1804cceeffb40f9bc4d9590
  - r2c_n/K9_3_DESIGN_DRAFT.md sha256 57fc50f2d78b1a33e5d3ed070a1b9fa00a9ead2689a8b2b104a906c9b05416c4
- 읽은 입력: N12_CODE_PLANT(1f630c3e…), N34_FLOWS(4b5677b7…), N5_W264_JSON(367473ea…), R2C_RESULT(4bbe03b7…), PRE_R2C(b3bf5a0c…), METER_NEXT r2(5f3c5ce8…), O4(fb178ef4…), VERIFY_NEXT(49cc05f7…), K9_2_DESIGN r2(1100f7af…), GATES_K92B1(449b361e…), K9_1_J1_NOTES(7f92eaec…).
- 이 단계에서 새로 읽은 것(읽기 전용) [실행]: `git show c20aff1d:` RS·ADP·UFA·UQM·RCC·PRB·link_predictor·CFG 해당 줄, 동결 v3c3 .inpx(3de889f0…1c2e) 결정점 1135·1136·1137, 커넥터 10625·10629·10633, 링크 46·66 헤드, U4 표(22384c00…) 66|p2·46|p1 행.
  - 결정점 1135: 경로 2 → 10646 relFlow ""(1), 경로 3 → 10773 자유 ""(1), 경로 4 → 10681 "2 0:3" → 행 (10681 0.6, 10646 0.2, 자유 0.2). 지금 표(0.1667, 0.5, 0.3333). RCC:995 경로 계약과 같음.
  - 커넥터 10625(N→W)는 링크 46 차로 1 의 949.21 m 에서 갈라짐, 차로 1 헤드 90030891 은 953.16 m, 10625 위 헤드 없음, 충돌 구역 넷 PASSIVE.
  - 커넥터 10633(S→W)은 헤드 90030875(2,658.617 m, v3b U4 와 같은 위치) 뒤에서 갈라짐.
  - U4 66|p2 F2 1,807.4 / s_unimpeded 1,919.7(measured), 46|p1 default(제안 1,850).
- 정정 셋(쓰는 중, 내 문서 안): RCC:997 → :995, inpx sha 끝자리 오기, 녹색 문자열 해독(s31 RM 팔 g9 는 6,900 s). G-K0 plant 표본에서 F 블라인드 런 v3c3-s47 을 뺌.
- FZP 읽기 0(잠금 안 잡음). VISSIM·COM·러너·재생·커밋·푸시·동결·체크아웃·kill 0. 런 폴더·frozen·sim3 쓰기 0. 봉인 시드·codex 64cf-s59/61/67 0. 디스크 C 31 GB, D 336 GB.

## 2026-10-24 17:11 KST — VERIFY_N2 시작 (METER_NEXT2·K9_3_DESIGN_DRAFT 재검증, 새 스크립트)
- 새 도구 r2c_n/verify_n2/tools/v2_scan.py (sha256 9d1ba3dd7fb91a3a781e271ad1ba59bd2cbb9f040b70ec251515b5cfdbb591fb). stage1·r2c·o1·n34·vn 도구 import 0.
- 17:11:43 KST WMI 분리 발사 PID 27380 (BelowNormal, PYTHONHASHSEED=0, python -B): FZP 8개(NC3·R1·RM·V-A × v3c3-s31·s41) 차례로, FZP 마다 r2c_n/fzp.lock 배타 생성 → 읽기 → 지움. 출력 r2c_n/verify_n2/out/ 만.
- 시험: RM s41 FZP 앞 40 MB 를 잠금 잡고 tmp 로 복사해 스캐너 시험(0.7 s), 복사본·시험 출력 지움.
- VISSIM·COM·러너·재생·커밋·푸시·동결·체크아웃·kill 0. 런 폴더·frozen 쓰기 0. 봉인 시드·codex 64cf-s59/61/67 0. 디스크 C 31 GB, D 336 GB.
- 2026-10-24 17:40 KST VERIFY_N2 끝 [실행]:
  - 보고서 r2c_n/VERIFY_N2.md sha256 abf5219b11ecd3c8acc75ee775e62aa283b6c892af5cf7253a607f4a4b1c53e9. 목록 r2c_n/verify_n2/SHA256SUMS.txt sha256 e3e85d1c4949111aa070bcfd2d8fc2f22f444220fa4164b6d7980fee43066267 (53줄, sha256sum -c 모두 OK).
  - FZP 읽기: v2_scan WMI PID 27380(v3c3 8개, 17:11:43–17:14:23) · PID 33100(64cf-s29 W264·NC·VSL 3개, 17:20:57–17:22:00), v2_routes 포그라운드(V-A v3c3-s31 1개, 17:28, 14.2 s). FZP 마다 r2c_n/fzp.lock 배타 생성·삭제, 끝에 잠금 없음 확인. NC3 FZP 의 1135 경로 번호는 세지 않음(K9-3 P0 C-1 사전 표본 보호).
  - 요지: R2c ① 짝 차이·옮겨 간 링크 줄 보고와 0.001 안 같음, 미삽입·④·Ω 밖 0–2.6 차; 미터 명령 SC 9106 만·녹색 문자열 동일; 206.53 사슬·링크 129 표현 코드 일치; 녹색 대 통과 19점 동일; W264 Δ 5결정 동일; D1·D2 진술·값 일치, V-A s31 FZP 1135 경로 몫 0.201/0.208/0.592. 정정 R1(METER_NEXT2 §3.1 5단계 "표 g9 = g10" 은 우리 plant 아님), 근거 부족 U1–U3(첫 갈림 정의, 148·165 개수 미재계산, s47 블라인드 표기에 U4 v3b-s47 포함), 인용 보충 C1–C4. 무게 있는 주장의 반박·근거 부족 0.
  - 새 VISSIM·COM·러너·재생·커밋·푸시·동결·체크아웃·kill 0. 런 폴더·frozen·GWT8·sim3 쓰기 0. 봉인 시드·codex 64cf-s59/61/67 0. R-obs v3c3-s47 열기 0. 다른 세션 VISSIM 53324·python 38636 무접촉. 디스크 C 31 GB, D 336 GB.

## 2026-10-24 17:49 KST — 마무리: VERIFY_N2 정정 반영 (METER_NEXT2 r2, K9-3 설계 초안 r2)
- 앞 판 보관 [실행 sha256]: r2c_n/METER_NEXT2_r1.md 95be62750085f4e7018e62f183d071ee0f27fc52b1804cceeffb40f9bc4d9590, r2c_n/K9_3_DESIGN_DRAFT_r1.md 57fc50f2d78b1a33e5d3ed070a1b9fa00a9ead2689a8b2b104a906c9b05416c4 (VERIFY_N2 대상 sha 와 같음).
- 새 판 [실행 sha256]: r2c_n/METER_NEXT2.md acebbe738677eebc1cbb36b9efca2d9e905bdc9b2bddc8d5b229563cbc43b33c (r2, 변경 기록 §6), r2c_n/K9_3_DESIGN_DRAFT.md 549f20e2507cc4ebe9dda97e6fd95ebb745582732362fe5ffe7c3cdba14f89b4 (초안 r2, 변경 기록 §11).
- 반영: R1(§3.1 5단계 "표 g9 = g10" 지움 → W264 표 대 우리 표 g9 3.69/g10 4.2, MC:87 a2-5·MC:88 a3), U1(첫 갈림 두 정의), U2(148·165·23 은 N12 인용 표지), U3(§6.8 블라인드 문장 지움 → U4 66|p2 per_seed v3b-s47 1,936.2 노출 표기, P0-6·Q8·§0·§9), C1(RS:113·:244-245·KB/K9_2_DESIGN.md:71,144), C2(× 5.84 → 약 917, 0.94; VERIFY 문구 916 은 버림값이라 917 로 적음), C3(RS:562-595, ADP:8523-8526, 함수 ADP:8472-8527), C4(g6 840 = RM 팔 3블록, 5블록 864). 보강: 1135 경로 몫 V-A v3c3-s31 0.201/0.208/0.592, 8망 블록 해시, 배포 무신호 증거, 재구성 차 범위.
- R2C_RESULT.md 는 안 고침: U1 첫 갈림은 사전 고정 도구 r2c_metrics.py(ece90b12…) 의 정의로 계산돼 PRE_R2C 에 비추어 틀린 곳이 아님. PRE_R2C 무변경(b3bf5a0c…).
- 이번 단계 읽기 전용 확인 [실행]: git show c20aff1d (CFG:7522-7536, RS:111-116·242-249·428-432·560-597, ADP:3830-3837·8472-8528, UQM:755-768), KB/K9_2_DESIGN.md:71·144, U4 표 22384c00… groups[20] per_seed, 배포 무신호 증거 43247697…fa16, 산술. 스크립트 r2c_n/final_n2/chk_final.py·chk_final2.py (출력은 화면만).
- D: 사본 D:/VISSIM_runs/20261001_v3c3/reports/k8/rmcause/r2c_n/ (새로 넣은 것: 문서 9개 + verify_n2·n12·n34·n5·final_n2 폴더; 기존 파일 덮어쓰기 0). 목록 SHA256SUMS_FINAL.txt sha256 c43e0667bd32099c8d31d66f15eea1dcb95b52593ebda858093e6488a7e30112, D: 에서 sha256sum -c 244/244 OK.
- FZP 읽기 0(잠금 안 잡음). VISSIM·COM·러너·재생·커밋·푸시·동결·체크아웃·kill 0. 런 폴더·frozen·GWT8·sim3 쓰기 0. 봉인 시드·codex 64cf-s59/61/67 0. R-obs v3c3-s47 자료 열기 0. 다른 세션 프로세스 무접촉. 디스크 C 30.8 GB, D 335.4 GB.
