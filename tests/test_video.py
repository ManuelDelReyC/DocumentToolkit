from pathlib import Path
from documenttoolkit.database import DocumentDatabase
from documenttoolkit.media_transcriber import MediaTranscriber, transcribir_y_guardar
from documenttoolkit.config import DB_PATH, INPUT_VIDEO_DIR

VIDEO = INPUT_VIDEO_DIR / "tu_prueba.mp4"

db = DocumentDatabase(db_path=DB_PATH)
transcriber = MediaTranscriber()
transcribir_y_guardar(VIDEO, db, transcriber)
