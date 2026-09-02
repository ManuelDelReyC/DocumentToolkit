"""
database.py
Capa de persistencia SQLite para DocumentToolkit.
No requiere instalación: sqlite3 es parte de la librería estándar de Python.
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import Optional, List, Dict


class DocumentDatabase:
    """
    Gestiona la base de datos SQLite de documentos procesados.
    """

    def __init__(self, db_path: str = "data/output/docs.db"):
        """
        :param db_path: Ruta al archivo .db. Por defecto en carpeta 'data/' del proyecto.
        """
        self.db_path = db_path
        # Aseguramos que la carpeta existe
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()

    def _connect(self):
        """Devuelve una conexión con row_factory para acceso tipo dict."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Permite acceder por nombre de columna
        return conn

    def _init_db(self):
        """Crea las tablas si no existen."""
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS documentos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ruta_original TEXT UNIQUE NOT NULL,
                    nombre_archivo TEXT NOT NULL,
                    tipo_entrada TEXT NOT NULL DEFAULT 'pdf',
                    tipo_documento TEXT,
                    texto_extraido TEXT,
                    num_caracteres INTEGER DEFAULT 0,
                    dominio TEXT,
                    datos_extraidos_json TEXT,
                    fecha_procesamiento TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    reprocesar BOOLEAN DEFAULT 0
                )
            """)
            conn.commit()

    # ============ OPERACIONES CRUD ============

    def guardar_documento(self, ruta: str, tipo_entrada: str, tipo_doc: str,
                          texto: str, num_chars: int, dominio: str,
                          datos_dict: Dict) -> int:
        """
        Inserta o actualiza un documento procesado.
        Si la ruta ya existe, actualiza los datos (útil si mejoras el extractor).
        Devuelve el ID del registro.
        """
        nombre = os.path.basename(ruta)
        datos_json = json.dumps(datos_dict, ensure_ascii=False, default=str)

        with self._connect() as conn:
            cursor = conn.execute("""
                INSERT INTO documentos (
                    ruta_original, nombre_archivo, tipo_entrada,
                    tipo_documento, texto_extraido, num_caracteres,
                    dominio, datos_extraidos_json, fecha_procesamiento, reprocesar
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                ON CONFLICT(ruta_original) DO UPDATE SET
                    tipo_documento = excluded.tipo_documento,
                    texto_extraido = excluded.texto_extraido,
                    num_caracteres = excluded.num_caracteres,
                    dominio = excluded.dominio,
                    datos_extraidos_json = excluded.datos_extraidos_json,
                    fecha_procesamiento = excluded.fecha_procesamiento,
                    reprocesar = 0
            """, (
                ruta, nombre, tipo_entrada,
                tipo_doc, texto, num_chars,
                dominio, datos_json, datetime.now().isoformat()
            ))
            conn.commit()
            return cursor.lastrowid

    def obtener_por_ruta(self, ruta: str) -> Optional[Dict]:
        """Devuelve un documento por su ruta original, o None si no existe."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM documentos WHERE ruta_original = ?",
                (ruta,)
            ).fetchone()
            if row is None:
                return None
            return self._row_to_dict(row)

    def listar_documentos(self, tipo_doc: Optional[str] = None,
                          dominio: Optional[str] = None,
                          limite: int = 100) -> List[Dict]:
        """
        Lista documentos. Permite filtrar por tipo o dominio.
        """
        query = "SELECT * FROM documentos WHERE 1=1"
        params = []

        if tipo_doc:
            query += " AND tipo_documento = ?"
            params.append(tipo_doc)
        if dominio:
            query += " AND dominio = ?"
            params.append(dominio)

        query += " ORDER BY fecha_procesamiento DESC LIMIT ?"
        params.append(limite)

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_dict(r) for r in rows]

    def buscar_por_texto(self, palabra_clave: str, limite: int = 20) -> List[Dict]:
        """
        Búsqueda simple LIKE en el texto extraído.
        Útil hasta que integres ChromaDB/FAISS.
        """
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM documentos WHERE texto_extraido LIKE ? "
                "ORDER BY fecha_procesamiento DESC LIMIT ?",
                (f"%{palabra_clave}%", limite)
            ).fetchall()
            return [self._row_to_dict(r) for r in rows]

    def documento_existe(self, ruta: str) -> bool:
        """True si el documento ya fue procesado y no está marcado para reprocesar."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM documentos WHERE ruta_original = ? AND reprocesar = 0",
                (ruta,)
            ).fetchone()
            return row is not None

    def marcar_para_reprocesar(self, ruta: str):
        """Fuerza a que un documento se vuelva a procesar en la siguiente ejecución."""
        with self._connect() as conn:
            conn.execute(
                "UPDATE documentos SET reprocesar = 1 WHERE ruta_original = ?",
                (ruta,)
            )
            conn.commit()

    def contar_documentos(self) -> int:
        """Total de documentos en la base."""
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) FROM documentos").fetchone()
            return row[0]

    # ============ UTILIDADES INTERNAS ============

    def _row_to_dict(self, row: sqlite3.Row) -> Dict:
        """Convierte una fila SQLite en diccionario Python, parseando el JSON."""
        d = dict(row)
        if d.get("datos_extraidos_json"):
            try:
                d["datos"] = json.loads(d["datos_extraidos_json"])
            except json.JSONDecodeError:
                d["datos"] = {}
        else:
            d["datos"] = {}
        return d