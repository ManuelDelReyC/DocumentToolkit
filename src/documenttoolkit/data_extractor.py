def extract_iban(texto):
    iban = ""
    lines = texto.splitlines()
    for line in lines:
        line = line.strip()
        line_norm = "".join(line.split())
        line_numb = line_norm[2:]
        if line.strip().startswith("ES") and line_numb.isdigit() and len(line_norm) == 24:
            iban = line.strip()
            return iban
    return ""

def validate_iban(iban):
    if not iban:
        return False
    iban_sin_espacios = "".join(iban.split()) # Normalizamos el IBAN eliminando espacios de la cadena
    iban_pais = iban_sin_espacios[:2] # Extraemos los 2 digitos con el codigo del pails 
    iban_numeros = iban_sin_espacios[2:]  # Extraemos la parte posterior al código de país 
    iban_numeros_1 = iban_numeros[2:] # Extraemos de la parte numerica la parte que corresponde a la cuenta
    iban_numeros_2 = iban_numeros[:2] # Extraemos la parte que corresponde a los 2 digitos de control
    iban_pais_num = ""
    for letra in iban_pais: # Bucle para convertir las letras en numeros
        iban_pais_num = iban_pais_num + str(ord(letra) -55)
    return int(iban_numeros_1 + str(iban_pais_num) + str(iban_numeros_2)) % 97 == 1 # Algoritmo de validacion

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

    iban = extract_iban(texto)
    
    datos["IBAN"] = iban
    datos["IBAN_Valido"] = validate_iban(iban)
    datos["Titular"] = extract_titular(texto)

    return datos