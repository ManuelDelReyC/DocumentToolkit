from pathlib import Path
from documenttoolkit.media_transcriber import (
    _es_video,
    _es_audio,
    _tipo_entrada,
    VIDEO_EXTENSIONS,
    AUDIO_EXTENSIONS,
)


def test_extensiones_soportadas():
    assert ".mp4" in VIDEO_EXTENSIONS
    assert ".mp3" in AUDIO_EXTENSIONS
    assert VIDEO_EXTENSIONS.isdisjoint(AUDIO_EXTENSIONS)


def test_clasificacion_por_extension():
    assert _es_video(Path("video.mp4")) is True
    assert _es_video(Path("video.mp3")) is False
    assert _es_audio(Path("audio.mp3")) is True
    assert _es_audio(Path("audio.mp4")) is False


def test_tipo_entrada():
    assert _tipo_entrada(Path("foo.mp4")) == "video"
    assert _tipo_entrada(Path("foo.wav")) == "audio"
    assert _tipo_entrada(Path("foo.xyz")) == "media"
