"""Experimentos DEFINITIVOS de R3 y R4 sin repetir R1/R2.

Uso final: python -m scripts.experimentos_r3_r4 --parte ambos --modo real
Prueba breve: python -m scripts.experimentos_r3_r4 --parte r4 --max-k 7 --limite-s 5

Los archivos DEMO y REAL quedan separados. Todas las mediciones se realizan
excluyendo lectura de archivos, creación de entradas, CSV y gráficas.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import platform
import random
import statistics
import sys
from pathlib import Path

import networkx as nx
import numpy as np
from scipy.spatial import ConvexHull

from rutas.datos import leer_lugares, leer_matriz, guardar_json
from rutas.envolvente import quickhull
from rutas.medicion import medir
from rutas.procesamiento import puntos_utm_de_grafo, guardar_envolvente_geojson
from rutas.tsp import (
    brecha_porcentaje,
    costo_recorrido,
    duracion_itinerario,
    tsp_fuerza_bruta,
    tsp_held_karp,
    tsp_vecino_cercano,
)

BASE = Path(__file__).resolve().parents[1]
SEMILLA = 2026


def guardar_csv(ruta: Path, filas: list[dict], campos: list[str]) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=campos, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(filas)


def medir_5(func, *args, repeticiones: int, **kwargs):
    """Mantiene regla: mediana de 5; una sola si alguna toma >60 s."""
    return medir(func, *args, repeticiones=repeticiones, **kwargs)


def graficar_r3(filas: list[dict], ruta: Path) -> None:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(8.5, 5))
    for label, campo in [('QuickHull propio', 'tiempo_propio_ms'), ('SciPy (Qhull)', 'tiempo_scipy_ms')]:
        s = sorted(filas, key=lambda r: r['n'])
        ax.plot([r['n'] for r in s], [r[campo] for r in s], marker='o', label=label)
    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.set_xlabel('Número de puntos únicos (n)')
    ax.set_ylabel('Mediana del tiempo (ms)')
    ax.set_title('R3 · Envolvente convexa: implementación propia vs SciPy')
    ax.legend()
    ax.grid(alpha=.25)
    fig.tight_layout()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(ruta, dpi=180)
    plt.close(fig)


def ejecutar_r3(datos: Path, resultados: Path, graficas: Path, repeticiones: int) -> None:
    """La proyección y las entradas aleatorias se preparan FUERA del cronómetro."""
    print('\n[R3] Leyendo coordenadas de red GraphML sin descargar OSM...')
    grafo = nx.read_graphml(datos / 'red.graphml', node_type=int, force_multigraph=True)
    puntos_red = sorted(puntos_utm_de_grafo(grafo))
    if not puntos_red:
        raise ValueError('La red no contiene coordenadas válidas')
    # El algoritmo de generación GeoJSON también verifica que hay >=3 extremos.
    hull_geo = guardar_envolvente_geojson(puntos_red, datos / 'envolvente.geojson')
    print(f'[R3] {grafo.number_of_nodes()} nodos -> {len(puntos_red)} puntos UTM únicos -> {len(hull_geo)} vértices')

    rng = np.random.default_rng(SEMILLA)
    conjuntos = [('Nodos de la red', puntos_red)]
    for n in (1000, 10000, 50000):
        xy = rng.integers(0, 1_000_000, size=(n, 2), dtype=np.int64)
        conjuntos.append((f'Cuadrado, {n:,} puntos', sorted(set(map(tuple, xy.tolist())))))

    filas = []
    detalles = []
    for nombre, puntos in conjuntos:
        # Matriz SciPy y deduplicación ya están preparadas antes de cronometrar.
        matriz = np.asarray(puntos, dtype=np.float64)
        propios = medir_5(quickhull, puntos, repeticiones=repeticiones)
        referencia = medir_5(ConvexHull, matriz, repeticiones=repeticiones)
        indices = referencia.resultado.vertices
        vertices_scipy = {tuple(map(int, matriz[i])) for i in indices}
        vertices_propios = set(propios.resultado)
        if vertices_propios != vertices_scipy:
            diferencia = vertices_propios.symmetric_difference(vertices_scipy)
            raise AssertionError(f'R3 difiere de SciPy en {nombre}; {len(diferencia)} vértices')
        filas.append({
            'conjunto': nombre,
            'n': len(puntos),
            'vertices': len(vertices_propios),
            'tiempo_propio_ms': round(propios.mediana_ms, 6),
            'tiempo_scipy_ms': round(referencia.mediana_ms, 6),
            'cociente': round(propios.mediana_ms / referencia.mediana_ms, 5) if referencia.mediana_ms else '',
            'verificacion': 'OK',
        })
        detalles.append({
            'conjunto': nombre,
            'n': len(puntos),
            'repeticiones_propio_ms': propios.repeticiones_ms,
            'repeticiones_scipy_ms': referencia.repeticiones_ms,
            'vertices_coinciden': True,
        })
        print(f'[R3] {nombre}: {len(puntos)} puntos, {len(vertices_propios)} vértices, '
              f'propio={propios.mediana_ms:.3f} ms, SciPy={referencia.mediana_ms:.3f} ms. OK')
    guardar_csv(resultados / 'r3_envolvente.csv', filas,
                ['conjunto', 'n', 'vertices', 'tiempo_propio_ms', 'tiempo_scipy_ms', 'cociente', 'verificacion'])
    guardar_json(resultados / 'r3_repeticiones.json', detalles)
    graficar_r3(filas, graficas / 'r3_envolvente.png')


def comprobar_ruta(matriz, inicio: str, destinos: list[str], resultado) -> None:
    ruta = resultado.ruta
    if (len(ruta) != len(destinos) + 2 or ruta[0] != inicio or ruta[-1] != inicio
            or len(set(ruta[1:-1])) != len(destinos) or set(ruta[1:-1]) != set(destinos)):
        raise AssertionError('Recorrido inválido o no circular')
    if not math.isclose(costo_recorrido(matriz, ruta), resultado.costo, rel_tol=1e-9, abs_tol=1e-6):
        raise AssertionError('El costo no coincide con la suma de los tramos')


def graficar_r4(filas: list[dict], ruta: Path) -> None:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(8.5, 5))
    for label, campo in [('Fuerza bruta', 'tiempo_fuerza_bruta_ms'), ('Held-Karp', 'tiempo_held_karp_ms')]:
        validos = [r for r in filas if isinstance(r[campo], (int, float))]
        ax.plot([r['k'] for r in validos], [r[campo] for r in validos], marker='o', label=label)
    ax.set_yscale('log')
    ax.set_xlabel('Cantidad de destinos (k)')
    ax.set_ylabel('Mediana del tiempo (ms) · escala log')
    ax.set_xticks([r['k'] for r in filas])
    ax.set_title('R4 · TSP asimétrico: fuerza bruta y Held-Karp')
    ax.legend()
    ax.grid(alpha=.25)
    fig.tight_layout()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(ruta, dpi=180)
    plt.close(fig)


def seleccionar_itinerario(matriz, lugares: list, inicio: str):
    """Escoge 8 visitas cortas y retira la que más ahorra al recalcular el óptimo.

    No se retiran automáticamente las visitas de un día entero sin justificar;
    se presenta la reducción paso a paso. Mínimo 6 atractivos.
    """
    atractivos = sorted((l for l in lugares if l.categoria == 'atractivo_turistico' and l.id != inicio),
                       key=lambda l: (l.visita_min, l.id))
    if len(atractivos) < 8:
        raise ValueError('Se requieren al menos ocho atractivos turísticos')
    elegidos = [l.id for l in atractivos[:8]]
    visitas = {l.id: l.visita_min for l in lugares}
    retirados = []
    while True:
        opt = tsp_held_karp(matriz, inicio, elegidos)
        comprobar_ruta(matriz, inicio, elegidos, opt)
        resumen = duracion_itinerario(matriz, opt.ruta, visitas)
        if resumen['cabe']:
            return elegidos, opt, resumen, retirados
        if len(elegidos) == 6:
            raise RuntimeError('Ni con seis atractivos seleccionados cabe en 11 h; revisar otra selección')
        candidatos = []
        for atractivo in elegidos:
            resto = [i for i in elegidos if i != atractivo]
            nueva_ruta = tsp_held_karp(matriz, inicio, resto)
            nuevo = duracion_itinerario(matriz, nueva_ruta.ruta, visitas)
            ahorro = (resumen['total_s'] - nuevo['total_s']) / 60
            candidatos.append((ahorro, atractivo, nuevo['total_s'] / 3600))
        ahorro, quitar, horas_restantes = max(candidatos, key=lambda x: (x[0], x[1]))
        retirados.append({'lugar_id': quitar, 'visita_min': visitas[quitar],
                          'motivo': 'Mayor reducción de la jornada tras recalcular Held-Karp',
                          'ahorro_total_min': round(ahorro, 3),
                          'jornada_anterior_h': round(resumen['total_s']/3600, 3),
                          'jornada_restante_h': round(horas_restantes, 3)})
        elegidos.remove(quitar)


def ejecutar_r4(datos: Path, resultados: Path, graficas: Path,
                repeticiones: int, limite_s: float, max_k: int) -> None:
    matriz = leer_matriz(datos / ('matriz_tiempos_40x40.csv' if datos.name == 'real' else 'matriz_tiempos.csv'))
    lugares = leer_lugares(datos / 'lugares.csv', verificar_minimos=True)
    inicio = 'M01' if 'M01' in matriz else lugares[0].id
    disponibles = [l.id for l in lugares if l.id != inicio]
    print(f'\n[R4] Origen {inicio}; matriz {len(matriz)}×{len(matriz)}; límite por ejecución {limite_s}s')

    exactos = []
    detalles = []
    bf_detenida = False
    for k in range(5, max_k+1):
        # Cada k tiene su semilla propia para que la muestra no cambie al reanudar.
        elegidos = random.Random(SEMILLA + k).sample(disponibles, k)
        medicion_hk = medir_5(tsp_held_karp, matriz, inicio, elegidos, repeticiones=repeticiones)
        comprobar_ruta(matriz, inicio, elegidos, medicion_hk.resultado)
        tiempo_bf: float | str = 'no_completada' if bf_detenida else ''
        bf_reps = []
        if not bf_detenida:
            try:
                med_bf = medir_5(tsp_fuerza_bruta, matriz, inicio, elegidos,
                                 tiempo_limite_s=limite_s, repeticiones=repeticiones)
                comprobar_ruta(matriz, inicio, elegidos, med_bf.resultado)
                if not math.isclose(med_bf.resultado.costo, medicion_hk.resultado.costo,
                                    rel_tol=1e-9, abs_tol=1e-6):
                    raise AssertionError(f'Fuerza bruta y Held-Karp no coinciden en k={k}')
                tiempo_bf = round(med_bf.mediana_ms, 6)
                bf_reps = med_bf.repeticiones_ms
            except TimeoutError:
                bf_detenida = True
                tiempo_bf = 'no_completada'
        exactos.append({'k': k, 'tiempo_fuerza_bruta_ms': tiempo_bf,
                        'tiempo_held_karp_ms': round(medicion_hk.mediana_ms, 6),
                        'costo_optimo_s': round(medicion_hk.resultado.costo, 6),
                        'fuerza_bruta_estado': 'OK' if isinstance(tiempo_bf, (float, int)) else 'no_completada'})
        detalles.append({'k': k, 'origen': inicio, 'destinos': elegidos,
                         'ruta_held_karp': medicion_hk.resultado.ruta,
                         'repeticiones_held_karp_ms': medicion_hk.repeticiones_ms,
                         'repeticiones_fuerza_bruta_ms': bf_reps,
                         'fuerza_bruta_completada': isinstance(tiempo_bf, (float, int))})
        print(f'[R4] k={k}: HK={medicion_hk.mediana_ms:.3f} ms, fuerza bruta={tiempo_bf}')

    guardar_csv(resultados/'r4_exactos.csv', exactos,
                ['k', 'tiempo_fuerza_bruta_ms', 'tiempo_held_karp_ms', 'costo_optimo_s', 'fuerza_bruta_estado'])
    guardar_json(resultados/'r4_exactos_detalle.json', detalles)
    graficar_r4(exactos, graficas/'r4_exactos.png')

    calidad = []
    instancias = []
    contraejemplo = None
    for k in (5, 8, 10, 12):
        rng = random.Random(SEMILLA + 1000 + k)
        brechas = []
        for i in range(1, 6):
            elegidos = rng.sample(disponibles, k)
            opt = tsp_held_karp(matriz, inicio, elegidos)
            voraz = tsp_vecino_cercano(matriz, inicio, elegidos)
            comprobar_ruta(matriz, inicio, elegidos, opt)
            comprobar_ruta(matriz, inicio, elegidos, voraz)
            if voraz.costo + 1e-6 < opt.costo:
                raise AssertionError('La heurística es menor que la ruta exacta; error de implementación')
            brecha = brecha_porcentaje(voraz.costo, opt.costo)
            brechas.append(brecha)
            instancias.append({'k':k,'instancia':i,'destinos': '|'.join(elegidos),
                               'costo_held_karp_s':round(opt.costo,6),
                               'costo_voraz_s':round(voraz.costo,6),
                               'brecha_pct':round(brecha,6)})
            if contraejemplo is None and brecha > 1e-8:
                contraejemplo = {'origen':inicio,'k':k,'destinos':elegidos,
                                 'ruta_optima':opt.ruta,'costo_optimo_s':opt.costo,
                                 'ruta_voraz':voraz.ruta,'costo_voraz_s':voraz.costo,
                                 'brecha_pct':brecha}
        calidad.append({'k':k,'instancias':len(brechas),
                        'brecha_promedio_pct':round(statistics.mean(brechas),6),
                        'brecha_maxima_pct':round(max(brechas),6)})
        print(f'[R4] Calidad k={k}: brecha media={statistics.mean(brechas):.2f}% '
              f'máxima={max(brechas):.2f}%')
    guardar_csv(resultados/'r4_calidad.csv', calidad,
                ['k','instancias','brecha_promedio_pct','brecha_maxima_pct'])
    guardar_csv(resultados/'r4_calidad_instancias.csv', instancias,
                ['k','instancia','destinos','costo_held_karp_s','costo_voraz_s','brecha_pct'])
    if contraejemplo is not None:
        guardar_json(resultados/'r4_contraejemplo.json', contraejemplo)

    elegidos, opt, resumen, retirados = seleccionar_itinerario(matriz, lugares, inicio)
    por_id = {l.id:l for l in lugares}
    duraciones = {l.id:l.visita_min for l in lugares}
    filas = []
    acumulado_s = 0.0
    for i, lugar in enumerate(opt.ruta):
        desplazamiento_s = matriz[opt.ruta[i-1]][lugar] if i else 0.0
        visita_min = duraciones.get(lugar,0.0) if 0 < i < len(opt.ruta)-1 else 0.0
        acumulado_s += desplazamiento_s + visita_min * 60
        filas.append({'orden':'Salida' if i==0 else ('Regreso' if i==len(opt.ruta)-1 else i),
                      'lugar_id':lugar, 'lugar':por_id[lugar].nombre,
                      'desplazamiento_min':round(desplazamiento_s/60,3),
                      'visita_min':visita_min,
                      'tiempo_acumulado_h':round(acumulado_s/3600,3)})
    guardar_csv(resultados/'r4_itinerario.csv', filas,
                ['orden','lugar_id','lugar','desplazamiento_min','visita_min','tiempo_acumulado_h'])
    guardar_json(resultados/'r4_itinerario_resumen.json', {
        'inicio':inicio,
        'criterio_inicial':'Ocho atractivos con menor duración de visita; empate por identificador',
        'destinos_iniciales':[l.id for l in sorted(
            [l for l in lugares if l.categoria=='atractivo_turistico'],key=lambda l:(l.visita_min,l.id))[:8]],
        'destinos_finales':elegidos,
        'ruta':opt.ruta,
        'retirados':retirados,
        'total_visitas_min':round(resumen['visitas_s']/60,3),
        'total_desplazamientos_min':round(resumen['viaje_s']/60,3),
        'total_jornada_h':round(resumen['total_s']/3600,4),
        'cabe_11h':bool(resumen['cabe'])
    })
    print(f'[R4] Itinerario: {len(elegidos)} atractivos, {resumen["total_s"]/3600:.3f} h, '
          f'retirados={len(retirados)}, cabe en 11 h={resumen["cabe"]}')


def main() -> None:
    p = argparse.ArgumentParser(description='R3 y R4 reales, sin tocar R1/R2')
    p.add_argument('--modo', choices=('demo','real'), default='real')
    p.add_argument('--parte', choices=('r3','r4','ambos'), default='ambos')
    p.add_argument('--limite-s', type=float, default=300.0)
    p.add_argument('--max-k', type=int, default=12, help='Prueba rápida: 6 o 7; final: 12')
    p.add_argument('--repeticiones', type=int, default=5)
    args = p.parse_args()
    if args.max_k < 5 or args.max_k > 12 or args.repeticiones < 1 or args.limite_s <= 0:
        p.error('Se requiere 5 <= max-k <= 12, repeticiones >= 1, limite-s > 0')
    datos = BASE/'datos'/args.modo
    resultados = BASE/'experimentos/resultados'/args.modo
    graficas = BASE/'experimentos/graficas'/args.modo
    resultados.mkdir(parents=True, exist_ok=True)
    graficas.mkdir(parents=True, exist_ok=True)
    guardar_json(resultados/'entorno.json', {
        'modo': args.modo,
        'advertencia': 'DEMOSTRACIÓN SINTÉTICA, NO usar para informe real' if args.modo=='demo'
                       else 'Datos reales del proyecto (red OSM y matriz calculada)',
        'procesador': platform.processor() or platform.machine(),
        'sistema_operativo': platform.platform(),
        'python': sys.version.split()[0],
        'semilla': SEMILLA,
        'repeticiones': args.repeticiones,
        'limite_s': args.limite_s,
        'max_k': args.max_k,
        'definitivo': bool(args.modo == 'real' and args.max_k==12 and args.repeticiones==5
                          and args.limite_s==300),
        'nota': 'Mediciones del algoritmo; sin lectura, generación de entradas, escritura y gráficas',
        'ram_gb': 'COMPLETAR CON RAM DEL EQUIPO QUE EJECUTA',
    })
    if args.parte in ('r3','ambos'):
        ejecutar_r3(datos, resultados, graficas, args.repeticiones)
    if args.parte in ('r4','ambos'):
        ejecutar_r4(datos, resultados, graficas, args.repeticiones, args.limite_s, args.max_k)
    print(f'\nResultados: {resultados}\nGráficas: {graficas}')


if __name__ == '__main__':
    main()
