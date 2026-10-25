"""
media_transcriber.py
Transcripción local de audio y video con faster-whisper (CPU).
No requiere GPU.

Soporta video: mp4, avi, mov, mkv.
Soporta audio: mp3, wav, m4a, ogg, flac.
"""

from pathlib import Path
from typing import Optional, Set, List, Dict, Any
from faster_whisper import WhisperModel


VIDEO_EXTENSIONS: Set[str] = {".mp4", ".avi", ".mov", ".mkv"}
AUDIO_EXTENSIONS: Set[str] = {".mp3", ".wav", ".m4a", ".ogg", ".flac"}
MEDIA_EXTENSIONS: Set[str] = VIDEO_EXTENSIONS | AUDIO_EXTENSIONS


def _es_video(ruta: Path) -> bool:
    return ruta.suffix.lower() in VIDEO_EXTENSIONS


def _es_audio(ruta: Path) -> bool:
    return ruta.suffix.lower() in AUDIO_EXTENSIONS


def _tipo_entrada(ruta: Path) -> str:
    if _es_video(ruta):
        return "video"
    if _es_audio(ruta):
        return "audio"
    return "media"


class MediaTranscriber:
    """
    Transcriptor local optimizado para CPU.
    Modelos: "base" (~500MB, rápido), "small" (~900MB, equilibrado), "medium" (~1.5GB, lento).
    """

    def __init__(self, model_size: str = "medium"):
        print(f"🔄 Cargando Whisper '{model_size}' en CPU (descarga inicial ~900 MB)...")
        self.model = WhisperModel(
            model_size,
            device="cpu",
            compute_type="int8"
        )
        print("✅ Whisper listo.")

    def transcribir(self, ruta_media: Path) -> Optional[str]:
        ruta = Path(ruta_media)
        if not ruta.exists():
            print(f"❌ No encontrado: {ruta}")
            return None

        print(f"🎙️  Transcribiendo: {ruta.name}")
        try:
            segments, info = self.model.transcribe(
                str(ruta),
                language="es",
                beam_size=5,
                condition_on_previous_text=True
            )
            print(f"   Idioma detectado: {info.language} (confianza: {info.language_probability:.2f})")

            lineas = []
            for seg in segments:
                t0 = self._fmt(seg.start)
                t1 = self._fmt(seg.end)
                lineas.append(f"[{t0} --> {t1}]  {seg.text.strip()}")

            texto = "\n".join(lineas)
            print(f"   Segmentos: {len(lineas)} | Duración: {self._fmt(info.duration)}")
            return texto

        except Exception as e:
            print(f"❌ Error: {e}")
            return None

    def transcribir_detallado(self, ruta_media: Path) -> Optional[List[Dict[str, Any]]]:
        """
        Transcribe devolviendo segmentos con las palabras y sus tiempos.
        No modifica el texto reconocido; es la base para la guionización.
        """
        ruta = Path(ruta_media)
        if not ruta.exists():
            print(f"❌ No encontrado: {ruta}")
            return None

        print(f"🎙️  Transcribiendo con tiempos por palabra: {ruta.name}")
        try:
            segments, info = self.model.transcribe(
                str(ruta),
                language="es",
                beam_size=5,
                condition_on_previous_text=True,
                word_timestamps=True,
            )
            print(f"   Idioma detectado: {info.language} (confianza: {info.language_probability:.2f})")

            resultado = []
            for seg in segments:
                palabras = []
                for w in getattr(seg, "words", []):
                    palabras.append({
                        "inicio": w.start,
                        "fin": w.end,
                        "texto": w.word.strip(),
                    })
                resultado.append({
                    "inicio": seg.start,
                    "fin": seg.end,
                    "texto": seg.text.strip(),
                    "palabras": palabras,
                })

            print(f"   Segmentos: {len(resultado)} | Duración: {self._fmt(info.duration)}")
            return resultado

        except Exception as e:
            print(f"❌ Error: {e}")
            return None

    @staticmethod
    def _fmt(segundos: float) -> str:
        h = int(segundos // 3600)
        m = int((segundos % 3600) // 60)
        s = segundos % 60
        return f"{h:02d}:{m:02d}:{s:06.3f}"


def transcribir_y_guardar(ruta_media: Path, db, transcriber: Optional[MediaTranscriber] = None):
    """
    Función de conveniencia: transcribe y guarda en la misma base de datos
    que los PDFs, reutilizando clasificación y extracción.
    """
    from .classifier import classify_document
    from .enriched_extractor import extract_data_enriched

    ruta = Path(ruta_media)
    tipo_entrada = _tipo_entrada(ruta)
    tipo_doc = "TRANSCRIPCION_VIDEO" if tipo_entrada == "video" else "TRANSCRIPCION_AUDIO"

    if transcriber is None:
        transcriber = MediaTranscriber()

    detalle = transcriber.transcribir_detallado(ruta)
    if not detalle:
        return None

    texto = "\n".join(
        f"[{transcriber._fmt(seg['inicio'])} --> {transcriber._fmt(seg['fin'])}]  {seg['texto']}"
        for seg in detalle
    )

    # Mismo pipeline exacto que un PDF
    clase = classify_document(texto)
    datos = extract_data_enriched(texto, clase)

    documento_id = db.guardar_documento(
        ruta=str(ruta.resolve()),
        tipo_entrada=tipo_entrada,
        tipo_doc=tipo_doc,
        texto=texto,
        num_chars=len(texto),
        dominio=datos.get("dominio", "desconocido"),
        datos_dict=datos
    )
    db.guardar_segmentos_asr(documento_id, detalle)
    print(f"💾 Guardado en BD: {ruta.name} → {clase}")
    return datos
