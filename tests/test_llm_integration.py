"""
Test de integración mínimo para el módulo LLM.
No requiere que el servidor esté corriendo.
"""

import pytest
from documenttoolkit.llm_client import LLMClient
from documenttoolkit.llm_extractor import (
    sugerir_tipo_documento,
    extraer_entidades_llm,
    sugerir_correccion_iban
)


def test_cliente_sin_servidor_no_crashea():
    """Si no hay servidor, todo debe devolver None gracefully."""
    client = LLMClient(base_url="http://localhost:99999")
    assert client.is_available() is False
    assert client.chat([{"role": "user", "content": "hola"}]) is None


def test_extractor_llm_sin_servidor_devuelve_none(monkeypatch):
    """Las funciones de negocio deben fallar silenciosamente sin servidor."""
    # Forzamos a que el cliente crea que no hay servidor
    monkeypatch.setattr(LLMClient, "is_available", lambda self: False)

    assert sugerir_tipo_documento("cualquier texto") is None
    assert extraer_entidades_llm("cualquier texto") is None
    assert sugerir_correccion_iban("ES00", "contexto") is None


def test_enriched_no_rompe_data_extractor(monkeypatch):
    """Sin LLM, extract_data_enriched debe ser idéntico a extract_data."""
    from documenttoolkit.enriched_extractor import extract_data_enriched
    from documenttoolkit.data_extractor import extract_data

    monkeypatch.setattr(LLMClient, "is_available", lambda self: False)

    texto = "Documento de prueba sin datos bancarios"
    basico = extract_data(texto, "desconocido")
    enriquecido = extract_data_enriched(texto, "desconocido")

    # Debe contener exactamente las mismas claves base
    assert basico == enriquecido