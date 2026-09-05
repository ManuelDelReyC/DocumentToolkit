# DocumentToolkit

Herramienta en Python para la **extracción, clasificación, enriquecimiento y persistencia de información procedente de documentos heterogéneos**: PDFs bancarios y judiciales, imágenes escaneadas (OCR), y archivos de audio/video transcritos localmente.

El proyecto nace como ejercicio práctico para aprender Python, procesamiento de documentos, expresiones regulares, testing, empaquetado con `pyproject.toml`, control de versiones con Git, e integración progresiva de **Inteligencia Artificial local** (sin costes de API ni dependencias de terceros en la nube).

---

## ✨ Características actuales

### 📄 Procesamiento de documentos
- **Extracción de texto** de PDFs con texto nativo.
- **OCR automático** para PDFs escaneados e imágenes (Tesseract).
- **Detección inteligente**: decide automáticamente si un PDF necesita OCR.
- **Extracción determinista** de datos bancarios: IBAN, CCC, titular.
- **Validación matemática** de IBAN (módulo 97) y CCC (dígitos de control).

### 🏷️ Clasificación inteligente
- **Clasificación híbrida**: reglas deterministas rápidas + fallback a **LLM local** (llama.cpp) cuando las reglas no coinciden.
- Dominios soportados: bancario (`EXTRACTO_BANCARIO`, `MOVIMIENTO_BANCARIO`, `TRANSFERENCIA_BANCARIA`, `NÓMINA`...) y judicial (`ESCRITO_JUDICIAL`, `SENTENCIA`, `AUTO`, `CONTRATO`).

### 🧠 Enriquecimiento con IA local
- Integración nativa con **llama.cpp server** (localhost:8080).
- Modelos probados: Qwen 2.5 Coder 7B, Mistral 7B, Phi-4 Mini.
- **Extracción de entidades** estructuradas por el LLM (titular, entidad, periodo, partes judiciales, etc.).
- **Corrección de IBANs inválidos** detectando errores tipográficos de OCR (O→0, espacios, etc.).
- Funcionamiento **degradado**: si el servidor LLM no está activo, todo el pipeline sigue operativo con extracción puramente determinista.

### 🎬 Transcripción de audio y video
- Transcripción local con **Faster-Whisper** (CPU, optimizado `int8`).
- Soporta: `mp4`, `mp3`, `wav`, `m4a`, `avi`, `mov`, `mkv`, `ogg`.
- El texto transcrito se procesa con el **mismo pipeline** que los PDFs: clasificación, extracción y guardado en base de datos.

### 🗄️ Persistencia y consultas
- **SQLite local** (`data/output/docs.db`) para evitar reprocesar archivos.
- **Herramienta de consulta** (`query_tool.py`) desde terminal:
  - `listar`, `buscar`, `ver`, `stats`, `exportar`.
- Visualización directa con cualquier cliente SQL (HeidiSQL, DBeaver, sqlite3 CLI).

### 🧪 Calidad de código
- Tests automatizados con `pytest`.
- Estructura `src/` empaquetable.
- Instalación editable: `pip install -e .`.
- Dependencias declaradas en `pyproject.toml`.

---

## 🏗️ Arquitectura
```
data/input/
├── pdf/              → PDFs e imágenes
└── videos/           → Audio y video
               ↓
┌──────────────────────────────────────────────┐
│  Ingestores (pdf_reader / video_transcriber) │
└──────────────────────────────────────────────┘
               ↓
          Texto plano
               ↓
┌──────────────────────────────────────────────┐
│  Clasificación híbrida                       │
│  ├── Reglas deterministas (regex, keywords)  │
│  └── Fallback LLM (llama.cpp local)          │
└──────────────────────────────────────────────┘
               ↓
┌──────────────────────────────────────────────┐
│  Extracción de datos                         │
│  ├── Determinista (IBAN, CCC, titular, DNI)  │
│  └── Enriquecida con LLM (entidades,         │
│      correcciones, metadatos judiciales)     │
└──────────────────────────────────────────────┘
               ↓
┌──────────────────────────────────────────────┐
│  SQLite (docs.db)                            │
│  └── Evita reprocesar archivos ya indexados  │
└──────────────────────────────────────────────┘
               ↓
┌──────────────────────────────────────────────┐
│  Query Tool (listar, buscar, exportar...)    │
└──────────────────────────────────────────────┘
```

---

## 🛠️ Stack tecnológico

| Componente | Tecnología | Notas |
|------------|-----------|-------|
| Lenguaje | Python 3.12+ | |
| Extracción PDF | `pdfplumber` | Texto nativo |
| OCR | `pytesseract` + `pdf2image` | Imágenes y PDFs escaneados |
| Transcripción | `faster-whisper` | CPU, modelos `small`/`base` |
| IA Local | `llama.cpp` (servidor) | Via API OpenAI-compatible |
| Cliente LLM | `urllib` nativo | Sin dependencias pesadas |
| Base de datos | `sqlite3` (stdlib) | Sin instalación adicional |
| Tests | `pytest` | |
| Empaquetado | `setuptools` + `pyproject.toml` | Modo editable |

---

## 📁 Estructura del proyecto

DocumentToolkit/
```
├── data/
│   ├── input/
│   │   ├── pdf/
│   │   └── videos/
│   └── output/
│       └── docs.db
├── scripts/
│   └── start_llm_server.sh
├── src/documenttoolkit/
│   ├── init.py
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── scanner.py
│   ├── pdf_reader.py
│   ├── ocr_reader.py
│   ├── classifier.py
│   ├── data_extractor.py
│   ├── extractores.py
│   ├── enriched_extractor.py
│   ├── llm_client.py
│   ├── llm_extractor.py
│   ├── video_transcriber.py
│   └── query_tool.py
├── tests/
│   ├── test_ocr_data.py
│   ├── test_llm_integration.py
│   └── test_video.py
├── pyproject.toml
├── README.md
└── .gitignore
```

---

## 🚀 Instalación


**Clonar**
```
bash

git clone https://github.com/ManuelDelReyC/DocumentToolkit.git

cd DocumentToolkit
```

**Entorno virtual**
```python -m venv .venv
source .venv/bin/activate
```

**Instalación editable con dependencias**
```
pip install -e .
```
## Requisitos del sistema

    Python 3.12+
    Tesseract OCR (apt install tesseract-ocr tesseract-ocr-spa en Ubuntu)
    llama.cpp compilado con soporte CUDA (si dispones de GPU) o CPU.
    Poppler (apt install poppler-utils) para pdf2image.

## ▶️ Uso

1. Procesar documentos (PDFs + Videos)

   Opcional: arrancar el servidor LLM para enriquecimiento:
   `./scripts/start_llm_server.sh`

   Ejecutar el pipeline:

   `python -m documenttoolkit.main`

   La primera vez procesa todo. Las siguientes, salta archivos ya indexados en la base de datos.

2. Consultar la base de datos
```
   # Estadísticas generales
   python -m documenttoolkit.query_tool stats

   # Listar últimos documentos
   python -m documenttoolkit.query_tool listar

   # Buscar palabra en todo el texto
   python -m documenttoolkit.query_tool buscar "pensión"

   # Ver detalle de un documento
   python -m documenttoolkit.query_tool ver "nombre_del_archivo.pdf"

   # Exportar a JSON
   python -m documenttoolkit.query_tool exportar data/output/resumen.json

   3. Transcribir un video de forma aislada

   python tests/test_video.py
   (Ajusta la ruta del video en el script antes de ejecutar.)


🧠 Filosofía de desarrollo

El proyecto se construye de forma incremental y deliberada:

    Determinista antes que mágico: las extracciones de IBAN, CCC y clasificación por reglas son rápidas, testeables y gratuitas. El LLM actúa como segunda opinión, nunca como reemplazo.
    Local antes que en la nube: todo el procesamiento (OCR, transcripción, inferencia) ocurre en la máquina local. Sin cuotas, sin latencia de red, sin enviar documentos judiciales o bancarios a terceros.
    Testeable desde el primer día: cada función nueva va acompañada de tests. Si el LLM no responde, el sistema sigue funcionando.
    Un solo pipeline para todas las fuentes: PDFs, imágenes escaneadas y videos de juicios convergen en el mismo flujo de texto → clasificación → extracción → base de datos.


📌 Roadmap

    [x] Extracción y validación de IBAN/CCC
    [x] OCR automático con detección de PDFs escaneados
    [x] Clasificación híbrida (reglas + LLM local)
    [x] Persistencia SQLite con evitación de reprocesado
    [x] Transcripción de audio/video con Whisper
    [x] Herramienta de consulta por terminal
    [ ] Extractores especializados por dominio (bancario vs. judicial)
    [ ] Prompts específicos para documentos judiciales (partes, objeto, pretensiones)
    [ ] Búsqueda semántica con embeddings (ChromaDB/FAISS)
    [ ] Detección de contradicciones entre documentos
    [ ] Generación de resúmenes ejecutivos automáticos
    [ ] Interfaz web (Streamlit/Gradio) para consulta no técnica


📄 Licencia

Proyecto personal de aprendizaje. Uso libre para fines educativos y profesionales propios.
"No basta con que una extracción 'parezca funcionar'; los datos extraídos deben poder validarse."
```
---

## INTRUCCIONES DE USO


### Iniciar Entorno Virtual

`source .venv/bin/activate`


### Iniciar Cliente llama.cpp

#### Con Script

`cd ~/Proyectos/DocumentToolkit`    o donde tengas la carpeta

`chmod +x start_llm_server.sh`      ← CORRECCIÓN: +x, no -x

`./start_llm_server.sh`             ← Ejecutar con ./


#### Sin Script

```
"$HOME/Proyectos/llama/src/llama.cpp/build/bin/llama-server" \
  -m "$HOME/Proyectos/llama/models/qwen2.5-coder-7b-instruct-q4_k_m-00001-of-00002.gguf" \
  -ngl 12 -c 6144 --host 127.0.0.1 --port 8080
```

### Terminar cliente llama.cpp

Desde otro terminal ejecutar:

  `kill -15 $(pgrep -f "llama-server")`

#### Error de Memoria al Iniciar llama.cpp

Si da error de memoria revisar RAM. Si > 476 MB entonces 

1) Estas usando la entrada de Video de la Tarjeta Grafica --> Cambiar fuera de Tarjeta

2) Hay basura
Se comprueba con: 

   `nvidia-smi`

Para limpiar restos de la ejecucion anterior ejecutar:

  `kill -9 <PID>`

Si no hubiera procesos visibles probar:

  `sudo nvidia-smi --gpu-reset -i 0`


### GIT Steps

```
git status

git add .

git commit -m "[TU MENSAJE]"

git push
```

### Ejecutar Prorgama

#### Módulo

`python -m documenttoolkit.main`