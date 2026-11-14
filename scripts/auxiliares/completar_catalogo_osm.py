import csv
from pathlib import Path

import osmnx as ox
from pyproj import Transformer
from scipy.spatial import cKDTree

base = Path("datos/real")
entrada = base / "catalogo_preliminar_osm.csv"
candidatos_ruta = base / "candidatos_osm.csv"
salida = base / "catalogo_ampliado_osm.csv"
direcciones_salida = base / "direcciones_centros_cafe.csv"

selecciones = {
    "A01": ("A01", "Parqueadero Parque del Café", None),
    "A07": ("A07", "RECUCA, Recorrido de la Cultura Cafetera.", None),

    "F03": ("F03", "Finca Hotel La Pradera", "Finca Hotel La Pradera"),
    "F04": ("F03", "Finca Hotel La Tata", "Finca Hotel La Tata"),
    "F05": ("F08", "Finca Hotel La Cuyabrita", "Finca Hotel La Cuyabrita"),
    "F06": ("F06", "Finca Hotel La Esperanza", "Finca Hotel La Esperanza"),
    "F07": ("F07", "Finca Cafetera La Granada", "Finca Cafetera La Granada"),
    "F08": ("F08", "Finca Hotel La Carmelita", "Finca Hotel La Carmelita"),
}

direcciones = {
    "C01": ("Armenia", "Carrera 18 # 51-26"),
    "C02": ("Calarcá", "Carrera 28 con Calle 36, esquina"),
    "C03": ("Quimbaya", "Carrera 2 entre calles 20 y 21"),
    "C04": ("Filandia", "Carrera 6 # 7-31, Edificio del Café"),
    "C05": ("Génova", "Calle 30 # 10-20"),
}

fuente_cafe = (
    "https://federaciondecafeteros.org/wp-content/"
    "uploads/2026/02/92-Publicacio%CC%81n-compradores-"
    "autorizados-MECIC-01082024.pdf"
)

def leer(ruta):
    with ruta.open(encoding="utf-8", newline="") as f:
        lector = csv.DictReader(f)
        return list(lector), lector.fieldnames

catalogo, columnas = leer(entrada)
candidatos, _ = leer(candidatos_ruta)

print("Cargando grafo y coordenadas UTM 18N...")
g = ox.load_graphml(base / "red.graphml")
g = ox.projection.project_graph(g, to_crs="EPSG:32618")

nodos = list(g.nodes)
posiciones = [
    (float(g.nodes[n]["x"]), float(g.nodes[n]["y"]))
    for n in nodos
]
arbol = cKDTree(posiciones)

proyector = Transformer.from_crs(
    "EPSG:4326", "EPSG:32618", always_xy=True
)

actualizados = []

for lugar in catalogo:
    identificador = lugar["id"]

    if identificador in selecciones:
        origen_id, nombre_osm, nuevo_nombre = selecciones[identificador]

        coincidencias = [
            c for c in candidatos
            if c["id"] == origen_id
            and c["nombre_osm"] == nombre_osm
            and c["latitud"] and c["longitud"]
        ]

        if not coincidencias:
            raise RuntimeError(
                f"No se encontró la referencia OSM para {identificador}: "
                f"{nombre_osm}"
            )

        candidato = coincidencias[0]
        lat = float(candidato["latitud"])
        lon = float(candidato["longitud"])

        x, y = proyector.transform(lon, lat)
        distancia, indice = arbol.query((x, y))

        if nuevo_nombre:
            lugar["nombre"] = nuevo_nombre

        lugar["latitud"] = f"{lat:.8f}"
        lugar["longitud"] = f"{lon:.8f}"
        lugar["nodo_id"] = str(nodos[int(indice)])
        lugar["distancia_nodo_m"] = f"{distancia:.2f}"

        lugar["fuente"] = (
            "https://www.openstreetmap.org/"
            f"{candidato['tipo_osm']}/{candidato['osm_id']}"
        )

        if identificador == "A01":
            estado = "PARQUEADERO_CANDIDATO_VERIFICAR_ENTRADA"
        else:
            estado = "CANDIDATO_OSM_NO_VALIDADO"

        if distancia > 500:
            estado += "_DISTANCIA_MAYOR_500M"

        lugar["estado"] = estado
        actualizados.append(identificador)

    if identificador in direcciones:
        municipio, direccion = direcciones[identificador]
        lugar["nombre"] = (
            f"Punto de compra Cooperativa de Caficultores "
            f"del Quindío - {municipio}"
        )
        lugar["municipio"] = municipio
        lugar["fuente"] = fuente_cafe
        lugar["estado"] = "DIRECCION_DOCUMENTADA_SIN_COORDENADAS"

with salida.open("w", encoding="utf-8", newline="") as f:
    escritor = csv.DictWriter(f, fieldnames=columnas)
    escritor.writeheader()
    escritor.writerows(catalogo)

with direcciones_salida.open(
    "w", encoding="utf-8", newline=""
) as f:
    escritor = csv.writer(f)
    escritor.writerow(["id", "municipio", "direccion", "fuente"])
    for identificador, (municipio, direccion) in direcciones.items():
        escritor.writerow([
            identificador, municipio, direccion, fuente_cafe
        ])

asociados = sum(
    bool(lugar["nodo_id"])
    for lugar in catalogo
)

print("\nRESULTADOS")
print("Total de lugares:", len(catalogo))
print("Ubicaciones candidatas asociadas:", asociados)
print("Pendientes de coordenadas:", len(catalogo) - asociados)
print("Incorporados en este paso:", ", ".join(actualizados))
print("Archivo:", salida)
print("Direcciones cafeteras:", direcciones_salida)

print("\nDETALLE DE LAS INCORPORACIONES")
for lugar in catalogo:
    if lugar["id"] in actualizados:
        print(
            lugar["id"],
            "|", lugar["nombre"],
            "|", lugar["distancia_nodo_m"], "m",
            "|", lugar["estado"]
        )
