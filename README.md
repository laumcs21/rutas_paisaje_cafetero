# Rutas del Paisaje Cultural Cafetero

Proyecto final de **Análisis de Algoritmos (2026-2)** — Universidad del Quindío.

Sistema académico de planificación de rutas sobre una red vial de OpenStreetMap (OSM) del Quindío, Colombia. Incluye procesamiento de grafos, componentes fuertemente conexas, caminos mínimos, envolvente convexa y optimización de itinerarios, con análisis teórico y experimental.

> **Estado del proyecto:** los requerimientos **R1 (modelo de la red vial)** y **R2 (caminos mínimos)** están implementados, experimentados y documentados. Se verificaron visualmente los 40 lugares del catálogo, se ejecutaron las pruebas de Dijkstra y se actualizó el experimento de componentes por radios. La aplicación Streamlit permite consultar rutas con datos reales y consultar las tablas y gráficas de R1 y R2. **R3, R4 y sus flujos completos en la aplicación requieren revisión final** antes de declarar terminado el proyecto completo.

## Requisitos

- **Python 3.11**, versión usada en las mediciones: **3.11.18**.
- Dependencias instalables desde `requirements.txt` (incluido en el proyecto).
- Para el **modo real**, archivos procesados en `datos/real/` (ver apartado siguiente).
- Conexión a Internet para visualizar el mapa base y para repetir las descargas de OSM mediante Overpass.

Los experimentos documentados de R1 y R2 se ejecutaron en **macOS 26.6.2, Apple M5, ARM64 y 16 GB de RAM**. Los tiempos dependen del equipo y de la ejecución.

## Instalación y entorno virtual

Desde la raíz del repositorio, en macOS o Linux:

```bash
python3.11 -m venv .venv311
source .venv311/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

En Windows (PowerShell), tras crear el entorno:

```powershell
.\.venv311\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Las versiones de `requirements.txt` se expresan mediante intervalos compatibles; para reproducir exactamente un entorno de medición es necesario conservar también las versiones instaladas.

## Datos que utiliza la aplicación

El modo **real** necesita los siguientes archivos:

| Archivo | Descripción |
|---|---|
| `datos/real/red.graphml` | Red vial definitiva dirigida, con `length` (m), `speed_kph` y `travel_time` (s) por arista. |
| `datos/real/lugares.csv` | Catálogo geográfico de 40 lugares, con nodo vial asociado. |
| `datos/real/matriz_tiempos_40x40.csv` | Matriz de tiempos mínimos entre los 40 lugares, expresados en segundos. |

La red candidata de **31.828 nodos y 73.014 aristas dirigidas** se conserva en `datos/real/red_candidata.graphml`. La componente fuertemente conexa definitiva contiene **30.981 nodos y 71.353 aristas**.

El catálogo comprende **12 cabeceras municipales, 15 atractivos turísticos, 8 fincas cafeteras u hoteles rurales y 5 cooperativas/puntos relacionados con el sector cafetero**. Sus 40 registros fueron verificados visualmente y asociados a nodos existentes de la red. La finca La Granada presenta una distancia de **741,70 m** a su nodo más cercano; el resto está por debajo de 500 m. La verificación geográfica **no certifica acceso vehicular efectivo** ni sustituye la comprobación de los establecimientos como centros de acopio/trilladoras.

Los tiempos de viaje son **estimaciones del modelo**, basadas en longitud y velocidad asignada; no reflejan tráfico actual ni garantizan condiciones reales de las vías.

> **Reproducibilidad:** `.gitignore` excluye `datos/real/red.graphml`. Por tanto, **clonar el repositorio no garantiza disponer del grafo real**. Antes de entregar, se debe proporcionar el archivo por un medio documentado o establecer y verificar un procedimiento íntegramente reproducible para generarlo. Tampoco debe asumirse que `red_candidata.graphml` o los demás datos grandes estarán publicados sin comprobarlo.

## Ejecutar la aplicación

Con el entorno virtual activo y los datos correspondientes disponibles:

```bash
python -m streamlit run app.py
```

La barra lateral permite elegir **demo** (datos sintéticos) o **real** cuando están presentes los tres archivos requeridos. La pestaña **Ruta más rápida** permite seleccionar origen y destino, calcular la ruta con **Dijkstra propio con heap**, ver el tiempo estimado y visualizar el camino en un mapa interactivo.

La pestaña **Experimentos y tablas** presenta las tablas y gráficas de R1 y R2; las secciones de R3 y R4 muestran sus resultados cuando están disponibles. El modo demo utiliza `datos/demo/matriz_tiempos.csv`, mientras que el modo real utiliza `datos/real/matriz_tiempos_40x40.csv`.

## Requerimiento 1: modelo de la red vial

### Construcción y representación

La red vial se obtuvo de datos OSM del Quindío, filtrados y procesados para construir un grafo dirigido. Se seleccionó la componente fuertemente conexa más grande mediante `ox.truncate.largest_component(G, strongly=True)` y se guardó en `datos/real/red.graphml`.

Para el grafo final, con 30.981 nodos y 71.353 aristas, se compararon dos modelos **teóricos simplificados** de almacenamiento (sin sobrecarga de objetos Python):

| Estructura | Supuesto | Estimación |
|---|---|---:|
| Matriz de adyacencia | 8 bytes por celda: `8V²` | 7.678.578.888 bytes ≈ 7.678,58 MB |
| Lista de adyacencia | 8 bytes por nodo y 16 bytes por arista: `8V + 16E` | 1.389.496 bytes ≈ 1,39 MB |

Se eligieron las **listas de adyacencia** porque esta red es dispersa. Cada arista conserva su longitud en metros y un tiempo estimado en segundos obtenido de la velocidad OSM disponible o de valores imputados por tipo de vía. Las velocidades asumidas y la procedencia de la red deben consultarse en `datos/real/resumen_red.json` y en el documento técnico; no representan límites de circulación ni velocidades reales.

### Asociación de los 40 lugares

Los lugares se asociaron al nodo más cercano de la componente mediante distancia euclidiana en **UTM zona 18N (`EPSG:32618`)**. Los 40 nodos asociados existen en el grafo definitivo. La distancia elevada de La Granada y las limitaciones de acceso rural se documentan en el informe.

### Experimento de componentes fuertemente conexas

El experimento definitivo mide la extracción de la componente fuerte mayor para **cuatro redes obtenidas con `graph_from_point()`** alrededor de la Plaza Bolívar de Armenia (radios 2, 5, 10 y 20 km) y la **red candidata completa** ya guardada en `datos/real/red_candidata.graphml`.

Para reproducirlo, con conexión a Internet y la red candidata disponible:

```bash
python -m scripts.medir_componentes --plaza-lat 4.532466 --plaza-lon -75.672951
```

La función ejecuta **cinco mediciones por red**, registra la **mediana** en milisegundos y excluye la descarga/carga de grafos del cronómetro. El comando vuelve a calcular el CSV, por lo que sus tiempos pueden variar.

| Red | Nodos (V) | Aristas (E) | V + E | Nodos SCC | Aristas SCC | Mediana (ms) |
|---|---:|---:|---:|---:|---:|---:|
| Radio 2 km | 1.651 | 3.647 | 5.298 | 1.599 | 3.568 | 18,358 |
| Radio 5 km | 4.316 | 9.718 | 14.034 | 4.262 | 9.654 | 41,311 |
| Radio 10 km | 6.003 | 13.488 | 19.491 | 5.906 | 13.341 | 68,186 |
| Radio 20 km | 8.850 | 20.141 | 28.991 | 8.751 | 20.014 | 113,046 |
| Departamento completo | 31.828 | 73.014 | 104.842 | 30.981 | 71.353 | 347,854 |

Evidencias definitivas:

- `resultados/r1_componentes/mediciones_radios.csv`
- `resultados/r1_componentes/tiempo_vs_tamano_red.png`

El comportamiento observado es coherente con la complejidad **O(V + E)** del algoritmo de identificación de componentes empleado internamente. Las mediciones no incluyen descarga ni lectura de archivos.

## Requerimiento 2: caminos mínimos

### Implementaciones y correctitud

En `rutas/dijkstra.py` se implementaron dos versiones propias:

- `dijkstra_lineal()`: mínimo por búsqueda lineal, complejidad de peor caso **O(V² + E)** (se resume como **O(V²)** para grafos simples).
- `dijkstra_heap()`: cola de prioridad mediante `heapq`, complejidad de la implementación **O((V + E) log V)** para la red analizada; pueden existir entradas repetidas en el heap.

Ambas emplean `travel_time` en segundos, se detienen al extraer definitivamente el destino y reconstruyen la ruta mediante predecesores. En modo **sin destino**, `dijkstra_heap()` calcula los costos hacia todos los nodos alcanzables. NetworkX se utiliza para **verificar**, no para reemplazar los Dijkstra propios.

### Experimento comparativo de pares

```bash
python -m scripts.experimento_r2_pares
```

Se evaluaron **20 pares con heap** y **10 de esos pares cercanos también con búsqueda lineal**, con cinco repeticiones por consulta (**150 ejecuciones individuales**). Se excluyeron la lectura de archivos y la construcción de adyacencia de los tiempos medidos. Las diez comparaciones lineal/heap coincidieron en el tiempo mínimo calculado.

**Resultados actualizados del 13 de noviembre de 2026 (Apple M5):** 30 consultas completas, 150 ejecuciones individuales, 10 verificaciones lineal/heap correctas y 0 errores. El cociente entre medianas lineal/heap obtuvo una **mediana de 2.700,03×**, un **mínimo de 1.138,70×** y un **máximo de 3.009,27×**. Son resultados de este equipo y de estas implementaciones, no valores universales.

Archivos generados en `resultados/r2_dijkstra/`:

| Archivo | Contenido |
|---|---|
| `pares_mediciones.csv` | Medianas de las consultas por algoritmo y par. |
| `pares_repeticiones.csv` | Mediciones individuales. |
| `pares_cocientes.csv` | Cocientes lineal/heap de los diez pares comunes. |
| `pares_rutas.json` | Rutas reconstruidas para los pares medidos. |
| `pares_resumen.json` | Resultados de las verificaciones y cocientes. |
| `pares_tiempo_vs_explorados.png` | Gráfica de tiempo frente a nodos explorados. |

Las figuras y tablas del frontend leen estos resultados guardados.

### Matriz de tiempos 40 × 40

```bash
python -m scripts.generar_matriz_real
```

El procedimiento ejecuta Dijkstra con heap **una vez por origen, sin destino específico**, y guarda los 1.600 tiempos en:

```text
datos/real/matriz_tiempos_40x40.csv
```

**Resultados actualizados:** 40 lugares, **1.600 relaciones ordenadas**, **0 pares inalcanzables** y **1.546 pares ordenados asimétricos**. La ejecución registrada tomó **626,34 ms** en total y presentó una **mediana de 15,62 ms por origen**.

> Los tiempos de generación de la matriz describen **una sola ejecución** y **no** forman parte de la comparación experimental de cinco repeticiones entre lineal y heap.

Las mediciones y el resumen están en `resultados/r2_dijkstra/mediciones_matriz.csv` y `resultados/r2_dijkstra/resumen_matriz.json`.

### Verificación

```bash
python -m pytest -q
python -m scripts.validar_matriz_real
```

Se registraron **13 pruebas automatizadas aprobadas**, diez coincidencias lineal/heap en los pares compartidos y **10 coincidencias frente a NetworkX** en la validación de la matriz, sin errores. Las pruebas constituyen evidencia experimental de correctitud para los casos verificados; el argumento teórico se fundamenta en la extracción definitiva del mínimo con pesos no negativos.

## Estructura principal del repositorio

```text
rutas_paisaje_cafetero/
├── app.py
├── rutas/
│   ├── procesamiento.py
│   ├── dijkstra.py
│   ├── grafos.py
│   └── ...
├── scripts/
│   ├── medir_componentes.py
│   ├── experimento_r2_pares.py
│   ├── generar_matriz_real.py
│   ├── validar_matriz_real.py
│   └── ...
├── datos/
│   ├── real/
│   │   ├── red.graphml
│   │   ├── red_candidata.graphml
│   │   ├── lugares.csv
│   │   └── matriz_tiempos_40x40.csv
│   └── demo/
├── resultados/
│   ├── r1_componentes/
│   └── r2_dijkstra/
├── tests/
├── requirements.txt
└── README.md
```

Este esquema indica los archivos necesarios o generados en el proyecto local; **no garantiza que todos estén incluidos en GitHub**.

## Estado de los requerimientos

| Requerimiento | Estado |
|---|---|
| **R1. Modelo de la red vial** | Red, componente, pesos, catálogo y experimento por radios implementados y documentados. |
| **R2. Caminos mínimos** | Dos Dijkstra propios, matriz 40 × 40, pruebas, 20/10 pares, repeticiones y gráficas completados. |
| **R3. Envolvente convexa** | Implementación existente; pendiente de auditoría integral contra el enunciado. |
| **R4. Optimización de recorridos** | Implementación existente; pendiente de auditoría integral contra el enunciado. |
| **R5. Aplicación** | Consulta de rutas reales y visualización de R1/R2 verificadas; resta revisar integralmente los demás flujos. |

## Reproducibilidad y consideraciones

1. Ejecutar los comandos **desde la raíz** del proyecto, con el entorno virtual activo.
2. Mantener la **misma versión del grafo, catálogo y matriz** al comparar experimentos. Cambiar coordenadas o nodos obliga a recalcular los resultados dependientes.
3. Confirmar que el repositorio o los medios de entrega incluyan los **datos procesados** o instrucciones completas y verificadas para obtenerlos. El modo real no descarga la red automáticamente.
4. Distinguir el **tiempo de cómputo de los algoritmos (ms)** del **tiempo estimado de viaje (s)**.
5. Los scripts de experimentos **pueden sobrescribir los archivos de resultados**. Utilizar Git para conservar la versión entregada.
6. Las coordenadas fueron revisadas visualmente; los accesos físicos y la actividad concreta de las cooperativas se deben comprobar antes de presentar el catálogo como guía turística operativa.

## Uso de inteligencia artificial

Se utilizó ChatGPT como apoyo para interpretar el enunciado, revisar código, proponer pruebas, analizar complejidades y preparar documentación. Las propuestas se contrastaron con ejecuciones locales, pruebas automatizadas y comparaciones con NetworkX. **El documento técnico debe incluir el anexo obligatorio** con herramientas utilizadas, fines y procedimientos de verificación.

## Fuentes

- **OpenStreetMap:** https://www.openstreetmap.org/
- **OSMnx:** https://osmnx.readthedocs.io/
- **Python `heapq`:** https://docs.python.org/3/library/heapq.html
- **Dasgupta, Papadimitriou y Vazirani, *Algorithms*, capítulo 4:** https://people.eecs.berkeley.edu/~vazirani/algorithms/chap4.pdf
- **Tarjan (1972)** y **Nuutila y Soisalon-Soininen (1994):** fundamentos del algoritmo de componentes fuertemente conexas, citados en el documento técnico.

> **Uso académico:** las rutas y tiempos del sistema son resultados de un modelo de análisis de algoritmos, no un servicio de navegación en tiempo real.
