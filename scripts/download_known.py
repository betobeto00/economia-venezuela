#!/usr/bin/env python3
"""
Descarga usando URLs CONOCIDAS del crawl previo exitoso + otras fuentes
INE está bloqueando - usamos URLs directas conocidas
Uso: python download_known.py
"""
import os
import httpx
from pathlib import Path
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

DOWNLOAD_DIR = Path("data/raw_downloads")
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

# URLs DIRECTAS conocidas del crawl previo que SÍ funcionó
KNOWN_FILES = {
    "ine.gob.ve": [
        # Census 2011 - 2025/09/
        "https://ine.gob.ve/wp-content/uploads/2025/09/POBLACION-POR-MUNICIPIOS-CENSO-2011.pdf",
        "https://ine.gob.ve/wp-content/uploads/2025/09/POBLACION-INDIGENA-CENSO-2011.pdf",
        "https://ine.gob.ve/wp-content/uploads/2025/09/Estructura-completa.pdf",
        "https://ine.gob.ve/wp-content/uploads/2025/09/TRANSICION-DEMOGRAFICA.pdf",
        # 2025/10/
        "https://ine.gob.ve/wp-content/uploads/2025/10/P.-Censo-2011.pdf",
        # 2026/03/ - Proyecciones poblacionales
        "https://ine.gob.ve/wp-content/uploads/2026/03/1950-2050-REP.-BOL.-VENEZUELA-PROYECCION-POBLACION.pdf",
        # 2026/04/ - XLS por estado (DATOS ECONÓMICOS/DEMOGRÁFICOS CLAVE)
        "https://ine.gob.ve/wp-content/uploads/2026/04/Nacional-36.xls",
        "https://ine.gob.ve/wp-content/uploads/2026/04/Distrito_Capital-3.xls",
        "https://ine.gob.ve/wp-content/uploads/2026/04/Estado_Amazonas-3.xls",
        "https://ine.gob.ve/wp-content/uploads/2026/04/Estado_Anzoategui-3.xls",
        "https://ine.gob.ve/wp-content/uploads/2026/04/Estado_Apure-3.xls",
        "https://ine.gob.ve/wp-content/uploads/2026/04/Estado_Aragua-3.xls",
        "https://ine.gob.ve/wp-content/uploads/2026/04/Estado_Barinas-3.xls",
        "https://ine.gob.ve/wp-content/uploads/2026/04/Estado_Bolivar-4.xls",
        "https://ine.gob.ve/wp-content/uploads/2026/04/Estado_Carabobo-4.xls",
        "https://ine.gob.ve/wp-content/uploads/2026/04/Estado_Cojedes-3.xls",
        "https://ine.gob.ve/wp-content/uploads/2026/04/Estado_Delta_Amacuro-3.xls",
        "https://ine.gob.ve/wp-content/uploads/2026/04/Estado_Falcon-3.xls",
        "https://ine.gob.ve/wp-content/uploads/2026/04/Estado_Guarico-3.xls",
        "https://ine.gob.ve/wp-content/uploads/2026/04/Estado_Lara-4.xls",
        "https://ine.gob.ve/wp-content/uploads/2026/04/Estado_Merida-4.xls",
        "https://ine.gob.ve/wp-content/uploads/2026/04/Estado_Miranda-4.xls",
        "https://ine.gob.ve/wp-content/uploads/2026/04/Estado_Monagas-3.xls",
        "https://ine.gob.ve/wp-content/uploads/2026/04/Estado_Nueva_Esparta-3.xls",
        "https://ine.gob.ve/wp-content/uploads/2026/04/Estado_Portuguesa-3.xls",
        "https://ine.gob.ve/wp-content/uploads/2026/04/Estado_Sucre-3.xls",
        "https://ine.gob.ve/wp-content/uploads/2026/04/Estado_Tachira-4.xls",
        "https://ine.gob.ve/wp-content/uploads/2026/04/Estado_Trujillo-3.xls",
        "https://ine.gob.ve/wp-content/uploads/2026/04/Estado_Vargas-3.xls",
        "https://ine.gob.ve/wp-content/uploads/2026/04/Estado_Yaracuy-3.xls",
        "https://ine.gob.ve/wp-content/uploads/2026/04/Estado_Zulia-4.xls",
        # 2026/07/
        "https://ine.gob.ve/wp-content/uploads/2026/07/VIVIENDA.pdf",
        # 2026/01/ - Fe de vida
        "https://ine.gob.ve/wp-content/uploads/2026/01/AVISO-OFICIAL-FE-DE-VIDA-2026.pdf",
        "https://ine.gob.ve/wp-content/uploads/2026/01/FORMATO-DE-FE-DE-VIDA-2026.pdf",
        # 2025/06-07/ - Plan Patria
        "https://ine.gob.ve/wp-content/uploads/2025/06/7TLeyPlanPatriaF.pdf",
        "https://ine.gob.ve/wp-content/uploads/2025/07/Folleto-Nacional-Venezuela-y-las-7T.pdf",
        "https://ine.gob.ve/wp-content/uploads/2025/07/Estado-Aragua_compressed.pdf",
    ],
    "observatorio.gob.ve": [
        "https://observatorio.gob.ve/wp-content/uploads/2026/07/Plan-Venezuela-Renace-Anuncios.pdf",
        "https://observatorio.gob.ve/wp-content/uploads/2023/07/DISCURSO-5-DE-JULIO_A_N-EDICION-FINAL-.pdf",
        "https://observatorio.gob.ve/wp-content/uploads/2022/07/Guia-de-Tablero-de-Precios-Commodities.pdf",
    ],
    "mppef.gob.ve": [
        "https://www.mppef.gob.ve/wp-content/uploads/2026/08/Listado_Bancos_Publicos_Programa_Venezuela_Renace_-5-de-agosto-II.pdf_20260811_121344_0000.pdf",
    ],
}

# Intentar descubrir más en directorios INE (patrón predecible)
def generate_ine_urls():
    """Genera URLs probables en directorios INE no rastreados"""
    urls = []
    base = "https://ine.gob.ve/wp-content/uploads/"
    # Meses 2026 que no probamos
    for month in ["05", "06", "08", "09", "10", "11", "12"]:
        urls.append(f"{base}2026/{month}/")
    # Años anteriores con datos económicos
    for year in ["2023", "2022", "2021", "2020"]:
        for month in ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]:
            urls.append(f"{base}{year}/{month}/")
    return urls

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
}

client = httpx.Client(timeout=60.0, follow_redirects=True, headers=HEADERS, verify=False)

def download_file(url, source_name):
    """Descarga un archivo individual"""
    parsed = urlparse(url)
    filename = parsed.path.split('/')[-1]
    if not filename or filename.endswith('/'):
        return f"⏭️  Saltado (directorio): {url}"
    
    dest_dir = DOWNLOAD_DIR / source_name
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / filename
    
    if dest_path.exists() and dest_path.stat().st_size > 1000:
        return f"⏭️  Ya existe: {dest_path.relative_to(DOWNLOAD_DIR)}"
    
    for attempt in range(3):
        try:
            with client.stream("GET", url) as r:
                if r.status_code == 404:
                    return f"⚠️  404 No encontrado: {filename}"
                if r.status_code != 200:
                    if attempt == 2:
                        return f"❌ HTTP {r.status_code}: {filename}"
                    time.sleep(3)
                    continue
                
                with open(dest_path, 'wb') as f:
                    for chunk in r.iter_bytes(chunk_size=8192):
                        f.write(chunk)
                
                if dest_path.stat().st_size < 1000:
                    dest_path.unlink(missing_ok=True)
                    return f"❌ Archivo muy pequeño: {filename}"
                
                size_mb = dest_path.stat().st_size / (1024*1024)
                return f"✅ {dest_path.relative_to(DOWNLOAD_DIR)} ({size_mb:.1f} MB)"
        except Exception as e:
            if attempt == 2:
                if dest_path.exists():
                    dest_path.unlink(missing_ok=True)
                return f"❌ Error: {filename} - {e}"
            time.sleep(3)
    return f"❌ Falló: {filename}"

def try_discover_ine():
    """Intenta descubrir archivos en directorios INE (con timeout corto)"""
    print("\n🔍 Intentando descubrir más archivos en INE (directorios)...")
    discovered = []
    for url in generate_ine_urls():
        try:
            r = client.get(url, timeout=10.0)
            if r.status_code == 200:
                # Parse directory listing
                import re
                links = re.findall(r'href=[\'"]([^\'"]+\.(?:pdf|xls|xlsx|csv|zip|ods|json))[\'"]', r.text, re.I)
                for link in links:
                    abs_url = url + link if not link.startswith('http') else link
                    discovered.append(abs_url)
                if links:
                    print(f"  📁 {url} -> {len(links)} archivos")
        except:
            pass  # Silencioso
    return discovered

def main():
    print("=" * 60)
    print("DESCARGA CON URLs CONOCIDAS + DESCUBRIMIENTO INE")
    print("=" * 60)
    
    all_files = []
    
    # 1. Archivos conocidos
    for source, urls in KNOWN_FILES.items():
        for url in urls:
            all_files.append({'url': url, 'source': source})
    
    print(f"\n📋 Archivos conocidos: {len(all_files)}")
    
    # 2. Intentar descubrir más en INE
    discovered = try_discover_ine()
    for url in discovered:
        all_files.append({'url': url, 'source': 'ine.gob.ve'})
    print(f"🔍 Descubiertos adicionales: {len(discovered)}")
    
    # Deduplicar
    seen = set()
    unique = []
    for f in all_files:
        if f['url'] not in seen:
            seen.add(f['url'])
            unique.append(f)
    
    print(f"\n{'='*60}")
    print(f"TOTAL ÚNICOS A DESCARGAR: {len(unique)}")
    print(f"{'='*60}")
    
    # 3. Descargar
    results = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(download_file, f['url'], f['source']): f for f in unique}
        for i, future in enumerate(as_completed(futures), 1):
            result = future.result()
            print(f"  [{i}/{len(unique)}] {result}")
            results.append(result)
    
    ok = sum(1 for r in results if r.startswith("✅"))
    skipped = sum(1 for r in results if r.startswith("⏭️"))
    notfound = sum(1 for r in results if r.startswith("⚠️"))
    failed = sum(1 for r in results if r.startswith("❌"))
    
    print(f"\n{'='*60}")
    print(f"RESUMEN: ✅ {ok} | ⏭️ {skipped} | ⚠️ {notfound} | ❌ {failed}")
    print(f"En: {DOWNLOAD_DIR.absolute()}")
    print(f"{'='*60}")

if __name__ == '__main__':
    main()