# -*- coding: utf-8 -*-
"""`*_out` 모델 링크의 저류 용량을 Ver2 망에서 실측한다 (2026-09-09).

왜. 정본 저류 산출물 `urban_storage_capacity_core17legs4b_20260819.json` 은 링크 80개를 담는데
**`*_out` 링크가 하나도 없다.** 그래서 config 의 `urban_link_storage_veh` 에서 out 링크 33개가
전부 **220.0** 이다 — vendor toy 망 기본 스칼라(`grid_link_storage_veh`)다.

문제가 되는 자리. `SC1001_W_out`(물리 링크 31 계열)과 `SC1004_W_out`(링크 68 계열)은 sink 가
아니라 **on-ramp 로 가는 모든 차량이 지나는 회랑**이고, B0(leg_split·offramp_direct·경계분할) ·
B5(gate_onramp_queue) · SPILL(스필백 관측·가드) · SAT3(경계 kind 포화유량)가 전부 여기서 돈다.
모형이 220 에서 찬다고 믿으면 스필백을 실제보다 일찍 예측하고 램프 관련 결정이 그쪽으로 편향된다.

그리고 Ver2 는 이 링크들을 **쪼갰다**. 링크 31 은 이제 412 m 짜리 조각이고 원래 회랑은
31 + 124 + 125 다(경로 linkSeq 로 확인). 그래서 out 링크 하나의 저류는 그 조각들의 **합**이어야 한다.

규칙은 정본과 같다: 저류 = Σ(길이[km] × 차로수) × jam_density.
jam_density = 168.18 veh/km/lane (`urban_storage_capacity_jam168_20260815.json`, 정본 산출물이 쓴 값).
검산: SC1001_to_SC1002 = 469.0 veh / 0.9965 km = 470.7 veh/km -> 2.80 차로 x 168.18. 맞는다.

물리 링크 -> 모델 링크는 **실런이 실제로 쓰는** 검지매핑의 `link_to_origins` 를 뒤집어 얻는다
(ver2n21 판이 아니라 `detector_local_mapping_ver2_20260907.json` 이 live 다 — 결정 메타의
`detector_mapping_resolved_path` 로 확인).

사용: python measure_out_link_storage_ver2_20260909.py <out_json>
"""
import collections
import io
import json
import math
import re
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[1]
NET = R / "network/real_world_gaepo_modi/modi_eval_userfix Ver2.inpx"
DM = R / "evaluation/real_world_modi_control_ver2_20260907/detector_local_mapping_ver2_20260907.json"
CFG = R / "evaluation/configs/canon_ver2n21_dlit_20260908.json"
JAM = 168.18
PLACEHOLDER = 220.0


def parse_links(path):
    """link no -> (길이 m, 차로수). 길이는 폴리라인 3D 누적."""
    t = io.open(path, encoding="utf-8", errors="replace").read()
    out = {}
    for m in re.finditer(r'<link\b([^>]*?)>', t):
        attrs = m.group(1)
        no = re.search(r'\bno="(\d+)"', attrs)
        if not no:
            continue
        # 이 link 요소의 본문 = 다음 </link> 까지
        s = m.end()
        e = t.find("</link>", s)
        body = t[s:e] if e > 0 else ""
        pts = re.findall(r'<linkPolyPoint x="([-\d.eE]+)" y="([-\d.eE]+)"(?: zOffset="([-\d.eE]+)")?', body)
        length = 0.0
        for a, b in zip(pts, pts[1:]):
            dx = float(b[0]) - float(a[0])
            dy = float(b[1]) - float(a[1])
            dz = float(b[2] or 0.0) - float(a[2] or 0.0)
            length += math.sqrt(dx * dx + dy * dy + dz * dz)
        lanes = len(re.findall(r'<lane\b', body))
        out[no.group(1)] = (length, lanes)
    return out


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    outj = sys.argv[1] if len(sys.argv) > 1 else "outputs/out_link_storage_ver2_20260909.json"

    links = parse_links(NET)
    dm = json.load(io.open(DM, encoding="utf-8"))
    l2o = dm.get("link_to_origins") or {}
    cfg = json.load(io.open(CFG, encoding="utf-8"))
    cur = cfg["config_overrides"]["network"]["urban_link_storage_veh"]

    # origin -> [물리 링크]. 한 링크가 여러 origin 을 물면 균등 분할한다(그 사실을 기록).
    by_origin = collections.defaultdict(list)
    multi = collections.Counter()
    for lk, origins in l2o.items():
        if not isinstance(origins, list):
            origins = [origins]
        for o in origins:
            by_origin[str(o)].append((str(lk), 1.0 / len(origins)))
            if len(origins) > 1:
                multi[str(lk)] = len(origins)

    targets = sorted(k for k in cur if k.endswith("_out"))
    print("*_out 모델 링크 %d개 (현재 전부 %.0f 폴백인지 확인)" % (len(targets), PLACEHOLDER))
    print("\n%-18s %8s %10s %8s %10s %10s   %s"
          % ("모델 링크", "물리링크", "길이 m", "차로", "저류 실측", "현재값", "배수"))
    result = {}
    missing = []
    for name in targets:
        phys = by_origin.get(name, [])
        if not phys:
            missing.append(name)
            continue
        tot_len = 0.0
        veh = 0.0
        lane_desc = []
        for lk, w in sorted(phys):
            if lk not in links:
                continue
            L, n = links[lk]
            tot_len += L * w
            veh += (L / 1000.0) * n * JAM * w
            lane_desc.append("%s:%.0fm×%d" % (lk, L, n))
        if veh <= 0:
            missing.append(name)
            continue
        old = float(cur.get(name, 0.0))
        result[name] = {"storage_veh": round(veh, 1), "length_m": round(tot_len, 1),
                        "physical": lane_desc, "config_value": old}
        print("%-18s %8d %10.1f %8s %10.1f %10.1f   %5.2fx"
              % (name, len(phys), tot_len, "-", veh, old, veh / old if old else float("nan")))
    if missing:
        print("\n물리 링크를 못 찾은 out 링크 %d개: %s" % (len(missing), ", ".join(missing[:12])))
    if multi:
        print("여러 origin 을 무는 링크 %d개 (균등 분할함)" % len(multi))

    doc = {"schema": "out_link_storage_ver2/1", "generated": "2026-09-09",
           "network": str(NET.name), "detector_mapping": str(DM.name),
           "jam_density_veh_km_lane": JAM,
           "rule": "저류 = Σ(길이[km] × 차로수) × jam_density. 정본 "
                   "urban_storage_capacity_core17legs4b_20260819.json 과 같은 규칙 "
                   "(검산: SC1001_to_SC1002 469.0 veh / 0.9965 km = 2.80 차로 × 168.18).",
           "why": "정본 저류 산출물에 *_out 링크가 하나도 없어 config 에서 33개가 vendor 기본 220.0 으로 "
                  "떨어져 있었다. Ver2 는 이 회랑들을 쪼갰으므로 조각들의 합이어야 한다.",
           "placeholder": PLACEHOLDER,
           "links": result, "missing": missing}
    io.open(outj, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False, indent=1))
    print("\n-> %s  (%d개)" % (outj, len(result)))


if __name__ == "__main__":
    main()
