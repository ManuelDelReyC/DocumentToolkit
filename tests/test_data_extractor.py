import pytest
from documenttoolkit.data_extractor import (
    extract_data,
    extract_iban,
    extract_ccc,
    validate_iban,
    validate_ccc,
    extract_titular,
    _validar_dni,
    _extraer_fecha_texto,
    _extraer_fecha_numerica,
)


# ==========================================================
# Regresión: API pública anterior
# ==========================================================

def test_extract_titular_tarjeta():
    texto = """
    Detalle del movimiento

    Titular de la tarjeta

    MANUEL IGNACIO DEL REY CARRAL

    Número de tarjeta
    """
    assert extract_titular(texto) == "MANUEL IGNACIO DEL REY CARRAL"


def test_extract_iban_valido():
    texto = "Número de cuenta\n\nES81 1491 0001 2930 0013 2401"
    assert extract_iban(texto) == "ES81 1491 0001 2930 0013 2401"
    assert validate_iban(extract_iban(texto)) is True


def test_extract_ccc_desde_iban():
    # El CCC correcto debe derivarse del IBAN español válido
    texto = "IBAN ES81 1491 0001 2930 0013 2401"
    iban = extract_iban(texto)
    ccc = extract_ccc(texto, iban)
    assert ccc == "14910001293000132401"
    assert validate_ccc(ccc) is True


def test_validate_ccc_invalido():
    assert validate_ccc("14910001293000132402") is False


# ==========================================================
# Nuevas reglas: IBAN
# ==========================================================

def test_iban_con_sufijo_ocr():
    texto = "Cuenta de cargo\nES38 1465 0120 3317 0005 3937 (ING)\nDetalle"
    iban = extract_iban(texto)
    assert iban == "ES38 1465 0120 3317 0005 3937"
    assert validate_iban(iban) is True


def test_dos_ibans_transferencia():
    texto = """
    IBAN 1er Titular
    ES38 1465 0120 3317 0005 3937
    Nº cuenta destino / IBAN
    ES66 1491 0001 2830 0016 8998
    """
    datos = extract_data(texto, "TRANSFERENCIA_BANCARIA")
    assert datos["dominio"] == "bancario"
    assert datos["IBAN"] == "ES38 1465 0120 3317 0005 3937"
    assert "ES38 1465 0120 3317 0005 3937" in datos["IBANs"]
    assert "ES66 1491 0001 2830 0016 8998" in datos["IBANs"]


# ==========================================================
# Nuevas reglas: titulares
# ==========================================================

def test_dos_titulares_triodos():
    texto = """
    MANUEL IGNACIO DEL REY CARRAL
    CIRA ROMERO ESCUDERO
    Titulares de la Cuenta Núm. de Cuenta
    ES81 1491 0001 2930 0013 2401
    """
    datos = extract_data(texto, "EXTRACTO_BANCARIO")
    assert datos["Titular"] == "MANUEL IGNACIO DEL REY CARRAL"
    assert "MANUEL IGNACIO DEL REY CARRAL" in datos["Titulares"]
    assert "CIRA ROMERO ESCUDERO" in datos["Titulares"]


def test_titulares_pegados_a_digitos():
    texto = """
    1491 0001 29 3000132401CIRA ROMERO ESCUDERO 210001
    Titulares del Préstamo
    """
    datos = extract_data(texto, "HIPOTECA")
    assert "CIRA ROMERO ESCUDERO" in datos["Titulares"]


def test_nombre_invertido_ing_deduplicado():
    texto = """
    Titular de la domiciliación
    MANUEL IGNACIO DEL REY CARRAL
    REY CARRAL, MANUEL IGNACIO DEL
    """
    datos = extract_data(texto, "MOVIMIENTO_BANCARIO")
    assert len(datos["Titulares"]) == 1
    assert datos["Titular"] == "MANUEL IGNACIO DEL REY CARRAL"


def test_no_titular_en_tabla_movimientos():
    texto = """
    MANUEL IGNACIO DEL REY CARRAL
    CIRA ROMERO ESCUDERO
    Titulares de la Cuenta
    EXTRACTO DE OPERACIONES
    03-01-2024 9007 TRANSF DE CECILIA MANUELA JIMENEZ BORRELL
    """
    datos = extract_data(texto, "EXTRACTO_BANCARIO")
    assert "CECILIA MANUELA JIMENEZ BORRELL" not in datos["Titulares"]


# ==========================================================
# Nuevas reglas: fechas
# ==========================================================

def test_fechas_movimiento_ing():
    texto = """
    Fecha de operación
    18/05/2026
    Fecha de valor
    21/05/2026
    """
    datos = extract_data(texto, "MOVIMIENTO_BANCARIO")
    assert datos["fecha_operacion"] == "2026-05-18"
    assert datos["fecha_valor"] == "2026-05-21"


def test_fecha_cabecera_triodos():
    texto = "03-02-2024TRIODOS BANK 900822982\nEXTRACTO DE OPERACIONES"
    datos = extract_data(texto, "EXTRACTO_BANCARIO")
    assert datos["fecha_documento"] == "2024-02-03"


def test_rango_extracto():
    texto = """
    Fecha Oficina Concepto F. Valor Importe Saldo
    01-01-2024 SALDO ANTERIOR 866,67
    02-01-2024 PAGO 375,39
    18-01-2024 TRASPASO 108,39
    """
    datos = extract_data(texto, "EXTRACTO_BANCARIO")
    assert datos["fecha_desde"] == "2024-01-01"
    assert datos["fecha_hasta"] == "2024-01-18"


def test_periodo_hipoteca():
    texto = "Periodo 01-12-2022 hasta 01-01-2023\nFecha Valor 02-01-2023"
    datos = extract_data(texto, "HIPOTECA")
    assert datos["fecha_desde"] == "2022-12-01"
    assert datos["fecha_hasta"] == "2023-01-01"


def test_fecha_literal_auto():
    texto = "En Navalmoral de la Mata a 4 de Febrero de dos mil veinticinco."
    datos = extract_data(texto, "AUTO")
    assert datos["fecha_documento"] == "2025-02-04"


def test_fecha_literal_escrito_sin_segundo_de():
    texto = "En Cáceres, a 24 de febrero 2026.\nSUPLICO AL JUZGADO."
    datos = extract_data(texto, "ESCRITO_JUDICIAL")
    assert datos["fecha_documento"] == "2026-02-24"


# ==========================================================
# Nuevas reglas: judicial
# ==========================================================

def test_cabecera_auto_lexnet():
    texto = """
JDO.1A.INST.E INSTRUCCION N.3
NAVALMORAL DE LA MATA

AUTO: 00012/2025

N.I.G.: 10131 41 1 2024 0002061
Procedimiento origen: DCT DIVORCIO CONTENCIOSO 0000702 /2024

Sobre OTRAS MATERIAS
D/ña. MINISTERIO FISCAL, CIRA ROMERO ESCUDERO
Procurador/a Sr/a. , MARIA ARANZAZU DIAZ JIMENEZ

DEMANDADO  D/ña. MANUEL IGNACIO DEL REY CARRAL
Procurador/a Sr/a. MARIA PATROCINIO BERMEJO DAVILA

En Navalmoral de la Mata a 4 de Febrero de dos mil veinticinco.
"""
    datos = extract_data(texto, "AUTO")
    assert datos["dominio"] == "judicial"
    assert datos["organo"] == "JDO.1A.INST.E INSTRUCCION N.3"
    assert datos["tribunal"] == "Juzgado de 1ª Instancia e Instrucción N.3"
    assert datos["numero_organo"] == "3"
    assert datos["plaza"] == "NAVALMORAL DE LA MATA"
    assert datos["nig"] == "1013141120240002061"
    assert "702/2024" in datos["num_procedimiento"]
    assert "MANUEL IGNACIO DEL REY CARRAL" in datos["demandados"]
    assert datos["ministerio_fiscal"] is True
    assert datos["fecha_documento"] == "2025-02-04"


def test_escrito_demanda():
    texto = """
AL JUZGADO DE 1* INSTANCIA E INSTRUCCIÓN DECANO
DE NAVALMORAL DE LA MATA

DOÑA MARÍA ARANZAZU DÍAZ JIMÉNEZ, Procuradora de los Tribunales,
en representación de DOÑA CIRA ROMERO ESCUDERO, mayor de edad, con DNI 46676617A,
ante el Juzgado comparece y, como mejor proceda en derecho, DICE:

Que vengo a formular DEMANDA DE DIVORCIO, frente a su marido,
DON MANUEL IGNACIO DEL REY CARRAL, mayor de edad, con DNI 44083275A.

Lo que es de Justicia que pido en Navalmoral de la Mata, a 6 de Noviembre de 2024.
"""
    datos = extract_data(texto, "ESCRITO_JUDICIAL")
    assert datos["organo"]
    assert "CIRA ROMERO ESCUDERO" in datos["demandantes"]
    assert "MANUEL IGNACIO DEL REY CARRAL" in datos["demandados"]
    assert "46676617A" in datos["dnis"]
    assert "44083275A" in datos["dnis"]
    assert datos["fecha_documento"] == "2024-11-06"


def test_validar_dni():
    assert _validar_dni("46676617A")[1] is True
    assert _validar_dni("44083275A")[1] is True
    assert _validar_dni("44083275B")[1] is False


def test_apud_acta():
    texto = """
CERTIFICADO DE INSCRIPCION DE APODERAMIENTO

D/Dª MANUEL IGNACIO DEL REY CARRAL CON NIF 44083275A CON DOMICILIO EN MADRIGAL DE LA VERA

A FAVOR DE (6):
D/Dª RICARD SIMO PASCUAL CON NIF 35077543J

VIGENCIA: DESDE 29/07/2024 HASTA 29/07/2025
FECHA DE CREACIÓN: 29/07/2024 17:27:50
"""
    datos = extract_data(texto, "APUD_ACTA")
    assert datos["otorgante"] == "MANUEL IGNACIO DEL REY CARRAL"
    assert datos["apoderado"] == "RICARD SIMO PASCUAL"
    assert datos["vigencia_desde"] == "2024-07-29"
    assert datos["vigencia_hasta"] == "2025-07-29"
    assert datos["fecha_documento"] == "2024-07-29"


# ==========================================================
# Reglas negativas: no falsos positivos
# ==========================================================

def test_no_ccc_en_demanda():
    texto = """
    DEMANDA DE DIVORCIO

    DOÑA CIRA ROMERO ESCUDERO, mayor de edad, con DNI 46676617A,
    contrajeron matrimonio el 28 de Julio de 2011.
    La pensión compensatoria asciende a 424,00 € mensuales.
    """
    datos = extract_data(texto, "ESCRITO_JUDICIAL")
    assert datos["CCC"] == ""
    assert datos["CCC_Valido"] is False


def test_no_titular_en_contrato():
    texto = """
    CONTRATO DE COMPRAVENTA

    REUNIDOS en Madrid, a 15 de enero de 2024, intervienen DON MANUEL DEL REY
    y DOÑA CIRA ROMERO, en su propio nombre y derecho.
    """
    datos = extract_data(texto, "CONTRATO")
    assert datos["Titular"] == ""
    assert datos["Titulares"] == []


def test_dominio_asignado():
    assert extract_data("x", "EXTRACTO_BANCARIO")["dominio"] == "bancario"
    assert extract_data("x", "AUTO")["dominio"] == "judicial"
    assert extract_data("x", "CONTRATO")["dominio"] == "desconocido"


def test_personas_judicial_con_dni():
    texto = """
    AL JUZGADO DE 1ª INSTANCIA E INSTRUCCIÓN DE NAVALMORAL DE LA MATA

    DEMANDANTE: DOÑA CIRA ROMERO ESCUDERO, mayor de edad, con DNI 46676617A.
    DEMANDADO: DON MANUEL IGNACIO DEL REY CARRAL, mayor de edad, con DNI 44083275A.
    """
    datos = extract_data(texto, "ESCRITO_JUDICIAL")
    personas = {p["nombre"]: p for p in datos["personas"]}
    assert "CIRA ROMERO ESCUDERO" in personas
    assert personas["CIRA ROMERO ESCUDERO"]["dni"] == "46676617A"
    assert personas["CIRA ROMERO ESCUDERO"]["rol"] == "demandante"
    assert "MANUEL IGNACIO DEL REY CARRAL" in personas
    assert personas["MANUEL IGNACIO DEL REY CARRAL"]["dni"] == "44083275A"


def test_personas_bancarias_sin_dni():
    texto = "Titular de la cuenta\nMANUEL IGNACIO DEL REY CARRAL\nIBAN ES81..."
    datos = extract_data(texto, "EXTRACTO_BANCARIO")
    nombres = [p["nombre"] for p in datos["personas"]]
    assert "MANUEL IGNACIO DEL REY CARRAL" in nombres


def test_personas_apud_acta():
    texto = """
    D/Dª MANUEL IGNACIO DEL REY CARRAL CON NIF 44083275A
    A FAVOR DE: D/Dª RICARD SIMO PASCUAL CON NIF 35077543J
    """
    datos = extract_data(texto, "APUD_ACTA")
    personas = {p["nombre"]: p for p in datos["personas"]}
    assert personas["MANUEL IGNACIO DEL REY CARRAL"]["dni"] == "44083275A"
    assert personas["MANUEL IGNACIO DEL REY CARRAL"]["rol"] == "otorgante"
    assert personas["RICARD SIMO PASCUAL"]["dni"] == "35077543J"
    assert personas["RICARD SIMO PASCUAL"]["rol"] == "apoderado"


def test_personas_rol_unico_prioridad():
    # Si una persona aparece como demandante y demandado, se elige demandado
    texto = """
    AL JUZGADO DE 1ª INSTANCIA E INSTRUCCIÓN DE NAVALMORAL DE LA MATA

    DEMANDANTE: DOÑA CIRA ROMERO ESCUDERO, con DNI 46676617A.
    DEMANDADO: DOÑA CIRA ROMERO ESCUDERO.
    """
    datos = extract_data(texto, "ESCRITO_JUDICIAL")
    cira = [p for p in datos["personas"] if p["nombre"] == "CIRA ROMERO ESCUDERO"][0]
    assert cira["rol"] == "demandado"
    assert cira.get("conflicto_roles") is True
