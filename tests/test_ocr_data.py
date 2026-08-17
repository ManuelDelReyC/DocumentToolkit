from documenttoolkit.data_extractor import extract_titular
from documenttoolkit.data_extractor import extract_iban
from documenttoolkit.data_extractor import validate_iban
from documenttoolkit.data_extractor import validate_ccc

def test_extract_titular():
    texto = """
    Detalle del movimiento

    Titular de la tarjeta

    MANUEL IGNACIO DEL REY CARRAL

    Número de tarjeta

    5351 2005 6774 7050
    """

    resultado = extract_titular(texto)

    assert resultado == "MANUEL IGNACIO DEL REY CARRAL"


def test_extract_titular_varias_lineas():
    texto = """
    Detalle del movimiento

    Titular de la tarjeta

    

    MANUEL IGNACIO DEL REY CARRAL

    Número de tarjeta

    5351 2005 6774 7050
    """

    resultado = extract_titular(texto)

    assert resultado == "MANUEL IGNACIO DEL REY CARRAL"


def test_extract_titular_sin_titular():
    texto = """
    Detalle del movimiento

    Número de tarjeta

    5351 2005 6774 7050
    """

    resultado = extract_titular(texto)

    assert resultado == ""


def test_extract_iban_normal():
    texto = """
    Detalle del movimiento

    Número de cuenta

    ES81 1491 0001 2930 0013 2401
    
    """

    resultado = extract_iban(texto)

    assert resultado == "ES81 1491 0001 2930 0013 2401"

def test_extract_iban_espacios_delante():
    texto = """
    Detalle del movimiento

    Número de cuenta

       ES81 1491 0001 2930 0013 2401
    
    """

    resultado = extract_iban(texto)

    assert resultado == "ES81 1491 0001 2930 0013 2401"


def test_extract_iban_inexistente():
    texto = """
    Detalle del movimiento

    Número de cuenta

    
    """

    resultado = extract_iban(texto)

    assert resultado == ""


def test_extract_iban_sin_espacios():
    texto = """
    Detalle del movimiento

    Número de cuenta

    ES8114910001293000132401
    
    """

    resultado = "".join(extract_iban(texto).split())

    assert resultado == "ES8114910001293000132401"

def test_extract_iban_texto_invalido():
    texto = """
    Detalle del movimiento

    Número de cuenta

    ESTO NO ES UN IBAN

    """

    resultado = extract_iban(texto)

    assert resultado == ""

#Test validacion iban valido
def test_validate_iban_valido():
    iban = "ES8114910001293000132401"
    assert validate_iban(iban) is True

#Test validacion iban invalido
def test_validate_iban_invalido():
    iban = "ES8114910001293000132405"
    assert validate_iban(iban) is False

#Test validacion con Cuenta Corriente Valida
def test_validate_ccc_valido():
    ccc = "14910001293000132401"
    assert validate_ccc(ccc) is True

#Test validacion con Cuenta Corriente Invalida
def test_validate_ccc_invalido():
    ccc = "14910001293000132402"
    assert validate_ccc(ccc) is False
