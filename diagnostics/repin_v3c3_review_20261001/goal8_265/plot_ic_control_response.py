"""Four IC/direction panels from closed native runs, with inspectable caches.

No simulation, model evaluation, calibration or changes to existing evidence.
"""
import bisect
import csv
import hashlib
import json
import math
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = HERE / 'ic_control_response900_8100'
OUT.mkdir(exist_ok=True)
REF = json.loads((HERE / 'warmup_excluded900_8100_no_west.json').read_bytes())
SELECTED = ROOT / 'diagnostics/sdmpc_n31_20260924/integration_20260926/selected'
GEOPATH = SELECTED / 'port_gain/geometry.json'
GEO = json.loads(GEOPATH.read_bytes())
NETWORK = SELECTED / 'network/native_seed29.inpx'
CTRL = Path('D:/VISSIM_runs/20261006_urban_storage40_fixed90_s29_9000/sdmpc')
ACTION = CTRL / 'action_sdmpc31_sdmpc9000_s29.csv'
START, END, BIN = 900., 8100., 150.
EDGES = [START + BIN*i for i in range(49)]
SITES = [
    dict(key='west_seocho', road='FW_W', ic='Seocho IC', ramps=[10480,10482]),
    dict(key='west_yangjae', road='FW_W', ic='Yangjae IC', ramps=[10646,10644]),
    dict(key='east_seocho', road='FW_E', ic='Seocho IC', ramps=[10490,10484]),
    dict(key='east_yangjae', road='FW_E', ic='Yangjae IC', ramps=[10639,10681]),
]
CHAIN = {str(r['link']): (road, r['offset_m']) for road, rows in GEO['chains'].items() for r in rows}
RAMPS = {str(r['connector']): r for r in GEO['boundaries'] if r['kind']=='ramp'}
OFFRAMPS = {str(r['connector']): r for r in GEO['boundaries'] if r['kind']=='offramp'}
CELL_EDGES = {road: [c['end_m'] for c in GEO['cells'] if c['road']==road] for road in ('FW_E','FW_W')}
CELL_TO_SITE = {}
RAMP_TO_SITE = {}
for i, site in enumerate(SITES):
    site['cells'] = [RAMPS[str(r)]['to_cell'] for r in site['ramps']]
    site['geometry'] = [c for c in GEO['cells'] if c['road']==site['road'] and c['cell'] in site['cells']]
    site['lane_km'] = sum(c['lane_km'] for c in site['geometry'])
    for cell in site['cells']:
        assert (site['road'],cell) not in CELL_TO_SITE
        CELL_TO_SITE[site['road'],cell] = i
    for ramp in site['ramps']:
        RAMP_TO_SITE[str(ramp)] = i


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def extract(arm):
    source = Path(REF['arms'][arm]['fzp_source'])
    pin = dict(path=str(source), bytes=source.stat().st_size, mtime_ns=source.stat().st_mtime_ns)
    assert pin['bytes'] == REF['arms'][arm]['fzp_size']
    cache = OUT / (arm+'_native_sites.json')
    if cache.exists():
        result = json.loads(cache.read_bytes())
        assert result['source']==pin and result['geometry_sha256']==sha(GEOPATH)
        return result
    # All 31 cell counts permit reconciliation with the already validated FW_E/W TTT.
    stamps = []
    frames = []
    merge_events = []
    prev_ramps, curr_ramps = {}, {}
    stamp = None
    count = [0]*4
    speed_sum = [0.]*4
    all_fw = [0,0]
    rows = 0
    seen_merges = set()
    ramp_disappearances = []
    bad_transitions = []
    frame_ids = set()
    # VISSIM's comment header includes legacy-encoded Korean paths; data are ASCII.
    with source.open(encoding='utf-8-sig', errors='replace') as f:
        for line in f:
            if line.startswith('$VEHICLE:'):
                columns = line.split(':',1)[1].strip().split(';')
                assert columns[:7] == ['SIMSEC','NO','LANE\\LINK\\NO','LANE\\INDEX','POS','POSLAT','SPEED']
                continue
            if line.startswith(('*','$')) or not line.strip():
                continue
            p = line.split(';',7)
            t = float(p[0])
            if t != stamp:
                if stamp is not None:
                    stamps.append(stamp)
                    frames.append(dict(n=count, speed_sum=speed_sum, freeway_n=all_fw))
                    if t >= END:
                        break
                    assert abs(t-stamp-5) < 1e-7
                    # Vehicles that disappear from a ramp are not counted as merges.
                    for vid, val in prev_ramps.items():
                        if vid not in frame_ids:
                            ramp_disappearances.append([stamp,vid,val[0]])
                prev_ramps, curr_ramps = curr_ramps, {}
                frame_ids = set()
                count, speed_sum, all_fw = [0]*4,[0.]*4,[0,0]
                stamp = t
            rows += 1
            vid, link = int(p[1]), p[2].strip()
            frame_ids.add(vid)
            position = float(p[4])
            if link in RAMP_TO_SITE:
                curr_ramps[vid] = (link,t,position)
            if vid in prev_ramps and link != prev_ramps[vid][0]:
                rlink, prior_t, prior_pos = prev_ramps[vid]
                boundary = RAMPS[rlink]
                crossing_kind=None
                if link in CHAIN and CHAIN[link][0]==boundary['road']:
                    distance = CHAIN[link][1]+position
                    assert distance >= boundary['chain_pos_m']-0.5
                    crossing_kind='mainline_observed'
                elif link in OFFRAMPS:
                    exit_boundary=OFFRAMPS[link]
                    if (exit_boundary['road']==boundary['road']
                            and exit_boundary['from_link']==boundary['to_link']
                            and exit_boundary['chain_pos_m']>=boundary['chain_pos_m']):
                        distance=exit_boundary['chain_pos_m']
                        crossing_kind='short_mainline_path_between_connectors'
                if crossing_kind:
                    event_key=(vid,rlink,t)
                    assert event_key not in seen_merges
                    seen_merges.add(event_key)
                    # Crossing is known only in (prior_t,t]; retain bounds, no artificial substep precision.
                    merge_events.append([t,prior_t,int(rlink),vid,distance,crossing_kind])
                else:
                    bad_transitions.append([t,vid,rlink,link])
            if link in CHAIN:
                road, offset = CHAIN[link]
                all_fw[0 if road=='FW_E' else 1] += 1
                cell = min(bisect.bisect_right(CELL_EDGES[road],offset+position),30)
                site_index = CELL_TO_SITE.get((road,cell))
                if site_index is not None:
                    speed = float(p[6])
                    assert math.isfinite(speed) and speed >= 0
                    count[site_index] += 1
                    speed_sum[site_index] += speed
    assert abs(stamps[-1]-8095.1)<1e-7
    assert not bad_transitions, bad_transitions[:10]
    expected = json.loads((HERE/'current_native_analysis_to8100'/arm/'area_metrics.json').read_bytes())
    assert rows == expected['sampling']['fzp_rows']
    assert len(stamps) == expected['sampling']['fzp_snapshots']
    reconciliation = {}
    for road,j in [('FW_E',0),('FW_W',1)]:
        # Match existing TTT convention: linear interpolation at900, hold final4.9s.
        at = bisect.bisect_right(stamps,START)-1
        frac=(START-stamps[at])/(stamps[at+1]-stamps[at])
        nstart=frames[at]['freeway_n'][j]*(1-frac)+frames[at+1]['freeway_n'][j]*frac
        ts=[START]+stamps[at+1:]+[END]
        ns=[nstart]+[r['freeway_n'][j] for r in frames[at+1:]]+[frames[-1]['freeway_n'][j]]
        ttt=sum((b-a)*(u+v)/7200 for a,b,u,v in zip(ts,ts[1:],ns,ns[1:]))
        assert abs(ttt-REF['arms'][arm]['domain'][road])<1e-7
        reconciliation[road] = ttt
    hist = []
    for i, site in enumerate(SITES):
        d, v, q = [], [], []
        for start,end in zip(EDGES,EDGES[1:]):
            samples = [r for t,r in zip(stamps,frames) if start<=t<end]
            assert len(samples)==30
            n=sum(s['n'][i] for s in samples)
            d.append(n/30/site['lane_km'])
            v.append(sum(s['speed_sum'][i] for s in samples)/n if n else None)
            q.append(sum(start<=e[0]<end and e[2] in site['ramps'] for e in merge_events)*3600/BIN)
        hist.append(dict(key=site['key'], density=d, speed=v, merge_vph=q))
    result=dict(source=pin, geometry_sha256=sha(GEOPATH), time_edges=EDGES,
        sites=hist, frame_times=stamps, frames=frames, merge_events=merge_events,
        audit=dict(rows=rows, frames=len(stamps), last_native_sec=stamps[-1],
            freeway_ttt_reconciliation_veh_h=reconciliation,
            bad_ramp_to_other_transitions=bad_transitions,
            observed_ramp_disappearances=ramp_disappearances,
            merge_timing='First observed mainline frame; true crossing in preceding5s interval',
            merge_events_after900=sum(START<=e[0]<END for e in merge_events),
            mainline_skipped_events_after900=sum(START<=e[0]<END and e[5]=='short_mainline_path_between_connectors' for e in merge_events),
            aggregation='30 native5s snapshots per150s; density time-average stock/lane-km; speed vehicle-record weighted'))
    cache.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(arm+': '+json.dumps(result['audit']),flush=True)
    return result


def commands():
    rows=list(csv.DictReader(ACTION.open(encoding='utf-8-sig')))
    ds={d.get('no'):d for d in ET.parse(NETWORK).getroot().iter('desSpeedDecision')}
    sign_positions={}
    for row in rows:
        if row['kind']=='vsl' and row['sim_sec']=='900':
            node=ds[row['dsd_no']]
            link=node.get('lane').split()[0]
            road,offset=CHAIN[link]
            sign_positions[row['id']]=(road,offset+float(node.get('pos')))
    rm_rows={f'RM_C{r}':[] for site in SITES for r in site['ramps']}
    vsl_rows={s:[] for s in sign_positions}
    for row in rows:
        if row['kind']=='ramp_meter': rm_rows[row['id']].append(row)
        elif row['kind']=='vsl':
            speed=float(row['speed_kph'])
            assert row['readback'] and all(float(x)==speed for x in row['readback'].split('|'))
            vsl_rows[row['id']].append(row)
    out=[]
    for site in SITES:
        first=min(RAMPS[str(r)]['chain_pos_m'] for r in site['ramps'])
        vsl_id=max((s for s,(road,p) in sign_positions.items() if road==site['road'] and p<=first),key=lambda s:sign_positions[s][1])
        site['vsl_sign']=dict(id=vsl_id,chain_position_m=sign_positions[vsl_id][1],
                              scope='Nearest controlled VSL sign upstream of first merge; actual network XML position')
        green=[[],[]]; nominal=[]; service=[]; vsl=[]
        for t in EDGES[:-1]:
            chosen=[max((x for x in rm_rows[f'RM_C{r}'] if float(x['sim_sec'])<=t),key=lambda x:float(x['sim_sec'])) for r in site['ramps']]
            for k,x in enumerate(chosen):
                g=float(x['green_sec'])
                assert 0<=g<=10
                # The writer's nominal900 full-green scale is not physical merge capacity.
                assert abs(float(x['rate_vph'])-90*g)<1e-6
                green[k].append(g)
            nominal.append(sum(float(x['rate_vph']) for x in chosen))
            meta=[dict(p.split('=',1) for p in x['metadata'].split(';') if '=' in p) for x in chosen]
            service.append(sum(float(m['group_rate_vph']) for m in meta))
            signrow=max((x for x in vsl_rows[vsl_id] if float(x['sim_sec'])<=t),key=lambda x:float(x['sim_sec']))
            vsl.append(float(signrow['speed_kph']))
        out.append(dict(key=site['key'],green=green,nominal_rm_vph=nominal,modeled_service_vph=service,vsl=vsl))
    evidence=json.loads((HERE/'current_native_analysis_to8100/sdmpc/execution.json').read_bytes())
    assert evidence['native_execution_passed'] and evidence['process_exit_verified']
    return out


def plot(data, command, mode='green'):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    from matplotlib.lines import Line2D
    from matplotlib.patches import FancyBboxPatch
    import numpy as np
    for name in ('times.ttf','timesbd.ttf','timesi.ttf','timesbi.ttf'):
        font_manager.fontManager.addfont('C:/Windows/Fonts/'+name)
    plt.rcParams.update({'font.family':'Times New Roman','font.size':13,'svg.fonttype':'none','pdf.fonttype':42,'axes.linewidth':.7})
    fontpath=font_manager.findfont('Times New Roman',fallback_to_default=False)
    assert Path(fontpath).name.lower()=='times.ttf'
    blue,red,grey='#137CCD','#D43E35','#8E8E8E'
    fig,axs=plt.subplots(4,4,figsize=(15.8,9.5),sharex=True,sharey='row')
    fig.subplots_adjust(left=.073,right=.842,top=.862,bottom=.127,hspace=.16,wspace=.24)
    x=np.array(EDGES)/60
    midpoint=(x[:-1]+x[1:])/2
    density_max=max(max(s['density']) for a in data.values() for s in a['sites'])
    flow_max=max(max(s['merge_vph']) for a in data.values() for s in a['sites'])
    flow_top=max(2000,math.ceil(flow_max/1000)*1000)
    for j,site in enumerate(SITES):
        for i in range(4):
            ax=axs[i,j]
            ax.spines[['top','right']].set_visible(False)
            ax.spines[['left','bottom']].set_color('#777777')
            ax.grid(True,color='#EAEAEA',lw=.55)
            ax.tick_params(length=3,pad=3,labelsize=11)
            ax.set_xlim(15,135)
            ax.set_xticks([15,45,75,105,135])
            if j: ax.tick_params(labelleft=False)
        ax=axs[0,j]
        if mode=='green':
            for k,ls in enumerate(('-', (0,(4,2)))):
                ax.stairs(command[j]['green'][k],x,color=blue,ls=ls,lw=1.25,baseline=None)
            ax.set_ylim(0,10.7);ax.set_yticks([0,2,4,6,8,10])
            actual_ax=ax.twinx()
            actual_ax.plot(midpoint,data['sdmpc']['sites'][j]['merge_vph'],color=red,lw=1.05)
            actual_ax.set_ylim(0,flow_top)
            actual_ax.spines[['top','left','bottom']].set_visible(False)
            actual_ax.spines['right'].set_color(red)
            actual_ax.tick_params(axis='y',colors=red,labelsize=10,length=2)
            actual_ax.set_yticks([0,flow_top/2,flow_top])
            if j==3: actual_ax.set_ylabel('Actual merge flow [veh/h]',color=red,labelpad=7,fontsize=11)
        else:
            ax.stairs(command[j]['nominal_rm_vph'],x,color=blue,lw=1.3,baseline=None)
            ax.plot(midpoint,data['sdmpc']['sites'][j]['merge_vph'],color=red,lw=1.05)
            ax.set_ylim(0,flow_top); ax.set_yticks(np.arange(0,flow_top+1,1000))
        ax.text(.03,.05,' / '.join(str(r) for r in site['ramps']),transform=ax.transAxes,fontsize=9.5,color='#555555',bbox=dict(facecolor='white',edgecolor='none',alpha=.8,pad=1))
        axs[1,j].stairs(command[j]['vsl'],x,color=blue,lw=1.4,baseline=None)
        axs[1,j].set_ylim(50,115);axs[1,j].set_yticks([50,70,90,110])
        for arm,c in [('nc',grey),('sdmpc',blue)]:
            axs[2,j].plot(midpoint,data[arm]['sites'][j]['density'],color=c,lw=1.2)
            axs[3,j].plot(midpoint,data[arm]['sites'][j]['speed'],color=c,lw=1.2)
        axs[2,j].set_ylim(0,math.ceil(density_max/20)*20)
        axs[3,j].set_ylim(0,125);axs[3,j].set_yticks([0,40,80,120])
        axs[3,j].set_xlabel('Simulation time [min]',fontsize=13)
        pos=axs[0,j].get_position()
        box=FancyBboxPatch((pos.x0,.878),pos.width,.034,boxstyle='round,pad=0.0015,rounding_size=0.005',transform=fig.transFigure,facecolor='#F4F4F4',edgecolor='#333333',lw=.85)
        fig.add_artist(box)
        fig.text(pos.x0+pos.width/2,.895,site['ic'],ha='center',va='center',fontsize=17)
    for start,title in [(0,'Westbound'),(2,'Eastbound')]:
        left=axs[0,start].get_position().x0;right=axs[0,start+1].get_position().x1
        fig.add_artist(FancyBboxPatch((left,.924),right-left,.041,boxstyle='round,pad=0.0015,rounding_size=0.005',transform=fig.transFigure,facecolor='#DEDEDE',edgecolor='#333333',lw=.9))
        fig.text((left+right)/2,.9445,title,ha='center',va='center',fontsize=19,weight='bold')
    axs[0,0].set_ylabel('RM green time\n[s / 10-s cycle]' if mode=='green' else 'Metering rate\n[veh/h]',fontsize=14)
    axs[1,0].set_ylabel('VSL command\n[km/h]',fontsize=14)
    axs[2,0].set_ylabel('Mean density\n[veh/km/lane]',fontsize=14)
    axs[3,0].set_ylabel('Mean speed\n[km/h]',fontsize=14)
    legendx=.913 if mode=='green' else .858
    fontsize=11.4
    if mode=='green':
        handles=[Line2D([],[],color=blue,lw=1.3,label='Ramp 1 green'),Line2D([],[],color=blue,lw=1.3,ls='--',label='Ramp 2 green'),Line2D([],[],color=red,lw=1.2,label='Actual merge')]
    else:
        handles=[Line2D([],[],color=blue,lw=1.3,label='Nominal RM command'),Line2D([],[],color=red,lw=1.2,label='Actual merge')]
    fig.legend(handles=handles,loc='upper left',bbox_to_anchor=(legendx,.85),frameon=False,fontsize=fontsize,handlelength=1.7,handletextpad=.45,borderaxespad=0)
    fig.legend(handles=[Line2D([],[],color=blue,lw=1.3,label='Applied command')],loc='upper left',bbox_to_anchor=(.865,.652),frameon=False,fontsize=fontsize,handlelength=1.7,handletextpad=.45,borderaxespad=0)
    for y in (.46,.275):
        fig.legend(handles=[Line2D([],[],color=grey,lw=1.3,label='No Control'),Line2D([],[],color=blue,lw=1.3,label='Proposed Controller')],loc='upper left',bbox_to_anchor=(.865,y),frameon=False,fontsize=fontsize,handlelength=1.7,handletextpad=.45,borderaxespad=0)
    foot='Native VISSIM data | Seed 29 | 900–8100 s | 150-s bins | IC density/speed: the two on-ramp merging cells.'
    fig.text(.073,.070,foot,fontsize=10.5,color='#555555')
    foot2='RM: each ramp\'s applied green and their combined actual mainline entry flow (right axis). VSL: the sign before the first merge.' if mode=='green' else 'Nominal RM command = 900 × green/10 per ramp; this writer scale is NOT a physical flow cap. Actual merge = FZP ramp-to-mainline transitions.'
    fig.text(.073,.045,foot2,fontsize=10.3,color='#555555')
    fig.text(.073,.020,'The tested strategy uses SDMPC signals/RM with fixed VSL90 near eastbound Seocho IC; these panels do not isolate individual lever effects.',fontsize=10.2,color='#555555')
    basename='ic_control_response' if mode=='green' else 'ic_control_response_nominal_rate'
    for ext in ('png','svg','pdf'):
        fig.savefig(OUT/(basename+'.'+ext),dpi=220,facecolor='white',bbox_inches='tight',pad_inches=.08)
    plt.close(fig)
    return fontpath


def main():
    # Reduce CPU scheduling priority while reading closed files once.
    if sys.platform=='win32':
        import ctypes
        ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(),0x4000)
    data={arm:extract(arm) for arm in ('nc','sdmpc')}
    command=commands()
    with (OUT/'series150s.csv').open('w',newline='',encoding='utf-8-sig') as f:
        fields=['start_sec','end_sec','site','road','ramp1','ramp2','green1_sec','green2_sec','nominal_rm_command_vph','modeled_service_vph','vsl_kph','nc_merge_vph','control_merge_vph','nc_density','control_density','nc_speed_kph','control_speed_kph']
        w=csv.DictWriter(f,fields);w.writeheader()
        for j,site in enumerate(SITES):
            for b,(start,end) in enumerate(zip(EDGES,EDGES[1:])):
                n,c=data['nc']['sites'][j],data['sdmpc']['sites'][j]
                w.writerow(dict(start_sec=start,end_sec=end,site=site['ic'],road=site['road'],ramp1=site['ramps'][0],ramp2=site['ramps'][1],green1_sec=command[j]['green'][0][b],green2_sec=command[j]['green'][1][b],nominal_rm_command_vph=command[j]['nominal_rm_vph'][b],modeled_service_vph=command[j]['modeled_service_vph'][b],vsl_kph=command[j]['vsl'][b],nc_merge_vph=n['merge_vph'][b],control_merge_vph=c['merge_vph'][b],nc_density=n['density'][b],control_density=c['density'][b],nc_speed_kph=n['speed'][b],control_speed_kph=c['speed'][b]))
    if '--extract-only' in sys.argv:
        print('EXTRACTION_DONE',flush=True)
        return
    font=plot(data,command,'green')
    plot(data,command,'nominal')
    summary=dict(evaluation_sec=[START,END],bin_sec=BIN,font=font,sites=SITES,
        sources={a:d['source'] for a,d in data.items()},geometry_sha256=sha(GEOPATH),network_sha256=sha(NETWORK),action_csv_sha256=sha(ACTION),
        native_execution_evidence=str(HERE/'current_native_analysis_to8100/sdmpc/execution.json'),
        execution='Existing native LDP and VSL application-readback validation reused; LSA coverage failure preserved.',
        metrics={'density':'Mean of30 native5s cell inventories / physical lane-km of2 merge cells',
            'speed':'Vehicle-record weighted mean native speed in same2 cells',
            'actual_merge':'Same-ID ramp-to-mainline transitions plus proven short mainline paths between on/off-ramp connectors /150s times3600',
            'nominal_rm':'Writer scaling900 * green/10 per ramp, summed; NOT physical cap or achieved flow',
            'modeled_service':'Model service table metadata, never labeled actual flow',
            'vsl':'Actual applied/read-back command at nearest sign upstream of first merge, positions from network XML'},
        limitations=['No rho_crit reference: no unique observed threshold established for these pooled sites.',
            'Sampled crossing times have up to5s interval uncertainty; no removal or end-residual counted as merge.',
            'Native5s can skip the short mainline path from10480 to10491 and10646 to10638. These are counted only when both connectors join the same physical mainline link in forward order.',
            'The preceding5s of the900 boundary and final4.9s are censored for crossing observations.',
            'No causal attribution to RM or VSL alone: signals/offset/RM jointly differ; VSL is fixed.',
            'Site names are used instead of upstream/downstream because travel direction reverses.',
            'Only the same eight original physical ramps are grouped for plotting; no controller grouping changed.'])
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print('PLOTS_DONE '+str(OUT),flush=True)


if __name__=='__main__':
    main()
