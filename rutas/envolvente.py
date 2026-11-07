"""QuickHull propio: divide y vencerás, coordenadas enteras y sin colineales intermedios.

Costo esperado aproximado O(n log n), peor caso O(n²). La selección de puntos
por lado y su recombinación es recursiva; SciPy solo valida el resultado.
"""
from __future__ import annotations
from typing import Iterable

Punto = tuple[int, int]


def giro(a: Punto, b: Punto, p: Punto) -> int:
    return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])


def quickhull(puntos: Iterable[tuple[int, int]]) -> list[Punto]:
    puntos = sorted(set((int(x), int(y)) for x,y in puntos))
    if len(puntos) <= 2:
        return puntos
    a,b = puntos[0],puntos[-1]
    if not any(giro(a,b,p) for p in puntos):
        return [a,b]  # Puntos colineales: conservar solo extremos.

    def partir(inicio: Punto, fin: Punto, candidatos: list[Punto]) -> list[Punto]:
        if not candidatos:
            return []
        p = max(candidatos, key=lambda q: (giro(inicio, fin, q), -q[0], -q[1]))
        izq = [q for q in candidatos if giro(inicio,p,q) > 0]
        der = [q for q in candidatos if giro(p,fin,q) > 0]
        return partir(inicio,p,izq) + [p] + partir(p,fin,der)

    arriba = [p for p in puntos if giro(a,b,p) > 0]
    abajo = [p for p in puntos if giro(b,a,p) > 0]
    return [a] + partir(a,b,arriba) + [b] + partir(b,a,abajo)


def verificar_con_scipy(puntos: Iterable[Punto], propios: list[Punto]) -> bool:
    from scipy.spatial import ConvexHull
    pts = sorted(set(puntos))
    if len(pts) <= 2 or not any(giro(pts[0],pts[-1],p) for p in pts):
        return set(propios) == {pts[0], pts[-1]} if pts else propios == []
    hull = ConvexHull(pts)
    return set(propios) == {pts[i] for i in hull.vertices}
