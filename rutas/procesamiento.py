"""Preparación de red real de OSMnx y asociación geográfica (EPSG:32618)."""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import csv
import math
import time
import networkx as nx
from pyproj import Transformer
from .datos import CATEGORIAS, CAMPOS, guardar_json, guardar_lugares, leer_lugares
from .grafos import estimar_memoria_estructuras, lista_adyacencia
from .dijkstra import dijkstra_heap
from .medicion import medir

EPSG_UTM_18N = 'EPSG:32618'
VELOCIDADES_SUPUESTAS = {
    'motorway':90,'trunk':70,'primary':60,'secondary':50,'tertiary':40,
    'unclassified':30,'residential':25,'living_street':10,'service':15,
}


def preparar_grafo_real(ruta_salida: str | Path, ruta_entrada: str | Path | None = None) -> dict:
    """Descarga si no hay archivo local. Precisa Internet solo en ese caso."""
    import osmnx as ox
    ruta_salida=Path(ruta_salida)
    ruta_salida.parent.mkdir(parents=True,exist_ok=True)
    if ruta_entrada is None:
        g=ox.graph.graph_from_place('Quindío, Colombia',network_type='drive',retain_all=True)
        procedencia='OpenStreetMap mediante OSMnx'
    else:
        g=ox.io.load_graphml(filepath=ruta_entrada)
        procedencia=str(ruta_entrada)
    antes=(g.number_of_nodes(),g.number_of_edges())
    # Es la API exigida por el profesor (aquí NO se requiere implementación propia).
    t0=time.perf_counter()
    g=ox.truncate.largest_component(g,strongly=True)
    tiempo_componente_ms=(time.perf_counter()-t0)*1000
    despues=(g.number_of_nodes(),g.number_of_edges())
    # Los valores personalizados son SUPUESTOS de modelado, no velocidades legales reales.
    # OSMnx aprovecha maxspeed cuando existe e imputa por clase de vía en caso contrario.
    g=ox.routing.add_edge_speeds(g,hwy_speeds=VELOCIDADES_SUPUESTAS,fallback=30)
    g=ox.routing.add_edge_travel_times(g)
    ox.io.save_graphml(g,filepath=ruta_salida)
    resumen={
        'origen':procedencia,'fecha_preparacion_utc':datetime.now(timezone.utc).isoformat(),
        'red_descargada':{'V':antes[0],'E':antes[1]},
        'componente_fuerte':{'V':despues[0],'E':despues[1]},
        'tiempo_componente_ms':tiempo_componente_ms,
        'estimacion_memoria_componente':estimar_memoria_estructuras(*despues),
        'estimacion_memoria_descargada':estimar_memoria_estructuras(*antes),
        'criterio_velocidad':'OSMnx add_edge_speeds: maxspeed OSM cuando está disponible; imputación por highway y fallback 30 km/h; velocidades supuestas, no límites legales',
        'velocidades_supuesto_kmh':VELOCIDADES_SUPUESTAS,
        'version_osmnx':ox.__version__,'version_networkx':nx.__version__,
    }
    guardar_json(ruta_salida.parent/'resumen_red.json',resumen)
    return resumen


def medir_componentes_radios(lat: float, lon: float, salida_csv: str | Path) -> list[dict]:
    """Mide la SCC en cuatro radios y en la red candidata completa."""
    import osmnx as ox

    ruta = Path(salida_csv)
    ruta.parent.mkdir(parents=True, exist_ok=True)

    radios = [2000, 5000, 10000, 20000]
    registros = []

    for r in radios:
        g = ox.graph.graph_from_point(
            (lat, lon),
            dist=r,
            network_type='drive',
            retain_all=True
        )

        medicion = medir(ox.truncate.largest_component, g, strongly=True)
        g_fuerte = medicion.resultado

        registros.append({
            'red': f'Radio {r // 1000} km',
            'V': g.number_of_nodes(),
            'E': g.number_of_edges(),
            'V+E': g.number_of_nodes() + g.number_of_edges(),
            'tiempo_ms': round(medicion.mediana_ms, 6),
            'V_componente': g_fuerte.number_of_nodes(),
            'E_componente': g_fuerte.number_of_edges()
        })

    # Quinto caso: red candidata completa del Quindío
    ruta_grafo = Path(__file__).resolve().parents[1] / 'datos/real/red_candidata.graphml'
    g = ox.load_graphml(ruta_grafo)

    medicion = medir(ox.truncate.largest_component, g, strongly=True)
    gc = medicion.resultado

    registros.append({
        'red': 'Departamento completo',
        'V': g.number_of_nodes(),
        'E': g.number_of_edges(),
        'V+E': g.number_of_nodes() + g.number_of_edges(),
        'tiempo_ms': round(medicion.mediana_ms, 6),
        'V_componente': gc.number_of_nodes(),
        'E_componente': gc.number_of_edges()
    })

    with open(ruta, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=registros[0].keys())
        w.writeheader()
        w.writerows(registros)

    return registros


def asociar_lugares(g: nx.MultiDiGraph, plantilla: str | Path, ruta_salida: str | Path) -> list[dict]:
    """Asocia coordenadas reales verificadas con el nodo vial más cercano usando UTM 18N.

    Se guardan también casos mayores de 500 m: deben documentarse y resolverse manualmente.
    """
    import osmnx as ox
    filas=[]
    with open(plantilla,encoding='utf-8-sig',newline='') as f:
        for linea,fila in enumerate(csv.DictReader(f),start=2):
            if (not fila.get('id') or not fila.get('nombre') or not fila.get('municipio')
                or fila.get('nombre','').startswith('PENDIENTE')):
                raise ValueError(f'Completa nombre/municipio/id en fila {linea}')
            try:
                lat=float(fila['latitud']);lon=float(fila['longitud'])
            except (ValueError,KeyError,TypeError) as exc:
                raise ValueError(f'Completa/valida latitud/longitud en fila {linea}: {fila.get("nombre")}') from exc
            if not (3.5<=lat<=5.5 and -76.5<=lon<=-74.5):
                raise ValueError(f'Coordenadas fuera de rango regional plausible en fila {linea}')
            if fila.get('categoria')=='atractivo_turistico':
                try:
                    if float(fila.get('visita_min') or 0)<=0:
                        raise ValueError()
                except ValueError:
                    raise ValueError(f'El atractivo de fila {linea} necesita visita_min > 0')
            if not fila.get('fuente','').strip():
                raise ValueError(f'Falta fuente o criterio de los datos de la fila {linea}')
            fila['latitud']=lat;fila['longitud']=lon
            filas.append(fila)
    conteos={cat:sum(f['categoria']==cat for f in filas) for cat in CATEGORIAS}
    for cat,minimo in CATEGORIAS.items():
        if conteos[cat]<minimo:
            raise ValueError(f'Catálogo insuficiente {cat}: {conteos[cat]} < {minimo}')
    # Proyectar los nodos y los lugares a la MISMA zona UTM en metros.
    gp=ox.projection.project_graph(g,to_crs=EPSG_UTM_18N)
    transform=Transformer.from_crs('EPSG:4326',EPSG_UTM_18N,always_xy=True)
    xx,yy=transform.transform([f['longitud'] for f in filas],[f['latitud'] for f in filas])
    nodos,dist=ox.distance.nearest_nodes(gp,X=xx,Y=yy,return_dist=True)
    for fila,nodo,metros in zip(filas,nodos,dist):
        fila['nodo_id']=int(nodo)
        fila['distancia_nodo_m']=round(float(metros),2)
        fila['estado']='revisar_si_mas_500m' if metros > 500 else 'asociado'
        if fila['categoria']!='atractivo_turistico' and not fila.get('visita_min'):
            fila['visita_min']=0
    guardar_lugares(ruta_salida,filas)
    guardar_json(Path(ruta_salida).parent/'alertas_nodos_lejanos.json',
                 [{k:f[k] for k in ('id','nombre','distancia_nodo_m','nodo_id')} for f in filas if f['distancia_nodo_m']>500])
    return filas


def matriz_tiempos(adj, lugares):
    """Una ejecución COMPLETA de Dijkstra con heap por cada uno de los >=40 lugares."""
    matriz={}
    for origen in lugares:
        res=dijkstra_heap(adj,origen.nodo_id,destino=None)
        fila={}
        for destino in lugares:
            fila[destino.id] = res.distancias.get(destino.nodo_id,math.inf)
        matriz[origen.id]=fila
    return matriz


def puntos_utm_de_grafo(g: nx.MultiDiGraph) -> list[tuple[int,int]]:
    proj=Transformer.from_crs('EPSG:4326',EPSG_UTM_18N,always_xy=True)
    xs=[float(n['x']) for _,n in g.nodes(data=True)]
    ys=[float(n['y']) for _,n in g.nodes(data=True)]
    xx,yy=proj.transform(xs,ys)
    return list(set((round(x),round(y)) for x,y in zip(xx,yy)))


def guardar_envolvente_geojson(puntos: list[tuple[int,int]], ruta: str | Path):
    from .envolvente import quickhull
    hull=quickhull(puntos)
    if len(hull)<3:
        raise ValueError('No se puede dibujar polígono con menos de 3 vértices')
    transformer=Transformer.from_crs(EPSG_UTM_18N,'EPSG:4326',always_xy=True)
    coord=[list(map(float,transformer.transform(x,y))) for x,y in hull+[hull[0]]]
    geo={'type':'FeatureCollection','features':[{'type':'Feature','properties':{'algoritmo':'QuickHull propio'},
                                                 'geometry':{'type':'Polygon','coordinates':[coord]}}]}
    guardar_json(ruta,geo)
    return hull
