from documenttoolkit.llm_client import LLMClient
from .scanner import scan_documents
from .pdf_reader import extract_text
from .classifier import classify_document
from .enriched_extractor import extract_data_enriched
from .ocr_reader import extract_text_ocr

if __name__ == "__main__":
    # Aviso informativo sobre el LLM
    llm = LLMClient()
    if not llm.is_available():
        print("⚠️  AVISO: llama.cpp server no está corriendo en localhost:8080")
        print("   Los resultados NO tendrán enriquecimiento LLM.")
        print("   Para activarlo: ./scripts/start_llm_server.sh\n")
    else:
        print("✅ LLM local conectado (localhost:8080)\n")
        
documentos = scan_documents()
for documento in documentos:
    print("\n==============================")
    print("Archivo:", documento.name)
    print("==============================")
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
