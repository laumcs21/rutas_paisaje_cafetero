"""Experimento R1: componentes fuertemente conexas en cuatro radios y la red completa."""
import argparse
from pathlib import Path
from rutas.procesamiento import medir_componentes_radios
import osmnx as ox

ox.settings.log_console = True
ox.settings.use_cache = True
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--plaza-lat', type=float, required=True)
    parser.add_argument('--plaza-lon', type=float, required=True)
    args = parser.parse_args()

    base = Path(__file__).resolve().parents[1]
    destino = base / 'resultados/r1_componentes/mediciones_radios.csv'

    resultados = medir_componentes_radios(
        args.plaza_lat,
        args.plaza_lon,
        destino
    )

    for fila in resultados:
        print(fila)

    print(f'\nResultados guardados en: {destino}')