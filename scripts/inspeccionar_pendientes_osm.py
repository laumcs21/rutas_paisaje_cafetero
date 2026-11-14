import re
import unicodedata
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

ARCHIVO = Path("datos/real/quindio_completo.osm")

BUSQUEDAS = {
    "PANACA": ["panaca"],
    "VALLE_COCORA": ["cocora"],
    "BAMBU_GUADUA": ["bambu", "guadua"],
    "BARBAS_BREMEN": ["barbas", "bremen"],
    "LOS_NEVADOS": ["nevados"],
    "COOPERATIVAS_CAFE": [
        "cooperativa de caficultores",
        "cooperativa de cafeteros",
        "punto de compra",
        "compra de cafe",
        "centro de acopio",
        "trilladora",
        "almacafe",
    ],
}

LIMITE = 15


def normalizar(texto):
    texto = unicodedata.normalize("NFKD", texto or "")
    texto = "".join(
        c for c in texto if not unicodedata.combining(c)
    )
    return re.sub(r"\s+", " ", texto.lower()).strip()


resultados = defaultdict(list)

print("Buscando etiquetas en el OSM original...", flush=True)

contexto = ET.iterparse(
    ARCHIVO,
    events=("start", "end")
)

_, raiz = next(contexto)

for evento, elemento in contexto:
    if evento != "end":
        continue

    if elemento.tag not in ("node", "way", "relation"):
        continue

    tags = {
        t.get("k"): t.get("v")
        for t in elemento.findall("tag")
    }

    nombre = (
        tags.get("name")
        or tags.get("official_name")
        or tags.get("alt_name")
        or ""
    )

    if nombre:
        nombre_normalizado = normalizar(nombre)

        for grupo, palabras in BUSQUEDAS.items():
            if len(resultados[grupo]) >= LIMITE:
                continue

            if any(
                palabra in nombre_normalizado
                for palabra in palabras
            ):
                resultados[grupo].append({
                    "nombre": nombre,
                    "tipo": elemento.tag,
                    "id": elemento.get("id"),
                    "lat": elemento.get("lat", ""),
                    "lon": elemento.get("lon", ""),
                    "turismo": tags.get("tourism", ""),
                    "amenity": tags.get("amenity", ""),
                    "shop": tags.get("shop", ""),
                    "direccion": (
                        tags.get("addr:street", "")
                        + " "
                        + tags.get("addr:housenumber", "")
                    ).strip(),
                })

    raiz.clear()

for grupo in BUSQUEDAS:
    print(f"\n========== {grupo} ==========")

    encontrados = resultados[grupo]

    if not encontrados:
        print("Sin coincidencias")
        continue

    for lugar in encontrados:
        print(
            f"{lugar['nombre']} | "
            f"{lugar['tipo']} {lugar['id']} | "
            f"{lugar['lat']}, {lugar['lon']} | "
            f"tourism={lugar['turismo']} | "
            f"amenity={lugar['amenity']} | "
            f"shop={lugar['shop']} | "
            f"direccion={lugar['direccion']}"
        )

print("\nBÚSQUEDA TERMINADA")
