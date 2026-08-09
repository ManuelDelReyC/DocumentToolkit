def classify_document(texto):
    texto_norm = texto.upper()
    if "RECIBO DE PRÉSTAMO" in texto_norm:
        return "HIPOTECA"
    elif "EXTRACTO" in texto_norm or "OPERACIONES" in texto_norm:
        return "EXTRACTO_BANCARIO"
    elif "DETALLE DEL MOVIMIENTO" in texto_norm:
        return "MOVIMIENTO_BANCARIO"
    return "OTRO"