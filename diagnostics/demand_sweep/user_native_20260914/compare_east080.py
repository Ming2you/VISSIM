"""Compare two completed native runs using only their post-run CSV/JSON."""
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
CASE = HERE/'east080_v1'


def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def read(folder, name):
    with (folder/name).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def summarize(folder):
    summary = load(folder/'summary.json')
    area = load(folder/'area_metrics.json')
    assert summary['completed'] and summary['end_sec'] == 9000
    assert area['sampling']['missing_snapshot_gaps'] == 0
    errors = [e for item in summary['native_errors'] for e in item['events']]
    remaining = {str(e['input_no']):e['remaining_vehicles'] for e in errors if e['kind']=='unfinished_vehicle_input'}
    removals = [e for e in errors if e['kind']=='lane_change_removal']
    ramps = defaultdict(lambda: defaultdict(float))
    for r in read(folder, 'ramps_150s.csv'):
        key = r['connector']
        ramps[key]['total_merges'] += int(r['observed_connector_to_mainline'])
        if 900 <= int(r['start_sec']) and int(r['end_sec']) <= 3000:
            ramps[key]['merges_900_3000'] += int(r['observed_connector_to_mainline'])
        ramps[key]['end_n'] = int(r['connector_end_n'])
        ramps[key]['stopped_veh_h'] += float(r['connector_stopped_veh_h'])
    origin_appearances = {}
    origin_windows = []
    link_rows = read(folder, 'links_150s.csv')
    pairs = read(folder, 'link_pairs_150s.csv')
    for source in ('74','26'):
        entries = sum(int(r['entries']) for r in link_rows if r['link']==source)
        incoming_pairs = sum(int(r['vehicles']) for r in pairs if r['to_link']==source)
        origin_appearances[source] = entries-incoming_pairs
        for start in range(0,9000,900):
            entries = sum(int(r['entries']) for r in link_rows if r['link']==source and start <= int(r['start_sec']) < start+900)
            incoming = sum(int(r['vehicles']) for r in pairs if r['to_link']==source and start <= int(r['start_sec']) < start+900)
            origin_windows.append(dict(source=source,start_sec=start,end_sec=start+900,first_appearances=entries-incoming))
    groups = defaultdict(list)
    cells = read(folder, 'fw_cells_30s.csv')
    for r in cells:
        groups[(r['direction'],int(r['cell']))].append(r)
    spatial = []
    for (direction, cell), rows in sorted(groups.items()):
        seq = []
        onset = None
        for r in rows:
            if int(r['n'])>=5 and r['mean_speed_kph'] and float(r['mean_speed_kph'])<30:
                seq.append(int(r['sec']))
                if onset is None and seq[-1]-seq[0]>=120:
                    onset=seq[0]
            else:
                seq=[]
        tail=[r for r in rows if int(r['sec'])>8700 and int(r['n'])>=5]
        count=sum(int(r['n']) for r in tail)
        spatial.append({'cell':direction+str(cell+1),'onset_sec':onset,
            'last300s_vehicle_weighted_speed':sum(int(r['n'])*float(r['mean_speed_kph']) for r in tail)/count if count else None,
            'final_n':int(rows[-1]['n']),'final_stopped':int(rows[-1]['stopped'])})
    return dict(ttt_veh_h=area['ttt_veh_h'],ttd_events=area['ttd_observed_plus_terminal_events'],
        end_omega_n=area['censored_last_observed_inside_vehicles'],
        unresolved_inside_disappearances=area['unresolved_inside_disappearances'],
        closure_max_abs=area['closure']['max_abs_residual_veh'],
        native_explicit_deletions=len(removals), uninserted_by_input=remaining,
        uninserted_total=sum(remaining.values()),source_link_first_appearances=origin_appearances,
        source_appearance_900s_windows=origin_windows,
        ramps=dict(ramps),spatial=spatial,road_recovery=read(folder,'road_recovery.csv'))


def main():
    a,b = summarize(HERE/'results_v1'),summarize(CASE/'results_v1')
    result={'baseline':a,'east080':b,'ttt_change_percent':(b['ttt_veh_h']/a['ttt_veh_h']-1)*100,
        'interpretation':'Demand sensitivity, not controller improvement. Only east freeway input1098 changed; same seed does not force equal stochastic realized counts at other origins.',
        'congestion_definition':'n>=5 and speed<30 at five consecutive30-second snapshots spanning120seconds; no continuous interpolation proof',
        'source_appearance_definition':'Physical source-link entries minus observed incoming-link transitions; sampled first appearance, not desired demand',
        'ramp_inventory':'Connector stock includes moving vehicles; upstream shared approaches excluded from this local stock, but included in Omega costs where mapped'}
    (CASE/'comparison.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    sys.path.insert(0,str(HERE.parents[1]/'rule_baseline_20260914/.plot-deps'))
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family':'Malgun Gothic','axes.unicode_minus':False,'font.size':11})
    fig, axes=plt.subplots(2,1,figsize=(14,8),sharex=True,layout='constrained')
    for ax, folder, title in zip(axes,(HERE/'results_v1',CASE/'results_v1'),('사용자 원본','동측 본선 입력만 0.8배')):
        grid=np.full((21,300),np.nan)
        for r in read(folder,'fw_cells_30s.csv'):
            if r['direction']=='E' and int(r['n'])>=5 and r['mean_speed_kph']:
                grid[int(r['cell']),int(r['sec'])//30-1]=float(r['mean_speed_kph'])
        cmap=plt.get_cmap('RdYlBu').copy(); cmap.set_bad('#eeeeee')
        im=ax.imshow(grid,origin='lower',aspect='auto',extent=(0,150,.5,21.5),vmin=0,vmax=120,cmap=cmap,interpolation='nearest')
        ax.set_title(title,loc='left',weight='bold'); ax.set_ylabel('동측 셀 번호 · 진행 방향 → 증가')
        ax.set_yticks([1,4,7,10,13,16,19,21]); ax.axvline(90,color='black',linestyle='--',alpha=.4)
    axes[-1].set_xlabel('시뮬레이션 시간 [분]')
    fig.colorbar(im,ax=axes,label='순간 셀 평균 속도 [km/h] · 5대 미만 회색',shrink=.9)
    fig.suptitle('동측 본선 수요 20% 감소 비교 · 9000초 · seed13\n도시·램프행 설정 수요, 신호, 희망속도 및 네트워크 동일',fontsize=16)
    fig.savefig(CASE/'east_speed_comparison.png',dpi=160); plt.close(fig)
    print(json.dumps({k:v for k,v in result.items() if k not in ('baseline','east080')},ensure_ascii=False))
    for name, data in [('baseline',a),('east080',b)]:
        print(json.dumps({name:{k:v for k,v in data.items() if k not in ('spatial','road_recovery')}},ensure_ascii=False))


if __name__ == '__main__':
    main()
