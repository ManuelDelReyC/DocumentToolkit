from documenttoolkit.llm_client import LLMClient
from .scanner import scan_documents
from .pdf_reader import extract_text
from .classifier import classify_document
from .enriched_extractor import extract_data_enriched
from .ocr_reader import extract_text_ocr
from pathlib import Path
from .database import DocumentDatabase
from documenttoolkit.video_transcriber import VideoTranscriber, transcribir_y_guardar
from documenttoolkit.config import DB_PATH, INPUT_VIDEO_DIR


if __name__ == "__main__":
    # Aviso informativo sobre el LLM
    llm = LLMClient()
    if not llm.is_available():
        print("⚠️  AVISO: llama.cpp server no está corriendo en localhost:8080")
        print("   Los resultados NO tendrán enriquecimiento LLM.")
        print("   Para activarlo: ./scripts/start_llm_server.sh\n")
    else:
        print("✅ LLM local conectado (localhost:8080)\n")

# Inicializa la base de datos (se crea automáticamente si no existe)
db = DocumentDatabase(db_path="data/output/docs.db")

documentos = scan_documents()
for documento in documentos:
    # Convertimos a ruta absoluta para la base de datos
    ruta_absoluta = str(documento.resolve())

    
    print("\n==============================")
    print("Archivo:", documento.name)
    print("==============================")

    # Si ya está en la base y no está marcado para reprocesar, lo saltamos
    if db.documento_existe(ruta_absoluta):
        print("⏩ Ya procesado y guardado en base de datos. Saltando.")
        continue

    texto = extract_text(documento)

    if texto:
        print("Texto extraído correctamente.")

    else:
        print("El documento no contiene texto. Extraccion por OCR.")
        texto = extract_text_ocr(documento)

    print("Número de caracteres:", len(texto))
    print(repr(texto[:100]))

    clase = classify_document(texto)
    print(clase)

    datos = extract_data_enriched(texto, clase)
    print(datos)

    # GUARDAR EN BASE DE DATOS (nuevo bloque, al final del bucle)
    db.guardar_documento(
        ruta=ruta_absoluta,
        tipo_entrada="pdf",
        tipo_doc=clase,
        texto=texto,
        num_chars=len(texto),
        dominio=datos.get("dominio", "desconocido"),
        datos_dict=datos
    )
    print("💾 Guardado en base de datos.")

# ========== BUCLE DE VIDEOS (nuevo, al final) ==========
videos = list(INPUT_VIDEO_DIR.glob("*.mp4")) + \
         list(INPUT_VIDEO_DIR.glob("*.mp3")) + \
         list(INPUT_VIDEO_DIR.glob("*.wav")) + \
         list(INPUT_VIDEO_DIR.glob("*.m4a")) + \
         list(INPUT_VIDEO_DIR.glob("*.avi")) + \
         list(INPUT_VIDEO_DIR.glob("*.mov"))

if videos:
    print(f"\n🎬 {len(videos)} video(s)/audio(s) encontrado(s).")
    transcriber = VideoTranscriber()
    for video in videos:
        if db.documento_existe(str(video.resolve())):
            print(f"⏩ Ya procesado: {video.name}")
            continue
        transcribir_y_guardar(video, db, transcriber)
else:
    print("\n🎬 No hay videos/audios en data/input/videos/")