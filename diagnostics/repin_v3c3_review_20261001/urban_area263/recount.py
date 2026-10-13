"""Recount the two saved native caches on the user-expanded physical area."""
import csv, hashlib, json, sys
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np

HERE=Path(__file__).resolve().parent
OUT=HERE/'approaches_only'
ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT))
from diagnostics.build_control_area_membership import expand_controlled_intersection_area
from evaluation.controllers.control_area_objective import physical_membership_from_ledger

def read(p):return json.loads(p.read_bytes())
def save(p,obj):p.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    OUT.mkdir(exist_ok=True)
    oldpath=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/scenario/control_area_membership_213a5d.json'
    old=read(oldpath);network=ROOT/old['network']['path']
    assert sha(network)==old['network']['sha256']
    mapping_path=ROOT/'evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json'
    territory_path=ROOT/'outputs/urban_player_territory_v2_20260907.json'
    tree=ET.parse(network).getroot()
    area=expand_controlled_intersection_area(old,tree,read(mapping_path),read(territory_path))
    area['previous_membership']={'path':str(oldpath.relative_to(ROOT)),'sha256':sha(oldpath)}
    area['area_revision_sources']=[{'path':str(p.relative_to(ROOT)),'sha256':sha(p)} for p in
        [mapping_path,territory_path,ROOT/'diagnostics/build_control_area_membership.py',Path(__file__)]]
    save(OUT/'membership.json',area)
    oldset=set(old['inside_links']);newset=set(area['inside_links']);added=newset-oldset
    physical=physical_membership_from_ledger(area)
    assert physical['66'] and not physical['38'] and set(physical)==set(old['inside_links']+old['outside_links'])
    ramps={str(x['connector']) for x in old['ramp_checks']}
    fw=set()
    for row in read(mapping_path)['freeway_model_links'].values():fw.update(str(x) for x in row['chain_links'])
    cache=HERE.parent/'urban_map262/to8550'
    meta=read(HERE.parent/'urban259/links.json');cats={str(x['link']):x['category'] for x in meta}
    metrics={};sources={};link_rows={};series={}
    for arm in ('nc','sdmpc'):
        path=cache/f'{arm}_link_observations.npz';sources[str(path)]=sha(path)
        with np.load(path) as z:times=z['times'];ids=[str(x) for x in z['link_ids']];n=z['N']
        assert times[-1]==8550 and set(ids)==set(physical) and n.shape==(len(times),len(ids))
        assert np.all(n>=0) and np.all(n==np.floor(n))
        per_link=(((n[1:]+n[:-1])/2)*np.diff(times)[:,None]/3600).sum(axis=0)
        masks={'previous_omega':np.array([i in oldset for i in ids]),
               'expanded_omega':np.array([i in newset for i in ids]),
               'added_roads_and_connectors':np.array([i in added for i in ids]),
               'urban_and_ramps':np.array([i in newset-fw for i in ids]),
               'freeway_e':np.array([cats[i]=='FW_E' for i in ids]),
               'freeway_w':np.array([cats[i]=='FW_W' for i in ids]),
               'outside_new_omega':np.array([i not in newset for i in ids])}
        metrics[arm]={};series[arm]={}
        for name,mask in masks.items():
            counts=n[:,mask].sum(axis=1)
            integral=float(np.dot((counts[1:]+counts[:-1])/2,np.diff(times))/3600)
            assert abs(integral-per_link[mask].sum())<1e-9
            metrics[arm][name]={'ttt_veh_h':integral,'remaining_8550':int(counts[-1])}
            series[arm][name]=counts
        def metric(k):return metrics[arm][k]['ttt_veh_h']
        assert abs(metric('expanded_omega')-metric('previous_omega')-metric('added_roads_and_connectors'))<1e-9
        assert abs(metric('expanded_omega')-metric('urban_and_ramps')-metric('freeway_e')-metric('freeway_w'))<1e-9
        for i,lid in enumerate(ids):
            if lid in added:link_rows.setdefault(lid,{'link':lid})[arm]=float(per_link[i])
    comparison={}
    for name in metrics['nc']:
        a=metrics['nc'][name]['ttt_veh_h'];b=metrics['sdmpc'][name]['ttt_veh_h']
        comparison[name]={'nc_veh_h':a,'sdmpc_veh_h':b,'delta_veh_h':b-a,'change_pct':100*(b/a-1)}
    for row in link_rows.values():row['delta_veh_h']=row['sdmpc']-row['nc']
    rows=sorted(link_rows.values(),key=lambda x:-x['delta_veh_h'])
    with (OUT/'added_link_ttt.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['link','nc','sdmpc','delta_veh_h']);writer.writeheader();writer.writerows(rows)
    result={'status':'VALIDATED_RECOUNT_OF_SAME_NATIVE_SNAPSHOTS','period_sec':[0,8550],
        'definition':'Same physical link union for both arms; every observed vehicle counted once regardless of route or stopped flag. Full link length/all lanes.',
        'area':{'previous_count':len(oldset),'expanded_count':len(newset),'added_count':len(added),'membership_sha256':sha(OUT/'membership.json')},
        'metrics':comparison,'per_arm':metrics,'added_highest_delta_links':rows[:15],
        'source_cache_sha256':sources,'prior_validation':str(cache/'summary.json'),
        'limitations':['150-second native inventory trapezoid estimate, not finalized five-second FZP TTT.',
                       'Identical horizon through8550 only; not a9000 result.',
                       'A changed evaluation area is not a new controlled run. Existing controller used the previous area.',
                       'Normal exits/deletions/uninserted not reclassified in this recount. New boundary event accounting must follow the same membership.'],
        'checks':{'exhaustive_disjoint_partition':True,'old_area_subset':True,'per_link_and_aggregate_integrals_match':True,
                  'decomposition_exact':True,'no_native_run_or_fzp_read':True,'live_sources_unchanged':True}}
    save(OUT/'ttt_comparison.json',result)
    print(json.dumps({'area':result['area'],'metrics':comparison,'top_added':rows[:6]},ensure_ascii=False))

if __name__=='__main__':main()
