"""Experimentación R2-R4, mediana de 5 ejecuciones y CSV/PNG replicables.

Uso: python -m scripts.experimentos --modo demo
     python -m scripts.experimentos --modo real --limite-s 300
"""
from __future__ import annotations
import argparse
import csv
import json
import math
import platform
import random
import statistics
import sys
from pathlib import Path
import numpy as np
from scipy.spatial import ConvexHull
from rutas.grafos import cargar_grafo,lista_adyacencia
from rutas.datos import leer_lugares,leer_matriz,guardar_json
from rutas.dijkstra import dijkstra_heap,dijkstra_lineal
from rutas.envolvente import quickhull,verificar_con_scipy
from rutas.medicion import medir
from rutas.procesamiento import puntos_utm_de_grafo
from rutas.tsp import tsp_fuerza_bruta,tsp_held_karp,tsp_vecino_cercano,brecha_porcentaje,duracion_itinerario

BASE=Path(__file__).resolve().parents[1]
RESULTADOS=BASE/'experimentos/resultados'
GRAFICAS=BASE/'experimentos/graficas'
SEMILLA=2026


def guardar_csv(nombre,filas,cabeceras):
    RESULTADOS.mkdir(parents=True,exist_ok=True)
    with open(RESULTADOS/nombre,'w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=cabeceras,extrasaction='ignore')
        w.writeheader();w.writerows(filas)


def grafica_xy(filas,campo_x,campo_y,campo_grupo,nombre,xlabel,ylabel):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    if not filas:
        return
    GRAFICAS.mkdir(parents=True,exist_ok=True)
    fig,ax=plt.subplots(figsize=(8,4.5))
    for grupo in sorted(set(str(f[campo_grupo]) for f in filas)):
        s=[f for f in filas if str(f[campo_grupo])==grupo and f.get(campo_y) not in ('no_completada',None,'')]
        if not s:continue
        s=sorted(s,key=lambda f:float(f[campo_x]))
        ax.plot([float(f[campo_x]) for f in s],[float(f[campo_y]) for f in s],marker='o',label=grupo)
    ax.set_xlabel(xlabel);ax.set_ylabel(ylabel)
    ax.grid(alpha=.3);ax.legend();fig.tight_layout()
    fig.savefig(GRAFICAS/nombre,dpi=170);plt.close(fig)


def pares_prueba(lugares):
    """10 cercanos + 10 diversos, pares distintos; semilla y selección reproducibles."""
    pares=[]
    for a in lugares:
        for b in lugares:
            if a.id==b.id:continue
            distancia=(a.latitud-b.latitud)**2+(a.longitud-b.longitud)**2
            pares.append((distancia,a,b))
    pares.sort(key=lambda x:(x[0],x[1].id,x[2].id))
    cercanos=pares[:10]
    ya={(a.id,b.id) for _,a,b in cercanos}
    lejanos=[]
    for dist,a,b in reversed(pares):
        if (a.id,b.id) not in ya:
            lejanos.append((dist,a,b));ya.add((a.id,b.id))
        if len(lejanos)==10:break
    return cercanos+lejanos


def r2(g,lugares,limite_s):
    adj=lista_adyacencia(g)
    filas=[];cocientes=[]
    for i,(_,a,b) in enumerate(pares_prueba(lugares)):
        heap=medir(dijkstra_heap,adj,a.nodo_id,b.nodo_id)
        if not math.isfinite(heap.resultado.costo):
            raise ValueError(f'Sin ruta en la componente: {a.nombre}->{b.nombre}')
        filas.append({'origen':a.id,'destino':b.id,'version':'cola_prioridad',
                      'tiempo_viaje_s':round(heap.resultado.costo,7),
                      'nodos_explorados':heap.resultado.explorados,
                      'tiempo_ms':round(heap.mediana_ms,6)})
        if i<10:
            try:
                linea=medir(dijkstra_lineal,adj,a.nodo_id,b.nodo_id,tiempo_limite_s=limite_s)
                if not math.isclose(linea.resultado.costo,heap.resultado.costo,rel_tol=1e-8,abs_tol=1e-6):
                    raise AssertionError(f'Dijkstra lineal discrepa para {a.id}->{b.id}')
                filas.append({'origen':a.id,'destino':b.id,'version':'lineal',
                              'tiempo_viaje_s':round(linea.resultado.costo,7),
                              'nodos_explorados':linea.resultado.explorados,
                              'tiempo_ms':round(linea.mediana_ms,6)})
                if heap.mediana_ms>0:
                    cocientes.append(linea.mediana_ms/heap.mediana_ms)
            except TimeoutError:
                filas.append({'origen':a.id,'destino':b.id,'version':'lineal',
                              'tiempo_viaje_s':'no_completada','nodos_explorados':'no_completada',
                              'tiempo_ms':'no_completada'})
    guardar_csv('r2_dijkstra.csv',filas,['origen','destino','version','tiempo_viaje_s','nodos_explorados','tiempo_ms'])
    guardar_json(RESULTADOS/'r2_cocientes.json',{'mediana':statistics.median(cocientes) if cocientes else None,
        'minimo':min(cocientes) if cocientes else None,'maximo':max(cocientes) if cocientes else None,
        'cantidad_comparables':len(cocientes)})
    # El anexo exige tiempos frente a número de nodos explorados (dispersión).
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(8,5))
    for version in ('lineal','cola_prioridad'):
        validos=[x for x in filas if x['version']==version and isinstance(x['tiempo_ms'],float)]
        if validos:
            ax.scatter([x['nodos_explorados'] for x in validos],[x['tiempo_ms'] for x in validos],label=version)
    ax.set_xlabel('Nodos explorados');ax.set_ylabel('Tiempo del algoritmo (ms)')
    ax.legend();ax.grid(alpha=.3);fig.tight_layout();fig.savefig(GRAFICAS/'r2_dijkstra.png',dpi=170);plt.close(fig)
    return filas


def r3(g):
    rng=np.random.default_rng(SEMILLA)
    datasets=[('Nodos de la red',puntos_utm_de_grafo(g))]
    for n in (1000,10000,50000):
        ar=rng.integers(0,1_000_000,size=(n,2),dtype=np.int64)
        datasets.append((f'Cuadrado {n:,}',list(set(map(tuple,ar.tolist())))))
    filas=[]
    for nombre,puntos in datasets:
        propios=medir(quickhull,puntos)
        # Preparación de matriz NumPy fuera de la medición.
        array=np.asarray(puntos,dtype=np.float64)
        scipy_m=medir(ConvexHull,array)
        if set(propios.resultado)!={tuple(map(int,array[i])) for i in scipy_m.resultado.vertices}:
            raise AssertionError(f'Envolvente propia no coincide con SciPy para {nombre}')
        filas.append({'conjunto':nombre,'n':len(puntos),'vertices':len(propios.resultado),
                      'tiempo_propio_ms':round(propios.mediana_ms,6),
                      'tiempo_scipy_ms':round(scipy_m.mediana_ms,6),
                      'cociente':round(propios.mediana_ms/scipy_m.mediana_ms,5) if scipy_m.mediana_ms else ''})
        print('R3',nombre,'OK')
    guardar_csv('r3_envolvente.csv',filas,['conjunto','n','vertices','tiempo_propio_ms','tiempo_scipy_ms','cociente'])
    gfilas=[]
    for f in filas:
        for variante,campo in [('QuickHull propio','tiempo_propio_ms'),('SciPy Qhull','tiempo_scipy_ms')]:
            gfilas.append({'n':f['n'],'tiempo_ms':f[campo],'version':variante})
    grafica_xy(gfilas,'n','tiempo_ms','version','r3_envolvente.png','Puntos únicos (n)','Tiempo (ms)')
    return filas


def r4(matriz,lugares,limite_s):
    disponibles=[l.id for l in lugares if l.id!='M01']
    inicio='M01' if 'M01' in matriz else lugares[0].id
    disponibles=[l.id for l in lugares if l.id!=inicio]
    rng=random.Random(SEMILLA)
    exactos=[]
    for k in range(5,13):
        elegidos=rng.sample(disponibles,k)
        hk=medir(tsp_held_karp,matriz,inicio,elegidos)
        try:
            bf=medir(tsp_fuerza_bruta,matriz,inicio,elegidos,tiempo_limite_s=limite_s)
            if not math.isclose(hk.resultado.costo,bf.resultado.costo,rel_tol=1e-9,abs_tol=1e-6):
                raise AssertionError(f'Difieren resultados exactos para k={k}')
            tiempo_bf=round(bf.mediana_ms,6)
        except TimeoutError:
            tiempo_bf='no_completada'
        exactos.append({'k':k,'tiempo_fuerza_bruta_ms':tiempo_bf,
                        'tiempo_held_karp_ms':round(hk.mediana_ms,6),'costo_optimo_s':round(hk.resultado.costo,5)})
        print('R4 k=',k,'fuerza bruta=',tiempo_bf,'Held-Karp=',round(hk.mediana_ms,3),'ms')
        if tiempo_bf=='no_completada':break
    guardar_csv('r4_exactos.csv',exactos,['k','tiempo_fuerza_bruta_ms','tiempo_held_karp_ms','costo_optimo_s'])
    gra=[]
    for e in exactos:
        for version,cam in [('Fuerza bruta','tiempo_fuerza_bruta_ms'),('Held-Karp','tiempo_held_karp_ms')]:
            gra.append({'k':e['k'],'ms':e[cam],'version':version})
    grafica_xy(gra,'k','ms','version','r4_exactos.png','Número de destinos (k)','Tiempo (ms)')
    calidad=[]
    for k in (5,8,10,12):
        brechas=[]
        for _ in range(5):
            elegidos=rng.sample(disponibles,k)
            hk=tsp_held_karp(matriz,inicio,elegidos)
            greedy=tsp_vecino_cercano(matriz,inicio,elegidos)
            brechas.append(brecha_porcentaje(greedy.costo,hk.costo))
        calidad.append({'k':k,'instancias':5,'brecha_promedio_pct':round(statistics.mean(brechas),5),
                        'brecha_maxima_pct':round(max(brechas),5)})
    guardar_csv('r4_calidad.csv',calidad,['k','instancias','brecha_promedio_pct','brecha_maxima_pct'])
    atr=[l for l in lugares if l.categoria=='atractivo_turistico']
    elegido=[l.id for l in atr[:8]]
    dur={l.id:l.visita_min for l in lugares}
    retirados=[]
    while elegido:
        optimo=tsp_held_karp(matriz,inicio,elegido)
        resumen=duracion_itinerario(matriz,optimo.ruta,dur)
        if resumen['cabe']:break
        # Criterio explícito: visita que más minutos ahorra incluyendo su desvío en la ruta actual.
        ahorros=[]
        for i in range(1,len(optimo.ruta)-1):
            prev,actual,post=optimo.ruta[i-1:i+2]
            ahorro=(matriz[prev][actual]+matriz[actual][post]-matriz[prev][post])/60+dur[actual]
            ahorros.append((ahorro,actual))
        ahorro,quitar=max(ahorros)
        retirados.append({'id':quitar,'criterio':'mayor ahorro marginal estimado en minutos',
                          'ahorro_estimado_min':round(ahorro,3)})
        elegido.remove(quitar)
    filas=[];acumulado_s=0
    for posicion,lugar in enumerate(optimo.ruta):
        desplazamiento_s=matriz[optimo.ruta[posicion-1]][lugar] if posicion else 0
        visita_s=0 if posicion==0 or posicion==len(optimo.ruta)-1 else dur[lugar]*60
        acumulado_s+=desplazamiento_s+visita_s
        filas.append({'orden':posicion,'lugar':lugar,'desplazamiento_min':round(desplazamiento_s/60,2),
                      'visita_min':round(visita_s/60,2),'tiempo_acumulado_h':round(acumulado_s/3600,3)})
    guardar_csv('r4_itinerario.csv',filas,['orden','lugar','desplazamiento_min','visita_min','tiempo_acumulado_h'])
    guardar_json(RESULTADOS/'r4_itinerario_resumen.json',{'inicio':inicio,'retirados':retirados,
        'total_visitas_min':round(resumen['visitas_s']/60,2),
        'total_desplazamientos_min':round(resumen['viaje_s']/60,2),
        'total_jornada_h':round(resumen['total_s']/3600,3),'cabe_11h':resumen['cabe']})
    return exactos,calidad


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--modo',choices=['demo','real'],default='demo')
    p.add_argument('--limite-s',type=float,default=5.0,
                   help='Límite por ejecución exacta/lineal. Para evaluación final usar 300. Default 5, prueba rápida.')
    args=p.parse_args()
    GRAFICAS.mkdir(parents=True,exist_ok=True)
    carpeta=BASE/'datos'/args.modo
    print('MODO',args.modo,'NO PRESENTAR RESULTADOS DEMO COMO REALES')
    g=cargar_grafo(carpeta/'red.graphml')
    lugares=leer_lugares(carpeta/'lugares.csv',verificar_minimos=True)
    matriz=leer_matriz(carpeta/'matriz_tiempos.csv')
    guardar_json(RESULTADOS/'entorno.json',{
        'modo':args.modo,'advertencia':'Resultados DEMO sintéticos' if args.modo=='demo' else 'Red OSM real',
        'procesador':platform.processor() or platform.machine(),'ram_gb':'COMPLETAR SEGUN EQUIPO',
        'sistema':platform.platform(),'python':sys.version,'semilla':SEMILLA,
        'repeticiones':5,'limite_s':args.limite_s,
        'nota':'Solo mide algoritmos; carga de datos, inicialización de experimentos y gráficas excluidas'})
    print('R2...');r2(g,lugares,args.limite_s)
    print('R3...');r3(g)
    print('R4...');r4(matriz,lugares,args.limite_s)
    print('Resultados en',RESULTADOS,'y',GRAFICAS)

if __name__=='__main__':main()
