# AGENTS.md — DocumentToolkit

Compact guidance for OpenCode sessions working on DocumentToolkit.

## Project basics

- Python 3.12+, `src/` layout, package name `documenttoolkit`.
- Install editable: `pip install -e .` from repo root.
- Dev/test extras: `pip install -e ".[dev]"` (only adds `pytest`).
- A `.venv/` already exists; activate with `source .venv/bin/activate`.

## Running the app

- Modules can be run from any working directory; paths resolve from the repo root via `config.py`.
- Main pipeline: `python -m documenttoolkit.main`
  - Scans `data/input/*.pdf`, extracts text with `pdf_reader.extract_text_hibrida`, classifies, enriches, persists to `data/output/docs.db`.
  - PDF extraction is hybrid (page-level): uses the native text layer when it is substantial; otherwise OCRs the page. This fixes mixed PDFs with a digital cover page plus scanned image pages.
  - To force full-document OCR, rename the file so its stem ends in `OCR`, e.g. `documento OCR.pdf`, `doc_ocr.pdf`, `doc-ocr.PDF`.
  - Then processes `data/input/videos/*.{mp4,avi,mov,mkv}` and `data/input/audios/*.{mp3,wav,m4a,ogg,flac}` via Whisper.
  - Uses `MediaTranscriber` from `media_transcriber.py`, with Faster-Whisper on CPU and `int8`; the default model is `medium`.
  - Stores media as `tipo_entrada="video"` or `tipo_entrada="audio"`, using `TRANSCRIPCION_VIDEO` or `TRANSCRIPCION_AUDIO`.
  - Skips files already in the DB unless marked for reprocessing.
- Optional local LLM enriches classification/extraction; the app degrades gracefully if `localhost:8080` is down.

## Query tool

- `python -m documenttoolkit.query_tool stats`
- `python -m documenttoolkit.query_tool listar [--tipo T] [--dominio D] [--limite N]`
- `python -m documenttoolkit.query_tool buscar "palabra"`
- `python -m documenttoolkit.query_tool ver <nombre_archivo>`
- `python -m documenttoolkit.query_tool exportar data/output/resumen.json`
- `python -m documenttoolkit.query_tool reprocesar <nombre_archivo>`

### Guionización (fase 1: alineación y formato)

- `python -m documenttoolkit.query_tool guion <nombre_archivo>` muestra el guion diarizado.
- `python -m documenttoolkit.query_tool etiquetar <nombre> HABLANTE_1 "LETRADO DE LA PARTE ACTORA"`
- `python -m documenttoolkit.query_tool fusionar <nombre> HABLANTE_2 HABLANTE_1`
- `python -m documenttoolkit.query_tool exportar-guion <nombre> data/output/guion.txt`
- `python -m documenttoolkit.query_tool cargar-turnos <nombre> turnos.json` carga turnos sintéticos para probar sin pyannote.
- `python -m documenttoolkit.query_tool regenerar-guion <nombre>` regenera el guion desde `segmentos_asr` + `turnos_diarizacion`.

La transcripción cruda de Whisper se conserva en `documentos.texto_extraido`. Los segmentos con palabras, turnos de voz, mapa de etiquetas y turnos del guion se guardan en tablas hijas (`segmentos_asr`, `turnos_diarizacion`, `hablantes`, `turnos_guion`).

## LLM server

- Helper script: `./scripts/start_llm_server.sh [ruta_modelo] [ngl] [ctx]`
  - Default binary: `$HOME/Proyectos/llama/src/llama.cpp/build/bin/llama-server`
  - Default model: `$HOME/Proyectos/llama/models/Qwen3-Coder-30B-A3B-Instruct.Q4_K_M.gguf`
  - Default GPU layers: `auto` (offload all layers that fit in the 16 GB VRAM)
  - Default context size: `8192`
  - Listens on `127.0.0.1:8080`.
- Override defaults via environment variables:
  - `LLAMA_SERVER` for the binary path.
  - `LLAMA_MODEL` for the model path.
  - `LLAMA_NGL`, `LLAMA_CTX` for GPU layers/context.
  - `LLAMA_EXTRA` for extra llama-server flags.
- To stop: `kill -15 $(pgrep -f "llama-server")`

## System dependencies

- Tesseract OCR with Spanish: `tesseract-ocr`, `tesseract-ocr-spa`
- Poppler: `poppler-utils`
- Whisper may need `ffmpeg` for some video formats.

## Tests

- Run: `python -m pytest` from repo root.
- Current state: `test_llm_client.py` fails because it calls `client.sugerir_tipo_documento()` and `client.extraer_entidades()`, which do not exist on `LLMClient`; those functions live in `documenttoolkit.llm_extractor`.
- `test_score_classifier.py` and `test_video.py` operate on real files in `data/input/` and can be slow or fail if inputs are missing.
- `test_audio.py` is the equivalent manual test for `data/input/audios/`; `test_media_transcriber.py` covers extension/type detection without loading Whisper.
- `test_guion.py` tests the alignment and theatrical-format rendering with synthetic data; no models are loaded.
- `test_database_diarizacion.py` tests the new child tables used for diarization.

## Dependencies

- `pdf_reader.py` uses `pypdf` for native PDF text extraction.
- `pyproject.toml` and `requirements.txt` both declare `pypdf` and `faster-whisper`.

## Paths

- `config.py` is the single source of truth for project paths.
- `scanner.py`, `main.py`, `database.py`, and `query_tool.py` all resolve paths from the repo root via `config.py`.
- `INPUT_AUDIO_DIR` points to `data/input/audios/`; `INPUT_VIDEO_DIR` points to `data/input/videos/`.
- Modules can be run from any working directory and still locate `data/input/` and `data/output/docs.db` correctly.

## Unused/placeholder code

- `src/documenttoolkit/ingestors/pdf_ingestor.py` is empty.
- `video_ingestor.py` is empty; the app uses `media_transcriber.py` (previously `video_transcriber.py`).
- `video_transcriber.py` is now a compatibility wrapper that re-exports `MediaTranscriber` as `VideoTranscriber`.
