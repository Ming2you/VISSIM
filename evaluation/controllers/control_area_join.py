"""Auditable physical-turn joins for accepted model movement transfers.

This module does not infer equal route weights or count scheduled/intended flow.
Its consumers must supply actual accepted vehicles and an explicit cohort ledger.
"""
from __future__ import annotations

from collections import Counter, defaultdict

from evaluation.controllers.control_area_objective import physical_membership_from_ledger


def turn_membership(turn, physical):
    links=[str(turn[key]) for key in ('from_link','connector','to_link')]
    missing=[link for link in links if link not in physical]
    if missing:raise ValueError(f'Physical turn links absent from control area: {missing}')
    mask=[physical[link] for link in links]
    edges=[{'source':a,'target':b,'from_inside':ia,'to_inside':ib}
           for a,b,ia,ib in zip(links,links[1:],mask,mask[1:]) if ia!=ib]
    return {'from_link':links[0],'connector':links[1],'to_link':links[2],
            'source_inside':mask[0],'connector_inside':mask[1],'target_inside':mask[2],
            'crossing_edges':edges,'outward_crossings_per_vehicle':sum(a and not b for a,b in zip(mask,mask[1:])),
            'inward_crossings_per_vehicle':sum(not a and b for a,b in zip(mask,mask[1:]))}


def build_movement_join(cfg, detectors, turns_document, membership_document, *, physical_successors=None):
    physical=physical_membership_from_ledger(membership_document)
    topology={str(t['connector']):(str(t['from_link']),str(t['to_link']))
              for t in membership_document['connector_transitions']}
    # The membership ledger records only boundary connectors. Interior physical
    # turns are still fully covered by the same exhaustive membership partition.
    by_signal=defaultdict(list)
    for turn in turns_document['turns']:
        connector=str(turn['connector'])
        if connector in topology and topology[connector]!=(str(turn['from_link']),str(turn['to_link'])):
            raise ValueError(f'Canonical turn and physical connector endpoints differ: {connector}')
        by_signal[str(turn['sc'])].append(turn)
    movement_support=defaultdict(set)
    for link, rows in detectors.get('link_to_movements',{}).items():
        for row in rows:
            movement_support[str(row['movement'])].add(str(link))
    origin_support=detectors.get('link_to_origins',{})
    def first_storage_support(link):
        frontier=[(str(link),[str(link)])];seen=set();found=[]
        for _ in range(7):
            next_frontier=[]
            for current,path in frontier:
                if current in seen:continue
                seen.add(current)
                supports=[str(x) for x in origin_support.get(current,[])]
                if supports:
                    found.append((supports,path))
                    continue
                for connector,target in (physical_successors or {}).get(current,[]):
                    if target not in seen:next_frontier.append((str(target),path+[str(connector),str(target)]))
            if not next_frontier:break
            frontier=next_frontier
        return sorted({s for supports,_ in found for s in supports}),[path for _,path in found]
    output={}
    for name,spec in cfg.network.urban_movements.items():
        signal=str(spec.get('signal',''))
        approach=str(spec.get('approach',''))
        exit_leg=str(spec.get('exit',''))
        heading=exit_leg.split('_')[0]
        receiver=str(spec.get('receiving_link',''))
        ramp=str(spec.get('ramp',''))
        off=str(spec.get('off_ramp',''))
        source_stock='storage:'+str(cfg.network.off_ramp_storage_link.get(off,'')) if off else 'movement:'+name
        target_stock='ramp:'+ramp if ramp else 'storage:'+receiver if receiver else None
        candidates=[]; source_choices=[]
        for turn in by_signal.get(signal,[]):
            source=str(turn['from_link'])
            leg_match=f'{signal}·{approach}' in turn.get('legs',[])
            detector_match=source in movement_support[name]
            if not (leg_match or detector_match):
                continue
            supports,support_paths=first_storage_support(str(turn['to_link']))
            source_choices.append({'from_link':str(turn['from_link']),'connector':str(turn['connector']),
                'to_link':str(turn['to_link']),'heading':turn.get('heading'),
                'first_destination_storages':supports,'destination_support_paths':support_paths})
            heading_match=str(turn.get('heading',''))==heading
            destination_match=receiver in supports if receiver else False
            if not (heading_match or destination_match):continue
            row=turn_membership(turn,physical)
            destination_status=('not_in_detector_support' if not supports else
                                'supported' if receiver in supports else 'different_model_storage')
            row.update({'canonical_class':turn['class'],'signal':signal,'canonical_source_legs':turn.get('legs',[]),
                        'source_evidence':{'canonical_approach_leg':leg_match,'runtime_detector_stopline':detector_match},
                        'exit_evidence':{'canonical_heading_matches_exit_compass':heading_match,
                                         'actual_destination_storage_matches':destination_match},
                        'destination_support_status':destination_status,'destination_storage_support':supports,
                        'destination_support_paths':support_paths,
                        'weight_source':None,'weight':None,
                        'canonical_declared_flow_veh_h':turn.get('flow_veh_h')})
            candidates.append(row)
        # Multiple legs can describe one physical connector. Count it once.
        candidates=list({row['connector']:row for row in candidates}.values())
        rejected=[r for r in candidates if r['destination_support_status']=='different_model_storage']
        candidates=[r for r in candidates if r['destination_support_status']!='different_model_storage']
        patterns={(r['source_inside'],r['connector_inside'],r['target_inside']) for r in candidates}
        if not candidates:
            status='no_match';reason='No canonical turn has this model signal, supported source approach, and physical exit heading.'
        elif len(candidates)==1:
            status='unique';reason=None
        elif len(patterns)==1:
            status='same_transition';reason=None
        else:
            status='mixed_transition';reason='Candidate physical turns cross different area boundaries; accepted branch flow weights or separate movements are required.'
        resolved=status in ('unique','same_transition')
        first=candidates[0] if resolved else None
        output[name]={'status':status,'physical_turns':candidates,'model_source_stock':source_stock,
                      'rejected_destination_candidates':rejected,
                      'source_approach_physical_choices':source_choices if not resolved else [],
                      'model_target_stock':target_stock,'kind':spec.get('kind'),'origin':spec.get('origin'),
                      'merged_from':spec.get('merged_from',[name]),'unresolved_reason':reason,
                      'source_inside':first['source_inside'] if first else None,
                      'target_inside':first['target_inside'] if first else None,
                      'outward_crossings_per_accepted_vehicle':first['outward_crossings_per_vehicle'] if first else None,
                      'inward_crossings_per_accepted_vehicle':first['inward_crossings_per_vehicle'] if first else None,
                      'arrival_stopline_inside':first['source_inside'] if first else None,
                      'requires_arrival_membership_transfer':True,
                      'timing_assumption':'Map accepted movement departure to the physical turn crossing; storage-to-movement arrival reaches its canonical stopline. Connector travel timing is an approximation.'}
    return {'schema':'control-area-movement-join/v1','inside_links':sum(physical.values()),
            'by_movement':output,'counts':dict(Counter(r['status'] for r in output.values())),
            'rules':{'weights':'No equal weighting or implicit external/internal classification.',
                     'flow':'Use actual accepted movement transfer, never demand, intended service, or configured beta alone.',
                     'arrival':'Mixed origin storage requires cohort propagation to the physical stopline before movement departure.',
                     'external_excursion':'The connector membership participates: inside→outside→inside contains an exit and an entry.',
                     'unmatched_positive_flow':'Coverage error; extend physical routing/model branch representation before using one common area objective.'}}


def route_contract(join):
    """Convert only proven joins; unresolved routes remain explicit None."""
    result={}
    for name,row in join['by_movement'].items():
        known=row['status'] in ('unique','same_transition')
        source=row['source_inside'] if known else None
        target=row['target_inside'] if known else None
        result['movement:'+name]={'status':row['status'],'source_inside':source,'target_inside':target,
            'inside_to_inside':float(target) if known else None,'outside_to_inside':float(target) if known else None,
            'outward_crossings_per_vehicle':row['outward_crossings_per_accepted_vehicle'],
            'inward_crossings_per_vehicle':row['inward_crossings_per_accepted_vehicle'],
            'physical_turns':row['physical_turns'],'unresolved_reason':row['unresolved_reason']}
        result['arrival:'+name]={'status':row['status'],'source_inside':None,'target_inside':source,
            'inside_to_inside':float(source) if known else None,'outside_to_inside':float(source) if known else None,
            'timing_assumption':'Arrival at the modeled stopline; mixing and travel time are model approximations.'}
    return result
