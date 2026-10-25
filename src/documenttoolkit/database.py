"""
database.py
Capa de persistencia SQLite para DocumentToolkit.
No requiere instalación: sqlite3 es parte de la librería estándar de Python.
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import Optional, List, Dict, Any

from .config import DB_PATH


class DocumentDatabase:
    """
    Gestiona la base de datos SQLite de documentos procesados.
    """

    def __init__(self, db_path: str = DB_PATH):
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
        conn.execute("PRAGMA foreign_keys = ON")
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

            # Tablas hijas para la fase de diarización/guionización.
            # Permiten conservar la transcripción cruda y reconstruir el guion
            # sin repetir el costoso proceso de Whisper ni pyannote.
            conn.execute("""
                CREATE TABLE IF NOT EXISTS segmentos_asr (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    documento_id INTEGER NOT NULL,
                    inicio REAL NOT NULL,
                    fin REAL NOT NULL,
                    texto TEXT NOT NULL,
                    palabras_json TEXT,
                    FOREIGN KEY(documento_id) REFERENCES documentos(id)
                        ON DELETE CASCADE
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS turnos_diarizacion (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    documento_id INTEGER NOT NULL,
                    hablante_id TEXT NOT NULL,
                    inicio REAL NOT NULL,
                    fin REAL NOT NULL,
                    FOREIGN KEY(documento_id) REFERENCES documentos(id)
                        ON DELETE CASCADE
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS hablantes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    documento_id INTEGER NOT NULL,
                    hablante_id TEXT NOT NULL,
                    etiqueta TEXT,
                    UNIQUE(documento_id, hablante_id),
                    FOREIGN KEY(documento_id) REFERENCES documentos(id)
                        ON DELETE CASCADE
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS turnos_guion (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    documento_id INTEGER NOT NULL,
                    hablante TEXT NOT NULL,
                    inicio REAL NOT NULL,
                    fin REAL NOT NULL,
                    texto TEXT NOT NULL,
                    confianza_media REAL DEFAULT 0,
                    es_solapamiento BOOLEAN DEFAULT 0,
                    requiere_revision BOOLEAN DEFAULT 0,
                    hablantes_solapados_json TEXT,
                    FOREIGN KEY(documento_id) REFERENCES documentos(id)
                        ON DELETE CASCADE
                )
            """)
            # Migración suave para bases creadas antes de esta columna.
            try:
                conn.execute(
                    "ALTER TABLE turnos_guion ADD COLUMN hablantes_solapados_json TEXT"
                )
            except sqlite3.OperationalError:
                pass
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

    # ============ DIARIZACIÓN / GUION ============

    def guardar_segmentos_asr(self, documento_id: int,
                              segmentos: List[Dict[str, Any]]) -> None:
        """
        Guarda los segmentos de Whisper con las palabras y sus tiempos.
        Cada segmento es un dict con: inicio, fin, texto, palabras (lista opcional).
        """
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM segmentos_asr WHERE documento_id = ?",
                (documento_id,)
            )
            for seg in segmentos:
                palabras_json = json.dumps(
                    seg.get("palabras", []), ensure_ascii=False, default=str
                )
                conn.execute("""
                    INSERT INTO segmentos_asr
                        (documento_id, inicio, fin, texto, palabras_json)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    documento_id,
                    float(seg["inicio"]),
                    float(seg["fin"]),
                    str(seg["texto"]),
                    palabras_json,
                ))
            conn.commit()

    def obtener_segmentos_asr(self, documento_id: int) -> List[Dict[str, Any]]:
        """Devuelve los segmentos ASR de un documento, con palabras parseadas."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM segmentos_asr WHERE documento_id = ? ORDER BY inicio",
                (documento_id,)
            ).fetchall()
            resultado = []
            for r in rows:
                d = dict(r)
                try:
                    d["palabras"] = json.loads(d["palabras_json"] or "[]")
                except json.JSONDecodeError:
                    d["palabras"] = []
                resultado.append(d)
            return resultado

    def guardar_turnos_diarizacion(self, documento_id: int,
                                   turnos: List[Dict[str, Any]]) -> None:
        """
        Guarda los turnos de voz crudos. Cada turno: hablante_id, inicio, fin.
        """
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM turnos_diarizacion WHERE documento_id = ?",
                (documento_id,)
            )
            for t in turnos:
                conn.execute("""
                    INSERT INTO turnos_diarizacion
                        (documento_id, hablante_id, inicio, fin)
                    VALUES (?, ?, ?, ?)
                """, (
                    documento_id,
                    str(t["hablante_id"]),
                    float(t["inicio"]),
                    float(t["fin"]),
                ))
            conn.commit()

    def obtener_turnos_diarizacion(self, documento_id: int) -> List[Dict[str, Any]]:
        """Devuelve los turnos de diarización de un documento."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM turnos_diarizacion WHERE documento_id = ? ORDER BY inicio",
                (documento_id,)
            ).fetchall()
            return [dict(r) for r in rows]

    def guardar_hablante(self, documento_id: int, hablante_id: str,
                         etiqueta: Optional[str]) -> None:
        """
        Asocia una etiqueta revisada a un identificador de voz.
        Si etiqueta es None, se borra la asignación.
        """
        with self._connect() as conn:
            if etiqueta is None or etiqueta.strip() == "":
                conn.execute("""
                    DELETE FROM hablantes
                    WHERE documento_id = ? AND hablante_id = ?
                """, (documento_id, hablante_id))
            else:
                conn.execute("""
                    INSERT INTO hablantes (documento_id, hablante_id, etiqueta)
                    VALUES (?, ?, ?)
                    ON CONFLICT(documento_id, hablante_id) DO UPDATE SET
                        etiqueta = excluded.etiqueta
                """, (documento_id, hablante_id, etiqueta.strip()))
            conn.commit()

    def obtener_hablantes(self, documento_id: int) -> Dict[str, str]:
        """Devuelve un dict {hablante_id: etiqueta} para un documento."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT hablante_id, etiqueta FROM hablantes WHERE documento_id = ?",
                (documento_id,)
            ).fetchall()
            return {r["hablante_id"]: r["etiqueta"] for r in rows}

    def guardar_turnos_guion(self, documento_id: int,
                             turnos: List[Dict[str, Any]]) -> None:
        """
        Guarda el guion ya alineado. Cada turno: hablante, inicio, fin,
        texto, confianza_media, es_solapamiento, requiere_revision,
        hablantes_solapados (lista).
        """
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM turnos_guion WHERE documento_id = ?",
                (documento_id,)
            )
            for t in turnos:
                solapados_json = json.dumps(
                    t.get("hablantes_solapados", []),
                    ensure_ascii=False,
                    default=str,
                )
                conn.execute("""
                    INSERT INTO turnos_guion
                        (documento_id, hablante, inicio, fin, texto,
                         confianza_media, es_solapamiento, requiere_revision,
                         hablantes_solapados_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    documento_id,
                    str(t["hablante"]),
                    float(t["inicio"]),
                    float(t["fin"]),
                    str(t["texto"]),
                    float(t.get("confianza_media", 0.0)),
                    bool(t.get("es_solapamiento", False)),
                    bool(t.get("requiere_revision", False)),
                    solapados_json,
                ))
            conn.commit()

    def obtener_turnos_guion(self, documento_id: int) -> List[Dict[str, Any]]:
        """Devuelve los turnos del guion de un documento."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM turnos_guion WHERE documento_id = ? ORDER BY inicio",
                (documento_id,)
            ).fetchall()
            resultado = []
            for r in rows:
                d = dict(r)
                try:
                    d["hablantes_solapados"] = json.loads(
                        d.get("hablantes_solapados_json") or "[]"
                    )
                except json.JSONDecodeError:
                    d["hablantes_solapados"] = []
                resultado.append(d)
            return resultado

    def eliminar_datos_diarizacion(self, documento_id: int) -> None:
        """Borra segmentos ASR, turnos de diarización, hablantes y guion de un documento."""
        with self._connect() as conn:
            for tabla in (
                "segmentos_asr",
                "turnos_diarizacion",
                "hablantes",
                "turnos_guion",
            ):
                conn.execute(
                    f"DELETE FROM {tabla} WHERE documento_id = ?",
                    (documento_id,)
                )
            conn.commit()

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
