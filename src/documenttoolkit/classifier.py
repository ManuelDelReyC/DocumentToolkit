from .llm_extractor import sugerir_tipo_documento

def classify_document(texto):
    texto_norm = texto.upper()
    if "AUTO" in texto_norm:
        return "AUTO"
    elif "SENTENCIA" in texto_norm or "FALLO" in texto_norm:
        return "SENTENCIA"    
    elif "DEMANDA" in texto_norm or "DILIGENCIA" in texto_norm or "ANTECEDENTES DE HECHO" in texto_norm:
        return "ESCRITO_JUDICIAL"
    elif "RECIBO DE PRÉSTAMO" in texto_norm:
        return "HIPOTECA"
    elif "EXTRACTO" in texto_norm or "OPERACIONES" in texto_norm:
        return "EXTRACTO_BANCARIO"
    elif "BIZUM" in texto_norm or "TRANSFERENCIA" in texto_norm:
        return "TRANSFERENCIA_BANCARIA"
    elif "DETALLE DEL MOVIMIENTO" in texto_norm or "LIQUIDACI" in texto_norm or "DOMICILIACI" in texto_norm or "ADEUDO" in texto_norm:
        return "MOVIMIENTO_BANCARIO"

    tipo_llm = sugerir_tipo_documento(texto)
    if tipo_llm and tipo_llm != "DESCONOCIDO":
        return tipo_llm
    return "OTRO"