"""
video_transcriber.py
Wrapper de compatibilidad hacia media_transcriber.py.

Este módulo existe por compatibilidad con importaciones antiguas.
Para código nuevo usa documenttoolkit.media_transcriber.
"""

from .media_transcriber import (
    MediaTranscriber as VideoTranscriber,
    transcribir_y_guardar,
    VIDEO_EXTENSIONS,
    AUDIO_EXTENSIONS,
    MEDIA_EXTENSIONS,
)

__all__ = [
    "VideoTranscriber",
    "transcribir_y_guardar",
    "VIDEO_EXTENSIONS",
    "AUDIO_EXTENSIONS",
    "MEDIA_EXTENSIONS",
]
