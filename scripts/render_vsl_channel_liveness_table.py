# VSL 채널 생사 요약 JSON을 보고서용 마크다운 표로 렌더링한다.
"""사용:
    python scripts/render_vsl_channel_liveness_table.py <summary.json>
analyze_vsl_channel_liveness.py 가 낸 JSON을 그대로 표로 옮긴다. 손으로 옮겨
적다가 숫자가 틀어지는 것을 막기 위한 용도다.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

VERDICT_KO = {"live": "집행", "partial": "부분", "dead": "죽음", "no_data": "표본없음"}


def main() -> None:
    d = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    print("| 채널 | 호스트 링크@pos(m) | 스냅(m) | 표본 | 자기지문 | 대상차량 자기지문 | 택시(class70) 비중 | 택시 자기지문 | 상류지문 유입 | 판정 |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for c in d["channels"]:
        if c["samples"] == 0:
            print(f"| {c['segment_id']} | {c['host_link']}@{c['dsd_pos_m']:.1f} | - | 0 | - | - | - | - | - | 표본없음 |")
            continue
        foreign = ", ".join(
            f"{b['segment_id']} {b['share']*100:.1f}%" for b in c["top_foreign_bands"]
        ) or "-"
        taxi_own = "-" if c["taxi_own_share"] is None else f"{c['taxi_own_share']*100:.1f}%"
        print(
            f"| {c['segment_id']} | {c['host_link']}@{c['dsd_pos_m']:.1f} | {c['dsd_snap_offset_m']:+.3f} | "
            f"{c['samples']} | {c['own_share']*100:.1f}% | {c['eligible_own_share']*100:.1f}% | "
            f"{c['taxi_share']*100:.1f}% | {taxi_own} | {foreign} | {VERDICT_KO[c['verdict']]} |"
        )
    print()
    print(f"표본 시각: {d['complete_sample_secs']}")
    print(f"차량 표본 행: {d['vehicle_rows']}, 기록기-재집계 불일치: {d['recorder_vs_rebin_mismatches']}")
    print(f"link 74 세그먼트 귀속: {d['link74_segment_counts']}")
    print(f"대상 클래스: {d.get('dsd_target_classes')}")
    print(f"S0 근사 구간 [0, {d.get('approach_zone_m')}): {d.get('s0_approach_zone')}")


if __name__ == "__main__":
    main()
