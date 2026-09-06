from documenttoolkit.scanner import scan_documents
from documenttoolkit.pdf_reader import extract_text
from documenttoolkit.ocr_reader import extract_text_ocr
from pathlib import Path
import re

def score_tipo(texto):
    texto_norm = texto.upper()
    # Fragmentos relevantes
    inicio = texto_norm[:3000]
    final = texto_norm[-3000:]    
    scores = {
        "AUTO": 0,
        "SENTENCIA": 0,
        "ESCRITO_JUDICIAL": 0,
        "CONTRATO": 0,
        "NOTA_SIMPLE": 0,
        "APUD_ACTA": 0,
    }

    # ==========================================================
    # SENTENCIA
    # ==========================================================

    if re.search(r"\bSENTENCIA\b", inicio):
        scores["SENTENCIA"] += 15

    if "EN NOMBRE DE S.M. EL REY" in inicio:
        scores["SENTENCIA"] += 20

    if "FALLAMOS" in texto_norm:
        scores["SENTENCIA"] += 15

    if "FALLO" in final:
        scores["SENTENCIA"] += 10

    if "ANTECEDENTES DE HECHO" in texto_norm:
        scores["SENTENCIA"] += 5

    if "FUNDAMENTOS DE DERECHO" in texto_norm:
        scores["SENTENCIA"] += 5


    # ==========================================================
    # AUTO
    # ==========================================================

    if re.search(r"^\s*AUTO\b", inicio):
        scores["AUTO"] += 20

    if re.search(r"\bAUTO\s+(N[ÚU]MERO|N[º°.]|DE FECHA)\b", inicio):
        scores["AUTO"] += 15

    if re.search(r"\bAUTO\s*:\s*\d+/\d+\b", inicio):
        scores["AUTO"] += 15

    if "RAZONAMIENTOS JURÍDICOS" in texto_norm:
        scores["AUTO"] += 6

    if "PARTE DISPOSITIVA" in texto_norm:
        scores["AUTO"] += 6

    if "DISPONGO" in final:
        scores["AUTO"] += 8

    if "SE ACUERDA" in final:
        scores["AUTO"] += 5


    # ==========================================================
    # ESCRITO JUDICIAL
    # ==========================================================

    if re.search(r"\bAL JUZGADO\b", inicio):
        scores["ESCRITO_JUDICIAL"] += 15

    if re.search(r"\bAL TRIBUNAL\b", inicio):
        scores["ESCRITO_JUDICIAL"] += 15

    if "SUPLICO AL JUZGADO" in texto_norm:
        scores["ESCRITO_JUDICIAL"] += 20

    if "SUPLICO AL TRIBUNAL" in texto_norm:
        scores["ESCRITO_JUDICIAL"] += 20

    if "OTROSÍ DIGO" in texto_norm:
        scores["ESCRITO_JUDICIAL"] += 10

    if "DIGO:" in texto_norm:
        scores["ESCRITO_JUDICIAL"] += 5

    if "ES JUSTICIA QUE PIDO" in texto_norm:
        scores["ESCRITO_JUDICIAL"] += 8

    if "EN NOMBRE Y REPRESENTACIÓN DE" in texto_norm:
        scores["ESCRITO_JUDICIAL"] += 8


    # ==========================================================
    # CONTRATO
    # ==========================================================

    if "CONTRATO" in inicio:
        scores["CONTRATO"] += 15

    if "REUNIDOS" in texto_norm:
        scores["CONTRATO"] += 6

    if "INTERVIENEN" in texto_norm:
        scores["CONTRATO"] += 6

    if "EXPONEN" in texto_norm:
        scores["CONTRATO"] += 4

    if "ESTIPULACIONES" in texto_norm:
        scores["CONTRATO"] += 8

    if "CLÁUSULA PRIMERA" in texto_norm:
        scores["CONTRATO"] += 8

    if "CLÁUSULA SEGUNDA" in texto_norm:
        scores["CONTRATO"] += 5


    # ==========================================================
    # NOTA SIMPLE
    # ==========================================================

    if "NOTA SIMPLE" in inicio:
        scores["NOTA_SIMPLE"] += 20

    if "REGISTRO DE LA PROPIEDAD" in inicio:
        scores["NOTA_SIMPLE"] += 15

    if "TITULARIDAD" in texto_norm:
        scores["NOTA_SIMPLE"] += 5

    if "CARGAS" in texto_norm:
        scores["NOTA_SIMPLE"] += 5

    if "INSCRIPCIÓN" in texto_norm:
        scores["NOTA_SIMPLE"] += 3

    if "FINCA" in texto_norm:
        scores["NOTA_SIMPLE"] += 2


    # ==========================================================
    # APUD_ACTA
    # ==========================================================

    if "APUD-ACTA" in inicio:
        scores["APUD_ACTA"] += 20

    if "APUD ACTA" in inicio:
        scores["APUD_ACTA"] += 20    

    ordenados = sorted(
        scores.items(),
        key=lambda x: x[1],
        reverse=True
    )

    mejor_tipo, mejor_score = ordenados[0]
    segundo_tipo, segundo_score = ordenados[1]

    # Umbral de confianza
    if mejor_score >= 15 and (mejor_score - segundo_score) >= 5:
        return mejor_tipo

    return None


def classify_document(texto):
    texto_norm = texto.upper()
    tipo_legal = score_tipo(texto)

    if "RECIBO DE PRÉSTAMO" in texto_norm:
        return "HIPOTECA"
    elif "EXTRACTO" in texto_norm or "OPERACIONES" in texto_norm:
        return "EXTRACTO_BANCARIO"
    elif "BIZUM" in texto_norm or "TRANSFERENCIA" in texto_norm:
        return "TRANSFERENCIA_BANCARIA"
    elif "DETALLE DEL MOVIMIENTO" in texto_norm or "LIQUIDACI" in texto_norm or "DOMICILIACI" in texto_norm or "ADEUDO" in texto_norm:
        return "MOVIMIENTO_BANCARIO"
    elif tipo_legal:
        if tipo_legal:
            return tipo_legal
    return "OTRO"

documentos = scan_documents()
for documento in documentos:
    # Convertimos a ruta absoluta para la base de datos
    ruta_absoluta = str(documento.resolve())

    
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

    legal_score = score_tipo(texto)
    print("Clase legal", legal_score)
    
    clase = classify_document(texto)
    print(clase)

