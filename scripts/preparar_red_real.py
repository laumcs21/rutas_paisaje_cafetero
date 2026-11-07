"""R1: descargar red real o cargar GraphML suministrado por el profesor."""
import argparse
from pathlib import Path
from rutas.procesamiento import preparar_grafo_real,medir_componentes_radios

BASE=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description='Descarga y prepara la red vial del Quindío (requiere conexión)')
    p.add_argument('--entrada',help='GraphML existente, evita descargar el departamento')
    p.add_argument('--medir-radios',action='store_true',help='Mide SCC en radios 2/5/10/20 km y departamento')
    p.add_argument('--plaza-lat',type=float,help='Latitud verificada de la plaza Bolívar de Armenia')
    p.add_argument('--plaza-lon',type=float,help='Longitud verificada de la plaza Bolívar de Armenia')
    args=p.parse_args()
    ruta=BASE/'datos/real/red.graphml'
    res=preparar_grafo_real(ruta,args.entrada)
    print('Red real preparada:',res)
    if args.medir_radios:
        if args.plaza_lat is None or args.plaza_lon is None:
            p.error('Para --medir-radios indica --plaza-lat y --plaza-lon verificadas')
        resultados=medir_componentes_radios(args.plaza_lat,args.plaza_lon,BASE/'experimentos/resultados/r1_componentes.csv')
        print('Radios medidos:',resultados)

if __name__=='__main__':main()
