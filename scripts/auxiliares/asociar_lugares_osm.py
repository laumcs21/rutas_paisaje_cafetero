import csv
import math
from pathlib import Path

import osmnx as ox
from scipy.spatial import cKDTree
from pyproj import Transformer

BASE = Path("datos/real")
CATALOGO = BASE / "catalogo_plantilla.csv"
CANDIDATOS = BASE / "candidatos_osm.csv"
GRAFO = BASE / "red.graphml"
SALIDA = BASE / "catalogo_preliminar_osm.csv"

# Coordenadas aproximadas utilizadas para desambiguar
# los centros urbanos, no para reemplazar los datos OSM.
CENTROS = {
    "M01": (4.5363, -75.6724),
    "M02": (4.3599, -75.7387),
    "M03": (4.5306, -75.6406),
    "M04": (4.6201, -75.6348),
    "M05": (4.3901, -75.6858),
    "M06": (4.6751, -75.6580),
    "M07": (4.2064, -75.7905),
    "M08": (4.4512, -75.7887),
    "M09": (4.5664, -75.7507),
    "M10": (4.3341, -75.7038),
    "M11": (4.6225, -75.7631),
    "M12": (4.6373, -75.5698),
}

# Nombres que sí identifican un candidato concreto.
NOMBRES = {
    "A04": ["Jardín Botánico del Quindío"],
    "A05": ["Museo del Oro Quimbaya"],
    "A06": ["Parque Los Arrieros"],
    "A07": ["RECUCA, Recorrido de la Cultura Cafetera"],
    "A08": ["Parque de La Vida"],
    "A09": ["Colina Iluminada"],
    "A10": ["La granja de mamá lulú"],
    "A14": ["Calle del tiempo detenido"],
    "A15": ["Parroquia María Inmaculada"],
    "F01": ["Finca El Ocaso"],
    "F02": ["Finca La Morelia"],
}


def leer_csv(ruta):
    with ruta.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def distancia_aproximada_m(a, b):
    lat1, lon1 = a
    lat2, lon2 = b
    factor = math.cos(math.radians((lat1 + lat2) / 2))
    return math.hypot(
        (lat1 - lat2) * 111_320,
        (lon1 - lon2) * 111_320 * factor
    )


catalogo = leer_csv(CATALOGO)
candidatos = leer_csv(CANDIDATOS)

por_id = {}
for candidato in candidatos:
    por_id.setdefault(candidato["id"], []).append(candidato)

print("1. Cargando red vial...")
g = ox.load_graphml(GRAFO)

print("2. Proyectando la red a UTM 18N...")
g_utm = ox.projection.project_graph(
    g,
    to_crs="EPSG:32618"
)

nodos = list(g_utm.nodes)
puntos = [
    (float(g_utm.nodes[n]["x"]), float(g_utm.nodes[n]["y"]))
    for n in nodos
]
arbol = cKDTree(puntos)

transformador = Transformer.from_crs(
    "EPSG:4326",
    "EPSG:32618",
    always_xy=True
)

total_asociados = 0
alertas = 0

print("3. Seleccionando candidatos y buscando nodos...")

for lugar in catalogo:
    identificador = lugar["id"]
    opciones = por_id.get(identificador, [])
    elegido = None

    if identificador in CENTROS:
        centro = CENTROS[identificador]
        municipio = lugar["municipio"].casefold()

        validos = []
        for c in opciones:
            try:
                lat = float(c["latitud"])
                lon = float(c["longitud"])
            except (ValueError, TypeError):
                continue

            nombre = c["nombre_osm"].casefold()

            if nombre != municipio:
                continue

            distancia = distancia_aproximada_m(
                centro, (lat, lon)
            )

            if distancia <= 2000:
                validos.append((distancia, c))

        if validos:
            elegido = min(validos, key=lambda x: x[0])[1]

    elif identificador in NOMBRES:
        esperados = {
            nombre.casefold()
            for nombre in NOMBRES[identificador]
        }

        validos = [
            c for c in opciones
            if (
                c["nombre_osm"].casefold() in esperados
                or (
                    identificador == "A07"
                    and c["nombre_osm"].casefold().startswith("recuca")
                )
            )
            and c["latitud"]
            and c["longitud"]
        ]

        if validos:
            elegido = max(
                validos,
                key=lambda c: float(c["coincidencia"])
            )

    if elegido is None:
        lugar["estado"] = "PENDIENTE_VERIFICACION_OSM"
        continue

    lat = float(elegido["latitud"])
    lon = float(elegido["longitud"])

    x, y = transformador.transform(lon, lat)

    distancia, indice = arbol.query((x, y))
    nodo = nodos[int(indice)]

    lugar["latitud"] = f"{lat:.8f}"
    lugar["longitud"] = f"{lon:.8f}"
    lugar["nodo_id"] = str(nodo)
    lugar["distancia_nodo_m"] = f"{distancia:.2f}"

    referencia = (
        "https://www.openstreetmap.org/"
        f"{elegido['tipo_osm']}/{elegido['osm_id']}"
    )
    lugar["fuente"] = referencia

    if identificador.startswith("M"):
        lugar["estado"] = "CENTRO_URBANO_NO_PLAZA"
    else:
        lugar["estado"] = "CANDIDATO_OSM_NO_VALIDADO"

    if distancia > 500:
        lugar["estado"] += "_DISTANCIA_MAYOR_500M"
        alertas += 1

    total_asociados += 1

with SALIDA.open("w", encoding="utf-8", newline="") as f:
    escritor = csv.DictWriter(
        f,
        fieldnames=list(catalogo[0].keys())
    )
    escritor.writeheader()
    escritor.writerows(catalogo)

print("\nRESULTADOS")
print("Lugares en catálogo:", len(catalogo))
print("Candidatos asociados:", total_asociados)
print("Pendientes:", len(catalogo) - total_asociados)
print("Alertas >500 m:", alertas)
print("Archivo generado:", SALIDA)

print("\nDETALLE")
for lugar in catalogo:
    print(
        f"{lugar['id']:4} | "
        f"{lugar['distancia_nodo_m'] or '-':>9} m | "
        f"{lugar['estado']}"
    )
