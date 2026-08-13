def extract_iban(texto):
    iban = ""
    lines = texto.splitlines()
    for line in lines:
        if line.strip().startswith("ES"):
            iban = line.strip()
            return iban
    return ""

def extract_titular(texto):
    lines = texto.splitlines()

    for i, line in enumerate(lines):
        if "Titular de la tarjeta" in line:
            for siguiente_linea in lines[i + 1:]:
                siguiente_linea = siguiente_linea.strip()

                if siguiente_linea:
                    return siguiente_linea

    return ""

def extract_titular(texto):
    lines = texto.splitlines()

    for i, line in enumerate(lines):
        if "Titular de la tarjeta" in line:
            for siguiente_linea in lines[i + 1:]:
                if siguiente_linea.strip():
                    return siguiente_linea.strip()

    return ""

def extract_data(texto, tipo_documento):
    datos = {}

    datos["tipo"] = tipo_documento
    datos["num_caracteres"] = len(texto)
    datos["IBAN"] = extract_iban(texto)
    datos["Titular"] = extract_titular(texto)

    return datos