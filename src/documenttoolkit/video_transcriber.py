"""
video_transcriber.py
Transcripción local de audio/video con faster-whisper (CPU).
No requiere GPU. Soporta: mp4, avi, mov, mkv, mp3, wav, m4a, ogg.
"""

from pathlib import Path
from typing import Optional
from faster_whisper import WhisperModel


class VideoTranscriber:
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

    def transcribir(self, ruta_video: Path) -> Optional[str]:
        ruta = Path(ruta_video)
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

    @staticmethod
    def _fmt(segundos: float) -> str:
        h = int(segundos // 3600)
        m = int((segundos % 3600) // 60)
        s = segundos % 60
        return f"{h:02d}:{m:02d}:{s:06.3f}"


def transcribir_y_guardar(ruta_video: Path, db, transcriber: Optional[VideoTranscriber] = None):
    """
    Función de conveniencia: transcribe y guarda en la misma base de datos
    que los PDFs, reutilizando clasificación y extracción.
    """
    from .classifier import classify_document
    from .enriched_extractor import extract_data_enriched

    if transcriber is None:
        transcriber = VideoTranscriber()

    texto = transcriber.transcribir(ruta_video)
    if not texto:
        return None

    # Mismo pipeline exacto que un PDF
    clase = classify_document(texto)
    datos = extract_data_enriched(texto, clase)

    db.guardar_documento(
        ruta=str(ruta_video.resolve()),
        tipo_entrada="video",
        tipo_doc=clase,
        texto=texto,
        num_chars=len(texto),
        dominio=datos.get("dominio", "desconocido"),
        datos_dict=datos
    )
    print(f"💾 Guardado en BD: {ruta_video.name} → {clase}")
    return datos