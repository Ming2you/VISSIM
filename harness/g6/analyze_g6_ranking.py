# G6 순위 진단 — 어느 액션 쌍이 어느 상태에서 뒤집히는지, 축별로 어디서 무너지는지 분해한다.
"""집계 지표(전체 Spearman/pairwise)는 "통과/실패"만 말한다. 이 스크립트는 그 다음 질문에 답한다.

  1. 축별 순위 — vsl / ramp / green / offset 각 축을 anchor 와 함께 잘라 축 내부 Spearman 을 낸다.
     계약이 4축 perturbation 을 요구한 이유가 여기다. 전체 ρ 가 높아도 특정 축만 뒤집힐 수 있다.
  2. 불일치 쌍 — 모든 후보쌍 (i,j) 중 sign(J_model_i - J_model_j) != sign(J_vissim_i - J_vissim_j)
     인 쌍을 크기순으로 나열한다. "어떤 액션 쌍이 어떤 상태에서" 에 직접 답한다.
  3. 아핀 편향 흡수 검정 — J_vissim ~ alpha*J_model + beta 최소자승 적합의 R^2 와 잔차.
     사용자 가설("유량 편향이 액션 무관 상수면 순위는 보존된다")이 실제로 성립하는지 본다.
  4. 축별 신호 대 잡음 — 모델/관측 각각의 축 내부 목적함수 폭(range)을 셀 간 산포와 비교한다.
     폭이 산포보다 작으면 그 축의 순위는 원리적으로 측정 불가다.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
import g6_core as core  # noqa: E402
import g6_records as rec  # noqa: E402

AXIS_OF = {c.candidate_id: c.axis for c in core.ACTIVE_CANDIDATE_SET}
ANCHOR = "c00_anchor"


def load_rows(matrix_dir: Path, config: str) -> list[dict]:
    out = []
    for group_dir in sorted((matrix_dir / config).iterdir()):
        rows_path = group_dir / "g6_candidate_rows.json"
        if not rows_path.is_dir() and rows_path.exists():
            for row in json.loads(rows_path.read_text(encoding="utf-8")):
                row["group"] = group_dir.name
                row["key"] = f"{group_dir.name}__{row['decision_id']}"
                out.append(row)
    return out


def group_by_decision(rows: list[dict]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for row in rows:
        out.setdefault(row["key"], []).append(row)
    return out


def _linfit(xs: list[float], ys: list[float]) -> tuple[float, float, float]:
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    syy = sum((y - my) ** 2 for y in ys)
    if sxx <= 0.0 or syy <= 0.0:
        return float("nan"), float("nan"), float("nan")
    alpha = sxy / sxx
    beta = my - alpha * mx
    r2 = (sxy * sxy) / (sxx * syy)
    return alpha, beta, r2


def analyze(rows: list[dict]) -> dict:
    decisions = group_by_decision(rows)
    per_decision = []
    discordant_tally: dict[tuple[str, str], int] = {}
    axis_rhos: dict[str, list[float]] = {}

    for key, items in sorted(decisions.items()):
        items = [i for i in items if i.get("vissim_objective") is not None]
        if len(items) < 2:
            continue
        ids = [i["candidate_id"] for i in items]
        m = [float(i["model_objective"]) for i in items]
        v = [float(i["vissim_objective"]) for i in items]
        rho = rec.spearman_rank_correlation(m, v)
        alpha, beta, r2 = _linfit(m, v)

        # 축별 부분순위 (anchor 포함)
        axis_block = {}
        for axis in ("vsl", "ramp", "green", "offset", "combined"):
            sel = [k for k, cid in enumerate(ids) if AXIS_OF.get(cid) in (axis, "anchor")]
            if len(sel) < 3:
                continue
            am = [m[k] for k in sel]
            av = [v[k] for k in sel]
            arho = rec.spearman_rank_correlation(am, av)
            axis_block[axis] = {
                "n": len(sel),
                "rho": arho,
                "model_range": max(am) - min(am),
                "model_range_rel": (max(am) - min(am)) / max(abs(sum(am) / len(am)), 1e-9),
                "vissim_range": max(av) - min(av),
                "vissim_range_rel": (max(av) - min(av)) / max(abs(sum(av) / len(av)), 1e-9),
            }
            if arho is not None:
                axis_rhos.setdefault(axis, []).append(arho)

        # 불일치 쌍
        flips = []
        for a in range(len(ids)):
            for b in range(a + 1, len(ids)):
                dm = m[a] - m[b]
                dv = v[a] - v[b]
                if dm == 0.0 or dv == 0.0:
                    continue
                if (dm > 0) != (dv > 0):
                    flips.append({
                        "pair": [ids[a], ids[b]],
                        "axes": [AXIS_OF.get(ids[a]), AXIS_OF.get(ids[b])],
                        "model_delta": dm,
                        "vissim_delta": dv,
                        "severity": min(abs(dm), abs(dv)),
                    })
                    pk = tuple(sorted((ids[a], ids[b])))
                    discordant_tally[pk] = discordant_tally.get(pk, 0) + 1
        flips.sort(key=lambda f: -f["severity"])

        # 최적 후보 비교
        best_model = min(zip(ids, m), key=lambda t: (t[1], t[0]))[0]
        best_vissim = min(zip(ids, v), key=lambda t: (t[1], t[0]))[0]

        # anchor 대비 효과 크기 — 모델이 각 액션의 이득/손해를 얼마나 크게 보는가.
        # 순위 뒤집힘의 원인을 "부호가 틀렸다" 와 "크기만 틀렸다" 로 가른다.
        deltas = {}
        if ANCHOR in ids:
            ia = ids.index(ANCHOR)
            for k, cid in enumerate(ids):
                if cid == ANCHOR:
                    continue
                deltas[cid] = {
                    "axis": AXIS_OF.get(cid),
                    "model_delta": m[k] - m[ia],
                    "vissim_delta": v[k] - v[ia],
                    "sign_agree": (m[k] - m[ia] > 0) == (v[k] - v[ia] > 0)
                    if (m[k] - m[ia]) != 0 and (v[k] - v[ia]) != 0 else None,
                    "gain_ratio": ((m[k] - m[ia]) / (v[k] - v[ia]))
                    if (v[k] - v[ia]) != 0 else None,
                }

        per_decision.append({
            "anchor_deltas": deltas,
            "key": key,
            "n": len(ids),
            "rho": rho,
            "affine": {"alpha": alpha, "beta": beta, "r2": r2},
            "best_model": best_model,
            "best_vissim": best_vissim,
            "best_match": best_model == best_vissim,
            "model_rank": [c for c, _ in sorted(zip(ids, m), key=lambda t: t[1])],
            "vissim_rank": [c for c, _ in sorted(zip(ids, v), key=lambda t: t[1])],
            "flip_count": len(flips),
            "pair_count": len(ids) * (len(ids) - 1) // 2,
            "top_flips": flips[:8],
            "axis": axis_block,
        })

    return {
        "per_decision": per_decision,
        "axis_rho_mean": {
            a: (sum(v) / len(v) if v else None) for a, v in sorted(axis_rhos.items())
        },
        "axis_rho_values": {a: v for a, v in sorted(axis_rhos.items())},
        "most_discordant_pairs": sorted(
            ({"pair": list(k), "count": c} for k, c in discordant_tally.items()),
            key=lambda d: -d["count"],
        )[:20],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix-dir", type=Path, required=True)
    parser.add_argument("--configs", default="fdA,fdC,fdA_cd,fdC_cd")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    result = {}
    for config in [c.strip() for c in args.configs.split(",") if c.strip()]:
        if not (args.matrix_dir / config).exists():
            continue
        rows = load_rows(args.matrix_dir, config)
        if not rows:
            continue
        result[config] = analyze(rows)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OUT={args.out}")
    for config, block in result.items():
        print(f"\n== {config}  axis rho mean: " + ", ".join(
            f"{a}={('%.3f' % r) if r is not None else 'None'}"
            for a, r in block["axis_rho_mean"].items()))
        for d in block["per_decision"]:
            rho = d["rho"]
            print(f"  {d['key']:44s} rho={('%+.3f' % rho) if rho is not None else 'None':>7s} "
                  f"flips={d['flip_count']:3d}/{d['pair_count']:3d} "
                  f"r2={d['affine']['r2']:.3f} best m/v={d['best_model']}/{d['best_vissim']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
