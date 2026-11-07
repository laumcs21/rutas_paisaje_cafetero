"""Experimento R1: redes de radio 2,5,10,20 km y departamento completo."""
import argparse
from pathlib import Path
from rutas.procesamiento import medir_componentes_radios

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--plaza-lat',type=float,required=True,help='Latitud verificada de Plaza Bolívar Armenia')
    parser.add_argument('--plaza-lon',type=float,required=True,help='Longitud verificada de Plaza Bolívar Armenia')
    args=parser.parse_args()
    destino=Path(__file__).resolve().parents[1]/'experimentos/resultados/r1_componentes.csv'
    print(medir_componentes_radios(args.plaza_lat,args.plaza_lon,destino))
