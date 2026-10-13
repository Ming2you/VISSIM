"""One bounded past-only aggregate candidate, without future calibration."""
from pathlib import Path
from collections import Counter
import hashlib,json,pickle,xml.etree.ElementTree as ET
from diagnostics.repin_v3c3_review_20261001.urban_rm269.sc12_source import audit as h
from evaluation.controllers import obs150_signal_clock as clock
from evaluation.controllers.obs150_observation import sig_manifest_files

HERE=Path(__file__).resolve().parent;A=HERE.parent;ROOT=HERE.parents[4]
def main():
    out=HERE/'support.json';assert not out.exists()
    netpath=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx'
    tree=ET.fromstring(h.pin(netpath));manifest=sig_manifest_files(h.read(netpath.parent/'sig_manifest.json'))
    node=tree.find("./signalControllers/signalController[@no='16']")
    name=node.get('supplyFile2').removeprefix('#data#');sig=netpath.parent/name
    assert hashlib.sha256(h.pin(sig)).hexdigest()==manifest[name]
    programs={'16':clock.sig_program_from_file('16',sig,int(node.get('progNo')),sha256=manifest[name])}
    heads={int(n.get('lane').split()[1]):float(n.get('pos')) for n in tree.findall('./signalHeads/signalHead')
           if n.get('lane').split()[0]=='1210012600'}
    assert set(heads)=={1,2,3,4}
    h.LINKS={'SC16_N':1210012600};rows=[]
    def stock(raw):
        r=raw['vehicle_records'];assert r['complete']
        return Counter(v['lane_no'] for v in r['records'] if v['link_no']==1210012600 and v['position_m']<=heads[v['lane_no']])
    previous=stock(h.read(h.ORIGINAL/'state_001800.json'))
    first=dict(previous)
    for end in (1950,2100,2250,2400):
        raw=h.read(h.ORIGINAL/f'state_{end:06}.json');current=stock(raw)
        counts,events=h.heads_and_entries(h.ORIGINAL,end)
        exits={x['lane']:x['crossings'] for x in counts['SC16_N']['rows']}
        log=raw['obs150']['signal_log']
        scoped={**log,'scs':['16'],'start':{k:v for k,v in log['start'].items() if k.startswith('16-')},
                'events':[e for e in log['events'] if e[1]=='16']}
        w=clock.windows(scoped,programs,raw['obs150']['window'],network_dir=Path(raw['network_path']).parent)
        assert w['16-7']['complete']
        green=sum(hi-lo for lo,hi in w['16-7']['green'])
        rows.append(dict(start_sec=end-150,end_sec=end,stock_before=dict(previous),stock_after=dict(current),
                         head_departures=exits,left_green_sec=green,left_achieved_veh_h=3600*exits[4]/green,
                         left_net_arrivals=exits[4]+current[4]-previous[4],
                         total_net_arrivals=sum(exits.values())+sum(current.values())-sum(previous.values())))
        previous=current
    n=sum(r['total_net_arrivals'] for r in rows);left=sum(r['left_net_arrivals'] for r in rows)
    assert n>0 and 0<left<n and all(r['total_net_arrivals']>=0 and r['left_net_arrivals']>=0 for r in rows)
    # Fixed600s support for composition; conservative min of the last2 actual-green windows for service.
    beta=left/n;rate=min(r['left_achieved_veh_h'] for r in rows[-2:])
    cfg,_,_=pickle.loads(h.pin(A/'citysplit287/forecast2400/initial.pickle'))
    names=['SC16_N_SC12_to_S_SC109','SC16_N_SC12_to_W_SC7','SC16_N_SC12_to_E']
    old={m:cfg.network.urban_movements[m]['beta'] for m in names}
    scale=(1-beta)/(old[names[0]]+old[names[1]])
    new={names[0]:old[names[0]]*scale,names[1]:old[names[1]]*scale,names[2]:beta}
    assert abs(sum(new.values())-1)<1e-12
    for p in (HERE/'prepare.py',A/'city_loss322/README.md',
              A.parent.parent/'upstream_worklog/02_urban_b2/diag_c3_r2/C3V2_PROPOSAL.md'):h.pin(p)
    report=dict(status='prepared_single_past_aggregate_candidate',cutoff_sec=2400,fit_start_sec=1800,
        network_sha256=hashlib.sha256(netpath.read_bytes()).hexdigest(),rows=rows,initial_terminal_lanes=first,
        net_arrivals=n,left_net_arrivals=left,beta_before=old,beta_after=new,
        service_before_veh_h=cfg.network.movement_capacity_by_movement_veh_h[names[2]],service_after_veh_h=rate,
        service_support_ends=[r['end_sec'] for r in rows[-2:]],source_pins=h.PINS,
        limits=['Terminal-lane net arrival composition includes net lateral exchanges and is an aggregate prior, not per-vehicle intent.',
            'Known current route/lane tags have priority; no NULL vehicle is assigned a future static decision.',
            'Right/through relative split is inherited because their shared-lane heads do not identify both separately.',
            'Past achieved green discharge is a conservative local service candidate, not universal saturation.',
            'Upstream SC12 supply, existing ETA, demand and finite receiving remain unchanged.'],
        candidate_sets=1,future_target_inputs=False,production_adopted=False)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('PAST600',n,left,'BETA',beta,'SERVICE',rate,'OLD',old)

if __name__=='__main__':main()
