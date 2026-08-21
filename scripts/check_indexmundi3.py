#!/usr/bin/env python3
with open('data/indexmundi_wti.html', 'r', encoding='utf-8') as f:
    content = f.read()

import re

idx = content.find('divMonthly')
after = content[idx:idx+15000]

# Check for Highcharts data embedded
hc_data = re.findall(r'series:\s*(\[.*?\])', after, re.DOTALL | re.IGNORECASE)
print('Highcharts series arrays:', len(hc_data))
for i, d in enumerate(hc_data[:3]):
    print('  Series {}: {}...'.format(i, d[:500]))

# Check for 'data:' arrays
data_arrays = re.findall(r'data:\s*(\[.*?\])', after, re.DOTALL)
print('Data arrays:', len(data_arrays))
for i, d in enumerate(data_arrays[:3]):
    print('  Data {}: {}...'.format(i, d[:500]))

# Look for the chart div
chart_divs = re.findall(r'<div[^>]*id=[\'"]([^\'"]*chart[^\'"]*)[\'"][^>]*>', after, re.IGNORECASE)
print('Chart divs:', chart_divs)

# Look for any JSON-LD data
json_ld = re.findall(r'<script type="application/ld\+json">(.*?)</script>', after, re.DOTALL)
for i, j in enumerate(json_ld):
    if 'Dataset' in j or 'price' in j.lower():
        print('JSON-LD Dataset {}: {}...'.format(i, j[:500]))