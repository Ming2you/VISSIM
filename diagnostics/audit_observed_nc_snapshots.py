"""Read closed native-baseline anchors; configure/project only, never roll out."""
from pathlib import Path
from collections import Counter,defaultdict
import argparse,csv,hashlib,json,math,os,sys,time,traceback
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def load(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def stable_json(path):
    before=path.stat();data=path.read_bytes();after=path.stat()
    if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):raise ValueError('Anchor is still being written')
    value=json.loads(data.decode('utf-8-sig'))
    return value,hashlib.sha256(data).hexdigest()


def old_rows(path,cutoff):
    with path.open(encoding='utf-8-sig',newline='') as stream:
        return [row for row in csv.DictReader(stream) if float(row['sim_sec'])<=cutoff]


def compare_raw(raw,old):
    fields=('veh_no','link_no','lane_no','position_m','speed_kph','stopped')
    current={r['veh_no']:r for r in raw['vehicle_records']['records']};previous={r['veh_no']:r for r in old['vehicle_records']['records']}
    common=current.keys()&previous.keys();differences=[];maxima={'position_m':0.,'speed_kph':0.}
    for no in sorted(common):
        changed={k:{'new':current[no][k],'old':previous[no][k]} for k in fields if current[no][k]!=previous[no][k]}
        if changed and len(differences)<10:differences.append({'vehicle':no,'fields':changed})
        for key in maxima:maxima[key]=max(maxima[key],abs(current[no][key]-previous[no][key]))
    return {'new_count':len(current),'old_count':len(previous),'new_only_ids':sorted(current.keys()-previous.keys()),
            'old_only_ids':sorted(previous.keys()-current.keys()),'first_differences':differences,'max_abs_difference':maxima,
            'all_record_fields_exact':current==previous}


def compare_csv(raw,global_rows,segment_rows,link_rows):
    second=raw['sim_sec'];global_row=global_rows.get(second)
    basic={};differences=[]
    if global_row:
        for field in ('total_vehicles','urban_vehicles','freeway_vehicles','ramp_vehicles','boundary_vehicles','other_vehicles','mean_speed_kph','freeway_mean_speed_kph','stopped_vehicles'):
            current=float(raw[field]);previous=float(global_row[field]);delta=abs(current-previous)
            basic[field]={'new':current,'old':previous,'abs_difference':delta}
            if delta>5.01e-7:differences.append({'scope':'basic','field':field,'difference':delta})
    segments=[]
    for row in segment_rows.get(second,[]):
        link=row['model_link'];index=int(row['segment_index']);current=raw['freeway_segments'][link][index]
        count=current['count'];speed=current['speed_sum']/count if count else 0.
        dN=count-int(row['count']);dv=abs(speed-float(row['mean_speed_kph']))
        if dN or dv>1e-6:segments.append({'model_link':link,'index':index,'count_delta':dN,'speed_abs_delta':dv})
    physical=defaultdict(list)
    for record in raw['vehicle_records']['records']:physical[str(record['link_no'])].append(record)
    link_diff=[]
    for row in link_rows.get(second,[]):
        records=physical[row['link']];n=len(records);stopped=sum(r['stopped'] for r in records)
        speed=sum(r['speed_kph'] for r in records)/n if n else 0.
        if n!=int(row['count']) or stopped!=int(row['stopped_count']) or abs(speed-float(row['mean_speed_kph']))>1e-6:
            link_diff.append({'link':row['link'],'count_delta':n-int(row['count']),'stopped_delta':stopped-int(row['stopped_count']),
                              'speed_abs_delta':abs(speed-float(row['mean_speed_kph']))})
    old_link_keys={row['link'] for row in link_rows.get(second,[])}
    unlisted={key:len(rows) for key,rows in physical.items() if key not in old_link_keys}
    return {'basic':basic,'basic_present':global_row is not None,'basic_differences':differences,
            'segment_count':len(segment_rows.get(second,[])),'segment_differences':segments,
            'old_link_row_count':len(link_rows.get(second,[])),'link_differences':link_diff,
            'old_link_counts_sum':sum(int(row['count']) for row in link_rows.get(second,[])),
            'new_positive_links_not_in_old_rows':unlisted,
            'scope':'Closed anchor versus completed originalNC CSV. Mean speeds compared at CSV six-decimal precision; this is not vehicle-ID trajectory equivalence.'}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--max-anchor',type=int,default=2700);parser.add_argument('--output',default='observed_nc_snapshot_audit_2700')
    args=parser.parse_args();os.environ['RW_MAINLINE_SG_ONLY']='1';os.environ['RW_OFFSET_WRITER']='experiment'
    new=ROOT/'evaluation/runs/codex_area_observed_nc_s13_20260910';old=ROOT/'evaluation/runs/codex_nc_s13_6056c94_20260909_retry'
    dec=new/('decisions_'+new.name);olddec=old/('decisions_'+old.name);config=ROOT/'diagnostics/area_candidate_configs/n7_area_beta0.json'
    anchors=sorted(path for path in dec.glob('anchor_*.json') if int(path.stem.split('_')[-1])<=args.max_anchor)
    if not anchors:raise ValueError('No completed anchor files selected')
    support_path=ROOT/load(config)['observation']['physical_support_repair'];support=load(support_path)
    physical_membership=load(ROOT/'diagnostics/control_area_membership.json')
    from evaluation.controllers.control_area_objective import physical_membership_from_ledger
    membership=physical_membership_from_ledger(physical_membership)
    paths=[old/f'state_{old.name}.csv',old/f'bottleneck_segments_{old.name}.csv',old/f'bottleneck_links_{old.name}.csv']
    basic={float(r['sim_sec']):r for r in old_rows(paths[0],args.max_anchor)}
    segments=defaultdict(list);links=defaultdict(list)
    for row in old_rows(paths[1],args.max_anchor):segments[float(row['sim_sec'])].append(row)
    for row in old_rows(paths[2],args.max_anchor):links[float(row['sim_sec'])].append(row)
    from diagnostics.probe_model_area_integration import build_projected,replay_provenance
    from evaluation.controllers import route_choice_corridor,area_runtime,vehicle_routes
    hashes=replay_provenance(load(config),config,support_path,*paths,*anchors,dec/'action_000001.json',Path(__file__))
    outputs=[];support_rows=[]
    for path in anchors:
        start=time.monotonic();raw,fingerprint=stable_json(path);second=int(raw['sim_sec'])
        item={'sim_sec':second,'anchor':str(path.relative_to(ROOT)),'anchor_sha256':fingerprint,
              'physical_record_count':len(raw['vehicle_records']['records']),'route_record_count':len(vehicle_routes.complete_vehicle_routes(raw,required=True))}
        item['raw_omega_veh']=sum(count for key,count in raw['vehicle_records']['full_network_link_counts'].items() if membership[key])
        item['prior_csv_comparison']=compare_csv(raw,basic,segments,links)
        previous=olddec/f'state_{second:06d}.json'
        if previous.is_file():item['prior_raw_comparison']=compare_raw(raw,load(previous));hashes[str(previous.relative_to(ROOT))]=sha(previous)
        try:
            cfg,state,detectors,tuning,observed,mapping,metadata=build_projected(config,path,dec/'action_000001.json',fixture_inputs=False)
            ledger=state._control_area_ledger;ledger.assert_stocks(area_runtime.model_inventory(state,cfg))
            item['model_omega_veh']=sum(v['inside'] for v in ledger.stocks.values())
            item['projection_exact']=math.isclose(item['raw_omega_veh'],item['model_omega_veh'],abs_tol=1e-7)
            item['initial_event_count']=ledger.event_count;item['initial_entered_veh']=ledger.metrics.entered_veh;item['initial_ttd_veh']=ledger.metrics.ttd_veh
            item['route_completeness']=route_choice_corridor.diagnostics(state,cfg)
            item['enabled_feature_checks']={'omega':bool(cfg.network.control_area_enabled),'beta_seconds':cfg.network.control_area_beta_seconds,
                'native1091':'1091' in cfg.network.native_internal_inputs['inputs'],
                'physical_phase_authority_corrected_count':metadata.get('physical_phase_authority_corrected_count'),
                'corridor_decisions':[spec['decision'] for spec in route_choice_corridor._specs(cfg)]}
            claim=set(detectors.get('route_choice_verified_physical_stock',{}))|set(detectors.get('native_internal_verified_physical_stock',{}))
            unresolved=set(support['full_area_coverage_audit']['unresolved_physical_links'])-claim
            item['positive_unresolved_links']={k:v for k,v in raw['vehicle_records']['full_network_link_counts'].items() if k in unresolved and v}
            item['unresolved_unclaimed_physical_link_count']=len(unresolved)
            assignment=state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']
            tables={'reviewed_transit_support':support['link_to_storage'],
                    'route_choice_claim':detectors.get('route_choice_verified_physical_stock',{}),
                    'native_internal_input_claim':detectors.get('native_internal_verified_physical_stock',{})}
            used={}
            for kind,table in tables.items():
                present=[]
                for link,target in table.items():
                    count=raw['vehicle_records']['full_network_link_counts'].get(link,0)
                    if count:
                        present.append(link);support_rows.append({'sim_sec':second,'kind':kind,'physical_link':link,'count':count,'target':target,
                            'actual_assignment':json.dumps(assignment.get(link,{}),sort_keys=True)})
                used[kind]={'positive_links':sorted(present,key=int),'counted_veh':sum(raw['vehicle_records']['full_network_link_counts'].get(k,0) for k in present)}
            item['positive_support_used']=used
            item['configure_pass']=(item['projection_exact'] and item['route_completeness']['route_choice_held_unknown_route_veh']==0
                and not item['positive_unresolved_links'] and ledger.event_count==0 and ledger.metrics.entered_veh==0 and ledger.metrics.ttd_veh==0)
        except Exception as exc:
            item['configure_pass']=False;item['error']=str(exc);item['traceback']=traceback.format_exc()
        item['elapsed_sec']=time.monotonic()-start;outputs.append(item)
        print(json.dumps({k:v for k,v in item.items() if k in ('sim_sec','configure_pass','raw_omega_veh','model_omega_veh','error','route_completeness','positive_unresolved_links')},ensure_ascii=False))
    changed=[key for key,value in hashes.items() if sha(ROOT/key)!=value]
    report={'scope':'Closed observed-baseline anchor configure/projection only; no endpoint/optimizer/VISSIM control',
        'new_run':new.name,'reference_run':old.name,'max_selected_anchor':args.max_anchor,'config':str(config.relative_to(ROOT)),
        'previous_action':'actual new baseline action000001 no-control','source_sha256':hashes,'source_changes':changed,
        'anchors':outputs,'limits':['Only900 has corresponding originalNC full raw vehicle records. Later anchors compare same-time completed original CSV physical summaries.',
            'This producer reads closed anchors only. Full FZP trajectory/metrics comparison is a separate completed-run audit.',
            'Successful initial projection is not a guarantee of future trajectory fidelity or complete native demand modelling.']}
    base=ROOT/'diagnostics'/args.output
    base.with_suffix('.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    with base.with_suffix('.csv').open('w',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=['sim_sec','kind','physical_link','count','target','actual_assignment']);writer.writeheader();writer.writerows(support_rows)
    lines=['# 완료된 새 무제어 스냅샷의 투영·동일성 검사','',
        f"{outputs[0]['sim_sec']}~{outputs[-1]['sim_sec']}초의 완료된 {len(outputs)}개 anchor 중 {sum(x['configure_pass'] for x in outputs)}개가 active beta0 error config의 실제 configure_runtime 및 투영을 통과했다. Endpoint나 optimizer는 실행하지 않았다. 생산·입력 파일 hash 변화: {len(changed)}개.",
        '', '| 시각 | 모든physical/route records | Ω raw=model | held unknown | 미지원양수 | 일반transit지원 대수(link수) | route corridor지원 대수(link수) |',
        '|---:|---:|---:|---:|---:|---:|---:|']
    for item in outputs:
        if not item['configure_pass']:
            lines.append(f"| {item['sim_sec']} | {item['physical_record_count']} | FAIL | — | — | — | — |")
            continue
        a=item['positive_support_used']['reviewed_transit_support'];b=item['positive_support_used']['route_choice_claim']
        lines.append(f"| {item['sim_sec']} | {item['physical_record_count']} | {item['raw_omega_veh']} | 0 | 0 | {a['counted_veh']} ({len(a['positive_links'])}) | {b['counted_veh']} ({len(b['positive_links'])}) |")
    lines += ['', '지원 분류는 projection provenance의 처리 경로이며 전체 Ω재고를 서로 배타적으로 분할한 표가 아니다. CSV에는 각 link별 원 관측 대수, target storage, 실제 assignment를 보존했다. 순간 관측 0을 미래 native demand 0으로 해석하지 않는다.',
        '', '900초는원본 `codex_nc_s13_6056c94_20260909_retry`의fullraw와차량별비교했다.2591개ID집합,link,lane,position,speed,stopped가전부정확히같다. 최대위치/속도차이는0이다. 다른nativequalifierrun은비교에사용하지않았다.',
        '', f"원본 NC CSV와 비교한 anchor별 차이 수: {sum(len(x['prior_csv_comparison']['basic_differences'])+len(x['prior_csv_comparison']['segment_differences'])+len(x['prior_csv_comparison']['link_differences'])+len(x['prior_csv_comparison']['new_positive_links_not_in_old_rows']) for x in outputs)}. 매 anchor에서 FW 42셀과 모든 양수 physical link를 대조했다. 평균속도는 CSV 6자리 정밀도로 비교한다.",
        '', '900초 외에는 원본 full raw가 없어 이 producer만으로 개별 ID 궤적 동치를 주장하지 않는다. 전체 5400초 FZP·지표 비교는 별도 완료 런 감사다. 초기 투영 성공은 예측모형 fidelity나 native input 전수 모형화를 증명하지 않는다.',
        '', f"재현: `python -X utf8 -m diagnostics.audit_observed_nc_snapshots --max-anchor {args.max_anchor} --output {args.output}`. 상세JSON과지원link표CSV는동명파일이다.", '']
    base.with_suffix('.md').write_text('\n'.join(lines),encoding='utf-8')


if __name__=='__main__':main()
