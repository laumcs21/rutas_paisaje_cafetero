# Cómo completar el catálogo de 40 lugares reales

El enunciado pide mínimo **40 lugares reales del Quindío**: 12 cabeceras municipales, 15 atractivos turísticos, 8 fincas/hoteles rurales y 5 centros de acopio/trilladoras.

El archivo `datos/real/catalogo_plantilla.csv` **NO está listo para usarse como fuente real**. Contiene las 12 cabeceras exigidas y cinco ejemplos de atractivos mencionados en el enunciado, pero sus coordenadas siguen vacías, y hay lugares pendientes por investigar. NO se inventaron nombres de fincas/trilladoras ni coordenadas.

## Campos CSV

| Campo | Qué registrar |
|---|---|
| `id` | Identificador único, p. ej. M01, A01, F01, C01 |
| `nombre` | Nombre público del sitio real, verificado |
| `municipio` | Uno de los 12 municipios del Quindío |
| `categoria` | `cabecera_municipal`, `atractivo_turistico`, `finca_hotel_rural`, `acopio_trilladora` |
| `latitud`, `longitud` | Coordenadas de la entrada o ubicación principal en WGS84, decimales |
| `visita_min` | Solo atractivos: duración estimada **>0** y justificada |
| `nodo_id` | Dejar vacío; lo genera el script de asociación |
| `distancia_nodo_m` | Dejar vacío; lo genera el script |
| `fuente` | URL, ficha oficial, OpenStreetMap ID o criterio propio explícito |
| `estado` | `verificado` cuando se compruebe el dato y fuente |

Las 12 cabeceras se ubican en su plaza principal, no en un punto genérico del municipio. Armenia (M01) debe representar **Plaza de Bolívar**. Verifica los 40 puntos en un mapa antes de asociarlos al grafo.

### Pasos

1. Abre `datos/real/catalogo_plantilla.csv` en Excel, LibreOffice o VS Code.
2. Sustituye todos los `PENDIENTE_*` por nombres auténticos y su municipio.
3. Busca/verifica cada latitud y longitud; registra la fuente consultada. Las fincas/hoteles/trilladoras deben existir y localizarse en el Quindío.
4. Registra duración y fuente/criterio para los 15 atractivos.
5. Guarda en **CSV UTF-8** con el mismo separador (coma) y nombres de columnas.
6. Ejecuta `python -m scripts.asociar_catalogo`.
7. Revisa `alertas_nodos_lejanos.json`; si hay >500 m, investiga si el sitio está en una finca rural sin acceso representado, la entrada está en otro lugar o hubo error geográfico. **No alteres la coordenada para forzar que aparezca <500m** sin justificación.
8. Ejecuta `python -m scripts.generar_resultados_reales`.

Una fuente sugerida para corroborar lugares: OpenStreetMap, páginas oficiales de turismo, autoridades locales y páginas oficiales de los establecimientos. La validación humana es obligatoria; OpenStreetMap también puede tener registros incorrectos.
