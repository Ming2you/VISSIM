"""Small static figure from completed postprocessor tables; never reads FZP."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT/'diagnostics/rule_baseline_20260914/.plot-deps'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

ARMS = ('none','vsl','rm','both')
LABELS = {'none':'무제어','vsl':'VSL','rm':'RM','both':'VSL + RM'}
COLORS = {'none':'#333333','vsl':'#2f6fb0','rm':'#d17b1f','both':'#25916d'}


def rows(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results', type=Path, required=True)
    args = parser.parse_args()
    folder = args.results.resolve()
    comparison = json.loads((folder/'comparison.json').read_text(encoding='utf-8'))
    assert comparison['paired_prefix_passed'] and comparison['paired_native_signals_passed']
    assert comparison['all_Omega_provenance_passed']
    assert all(s['complete'] for s in comparison['arms'])
    font = Path('C:/Windows/Fonts/malgun.ttf')
    if font.exists():
        font_manager.fontManager.addfont(str(font))
        plt.rcParams['font.family'] = font_manager.FontProperties(fname=str(font)).get_name()
    plt.rcParams.update({'axes.unicode_minus':False,'font.size':11,'axes.spines.top':False,
                         'axes.spines.right':False,'savefig.dpi':180})
    fig, axes = plt.subplots(2,2,figsize=(13.4,8.5),layout='constrained')
    totals = {}
    for arm in ARMS:
        color,label = COLORS[arm],LABELS[arm]
        events = rows(folder/arm/'meter_merge_events.csv')
        times = [int(r['upper_s']) for r in events if 1350 < int(r['upper_s']) <= 2250]
        axes[0,0].step([1350]+times+[2250],[0]+list(range(1,len(times)+1))+[len(times)],
                       where='post',color=color,label=label,lw=1.7)
        stocks = [r for r in rows(folder/arm/'meter_states_1s.csv') if 1350 <= int(r['time_s']) <= 2250]
        axes[0,1].plot([int(r['time_s']) for r in stocks],
                       [int(r['upstream_n'])+int(r['downstream_n']) for r in stocks],
                       color=color,label=label,lw=1.3,alpha=.88)
        speeds = [r for r in rows(folder/arm/'spatial_30s.csv')
                  if r['zone']=='drop_upstream_500_0' and 1350 <= int(r['time_s']) <= 2250]
        axes[1,0].plot([int(r['time_s']) for r in speeds],
                       [float(r['v_kmh']) if r['v_kmh'] else float('nan') for r in speeds],
                       color=color,label=label,lw=1.7,marker='o',ms=2.5)
        windows = json.loads((folder/arm/'area_windows.json').read_text(encoding='utf-8'))
        totals[arm] = {(r['window_start_s'],r['window_end_s']):r['ttt_veh_h'] for r in windows}
    titles = ['10490 실제 본선 합류 누적량','10490 커넥터 재고',
              '실제 차로 감소 지점 직전 500 m 평균속도','Ω TTT 변화: 제어 - 무제어']
    for ax,title in zip(axes.flat,titles):
        ax.set_title(title,pad=9,fontweight='bold')
        ax.grid(alpha=.2)
    for ax in (axes[0,0],axes[0,1],axes[1,0]):
        ax.set_xlim(1350,2250)
        ax.set_xlabel('시뮬레이션 시간 [s]')
        ax.axvline(1800,color='#999999',ls=':',lw=1)
    axes[0,0].set_ylabel('누적 합류 차량 [veh]')
    axes[0,1].set_ylabel('신호두 전·후 전체 재고 [veh]')
    axes[1,0].set_ylabel('30초 시점 차량 평균속도 [km/h]')
    axes[0,0].legend(ncols=2,frameon=False)
    windows = ((1350,1800),(1800,2250),(1350,2250))
    width = .23
    for index,arm in enumerate(ARMS[1:]):
        values = [totals[arm][w]-totals['none'][w] for w in windows]
        bars = axes[1,1].bar([j+(index-1)*width for j in range(3)],values,width,
                             color=COLORS[arm],label=LABELS[arm])
        axes[1,1].bar_label(bars,fmt='%+.2f',padding=3,fontsize=9)
    axes[1,1].axhline(0,color='#333333',lw=.8)
    axes[1,1].set_xticks(range(3),['1350–1800','1800–2250','1350–2250'])
    axes[1,1].set_xlabel('평가 구간 [s] · 음수는 TTT 감소')
    axes[1,1].set_ylabel('ΔTTT [veh·h]')
    axes[1,1].margins(y=.16)
    axes[1,1].legend(frameon=False,ncols=3)
    fig.suptitle('동일 초기 상태 · seed 13 · 고정 명령의 실제 VISSIM 반응\n'
                 '1350초 이전 FZP 일치 | Ω = 고속도로 + 도시 protected network',fontsize=15)
    for suffix in ('png','pdf'):
        target=folder/('four_arm_native_response.'+suffix)
        assert not target.exists(),target
        fig.savefig(target)
    plt.close(fig)
    print(json.dumps({'figure':str(folder/'four_arm_native_response.png')},ensure_ascii=False))


if __name__ == '__main__':
    main()
