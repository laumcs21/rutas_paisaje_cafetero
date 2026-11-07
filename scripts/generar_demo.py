"""Genera datos SINTÉTICOS y reproducibles (jamás presentarlos como OSM reales)."""
import math
from pathlib import Path
import networkx as nx
from rutas.grafos import lista_adyacencia
from rutas.datos import guardar_lugares,guardar_matriz,guardar_json,leer_lugares
from rutas.procesamiento import matriz_tiempos,puntos_utm_de_grafo,guardar_envolvente_geojson

BASE=Path(__file__).resolve().parents[1]
DEMO=BASE/'datos/demo'


def main():
    DEMO.mkdir(parents=True,exist_ok=True)
    g=nx.MultiDiGraph(crs='EPSG:4326',nombre='RED 100% SINTÉTICA NO USAR COMO OSM')
    lado=8
    for i in range(lado):
        for j in range(lado):
            idx=i*lado+j+1
            g.add_node(idx,x=-75.83+j*.020,y=4.42+i*.018)
    for i in range(lado):
        for j in range(lado):
            u=i*lado+j+1
            for di,dj in ((1,0),(0,1)):
                ni,nj=i+di,j+dj
                if ni>=lado or nj>=lado:continue
                v=ni*lado+nj+1
                x1,y1=g.nodes[u]['x'],g.nodes[u]['y']
                x2,y2=g.nodes[v]['x'],g.nodes[v]['y']
                length=math.hypot((x2-x1)*111000*math.cos(math.radians(y1)),(y2-y1)*111000)
                velocidad=35+((u*13+v*7)%25)
                for a,b,factor in ((u,v,1),(v,u,1.12)):
                    g.add_edge(a,b,length=length,speed_kph=velocidad,
                               travel_time=length/velocidad*3.6*factor,highway='synthetic')
    nombres_mun=['Armenia','Buenavista','Calarcá','Circasia','Córdoba','Filandia',
                 'Génova','La Tebaida','Montenegro','Pijao','Quimbaya','Salento']
    regs=[]
    for z in range(40):
        nodo=1+z + (z//6)  # 1..46, índices distintos.
        n=g.nodes[nodo]
        cat='cabecera_municipal' if z<12 else ('atractivo_turistico' if z<27 else ('finca_hotel_rural' if z<35 else 'acopio_trilladora'))
        prefijo='M' if z<12 else ('A' if z<27 else ('F' if z<35 else 'C'))
        nombre=(nombres_mun[z]+' (DEMO)') if z<12 else (f'{cat.replace("_"," ").title()} {z+1} (DEMO)')
        regs.append({'id':f'{prefijo}{z+1:02}', 'nombre':nombre,'municipio':nombres_mun[z%12],
                     'categoria':cat,'latitud':n['y'],'longitud':n['x'],
                     'visita_min':45+((z%4)*15) if cat=='atractivo_turistico' else 0,
                     'nodo_id':nodo,'distancia_nodo_m':0.0,'fuente':'SINTETICO/DEMO', 'estado':'demo'})
    guardar_lugares(DEMO/'lugares.csv',regs)
    nx.write_graphml(g,DEMO/'red.graphml')
    lugares=leer_lugares(DEMO/'lugares.csv',verificar_minimos=True)
    matriz=matriz_tiempos(lista_adyacencia(g),lugares)
    guardar_matriz(DEMO/'matriz_tiempos.csv',matriz)
    guardar_envolvente_geojson(puntos_utm_de_grafo(g),DEMO/'envolvente.geojson')
    guardar_json(DEMO/'resumen_red.json',{
        'advertencia':'DATOS ARTIFICIALES, NO SON CARRETERAS REALES DEL QUINDÍO',
        'V':g.number_of_nodes(),'E':g.number_of_edges(),'lugares':len(lugares),
        'semilla':'determinista_sin_aleatoriedad',
    })
    print(f'DEMO generado: V={g.number_of_nodes()}, E={g.number_of_edges()}, lugares={len(lugares)}')

if __name__=='__main__':main()
