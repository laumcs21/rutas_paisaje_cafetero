"""Modelos pequeños para no acoplar los algoritmos a la interfaz."""
from dataclasses import dataclass, field
from typing import Hashable

Nodo = Hashable


@dataclass
class ResultadoRuta:
    costo: float
    ruta: list[Nodo]
    explorados: int
    distancias: dict[Nodo, float] = field(default_factory=dict)
    anteriores: dict[Nodo, Nodo] = field(default_factory=dict)


@dataclass
class ResultadoTSP:
    costo: float
    ruta: list[str]
    estados: int = 0


@dataclass
class Lugar:
    id: str
    nombre: str
    municipio: str
    categoria: str
    latitud: float
    longitud: float
    nodo_id: int
    visita_min: float = 0.0
    distancia_nodo_m: float = 0.0

    @property
    def etiqueta(self) -> str:
        return f"{self.nombre} [{self.id}]"
