"""R1: medir la componente fuertemente conexa en cinco tamaños de red."""

import csv
import json
from pathlib import Path
from statistics import median
from time import perf_counter_ns

import matplotlib.pyplot as plt
import osmnx as ox
from pyproj import Transformer


GRAFO = Path("datos/real/red_candidata.graphml")
SALIDA = Path("resultados/r1_componentes")
LAT_CENTRO = 4.53630700
LON_CENTRO = -75.67237510
RADIOS = [2000, 5000, 10000, 20000]
REPETICIONES = 5

SALIDA.mkdir(parents=True, exist_ok=True)


def guardar_csv(ruta, filas, columnas):
    with ruta.open("w", encoding="utf-8", newline="") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=columnas)
        escritor.writeheader()
        escritor.writerows(filas)


print("Cargando red candidata...", flush=True)
grafo = ox.load_graphml(GRAFO)

transformador = Transformer.from_crs(
    "EPSG:4326", "EPSG:32618", always_xy=True
)

centro_x, centro_y = transformador.transform(
    LON_CENTRO, LAT_CENTRO
)

coordenadas = {
    nodo: transformador.transform(
        float(datos["x"]), float(datos["y"])
    )
    for nodo, datos in grafo.nodes(data=True)
}

experimentos = []

for radio in RADIOS:
    nodos = [
        nodo
        for nodo, (x, y) in coordenadas.items()
        if (x - centro_x) ** 2 + (y - centro_y) ** 2 <= radio ** 2
    ]
    subgrafo = grafo.subgraph(nodos).copy()
    experimentos.append((f"Radio {radio // 1000} km", subgrafo))

experimentos.append(("Red candidata completa", grafo))

resumen = []
repeticiones = []

for nombre, red in experimentos:
    v = red.number_of_nodes()
    e = red.number_of_edges()

    if v == 0:
        raise RuntimeError(f"La red {nombre} no contiene nodos")

    tiempos = []
    componente = None

    print(f"\nProcesando: {nombre}", flush=True)
    print(f"Nodos: {v} | Aristas: {e}", flush=True)

    for numero in range(1, REPETICIONES + 1):
        inicio = perf_counter_ns()

        componente = ox.truncate.largest_component(
            red, strongly=True
        )

        tiempo_ms = (perf_counter_ns() - inicio) / 1_000_000
        tiempos.append(tiempo_ms)

        repeticiones.append({
            "red": nombre,
            "repeticion": numero,
            "V": v,
            "E": e,
            "V_mas_E": v + e,
            "tiempo_ms": round(tiempo_ms, 6),
        })

        print(
            f"  Repetición {numero}: {tiempo_ms:.3f} ms",
            flush=True,
        )

        if tiempo_ms > 60_000:
            print("  Más de 60 s: se detienen las repeticiones")
            break

        if tiempo_ms > 300_000:
            print("  Advertencia: superó el límite de cinco minutos")
            break

    registro = {
        "red": nombre,
        "V": v,
        "E": e,
        "V_mas_E": v + e,
        "V_componente": componente.number_of_nodes(),
        "E_componente": componente.number_of_edges(),
        "repeticiones": len(tiempos),
        "mediana_ms": round(median(tiempos), 6),
        "minimo_ms": round(min(tiempos), 6),
        "maximo_ms": round(max(tiempos), 6),
    }

    resumen.append(registro)

    print(
        f"  SCC: {registro['V_componente']} nodos, "
        f"{registro['E_componente']} aristas"
    )
    print(f"  Mediana: {registro['mediana_ms']:.3f} ms")


guardar_csv(
    SALIDA / "componentes_resumen.csv",
    resumen,
    list(resumen[0]),
)

guardar_csv(
    SALIDA / "componentes_repeticiones.csv",
    repeticiones,
    list(repeticiones[0]),
)

metadatos = {
    "grafo": str(GRAFO),
    "centro": {
        "latitud": LAT_CENTRO,
        "longitud": LON_CENTRO,
    },
    "proyeccion_metrica": "EPSG:32618",
    "metodo_subgrafo": "Nodos dentro de distancia euclidiana proyectada",
    "metodo_componente": "ox.truncate.largest_component(strongly=True)",
    "repeticiones_previstas": REPETICIONES,
    "incluye_descarga_en_tiempo": False,
    "resultados": resumen,
}

with (SALIDA / "componentes_resumen.json").open(
    "w", encoding="utf-8"
) as archivo:
    json.dump(metadatos, archivo, indent=2, ensure_ascii=False)


x = [fila["V_mas_E"] for fila in resumen]
y = [fila["mediana_ms"] for fila in resumen]

plt.figure(figsize=(9, 5.5))
plt.plot(x, y, marker="o")

for fila in resumen:
    plt.annotate(
        fila["red"],
        (fila["V_mas_E"], fila["mediana_ms"]),
        xytext=(6, 6),
        textcoords="offset points",
        fontsize=8,
    )

plt.xlabel("Tamaño del grafo (V + E)")
plt.ylabel("Tiempo mediano de extracción (ms)")
plt.title("R1 - Componentes fuertemente conexas")
plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(
    SALIDA / "componentes_tiempo_vs_tamano.png",
    dpi=180,
)
plt.close()

print("\n===== RESUMEN FINAL =====")
for fila in resumen:
    print(
        f"{fila['red']}: V={fila['V']}, E={fila['E']}, "
        f"V+E={fila['V_mas_E']}, "
        f"mediana={fila['mediana_ms']:.3f} ms"
    )

print(f"\nResultados guardados en: {SALIDA}")
