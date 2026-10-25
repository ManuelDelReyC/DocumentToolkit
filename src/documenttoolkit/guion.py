"""
guion.py
Alineación de palabras de Whisper con turnos de voz y renderizado de un
guion teatral con marcas temporales. No importa modelos de diarización;
recibe los turnos como datos y produce el texto del guion.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple, Any


UMBRAL_PAUSA_SEG: float = 1.5
UMBRAL_SOLAPAMIENTO_PALABRA: float = 0.05
UMBRAL_CONFUSION_SOLAPE: float = 0.35
ID_HABLANTE_DESCONOCIDO: str = "HABLANTE_?"
ETIQUETA_SOLAPAMIENTO: str = "SOLAPAMIENTO"


@dataclass
class Palabra:
    """Una palabra reconocida por Whisper con sus tiempos."""
    inicio: float
    fin: float
    texto: str
    hablante: Optional[str] = None
    solapamiento: float = 0.0  # fracción de la duración cubierta por el turno principal
    hablantes_solapados: List[str] = field(default_factory=list)

    def duracion(self) -> float:
        return max(0.0, self.fin - self.inicio)


@dataclass
class TurnoVoz:
    """Turno crudo de diarización: intervalo de tiempo y etiqueta de hablante."""
    hablante: str
    inicio: float
    fin: float

    def duracion(self) -> float:
        return max(0.0, self.fin - self.inicio)


@dataclass
class TurnoGuion:
    """Bloque de diálogo ya alineado, listo para renderizar."""
    hablante: str
    inicio: float
    fin: float
    texto: str
    confianza_media: float = 0.0
    es_solapamiento: bool = False
    hablantes_solapados: List[str] = field(default_factory=list)
    requiere_revision: bool = False
    es_pausa: bool = False


@dataclass
class Hablante:
    """Mapa entre un identificador de voz y su etiqueta revisada."""
    id_voz: str
    etiqueta: Optional[str] = None


def formatear_tiempo(segundos: float) -> str:
    """Devuelve HH:MM:SS.mmm si hay horas, o MM:SS.mmm si no."""
    segundos = max(0.0, segundos)
    h = int(segundos // 3600)
    m = int((segundos % 3600) // 60)
    s = segundos % 60
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:06.3f}"
    return f"{m:02d}:{s:06.3f}"


def _solapamiento(inicio_a: float, fin_a: float, inicio_b: float, fin_b: float) -> float:
    """Longitud del solapamiento entre dos intervalos."""
    return max(0.0, min(fin_a, fin_b) - max(inicio_a, inicio_b))


def _cobertura_palabra(palabra: Palabra, inicio_turno: float, fin_turno: float) -> float:
    """Fracción de la palabra cubierta por un turno de voz."""
    duracion = palabra.duracion()
    if duracion <= 0:
        return 0.0
    return _solapamiento(palabra.inicio, palabra.fin, inicio_turno, fin_turno) / duracion


def alinear_palabras_a_turnos(
    palabras: List[Palabra],
    turnos: List[TurnoVoz],
    umbral_cobertura: float = UMBRAL_SOLAPAMIENTO_PALABRA,
    umbral_confusion: float = UMBRAL_CONFUSION_SOLAPE,
) -> List[Palabra]:
    """
    Asigna cada palabra al hablante cuyo turno de voz la cubre más.

    Reglas:
    - Si ningún turno cubre al menos `umbral_cobertura`, la palabra queda
      como desconocida.
    - Si hay dos o más turnos y el segundo cubre al menos un
      `umbral_confusion` del primero, se marca como solapamiento.
    - El texto de las palabras no se modifica.
    """
    palabras_alineadas: List[Palabra] = []

    for palabra in palabras:
        # (hablante, cobertura)
        coberturas: List[Tuple[str, float]] = []
        for turno in turnos:
            cob = _cobertura_palabra(palabra, turno.inicio, turno.fin)
            if cob > 0:
                coberturas.append((turno.hablante, cob))

        if not coberturas:
            palabras_alineadas.append(Palabra(
                inicio=palabra.inicio,
                fin=palabra.fin,
                texto=palabra.texto,
                hablante=ID_HABLANTE_DESCONOCIDO,
                solapamiento=0.0,
            ))
            continue

        coberturas.sort(key=lambda x: x[1], reverse=True)
        principal, cob_principal = coberturas[0]

        hay_confusion = False
        if len(coberturas) >= 2 and cob_principal > 0:
            ratio = coberturas[1][1] / cob_principal
            if ratio >= umbral_confusion:
                hay_confusion = True

        if hay_confusion:
            solapados = [c[0] for c in coberturas if c[1] >= umbral_cobertura]
            solapados = sorted(set(solapados))
            palabras_alineadas.append(Palabra(
                inicio=palabra.inicio,
                fin=palabra.fin,
                texto=palabra.texto,
                hablante=ETIQUETA_SOLAPAMIENTO,
                solapamiento=cob_principal,
                hablantes_solapados=solapados,
            ))
        elif cob_principal < umbral_cobertura:
            palabras_alineadas.append(Palabra(
                inicio=palabra.inicio,
                fin=palabra.fin,
                texto=palabra.texto,
                hablante=ID_HABLANTE_DESCONOCIDO,
                solapamiento=cob_principal,
            ))
        else:
            palabras_alineadas.append(Palabra(
                inicio=palabra.inicio,
                fin=palabra.fin,
                texto=palabra.texto,
                hablante=principal,
                solapamiento=cob_principal,
            ))

    return palabras_alineadas


def agrupar_turnos_guion(
    palabras: List[Palabra],
    umbral_pausa: float = UMBRAL_PAUSA_SEG,
    umbral_revision_confianza: float = 0.6,
) -> List[TurnoGuion]:
    """
    Agrupa palabras consecutivas del mismo hablante en turnos de guion.

    Separa por:
    - Cambio de hablante.
    - Bloque de solapamiento (siempre aislado).
    - Pausa mayor que `umbral_pausa`.
    """
    if not palabras:
        return []

    turnos: List[TurnoGuion] = []

    # Estado del turno en construcción
    hablante_actual: Optional[str] = None
    inicio_actual: Optional[float] = None
    fin_actual: Optional[float] = None
    palabras_actuales: List[Palabra] = []

    def _cerrar_turno():
        nonlocal hablante_actual, inicio_actual, fin_actual, palabras_actuales
        if not palabras_actuales or hablante_actual is None:
            return
        texto = " ".join(p.texto for p in palabras_actuales).strip()
        if not texto:
            return
        confianzas = [p.solapamiento for p in palabras_actuales]
        confianza_media = sum(confianzas) / len(confianzas)

        hablantes_solapados: List[str] = []
        if hablante_actual == ETIQUETA_SOLAPAMIENTO:
            vistos: set = set()
            for p in palabras_actuales:
                for h in p.hablantes_solapados:
                    if h not in vistos:
                        vistos.add(h)
                        hablantes_solapados.append(h)

        turnos.append(TurnoGuion(
            hablante=hablante_actual,
            inicio=inicio_actual,
            fin=fin_actual,
            texto=texto,
            confianza_media=confianza_media,
            es_solapamiento=hablante_actual == ETIQUETA_SOLAPAMIENTO,
            hablantes_solapados=hablantes_solapados,
            requiere_revision=(confianza_media < umbral_revision_confianza
                               or hablante_actual == ID_HABLANTE_DESCONOCIDO),
        ))

    for palabra in palabras:
        # Primera palabra
        if hablante_actual is None:
            hablante_actual = palabra.hablante
            inicio_actual = palabra.inicio
            fin_actual = palabra.fin
            palabras_actuales = [palabra]
            continue

        # Forzar cierre si cambia el tipo de hablante o hay solapamiento
        cambio_hablante = palabra.hablante != hablante_actual
        pausa_larga = (palabra.inicio - fin_actual) > umbral_pausa
        es_solap = (hablante_actual == ETIQUETA_SOLAPAMIENTO
                    or palabra.hablante == ETIQUETA_SOLAPAMIENTO)

        if cambio_hablante or pausa_larga or es_solap:
            _cerrar_turno()
            hablante_actual = palabra.hablante
            inicio_actual = palabra.inicio
            fin_actual = palabra.fin
            palabras_actuales = [palabra]
        else:
            palabras_actuales.append(palabra)
            fin_actual = palabra.fin

    _cerrar_turno()
    return turnos


def _etiqueta_visible(hablante: str, mapa_etiquetas: Dict[str, str]) -> str:
    """Devuelve la etiqueta revisada de un hablante, o el id original."""
    if hablante in mapa_etiquetas:
        return mapa_etiquetas[hablante]
    return hablante


def renderizar_guion(
    turnos: List[TurnoGuion],
    mapa_etiquetas: Optional[Dict[str, str]] = None,
    metadatos: Optional[Dict[str, str]] = None,
    incluir_cabecera: bool = True,
) -> str:
    """
    Genera el texto del guion teatral con tiempos y notas metodológicas.
    """
    if mapa_etiquetas is None:
        mapa_etiquetas = {}

    lineas: List[str] = []

    if incluir_cabecera:
        lineas.append("=" * 70)
        lineas.append("GUION DE TRANSCRIPCION")
        lineas.append("=" * 70)
        if metadatos:
            for clave, valor in metadatos.items():
                lineas.append(f"{clave}: {valor}")
        lineas.append("")
        lineas.append("NOTA METODOLOGICA:")
        lineas.append("- El texto es el reconocido automaticamente por Whisper.")
        lineas.append("- No se ha reescrito ni corregido el contenido del dialogo.")
        lineas.append("- HABLANTE_N son agrupaciones acusticas; no son identidades.")
        lineas.append("- El nombre de una parte solo aparece si se ha asignado manualmente.")
        lineas.append("- Los solapamientos se indican como bloques especiales; no se reparten")
        lineas.append("  el texto entre dos voces porque Whisper produce un unico flujo.")
        lineas.append("- [?] marca un turno que requiere revision humana.")
        lineas.append("")

    ultimo_fin: Optional[float] = None
    for turno in turnos:
        # Pausa entre turnos
        if ultimo_fin is not None and not turno.es_solapamiento:
            hueco = turno.inicio - ultimo_fin
            if hueco > UMBRAL_PAUSA_SEG:
                lineas.append(f"(pausa {hueco:.1f} s)")
                lineas.append("")

        marca_revision = " [?]" if turno.requiere_revision else ""

        if turno.es_solapamiento:
            lineas.append(
                f"[{ETIQUETA_SOLAPAMIENTO} {formatear_tiempo(turno.inicio)} --> "
                f"{formatear_tiempo(turno.fin)}]{marca_revision}"
            )
            voces = ", ".join(turno.hablantes_solapados) if turno.hablantes_solapados else "DESCONOCIDAS"
            lineas.append(f"    Voces activas: {voces}")
            lineas.append("    Texto reconocido, no separable:")
            lineas.append(f"    {turno.texto}")
        else:
            etiqueta = _etiqueta_visible(turno.hablante, mapa_etiquetas)
            lineas.append(
                f"{etiqueta}{marca_revision}  [{formatear_tiempo(turno.inicio)} --> "
                f"{formatear_tiempo(turno.fin)}]"
            )
            lineas.append(f"    {turno.texto}")

        lineas.append("")
        ultimo_fin = turno.fin

    return "\n".join(lineas).rstrip() + "\n"


def palabras_desde_segmentos(segmentos: List[Dict[str, Any]]) -> List[Palabra]:
    """Convierte los segmentos ASR guardados en la BD en lista de Palabra."""
    palabras: List[Palabra] = []
    for seg in segmentos:
        for w in seg.get("palabras", []):
            palabras.append(Palabra(
                inicio=float(w["inicio"]),
                fin=float(w["fin"]),
                texto=str(w["texto"]),
            ))
    return palabras


def turnos_voz_desde_db(turnos_db: List[Dict[str, Any]]) -> List[TurnoVoz]:
    """Convierte los turnos de diarización de la BD en objetos TurnoVoz."""
    return [
        TurnoVoz(
            hablante=str(t["hablante_id"]),
            inicio=float(t["inicio"]),
            fin=float(t["fin"]),
        )
        for t in turnos_db
    ]


def turnos_guion_a_db(turnos: List[TurnoGuion]) -> List[Dict[str, Any]]:
    """Convierte objetos TurnoGuion en dicts listos para guardar en BD."""
    return [
        {
            "hablante": t.hablante,
            "inicio": t.inicio,
            "fin": t.fin,
            "texto": t.texto,
            "confianza_media": t.confianza_media,
            "es_solapamiento": t.es_solapamiento,
            "requiere_revision": t.requiere_revision,
            "hablantes_solapados": t.hablantes_solapados,
        }
        for t in turnos
    ]


def construir_guion(
    segmentos: List[Dict[str, Any]],
    turnos_diarizacion: List[Dict[str, Any]],
    mapa_etiquetas: Optional[Dict[str, str]] = None,
) -> List[TurnoGuion]:
    """
    Pipeline completo de alineación: de segmentos ASR + turnos de voz
    a turnos de guion listos para renderizar.
    """
    palabras = palabras_desde_segmentos(segmentos)
    turnos_voz = turnos_voz_desde_db(turnos_diarizacion)
    palabras_alineadas = alinear_palabras_a_turnos(palabras, turnos_voz)
    turnos = agrupar_turnos_guion(palabras_alineadas)

    if mapa_etiquetas:
        # El renderizador ya aplica el mapa; aquí no transformamos el hablante
        # para no perder la trazabilidad en la BD.
        pass

    return turnos
