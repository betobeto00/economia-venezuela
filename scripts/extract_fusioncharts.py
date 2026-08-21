#!/usr/bin/env python3
with open('data/indexmundi_wti.html', 'r', encoding='utf-8') as f:
    content = f.read()

import re

# Extract all FusionCharts data
fc_matches = re.findall(r'dataSource\\":\s*\"<chart[^>]*>(.*?)</chart>\"', content, re.DOTALL)
print('FusionCharts data sources:', len(fc_matches))

for i, fc in enumerate(fc_matches):
    # Extract set elements
    sets = re.findall(r'<set label="([^"]*)" value="([^"]*)"', fc)
    print('Chart {}: {} data points'.format(i, len(sets)))
    for label, value in sets:
        print('  {}: {}'.format(label, value))
    print('---')