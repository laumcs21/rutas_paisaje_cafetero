import csv
import heapq
import json
import math
import statistics
import time
from datetime import datetime
from pathlib import Path

import osmnx as ox

BASE = Path("datos/real")
RESULTADOS = Path("resultados/r2_dijkstra")

RESULTADOS.mkdir(parents=True, exist_ok=True)


def cargar_lugares():
    with (BASE / "lugares.csv").open(
        encoding="utf-8", newline=""
    ) as archivo:
        return list(csv.DictReader(archivo))


def construir_adyacencia(grafo):
    adyacencia = {nodo: [] for nodo in grafo.nodes}

    mejores = {}

    for origen, destino, clave, atributos in grafo.edges(
        keys=True, data=True
    ):
        peso = float(atributos["travel_time"])

        if not math.isfinite(peso) or peso <= 0:
            raise ValueError("Se encontró un peso inválido")

        par = (origen, destino)

        if peso < mejores.get(par, math.inf):
            mejores[par] = peso

    for (origen, destino), peso in mejores.items():
        adyacencia[origen].append((destino, peso))

    return adyacencia


def dijkstra_heap(adyacencia, origen):
    distancias = {origen: 0.0}
    anteriores = {}

    cola = [(0.0, origen)]
    visitados = set()

    while cola:
        distancia, actual = heapq.heappop(cola)

        if actual in visitados:
            continue

        visitados.add(actual)

        for vecino, peso in adyacencia[actual]:
            nueva = distancia + peso

            if nueva < distancias.get(vecino, math.inf):
                distancias[vecino] = nueva
                anteriores[vecino] = actual

                heapq.heappush(
                    cola, (nueva, vecino)
                )

    return distancias, anteriores


def reconstruir_ruta(anteriores, origen, destino):
    if origen == destino:
        return [origen]

    camino = []
    actual = destino

    while actual != origen:
        camino.append(actual)

        if actual not in anteriores:
            return []

        actual = anteriores[actual]

    camino.append(origen)
    camino.reverse()

    return camino


print("1. Cargando la red vial real...", flush=True)

grafo = ox.load_graphml(BASE / "red.graphml")
lugares = cargar_lugares()

if len(lugares) != 40:
    raise ValueError("El catálogo debe tener 40 lugares")

ids = [lugar["id"] for lugar in lugares]

if len(set(ids)) != 40:
    raise ValueError("Hay identificadores duplicados")

nodos = {
    lugar["id"]: int(lugar["nodo_id"])
    for lugar in lugares
}

for identificador, nodo in nodos.items():
    if nodo not in grafo:
        raise ValueError(
            f"El nodo de {identificador} no existe"
        )

print("Nodos:", grafo.number_of_nodes())
print("Aristas:", grafo.number_of_edges())
print("Lugares:", len(lugares))

print("\n2. Construyendo adyacencia...", flush=True)

adyacencia = construir_adyacencia(grafo)

print("\n3. Ejecutando Dijkstra para cada origen...", flush=True)

matriz = {}
mediciones = []
ejemplo = None

for numero, origen_id in enumerate(ids, start=1):
    origen = nodos[origen_id]

    inicio = time.perf_counter()

    distancias, anteriores = dijkstra_heap(
        adyacencia, origen
    )

    tiempo_ms = (
        time.perf_counter() - inicio
    ) * 1000

    mediciones.append({
        "origen": origen_id,
        "tiempo_ms": tiempo_ms
    })

    matriz[origen_id] = {}

    for destino_id in ids:
        destino = nodos[destino_id]

        matriz[origen_id][destino_id] = (
            distancias.get(destino, math.inf)
        )

    if origen_id == "M01":
        destino_id = "M12"

        camino = reconstruir_ruta(
            anteriores,
            origen,
            nodos[destino_id]
        )

        ejemplo = {
            "origen": "M01",
            "destino": "M12",
            "algoritmo": "Dijkstra heap",
            "tiempo_segundos": distancias.get(
                nodos[destino_id], math.inf
            ),
            "camino_nodos": camino,
            "cantidad_nodos": len(camino)
        }

    print(
        f"{numero:02d}/40 - {origen_id} - "
        f"{tiempo_ms:.3f} ms",
        flush=True
    )

print("\n4. Validando la matriz...", flush=True)

inalcanzables = []

for origen_id in ids:
    for destino_id in ids:
        valor = matriz[origen_id][destino_id]

        if not math.isfinite(valor):
            inalcanzables.append(
                (origen_id, destino_id)
            )

        if origen_id == destino_id and valor != 0:
            raise ValueError(
                "La diagonal de la matriz debe ser cero"
            )

if inalcanzables:
    raise ValueError(
        f"Existen {len(inalcanzables)} pares "
        "inalcanzables"
    )

print("Todos los pares son alcanzables.")

print("\n5. Guardando resultados...", flush=True)

matriz_ruta = BASE / "matriz_tiempos_40x40.csv"

with matriz_ruta.open(
    "w", encoding="utf-8", newline=""
) as archivo:
    escritor = csv.writer(archivo)
    escritor.writerow(["origen"] + ids)

    for origen_id in ids:
        escritor.writerow(
            [origen_id] + [
                f"{matriz[origen_id][destino_id]:.6f}"
                for destino_id in ids
            ]
        )

with (
    RESULTADOS / "mediciones_matriz.csv"
).open("w", encoding="utf-8", newline="") as archivo:
    escritor = csv.DictWriter(
        archivo,
        fieldnames=["origen", "tiempo_ms"]
    )
    escritor.writeheader()
    escritor.writerows(mediciones)

asimetria = sum(
    1
    for a in ids
    for b in ids
    if a != b
    and abs(matriz[a][b] - matriz[b][a]) > 1e-6
)

tiempos = [
    medicion["tiempo_ms"]
    for medicion in mediciones
]

resumen = {
    "fecha": datetime.now().isoformat(),
    "algoritmo": "Dijkstra con heap binario",
    "grafo": str(BASE / "red.graphml"),
    "nodos": grafo.number_of_nodes(),
    "aristas": grafo.number_of_edges(),
    "lugares": 40,
    "dimension_matriz": [40, 40],
    "unidad_matriz": "segundos",
    "pares_inalcanzables": len(inalcanzables),
    "pares_ordenados_asimetricos": asimetria,
    "tiempo_total_ms": sum(tiempos),
    "tiempo_mediano_por_origen_ms": statistics.median(
        tiempos
    ),
    "tipo_medicion": (
        "Ejecucion exploratoria de 40 origenes; "
        "no equivale a cinco repeticiones por experimento"
    )
}

with (
    RESULTADOS / "resumen_matriz.json"
).open("w", encoding="utf-8") as archivo:
    json.dump(
        resumen, archivo,
        indent=2, ensure_ascii=False
    )

with (
    RESULTADOS / "ruta_armenia_salento.json"
).open("w", encoding="utf-8") as archivo:
    json.dump(
        ejemplo, archivo,
        indent=2, ensure_ascii=False
    )

print("\n========== RESULTADOS ==========")
print("Matriz:", len(ids), "x", len(ids))
print("Pares inalcanzables:", len(inalcanzables))
print("Pares ordenados asimétricos:", asimetria)
print("Tiempo total:", round(sum(tiempos), 2), "ms")
print(
    "Mediana por origen:",
    round(statistics.median(tiempos), 2),
    "ms"
)

print("\nARCHIVOS GUARDADOS")
print(matriz_ruta)
print(RESULTADOS / "mediciones_matriz.csv")
print(RESULTADOS / "resumen_matriz.json")
print(RESULTADOS / "ruta_armenia_salento.json")
