from documenttoolkit.data_extractor import extract_titular
from documenttoolkit.data_extractor import extract_iban


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

    resultado = extract_iban(texto)

    assert resultado == "ES81 1491 0001 2930 0013 2401"