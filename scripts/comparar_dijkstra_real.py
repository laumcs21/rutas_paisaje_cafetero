import csv
import heapq
import json
import math
import statistics
import time
from collections import deque
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import osmnx as ox

BASE = Path("datos/real")
SALIDA = Path("resultados/r2_dijkstra")
SALIDA.mkdir(parents=True, exist_ok=True)

TAMANOS = [250, 500, 1000, 2000, 4000]
REPETICIONES = 5
LIMITE_SEGUNDOS = 300

ARCHIVO_MEDICIONES = SALIDA / "comparacion_mediciones.csv"
ARCHIVO_RESUMEN = SALIDA / "comparacion_resumen.csv"
ARCHIVO_JSON = SALIDA / "comparacion_configuracion.json"
ARCHIVO_GRAFICA = SALIDA / "comparacion_dijkstra.png"


def construir_adyacencia(grafo):
    adj = {nodo: {} for nodo in grafo.nodes}

    for u, v, _, datos in grafo.edges(keys=True, data=True):
        peso = float(datos["travel_time"])

        if not math.isfinite(peso) or peso <= 0:
            raise ValueError("Peso de carretera inválido")

        anterior = adj[u].get(v, math.inf)

        if peso < anterior:
            adj[u][v] = peso

    return adj


def extraer_subgrafo(adj, origen, cantidad):
    """
    Selecciona nodos mediante BFS sobre la red real.
    Devuelve la adyacencia dirigida inducida por ellos.
    """
    seleccionados = []
    visitados = {origen}
    cola = deque([origen])

    while cola and len(seleccionados) < cantidad:
        actual = cola.popleft()
        seleccionados.append(actual)

        for vecino in sorted(adj[actual]):
            if vecino not in visitados:
                visitados.add(vecino)
                cola.append(vecino)

    if len(seleccionados) < cantidad:
        raise ValueError(
            f"No se pudieron seleccionar {cantidad} nodos"
        )

    indices = {
        nodo: indice
        for indice, nodo in enumerate(seleccionados)
    }

    subadj = [[] for _ in seleccionados]
    aristas = 0

    for nodo in seleccionados:
        u = indices[nodo]

        for vecino, peso in adj[nodo].items():
            if vecino in indices:
                subadj[u].append((indices[vecino], peso))
                aristas += 1

    return subadj, aristas


def dijkstra_lineal(adj, origen, limite):
    """
    Dijkstra con selección lineal del mínimo.
    Complejidad: O(V^2 + E).
    """
    n = len(adj)
    distancias = [math.inf] * n
    visitados = [False] * n

    distancias[origen] = 0.0
    inicio = time.perf_counter()

    for paso in range(n):
        if paso % 32 == 0:
            if time.perf_counter() - inicio > limite:
                raise TimeoutError("Dijkstra lineal excedió el límite")

        actual = -1
        menor = math.inf

        for i in range(n):
            if not visitados[i] and distancias[i] < menor:
                menor = distancias[i]
                actual = i

        if actual == -1:
            break

        visitados[actual] = True

        for vecino, peso in adj[actual]:
            nueva = menor + peso

            if nueva < distancias[vecino]:
                distancias[vecino] = nueva

    return distancias


def dijkstra_heap(adj, origen, limite):
    """
    Dijkstra con heap binario.
    Complejidad: O((V+E) log V).
    """
    n = len(adj)
    distancias = [math.inf] * n
    distancias[origen] = 0.0

    cola = [(0.0, origen)]
    visitados = [False] * n
    inicio = time.perf_counter()
    iteraciones = 0

    while cola:
        iteraciones += 1

        if iteraciones % 256 == 0:
            if time.perf_counter() - inicio > limite:
                raise TimeoutError("Dijkstra heap excedió el límite")

        distancia, actual = heapq.heappop(cola)

        if visitados[actual]:
            continue

        visitados[actual] = True

        for vecino, peso in adj[actual]:
            nueva = distancia + peso

            if nueva < distancias[vecino]:
                distancias[vecino] = nueva
                heapq.heappush(cola, (nueva, vecino))

    return distancias


def comparar_distancias(a, b):
    if len(a) != len(b):
        return False

    return all(
        math.isclose(x, y, rel_tol=1e-9, abs_tol=1e-6)
        for x, y in zip(a, b)
    )


def medir(algoritmo, adj, origen):
    inicio = time.perf_counter()

    resultado = algoritmo(
        adj,
        origen,
        LIMITE_SEGUNDOS
    )

    tiempo_ms = (time.perf_counter() - inicio) * 1000

    return resultado, tiempo_ms


print("1. Cargando grafo real...", flush=True)

grafo = ox.load_graphml(BASE / "red.graphml")

with (BASE / "lugares.csv").open(
    encoding="utf-8", newline=""
) as f:
    lugares = list(csv.DictReader(f))

armenia = next(
    lugar for lugar in lugares
    if lugar["id"] == "M01"
)

origen = int(armenia["nodo_id"])

if origen not in grafo:
    raise ValueError("El nodo de Armenia no está en el grafo")

adyacencia = construir_adyacencia(grafo)

print("Nodos:", grafo.number_of_nodes())
print("Aristas:", grafo.number_of_edges())
print("Origen:", origen)

configuracion = {
    "fecha": datetime.now().isoformat(),
    "grafo": str(BASE / "red.graphml"),
    "origen": "M01",
    "nodo_origen": origen,
    "tamanos": TAMANOS,
    "repeticiones": REPETICIONES,
    "limite_segundos": LIMITE_SEGUNDOS,
    "peso": "travel_time",
    "unidad_pesos": "segundos",
    "unidad_mediciones": "milisegundos",
    "metodo_subgrafo": "BFS dirigido con vecinos ordenados",
    "nota": (
        "Subgrafos reales de distintos tamaños. "
        "No corresponden a radios geográficos."
    )
}

with ARCHIVO_JSON.open("w", encoding="utf-8") as f:
    json.dump(configuracion, f, indent=2, ensure_ascii=False)

algoritmos = {
    "lineal": dijkstra_lineal,
    "heap": dijkstra_heap
}

mediciones = []
resumen = []

campos_medicion = [
    "nodos",
    "aristas",
    "algoritmo",
    "repeticion",
    "tiempo_ms",
    "estado"
]

print("\n2. Ejecutando experimentos...", flush=True)

with ARCHIVO_MEDICIONES.open(
    "w", encoding="utf-8", newline=""
) as archivo:

    escritor = csv.DictWriter(
        archivo,
        fieldnames=campos_medicion
    )
    escritor.writeheader()

    for cantidad in TAMANOS:
        print(
            f"\n========== {cantidad} NODOS ==========",
            flush=True
        )

        subadj, aristas = extraer_subgrafo(
            adyacencia,
            origen,
            cantidad
        )

        print("Aristas inducidas:", aristas, flush=True)

        # Verificación previa: los dos algoritmos deben
        # producir exactamente los mismos costos mínimos.
        referencia = dijkstra_heap(
            subadj, 0, LIMITE_SEGUNDOS
        )

        comprobacion = dijkstra_lineal(
            subadj, 0, LIMITE_SEGUNDOS
        )

        if not comparar_distancias(referencia, comprobacion):
            raise ValueError(
                f"Resultados diferentes con {cantidad} nodos"
            )

        print("Validación de distancias: OK", flush=True)

        for repeticion in range(1, REPETICIONES + 1):

            # Alternamos el orden para reducir
            # posibles ventajas de caché.
            if repeticion % 2:
                orden = ["lineal", "heap"]
            else:
                orden = ["heap", "lineal"]

            for nombre in orden:
                estado = "OK"
                tiempo_ms = None

                try:
                    resultado, tiempo_ms = medir(
                        algoritmos[nombre],
                        subadj,
                        0
                    )

                    if not comparar_distancias(
                        referencia, resultado
                    ):
                        raise ValueError(
                            "Distancias mínimas incorrectas"
                        )

                except TimeoutError:
                    estado = "TIMEOUT"

                fila = {
                    "nodos": cantidad,
                    "aristas": aristas,
                    "algoritmo": nombre,
                    "repeticion": repeticion,
                    "tiempo_ms": (
                        f"{tiempo_ms:.6f}"
                        if tiempo_ms is not None
                        else ""
                    ),
                    "estado": estado
                }

                escritor.writerow(fila)
                archivo.flush()
                mediciones.append(fila)

                print(
                    f"Repetición {repeticion} | "
                    f"{nombre:6} | "
                    f"{tiempo_ms:.3f} ms"
                    if tiempo_ms is not None
                    else (
                        f"Repetición {repeticion} | "
                        f"{nombre} | TIMEOUT"
                    ),
                    flush=True
                )

        for nombre in algoritmos:
            valores = [
                float(fila["tiempo_ms"])
                for fila in mediciones
                if fila["nodos"] == cantidad
                and fila["algoritmo"] == nombre
                and fila["estado"] == "OK"
            ]

            estado = (
                "COMPLETO"
                if len(valores) == REPETICIONES
                else "INCOMPLETO"
            )

            resumen.append({
                "nodos": cantidad,
                "aristas": aristas,
                "algoritmo": nombre,
                "repeticiones_validas": len(valores),
                "mediana_ms": (
                    round(statistics.median(valores), 6)
                    if len(valores) == REPETICIONES
                    else ""
                ),
                "estado": estado
            })

with ARCHIVO_RESUMEN.open(
    "w", encoding="utf-8", newline=""
) as archivo:

    columnas = [
        "nodos",
        "aristas",
        "algoritmo",
        "repeticiones_validas",
        "mediana_ms",
        "estado"
    ]

    escritor = csv.DictWriter(
        archivo,
        fieldnames=columnas
    )

    escritor.writeheader()
    escritor.writerows(resumen)

print("\n3. Generando gráfica...", flush=True)

fig, ax = plt.subplots(figsize=(9, 5))

for nombre, etiqueta in [
    ("lineal", "Dijkstra lineal"),
    ("heap", "Dijkstra con heap")
]:
    datos = [
        fila
        for fila in resumen
        if fila["algoritmo"] == nombre
        and fila["estado"] == "COMPLETO"
    ]

    ax.plot(
        [fila["nodos"] for fila in datos],
        [fila["mediana_ms"] for fila in datos],
        marker="o",
        label=etiqueta
    )

ax.set_title(
    "Comparación experimental de Dijkstra - Quindío"
)
ax.set_xlabel("Número de nodos")
ax.set_ylabel("Mediana del tiempo (ms)")
ax.grid(True, alpha=0.3)
ax.legend()

fig.tight_layout()
fig.savefig(ARCHIVO_GRAFICA, dpi=180)
plt.close(fig)

print("\n========== RESUMEN ==========")

for fila in resumen:
    print(
        f"{fila['nodos']:5} nodos | "
        f"{fila['algoritmo']:6} | "
        f"mediana={fila['mediana_ms']} ms | "
        f"{fila['estado']}"
    )

print("\n========== ARCHIVOS GENERADOS ==========")
print(ARCHIVO_MEDICIONES)
print(ARCHIVO_RESUMEN)
print(ARCHIVO_JSON)
print(ARCHIVO_GRAFICA)

print("\nEXPERIMENTO TERMINADO")
