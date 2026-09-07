# -*- coding: utf-8 -*-
"""Ver2 망 무제어(v0) 상태에서 링크별 평균 정지 차량 수로 '큐가 서는 링크' 를 분류한다 — outputs/link_queue_class_h0_20260906.json 의 Ver2 판
(SAT 의 queued_links_json: 큐가 서는 링크만 실측 용량을 쓰고, 안 서는 링크는 기하 용량 그대로).
사용: python derive_link_queue_class_ver2_20260907.py [run] [out_json] [threshold]"""
import io, json, re, sys, glob, datetime
from pathlib import Path

R = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RUN = sys.argv[1] if len(sys.argv) > 1 else "v0_nocontrol_ver2_x18_20260907"
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else R / "outputs/link_queue_class_v0_ver2_20260907.json"
TH = float(sys.argv[3]) if len(sys.argv) > 3 else 6.0


def main():
    D = R / "evaluation/runs" / RUN / ("decisions_%s" % RUN)
    files = sorted(glob.glob(str(D / "state_*.json")), key=lambda p: int(re.search(r"(\d+)\.json", p).group(1)))
    files = [p for p in files if int(re.search(r"(\d+)\.json", p).group(1)) >= 900]
    if not files:
        raise SystemExit("state 파일이 없다: %s" % D)
    acc_stop = {}; acc_cnt = {}; n = 0
    for p in files:
        j = json.load(io.open(p, encoding="utf-8")); lo = j.get("local_observation") or {}
        st = lo.get("link_stopped_counts") or {}; lc = lo.get("link_counts") or {}
        for k, v in st.items():
            acc_stop[k] = acc_stop.get(k, 0.0) + float(v or 0)
        for k, v in lc.items():
            acc_cnt[k] = acc_cnt.get(k, 0.0) + float(v or 0)
        n += 1
    mean_stop = {k: round(v / n, 3) for k, v in acc_stop.items()}
    mean_cnt = {k: round(v / n, 3) for k, v in acc_cnt.items()}
    queued = sorted([k for k, v in mean_stop.items() if v >= TH], key=lambda x: int(x) if x.isdigit() else 10**12)
    out = {"schema": "link_queue_class_v1", "generated": datetime.date.today().isoformat(), "source_run": RUN,
           "definition": "t>=900 상태의 link_stopped_counts 평균 >= threshold 인 링크 = 큐가 서는 링크(SAT 실측 용량 적용 대상). 나머지는 기하 용량(unqueued_geometric_frac).",
           "threshold_stopped_mean": TH, "mean_stopped": mean_stop, "mean_count": mean_cnt, "queued_links": queued}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
    print("링크 %d · 큐 링크 %d (임계 %.0f) → %s" % (len(mean_stop), len(queued), TH, OUT))
    print("  큐 링크 상위:", sorted(((mean_stop[k], k) for k in queued), reverse=True)[:12])


if __name__ == "__main__":
    main()
