#!/usr/bin/env python3
"""
Descarga masiva de archivos de fuentes oficiales venezolanas
Uso: python download_all.py
"""
import os
import re
import httpx
from pathlib import Path
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# Configuración
DOWNLOAD_DIR = Path("data/raw_downloads")
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

FILE_EXTENSIONS = ('.pdf', '.xls', '.xlsx', '.csv', '.zip', '.ods', '.json')

# URLs a rastrear (profundidad 1)
SOURCES = {
    "ine": "https://ine.gob.ve/",
    "observatorio_main": "https://observatorio.gob.ve/",
    "observatorio_commodities": "https://observatorio.gob.ve/commodities/",
    "observatorio_antibloqueo": "https://observatorio.gob.ve/sistema-estadistico-antibloqueo/",
    "mppef_main": "https://www.mppef.gob.ve/",
    "mppef_stats": "https://www.mppef.gob.ve/estadisticas/",
    "minhidro_main": "https://www.minhidrocarburos.gob.ve/",
}

# Headers para evitar bloqueos
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'es-VE,es;q=0.9,en;q=0.8',
}

client = httpx.Client(timeout=30.0, follow_redirects=True, headers=HEADERS, verify=False)

def find_files_on_page(url):
    """Encuentra todos los enlaces a archivos en una página"""
    files = []
    try:
        r = client.get(url)
        if r.status_code != 200:
            return files
        
        links = re.findall(r'href=[\'"]([^\'"]+)[\'"]', r.text)
        for link in links:
            abs_url = urljoin(url, link)
            if any(abs_url.lower().endswith(ext) for ext in FILE_EXTENSIONS):
                parsed = urlparse(abs_url)
                files.append({
                    'url': abs_url,
                    'filename': parsed.path.split('/')[-1] or 'unknown',
                    'source': url,
                })
    except Exception as e:
        print(f"  ⚠️ Error rastreando {url}: {e}")
    return files

def download_file(file_info, semaphore=None):
    """Descarga un archivo individual"""
    url = file_info['url']
    filename = file_info['filename']
    source = file_info['source']
    
    # Carpeta por fuente
    source_name = urlparse(source).netloc.replace('www.', '').replace('.gob.ve', '').replace('.ve', '')
    dest_dir = DOWNLOAD_DIR / source_name
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / filename
    
    # Evitar re-descargar
    if dest_path.exists() and dest_path.stat().st_size > 0:
        return f"⏭️  Ya existe: {dest_path.relative_to(DOWNLOAD_DIR)}"
    
    try:
        with client.stream("GET", url) as r:
            if r.status_code != 200:
                return f"❌ HTTP {r.status_code}: {url}"
            
            total = int(r.headers.get('content-length', 0))
            with open(dest_path, 'wb') as f:
                downloaded = 0
                for chunk in r.iter_bytes(chunk_size=8192):
                    f.write(chunk)
                    downloaded += len(chunk)
            
            size_mb = dest_path.stat().st_size / (1024*1024)
            return f"✅ {dest_path.relative_to(DOWNLOAD_DIR)} ({size_mb:.1f} MB)"
    except Exception as e:
        if dest_path.exists():
            dest_path.unlink(missing_ok=True)
        return f"❌ Error: {url} - {e}"

def main():
    print("=" * 60)
    print("DESCARGA MASIVA - FUENTES OFICIALES VENEZUELA")
    print("=" * 60)
    
    # 1. Rastrear todas las fuentes
    all_files = []
    for name, url in SOURCES.items():
        print(f"\n🔍 Rastreando {name}...")
        files = find_files_on_page(url)
        print(f"   Encontrados: {len(files)} archivos")
        for f in files:
            f['source_name'] = name
        all_files.extend(files)
    
    print(f"\n{'='*60}")
    print(f"TOTAL ARCHIVOS A DESCARGAR: {len(all_files)}")
    print(f"{'='*60}")
    
    # Agrupar por extensión
    by_ext = {}
    for f in all_files:
        ext = Path(f['filename']).suffix.lower()
        by_ext[ext] = by_ext.get(ext, 0) + 1
    for ext, count in sorted(by_ext.items()):
        print(f"  {ext}: {count}")
    
    # 2. Descargar en paralelo
    print(f"\n📥 Iniciando descargas (máx 5 concurrentes)...")
    print(f"Directorio: {DOWNLOAD_DIR.absolute()}")
    
    results = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(download_file, f): f for f in all_files}
        for i, future in enumerate(as_completed(futures), 1):
            result = future.result()
            print(f"  [{i}/{len(all_files)}] {result}")
            results.append(result)
    
    # 3. Resumen
    ok = sum(1 for r in results if r.startswith("✅"))
    skipped = sum(1 for r in results if r.startswith("⏭️"))
    failed = sum(1 for r in results if r.startswith("❌"))
    
    print(f"\n{'='*60}")
    print(f"RESUMEN: ✅ {ok} descargados | ⏭️ {skipped} ya existían | ❌ {failed} fallaron")
    print(f"Archivos en: {DOWNLOAD_DIR.absolute()}")
    print(f"{'='*60}")

if __name__ == '__main__':
    main()