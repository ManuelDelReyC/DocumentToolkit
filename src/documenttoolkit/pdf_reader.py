from pypdf import PdfReader
def extract_text(pdf_path):
    reader = PdfReader(pdf_path) 
    texto = ""
    for pagina in reader.pages:
        contenido = pagina.extract_text()

        if contenido:
            texto += contenido
 
    return texto.strip()