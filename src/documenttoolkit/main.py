from documenttoolkit.llm_client import LLMClient
from .scanner import scan_documents
from .pdf_reader import extract_text_hibrida, nombre_forzar_ocr
from .classifier import classify_document
from .enriched_extractor import extract_data_enriched
from pathlib import Path
from .database import DocumentDatabase
from documenttoolkit.media_transcriber import (
    MediaTranscriber,
    transcribir_y_guardar,
    MEDIA_EXTENSIONS,
)
from documenttoolkit.config import DB_PATH, INPUT_VIDEO_DIR, INPUT_AUDIO_DIR


def scan_media_files():
    """Busca ficheros de audio y video en las carpetas dedicadas."""
    archivos = []
    for carpeta in (INPUT_VIDEO_DIR, INPUT_AUDIO_DIR):
        if not carpeta.exists():
            continue
        for elemento in carpeta.iterdir():
            if elemento.is_file() and elemento.suffix.lower() in MEDIA_EXTENSIONS:
                archivos.append(elemento)
    return archivos


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
db = DocumentDatabase(db_path=DB_PATH)

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

    forzar_ocr = nombre_forzar_ocr(documento.name)
    if forzar_ocr:
        print("🔠 Marcador OCR detectado en el nombre. Se forzará OCR completo.")

    texto, info_extraccion = extract_text_hibrida(
        documento,
        forzar_ocr=forzar_ocr,
    )

    metodo = info_extraccion["metodo_extraccion"]
    if metodo == "mixto":
        print(
            f"Texto híbrido extraído: "
            f"{len(info_extraccion['paginas_texto'])} página(s) nativas + "
            f"{len(info_extraccion['paginas_ocr'])} página(s) por OCR."
        )
    elif metodo == "ocr_forzado":
        print("Texto extraído por OCR forzado.")
    elif metodo == "ocr":
        print("Texto extraído por OCR (sin capa de texto nativo).")
    else:
        print("Texto extraído correctamente desde la capa nativa.")

    print("Número de caracteres:", len(texto))
    print(repr(texto[:100]))

    clase = classify_document(texto)
    print(clase)

    datos = extract_data_enriched(texto, clase)
    print(datos)

    # Guardamos metadatos de la extracción junto al resto de datos extraídos
    datos["metodo_extraccion"] = info_extraccion["metodo_extraccion"]
    datos["paginas_ocr"] = info_extraccion["paginas_ocr"]
    datos["paginas_texto"] = info_extraccion["paginas_texto"]
    datos["chars_nativo"] = info_extraccion["chars_nativo"]
    datos["chars_ocr"] = info_extraccion["chars_ocr"]

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

# ========== BUCLE DE AUDIO/VIDEO (al final) ==========
media = scan_media_files()

if media:
    print(f"\n🎬 {len(media)} fichero(s) de audio/video encontrado(s).")
    transcriber = MediaTranscriber()
    for fichero in media:
        if db.documento_existe(str(fichero.resolve())):
            print(f"⏩ Ya procesado: {fichero.name}")
            continue
        transcribir_y_guardar(fichero, db, transcriber)
else:
    print("\n🎬 No hay videos en data/input/videos/ ni audios en data/input/audios/")