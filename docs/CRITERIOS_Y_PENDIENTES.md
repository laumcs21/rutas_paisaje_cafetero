# Estado del proyecto y pendientes para una entrega auténtica

## Lo que YA trae este ZIP

- Código ejecutable: grafo y catálogo sintéticos separados de los datos reales.
- Dijkstra lineal y Dijkstra con cola de prioridad, con reconstrucción de caminos y conteo de explorados.
- QuickHull propio de divide y vencerás, verificado con SciPy en datos de prueba.
- TSP asimétrico: fuerza bruta, Held-Karp con recorrido y vecino cercano.
- Medidor de cinco repeticiones, tabla/gráficos R2-R4 y límite de tiempo explícito para los algoritmos lentos.
- R1: código de descarga, velocidades, componente, radios, asociación a 500 m y estimación de memoria.
- R2: matriz de tiempos creada una vez por origen.
- R3: polígonos GeoJSON sobre coordenadas métricas.
- R4: criterio explícito para retirar atractivos hasta cumplir 11 horas.
- R5: aplicación Streamlit con mapas y resultados.
- Pruebas unitarias y prueba integral sobre datos sintéticos.
- Documento técnico iniciado y carpeta `specs`.

## Lo que falta y NO sería correcto inventar

1. **Red vial REAL:** ejecutar descarga con Internet o utilizar el GraphML del profesor. La red sintética no demuestra tamaño, tiempos ni geometría vial real.
2. **Catálogo de 40 lugares REALES:** confirmar los 40 nombres, municipios, coordenadas y fuentes. La plantilla real tiene entradas pendientes. Especial atención a los 5 centros de acopio/trilladoras.
3. **Duración de visita y fuentes:** para los 15 atractivos y las decisiones del itinerario.
4. **Auditar los >500 m:** revisar puntos remotos antes de hacer TSP sobre rutas reales.
5. **Experimentos REALES:** ejecutar R1 y R2-R4 con límite correcto de 300 s, en la misma máquina; registrar hardware, software, valores y tendencias.
6. **Verificar la versión real instalada de NetworkX:** la implementación interna exacta de SCC puede cambiar entre versiones. Citar código de la instalada.
7. **Informe académico completo:** incorporar cifras reales, las gráficas, discutir tendencias y justificar las condiciones de los algoritmos y heurísticas. No presentar texto o resultados simulados como reales.
8. **Integración final en GitHub y sustentación:** commits de integrantes, ejecutar la app desde README y preparar respuestas individuales.

En los archivos de `experimentos/resultados` se guardan resultados **demo** inicialmente. Al correr `--modo real` se sobreescriben, y `entorno.json` identifica inequívocamente su procedencia.
