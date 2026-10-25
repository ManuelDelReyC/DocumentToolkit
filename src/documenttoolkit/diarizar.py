"""
diarizar.py
Fase 2 de la guionización: motor de diarización de audio/video.

Ejecutable como script:
    python -m documenttoolkit.diarizar RUTA_O_NOMBRE [--hablantes N] [--device cuda|cpu|auto] [--parar-llm]

No importa pyannote.audio al cargar el módulo; se importa solo dentro de la
función que diariza. Whisper se libera antes de cargar pyannote.
"""

import argparse
import contextlib
import hashlib
import os
import signal
import socket
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .config import DB_PATH
from .database import DocumentDatabase
from . import guion as guion_mod
from .media_transcriber import MediaTranscriber


LLM_HOST = "127.0.0.1"
LLM_PORT = 8080
PYANNOTE_PIPELINE_DEFAULT = "pyannote/speaker-diarization-community-1"
VRAM_MINIMA_MB = 4096


def _buscar_documento(db: DocumentDatabase, ruta_o_nombre: str) -> Optional[Dict[str, Any]]:
    """Busca un documento por ruta exacta o por prefijo de nombre."""
    doc = db.obtener_por_ruta(ruta_o_nombre)
    if doc:
        return doc
    docs = db.listar_documentos(limite=9999)
    for d in docs:
        if d["nombre_archivo"] == ruta_o_nombre or d["nombre_archivo"].startswith(ruta_o_nombre):
            return d
    return None


def _sha256_archivo(ruta: Path) -> str:
    """Devuelve el hash SHA-256 de un archivo."""
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(8192), b""):
            h.update(bloque)
    return h.hexdigest()


def _extraer_wav(ruta_media: Path, wav_salida: Path) -> None:
    """Extrae el audio a WAV mono 16 kHz PCM con ffmpeg."""
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(ruta_media),
        "-ac",
        "1",
        "-ar",
        "16000",
        "-sample_fmt",
        "s16",
        "-vn",
        str(wav_salida),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def _ejecutar_ffprobe(*args: str) -> str:
    """Ejecuta ffprobe y devuelve la salida como texto."""
    cmd = ["ffprobe", "-v", "error"] + list(args)
    return subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode().strip()


def _obtener_duracion(ruta: Path) -> float:
    """Duración en segundos según ffprobe."""
    salida = _ejecutar_ffprobe(
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(ruta),
    )
    return float(salida)


def _obtener_canales(ruta: Path) -> int:
    """Número de canales de audio según ffprobe."""
    salida = _ejecutar_ffprobe(
        "-select_streams", "a:0",
        "-show_entries", "stream=channels",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(ruta),
    )
    return int(salida)


def _puerto_ocupado(host: str = LLM_HOST, puerto: int = LLM_PORT, timeout: float = 1.0) -> bool:
    """True si hay algo escuchando en el puerto."""
    try:
        with socket.create_connection((host, puerto), timeout=timeout):
            return True
    except OSError:
        return False


def _esperar_puerto_libre(host: str = LLM_HOST, puerto: int = LLM_PORT, timeout: int = 60) -> bool:
    """Espera hasta que el puerto quede libre."""
    for _ in range(timeout):
        if not _puerto_ocupado(host, puerto):
            return True
        time.sleep(1)
    return False


def _esperar_puerto_ocupado(host: str = LLM_HOST, puerto: int = LLM_PORT, timeout: int = 120) -> bool:
    """Espera hasta que el puerto esté ocupado."""
    for _ in range(timeout):
        if _puerto_ocupado(host, puerto):
            return True
        time.sleep(1)
    return False


def _hay_terminal() -> bool:
    """True si stdin y stdout están conectados a una terminal interactiva."""
    return sys.stdin.isatty() and sys.stdout.isatty()


def _parar_llm() -> None:
    """Envía SIGTERM a los procesos llama-server."""
    try:
        pids = (
            subprocess.check_output(["pgrep", "-f", "llama-server"])
            .decode()
            .strip()
            .splitlines()
        )
    except subprocess.CalledProcessError:
        return
    for pid_str in pids:
        try:
            os.kill(int(pid_str), signal.SIGTERM)
        except ProcessLookupError:
            pass


def _rearrancar_llm() -> None:
    """Relanza el servidor LLM con scripts/start_llm_server.sh."""
    script = Path(__file__).resolve().parent.parent.parent / "scripts" / "start_llm_server.sh"
    if not script.exists():
        print(f"⚠️  No se encuentra {script}")
        print(f"   Relanza manualmente el servidor LLM para volver a usar main.")
        return
    print("🚀 Rearrancando servidor LLM...")
    try:
        subprocess.Popen(
            [str(script)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except Exception as e:
        print(f"⚠️  Error al rearrancar el servidor LLM: {e}")
        print(f"   Comando: {script}")
        return

    if _esperar_puerto_ocupado(timeout=120):
        print("✅ Servidor LLM escuchando de nuevo en http://localhost:8080")
    else:
        print("⚠️  El servidor LLM no respondió en el puerto 8080 tras rearrancarlo.")
        print(f"   Comando: {script}")
        print("   No ejecutes main ni llames al LLM hasta que lo arranques manualmente.")


def _cuda_disponible() -> bool:
    """True si nvidia-smi está disponible y hay al menos una GPU."""
    try:
        subprocess.check_output(["nvidia-smi"], stderr=subprocess.DEVNULL)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def _vram_libre_mb() -> int:
    """Megabytes de VRAM libre en la GPU 0 según nvidia-smi."""
    try:
        salida = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
            stderr=subprocess.DEVNULL,
        )
        return int(salida.decode().strip().splitlines()[0])
    except (subprocess.CalledProcessError, ValueError, FileNotFoundError):
        return 0


@contextlib.contextmanager
def _gestion_llm(dispositivo_solicitado: str, parar_llm: bool):
    """
    Decide si hay que parar el servidor LLM para liberar la GPU y lo rearranca
    en finally si lo paramos.

    Yields: dispositivo efectivo ("cuda" o "cpu").
    """
    llm_running = _puerto_ocupado()
    lo_paramos = False
    dispositivo = dispositivo_solicitado

    if dispositivo == "auto":
        if not _cuda_disponible():
            dispositivo = "cpu"
        elif llm_running:
            if parar_llm:
                lo_paramos = True
                dispositivo = "cuda"
            elif _hay_terminal():
                try:
                    resp = input(
                        "El servidor LLM ocupa la GPU. "
                        "¿Pararlo durante la diarización y volver a arrancarlo al terminar? [S/n] "
                    ).strip().lower()
                except EOFError:
                    resp = "n"
                if resp in ("", "s", "si", "yes"):
                    lo_paramos = True
                    dispositivo = "cuda"
                else:
                    print("ℹ️  Se continúa en CPU sin tocar el servidor LLM.")
                    dispositivo = "cpu"
            else:
                print(
                    "ℹ️  Servidor LLM en GPU, sin terminal interactivo y sin --parar-llm. "
                    "Se continúa en CPU."
                )
                dispositivo = "cpu"
        else:
            dispositivo = "cuda"
    elif dispositivo == "cuda" and llm_running:
        if parar_llm:
            lo_paramos = True
            dispositivo = "cuda"
        elif _hay_terminal():
            try:
                resp = input(
                    "El servidor LLM ocupa la GPU. "
                    "¿Pararlo durante la diarización y volver a arrancarlo al terminar? [S/n] "
                ).strip().lower()
            except EOFError:
                resp = "n"
            if resp in ("", "s", "si", "yes"):
                lo_paramos = True
                dispositivo = "cuda"
            else:
                print("ℹ️  Se continúa en CPU sin tocar el servidor LLM.")
                dispositivo = "cpu"
        else:
            raise SystemExit(
                "Se pidió --device cuda pero el servidor LLM ocupa la GPU. "
                "Usa --parar-llm o detén el LLM manualmente."
            )

    if lo_paramos:
        print("🛑 Deteniendo servidor LLM...")
        _parar_llm()
        if not _esperar_puerto_libre(timeout=60):
            raise RuntimeError("No se pudo liberar el puerto 8080 tras parar el LLM")

    if dispositivo == "cuda":
        vram = _vram_libre_mb()
        if vram < VRAM_MINIMA_MB:
            print(
                f"⚠️  Solo hay {vram} MB de VRAM libre (mínimo {VRAM_MINIMA_MB} MB). "
                "La diarización será lenta en CPU."
            )
            dispositivo = "cpu"

    try:
        yield dispositivo
    finally:
        if lo_paramos:
            _rearrancar_llm()


def _leer_audio_numpy(ruta: Path, canales: Optional[int] = None) -> Optional[np.ndarray]:
    """Lee un archivo de audio como array numpy [muestras, canales] float32."""
    if canales is None:
        canales = _obtener_canales(ruta)
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(ruta),
        "-ac",
        str(canales),
        "-ar",
        "16000",
        "-sample_fmt",
        "flt",
        "-vn",
        "-f",
        "f32le",
        "-",
    ]
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        return None
    muestras = np.frombuffer(out, dtype=np.float32)
    if len(muestras) % canales != 0:
        return None
    return muestras.reshape(-1, canales)


def _canales_estan_separados(ruta_media: Path, umbral_dominancia: float = 0.80) -> bool:
    """
    Heurística de energía: devuelve True si en la mayoría de las ventanas
    temporales un canal concentra la mayor parte de la energía total, lo que
    indica que cada canal es un hablante diferente.
    """
    canales = _obtener_canales(ruta_media)
    if canales < 2:
        return False
    audio = _leer_audio_numpy(ruta_media, canales)
    if audio is None or len(audio) == 0:
        return False

    ventana = int(16000 * 0.1)  # 100 ms
    n_ventanas = len(audio) // ventana
    if n_ventanas == 0:
        return False

    frames = audio[: n_ventanas * ventana].reshape(n_ventanas, ventana, canales)
    energias = np.sum(frames ** 2, axis=1)

    dominantes = 0
    for i in range(n_ventanas):
        e = energias[i]
        total = float(np.sum(e))
        if total == 0:
            continue
        dom = float(np.max(e)) / total
        if dom > umbral_dominancia:
            dominantes += 1

    return (dominantes / n_ventanas) > 0.7


def _canales_a_turnos(ruta_media: Path) -> List[Dict[str, Any]]:
    """
    Convierte cada canal en un hablante y segmenta por energía.
    Devuelve turnos {hablante_id, inicio, fin}.
    """
    canales = _obtener_canales(ruta_media)
    audio = _leer_audio_numpy(ruta_media, canales)
    if audio is None:
        return []

    duracion_ventana = 0.2  # s
    ventana = int(16000 * duracion_ventana)
    n_ventanas = len(audio) // ventana
    if n_ventanas == 0:
        return []

    frames = audio[: n_ventanas * ventana].reshape(n_ventanas, ventana, canales)
    energias = np.sum(frames ** 2, axis=1)
    max_e = np.max(energias, axis=0)
    max_e[max_e == 0] = 1.0
    umbrales = max_e * 0.05

    turnos: List[Dict[str, Any]] = []
    for c in range(canales):
        activo = False
        inicio = 0.0
        for i in range(n_ventanas):
            if energias[i, c] > umbrales[c]:
                if not activo:
                    activo = True
                    inicio = i * duracion_ventana
            else:
                if activo:
                    turnos.append(
                        {
                            "hablante_id": f"HABLANTE_{c + 1}",
                            "inicio": inicio,
                            "fin": i * duracion_ventana,
                        }
                    )
                    activo = False
        if activo:
            turnos.append(
                {
                    "hablante_id": f"HABLANTE_{c + 1}",
                    "inicio": inicio,
                    "fin": n_ventanas * duracion_ventana,
                }
            )

    return sorted(turnos, key=lambda t: t["inicio"])


def _anotacion_a_turnos(anotacion: Any) -> List[Dict[str, Any]]:
    """
    Convierte la salida de pyannote.audio en turnos {hablante_id, inicio, fin}.
    Soporta la API 4.x (output.speaker_diarization) y la API 3.x
    (anotacion.itertracks(yield_label=True)).
    """
    turnos: List[Dict[str, Any]] = []

    if hasattr(anotacion, "speaker_diarization"):
        for turn, speaker in anotacion.speaker_diarization:
            turnos.append(
                {
                    "hablante_id": str(speaker),
                    "inicio": float(turn.start),
                    "fin": float(turn.end),
                }
            )
    else:
        for turn, _track, speaker in anotacion.itertracks(yield_label=True):
            turnos.append(
                {
                    "hablante_id": str(speaker),
                    "inicio": float(turn.start),
                    "fin": float(turn.end),
                }
            )

    return sorted(turnos, key=lambda t: t["inicio"])


def _diarizar_con_pyannote(
    wav_path: Path, device: str, num_speakers: Optional[int]
) -> Tuple[List[Dict[str, Any]], str]:
    """
    Diariza con pyannote.audio. Devuelve (turnos, nombre_modelo).
    pyannote.audio se importa dentro de esta función.
    """
    try:
        from pyannote.audio import Pipeline
    except ImportError as e:
        raise SystemExit(
            f"❌ pyannote.audio no está instalado. "
            f"Instala el extra [diarizacion]: pip install -e '.[diarizacion]' ({e})"
        )

    token = os.environ.get("HF_TOKEN")
    if not token:
        raise SystemExit(
            "❌ HF_TOKEN no definido. "
            "Necesitas un token de Hugging Face con acceso aceptado a "
            "pyannote/speaker-diarization-community-1 (o el pipeline configurado)."
        )

    pipeline_name = os.environ.get("PYANNOTE_PIPELINE", PYANNOTE_PIPELINE_DEFAULT)
    print(f"🔄 Cargando pyannote ({pipeline_name}) en {device}...")

    import torch

    pipeline = Pipeline.from_pretrained(pipeline_name, token=token)
    if device == "cuda":
        pipeline.to(torch.device("cuda"))

    kwargs: Dict[str, Any] = {}
    if num_speakers is not None:
        kwargs["num_speakers"] = num_speakers

    print(f"🎙️  Diarizando: {wav_path.name}")
    output = pipeline(str(wav_path), **kwargs)
    turnos = _anotacion_a_turnos(output)
    return turnos, pipeline_name


def _metadatos_guion_diarizacion(
    doc: Dict[str, Any], db: DocumentDatabase
) -> Dict[str, str]:
    """Construye los metadatos que aparecen en la cabecera del guion."""
    meta: Dict[str, str] = {
        "Archivo": doc["nombre_archivo"],
        "Ruta": doc["ruta_original"],
        "Tipo": doc.get("tipo_documento") or "desconocido",
        "Procesado": doc.get("fecha_procesamiento") or "desconocido",
    }
    md = db.obtener_metadatos_diarizacion(doc["id"])
    if md:
        meta["Modelo diarizacion"] = md.get("modelo") or "desconocido"
        meta["Dispositivo"] = md.get("dispositivo") or "desconocido"
        meta["Hablantes estimados"] = str(md.get("hablantes_estimados") or "desconocido")
        if md.get("hablantes_solicitados"):
            meta["Hablantes solicitados"] = str(md["hablantes_solicitados"])
        meta["Hash SHA-256"] = md.get("hash_original") or "desconocido"
        meta["Duracion"] = f"{md.get('duracion', 0):.3f} s"
        meta["Canales"] = str(md.get("canales") or "desconocido")
        meta["Fecha diarizacion"] = md.get("fecha") or "desconocido"
    return meta


def diarizar(
    ruta_o_nombre: str,
    hablantes: Optional[int] = None,
    device: str = "auto",
    parar_llm: bool = False,
    db_path: str = DB_PATH,
) -> int:
    """
    Punto de entrada principal de la fase 2 de guionización.
    Devuelve 0 si tuvo éxito, otro código en caso contrario.
    """
    db = DocumentDatabase(db_path=db_path)
    doc = _buscar_documento(db, ruta_o_nombre)
    if not doc:
        print(
            f"❌ Documento no encontrado: {ruta_o_nombre}\n"
            f"   Ejecuta primero python -m documenttoolkit.main para procesar el archivo."
        )
        return 1

    if doc.get("tipo_entrada") not in ("audio", "video"):
        print(
            f"❌ {doc['nombre_archivo']} no es un archivo de audio/video "
            f"(tipo_entrada={doc.get('tipo_entrada')})."
        )
        return 1

    ruta_media = Path(doc["ruta_original"])
    if not ruta_media.exists():
        print(f"❌ Archivo original no encontrado: {ruta_media}")
        return 1

    segmentos = db.obtener_segmentos_asr(doc["id"])
    if not segmentos:
        print("🎙️  No hay segmentos ASR guardados; transcribiendo con Whisper...")
        transcriber = MediaTranscriber()
        segmentos = transcriber.transcribir_detallado(ruta_media)
        del transcriber
        if not segmentos:
            print("❌ La transcripción con Whisper no devolvió segmentos.")
            return 1
        db.guardar_segmentos_asr(doc["id"], segmentos)
        print("💾 Segmentos ASR guardados.")

    wav_path = Path(tempfile.gettempdir()) / f"diarizar_{doc['id']}_{ruta_media.stem}.wav"
    try:
        _extraer_wav(ruta_media, wav_path)
        duracion = _obtener_duracion(wav_path)
        canales = _obtener_canales(ruta_media)
        hash_original = _sha256_archivo(ruta_media)

        with _gestion_llm(device, parar_llm) as dispositivo_efectivo:
            if canales >= 2 and _canales_estan_separados(ruta_media):
                print(f"🔊 {canales} canales claramente separados; cada canal = hablante.")
                turnos = _canales_a_turnos(ruta_media)
                modelo_usado = "canal"
            else:
                turnos, modelo_usado = _diarizar_con_pyannote(
                    wav_path, dispositivo_efectivo, hablantes
                )

        hablantes_estimados = len({t["hablante_id"] for t in turnos})
        if hablantes is None:
            print(
                f"ℹ️  Número de hablantes estimado por el modelo: {hablantes_estimados}"
            )

        db.guardar_turnos_diarizacion(doc["id"], turnos)
        db.guardar_metadatos_diarizacion(
            doc["id"],
            {
                "modelo": modelo_usado,
                "dispositivo": dispositivo_efectivo,
                "hablantes_solicitados": hablantes,
                "hablantes_estimados": hablantes_estimados,
                "hash_original": hash_original,
                "duracion": duracion,
                "canales": canales,
                "fecha": datetime.now().isoformat(),
            },
        )

        turnos_guion = guion_mod.construir_guion(segmentos, turnos)
        db.guardar_turnos_guion(doc["id"], guion_mod.turnos_guion_a_db(turnos_guion))

        mapa_etiquetas = db.obtener_hablantes(doc["id"])
        metadatos = _metadatos_guion_diarizacion(doc, db)
        texto = guion_mod.renderizar_guion(
            turnos_guion, mapa_etiquetas=mapa_etiquetas, metadatos=metadatos
        )
        print(texto)
        return 0
    except SystemExit as e:
        print(str(e))
        return 1
    except Exception as e:
        print(f"❌ Error durante la diarización: {e}")
        return 1
    finally:
        if wav_path.exists():
            wav_path.unlink()


def main():
    parser = argparse.ArgumentParser(
        description="Fase 2 de guionización: diarización de audio/video"
    )
    parser.add_argument("ruta_o_nombre", help="Ruta o nombre del archivo ya procesado")
    parser.add_argument(
        "--hablantes",
        type=int,
        default=None,
        help="Número exacto de hablantes (si no se indica, el modelo lo estima)",
    )
    parser.add_argument(
        "--device",
        choices=["cuda", "cpu", "auto"],
        default="auto",
        help="Dispositivo para pyannote (default: auto)",
    )
    parser.add_argument(
        "--parar-llm",
        action="store_true",
        help="Parar el servidor LLM en GPU aunque no haya terminal interactivo",
    )
    parser.add_argument(
        "--db",
        default=DB_PATH,
        help="Ruta a la base de datos SQLite (default: data/output/docs.db)",
    )
    args = parser.parse_args()

    return diarizar(
        ruta_o_nombre=args.ruta_o_nombre,
        hablantes=args.hablantes,
        device=args.device,
        parar_llm=args.parar_llm,
        db_path=args.db,
    )


if __name__ == "__main__":
    sys.exit(main())
