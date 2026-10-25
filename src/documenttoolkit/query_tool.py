"""
query_tool.py
Herramienta de consulta sobre la base de datos SQLite.
Ejecutable como script o importable como módulo.
"""

import json
import argparse
from pathlib import Path
from typing import Optional, List
from .database import DocumentDatabase
from .config import DB_PATH
from . import guion as guion_mod
from .guion import TurnoGuion


def _icono_entrada(tipo_entrada: str) -> str:
    """Devuelve un icono representativo según el tipo de entrada."""
    return {
        "pdf": "📄",
        "video": "🎬",
        "audio": "🎵",
    }.get(tipo_entrada, "📁")


def mostrar_documento(doc: dict, completo: bool = False):
    """Imprime un documento de forma legible."""
    print(f"\n{'='*60}")
    print(f"📄 {doc['nombre_archivo']}")
    print(f"{'='*60}")
    print(f"   Tipo:        {doc['tipo_documento']}")
    print(f"   Dominio:     {doc.get('dominio', 'N/A')}")
    print(f"   Entrada:     {doc['tipo_entrada']}")
    print(f"   Caracteres:  {doc['num_caracteres']}")
    metodo = doc.get('datos', {}).get('metodo_extraccion')
    if metodo:
        print(f"   Extracción:  {metodo}")
        if doc['datos'].get('paginas_ocr'):
            print(f"   Págs. OCR:   {doc['datos']['paginas_ocr']}")
    print(f"   Procesado:   {doc['fecha_procesamiento']}")

    datos = doc.get("datos", {})
    
    # Campos específicos por dominio
    if doc.get("dominio") == "bancario":
        print(f"   IBAN:        {datos.get('IBAN', 'N/A')}")
        print(f"   IBAN Válido: {datos.get('IBAN_Valido', 'N/A')}")
        print(f"   Titular:     {datos.get('Titular', 'N/A') or 'N/A'}")
        if datos.get("importes"):
            print(f"   Importes:    {datos['importes']}")
    elif doc.get("dominio") == "judicial":
        print(f"   DNIs:        {datos.get('dnis', [])}")
        print(f"   Tribunal:    {datos.get('tribunal', 'N/A') or 'N/A'}")
        print(f"   Procedimiento: {datos.get('num_procedimiento', [])}")

    # Entidades del LLM (si existen)
    entidades = datos.get("_llm_entidades")
    if entidades:
        print(f"   🧠 LLM:")
        for k, v in entidades.items():
            if v:
                print(f"      - {k}: {v}")

    if completo:
        print(f"\n--- TEXTO COMPLETO ({doc['num_caracteres']} chars) ---")
        print(doc.get("texto_extraido", "")[:2000])
        if doc['num_caracteres'] > 2000:
            print("... (truncado, usar --export para ver todo)")


def listar(db: DocumentDatabase, tipo: str = None, dominio: str = None, limite: int = 20):
    """Lista documentos con filtros opcionales."""
    docs = db.listar_documentos(tipo_doc=tipo, dominio=dominio, limite=limite)
    
    if not docs:
        print("No se encontraron documentos.")
        return

    print(f"\n📚 Total: {len(docs)} documento(s)")
    for doc in docs:
        icono = _icono_entrada(doc['tipo_entrada'])
        print(f"  {icono} {doc['nombre_archivo']:<40} | {doc['tipo_documento']:<20} | {doc['num_caracteres']:>6} chars")

    print(f"\n💡 Usa --ver <ruta> para ver detalle de uno, o --completo con --listar")


def buscar(db: DocumentDatabase, palabra: str, limite: int = 20):
    """Búsqueda simple por palabra clave en el texto."""
    docs = db.buscar_por_texto(palabra, limite=limite)
    
    if not docs:
        print(f"No se encontraron documentos con '{palabra}'.")
        return

    print(f"\n🔍 {len(docs)} resultado(s) para '{palabra}':")
    for doc in docs:
        print(f"  📄 {doc['nombre_archivo']:<40} | {doc['tipo_documento']:<20}")
        # Mostramos un snippet del texto donde aparece
        texto = doc.get("texto_extraido", "")
        idx = texto.lower().find(palabra.lower())
        if idx != -1:
            inicio = max(0, idx - 60)
            fin = min(len(texto), idx + len(palabra) + 60)
            snippet = texto[inicio:fin].replace("\n", " ")
            print(f"      ...{snippet}...")


def ver(db: DocumentDatabase, ruta: str, completo: bool = False):
    """Muestra el detalle completo de un documento por ruta o nombre."""
    # Intentamos buscar por ruta exacta primero
    doc = db.obtener_por_ruta(ruta)
    
    # Si no, buscamos por nombre de archivo
    if not doc:
        docs = db.listar_documentos(limite=9999)
        for d in docs:
            if d['nombre_archivo'] == ruta or d['nombre_archivo'].startswith(ruta):
                doc = d
                break

    if not doc:
        print(f"❌ Documento no encontrado: {ruta}")
        return

    mostrar_documento(doc, completo=completo)


def estadisticas(db: DocumentDatabase):
    """Muestra estadísticas generales de la base."""
    total = db.contar_documentos()
    print(f"\n📊 ESTADÍSTICAS DE LA BASE DE DATOS")
    print(f"   Total documentos: {total}")
    
    if total == 0:
        return

    # Contamos por tipo
    docs = db.listar_documentos(limite=9999)
    tipos = {}
    dominios = {}
    for d in docs:
        t = d['tipo_documento'] or 'SIN_CLASIFICAR'
        tipos[t] = tipos.get(t, 0) + 1
        dom = d.get('dominio') or 'desconocido'
        dominios[dom] = dominios.get(dom, 0) + 1

    print(f"\n   Por tipo:")
    for tipo, count in sorted(tipos.items(), key=lambda x: -x[1]):
        print(f"      {count:>3} × {tipo}")

    print(f"\n   Por dominio:")
    for dom, count in sorted(dominios.items(), key=lambda x: -x[1]):
        print(f"      {count:>3} × {dom}")


def marcar_reprocesar(db: DocumentDatabase, nombre: str):
    """Busca un documento por nombre y lo marca para reprocesar."""
    docs = db.listar_documentos(limite=9999)
    for d in docs:
        if d['nombre_archivo'] == nombre or d['nombre_archivo'].startswith(nombre):
            db.marcar_para_reprocesar(d['ruta_original'])
            print(f"✅ Marcado para reprocesar: {d['nombre_archivo']}")
            return
    print(f"❌ Documento no encontrado: {nombre}")


def exportar(db: DocumentDatabase, ruta_salida: str):
    """Exporta todos los documentos a un JSON."""
    docs = db.listar_documentos(limite=9999)
    # Limpiamos campos internos para el export
    exportable = []
    for d in docs:
        exportable.append({
            "nombre": d['nombre_archivo'],
            "tipo": d['tipo_documento'],
            "dominio": d.get('dominio'),
            "caracteres": d['num_caracteres'],
            "fecha": d['fecha_procesamiento'],
            "datos": d.get('datos', {})
        })

    with open(ruta_salida, 'w', encoding='utf-8') as f:
        json.dump(exportable, f, ensure_ascii=False, indent=2)

    print(f"✅ Exportados {len(docs)} documentos a: {ruta_salida}")


# ============ GUION / DIARIZACIÓN ============

def _buscar_documento(db: DocumentDatabase, ruta_o_nombre: str) -> Optional[Dict]:
    """Busca un documento por ruta exacta o por prefijo de nombre."""
    doc = db.obtener_por_ruta(ruta_o_nombre)
    if doc:
        return doc
    docs = db.listar_documentos(limite=9999)
    for d in docs:
        if d['nombre_archivo'] == ruta_o_nombre or d['nombre_archivo'].startswith(ruta_o_nombre):
            return d
    return None


def _metadatos_guion(doc: Dict) -> Dict[str, str]:
    """Metadatos que aparecerán en la cabecera del guion."""
    return {
        "Archivo": doc['nombre_archivo'],
        "Ruta": doc['ruta_original'],
        "Tipo": doc.get('tipo_documento') or "desconocido",
        "Procesado": doc.get('fecha_procesamiento') or "desconocido",
    }


def _regenerar_guion(db: DocumentDatabase, doc_id: int) -> Optional[List[TurnoGuion]]:
    """Reconstruye y guarda los turnos del guion a partir de los datos almacenados."""
    segmentos = db.obtener_segmentos_asr(doc_id)
    turnos_db = db.obtener_turnos_diarizacion(doc_id)

    if not segmentos:
        return None

    turnos_guion = guion_mod.construir_guion(segmentos, turnos_db)
    db.guardar_turnos_guion(doc_id, guion_mod.turnos_guion_a_db(turnos_guion))
    return turnos_guion


def mostrar_guion(db: DocumentDatabase, ruta_o_nombre: str, sin_cabecera: bool = False):
    """Muestra el guion teatral de un archivo de audio/video."""
    doc = _buscar_documento(db, ruta_o_nombre)
    if not doc:
        print(f"❌ Documento no encontrado: {ruta_o_nombre}")
        return

    turnos_guion = _regenerar_guion(db, doc['id'])
    if turnos_guion is None:
        print(f"⚠️  {doc['nombre_archivo']} no tiene segmentos ASR. "
              "Transcríbelo primero con python -m documenttoolkit.main")
        return

    mapa_etiquetas = db.obtener_hablantes(doc['id'])
    metadatos = None if sin_cabecera else _metadatos_guion(doc)
    texto = guion_mod.renderizar_guion(
        turnos_guion,
        mapa_etiquetas=mapa_etiquetas,
        metadatos=metadatos,
        incluir_cabecera=not sin_cabecera,
    )
    print(texto)


def etiquetar_hablante(db: DocumentDatabase, ruta_o_nombre: str,
                       hablante_id: str, etiqueta: str):
    """Asigna una etiqueta humana a un identificador de voz."""
    doc = _buscar_documento(db, ruta_o_nombre)
    if not doc:
        print(f"❌ Documento no encontrado: {ruta_o_nombre}")
        return

    db.guardar_hablante(doc['id'], hablante_id, etiqueta)
    _regenerar_guion(db, doc['id'])
    print(f"✅ {hablante_id} → {etiqueta} en {doc['nombre_archivo']}")


def fusionar_hablantes(db: DocumentDatabase, ruta_o_nombre: str,
                       hablante_fuente: str, hablante_destino: str):
    """
    Une dos identificadores de voz en uno solo. Todos los turnos de la fuente
    pasan al destino y la etiqueta de la fuente se elimina.
    """
    doc = _buscar_documento(db, ruta_o_nombre)
    if not doc:
        print(f"❌ Documento no encontrado: {ruta_o_nombre}")
        return

    doc_id = doc['id']
    # Actualizar turnos crudos de diarización
    turnos = db.obtener_turnos_diarizacion(doc_id)
    actualizados = []
    for t in turnos:
        if t['hablante_id'] == hablante_fuente:
            t = dict(t)
            t['hablante_id'] = hablante_destino
        actualizados.append(t)
    db.guardar_turnos_diarizacion(doc_id, actualizados)

    # Borrar etiqueta de la fuente, si existía
    db.guardar_hablante(doc_id, hablante_fuente, None)

    _regenerar_guion(db, doc_id)
    print(f"✅ Fusionado {hablante_fuente} en {hablante_destino} en {doc['nombre_archivo']}")


def exportar_guion(db: DocumentDatabase, ruta_o_nombre: str, ruta_salida: str):
    """Exporta el guion a un archivo de texto."""
    doc = _buscar_documento(db, ruta_o_nombre)
    if not doc:
        print(f"❌ Documento no encontrado: {ruta_o_nombre}")
        return

    turnos_guion = _regenerar_guion(db, doc['id'])
    if turnos_guion is None:
        print(f"⚠️  {doc['nombre_archivo']} no tiene segmentos ASR.")
        return

    mapa_etiquetas = db.obtener_hablantes(doc['id'])
    texto = guion_mod.renderizar_guion(
        turnos_guion,
        mapa_etiquetas=mapa_etiquetas,
        metadatos=_metadatos_guion(doc),
    )

    with open(ruta_salida, 'w', encoding='utf-8') as f:
        f.write(texto)
    print(f"✅ Guion exportado a: {ruta_salida}")


def cargar_turnos(db: DocumentDatabase, ruta_o_nombre: str, ruta_json: str):
    """Carga turnos de diarización desde un JSON y regenera el guion."""
    doc = _buscar_documento(db, ruta_o_nombre)
    if not doc:
        print(f"❌ Documento no encontrado: {ruta_o_nombre}")
        return

    ruta_json_path = Path(ruta_json)
    if not ruta_json_path.exists():
        print(f"❌ No encontrado: {ruta_json}")
        return

    with open(ruta_json_path, 'r', encoding='utf-8') as f:
        turnos = json.load(f)

    if not isinstance(turnos, list):
        print("❌ El JSON debe contener una lista de turnos.")
        return

    db.guardar_turnos_diarizacion(doc['id'], turnos)
    _regenerar_guion(db, doc['id'])
    print(f"✅ Cargados {len(turnos)} turnos en {doc['nombre_archivo']}")


def regenerar_guion(db: DocumentDatabase, ruta_o_nombre: str):
    """Fuerza la regeneración del guion desde segmentos ASR y turnos de voz."""
    doc = _buscar_documento(db, ruta_o_nombre)
    if not doc:
        print(f"❌ Documento no encontrado: {ruta_o_nombre}")
        return

    turnos_guion = _regenerar_guion(db, doc['id'])
    if turnos_guion is None:
        print(f"⚠️  {doc['nombre_archivo']} no tiene segmentos ASR.")
        return
    print(f"✅ Guion regenerado: {len(turnos_guion)} turno(s)")


def main():
    parser = argparse.ArgumentParser(
        description="Consulta la base de datos de DocumentToolkit"
    )
    parser.add_argument(
        "--db", default=DB_PATH,
        help="Ruta a la base de datos SQLite (default: data/output/docs.db)"
    )
    
    subparsers = parser.add_subparsers(dest="comando", help="Comandos disponibles")

    # listar
    cmd_listar = subparsers.add_parser("listar", help="Listar documentos")
    cmd_listar.add_argument("--tipo", help="Filtrar por tipo de documento")
    cmd_listar.add_argument("--dominio", help="Filtrar por dominio")
    cmd_listar.add_argument("--limite", type=int, default=20, help="Máximo resultados")
    cmd_listar.add_argument("--completo", action="store_true", help="Ver detalle de cada uno")

    # buscar
    cmd_buscar = subparsers.add_parser("buscar", help="Buscar palabra en texto")
    cmd_buscar.add_argument("palabra", help="Palabra o frase a buscar")
    cmd_buscar.add_argument("--limite", type=int, default=20)

    # ver
    cmd_ver = subparsers.add_parser("ver", help="Ver detalle de un documento")
    cmd_ver.add_argument("ruta", help="Ruta o nombre del archivo")
    cmd_ver.add_argument("--completo", action="store_true", help="Mostrar texto completo")

    # stats
    subparsers.add_parser("stats", help="Estadísticas generales")

    # exportar
    cmd_export = subparsers.add_parser("exportar", help="Exportar a JSON")
    cmd_export.add_argument("salida", help="Ruta del archivo JSON de salida")

    # reprocesar
    cmd_reprocesar = subparsers.add_parser(
        "reprocesar",
        help="Marcar un documento para que se vuelva a procesar",
    )
    cmd_reprocesar.add_argument("nombre", help="Nombre del archivo")

    # guion
    cmd_guion = subparsers.add_parser(
        "guion",
        help="Mostrar el guion diarizado de un audio/video",
    )
    cmd_guion.add_argument("ruta", help="Ruta o nombre del archivo")
    cmd_guion.add_argument("--sin-cabecera", action="store_true",
                           help="Omitir la cabecera metodológica")

    # etiquetar
    cmd_etiquetar = subparsers.add_parser(
        "etiquetar",
        help="Asignar una etiqueta a un hablante",
    )
    cmd_etiquetar.add_argument("ruta", help="Ruta o nombre del archivo")
    cmd_etiquetar.add_argument("hablante", help="Identificador de hablante")
    cmd_etiquetar.add_argument("etiqueta", help="Etiqueta descriptiva")

    # fusionar
    cmd_fusionar = subparsers.add_parser(
        "fusionar",
        help="Fusionar dos identificadores de hablante",
    )
    cmd_fusionar.add_argument("ruta", help="Ruta o nombre del archivo")
    cmd_fusionar.add_argument("fuente", help="Hablante que desaparece")
    cmd_fusionar.add_argument("destino", help="Hablante que permanece")

    # exportar-guion
    cmd_export_guion = subparsers.add_parser(
        "exportar-guion",
        help="Exportar el guion a un archivo de texto",
    )
    cmd_export_guion.add_argument("ruta", help="Ruta o nombre del archivo")
    cmd_export_guion.add_argument("salida", help="Ruta del archivo TXT")

    # cargar-turnos
    cmd_cargar_turnos = subparsers.add_parser(
        "cargar-turnos",
        help="Cargar turnos de diarización desde un JSON (pruebas sin pyannote)",
    )
    cmd_cargar_turnos.add_argument("ruta", help="Ruta o nombre del archivo")
    cmd_cargar_turnos.add_argument("json", help="Ruta del JSON con turnos")

    # regenerar-guion
    cmd_regenerar = subparsers.add_parser(
        "regenerar-guion",
        help="Regenerar el guion desde segmentos ASR y turnos",
    )
    cmd_regenerar.add_argument("ruta", help="Ruta o nombre del archivo")

    args = parser.parse_args()

    if not args.comando:
        parser.print_help()
        return

    db = DocumentDatabase(db_path=args.db)

    if args.comando == "listar":
        docs = db.listar_documentos(tipo_doc=args.tipo, dominio=args.dominio, limite=args.limite)
        if args.completo:
            for doc in docs:
                mostrar_documento(doc, completo=False)
        else:
            listar(db, args.tipo, args.dominio, args.limite)

    elif args.comando == "buscar":
        buscar(db, args.palabra, args.limite)

    elif args.comando == "ver":
        ver(db, args.ruta, args.completo)

    elif args.comando == "stats":
        estadisticas(db)

    elif args.comando == "exportar":
        exportar(db, args.salida)

    elif args.comando == "reprocesar":
        marcar_reprocesar(db, args.nombre)

    elif args.comando == "guion":
        mostrar_guion(db, args.ruta, sin_cabecera=args.sin_cabecera)

    elif args.comando == "etiquetar":
        etiquetar_hablante(db, args.ruta, args.hablante, args.etiqueta)

    elif args.comando == "fusionar":
        fusionar_hablantes(db, args.ruta, args.fuente, args.destino)

    elif args.comando == "exportar-guion":
        exportar_guion(db, args.ruta, args.salida)

    elif args.comando == "cargar-turnos":
        cargar_turnos(db, args.ruta, args.json)

    elif args.comando == "regenerar-guion":
        regenerar_guion(db, args.ruta)


if __name__ == "__main__":
    main()