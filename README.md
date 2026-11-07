# Rutas del Paisaje Cultural Cafetero

**Proyecto final 2026-2 — Análisis de Algoritmos — Universidad del Quindío**

Sistema demostrativo para calcular rutas y visitas turísticas sobre una **red vial real del Quindío**, con implementaciones **propias** de Dijkstra, QuickHull, fuerza bruta para TSP, Held-Karp y vecino más cercano. Incluye experimentos, gráficos, pruebas automáticas y aplicación web.

> **IMPORTANTE:** Este ZIP incluye una **red sintética de 64 nodos y 40 lugares ficticios** únicamente para ejecutar la app y las pruebas sin Internet. **NO se ha descargado la red real ni verificado un catálogo real de 40 lugares.** No presentes las tablas o tiempos del modo `demo` como datos del departamento. La descarga y la verificación real están preparadas en los scripts.

## 1. Requisitos

- Python **3.11 o 3.12** (recomendado). Python 3.13+ puede exigir versiones de dependencias más recientes.
- Internet para instalar paquetes, descargar OSM y mostrar los mosaicos del mapa. No se requiere Internet para usar los algoritmos sobre datos de demostración ya incluidos.
- RAM suficiente para leer la red departamental; la memoria dependerá del tamaño actual de OSM. No se asume un número de nodos de antemano.

### macOS / Linux

```bash
cd rutas_paisaje_cafetero
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pytest -q
python -m streamlit run app.py
```

### Windows PowerShell

```powershell
cd rutas_paisaje_cafetero
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pytest -q
python -m streamlit run app.py
```

Si PowerShell bloquea la activación, ejecuta `Set-ExecutionPolicy -Scope Process Bypass` y vuelve a activar el entorno. Como alternativa usa `cmd.exe` y `.venv\Scripts\activate.bat`.

La app normalmente abre en `http://localhost:8501`. Selecciona `demo` en el menú lateral. Si prefieres regenerar los archivos sintéticos:

```bash
python -m scripts.generar_demo
```

## 2. Experimentos de demostración

```bash
python -m scripts.experimentos --modo demo --limite-s 5
```

Se guardan CSV en `experimentos/resultados/`, PNG en `experimentos/graficas/` y metadatos de entorno en `experimentos/resultados/entorno.json` con la marca `demo`.

El argumento `--limite-s 5` hace rápida la validación de la fuerza bruta. **Para la entrega final** debe usarse `--limite-s 300` (5 minutos por ejecución); ver protocolo del profesor.

## 3. Obtener y procesar la red vial REAL (requisito 1)

**3.1. Descargar las carreteras** de OpenStreetMap con OSMnx (requiere Internet, puede demorar según Overpass):

```bash
python -m scripts.preparar_red_real
```

O, si el docente entrega un GraphML:

```bash
python -m scripts.preparar_red_real --entrada ruta/al/archivo.graphml
```

Este comando guarda `datos/real/red.graphml` y `datos/real/resumen_red.json`. Descarga el grafo dirigido, obtiene la **componente fuertemente conexa más grande**, asigna velocidades de la etiqueta `maxspeed` o supuestos por tipo de vía, y obtiene el tiempo de viaje en segundos. No guarda tiempos reales de tráfico.

**3.2. Completar el catálogo auténtico de 40 lugares.** Edita `datos/real/catalogo_plantilla.csv` con **12 plazas principales, 15 atractivos, 8 fincas/hoteles rurales y 5 centros de acopio/trilladoras**, verificando nombre, municipio, coordenadas y fuente. Los atractivos requieren `visita_min` y justificación. Las filas pendientes no sirven para generar resultados. Consulta `docs/CATALOGO_REAL.md`.

**3.3. Asociar lugares a la red** usando la distancia euclidiana en **UTM 18N (EPSG:32618)**:

```bash
python -m scripts.asociar_catalogo
```

Revisa `datos/real/alertas_nodos_lejanos.json`: si un lugar está a más de 500 metros de un nodo, debes decidir/documentar si corregir sus coordenadas, elegir una entrada vial o excluir/sustituir el lugar. El programa **no inventa conexiones** y reporta todos los casos.

**3.4. Generar tiempos y envolvente**:

```bash
python -m scripts.generar_resultados_reales
```

Esto genera `datos/real/matriz_tiempos.csv` usando **una ejecución completa de nuestro Dijkstra con heap por cada lugar** y `datos/real/envolvente.geojson` usando nuestro QuickHull.

**3.5. Experimentos de la red real**:

```bash
python -m scripts.experimentos --modo real --limite-s 300
```

**3.6. Medir las componentes de cinco tamaños**. Primero verifica en un mapa las coordenadas exactas de **Plaza de Bolívar de Armenia**. No uses coordenadas aproximadas o del modo demo:

```bash
python -m scripts.medir_componentes --plaza-lat LAT_VERIFICADA --plaza-lon LON_VERIFICADA
```

La tabla de R1 se guarda en `experimentos/resultados/r1_componentes.csv`. El algoritmo de SCC se ejecuta 5 veces por tamaño; no se incluye tiempo de descarga.

**3.7. Aplicación con datos reales**:

```bash
python -m streamlit run app.py
```

Cuando existan los tres archivos necesarios (red, lugares y matriz), aparecerá el modo `real`. En el mapa las rutas y el itinerario se calculan al momento, no se leen como imágenes estáticas.

## 4. Algoritmos implementados desde cero

| Requisito | Implementación propia | Complejidad teórica principal |
|---|---|---|
| R1 | Representación como listas; SCC mediante OSMnx **permitido por el enunciado** | SCC O(V+E) |
| R2 | Dijkstra lineal | O(V²+E) = O(V²) para grafos simples |
| R2 | Dijkstra con `heapq` (solo la estructura de prioridad es biblioteca) | O((V+E) log V) |
| R3 | QuickHull: divide y vencerás; no usa `scipy` para calcular la solución propia | Esperado O(n log n); peor O(n²) |
| R4 | Fuerza bruta con permutaciones | O(k · k!) |
| R4 | Held-Karp para TSP **asimétrico**, recupera la ruta | O(k² · 2^k), memoria O(k · 2^k) |
| R4 | Vecino más cercano como heurística voraz | O(k²) |

**Atención:** `networkx` contiene/guarda el grafo pero **no se usa** para calcular los caminos en la solución propia. `scipy.spatial.ConvexHull` se usa **solo para comprobar** QuickHull, tal como permite el enunciado. `itertools.permutations` es una herramienta de enumeración, pero la fuerza bruta y su evaluación de recorridos son nuestras.

## 5. Archivos importantes

```text
app.py                       Aplicación web Streamlit
rutas/dijkstra.py            Dos Dijkstra propios
rutas/envolvente.py          QuickHull propio
rutas/tsp.py                 Fuerza bruta, Held-Karp, voraz
rutas/procesamiento.py       R1, UTM 18N, tiempos, matriz, polígonos
rutas/grafos.py              Lista de adyacencia, memoria, dibujo de rutas
scripts/generar_demo.py      Grafo y catálogo SINTÉTICOS
scripts/preparar_red_real.py Descarga de vías y cálculo SCC
scripts/asociar_catalogo.py Nodo más cercano por lugar
scripts/generar_resultados_reales.py   Matriz y envolvente
scripts/medir_componentes.py Medición R1, radios de 2/5/10/20 km
scripts/experimentos.py      Medición R2, R3 y R4, CSV/PNG
specs/                      Especificaciones y casos de prueba (SDD)
tests/                      Pruebas unitarias y prueba integral de demo
docs/INFORME_TECNICO_BORRADOR.md  Guion del informe académico
```

## 6. Protocolo experimental del enunciado

1. Medir en la misma máquina para cada requisito y reportar CPU, RAM, SO y Python.
2. No incluir carga de archivos, impresión, construcción de entradas ni gráficos dentro de la medición.
3. Hacer **5 ejecuciones y reportar la mediana**; si una ejecución tarda más de 1 minuto, ejecutarla solo una vez.
4. Usar milisegundos en CSV; semillas fijas documentadas (2026 en los experimentos).
5. Verificar correctitud **antes** de interpretar tiempos: los algoritmos propios se contrastan entre sí, con SciPy o con NetworkX en tests.
6. Límite: **5 minutos por ejecución**; reportar «no_completada» cuando exceda el límite en fuerza bruta o Dijkstra lineal.
7. Guardar CSV/JSON/PNG y explicar si los datos corresponden con la complejidad.

**Las tablas del modo demo no son resultados académicos reales.** Para entregar, usa datos `real`, registra el hardware (RAM en `entorno.json` se deja como campo a completar) y verifica el código/fuentes de cada biblioteca instalada.

## 7. Entrega

- Repositorio GitHub del grupo: fuente, datos **procesados**, resultados y README. Si los GraphML exceden el límite de GitHub, usa Git LFS o entrega un enlace y un procedimiento reproducible; no desaparezcas datos sin documentarlo.
- Aplicación local funcionando con instrucciones.
- Documento técnico: arquitectura, análisis teórico (incluidas recurrencias), correctitud, tablas/gráficas, discusión, conclusiones y anexo de uso de IA.
- Sustentación: cada integrante puede ser evaluado sobre cualquier módulo; **la nota individual se ajusta según la sustentación**.

Se incluyen plantillas en `docs/` para completar el análisis con los datos reales. Más detalles en `COMENZAR_AQUI.txt`.
