"""
Tests para la normalización de personas en la base de datos.
"""

import pytest
from pathlib import Path
from documenttoolkit.database import DocumentDatabase


@pytest.fixture
def db(tmp_path):
    db_path = tmp_path / "test_personas.db"
    return DocumentDatabase(db_path=str(db_path))


def test_sincronizar_personas_crea_registros(db):
    doc_id = db.guardar_documento(
        ruta="/tmp/doc1.pdf",
        tipo_entrada="pdf",
        tipo_doc="ESCRITO_JUDICIAL",
        texto="texto",
        num_chars=100,
        dominio="judicial",
        datos_dict={
            "personas": [
                {"nombre": "MANUEL IGNACIO DEL REY CARRAL", "dni": "44083275A", "rol": "demandado", "confianza": "alta"},
                {"nombre": "CIRA ROMERO ESCUDERO", "dni": "46676617A", "rol": "demandante", "confianza": "alta"},
            ]
        },
    )

    personas = db.listar_personas()
    assert len(personas) == 2

    docs = db.documentos_de_persona(personas[0]["id"])
    assert len(docs) == 1
    assert docs[0]["rol"] in ("demandado", "demandante")


def test_no_duplica_personas_iguales(db):
    for i in range(2):
        db.guardar_documento(
            ruta=f"/tmp/doc{i}.pdf",
            tipo_entrada="pdf",
            tipo_doc="ESCRITO_JUDICIAL",
            texto="texto",
            num_chars=100,
            dominio="judicial",
            datos_dict={
                "personas": [
                    {"nombre": "MANUEL IGNACIO DEL REY CARRAL", "dni": "44083275A", "rol": "demandado", "confianza": "alta"},
                ]
            },
        )

    personas = db.listar_personas()
    assert len(personas) == 1


def test_persona_sin_dni_puede_repetirse(db):
    db.guardar_documento(
        ruta="/tmp/doc1.pdf",
        tipo_entrada="pdf",
        tipo_doc="CONTRATO",
        texto="texto",
        num_chars=100,
        dominio="desconocido",
        datos_dict={
            "personas": [
                {"nombre": "JUAN PEREZ GARCIA", "dni": None, "rol": "desconocido", "confianza": "baja"},
            ]
        },
    )
    db.guardar_documento(
        ruta="/tmp/doc2.pdf",
        tipo_entrada="pdf",
        tipo_doc="CONTRATO",
        texto="texto",
        num_chars=100,
        dominio="desconocido",
        datos_dict={
            "personas": [
                {"nombre": "ANA LOPEZ TORRES", "dni": None, "rol": "desconocido", "confianza": "baja"},
            ]
        },
    )

    personas = db.listar_personas()
    assert len(personas) == 2


def test_buscar_persona_por_dni(db):
    db.guardar_documento(
        ruta="/tmp/doc1.pdf",
        tipo_entrada="pdf",
        tipo_doc="ESCRITO_JUDICIAL",
        texto="texto",
        num_chars=100,
        dominio="judicial",
        datos_dict={
            "personas": [
                {"nombre": "MANUEL IGNACIO DEL REY CARRAL", "dni": "44083275A", "rol": "demandado", "confianza": "alta"},
            ]
        },
    )

    resultados = db.buscar_persona("44083275A")
    assert len(resultados) == 1
    assert resultados[0]["nombre_canonico"] == "MANUEL IGNACIO DEL REY CARRAL"


def test_json_actualizado_con_persona_id(db):
    doc_id = db.guardar_documento(
        ruta="/tmp/doc1.pdf",
        tipo_entrada="pdf",
        tipo_doc="ESCRITO_JUDICIAL",
        texto="texto",
        num_chars=100,
        dominio="judicial",
        datos_dict={
            "personas": [
                {"nombre": "MANUEL IGNACIO DEL REY CARRAL", "dni": "44083275A", "rol": "demandado", "confianza": "alta"},
            ]
        },
    )

    doc = db.obtener_por_ruta("/tmp/doc1.pdf")
    assert "persona_id" in doc["datos"]["personas"][0]
    assert isinstance(doc["datos"]["personas"][0]["persona_id"], int)
