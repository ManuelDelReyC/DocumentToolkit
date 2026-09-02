"""
config.py
Rutas centralizadas del proyecto. Resuelve rutas absolutas
independientemente de desde dónde se ejecute el script.
"""

from pathlib import Path

# Raíz del proyecto: src/documenttoolkit/config.py → sube 3 niveles → DocumentToolkit/
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Rutas clave
DB_PATH = str(PROJECT_ROOT / "data" / "output" / "docs.db")
INPUT_PDF_DIR = PROJECT_ROOT / "data" / "input"
INPUT_VIDEO_DIR = PROJECT_ROOT / "data" / "input" / "videos"