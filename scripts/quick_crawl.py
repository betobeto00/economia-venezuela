#!/usr/bin/env python3
"""
Quick check of government sources for data files
"""
import re
import httpx
from urllib.parse import urljoin, urlparse

URLS = [
    'https://www.minhidrocarburos.gob.ve',
    'https://www.mppef.gob.ve/category/noticias-nacionales/',
    'https://observatorio.gob.ve/sistema-estadistico-antibloqueo/',
    'https://observatorio.gob.ve/commodities/',
    'https://ine.gob.ve/',
]

FILE_EXTENSIONS = ('.pdf', '.xls', '.xlsx', '.csv', '.zip', '.ods', '.json')

def check_url(url):
    files_found = []
    try:
        r = httpx.get(url, timeout=10, follow_redirects=True, headers={'User-Agent': 'Mozilla/5.0'})
        print(f"{url} -> {r.status_code} ({len(r.text)} chars)")
        
        # Find all links
        links = re.findall(r'href=[\'"]([^\'"]+)[\'"]', r.text)
        
        for link in links:
            abs_url = urljoin(url, link)
            parsed = urlparse(abs_url)
            
            # Check if it's a file
            if any(abs_url.lower().endswith(ext) for ext in FILE_EXTENSIONS):
                files_found.append({
                    'source_url': url,
                    'file_url': abs_url,
                    'filename': parsed.path.split('/')[-1],
                })
                    
    except Exception as e:
        print(f"Error: {e}")
    
    return files_found

if __name__ == '__main__':
    all_files = []
    for url in URLS:
        print(f"\n{'='*60}")
        files = check_url(url)
        if files:
            for f in files:
                print(f"  [FILE] {f['filename']}")
                print(f"     URL: {f['file_url']}")
                all_files.append(f)
        else:
            print("  No files found on main page")
    
    print(f"\n{'='*60}")
    print(f"TOTAL FILES FOUND: {len(all_files)}")
    print(f"{'='*60}")