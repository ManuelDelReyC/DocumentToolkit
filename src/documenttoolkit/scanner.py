from pathlib import Path
def scan_documents():
    documentos = []
    ruta = Path("data/input")
    if ruta.exists():
        print("La cartpeta existe")
    else:
        print("La carpeta no existe")
        print(ruta.is_dir())
    for elemento in ruta.iterdir():
        if  elemento.suffix.lower() == ".pdf":
            documentos.append(elemento)
    return documentos

