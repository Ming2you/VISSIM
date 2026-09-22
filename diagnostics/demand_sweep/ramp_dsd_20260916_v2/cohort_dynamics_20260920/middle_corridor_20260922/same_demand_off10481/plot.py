"""Post-run FZP speed picture for the unchanged-input route experiment."""
from pathlib import Path
import argparse, json, sys
ROOT=Path(__file__).resolve().parents[6]
sys.path.insert(0,str(ROOT/'.review-deps'))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--case',type=Path,default=Path(__file__).resolve().parent)
parser.add_argument('--moved-pct',type=int,choices=(25,50),default=50)
parser.add_argument('--both-off-half',action='store_true',help='Label the scenario reducing both exits, not relocating toward10481')
parser.add_argument('--geometry',type=Path,default=Path(__file__).resolve().parents[3]/'segment_resolution_20260921/geometry_200_branch_guard.json')
parser.add_argument('--demand-pct',type=int,choices=(70,80,90,100),default=100)
parser.add_argument('--demand-label',help='Explicit demand label for different freeway/urban scales')
parser.add_argument('--control-arm',choices=('none','rm','vsl','both'),default='none')
args=parser.parse_args()
B=args.case.resolve()
receipt=json.loads((B/'run/run.json').read_text(encoding='utf-8-sig'))
terminal=int(receipt.get('terminal_sec',0))
assert receipt['completed'] and terminal in (5400,7200,9000), 'Require completed native run'
g=json.loads(args.geometry.read_text())
chain={int(r['link']):r for r in g['chains']['FW_E']}
end=g['bounds']['FW_E'][-1]
x=np.arange(0,terminal+1,30)
y=np.append(np.arange(0,end,100),end)
n=np.zeros((len(y)-1,len(x)-1));moment=np.zeros_like(n)
last=None;times=[];total=0;outside=0
with (B/'run/vissim_eval/baseline_001.fzp').open('rb') as f:
    cols=None
    for line in f:
        if line.startswith(b'$VEHICLE:'):
            cols=line.strip().split(b':',1)[1].split(b';')
            assert cols[:7]==[b'SIMSEC',b'NO',b'LANE\\LINK\\NO',b'LANE\\INDEX',b'POS',b'POSLAT',b'SPEED']
            continue
        if not line[:1].isdigit():continue
        assert cols is not None
        p=line.split(b';',7);t=float(p[0]);total+=1
        if t!=last:
            if last is not None:assert abs(t-last-5)<1e-7,(last,t)
            times.append(t);last=t
        link=int(p[2])
        if link not in chain or not 0<=t<terminal:continue
        r=chain[link];pos=r['offset_m']+float(p[4])
        if not 0<=pos<end:outside+=1;continue
        i=min(int(pos//100),len(y)-2);j=int(t//30)
        n[i,j]+=1;moment[i,j]+=float(p[6])
assert last>=terminal-5 and len(times)>=terminal//5-2,(last,len(times))
speed=np.divide(moment,n,out=np.full_like(n,np.nan),where=n>0)
plt.rcParams.update({'font.family':'Malgun Gothic','axes.unicode_minus':False,'font.size':11})
fig,ax=plt.subplots(figsize=(14,8.2))
fig.subplots_adjust(left=.08,right=.77,bottom=.17,top=.84)
cmap=plt.get_cmap('RdYlBu').copy();cmap.set_bad('#eeeeee')
mesh=ax.pcolormesh(x,y/1000,speed,cmap=cmap,vmin=0,vmax=120,shading='flat',rasterized=True)
ax.set(xlim=(0,terminal),ylim=(0,end/1000),xlabel='시뮬레이션 시간 [초]',ylabel='동측 본선 진입점부터 거리 [km] → 하류')
ax.set_xticks(np.arange(0,terminal+1,900));ax.set_yticks(np.arange(0,11,1))
ax.grid(axis='x',color='white',alpha=.3,lw=.6)
marks=[(4.386,'10643 진출 ↓',4.21),(4.699,'10639 진입',4.67),(5.042,'10681 진입',5.13),
       (6.827,'10481 진출 ↓' if args.both_off_half else '10481 진출 ↑',6.72),(7.243,'10490 진입',7.24),(7.604,'10484 진입',7.78)]
for d,text,label in marks:
    ax.axhline(d,color='#172d46',linestyle='--',alpha=.5,lw=.7)
    ax.annotate(text,xy=(terminal,d),xytext=(terminal+terminal/135,label),ha='left',va='center',fontsize=10,
                annotation_clip=False,arrowprops={'arrowstyle':'-','lw':.6,'color':'#172d46'})
ax.axhspan(5.042,6.827,fill=False,edgecolor='#781478',lw=1.5,linestyle=':')
ax.text(90,6.05,'두 램프군 사이',color='#501750',fontsize=11,
        bbox=dict(facecolor='white',edgecolor='none',alpha=.8,pad=3))
cax=fig.add_axes([.92,.25,.017,.48]);fig.colorbar(mesh,cax=cax,label='평균속도 [km/h]')
demand_label=args.demand_label or f'입력 수요 {args.demand_pct}%'
control_label={'none':'무제어','rm':'ALINEA RM','vsl':'규칙 기반 VSL','both':'ALINEA RM + 규칙 기반 VSL'}[args.control_arm]
title=(f'{demand_label} · 10643·10481행 감소 → 본선 직진 — {control_label}' if args.both_off_half
       else f'수요 유지 · 기존 10643행의 {args.moved_pct}%를 10481로 이동 — {control_label}')
fig.suptitle(title,fontsize=18,fontweight='bold',y=.97)
subtitle=('기존 기하/신호/VSL 유지 · RM 제어 없음' if args.control_arm=='none'
          else '동일 기하·수요·도시 신호 · 900초부터 150초마다 제어')
fig.text(.5,.905,f'seed {receipt["seed"]} · {terminal}초 · {subtitle}',ha='center',fontsize=12)
fig.text(.08,.06,'FZP 5초 간격 기록 → 30초 × 100m 차량 가중 평균속도 | 빈 공간은 회색\n'
         '보라색 테두리: 앞쪽 램프군 이후 ~ 뒤쪽 진출부. 혼잡 원인과 제어 효과는 이 그림만으로 확정하지 않음.',fontsize=10,color='#425269')
fig.savefig(B/'east_heatmap.png',dpi=165,facecolor='white')
print('FIGURE',B/'east_heatmap.png')
print('FZP',len(times),'frames,',total,'rows; first/last',times[0],last,'outside',outside)
windows=[(0,900),(1800,2700),(2700,3600),(4500,5400)]
windows.extend((lo,lo+900) for lo in range(5400,terminal,900))
for lo,hi in windows:
    yy=(y[:-1]>=5041.906)&(y[1:]<=6826.843);xx=(x[:-1]>=lo)&(x[1:]<=hi)
    nn=n[np.ix_(yy,xx)];mm=moment[np.ix_(yy,xx)]
    print('middle',lo,hi,'mean_speed_kmh',round(mm.sum()/nn.sum(),2))
