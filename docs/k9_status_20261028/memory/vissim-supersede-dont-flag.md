---
name: vissim-supersede-dont-flag
description: 승격된 수정은 구버전을 격리 폴더로 치우고 정본에서 완전히 제거한다 — 플래그로 남겨두지 마라
metadata: 
  node_type: memory
  type: feedback
  originSessionId: ab16ebe2-114b-4182-9877-9977f80eb5f9
  modified: 2026-08-27T02:51:53.025Z
---

정합성 수정(movement 병합 같은)을 하고 검증런으로 승격시켰으면, 이전 버전 코드는
`_superseded_<날짜>/` 같은 격리 폴더로 옮겨 참조용으로만 두고 **정본 코드에서는 흔적도
남기지 않는다.** 어댑터 사본을 새로 파고 옛 경로를 플래그로 꺼두는 방식은 금지다.

**Why:** 2026-08-27 에 이 방식이 실제로 터졌다. 어댑터가 19벌(155,827행)로 늘어
최상위 함수 217개 중 195개가 중복 정의되고 17개는 구현이 갈렸다(`main` 10종,
`install_config_switches` 9종). TTT 사다리 11개 팔이 서로 다른 어댑터 9개·sha 10종으로
돌아 팔 간 차이가 설정인지 코드인지 분리되지 않았다. 그리고 새 시나리오를 돌릴 때
플래그를 제대로 안 읽어 구버전 경로가 조용히 살아나는 사고가 반복됐다 —
`urban.capacity.perimeter` 는 코드·테스트·A/B 팔까지 다 만들고 기본 off 인 채 잊혔고,
`rollout_far` 는 25단 config 체인 어디에도 없어 far 가 실런에서 **한 번도 계산되지
않았다**(결정 37개에 far 진단 키 0회). 분석 하네스도 설치 함수를 일부만 불러
movement 를 474(실제 368)로 읽는 오측정을 냈다.

**How to apply:** 정본은 어댑터 한 벌. 새 기능은 사본이 아니라 정본에 넣고, 끌 필요가
있으면 config 키 하나로만 끈다. 승격이 끝나면 구버전은 격리 폴더로 옮기고 sha 와
그것을 쓴 런 목록을 매니페스트로 남긴다(`run_provenance` 증거 사슬 보존). config 도
같다 — `extends` 사슬을 길게 쌓지 말고 정본 시나리오는 자립 파일로 평탄화한다.
어댑터 사본을 만들고 싶어지면 그 자체가 신호다. 관련: [[vissim-resolve-live-controller-first]]
