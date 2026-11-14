import csv
import json
import math
import statistics
import time
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import osmnx as ox

from rutas.dijkstra import dijkstra_heap, dijkstra_lineal


BASE = Path("datos/real")
SALIDA = Path("resultados/r2_dijkstra")
SALIDA.mkdir(parents=True, exist_ok=True)

REPETICIONES = 5
UMBRAL_UNA_MEDICION_S = 60
LIMITE_SEGUNDOS = 300

PARES_CERCANOS = [
    ("M03", "A04"),
    ("M06", "A14"),
    ("M06", "A15"),
    ("M06", "A09"),
    ("M09", "A01"),
    ("M09", "A06"),
    ("M11", "C03"),
    ("M03", "C02"),
    ("M07", "C05"),
    ("M12", "A13"),
]

PARES_ADICIONALES = [
    ("M01", "M12"),
    ("M12", "M01"),
    ("M01", "M07"),
    ("M07", "M01"),
    ("M11", "A02"),
    ("M01", "A05"),
    ("M01", "A08"),
    ("M10", "F07"),
    ("M08", "F03"),
    ("M12", "A03"),
]


def construir_adyacencia(g):
    mejores = {nodo: {} for nodo in g.nodes}

    for u, v, _, datos in g.edges(keys=True, data=True):
        peso = float(datos["travel_time"])

        if not math.isfinite(peso) or peso < 0:
            raise ValueError("Se encontró un peso inválido")

        if peso < mejores[u].get(v, math.inf):
            mejores[u][v] = peso

    return {
        nodo: list(vecinos.items())
        for nodo, vecinos in mejores.items()
    }


def guardar_csv(ruta, filas, columnas):
    with ruta.open("w", encoding="utf-8", newline="") as f:
        escritor = csv.DictWriter(f, fieldnames=columnas)
        escritor.writeheader()
        escritor.writerows(filas)


def guardar_json(ruta, contenido):
    with ruta.open("w", encoding="utf-8") as f:
        json.dump(contenido, f, indent=2, ensure_ascii=False)


def medir(nombre, adj, origen, destino):
    inicio = time.perf_counter()

    if nombre == "heap":
        resultado = dijkstra_heap(adj, origen, destino)
    else:
        resultado = dijkstra_lineal(
            adj,
            origen,
            destino,
            tiempo_limite_s=LIMITE_SEGUNDOS,
        )

    duracion_ms = (time.perf_counter() - inicio) * 1000

    return {
        "tiempo_ejecucion_ms": duracion_ms,
        "tiempo_viaje_s": resultado.costo,
        "nodos_explorados": resultado.explorados,
        "ruta": resultado.ruta,
    }


COLUMNAS_MEDICIONES = [
    "origen", "destino", "algoritmo",
    "repeticiones_realizadas", "tiempo_ejecucion_ms",
    "nodos_explorados", "tiempo_viaje_s",
    "nodos_ruta", "estado",
]

COLUMNAS_REPETICIONES = [
    "origen", "destino", "algoritmo", "repeticion",
    "tiempo_ejecucion_ms", "nodos_explorados",
    "tiempo_viaje_s", "estado",
]

COLUMNAS_COCIENTES = [
    "origen", "destino",
    "lineal_ms", "heap_ms", "cociente",
]


def main():
    pares = PARES_CERCANOS + PARES_ADICIONALES

    if len(pares) != 20 or len(set(pares)) != 20:
        raise ValueError("Deben existir 20 pares diferentes")

    print("1. Cargando red y catálogo...", flush=True)

    grafo = ox.load_graphml(BASE / "red.graphml")
    adj = construir_adyacencia(grafo)

    with (BASE / "lugares.csv").open(
        encoding="utf-8", newline=""
    ) as f:
        lugares = {
            fila["id"]: fila
            for fila in csv.DictReader(f)
        }

    for a, b in pares:
        if a not in lugares or b not in lugares:
            raise ValueError(f"Lugar desconocido: {a}, {b}")

    print("Nodos:", grafo.number_of_nodes())
    print("Aristas:", grafo.number_of_edges())
    print("Pares heap:", len(pares))
    print("Pares lineal:", len(PARES_CERCANOS))
    print("Repeticiones previstas:", REPETICIONES)

    mediciones = []
    repeticiones = []
    rutas = []
    cocientes = []
    errores = 0

    def guardar_progreso():
        guardar_csv(
            SALIDA / "pares_mediciones.csv",
            mediciones,
            COLUMNAS_MEDICIONES,
        )
        guardar_csv(
            SALIDA / "pares_repeticiones.csv",
            repeticiones,
            COLUMNAS_REPETICIONES,
        )
        guardar_csv(
            SALIDA / "pares_cocientes.csv",
            cocientes,
            COLUMNAS_COCIENTES,
        )
        guardar_json(SALIDA / "pares_rutas.json", rutas)

    # Reinicia los archivos existentes, sin crear respaldos.
    guardar_progreso()

    print("\n2. Ejecutando consultas...", flush=True)

    for numero, (a, b) in enumerate(pares, start=1):
        origen = int(lugares[a]["nodo_id"])
        destino = int(lugares[b]["nodo_id"])

        print(
            f"\n{numero:02d}/20 {a} -> {b}",
            flush=True,
        )

        resultados_par = {}

        algoritmos = ["heap"]
        if (a, b) in PARES_CERCANOS:
            algoritmos.append("lineal")

        for nombre in algoritmos:
            muestras = []
            referencia = None
            estado = "OK"

            for repeticion in range(1, REPETICIONES + 1):
                try:
                    resultado = medir(
                        nombre, adj, origen, destino
                    )

                    ms = resultado["tiempo_ejecucion_ms"]

                    if ms > LIMITE_SEGUNDOS * 1000:
                        raise TimeoutError(
                            "La ejecución superó cinco minutos"
                        )

                    if not math.isfinite(
                        resultado["tiempo_viaje_s"]
                    ):
                        raise ValueError(
                            "El destino resultó inalcanzable"
                        )

                    ruta = resultado["ruta"]

                    if (
                        not ruta
                        or ruta[0] != origen
                        or ruta[-1] != destino
                    ):
                        raise ValueError(
                            "La ruta reconstruida es inválida"
                        )

                    if referencia is not None:
                        if not math.isclose(
                            resultado["tiempo_viaje_s"],
                            referencia["tiempo_viaje_s"],
                            rel_tol=1e-9,
                            abs_tol=1e-6,
                        ):
                            raise ValueError(
                                "Las repeticiones dieron "
                                "tiempos de viaje diferentes"
                            )

                        if (
                            resultado["nodos_explorados"]
                            != referencia["nodos_explorados"]
                        ):
                            raise ValueError(
                                "Las repeticiones dieron "
                                "cantidades diferentes "
                                "de nodos explorados"
                            )

                    if referencia is None:
                        referencia = resultado

                    muestras.append(ms)

                    repeticiones.append({
                        "origen": a,
                        "destino": b,
                        "algoritmo": nombre,
                        "repeticion": repeticion,
                        "tiempo_ejecucion_ms": round(ms, 6),
                        "nodos_explorados":
                            resultado["nodos_explorados"],
                        "tiempo_viaje_s": round(
                            resultado["tiempo_viaje_s"], 6
                        ),
                        "estado": "OK",
                    })

                    print(
                        f"  {nombre:6} rep {repeticion}: "
                        f"{ms:.3f} ms",
                        flush=True,
                    )

                    guardar_progreso()

                    # Excepción: si supera un minuto,
                    # no se hacen más repeticiones.
                    if ms > UMBRAL_UNA_MEDICION_S * 1000:
                        print(
                            "  Superó 60 s: "
                            "se conserva una medición.",
                            flush=True,
                        )
                        break

                except TimeoutError as error:
                    estado = "TIMEOUT"
                    errores += 1
                    print(
                        f"  {nombre}: TIMEOUT ({error})",
                        flush=True,
                    )
                    repeticiones.append({
                        "origen": a,
                        "destino": b,
                        "algoritmo": nombre,
                        "repeticion": repeticion,
                        "tiempo_ejecucion_ms": "",
                        "nodos_explorados": "",
                        "tiempo_viaje_s": "",
                        "estado": "TIMEOUT",
                    })
                    guardar_progreso()
                    break

                except ValueError as error:
                    estado = "ERROR"
                    errores += 1
                    print(
                        f"  {nombre}: ERROR ({error})",
                        flush=True,
                    )
                    guardar_progreso()
                    break

            if referencia is not None and estado == "OK":
                mediana_ms = statistics.median(muestras)

                fila = {
                    "origen": a,
                    "destino": b,
                    "algoritmo": nombre,
                    "repeticiones_realizadas": len(muestras),
                    "tiempo_ejecucion_ms": round(
                        mediana_ms, 6
                    ),
                    "nodos_explorados":
                        referencia["nodos_explorados"],
                    "tiempo_viaje_s": round(
                        referencia["tiempo_viaje_s"], 6
                    ),
                    "nodos_ruta": len(referencia["ruta"]),
                    "estado": "OK",
                }

                mediciones.append(fila)

                resultados_par[nombre] = {
                    "mediana_ms": mediana_ms,
                    **referencia,
                }

                rutas.append({
                    "origen": a,
                    "destino": b,
                    "algoritmo": nombre,
                    "tiempo_viaje_s":
                        referencia["tiempo_viaje_s"],
                    "ruta_nodos": referencia["ruta"],
                })

                print(
                    f"  MEDIANA {nombre}: "
                    f"{mediana_ms:.3f} ms | "
                    f"{referencia['nodos_explorados']} "
                    "explorados",
                    flush=True,
                )

            else:
                mediciones.append({
                    "origen": a,
                    "destino": b,
                    "algoritmo": nombre,
                    "repeticiones_realizadas":
                        len(muestras),
                    "tiempo_ejecucion_ms": "",
                    "nodos_explorados": "",
                    "tiempo_viaje_s": "",
                    "nodos_ruta": "",
                    "estado": estado,
                })

            guardar_progreso()

        if (a, b) in PARES_CERCANOS:
            if (
                "lineal" in resultados_par
                and "heap" in resultados_par
            ):
                lineal = resultados_par["lineal"]
                heap = resultados_par["heap"]

                if not math.isclose(
                    lineal["tiempo_viaje_s"],
                    heap["tiempo_viaje_s"],
                    rel_tol=1e-9,
                    abs_tol=1e-6,
                ):
                    errores += 1
                    print(
                        "  ERROR: los tiempos mínimos "
                        "son diferentes",
                        flush=True,
                    )
                else:
                    cocientes.append({
                        "origen": a,
                        "destino": b,
                        "lineal_ms":
                            lineal["mediana_ms"],
                        "heap_ms":
                            heap["mediana_ms"],
                        "cociente": (
                            lineal["mediana_ms"]
                            / heap["mediana_ms"]
                        ),
                    })

                    print(
                        "  Verificación lineal/heap: OK",
                        flush=True,
                    )

        guardar_progreso()

    print("\n3. Generando gráfica...", flush=True)

    fig, ax = plt.subplots(figsize=(9, 6))

    for nombre, etiqueta in [
        ("heap", "Dijkstra con heap"),
        ("lineal", "Dijkstra lineal"),
    ]:
        datos = [
            fila for fila in mediciones
            if fila["algoritmo"] == nombre
            and fila["estado"] == "OK"
        ]

        ax.scatter(
            [fila["nodos_explorados"] for fila in datos],
            [fila["tiempo_ejecucion_ms"] for fila in datos],
            label=etiqueta,
            s=48,
            alpha=0.8,
        )

    ax.set_title(
        "Dijkstra: tiempo frente a nodos explorados"
    )
    ax.set_xlabel("Nodos explorados")
    ax.set_ylabel(
        "Mediana del tiempo de ejecución (ms)"
    )
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()

    fig.savefig(
        SALIDA / "pares_tiempo_vs_explorados.png",
        dpi=180,
    )
    plt.close(fig)

    valores = [
        fila["cociente"] for fila in cocientes
    ]

    resumen = {
        "fecha": datetime.now().isoformat(),
        "grafo_nodos": grafo.number_of_nodes(),
        "grafo_aristas": grafo.number_of_edges(),
        "implementacion":
            "rutas/dijkstra.py",
        "repeticiones_previstas": REPETICIONES,
        "umbral_una_medicion_s":
            UMBRAL_UNA_MEDICION_S,
        "limite_ejecucion_s": LIMITE_SEGUNDOS,
        "pares_heap_esperados": 20,
        "pares_lineal_esperados": 10,
        "mediciones_completadas": sum(
            fila["estado"] == "OK"
            for fila in mediciones
        ),
        "repeticiones_completadas": sum(
            fila["estado"] == "OK"
            for fila in repeticiones
        ),
        "pares_verificados": len(cocientes),
        "errores": errores,
        "cociente_mediana": (
            statistics.median(valores)
            if valores else None
        ),
        "cociente_minimo": (
            min(valores) if valores else None
        ),
        "cociente_maximo": (
            max(valores) if valores else None
        ),
        "unidad_tiempo_ejecucion": "ms",
        "unidad_tiempo_viaje": "s",
        "nota": (
            "El tiempo de ejecución es la mediana "
            "de las repeticiones realizadas. "
            "La lectura del grafo y el catálogo "
            "no se incluye en las mediciones."
        ),
    }

    guardar_json(
        SALIDA / "pares_resumen.json",
        resumen,
    )

    print("\n========== RESULTADOS ==========")
    print(
        "Consultas completas:",
        resumen["mediciones_completadas"],
    )
    print(
        "Repeticiones completas:",
        resumen["repeticiones_completadas"],
    )
    print(
        "Pares verificados:",
        resumen["pares_verificados"],
    )
    print("Errores:", errores)

    if valores:
        print(
            "Cociente mediano:",
            round(statistics.median(valores), 2),
        )
        print(
            "Cociente mínimo:",
            round(min(valores), 2),
        )
        print(
            "Cociente máximo:",
            round(max(valores), 2),
        )

    print("\nEVIDENCIAS GENERADAS:")
    for archivo in [
        "pares_mediciones.csv",
        "pares_repeticiones.csv",
        "pares_cocientes.csv",
        "pares_rutas.json",
        "pares_resumen.json",
        "pares_tiempo_vs_explorados.png",
    ]:
        print(SALIDA / archivo)

    if errores or len(cocientes) != 10:
        raise SystemExit(
            "Experimento incompleto o con errores"
        )

    if resumen["mediciones_completadas"] != 30:
        raise SystemExit(
            "No se completaron las 30 consultas"
        )

    print(
        "\nREQUERIMIENTO 2: "
        "EXPERIMENTO DE PARES COMPLETADO"
    )


if __name__ == "__main__":
    main()
