"""Reconstruct first150s cell crossings from saved stock/port conservation only."""
import bisect
import csv
import gzip
import hashlib
import json
from collections import defaultdict
from pathlib import Path

L = Path(__file__).resolve().parent
I = L.parent.parent
O = L / 'mainline_balance'
RUN = Path('D:/VISSIM_runs/20260930_expanded036_s29_9000_r2/sdmpc/decisions_sdmpc31_sdmpc9000_s29')
pins = {}


def read(p):
    b = p.read_bytes()
    pins[str(p)] = hashlib.sha256(b).hexdigest()
    return json.loads(gzip.decompress(b) if p.suffix == '.gz' else b)


def close(a, b, label):
    assert abs(a-b) < 1e-6, (label, a, b)


def main():
    O.mkdir(exist_ok=True)
    assert not (O/'summary.json').exists() and not (O/'cells.csv').exists()
    geometry = read(I / 'selected/port_gain/geometry.json')
    cells = sorted((c for c in geometry['cells'] if c['road'] == 'FW_E'), key=lambda c: c['cell'])
    ends = [c['end_m'] for c in cells]
    boundaries = [b for b in geometry['boundaries'] if b['road'] == 'FW_E' and b['kind'] in ('ramp','offramp')]
    assert len(boundaries) == 8
    detectors = list(csv.DictReader((I / 'selected/obs150/obs150_detectors_v2.csv').open(encoding='utf-8-sig')))
    heads = defaultdict(list)
    for r in detectors:
        if r['role'] == 'meter_head':
            heads[int(r['link'])].append(r)

    def position(row):
        address = geometry['addresses'].get(str(row[1]))
        return address[1]+row[3] if address and address[0] == 'FW_E' else None

    def stocks(frame):
        counts = [0]*31
        for row in frame:
            pos = position(row)
            if pos is not None:
                counts[min(bisect.bisect_right(ends, pos), 30)] += 1
        return counts

    def prefix(frame, x):
        return sum(1 for r in frame if (pos := position(r)) is not None and pos < x)

    rows, windows = [], []
    for start in (2250, 3600):
        end = start+150
        states = [read(RUN/f'state_{t:06d}.json') for t in (start,end)]
        frames = []
        for t,s in zip((start,end),states):
            meta = s['obs150']['frames']['current']
            frame = read(RUN/meta['path'])
            assert pins[str(RUN/meta['path'])] == meta['sha256']
            assert frame['complete'] and frame['time_s'] == t
            frames.append(frame['vehicles'])
        derived = read(RUN/f'obs150/derived_{end:06d}.json')
        assert derived['window'] == dict(start_s=start,end_s=end)
        assert not derived['boundary_ambiguous'] and derived['lag']['ok']
        assert not derived['removals']['window_total']
        terms = derived['boundaries']
        n0,n1 = map(stocks,frames)
        native_in = terms['source:FW_E']['cross']
        native_exit = terms['chain_end:FW_E']['cross']
        native_ports = {}
        for b in boundaries:
            if b['kind'] == 'offramp':
                native_ports[b['id']] = terms[f'off_entry:{b["connector"]}']['cross']
            else:
                link = b['connector']
                stations = heads[link]
                assert stations
                positions = {int(d['lane']): float(d['pos']) for d in stations}
                post = [sum(r[1] == link and r[3] >= positions[r[2]] for r in f) for f in frames]
                # meter_head is an at station; finite posthead inventory remains on its connector.
                head_terms = [terms[d['boundary_ref']] for d in stations]
                assert all(t['orientation'] == 'at' for t in head_terms)
                native_ports[b['id']] = sum(t['cross'] for t in head_terms)+post[0]-post[1]
                assert native_ports[b['id']] >= 0
        close(sum(n1)-sum(n0),native_in-native_exit+sum((1 if b['kind']=='ramp' else -1)*native_ports[b['id']] for b in boundaries),'native whole chain')
        # Independent point checks, with exact prefix stocks instead of cell-uniform interpolation.
        station_checks = {}
        for ref in ('10481','10483','10643','10682'):
            d = next(r for r in detectors if r['role']=='through' and r['ref']==ref)
            t = terms['through:'+ref]
            x = geometry['addresses'][d['link']][1] + (0 if t['orientation']=='down' else float(d['pos']))
            inferred = native_in + sum((1 if b['kind']=='ramp' else -1)*native_ports[b['id']] for b in boundaries if b['chain_pos_m'] < x)
            inferred -= prefix(frames[1],x)-prefix(frames[0],x)
            close(inferred,t['cross'],'through '+ref)
            station_checks[ref] = dict(chain_m=x,inferred=inferred,detector=t['cross'])
        native_flow=[];flow=native_in
        for c in range(31):
            flow += sum((1 if b['kind']=='ramp' else -1)*native_ports[b['id']] for b in boundaries if b.get('to_cell' if b['kind']=='ramp' else 'from_cell')==c)
            flow -= n1[c]-n0[c]
            assert flow>=0
            native_flow.append(flow)
        close(flow,native_exit,'native terminal')

        results={}
        for model,suffix in (('before','geotimecandidate'),('candidate','clockcandidate')):
            folder=L/f'city_path/{start}_ps_all8_{suffix}'
            # Actual saved names are supplied explicitly; absent evidence fails rather than falling back.
            trace=read(folder/'trace.json.gz')
            result=read(I/f'closedloop_recorded{start}_lever450_RM_C10484_city{start}_ps_all8_{suffix}/held_actual.json')
            phys=result['physical_cell_states'][:2]
            assert [s['time_sec'] for s in phys]==[start,end]
            ns=[[rho*lane*c['length_km'] for rho,lane,c in zip(s['density']['FW_E'],s['effective_lanes']['FW_E'],cells)] for s in phys]
            for c in range(31):close(ns[0][c],n0[c],f'initial cell{c}')
            transfers=defaultdict(float)
            for r in trace['transfers']:
                if start <= r['start_sec'] < end:
                    transfers[r['source'],r['target']]+=r['vehicles']
            ports={}
            for b in boundaries:
                if b['kind']=='ramp':
                    ports[b['id']]=transfers['merge_pending:'+b['id'],'freeway:FW_E']
                else:
                    target='storage:'+('lane_off_'+str(b['connector']) if b['branch']=='direct' else b['group']+'_storage')
                    ports[b['id']]=transfers['freeway:FW_E',target]
            source=transfers['origin:FW_E','freeway:FW_E']
            terminal=transfers['freeway:FW_E','external:terminal:FW_E']
            flow=source
            for c in range(31):
                ramp=sum(ports[b['id']] for b in boundaries if b['kind']=='ramp' and b['to_cell']==c)
                off=sum(ports[b['id']] for b in boundaries if b['kind']=='offramp' and b['from_cell']==c)
                actual_ramp=sum(native_ports[b['id']] for b in boundaries if b['kind']=='ramp' and b['to_cell']==c)
                actual_off=sum(native_ports[b['id']] for b in boundaries if b['kind']=='offramp' and b['from_cell']==c)
                up_error=flow-(native_in if c==0 else native_flow[c-1])
                flow+=ramp-off-(ns[1][c]-ns[0][c])
                error=flow-native_flow[c]
                residual=up_error+(ramp-actual_ramp)-(off-actual_off)-(ns[1][c]-n1[c])-error
                close(residual,0,'error identity')
                rows.append(dict(start=start,model=model,cell=c,start_m=cells[c]['start_m'],end_m=cells[c]['end_m'],
                    native_n0=n0[c],native_n1=n1[c],model_n1=ns[1][c],native_downstream=native_flow[c],model_downstream=flow,
                    upstream_error=up_error,merge_error=ramp-actual_ramp,off_error=off-actual_off,
                    stock_error=ns[1][c]-n1[c],downstream_error=error,identity_residual=residual,
                    model_speed_initial=phys[0]['speed_kmh']['FW_E'][c],model_speed_end=phys[1]['speed_kmh']['FW_E'][c]))
            close(flow,terminal,'model terminal')
            results[model]=dict(source=source,terminal=terminal,ports=ports,stock_change=sum(ns[1])-sum(ns[0]))
        windows.append(dict(start=start,end=end,native=dict(source=native_in,terminal=native_exit,ports=native_ports,stock_change=sum(n1)-sum(n0)),model=results,station_checks=station_checks))
    with (O/'cells.csv').open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    output=dict(status='complete',windows=windows,source_pins=pins,cell_rows=len(rows),new_forecasts=0,new_native=0,fzp_scans=0,fit=0,
        limitations=['Cumulative crossings reconstructed from conservation, not independent causal contributions or within-window timing.',
                     'Native command matches only first150s; later held predictions are not compared to changing native commands.',
                     'Native derived counts include offset-stock correction; no raw point count substituted for source/exit boundaries.'])
    (O/'summary.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(windows,ensure_ascii=False))


if __name__=='__main__':
    main()
