"""Temporizador estandarizado del documento: sin I/O; mediana de cinco repeticiones."""
from __future__ import annotations
from dataclasses import dataclass
from statistics import median
from time import perf_counter_ns

@dataclass
class Medicion:
    mediana_ms: float
    repeticiones_ms: list[float]
    resultado: object


def medir(funcion, *args, repeticiones: int = 5, **kwargs) -> Medicion:
    tiempos=[]
    resultado=None
    for _ in range(repeticiones):
        antes=perf_counter_ns()
        resultado=funcion(*args,**kwargs)
        ms=(perf_counter_ns()-antes)/1_000_000
        tiempos.append(ms)
        if ms>60_000:  # Una ejecución >1 minuto solo se mide una vez.
            break
    return Medicion(median(tiempos),tiempos,resultado)
