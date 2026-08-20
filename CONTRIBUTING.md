# Contribuir a Economía Venezuela

¡Gracias por tu interés en contribuir! Este documento explica cómo participar en el desarrollo del proyecto.

## 🚀 Configuración del Entorno de Desarrollo

```bash
# 1. Clonar el repositorio
git clone https://github.com/betobeto00/economia-venezuela.git
cd economia-venezuela

# 2. Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus API keys (al menos DATABASE_URL)

# 5. Crear base de datos (si usas Docker)
docker compose up -d db redis
```

## 🧪 Ejecutar los Tests

```bash
# Ejecutar todos los tests
pytest

# Ejecutar tests verbose
pytest -v

# Ejecutar tests de un módulo específico
pytest tests/test_econometric.py
pytest tests/test_collectors_market.py
pytest tests/test_surveys.py

# Ejecutar con cobertura
pytest --cov=src --cov-report=term-missing
```

## 📏 Estilo de Código

El proyecto usa las siguientes herramientas:

| Herramienta | Uso | Comando |
|-------------|-----|---------|
| **black** | Formateo automático | `black src/ tests/` |
| **flake8** | Linting | `flake8 src/ tests/` |
| **pytest** | Tests | `pytest` |

### Convenciones

- **Docstrings**: Google style para funciones y clases públicas
- **Nombres**: `snake_case` para funciones/variables, `PascalCase` para clases
- **Imports**: agrupados (stdlib → third-party → local), ordenados alfabéticamente
- **Type hints**: usar en signatures públicas cuando sea claro
- **Tests**: un archivo `test_<modulo>.py` por módulo, clases `Test<Nombre>`

## 🔧 Estructura del Proyecto

```
src/
├── collectors/       # Recolección de datos (apis, scraping)
├── analyzers/        # Análisis (econometría, IA, sentimiento)
├── models/           # Modelos Pydantic
├── db/               # Persistencia (ORMs, repositorios)
├── dashboard/        # Streamlit
├── scripts/          # CLIs para ejecución manual
├── scheduler/        # APScheduler jobs
└── config.py         # Configuración centralizada
```

## 📋 Cómo Proponer un Cambio

1. **Abrir un issue** primero para discutir el cambio (especialmente para collectors nuevos o cambios de arquitectura)
2. **Crear una rama** desde `master`: `git checkout -b feat/nombre-descriptivo`
3. **Implementar** el cambio con tests
4. **Ejecutar** `pytest` para asegurar que todo pasa
5. **Hacer commit** con mensaje descriptivo (ver abajo)
6. **Abrir un Pull Request** describiendo qué hace el cambio y por qué

### Convención de Commits

```
tipo: descripción corta

Descripción más detallada (opcional).

🤖 Generated with Codebuff
Co-Authored-By: Codebuff <noreply@codebuff.com>
```

**Tipos**: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`

## 🆕 Agregar un Nuevo Collector

1. Crear `src/collectors/<categoria>/<nombre>_collector.py`
2. Implementar la clase collector siguiendo el patrón existente
3. Crear tests en `tests/test_collectors_<nombre>.py`
4. Registrar en `src/scripts/collect_market.py` si aplica
5. Documentar la fuente en `knowledge.md`
6. Añadir variables de entorno en `src/config.py` y `.env.example`

## 🐛 Reportar Bugs

Al reportar un bug, incluir:
- Pasos para reproducir
- Comportamiento esperado vs actual
- Traceback completo si es un error
- Versión de Python y sistema operativo

## 📞 Preguntas

Si tienes dudas, abre un issue con la etiqueta `question`.
