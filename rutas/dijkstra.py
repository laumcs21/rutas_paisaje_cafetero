"""Implementaciones ORIGINALES de Dijkstra; no se invoca nx.shortest_path.

Invariante: al extraer/asentar u con distancia mínima tentativa, su distancia
es la mínima real entre el origen y u (pesos no negativos).
"""
from __future__ import annotations
import heapq
import math
import time
from itertools import count
from .modelos import ResultadoRuta, Nodo


def _armar(salida: Nodo | None, inicio: Nodo, dist: dict, ant: dict, explorados: int) -> ResultadoRuta:
    if salida is None:
        return ResultadoRuta(0.0, [], explorados, dist, ant)
    if math.isinf(dist.get(salida, math.inf)):
        return ResultadoRuta(math.inf, [], explorados, dist, ant)
    camino = [salida]
    while camino[-1] != inicio:
        camino.append(ant[camino[-1]])
    camino.reverse()
    return ResultadoRuta(dist[salida], camino, explorados, dist, ant)


def dijkstra_heap(adj: dict[Nodo, list[tuple[Nodo, float]]], origen: Nodo, destino: Nodo | None = None) -> ResultadoRuta:
    if origen not in adj or (destino is not None and destino not in adj):
        raise ValueError('Origen/destino no pertenece al grafo')
    dist = {origen: 0.0}
    ant: dict[Nodo, Nodo] = {}
    cerrados = set()
    q = count()
    heap = [(0.0, next(q), origen)]
    while heap:
        distancia, _, u = heapq.heappop(heap)
        if u in cerrados:
            continue
        cerrados.add(u)
        if u == destino:
            break
        for v, peso in adj[u]:
            if peso < 0:
                raise ValueError('Dijkstra requiere pesos no negativos')
            nd = distancia + peso
            if nd < dist.get(v, math.inf):
                dist[v] = nd
                ant[v] = u
                heapq.heappush(heap, (nd, next(q), v))
    return _armar(destino, origen, dist, ant, len(cerrados))


def dijkstra_lineal(adj: dict[Nodo, list[tuple[Nodo, float]]], origen: Nodo, destino: Nodo | None = None, tiempo_limite_s: float | None = None) -> ResultadoRuta:
    """Selecciona el mínimo mediante barrido lineal, O(V²+E), muy costoso en red real."""
    if origen not in adj or (destino is not None and destino not in adj):
        raise ValueError('Origen/destino no pertenece al grafo')
    dist = {u: math.inf for u in adj}
    dist[origen] = 0.0
    ant: dict[Nodo, Nodo] = {}
    sin_visitar = set(adj)
    explorados = 0
    comienzo = time.perf_counter()
    while sin_visitar:
        if tiempo_limite_s is not None and explorados % 64 == 0 and time.perf_counter() - comienzo > tiempo_limite_s:
            raise TimeoutError(f"Dijkstra lineal superó {tiempo_limite_s} s")
        u = min(sin_visitar, key=lambda x: dist[x])
        if math.isinf(dist[u]):
            break
        sin_visitar.remove(u)
        explorados += 1
        if u == destino:
            break
        for v, peso in adj[u]:
            if peso < 0:
                raise ValueError('Dijkstra requiere pesos no negativos')
            if v in sin_visitar and dist[u] + peso < dist[v]:
                dist[v] = dist[u] + peso
                ant[v] = u
    return _armar(destino, origen, dist, ant, explorados)
