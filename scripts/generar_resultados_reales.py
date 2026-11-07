"""R2+R3: calcula matriz de tiempos y envolvente a partir de red y catálogo REALES."""
from pathlib import Path
from rutas.grafos import cargar_grafo,lista_adyacencia
from rutas.datos import leer_lugares,guardar_matriz
from rutas.procesamiento import matriz_tiempos,puntos_utm_de_grafo,guardar_envolvente_geojson

BASE=Path(__file__).resolve().parents[1]

if __name__=='__main__':
    raiz=BASE/'datos/real'
    g=cargar_grafo(raiz/'red.graphml')
    lugares=leer_lugares(raiz/'lugares.csv',verificar_minimos=True)
    print(f'Calculando la matriz {len(lugares)} x {len(lugares)} con Dijkstra propio...')
    matriz=matriz_tiempos(lista_adyacencia(g),lugares)
    guardar_matriz(raiz/'matriz_tiempos.csv',matriz)
    print('Matriz guardada.')
    hull=guardar_envolvente_geojson(puntos_utm_de_grafo(g),raiz/'envolvente.geojson')
    print(f'Envolvente guardada: {len(hull)} vértices')
