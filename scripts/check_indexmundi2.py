#!/usr/bin/env python3
with open('data/indexmundi_wti.html', 'r', encoding='utf-8') as f:
    content = f.read()

import re

# Look for the actual data table
idx = content.find('Monthly Price - US Dollars per Barrel')
if idx > 0:
    print('Found Monthly Price heading at', idx)
    after = content[idx:idx+5000]
    tables = re.findall(r'<table.*?</table>', after, re.DOTALL | re.IGNORECASE)
    for i, t in enumerate(tables):
        print(f'Table {i}:')
        print(t[:2000])
        print('---')

# Check for 'format=' links
format_links = re.findall(r'href=[\'"]([^\'"]*format=(?:csv|excel|xls)[^\'"]*)[\'"]', content, re.IGNORECASE)
print('Format links:', format_links)

# Check all format params
all_format = re.findall(r'format=(csv|excel|xls|xlsx)', content, re.IGNORECASE)
print('Format params:', all_format)

# Look for any download/historical data links
download_links = re.findall(r'href=[\'"]([^\'"]*download[^\'"]*)[\'"]', content, re.IGNORECASE)
print('Download links:', download_links)

# Check for any 'Historical Data' text links
hist_links = re.findall(r'href=[\'"]([^\'"]*)[\'"][^>]*>Historical', content, re.IGNORECASE)
print('Historical links:', hist_links)

# Search for 'Export' links
export_links = re.findall(r'href=[\'"]([^\'"]*)[\'"][^>]*>Export', content, re.IGNORECASE)
print('Export links:', export_links)