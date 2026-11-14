import csv
import math
from pathlib import Path

import osmnx as ox
from pyproj import Transformer
from scipy.spatial import cKDTree

BASE = Path("datos/real")
ENTRADA = BASE / "catalogo_ampliado_osm.csv"
ESTABLECIMIENTOS = BASE / "establecimientos_localizados_osm.csv"
SALIDA = BASE / "lugares.csv"

# Correspondencias verificables mediante identificadores OSM.
# La posición del polígono NO equivale necesariamente a su entrada.
POLIGONOS = {
    "A02": "610011228",
    "A12": "1016991317",
    "C01": "302511718",
    "C02": "507677601",
    "C03": "1315832516",
    "C04": "1370764909",
    "C05": "471991763",
}

# Coordenadas de nodos OSM encontrados en nuestro archivo local.
NODOS_OSM = {
    "A03": {
        "nombre": "Cocora",
        "osm_id": "703492775",
        "lat": 4.6375735,
        "lon": -75.4874648,
    },
    "A11": {
        "nombre": "Centro Experimental de la Guadua",
        "osm_id": "4511384787",
        "lat": 4.4022264,
        "lon": -75.715832,
    },
    "A13": {
        "nombre": "Parque Nacional Natural Los Nevados",
        "osm_id": "13876807128",
        "lat": 4.7480903,
        "lon": -75.4290819,
    },
}

def leer(ruta):
    with ruta.open(encoding="utf-8", newline="") as f:
        lector = csv.DictReader(f)
        return list(lector), lector.fieldnames

lugares, columnas = leer(ENTRADA)
establecimientos, _ = leer(ESTABLECIMIENTOS)

por_osm_id = {
    fila["osm_id"]: fila
    for fila in establecimientos
}

print("1. Cargando el grafo vial...", flush=True)

g = ox.load_graphml(BASE / "red.graphml")
g = ox.projection.project_graph(
    g,
    to_crs="EPSG:32618"
)

ids_nodos = list(g.nodes)
coordenadas_nodos = [
    (
        float(g.nodes[n]["x"]),
        float(g.nodes[n]["y"])
    )
    for n in ids_nodos
]

arbol = cKDTree(coordenadas_nodos)

transformador = Transformer.from_crs(
    "EPSG:4326",
    "EPSG:32618",
    always_xy=True
)

def asociar(lugar, lat, lon, fuente, estado):
    x, y = transformador.transform(lon, lat)
    distancia, indice = arbol.query((x, y))

    if not math.isfinite(distancia):
        raise ValueError(
            f"Distancia inválida para {lugar['id']}"
        )

    lugar["latitud"] = f"{lat:.8f}"
    lugar["longitud"] = f"{lon:.8f}"
    lugar["nodo_id"] = str(ids_nodos[int(indice)])
    lugar["distancia_nodo_m"] = f"{distancia:.2f}"
    lugar["fuente"] = fuente

    if distancia > 500:
        estado += "_DISTANCIA_MAYOR_500M"

    lugar["estado"] = estado

print("2. Completando lugares pendientes...", flush=True)

for lugar in lugares:
    identificador = lugar["id"]

    if identificador in POLIGONOS:
        osm_id = POLIGONOS[identificador]

        if osm_id not in por_osm_id:
            raise ValueError(
                f"Falta el polígono OSM {osm_id}"
            )

        referencia = por_osm_id[osm_id]

        lat = float(referencia["latitud"])
        lon = float(referencia["longitud"])

        # Conservamos el nombre de PANACA y Barbas Bremen.
        # Para cooperativas registramos el establecimiento
        # tal como aparece en OpenStreetMap.
        if identificador.startswith("C"):
            lugar["nombre"] = referencia["nombre_osm"]

        asociar(
            lugar,
            lat,
            lon,
            referencia["fuente"],
            "CENTRO_POLIGONO_OSM_VERIFICAR_ACCESO"
        )

    elif identificador in NODOS_OSM:
        referencia = NODOS_OSM[identificador]

        if identificador == "A11":
            lugar["nombre"] = referencia["nombre"]

        asociar(
            lugar,
            referencia["lat"],
            referencia["lon"],
            (
                "https://www.openstreetmap.org/node/"
                + referencia["osm_id"]
            ),
            "NODO_OSM_VERIFICAR_ACCESO_VEHICULAR"
        )

print("3. Validando las 40 ubicaciones...", flush=True)

if len(lugares) != 40:
    raise ValueError(
        f"Se esperaban 40 lugares y hay {len(lugares)}"
    )

ids = [lugar["id"] for lugar in lugares]

if len(ids) != len(set(ids)):
    raise ValueError("Hay identificadores repetidos")

faltantes = []

for lugar in lugares:
    if not all(
        lugar[campo]
        for campo in (
            "latitud",
            "longitud",
            "nodo_id",
            "distancia_nodo_m"
        )
    ):
        faltantes.append(lugar["id"])
        continue

    lat = float(lugar["latitud"])
    lon = float(lugar["longitud"])
    distancia = float(lugar["distancia_nodo_m"])

    if (
        not math.isfinite(lat)
        or not math.isfinite(lon)
        or not math.isfinite(distancia)
        or lugar["nodo_id"] not in {
            str(n) for n in ids_nodos
        }
    ):
        raise ValueError(
            f"Datos inválidos para {lugar['id']}"
        )

if faltantes:
    raise ValueError(
        "Lugares sin asociar: " + ", ".join(faltantes)
    )

with SALIDA.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:
    escritor = csv.DictWriter(
        f,
        fieldnames=columnas
    )
    escritor.writeheader()
    escritor.writerows(lugares)

alertas = [
    lugar for lugar in lugares
    if float(lugar["distancia_nodo_m"]) > 500
]

print("\n========== RESULTADOS ==========")
print("Total:", len(lugares))
print("Coordenadas completas:", len(lugares))
print("Nodos asociados:", len(lugares))
print("Distancias mayores a 500 m:", len(alertas))
print("Archivo:", SALIDA)

print("\nALERTAS:")
for lugar in alertas:
    print(
        lugar["id"],
        "|", lugar["nombre"],
        "|", lugar["distancia_nodo_m"], "m"
    )

print("\nDETALLE DE LOS 10 NUEVOS:")
for lugar in lugares:
    if (
        lugar["id"] in POLIGONOS
        or lugar["id"] in NODOS_OSM
    ):
        print(
            f"{lugar['id']:4} | "
            f"{lugar['nombre'][:45]:45} | "
            f"{lugar['distancia_nodo_m']:>9} m | "
            f"{lugar['estado']}"
        )

print("\nCatálogo geográfico preliminar generado.")
