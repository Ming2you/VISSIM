import json
p = r'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\rmcause\o1o4\o1\scans\rm_s41\scan.json'
s = json.load(open(p, encoding='utf-8'))
print(list(s.keys()))
print('n_bins', s['n_bins'], 'bin_sec', s['bin_sec'], 'seed', s['seed'], 'frames', s['frames'])
print('speed keys', list(s['speed'].keys()), 'zones', list(s['speed']['zones'].keys()))
print('frame_series keys', list(s['frame_series'].keys()))
print('meterbound keys', list(s['frame_series']['meterbound'].keys()))
print('regions keys', list(s['regions'].keys()))
print('fzp', s['fzp'], 'inpx', s['inpx'])
m = json.load(open(r'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\rmcause\o1o4\o1\out\o1_metrics.json', encoding='utf-8'))
bd = m['pairs']['RM-NC3|UC']['bins_delta']['M1']['41']
print('RM-NC3 s41 early', round(sum(bd[18:30]), 2), 'late', round(sum(bd[42:54]), 2), 'whole', round(sum(bd[6:60]), 2), 'full', round(sum(bd), 2))
bd = m['pairs']['VA-NC3|UC']['bins_delta']['M1']['41']
print('VA-NC3 s41 early', round(sum(bd[18:30]), 2), 'late', round(sum(bd[42:54]), 2))
bd = m['pairs']['RM-NC3|UC']['bins_delta']['M1']['31']
print('RM-NC3 s31 early', round(sum(bd[18:30]), 2), 'late', round(sum(bd[42:54]), 2))
v = json.load(open(r'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\rmcause\o1o4\vnext\out\vn_analysis.json', encoding='utf-8'))
print('vn keys', list(v.keys())[:30])
