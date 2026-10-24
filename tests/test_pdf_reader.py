import pytest
from documenttoolkit.pdf_reader import (
    extract_text_hibrida,
    nombre_forzar_ocr,
)


def test_nombre_forzar_ocr():
    assert nombre_forzar_ocr("doc OCR.pdf") is True
    assert nombre_forzar_ocr("doc_ocr.pdf") is True
    assert nombre_forzar_ocr("doc-ocr.PDF") is True
    assert nombre_forzar_ocr("doc ocr.pdf") is True
    assert nombre_forzar_ocr("doc ocr .pdf") is True
    assert nombre_forzar_ocr("documento.pdf") is False
    assert nombre_forzar_ocr("mi doc ocrono.pdf") is False
    assert nombre_forzar_ocr("Atestado 10 2 2025.pdf") is False


@pytest.mark.skip(reason="Requiere el PDF real de data/input y tarda ~2 min")
def test_extract_text_hibrida_atestado():
    """Verifica extracción híbrida sobre el PDF problemático."""
    texto, info = extract_text_hibrida("data/input/Atestado 10 2 2025.pdf")
    assert info["metodo_extraccion"] == "mixto"
    assert info["paginas_texto"] == [1]
    assert len(info["paginas_ocr"]) == 35
    assert len(texto) > 40000
    assert "GUARDIA CIVIL" in texto
