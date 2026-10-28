import json
m = json.load(open(r'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\rmcause\o1o4\o1\out\o1_metrics.json', encoding='utf-8'))
for k, v in m['per_run'].items():
    if 'rm_s31' in k:
        print(k, v['checks']['M1_links_minus_region'], v['checks']['missing_links'])
s = json.load(open(r'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\rmcause\o1o4\o1\scans\rm_s31\scan.json', encoding='utf-8'))
ls = json.load(open(r'D:\VISSIM-merge\review-d80faf9\diagnostics\vsl_handoff_20260924\evidence\accounting\east_link_sets_source.json', encoding='utf-8'))['link_sets']
print(ls['mainline'])
tot = sum(sum(s['link_vh'][str(i)]) for i in ls['mainline'])
print('links sum', tot, 'region sum', sum(s['region_vh']['fw_e_main']) if 'fw_e_main' in s['region_vh'] else list(s['region_vh'])[:5])
