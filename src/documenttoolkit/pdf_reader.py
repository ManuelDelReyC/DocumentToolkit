from pathlib import Path
from typing import Dict, Tuple, Any
from pypdf import PdfReader
from .ocr_reader import extract_text_ocr_paginas


def extract_text(pdf_path):
    reader = PdfReader(pdf_path)
    texto = ""
    for pagina in reader.pages:
        contenido = pagina.extract_text()

        if contenido:
            texto += contenido

    return texto.strip()


def _tiene_imagenes(pagina) -> bool:
    """Devuelve True si la página contiene al menos una imagen incrustada."""
    try:
        return len(list(pagina.images)) > 0
    except Exception:
        return False


def nombre_forzar_ocr(nombre_archivo: str) -> bool:
    """
    Detecta si el nombre del archivo indica que se debe forzar el OCR.
    Tras quitar la extensión, se considera marcador 'ocr' si el stem
    termina en 'ocr' ignorando espacios, guiones, puntos y barras bajas.
    Ejemplos válidos: 'doc OCR.pdf', 'doc_ocr.pdf', 'doc-ocr.PDF'.
    """
    stem = Path(nombre_archivo).stem
    normalizado = stem.rstrip(" ._-").lower()
    return normalizado.endswith("ocr")


def extract_text_hibrida(
    pdf_path,
    forzar_ocr: bool = False,
    umbral: int = 50,
) -> Tuple[str, Dict[str, Any]]:
    """
    Extrae texto de un PDF combinando capa de texto nativo y OCR.

    - Por defecto decide página a página: si una página tiene menos de
      ``umbral`` caracteres de texto nativo y contiene imágenes, se OCR-iza.
    - Si ``forzar_ocr`` es True, se ignora el texto nativo y se OCR-iza
      todo el documento.

    Devuelve (texto_completo, info), donde info contiene metadatos de la
    extracción (método usado, páginas OCR-izadas, caracteres por fuente).
    """
    reader = PdfReader(pdf_path)
    total_paginas = len(reader.pages)

    info_base = {
        "paginas_ocr": [],
        "paginas_texto": [],
        "chars_nativo": 0,
        "chars_ocr": 0,
    }

    if forzar_ocr:
        paginas_ocr = list(range(1, total_paginas + 1))
        ocr_por_pagina = extract_text_ocr_paginas(pdf_path, paginas_ocr)
        texto_final = "\n\n".join(
            ocr_por_pagina.get(p, "") for p in paginas_ocr
        ).strip()
        info = {
            **info_base,
            "metodo_extraccion": "ocr_forzado",
            "paginas_ocr": paginas_ocr,
            "chars_ocr": sum(len(t) for t in ocr_por_pagina.values()),
        }
        return texto_final, info

    # Primera pasada: decidir fuente de cada página
    paginas_a_ocr = []
    texto_por_pagina: Dict[int, str] = {}

    for idx, pagina in enumerate(reader.pages, start=1):
        contenido = (pagina.extract_text() or "").strip()
        if len(contenido) < umbral and _tiene_imagenes(pagina):
            paginas_a_ocr.append(idx)
        else:
            texto_por_pagina[idx] = contenido
            info_base["paginas_texto"].append(idx)
            info_base["chars_nativo"] += len(contenido)

    # Segunda pasada: OCR de las páginas seleccionadas
    if paginas_a_ocr:
        ocr_por_pagina = extract_text_ocr_paginas(pdf_path, paginas_a_ocr)
        for idx in paginas_a_ocr:
            texto_por_pagina[idx] = ocr_por_pagina.get(idx, "")
            info_base["paginas_ocr"].append(idx)
            info_base["chars_ocr"] += len(texto_por_pagina[idx])

    # Unir en orden de página
    texto_final = "\n\n".join(
        texto_por_pagina[idx] for idx in range(1, total_paginas + 1)
        if idx in texto_por_pagina and texto_por_pagina[idx]
    )

    if info_base["paginas_ocr"] and info_base["paginas_texto"]:
        metodo = "mixto"
    elif info_base["paginas_ocr"]:
        metodo = "ocr"
    else:
        metodo = "texto"

    info = {
        **info_base,
        "metodo_extraccion": metodo,
    }

    return texto_final, info
