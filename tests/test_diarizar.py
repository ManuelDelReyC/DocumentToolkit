"""
test_diarizar.py
Tests de la fase 2 de guionización (diarización).
No descargan modelos salvo el test de integración, que se salta si no hay
pyannote.audio o HF_TOKEN.
"""

import importlib.util
import os
import struct
import wave
from pathlib import Path

import pytest

from documenttoolkit.database import DocumentDatabase
from documenttoolkit.diarizar import (
    _anotacion_a_turnos,
    _canales_a_turnos,
    _canales_estan_separados,
    _gestion_llm,
    _sha256_archivo,
)


# ============ Helpers ============

def _escribir_wav_estereo(ruta: Path, canales: int, muestras_por_canal, frecuencias):
    """
    Escribe un WAV con canales independientes. Cada canal reproduce su propia
    frecuencia de seno en los intervalos indicados por muestras_por_canal.
    """
    sr = 16000
    duracion_total = max(len(m) for m in muestras_por_canal) / sr
    n_muestras = int(duracion_total * sr)

    data = []
    for i in range(n_muestras):
        frame = []
        for c in range(canales):
            if i < len(muestras_por_canal[c]) and muestras_por_canal[c][i]:
                import math
                t = i / sr
                frame.append(int(32767 * 0.8 * math.sin(2 * math.pi * frecuencias[c] * t)))
            else:
                frame.append(0)
        data.append(frame)

    with wave.open(str(ruta), "w") as wf:
        wf.setnchannels(canales)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        for frame in data:
            for sample in frame:
                wf.writeframesraw(struct.pack("<h", sample))


def _wav_separado(tmp_path: Path) -> Path:
    """Estéreo con hablante en canal 0 durante 1 s y en canal 1 durante el siguiente."""
    ruta = tmp_path / "separado.wav"
    sr = 16000
    muestras_c0 = [True] * sr + [False] * sr
    muestras_c1 = [False] * sr + [True] * sr
    _escribir_wav_estereo(ruta, 2, [muestras_c0, muestras_c1], [400, 800])
    return ruta


def _wav_mezclado(tmp_path: Path) -> Path:
    """Estéreo con la misma señal en ambos canales."""
    ruta = tmp_path / "mezclado.wav"
    sr = 16000
    muestras = [True] * (2 * sr)
    _escribir_wav_estereo(ruta, 2, [muestras, muestras], [400, 400])
    return ruta


def _wav_mono(tmp_path: Path) -> Path:
    """WAV mono."""
    ruta = tmp_path / "mono.wav"
    sr = 16000
    muestras = [True] * sr
    _escribir_wav_estereo(ruta, 1, [muestras], [400])
    return ruta


# ============ Tests unitarios ============

class TestAnotacionATurnos:
    def test_api_nueva_speaker_diarization(self):
        class Turn:
            def __init__(self, start, end):
                self.start = start
                self.end = end

        class Output:
            speaker_diarization = [
                (Turn(0.0, 1.5), "SPEAKER_00"),
                (Turn(2.0, 3.5), "SPEAKER_01"),
            ]

        turnos = _anotacion_a_turnos(Output())
        assert len(turnos) == 2
        assert turnos[0] == {"hablante_id": "SPEAKER_00", "inicio": 0.0, "fin": 1.5}
        assert turnos[1] == {"hablante_id": "SPEAKER_01", "inicio": 2.0, "fin": 3.5}

    def test_api_legacy_itertracks(self):
        class Turn:
            def __init__(self, start, end):
                self.start = start
                self.end = end

        class Annotation:
            def itertracks(self, yield_label=False):
                assert yield_label is True
                return iter([
                    (Turn(0.0, 1.0), "A", "SPEAKER_01"),
                    (Turn(1.5, 2.5), "B", "SPEAKER_02"),
                ])

        turnos = _anotacion_a_turnos(Annotation())
        assert len(turnos) == 2
        assert turnos[0] == {"hablante_id": "SPEAKER_01", "inicio": 0.0, "fin": 1.0}


class TestCanalesSeparados:
    def test_detecta_canales_separados(self, tmp_path):
        ruta = _wav_separado(tmp_path)
        assert _canales_estan_separados(ruta) is True

    def test_rechaza_canales_mezclados(self, tmp_path):
        ruta = _wav_mezclado(tmp_path)
        assert _canales_estan_separados(ruta) is False

    def test_mono_nunca_separado(self, tmp_path):
        ruta = _wav_mono(tmp_path)
        assert _canales_estan_separados(ruta) is False


class TestCanalesATurnos:
    def test_genera_un_turno_por_canal(self, tmp_path):
        ruta = _wav_separado(tmp_path)
        turnos = _canales_a_turnos(ruta)
        assert len(turnos) == 2
        ids = [t["hablante_id"] for t in turnos]
        assert "HABLANTE_1" in ids
        assert "HABLANTE_2" in ids

        t0 = next(t for t in turnos if t["hablante_id"] == "HABLANTE_1")
        t1 = next(t for t in turnos if t["hablante_id"] == "HABLANTE_2")
        # Cada hablante activo aproximadamente 1 s, sin solaparse
        assert t0["inicio"] < 0.5
        assert t0["fin"] < 1.5
        assert t1["inicio"] > 0.5
        assert t1["fin"] > 1.5


class TestSha256:
    def test_hash_es_hexadecimal_largo(self, tmp_path):
        ruta = tmp_path / "hola.txt"
        ruta.write_text("hola mundo")
        h = _sha256_archivo(ruta)
        assert len(h) == 64
        int(h, 16)  # válido hexadecimal


class TestGestionLLM:
    def test_no_para_llm_cuando_no_esta_en_puerto(self, monkeypatch):
        calls = {"parar": 0, "rearrancar": 0}

        def ocupado():
            return False

        def parar():
            calls["parar"] += 1

        def rearrancar():
            calls["rearrancar"] += 1

        monkeypatch.setattr("documenttoolkit.diarizar._puerto_ocupado", ocupado)
        monkeypatch.setattr("documenttoolkit.diarizar._parar_llm", parar)
        monkeypatch.setattr("documenttoolkit.diarizar._rearrancar_llm", rearrancar)
        monkeypatch.setattr("documenttoolkit.diarizar._cuda_disponible", lambda: True)
        monkeypatch.setattr("documenttoolkit.diarizar._vram_libre_mb", lambda: 8000)

        with _gestion_llm("cuda", parar_llm=False) as device:
            assert device == "cuda"

        assert calls["parar"] == 0
        assert calls["rearrancar"] == 0

    def test_para_y_rearranca_con_parar_llm(self, monkeypatch):
        calls = {"parar": 0, "rearrancar": 0}
        port_free = {"value": False}

        def ocupado():
            return not port_free["value"]

        def parar():
            calls["parar"] += 1
            port_free["value"] = True

        def rearrancar():
            calls["rearrancar"] += 1

        monkeypatch.setattr("documenttoolkit.diarizar._puerto_ocupado", ocupado)
        monkeypatch.setattr("documenttoolkit.diarizar._esperar_puerto_libre", lambda *a, **k: True)
        monkeypatch.setattr("documenttoolkit.diarizar._parar_llm", parar)
        monkeypatch.setattr("documenttoolkit.diarizar._rearrancar_llm", rearrancar)
        monkeypatch.setattr("documenttoolkit.diarizar._cuda_disponible", lambda: True)
        monkeypatch.setattr("documenttoolkit.diarizar._vram_libre_mb", lambda: 8000)

        with _gestion_llm("auto", parar_llm=True) as device:
            assert device == "cuda"

        assert calls["parar"] == 1
        assert calls["rearrancar"] == 1

    def test_rearranca_incluso_si_falla_el_bloque(self, monkeypatch):
        calls = {"parar": 0, "rearrancar": 0}

        monkeypatch.setattr("documenttoolkit.diarizar._puerto_ocupado", lambda: True)
        monkeypatch.setattr("documenttoolkit.diarizar._esperar_puerto_libre", lambda *a, **k: True)
        monkeypatch.setattr("documenttoolkit.diarizar._parar_llm", lambda: calls.__setitem__("parar", calls["parar"] + 1) or None)
        monkeypatch.setattr(
            "documenttoolkit.diarizar._rearrancar_llm",
            lambda: calls.__setitem__("rearrancar", calls["rearrancar"] + 1) or None,
        )
        monkeypatch.setattr("documenttoolkit.diarizar._cuda_disponible", lambda: True)
        monkeypatch.setattr("documenttoolkit.diarizar._vram_libre_mb", lambda: 8000)

        with pytest.raises(RuntimeError):
            with _gestion_llm("auto", parar_llm=True):
                raise RuntimeError("fallo interno")

        assert calls["parar"] == 1
        assert calls["rearrancar"] == 1

    def test_sin_terminal_sin_parar_llm_usa_cpu(self, monkeypatch):
        calls = {"parar": 0}

        monkeypatch.setattr("documenttoolkit.diarizar._puerto_ocupado", lambda: True)
        monkeypatch.setattr("documenttoolkit.diarizar._parar_llm", lambda: calls.__setitem__("parar", calls["parar"] + 1) or None)
        monkeypatch.setattr("documenttoolkit.diarizar._hay_terminal", lambda: False)
        monkeypatch.setattr("documenttoolkit.diarizar._cuda_disponible", lambda: True)

        with _gestion_llm("auto", parar_llm=False) as device:
            assert device == "cpu"

        assert calls["parar"] == 0


class TestDiarizarFlujo:
    def test_rechaza_documento_inexistente(self, tmp_path):
        from documenttoolkit.diarizar import diarizar
        codigo = diarizar("no_existe.wav", db_path=str(tmp_path / "test.db"))
        assert codigo == 1

    def test_rechaza_documento_pdf(self, tmp_path):
        db = DocumentDatabase(db_path=str(tmp_path / "test.db"))
        db.guardar_documento(
            ruta="/tmp/prueba.pdf",
            tipo_entrada="pdf",
            tipo_doc="PDF",
            texto="texto",
            num_chars=5,
            dominio="desconocido",
            datos_dict={},
        )
        from documenttoolkit.diarizar import diarizar
        codigo = diarizar("prueba.pdf", db_path=str(tmp_path / "test.db"))
        assert codigo == 1

    def test_guarda_metadatos_y_regenera_guion_desde_canales(self, tmp_path, monkeypatch):
        """Flujo completo usando detección de canales separados (sin pyannote)."""
        db_path = tmp_path / "test.db"
        db = DocumentDatabase(db_path=str(db_path))

        ruta_media = tmp_path / "grabacion.wav"
        ruta_media = _wav_separado(tmp_path)
        ruta_media.rename(tmp_path / "grabacion.wav")
        ruta_media = tmp_path / "grabacion.wav"

        doc_id = db.guardar_documento(
            ruta=str(ruta_media),
            tipo_entrada="audio",
            tipo_doc="TRANSCRIPCION_AUDIO",
            texto="hola adios",
            num_chars=10,
            dominio="desconocido",
            datos_dict={},
        )
        db.guardar_segmentos_asr(
            doc_id,
            [
                {
                    "inicio": 0.0,
                    "fin": 0.5,
                    "texto": "hola",
                    "palabras": [{"inicio": 0.0, "fin": 0.5, "texto": "hola"}],
                },
                {
                    "inicio": 1.0,
                    "fin": 1.5,
                    "texto": "adios",
                    "palabras": [{"inicio": 1.0, "fin": 1.5, "texto": "adios"}],
                },
            ],
        )

        # Evitar que toque el LLM real y forzar CPU.
        monkeypatch.setattr("documenttoolkit.diarizar._puerto_ocupado", lambda: False)
        monkeypatch.setattr("documenttoolkit.diarizar._cuda_disponible", lambda: False)

        from documenttoolkit.diarizar import diarizar
        codigo = diarizar("grabacion.wav", device="cpu", db_path=str(db_path))
        assert codigo == 0

        turnos = db.obtener_turnos_diarizacion(doc_id)
        assert len(turnos) == 2

        meta = db.obtener_metadatos_diarizacion(doc_id)
        assert meta is not None
        assert meta["modelo"] == "canal"
        assert meta["dispositivo"] == "cpu"
        assert meta["canales"] == 2
        assert meta["hash_original"] == _sha256_archivo(ruta_media)

        guion = db.obtener_turnos_guion(doc_id)
        assert len(guion) >= 1


# ============ Test de integración con pyannote ============

@pytest.mark.skipif(
    importlib.util.find_spec("pyannote") is None or not os.environ.get("HF_TOKEN"),
    reason="pyannote.audio no instalado o HF_TOKEN no definido",
)
class TestDiarizarPyannoteIntegracion:
    def test_diarizar_con_pyannote(self, tmp_path):
        from documenttoolkit.diarizar import _diarizar_con_pyannote

        ruta = _wav_separado(tmp_path)
        turnos, modelo = _diarizar_con_pyannote(ruta, "cpu", num_speakers=2)
        assert modelo == "pyannote/speaker-diarization-community-1"
        assert len(turnos) >= 1
        assert all("hablante_id" in t for t in turnos)
