# v3 N9-3 - 관측을 60초로 집계하고 ΔJ 를 같은 prefix 에서 계산하는 계약 테스트
"""VISSIM 1초 관측을 보존한 채 60초로 집계하고, `ΔJ = J(action) − J(base)` 를 만든다.

계획 원문(N9-3)이 요구하는 것이다.

    VISSIM 1초 관측을 보존하고 60초로 집계한다. ΔJ(action) = J(action) − J(base) 를
    같은 prefix 에서 계산한다. 반복은 잡음만 추정하고 표본 수를 늘리지 않는다.
    controlled 15 / monitor 26 / midblock 9 / boundary / ramp / freeway 를 분리한다.

세 문장이 각각 함정을 하나씩 막는다.

**"같은 prefix 에서"** — base 와 action 은 anchor 까지 동일한 궤적이어야 한다. 다른 prefix 의
J 를 빼면 그 차이가 레버 효과로 둔갑한다. 그래서 prefix 신원이 다르면 거부한다.

**"반복은 잡음만 추정하고 표본 수를 늘리지 않는다"** — replicate 를 독립 표본으로 세면
유의성이 부풀려진다. 집계는 replicate 를 평균으로 접고 분산은 잡음 추정에만 쓴다.

**채널 분리** — 총량 지표가 접속부 오차를 흡수하지 못하게 한다. 램프미터 레버 효과가
발생하는 곳이 정확히 거기다.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
if str(REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO / "scripts"))

import paired_validation_aggregate as agg  # noqa: E402


class BinningTests(unittest.TestCase):
    def test_one_second_samples_collapse_to_sixty_second_bins(self) -> None:
        samples = [(float(t), 1.0) for t in range(180)]
        bins = agg.aggregate_to_bins(samples, bin_sec=60.0)
        self.assertEqual([b.start_sec for b in bins], [0.0, 60.0, 120.0])
        self.assertEqual([b.count for b in bins], [60, 60, 60])
        for b in bins:
            self.assertAlmostEqual(b.mean, 1.0, places=12)

    def test_bin_edges_are_half_open(self) -> None:
        """[start, end) 다. 닫힌 구간이면 경계 표본이 두 bin 에 들어간다."""
        bins = agg.aggregate_to_bins([(59.999, 1.0), (60.0, 2.0)], bin_sec=60.0)
        self.assertEqual([(b.start_sec, b.count) for b in bins], [(0.0, 1), (60.0, 1)])

    def test_a_partial_trailing_bin_is_reported_not_dropped(self) -> None:
        """잘린 bin 을 조용히 버리면 표본 수가 줄어든 것을 아무도 모른다."""
        bins = agg.aggregate_to_bins([(t, 1.0) for t in range(0, 90)], bin_sec=60.0)
        self.assertEqual(len(bins), 2)
        self.assertEqual(bins[-1].count, 30)
        self.assertTrue(bins[-1].partial)
        self.assertFalse(bins[0].partial)

    def test_empty_bins_are_materialised_with_zero_count(self) -> None:
        """구멍을 건너뛰면 인덱스가 밀려 base 와 action 의 bin 이 어긋난다."""
        bins = agg.aggregate_to_bins([(0.0, 1.0), (130.0, 3.0)], bin_sec=60.0)
        self.assertEqual([b.start_sec for b in bins], [0.0, 60.0, 120.0])
        self.assertEqual(bins[1].count, 0)
        self.assertIsNone(bins[1].mean)

    def test_rejects_unsorted_input(self) -> None:
        with self.assertRaises(agg.AggregateError):
            agg.aggregate_to_bins([(60.0, 1.0), (0.0, 1.0)], bin_sec=60.0)


class DeltaTests(unittest.TestCase):
    def test_delta_requires_the_same_prefix_identity(self) -> None:
        """다른 prefix 의 J 를 빼면 그 차이가 레버 효과로 둔갑한다."""
        base = agg.RunObjective(prefix_id="p1", anchor_sec=900, value=10.0)
        action = agg.RunObjective(prefix_id="p2", anchor_sec=900, value=12.0)
        with self.assertRaises(agg.AggregateError):
            agg.delta_j(action, base)

    def test_delta_requires_the_same_anchor(self) -> None:
        base = agg.RunObjective(prefix_id="p1", anchor_sec=900, value=10.0)
        action = agg.RunObjective(prefix_id="p1", anchor_sec=1500, value=12.0)
        with self.assertRaises(agg.AggregateError):
            agg.delta_j(action, base)

    def test_delta_is_action_minus_base(self) -> None:
        base = agg.RunObjective(prefix_id="p1", anchor_sec=900, value=10.0)
        action = agg.RunObjective(prefix_id="p1", anchor_sec=900, value=12.5)
        self.assertAlmostEqual(agg.delta_j(action, base), 2.5, places=12)


class ReplicateTests(unittest.TestCase):
    def test_replicates_collapse_to_one_sample(self) -> None:
        """계획 - 반복은 잡음만 추정하고 표본 수를 늘리지 않는다."""
        summary = agg.collapse_replicates([10.0, 12.0, 11.0])
        self.assertAlmostEqual(summary.value, 11.0, places=12)
        self.assertEqual(summary.sample_count, 1)
        self.assertEqual(summary.replicate_count, 3)

    def test_noise_uses_the_spread_across_replicates(self) -> None:
        summary = agg.collapse_replicates([10.0, 12.0])
        self.assertAlmostEqual(summary.noise, 2.0, places=12)

    def test_single_replicate_reports_unknown_noise_not_zero(self) -> None:
        """반복이 하나면 잡음을 모른다. 0 으로 두면 모든 효과가 유의해 보인다."""
        summary = agg.collapse_replicates([10.0])
        self.assertAlmostEqual(summary.value, 10.0, places=12)
        self.assertIsNone(summary.noise)

    def test_no_replicates_is_an_error(self) -> None:
        with self.assertRaises(agg.AggregateError):
            agg.collapse_replicates([])


class ChannelTests(unittest.TestCase):
    def test_channels_match_the_plan(self) -> None:
        self.assertEqual(
            agg.CHANNELS,
            ("controlled", "monitor", "midblock", "boundary", "ramp", "freeway"),
        )

    def test_expected_channel_sizes_are_declared(self) -> None:
        """계획의 controlled 15 / monitor 26 / midblock 9 를 코드에 못박는다."""
        self.assertEqual(agg.EXPECTED_CHANNEL_SIZES["controlled"], 15)
        self.assertEqual(agg.EXPECTED_CHANNEL_SIZES["monitor"], 26)
        self.assertEqual(agg.EXPECTED_CHANNEL_SIZES["midblock"], 9)

    def test_split_keeps_every_item_exactly_once(self) -> None:
        assignment = {"a": "controlled", "b": "ramp", "c": "controlled"}
        split = agg.split_by_channel(["a", "b", "c"], assignment)
        self.assertEqual(split["controlled"], ["a", "c"])
        self.assertEqual(split["ramp"], ["b"])
        self.assertEqual(sum(len(v) for v in split.values()), 3)

    def test_unassigned_items_are_reported_not_dropped(self) -> None:
        """미배정을 버리면 총량 지표가 접속부 오차를 흡수한다 - 계획이 막는 바로 그것이다."""
        split = agg.split_by_channel(["a", "z"], {"a": "controlled"})
        self.assertEqual(split["unassigned"], ["z"])

    def test_unknown_channel_is_rejected(self) -> None:
        with self.assertRaises(agg.AggregateError):
            agg.split_by_channel(["a"], {"a": "made_up"})


if __name__ == "__main__":
    unittest.main()
