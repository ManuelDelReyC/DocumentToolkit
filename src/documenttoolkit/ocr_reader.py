from pdf2image import convert_from_path
import pytesseract


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