"""
test_guion.py
Tests unitarios de la fase de alineación y formato del guion.
No cargan modelos de diarización ni Whisper; usan datos sintéticos.
"""

import pytest
from documenttoolkit.guion import (
    Palabra,
    TurnoVoz,
    alinear_palabras_a_turnos,
    agrupar_turnos_guion,
    renderizar_guion,
    construir_guion,
    formatear_tiempo,
    ID_HABLANTE_DESCONOCIDO,
    ETIQUETA_SOLAPAMIENTO,
)


class TestFormatearTiempo:
    def test_segundos(self):
        assert formatear_tiempo(12.34) == "00:12.340"

    def test_minutos(self):
        assert formatear_tiempo(72.5) == "01:12.500"

    def test_horas(self):
        assert formatear_tiempo(3661.123) == "01:01:01.123"


class TestAlinearPalabras:
    def test_asignacion_simple(self):
        palabras = [
            Palabra(inicio=0.0, fin=0.5, texto="Hola"),
            Palabra(inicio=0.6, fin=1.0, texto="mundo"),
            Palabra(inicio=2.0, fin=2.5, texto="Adios"),
        ]
        turnos = [
            TurnoVoz(hablante="HABLANTE_1", inicio=0.0, fin=1.2),
            TurnoVoz(hablante="HABLANTE_2", inicio=1.8, fin=2.8),
        ]
        resultado = alinear_palabras_a_turnos(palabras, turnos)

        assert [p.hablante for p in resultado] == ["HABLANTE_1", "HABLANTE_1", "HABLANTE_2"]
        assert resultado[0].solapamiento > 0

    def test_palabra_desconocida(self):
        palabras = [Palabra(inicio=5.0, fin=5.4, texto="suelta")]
        turnos = [TurnoVoz(hablante="HABLANTE_1", inicio=0.0, fin=1.0)]
        resultado = alinear_palabras_a_turnos(palabras, turnos)

        assert resultado[0].hablante == ID_HABLANTE_DESCONOCIDO
        assert resultado[0].solapamiento == pytest.approx(0.0)

    def test_cobertura_insuficiente(self):
        palabras = [Palabra(inicio=0.9, fin=1.3, texto="corta")]
        turnos = [TurnoVoz(hablante="HABLANTE_1", inicio=0.0, fin=1.0)]
        resultado = alinear_palabras_a_turnos(
            palabras, turnos, umbral_cobertura=0.5
        )

        # Solo la mitad de la palabra está cubierta; por debajo del umbral
        assert resultado[0].hablante == ID_HABLANTE_DESCONOCIDO

    def test_solucion_simple_sin_confusion(self):
        palabras = [Palabra(inicio=0.4, fin=0.9, texto="clara")]
        turnos = [
            TurnoVoz(hablante="HABLANTE_1", inicio=0.0, fin=1.0),
            TurnoVoz(hablante="HABLANTE_2", inicio=2.0, fin=3.0),
        ]
        resultado = alinear_palabras_a_turnos(palabras, turnos)
        assert resultado[0].hablante == "HABLANTE_1"

    def test_solucion_marcada_como_solapamiento(self):
        palabras = [Palabra(inicio=1.5, fin=2.5, texto="mezcla")]
        turnos = [
            TurnoVoz(hablante="HABLANTE_1", inicio=0.0, fin=2.0),
            TurnoVoz(hablante="HABLANTE_2", inicio=2.0, fin=3.0),
        ]
        # La palabra cubre 0.5s de cada turno -> confusion 1.0 (>= umbral_confusion)
        resultado = alinear_palabras_a_turnos(palabras, turnos)
        assert resultado[0].hablante == ETIQUETA_SOLAPAMIENTO
        assert set(resultado[0].hablantes_solapados) == {"HABLANTE_1", "HABLANTE_2"}


class TestAgruparTurnos:
    def test_agrupacion_mismo_hablante(self):
        palabras = [
            Palabra(inicio=0.0, fin=0.4, texto="Buenos", hablante="HABLANTE_1", solapamiento=1.0),
            Palabra(inicio=0.5, fin=0.9, texto="dias", hablante="HABLANTE_1", solapamiento=1.0),
            Palabra(inicio=1.0, fin=1.4, texto="señoria", hablante="HABLANTE_1", solapamiento=1.0),
        ]
        turnos = agrupar_turnos_guion(palabras)

        assert len(turnos) == 1
        assert turnos[0].hablante == "HABLANTE_1"
        assert turnos[0].texto == "Buenos dias señoria"
        assert turnos[0].inicio == pytest.approx(0.0)
        assert turnos[0].fin == pytest.approx(1.4)

    def test_separacion_cambio_hablante(self):
        palabras = [
            Palabra(inicio=0.0, fin=0.4, texto="Hola", hablante="HABLANTE_1", solapamiento=1.0),
            Palabra(inicio=0.5, fin=0.9, texto="adios", hablante="HABLANTE_2", solapamiento=1.0),
        ]
        turnos = agrupar_turnos_guion(palabras)

        assert len(turnos) == 2
        assert turnos[0].hablante == "HABLANTE_1"
        assert turnos[1].hablante == "HABLANTE_2"

    def test_separacion_por_pausa(self):
        palabras = [
            Palabra(inicio=0.0, fin=0.4, texto="A", hablante="HABLANTE_1", solapamiento=1.0),
            Palabra(inicio=4.0, fin=4.4, texto="B", hablante="HABLANTE_1", solapamiento=1.0),
        ]
        turnos = agrupar_turnos_guion(palabras, umbral_pausa=1.0)

        assert len(turnos) == 2

    def test_turno_desconocido_requiere_revision(self):
        palabras = [
            Palabra(inicio=0.0, fin=0.4, texto="x", hablante=ID_HABLANTE_DESCONOCIDO, solapamiento=0.0),
        ]
        turnos = agrupar_turnos_guion(palabras)

        assert len(turnos) == 1
        assert turnos[0].requiere_revision is True


class TestRenderizarGuion:
    def test_incluye_etiqueta_visible(self):
        from documenttoolkit.guion import TurnoGuion
        turnos = [
            TurnoGuion(
                hablante="HABLANTE_1",
                inicio=0.0,
                fin=1.0,
                texto="Buenos dias",
                confianza_media=1.0,
            )
        ]
        texto = renderizar_guion(
            turnos,
            mapa_etiquetas={"HABLANTE_1": "LETRADO"},
            incluir_cabecera=False,
        )

        assert "LETRADO" in texto
        assert "HABLANTE_1" not in texto
        assert "Buenos dias" in texto
        assert "00:00.000 --> 00:01.000" in texto

    def test_marca_revision(self):
        from documenttoolkit.guion import TurnoGuion
        turnos = [
            TurnoGuion(
                hablante=ID_HABLANTE_DESCONOCIDO,
                inicio=0.0,
                fin=1.0,
                texto="inaudible",
                confianza_media=0.0,
                requiere_revision=True,
            )
        ]
        texto = renderizar_guion(turnos, incluir_cabecera=False)

        assert "[?]" in texto
        assert ID_HABLANTE_DESCONOCIDO in texto

    def test_pausa_entre_turnos(self):
        from documenttoolkit.guion import TurnoGuion
        turnos = [
            TurnoGuion(
                hablante="HABLANTE_1",
                inicio=0.0,
                fin=1.0,
                texto="A",
                confianza_media=1.0,
            ),
            TurnoGuion(
                hablante="HABLANTE_2",
                inicio=3.0,
                fin=4.0,
                texto="B",
                confianza_media=1.0,
            ),
        ]
        texto = renderizar_guion(turnos, incluir_cabecera=False)

        assert "(pausa 2.0 s)" in texto

    def test_bloque_solapamiento(self):
        from documenttoolkit.guion import TurnoGuion
        turnos = [
            TurnoGuion(
                hablante=ETIQUETA_SOLAPAMIENTO,
                inicio=10.0,
                fin=11.0,
                texto="voces mezcladas",
                confianza_media=0.5,
                es_solapamiento=True,
                hablantes_solapados=["HABLANTE_1", "HABLANTE_2"],
            )
        ]
        texto = renderizar_guion(turnos, incluir_cabecera=False)

        assert ETIQUETA_SOLAPAMIENTO in texto
        assert "voces mezcladas" in texto
        assert "no separable" in texto
        assert "HABLANTE_1, HABLANTE_2" in texto

    def test_cabecera_metodologica(self):
        texto = renderizar_guion([], metadatos={"Archivo": "prueba.wav"})
        assert "GUION DE TRANSCRIPCION" in texto
        assert "Archivo: prueba.wav" in texto
        assert "NOTA METODOLOGICA" in texto


class TestConstruirGuion:
    def test_pipeline_completo(self):
        segmentos = [
            {
                "inicio": 0.0,
                "fin": 2.0,
                "texto": "hola adios",
                "palabras": [
                    {"inicio": 0.0, "fin": 0.5, "texto": "hola"},
                    {"inicio": 1.5, "fin": 2.0, "texto": "adios"},
                ],
            }
        ]
        turnos = [
            {"hablante_id": "HABLANTE_1", "inicio": 0.0, "fin": 1.0},
            {"hablante_id": "HABLANTE_2", "inicio": 1.2, "fin": 2.2},
        ]
        guion_turnos = construir_guion(segmentos, turnos)

        assert len(guion_turnos) == 2
        assert guion_turnos[0].hablante == "HABLANTE_1"
        assert "hola" in guion_turnos[0].texto
        assert guion_turnos[1].hablante == "HABLANTE_2"
        assert "adios" in guion_turnos[1].texto

    def test_palabra_sin_turno(self):
        segmentos = [
            {
                "inicio": 0.0,
                "fin": 1.0,
                "texto": "suelta",
                "palabras": [
                    {"inicio": 0.0, "fin": 0.6, "texto": "suelta"},
                ],
            }
        ]
        turnos = [{"hablante_id": "HABLANTE_1", "inicio": 2.0, "fin": 3.0}]
        guion_turnos = construir_guion(segmentos, turnos)

        assert len(guion_turnos) == 1
        assert guion_turnos[0].hablante == ID_HABLANTE_DESCONOCIDO
        assert guion_turnos[0].requiere_revision is True

    def test_pipeline_con_solapamiento(self):
        segmentos = [
            {
                "inicio": 0.0,
                "fin": 3.0,
                "texto": "a b c",
                "palabras": [
                    {"inicio": 1.5, "fin": 2.5, "texto": "mezcla"},
                ],
            }
        ]
        turnos = [
            {"hablante_id": "HABLANTE_1", "inicio": 0.0, "fin": 2.0},
            {"hablante_id": "HABLANTE_2", "inicio": 2.0, "fin": 4.0},
        ]
        guion_turnos = construir_guion(segmentos, turnos)

        assert len(guion_turnos) == 1
        assert guion_turnos[0].es_solapamiento is True
        assert set(guion_turnos[0].hablantes_solapados) == {"HABLANTE_1", "HABLANTE_2"}
