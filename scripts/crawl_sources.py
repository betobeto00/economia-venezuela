#!/usr/bin/env python3
"""
Crawl government sources for PDF/XLS/CSV data files
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

def find_files(url, max_depth=2, visited=None):
    if visited is None:
        visited = set()
    
    if url in visited or len(visited) > 50:
        return []
    visited.add(url)
    
    files_found = []
    try:
        r = httpx.get(url, timeout=15, follow_redirects=True, headers={'User-Agent': 'Mozilla/5.0'})
        if r.status_code != 200:
            return []
        
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
            
            # Recurse into same-domain pages (limited depth)
            elif parsed.netloc == urlparse(url).netloc and max_depth > 0:
                if abs_url not in visited:
                    files_found.extend(find_files(abs_url, max_depth - 1, visited))
                    
    except Exception as e:
        print(f"Error crawling {url}: {e}")
    
    return files_found

if __name__ == '__main__':
    all_files = []
    for url in URLS:
        print(f"\n{'='*60}")
        print(f"Crawling: {url}")
        print(f"{'='*60}")
        files = find_files(url, max_depth=1)
        if files:
            for f in files:
                print(f"  [FILE] {f['filename']}")
                print(f"     URL: {f['file_url']}")
                all_files.append(f)
        else:
            print("  No files found")
    
    print(f"\n{'='*60}")
    print(f"TOTAL FILES FOUND: {len(all_files)}")
    print(f"{'='*60}")
    
    # Group by source
    from collections import defaultdict
    by_source = defaultdict(list)
    for f in all_files:
        by_source[f['source_url']].append(f)
    
    for source, files in by_source.items():
        print(f"\n{source}: {len(files)} files")
        for f in files[:20]:
            print(f"  - {f['filename']} ({f['file_url']})")