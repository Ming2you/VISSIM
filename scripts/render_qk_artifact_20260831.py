# -*- coding: utf-8 -*-
"""q-k 기본도(fundamental diagram)를 그린다 — 플랜트 곡선 · VISSIM 관측 · 수요 작동점.

왜 (2026-08-31).

오늘 하루의 이야기가 이 한 장에 다 들어간다.

    플랜트 곡선   재적합 FD (v_free 120.0 · rho_crit 27.0 · a 1.6) -> q = rho * V(rho)
                  용량점 (27.0, 1734 veh/h/lane) · 4차로 6,938 veh/h
    VISSIM 관측   무제어 14런 6,944점 (수요 x1.0 ~ x2.4). 컨트롤러 간섭 없는 순수 플랜트 거동
    수요 작동점    .inpx 본선 구간유량 / 4차로 — **첨두가 용량의 67% 다**

그래서 x1.0 에서 고속도로 레버가 잠긴다. 본선 수요가 용량 근처에 못 가므로
`density_ratio <= metering_activation_density_ratio` 가 매 결정 참이고, VSL 은 전 결정 120.0 이며
density_stress 가 0.0000 이다. 그 사실을 TTT 표로 보면 "freeway 가 -2~-5 밖에 안 움직인다" 인데,
여기서 보면 작동점이 곡선의 왼쪽 자락에 붙어 있는 것이다.

산출: HTML (Artifact 로 발행)
"""
import argparse
import io
import json
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent

HEAD = """<title>q–k 기본도</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=Newsreader:opsz,wght@6..72,400;6..72,600;6..72,700&family=Work+Sans:wght@400;500;600&display=swap">
<style>
:root{
  --ground:#F0EEEA; --surface:#FFFFFF; --surface-2:#F7F5F2;
  --ink:#1A1A19; --ink-2:#4A4A47; --muted:#7C7B75;
  --line:#D7D4CE; --line-soft:#E7E4DF;
  --curve:#14524B; --curve-soft:#D6E5E2;
  --cap:#A8451C;
  --grid:#E2DFD9;
  --shadow:0 1px 2px rgba(26,26,25,.06),0 12px 30px -18px rgba(26,26,25,.3);
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --ground:#12130F; --surface:#1B1D18; --surface-2:#202219;
  --ink:#EDEBE4; --ink-2:#BCBAB1; --muted:#8B8A81;
  --line:#2E3129; --line-soft:#24271F;
  --curve:#67C7B6; --curve-soft:#16302C;
  --cap:#E08A5F; --grid:#282B23;
  --shadow:0 1px 2px rgba(0,0,0,.5),0 12px 30px -18px rgba(0,0,0,.8);
}}
:root[data-theme="dark"]{
  --ground:#12130F; --surface:#1B1D18; --surface-2:#202219;
  --ink:#EDEBE4; --ink-2:#BCBAB1; --muted:#8B8A81;
  --line:#2E3129; --line-soft:#24271F;
  --curve:#67C7B6; --curve-soft:#16302C;
  --cap:#E08A5F; --grid:#282B23;
  --shadow:0 1px 2px rgba(0,0,0,.5),0 12px 30px -18px rgba(0,0,0,.8);
}
*{box-sizing:border-box}
body{margin:0;background:var(--ground);color:var(--ink);
  font-family:"Work Sans",system-ui,sans-serif;font-size:15px;line-height:1.62;
  -webkit-font-smoothing:antialiased}
.wrap{max-width:1080px;margin:0 auto;padding:46px 26px 74px}
.mono{font-family:"IBM Plex Mono",monospace;font-variant-numeric:tabular-nums}
.eyebrow{font-family:"IBM Plex Mono",monospace;font-size:11px;letter-spacing:.17em;
  text-transform:uppercase;color:var(--curve);font-weight:600;margin:0 0 14px}
h1{font-family:Newsreader,Georgia,serif;font-weight:700;font-size:clamp(36px,5.4vw,54px);
  line-height:1.02;letter-spacing:-.012em;margin:0 0 16px;text-wrap:balance}
.lede{font-size:17px;color:var(--ink-2);margin:0;max-width:60ch}
.lede b{color:var(--ink);font-weight:600}
hr.r{border:0;border-top:1px solid var(--line);margin:38px 0}
h2{font-family:Newsreader,Georgia,serif;font-weight:600;font-size:26px;margin:0 0 5px;
  letter-spacing:-.006em}
.sub{color:var(--muted);font-size:13.5px;margin:0 0 20px;max-width:72ch}
.card{background:var(--surface);border:1px solid var(--line);border-radius:5px;
  padding:22px;box-shadow:var(--shadow);margin-bottom:20px}
.scroller{overflow-x:auto}
svg{display:block;max-width:100%;height:auto}
.legend{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-top:16px;
  font-family:"IBM Plex Mono",monospace;font-size:11px;color:var(--muted)}
.chip{display:inline-flex;align-items:center;gap:5px;padding:2px 7px;border-radius:3px;
  background:var(--surface-2);border:1px solid var(--line-soft)}
.dot{width:9px;height:9px;border-radius:50%}
table{width:100%;border-collapse:collapse;font-size:13.5px}
th{font-family:"IBM Plex Mono",monospace;font-size:10.5px;letter-spacing:.1em;
  text-transform:uppercase;color:var(--muted);text-align:right;font-weight:500;
  padding:0 9px 8px;border-bottom:1px solid var(--line)}
th:first-child{text-align:left}
td{padding:8px 9px;border-bottom:1px solid var(--line-soft);text-align:right;
  font-family:"IBM Plex Mono",monospace;font-variant-numeric:tabular-nums}
td:first-child{text-align:left;font-family:"Work Sans",sans-serif}
tr:last-child td{border-bottom:0}
.hi{color:var(--cap);font-weight:600}
.note{margin-top:32px;padding:20px 22px;border:1px solid var(--line);
  border-left:3px solid var(--curve);border-radius:0 5px 5px 0;background:var(--surface)}
.note h3{font-family:Newsreader,Georgia,serif;font-size:19px;font-weight:600;margin:0 0 10px}
.note p{margin:0 0 9px;font-size:13.5px;color:var(--ink-2);line-height:1.65}
.note p:last-child{margin-bottom:0}
code{font-family:"IBM Plex Mono",monospace;font-size:12.5px;background:var(--surface-2);
  padding:1px 5px;border-radius:3px}
@media (max-width:600px){.wrap{padding:32px 15px 56px}}
</style>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="outputs/qk_plot_data_20260831.json")
    ap.add_argument("--numsim", default="outputs/numsim_qk_20260831.json")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    d = json.loads((R / args.data).read_text(encoding="utf-8"))
    fd, curve, vissim = d["fd"], d["curve"], d["vissim"]
    mb, isec = d["demand_mainline_vph"], d["interval_sec"]
    lanes = fd["lanes"]

    ns = []
    p = R / args.numsim
    if p.is_file():
        try:
            nj = json.loads(p.read_text(encoding="utf-8"))
            for run in nj.get("runs", []):
                pts = []
                for row in run.get("rows", []):
                    for s in row.get("segments", []):
                        r_, v_ = float(s["rho"]), float(s["v"])
                        if r_ > 0.05:
                            pts.append([round(r_, 2), round(r_ * v_, 1)])
                if pts:
                    ns.append({"label": run["label"], "points": pts[:900]})
        except Exception as e:
            print("numsim 읽기 실패: %s" % e)

    # 관측 요약표
    tbl = []
    for s in vissim:
        qs = sorted(x[1] for x in s["points"])
        ks = sorted(x[0] for x in s["points"])
        n = len(qs)
        tbl.append({"demand": s["demand"], "n": n,
                    "k_med": ks[n // 2], "q_med": qs[n // 2],
                    "q_p95": qs[int(n * 0.95) - 1],
                    "pct": 100.0 * qs[int(n * 0.95) - 1] / fd["capacity_q_per_lane"]})

    payload = {"fd": fd, "curve": curve, "vissim": vissim, "numsim": ns,
               "demand": [{"i": i, "vph": v, "per_lane": v / lanes,
                           "pct": 100.0 * (v / lanes) / fd["capacity_q_per_lane"],
                           "t0": i * isec, "t1": (i + 1) * isec} for i, v in enumerate(mb)],
               "table": tbl}

    body = """
<div class="wrap">
  <p class="eyebrow">무제어 14런 6,944점 · 재적합 FD · .inpx 수요</p>
  <h1>q–k 기본도</h1>
  <p class="lede">
    플랜트의 평형 곡선 위에 VISSIM 실측과 본선 수요 작동점을 겹쳤다.
    <b>수요 첨두가 용량의 67%</b> 라 작동점이 곡선 왼쪽 자락을 벗어나지 못한다 —
    고속도로 레버가 잠기는 이유가 여기 보인다.
  </p>

  <hr class="r">

  <div class="card">
    <div class="scroller"><svg id="plot" viewBox="0 0 980 560" role="img"
      aria-label="유량-밀도 기본도"></svg></div>
    <div class="legend" id="legend"></div>
  </div>

  <div class="note">
    <h3>이 그림이 말하는 것</h3>
    <p>
      곡선은 재적합 FD <code>V(ρ)=120.0·exp(−(1/1.6)(ρ/27.0)^1.6)</code> 에서
      <code>q=ρ·V(ρ)</code> 로 얻은 것이다. 정점이 <b>(27.0, 1,734 veh/h/lane)</b> 이고
      4차로로 <b>6,938 veh/h</b> 다.
    </p>
    <p>
      회색 띠가 <code>.inpx</code> 본선 수요다 — 구간별 550~1,155 veh/h/lane 이고
      <b>첨두조차 용량의 67%</b> 다. 램프가 더해져도 관측 유량 중앙이 x1.0 에서 881,
      x2.2 에서 1,561 veh/h/lane 이다.
    </p>
    <p>
      점은 무제어 실측이고 색이 수요 배율이다. x1.0 은 밀도 8.35 로 <b>임계의 31%</b> 자리에
      뭉쳐 있다. 수요를 x2.2 까지 올려야 정점 근처로 올라오고, 그때 비로소
      <code>density_stress</code> 가 0 을 벗어난다.
    </p>
  </div>

  <hr class="r">

  <h2>수요 배율별 작동점</h2>
  <p class="sub">유량 p95 가 적합 용량을 넘는 구간이 있다 — 램프 합류분이 본선 수요 위에 얹히기 때문이다.</p>
  <div class="card">
    <table><thead><tr>
      <th>수요</th><th>표본</th><th>밀도 중앙</th><th>유량 중앙</th><th>유량 p95</th><th>용량 대비 p95</th>
    </tr></thead><tbody id="tbl"></tbody></table>
  </div>

  <div class="note">
    <h3>본선 수요 구간</h3>
    <p><code>.inpx</code> 의 <code>vehicleInput</code> 구간유량(link 26 · 74 각각)을 4차로로 나눈 값이다.</p>
    <div class="scroller"><table><thead><tr>
      <th>구간</th><th>veh/h</th><th>veh/h/lane</th><th>용량 대비</th>
    </tr></thead><tbody id="dtbl"></tbody></table></div>
  </div>
</div>
"""

    script = """
<script>
const D = %s;
const W=980,H=560,L=76,Rr=22,T=26,B=54;
const KMAX=68, QMAX=2050;
const sx=k=>L+(W-L-Rr)*k/KMAX, sy=q=>H-B-(H-T-B)*q/QMAX;
const RAMP=["#3E5C8A","#4A6E93","#56809A","#6A8C97","#87968C","#A69B7E","#C09A6C","#CE8F5C","#D8804F","#DC6E45","#D65B3E","#C8453A"];
function draw(){
  const dem=D.vissim.map(s=>s.demand), lo=Math.min(...dem), hi=Math.max(...dem);
  const col=d=>RAMP[Math.round((RAMP.length-1)*(d-lo)/Math.max(hi-lo,1e-9))];
  let h="";
  // grid
  for(let k=0;k<=KMAX;k+=10){h+=`<line x1="${sx(k)}" y1="${T}" x2="${sx(k)}" y2="${H-B}" stroke="var(--grid)" stroke-width="1"/>`;
    h+=`<text x="${sx(k)}" y="${H-B+20}" text-anchor="middle" font-family="IBM Plex Mono" font-size="11" fill="var(--muted)">${k}</text>`;}
  for(let q=0;q<=QMAX;q+=250){h+=`<line x1="${L}" y1="${sy(q)}" x2="${W-Rr}" y2="${sy(q)}" stroke="var(--grid)" stroke-width="1"/>`;
    h+=`<text x="${L-9}" y="${sy(q)+4}" text-anchor="end" font-family="IBM Plex Mono" font-size="11" fill="var(--muted)">${q}</text>`;}
  // demand band
  const dq=D.demand.map(x=>x.per_lane), dmin=Math.min(...dq), dmax=Math.max(...dq);
  h+=`<rect x="${L}" y="${sy(dmax)}" width="${W-L-Rr}" height="${sy(dmin)-sy(dmax)}" fill="var(--ink)" opacity=".055"/>`;
  h+=`<text x="${W-Rr-6}" y="${sy(dmax)-7}" text-anchor="end" font-family="IBM Plex Mono" font-size="10.5" fill="var(--muted)">본선 수요 ${Math.round(dmin)}–${Math.round(dmax)} veh/h/lane</text>`;
  // scatter
  D.vissim.forEach(s=>{const c=col(s.demand);
    s.points.filter((_,i)=>i%%2===0).forEach(p=>{h+=`<circle cx="${sx(p[0]).toFixed(1)}" cy="${sy(p[1]).toFixed(1)}" r="1.7" fill="${c}" opacity=".5"/>`;});});
  // numsim
  (D.numsim||[]).forEach((s,j)=>{s.points.filter((_,i)=>i%%3===0).forEach(p=>{
    h+=`<rect x="${(sx(p[0])-2).toFixed(1)}" y="${(sy(p[1])-2).toFixed(1)}" width="4" height="4" fill="none" stroke="var(--ink)" stroke-width="1" opacity=".55"/>`;});});
  // FD curve
  const pth=D.curve.filter(p=>p.rho<=KMAX&&p.q<=QMAX).map((p,i)=>`${i?"L":"M"}${sx(p.rho).toFixed(1)},${sy(p.q).toFixed(1)}`).join(" ");
  h+=`<path d="${pth}" fill="none" stroke="var(--curve)" stroke-width="2.6"/>`;
  // capacity point
  const kc=D.fd.rho_crit, qc=D.fd.capacity_q_per_lane;
  h+=`<line x1="${sx(kc)}" y1="${sy(qc)}" x2="${sx(kc)}" y2="${H-B}" stroke="var(--cap)" stroke-width="1.2" stroke-dasharray="4 3"/>`;
  h+=`<circle cx="${sx(kc)}" cy="${sy(qc)}" r="5.5" fill="var(--cap)"/>`;
  h+=`<text x="${sx(kc)+11}" y="${sy(qc)-9}" font-family="IBM Plex Mono" font-size="11.5" font-weight="600" fill="var(--cap)">용량 ${kc.toFixed(1)} · ${Math.round(qc)}</text>`;
  // axes
  h+=`<line x1="${L}" y1="${H-B}" x2="${W-Rr}" y2="${H-B}" stroke="var(--ink-2)" stroke-width="1.3"/>`;
  h+=`<line x1="${L}" y1="${T}" x2="${L}" y2="${H-B}" stroke="var(--ink-2)" stroke-width="1.3"/>`;
  h+=`<text x="${(L+W-Rr)/2}" y="${H-14}" text-anchor="middle" font-family="Work Sans" font-size="13" fill="var(--ink-2)">밀도 k [veh/km/lane]</text>`;
  h+=`<text transform="translate(20,${(T+H-B)/2}) rotate(-90)" text-anchor="middle" font-family="Work Sans" font-size="13" fill="var(--ink-2)">유량 q [veh/h/lane]</text>`;
  document.getElementById("plot").innerHTML=h;
  document.getElementById("legend").innerHTML =
    `<span class="chip"><span style="width:16px;height:3px;background:var(--curve);display:inline-block"></span>플랜트 FD</span>`+
    `<span class="chip"><span class="dot" style="background:var(--cap)"></span>용량점</span>`+
    D.vissim.map(s=>`<span class="chip"><span class="dot" style="background:${col(s.demand)}"></span>×${s.demand.toFixed(1)}</span>`).join("")+
    ((D.numsim||[]).length?`<span class="chip"><span style="width:8px;height:8px;border:1px solid var(--ink);display:inline-block"></span>numsim 플랜트</span>`:"");
}
draw();
document.getElementById("tbl").innerHTML = D.table.map(r=>
  `<tr><td>×${r.demand.toFixed(1)}</td><td>${r.n}</td><td>${r.k_med.toFixed(2)}</td>
   <td>${Math.round(r.q_med)}</td><td>${Math.round(r.q_p95)}</td>
   <td class="${r.pct>100?"hi":""}">${r.pct.toFixed(0)}%%</td></tr>`).join("");
document.getElementById("dtbl").innerHTML = D.demand.map(r=>
  `<tr><td>${r.t0}–${r.t1} s</td><td>${Math.round(r.vph)}</td>
   <td>${Math.round(r.per_lane)}</td><td>${r.pct.toFixed(0)}%%</td></tr>`).join("");
</script>
""" % json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    out = R / args.out if not Path(args.out).is_absolute() else Path(args.out)
    out.write_text(HEAD + body + script, encoding="utf-8")
    print("-> %s  (%.0f KB · numsim %d런)" % (out, out.stat().st_size / 1024, len(ns)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
