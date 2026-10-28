---
name: vissim-n21-vsl-product-oom
description: 21셀 격자에서 결정이 OOM 으로 죽은 진짜 원인 - VSL 시퀀스 후보가 세그먼트 데카르트 곱을 전량 전개한다 (2026-09-08)
metadata: 
  node_type: memory
  type: project
  originSessionId: 363c7808-e973-4c3e-92d8-2d00dcc50f83
  modified: 2026-09-08T03:58:40.967Z
---

본선 격자를 8셀→21셀로 늘린 뒤 wu-link 결정이 **MemoryError** 로 죽고
`controller_status=fallback_fixed` 로 떨어졌다(런 n21x15_n0, t=900, decision_wall 560.5 s).
워크스테이션이 실제로 OOM 으로 꺼져 사용자가 RAM 을 64→128 GB 로 증설했다.

원인은 속도가 아니라 **조합 폭발**이다. `WuFaithfulFollower._freeway_vsl_sequence_candidates`
(vendor wu_faithful_follower.py:2124)가 세그먼트별 VSL 옵션의 **전체 곱을 리스트로 전개**한 뒤
복사하고 정렬한 다음에야 `vsl_sequence_candidate_limit`(12)로 자른다. 자유도를 갖는 세그먼트는
`upstream_control_idx` = 첫 off-ramp 셀보다 상류인 셀들뿐이라, 8셀에서는 FW_E 가 3개(10^3=1,000)
였는데 **21셀에서는 8개가 되어 10^8** 이다(FW_W 는 6 → 10^6).

수선 = 어댑터 몽키패치 `install_freeway_vsl_sequence_kbest`
(`scripts/apply_vsl_kbest_patch_20260908.py`, config 키 `freeway.vsl_sequence_kbest`, 기본 true).
정렬 키 (mean, terminal, first)가 **세그먼트별 합의 사전식 비교**라 단조이므로, 세그먼트별 옵션을
자기 키로 정렬하고 인덱스 벡터를 힙으로 전개하는 k-best 가 같은 순서를 낸다. 동률은 원본
`sorted`(안정)가 생성 순서를 지키므로 **원래 옵션 인덱스 튜플**을 키 4번째 성분으로 넣어야
완전 동치가 된다 — 이걸 빼면 동률 자리에서 갈린다(실측으로 확인).
검증: `scripts/test_vsl_kbest_offline_20260908.py` — 자유 2/3/4 에서 원본과 **완전 일치**,
21셀 실제 설정에서 0.016 s. 결정 1회 상주메모리 21 GB → 0.05 GB.

**교훈**: 격자 해상도를 올릴 때는 셀 수가 *지수로* 들어가는 자리를 먼저 찾아라. vendor 는
"limit 으로 자르니 괜찮다" 는 전제로 짜였고, 그 자르기가 전개 **뒤**에 있었다.

관련: [[vissim-parent-run-launch-traps]] (같은 런이 StallSec 300 에도 걸렸다 — 수요 스케일링
COM 이 8분이라 임계를 2400 으로 올렸다), [[vissim-supersede-dont-flag]] (수선은 어댑터 정본
한 벌에 config 키로 넣었다).
