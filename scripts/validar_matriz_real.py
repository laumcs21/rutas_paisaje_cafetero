import csv
import json
import math
from datetime import datetime
from pathlib import Path

import networkx as nx
import osmnx as ox

BASE = Path("datos/real")
RESULTADOS = Path("resultados/r2_dijkstra")
RESULTADOS.mkdir(parents=True, exist_ok=True)

with (BASE / "lugares.csv").open(encoding="utf-8", newline="") as f:
    lugares = {fila["id"]: fila for fila in csv.DictReader(f)}

with (BASE / "matriz_tiempos_40x40.csv").open(
    encoding="utf-8", newline=""
) as f:
    matriz = {
        fila["origen"]: fila
        for fila in csv.DictReader(f)
    }

pares = [
    ("M01", "M12"),
    ("M12", "M01"),
    ("M01", "M07"),
    ("M07", "M01"),
    ("M03", "A04"),
    ("M09", "A01"),
    ("M11", "A02"),
    ("M12", "A13"),
    ("M06", "C04"),
    ("M10", "F07"),
]

print("Cargando grafo...", flush=True)
g = ox.load_graphml(BASE / "red.graphml")

resultados = []
errores = 0

print("\nVALIDACIÓN DE 10 RECORRIDOS\n")

for origen, destino in pares:
    u = int(lugares[origen]["nodo_id"])
    v = int(lugares[destino]["nodo_id"])

    calculado = float(matriz[origen][destino])

    referencia = nx.shortest_path_length(
        g, source=u, target=v, weight="travel_time"
    )

    diferencia = abs(calculado - referencia)
    correcto = math.isclose(
        calculado, referencia, rel_tol=1e-8, abs_tol=1e-4
    )

    if not correcto:
        errores += 1

    resultados.append({
        "origen": origen,
        "destino": destino,
        "dijkstra_propio_s": round(calculado, 6),
        "networkx_s": round(referencia, 6),
        "diferencia_s": round(diferencia, 6),
        "coincide": correcto,
    })

    print(
        f"{origen} -> {destino} | "
        f"Propio: {calculado / 60:.2f} min | "
        f"NetworkX: {referencia / 60:.2f} min | "
        f"{'OK' if correcto else 'ERROR'}"
    )

csv_salida = RESULTADOS / "validacion_matriz.csv"
with csv_salida.open("w", encoding="utf-8", newline="") as f:
    escritor = csv.DictWriter(f, fieldnames=resultados[0].keys())
    escritor.writeheader()
    escritor.writerows(resultados)

resumen = {
    "fecha": datetime.now().isoformat(),
    "metodo": "Comparacion con NetworkX shortest_path_length",
    "peso": "travel_time",
    "unidad": "segundos",
    "pares_validados": len(pares),
    "coincidencias": len(pares) - errores,
    "errores": errores,
    "resultado": "APROBADO" if errores == 0 else "FALLIDO",
}

json_salida = RESULTADOS / "validacion_matriz.json"
with json_salida.open("w", encoding="utf-8") as f:
    json.dump(resumen, f, indent=2, ensure_ascii=False)

print("\n========== RESULTADO FINAL ==========")
print("Pares comprobados:", len(pares))
print("Coincidencias:", len(pares) - errores)
print("Errores:", errores)
print("Validación:", resumen["resultado"])
print("\nEvidencias guardadas:")
print(csv_salida)
print(json_salida)

if errores:
    raise SystemExit(1)
