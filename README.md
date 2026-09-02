# DocumentToolkit

Herramienta en Python para la **extracción, normalización y validación de información procedente de documentos**, especialmente documentos bancarios y otros documentos PDF que pueden contener texto directamente o requerir OCR.

El proyecto nace como un ejercicio práctico para aprender y consolidar conocimientos de Python, procesamiento de documentos, expresiones regulares, testing, estructura de paquetes y, progresivamente, técnicas más avanzadas de extracción de información.

## Objetivo

La idea a medio/largo plazo es construir una herramienta capaz de recibir documentos heterogéneos y convertirlos en **datos estructurados y reutilizables**.

Por ejemplo, a partir de un extracto bancario:

```text
PDF / Imagen
     │
     ▼
Extracción de texto / OCR
     │
     ▼
Análisis del contenido
     │
     ├── Tipo de documento
     ├── IBAN
     ├── CCC
     ├── Titular
     ├── Fechas
     ├── Importes
     ├── Conceptos
     └── Otros datos
     │
     ▼
Validación y normalización
     │
     ▼
Diccionario / JSON / datos estructurados
```

El objetivo final no es simplemente "sacar texto" de un PDF, sino **entender parcialmente qué contiene el documento y convertirlo en información estructurada**.

---

## Estado actual

El proyecto se encuentra en una fase inicial pero funcional.

Actualmente se dispone de:

* Extracción de texto de documentos PDF.
* Detección de documentos que no contienen texto y utilización de OCR.
* Clasificación inicial del tipo de documento.
* Extracción de IBAN.
* Normalización básica del IBAN.
* Validación matemática del IBAN.
* Extracción de CCC.
* Validación matemática del CCC.
* Extracción inicial del titular en determinados documentos.
* Tests automatizados con `pytest`.
* Estructura de proyecto basada en `src/`.
* Configuración mediante `pyproject.toml`.
* Control de versiones mediante Git.

El proyecto todavía está lejos de ser un extractor documental general. Las funciones actuales son deliberadamente sencillas y están orientadas a construir progresivamente una base sólida.

---

## Estructura del proyecto

Actualmente se utiliza una estructura basada en `src`, habitual en proyectos Python empaquetables:

```text
DocumentToolkit/
│
├── .gitignore
├── pyproject.toml
├── README.md
│
├── src/
│   └── documenttoolkit/
│       ├── __init__.py
│       ├── main.py
│       ├── scanner.py
│       └── data_extractor.py
│
└── tests/
    └── test_ocr_data.py
```

El código de la aplicación se encuentra dentro de `src/documenttoolkit/`, mientras que los tests permanecen separados en `tests/`.

Esta organización ayuda a evitar determinados problemas de importación y hace que el proyecto se comporte de forma más parecida a un paquete Python real.

---

## Entorno de desarrollo

El proyecto utiliza un entorno virtual Python.

Activación:

```bash
source .venv/bin/activate
```

Comprobar el Python utilizado:

```bash
which python
```

Instalación del proyecto en modo editable:

```bash
pip install -e .
```

El modo editable permite trabajar sobre el código de `src/` sin tener que reinstalar el paquete después de cada modificación.

---

## Ejecución

Debido a que el proyecto utiliza una estructura `src/` y módulos con imports relativos, `main.py` no debe ejecutarse directamente como:

```bash
python src/documenttoolkit/main.py
```

La forma adecuada es ejecutar el módulo:

```bash
python -m documenttoolkit.main
```

---

## Tests

El proyecto utiliza `pytest`.

Para ejecutar toda la batería:

```bash
pytest
```

o:

```bash
python -m pytest
```

Los tests se encuentran actualmente en:

```text
tests/test_ocr_data.py
```

Una de las decisiones importantes del proyecto ha sido **desarrollar las funciones acompañadas de tests**, en lugar de limitarse a comprobar manualmente que el programa parece funcionar.

Esto permite modificar progresivamente el código manteniendo una comprobación automática de las funcionalidades ya implementadas.

---

# Funcionalidades implementadas

## Extracción de IBAN

Se implementó una primera versión de:

```python
extract_iban(texto)
```

La función busca una línea que comience por `ES`, ignorando espacios al principio y normalizando los espacios internos para realizar las comprobaciones.

Actualmente se comprueba:

* Que el texto comienza por `ES`.
* Que la parte numérica es realmente numérica.
* Que el IBAN español contiene 24 caracteres al eliminar los espacios.
* Conservación del formato encontrado en el documento.

Ejemplo:

```text
ES81 1491 0001 2930 0013 2401
```

También se contempla:

```text
ES8114910001293000132401
```

Los tests cubren, entre otros casos:

* IBAN normal.
* IBAN con espacios delante.
* IBAN sin espacios.
* Ausencia de IBAN.
* Texto que contiene una cadena que comienza por `ES` pero no es un IBAN válido.

---

## Validación de IBAN

Se implementó:

```python
validate_iban(iban)
```

utilizando el algoritmo estándar de validación mediante módulo 97.

De forma simplificada:

```text
IBAN
 │
 ├── mover los primeros 4 caracteres al final
 │
 ├── convertir las letras del país a números
 │
 ├── obtener una secuencia numérica
 │
 └── calcular módulo 97
          │
          └── resultado == 1 → IBAN válido
```

Actualmente se prueba tanto un IBAN válido como uno alterado deliberadamente para comprobar que la validación detecta el error.

---

## Extracción de CCC

Se añadió:

```python
extract_ccc(texto, iban)
```

El CCC español tiene 20 dígitos:

```text
Entidad Oficina DC Cuenta
  4      4    2   10
```

Por ejemplo:

```text
1491 0001 29 3000132401
```

La extracción actual busca una secuencia de 20 dígitos cuando el documento no contiene un IBAN.

Esto permite obtener el CCC de documentos antiguos en los que aparece el número de cuenta pero no el IBAN.

### Limitación conocida

Buscar simplemente cualquier secuencia de 20 dígitos puede producir falsos positivos.

Por ejemplo, un documento puede contener:

* números de referencia,
* identificadores,
* teléfonos,
* códigos internos,
* otras secuencias numéricas.

Por ello, la extracción del CCC deberá mejorar en una fase posterior utilizando el contexto del documento y, especialmente, la validación del CCC.

---

## Validación de CCC

Se implementó:

```python
validate_ccc(ccc)
```

La validación utiliza los dos dígitos de control del CCC.

La estructura utilizada es:

```text
Entidad + Oficina + DC + Cuenta
```

Para calcular los dígitos de control se utilizan los pesos:

```python
[1, 2, 4, 8, 5, 10, 9, 7, 3, 6]
```

Se realizan dos cálculos:

```text
00 + Entidad + Oficina
```

y:

```text
Cuenta
```

Después se obtiene cada dígito de control y se compara con los dos dígitos presentes en el CCC.

Actualmente se prueba tanto un CCC válido como uno modificado para comprobar que la validación falla correctamente.

---

# Extracción de datos

Las distintas funciones se integran mediante:

```python
extract_data(texto, tipo_documento)
```

que genera un diccionario similar a:

```python
{
    "tipo": "...",
    "num_caracteres": ...,
    "IBAN": "...",
    "IBAN_Valido": True,
    "CCC": "...",
    "CCC Valido": True,
    "Titular": "..."
}
```

Esto constituye una primera capa de estructuración de la información extraída.

La intención es que esta estructura crezca progresivamente a medida que se incorporen nuevos tipos de documentos y nuevos campos.

---

# Titular

Existe una primera implementación de:

```python
extract_titular(texto)
```

que busca determinados patrones presentes en documentos bancarios y obtiene la siguiente línea no vacía.

Es una solución todavía muy dependiente del formato concreto del documento.

La extracción del titular deberá evolucionar posteriormente hacia una estrategia más robusta basada en:

* patrones,
* contexto,
* distintos formatos bancarios,
* OCR,
* expresiones regulares,
* y posiblemente técnicas de clasificación o NLP.

---

# OCR

Una de las características importantes del proyecto es que no todos los PDFs contienen texto directamente.

El flujo contempla:

```text
PDF
 │
 ├── ¿Contiene texto?
 │       │
 │       ├── Sí → extracción directa
 │       │
 │       └── No → OCR
 │
 ▼
texto
```

Esto es especialmente importante para documentos escaneados o PDFs que contienen únicamente imágenes.

---

# Decisiones y aprendizajes importantes

Durante el desarrollo se han trabajado varios conceptos fundamentales de Python:

* funciones y parámetros;
* slicing de strings;
* `strip()`;
* `split()`;
* `join()`;
* `isdigit()` / `isnumeric()`;
* `ord()`;
* conversión entre `str` e `int`;
* expresiones regulares;
* módulos e imports;
* paquetes Python;
* imports relativos;
* entornos virtuales;
* `pyproject.toml`;
* estructura `src`;
* `pytest`;
* assertions;
* Git;
* commits y ramas;
* depuración mediante ejecución real del programa.

También se ha trabajado una idea especialmente importante para el proyecto:

> No basta con que una extracción "parezca funcionar"; los datos extraídos deben poder validarse.

Por eso IBAN y CCC tienen actualmente dos fases diferenciadas:

```text
EXTRACCIÓN
    ↓
¿qué cadena parece ser el dato?
    ↓
VALIDACIÓN
    ↓
¿esa cadena cumple realmente las reglas del dato?
```

Esta separación deberá mantenerse en futuras funcionalidades.

---

# Próximos objetivos

El proyecto no pretende alcanzar desde el principio un extractor perfecto. La estrategia prevista es evolucionar por capas.

## 1. Mejorar la extracción de CCC

La implementación actual puede producir falsos positivos.

Siguiente paso:

* utilizar el contexto de palabras como `Cuenta`, `Núm. de Cuenta`, `Entidad`, etc.;
* localizar mejor las secuencias de 20 dígitos;
* utilizar la validación CCC como filtro;
* añadir tests específicos para falsos positivos.

---

## 2. Mejorar la extracción del titular

La implementación actual funciona para determinados documentos, pero depende demasiado del formato.

Será necesario soportar diferentes estructuras documentales.

---

## 3. Extraer información bancaria adicional

Posibles campos:

```text
Fecha
Concepto
Importe
Saldo
Referencia
Número de operación
Entidad bancaria
```

Especialmente interesante será poder transformar una tabla de movimientos en una estructura como:

```python
[
    {
        "fecha": "...",
        "concepto": "...",
        "importe": ...,
        "saldo": ...
    },
    ...
]
```

---

## 4. Mejorar el reconocimiento del tipo de documento

Actualmente existe una clasificación inicial.

A futuro podría evolucionar hacia un sistema capaz de distinguir automáticamente:

```text
HIPOTECA
EXTRACTO_BANCARIO
MOVIMIENTO_BANCARIO
FACTURA
RECIBO
NÓMINA
CONTRATO
...
```

---

## 5. Crear una capa de normalización

Los documentos reales pueden representar el mismo dato de muchas formas.

Por ejemplo:

```text
ES81 1491 0001 2930 0013 2401
ES8114910001293000132401
ES81 1491 0001 2930 0013 2401
```

La aplicación debería ser capaz de:

```text
OCR / texto original
        ↓
extracción
        ↓
normalización
        ↓
validación
        ↓
dato estructurado
```

Esto será especialmente importante cuando se incorporen fechas, importes y nombres.

---

# Posible evolución futura

A largo plazo, DocumentToolkit podría convertirse en una herramienta de procesamiento documental más general:

```text
                    ┌───────────────┐
                    │ PDF / Imagen  │
                    └───────┬───────┘
                            │
                            ▼
                  ┌──────────────────┐
                  │ Texto / OCR      │
                  └────────┬─────────┘
                           │
                           ▼
                ┌─────────────────────┐
                │ Clasificación       │
                │ del documento       │
                └──────────┬──────────┘
                           │
                           ▼
                ┌─────────────────────┐
                │ Extracción          │
                │ de información      │
                └──────────┬──────────┘
                           │
                           ▼
                ┌─────────────────────┐
                │ Normalización       │
                └──────────┬──────────┘
                           │
                           ▼
                ┌─────────────────────┐
                │ Validación          │
                └──────────┬──────────┘
                           │
                           ▼
                ┌─────────────────────┐
                │ Datos estructurados │
                └─────────────────────┘
```

En una fase posterior, y si los requisitos lo justifican, se podrán estudiar técnicas más avanzadas:

* NLP;
* modelos de lenguaje;
* modelos especializados para documentos;
* clasificación automática;
* extracción mediante modelos de visión;
* procesamiento de tablas;
* procesamiento de documentos escaneados;
* aceleración mediante GPU.

La GPU disponible actualmente permitirá explorar este tipo de herramientas cuando el proyecto llegue a ese punto, pero **no es necesario introducirlas prematuramente**. La prioridad sigue siendo construir una base determinista, testeable y comprensible.

---

# Filosofía de desarrollo

El proyecto se desarrolla de forma incremental.

La estrategia seguida hasta ahora es:

```text
Problema pequeño
     ↓
Implementación sencilla
     ↓
Test
     ↓
Encontrar casos límite
     ↓
Mejorar implementación
     ↓
Nuevo test
     ↓
Commit
```

Se prioriza que cada nueva funcionalidad sea comprensible antes de intentar hacerla excesivamente sofisticada.

Una función sencilla que funciona, está testeada y puede mejorarse posteriormente es preferible a una implementación compleja que no se entiende bien.

---

# Estado de Git

El proyecto utiliza Git para conservar los avances.

Antes de realizar cambios importantes:

```bash
git status
```

Después de completar una funcionalidad y comprobar los tests:

```bash
pytest
```

se recomienda revisar los cambios:

```bash
git diff
```

y realizar un commit que represente una unidad lógica de trabajo:

```bash
git add ...
git commit -m "Descripción del cambio"
git push
```

Los ficheros experimentales que no forman parte del proyecto, como `tests/test_manu.py`, no deben incorporarse al repositorio.

---

# Cómo retomar el proyecto

En una nueva sesión:

```bash
cd ~/Proyectos/DocumentToolkit
source .venv/bin/activate
pip install -e .
pytest
```

Si los tests pasan, el entorno básico está preparado.

Para ejecutar la aplicación:

```bash
python -m documenttoolkit.main
```

Antes de continuar desarrollando conviene comprobar:

```bash
git status
```

y:

```bash
git log --oneline -5
```

---

# Situación actual

DocumentToolkit es todavía un proyecto en desarrollo.

Las funciones actuales no pretenden resolver todos los formatos posibles. Su propósito principal es construir progresivamente una arquitectura capaz de transformar documentos reales en información fiable.

El proyecto combina tres objetivos:

1. **Aprender Python mediante un proyecto real.**
2. **Construir una herramienta útil de procesamiento documental.**
3. **Crear una base que permita incorporar técnicas más avanzadas cuando sean necesarias.**

La evolución prevista es deliberadamente incremental: primero extracción y validación determinista; posteriormente normalización, clasificación y extracción de información más compleja; y finalmente, si aporta valor, técnicas de OCR/visión/NLP más avanzadas.
