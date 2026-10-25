"""
test_database_diarizacion.py
Tests de las nuevas tablas hijas para guionización.
"""

import json
import pytest
from pathlib import Path
from documenttoolkit.database import DocumentDatabase


@pytest.fixture
def db(tmp_path):
    return DocumentDatabase(db_path=str(tmp_path / "test.db"))


@pytest.fixture
def doc_id(db):
    return db.guardar_documento(
        ruta="/tmp/prueba.m4a",
        tipo_entrada="audio",
        tipo_doc="TRANSCRIPCION_AUDIO",
        texto="texto",
        num_chars=5,
        dominio="judicial",
        datos_dict={},
    )


def test_guardar_y_obtener_segmentos_asr(db, doc_id):
    segmentos = [
        {
            "inicio": 0.0,
            "fin": 1.0,
            "texto": "hola",
            "palabras": [{"inicio": 0.0, "fin": 1.0, "texto": "hola"}],
        }
    ]
    db.guardar_segmentos_asr(doc_id, segmentos)
    resultado = db.obtener_segmentos_asr(doc_id)

    assert len(resultado) == 1
    assert resultado[0]["texto"] == "hola"
    assert resultado[0]["palabras"][0]["texto"] == "hola"


def test_guardar_y_obtener_turnos_diarizacion(db, doc_id):
    turnos = [
        {"hablante_id": "HABLANTE_1", "inicio": 0.0, "fin": 1.0},
        {"hablante_id": "HABLANTE_2", "inicio": 2.0, "fin": 3.0},
    ]
    db.guardar_turnos_diarizacion(doc_id, turnos)
    resultado = db.obtener_turnos_diarizacion(doc_id)

    assert len(resultado) == 2
    assert resultado[0]["hablante_id"] == "HABLANTE_1"


def test_guardar_y_obtener_hablantes(db, doc_id):
    db.guardar_hablante(doc_id, "HABLANTE_1", "LETRADO")
    assert db.obtener_hablantes(doc_id) == {"HABLANTE_1": "LETRADO"}

    db.guardar_hablante(doc_id, "HABLANTE_1", None)
    assert db.obtener_hablantes(doc_id) == {}


def test_guardar_y_obtener_turnos_guion(db, doc_id):
    turnos = [
        {
            "hablante": "HABLANTE_1",
            "inicio": 0.0,
            "fin": 1.0,
            "texto": "hola",
            "confianza_media": 0.9,
            "es_solapamiento": False,
            "requiere_revision": False,
        },
        {
            "hablante": "SOLAPAMIENTO",
            "inicio": 2.0,
            "fin": 3.0,
            "texto": "voces",
            "confianza_media": 0.5,
            "es_solapamiento": True,
            "requiere_revision": False,
            "hablantes_solapados": ["HABLANTE_1", "HABLANTE_2"],
        },
    ]
    db.guardar_turnos_guion(doc_id, turnos)
    resultado = db.obtener_turnos_guion(doc_id)

    assert len(resultado) == 2
    assert resultado[0]["texto"] == "hola"
    assert resultado[1]["hablantes_solapados"] == ["HABLANTE_1", "HABLANTE_2"]


def test_eliminar_datos_diarizacion(db, doc_id):
    db.guardar_segmentos_asr(doc_id, [{"inicio": 0, "fin": 1, "texto": "x", "palabras": []}])
    db.guardar_turnos_diarizacion(doc_id, [{"hablante_id": "H1", "inicio": 0, "fin": 1}])
    db.guardar_hablante(doc_id, "H1", "A")
    db.guardar_turnos_guion(doc_id, [{"hablante": "H1", "inicio": 0, "fin": 1, "texto": "x"}])

    db.eliminar_datos_diarizacion(doc_id)

    assert db.obtener_segmentos_asr(doc_id) == []
    assert db.obtener_turnos_diarizacion(doc_id) == []
    assert db.obtener_hablantes(doc_id) == {}
    assert db.obtener_turnos_guion(doc_id) == []


def test_documento_base_no_se_borra_al_eliminar_diarizacion(db, doc_id):
    db.guardar_segmentos_asr(doc_id, [{"inicio": 0, "fin": 1, "texto": "x", "palabras": []}])
    db.eliminar_datos_diarizacion(doc_id)

    doc = db.obtener_por_ruta("/tmp/prueba.m4a")
    assert doc is not None
    assert doc["texto_extraido"] == "texto"
