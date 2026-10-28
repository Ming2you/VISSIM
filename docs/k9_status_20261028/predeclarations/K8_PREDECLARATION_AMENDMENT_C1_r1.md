# K8 보충 C1 (Declare 판) — C 묶음 1 이식: 목적 경계 Ω701(접근로 66링크) + 미터 결정 묶음(이웃 검사·조합, cap 3, 녹색 0 금지, 저장 보호 0.9 + 운영 seed·held 유지, FW_E 미터 4개 머리 서비스 표)의 키·값·자리·증거, P0·미니 탐침, 커밋 관문 G-K0–G-K5a/b·G-RR, 오프라인 재생 R, 판정 단계 c1t(J·F 보고만), STOP, 퇴행 막기 숫자, 고정 목록, 비용 (2026-10-27)

- **상태: Declare 판.** 설계 초안 r2 `CP/C1_DESIGN_DRAFT.md`(sha256 `c32e1006a2a2c4084af9f77b615739dc51a6fb8a7768207f40bf461f742c2816`)의 ⟨Q1⟩–⟨Q19⟩ 와 종합 r2 `CP/C_PREP_RESULTS.md`(`4b58fb4e09a72a826c86975bccfcdb5ed2f67848b3e5c2556c64c6179c51c3ca`) §2.2 의 ⟨Q20⟩–⟨Q26⟩ 를 사용자 결정 D-K9-94("권장안 일괄")대로 모두 채운 판입니다. 빈 결정 칸은 없습니다. 설계 대비 바꾼 곳은 §16 에 모두 적었습니다.
- **쓸 때 상태** [실행 2026-10-27 10:06 KST]: GWT8 head = `c20aff1d7bf0c432cb4f20e2922bd406d857aa5d`(브랜치 `claude/k92-b1-20261016`), `git status --porcelain` 0줄, `claude/c1-port-*` 브랜치 없음, C1 스크래치 뿌리 `D:/VISSIM-merge/k8_gate_trees/c1` 없음, `heavy.lock` 없음. P0·탐침·관문·커밋·재생 데이터 0개. PC 의 python·VISSIM 프로세스 0. 디스크 C 25 GB, D 223 GB.
- **고정 방법**: 이 파일의 sha256 을 `SP/K8_PREDECLARATION_AMENDMENT_C1.md.sha256` 과 `C1D/LOG.md` 에 적습니다. 반박 검토(ReviewDeclare)가 글을 고칠 수 있습니다. 고치면 이 판을 `SP/K8_PREDECLARATION_AMENDMENT_C1_r1.md` 로 남깁니다. 검토가 끝난 판의 sha256 을 고정점 파일 `C1D/AMENDMENT_C1_FIXED.md`(64자)에 적은 시각이 **고정 시각**입니다. 고정점에 적힌 sha 와 다른 보충 C1 로는 어떤 단계(P0·탐침·브랜치·커밋·관문·재생·판정)도 하지 않습니다(S-C1-1).
- **구속**: 보충 1–34 의 규칙·식·값·문턱·관문은 모두 그대로 구속합니다. COMPARE_RULE_B·PINS_B 는 바꾸지 않습니다. 이 보충은 C 묶음 1(이하 C1)만 다룹니다. K9-3(D1·D2)은 보류 그대로입니다(D-K9-91·94).
- **표시**: [실행] 이 Declare 가 읽기 전용 명령·작은 스크립트로 확인 · [읽음] 문서·코드·설정에서 확인(다른 보고서가 [실행] 으로 낸 값을 옮긴 것 포함) · [추론] 시험하지 않은 판단 · [계산] 이 문서의 산술.
- **말 규칙**: 판정 낱말은 쓰지 않습니다. 관문 결과는 PASS / FAIL / 보류 / INCOMPLETE 와 숫자로만 적습니다. 보고만 하는 항목은 "보고" 라고 적습니다. 시드는 망 접두로 적고(v3c3-s31 등) 평균 내지 않습니다. Ω 숫자는 늘 ④·Ω 밖과 같은 줄·표에 둡니다. ④b 는 첫 관측 차분이 주 값입니다. 64cf 숫자에는 "다른 망, 한 시드" 를 붙입니다.

## 줄임말 (처음 한 번만 풉니다)

- **경로**: SP = `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8`, CP = `SP/c_port`, **C1D** = `CP/c1`(이 보충의 LOG·선언 참조 바이트·도구), CH = `SP/codex_handoff`, KB = `SP/k92/bundle1`, KV2 = `KB/k92_vb2`. GWT8 = `D:/VISSIM-merge/sim3-n31-k8`. **TC1** = `D:/VISSIM-merge/k8_gate_trees/c1`(C1 스크래치 뿌리). **RC1** = `D:/VISSIM_runs/20261001_v3c3/reports/k8/c_port/c1`(보고 사본). LOCK = `D:/VISSIM-merge/k8_gate_trees/heavy.lock`.
- **트리**: CX = `D:/VISSIM-merge/k8_gate_trees/codexhandoff/a49981ff`(codex 인계 HEAD a49981ff, 읽기만). FRZ_B1 = `D:/VISSIM-merge/k8_gate_trees/codexhandoff/b1/frozen/sdmpc31_a49981ff_202610261410`(B 런 동결 트리, 읽기만). B0F = `FRZ_B1/diagnostics/b0_v3c3`. OU = GWT8 의 c20aff1d(줄 번호는 모두 `git show c20aff1d:` 기준).
- **런**: V-A = `D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s{31,41,43}`(우리 묶음 B1 폐루프). R-obs = `D:/VISSIM_runs/20261001_sdmpc31_v3c3/sdmpc31_v3c3_nc_s{31,43,47}`(v3c3 무제어 VISSIM 에서 결정을 계산만 한 런). B = `D:/VISSIM_runs/20261026_codex_b_v3c3/s{31,41,43}/sdmpc`(이름 `sdmpc31_sdmpc9000_s<시드>`, codex 제어기 폐루프). NC3 = `D:/VISSIM_runs/20261001_v3c3/s{31,41,43}_v3c3nc/run`(v3c3 무제어). 모두 읽기만.
- **코드 약칭**(모두 `evaluation/controllers/`): SD `sdmpc.py`, SEQ `sdmpc_sequence.py`, PRB `physical_ramp_branches.py`, LPR `lane_plant_runtime.py`, RS `runtime_setup.py`, AR `area_runtime.py`, CAO `control_area_objective.py`, ADP `vissim_stackelberg_adapter.py`, **C1M** = 새 모듈 `c1_port.py`. CH_H = `diagnostics/demand_sweep/user_native_20260914/metanet_calibration_v1/canonical_harness.py`. PN = codex `diagnostics/repin_v3c3_review_20261001/urban_area263/prepare_next.py`.
- **설정**: OUC = OU `diagnostics/sdmpc_n31_20260924/config_n31_v2.json`(`c8e3ee2c99b66c255b2279f0aa18eaafc18d4c7689e59e260109fac3b7d71866`, V-A 배포 튜닝). SAF-K91 = OU `…/config_n31_v2_stopline_observed_full_k91.json`(`5f0d0e40a39e44b3c7601f23177afbad8c2eee23d4421626482f2244a86c3341`). CFG_B = `B0F/config_b0_v3c3.json`(`729640af754a90c8d7fbe8f81577b27bae02b86f1d504e18333c0fc99717f983`).
- **기구 이름**(설계 §2.1 그대로): M0 목적 경계 Ω701, M1 이웃 검사 + 조합 1회, M2 cap 후보 3, M3 녹색 0 금지, M4 저장 보호 0.9, M4a 운영 seed 투영, M4b held 유지, M5 FW_E 미터 4개 머리 서비스 표.
- 이웃 검사 = codex 미터 결정의 유한 후보 검사(미터마다·고속도로 묶음마다 3블록 "가장 조임 / 가장 풂" 계획을 전체 모형으로 채점). 조합 = 따로 이로운 후보 가운데 겹치지 않는 것을 한 번 묶어 다시 채점. cap 후보 = 리더가 시험하는 NP 상한 수. NP = 보호망 순유입 상한. 저장 보호 = 미터 머리 앞 저장이 90 % 차면 그 결정의 녹색 하한을 올리는 규칙. 운영 seed = 직전 명령을 새 하한 안으로 미터 축만 자른 시작점. held = 직전 실행 명령. 머리 서비스 표 = 녹색 초별 미터 방류(대/주기). g = 10 s 주기 중 녹색 초.
- SDMPC = 이 계열 분산 모형예측제어기. plant = 그 안의 교통 예측 모형. PFO = 첫 단계 소유자별 자기 비용 따뜻한 시작. 재생 = 기록된 상태로 제어기만 다시 돌림(VISSIM 0). 연쇄 재생 = 재생 출력을 다음 결정의 직전 명령으로 이어 쓰는 재생. plant 잡 = 기록 행동을 그대로 두고 plant 만 굴리는 오프라인 계산. 정책 토큰 = `token(policy)`(OU SD:24-25, :527, :958), policy = `cfg.network.sdmpc_options`(OU SD:543).
- Ω635 = 우리 목적 영역(635링크). Ω701 = codex 목적 영역 = Ω635 + 신호 17곳 접근로 66링크(도로 35 + 직접 커넥터 31). ④a = 망 전체 링크 체류(veh·h), ④b = 미삽입 대기, ④ = ④a + ④b, Ω 밖 (a) = ④ − Ω, (b) = ④a − Ω. OUTW = 예측 지평 450 s 의 Ω 밖 모형 대기. ① = FW_E 본선 7링크.
- SG = 신호 그룹, SC = 신호 제어기. **SG2 = SC1001 EBT**(동쪽행 직진), SG5 = EBL. GREEN 만 = 노랑·전적색을 뺀 녹색 초.
- U·B·G-K0–G-K5·G-RR·R·J·F·c1t = 이 보충의 관문·단계 이름(§6–§9). RG = 퇴행 막기 숫자(§13). S-C1-n = STOP 규칙(§12).

---

## 0. 근거 문서·코드·설정 (sha256) [실행 2026-10-27, 고정 목록 `C1D/declared/PINS_C1_DECLARE.sha256` = `ad84aa2f64754ed8e87a4a8834845520585ce1b6e377313621ba49c057fe3a28`, 53줄, `sha256sum -c` 53/53 OK]

| 대상 | sha256 |
|---|---|
| 결정 기록 `SP/K9_1_J1_NOTES_20261013.md`(D-K9-91~95 포함) | `bbfe77b087bf41c6ec7810b145d45802cc36efbad88622a09c6737f4467a8863` |
| 설계 초안 r2 `CP/C1_DESIGN_DRAFT.md` / 종합 r2 `CP/C_PREP_RESULTS.md` | `c32e1006a2a2c4084af9f77b615739dc51a6fb8a7768207f40bf461f742c2816` / `4b58fb4e09a72a826c86975bccfcdb5ed2f67848b3e5c2556c64c6179c51c3ca` |
| `CP/READBACK_METER.md` / `CP/INPUT1099.md` r2 / `CP/VSL_OFFLINE.md` r2 / `CP/VERIFY_C_PREP.md` | `2fd9863934f93d09341e84df45f7c67cc404e0c4e97dcb85ed1ec465bbd7f980` / `c89011d8d1d7b3a45fea46f2622d87930e6f0e361969e4dae219e418b6d54274` / `a8ff255ecf5b20717c16b7c6bbb45e388810fa3d8bef47ef23e686a759a5d0ba` / `c83130bb4200f417e236be9799f1bb8ece68bacd61c666b58ad9d7306a44a004` |
| `CH/R_MECH.md` / `CH/b0/B0.md` r2 / `CH/B_RESULTS.md` r2 / `CH/VERIFY_B.md` / `CH/b/COMPARE_RULE_B.md` | `2fc879d62760621f9e40df92774fe4f74eb29fc9ce8edaf08360d3eaab0434e5` / `11fa75788e5457f95ab20a43ca2287e663f0390bef67940bcfb66dd8368c86bc` / `152a2f6fe0fd6c5cfd1462ba7d7e444cd13a6bd0ba2554874d07a1390a8209f9` / `f2851f8b53f026ada64f52e51d877b8c0ddc7ac3bbaf7f19cd27097c21462104` / `f902f7f0013bed0a0eb5dec27818e2bda4851995eae235130b7cb241e8b28f0c` |
| `SP/k92/va/analysis/VA_REPORT.md` r3 / KV2 연쇄 구동기 `vb_chain.py`(꼴 원본) | `b57022e651adeefcaf1484993c20fd940b2e13012f0437e3a5b6c5ad6a20fc1b` / `87b89ce48b6552b4967cc5416d2e56d5f9f6d20d887d9997385df4f1be521322` |
| 보충 21 / 24 / 27 / 29 / 32 / 33 / 34 | 전체 64자는 표 아래 첫 줄 |
| OU 블롭(`git show c20aff1d:` 바이트) SD / PRB / LPR / RS / AR / CAO / SEQ / ADP | `352701a08b10628511119ff188a7cbcc1b577977f3445b648aba0dc2742c19a4` / `08cb370d20fb727c77ef1069a07869faf86fb583e83cf92fbf0727d0e4d39778` / `493a5bf2e026c1b7bfeb1b3915dddf5307ac85c9b9f4ac5255d0eb72ad43ac35` / `70cca680ef9f5dd84ee506ff8857712466f3779039289ca79adadc3d8f1eceba` / `2c7cccdf01e8bcdbc2d0f26dc9fed59dbe2a5b41d52ab0512ba2e9370124a5bc` / `2c21cd8cdeab50cba81a21321abccdcbdb1ea4c5f8f27977ecb61e589f52ad60` / `d96a611c590336a6bc96892242fbddc984ea75d85a9f51b5b71a65f7cb5dc2c4` / `e616ade51ac7d5d506a6bf789d268662c3212ec87627a6eae72ae6039d7bb213` |
| CX SD / PRB / LPR / SEQ (= FRZ_B1 같은 sha) | `5c1ba251a3526cafa6574459e23627e59cb96e9373ff7d1c5588bcdde3c3a0c0` / `0ab140ac0967348b1b475d06668965284ac2170a93a7ee963cbd80b22c4dc966` / `d774daee3ae12a58f76e660b3dc0ea919f7187e39c625000205ba57dc0cb9563` / `c5004c7ad5fb8d509322fc09881117a34e47c4ccc6ac9f36eead6557e03aedf6` |
| CX `diagnostics/build_control_area_membership.py`(빌더, `expand_controlled_intersection_area` :25) / PN | `567bca5f4e4f955a5a27e762f4f242769dfa433bcffbc4b454aa75320f90dae5` / `525897ada99ec2859bb83246c2dc95fb06e16a0d08000032ddc8bf444b8d3625` |
| OUC / SAF-K91 / CFG_B | `c8e3ee2c…` / `5f0d0e40…` / `729640af…`(전체 값 줄임말) |
| OU 블롭 `plant_n31_v2.json`(manifest) / `reference_config_n31_v2.json` 핀 | `b119d6d90081ac0ffabef45e02c189055d2f3c6280c2f65b2ce806730537098f` / `add58bc436423a01753b24b5a4d96e846c5c50cfed98118ea361782c7cb78fd2` |
| OU 블롭 Ω635 `scenario/control_area_membership_213a5d.json` / 바탕 경로 계약 `diagnostics/control_area_route_contract_physical_routes.json` | `30abb1db4f549068cb7069971c60e7ade8205a882c7999a0d0f2ede4460e5f85` / `11d0db7977961a9a0dbca220e12d6db6f46085d2ec051b929f788595658224a9` |
| READBACK K7 출력 `CP/readback/out/discharge.json` / `headcurve.json` | `34220b5c7fc30cbcba9fa0f2def206301f08212a9d2a62200ae1b7f021e90a3d` / `1978197cdf611e1e90f6d99eb9681de7224b3c03830a4b4f7b502a50f0b33bf8` |
| 선언 도구 `C1D/work/declare_values.py` / `ref_closure.py` | `b6342d89ce77db91f536d3232b1cdc15edab6f503b972085b862837f171c72ac` / `9bd1eb8645b9c6a611cbae526c75fa12fec1c9a285b204d3a163c897ff8d1d71` |

- 보충 21–34 의 전체 sha256 64자는 고정 목록 `PINS_C1_DECLARE.sha256` 에 있습니다(보충 21 `ca369954977fc5f98e19b84d08932202847d37e36e26f243caa25df2d135d176`, 24 `d46db6dc3959b19525f0fce77ead5432682e3de0ef8060cdc3da09661559aadc`, 27 `4ce8b27a2ebf08aa0e8ac3f647b4e4336a98f7be7ec8d6f006a0fd1d12005a13`, 29 `4bd6dc8de8b0a4a4ab0b8703c07d7a73d244c4a622b81585f06dc69d6d83599d`, 32 `7f25c21e72fc2599022c72adb1976257413a8486f4898ffcec61f3c6b01423e7`, 33 `76ae084b2b12eb820238a8c2b980c6554c2a988ebeebca877d51fb9714f733ea`, 34 `a05592d48512a515fc254d70b8173360d448b0aa17afb3f63c98b52ef713205e`).
- **선언 참조 바이트** [실행 `declare_values.py`, 10:29 KST; 입력은 설정·증거 파일뿐, 런 결과 자료 0]: `C1D/declared/` 의 파일 8개. 이 보충이 값을 정한 새 증거 파일 셋의 바이트 그대로입니다. 구현 커밋의 빌더는 같은 바이트를 내야 합니다(관문 B).

| 선언 파일 (`C1D/declared/`) | 뜻 | sha256 |
|---|---|---|
| `c1_port_section.json` | 배포 팔의 `c1_port` 구역 전체(§2.1) | `865cc354e498f1c77894f376e249682d52ee082639eaa585ec13af5f0d059654` (정규 JSON sha `c2f3cf19cf6d95e71ad111a044d25fc7c7c2713331bbf7f11dc5abaf339c8fe9`) |
| `omega701_v3c3_bundle.json` | Ω701 묶음 목록(파일 11개 이름·sha·튜닝 포인터) | `40f4a84b547bf9a9a2d1fa44980da5e0d5b3d026c80c55edaa5e5aa6d15ee42e` |
| `head_service_fwe_c1.json` | M5 증거(codex 곡선·설치 규칙·설치 표) | `3933a882b7948abdae825731ecd06494dead4628d5d26c69d1d8f53dc6866333` |
| `plant_n31_v2_omega701.json` | Ω701 판 lane plant manifest | `93f171437fbc55420e234a98efb262e83010566902a691a0cc438f17d247a4f7` |
| `omega701_added_links.json` | 더한 66링크 닫힌 목록·신호별 | `6551e00e0cc5c544cb567ee46e821c7573e2d5dce62e508f324821d15ab0e6f9` |
| `c1_chain_closed_leaves.json` | 연쇄 재생 닫힌 잎 목록(§8.3) | `a9be4b9703ee601e1ef8b04a9766fc38e32d336ef9663a4a3060d75f713e3325` |
| `c1_states.json` | 모든 상태 목록(탐침·G-K0·R·G-RR·F; 시드는 run_provenance `/seed`) | `8ff57e4638588a61d58182d9bae354bdc42e96f56b30bdc61bd5f9bb20cf83df` |
| `SUMMARY.json` | 위 값과 설치 표 repr 요약 | `9ee1c2df950df0aba564e4270b9e4891f7c2e1b1b8f7c14d5efa8b5838d24007` |

---

## 1. 사용자 결정과 ⟨Q⟩ 적용

### 1.1 결정 원문 [읽음 결정 기록, D-K9-91~95 표 행 그대로 요약]

| # | 사용자 답 | 이 보충에서의 뜻 |
|---|---|---|
| D-K9-91 | 기구별 이식(C). 첫 묶음 = 목적 경계(Ω701 접근로) + 미터 결정 묶음. K9-3 보류 | C1 범위 = M0–M5 + M4a·M4b. K9-3 은 넣지 않음 |
| D-K9-92 | VSL 은 오프라인부터 | VSL 은 C1 밖(§2.11). V-A 의 VSL 그대로 |
| D-K9-93 | ① X6 칸 단위 ② † 숫자 그대로 ③ readback 미터 대조 ④ 1099 분해 ⑤ 같은 시드 반복 런 안 함 | §11 폐루프 꼴, §9.2 F 의 "못 냄" 칸 단위 |
| **D-K9-94** | **C1 설계 Q1–Q26 권장안 일괄** | 아래 1.2 표 전부 |
| D-K9-95 | VSL 오프라인 O1·O2 + v3c3 VSL 단독 런 3개 | C1 밖. 다만 무거운 일은 LOCK 을 같이 씀(§3) |

### 1.2 ⟨Q1⟩–⟨Q26⟩ 적용 (모두 권장안)

| ⟨Q⟩ | 권장안(D-K9-94) | 이 보충의 자리 |
|---|---|---|
| Q1 | M0–M5 + M4a·M4b 한 묶음, 키는 기구별(탐침 팔로 몫), 폐루프는 묶음 팔 하나(3런) | §2.1 키, §5 팔, §11 |
| Q2 | FW_W 입구·엮임 보호 장치 없음. SG2 오프라인 대조 + 폐루프 사슬 줄 | §8.2, §11.2 |
| Q3 | 연쇄 재생 SC1001 SG2 계획 녹색(900–2,700 s 합)이 V-A 기록보다 100 s 넘게 짧은 시드가 있으면 멈추고 질문 | §8.2 식, S-C1-9 |
| Q4 | FW_E 4미터 표에서 g9 빼고 g10 남김(K3 정규화에 규칙 하나, 키 끔 불변) | §2.7 |
| Q5 | FW_W 미터 4개는 배분 표 그대로, 10480 g2 3블록은 보고 | §2.7 끝, §11.2 |
| Q6 | 링크 124 공유 차로 옮기지 않음, 124·10483·10480 줄을 폐루프 표에 | §2.11, §11.2 |
| Q7 | 운영 seed·held 유지 함께 옮김, held 유지는 키 따로 | §2.6 |
| Q8 | V-A VSL 그대로, 이웃 검사는 VSL 고정 | §2.3, §2.10 |
| Q9 | 속도 기구 안 넣음. G-K5b 를 넘으면 멈추고 질문 | §2.11, S-C1-8 |
| Q10 | 증거는 이름 + sha 만, Ω701 은 묶음 목록 하나로 11파일 | §2.0, §2.2 |
| Q11 | 런타임은 하위 키 단독 허용, 배포·폐루프는 함께, M1 을 M3·M4 없이 켜면 ValueError | §2.1 검사 (c) |
| Q12 | 키 끔 같음은 G-K0, 키 켬 J 는 보고·C0–C3 분류만 | §9.1 |
| Q13 | R-a T=900 5상태 + R-b V-A 세 시드 900–2,700 s 연쇄(키 켬) | §8 |
| Q14 | B 세 시드 T=900 에서 미터 후보 이름·수·허용 집합·하한·cap 목표 수만 대조(보고, 못 읽으면 "못 냄") | §7 G-RR (c) |
| Q15 | F-Ω·F-S 보고만(절대 문턱 없음) | §9.2 |
| Q16 | 관문·재생 뒤 3시드 동시, 짝 NC3·V-A, 참고 B, 발사 전 다시 물음, 표시 규칙 안 붙임 | §11, S-C1-13 |
| Q17 | readback + FZP 머리 통과(READBACK 고정 도구), 매초 readback 안 씀 | §11.3 |
| Q18 | G-K5a 1.0158, G-K5b 1,500 s, SG2 100 s, 탐침 멈춤 1–4 지금 고정 | §5.4, §6.4, §8.2, §13 |
| Q19 | C1 먼저, K9-3 보류, K9-3 재개 때 C1 켬 상태에서 J 다시 셈 | §2.12-8, §17 |
| Q20 | B 저장 보호가 10639 g2 대기를 왜 안 풀었나: B 결정 JSON 의 RM_C10639 하한·점유 읽기 | P0-8 |
| Q21 | B 가 900–2,700 s 에 SG2 를 왜 줄였나: B 결정 JSON 읽기, NC3 대조는 GREEN 만(540 s), v3c3-s43 은 현시 배치·offset·SG5 도 | P0-9 |
| Q22 | plant 가 127 → 129 → 10491 → 26 사슬을 보는가: 코드 읽기 + F-S 에 링크 26 차로 1 끝 줄 | P0-10, §9.2 F-S |
| Q23 | VSL O1·O2 는 C1 무거운 일과 겹치지 않게, VISSIM R1 은 따로 물음 | §3 LOCK |
| Q24 | 정정 메모(B_RESULTS r2·VERIFY_B 원본 sha 그대로): "3,525 m" → "3,625.8 m", B_RESULTS §2.1-3 (iii) → "SC1001 EBT 녹색 → 127 → 129 → 10491" | P0-12 |
| Q25 | 입구 처리량(차로 바꿈 거리 9999 m·차로 1 37.5 %)은 망 변경 후보 목록에만, C1 밖 | P0-12 |
| Q26 | codex 머리 곡선 출처 읽기(인계 문서·코드), 값은 출처와 무관하게 Q4 규칙 | P0-4 |

---

## 2. 정의 (고정)

### 2.0 공통

1. **키 끔 = c20aff1d 경로.** 튜닝에 `c1_port` 구역이 없으면 런타임 동작·출력은 c20aff1d 와 비트 같아야 합니다(G-K0). 새 코드는 모두 "`c1_port` 의 그 하위 키가 있을 때만" 도는 가지에 둡니다. 키가 없을 때 지나는 줄은 c20aff1d 줄과 내용이 같아야 합니다(관문 G-K1 정적 (h)).
2. **증거는 이름 + sha 만.** `c1_port` 안에는 경로 문자열이 없습니다. 이름은 코드 상수 폴더 안에서만 찾습니다(C1M 상수, §2.2 표). 이름 규칙: 비지 않은 문자열, `/`·`\`·`..`·`:` 없음, 절대 경로 아님. 어기면 ValueError. 파일 바이트 sha256 이 값과 다르면 ValueError. schema 가 다르면 ValueError.
   - 단 Ω701 의 팩 문서 8개와 manifest 는 **기존 소비 코드가 읽는 경로 칸**(`membership_path`, `{path, sha256}` 핀)을 품습니다. 이 칸은 소비 코드의 기존 꼴이라 바꿀 수 없습니다. 그래서 이 칸들은 codex B 의 바이트 그대로(B0 배치, §2.2)이고, 모든 칸이 저장소 상대 경로이며 그 대상 sha 가 맞는지를 P0-2·G-K1 정적 (a) 가 봅니다. 새로 쓰는 C1 증거(묶음 목록·머리 표)에는 경로 문자열이 없습니다.
3. **새 파일 자리와 줄 끝**(core.autocrlf=true):
   - C1 증거·빌더·시험 = `diagnostics/sdmpc_n31_20260924/c1/…`, `diagnostics/sdmpc_n31_20260924/tests/test_c1_*.py`. 기존 규칙 `diagnostics/sdmpc_n31_20260924/** -text`(`.gitattributes:5666`)가 바이트를 지킵니다 [실행 `git check-attr`: text unset].
   - Ω701 파일 10개 = B0 배치 그대로 `diagnostics/b0_v3c3/omega701/{membership.json, route_contract.json}`, `diagnostics/b0_v3c3/evidence/<이름 8개>`. codex `membership.json` 은 CRLF(CR 7,744개)라 [실행] `.gitattributes` 에 `diagnostics/b0_v3c3/** -text` 한 줄을 더합니다(그 파일 줄 끝 CRLF 그대로, `.gitattributes` 는 text unset·eol crlf [실행]).
   - 새 모듈 C1M = `evaluation/controllers/c1_port.py`, LF. `.gitattributes` 에 `"evaluation/controllers/c1_port.py" text eol=lf whitespace=cr-at-eol` 한 줄을 더합니다(이웃 줄 `area_runtime.py` 꼴, `.gitattributes:98`).
4. **새 메타 이름**: 런타임 메타는 `/metadata/c1_port`(RS 가 씀)와 SD 결정 메타 `/metadata/joint_leader_selection/{meter_operating_bounds, meter_neighbor_audit, original_held_candidate}` 뿐입니다. `head_` 로 시작하는 새 메타 키는 만들지 않습니다(보충 21 §6.2 H5).
5. **배포 튜닝 OUC 는 이 보충 단계에서 바꾸지 않습니다.** 묶음 팔 파일 = `diagnostics/sdmpc_n31_20260924/config_n31_v2_c1.json` = OUC + 최상위 키 `c1_port` 하나(값 = `c1_port_section.json` 의 값). 승격은 폐루프 질문 때 따로 정합니다.
6. **팔 튜닝 바탕** = 그 상태 런의 튜닝 계열. V-A·R-obs·B 상태의 탐침·관문·R 은 OUC 바탕. J-1 의 K9-1 판정 잎은 그 잎을 만든 SAF-K91 계열 바탕(`sa_arms.py --k92b1` 위에 `--c1`)입니다. SAF-K91 의 11개 튜닝 포인터 값은 OUC 와 같습니다 [실행].

### 2.1 설정 구역 `c1_port` — 정확한 키와 값 (repr 고정)

배포·폐루프 팔의 값(파일 `C1D/declared/c1_port_section.json` 의 값, 정규 JSON sha `c2f3cf19cf6d95e71ad111a044d25fc7c7c2713331bbf7f11dc5abaf339c8fe9`):

```json
"c1_port": {
  "omega701": {"bundle_name": "omega701_v3c3_bundle.json",
               "bundle_sha256": "40f4a84b547bf9a9a2d1fa44980da5e0d5b3d026c80c55edaa5e5aa6d15ee42e"},
  "meter_neighbor_audit": true,
  "max_leader_candidates": 3,
  "allow_zero_green": false,
  "storage_release_guard": {"enabled": true, "trigger_fraction": 0.9},
  "held_retention": true,
  "head_service": {"evidence_name": "head_service_fwe_c1.json",
                   "evidence_sha256": "3933a882b7948abdae825731ecd06494dead4628d5d26c69d1d8f53dc6866333",
                   "meters": ["RM_C10639", "RM_C10681", "RM_C10490", "RM_C10484"],
                   "full_service_rule": "keep_green_10"}
}
```

| 하위 키 | 기구 | 받는 값(이 밖은 ValueError) | Python repr | codex 대응 [읽음] |
|---|---|---|---|---|
| `omega701` | M0 | 키가 정확히 {`bundle_name`, `bundle_sha256`}; 이름 규칙 §2.0-2; sha 64자 소문자 16진 | `{'bundle_name': 'omega701_v3c3_bundle.json', 'bundle_sha256': '40f4a84b…e42e'}` | CFG_B:8323-8324 + B0 REGEN 8 |
| `meter_neighbor_audit` | M1 | `True` 만(끄려면 키를 뺌) | `True` | `/adapter/sdmpc_meter_neighbor_audit`(CFG_B:7732) |
| `max_leader_candidates` | M2 | `int`(bool 아님), 1 이상; 배포 값 3 | `3` | `/adapter/joint_owner_game/max_leader_candidates`(CFG_B:7696) |
| `allow_zero_green` | M3 | `False` 만 | `False` | `/actuation/real_world_ramp_metering/allow_zero_green`(CFG_B:7541) |
| `storage_release_guard` | M4 + M4a | 키가 정확히 {`enabled`, `trigger_fraction`}; `enabled` 은 `True` 만; `trigger_fraction` 은 int/float(bool 아님), 유한, 0 < x ≤ 1(CX PRB:55-58 꼴) | `{'enabled': True, 'trigger_fraction': 0.9}` | CFG_B:7542-7545 |
| `held_retention` | M4b | `True` 만 | `True` | 키 없음(codex 는 cap 모드면 늘 켬, CX SD:1224-1230) |
| `head_service` | M5 | 키가 정확히 {`evidence_name`, `evidence_sha256`, `meters`, `full_service_rule`}; `meters` = 위 네 이름 그 순서; `full_service_rule` = `"keep_green_10"` 만 | 위 JSON 그대로 | `/freeway/physical_ramp_head_service_veh_per_cycle`(CFG_B:8161-8206) |

- **검사** (C1M `validate(section)`; RS·ADP 의 첫 적용 때 한 번):
  - (a) `c1_port` 가 dict 이고 비어 있지 않음, 키 ⊆ 위 7개(모르는 키 → ValueError).
  - (b) 값 꼴은 위 표.
  - (c) **묶기(Q11·Q1)**: `meter_neighbor_audit` 이 있으면 `allow_zero_green` 과 `storage_release_guard` 가 함께 있어야 함. 없으면 ValueError(`'c1_port.meter_neighbor_audit requires allow_zero_green and storage_release_guard (D-K9-94 Q1/Q11)'`). 그 밖의 키는 단독 허용(탐침 팔용).
  - (d) `head_service` 는 lane plant(`/freeway/lane_plant`)가 있어야 함. 없으면 ValueError.
  - (e) `meter_neighbor_audit` 은 SD 의 3블록(`adapter.sdmpc_control_blocks` = 3)에서만. 아니면 ValueError(`'Finite meter schedule audit requires three control blocks'`, CX SD:197-198 글 그대로).
- **팔**(탐침·관문용 튜닝; 모두 OUC 또는 SAF-K91 바탕 + 아래 하위 키만): OFF = 없음, Ω = {omega701}, M = {meter_neighbor_audit, max_leader_candidates, allow_zero_green, storage_release_guard, held_retention}, H = {head_service}, **C1** = 7개 전부(배포 팔), 보고 팔 M_cap1 = M − {max_leader_candidates}, M_noheld = M − {held_retention}, C1⁻ = C1 − {meter_neighbor_audit}(정책 토큰을 바꾸지 않는 팔, J-1 의 T > 900 결정 잎에만, §9.1).

### 2.2 M0 — 목적 경계 Ω701

**무엇** [읽음 B0F `omega701/membership.json` `/controlled_intersection_expansion`; 실행 대조]: Ω 를 701링크로 바꿉니다. Ω701 − Ω635 = 정확히 66링크, Ω635 − Ω701 = 0. 도로 35 + 직접 커넥터 31. 신호별 도로 수 SC6 12·SC5 5·SC101 4·SC12 4·SC108 3·SC107 3·SC1001 1(링크 37)·SC1004 1(66)·SC1002 1(72)·SC109 1(1220000704)·SC16 1·SC1 1(링크 378·379 는 SC107·SC108 둘에 걸침). 링크 번호 전체 = `omega701_added_links.json`(`6551e00e…`). NP 정의는 그대로입니다(`/controlled_intersection_expansion/np_rule`: "N_P remains the existing 17-player PN net inflow quantity").

**묶음 파일 11개** (묶음 목록 `omega701_v3c3_bundle.json` `/entries`; 폴더 역할 → 코드 상수 C1M `C1_DIRS` = {`omega701`: `diagnostics/b0_v3c3/omega701`, `pack`: `diagnostics/b0_v3c3/evidence`, `c1`: `diagnostics/sdmpc_n31_20260924/c1/evidence`})

| # | 역할 | 이름 | sha256 (1–10 = FRZ_B1 같은 이름 파일 바이트 [실행]; 11 = 선언 계산 [실행]) | 바꾸는 튜닝 포인터 | 지금(c20aff1d) 대상 sha |
|---|---|---|---|---|---|
| 1 | membership | `membership.json` | `9bb740b321d28162c0e849b56e0e618adf4ec800caa60476c96f3fc469318d51` | `/control_area_objective/membership_path` | `30abb1db…` |
| 2 | route_contract | `route_contract.json` | `08fec9c71b1c612ad3f95555173e372fd2f9428ef58d7010246a00bf0b77063a` | `/control_area_objective/route_contract_path` | `11d0db79…` |
| 3 | pack | `native_input_1083_signal_authority_ver2_022a16.json` | `8f65b25c7af1e2f4f83e07890bab90b07d0fe0af283180e3d51052757670a3a1` | `/urban/movements/native_input_signal_authority` | `62d65f9e…` |
| 4 | pack | `native_internal_inputs_c92673.json` | `a23a13632f20cdb81824a406e0c3a83fa9b88cd3eb7f8d32fb33ce318fd820d8` | `/urban/native_internal_inputs` | `9eb1c378…` |
| 5 | pack | `physical_projection_support_635_proposal_ec2393.json` | `7d092b3db6e4107b47ecf751c60196e11a32120dc722d9221c1fb888d447faec` | `/observation/physical_support_repair` | `8d02ed64…` |
| 6 | pack | `sc2001_corridor_nc13_2d0c62.json` | `cc5e6863ca8f9ade6f47689db0ca83744b2ce1186f0d56a92ca8f55074a00c62` | `/urban/sc2001_corridor` | `4b6f0875…` |
| 7 | pack | `route_choice_corridor_sc1004_calibrated_9e6354.json` | `7067a6610b052830885bc56726d944f05fac48daf43dda8ba06fff4750f63716` | `/urban/route_choice_corridor/evidence_paths/0` | `3156fa53…` |
| 8 | pack | `route_choice_corridor_1128_ver2_0fd58c.json` | `d92f90aacb24f44849826ab0c9ed41dd5574a596d27c6d6637ea709e52b2f4b1` | `…/evidence_paths/1` | `dceb222f…` |
| 9 | pack | `route_choice_corridor_1099_sc15_calibrated_e02d01.json` | `8e40f046558d921868bc2f5db435ba131eece073e41052107496f6a541620306` | `…/evidence_paths/2` | `2fd1b191…` |
| 10 | pack | `route_choice_corridor_1100_sc15_calibrated_05ed35.json` | `59fa5c59d58c97c7170de273484ebfb002b158b9f6a2325b23accc3a260c850e` | `…/evidence_paths/3` | `9efa8a75…` |
| 11 | lane_plant_manifest | `plant_n31_v2_omega701.json` | `93f171437fbc55420e234a98efb262e83010566902a691a0cc438f17d247a4f7` | `/freeway/lane_plant` | `b119d6d9…` |

- **바이트 출처**: 1–10 은 codex 빌더·PN 규칙으로 우리 v3c3 팩(c20aff1d 와 같은 바이트, V-A 동결 트리에서 복사)에서 B0 가 만든 파일 그대로입니다 [읽음 B0 §2.3; 실행 sha]. B0 배치(`diagnostics/b0_v3c3/…`)를 그대로 쓰는 까닭: 팩 문서 안의 경로 칸(`membership_path`, `/membership/path`, `/canonical_contract/path`, `/evidence/{10379,336}/…/canonical_contract/path`)이 그 자리를 가리키므로 바이트를 바꾸지 않고 쓸 수 있습니다 [실행 `cmp_docs.py` 차이 목록].
- 11 = OU manifest(`b119d6d9`)에 PN 의 `rewrite`(PN:88-95) 규칙을 적용한 것: `/membership` = {`path`: `diagnostics/b0_v3c3/omega701/membership.json`, `sha256`: `9bb740b3…`}. 직렬화 = PN `data()`(PN:11: `json.dumps(…, ensure_ascii=False, indent=2, allow_nan=False) + '\n'`). 원본을 같은 꼴로 다시 쓰면 원본 바이트와 같았으므로(`SUMMARY.json` `/manifest/original_reserialised_equal_bytes` = true [실행]) 바이트 차이는 그 두 값뿐입니다.
- **재결속 닫힘(새로 안 것, 선언)** [실행 `ref_closure.py`]: OUC 를 원천으로 PN 재결속 규칙(PN:57-108)을 그대로 돌리면 B0 의 8문서 + manifest 말고도 우리 고침 증거 3개가 Ω635 묶음 문서를 `{path, sha256}` 로 가리켜 함께 다시 쓰입니다. 이 셋은 **다시 쓰지 않습니다**(닫힌 목록, 묶음 목록 `/not_rewritten`):

| 문서 (OUC 가 가리킴, 그대로 둠) | 포인터 | 그대로 두는 까닭 [읽음] |
|---|---|---|
| `stopline/sc1001eb_evidence_v3c3_20261004.json`(K8b, `05c821f6…`) | `/inputs/support` → 지지 문서 c20aff1d 판 `8d02ed64…` | 빌더 출처 기록. 런타임은 `/inputs/g2_inpx/extract_sha12` 만 읽음(OU `stopline_approach.py:343`) |
| `k9/wout_side_handoff_v3c3_20261009.json`(K9-1 W2-A, `4683484b…`) | `/derivation/corridor_evidence` → sc2001 회랑 c20aff1d 판 | 빌더 출처 기록. 런타임은 `/values` 만 읽음(OU RS:199-229) |
| `scenario/head_service_resource_contract_7b2da6.json`(HSR) | `/resources/10619/proof` → 회랑 1128 c20aff1d 판 `dceb222f…` | HSR 은 증명 파일을 그 자기 핀 경로·sha 로 읽음(`head_service_resources.py:15-19`). c20aff1d 파일은 트리에 그대로 남음. 읽는 칸(`incoming_turns`·`topology_repairs`)은 Ω701 판과 같음 [추론, 차이는 `membership_path` 하나 — `cmp_docs.py`] |

- **옛 소속 sha 4863f5ee… (열린 항목, 기대 차이 선언)** [실행]: physical_projection_support 의 `4863f5ee5bae6dd47bd00d2adf4a437b9c5eed94f17d3af72fb647fdb31ade9d` 는 `/full_area_coverage_audit/area_membership_sha256` 에 있습니다. c20aff1d 판과 B0 재결속 판(7d092b3d) **둘 다 같은 값**입니다(PN 의 `rewrite` 는 경로 없는 sha 칸을 건드리지 않음, PN:88-95). 런타임은 이 문서의 `full_area_coverage_audit` 에서 `require_positive_unresolved_failure`·`unresolved_physical_links` 만 읽고 이 sha 는 읽지 않습니다(OU `projection_support.py:304-310`; `git grep area_membership_sha256 -- evaluation` 0건). **선언**: C1 에서 이 칸은 `4863f5ee…` 그대로가 기대 값입니다(Ω635 `30abb1db…` 도, Ω701 `9bb740b3…` 도 아님). 지지 문서 c20aff1d 판 대 B0 판의 기대 차이 = 정확히 63잎: `/link_to_storage` 새 키 29, `/evidence` 새 키 29, `/controlled_approach_revision` 새 키 1, `/evidence/10379/source_lineage/canonical_contract/{path,sha256}`·`/evidence/336/downstream_path/canonical_contract/{path,sha256}` 값 4. P0-2 가 이것과 다르면 STOP(S-C1-2).
- **설치 자리** [OU 줄]:
  - ADP:13503 다음 줄(`tuning = load_optional_json(args.tuning_json)` 바로 뒤, `bind_joint_cli_module` 앞): `tuning, _ = c1_port.apply_tuning(tuning)`. 결정 프로그램의 모든 뒤 단계(build_config ADP:8161 포함)가 바뀐 사본을 봅니다.
  - RS:350 앞(`configure_runtime` 본문 첫 줄, 설명문 :344-349 뒤): `tuning, c1_meta = c1_port.apply_tuning(tuning, state_json=state_json)`. ADP 밖의 호출자(오프라인 하네스·plant 잡)도 같은 사본을 씁니다. 이미 적용된 사본이면 값은 그대로 두고 검사·메타만 냅니다(멱등).
  - RS:558 다음(`return state, detector_mapping, metadata`(:559) 앞): `if c1_meta: metadata['c1_port'] = c1_meta`.
  - `apply_tuning`: 원본 dict 를 바꾸지 않고 `copy.deepcopy` 사본에서 11개 포인터 값을 `C1_DIRS[dir] + '/' + name` 으로 바꿉니다. 바꾸기 전 값이 가리키는 파일의 sha 가 묶음 목록 `/before_c20aff1d/<포인터>/sha256` 과 다르면 ValueError(다른 바탕 튜닝에 잘못 얹는 것 막음). `state_json` 이 주어지면 `network_provenance.snapshot_network_sha256(state_json)` = 묶음 `/network_sha256` = `3de889f0…`(아니면 ValueError).
- **소비 코드는 바꾸지 않습니다**: OU AR:150-200(`read_required` :168-170, `extend_gate_routes`), OU CAO:90-150(schema·`unresolved`·안밖 겹침 검사), :252-273(K8-9 유령 경로 별칭), OU LPR:299(`read_pin(document['membership'])`), `route_choice_corridor.py:308`, `sc2001_corridor.py:94`, `projection_support.py:289-363`, `obs150_contract.py:163-198`.
- **단언**(빌더 B / 런타임 R; 거짓이면 빌더 STOP, 런타임 ValueError): O1 (B,R) 묶음 항목 11개, 역할별 수 {membership 1, route_contract 1, pack 8, lane_plant_manifest 1}; O2 (B,R) 항목마다 파일 sha = 항목 sha; O3 (B) Ω701 inside − Ω635 inside = `omega701_added_links.json` `/added_links`(66), 반대 0, inside 701·outside 535; O4 (B) membership `/schema` = `control-area-membership/v1`, `/unresolved` = [], 안·밖 겹침 0; O5 (B) manifest 11 대 OU manifest JSON 차이 = {`/membership/path`, `/membership/sha256`}; O6 (B) 팩 문서 8개 대 c20aff1d 판 JSON 차이 = P0-2 표의 기대 잎 그대로; O7 (B) `/full_area_coverage_audit/area_membership_sha256` = `4863f5ee…`(두 판); O8 (R) 바꾼 포인터 = 정확히 11개, 그 밖의 튜닝 잎 바이트 같음(정규 JSON 비교).

### 2.3 M1 — 이웃 검사 + 조합 1회

| 무엇 | codex 원천 [읽음] | 우리 자리 [OU 줄] | 옮기는 꼴 |
|---|---|---|---|
| `retain_feasible_held` | CX SD:28-51 | SD:25 뒤(:28 `class GradientCache` 앞), 모듈 수준 | 함수 본문 CX 와 같음(G-K1 정적 (g)) |
| `meter_neighbors` | CX SD:556-599 | SD:510 뒤(:513 `def load_prices` 앞) | 같음 |
| `audit_meter_neighbors` | CX SD:602-658 | 같은 자리 | 같음 |
| `audit_meter_budget_candidates` | CX SD:661-689 | 같은 자리 | 같음 |
| 옵션 켜기 | CX SD:126-127(이름 목록) | SD:102 뒤: `c1 = tuning.get('c1_port') or {}`; `'meter_neighbor_audit' in c1` 이면 `options = dict(options, meter_neighbor_audit=True)` | 이름 `meter_neighbor_audit` 은 codex 와 같음 |
| 3블록 검사 | CX SD:197-198 | SD:166 뒤 | 글 그대로 |
| 예산 후보 모음 | CX SD:963, :1216-1218 | SD:684 뒤 `meter_budget_candidates = []`; SD:932 앞 `if audit and candidate_best: meter_budget_candidates.append(candidate_best)`(SD:932-933 은 바꾸지 않음) | 키 끔 줄 그대로 |
| 부르기 | CX SD:1233-1239 | SD:935 뒤(held 유지·`best is None` 검사 뒤) | 같음 |
| 기록 | CX SD:1287-1289 | SD:980 `'finite_neighbor_audit_performed': meter_audit is not None`, 그 뒤 `if meter_audit is not None: metadata['meter_neighbor_audit'] = meter_audit` | 키 끔 값 False 그대로 |

- 쓰는 것(이미 우리 SD·SEQ 에 있음 [읽음]): `coord.encode/decode/validate/valid`(OU SD:365-423, SEQ `SequenceCoordinates`), `coord.move_box.entries`, `evaluate`(OU SD:602-608), `feasible`(:618-622), `finish_trial_derivatives`(:693-697). SEQ 는 바꾸지 않습니다(CX SEQ 와의 차는 secant 갈고리 둘뿐, CX SEQ:116-117, :205-208 [읽음 VC §6]).
- 신호·VSL·cap 은 이웃 검사에서 고정입니다(CX SD:561; "Signal/VSL controls and quantity caps stay fixed") — Q8 의 "이웃 검사는 VSL 고정".
- **후보 수 식(열린 항목 — 저장 보호 이웃 후보 수, 선언)** [계산, CX SD:565-598·PRB:886-905·SEQ:111-127]: 묶음 = 미터 8 + 소유자 묶음(FW_E·FW_W 각 미터 4) 2. SEQ 의 세 블록 좌표는 같은 `ramp_operating_green_floors` 로 만들어지므로(CX SEQ:118-119 → CX SD:410) 하한 10 인 미터는 세 블록 모두 {10} 입니다. 그래서 시작안의 8미터가 모두 g10 일 때:
  - 풂 후보 = 0(가장 풂 = 시작안과 같아 빠짐, CX SD:590-596).
  - 조임 후보 수 N = f(u_E) + f(u_W), u_b = 그 묶음에서 하한이 10 이 아닌 미터 수, f(u) = u + [u ≥ 2] (f(4)=5, f(3)=4, f(2)=3, f(1)=1, f(0)=0). 보호가 안 걸린 상태 N = 10. 묶음 후보는 u_b ≥ 2 일 때만 단일 후보와 다른 z 라서 남습니다(u_b = 1 이면 그 미터 단일 후보와 같은 z 라 `seen` 으로 빠짐).
  - 조임 계획(블록 0/1/2) = g8 / g6 / g4(블록 k 의 허용은 기준 ±2(k+1), 이웃 블록끼리 ±2; CX SEQ:101-106, :147-155).
  - 조합 = 0 또는 1(이로운 후보가 둘 이상이고 겹치지 않을 때 한 번).
  - 시작안이 g10 이 아닌 상태의 후보 수는 보고만 합니다.
- **정책 토큰**: `meter_neighbor_audit` 은 `cfg.network.sdmpc_options` 에 들어가므로 토큰이 바뀝니다(§2.9).
- **단언**(런타임 R; 거짓이면 ValueError, 모두 codex 글 그대로): M-A1 이웃 후보가 미터 밖 축을 바꾸면 `'Finite meter candidate changed another actuator'`(CX SD:622-626); M-A2 후보 평가 수 ≠ 후보 수 → `'Incomplete finite meter evaluation'`(CX SD:613-614); M-A3 조합 평가 수 ≠ 1 → `'Incomplete combined meter evaluation'`(CX SD:646-647); M-A4 예산 incumbent 가 가능하지 않음 → `'Meter budget audit requires a feasible incumbent'`(CX SD:676-677); M-A5 블록 사이 허용 녹색이 없음 → `'No legal successive meter value'`(CX SD:585-586).

### 2.4 M2 — cap 후보 3

- 코드는 이미 같습니다: OU SD:681 `targets = ordered[:options['max_leader_candidates']]`, central 모드 :683 `targets = [(anchor caps)]` 뒤 :925-931 `next_budget` 으로 더함 [읽음; CX SD:959, :1209-1215 같음].
- **자리**: ADP:13047 뒤(`joint_owner_game_settings` 의 `return result`(:13048) 앞): `c1 = (tuning or {}).get('c1_port') or {}`; `'max_leader_candidates' in c1` 이면 `result['max_leader_candidates'] = c1['max_leader_candidates']`. 원래 검사(ADP:12987-13047, 함수 머리 :12987)는 그대로 지난 뒤 덮습니다.
- 바뀌는 값: 1 → 3(OUC `/adapter/joint_owner_game/max_leader_candidates` = 1, SAF-K91 도 1 [실행]). joint 옵션은 policy 에 들지 않으므로 정책 토큰은 그대로입니다(§2.9).
- codex 의 리더 영역 `np_only=True`(CX SD:934, :952; CX PRB:947-953)는 옮기지 않습니다(Q4 (나)를 고르지 않았음). 우리 SD 는 영역에서 `np_values` 만 씁니다(OU SD:675).

### 2.5 M3 — 녹색 0 금지

| 무엇 | codex [읽음] | 우리 자리 [OU 줄] |
|---|---|---|
| 설정 읽기·검사 | CX PRB:49-58 | PRB:112 뒤: `c1` 의 `allow_zero_green` 이 있으면 값 검사(§2.1) |
| spec 에 저장 | CX PRB:145 | PRB:200 뒤(:201 `if city` 앞): `if 'allow_zero_green' in c1: net.physical_ramp_branches['allow_zero_green'] = False` |
| `operating_green_allowed` | CX PRB:866-868 | PRB:412 뒤(:415 `candidate_from_services` 앞), 함수 본문 같음 |
| 새 후보 거부 | CX PRB:859-860 | PRB:409 뒤: `if 'allow_zero_green' in spec and not operating_green_allowed(spec, value): raise ValueError('Physical meter green is below the operating minimum: '+mid)` |
| 미터 축 허용 집합 | CX SD:406-417 | SD:338-345: spec 에 `allow_zero_green` 이 있거나 `ramp_operating_green_floors` 속성이 있으면 codex 식(하한 `floor` + `operating_green_allowed`, 빈 집합 ValueError), 아니면 c20aff1d 식(:341-342) 그대로 |

- 기록된 0 은 읽기만 허용(CX PRB:867 주석)이고, `prepare_control`(OU PRB:321-340)은 바꾸지 않습니다.
- 뜻 [계산]: g10 에서 변경 한도 ±2 s 라 0 은 처음부터 닿지 않습니다. 미터가 2 s 근처로 내려간 뒤에만 뜻이 있습니다.

### 2.6 M4 저장 보호 + M4a 운영 seed + M4b held 유지 (Q7)

| 무엇 | codex [읽음] | 우리 자리 [OU 줄] | 켜는 키 |
|---|---|---|---|
| spec 에 저장 | CX PRB:51-59, :145 | PRB:200 뒤: `net.physical_ramp_branches['storage_release_guard'] = copy.deepcopy(c1['storage_release_guard'])` | storage_release_guard |
| `configure_operating_bounds` | CX PRB:871-908 | PRB:412 뒤, 본문 같음 | 위 |
| 부르기 | CX SD:827-828 | SD:571 뒤(`reference = …` 다음): spec 에 `allow_zero_green` 또는 `storage_release_guard` 가 있으면 `meter_operating_bounds = configure_operating_bounds(state, cfg, reference)`, 아니면 `None` 이고 아무 속성도 쓰지 않음 | allow_zero_green 또는 storage_release_guard |
| 운영 seed | CX SD:858-864(USG 아닌 가지만; 우리 줄기에 `urban_storage_guard` 없음) | SD:586 뒤(:587 `surrogate = …` 앞): 하한이 켜졌으면 codex 꼴로 `operating_seed` 를 만들고, 아니면 `operating_seed = reference` | 위 |
| seed 쓰기 | CX SD:907, :919-922, :945 | SD:629 첫 인자, :641·:642·:644, :667 의 `reference` → `operating_seed`(하한이 꺼졌으면 같은 객체) | 위 |
| 가능 검사 | CX SD:898 | SD:620 `return (` 식의 첫 항으로 `bool(coord.valid(coord.encode(action))) and` — 하한이 켜졌을 때만 | 위 |
| held 유지 | CX SD:1221-1230 | SD:933 뒤 고리 밖(:934 `if best is None` 앞): `cap_mode` 이고 `held_retention` 키가 있을 때만 codex 꼴 | held_retention |
| held 기록 | CX SD:1300 | SD:990 cap_mode `metadata.update(…)` 에 `original_held_candidate=held_candidate`(held_retention 이 있을 때만) | held_retention |
| 하한 기록 | CX SD:1270 | SD:965 메타에 `'meter_operating_bounds': meter_operating_bounds`(None 이 아닐 때만) | 위 |

- **하한 식** [계산, CX PRB:883, :897-901]: base = 2(녹색 0 금지면 `minimum_green_sec` 2, OUC `/actuation/real_world_ramp_metering/min_green_sec` = 2.0 [실행]); 차로마다 점유율 = (`upstream_travelling_veh` + `head_ready_veh`) / (`head_position_m` × `lanes` / `spacing_m`); 어느 차로라도 점유율 ≥ 0.9 − 1e-10 이면 하한 = max(2, min(10, 직전 + 2)), 아니면 2. 직전 g10 이면 하한 10 → 그 결정은 g10 만. 변경 한도 2 s 는 두 줄기가 같은 spec 에서 읽습니다(`topology_routes_v2_8ac6fd.json` `/max_green_change_sec` = 2, 두 트리 sha `089238ed…` 같음 [읽음 설계 §3.5]).
- 저장 보호는 명령 하한일 뿐이고 용량·재고·흐름·목적을 바꾸지 않습니다(CX PRB:874-878 글). 쓰는 상태 이름(`lane_ramp_runtime.buffers[ramp]`, `_lane_buffers`, `snapshot()`, `head_position_m`, `lanes`, `spacing_m`)은 우리 줄기에 있습니다(OU `physical_ramp_boundary.py:85-100, :154-155, :565`, OU `lane_ramp_runtime.py:44-56`) [실행]. 뜻이 같은지는 P0-5 가 봅니다.
- held 유지(CX SD:28-51 그대로)는 운영 seed 를 고른 cap 아래 다시 채점해 1e-7(`objective_tolerance`) 넘게 낮으면 남깁니다. 예측 1번 더.
- **단언**(런타임 R; 거짓이면 ValueError): G-A1 저장 보호가 켜졌는데 `state.lane_ramp_runtime` 이 없음 → `'Storage release guard requires actual physical ramp buffers'`(CX PRB:884-885); G-A2 차로 용량이 유한한 양수가 아니거나 점유가 유한한 0 이상 값이 아님 → `'Invalid observed pre-head storage: '+ramp`(CX PRB:895-896); G-A3 하한·변경 한도·녹색 0 금지로 허용 집합이 비면 → `'No meter command satisfies operating bounds and actual-change limit: '+ramp`(CX SD:413-414); G-A4 하한 ∈ {2, 4, 6, 8, 10}(직전 녹색이 짝수 표 값일 때) [계산]; G-A5 M3: 새 후보 녹색 0 → `'Physical meter green is below the operating minimum: '+mid`(CX PRB:859-860); G-A6 M2: `max_leader_candidates` 가 1 이상 int 가 아님 → ValueError, joint 옵션 차이 = 이 키 하나(G-K1 정적).

### 2.7 M5 — FW_E 미터 4개 머리 서비스 표 (Q4 (가))

- **들어오는 길(새로 안 것)** [읽음]: 머리 곡선은 튜닝이 아니라 lane plant manifest 가 핀한 reference_config 에서 들어옵니다. `CanonicalFreewayModel(geometry, paths['reference_config'])`(OU LPR:119) → CH_H:373 `self.ramp_head_service_veh_per_cycle` → 검사 CH_H:492-497(키가 정확히 "2"–"10", 유한·음 아님·단조) → 설치 OU LPR:512-520. 런타임에서 이 속성을 읽는 곳은 LPR:512-513 뿐입니다(`git grep ramp_head_service -- evaluation vendor` [실행]).
- **자리**:
  - RS:366 뒤(`lane_context['initial_spillback_projection']=…` 다음): `c1_port.install_head_service(lane_context, tuning)` — 증거를 이름 + sha 로 읽고, 곡선 넷을 CH_H:492-497 과 같은 검사로 확인한 뒤 `component.ramp_head_service_veh_per_cycle` 의 네 미터 항목을 증거 곡선으로 바꾸고(다른 미터 항목은 그대로), `component.provenance['physical_ramp_head_service_veh_per_cycle']`(CH_H:545-546)도 같은 값으로 맞춥니다. `lane_context['c1_head_service'] = {meters, rule, evidence_sha256}` 를 둡니다.
  - PRB:36 `normalise_service_table(table, minimum_green_sec, full_service_rule=None)`: 인자가 `None` 이면 지금 본문 그대로(:75-77 의 ValueError 포함). `'keep_green_10'` 이면 최대 서비스 묶음에 대해서만 "`'10'` 을 남기고 나머지를 뺌"(그 묶음에 `'10'` 이 없거나 `'10'` 이 표의 가장 큰 녹색이 아니면 ValueError), 다른 같은 서비스 묶음은 지금 규칙(가장 낮은 허용 녹색)대로. 그 뒤 유일성 검사(:79-80) 그대로.
  - PRB:84-86 `measured_head_service_table(curve, minimum_green_sec, full_service_rule=None)`: 인자를 그대로 넘김.
  - LPR:516: `name` 이 `context['c1_head_service']['meters']` 에 있으면 `full_service_rule='keep_green_10'` 로 부름. 아니면 지금 호출 그대로.
- **값** [읽음 CFG_B:8161-8206; 실행 `declare_values.py`]: 곡선(대/주기) RM_C10639·RM_C10490·RM_C10484 = {2: 1.0, 3: 1.5, 4: 2.0, 5: 2.5, 6: 3.0, 7: 3.5, 8: 4.0, 9: 4.2, 10: 4.2}, RM_C10681 = 그 두 배(2.0 … 8.4; 2차로 합). 설치 표(식 `n*3600/10`, CX LPR:618 = OU PRB:86, repr 고정):

| 미터 | '0' | '2' | '3' | '4' | '5' | '6' | '7' | '8' | '10' | 뺀 것 |
|---|---|---|---|---|---|---|---|---|---|---|
| RM_C10639 / RM_C10490 / RM_C10484 | `0.0` | `360.0` | `540.0` | `720.0` | `900.0` | `1080.0` | `1260.0` | `1440.0` | `1512.0` | `{'9': '10'}` |
| RM_C10681 | `0.0` | `720.0` | `1080.0` | `1440.0` | `1800.0` | `2160.0` | `2520.0` | `2880.0` | `3024.0` | `{'9': '10'}` |

- 바뀌는 점 [계산]: g10 값은 지금과 같습니다(1,512 = 4.2 × 360; 10681 3,024). 저녹색에서 모형 방류가 늘어(g2 255.6 → 360 veh/h/차로, ×1.41) 조임의 모형 구속이 약해집니다. RM_C10490 의 지금 표(OUC `/freeway/physical_ramp_head_service_veh_per_cycle/RM_C10490` = 1.0·1.0·1.44…, 설치 때 g3 빠짐)는 codex 줄로 바뀌고 g3 = 540 이 다시 생깁니다. **B 는 g9 를 썼고 C1 은 g9 를 못 고릅니다**(RM_C10490 240 / 0 / 165, RM_C10681 75 / 30 / 45 주기 [읽음 RB §2.2]) — C1 − B 미터 차에 섞입니다.
- FW_W 미터 4개(10480·10482·10646·10644)는 배분 표(`/actuation/real_world_ramp_metering/per_lane_veh_per_cycle`) 그대로입니다(Q5). 10480 g2 1차 3블록(v3c3-s41, 360 veh/h/차로)은 보고만 합니다 [읽음 RB:97].
- **단언**: H1 (B,R) 곡선 키 = "2"–"10", 유한·음 아님·단조(CH_H:492-497 꼴); H2 (B,R) 설치 표 = 증거 `/values/installed_service_by_green_veh_h` 와 repr 같음; H3 (B) 곡선 = CFG_B 포인터 값과 정규 JSON 같음; H4 (R) 바뀐 component 항목 = 정확히 네 미터; H5 (R) `'10'` 값 = 곡선 '10' × 360 = 기존 g10 값(1,512 / 3,024).
- 증거 파일 `head_service_fwe_c1.json` 의 출처 칸: CFG_B 이름·sha·포인터, codex 설치 코드(`lane_plant_runtime.py` :616-620, `d774daee…`), codex head a49981ff. READBACK K7 출력 sha 는 `report_only` 칸(비교만, 값 출처 아님). 곡선이 어디서 왔는지는 P0-4 가 읽고 보고만 합니다(Q26).

### 2.8 메타 기록 (모든 결정, 키가 있을 때만)

- `/metadata/c1_port` = {`keys`: 켠 하위 키 정렬 목록, `network_sha256`: `3de889f0…`, `omega701`: {`bundle_sha256`, `replaced`: {포인터: {`before_sha256`, `after_name`, `after_sha256`}}}, `head_service`: {`evidence_sha256`, `meters`, `rule`, `dropped`}}. 경로 문자열은 넣지 않습니다(이름 + sha).
- SD 메타(§2.3·§2.6): `/metadata/joint_leader_selection/meter_operating_bounds`, `/meter_neighbor_audit`, `/original_held_candidate`, `/finite_neighbor_audit_performed`(값만 바뀜), `/policy/meter_neighbor_audit`(새 키).
- 이 경로들은 G-RR·G-K1 의 선언 차이 A_C1-M 입니다(§6.3).

### 2.9 정책 토큰 표 (열린 항목 — 어느 키가 토큰을 바꾸나, 선언)

- 토큰 = `sha256(pickle(dict(cfg.network.sdmpc_options), protocol=5))`(OU SD:24-25, :543, :958). V-A 기록의 T=900 토큰 = `428e650ded2f1cb8bb4365abac76ea9765da4783d19e8c2dab1bcd7b688399f9`(v3c3-s31·s41·s43 같음 [실행]).
- C1 구현은 `meter_neighbor_audit` 말고 어떤 C1 값도 `sdmpc_options` 에 넣지 않습니다.

| 팔 | 토큰 | 까닭 |
|---|---|---|
| OFF, Ω, H, {allow_zero_green}, {storage_release_guard}, {held_retention}, {max_leader_candidates}, C1⁻ | `428e650d…` 그대로 | 값이 spec·joint 옵션·cfg 속성·lane_context 에만 들어감 |
| M, M_cap1, M_noheld, C1 | 바뀜(넷이 서로 같음) | `sdmpc_options['meter_neighbor_audit'] = True` |

- 결과: 토큰이 바뀌는 팔로 T > 900 기록 상태를 한 결정만 재생하면 `load_prices`(OU SD:527-528)에서 멈춥니다(B0 R1–R3 와 같은 자리). 그래서 키 켬 재생은 **T=900 단일 결정 또는 연쇄**만 합니다(§8). P0-6 이 이 표를 configure 만으로 확인합니다.

### 2.10 바꾸지 않는 것 (G-K1 정적 "불변 목록")

키 켬(C1 팔) 대 키 끔에서 아래는 같아야 합니다. 하나라도 다르면 STOP(S-C1-5).

| 무리 | 항목 (OUC 포인터 또는 코드) | 같음의 뜻 |
|---|---|---|
| K8b·K9-1·K9-2 증거 핀 | `/urban/stopline_approach/evidence/sha256` `05c821f6…`, `/urban/stopline_approach/city_arrival/evidence_sha256` `ef75c8e6…`, `/urban/sc1002w_saturation/evidence_sha256` `32e48781…`, `/urban/wout_exit_law/SC1001_W_out/evidence_sha256` `314b5c8e…`, `/urban/sc1001_wout_saturation/evidence_sha256` `b64eadc4…`, `/urban/wout_side_handoff/evidence_sha256` `4683484b…`, `/urban/sc109w_through_saturation/evidence_sha256` `b4b7294d…`, `/urban/capacity/head_floor_seed/evidence_sha256` `b9fa1d01…`, `/freeway/offramp_split_forecast/evidence_sha256` `48f7bfca…`, `/urban/known_wout_route_evidence/sha256` `a120dd74…` [실행 OUC] | 튜닝 값·파일 바이트 같음, 그 결정 메타(`k8b_*`·`k9_*`·`k92_*`) 값 같음 |
| 닫힌 목록 3문서 | §2.2 표(K8b 정지선 증거·W2-A·HSR 계약) | 바이트 같음, 다시 쓰지 않음 |
| 유령 경로 별칭 | OU CAO:252-273 | 코드 같음, Ω701 경로 계약에서 유령 키 3개가 별칭으로 쓰임(G-K1 정적 (d)) |
| K6 plant 기준 키 거부 | OU LPR:69-89 | 코드 같음 |
| VSL | `/config_overrides/freeway_follower/{vsl_set [80, 90, 100, 110], max_vsl_step, vsl_smoothness_weight, horizon_vsl_candidate_limit_per_link}`, `/actuation/vsl_command_distribution`(단일값 81/91/101/110), `/actuation/active_lever_mask/allowed_vsl_segments`, `/adapter/vsl_metanet_rollout`, `/freeway/{vsl_sequence_kbest, vsl_zone_heads, vsl_zone_free}`(V-A 그대로, Q8) [실행 OUC] | 튜닝 잎 같음; 이웃 검사 후보의 VSL 좌표 = 시작안(CX SD:561) |
| FW_W 미터 표·배분 표 | `/actuation/real_world_ramp_metering/per_lane_veh_per_cycle`, `min_green_sec` 2, `cycle_sec` 10 | 같음 |
| 램프 도착 예측 | `/calibration_override/prediction/local_ramp_arrival_forecast`(RM_C 키 + strict) | 같음 |
| 소유자·영역 | `sdmpc_cost_ownership` 표(OU SD:220-258, `territory_path`) | 같음 |
| 유지 정책·해시 순서 | VBS `hold_previous_on_exception`(OU VBS:1241-1250), UQM:1306 정렬 합(PYTHONHASHSEED) | 코드 같음 |
| 11개 밖의 튜닝 경로 | OUC 의 모든 `.json` 문자열 값 가운데 §2.2 의 11개를 뺀 것 | 같음 |
| 망 | v3c3 `3de889f0…` | 같음 |

### 2.11 옮기지 않는 것 (설계 §4 그대로)

64cf 로 맞춘 계수(셀 FD·δ_merge·port 계수·`/freeway/segment_params`·retained10638·합류 노드 4·램프 속도·known_wout 일곱 키·망 핀만 바꾼 codex 계약 11·native_beta 8묶음·goal8 추가분), `/urban/calibrated_aggregate`, VSL 부분 전부(집합 50–110·구역 머리·`sdmpc_vsl_activation_secant`·`sdmpc_fixed_vsl`·Carlson·`physical_vsl_sign_binding`·`observed_vsl_history`), 도시 묶음 C5(USG `urban_storage_guard`·머리 자원 v11·무신호 10·머리 현시 대기 귀속·SC1001 공유 접근), 진입 지연(C3·D3), 링크 124 공유 차로(CX RCC:1929-1975, LOR:659·722; Q6), 속도 기구(`sdmpc_response_cap_cache` CX SD:59-88·:226-228·:758-767, `lazy_trial_derivatives`, geometry 캐시; Q9), `meter_activation_secant`(CX SD:547-553), 종단 비용·거리 보상·신호 1 ms 수리·옛 그룹 램프 도착 키·고속도로 5 s 다중 시계, codex `policy_token`(CX SD:758-765, 우리는 `token(policy)` 그대로), FW_W 입구·엮임 보호 장치(Q2), 입구 처리량 망 변경(Q25).

### 2.12 알려진 한계 (선언, 보고서 머리에 옮김)

1. 미터가 g10 에 머물 수 있습니다. 우리 plant 는 조임에 모형 Ω 가 늘거나 그대로였고(METER_CAUSE a2·a2-5), 이웃 검사는 1e-7 넘는 모형 감소가 있어야 고릅니다. S-C1-7 이 폐루프 전에 잡습니다.
2. Ω701 은 TSC 목적을 넓게 바꿉니다. B − V-A 66링크 −246.1 / −286.6 / −271.8, Ω635 +329.7 / +184.9 / +359.1, Ω701 +83.6 / −101.8 / +87.3, ④ +549.1 / +275.6 / −94.3, Ω 밖 (a) +465.5 / +377.3 / −181.6 veh·h(v3c3-s31 / s41 / s43; B 는 다른 제어기라 몫 아님) [읽음 B_RESULTS:65-71].
3. Ω701 이 SC1001 에 더하는 것은 북쪽 링크 37 하나입니다. SG2 가 줄면 B 와 같은 1099 사슬이 생길 수 있습니다. 목적은 ④b 를 보지 않습니다(§8.2 의 멈춤, §11.2 사슬 줄).
4. 결정 시간: cap 3 + 이웃 검사 + V-A VSL 축, cap 캐시 없음. V-A SDMPC 중앙 536.5 / 559.4 / 473.0 s, 최대 743.7 / 818.6 / 782.8 s [읽음 VA_REPORT:622].
5. 키 켬 단일 재생은 T=900 만 됩니다(§2.9). 연쇄 재생의 관측은 V-A 기록이고 직전 명령만 사슬 출력입니다(관측이 C1 명령에 반응하지 않음) — 연쇄는 "이미 본 상태, 독립 근거 아님" 표지.
6. 머리 표 g9: C1 은 g9 를 못 고르고 B 는 썼습니다.
7. FW_W 녹색별 VISSIM 값은 10480 g2 3블록뿐이고 링크 124 공유 차로는 옮기지 않습니다.
8. D1(1135 분할) 미수정: 모형 10681 도착이 VISSIM 의 0.16배라 10681 후보 값이 작을 수 있습니다 [읽음 K9_3_DESIGN_DRAFT:287]. K9-3 을 나중에 얹으면 미터 선택이 바뀔 수 있고, 그때 C1 켬 상태에서 J 를 다시 셉니다(Q19).
9. 저장 보호 상태 이름의 뜻은 P0-5 전에는 모릅니다.
10. 문턱 100 s(SG2)는 B 자료에서 뽑은 데이터 뒤 문턱입니다(B − V-A readback −172 / −229 / −168 s 의 가장 작은 크기 168 s 의 약 0.6배).
11. 세 시드(v3c3-s31·s41·s43)는 모두 우리 fit 시드이고, 블라인드는 NC 한 런(R-obs v3c3-s47)이며 미터 반응은 블라인드로 못 봅니다(§9.2 F-M).
12. VSL 이 섞임: C1 은 V-A VSL, B 는 110 고정입니다. C1 − B 의 ①·입력 1098 차에는 VSL 차가 섞입니다.

---

## 3. 실행 위생과 LESSONS 적용 (모든 단계 구속)

- **무거운 일**(결정 재생·plant 잡·FZP 스캔·시험 묶음)은 한 번에 하나이고 **LOCK** 을 잡은 뒤에만 합니다: `D:/VISSIM-merge/k8_gate_trees/heavy.lock` 을 배타 생성(`open(…, 'x')`, 내용 = {`owner`: `c1`, `pid`, `started_kst`, `job`}). 이미 있으면 기다렸다 다시(확인 간격 ≤ 9분). 끝나면 **우리가 만든 LOCK 만** 지웁니다(내용의 owner·pid 확인). VSL 워크플로도 같은 LOCK 을 씁니다(Q23, D-K9-95).
- 발사: 5분 넘는 일은 WMI `Win32_Process.Create` 로 세션과 분리, 우선순위 BELOW_NORMAL(16384), `PYTHONHASHSEED=0`, `python -B`, `OMP_NUM_THREADS=1`·`NUMBA_NUM_THREADS=1`(K9-2 재생 꼴), codex 코드를 돌리는 P0-1·P0-2 는 env_hsw(`OPENBLAS_CORETYPE=Haswell`, AVX-512 끔, `NUMBA_CPU_NAME=haswell`). 기다림 확인은 한 번에 9분 이하. 소유 PID 만 끕니다. 다른 세션의 VISSIM·python(codex 일, VSL 워크플로 VISSIM 3개)은 건드리지 않습니다.
- 금지: VISSIM·COM·폐루프 러너·동결(`D:/VISSIM-merge/frozen/*`)·푸시. 시험 `test_b1a_watchdog_attempt_launch.py`, `run_plant_fidelity_matrix`, `test_runner_ps1_obs150.py`, `test_native_vbs_clock.py`, `test_tools_launch.py`, `test_tools_replay.py`, real_watchdog 은 돌리지 않습니다. 그 밖의 시험은 새것이거나 §6.4 U 에 적은 것만 돌립니다.
- 읽기만: 동결 트리, 모든 런 폴더, codex 인계 사본 `D:/VISSIM_handoff/20261024`, CX·FRZ_B1·`D:/VISSIM-merge/k8_gate_trees/codexhandoff/` 아래, Y:.
- 봉인 시드 37·59·61·67 은 열지 않습니다(폴더 목록에서 이름을 지나치는 것 말고). codex 64cf-s59/s61/s67 숫자는 쓰지 않습니다.
- C:·D: 가운데 하나라도 8 GB 밑이면 멈춥니다(S-C1-14). 단계마다 시작·끝에 잽니다.
- 이어 하기: 끊긴 단계는 남은 출력을 지우지 않고 이어서 합니다. 같은 커밋을 두 번 만들지 않습니다.
- LOG: 모든 단계의 시작·고정·끝을 `C1D/LOG.md` 에 KST 시각으로 덧붙입니다. 보고서·LOG 사본은 RC1 에.

| LESSON | 이 보충에서 지키는 자리 |
|---|---|
| 튜닝·증거에 경로 문자열 없음(이름 + sha) | §2.0-2, §2.1, `c1_port` 와 새 증거 둘(묶음 목록·머리 표)에 경로 0; 상속 경로 칸은 B0 바이트 그대로 + P0-2·O2 대조 |
| 긴 목록은 파일로 | 상태 목록 `c1_states.json`, 66링크 `omega701_added_links.json`, 닫힌 잎 `c1_chain_closed_leaves.json`, 시험 목록 `C1_U_TESTS.json`(§6.4 U), 구동기 인자는 그 파일 경로 하나 |
| 임시 이름은 PID 로 유일 | 도구·훅이 쓰는 임시 파일·폴더 이름 = `<앞머리>_<pid>_<time_ns>_<순번>`, 배타 생성(`'x'`/`exist_ok=False`); 판정 도구는 이름을 쪼개지 않고 파일 안의 pid 를 읽음(보충 33 꼴) |
| 판정기는 폴더 이름에서 시드를 읽지 않음 | 시드 = 그 런 `run_provenance_<이름>.json` `/seed`(`c1_states.json` `/seed_rule`), 상태 열쇠 = (런 이름, T) |
| 새 키의 메타 표지는 기록 대 재생 관문에 선언 차이로 | A_C1-M(§6.3), G-RR (a)(b) |
| 승격 전 `make_config --check` | C1-4 관문 `make_config_n31.py --c1 --check`(§6.5); 배포 OUC 는 이 보충에서 바꾸지 않음 |
| 벽시계는 중앙값으로만 판정 | G-K5a(중앙 비), G-K5b(중앙 결정 시간; 최대는 보고) — §6.4, §16 |
| 시험은 기준과 시험별로 | U = `git archive c20aff1d` 트리와 같은 명령·env, 시험 id 별 결과 같음 |
| 연쇄 재생: 직전 행동 경로·영수증은 닫힌 잎, 보고만 | R-b(§8.3), `c1_chain_closed_leaves.json` 11잎 |
| 경로 정규화는 새 트리 뿌리까지 | N_C1(§6.3) + 비교기 자기 시험 |
| NC3 녹색 초는 GREEN 만 | §8.2 SG2 식(행동 CSV 녹색창), §11.2 사슬 줄(readback GREEN 만, NC3 `.sig` 540 s 꼴) |
| 새 정책 토큰으로 기록 상태 재생은 `load_prices` 에서 멈춤 | §2.9, §8(T=900 단일·연쇄만), J-1 의 C1⁻ |
| codex 머리 표 g9=g10 대 K3 | §2.7(g9 빼고 g10 남김) |

---

## 4. P0 (고정 뒤, 탐침 전; 읽기·증거·구조 점검만, VISSIM 0)

- 도구: `C1D/tools/c1_p0.py`(하위 명령 p0_1 … p0_13)와 P0 패치 트리 `TC1/trees/p0_<패치sha8>`(= `git archive c20aff1d` + 탐침 패치 `C1D/tools/c1_probe.patch`). 도구·패치 sha256 을 첫 P0 계산 **전에** LOG 에 고정합니다. 출력 `TC1/out/p0/`.
- 결과 값 파일 `C1D/C1_VALUES.json`: P0 이 낸 기대 값(P0-3 차이 집합, P0-5 점유·하한, P0-6 토큰 표, P0-7 노출 목록 sha, P0-11 상태별 기대 후보 수). 첫 탐침 계산 **전에** 그 sha256 을 LOG 에 고정하고 그 뒤 고치지 않습니다.

| # | 내용 | 멈춤 |
|---|---|---|
| P0-1 | Ω701 소속·경로 계약 재현: CX 빌더 `expand_controlled_intersection_area`(sha `567bca5f…`)를 OU Ω635(`30abb1db…`)에 돌림 → `previous_membership`·`area_revision_sources` 두 키를 뺀 JSON 이 B0F `membership.json` 과 같고, 두 키는 B0F 값 그대로(`/previous_membership` = {`path`: Ω635 경로를 역슬래시로 쓴 B0F 의 JSON 글자 그대로, `sha256`: `30abb1db…`}, `/area_revision_sources` = B0F 목록 그대로; 같은 함수를 64cf 에 돌리면 codex 문서와 이 두 키만 다르다는 B0 §2.3 의 규칙). PN:21-56 경로 부분을 바탕 계약(`11d0db79…`)에 돌림 → 바이트 = `08fec9c7…`, turn 57개 갱신 | 다르면 STOP·질문 |
| P0-2 | 재결속 재현: PN:57-108 을 `documents` = 닫힌 목록(팩 8 + manifest; §2.2 의 3문서 뺌), B0 배치로 c20aff1d 블롭에 돌림 → 팩 8개 바이트 = §2.2 표 sha, manifest 바이트 = `93f17143…`, 다시 쓰인 문서 = 정확히 9, 지지 문서 c20aff1d 대 결과 차이 = §2.2 의 63잎, `/full_area_coverage_audit/area_membership_sha256` = `4863f5ee…`(두 판), 연결자 지원 29개 = membership 의 `added_unique_connector_support` 와 같음. 그리고 `git grep -n area_membership_sha256 -- evaluation` 0건, `full_area_coverage_audit` 를 읽는 곳 = `projection_support.py:304` 하나 | 하나라도 다르면 STOP·질문(S-C1-2) |
| P0-3 | 구조 점검(결정 0): P0 트리 + Ω 팔로 V-A v3c3-s31 T=900 상태에서 ADP 결정 프로그램을 `sdmpc.configure`·`install_cost_ownership`(ADP:13586-13591)까지만 돌림(결정 풀이 전에 끝냄). 끝까지 가는지(OU CAO:125-150 `unresolved model membership`, LPR:299, AR:168-185), 그리고 OFF 대 Ω 의 `cfg.network` 깊은 비교 차이 경로 집합 E_Ω(리스트 첨자는 `[*]` 로 일반화)을 C1_VALUES.json `/p0_3/E_omega` 에 적음 | 예외 → STOP·질문 |
| P0-4 | 머리 표 증거: 빌더가 CFG_B 에서 `head_service_fwe_c1.json` 을 다시 냄 → 바이트 = `3933a882…`; 설치 표 = §2.7 표. Q26: codex 인계 문서(`D:/VISSIM_handoff/20261024` 의 HANDOFF·문서)와 CX 코드에서 곡선 출처(녹색 1초당 0.5 대/차로, 상한 4.2)를 읽어 보고만 | 바이트가 다르면 STOP. 출처는 보고만(값 불변) |
| P0-5 | 저장 보호 상태 이름: 탐침 상태 5개(V-A v3c3-s31·s41·s43 T=900, R-obs v3c3-s31·s43 T=900)에서 설정 단계 뒤 `state.lane_ramp_runtime.buffers[RM_C*]` 의 `_lane_buffers`·`snapshot()` 키(`upstream_travelling_veh`·`head_ready_veh`)·`head_position_m`·`lanes`·`spacing_m` 이 있고 유한·양인지, 8미터 차로별 점유율·하한(§2.6 식) | 없음·비유한 → STOP(S-C1-2) |
| P0-6 | 정책 토큰 표: P0 트리에서 팔 OFF·Ω·H·M·M_cap1·M_noheld·C1·C1⁻·{allow_zero_green}·{storage_release_guard}·{held_retention}·{max_leader_candidates} 를 configure 만 해 토큰을 셈 | §2.9 표와 다르면 STOP |
| P0-7 | 블라인드 노출 목록: 기존 산출(K8b·K9-1·K9-2 출력 뿌리, `CP/` 아래)에서 R-obs v3c3-s47 의 F 창((T, T+450], T = 1,050 … 8,400)에 66링크·링크 37·127·129·10491·26 값을 담은 파일을 **파일·키 이름으로만** 찾음(값 안 엶). 첫 줄 = "D-K9-84 Q3 의 Ω701 재집계는 V-A·J1·NC3 9런, R-obs 아님" [읽음 NOTES:277] | 목록 sha 를 C1_VALUES.json 에. STOP 아님(노출 표지에 씀) |
| P0-8 | (Q20) B 세 시드 결정 JSON(T = 900 … 8,100)의 `/metadata/joint_leader_selection/meter_operating_bounds/ramps/RM_C10639`(`triggered`, 차로 `fill_fraction`, `minimum_green_sec`)를 읽어 발동 수·점유 분포를 READBACK 의 g2 블록 미터 앞 중앙 42.6대 [읽음 RB:175] 와 나란히 | 보고만 |
| P0-9 | (Q21) B 세 시드 900–2,550 s 결정 JSON 의 SC1001 가격·접근로 대기 예측·현시 배치·offset·SG2/SG5 계획 녹색(§8.2 식)을 읽음. NC3 대조는 GREEN 만 540 s(`.sig` prog 1). v3c3-s43 은 현시 배치·offset·SG5(+194 s)도 | 보고만. "Q2·Q3 를 다시 볼지" 는 다음 질문 지점(어떤 STOP 이든, 늦어도 폐루프 질문)에 사용자에게 함께 보임 |
| P0-10 | (Q22) 우리 plant 코드에서 링크 129 저장·10491 막힘·링크 26 차로 1 끝의 표현을 읽음(파일:줄 목록). 표현이 없으면 F-S 의 그 줄은 "모형 대응 없음" | 보고만 |
| P0-11 | 기대 이웃 후보 수: P0-5 의 하한으로 상태마다 §2.3 식 N(u_E, u_W) 를 계산해 C1_VALUES.json `/p0_11` 에. 식 자체는 합성 좌표 단위 시험(`test_c1_meter.py` 의 일부와 같은 내용)으로 P0 트리에서 확인 | 식 시험 거짓 → STOP |
| P0-12 | 문서만: (Q24) 정정 메모 `CH/B_RESULTS_ERRATA_20261027.md`("RM_C10480 합류 3,525 m" → "3,625.8 m"(inpx 3,625.80, 10491 3,650.90 → 129 239.38 m [실행 VC §3]); B_RESULTS §2.1-3 볼 길 (iii) → "SC1001 EBT 녹색 → 127 → 129 → 10491"); B_RESULTS r2·VERIFY_B 원본은 그대로. (Q25) `C1D/NETWORK_CANDIDATES_C1.md` 에 "1099 입구 처리량: 차로 바꿈 거리 9999 m·차로 1 37.5 % — 다음 망 묶음 때 FZP 차로 바꿈 수로 확인" 한 줄 | 없음 |
| P0-13 | 비교기 정규화 자기 시험: N_C1(§6.3) 이 TC1 트리·출력, V-A·B·R-obs 런 뿌리의 합성 경로를 모두 `<root>`·`<bundle>`·`<run>`·`<name>` 으로 바꾸는지 | 거짓 → STOP |

---

## 5. 미니 탐침 (P0 뒤, 구현 전; 보고만, 판정 아님)

### 5.1 트리·팔·상태

- 트리 `TC1/trees/probe_<패치sha8>` = `git archive c20aff1d` + `C1D/tools/c1_probe.patch`(선언 키로 M0–M5 + M4a·M4b, §2 의 자리). 패치·팔 튜닝 파일(`C1D/tools/arms/*.json`)·`C1_VALUES.json` sha 를 첫 탐침 계산 전 LOG 에 고정.
- 팔: OFF, Ω, M, H, C1, 보고 팔 M_cap1·M_noheld(§2.1).
- 결정 재생 상태(`c1_states.json` `/probe_decisions_T900`): V-A v3c3-s31·s41·s43 T=900, R-obs v3c3-s31·s43 T=900. 모두 첫 SDMPC 결정이라 직전 `sdmpc_state` 가 없어 `load_prices` 를 그대로 지납니다(OU SD:516-518). 팔 7 × 상태 5 = 35 결정.
- plant 잡(기록 행동, 결정 없음; `/probe_plant_jobs`): R-obs v3c3-s31 {1,500, 2,850, 3,900, 5,250, 6,000, 6,600, 7,500, 8,250}, v3c3-s43 {1,050, 3,300, 4,800, 5,550, 6,450, 7,050, 7,800, 8,400}(K9-2 탐침 둘째 표본 [읽음 보충 24:337]) × {OFF, Ω, H}.

### 5.2 보고 항목

팔·상태별: 이웃 검사 후보 표(이름·Δ 모형 Ω·가능 여부·선택), P0-11 기대 후보 수 대 실제, 블록별 미터 녹색, 저장 보호 하한·점유, cap 목표 수, held 유지 여부, 모형 Ω701·Ω635·OUTW(같은 표), SC1001 SG2·SG5 계획 녹색(§8.2 식, 블록 0), 결정 벽시계(`replay_run.json` `wall_sec`)·예측 수. 머리에 "탐침, 판정 아님".

### 5.3 기대 (선언)

- Ω·H 팔 plant 잡은 셀·저장고 궤적이 OFF 와 숫자 잎까지 같고, 다른 것은 목적 합(Ω)과 선언 메타뿐입니다. R-obs 기록은 미터가 늘 g10 이고 g10 설치 값은 바뀌지 않기 때문입니다(§2.7) [추론].
- M·C1 팔에서 보호가 안 걸린 g10 시작안의 조임 후보는 10개입니다(§2.3) [계산].

### 5.4 멈춤·질문 규칙 (Q18 고정; 하나라도 참이면 구현 전에 보고·질문)

1. 예외·장부·불변식 위반 1건 이상.
2. Ω 또는 H 팔 plant 잡의 저장고·셀 궤적 숫자 잎이 OFF 와 다름(목적 합·선언 메타 말고) → STOP.
3. M·C1 팔에서 5상태 모두 조임을 한 번도 고르지 않음(§12 S-C1-7 의 "조임 고름" 정의) → 보고·질문(구현 전).
4. 키 켬(C1 팔) 결정 벽시계 **중앙**이 1,500 s 를 넘음 → 보고·질문(G-K5b 미리 보기). 최대는 보고.
- 그 밖: 탐침 산출이 없거나 끝나지 않음(INCOMPLETE) → 다시 돌리지 않고 보고·질문.
- 보고서 `C1D/C1_PROBE_RESULTS.md`(+ RC1 사본).

---

## 6. 커밋과 커밋별 관문

### 6.1 브랜치·공통

- GWT8 새 브랜치 **`claude/c1-port-20261027`** 를 `c20aff1d7bf0c432cb4f20e2922bd406d857aa5d` 에서 만듭니다. `claude/k92-b1-20261016` 은 c20aff1d 에, K8 브랜치 `claude/k8-sc1001eb-defects-20261004` 는 `b9734abe1c83f95c9cec5fca5e42b7b18cd45991` 에 그대로 둡니다. **푸시 0.**
- 브랜치 앞 확인(커밋마다 다시): 두 브랜치 위치 그대로, `git status --porcelain` 0줄(커밋할 명시 경로 밖), 새 브랜치가 없거나(처음) 있으면 커밋 목록이 §6.2 표 앞부분과 순서·이름이 같음(이어 하기). 거짓이면 STOP(S-C1-15).
- 공통: 명시 경로만 스테이징(`add -A`·`.`·`-u`·`--renormalize`·amend·rebase·force 금지). 작성자·커미터 `git -c user.name=Ming2you -c user.email=alsrjsrb1915@snu.ac.kr`. 메시지 끝 줄 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. 메시지 첫 줄 꼴 `C1-n: <요약> (amendment C1 <고정판 sha16>)`.
- **줄 끝·바이트** [실행 c20aff1d 상태]: text unset 파일(PRB·RS·ADP·`.gitattributes`·`diagnostics/sdmpc_n31_20260924/**`·새 `diagnostics/b0_v3c3/**`)은 커밋 뒤 `git ls-tree` 블롭 = `git hash-object --no-filters <작업 파일>`. text 미지정 파일 SD·LPR 은 c20aff1d 에서 이미 블롭(LF; SD `d21fdd49…`, LPR `e788f596…`) ≠ 작업 파일(CRLF; `d7ca462a…`, `69c2143f…`)이므로 줄 끝은 작업 파일 꼴(CRLF) 그대로 두고, 커밋 뒤 블롭 = `git hash-object <작업 파일>`(필터 적용)과 `git diff c20aff1d --ignore-cr-at-eol` = `git diff c20aff1d`(줄 끝만 바뀐 줄 0)를 확인합니다. 새 C1M 은 LF(`text eol=lf` 규칙)로 블롭 = 작업 바이트. 넣는 줄의 줄 끝 = 바로 위 앵커 줄.
- 커밋별 계산 출력 `TC1/out/commit/<커밋>/`, 트리 `TC1/trees/c1_<n>_<커밋sha8>`(`git archive <커밋>`).

### 6.2 커밋 표

| 커밋 | 파일 (명시 경로) | 런타임 |
|---|---|---|
| **C1-0** 하네스(진단 전용) | `diagnostics/sdmpc_n31_20260924/k8_gates/sa/` 의 기록기 새 필드(이웃 검사·하한·held·SG2/SG5 계획·66링크 모형 체류·링크 37/127/129/10491 저장고; 새 기록은 `c1_record.json` 에만, `summary.json` 잎 집합 불변), 가드 `c1_judging_state`(R-obs v3c3-s47 의 F 표본·K9-1/K9-2 판정 상태는 단계 토큰 `c1t` + 보충 C1 고정판 sha 없이 거부; 키 열쇠 = (런 이름, T)), `sa_arms.py --c1`(팔 파일 = 바탕 + `c1_port` 하위 키), 비교기 `c1_compare.py`(보충 21 §6 + 보충 27·29 규칙 + §6.3), 자기 시험 `k8_gates/sa/tests/test_c1_harness.py`, README | 0 |
| **C1-1** Ω701 | C1M(전체 키 검사·이름 찾기·`apply_tuning`; 이 커밋에서는 `omega701` 말고 다른 하위 키가 있으면 ValueError `'c1_port.<키> not installed at C1-1'`), RS(§2.2 세 자리), ADP:13503 한 줄, `.gitattributes` 두 줄(§2.0-3), `diagnostics/b0_v3c3/omega701/{membership.json, route_contract.json}`, `diagnostics/b0_v3c3/evidence/<8개>`, `diagnostics/sdmpc_n31_20260924/c1/evidence/{omega701_v3c3_bundle.json, plant_n31_v2_omega701.json}`, 빌더 `diagnostics/sdmpc_n31_20260924/c1/build_c1_evidence.py`(하위 명령 `omega`, `--check`), `diagnostics/sdmpc_n31_20260924/tests/test_c1_omega.py` | 있음(키 없으면 0) |
| **C1-2** 미터 결정 | SD(§2.3·§2.4 메타·§2.6), PRB(§2.5·§2.6), ADP(§2.4 한 자리), C1M(M1–M4b 키 허용), `tests/test_c1_meter.py` | 있음(키 없으면 0) |
| **C1-3** 머리 표 | PRB(§2.7 정규화 규칙·인자), LPR:516 한 자리, RS:366 한 줄, C1M(`install_head_service`, head_service 키 허용), `c1/evidence/head_service_fwe_c1.json`, 빌더 하위 명령 `head`, `tests/test_c1_head.py` | 있음(키 없으면 0) |
| **C1-4** 팔·문서 | `make_config_n31.py --c1`(OUC 에 `c1_port` 하나만 더함; `--check`), `config_n31_v2_c1.json`, `diagnostics/sdmpc_n31_20260924/c1/README.md`, `c1/WORKLOG_20261027.md` | 0 |

- 커밋하지 않는 것: 탐침 패치·팔 파일, P0 출력, R 구동기(`C1D/tools/`), 보고서.
- 배포 OUC 와 `make_config_n31.py` 의 기본 출력은 바꾸지 않습니다(`--c1` 일 때만 새 파일).

### 6.3 비교 규칙

- **바탕**: 보충 21 §6(정규화 N §6.1, HARD H1–H5 §6.2, 출처 꼴 F §6.3, 결정적 잎 D §6.3a, 허용 V ∪ R3 ∪ F §6.4)과 보충 27 의 K9-2 트리 뿌리 N 규칙·CR 짝 규칙, 보충 29 의 A_K92 옛 값 조건·쪽별 메타 키·모든 깊이 결정적 잎 규칙을 그대로 씁니다.
- **결과 넷**(보충 21 §6.4): **PASS** = HARD 모두 같음 + 미분류 0, **FAIL** = HARD 하나라도 다름, **보류** = HARD 같음 + 미분류 > 0, **INCOMPLETE** = 비교할 출력이 없거나 실행이 끝나지 않음. FAIL·보류·INCOMPLETE 는 모두 STOP 입니다. 결과를 본 뒤 HARD·N·F·허용을 바꾸지 않습니다.
- **N_C1**(보충 21 §6.1 의 목록 **앞에** 넣음, 먼저 맞는 것 하나):
  - `d:/vissim-merge/k8_gate_trees/c1/trees/[a-z0-9_]+` → `<root>`
  - `d:/vissim-merge/k8_gate_trees/c1/out/(?:[a-z0-9_]+/)*?t[0-9]{6}(?:_[a-z0-9]+)*` → `<bundle>`(C1 출력 묶음 폴더 이름은 반드시 `t<6자리>[_접미사]`)
  - `d:/vissim_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s[0-9]+` → `<run>`, `d:/vissim_runs/20261026_codex_b_v3c3/s[0-9]+/sdmpc` → `<run>`
  - 그 뒤 이름 `sdmpc31_v3c3_k92va_s[0-9]+`·`sdmpc31_sdmpc9000_s[0-9]+` → `<name>`.
  - 트리·출력 이름은 소문자 `[a-z0-9_]` 만 씁니다.
- **A_C1**(허용에 더함): D5 경로 `…/transformed_source_sha256/<root>/evaluation/controllers/<f>` 의 값 차이, `<f>` ∈ {`runtime_setup.py`, `sdmpc.py`, `physical_ramp_branches.py`, `lane_plant_runtime.py`, `vissim_stackelberg_adapter.py`}. 조건: 옛 값 = 옛 쪽 Root 의 그 파일 바이트 sha256 이고 새 값 = 새 쪽 Root 의 그 파일 바이트 sha256(두 트리를 만든 직후 파일 표 `tree_manifest.json` 에 적은 값과 같음). 더해 새 쪽에만 있는 키 `…/evaluation/controllers/c1_port.py` 는 값 = 새 쪽 C1M 바이트 sha256 일 때만.
- **A_C1-M**(키 켬 비교에서만):
  - 한쪽(새 쪽)에만 있을 때만 허용(양쪽에 있고 다르면 미분류): `/metadata/c1_port`(하위 전체), `/metadata/joint_leader_selection/meter_operating_bounds`, `/metadata/joint_leader_selection/meter_neighbor_audit`, `/metadata/joint_leader_selection/original_held_candidate`, `/metadata/joint_leader_selection/policy/meter_neighbor_audit`.
  - 값 차이로 허용(조건이 참일 때만): `/metadata/joint_leader_selection/finite_neighbor_audit_performed`(옛 False → 새 True), `/metadata/sdmpc_state/policy_sha256`·`/metadata/joint_leader_selection/price_state/policy_sha256`(옛 = `428e650d…`, 새 = P0-6 의 M 계열 토큰), `/metadata/lane_plant_manifest_sha256`(Ω 키가 있을 때, 옛 = `b119d6d9…`, 새 = `93f17143…`), `/metadata/lane_ramp_head_service_normalisation/dropped`(H 키가 있을 때, 새 = 네 미터 `{'9': '10'}` + 그 밖의 미터는 옛 값; C0 무리로 보고).
  - 결정적 잎 조건(거짓이면 미분류): `/metadata/c1_port/omega701/bundle_sha256` = `40f4a84b…`, `/metadata/c1_port/head_service/evidence_sha256` = `3933a882…`, `/metadata/c1_port/network_sha256` = `3de889f0…`, `/metadata/c1_port/omega701/replaced/*/after_sha256` = §2.2 표 값.
- **C0–C3 분류**(키 켬 차이 보고용 잎 무리): C0 = 미터 축·미터 대기·하한·이웃 검사·머리 표·Ω701 66링크 저장고 회계; C1 = 그 신호 17곳의 녹색·offset, 리더 cap·NP; C2 = 합계(Ω701·Ω635·OUTW·목적); C3 = 그 밖. 무리 소속 규칙(경로 정규식)은 C1-0 비교기 상수로 두고 그 sha 를 데이터 전에 고정합니다.
- 블라인드: 비교 도구는 같음/다름·경로·sha 만 출력합니다. 목적값·예측값은 판정 메모리에서만 씁니다. 판정 도구(비교기·관문 계산기·구동기·독립 검증기)는 데이터 전에 sha 를 LOG 에 고정하고, 데이터를 본 뒤 고치면 그 관문 STOP(S-C1-12).

### 6.4 관문 정의

| 관문 | 상태·계산 | 참이어야 할 조건 |
|---|---|---|
| **U** | 닫힌 시험 목록 `C1D/C1_U_TESTS.json`(C1-0 전에 sha 고정): 기존 `diagnostics/sdmpc_n31_20260924/tests/` 의 `test_k8b_p1.py`·`test_k8b_p2.py`·`test_k8b_p4.py`·`test_k9_latent.py`·`test_k9_w1.py`·`test_k9_w2a.py`·`test_k9_f17b.py`·`test_k92_w.py`·`test_k92_hb.py`·`test_k8_phantom_route_alias.py`·`test_stopline_approach.py`·`test_stopline_wiring.py`·`test_stopline_evidence.py`·`test_stopline_approach_captured.py`, `…/k8_gates/sa/tests/` 의 `test_k8b_harness.py`·`test_k91_harness.py`·`test_k92_harness.py`·`test_k92_a27.py`·`test_k92_a29.py`·`test_sa_harness.py`·`test_sa_tl3m.py`, `scripts/tests/test_b1a_vbs_verified_capture_static.py`, `diagnostics/obs150_20260924/tests/test_runner_static_obs150.py`, `diagnostics/sdmpc_n31_20260924/tools/tests/test_tools_watch.py` + 새 `test_c1_omega.py`·`test_c1_meter.py`·`test_c1_head.py`·`test_c1_harness.py` | 기존 시험: 깨끗한 `git archive c20aff1d` 트리에서 같은 명령·같은 env 로 얻은 결과와 **시험 id 별로 같음**(기준에서 실패하는 시험은 같은 단언 글로 실패; 알려진 기준 실패 후보: `test_b1a_vbs_verified_capture_static.py::test_called_path_satisfies_capture_contract`(보충 23), `test_stopline_wiring.py::ConfigFlagTests::{test_default_output_is_byte_identical, test_arms_add_exactly_the_key}`(보충 31 §3) — 실제 기준 목록은 기준 실행이 정함). 새 시험 모두 통과. 기존 시험 파일은 바꾸지 않음 |
| **B** | `build_c1_evidence.py omega --check`, `head --check` | 커밋 증거 바이트 = `C1D/declared/` 의 같은 이름 파일 바이트(묶음 `40f4a84b…`, manifest `93f17143…`, 머리 `3933a882…`); B0 배치 10파일 바이트 = §2.2 표 sha |
| **G-K0** 키 끔 = c20aff1d | 결정(`c1_states.json` `/gk0_decisions`): D-a GB-7′ 무제어 61(R-obs v3c3-s31, T = 1, 150, …, 9,000), D-b GB-9′ SDMPC 4(R-obs v3c3-s31, T = 900·2,700·4,950·6,300, 직전 = R-obs `action_<T−150>`), D-c V-A 3런 × T = 900·2,700·4,950·6,300(12, 직전 = V-A 기록 + 영수증). plant(`/gk0_plant_jobs`, 33잡): K9-1 탐침 표본에서 v3c3-s47 을 뺀 17(R-obs v3c3-s31 H3 8 + v3c3-s43 H3 8 + v3c3-s43 2,400 H42) + K9-2 둘째 표본 16. 튜닝 = OUC(키 없음). 기준 = `TC1/trees/base_c20aff1d` 출력 — **C1-0 관문 때 한 번** 계산해 출력 sha 목록 `TC1/out/base/BASE_PINS.sha256` 를 LOG 에 고정하고, 뒤 커밋은 그 고정 출력과 비교 | 결정: 모두 §6.3 PASS. plant: 숫자 잎 차 0, `summary.json` 한쪽 잎 0(새 기록은 `c1_record.json` 에만). 정책 토큰 = `428e650d…`(D-b·D-c) |
| **G-K1** 키 켬 차이 분류 | 정적(P0-5 의 5상태 × 팔 Ω·M·H·C1, configure 만): (a) Ω 소속 집합 차 = `omega701_added_links.json` 66링크 정확히, 경로 계약 차 = turn 57, 튜닝 값 차 = 정확히 11포인터(§2.2), 11파일 sha = 표 값, 팩 문서 안 모든 경로 칸이 저장소 상대이고 그 대상 sha 가 맞음 (b) 미터 허용 집합 차 = 0 빠짐 + 하한(§2.6) (c) 설치 머리 표 차 = FW_E 4미터 행만, 값 = §2.7 표 (d) Ω701 경로 계약에서 유령 별칭 키 3개가 쓰임 (e) `configure_runtime` 끝 `cfg.network` 깊은 비교: Ω 팔 차이 = C1_VALUES `/p0_3/E_omega`(같은 상태는 같은 집합, 다른 상태는 그 일반화 집합의 부분), M 팔 차이 ⊆ {`physical_ramp_branches/allow_zero_green`, `physical_ramp_branches/storage_release_guard`, `c1_port`}, H 팔 차이 ⊆ {`physical_ramp_branches/ramps/<FW_E 4>/service_by_green_veh_h`, `c1_port`}; `sdmpc.configure` 뒤에는 M·C1 에 `sdmpc_options/meter_neighbor_audit` 하나 더 (f) 작업자(도함수 작업자 포함) 프로세스가 받는 `cfg.network` 피클 sha = 주 프로세스 값 (g) §2.3·§2.5·§2.6 의 옮긴 함수 6개(`retain_feasible_held`, `meter_neighbors`, `audit_meter_neighbors`, `audit_meter_budget_candidates`, `configure_operating_bounds`, `operating_green_allowed`)의 `ast.dump` = CX 의 같은 함수 (h) 키 끔 가지의 줄 = c20aff1d 줄(커밋 diff 에서 키 끔 가지 안의 바뀐 줄 0) (i) §2.10 불변 목록. 동적(`/gk0_plant_jobs` 33 × {Ω, H, C1}): 잎을 C0–C3 로; Ω·H 는 저장고·셀 궤적 숫자 잎 차 0 | 정적 (a)–(i) 모두 참, 그 밖 차이 하나라도 → STOP. 동적: Ω·H 궤적 차 0; C1 팔은 C3 잎의 첫 차이 스텝·경로 목록을 적고, **C3 첫 차이 스텝이 C0 첫 차이 스텝보다 앞서면 STOP** |
| **G-K2** 식 재현 | (a) 이웃 후보 수: 합성 좌표 시험 + 탐침 5상태 C1 팔의 g10 시작안 → P0-11 기대 수(보호 없음 = 10), 계획 g8/g6/g4, 풂 0 (b) 하한 = §2.6 식(점유 ≥ 0.9 → max(2, min(10, 직전 + 2)), 아니면 2) (c) 머리 설치 = §2.7 표(`n*3600/10`) (d) 같은 plant 잡에서 Ω 팔 목적 − OFF 목적 = 66링크 모형 체류 합(`c1_record.json`) (e) cap 목표 수 ≤ 3, = 1 + 받아들인 `next_budget` 수 | (a)(b)(e) 정확히 같음, (c) repr 같음, (d) 상대 1e-9 |
| **G-K3** 거부·묶기 | §2.0-2 이름 규칙 위반 → ValueError, sha 다름 → ValueError, schema 다름 → ValueError, 3블록 아닌데 이웃 검사 → ValueError, 문턱 ∉ (0, 1] → ValueError, 모르는 하위 키 → ValueError, `meter_neighbor_audit` 만(M3·M4 없이) → ValueError, `false` 인 불 키·`allow_zero_green: true` → ValueError, 규칙 밖 머리 표(`'10'` 없음·`'10'` 이 최대 녹색 아님) → ValueError, `apply_tuning` 바탕 sha 다름 → ValueError, `make_config --c1` 이 하위 키 7개 전부를 씀 | 모두 참(자식 프로세스 0) |
| **G-K4** 탐침 재현 | 커밋 코드(그 커밋까지의 팔)로 탐침 5상태 결정 + 탐침 plant 잡 둘(R-obs v3c3-s31 1,500·v3c3-s43 1,050) | 스크래치 탐침 같은 팔과 모든 차이가 상대 1e-9 이하이고 연산 순서로 설명될 때만 PASS; 결정 HARD 는 같음 |
| **G-K5a** 키 끔 벽시계 | 키 끔 결정 재생 짝: 탐침 5상태마다 A(`base_c20aff1d`)·B(커밋 트리)·A·B 연속 → 연속 (A, B) 짝 2개, 10짝. 짝마다 시작 전·중간·끝 뒤 `Get-Process -Name VISSIM*` 개수(읽기만)가 모두 0 인 짝만; 0 이 아니면 VISSIM 0 일 때 같은 인자로 다시(처음 깨끗한 것 하나), 24 h 안에 못 채우면 INCOMPLETE | 짝 비(B/A, `replay_run.json` `wall_sec`)의 **중앙** ≤ **1.0158**(= 1.05 / 1.033718118959995 [계산], K9-1 G-EB-11(a) 남은 예산, K9-3 G-K5 와 같음). 사분위 범위 > 0.006 이면 "가릴 수 없음" 보고·질문 |
| **G-K5b** 키 켬 결정 시간 | C1 팔 결정 벽시계(`replay_run.json` `wall_sec`): C1-2 관문 = G-K4 의 C1-2 팔 5결정, R 단계 = R-a 5 + R-b 39 | **중앙** ≤ **1,500 s**(D-K9-88 관문 1 값). 평균·최대·p90 은 보고. 최대가 러너 무진행 상한 StallSec 3,600 s(D-K9-90)를 넘으면 폐루프 질문에 따로 적음(보고) |

### 6.5 커밋별 관문 표

| 커밋 | 관문 (순서대로; 앞이 PASS 가 아니면 다음 없음) |
|---|---|
| C1-0 | `git diff --name-status c20aff1d..` ⊆ {하네스, c1 도구, 시험}, `git diff c20aff1d -- evaluation vendor plant scripts` 빈 결과, `py_compile`, 가드 자체 시험(블라인드 상태 거부·`c1t` 없는 판정 상태 거부·옛 토큰 `k8bt`·`k91t`·`k92t` 로 C1 키 계산 거부·탐침 상태 허용; 자식 프로세스 0), P0-13 비교기 자기 시험, U, G-K0(기준 출력 계산·고정 + 커밋 트리 plant) |
| C1-1 | U, B(omega), G-K0(전부), G-K1(Ω), G-K2(d), G-K3(Ω 몫), G-K4(Ω), G-K5a |
| C1-2 | U, G-K0(전부), G-K1(M), G-K2(a)(b)(e), G-K3(M 몫), G-K4(M), G-K5a, G-K5b(C1-2 값) |
| C1-3 | U, B(head), G-K0(전부), G-K1(H), G-K2(c), G-K3(H 몫), G-K4(H), G-K5a |
| C1-4 | G-K0(D-c·plant), G-K3(전부), G-K1(C1 팔 정적), 팔 동일성(`sa_arms.py --c1` 팔 파일 − 바탕 = `c1_port` 하위 키만), `make_config_n31.py --c1 --check` |

- 관문(또는 그 앞 점검) 하나라도 FAIL·보류·INCOMPLETE 면 그 자리에서 STOP 하고 보고합니다. 하네스든 런타임이든 **사용자 결정 뒤에만** 고칩니다(S-C1-12).

---

## 7. G-RR — 기록 대 재생 (선언 차이)

| # | 비교 | 선언 차이 | 조건 |
|---|---|---|---|
| (a) | 키 끔 재생 대 V-A 기록: G-K0 D-c 의 12결정(같은 계산을 씀) | 보충 21 §6.4 허용(V 7 ∪ A_K8 R3 ∪ F, D 뺌) ∪ A_C1 | §6.3 PASS. 아니면 STOP |
| (b) | 키 켬(C1 팔) 재생 대 V-A 기록: R-a 의 V-A 3결정(T=900) | A_C1 ∪ A_C1-M ∪ 결정 차(C0–C3 로 분류, 행동이 바뀌므로 D1 `*action_token`·HARD 물리 필드 차는 보고) | 보고 + 멈춤 하나: A_C1-M 의 결정적 잎 조건(증거·망·manifest sha) 거짓 → STOP |
| (c) | 키 켬 재생 대 **B 기록**(B 세 시드 T=900, `/g_rr_c_b`) | §2.11 의 옮기지 않은 plant 부분 전부 + VSL 정책(B 110 고정) + 머리 표 g9 | 보고만: 미터 후보 이름 집합·후보 수·허용 집합·하한·cap 목표 수 대조. 우리 어댑터가 B 상태 파일을 쓰인 대로 못 읽으면 그 칸 "못 냄"(도구 고치지 않음, X6 꼴) |

- 연쇄 재생(R-b)의 기록 대 재생 비교는 §8.3 의 닫힌 잎 목록으로 보고만 합니다.

---

## 8. 오프라인 재생 R (이미 본 상태; 보고 + 미리 정한 멈춤)

- 트리 = C1-4 커밋 트리 `TC1/trees/c1_4_<sha8>`, 팔 = C1(배포 팔 값), 튜닝 = `config_n31_v2_c1.json`. 표지 "이미 본 상태(V-A 기록), 독립 근거 아님". 판정에 쓰지 않습니다.

### 8.1 R-a 단일 결정 (`/r_a`)

- V-A v3c3-s31·s41·s43 T=900, R-obs v3c3-s31·s43 T=900. 직전 = 그 런 `action_000750`. 5결정. G-RR (b) 와 같은 계산.

### 8.2 R-b 연쇄 재생 (`/r_b_chains`) 과 SG2 멈춤 (Q3)

- V-A v3c3-s31·s41·s43 각각 T = 900, 1,050, …, 2,700(13결정, 합 39). 관측 상태 = V-A 기록. 직전 명령 = T=900 은 V-A `action_000750`, 그 뒤는 바로 앞 사슬 출력(JSON·CSV)과 구동기가 만든 적용 영수증(`<직전>.json.applied`, UTF-16 세 줄: 직전 결정 시각, 사슬 CSV 경로, 그 CSV 바이트 수 — OU SD:519-528 이 읽는 꼴). 정책 토큰은 사슬 안에서 같으므로 `load_prices` 를 지납니다.
- 구동기 `C1D/tools/c1_chain.py` = KV2 `vb_chain.py`(`87b89ce4…`)의 사본에 바꾼 곳(뿌리·트리·팔·상태 파일·출력 자리·훅 없음·LOCK)만 고친 것. 바뀐 최상위 함수 목록과 sha 를 첫 사슬 계산 전 LOG 에 고정, 자기 시험(합성, 자식 프로세스 0) 먼저.
- **SG2 계획 녹색 식**(GREEN 만; 행동 CSV `signal_sg` 행, ADP:1449-1520: `p1_green` = 녹색창 시작, `p2_green` = 녹색창 끝, `green_sec` = 플랜 주기; 창은 녹색만이고 노랑·전적색은 창 밖, `signal_group_plan.py:455-485`):
  - G_SG2(T) = (150 / `green_sec`) × Σ_{행: `kind` = `signal_sg`, `id` 가 `SC1001_SG2_W` 로 시작} (`p2_green` − `p1_green`)
  - S_SG2 = Σ_{T ∈ {900, 1,050, …, 2,550}} G_SG2(T) (12결정, 900–2,700 s 창). SG5 도 같은 식(보고).
  - 양쪽(C1 사슬 출력 CSV, V-A 기록 `action_<T>.csv`) 모두 같은 식.
- **멈춤(S-C1-9)**: 어느 시드든 S_SG2(V-A 기록) − S_SG2(C1 사슬) > **100 s** 이면 멈추고 질문. SC1001 행이 없거나 CSV 를 못 읽으면 INCOMPLETE → STOP. 문턱 출처(데이터 뒤): B − V-A readback −172 / −229 / −168 s 의 가장 작은 크기 168 s 의 약 0.6배 [읽음 VC §2].
- 보고 표(결정별): 이웃 검사 후보·선택, 블록 0 미터 녹색(실행될 명령), 저장 보호 발동, cap 목표·NP, held 유지, 모형 Ω701·Ω635·OUTW(같은 표), SC1001 SG2·SG5 계획 녹색, 모형 링크 127·129·10491 저장고, 결정 벽시계. T=2,700 결정은 SG2 합 밖으로 따로 적습니다.

### 8.3 닫힌 잎 (연쇄 재생, 보고만)

- `c1_chain_closed_leaves.json`(`a9be4b97…`) 11잎: `/prediction_error/source_action_json`, `/metadata/n31_binding/vsl_cohort_initialization/{sha256, source}`, `/metadata/sdmpc_state/previous_application/{source, receipt_sha256, committed}`, `/metadata/joint_leader_selection/price_state/previous_application/{source, receipt_sha256, committed}`, `/metadata/head_observation_groups_carried`, `/metadata/head_observation_prior_discarded`(앞 둘은 보충 34 §2.1 표의 V-B 사슬 인공물 꼴). 이 잎들의 차이는 사슬의 직전 파일 경로·영수증에서 나오므로 보고만 하고 판정에 쓰지 않습니다. 이 밖의 차이는 C0–C3 로 분류해 보고합니다.

---

## 9. 판정 단계 c1t (블라인드; R 뒤, 독립 검증 전)

- 시작 조건: C1-0…C1-4 관문 모두 PASS, R-a·R-b 끝(S-C1-9 안 걸림), 단계 토큰 `c1t` + 보충 C1 고정판 sha 를 LOG 에 적은 뒤. 가드 `c1_judging_state` 가 토큰 없는 판정 상태 계산을 자식 프로세스 전에 거부합니다(S-C1-10).
- 시작 훑기: `TC1/out` 아래 파일을 이름·키 이름만으로 훑어 R-obs v3c3-s47 의 F 창 값이 이미 있으면 S-C1-10(그 단계 무효, STOP). P0-7 노출 목록(기존 산출)은 이 규칙 밖이고 노출 표지로만 씁니다.

### 9.1 J — K9-1·K9-2 판정 잎 (Q12 (가): 보고·분류만)

- 키 끔 같음은 G-K0 가 봅니다(코드 경로 같음).
- **J-1**: K9-1 판정 잎 45개(`gates_k91t.json` `4e59f61d…` 의 G-EB-2·3·4·5·6·7·8·13·14, `pass_` 가 null 아닌 것)를 K9-2 J-b 와 같은 잡 사상으로 다시 계산. 키 끔 기준 = K9-2 J-b 값 `OUTK/judge/jb.json`(`f8a273ef9b6e2f02f539b4193a39d35516959d8799e3cd89a2b060c006faa200`, SAF-K92b1 팔). 키 켬 팔 = SAF-K91 계열 `--k92b1 --c1`(C1 팔). T > 900 인 SDMPC 결정 잎은 C1 팔이면 `load_prices` 에서 멈추므로(§2.9) **C1⁻ 팔**로 계산하고 표지 "C1⁻(M1 뺀 팔, 정책 토큰 때문)" 를 붙입니다.
- **J-2**: K9-2 판정 F 표본(R-obs v3c3-s47 22상태, 보충 24 §5.3)의 모형 쪽 F-1–F-3 잎(SC109 서측·좌회전 관련)을 plant 잡 {OFF(SAF-K92b1), C1} 로 커밋 트리에서 계산해 비교. VISSIM 쪽 값과 K9-2 봉인 뿌리는 열지 않습니다.
- 보고: 잎별 같음/다름, 바뀐 값·크기, C0–C3, 첫 차이 스텝. 판정·STOP 없음(단 실행 실패는 INCOMPLETE → STOP).

### 9.2 F — 충실도 (NC 전용, 블라인드, 보고만; Q15)

- 표본: R-obs v3c3-s47 T ∈ {1,050, 1,200, …, 8,400} 50상태(`/f_blind`; 봉인 시드 아님). 표지 "부분 노출(다른 지표)"(K9-1·K9-2 판정에 쓴 상태 포함), P0-7 노출 목록을 첫 줄로.
- plant 잡(기록 native 동작, H3) OFF 하나 + 그 런 FZP 한 번 스캔.

| 지표 | 모형 | VISSIM (FZP) | 처리 |
|---|---|---|---|
| F-Ω 66링크 체류 (T, T+450] | `c1_record.json` 66링크 모형 체류 합(= Ω701 − Ω635 몫) | 같은 66링크 체류 | 보고: 편향·MAE·지속 예측(T 의 VISSIM 값) 대비 |
| F-S 링크 37·127·129·10491 저장고 | 모형 저장고 재고 T+150·T+450 | 링크별 차 수 | 보고 |
| F-S2 링크 26 차로 1 끝(3,200–3,700 m) (Q22) | P0-10 이 찾은 대응 칸(없으면 "모형 대응 없음") | 그 구간 차로 1 차 수 | 보고 |
| F-M 미터 머리 표 | — | — | **블라인드로 못 냄**(NC 는 미터가 늘 g10, g10 설치 값은 안 바뀜). 비블라인드 대조는 READBACK K7(B 세 시드, "이미 본 자료") |

- 절대 문턱은 두지 않습니다(근거 없음). 폐루프 질문 때 함께 보입니다.

---

## 10. 독립 검증 (VerifyC1)

- 판정기·하네스를 import 하지 않는 재계산 도구 `C1D/verify/v_*.py`. 첫 관문 출력을 읽기 전에 sha 를 LOG 에 고정합니다.
- 다시 셈: 선언 참조 바이트(§0 표 8개)와 커밋 증거 바이트, Ω 소속 차 66, 머리 설치 표 repr, 정책 토큰 표, G-K0·G-K1(정적)·G-K2·G-K5a/b 값, R-b S_SG2 세 시드, S-C1-7 의 조임 수.
- 하나라도 다르면 STOP(S-C1-16).

---

## 11. 폐루프에서 어떻게 비교하나 (`COMPARE_RULE_C1` 에 옮길 꼴; 숫자 없음; 발사는 다시 물음)

### 11.1 런과 짝

- 런: C1 팔(`config_n31_v2_c1.json`, 우리 러너·우리 동결본) v3c3-s31·s41·s43, 9,000 s, 자리가 나면 3시드 동시(D-K9-90 꼴). **발사 전에 다시 묻습니다**(Q16, S-C1-13). 짝: NC3(같은 시드), V-A(같은 시드, 같은 줄기, C1 키만 다름), 참고 B(같은 시드, 다른 제어기 — codex 코드·64cf 계수·VSL 110 고정). 시드 3, 평균·신뢰구간 없음. "대기 이전" 같은 표시 규칙은 붙이지 않습니다.
- 적분 꼴 둘: 우리 꼴 [0, 9,000] s, codex 꼴 [0, 8,100] s(COMPARE_RULE_B §2).
- `COMPARE_RULE_C1` 과 그 도구 sha 는 첫 C1 런 전에 고정합니다.

### 11.2 표 (veh·h; 시드마다 짝 하나)

| 줄 | C1 − NC3 (v3c3-s31 / s41 / s43) | C1 − V-A | 참고 C1 − B |
|---|---|---|---|
| Ω701 / Ω635 / Ω701 − Ω635(66링크) | | | |
| ④a / **④b(첫 관측 차분, 주 값)** / **④** | | | |
| **Ω 밖 (a) Ω701 기준 / Ω635 기준**, Ω 밖 (b) Ω701 기준 | | | |
| ① FW_E 본선 7링크 / ② 동측 국소 19링크 | | | |
| **④b 중 입력 1099** / 1098 / 도시 입력 | | | |
| 링크 66 (SC1004 남측) | | | |
| 링크 124·10483·10480 (Q6), 링크 70·10639·10638·120 | | | |
| 참고·선언 밖: FW_W 본선(26·120·10771), 링크 26 | | | |

- **사슬 줄**(세 짝 모두): SC1001 SG2·SG5 녹색 초(GREEN 만, readback) 900–2,700·2,700–4,500 s(NC3 = `.sig` prog 1 GREEN 만 540 s 꼴), 127→30 통과 수, 링크 127 0–50 m 차로 1·2 속도 1,800–2,700 s, 링크 129·10491 느린 체류 1,800–3,600 s, 링크 26 차로 1 끝(3,200–3,700 m) 대기 꼬리가 0 m 에 닿은 300 s 칸 수, 넣은 1099 차 2,700–4,500 s. 도구 = INPUT1099 고정 도구(`w1099_scan.py` `0ed864f2…`, `w1099_scan2.py` `e33c0807…`, `w1099_sc_readback.py` `c31227d7…`)의 경로 상수만 바꾼 사본(사본 sha 는 COMPARE_RULE_C1 고정 때).
- **미터 줄**(Q17): 결정별 미터 명령 분포(8미터 × 녹색), readback 대조 K3(주기 녹색 초 = 명령)·K7(녹색별 차로 방류, FZP 머리 통과) — READBACK 고정 도구(`rb_readback.py` `cee5f262…`, `rb_discharge.py` `4c385da9…`, `rb_headcurve.py` `1466ff35…`)를 같은 규칙으로. `rate_vph` 가 아니라 FZP 방류로 적음. `RW_SIGNAL_READBACK_SEC` 는 쓰지 않습니다(OU VBS:4061 "for short audits").
- 읽는 법 [추론]: Ω 줄은 ④·Ω 밖 줄과 함께만 인용합니다. C1 − V-A 는 "같은 줄기, C1 키만 다름", C1 − B 는 "다른 제어기" 로 따로 적습니다.

### 11.3 점검 (데이터 전 고정, COMPARE_RULE_B §5 꼴)

- X1 두 스캐너 차 ≤ 0.05 veh·h(보고). X3 고친 도구가 V-A·NC3 칸을 원본과 같게 냄(아니면 STOP). X5 시드마다 도착 수·입력 1099 도착 수(보고). **X6 도구가 C1 자료에서 쓰인 대로 못 돌면 그 칸만 "못 냄"**(D-K9-93 ①). X7 미터 실행: readback K3 어긋남 수, K1 요청 = 읽음 비율(보고). X8 결정: DECISIONS_OK/FAILED/HELD, 결정 벽시계 분포, `.err` 크기(보고).
- 단서: 900 s 전 FZP 접두 † 는 숫자 그대로 † 만 붙임(D-K9-93 ②). 런 사이 흔들림은 모름(같은 시드 반복 없음, D-K9-93 ⑤). 세 시드는 fit 시드이고 봉인 시드 사용은 따로 묻습니다.

---

## 12. STOP 규칙

- **S-C1-1** 고정점 `C1D/AMENDMENT_C1_FIXED.md` 전에 P0·탐침·브랜치·커밋·관문·재생을 함, 또는 고정 뒤 정의·값·문턱·표본·판정 도구를 바꿈 → 무효, STOP.
- **S-C1-2** P0-1·P0-2·P0-3·P0-5·P0-11·P0-13 거짓(소속·재결속·4863f5ee 기대 차이·구조·상태 이름·후보 식·정규화) → STOP·질문.
- **S-C1-3** 탐침 멈춤 1·2 → 구현 전 STOP·질문. 탐침 멈춤 3·4·INCOMPLETE → 구현 전 보고·질문.
- **S-C1-4** G-K0 이 PASS 아님 → STOP.
- **S-C1-5** G-K1 정적 선언 밖 차이·작업자 불일치·불변 목록 차이·Ω/H 궤적 차·C3 첫 차이가 C0 보다 앞섬 → STOP.
- **S-C1-6** G-K2·G-K4 다름, G-K3 거짓, B 거짓, A_C1-M 결정적 잎 조건 거짓 → STOP.
- **S-C1-7** "조임 고름" 이 탐침 M·C1 팔 5상태(10결정)와 R-b 39결정을 통틀어 한 번도 없음 → **폐루프 전에 멈추고 질문**(선택지 예: Ω701 몫만 보는 폐루프 / S1 본선 기구 묶음 먼저 / D1 먼저). "조임 고름" = 그 결정 JSON 의 쓰인 블록 0 명령 `diagnostics.rw_meter_green_<미터>` 가 8미터 가운데 하나라도 직전 실행 명령보다 작음(T=900 상태는 직전이 모두 g10). 이웃 검사 선택 이름(`:tighten`·`combined_meter_owners`)의 수는 따로 보고합니다.
- **S-C1-8** G-K5a 중앙 > 1.0158, G-K5b 중앙 > 1,500 s → STOP·질문(Q9: 선택지 = cap 캐시 이식·cap 2·예산 재선언).
- **S-C1-9** R-b SG2 멈춤(§8.2) → 멈추고 질문.
- **S-C1-10** 블라인드 가드 위반·판정 단계 시작 훑기 거짓 → 그 단계 무효, STOP.
- **S-C1-11** 봉인 시드(37·59·61·67) 열기, codex 64cf-s59/s61/s67 숫자 사용, 동결본·런 폴더·인계 사본·CX·FRZ_B1·Y: 쓰기 → 중지·보고.
- **S-C1-12** 관문 결과를 본 뒤 판정기·하네스·런타임을 사용자 결정 없이 고침, 또는 고쳐서 결과가 바뀜 → 그 관문 STOP, 사용자.
- **S-C1-13** 사용자 결정 없이 폐루프 발사·동결·푸시·배포 OUC 변경 → 금지.
- **S-C1-14** C:·D: 8 GB 밑 → 멈춤.
- **S-C1-15** 브랜치 앞 확인 거짓(다른 브랜치 이동, status 줄, 커밋 목록 다름), 명시 경로 밖 스테이징, 블롭·작업 바이트 확인 거짓 → STOP.
- **S-C1-16** 독립 검증 다름 → STOP.
- **S-C1-17** LOCK 을 잡지 않고 무거운 일을 함, 남의 LOCK·PID 를 지우거나 끔 → 중지·보고.
- 그 밖: 어떤 관문·점검이든 FAIL·보류·INCOMPLETE 는 STOP 이고 사용자가 정합니다.

---

## 13. 퇴행 막기 숫자 (지금 고정)

| # | 값 | 출처 |
|---|---|---|
| RG-1 | G-K5a 중앙 비 ≤ 1.0158 = 1.05 / 1.033718118959995, 사분위 0.006 | K9-1 G-EB-11(a) [읽음 보충 24 RG-6] |
| RG-2 | G-K5b 중앙 ≤ 1,500 s. 참고 V-A SDMPC 중앙 536.5 / 559.4 / 473.0 s, 평균 513.5 / 539.2 / 465.4 s, 최대 743.7 / 818.6 / 782.8 s | D-K9-88 관문 1, VA_REPORT:622 |
| RG-3 | SG2 멈춤 100 s. B − V-A readback −172 / −229 / −168 s, V-A readback SG2 900–2,700 s 578 / 638 / 680 s, NC3 540 s(GREEN 만) | VC §2 [읽음] |
| RG-4 | Ω701: inside 701, outside 535, 더한 66 = 도로 35 + 커넥터 31, 링크 목록 `6551e00e…`, SC1001 = 링크 37 하나 | §2.2 [실행] |
| RG-5 | 증거·묶음 sha: §0 선언 표 8개, §2.2 표 11개, `c1_port` 정규 JSON `c2f3cf19…` | [실행] |
| RG-6 | 머리 설치 표 repr: §2.7 표, 뺀 것 `{'9': '10'}` × 4 | [실행] |
| RG-7 | 이웃 후보: 보호 없음 g10 시작안 조임 10, 풂 0, 계획 g8/6/4, N = f(u_E)+f(u_W) | §2.3 [계산] |
| RG-8 | 키 끔 정책 토큰 `428e650ded2f1cb8bb4365abac76ea9765da4783d19e8c2dab1bcd7b688399f9` | V-A T=900 세 시드 [실행] |
| RG-9 | GB-7′ 허용 목록 sha `a8148f3849fb5e26f09d8f0a095d442aa56da051d888df0b2f657dba089e7af1`(A_K8 35 = R1 16·R2 12·R3 7) | 보충 24 RG-9, 보충 34 [읽음] |
| RG-10 | OU 블롭/작업 바이트: SD `d21fdd49…`/`d7ca462a…`, LPR `e788f596…`/`69c2143f…`, PRB `cef8bfea…` = 작업, RS `bcf7a777…` = 작업, ADP `3fd00007…` = 작업, `.gitattributes` `d3a28806…` = 작업 (git 블롭 id) | [실행 `git rev-parse`, `git hash-object --no-filters`] |
| RG-11 | 지지 문서 c20aff1d 대 B0 판 기대 차이 63잎, `/full_area_coverage_audit/area_membership_sha256` = `4863f5ee…` | §2.2 [실행] |
| RG-12 | 상태 수: G-K0 결정 77(61 + 4 + 12)·plant 33, 탐침 결정 35·plant 48, R-a 5, R-b 39, G-RR (c) 3, F 50 | `c1_states.json` [실행] |

---

## 14. 고정 목록 (pins)

- **Declare 때**(이 판): `C1D/declared/PINS_C1_DECLARE.sha256`(`ad84aa2f…`, 53줄): 근거 문서 21·선언 도구 5·선언 참조 바이트 8·READBACK 출력 2·FRZ_B1 의 CFG_B·Ω701 2·재결속 8·CX 코드 6. 이 보충 파일 자신은 넣지 않습니다(`.sha256` 와 LOG 가 따로 고정).
- **P0 앞**: `C1D/tools/` 의 P0 도구·탐침 패치·팔 파일 → `C1D/PINS_P0.sha256`, LOG.
- **탐침 앞**: `C1_VALUES.json` → LOG.
- **C1-0 앞**: `C1_U_TESTS.json`, 비교기 무리 규칙 상수, 가드 자기 시험 출력 → LOG.
- **C1-0 관문 뒤**: 기준 출력 `TC1/out/base/BASE_PINS.sha256` → LOG.
- **R 앞**: `c1_chain.py`·자기 시험 출력 → `C1D/PINS_R.sha256`, LOG.
- **c1t 앞**: 단계 토큰·J/F 구동기·FZP 스캐너 → `C1D/PINS_C1T.sha256`, LOG.
- **VerifyC1 앞**: `C1D/verify/` 도구 → LOG.
- 각 고정 목록은 고정 뒤 바이트가 바뀌면 S-C1-1·S-C1-12 입니다.

---

## 15. 비용 어림 [추론]

| 단계 | 어림 |
|---|---|
| P0(재현 2·구조 1·상태 5·토큰 12팔 configure·읽기 4·문서) | 4–7 h |
| 미니 탐침(결정 35 × 15–35 분, plant 48 × 약 3 분) | 12–23 h |
| 기준 출력(G-K0 결정 77·plant 33, 한 번) | 6–9 h |
| 커밋 관문 C1-0…C1-4(G-K0 커밋 트리 넷 × 6–9 h, G-K1·G-K2·G-K4 키 켬 재생, G-K5a ABAB 10짝 × 넷) | 40–60 h |
| R-a 5 + G-RR (c) 3 | 2–4 h |
| R-b 연쇄 39결정 × 20–35 분 | 13–23 h |
| J(J-1 45잎 키 켬 + J-2 22상태 두 팔) | 15–25 h |
| F(50 plant 잡 + FZP 스캔) | 4–6 h |
| 독립 검증 | 3–4 h |
| 합 | **약 100–160 h 계산**(무거운 일 한 번에 하나, LOCK 기다림 빼고 약 5–7일) |
| 폐루프 C1 3런(동시, 다시 물은 뒤) | 런당 약 10 h(결정이 V-A 와 비슷할 때; B 34,369–35,143 s, V-A 32,562–37,583 s) ~ 24 h(결정이 2배일 때) [읽음 B_RESULTS:48-50, VA_REPORT:624] |
| 디스크 | 트리 하나 약 1–2 GB × (기준·탐침·P0·커밋 5) + 출력; 폐루프 런당 6.5–7.6 GB(D: 에만). C: 25 GB 라 NUMBA·임시 캐시는 D: 에 둠 |

---

## 16. 설계 초안 r2 대비 바뀐 곳 (데이터 0 상태에서)

| # | 자리 | 초안 r2 | 이 판 | 까닭 |
|---|---|---|---|---|
| 1 | 증거 자리 | `diagnostics/c1_port/evidence/`, Ω701 파일도 거기 | C1 증거 = `diagnostics/sdmpc_n31_20260924/c1/evidence/`; Ω701 10파일 = B0 배치 `diagnostics/b0_v3c3/…` 바이트 그대로 + `.gitattributes` 두 줄 | 기존 `-text` 규칙(`.gitattributes:5666`), 팩 문서의 상속 경로 칸이 B0 자리를 가리킴, codex membership 은 CRLF [실행]. 모든 sha 를 지금 고정 |
| 2 | `bundle_sha256`·`evidence_sha256` | "P0 고정" | 지금 값(`40f4a84b…`, `3933a882…`) | 선언 참조 바이트를 결정적으로 계산(§0) |
| 3 | 재결속 범위 | 문서 8 + manifest | 같음 + 닫힌 목록 3문서는 다시 쓰지 않음 | `ref_closure.py` 로 새로 안 닿음(§2.2) |
| 4 | 옛 소속 4863f5ee | "만날 수 있음, 규칙은 그대로" | 기대 차이 선언: 그 칸 그대로, 63잎 차이, 런타임 미사용 | 열린 항목을 닫음(§2.2) |
| 5 | 머리 표 설치 | "LPR:512-520 설치 전 component 에 씀" | RS:366 뒤 component 속성 교체 + PRB 정규화 인자 + LPR:516 | 곡선이 reference_config 에서 오고, CH_H 가 "2"–"10" 전부를 요구 [읽음] |
| 6 | Ω701 적용 자리 | RS:341-350 첫머리 | 같음 + ADP:13503 | ADP 에서 build_config 가 configure_runtime 보다 먼저 튜닝을 받음 [읽음 ADP:13503-13584] |
| 7 | A_C1-M 경로 | `/metadata/meter_neighbor_audit` 등 | `/metadata/joint_leader_selection/…` | V-A 결정 JSON 의 실제 자리 [실행 키 구조] |
| 8 | 정책 토큰 | "P0-6 에서 확인" | 표로 선언(§2.9), P0-6 은 대조 | 코드에서 정해짐(OU SD:543) |
| 9 | 이웃 후보 수(보호 걸림) | "P0 에서 코드로 정함" | 식 f(u) 로 선언, P0-11 은 상태별 값 | 열린 항목을 닫음(§2.3) |
| 10 | G-K5b | 최대 ≤ 1,500 s | **중앙** ≤ 1,500 s, 최대는 보고 | LESSON "벽시계는 중앙값으로만 판정" |
| 11 | G-K0 기준 | 커밋마다 같은 실행의 c20aff1d 트리 | C1-0 때 한 번 계산·고정, 뒤는 고정 출력과 비교 | 같은 코드의 재계산 비용을 줄임(결과 정의 같음) |
| 12 | 불 키 값 | `true`/`false` 둘 다 | 켤 값 하나만(끄려면 키를 뺌) | "있는데 꺼짐" 상태를 없앰 |
| 13 | G-RR (b) | 미분류 0 | 보고 + 결정적 잎 조건만 멈춤 | 키 켬은 행동이 바뀌어 D1 토큰 차이가 설계상 생김 |
| 14 | J 범위 | "K9-1·K9-2 잎" | J-1 45잎(T > 900 결정은 C1⁻), J-2 F 모형 잎 22상태 | 정책 토큰·봉인 뿌리를 피함 |
| 15 | SG2 합 | "900–2,700 s 합" | 12결정(T=900…2,550) 식 고정, T=2,700 은 따로 | 창과 결정 수를 맞춤 |
| 16 | P0 | P0-1…P0-7 | P0-8…P0-13 더함(Q20·Q21·Q22·Q24·Q25·Q26, 후보 식, 정규화) | D-K9-94 |
| 17 | 비용 | 55–85 h | 100–160 h | G-K0 커밋별·J 두 팔·탐침 팔 7 을 셈 |

---

## 17. 이 문서를 쓰며 한 일·하지 않은 일·파일

- **한 일** [실행, 모두 읽기 전용, 10:06–10:4x KST]: 근거 문서 읽기와 sha256; GWT8 `git show c20aff1d:`·`git grep`·`git check-attr`·`git hash-object --no-filters`(쓰기 0, 체크아웃 0); CX·FRZ_B1 코드·설정·증거 읽기; V-A 결정 JSON 의 키 구조와 T=900 `policy_sha256`·`finite_neighbor_audit_performed` 값, V-A T=900 행동 CSV 머리와 SC1001 SG2 행 꼴(숫자 가림); 9런 run_provenance 의 `/seed`·`/name`·sha; 선언 도구 5개(LOG 10:28 에 sha 고정 뒤 실행)로 `C1D/declared/` 8파일 생성(배타 생성).
- **하지 않은 일**: 코드 변경·브랜치·커밋·푸시 0, P0·탐침·관문·재생·plant 잡 0, VISSIM·COM·러너·동결 0, 시험 0, FZP·readback 새 분석 0, 동결본·런 폴더·인계 사본·CX·FRZ_B1·Y: 쓰기 0, kill 0, LOCK 0(가벼운 세션 일만), 봉인 시드 자료·sealed/ 0, codex 64cf 다른 시드 숫자 0, 금지 시험 0. COMPARE_RULE_B·PINS_B 그대로.
- **파일**: 이 문서 `SP/K8_PREDECLARATION_AMENDMENT_C1.md`(sha256 은 `.sha256` 과 `C1D/LOG.md`), 선언 참조 `C1D/declared/`(8 + 고정 목록), 선언 도구 `C1D/work/`, 보고 사본 RC1.

## 변경 기록

- Declare 판 (2026-10-27 KST): 첫 판. 설계 초안 r2 + D-K9-94.
