# K8 보충 33 (고정판) — K9-2 묶음 1: 측정 훅이 쓰는 파일·폴더 이름을 프로세스마다 유일하게 하고 배타 생성으로 바꿈(D-K9-65), V-B를 새 자리에서 처음부터 다시(ZI → OFF 14 → B1 41 → 점검 → 지표 → 재계산 → 보고), 보고 전용 `action_token` 11경로 글(D-K9-66) (2026-10-22)

- **상태: 고정판(반박 검토 판, ReviewDeclare 2026-10-22).** Declare 판은 `SP/K8_PREDECLARATION_AMENDMENT_33_r1.md`(sha256 `b0db6bf5d49e5b989dd09b629bba016b52e45647a24104cfc4a0a5487dd0bdc9`, 같은 이름 `.sha256` 있음)로 남깁니다. 검토가 고친 곳에는 "[검토]"를 붙였고, 까닭과 확인은 §16에 모았습니다. **검토는 도구(훅·구동기·재계산기·고르기·도움 함수·닫힌 목록·확인 도구)와 확인 출력과 기대 고정 목록(§7.1, 63줄, `a1b02027…`)의 바이트를 바꾸지 않았습니다(글만 고침).** 고정점 파일은 `KB/AMENDMENT33_FIXED.md`이고, 그 파일에 적힌 sha256과 다른 보충 33으로는 V-B의 어떤 단계(사전 점검, 트리, 팔, 훅 영향 0 시험, 사슬 계산, 판정, 재계산, 보고)도 하지 않습니다(§7).
- 이 파일의 sha256을 `SP/K8_PREDECLARATION_AMENDMENT_33.md.sha256`에 적습니다.
- [검토] **검토 끝 상태** [실행 2026-10-22 15:22 KST]: 아래 "쓸 때 상태"와 같음(GWT8 head·K8 브랜치·status 0줄·푸시 0). 새 V-B 데이터 0(`OK2/vb2`·`TK/vb2_e27ceac8`·`KB/a33_pins.sha256` 없음). 검토가 쓴 곳은 `KB/a33review`, 이 글·`_r1`·두 `.sha256`, 고정점, `KB/LOG.md` 덧붙임뿐. 끝에 python·VISSIM 0. C: 40 GB, D: 384 GB.
- **쓸 때 상태** [실행 2026-10-22 14:20–14:50 KST]: GWT8 head = K9-2-5 `e27ceac86c01c1dcfd5b2bb2d9b522be3dc33c0d`(브랜치 `claude/k92-b1-20261016`), K8 브랜치 `claude/k8-sc1001eb-defects-20261004` = `b9734abe1c83f95c9cec5fca5e42b7b18cd45991`, `git status --porcelain` 0줄, 푸시 0. **새 V-B 데이터 0개**: `OK2/vb2`·`TK/vb2_e27ceac8` 없음, 결정 재생·어댑터 실행 0. 이 단계가 띄운 python은 합성 확인과 스냅숏뿐이고 끝난 뒤 python·VISSIM 0. C: 40 GB, D: 384 GB 여유.
- **구속**: 보충 1–32의 규칙·식·값·문턱·관문·표본은 §11 표에 적은 자리만 빼고 **그대로** 구속합니다.
- **알리는 말(먼저 읽을 것)**:
  1. **결정 글은 "후보 폴더 이름"만 말하지만, 이 보충은 같은 훅이 쓰는 `loaded` 파일과 오류 파일 이름에도 같은 값을 붙입니다**(§2.1, 공개 P1). 까닭: (가) 멈춘 실행에서 `loaded_26704.json`이 실제로 덮어써졌습니다(`w` 모드) [읽음 STOP 보고 r1 §3.4]. (나) 사용자가 고른 권장안 글이 "후보 폴더·`loaded` 파일 이름에 프로세스마다 다른 값"이었습니다 [읽음 STOP 보고 r1 :181]. (다) D-K9-65의 "덮어쓰지 않음" 조건은 `loaded` 파일까지 고쳐야 지켜집니다. 훅의 다른 동작(대상, 기록기 호출, 읽기 규칙, 파일 안의 칸)은 바꾸지 않았습니다(§2.5). 사용자가 이 범위를 받아들이지 않으면 반박 검토 또는 V-B 시작 전에 멈춥니다.
  2. **구동기와 재계산기도 새 파일입니다**(`KV2/vb_chain.py`, `KV2/vb_recalc.py`). 옛 파일의 사본에 새 자리·새 고정·보관 점검만 고쳤고, 바뀐 함수는 기계로 확인했습니다(§3, 부록 B·C). 옛 파일은 보관으로 그대로 둡니다.
  3. **옛 출력은 보관이고, 바뀌면 STOP입니다**(새 S-K57, §5, §10). `OK2/vb`·`TK/vb_e27ceac8`·`KV`의 옛 도구와 출력·`AD32`는 읽기만 합니다.
  4. **판정 정의·문턱·표본·닫힌 잎 목록·VB-I1–I7·VB-M1–M9·ZI 규칙은 바꾸지 않습니다.** VB-I1은 여전히 사슬 첫 결정 4개로만 판정하고, 사슬 이어받는 OFF 10결정은 보고만 합니다(D-K9-62).
  5. **보고 전용 `action_token` 11경로는 보고만 합니다(D-K9-66).** 닫힌 목록은 바꾸지 않습니다. 새 보고서 맨 앞에 표와 원인 추론을 정해진 글로 적습니다(§9).
  6. 메인 세션 처리대로, 이 Declare 단계가 STOP 판 r1 보고서의 보관 사본 둘을 미리 만들었습니다(§8, 공개 P4).
  7. [검토] **반박 검토가 합성 시험을 더 돌렸습니다(§16)**: 실제 운영 체제에서 차례로 띄운 121개 프로세스 가운데 PID 재사용이 3번 일어났고 새 훅은 겹침·오류 0, 같은 꼴에서 옛 훅은 재사용 8번에 `hook_error` 8개를 냈습니다(멈춘 실행의 겹침을 합성 강제 없이 다시 냄). 같은 PID·같은 시각의 동시 실행 12개, 토큰 전체 겹침, 한 프로세스 안에서 훅이 두 번 실리는 꼴도 겹침·덮어쓰기·거짓 PASS가 없었습니다. **검토가 찾은 것**: (가) 확인 도구 `AD33/run_bn.py`는 BelowNormal 설정이 조용히 실패합니다 — 그래서 Declare의 자기 시험 둘은 보통 우선순위로 돌았습니다(가벼운 합성, V-B에서 쓰지 않음; 공개 P14). (나) 보관 자리를 지금부터 V0까지 지키는 대조가 없어, 검토 때 목록 값 둘을 고정점에 적고 VerifyVB가 대조하게 했습니다(§6.5, §10 S-K57). (다) VerifyVB의 토큰 짝 점검 글을 정확하게 고쳤습니다(§6.5).
- 표시: [실행] 이번에 돌려서 확인, [읽음] 문서·코드에서 확인, [추론] 시험하지 않은 판단, [계산] 산술.
- 이 보충은 판정 말을 쓰지 않습니다. 결과는 PASS / FAIL / 보류 / INCOMPLETE / STOP과 숫자로만 적습니다. V-B는 보고만이고, 무결성 점검(VB-I)만 통과·실패가 있습니다. 교통 성능 판정이 아닙니다.

## 줄임말 (처음 한 번만 풉니다)

- SP = `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8`. KB = `SP/k92/bundle1`. KI = `KB/impl`(구현 도우미, 바꾸지 않음).
- **KV** = `KB/k92_vb`(멈춘 V-B의 도구·자기 시험·보고서 자리; 이제 보관, 정본 보고서 파일 하나만 새 판으로 덮어씀, §8). **KV2** = `KB/k92_vb2`(새 구동기·재계산기·자기 시험 출력).
- **AD32** = `KB/a32decl`(보충 32 도구: 옛 훅, 고르기 `vb_select.py`, 도움 함수 `vb_lib32.py`, 닫힌 잎 목록; 읽기만). **AD33** = `KB/a33decl`(이 보충의 새 훅·합성 확인 도구·확인 출력·차이 파일·기대 고정 목록).
- TK = `D:/VISSIM-merge/k8_gate_trees/k92b1`. **VBT** = `TK/vb2_e27ceac8`(새 V-B 트리, 아직 없음). **옛 VBT** = `TK/vb_e27ceac8`(+ `.build.json`, 보관).
- OK2 = `D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1`. **VBR** = `OK2/vb2`(새 V-B 출력 뿌리, 아직 없음). **옛 VBR** = `OK2/vb`(보관).
- RR = `D:/VISSIM_runs/20261004_sdmpc31_k8`(J1 기록 런, 읽기만). GWT8 = `D:/VISSIM-merge/sim3-n31-k8`. FRZ_K8 / FRZ_K8b = 두 동결본(읽기만).
- **PID** = 운영 체제가 프로세스에 주는 번호. 한 프로세스가 끝나면 같은 번호가 다른 프로세스에 다시 주어질 수 있습니다(**PID 재사용**).
- **토큰** = 이 보충이 프로세스마다 한 번 만드는 이름 조각 `<pid>_<time_ns>_<16진 16자>`(§2.1). `time_ns` = 1970년부터 나노초로 센 벽시계 값. 16진 16자 = 운영 체제 난수원에서 읽은 8바이트.
- **배타 생성** = 같은 이름이 이미 있으면 만들지 않고 오류를 내는 생성(폴더 `os.mkdir`, 파일 열기 모드 `x`). **덧붙이기 전용** = 파일 끝에만 쓰고 앞 내용을 지우지 않는 열기(모드 `a`).
- 어댑터(ADP) = 결정 하나를 계산하는 프로그램 `vissim_stackelberg_adapter.py`. **탄젠트 작업자** = 어댑터가 미분 계산을 맡기려고 새로 띄우는 파이썬 프로세스(`sdmpc_tangent_worker.py`).
- 훅 = 결정 프로세스 안에서 기록기 `k92_record.py`(REC)를 부르는 읽기 전용 측정 도구(`sitecustomize.py`). 후보 = 훅이 `omega_costs` 호출 하나에서 만든 기록 한 벌. 고르기 = 결정이 고른 행동과 맞는 후보를 고르는 일(`vb_select.py`).
- ZI = 훅 영향 0 시험. VB-I = V-B 무결성 점검(통과·실패 있음). VB-M = V-B 지표(보고만). 결과 넷 = PASS / FAIL / 보류(HOLD) / INCOMPLETE. KC = K9-2-5 비교기 `k92_compare.py`. N = 비교 전 경로 정규화.
- 사슬 첫 결정 = 직전 행동이 RR 기록 파일 그대로인 결정(VB-31·VB-43·VB-41의 T=3,000, VB-41w의 T=1). 사슬 이어받는 결정 = 직전 행동이 같은 사슬의 앞 결정 출력인 결정.
- 시드는 망 접두어를 붙입니다(v3c3-s41 등). 봉인 시드 37/59/61/67은 열지 않습니다. codex 64cf-s59·s61·s67 숫자는 쓰지 않습니다. V-B는 v3c3-s47을 쓰지 않습니다.

---

## 0. 근거 문서 [실행: sha256, 2026-10-22 14:20–14:50 KST]

| 문서 | sha256 |
|---|---|
| 결정 기록 `SP/K9_1_J1_NOTES_20261013.md`(214줄, LF로 끝남; D-K9-65·66 :206-214) | `187242343570f1fe4e22d644509139e87ff59f76c70458b58160c1cde5387109` |
| 보충 32 고정판 / 그 `.sha256` / 고정점 `KB/AMENDMENT32_FIXED.md` | `7f25c21e72fc2599022c72adb1976257413a8486f4898ffcec61f3c6b01423e7` / 같은 값 / `b59088ab44683f5990f2a44038c688aec59a21fcb5207e72b0bc7ee5782ddef4` |
| 보충 24–31 고정판·고정점 | 보충 32 §0 표와 같음(구동기 V0 C1이 64자로 봄) |
| V-B STOP 판 r1 `KV/K92_VB_REPORT.md` = `KB/VB_REPORT.md` = `OK2/vb/K92_VB_REPORT.md` | `d7bf44f3e309aa4ae8e5084b0db238f9baeb2870b6d75b4bea7b6d854427ea00` |
| 고정된 옛 훅 `AD32/vbhook/sitecustomize.py`(248줄) | `4d7e0375116c3f805aa223651da0dc1c0c04b7d3315062e98e21137ba60aa321` |
| 옛 구동기 `KV/vb_chain.py` / 옛 재계산기 `KV/vb_recalc.py` / 옛 V-B 고정 목록 `KV/vb_pins.sha256` | `4dc9297df760800ebb20948b05ba94a645d93a8c7e44abb64c511d1be21d6e99` / `cab7939df8fd55ff4d7df36b058f8892d045a9aff5610b17c8f81f336d5c3e7c` / `6bed354112b93b65d6ffe59bbc8b1472c5e3911683e0d0fcc31964e44514f366` |
| 보충 32 고정 목록 `KB/a32_pins.sha256` = `AD32/a32_pins.expected.sha256`(51줄) | `9e4dc5925e36fcc092f1b4ace4c3e86600d8f96422f3720653fe7d72d4514fcb` |
| 고르기 `AD32/vb_select.py` / 도움 함수 `AD32/vb_lib32.py` / 닫힌 잎 목록 `AD32/vb_closed_leaves.json`(모두 그대로) | `33adfd5033c277a3ad640f745a69efb2a929b27c1ff2a88d794dfa69b489e9cc` / `504999a196a9e08582f303d4ad38d4cc661fcfc765df62d11bc4cc7c05ddc75f` / `b800be45ae3e4e5030ed31ecd221e6288d52c2a287bdeaa5efee243e3cc2f426` |
| 멈춘 실행의 판정·STOP·훅 오류 파일(sha만; 내용은 STOP 보고 r1에 이미 보고됨): `OK2/vb/STOP_vb_V5.json` / `judge/vb_i1.json` / `judge/vb_reportonly.json` / `chain/vb41_off/hook/t003150/hook_error_26704.txt` | `4127cbf2…` / `9c1749a9…` / `30fcda3e…` / `c9809767…`(64자는 기대 고정 목록 29–32줄) |
| 옛 VBT 빌드 기록 `TK/vb_e27ceac8.build.json` | `2ace33638b30a4daccb63544d55e668608e2f51e140a6f93706e79c0514bab0e` |
| 작업 기록 `KB/LOG.md`(이 단계 첫 항목 덧붙임 전, 265,344 B) | `71b698eea2486fa35b7022b5c130a37910aabfc6e2e2ec4ab9640ef827105bfb` |
| 이 단계 스냅숏 `OK2/snap/s42_a33decl.json`(s02 대비 SAME) | `4e55240d36e460f33f9c13c5cf5164e2a03ed2653ae65675afcac9d6b6410302` |

### 0.1 이 판을 쓰며 한 일

- **확인** [실행]: 결정 기록 sha = 작업 지시 값 `18724234…`. 보충 32 고정판·`.sha256`·고정점 32 sha. STOP 판 r1 세 곳 같은 바이트(`d7bf44f3…`). 옛 훅 `4d7e0375…`. GWT8·K8 상태(머리글). `OK2/vb2`·`TK/vb2_e27ceac8`·`KB/a33decl`·`KB/k92_vb2` 없음(시작 때).
- **읽기**: 결정 기록 :180-214, 보충 32 전문, 고정점 32, STOP 판 r1 전문(그 안의 값은 이미 보고된 것), LOG 끝 9 KB, 옛 훅 전문, `vb_select.py` 전문, 옛 구동기 머리·guard·환경·`vbi7`·이어 하기·V0·V1·V2·준비·발사·결정·ZI·V9·V10·`cmd_chain`·자기 시험 전문, 옛 재계산기 머리·고르기·VB-I7·자기 시험, `dry_a32.py`의 합성 프로그램과 훅 부분, KI `launch.ps1`·`cglib.build_archive`·`k92snap.py` 머리, REC `write()`(REC:211-240), GWT8 `sdmpc_tangent.py:40-75`·`sdmpc_tangent_concurrent.py:30-75`(작업자 띄우는 자리), `area_follower_objective.py:435-441`·`:546-549`, `physical_ramp_branches.py:364-369`, `k92_compare.py` 머리(N 규칙), `k92_a27.py`의 `tree_root_ok`.
- **쓰기**: AD33 전부, KV2 전부, STOP 판 r1 보관 사본 둘(`KV/K92_VB_REPORT_stop_r1.md`, `KB/VB_REPORT_stop_r1.md`; 바이트 복사), `OK2/snap/s42_a33decl.json`·`OK2/logs/a33decl_snap.txt`(WMI 발사 표준 출력), `KI/wmi_launch_lines.txt`(launch.ps1이 한 줄 덧붙임), 이 글과 `.sha256`, `KB/LOG.md` 덧붙임. RR·동결본·GWT8·저장소 `.git`·K8 브랜치·OUTK·봉인 뿌리·옛 VBR·옛 VBT·AD32 쓰기 0.
- **확인 실행**(모두 합성 입력, `PYTHONHASHSEED=0`, `python -B`; 5분 안이라 앞에서 돌림): 구동기 자기 시험 `KV2/vb_chain.py selftest`(자식 프로세스 0, 1.1 s), 재계산기 자기 시험 `KV2/vb_recalc.py selftest`(자식 0), `AD33/dry_a33.py all`(자식은 합성 프로그램과 `vb_select.py`뿐, 33 s). [검토] 우선순위: `dry_a33.py all`은 자기 안에서 BelowNormal을 바르게 설정하고 확인했습니다(요약 `below_normal` 참). 자기 시험 둘을 띄운 `AD33/run_bn.py`는 BelowNormal 설정이 실패하므로(공개 P14) **자기 시험 둘은 보통 우선순위로 돌았습니다**(가벼운 합성, 자식 0). 스냅숏 한 번은 `KI/launch.ps1 -Tag a33decl_snap`(WMI 분리, 52.7 s), 그 s02 대비 비교는 앞에서(SAME).
- **개발 중 공개**: 첫 확인 판(14:32–14:34; 구동기 `57e7749f…`)이 모두 참으로 끝난 뒤, 구동기의 STOP 파일 규칙 이름만 고쳤습니다: 보관 점검(V0 C13, V10 보관 목록·바이트)이 거짓이면 S-K53 대신 새 S-K57을 적습니다(두 줄; 판정 조건 그대로). 그래서 구동기 자기 시험과 `dry_a33.py all`을 다시 돌렸고, 고정 목록에 든 출력은 둘째 판입니다. 훅·재계산기·dry 도구 바이트는 첫 실행 뒤 바꾸지 않았습니다. 재계산기 자기 시험은 한 번만 돌렸습니다. 두 판의 도구 sha는 실행 전에 LOG에 적었습니다.
- **하지 않은 일**: VISSIM·COM·러너·동결·결정 재생·plant 잡·어댑터 실행 0. VBT·VBR 만들기 0. ZI·사슬 계산 0. 커밋·브랜치·푸시 0. 금지 시험 0. 봉인 뿌리·봉인 시드·v3c3-s47 자료 열람 0. 멈춘 실행의 출력 파일은 sha만 셈(내용 열람 0, §12 P5).

---

## 1. 사용자 결정 원문 [읽음 결정 기록 :206-214, 표 행 그대로]

근거 줄(:207): `k92/bundle1/k92_vb/K92_VB_REPORT.md` STOP 판 r1(d7bf44f3…). 보충 32 고정(7f25c21e…, 고정점 b59088ab…). 진행: 훅 무영향 시험 ZI 3칸 PASS(CSV 같음, 다른 잎은 벽시계뿐, 훅 켬/끔 벽시계 비 0.991·1.043·1.022), OFF 14결정 종료 0, VB-I1(사슬 첫 결정 4개) 4/4 PASS, VB-I2 14/14. STOP S-K55: VB-I7(훅 무결성) 13/14 — VB-41 OFF T=3,150 에서 탄젠트 작업자 둘이 같은 PID 26704 를 받아 훅 후보 폴더 c_26704_0001 이 겹침(FileExistsError → hook_error; 보충 32 P14 가 미리 적은 위험). 보고 전용 10결정: 행동 CSV 10/10 기록과 바이트 같음, 닫힌 목록 밖 차이는 SDMPC 사슬 결정 5개(VB-41w T=900·1,050, VB-31·43·41 T=3,150)에서 같은 11경로의 D1 action_token 잎뿐(추론: 피클한 행동 객체에 직전 CSV 경로가 들어 있음), 무제어 5결정은 0.

| # | 질문 | 사용자 답 | 효과 |
|---|---|---|---|
| D-K9-65 | 훅 폴더 PID 겹침 처리는? | **훅 고치고 처음부터 다시 (Recommended)** | 보충 33: 훅 후보 폴더 이름에 프로세스마다 유일한 값(PID 재사용에도 겹치지 않는 값)을 넣는 것만 고침, 새 고정. ZI·OFF 14·B1 41 을 새 자리에서 처음부터 다시(약 8–9 h). 기존 OK2/vb(2.5 GB)·TK/vb_e27ceac8(2.1 GB)은 보관 |
| D-K9-66 | 보고 전용 결정의 목록 밖 action_token 11경로는? | **보고만 그대로 (Recommended)** | D-K9-62 글대로. 닫힌 목록 바꾸지 않음. 보고서 앞쪽에 눈에 띄게 적고 원인 추론을 함께 적음 |

메인 세션 처리(:214, 질문 없이): 다시 돌리는 자리는 새 OK2/vb2 와 새 V-B 트리(고정 위반 S-K53 피함), 옛 자리는 보관.

- 작업 지시(메인 세션)가 더 자세히 적은 것 [읽음]: (가) 이름 = 예를 들어 PID + `time.time_ns()` + 난수/uuid4 토큰, 또는 결정 훅 폴더 아래 `tempfile.mkdtemp`; 생성은 배타 생성, 덮어쓰기 없음; 고르기 `vb_select.py`는 고른 행동과 맞는 후보를 여전히 찾아야 하고, 새 이름이 요구하는 것만 고침. (나) 새 고정(훅과 바이트가 바뀐 모든 도구). (다) 새 V-B 출력 뿌리 `OK2/vb2`와 `TK` 아래 새 V-B 트리에서 처음부터: ZI(같은 상태·같은 규칙) → OFF 14 → B1 41 → VB-I1..I7 → VB-M1..M9 → 재계산 → 보고. `OK2/vb`·`TK/vb_e27ceac8`는 고치지도 다시 쓰지도 않음. (라) 보충 24/27/29/31/32의 나머지는 그대로(VB-I1은 사슬 첫 결정 4개, 사슬 이어받는 OFF 10결정은 보고만). (마) 같은 결정 안에서 같은 PID가 두 번 나오게 강제하는 합성 자기 시험. (바) 보고서는 새 판으로 쓰고 STOP 판 r1은 `K92_VB_REPORT_stop_r1.md`(와 `VB_REPORT_stop_r1.md`)로 남기며, `OK2/vb2` 아래에 같은 바이트 사본을 둠.

---

## 2. 훅 이름 고침 (D-K9-65)

### 2.1 무엇이 바뀌나 — 이름

훅은 프로세스가 시작할 때(파이썬이 `sitecustomize`를 읽을 때) **토큰을 한 번** 만듭니다:

```
_proc_token() = '%d_%d_%s' % (os.getpid(), time.time_ns(), os.urandom(8).hex())      # 예: 26704_1792647185147611400_d779296396c57adb
```

훅이 쓰는 이름 넷이 모두 이 토큰을 씁니다 [읽음 새 훅 :37-41, :72, :76, :97, :187, :258].

| 쓰는 것 | 옛 이름(보충 32) | 새 이름(보충 33) | 만드는 법 |
|---|---|---|---|
| 프로세스 시작 기록 | `loaded_<pid>.json` | `loaded_<토큰>.json` | 배타 생성(`x`) |
| 후보 폴더(호출마다) | `c_<pid>_<순번 4자리>/` | `c_<토큰>_<순번 4자리>/` | 배타 생성(`os.mkdir`) |
| 후보 메타 | `c_…/cand.json` | 그대로(폴더 이름만 바뀜) | 배타 생성(`x`) |
| 후보 기록 | `c_…/k92_record.json`, `k92_series.npz` | 그대로 | 기록기 `write()`가 씀(REC:211-240), 폴더가 방금 배타 생성된 새 폴더라 다른 쓰는 이 없음 |
| 훅 안 오류 | `hook_error_<pid>.txt` | `hook_error_<토큰>.txt` | 덧붙이기 전용(`a`) |
| 시작 오류 | `hook_setup_error_<pid>.txt` | `hook_setup_error_<토큰>.txt`(토큰을 만들지 못했으면 `hook_setup_error_<pid>_notoken.txt`) | 덧붙이기 전용(`a`, 옛 `w`) |

- 토큰의 세 조각: PID(사람이 읽기 좋게), 시작 때의 `time_ns`(같은 PID라도 앞뒤 프로세스의 시각이 다름), 운영 체제 난수원의 8바이트(앞 둘이 모두 같아도 갈라 놓음). 파일 안의 칸(`pid` 등)은 바꾸지 않았습니다(§2.5).
- `tempfile.mkdtemp`는 쓰지 않았습니다: `tempfile`이 `random` 모듈을 작업자 프로세스에 싣고, 폴더 이름에서 프로세스를 알아볼 수 없기 때문입니다 [추론]. `uuid` 모듈도 같은 까닭으로 쓰지 않고 `os.urandom`을 바로 씁니다(훅의 import 목록은 옛 훅과 같음, §4.4 static).
- `os.urandom`은 운영 체제 난수원(Windows는 BCryptGenRandom)에서 읽습니다. 파이썬 `random` 모듈의 상태와 numpy 난수 상태를 건드리지 않습니다 [추론: 일반 지식]. 그래서 결정 계산에 영향이 없을 것으로 봅니다. 영향이 있으면 ZI(§6)와 VB-I1이 보입니다.

### 2.2 배타 생성 규칙

1. 훅이 **만드는** 모든 파일·폴더는 배타 생성이거나 덧붙이기 전용입니다. 훅 바이트 안에 쓰기 모드 `w`는 없습니다 [실행 `dry_a33_static.json`: `open` 모드 = `rb` 1, `x` 3, `a` 2; `os.makedirs`는 훅 폴더 `_OUT` 자체에만 두 번(`exist_ok=True`), 후보 폴더는 `os.mkdir` 한 번].
2. **덮어쓰기 없음**: 같은 이름이 이미 있으면 `FileExistsError`가 납니다. 훅은 그 예외를 잡아 오류 파일에 덧붙이고(`hook_error_<토큰>.txt` 또는 `hook_setup_error_<토큰>.txt`) 원래 프로그램으로 올려 보내지 않습니다(보충 32 §3.1 규칙 그대로). 그 결정은 VB-I7 거짓 → S-K52 STOP입니다. 앞 프로세스의 파일은 그대로 남습니다 [실행 P5].
3. 오류 파일은 덧붙이기 전용이라 여러 오류가 한 파일에 쌓여도 앞 내용이 지워지지 않습니다. 오류 파일이 하나라도 있으면 STOP이므로(VB-I7 2번) 덧붙임이 판정을 느슨하게 하지 않습니다.
4. 훅 폴더 자체(결정마다 `VBR/chain/<사슬>_<팔>/hook/t<T6>/`, ZI `VBR/zi/<칸>/hook_on/`)는 구동기가 결정 전에 **비어 있는 새 폴더**로 만듭니다. 사슬 결정은 이미 있으면 S-K54로 멈춥니다(`KV2/vb_chain.py:1086-1088`). [검토] ZI는 칸 폴더가 준비 전에 없어야 하고(있으면 `prepare`가 S-K54, :965-966; 반쯤 된 칸은 통째로 `_interrupted_<시각>`으로 옮김, :1165-1171), `hook_on`은 `exist_ok=False`로 만듭니다(:1189; 있으면 예외로 구동기가 멈춤 — STOP 파일 없이 종료 코드 ≠ 0). 옛 구동기와 같은 코드입니다 [읽음]. 훅의 `os.makedirs(_OUT, exist_ok=True)`는 이 폴더를 다시 만들지 않습니다(있으면 그대로).

### 2.3 차이 — 고정된 옛 훅 `4d7e0375…` 대비

- 새 훅 `AD33/vbhook/sitecustomize.py` sha256 `691fe8100e38d3222f3508f3f682b84b225535d1d3f7cca57f08a671708e365c`(262줄, 12,368 B, LF, CR 0). HOOKDIR(`AD33/vbhook`)에는 이 파일 하나만 있습니다.
- 차이 파일 `AD33/diff/hook.diff`(`diff -u`, 110줄) sha256 `144f90b9346a519697918f426393904e09b1c627cb3fad960adfbf8352789a3e`. 전문은 **부록 A**.
- 기계 확인 [실행 `dry_a33_static.json` `/hook_diff`]: 지운 줄 12개와 더한 줄 26개가 이 보충이 선언한 목록(`dry_a33.py`의 `DECL_REMOVED`·`DECL_ADDED`)과 정확히 같습니다. 바뀐 줄은 (가) 머리 설명 주석, (나) `_proc_token()` 함수(5줄)와 `_setup(tok)` 인자, (다) 이름 넷의 `%d`→`%s` 토큰, (라) 열기 모드 `w`→`x`(세 곳)·`w`→`a`(시작 오류), (마) `os.makedirs(folder)`→`os.mkdir(folder)`, (바) 맨 아래 시작 블록(토큰을 만들고 `_setup`에 넘김)뿐입니다.

### 2.4 왜 겹치지 않나

1. **한 프로세스 안**: 순번은 `threading.Lock` 아래에서 하나씩 늘어나므로(새 훅 :184-187) 같은 토큰 안에서 `c_<토큰>_<순번>`이 겹치지 않습니다. 스레드 4개 합성 시험에서 후보 4개·오류 0 [실행 `dry_a33_hook.json` `threads`].
2. **같은 결정의 다른 프로세스끼리**(어댑터 1 + 작업자 여럿):
   - 동시에 살아 있는 프로세스는 운영 체제가 다른 PID를 줍니다. 토큰의 첫 조각이 다릅니다.
   - 차례로 뜬 프로세스는 같은 PID를 받을 수 있습니다(멈춘 실행에서 실제로 일어남). 이때도 시작 시각 조각과 난수 8바이트가 다릅니다. 앞 프로세스가 끝난 뒤에야 같은 PID가 다시 주어지므로 시작 시각은 앞 프로세스의 수명만큼 뒤입니다 [추론]. 시각이 같더라도(시계 되돌림 등) 난수 조각이 다릅니다 [실행 P4: 같은 PID·같은 `time_ns`로 강제해도 토큰 다름].
   - 우연히 셋 다 같을 확률 [계산]: 난수 조각만 봐도 프로세스 짝 하나당 2⁻⁶⁴. 결정 하나의 프로세스는 멈춘 실행에서 많아야 11개였습니다(`loaded` 10 + 덮어쓰인 1; STOP 보고 r1 §3.4). 12개로 잡으면 짝 66개 → 결정당 ≤ 66 / 2⁶⁴ ≈ 3.6 × 10⁻¹⁸, 훅을 켠 실행 58번(사슬 55 + ZI 훅 켬 3) 합쳐 ≤ 2.1 × 10⁻¹⁶. [검토] B1 결정의 작업자 수는 아직 본 적이 없으므로 12개 가정에 기대지 않는 값도 적습니다: 결정당 프로세스 1,000개라도 짝 499,500개 → 결정당 ≤ 2.7 × 10⁻¹⁴, 58번 합쳐 ≤ 1.6 × 10⁻¹² [계산]. 실제로는 PID와 시작 시각까지 같아야 하므로 더 작습니다.
   - 그래도 겹치면: 배타 생성이 거절하고 오류 파일이 생겨 STOP입니다(§2.2-2). 덮어쓰기·조용한 섞임·거짓 PASS는 생기지 않습니다 [실행 P5; 검토 R4: 셋 가운데 둘만 토큰 전체가 같을 때도 첫 프로세스 파일 11개 바이트 그대로, 둘째는 시작 오류 파일 하나만, 셋째는 정상, 고르기 `hook_error`·VB-I7 거짓].
   - [검토] **실제 운영 체제의 PID 재사용 빈도** [실행 검토 R1·R1o]: 합성 프로그램 121개(어댑터 역 1 + 작업자 역 120)를 한 훅 폴더에 차례로 띄우자 PID 재사용이 새 훅 쪽 3번, 옛 훅 쪽 8번 일어났습니다(같은 기계, 강제 없음; 검토 도구를 세 번 돌린 기록에서 한 번에 2–8번, 새 훅은 세 번 모두 오류 0, 옛 훅은 세 번 모두 `hook_error`). 새 훅은 `loaded` 121·토큰 121(모두 다름)·후보 360·오류 0·고르기 `selected`·VB-I7 참(구동기·재계산기 같음)이었고, 옛 훅은 `loaded` 113(덮어씀)·`hook_error_<pid>.txt` 8개·고르기 `hook_error`·VB-I7 거짓이었습니다. 보충 32 P14의 "차례로 띄운 60개 프로세스의 PID 재사용 0"(`cmd /c exit`)은 이 기계의 재사용 빈도를 낮게 본 것입니다.
3. **탄젠트 작업자끼리**: 작업자는 어댑터가 `subprocess.run([sys.executable, '-B', worker, …])`(차례로, `sdmpc_tangent.py:62`)이나 `subprocess.Popen([...])`(둘이 함께, `sdmpc_tangent_concurrent.py:53`)으로 띄우는 **새 파이썬 프로세스**입니다 [읽음]. 환경(`PYTHONPATH`의 HOOKDIR, `K92VB_*`)을 물려받아 시작 때 훅을 따로 읽고, 그때 자기 토큰을 따로 만듭니다. Windows에는 fork(부모 프로세스 메모리를 복사해 자식을 만드는 방식)가 없으므로 부모의 토큰을 물려받는 길이 없습니다 [추론]. 멈춘 실행의 겹침(차례로 뜬 두 작업자가 PID 26704)은 이 경우입니다.
4. **결정끼리**: 결정마다(그리고 ZI 칸마다) 훅 폴더가 따로이고, 구동기가 빈 새 폴더로 만들며 다시 쓰지 않습니다(§2.2-4). 그래서 다른 결정의 이름과 만날 일이 없습니다. 같은 가짜 PID로 두 결정 폴더를 만든 합성 시험에서 두 폴더 이름이 겹치지 않고 둘 다 `selected` [실행 P7].
5. **판정 도구가 이름을 읽는 법**: 고르기·구동기 VB-I7·재계산기는 이름을 앞머리(`c_*`, `loaded_*.json`, `hook_error_*.txt`, `hook_setup_error_*.txt`)로만 찾고, PID·순번은 `cand.json` 안에서 읽습니다(`vb_select.py:128-142`, `KV2/vb_chain.py` `vbi7`(:522), `KV2/vb_recalc.py` `reselect`(:136)·`i7_of`(:206)) [읽음]. 새 이름도 같은 앞머리라 세 도구 모두 바꿀 필요가 없습니다 [실행 P2–P7]. [검토] 세 도구 가운데 폴더·파일 이름을 잘라 PID·순번을 읽는 곳은 없습니다(이름 쪼개기·정규식 0) [읽음 `vb_select.py`, `vb_lib32.py`, `KV2/vb_chain.py`, `KV2/vb_recalc.py` 전문 검색].
6. [검토] **동시에 뜬 작업자**: 같은 PID·같은 `time_ns`로 강제한 12개를 동시에 띄우고 각자 스레드 4개로 `omega_costs`를 부르게 해도 토큰 12개(난수 조각만 다름)·후보 48·오류 0·맞음 12·`selected`·VB-I7 참이었습니다 [실행 검토 R2]. 실제로는 동시에 살아 있는 프로세스의 PID가 다르므로 이보다 쉬운 꼴입니다(`sdmpc_tangent_concurrent.py:53`의 `Popen` 작업자와 `_evaluate_single`의 작업자가 함께 뜨는 자리).
7. [검토] **한 프로세스 안에서 훅이 두 번 실리는 꼴**(다시 시도의 한 꼴; `importlib.reload(sitecustomize)`로 강제) [실행 검토 R3]: 새 훅은 그 프로세스에 토큰을 하나 더 만들고 `sys.monitoring` 도구 번호를 하나 더 써서, 같은 `omega_costs` 호출마다 후보가 둘(토큰마다 하나) 생깁니다. 작업자 역이면 `loaded` 둘·후보 6(호출 3 × 2)·오류 0이고, 두 후보의 기록이 같아 고르기는 `selected`, VB-I7 참입니다(고른 기록은 그 호출의 기록 그대로). 어댑터 역이면 어댑터 `loaded`가 둘이 되어 VB-I7 1번(어댑터 `loaded` 정확히 하나)이 거짓 → STOP 쪽입니다. 옛 훅은 두 꼴 모두 `loaded` 덮어씀·후보 폴더 겹침 → `hook_error`(STOP 쪽)였습니다. GWT8의 `evaluation`·`src`·`scripts`에는 `sitecustomize`·`site.main`·`importlib.reload`가 없습니다 [실행 grep 0]. 그래서 이 꼴은 V-B에서 생길 길이 보이지 않고 [추론], 생겨도 거짓 기록이 고르기에 들어가지 않습니다. VerifyVB가 같은 PID 토큰 묶음의 후보 시각이 겹치는지 보고합니다(§6.5).
8. [검토] **결정 단계의 다시 시도**: 반쯤 된 사슬 결정은 훅 폴더를 `hook/t<T6>_interrupted_<시각>`으로 옮긴 뒤 새 빈 폴더로 다시 돌고(`move_interrupted`, :571-591), 반쯤 된 ZI 칸은 칸 폴더 전체를 옮깁니다(§2.2-4). 고르기·VB-I7·재계산기는 결정의 훅 폴더 경로 하나만 읽으므로 옮긴 폴더의 이름과 만나지 않습니다 [읽음]. 어댑터가 실패한 작업자를 다시 띄우면 새 프로세스라 새 토큰입니다(§2.4-3).

### 2.5 바뀌지 않는 것

- 대상(`sdmpc.py`의 `omega_costs`, `PY_START`), 켜는 스위치(`K92VB_HOOK_DIR`), 기록기 sha 확인과 세 입구(`network_facts`, `collect`, `write(…, 3, None)`), 읽기 규칙(AD 값은 `.value`만), `sys.monitoring` 도구 번호, 행동 서명, 후보 메타와 `loaded` 파일의 칸 이름 [실행 `dry_a33_hook.json` `on_normal`: `cand.json` 키 24개·`loaded` 키 15개가 보충 32 훅과 같은 목록].
- 더한 호출은 프로세스마다 시작 때 `os.urandom(8)` 한 번과 `time.time_ns()` 한 번입니다(옛 훅도 시작 때 `time.time_ns()`를 `started_ns`로 읽었음). 새 import 0.
- 보충 32 §3.1–§3.6의 나머지 글(싣는 법, 프로세스·횟수, 결정마다 자리, 고르기 규칙, VB-M5·M6·M8 읽는 법, 키 끔 14결정)은 그대로입니다.

### 2.6 고르기 `vb_select.py` — 바꾸지 않음

- 바이트 그대로(`33adfd50…`). 새 이름이 요구하는 고침이 없습니다(§2.4-5).
- 같은 순서 값이 겹칠 때: 맞는 후보의 순서 열쇠는 (AD 여부, `time_ns`, pid, 순번)이고(`vb_select.py:162-163`), 열쇠가 모두 같으면 파이썬 정렬이 안정적이라 폴더 이름 순서(`sorted(glob('c_*'))`, :142)가 남습니다. 재계산기 `reselect`도 같은 두 단계라(`KV2/vb_recalc.py:150-162`) 두 도구가 같은 후보를 고릅니다 [읽음]. 같은 PID·같은 `time_ns`로 강제한 P4에서 두 도구의 상태·고른 폴더·기록 sha가 같았습니다 [실행].
- 옛 이름에서는 PID 재사용이 이 순서 열쇠도 겹치게 할 수 있었지만, 그 전에 폴더가 겹쳐 STOP이었습니다.

---

## 3. 다른 도구 (차이는 부록 B·C)

### 3.1 새 구동기 `KV2/vb_chain.py` (옛 `KV/vb_chain.py` `4dc9297d…`의 사본을 고침)

- sha256 `87b89ce48b6552b4967cc5416d2e56d5f9f6d20d887d9997385df4f1be521322`(2,084줄, 108,273 B, LF). 차이 `AD33/diff/vb_chain.diff`(504줄) `976c31d0a8133ea199fe209ad90b1065aca63393123157026164007be883a3c2`.
- 기계 확인 [실행 `dry_a33_static.json`]: 옛 판과 다른 최상위 함수는 정확히 14개 — 고친 11개(`allowed`, `ok2_listing`, `pins_check`, `v0`, `v1`, `v9`, `v10`, `cmd_chain`, 자기 시험 `st_ad32`·`st_guard`·`st_judge`) + 새 3개(`archive_listing`, `archive_bytes`, `pin_line_ok`) — 이고, 이것이 선언 목록과 같습니다. import 목록은 같습니다. 그 밖의 함수(준비 `prepare`, 발사 `adapter_launch`, 결정 `decision`, ZI `zi_cell`, VB-I1 `v5`, VB-I2·I6·I7 `vbi2`·`vbi6`·`vbi7`, 지표 `v8`·`record_metrics`, 영수증, 이어 하기)는 바이트 그대로입니다.

| 자리 | 고친 것 | 까닭 |
|---|---|---|
| 상수 | `KV2`, `AD33`; `HOOKDIR = AD33/vbhook`; `HOOK_SHA = 691fe810…`; `VBT_NAME = 'vb2_e27ceac8'`; `VBR = OK2/vb2`; `OLD_VBT`·`OLD_VBT_BUILD`·`OLD_VBR`; 보충 32·고정점 32 sha를 C1 표에 더함; 보충 33 자리(`A33`, `.sha256`, `_r1`, `FIXED33`); 결정 기록 앞 214줄 sha; 기대 고정 목록 `AD33/a33_pins.expected.sha256`, 고정 목록 `KB/a33_pins.sha256`; 보관 sha 상수(옛 훅, 보충 32 고정 목록, 옛 V-B 고정 목록, STOP 판 r1, 옛 빌드 기록) | 새 자리·새 고정·보관(§5, §7) |
| `allowed`(쓰기 지킴) | 거부: 옛 VBR·옛 VBT·옛 빌드 기록·KV·AD33 더함. 허용: VBR(vb2)·KV2, 스냅숏 `s43–s46_vb2_*.json`, 로그 `vb2_*` | 보관 보호, 새 자리 |
| `ok2_listing` | OK2 훑기에서 `vb2`만 뺌(옛 `vb`는 이제 포함), 새 스냅숏·로그 이름만 뺌 | 옛 VBR이 바뀌면 V10에 보임 |
| `archive_listing`(새) | 옛 VBT 트리와 빌드 기록의 이름·크기·시각 목록 sha | TK는 읽기 전용 스냅숏 뿌리 밖이라 따로 봄 |
| `archive_bytes`(새) | 보충 32 고정 목록 51/51과 파일 sha, 옛 V-B 고정 목록 4/4와 파일 sha, 옛 훅 sha, 옛 빌드 기록 sha, 옛 VBR·VBT 있음, STOP 판 r1 사본 셋 = `d7bf44f3…` | 보관 바이트 보호 |
| `pins_check`, `pin_line_ok`(새) | 고정 줄에 기대 sha를 함께 돌려줌; 한 파일 줄이 한 번·같은 sha인지 봄 | V0 C5 |
| `v0` | C1 = 보충 24–32; C2 = 보충 33(§7); C3 = 앞 214줄; C5 = 보충 33 고정 목록; 새 C13 = `archive_bytes`; 보관 트리 목록 기록 | §6.2 |
| `v1` | LOG 글의 트리 이름 | 표시만 |
| `v9` | 재계산기 자리 KV2 | 새 파일 |
| `v10` | 보충 33 고정 목록, 보관 트리 목록 = V0, 보관 바이트 참을 더함; 보관 거짓이면 S-K57 | §6.2, §10 |
| `cmd_chain` | 훅 점검에 "새 훅 sha ≠ 옛 훅 sha, HOOKDIR 파일 하나"를 더함; 스냅숏 이름 `s43_vb2_v0`·`s44_vb2_zi`·`s45_vb2_off`·`s46_vb2_end`; C13 거짓이면 S-K57; LOG 글 | §6 |
| 자기 시험 `st_guard`·`st_judge`·`st_ad32` | 허용 8·거부 41(옛 27 + 보관·옛 이름 14); 새 이름 VB-I7 두 사례(같은 PID 두 작업자 → 참, 그 하나에 오류 파일 → 거짓); 고르기·도움 함수·닫힌 목록 = 보충 32 고정 목록 2·3·5줄, 훅 = 새 훅(옛 훅 1줄과 다름) | 자기 시험 |

- 자기 시험 [실행]: `KV2/selftest/vb_selftest.json` sha256 `a649aaa5094bf0b94aebe5c4eed9418193cfa032b6ec20c97145744ddd6f8922` — t1 발사 규칙(GWT8 `k92_replay.py` 822dd78f와 인자·작업 폴더·환경 같음 5꼴), t2 RR 영수증 5/5 바이트 같음·합성 쓰기 규칙, t3 쓰기 범위(허용 8·거부 41), t4 사슬 계획 55행, t5 VB-I2·I6·I7 29사례, t6 이어 하기, t7 도구 고정 — **모두 참**. 자식 프로세스 0(`subprocess.Popen/run`을 막은 채).

### 3.2 새 재계산기 `KV2/vb_recalc.py` (옛 `cab7939d…`의 사본)

- sha256 `6531a5e8eab37201781d4f81c80c7090b1546c2511c128c5db58026f28625d8b`(766줄, LF). 차이 `AD33/diff/vb_recalc.diff`(51줄) `b020af092a354bf4dd8ae5c95635928aca177db76253cc6cadf2d9b28cbf09ff`, 전문은 **부록 C**.
- 고친 것: 머리 설명, `TK_VBT = TK/vb2_e27ceac8`(팔 파일 VB-I3을 다시 낼 때 바탕 파일 자리), 자기 시험에 새 이름 사례 셋(같은 PID 두 작업자 → `selected`·더 이른 `time_ns` 고름, VB-I7 참, 오류 파일 하나 → `hook_error`·VB-I7 거짓). 바뀐 최상위 함수 = `selftest` 하나 [실행 static]. 독립 조건(표준 라이브러리와 numpy만, 구동기·AD32·하네스 import 0)은 그대로.
- 자기 시험 [실행]: `KV2/selftest/vb_recalc_selftest.json` sha256 `9e7d864a7eff440c0ad62cecca01d299a0f7ef4135eca647919d14d8d52c6379`, 26사례(옛 23 + 새 3) **모두 참**.

### 3.3 새 확인 도구

| 파일 | sha256 | 하는 일 |
|---|---|---|
| `AD33/dry_a33.py`(930줄) | `d1992a8c244c654b5663f8b14fe8875f9682549a5f7f0b888972b41ed9b027ab` | §4의 합성 확인 다섯 부분 |
| `AD33/run_bn.py`(11줄) | `c635e1513d71ad071a788d740d7ae637c22f8c73b12cea132cdfca4e6ff153ee` | 명령 하나를 BelowNormal로 띄우려 함(자기 시험용). [검토] **설정이 조용히 실패함**: `ctypes.windll.kernel32.GetCurrentProcess()`의 기본 반환형(int)이 가짜 핸들을 32비트로 잘라 `SetPriorityClass`가 0을 돌려줌(ERROR_INVALID_HANDLE 6) [실행]. 바이트는 고정 목록 10줄이라 그대로 두고, **V-B 단계에서 쓰지 않습니다**(공개 P14) |
| `AD33/make_pins33.sh`(33줄) | `fa59909897ef1759fdbe3e7cf92da1c088a50e9e8b77a7790b2b9af367e83bd9` | 기대 고정 목록 63줄을 만듦(§7) |

### 3.4 바꾸지 않은 도구 (보관 또는 그대로 씀)

- 그대로 씀: `AD32/vb_select.py`, `AD32/vb_lib32.py`, `AD32/vb_closed_leaves.json`, KI 도우미 넷, `gprep.py`, GWT8 하네스 파일들(§7 목록).
- 보관(읽기만, 쓰지 않음): `AD32/vbhook/sitecustomize.py`(옛 훅), `KV/vb_chain.py`, `KV/vb_recalc.py`, `KV/selftest/`, `KV/vb_pins.sha256`, `KB/a32_pins.sha256`.

---

## 4. 합성 PID 재사용 자기 시험과 그 밖의 합성 확인 (`AD33/dry_a33.py all`) [실행]

### 4.1 방법

- 실제 운영 체제에 PID 재사용을 강제할 수는 없습니다. 그래서 합성 자식 프로세스를 `python -S`(시작 때 `site`를 읽지 않음)로 띄우고, 프로그램 맨 앞에서 `os.getpid`를 상수(4242)로 바꾼 뒤 `site.main()`을 불러 훅(`sitecustomize`)을 읽게 합니다. 훅은 보통 시작과 같은 코드로 실리지만, 시작 때 보는 PID가 4242가 됩니다. 이런 자식 둘 = "운영 체제가 한 결정의 두 프로세스에 같은 PID를 준 것". 몇 사례는 `time.time_ns`·`os.urandom`도 상수로 바꿉니다.
- 합성 프로그램은 보충 32 `dry_a32.py`의 것과 같은 꼴(합성 `sdmpc.omega_costs`, 합성 `Dual`, 50 s 행 9개)에 `idle`(어댑터처럼 `omega_costs` 호출 없음) 꼴을 더했습니다. 프로그램 이름은 `vissim_stackelberg_adapter.py`(어댑터 역)와 `sdmpc_tangent_worker.py`(작업자 역)입니다. 기록기는 커밋 바이트(`1d1dfa36…`) 사본입니다.
- 결정 하나 = 빈 훅 폴더 + 어댑터 역 1(보통 시작, 실제 PID) + 작업자 역 여럿. 끝나면 고르기 `AD32/vb_select.py`를 자식으로 돌리고(합성 출력 JSON = 서명 A), 새 구동기의 `vbi7`과 새 재계산기의 `reselect`·`i7_of`를 같은 폴더에 부릅니다.
- 통제 P8: `-S` 시작 + 상수 없음과 보통 시작이 같은 결과·같은 기록 바이트를 내는지 봅니다(이 강제 방법이 훅 동작을 바꾸지 않음).

### 4.2 결과 — PID 재사용 (`dry_a33_pidreuse.json` `a81f1675…`)

| 사례 | 꾸민 것 | 결과 | 기대 | 판정 |
|---|---|---|---|---|
| P1 **옛 훅**, 같은 PID 작업자 둘 차례로 | 보충 32 훅 | `loaded` 2개(프로세스 3개 — 하나 덮어씀), 후보 3, `hook_error_4242.txt` 1, 고르기 `hook_error`, VB-I7 거짓(구동기·재계산기 모두) | 멈춘 실행의 겹침을 합성으로 다시 냄 | 참 |
| P2 **새 훅**, 같은 PID 작업자 둘 차례로 | | `loaded` 3(토큰 3개, 4242로 시작 2개), 후보 6, 오류 0, 고르기 `selected`(맞음 4, 고른 것 = 첫 작업자의 순번 1·pid 4242), VB-I7 참, 재계산기와 같음 | 겹침 없음 | 참 |
| P3 새 훅, 같은 PID 작업자 둘 **동시에** | 운영 체제에선 못 일어나는 꼴(견고성) | `loaded` 3, 후보 6, 오류 0, `selected`, VB-I7 참, 두 도구 같음 | 겹침 없음 | 참 |
| P4 새 훅, 같은 PID **+ 같은 `time_ns`** | 시계 겹침 | 토큰 둘이 `4242_1761111111000000000_`까지 같고 난수 조각만 다름, 후보 6, 오류 0, `selected`, 두 도구의 고른 폴더·기록 sha 같음(순서 열쇠가 같아 폴더 이름 순서로 갈림) | 난수 조각이 가름 | 참 |
| P5 새 훅, **토큰 전체 강제 겹침**(PID·시각·난수 모두 같음) | 일어날 확률 ≈ 0인 꼴 | 둘째 프로세스: `loaded` 배타 생성 거절 → `hook_setup_error_4242_1761111111000000000_00112233aabbccdd.txt` 하나만 새로 생김, 훅은 그 프로세스에서 꺼짐; **첫 프로세스 파일 sha 모두 그대로**; 고르기 `hook_error`, VB-I7 거짓 | 거절·덮어쓰기 없음·STOP 쪽 | 참 |
| P6 새 훅, 멈춘 결정 꼴 | 어댑터 + 작업자 4(그 가운데 둘이 4242, 사이에 다른 작업자) | `loaded` 5, 후보 12, 오류 0, `selected`(맞음 8), VB-I7 참, 두 도구 같음 | 겹침 없음 | 참 |
| P7 새 훅, 결정 둘 | 두 결정 폴더 각각 4242 작업자 | 두 폴더 이름 겹침 0, 둘 다 `selected`·VB-I7 참 | 결정끼리 독립 | 참 |
| P8 통제 | `-S` 시작(상수 없음) 대 보통 시작 | 종료 0·0, 결과 같음(= 훅 없는 기준), 후보 기록 3개 바이트 같음 | 강제 방법이 동작을 바꾸지 않음 | 참 |

- 모든 사례에서 합성 프로그램의 결과값은 훅 없는 기준과 같았습니다(P1 포함: 옛 훅의 오류도 프로그램 결과를 바꾸지 않음).

### 4.3 결과 — 망가뜨림 (`dry_a33_mutants.json` `48bb9e64…`)

새 훅의 고침을 한 곳씩 되돌린 네 벌을 같은 PID 재사용 꼴로 돌려, "`loaded` 3·후보 6·오류 0·첫 프로세스 파일 그대로·`selected`·VB-I7 참"이 아니면 잡은 것으로 셉니다.

| 망가뜨림 | 결과 | 잡음 |
|---|---|---|
| M1 후보 폴더 이름을 PID만으로 | 오류 1, `hook_error`, VB-I7 거짓 | 잡음 |
| M2 `loaded` 이름을 PID만으로 + `w` | `loaded` 2(덮어씀), 첫 파일 바뀜 — **고르기 `selected`·VB-I7 참으로 남음** | 잡음(파일 비교로만) |
| M3 토큰에서 난수 조각 뺌 + 같은 `time_ns` | 시작 오류 1, `hook_error`, VB-I7 거짓 | 잡음 |
| M4 배타 생성 뺌(`w`, `makedirs(exist_ok=True)`) + 토큰 전체 겹침 | 오류 0, 첫 파일 바뀜(조용히 덮어씀) — **`selected`·VB-I7 참으로 남음** | 잡음(파일 비교로만) |

- M2·M4는 중요한 점을 보입니다: 덮어쓰기가 일어나면 VB-I7과 고르기는 그것을 보지 못합니다. 그래서 이 보충은 이름 토큰과 함께 **배타 생성**을 요구합니다(덮어쓰기 자체가 일어날 수 없게). VB-I7에 새 조건을 더하지는 않았습니다(공개 P9).

### 4.4 그 밖의 합성 확인

- **static** (`dry_a33_static.json` `e7f4e8d3…`): 훅 import = `hashlib, json, os, sys, threading, time, traceback, types`(옛 훅과 같음); HOOKDIR 파일 하나; 열기 모드·`makedirs`·`mkdir` 자리(§2.2-1); 이름 문자열 = `%d_%d_%s`, `%d_notoken`, `c_%s_%04d`, `hook_error_%s.txt`, `hook_setup_error_%s.txt`, `loaded_%s.json`; 대상·스위치·세 입구 글자; 훅 차이 = 선언 목록(§2.3); 구동기 바뀐 함수 14개 = 선언 목록, 재계산기 = `selftest` 하나, 두 파일 import 같음; 옛 구동기·재계산기·고르기 sha = 고정값 — **모두 참**.
- **hook** (`dry_a33_hook.json` `6f711a9b…`): 보충 32 `dry_a32.py`의 훅 사례 아홉(기준 실행 포함)을 새 훅으로 다시 — 훅 경로 없음/스위치 끔/켬 결과 같음, 끔에서 파일 0·모듈 목록 같음, 켬에서 후보 3(비AD·비AD·AD)·파일 셋·서명·메타·기록 값 맞음·`evaluation`·`src` 모듈 더함 0·`k92_record`가 `sys.modules`에 없음, 기록기 sha 다름·`K92VB_T` 없음 → 시작 오류(이름에 토큰)·후보 0·결과 같음, 응답 읽기 예외 → `hook_error_<토큰>.txt` 1, 스레드 4 → 후보 4(이름 넷 모두 다르고 토큰 꼴, 오류 0), 다른 파일의 `omega_costs` → 후보 0, 다른 프로그램 이름 → 후보 3. 모든 이름이 토큰 꼴. 훅 켬에서 더 실린 모듈은 보충 32 때와 같은 표준 라이브러리 24개 — **모두 참**.
- **paths** (`dry_a33_paths.json` `6749ff77…`): `k92_a27.tree_root_ok('…/k92b1/vb2_e27ceac8')` 참(옛 이름도 참); KC `norm_s`가 새·옛 트리 아래 파일 경로를 모두 `<root>/…`로 바꿈(역슬래시도); OK2 출력 경로는 옛날처럼 N이 바꾸지 않고 `vb2`/`vb` 글자만 다름 — **참**. 그래서 트리 이름이 바뀌어도 VB-I1·ZI 비교의 경로 처리는 멈춘 실행과 같습니다 [추론].
- **요약** `dry_a33_summary.json` `de72ea283b2529ac5d3eac868ab70fc33a056725e7bd15e48cb0e4343a98af3b`: 다섯 부분 모두 참, BelowNormal 참.

---

## 5. 새 자리와 보관

| 것 | 새 자리 (이 재실행) | 보관 (읽기만; 바뀌면 STOP — 아래 셋) |
|---|---|---|
| V-B 출력 뿌리 | **VBR = `OK2/vb2`** | `OK2/vb`(2.5 GB, 1,129 파일) |
| V-B 트리 | **VBT = `TK/vb2_e27ceac8`** + `TK/vb2_e27ceac8.build.json`(V1이 `git archive e27ceac8` + CR 고침으로 만듦) | `TK/vb_e27ceac8`(2.1 GB, 10,659 파일) + `.build.json` `2ace3363…` |
| 구동기·재계산기·자기 시험 | **`KV2`** | `KV/vb_chain.py`·`vb_recalc.py`·`selftest/`·`vb_pins.sha256` |
| 훅 | **`AD33/vbhook/sitecustomize.py`** | `AD32/vbhook/sitecustomize.py`(`4d7e0375…`) |
| 고정 목록 | **`KB/a33_pins.sha256`** = `AD33/a33_pins.expected.sha256` 바이트 | `KB/a32_pins.sha256`·`AD32/a32_pins.expected.sha256` |
| 스냅숏 | `OK2/snap/s43_vb2_v0`·`s44_vb2_zi`·`s45_vb2_off`·`s46_vb2_end.json` | `s38_vb_v0`·`s39_vb_zi`(옛 실행), `s42_a33decl`(이 단계) |
| 발사 로그 | `OK2/logs/vb2_chain.txt`(launch.ps1 `-Tag vb2_chain`) | `OK2/logs/vb_chain.txt`·`vb_stop_snap.txt` |
| 보고서 | §8 | STOP 판 r1 사본 셋 |

- **보관을 지키는 셋** [읽음 `KV2/vb_chain.py`]: (가) 쓰기 지킴 `allowed`이 보관 자리 모두를 거부합니다(자기 시험 t3: 보관 14경로 거부 참). (나) V0 C13과 V10이 보관 바이트(`archive_bytes`)를 봅니다. (다) V0에서 옛 VBT 트리 목록(`archive_listing`)과 OK2 목록(옛 VBR 포함, `ok2_listing`)을 적고 V10에서 같은지 봅니다. (나)나 옛 VBT 트리 목록이 거짓이면 S-K57, OK2 목록이 다르면 보충 32와 같이 S-K53으로 STOP 파일에 적힙니다(OK2 목록은 옛 VBR과 OK2의 다른 폴더를 함께 담아 어느 쪽인지 가르지 않음; STOP 파일에 모든 점검 값이 남음). 어느 쪽이든 STOP이고 사용자가 정합니다.
- [검토] **(라) 검토 때 기준 값**: 위 셋은 V0부터 V10까지만 지킵니다(V0 목록이 기준). 멈춘 실행(옛 VBR 마지막 파일 14:07:20)부터 V0까지의 틈을 막으려고, 검토가 이름·크기·수정 시각 목록 둘을 냈습니다 [실행 `KB/a33review/out/rev_a33_archive.json`, 15:14]: 옛 VBT `TK/vb_e27ceac8` + 빌드 기록 = 구동기 `archive_listing()` 그대로 10,660행 `d51f4deefc53b69cdadd9472a6ea2ca9197f694760f26c2380e1a101a1089680`; 옛 VBR `OK2/vb` = 같은 코드 꼴(뿌리 `OK2/vb`, 덧붙인 행 없음) 1,129파일·2,665,452,354 B `392d10278514a2206fe9a6b5d22190708931ffabdecaf911037668f5f4ecd583`(가장 늦은 수정 시각 = STOP 판 r1 사본 14:07:20). 같은 때 `archive_bytes()` 아홉 점검 모두 참. 두 값은 고정점 33에도 적습니다. 목록 꼴(다시 낼 때 이대로; 구동기를 가져오지 않고 다시 짜도 됨): 뿌리를 `\\?\` 붙인 절대 경로로 두고 파이썬 `os.walk`(위에서 아래, 폴더마다 `dirs.sort()`, 파일 이름 `sorted()`)로 돌며 파일마다 행 `[os.path.relpath(폴더, 뿌리)의 '\\'→'/' + '/' + 이름, st_size, round(st_mtime, 6)]`(뿌리 바로 아래 파일은 `./이름`); 옛 VBT는 끝에 `['../vb_e27ceac8.build.json', 크기, round(수정 시각, 6)]` 한 행을 더함; 값 = `json.dumps(행 목록)`(기본 구분자) 바이트의 sha256. `\\?\` 접두어가 없어도 값은 같습니다 [실행: 구동기를 가져오지 않고 접두어 없이 다시 짠 꼴로 같은 두 값]. VerifyVB가 V0의 `archive_tree`와 자기 때 다시 낸 두 목록을 이 값과 견줍니다(§6.5). 파일 시각으로 본 것: 옛 VBR 안에 14:07:20보다 늦은 파일 0, 옛 VBT 안에 11:28:38(접선 캐시)보다 늦은 파일 0 [실행 `find`].
- 이 단계 스냅숏 `OK2/snap/s42_a33decl.json`(`4e55240d…`)은 s02 대비 SAME입니다 [실행]. RR·동결본·몫 가르기 트리 등 읽기 전용 뿌리가 STOP 뒤에도 그대로라는 뜻입니다.

---

## 6. 다시 돌리는 순서 (V-B 단계가 할 일)

### 6.1 시작 전 (V-B 단계, 사슬 계산 0인 동안)

1. 보충 33 고정판 sha = `.sha256` = 고정점 `KB/AMENDMENT33_FIXED.md` 안의 64자(§7).
2. `cp AD33/a33_pins.expected.sha256 KB/a33_pins.sha256`, `cmp` 같음, `sha256sum -c` 63/63 OK.
3. LOG 한 항목: 고정점 33 파일 sha(64자), `KB/a33_pins.sha256` sha(64자), 구동기 `87b89ce4…`·재계산기 `6531a5e8…`(64자). 구동기 V0 C2·C5가 이 셋을 LOG에서 기계로 봅니다.
4. 자기 시험은 **다시 돌리지 않습니다**(출력이 고정 목록에 들어 있어 다시 쓰면 S-K53).
5. 발사: `KI/launch.ps1 -Tag vb2_chain -Script ..\k92_vb2\vb_chain.py -ArgLine chain`(WMI 분리, BelowNormal, `PYTHONHASHSEED=0`, `python -B`). 기다림 확인은 한 번에 9분 이하, `VBR/steps.jsonl`·`stages/`·`STOP_vb_*` 이름만 봄. 자기 PID만 끔. [검토] 우선순위는 `launch.ps1`의 WMI 시작 정보(PriorityClass 16384)와 구동기의 `k92lib.set_below_normal()`(핸들 형을 밝혀 쓰고, 읽어 본 값이 BelowNormal이 아니면 멈춤 [읽음 KI `k92lib.py:80-91`])이 맡습니다. `AD33/run_bn.py`는 쓰지 않습니다(공개 P14).

### 6.2 구동기 단계 V0–V10 (보충 32 §4.2와 같은 순서·같은 통과 조건; 바뀐 칸만 굵게)

| 단계 | 내용 | 통과 조건 |
|---|---|---|
| V0 사전 점검 | C1 **보충 24–32**와 고정점 24–32 sha. **C2 보충 33**: 파일 sha = `.sha256` 앞 64자 = 고정점 33 안의 64자 낱말; Declare 판 `_r1`이 있으면 그 sha는 고정판과 같거나 고정점 안에 64자로 없음; 고정점 33 sha가 LOG에; 기대 고정 목록 sha가 고정점 33 안에 64자로. **C3 결정 기록 앞 214줄 sha = `18724234…`**(덧붙임만 허용). C4 GWT8 head `e27ceac8`·브랜치·K8 `b9734abe`·status 0·`b9734abe..HEAD` 6·원격 k92 0·이름에 vb 든 worktree 0. **C5 `KB/a33_pins.sha256` = 기대 바이트, 모든 줄 OK, 구동기·재계산기·훅·고르기·도움 함수·닫힌 목록 줄이 한 번씩 기대 sha로, 그 목록 sha와 구동기·재계산기 sha가 LOG에.** C6–C12 그대로. **C13 보관 바이트(§5).** **보관 트리 목록·OK2 목록(옛 VBR 포함)을 기록.** 훅 점검: 새 훅 sha = `691fe810…` ≠ 옛 훅 sha, HOOKDIR 파일 하나, 닫힌 목록 `b800be45…` | 모두 참; C13이 거짓이면 S-K57, 그 밖의 거짓만 있으면 S-K53 |
| 스냅숏 | **`s43_vb2_v0`**, s02 대비 | SAME |
| V1 트리 | `cglib.build_archive('vb2_e27ceac8', e27ceac8, cr_fix=True)` → **`TK/vb2_e27ceac8`** + 빌드 기록. 점검은 보충 32와 같음(`tree_root_ok`, CR 형태 `CCCCCCCCCC`, `cr_pair` 둘, RS `70cca680…`·SHO·CFG·SAF-K91·CFG-B1·REC·KC·`k92_replay.py`·`sa_arms.py` sha) | 모두 참 |
| V2 팔 | `sa_arms.py --root VBT --out VBR/arms --k92b1` → SAF-B1 `65cac7ea…`, VB-I3 두 팔, C12 | 모두 참 |
| V3 ZI | 보충 32 §3.5 그대로: `z1_off`(v3c3-s43 T=1,050, OFF), `z1_b1`(같은 상태, B1), `z2_b1`(v3c3-s43 T=750, B1); 칸마다 같은 준비 폴더·같은 출력 경로로 훅 끔 → 훅 켬; 규칙 (z1)–(z7) "G-K0 비교로 같고 벽시계 잎만 다름" | 세 칸 PASS(아니면 S-K51) |
| 스냅숏 | **`s44_vb2_zi`** | SAME |
| V4 OFF 사슬 | 순서 VB-41w(8) → VB-31(2) → VB-43(2) → VB-41(2); 결정마다 준비 → 재생(훅 켬) → 영수증 → 고르기 → 결정 기록 | 결정마다 종료 0 |
| V5 OFF 관문 | VB-I1 **사슬 첫 결정 4개**(VB-31·43·41 T=3,000, VB-41w T=1; 결과 넷 PASS, SDMPC 셋은 A_K92 줄 하나 이상·모두 참), OFF 14결정 VB-I2·VB-I7, 보고 전용 10결정 표(§9) | VB-I1 4/4 PASS, VB-I2·VB-I7 14/14 참(아니면 S-K55) |
| 스냅숏 | **`s45_vb2_off`** | SAME |
| V6 B1 사슬 | 순서 VB-41w(8) → VB-31(11) → VB-43(11) → VB-41(11) | 결정마다 종료 0 |
| V7 무결성 | VB-I2·I3·I4·I6·I7 55결정 | 모두 참 |
| V8 지표 | VB-M1–M9 표(보충 24 :556-566, 보충 32 §3.6) | 표가 만들어짐 |
| V9 재계산 | `python -B KV2/vb_recalc.py run --vbr VBR --dest VBR/recalc/recalc.json` → VB-I5 | 다시 낸 값 모두 같음 |
| 스냅숏 | **`s46_vb2_end`** | SAME |
| V10 끝 대조 | **보충 33 고정 목록 모두 OK·바이트 = 기대**, GWT8 상태 = V0, RR 목록 = V0, **OK2 목록(vb2 밖, 옛 VBR 포함) = V0, 옛 VBT 트리 목록 = V0, 보관 바이트 참** | 모두 참; 옛 VBT 트리 목록·보관 바이트 거짓 → S-K57, 그 밖(OK2 목록 포함) → S-K53 |

- 그 뒤 V-B 단계: 보고서(§8, §9) → LOG. 그다음 VerifyVB(§6.5). V-A와 푸시는 그 뒤 사용자 결정입니다.

### 6.3 그대로인 규칙 (보충 32를 그대로 따름)

- 판정 4결정과 규칙(보충 32 §2.1), 보고 10결정·닫힌 목록·`reportonly` 표(§2.2–§2.3), VB-I2–I6(§2.4), VB-I7(§2.5; 1번의 "`loaded_<pid>.json`"과 3번의 "`c_<pid>_<seq>`"는 §2.1의 새 이름으로 읽음 — 뜻 그대로), VB-I 결과 규칙(§2.6), 훅 싣기·기록기 입구·프로세스·고르기·ZI·VB-M5·M6·M8 읽기·키 끔 14결정(§3, 이름만 §2.1), 발사 규칙·직전 행동·영수증(§4.3–§4.4), 이어 하기(§4.7; 새 VBR 안에서만), 보고서 꼴(§5), 공개 P1–P15(§7).
- 같은 RR 상태·같은 팔 파일·같은 튜닝·같은 커밋 트리 바이트(e27ceac8 + CR 고침)를 씁니다. 바뀌는 것은 출력 자리 이름과 훅 이름 규칙뿐입니다.

### 6.4 이어 하기·실행 위생

- 보충 32 §4.7 그대로이되, 모두 `OK2/vb2`·`TK/vb2_e27ceac8` 안에서입니다. 옛 `OK2/vb`의 결정 출력은 **이어 받지도 다시 쓰지도 않습니다**(직전 행동으로도 쓰지 않음).
- 무거운 Python 한 번에 하나, BelowNormal, `python -B`, `PYTHONHASHSEED=0`, WMI 분리, 기다림 확인 9분 이하, 자기 PID만 끔, C:·D: 8 GB 밑이면 멈춤(S-K14), VISSIM·COM·러너·동결 0, 커밋·푸시 0, 금지 시험 0.

### 6.5 VerifyVB (보충 31 §4.4, 보충 32 §4.8에 더함)

- 더 보는 것: 훅을 켠 58개 훅 폴더(사슬 55 + ZI 3)의 모든 이름이 §2.1의 새 꼴인지(옛 꼴 0), 오류 파일 0인지, `loaded` 파일 수 = 그 폴더에 기록을 남긴 프로세스 수와 맞는지(같은 토큰의 후보 폴더마다 같은 토큰의 `loaded` 파일이 있음). 다르면 S-K50 STOP.
- [검토] 위 줄을 다음 넷으로 정확히 읽습니다(괄호 안 뜻 "같은 토큰 짝"은 그대로 두고, PID 일치·"그 밖의 이름 0"·순번 이어짐을 더함 — STOP을 늘리는 쪽, V-B 데이터 전에 정함; 넷 가운데 하나라도 거짓이면 S-K50 STOP). 토큰 꼴 `<P>_<N>_<H>` = `[0-9]+_[0-9]+_[0-9a-f]{16}`.
  1. **이름**: 훅 폴더 바로 아래 이름은 `loaded_<토큰>.json`, `c_<토큰>_<순번>`(순번 `[0-9]{4,}`, 폴더), `hook_error_<토큰>.txt`, `hook_setup_error_<토큰>.txt`, `hook_setup_error_<P>_notoken.txt`뿐입니다(그 밖의 이름 0, 옛 꼴 `loaded_<P>.json`·`c_<P>_<순번>` 0). 후보 폴더 안은 `cand.json`·`k92_record.json`이 있고 그 밖에는 `k92_series.npz`뿐입니다.
  2. **오류 0**: `hook_error_*`·`hook_setup_error_*` 0개(VB-I7 2번과 같은 뜻).
  3. **짝**: 후보 폴더의 토큰마다 같은 토큰의 `loaded_<토큰>.json`이 정확히 하나 있고, 그 `loaded`의 `pid` = 그 토큰의 첫 조각 = 그 토큰의 모든 `cand.json`의 `pid`입니다. 그래서 `loaded` 파일 수 = `loaded`와 후보 이름을 합쳐 센 서로 다른 토큰 수입니다(`loaded`만 있고 후보가 없는 토큰은 됨 — 어댑터처럼 `omega_costs`를 부르지 않은 프로세스).
  4. **순번**: 한 토큰 안의 순번은 1부터 빈틈없이 이어집니다(빈틈은 후보를 만들다 실패한 흔적이고, 그때는 2번이 이미 거짓).
  - 보고만(STOP 아님): 폴더마다 `loaded` 수·후보가 있는 토큰 수·같은 PID를 둘 이상 받은 토큰 묶음 수(§8-5), 그리고 그런 묶음마다 토큰들의 후보 `time_ns` 구간이 서로 겹치는지(차례로 뜬 프로세스면 겹치지 않음; 겹치면 §2.4-7의 "한 프로세스 안 두 번" 꼴로 눈에 띄게 보고).
- [검토] **보관 대조**(§5 (라)): (가) `VBR/check_v0.json`(처음 V0)의 `archive_tree` = `d51f4deefc53b69cdadd9472a6ea2ca9197f694760f26c2380e1a101a1089680`(10,660행), (나) VerifyVB 때 §5 (라)의 목록 꼴로 다시 낸 옛 VBT 목록 = 같은 값, (다) VerifyVB 때 같은 꼴로 다시 낸 `OK2/vb` 목록 = `392d10278514a2206fe9a6b5d22190708931ffabdecaf911037668f5f4ecd583`(1,129파일). 하나라도 다르면 S-K57 STOP(사용자). 목록은 이름·크기·수정 시각만 읽습니다(내용 열람 0).
- 도구는 새 파일, 첫 읽기 전 LOG 고정. 나머지는 보충 32 §4.8 그대로.

### 6.6 비용 [계산]

- 멈춘 실행 기록: ZI 6실행 약 48분(11:27–12:15), OFF 14결정 약 1.7 h, SDMPC 결정 하나 623–778 s [읽음 STOP 보고 r1 §3.4].
- 다시: ZI 약 0.8 h + OFF 14(SDMPC 8) 약 1.7 h + B1 41(SDMPC 35 × 약 12분 ≈ 7.1 h + 무제어 6) + 트리·팔·스냅숏 넷·재계산 약 0.3 h ≈ **9.5–10 h**(결정 기록의 "약 8–9 h"보다 조금 김; 실제 결정 벽시계 기준).
- 디스크: 멈춘 실행은 SDMPC 실행 12번에 약 2.5 GB → 이번 SDMPC 47번(사슬 43 + ZI 4)에 약 10 GB + 트리 2.1 GB ≈ 12 GB. D: 384 GB 여유.

---

## 7. 고정

### 7.1 기대 고정 목록 `AD33/a33_pins.expected.sha256`

- sha256 `a1b02027c3238dcb3cb55bae42e163d4d1ce60b0f7c688e44517efcfe9e7ac74`, **63줄**, 12,478 B, LF, CR 0 [실행 `sha256sum -c` 63/63 OK]. 줄 꼴 `<sha256 64자> *<절대 경로, / 구분>`(보충 30 §9·31 §8·32 §10과 같음). 만드는 도구 `AD33/make_pins33.sh`(63줄째).

| 줄 | 파일 | sha256 앞 16자 |
|---|---|---|
| 1 | `AD33/vbhook/sitecustomize.py`(새 훅) | `691fe8100e38d322` |
| 2–4 | `AD32/vb_select.py` / `vb_lib32.py` / `vb_closed_leaves.json`(그대로) | `33adfd5033c277a3` / `504999a196a9e085` / `b800be45ae3e4e50` |
| 5–8 | `KV2/vb_chain.py` / `vb_recalc.py` / `selftest/vb_selftest.json` / `selftest/vb_recalc_selftest.json` | `87b89ce48b6552b4` / `6531a5e8eab37201` / `a649aaa5094bf0b9` / `9e7d864a7eff440c` |
| 9–10 | `AD33/dry_a33.py` / `run_bn.py` | `d1992a8c244c654b` / `c635e1513d71ad07` |
| 11–16 | `AD33/dry/decl/dry_a33_{static,hook,pidreuse,paths,mutants,summary}.json` | `e7f4e8d3…` / `6f711a9b…` / `a81f1675…` / `6749ff77…` / `48bb9e64…` / `de72ea28…` |
| 17–19 | `AD33/diff/{hook,vb_chain,vb_recalc}.diff` | `144f90b9…` / `976c31d0…` / `b020af09…` |
| 20–22 | 보관: `AD32/vbhook/sitecustomize.py`(옛 훅) / `AD32/a32_pins.expected.sha256` / `KB/a32_pins.sha256` | `4d7e0375116c3f80` / `9e4dc5925e36fcc0` / `9e4dc5925e36fcc0` |
| 23–25 | 보관: `KV/vb_chain.py` / `KV/vb_recalc.py` / `KV/vb_pins.sha256` | `4dc9297df760800e` / `cab7939df8fd55ff` / `6bed354112b93b65` |
| 26–28 | STOP 판 r1 사본: `KV/K92_VB_REPORT_stop_r1.md` / `KB/VB_REPORT_stop_r1.md` / `OK2/vb/K92_VB_REPORT.md` | `d7bf44f3e309aa4a`(셋 같음) |
| 29–32 | 보관(멈춘 실행 증거): `OK2/vb/STOP_vb_V5.json` / `judge/vb_i1.json` / `judge/vb_reportonly.json` / `chain/vb41_off/hook/t003150/hook_error_26704.txt` | `4127cbf2bfbbd362` / `9c1749a9f7bc6331` / `30fcda3ec3e3d8b7` / `c98097670e66928d` |
| 33 | 보관: `TK/vb_e27ceac8.build.json` | `2ace33638b30a4da` |
| 34–36 | 보충 32 고정판 / 고정점 32 / `KB/k92_probe_a25/K92_VALUES.json` | `7f25c21e72fc2599` / `b59088ab44683f59` / `296c659562e45528` |
| 37–40 | `KB/GATES_K92B1_A31.md` / `KB/VERIFY_GATES_K92B1_r3.md` / `KB/vgates4/out/vg4_result.json` / `KB/a31_pins.sha256` | `e2b301837feb35d6` / `6fb66ac5b8de8bbd` / `0b7654eca9e1165f` / `bf1ca001e8c8a421` |
| 41–44 | KI `k92lib.py` / `cglib.py` / `launch.ps1` / `k92snap.py` | `ae5de0ccd90d688c` / `be5a0c95ad7bc86d` / `bf7a81322086625d` / `0dbd7d2c75f982d8` |
| 45–46 | `SP/j1/fix/gates/gprep.py` / `gcommon.py` | `0482a53868fd3ee6` / `556a6511c5b17c5f` |
| 47–52 | GWT8 `k8_gates/sa/` `k92_compare.py` / `k92_record.py` / `k92_replay.py` / `sa_arms.py` / `k92_a27.py` / `k92_common.py` | `3e2da987…` / `1d1dfa36…` / `822dd78f…` / `578a8707…` / `d4ab3f3d…` / `cb2a0335…` |
| 53–56 | GWT8 `evaluation/controllers/sdmpc.py` / `scripts/run_real_world_stackelberg_controller.vbs` / `tools/make_replay_state_v2.py` / FRZ_K8b 같은 파일 | `8f91298a…` / `bffb59f8…` / `4adf41cf…` / `4adf41cf…` |
| 57–61 | RR 영수증 다섯(보충 32 §0과 같음) | `602f2a85…` / `61983196…` / `f72c349e…` / `574dfdc1…` / `561652c6…` |
| 62 | `OK2/snap/s42_a33decl.json`(이 단계 스냅숏) | `4e55240d36e460f3` |
| 63 | `AD33/make_pins33.sh` | `fa59909897ef1759` |

- 목록에 넣지 않는 것(창 안에서 바뀜): `KB/LOG.md`, 결정 기록(앞 214줄만 V0 C3), 보충 33 자신과 고정점(구동기가 C2로 따로 봄), VBR·VBT(새 출력), `KV/K92_VB_REPORT.md`·`KB/VB_REPORT.md`(새 판으로 덮어씀, §8), 합성 트리 `AD33/dry/syn`·`KV2/selftest/syn`.

### 7.2 고정점 33이 적어야 하는 것 (반박 검토의 일)

- 고정판 보충 33의 sha256(64자), 기대 고정 목록 `AD33/a33_pins.expected.sha256`의 sha256(64자; 검토가 목록을 바꾸지 않으면 `a1b02027c3238dcb3cb55bae42e163d4d1ce60b0f7c688e44517efcfe9e7ac74`). Declare 판 보충 33의 sha는 앞 16자만(되돌린 파일이 V0 C2를 통과하지 않게; 보충 29 §14.1 V4·보충 32와 같은 까닭). Declare 판은 `SP/K8_PREDECLARATION_AMENDMENT_33_r1.md`로 남깁니다(구동기 V0 C2가 이 이름을 봄).
- 검토가 도구 바이트(훅·구동기·재계산기·확인 도구)를 바꾸면: 자기 시험 둘과 `dry_a33.py all`을 다시 돌리고, `make_pins33.sh`로 목록을 다시 만들고, 고정점에 새 목록 sha를 적습니다. 구동기 안 상수(`HOOK_SHA` 등)도 그에 맞춰야 합니다.

### 7.3 고정 창

- V-B 단계의 시작 전 고정(§6.1)부터 V10 끝 대조까지. 그 안에서 63개 가운데 하나라도 바이트가 바뀌면 STOP입니다. 구동기는 보관 바이트 점검(`archive_bytes`: 20·22·23–28·33줄의 파일과 옛 VBR·VBT 있음)이 함께 거짓이면 S-K57, 아니면 S-K53으로 적습니다(§10). 결과를 보았든 아니든 고정 뒤 훅·고르기·도움 함수·닫힌 목록·구동기·재계산기를 고치면 S-K53입니다.

---

## 8. 보고서 판·보관 규칙

1. **보관(이미 함)** [실행]: STOP 판 r1(`d7bf44f3…`)의 바이트 사본 `KV/K92_VB_REPORT_stop_r1.md`와 `KB/VB_REPORT_stop_r1.md`를 이 Declare 단계가 만들었습니다(`cp -p`, `cmp` 같음). `OK2/vb/K92_VB_REPORT.md`(같은 바이트)는 보관으로 그대로 둡니다. 셋 모두 고정 목록 26–28줄이고 구동기 V0·V10이 봅니다. 이 셋은 다시 쓰지 않습니다.
2. **새 판**: 재실행 보고서는 **r2**입니다(끝까지 가면 완료 판 r2, 중간에 멈추면 STOP 판 r2). 정본 `KV/K92_VB_REPORT.md`를 r2로 덮어씁니다. 덮어쓰기 전에 두 보관 사본이 `d7bf44f3…`인지 봅니다(아니면 덮어쓰지 않고 STOP).
3. **같은 바이트 사본 둘**: `KB/VB_REPORT.md`, `OK2/vb2/K92_VB_REPORT.md`(VBR 안; V10 뒤에 씀). 셋을 `cmp`로 보고, 세 sha를 LOG에 적습니다. 사본만 고치는 일은 없습니다(정본을 고치고 다시 복사).
4. **머리**: 판 이름(r2, 보충 33 재실행), r1 자리(`KV/K92_VB_REPORT_stop_r1.md`, `d7bf44f3…`), 쓴 자리(VBR = `OK2/vb2`, VBT = `TK/vb2_e27ceac8`), 보충 27–33의 공개 옮김. 첫 줄 가까이에 §9의 묶음.
5. **본문**: 보충 32 §5 그대로(V0–V10 결과, ZI 표와 훅 비용, VB-I 표, 보고 전용 10결정 표, VB-M1–M9 표, 고르기 상태 개수, 한계). 더해 훅 폴더 이름 요약(훅 켠 58폴더의 `loaded` 수·토큰 수·같은 PID를 둘 이상 받은 토큰 묶음 수 — PID 재사용이 이번에 몇 번 일어났는지; 보고만).
6. 판정 말 없음.

---

## 9. 보고 전용 `action_token` 11경로 (D-K9-66) — 보고서에 쓰는 정해진 글

- **자리**: 보고서 §0(쉬운 요약) 맨 앞, 보충 32 §2.3의 요약 문장 바로 뒤.
- **판정·STOP 없음, 닫힌 목록 그대로**: 이 경로들은 판정에 쓰지 않고 STOP을 만들지 않습니다(D-K9-62·66). `AD32/vb_closed_leaves.json`(`b800be45…`)은 바꾸지 않습니다.
- **표**: 보고 전용 10결정마다 목록 밖 경로를 보충 32 §2.3 꼴로(경로·종류·까닭·잎 수). 그 아래 r1과의 대조 한 줄: "STOP 판 r1에서 본 11경로와 견주면: 같은 경로 c개, 이번에 새로 보인 경로 d개, 이번에 보이지 않은 경로 e개." r1의 11경로(비교 기준, STOP 판 r1 §3.3 표 그대로):
  1. `/metadata/joint_leader_selection/budget_initialization/reference_action_token`
  2. `/metadata/joint_leader_selection/control_sequence/plan_action_token`
  3. `/metadata/joint_leader_selection/pfo_warm_start/iterations[*]/action_token`
  4. `/metadata/joint_leader_selection/pfo_warm_start/trial_rows[*]/action_token`
  5. `/metadata/joint_leader_selection/surrogate_query/rows[*]/action_token`
  6. `/metadata/joint_leader_selection/surrogate_query/warm_budget_binding/initialization/reference_action_token`
  7. `/metadata/joint_leader_selection/tangent_derivatives[*]/candidate_prediction_reused/requested_action_token`
  8. `/metadata/joint_leader_selection/tangent_derivatives[*]/candidate_prediction_reused/source_action_token`
  9. `/metadata/joint_leader_selection/tangent_derivatives[*]/candidate_prediction_reused/warm_budget_binding/initialization/reference_action_token`
  10. `/metadata/joint_leader_selection/tangent_derivatives[*]/surrogate_prediction/action_token`
  11. `/metadata/joint_leader_selection/trial_rows[*]/action_token`
- **정해진 문장**(이 글 그대로 옮김; 괄호 안 숫자만 데이터로 채움):
  > **보고 전용 OFF 10결정의 닫힌 목록 밖 차이(판정 아님, STOP 아님; D-K9-62·66): 결정 (a)개에서 모두 (b)개.** 그 가운데 `action_token` 꼴 경로는 (c)개입니다. 까닭 [추론, 근거 읽음]: `action_token`은 행동 객체를 피클(pickle, 파이썬 객체를 바이트로 바꾸는 것)한 바이트의 sha256입니다(`evaluation/controllers/area_follower_objective.py:436-441`, `:548`). 행동 객체의 `diagnostics`에는 직전 행동 CSV의 경로와 sha가 들어갑니다(`physical_ramp_branches.py:368`; 닫힌 목록 F2–F7·S4–S9가 가리키는 칸). 사슬을 이어받는 결정에서는 그 경로가 RR이 아니라 V-B 출력 뿌리 아래에 있으므로 이 해시가 달라집니다. 닫힌 목록은 "직전 경로 글자를 담거나 직전 파일 sha와 같은 잎"을 찾아 만든 것이라, 그 값을 다시 해시한 이 잎은 목록을 만드는 방법으로 잡히지 않았습니다. 사슬 첫 결정 4개에서는 직전 행동이 RR 파일 그대로라 이 잎이 다르지 않습니다.
- (b) = 0이어도 첫 문장은 씁니다. `action_token` 꼴이 아닌 목록 밖 경로가 있으면 같은 표에 굵게 적고 "이 경로의 까닭은 이 보고에서 정하지 않음"이라고 씁니다(새 추론을 붙이지 않음).
- 경로 비교는 KC의 일반화 꼴(소문자, `[*]`)로 합니다(보충 32 §2.2 표와 같은 꼴).

---

## 10. STOP 규칙 (보충 24 §8·25 §9·26 §7·27 §11·28 §7·29 §8·30 §7·31 §6·32 §8에 더함)

- 그대로: S-K11(스냅숏 다름·봉인 시드·쓰기 금지 뿌리), S-K12, S-K13(V-A 행동), S-K14(드라이브 8 GB), S-K15(VB_INCOMPLETE·구동기 자기 시험 거짓), S-K50(VerifyVB 다름), S-K51(ZI), S-K52(VB-I7 거짓), S-K54(쓰기·직전 행동 위반), S-K55(OFF 관문).
- **S-K53 넓힘**(고정 위반): 보충 33 고정점·`KB/a33_pins.sha256`(= 기대 바이트)·V0 C2·C5 대조 다름, LOG 고정 항목 전에 ZI·사슬 계산을 함, 고정 뒤 새 훅·고르기·도움 함수·닫힌 목록·구동기·재계산기·자기 시험 출력을 고침, 옛 훅(`4d7e0375…`)이나 옛 VBT·옛 VBR을 이번 실행에 씀.
- **S-K56 (새)**: 보충 33의 합성 확인(`dry_a33.py all`)이나 자기 시험 둘 가운데 하나라도 거짓이면 고정하지 않고 STOP(검토가 도구를 고쳐 다시 돌릴 때도 같음). 이 Declare 판에서는 모두 참이었습니다 [실행].
- **S-K57 (새)**: 보관 자리 바뀜 — V0 C13 거짓, 또는 V10에서 보관 바이트 거짓·옛 VBT 트리 목록 ≠ V0, [검토] 또는 VerifyVB의 보관 대조(§6.5: V0 `archive_tree`·다시 낸 옛 VBT 목록·다시 낸 `OK2/vb` 목록 ≠ 고정점 33의 검토 값). 구동기가 STOP 파일에 `S-K57`을 적습니다(보관과 다른 고정 위반이 함께면 S-K57로 적고 모든 점검을 파일에 남김). OK2 목록(옛 VBR 포함) ≠ V0은 보충 32대로 S-K53으로 적히며, 옛 VBR이 바뀐 경우도 여기에 듭니다(§5).
- **STOP이 아닌 것**: 보고 전용 10결정의 목록 밖 차이(`action_token` 포함, D-K9-62·66), SDMPC 결정의 고르기 상태가 `selected`가 아님(눈에 띄게 보고), VB-M 값, PID 재사용이 일어난 횟수(보고만, §8-5).

---

## 11. 보충 24–32가 바뀌는 곳 (그 밖은 그대로 구속)

| 자리 | 옛 내용 | 이 보충 | 근거 |
|---|---|---|---|
| 보충 32 §3.1·§3.4·§2.5 훅 파일 이름 | `loaded_<pid>.json`, `c_<pid>_<seq>`, `hook_error_<pid>.txt`, `hook_setup_error_<pid>.txt`; 열기 `w` | `<토큰>` 이름, 배타 생성·덧붙이기 전용(§2.1–§2.2) | D-K9-65(+ 공개 P1) |
| 보충 32 §3.1 훅 파일 sha | `4d7e0375…`(AD32) | `691fe810…`(AD33) | D-K9-65 |
| 보충 32 §3.2 [검토] 7·P14 | PID 겹침이면 STOP 쪽 위험 | 겹치지 않음(§2.4), 그래도 겹치면 배타 생성 거절 → STOP 쪽 | D-K9-65 |
| 보충 32 §4.1·§10 고정 | `KB/a32_pins.sha256`(51줄)·`KV/vb_pins.sha256` | `KB/a33_pins.sha256`(63줄, 구동기·재계산기·자기 시험 출력 포함; V-B 단계는 자기 시험을 다시 돌리지 않음) | D-K9-65 "새 고정" |
| 보충 32 §4.2 자리 | VBR `OK2/vb`, VBT `TK/vb_e27ceac8`, KV, 스냅숏 s38–s41, 로그 `vb_` | VBR `OK2/vb2`, VBT `TK/vb2_e27ceac8`, KV2, 스냅숏 s43–s46 `vb2`, 로그 `vb2_`; 옛 자리 보관(§5) | D-K9-65, 메인 세션 처리 |
| 보충 32 §4.2 V0·V10 | C1 24–31, C2 보충 32, C3 204줄, C5 a32·vb 목록 | C1 24–32, C2 보충 33, C3 214줄, C5 a33 목록, C13·보관 목록(§6.2) | 구체화 |
| 보충 32 §5·보충 31 §4.4 보고서 | 정본 + 사본 하나 | r2 새 판, r1 보관 사본 둘(+ 옛 VBR 사본), 새 사본 `OK2/vb2`(§8) | 메인 세션 처리 |
| 보충 32 §2.3 보고서 §0 요약 | 목록 밖 요약 문장 | + `action_token` 정해진 글·r1 대조(§9) | D-K9-66 |
| 보충 32 §4.8 VerifyVB | (그대로) | + 훅 이름 꼴·토큰 짝 확인 넷(§6.5), [검토] + 보관 대조(검토 때 목록 값 둘, 다르면 S-K57) | 구체화, [검토] 보관 틈 막기 |
| 보충 32 §8 STOP | S-K51–S-K55 | S-K53 넓힘, S-K56·S-K57 새(§10) | 이 보충 |

- 바꾸지 않는 것: 비교 규칙(보충 21 §6, 보충 24 §4.2, 보충 27·29), 결과 넷의 뜻, VB-I1 판정 4결정, 보고 10결정과 닫힌 잎 목록, VB-I2–VB-I7의 뜻, VB-M1–M9 정의, ZI 상태·규칙, V-B 사슬·상태·팔(보충 24 §14.1 표), 영수증·직전 행동 규칙, 봉인·블라인드 규칙, 커밋 K9-2-0…5. 코드 변경 0. 푸시 0.

---

## 12. 공개 (V-B 보고서 머리에 옮김)

- **P1 결정 글보다 넓은 이름 고침**: D-K9-65 효과 칸은 "후보 폴더 이름"입니다. 이 보충은 `loaded`·`hook_error`·`hook_setup_error` 이름에도 같은 토큰을 붙이고, 열기 모드를 배타 생성·덧붙이기 전용으로 바꿨습니다. 근거: STOP 보고 r1 §3.4(실제 `loaded` 덮어씀), §6 Q1 (가) 글(사용자가 고른 권장안: "후보 폴더·`loaded` 파일 이름"), 작업 지시의 "배타 생성, 덮어쓰기 없음". 합성 M2·M4는 덮어쓰기가 VB-I7에 보이지 않음을 보였습니다(§4.3). 사용자가 이 범위를 원하지 않으면 V-B 시작 전에 정합니다.
- **P2 구동기·재계산기를 Declare가 씀**: 보충 32에서는 V-B 단계가 구동기·재계산기를 쓰고 자기 시험을 돌렸습니다. 이번에는 바뀌는 곳을 보충 안에서 보이려고 Declare가 사본을 고치고 자기 시험까지 돌려 고정 목록에 넣었습니다. V-B 단계는 자기 시험을 다시 돌리지 않습니다.
- **P3 확인 판 둘**: 첫 확인 판이 모두 참인 뒤 구동기의 STOP 규칙 이름(S-K57)만 고쳐 다시 돌렸습니다(§0.1). 두 판의 도구 sha는 실행 전에 LOG에 있습니다.
- **P4 Declare가 KV·KB에 보관 사본을 씀**: 메인 세션 처리(STOP 판 r1 보관)를 이 단계가 했습니다. 바이트 복사뿐입니다.
- **P5 이 단계가 읽은 기록 자료**: STOP 보고 r1 전문(이미 보고된 값), LOG 끝 부분. 멈춘 실행의 출력 파일 넷(`STOP_vb_V5.json`, `vb_i1.json`, `vb_reportonly.json`, 훅 오류 파일)과 보관 트리는 sha·파일 수·크기만 셌고 내용을 열지 않았습니다. 목적값·예측값 출력 0.
- **P6 합성 강제의 한계**: 실제 PID 재사용은 운영 체제가 정하므로 강제할 수 없습니다. 합성 시험은 `-S` 시작 + `os.getpid` 바꿈 + `site.main()`으로 훅이 같은 PID를 보게 했고, P8로 이 방법이 보통 시작과 같은 결과·기록을 냄을 보였습니다.
- **P7 시계 해상도에 기대지 않음**: 합성 토큰의 `time_ns`는 100 ns 단위로 보였습니다 [실행]. 유일성은 난수 조각이 맡으므로 시계 해상도에 기대지 않습니다(P4).
- **P8 훅이 더 하는 일**: 프로세스마다 시작 때 `os.urandom(8)` 한 번. 결정 계산의 난수 상태를 건드리지 않을 것으로 봅니다 [추론]. ZI·VB-I1이 실제 출력으로 봅니다.
- **P9 VB-I7에 짝 점검을 더하지 않음**: 후보 토큰과 `loaded` 토큰의 짝을 VB-I7 STOP 조건으로 더하는 길이 있지만, D-K9-65의 "이름만 고침" 범위를 지키려고 더하지 않았습니다. 배타 생성으로 덮어쓰기는 일어날 수 없고 [실행 P5], VerifyVB가 짝을 다시 봅니다(§6.5).
- **P10 보충 32 P12·P13(ZI 토큰 가정, VB-41w T=1 선례)**: 멈춘 실행에서는 둘 다 그대로였습니다(ZI 3칸 PASS, VB-41w T=1 PASS). 이번 재실행에서 새로 판가름 나며, 어긋나면 STOP입니다.
- **P11 B1 사슬은 아직 한 번도 돌지 않았습니다.** 이 재실행이 B1의 첫 데이터입니다.
- **P12 스냅숏**: 이 단계 스냅숏 `s42_a33decl`(WMI 분리, 52.7 s)은 s02 대비 SAME입니다.
- **P13 비용 어림이 결정 기록보다 김**: §6.6의 9.5–10 h는 멈춘 실행의 실제 결정 벽시계(623–778 s)로 셈한 것입니다.
- **P14 [검토] `AD33/run_bn.py`의 우선순위 설정 실패**: 이 도우미는 `ctypes.windll.kernel32`의 기본 반환형(int)으로 `GetCurrentProcess()`의 가짜 핸들(−1)을 받아 `SetPriorityClass`에 넘기는데, 이 꼴은 이 기계의 64비트 Python 3.12에서 0(실패)을 돌려주고 마지막 오류는 6(잘못된 핸들)입니다 [실행]. 그래서 Declare의 구동기·재계산기 자기 시험(자식 0, 합성)은 보통 우선순위로 돌았습니다. `dry_a33.py all`은 자기 안에서 핸들 형을 밝혀 BelowNormal을 설정하고 확인했으므로 해당하지 않습니다. 자기 시험 출력은 우선순위와 무관하고(합성 입력, 같은 코드), 바이트는 고정 목록 7–8·10줄 그대로 둡니다. V-B 단계는 이 도우미를 쓰지 않고 `KI/launch.ps1`(WMI PriorityClass 16384)로 발사합니다.
- **P15 [검토] 검토가 돌린 것**: 합성 시험 `KB/a33review/rev_a33.py`를 세 번 돌렸습니다(실행 전마다 도구 sha를 LOG에 적음). 첫째는 검토 도구 결함(R4 비교 열쇠를 파일 이름만으로 삼음)으로 R4가 거짓, 둘째는 R1–R4 참이었지만 검토 도구의 우선순위 함수가 P14와 같은 꼴로 실패(보통 우선순위), 셋째(두 결함만 고친 도구)가 R1–R4 참·BelowNormal 참입니다. 세 출력 모두 남깁니다(§16.5). 보관 목록 도구 `rev_a33_archive.py`는 한 번(첫 시도는 문법 오류로 시작 전에 멈춤, 읽기 0). 모두 합성 입력이거나 이름·크기·수정 시각만 읽음; 결정 재생·어댑터·VISSIM 0, 무거운 일 0(셋 다 3분 안, 앞에서 돌림).
- **P16 [검토] 고르기 자식의 작업 폴더가 옛 `KV`**: 구동기 `select()`는 `vb_select.py`를 작업 폴더 `KV`(보관)에서 띄웁니다(`KV2/vb_chain.py:1033`, 보충 32 구동기와 같은 줄). 작업 폴더일 뿐 쓰기가 아닙니다 — `vb_select.py`는 `python -B`·`sys.dont_write_bytecode`로 돌고 `--dest`(VBR 안)에만 씁니다 [읽음]. V10의 보관 바이트 점검과 VerifyVB 보관 대조가 바뀜을 봅니다. 구동기 바이트는 바꾸지 않았습니다.

---

## 13. 알려진 사실·한계 (V-B 보고서 머리에 옮김)

1. 이 보충은 훅의 이름 규칙과 출력 자리만 바꿉니다. 결정 계산·판정 규칙·지표 정의는 보충 32 그대로입니다.
2. 토큰 겹침 확률은 0이 아니지만(§2.4-2) 겹치면 STOP 쪽입니다. 거짓 PASS 길은 없습니다.
3. ZI는 V-B 밖 두 상태·세 칸에서만 훅 영향 0을 직접 봅니다(보충 32 §11-6 그대로). 새 훅의 추가 호출(`os.urandom`)의 영향 0도 ZI와 VB-I1이 실제 출력으로 봅니다.
4. 보고 전용 10결정·닫힌 목록·`action_token` 11경로의 한계는 보충 32 §11과 §9 그대로입니다.
5. 멈춘 실행의 OFF 14결정 출력(`OK2/vb`)은 보관이고 이번 판정·지표에 쓰지 않습니다. 같은 상태를 새로 계산합니다.
6. 보충 24 §2.6의 한계 1–13, 보충 24 §14.1 "한계", 보충 25 §11, 보충 26 §10, 보충 27 §13, 보충 28 §9, 보충 29 §11, 보충 30 §10, 보충 31 §9, 보충 32 §11은 그대로입니다.
7. [검토] **경로 길이**: 이 기계는 긴 경로 지원이 꺼져 있습니다(`LongPathsEnabled` = 0) [실행]. 새 이름은 트리 이름이 한 글자(`vb`→`vb2`), 훅 후보 폴더 이름이 많아야 37글자(`c_26704_0001` 12글자 → `c_<7자리 PID>_<19자리>_<16자>_0001` 49글자) 깁니다. 옛 VBT의 가장 긴 경로 233글자 → 234, 옛 VBR의 가장 긴 훅 경로 107글자 → 약 145글자로, 260글자 한도 안입니다 [실행 `find` 이름 길이, 계산].
8. [검토] **한 프로세스 안 두 번 실림**(§2.4-7)은 새 훅에서 작업자면 같은 기록의 후보가 둘 생길 뿐 STOP이 아니고, 어댑터면 STOP입니다. 지금 코드에는 생길 길이 보이지 않습니다 [실행 grep 0]. VerifyVB가 보고합니다(§6.5).

---

## 14. 자체 점검

1. **빈 칸 없음**: "나중에 정함"·자리표가 없습니다. 아직 생기지 않은 값은 규칙으로 정했습니다: 보충 33 고정판 sha와 기대 목록 sha의 기록 자리(고정점 33, §7.2), V-B 단계 LOG 항목(§6.1), 새 출력 sha(구동기가 LOG에), VerifyVB 도구 sha(첫 읽기 전 LOG).
2. **D-K9-65**: 정확한 이름 고침(§2.1, 부록 A), 배타 생성 규칙(§2.2), 겹치지 않는 까닭 — 한 프로세스·같은 결정의 프로세스·탄젠트 작업자·결정끼리·그래도 겹치면(§2.4), 고르기 그대로(§2.6), 다른 바뀐 도구와 차이(§3, 부록 B·C), 합성 PID 재사용 자기 시험(§4), 새 고정(§7), 새 출력 뿌리와 새 트리(§5), 처음부터 다시 하는 순서(§6), 보관(§5, §8).
3. **D-K9-66**: 보고만, 닫힌 목록 그대로, 보고서 맨 앞 표와 정해진 원인 추론 글(§9).
4. **STOP 규칙**: 그대로 + S-K53 넓힘 + S-K56·S-K57(§10).
5. **합성 확인만**: 새 도구는 합성 입력에서만 돌렸습니다(§4). 실제 자리에서 읽은 것은 RR 영수증 다섯의 바이트·CSV 크기(구동기 자기 시험 t2, 보충 32와 같은 확인)와 path 문자열 규칙뿐입니다. 새 V-B 데이터 0.
6. 판정 말 없음.
7. [검토] 반박 검토의 확인과 고친 곳은 §16에 있습니다. 검토 뒤에도 빈 칸·나중에 정할 값은 없습니다(검토 때 보관 목록 값 둘은 §5 (라)와 고정점 33에 숫자로 있음).

---

## 15. 파일 (AD33 = `KB/a33decl`, KV2 = `KB/k92_vb2`)

| 파일 | sha256 |
|---|---|
| `AD33/vbhook/sitecustomize.py`(새 훅, 262줄, 12,368 B, LF) | `691fe8100e38d3222f3508f3f682b84b225535d1d3f7cca57f08a671708e365c` |
| `KV2/vb_chain.py`(새 구동기, 2,084줄, 108,273 B) | `87b89ce48b6552b4967cc5416d2e56d5f9f6d20d887d9997385df4f1be521322` |
| `KV2/vb_recalc.py`(새 재계산기, 766줄, 42,514 B) | `6531a5e8eab37201781d4f81c80c7090b1546c2511c128c5db58026f28625d8b` |
| `KV2/selftest/vb_selftest.json` | `a649aaa5094bf0b94aebe5c4eed9418193cfa032b6ec20c97145744ddd6f8922` |
| `KV2/selftest/vb_recalc_selftest.json` | `9e7d864a7eff440c0ad62cecca01d299a0f7ef4135eca647919d14d8d52c6379` |
| `AD33/dry_a33.py` | `d1992a8c244c654b5663f8b14fe8875f9682549a5f7f0b888972b41ed9b027ab` |
| `AD33/run_bn.py` | `c635e1513d71ad071a788d740d7ae637c22f8c73b12cea132cdfca4e6ff153ee` |
| `AD33/make_pins33.sh` | `fa59909897ef1759fdbe3e7cf92da1c088a50e9e8b77a7790b2b9af367e83bd9` |
| `AD33/dry/decl/dry_a33_static.json` | `e7f4e8d3b85442ccbba8071d3cc4153eba978a01885a3200d04d98e83e788bcc` |
| `AD33/dry/decl/dry_a33_hook.json` | `6f711a9bf9a85bd4dd0a3a040e101a9f26c3f3470b0a475ad1b5c7a5e0ae3de2` |
| `AD33/dry/decl/dry_a33_pidreuse.json` | `a81f1675fed2757077e44c013c7110273407b898852e576bd66bdc0c63dab2fc` |
| `AD33/dry/decl/dry_a33_paths.json` | `6749ff778d9ee1f8cfd73baa8bcbc3a5ef672bab324e58ca6fa0334672da9b7b` |
| `AD33/dry/decl/dry_a33_mutants.json` | `48bb9e64d31edf4b10d4b5c04e8fe86b0851c19a028f1a4f62ffa96453d3fd46` |
| `AD33/dry/decl/dry_a33_summary.json`(all_ok 참, BelowNormal 참) | `de72ea283b2529ac5d3eac868ab70fc33a056725e7bd15e48cb0e4343a98af3b` |
| `AD33/diff/hook.diff` / `vb_chain.diff` / `vb_recalc.diff` | `144f90b9346a519697918f426393904e09b1c627cb3fad960adfbf8352789a3e` / `976c31d0a8133ea199fe209ad90b1065aca63393123157026164007be883a3c2` / `b020af092a354bf4dd8ae5c95635928aca177db76253cc6cadf2d9b28cbf09ff` |
| `AD33/a33_pins.expected.sha256`(63줄) | `a1b02027c3238dcb3cb55bae42e163d4d1ce60b0f7c688e44517efcfe9e7ac74` |
| `KV/K92_VB_REPORT_stop_r1.md` / `KB/VB_REPORT_stop_r1.md`(STOP 판 r1 보관 사본) | `d7bf44f3e309aa4ae8e5084b0db238f9baeb2870b6d75b4bea7b6d854427ea00`(둘 같음) |
| `OK2/snap/s42_a33decl.json` | `4e55240d36e460f33f9c13c5cf5164e2a03ed2653ae65675afcac9d6b6410302` |
| `AD33/dry/syn/`(합성 트리 약 1.8 MB), `KV2/selftest/syn/`(약 0.2 MB) — 고정 목록 밖 | — |

- 새 도구·출력·이 글은 줄 끝 LF, CR 0입니다 [실행].
- [검토] 검토의 도구·출력은 §16.5에 있습니다(고정 목록 밖, 판정에 쓰지 않음).

---

## 16. 반박 검토 (ReviewDeclare, 2026-10-22 14:51–15:25 KST) — 고친 곳과 확인

- 검토는 Declare 판(`SP/K8_PREDECLARATION_AMENDMENT_33_r1.md`, `b0db6bf5d49e5b989dd09b629bba016b52e45647a24104cfc4a0a5487dd0bdc9`; 사본 `RV33/r1/K8_PREDECLARATION_AMENDMENT_33_declare.md` 같은 바이트)을 읽고, 작업 지시가 든 여섯 물음을 따졌습니다: (1) 훅 고침이 유일한 동작 바뀜이고 결정 출력·원천 고정을 바꿀 수 없는가, (2) PID 재사용·동시 작업자·다시 시도에서 이름이 겹치지 않는가(적대 합성 사례), (3) 고르기가 여전히 맞는 후보를 고르는가, (4) `OK2/vb2`에 새 V-B 데이터가 없는가, (5) 옛 `OK2/vb`·`TK/vb_e27ceac8`가 그대로인가, (6) 고정·STOP 규칙. RV33 = `KB/a33review`.
- 하지 않은 일: VISSIM·COM·러너·동결·결정 재생·plant 잡·어댑터 실행 0. VBT·VBR 만들기 0, ZI·사슬 계산 0. RR·동결본·GWT8·저장소 `.git`·K8 브랜치·OUTK·봉인 뿌리·옛 VBR·옛 VBT·KV·AD32·AD33·KV2·KI 쓰기 0. 봉인 뿌리·봉인 시드·v3c3-s47·codex 64cf 열람 0. 커밋·브랜치·푸시 0. 금지 시험 0. 끈 프로세스 0.

### 16.1 고친 곳 (모두 글; 도구·확인 출력·기대 고정 목록 바이트 그대로)

| # | 구멍 | 고침 | 자리 |
|---|---|---|---|
| R1 | 확인 도구 `AD33/run_bn.py`의 BelowNormal 설정이 조용히 실패합니다(ctypes 기본 int 반환형이 가짜 핸들을 자름; `SetPriorityClass` 0, 오류 6) [실행]. 그런데 §0.1·§3.3은 자기 시험 둘이 BelowNormal로 돌았다고 적었습니다 | 사실을 바로잡고 공개(P14). 출력은 우선순위와 무관하고 바이트는 고정 목록 그대로. V-B 단계는 이 도우미를 쓰지 않고 `KI/launch.ps1`로 발사(구동기의 `k92lib.set_below_normal()`은 바른 꼴이고 실패하면 멈춤) | 머리 7, §0.1, §3.3, §6.1-5, P14 |
| R2 | 보관 자리를 지키는 대조가 V0–V10뿐이라, 멈춘 실행(옛 VBR 마지막 파일 14:07:20)부터 V0까지 바뀌어도 V0 목록이 그대로 기준이 됩니다(고정 목록의 보관 파일 14개 밖) | 검토 때 목록 값 둘(옛 VBT + 빌드 기록 `d51f4dee…` 10,660행, `OK2/vb` `392d1027…` 1,129파일)을 내어 §5와 고정점에 적고, VerifyVB가 V0 `archive_tree`와 다시 낸 두 목록을 견줌. 다르면 S-K57 | §5 (라), §6.5, §10, §11 |
| R3 | VerifyVB의 "`loaded` 파일 수 = 그 폴더에 기록을 남긴 프로세스 수"는 뜻이 둘로 읽힙니다(모든 프로세스가 `loaded`를 쓰므로 늘 참으로도 읽힘) | 이름·오류 0·짝·순번 넷과 보고 항목으로 정확히 씀. 괄호 안 뜻(같은 토큰 짝)에 PID 일치와 "그 밖의 이름 0"을 더해 STOP을 늘리는 쪽 | §6.5 |
| R4 | 겹침 확률이 "결정당 프로세스 12개" 가정에 기대고, 실제 운영 체제의 PID 재사용 빈도·동시 작업자·한 프로세스 안 두 번 실림·셋 가운데 둘 겹침·결정 단계 다시 시도의 근거가 합성 강제(P1–P8)뿐이었습니다 | 가정 없는 상한(1,000개라도 58번 합쳐 ≤ 1.6 × 10⁻¹²), 검토 시험 R1·R1o(실제 재사용 3·8번)·R2·R3·R4 결과와 다시 시도 경로를 적음 | §2.4-2, §2.4-5–8, §13-8 |
| R5 | §2.2-4가 ZI `hook_on`이 이미 있으면 S-K54라고 적었지만, 코드는 `exist_ok=False` 예외로 멈춥니다(STOP 파일 없음). 칸 폴더는 준비 전에 없어야 하므로(준비 S-K54) 그 자리에 오지 않습니다 | 실제 동작을 적음(멈춘다는 점은 그대로) | §2.2-4 |
| R6 | 이름이 길어지는데 경로 길이 여유를 보지 않았습니다(긴 경로 지원 꺼짐) | 234/260, 약 145/260 [실행·계산] | §13-7 |
| R7 | 고르기 자식의 작업 폴더가 보관 `KV`라는 점이 적혀 있지 않았습니다 | 쓰기가 아님을 근거와 함께 공개(P16) | P16 |

- R1–R7은 판정 정의·문턱·표본·VB-I1 판정 4결정·보고 10결정·닫힌 잎 목록·VB-I1–I7·VB-M1–M9·ZI 규칙(z1)–(z7)·결과 넷의 뜻을 바꾸지 않습니다. R2·R3은 STOP 조건을 늘리는 쪽이고 V-B 데이터 전에 정합니다. 도구(훅 `691fe810…`, 구동기 `87b89ce4…`, 재계산기 `6531a5e8…`, 고르기·도움 함수·닫힌 목록, `dry_a33.py`, `run_bn.py`, `make_pins33.sh`)·확인 출력·기대 고정 목록(`a1b02027c3238dcb3cb55bae42e163d4d1ce60b0f7c688e44517efcfe9e7ac74`, 63줄)은 바꾸지 않았으므로 §7.2의 "다시 돌리고 다시 만듦"은 해당하지 않습니다.

### 16.2 다시 확인했고 문제없는 것

1. **근거 sha** [실행]: 결정 기록 `18724234…`(214줄, LF로 끝남) = 작업 지시 값; 보충 32 고정판 `7f25c21e…` = `.sha256`, 고정점 32 `b59088ab…`; STOP 판 r1 세 곳 `d7bf44f3…`; 옛 훅 `4d7e0375…`; Declare 판 `b0db6bf5…` = 그 `.sha256`.
2. **고정 목록·도구** [실행]: `sha256sum -c AD33/a33_pins.expected.sha256` 63/63 OK, 그 파일 `a1b02027…`. 차이 파일 셋은 지금 파일에서 `diff -u`로 다시 낸 본문과 같음(머리 시각 두 줄 뺌). 훅 차이 지운 줄 12·더한 줄 26(빈 줄 2 포함). 구동기 자기 시험 t1–t7 참, 재계산기 자기 시험 26사례 참, `dry_a33` 다섯 부분 참·망가뜨림 M1–M4 모두 잡음. HOOKDIR·AD32 `vbhook`·AD33·KV2·KI에 `__pycache__` 0.
3. **(1) 결정 출력·원천 고정** [읽음·실행]: 새 훅이 더한 호출은 `K92VB_HOOK_DIR`이 있을 때만 프로세스마다 `os.urandom(8)`·`time.time_ns()` 한 번이고 `random`·numpy 난수 상태를 건드리지 않습니다(새 import 0, static). 모듈 수준 이름 `_proc_token`·`_TOK`가 더해지지만, 어댑터가 `sys.modules`를 훑는 자리(ADP:1280-1291 원천 고정은 `src.*`만; ADP:3034·:3241·:3366·:8966과 `observation_projection.py:252`는 특정 이름의 특정 객체만 바꿈)에 닿지 않습니다. 훅이 쓰는 이름은 훅 폴더 안에만 있고, 어댑터·작업자는 그 폴더를 읽지 않습니다(`K92VB_*`는 훅만 읽음). 원천 고정 `joint_runtime_source_pins`가 따라가는 튜닝 바이트는 그대로입니다(VB-I3 SAF-B1 `65cac7ea…`). `vb`→`vb2`: N이 새 트리 이름도 `<root>`로 바꾸고(dry paths), OK2 출력 경로는 옛 실행처럼 N 밖이며 KC는 경로 잎을 자리(V·R3-05·R3-06 등)로 가르지 글자로 가르지 않습니다(KC:52-125, :186-237). 작업자 띄우기는 `[sys.executable, '-B', …]`·환경 물려받음(`sdmpc_tangent.py:62`, `sdmpc_tangent_concurrent.py:53`), 토큰은 환경에 넣지 않음. 직접 증거는 ZI·VB-I1(V-B 단계)이 냅니다.
4. **(2) 이름 유일성** [실행 검토 R1–R4, Declare P1–P8]: §2.4-2·§2.4-5–8. 실제 PID 재사용에서 새 훅 겹침 0, 옛 훅 겹침 재현; 같은 PID·같은 시각 동시 12개 겹침 0; 셋 가운데 둘의 토큰 전체 겹침은 거절·덮어쓰기 0·STOP 쪽; 한 프로세스 안 두 번 실림은 작업자면 같은 기록 둘(STOP 아님), 어댑터면 STOP 쪽.
5. **(3) 고르기** [읽음·실행]: `vb_select.py`는 앞머리 `glob`과 `cand.json` 안의 `pid`·`seq`만 쓰고 이름을 쪼개지 않음; 재계산기 `reselect`도 같은 두 단계. 검토 R1(맞음 240)·R2(맞음 12)·R4에서 고르기와 재계산기의 상태·고른 폴더가 같음.
6. **(4) 새 V-B 데이터 0** [실행]: `OK2/vb2`·`TK/vb2_e27ceac8`·`KB/a33_pins.sha256`·`OK2/snap/s43–s46_vb2_*`·`OK2/logs/vb2_*` 없음. KV2에는 구동기·재계산기·자기 시험(합성)만.
7. **(5) 보관 그대로** [실행]: 고정 목록 20–33줄 OK, `archive_bytes()` 아홉 점검 참, 옛 VBR 1,129파일·2,665,452,354 B·마지막 수정 14:07:20(STOP 판 r1 사본), 옛 VBT 10,659파일·2,150,845,898 B·마지막 수정 11:28:38. 검토 때 목록 값 둘은 §5 (라).
8. **(6) 고정·STOP** [읽음]: V0 C2(`_r1`이 있으면 고정점에 64자로 없어야 함 — 고정점은 앞 16자만), C3(앞 214줄), C5(줄마다 기대 sha 한 번), C13·V10의 S-K57/S-K53 갈림이 §6.2·§7.3·§10 글과 같음. V0 훅 점검의 "HOOKDIR 파일 하나"가 깨질 길(`__pycache__`): 어댑터 `-B`·작업자 `-B`·구동기 환경 `PYTHONDONTWRITEBYTECODE=1`이라 없음 [읽음 `adapter_launch`, `k92lib.child_env`].
9. **GWT8** [실행 git 읽기]: head `e27ceac8`, 브랜치 `claude/k92-b1-20261016`, K8 `b9734abe`, `status --porcelain` 0줄, `b9734abe..HEAD` 6, 원격 k92 0, 이름에 vb 든 worktree 0. 디스크 C: 40 GB, D: 384 GB.

### 16.3 검토가 읽은 것·돌린 것 (공개 P15)

- 돌림: `RV33/rev_a33.py` 세 번(P15), `RV33/rev_a33_archive.py` 한 번(첫 시도는 문법 오류로 시작 전 멈춤), ctypes 우선순위 진단 한 줄(`python -c`), `sha256sum -c`, `diff -u`, git 읽기, `find`(이름·크기·수정 시각·경로 길이; `OK2/vb`·`TK/vb_e27ceac8`만, 봉인 뿌리 밖), `grep`(GWT8 코드 글자). 모두 3분 안, 앞에서 돌림.
- 읽음: 이 보충 전문, LOG 끝, 결정 기록 :196-214, STOP 판 r1 §3.4·§6, 새·옛 훅 전문, `vb_select.py` 전문, 구동기(도움 함수·발사·계획·`vbi7`·이어 하기·결정·고르기·ZI·V0·V10·`cmd_chain`), 재계산기 `reselect`·`i7_of`, `dry_a33.py`(합성 프로그램·자식 실행·P 사례), 확인 출력 JSON, `make_pins33.sh`, KI `launch.ps1`·`k92lib.py`(`lp`·`set_below_normal`·`child_env`), REC `write()`(:200-240), KC N·허용 규칙, ADP·`observation_projection.py`·`sdmpc_tangent*.py`의 위 줄들, 보충 32 머리·§8·§14, 고정점 32.
- 열람 0: 옛 VBR·옛 VBT 파일 내용(이름·크기·시각·길이만), 봉인 뿌리, 봉인 시드, v3c3-s47, codex 64cf. 목적값·예측값 출력 0.

### 16.4 남은 것 (막힘 아님)

1. P14의 `run_bn.py` 결함은 고정 목록 안의 바이트로 남습니다(V-B에서 쓰지 않음). 고칠지는 다음 묶음에서 사용자가 정합니다.
2. 보충 32 P12·P13(ZI 토큰 가정, VB-41w T=1 선례)은 이번 재실행의 ZI·V5에서 판가름 납니다. 어긋나면 STOP입니다.
3. 남은 미해결: 없음.

### 16.5 검토 도구와 출력 (RV33 = `KB/a33review`; 고정 목록 밖, 판정에 쓰지 않음; sha는 고정점 33에도)

| 파일 | sha256 |
|---|---|
| `rev_a33.py`(셋째 판; 첫째 `da72c750…`, 둘째 `10119951…`) | `a35a286f82560617e692f4b15f307ede4be95eec73faf82817cd41b27a847487` |
| `out/rev_a33.json`(셋째 실행, R1–R4 참, BelowNormal 참) | `9b8694dca6fe08349e91857c0ff56c496a0fae3493b48012a7cecf7560e68f14` |
| `out/rev_a33_run1.json` / `out/rev_a33_run2.json`(첫째·둘째 실행, 남김) | `2ebe01d0fd4da3938e839c5c4dcc47b3943a344b1b9ee37d3e7b80544724a515` / `c1796ee1215a5377e82def50152e4f66204fa66a805737051ae6efe83fe67e09` |
| `rev_a33_archive.py` | `325871a7e2e72846d2bca48a9bf93a26a94fe5bf8e00a470ec116711707a6a0a` |
| `out/rev_a33_archive.json`(검토 때 보관 목록 값) | `b08c3b5ebb1ff6ed4e8fcbdd09b53f12b739d99b002d9a4aa379a405bba83b07` |
| `r1/K8_PREDECLARATION_AMENDMENT_33_declare.md`(Declare 판 사본) | `b0db6bf5d49e5b989dd09b629bba016b52e45647a24104cfc4a0a5487dd0bdc9` |
| `syn/`(합성 트리 약 15 MB) | — |

---

## 부록 A. 훅 차이 (`AD33/diff/hook.diff`, 옛 `4d7e0375…` → 새 `691fe810…`)

```diff
--- a32decl/vbhook/sitecustomize.py	2026-10-22 09:48:50.981555100 +0900
+++ a33decl/vbhook/sitecustomize.py	2026-10-22 14:23:05.142171400 +0900
@@ -1,5 +1,9 @@
 # K9-2 V-B measurement hook (K8_PREDECLARATION_AMENDMENT_32 section 3; user decision D-K9-63).  Diagnostics only,
 # never committed.  READ-ONLY with respect to the program it is loaded into.
+# Amendment 33 (user decision D-K9-65): only the names of the files / folders this hook writes changed.  Every name
+# carries a per-process token <pid>_<time_ns>_<16 hex> drawn once at setup (the OS process id, the wall clock in ns and
+# 8 bytes of os.urandom), so a process id the OS hands out again inside one decision never meets an earlier name; every
+# file / folder is created exclusively (os.mkdir, open mode 'x'; the error files are append-only) and never overwritten.
 # Loaded only through the V-B launcher's extra PYTHONPATH entry (this folder holds this one file); the tangent worker
 # processes inherit PYTHONPATH and the environment.  Inert unless env K92VB_HOOK_DIR is set.
 # Same mechanism as the attribution-study hook (SP/k92/attrib/hook/sitecustomize.py, METHOD.md section 5.1):
@@ -11,7 +15,7 @@
 #     network_facts(cfg); collect(point.control_area_response, T, dt); write(folder, job, T, dt, 3, None)
 # with T = K92VB_T (the decision time), dt = cfg.simulation.T_c_sec, H = 3 blocks (450 s), keyed = None and
 # job = {'label': K92VB_LABEL, 'harness': 'k92vb_hook', 'seed': K92VB_SEED, 'T': T}.  write() puts k92_record.json and
-# k92_series.npz into <K92VB_HOOK_DIR>/c_<pid>_<seq:04d>/; the hook adds cand.json there (the action signature read
+# k92_series.npz into <K92VB_HOOK_DIR>/c_<token>_<seq:04d>/; the hook adds cand.json there (the action signature read
 # from the caller frame's local `action`, flags, timing).  Choosing the candidate of the decision's written action is
 # done afterwards by vb_select.py, outside the program.
 # Reading rules (attribution hook rules): attribute reads, dict/list iteration, isinstance, number extraction only.  A
@@ -19,8 +23,8 @@
 # MRO holds `Dual` of module evaluation.controllers.sdmpc_dual), numpy scalars by float().  No method of a model object
 # is called (dict get/items/keys excepted; the recorder's own reads are the same kind).  No `evaluation` / `src` module
 # is imported.  Nothing reachable from a frame is written.  Every exception inside the hook is caught and written to
-# hook_error_<pid>.txt (setup: hook_setup_error_<pid>.txt); nothing is raised into the original program.  The per-call
-# folder number comes from a counter under a threading.Lock.
+# hook_error_<token>.txt (setup: hook_setup_error_<token>.txt); nothing is raised into the original program.  The
+# per-call folder number comes from a counter under a threading.Lock.
 import os
 import sys
 
@@ -30,7 +34,14 @@
 _SCHEMA = 'k92vb-candidate/v1'
 
 
-def _setup():
+def _proc_token():
+    """'<pid>_<time_ns>_<16 hex>', drawn once per process (amendment 33 section 2.1).  os.urandom reads the OS random
+    source; the random module and numpy random states are not touched."""
+    import time
+    return '%d_%d_%s' % (os.getpid(), time.time_ns(), os.urandom(8).hex())
+
+
+def _setup(tok):
     import hashlib
     import json
     import threading
@@ -58,11 +69,11 @@
         got = hashlib.sha256(src).hexdigest()
     except Exception:  # noqa: BLE001
         loaded['recorder_ok'] = False
-        with open(os.path.join(_OUT, 'loaded_%d.json' % pid), 'w', encoding='utf-8') as h:
+        with open(os.path.join(_OUT, 'loaded_%s.json' % tok), 'x', encoding='utf-8') as h:
             json.dump(loaded, h)
         raise
     loaded.update(T=T, seed=seed, recorder_sha256=got, recorder_ok=(got == rec_want and len(rec_want) == 64))
-    with open(os.path.join(_OUT, 'loaded_%d.json' % pid), 'w', encoding='utf-8') as h:
+    with open(os.path.join(_OUT, 'loaded_%s.json' % tok), 'x', encoding='utf-8') as h:
         json.dump(loaded, h)
     if not loaded['recorder_ok']:
         raise RuntimeError('K92VB: recorder bytes differ from K92VB_RECORDER_SHA256 (%s)' % got)
@@ -83,7 +94,7 @@
     def error(where):
         try:
             with lock:
-                with open(os.path.join(_OUT, 'hook_error_%d.txt' % pid), 'a', encoding='utf-8') as h:
+                with open(os.path.join(_OUT, 'hook_error_%s.txt' % tok), 'a', encoding='utf-8') as h:
                     h.write('%s %s\n%s\n' % (time.strftime('%Y-%m-%dT%H:%M:%S'), where, traceback.format_exc()))
         except Exception:  # noqa: BLE001
             pass
@@ -173,8 +184,8 @@
         with lock:
             state['seq'] += 1
             seq = state['seq']
-        folder = os.path.join(_OUT, 'c_%d_%04d' % (pid, seq))
-        os.makedirs(folder)
+        folder = os.path.join(_OUT, 'c_%s_%04d' % (tok, seq))
+        os.mkdir(folder)
         num = Num()
         L = frame.f_locals
         point, cfg = L.get('point'), L.get('cfg')
@@ -213,7 +224,7 @@
         meta['is_ad'] = bool(num.ad)
         meta['incomplete_types'] = dict(num.bad)
         meta['hook_sec'] = time.perf_counter() - t0
-        with open(os.path.join(folder, 'cand.json'), 'w', encoding='utf-8') as h:
+        with open(os.path.join(folder, 'cand.json'), 'x', encoding='utf-8') as h:
             json.dump(meta, h, separators=(',', ':'), default=str)
 
     def on_start(code, offset):
@@ -236,13 +247,16 @@
 
 
 if _OUT:
+    _TOK = None
     try:
-        _setup()
+        _TOK = _proc_token()
+        _setup(_TOK)
     except Exception:  # noqa: BLE001
         try:
             import traceback as _tb
             os.makedirs(_OUT, exist_ok=True)
-            with open(os.path.join(_OUT, 'hook_setup_error_%d.txt' % os.getpid()), 'w', encoding='utf-8') as _h:
+            _name = 'hook_setup_error_%s.txt' % (_TOK if _TOK else '%d_notoken' % os.getpid())
+            with open(os.path.join(_OUT, _name), 'a', encoding='utf-8') as _h:
                 _h.write(_tb.format_exc())
         except Exception:  # noqa: BLE001
             pass
```

## 부록 B. 구동기 차이 (`AD33/diff/vb_chain.diff`, 옛 `KV/vb_chain.py` `4dc9297d…` → 새 `KV2/vb_chain.py` `87b89ce4…`)

```diff
--- k92_vb/vb_chain.py	2026-10-22 11:17:06.064037100 +0900
+++ k92_vb2/vb_chain.py	2026-10-22 14:36:37.829910500 +0900
@@ -1,14 +1,18 @@
 """K9-2 V-B chain driver (K8_PREDECLARATION_AMENDMENT_32 section 4; amendment 24 section 14.1 as changed by
 amendments 27 section 6.2, 29 section 6.2, 31 section 4.4 and 32).  Scratch tool, never committed.
-
-    python -B vb_chain.py selftest     synthetic self-tests, no child process -> KV/selftest/vb_selftest.json
-    python -B vb_chain.py chain        V0 .. V10 (one detached run: KI/launch.ps1 -Tag vb_chain)
-
-Writes only (guard()): VBR = OK2/vb, TK/vb_e27ceac8 and TK/vb_e27ceac8.build.json (V1 only), KV, KB/LOG.md (append),
-OK2/snap/s38-s41_vb_*.json (snapshot child), OK2/logs/vb_* (launcher).  Read only: RR, FRZ_K8 / FRZ_K8b, GWT8 (git
-read only), AD32, KI.  No VISSIM, no COM, no runner, no commit / push.  The adapter children write their own tangent
-cache under VBT/evaluation/controllers/__tangentcache__ (as every earlier TK-tree replay) and obs150/derived_<T>.json
-in their prepared folder (VBR).
+Amendment 33 (D-K9-65) rerun copy: the same driver with new places (VBR = OK2/vb2, VBT = TK/vb2_e27ceac8, KV2 =
+KB/k92_vb2), the amendment-33 hook (AD33/vbhook), the amendment-33 pins and V0 / V10 checks, and the earlier V-B
+places (OK2/vb, TK/vb_e27ceac8, KV) kept read-only as an archive.  Every rule of amendment 32 section 4 is unchanged.
+
+    python -B vb_chain.py selftest     synthetic self-tests, no child process -> KV2/selftest/vb_selftest.json
+    python -B vb_chain.py chain        V0 .. V10 (one detached run: KI/launch.ps1 -Tag vb2_chain)
+
+Writes only (guard()): VBR = OK2/vb2, TK/vb2_e27ceac8 and TK/vb2_e27ceac8.build.json (V1 only), KV2, KB/LOG.md
+(append), OK2/snap/s43-s46_vb2_*.json (snapshot child), OK2/logs/vb2_* (launcher).  Read only: RR, FRZ_K8 / FRZ_K8b,
+GWT8 (git read only), AD32, AD33, KI and the archive (OK2/vb, TK/vb_e27ceac8 + build record, KV).  No VISSIM, no COM,
+no runner, no commit / push.  The adapter children write their own tangent cache under
+VBT/evaluation/controllers/__tangentcache__ (as every earlier TK-tree replay) and obs150/derived_<T>.json in their
+prepared folder (VBR).
 Launch rule (section 4.3): the argument list / order, the environment and the working folder of k92_replay.py
 (blob 822dd78f, VBT copy) -- differences only: the output paths and, for chained decisions, the previous action.
 Stdout of this driver: stage names, verdict words, counts and sha only (metric values go to VBR/judge files)."""
@@ -30,19 +34,24 @@
           r'491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8')
 KB = SP / 'k92' / 'bundle1'
 KV = KB / 'k92_vb'
+KV2 = KB / 'k92_vb2'
 KI = KB / 'impl'
 AD32 = KB / 'a32decl'
-HOOKDIR = AD32 / 'vbhook'
+AD33 = KB / 'a33decl'
+HOOKDIR = AD33 / 'vbhook'
 sys.path.insert(0, str(KI))
 import k92lib as L  # noqa: E402
 import cglib as G  # noqa: E402
 
 TK = Path(r'D:/VISSIM-merge/k8_gate_trees/k92b1')
-VBT_NAME = 'vb_e27ceac8'
+VBT_NAME = 'vb2_e27ceac8'
 VBT = TK / VBT_NAME
 VBT_BUILD = TK / (VBT_NAME + '.build.json')
 OK2 = Path(r'D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1')
-VBR = OK2 / 'vb'
+VBR = OK2 / 'vb2'
+OLD_VBT = TK / 'vb_e27ceac8'                        # archive (amendment 33 section 5): read only
+OLD_VBT_BUILD = TK / 'vb_e27ceac8.build.json'
+OLD_VBR = OK2 / 'vb'
 RR = Path(r'D:/VISSIM_runs/20261004_sdmpc31_k8')
 FRZ7 = Path(r'D:/VISSIM-merge/frozen')
 FRZ8 = Path(r'D:/VISSIM-merge/frozen/sdmpc31_74cd495f_202610131824')
@@ -76,7 +85,8 @@
          28: '9881eb40c1129af0cdff48026dc8656b4235d43f0eb80566e4be9b66d9ac345e',
          29: '4bd6dc8de8b0a4a4ab0b8703c07d7a73d244c4a622b81585f06dc69d6d83599d',
          30: 'ba556227a6356b1733bfa8125b334cfef180c1eed97e8d69ae4ba53a3106a56a',
-         31: '8541ccb7fa6c951b4affcca67d57e25be09b061c3ae3dd006d050c9c6413e304'}
+         31: '8541ccb7fa6c951b4affcca67d57e25be09b061c3ae3dd006d050c9c6413e304',
+         32: '7f25c21e72fc2599022c72adb1976257413a8486f4898ffcec61f3c6b01423e7'}
 F_SHA = {24: 'fbc3d59fe2e47fec00d87262d624aa9a163ed02e113609b06173841397df101a',
          25: 'd1338fbc40a2efaf6997667f59e7bd709951e1fd3f2b1a8a0a0881794c3d24ed',
          26: '6edc55acd5aa0976701456d956e33f33c52ae0853535f6a4d8cb8bf26a354581',
@@ -84,25 +94,35 @@
          28: '14451cf4d46c5c0095bc896134112148ba5700ee70b2ed78b8ee38d0e62e20e5',
          29: '3ba1d0bdaab8a0189f903d10fc1024baed770080542cbd841f79d3a56df58e43',
          30: 'ad3fafadd59985b3b71f33d5523ceb2324aa8267395d7280039228669cb83e9c',
-         31: '605ccbd2cb392ac2ed0a6da1d27c20e93aa68fcac50ec6d99c4393236f98a053'}
-A32 = SP / 'K8_PREDECLARATION_AMENDMENT_32.md'
-A32_SHA = '7f25c21e72fc2599022c72adb1976257413a8486f4898ffcec61f3c6b01423e7'
-A32_DECLARE_SHA = '176ded8997b53206b320b15efb3c92b79de2b256ee8293acbd41c1dabbd36e52'
-FIXED32 = KB / 'AMENDMENT32_FIXED.md'
-FIXED32_SHA = 'b59088ab44683f5990f2a44038c688aec59a21fcb5207e72b0bc7ee5782ddef4'
+         31: '605ccbd2cb392ac2ed0a6da1d27c20e93aa68fcac50ec6d99c4393236f98a053',
+         32: 'b59088ab44683f5990f2a44038c688aec59a21fcb5207e72b0bc7ee5782ddef4'}
+# amendment 33: its own sha and the expected pin-list sha are not constants here (the pin list holds this file's sha);
+# they are read from the fixation record, whose sha the V-B stage writes into KB/LOG.md before the launch (V0 C2).
+A33 = SP / 'K8_PREDECLARATION_AMENDMENT_33.md'
+A33_SHA_FILE = SP / 'K8_PREDECLARATION_AMENDMENT_33.md.sha256'
+A33_R1 = SP / 'K8_PREDECLARATION_AMENDMENT_33_r1.md'
+FIXED33 = KB / 'AMENDMENT33_FIXED.md'
 NOTES = SP / 'K9_1_J1_NOTES_20261013.md'
-NOTES_204_SHA = '402eaf59aa738bef1dcb27f41d51eba873a8cb6abdbfde7707dfc6b146cfbd3b'
-EXPECTED_PINS = AD32 / 'a32_pins.expected.sha256'
-EXPECTED_PINS_SHA = '9e4dc5925e36fcc092f1b4ace4c3e86600d8f96422f3720653fe7d72d4514fcb'
-A32_PINS = KB / 'a32_pins.sha256'
-VB_PINS = KV / 'vb_pins.sha256'
+NOTES_N = 214
+NOTES_N_SHA = '187242343570f1fe4e22d644509139e87ff59f76c70458b58160c1cde5387109'
+EXPECTED_PINS = AD33 / 'a33_pins.expected.sha256'
+A33_PINS = KB / 'a33_pins.sha256'
 A31_PINS = KB / 'a31_pins.sha256'
+# archive of the stopped amendment-32 V-B run (amendment 33 section 5): must stay byte / listing identical
+OLD_HOOK_SHA = '4d7e0375116c3f805aa223651da0dc1c0c04b7d3315062e98e21137ba60aa321'
+A32_PINS = KB / 'a32_pins.sha256'
+A32_PINS_SHA = '9e4dc5925e36fcc092f1b4ace4c3e86600d8f96422f3720653fe7d72d4514fcb'
+OLD_VB_PINS = KV / 'vb_pins.sha256'
+OLD_VB_PINS_SHA = '6bed354112b93b65d6ffe59bbc8b1472c5e3911683e0d0fcc31964e44514f366'
+STOP_R1_SHA = 'd7bf44f3e309aa4ae8e5084b0db238f9baeb2870b6d75b4bea7b6d854427ea00'
+STOP_R1_COPIES = (KV / 'K92_VB_REPORT_stop_r1.md', KB / 'VB_REPORT_stop_r1.md', OLD_VBR / 'K92_VB_REPORT.md')
+OLD_VBT_BUILD_SHA = '2ace33638b30a4daccb63544d55e668608e2f51e140a6f93706e79c0514bab0e'
 GATES_REC = {KB / 'GATES_K92B1_A31.md': 'e2b301837feb35d652d0db088d634e07449676abd01cb0e8b2dfef6eff232885',
              KB / 'VERIFY_GATES_K92B1_r3.md': '6fb66ac5b8de8bbd00df420bc3b1bf5364e5f95148574dd2834204e3df3ac189',
              KB / 'vgates4' / 'out' / 'vg4_result.json':
                  '0b7654eca9e1165fad42ebe59b28bde91598d0b183f0cf694a21ba09a398b603'}
 GATES_MD_NOW = '449b361e96d047156e63f73bcdae905ec61408b9a5f9be047629092d3ab0a792'
-HOOK_SHA = '4d7e0375116c3f805aa223651da0dc1c0c04b7d3315062e98e21137ba60aa321'
+HOOK_SHA = '691fe8100e38d3222f3508f3f682b84b225535d1d3f7cca57f08a671708e365c'
 SELECT_SHA = '33adfd5033c277a3ad640f745a69efb2a929b27c1ff2a88d794dfa69b489e9cc'
 LIB_SHA = '504999a196a9e08582f303d4ad38d4cc661fcfc765df62d11bc4cc7c05ddc75f'
 CLOSED_SHA = 'b800be45ae3e4e5030ed31ecd221e6288d52c2a287bdeaa5efee243e3cc2f426'
@@ -204,13 +224,16 @@
     return a == b or a.startswith(b + '\\')
 
 
-DENY = (RR, FRZ7, GWT8, REPO, K92ATTRIB, DA, V4, OUTH, OUTK, SEALED, AD32, KI)
+DENY = (RR, FRZ7, GWT8, REPO, K92ATTRIB, DA, V4, OUTH, OUTK, SEALED, AD32, AD33, KI, OLD_VBR, OLD_VBT, OLD_VBT_BUILD,
+        KV)
+SNAP_RE = r's(43|44|45|46)_vb2_[a-z0-9_]+\.json'
+LOG_PREFIX = 'vb2_'
 
 
 def allowed(p, v1=False):
     if any(_inside(p, d) for d in DENY):
         return False
-    if _inside(p, VBR) or _inside(p, KV):
+    if _inside(p, VBR) or _inside(p, KV2):
         return True
     if _inside(p, VBT) or _n(p) == _n(VBT_BUILD):
         return bool(v1)
@@ -218,9 +241,9 @@
         return True
     q = Path(os.path.abspath(str(p)))
     if _n(q.parent) == _n(OK2 / 'snap'):
-        return re.fullmatch(r's(38|39|40|41)_vb_[a-z0-9_]+\.json', q.name) is not None
+        return re.fullmatch(SNAP_RE, q.name) is not None
     if _n(q.parent) == _n(OK2 / 'logs'):
-        return q.name.startswith('vb_')
+        return q.name.startswith(LOG_PREFIX)
     return False
 
 
@@ -646,7 +669,7 @@
             got = sha(p)
         except OSError:
             got = None
-        rows.append({'path': p, 'ok': got == h})
+        rows.append({'path': p, 'ok': got == h, 'sha': h})
     return rows
 
 
@@ -696,18 +719,19 @@
 
 
 def ok2_listing():
-    """OK2 outside VBR (sealed root never entered); the snapshot / log files this stage may add are left out."""
+    """OK2 outside VBR (sealed root never entered); the snapshot / log files this stage may add are left out.  The
+    archive OK2/vb (amendment 33 section 5) is inside this listing, so any change to it shows at V10."""
     rows = []
     root = L.lp(OK2)
     for base, dirs, names in os.walk(root):
         if _n(base) == _n(root):
-            dirs[:] = [x for x in dirs if x not in ('sealed_s47', 'vb')]
+            dirs[:] = [x for x in dirs if x not in ('sealed_s47', VBR.name)]
         dirs.sort()
         rel_base = os.path.relpath(base, root).replace('\\', '/')
         for n in sorted(names):
-            if rel_base == 'snap' and re.fullmatch(r's(38|39|40|41)_vb_[a-z0-9_]+\.json', n):
+            if rel_base == 'snap' and re.fullmatch(SNAP_RE, n):
                 continue
-            if rel_base == 'logs' and n.startswith('vb_'):
+            if rel_base == 'logs' and n.startswith(LOG_PREFIX):
                 continue
             p = os.path.join(base, n)
             st = os.stat(p)
@@ -715,6 +739,38 @@
     return {'files': len(rows), 'sha256': hashlib.sha256(json.dumps(rows).encode()).hexdigest()}
 
 
+def archive_listing():
+    """Names, sizes and mtimes of the archived V-B tree TK/vb_e27ceac8 and its build record (amendment 33 section
+    5); TK is outside the read-only snapshot roots, so V0 / V10 compare this listing."""
+    rows = []
+    root = L.lp(OLD_VBT)
+    for base, dirs, names in os.walk(root):
+        dirs.sort()
+        rel_base = os.path.relpath(base, root).replace('\\', '/')
+        for n in sorted(names):
+            st = os.stat(os.path.join(base, n))
+            rows.append([rel_base + '/' + n, st.st_size, round(st.st_mtime, 6)])
+    st = os.stat(L.lp(OLD_VBT_BUILD))
+    rows.append(['../vb_e27ceac8.build.json', st.st_size, round(st.st_mtime, 6)])
+    return {'files': len(rows), 'sha256': hashlib.sha256(json.dumps(rows).encode()).hexdigest()}
+
+
+def archive_bytes():
+    """Byte checks of the archive (amendment 33 section 5): the stopped run's pin lists, the old hook and the three
+    STOP r1 report copies."""
+    a32 = pins_check(A32_PINS) if A32_PINS.is_file() else []
+    old_vb = pins_check(OLD_VB_PINS) if OLD_VB_PINS.is_file() else []
+    c = {'a32_pins_file': A32_PINS.is_file() and sha(A32_PINS) == A32_PINS_SHA,
+         'a32_pins_51_ok': len(a32) == 51 and all(r['ok'] for r in a32),
+         'old_vb_pins_file': OLD_VB_PINS.is_file() and sha(OLD_VB_PINS) == OLD_VB_PINS_SHA,
+         'old_vb_pins_4_ok': len(old_vb) == 4 and all(r['ok'] for r in old_vb),
+         'old_hook': sha(AD32 / 'vbhook' / 'sitecustomize.py') == OLD_HOOK_SHA,
+         'old_vbt_build': OLD_VBT_BUILD.is_file() and sha(OLD_VBT_BUILD) == OLD_VBT_BUILD_SHA,
+         'old_vbr_dir': OLD_VBR.is_dir(), 'old_vbt_dir': OLD_VBT.is_dir(),
+         'stop_r1_copies': all(p.is_file() and sha(p) == STOP_R1_SHA for p in STOP_R1_COPIES)}
+    return {'ok': all(c.values()), 'checks': c}
+
+
 def phase_mode(path):
     doc = json.loads(Path(path).read_text(encoding='utf-8-sig'))
     sec = doc.get('phase_price') if isinstance(doc.get('phase_price'), dict) else {}
@@ -722,32 +778,46 @@
             'ok': sec.get('mode') != 'observed_backpressure'}
 
 
+HEX64 = r'(?<![0-9a-f])[0-9a-f]{64}(?![0-9a-f])'
+
+
+def pin_line_ok(rows, path, want):
+    """True when the pin list holds `path` (normalised) once, with sha `want`, and the line checks OK."""
+    hits = [r for r in rows if _n(r['path']) == _n(path)]
+    return len(hits) == 1 and hits[0]['ok'] and hits[0]['sha'] == want
+
+
 def v0(resume):
     c = {}
     c['C1'] = {n: {'amend': sha(SP / ('K8_PREDECLARATION_AMENDMENT_%d.md' % n)) == A_SHA[n]
                    and (SP / ('K8_PREDECLARATION_AMENDMENT_%d.md.sha256' % n)).read_text(encoding='utf-8')[:64]
                    == A_SHA[n],
-                   'fixed': sha(KB / ('AMENDMENT%d_FIXED.md' % n)) == F_SHA[n]} for n in range(24, 32)}
+                   'fixed': sha(KB / ('AMENDMENT%d_FIXED.md' % n)) == F_SHA[n]} for n in range(24, 33)}
     c1 = all(v['amend'] and v['fixed'] for v in c['C1'].values())
-    fixed_text = FIXED32.read_text(encoding='utf-8')
-    toks = set(re.findall(r'(?<![0-9a-f])[0-9a-f]{64}(?![0-9a-f])', fixed_text))
-    c['C2'] = {'a32': sha(A32) == A32_SHA,
-               'a32_sha256_file': (SP / 'K8_PREDECLARATION_AMENDMENT_32.md.sha256').read_text(encoding='utf-8')[:64]
-               == A32_SHA,
-               'in_fixed': A32_SHA in toks, 'declare_not_64': A32_DECLARE_SHA not in toks,
-               'fixed_file': sha(FIXED32) == FIXED32_SHA}
-    c['C3'] = {'notes_204': first_lines_sha(NOTES, 204) == NOTES_204_SHA}
-    c['C4'] = git_state()
-    exp = EXPECTED_PINS.read_bytes()
-    a32rows = pins_check(A32_PINS) if A32_PINS.is_file() else []
-    vbrows = pins_check(VB_PINS) if VB_PINS.is_file() else []
     logtext = (KB / 'LOG.md').read_text(encoding='utf-8')
-    c['C5'] = {'a32_pins_bytes': A32_PINS.is_file() and A32_PINS.read_bytes() == exp and sha(EXPECTED_PINS) ==
-               EXPECTED_PINS_SHA, 'a32_pins_ok': len(a32rows) == 51 and all(r['ok'] for r in a32rows),
-               'vb_pins_ok': bool(vbrows) and all(r['ok'] for r in vbrows), 'vb_pins_n': len(vbrows),
-               'vb_pins_sha_in_log': VB_PINS.is_file() and sha(VB_PINS) in logtext,
-               'driver_sha_in_log': sha(__file__) in logtext,
-               'recalc_sha_in_log': (KV / 'vb_recalc.py').is_file() and sha(KV / 'vb_recalc.py') in logtext}
+    fixed_text = FIXED33.read_text(encoding='utf-8') if FIXED33.is_file() else ''
+    toks = set(re.findall(HEX64, fixed_text))
+    a33 = sha(A33) if A33.is_file() else None
+    r1 = sha(A33_R1) if A33_R1.is_file() else None
+    c['C2'] = {'a33_present': a33 is not None,
+               'a33_sha256_file': A33_SHA_FILE.is_file() and A33_SHA_FILE.read_text(encoding='utf-8')[:64] == a33,
+               'a33_in_fixed': a33 in toks, 'declare_not_64': r1 is None or r1 == a33 or r1 not in toks,
+               'fixed_sha_in_log': FIXED33.is_file() and sha(FIXED33) in set(re.findall(HEX64, logtext)),
+               'expected_pins_in_fixed': EXPECTED_PINS.is_file() and sha(EXPECTED_PINS) in toks}
+    c['C3'] = {'notes_first': first_lines_sha(NOTES, NOTES_N) == NOTES_N_SHA}
+    c['C4'] = git_state()
+    exp = EXPECTED_PINS.read_bytes() if EXPECTED_PINS.is_file() else None
+    rows = pins_check(A33_PINS) if A33_PINS.is_file() else []
+    me, rc = sha(__file__), (sha(KV2 / 'vb_recalc.py') if (KV2 / 'vb_recalc.py').is_file() else None)
+    c['C5'] = {'a33_pins_bytes': A33_PINS.is_file() and exp is not None and A33_PINS.read_bytes() == exp,
+               'a33_pins_ok': bool(rows) and all(r['ok'] for r in rows), 'a33_pins_n': len(rows),
+               'driver_line': pin_line_ok(rows, __file__, me), 'recalc_line': pin_line_ok(rows, KV2 / 'vb_recalc.py', rc),
+               'hook_line': pin_line_ok(rows, HOOKDIR / 'sitecustomize.py', HOOK_SHA),
+               'select_line': pin_line_ok(rows, AD32 / 'vb_select.py', SELECT_SHA),
+               'lib_line': pin_line_ok(rows, AD32 / 'vb_lib32.py', LIB_SHA),
+               'closed_line': pin_line_ok(rows, AD32 / 'vb_closed_leaves.json', CLOSED_SHA),
+               'a33_pins_sha_in_log': A33_PINS.is_file() and sha(A33_PINS) in logtext,
+               'driver_sha_in_log': me in logtext, 'recalc_sha_in_log': rc is not None and rc in logtext}
     a31 = pins_check(A31_PINS)
     bad = [i + 1 for i, r in enumerate(a31) if not r['ok']]
     c['C6'] = {'lines': len(a31), 'bad_lines': bad,
@@ -770,12 +840,15 @@
     for rel, want in ((CFG_REL, CFG_SHA), (SAFK91_REL, SAFK91_SHA), (CFGB1_REL, CFGB1_SHA)):
         c12[rel] = dict(phase_mode(GWT8 / rel), sha_ok=sha(GWT8 / rel) == want)
     c['C12'] = c12
-    c['ok_by'] = {'C1': c1, 'C2': all(c['C2'].values()), 'C3': c['C3']['notes_204'], 'C4': c['C4']['ok'],
-                  'C5': all(v for k, v in c['C5'].items() if k != 'vb_pins_n'), 'C6': c['C6']['ok'],
+    c['C13'] = archive_bytes()
+    c['ok_by'] = {'C1': c1, 'C2': all(c['C2'].values()), 'C3': c['C3']['notes_first'], 'C4': c['C4']['ok'],
+                  'C5': all(v for k, v in c['C5'].items() if k != 'a33_pins_n'), 'C6': c['C6']['ok'],
                   'C7': all(c['C7'].values()), 'C8': c8, 'C10': c['C10']['vissim_any'] == 0 and c['C10']['foreign'] == 0,
-                  'C11': c['C11']['ok'], 'C12': all(v['ok'] and v['sha_ok'] for v in c12.values())}
+                  'C11': c['C11']['ok'], 'C12': all(v['ok'] and v['sha_ok'] for v in c12.values()),
+                  'C13': c['C13']['ok']}
     c['ok'] = all(c['ok_by'].values())
     c['ok2_outside_vb'] = ok2_listing()
+    c['archive_tree'] = archive_listing()
     return c
 
 
@@ -834,9 +907,9 @@
         wjson(VBR / 'stages' / 'V1_failed.json', doc)
         stop('V1', 'S-K15', 'V-B tree checks false', {'sha_ok': shas, 'cr_form': forms})
     stage_pass('V1', doc)
-    logmd('V1 트리 `TK/vb_e27ceac8` (git archive e27ceac8 + CR 고침, 형태 %s, cr_pair 둘 참, RS·SHO·튜닝·REC·KC·'
+    logmd('V1 트리 `TK/%s` (git archive e27ceac8 + CR 고침, 형태 %s, cr_pair 둘 참, RS·SHO·튜닝·REC·KC·'
           'k92_replay sha 기대값), 빌드 기록 sha256 `%s`; GWT8 작업 트리 대비 바이트 다름 %d·VBT만 %d·GWT8만 %d(보고만)'
-          % (forms, doc['build_sha256'], len(d['changed']), len(d['only_a']), len(d['only_b'])))
+          % (VBT_NAME, forms, doc['build_sha256'], len(d['changed']), len(d['only_a']), len(d['only_b'])))
     return doc
 
 
@@ -1472,8 +1545,8 @@
         stop('V9', 'S-K54', 'recalc output exists')
     mkdir(dest.parent)
     pre = L.vissim_count()
-    rc, sec = child([PY, '-B', KV / 'vb_recalc.py', 'run', '--vbr', VBR, '--dest', dest], VBR / 'logs' / 'v9_recalc.txt',
-                    KV, clean_env())
+    rc, sec = child([PY, '-B', KV2 / 'vb_recalc.py', 'run', '--vbr', VBR, '--dest', dest], VBR / 'logs' / 'v9_recalc.txt',
+                    KV2, clean_env())
     step_line('V9_recalc', rc, sec, pre, L.vissim_count())
     r = read_json(dest) or {}
     if rc != 0 or r.get('equal') is not True:
@@ -1488,23 +1561,29 @@
     rec = stage_rec('V10')
     if rec:
         return rec
-    a32 = pins_check(A32_PINS)
-    vbp = pins_check(VB_PINS)
+    a33 = pins_check(A33_PINS)
     gs = git_state()
     rr = rr_listing()
     ok2 = ok2_listing()
-    doc = {'a32_pins_ok': len(a32) == 51 and all(x['ok'] for x in a32) and A32_PINS.read_bytes() ==
-           EXPECTED_PINS.read_bytes(), 'vb_pins_ok': bool(vbp) and all(x['ok'] for x in vbp), 'git': gs,
+    arch = archive_listing()
+    arch_b = archive_bytes()
+    doc = {'a33_pins_ok': bool(a33) and all(x['ok'] for x in a33) and A33_PINS.read_bytes() ==
+           EXPECTED_PINS.read_bytes(), 'git': gs,
            'rr_same': rr == v0doc['C9'], 'ok2_outside_vb_same': ok2 == v0doc['ok2_outside_vb'],
-           'rr': rr, 'ok2_outside_vb': ok2, 'vissim': L.vissim_count(), 'free_gb': L.free_space_gb()}
-    doc['ok'] = doc['a32_pins_ok'] and doc['vb_pins_ok'] and gs['ok'] and doc['rr_same'] and doc['ok2_outside_vb_same']
+           'archive_tree_same': arch == v0doc['archive_tree'], 'archive_bytes_ok': arch_b['ok'],
+           'rr': rr, 'ok2_outside_vb': ok2, 'archive_tree': arch, 'archive_bytes': arch_b,
+           'vissim': L.vissim_count(), 'free_gb': L.free_space_gb()}
+    doc['ok'] = doc['a33_pins_ok'] and gs['ok'] and doc['rr_same'] and doc['ok2_outside_vb_same'] and \
+        doc['archive_tree_same'] and doc['archive_bytes_ok']
     if not doc['ok']:
         wjson(VBR / 'stages' / 'V10_failed.json', doc)
-        stop('V10', 'S-K53', 'end comparison false', {k: doc[k] for k in ('a32_pins_ok', 'vb_pins_ok', 'rr_same',
-                                                                       'ok2_outside_vb_same')})
+        rule = 'S-K57' if not (doc['archive_tree_same'] and doc['archive_bytes_ok']) else 'S-K53'
+        stop('V10', rule, 'end comparison false', {k: doc[k] for k in ('a33_pins_ok', 'rr_same', 'ok2_outside_vb_same',
+                                                                    'archive_tree_same', 'archive_bytes_ok')})
     stage_pass('V10', doc)
-    logmd('V10 끝 대조 OK: a32 고정 51/51·V-B 고정 목록 OK, GWT8 head `e27ceac8`·status 0·K8 `b9734abe`·원격 k92 0, '
-          'RR 목록 sha = V0, OK2 의 vb 밖 = 스냅숏·로그뿐')
+    logmd('V10 끝 대조 OK: a33 고정 %d/%d, GWT8 head `e27ceac8`·status 0·K8 `b9734abe`·원격 k92 0, '
+          'RR 목록 sha = V0, OK2 의 vb2 밖(보관 OK2/vb 포함) = V0, 보관 TK/vb_e27ceac8 목록 = V0, 보관 바이트 참'
+          % (len(a33), len(a33)))
     return doc
 
 
@@ -1521,7 +1600,7 @@
                 wjson(VBR / 'check_v0.json', v0doc)
             except Exception:  # noqa: BLE001
                 pass
-        stop('V0', 'S-K53', 'precheck false', v0doc['ok_by'])
+        stop('V0', 'S-K57' if not v0doc['ok_by'].get('C13', True) else 'S-K53', 'precheck false', v0doc['ok_by'])
     mkdir(VBR)
     name = 'check_v0.json' if not resume else 'check_v0_resume_%s.json' % time.strftime('%Y%m%d_%H%M%S')
     h0 = wjson(VBR / name, v0doc)
@@ -1531,30 +1610,31 @@
     else:
         stage_pass('V0', dict(v0doc, check_file=name, check_sha256=h0))
         v0first = read_json(VBR / 'stages' / 'V0.json')
-    logmd('V0 사전 점검 %s 참(C1–C12), `%s` sha256 `%s`, 구동기 `%s`, 재계산기 `%s`' % (
-        'resume' if resume else 'first', name, h0, sha(__file__), sha(KV / 'vb_recalc.py')))
+    logmd('V0 사전 점검 %s 참(C1–C13), `%s` sha256 `%s`, 구동기 `%s`, 재계산기 `%s`' % (
+        'resume' if resume else 'first', name, h0, sha(__file__), sha(KV2 / 'vb_recalc.py')))
     CTX.lib = load_pinned(AD32 / 'vb_lib32.py', LIB_SHA, 'vb_lib32')
     CTX.sel = load_pinned(AD32 / 'vb_select.py', SELECT_SHA, 'vb_select')
-    if sha(AD32 / 'vb_closed_leaves.json') != CLOSED_SHA or sha(HOOKDIR / 'sitecustomize.py') != HOOK_SHA:
+    if sha(AD32 / 'vb_closed_leaves.json') != CLOSED_SHA or sha(HOOKDIR / 'sitecustomize.py') != HOOK_SHA \
+            or HOOK_SHA == OLD_HOOK_SHA or sorted(p.name for p in HOOKDIR.iterdir()) != ['sitecustomize.py']:
         stop('V0', 'S-K53', 'closed list / hook bytes differ')
     CTX.closed = CTX.lib.load_closed(AD32 / 'vb_closed_leaves.json')
     if sha(K92_VALUES) != K92_VALUES_SHA:
         stop('V0', 'S-K53', 'K92_VALUES.json differs')
     CTX.floor_keys = json.loads(K92_VALUES.read_text(encoding='utf-8'))['p0_2']['f_expected_floor_keys']
     CTX.base = base_env()
-    snapshot('s38_vb_v0')
+    snapshot('s43_vb2_v0')
     v1()
     CTX.kc = load_pinned(VBT / SA_REL / 'k92_compare.py', KC_SHA, 'k92_compare_vb')
     CTX.a27 = load_pinned(VBT / SA_REL / 'k92_a27.py', A27M_SHA, 'k92_a27_vb')
     v2()
     v3()
-    snapshot('s39_vb_zi')
+    snapshot('s44_vb2_zi')
     if not stage_rec('V4'):
         run_chain('off')
         stage_pass('V4', {'n': 14})
         logmd('V4 OFF 사슬 14결정 끝(종료 0)')
     v5()
-    snapshot('s40_vb_off')
+    snapshot('s45_vb2_off')
     if not stage_rec('V6'):
         run_chain('b1')
         stage_pass('V6', {'n': 41})
@@ -1562,7 +1642,7 @@
     v7()
     v8()
     v9()
-    snapshot('s41_vb_end')
+    snapshot('s46_vb2_end')
     v10(v0first)
     CTX.log('CHAIN END all stages PASS')
     print('VB_CHAIN_DONE', flush=True)
@@ -1570,7 +1650,7 @@
 
 
 # ================================================================================================ self-tests (4.5)
-ST = KV / 'selftest'
+ST = KV2 / 'selftest'
 SYN = ST / 'syn'
 
 
@@ -1742,17 +1822,24 @@
 
 def st_guard():
     ok_paths = [(VBR / 'chain' / 'x.json', False), (VBT / 'evaluation' / 'x.py', True), (VBT_BUILD, True),
-                (KV / 'selftest' / 'x.json', False), (KB / 'LOG.md', False), (OK2 / 'snap' / 's38_vb_v0.json', False),
-                (OK2 / 'snap' / 's41_vb_end.json', False), (OK2 / 'logs' / 'vb_chain.txt', False)]
+                (KV2 / 'selftest' / 'x.json', False), (KB / 'LOG.md', False), (OK2 / 'snap' / 's43_vb2_v0.json', False),
+                (OK2 / 'snap' / 's46_vb2_end.json', False), (OK2 / 'logs' / 'vb2_chain.txt', False)]
     bad_paths = [(VBT / 'evaluation' / 'x.py', False), (VBT_BUILD, False),
                  (RR / 'sdmpc31_v3c3_k8j1_s41' / 'x.json', True), (FRZ8 / 'x.py', True), (FRZ8B / 'x.py', True),
                  (Path(r'D:/VISSIM-merge/frozen/sdmpc31_6c4c7400_202610011831/x'), True), (GWT8 / 'x.py', True),
                  (GWT8 / '.git', True), (REPO / '.git' / 'worktrees' / 'x', True), (K92ATTRIB / 'x', True),
                  (DA / 'x', True), (V4 / 'x', True), (OUTH / 'x', True), (OUTK / 'x', True), (SEALED / 'x', True),
                  (OK2 / 'commit' / 'x', True), (OK2 / 'snap' / 's02_after_probe_stop.json', True),
-                 (OK2 / 'snap' / 's42_vb_x.json', True), (OK2 / 'logs' / 'other.txt', True), (OK2 / 'x.json', True),
+                 (OK2 / 'snap' / 's42_vb2_x.json', True), (OK2 / 'logs' / 'other.txt', True), (OK2 / 'x.json', True),
                  (KB / 'other.md', True), (AD32 / 'vb_lib32.py', True), (HOOKDIR / 'x.py', True), (KI / 'x.py', True),
-                 (TK / 'other' / 'x', True), (TK / 'vb_e27ceac8_interrupted_1' / 'x', True), (SP / 'x.md', True)]
+                 (TK / 'other' / 'x', True), (TK / 'vb2_e27ceac8_interrupted_1' / 'x', True), (SP / 'x.md', True),
+                 # amendment 33 archive (section 5) and the earlier V-B names
+                 (OLD_VBR / 'chain' / 'x.json', True), (OLD_VBR / 'K92_VB_REPORT.md', True), (OLD_VBT / 'x.py', True),
+                 (OLD_VBT_BUILD, True), (KV / 'vb_chain.py', True), (KV / 'K92_VB_REPORT.md', True),
+                 (KV / 'selftest' / 'x.json', True), (AD33 / 'vbhook' / 'sitecustomize.py', True),
+                 (AD33 / 'a33_pins.expected.sha256', True), (OK2 / 'snap' / 's38_vb_v0.json', True),
+                 (OK2 / 'snap' / 's41_vb_end.json', True), (OK2 / 'logs' / 'vb_chain.txt', True),
+                 (KB / 'VB_REPORT.md', True), (KB / 'a33_pins.sha256', True)]
     a = [allowed(p, v) for p, v in ok_paths]
     b = [not allowed(p, v) for p, v in bad_paths]
     raised = False
@@ -1857,6 +1944,18 @@
     r['i7_status_hook_error'] = hook(S / 'h6', status='hook_error') is False
     r['i7_no_select'] = hook(S / 'h7', status=None) is False
     r['i7_no_candidate_ok'] = hook(S / 'h8', cands=0, status='no_candidate') is True
+    # amendment 33 names: <prefix>_<pid>_<time_ns>_<16 hex>; two worker processes that got the same pid 4242
+    h9, rc9 = S / 'h9' / 'hook', S / 'h9' / 'rec'
+    _w(h9 / 'loaded_100_1761111111111111111_00112233aabbccdd.json', {'argv0': ADAPTER, 'recorder_ok': True})
+    for tok in ('4242_1761111111222222222_0123456789abcdef', '4242_1761111111333333333_fedcba9876543210'):
+        _w(h9 / ('loaded_%s.json' % tok), {'argv0': 'sdmpc_tangent_worker.py', 'recorder_ok': True})
+        _w(h9 / ('c_%s_0001' % tok) / 'cand.json', {})
+        _w(h9 / ('c_%s_0001' % tok) / 'k92_record.json', {})
+    _w(rc9 / 'k92_select.json', {'status': 'selected'})
+    v9 = vbi7(h9, rc9)
+    r['i7_pid_reuse_names'] = v9['ok'] is True and v9['n_loaded'] == 3 and v9['n_candidates'] == 2
+    _w(h9 / 'hook_error_4242_1761111111333333333_fedcba9876543210.txt', 'x')
+    r['i7_pid_reuse_error_seen'] = vbi7(h9, rc9)['ok'] is False
     return {'ok': all(r.values()), 'cases': r}
 
 
@@ -1903,14 +2002,20 @@
 
 
 def st_ad32():
+    """Amendment 33: select / lib / closed list = the amendment-32 pinned bytes (KB/a32_pins.sha256 lines 2, 3, 5);
+    the hook = the amendment-33 hook (not the amendment-32 one, line 1); the pin-list lines of the amendment-33 list
+    are checked at V0 C5 (the list holds this driver's sha, so it exists only after this self-test)."""
     pins = {}
-    for line in A32_PINS.read_text(encoding='utf-8').splitlines()[:3]:
+    for line in A32_PINS.read_text(encoding='utf-8').splitlines()[:5]:
         h, p = line.split(' *', 1)
         pins[Path(p).name] = h
     lib = load_pinned(AD32 / 'vb_lib32.py', LIB_SHA, 'vb_lib32_st')
     sel = load_pinned(AD32 / 'vb_select.py', SELECT_SHA, 'vb_select_st')
-    r = {'pins_lines_1_3': pins == {'sitecustomize.py': HOOK_SHA, 'vb_select.py': SELECT_SHA,
-                                    'vb_lib32.py': LIB_SHA},
+    r = {'a32_pins_lines_2_3_5': (pins.get('vb_select.py'), pins.get('vb_lib32.py'),
+                                  pins.get('vb_closed_leaves.json')) == (SELECT_SHA, LIB_SHA, CLOSED_SHA),
+         'a32_pins_line_1_is_old_hook': pins.get('sitecustomize.py') == OLD_HOOK_SHA != HOOK_SHA,
+         'hookdir_is_ad33': _n(HOOKDIR) == _n(AD33 / 'vbhook')
+         and sorted(p.name for p in HOOKDIR.iterdir()) == ['sitecustomize.py'],
          'lib_loaded_from_ad32': Path(lib.__file__).resolve() == (AD32 / 'vb_lib32.py').resolve(),
          'select_loaded_from_ad32': Path(sel.__file__).resolve() == (AD32 / 'vb_select.py').resolve(),
          'lib_sha': lib.__pinned_sha256__ == LIB_SHA, 'select_sha': sel.__pinned_sha256__ == SELECT_SHA,
```

## 부록 C. 재계산기 차이 (`AD33/diff/vb_recalc.diff`, 옛 `KV/vb_recalc.py` `cab7939d…` → 새 `KV2/vb_recalc.py` `6531a5e8…`)

```diff
--- k92_vb/vb_recalc.py	2026-10-22 11:21:33.522671100 +0900
+++ k92_vb2/vb_recalc.py	2026-10-22 14:26:54.769010700 +0900
@@ -1,9 +1,10 @@
 """K9-2 V-B independent recalculation, VB-I5 (K8_PREDECLARATION_AMENDMENT_32 section 4.6; amendment 24 section 14.1).
-Scratch tool, never committed.  Imports the standard library and numpy only: never the V-B driver, the AD32 tools
+Scratch tool, never committed.  Amendment 33 rerun copy: the V-B tree is TK/vb2_e27ceac8 (the only change besides this
+note and one self-test case for the amendment-33 hook names <prefix>_<pid>_<time_ns>_<16 hex>).  Imports the standard library and numpy only: never the V-B driver, the AD32 tools
 (vb_lib32, vb_select, the hook), KI, the harness (sa_*, k92_*) or any VBT / GWT8 module.  The rules are written again
 here from the text of amendments 24 section 14.1 and 32 sections 2.4, 2.5, 3.4, 3.6; the closed leaf list is not used.
 
-    python -B vb_recalc.py run --vbr <OK2/vb> --dest <file>     recompute and compare with the driver's judge files
+    python -B vb_recalc.py run --vbr <OK2/vb2> --dest <file>    recompute and compare with the driver's judge files
     python -B vb_recalc.py selftest                             synthetic self-test, no child process
 
 What is recomputed from the raw files (decision JSON / CSV, run records, hook folders, record folders, arm files,
@@ -24,7 +25,7 @@
 
 sys.dont_write_bytecode = True
 RR = Path(r'D:/VISSIM_runs/20261004_sdmpc31_k8')
-TK_VBT = Path(r'D:/VISSIM-merge/k8_gate_trees/k92b1/vb_e27ceac8')
+TK_VBT = Path(r'D:/VISSIM-merge/k8_gate_trees/k92b1/vb2_e27ceac8')
 KB = Path(r'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/'
           r'491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/k92/bundle1')
 VALUES = KB / 'k92_probe_a25' / 'K92_VALUES.json'
@@ -714,6 +715,26 @@
                                                              t1doc))['ok'] is True
     checks['i2_warm_exception_false'] = i2_of(t150, [], 150, 0, 0, ('head_discharge_floor_173_p4_301ceabb95f116fa',
                                                                    act(1, 30.0)))['ok'] is False
+    # amendment 33 hook names: two worker processes with the same pid 4242 (one decision), both candidates match with
+    # the same record -> selected, the earlier time_ns first; VB-I7 true; an error file of one of them -> hook_error
+    hp = root / 'pidreuse' / 'hook'
+    put(hp / 'loaded_100_1761111111111111111_00112233aabbccdd.json', {'argv0': ADAPTER_NAME, 'recorder_ok': True})
+    toks = ('4242_1761111111333333333_fedcba9876543210', '4242_1761111111222222222_0123456789abcdef')
+    for i, tok in enumerate(toks):
+        put(hp / ('loaded_%s.json' % tok), {'argv0': 'sdmpc_tangent_worker.py', 'recorder_ok': True})
+        c = hp / ('c_%s_0001' % tok)
+        put(c / 'cand.json', {'seq': 1, 'pid': 4242, 'is_ad': False, 'time_ns': 2000 - i, 'first_row_start_sec': 3000.0,
+                              'dt_sec': 150.0, 'n_residence_rows': 9, 'n_states': 3, 'signature': {
+                                  'green_times': {'SC109_p2': 20.0, 'SC109_p3': 25.0, 'SC109_p4': 15.0},
+                                  'offsets': {'SC109': 0.0}, 'future_green_times': [{'SC109_p3': 26.0}]}})
+        put(c / 'k92_record.json', {'blocks': [{'chain_sum': 1.0}], 'horizon': {'m1_chain_T450': 12.0}})
+    put(root / 'pidreuse' / 'rec' / 'k92_select.json', {'status': 'selected'})
+    sp = reselect(hp, act(3000, 25.0), 3000)
+    checks['pid_reuse_selected'] = (sp['status'], sp['n_candidates'], sp['n_match'], sp['chosen']) == (
+        'selected', 2, 2, 'c_4242_1761111111222222222_0123456789abcdef_0001')
+    checks['pid_reuse_i7'] = i7_of(hp, root / 'pidreuse' / 'rec')['ok'] is True
+    put(hp / ('hook_error_%s.txt' % toks[0]), b'x')
+    checks['pid_reuse_error_seen'] = reselect(hp, act(3000, 25.0), 3000)['status'] == 'hook_error' and         i7_of(hp, root / 'pidreuse' / 'rec')['ok'] is False
     checks['no_import_of_driver'] = not any(m in sys.modules for m in ('vb_chain', 'vb_lib32', 'vb_select', 'k92lib',
                                                                       'cglib', 'k92_compare', 'k92_record'))
     ok = all(v is True for v in checks.values())
```
