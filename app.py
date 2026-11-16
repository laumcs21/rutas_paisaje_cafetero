"""Interfaz Streamlit para la red real del Quindío y un modo de demostración sintético."""
from pathlib import Path
import json
import math
import pandas as pd
import folium
from folium.plugins import Fullscreen
import streamlit as st
from streamlit_folium import st_folium
from rutas.datos import leer_lugares,leer_matriz
from rutas.grafos import cargar_grafo,lista_adyacencia,coordenadas_ruta
from rutas.dijkstra import dijkstra_heap
from rutas.tsp import tsp_held_karp,tsp_vecino_cercano,brecha_porcentaje,duracion_itinerario

BASE=Path(__file__).resolve().parent

st.set_page_config(page_title='Rutas del Paisaje Cultural Cafetero',page_icon='🗺️',layout='wide')
st.title('Rutas del Paisaje Cultural Cafetero')
st.caption('Proyecto final — Análisis de Algoritmos | Red vial, Dijkstra, QuickHull y TSP')

opciones=['demo']
if all((BASE/'datos/real'/f).exists() for f in ('red.graphml','lugares.csv','matriz_tiempos_40x40.csv')):
    opciones.append('real')
modo=st.sidebar.radio('Conjunto de datos',opciones,index=(len(opciones)-1))
carpeta=BASE/'datos'/modo
if modo=='demo':
    st.warning('MODO DEMOSTRACIÓN — Todas las carreteras, coordenadas y tiempos de este conjunto son SINTÉTICOS. NO son resultados del Quindío real.')
else:
    st.info('MODO REAL — Tiempos estimados por velocidades imputadas desde los datos viales de OpenStreetMap; no representan tráfico en tiempo real.')

@st.cache_resource(show_spinner='Cargando grafo...')
def cargar_red(ruta):
    g=cargar_grafo(ruta)
    return g,lista_adyacencia(g)

@st.cache_data
def cargar_catalogo(ruta):
    return leer_lugares(ruta,verificar_minimos=True)

@st.cache_data
def cargar_tiempos(ruta):
    return leer_matriz(ruta)

try:
    g,adj=cargar_red(str(carpeta/'red.graphml'))
    lugares=cargar_catalogo(str(carpeta/'lugares.csv'))
    nombre_matriz = (
        'matriz_tiempos_40x40.csv'
        if modo == 'real'
        else 'matriz_tiempos.csv'
    )
    matriz = cargar_tiempos(str(carpeta / nombre_matriz))
except (FileNotFoundError, ValueError, ImportError, RuntimeError) as err:
    st.error(f'No se pueden cargar los datos: {err}')
    st.stop()
por_id={l.id:l for l in lugares}
ids=list(por_id)


def etiqueta(id_):return por_id[id_].etiqueta


def mapa_base(center=None):
    if center is None:
        center=(sum(l.latitud for l in lugares)/len(lugares),sum(l.longitud for l in lugares)/len(lugares))
    m = folium.Map(
        location=center,
        zoom_start=13,
        tiles='OpenStreetMap',
        control_scale=True,
        scrollWheelZoom=True
    )
    Fullscreen(
        position='topright',
        title='Ampliar mapa',
        title_cancel='Salir de pantalla completa'
    ).add_to(m)
    return m


def dibujar_ruta(mapa,ruta,color='#1667D9',tooltip='Ruta'):
    if ruta:
        folium.PolyLine(coordenadas_ruta(g,ruta),color=color,weight=5,opacity=.85,tooltip=tooltip).add_to(mapa)


def ver_mapa(mapa,clave):
    st_folium(
        mapa,
        height=650,
        use_container_width=True,
        returned_objects=[],
        key=clave
    )

pestañas=st.tabs(['Ruta más rápida','Envolvente convexa','Itinerario de un día','Experimentos y tablas','Acerca del proyecto'])

with pestañas[0]:
    st.subheader('Consulta de caminos mínimos — Dijkstra con cola de prioridad')
    c1,c2=st.columns(2)
    with c1:inicio=st.selectbox('Origen',ids,format_func=etiqueta,key='ruta_inicio')
    with c2:fin=st.selectbox('Destino',ids,index=min(11,len(ids)-1),format_func=etiqueta,key='ruta_fin')
    r=dijkstra_heap(adj,por_id[inicio].nodo_id,por_id[fin].nodo_id)
    if math.isfinite(r.costo):
        st.metric('Tiempo estimado de viaje',f'{r.costo/60:.1f} min')
        st.caption(f'{r.explorados:,} nodos explorados · {len(r.ruta):,} nodos en la ruta')
        m=mapa_base((por_id[inicio].latitud,por_id[inicio].longitud))
        dibujar_ruta(m,r.ruta)
        for punto,color in [(por_id[inicio],'green'),(por_id[fin],'red')]:
            folium.Marker([punto.latitud,punto.longitud],tooltip=punto.nombre,icon=folium.Icon(color=color)).add_to(m)
        puntos_ruta = coordenadas_ruta(g, r.ruta)
        puntos_visibles = list(puntos_ruta) + [
            (por_id[inicio].latitud, por_id[inicio].longitud),
            (por_id[fin].latitud, por_id[fin].longitud)
        ]

        latitudes = [p[0] for p in puntos_visibles]
        longitudes = [p[1] for p in puntos_visibles]

        m.fit_bounds(
            [
                [min(latitudes), min(longitudes)],
                [max(latitudes), max(longitudes)]
            ],
            padding=(40, 40),
            max_zoom=16
        )

        ver_mapa(m, f'mapa-ruta-{modo}-{inicio}-{fin}')
    else:
        st.error('No existe camino entre los puntos seleccionados.')

with pestañas[1]:
    st.subheader('Envolvente convexa — QuickHull de implementación propia')
    geo=carpeta/'envolvente.geojson'
    if geo.exists():
        m=mapa_base()
        capa_hull=folium.GeoJson(
            json.loads(geo.read_text(encoding='utf-8')),
            style_function=lambda _: {'color':'#7C3AED','weight':3,'fillOpacity':.12}
        ).add_to(m)
        m.fit_bounds(capa_hull.get_bounds(),padding=(30,30))
        for l in lugares:
            folium.CircleMarker([l.latitud,l.longitud],radius=2,color='#164E63',fill=True).add_to(m)
        ver_mapa(m,f'mapa-hull-{modo}')
        st.caption('La envolvente corresponde a los nodos viales, no al contorno administrativo del departamento.')
    else:
        st.warning('No se encontró la envolvente de este modo. Para el modo real ejecuta: python -m scripts.experimentos_r3_r4 --parte r3 --modo real')

with pestañas[2]:
    st.subheader('Recorrido por atractivos: Held-Karp vs vecino más cercano')
    punto=st.selectbox('Lugar de salida/llegada',ids,
                       index=ids.index('M01') if 'M01' in ids else 0,
                       format_func=etiqueta,key='tsp_inicio')
    opciones_atr=[l.id for l in lugares if l.categoria=='atractivo_turistico' and l.id!=punto]
    # En modo REAL iniciar con el itinerario de 6-8 atractivos ya validado
    # experimentalmente; permite modificar cualquier selección manualmente.
    seleccion_inicial = opciones_atr[:6]
    resumen_itinerario = BASE / 'experimentos/resultados' / modo / 'r4_itinerario_resumen.json'
    if resumen_itinerario.exists():
        try:
            previo = json.loads(resumen_itinerario.read_text(encoding='utf-8'))
            if previo.get('inicio') == punto:
                candidatos = [i for i in previo.get('destinos_finales', []) if i in opciones_atr]
                if 6 <= len(candidatos) <= 8:
                    seleccion_inicial = candidatos
        except (ValueError, OSError):
            pass
    visitados=st.multiselect('Selecciona entre 6 y 8 atractivos',opciones_atr,
        default=seleccion_inicial,format_func=etiqueta,max_selections=8)
    if 6<=len(visitados)<=8:
        opt=tsp_held_karp(matriz,punto,visitados)
        vor=tsp_vecino_cercano(matriz,punto,visitados)
        visitas={l.id:l.visita_min for l in lugares}
        total=duracion_itinerario(matriz,opt.ruta,visitas)
        total_voraz=duracion_itinerario(matriz,vor.ruta,visitas)
        a,b,c=st.columns(3)
        a.metric('Held-Karp (desplazamiento)',f'{opt.costo/60:.1f} min')
        b.metric('Vecino cercano (desplazamiento)',f'{vor.costo/60:.1f} min')
        c.metric('Brecha del tiempo de viaje',f'{brecha_porcentaje(vor.costo,opt.costo):.2f} %')
        a,b=st.columns(2)
        a.metric('Jornada total Held-Karp',f'{total["total_s"]/3600:.2f} h')
        b.metric('Jornada total vecino cercano',f'{total_voraz["total_s"]/3600:.2f} h')
        st.write('**Ruta óptima:**',' → '.join(por_id[x].nombre for x in opt.ruta))
        st.write('**Ruta voraz:**',' → '.join(por_id[x].nombre for x in vor.ruta))
        st.write(f"**Jornada óptima:** {total['viaje_s']/3600:.2f} h de desplazamiento + "
                 f"{total['visitas_s']/3600:.2f} h de visitas = **{total['total_s']/3600:.2f} h**")
        if total['cabe']:
            st.success('El itinerario óptimo cabe en una jornada de 11 horas.')
        else:
            st.warning('El itinerario óptimo no cabe en 11 horas. Ajusta los destinos y recalcula.')
        st.caption('Las duraciones de visita son las mismas en ambos órdenes; la diferencia de jornada se debe al desplazamiento. No se incluye tráfico en tiempo real ni horarios de apertura.')
        tabla=[];acum=0
        for i,lid in enumerate(opt.ruta):
            mov=(matriz[opt.ruta[i-1]][lid]/60 if i else 0)
            visita=visitas.get(lid,0) if i>0 and i<len(opt.ruta)-1 else 0
            acum+=(mov+visita)
            tabla.append({'Orden':i,'Lugar':por_id[lid].nombre,'Desplazamiento (min)':round(mov,1),
                          'Visita (min)':visita,'Acumulado (h)':round(acum/60,2)})
        st.dataframe(pd.DataFrame(tabla),hide_index=True,use_container_width=True)
        m=mapa_base((por_id[punto].latitud,por_id[punto].longitud))
        for ruta,color,titulo in [(opt.ruta,'#1679D2','Held-Karp'),(vor.ruta,'#D46C19','Vecino cercano')]:
            for u,v in zip(ruta,ruta[1:]):
                r=dijkstra_heap(adj,por_id[u].nodo_id,por_id[v].nodo_id)
                if r.ruta:
                    dibujar_ruta(m,r.ruta,color,titulo)
        for n in set(visitados+[punto]):
            l=por_id[n]
            folium.Marker([l.latitud,l.longitud],tooltip=l.nombre,
                          icon=folium.Icon(color='green' if n==punto else 'blue')).add_to(m)
        puntos_visita=[(por_id[i].latitud,por_id[i].longitud) for i in [punto,*visitados]]
        m.fit_bounds([[min(p[0] for p in puntos_visita),min(p[1] for p in puntos_visita)],
                      [max(p[0] for p in puntos_visita),max(p[1] for p in puntos_visita)]],padding=(35,35))
        st.caption('Azul = recorrido Held-Karp; naranja = heurística. Las líneas pueden superponerse.')
        ver_mapa(m,f'mapa-itinerario-{modo}-{punto}')
    else:
        st.info('Debes seleccionar entre 6 y 8 atractivos para calcular los recorridos.')


with pestañas[3]:
    st.subheader("Tablas y gráficas del protocolo experimental")

    r1 = BASE / "resultados/r1_componentes"
    r2 = BASE / "resultados/r2_dijkstra"
    # No mezclar resultados sintéticos con los obtenidos sobre la red real.
    res = BASE / "experimentos/resultados" / modo
    gra = BASE / "experimentos/graficas" / modo
    if modo == "demo" and not res.exists():
        # Compatibilidad con resultados DEMO incluidos en el ZIP original.
        res = BASE / "experimentos/resultados"
        gra = BASE / "experimentos/graficas"
    if modo == "real" and not (res / "entorno.json").exists():
        st.info("R3/R4 aún no tienen mediciones reales. Ejecuta python -m scripts.experimentos_r3_r4 --modo real")

    st.caption('R1 y R2: resultados experimentales guardados sobre la red REAL del Quindío. R3 y R4: resultados del modo seleccionado.')
    st.markdown("### R1 · Componentes fuertemente conexas")

    archivo_r1 = r1 / "mediciones_radios.csv"
    grafica_r1 = r1 / "tiempo_vs_tamano_red.png"

    if archivo_r1.exists():
        st.dataframe(
            pd.read_csv(archivo_r1),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No se encontraron las mediciones de R1")

    if grafica_r1.exists():
        st.image(str(grafica_r1), caption="R1 · Tiempo frente al tamaño de la red")

    st.divider()

    st.markdown("### R2 · Caminos mínimos con Dijkstra")

    archivos_r2 = [
        ("pares_mediciones.csv", "Mediciones de los pares evaluados"),
        ("pares_cocientes.csv", "Comparación de rendimiento: lineal / heap"),
    ]

    for nombre, titulo in archivos_r2:
        archivo = r2 / nombre
        if archivo.exists():
            st.markdown(f"**{titulo}**")
            st.dataframe(
                pd.read_csv(archivo),
                use_container_width=True,
                hide_index=True
            )

    grafica_r2 = r2 / "pares_tiempo_vs_explorados.png"

    if grafica_r2.exists():
        st.image(
            str(grafica_r2),
            caption="R2 · Tiempo de ejecución frente a nodos explorados"
        )

    resumen_r2 = r2 / "pares_resumen.json"

    if resumen_r2.exists():
        with st.expander("Resumen de los experimentos de R2"):
            st.json(json.loads(resumen_r2.read_text(encoding="utf-8")))

    st.divider()

    st.markdown("### R3 · Envolvente convexa")

    archivo_r3 = res / "r3_envolvente.csv"
    grafica_r3 = gra / "r3_envolvente.png"

    if archivo_r3.exists():
        st.dataframe(
            pd.read_csv(archivo_r3),
            use_container_width=True,
            hide_index=True
        )

    if grafica_r3.exists():
        st.image(str(grafica_r3), caption="R3 · Envolvente convexa")
    if not archivo_r3.exists() or not grafica_r3.exists():
        st.info("Faltan resultados de R3 para este modo; comprueba la carpeta de experimentos.")

    st.divider()

    st.markdown("### R4 · Optimización de itinerarios")

    for nombre, titulo in [
        ("r4_exactos.csv", "Algoritmos exactos"),
        ("r4_calidad.csv", "Calidad de las heurísticas"),
        ("r4_itinerario.csv", "Resultados de itinerarios"),
    ]:
        archivo = res / nombre
        if archivo.exists():
            st.markdown(f"**{titulo}**")
            st.dataframe(
                pd.read_csv(archivo),
                use_container_width=True,
                hide_index=True
            )

    grafica_r4 = gra / "r4_exactos.png"

    if grafica_r4.exists():
        st.image(str(grafica_r4), caption="R4 · Comparación de algoritmos exactos")
    if not (res / "r4_exactos.csv").exists() or not grafica_r4.exists():
        st.info("Faltan resultados de R4 para este modo; comprueba la carpeta de experimentos.")

    resumen_r4 = res / "r4_itinerario_resumen.json"

    if resumen_r4.exists():
        with st.expander("Resumen de itinerarios"):
            st.json(json.loads(resumen_r4.read_text(encoding="utf-8")))

    with st.expander("Información de la red vial"):
        resumen_red = carpeta / "resumen_red.json"
        if resumen_red.exists():
            st.json(json.loads(resumen_red.read_text(encoding="utf-8")))

with pestañas[4]:
    st.markdown('''**Proyecto final de Análisis de Algoritmos.** Implementaciones propias de
    Dijkstra lineal y con heap, QuickHull divide y vencerás, fuerza bruta, Held-Karp
    (programación dinámica) y vecino más cercano (voraz). Las librerías proporcionan
    mapas y procesamiento de datos, NO resuelven estos algoritmos.

    **Importante:** el modo DEMO utiliza datos sintéticos. El modo REAL requiere los
    archivos procesados de OpenStreetMap y la matriz de 40 lugares. Los tiempos de
    desplazamiento son estimaciones, no información de tráfico en tiempo real.
    ''')
    st.write(f'Nodos: {g.number_of_nodes():,} | Aristas: {g.number_of_edges():,} | Lugares: {len(lugares)}')
