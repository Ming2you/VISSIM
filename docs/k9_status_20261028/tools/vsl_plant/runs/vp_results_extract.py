# vp_results_extract.py — VP_RESULTS 용 읽기 전용 모음 (데이터 뒤, 2026-10-27 KST)
# 입력: 고정 표 도구 출력 두 개(vp_tables_qv3r3.json, vp_tables_p1r3.json). 쓰기는 출력 JSON 하나뿐.
# 계산: (1) P1 9상태(VSL 끔) 기준 굴림의 구역·셀 편향(B1·D·셀 11–13 포함; 표 도구는 m1–m5 만 표로 냄)
#       (2) AB 12상태: 100 팔 VSL 반응(팔100 − 팔110, w450 구역 속도)과 같은 상태 EXEC 편향의 크기 비
#       (3) AB 12상태: plant FW_E 입구 대기(절대값) 팔별 최댓값
# 판정 없음. 숫자만.
import json, os, statistics as st, sys, hashlib

ROOT = "D:/VISSIM-merge/k8_gate_trees/vsl_plant/out/tables"
F_AB = os.path.join(ROOT, "vp_tables_qv3r3.json")
F_P1 = os.path.join(ROOT, "vp_tables_p1r3.json")
OUT = sys.argv[1]


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def rng(v):
    v = [x for x in v if x is not None]
    if not v:
        return None
    return {"n": len(v), "min": min(v), "max": max(v), "median": st.median(v),
            "n_pos": sum(x > 0 for x in v), "n_neg": sum(x < 0 for x in v)}


ab = json.load(open(F_AB, encoding="utf-8"))
p1 = json.load(open(F_P1, encoding="utf-8"))
out = {"inputs": {"vp_tables_qv3r3.json": sha(F_AB), "vp_tables_p1r3.json": sha(F_P1)},
       "note": "data-after, read-only; e = plant - VISSIM; w450"}

# (1) P1 base biases, all zones + cells 11-13
ZONES = ["U", "B1", "M1", "VSa", "Mu'", "VS0'", "VSb", "B2'", "D"]
rows = []
for s in p1["P1"]["states"]:
    z = s["base"]["w450"]["zones"]
    c = s["base"]["w450"]["cells"]
    r = {"job": s["job"], "T": s["T"]}
    for k in ZONES:
        r[k] = {"e_speed": z[k]["e"]["speed"], "e_stock": z[k]["e"]["stock"],
                "plant_speed": z[k]["plant"]["speed"], "vissim_speed": z[k]["vissim"]["speed"]}
    for cc in ["11", "12", "13", "18"]:
        r["cell" + cc] = {"e_speed": c[cc]["speed"]["e"], "plant": c[cc]["speed"]["plant"],
                          "vissim": c[cc]["speed"]["vissim"]}
    rows.append(r)
out["P1_base_w450_rows"] = rows
summ = {}
for k in ZONES:
    summ[k + "_e_speed"] = rng([r[k]["e_speed"] for r in rows])
    summ[k + "_e_stock"] = rng([r[k]["e_stock"] for r in rows])
    summ[k + "_plant_speed"] = rng([r[k]["plant_speed"] for r in rows])
    summ[k + "_vissim_speed"] = rng([r[k]["vissim_speed"] for r in rows])
for cc in ["11", "12", "13", "18"]:
    summ["cell" + cc + "_e_speed"] = rng([r["cell" + cc]["e_speed"] for r in rows])
out["P1_base_w450_summary"] = summ

# (2) AB: VSL response (arm100 - arm110) vs EXEC bias magnitude, w450 zone speed
RZ = ["M1", "VSa", "VS0'", "VSb"]
resp_rows = []
for s in ab["AB"]["states"]:
    a100 = s["arms"]["100"]["zones"]["w450"]
    ex = s["B_exec"]["w450"]["zones"]
    r = {"job": s["job"], "T": s["T"]}
    for k in RZ:
        d = a100.get(k, {})
        resp = None
        if isinstance(d, dict):
            for key in ("d_speed", "speed"):
                if key in d and not isinstance(d[key], dict):
                    resp = d[key]
                    break
        r[k] = {"resp100_speed": resp, "exec_bias_speed": ex[k]["e"]["speed"]}
    resp_rows.append(r)
out["AB_resp_vs_bias_rows"] = resp_rows
rs = {}
for k in RZ:
    resp = [abs(r[k]["resp100_speed"]) for r in resp_rows if r[k]["resp100_speed"] is not None]
    bias = [abs(r[k]["exec_bias_speed"]) for r in resp_rows]
    rs[k] = {"abs_resp100": rng(resp), "abs_exec_bias": rng(bias)}
out["AB_resp_vs_bias_summary"] = rs
out["AB_arm100_zone_w450_keys_example"] = sorted(list(ab["AB"]["states"][0]["arms"]["100"]["zones"]["w450"].get("M1", {}).keys()))

# (3) AB: plant FW_E origin queue absolute, per arm
oq = {}
for s in ab["AB"]["states"]:
    for arm, a in s["arms"].items():
        oq.setdefault(arm, []).append(a.get("origin_queue_veh_h"))
out["AB_origin_queue_veh_h_by_arm"] = {k: rng(v) for k, v in oq.items()}

# (4) AB: where the arm cost goes — zone veh·h difference (arm - 110), w450, arms 100 and 90
ZD = ["U", "B1", "M1", "VSa", "VS0'", "VSb", "D"]
dv = {}
for arm in ("100", "90"):
    per_zone = {k: [] for k in ZD}
    for s in ab["AB"]["states"]:
        zz = s["arms"][arm]["zones"]["w450"]
        for k in ZD:
            per_zone[k].append(zz.get(k, {}).get("d_veh_h"))
    dv[arm] = {k: rng(v) for k, v in per_zone.items()}
out["AB_arm_zone_d_veh_h_w450"] = dv

tmp = OUT + ".tmp.%d" % os.getpid()
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1, sort_keys=True)
os.replace(tmp, OUT)
print(json.dumps({"P1": summ, "AB_resp": rs, "AB_oq": out["AB_origin_queue_veh_h_by_arm"],
                  "keys": out["AB_arm100_zone_w450_keys_example"]}, ensure_ascii=False, indent=0)[:6000])
