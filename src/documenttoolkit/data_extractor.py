def extract_iban(texto):
    iban = ""
    lines = texto.splitlines()
    for line in lines:
        if line.startswith("ES"):
            iban = line
            return iban
    return ""

def extract_titular(texto):
    titular = ""
    lines = texto.splitlines()
    for line in lines:
        if line.isupper() is True and line.count(" ") in (1, 2, 3, 4):
            print(line)
            titular = line
            return titular
        return ""

def extract_titular(texto):
    lines = texto.splitlines()

    for i, line in enumerate(lines):
        if "Titular de la tarjeta" in line:
            if i + 1 < len(lines):
                return lines[i + 1].strip()
    return ""

def extract_data(texto, tipo_documento):
    datos = {}

    datos["tipo"] = tipo_documento
    datos["num_caracteres"] = len(texto)
    datos["IBAN"] = extract_iban(texto)
    datos["Titular"] = extract_titular(texto)

    return datos