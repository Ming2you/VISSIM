"""Render already computed private-prior evidence; never runs the model."""
from pathlib import Path
import csv,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]


def main():
    report=json.loads((ROOT/'diagnostics/joint_offratio_sensitivity.json').read_text(encoding='utf-8'))
    trace=json.loads((ROOT/'diagnostics/joint_offratio_sensitivity_trace.json').read_text(encoding='utf-8'))
    rows=report['results'];names=['current','native_total_only','native_joint'];labels={'current':'현재','native_total_only':'total만 native','native_joint':'일관된 native joint'}
    keyed={(r['name'],r['horizon_sec']):r for r in rows}
    text=['# 총 유출과 신호·직행 비율의 공동 민감도',
        '', '**총 유출 비율만 native 값으로 바꾸면 잘못 늘어난 신호 방향 유입으로 추가 정체를 만들 수 있다.** 실제1200초 상태와 같은1200초 명령을 고정한450초 모델 예측에서 total-only는 FE 신호 저장고를 포화시키고 E8 속도를5km/h로 떨어뜨렸다. Native signal/direct/through를 함께 맞춘 arm에서는 해당 포화가 발생하지 않았다. 이 결과는 비율의 일관성 검증이며 물리 모델의 보정 완료나 실제 성능 개선을 뜻하지 않는다.',
        '', '세 arm은 동일한 합본 canonical runtime, 초기 물리 재고, 수요 전망, geometry/capacity, signal/meter/VSL/offset을 쓴다. 바뀌는 것은 private cfg의 total off ratio와 (joint arm에서만) conditional direct ratio다. 과거 파일에는 현재 route가 없어4대를 명시적으로 보류하며, 모든 arm에서 같은 보류 상태를 유지했다. 새 VISSIM이나 optimizer는 실행하지 않았다.',
        '', '| 그룹 | native signal/direct/through weight | total off | direct given off | total-only의 signal 몫 | native signal 몫 |',
        '|---|---|---:|---:|---:|---:|']
    overlay=report['overlay']
    for off,row in overlay['native_sources'].items():
        w=row['weights'];wrong=overlay['arms']['native_total_only']['implied_joint'][off]['signal']
        text.append(f"| {off} | {w['signal']:g}/{w['direct']:g}/{w['through']:g} | {row['total_off']:.6f} | {row['direct_given_off']:.6f} | {wrong:.6f} | {row['joint']['signal']:.6f} |")
    text += ['', 'FE에서 total-only의 signal 몫0.212471은 native1.6/13.6=0.117647과 다르다. FW도0.172000 대0.083333으로 차이가 크다. 이 비율은 해당 정적 결정에 적용되는 미래 선택의 조건부 prior다. 두 출구 사이 합류 차량, 앞선 경로의 종료·조합, 시간창 내 재고 변화는 이 분모와 같지 않다. 빈1133 signal weight는 공식 VISSIM2020 default1이고 COM passage에서 추정한 값이 아니다.',
        '', '| 길이(s) | arm | Ω TTT(veh·h) | Ω TD(veh) | FW cell TTT(veh·h) | 최종 FW N | 최종 Ω N | E8 v(km/h) | E8 λ |',
        '|---:|---|---:|---:|---:|---:|---:|---:|---:|']
    for r in rows:
        e8=r['final_stock']['cells']['FW_E'][8]
        text.append(f"| {r['horizon_sec']} | {labels[r['name']]} | {r['area']['ttt_veh_h']:.3f} | {r['area']['ttd_veh']:.3f} | {r['controlled_freeway_cell_ttt_veh_h']:.3f} | {sum(r['final_stock']['FW_count_veh'].values()):.3f} | {r['final_omega_veh']:.3f} | {e8['speed_kph']:.3f} | {e8['effective_lanes']:.6f} |")
    text += ['', 'E8의 초기 관측은N51대, 속도41.800km/h다. 첫150초에는 세 모델 모두95–99km/h까지 회복한다. Joint prior가 이 낙관적 회복 문제를 고쳤다는 근거는 없다.450초에서는 total-only가 artificial signal loading에 민감하게 포화되는 차이가 추가로 드러난다.',
        '', '| 길이(s) | off group | 현재 accepted signal/direct(veh) | total-only signal/direct | joint signal/direct |',
        '|---:|---|---:|---:|---:|']
    for depth in (150,450):
        for off in overlay['native_sources']:
            cells=[]
            for name in names:
                flow=keyed[name,depth]['off_flows'][off]
                cells.append(f"{flow['accepted_signal_veh']:.3f}/{flow['accepted_direct_veh']:.3f}")
            text.append(f"| {depth} | {off} | {' | '.join(cells)} |")
    text += ['', '총 selected offflow와 signal/direct의 실제 accepted landing을 별도 계측했다. 각10초에서 signal+direct accepted 합은 freeway가 선택한 offflow와 일치하고 scheduler rejection은0이다.150초 receiving rejection은 전부0.450초 total-only의 DW/FE requested 차단은28.115/29.129대, joint의 DW만25.652대다. 따라서 branch landing 이후의 이중계수나 차량 삭제로 결과가 만들어진 것은 아니다.',
        '', '| 450초 arm | FE signal 모델저장고 N/cap | FE direct 모델저장고 N/cap | FE 첫 receiving차단 시각 | R_D_W queue | R_F_W queue | R_D_E queue | R_F_E queue |',
        '|---|---:|---:|---:|---:|---:|---:|---:|']
    for name in names:
        r=keyed[name,450];off=r['final_stock']['off_branch']['OR_F_E'];q=r['final_stock']['ramp_queue_veh']
        first=next((str(int(p['end_sim_sec'])) for p in trace[name+'_450'] if p['groups']['OR_F_E']['blocked_veh']>1e-8),'없음')
        text.append(f"| {labels[name]} | {off['signal']['stock_veh']:.3f}/{off['signal']['capacity_veh']:.3f} | {off['direct']['stock_veh']:.3f}/{off['direct']['capacity_veh']:.3f} | {first} | {q['R_D_W']:.3f} | {q['R_F_W']:.3f} | {q['R_D_E']:.3f} | {q['R_F_E']:.3f} |")
    text += ['', 'FE total-only에서1,520초부터 receiving이 막히며, 마지막 λ=3.136802, rho93.044veh/km/lane, N149.854대, v5km/h다. Joint는 λ=3.450567, rho21.737, N38.511, v84.586이다. Joint direct 흐름은 다른 하류 문제도 바꾼다. 예를 들어 R_F_W queue가현재123.878→joint174.044대로 늘며,450초 TD는현재1476.047보다 joint1421.943이 적다. 한 비용값으로 물리 prior를 선택하거나 성능 향상이라고 해석해서는 안 된다.',
        '', '위 direct 재고/용량은 모델 landing receiver `SC1004_W_out`의N/cap220이다. 물리10682 단독 저장능력이라고 부르지 않았다. 초기8개 물리 connector의 관측 대수와 projection ownership은 JSON의 `initial_physical_connector_counts_and_projection`에 별도 보존했다. λ 역시 현재 모델의 신호저장고 기반 경로와 기존 grouped cell 위치를 따르며, direct 실제 작은 connector에서 생기는 국지 queue tail을 식별한 결과가 아니다.',
        '', '모든6endpoint의 원본cfg/state/control/demand 불변, 모든10초 제어벡터 일치, macrostep Ω재고 closure, 각450초의 첫150초와 독립150초의 trace 완전일치, 전후 source hash 불변을 검사했다. 현재 결과를 바탕으로 적용 가능한 가장 작은 결론은 total ratio 단독 교정안을 물리적으로 일관된 parameterization으로 취급하지 않는 것이다. 다음 물리 식별에는 출구 사이 합류와 decision eligibility를 포함한 origin/route cohort 및 실제 branch geometry가 필요하다.',
        '', '생산 및 활성 config 변경 없음. 결과는 `joint_offratio_sensitivity.json`,10초 trace는 `joint_offratio_sensitivity_trace.json`, 읽기 전용 private overlay는 `joint_offratio_private_overlay.json`. 재현은 `python -X utf8 -m diagnostics.probe_joint_offratio_sensitivity`, 표/그림은 `python -X utf8 -m diagnostics.render_joint_offratio_sensitivity`.',
        '', '![Model-only native joint sensitivity](joint_offratio_sensitivity.png)', '']
    (ROOT/'diagnostics/joint_offratio_sensitivity.md').write_text('\n'.join(text),encoding='utf-8')
    fields=['arm','end_sim_sec','FE_signal_stock_veh','FE_signal_capacity_veh','FE_direct_receiver_stock_veh','E8_N_veh','E8_speed_kph','E8_lambda','FE_requested_veh','FE_accepted_signal_veh','FE_accepted_direct_veh','FE_blocked_veh','R_F_W_queue_veh']
    flat=[]
    for name in names:
        for row in trace[name+'_450']:
            stock=row['after_landings'];e8=stock['cells']['FW_E'][8];fe=stock['off_branch']['OR_F_E']
            flat.append(dict(zip(fields,[name,row['end_sim_sec'],fe['signal']['stock_veh'],fe['signal']['capacity_veh'],fe['direct']['stock_veh'],
                e8['N_veh'],e8['speed_kph'],e8['effective_lanes'],row['groups']['OR_F_E']['requested_veh'],
                row['landings']['OR_F_E']['signal'],row['landings']['OR_F_E']['direct'],row['groups']['OR_F_E']['blocked_veh'],stock['ramp_queue_veh']['R_F_W']])))
    with (ROOT/'diagnostics/joint_offratio_sensitivity.csv').open('w',newline='',encoding='utf-8') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(flat)
    sys.path.insert(0,str(ROOT/'.review-deps'))
    import matplotlib
    matplotlib.use('Agg')
    matplotlib.rcParams['svg.hashsalt']='joint-offratio-sensitivity'
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(3,1,figsize=(10,8),sharex=True,layout='constrained')
    english={'current':'Current .2 + legacy direct split','native_total_only':'Native total only','native_joint':'Coherent native joint prior'}
    colors={'current':'#4777a7','native_total_only':'#d35e4f','native_joint':'#268a79'}
    for name in names:
        subset=[r for r in flat if r['arm']==name];x=[report['initial_sim_sec']]+[r['end_sim_sec'] for r in subset]
        initial={'FE_signal_stock_veh':report['initial_stock']['off_branch']['OR_F_E']['signal']['stock_veh'],
                 'E8_speed_kph':report['initial_stock']['cells']['FW_E'][8]['speed_kph'],
                 'R_F_W_queue_veh':report['initial_stock']['ramp_queue_veh']['R_F_W']}
        for ax,field in zip(axes,('FE_signal_stock_veh','E8_speed_kph','R_F_W_queue_veh')):
            ax.plot(x,[initial[field]]+[r[field] for r in subset],label=english[name],color=colors[name],linewidth=2)
            ax.grid(alpha=.2)
    axes[0].axhline(flat[0]['FE_signal_capacity_veh'],color='#777777',linestyle='--',linewidth=1,label='FE signal receiver capacity')
    axes[0].set_ylabel('FE signal receiver stock [veh]');axes[1].set_ylabel('E8 model speed [km/h]');axes[2].set_ylabel('R_F_W queue [veh]')
    axes[2].set_xlabel('Simulation time [s]');axes[0].legend(fontsize=8,loc='upper left',ncol=2)
    fig.suptitle('Held actual1200 action: model sensitivity, not physical performance\nSame initial stock/demand/capacity; incomplete historical route observations')
    fig.savefig(ROOT/'diagnostics/joint_offratio_sensitivity.png',dpi=160)
    fig.savefig(ROOT/'diagnostics/joint_offratio_sensitivity.svg',metadata={'Date':None})
    plt.close(fig)
    paths=[ROOT/'diagnostics'/name for name in ('joint_offratio_sensitivity.json','joint_offratio_sensitivity_trace.json',
        'joint_offratio_sensitivity.csv','joint_offratio_sensitivity.png','joint_offratio_sensitivity.svg')]+[Path(__file__).resolve()]
    provenance={'scope':'Model-only private native joint-prior sensitivity; no new VISSIM observations or optimization',
        'source_model_sha256':report['source_sha256'],'figure_initial_sim_sec':report['initial_sim_sec'],
        'figure_end_sim_sec':1650,'trace_cadence_sec':10,'initial_point':'same actual1200 snapshot across arms',
        'matplotlib_version':matplotlib.__version__,'paths_sha256':{str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}}
    (ROOT/'diagnostics/joint_offratio_plot_provenance.json').write_text(json.dumps(provenance,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
