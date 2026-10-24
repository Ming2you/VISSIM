"""Standalone scientific figure from two completed, pinned native caches."""
import gzip
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, Normalize

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
protocol = json.loads((HERE/'protocol.json').read_text(encoding='utf-8'))
plt.rcParams.update({'font.family':'Malgun Gothic', 'axes.unicode_minus':False,
                     'font.size':11, 'axes.spines.top':False, 'axes.spines.right':False})
cmap = LinearSegmentedColormap.from_list('traffic', ['#d95420','#f4ce75','#2266a5'])
fig, axes = plt.subplots(2,1,figsize=(12,6.6),sharex=True,sharey=True)
fig.subplots_adjust(left=.09,right=.89,top=.80,bottom=.19,hspace=.36)
fig.suptitle('셀19·20의 차로별 차량 위치와 속도',fontsize=19,y=.97)
fig.text(.09,.88,'seed67 · 2940.1초 · 두 조건 모두 RM 완화 + 동일 도시 신호\n점 1개 = 차량 1대 · 검은 테두리 사각형 = 속도 5km/h 미만',fontsize=11)
chart_rows=[]
for ax,case,title in zip(axes,('67_release','67_release_vsl90'),('VSL110','VSL90')):
    pin=protocol['inputs'][case]; blob=(ROOT/pin['path']).read_bytes()
    assert hashlib.sha256(blob).hexdigest()==pin['sha256']
    frame=json.loads(gzip.decompress(blob))['frames']['2940.1']
    values=[dict(case=case,vehicle=k,cell=v[0],speed=v[1],x_km=v[2]/1000,lane=v[3])
            for k,v in frame.items() if v[0] in (19,20)]
    chart_rows.extend(values)
    for stopped,marker,size in ((False,'o',34),(True,'s',40)):
        rows=[v for v in values if (v['speed']<5)==stopped]
        ax.scatter([v['x_km'] for v in rows],[v['lane'] for v in rows],
                   c=[v['speed'] for v in rows],cmap=cmap,norm=Normalize(0,110),
                   marker=marker,s=size,edgecolors='#222222' if stopped else 'none',linewidths=.7,zorder=3)
    count=sum(v['speed']<5 and v['lane']==1 for v in values)
    ax.set_title(f'{title}  |  1차로 정지 차량 {count}대',loc='left',fontsize=13,pad=9)
    ax.axvline(7.041711150016619,color='#7f858c',ls='--',lw=1)
    ax.text(6.925,3.35,'셀19',ha='center',color='#565d65')
    ax.text(7.14,3.35,'셀20',ha='center',color='#565d65')
    ax.set_yticks([1,2,3],['1차로','2차로','3차로'])
    ax.set_ylim(.55,3.65);ax.set_xlim(6.835,7.248)
    ax.grid(axis='y',color='#e6e8eb',zorder=0)
    ax.tick_params(axis='both',length=3)
axes[-1].set_xlabel('동측 본선 진입점부터의 누적 거리 [km] → 하류',labelpad=10)
bar=fig.colorbar(matplotlib.cm.ScalarMappable(norm=Normalize(0,110),cmap=cmap),
                 cax=fig.add_axes([.915,.255,.015,.45]),ticks=[0,20,40,60,80,100,110])
bar.set_label('차량 속도 [km/h]',labelpad=10)
fig.text(.09,.055,'완료된 5초 차량 캐시의 한 장면 · 셀 번호는 0기준 · 셀20 끝 부근에 10483 진출부\n사후 선택한 사례이며, 차로 변경 원인이나 전체 망 이득을 이 그림만으로 확정하지 않습니다.',fontsize=10,color='#555d66')
fig.savefig(HERE/'lane_queue_comparison.png',dpi=170,facecolor='white')
(HERE/'chart_rows.json').write_text(json.dumps(chart_rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'png':str(HERE/'lane_queue_comparison.png'),'points':len(chart_rows)}))
