# SDD · R2 Caminos mínimos
**Entrada:** adyacencia dirigida con pesos en segundos no negativos; origen y destino válidos.
**Salida:** costo mínimo en segundos, camino ordenado, explorados una sola vez.
**Reglas:** dos implementaciones propias, lineal y cola de prioridad; detener al extraer el destino; con `destino=None`, calcular todas las distancias de origen (matriz al menos 40×40).
**Casos:** multiaristas conserva la más barata; ruta inexistente devuelve inf y []; inicio=fin costo 0; rutas dirigidas asimétricas; comparación contra NetworkX **solo en test**.
**Complejidad:** lineal O(V²+E), heap O((V+E) log V).
**Medición:** 20 pares heap, 10 también lineal; gráfica explorados vs tiempo, cociente lineal/heap.
