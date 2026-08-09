from pdf2image import convert_from_path
import pytesseract


def extract_text_ocr(pdf_path):
    paginas = convert_from_path(pdf_path)

    texto = ""

    for pagina in paginas:
        contenido = pytesseract.image_to_string(
            pagina,
            lang="spa"
        )

        texto += contenido

    return texto.strip()