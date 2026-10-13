"""Bounded offline SC101 head-rate candidate; never installed in a native run.

Rate is a past-only achieved support estimate including startup, not proof of
universal saturation capacity. Reuse2400 estimate unchanged at3300.
"""
import copy,hashlib,json
from pathlib import Path
import xml.etree.ElementTree as ET
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
MOVEMENT='SC101_S_SC1_to_N_SC2005'
RIGHT='SC101_S_SC1_to_E_SC5'
CUTOFF=2400

def read(p):return json.loads(p.read_bytes())

def paired_support(report,cutoff=CUTOFF):
    rows=[r for r in report['rows'] if r['end_sec']<=cutoff]
    pairs=[]
    for x,y in zip(rows,rows[1:]):
        gx,gy=x['groups']['SC101_S'],y['groups']['SC101_S']
        if x['end_sec']!=y['start_sec'] or not (gx['all_heads_prefix_qualified'] and gy['all_heads_prefix_qualified']):continue
        hx={h['head_id']:h for h in gx['heads']};hy={h['head_id']:h for h in gy['heads']}
        if set(hx)!=set(hy) or len(hx)!=3:raise ValueError('Different physical heads')
        per_head={}
        for k,h in hx.items():
            z=hy[k]
            if h['lane']!=z['lane']:raise ValueError('Head lane changed')
            for r in (h,z):
                if (not r['eligible'] or r['queued_prefix_veh']<5
                    or not r['green_start']<r['prefix_last_sec']<r['green_end']
                    or len(set(r['queued_prefix_ids']))!=r['queued_prefix_veh']):
                    raise ValueError('Invalid queued prefix witness')
                expected=3600*r['queued_prefix_veh']/(r['prefix_last_sec']-r['green_start'])
                if abs(expected-r['startup_inclusive_achieved_rate_veh_h'])>1e-7:raise ValueError('Rate calculation mismatch')
            per_head[k]=min(h['startup_inclusive_achieved_rate_veh_h'],z['startup_inclusive_achieved_rate_veh_h'])
        pairs.append(dict(end_sec=[x['end_sec'],y['end_sec']],per_head_rate_veh_h=per_head,rate_veh_h=sum(per_head.values())))
    if not pairs:raise ValueError('No paired past-only queued discharge witness')
    return max(pairs,key=lambda p:p['rate_veh_h'])

def install(cfg,at):
    if at not in (2400,3300):raise ValueError('Bounded saved-state diagnostic only')
    report=read(HERE/'service_evidence.json')
    for p,h in report['source_pins'].items():
        if hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h:raise ValueError('Audit source changed: '+p)
    support=paired_support(report)
    tree=ET.parse(ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx').getroot()
    heads=[h for h in tree.findall('./signalHeads/signalHead') if h.get('no') in support['per_head_rate_veh_h']]
    if len(heads)!=3 or {h.get('sg') for h in heads}!={'101 8'} or {h.get('lane') for h in heads}!={f'1220011503 {i}' for i in (1,2,3)}:raise ValueError('SC101 head identity changed')
    links={x.get('no'):x for x in tree.findall('./links/link')}
    direct=links['10538'];start=direct.find('fromLinkEndPt');end=direct.find('toLinkEndPt')
    if start.get('lane')!='1220011503 1' or len(direct.findall('./lanes/lane'))!=3 or end.get('lane').split()[0]!='1220016101':raise ValueError('Straight connector changed')
    for node in links.values():
        src=node.find('fromLinkEndPt')
        if src is None or node.get('no')=='10538' or src.get('lane').split()[0]!='1220011503':continue
        low=int(src.get('lane').split()[1]);lanes=set(range(low,low+len(node.findall('./lanes/lane'))))
        if any(int(h.get('lane').split()[1]) in lanes and float(src.get('pos'))>=float(h.get('pos')) for h in heads):raise ValueError('Competing post-head consumer')
    right=links['10528'].find('fromLinkEndPt')
    if right.get('lane')!='1220011503 1' or float(right.get('pos'))>=float(next(h for h in heads if h.get('lane').endswith(' 1')).get('pos')):raise ValueError('Right no longer branches before the measured head')
    expected={'signal':'SC101','phase':'SC101_p1','origin':'SC1_to_SC101','receiving_link':'SC101_to_SC2005'}
    net=cfg.network
    if any(net.urban_movements[MOVEMENT].get(k)!=v for k,v in expected.items()):raise ValueError('Movement identity changed')
    turns=net.control_area_routes['movement:'+MOVEMENT]['physical_turns']
    if len(turns)!=1 or turns[0].get('connector')!='10538':raise ValueError('Canonical turn changed')
    if MOVEMENT in net.local_service_pool['group_of']:raise ValueError('Unexpected shared model pool')
    if expected['receiving_link'] not in net.urban_link_storage_veh:raise ValueError('No downstream storage')
    before=copy.deepcopy(net.movement_capacity_by_movement_veh_h)
    after=dict(before);after[MOVEMENT]=max(before[MOVEMENT],support['rate_veh_h'])
    net.movement_capacity_by_movement_veh_h=after
    assert {k for k in after if after[k]!=before[k]}=={MOVEMENT}
    assert after[RIGHT]==before[RIGHT]
    return dict(variant='offline_past_prefix_service',cutoff_sec=CUTOFF,applied_at=at,
        before_veh_h=before[MOVEMENT],after_veh_h=after[MOVEMENT],right_veh_h_unchanged=after[RIGHT],
        support=support,new_parameters=1,production_installed=False,
        source='Two past queued-prefix windows; per-head minimum summed, no future native observations',
        limitations=['Startup-inclusive achieved lower-bound support is not a constant future capacity guarantee.',
        'Existing shared source stock and receiving limits still apply. Lateral gap/FIFO is not solved.',
        'Rate estimate and unique head attribution are one candidate, not isolated causal effects.'])

