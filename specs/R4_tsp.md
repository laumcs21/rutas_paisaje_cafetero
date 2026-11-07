# SDD · R4 TSP asimétrico
**Entrada:** matriz dirigida de tiempos de todos los lugares del catálogo; un origen (Armenia por defecto) y k destinos distintos.
**Salida:** ruta circular óptima o voraz con identificadores de lugares, tiempos de viaje; evaluación de jornada de 11 horas incluyendo visitas.
**Algoritmos propios:** fuerza bruta, Held-Karp con tabla por máscara y predecesores, vecino cercano voraz.
**Casos:** k=0; costos asimétricos; comparar Held-Karp y fuerza bruta; contraejemplo del voraz; verificar recorrido inicial/final idéntico; limitar fuerza bruta a 300 segundos en modo final.
**Mediciones:** k=5..12 o límite; 5 instancias por k en 5/8/10/12 para calidad; reportar % de brecha y tiempos.
