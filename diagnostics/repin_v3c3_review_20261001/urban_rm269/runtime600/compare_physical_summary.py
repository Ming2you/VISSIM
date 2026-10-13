"""Compare all physical summary fields; report changed record counts separately."""
from copy import deepcopy
from evaluation.controllers.sdmpc_tangent_surrogate import check_scalar_upgrade


def compare(before,after):
    pair=[deepcopy(before),deepcopy(after)];counts=[]
    for item in pair:
        item.pop('diagnostic_transfer_witness',None);item.pop('frozen_context_token',None)
        observed={}
        for owner,row in item['quantities']['owners'].items():
            if 'accepted_event_count' in row:
                n=row.pop('accepted_event_count')
                assert isinstance(n,(float,int)) and n>=0 and int(n)==n
                observed['owner:'+owner]=n
        n=item['control_area']['event_count']
        assert isinstance(n,(float,int)) and n>=0 and int(n)==n
        item['control_area']['event_count']=0
        observed['control_area']=n;counts.append(observed)
        for label,row in [('resource',item['resource_summary']),
                          ('streamed_allocations',item['streamed_model_checks']['allocation_summary'])]:
            n=row['count'];kinds=row['kinds']
            assert type(n) is int and n>0 and isinstance(kinds,dict)
            assert all(type(v) is int and v>=0 for v in kinds.values()) and sum(kinds.values())==n
            observed[label]={'count':n,'kinds':dict(kinds)}
            row['count']=0;row['kinds']={k:0 for k in kinds}
        n=item['model_constraint_coverage']['checked_allocation_count']
        assert type(n) is int and n>0
        observed['checked_allocations']=n
        item['model_constraint_coverage']['checked_allocation_count']=0
    check_scalar_upgrade(*pair,1e-7)
    return dict(physical_fields_equivalent=True,record_counts_before=counts[0],record_counts_after=counts[1],
                scope='Record cardinality is not traffic mass. All other costs, stocks, flows, capacities and constraints compared.')
