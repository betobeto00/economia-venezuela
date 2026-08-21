#!/usr/bin/env python3
"""
Descarga archivos INE usando Playwright (evita bloqueos)
Uso: python download_playwright.py
"""
import os
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

DOWNLOAD_DIR = Path("data/raw_downloads")
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

# URLs directas conocidas
KNOWN_FILES = {
    "ine.gob.ve": [
        "https://ine.gob.ve/wp-content/uploads/2025/09/POBLACION-POR-MUNICIPIOS-CENSO-2011.pdf",
        "https://ine.gob.ve/wp-content/uploads/2025/09/POBLACION-INDIGENA-CENSO-2011.pdf",
        "https://ine.gob.ve/wp-content/uploads/2025/09/Estructura-completa.pdf",
        "https://ine.gob.ve/wp-content/uploads/2025/09/TRANSICION-DEMOGRAFICA.pdf",
        "https://ine.gob.ve/wp-content/uploads/2025/10/P.-Censo-2011.pdf",
        "https://ine.gob.ve/wp-content/uploads/2026/03/1950-2050-REP.-BOL.-VENEZUELA-PROYECCION-POBLACION.pdf",
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
        "https://ine.gob.ve/wp-content/uploads/2026/07/VIVIENDA.pdf",
        "https://ine.gob.ve/wp-content/uploads/2026/01/AVISO-OFICIAL-FE-DE-VIDA-2026.pdf",
        "https://ine.gob.ve/wp-content/uploads/2026/01/FORMATO-DE-FE-DE-VIDA-2026.pdf",
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

async def download_with_playwright(page, url, dest_path):
    """Descarga un archivo usando Playwright"""
    try:
        # Navegar a la URL
        response = await page.goto(url, wait_until="networkidle", timeout=60000)
        
        if response and response.status == 200:
            # Obtener el contenido
            content = await response.body()
            
            if len(content) > 1000:  # Archivo válido
                dest_path.write_bytes(content)
                size_mb = len(content) / (1024 * 1024)
                return f"[OK] {dest_path.name} ({size_mb:.1f} MB)"
            else:
                return f"[SMALL] {dest_path.name}"
        elif response and response.status == 404:
            return f"[404] {dest_path.name}"
        else:
            status = response.status if response else "No response"
            return f"[FAIL] HTTP {status}: {dest_path.name}"
    except Exception as e:
        return f"[FAIL] Error: {dest_path.name} - {str(e)[:100]}"

async def main():
    print("=" * 60)
    print("DESCARGA CON PLAYWRIGHT - INE + OTRAS FUENTES")
    print("=" * 60)
    
    # Preparar lista de descargas
    downloads = []
    for source, urls in KNOWN_FILES.items():
        dest_dir = DOWNLOAD_DIR / source
        dest_dir.mkdir(parents=True, exist_ok=True)
        for url in urls:
            filename = url.split("/")[-1]
            dest_path = dest_dir / filename
            if dest_path.exists() and dest_path.stat().st_size > 1000:
                print(f"[SKIP] Ya existe: {dest_path.relative_to(DOWNLOAD_DIR)}")
                continue
            downloads.append((url, dest_path, source))
    
    print(f"\nTotal a descargar: {len(downloads)}")
    if not downloads:
        print("Todo ya descargado.")
        return
    
    async with async_playwright() as p:
        # Usar Chromium con configuración anti-bloqueo
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
            ]
        )
        
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080},
            accept_downloads=True,
        )
        
        page = await context.new_page()
        
        # Descargar secuencialmente (más confiable para archivos grandes)
        results = []
        for i, (url, dest_path, source) in enumerate(downloads, 1):
            print(f"  [{i}/{len(downloads)}] {dest_path.name}...", end=" ", flush=True)
            result = await download_with_playwright(page, url, dest_path)
            print(result)
            results.append(result)
            await asyncio.sleep(1)  # Pausa entre descargas
        
        await browser.close()
    
    # Resumen
    ok = sum(1 for r in results if r.startswith("[OK]"))
    notfound = sum(1 for r in results if r.startswith("[404]"))
    failed = sum(1 for r in results if r.startswith("[FAIL]"))
    small = sum(1 for r in results if r.startswith("[SMALL]"))
    
    print(f"\n{'='*60}")
    print(f"RESUMEN: [OK] {ok} | [404] {notfound} | [SMALL] {small} | [FAIL] {failed}")
    print(f"Archivos en: {DOWNLOAD_DIR.absolute()}")
    print(f"{'='*60}")

if __name__ == '__main__':
    asyncio.run(main())