# SDD · R1 Modelo de la red vial
**Entrada:** red de OSMnx o GraphML externo y archivo CSV de 40 lugares verificados.
**Salida:** componente fuertemente conexa, tiempos no negativos, catálogo con nodos cercanos, resumen, tabla de radios y datos reutilizables.
**Reglas:** usar EPSG:32618 para proximidad Euclidiana, informar casos >500 m, retener sentidos de las calles y aristas paralelas, separar descarga de medición. `speed_kph` faltantes se imputan por tipo con parámetros documentados. No inventar posiciones.
**Casos:** componente aislada eliminada; un sitio remoto reportado; coordenada vacía rechazada; 40 categorías mínimas verificadas; Grafo de salida conectado en ambos sentidos.
**Complejidad:** SCC O(V+E); matriz V² vs listas V+E (estimadas bajo supuestos).
