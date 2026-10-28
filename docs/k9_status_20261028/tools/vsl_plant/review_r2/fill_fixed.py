"""Review r2 one-off (scratch): fill the placeholders of PRE_VP_FIXED.md.  python -B fill_fixed.py <PRE_VP_FIXED.md> <time>"""
import sys

p, when = sys.argv[1], sys.argv[2]
s = open(p, encoding='utf-8').read()

SMOKE = """- [실행] smoke v5 (17:15:33–17:25:42 KST, 공유 잠금 아래 — 다른 워크플로 잠금이 풀린 뒤 6 s 기다림, WMI 분리 PID 46848, BELOW_NORMAL, 목록 밖 v3c3-s31 T=2,400, 명세 `smoke/specs/spec_smoke_v5.json` = v2 명세 + C8·C9): 종료 0, 벽시계 609 s(준비 60 s, AD 148 s, 스칼라 묶음 100 s(작업자 5), 절제 10굴림 세 차례 약 283 s; 다른 워크플로가 함께 돌아 v4 의 403 s 보다 느림).
- [실행] R1 목적값 비트 같음, 비용 최대 차 ≤ 1e-13, R2 − R1 = 0.0. REPACK 토큰 = REC 토큰(그래서 R3 는 캐시 적중, §3.4). null 비트 같음이고 null 요청 sha ≠ EXEC_scalar 요청 sha(따로 굴린 재현). C5 요청 sha = null 요청 sha(구조상 0).
- [실행] 훅 파일 16개, 모든 평가 레이블에서 걸음 450·블록 150·셀 31·오류 0, 출구 기록(X1·X2) 모두 있음(`exit_missing` 0건), 셀 경계 차 0.000 m.
- [실행] 도달 점검 C1–C9 모두 참(C8 `cells {"18": {"old": 38.7, "new": 0.0}}`, C9 φ 3.0 → 0 + 같은 ν). 기준(EXEC)과 블록 값이 다른 절제 = C1·C2·C3·C4·C7·C8·C9, 같은 절제 = C5·C6(값은 보지 않고 같음·다름만 봄).
- [실행] `vp_jobcheck.py` 걸림 0(`smoke/jobcheck_v5.json` 75afe816…), `vp_smokecheck.py`(`smoke/smokecheck_v5.json` 097f3aa8…), `vp_tablesmoke.py` 멈춤 0(`smoke/tablesmoke_v5.json` 2656e36b…). 기록 `probe.json` d30ecbe6…, `job_summary.json` 4797c06b….
- 검토자는 smoke v5 의 J·편향·X1·X2 값을 보지 않았습니다. 이 문서의 규칙·문턱은 smoke 값으로 정하지 않았습니다."""

PINS = """- 핀 목록 파일 `VP/SHA256SUMS_VP.txt`(39줄, VP 기준 상대 경로, `sha256sum -c` 로 대조) sha256 `51f9f38bdd1c2b2806161f442ae4af0d1df24105d69050697ba44cd863430156`, 바깥 핀 `VP/SHA256SUMS_VP_EXT.txt`(15줄, 절대 경로) sha256 `5e84baf4b90c799efe1efb20911038ee8a17264a7934c76de59380ae82c21ad6`. 두 목록 모두 [실행] `sha256sum -c` 걸림 0. r1 목록은 `SHA256SUMS_VP_r1.txt`(5c36cffa…)·`SHA256SUMS_VP_EXT_r1.txt`(7ce3016b…)로 둠.
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
- 검토 r2 의 일회용 편집 스크립트 `VP/review_r2/edit_analyze_2.py`·`fill_fixed.py` 는 도구가 아닙니다(실행 경로에 없음)."""

for a, b in (('SMOKE_V5_PLACEHOLDER', SMOKE), ('PINS_PLACEHOLDER', PINS), ('SMOKE_V5_PSTATE', '8–11'),
             ('SMOKE_V5_PTOTAL', '1.2–1.7'), ('FIXED_TIME_PLACEHOLDER', when)):
    assert s.count(a) == 1, a
    s = s.replace(a, b)
open(p, 'w', encoding='utf-8').write(s)
print('filled')
