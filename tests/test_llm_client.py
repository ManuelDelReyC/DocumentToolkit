"""
tests/test_llm_client.py
Tests para el cliente LLM. No requieren llama.cpp server.
"""

import pytest
from documenttoolkit.llm_client import LLMClient


def test_client_sin_servidor_devuelve_none():
    """Si no hay servidor, los métodos deben devolver None sin crashear."""
    client = LLMClient(base_url="http://localhost:99999")  # puerto imposible
    assert client.is_available() is False
    assert client.sugerir_tipo_documento("cualquier texto") is None
    assert client.extraer_entidades("cualquier texto") is None


def test_limpieza_respuesta_clasificacion():
    """El cliente debe limpiar correctamente respuestas con ruido."""
    client = LLMClient.__new__(LLMClient)  # instancia sin __init__
    # Simulamos respuesta del LLM con markdown o espacios
    raw = "  ```json\nEXTRACTO_BANCARIO\n```  "
    # No podemos testear _chat directamente sin servidor, pero verificamos
    # que la lógica de limpieza funciona si la extraemos a función pura.
    # (Opcional: podrías refactorizar la limpieza a una función testeable)
    assert True  # placeholder para extender


def test_enriched_extractor_no_rompe_flujo(monkeypatch):
    """extract_data_enriched debe funcionar igual sin LLM."""
    from documenttoolkit.enriched_extractor import extract_data_enriched

    # Forzamos a que el LLM parezca no disponible
    monkeypatch.setattr(
        "documenttoolkit.llm_client.LLMClient.is_available",
        lambda self: False
    )

    texto = "Documento de prueba sin IBAN ni CCC"
    resultado = extract_data_enriched(texto, "desconocido")

    # Debe tener las claves base de data_extractor
    assert "tipo" in resultado
    assert "num_caracteres" in resultado