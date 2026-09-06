import re
import json
from typing import Optional, Dict
from .llm_client import LLMClient


def _client() -> LLMClient:
    """Instancia lazy del cliente."""
    return LLMClient()


def sugerir_tipo_documento(texto_muestra: str) -> Optional[str]:
    """
    Segunda opinión sobre el tipo de documento.
    No reemplaza tu clasificación actual.
    """
    client = _client()
    if not client.is_available():
        return None

    system = (
        "Eres un clasificador documental. "
        "Dado un fragmento de documento, responde ÚNICAMENTE una de estas etiquetas: "
        "EXTRACTO_BANCARIO, NOMINA, FACTURA, CONTRATO, ESCRITO_JUDICIAL, "
        "SENTENCIA, AUTO, NOTA_SIMPLE, APUD_ACTA, DESCONOCIDO. "
        "Sin explicaciones, solo la etiqueta en mayúsculas."
    )
    muestra = texto_muestra[:2000].replace("\n", " ")

    resp = client.chat([
        {"role": "system", "content": system},
        {"role": "user", "content": f"Fragmento:\n{muestra}\n\nEtiqueta:"}
    ], temperature=0.1, max_tokens=30)

    if not resp:
        return None

    resp = resp.strip().upper()
    validos = {"EXTRACTO_BANCARIO", "NOMINA", "FACTURA", "CONTRATO",
               "ESCRITO_JUDICIAL", "SENTENCIA", "AUTO", "NOTA_SIMPLE", "APUD_ACTA", "DESCONOCIDO"}
    for v in validos:
        if v in resp:
            return v
    return None


def extraer_entidades_llm(texto: str) -> Optional[Dict]:
    """
    Extrae entidades estructuradas: titular, entidad, periodo, etc.
    Devuelve un dict o None si el LLM no responde o el JSON es inválido.
    """
    client = _client()
    if not client.is_available():
        return None

    system = (
        "Extrae entidades del siguiente texto legal/bancario. "
        "Responde ÚNICAMENTE con un JSON válido y nada más. "
        "Campos: tipo_documento, entidad_bancaria, titular, periodo, "
        "total_importe (número o null), moneda (EUR o null), "
        "observaciones (texto breve o null). "
        "Si un dato no aparece, usa null. Sin markdown, sin explicaciones."
    )

    resp = client.chat([
        {"role": "system", "content": system},
        {"role": "user", "content": f"Texto:\n{texto[:3500]}\n\nJSON:"}
    ], temperature=0.1, max_tokens=400)

    if not resp:
        return None

    resp = re.sub(r"```(?:json)?\s*", "", resp).replace("```", "").strip()
    try:
        return json.loads(resp)
    except json.JSONDecodeError:
        return None


def sugerir_correccion_iban(iban_sospechoso: str, contexto: str) -> Optional[str]:
    """
    Si tu validador determinista dice que el IBAN es inválido,
    el LLM puede detectar errores tipográficos de OCR (O→0, etc.).
    """
    client = _client()
    if not client.is_available():
        return None

    system = (
        "Eres un validador bancario. Se te proporciona un IBAN marcado como inválido "
        "y su contexto en el documento. Indica si detectas un error tipográfico obvio. "
        "Responde ÚNICAMENTE con el IBAN corregido o la palabra 'INCORREGIBLE'."
    )

    resp = client.chat([
        {"role": "system", "content": system},
        {"role": "user", "content": (
            f"IBAN inválido: {iban_sospechoso}\n"
            f"Contexto en documento:\n{contexto[:1000]}\n\n"
            f"Respuesta:"
        )}
    ], temperature=0.1, max_tokens=40)

    if not resp or "INCORREGIBLE" in resp.upper():
        return None

    limpio = resp.replace(" ", "").upper()
    if len(limpio) == 24 and limpio.startswith("ES") and limpio[2:].isdigit():
        return limpio
    return None