# -*- coding: utf-8 -*-
"""Wu 충실 팔로워를 그대로 쓰되 player 입도를 링크 단위로 고정한 가격 Stackelberg 팔.

무엇을 하는 파일인가
--------------------
`StackelbergWuMeteredController`(가격 4채널 + λ_P/λ_UF)와 `WuFaithfulFollower`(Wu 2022
§IV-D 충실 Jacobi 분산 팔로워)를 **그대로** 쓴다. 바꾸는 것은 한 줄이다.

    segment_agents = False        freeway agent 를 세그먼트 16개가 아니라 링크 2개로

이게 전부인 이유는 wu 팔로워가 이미 우리가 원하는 player 구조를 기본값으로 갖기 때문이다.

    urban_agents   = list(cfg.network.signals)         17개 (SC1 … SC1005)
    freeway_agents = list(cfg.network.freeway_links)    2개 (FW_W · FW_E)
    segment_agents = False                              ← 기본이 링크 단위

`build_pstack_flagship_controller` 가 `segment_agents = True` 로 켜서 세그먼트로 쪼개고
있었을 뿐이다. 그래서 "player 를 우리 구조로" 는 그 스위치를 끄는 것으로 끝난다.

**plant 모델은 안 바뀐다.** `freeway_segments_per_link = 8` · `ramps = 4` 가 그대로라
METANET 롤아웃은 여전히 2링크 x 8세그먼트 = 16셀 + 램프 4개를 굴린다. 바뀌는 것은
"누가 어느 레버를 소유하고 어느 셀을 보는가" 뿐이다. 링크 agent 는 VSL 1 + 램프 2 =
액션 3개를 정확히 소유한다 — 세그먼트 8개가 VSL 하나를 두고 경합하던 구조가 사라진다.

2026-08-20 개정 — 초판(333줄)에서 덜어낸 것
-------------------------------------------
초판은 `DistributedCoordinator` 를 베이스로 삼아 가격 오라클 3개·λ_P 듀얼·neighbor
결합항을 직접 구현했다. **그건 요청받은 것이 아니었다** — 요청은 "wu 구조를 홀드하고
player 만" 이었는데 초판은 리더의 가격 기구만 보존하고 팔로워의 GNE 를 분산 코디네이터
것으로 바꿔놨다(순수 Jacobi 대 블록 Gauss-Seidel, 결합변수 해상도 4키 대 48키).
확인해 보니 직접 구현한 것도 전부 불필요하거나 열등했다.

  가격 오라클 3개   wu 에 7개가 이미 있다(green·metering·vsl·offset·교차 2종·λ_P).
  λ_P 듀얼          wu 의 `_lambda_np_update` + `use_dual_np`(기본 True)가 이미 한다.
                    λ_UF 도 있다(`wu_faithful_nuf_coordination_mode`, 기본 "equality").
  neighbor 결합항   램프 저수지가 차기 전 상류 교차로 비용을 매끄럽게 계상하려던 휴리스틱.
                    (a) 문턱은 물리적으로 옳다 — 저수지에 공간이 있는 동안 차량은 램프에
                        대기하고 그건 이미 `link_ramp_queue` 로 계상된다. 빠진 질량이 아니었다.
                    (b) wu 는 그 회계를 substep 마다 FIFO 이월로 돌려 분산 판의 종말 1회
                        추정보다 정교하다(`count_blocked_ramp_inflow`, 기본 True).
                    (c) 근시 병리는 wu 의 `follower_terminal_cost_enabled`(기본 OFF)가
                        Q^2/2R 삼각 배수 tail 로 더 잘 다룬다 — far 의 램프 항과 같은 형태다.
                    그래서 넣지 않는다. 필요해지면 (c) 를 켜는 게 먼저다.

`AgentSpec.neighbors`(분산 코디네이터의 죽은 필드) 이야기도 여기서는 해당 없다 — wu 는
`_coupling` 으로 램프↔교차로를 직접 주고받는다(`u_on_{ramp}` · `arr_{signal}_{phase}` ·
freeway→urban 은 `_last_offramp_flow`).

무엇을 켜는가
-------------
가격 플래그는 어댑터의 `build_priced_wu_link_controller` 가 세운다. flagship 과 같은
운영점(green·metering·vsl·offset ON, 교차가격 OFF)을 쓰되 `segment_agents` 만 다르다.
"""
from __future__ import annotations

from src.controllers.stackelberg_wu_metered import StackelbergWuMeteredController
from src.controllers.wu_faithful_follower import WuFaithfulFollower
from src.models.state import ExperimentConfig


class LinkAgentWuFollower(WuFaithfulFollower):
    """Wu 충실 팔로워 그대로. freeway agent 입도만 링크 단위로 고정한다.

    `segment_agents` 는 wu 의 기본값도 False 지만 여기서 명시적으로 못박는다 —
    `build_pstack_flagship_controller` 가 True 로 켜는 값이라 "안 켰으니 False 일 것" 에
    기대면 빌더가 바뀔 때 조용히 뒤집힌다.
    """

    def __init__(self, cfg: ExperimentConfig):
        super().__init__(cfg)
        self.segment_agents = False


class PricedWuLinkStackelbergController(StackelbergWuMeteredController):
    """가격 리더 그대로 + 링크 단위 player.

    `StackelbergWuMeteredController` 가 "`_make_follower_solver` 만 오버라이드하는 thin
    서브클래스" 로 설계돼 있어(그 파일 독스트링) 가격 계산·하달·GNE 반복을 한 줄도
    건드리지 않는다.
    """

    def _make_follower_solver(self, cfg: ExperimentConfig):
        return LinkAgentWuFollower(cfg)
