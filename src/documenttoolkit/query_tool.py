"""
query_tool.py
Herramienta de consulta sobre la base de datos SQLite.
Ejecutable como script o importable como módulo.
"""

import json
import argparse
from pathlib import Path
from .database import DocumentDatabase


def mostrar_documento(doc: dict, completo: bool = False):
    """Imprime un documento de forma legible."""
    print(f"\n{'='*60}")
    print(f"📄 {doc['nombre_archivo']}")
    print(f"{'='*60}")
    print(f"   Tipo:        {doc['tipo_documento']}")
    print(f"   Dominio:     {doc.get('dominio', 'N/A')}")
    print(f"   Entrada:     {doc['tipo_entrada']}")
    print(f"   Caracteres:  {doc['num_caracteres']}")
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
        icono = "📄" if doc['tipo_entrada'] == 'pdf' else "🎬"
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


def main():
    parser = argparse.ArgumentParser(
        description="Consulta la base de datos de DocumentToolkit"
    )
    parser.add_argument(
        "--db", default="data/output/docs.db",
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


if __name__ == "__main__":
    main()