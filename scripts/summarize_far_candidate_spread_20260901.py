# -*- coding: utf-8 -*-
"""probe_far_candidate_spread 산출을 표로 — 항별 후보간 스프레드와 레버 귀속."""
import glob
import json
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent


def spread(vals):
    return (max(vals) - min(vals)) if vals else 0.0


def main():
    pats = sys.argv[1:] or [str(R / "outputs/far_candidate_spread_*.json")]
    files = []
    for p in pats:
        files.extend(sorted(glob.glob(p)))
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("%-6s %4s %10s %10s %10s %10s | %9s %9s %9s %9s | %8s %8s %8s" % (
        "sec", "n", "far_mean", "urban_lv", "main_lv", "ramp_lv",
        "far_sp", "urban_sp", "main_sp", "ramp_sp",
        "u/far%", "u/ramp%", "n_u_sp"))
    for f in files:
        d = json.load(open(f, encoding="utf-8"))
        rows = [r for r in d["far_calls"] if not (r.get("ctx") or {}).get("sweep")]
        if not rows:
            continue
        far = [r["far_true"] for r in rows]
        u = [r["urban"] for r in rows]
        m = [r["main"] for r in rows]
        rm = [r["ramp"] for r in rows]
        nu = [r["n_u"] for r in rows]
        mean_far = sum(far) / len(far)
        print("%-6d %4d %10.2f %10.2f %10.2f %10.2f | %9.3f %9.3f %9.3f %9.3f | %8.4f %8.2f %8.3f" % (
            d["sim_sec"], len(rows), mean_far,
            sum(u) / len(u), sum(m) / len(m), sum(rm) / len(rm),
            spread(far), spread(u), spread(m), spread(rm),
            100.0 * spread(u) / max(mean_far, 1e-9),
            100.0 * spread(u) / max(spread(rm), 1e-9),
            spread(nu)))
    print()
    for f in files:
        d = json.load(open(f, encoding="utf-8"))
        if not d.get("sweep"):
            continue
        print("--- sim_sec %d  레버 교차 스왑(base=목적값 최소 후보, alt=최대) ---" % d["sim_sec"])
        base = next((s for s in d["sweep"] if s["tag"] == "base"), None)
        cands = {c["index"]: c for c in d["candidates"]}
        ordered = sorted(d["candidates"], key=lambda r: r["objective"])
        bi, ai = ordered[0]["index"], ordered[-1]["index"]
        print("    base=cand%d (N_P*=%.1f N_UF*=%.1f)  alt=cand%d (N_P*=%.1f N_UF*=%.1f)" % (
            bi, cands[bi]["cand_N_P_star"], cands[bi]["cand_N_UF_star"],
            ai, cands[ai]["cand_N_P_star"], cands[ai]["cand_N_UF_star"]))
        for fam in ("green_times", "ramp_metering", "vsl", "offsets", "inflow_outflow_allocation"):
            b = cands[bi]["control"].get(fam, {})
            a = cands[ai]["control"].get(fam, {})
            keys = sorted(set(b) | set(a))
            l1 = sum(abs(b.get(k, 0.0) - a.get(k, 0.0)) for k in keys)
            nd = sum(1 for k in keys if abs(b.get(k, 0.0) - a.get(k, 0.0)) > 1e-9)
            print("    %-26s L1=%10.3f  다른키 %d/%d" % (fam, l1, nd, len(keys)))
        print("    %-26s %10s %10s %10s %10s %10s" % ("변형", "far", "urban", "main", "ramp", "n_u"))
        for s in d["sweep"]:
            print("    %-26s %10.3f %10.3f %10.3f %10.3f %10.3f" % (
                s["tag"], s["far"], s["urban"], s["main"], s["ramp"], s["n_u"]))
        if base:
            print("    %-26s %10s %10s %10s %10s %10s" % ("Δ vs base", "", "", "", "", ""))
            for s in d["sweep"]:
                if s["tag"] == "base":
                    continue
                print("    %-26s %+10.4f %+10.4f %+10.4f %+10.4f %+10.4f" % (
                    s["tag"], s["far"] - base["far"], s["urban"] - base["urban"],
                    s["main"] - base["main"], s["ramp"] - base["ramp"],
                    s["n_u"] - base["n_u"]))
        print()
    for f in files:
        d = json.load(open(f, encoding="utf-8"))
        print("--- sim_sec %d  후보별 ---" % d["sim_sec"])
        print("    %-5s %-14s %9s %9s %12s %10s %10s %10s %10s" % (
            "idx", "stage", "N_P*", "N_UF*", "objective", "far", "urban", "main", "ramp"))
        calls = d["far_calls"]
        for c in d["candidates"]:
            fc = c["far_calls"]
            r = calls[fc[0]] if fc else {}
            print("    %-5d %-14s %9.1f %9.1f %12.4f %10.3f %10.3f %10.3f %10.3f" % (
                c["index"], c["stage"], c["cand_N_P_star"], c["cand_N_UF_star"], c["objective"],
                r.get("far_true", 0.0), r.get("urban", 0.0), r.get("main", 0.0), r.get("ramp", 0.0)))
        objs = [c["objective"] for c in d["candidates"]]
        if len(objs) >= 2:
            s = sorted(objs)
            print("    목적값 스프레드 %.4f · 1위-2위 간격 %.4f" % (max(objs) - min(objs), s[1] - s[0]))
        # 항 제거 반사실: 그 항이 없었으면 argmin 이 바뀌나
        calls = d["far_calls"]
        rows = [(c, calls[c["far_calls"][0]]) for c in d["candidates"] if c["far_calls"]]
        if len(rows) >= 2:
            win = min(rows, key=lambda t: t[0]["objective"])[0]["index"]
            for term in ("urban", "main", "ramp", "far_true"):
                alt_win = min(rows, key=lambda t: t[0]["objective"] - t[1][term])[0]["index"]
                margin = sorted(t[0]["objective"] - t[1][term] for t in rows)
                print("    %-9s 제거 → 승자 cand%-3d (%s) · 새 1-2위 간격 %.4f" % (
                    term, alt_win, "동일" if alt_win == win else "**뒤집힘**",
                    margin[1] - margin[0]))
        print()


if __name__ == "__main__":
    main()
