# Fuentes Fiscales Gubernamentales - Análisis Presupuestario

## 📋 Visión General

Integración de informes de gestión gubernamentales para análisis fiscal completo. Permite pasar de analizar solo resultados económicos a analizar las **decisiones de gasto e inversión pública**.

---

## 🏛️ Fuentes Gubernamentales Clave

### 1. Oficina Nacional de Presupuesto (ONAPRE)

**URL:** https://www.onapre.gob.ve

| Categoría | Contenido | Frecuencia |
|-----------|-----------|------------|
| **Normativos** | Instructivos y manuales de presupuesto | Anual |
| **Ejecución** | Informes de ejecución presupuestaria | Trimestral |
| **Plan de Cuentas** | Plan oficial del Estado | Permanente |

**Tipo de datos:** Normativos y de ejecución agregada

**Método de extracción:**
- Web scraping de sección "Informes" y "Descargas"
- Descarga de PDFs y procesamiento con PyPDF2/pdfplumber

---

### 2. Contraloría General de la República (CGR)

**URL:** https://www.cgr.gob.ve

| Categoría | Contenido | Frecuencia |
|-----------|-----------|------------|
| **Informes de Gestión** | Resultados de actividad contralora | Anual |
| **Actuaciones** | Rendición de cuentas | Permanente |
| **Auditorías** | Hallazgos sobre uso de recursos | Variable |

**Tipo de datos:** Control, auditoría y hallazgos

**Importancia:** Fuente independiente para contrastar datos oficiales

---

### 3. Asamblea Nacional (AN)

**URL:** https://www.asambleanacional.gob.ve

| Categoría | Contenido | Frecuencia |
|-----------|-----------|------------|
| **Leyes** | Proyecto de Ley de Presupuesto | Anual |
| **Endeudamiento** | Proyecto de Endeudamiento Anual | Anual |
| **Memorias y Cuentas** | Rendición de cuentas de órganos | Anual |

**Tipo de datos:** Leyes, proyectos y rendición de cuentas

---

### 4. Ministerio del Poder Popular de Economía y Finanzas (MPPEF)

**URL:** https://www.mppef.gob.ve

| Categoría | Contenido | Frecuencia |
|-----------|-----------|------------|
| **Ejecución Presupuestaria** | Informes trimestrales | Trimestral |
| **Comunicados** | Presentaciones sobre gasto público | Variable |
| **Finanzas Públicas** | Deuda y balances | Mensual/Trimestral |

**Tipo de datos:** Ejecución presupuestaria y finanzas públicas

---

### 5. Gobierno del Distrito Capital / Alcaldía de Caracas

**URL:** Sitio de la Alcaldía

| Categoría | Contenido | Frecuencia |
|-----------|-----------|------------|
| **Informe de Gestión** | Político y administrativo | Anual |
| **Ejecución Municipal** | Presupuesto municipal | Anual |
| **Inversión** | Infraestructura, salud, transporte | Anual |

**Tipo de datos:** Gestión municipal e inversión local

---

## 🔧 Estrategia de Integración

### Fase 1: Identificación y Monitoreo

**Desafío principal:** Estos entes no ofrecen APIs. La información está en PDF, comunicados o páginas web estáticas.

**Solución:**

```
1. Rastreador de Cambios
   - Monitorear URLs clave de informes
   - Alertar cuando se publique nuevo documento
   - Herramienta: changedetection.io

2. Estructura de Extracción
   - Descargar archivos PDF/Word
   - Extraer texto con PyPDF2/pdfplumber
   - Usar DeepSeek para extracción estructurada
```

### Fase 2: Modelado de Datos

**Modelo de datos fiscal:**

```python
# src/models/fiscal.py
from pydantic import BaseModel
from datetime import date
from typing import Optional

class BudgetExecution(BaseModel):
    """Modelo de ejecución presupuestaria"""
    
    # Metadatos
    fiscal_year: int
    source: str  # "ONAPRE", "CGR", "MPPEF", "AN"
    document_url: str
    publication_date: date
    
    # Presupuesto
    total_budget_approved: float
    total_budget_executed: float
    execution_percentage: float
    
    # Desglose por partidas
    current_expenditure: float  # Gasto corriente (personal, etc.)
    capital_expenditure: float  # Gasto de capital (inversión)
    social_investment: float    # Inversión social
    
    # Metadatos para análisis
    notes: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "fiscal_year": 2024,
                "source": "ONAPRE",
                "total_budget_approved": 1000000000,
                "total_budget_executed": 750000000,
                "execution_percentage": 75.0
            }
        }


class FiscalIndicators(BaseModel):
    """Indicadores fiscales derivados"""
    
    fiscal_year: int
    deficit: float  # Gasto - Ingreso
    deficit_gdp_ratio: float  # Déficit como % del PIB
    debt_gdp_ratio: float  # Deuda como % del PIB
    primary_balance: float  # Balance primario
    monetization: float  # Financiamiento con emisión
    
    class Config:
        json_schema_extra = {
            "example": {
                "fiscal_year": 2024,
                "deficit": -500000000,
                "deficit_gdp_ratio": -4.5,
                "debt_gdp_ratio": 35.0,
                "primary_balance": 100000000,
                "monetization": 600000000
            }
        }
```

### Fase 3: Automatización y Almacenamiento

```
1. Programar recolección
   - GitHub Action semanal/mensual
   - Ejecutar colectores fiscales

2. Almacenar en TimescaleDB
   - Datos históricos
   - Series de ejecución presupuestaria

3. Generar alertas
   - Brecha significativa presupuesto aprobado vs ejecutado
   - Cambios drásticos en asignación por partidas
```

---

## 📊 Uso en Análisis Econométrico

### Análisis Fiscales Habilitados

| Análisis | Datos Necesarios | Pregunta a Responder |
|----------|------------------|---------------------|
| **Efecto del Gasto Público** | Ejecución + PIB | ¿El gasto impulsa el crecimiento? |
| **Sostenibilidad Fiscal** | Ingresos vs Gastos | ¿El déficit se financia con emisión? |
| **Eficiencia del Gasto** | Inversión social vs indicadores | ¿Se correlaciona con mejoras? |
| **Nowcasting Económico** | Ejecución del gasto | ¿Se puede estimar PIB en curso? |

### Modelos Econométricos con Datos Fiscales

```python
# Ejemplo: Regresión del efecto del gasto público sobre PIB
from src.analyzers.econometric.regression import NeweyWestRegressor

regressor = NeweyWestRegressor()

# Datos
gasto_publico = ...  # Ejecución presupuestaria trimestral
pib = ...  # PIB trimestral

# Regresión
result = regressor.regress_inflation_m2(
    y=pib,
    X=pd.DataFrame({'gasto': gasto_publico})
)

# Interpretación: ¿El gasto público afecta el PIB?
```

```python
# Ejemplo: VECM para relación gasto-emisión-inflación
from src.analyzers.econometric.causality import VECMAnalyzer

vecm = VECMAnalyzer()

# Variables
gasto = ...  # Gasto público
emision = ...  # Emisión monetaria
inflacion = ...  # Inflación

# Modelo VECM
result = vecm.fit_vecm(
    series_1=gasto,
    series_2=emision,
    name_1="Gasto Público",
    name_2="Emisión Monetaria"
)

# Interpretación: ¿El gasto financiado con emisión causa inflación?
```

---

## 📁 Estructura de Collectors Fiscales

```
src/collectors/fiscal/
├── __init__.py
├── onapre_collector.py     # Oficina Nacional de Presupuesto
├── cgr_collector.py        # Contraloría General
├── an_collector.py         # Asamblea Nacional
├── mppef_collector.py      # Ministerio de Economía
├── caracas_collector.py    # Alcaldía de Caracas
├── pdf_extractor.py        # Extracción de PDFs
└── utils.py                # Funciones comunes
```

### Ejemplo: Collector ONAPRE

```python
# src/collectors/fiscal/onapre_collector.py
import requests
from bs4 import BeautifulSoup
import pdfplumber
from typing import List, Dict

class ONAPRECollector:
    """Colector de datos de la Oficina Nacional de Presupuesto"""
    
    BASE_URL = "https://www.onapre.gob.ve"
    REPORTS_URL = f"{BASE_URL}/sites/default/files/informes/"
    
    def __init__(self):
        self.session = requests.Session()
    
    def get_available_reports(self) -> List[Dict]:
        """Obtiene lista de informes disponibles"""
        response = self.session.get(self.REPORTS_URL)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        reports = []
        for link in soup.find_all('a', href=True):
            if link['href'].endswith('.pdf'):
                reports.append({
                    'title': link.text.strip(),
                    'url': f"{self.BASE_URL}{link['href']}",
                    'type': 'pdf'
                })
        
        return reports
    
    def download_report(self, url: str) -> bytes:
        """Descarga un informe PDF"""
        response = self.session.get(url)
        return response.content
    
    def extract_text_from_pdf(self, pdf_content: bytes) -> str:
        """Extrae texto de un PDF"""
        import io
        
        with pdfplumber.open(io.BytesIO(pdf_content)) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text() or ""
        
        return text
    
    def parse_budget_execution(self, text: str) -> Dict:
        """Parsea información de ejecución presupuestaria"""
        # Usar DeepSeek para extracción estructurada
        # o regex para datos específicos
        
        import re
        
        # Ejemplo: Extraer porcentaje de ejecución
        execution_match = re.search(
            r'(?:ejecución|ejecutado).*?(\d+[.,]?\d*)\s*%',
            text, re.IGNORECASE
        )
        
        return {
            'execution_percentage': float(
                execution_match.group(1).replace(',', '.')
            ) if execution_match else None,
            'raw_text': text[:1000]  # Primeros 1000 chars para revisión
        }
```

### Ejemplo: Collector CGR

```python
# src/collectors/fiscal/cgr_collector.py
import requests
from bs4 import BeautifulSoup

class CGRCollector:
    """Colector de la Contraloría General"""
    
    BASE_URL = "https://www.cgr.gob.ve"
    REPORTS_URL = f"{BASE_URL}/informes-de-gestion"
    
    def get_management_reports(self) -> list:
        """Obtiene informes de gestión anuales"""
        response = self.session.get(self.REPORTS_URL)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        reports = []
        for item in soup.find_all('div', class_='report-item'):
            title = item.find('h3').text.strip()
            year = item.find('span', class_='year').text.strip()
            url = item.find('a', class_='download')['href']
            
            reports.append({
                'title': title,
                'year': int(year),
                'url': url
            })
        
        return reports
    
    def extract_findings(self, text: str) -> dict:
        """Extrae hallazgos de auditoría"""
        # Buscar secciones clave
        findings = {
            'strengths': [],
            'weaknesses': [],
            'recommendations': []
        }
        
        # Lógica de extracción con regex o IA
        import re
        
        # Buscar recomendaciones
        rec_pattern = r'recomendación.*?:?\s*(.+?)(?:\n|$)'
        findings['recommendations'] = re.findall(rec_pattern, text, re.IGNORECASE)
        
        return findings
```

---

## 🔄 Flujo de Datos Fiscal

```
┌─────────────────────────────────────────────────────────────┐
│                    FLUJO DE DATOS FISCALES                   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   ONAPRE     │    │    CGR       │    │    MPPEF     │  │
│  │   (Presup.)  │    │  (Control)   │    │  (Ejecut.)   │  │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘  │
│         │                   │                   │           │
│         ▼                   ▼                   ▼           │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              COLECTORES FISCALES                     │   │
│  │  - Descarga PDFs                                     │   │
│  │  - Extracción de texto                               │   │
│  │  - Parsing estructurado (DeepSeek)                   │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                  │
│                          ▼                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              MODELO DE DATOS                         │   │
│  │  - BudgetExecution                                   │   │
│  │  - FiscalIndicators                                  │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                  │
│                          ▼                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              ANÁLISIS                                │   │
│  │  - Efecto del gasto público                          │   │
│  │  - Sostenibilidad fiscal                             │   │
│  │  - Nowcasting con ejecución                          │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 📋 Dependencias Adicionales

```txt
# Para procesamiento de PDFs
pdfplumber==0.10.3
PyPDF2==3.0.1

# Para monitoreo de cambios
changedetection.io  # O implementar propio

# Para extracción con IA
openai==1.10.0  # DeepSeek API
```

---

## 🎯 Prioridades de Implementación

### Inmediato (2 semanas)
1. **ONAPRE** - Informes de ejecución presupuestaria
2. **MPPEF** - Informes trimestrales

### Corto plazo (1 mes)
3. **CGR** - Informes de gestión anuales
4. **AN** - Leyes de presupuesto

### Mediano plazo (2 meses)
5. **Alcaldía Caracas** - Informes municipales
6. **Integración con modelos econométricos**

---

## 💡 Recomendaciones

1. **Contrastar fuentes:** Comparar datos de CGR con ONAPRE y MPPEF
2. **Aprovechar contexto:** Usar DeepSeek para resumir narrativas oficiales
3. **Iniciar con lo accesible:** CGR y AN suelen tener secciones más estructuradas
4. **Monitorear cambios:** Alertar cuando se publiquen nuevos informes

---

**Documento creado: Agosto 2025**
**Versión: 1.0**
