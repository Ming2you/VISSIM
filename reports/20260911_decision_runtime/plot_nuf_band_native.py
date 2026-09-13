"""Render the completed SC5 native audit; no simulator or FZP scan."""
from pathlib import Path
import json
import gzip
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT/'.review-deps'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from audit_fw8_rg_meter_response import IndexedFzp, WINDOWS

D=ROOT/'diagnostics/control_improvement/decision_common_anchor_20260911/ramp8_physical_v1'
x=json.loads((D/'native_band5_replay_audit_v1.json').read_text())
font=FontProperties(fname='C:/Windows/Fonts/malgun.ttf').get_name()
plt.rcParams.update({'font.family':font,'axes.unicode_minus':False,'font.size':10})
fig,(ax,bx)=plt.subplots(2,1,figsize=(12,7),sharex=True,
    gridspec_kw={'height_ratios':[1.15,1]},layout='constrained')
rows=[]
for i,sg in enumerate(('1','6','3')):
    for arm in (0,1):
        y=5-(i*2+arm);rows.append((y,f'SG{sg} '+('기준' if arm==0 else '변경')))
        for w in x['runs'][arm]['sc5']['native_green_windows'][sg]:
            a=w['first_native_green_frame_sec'];b=w['last_native_green_frame_sec']
            ax.broken_barh([(a,max(1,b-a+1))],(y-.30,.6),facecolors=('#b1bdc8' if arm==0 else '#158b77'))
ax.scatter([989,991,993,995],[5.62]*4,c='#b63828',s=28,marker='v',zorder=3,
    label='SG1 차량 4대: 접근로 첫 관측')
ax.set_yticks([y for y,l in rows],[l for y,l in rows]);ax.set_ylim(-.7,6.1)
ax.set_title('SC5: 녹색 시점과 차량 도착의 관계 (native LDP · FZP 1초)',loc='left',weight='bold')
ax.legend(loc='upper left',fontsize=9);ax.grid(axis='x',alpha=.2)
for arm,name in enumerate(('native_joint_v2_area','native_band5_replay_area_v1')):
    reader=IndexedFzp(Path(x['runs'][arm]['meters']['fzp']['path']),max_bytes=80*1024*1024)
    try:
        frames={t:{v:r for v,r in rows.items() if r[0] in (1220018401,1220019201)}
            for t,rows in WINDOWS.frames(reader,900,1050)}
    finally:reader.handle.close()
    times=sorted(frames)
    for link,color,road in ((1220018401,'#235a93','SG1·6 접근로'),(1220019201,'#b2682b','SG4·7 접근로')):
        values=[sum(r[0]==link and r[3]<5 for r in frames[t].values()) for t in times]
        assert sum(values[1:])==x['runs'][arm]['sc5']['road_stats'][str(link)]['stopped_vehicle_seconds_lt5']
        bx.plot(times,values,color=color,ls='--' if arm==0 else '-',lw=1.5,
            label=f'{road} '+('기준' if arm==0 else '변경'))
bx.set_ylabel('속도 5 km/h 미만 차량 수 [veh]');bx.set_xlabel('시뮬레이션 시간 [s]')
bx.set_xlim(900,1050);bx.grid(alpha=.2);bx.legend(ncol=2,fontsize=9)
bx.set_title('접근로별 대기 재배분: SG1·6은 Ω 내부, SG4·7은 Ω 밖',loc='left')
fig.suptitle('고속도로80% · 도시50% · seed13 | 동일 준비 구간 후 SC5 고정 명령 비교',fontsize=13)
target=Path(__file__).with_name('SC5_NUF_BAND_NATIVE.png')
fig.savefig(target,dpi=150);plt.close(fig)
print(target)
