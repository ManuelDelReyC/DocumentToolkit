from scanner import scan_documents
from pdf_reader import extract_text
from classifier import classify_document
from data_extractor import extract_data
from ocr_reader import extract_text_ocr

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
    datos = extract_data(texto, clase)
    print(datos)