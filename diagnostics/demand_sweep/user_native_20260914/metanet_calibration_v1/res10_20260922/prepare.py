"""Freeze this demand-holdout protocol using training data only."""
import json
import sys
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace

B=Path(__file__).resolve().parent
CAL=B.parent
ROOT=CAL.parents[3]
sys.path[:0]=[str(ROOT),str(ROOT/'.review-deps'),str(CAL)]
from boundary_factory import ObservationData
from canonical_harness import DEFAULT_CONFIG, sha256, PARAMETER_BOUNDS
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.evaluate_response import refresh_free_speed


def load(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(p,v):
    with Path(p).open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2,allow_nan=False)


def main():
    data=ObservationData(B/'p100_observations')
    geometry=data.geometry
    parent={(c['road'],c['cell']):c['parent_cell'] for c in geometry['cells']}
    areas=defaultdict(float)
    for c in geometry['cells']: areas[c['road'],c['parent_cell']]+=c['lane_km']
    aggregate={}
    for t,rows in data.cells.items():
        if not 0<t<=900: continue
        groups=defaultdict(list)
        for row in rows:groups[row['road'],parent[row['road'],row['cell']]].append(row)
        aggregate[t]=[]
        for (road,i),rs in groups.items():
            n=sum(r['n_veh'] for r in rs)
            aggregate[t].append(dict(time_s=t,road=road,cell=i,n_veh=n,
                v_kmh=sum(r['n_veh']*(r['v_kmh'] or 0) for r in rs)/n if n else None,
                rho_veh_per_km_lane=n/areas[road,i]))
    parent_data=SimpleNamespace(cells=aggregate,geometry={**geometry,'cells':[dict(road=r,cell=i) for r,i in areas]})
    fitbase=B/'free_speed_refresh';fitbase.mkdir()
    path=refresh_free_speed(parent_data,fitbase)
    config=load(path);config['freeway']['physical_integration_step_sec']=1
    save(B/'fit_config.json',config)
    baseline=load(DEFAULT_CONFIG);baseline['freeway']['physical_integration_step_sec']=1
    # Baseline created by numerical preflight; verify rather than overwrite.
    if load(B/'baseline_config.json')!=baseline:raise ValueError('Baseline changed')
    def case(name,run,cutoffs):
        receipt=load(Path(run)/'run.json')
        network=Path(receipt['network'])
        return dict(id=name,observations=str((B/(name+'_observations')).relative_to(ROOT)).replace('\\','/'),
            run=str(run),network_sha256=sha256(network),cutoffs_s=[t+.1 for t in cutoffs])
    q=Path('D:/VISSIM_runs/20260922_both_off_half')
    times=[900,1800,2700,3600,4500,5400,6300,7200,8100]
    protocol=dict(schema='metanet-completed-demand-holdout/v1',seed=23,
        training=case('p100',q/'p100_nc9000/run',times),
        validation=[case('p90',q/'p90_nc9000/run',times),
            case('fw080_urban100',q/'fw080_urban100_nc9000/run',times),
            case('p80',q/'p80_retry1/run',[900,1800,2700,3600,4500]),
            case('p70',q/'p70/run',[900,1800,2700,3600,4500])],
        config=str((B/'fit_config.json').relative_to(ROOT)).replace('\\','/'),config_sha256=sha256(B/'fit_config.json'),
        baseline_config=str((B/'baseline_config.json').relative_to(ROOT)).replace('\\','/'),baseline_config_sha256=sha256(B/'baseline_config.json'),
        integration_step_sec=1,recording_interval_sec=5,fit_keys=list(PARAMETER_BOUNDS),
        fit_mode='conditioned_diagnostic',evaluation_modes=['conditioned_diagnostic','history_forecast'],
        normalization=dict(speed_kmh=20,density_veh_km_lane=10,flow_veh_h=1000),
        limitations=['All scenarios use seed23; different demand, not independent seed validation.',
            'Prior heatmaps were inspected. This is a frozen demand holdout, not a blind dataset.',
            'Fit physical dynamics with explicitly future-conditioned external boundary support; mainline states never reset.',
            'History forecasts use only cutoff state and past150s boundary observations plus known input timetable.',
            'No VSL/RM causal gain identification from these no-control runs.',
            'Freeway component only; observed external ramp/off boundaries, not full urban coupling or Omega TTT.',
            'One existing parameter family per direction; state-regime and lane interaction candidates not reintroduced without evidence.',
            'Synthetic conservation preflight requires1s integration on the unchanged minimum76m refined grid.'],
        adoption_rule='Require no physical failures and improvement in held-out dynamic/flow measures; no production promotion from aggregate score alone.')
    save(B/'PROTOCOL.json',protocol)
    print(json.dumps({'prepared':str(B/'PROTOCOL.json'),'free_speed_rows':len(load(fitbase/'free_speed_evidence.json'))}))


def literature_main():
    """One frozen comparison on the already extracted resolution10 data."""
    import copy
    import xml.etree.ElementTree as ET
    out=B/'boundary_literature_v1'
    data=ObservationData(B/'p100_observations')
    old=load(B/'PROTOCOL.json')
    previous=load(B/'fit_v1/parameters.json')['parameters']['by_direction']
    geometry=data.geometry
    network=Path(load(Path(old['training']['run'])/'run.json')['network'])
    xml=ET.parse(network)
    evidence={}
    for road in ('FW_E','FW_W'):
        cs=sorted((c for c in geometry['cells'] if c['road']==road),key=lambda c:c['cell'])
        end=cs[-1];link=end['physical_pieces'][-1]['link']
        outgoing=[dict(connector=n.get('no'),**n.find('fromLinkEndPt').attrib)
            for n in xml.findall('./links/link') if n.find('fromLinkEndPt') is not None
            and n.find('fromLinkEndPt').get('lane').split()[0]==str(link)]
        # Interior ramp branches do not make the physical link end a receiver.
        tail_start=end['start_m']
        chain_start=next(p['offset_m'] for p in geometry['chains'][road] if p['link']==link)
        terminal_outgoing=[a for a in outgoing if float(a['pos'])+chain_start>=tail_start]
        if terminal_outgoing: raise ValueError('Terminal cell has an unmodeled outgoing connector')
        last=[r for t,rs in data.cells.items() for r in rs if r['road']==road and r['cell']==end['cell'] and r['n_veh']>=5 and r['v_kmh'] is not None]
        source=next(b['id'] for b in geometry['boundaries'] if b['road']==road and b['kind']=='source')
        evidence[road]=dict(terminal_link=link,terminal_cell=end,terminal_outgoing=terminal_outgoing,
            terminal_speed_min_kmh=min(r['v_kmh'] for r in last),
            observed_source_max_30s_vph=max(float(r['crossings'])*120 for (t,k),r in data.boundaries.items() if k==source),
            observed_terminal_max_30s_vph=max(float(r['terminal_exits_inferred'])*120 for (t,rr,c),r in data.flows.items() if rr==road and c==end['cell']),
            old_source_gate_vph=6937.,old_terminal_gate_vph=6937*end['effective_lanes']/4,
            interpretation='Physical network exit with no downstream cell; maxima are NOT sustained capacity estimates.')
    save(out/'boundary_evidence.json',dict(training_only=True,network_sha256=sha256(network),roads=evidence,
        source_policy='Observed/forecast admitted-interface supply, without a second desired-demand gate. Receiving/storage remain; rejected supply stays in explicit outside-component queue.',
        terminal_policy='Open physical network end: sending-limited, same density ghost rule. No origin-capacity reuse.'))
    base=load(B/'fit_config.json')
    for family in ('source_only','terminal_only','boundary','hadi','wang'):
        config=copy.deepcopy(base)
        config['freeway']['component_boundary']={'source':'legacy' if family=='terminal_only' else 'admitted_interface',
            'terminal':'legacy' if family=='source_only' else 'open_exit'}
        if family in ('hadi','wang'):
            config['freeway']['component_literature']=dict(family=family,
                relaxation_cells={road:[c['cell'] for c in geometry['cells'] if c['road']==road] for road in ('FW_E','FW_W')},
                initial={road:dict(literature_tau_sec=108.,nu_km2_h=35.,kappa_veh_km_lane=40.,
                    receiving_capacity_vphpl=2400.,receiving_wave_kmh=17.5,receiving_critical=30.,capacity_drop_fraction=0.) for road in ('FW_E','FW_W')})
        path=out/(family+'_config.json');save(path,config)
        if family.endswith('_only'): continue
        protocol=copy.deepcopy(old)
        protocol.update(config=str(path.relative_to(ROOT)).replace('\\','/'),config_sha256=sha256(path),
            baseline_config=str((B/'fit_config.json').relative_to(ROOT)).replace('\\','/'),baseline_config_sha256=sha256(B/'fit_config.json'),
            baseline_parameters=previous,initial_parameters=previous,
            comparison_family=family,
            include_source_boundary=True,
            limitations=old['limitations']+["Boundary semantics corrected; rejected interface flow remains visible.",
                "Hadi/Wang core equations on aggregated cells; nominal and controlled use the same command law, no model switch.",
                "Q/rho_c/w/theta are effective fitted coefficients, not independently identified physical capacity/drop.",
                "No native command pairs on this exact latest network; no control-gain certification."])
        if family in ('hadi','wang'):
            protocol['initial_parameters']=config['freeway']['component_literature']['initial']
            protocol['fit_keys']=['literature_tau_sec','nu_km2_h','kappa_veh_km_lane','receiving_capacity_vphpl','capacity_drop_fraction']
            if family=='hadi': protocol['fit_keys']+=['receiving_wave_kmh','receiving_critical']
            protocol['literature_equations']={'receiving':"Hadi fixed wave" if family=='hadi' else "Wang w'=Q'/(jam-rho_c), rho_c=Q/u_max; same triangular relation in free branch",
                'speed':'Paper command relaxation + convection + anticipation; previous merge and lane-drop deceleration disabled.',
                'scope':'All existing model VSL zones, fixed across commands; 31 cells per direction.',
                'flow_mapping':'Existing conserved per-cell mainline/off split; ramp flow independently accounted and deducted from shared receiving budget. Wang printed r-s addition not double-counted.',
                'capacity':'One per-lane family per direction; observed lane count varies by segment, jam storage unchanged.'}
        save(out/(family+'_protocol.json'),protocol)
    print(json.dumps({'prepared':str(out),'families':['boundary','hadi','wang'],'training_windows_per_road':9}))


if __name__=='__main__':literature_main() if '--literature' in sys.argv else main()
