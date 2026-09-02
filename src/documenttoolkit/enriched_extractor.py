from .data_extractor import extract_data
from .llm_extractor import extraer_entidades_llm, sugerir_correccion_iban


def extract_data_enriched(texto: str, tipo_documento: str = "desconocido") -> dict:
    """
    Extracción determinista + enriquecimiento LLM.
    NOTA: NO reclasifica el documento. Eso ya lo hizo classify_document().
    """
    # 1. Extracción determinista actual (nunca se toca)
    resultado = extract_data(texto, tipo_documento)

    # 2. Entidades estructuradas del LLM (titular, entidad, periodo, etc.)
    entidades = extraer_entidades_llm(texto)
    if entidades:
        resultado["_llm_entidades"] = entidades

    # 3. Si el IBAN existe pero no es válido, intentar corrección OCR
    iban = resultado.get("IBAN")
    if iban and not resultado.get("IBAN_Valido"):
        correccion = sugerir_correccion_iban(iban, texto)
        if correccion:
            resultado["_llm_iban_corregido"] = correccion

    return resultado