# G6 매트릭스 요약 JSON 을 보고서용 마크다운 표로 굽는다.
from __future__ import annotations

import argparse
import json
from pathlib import Path

ORDER = ["fdA", "fdC", "fdA_cd", "fdC_cd"]
LABEL = {
    "fdA": "A 현행 (119.505/16.354/2.154, q_cap 4914, phi=1)",
    "fdC": "C 자유분지 (122.562/21.419/1.724, q_cap 6956, phi=1)",
    "fdA_cd": "A + capacity drop (phi=0.6)",
    "fdC_cd": "C + capacity drop (phi=0.6)",
}


def fmt(x, digits=3):
    if x is None:
        return "n/a"
    return f"{x:.{digits}f}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--ranking", type=Path)
    args = parser.parse_args()
    data = json.loads(args.summary.read_text(encoding="utf-8"))
    tags = [t for t in ORDER if t in data] + [t for t in data if t not in ORDER]

    print("### 구성 x 호라이즌 G6 지표\n")
    print("| FD 구성 | H | decisions | Spearman rho | top-action pairwise | spillback F1 | G6 초기 | G6 승격 |")
    print("|---|---|---|---|---|---|---|---|")
    for tag in tags:
        block = data[tag]
        for h in ("1", "3", "5"):
            if h not in block["by_horizon"]:
                continue
            d = block["by_horizon"][h]
            print(f"| {LABEL.get(tag, tag)} | {h} | {d['decision_count']} | {fmt(d['spearman_rho'])} | "
                  f"{fmt(d['pairwise'])} | {fmt(d['spillback_f1'])} | {d['g6_initial']} | {d['g6_release']} |")
        d = block["all"]
        print(f"| **{tag} 전체** | 1+3+5 | {d['decision_count']} | **{fmt(d['spearman_rho'])}** | "
              f"**{fmt(d['pairwise'])}** | **{fmt(d['spillback_f1'])}** | **{d['g6_initial']}** | **{d['g6_release']}** |")

    print("\n### 셀그룹 x 호라이즌 (Spearman rho / pairwise)\n")
    groups = sorted({g for t in tags for g in data[t].get("by_group_horizon", {})})
    print("| FD 구성 | 셀그룹 | H=1 | H=3 | H=5 |")
    print("|---|---|---|---|---|")
    for tag in tags:
        for g in groups:
            blk = data[tag].get("by_group_horizon", {}).get(g, {})
            if not blk:
                continue
            cells = []
            for h in ("1", "3", "5"):
                d = blk.get(h)
                cells.append("n/a" if not d else f"{fmt(d['spearman_rho'])} / {fmt(d['pairwise'])}")
            print(f"| {tag} | {g} | " + " | ".join(cells) + " |")

    if args.ranking and args.ranking.exists():
        rank = json.loads(args.ranking.read_text(encoding="utf-8"))
        print("\n### 축별 부분순위 Spearman (anchor 포함)\n")
        axes = sorted({a for t in rank for a in rank[t]["axis_rho_mean"]})
        print("| FD 구성 | " + " | ".join(axes) + " |")
        print("|---|" + "---|" * len(axes))
        for tag in tags:
            if tag not in rank:
                continue
            row = rank[tag]["axis_rho_mean"]
            print(f"| {tag} | " + " | ".join(fmt(row.get(a)) for a in axes) + " |")

        print("\n### 가장 자주 뒤집히는 후보쌍\n")
        for tag in tags:
            if tag not in rank:
                continue
            print(f"\n**{tag}**\n")
            print("| 후보쌍 | 뒤집힌 decision 수 |")
            print("|---|---|")
            for item in rank[tag]["most_discordant_pairs"][:10]:
                print(f"| {item['pair'][0]} vs {item['pair'][1]} | {item['count']} |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
