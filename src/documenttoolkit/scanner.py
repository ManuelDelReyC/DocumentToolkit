from pathlib import Path
from .config import INPUT_PDF_DIR


def scan_documents():
    documentos = []
    ruta = INPUT_PDF_DIR
    if ruta.exists():
        print("La carpeta existe")
    else:
        print("La carpeta no existe")
        print(ruta.is_dir())
        return documentos
    for elemento in ruta.iterdir():
        if elemento.suffix.lower() == ".pdf":
            documentos.append(elemento)
    return documentos

