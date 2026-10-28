# 승격 독립 검증 (VerifyPromote r1) — K9-2-6, K9-2-7

- 작성: 2026-10-23 08:13–08:2x KST. Promote 단계 보고(`VA/PROMOTE.md`)를 믿지 않고, git과 파일 바이트에서 따로 다시 냈습니다.
- **검증 head = `c20aff1d7bf0c432cb4f20e2922bd406d857aa5d`(K9-2-7)**. 이것이 푸시할 head입니다(보충 34 §3.3 `:168`, §4.1 `:176`).
- 이 파일과 `VA/VERIFY_PROMOTE_VA.md`는 바이트가 같습니다. 보충 34 §3.3(`:161`)이 정한 이름은 `VERIFY_PROMOTE_VA.md`이고, 작업 지시가 정한 이름은 `VERIFY_PROMOTE_r1.md`라서 둘 다 둡니다.
- 표시: [실행] 이번에 직접 돌려 확인 · [읽음] 문서·코드에서 확인 · [추론] 시험하지 않은 판단.

## 줄임말 (처음 한 번만 풉니다)

- SP = `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8`. VA = `SP/k92/va`. PR = `VA/promote`(Promote 단계 출력). VP = `VA/vpromote`(이 검증의 도구와 출력). REPVA = `D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_va`(보고 사본 자리).
- GWT8 = 작업 트리 `D:/VISSIM-merge/sim3-n31-k8`, 브랜치 `claude/k92-b1-20261016`. K8 가지 = `claude/k8-sc1001eb-defects-20261004`(`b9734abe…`).
- K9-2-5 = `e27ceac8…`(승격 전 head). K9-2-6 = `11d99c2a4790f2bed1a610054e322ffff0253bc1`(승격 커밋). K9-2-7 = `c20aff1d…`(목록 보충 커밋).
- CFG = 배포 튜닝 `diagnostics/sdmpc_n31_20260924/config_n31_v2.json`. 팔 파일(CFG-B1) = `diagnostics/sdmpc_n31_20260924/config_n31_v2_k92b1.json`(묶음 1 팔, K9-2-3에서 만듦).
- GB7 = GB-7′ 허용 차이 경로 목록 `diagnostics/sdmpc_n31_20260924/k8_gates/gb7_allowed.py`. GB-7′ = 무제어 결정 재생 대조 관문. R2-12 = 이번에 더한 목록 항목 하나.
- W = SC109 서측 직진 용량 키 `/urban/sc109w_through_saturation`. H-b = (173, p4) 좌회전 헤드 하한 씨앗 키 `/urban/capacity/head_floor_seed`.
- E_K92 = 보충 34 §5.2가 GB-7′ 판정에 더한 K9-2 선언 차이 네 경로.
- blob = git 객체 해시. `core.autocrlf=true`이라 작업 파일은 `git hash-object --no-filters`로 셉니다.

---

## 0. 결론

**Promote 단계에서 결함을 찾지 못했습니다. pass = true 입니다.**

| 점검 (보충 34 §3.3 `:162-167`, 작업 지시) | 결과 | 근거 |
|---|---|---|
| ① 커밋 8개 순서·작성자·커미터·첫 줄·끝 줄 | 참 | §3 |
| ② diff 범위 = {M CFG, M GB7}, 런타임 폴더 차이 0, K8 가지 그대로 | 참 | §4 |
| ③ CFG blob = 팔 파일 blob `b6ccd50d…`, 팔 − 이전 바탕 = 정확히 W·H-b 두 경로, 증거 sha, 유지 정책 키 | 참 | §5 |
| ④ GB7 = R2-12 하나(+ 선언된 docstring 한 줄), 목록 sha `a8148f38…7af1`, 판정 표 6행, 바이트 범위, E_K92 네 경로 A 밖 | 참 | §6 |
| ⑤ 작업 트리 HEAD = K9-2-7, status 0줄, 두 경로 작업 바이트 = ls-tree blob | 참 | §7 |
| 푸시 없음, K8 가지 `b9734abe` (로컬·추적·원격) | 참 | §7 |
| 남은 파일 없음, 명시 경로(커밋마다 경로 하나) | 참 | §7, §8 |

- **공개 (판정에 영향 없음)**: 내 점검 도구 `VP/v_promote.py`는 exit 1, CORE 36/37, EXTRA 8/8로 끝났습니다 [실행]. 거짓 1개는 `5.no_stray_files_since_0759`입니다. 이것은 보충 34 §3.3 ①–⑤ 밖에 내가 더한 점검입니다. 기대를 "07:59 뒤 바뀐 파일 = {CFG, GB7}"로 잘못 잡았습니다. 실제는 {GB7}뿐입니다. CFG의 수정 시각은 바이트 복사 때 원본(팔 파일)의 시각 `2026-10-20 06:48:04.362`을 그대로 받았기 때문입니다 [실행 `VP/supp_file_times.txt`; 추론: `[System.IO.File]::Copy`는 원본 수정 시각을 옮김]. 남은 파일이 없다는 점검의 뜻은 참입니다(§8). 도구는 고치지 않았습니다. 자세한 설명은 §8.

## 1. 시작 점검 [실행 08:13]

- 재개 점검: LOG에 VerifyPromote 줄 없음, `VP` 없음, `VERIFY_PROMOTE_VA.md`·`VERIFY_PROMOTE_r1.md` 없음 → 처음부터.
- 고정점 `VA/AMENDMENT34_FIXED.md` sha256 `fef58eca53240e6026a78e19729a699be5fa7e965a2d1648f185e551afc3c167`. 보충 34 `SP/K8_PREDECLARATION_AMENDMENT_34.md` = `a05592d48512a515fc254d70b8173360d448b0aa17afb3f63c98b52ef713205e` (= 고정점 `:7`, = `.sha256`).
- 고정 목록 `VA/a34_pins.sha256` = `4e44741657dc483f2cbe5dd99a83fe9b477f5bdeffd5eadd534f87cb6cac0403`, `sha256sum -c` 83/83 OK.
- 결정 기록 `SP/K9_1_J1_NOTES_20261013.md` = `6b76cc09cc0bc0ea568f219dce16900799e3b1095b0d850ecc1d442720e6af88`. 보충 24 = `d46db6dc…aadc`.
- Promote 보고 `VA/PROMOTE.md` = `bee1269ba53496d730ba04c705c6d393198f113c4996cf04e65b6698b1280265` (작업 지시 값과 같음).
- 디스크: C: 39.5 GB, D: 368.9 GB. python·VISSIM·cscript 0개.

## 2. 방법

- 도구: `VP/v_promote.py` sha256 `88f553519d61379fdb78eaf8ba128795a1dcb1d94de8a2b431c9506b26a97627`(32,335 B, CR 0). **첫 실행 전에** `VA/LOG.md`(08:20:43 줄)와 `VP/v_promote_pins.sha256`에 고정했습니다 (보충 34 §3.3 `:161`). 실행 전에는 `ast.parse` 문법 확인만 했습니다(실행 아님).
- 읽기 전용입니다. git 읽기 명령과 파일 읽기만 합니다. `GIT_OPTIONAL_LOCKS=0`으로 `git status`가 색인을 고쳐 쓰지 않게 했습니다.
- import하지 않은 것: `make_config_n31.py`, `gb7_allowed.py`, `build_obs150_detectors.py`, Promote 스크립트(`p5_json_diff.py`, `p7_edit.py`, `p7_checks.py`).
- 목록 sha: `git cat-file blob <커밋>:GB7` 소스를 자료로 읽고, `ast`로 상수(`LIST_SCHEMA`, `SCAN`, `V`, `_SUB`, `A_K8`)만 평가했습니다. 정규 JSON 규칙(정렬 키, `ensure_ascii=False`, 구분자 `(',', ':')`, UTF-8 sha256)은 도구 안에서 따로 짰습니다. 이 규칙이 모듈 규칙과 같은지 두 가지로 확인했습니다 [실행]:
  - 같은 규칙으로 낸 K9-2-5 목록 sha = `f954c2b0510ddc8d77d8b5b6d2efb288eee4110e37eac935a4d153baefe366e7` = 보충 24 `:590`의 옛 목록 sha `f954c2b0…`.
  - 소스의 `canonical()`·`list_sha256()`·`which()`·`allowed()`·`outside()`·`__main__` 블록 AST가 K9-2-5와 K9-2-7에서 같음.
- git blob id도 `sha1("blob <크기>\0" + 바이트)`로 따로 셌고, git 값과 같았습니다.
- 실행 [실행]: 08:20:52–08:21:02, 부모 PowerShell BelowNormal(자식이 물려받음), `python -B`, `PYTHONHASHSEED=0`, `PYTHONDONTWRITEBYTECODE=1`, `PYTHONIOENCODING=utf-8`, 현재 폴더 `VP`(GWT8 아님), cmd 리다이렉션. 1회.
- 출력: `VP/v_promote.json` `cdb0cf124b447d3d0889d165350918d17dde8f1b3bb42d410caaaa0914291ddd`, `VP/v_promote.out.txt` `ed61d9b2b88194b07cbccc678a39d638ef6b5fe66d008677f4fc6d906053fac6`, `VP/v_promote.err.txt` 0 B.

## 3. ① 커밋 목록과 위생 [실행 `v_promote.json` 점검 `1.*`, `git cat-file commit`, `git reflog`]

- `git log b9734abe..HEAD` = 8개, 순서 `c20aff1d`(K9-2-7), `11d99c2a`(K9-2-6), `e27ceac8`(K9-2-5), `bfd609c0`, `b887f99f`, `2d5d95f0`, `7ed49cdf`, `1868b37c`(K9-2-0). 부모가 하나씩 이어진 선형 사슬이고 끝 부모는 `b9734abe`입니다.
- 8개 모두 작성자·커미터 = `Ming2you <alsrjsrb1915@snu.ac.kr>`.
- 두 새 커밋:
  - 첫 줄이 보충 34 `:136`·`:154`의 고정 글과 글자 같음(도구가 보충 34 줄에서 따옴표 안 글을 뽑아 비교).
  - 끝 줄 = `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`, 그 꼬리말 1번, 앞에 빈 줄, 메시지 끝 줄바꿈.
  - 부모 1개, 추가 머리(서명 등) 없음, 작성 시각 = 커밋 시각(K9-2-6 08:04:46, K9-2-7 08:07:52 KST).
  - 커밋 메시지 = `PR/msg_k926.txt`·`PR/msg_k927.txt` 바이트와 같음.
- 본문 요소:
  - K9-2-6(§3.1 `:137`): 새 sha·blob·크기, 옛 sha·blob, 두 경로, 증거 sha, 유지 정책 키, 순서 1–6 결과 줄, 순서 1 고정 문구 "make_config --k92b1 --check run on the clean K9-2-5 tree before the byte copy (D-K9-72)", D-K9-67·D-K9-72, 보충 34 고정 sha가 모두 있음.
  - K9-2-7(§3.2 `:154`): 새 목록 sha, 파일 sha·blob, 결과를 본 뒤의 보충(D-K9-38 (4)), D-K9-12 예외를 다시 쓰지 않음, 보충 34 고정 sha가 모두 있음.
- 나머지 6개 옛 커밋도 끝 줄이 같은 꼬리말입니다(§4.1 전 조건용 덧붙임 점검).
- reflog: 이 브랜치는 `commit` 항목만 있고 amend·rebase·reset 흔적이 없습니다.

## 4. ② diff 범위와 K8 가지 [실행 점검 `2.*`]

- `git diff --raw e27ceac8 c20aff1d` = 정확히 두 줄:
  - `:100644 100644 268ae471… b6ccd50d… M  CFG`
  - `:100644 100644 9fd7d519… 1ca72d81… M  GB7`
- 커밋별: `e27ceac8..11d99c2a` = CFG 한 줄, `11d99c2a..c20aff1d` = GB7 한 줄. 파일 모드 바뀜 없음.
- `git diff e27ceac8 c20aff1d -- evaluation vendor plant scripts` = 빈 결과. 네 폴더 모두 트리에 있습니다(빈 결과가 "폴더 없음" 때문이 아님). `git diff e27ceac8 HEAD -- evaluation vendor`도 빈 결과.
- K8 가지: 로컬 `b9734abe1c83f95c9cec5fca5e42b7b18cd45991`, 원격 추적 같음, `git ls-remote origin` 같음.

## 5. ③ CFG 승격 바이트와 JSON 차이 [실행 점검 `3.*`]

- blob: K9-2-6과 K9-2-7의 CFG = `b6ccd50d96321e293f6ad9cf020e53ce1a8fbf5c`. 팔 파일 blob도 K9-2-3·K9-2-5·K9-2-7에서 모두 `b6ccd50d…`(팔 파일은 승격 중 안 바뀜). K9-2-5 CFG = `268ae47132443a4a97e87ffa51ca7f7f0c878586`.
- 바이트: K9-2-6 CFG sha256 `c8e3ee2c99b66c255b2279f0aa18eaafc18d4c7689e59e260109fac3b7d71866`, 278,607 B, CR 0, BOM 없음. K9-2-5 팔 파일 바이트와 **같음**. K9-2-5 CFG = `d0f9ef395d4f9c51e6c68412f7c33abd546217e0d8cdc59d3c620183fa7aaec6`, 278,142 B.
- JSON 값 차이(K9-2-5 CFG 대 K9-2-6 CFG; 같은 키 두 번 있으면 오류로 멈추게 읽음; 형·값 `repr`로 비교) = 정확히 두 경로, 둘 다 새 쪽에만:
  - `/urban/capacity/head_floor_seed` (H-b)
  - `/urban/sc109w_through_saturation` (W)
- 두 값은 각각 키 `{evidence, evidence_sha256}` 둘뿐입니다.
  - W: `evidence` = `diagnostics/sdmpc_n31_20260924/k92/sc109w_through_saturation_v3b_u4_20261016.json`, `evidence_sha256` = `b4b7294df0369874ea53dd5f0538abd31bac1c946aebdf241bdc7837a7671712` = 그 파일의 커밋 blob 바이트 sha = 작업 파일 sha. blob `0399c369…`.
  - H-b: `evidence` = `…/k92/head_floor_seed_v3c3_robs_20261016.json`, `evidence_sha256` = `b9fa1d01b9d922e9fc327793aa428cd7b544dae221044704dea7f0af610f20ee` = 바이트 sha. blob `6ed42f16…`.
- `/runtime/decision_error_policy` = `hold_previous_on_exception` (옛·새 둘 다).
- 덧붙임 [실행]: 증거 파일의 값 잎만 읽음. W `/values/capacity_veh_h` = 5209.8, H-b `/values/seed` = 1045.1612903225805 (작업 지시의 값과 같음). 다른 잎(시드별 자료 등)은 열지 않았습니다.
- 글 diff는 9줄 더함·1줄 지움입니다. 지운 1줄은 `head_free_service` 줄 끝에 쉼표가 붙은 것입니다(JSON 키를 뒤에 더하면 생김). 값 차이는 위 두 경로뿐입니다 [실행 `git diff e27ceac8 11d99c2a -- CFG`].
- D-K9-72 순서 1(편집 전 make_config 점검)의 시점 [읽음·추론]: `make_config_n31.py`는 작업 트리 CFG 바이트를 바탕으로 읽고(`cfg_document`, `:643-649`), 두 키가 이미 있으면 `ValueError`를 냅니다(`apply_k92b1`, `:652-658`, 호출 `:721-723`). 그래서 기록된 출력 `CONFIG_N31_K92B1_OK … c8e3ee2c…` 자체가 "두 키 없는 CFG로 돌았다", 곧 복사 전에 돌았다는 증거입니다. 기록 파일 `PR/pre_edit_mkcfg_k92b1_check.out.txt`(`41a9020a…`)는 첫 Declare 출력 `VA/work/pre_mkcfg_k92b1_check.out.txt`와 바이트가 같습니다 [실행]. 복사 뒤 obs150 기록 `PR/post_copy_obs150_check.out.txt`(`7e6191ad…`)도 첫 Declare 출력과 같습니다 [실행]. 두 점검은 다시 돌리지 않았습니다(§3.3에 없음, 그리고 make_config는 지금 돌리면 설계상 `ValueError`).

## 6. ④ GB7 (R2-12) [실행 점검 `4.*`]

- blob: K9-2-5·K9-2-6 = `9fd7d5194081a089298444351072a2d058af5aef`(sha256 `c6f9ca1c…94c8`, 11,304 B; K9-2-6은 GB7을 안 바꿈). K9-2-7 = `1ca72d81f6e63736fa835cd408c9c9d6b7563ffa`, sha256 `61c70c222cf3bed2a0a299b539aa3fccad288c059b72be678cceda2c3dc6f319`, 11,780 B, CR 0, BOM 없음.
- 목록 sha(따로 셈) = **`a8148f3849fb5e26f09d8f0a095d442aa56da051d888df0b2f657dba089e7af1`** = 보충 24 `:594`·보충 34 `:150` 기대값.
- 도구가 모은 출력 줄 = `GB7_ALLOWED schema=k8-gb7-allowed/v1 V=7 A_K8=35 R1=16 R2=12 R3=7 list_sha256=a8148f38…7af1` = 보충 34 `:150` 기대 줄 = Promote 기록 `PR/p7_check3_gb7_main.out.txt`.
- 항목 구조:
  - 새 `A_K8`에서 R2-12를 빼면 옛 `A_K8` 34개와 순서까지 같음. R2-12는 1개, R2-11 바로 뒤. id 겹침 없음.
  - R2-12 = `('R2-12', 'R2', r'/diagnostics/leg_ramp_split_(?:len_[^/\[]*|length_fallback)', <이유>)`. 정규식 글자가 보충 24 `:591`과 같음.
  - 이유 문자열 = 보충 24 `:592` 따옴표 안 글자(117자, UTF-8 sha256 `7a51c150f6bc3cc4…`)와 같음.
  - `V`(7개)·`SCAN`·`LIST_SCHEMA`·`_SUB` 안 바뀜.
- 판정 표(보충 24 `:600-605`, 보충 34 `:151`), 보충 전 → 뒤:
  - `…_len_SC1001_W_out`: 밖 → R2-12
  - `…_length_fallback`: 밖 → R2-12
  - `…_req_last_SC1001_W_out`, `…_u_on_last`, `…_len_SC1001_W_out/x`: 밖 → 밖
  - `…_injected_RM_C10484`: R2-11 → R2-11
- E_K92 네 경로(`/metadata/k92_w`, `/metadata/k92_hb`, `/metadata/k92_hb_seed_binding`, `/metadata/head_discharge_floor_173_p4_e36d6761cfeac634`): 보충 전·뒤 모두 `which` = None (A 밖) (보충 34 `:153`).
- 바이트 범위(줄 단위 비교, 보충 34 `:152`):
  - 바뀐 곳은 끼워 넣기 두 덩이뿐이고 지운 줄은 0입니다.
  - 덩이 1 = 새 20번째 줄 한 줄. 옛 19번째 줄(`  A 밖 경로가 하나라도 다르면…`) 바로 뒤입니다. 글 = `- ` + 보충 24 `:593` 따옴표 안 글자 + `.`(보충 34 `:146`). 이 줄은 모듈 docstring 안에 있고 파일 전체에 1번입니다.
  - 덩이 2 = 새 101–102번째 줄 두 줄. 옛 R2-11 튜플 끝 줄(99) 바로 뒤이고, 새 소스의 R2-12 튜플 범위(101–102)와 정확히 같습니다.
  - `git diff --numstat 11d99c2a c20aff1d -- GB7` = `3 0`.
  - docstring은 목록 sha에 들지 않습니다 [읽음 `canonical()`].

## 7. ⑤ 작업 트리, 푸시 없음 [실행 점검 `5.*`, `6.*`]

- HEAD = `c20aff1d…`, `symbolic-ref HEAD` = `refs/heads/claude/k92-b1-20261016`.
- `git status --porcelain=v1 -uall` 0줄, `git diff --cached` 빈 결과, stash 0. 무시된 항목 152개는 모두 `!!` 줄(추적 안 된 `??` 줄 0).
- 작업 파일 바이트 = ls-tree blob(`hash-object --no-filters`, 내 sha1 계산, `ls-tree HEAD` 셋이 같음):
  - CFG `b6ccd50d…`, GB7 `1ca72d81…`, 팔 파일 `b6ccd50d…`.
  - 셋 다 `text: unset`, `i/lf w/lf attr/-text`.
- 훅: `core.hooksPath` 없음, 공통 git 폴더 hooks에 `.sample` 아닌 파일 0.
- 푸시 없음:
  - `branch.claude/k92-b1-20261016.remote` 설정 없음.
  - 원격 추적 ref에 k92 없음.
  - `git ls-remote origin`(18 ref)에 k92 이름 없음, `11d99c2a`·`c20aff1d`를 가리키는 ref 없음.
  - 로컬에서 `c20aff1d`를 가리키는 ref는 이 브랜치 하나, `11d99c2a`를 가리키는 ref는 0.
- K8 원격 가지 = `b9734abe…` 그대로.
- 동결·런: `D:/VISSIM-merge/frozen/` 34항목(폴더 17 + 로그 17) 그대로, 가장 늦은 것 = FRZ_K8b `sdmpc31_b9734abe_202610141821`(`FREEZE.json` `6143d3eb…`, 보충 34 `:17`과 같음), k92 동결 0. RVA `D:/VISSIM_runs/20261023_sdmpc31_k92` 없음.

## 8. 도구 거짓 1개와 남은 파일 보충 점검

- 도구 점검 `5.no_stray_files_since_0759`: 07:59 KST(보충 34 고정 시각) 뒤 수정된 GWT8 파일(`.git` 빼고 10,721개)을 셌습니다. 기대 = {CFG, GB7}, 실제 = {GB7}. → 거짓.
- 원인 [실행 `VP/supp_file_times.txt` `1abf0cbf…1436`]: CFG LastWriteTime = `2026-10-20 06:48:04.362` = 팔 파일 LastWriteTime과 1 ms까지 같습니다. CFG CreationTime은 `2026-10-04 15:29:52`(덮어쓰기라 대상 생성 시각 유지). Promote가 `[System.IO.File]::Copy(…, $true)`로 복사했고(`VA/LOG.md` Promote 순서 2 줄), 이 복사는 원본 수정 시각을 옮깁니다 [추론]. 바이트는 이미 §5에서 커밋 blob과 같음을 확인했습니다.
- 보충 훑기 [실행, 도구 결과를 본 뒤라 공개]: CreationTime 또는 LastWriteTime이 07:59 뒤인 파일 = GB7 하나, 새 폴더 0. 그래서 "남은 파일 없음"은 참입니다.
- 이 거짓은 Promote 결함이 아니라 내 기대 오류입니다. 도구와 기대는 고치지 않았습니다.
- CFG 수정 시각이 옛 시각인 영향 [읽음·추론]: `D:/VISSIM-merge/tools/run_sdmpc_n31.ps1`·`freeze_worktree.ps1`에 `LastWriteTime`·`getmtime`이 없습니다(grep 0). 동결과 관문은 sha로 대조합니다. 영향 없음으로 봅니다.

## 9. 덧붙인 점검 (EXTRA 8/8 참) [실행]

- 8개 커밋 끝 줄 꼬리말, 메시지 파일 = 커밋 메시지, 증거 값 5209.8·1045.1612903225805, Promote 출력 줄 기록 = 기대 줄, docstring 줄 위치, 무시 항목 꼴, 훅 없음.
- Promote 점검 출력 기록 2개 = 첫 Declare 출력 바이트, `PR/*.err.txt` 8개 모두 0 B.
- 도구 밖 [실행]:
  - `git diff 11d99c2a c20aff1d`를 다시 내니 `PR/k927_commit_diff.patch`와 바이트가 같음(`595f1ca7…`). K9-2-6 stat 다시 낸 것 = `PR/k926_commit_stat.txt`(`94ea2e04…`).
  - `PR` 25파일 sha = `PROMOTE.md` §6 표 값.
  - REPVA `promote/` 사본: `sha256sum -c SHA256SUMS_PROMOTE.txt` 26/26 OK, 목록 파일 `4985c37a…`, 25파일과 `PROMOTE.md`가 원본과 바이트 같음.

## 10. 결함 아닌 메모

1. **보고 파일 이름**: 보충 34 §3.3(`:161`, `:168`)과 §4.1(`:176`)은 `VA/VERIFY_PROMOTE_VA.md`를 봅니다. 작업 지시는 `VERIFY_PROMOTE_r1.md`를 정했습니다. 두 이름에 같은 바이트를 두었습니다. PushFreeze 단계는 `VERIFY_PROMOTE_VA.md`의 `pass = true`와 검증 head `c20aff1d…`를 보면 됩니다.
2. **Promote LOG 시각**: Promote LOG 줄 다섯 개(08:03:10·08:08:30·08:10:30·08:12:00·08:14:30)는 어림 시각이었고, 뒤에 덧붙인 08:09:16 줄이 실제 범위로 정정했습니다(`PROMOTE.md` §5-7). 그래서 "Promote 점검 스크립트를 LOG에 고정한 뒤 처음 돌렸다"는 순서는 LOG 시각만으로는 따로 확인할 수 없습니다 [추론]. 이 검증은 그 스크립트 결과에 기대지 않고 모든 값을 따로 다시 냈으므로 결론에 영향이 없습니다. 고칠 것은 없습니다. 다음 단계부터는 시계를 읽어 적는 것이 좋겠습니다.
3. **순서 1을 두 번 돈 것**(`PROMOTE.md` §5-1): 1차 `try1_*` 출력에 BOM이 붙어 있음은 PowerShell 리다이렉션으로 실제 돈 흔적과 맞습니다 [실행 sha `ad13edcc…`; 추론]. 두 번 모두 쓰기 0이라는 기록과 지금 상태(트리 깨끗함)가 맞습니다.
4. **CFG 수정 시각**: §8. 바이트·blob 판정에는 영향이 없습니다.
5. **이 검증에서 도구 전에 한 작은 읽기**: `python -c` 두 번(증거 파일 키 이름과 두 값 보기; 첫 번은 PowerShell 파이프가 붙인 BOM으로 JSON 읽기 실패, 이때 우선순위 지정 없음), `git ls-remote origin` 1회. 모두 읽기만 했습니다.

## 11. 한 일과 안 한 일

- 한 일: git 읽기 명령, 파일 읽기, `VP/v_promote.py` 1회, PowerShell 파일 시각 훑기 2회(1회는 화면만, 1회는 `VP/supp_file_times.txt`로 저장), `git ls-remote origin` 2회(도구 밖 1, 도구 안 1).
- 쓴 곳: `VP/`(도구·고정 목록·출력·보충 파일), 이 보고와 같은 바이트의 `VA/VERIFY_PROMOTE_VA.md`, `VA/LOG.md` 덧붙임, 사본 `REPVA/verify_promote/`.
- 안 한 일: 커밋·푸시·동결·관문·재생·VISSIM·COM·러너·시험 0. GWT8 작업 트리·`.git`·`frozen/`·런 폴더 쓰기 0. 끈 프로세스 0. 금지 시험 0.
- 블라인드: 봉인 시드(37/59/61/67) 자료·codex 64cf 숫자 0, v3c3-s47 자료 0. 증거 파일에서는 두 값 잎만 읽었습니다.
- 끝 상태 [실행 08:24]: GWT8 HEAD `c20aff1d…`, status 0줄, K8 가지 `b9734abe…`, 원격 k92 0, python·VISSIM·cscript 0, C: 39.5 GB·D: 368.9 GB.

## 12. 파일 (`VP/`, sha256 [실행])

| 파일 | sha256 |
|---|---|
| `v_promote.py` (실행 전 고정) | `88f553519d61379fdb78eaf8ba128795a1dcb1d94de8a2b431c9506b26a97627` |
| `v_promote_pins.sha256` | 위 값 한 줄 |
| `v_promote.json` | `cdb0cf124b447d3d0889d165350918d17dde8f1b3bb42d410caaaa0914291ddd` |
| `v_promote.out.txt` (끝: `CORE 36/37 EXTRA 8/8`, `V_PROMOTE_CORE_FAIL`, `V_PROMOTE_EXTRA_ALL_OK`; 거짓 1개는 §8) | `ed61d9b2b88194b07cbccc678a39d638ef6b5fe66d008677f4fc6d906053fac6` |
| `v_promote.err.txt` | 0 B |
| `supp_file_times.txt` | `1abf0cbf1780c792287235136e076fa7118d931da946a380b571627d67d41436` |
| `recheck_k927_diff.patch` | `595f1ca7ca69894a31b540a2c2c2ee4f7d34b89015b5754348297d0e1deefda3` |
| `recheck_k926_stat.txt` | `94ea2e0414e0e8a0d89eeb02ebe2b05ec13d49ec4e28e7e65922bc80dfe5082f` |

검증 head = c20aff1d7bf0c432cb4f20e2922bd406d857aa5d

pass = true
