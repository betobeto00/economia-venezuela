#!/usr/bin/env python3
"""
Check indexmundi.com for downloadable commodity data
"""
import httpx
import re

url = 'https://www.indexmundi.com/commodities/?commodity=crude-oil-west-texas-intermediate'
r = httpx.get(url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})

# Look for divMonthly content
div_monthly = re.findall(r'<div id="divMonthly">.*?</div>', r.text, re.DOTALL)
if div_monthly:
    print("Found divMonthly")
    # Extract table from within
    inner_tables = re.findall(r'<table.*?</table>', div_monthly[0], re.DOTALL)
    print(f"Tables inside divMonthly: {len(inner_tables)}")
    for i, t in enumerate(inner_tables):
        print(f"  Table {i}: {t[:500]}...")

# Also look for any CSV/Excel download links
csv_links = re.findall(r'href=[\'"]([^\'"]*\.(?:csv|xls|xlsx))[\'"]', r.text, re.IGNORECASE)
print(f"\nCSV/Excel links: {csv_links}")

# Check for 'Download' or 'Export' links
download_links = re.findall(r'href=[\'"]([^\'"]*)[\'"][^>]*>(?:Download|Export|CSV|Excel)', r.text, re.IGNORECASE)
print(f"Download links: {download_links}")

# Look for any data-* attributes with JSON
data_attrs = re.findall(r'data-(\w+)=[\'"]([^\'"]*)[\'"]', r.text)
for attr, val in data_attrs:
    if 'data' in attr.lower() or 'series' in attr.lower() or 'chart' in attr.lower():
        print(f"data-{attr}: {val[:200]}...")

# Check for Highcharts/Chart.js initialization
hc_matches = re.findall(r'Highcharts\.chart\([^)]*\)', r.text)
print(f"\nHighcharts initializations: {len(hc_matches)}")
for m in hc_matches[:2]:
    print(f"  {m[:300]}...")