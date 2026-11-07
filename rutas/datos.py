"""Entrada/salida de catálogo, matrices y GeoJSON. Sin supuestos sobre nombres de lugares."""
from __future__ import annotations
import csv
import json
import math
from pathlib import Path
from .modelos import Lugar

CATEGORIAS = {
    'cabecera_municipal': 12,
    'atractivo_turistico': 15,
    'finca_hotel_rural': 8,
    'acopio_trilladora': 5,
}
CAMPOS = ['id','nombre','municipio','categoria','latitud','longitud','visita_min','nodo_id','distancia_nodo_m','fuente','estado']


def leer_lugares(ruta: str | Path, verificar_minimos: bool = False) -> list[Lugar]:
    lugares = []
    with open(ruta,encoding='utf-8-sig',newline='') as f:
        for n,fila in enumerate(csv.DictReader(f),start=2):
            try:
                lugares.append(Lugar(
                    id=fila['id'].strip(),nombre=fila['nombre'].strip(),municipio=fila['municipio'].strip(),
                    categoria=fila['categoria'].strip(),latitud=float(fila['latitud']),
                    longitud=float(fila['longitud']),nodo_id=int(fila['nodo_id']),
                    visita_min=float(fila.get('visita_min') or 0),
                    distancia_nodo_m=float(fila.get('distancia_nodo_m') or 0),
                ))
            except (KeyError,ValueError,TypeError) as e:
                raise ValueError(f'Fila {n} sin datos completos en {ruta}: {e}') from e
    ids=[x.id for x in lugares]
    if len(ids)!=len(set(ids)):
        raise ValueError('Existen identificadores de lugar repetidos')
    if verificar_minimos:
        from collections import Counter
        conteo=Counter(l.categoria for l in lugares)
        errores=[f'{cat} necesita {minimo}; encontrados {conteo[cat]}' for cat,minimo in CATEGORIAS.items() if conteo[cat] < minimo]
        if errores:
            raise ValueError('Catálogo incompleto: '+'; '.join(errores))
    return lugares


def guardar_lugares(ruta: str | Path, registros: list[dict]) -> None:
    Path(ruta).parent.mkdir(parents=True, exist_ok=True)
    with open(ruta,'w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=CAMPOS,extrasaction='ignore')
        writer.writeheader()
        writer.writerows(registros)


def leer_matriz(ruta: str | Path) -> dict[str,dict[str,float]]:
    with open(ruta,encoding='utf-8-sig',newline='') as f:
        lector=csv.DictReader(f)
        nombres=lector.fieldnames[1:]
        matriz={fila[lector.fieldnames[0]]: {k:float(fila[k]) for k in nombres} for fila in lector}
    return matriz


def guardar_matriz(ruta: str | Path, matriz: dict[str,dict[str,float]]) -> None:
    ids=list(matriz)
    Path(ruta).parent.mkdir(parents=True,exist_ok=True)
    with open(ruta,'w',encoding='utf-8',newline='') as f:
        writer=csv.writer(f)
        writer.writerow(['id',*ids])
        for u in ids:
            writer.writerow([u,*[f'{matriz[u][v]:.8f}' for v in ids]])


def guardar_json(ruta: str | Path, objeto) -> None:
    Path(ruta).parent.mkdir(parents=True,exist_ok=True)
    Path(ruta).write_text(json.dumps(objeto,ensure_ascii=False,indent=2,allow_nan=False,default=str),encoding='utf-8')


def catalogo_a_filas(lugares: list[Lugar]) -> list[dict]:
    return [vars(l).copy() for l in lugares]


def validar_matriz(matriz: dict[str,dict[str,float]], ids: list[str]) -> None:
    for i in ids:
        for j in ids:
            if i not in matriz or j not in matriz[i] or not math.isfinite(matriz[i][j]) or matriz[i][j]<0:
                raise ValueError(f'Matriz inválida: {i} -> {j}')
