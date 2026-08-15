"""A/B 두 런의 결정을 대조해 무엇이 달라졌는지 본다."""
import json, io, sys, glob, os
from pathlib import Path
import statistics as st

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
D = Path(r"C:\Users\TRLAB\Desktop\찐찐막\VISSIM\evaluation\runs\warmstart_ab_20260815")


def load(name):
    out = {}
    for f in sorted(glob.glob(str(D / f"decisions_{name}" / "action_*.json"))):
        sec = int(os.path.basename(f)[len("action_"):-len(".json")])
        out[sec] = json.load(open(f, encoding="utf-8"))
    return out


a = load("wsoff_20260815")
b = load("wson900_20260815")
common = sorted(set(a) & set(b))
print(f"공통 결정 {len(common)}건")

# 램프미터
rd = []
for s in common:
    ra = (a[s].get("ramp_metering") or {})
    rb = (b[s].get("ramp_metering") or {})
    for k in sorted(set(ra) | set(rb)):
        va, vb = ra.get(k), rb.get(k)
        if isinstance(va, (int, float)) and isinstance(vb, (int, float)) and abs(va - vb) > 1e-9:
            rd.append((s, k, va, vb))
print(f"\n램프미터 값이 다른 (결정,램프) 쌍: {len(rd)}")
for s, k, va, vb in rd[:8]:
    print(f"  t={s:5d} {k:10s} off={va:8.2f}  on={vb:8.2f}  ({vb-va:+.2f})")

# VSL
vd = 0
for s in common:
    va = json.dumps(a[s].get("vsl") or {}, sort_keys=True)
    vb = json.dumps(b[s].get("vsl") or {}, sort_keys=True)
    if va != vb:
        vd += 1
print(f"\nVSL 이 다른 결정: {vd}/{len(common)}")

# 녹색시간
gd = 0
gdiff = []
for s in common:
    ga = a[s].get("green_times") or {}
    gb = b[s].get("green_times") or {}
    keys = set(ga) | set(gb)
    d = [abs(float(ga.get(k, 0)) - float(gb.get(k, 0))) for k in keys]
    d = [x for x in d if x > 1e-9]
    if d:
        gd += 1
        gdiff.extend(d)
print(f"녹색시간이 다른 결정: {gd}/{len(common)}   차이 중앙값 {st.median(gdiff):.2f}s (n={len(gdiff)})" if gdiff else f"녹색시간이 다른 결정: {gd}")

# 모델이 본 예측 (raw)
print("\n모델 예측 state_summary 비교 (평균):")
for key in ("total_model_vehicles", "urban_total_veh", "freeway_total_veh", "off_ramp_storage_veh", "ramp_queue_total_veh"):
    xa = [float((a[s].get("prediction") or {}).get("state_summary", {}).get(key, "nan")) for s in common]
    xb = [float((b[s].get("prediction") or {}).get("state_summary", {}).get(key, "nan")) for s in common]
    xa = [v for v in xa if v == v]
    xb = [v for v in xb if v == v]
    if xa and xb:
        print(f"  {key:28s} off={st.mean(xa):9.2f}  on={st.mean(xb):9.2f}  ({st.mean(xb)-st.mean(xa):+.2f})")
