import re
from datetime import datetime

# ==========================================================
# Constantes y tablas
# ==========================================================

_MESES_ES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
    "ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6,
    "jul": 7, "ago": 8, "sep": 9, "oct": 10, "nov": 11, "dic": 12,
}

_NUMEROS_ES = {
    "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5,
    "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10, "once": 11,
    "doce": 12, "trece": 13, "catorce": 14, "quince": 15, "dieciseis": 16,
    "dieciséis": 16, "diecisiete": 17, "dieciocho": 18, "diecinueve": 19,
    "veinte": 20, "veintiuno": 21, "veintiún": 21, "veintidos": 22, "veintidós": 22,
    "veintitres": 23, "veintitrés": 23, "veinticuatro": 24, "veinticinco": 25,
    "veintiseis": 26, "veintiséis": 26, "veintisiete": 27, "veintiocho": 28,
    "veintinueve": 29, "treinta": 30, "treinta y uno": 31, "treinta y dos": 32,
    "treinta y tres": 33, "treinta y cuatro": 34, "treinta y cinco": 35,
}

_ANOS_LITERAL = {
    "dos mil": 2000,
    "dos mil uno": 2001, "dos mil dos": 2002, "dos mil tres": 2003, "dos mil cuatro": 2004,
    "dos mil cinco": 2005, "dos mil seis": 2006, "dos mil siete": 2007, "dos mil ocho": 2008,
    "dos mil nueve": 2009, "dos mil diez": 2010, "dos mil once": 2011, "dos mil doce": 2012,
    "dos mil trece": 2013, "dos mil catorce": 2014, "dos mil quince": 2015,
    "dos mil dieciséis": 2016, "dos mil diecisiete": 2017, "dos mil dieciocho": 2018,
    "dos mil diecinueve": 2019, "dos mil veinte": 2020, "dos mil veintiuno": 2021,
    "dos mil veintidos": 2022, "dos mil veintitres": 2023, "dos mil veinticuatro": 2024,
    "dos mil veinticinco": 2025, "dos mil veintiseis": 2026, "dos mil veintisiete": 2027,
    "dos mil veintiocho": 2028, "dos mil veintinueve": 2029, "dos mil treinta": 2030,
    "dos mil treinta y uno": 2031, "dos mil treinta y dos": 2032, "dos mil treinta y tres": 2033,
    "dos mil treinta y cuatro": 2034, "dos mil treinta y cinco": 2035,
}

_TIPOS_BANCARIOS = {
    "EXTRACTO_BANCARIO", "MOVIMIENTO_BANCARIO", "TRANSFERENCIA_BANCARIA",
    "HIPOTECA", "NOMINA", "FACTURA",
}

_TIPOS_JUDICIALES = {
    "AUTO", "SENTENCIA", "ESCRITO_JUDICIAL", "APUD_ACTA",
}

_DNI_LETRAS = "TRWAGMYFPDXBNJZSQVHLCKE"


# ==========================================================
# API pública histórica: IBAN y CCC
# ==========================================================

def validate_iban(iban):
    """Valida un IBAN con el algoritmo módulo 97."""
    if not iban:
        return False
    iban_sin_espacios = "".join(iban.split())
    if len(iban_sin_espacios) < 4:
        return False
    iban_pais = iban_sin_espacios[:2]
    iban_numeros = iban_sin_espacios[2:]
    iban_numeros_1 = iban_numeros[2:]
    iban_numeros_2 = iban_numeros[:2]
    iban_pais_num = "".join(str(ord(letra) - 55) for letra in iban_pais)
    try:
        return int(iban_numeros_1 + iban_pais_num + iban_numeros_2) % 97 == 1
    except ValueError:
        return False


def extract_iban(texto):
    """Extrae el primer IBAN válido o, si ninguno lo es, el primer candidato.

    Permite que el IBAN vaya acompañado de otros caracteres en la misma línea
    (p. ej. ``ES38...3937 (ING)``) y devuelve el IBAN tal cual aparece en el
    texto, conservando su formato original.
    """
    candidatos = _extraer_ibans(texto)
    if not candidatos:
        return ""
    for iban in candidatos:
        if validate_iban(iban):
            return iban
    return candidatos[0]


def _extraer_ibans(texto):
    """Devuelve todos los IBANs candidatos encontrados en el texto."""
    ibans = []
    for line in texto.splitlines():
        # Buscamos ES seguido de dígitos, permitiendo espacios en grupos de 4.
        for m in re.finditer(r'ES\s*(?:\d{2}\s*(?:\d{4}\s*){5}\d{0,4}|\d{22})', line, re.IGNORECASE):
            raw = m.group()
            norm = "".join(raw.split()).upper()
            if len(norm) == 24 and norm[2:].isdigit():
                # Preferimos el formato exacto que aparece en el texto, recortado.
                inicio = m.start()
                fin = m.end()
                # Si va pegado a letras (p. ej. "ABC ES12...") descartamos.
                if inicio > 0 and re.match(r"[A-Za-zÁ-Úá-úÑñ]", line[inicio - 1]):
                    continue
                if fin < len(line) and re.match(r"[A-Za-zÁ-Úá-úÑñ0-9]", line[fin]):
                    # Un dígito inmediatamente después podría ser parte de un número
                    # más largo; solo lo aceptamos si los 24 caracteres ya son válidos.
                    if not validate_iban(norm):
                        continue
                ibans.append(raw.strip())
    return ibans


def suma_ponderada_ccc(cadena):
    pesos = [1, 2, 4, 8, 5, 10, 9, 7, 3, 6]
    suma = sum(int(cadena[i]) * pesos[i] for i in range(len(pesos)))
    resto = suma % 11
    number = 11 - resto
    if number == 10:
        return 1
    if number == 11:
        return 0
    return number


def validate_ccc(ccc):
    if not ccc or len(ccc) != 20 or not ccc.isdigit():
        return False
    entidad = ccc[:4]
    oficina = ccc[4:8]
    control = ccc[8:10]
    cuenta = ccc[10:]
    primer_dc = "00" + entidad + oficina
    segundo_dc = cuenta
    digito_control = str(suma_ponderada_ccc(primer_dc)) + str(suma_ponderada_ccc(segundo_dc))
    return control == digito_control


def extract_ccc(texto, iban):
    """Extrae CCC preferentemente del IBAN español o de su entorno etiquetado."""
    # 1. CCC derivado de IBAN español válido.
    if iban:
        norm = "".join(iban.split()).upper()
        if norm.startswith("ES") and len(norm) == 24:
            derivado = norm[4:24]
            if validate_ccc(derivado):
                return derivado

    # 2. Buscar 20 dígitos solo cerca de etiquetas de cuenta.
    lineas = texto.splitlines()
    for i, line in enumerate(lineas):
        if re.search(r"\b(CCC|CUENTA CORRIENTE|NÚM\.? DE CUENTA|NUM\.? DE CUENTA|CUENTA ASOCIADA)\b", line, re.IGNORECASE):
            ventana = lineas[max(0, i - 2):min(len(lineas), i + 3)]
            for l in ventana:
                for m in re.finditer(r"\d{20}", l):
                    ccc = m.group()
                    if validate_ccc(ccc):
                        return ccc
    return ""


# ==========================================================
# Fechas
# ==========================================================

def _normalizar_fecha(dia, mes, anio):
    """Devuelve ISO YYYY-MM-DD o None si la fecha no es válida."""
    from datetime import date
    try:
        anio_int = int(anio)
        if anio_int < 100:
            anio_int += 2000 if anio_int < 50 else 1900
        d = date(anio_int, int(mes), int(dia))
        return d.isoformat()
    except (ValueError, TypeError):
        return None


def _parse_anio_literal(texto):
    """Convierte 'dos mil veinticinco' -> 2025."""
    t = " ".join(texto.lower().split())
    if t in _ANOS_LITERAL:
        return _ANOS_LITERAL[t]
    # Año en dígitos
    m = re.match(r"^(\d{4})$", t)
    if m:
        return int(m.group(1))
    return None


def _parse_dia_literal(texto):
    t = " ".join(texto.lower().split())
    if t in _NUMEROS_ES:
        return _NUMEROS_ES[t]
    m = re.match(r"^(\d{1,2})$", t)
    if m:
        return int(m.group(1))
    return None


def _extraer_fecha_texto(texto):
    """Busca fechas del tipo '4 de Febrero de dos mil veinticinco' o '24 de febrero 2026'."""
    # "4 de Febrero de dos mil veinticinco" (permitiendo salto de línea en el año)
    patron1 = re.compile(
        r"(\d{1,2}|" + "|".join(_NUMEROS_ES.keys()) + r")\s+de\s+([a-zA-ZáéíóúñÁÉÍÓÚÑ]+)\s+(?:de\s+)?(dos mil(?:\s+[a-zA-ZáéíóúñÁÉÍÓÚÑ]+)?|\d{4})",
        re.IGNORECASE,
    )
    texto_para_fecha = texto.replace("\n", " ")
    for m in patron1.finditer(texto_para_fecha):
        dia = _parse_dia_literal(m.group(1))
        mes = _MESES_ES.get(m.group(2).lower())
        anio = _parse_anio_literal(m.group(3))
        if dia and mes and anio:
            return _normalizar_fecha(dia, mes, anio), m.group(0)
    return None, None


def _extraer_fecha_numerica(texto):
    """Busca fechas numéricas separadas por / - . y posiblemente pegadas a texto."""
    # 03-02-2024, 18/05/2026, 10.02.2025, posiblemente pegadas: 03-02-2024TRIODOS
    patron = re.compile(r"\b(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})\b")
    for m in patron.finditer(texto):
        dia, mes, anio = m.group(1), m.group(2), m.group(3)
        # Evitar cosas como 02/24 de recibo
        if len(anio) == 2 and int(anio) < 50:
            anio = "20" + anio
        elif len(anio) == 2:
            anio = "19" + anio
        fecha = _normalizar_fecha(dia, mes, anio)
        if fecha:
            return fecha, m.group(0)
    return None, None


def extraer_fechas(texto):
    """Devuelve una lista de {valor, texto}. No asigna etiquetas."""
    fechas = []
    visto = set()
    for f, raw in [_extraer_fecha_texto(texto), _extraer_fecha_numerica(texto)]:
        if f and f not in visto:
            fechas.append({"valor": f, "texto": raw})
            visto.add(f)
    return fechas


def _fecha_en_ventana(lineas, idx, etiquetas, direccion="adelante"):
    """Busca una fecha en las líneas adyacentes a una etiqueta."""
    rango = range(idx + 1, min(len(lineas), idx + 4)) if direccion == "adelante" else range(max(0, idx - 3), idx)
    for j in rango:
        linea = lineas[j]
        # A veces la fecha va en la misma línea que la etiqueta; si no, prueba la línea completa.
        for fn in (_extraer_fecha_texto, _extraer_fecha_numerica):
            f, raw = fn(linea)
            if f:
                return f, raw
    return None, None


def _rango_fechas_tabla(lineas):
    """Para extractos: toma la primera y última fecha al inicio de línea de la tabla."""
    fechas = []
    for linea in lineas:
        # Fecha al inicio de línea tipo 01-01-2024, ignorando sangría
        m = re.match(r"\s*(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})(?:\s|$)", linea)
        if m:
            f = _normalizar_fecha(m.group(1), m.group(2), m.group(3))
            if f:
                fechas.append(f)
    if fechas:
        return min(fechas), max(fechas)
    return None, None


def _extraer_periodo(texto):
    """Busca 'Periodo X hasta Y' o 'X / Y' en contexto de periodo."""
    patron = re.compile(
        r"Periodo\s+(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4})\s+(?:hasta|a)\s+(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4})",
        re.IGNORECASE,
    )
    for m in patron.finditer(texto):
        f1, _ = _extraer_fecha_numerica(m.group(1))
        f2, _ = _extraer_fecha_numerica(m.group(2))
        if f1 and f2:
            return f1, f2
    # Periodo con barra: "30-09-2024 / 31-12-2024"
    patron2 = re.compile(
        r"(?:periodo|período|devengo).*?(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4})\s*/\s*(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4})",
        re.IGNORECASE,
    )
    for m in patron2.finditer(texto):
        f1, _ = _extraer_fecha_numerica(m.group(1))
        f2, _ = _extraer_fecha_numerica(m.group(2))
        if f1 and f2:
            return f1, f2
    return None, None


# ==========================================================
# Personas / nombres / DNI
# ==========================================================

def _es_nombre(linea):
    """Heurística para detectar si una línea es un nombre de persona."""
    t = linea.strip()
    if not t:
        return False
    # No debe contener dígitos ni signos raros (guiones internos sí).
    if re.search(r"[0-9@#%&*=+<>{}\[\]|\\]", t):
        return False
    # Tokens
    tokens = t.split()
    if not (2 <= len(tokens) <= 7):
        return False
    # Palabras prohibidas (bancarias, judiciales, empresariales)
    prohibidas = {
        "TRIODOS", "BANK", "ING", "BANK", "SUCURSAL", "OFICINA", "TELÉFONO", "TELEFONO",
        "FECHA", "EXTRACTO", "OPERACIONES", "SALDO", "ANTERIOR", "CONCEPTO", "IMPORTE",
        "PÁGINA", "PAGINA", "EUROS", "EUR", "BIC", "IBAN", "CCC", "DOMICILIACIÓN",
        "TRANSFERENCIA", "TRANSF", "ORDENANTE", "BENEFICIARIO", "ADEUDO", "RECIBIDO",
        "TITULAR", "TITULARES", "CUENTA", "TARJETA", "PRESTAMO", "PRÉSTAMO", "LIQUIDACIÓN",
        "COMISIÓN", "ORG.", "DIPUTACION", "AUT.", "RECAUDACION", "GESTION", "TRIBUTARIA",
        "PAGO", "NÚM", "NUM", "REFERENCIA", "MOVIMIENTO", "DETALLE", "DOM.", "SOC.",
        "REG.MER.", "MADRID", "CÁCERES", "CACERES", "BARCELONA", "SEVILLA", "VALENCIA",
        "JUZGADO", "TRIBUNAL", "AUDIENCIA", "SALA", "DILIGENCIAS", "PREVIAS", "PROC.",
        "ABREVIADO", "EXPEDIENTE", "AUTO", "SENTENCIA", "DEMANDA", "QUERELLA",
        "MINISTERIO", "FISCAL", "PROCURADOR", "PROCURADORA", "ABOGADO", "ABOGADA",
        "LETRADO", "LETRADA", "MAGISTRADO", "JUEZ", "SECRETARIO", "ACTA",
    }
    up = t.upper()
    for p in prohibidas:
        if p in up:
            return False
    # Debe ser mayoritariamente texto alfabético (permitir ',', '.', '/', etc. mínimos)
    letras = sum(1 for c in t if c.isalpha() or c.isspace() or c in "-'")
    if letras / len(t) < 0.8:
        return False
    return True


def _normalizar_nombre(nombre):
    """Limpia espacios, quita conjunciones finales y pasa a mayúsculas."""
    nombre = nombre.strip()
    # Quitar conjunciones o signos sueltos al final
    nombre = re.sub(r"\s+(Y|E|O|U|/|-)\s*$", "", nombre, flags=re.IGNORECASE)
    return " ".join(nombre.split()).upper()


def _nombre_invertido(nombre):
    """Convierte 'APELLIDO1 APELLIDO2, NOMBRE' -> 'NOMBRE APELLIDO1 APELLIDO2'."""
    if "," in nombre:
        partes = [p.strip() for p in nombre.split(",", 1)]
        if len(partes) == 2 and partes[0] and partes[1]:
            return f"{partes[1]} {partes[0]}"
    return nombre


def _nombres_iguales(n1, n2):
    """Compara dos nombres por conjunto de tokens, permitiendo subconjuntos."""
    def tokens(n):
        return set(re.findall(r"[A-ZÁÉÍÓÚÑ]+", _normalizar_nombre(_nombre_invertido(n))))
    t1, t2 = tokens(n1), tokens(n2)
    inter = t1 & t2
    return len(inter) >= 2 and (t1.issubset(t2) or t2.issubset(t1))


def _validar_dni(numero):
    """Valida letra de DNI/NIE. Devuelve (dni_normalizado, valido)."""
    if not numero:
        return None, False
    numero = "".join(numero.split()).upper()
    # NIE: X/Y/Z + 7 dígitos + letra
    m_nie = re.match(r"^[XYZ](\d{7,8})([A-Z])$", numero)
    if m_nie:
        prefijo = {"X": "0", "Y": "1", "Z": "2"}[m_nie.group(1)[0]]
        n = int(prefijo + m_nie.group(1))
        letra = m_nie.group(2)
        return numero, letra == _DNI_LETRAS[n % 23]
    # DNI
    m = re.match(r"^(\d{8})([A-Z])$", numero)
    if m:
        n = int(m.group(1))
        letra = m.group(2)
        return numero, letra == _DNI_LETRAS[n % 23]
    return numero, False


def _extraer_dnis(texto):
    """Extrae DNI/NIE y valida la letra."""
    dnis = []
    vistos = set()
    for m in re.finditer(r"\b(\d{8}[A-Z]|[XYZ]\d{7,8}[A-Z])\b", texto.upper()):
        raw = m.group(1)
        normalizado, valido = _validar_dni(raw)
        if normalizado and normalizado not in vistos:
            dnis.append({"valor": normalizado, "valido": valido})
            vistos.add(normalizado)
    return dnis


def _extraer_nombres_cerca(lineas, etiquetas, antes=6, despues=2, permitir_invertido=True):
    """Busca nombres alrededor de etiquetas como 'Titulares de la Cuenta'."""
    nombres = []
    for i, line in enumerate(lineas):
        if any(et.lower() in line.lower() for et in etiquetas):
            ventana = lineas[max(0, i - antes):min(len(lineas), i + despues + 1)]
            for l in ventana:
                # Si el nombre está pegado a dígitos, intentamos separarlo.
                for candidato in re.findall(r"[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑa-záéíóúñ\-']*(?:\s+[A-ZÁÉÍÓÚÑa-záéíóúñ\-']+){1,6}", l):
                    # Normalizar a mayúsculas para evitar mezclas
                    cand = _normalizar_nombre(candidato)
                    if permitir_invertido and "," in cand:
                        cand = _nombre_invertido(cand)
                    if _es_nombre(cand):
                        # descartar si coincide con algún nombre ya añadido
                        if not any(_nombres_iguales(cand, existente) for existente in nombres):
                            nombres.append(cand)
    return nombres


def _nombre_despues_de_etiqueta(lineas, etiquetas, max_saltar=3):
    """Caso simple: etiqueta y nombre en la(s) siguiente(s) línea(s)."""
    for i, line in enumerate(lineas):
        if any(et.lower() in line.lower() for et in etiquetas):
            saltados = 0
            for j in range(i + 1, min(len(lineas), i + 1 + max_saltar)):
                candidato = lineas[j].strip()
                if not candidato:
                    saltados += 1
                    continue
                # Permitir nombre en la línea pegado a otras cosas
                for c in re.findall(r"[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑa-záéíóúñ\-']*(?:\s+[A-ZÁÉÍÓÚÑa-záéíóúñ\-']+){1,6}", candidato):
                    c = _normalizar_nombre(c)
                    if _es_nombre(c):
                        return c
                if saltados == 0:
                    break
    return ""


def _es_linea_nombre_limpia(line):
    """Comprueba si una línea entera es un nombre de persona válido."""
    if not re.match(r"^[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑa-záéíóúñ\s,\-'']+$", line):
        return False
    if len(line) > 80:
        return False
    palabras_excluidas = {
        "INFORMACIÓN", "ADICIONAL", "REFERENCIA", "PÁGINA", "PAGINA", "FECHA",
        "TRANSFERENCIA", "SEPA", "VÍA", "POBLADOS", "CIF", "TOMO", "FOLIO",
        "SECCIÓN", "HOJA", "REGISTRO", "MERANTIL", "MADRID", "BANCO", "BANK",
        "SUCURSAL", "ING", "INGES", "WWW", "HTTP", "HTTPS", "NÚM", "NUM",
        "BIC", "IBAN", "CCC", "CONCEPTO", "GASTOS", "COMISIÓN", "COMISION",
        "OPCIÓN", "OPCION", "COMPARTIDOS", "DOMICILIACIÓN", "EMISORA",
        "ENTIDAD", "ORDENANTE", "BENEFICIARIO", "TITULAR", "ADEDO", "RECIBO",
        "ADEUDO", "RECIBIDA", "PAGO", "IMPORTE", "EUROS", "EUR", "ID",
        "EMISOR", "RECAUDACION", "GESTION", "TRIBUTARIA", "DIPUTACION",
        "AUT", "ORG", "NOMBRE", "REPRESENTACIÓN", "DEMANDA", "QUERELLA",
    }
    tokens = line.split()
    if len(tokens) < 3 or len(tokens) > 6:
        return False
    tokens_limpios = [tok for tok in tokens if tok.upper() not in {"DE", "DEL", "LA", "LAS", "LOS", "Y", "E"}]
    if not tokens_limpios or any(len(tok) < 2 for tok in tokens_limpios):
        return False
    if any(tok.upper() in palabras_excluidas for tok in tokens):
        return False
    return _es_nombre(line)


def _harvest_nombres_bancarios(texto):
    """Recolección conservadora de nombres en documentos bancarios cortos.

    Se usa como último recurso cuando no hay anclas claras. Es muy restrictiva
    para no levantar falsos positivos en transferencias ING, donde el volcado de
    texto mezcla etiquetas, direcciones y datos del banco.
    """
    nombres = []
    for line in texto.splitlines():
        if not _es_linea_nombre_limpia(line):
            continue
        cand = _normalizar_nombre(line)
        if "," in cand:
            cand = _nombre_invertido(cand)
        if not any(_nombres_iguales(cand, existente) for existente in nombres):
            nombres.append(cand)
    return nombres


# ==========================================================
# Extractor bancario
# ==========================================================

def _extraer_bancario(texto, tipo_documento):
    datos = {}

    ibans = _extraer_ibans(texto)
    iban_principal = ""
    iban_valido = False
    for iban in ibans:
        if validate_iban(iban):
            iban_principal = iban
            iban_valido = True
            break
    if not iban_principal and ibans:
        iban_principal = ibans[0]

    datos["IBAN"] = iban_principal
    datos["IBAN_Valido"] = iban_valido or validate_iban(iban_principal)
    datos["IBANs"] = ibans

    ccc = extract_ccc(texto, iban_principal)
    datos["CCC"] = ccc
    datos["CCC_Valido"] = validate_ccc(ccc) if ccc else False
    # Alias histórico
    datos["CCC Valido"] = datos["CCC_Valido"]

    # Titulares
    lineas = texto.splitlines()
    titulares = []

    # 1. Etiquetas de tarjeta / domiciliación
    tarjeta = _nombre_despues_de_etiqueta(lineas, ["Titular de la tarjeta", "Titular de la domiciliación"])
    if tarjeta:
        titulares.append(tarjeta)

    # 2. Titulares de cuenta / préstamo
    if not titulares:
        titulares = _extraer_nombres_cerca(
            lineas,
            ["Titulares de la Cuenta", "Titulares del Préstamo", "Titulares del Prestamo"],
            antes=8, despues=1,
        )

    # 3. IBAN 1er Titular (ING transferencias) - ventana pequeña; "Compartidos"
    # en ING se refiere a gastos, no a titulares.
    if not titulares:
        titulares = _extraer_nombres_cerca(
            lineas,
            ["IBAN 1er Titular", "1er Titular"],
            antes=2, despues=3,
        )

    # 4. Fallback conservador solo para documentos cortos
    if not titulares and len(texto) < 2500:
        titulares = _harvest_nombres_bancarios(texto)

    datos["Titulares"] = titulares
    datos["Titular"] = titulares[0] if titulares else ""

    # Fechas
    datos["fecha_documento"] = None
    datos["fecha_operacion"] = None
    datos["fecha_valor"] = None
    datos["fecha_desde"] = None
    datos["fecha_hasta"] = None
    fechas = []

    # Fechas etiquetadas
    for i, line in enumerate(lineas):
        up = line.upper()
        if re.search(r"FECHA\s*(?:DE\s+)?OPERACI[ÓO]N", up):
            f, raw = _fecha_en_ventana(lineas, i, [], direccion="adelante")
            if f:
                datos["fecha_operacion"] = f
                fechas.append({"valor": f, "etiqueta": "fecha_operacion", "texto": raw})
        if re.search(r"FECHA\s*(?:DE\s+)?VALOR", up):
            f, raw = _fecha_en_ventana(lineas, i, [], direccion="adelante")
            if f:
                datos["fecha_valor"] = f
                fechas.append({"valor": f, "etiqueta": "fecha_valor", "texto": raw})
        if re.search(r"FECHA\s*(?:DE\s+)?ACEPTACI[ÓO]N", up):
            f, raw = _fecha_en_ventana(lineas, i, [], direccion="adelante")
            if f:
                fechas.append({"valor": f, "etiqueta": "fecha_aceptacion", "texto": raw})

    # Fecha de documento: cabecera bancaria (FECHA pegada a banco)
    for line in lineas[:15]:
        if re.search(r"TRIODOS|ING\s+BANK|CAIXA|SANTANDER|BBVA", line, re.IGNORECASE):
            m = re.search(r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})", line)
            if m:
                f = _normalizar_fecha(m.group(1), m.group(2), m.group(3))
                if f and not datos["fecha_documento"]:
                    datos["fecha_documento"] = f
                    fechas.append({"valor": f, "etiqueta": "fecha_documento", "texto": m.group(0)})

    # Extracto: rango desde la tabla
    if tipo_documento == "EXTRACTO_BANCARIO":
        desde, hasta = _rango_fechas_tabla(lineas)
        if desde:
            datos["fecha_desde"] = desde
        if hasta:
            datos["fecha_hasta"] = hasta

    # Hipoteca / liquidación: periodo explícito
    if tipo_documento in ("HIPOTECA", "MOVIMIENTO_BANCARIO", "EXTRACTO_BANCARIO"):
        desde, hasta = _extraer_periodo(texto)
        if desde and (not datos["fecha_desde"]):
            datos["fecha_desde"] = desde
        if hasta and (not datos["fecha_hasta"]):
            datos["fecha_hasta"] = hasta

    # Fechas sin etiqueta (respaldo)
    for fd in extraer_fechas(texto):
        if not any(f.get("valor") == fd["valor"] for f in fechas):
            fechas.append({"valor": fd["valor"], "etiqueta": None, "texto": fd["texto"]})

    datos["fechas"] = fechas
    datos["personas"] = _construir_personas(datos, texto)
    return datos


# ==========================================================
# Extractor judicial
# ==========================================================

def _extraer_organo(lineas):
    """Extrae órgano judicial, número y plaza de la cabecera."""
    organo = ""
    numero = ""
    plaza = ""
    sala = ""

    for i, line in enumerate(lineas[:25]):
        up = line.upper()
        # Sala
        m_sala = re.search(r"\bSALA\s*[Nº°\.]*\s*(\d+)", up)
        if m_sala:
            sala = m_sala.group(1)

        # Escrito judicial: "AL JUZGADO DE 1ª INSTANCIA ... DE CÁCERES"
        m = re.search(r"^\s*AL\s+(JUZGADO|TRIBUNAL)\s+(?:DE\s+)?(.+)$", line, re.IGNORECASE)
        if m and not organo:
            organo_raw = m.group(2).strip()
            # Si contiene DECANO, la plaza está en la siguiente línea no vacía
            if re.search(r"\bDECANO\b", organo_raw, re.IGNORECASE):
                organo = f"{m.group(1)} DE {organo_raw}"
                for j in range(i + 1, min(len(lineas), i + 4)):
                    sig = lineas[j].strip()
                    if sig:
                        plaza = re.sub(r"^DE\s+", "", sig, flags=re.IGNORECASE).strip()
                        break
                continue
            # La plaza es lo que sigue al último "DE " si es un topónimo corto
            partes = [p.strip() for p in re.split(r"\bDE\b", organo_raw, flags=re.IGNORECASE) if p.strip()]
            if len(partes) >= 2:
                posible_plaza = partes[-1]
                # Limpiar rótulos como "QUE POR TURNO CORRESPONDA"
                posible_plaza = re.sub(r"\s+QUE\s+.*", "", posible_plaza, flags=re.IGNORECASE).strip()
                plaza_tokens = posible_plaza.split()
                if 1 <= len(plaza_tokens) <= 4:
                    plaza = posible_plaza
                organo = f"{m.group(1)} DE {partes[0]}"
            else:
                organo = f"{m.group(1)} DE {organo_raw}"
            # Extraer número de órgano
            m_num = re.search(r"N\.?\s*(\d+)", organo_raw, re.IGNORECASE)
            if m_num:
                numero = m_num.group(1)
            continue

        # Formato LexNET: "JDO.1A.INST.E INSTRUCCION N.3"
        m2 = re.search(r"\b(JDO\.\S+(?:\s+[A-Z\.]+)*)\s+(N\.?\s*\d+)\b", up)
        if m2 and not organo:
            organo = f"{m2.group(1).strip()} {m2.group(2).strip()}"
            numero = "".join(filter(str.isdigit, m2.group(2)))
            if i + 1 < len(lineas):
                plaza = lineas[i + 1].strip()
            continue

        # Auto no-LexNET con "JUZGADO DE ... N.º X DE {Ciudad}"
        m3 = re.search(r"\b(JUZGADO|TRIBUNAL|AUDIENCIA)\s+DE\s+([^,\n]+?)(?:\s+N\.?\s*(\d+))?(?:\s+DE\s+([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑa-záéíóúñ\s]+?))?\s*$", line, re.IGNORECASE)
        if m3 and not organo:
            organo = f"{m3.group(1)} DE {m3.group(2).strip()}"
            if m3.group(3):
                numero = m3.group(3)
            if m3.group(4):
                plaza = m3.group(4).strip()
            continue

    return {
        "organo": organo,
        "numero_organo": numero,
        "plaza": plaza,
        "sala": sala,
        "tribunal": _expandir_organo(organo),
    }


def _expandir_organo(organo):
    """Expande abreviaturas LexNET a un nombre legible (best-effort).

    Si no reconoce el patrón, devuelve el texto original para no perder información.
    """
    if not organo:
        return organo
    up = organo.upper()

    # Solo intentamos expandir formatos LexNET conocidos
    if not up.startswith("JDO.") and not up.startswith("TRIB.") and not up.startswith("AUD."):
        return organo

    # Normalizamos puntos y partimos en tokens, pero respetamos "N.3"
    tmp = organo.replace(".", " ")
    raw_tokens = tmp.split()
    tokens = []
    i = 0
    while i < len(raw_tokens):
        if raw_tokens[i].upper() == "N" and i + 1 < len(raw_tokens) and raw_tokens[i + 1].isdigit():
            tokens.append(f"N.{raw_tokens[i + 1]}")
            i += 2
        else:
            tokens.append(raw_tokens[i])
            i += 1

    resultado = []
    for tok in tokens:
        up_tok = tok.upper()
        if up_tok == "JDO":
            resultado.append("Juzgado")
        elif up_tok == "TRIB":
            resultado.append("Tribunal")
        elif up_tok == "AUD":
            resultado.append("Audiencia")
        elif up_tok in ("1A", "1ª"):
            resultado.append("1ª")
        elif up_tok in ("2A", "2ª"):
            resultado.append("2ª")
        elif up_tok == "INST":
            resultado.append("Instancia")
        elif up_tok == "E":
            resultado.append("e")
        elif up_tok == "INSTRUCCION":
            resultado.append("Instrucción")
        elif up_tok == "CIVIL":
            resultado.append("Civil")
        elif up_tok == "PENAL":
            resultado.append("Penal")
        elif up_tok == "SOCIAL":
            resultado.append("Social")
        elif up_tok == "SALA":
            resultado.append("Sala")
        elif up_tok == "DE":
            resultado.append("de")
        elif re.match(r"^N\.\d+$", up_tok):
            resultado.append(tok)
        else:
            # Palabra no reconocida: mantenemos el original y abortamos la expansión
            return organo

    # Reconstruimos conectores gramaticales básicos
    legible = " ".join(resultado)
    # "Juzgado 1ª ..." -> "Juzgado de 1ª ..."
    legible = re.sub(r"\bJuzgado\s+(\d+[ªA])", r"Juzgado de \1", legible)
    legible = re.sub(r"\bTribunal\s+(\d+[ªA])", r"Tribunal de \1", legible)
    legible = re.sub(r"\bAudiencia\s+(\d+[ªA])", r"Audiencia de \1", legible)
    return legible


def _extraer_numero_resolucion(texto):
    # Solo al inicio de línea y en mayúsculas, para no confundir con citas del TS.
    for m in re.finditer(r"^(AUTO|SENTENCIA)\s*[:.]?\s*(\d{3,7}\s*/\s*\d{4})\b", texto, re.MULTILINE):
        return m.group(2).replace(" ", "")
    return ""


def _extraer_nig(texto):
    for m in re.finditer(r"\bN\.?I\.?G\.?\s*[:.]?\s*([\d\s]+)", texto, re.IGNORECASE):
        nig = "".join(m.group(1).split())
        if len(nig) >= 10:
            return nig
    return ""


def _normalizar_numero_procedimiento(numero):
    """Quita ceros a la izquierda del numerador: 0000702/2024 -> 702/2024."""
    numero = numero.replace(" ", "")
    partes = numero.split("/")
    if len(partes) == 2 and partes[0].isdigit() and partes[1].isdigit():
        anio = int(partes[1])
        if 1990 <= anio <= 2035:
            return f"{int(partes[0])}/{partes[1]}"
    return None


def _extraer_procedimientos(texto):
    procs = []
    vistos = set()
    # "Procedimiento origen: ... 0000702 /2024"
    for m in re.finditer(r"Procedimiento\s+origen.*?([A-ZÁÉÍÓÚÑ\s]+)\s+(\d{1,7}\s*/\s*\d{4})", texto, re.IGNORECASE):
        num = _normalizar_numero_procedimiento(m.group(2))
        if num and num not in vistos:
            procs.append({"tipo": m.group(1).strip(), "numero": num, "pos": m.start()})
            vistos.add(num)
    # Códigos tipo 0000702 /2024, 82/2025, pero solo cerca de contexto procesal
    contextos = [r"n\.?\s*º", "número", "expediente", "procedimiento", "auto", "sentencia", "pieza", "diligencia", "juicio"]
    for m in re.finditer(r"\b(\d{1,7})\s*/\s*(\d{4})\b", texto):
        num = _normalizar_numero_procedimiento(f"{m.group(1)}/{m.group(2)}")
        if not num or num in vistos:
            continue
        # Revisar contexto cercano (150 chars antes y después)
        inicio = max(0, m.start() - 150)
        fin = min(len(texto), m.end() + 150)
        contexto = texto[inicio:fin].upper()
        # Descartar si es claramente un artículo de ley o una cita de sentencia
        if re.search(r"\bART[ÍI]CULO|ART\b", contexto, re.IGNORECASE):
            continue
        if re.search(r"\bSSTS\b|\bSTS\s|\bSENTENCIAS?\b|\bRECURSO\s*[:\-]|\bJURISPRUDENCIA\b", contexto, re.IGNORECASE):
            continue
        if any(re.search(c, contexto, re.IGNORECASE) for c in contextos):
            procs.append({"tipo": None, "numero": num, "pos": m.start()})
            vistos.add(num)
    # Ordenar por posición y limitar a los primeros 10 para no saturar
    procs.sort(key=lambda x: x["pos"])
    return [{"tipo": p["tipo"], "numero": p["numero"]} for p in procs[:10]]


def _extraer_partes_judiciales(texto):
    """Extrae demandantes/demandados/denunciantes/denunciados."""
    partes = {
        "demandantes": [],
        "demandados": [],
        "denunciantes": [],
        "denunciados": [],
        "ministerio_fiscal": False,
    }
    lineas = texto.splitlines()

    # Roles etiquetados
    for line in lineas:
        up = line.upper()
        for rol_es, clave in [
            ("DEMANDANTE", "demandantes"),
            ("DEMANDADO", "demandados"),
            ("DENUNCIANTE", "denunciantes"),
            ("DENUNCIADO", "denunciados"),
        ]:
            patron = re.compile(rf"\b{rol_es}[S]?\b", re.IGNORECASE)
            if patron.search(line):
                # Buscar D./Do/Doña/Dña./DON/DOÑA Nombre en la misma línea
                prefijo = r"(?:D[./]\s*|D\.ª\s*|D/ña\.?\s*|Doña\s+|Do\s+|Dña\.?\s+|DON\s+|DOÑA\s+)"
                for m in re.finditer(r"\b" + prefijo + r"([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑa-záéíóúñ\-']*(?:\s+[A-ZÁÉÍÓÚÑa-záéíóúñ\-']+){1,5})", line, re.IGNORECASE):
                    nombre = _normalizar_nombre(m.group(1))
                    if _es_nombre(nombre):
                        if not any(_nombres_iguales(nombre, x) for x in partes[clave]):
                            partes[clave].append(nombre)
                # Atestado: nombre en mayúsculas ANTES de la etiqueta, pegado a fecha/hora
                m_atestado = re.search(
                    r"([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\-'']*(?:\s+[A-ZÁÉÍÓÚÑ\-'']+){2,5})\s+\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}.*?\b" + rol_es + r"[S]?\b",
                    line, re.IGNORECASE,
                )
                if m_atestado:
                    nombre = _normalizar_nombre(m_atestado.group(1))
                    if _es_nombre(nombre):
                        if not any(_nombres_iguales(nombre, x) for x in partes[clave]):
                            partes[clave].append(nombre)
        if "MINISTERIO FISCAL" in up:
            partes["ministerio_fiscal"] = True

    def _extraer_nombres_segmento(segmento, destino):
        """Extrae todos los nombres con prefijo D./Doña de un segmento de texto."""
        for m in re.finditer(r"\b" + prefijo + r"([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑa-záéíóúñ\-']*(?:\s+[A-ZÁÉÍÓÚÑa-záéíóúñ\-']+){1,5})", segmento, re.IGNORECASE):
            nombre = _normalizar_nombre(m.group(1))
            if _es_nombre(nombre):
                if not any(_nombres_iguales(nombre, x) for x in partes[destino]):
                    partes[destino].append(nombre)

    # Querella: "contra D. NOMBRE, ... y D. NOMBRE"
    prefijo = r"(?:D[./]\s*|D\.ª\s*|D/ña\.?\s*|Doña\s+|Do\s+|Dña\.?\s+|DON\s+|DOÑA\s+)"
    if "querella" in texto.lower():
        for m in re.finditer(r"\bcontra\b(.{0,400})", texto, re.IGNORECASE | re.DOTALL):
            _extraer_nombres_segmento(m.group(1), "denunciados")
    else:
        for m in re.finditer(r"\b(?:frente\s+a|contra)\s+(?:su\s+marido,\s*)?" + prefijo + r"([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑa-záéíóúñ\-']*(?:\s+[A-ZÁÉÍÓÚÑa-záéíóúñ\-']+){1,5})", texto, re.IGNORECASE):
            nombre = _normalizar_nombre(m.group(1))
            if _es_nombre(nombre):
                if not any(_nombres_iguales(nombre, x) for x in partes["demandados"]):
                    partes["demandados"].append(nombre)

    # Compareciente: "en (nombre y) representación, de D./Do/Doña NOMBRE"
    # Solo en las primeras líneas del escrito para no confundir con cuerpo.
    cabecera = "\n".join(texto.splitlines()[:20])
    compareciente = None
    for m in re.finditer(r"en\s+(?:nombre\s+y\s+)?representaci[óo]n,?\s+de\s+" + prefijo + r"([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑa-záéíóúñ\-']*(?:\s+[A-ZÁÉÍÓÚÑa-záéíóúñ\-']+){1,5})", cabecera, re.IGNORECASE):
        nombre = _normalizar_nombre(m.group(1))
        if _es_nombre(nombre):
            compareciente = nombre
            break

    es_querella = "querella" in texto.lower()
    if es_querella:
        # En una querella el compareciente es el querellante/denunciante;
        # los denunciados salen del bloque 'contra'.
        partes["demandantes"] = []
        partes["demandados"] = []
        partes["denunciantes"] = [compareciente] if compareciente else []
        # Filtrar denunciados: descartar si coincide con el compareciente
        partes["denunciados"] = [
            d for d in partes["denunciados"]
            if not (compareciente and _nombres_iguales(d, compareciente))
        ]
    else:
        if compareciente:
            if not any(_nombres_iguales(compareciente, x) for x in partes["demandantes"]):
                partes["demandantes"].append(compareciente)

    return partes


def _extraer_juez(texto):
    """Busca el nombre del juez/a cerca de la firma."""
    lineas = texto.splitlines()
    for i, line in enumerate(lineas):
        if re.search(r"MAGISTRADO-JUEZ|EL/LA MAGISTRADO", line, re.IGNORECASE):
            for j in range(i + 1, min(len(lineas), i + 6)):
                candidato = lineas[j].strip()
                if re.search(r"LETRADO|SECRETARIO|ADMINISTRACI[ÓO]N", candidato, re.IGNORECASE):
                    continue
                if candidato and len(candidato.split()) <= 6:
                    for m in re.finditer(r"[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\-']*(?:\s+[A-ZÁÉÍÓÚÑ\-']+){1,5}", candidato):
                        nombre = _normalizar_nombre(m.group())
                        if _es_nombre(nombre):
                            return nombre
    return ""


def _extraer_fecha_documento_judicial(texto):
    """Fecha del auto o del cierre del escrito, no fechas de hechos."""
    # Auto: "En Navalmoral de la Mata a 4 de Febrero de dos mil veinticinco."
    for m in re.finditer(r"En\s+([A-ZÁÉÍÓÚÑa-záéíóúñ][A-Za-zÁÉÍÓÚÑáéíóúñ\s]+?)\s+a\s+(\d{1,2}|" + "|".join(_NUMEROS_ES.keys()) + r")\s+de\s+([a-zA-ZáéíóúñÁÉÍÓÚÑ]+)\s+(?:de\s+)?(dos mil(?:\s+[a-zA-ZáéíóúñÁÉÍÓÚÑ]+)?|\d{4})", texto, re.IGNORECASE):
        dia = _parse_dia_literal(m.group(2))
        mes = _MESES_ES.get(m.group(3).lower())
        anio = _parse_anio_literal(m.group(4))
        if dia and mes and anio:
            return _normalizar_fecha(dia, mes, anio)

    # Escrito: cierre "en ..., a 6 de Noviembre de 2024" o "En ..., a 24 de febrero 2026"
    lineas = texto.splitlines()
    for line in reversed(lineas[-30:]):
        f, _ = _extraer_fecha_texto(line)
        if f:
            return f

    # Atestado: "DE FECHA: 10-02-2025"
    for m in re.finditer(r"DE\s+FECHA\s*[:.]\s*(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4})", texto, re.IGNORECASE):
        f, _ = _extraer_fecha_numerica(m.group(1))
        if f:
            return f

    return None


def _extraer_judicial(texto, tipo_documento):
    datos = {}
    lineas = texto.splitlines()

    organo_info = _extraer_organo(lineas)
    datos["organo"] = organo_info["organo"]
    datos["numero_organo"] = organo_info["numero_organo"]
    datos["plaza"] = organo_info["plaza"]
    datos["sala"] = organo_info["sala"]
    datos["tribunal"] = organo_info.get("tribunal", organo_info["organo"])

    datos["nig"] = _extraer_nig(texto)
    datos["numero_resolucion"] = _extraer_numero_resolucion(texto)

    # En escritos de parte, solo extraemos partes/procedimientos si hay cabecera
    # de órgano o es un atestado; así evitamos falsos en informes/transcripciones.
    cabecera_judicial = bool(datos["organo"]) or bool(
        re.search(r"\bAL\s+(JUZGADO|TRIBUNAL|AUDIENCIA)\b", "\n".join(lineas[:10]), re.IGNORECASE)
    )
    es_atestado = bool(re.search(r"\bATESTADO\s+N[ÚU]M", "\n".join(lineas[:60]), re.IGNORECASE))
    es_documento_judicial_fuerte = tipo_documento in ("AUTO", "SENTENCIA") or cabecera_judicial or es_atestado

    if es_documento_judicial_fuerte:
        procs = _extraer_procedimientos(texto)
        partes = _extraer_partes_judiciales(texto)
    else:
        procs = []
        partes = {
            "demandantes": [], "demandados": [],
            "denunciantes": [], "denunciados": [],
            "ministerio_fiscal": False,
        }
    datos["procedimientos"] = procs
    datos["num_procedimiento"] = [p["numero"] for p in procs]
    datos.update(partes)

    datos["juez"] = _extraer_juez(texto)
    datos["dnis"] = [d["valor"] for d in _extraer_dnis(texto)]
    datos["dnis_detalle"] = _extraer_dnis(texto)

    datos["fecha_documento"] = _extraer_fecha_documento_judicial(texto)

    # Fechas sin etiqueta
    datos["fechas"] = extraer_fechas(texto)

    # IBAN/CCC se ignoran en judicial salvo apud_acta (que va por su propio extractor)
    datos["IBAN"] = ""
    datos["IBAN_Valido"] = False
    datos["IBANs"] = []
    datos["CCC"] = ""
    datos["CCC_Valido"] = False
    datos["CCC Valido"] = False
    datos["Titular"] = ""
    datos["Titulares"] = []
    datos["personas"] = _construir_personas(datos, texto)

    return datos


# ==========================================================
# Extractor APUD_ACTA / Registral / Genérico
# ==========================================================

def _extraer_apud_acta(texto):
    datos = {}
    # Extraemos todas las personas con prefijo D/Dª y NIF/NIE/DNI
    personas_apud = []
    for m in re.finditer(
        r"D/Dª\.?\s*([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑa-záéíóúñ\-']*(?:\s+(?!CON\s+(?:NIF|NIE|DNI)\b)[A-ZÁÉÍÓÚÑa-záéíóúñ\-']+){1,5})(?=\s+(?:CON\s+)?(?:NIF|NIE|DNI)\s*[:.]?\s*(?:\d{8}[A-Z]|[XYZ]\d{7,8}[A-Z]))",
        texto,
        re.IGNORECASE,
    ):
        nombre = _normalizar_nombre(m.group(1))
        if _es_nombre(nombre):
            personas_apud.append({"nombre": nombre, "pos": m.start()})

    # La primera persona es el otorgante.
    if len(personas_apud) >= 1:
        datos["otorgante"] = personas_apud[0]["nombre"]

    # Apoderado: persona tras la etiqueta A FAVOR DE, o la segunda persona si no hay etiqueta.
    m_favor = re.search(r"A\s+FAVOR\s+DE\s*(?:\(6\)\s*)?[:\-]?", texto, re.IGNORECASE)
    if m_favor:
        pos_favor = m_favor.end()
        # Elegir la persona más cercana a A FAVOR DE (excluyendo al otorgante)
        personas_apud.sort(key=lambda x: abs(x["pos"] - pos_favor))
        for p in personas_apud:
            if p["nombre"] != datos.get("otorgante"):
                datos["apoderado"] = p["nombre"]
                break
    elif len(personas_apud) >= 2:
        datos["apoderado"] = personas_apud[1]["nombre"]

    # Vigencia
    m = re.search(r"VIGENCIA:\s*DESDE\s*(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4})\s+HASTA\s*(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4})", texto, re.IGNORECASE)
    if m:
        datos["vigencia_desde"], _ = _extraer_fecha_numerica(m.group(1))
        datos["vigencia_hasta"], _ = _extraer_fecha_numerica(m.group(2))
    # Fecha de creación
    m = re.search(r"FECHA\s+DE\s+CREACI[ÓO]N\s*[:.]?\s*(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4})", texto, re.IGNORECASE)
    if m:
        datos["fecha_documento"], _ = _extraer_fecha_numerica(m.group(1))

    datos["dnis"] = [d["valor"] for d in _extraer_dnis(texto)]
    datos["fechas"] = extraer_fechas(texto)
    datos["IBAN"] = ""
    datos["IBAN_Valido"] = False
    datos["CCC"] = ""
    datos["CCC_Valido"] = False
    datos["CCC Valido"] = False
    datos["Titular"] = ""
    datos["Titulares"] = []
    datos["personas"] = _construir_personas(datos, texto)
    return datos


def _extraer_generico(texto):
    datos = {
        "IBAN": "",
        "IBAN_Valido": False,
        "IBANs": [],
        "CCC": "",
        "CCC_Valido": False,
        "CCC Valido": False,
        "Titular": "",
        "Titulares": [],
        "dnis": [d["valor"] for d in _extraer_dnis(texto)],
        "fechas": extraer_fechas(texto),
    }
    datos["personas"] = _construir_personas(datos, texto)
    return datos


# ==========================================================
# Dominio y despacho
# ==========================================================

def _dominio_para_tipo(tipo_documento):
    if tipo_documento in _TIPOS_BANCARIOS:
        return "bancario"
    if tipo_documento in _TIPOS_JUDICIALES:
        return "judicial"
    return "desconocido"


def extract_titular(texto):
    """Compatibilidad histórica: devuelve el primer titular de tarjeta."""
    lineas = texto.splitlines()
    for i, line in enumerate(lineas):
        if "Titular de la tarjeta" in line:
            for siguiente_linea in lineas[i + 1:]:
                siguiente_linea = siguiente_linea.strip()
                if siguiente_linea:
                    return siguiente_linea
    return ""


_ROL_PRIORIDAD = {
    "demandado": 1,
    "denunciado": 2,
    "demandante": 3,
    "denunciante": 4,
    "otorgante": 5,
    "apoderado": 6,
    "titular": 7,
}


def _posicion_nombre_en_texto(texto, nombre):
    """Devuelve la posición aproximada del nombre en el texto, tolerando saltos de línea."""
    # Nombre exacto, normalizando espacios
    patron = re.compile(r"\b" + re.escape(nombre).replace(r"\ ", r"\s+") + r"\b", re.IGNORECASE)
    for m in patron.finditer(texto):
        return m.start()
    # Fallback: buscar los dos últimos apellidos
    tokens = nombre.split()
    if len(tokens) >= 2:
        sub = " ".join(tokens[-2:])
        patron_sub = re.compile(r"\b" + re.escape(sub).replace(r"\ ", r"\s+") + r"\b", re.IGNORECASE)
        for m in patron_sub.finditer(texto):
            return m.start()
    return None


def _dni_mas_cercano(dnis_con_pos, pos_nombre):
    """Devuelve (dni, distancia) al DNI más cercano a la posición del nombre."""
    if not dnis_con_pos or pos_nombre is None:
        return None, None
    mejor = min(dnis_con_pos, key=lambda dp: abs(dp["pos"] - pos_nombre))
    return mejor["valor"], abs(mejor["pos"] - pos_nombre)


def _construir_personas(datos, texto):
    """Construye la lista normalizada de personas con DNI asociado y rol único."""
    dnis_con_pos = []
    for m in re.finditer(r"\b(\d{8}[A-Z]|[XYZ]\d{7,8}[A-Z])\b", texto.upper()):
        val = m.group(1)
        normalizado, valido = _validar_dni(val)
        if normalizado:
            dnis_con_pos.append({"valor": normalizado, "pos": m.start(), "valido": valido})

    # Recogemos todos los nombres por rol detectado
    candidatos = []
    mapeo_roles = {
        "titular": datos.get("Titulares", []) or ([datos.get("Titular")] if datos.get("Titular") else []),
        "demandante": datos.get("demandantes", []),
        "demandado": datos.get("demandados", []),
        "denunciante": datos.get("denunciantes", []),
        "denunciado": datos.get("denunciados", []),
        "otorgante": [datos.get("otorgante")] if datos.get("otorgante") else [],
        "apoderado": [datos.get("apoderado")] if datos.get("apoderado") else [],
    }

    nombres_conocidos = set()
    for rol, nombres in mapeo_roles.items():
        for nombre in nombres:
            if not nombre or not isinstance(nombre, str):
                continue
            nombre_canonico = _normalizar_nombre(nombre)
            nombres_conocidos.add(nombre_canonico)
            pos = _posicion_nombre_en_texto(texto, nombre_canonico)

            # Preferimos un DNI en la misma línea del nombre
            dni = None
            distancia = None
            if pos is not None:
                linea_inicio = texto.rfind("\n", 0, pos) + 1
                linea_fin = texto.find("\n", pos)
                if linea_fin == -1:
                    linea_fin = len(texto)
                linea = texto[linea_inicio:linea_fin]
                for m in re.finditer(r"\b(\d{8}[A-Z]|[XYZ]\d{7,8}[A-Z])\b", linea.upper()):
                    val = m.group(1)
                    normalizado, _ = _validar_dni(val)
                    if normalizado:
                        dni = normalizado
                        distancia = abs(linea_inicio + m.start() - pos)
                        break

            # Si no hay DNI en la misma línea, buscamos el más cercano
            if not dni:
                dni, distancia = _dni_mas_cercano(dnis_con_pos, pos)

            confianza = "alta" if distancia is not None and distancia <= 200 else (
                "media" if distancia is not None and distancia <= 500 else "baja"
            )
            # Sin DNI visible => confianza baja si no hay contexto claro
            if not dni:
                confianza = "media" if pos is not None else "baja"
            candidatos.append({
                "nombre": nombre_canonico,
                "dni": dni,
                "rol": rol,
                "confianza": confianza,
                "variantes": [],
            })

    # Fallback: buscar en el texto personas con prefijo D./Doña y DNI/NIF
    # que no hayan sido capturadas por los extractores específicos.
    prefijo = r"(?:D[./]\s*|D\.ª\s*|D/ña\.?\s*|Doña\s+|Do\s+|Dña\.?\s+|DON\s+|DOÑA\s+|D/Dª\.?\s*)"
    patron_persona_dni = re.compile(
        prefijo + r"([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑa-záéíóúñ\-'']*(?:\s+[A-ZÁÉÍÓÚÑa-záéíóúñ\-'']+){2,5}).{0,80}?\bcon\b\s+(?:NIF|NIE|DNI)\s*[:.]?\s*(\d{8}[A-Z]|[XYZ]\d{7,8}[A-Z])",
        re.IGNORECASE | re.DOTALL,
    )
    for m in patron_persona_dni.finditer(texto):
        nombre = _normalizar_nombre(m.group(1))
        dni = _validar_dni(m.group(2))[0]
        if nombre not in nombres_conocidos and _es_nombre(nombre):
            candidatos.append({
                "nombre": nombre,
                "dni": dni,
                "rol": "desconocido",
                "confianza": "alta",
                "variantes": [],
            })

    # Deduplicar por nombre canónico (mismo nombre = misma persona en este documento)
    por_nombre = {}
    for c in candidatos:
        key = c["nombre"]
        if key not in por_nombre:
            por_nombre[key] = []
        por_nombre[key].append(c)

    personas = []
    for nombre, lista in por_nombre.items():
        # Elegir el rol de mayor prioridad
        lista_ordenada = sorted(lista, key=lambda x: _ROL_PRIORIDAD.get(x["rol"], 99))
        elegido = lista_ordenada[0].copy()
        roles_detectados = sorted({c["rol"] for c in lista},
                                  key=lambda r: _ROL_PRIORIDAD.get(r, 99))
        if len(roles_detectados) > 1:
            elegido["conflicto_roles"] = True
            elegido["roles_detectados"] = roles_detectados
        # Elegir el DNI con mayor confianza entre las apariciones
        dnis_validos = [c["dni"] for c in lista if c["dni"]]
        if dnis_validos:
            # Tomar el DNI que esté más cerca (el del candidato principal)
            elegido["dni"] = dnis_validos[0]
        personas.append(elegido)

    return personas


def extract_data(texto, tipo_documento):
    datos = {}
    datos["tipo"] = tipo_documento
    datos["num_caracteres"] = len(texto)
    datos["dominio"] = _dominio_para_tipo(tipo_documento)

    if datos["dominio"] == "bancario":
        datos.update(_extraer_bancario(texto, tipo_documento))
    elif tipo_documento == "APUD_ACTA":
        datos.update(_extraer_apud_acta(texto))
    elif datos["dominio"] == "judicial":
        datos.update(_extraer_judicial(texto, tipo_documento))
    else:
        datos.update(_extraer_generico(texto))

    # Garantizar claves de compatibilidad si faltan
    for clave, default in [
        ("IBAN", ""), ("IBAN_Valido", False), ("IBANs", []),
        ("CCC", ""), ("CCC_Valido", False), ("CCC Valido", False),
        ("Titular", ""), ("Titulares", []),
        ("dnis", []), ("tribunal", ""), ("num_procedimiento", []),
        ("organo", ""), ("numero_organo", ""), ("plaza", ""), ("sala", ""),
        ("nig", ""), ("numero_resolucion", ""),
        ("demandantes", []), ("demandados", []),
        ("denunciantes", []), ("denunciados", []), ("ministerio_fiscal", False),
        ("juez", ""), ("otorgante", ""), ("apoderado", ""),
        ("vigencia_desde", None), ("vigencia_hasta", None),
        ("fecha_documento", None), ("fecha_operacion", None),
        ("fecha_valor", None), ("fecha_desde", None), ("fecha_hasta", None),
        ("fechas", []), ("personas", []),
    ]:
        datos.setdefault(clave, default)

    return datos
