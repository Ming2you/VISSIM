"""Render cached TTT and write the completed report; never read FZP again."""
from pathlib import Path
import csv,json,os,shutil,hashlib
OUT=Path('E:/VISSIM_analysis/20261010_coupling268_three8100_v2')
os.environ['MPLCONFIGDIR']=str(OUT/'mplconfig')
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
read=lambda p:json.loads(p.read_bytes())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
s=read(OUT/'summary.json')
assert s['precontrol_prefix_exact'] and s['all_native_execution_passed']
arms=['nc','window','optimized','off']
labels=['무제어','시간창 VSL90','SDMPC VSL','VSL OFF']
plt.rcParams.update({'font.family':'Malgun Gothic','axes.unicode_minus':False,'font.size':11})
initial=OUT/'TTT_comparison_initial.png'
assert not initial.exists(),'Preserve original and avoid duplicate render'
shutil.copy2(OUT/'TTT_comparison.png',initial)
fig,axes=plt.subplots(1,2,figsize=(14,5.4),layout='constrained')
for arm,label,color in zip(arms,labels,['#808080','#2476b8','#d47720','#239379']):
    with (OUT/arm/'area_timeseries.csv').open(encoding='utf-8-sig') as f:rows=list(csv.DictReader(f))
    axes[0].plot([float(x['sim_sec']) for x in rows],[float(x['ttt_veh_h_cumulative']) for x in rows],label=label,color=color,lw=2)
axes[0].set(xlabel='시뮬레이션 시간 [초]',ylabel='누적 Ω701 TTT [대·시간]',xlim=(0,8100))
axes[0].legend();axes[0].grid(alpha=.25)
bottom=np.zeros(4);x=np.arange(4)
for key,label,color in zip(['FW_E','FW_W','urban_ramps_inside'],['동측 본선','서측 본선','도시부·램프 등'],['#5e91ba','#8cc2d8','#dda465']):
    v=np.array([s['conditions'][a]['components_veh_h'][key] for a in arms])
    axes[1].bar(x,v,bottom=bottom,label=label,color=color);bottom+=v
for i,arm in enumerate(arms):
    row=s['conditions'][arm];label=f"{row['ttt_veh_h']:,.1f}"
    if arm!='nc':label+=f"\n{row['improvement_percent']:.2f}% 감소"
    axes[1].text(i,bottom[i]+90,label,ha='center',va='bottom',fontsize=10)
axes[1].set_xticks(x,labels);axes[1].set_ylabel('TTT [대·시간]');axes[1].set_ylim(0,max(bottom)*1.17)
axes[1].legend(loc='upper center',bbox_to_anchor=(.5,1.09),ncol=3,fontsize=9,frameon=False)
fig.suptitle('동일 Ω701·0–8100초 TTT 비교 | 도시 신호·RM은 세 제어 조건 모두 SDMPC',fontsize=14,fontweight='bold')
fig.savefig(OUT/'TTT_comparison.png',dpi=160);plt.close(fig)
rows=['| 조건 | 전체 TTT [대·시간] | 무제어 대비 감소 | 동측 본선 | 서측 본선 | 도시부·램프 등 | 삭제 |',
      '|---|---:|---:|---:|---:|---:|---:|']
for arm,label in zip(arms,labels):
    r=s['conditions'][arm];c=r['components_veh_h']
    rows.append(f"| {label} | {r['ttt_veh_h']:,.3f} | {r['improvement_percent']:.3f}% | {c['FW_E']:,.3f} | {c['FW_W']:,.3f} | {c['urban_ramps_inside']:,.3f} | {r['native_removals']} |")
text='# coupling268 완료3조건 · 0–8100초 비교\n\n'+ '\n'.join(rows)+"""
\n같은 망·FW80/도시90·seed29·Ω701.900초 제어 전 FZP기록이 동일하다. 세 제어 조건의 green/offset/RM은 모두 SDMPC다. window는 동측 병목에1800≤t<5700만90, 나머지110. optimized는8개 내부 구역의 VSL도 SDMPC가 선택한다. off는 전구간110이고 green/offset/RM은 계속 제어한다. 적용 구역과 다른 명령도 다르므로 VSL 단독의 인과효과로 해석하지 않는다.

시간창 조건이 전체 TTT에서는 가장 낮다. OFF 대비46.001대·시간(약0.65%) 낮고, 동측 본선만 보면 OFF가5.205대·시간 낮다. 시간창 조건의 전체 우위는 도시부·램프 등 및 서측 본선 차이에서 온다. 독립seed 반복 없이 이 작은 차이의 일반성을 주장하지 않는다.

계산은 기존 정본 measure_frames를 사용했다. NC의 완료된 동일영역 TTT/5초 시계열은 재사용했고, 동서측15초×100m 속도 지도는 각 파일을 한 번씩 읽어 생성했다. 신규 세 조건은 같은 순회에서 TTT도 집계했다. 마지막 실측8095.1초부터8100초까지4.9초는 재고 유지이며 유출로 세지 않았다. 실측5초 기록을 차량 가중 평균속도로 집계했고 빈 공간은 보간하지 않았다.

주의:
- 삭제 차량이 NC233대에서 window350/optimized422/off360대로 늘었다. 표의 TTT감소를 삭제와 무관한 순수 교통개선으로 확정하지 않는다.
- Ω 밖 관측 체류는 각각 NC1588.760/window1656.121/optimized1653.225/off1645.241대·시간으로 증가했다. 목적함수의 Ω 범위는 그대로 유지하며 외부효과로 따로 보고한다.
- 미삽입 대기시간은 같은8100초 기준의 NC값이 없어 비교하지 않는다. NC9000초 종료값을 가져오지 않았다.
- 도시부·램프 등 열은 본선을 제외한 Ω내부 전체다. 도시부만의 지표가 아니다.
- 원래 verifier의 신호/DSD readback·native LDP 실행 검사를 모두 통과했다. 기존 LSA coverage미충족은 각 execution.json에 보존했다.
- 원본 VISSIM·설정·동결본은 수정하지 않았다. 새native/plant예측/보정은0회다. 이 결과는 coupling268실행본이며 이후 집계동역학/347정본 연결을 적용한 native결과가 아니다.

그림: TTT_comparison.png, FW_E_heatmap_zoom.png, FW_E_heatmap.png, FW_W_heatmap.png.
원시 집계와 재현정보: summary.json, comparison.csv 및 각조건폴더.
"""
(OUT/'README.md').write_text(text,encoding='utf8')
receipt=dict(status='complete_visual_review',source=str(Path(__file__)),source_sha256=sha(Path(__file__)),
    initial_ttt_sha256=sha(initial),final_ttt_sha256=sha(OUT/'TTT_comparison.png'),fzp_rescanned=False)
(OUT/'render_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf8')
plan=Path(__file__).parent/'plan.json';data=read(plan)
data['completed_analysis_20261010']=dict(status='complete',output=str(OUT),summary_sha256=sha(OUT/'summary.json'),
    end_sec=8100,omega_links=701,all_native_execution_passed=True,lsa_coverage_passed=False,
    raw_ttt_improvement_percent={a:s['conditions'][a]['improvement_percent'] for a in arms},
    deletion_and_outside_cost_limitations=True,new_native=0,latest_aggregate_plant_native_validation=False)
tmp=plan.with_suffix('.analysis.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8');tmp.replace(plan)
with (Path(__file__).parent/'README.md').open('a',encoding='utf8') as f:f.write('\n\n## 2026-10-10 완료 비교\n\n'+text.split('\n\n',1)[1])
print('Cached figures/report finalized; no FZP re-read.')

