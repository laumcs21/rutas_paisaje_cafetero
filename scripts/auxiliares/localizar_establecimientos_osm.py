import csv
import xml.etree.ElementTree as ET
from pathlib import Path

import osmnx as ox
from pyproj import Transformer
from scipy.spatial import cKDTree

BASE = Path("datos/real")
OSM = BASE / "quindio_completo.osm"
GRAFO = BASE / "red.graphml"
SALIDA = BASE / "establecimientos_localizados_osm.csv"

OBJETIVOS = {
    "610011228": "PANACA",
    "1016991317": "Reserva Barbas Bremen",
    "296113221": "Trilladora Colombia",
    "302511718": "Cooperativa de Caficultores",
    "318893062": "Almacafe Armenia",
    "335522436": "Trilladora Goncheverry",
    "335522438": "Trilladora La Amelia",
    "436483002": "Cooperativa de Caficultores",
    "440352500": "Trilladora Europa",
    "471991763": "Cooperativa de Caficultores",
    "507677601": "Cooperativa de Caficultores",
    "1315832516": "Cooperativa de Caficultores",
    "1370764909": "Cooperativa de Caficultores",
    "1472557688": "Centro de acopio",
}

ways = {}
referencias = set()

print("1. Buscando las vías y polígonos seleccionados...", flush=True)

contexto = ET.iterparse(OSM, events=("start", "end"))
_, raiz = next(contexto)

for evento, elemento in contexto:
    if evento != "end":
        continue

    if elemento.tag == "way":
        identificador = elemento.get("id")

        if identificador in OBJETIVOS:
            refs = [
                nd.get("ref")
                for nd in elemento.findall("nd")
            ]

            tags = {
                tag.get("k"): tag.get("v")
                for tag in elemento.findall("tag")
            }

            ways[identificador] = {
                "refs": refs,
                "tags": tags,
            }

            referencias.update(refs)

    if elemento.tag in ("node", "way", "relation"):
        raiz.clear()

print("Polígonos encontrados:", len(ways))
print("Nodos necesarios:", len(referencias))

print("\n2. Recuperando coordenadas...", flush=True)

coordenadas = {}

contexto = ET.iterparse(OSM, events=("start", "end"))
_, raiz = next(contexto)

for evento, elemento in contexto:
    if evento != "end":
        continue

    if elemento.tag == "node":
        identificador = elemento.get("id")

        if identificador in referencias:
            coordenadas[identificador] = (
                float(elemento.get("lat")),
                float(elemento.get("lon")),
            )

    if elemento.tag in ("node", "way", "relation"):
        raiz.clear()

print("Coordenadas recuperadas:", len(coordenadas))

print("\n3. Cargando grafo vial...", flush=True)

g = ox.load_graphml(GRAFO)
g = ox.projection.project_graph(g, to_crs="EPSG:32618")

nodos = list(g.nodes)
posiciones = [
    (float(g.nodes[n]["x"]), float(g.nodes[n]["y"]))
    for n in nodos
]

arbol = cKDTree(posiciones)

transformador = Transformer.from_crs(
    "EPSG:4326",
    "EPSG:32618",
    always_xy=True
)

resultados = []

for identificador, nombre_referencia in OBJETIVOS.items():
    way = ways.get(identificador)

    if way is None:
        print("NO ENCONTRADO:", identificador)
        continue

    puntos = [
        coordenadas[ref]
        for ref in way["refs"]
        if ref in coordenadas
    ]

    if not puntos:
        print("SIN GEOMETRIA:", identificador)
        continue

    # Centro medio aproximado del conjunto de nodos.
    # No representa necesariamente la entrada vehicular.
    lat = sum(p[0] for p in puntos) / len(puntos)
    lon = sum(p[1] for p in puntos) / len(puntos)

    x, y = transformador.transform(lon, lat)
    distancia, indice = arbol.query((x, y))

    tags = way["tags"]

    resultado = {
        "osm_id": identificador,
        "nombre_osm": tags.get("name", nombre_referencia),
        "referencia": nombre_referencia,
        "latitud": round(lat, 8),
        "longitud": round(lon, 8),
        "nodo_id": nodos[int(indice)],
        "distancia_nodo_m": round(float(distancia), 2),
        "tipo_osm": "way",
        "fuente": (
            f"https://www.openstreetmap.org/way/{identificador}"
        ),
        "estado": "CENTRO_GEOMETRICO_POR_VALIDAR",
    }

    resultados.append(resultado)

with SALIDA.open("w", encoding="utf-8", newline="") as f:
    columnas = list(resultados[0].keys())
    escritor = csv.DictWriter(f, fieldnames=columnas)
    escritor.writeheader()
    escritor.writerows(resultados)

print("\n========== RESULTADOS ==========")

for lugar in resultados:
    alerta = (
        "ALERTA >500m"
        if lugar["distancia_nodo_m"] > 500
        else "DISTANCIA <=500m"
    )

    print(
        f"{lugar['osm_id']} | "
        f"{lugar['nombre_osm']} | "
        f"{lugar['latitud']}, {lugar['longitud']} | "
        f"{lugar['distancia_nodo_m']} m | "
        f"{alerta}"
    )

print("\nArchivo:", SALIDA)
print("Total de polígonos localizados:", len(resultados))
