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
- Modelo por defecto: `medium`, configurable al crear `MediaTranscriber`.
- Soporta video: `mp4`, `avi`, `mov`, `mkv`.
- Soporta audio: `mp3`, `wav`, `m4a`, `ogg`, `flac`.
- Los videos se procesan desde `data/input/videos/` y los audios desde `data/input/audios/`.
- El texto transcrito se procesa con el **mismo pipeline** que los PDFs: clasificación, extracción y guardado en base de datos.
- La base de datos distingue `tipo_entrada="video"` y `tipo_entrada="audio"`, con tipos `TRANSCRIPCION_VIDEO` y `TRANSCRIPCION_AUDIO`.
- Fase 1 de guionización implementada: alineación de palabras de Whisper con turnos de voz y renderizado de un guion teatral con tiempos, pausas, solapamientos y marcas de revisión.
- Fase 2 de guionización implementada: diarización automática de hablantes con `pyannote.audio` (comando aparte `python -m documenttoolkit.diarizar`).
- Los identificadores de hablante son anónimos (`HABLANTE_1`, `HABLANTE_2`…) hasta que un usuario los etiqueta manualmente con un rol procesal.
- El texto del guion no se reescribe: es el mismo reconocido por Whisper, agrupado por intervenciones.
- Si el audio tiene varios canales claramente separados, se usa `canal = hablante` sin necesidad de modelo de diarización.

### 🗄️ Persistencia y consultas
- **SQLite local** (`data/output/docs.db`) para evitar reprocesar archivos.
- **Herramienta de consulta** (`query_tool.py`) desde terminal:
  - `listar`, `buscar`, `ver`, `stats`, `exportar`.
  - Para guiones: `guion`, `etiquetar`, `fusionar`, `exportar-guion`, `cargar-turnos`, `regenerar-guion`.
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
├── *.pdf             → PDFs e imágenes
├── videos/           → Archivos de video
└── audios/           → Archivos de audio
               ↓
┌──────────────────────────────────────────────┐
│  Lectura y transcripción                     │
│  (pdf_reader / ocr_reader / media_transcriber)│
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
| Extracción PDF | `pypdf` | Texto nativo |
| OCR | `pytesseract` + `pdf2image` | Imágenes y PDFs escaneados |
| Transcripción | `faster-whisper` | CPU, `int8`, modelo `medium` por defecto |
| Diarización | `pyannote-audio` (extra opcional `[diarizacion]`) | Pipeline `speaker-diarization-community-1` por defecto |
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
│   │   ├── *.pdf
│   │   ├── videos/
│   │   └── audios/
│   └── output/
│       └── docs.db
├── scripts/
│   └── start_llm_server.sh
├── src/documenttoolkit/
│   ├── __init__.py
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
│   ├── media_transcriber.py
│   ├── video_transcriber.py      (compatibilidad)
│   ├── query_tool.py
│   └── diarizar.py
├── tests/
│   ├── test_ocr_data.py
│   ├── test_llm_integration.py
│   ├── test_video.py
│   ├── test_audio.py
│   ├── test_media_transcriber.py
│   └── test_diarizar.py
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

**Con diarización de hablantes (opcional)**
```
pip install -e ".[diarizacion]"
```

## Requisitos del sistema

    Python 3.12+
    Tesseract OCR (apt install tesseract-ocr tesseract-ocr-spa en Ubuntu)
    llama.cpp compilado con soporte CUDA (si dispones de GPU) o CPU.
    Poppler (apt install poppler-utils) para pdf2image.
    ffmpeg y ffprobe para extracción de audio y análisis de canales.
    Token de Hugging Face (`HF_TOKEN`) con acceso aceptado al pipeline de diarización si se usa `pyannote.audio`.

## ▶️ Uso

El flujo habitual es: **procesar** → **diarizar** (solo audio/video) → **consultar/editar**.

### 1. Procesar documentos (PDFs + audio/video)

Opcional: arrancar el servidor LLM para enriquecimiento:
```bash
./scripts/start_llm_server.sh
```

Ejecutar el pipeline principal:
```bash
python -m documenttoolkit.main
```

La primera vez procesa todo. Las siguientes ejecuciones saltan los archivos ya indexados en `data/output/docs.db`.
- PDFs: `data/input/`
- Vídeos: `data/input/videos/`
- Audios: `data/input/audios/`

### 2. Reprocesar un archivo ya leído

Si cambias un archivo (por ejemplo, una transcripción corregida) o quieres forzar que `main` lo vuelva a procesar:

```bash
python -m documenttoolkit.query_tool reprocesar "nombre_del_archivo.pdf"
```

La siguiente ejecución de `python -m documenttoolkit.main` reprocesará ese archivo.

### 3. Diarizar un audio o video ya procesado

Este paso es **opcional** y se ejecuta después de `main`. Divide la transcripción en intervenciones de hablante.

Requisitos:
```bash
pip install -e ".[diarizacion]"
export HF_TOKEN="tu_token_de_hugging_face"
```

Ejemplos:
```bash
# Dejar que el modelo estime el número de hablantes
python -m documenttoolkit.diarizar "nombre_del_archivo.wav"

# Forzar un número concreto de hablantes
python -m documenttoolkit.diarizar "nombre_del_archivo.wav" --hablantes 2

# Forzar CPU (también se puede usar --device cuda o --device auto)
python -m documenttoolkit.diarizar "nombre_del_archivo.wav" --device cpu
```

Durante la ejecución:
- Extrae un WAV mono 16 kHz como base de tiempos y lo borra al terminar.
- Calcula el **hash SHA-256** del archivo original y lo guarda en los metadatos de la corrida. Es una huella digital para trazabilidad; **no se pide ni se usa en ejecuciones posteriores**, solo se registra una vez.
- Si detecta canales de audio claramente separados, asigna cada canal a un hablante sin cargar pyannote.
- Si no, usa `pyannote.audio` para diarizar.

### 4. Ver y editar el guion diarizado

```bash
# Mostrar guion por pantalla
python -m documenttoolkit.query_tool guion "nombre_del_archivo.wav"

# Asignar una etiqueta humana a un hablante
python -m documenttoolkit.query_tool etiquetar "nombre.wav" HABLANTE_1 "LETRADO DE LA PARTE ACTORA"

# Fusionar dos hablantes detectados en uno solo
python -m documenttoolkit.query_tool fusionar "nombre.wav" HABLANTE_2 HABLANTE_1

# Exportar guion a un archivo de texto
python -m documenttoolkit.query_tool exportar-guion "nombre.wav" data/output/guion.txt
```

### 5. Consultar la base de datos

```bash
# Estadísticas generales
python -m documenttoolkit.query_tool stats

# Listar últimos documentos
python -m documenttoolkit.query_tool listar

# Buscar una palabra en todo el texto
python -m documenttoolkit.query_tool buscar "pensión"

# Ver detalle de un documento
python -m documenttoolkit.query_tool ver "nombre_del_archivo.pdf"

# Exportar a JSON
python -m documenttoolkit.query_tool exportar data/output/resumen.json
```

### 6. Transcribir un video o audio de forma aislada

Para pruebas sin pasar por `main`:
```bash
python tests/test_video.py
python tests/test_audio.py
```
(Ajusta la ruta del fichero en el script antes de ejecutar.)


🧠 Filosofía de desarrollo

El proyecto se construye de forma incremental y deliberada:

    Determinista antes que mágico: las extracciones de IBAN, CCC y clasificación por reglas son rápidas, testeables y gratuitas. El LLM actúa como segunda opinión, nunca como reemplazo.
    Local antes que en la nube: todo el procesamiento (OCR, transcripción, inferencia) ocurre en la máquina local. Sin cuotas, sin latencia de red, sin enviar documentos judiciales o bancarios a terceros.
    Testeable desde el primer día: cada función nueva va acompañada de tests. Si el LLM no responde, el sistema sigue funcionando.
    Un solo pipeline para todas las fuentes: PDFs, imágenes escaneadas, audios y videos convergen en el mismo flujo de texto → clasificación → extracción → base de datos.


📌 Roadmap

    [x] Extracción y validación de IBAN/CCC
    [x] OCR automático con detección de PDFs escaneados
    [x] Clasificación híbrida (reglas + LLM local)
    [x] Persistencia SQLite con evitación de reprocesado
    [x] Transcripción de audio/video con Whisper
    [x] Herramienta de consulta por terminal
    [x] Diarización de hablantes en conversaciones
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

`chmod +x scripts/start_llm_server.sh`

`./scripts/start_llm_server.sh`     ← Ejecutar con ./

También puedes indicar modelo, capas GPU y contexto:

`./scripts/start_llm_server.sh "$HOME/Proyectos/llama/models/Qwen3-8B-Q4_K_M.gguf" 99 8192`


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
