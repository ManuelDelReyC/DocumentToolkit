from pdf2image import convert_from_path
import pytesseract
from typing import Dict, Iterable


def extract_text_ocr(pdf_path):
    paginas = convert_from_path(pdf_path)   # Converts the pdf file into several images, one per page

    texto = ""

    for pagina in paginas:   # Loop over each page
        contenido = pytesseract.image_to_string(        # OCR page by page
            pagina,
            lang="spa"
        )

        texto += contenido      # Cumululate text of all pages into a single string

    return texto.strip()


def extract_text_ocr_paginas(pdf_path, paginas: Iterable[int]) -> Dict[int, str]:
    """
    OCR-iza solo las páginas indicadas (1-based) y devuelve un dict
    {numero_pagina: texto}. Agrupa rangos consecutivos para reducir
    llamadas a poppler.
    """
    paginas = sorted({int(p) for p in paginas})
    if not paginas:
        return {}

    resultados: Dict[int, str] = {}

    inicio_rango = paginas[0]
    fin_rango = paginas[0]

    for p in list(paginas[1:]) + [None]:
        if p is not None and p == fin_rango + 1:
            fin_rango = p
            continue

        imgs = convert_from_path(
            pdf_path,
            first_page=inicio_rango,
            last_page=fin_rango,
        )
        for offset, img in enumerate(imgs):
            num_pagina = inicio_rango + offset
            contenido = pytesseract.image_to_string(
                img,
                lang="spa"
            )
            resultados[num_pagina] = contenido.strip()

        if p is not None:
            inicio_rango = p
            fin_rango = p

    return resultados
