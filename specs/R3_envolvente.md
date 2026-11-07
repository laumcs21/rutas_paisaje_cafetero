# SDD · R3 Envolvente convexa
**Entrada:** nodos viales WGS84; conversión a UTM zona 18N, enteros redondeados sin duplicados.
**Salida:** vértices extremos del polígono convexo en orden; excluir interiores y colineales de los lados.
**Algoritmo propio:** QuickHull: dividir puntos a un lado de la recta entre dos extremos; elegir el más alejado; recursión sobre dos segmentos y combinar.
**Casos:** cuadrado con puntos interiores, coordenadas duplicadas, todos colineales, puntos aleatorios de tamaño fijo, vértices idénticos a SciPy.
**Medición:** red real y 1000/10000/50000 puntos aleatorios con semilla 2026; medianas de 5.
