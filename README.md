
# Rutas del Paisaje Cultural Cafetero

Proyecto final de Análisis de Algoritmos — Universidad del Quindío, 2026-2.

Este proyecto consiste en una aplicación para consultar rutas y organizar recorridos turísticos en el Quindío, utilizando una red vial construida a partir de datos de OpenStreetMap.

Durante el desarrollo trabajamos con algoritmos de grafos, divide y vencerás, programación dinámica y estrategias voraces. Además de implementarlos, realizamos pruebas para comparar sus tiempos de ejecución y comprobar sus resultados.

La aplicación permite consultar caminos mínimos, visualizar la envolvente convexa de la red vial, comparar recorridos turísticos y revisar los resultados de los experimentos.

## 1. Tecnologías utilizadas

- Python 3.11
- NetworkX y OSMnx para trabajar con la red vial
- OpenStreetMap como fuente de información geográfica
- SciPy para comprobar los resultados de QuickHull
- Streamlit para la aplicación web
- Folium y Streamlit-Folium para los mapas interactivos
- Pandas para manejar y presentar los datos
- Matplotlib para generar las gráficas
- Pytest para las pruebas automatizadas

Las implementaciones de Dijkstra, QuickHull, fuerza bruta, Held-Karp y vecino más cercano se desarrollaron como parte del proyecto. Las bibliotecas externas se utilizaron para manejar los datos, visualizar resultados y realizar comparaciones.

## 2. Datos utilizados

Se trabajó con una red vial dirigida y ponderada obtenida de OpenStreetMap, correspondiente al área de estudio del Quindío.

Después de procesar la red y seleccionar su componente fuertemente conexa principal, se obtuvieron:

| Característica | Cantidad |
|---|---:|
| Nodos | 30.981 |
| Aristas dirigidas | 71.353 |
| Lugares del catálogo | 40 |
| Pares origen-destino de la matriz | 1.600 |

El catálogo de lugares se organizó de la siguiente manera:

| Categoría | Cantidad |
|---|---:|
| Cabeceras municipales | 12 |
| Atractivos turísticos | 15 |
| Fincas y hoteles rurales | 8 |
| Centros de acopio y trilladoras | 5 |
| Total | 40 |

Las aristas de la red tienen pesos que representan tiempos estimados de desplazamiento, calculados a partir de las características de las vías y las velocidades asignadas.

Estos tiempos no corresponden a información de tráfico en tiempo real.

### Archivos principales

Los datos del modo real se encuentran en `datos/real/`.

- `red.graphml`: red vial procesada y ponderada
- `lugares.csv`: catálogo de los 40 lugares
- `matriz_tiempos_40x40.csv`: tiempos mínimos entre los lugares
- `envolvente.geojson`: polígono de la envolvente convexa
- `resumen_red.json`: información de la red procesada

También existe una carpeta `datos/demo/`, utilizada para trabajar con datos de demostración sin depender de toda la red real.

## 3. Instalación

Se recomienda utilizar Python 3.11 y trabajar dentro de un entorno virtual.

Primero se descarga el repositorio:

```bash
git clone https://github.com/laumcs21/rutas_paisaje_cafetero.git
cd rutas_paisaje_cafetero
```

### Windows (PowerShell)

Crear el entorno virtual:

```powershell
py -3.11 -m venv .venv
```

Instalar las dependencias:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Linux o macOS

Crear y activar el entorno:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

Instalar las dependencias:

```bash
python -m pip install -r requirements.txt
```

Para utilizar el modo REAL se necesitan los archivos procesados de `datos/real/`. La descarga del repositorio debe incluirlos o deben obtenerse mediante el procedimiento de preparación de datos.

También se necesita conexión a Internet para cargar el mapa base de OpenStreetMap.

## 4. Ejecutar la aplicación

En Windows, desde la carpeta principal del proyecto:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

En Linux o macOS, con el entorno virtual activo:

```bash
python -m streamlit run app.py
```

Streamlit mostrará una dirección local, normalmente:

```text
http://localhost:8501
```

La aplicación tiene cinco pestañas:

1. Ruta más rápida
2. Envolvente convexa
3. Itinerario de un día
4. Experimentos y tablas
5. Acerca del proyecto

En el menú lateral se puede seleccionar el conjunto de datos DEMO o REAL.

## 5. Requerimientos desarrollados

### R1. Construcción y procesamiento de la red vial

En este requerimiento se preparó la red vial del área de estudio a partir de información geográfica de OpenStreetMap.

Se utilizó el concepto de componentes fuertemente conexas para identificar la parte de la red en la que es posible encontrar caminos dirigidos entre sus nodos.

Se analizaron redes correspondientes a diferentes radios y al área completa, registrando sus tamaños y los tiempos de extracción de la componente principal.

Para la red completa se procesaron inicialmente 31.828 nodos y 73.014 aristas. La componente seleccionada quedó formada por 30.981 nodos y 71.353 aristas.

Los resultados de los experimentos están guardados en:

```text
resultados/r1_componentes/
```

En esta carpeta se encuentran las mediciones, la gráfica de tiempo frente al tamaño de la red y los demás archivos producidos durante las pruebas.

La red procesada se utilizó posteriormente para calcular los caminos mínimos del requerimiento 2.

### R2. Caminos mínimos con Dijkstra

Se implementaron dos versiones propias del algoritmo de Dijkstra en `rutas/dijkstra.py`.

**Dijkstra lineal**

Selecciona el nodo pendiente de menor distancia mediante una búsqueda lineal.

Complejidad temporal:

```text
O(V² + E)
```

**Dijkstra con cola de prioridad**

Utiliza un montículo binario mediante `heapq` para seleccionar el siguiente nodo.

Complejidad temporal:

```text
O((V + E) log V)
```

Las dos implementaciones utilizan el tiempo de viaje como peso de las aristas y reconstruyen el recorrido mediante los predecesores.

#### Experimentos

Se realizaron pruebas con 20 pares origen-destino utilizando Dijkstra con heap. Para comparar ambas versiones, también se ejecutó Dijkstra lineal sobre 10 de esos pares.

Se registraron:

- Tiempo de ejecución del algoritmo
- Tiempo estimado de viaje
- Número de nodos explorados
- Cantidad de nodos de la ruta
- Comparación de tiempos entre las dos implementaciones

Cada consulta se ejecutó cinco veces, salvo las excepciones del protocolo experimental, y se utilizó la mediana para presentar los tiempos.

Para reproducir estas pruebas:

```bash
python -m scripts.experimento_r2_pares
```

Las mediciones están en:

```text
resultados/r2_dijkstra/
```

#### Matriz de tiempos

También se construyó una matriz de 40 × 40 con los tiempos mínimos de desplazamiento entre los lugares del catálogo.

Para generar la matriz:

```bash
python -m scripts.generar_matriz_real
```

El archivo resultante es:

```text
datos/real/matriz_tiempos_40x40.csv
```

La matriz es asimétrica, ya que el tiempo de desplazamiento entre dos lugares puede cambiar según el sentido de circulación.

Para verificarla:

```bash
python -m scripts.validar_matriz_real
```

Los resultados de Dijkstra se compararon con NetworkX para comprobar que las distancias mínimas coincidieran en los casos evaluados.

### R3. Envolvente convexa con QuickHull

Se implementó QuickHull utilizando la estrategia de divide y vencerás.

El algoritmo identifica puntos extremos y divide el conjunto de coordenadas en subconjuntos para encontrar los vértices que forman la envolvente convexa.

La implementación propia se encuentra en:

```text
rutas/envolvente.py
```

Se utilizaron 30.980 puntos únicos de la red vial y se obtuvo una envolvente de 14 vértices.

#### Experimentos

La implementación propia se comparó con `scipy.spatial.ConvexHull` utilizando cuatro conjuntos:

| Conjunto | Puntos |
|---|---:|
| Red vial procesada | 30.980 |
| Cuadrado aleatorio | 1.000 |
| Cuadrado aleatorio | 10.000 |
| Cuadrado aleatorio | 50.000 |

Para generar los conjuntos aleatorios se utilizó la semilla 2026.

En los cuatro casos, los vértices calculados coincidieron con los obtenidos mediante SciPy. Sin embargo, SciPy presentó menores tiempos de ejecución.

Para repetir las pruebas:

```bash
python -m scripts.experimentos_r3_r4 --parte r3 --modo real --repeticiones 5
```

Resultados:

```text
experimentos/resultados/real/r3_envolvente.csv
experimentos/resultados/real/r3_repeticiones.json
```

Gráfica:

```text
experimentos/graficas/real/r3_envolvente.png
```

La aplicación también permite observar el polígono obtenido sobre el mapa.

### R4. Optimización de itinerarios turísticos

En este requerimiento se estudió el problema del viajante asimétrico utilizando la matriz de tiempos generada en R2.

Se implementaron tres algoritmos:

**Fuerza bruta**

Evalúa los posibles órdenes de visita mediante backtracking para encontrar el recorrido de menor costo.

Complejidad temporal:

```text
O(k · k!)
```

**Held-Karp**

Utiliza programación dinámica para evitar resolver repetidamente los mismos subproblemas.

Complejidad temporal:

```text
O(k² · 2^k)
```

**Vecino más cercano**

En cada paso selecciona el siguiente lugar con el menor costo de desplazamiento entre los destinos pendientes.

Complejidad temporal:

```text
O(k²)
```

La implementación de estos algoritmos se encuentra en:

```text
rutas/tsp.py
```

#### Comparación de los algoritmos exactos

Se compararon fuerza bruta y Held-Karp con diferentes cantidades de destinos, utilizando los tiempos de la matriz real.

| Destinos | Fuerza bruta (ms) | Held-Karp (ms) |
|---|---:|---:|
| 5 | 0,118 | 0,099 |
| 6 | 0,687 | 0,261 |
| 7 | 5,168 | 0,658 |
| 8 | 44,074 | 1,697 |
| 9 | 436,896 | 4,232 |
| 10 | 4.554,776 | 10,030 |
| 11 | 52.482,254 | 24,153 |
| 12 | No completada | 77,378 |

Para los tamaños completados por fuerza bruta, ambos algoritmos encontraron el mismo costo óptimo.

Se observó que fuerza bruta aumenta rápidamente su tiempo de ejecución a medida que crece la cantidad de destinos. En cambio, Held-Karp pudo resolver los casos evaluados en tiempos considerablemente menores.

#### Calidad del vecino más cercano

También se comparó el resultado del algoritmo voraz con la solución óptima obtenida por Held-Karp.

| Destinos | Brecha media | Brecha máxima |
|---|---:|---:|
| 5 | 1,90 % | 4,68 % |
| 8 | 8,82 % | 24,59 % |
| 10 | 4,29 % | 10,49 % |
| 12 | 13,11 % | 22,59 % |

Los resultados muestran que vecino más cercano puede encontrar buenas rutas, pero no garantiza obtener siempre el menor costo posible.

#### Itinerario turístico

Se elaboró un itinerario que inicia y termina en la Plaza principal de Armenia.

La selección final incluye siete atractivos turísticos:

1. Parque de la Vida
2. Museo del Oro Quimbaya
3. Tour de Finca Don Elias
4. Parroquia María Inmaculada
5. Calle del Tiempo Detenido
6. Mirador Colina Iluminada
7. La Pequeña Granja de Mamá Lulú

El recorrido calculado tiene aproximadamente 109,4 minutos de desplazamiento y 7,75 horas de visitas.

La duración total es de 9,574 horas, por lo que cumple el límite de 11 horas definido para la jornada.

Los tiempos de visita son estimaciones utilizadas para la planificación; no representan horarios oficiales ni duración obligatoria de permanencia.

#### Reproducir los experimentos

```bash
python -m scripts.experimentos_r3_r4 --parte r4 --modo real --max-k 12 --limite-s 300 --repeticiones 5
```

La ejecución de fuerza bruta para los tamaños mayores puede tardar varios minutos.

Los resultados quedan guardados en:

```text
experimentos/resultados/real/
```

Los principales archivos son:

- `r4_exactos.csv`: tiempos de fuerza bruta y Held-Karp
- `r4_exactos_detalle.json`: información detallada de las ejecuciones
- `r4_calidad.csv`: brechas de la heurística
- `r4_calidad_instancias.csv`: resultados de cada instancia
- `r4_contraejemplo.json`: ejemplo donde el voraz no encuentra el óptimo
- `r4_itinerario.csv`: recorrido turístico
- `r4_itinerario_resumen.json`: resumen del itinerario

La gráfica de rendimiento se encuentra en:

```text
experimentos/graficas/real/r4_exactos.png
```

### R5. Aplicación con Streamlit

Se desarrolló una aplicación que integra los algoritmos y permite consultar sus resultados mediante una interfaz web.

Las funcionalidades principales son:

**Ruta más rápida:** permite seleccionar un origen y un destino y calcular el camino mínimo utilizando Dijkstra con cola de prioridad.

**Envolvente convexa:** muestra el polígono calculado por QuickHull sobre el mapa de la red vial.

**Itinerario de un día:** permite seleccionar entre seis y ocho atractivos, calcular el recorrido óptimo mediante Held-Karp y compararlo con vecino más cercano.

**Experimentos y tablas:** presenta las mediciones y gráficas de los cuatro requerimientos.

**Acerca del proyecto:** muestra información general sobre el trabajo y los datos utilizados.

Los mapas se generan utilizando Folium y OpenStreetMap.

La aplicación funciona tanto con datos de demostración como con los archivos reales procesados.

## 6. Pruebas y verificaciones

El proyecto contiene pruebas automatizadas que se pueden ejecutar desde la raíz:

```bash
python -m pytest -q
```

En la última ejecución, realizada con Python 3.11.9, se obtuvo:

```text
13 passed in 7.38s
```

También se realizaron comprobaciones adicionales:

- Comparación de las distancias mínimas de Dijkstra con NetworkX
- Comparación de QuickHull con SciPy
- Comparación de los costos óptimos de Held-Karp y fuerza bruta
- Evaluación de la calidad de vecino más cercano
- Comprobación de la duración del itinerario turístico
- Verificación visual de las cinco pestañas de Streamlit

Los resultados experimentales de R3 y R4 se realizaron en Windows 11, con un procesador Intel Core i5-13420H y aproximadamente 16 GB de RAM.

Las mediciones de R2 se realizaron en otro equipo, con Apple M5. Por esta razón, los tiempos de distintos requerimientos no deben compararse directamente como si se hubieran obtenido bajo las mismas condiciones.

## 7. Estructura principal del proyecto

```text
rutas_paisaje_cafetero/
|
|-- app.py
|-- README.md
|-- requirements.txt
|-- pytest.ini
|
|-- rutas/
|   |-- dijkstra.py
|   |-- envolvente.py
|   |-- grafos.py
|   |-- tsp.py
|   `-- ...
|
|-- datos/
|   |-- demo/
|   `-- real/
|       |-- red.graphml
|       |-- lugares.csv
|       |-- matriz_tiempos_40x40.csv
|       |-- envolvente.geojson
|       `-- resumen_red.json
|
|-- scripts/
|   |-- experimento_r2_pares.py
|   |-- generar_matriz_real.py
|   |-- validar_matriz_real.py
|   |-- experimentos_r3_r4.py
|   `-- ...
|
|-- resultados/
|   |-- r1_componentes/
|   `-- r2_dijkstra/
|
|-- experimentos/
|   |-- resultados/
|   |   `-- real/
|   `-- graficas/
|       `-- real/
|
|-- docs/
|-- specs/
`-- tests/
```

Este esquema muestra los archivos y carpetas principales. El repositorio contiene otros módulos y archivos utilizados para preparar los datos y ejecutar los experimentos.

## 8. Consideraciones

Los resultados se obtuvieron con datos procesados de OpenStreetMap y las condiciones de ejecución descritas en el documento técnico.

Hay que tener presente que:

- Los tiempos de viaje son estimaciones, no información de tráfico en tiempo real.
- La matriz utilizada es dirigida, por lo que los tiempos de ida y regreso pueden ser diferentes.
- La envolvente convexa corresponde a los puntos de la red vial procesada, no al límite administrativo del Quindío.
- Held-Karp encuentra el recorrido de menor costo para los destinos seleccionados y los tiempos definidos en la matriz.
- El vecino más cercano no garantiza siempre el resultado óptimo.
- Los tiempos de visita de los atractivos son estimaciones para el ejercicio académico.
- Las mediciones de rendimiento pueden variar según el computador y el entorno utilizado.

Para ejecutar los experimentos se deben conservar las mismas versiones de los datos de entrada. Si cambia la red vial, el catálogo o la matriz de tiempos, puede ser necesario generar nuevamente algunos resultados.

## 9. Documentación

El documento técnico del proyecto contiene el desarrollo de los cinco requerimientos, incluyendo:

- Explicación de los algoritmos
- Análisis de complejidad temporal y espacial
- Argumentos de correctitud
- Metodología experimental
- Tablas y gráficas de resultados
- Comparaciones entre implementaciones
- Evidencias de la aplicación
- Conclusiones generales
- Referencias bibliográficas

También se documenta el uso de inteligencia artificial como herramienta de apoyo durante el desarrollo y la revisión del proyecto, junto con los procedimientos utilizados para comprobar los resultados.

## 10. Fuentes principales

- OpenStreetMap: https://www.openstreetmap.org/
- BBBike Extracts: https://extract.bbbike.org/
- OSMnx: https://osmnx.readthedocs.io/
- NetworkX: https://networkx.org/
- SciPy: https://docs.scipy.org/
- Streamlit: https://docs.streamlit.io/
- Python: https://docs.python.org/3/
- Algoritmos y referencias académicas: ver bibliografía del documento técnico

---

Proyecto académico desarrollado para la asignatura Análisis de Algoritmos de la Universidad del Quindío.
