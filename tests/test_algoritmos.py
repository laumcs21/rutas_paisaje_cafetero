import itertools
import math
import random
import networkx as nx
import numpy as np
import pytest
from scipy.spatial import ConvexHull
from rutas.grafos import lista_adyacencia,estimar_memoria_estructuras,coordenadas_ruta
from rutas.dijkstra import dijkstra_heap,dijkstra_lineal
from rutas.envolvente import quickhull,verificar_con_scipy
from rutas.tsp import (tsp_held_karp,tsp_fuerza_bruta,tsp_vecino_cercano,
                       brecha_porcentaje,duracion_itinerario)


def grafo_prueba():
    g=nx.MultiDiGraph()
    for n,xy in [(0,(0,0)),(1,(1,0)),(2,(2,0)),(3,(2,1)),(4,(0,2))]:
        g.add_node(n,x=xy[0],y=xy[1])
    for u,v,w in [(0,1,5),(0,2,99),(1,2,4),(2,3,1),(0,3,20),(3,0,30),(2,1,3),(1,0,2),
                  (3,1,8),(0,1,9)]:
        g.add_edge(u,v,travel_time=w)
    return g


def test_dijkstra_heap_lineal_y_networkx():
    g=grafo_prueba();adj=lista_adyacencia(g)
    for s in (0,1,2,3):
        for t in (0,1,2,3):
            a=dijkstra_heap(adj,s,t)
            b=dijkstra_lineal(adj,s,t)
            oracle=nx.shortest_path_length(g,s,t,weight='travel_time')  # SOLO verificación
            assert math.isclose(a.costo,oracle)
            assert math.isclose(b.costo,oracle)
            assert a.ruta[0]==s and a.ruta[-1]==t
            assert a.explorados<=len(adj)


def test_dijkstra_origen_inalcanzable_y_matriz():
    adj=lista_adyacencia(grafo_prueba())
    assert dijkstra_heap(adj,0,4).ruta==[]
    assert math.isinf(dijkstra_lineal(adj,0,4).costo)
    result=dijkstra_heap(adj,0,destino=None)
    assert result.distancias[3]==10
    assert dijkstra_heap(adj,0,0).ruta==[0]


def test_multiaristas_peso_y_geometria():
    g=grafo_prueba()
    assert dict(lista_adyacencia(g)[0])[1]==5
    assert coordenadas_ruta(g,[0,1])==[(0,0),(0,1)]
    with pytest.raises(ValueError):
        g.add_edge(3,4,travel_time=-1)
        lista_adyacencia(g)


def test_quickhull_cuadrado_colineales():
    pts=[(0,0),(10,0),(10,10),(0,10),(5,5),(3,0),(7,0),(10,5),(5,10),(0,7),(0,0)]
    esperado={(0,0),(10,0),(10,10),(0,10)}
    assert set(quickhull(pts))==esperado
    assert quickhull([(3,3),(1,1),(2,2),(3,3)])==[(1,1),(3,3)]
    assert quickhull([])==[]


@pytest.mark.parametrize('semilla',[1,7,42,2026])
def test_quickhull_con_scipy(semilla):
    rng=np.random.default_rng(semilla)
    pts=[tuple(map(int,p)) for p in rng.integers(0,2000,size=(300,2))]
    propios=quickhull(pts)
    assert verificar_con_scipy(pts,propios)
    assert len(propios)==len(set(propios))


def matriz_tsp_de_prueba():
    return {'A':{'A':0,'B':1,'C':9,'D':5},
            'B':{'A':7,'B':0,'C':2,'D':8},
            'C':{'A':4,'B':7,'C':0,'D':3},
            'D':{'A':1,'B':2,'C':8,'D':0}}


def test_held_karp_vs_bruta_asimetrico():
    m=matriz_tsp_de_prueba()
    a=tsp_fuerza_bruta(m,'A',['B','C','D'])
    b=tsp_held_karp(m,'A',['B','C','D'])
    assert a.costo==b.costo
    assert a.ruta[0]=='A' and a.ruta[-1]=='A'
    assert set(b.ruta[1:-1])=={'B','C','D'}
    assert a.costo==7  # A-B=1, B-C=2, C-D=3, D-A=1


def test_held_karp_random_vs_bruta():
    rng=random.Random(45)
    for n in (3,4,5,6):
        ids=[f'p{i}' for i in range(n)]
        m={u:{v:(0 if u==v else rng.randint(1,50)) for v in ids} for u in ids}
        hk=tsp_held_karp(m,ids[0],ids[1:])
        brute=tsp_fuerza_bruta(m,ids[0],ids[1:])
        assert hk.costo==brute.costo


def test_vecino_cercano_no_siempre_optimo():
    # Ejemplo con costos dirigidos positivos: el voraz elige B localmente,
    # pero el óptimo visita C primero.
    m={'A':{'A':0,'B':1,'C':2},'B':{'A':1,'B':0,'C':100},'C':{'A':2,'B':1,'C':0}}
    vor=tsp_vecino_cercano(m,'A',['B','C'])
    opt=tsp_held_karp(m,'A',['B','C'])
    assert vor.costo==103
    assert opt.costo==4
    assert brecha_porcentaje(vor.costo,opt.costo)>0


def test_itinerario_y_memoria():
    m=matriz_tsp_de_prueba()
    x=duracion_itinerario(m,['A','B','C','D','A'],{'B':30,'C':45,'D':25})
    assert x['viaje_s']==7
    assert x['visitas_s']==6000
    assert x['cabe']
    y=estimar_memoria_estructuras(1000,2000)
    assert y['matriz_mb']>y['listas_mb']
