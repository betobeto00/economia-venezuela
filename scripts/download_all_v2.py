#!/usr/bin/env python3
"""
Descarga masiva MEJORADA - Foco en INE (1300+ archivos) + otras fuentes
Uso: python download_all_v2.py
"""
import os
import re
import httpx
from pathlib import Path
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

DOWNLOAD_DIR = Path("data/raw_downloads")
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

FILE_EXTENSIONS = ('.pdf', '.xls', '.xlsx', '.csv', '.zip', '.ods', '.json')

# Fuentes expandidas con sub-páginas conocidas de INE
SOURCES = {
    # INE - páginas principales + subdirectorios conocidos con archivos
    "ine_main": "https://ine.gob.ve/",
    "ine_2026_01": "https://ine.gob.ve/wp-content/uploads/2026/01/",
    "ine_2026_02": "https://ine.gob.ve/wp-content/uploads/2026/02/",
    "ine_2026_03": "https://ine.gob.ve/wp-content/uploads/2026/03/",
    "ine_2026_04": "https://ine.gob.ve/wp-content/uploads/2026/04/",  # XLS por estado
    "ine_2026_05": "https://ine.gob.ve/wp-content/uploads/2026/05/",
    "ine_2026_06": "https://ine.gob.ve/wp-content/uploads/2026/06/",
    "ine_2026_07": "https://ine.gob.ve/wp-content/uploads/2026/07/",
    "ine_2025_09": "https://ine.gob.ve/wp-content/uploads/2025/09/",  # Census 2011
    "ine_2025_10": "https://ine.gob.ve/wp-content/uploads/2025/10/",
    "ine_2024_09": "https://ine.gob.ve/wp-content/uploads/2024/09/",
    
    # Observatorio
    "observatorio_main": "https://observatorio.gob.ve/",
    "observatorio_commodities": "https://observatorio.gob.ve/commodities/",
    "observatorio_antibloqueo": "https://observatorio.gob.ve/sistema-estadistico-antibloqueo/",
    
    # MPPEF
    "mppef_main": "https://www.mppef.gob.ve/",
    "mppef_stats": "https://www.mppef.gob.ve/estadisticas/",
    "mppef_datos": "https://www.mppef.gob.ve/datos/",
    "mppef_2026_08": "https://www.mppef.gob.ve/wp-content/uploads/2026/08/",
    
    # MinHidrocarburos
    "minhidro_main": "https://www.minhidrocarburos.gob.ve/",
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}

# Cliente con timeout largo para INE
client = httpx.Client(timeout=60.0, follow_redirects=True, headers=HEADERS, verify=False)

def find_files_on_page(url):
    """Encuentra todos los enlaces a archivos en una página (incluye directory listing)"""
    files = []
    try:
        r = client.get(url)
        if r.status_code != 200:
            return files
        
        # Buscar enlaces en HTML normal
        links = re.findall(r'href=[\'"]([^\'"]+)[\'"]', r.text)
        
        # También buscar en directory listing (Apache/Nginx)
        dir_links = re.findall(r'href=[\'"]([^\'"]+\.(?:pdf|xls|xlsx|csv|zip|ods|json))[\'"]', r.text, re.I)
        links.extend(dir_links)
        
        for link in links:
            abs_url = urljoin(url, link)
            if any(abs_url.lower().endswith(ext) for ext in FILE_EXTENSIONS):
                parsed = urlparse(abs_url)
                fname = parsed.path.split('/')[-1]
                if fname and not fname.endswith('/'):
                    files.append({
                        'url': abs_url,
                        'filename': fname,
                        'source': url,
                    })
    except Exception as e:
        print(f"  ⚠️ Error rastreando {url}: {e}")
    return files

def download_file(file_info):
    """Descarga un archivo individual con reintentos"""
    url = file_info['url']
    filename = file_info['filename']
    source = file_info['source']
    
    source_name = urlparse(source).netloc.replace('www.', '').replace('.gob.ve', '').replace('.ve', '')
    dest_dir = DOWNLOAD_DIR / source_name
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / filename
    
    if dest_path.exists() and dest_path.stat().st_size > 1000:  # >1KB
        return f"⏭️  Ya existe: {dest_path.relative_to(DOWNLOAD_DIR)}"
    
    for attempt in range(3):
        try:
            with client.stream("GET", url) as r:
                if r.status_code != 200:
                    if attempt == 2:
                        return f"❌ HTTP {r.status_code}: {url}"
                    time.sleep(2)
                    continue
                
                total = int(r.headers.get('content-length', 0))
                with open(dest_path, 'wb') as f:
                    downloaded = 0
                    for chunk in r.iter_bytes(chunk_size=8192):
                        f.write(chunk)
                        downloaded += len(chunk)
                
                if dest_path.stat().st_size < 1000:
                    dest_path.unlink(missing_ok=True)
                    return f"❌ Archivo muy pequeño: {url}"
                
                size_mb = dest_path.stat().st_size / (1024*1024)
                return f"✅ {dest_path.relative_to(DOWNLOAD_DIR)} ({size_mb:.1f} MB)"
        except Exception as e:
            if attempt == 2:
                if dest_path.exists():
                    dest_path.unlink(missing_ok=True)
                return f"❌ Error (3 intentos): {url} - {e}"
            time.sleep(2)
    
    return f"❌ Falló: {url}"

def main():
    print("=" * 60)
    print("DESCARGA MASIVA v2 - INE PROFUNDO + OTRAS FUENTES")
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
    
    # Deduplicar por URL
    seen = set()
    unique_files = []
    for f in all_files:
        if f['url'] not in seen:
            seen.add(f['url'])
            unique_files.append(f)
    
    print(f"\n{'='*60}")
    print(f"TOTAL ARCHIVOS ÚNICOS: {len(unique_files)}")
    print(f"{'='*60}")
    
    # Agrupar por extensión
    by_ext = {}
    for f in unique_files:
        ext = Path(f['filename']).suffix.lower()
        by_ext[ext] = by_ext.get(ext, 0) + 1
    for ext, count in sorted(by_ext.items()):
        print(f"  {ext}: {count}")
    
    # Mostrar primeros 20
    print(f"\nPrimeros 20 archivos:")
    for f in unique_files[:20]:
        print(f"  {f['filename']} <- {f['source']}")
    
    # 2. Descargar en paralelo
    print(f"\n📥 Iniciando descargas (máx 5 concurrentes)...")
    print(f"Directorio: {DOWNLOAD_DIR.absolute()}")
    
    results = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(download_file, f): f for f in unique_files}
        for i, future in enumerate(as_completed(futures), 1):
            result = future.result()
            print(f"  [{i}/{len(unique_files)}] {result}")
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