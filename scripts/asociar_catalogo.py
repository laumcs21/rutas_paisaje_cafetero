"""R1: valida catálogo real, proyecta UTM 18N y asigna nodo vial más cercano."""
from pathlib import Path
from rutas.procesamiento import asociar_lugares
from rutas.grafos import cargar_grafo

BASE=Path(__file__).resolve().parents[1]

if __name__=='__main__':
    grafo=BASE/'datos/real/red.graphml'
    plantilla=BASE/'datos/real/catalogo_plantilla.csv'
    salida=BASE/'datos/real/lugares.csv'
    filas=asociar_lugares(cargar_grafo(grafo),plantilla,salida)
    print(f'Guardados {len(filas)} lugares en {salida}')
    print('Más de 500 m del nodo vial:',sum(f['distancia_nodo_m']>500 for f in filas))
