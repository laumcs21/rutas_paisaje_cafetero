"""Estructuras para grafos dirigidos con aristas paralelas y pesos positivos."""
from __future__ import annotations
import math
from pathlib import Path
import networkx as nx
from .modelos import Nodo


def lista_adyacencia(g: nx.MultiDiGraph, peso: str = "travel_time") -> dict[Nodo, list[tuple[Nodo, float]]]:
    """Conserva para cada (u,v) la arista de menor peso; respeta el sentido de las vías.

    NetworkX se utiliza como contenedor/formato, NO para calcular rutas.
    """
    adj: dict[Nodo, dict[Nodo, float]] = {u: {} for u in g.nodes}
    for u, v, datos in g.edges(data=True):
        w = float(datos[peso])
        if not math.isfinite(w) or w < 0:
            raise ValueError(f"Peso inválido en {u}->{v}: {w}")
        adj[u][v] = min(w, adj[u].get(v, math.inf))
    return {u: list(vecinos.items()) for u, vecinos in adj.items()}


def cargar_grafo(ruta: str | Path) -> nx.MultiDiGraph:
    ruta = Path(ruta)
    if not ruta.exists():
        raise FileNotFoundError(f"Falta {ruta}. Ejecuta generar_demo.py o preparar_red_real.py")
    if ruta.suffix != '.graphml':
        raise ValueError('El grafo debe ser GraphML')
    # OSMnx restaura correctamente los atributos geométricos y numéricos de OpenStreetMap.
    if 'datos/real' in ruta.as_posix().replace('\\', '/'):
        try:
            import osmnx as ox
            g = ox.io.load_graphml(filepath=ruta)
        except ImportError as e:
            raise RuntimeError('Instala requirements.txt para leer el grafo real.') from e
    else:
        g = nx.read_graphml(ruta, node_type=int, force_multigraph=True)
    if not isinstance(g, nx.MultiDiGraph):
        g = nx.MultiDiGraph(g)
    for _, _, d in g.edges(data=True):
        for campo in ('travel_time','length','speed_kph'):
            if campo in d:
                d[campo] = float(d[campo])
    return g


def estimar_memoria_estructuras(v: int, e: int, bytes_celda: int = 8, bytes_vecino: int = 24) -> dict:
    """Estimación teórica con supuestos explícitos, no medición del heap de Python."""
    if v < 0 or e < 0:
        raise ValueError('V y E deben ser no negativos')
    return {
        'V': v, 'E': e,
        'matriz_mb': v * v * bytes_celda / 1_000_000,
        'listas_mb': (v * 8 + e * bytes_vecino) / 1_000_000,
        'supuestos': f'{bytes_celda} B/celda; 8 B/cabecera de nodo; {bytes_vecino} B/entrada (destino, peso, referencia)'
    }


def coordenadas_ruta(g: nx.MultiDiGraph, ruta: list[Nodo]) -> list[tuple[float, float]]:
    """Devuelve [(lat,lon)] siguiendo la geometría OSM de cada tramo si existe."""
    salida: list[tuple[float, float]] = []
    if not ruta:
        return salida
    for u, v in zip(ruta, ruta[1:]):
        aristas = g.get_edge_data(u, v)
        if not aristas:
            raise ValueError(f'La ruta contiene tramo inexistente: {u}->{v}')
        d = min(aristas.values(), key=lambda a: float(a.get('travel_time', math.inf)))
        geo = d.get('geometry')
        if geo is not None:
            if isinstance(geo, str):
                from shapely import wkt
                geo = wkt.loads(geo)
            xs = list(geo.coords)
            uxy = (float(g.nodes[u]['x']),float(g.nodes[u]['y']))
            if sum((xs[0][j]-uxy[j])**2 for j in (0,1)) > sum((xs[-1][j]-uxy[j])**2 for j in (0,1)):
                xs.reverse()
            coords = [(float(y),float(x)) for x,y in xs]
        else:
            coords = [(float(g.nodes[n]['y']),float(g.nodes[n]['x'])) for n in (u, v)]
        salida.extend(coords if not salida else coords[1:])
    if len(ruta) == 1:
        u = ruta[0]
        salida = [(float(g.nodes[u]['y']),float(g.nodes[u]['x']))]
    return salida
