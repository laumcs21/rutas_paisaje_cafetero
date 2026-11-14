import csv
import re
import unicodedata
import xml.etree.ElementTree as ET
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path

ORIGEN = Path("datos/real/quindio_completo.osm")
CATALOGO = Path("datos/real/catalogo_plantilla.csv")
SALIDA = Path("datos/real/candidatos_osm.csv")
MAX_CANDIDATOS = 5


def normalizar(texto):
    texto = unicodedata.normalize("NFKD", texto or "")
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", texto.lower()).strip()


def variantes(lugar):
    nombre = lugar["nombre"]
    municipio = lugar["municipio"]

    if lugar["categoria"] == "cabecera_municipal":
        return [
            nombre,
            "Parque principal de " + municipio,
            "Parque Bolívar de " + municipio,
            "Plaza Bolívar de " + municipio,
            municipio,
        ]

    nombres = [nombre]

    if lugar["id"] == "A07":
        nombres += ["Recorrido de la Cultura Cafetera"]
    if lugar["id"] == "A09":
        nombres += ["Colina Iluminada"]
    if lugar["id"] == "A03":
        nombres += ["Valle del Cocora"]
    if lugar["id"] == "A01":
        nombres += ["Parque del Café"]
    if lugar["id"] == "A02":
        nombres += ["Parque PANACA"]

    return nombres


def similitud(a, b):
    a, b = normalizar(a), normalizar(b)

    if not a or not b:
        return 0.0

    if a == b:
        return 1.0

    puntuacion = SequenceMatcher(None, a, b).ratio()

    if len(a) >= 8 and len(b) >= 8:
        if a in b or b in a:
            puntuacion = max(puntuacion, 0.88)

    return puntuacion


def etiquetas(elemento):
    return {
        t.get("k"): t.get("v")
        for t in elemento.findall("tag")
    }


if not ORIGEN.exists():
    raise SystemExit(f"No existe: {ORIGEN}")

with CATALOGO.open(encoding="utf-8", newline="") as archivo:
    catalogo = list(csv.DictReader(archivo))

mejores = defaultdict(list)

print("Primera lectura: buscando nombres en OpenStreetMap...", flush=True)

contexto = ET.iterparse(ORIGEN, events=("start", "end"))
_, raiz = next(contexto)

for evento, elemento in contexto:
    if evento != "end":
        continue

    if elemento.tag not in ("node", "way"):
        continue

    tags = etiquetas(elemento)
    nombres = [
        valor for clave, valor in tags.items()
        if clave in ("name", "name:es", "official_name", "alt_name")
        and valor
    ]

    if nombres:
        for lugar in catalogo:
            puntuacion = max(
                (similitud(variante, nombre_osm)
                 for variante in variantes(lugar)
                 for nombre_osm in nombres),
                default=0.0
            )

            if puntuacion < 0.65:
                continue

            candidato = {
                "id": lugar["id"],
                "nombre_catalogo": lugar["nombre"],
                "nombre_osm": nombres[0],
                "coincidencia": round(puntuacion, 3),
                "tipo_osm": elemento.tag,
                "osm_id": elemento.get("id"),
                "latitud": elemento.get("lat", ""),
                "longitud": elemento.get("lon", ""),
                "referencias": [
                    nd.get("ref")
                    for nd in elemento.findall("nd")
                ] if elemento.tag == "way" else [],
                "categoria_osm": (
                    tags.get("tourism")
                    or tags.get("amenity")
                    or tags.get("place")
                    or tags.get("leisure")
                    or tags.get("shop")
                    or ""
                ),
            }

            lista = mejores[lugar["id"]]
            lista.append(candidato)
            lista.sort(
                key=lambda c: c["coincidencia"],
                reverse=True
            )
            del lista[MAX_CANDIDATOS:]

    raiz.clear()

referencias = {
    ref
    for lista in mejores.values()
    for candidato in lista
    for ref in candidato["referencias"]
}

print(
    "Segunda lectura: resolviendo",
    len(referencias),
    "nodos de polígonos...",
    flush=True
)

coordenadas = {}

if referencias:
    contexto = ET.iterparse(ORIGEN, events=("start", "end"))
    _, raiz = next(contexto)

    for evento, elemento in contexto:
        if evento != "end":
            continue

        if elemento.tag == "node":
            identificador = elemento.get("id")

            if identificador in referencias:
                coordenadas[identificador] = (
                    float(elemento.get("lat")),
                    float(elemento.get("lon"))
                )

            raiz.clear()
        elif elemento.tag in ("way", "relation"):
            raiz.clear()

for lista in mejores.values():
    for candidato in lista:
        if candidato["tipo_osm"] != "way":
            continue

        puntos = [
            coordenadas[ref]
            for ref in candidato["referencias"]
            if ref in coordenadas
        ]

        if puntos:
            candidato["latitud"] = sum(p[0] for p in puntos) / len(puntos)
            candidato["longitud"] = sum(p[1] for p in puntos) / len(puntos)

columnas = [
    "id", "nombre_catalogo", "nombre_osm",
    "coincidencia", "tipo_osm", "osm_id",
    "latitud", "longitud", "categoria_osm",
    "estado"
]

total = 0

with SALIDA.open("w", encoding="utf-8", newline="") as archivo:
    escritor = csv.DictWriter(archivo, fieldnames=columnas)
    escritor.writeheader()

    for lugar in catalogo:
        candidatos = mejores.get(lugar["id"], [])

        for candidato in candidatos:
            fila = {
                clave: candidato.get(clave, "")
                for clave in columnas
            }
            fila["estado"] = "REVISAR_MANUALMENTE"
            escritor.writerow(fila)
            total += 1

        print(
            f"{lugar['id']}: "
            f"{len(candidatos)} candidatos"
        )

print("\nBúsqueda terminada.")
print("Coincidencias:", total)
print("Archivo:", SALIDA)
print("Las coordenadas son candidatas, no verificadas.")
