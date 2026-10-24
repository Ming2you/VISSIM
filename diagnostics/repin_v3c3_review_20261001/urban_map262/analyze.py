"""Matched 150-second native snapshots on original INPX road geometry. No COM/FZP."""
import csv, ctypes, ctypes.wintypes, hashlib, json, sys
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.colors import Normalize, LinearSegmentedColormap
from matplotlib.lines import Line2D
from PIL import Image

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
I=ROOT/"diagnostics/sdmpc_n31_20260924/integration_20260926"
sys.path.insert(0,str(ROOT))
from evaluation.controllers.control_area_objective import physical_membership_from_ledger
END=8550
OUT=HERE/f"to{END}"
RUNS={
 "nc":Path("D:/VISSIM_runs/20260927_sd31_wiring9000/nc"),
 "sdmpc":Path("D:/VISSIM_runs/20261006_min2_storage90_fixed90_s29_9000/sdmpc")}
PINS={}
def read(p):
    b=p.read_bytes();PINS[str(p)]=hashlib.sha256(b).hexdigest()
    return json.loads(b)
def save(p,obj):
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf8")
def integrate(a,t):
    return ((a[1:]+a[:-1])*0.5*np.diff(t)[:,None]).sum(axis=0)
def main():
    OUT.mkdir(exist_ok=True)
    assert not (OUT/"summary.json").exists(),"Preserve completed output"
    k=ctypes.WinDLL("kernel32");k.GetCurrentProcess.restype=ctypes.wintypes.HANDLE
    k.SetPriorityClass.argtypes=[ctypes.wintypes.HANDLE,ctypes.wintypes.DWORD]
    assert k.SetPriorityClass(k.GetCurrentProcess(),0x4000)
    member=physical_membership_from_ledger(read(I/"selected/scenario/control_area_membership_213a5d.json"))
    meta=read(ROOT/"diagnostics/repin_v3c3_review_20261001/urban259/links.json")
    cats={int(a["link"]):a["category"] for a in meta}
    prov={a:read(r/f"run_provenance_sdmpc31_{a}9000_s29.json") for a,r in RUNS.items()}
    for key in ["network","demand_profile","control_mapping","vehicle_input_roles","generated_vbs_config","signal_group_plan"]:
        assert prov["nc"]["files"][key]["sha256"]==prov["sdmpc"]["files"][key]["sha256"],key
    for key in ["seed","sim_period_sec","control_interval_sec","demand_scale"]:
        assert prov["nc"][key]==prov["sdmpc"][key],key
    network=Path(prov["sdmpc"]["files"]["network"]["path"]);raw=network.read_bytes()
    PINS[str(network)]=hashlib.sha256(raw).hexdigest()
    assert PINS[str(network)]==prov["sdmpc"]["files"]["network"]["sha256"]
    net=ET.fromstring(raw)
    links={}
    for l in net.findall("./links/link"):
        lid=int(l.get("no"))
        xyz=np.array([[float(x.get("x")),float(x.get("y")),float(x.get("zOffset","0"))] for x in l.findall("./geometry/linkPolyPts/linkPolyPoint")])
        length=float(np.linalg.norm(np.diff(xyz,axis=0),axis=1).sum())
        assert length>0 and len(l.findall("./lanes/lane"))>0
        links[lid]=dict(xy=xyz[:,:2],length=length,lanes=len(l.findall("./lanes/lane")),category=cats[lid],inside=bool(member[str(lid)]))
    ids=sorted(links);index={lid:j for j,lid in enumerate(ids)}
    times=np.array([0,1]+list(range(150,END+1,150)),float)
    data={};warm={}
    for arm,run in RUNS.items():
        N=np.zeros((len(times),len(ids)),int);S=N.copy();V=np.zeros_like(N,dtype=float)
        lane_end={};source_rows=0;stop_speed_max=0.
        for ti,t in enumerate(times[1:],1):
            st=read(run/f"decisions_sdmpc31_{arm}9000_s29"/f"state_{int(t):06d}.json")
            v=st["vehicle_records"];rows=v["records"]
            assert st["sim_sec"]==t==v["paused_at_sim_sec"]==v["capture_sim_sec_before"]==v["capture_sim_sec_after"]
            assert v["complete"] and v["unobservable_count"]==0
            assert len(rows)==v["record_count"]==st["total_vehicles"]==len({x["veh_no"] for x in rows})
            assert st["run_provenance"]["run_id"]==prov[arm]["run_id"]
            if t<=900:
                digest=hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest()
                if arm=="nc":warm[int(t)]=digest
                else:assert digest==warm[int(t)]
            for vrec in rows:
                lid=int(vrec["link_no"]);j=index[lid];speed=vrec["speed_kph"];stop=bool(vrec["stopped"])
                assert 1<=vrec["lane_no"]<=links[lid]["lanes"]
                N[ti,j]+=1;S[ti,j]+=stop;V[ti,j]+=speed
                if stop:stop_speed_max=max(stop_speed_max,speed)
                if t==END:
                    key=f'{lid}:{vrec["lane_no"]}'
                    lane_end.setdefault(key,dict(n=0,stopped=0))
                    lane_end[key]["n"]+=1;lane_end[key]["stopped"]+=stop
            assert N[ti].sum()==len(rows)
            assert {str(ids[j]):int(n) for j,n in enumerate(N[ti]) if n}=={str(k):v for k,v in st["vehicle_records"]["full_network_link_counts"].items() if v}
            source_rows+=len(rows)
        data[arm]=dict(N=N,S=S,V=V,lane_end=lane_end,source_rows=source_rows,stopped_max_speed_kph=stop_speed_max)
    lane_km=np.array([links[x]["length"]*links[x]["lanes"]/1000 for x in ids])
    urban=np.array([cats[x]=="urban_and_other_inside" for x in ids])
    outside=np.array([cats[x]=="outside" for x in ids])
    ramps=np.array([cats[x] in ("on_ramp_connector","off_ramp_connector") for x in ids])
    freeway=np.array([cats[x].startswith("FW_") for x in ids])
    assert np.all(urban.astype(int)+outside+ramps+freeway==1)
    # Compare already certified prefix link/cell stocks without rerunning any forecast.
    prior=ROOT/"diagnostics/repin_v3c3_review_20261001/interim261/to8100"
    for arm in data:
        d=data[arm];old=np.load(prior/f"{arm}_snapshots.npz")
        subset=times<=8100
        for c,mask in enumerate([np.array([cats[x]=="FW_E" for x in ids]),np.array([cats[x]=="FW_W" for x in ids]),urban|ramps,outside]):
            assert np.array_equal(d["N"][subset][:,mask].sum(axis=1),old["stocks"][:,c])
        np.savez_compressed(OUT/f"{arm}_link_observations.npz",times=times,link_ids=ids,N=d["N"],stopped=d["S"],speed_sum=d["V"],lane_km=lane_km)
    windows=[(3600,4200),(END-600,END)]
    means={}
    for arm,d in data.items():
        means[arm]=[]
        for lo,hi in windows:
            mask=(times>=lo)&(times<=hi)
            means[arm].append({key:integrate(d[key][mask],times[mask])/(hi-lo) for key in ["N","S"]})
    summary=dict(status="INTERIM_NATIVE_SNAPSHOT_MAP",end_sec=END,seed=29,windows=windows,
      physical_model_predictions=False,source_rows={a:d["source_rows"] for a,d in data.items()},
      warmup_exact=list(warm),network_sha256=PINS[str(network)],arms={},focus_links=[],
      definitions=dict(density="Trapezoid time-average native link vehicle count / (3D polyline km x native number of lanes).",
       stopped_density="Same normalization for native stopped flag; not detector occupancy and not mean waiting time per vehicle.",
       scope="Maps color all non-freeway/non-ramp urban/other links; solid=inside physical Omega, dashed=outside. Mainline and 14 ramp connectors shown only as context.",
       windows="600s trapezoid from five complete native snapshots 150s apart; endpoints weighted by 75s and interior by150s.",
       waiting_time="Individual accrued waiting time not available. Sparse stopped-stock integral is only an estimated total stopped-vehicle time, not vehicle mean delay."),
      limitations=["Not a completed9000 result.","150s sampling aliases red/green and misses between-sample queues; 600s aggregation cannot remove all phase bias.",
       "Whole-link lane-average density can dilute a queue concentrated in one lane or one end.",
       "No native exit/deletion/uninserted analysis in this task; a falling stock alone does not prove normal discharge.",
       "Schematic uses original INPX road geometry without satellite imagery; sub60m urban links shown as neutral context only."],
      geometry=dict(links=len(ids),urban_inside_links=int(urban.sum()),urban_inside_lane_km=float(lane_km[urban].sum())),
      checks=dict(prefix8100_exact=True,complete_native_vehicle_records=True,unique_vehicle_ids=True,link_counts_reconciled=True,simulation_or_queue_changed=False))
    for arm,d in data.items():
        sums={}
        for name,mask in [("urban_inside",urban),("urban_outside",outside),("ramps",ramps)]:
            total=d["N"][:,mask].sum(axis=1);stop=d["S"][:,mask].sum(axis=1)
            sums[name]=dict(end_vehicles=int(total[-1]),end_stopped=int(stop[-1]),
                peak_stopped=int(stop.max()),peak_stopped_sec=int(times[stop.argmax()]),
                end_density=float(total[-1]/lane_km[mask].sum()),
                stopped_time_estimate_veh_h=float(integrate(stop[:,None],times)[0]/3600),
                window_means=[dict(vehicles=float(m["N"][mask].sum()),stopped=float(m["S"][mask].sum())) for m in means[arm]])
        summary["arms"][arm]=sums
    scores=means["sdmpc"][-1]["S"].copy()
    scores[freeway|ramps]=-1
    focus=sorted(set([40,52,68,66,120,329]+[ids[j] for j in np.argsort(scores)[-8:]]))
    for lid in focus:
        j=index[lid];row=dict(link=lid,category=cats[lid],length_m=links[lid]["length"],lanes=links[lid]["lanes"])
        for arm,d in data.items():
            row[arm]=dict(end_n=int(d["N"][-1,j]),end_stopped=int(d["S"][-1,j]),
                early_mean_stopped=float(means[arm][0]["S"][j]),late_mean_stopped=float(means[arm][1]["S"][j]),
                late_stopped_density=float(means[arm][1]["S"][j]/lane_km[j]),
                end_lanes={k:v for k,v in d["lane_end"].items() if k.startswith(f"{lid}:")})
        summary["focus_links"].append(row)
    with (OUT/"link_window_metrics.csv").open("w",newline="",encoding="utf-8-sig") as f:
        w=csv.writer(f);w.writerow(["arm","from_sec","to_sec","link","category","lanes","length_m","mean_n","mean_stopped","density_veh_per_lane_km","stopped_density_veh_per_lane_km"])
        for arm in data:
            for wi,(lo,hi) in enumerate(windows):
                for j,lid in enumerate(ids):
                    n,s=means[arm][wi]["N"][j],means[arm][wi]["S"][j]
                    w.writerow([arm,lo,hi,lid,cats[lid],links[lid]["lanes"],links[lid]["length"],n,s,n/lane_km[j],s/lane_km[j]])
    draw(links,ids,index,lane_km,urban,outside,ramps,freeway,times,data,means,net,summary)
    summary["source_sha256"]=PINS
    save(OUT/"summary.json",summary)
    print(json.dumps({k:summary[k] for k in ["end_sec","arms","focus_links","checks"]},ensure_ascii=False),flush=True)

def draw(links,ids,index,lane_km,urban,outside,ramps,freeway,times,data,means,net,summary,*,speed_only=False,controlled_signals=None):
    plt.rcParams.update({"font.family":"Malgun Gothic","axes.unicode_minus":False,"font.size":11,"figure.facecolor":"white"})
    bg=next(x for x in net.findall("./backgroundImages/backgroundImage") if x.get("no")=="4")
    bl=bg.find("coordBL");tr=bg.find("coordTR")
    origin=np.array([float(bl.get("x")),float(bl.get("y"))])
    extent=[0,(float(tr.get("x"))-origin[0])/1000,0,(float(tr.get("y"))-origin[1])/1000]
    geom=[(links[l]["xy"]-origin)/1000 for l in ids]
    major=np.array([links[l]["length"]>=60 for l in ids])
    points=np.vstack([geom[j] for j in np.where(urban)[0]])
    xmin,xmax=points[:,0].min()-.18,points[:,0].max()+.18
    ymin,ymax=points[:,1].min()-.18,points[:,1].max()+.18
    cmap=plt.get_cmap("RdYlBu") if speed_only else LinearSegmentedColormap.from_list("urban_density",["#719db4","#ecddae","#efa45b","#d6543b","#851b34"])
    norm=Normalize(0,60 if speed_only else 100)
    labels={40:(-.65,.24),52:(.72,.30),68:(.78,-.22),66:(-.65,-.48),127:(.1,.25),38:(-.4,-.2)}
    centers={}
    if controlled_signals:
        heads={int(s['sc_no']):[] for s in controlled_signals}
        for head in net.findall('./signalHeads/signalHead'):
            sc=int(head.get('sg').split()[0])
            if sc not in heads:continue
            lid=int(head.get('lane').split()[0]);xy=geom[index[lid]]
            along=np.r_[0,np.cumsum(np.linalg.norm(np.diff(xy,axis=0),axis=1))]
            pos=float(head.get('pos'))/1000
            heads[sc].append([np.interp(pos,along,xy[:,axis]) for axis in (0,1)])
        assert all(heads.values()) and len(heads)==17
        centers={sc:np.mean(points,axis=0) for sc,points in heads.items()}
    def base(ax):
        ax.add_collection(LineCollection(geom,colors="#d7dce1",linewidths=.55,zorder=1))
        ax.add_collection(LineCollection([geom[j] for j in np.where(freeway)[0]],colors="#6d4ca0",linewidths=1.25,zorder=2))
        ax.add_collection(LineCollection([geom[j] for j in np.where(ramps)[0]],colors="#495f76",linewidths=1.0,zorder=2))
        ax.set(xlim=(xmin,xmax),ylim=(ymin,ymax),aspect="equal")
        ax.set_xticks([]);ax.set_yticks([])
        ax.plot([xmin+.25,xmin+1.25],[ymin+.18,ymin+.18],color="#17212b",lw=2)
        ax.text(xmin+.75,ymin+.22,"1 km",ha="center",fontsize=9)
        ax.annotate("N",xy=(xmin+.23,ymax-.32),xytext=(xmin+.23,ymax-.7),
                    ha="center",fontsize=10,arrowprops=dict(arrowstyle="-|>",color="#17212b"))
        for spine in ax.spines.values():spine.set_edgecolor("#d0d6dd")
    def map_panel(ax,arm,wi,key,annotate=True):
        base(ax)
        if key=="V":
            n=means[arm][wi]['N']
            values=np.divide(means[arm][wi]['V'],n,out=np.full_like(n,np.nan),where=n>0)
        else:values=means[arm][wi][key]/lane_km
        for mask,style,width in [(outside,"solid" if speed_only else "dashed",1.9 if speed_only else 1.45),(urban,"solid",1.9)]:
            js=np.where(mask & major & np.isfinite(values))[0]
            ax.add_collection(LineCollection([geom[j] for j in js],array=values[js],cmap=cmap,norm=norm,linewidths=width,linestyles=style,zorder=3))
        if centers:
            points=np.array(list(centers.values()))
            ax.scatter(points[:,0],points[:,1],marker='s',s=23,facecolors='white',edgecolors='#202b37',linewidths=.9,zorder=5)
            ax.annotate('SC1004',xy=centers[1004],xytext=centers[1004]+[-.18,-.27],fontsize=8,color='#253342',ha='right',zorder=7)
        if annotate:
            for lid,offset in labels.items():
                j=index[lid];g=geom[j];middle=g[len(g)//2]
                n=means[arm][wi]["S"][j]
                value_label=(f'{values[j]:.1f} km/h' if np.isfinite(values[j]) else '차량 관측 없음') if key=='V' else f'정지 {n:.0f}대'
                label=f"{lid}"+("*" if outside[j] else "")+f"\n{value_label}"
                ax.annotate(label,xy=middle,xytext=middle+offset,fontsize=9,ha="center",va="center",
                  bbox=dict(boxstyle="round,pad=.22",facecolor="white",edgecolor="#c5ccd3",alpha=.95),
                  arrowprops=dict(arrowstyle="-",lw=.65,color="#374151"),zorder=6)
    handles=[Line2D([0],[0],color="#e07c2e",lw=2,label="Ω 내부 도시도로"),
       Line2D([0],[0],color="#e07c2e",ls="--",lw=2,label="Ω 밖 도시도로 (*)"),
       Line2D([0],[0],color="#6d4ca0",lw=2,label="고속도로 (배경)"),
       Line2D([0],[0],color="#495f76",lw=2,label="램프 (배경)")]
    plots=[("V","도시부 평균속도","urban_speed_latest")] if speed_only else [("S","도시부 정지 차량 밀도","urban_stopped_density_latest"),("N","도시부 전체 차량 밀도","urban_density_latest")]
    if speed_only:
        handles=[Line2D([0],[0],color='#9e5a39',lw=2,label='도시도로: 평균속도로 채색'),
          Line2D([0],[0],color='#202b37',marker='s',markerfacecolor='white',ls='',label='제어 교차로 17개'),
          Line2D([0],[0],color='#6d4ca0',lw=2,label='고속도로 (배경)'),
          Line2D([0],[0],color='#d7dce1',lw=2,label='차량 미관측 / 짧은 연결로')]
    for key,title,fname in plots:
        fig,axes=plt.subplots(1,2,figsize=(17,8.8))
        fig.subplots_adjust(left=.02,right=.92,bottom=.15,top=.86,wspace=.035)
        for ax,arm,name in zip(axes,["nc","sdmpc"],["무제어","SDMPC + 고정 VSL90"]):
            map_panel(ax,arm,1,key)
            avg=means[arm][1][key][urban].sum()
            label="정지" if key=="S" else "재고"
            ax.set_title(name if speed_only else f"{name}  |  Ω 도시부 평균 {label} {avg:.0f}대",fontsize=14)
        cax=fig.add_axes([.937,.24,.015,.53])
        fig.colorbar(plt.cm.ScalarMappable(norm=norm,cmap=cmap),cax=cax,extend="max",label="차량 가중 평균속도 [km/h]" if speed_only else ("정지 " if key=="S" else "")+"차량 / (차로·km)")
        fig.suptitle(title+f" · {END-600:,}–{END:,}초",fontsize=20,y=.97)
        fig.legend(handles=handles,loc="lower center",bbox_to_anchor=(.47,.083),ncol=4,frameon=False)
        if speed_only:
            fig.text(.025,.060,"실제 도로 선형 · seed29 · 150초 관측 5회의 600초 집계 · 정지 차량 포함 · 두 패널의 색상 범위 동일 (0–60 km/h)",fontsize=10)
            fig.text(.025,.030,"* 기존 Ω 집계 경계 밖 (무제어라는 뜻 아님): 66번은 SC1004 제어 접근도로 · 도로 전체 평균이며 대기시간이 아님",fontsize=10,color="#505a65")
        else:
            fig.text(.025,.060,"실제 도로 선형 · 60m 이상 도시도로 중심 · seed29 · 150초 관측 5회의 600초 평균 · 길이·차로 수로 정규화",fontsize=10)
            fig.text(.025,.030,"숫자: 도로 ID / 평균 정지 대수 · 차량 없는 링크는 0 · 신호 정차 포함 · 개별 차량의 평균 대기시간이 아님",fontsize=10,color="#505a65")
        fig.savefig(OUT/f"{fname}.png",dpi=160)
        plt.close(fig)
    if speed_only:return
    fig,axes=plt.subplots(2,2,figsize=(15,14))
    fig.subplots_adjust(left=.025,right=.915,bottom=.10,top=.90,hspace=.12,wspace=.03)
    for wi,window in enumerate(summary["windows"]):
        for ai,arm in enumerate(["nc","sdmpc"]):
            map_panel(axes[wi,ai],arm,wi,"S",False)
            name="무제어" if arm=="nc" else "현재 제어"
            axes[wi,ai].set_title(f"{name} · {window[0]:,}–{window[1]:,}초",fontsize=14)
    cax=fig.add_axes([.934,.28,.015,.45])
    fig.colorbar(plt.cm.ScalarMappable(norm=norm,cmap=cmap),cax=cax,extend="max",label="정지 차량 / (차로·km)")
    fig.suptitle("도시부 정체의 공간 분포 변화",fontsize=21,y=.965)
    fig.legend(handles=handles,loc="lower center",bbox_to_anchor=(.48,.05),ncol=4,frameon=False)
    fig.text(.025,.027,"600초 평균 · 모든 패널의 위치·색상 범위 동일 · 150초 관측에 따른 중간 추정치",fontsize=11)
    fig.savefig(OUT/"urban_spatial_evolution.png",dpi=140);plt.close(fig)
    fig,axes=plt.subplots(2,1,figsize=(12,7.8),sharex=True)
    for arm,color,label in [("nc","#3175a8","무제어"),("sdmpc","#c84e36","현재 제어")]:
        for ax,mask in zip(axes,[urban,outside]):
            ax.plot(times,data[arm]["S"][:,mask].sum(axis=1),color=color,label=label,lw=1.8)
            ax.scatter([END],[data[arm]["S"][-1,mask].sum()],s=24,color=color)
    for ax,title in zip(axes,["Ω 내부 도시·연결도로 (본선·진입/진출 램프 커넥터 제외)","Ω 밖 도시·기타 도로"]):
        ax.set_title(title,loc="left");ax.set_ylabel("관측 정지 차량 수 [대]")
        ax.set_ylim(bottom=0);ax.grid(alpha=.18);ax.axvline(900,color="#777",ls="--",lw=.8);ax.legend(frameon=False,ncol=2)
    axes[-1].set_xlim(0,END);axes[-1].set_xticks(list(range(0,8101,900))+[END])
    axes[-1].set_xlabel("시뮬레이션 시간 [초]")
    fig.suptitle("도시부 정지 재고가 후반에 줄어드는가?",fontsize=17)
    fig.text(.09,.025,"150초 간격 순간 관측 · 신호 정차 포함 · 9000초 종료 결과가 아님",fontsize=10,color="#555")
    fig.subplots_adjust(left=.09,right=.98,top=.90,bottom=.12,hspace=.30)
    fig.savefig(OUT/"urban_stopped_over_time.png",dpi=160);plt.close(fig)
def render_cached_speed():
    """Only the completed NPZ cache and pinned geometry; never read live states."""
    summary=json.loads((OUT/'summary.json').read_text(encoding='utf8'))
    network=next(Path(p) for p,h in summary['source_sha256'].items()
                 if p.lower().endswith('.inpx') and h==summary['network_sha256'])
    raw=network.read_bytes()
    assert hashlib.sha256(raw).hexdigest()==summary['network_sha256']
    net=ET.fromstring(raw)
    meta=json.loads((ROOT/'diagnostics/repin_v3c3_review_20261001/urban259/links.json').read_text(encoding='utf8'))
    cats={int(x['link']):x['category'] for x in meta}
    ledger_path=I/'selected/scenario/control_area_membership_213a5d.json'
    ledger=json.loads(ledger_path.read_text(encoding='utf8'))
    mapping_path=ROOT/'evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json'
    mapping_raw=mapping_path.read_bytes()
    assert hashlib.sha256(mapping_raw).hexdigest()=='d0a7bb9ff830f84c519608b2e77379f7bbe65606567cf2b9488b2c47759cde64'
    mapping=json.loads(mapping_raw)
    links={}
    for link in net.findall('./links/link'):
        lid=int(link.get('no'))
        xyz=np.array([[float(p.get('x')),float(p.get('y')),float(p.get('zOffset','0'))]
                      for p in link.findall('./geometry/linkPolyPts/linkPolyPoint')])
        links[lid]=dict(xy=xyz[:,:2],length=float(np.linalg.norm(np.diff(xyz,axis=0),axis=1).sum()),
                        lanes=len(link.findall('./lanes/lane')),category=cats[lid])
    data={};means={};cache_hashes={}
    for arm in ('nc','sdmpc'):
        path=OUT/f'{arm}_link_observations.npz'
        cache_hashes[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
        with np.load(path) as z:
            if arm=='nc':times=z['times'];ids=z['link_ids'].tolist();lane_km=z['lane_km']
            else:
                assert np.array_equal(times,z['times']) and ids==z['link_ids'].tolist()
                assert np.array_equal(lane_km,z['lane_km'])
            data[arm]={'N':z['N'],'S':z['stopped'],'V':z['speed_sum']}
        assert times[-1]==END and set(ids)==set(links)
        assert np.all(data[arm]['V'][data[arm]['N']==0]==0)
        means[arm]=[]
        for lo,hi in summary['windows']:
            mask=(times>=lo)&(times<=hi)
            assert np.array_equal(times[mask],np.arange(lo,hi+1,150))
            means[arm].append({k:integrate(v[mask],times[mask])/(hi-lo) for k,v in data[arm].items()})
    expected_lane_km=np.array([links[l]['length']*links[l]['lanes']/1000 for l in ids])
    assert np.allclose(lane_km,expected_lane_km,rtol=0,atol=1e-12)
    index={lid:i for i,lid in enumerate(ids)}
    urban=np.array([cats[l]=='urban_and_other_inside' for l in ids])
    outside=np.array([cats[l]=='outside' for l in ids])
    ramps=np.array([cats[l] in ('on_ramp_connector','off_ramp_connector') for l in ids])
    freeway=np.array([cats[l].startswith('FW_') for l in ids])
    assert all((str(l) in ledger['outside_links'])==bool(outside[i]) for i,l in enumerate(ids))
    heads66=[dict(h.attrib) for h in net.findall('./signalHeads/signalHead') if h.get('lane','').split()[0]=='66']
    assert len(heads66)==4 and {h['sg'] for h in heads66}=={'1004 3','1004 8'}
    assert '66' in ledger['pn_perimeter_links'] and '66' in ledger['comparison_controlled_owner_union_links']
    details=[]
    for lid in (40,52,68,66,127,38):
        j=index[lid]
        row={'link':lid,'category':cats[lid],'length_m':links[lid]['length'],'lanes':links[lid]['lanes']}
        for arm in data:
            m=means[arm][-1];n=float(m['N'][j]);s=float(m['S'][j]);v=float(m['V'][j]/n) if n>0 else None
            # Independent direct five-snapshot weights verify the plotted statistic.
            mask=(times>=END-600)&(times<=END);w=np.array([.125,.25,.25,.25,.125])
            if v is not None:assert abs(v-(data[arm]['V'][mask,j]@w)/(data[arm]['N'][mask,j]@w))<1e-10
            row[arm]={'mean_n':n,'mean_stopped':s,'density_veh_per_lane_km':n/lane_km[j],
                      'stopped_density_veh_per_lane_km':s/lane_km[j],'vehicle_weighted_speed_kph':v}
        details.append(row)
    draw(links,ids,index,lane_km,urban,outside,ramps,freeway,times,data,means,net,summary,
         speed_only=True,controlled_signals=mapping['signals'])
    save(OUT/'speed_map_summary.json',dict(window_sec=[END-600,END],source_cache_sha256=cache_hashes,
        network_sha256=summary['network_sha256'],focus_links=details,link66_signal_heads=heads66,
        membership_ledger=str(ledger_path),control_mapping=str(mapping_path),
        definitions={'speed':'Trapezoid integral of native sum(vehicle speeds) / integral of native vehicle count; stopped vehicles included.',
                     'zero_vehicles':'Unknown speed, gray. Never assigned zero or free-flow speed.',
                     'color':'Common absolute 0..60 km/h; red=slow, blue=fast, upper extension above60.',
                     'line_style':'All colored urban roads solid. Squares=17 controlled junctions, estimated from associated signal head positions.',
                     'asterisk':'Outside existing physical Omega accounting, not uncontrolled. Link66 is controlled by SC1004 SG3/SG8 but outside stopline-based Omega.'},
        limitations=summary['limitations']+['Observed vehicle mean speed, not route travel speed or individual waiting time.','Sparse signal-phase sampling can bias speed, too.'],
        checks={'five_point_weights_verified':True,'geometry_lane_km_matches_cache':True,'no_simulation_or_objective_changes':True}))
    print(json.dumps({'image':str(OUT/'urban_speed_latest.png'),'focus_links':details},ensure_ascii=False))

if __name__=="__main__":
    if sys.argv[1:]==['--cached-speed']:render_cached_speed()
    else:main()
