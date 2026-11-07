"""TSP dirigido/asimétrico con fuerza bruta, Held-Karp y vecino más cercano propios."""
from __future__ import annotations
import math
import time
from .modelos import ResultadoTSP

Matriz = dict[str, dict[str, float]]


def _validar(matriz: Matriz, inicio: str, visitas: list[str]) -> None:
    if len(set([inicio] + visitas)) != len(visitas) + 1:
        raise ValueError('El inicio y las visitas deben ser lugares distintos')
    for u in [inicio] + visitas:
        for v in [inicio] + visitas:
            if u not in matriz or v not in matriz[u]:
                raise ValueError(f'Falta tiempo {u}->{v} en matriz')
            w = float(matriz[u][v])
            if math.isnan(w) or w < 0:
                raise ValueError('TSP no acepta tiempos negativos o NaN')


def costo_recorrido(matriz: Matriz, ruta: list[str]) -> float:
    return sum(matriz[u][v] for u, v in zip(ruta, ruta[1:]))


def tsp_fuerza_bruta(matriz: Matriz, inicio: str, visitas: list[str], tiempo_limite_s: float | None = None) -> ResultadoTSP:
    """Enumera todas las permutaciones con backtracking PROPIO, sin librería TSP.

    No poda ramas: la búsqueda es realmente exhaustiva. O(k · k!) tiempo,
    O(k) espacio auxiliar; comprueba el tiempo tras cada 1024 recorridos.
    """
    _validar(matriz, inicio, visitas)
    k = len(visitas)
    if not k:
        return ResultadoTSP(0.0, [inicio, inicio], 1)
    mejor = math.inf
    mejor_ruta: list[str] = []
    ruta_actual = [inicio]
    estados = 0
    comienzo = time.perf_counter()

    def explorar(actual: str, mascara: int, acumulado: float) -> None:
        nonlocal mejor, mejor_ruta, estados
        if mascara == (1 << k) - 1:
            estados += 1
            if tiempo_limite_s is not None and estados % 1024 == 0 and time.perf_counter() - comienzo > tiempo_limite_s:
                raise TimeoutError(f'Fuerza bruta superó {tiempo_limite_s} s para k={k}')
            total = acumulado + matriz[actual][inicio]
            if total < mejor:
                mejor = total
                mejor_ruta = ruta_actual.copy() + [inicio]
            return
        for j, siguiente in enumerate(visitas):
            if not (mascara & (1 << j)):
                ruta_actual.append(siguiente)
                explorar(siguiente, mascara | (1 << j), acumulado + matriz[actual][siguiente])
                ruta_actual.pop()

    explorar(inicio, 0, 0.0)
    return ResultadoTSP(mejor, mejor_ruta, estados)


def tsp_held_karp(matriz: Matriz, inicio: str, visitas: list[str]) -> ResultadoTSP:
    """DP (máscara,último) = costo óptimo desde inicio visitando máscara y terminando allí.

    DP({j},j)=d(inicio,j).
    DP(S,j)=min_{i en S\\{j}} [DP(S\\{j},i)+d(i,j)].
    Opt=min_j DP(Todos,j)+d(j,inicio). O(k² 2^k) tiempo; O(k 2^k) memoria.
    """
    _validar(matriz, inicio, visitas)
    k=len(visitas)
    if k==0:
        return ResultadoTSP(0.0,[inicio,inicio],1)
    dp: dict[tuple[int,int],float] = {}
    anterior: dict[tuple[int,int],int] = {}
    for j in range(k):
        dp[(1<<j,j)]=matriz[inicio][visitas[j]]
    for mask in range(1,1<<k):
        if (mask & (mask - 1)) == 0:
            continue
        for j in range(k):
            if not mask & (1<<j):
                continue
            prev_mask=mask ^ (1<<j)
            mejores = ((dp[(prev_mask,i)]+matriz[visitas[i]][visitas[j]],i)
                       for i in range(k) if prev_mask & (1<<i) and (prev_mask,i) in dp)
            costo, ultimo = min(mejores,default=(math.inf,-1))
            if math.isfinite(costo):
                dp[(mask,j)]=costo
                anterior[(mask,j)]=ultimo
    completo=(1<<k)-1
    mejor, ultimo = min(((dp.get((completo,j),math.inf)+matriz[visitas[j]][inicio],j)
                         for j in range(k)),default=(math.inf,-1))
    if not math.isfinite(mejor):
        return ResultadoTSP(math.inf,[],len(dp))
    m=completo
    orden=[]
    while m:
        orden.append(visitas[ultimo])
        previo=anterior.get((m,ultimo),-1)
        m ^= 1<<ultimo
        ultimo=previo
    return ResultadoTSP(mejor,[inicio,*reversed(orden),inicio],len(dp))


def tsp_vecino_cercano(matriz: Matriz, inicio: str, visitas: list[str]) -> ResultadoTSP:
    """Voraz determinista; NO garantiza óptimo en TSP (a diferencia de Dijkstra)."""
    _validar(matriz, inicio, visitas)
    pendientes=set(visitas)
    ruta=[inicio]
    while pendientes:
        destino = min(pendientes, key=lambda v: (matriz[ruta[-1]][v],v))
        ruta.append(destino)
        pendientes.remove(destino)
    ruta.append(inicio)
    return ResultadoTSP(costo_recorrido(matriz,ruta),ruta,len(visitas))


def brecha_porcentaje(aproximado: float, optimo: float) -> float:
    if optimo == 0:
        return 0.0 if aproximado == 0 else math.inf
    return 100*(aproximado-optimo)/optimo


def duracion_itinerario(matriz: Matriz, ruta: list[str], duraciones_min: dict[str,float], limite_h: float = 11) -> dict:
    viaje_s = costo_recorrido(matriz,ruta)
    visitas_s = sum(duraciones_min.get(n,0)*60 for n in ruta[1:-1])
    return {'viaje_s':viaje_s,'visitas_s':visitas_s,'total_s':viaje_s+visitas_s,
            'cabe': viaje_s+visitas_s <= limite_h*3600,
            'limite_h': limite_h}
