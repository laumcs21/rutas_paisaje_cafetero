# SDD · R5 Aplicación
**Entrada:** grafo y catálogo válidos, matriz, envolvente precomputada y archivos de experimento.
**Salida:** mapa de camino origen-destino con tiempo, polígono, itinerario de 6 a 8 atractivos con Held-Karp/heurística, diferencia porcentual, tablas y gráficas de R1-R4.
**Reglas:** rutas e itinerarios se calculan en el momento, no se sustituyen por un resultado estático. Diferenciar demo sintética de real. La aplicación debe ejecutarse localmente vía README.
**Casos:** origen=destino, ruta no encontrada, selección de menos de 6, comparación de costos y jornada >11h, datos faltantes.
