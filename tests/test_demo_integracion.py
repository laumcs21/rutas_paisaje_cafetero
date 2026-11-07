from pathlib import Path
import math
from rutas.datos import leer_lugares,leer_matriz,validar_matriz
from rutas.grafos import cargar_grafo,lista_adyacencia
from rutas.dijkstra import dijkstra_heap
from rutas.tsp import tsp_held_karp,tsp_fuerza_bruta
from rutas.procesamiento import puntos_utm_de_grafo
from rutas.envolvente import quickhull,verificar_con_scipy

BASE=Path(__file__).resolve().parents[1]
DEMO=BASE/'datos/demo'


def test_demo_integral():
    g=cargar_grafo(DEMO/'red.graphml')
    lugares=leer_lugares(DEMO/'lugares.csv',verificar_minimos=True)
    m=leer_matriz(DEMO/'matriz_tiempos.csv')
    assert len(lugares)==40
    assert g.number_of_nodes()==64
    validar_matriz(m,[l.id for l in lugares])
    adj=lista_adyacencia(g)
    for x,y in ((lugares[0],lugares[10]),(lugares[7],lugares[19]),(lugares[31],lugares[2])):
        r=dijkstra_heap(adj,x.nodo_id,y.nodo_id)
        assert math.isclose(r.costo,m[x.id][y.id],rel_tol=1e-8,abs_tol=1e-5)
    pts=puntos_utm_de_grafo(g)
    assert verificar_con_scipy(pts,quickhull(pts))
    visitas=[l.id for l in lugares if l.categoria=='atractivo_turistico'][:6]
    assert math.isclose(tsp_fuerza_bruta(m,'M01',visitas).costo,
                        tsp_held_karp(m,'M01',visitas).costo)
